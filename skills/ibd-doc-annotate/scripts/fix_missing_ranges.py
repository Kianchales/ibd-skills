#!/usr/bin/env python3
"""后处理：为丢失 commentRangeStart/End 的批注补插范围标记（同段落多批注冲突修复）"""
import argparse
import copy
import io
import json
import re
import sys
import zipfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from docx import Document
from docx.oxml.ns import qn

# 用法: python fix_missing_ranges.py <批注版docx> <issues.json>
_ap = argparse.ArgumentParser(description="为丢失 commentRangeStart/End 的批注补插范围标记")
_ap.add_argument("docx", help="批注版 docx 路径")
_ap.add_argument("issues", help="issues.json 路径")
_a = _ap.parse_args()
DOCX, ISSUES = _a.docx, _a.issues

issues = json.load(open(ISSUES, encoding='utf-8'))

def iter_all_paras(doc):
    """遍历正文+表格所有段落"""
    body = doc.element.body
    for p in body.iter(qn('w:p')):
        yield p

def para_text(p):
    return ''.join(t.text or '' for t in p.findall('.//' + qn('w:t')))

def runs_in_para(p):
    """段落直接子级的 w:r（不含批注参考 run 之外的嵌套）"""
    return [c for c in p if c.tag == qn('w:r')]

def run_text(r):
    return ''.join(t.text or '' for t in r.findall(qn('w:t')))

def split_run(r, offset):
    """在 run 内 offset 字符处切开，返回 (前半run, 后半run) 元素；offset=len 则不切"""
    full = run_text(r)
    if offset <= 0:
        return None, r
    if offset >= len(full):
        return r, None
    r2 = copy.deepcopy(r)
    # 前半
    ts = r.findall(qn('w:t'))
    # 清空原 run 文本设为前段
    for t in ts:
        r.remove(t)
    t1 = r.makeelement(qn('w:t'), {})
    t1.text = full[:offset]
    t1.set(qn('xml:space'), 'preserve')
    r.append(t1)
    # 后半
    ts2 = r2.findall(qn('w:t'))
    for t in ts2:
        r2.remove(t)
    t2 = r2.makeelement(qn('w:t'), {})
    t2.text = full[offset:]
    t2.set(qn('xml:space'), 'preserve')
    r2.append(t2)
    r.addnext(r2)
    return r, r2

def make_elem(p, tag, cid):
    e = p.makeelement(qn(tag), {})
    e.set(qn('w:id'), str(cid))
    return e

def make_ref_run(p, cid):
    r = p.makeelement(qn('w:r'), {})
    rPr = p.makeelement(qn('w:rPr'), {})
    rStyle = p.makeelement(qn('w:rStyle'), {})
    rStyle.set(qn('w:val'), 'a3')
    rPr.append(rStyle)
    r.append(rPr)
    ref = p.makeelement(qn('w:commentReference'), {})
    ref.set(qn('w:id'), str(cid))
    r.append(ref)
    return r

def _split_at_boundary(p, boundary):
    """把段落内字符位置 boundary 切成 run 边界（已在边界上则不动）"""
    pos = 0
    for r in runs_in_para(p):
        L = len(run_text(r))
        if L and pos < boundary < pos + L:
            split_run(r, boundary - pos)
            return True
        pos += L
    return False

def _run_spans(p):
    """[(run, 段内起始, 段内结束)]；跳过空文本 run（批注标记 run 文本为空，天然不计入坐标）"""
    pos = 0
    out = []
    for r in runs_in_para(p):
        L = len(run_text(r))
        if not L:
            continue
        out.append((r, pos, pos + L))
        pos += L
    return out

def inject_range_at(p, start, end, cid):
    """在段落 p 的字符区间 [start,end) 插入批注范围

    步骤：先把 end / start 切成 run 边界（先切后边界、再切前边界；切分只改变 run
    划分、不改变字符坐标）→ 按边界定位锚点首/末 run → start 标记插在锚点首 run 前、
    end 标记插在锚点末 run 后（其后紧跟 commentReference run）。
    这样可覆盖「起终点落在同一 run 内」的情形（此时曾出现 end 标记插到 start 之前）。
    """
    _split_at_boundary(p, end)
    _split_at_boundary(p, start)
    spans = _run_spans(p)
    s_run = next((r for r, b, _e in spans if b == start), None)
    e_run = next((r for r, _b, e in spans if e == end), None)
    if s_run is None or e_run is None:
        return False, f'locate fail s={s_run is not None} e={e_run is not None}'
    start_el = make_elem(p, 'w:commentRangeStart', cid)
    s_run.addprevious(start_el)
    end_el = make_elem(p, 'w:commentRangeEnd', cid)
    nxt = e_run.getnext()
    if nxt is None:
        p.append(end_el)
    else:
        nxt.addprevious(end_el)
    # commentReference 放在 rangeEnd 之后
    ref = make_ref_run(p, cid)
    end_el.addnext(ref)
    return True, 'ok'

# 检测缺失
z = zipfile.ZipFile(DOCX)
com = z.read('word/comments.xml').decode('utf-8')
z.close()
all_ids = re.findall(r'w:comment w:id="(\d+)"', com)

doc = Document(DOCX)
doc_starts = set()
doc_ends = set()
for el in doc.element.body.iter():
    if el.tag == qn('w:commentRangeStart'):
        doc_starts.add(el.get(qn('w:id')))
    elif el.tag == qn('w:commentRangeEnd'):
        doc_ends.add(el.get(qn('w:id')))
missing = [i for i in all_ids if i not in doc_starts]
print('missing ids:', missing)

paras = list(iter_all_paras(doc))
fixed = 0
for cid in missing:
    it = issues[int(cid)]
    anchor = it['anchor']
    done = False
    for p in paras:
        txt = para_text(p)
        if anchor in txt:
            s = txt.find(anchor)
            ok, msg = inject_range_at(p, s, s + len(anchor), cid)
            if ok:
                fixed += 1
                print(f'fixed cid {cid} (Z-{int(cid)+1:02d}) anchor={anchor[:20]}')
                done = True
                break
    if not done:
        print(f'!! cid {cid} anchor not found: {anchor[:30]}', file=sys.stderr)

doc.save(DOCX)
print(f'saved, fixed {fixed}/{len(missing)}')

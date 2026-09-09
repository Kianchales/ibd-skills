# -*- coding: utf-8 -*-
"""后处理：为丢失 commentRangeStart/End 的批注补插范围标记（同段落多批注冲突修复）"""
import io, sys, json, zipfile, re, copy
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from docx import Document
from docx.oxml.ns import qn

# 用法: python fix_missing_ranges.py <批注版docx> <issues.json>
DOCX = sys.argv[1] if len(sys.argv) > 1 else 'review/1-1 招股说明书_20260906_v1_批注版.docx'
ISSUES = sys.argv[2] if len(sys.argv) > 2 else 'review/issues.json'

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

def inject_range_at(p, start, end, cid):
    """在段落 p 的字符区间 [start,end) 插入批注范围"""
    runs = runs_in_para(p)
    pos = 0
    # 定位起始 run
    s_run, s_off = None, None
    e_run, e_off = None, None
    for r in runs:
        L = len(run_text(r))
        if s_run is None and pos <= start < pos + L:
            s_run, s_off = r, start - pos
        if pos < end <= pos + L:
            e_run, e_off = r, end - pos
        pos += L
    if s_run is None or e_run is None:
        return False, f'locate fail s={s_run is not None} e={e_run is not None}'
    # 切分
    a, b = split_run(s_run, s_off)  # a=前半, b=后半(含锚点起点)
    if a is not None:
        s_run = b  # 锚点起点在后半 run
    # 重新收集 runs 后对 end 切分（end 偏移可能因切分右移1个run，但字符位置不变）
    if e_run is s_run:
        # 起终点同 run：先按原始偏移处理——切 start 后该 run 文本从锚点开始，end 相对该 run = end-start
        e_run, e_off = s_run, (end - start) if a is not None else e_off
    a2, b2 = split_run(e_run, e_off)  # a2=锚点部分, b2=其后
    # 插标记
    start_el = make_elem(p, 'w:commentRangeStart', cid)
    s_run.addprevious(start_el)
    end_el = make_elem(p, 'w:commentRangeEnd', cid)
    (b2 if b2 is not None else e_run).addprevious(end_el)
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
        print(f'!! cid {cid} anchor not found: {anchor[:30]}')

doc.save(DOCX)
print(f'saved, fixed {fixed}/{len(missing)}')

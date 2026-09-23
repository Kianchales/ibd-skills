#!/usr/bin/env python3
"""S7-b 回写执行器（A-Mem 演化）＋ 回写行修复

**用途**：按各案 `共通点映射_<简称>_<日期>.md`「一、回写清单」把 S6a 定稿的
**高／中高重合**条目回写到旧条目（**低重合不回写，改新增**）：

- **高重合** → 目标条目块尾追加 `- **<案名>实证**：<标题> —— <本案实证首句>（<来源>）`
- **中高**   → 追加 `> **适用场景扩展 YYYY-MM-DD（<案名>）**：…`
- **`--repair`**：修正历史回写行的**截断／括号不配对**（旧脚本硬截断 `emp[:180]` 所致）——
  按源文件重抽「**括号深度为 0 的首句**」，禁硬截断（2026-09-22 实证：205 行受损）

**安全纪律**：
- 默认 **dry-run**；`--apply` 才写盘
- **幂等**：目标条目块内已出现该案名 ⇒ 跳过（重跑不重复追加）
- 只**追加**不删改；按文件分组、行号**降序**插入防漂移
- 写盘一律 `newline="\\n"`（库内行尾统一 LF；见 `docs/ENV-PITFALLS.md` §八）
- 执行后必须 `--refresh-index` ＋ 护栏 0 ERROR ＋ 清单销项（**回写会改变后续条目行号**）

用法：
    python <skill>/scripts/apply_rewrite.py --methods-root <工作区根>              # dry-run 统计
    python <skill>/scripts/apply_rewrite.py --methods-root <工作区根> --apply
    python <skill>/scripts/apply_rewrite.py --methods-root <工作区根> --repair --apply
"""
import argparse
import collections
import glob
import io
import json
import os
import re
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HDR = re.compile(r'^(#{2,4})\s+([A-Z]{1,2})-(\d{2})(\d{4})(?!\d)')
ENTRY = re.compile(r'^###\s+[FLI]-AN\d{4}-\d{2}\s*[｜|]\s*(.+?)\s*$')
ANCHOR = re.compile(r'-\s*\*\*对照锚点\*\*\s*[:：]\s*(.+?)\s*$')
REL = re.compile(r'\[(强化|扩展|新增)\s*([A-Z]{1,2}-\d{5,6})?\s*([^\]]*)\]')
LINE = re.compile(r'^(- \*\*(?P<n1>\S+?)实证\*\*：|> \*\*适用场景扩展 \d{4}-\d{2}-\d{2}（(?P<n2>\S+?)）\*\*：)')
PAT = re.compile(r'^(?P<head>- \*\*\S+?实证\*\*：|> \*\*适用场景扩展 \d{4}-\d{2}-\d{2}（\S+?）\*\*：)'
                 r'(?P<title>.*?)\s+——\s+(?P<rest>.*)$')


def read_text(p):
    return io.open(p, encoding='utf-8', newline='').read()


def write_text(p, t):
    io.open(p, 'w', encoding='utf-8', newline='\n').write(t)


def target_files(root):
    m = os.path.join(root, 'methods')
    out = [os.path.join(m, x) for x in ('通用方法论_财务域.md', '通用方法论_法律域.md',
                                        '通用方法论_行业域.md', '通用方法论_体例域.md',
                                        '投行语言专项_W系列.md', '投行语言专项_P系列.md')
           if os.path.isfile(os.path.join(m, x))]
    out += sorted(glob.glob(os.path.join(m, '分卷', '*.md')))
    return out


def build_index(files):
    idx = collections.defaultdict(list)
    for p in files:
        for i, ln in enumerate(read_text(p).split('\n')):
            m = HDR.match(ln)
            if m:
                idx[m.group(2) + '-' + m.group(3) + m.group(4)].append((p, i))
    return idx


def entry_text(case_dir, code):
    """在案目录三份专家产出里按编号取条目原文"""
    for role in ('财务', '法律', '行业'):
        for f in glob.glob(os.path.join(case_dir, '产出_%s_*蒸馏.md' % role)):
            t = read_text(f)
            m = re.search(r'^###\s+' + re.escape(code) + r'\s*[｜|]?\s*(.+?)\s*$', t, re.M)
            if m:
                return m.group(1), t[m.end():m.end() + 4000]
    return None, None


def sentence(seg):
    """本案实证首句：取「括号深度为 0 的第一个 。」；无则回退到最后一个平衡点 + ……"""
    m = re.search(r'-\s*\*\*本案实证\*\*\s*[:：]\s*(.+)', seg)
    et = m.group(1) if m else ''
    depth, cut = 0, -1
    for k, ch in enumerate(et[:400]):
        if ch == '（':
            depth += 1
        elif ch == '）':
            depth = max(0, depth - 1)
        elif ch == '。' and depth == 0:
            cut = k
            break
    if cut >= 0:
        body = et[:cut + 1]
    else:
        body = et[:260]
        d, last = 0, 0
        for k, ch in enumerate(body):
            if ch == '（':
                d += 1
            elif ch == '）':
                d -= 1
            if d == 0:
                last = k
        body = body[:last + 1] + '……'
    src = re.findall(r'（[^（）]{0,40}?(?:PAGE|P)\s*\d+[^（）]{0,50}?）', et)
    if not src:
        src = re.findall(r'(?:PAGE|P)\s*\d+(?:[-–、]\d+)?', et)
    src = re.sub(r'[（）]', '', src[0]) if src else '本案产出文件'
    return body, src


def unclosed(line):
    """截断特征判据：**行末括号深度 > 0**（＝某处 `（` 未闭合，实为硬截断）。

    不用「开闭数量不等」——合法嵌套 `（（一）（二））` 与引文中的孤立 `）`（如「1）中大型 PLC」）
    都会造成数量不等，但**深度归零/为负**，属正常文本（2026-09-22 实证：粗判据误报 1 行）。
    """
    depth = 0
    for ch in line:
        if ch == '（':
            depth += 1
        elif ch == '）':
            depth -= 1
    return depth > 0


def plans(root):
    out = []
    for mp in sorted(glob.glob(os.path.join(root, 'cases', '*', '共通点映射_*_*.md'))):
        case_dir = os.path.dirname(mp)
        name = os.path.basename(case_dir).split('_')[1] if '_' in os.path.basename(case_dir) else ''
        t = read_text(mp)
        if '一、回写清单' not in t:
            continue
        sec = t.split('一、回写清单')[1].split('## 二、')[0]
        for ln in sec.split('\n'):
            m = re.match(r'^\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|\s*(高|中高)\s*\|', ln)
            if not m or '---' in m.group(1) or m.group(1).strip() in ('新案条目', '新案条目 '):
                continue
            nt, field, grade = m.group(1).strip(), m.group(2).strip(), m.group(3)
            nc = re.match(r'^([FLI]-AN\d{4}-\d{2})', nt)
            tc = re.search(r'\b([FLIWS]{1,2}-\d{2}\d{4})\b', field)
            if not (nc and tc):
                continue
            out.append({'case': name, 'dir': case_dir, 'new': nc.group(1),
                        'target': tc.group(1), 'grade': grade})
    return out


def do_rewrite(root, apply_):
    files = target_files(root)
    idx = build_index(files)
    rows, pend = [], []
    for r in plans(root):
        title, seg = entry_text(r['dir'], r['new'])
        if not title:
            pend.append((r['case'], r['new'], 'source_missing'))
            continue
        if r['target'] not in idx:
            pend.append((r['case'], r['new'], 'target_not_in_library:' + r['target']))
            continue
        body, src = sentence(seg)
        r.update({'title': title, 'emp': body, 'src': src, 'file': idx[r['target']][0][0],
                  'line': idx[r['target']][0][1]})
        rows.append(r)
    print('可执行回写 %d 条 ｜ 待人工判定 %d 条' % (len(rows), len(pend)))
    c = collections.Counter(x['grade'] for x in rows)
    print('分布：高 %d ／ 中高 %d' % (c['高'], c['中高']))
    for x in pend[:8]:
        print('   [待判]', x[0], x[1], x[2])
    byfile = collections.defaultdict(list)
    for r in rows:
        byfile[r['file']].append(r)
    written, skipped = 0, 0
    for p, rs in byfile.items():
        lines = read_text(p).split('\n')
        ins = collections.defaultdict(list)
        for r in rs:
            i = r['line']
            j = i + 1
            while j < len(lines) and not lines[j].startswith('#'):
                j += 1
            if r['case'] in '\n'.join(lines[i:j]):
                skipped += 1
                continue
            if r['grade'] == '高':
                add = '- **%s实证**：%s —— %s（%s）' % (r['case'], r['title'][:60], r['emp'], r['src'])
            else:
                add = '> **适用场景扩展 2026-09-20（%s）**：%s —— %s（%s）' % (
                    r['case'], r['title'][:60], r['emp'], r['src'])
            ins[j - 1].append(add)
        for pos in sorted(ins, reverse=True):
            for add in ins[pos]:
                lines.insert(pos + 1, add)
                written += 1
        if apply_ and ins:
            write_text(p, '\n'.join(lines) + '\n')
    print('写入 %d 条 ｜ 幂等跳过 %d 条 ｜ 写盘: %s' % (written, skipped, '是' if apply_ else '否（dry-run）'))
    return written


def do_repair(root, apply_):
    cases = {}
    for d in glob.glob(os.path.join(root, 'cases', '*_*_2026*')):
        b = os.path.basename(d)
        if '_' in b:
            cases[b.split('_')[1]] = d
    idx = {}
    for name, d in cases.items():
        for role in ('财务', '法律', '行业'):
            for f in glob.glob(os.path.join(d, '产出_%s_*蒸馏.md' % role)):
                t = read_text(f)
                for m in re.finditer(r'^###\s+[FLI]-AN\d{4}-\d{2}\s*[｜|]\s*(.+?)\s*$', t, re.M):
                    body, src = sentence(t[m.end():m.end() + 4000])
                    idx[(name, m.group(1)[:18])] = (m.group(1), body, src)
    fixed = 0
    for p in target_files(root):
        lines = read_text(p).split('\n')
        out, changed = [], False
        for l in lines:
            if PAT.match(l) and unclosed(l):
                m = PAT.match(l)
                nm = LINE.match(l)
                name = (nm.group('n1') or nm.group('n2')) if nm else ''
                hit = idx.get((name, m.group('title').strip()[:18]))
                if hit:
                    out.append('%s%s —— %s（%s）' % (m.group('head'), hit[0], hit[1], hit[2]))
                else:
                    rest = re.sub(r'（（.*$', '（', m.group('rest')).rstrip('；，、 ')
                    out.append('%s%s —— %s）' % (m.group('head'), m.group('title'), rest))
                fixed += 1
                changed = True
                continue
            out.append(l)
        if changed and apply_:
            write_text(p, '\n'.join(out) + '\n')
    print('修复回写行 %d 行 ｜ 写盘: %s' % (fixed, '是' if apply_ else '否（dry-run）'))
    return fixed


def main():
    ap = argparse.ArgumentParser(description='S7-b 回写执行器（＋ --repair 修历史截断行）')
    ap.add_argument('--methods-root', default=os.getcwd(), help='工作区根（其下含 methods/ 与 cases/）')
    ap.add_argument('--repair', action='store_true', help='只跑「回写行修复」模式')
    ap.add_argument('--apply', action='store_true', help='实际写盘（缺省 dry-run）')
    a = ap.parse_args()
    root = a.methods_root
    if not os.path.isdir(os.path.join(root, 'methods')):
        print('[ENV-ERROR] 未找到方法论库: %s' % os.path.join(root, 'methods'), file=sys.stderr)
        return 2
    if a.repair:
        do_repair(root, a.apply)
    else:
        do_rewrite(root, a.apply)
    print('\n下一步（强制）：① 回写清单销项 ② `daily_distill.py --refresh-index` '
          '③ `check_methods_health.py` 0 ERROR ④ `replay_gate_report.py` 四项门禁')
    return 0


if __name__ == '__main__':
    sys.exit(main())

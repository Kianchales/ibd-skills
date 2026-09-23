#!/usr/bin/env python3
"""PL/S 案例层编号 → 主库编号 归一（族内连续 · 零撞号 · **幂等**）

**用途**：S5 双向三轨产出（各案 `招股书向提炼_PL_<简称>.md` / `体例向提炼_S_<简称>.md`）由多位 writer
并行撰写时，编号各自自定 ⇒ **跨案撞号**（2026-09-20 实证：5 案同时占用 PL-150106–150115）且形态不一
（`PL-AN00NN-NN`／`PL-15-01`／主库号混用）。本脚本由**主理人**统一归一。

**算法（两遍 · 幂等）**：
1. **收集**全部条目的（族，原编号），并统计每个编号的全库出现次数
2. **判定**：
   - 原编号**已是主库号形态**（`PL-1[5-9]xxxx` / `S-0[1-4]xxxx`）**且全库唯一** ⇒ **保留**（已归位，重跑不动）
   - 其余（案例层号／自创形态／撞号者）⇒ 从该族「库内 max+1」起取**首个未被占用**的号
3. **落盘**：仅改写标题行编号与正文自引用；写盘一律 `newline="\\n"`（库内行尾统一 LF）

**族判定三级优先**：① 节标题标记（`族 15` / `PL-15` / `靶心①-⑤`）→ ② 条目自身编号族位 → ③ 文件内
「靶心覆盖自检表」映射；S 条目额外优先读条目下的 `所述族：NN`。

用法：
    python <skill>/scripts/normalize_pl_s.py --methods-root <工作区根>              # dry-run（默认）
    python <skill>/scripts/normalize_pl_s.py --methods-root <工作区根> --apply
    python <skill>/scripts/normalize_pl_s.py --methods-root <工作区根> --cases 北交所_天广实_20260918,北交所_九目化学_20260916
"""
import argparse
import collections
import io
import glob
import os
import re
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CIRCLE = {'①': '15', '②': '16', '③': '17', '④': '18', '⑤': '19'}
PL_ENTRY = re.compile(r'^(#{2,4})\s*(PL[-A-Za-z0-9（）]*)\s*[｜|]\s*(.+?)\s*$')
S_ENTRY = re.compile(r'^(#{2,4})\s*(S[^\s｜|]*)\s*[｜|]\s*(.+?)\s*$')
MAIN_CODE = {'PL': re.compile(r'^PL-1[5-9]\d{4}$'), 'S': re.compile(r'^S-0[1-4]\d{4}$')}


def read_text(p):
    return io.open(p, encoding='utf-8', newline='').read()


def write_text(p, t):
    io.open(p, 'w', encoding='utf-8', newline='\n').write(t)


def fam_marker(line):
    m = re.search(r'PL\s*-?\s*(1[5-9])', line)
    if m:
        return m.group(1)
    m = re.search(r'族\s*[:：]?\s*(0?[1-4]|1[5-9])', line)
    if m:
        return m.group(1).zfill(2)
    m = re.search(r'靶心\s*([①②③④⑤])', line)
    if m:
        return CIRCLE[m.group(1)]
    return None


def fam_of_old(old):
    m = re.match(r'PL-?(1[5-9])\d*', old)
    return m.group(1) if m else None


def selftable_map(lines):
    """从「靶心覆盖自检表」建立 旧编号 → 族 映射（支持 PL-AN0083-01~02 形态）"""
    mp = {}
    for ln in lines:
        f = None
        m = re.search(r'\bPL\s*-?\s*(1[5-9])', ln)
        if m:
            f = m.group(1)
        if not f:
            continue
        for mo in re.finditer(r'PL-AN(\d{4})-(\d{2,3})(?:\s*[~～]\s*(\d{2,3}))?', ln):
            a = int(mo.group(2))
            b = int(mo.group(3)) if mo.group(3) else a
            for i in range(a, b + 1):
                mp['PL-AN%s-%02d' % (mo.group(1), i)] = f
                mp['PL-AN%s-%d' % (mo.group(1), i)] = f
    return mp


def s_counts(lines):
    cnt = {}
    for ln in lines:
        m = re.match(r'^\|\s*(0[1-4])\s*\|\s*[^|]*\|\s*(\d+)\s*\|', ln)
        if m:
            cnt[m.group(1)] = int(m.group(2))
    return cnt


def library_max(root):
    """库内实测各族 max（PL 15-19 / S 01-04）"""
    mx = {'PL': {}, 'S': {}}
    m = os.path.join(root, 'methods')
    paths = [os.path.join(m, '投行语言专项_P系列.md'), os.path.join(m, '通用方法论_体例域.md')]
    vol = os.path.join(m, '分卷')
    if os.path.isdir(vol):
        paths += [os.path.join(vol, x) for x in sorted(os.listdir(vol)) if x.endswith('.md')]
    for p in paths:
        if not os.path.isfile(p):
            continue
        for ln in read_text(p).split('\n'):
            mm = re.match(r'^#{2,4}\s+(PL|S)-(\d{2})(\d{4})', ln)
            if mm:
                kind, fam, n = mm.group(1), mm.group(2), int(mm.group(3))
                mx[kind][fam] = max(mx[kind].get(fam, 0), n)
    return mx


def library_text(root):
    """库内全文（主库文件 ＋ 分卷）——用于「该案简称是否已在库中出现」的兜底入库判定"""
    m = os.path.join(root, 'methods')
    buf = []
    for p in glob.glob(os.path.join(m, '*.md')) + glob.glob(os.path.join(m, '分卷', '*.md')):
        try:
            buf.append(read_text(p))
        except Exception:
            continue
    return '\n'.join(buf)


def ingested_names(root):
    """从库内「来源案」标记解析**已入库**的案简称 —— 已入库的案一律跳过（除非 --force）

    依据：S7 入库时卷/域文件条目均带 `- **来源案**：<简称>（ANxxxx）`。若某案简称已在库内
    出现，说明其 PL/S 条目**已随批次入库**，此时再「归一」会把它改成新号 ⇒ 与库内旧号脱钩。
    """
    names = set()
    m = os.path.join(root, 'methods')
    paths = []
    for pat in ('*.md',):
        paths += glob.glob(os.path.join(m, pat))
    paths += glob.glob(os.path.join(m, '分卷', '*.md'))
    for p in paths:
        try:
            for ln in read_text(p).split('\n'):
                mm = re.search(r'来源案\*\*\s*[:：]\s*([^\s（(｜|]+)', ln)
                if mm:
                    names.add(mm.group(1).strip())
                mb = re.search(r'案批次\s*[:：]\s*([^\s（(｜|]+)', ln)   # 卷内案批次标题（第二入库信号）
                if mb:
                    names.add(mb.group(1).strip())
        except Exception:
            continue
    return names


def collect_case(case_dir, kind):
    """解析案文件 → (path, [(行号, 族, 原编号, 标题)])"""
    pref = '招股书向提炼_PL_' if kind == 'PL' else '体例向提炼_S_'
    fs = [f for f in os.listdir(case_dir) if f.startswith(pref)]
    if not fs:
        return None, None
    path = os.path.join(case_dir, fs[0])
    lines = read_text(path).split('\n')
    selfmap = selftable_map(lines) if kind == 'PL' else {}
    scnt = s_counts(lines) if kind == 'S' else {}
    s_entries = [i for i, l in enumerate(lines)
                 if S_ENTRY.match(l) and 'S-' in S_ENTRY.match(l).group(2)] if kind == 'S' else []
    order_fam = {}
    if kind == 'S' and scnt and sum(scnt.values()) == len(s_entries):
        seq = []
        for f in sorted(scnt):
            seq += [f] * scnt[f]
        for i, idx in enumerate(s_entries):
            order_fam[idx] = seq[i]

    fam, found = None, []
    for i, ln in enumerate(lines):
        if kind == 'PL':
            if ln.startswith('#'):
                f2 = fam_marker(ln)
                if f2 and f2.startswith('1'):
                    fam = f2
            me = PL_ENTRY.match(ln)
            if me and 'PL' in me.group(2):
                f = fam if (fam and fam.startswith('1')) else None
                f = f or fam_of_old(me.group(2)) or selfmap.get(me.group(2))
                if not f:
                    for j in range(i + 1, min(i + 4, len(lines))):
                        f2 = fam_marker(lines[j])
                        if f2 and f2.startswith('1'):
                            f = f2
                            break
                if f:
                    found.append((i, f, me.group(2), me.group(3), me.group(1)))
        else:
            me = S_ENTRY.match(ln)
            if me and 'S-' in me.group(2):
                f = order_fam.get(i)
                if not f:
                    for j in range(i + 1, min(i + 6, len(lines))):
                        m2 = (re.search(r'所述族\**\s*[:：]\s*\**\s*(0?[1-4])', lines[j])
                              or re.search(r'^\s*-\s*\*\*族\*\*\s*[:：]\s*\**\s*(0?[1-4])', lines[j]))
                        if m2:
                            f = m2.group(1).zfill(2)
                            break
                if not f and ln.startswith('#'):
                    f = fam_marker(ln)
                if not f:
                    for j in range(i - 1, max(i - 8, -1), -1):
                        if lines[j].startswith('#'):
                            f = fam_marker(lines[j])
                            break
                if f:
                    found.append((i, f, me.group(2), me.group(3), me.group(1)))
    return path, found


def discover_cases(root, explicit):
    if explicit:
        return [x.strip() for x in explicit.split(',') if x.strip()]
    tbl = os.path.join(root, 'state', '单案索引对照表.md')
    names = []
    if os.path.isfile(tbl):
        for ln in read_text(tbl).split('\n'):
            m = re.match(r'^\|\s*AN\d{4}\s*\|[^|]*\|\s*([^|]+?)\s*\|', ln)
            if m and m.group(1).strip().startswith(('北交所_', '科创板_', '创业板_', '沪市主板_', '深市主板_')):
                names.append(m.group(1).strip())
    cdir = os.path.join(root, 'cases')
    if not names and os.path.isdir(cdir):
        names = sorted(x for x in os.listdir(cdir) if os.path.isdir(os.path.join(cdir, x)))
    return names


def main():
    ap = argparse.ArgumentParser(description='PL/S 编号归一（族内连续 · 零撞号 · 幂等）')
    ap.add_argument('--methods-root', default=os.getcwd(), help='工作区根（其下含 methods/ 与 cases/）')
    ap.add_argument('--cases', default='', help='案目录名逗号分隔（缺省＝读 state/单案索引对照表.md 或扫 cases/）')
    ap.add_argument('--apply', action='store_true', help='实际写盘（缺省 dry-run）')
    ap.add_argument('--force', action='store_true', help='即使该案已入库也强制归一（默认跳过）')
    a = ap.parse_args()
    root = a.methods_root
    if not os.path.isdir(os.path.join(root, 'methods')):
        print('[ENV-ERROR] 未找到方法论库: %s' % os.path.join(root, 'methods'), file=sys.stderr)
        return 2

    cases = discover_cases(root, a.cases)
    done = ingested_names(root)
    libtext = library_text(root)
    print('案数: %d ｜ MODE=%s' % (len(cases), 'APPLY' if a.apply else 'DRY-RUN'))
    print('库内已入库案（来源案/案批次标记）: %d 个' % len(done))

    # ── 第一遍：收集 ──
    data = []
    code_count = collections.Counter()
    for case in cases:
        cdir = case if os.path.isabs(case) else os.path.join(root, 'cases', case)
        if not os.path.isdir(cdir):
            print('  [SKIP] 目录不存在: %s' % cdir)
            continue
        short = os.path.basename(cdir).split('_')[1] if '_' in os.path.basename(cdir) else os.path.basename(cdir)
        if not a.force and (short in done or short in libtext):
            print('  [SKIP] 已入库（简称已在库内出现）: %s' % short)
            continue
        for kind in ('PL', 'S'):
            path, found = collect_case(cdir, kind)
            if path and found:
                data.append((os.path.basename(cdir), kind, path, found))
                for e in found:
                    code_count[e[2]] += 1

    # ── 第二遍：判定 + 落盘 ──
    lib = library_max(root)
    used = {'PL': set(), 'S': set()}
    for kind in ('PL', 'S'):
        for fam, n in lib[kind].items():
            used[kind] |= {'%s-%s%04d' % (kind, fam, i) for i in range(1, n + 1)}
    for _, kind, _, found in data:                      # 已为主库号且唯一 ⇒ 保留占位
        for e in found:
            if MAIN_CODE[kind].match(e[2]) and code_count[e[2]] == 1:
                used[kind].add(e[2])

    total, need = 0, 0
    for case, kind, path, found in data:
        lines = read_text(path).split('\n')
        per_line, mapping, dist = {}, {}, collections.Counter()
        for idx, fam, old, title, hashes in found:
            total += 1
            dist[fam] += 1
            if MAIN_CODE[kind].match(old) and code_count[old] == 1:
                continue                                 # 已归位 → 幂等保留
            new = None
            for cand in range(lib[kind].get(fam, 0) + 1, 999999):
                code = '%s-%s%04d' % (kind, fam, cand)
                if code not in used[kind]:
                    new = code
                    break
            used[kind].add(new)
            per_line[idx] = new                          # ★ 按行号分配（占位号可能被多条共用）
            if code_count[old] == 1:
                mapping[old] = new                       # 仅唯一旧号才可用于正文自引用替换
            need += 1
        if not per_line:
            print('  %-26s %-3s 条目=%-3d 改号=0（已归位）' % (case, kind, len(found)))
            continue
        fi = {e[0]: e for e in found}
        out = []
        for i, ln in enumerate(lines):
            if i in per_line:
                out.append(ln.replace(fi[i][2], per_line[i], 1))
            else:
                out.append(ln)
        text = '\n'.join(out) + '\n'
        for old, new in sorted(mapping.items(), key=lambda x: -len(x[0])):
            if '待' in old or '（' in old:
                continue
            text = re.sub(r'(?<![A-Za-z0-9-])' + re.escape(old) + r'(?![0-9])', new, text)
        if a.apply:
            write_text(path, text)
        print('  %-26s %-3s 条目=%-3d 改号=%-3d 分布=%s' % (case, kind, len(found), len(per_line), dict(sorted(dist.items()))))
    print('合计条目: %d ｜ 需改号: %d ｜ 写盘: %s' % (total, need, '是' if a.apply else '否（dry-run）'))
    return 0


if __name__ == '__main__':
    sys.exit(main())

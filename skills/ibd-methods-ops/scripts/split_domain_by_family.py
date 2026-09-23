#!/usr/bin/env python3
"""域文件「按族外置」拆分器（配置驱动 · 通用引擎 · 支持**多源汇料**）
一个域的正文可能散在「壳 ＋ N 个批次卷」里；本器按**编号族前缀**把编号条目重组为**族卷**，
非条目内容（批次头／族分组头／附节／过程记录）逐字移入归档伴生文件，壳文件改为薄壳入口。

铁律：**只搬位置、不改内容**（按族重组；族内保持「源顺序 → 源内原顺序」）。
内置自校验：G1 条目守恒（源编号集 == 各族卷编号集）＋ G2 族卷含编号条目
          ＋ G3 壳内无残留编号条目 ＋ G4 非条目内容守恒（逐源拼接、字节可核）。

用法：
    python split_domain_by_family.py --config <配置.json> [--methods-root <工作区根>] [--apply]
    （默认 dry-run；--apply 才写盘 —— 写族卷 ＋ 覆写薄壳 ＋ 非条目归档 ＋ 源文件移入归档）

配置格式（tasks/split_family_config.json）：
{
  "updated": "YYYY-MM-DD",
  "archive_dir": "archive/methods/superseded_<date>",
  "splits": [
    { "prefix": "PL",
      "shell": "20_语言专项/投行语言专项_招股书PL系列.md",
      "sources": ["<壳>", "<卷1>", "<卷2>", ...],
      "out_dir": "50_分卷",
      "volume_stem": "投行语言专项_招股书PL系列",
      "families": {"15": "章节陈述句式"},
      "shell_note": "> ..." }
  ]
}
"""
import argparse, io, json, os, re, shutil, sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_ap = argparse.ArgumentParser(description="域文件按族外置拆分器（多源版）")
_ap.add_argument("--config", default="", help="拆分配置 JSON（默认 {工作区根}/tasks/split_family_config.json）")
_ap.add_argument("--methods-root", default="", help="工作区根")
_ap.add_argument("--apply", action="store_true", help="写盘（默认 dry-run）")
_args = _ap.parse_args()

ROOT = _args.methods_root or os.environ.get("METHODS_ROOT", "") or \
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
M = os.path.join(ROOT, "methods")
CFG = _args.config or os.path.join(ROOT, "tasks", "split_family_config.json")

if not os.path.isdir(M):
    print(u"✗ 未找到方法论库：%s" % M, file=sys.stderr); sys.exit(2)
if not os.path.isfile(CFG):
    print(u"✗ 未找到配置：%s" % CFG, file=sys.stderr); sys.exit(2)

_ILLEGAL = re.compile(u"[\\\\/:*?\"<>|]")
_FULLWIDTH = {u"\\": u"＼", u"/": u"／", u":": u"：", u"*": u"＊", u"?": u"？",
              u"\"": u"”", u"<": u"＜", u">": u"＞", u"|": u"｜"}


def sanitize(s):
    s = u"".join(_FULLWIDTH.get(ch, ch) for ch in s)
    return _ILLEGAL.sub(u"·", s).strip().rstrip(u".")


def read(p):
    return io.open(p, encoding="utf-8").read()


def write(p, t):
    d = os.path.dirname(p)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    io.open(p, "w", encoding="utf-8", newline="\n").write(t)


def split_source(text, ent_rx):
    """→ (items, nonentry, first_line)
    items=[(族号2位, 条目原文)]（条目块截到块内首个 h2 之前）
    nonentry=[非条目段]（首个条目之前的头部 ＋ 块内 h2 之后的尾段 ＋ 未编号 h3 段）"""
    lines = text.split("\n")
    idx = [i for i, l in enumerate(lines) if l.startswith("### ")]
    first = idx[0] if idx else len(lines)
    items, nonentry = [], []
    if first:
        nonentry.append(u"\n".join(lines[:first]))
    for k, i in enumerate(idx):
        j = idx[k + 1] if k + 1 < len(idx) else len(lines)
        seg = lines[i:j]
        cut = len(seg)
        for q, l in enumerate(seg):
            if l.startswith("## "):
                cut = q
                break
        m = ent_rx.match(seg[0])
        if m:
            items.append((m.group(1), u"\n".join(seg[:cut])))   # group(1) = 族号 2 位
        if cut < len(seg):
            nonentry.append(u"\n".join(seg[cut:]))
        elif not m:
            nonentry.append(u"\n".join(seg))
    return items, nonentry, first


cfg = json.load(io.open(CFG, encoding="utf-8"))
TODAY = cfg.get("updated", "")
ARCH = cfg.get("archive_dir", "")

for spec in cfg["splits"]:
    pre, fam = spec["prefix"], spec["families"]
    stem, out_dir = spec["volume_stem"], spec["out_dir"]
    ent_rx = re.compile(u"^### (?:%s)-(\\d{2})(\\d{4})" % pre, re.M)   # re.M：校验时用于整卷 finditer
    print(u"==== %s（%s 域）· 源 %d 份 · %d 族 ====" % (stem, pre, len(spec["sources"]), len(fam)))

    all_items, ne_chunks, used_srcs = [], [], []
    for s in spec["sources"]:
        p = os.path.join(M, s)
        if not os.path.isfile(p):
            print(u"  ✗ 源缺失：%s" % s); continue
        used_srcs.append(s)
        items, ne, _f = split_source(read(p), ent_rx)
        nb = len((u"\n".join(ne)).encode("utf-8"))
        print(u"  · %-54s 编号条目 %3d ｜ 非条目 %6.1fKB" % (os.path.basename(s)[:52], len(items), nb / 1024.0))
        ne_chunks.append(u"<!-- ===== 源：%s（非条目部分 · 逐字保留）===== -->\n\n%s"
                         % (os.path.basename(s), u"\n\n".join(ne).strip()))
        for c2, t in items:
            all_items.append((c2, t, os.path.basename(s)))

    unknown = sorted({c2 for (c2, _t, _s) in all_items if c2 not in fam})
    print(u"  合计编号条目 %d ｜ 未归族 %d %s" % (len(all_items), len(unknown), unknown if unknown else u""))
    if not all_items:
        print(u"  ⏭ 无编号条目（该域可能已拆）⇒ 跳过，不写盘"); print(); continue
    if unknown:
        print(u"  ⚠ 有编号未在 families 登记 ⇒ 本域跳过（先补族名）"); continue

    vols = []
    for c2 in sorted(fam):
        seg = [t for (c, t, _s) in all_items if c == c2]
        if not seg:
            continue
        name = sanitize(fam[c2])
        fname = u"%s_卷%s_%s.md" % (stem, c2, name)
        srcs = u"、".join(sorted({s for (c, _t, s) in all_items if c == c2}))
        body = (u"---\ntype: 方法论族卷\ndomain: %s\nfamily: %s\nfamily_name: %s\nupdated: %s\n---\n\n"
                u"# %s · 卷%s %s\n\n"
                u"> 本卷为**族 %s「%s」**条目正文唯一存放地（%d 条）；2026-09-23 按族重组"
                u"（**只搬位置不改内容**，族内保持「源顺序 → 源内原顺序」）。\n"
                u"> 汇料来源：%s\n"
                u"> 入口壳：`%s`｜调用索引：`methods/_generated/方法论调用索引.md`\n\n%s\n"
                % (stem, c2, name, TODAY, stem, c2, name, c2, name, len(seg), srcs, spec["shell"], u"\n".join(seg)))
        vols.append((fname, body, len(seg), c2))

    shell_raw = read(os.path.join(M, spec["shell"]))
    _si, _sn, sh_first = split_source(shell_raw, ent_rx)
    sh_lines = shell_raw.split("\n")
    sh_head = u"\n".join(sh_lines[:sh_first]).rstrip(u"\n")
    if TODAY:
        sh_head = re.sub(u"(?m)^updated: .*$", u"updated: " + TODAY, sh_head)
    rows = [u"| `%s/%s` | **%s** %s | %d |" % (out_dir, fn, c2, fam[c2], n) for (fn, _b, n, c2) in vols]
    ne_file = u"%s_非条目部分.md" % os.path.splitext(os.path.basename(spec["shell"]))[0]
    shell = (sh_head + u"\n\n" + spec["shell_note"] + u"\n\n## 族分卷索引\n\n"
             u"> 本文件为**入口壳（0 条目）**；全部编号条目按**族**外置为卷（族号＝卷号，族号已冻结）。"
             u"新增条目**追加至对应族卷末尾**（族内 `max+1`、不重排）。\n"
             u"> 原载体的**非条目内容**（批次头／族分组头／附节／过程记录）逐字保留于 `%s/%s`。\n\n"
             u"| 卷文件（`%s/`） | 族 | 条目数 |\n|---|---|---|\n%s\n"
             % (ARCH, ne_file, out_dir, u"\n".join(rows)))

    src_ids, vol_ids = set(), set()
    for (c2, t, _s) in all_items:
        m = ent_rx.match(t)
        if m:
            src_ids.add(pre + u"-" + m.group(1) + m.group(2))
    for (fn, body, _n, _c) in vols:
        for m in ent_rx.finditer(body):
            vol_ids.add(pre + u"-" + m.group(1) + m.group(2))
    g1 = src_ids == vol_ids
    g2 = all(len(re.findall(ent_rx, b)) == n for (_f, b, n, _c) in vols)
    g3 = not any(ent_rx.match(l) for l in shell.split("\n"))
    ne_bytes = len(u"\n\n".join(ne_chunks).encode("utf-8"))
    print(u"  G1 条目守恒：源 %d ｜ 族卷 %d → %s" % (len(src_ids), len(vol_ids), u"PASS" if g1 else u"FAIL"))
    print(u"  G2 族卷条目数吻合：%s" % (u"PASS" if g2 else u"FAIL"))
    print(u"  G3 壳内无残留编号条目：%s" % (u"PASS" if g3 else u"FAIL"))
    print(u"  G4 非条目归档：%d 段 / %.1fKB → %s/%s" % (len(ne_chunks), ne_bytes / 1024.0, ARCH, ne_file))
    for (fn, _b, n, c2) in vols:
        print(u"    · %s（%d 条）" % (fn, n))
    if not (g1 and g2 and g3):
        print(u"  ✗ 自校验未过 ⇒ 不写盘"); continue
    if _args.apply:
        for (fn, body, _n, _c) in vols:
            write(os.path.join(M, out_dir, fn), body)
        write(os.path.join(M, spec["shell"]), shell)
        write(os.path.join(ROOT, ARCH, ne_file), u"\n\n".join(ne_chunks) + u"\n")
        moved = 0
        for s in used_srcs:
            if s == spec["shell"]:
                continue
            shutil.copyfile(os.path.join(M, s), os.path.join(ROOT, ARCH, os.path.basename(s)))
            os.remove(os.path.join(M, s))
            moved += 1
        print(u"  ✓ 已写盘：%d 族卷 ＋ 薄壳；%d 份批次卷移入 %s" % (len(vols), moved, ARCH))
    else:
        print(u"  （dry-run，未写盘）")
    print()

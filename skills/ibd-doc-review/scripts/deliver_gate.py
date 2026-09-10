#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""交付前综合核验（一次跑完 · 极简输出）

把交付前反复核验的物理项**合并为一次调用**，输出「一行一指标」：
PASS 不展开、FAIL 才给明细 —— 避免核验输出本身吃掉上下文。

为什么要有这个脚本：实测一次交付前核验中，同一指标被反复统计（引号 8 次、
XML/结构核验 6 次、锚点 5 次），每次脚本输出都进上下文，成为 token 消耗大头。
把常用核验合并成一次调用、并约定「只输出结论行」，可显著压缩这部分开销。

两种模式（两个参数至少给一个）:
    ① 交付件全套九项（给 --docx）—— 交付前跑:
       python deliver_gate.py --docx 交付件.docx --md 内容源.md --anchors "36,507.55;19.96"
       （查: 标点 / 样式 / vMerge / 锚点 / 禁用词 / 占位符 / 结构 / 同源核验 / 指纹）
    ② md 侧预检（只给 --md）—— 套样式「之前」跑，把文字规范门禁前移:
       python deliver_gate.py --md 草稿.md --anchors "36,507.55;19.96"
       （查: 标点全半角 / 禁用词红线 / 占位符 / 锚点计数 / 文档结构）

可选参数:
    --anchors "A;B"      关键数字锚点，分号分隔（勿用逗号——数字含千分位逗号）
    --ban "词1,词2"      禁用词，逗号/分号分隔；不传则用内置投行红线（13 词）
    --scenario 反馈回复|招股书|报告   必备样式集合，默认 反馈回复
    --expect-vmerge N    期望的纵向合并标记数
    --detail N           FAIL 时最多展开几条明细，默认 5

退出码: 0 = 全过；1 = 存在 FAIL（可直接作为交付门禁判断依据）

设计约定（配合低 token 消耗）:
    · 只输出结论行；FAIL 明细默认最多 5 条
    · 不做全量文本 dump；需要明细时用 check_styles.py / check_content.py 单独跑
    · 零第三方依赖（zipfile + xml.etree 即可），与 skill「内置脚本零依赖」承诺一致
"""
import argparse
import hashlib
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

STYLE_BY_SCENARIO = {
    "反馈回复": ["000", "0011", "001"],
    "招股书": ["000", "001"],
    "报告": ["000", "001"],
}

# 投行文档禁用词红线（默认启用；传 --ban 可覆盖）
DEFAULT_BAN = [
    "颠覆", "革命性", "领先全球", "世界第一", "国内首创", "填补空白",
    "唯一", "最先进", "必将", "确保上市", "大力", "赋能", "护城河",
]

# 中文标点成对表
DQ_HALF, DQ_L, DQ_R = '"', "\u201c", "\u201d"
LP_HALF, RP_HALF = "(", ")"
LP_FULL, RP_FULL = "\uff08", "\uff09"


# ----------------------------------------------------------------- 读取

def read_docx(path):
    """返回 (全文文本, 根节点, 包内 document.xml 原文)"""
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    root = ET.fromstring(xml)
    text = "".join(t.text or "" for t in root.iter(W + "t"))
    return text, root, xml


def read_md(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def norm_for_compare(s):
    """内容比对用的归一化：去 markdown/HTML 标记与全部空白（用于 md↔docx 同源核验）

    注：md 侧的 <sup> 标记在 docx 中已转为原生上标，故一并剥离，
    否则会产生 4 处「伪差异」（实测 2026-09-10）。
    """
    s = re.sub(r"`+", "", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"[#>*|]+", "", s)
    s = re.sub(r"[-]{3,}", "", s)
    return re.sub(r"\s|\u3000", "", s)


def strip_punct(s):
    """去掉成对标点字符，用于「零内容改动」指纹"""
    return re.sub("[" + re.escape(DQ_HALF + DQ_L + DQ_R + LP_HALF + RP_HALF + LP_FULL + RP_FULL) + "]", "", s)


# ----------------------------------------------------------------- 核验项

def check_punct(docx_text):
    half = docx_text.count(DQ_HALF) + docx_text.count(LP_HALF) + docx_text.count(RP_HALF)
    ok = half == 0
    detail = (f"半角引号 {docx_text.count(DQ_HALF)} / 半角括号 "
              f"{docx_text.count(LP_HALF)}+{docx_text.count(RP_HALF)}；"
              f"全角引号 {docx_text.count(DQ_L)}+{docx_text.count(DQ_R)} / "
              f"全角括号 {docx_text.count(LP_FULL)}+{docx_text.count(RP_FULL)}")
    fails = [] if ok else [f"残留半角标点 {half} 处（中文语境须用全角）"]
    return "标点规范", ok, detail, fails


def check_styles(root, scenario):
    styles = [p.get(W + "val") for p in root.iter(W + "pStyle")]
    dist = {}
    for s in styles:
        dist[s] = dist.get(s, 0) + 1
    need = STYLE_BY_SCENARIO.get(scenario, STYLE_BY_SCENARIO["反馈回复"])
    missing = [s for s in need if s not in dist]
    # 正文段落（body 级，排除表格单元格内的段落）：有文字但无 pStyle / 空段落
    in_table = set()
    for tc in root.iter(W + "tc"):
        for p in tc.iter(W + "p"):
            in_table.add(id(p))
    body_bare = body_empty = 0
    for p in root.iter(W + "p"):
        if id(p) in in_table:
            continue  # 表格内段落由 tblStyle 承担，不计
        txt = "".join(t.text or "" for t in p.iter(W + "t"))
        if txt.strip() == "":
            body_empty += 1
        elif p.find(W + "pPr/" + W + "pStyle") is None:
            body_bare += 1
    ok = (not missing) and body_bare == 0 and body_empty == 0
    top = " ".join(f"{k or '(裸)'}:{v}" for k, v in sorted(dist.items(), key=lambda x: -x[1])[:8])
    detail = f"pStyle {len(styles)} 段（{top}）；必备 {'齐备' if not missing else '缺 ' + ','.join(missing)}；裸 {body_bare} / 空 {body_empty}"
    fails = []
    if missing:
        fails.append(f"缺少必备样式: {missing}")
    if body_bare:
        fails.append(f"裸正文段落 {body_bare} 个")
    if body_empty:
        fails.append(f"空段落 {body_empty} 个")
    return "样式规范", ok, detail, fails


def check_merge(root, expect):
    vm = sum(1 for _ in root.iter(W + "vMerge"))
    gs = sum(1 for _ in root.iter(W + "gridSpan"))
    if expect is None:
        return "合并标记", True, f"vMerge {vm} / gridSpan {gs}（未设期望值，仅报告）", []
    ok = vm == expect
    fails = [] if ok else [f"vMerge 期望 {expect}，实测 {vm}"]
    return "合并标记", ok, f"vMerge {vm} / gridSpan {gs}", fails


def check_anchors(docx_text, md_text, anchors):
    if not anchors:
        return None
    fails, parts, n_ok = [], [], 0
    for a in anchors:
        a = a.strip()
        if not a:
            continue
        c1, c2 = docx_text.count(a), md_text.count(a)
        if c1 == c2 and c1 > 0:
            n_ok += 1
            parts.append(f"{a}:{c1}")
        else:
            fails.append(f"{a} docx={c1} md={c2}")
    ok = not fails
    detail = f"{n_ok}/{len([a for a in anchors if a.strip()])} 项一致（{' '.join(parts[:6])}{' …' if len(parts) > 6 else ''}）"
    return "关键锚点", ok, detail, fails


def check_ban(docx_text, words):
    if not words:
        return None
    hits = [(w, docx_text.count(w)) for w in words if w and docx_text.count(w)]
    ok = not hits
    detail = "0 处命中" if ok else f"命中 {sum(c for _, c in hits)} 处"
    fails = [f"{w}: {c} 处" for w, c in hits]
    return "禁用词红线", ok, detail, fails


def check_placeholder(docx_text):
    n = len(re.findall(r"【待补[^】]*】", docx_text))
    return "占位符", True, f"【待补…】{n} 处（须与附表一逐条对应）", []


def check_structure(root, docx_text):
    tbl = len(list(root.iter(W + "tbl")))
    par = len(list(root.iter(W + "p")))
    return "文档结构", True, f"表格 {tbl} / 段落 {par} / 文本 {len(docx_text):,} 字符", []


def check_fingerprint(docx_text, md_text):
    """md↔docx 同源核验：归一化后比对（含差异定位）"""
    if not md_text:
        return None
    a, b = norm_for_compare(md_text), norm_for_compare(docx_text)
    if a == b:
        return "同源核验", True, f"归一化后逐字一致（{len(b):,} 字符）", []
    from difflib import SequenceMatcher
    sm = SequenceMatcher(None, a, b, autojunk=False)
    diffs = [o for o in sm.get_opcodes() if o[0] != "equal"]
    samples = []
    for tag, i1, i2, j1, j2 in diffs[:3]:
        samples.append(f"{tag}: md[{a[i1:i2][:20]!r}] vs docx[{b[j1:j2][:20]!r}]")
    return ("同源核验", False, f"归一化后不一致：{len(diffs)} 处差异（md {len(a):,} / docx {len(b):,} 字符）",
            samples)


def check_footer_hash(docx_xml_punct_stripped):
    h = hashlib.sha256(docx_xml_punct_stripped.encode("utf-8")).hexdigest()[:16]
    return "指纹(去标点)", True, f"document.xml 去标点 sha256[:16] = {h}", []


# ----------------------------------------------------------------- 主流程

def check_md_structure(md_text):
    """md 阶段：标题/表格行/行数/字符规模（仅报告，不作 FAIL）"""
    n_head = len(re.findall(r"^#{1,6} ", md_text, re.M))
    n_tbl = len(re.findall(r"^\|.*\|$", md_text, re.M))
    return ("文档结构", True,
            f"标题 {n_head} / 表格行 {n_tbl} / 行 {md_text.count(chr(10)) + 1:,} / 字符 {len(md_text):,}", [])


def check_anchor_count(md_text, anchors):
    """md 阶段：只报锚点出现次数（此时无 docx 可比对），计数为 0 即 FAIL"""
    if not anchors:
        return None
    parts, zero = [], []
    for a in anchors:
        a = a.strip()
        if not a:
            continue
        c = md_text.count(a)
        parts.append(f"{a}:{c}")
        if c == 0:
            zero.append(a)
    detail = f"{len(parts)} 项（{' '.join(parts[:6])}{' …' if len(parts) > 6 else ''}）"
    return "锚点计数", not zero, detail, [f"锚点未出现: {a}" for a in zero]


def run_md_precheck(md_text, anchors, ban):
    """md 阶段预检 —— 套样式之前就能查的项（标点/禁用词/占位符/锚点/结构）

    用途：把「文字规范」门禁前置到写作链，避免标点问题拖到套样式之后才发现
    （套样式后再改文字会导致样式重做）。
    """
    results = [
        check_punct(md_text),
        check_ban(md_text, ban),
        check_placeholder(md_text),
        check_anchor_count(md_text, anchors),
        check_md_structure(md_text),
    ]
    return [r for r in results if r is not None]


def run_full(args, md_text, anchors, ban):
    """交付件全套九项核验"""
    docx_text, root, xml = read_docx(args.docx)
    results = [
        check_punct(docx_text),
        check_styles(root, args.scenario),
        check_merge(root, args.expect_vmerge),
        check_anchors(docx_text, md_text, anchors),
        check_ban(docx_text, ban),
        check_placeholder(docx_text),
        check_structure(root, docx_text),
        check_fingerprint(docx_text, md_text),
        check_footer_hash(strip_punct(xml)),
    ]
    return [r for r in results if r is not None]


def main():
    ap = argparse.ArgumentParser(description="交付前综合核验（一次跑完 · 极简输出）")
    ap.add_argument("--docx", help="交付件 docx（给了跑全套九项）")
    ap.add_argument("--md", help="内容源 md；只给 --md 则跑「套样式前」的 md 侧预检（标点/禁用词/占位符/锚点/结构）")
    ap.add_argument("--anchors", default="",
                    help="关键数字锚点，分号分隔（勿用逗号——数字含千分位逗号），如 '36,507.55;19.96'")
    ap.add_argument("--ban", default="", help="禁用词，逗号或分号分隔；不传则用内置红线（13 词）")
    ap.add_argument("--scenario", default="反馈回复", choices=list(STYLE_BY_SCENARIO))
    ap.add_argument("--expect-vmerge", type=int, default=None)
    ap.add_argument("--detail", type=int, default=5, help="FAIL 时最多展开明细条数")
    args = ap.parse_args()

    if not args.docx and not args.md:
        ap.error("至少提供 --docx 或 --md 之一")

    anchors = [a.strip() for a in args.anchors.split(";") if a.strip()]
    ban = [b.strip() for b in re.split(r"[;,]", args.ban) if b.strip()] or DEFAULT_BAN
    md_text = read_md(args.md) if args.md else ""

    if args.docx:
        results = run_full(args, md_text, anchors, ban)
        title, tail = "交付前综合核验（交付件全套九项）", "可交付"
    else:
        results = run_md_precheck(md_text, anchors, ban)
        title, tail = "内容源预检（md 阶段 · 套样式前）", "可进入套样式"

    print("=" * 72)
    print(title)
    if args.docx:
        print(f"  交付件: {args.docx}")
    if args.md:
        print(f"  内容源: {args.md}")
    print("=" * 72)

    n_fail = 0
    for name, ok, detail, fails in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name:<10} {detail}")
        if not ok:
            n_fail += 1
            for f in fails[: args.detail]:
                print(f"         └─ {f}")
            if len(fails) > args.detail:
                print(f"         └─ …另有 {len(fails) - args.detail} 条（用 check_content.py / check_styles.py 看全量）")

    print("-" * 72)
    total = len(results)
    if n_fail == 0:
        print(f"结论 {total}/{total} PASS ✅  {tail}")
    else:
        print(f"结论 {total - n_fail}/{total} PASS ❌  有 {n_fail} 项 FAIL，修复后重跑")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())

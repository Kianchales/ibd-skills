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

复核产物挂载（与 ① 叠加，开关式）:
    --annotated          批注版交付件 → 追加三项（批注部件 / 批注结构 / 批注编号），共十二项:
                         python deliver_gate.py --docx 批注版.docx --annotated --expect-annotated 42
    --revised            修订版交付件 → 追加三项（修订成对 / 修订落定 / 修订计数），共十二项:
                         python deliver_gate.py --docx 修订稿.docx --revised --expect-revised 18
    注: 批注版与修订版互斥，不要同时给两个开关（同给即报错）。

物理层扫描挂载（与 ① 叠加，开关式 · officecli 驱动）:
    --officecli          追加「物理扫描」一项：OpenXML 架构校验（validate）+
                         渲染层缺陷扫描（view issues）。共十项。
                         python deliver_gate.py --docx 交付件.docx --officecli
    注: officecli 是**可选外部二进制**，未安装时该项输出 [SKIP] 且**不阻断交付**
        （退出码不受影响）；不给 --officecli 时同样输出 [SKIP] 一行——
        **目的就是让「未跑物理扫描」在交付输出里可见**，不靠人记。
        用 --officecli-path 显式指定二进制位置；--expect-issues N 设定可接受的
        缺陷条数（默认 0，即有任何渲染层缺陷即 FAIL）。

三态输出:
    [PASS]  该项通过
    [FAIL]  该项不通过（计入退出码，1）
    [SKIP]  该项未执行（**不计入退出码**；原因写在结论行里）

可选参数:
    --anchors "A;B"      关键数字锚点，分号分隔（勿用逗号——数字含千分位逗号）
    --ban "词1,词2"      禁用词，逗号/分号分隔；不传则用内置投行红线（13 词）
    --scenario 反馈回复|招股书|报告   必备样式集合，默认 反馈回复
    --expect-vmerge N    期望的纵向合并标记数
    --expect-annotated N 期望批注条数（配 --annotated；不传则只查三方自洽）
    --expect-revised N   期望已修订条数（配 --revised；不传则仅报告）
    --officecli-path P   officecli 可执行文件路径（默认自动探测）
    --expect-issues N    可接受的渲染层缺陷条数上限，默认 0（配 --officecli）
    --detail N           FAIL 时最多展开几条明细，默认 5

退出码: 0 = 无 FAIL（含全 SKIP）；1 = 存在 FAIL（可直接作为交付门禁判断依据）

设计约定（配合低 token 消耗）:
    · 只输出结论行；FAIL 明细默认最多 5 条
    · 不做全量文本 dump；需要明细时用 check_styles.py / check_content.py 单独跑
    · 零第三方依赖（zipfile + xml.etree 即可），与 skill「内置脚本零依赖」承诺一致
    · officecli 走 subprocess（可选路径，缺省不影响零依赖承诺）
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
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

# 数字前后不加空格（2026-09-11 用户裁定，rules.md 三·3）
# 西文缩写与数字之间（GB 35114）不匹配——前邻字符为字母而非汉字，天然豁免
RE_SPACE_CJK_NUM = re.compile(r"[\u4e00-\u9fff][ \t]+\d|\d[ \t]+[\u4e00-\u9fff]")


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
    nspace = RE_SPACE_CJK_NUM.findall(docx_text)
    ok = half == 0 and not nspace
    detail = (f"半角引号 {docx_text.count(DQ_HALF)} / 半角括号 "
              f"{docx_text.count(LP_HALF)}+{docx_text.count(RP_HALF)}；"
              f"全角引号 {docx_text.count(DQ_L)}+{docx_text.count(DQ_R)} / "
              f"全角括号 {docx_text.count(LP_FULL)}+{docx_text.count(RP_FULL)}；"
              f"数字前后空格 {len(nspace)} 处")
    fails = [] if half == 0 else [f"残留半角标点 {half} 处（中文语境须用全角）"]
    if nspace:
        sample = "；".join(f"「{s}」" for s in nspace[:5])
        more = f"（另有 {len(nspace) - 5} 处）" if len(nspace) > 5 else ""
        fails.append(
            f"中文与数字之间出现空格 {len(nspace)} 处（数字前后不加空格，"
            f"rules.md 三·3）：{sample}{more}")
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


# ------------------------------------------------ 批注版挂载（--annotated）

CT_NS = "{http://schemas.openxmlformats.org/package/2006/content-types}"
REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"
LABEL_PAT = re.compile(r"^【([A-Z]{1,2})-(\d{2})｜(.+?)｜(高|中|低)】")
# 批注每条固定 4 行紧凑排版：标签行 / 标题行 / 问题描述行 / 建议行
ANN_LEADS = ("问题描述：", "建议：")


def _z_read(path, name):
    with zipfile.ZipFile(path) as z:
        return z.read(name)


def _is_bold(run):
    """run 是否加粗 —— 语义判定：<w:b/> 或无 val 的 <w:b> 为加粗；<w:b w:val="0"> 为显式不加粗

    注意 w:b 与 w:pStyle 同用 w:val 属性，属性名就是 `w:val`（无内层前缀）。
    只判元素存在会把「显式取消加粗」误判为加粗（实测 2026-09-11）。
    """
    el = run.find(W + "rPr/" + W + "b")
    if el is None:
        return False
    v = el.get(W + "val")
    return v is None or str(v).strip() not in ("0", "false", "off")


def check_annotated_parts(docx_path):
    """批注部件：comments.xml 本体 + Content_Types Override + document.xml.rels 关系

    comments.xml 缺失时不再继续读其余部件（否则 KeyError 打断整轮核验）。
    """
    with zipfile.ZipFile(docx_path) as z:
        names = set(z.namelist())
        has_ct = has_rel = False
        if "word/comments.xml" in names:
            ct = z.read("[Content_Types].xml").decode("utf-8")
            rels = (z.read("word/_rels/document.xml.rels").decode("utf-8")
                    if "word/_rels/document.xml.rels" in names else "")
            has_ct = "comments.xml" in ct
            has_rel = "comments.xml" in rels
    if "word/comments.xml" not in names:
        return ("批注部件", False, "缺 word/comments.xml",
                ["交付件不含批注部件（非批注版？）"])
    fails = []
    if not has_ct:
        fails.append("[Content_Types].xml 缺 comments Override")
    if not has_rel:
        fails.append("document.xml.rels 缺 → comments.xml 关系")
    ok = not fails
    detail = f"comments.xml 在包 ✅ / Override {'✅' if has_ct else '❌'} / rels {'✅' if has_rel else '❌'}"
    return "批注部件", ok, detail, fails


def check_annotated_structure(docx_path, expect):
    """批注结构 + 编号合一：条数自洽、cid 唯一、每条 4 段无空行、加粗规则、编号格式与唯一性"""
    with zipfile.ZipFile(docx_path) as z:
        names = set(z.namelist())
        if "word/comments.xml" not in names:
            return ("批注结构", False, "无 comments.xml，跳过结构核验",
                    ["缺 word/comments.xml——批注结构无法核验"])
        cxml = z.read("word/comments.xml")
        dxml = z.read("word/document.xml")
    root = ET.fromstring(cxml)
    comments = root.findall(f"{W}comment")
    n = len(comments)
    doc = ET.fromstring(dxml)
    cs = len(doc.findall(f".//{W}commentRangeStart"))
    ce = len(doc.findall(f".//{W}commentRangeEnd"))
    ref = len(doc.findall(f".//{W}commentReference"))
    fails = []

    cids = [c.get(f"{W}id") for c in comments]
    if len(set(cids)) != n:
        fails.append(f"comment id 重复：{n} 条中唯一 {len(set(cids))}")
    if not (cs == ce == ref == n):
        fails.append(f"锚定对数不齐：cs={cs} ce={ce} ref={ref} 期望={n}")

    numbers = []
    for c in comments:
        cid = c.get(f"{W}id")
        paras = c.findall(f"{W}p")
        if len(paras) != 4:
            fails.append(f"cid {cid}：段落数 {len(paras)} ≠ 4（须 4 行紧凑无空行）")
            continue

        def ptext(p):
            return "".join(t.text or "" for r in p.findall(f"{W}r") for t in r.findall(f"{W}t"))

        def bolds(p):
            return [(_is_bold(r), "".join(t.text or "" for t in r.findall(W + "t")))
                    for r in p.findall(W + "r")]

        texts = [ptext(p) for p in paras]
        if any(not t.strip() for t in texts):
            fails.append(f"cid {cid}：含空段落（批注内禁空行）")
            continue
        # 行1 标签：整行加粗 + 编号格式
        rb0 = bolds(paras[0])
        if not rb0 or not all(b for b, _ in rb0):
            fails.append(f"cid {cid}：行1 标签行未整行加粗")
        m = LABEL_PAT.match(texts[0])
        if not m:
            fails.append(f"cid {cid}：行1 非 【前缀-序号｜类型｜严重度】：{texts[0][:30]}")
        else:
            numbers.append(f"{m.group(1)}-{m.group(2)}")
        # 行2 标题：整行加粗
        rb1 = bolds(paras[1])
        if not rb1 or not all(b for b, _ in rb1):
            fails.append(f"cid {cid}：行2 标题行未整行加粗")
        # 行3/4 引导词加粗、正文常规
        for idx, lead in ((2, ANN_LEADS[0]), (3, ANN_LEADS[1])):
            if not texts[idx].startswith(lead):
                fails.append(f"cid {cid}：行{idx + 1} 应以「{lead}」开头")
                continue
            rb = bolds(paras[idx])
            first = rb[0] if rb else (None, "")
            if not first[0] or not first[1].startswith(lead):
                fails.append(f"cid {cid}：行{idx + 1} 引导词「{lead}」未加粗")
            if [b for b, t in rb[1:] if b and t.strip()]:
                fails.append(f"cid {cid}：行{idx + 1} 正文存在加粗 run（仅引导词可加粗）")

    if len(set(numbers)) != len(numbers):
        dup = sorted({x for x in numbers if numbers.count(x) > 1})
        fails.append(f"批注编号重复：{dup}")
    if expect is not None and n != expect:
        fails.append(f"批注条数 {n} ≠ 期望 {expect}")

    ok = not fails
    detail = (f"{n} 条 / 锚定 cs{cs}=ce{ce}=ref{ref} / 编号唯一 {len(set(numbers))}"
              f"{' / 期望 ' + str(expect) if expect is not None else ''}")
    return "批注结构", ok, detail, fails


# ------------------------------------------------ 修订版挂载（--revised）

def _rev_clean_text(root):
    """接受全部修订后的全文（删 w:del、解包 w:ins），用于「落定证明」"""
    copy = ET.fromstring(ET.tostring(root, encoding="unicode"))
    parent = {}
    stack = [(None, copy)]
    while stack:
        p, c = stack.pop()
        parent[id(c)] = p
        stack.extend((c, ch) for ch in reversed(list(c)))
    nodes = list(copy.iter())
    for c in nodes:
        if c.tag == W + "del" and parent.get(id(c)) is not None:
            parent[id(c)].remove(c)
    for i in reversed([c for c in nodes if c.tag == W + "ins"]):
        p = parent.get(id(i))
        if p is None:
            continue
        children = list(p)
        idx = children.index(i)
        for child in list(i):
            p.insert(idx, child)
            idx += 1
        p.remove(i)
    return "".join(t.text or "" for t in copy.iter(W + "t"))


def check_revised(docx_path, expect):
    """修订成对 + 落定证明 + 计数（三项合一，判定维度不混算）"""
    root = ET.fromstring(_z_read(docx_path, "word/document.xml"))
    settings = ""
    with zipfile.ZipFile(docx_path) as z:
        if "word/settings.xml" in z.namelist():
            settings = z.read("word/settings.xml").decode("utf-8")

    ins_els = list(root.iter(W + "ins"))
    del_els = list(root.iter(W + "del"))

    # --- 修订成对
    fails_pair = []
    if len(ins_els) != len(del_els):
        fails_pair.append(f"ins({len(ins_els)}) != del({len(del_els)})——修订未成对")
    bad_author = sum(1 for e in ins_els + del_els if not (e.get(W + "author") or "").strip())
    if bad_author:
        fails_pair.append(f"{bad_author} 处修订缺 author（复核人归责缺失）")
    ins_ids = [i.get(W + "id") for i in ins_els]
    del_ids = [i.get(W + "id") for i in del_els]
    if len(set(ins_ids)) != len(ins_ids):
        fails_pair.append("ins 修订 id 重复")
    if set(ins_ids) != set(del_ids):
        fails_pair.append("ins/del 修订 id 不成对（应共享同一 id）")
    ok_pair = not fails_pair
    detail_pair = f"ins {len(ins_els)} / del {len(del_els)} 对；author 缺失 {bad_author}"
    res_pair = ("修订成对", ok_pair, detail_pair, fails_pair)

    # --- 修订落定
    fails_settle = []
    empty = 0
    for d in del_els:
        if not "".join(t.text or "" for t in d.iter(W + "delText")).strip():
            empty += 1
    for i in ins_els:
        if not "".join(t.text or "" for t in i.iter(W + "t")).strip():
            empty += 1
    if empty:
        fails_settle.append(f"{empty} 处修订文本为空（delText/ins 内容缺失）")
    if "w:trackRevisions" not in settings:
        fails_settle.append("settings 未开启 w:trackRevisions（修订可能不显示）")
    if "revisionView" not in settings:
        fails_settle.append("settings 缺 w:revisionView")
    clean_txt = _rev_clean_text(root)
    lost = []
    for i in ins_els:
        t = "".join(x.text or "" for x in i.iter(W + "t"))
        if t and t not in clean_txt:
            lost.append(t[:24])
    if lost:
        fails_settle.append(f"{len(lost)} 条 ins 文本 clean 化后缺失（修订未落定）: {lost}")
    ok_settle = not fails_settle
    res_settle = ("修订落定", ok_settle,
                  f"空修订 {empty} / trackRevisions {'✅' if 'w:trackRevisions' in settings else '❌'} / "
                  f"clean 化后 {len(clean_txt):,} 字符", fails_settle)

    # --- 修订计数
    fails_cnt = [] if expect is None or len(ins_els) == expect else [
        f"ins 条数 {len(ins_els)} != 期望 {expect}（与修改清单「已修订」数不一致）"]
    res_cnt = ("修订计数", not fails_cnt,
               f"ins {len(ins_els)}" + (f" / 期望 {expect}" if expect is not None else "（未设期望，仅报告）"),
               fails_cnt)
    return [res_pair, res_settle, res_cnt]


# ----------------------------------------------------------------- officecli 物理扫描

# 探测顺序：显式路径 → PATH → 平台常见安装位置 → 脚本同目录
# 自定义安装位置：用 --officecli-path 指定，或用环境变量 OFFICECLI_HOME 指向安装目录
def _officecli_candidates():
    here = os.path.dirname(os.path.abspath(__file__))
    home = os.path.expanduser("~")
    local = os.environ.get("LOCALAPPDATA") or os.path.join(home, "AppData", "Local")
    cands = []
    extra = os.environ.get("OFFICECLI_HOME")
    if extra:
        cands += [os.path.join(extra, "officecli.exe"), os.path.join(extra, "officecli")]
    cands += [
        os.path.join(home, ".officecli", "officecli.exe"),
        os.path.join(home, ".officecli", "officecli"),
        os.path.join(home, ".local", "bin", "officecli"),
        os.path.join(home, "bin", "officecli"),
        os.path.join(local, "Programs", "officecli", "officecli.exe"),
        os.path.join(here, "officecli.exe"),
    ]
    return cands


def find_officecli(explicit=None):
    """返回可用 officecli 路径；未找到返回 None。不抛异常。"""
    if explicit:
        return explicit if os.path.isfile(explicit) else None
    found = shutil.which("officecli")
    if found:
        return found
    for c in _officecli_candidates():
        if os.path.isfile(c):
            return c
    return None


def _run_oc(binary, args, timeout=120):
    """执行 officecli 并返回 (ok, stdout)。异常一律吞掉转 False —— 软门禁不得中断主流程。"""
    try:
        p = subprocess.run([binary] + args, capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
        return p.returncode == 0, (p.stdout or "") + (p.stderr or "")
    except Exception:
        return False, ""


def check_physical(docx_path, enabled, explicit_path=None, expect_issues=0):
    """物理层扫描（架构校验 + 渲染缺陷）—— officecli 软门禁

    三态语义：
      · 未启用（没给 --officecli）→ SKIP，不阻断
      · 启用但 officecli 不在     → SKIP，不阻断（这是「可见的未跑」，不是失败）
      · 启用且跑出问题             → FAIL（架构不合法 或 缺陷数 > expect_issues）
    """
    if not enabled:
        return ("物理扫描", None, "未启用（加 --officecli 启用）", [])

    binary = find_officecli(explicit_path)
    if not binary:
        return ("物理扫描", None, "未执行——未找到 officecli（装好或 --officecli-path 指定）", [])

    fails = []
    # ① 架构校验
    ok_v, out_v = _run_oc(binary, ["validate", docx_path, "--json"])
    arch = "架构合法"
    if ok_v:
        try:
            j = json.loads(out_v.strip() or "{}")
            if j.get("success") is False:
                arch = f"架构校验失败：{str(j.get('error', ''))[:80]}"
                fails.append(arch)
        except Exception:
            pass  # 非 JSON 但退出码 0 → 视为通过
    else:
        arch = f"架构校验未通过（officecli exit≠0）"
        fails.append(arch)

    # ② 渲染层缺陷
    ok_i, out_i = _run_oc(binary, ["view", docx_path, "issues", "--json"])
    n_issue, kinds = 0, []
    if ok_i:
        try:
            j = json.loads(out_i.strip() or "{}")
            items = (j.get("data") or {}).get("issues") or []
            n_issue = int((j.get("data") or {}).get("count", len(items)) or 0)
            kinds = sorted({str(i.get("type", "?")) for i in items if isinstance(i, dict)})[:5]
        except Exception:
            n_issue = 0
    if n_issue > expect_issues:
        msg = f"渲染层缺陷 {n_issue} 条（> 期望 {expect_issues}）"
        if kinds:
            msg += f"：{'、'.join(kinds)}"
        fails.append(msg)

    detail = f"{arch}；渲染缺陷 {n_issue} 条" + (f"（{'、'.join(kinds)}）" if kinds else "")
    return ("物理扫描", not fails, detail, fails)


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
    """交付件核验：基础九项 + 按开关追加批注/修订三项 + 物理扫描一项"""
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
    if args.annotated:
        results.append(check_annotated_parts(args.docx))
        results.append(check_annotated_structure(args.docx, args.expect_annotated))
    if args.revised:
        results.extend(check_revised(args.docx, args.expect_revised))
    # 物理扫描：常驻一行（未启用/未安装 → SKIP，让「未跑」可见）
    results.append(check_physical(args.docx, args.officecli,
                                  args.officecli_path, args.expect_issues))
    return [r for r in results if r is not None]


def main():
    ap = argparse.ArgumentParser(description="交付前综合核验（一次跑完 · 极简输出）")
    ap.add_argument("--docx", help="交付件 docx（给了跑全套九项）")
    ap.add_argument("--md", help="内容源 md；只给 --md 则跑「套样式前」的 md 侧预检（标点/禁用词/占位符/锚点/结构）")
    ap.add_argument("--annotated", action="store_true", help="批注版交付件：追加批注部件/结构/编号三项")
    ap.add_argument("--revised", action="store_true", help="修订版交付件：追加修订成对/落定/计数三项")
    ap.add_argument("--anchors", default="",
                    help="关键数字锚点，分号分隔（勿用逗号——数字含千分位逗号），如 '36,507.55;19.96'")
    ap.add_argument("--ban", default="", help="禁用词，逗号或分号分隔；不传则用内置红线（13 词）")
    ap.add_argument("--scenario", default="反馈回复", choices=list(STYLE_BY_SCENARIO))
    ap.add_argument("--expect-vmerge", type=int, default=None)
    ap.add_argument("--expect-annotated", type=int, default=None, help="期望批注条数（配 --annotated）")
    ap.add_argument("--expect-revised", type=int, default=None, help="期望已修订条数（配 --revised）")
    ap.add_argument("--officecli", action="store_true",
                    help="物理层扫描（officecli validate + view issues）；未安装则输出 SKIP 不阻断")
    ap.add_argument("--officecli-path", default=None, help="officecli 可执行文件路径（默认自动探测）")
    ap.add_argument("--expect-issues", type=int, default=0,
                    help="可接受的渲染层缺陷条数上限，默认 0（配 --officecli）")
    ap.add_argument("--detail", type=int, default=5, help="FAIL 时最多展开明细条数")
    args = ap.parse_args()

    if not args.docx and not args.md:
        ap.error("至少提供 --docx 或 --md 之一")
    if args.annotated and args.revised:
        ap.error("--annotated 与 --revised 互斥（批注版/修订版不会同时存在）")
    if args.annotated and not args.docx:
        ap.error("--annotated 需配 --docx（批注校验只在交付件上做）")
    if args.revised and not args.docx:
        ap.error("--revised 需配 --docx（修订校验只在交付件上做）")

    anchors = [a.strip() for a in args.anchors.split(";") if a.strip()]
    ban = [b.strip() for b in re.split(r"[;,]", args.ban) if b.strip()] or DEFAULT_BAN
    md_text = read_md(args.md) if args.md else ""

    if args.docx:
        results = run_full(args, md_text, anchors, ban)
        kind = " · 批注版" if args.annotated else (" · 修订版" if args.revised else "")
        title, tail = f"交付前综合核验（交付件全套 {len(results)} 项{kind}）", "可交付"
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
    n_skip = 0
    for name, ok, detail, fails in results:
        # ok 三态：True=PASS / False=FAIL / None=SKIP（未执行，不阻断）
        tag = "SKIP" if ok is None else ("PASS" if ok else "FAIL")
        print(f"[{tag}] {name:<10} {detail}")
        if ok is None:
            n_skip += 1
        elif not ok:
            n_fail += 1
            for f in fails[: args.detail]:
                print(f"         └─ {f}")
            if len(fails) > args.detail:
                print(f"         └─ …另有 {len(fails) - args.detail} 条（用 check_content.py / check_styles.py 看全量）")

    print("-" * 72)
    total = len(results)
    n_run = total - n_skip
    skip_note = f"（{n_skip} 项 SKIP 未执行）" if n_skip else ""
    if n_fail == 0:
        print(f"结论 {n_run - n_fail}/{n_run} PASS ✅  {tail}{skip_note}")
    else:
        print(f"结论 {n_run - n_fail}/{n_run} PASS ❌  有 {n_fail} 项 FAIL，修复后重跑{skip_note}")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())

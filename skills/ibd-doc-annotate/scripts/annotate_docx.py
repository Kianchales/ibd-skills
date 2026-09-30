#!/usr/bin/env python3
"""
ibd-doc-annotate · annotate_docx.py — 在 docx 原文上注入复核批注（Word 审阅批注）

用法:
  python annotate_docx.py --docx <原文.docx> --issues <issues.json> [--out <输出.docx>]

issues.json（数组，每元素一条复核关注点）:
{
  "author": "张敏",            // 复核人姓名（任意）；编号前缀可另给 "code": "J"
  "code":   "J",                 // 可选：编号前缀（缺省 ASCII 名取首字母；中文名建议显式提供，否则回退 U）
  "type":   "数据·正负号",        // 类型词表见 ibd-doc-review references/annotations.md §4（本脚本不校验词表）
  "sev":    "高",                 // 严重度（同词表；不校验）
  "anchor": "公司因结算货币汇率波动产生的汇兑净损失为…",  // 原文问题句段（精确子串）
  "title":  "「汇兑净损失」负值实为净收益，正负口径与措辞相悖",  // 行2 标题（一句话）
  "desc":   "……矛盾点/原文依据……",   // 行3
  "advice": "核对……后统一表述为……"      // 行4
}

行为:
  - 编号自动分配（编号前缀 code + 两位序号，如 J-01/J-02…；同前缀超 99 条顺延双字母分段
    J-99 → JA-01…，序号恒 2 位对齐门禁 LABEL_PAT），顺序 = 清单顺序
  - 锚点定位：正文段落 + 表格单元格段落；跨 run 按字符拆分注入并**保留原 run 格式**；
    段落内非文本内容（他人批注锚点/书签/超链接/w:tab·w:br 兄弟 run）与锚点外 run 原位保留，
    可在已带批注的文档上直接二次批注（新批注 id 接续既有最大 id，既有批注内容合并保留）
  - 边界：锚点段落含复杂 run（换行 w:br / 制表 w:tab / 多 w:t 的 run 等）或锚点骑跨超链接 →
    不自动注入，记入总览「未锚定」清单（人工定位），不报错中断
  - 输出：<原文名>_批注版.docx（或 --out）+ <输出>_批注总览.md
    （总览默认只产 md；如需 Word 版须显式加 --overview-docx；编号一一对应）
  - 批注正文 4 行紧凑：标签行/标题行整行加粗，问题描述/建议仅引导词加粗
  - 只注入批注，不修改原文文字

依赖：python-docx + lxml + 标准库 zipfile（补 comments 四件套）
格式单一事实源：ibd-doc-review skill references/annotations.md（本脚本只实现、不另立规则）。
"""
import argparse
import copy
import datetime
import json
import os
import sys
import zipfile

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from lxml import etree

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
CT_NS = 'http://schemas.openxmlformats.org/package/2006/content-types'
REL_NS = 'http://schemas.openxmlformats.org/package/2006/relationships'
XML_SPACE = '{http://www.w3.org/XML/1998/namespace}space'
NSMAP = {'w': W}

def _derive_code(it):
    """编号前缀推导：清单 code 字段 > ASCII 复核人名首字母 > 回退 U（提示补 code）。

    前缀语义由复核流程自定义（如 J=财务复核人），脚本不内置任何团队映射——
    方法层只认结构，人名/代号对应关系是上游清单的内容。
    """
    code = str(it.get("code") or "").strip().upper()
    code = "".join(ch for ch in code if ch.isascii() and ch.isalpha())[:2]  # 规范化：仅 A-Z、≤2 位（对齐门禁 LABEL_PAT）
    if code:
        return code
    author = str(it.get("author") or "").strip()
    if author and author[0].isascii() and author[0].isalpha():
        return author[0].upper()
    print(f"[warn] 编号前缀回退 U：author「{author}」非拉丁名且清单未提供 code 字段"
          f"（建议每条加 \"code\": \"J\" 等，规范见 ibd-doc-review references/annotations.md §3）",
          file=sys.stderr)
    return "U"


def _full_label(code, n):
    """前缀-序号合成：序号恒 2 位（对齐门禁 LABEL_PAT 的 \\d{2}，位数单一事实源在门禁侧，
    本函数只适配、不放宽门禁）。同前缀超 99 条顺延双字母分段（J-99 → JA-01…JA-99，
    单字母前缀容量 26×99）；双字母前缀无顺延空间，超 99 条直接报错提示拆分清单——
    静默改写显式前缀＝编号漂移，禁。
    """
    seg, k = divmod(n - 1, 99)
    if seg == 0:
        return f"{code}-{k + 1:02d}"
    if len(code) >= 2:
        raise ValueError(f"编号前缀 {code} 为双字母，超 99 条无法分段顺延（第 {n} 条）"
                         f"——请拆分清单或改用单字母前缀")
    if seg > 26:
        raise ValueError(f"编号前缀 {code} 分段容量穷尽（27×99=2673 条）——请拆分清单")
    return f"{code}{chr(ord('A') + seg - 1)}-{k + 1:02d}"


def assign_numbers(issues):
    """编号分配 + 结构校验（方法层只查结构必填，不做内容判断）。

    类型/严重度词表归 ibd-doc-review references/annotations.md §4 定义，本脚本不校验词表、
    不维护词表副本（复核分类属上游清单内容）；type/sev 缺省仅以「-」作显示兜底。
    """
    seen = {}
    for it in issues:
        for f in ("author", "anchor", "title"):
            if not str(it.get(f) or "").strip():
                raise ValueError(f"条目缺必填字段 {f}: {json.dumps(it, ensure_ascii=False)[:100]}")
        code = _derive_code(it)
        seen[code] = seen.get(code, 0) + 1
        it["full"] = _full_label(code, seen[code])
        it["type"] = it.get("type") or "-"
        it["sev"] = it.get("sev") or "-"
    return issues


# ---------------- 段落遍历（正文 + 表格单元格，不含页眉页脚） ----------------
def _walk_paras(container):
    for child in container:
        if child.tag == qn('w:p'):
            yield child
        elif child.tag == qn('w:tbl'):
            for row in child.findall(qn('w:tr')):
                for cell in row.findall(qn('w:tc')):
                    yield from _walk_paras(cell)


def para_text_of_runs(p_el):
    """段落内顶层 w:r 的 w:t 拼接文本。"""
    return "".join("".join(t.text or "" for t in r.findall(qn('w:t')))
                   for r in p_el if r.tag == qn('w:r'))


def _run_simple(r):
    """简单 run：除 rPr 外仅一个 w:t（可安全按字符拆分且不丢换行/制表等）。"""
    non_text = [c for c in r if c.tag != qn('w:rPr') and c.tag != qn('w:t')]
    return not non_text and len(r.findall(qn('w:t'))) == 1


# ---------------- 锚定注入（保留原 run 格式的跨 run 拆分） ----------------
def inject_range(p_el, s, e, cid):
    """
    在段落 p_el 的 [s,e) 字符区间注入一条批注锚定。
    s/e 基于顶层 w:r 的 w:t 拼接文本坐标。
    返回 (ok, reason)；锚点覆盖范围内存在复杂 run 或骑跨非 run 元素时返回 False（不注入）。
    实现：把覆盖的 run 按字符切为片段（首片段复用原元素、其余深拷贝，保留 rPr），
    在锚点起点前插 commentRangeStart、终点后插 commentRangeEnd + commentReference。
    """
    runs = [r for r in p_el if r.tag == qn('w:r')]
    texts = []
    for r in runs:
        texts.append("".join(t.text or "" for t in r.findall(qn('w:t'))))
    cum, acc = [], 0
    for t in texts:
        cum.append(acc)
        acc += len(t)
    full_len = acc
    if not (0 <= s <= e <= full_len):
        return False, "锚点越界"

    lo = hi = None
    for i, base in enumerate(cum):
        end = base + len(texts[i])
        if base <= s < end:
            lo = i
        if base < e <= end:
            hi = i
    if lo is None or hi is None or lo > hi:
        return False, "锚点未完整落在顶层 run 文本内（可能骑跨超链接等）"
    for i in range(lo, hi + 1):
        if not _run_simple(runs[i]):
            return False, "锚点覆盖复杂 run（含换行/制表/多文本段），不自动注入"

    # 逐 run 切片段：只对锚点覆盖区间 [lo, hi] 内的 run 按字符切分并重建；
    # 锚点外 run 与一切非文本内容保持原位（见下方组装说明）。
    run_segs = []  # run_segs[i] = [[seg_text, pre_marker, post_marker], ...]，仅覆盖区间的 run 非空
    for i in range(len(runs)):
        if not (lo <= i <= hi):
            run_segs.append([])
            continue
        base = cum[i]
        local = {0, len(texts[i])}
        if base < s < base + len(texts[i]):
            local.add(s - base)
        if base < e < base + len(texts[i]):
            local.add(e - base)
        cut = sorted(local)
        segs = []
        for k in range(len(cut) - 1):
            g0, g1 = base + cut[k], base + cut[k + 1]
            if g1 > g0:
                segs.append([texts[i][cut[k]:cut[k + 1]], g0 == s, g1 == e])
        run_segs.append(segs)

    # 组装（原位保留版）：pPr、锚点外的全部 run、以及一切非 run 子元素——他人批注锚点
    # （commentRangeStart/End）、书签、超链接、修订标记、w:tab/w:br 兄弟 run 等——一律原位保留；
    # 仅锚点覆盖的文本 run 被其切片替换，并在锚点首片段前插 commentRangeStart、末片段后插
    # commentRangeEnd + commentReference。
    # 此前「保留 pPr、清空其余内容流」的整段重建会静默删除同段他人批注锚点等非文本内容
    # （2026-09-25 语言复核批次实测数据丢失），已废弃。
    pPr = p_el.find(qn('w:pPr'))

    def emit_text(run, text):
        for t in run.findall(qn('w:t')):
            run.remove(t)
        t = OxmlElement('w:t')
        t.text = text
        t.set(XML_SPACE, 'preserve')
        run.append(t)
        return run

    def emit_copy(run, text):
        el = copy.deepcopy(run)
        return emit_text(el, text)

    def marker_end_els():
        ce = OxmlElement('w:commentRangeEnd')
        ce.set(qn('w:id'), str(cid))
        rr = OxmlElement('w:r')
        rpr = OxmlElement('w:rPr')
        rs = OxmlElement('w:rStyle')
        rs.set(qn('w:val'), 'CommentReference')
        rpr.append(rs)
        rr.append(rpr)
        ref = OxmlElement('w:commentReference')
        ref.set(qn('w:id'), str(cid))
        rr.append(ref)
        return [ce, rr]

    new_children = []
    run_no = -1  # runs 按文档序构建，遍历时第 N 个顶层 w:r 即 runs[N]
    for child in list(p_el):
        if child is pPr:
            new_children.append(child)
        elif child.tag == qn('w:r'):
            run_no += 1
            segs = run_segs[run_no]
            if lo <= run_no <= hi and segs:
                for k, (seg_text, pre, post) in enumerate(segs):
                    if pre:
                        cs = OxmlElement('w:commentRangeStart')
                        cs.set(qn('w:id'), str(cid))
                        new_children.append(cs)
                    # 每 run 首个片段复用原元素（保留 rPr），其余片段深拷贝
                    new_children.append(emit_text(runs[run_no], seg_text) if k == 0
                                        else emit_copy(runs[run_no], seg_text))
                    if post:
                        new_children.extend(marker_end_els())
            else:
                new_children.append(child)  # 未覆盖 run / 零宽 run：原样保留
        else:
            new_children.append(child)  # 非 run 子元素（他人批注锚点等）：原位保留

    for child in list(p_el):
        p_el.remove(child)
    for el in new_children:
        p_el.append(el)
    return True, ""


def locate_and_inject(doc, issue, cid):
    anchor = issue["anchor"]
    if not anchor:
        return False, "锚点为空"
    for p_el in _walk_paras(doc.element.body):
        text = para_text_of_runs(p_el)
        s = text.find(anchor)
        if s < 0:
            continue
        ok, reason = inject_range(p_el, s, s + len(anchor), cid)
        if ok:
            return True, None
        return False, f"锚点定位成功但注入受限：{reason}"
    return False, "正文/表格未找到锚点文本"


# ---------------- comments.xml（4 行紧凑，规范 §2） ----------------
def build_comments_xml(issues, date_iso):
    root = etree.Element('{%s}comments' % W, nsmap=NSMAP)
    for it in issues:
        c = etree.SubElement(root, '{%s}comment' % W)
        c.set('{%s}id' % W, str(it['cid']))
        c.set('{%s}author' % W, it['author'])
        c.set('{%s}date' % W, date_iso)
        c.set('{%s}initials' % W, ''.join(p[0] for p in it['author']))
        for runs in (
            [(f"【{it['full']}｜{it['type']}｜{it['sev']}】", True)],
            [(it['title'], True)],
            [("问题描述：", True), (it['desc'], False)],
            [("建议：", True), (it['advice'], False)],
        ):
            p = etree.SubElement(c, '{%s}p' % W)
            pPr = etree.SubElement(p, '{%s}pPr' % W)
            ps = etree.SubElement(pPr, '{%s}pStyle' % W)
            ps.set('{%s}val' % W, 'CommentText')
            for txt, bold in runs:
                r = etree.SubElement(p, '{%s}r' % W)
                if bold:
                    rPr = etree.SubElement(r, '{%s}rPr' % W)
                    etree.SubElement(rPr, '{%s}b' % W)
                t = etree.SubElement(r, '{%s}t' % W)
                t.text = txt
                t.set(XML_SPACE, 'preserve')
    return etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)


# ---------------- zip 补件（styles / Content_Types / rels） ----------------
def patch_styles(xml_bytes):
    root = etree.fromstring(xml_bytes)
    have_para = root.xpath('//w:style[@w:styleId="CommentText" and @w:type="paragraph"]', namespaces=NSMAP)
    have_char = root.xpath('//w:style[@w:styleId="CommentReference" and @w:type="character"]', namespaces=NSMAP)
    if not have_para:
        s = etree.SubElement(root, '{%s}style' % W)
        s.set('{%s}type' % W, 'paragraph')
        s.set('{%s}styleId' % W, 'CommentText')
        nm = etree.SubElement(s, '{%s}name' % W)
        nm.set('{%s}val' % W, 'annotation text')
        bo = etree.SubElement(s, '{%s}basedOn' % W)
        bo.set('{%s}val' % W, 'Normal')
        rPr = etree.SubElement(s, '{%s}rPr' % W)
        rf = etree.SubElement(rPr, '{%s}rFonts' % W)
        rf.set('{%s}ascii' % W, 'Times New Roman')
        rf.set('{%s}hAnsi' % W, 'Times New Roman')
        rf.set('{%s}eastAsia' % W, '宋体')
        rf.set('{%s}cs' % W, '宋体')
        sz = etree.SubElement(rPr, '{%s}sz' % W)
        sz.set('{%s}val' % W, '21')
        szCs = etree.SubElement(rPr, '{%s}szCs' % W)
        szCs.set('{%s}val' % W, '21')
    if not have_char:
        s = etree.SubElement(root, '{%s}style' % W)
        s.set('{%s}type' % W, 'character')
        s.set('{%s}styleId' % W, 'CommentReference')
        nm = etree.SubElement(s, '{%s}name' % W)
        nm.set('{%s}val' % W, 'annotation reference')
        rPr = etree.SubElement(s, '{%s}rPr' % W)
        sz = etree.SubElement(rPr, '{%s}sz' % W)
        sz.set('{%s}val' % W, '16')
    return etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)


def patch_content_types(xml_bytes):
    root = etree.fromstring(xml_bytes)
    have = root.xpath('//ct:Override[@PartName="/word/comments.xml"]', namespaces={'ct': CT_NS})
    if not have:
        ov = etree.SubElement(root, '{%s}Override' % CT_NS)
        ov.set('PartName', '/word/comments.xml')
        ov.set('ContentType', 'application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml')
    return etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)


def patch_rels(xml_bytes):
    root = etree.fromstring(xml_bytes)
    rel_type = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments'
    have = root.xpath('//r:Relationship[@Type="%s"]' % rel_type, namespaces={'r': REL_NS})
    if not have:
        ids = root.xpath('//r:Relationship/@Id', namespaces={'r': REL_NS})
        max_n = max((int(i[3:]) for i in ids if i.startswith('rId')), default=0)
        rel = etree.SubElement(root, '{%s}Relationship' % REL_NS)
        rel.set('Id', 'rId%d' % (max_n + 1))
        rel.set('Type', rel_type)
        rel.set('Target', 'comments.xml')
    return etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)


# ---------------- 总览 md ----------------
def write_overview(out_docx, issues, misses):
    base = os.path.splitext(out_docx)[0]
    out = base + "_批注总览.md"
    lines = ["# 复核批注总览", "",
             f"> 批注版：`{os.path.basename(out_docx)}`（Word/WPS 审阅面板查看，支持回复/解决流转）",
             "> 本总览与批注编号一一对应（双轨兜底）；未自动锚定条目仅在下方列出，请人工定位。", "",
             "| 编号 | 类型·严重度 | 锚点摘要 | 作者 | 状态 |",
             "|---|---|---|---|---|"]
    miss_full = {m["full"] for m in misses}
    for it in issues:
        status = "已锚定" if it["full"] not in miss_full else "未锚定 → 见下"
        anchor = it["anchor"] if len(it["anchor"]) <= 40 else it["anchor"][:40] + "…"
        lines.append(f"| {it['full']} | {it['type']}·{it['sev']} | {anchor} | {it['author']} | {status} |")
    if misses:
        lines += ["", "## 未自动锚定条目（人工定位）", ""]
        for m in misses:
            lines.append(f"- **{m['full']}**（{m['author']}）：{m['reason']}")
            lines.append(f"  - 锚点：{m['anchor']}")
            lines.append(f"  - 问题：{m['title']}")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return out


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    ap = argparse.ArgumentParser(description="docx 原文批注注入（规范：ibd-doc-review references/annotations.md）")
    ap.add_argument("--docx", required=True, help="原文 docx 路径")
    ap.add_argument("--issues", required=True, help="复核问题清单 JSON（数组）")
    ap.add_argument("--out", help="输出 docx 路径（默认 <原文名>_批注版.docx）")
    ap.add_argument("--date", default="", help="ISO8601 批注日期（默认当前 UTC）")
    ap.add_argument("--dry-run", action="store_true",
                    help="只报「命中／未锚定」统计与目标路径，**不写任何文件**（锚点质量预检）")
    ap.add_argument("--force", action="store_true",
                    help="目标文件已存在时覆盖（默认拒绝，防误盖既有交付物）")
    ap.add_argument("--overview-docx", action="store_true",
                    help="总览另产 Word 版（默认只产 md；总览 Word 版须显式要求）")
    args = ap.parse_args()

    with open(args.issues, encoding="utf-8") as fh:
        raw = json.load(fh)
    # G1 入口校验（复核链数据入口早拦）：errors 非空即退出不注入；warnings 仅提示
    from validate_issues import validate_issues
    _errs, _warns = validate_issues(raw)
    for _w in _warns:
        print(f"[WARN] {_w}")
    if _errs:
        print(f"[ERROR] issues 清单未通过入口校验（{len(_errs)} 项）——不注入，请修正后重试：")
        for _e in _errs:
            print(f"  - {_e}")
        sys.exit(2)
    try:
        issues = assign_numbers([dict(x) for x in raw])
    except ValueError as exc:
        print(f"[ERROR] 编号分配失败：{exc}")
        sys.exit(2)
    out_docx = args.out or os.path.splitext(args.docx)[0] + "_批注版.docx"
    date_iso = args.date or _now_iso()
    # 覆盖保护（2026-09-23 补）：目标已存在时默认拒绝——本脚本是投行产线里唯一直写交付件的环节，
    # 误盖既有批注版＝静默丢失上一轮复核结果。要覆盖须显式 --force。
    if (not args.dry_run) and os.path.exists(out_docx) and not args.force:
        print(f"[ERROR] 目标已存在，拒绝覆盖：{out_docx}")
        print("        如需覆盖请显式加 --force；或先用 --dry-run 预检、或改 --out 换路径。")
        return 2

    doc = Document(args.docx)
    # 既有批注探测（二次批注场景）：新批注 id 须接续既有最大 id，避免与残留批注 id 冲突；
    # 既有 comments.xml 在输出阶段合并保留（只增不改，他人批注内容不丢）。
    existing_comments_xml = None
    try:
        with zipfile.ZipFile(args.docx) as z:
            if "word/comments.xml" in z.namelist():
                existing_comments_xml = z.read("word/comments.xml")
    except OSError:
        existing_comments_xml = None
    max_existing_id = -1
    if existing_comments_xml:
        _root = etree.fromstring(existing_comments_xml)
        _ids = []
        for _c in _root:
            _v = _c.get(qn('w:id'))
            if _v is not None and str(_v).lstrip("-").isdigit():
                _ids.append(int(_v))
        max_existing_id = max(_ids, default=-1)
    for i, it in enumerate(issues):
        it["cid"] = max_existing_id + 1 + i
    misses = []
    for it in issues:
        ok, reason = locate_and_inject(doc, it, it["cid"])
        if ok:
            print(f"[OK] {it['full']} {it['author']}：{it['anchor'][:24]}…")
        else:
            misses.append({**it, "reason": reason})  # 补 reason：write_overview 渲染未锚定清单需要
            print(f"[MISS] {it['full']} {it['author']}：{reason}")

    if args.dry_run:
        print("[DRY-RUN] 未写任何文件。目标路径：%s" % out_docx)
        print("[DRY-RUN] 命中 %d 条 ／ 未锚定 %d 条（未锚定明细见上方逐条 [MISS]）"
              % (len(issues) - len(misses), len(misses)))
        print("[DRY-RUN] 正式运行将另产：<输出>_批注总览.md"
              + (" ＋ <输出>_批注总览.docx（--overview-docx）" if args.overview_docx
                 else "（默认只产 md；如需 Word 版加 --overview-docx）"))
        return 0

    tmp = out_docx + ".tmp"
    doc.save(tmp)
    with zipfile.ZipFile(tmp, "r") as z:
        items = {n: z.read(n) for n in z.namelist()}
    items["word/styles.xml"] = patch_styles(items["word/styles.xml"])
    items["[Content_Types].xml"] = patch_content_types(items["[Content_Types].xml"])
    items["word/_rels/document.xml.rels"] = patch_rels(items["word/_rels/document.xml.rels"])
    # 既有批注合并：新批注追加进既有 comments.xml（只增不改，他人批注内容不丢）；无既有批注才整体新建
    new_comments = build_comments_xml(issues, date_iso)
    if existing_comments_xml:
        _root = etree.fromstring(existing_comments_xml)
        for _c in etree.fromstring(new_comments):
            _root.append(_c)
        items["word/comments.xml"] = etree.tostring(
            _root, xml_declaration=True, encoding='UTF-8', standalone=True)
    else:
        items["word/comments.xml"] = new_comments
    with zipfile.ZipFile(out_docx, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in items.items():
            z.writestr(name, data)
    os.remove(tmp)
    overview = write_overview(out_docx, issues, misses)
    print("saved:", out_docx)
    if args.overview_docx:
        # 总览 Word 版为显式 opt-in（默认只产 md，2026-09-29 口径；原「双格式默认」已废止）
        try:
            from overview_to_docx import convert as _md2docx
        except ImportError:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from overview_to_docx import convert as _md2docx
        overview_docx = os.path.splitext(overview)[0] + ".docx"
        _md2docx(overview, overview_docx)
        print("overview:", overview, "+", overview_docx)
    else:
        print("overview:", overview)
    print(f"未锚定 {len(misses)} 条（详见总览）" if misses else "全部锚定 ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_annotations.py — 批注复核产物校验脚本（ibd-doc-review skill 附带 · 规范见 references/annotations.md）
功能（只读校验，不改文件）：
  docx 侧：
    - 部件：word/comments.xml 存在；[Content_Types].xml Override；document.xml.rels Relationship
    - 结构：comments 条数 == commentRangeStart/End/Reference 对数；cid 不重复且互相对应
    - 每条批注 4 段且无空段落（无空行）；标签行/标题行整行加粗；
      「问题描述：」「建议：」引导词 run 加粗而正文常规
    - 编号：行1 形如 【前缀-序号｜类型｜严重度】，前缀 = 1-2 个大写字母（复核流程自定义代号），全局不重复
    - 样式：styles.xml 含 CommentText（段落）与 CommentReference（字符）
  pdf 侧（--pdf，需 pymupdf 可用）：
    - 高亮注释数与问题清单条数一致；每条弹注 content 首行以 【编号｜ 开头；编号唯一
用法：
  python check_annotations.py --input <带批注.docx 或目录>
  python check_annotations.py --pdf <带注释.pdf> --expect <条数>
说明：
  - 只依赖标准库 zipfile/xml.etree（docx 侧）；pymupdf 仅 PDF 侧需要，缺失时跳过并提示
  - 任一硬性不符 → 控制台汇总 FAIL 并以退出码 1 结束，不交付
"""
import argparse
import glob
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
CT = "{http://schemas.openxmlformats.org/package/2006/content-types}"
REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
# 编号前缀无白名单：1-2 大写字母（复核流程自定义代号，如 J=财务复核人），格式由 LABEL_PAT 约束
LABEL_PAT = re.compile(r"^【([A-Z]{1,2})-(\d{2})｜(.+?)｜(高|中|低)】")
NO = []  # [(severity, msg)]


def note(sev, msg):
    NO.append((sev, msg))
    print(f"[{sev}] {msg}")


def is_bold(run):
    """run 是否加粗 —— 语义判定，不能只看 <w:b> 元素是否存在。

    <w:b/> 或 <w:b w:val="1|true|on"> → 加粗；
    <w:b w:val="0|false|off">       → **显式取消加粗**，须判为不加粗。

    实测（2026-09-11）：写作链产出的批注正文 run 常带
    `<w:b w:val="0"/>` 显式声明常规字重，旧判定会将其误判为加粗，
    导致合规批注被 FAIL（仅引导词可加粗）。属性名即 w:val，无内层前缀。
    """
    el = run.find(f"{W}rPr/{W}b")
    if el is None:
        return False
    v = el.get(f"{W}val")
    return v is None or str(v).strip() not in ("0", "false", "off")


def check_docx(path):
    print(f"=== docx: {path}")
    try:
        with zipfile.ZipFile(path) as z:
            names = set(z.namelist())
    except Exception as e:
        note("FAIL", f"无法打开 docx：{e}")
        return False

    # 1) 部件
    if "word/comments.xml" not in names:
        note("FAIL", "缺少 word/comments.xml")
        return False
    ct = z_read(path, "[Content_Types].xml").decode("utf-8")
    rels = z_read(path, "word/_rels/document.xml.rels").decode("utf-8")
    styles = z_read(path, "word/styles.xml")
    if "comments.xml" not in ct or "comments" not in ct:
        note("FAIL", "[Content_Types].xml 缺少 comments Override")
    else:
        note("INFO", "Content_Types comments Override 存在")
    if "comments.xml" not in rels:
        note("FAIL", "document.xml.rels 缺少 → comments.xml 关系")
    else:
        note("INFO", "rels → comments.xml 存在")

    root = ET.fromstring(z_read(path, "word/comments.xml"))
    comments = root.findall(f"{W}comment")
    n = len(comments)
    cids = [c.get(f"{W}id") for c in comments]
    if len(set(cids)) != n:
        note("FAIL", f"comment id 重复：{n} 条中唯一 {len(set(cids))}")
    note("INFO", f"comments 条数：{n}")

    doc = ET.fromstring(z_read(path, "word/document.xml"))
    cs = doc.findall(f".//{W}commentRangeStart")
    ce = doc.findall(f".//{W}commentRangeEnd")
    ref = doc.findall(f".//{W}commentReference")
    if not (len(cs) == len(ce) == len(ref) == n):
        note("FAIL", f"锚定对数不齐：cs={len(cs)} ce={len(ce)} ref={len(ref)} 期望={n}")
    else:
        note("INFO", f"cs/ce/ref 对数 = {n} ✅")

    # 3/4) 每条批注结构 + 加粗
    sev_prefix = ("问题描述：", "建议：")
    numbers = []
    for c in comments:
        cid = c.get(f"{W}id")
        paras = c.findall(f"{W}p")
        if len(paras) != 4:
            note("FAIL", f"cid {cid}：段落数 {len(paras)} ≠ 4（期望 4 行紧凑、无空行）")
        # 空段判定：无 w:r 或所有 run 文本为空
        empties = []
        for p in paras:
            runs = p.findall(f"{W}r")
            text = "".join(t.text or "" for r in runs for t in r.findall(f"{W}t"))
            if not text.strip():
                empties.append(p)
        if empties:
            note("FAIL", f"cid {cid}：含 {len(empties)} 个空段落（批注内禁空行）")

        def para_text(p):
            return "".join(t.text or "" for r in p.findall(f"{W}r") for t in r.findall(f"{W}t"))

        def runs_bold_state(p):
            return [(is_bold(r),
                     "".join(t.text or "" for t in r.findall(f"{W}t"))) for r in p.findall(f"{W}r")]

        texts = [para_text(p) for p in paras]
        # 行1 标签：整行加粗 + 编号格式
        rb0 = runs_bold_state(paras[0])
        if not rb0 or not all(b for b, _ in rb0):
            note("FAIL", f"cid {cid}：行1 标签行未整行加粗")
        m = LABEL_PAT.match(texts[0])
        if not m:
            note("FAIL", f"cid {cid}：行1 非 【前缀-序号｜类型｜严重度】 格式：{texts[0][:30]}")
        else:
            pre, seq, typ, sev = m.groups()
            numbers.append(f"{pre}-{seq}")
            if sev not in ("高", "中", "低"):
                note("FAIL", f"cid {cid}：严重度 {sev} 非 高/中/低")
        # 行2 标题：整行加粗
        rb1 = runs_bold_state(paras[1])
        if not rb1 or not all(b for b, _ in rb1) or not texts[1].strip():
            note("FAIL", f"cid {cid}：行2 标题行缺失或未整行加粗")
        # 行3/4 引导词加粗、正文常规
        for idx, expect_pre in ((2, "问题描述："), (3, "建议：")):
            if not texts[idx].startswith(expect_pre):
                note("FAIL", f"cid {cid}：行{idx+1} 应以「{expect_pre}」开头")
                continue
            rb = runs_bold_state(paras[idx])
            lead = rb[0] if rb else (None, "")
            if not lead[0] or not lead[1].startswith(expect_pre):
                note("FAIL", f"cid {cid}：行{idx+1} 引导词「{expect_pre}」run 未加粗")
            body_bold = [b for b, t in rb[1:] if b and t.strip()]
            if body_bold:
                note("FAIL", f"cid {cid}：行{idx+1} 正文存在加粗 run（仅引导词可加粗）")

    # 5) 编号唯一
    if len(set(numbers)) != len(numbers):
        dup = [x for x in numbers if numbers.count(x) > 1]
        note("FAIL", f"编号重复：{sorted(set(dup))}")
    else:
        note("INFO", f"编号 {len(numbers)} 个唯一 ✅：{', '.join(numbers)}")

    # 6) 样式（ElementTree 不支持 xpath and，手动遍历）
    sroot = ET.fromstring(styles)
    has_text = has_ref = False
    for st in sroot.findall(f"{W}style"):
        if st.get(f"{W}styleId") == "CommentText" and st.get(f"{W}type") == "paragraph":
            has_text = True
        if st.get(f"{W}styleId") == "CommentReference" and st.get(f"{W}type") == "character":
            has_ref = True
    if not has_text:
        note("FAIL", "styles.xml 缺 CommentText 段落样式（批注字号/字体统一依赖它）")
    if not has_ref:
        note("WARN", "styles.xml 缺 CommentReference 字符样式（批注标记上标）")
    return True


def z_read(path, name):
    with zipfile.ZipFile(path) as z:
        return z.read(name)


def check_pdf(path, expect):
    print(f"=== pdf: {path}")
    try:
        import pymupdf
    except Exception:
        note("SKIP", "pymupdf 不可用，跳过 PDF 校验（可 pip install pymupdf 后重跑）")
        return True
    doc = pymupdf.open(path)
    annots = []
    for page in doc:
        for a in page.annots() or []:
            if a.type[0] in (8, 9, 10):  # Highlight / Underline / Squiggly
                annots.append(a)
    n = len(annots)
    if expect is not None and n != expect:
        note("FAIL", f"高亮注释数 {n} ≠ 期望 {expect}")
    else:
        note("INFO", f"高亮注释数：{n}")
    numbers = []
    for a in annots:
        info = a.info or {}
        content = (info.get("content") or "").split("\n")[0]
        m = LABEL_PAT.match(content.strip())
        if not m:
            note("FAIL", f"弹注首行非编号格式：{content[:30]!r}")
        else:
            numbers.append(f"{m.group(1)}-{m.group(2)}")
    if len(set(numbers)) != len(numbers):
        note("FAIL", "PDF 弹注编号重复")
    else:
        note("INFO", f"编号 {len(numbers)} 个唯一 ✅")
    doc.close()
    return True


def main():
    ap = argparse.ArgumentParser(description="批注复核产物校验（规范见 references/annotations.md）")
    ap.add_argument("--input", help="带批注的 docx 文件或目录")
    ap.add_argument("--pdf", help="带注释的 PDF 文件")
    ap.add_argument("--expect", type=int, default=None, help="PDF 期望批注条数")
    ap.add_argument("--report", action="store_true", help="同时写出 <文件>_批注校验报告.md")
    args = ap.parse_args()

    ok = True
    report_lines = []
    if args.input:
        files = []
        if os.path.isdir(args.input):
            files = sorted(glob.glob(os.path.join(args.input, "*.docx")))
        elif os.path.isfile(args.input):
            files = [args.input]
        else:
            files = glob.glob(args.input)
        for f in files:
            report_lines.append(f"# {os.path.basename(f)}")
            NO.clear()
            check_docx(f)
            report_lines += [f"- [{s}] {m}" for s, m in NO]
            report_lines.append("")
            if any(s == "FAIL" for s, _ in NO):
                ok = False
    if args.pdf:
        report_lines.append(f"# {os.path.basename(args.pdf)}")
        NO.clear()
        check_pdf(args.pdf, args.expect)
        report_lines += [f"- [{s}] {m}" for s, m in NO]
        report_lines.append("")
        if any(s == "FAIL" for s, _ in NO):
            ok = False

    if args.report and (args.input or args.pdf):
        target = args.pdf or (files[0] if files else args.input)
        out = os.path.splitext(target)[0] + "_批注校验报告.md"
        with open(out, "w", encoding="utf-8") as fh:
            fh.write("\n".join(report_lines))
        print("report:", out)

    print("结果：", "PASS ✅" if ok else "FAIL ❌（存在硬性不符，不交付）")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

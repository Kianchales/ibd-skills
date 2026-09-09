#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ibd-doc-review · check_revisions.py — 复核修订稿只读校验门禁（规范：references/revisions.md）

用法:
  python check_revisions.py --input <修订稿.docx> [--mode revise|clean] [--expect <已修订条数>] [--report]

校验（按模式）:
  revise/both 修订版:
    1. w:ins 数量 == w:del 数量（每修订一对）
    2. ins/del 带非空 author、id 唯一且成对
    3. w:del 内含 w:delText、w:ins 内含 w:t，均非空
    4. settings 已开 trackRevisions + revisionView
    5. 落定证明：clean 化（删 del、解包 ins）后每个 ins 文本仍出现在全文
  clean 干净版:
    不含任何 w:ins / w:del 残留
  --expect N（可选）：ins 条数与 N 比对

任一 FAIL → exit 1，不交付。--report 写 <输入>_修订校验报告.md。
依赖：纯标准库（zipfile + lxml）。
"""
import argparse
import os
import sys
import zipfile
from lxml import etree

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
XML_SPACE = '{http://www.w3.org/XML/1998/namespace}space'


def load_doc(path):
    with zipfile.ZipFile(path) as z:
        doc = etree.fromstring(z.read('word/document.xml'))
        settings = ""
        if 'word/settings.xml' in z.namelist():
            settings = z.read('word/settings.xml').decode('utf-8')
    return doc, settings


def full_text(root):
    """全部 w:t 拼接（段落流，含表格内）。"""
    return "".join(t.text or "" for t in root.iter(W + 't'))


def clean_tree(doc):
    """返回接受全部修订后的文档根（删 w:del、解包 w:ins）。不影响传入树（深拷贝）。"""
    root = etree.fromstring(etree.tostring(doc))
    dels = [d for d in root.iter(W + 'del')]
    for d in dels:
        d.getparent().remove(d)
    inss = [i for i in root.iter(W + 'ins')]
    for i in reversed(inss):
        parent = i.getparent()
        idx = parent.index(i)
        for child in list(i):
            parent.insert(idx, child)
            idx += 1
        parent.remove(i)
    return root


def check(input_path, mode, expect, report):
    fails = []
    notes = []
    doc, settings = load_doc(input_path)
    ins_els = list(doc.iter(W + 'ins'))
    del_els = list(doc.iter(W + 'del'))

    if mode in ("revise", "both"):
        # 1) 数量成对
        if len(ins_els) != len(del_els):
            fails.append(f"ins({len(ins_els)}) != del({len(del_els)})——修订未成对")
        # 2) author / id（ins 与 del 成对共享同一 id：各自集合相等且各自无重复）
        bad = 0
        for e in ins_els + del_els:
            if not (e.get(W + 'author') or "").strip():
                bad += 1
        if bad:
            fails.append(f"{bad} 处修订缺 author（复核人归责缺失）")
        ins_ids = [i.get(W + 'id') for i in ins_els]
        del_ids = [i.get(W + 'id') for i in del_els]
        if len(set(ins_ids)) != len(ins_ids):
            fails.append("ins 修订 id 重复")
        if set(ins_ids) != set(del_ids):
            fails.append("ins/del 修订 id 不成对（应对共享同一 id）")
        # 3) delText / t 非空
        empty = 0
        for d in del_els:
            txt = "".join(t.text or "" for t in d.iter(W + 'delText'))
            if not txt.strip():
                empty += 1
        for i in ins_els:
            txt = "".join(t.text or "" for t in i.iter(W + 't'))
            if not txt.strip():
                empty += 1
        if empty:
            fails.append(f"{empty} 处修订文本为空（delText/ins 内容缺失）")
        # 4) settings
        if "w:trackRevisions" not in settings:
            fails.append("settings 未开启 w:trackRevisions（修订可能不显示）")
        if "revisionView" not in settings:
            fails.append("settings 缺 w:revisionView")
        # 5) 落定证明
        clean = clean_tree(doc)
        clean_txt = full_text(clean)
        lost = []
        for i in ins_els:
            t = "".join(x.text or "" for x in i.iter(W + 't'))
            if t and t not in clean_txt:
                lost.append(t[:24])
        if lost:
            fails.append(f"{len(lost)} 条 ins 文本 clean 化后缺失（修订未落定）: {lost}")
        notes.append(f"ins/del 各 {len(ins_els)} 对；clean 化后全文 {len(clean_txt)} 字")
    else:  # clean
        if ins_els or del_els:
            fails.append(f"干净版残留修订标记（ins {len(ins_els)} / del {len(del_els)}）")
        notes.append("无修订标记残留 ✅")

    if expect is not None and mode in ("revise", "both"):
        if len(ins_els) != expect:
            fails.append(f"ins 条数 {len(ins_els)} != 期望 {expect}（与修改清单「已修订」数不一致）")

    report_lines = [f"# 修订稿校验报告", "",
                    f"> 文件：`{os.path.basename(input_path)}`（mode={mode}）", ""]
    if notes:
        report_lines += ["## 检查", ""] + [f"- {n}" for n in notes]
    if fails:
        report_lines += ["", f"## FAIL（{len(fails)}）", ""] + [f"- ❌ {f}" for f in fails]
    else:
        report_lines += ["", "结果：**PASS** ✅"]
    body = "\n".join(report_lines)
    print("\n".join([f"[{'FAIL' if fails else 'OK'}] {n}" for n in notes + fails]) or "(no checks)")
    print("结果：", "FAIL ❌" if fails else "PASS ✅")
    if report:
        rep = os.path.splitext(input_path)[0] + "_修订校验报告.md"
        with open(rep, "w", encoding="utf-8") as fh:
            fh.write(body)
        print("report:", rep)
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description="复核修订稿校验门禁（规范：ibd-doc-review references/revisions.md）")
    ap.add_argument("--input", required=True, help="修订稿 docx（revise 版或 clean 版）")
    ap.add_argument("--mode", default="revise", choices=["revise", "clean"],
                    help="revise=Word 修订模式稿（默认）| clean=干净版")
    ap.add_argument("--expect", type=int, default=None, help="期望已修订条数（修改清单「已修订 N 条」）")
    ap.add_argument("--report", action="store_true", help="写校验报告 md")
    args = ap.parse_args()
    sys.exit(check(args.input, args.mode, args.expect, args.report))


if __name__ == "__main__":
    main()

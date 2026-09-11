#!/usr/bin/env python3
"""IPO 文档基本格式核对 v3（只读，不改文件）。

按「问题类型 × 严重程度」组织：HIGH=错误（须改）/ MEDIUM=警告 / LOW=提示。

组别与核对项（docx 载体，样式化后核对）：
  text  文字类（实现见 content_text.py）：
        heading_seq 标题层级序号连续性（含 第X节/第X章、问题X 自定义编号）   HIGH
        terms       用词规范性（错别字/异形词；支持外部清单扩展）            MEDIUM
        dates       日期写法统一（中文/分隔符/斜杠/连写/英文月缩写/年月）      MEDIUM
        spaces      多余空格/数字前后空格/重复标点                          HIGH
        abbr        释义简称统一（冲突/前置使用/未定义复用/引号风格）          MEDIUM-LOW
        geo         国家城市表述合规（--geo-file 外部清单驱动）              HIGH
        punctuation 中英文标点（前后字符判定）                              HIGH
  table 表格类（实现见 content_table.py）：
        table_font  字号体系（五号21pt/小五18pt，其余违规）                 HIGH
        table_align 数字单元格右对齐                                    MEDIUM
        table_empty 空单元格                                           LOW
        table_na    「不适用」标记统一性                                 MEDIUM

用法：
  python check_content.py --input <docx> [--output 报告.md]
      [--checks all | text | table | heading_seq,table_font,...]

载体：
  docx —— 样式化后跑（text 组文字规范 + table 组表格样式/结构核对）
  注：数值自洽核对（data 组：金额文本格式/数值前后一致/合计勾稽/跨表比对）
      已于 2026-09-06 迁至 ibd-quality-gates scripts/check_data.py（md/docx 双载体），
      本脚本不再承担；--checks 传入 data 组相关 id 会提示新归属。

模块结构（2026-09-11 按业务域拆组，P2-⑧）：
  content_common.py  共享基础层：Issue / docx 解析 / 中文序号基元 / 标点基元
  content_text.py    文字类 7 个核对项
  content_table.py   表格类 4 个核对项
  check_content.py   ← 本文件：核对项登记表 + 编排（run / render_report / main）
  本文件是**唯一 CLI 入口**，对外契约（参数/报告文件名/退出码）与拆组前完全一致。
"""

import argparse
import datetime
import glob
import os
import sys
from collections import Counter

from content_common import (
    SEV_LABEL,
    SEV_ORDER,
    extract_structure,
    full_text_of,
    load_docx,
    parse_tables,
)
from content_table import (
    check_table_align,
    check_table_empty,
    check_table_font,
    check_table_na,
)
from content_text import (
    check_abbr,
    check_dates,
    check_geo,
    check_heading_seq,
    check_punctuation,
    check_spaces,
    check_terms,
    load_external_rules,
    load_geo_rules,
)


# ---------------------------------------------------------------- 登记 & 主流程

CHECK_REGISTRY = [
    {"id": "heading_seq", "group": "text", "name": "标题层级序号连续性（跳号/重号/倒退）", "severity": "HIGH"},
    {"id": "terms", "group": "text", "name": "用词规范性（错别字/异形词）", "severity": "MEDIUM"},
    {"id": "dates", "group": "text", "name": "日期写法统一（十种形式识别）", "severity": "MEDIUM"},
    {"id": "spaces", "group": "text", "name": "多余空格/数字前后空格/重复标点", "severity": "HIGH"},
    {"id": "punctuation", "group": "text", "name": "中英文标点（前后字符判定）", "severity": "HIGH"},
    {"id": "abbr", "group": "text", "name": "释义简称统一（含未定义使用检出）", "severity": "MEDIUM"},
    {"id": "geo", "group": "text", "name": "国家/城市表述合规（外部清单）", "severity": "HIGH"},
    {"id": "table_font", "group": "table", "name": "表格字号体系（五号/小五）", "severity": "HIGH"},
    {"id": "table_align", "group": "table", "name": "表格数字右对齐", "severity": "MEDIUM"},
    {"id": "table_empty", "group": "table", "name": "表格空单元格", "severity": "LOW"},
    {"id": "table_na", "group": "table", "name": "不适用标记统一性", "severity": "MEDIUM"},
]

GROUPS = {"text": [], "table": []}
for _item in CHECK_REGISTRY:
    GROUPS[_item["group"]].append(_item["id"])
CHECK_BY_ID = {_item["id"]: _item for _item in CHECK_REGISTRY}


def resolve_checks(spec):
    """all / 组名 / 核对项 id（可混合逗号分隔）。返回有序 id 集合。"""
    chosen = []
    if spec in (None, "", "all"):
        return [c["id"] for c in CHECK_REGISTRY]
    tokens = [tk.strip() for tk in spec.split(",") if tk.strip()]
    for tk in tokens:
        if tk in GROUPS:
            chosen.extend(GROUPS[tk])
        elif tk in CHECK_BY_ID:
            chosen.append(tk)
        else:
            if tk in ("data", "amounts", "consistency", "calc", "cross_table"):
                print(f"[WARN] {tk} 已随 data 组迁至 ibd-quality-gates scripts/check_data.py"
                      f"——本脚本只做 text/table 组")
            else:
                print(f"[WARN] 未知核对项/组名: {tk}")
    ordered = [c["id"] for c in CHECK_REGISTRY if c["id"] in set(chosen)]
    return ordered


def run(input_path, check_ids, geo_file=None, terms_file=None):
    xmls = load_docx(input_path)
    if not xmls:
        return None
    doc = xmls["word/document.xml"]
    items = extract_structure(doc)
    tables = parse_tables(doc)
    full_text = full_text_of(doc)
    geo_rules = load_geo_rules(geo_file)
    term_rules = load_external_rules(terms_file)

    runners = {
        "heading_seq": lambda: check_heading_seq(items),
        "terms": lambda: check_terms(full_text, term_rules),
        "dates": lambda: check_dates(items),
        "spaces": lambda: check_spaces(items),
        "punctuation": lambda: check_punctuation(items),
        "abbr": lambda: check_abbr(full_text),
        "geo": lambda: check_geo(full_text, geo_rules),
        "table_font": lambda: check_table_font(tables),
        "table_align": lambda: check_table_align(tables),
        "table_empty": lambda: check_table_empty(tables),
        "table_na": lambda: check_table_na(tables),
    }
    results = {}
    for cid in check_ids:
        results[cid] = runners[cid]() if cid in runners else []
    return base_name(input_path), results


def base_name(p):
    return os.path.basename(p)


def render_report(base, check_ids, results):
    lines = ["# 投行基本格式核对报告", ""]
    lines.append(f"- **核对对象**：`{base}`")
    lines.append("- **性质**：只读核对，未对文件做任何修改")
    lines.append("- 生成：ibd-doc-review `check_content.py` v2")
    lines.append("")
    cnt = {s: 0 for s in SEV_ORDER}
    by_check_sev = {}
    for cid in check_ids:
        for it in results[cid]:
            cnt[it.severity] = cnt.get(it.severity, 0) + 1
            by_check_sev.setdefault(cid, Counter())[it.severity] += 1

    lines.append("## 核对总览（按严重程度）")
    lines.append("")
    lines.append("| 组别 | 核对项 | 错误(HIGH) | 警告(MED) | 提示(LOW) |")
    lines.append("|------|--------|-----------|-----------|-----------|")
    group_names = {"text": "文字类", "data": "数据类", "table": "表格类"}
    last_group = None
    for item in CHECK_REGISTRY:
        cid = item["id"]
        if cid not in results:
            continue
        glabel = group_names[item["group"]]
        last_group = item["group"]
        sevc = by_check_sev.get(cid, Counter())
        lines.append(f"| {glabel} | {item['name']} | {sevc.get('HIGH', 0)} | "
                     f"{sevc.get('MEDIUM', 0)} | {sevc.get('LOW', 0)} |")
    lines.append(f"| **合计** | — | **{cnt.get('HIGH', 0)}** | **{cnt.get('MEDIUM', 0)}** | "
                 f"**{cnt.get('LOW', 0)}** |")
    lines.append("")
    lines.append("> 严重程度：HIGH=错误（必须修正）；MEDIUM=警告（大概率需修正）；LOW=提示（人工酌情）。")
    lines.append("> 标注「疑似」的条目为机器初筛结果，需人工复核定性。")
    lines.append("")

    sev_block = {"HIGH": "### 🔴 错误（HIGH，须修正）",
                 "MEDIUM": "### 🟡 警告（MEDIUM，建议修正）",
                 "LOW": "### 🟢 提示（LOW，人工酌情）"}

    for sev in SEV_ORDER:
        block_items = [(cid, it) for cid in check_ids for it in results[cid]
                       if it.severity == sev]
        lines.append(sev_block[sev])
        lines.append("")
        if not block_items:
            lines.append("无。")
            lines.append("")
            continue
        lines.append("| 核对项 | 位置 | 原文/对象 | 问题 | 建议 |")
        lines.append("|---|------|----------|------|------|")
        esc = lambda s: s.replace("|", "\\|").replace("\n", " ")
        block_items.sort(key=lambda x: CHECK_BY_ID.get(x[0], {}).get("name", ""))
        for idx, (cid, it) in enumerate(block_items, 1):
            cname = CHECK_BY_ID.get(cid, {}).get("name", cid)
            lines.append(f"| {idx} | {cname} | {esc(it.location)} | {esc(it.snippet)} | "
                         f"{esc(it.problem)} | {esc(it.suggestion)} |")
        lines.append("")
    return "\n".join(lines)


def resolve_files(path):
    if os.path.isdir(path):
        return sorted(glob.glob(os.path.join(path, "*.docx")))
    if os.path.isfile(path):
        return [path]
    return glob.glob(path)


def main():
    ap = argparse.ArgumentParser(description="IPO 文档基本格式核对 v3（只读，不改文件）")
    ap.add_argument("--input", required=True,
                    help="docx 文件路径（样式化后；支持 glob）")
    ap.add_argument("--output", default=None, help="核对报告 md 输出路径（默认 <input>_格式核对报告.md）")
    ap.add_argument("--checks", default="all",
                    help="all 或 组名(text/table) 或核对项 id，可组合逗号分隔，"
                         "如 --checks text,table 或 --checks table_font,geo")
    ap.add_argument("--geo-file", default=None,
                    help="国家/城市敏感词清单 JSON：[{\"term\":\"...\",\"note\":\"...\",\"suggestion\":\"...\"}]")
    ap.add_argument("--terms-file", default=None,
                    help="术语规则清单 JSON 扩展：[{\"pattern\":\"...\",\"problem\":\"...\",\"suggestion\":\"...\"}]")
    args = ap.parse_args()

    files = resolve_files(args.input)
    if not files:
        print(f"[ERROR] 未找到 docx: {args.input}")
        sys.exit(1)

    check_ids = resolve_checks(args.checks)
    exit_ok = True
    for f in files:
        result = run(f, check_ids, geo_file=args.geo_file, terms_file=args.terms_file)
        if result is None:
            exit_ok = False
            continue
        base, results = result
        report = render_report(base, check_ids, results)
        out = args.output or os.path.splitext(f)[0] + "_格式核对报告.md"
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(report)

        summary_parts = []
        sev_cnt = Counter()
        for cid in check_ids:
            for it in results[cid]:
                sev_cnt[it.severity] += 1
        for sev in SEV_ORDER:
            label = SEV_LABEL[sev]
            mark = "✅ 0" if sev_cnt.get(sev, 0) == 0 else f"⚠️ {sev_cnt[sev]}"
            summary_parts.append(f"{label}: {mark}")
        print(f"\n=== 格式核对：{os.path.basename(f)} ===")
        for line_txt in summary_parts:
            print(f"  {line_txt}")
        print(f"  → 报告已写入：{out}")

    sys.exit(0 if exit_ok else 2)


if __name__ == "__main__":
    main()

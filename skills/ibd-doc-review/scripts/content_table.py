#!/usr/bin/env python3
"""格式核对 · 表格类核对域（`--checks table` 组）。

归属：本模块原为 `check_content.py` 的「核对项：表格类」一段，
2026-09-11 按业务域拆组时独立成文件（P2-⑧）。

收录 4 个核对项（与 `check_content.py` 的 `CHECK_REGISTRY` 一一对应）：
  · `table_font`   表格字号体系（五号 21 / 小五 18）        HIGH
  · `table_align`  表格数字右对齐                            MEDIUM
  · `table_empty`  表格空单元格（全文汇总提示）               LOW
  · `table_na`     「不适用」标记统一性                       MEDIUM

**依赖 docx 样式字段**：本组依赖单元格的 `w:sz` 与段落 `w:jc`，
故须在**样式化 docx** 上跑（md 载体下不适用）。
"""

import re
from collections import Counter

from content_common import Issue


# ---------------------------------------------------------------- table_font

FONT_OK_SIZES = {21, 18}   # 半点值：21 = 10.5pt 五号；18 = 9pt 小五


def _is_formal_data_table(tbl):
    """正式数据表判定（2026-08-27 裁定）：行数≤2（封面提示框）或整表无数字
    （签字页/人名表）不参照正文表格规范——豁免字号与对齐检查。"""
    rows = tbl["rows"]
    if len(rows) <= 2:
        return False
    joined = "".join(c["text"] for row in rows for c in row)
    return bool(re.search(r"\d", joined))


def check_table_font(tables):
    issues = []
    for tbl in tables:
        if not _is_formal_data_table(tbl):
            continue
        bad_by_size = Counter()
        example = None
        for ri, row in enumerate(tbl["rows"]):
            for ci, cell in enumerate(row):
                if not cell["text"]:
                    continue
                for sz in cell["sizes"]:
                    if sz in FONT_OK_SIZES:
                        continue
                    pt = sz / 2
                    bad_by_size[f"{pt:g}pt(sz={sz})"] += 1
                    if example is None:
                        example = (ri + 1, ci + 1, cell["text"][:16], f"{pt:g}pt")
        if bad_by_size:
            detail = "、".join(f"{k}×{v}" for k, v in bad_by_size.most_common())
            ex_txt = (f"，如 行{example[0]} 列{example[1]}「{example[2]}」为 {example[3]}"
                      if example else "")
            issues.append(Issue(
                "table_font", "表格字号体系",
                f"表{tbl['no']}" + (f"（首行『{tbl['head']}』）" if tbl.get("head") else ""),
                detail,
                "IPO 表格字号应统一为五号（10.5pt）；放不下可用小五（9pt）" + ex_txt,
                "将违规字号调整为五号或小五", "HIGH"))
    return issues


# ---------------------------------------------------------------- table_align


def _is_numeric_like(cell):
    t = cell["text"]
    if not t:
        return False
    core = re.sub(r"[（）()\u4e00-\u9fff]", "", t)
    return bool(re.fullmatch(r"-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?\d{4,}(?:\.\d+)?", core))


def check_table_align(tables):
    issues = []
    examples = Counter()
    sample_cell = None
    for tbl in tables:
        if not _is_formal_data_table(tbl):
            continue
        for ri, row in enumerate(tbl["rows"]):
            for ci, cell in enumerate(row):
                if ci == 0 or not _is_numeric_like(cell):
                    continue
                non_right = [p for p in cell["paras"]
                             if p["align"] not in ("right", None)]
                if non_right:
                    examples[(tbl["no"],)] += 1
                    if sample_cell is None:
                        sample_cell = (tbl["no"], ri + 1, ci + 1, cell["text"][:16])
    if examples:
        detail = "、".join(f"表{k}×{v}" for k, v in examples.most_common())
        sc = (f"，如 表{sample_cell[0]} 行{sample_cell[1]} 列{sample_cell[2]}"
              f"「{sample_cell[3]}」") if sample_cell else ""
        issues.append(Issue(
            "table_align", "表格数字右对齐", detail + sc,
            "部分数字单元格未右对齐",
            "表格内会计数字建议右对齐（参考 check_content 的规则来源：rules.md 表格 v2）", "MEDIUM"))
    return issues


# ---------------------------------------------------------------- table_empty


def check_table_empty(tables):
    """空单元格（2026-08-27 裁定：不再逐表报警告，改为全文 1 条汇总提示）。

    2026-09-10 补充：排除 vMerge 续格（continue）——纵向合并的续格本就无文字，
    计入会产生误报（实测：合并「行业共性因素」「公司特有因素」后仍被报 3 个空格）。
    """
    issues = []
    total_all = 0
    affected = 0
    table_names = []
    for tbl in tables:
        empty_rows = Counter()
        for ri, row in enumerate(tbl["rows"]):
            for ci, cell in enumerate(row):
                # vMerge 续格（continue）本就无文字，不计为空单元格
                if cell["text"] == "" and cell.get("vmerge") != "continue":
                    empty_rows[(ri + 1)] += 1
        if empty_rows:
            total = sum(empty_rows.values())
            total_all += total
            affected += 1
            table_names.append(f"表{tbl['no']}" + (f"（首行『{tbl['head']}』）" if tbl.get("head") else ""))
    if total_all:
        detail_show = "、".join(table_names[:8]) + ("…等" if len(table_names) > 8 else "")
        issues.append(Issue(
            "table_empty", "表格空单元格（汇总提示）",
            f"共 {affected} 张表、{total_all} 个空单元格：" + detail_show,
            f"空单元格共 {total_all} 个（{affected} 张表）",
                "如为无内容建议统一以「—」填充；确属留白可忽略", "LOW"))
    return issues


# ---------------------------------------------------------------- table_na

NA_TOKENS_GROUPS = {
    "长破折号": ["—"],
    "短横线": ["-", "－"],
    "斜杠": ["/"],
    "文字类": ["不适用", "N/A", "N.A.", "无"],
}


def check_table_na(tables):
    issues = []
    for tbl in tables:
        na_counter = Counter()
        for row in tbl["rows"]:
            for cell in row:
                t = cell["text"]
                if t in [tok for toks in NA_TOKENS_GROUPS.values() for tok in toks]:
                    na_counter[t] += 1
        distinct = list(na_counter.keys())
        if len(distinct) > 1:
            merged = {}
            for gname, tokens in NA_TOKENS_GROUPS.items():
                used = [k for k in distinct if k in tokens]
                c = sum(v for k, v in na_counter.items() if k in tokens)
                if c:
                    merged[gname] = (c, used)
            if len(merged) > 1:
                detail = "、".join(f"{g}{'/'.join(tk)}×{c}" for g, (c, tk) in merged.items())
                issues.append(Issue(
                    "table_na", "表格填写（标记统一性）",
                    f"表{tbl['no']}" + (f"（首行『{tbl['head']}』）" if tbl.get("head") else ""), detail,
                    "同一表内「不适用/无内容」标记符号混用",
                    "建议全表统一一种标记（通常「—」或「不适用」）", "MEDIUM"))
    return issues

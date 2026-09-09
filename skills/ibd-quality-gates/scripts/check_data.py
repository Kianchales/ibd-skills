#!/usr/bin/env python3
"""数值自洽核对器（data 组：金额文本格式 / 数值前后一致 / 合计勾稽 / 跨表比对）。

归属（2026-09-06 裁定）：本脚本原为 ibd-doc-review check_content.py 的 data 组。
「数值一致/勾稽属内容层自洽关切——发现问题要回头改内容」，故连同 md 前端一并迁入
ibd-quality-gates，与 G1 裸数字粗筛同属内容层数字门；docx 的样式/结构核对
（text/table 组）留在 ibd-doc-review check_content.py。逻辑单一事实源 = 本脚本。

组别与核对项（data 数据类）：
  amounts     金额千分位与两位小数（豁免 %、文号/编码、标准号、地址要素等）  MEDIUM
  consistency 同名指标数值前后一致                                        MEDIUM
  calc        表格合计行求和 / 占比列合计≈100%                             HIGH
  cross_table 跨表同名科目数值比对                                        MEDIUM

用法：
  python check_data.py --input <文档.md|文档.txt|文档.docx>
      [--output 报告.md] [--checks all | data | amounts,consistency,calc,cross_table]

载体：
  md/txt —— 写作链草稿阶段数值一致门（①'：套样式前跑，改 md 零排版成本）
  docx  —— 正式稿复核（只读：zipfile 抽段落文本流 + 表格文本矩阵，不读样式字段）

输出：
  终端汇总（HIGH=错误 / MEDIUM=警告 / LOW=提示）+ 报告 md（默认 <input>_数据核对报告.md）
  退出码：0=无 HIGH 命中；1=存在 HIGH 命中；2=文件/参数错误
"""
import argparse
import glob
import os
import re
import sys
import zipfile
from collections import Counter

# ---------------------------------------------------------------- Issue 结构


class Issue:
    def __init__(self, check_id, check_name, location, snippet, problem,
                 suggestion="", severity="MEDIUM"):
        self.check_id = check_id
        self.check_name = check_name
        self.location = location
        self.snippet = snippet
        self.problem = problem
        self.suggestion = suggestion
        self.severity = severity


SEV_ORDER = ["HIGH", "MEDIUM", "LOW"]
SEV_LABEL = {"HIGH": "错误", "MEDIUM": "警告", "LOW": "提示"}

# ---------------------------------------------------------------- 载体前端
# items = [(kind, info)]：kind ∈ body/cell；info.text = 段落/单元格文本
# tables = [{"no","rows","head"}]：row = [cell dict]，cell 含 text/raw/sizes/paras
# （sizes/paras 恒为空列表——本脚本只读文本，不读 docx 样式字段）

MD_TABLE_SEP_RE = re.compile(r"^\s*\|[\s:\-|]*\|\s*$")


def load_text(path):
    """md/txt → (items, tables)：行文本 → body，管道表格块 → tables（保序）。"""
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    items, tables, tbl_no = [], [], 0
    i, n = 0, len(lines)
    while i < n:
        stripped = lines[i].strip()
        # 表格块：当前行以 | 开头且下一行是分隔行（|--|--|）
        if stripped.startswith("|") and i + 1 < n and MD_TABLE_SEP_RE.match(lines[i + 1]):
            block = []
            while i < n and lines[i].strip().startswith("|"):
                block.append(lines[i].strip())
                i += 1
            rows = []
            for bl in block:
                if MD_TABLE_SEP_RE.match(bl):
                    continue
                cells = [c.strip() for c in bl.strip().strip("|").split("|")]
                rows.append([{"text": c, "raw": c, "sizes": [], "paras": []}
                             for c in cells])
            if rows:
                tbl_no += 1
                head_snips = []
                for row in rows[:2]:
                    for cell in row:
                        if cell["text"]:
                            head_snips.append(cell["text"][:14])
                    if head_snips:
                        break
                tables.append({"no": tbl_no, "rows": rows,
                               "head": ("｜".join(head_snips[:3])) if head_snips else ""})
                for row in rows:
                    for cell in row:
                        if not cell["text"]:
                            continue
                        items.append(("cell", {"kind": "cell", "text": cell["text"],
                                               "style": None, "align": None,
                                               "table_no": tbl_no}))
            continue
        if stripped:
            items.append(("body", {"kind": "body", "text": stripped,
                                   "style": None, "align": None}))
        i += 1
    return items, tables


_W_T_RE = re.compile(r"<w:t[^>]*>([^<]*)</w:t>")
_ROW_RE = re.compile(r"<w:tr\b[^>]*>.*?</w:tr>", re.S)
_CELL_RE = re.compile(r"<w:tc\b[^>]*>.*?</w:tc>", re.S)
# 顶层块保序捕获：w:tbl 整体 或 w:p（表格内部段落已被 tbl 分支整体吃掉，不会重复计）
_BLOCK_RE = re.compile(r"<w:tbl\b[^>]*>.*?</w:tbl>|<w:p\b[^>]*>.*?</w:p>", re.S)


def _w_text(fragment):
    return "".join(_W_T_RE.findall(fragment))


def load_docx(path):
    """docx → (items, tables)：仅抽段落文本流 + 表格文本矩阵（data 组所需）。

    与 ibd-doc-review 的样式化解析无关——本脚本只读文本，不依赖 pStyle/jc 等
    样式字段，样式化与否均可跑。"""
    try:
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[ERROR] 读取失败 {path}: {e}")
        return None
    items, tables, tbl_no = [], [], 0
    for mo in _BLOCK_RE.finditer(xml):
        blk = mo.group(0)
        if blk.startswith("<w:tbl"):
            tbl_no += 1
            rows = []
            for rmo in _ROW_RE.finditer(blk):
                cells = [_w_text(tc) for tc in _CELL_RE.findall(rmo.group(0))]
                rows.append([{"text": c, "raw": c, "sizes": [], "paras": []}
                             for c in cells])
            head_snips = []
            for row in rows[:2]:
                for cell in row:
                    if cell["text"]:
                        head_snips.append(cell["text"][:14])
                if head_snips:
                    break
            tables.append({"no": tbl_no, "rows": rows,
                           "head": ("｜".join(head_snips[:3])) if head_snips else ""})
            for row in rows:
                for cell in row:
                    if not cell["text"]:
                        continue
                    items.append(("cell", {"kind": "cell", "text": cell["text"],
                                           "style": None, "align": None,
                                           "table_no": tbl_no}))
        else:
            t = _w_text(blk).strip()
            if t:
                items.append(("body", {"kind": "body", "text": t,
                                       "style": None, "align": None}))
    return items, tables


# ---- amounts 金额文本格式（千分位/两位小数；豁免 % 与文号/编码）

RE_NO_THOUSANDS = re.compile(r"(?<![\d,.%])(\d{5,9})(?=元|万元|亿元|[^\d]|$)")
RE_BAD_DECIMALS = re.compile(r"\d{1,3}(?:,\d{3})+\.(\d)(?![\d%])")
DOC_CODE_RE = re.compile(r"^\d{6,8}$")


def _is_percent_after(text, end):
    return text[end:].lstrip(" ").startswith("%")


def check_amounts(items):
    issues = []
    seen = set()
    for i, (kind, info) in enumerate(items):
        text = info["text"]
        if not text:
            continue
        work = re.sub(r"\d+(?:[,.]\d+)*\s*%",
                      lambda mm: "%" * len(mm.group(0)), text)
        where = ("表格" + f"表{info['table_no']}") if kind == "cell" else (f"正文#{i + 1}")

        for m in RE_NO_THOUSANDS.finditer(work):
            frag = m.group(0)
            key = (where, frag, m.start())
            if key in seen:
                continue
            seen.add(key)
            if DOC_CODE_RE.match(frag):
                continue  # 文号/编码豁免（含日期连写，由 dates 项处理）
            # 标准号豁免（2026-08-27 裁定）：GB/GB/T/ISO/Q/DB… 后接数字串属标准编号非金额
            prefix = text[max(0, m.start() - 10):m.start()]
            if re.search(r"[A-Za-z]{1,4}(?:/[A-Za-z]{1,4})?\s*$", prefix):
                continue
            # 地址要素豁免（2026-08-27 裁定）：…路6号105室-40627（集中办公区）等地址数字段
            if re.search(r"[路街号室栋层弄巷门]", prefix):
                continue
            # 连字符/波浪线分隔的编号段豁免（如 105室-40627）
            if prefix.rstrip()[-1:] in ("-", "—", "~"):
                continue
            # 编码串豁免：数字后紧跟字母（如 84025S11267R0SC）
            after_ch = text[m.end()] if m.end() < len(text) else ""
            if after_ch.isalpha():
                continue
            # # 前缀编号豁免（如 #72897）
            if prefix.rstrip()[-1:] == "#":
                continue
            # 案号/文号豁免：数字后接「号」（如 民初11336号）
            if text[m.end():m.end() + 2].lstrip().startswith("号"):
                continue
            note = ""
            if len(frag) >= 8:
                note = "（长数字串，若为文号/编码可忽略本条）"
            ctx_l = max(0, m.start() - 12)
            snippet = text[ctx_l:m.end() + 10].replace("\n", "")
            issues.append(Issue(
                "amounts", "金额数字（千分位/两位小数）", where + f"「…{snippet[:26]}…」",
                frag, "位数较多的数字未加千分位分隔符" + note, "添加千分位并核对是否需保留两位小数",
                "MEDIUM"))

        for m in RE_BAD_DECIMALS.finditer(work):
            frag_raw = text[m.start():m.end()] if m.start() < len(text) else ""
            frag = work[m.start():m.end()]
            key = (where, frag, m.start())
            if key in seen:
                continue
            seen.add(key)
            if _is_percent_after(text, m.end()):
                continue  # 百分比豁免
            ctx_l = max(0, m.start() - 12)
            snippet = text[ctx_l:m.end() + 10].replace("\n", "")
            issues.append(Issue(
                "amounts", "金额数字（千分位/两位小数）", where + f"「…{snippet[:26]}…」",
                frag, "带千分位的金额仅保留一位小数", "补齐至两位小数（如 .50）", "MEDIUM"))
    return issues


# ---- consistency 数值前后一致（同名指标不同值）

METRIC_VAL_RE = re.compile(
    r"([\u4e00-\u9fffA-Za-z][\u4e00-\u9fffA-Za-z0-9（）]{1,19}?(?:营业收入|净利润|净利总额|归母净利润|总资产|总负债|净资产|所有者权益|货币资金|应收账款|存货|总股本|股本))"
    r"[^\d\-]{0,6}(-?[\d,]+\.[\d]{2}|-?\d{4,}(?:,\d{3})*(?:\.\d+)?)\s*(万元|亿元|元|万|%)")


def check_consistency(items):
    metrics = {}
    issues = []
    for i, (kind, info) in enumerate(items):
        t = info["text"]
        if not t:
            continue
        for m in METRIC_VAL_RE.finditer(t):
            name, val, unit = m.group(1), m.group(2), m.group(3)
            # 千分位去掉再比较数值；保持展示为原文片段
            norm_val = val.replace(",", "").rstrip(".")
            try:
                fv = float(norm_val)
                if unit == "万元":
                    fv *= 10000
                elif unit == "亿元":
                    fv *= 100000000
            except ValueError:
                continue
            key = name[-14:]
            metrics.setdefault((key, unit), []).append(
                {"pos": i, "raw": m.group(0)[:40], "val": fv})
    for (name_key, unit), records in metrics.items():
        uniq_vals = {round(r["val"], 4) for r in records}
        if len(uniq_vals) > 1:
            vals_disp = " / ".join(str(r["val"]) + unit for r in records[:6])
            positions = ", ".join(f"#{r['pos'] + 1}段" for r in records[:6])
            issues.append(Issue(
                "consistency", "指标数值前后一致",
                f"指标「{name_key}」（单位{unit}，出现于 {positions}）",
                vals_disp,
                f"同名指标在不同位置数值不同（共 {len(records)} 处、{len(uniq_vals)} 个不同取值），疑似前后不一致——可能是口径差异，请人工核实",
                "核实口径一致后统一数值，或在表述中明确口径差异", "MEDIUM"))
    return issues


# ---- calc 表格合计行求和 / 占比列合计≈100%

def _to_num(s):
    s = s.replace(",", "").replace("%", "").strip().rstrip("。")
    try:
        return float(s)
    except ValueError:
        return None


def check_calc(tables):
    issues = []
    for tbl in tables:
        no = tbl["no"]
        rows = tbl["rows"]
        texts = [[c["text"] for c in row] for row in rows]
        tbl_loc = f"表{no}" + (f"（首行『{tbl['head']}』）" if tbl.get("head") else "")

        # (a) 合计行求和校验（其余数据行列和 vs 合计行；×100 差异视为单位口径问题）
        for ri, trow in enumerate(texts):
            if not any(("合计" in c) or ("总计" in c) for c in trow if isinstance(c, str)):
                continue
            header_rows = 1 if ri > 0 else 0
            data_rows = [r2 for ri2, r2 in enumerate(texts)
                         if ri2 >= header_rows and ri2 != ri and any(c.strip() for c in r2)]
            # 排除小计/中间汇总行（2026-08-27 裁定：小计行含数值，作分项会重复计数）
            data_rows = [r2 for r2 in data_rows
                         if not any(("小计" in c) or ("其中" in c) or ("减：" in c)
                                    or ("加：" in c) or ("剔除" in c)
                                    for c in r2 if isinstance(c, str))]
            if len(data_rows) < 2:
                continue
            bad_cols = []
            for ci in range(len(trow)):
                col_total = _to_num(trow[ci])
                if col_total is None:
                    continue
                parts = []
                ok_all = True
                for drow in data_rows:
                    v = _to_num(drow[ci]) if ci < len(drow) else None
                    if v is None:
                        ok_all = False
                        break
                    parts.append(v)
                if not ok_all or not parts:
                    continue  # 该列存在非数值单元格，跳过（无法可靠求和）
                s = round(sum(parts), 4)
                tol = max(0.02, abs(col_total) * 0.001)
                if abs(s - col_total) > tol:
                    bad_cols.append((ci, s, col_total))
            if not bad_cols:
                continue
            # 单位口径差异识别：仅分项之和恰为合计值的 100 倍（小数 vs 百分数）时降级
            unit_issue = []
            real_bad = []
            for bc in bad_cols:
                ci, s, tot = bc
                if s and abs(s - tot * 100) <= max(0.02, abs(tot * 100) * 0.001):
                    unit_issue.append(bc)   # 小数 vs 百分数 口径
                else:
                    real_bad.append(bc)
            if unit_issue:
                ci, s, tot = unit_issue[0]
                issues.append(Issue(
                    "calc", "表格合计与占比计算校验",
                    f"{tbl_loc} 合计行第{ci + 1}列",
                    f"分项之和 {s:g} 为合计值 {tot:g} 的 100 倍",
                    "疑似单位/口径不一致（分项与合计数量级差异过大），请人工核实",
                    "MEDIUM"))
            for ci, s, tot in real_bad[:3]:
                issues.append(Issue(
                    "calc", "表格合计与占比计算校验",
                    f"{tbl_loc} 合计行（第{ri + 1}行）第{ci + 1}列",
                    f"分项之和 {s:g} ≠ 合计值 {tot:g}",
                    "疑似计算错误或分项有遗漏（容差已计入四舍五入），请人工复核",
                    "重新计算合计或补充分项", "HIGH"))

        # (b) 占比列合计 ≈100%
        ncols = max((len(r) for r in texts), default=0)
        for ci in range(ncols):
            pct_vals = []
            has_header = False
            for ri, trow in enumerate(texts):
                if any(("小计" in c) or ("其中" in c) for c in trow if isinstance(c, str)):
                    pct_vals.append(None)
                    continue
                if ci >= len(trow):
                    pct_vals.append(None)
                    continue
                txt = trow[ci].strip()
                if any(k in txt for k in ("比例", "占比", "%")):
                    has_header = True
                v = _to_num(txt)
                if "%" in txt or (txt.endswith("%")):
                    v = _to_num(txt.replace("%", ""))
                    pct_vals.append(v if v is None else v)
                    continue
                if "占比" in (texts[0][ci] if texts and ci < len(texts[0]) else ""):
                    pct_vals.append(v)
                else:
                    pct_vals.append(None)
            nums = [v for v in pct_vals if v is not None]
            if has_header and len(nums) >= 3:
                ssum = round(sum(nums), 2)
                if abs(ssum - 100.0) > 1.0:
                    issues.append(Issue(
                        "calc", "表格合计与占比计算校验",
                        f"{tbl_loc} 第{ci + 1}列（占比列）",
                        f"占比合计 {ssum:g}% ≠ 100%（±1%）",
                        "疑似占比计算错误或有遗漏项，请人工复核", "HIGH"))
    return issues


# ---- cross_table 同名科目跨表数值比对

def check_cross_table(tables):
    first_col_values = {}
    for tbl in tables:
        seen_in_this_table = set()
        for row in tbl["rows"]:
            if not row:
                continue
            key = row[0]["text"]
            if not key or key in seen_in_this_table:
                continue
            seen_in_this_table.add(key)
            vals = tuple(_to_num(c["text"]) for c in row[1:])
            first_col_values.setdefault(key, []).append((tbl["no"], vals))

    issues = []
    for key, occurrences in sorted(first_col_values.items()):
        distinct = {(vals) for _, vals in occurrences if all(v is not None for v in vals)}
        tables_involved = [no for no, _ in occurrences]
        if len(distinct) > 1 and len(tables_involved) > 1:
            disp = " / ".join(str(list(v))[:60] for _, v in occurrences[:4])
            issues.append(Issue(
                "cross_table", "跨表同名科目勾稽", f"科目「{key}」出现在表 {'、'.join('表'+str(n) for n in tables_involved)}",
                f"各行数值不一致：{disp}",
                "疑似勾稽关系差异——可能是口径/期间不同属正常，请人工核实", "MEDIUM"))
    return issues


# ---------------------------------------------------------------- 注册与调度

CHECK_REGISTRY = [
    {"id": "amounts", "group": "data", "name": "金额千分位与两位小数", "severity": "MEDIUM"},
    {"id": "consistency", "group": "data", "name": "指标数值前后一致", "severity": "MEDIUM"},
    {"id": "calc", "group": "data", "name": "表格合计与占比计算校验", "severity": "HIGH"},
    {"id": "cross_table", "group": "data", "name": "跨表同名科目勾稽比对", "severity": "MEDIUM"},
]

GROUPS = {"data": [c["id"] for c in CHECK_REGISTRY]}
CHECK_BY_ID = {c["id"]: c for c in CHECK_REGISTRY}


def resolve_checks(spec):
    """all / data / 核对项 id（逗号分隔）。返回有序 id 集合。"""
    if spec in (None, "", "all", "data"):
        return [c["id"] for c in CHECK_REGISTRY]
    chosen = []
    tokens = [tk.strip() for tk in spec.split(",") if tk.strip()]
    for tk in tokens:
        if tk in CHECK_BY_ID:
            chosen.append(tk)
        else:
            print(f"[WARN] 未知核对项: {tk}（可选: {', '.join(c['id'] for c in CHECK_REGISTRY)}）")
    return [c["id"] for c in CHECK_REGISTRY if c["id"] in set(chosen)]


def run(input_path, check_ids):
    """按扩展名分流载体，跑 data 组核对。返回 (base, results) 或 None。"""
    if str(input_path).lower().endswith((".md", ".txt", ".markdown")):
        loaded = load_text(input_path)
    else:
        loaded = load_docx(input_path)
    if loaded is None:
        return None
    items, tables = loaded

    runners = {
        "amounts": lambda: check_amounts(items),
        "consistency": lambda: check_consistency(items),
        "calc": lambda: check_calc(tables),
        "cross_table": lambda: check_cross_table(tables),
    }
    results = {}
    for cid in check_ids:
        results[cid] = runners[cid]() if cid in runners else []
    return os.path.basename(input_path), results


def render_report(base, check_ids, results):
    lines = ["# 数值自洽核对报告（data 组）", ""]
    lines.append(f"- **核对对象**：`{base}`")
    lines.append("- **性质**：只读核对，未对文件做任何修改")
    lines.append("- 生成：ibd-quality-gates `check_data.py`（数值一致/勾稽/金额文本格式门）")
    lines.append("- 归属：原 ibd-doc-review check_content.py data 组迁入（2026-09-06），逻辑单一事实源在本脚本")
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
    for item in CHECK_REGISTRY:
        cid = item["id"]
        if cid not in results:
            continue
        sevc = by_check_sev.get(cid, Counter())
        lines.append(f"| 数据类 | {item['name']} | {sevc.get('HIGH', 0)} | "
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
    esc = lambda s: s.replace("|", "\\|").replace("\n", " ")

    for sev in SEV_ORDER:
        block_items = [(cid, it) for cid in check_ids for it in results[cid]
                       if it.severity == sev]
        lines.append(sev_block[sev])
        lines.append("")
        if not block_items:
            lines.append("无。")
            lines.append("")
            continue
        lines.append("| # | 核对项 | 位置 | 原文/对象 | 问题 | 建议 |")
        lines.append("|---|--------|------|----------|------|------|")
        block_items.sort(key=lambda x: CHECK_BY_ID.get(x[0], {}).get("name", ""))
        for idx, (cid, it) in enumerate(block_items, 1):
            cname = CHECK_BY_ID.get(cid, {}).get("name", cid)
            lines.append(f"| {idx} | {cname} | {esc(it.location)} | {esc(it.snippet)} | "
                         f"{esc(it.problem)} | {esc(it.suggestion)} |")
        lines.append("")
    return "\n".join(lines)


def resolve_files(path):
    if os.path.isdir(path):
        return sorted(glob.glob(os.path.join(path, "*.md")) +
                      glob.glob(os.path.join(path, "*.txt")) +
                      glob.glob(os.path.join(path, "*.docx")))
    if os.path.isfile(path):
        return [path]
    return glob.glob(path)


def main():
    ap = argparse.ArgumentParser(description="数值自洽核对（data 组：金额文本格式/数值一致/合计勾稽/跨表比对，只读）")
    ap.add_argument("--input", required=True,
                    help="md/txt（草稿阶段）或 docx（正式稿）；支持 glob/目录")
    ap.add_argument("--output", default=None,
                    help="核对报告 md 输出路径（默认 <input>_数据核对报告.md）")
    ap.add_argument("--checks", default="data",
                    help="all/data 或核对项 id 逗号分隔（amounts,consistency,calc,cross_table）")
    args = ap.parse_args()

    files = resolve_files(args.input)
    if not files:
        print(f"[ERROR] 未找到可核对文件: {args.input}")
        sys.exit(2)

    check_ids = resolve_checks(args.checks)
    if not check_ids:
        print("[ERROR] 无可执行的核对项")
        sys.exit(2)

    has_high = False
    for f in files:
        result = run(f, check_ids)
        if result is None:
            continue
        base, results = result
        report = render_report(base, check_ids, results)
        out = args.output or os.path.splitext(f)[0] + "_数据核对报告.md"
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(report)

        sev_cnt = Counter()
        for cid in check_ids:
            for it in results[cid]:
                sev_cnt[it.severity] += 1
        if sev_cnt.get("HIGH", 0) > 0:
            has_high = True
        summary_parts = []
        for sev in SEV_ORDER:
            label = SEV_LABEL[sev]
            mark = "✅ 0" if sev_cnt.get(sev, 0) == 0 else f"⚠️ {sev_cnt[sev]}"
            summary_parts.append(f"{label}: {mark}")
        print(f"\n=== 数值自洽核对：{os.path.basename(f)} ===")
        for line_txt in summary_parts:
            print(f"  {line_txt}")
        print(f"  → 报告已写入：{out}")

    sys.exit(1 if has_high else 0)


if __name__ == "__main__":
    main()

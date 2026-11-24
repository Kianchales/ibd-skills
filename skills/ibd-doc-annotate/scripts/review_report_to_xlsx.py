#!/usr/bin/env python3
"""review_report_to_xlsx.py — 复核报告（Excel）生成器

为什么存在（2026-10-07 用户裁定）：
    复核报告的交付载体由 **Word 改为 Excel**——「Excel 可以根据问题性质分成不同的 sheet，
    比 Word 报告好」。此前该报告的**文件级骨架从未进规范**（`ibd-doc-review` delivery.md
    §八 的「收尾四段式」是**对话回复**的话术骨架，不是报告文件骨架），本脚本与
    `ibd-doc-review/references/delivery.md` **§八之二**配套：**规范定形态，本脚本落形态**。

输入：
    --issues <问题清单.json>   复核问题清单（结构契约 ibd-doc-review/references/interface.md §3）
    --round-ledger <台账.json> **可选**——多轮复核时传 `round_diff.py --json` 的产物，
                               追加「轮次状态」工作表（第二页；规格 delivery.md §七之二）
    --meta  <报告元信息.json>  **可选**——报告头的叙述性内容（复核对象/基准/方式/**复核声明**/
                               范围与方法/已核查通过/质量证据/行动项）；缺省时只出明细页 ＋ 自动统计。
                               模板随包：scripts/report-meta.example.json
输出：
    Excel 工作簿。G3 命名规范：`<原文>_<YYYYMMDD>_v<N>_复核报告.xlsx`（正式交付请用 --out 显式传入）。

工作簿结构（规格单一事实源 = delivery.md §八之二）：
    ① 封面与汇总   报告头 ＋ **复核声明** ＋ 结论 ＋ 复核范围与方法 ＋ 统计 ＋ 已核查通过
                   ＋ 质量证据 ＋ 行动项（小节序号按**实际渲染顺序**自增，缺节不跳号；
                   **仅主标题一行居中**，其余标题一律左对齐；**所有行统一跨 A:C 合并**，
                   列宽 A:B:C 唯一一套 —— 封面上下等宽）
    ② 轮次状态      **可选**（传 --round-ledger 时才有）：跨轮五态台账 ＋ 统计；
                   紧跟封面，便于评审一眼看到「上轮的条目这轮动了没有」。
                   无台账时此页不出现（**不留空页**——空页会被读成「本轮无遗留」）
    ③ 按性质分页   一张工作表一个「问题性质」（--split 可换轴；nature 缺省回退 type 大类）
    ④ 全部         不拆分的完整台账

明细列：编号｜严重度｜性质｜域｜行号｜原文片段｜问题标题｜问题描述｜建议（＋定稿文本/作者，有则加列）

用法：
    python review_report_to_xlsx.py --issues issues.json [--meta meta.json]
           [--out 报告.xlsx] [--split nature] [--title "…"] [--date 20261007] [--json]
           [--round-ledger ledger.json]
退出码：0 = 成功；1 = 失败；2 = 用法/清单错误。

依赖：openpyxl（**惰性导入**——仅本功能需要，本包其它链路不依赖）
编号同源：issue_numbering.py（与批注注入器共用，保证「报告编号 ↔ 批注编号 一一对应」）
"""
import argparse
import copy
import datetime
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ── 与注入器共用的编号单一事实源（零三方依赖）──
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from issue_numbering import derive_code, full_label  # noqa: E402
from validate_issues import validate_issues  # noqa: E402

# ── 展示常量 ──
SEV_ORDER = {"高": 0, "中": 1, "低": 2}
SEV_LABEL = {"高": "必改（高）", "中": "应改（中）", "低": "建议改（低）"}
# 性质标签的排序优先级：**只看前导圈号**（①–⑩），不比对完整标签文字——标签由项目自定
# （如「③自身逻辑」vs「③回复自身逻辑」），圈号才是跨项目稳定的序。无圈号者排末位。
CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩"
SPLIT_CHOICES = ("nature", "type", "code", "sev")

SHEET_COVER = "封面与汇总"
SHEET_ALL = "全部"
# 轮次状态页（2026-10-20 新增 · 规格 ibd-doc-review delivery.md §七之二）——
# 多轮复核时把 round_diff.py 的台账并进报告，作为**第二工作表**（紧跟封面）。
SHEET_ROUND = "轮次状态"
ROUND_STATE_ORDER = ("未修复·原句未动", "未修复·已改写", "新增", "疑似已关闭", "已关闭")

# 封面统一跨度：**所有行一律合并/铺设到 C 列**（用户裁定 2026-10-07）——
# 此前多数行只跨 A:B，而「域／覆盖范围／条数」统计表天然占 A:B:C，导致封面**上下不等宽**。
COVER_LAST_COL = 5
SHEET_SCOPE = "复核范围"
SHEET_STATS = "问题统计"
COVER_WIDTHS = {"A": 2.5, "B": 16, "C": 29, "D": 29, "E": 31}   # 5 列：留白/标签/值/值/值

# 封面小节序号（「一、」「二、」…）——按渲染顺序自增，某节缺省时不跳号
CN_NUM = "一二三四五六七八九十"

# 复核声明的分栏（键 → 小标题），对应《本轮检查项声明》
# （ibd-doc-review check-scope.md §六）；「声明与报告头一致」＝交付纪律，见 delivery.md §八。
# 顺序即渲染顺序，须与 check-scope.md §六 模板一致：覆盖方式 → 检查 → 不查 → 特别专项 → 依据来源 → 交付前将跑
DECL_SECTIONS = (("coverage", "覆盖方式（全文逐段／圈定范围／抽核）"),
                 ("checked", "检查（本次实际要跑的项）"),
                 ("not_checked", "不查（点名 ＋ 原因）"),
                 ("special", "特别专项（触发即生效）"),
                 ("sources", "依据来源（本轮参照了哪些参考资料）"),
                 ("gates", "交付前将跑"))

# 严重度着色：高＝红系｜中＝橙系｜低＝灰系（遵中文语境「红＝最需处理」）
# ── 字体（2026-11-20 定稿）：不依赖 Excel 默认字体（默认值随机器/语言包变化，跨机不一致）
FONT_NAME = "微软雅黑"      # 报告是屏幕件：雅黑在屏上比宋体清；正文仍由 Word 承租宋体
TITLE_FONT = "微软雅黑"
BODY_SZ = 10          # 明细正文
HEAD_SZ = 10          # 表头
COVER_TITLE_SZ = 16   # 封面主标题
SECTION_SZ = 11       # 封面小节标题

# 严重度配色（2026-11-23 定稿：投行沉色 —— 底为同色系极浅、字为沉色，比 Excel 经典色克制）
# 高＝深红 C00000｜中＝赭 BF8F00｜低＝灰 808080；只着色「严重度」一列，不整行、不斑马纹
SEV_STYLE = {"高": ("FBE5E5", "C00000"), "中": ("FEF2D9", "BF8F00"), "低": ("EDEDED", "808080")}
HEAD_FILL = "1F3864"      # 深海军蓝：表头唯一用色（设计规范：单一主色）
HEAD_FONT = "FFFFFF"
SECTION_FONT = "1F3864"
BORDER_COLOR = "BFBFBF"

# 台账列（键 → 表头），顺序即列序；末两列按需追加
BASE_COLS = [("full", "编号"), ("sev", "严重度"), ("nature", "性质"), ("code", "域"),
             ("line", "行号"), ("anchor", "原文片段"), ("title", "问题标题"),
             ("desc", "问题描述"), ("advice", "建议")]
OPT_COLS = [("rev", "定稿文本"), ("author", "作者")]
# 列宽按"整表缩到 A4 横向一页"倒推：总宽越小，单列越不容易被压成竖排
COL_WIDTH = {"编号": 8, "严重度": 8, "性质": 12, "域": 5, "行号": 12, "原文片段": 34,
             "问题标题": 24, "问题描述": 40, "建议": 26, "定稿文本": 38, "作者": 8}
LONG_COLS = {"原文片段", "问题标题", "问题描述", "建议", "定稿文本"}


def _load_openpyxl():
    """惰性导入：openpyxl 只在真正生成报告时需要，不拖累本包其它链路。"""
    try:
        import openpyxl
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
        from openpyxl.utils import get_column_letter
    except ImportError:  # pragma: no cover
        sys.exit("[ERROR] 缺少 openpyxl——复核报告生成器需要它（pip install openpyxl）；"
                 "本包其余链路不受影响。")
    return openpyxl, Alignment, Border, Font, PatternFill, Side, get_column_letter


# ───────────────────────── 领域逻辑（无 Excel 依赖，便于单测） ─────────────────────────

def nature_of(it):
    """条目的「性质」：清单 `nature` 字段优先；缺省回退 `type` 的大类（数据/表述/披露/合规）。"""
    n = str(it.get("nature") or "").strip()
    if n:
        return n
    t = str(it.get("type") or "").strip()
    if "·" in t:
        return t.split("·", 1)[0]
    return t or "未分类"


def number_entries(issues):
    """按注入器同一规则编号（issue_numbering）——**不改动入参**，返回新列表。

    每组前缀独立自增，顺序 ＝ 清单顺序（编号一次性分配，与批注/总览一一对应）。
    """
    seen, out = {}, []
    for it in issues:
        code = derive_code(it)
        seen[code] = seen.get(code, 0) + 1
        row = dict(it)
        row["code"] = code
        row["full"] = full_label(code, seen[code])
        row["nature"] = nature_of(it)
        row["sev"] = str(it.get("sev") or "")
        out.append(row)
    return out


def _nature_rank(name):
    """性质标签排序键：有前导圈号①–⑩按圈号；无则排到末位（同档再按条数降、名称升）。"""
    return CIRCLED.index(name[0]) if name and name[0] in CIRCLED else len(CIRCLED)


def group_entries(rows, axis):
    """按轴分组，返回 [(组名, [条目…])]，组序可预期（推荐序 > 条数 > 名称）。"""
    key = {"nature": lambda r: r["nature"],
           "type": lambda r: (r["type"].split("·", 1)[0] if "·" in r["type"] else r["type"]) or "未分类",
           "code": lambda r: r["code"],
           "sev": lambda r: r["sev"] or "未定"}[axis]
    buckets = {}
    for r in rows:
        buckets.setdefault(key(r), []).append(r)
    if axis == "sev":
        names = sorted(buckets, key=lambda k: (SEV_ORDER.get(k, 9), k))
    elif axis == "nature":
        names = sorted(buckets, key=lambda k: (_nature_rank(k), -len(buckets[k]), k))
    else:
        names = sorted(buckets, key=lambda k: (len(k) != 1, k))
    return [(n, buckets[n]) for n in names]


def sort_rows(rows):
    """严重度升序（高→低），同档保持清单原序。"""
    return sorted(rows, key=lambda r: SEV_ORDER.get(r["sev"], 9))


def counts_by(rows, axis):
    if axis == "sev":
        return [(SEV_LABEL.get(k, k), sum(1 for r in rows if r["sev"] == k))
                for k in ("高", "中", "低") if any(r["sev"] == k for r in rows)]
    if axis == "code":
        return [(n, len(g)) for n, g in group_entries(rows, "code")]
    if axis == "type":
        return [(n, len(g)) for n, g in group_entries(rows, "type")]
    return [(n, len(g)) for n, g in group_entries(rows, "nature")]


def _sanitize_sheet_name(name, used):
    """Excel 工作表名净化：去 []:*?/\\ 、截 31、去首尾引号，冲突时加序号。"""
    s = re.sub(r"[\[\]:*?/\\]", "", str(name)).strip().strip("'").strip()
    s = s[:31] or "未命名"
    base, i = s, 2
    while s in used or s == SHEET_COVER:
        suffix = f"({i})"
        s = base[:31 - len(suffix)] + suffix
        i += 1
    used.add(s)
    return s


# ───────────────────────── Excel 渲染 ─────────────────────────

def _write_table(ws, r, header, rows, widths, styles, start_col=1, extend_last_to=None):
    """写一张带表头的表；返回下一空行号。

    `extend_last_to`：把**末列右延并合并**到指定列（封面统计表统一到 C 列用，
    保证封面「上下等宽」——见 COVER_LAST_COL）。
    """
    Alignment, Border, Font, PatternFill, Side, _ = styles
    # 去全框线（全框是"Excel 默认感"的主因）；只用行底 hair 线＋表头下一条粗线
    hair = Side(style="hair", color="D9D9D9")
    head_rule = Side(style="medium", color="1F3864")
    box = Border(bottom=hair)
    head_fill, head_font = HEAD_FILL, HEAD_FONT
    n = len(header)
    last_native = start_col + n - 1
    end_col = max(last_native, extend_last_to or 0)

    def _extend(rr):
        """末列右延到 end_col：先给补位格描边、再合并（合并区外框取各边所属格）。"""
        if end_col <= last_native:
            return
        for j in range(last_native + 1, end_col + 1):
            ws.cell(row=rr, column=j).border = box
        ws.merge_cells(start_row=rr, start_column=last_native, end_row=rr, end_column=end_col)

    for j, h in enumerate(header):
        c = ws.cell(row=r, column=start_col + j, value=h)
        c.fill = PatternFill("solid", fgColor=head_fill)
        c.font = Font(name=FONT_NAME, size=HEAD_SZ, bold=True, color=head_font)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = Border(bottom=head_rule)
    _extend(r)
    r += 1
    sev_idx = header.index("严重度") if "严重度" in header else -1
    for i_row, row in enumerate(rows):
        banded = (i_row % 2 == 1)
        for j, v in enumerate(row):
            c = ws.cell(row=r, column=start_col + j, value=v)
            c.font = Font(name=FONT_NAME, size=BODY_SZ)
            c.border = box
            if banded:
                c.fill = PatternFill("solid", fgColor="F7F9FC")   # 斑马纹，替代边框分区
            c.alignment = Alignment(vertical="top",
                                    wrap_text=header[j] in LONG_COLS,
                                    horizontal=("center" if header[j] in ("编号", "严重度", "性质", "域", "行号")
                                                else "right" if header[j] in ("条数", "金额", "占比") else "left"))
            if j == sev_idx and str(v) in SEV_STYLE:
                fill, font = SEV_STYLE[str(v)]
                c.fill = PatternFill("solid", fgColor=fill)
                c.font = Font(name=FONT_NAME, size=BODY_SZ, bold=True, color=font)
        _extend(r)
        r += 1
    return r


def _write_kv(ws, r, pairs, styles, key_w=None):
    """标签格（A）＋ 值格（**合并 B:C**）——值格右延到 COVER_LAST_COL，与全封面等宽。"""
    Alignment, Border, Font, PatternFill, Side, _ = styles
    thin = Side(style="thin", color=BORDER_COLOR)
    box = Border(left=thin, right=thin, top=thin, bottom=thin)
    for k, v in pairs:
        a = ws.cell(row=r, column=1, value=k)
        a.font = Font(name=FONT_NAME, size=BODY_SZ, bold=True)
        a.fill = PatternFill("solid", fgColor="F2F2F2")
        a.border = box
        a.alignment = Alignment(vertical="top", wrap_text=True)
        b = ws.cell(row=r, column=2, value=v)
        b.border = box
        b.font = Font(name=FONT_NAME, size=BODY_SZ)
        b.alignment = Alignment(vertical="top", wrap_text=True)
        for j in range(3, COVER_LAST_COL + 1):
            ws.cell(row=r, column=j).border = box
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=COVER_LAST_COL)
        r += 1
    return r


def _write_center(ws, r, text, styles, bold=False, size=11, color=None):
    """跨 **A:C** 合并的**居中**单行——**仅封面主标题（第 1 行）使用**。

    用户裁定（2026-10-07）：**只第一行居中**，其余标题一律正常居左——故本函数
    不再用于副标题，也不用于小节标题（见 `_write_section`）。
    """
    Alignment, _, Font, _, _, _ = styles
    c = ws.cell(row=r, column=1, value=text)
    opts = {"name": FONT_NAME, "bold": bold, "size": size}
    if color:
        opts["color"] = color
    c.font = Font(**opts)
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=COVER_LAST_COL)
    return r + 1


def _write_section(ws, r, title, styles):
    """小节标题：跨 **A:C** 合并 ＋ **左对齐**（用户裁定：主标题之外一律正常居左；
    跨度仍与全封面统一，保证上下等宽）。"""
    Alignment, _, Font, _, _, _ = styles
    c = ws.cell(row=r, column=1, value=title)
    c.font = Font(name=FONT_NAME, size=SECTION_SZ, bold=True, color=SECTION_FONT)
    c.alignment = Alignment(vertical="center")
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=COVER_LAST_COL)
    return r + 1


def _write_lines(ws, r, lines, styles, bullet=True, bold_idx=()):
    Alignment, _, Font, _, _, _ = styles
    # 字符串按「一整行」处理：传 list 才是多行。
    # 2026-11-20 修：此前把 str 当可迭代对象，一个字一行 —— `approach` 写成字符串时，
    # 封面 20 个字被渲染成 20 行（实测「· 先 / · 定 / · 分 / · 母 …」）。
    if isinstance(lines, str):
        lines = [lines]
    for i, ln in enumerate(lines):
        c = ws.cell(row=r, column=1, value=("· " if bullet else "") + str(ln))
        # bold_idx：把"本轮实际使用"的那一行整行加粗并染色（Excel 单元格无法部分加粗）
        on = i in bold_idx
        c.font = Font(name=FONT_NAME, size=BODY_SZ, bold=on,
                      color="C00000" if on else None)
        c.alignment = Alignment(vertical="top", wrap_text=True)
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=COVER_LAST_COL)
        r += 1
    return r


def _write_declaration(ws, r, decl, styles):
    """**复核声明**块（2026-10-07 用户裁定：声明要随报告走）。

    报告是一份独立文件、会脱离对话单独流转，故「动手前声明什么、报告头就写什么」
    （`ibd-doc-review` delivery.md §八 落款义务 ⟷ check-scope.md §六 声明单）。
    两种形态都收：
      - dict：{depth, coverage, checked[], not_checked[], special[], sources[], gates}
        （结构化，推荐；键名与 `ibd-doc-review` check-scope.md §六 声明单一致）
      - list／str：逐行文字（简单形态，无分栏）
    """
    Alignment, _, Font, _, _, _ = styles
    if isinstance(decl, str):
        decl = [decl]
    if isinstance(decl, list):
        return _write_lines(ws, r, decl, styles)
    depth = str(decl.get("depth") or "").strip()
    if depth:
        c = ws.cell(row=r, column=1, value=f"复核深度：{depth}")
        c.font = Font(bold=True)
        c.alignment = Alignment(vertical="center")
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=COVER_LAST_COL)
        r += 1
    for key, label in DECL_SECTIONS:
        val = decl.get(key)
        if not val:
            continue
        c = ws.cell(row=r, column=1, value="▍" + label)
        c.font = Font(bold=True)
        c.alignment = Alignment(vertical="center")
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=COVER_LAST_COL)
        r += 1
        r = _write_lines(ws, r, val if isinstance(val, list) else [val], styles)
    return r


class _SectionNumber:
    """封面小节序号自增器——**按实际渲染顺序**编号，某节缺省时不出现跳号。"""

    def __init__(self):
        self._i = 0

    def __call__(self, title):
        self._i += 1
        n = CN_NUM[self._i - 1] if self._i <= len(CN_NUM) else str(self._i)
        return f"{n}、{title}"


def _detail_sheet(wb, name, rows, cols, styles, first=False):
    Alignment, _, Font, _, _, get_column_letter = styles
    ws = wb.active if first else wb.create_sheet()
    ws.title = name
    header = [h for _, h in cols]
    data = [[r.get(k, "") for k, _ in cols] for r in sort_rows(rows)]
    nxt = _write_table(ws, 1, header, data, None, styles)
    for j, (_, h) in enumerate(cols, start=1):
        ws.column_dimensions[get_column_letter(j)].width = COL_WIDTH.get(h, 14)
    # 行高按内容估算（否则 wrap 的两行字被固定 15 高切掉）
    import math
    for i_, row in enumerate(data, start=2):
        lines = 1
        for j, v in enumerate(row):
            h = header[j]
            if h in LONG_COLS:
                w = max(8, COL_WIDTH.get(h, 14) / 2)      # 中文按半个宽度单位/字
                lines = max(lines, math.ceil(len(str(v or "")) / w))
        ws.row_dimensions[i_].height = min(110, max(15, 12 * lines + 3))
    ws.freeze_panes = "A2"
    if data:
        ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{len(data) + 1}"
    _apply_print(ws, repeat_header=True)
    return ws


def _apply_print(ws, repeat_header=False):
    """打印设置（2026-11-20 定稿）：A4 横向、按宽缩放 1 页、重复首行、页脚页码。

    此前完全没设 —— 打印出来会按纵向硬切、跨页断表、续页无表头，交付件不能直接给人。
    """
    from openpyxl.worksheet.properties import PageSetupProperties
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0        # 高度不限页，避免长清单被压成小字
    if repeat_header:
        ws.print_title_rows = "1:1"      # 续页自动重复表头
    ws.page_margins.left = ws.page_margins.right = 0.4
    ws.page_margins.top = ws.page_margins.bottom = 0.5
    ws.oddFooter.center.text = "第 &P 页 / 共 &N 页"
    ws.oddFooter.center.size = 8
    ws.oddFooter.center.font = FONT_NAME


def load_round_ledger(path):
    """读 `round_diff.py --json` 的产物；结构不对即拒（宁可报错，不出半截页）。

    为什么校验而不是「能读就读」：台账页会被当成**交付件**随报告流转，
    结构缺项时静默生成一张空表，比报错更坏——读的人会以为「本轮没问题」。
    """
    with open(path, encoding="utf-8-sig") as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or not isinstance(data.get("stats"), dict) \
            or not isinstance(data.get("items"), list):
        raise ValueError("轮次台账结构不符：须为 round_diff.py --json 的输出（含 stats 对象与 items 数组）")
    return data


def _round_note(ws, r, text, last_col, styles):
    """整行说明文字（跨 A:last_col 合并）——台账页比封面宽，故不用 _write_lines 的 A:C。"""
    Alignment, _, Font, _, _, _ = styles
    c = ws.cell(row=r, column=1, value=text)
    c.font = Font(name=FONT_NAME, size=BODY_SZ)
    c.alignment = Alignment(vertical="top", wrap_text=True)
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=last_col)
    return r + 1


def _round_sheet(wb, ledger, styles):
    """轮次状态页：统计表 ＋ 逐条五态台账。

    **口径不复制**（P1 单一事实源）：档位定义与三条硬约束写在
    `ibd-doc-review/references/delivery.md` §七之二，此处只渲染，并把「读法警示」重复一遍
    ——因为报告会脱离对话单独流转，读的人看不到规范。
    """
    Alignment, _, Font, PatternFill, _, get_column_letter = styles
    ws = wb.create_sheet(SHEET_ROUND)
    for col, w in (("A", 24), ("B", 16), ("C", 10), ("D", 40), ("E", 58)):
        ws.column_dimensions[col].width = w

    r = _write_center(ws, 1, "轮次状态（跨轮收敛台账）", styles, bold=True, size=13, color=SECTION_FONT)
    r = _round_note(ws, r,
                    "读法：本页由 round_diff.py 生成，比对「上轮问题清单」与「本轮问题清单」。"
                    "「未修复」两档可直接采信；「疑似已关闭」与「已关闭」须人工过目，"
                    "并与封面报告头的**复核范围声明**逐项对照——范围收窄（如 L2→L1、只核财务域）"
                    "同样会造成「已关闭」，那不是改好了。", 5, styles)
    r += 1

    st = ledger.get("stats") or {}
    pairs = [("上轮条数", st.get("上轮条数", "—")),
             ("本轮条数", st.get("本轮条数", "—")),
             ("未修复·原句未动", st.get("未修复·原句未动", 0)),
             ("未修复·已改写", st.get("未修复·已改写", 0)),
             ("疑似已关闭（待人工确认）", st.get("疑似已关闭", 0)),
             ("已关闭（原句已不存在）", st.get("已关闭", 0)),
             ("本轮新增", st.get("新增", 0))]
    if st.get("关闭率") is not None:
        pairs.append(("关闭率（已关闭／上轮条数）", "%.1f%%" % (float(st["关闭率"]) * 100)))
    r = _write_table(ws, r, ["指标", "值"], pairs, None, styles)
    r += 1

    items = ledger.get("items") or []
    order = {k: i for i, k in enumerate(ROUND_STATE_ORDER)}
    rows = []
    for it in items:
        state = str(it.get("state") or "")
        src = it.get("cur") or it.get("prev") or {}
        score = it.get("score")
        anchor_txt = str(src.get("anchor") or "").replace("\n", " ")
        if len(anchor_txt) > 70:
            anchor_txt = anchor_txt[:70] + "…"
        rows.append((state, "—" if score is None else "%.2f" % float(score),
                     src.get("sev", ""), src.get("title", ""), anchor_txt))
    rows.sort(key=lambda x: order.get(x[0], len(order)))
    r = _write_table(ws, r, ["状态", "相似度", "严重度", "问题标题", "位置锚点（节选）"],
                     rows, None, styles)
    ws.freeze_panes = "A%d" % (r - len(rows) - 1 if rows else r)
    return ws


def _cover_sheet(wb, meta, rows, split, styles, extra_sheets=()):
    """首页：按"控制表"（dashboard）思路排——横向 KPI 组、色带压边、区块底色。

    上一版是"标签＋长值"纵向堆叠，读起来像一张表，没有版面。这一版：
    · 顶部 navy 色带压边（一条线定住整页）
    · KPI 横向三段（大数字＋小标签），一眼看结论
    · 域做成 chips（浅底小块），扫读快
    · 档位做成红底白字徽标
    """
    Alignment, Border, Font, PatternFill, Side, get_column_letter = styles
    from collections import Counter
    ws = wb.active
    ws.title = SHEET_COVER
    ws.sheet_view.showGridLines = False
    for col, w in COVER_WIDTHS.items():
        ws.column_dimensions[col].width = w
    ws.page_margins.left = ws.page_margins.right = 0.45
    ws.page_margins.top = 0.45

    NAVY, GREY, LIGHT, RED = "1F3864", "595959", "F4F7FB", "C00000"

    def fill_row(row, color, height=None):
        for col in range(1, COVER_LAST_COL + 1):
            ws.cell(row=row, column=col).fill = PatternFill("solid", fgColor=color)
        if height:
            ws.row_dimensions[row].height = height

    def merge(row, c1, c2):
        if c2 > c1:
            ws.merge_cells(start_row=row, start_column=c1, end_row=row, end_column=c2)

    def put(row, col, text, size=10, color="262626", bold=False, align="left",
            wrap=False, span=None):
        c = ws.cell(row=row, column=col, value=str(text))
        c.font = Font(name=FONT_NAME, size=size, color=color, bold=bold)
        c.alignment = Alignment(horizontal=align, vertical="top", wrap_text=wrap)
        if span:
            merge(row, col, span)
        return c

    # ① 顶部色带（压边，全页气质靠这一条）
    fill_row(1, NAVY, height=7)

    # ② 标题区：左对齐大字（居中显软，投行封面多为左对齐）
    put(4, 2, str(meta.get("title") or "复核报告"), size=26, color=NAVY, bold=True)
    merge(4, 2, 5); ws.row_dimensions[4].height = 44
    sub = str(meta.get("subject_short") or meta.get("subject") or "")
    put(5, 2, sub, size=11, color="404040"); merge(5, 2, 5)
    ws.row_dimensions[5].height = 20
    put(6, 2, str(meta.get("date") or ""), size=9.5, color="7F7F7F"); merge(6, 2, 5)
    ws.row_dimensions[6].height = 16

    # ③ KPI 横排三段：大数字＋小标签（控制表的核心观感）
    total = len(rows)
    hi = sum(1 for x in rows if x["sev"] == "高")
    mid = sum(1 for x in rows if x["sev"] == "中")
    lo = sum(1 for x in rows if x["sev"] == "低")
    base = 9
    fill_row(base - 1, "FFFFFF", height=6)
    for col, num, lab_, tone in ((2, total, "问题总数", NAVY),
                                 (3, hi, "必改（高）", RED),
                                 (4, mid, "应改（中）", NAVY),
                                 (5, lo, "建议改（低）", "7F7F7F")):
        n = ws.cell(row=base, column=col, value=str(num))
        n.font = Font(name=FONT_NAME, size=30, bold=True, color=tone)
        n.alignment = Alignment(horizontal="left", vertical="bottom")
        l = ws.cell(row=base + 1, column=col, value=lab_)
        l.font = Font(name=FONT_NAME, size=9.5, color=GREY)
        l.alignment = Alignment(horizontal="left", vertical="top")
    ws.row_dimensions[base].height = 40
    ws.row_dimensions[base + 1].height = 16

    # ④ 分隔细线
    for col in range(2, COVER_LAST_COL + 1):
        ws.cell(row=base + 3, column=col).border = Border(
            bottom=Side(style="hair", color="BFBFBF"))
    ws.row_dimensions[base + 3].height = 8

    # ⑤ 三项信息（标签在上、值在下：更像卡片，不像表格）
    r = base + 4
    for k, v in (("数据基准", meta.get("baseline", "—")),
                 ("覆盖方式", meta.get("method", "—"))):
        put(r, 2, k, size=9, color=GREY, align="right")
        put(r + 1, 2, v, size=10.5, color="262626", wrap=True, span=COVER_LAST_COL)
        ws.row_dimensions[r].height = 15
        ws.row_dimensions[r + 1].height = max(17, 16 * (1 + len(str(v)) // 54))
        r += 2
    r += 1

    # ⑥ 复核域：chips（浅底小块，横向扫读）
    if meta.get("domain_lines"):
        # 两栏清单：左列域名（浅底徽标）、右列项名——避免 chips 与行首域名重复
        put(r, 2, "复核域", size=9, color=GREY, align="right")
        r += 1
        for ln in meta["domain_lines"]:
            name, _, rest = ln.partition("（")
            badge = ws.cell(row=r, column=2, value=name.strip())
            badge.font = Font(name=FONT_NAME, size=9, color=NAVY, bold=True)
            badge.fill = PatternFill("solid", fgColor=LIGHT)
            badge.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            badge.border = Border(bottom=Side(style="medium", color="4472C4"))
            put(r, 3, "（" + rest, size=9.5, color=GREY, wrap=True, span=COVER_LAST_COL)
            ws.row_dimensions[r].height = max(24, 15 * (1 + len(rest) // 56))
            r += 1
        if meta.get("domain_note"):
            put(r, 3, str(meta["domain_note"]), size=8.5, color="9C6500", span=COVER_LAST_COL)
            ws.row_dimensions[r].height = 14
            r += 1
        r += 1

    # ⑦ 档位：红底白字徽标（一眼定位"本轮用的是哪档"）
    if meta.get("depth_levels"):
        used = [x for x in meta["depth_levels"] if x.get("used")]
        others = [x["text"].split("：")[0].strip() for x in meta["depth_levels"] if not x.get("used")]
        put(r, 2, "复核档位", size=9, color=GREY)
        if used:
            nm = used[0]["text"].replace("【本轮使用】", "")
            code, _, tail = nm.partition("：")
            b = ws.cell(row=r, column=3, value=code.strip())
            b.font = Font(name=FONT_NAME, size=10, bold=True, color="FFFFFF")
            b.fill = PatternFill("solid", fgColor=RED)
            b.alignment = Alignment(horizontal="center", vertical="center")
            put(r, 4, "　" + tail.strip(), size=9.5, color="404040", span=COVER_LAST_COL)
            ws.row_dimensions[r].height = 22
            r += 1
        if others:
            put(r, 3, "其他档位　" + "｜".join(others), size=9.5, color="7F7F7F",
                span=COVER_LAST_COL)
            ws.row_dimensions[r].height = 14
            r += 1
        r += 1

    # ⑧ 底部：hair 线 + 三列小字（横排，不再纵向堆成一列"注释垃圾场"）
    for col in range(2, COVER_LAST_COL + 1):
        ws.cell(row=r, column=col).border = Border(bottom=Side(style="hair", color="D9D9D9"))
    ws.row_dimensions[r].height = 6
    r += 1

    def _txt(x):
        if not x:
            return ""
        return "；".join(str(i) for i in x) if isinstance(x, (list, tuple)) else str(x)

    decl = meta.get("declaration") or []
    if isinstance(decl, str):
        decl = [decl]
    uncheck = next((x for x in decl if str(x).startswith("不查")), "")
    basis = next((x for x in decl if str(x).startswith("依据来源")), "")
    # 标签已是「未查」「依据」，值里再去掉重复的前缀
    if not uncheck and not basis and decl:      # 自由文本声明：整段落在「未查」行，不能凭空消失
        uncheck = "；".join(str(x) for x in decl)
    uncheck = str(uncheck).replace("不查：", "", 1) if isinstance(uncheck, str) else uncheck
    basis = str(basis).replace("依据来源：", "", 1) if isinstance(basis, str) else basis
    blocks = [("方法", _txt(meta.get("approach"))), ("未查", _txt(uncheck)),
              ("依据", _txt(basis)),
              ("已核查", _txt(meta.get("verified"))),
              ("质量证据", _txt(meta.get("quality_evidence")))]
    for i_, (k, v) in enumerate(blocks):
        if not v:
            continue
        put(r, 2, k, size=9, color=GREY)
        put(r, 3, v, size=9.5, color=GREY, wrap=True, span=COVER_LAST_COL)
        ws.row_dimensions[r].height = max(16, 15 * (1 + len(v) // 58))
        r += 1

    acts = meta.get("actions") or []
    if acts:
        put(r, 2, "待补", size=9, color="9C6500")
        put(r, 3, _txt(acts), size=9.5, color="9C6500", wrap=True, span=COVER_LAST_COL)
        ws.row_dimensions[r].height = max(14, 13 * (1 + len(_txt(acts)) // 58))

    # ⑨ 收尾色带：与顶部呼应，页面上下闭合
    end = r + 3
    for col in range(1, COVER_LAST_COL + 1):
        ws.cell(row=end, column=col).fill = PatternFill("solid", fgColor=NAVY)
    ws.row_dimensions[end].height = 5

    _apply_print(ws, repeat_header=False)
    ws.page_setup.orientation = "portrait"
    return ws


def build(args, issues, meta, ledger=None):
    openpyxl, Alignment, Border, Font, PatternFill, Side, get_column_letter = _load_openpyxl()
    styles = (Alignment, Border, Font, PatternFill, Side, get_column_letter)

    rows = number_entries(issues)
    cols = list(BASE_COLS) + [(k, h) for k, h in OPT_COLS if any(r.get(k) for r in rows)]
    meta = dict(meta)
    if args.title:
        meta["title"] = args.title
    if args.date:
        meta["date"] = args.date
    else:
        d = str(meta.get("date") or "").strip()
        meta["date"] = d or datetime.date.today().strftime("%Y-%m-%d")

    wb = openpyxl.Workbook()
    extra = [SHEET_ROUND] if ledger else []
    _cover_sheet(wb, meta, rows, args.split, styles, extra_sheets=extra)
    if ledger:
        _round_sheet(wb, ledger, styles)

    used = {SHEET_COVER} | set(extra)
    for name, group in group_entries(rows, args.split):
        _detail_sheet(wb, _sanitize_sheet_name(name, used), group, cols, styles)
    _detail_sheet(wb, _sanitize_sheet_name(SHEET_ALL, used), rows, cols, styles)

    out = args.out or os.path.splitext(os.path.abspath(args.issues))[0] + "_复核报告.xlsx"
    wb.save(out)
    return out, rows, cols


def find_runlog(issues_path, out_path=None):
    """在清单同目录 / 输出目录 / <清单同名>_复核/ 里找 _run.json。"""
    cands = []
    for base in (os.path.dirname(os.path.abspath(issues_path)),
                 os.path.dirname(os.path.abspath(out_path)) if out_path else None):
        if base:
            cands.append(os.path.join(base, "_run.json"))
    stem = os.path.splitext(os.path.basename(issues_path))[0]
    cands.insert(0, os.path.join(os.path.dirname(os.path.abspath(issues_path)),
                                 stem + "_复核", "_run.json"))
    for c in cands:
        if os.path.exists(c):
            return c
    return None


def runlog_summary(path):
    """把指纹压成两行证据；解析失败返回 (None, "无法解析")。"""
    try:
        import json as _j
        with open(path, encoding="utf-8") as f:
            st = _j.load(f)
        steps = st.get("steps", [])
        tools = []
        for s_ in steps:
            t = s_.get("tool")
            if t and t not in tools:
                tools.append(t)
        return st, "执行记录：本报告由固定流程逐步生成，过程记录已随文件留存（可复核）"
    except Exception:      # noqa: BLE001
        return None, "执行记录：过程记录存在但无法解析（请人工确认本轮是否按流程执行）"


def main():
    ap = argparse.ArgumentParser(
        description="复核报告（Excel）生成器（规格：ibd-doc-review references/delivery.md §八之二）")
    ap.add_argument("--issues", required=True, help="复核问题清单 JSON（数组）")
    ap.add_argument("--meta", help="报告元信息 JSON（可选：报告头/范围与方法/已核查/质量证据/行动项）")
    ap.add_argument("--out", help="输出 xlsx（默认 <issues 同名>_复核报告.xlsx；正式交付按 G3 命名显式传入）")
    ap.add_argument("--split", choices=SPLIT_CHOICES, default="nature",
                    help="分工作表轴：nature（默认，问题性质）/ type（12 类大类）/ code（域）/ sev（严重度）")
    ap.add_argument("--title", help="报告标题（覆盖 meta.title）")
    ap.add_argument("--date", help="生成日期（覆盖 meta.date；默认今天）")
    ap.add_argument("--json", action="store_true", help="输出结构化 JSON（供上层消费；不打印人类可读摘要）")
    ap.add_argument("--round-ledger", default=None,
                    help="轮次台账 JSON（round_diff.py --json 的产物）——传则追加「轮次状态」工作表")
    ap.add_argument("--verbose", action="store_true", help="逐条打印入口校验提示（默认折叠为一行计数）")
    ap.add_argument("--runlog", default=None,
                    help="运行指纹路径（<文件>_复核/_run.json）；缺省自动在 --out 目录附近找")
    ap.add_argument("--allow-no-runlog", action="store_true",
                    help="无运行指纹也生成报告（会**在封面标注「未按流程执行」**，留痕供追责）")
    args = ap.parse_args()

    try:
        with open(args.issues, encoding="utf-8") as fh:
            issues = json.load(fh)
    except (OSError, json.JSONDecodeError) as e:
        print(f"[ERROR] 清单读取/解析失败：{e}", file=sys.stderr)
        sys.exit(2)

    # 入口校验（与注入器同源）：结构性坏清单不生成报告
    errs, warns = validate_issues(issues)
    if errs:
        print(f"[ERROR] 清单未通过入口校验（{len(errs)} 项）——不生成报告：", file=sys.stderr)
        for e in errs:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(2)
    if warns:
        # 输出分层（P10）：报告清单里「同前缀多条」是常态，逐条刷屏无信息量——默认折叠为计数。
        if args.verbose:
            for w in warns:
                print(f"[WARN] {w}", file=sys.stderr)
        else:
            print(f"[WARN] 入口校验 {len(warns)} 条提示（同前缀多条属正常；如需逐条加 --verbose）",
                  file=sys.stderr)

    meta = {}
    if args.meta:
        try:
            with open(args.meta, encoding="utf-8") as fh:
                meta = json.load(fh)
        except (OSError, json.JSONDecodeError) as e:
            print(f"[ERROR] 元信息读取/解析失败：{e}", file=sys.stderr)
            sys.exit(2)
        if not isinstance(meta, dict):
            print("[ERROR] 元信息顶层须为对象（dict）", file=sys.stderr)
            sys.exit(2)

    # ── 运行指纹闸（2026-11-23）：没有指纹 = 没按 skill 流程跑，报告不得"看起来像走完了"
    rl_path = args.runlog or find_runlog(args.issues, args.out)
    rl_state, rl_line = (None, "执行记录：未发现过程记录（本轮可能未按标准流程执行）")
    if rl_path:
        rl_state, rl_line = runlog_summary(rl_path)
    elif not args.allow_no_runlog:
        print("[ERROR] 未找到运行指纹 `_run.json`——本轮没有按 ibd-doc-review 流程执行"
              "（未经 review_file 编排／未跑 check_content／check_cq／deliver_gate）。", file=sys.stderr)
        print("  处置：① 按流程重跑（python scripts/review_file.py --input <文件>）后生成报告；"
              "② 确需先出报告，加 --allow-no-runlog —— 封面会标注「未按流程执行」留痕。",
              file=sys.stderr)
        sys.exit(3)
    # 证据行并入「质量证据」节（读者在报告里就能看到流程是否合规）
    ev = list(meta.get("quality_evidence") or [])
    ev.append(rl_line)
    if rl_state is None:
        ev.append("⚠️ 本轮未按 skill 流程执行（无运行指纹），结论仅供内部参考")
    meta["quality_evidence"] = ev

    # 声明未做 ＝ 未声明范围（与 SKIP 同纪律）：缺声明不阻断生成，但必须留痕
    if not meta.get("declaration"):
        print("[WARN] meta 未提供 declaration（复核声明）——「复核范围」页的「未查与依据」将缺省；"
              "凡非「全项」复核，按 ibd-doc-review delivery.md §八 须随报告声明核对范围。",
              file=sys.stderr)

    ledger = None
    if args.round_ledger:
        try:
            ledger = load_round_ledger(args.round_ledger)
        except (OSError, json.JSONDecodeError, ValueError) as e:
            print(f"[ERROR] 轮次台账读取/校验失败：{e}", file=sys.stderr)
            sys.exit(2)

    out, rows, cols = build(args, issues, meta, ledger)
    hi = sum(1 for r in rows if r["sev"] == "高")
    mid = sum(1 for r in rows if r["sev"] == "中")
    lo = sum(1 for r in rows if r["sev"] == "低")
    sheets = [n for n, _ in group_entries(rows, args.split)]

    if args.json:
        print(json.dumps({"tool": "review_report_to_xlsx", "out": out, "total": len(rows),
                          "split": args.split, "groups": sheets, "cols": [h for _, h in cols],
                          "declaration": bool(meta.get("declaration")),
                          "round_ledger": bool(ledger),
                          "round_items": len((ledger or {}).get("items") or []),
                          "sev": {"高": hi, "中": mid, "低": lo}},
                         ensure_ascii=False))
        return 0
    # 输出分层（P10）：stdout 只出指标行 ＋ 路径，明细在工作簿里
    print(f"[OK] 复核报告已生成：{out}")
    _round_txt = "轮次状态 ／ " if ledger else ""
    print(f"     条目 {len(rows)}｜工作表 {len(sheets) + 2 + (1 if ledger else 0)}"
          f"（封面与汇总 ／ {_round_txt}{' ／ '.join(sheets)} ／ 全部）")
    print(f"     严重度 高 {hi} ／ 中 {mid} ／ 低 {lo}｜分页轴 {args.split}｜列 {len(cols)} 列")
    return 0


if __name__ == "__main__":
    sys.exit(main())

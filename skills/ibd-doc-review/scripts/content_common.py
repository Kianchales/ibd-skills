#!/usr/bin/env python3
"""格式核对共享基础层（docx 解析 + 中文序号基元 + 标点判定基元）。

归属：本模块原为 `check_content.py` 的「基础解析 / 中文数字与序号 / 标点基元」三段，
2026-09-11 按业务域拆组时抽为共享层（P2-⑧）。

**谁是单一事实源**：`Issue` 数据结构、docx 文本/表格解析、段落序号识别、
中英文标点邻接判定 —— 逻辑单一事实源在**本模块**；`check_content.py` 只做登记与编排。

被谁依赖：
  · `content_text.py`  —— 文字类核对项（用 Issue / 解析结果 / 序号基元 / 标点基元）
  · `content_table.py` —— 表格类核对项（用 Issue / 表格解析结果）
  · `check_content.py` —— 入口（用 Issue / 解析器 / 严重度常量做报告渲染）

本模块不 import 任何兄弟模块 —— 保持零环依赖。
"""

import os
import re
import zipfile

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TERM_RULES_FILE = os.path.join(SKILL_DIR, "references", "term_rules.json")


# ---------------------------------------------------------------- 基础解析


def load_docx(path):
    try:
        with zipfile.ZipFile(path) as z:
            names = set(z.namelist())
            out = {}
            if "word/document.xml" in names:
                out["word/document.xml"] = z.read("word/document.xml").decode("utf-8", errors="ignore")
            return out or None
    except Exception as e:
        print(f"[ERROR] 读取失败 {path}: {e}")
        return None


PARA_RE = re.compile(r"<w:p\b[^>]*>.*?</w:p>", re.S)
CELL_RE = re.compile(r"<w:tc\b[^>]*>.*?</w:tc>", re.S)
TBL_RE = re.compile(r"<w:tbl\b[^>]*>.*?</w:tbl>", re.S)
ROW_RE = re.compile(r"<w:tr\b[^>]*>.*?</w:tr>", re.S)


def _text_of(fragment):
    return "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", fragment))


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


def _para_info(body):
    ppr_m = re.search(r"<w:pPr\b[^>]*>.*?</w:pPr>", body, re.S)
    ppr = ppr_m.group(0) if ppr_m else None
    st = re.search(r'<w:pStyle w:val="([^"]+)"', ppr or "")
    jc = re.search(r'<w:jc w:val="([^"]+)"', ppr or "")
    return {
        "style": st.group(1) if st else None,
        "align": jc.group(1) if jc else None,
        "text": "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", body)).strip(),
    }


def extract_structure(doc):
    items = []
    cell_spans = [(m.start(), m.end()) for m in CELL_RE.finditer(doc)]
    tbl_spans = [(m.start(), m.end()) for m in TBL_RE.finditer(doc)]
    para_spans = [(m.start(), m.end()) for m in PARA_RE.finditer(doc)]

    def table_no(pos):
        return sum(1 for ms, me in tbl_spans if ms <= pos)

    for ps, pe in para_spans:
        in_cell = any(cs <= ps and pe <= ce for cs, ce in cell_spans)
        info = _para_info(doc[ps:pe])
        if in_cell:
            info["kind"] = "cell"
            info["table_no"] = table_no(ps)
        else:
            info["kind"] = "body"
        items.append((info["kind"], info))
    return items


def full_text_of(doc):
    return "\n".join(_text_of(m.group(0)) for m in PARA_RE.finditer(doc))


def parse_tables(doc):
    tables = []
    for tn, tm in enumerate(TBL_RE.finditer(doc), 1):
        rows = []
        for rm in ROW_RE.finditer(tm.group(0)):
            cells = []
            for cm in CELL_RE.finditer(rm.group(0)):
                cxml = cm.group(0)
                sizes = sorted({int(v) for v in re.findall(r'<w:sz w:val="(\d+)"', cxml)})
                paras = [_para_info(pb.group(0)) for pb in PARA_RE.finditer(cxml)]
                raw_text = _text_of(cxml).strip()
                # 纵向合并标记：restart = 合并起始格；continue = 被合并的续格（续格本就无文字）
                _tcpr = re.search(r'<w:tcPr>.*?</w:tcPr>', cxml, re.S)
                _vm = re.search(r'<w:vMerge(?:\s+w:val="([^"]+)")?\s*/>', _tcpr.group(0)) if _tcpr else None
                vmerge = (_vm.group(1) or "continue") if _vm else None
                cells.append({"text": raw_text,
                              "raw": "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", cxml)),
                              "vmerge": vmerge,
                              "sizes": sizes, "paras": paras})
            rows.append(cells)
        head_snips = []
        for row in rows[:2]:
            for c in row:
                if c["text"]:
                    head_snips.append(c["text"][:14])
            if head_snips:
                break
        tables.append({"no": tn, "rows": rows,
                       "head": ("｜".join(head_snips[:3])) if head_snips else ""})
    return tables


# ---------------------------------------------------------------- 中文数字与序号

_CN_UNITS = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
             "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def cn_to_int(s):
    s = s.strip()
    if not s:
        return None
    if s == "十":
        return 10
    if len(s) == 1:
        return _CN_UNITS.get(s)
    if s.startswith("十"):
        rest = s[1:]
        return 10 + (_CN_UNITS.get(rest, 0) if rest else 0)
    if "十" in s:
        a, _, b = s.partition("十")
        av = _CN_UNITS.get(a)
        bv = _CN_UNITS.get(b, 0) if b else 0
        if av is None:
            return None
        return av * 10 + bv
    if s.endswith("百"):
        av = _CN_UNITS.get(s[:-1])
        return av * 100 if av is not None else None
    return _CN_UNITS.get(s)


CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"

CN_CHAPTER_RE = re.compile(r"^第\s*([一二三四五六七八九十百]+|\d+)\s*[章节篇]")
PROBLEM_NUM_RE = re.compile(r"^问题\s*(\d{1,3})(?=$|[.．:：、\s（(])")
LEVEL_RES = [
    ("L1", re.compile(r"^([一二三四五六七八九十百]+)、"), "cn"),
    ("L2", re.compile(r"^[（(]\s*([一二三四五六七八九十百]+)\s*[）)]"), "cn"),
    ("L3", re.compile(r"^(\d{1,3})\s*[、．]"), "num"),
    ("L4", re.compile(r"^[（(]\s*(\d{1,3})\s*[）)]"), "num"),
    ("L5", re.compile(r"^(\d{1,3})\s*[）)]"), "num"),
    ("L6", re.compile(r"^([①-⑳])"), "circled"),
    ("L7", re.compile(r"^([A-Z])\s*[、．.]"), "alpha_up"),
    ("L8", re.compile(r"^([a-z])\s*[、．.]"), "alpha_lo"),
]
LEVEL_NAMES = {
    "C0": "章/节编号（第X节/第X章）",
    "P0": "问题编号（问题X）",
    "L1": "一级（一、）", "L2": "二级（（一））", "L3": "三级（1、）",
    "L4": "四级（（1））", "L5": "五级（1））", "L6": "六级（①）",
    "L7": "七级（A、）", "L8": "八级（a、）",
}
ALL_LEVELS = list(LEVEL_NAMES.keys())


def parse_numbering(text):
    """识别段落开头序号 → (level, value:int, raw)。"""
    m = CN_CHAPTER_RE.match(text)
    if m:
        raw = m.group(1)
        val = int(raw) if raw.isdigit() else cn_to_int(raw)
        if val and val > 0:
            return ("C0", val, raw)
    m = PROBLEM_NUM_RE.match(text)
    if m:
        return ("P0", int(m.group(1)), m.group(1))
    for level, pat, kind in LEVEL_RES:
        m = pat.match(text)
        if m:
            raw = m.group(1)
            if kind == "cn":
                val = cn_to_int(raw)
            elif kind == "circled":
                val = CIRCLED.index(raw) + 1
            elif kind == "alpha_up":
                val = ord(raw) - ord("A") + 1
            elif kind == "alpha_lo":
                val = ord(raw) - ord("a") + 1
            else:
                val = int(raw)
            if val is not None and val > 0:
                return (level, val, raw)
    return None


def _disp_num(level, val):
    if level == "C0":
        return str(val)
    if level == "P0":
        return str(val)
    if level in ("L1", "L2"):
        if val <= 10:
            return ["", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十"][val]
        tens, ones = divmod(val, 10)
        s = "十" if tens == 1 else _CN_UNITS.get(tens, str(tens)) + "十"
        if ones:
            s += _CN_UNITS.get(ones, str(ones))
        return s
    return str(val)


# ---------------------------------------------------------------- 标点判定基元

HALF_PUNCTS = ",.;:?!()\"'"
FULL_PUNCTS = "，。；：？！（）"


def _char_class(c):
    if c and "\u4e00" <= c <= "\u9fff":
        return "C"
    if c and c.isascii() and (c.isalpha() or c.isdigit()):
        return "E"
    return "O"


def _neighbor_class(s, k, direction):
    if direction < 0:
        rng = range(k - 1, -1, -1)
    else:
        rng = range(k + 1, len(s))
    for j in rng:
        c = s[j]
        if not c.isspace():
            return _char_class(c), j
    return None, None


FULL_HALF_MAP = {"，": ",", "。": ".", "；": ";", "：": ":",
                 "？": "?", "！": "!", "（": "(", "）": ")"}
HALF_FULL_MAP = {",": "，", ".": "。", ";": "；", ":": "：",
                 "?": "？", "!": "！", "(": "（", ")": "）"}

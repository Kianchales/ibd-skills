#!/usr/bin/env python3
"""docxio — docx 读取公共层（标准库 only，零依赖）

为什么要有这一层
----------------
抽层前实测：**8 个脚本各自 `zipfile.ZipFile` 解包、9 个各自读 `document.xml`、
6 个各自定义 Word 命名空间**。于是"同一判据两套实现"必然发生——
2026-11-19 那次真事故（注入器按样式名复用、校验按 styleId 判）就是这个结构的产物。

更直接的证据：两套流派对 XML 实体的处理不同——
    正则流派  → '某发行人 &amp; 合作方'
    ElementTree → '某发行人 & 合作方'
真实招股书里 `&amp;` 3 处、`&lt;` 2 处、`&gt;` 3 处，正则流派会把它们当字面量，
于是 `&amp;` 里的 `;` 被标点检查当成半角分号（假报）。本层统一用 ElementTree，实体由解析器解码。

设计原则：**参数化复现旧行为，不统一口径**
------------------------------------------
统一口径会悄悄改变结论（尤其"分母"：表格单元格 22,535 段 vs 正文 909 段，混算差 25 倍）。
故 `flat_text` / `para_text` 把差异做成显式参数——每个旧调用点都能一对一映射。
真要统一口径，那是**改判据**，须单独立项，不能夹在抽层里做。

分层
----
    open_docx()      → Bundle（names / xml / root）
    iter_blocks()    → 按文档顺序产出 ("p" | "tbl", node)，可下钻 sdt / customXml
    iter_paras()     → 逐段产出 Para（text / style / in_table / index）
    flat_text()      → 口径化全文（include_table / para_sep / tabs / breaks / del_text）
    iter_tables()    → 表格与单元格
    norm_for_compare() / strip_punct() → 归一化（原先 4 个脚本各写一份）

用法示例
--------
    b = open_docx("a.docx")
    text = flat_text(b, include_table=True, para_sep="")        # = 旧 deliver_gate 口径
    for p in iter_paras(b, include_table=False):                # = 旧 check_styles 裸段口径
        if p.text.strip() and not p.style:
            ...
"""
import html
import re
import zipfile
from dataclasses import dataclass, field
from typing import Iterator
from xml.etree import ElementTree as ET

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = "{%s}" % W_NS
DOC_PART = "word/document.xml"


@dataclass
class Bundle:
    """一个已打开的 docx：包内件名、document.xml 原文、解析后的根节点。"""
    path: str
    names: set
    xml: str
    root: ET.Element


@dataclass
class Para:
    """一个段落及其上下文。in_table 决定它算"正文"还是"单元格"。"""
    elem: ET.Element
    text: str
    style: str | None
    in_table: bool
    index: int                      # 段落文档序号（含表格内）
    extra: dict = field(default_factory=dict)


# ---------------------------------------------------------------- 包与节点

def open_docx(path: str, part: str = DOC_PART) -> Bundle:
    """打开 docx 并解析指定部件（默认 document.xml）。非标准包抛 ValueError。"""
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        if part not in names:
            raise ValueError("非标准 docx：缺 %s（实际 %d 个部件）" % (part, len(names)))
        xml = z.read(part).decode("utf-8")
    return Bundle(path=path, names=names, xml=xml, root=ET.fromstring(xml))


def body_of(bundle: Bundle) -> ET.Element:
    b = bundle.root.find(W + "body")
    if b is None:
        raise ValueError("document.xml 无 w:body")
    return b


def iter_blocks(src, dive_sdt=True):
    """按文档顺序产出 ("p", elem) / ("tbl", elem)。

    `src` 可以是 Bundle，也可以直接是 `w:body` 节点（便于脚本保留自己的 walk 函数签名）。

    `dive_sdt=True` 时递归下钻内容控件（w:sdt / w:sdtContent / w:customXml）——
    此前只有 plan_review 做了这件事，其余脚本遇到控件包裹的段落会**整块漏读**。
    """
    def walk(node):
        for child in list(node):
            if child.tag == W + "p":
                yield "p", child
            elif child.tag == W + "tbl":
                yield "tbl", child
            elif dive_sdt and child.tag in (W + "sdt", W + "sdtContent", W + "customXml"):
                yield from walk(child)

    node = src if isinstance(src, ET.Element) else body_of(src)
    yield from walk(node)


def style_of(p: ET.Element) -> str | None:
    st = p.find(W + "pPr/" + W + "pStyle")
    return st.get(W + "val") if st is not None else None


def para_text(p: ET.Element, tabs: bool = True, breaks: bool = True,
              del_text: bool = False) -> str:
    """段落文本。

    tabs/breaks：是否把 w:tab → "\\t"、w:br → "\\n"（旧 deliver_gate 不做，plan_review 做）
    del_text：是否计入 w:delText（修订删除的旧文；"取终稿"口径应为 False）
    """
    buf = []
    for node in p.iter():
        if node.tag == W + "t" and node.text:
            buf.append(node.text)
        elif del_text and node.tag == W + "delText" and node.text:
            buf.append(node.text)
        elif tabs and node.tag == W + "tab":
            buf.append("\t")
        elif breaks and node.tag == W + "br":
            buf.append("\n")
    return "".join(buf)


def iter_paras(bundle, include_table=True, dive_sdt=True, tabs=True, breaks=True,
               del_text=False):
    """逐段产出 Para；表格内段落标 in_table=True，可用 include_table=False 滤掉。"""
    idx = 0
    for kind, node in iter_blocks(bundle, dive_sdt=dive_sdt):
        if kind == "p":
            txt = para_text(node, tabs=tabs, breaks=breaks, del_text=del_text)
            yield Para(node, txt, style_of(node), False, idx)
            idx += 1
        elif include_table:
            for p in node.iter(W + "p"):
                txt = para_text(p, tabs=tabs, breaks=breaks, del_text=del_text)
                yield Para(p, txt, style_of(p), True, idx)
                idx += 1


def iter_tables(bundle):
    for kind, node in iter_blocks(bundle):
        if kind == "tbl":
            yield node


def table_cells(tbl: ET.Element) -> Iterator[ET.Element]:
    """表格的单元格元素（按行取 w:tc，不做 span 展开——需要合并信息时读 w:gridSpan/vMerge）"""
    for tr in tbl.findall(W + "tr"):
        for tc in tr.findall(W + "tc"):
            yield tc


# ---------------------------------------------------------------- 口径化文本

def flat_text(bundle, include_table=True, para_sep="", tabs=False, breaks=False,
              del_text=False):
    """全文文本。

    默认（include_table=True, para_sep=""）**等价于旧 `deliver_gate.read_docx`** 的口径：
    跨段直接拼接、不处理 tab/br。para_sep="\\n" 即 plan_review 的逐段口径。
    """
    if include_table and para_sep == "" and not tabs and not breaks and not del_text:
        # 快路径：与旧实现逐字一致（含表格、无分隔）
        return "".join(t.text or "" for t in bundle.root.iter(W + "t"))
    parts = [p.text for p in iter_paras(bundle, include_table=include_table,
                                        tabs=tabs, breaks=breaks, del_text=del_text)]
    return para_sep.join(parts)


# ---------------------------------------------------------------- 正则流派

RX_WT = re.compile(r"<w:t[^>]*>([^<]*)</w:t>")


def decode_entities(s: str) -> str:
    """解码 XML 实体（`&amp;` → `&`）。"""
    return html.unescape(s) if s else s


def regex_text(fragment: str) -> str:
    """从**原始 XML 片段**取文本（正则流派），**并解码实体**。

    为什么保留正则：`check_styles` 的裸段/空段/表格排除依赖 `<w:p>`/`<w:tc>` 的**字符偏移**，
    换 ElementTree 需整体重写且会改变边界计数——为零功能收益冒大风险，不值。
    但"不解实体"是**功能缺陷**：真实招股书 `7&amp;11` 里的 `;` 会被标点检查当半角分号假报。
    故此处只修实体，不换引擎。
    """
    return html.unescape("".join(RX_WT.findall(fragment)))


# ---------------------------------------------------------------- 归一化

_DQ_HALF = '"'
_DQ_L = "\u201c"
_DQ_R = "\u201d"
_LP_HALF, _RP_HALF = "(", ")"
_LP_FULL, _RP_FULL = "\uff08", "\uff09"


def strip_punct(s: str) -> str:
    """去掉成对标点，用于「零内容改动」指纹（与 deliver_gate 同口径）。"""
    return re.sub("[" + re.escape(_DQ_HALF + _DQ_L + _DQ_R + _LP_HALF + _RP_HALF
                                  + _LP_FULL + _RP_FULL) + "]", "", s)


def norm_for_compare(s: str) -> str:
    """内容比对归一化：去 markdown/HTML 标记与全部空白（与 deliver_gate 同口径）。"""
    s = re.sub(r"`+", "", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"[#>*|]+", "", s)
    s = re.sub(r"[-]{3,}", "", s)
    return re.sub(r"\s|\u3000", "", s)

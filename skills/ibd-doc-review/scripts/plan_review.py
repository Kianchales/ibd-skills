#!/usr/bin/env python3
"""复核计划器：定分母 → 归判据 → 切批次（只读，不改源文件）。

解决什么问题
------------
"抽样的直接诱因是分母算错"——按"逐段读全部"估一份 2.4 万段的招股书，必然得出
"做不完"，于是只能挑几段看。本脚本先把文档归到判据上（正文段/表格/单元格/标题/
中段），四类之和必须等于总段数，再按容量切批。**分母定了，抽样就没有借口。**

用法
----
    python scripts/plan_review.py --input <docx> [--input <docx2>] [--out <目录>]
                                  [--capacity-prose 400] [--capacity-tables 50]
                                  [--emit-batches] [--json]

输出
----
    <out>/_复核计划.md      分母表 ＋ 批次表 ＋ 台账骨架
    <out>/B01.txt ...       每批的必读正文段（[段号] 原文），供逐段过六问
    --json                  结构化结果（供上层消费）

判据
----
    正文段  : 非表内、去空白后 >40 字且含句读（。或，）  → 逐段过六问（人判）
    表格    : w:tbl 元素，一表一单元                     → 表级判一次
    单元格  : 表内段落                                   → 随表判，不单独判
    标题    : 序号开头（第X节/第X章/问题N./一、/（一）/1、/（1））→ 随序号链
    中段    : 15–40 字                                   → 随所在节扫读
    短句    : 其余                                       → 随表/随节
"""
import argparse
import json
import os
import re
import sys
from typing import Iterator, Literal, TypedDict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import docxio      # noqa: E402  docx 读取公共层（0.54.0）

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

RE_SEC = re.compile(r"^第[一二三四五六七八九十百\d]+[节章]")
RE_Q = re.compile(r"^问题\s*\d+\s*[\.．、]")
RE_L1 = re.compile(r"^[一二三四五六七八九十]{1,3}、")
RE_L2 = re.compile(r"^（[一二三四五六七八九十]{1,3}）")
RE_L3 = re.compile(r"^\d{1,2}[、\.]")
RE_L4 = re.compile(r"^（\d{1,2}）")
RE_L5 = re.compile(r"^[①-⑳]")
RE_HEAD = re.compile("|".join(r.pattern for r in (RE_SEC, RE_Q, RE_L1, RE_L2, RE_L3, RE_L4, RE_L5)))
RE_DIGIT = re.compile(r"\d")
RE_INFER = re.compile(r"因此|表明|可见|由此可见|由于|综上|因而|据此|足以")
RE_OVER = re.compile(r"最[大为优佳新高]|唯一|率先|领先|首家|龙头|完全|彻底|显著|极大|必将|必然|绝对|第一|顶级|卓越|优异")
RE_FACT = re.compile(r"《[^》]{2,40}》|第[一二三四五六七八九十\d]+名|排名|市场份额|市占率|占有率|[^\s，。]{2,20}(?:有限公司|股份有限公司|集团|研究院|大学|事务所)")
RE_FORE = re.compile(r"预计|有望|预期|未来|将要|计划于|承诺|保证")
# 目录行：带制表符、或尾部引导点＋页码、或连续空格＋页码（正文标题不会这样）
RE_TOC = re.compile(r"\t|[.·…]{2,}\s*\d{1,4}\s*$|\s{2,}\d{1,4}\s*$")

# 标题层级：rank 相同的两类（第X节／问题N）在文档里通常互斥；同时出现时取"更粗"的那类
LEVELS = (("SEC", RE_SEC, 0), ("Q", RE_Q, 0), ("L1", RE_L1, 1), ("L2", RE_L2, 2),
          ("L3", RE_L3, 3), ("L4", RE_L4, 4), ("L5", RE_L5, 5))


# ---- 数据结构契约（0.59.0）：units/batches 的字段语义由类型承载，免得靠读代码猜
UnitType = Literal["正文", "标题", "中段", "短句", "目录", "单元格", "表格", "空段落"]


class Unit(TypedDict, total=False):
    """一条被切分的单元。`表格` 是占位行（其 `单元格` 已各自成条）。"""
    type: UnitType
    text: str
    table: int          # 表格序号（仅 单元格／表格 有）
    trig: list          # classify 命中的触发项


class Batch(TypedDict):
    """一个批次。`items` 按文档顺序；`表格` 条目只做计数与定位，不占正文配额。"""
    name: str
    items: list[Unit]


class Stats(TypedDict, total=False):
    """分母统计。`总段` 不含空段落；`_校验_五类之和` 供守恒自查。"""
    总段: int
    表格: int
    单元格: int
    正文: int
    标题: int
    中段: int
    短句: int
    目录: int
    空段落: int
    _校验_五类之和: int


def detect_levels(units: list[Unit]):
    """自动识别标题层级：不看标签叫什么，看它在文档里**实际覆盖多少内容**。

    为什么不能按标签硬编码：`问题N` 在问询回复里是顶层，在保荐工作报告里却嵌在
    「第X节 → 一、→ 问题N」之下；只用 `一、` 或 `1、` 的文件更是无节标题。
    为什么不能用"首次出现顺序"：目录页会污染——问询回复的目录里「一、发现的问题」
    出现在第一个「问题1.」之前，按顺序会把 `一、` 误判为顶层。

    判据：计算每类标题的 **span**（该标题到下一个同类标题之间的段落数），
    取**中位数**（抗目录里的孤立项），span 越大层级越高；同 span 时按出现次数少者更粗。
    """
    positions = []                             # (类别, 在 units 中的下标)
    for idx, u in enumerate(units):
        if u["type"] != "标题":
            continue
        for name, pat, _rank in LEVELS:
            if pat.match(u["text"]):
                positions.append((name, idx))
                break
    if not positions:
        return (None, None), [], {}, {}
    seq = [n for n, _i in positions]
    counts = {n: seq.count(n) for n in set(seq)}
    # span：该标题到**下一个同类标题**之间隔了多少段落（用 units 下标，不是标题序号）
    spans = {}
    for n in counts:
        idxs = [i for c, i in positions if c == n]
        vals = sorted((idxs[k + 1] if k + 1 < len(idxs) else len(units)) - i
                      for k, i in enumerate(idxs))
        spans[n] = vals[len(vals) // 2]        # 中位数，抗目录里的孤立项

    rank_of = {n: r for n, _p, r in LEVELS}
    # 候选三条件：出现 ≥2 次（排除目录里的孤立分组标题）、中位 span ≥3（真能覆盖内容）。
    # 只出现 1 次的多半是目录项（如回复目录的「一、发现的问题」），span 会撑到文末冒充顶层。
    # 深层编号（1、／（1）／①）在正文里遍地都是，出现 2 次不足为凭；浅层（节／问题／一、／（一））2 次即算
    def _min_count(n):
        return 3 if rank_of[n] >= 3 else 2
    cand = [(spans[n], -rank_of[n], -counts[n], n) for n in spans
            if counts[n] >= _min_count(n) and spans[n] >= 2]
    if not cand:
        # 通篇无编号标题（如财务报表附注：分层靠样式不靠序号）→ 不猜层级，按容量切
        pat_of = {n: p for n, p, _r in LEVELS}
        return (None, None), [], counts, spans
    span, _c, _r, top = max(cand)
    # 防跳级：当选层级比另一候选深 ≥2 级、且对方覆盖量不少于其 1/4 时，取更浅的那级
    # （例：申请报告里两处「（1）」跨了大半篇，会把 L4 误判成顶层）
    shallower = [n for n in spans
                 if counts[n] >= 2 and rank_of[n] < rank_of[top] - 1
                 and spans[n] * 4 >= spans[top]]
    if shallower:
        top = min(shallower, key=lambda n: rank_of[n])
    pat_of = {n: p for n, p, _r in LEVELS}
    rest = [n for n in spans if n != top]
    ladder = sorted(rest, key=lambda n: (-spans[n], counts[n], rank_of[n]))
    return (top, pat_of[top]), [pat_of[n] for n in ladder[1:]], counts, spans


def para_text(p) -> str:
    """取段落终稿文本：w:t 计入、w:delText 排除（接受修订口径）——实现归 docxio。"""
    return docxio.para_text(p, tabs=True, breaks=True, del_text=False)


def walk_body(body) -> Iterator[tuple[str, object]]:
    """按文档顺序产出 (kind, payload)。kind ∈ {'p','tbl'}；sdt 等容器递归下钻——实现归 docxio。"""
    yield from docxio.iter_blocks(body, dive_sdt=True)


def classify(text: str, in_table: bool) -> tuple[UnitType, list]:
    """返回 (类别, 触发项列表)。类别 ∈ 正文/表格/单元格/标题/中段/短句/目录。"""
    t = text.strip()
    if in_table:
        return "单元格", []
    if not t:
        return "短句", []
    if RE_HEAD.match(t) and len(t) <= 80:
        if RE_TOC.search(t):
            return "目录", []
        return "标题", []
    if len(t) > 40 and ("。" in t or "，" in t):
        trig = []
        if RE_DIGIT.search(t):
            trig.append("Q1")
        if RE_INFER.search(t):
            trig.append("Q2")
        if RE_OVER.search(t):
            trig.append("Q3")
        if RE_FACT.search(t):
            trig.append("Q4")
        if RE_FORE.search(t):
            trig.append("Q6")
        return "正文", trig
    if 15 < len(t) <= 40:
        return "中段", []
    return "短句", []


def anchor_of(text, top_pat=None):
    """一级锚点：按 detect_levels 识别出的模式匹配。"""
    t = text.strip()
    if top_pat is None:
        return None
    return t[:40] if top_pat.match(t) else None


def load_units(path: str) -> tuple[list[Unit], Stats]:
    """解析 docx → (units, stats)。units 为有序条目列表。"""
    body = docxio.body_of(docxio.open_docx(path))
    units = []
    total = tables = cells = empty = 0
    for kind, node in walk_body(body):
        if kind == "tbl":
            tables += 1
            n_para = 0
            for p in node.iter(W + "p"):
                n_para += 1
                cells += 1
                total += 1
                units.append({"type": "单元格", "text": para_text(p)[:200], "table": tables})
            units.append({"type": "表格", "text": "[表 %d] %d 个单元格段落" % (tables, n_para),
                          "table": tables})
            continue
        txt = para_text(node)
        if not txt.strip():
            empty += 1
            units.append({"type": "空段落", "text": ""})
            continue
        total += 1
        cat, trig = classify(txt, False)
        units.append({"type": cat, "text": txt[:400], "trig": trig})
    stats = {"总段": total, "表格": tables, "单元格": cells}
    for k in ("正文", "标题", "中段", "短句", "目录"):
        stats[k] = sum(1 for u in units if u["type"] == k)
    stats["空段落"] = empty
    stats["_校验_五类之和"] = sum(stats[k] for k in ("正文", "标题", "中段", "短句", "目录", "单元格"))
    return units, stats


def _cnt(items: list[Unit]) -> tuple[int, int]:
    return (sum(1 for u in items if u["type"] == "正文"),
            sum(1 for u in items if u["type"] == "表格"))


def _hard_split(name: str, items: list[Unit], cap_p: int, cap_t: int) -> list[Batch]:
    """块本身超容量时按序硬切（唯一允许硬切的情形）。"""
    out, buf, cp, ct = [], [], 0, 0
    for u in items:
        buf.append(u)
        if u["type"] == "正文":
            cp += 1
        elif u["type"] == "表格":
            ct += 1
        if cp >= cap_p or ct >= cap_t:
            out.append({"name": name, "items": buf})
            buf, cp, ct = [], 0, 0
    if buf:
        out.append({"name": name + "（末）", "items": buf})
    return out


def _pack(items_list, cap_prose, cap_tables):
    """贪心装箱：相邻单元合计不超容量即并入同一批。"""
    out, cur, cp, ct, cur_name = [], [], 0, 0, None
    for name, items in items_list:
        bp, bt = _cnt(items)
        if cp + bp > cap_prose or ct + bt > cap_tables:
            if cur:
                out.append({"name": cur_name, "items": cur})
            cur, cp, ct, cur_name = [], 0, 0, name
        if not cur:
            cur_name = name
            names = [name]
        else:
            names.append(name)
            base = names[0].split(" · ")[0]
            n_distinct = len({x.split(" · ")[0] for x in names})
            cur_name = base if n_distinct == 1 else "%s 等 %d 节/题" % (base, n_distinct)
        cur.extend(items)
        cp += bp
        ct += bt
    if cur:
        out.append({"name": cur_name, "items": cur})
    return out


def _split_by(items, pat):
    """按某一级标题切块（首个块含切点前的引子）。"""
    blocks, cur, started = [], [], False
    for u in items:
        if u["type"] == "标题" and started and pat.match(u["text"]):
            blocks.append(cur)
            cur = []
        cur.append(u)
        started = True
    if cur:
        blocks.append(cur)
    return blocks


def _fit(items, cap_p, cap_t):
    p, t = _cnt(items)
    return p <= cap_p and t <= cap_t


def _descend(name, items, pats, cap_p, cap_t):
    """块超容量时逐级下探：用下一级标题再切，直到装得下或层级用尽（末级才硬切）。"""
    if _fit(items, cap_p, cap_t) or not pats:
        if _fit(items, cap_p, cap_t):
            return [(name, items)]
        return [(h["name"], h["items"]) for h in _hard_split(name, items, cap_p, cap_t)]
    out = []
    for blk in _split_by(items, pats[0]):
        if not blk:
            continue
        head = blk[0]["text"][:24] if blk and blk[0]["type"] == "标题" else ""
        sub = (name + " · " + head) if head and head not in name else name
        out.extend(_descend(sub, blk, pats[1:], cap_p, cap_t))
    return out


def build_batches(units, cap_prose, cap_tables):
    """分段 → 节内按层级逐级下探切块 → 装箱；顺序严格保持文档顺序。"""
    (top_name, top_pat), pats, counts, _spans = detect_levels(units)
    if top_pat is None:
        # 无编号标题体系：整篇视作一节，靠容量按顺序硬切（表格多的文档自然分批）
        hs = _hard_split("（全文）", units, cap_prose, cap_tables)
        return _pack([(h["name"], h["items"]) for h in hs], cap_prose, cap_tables)
    sections, cur = [], {"name": "（文首）", "items": []}
    for u in units:
        if u["type"] == "标题":
            a = anchor_of(u["text"], top_pat)
            if a:
                if cur["items"]:
                    sections.append(cur)
                cur = {"name": a, "items": [u]}
                continue
        cur["items"].append(u)
    if cur["items"]:
        sections.append(cur)

    out, pending = [], []

    def flush():
        nonlocal pending
        if pending:
            out.extend(_pack(pending, cap_prose, cap_tables))
            pending = []

    for sec in sections:
        if _fit(sec["items"], cap_prose, cap_tables):
            pending.append((sec["name"], sec["items"]))
            continue
        flush()
        # _descend 只负责"切到装得下的块"，装箱仍交给 _pack（否则每个小块各自成批，批数爆炸）
        out.extend(_pack(_descend(sec["name"], sec["items"], pats, cap_prose, cap_tables),
                         cap_prose, cap_tables))
    flush()
    return out


def safe_name(name):
    """文件名净化：去掉扩展名与路径非法字符。"""
    base = os.path.splitext(os.path.basename(name))[0]
    return re.sub(r'[\\/:*?"<>|]', "_", base)[:40]


def safe_name(name):
    """文件名净化：去掉扩展名与路径非法字符。"""
    base = os.path.splitext(os.path.basename(name))[0]
    return re.sub(r'[\/:*?"<>|]', "_", base)[:40]


def render_md(docs, out_dir, emit_batches):
    L = ["# 复核计划（分母 · 批次 · 台账骨架）", "",
         "> 由 `plan_review.py` 生成。**分母先定死，抽样就没有借口。**", ""]
    grand = {"总段": 0, "正文": 0, "表格": 0}
    for d in docs:
        s = d["stats"]
        L.append("## %s" % d["name"])
        L.append("")
        L.append("| 类 | 数量 | 归属判据 |")
        L.append("|---|---|---|")
        L.append("| 正文段 | **%d** | 逐段过六问（人判） |" % s["正文"])
        L.append("| 表格 | **%d** | 每表判一次（表头/单位行/表注） |" % s["表格"])
        L.append("| 单元格 | %d | 随表判，不单独判 |" % s["单元格"])
        L.append("| 标题 | %d | 随序号链 |" % s["标题"])
        L.append("| 中段 15–40 字 | %d | 随所在节扫读 |" % s["中段"])
        L.append("| 短句 | %d | 随表/随节 |" % s["短句"])
        L.append("| 目录行 | %d | 不计入分母（G7 另判） |" % s.get("目录", 0))
        L.append("| 空段落 | %d | 不计入分母（无内容可判） |" % s.get("空段落", 0))
        L.append("| **总段** | **%d** | 校验：%s |" % (
            s["总段"], "✅ 五类之和相符" if s["_校验_五类之和"] == s["总段"]
            else "❌ 不符（差 %d），须回查" % (s["总段"] - s["_校验_五类之和"])))
        L.append("")
        grand["总段"] += s["总段"]
        grand["正文"] += s["正文"]
        grand["表格"] += s["表格"]

        L.append("### 批次表（%d 批 ＋ 全文批）" % len(d["batches"]))
        L.append("")
        L.append("| 批 | 对象 | 段号区间 | 正文段 | 表 | 拆轴 |")
        L.append("|---|---|---|---|---|---|")
        for i, b in enumerate(d["batches"], 1):
            idx = [u.get("line") for u in b["items"] if u.get("line")]
            rng = "%d–%d" % (min(idx), max(idx)) if idx else "—"
            p_ = sum(1 for u in b["items"] if u["type"] == "正文")
            t_ = sum(1 for u in b["items"] if u["type"] == "表格")
            L.append("| B%02d | %s | %s | %d | %d | ① 按节 |" % (i, b["name"], rng, p_, t_))
        L.append("| **B全文** | **⛔ 11 项全文性项**（A1/A3/A7/A12/B8/C15/R5/B6/B7/F/S） | 全部单元之后 | — | — | ⛔ |")
        L.append("")
        if any("概览" in b["name"] for b in d["batches"]):
            L.append("> ⚠️ 含「概览」节的批次**须移至最后**：它是全书摘要，各节一改即过期。")
            L.append("")

        if emit_batches:
            L.append("**每批必读正文段（逐段过六问；未命中不记录，命中记问题）**")
            L.append("")
            sub = os.path.join(out_dir, safe_name(d["name"]))
            os.makedirs(sub, exist_ok=True)
            for i, b in enumerate(d["batches"], 1):
                fn = os.path.join(sub, "B%02d_batch.txt" % i)
                with open(fn, "w", encoding="utf-8") as f:
                    f.write("# B%02d %s\n# 逐段过六问；不命中不记录\n" % (i, b["name"]))
                    for u in b["items"]:
                        if u["type"] == "正文":
                            f.write("[%s] %s\n" % (u.get("line", "?"), u["text"]))
                L.append("- `%s`（%d 段正文）" % (os.path.basename(fn),
                                                sum(1 for u in b["items"] if u["type"] == "正文")))
            L.append("")

    L.append("## 合计")
    L.append("")
    L.append("| 对象 | 总段 | 正文段 | 表 |")
    L.append("|---|---|---|---|")
    L.append("| %d 份 | %d | **%d** | **%d** |" % (len(docs), grand["总段"], grand["正文"], grand["表格"]))
    L.append("")
    L.append("## 台账骨架（每批一行）")
    L.append("")
    L.append("| 批 | 覆盖区间 | 正文段/表 | 五类之和核对 | 未核（具名，写「无」才是真无） | 拆轴 |")
    L.append("|---|---|---|---|---|---|")
    n = 1
    for d in docs:
        for i in range(1, len(d["batches"]) + 1):
            L.append("| %s-B%02d | | | | | |" % (d["name"][:6], i))
        L.append("| %s-B全文 | | | | | ⛔ |" % d["name"][:6])
    L.append("")
    L.append("> **完成判定**：未核归零 ＋ 各批区间首尾相接 ＋ 全文批在所有单元之后。")
    L.append("> **冲突判定**：属 ⛔ 的维度若在单元批里下结论 ⇒ 该批该项作废重判。")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="复核计划器：定分母 → 归判据 → 切批次（只读）")
    ap.add_argument("--input", action="append", required=True, help="待复核 docx（可多次）")
    ap.add_argument("--out", help="输出目录（默认 <首个文件同级>/_复核计划/）")
    ap.add_argument("--capacity-prose", type=int, default=400, help="每批正文段上限（默认 400）")
    ap.add_argument("--capacity-tables", type=int, default=50, help="每批表格上限（默认 50）")
    ap.add_argument("--emit-batches", action="store_true", help="同时导出每批必读正文段 txt")
    ap.add_argument("--json", action="store_true", help="输出结构化 JSON")
    a = ap.parse_args()

    out_dir = a.out or os.path.join(os.path.dirname(os.path.abspath(a.input[0])), "_复核计划")
    os.makedirs(out_dir, exist_ok=True)

    docs = []
    for p in a.input:
        units, stats = load_units(p)
        # 段号：以"非空段落"的序号为行号（与 extract_final_text 对齐）
        n = 0
        for u in units:
            if u["type"] in ("表格", "空段落"):
                continue
            n += 1
            u["line"] = n
        batches = build_batches(units, a.capacity_prose, a.capacity_tables)
        # 批内段号回填
        docs.append({"name": os.path.basename(p), "stats": stats, "batches": batches,
                     "units": units})
        print("[计划] %s  总段=%d 正文=%d 表=%d 单元格=%d → %d 批" % (
            os.path.basename(p), stats["总段"], stats["正文"], stats["表格"],
            stats["单元格"], len(batches)))
        if stats["_校验_五类之和"] != stats["总段"]:
            print("[警告] 五类之和 %d ≠ 总段 %d，归类有漏" % (stats["_校验_五类之和"], stats["总段"]),
                  file=sys.stderr)

    md = render_md(docs, out_dir, a.emit_batches)
    plan_path = os.path.join(out_dir, "_复核计划.md")
    with open(plan_path, "w", encoding="utf-8") as f:
        f.write(md)
    print("[计划] 已写入 %s" % plan_path)

    if a.json:
        print(json.dumps([{"name": d["name"], "stats": d["stats"],
                           "batches": [{"name": b["name"],
                                        "prose": sum(1 for u in b["items"] if u["type"] == "正文"),
                                        "tables": sum(1 for u in b["items"] if u["type"] == "表格")}
                                       for b in d["batches"]]} for d in docs],
                         ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

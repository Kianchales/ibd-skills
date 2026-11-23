#!/usr/bin/env python3
"""回复子问对位器：抽子问 → 判问句类型 → 配回复小节 → 出待填对照表（只读）。

解决什么问题
------------
R3「结论与问题对位」是全靠人翻的活：17 题、上百个子问，人工对一遍要半天，还容易
只看"答了没有"（R1）而漏"答得对不对"（R3）。本脚本把**问句类型**先判出来——
问句类型决定结论该长什么样（是否型要"是/否"、量化型要数字、合规型要条文），
再配上对应回复小节的**末段（结论句候选）**，人只需填两列：结论形态、是否对位。

用法
----
    python scripts/subquestion_map.py --input <回复.docx> [--out <md>] [--json]
                                      [--max-len 60]

输出
----
    <out>（默认 <源文件同级>/<名>_子问对位表.md）
    题号 | 子问 | 问句类型 | 子问摘要 | 对应回复小节 | 小节末段(结论候选) | 结论形态 | 对位

判据
----
    问句类型（决定 R3 的尺子）：
      量化型  ：量化／金额／占比／影响／测算        → 结论须给数字＋口径＋方法
      原因型  ：说明原因／合理性                    → 结论须给原因＋合理性结论
      合规型  ：是否合规／是否符合／是否恰当／是否满足 → 结论须给判断＋依据条文
      是否型  ：是否存在／是否构成／有无            → 结论须给「是／否」＋范围
      说明型  ：补充说明／说明／列示／介绍（兜底）    → 结论须要素齐备
"""
import argparse
import json
import os
import re
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import docxio      # noqa: E402  docx 读取公共层（0.54.0）

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
RE_Q = re.compile(r"^问题\s*(\d+)\s*[\.．、]")
RE_SUB = re.compile(r"^（(\d{1,2})）")
RE_SEC = re.compile(r"^[一二三四五六七八九十]{1,3}、")
RE_REPLY = re.compile(r"^【回复】|^【发行人回复】|^【发行人说明】")

TYPE_RULES = [
    ("量化型", re.compile(r"量化|金额|占比|比重|影响.*(多大|多少|金额)|测算|列示.*金额")),
    ("原因型", re.compile(r"原因|合理性|为何|何以")),
    ("合规型", re.compile(r"是否合规|是否符合|是否恰当|是否满足|是否准确|是否完整|是否属于")),
    ("是否型", re.compile(r"是否存在|是否构成|是否有|是否仍|有无|是否存在")),
    ("说明型", re.compile(r"补充说明|说明|列示|介绍|请.*结合")),
]


def load_paras(path):
    """正文段落列表（去空）。

    用 `body.iter(w:p)` 而非按块遍历：本脚本要吃**所有后代段落**（含表格内、文本框内），
    按块遍历会漏掉深层的——这是旧行为，抽层时原样保留。
    """
    b = docxio.open_docx(path)
    out = []
    for p in docxio.body_of(b).iter(docxio.W + "p"):
        t = docxio.para_text(p, tabs=True, breaks=False, del_text=False).strip()
        if t:
            out.append(t)
    return out


def qtype(text):
    for name, rx in TYPE_RULES:
        if rx.search(text):
            return name
    return "说明型"


def split_questions(paras):
    """按"问题N."切题；题内含 提问块 / 回复块。"""
    idx = [i for i, t in enumerate(paras) if RE_Q.match(t)]
    marks = []
    for k, i in enumerate(idx):
        marks.append((i, idx[k + 1] if k + 1 < len(idx) else len(paras)))
    items = []
    for i, e in marks:
        title = paras[i]
        no = RE_Q.match(title).group(1)
        # 提问块 / 回复块
        cut = None
        for j in range(i, e):
            if RE_REPLY.match(paras[j]):
                cut = j
                break
        ask = paras[i + 1:cut] if cut else paras[i + 1:e]
        rep = paras[cut + 1:e] if cut else []
        # 子问
        joined = "\n".join(ask)
        marks = list(re.finditer(r"（(\d{1,2})）", joined))
        # 按编号回落切"列表组"：问题原文常先有一段带（1）（2）（3）的背景陈述，
        # 真正的子问在后面重新从（1）起。取**最后一组从 1 开始且连续**的列表。
        groups, cur = [], []
        for k, m in enumerate(marks):
            num = int(m.group(1))
            end = marks[k + 1].start() if k + 1 < len(marks) else len(joined)
            if cur and num != cur[-1][0] + 1:
                groups.append(cur)
                cur = []
            cur.append((num, m.end(), end, joined[m.end():end]))
        if cur:
            groups.append(cur)
        starts_one = [g for g in groups if g[0][0] == 1]
        pick = starts_one[-1] if starts_one else (groups[-1] if groups else [])
        subs = [(str(num), seg.strip().replace("\n", " ")[:400])
                for num, _s, _e, seg in pick]
        if not subs:
            merged = joined.strip().replace("\n", " ")[:400]
            subs = [("—", merged)] if merged else []
        # 回复小节
        secs = [(j, t) for j, t in enumerate(rep) if RE_SEC.match(t)]
        # 目录页的"问题N."没有【回复】且提问块极短 → 不是正文题，跳过
        if cut is None and len(ask) < 3:
            continue
        items.append({"no": no, "title": title, "ask": ask, "subs": subs,
                      "reply": rep, "secs": secs})
    best = {}
    for it in items:
        k = it["no"]
        if k not in best or len(it["reply"]) > len(best[k]["reply"]):
            best[k] = it
    return [best[k] for k in sorted(best, key=lambda x: int(x))]


def sec_tail(rep, start, end, maxlen):
    """回复小节的末段（结论句候选，跳过表格碎片）。"""
    body = [t for t in rep[start + 1:end] if len(t) > 20]
    return (body[-1][:maxlen] if body else "（无正文段）")


def render(items, src, maxlen):
    L = ["# 回复子问对位表（R3 待填）", "",
         "- 源文件：`%s`" % os.path.basename(src),
         "- 用法：先看「问句类型」认尺子，再读「小节末段」判结论是否对位，**填最后两列**。",
         "- 判据：是否型→须给「是/否」＋范围；原因型→原因＋合理性结论；量化型→数字＋口径＋方法；"
         "合规型→判断＋依据条文；说明型→要素齐备。", ""]
    stat = []
    for it in items:
        n_sub, n_sec = len(it["subs"]), len(it["secs"])
        unnum = (n_sub == 1 and it["subs"][0][0] == "—")
        stat.append((it["no"], it["title"], n_sub, n_sec, unnum))
        unnumbered = (n_sub == 1 and it["subs"][0][0] == "—")
        if unnumbered:
            note = "　（无编号子问：整段作答、分 %d 小节，不按数量比对）" % n_sec
        elif n_sub == n_sec:
            note = ""
        else:
            note = "　⚠️ 数量不等，逐条看是否合并作答或漏答"
        L.append("## 问题 %s（子问 %d ／ 回复小节 %d）%s" % (it["no"], n_sub, n_sec, note))
        L.append("")
        L.append("| # | 子问摘要 | 问句类型 | 对应回复小节 | 小节末段（结论候选） | 结论形态 | 是否对位 |")
        L.append("|---|---|---|---|---|---|---|")
        for k, (sn, stext) in enumerate(it["subs"]):
            if k < len(it["secs"]):
                j, sect = it["secs"][k]
                nxt = it["secs"][k + 1][0] if k + 1 < len(it["secs"]) else len(it["reply"])
                tail = sec_tail(it["reply"], j, nxt, maxlen)
                col = sect[:26]
            else:
                tail, col = "（无对应小节）", "—"
            L.append("| %s | %s | **%s** | %s | %s |  |  |" % (
                sn, stext[:maxlen].replace("|", "／"), qtype(stext),
                col.replace("|", "／"), tail.replace("|", "／")))
        L.append("")
    L.append("## 汇总")
    L.append("")
    L.append("| 题 | 标题 | 子问数 | 回复小节数 | 提示 |")
    L.append("|---|---|---|---|---|")
    for no, title, a, b, unnum in stat:
        if unnum:
            mark = "—（无编号子问）"
        elif a == b:
            mark = "✅"
        else:
            mark = "⚠️ 不等，须人工确认"
        L.append("| %s | %s | %d | %d | %s |" % (no, title[:30], a, b, mark))
    L.append("")
    L.append("> **机判只做两件事**：认问句类型、把子问与回复小节按序配对。**结论是否对位必须人来判**——"
             "机器无法替你看懂「答的是不是问的那件事」。")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="回复子问对位器（只读）")
    ap.add_argument("--input", required=True, help="问询回复 docx")
    ap.add_argument("--out", help="输出 md（默认 <源文件同级>/<名>_子问对位表.md）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--max-len", type=int, default=60, help="摘要截断长度（默认 60）")
    a = ap.parse_args()

    paras = load_paras(a.input)
    items = split_questions(paras)
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.input)),
                                os.path.splitext(os.path.basename(a.input))[0] + "_子问对位表.md")
    md = render(items, a.input, a.max_len)
    with open(out, "w", encoding="utf-8") as f:
        f.write(md)

    tot_sub = sum(len(i["subs"]) for i in items)
    tot_sec = sum(len(i["secs"]) for i in items)
    diff = [i["no"] for i in items
            if not (len(i["subs"]) == 1 and i["subs"][0][0] == "—")
            and len(i["subs"]) != len(i["secs"])]
    print("[对位] 题数=%d 子问=%d 回复小节=%d 数量不等=%d 题%s" % (
        len(items), tot_sub, tot_sec, len(diff), ("（%s）" % ",".join(diff)) if diff else ""))
    print("[对位] 已写入 %s" % out)
    if diff:
        print("[提示] 数量不等的题：逐条看是「合并作答」还是「漏答」——R1 管漏答，R3 管答偏。",
              file=sys.stderr)

    if a.json:
        print(json.dumps([{"no": i["no"], "subs": len(i["subs"]), "secs": len(i["secs"])}
                          for i in items], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

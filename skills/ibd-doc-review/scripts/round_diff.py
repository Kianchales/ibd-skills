#!/usr/bin/env python3
"""round_diff.py — 跨轮次复核状态追踪（上轮问题 → 本轮处置）

为什么需要它（2026-10-20 立）：
  L2 档位复核是**多轮迭代**：改一版 → 全量复核（不是只核变动）→ 再改。此前每轮都从零出清单，
  「上轮 20 条里哪几条改好了、哪几条没动、这轮又新冒了什么」全靠人工对着两份 Excel 数。
  计数模型天然可算：**清单条目带 `anchor`（原文问题句段的精确子串）**，它随原文改动而变——
  所以「上轮 anchor 在本轮清单里还在不在」就是「这条问题还在不在」的可复算代理。

五态口径（判据可复算，不靠感觉；**保守方向＝宁可报「还在」也不轻易报「关闭」**）：
  ① 未修复·原句未动  归一化后**完全相同**的 anchor ⇒ 原句一字未动，问题照旧
  ② 未修复·已改写    相似度 ≥ --hi（默认 0.85）但不是完全相同 ⇒ 句子动过（改数字/换措辞），
                     **本轮复核仍把它标出来** ⇒ 问题仍在
  ③ 疑似已关闭       相似度落在 [--lo, --hi)（默认 0.60–0.85）⇒ 措辞大改，本轮未再逐字命中，
                     **须人工确认是不是真改掉了**（本档故意不自动下结论，退出码会提醒）
  ④ 已关闭           相似度 < --lo ⇒ 原句已不存在，本轮也未再报
  ⑤ 新增             本轮条目在本轮未匹配到上轮任何一条

⚠ 边界（必须知道，否则会误读台账）：
  · 关键前提：**本轮清单＝本轮复核判定「仍然存在」的问题**。所以「上轮条目在本轮清单里出现」
    就等价于「问题还在」，差别只是原句动没动（①②）。反之不在清单里（④）未必等于改好了——
    也可能是整段被删、或本轮复核范围收窄（L2→L1）而没查。故 ③④ 均须与**报告头范围声明**对照。
  · 判据只认 `anchor`；`title` 不作匹配键（同标题不同段落的问题很常见）。

**清单留档规约（这条不用它就跑不了多轮）**：每轮清单按
  `<原文名>_<YYYYMMDD>_v<N>_issues.json` 与复核报告**同目录**留档，全轮次不删（单份 3–8 KB）。
  名字里有日期与轮次号，`--find-prev` 才能按「日期＋轮次」自动认出上一份。

用法：
    python round_diff.py --prev 上轮清单.json --cur 本轮清单.json
    python round_diff.py --find-prev <目录> --cur 本轮清单.json   # 自动挑上一轮（按日期＋vN）
    python round_diff.py --prev a.json --cur b.json --out 轮次台账.md --round 3
    python round_diff.py --prev a.json --cur b.json --json
    python round_diff.py --self-test          # 内置三档夹具自检

退出码：0 = 正常产出；1 = 有待人工确认项（③ 档非空）；2 = 用法／环境错误。
  —— 把「有待核」做成退出码而不是提示，是为了让调用方**不能装作没看见**。
"""
import argparse
import io
import json
import os
import re
import sys
import unicodedata

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

SEV_ORDER = {"高": 0, "中": 1, "低": 2}
# 归一化时剔除的字符：空白、常见中西标点、书名号/引号（原文换排版会动这些，不动语义）
STRIP_CHARS = set(" \t\r\n\u3000·、，。；：？！“”‘’《》〈〉【】（）()[]{}<>\"'`,.;:?!-_—…／/\\|~")


def norm(s):
    """归一化：全角转半角 ＋ 删美化字符 ＋ 小写。只抹排版差异，不抹语义。"""
    s = unicodedata.normalize("NFKC", s or "")
    return "".join(ch for ch in s if ch not in STRIP_CHARS).lower()


def ratio(a, b):
    """相似度（difflib，零依赖）。a/b 为已归一化文本。"""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a, b).ratio()


def load_list(path):
    """读问题清单 JSON；容忍 `{"issues": [...]}` 包一层与 BOM。"""
    with io.open(path, encoding="utf-8-sig") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        data = data.get("issues") or data.get("items") or []
    if not isinstance(data, list):
        raise ValueError("清单不是数组：%s" % path)
    for i, it in enumerate(data):
        if not isinstance(it, dict) or "anchor" not in it:
            raise ValueError("第 %d 条缺 anchor：%s" % (i + 1, path))
    return data


def match(prev, cur, hi=0.85, lo=0.60):
    """返回 (rows, stats)。rows 每条带 state/score/hit_index。"""
    cur_norm = [norm(c["anchor"]) for c in cur]
    used = [False] * len(cur)
    rows = []

    # 第一轮：完全一致优先（避免「最近似」把已修项抢走）
    for pi, p in enumerate(prev):
        pn = norm(p["anchor"])
        hit = None
        for ci, cn in enumerate(cur_norm):
            if not used[ci] and cn == pn:
                hit = ci
                break
        if hit is None:
            continue
        used[hit] = True
        rows.append({"state": "未修复·原句未动", "score": 1.0, "prev": p, "cur": cur[hit]})

    # 第二轮：近似匹配（只处理第一轮没配上的）
    unmatched_prev = [i for i, p in enumerate(prev)
                      if not any(r["prev"] is p for r in rows)]
    for pi in unmatched_prev:
        pn = norm(prev[pi]["anchor"])
        best, best_ci = 0.0, None
        for ci, cn in enumerate(cur_norm):
            if used[ci]:
                continue
            r = ratio(pn, cn)
            if r > best:
                best, best_ci = r, ci
        if best_ci is not None and best >= hi:
            used[best_ci] = True
            rows.append({"state": "未修复·已改写", "score": best,
                         "prev": prev[pi], "cur": cur[best_ci]})
        elif best_ci is not None and best >= lo:
            used[best_ci] = True
            rows.append({"state": "疑似已关闭", "score": best,
                         "prev": prev[pi], "cur": cur[best_ci]})
        else:
            rows.append({"state": "已关闭", "score": best, "prev": prev[pi], "cur": None})

    for ci, c in enumerate(cur):
        if not used[ci]:
            rows.append({"state": "新增", "score": None, "prev": None, "cur": c})

    order = {"未修复·原句未动": 0, "未修复·已改写": 1, "新增": 2, "疑似已关闭": 3, "已关闭": 4}
    rows.sort(key=lambda r: (order[r["state"]],
                             SEV_ORDER.get((r["cur"] or r["prev"]).get("sev", "中"), 9)))
    stats = {k: sum(1 for r in rows if r["state"] == k)
             for k in ("未修复·原句未动", "未修复·已改写", "疑似已关闭", "已关闭", "新增")}
    stats["上轮条数"] = len(prev)
    stats["本轮条数"] = len(cur)
    stats["关闭率"] = round(stats["已关闭"] / len(prev), 4) if prev else None
    return rows, stats


RE_ROUNDED = re.compile(r"(\d{8}).*?[vV](\d+)")
RE_ANY_DATE = re.compile(r"(\d{8})")


def find_prev(directory, cur_path, prefer_suffix="issues"):
    """按**文件名里的日期＋轮次号**挑上一轮清单（B 的半边：清单留档规约的消费端）。

    为什么不在目录里「挑最新的 JSON」：目录里还躺着台账 md、报告 xlsx、meta json——
    按 mtime 或随便挑都会认错文件。**判据只认文件名**：`<原文名>_<YYYYMMDD>_v<N>_issues.json`。
    刻意不猜：认不出就报错并列出候选，让人改名，而不是默默拿个错的去比对。
    """
    cur_abs = os.path.abspath(cur_path) if cur_path else ""
    cands = []
    for name in sorted(os.listdir(directory)):
        if not name.lower().endswith(".json"):
            continue
        if prefer_suffix and prefer_suffix not in name.lower():
            continue
        path = os.path.join(directory, name)
        if os.path.abspath(path) == cur_abs or not os.path.isfile(path):
            continue
        m = RE_ROUNDED.search(name)
        if m:
            key = (m.group(1), int(m.group(2)))
        else:
            m2 = RE_ANY_DATE.search(name)
            if not m2:
                continue
            key = (m2.group(1), 0)
        cands.append((key, name, path))
    if not cands:
        raise ValueError("目录内找不到可作「上轮清单」的 JSON（须含 8 位日期；建议命名 "
                         "`<原文名>_<YYYYMMDD>_v<N>_issues.json`）：%s" % directory)
    cands.sort()
    key, name, path = cands[-1]
    return path, [c[1] for c in cands]


def render_md(rows, stats, prev_path, cur_path, rnd):
    L = []
    L.append("# 复核轮次台账%s" % ("（第 %s 轮）" % rnd if rnd else ""))
    L.append("")
    L.append("> 生成：`round_diff.py`｜上轮清单＝`%s`｜本轮清单＝`%s`"
             % (os.path.basename(prev_path), os.path.basename(cur_path)))
    L.append("> **读法**：「已修复」与「疑似仍在」两档**须人工过目**后才计入关闭——"
             "句子改了说法但问题仍在会落进后者；整段删除而问题转移会落进前者。")
    L.append("")
    L.append("| 指标 | 值 |")
    L.append("|---|---|")
    L.append("| 上轮条数 | %d |" % stats["上轮条数"])
    L.append("| 本轮条数 | %d |" % stats["本轮条数"])
    L.append("| 未修复·原句未动 | %d |" % stats["未修复·原句未动"])
    L.append("| 未修复·已改写 | %d |" % stats["未修复·已改写"])
    L.append("| 疑似已关闭（待人工确认） | %d |" % stats["疑似已关闭"])
    L.append("| 已关闭（原句已不存在） | %d |" % stats["已关闭"])
    L.append("| 本轮新增 | %d |" % stats["新增"])
    if stats["关闭率"] is not None:
        L.append("| 关闭率（④／上轮条数） | %.1f%% |" % (stats["关闭率"] * 100))
    L.append("")
    L.append("## 逐条台账")
    L.append("")
    L.append("| # | 状态 | 相似度 | 严重度 | 问题标题 | 位置锚点（节选） |")
    L.append("|---|---|---|---|---|---|")
    for i, r in enumerate(rows, 1):
        src = r["cur"] or r["prev"]
        sc = "—" if r["score"] is None else ("%.2f" % r["score"])
        anchor = (src.get("anchor") or "").replace("|", "\\|").replace("\n", " ")
        if len(anchor) > 40:
            anchor = anchor[:40] + "…"
        L.append("| %d | %s | %s | %s | %s | %s |"
                 % (i, r["state"], sc, src.get("sev", ""),
                    (src.get("title") or "").replace("|", "\\|"), anchor))
    L.append("")
    return "\n".join(L) + "\n"


SELF_TEST_PREV = [
    {"anchor": "公司2026年1-6月营业收入较上年同期增长23.5%", "type": "数据·勾稽", "sev": "高",
     "title": "营收增幅与明细表不符", "desc": "x"},
    {"anchor": "本次募集资金投资项目预计税后内部收益率为18.2%", "type": "数据·口径", "sev": "中",
     "title": "IRR 口径未披露", "desc": "x"},
    {"anchor": "公司不存在对持续经营能力产生重大不利影响的事项", "type": "表述·绝对化", "sev": "中",
     "title": "绝对化表述", "desc": "x"},
]
SELF_TEST_CUR = [
    # 一字未动 → 未修复·原句未动
    {"anchor": "公司2026年1-6月营业收入较上年同期增长23.5%", "type": "数据·勾稽", "sev": "高",
     "title": "营收增幅与明细表不符", "desc": "x"},
    # 只改了一个数字、句子基本没动 → 未修复·已改写
    {"anchor": "本次募集资金投资项目预计税后内部收益率为18.0%", "type": "数据·口径", "sev": "中",
     "title": "IRR 口径未披露", "desc": "x"},
    # 换了大半措辞 → 疑似已关闭（待人工核）
    {"anchor": "截至报告期末，公司不存在影响持续经营能力的重大不确定性事项", "type": "表述·绝对化",
     "sev": "中", "title": "绝对化表述", "desc": "x"},
    # 新问题 → 新增
    {"anchor": "报告期内公司毛利率分别为31.2%、29.8%和30.5%", "type": "数据·完整性", "sev": "低",
     "title": "毛利率缺一期", "desc": "x"},
]


def self_test():
    """三档夹具自检：未修复／疑似仍在／新增／已修复 各命中且计数守恒。"""
    rows, stats = match(SELF_TEST_PREV, SELF_TEST_CUR)
    exp = {"未修复·原句未动": 1, "未修复·已改写": 1, "疑似已关闭": 1, "已关闭": 0, "新增": 1}
    got = {k: stats[k] for k in exp}
    ok = got == exp
    print("[self-test] 五档计数 = %s，期望 = %s ⇒ %s" % (got, exp, "PASS" if ok else "FAIL"))
    tot = stats["未修复·原句未动"] + stats["未修复·已改写"] + stats["疑似已关闭"] + stats["已关闭"]
    print("[self-test] 上轮条数守恒：%d = %d ⇒ %s"
          % (stats["上轮条数"], tot, "PASS" if stats["上轮条数"] == tot else "FAIL"))
    # 阴性对照：本轮空清单 → 全部计「已关闭」，不得凭空出现「未修复」
    rows2, stats2 = match(SELF_TEST_PREV, [])
    neg = (stats2["未修复·原句未动"] == 0 and stats2["未修复·已改写"] == 0
           and stats2["已关闭"] == len(SELF_TEST_PREV))
    print("[self-test] 阴性对照（本轮空清单）→ 已关闭 %d／未修复合计 %d ⇒ %s"
          % (stats2["已关闭"], stats2["未修复·原句未动"] + stats2["未修复·已改写"],
             "PASS" if neg else "FAIL"))
    return 0 if (ok and neg and stats["上轮条数"] == tot) else 1


def main():
    ap = argparse.ArgumentParser(description="跨轮次复核状态追踪（四态台账）")
    ap.add_argument("--prev", help="上轮问题清单 JSON（与 --find-prev 二选一）")
    ap.add_argument("--find-prev", default=None, metavar="DIR",
                    help="在目录内按文件名（日期＋vN）自动挑上一轮清单；--prev 显式给出时以 --prev 为准")
    ap.add_argument("--cur", help="本轮问题清单 JSON")
    ap.add_argument("--out", default=None, help="台账落盘路径（.md）；缺省只打印")
    ap.add_argument("--round", default=None, help="轮次号（仅用于标题）")
    ap.add_argument("--hi", type=float, default=0.85, help="高于此相似度判「未修复」（默认 0.85）")
    ap.add_argument("--lo", type=float, default=0.60, help="低于此相似度判「已修复」（默认 0.60）")
    ap.add_argument("--json", action="store_true", help="结构化输出（不写 md）")
    ap.add_argument("--self-test", action="store_true", help="内置夹具自检")
    a = ap.parse_args()

    if a.self_test:
        return self_test()
    if not a.cur:
        print("错误：--cur 必填（或用 --self-test）", file=sys.stderr)
        return 2
    if not a.prev and a.find_prev:
        try:
            a.prev, _cands = find_prev(a.find_prev, a.cur)
        except (OSError, ValueError) as e:
            print("错误：%s" % e, file=sys.stderr)
            return 2
        # --json 时提示必须走 stderr：stdout 只能有那一个 JSON（否则调用方解析必炸）
        print("[--find-prev] 采用上轮清单：%s（候选 %d 份）"
              % (os.path.basename(a.prev), len(_cands)),
              file=(sys.stderr if a.json else sys.stdout))
    if not a.prev:
        print("错误：--prev 或 --find-prev 至少给一个（或用 --self-test）", file=sys.stderr)
        return 2
    if a.lo > a.hi:
        print("错误：--lo 不得大于 --hi", file=sys.stderr)
        return 2
    try:
        prev, cur = load_list(a.prev), load_list(a.cur)
    except (OSError, ValueError) as e:
        print("错误：%s" % e, file=sys.stderr)
        return 2

    rows, stats = match(prev, cur, hi=a.hi, lo=a.lo)
    if a.json:
        print(json.dumps({"tool": "round_diff", "stats": stats,
                          "items": [{"state": r["state"], "score": r["score"],
                                     "prev": r["prev"], "cur": r["cur"]} for r in rows]},
                         ensure_ascii=False, indent=2))
    else:
        md = render_md(rows, stats, a.prev, a.cur, a.round)
        if a.out:
            with io.open(a.out, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(md)
            print("台账已写入：%s" % a.out)
        print("上轮 %d 条 → 本轮 %d 条：" % (stats["上轮条数"], stats["本轮条数"]))
        print("  未修复·原句未动 %d ／未修复·已改写 %d ／疑似已关闭 %d ／已关闭 %d ／新增 %d"
              % (stats["未修复·原句未动"], stats["未修复·已改写"], stats["疑似已关闭"],
                 stats["已关闭"], stats["新增"]))
        if stats["关闭率"] is not None:
            print("  关闭率（已关闭／上轮条数）：%.1f%%" % (stats["关闭率"] * 100))
        if stats["疑似已关闭"]:
            print("⚠ %d 条落在「疑似已关闭」档：措辞大改、本轮未逐字命中——须逐条人工确认是否真改掉；"
                  "并核对本轮报告头的范围声明（范围收窄会造成假关闭）。" % stats["疑似已关闭"])
    return 1 if stats["疑似已关闭"] else 0


if __name__ == "__main__":
    sys.exit(main())

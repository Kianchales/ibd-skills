#!/usr/bin/env python3
"""S7 回写工作表生成器：把「回写清单候选 × 单案新条目 × 主库旧条目」三方汇编成一份工作表，
使回写起草时上下文一次到位（免去逐条开文件的来回读）。

用法：
    # ① 回写工作表（S7 起草时一次到位）
    python gen_replay_worksheet.py --case 1 [--filter 中高] [--list <清单路径>] [--methods-root <工作区根>]
    # ② 回响检查（级联 · S7 收尾必跑）：列出「清单未覆盖但受实质影响」的条目候选
    python gen_replay_worksheet.py --echo --case 1 [--keywords 明股实债,票据] [--methods-root <工作区根>]

参数：
    --case          清单节序号（1=第 1 案…，与清单 `### N. 案名` 对应）；**回响模式下可省**
    --filter        只取指定重合度（高 / 中高 / 中 / 全部，默认全部）
    --list          回写清单路径（默认 <工作区根>/tasks/建议回写清单.md）
    --echo          回响检查模式：按关键词**全库扫**（跨案域／语言专项／分卷），列出命中**且不在清单
                    已见编号集合**里的条目 —— 即**候选清单未覆盖但受实质影响**者。**只列候选、不作判断**。
    --keywords      回响模式关键词（逗号分隔）。⚠️ 关键词越通用命中越多（如「票据」这类词会命中大量
                    仅顺带提及的条目）——**建议用案名、专有实体或明确的主张短语**，让清单短而准。
    --methods-root  方法论库所在的工作区根（其下应有 methods/、tasks/）；默认 $METHODS_ROOT

输出：<工作区根>/tasks/_replay_ws_case<N>_<YYYYMMDD>.md
"""
import argparse, glob, io, os, re, sys, datetime
from pathlib import Path

import sys
import os as _lo, sys as _ls
_ls.path.insert(0, _lo.path.dirname(_lo.path.abspath(__file__)))
from _lib.layout import (METHODS_NAME, SINGLE_NAME, TOC_FILE, DIR_DOMAIN,
                         FINANCE_DOMAIN_FILE, LAW_DOMAIN_FILE, INDUSTRY_DOMAIN_FILE)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_ap = argparse.ArgumentParser(description="S7 回写工作表生成器 ＋ 回响检查（级联候选）")
_ap.add_argument("--case", type=int, default=0, help="清单节序号（回响模式下可省，改由 --keywords 给关键词）")
_ap.add_argument("--filter", default="", help="重合度筛选（高/中高/中）")
_ap.add_argument("--list", default="", help="回写清单路径")
_ap.add_argument("--echo", action="store_true",
                 help="**回响检查模式**：按关键词全库扫，列出「清单未覆盖但受实质影响」的条目候选（只列不判）")
_ap.add_argument("--keywords", default="", help="回响模式的关键词（逗号分隔，如「明股实债,票据」）")
_ap.add_argument("--methods-root", default=os.environ.get("METHODS_ROOT", ""),
                 help="方法论库所在的工作区根（默认 $METHODS_ROOT，或脚本上级目录）")
_a = _ap.parse_args()

ROOT = Path(_a.methods_root) if _a.methods_root else Path(__file__).resolve().parents[1]
LIB = ROOT / METHODS_NAME
LIST = Path(_a.list) if _a.list else ROOT / "tasks" / "建议回写清单.md"
if not LIB.is_dir():
    sys.exit("✗ 未找到方法论库：%s\n  用法：--methods-root <库所在的工作区根>（其下应有 methods/ 子目录）" % LIB)

# ── 回响检查（级联 · 清单未覆盖但受实质影响者） ──────────────────────────────
# 为什么需要它：回写由清单驱动，**清单只能覆盖它看见的**。受本批同实体／同口径／同主张影响、
#   却未被列进清单的旧条目，此前**永远不会被回写**（机制层面有「被取代」块的写法，缺的是
#   **触发器**：谁去发现该加块的旧条目）。本模式即那个触发器——按关键词**全库扫一遍**，
#   把「命中关键词 且 不在清单已见集合里」的条目列出来，交人裁定。
ID_IN_HEAD = re.compile(r"((?:WL|PL|I-CL|[FLIWS])-(?:AN\d{4}|\d{6})(?:-\d{1,3})?)")


def echo_mode():
    kws = [k.strip() for k in (_a.keywords or "").split(",") if k.strip()]
    if _a.case:
        try:
            _t = io.open(LIST, encoding="utf-8").read().split("\n")
            for i, l in enumerate(_t):
                if re.match(r"^### %d\. " % _a.case, l):
                    kws.insert(0, re.match(r"^### \d+\. ([^_（]+)", l).group(1))
                    break
        except OSError:
            pass
    if not kws:
        sys.exit("✗ 需给 --keywords（逗号分隔）或 --case")
    seen = set()
    try:
        for i, l in enumerate(io.open(LIST, encoding="utf-8").read().split("\n")):
            for m in ID_IN_HEAD.finditer(l):
                seen.add(m.group(1))
    except OSError:
        pass
    scan = [str(LIB / DIR_DOMAIN), str(LIB / "20_语言专项"), str(LIB / "50_分卷")]
    hits = []
    for d in scan:
        for fp in sorted(glob.glob(os.path.join(d, "*.md"))):
            try:
                lines = io.open(fp, encoding="utf-8", errors="replace").read().split("\n")
            except OSError:
                continue
            cur_id, cur_hit, buf = "", [], []
            def _flush():
                if cur_id and cur_hit and cur_id not in seen:
                    hits.append((os.path.relpath(fp, str(LIB)).replace("\\", "/"),
                                 cur_id, cur_hit, buf[0].strip()[:70]))
            for l in lines:
                if l.startswith("### "):
                    _flush()
                    mm = ID_IN_HEAD.search(l)
                    cur_id, cur_hit, buf = (mm.group(1) if mm else ""), [], [l]
                    for k in kws:
                        if k in l:
                            cur_hit.append(k)
                else:
                    if cur_id and l.strip() and len(buf) < 3:
                        buf.append(l)
                    if cur_id:
                        for k in kws:
                            if k in l and k not in cur_hit:
                                cur_hit.append(k)
            _flush()
    out = ROOT / "tasks" / ("_回响检查_%s.md" % (_a.case and ("案%d" % _a.case) or "关键词"))
    with io.open(str(out), "w", encoding="utf-8", newline="\n") as f:
        f.write("# 回响检查（级联）—— 清单未覆盖但受实质影响者\n\n")
        f.write("> 关键词：%s ｜ 清单已见编号 %d 个 ｜ 命中 **%d** 条\n"
                "> **用途**：逐条裁定「是否需回写／是否需加『已被取代』块」；**本表只列候选、不作判断**。\n\n"
                % ("、".join(kws), len(seen), len(hits)))
        f.write("| # | 位置 | 编号 | 命中关键词 | 标题 |\n|---|---|---|---|---|\n")
        for i, (fp, eid, hk, t) in enumerate(hits, 1):
            f.write("| %d | `%s` | `%s` | %s | %s |\n" % (i, fp, eid, "／".join(hk[:4]), t))
    print("回响检查完成：关键词 %s ｜ 清单已见 %d ｜ **未覆盖但命中 %d 条**"
          % ("、".join(kws), len(seen), len(hits)))
    print("落点：%s" % out)
    for fp, eid, hk, t in hits[:15]:
        print("  · %s ｜ %s ｜ %s" % (eid, "／".join(hk[:3]), t[:50]))


if _a.echo:
    echo_mode()
    sys.exit(0)

if not _a.case:
    sys.exit("✗ 回写工作表模式需 --case <清单节序号>；若要做级联回响检查，请加 --echo")

if not LIST.exists():
    sys.exit("✗ 未找到回写清单：%s\n  可用 --list 指定" % LIST)

toc = io.open(str(LIB / TOC_FILE), encoding='utf-8').read()

# ---------- 1. 解析清单指定案节 ----------
txt = io.open(LIST, encoding='utf-8').read().split('\n')
start = None
for i, l in enumerate(txt):
    if re.match(r"^### %d\. " % _a.case, l):
        start = i
        break
if start is None:
    sys.exit("✗ 清单里找不到第 %d 案节" % _a.case)
end = len(txt)
for j in range(start + 1, len(txt)):
    if txt[j].startswith('### '):
        end = j
        break
head = txt[start]
case_name = re.match(r"^### \d+\. ([^_（]+)", head).group(1)
rows = []
for l in txt[start:end]:
    m = re.match(r"\|\s*\[([ x])\]\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(.*?)\s*\|", l)
    if m:
        rows.append(dict(done=m.group(1) == 'x', new=m.group(2), old=m.group(3),
                         deg=m.group(4), note=m.group(5)))
if _a.filter and _a.filter != '全部':
    rows = [r for r in rows if r['deg'].strip() == _a.filter.strip()]   # 精确匹配（防「高」误命中「中高」）
print("案：%s ｜ 候选 %d 条%s" % (case_name, len(rows), ("（筛 %s）" % _a.filter) if _a.filter else ""))

# ---------- 2. 定位单案文件 ----------
cand = [p for p in glob.glob(str(LIB / SINGLE_NAME / "*.md")) if case_name in os.path.basename(p)]
CASE = cand[0] if cand else ""
CL = io.open(CASE, encoding='utf-8').read().split('\n') if CASE else []
print("单案文件：%s" % (os.path.basename(CASE) or "（未找到）"))


def new_entry(code):
    """清单「新案条目」列形如 `F-ZKY-06 标题…` / `F-AN0023-01 标题…`（含标题文字）——
    先取编号（域 + 序号），再按序号在单案文件里匹配 `### <域>-AN<案号4位>-<序号>`。"""
    mm = re.match(r"^([FLI])-(?:AN\d{4}|[A-Za-z]{2,4})-(\d{2})", code.strip())
    if not mm:
        return ""
    pat = re.compile(r"^### %s-AN\d{4}-%s(?![0-9])" % (mm.group(1), mm.group(2)))
    for i, l in enumerate(CL):
        if pat.match(l):
            j = i + 1
            while j < len(CL) and not CL[j].startswith('### '):
                j += 1
            return "\n".join(x for x in CL[i:j] if x.strip())
    return ""


def old_entry(code):
    """清单「既有方法论对应条目」列（可能含多个编号，取首个）→ 目录查行号 → 取主库条目块。"""
    m = re.search(r"([FLI]-\d{6})", code)
    if not m:
        return "(旧条目编号未识别)"
    cid = m.group(1)
    tm = re.search(r"\|\s*" + cid + r"\s*\|(.*?)\|\s*(\d+)\s*\|", toc)
    if not tm:
        return "(目录中无此编号)"
    fmap = {"F": FINANCE_DOMAIN_FILE, "L": LAW_DOMAIN_FILE, "I": INDUSTRY_DOMAIN_FILE}
    f = LIB / DIR_DOMAIN / fmap[cid[0]]
    if not f.exists():
        return "(域文件缺失)"
    lines = io.open(f, encoding='utf-8').read().split('\n')
    ln = int(tm.group(2))
    if ln - 1 >= len(lines) or not lines[ln - 1].startswith('### ' + cid):
        return "(行号与条目不符：索引可能过期，请先跑 refresh_index.py)"
    blk = []
    for k in range(ln - 1, min(ln + 13, len(lines))):
        if k > ln - 1 and (lines[k].startswith('### ') or lines[k].strip() == '---'):
            break
        blk.append(lines[k])
    return "\n".join(blk)


# ---------- 3. 汇编 ----------
out = ["# S7 回写工作表 · 第 %d 案 %s（%s）" % (_a.case, case_name, datetime.date.today()),
       "", "> 用途：清单候选 × 单案新条目 × 主库旧条目 三方对照，供逐条起草回写文本。",
       "> 回写规则（三过滤）：高重合=旧条「本案实证」追加新案实证 ＋ 案数表述递增；",
       "> 中/中高=扩展「适用场景/特有升级」；低/新增=不回写。冲突走修订留痕，禁静默覆盖。",
       "", "## 候选一览（%d 条）" % len(rows), "",
       "| # | 状态 | 新案条目 | 旧条目 | 重合度 |", "|---|---|---|---|---|"]
for i, r in enumerate(rows, 1):
    out.append("| %d | %s | %s | %s | %s |" % (i, "已回写" if r['done'] else "待回写",
                                              r['new'], r['old'], r['deg']))
for i, r in enumerate(rows, 1):
    out += ["", "---", "", "## %d. %s → %s（%s）" % (i, r['new'], r['old'], r['deg']),
            "", "**清单说明**：%s" % r['note'], "",
            "**旧条目现状（主库）**：", "```markdown", old_entry(r['old']), "```", "",
            "**新案条目（单案文件）**：", "```markdown", new_entry(r['new']) or "(未在单案文件中匹配到：请核对编号与单案文件)", "```"]

_sfx = ("_" + _a.filter) if (_a.filter and _a.filter != '全部') else ""
OUT = ROOT / "tasks" / ("_replay_ws_case%d%s_%s.md" % (_a.case, _sfx, datetime.date.today().strftime("%Y%m%d")))
io.open(OUT, 'w', encoding='utf-8', newline="\n").write("\n".join(out))
hit = sum(1 for r in rows if new_entry(r['new']))
print("✅ 工作表已生成：%s（候选 %d 条，新案条目命中 %d 条）" % (OUT, len(rows), hit))

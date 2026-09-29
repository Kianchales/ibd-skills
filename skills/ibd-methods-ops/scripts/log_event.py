#!/usr/bin/env python3
"""操作日志追加器：向 `<工作区根>/logs/库操作日志.md` 追加**一条**事件（append-only）。

用法：
    python log_event.py --action 蒸馏 --object "案例 X 蒸馏" --result "新增 12 条｜回写 5 条" \\
        [--where <产物路径>] [--basis WO-xx] [--methods-root <工作区根>] [--cases 10]
    python log_event.py --action 体检 --object 方法论库 --result "ERROR 0 ／ WARN 1"
    python log_event.py --stats          # **派生视图**：从事件stream现算计数，不写盘

参数：
    --action   动作键（**机器可读**）：蒸馏｜回写｜体检｜索引刷新｜治理｜迁移｜升版｜未沉淀案
    --object   对象（一句话）
    --result   结果（一句话结论 ＋ 关键数字）
    --where    产物路径（可选，多条用「／」分隔）
    --basis    依据（裁定／工单号，可选）
    --cases    本次**新增案例数**（`蒸馏` ＝本次新增**案例**；`迁移` ＝历史基线固化）。落机器可读键
               `- 案数：+N`，使「累计案数」可由操作日志派生 ⇒ `state/维护体检计数.md` 得以改为指针
               **★ 语义边界（2026-09-27 补 · 承「累计案数 31 ≠ 10」复盘）**：`--cases` 只计
               **新增案例（新案入库）**。**「条目提炼／回填／共通条目沉淀」不占案数**——
               即便动作键为 `蒸馏`（如「N 案共现提炼 1 条通用条目」），若**未引入新案**，
               应**省略 `--cases`**（或传 0），否则「维护域触发进度 N/40」会被虚增。
               判据一句话：**`--cases` 数的是「案」不是「条」**。
    --stats    派生视图：读操作日志现算「事件数／各动作计数／累计案数／上次体检日／维护域触发」，
               **不写盘、不落状态**（可重算结论不进台账）
    --no-dup   若**同日同「动作+对象+结果」**已存在则跳过（防同日重复记，如反复跑同一流程；
               原判据为「仅比末条」，中间夹入其他事件即失效，2026-09-27 更正；默认开启，
               `--allow-dup` 关闭）
    --dry-run  只打印将要追加的内容，不写盘

定位（承接 `logs/库操作日志.md` 头部纪律）：
    · **发生过什么**一律进操作日志；`state/` 只回答「现在到哪了」⇒ 事件**不落 state/**。
    · **只记不可重算的源事实** —— 条目数/行号/告警数等**现算即得**的不落盘（免漂移）。
      「累计案数」看似状态、实为**源事实之和**（各次蒸馏新增量）⇒ 可派生，故由 `--stats` 现算。
    · **只追加、不修改、不删除**；一行一事件；不承载细则。

为什么要有它：把「写操作日志」从**约定**变成**一条命令**，使蒸馏／回写／体检／治理各流程都能低成本留痕；
    事件序列一旦连续，**「新增／已消」的动向**与**可重算台账的派生**（如下移「体检计数」）才具备前提。
"""
import argparse, io, os, re, sys, time

import sys as _s
if hasattr(_s.stdout, "reconfigure"):
    _s.stdout.reconfigure(encoding="utf-8")

ACTIONS = ("蒸馏", "回写", "体检", "索引刷新", "治理", "迁移", "升版", "未沉淀案")
TRIGGER_EVERY = 40          # 维护域体检触发阈值（每累计 40 案一次 · 2026-09-06 用户裁定）

_ap = argparse.ArgumentParser(description="向库操作日志追加一条事件 / 或从操作日志派生计数视图")
_ap.add_argument("--action", help="动作键（机器可读）：" + "｜".join(ACTIONS))
_ap.add_argument("--object", help="对象（一句话）")
_ap.add_argument("--result", help="结果（一句话结论 ＋ 关键数字）")
_ap.add_argument("--where", default="", help="产物路径（可选，多条用「／」分隔）")
_ap.add_argument("--basis", default="", help="依据（裁定／工单号，可选）")
_ap.add_argument("--cases", type=int, default=None, help="本次新增案例数（仅 蒸馏 用；落机器可读键）")
_ap.add_argument("--stats", action="store_true", help="派生视图：读操作日志现算计数，不写盘")
_ap.add_argument("--methods-root", default=os.environ.get("METHODS_ROOT", ""),
                 help="工作区根（默认 $METHODS_ROOT，或库根推断）")
_ap.add_argument("--allow-dup", action="store_true", help="允许与末条事件完全相同的重复记录")
_ap.add_argument("--dry-run", action="store_true", help="只打印，不写盘")
_args, _ = _ap.parse_known_args()

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)
from _lib.layout import resolve as _layout_resolve
_ROOT, METHODS, SCRIPTS = _layout_resolve(_args.methods_root)

_log = os.path.join(_ROOT, "logs", "库操作日志.md")


def parse_events(path):
    """把操作日志解析为块列表（`## [日期] 动作 | 对象` 起块）。**只读**。"""
    if not os.path.exists(path):
        return []
    ev, cur = [], None
    for ln in io.open(path, encoding="utf-8", errors="replace").read().splitlines():
        m = re.match(r"^##\s*\[(\d{4}-\d{2}-\d{2})\]\s*(\S+)\s*\|\s*(.+?)\s*$", ln)
        if m:
            cur = {"date": m.group(1), "action": m.group(2), "object": m.group(3),
                   "cases": 0, "lines": []}
            ev.append(cur)
            continue
        if cur is not None:
            cur["lines"].append(ln)
            c = re.match(r"^-\s*案数：[+＋]?(-?\d+)", ln.strip())
            if c:
                cur["cases"] += int(c.group(1))
    return ev


def show_stats():
    """**派生视图**：可重算结论**不落盘**，读时现算（原则见 state/README.md §三·6）。"""
    ev = parse_events(_log)
    if not ev:
        print("（操作日志为空或不存在：%s）" % os.path.relpath(_log, _ROOT))
        return 0
    by = {}
    for e in ev:
        by[e["action"]] = by.get(e["action"], 0) + 1
    cases = sum(e["cases"] for e in ev)
    dist_batches = sum(1 for e in ev if e["action"] == "蒸馏")
    last_health = next((e["date"] for e in reversed(ev) if e["action"] == "体检"), "—")
    last_maint = next((e["date"] for e in reversed(ev)
                       if e["action"] == "体检" and "维护" in e["object"]), "—")
    print("=== 操作日志派生视图（`log_event.py --stats` · 读时现算，不落盘）===")
    print("操作日志：%s" % os.path.relpath(_log, _ROOT))
    print("事件总数：%d ｜ 时间跨度：%s → %s" % (len(ev), ev[0]["date"], ev[-1]["date"]))
    print("各动作计数：" + "｜".join("%s %d" % (k, by[k]) for k in sorted(by)))
    print("蒸馏批次数：%d" % dist_batches)
    print("累计案数：%d（＝各次 `--cases` 之和 ＋ 迁移基线）" % cases)
    print("维护域体检触发：每累计 %d 案一次 ⇒ 本档进度 %d/%d%s"
          % (TRIGGER_EVERY, cases % TRIGGER_EVERY, TRIGGER_EVERY,
             "（**已达阈值，应触发**）" if cases and cases % TRIGGER_EVERY == 0 else ""))
    print("上次体检日期：%s ｜ 上次**维护域**体检：%s" % (last_health, last_maint))
    print("→ 台账 `state/维护体检计数.md` 已改为**指针**；本视图即其真身读数。")
    return 0


if _args.stats:
    sys.exit(show_stats())

if not (_args.action and _args.object and _args.result):
    sys.stderr.write("✗ 追加事件需同时给 `--action`／`--object`／`--result`"
                     "（只读派生视图请用 `--stats`）\n")
    sys.exit(2)
if _args.action not in ACTIONS:
    sys.stderr.write("✗ 非法 action「%s」；取值：%s\n" % (_args.action, "｜".join(ACTIONS)))
    sys.exit(2)
if _args.cases is not None and _args.action not in ("蒸馏", "迁移"):
    sys.stderr.write("✗ `--cases` 仅适用于 `蒸馏`（本次新增）与 `迁移`（基线固化）事件"
                     "（本次为「%s」）\n" % _args.action)
    sys.exit(2)

_today = time.strftime("%Y-%m-%d")
_block = ["## [%s] %s | %s" % (_today, _args.action, _args.object.strip()),
          "- 结果：%s" % _args.result.strip()]
if _args.cases is not None:
    # 正数带 `+`（历史形态，解析兼容）；0 与负数按原样（冲正/订正场景）
    _block.append("- 案数：%s" % ("+%d" % _args.cases if _args.cases > 0 else str(_args.cases)))
if _args.where.strip():
    _block.append("- 落点：%s" % _args.where.strip())
if _args.basis.strip():
    _block.append("- 依据：%s" % _args.basis.strip())
_text = "\n" + "\n".join(_block) + "\n"

os.makedirs(os.path.dirname(_log), exist_ok=True)

if not _args.allow_dup and os.path.exists(_log):
    # 去重判据（2026-09-27 更正）：同日 + 同「动作 | 对象」块内 + 同「结果」行 ⇒ 跳过。
    #   原判据「仅比末条」有两处失效：① 中间夹入其他事件后末条改变 ⇒ 拦不住；
    #   ② 与 check_methods_health.py 的自写通道不共享（该脚本已内联同源判据）。
    #   现判据不再依赖「末条」，与体检脚本同源 ⇒ 同日重复跑同一流程不再刷屏。
    _prev_all = io.open(_log, encoding="utf-8", errors="replace").read()
    _dup = False
    for _m in re.finditer(r"^##\s*\[(\d{4}-\d{2}-\d{2})\]\s*(.+?)\s*$", _prev_all, re.M):
        if _m.group(1) != _today:
            continue
        _seg = _prev_all[_m.end():_m.end() + 500]
        _nxt = re.search(r"^##\s*\[", _seg, re.M)
        if _nxt:
            _seg = _seg[:_nxt.start()]
        if _m.group(2).strip() == "%s | %s" % (_args.action, _args.object.strip()) \
                and ("- 结果：%s" % _args.result.strip()) in _seg:
            _dup = True
            break
    if _dup:
        print("≡ 同日同「动作+对象+结果」已存在，跳过（--allow-dup 可强制追加）")
        sys.exit(0)

if _args.dry_run:
    print("（dry-run）将追加到 %s：%s" % (os.path.relpath(_log, _ROOT), _text))
    sys.exit(0)

with io.open(_log, "a", encoding="utf-8", newline="\n") as f:
    f.write(_text)
print("✓ 已追加事件：[%s] %s | %s" % (_today, _args.action, _args.object.strip()))

#!/usr/bin/env python3
"""replay_gate_report.py — S7「回写硬门禁」四项指标的 **dry-run 报告**（不阻断）

背景（2026-09-19 用户裁定）
    「回写硬门禁」目前维持**软执行**（纪律 ＋ 人判），不打断无人值守蒸馏链路。
    为让后续裁定有据可依，把四项**机器可判**指标每轮以**报告**形式输出（**不阻断、不影响退出码**），
    连续积累后按判据复检：冲突升级裁定 ≥2 次 或 同型软违规 ≥3 次 ⇒ 该型升硬门禁。

四项指标
    ① 回写清单无本轮未销项（汇总＝明细＝进度行；`[x]` 计数一致）
    ② 索引已刷新（`check_index_locator.py` 行号定位抽查全命中）
    ③ 护栏 0 ERROR（`check_methods_health.py`，10 项）
    ④ 基线已落笔记（`methods/notes/` 最新笔记含「回写基线」行）

用法
    python replay_gate_report.py --methods-root <工作区根> [--json] [--quiet]

退出码
    恒 0（报告性质，**不阻断**）；仅当参数/路径错误返回 2／3
"""
import argparse
import glob
import io
import json
import os
import re
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))


def run_script(name, *extra):
    """调用同目录脚本，返回 (退出码, 输出文本)。脚本缺失返回 (3, 提示)。"""
    p = os.path.join(HERE, name)
    if not os.path.exists(p):
        return 3, "[MISS] %s 不存在" % name
    try:
        r = subprocess.run([sys.executable, p] + list(extra),
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except OSError as e:
        return 3, "[ERR] %s: %s" % (name, e)


def check_manifest(ws):
    """① 回写清单一致性（汇总＝明细＝进度行）。"""
    for cand in ("tasks/建议回写清单.md", "state/建议回写清单.md"):
        p = os.path.join(ws, cand)
        if os.path.exists(p):
            break
    else:
        return None, "清单文件未找到"
    t = io.open(p, encoding="utf-8", errors="replace").read()
    rows = [x for x in t.splitlines() if x.startswith("| [")]
    done = sum(1 for x in rows if x.startswith("| [x]"))
    m_sum = re.search(r"合计回写候选[：:]\s*(\d+)", t)
    m_prog = re.search(r"已回写\s*(\d+)\s*[/／]\s*待回写\s*(\d+)", t)
    ok = bool(m_sum and int(m_sum.group(1)) == len(rows))
    if m_prog:
        ok = ok and int(m_prog.group(1)) == done and int(m_prog.group(1)) + int(m_prog.group(2)) == len(rows)
    return ok, "明细 %d 行｜已销项 %d｜汇总 %s｜进度 %s" % (
        len(rows), done, m_sum.group(1) if m_sum else "—", m_prog.group(0) if m_prog else "—")


def check_locator(ws):
    """② 索引行号定位抽查（复用 check_index_locator.py）。"""
    code, out = run_script("check_index_locator.py", "--methods-root", ws)
    tail = [l for l in out.strip().splitlines() if l.strip()]
    return code == 0, (tail[-1] if tail else "(无输出)")


def check_health(ws):
    """③ 护栏（复用 check_methods_health.py）。"""
    code, out = run_script("check_methods_health.py", "--methods-root", ws)
    m = re.search(r"ERROR\s*(\d+)\s*项", out)
    n = int(m.group(1)) if m else -1
    return code == 0 and n == 0, "ERROR %s 项" % (n if n >= 0 else "?")


def check_baseline(ws):
    """④ 最新蒸馏笔记是否含「回写基线」行。"""
    notes = sorted(glob.glob(os.path.join(ws, "methods", "notes", "*蒸馏笔记*.md")),
                   key=os.path.getmtime, reverse=True)
    if not notes:
        return None, "无蒸馏笔记"
    latest = notes[0]
    t = io.open(latest, encoding="utf-8", errors="replace").read()
    m = re.search(r"回写基线[^\n]*", t)
    return bool(m), ("%s：%s" % (os.path.basename(latest), m.group(0)[:90]) if m else
                     "%s：未找到「回写基线」行" % os.path.basename(latest))


def main():
    ap = argparse.ArgumentParser(description="S7 回写硬门禁四项指标 dry-run 报告（不阻断）")
    ap.add_argument("--methods-root", required=True, help="工作区根（含 methods/ state/ tasks/）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    ws = os.path.abspath(a.methods_root)
    if not os.path.isdir(ws):
        sys.stderr.write("[USAGE] 工作区根不存在: %s\n" % ws)
        return 2

    checks = [
        ("① 回写清单无未销项", check_manifest(ws)),
        ("② 索引行号定位", check_locator(ws)),
        ("③ 护栏 0 ERROR", check_health(ws)),
        ("④ 基线已落笔记", check_baseline(ws)),
    ]
    passed = sum(1 for _, (ok, _) in checks if ok is True)
    total = sum(1 for _, (ok, _) in checks if ok is not None)

    if a.json:
        print(json.dumps({"tool": "replay_gate_report", "workspace": ws, "passed": passed,
                          "total": total, "blocking": False, "enforcement": "soft",
                          "items": [{"name": n, "ok": ok, "detail": d} for n, (ok, d) in checks]},
                         ensure_ascii=False))
        return 0

    if not a.quiet:
        print("=== S7 回写硬门禁 · dry-run 报告（**软执行、不阻断**）===")
        for n, (ok, d) in checks:
            mark = "✅" if ok is True else ("⏭" if ok is None else "⚠️")
            print("  %s %-18s %s" % (mark, n, d))
    print("--- 四项机器可判指标：%d/%d 通过 ｜ **不阻断本轮沉淀**（Enforcement=soft，2026-09-19 裁定）"
          % (passed, total))
    if passed < total:
        print("    复检判据：冲突升级裁定 ≥2 次 或 同型软违规 ≥3 次 ⇒ 该型升硬门禁；满 6 轮强制复检一次")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""check_runlog.py — 复核流程合规判定（读 `_run.json` 指纹）

回答一个问题：**这一轮到底按 skill 流程做了没有？**

用法
----
    python scripts/check_runlog.py --file <被复核文件>      # 自动定位 <文件>_复核/
    python scripts/check_runlog.py --dir  <运行目录>        # 指定目录（如已有 review_file 状态）

判据（逐条给结论，不笼统说"没问题"）
------------------------------------
  R1 有指纹文件            —— 没有 `_run.json` ⇒ 无法证明按流程走（FAIL）
  R2 版本一致              —— 记录里的 skill 版本 = 当前 SKILL.md 版本（不一致 ⇒ WARN：旧版跑的）
  R3 三项必需检查都跑过    —— check_content / check_cq / deliver_gate，且退出码 0
  R4 编排器跑完            —— 出现 review_file 的 finish，且 rc=0（未走编排器 ⇒ WARN）
  R5 声明单已落盘并可校验   —— 存在 `*_scope.md` 且 `check_scope_decl` 判 PASS
  R6 有报告产出            —— 目录内或 --report 指向的 xlsx 存在

退出码：0 合规／2 有 FAIL（WARN 不阻断，但逐条列出）
"""
import argparse
import glob
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runlog                     # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def dir_of(path):
    base = os.path.splitext(os.path.basename(path))[0]
    return os.path.join(os.path.dirname(os.path.abspath(path)), base + "_复核")


def scope_ok(d):
    """跑声明单校验器；返回 (有无, 是否 PASS, 文件)。"""
    files = sorted(glob.glob(os.path.join(d, "*_scope.md")))
    if not files:
        return False, False, None
    f = files[-1]
    r = subprocess.run([sys.executable, os.path.join(HERE, "check_scope_decl.py"), "--file", f],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return True, r.returncode == 0, f


def main():
    ap = argparse.ArgumentParser(description="复核流程合规判定（读运行指纹）")
    ap.add_argument("--file", default=None, help="被复核文件（自动定位 <文件>_复核/）")
    ap.add_argument("--dir", default=None, help="运行目录（含 _run.json）")
    ap.add_argument("--report", default=None, help="报告文件路径（可选，用于 R6）")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if not a.file and not a.dir:
        print("[ERROR] 需给 --file 或 --dir")
        return 2
    d = a.dir or dir_of(a.file)
    if not os.path.isdir(d):
        print(f"[FAIL] 运行目录不存在：{d}")
        print("  ⇒ 说明这一轮没有留下任何运行痕迹（未按 skill 流程执行）")
        return 2

    st = runlog.read(d)
    steps = st.get("steps", [])
    cur_ver = runlog.skill_version()
    rec_ver = st.get("skill_version")

    rows = []      # (判据, 状态, 说明)

    # R1
    has_log = bool(steps)
    rows.append(("R1 运行指纹", "PASS" if has_log else "FAIL",
                 f"{len(steps)} 步已记录" if has_log else "无 _run.json —— 无法证明按流程走"))

    # R2
    if not has_log:
        rows.append(("R2 版本一致", "SKIP", "无记录"))
    elif rec_ver == cur_ver:
        rows.append(("R2 版本一致", "PASS", f"skill {cur_ver}"))
    else:
        rows.append(("R2 版本一致", "WARN", f"记录 {rec_ver} ≠ 当前 {cur_ver}（旧版跑的，判据可能不同）"))

    # R3
    by_tool = {}
    for s in steps:
        by_tool.setdefault(s["tool"], []).append(s)
    for t in runlog.REQUIRED_STEPS:
        got = by_tool.get(t)
        if not got:
            rows.append((f"R3 {t}", "FAIL", "未执行"))
        else:
            rcs = [g["rc"] for g in got]
            rows.append((f"R3 {t}", "PASS" if 0 in rcs else "WARN",
                         f"{len(got)} 次，退出码 {rcs}" if 0 in rcs else f"退出码 {rcs}"))

    # R4
    fin = by_tool.get("review_file", [])
    fin = [s for s in fin if s.get("extra", {}).get("step") == "finish"]
    if not fin:
        rows.append(("R4 编排器", "WARN", "未走 review_file（自建管线时无内部状态可核）"))
    else:
        rows.append(("R4 编排器", "PASS" if fin[-1]["rc"] == 0 else "FAIL",
                     f"finish rc={fin[-1]['rc']}"))

    # R5
    has_scope, ok_scope, sf = scope_ok(d)
    if not has_scope:
        rows.append(("R5 声明单", "FAIL", "无 *_scope.md"))
    else:
        rows.append(("R5 声明单", "PASS" if ok_scope else "FAIL",
                     os.path.basename(sf) + ("（校验通过）" if ok_scope else "（校验未通过）")))

    # R6
    rep = a.report
    if not rep:
        cand = sorted(glob.glob(os.path.join(d, "*.xlsx")))
        rep = cand[-1] if cand else None
    rows.append(("R6 报告产出", "PASS" if rep and os.path.exists(rep) else "WARN",
                 rep or "未找到 xlsx（可能尚未生成）"))

    n_fail = sum(1 for _, s, _ in rows if s == "FAIL")
    n_warn = sum(1 for _, s, _ in rows if s == "WARN")
    verdict = "FAIL" if n_fail else ("WARN" if n_warn else "PASS")

    if a.json:
        print(json.dumps({"tool": "check_runlog", "dir": d, "verdict": verdict,
                          "fail": n_fail, "warn": n_warn,
                          "checks": [{"id": r[0], "status": r[1], "detail": r[2]} for r in rows]},
                         ensure_ascii=False))
    else:
        print(f"=== 流程合规：{os.path.basename(d)} ===")
        for cid, status, detail in rows:
            mark = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌", "SKIP": "—"}[status]
            print(f"  {mark} {cid:14s} {detail}")
        print(f"  => {verdict}（FAIL {n_fail} / WARN {n_warn}）")
        if verdict == "FAIL":
            print("  未按 skill 流程走完 —— 该轮结果不能当作「按判据复核」使用")
    return 2 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())

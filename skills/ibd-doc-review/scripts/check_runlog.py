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
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runlog                     # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def dir_of(path):
    base = os.path.splitext(os.path.basename(path))[0]
    return os.path.join(os.path.dirname(os.path.abspath(path)), base + "_复核")


def scope_ok(d):
    """跑声明单校验器；返回 (有无, 是否 PASS, 文件, 覆盖方式)。"""
    files = sorted(glob.glob(os.path.join(d, "*_scope.md")))
    if not files:
        return False, False, None, None
    f = files[-1]
    r = subprocess.run([sys.executable, os.path.join(HERE, "check_scope_decl.py"), "--file", f],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    txt = ""
    try:
        with open(f, encoding="utf-8") as fh:
            txt = fh.read()
    except OSError:
        pass
    m = re.search(r"覆盖方式[：:]\s*([^｜|\n]+)", txt)
    mode = (m.group(1).strip() if m else "")
    return True, r.returncode == 0, f, mode


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

    # R1b 链完整性（防"回头补一笔"）
    if has_log:
        import hashlib as _h, json as _j
        prev, broken = "", None
        for s_ in steps:
            want = _h.sha1((prev + _j.dumps({k: v for k, v in s_.items() if k != "h"},
                                            ensure_ascii=False, sort_keys=True)).encode("utf-8")).hexdigest()[:16]
            if s_.get("h") and s_["h"] != want:
                broken = s_
                break
            prev = s_.get("h", "")
        if broken:
            rows.append(("R1b 指纹链", "FAIL",
                         f"第 {broken.get('seq')} 步（{broken.get('tool')}）哈希不接上——"
                         f"该步疑似事后补写或改写，凭证不可信"))
        else:
            rows.append(("R1b 指纹链", "PASS", "逐条哈希相接"))

    # R1c 步骤时间 vs 产物时间（补记的典型特征：步骤晚于产物）
    if has_log and a.report:
        import time as _t
        try:
            art = os.path.getmtime(a.report)
            late = [s_ for s_ in steps
                    if _t.mktime(_t.strptime(s_["at"], "%Y-%m-%d %H:%M:%S")) > art + 120]
            if late:
                rows.append(("R1c 时序一致", "FAIL",
                             f"{len(late)} 步晚于报告生成时间（如 {late[0]['tool']} @ {late[0]['at']}）"
                             f"——疑似事后补记"))
            else:
                rows.append(("R1c 时序一致", "PASS", "全部步骤早于产物"))
        except (OSError, ValueError):
            pass

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
    # R3 按**实际交付形态**判：只出报告时没有勾稽输入、没有批注版，不能算"未执行"。
    # 但"做了却没留指纹"是另一回事——那是漏记，必须红。
    evidence = {
        "check_cq": os.path.exists(os.path.join(d, "checks.json")),
        "deliver_gate": bool(glob.glob(os.path.join(d, "*.docx"))) or
                        bool(glob.glob(os.path.join(d, "*批注*"))) or
                        bool(glob.glob(os.path.join(d, "*修订*"))),
    }
    for t in runlog.REQUIRED_STEPS:
        got = by_tool.get(t)
        if got:
            rcs = [g["rc"] for g in got]
            # rc=0 正常、rc=1 表示"查出了问题"——两者都是**合规执行**；rc>=2 才是用法/输入错误。
            # rc=0 正常、1 查出问题、3 缺输入未完成（不该算"做错"，但也不能算"做完"）
            bad_usage = [r for r in rcs if r >= 2 and r != 3]
            uncompleted = [r for r in rcs if r == 3]
            if bad_usage:
                rows.append((f"R3 {t}", "FAIL", f"{len(got)} 次，退出码 {rcs}（用法/输入错误）"))
            elif uncompleted and not any(r in (0, 1) for r in rcs):
                rows.append((f"R3 {t}", "SKIP", f"退出码 {rcs}：缺输入未完成（见 pending_inputs）"))
            else:
                rows.append((f"R3 {t}", "PASS", f"{len(got)} 次，退出码 {rcs}"))
        elif t == "check_content":
            # 格式/内容核对**永远必需**：没有它就不构成一次复核
            rows.append((f"R3 {t}", "FAIL", "未执行（内容核对是本流程的必需项）"))
        elif evidence.get(t):
            rows.append((f"R3 {t}", "FAIL", "有产物痕迹但无运行指纹——漏记或未走流程"))
        else:
            rows.append((f"R3 {t}", "SKIP", "本轮无该类输入/产物（无报表则不勾稽；未出批注版则不校验批注）"))

    # R3b L4 的专业判断是否真有人跑（本包看不到，只能提示）
    lv = None
    stp2 = os.path.join(d, ".review_state.json")
    if os.path.exists(stp2):
        try:
            with open(stp2, encoding="utf-8") as f:
                lv = json.load(f).get("level")
        except (OSError, ValueError):
            lv = None
    if lv == "L4":
        ext = [s_ for s_ in steps if any(k in str(s_.get("tool", "")).lower()
                                         for k in ("finance", "legal"))]
        rows.append(("R3b L4 专业判断", "PASS" if ext else "WARN",
                     f"外部痕迹 {len(ext)} 条" if ext else
                     "声明 L4，但无 ibd-finance-review／ibd-legal-review 运行痕迹——"
                     "L4 实际只到 L3（见 pending_inputs）"))

    # R4
    fin = by_tool.get("review_file", [])
    fin = [s for s in fin if s.get("extra", {}).get("step") == "finish"]
    n_commit = len([s_ for s_ in by_tool.get("review_file", [])
                    if s_.get("extra", {}).get("step") == "commit"])
    n_batch = None
    stp = os.path.join(d, ".review_state.json")
    if os.path.exists(stp):
        try:
            with open(stp, encoding="utf-8") as f:
                n_batch = len(json.load(f).get("batches") or [])
        except (OSError, ValueError):
            n_batch = None
    if not fin:
        # 《复核章程》§六：未走编排器 = 覆盖不可证 = 不得交付。
        rows.append(("R4 编排器", "FAIL",
                     "无 finish 步——未走 review_file 状态机，逐批覆盖不可证（自建管线不算完成复核）"))
    elif n_batch and n_commit < n_batch:
        rows.append(("R4 编排器", "FAIL", f"commit {n_commit}/{n_batch} 批——有批未登记，覆盖不全"))
    else:
        rows.append(("R4 编排器", "PASS" if fin[-1]["rc"] == 0 else "FAIL",
                     f"finish rc={fin[-1]['rc']}｜commit {n_commit}"
                     + (f"/{n_batch} 批" if n_batch else "")))

    # R5
    has_scope, ok_scope, sf, mode = scope_ok(d)
    if not has_scope:
        rows.append(("R5 声明单", "FAIL", "无 *_scope.md（未声明覆盖范围）"))
    elif not ok_scope:
        rows.append(("R5 声明单", "FAIL", os.path.basename(sf) + "（校验未通过）"))
    elif "全文" not in (mode or ""):
        # 《复核章程》§四：复核＝全量。非全文即缩范围，除非声明里写明用户指示（由 scope 校验器把关）
        rows.append(("R5 声明单", "FAIL",
                     f"覆盖方式＝{mode or '未写'}，非「全文逐段」——复核必须全量（见 fuhe-charter.md §四）"))
    else:
        rows.append(("R5 声明单", "PASS", os.path.basename(sf) + "（全文逐段，校验通过）"))

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

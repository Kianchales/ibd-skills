#!/usr/bin/env python3
"""
test_check_runlog.py — 运行指纹与流程合规判定

为什么必须测：这份东西的唯一价值是"能判出没按流程走"。若它对缺步骤、缺声明单也判 PASS，
就等于给人一个假的合规背书。所以每条判据都要有**反例**（该红时必须红）。
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, "..", ".."))
SCRIPTS = os.path.join(PKG, "scripts")
CHECK = os.path.join(SCRIPTS, "check_runlog.py")


def write_log(d, steps, version=None):
    sys.path.insert(0, SCRIPTS)
    import runlog
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "_run.json"), "w", encoding="utf-8") as f:
        json.dump({"skill_version": version or runlog.skill_version(), "steps": steps}, f,
                  ensure_ascii=False)
    return d


def step(tool, rc=0, **extra):
    return {"tool": tool, "rc": rc, "argv": [], "at": "2026-11-23 11:00:00", "extra": extra}


def run(args):
    p = subprocess.run([sys.executable, CHECK] + args,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


GOOD_SCOPE = ("【本轮检查项声明】对象：x.docx ｜ 深度：L2 ｜ 覆盖方式：全文逐段 ｜ "
              "分母：总 900 段（正文 100／表 10）\n")


class TestRunlog(unittest.TestCase):

    def setUp(self):
        self._d = tempfile.TemporaryDirectory()
        self.d = self._d.name
        self.addCleanup(self._d.cleanup)

    def test_missing_dir_is_fail(self):
        rc, out = run(["--dir", os.path.join(self.d, "nope")])
        self.assertEqual(rc, 2)
        self.assertIn("没有留下任何运行痕迹", out)

    def test_missing_content_check_fails(self):
        """内容核对永远必需：只跑了编排器与合并 → FAIL。"""
        write_log(self.d, [step("review_file", 0, step="finish")])
        rc, out = run(["--dir", self.d])
        self.assertEqual(rc, 2)
        self.assertIn("R3 check_content", out)
        self.assertIn("必需项", out)

    def test_optional_steps_skip_not_fail(self):
        """无报表 → 不勾稽；未出批注版 → 不校验批注。属 SKIP，不应判 FAIL。"""
        write_log(self.d, [step("check_content"), step("review_file", 0, step="finish")])
        with open(os.path.join(self.d, "x_scope.md"), "w", encoding="utf-8") as f:
            f.write(GOOD_SCOPE)
        rc, out = run(["--dir", self.d])
        self.assertEqual(rc, 0, out)
        self.assertIn("—", out, "SKIP 应显示为 —")

    def test_evidence_without_fingerprint_fails(self):
        """有 checks.json 却没 check_cq 指纹 → 漏记，必须红（不许静默放过）。"""
        write_log(self.d, [step("check_content"), step("review_file", 0, step="finish")])
        with open(os.path.join(self.d, "x_scope.md"), "w", encoding="utf-8") as f:
            f.write(GOOD_SCOPE)
        with open(os.path.join(self.d, "checks.json"), "w", encoding="utf-8") as f:
            f.write("{}")
        rc, out = run(["--dir", self.d])
        self.assertEqual(rc, 2)
        self.assertIn("无运行指纹", out)

    def test_all_green_pass(self):
        write_log(self.d, [step("check_content"), step("check_cq"), step("deliver_gate"),
                           step("review_file", 0, step="finish")])
        with open(os.path.join(self.d, "x_scope.md"), "w", encoding="utf-8") as f:
            f.write(GOOD_SCOPE)
        with open(os.path.join(self.d, "r.xlsx"), "wb") as f:
            f.write(b"fake")
        rc, out = run(["--dir", self.d])
        self.assertEqual(rc, 0, out)
        self.assertIn("✅", out)

    def test_no_finish_fails(self):
        """《复核章程》§四-7：只跑 prepare/单点检查就宣称完成 → R4 FAIL，不是 WARN。"""
        write_log(self.d, [step("check_content"), step("check_cq"), step("deliver_gate")])
        with open(os.path.join(self.d, "x_scope.md"), "w", encoding="utf-8") as f:
            f.write(GOOD_SCOPE)
        rc, out = run(["--dir", self.d])
        self.assertEqual(rc, 2, out)
        self.assertIn("无 finish 步", out)

    def test_backfilled_step_fails(self):
        """步骤时间晚于产物 → 疑似补记，判 FAIL。"""
        import time
        write_log(self.d, [step("check_content"), step("review_file", 0, step="finish")])
        rep = os.path.join(self.d, "r.xlsx")
        with open(rep, "wb") as f:
            f.write(b"x")
        old = time.mktime(time.strptime("2020-01-01 00:00:00", "%Y-%m-%d %H:%M:%S"))
        os.utime(rep, (old, old))          # 产物时间调到过去
        with open(os.path.join(self.d, "x_scope.md"), "w", encoding="utf-8") as f:
            f.write(GOOD_SCOPE)
        rc, out = run(["--dir", self.d, "--report", rep])
        self.assertEqual(rc, 2, out)
        self.assertIn("疑似事后补记", out)

    def test_l4_without_external_traces_warns(self):
        """L4 的专业判断靠外部两包；本包看不到就必须点出来，不能默认它跑了。"""
        write_log(self.d, [step("check_content"), step("check_cq"), step("deliver_gate"),
                           step("review_file", 0, step="finish")])
        with open(os.path.join(self.d, "x_scope.md"), "w", encoding="utf-8") as f:
            f.write(GOOD_SCOPE)
        with open(os.path.join(self.d, ".review_state.json"), "w", encoding="utf-8") as f:
            json.dump({"v": 2, "level": "L4", "batches": []}, f)
        rc, out = run(["--dir", self.d])
        self.assertIn("R3b L4 专业判断", out)
        self.assertIn("实际只到 L3", out)

    def test_version_mismatch_warns(self):
        write_log(self.d, [step("check_content"), step("check_cq"), step("deliver_gate"),
                           step("review_file", 0, step="finish")], version="0.0.1")
        rc, out = run(["--dir", self.d])
        self.assertIn("旧版跑", out)

    def test_scope_missing_fails(self):
        write_log(self.d, [step("check_content"), step("check_cq"), step("deliver_gate"),
                           step("review_file", 0, step="finish")])
        rc, out = run(["--dir", self.d])
        self.assertEqual(rc, 2)
        self.assertIn("无 *_scope.md", out)

    def test_non_full_coverage_fails(self):
        """《复核章程》：复核＝全量。声明单合法但覆盖方式非全文 → R5 FAIL。"""
        write_log(self.d, [step("check_content"), step("review_file", 0, step="finish")])
        with open(os.path.join(self.d, "x_scope.md"), "w", encoding="utf-8") as f:
            f.write("【本轮检查项声明】对象：x.docx ｜ 深度：L2 ｜ 覆盖方式：圈定范围 ｜ "
                    "分母：总 900 段（正文 100／表 10）\n· 指示来源：用户指定只看第四节\n")
        rc, out = run(["--dir", self.d])
        self.assertEqual(rc, 2, out)
        self.assertIn("非「全文逐段」", out)

    def test_bad_scope_fails(self):
        write_log(self.d, [step("check_content"), step("check_cq"), step("deliver_gate"),
                           step("review_file", 0, step="finish")])
        with open(os.path.join(self.d, "x_scope.md"), "w", encoding="utf-8") as f:
            f.write("【本轮检查项声明】对象：x.docx ｜ 覆盖方式：圈定范围\n")   # 缺栏＋无用户指示
        rc, out = run(["--dir", self.d])
        self.assertEqual(rc, 2)
        self.assertIn("校验未通过", out)

    def test_autolog_writes_fingerprint(self):
        """真实跑一次 check_cq，指纹应带上工具名/退出码/版本。"""
        sys.path.insert(0, SCRIPTS)
        import runlog
        before = len(runlog.read(self.d)["steps"])
        runlog.log("check_cq", ["--xlsx", "x.xlsx"], 1, out_dir=self.d)
        st = runlog.read(self.d)
        self.assertEqual(len(st["steps"]), before + 1)
        self.assertEqual(st["steps"][-1]["tool"], "check_cq")
        self.assertEqual(st["steps"][-1]["rc"], 1)
        self.assertTrue(st["skill_version"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

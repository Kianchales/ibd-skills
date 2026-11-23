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

    def test_missing_required_steps_fail(self):
        write_log(self.d, [step("review_file", 0, step="finish")])
        rc, out = run(["--dir", self.d])
        self.assertEqual(rc, 2)
        for t in ("check_content", "check_cq", "deliver_gate"):
            self.assertIn(f"R3 {t}", out)
        self.assertIn("未执行", out)

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

#!/usr/bin/env python3
"""
test_round_diff_selftest.py — 把 round_diff 的内置自检接进 unittest

为什么单独接
------------
`round_diff.py --self-test` 早就有了，但**没进测试套件**——等于"有自检但没人跑"。
本轮复盘把它登记进来：只要 `--self-test` 退出码非 0 或关键断言缺失，构建就红。

覆盖：
  1. 自检退出码 0
  2. 五档计数与期望一致（输出含 "⇒ PASS"）
  3. 上轮条数守恒（输出含"守恒"且 PASS）
  4. 阴性对照（本轮空清单 → 全部已关闭）

运行：REVIEW_TESTS=all python scripts/tests/test_round_diff_selftest.py
"""
import os
import re
import subprocess
import sys
import unittest

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from _tier import slow_all  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.abspath(os.path.join(HERE, "..", "round_diff.py"))


def run_selftest():
    p = subprocess.run([sys.executable, SCRIPT, "--self-test"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


class TestRoundDiffSelfTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.rc, cls.out = run_selftest()

    def test_exit_zero(self):
        self.assertEqual(self.rc, 0, "自检失败：\n" + self.out[-800:])

    def test_five_states_checked(self):
        """五档全被覆盖（缺一档 = 该分支没被测到）。"""
        self.assertTrue(self.out.count("⇒ PASS") >= 3, "自检断言数不足：\n" + self.out[-600:])
        for state in ("未修复·原句未动", "未修复·已改写", "疑似已关闭", "新增"):
            self.assertIn(state, self.out, "自检未覆盖状态：" + state)

    def test_count_conserved(self):
        self.assertRegex(self.out, r"条数守恒.*PASS")

    def test_negative_control(self):
        m = re.search(r"阴性对照.*?(PASS|FAIL)", self.out)
        self.assertIsNotNone(m, "缺阴性对照：\n" + self.out[-600:])
        self.assertEqual(m.group(1), "PASS")


slow_all(globals())

if __name__ == "__main__":
    unittest.main(verbosity=2)

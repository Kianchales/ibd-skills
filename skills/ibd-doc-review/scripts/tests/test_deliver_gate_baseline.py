#!/usr/bin/env python3
"""
test_deliver_gate_baseline.py — 基线差分（`--baseline`）自测

背景：复核是只读的——源件的半角标点、裸段、空段、禁词都在，且用户明确「不改源件」。
若门禁把这些当成本次 FAIL，批注版永远交不出去，门禁形同废纸。
判据：交付件 FAIL 且**基线同项亦 FAIL** ⇒ 标〔源件遗留〕不计入结论；
     交付件 FAIL 但基线 PASS ⇒ **是本次引入的，照旧 FAIL**（这条最关键，防放过真问题）。

覆盖：
  1. FAIL ＋ 基线 FAIL → PASS 且名称带〔源件遗留〕
  2. **FAIL ＋ 基线 PASS → 仍 FAIL**（本次引入，不得放过）
  3. PASS → 原样；SKIP(None) → 原样
  4. 混合场景：三真一假，只有"本次引入"那项计入 FAIL
  5. 遗留项保留原明细（可溯源到源件问题），不吞掉

运行：python scripts/tests/test_deliver_gate_baseline.py
"""
import importlib.util
import os
import sys
import unittest

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SKILL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
GATE = os.path.join(SKILL_DIR, "scripts", "deliver_gate.py")

_spec = importlib.util.spec_from_file_location("dg_base", GATE)
dg = importlib.util.module_from_spec(_spec)
sys.modules["dg_base"] = dg
_spec.loader.exec_module(dg)


def R(name, ok, fails=()):
    return (name, ok, "明细", list(fails))


class TestBaseline(unittest.TestCase):

    def test_legacy_marked_pass(self):
        out, legacy = dg._apply_baseline([R("标点规范", False, ["半角括号 6"])], {"标点规范"})
        name, ok, detail, fails = out[0]
        self.assertTrue(ok, "源件遗留项应不计入 FAIL")
        self.assertIn("〔源件遗留〕", name)
        self.assertIn("基线同项亦 FAIL", detail)
        self.assertEqual(legacy, ["标点规范"])
        self.assertIn("半角括号 6", fails, "原明细须保留，可溯源到源件问题")

    def test_introduced_stays_fail(self):
        """本次引入的问题绝不能被基线放过。"""
        out, legacy = dg._apply_baseline([R("指纹(去标点)", False, ["原文被改"])], {"标点规范"})
        name, ok, _d, _f = out[0]
        self.assertFalse(ok, "基线 PASS 的项 FAIL 属本次引入，必须仍判 FAIL")
        self.assertNotIn("〔源件遗留〕", name)
        self.assertEqual(legacy, [])

    def test_pass_and_skip_untouched(self):
        out, legacy = dg._apply_baseline([R("占位符", True), R("物理扫描", None)], {"占位符"})
        self.assertEqual([o[0] for o in out], ["占位符", "物理扫描"])
        self.assertEqual([o[1] for o in out], [True, None])
        self.assertEqual(legacy, [])

    def test_mixed(self):
        results = [R("标点规范", False), R("样式规范", False),
                   R("指纹(去标点)", False), R("占位符", True)]
        out, legacy = dg._apply_baseline(results, {"标点规范", "样式规范"})
        fails = [n for n, ok, _d, _f in out if ok is False]
        self.assertEqual(fails, ["指纹(去标点)"], "只有本次引入项计入 FAIL")
        self.assertEqual(set(legacy), {"样式规范", "标点规范"})


class TestPhysicalDiff(unittest.TestCase):
    """物理扫描的基线差分：架构错误可归遗留，**缺陷数增量必须算本次引入**。"""

    def test_arch_only_legacy(self):
        cur = ("物理扫描", False, "架构校验未通过；渲染缺陷 188 条", ["架构校验未通过（officecli exit≠0）"])
        base = ("物理扫描", False, "架构校验未通过；渲染缺陷 188 条", ["架构校验未通过"])
        name, ok, detail, _f = dg._diff_physical(cur, base)
        self.assertTrue(ok)
        self.assertIn("〔源件遗留〕", name)

    def test_increment_is_introduced(self):
        """交付件缺陷数比源件多 → 本次引入，必须仍 FAIL（防把注入缺陷当遗留放过）。"""
        cur = ("物理扫描", False, "渲染缺陷 191 条", ["缺陷 191 > 0"])
        base = ("物理扫描", False, "渲染缺陷 188 条", [])
        name, ok, detail, fails = dg._diff_physical(cur, base)
        self.assertFalse(ok, "有增量就必须 FAIL")
        self.assertIn("本次引入 3 处", detail)
        self.assertTrue(any("本次注入引入" in f for f in fails))

    def test_pass_untouched(self):
        cur = ("物理扫描", True, "架构合法；缺陷 0", [])
        self.assertEqual(dg._diff_physical(cur, ("物理扫描", False, "x", [])), cur)


if __name__ == "__main__":
    unittest.main(verbosity=2)

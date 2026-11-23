#!/usr/bin/env python3
"""
test_check_scope_decl.py — 声明单校验（抽核须有正当理由）

为什么这条要测：判据把"量大／时间紧"明确排除在正当理由之外（复核慢点就慢点），
若不测，改一行白名单就可能把闸门放宽而无人知晓。

保持快档：断言直接调 `check()`，只留 1 条 CLI 冒烟。
"""
import importlib.util
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
SCRIPT = os.path.join(PKG, "scripts", "check_scope_decl.py")
spec = importlib.util.spec_from_file_location("csd", SCRIPT)
csd = importlib.util.module_from_spec(spec)
sys.modules["csd"] = csd
spec.loader.exec_module(csd)

HDR = ("【本轮检查项声明】对象：1-1 招股说明书.docx ｜ 深度：L2 ｜ "
       "覆盖方式：{mode} ｜ 分母：总 25041 段（正文 909／表 303）")


class TestDeclCheck(unittest.TestCase):

    def test_full_coverage_passes(self):
        errs, warns, _ = csd.check(HDR.format(mode="全文逐段"))
        self.assertEqual((errs, warns), ([], []))

    def test_missing_field_fails(self):
        errs, _w, _ = csd.check("【本轮检查项声明】对象：x.docx ｜ 深度：L2 ｜ 覆盖方式：全文逐段")
        self.assertTrue(any("分母" in e for e in errs), errs)

    def test_sampling_without_reason_fails(self):
        errs, _w, _ = csd.check(HDR.format(mode="抽核"))
        self.assertTrue(any("抽核" in e for e in errs), errs)

    def test_sampling_bad_reason_warns(self):
        """「量大／时间紧」不是正当理由——只提示，不阻断；--strict 才算不通过。"""
        text = HDR.format(mode="抽核") + "\n· 抽核：抽第四节，因为文件太大时间紧\n"
        errs, warns, info = csd.check(text)
        self.assertEqual(errs, [])
        self.assertTrue(any("不是正当理由" in w for w in warns), warns)
        self.assertIn("时间紧", info["理由"])

    def test_sampling_good_reason_passes(self):
        text = HDR.format(mode="抽核") + "\n· 抽核：抽第四节，因为该节缺件、技术上不可读\n"
        errs, warns, _ = csd.check(text)
        self.assertEqual((errs, warns), ([], []))

    def test_sampling_needs_location(self):
        text = HDR.format(mode="抽核") + "\n· 抽核：抽了一些，因为缺件\n"
        errs, _w, _ = csd.check(text)
        self.assertTrue(any("抽了哪些" in e for e in errs), errs)

    def test_full_but_samples_is_worse(self):
        """写了全文却实际抽核＝静默缩范围，判 ERROR。"""
        text = HDR.format(mode="全文逐段") + "\n· 抽核：抽第三节，因为缺件\n"
        errs, _w, _ = csd.check(text)
        self.assertTrue(any("静默缩范围" in e for e in errs), errs)


class TestCliSmoke(unittest.TestCase):

    def test_cli_json_and_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            ok = os.path.join(d, "ok_scope.md")
            with open(ok, "w", encoding="utf-8") as f:
                f.write(HDR.format(mode="全文逐段") + "\n")
            r = subprocess.run([sys.executable, SCRIPT, "--file", ok, "--json"],
                               capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(json.loads(r.stdout)["verdict"], "PASS")

            bad = os.path.join(d, "bad_scope.md")
            with open(bad, "w", encoding="utf-8") as f:
                f.write(HDR.format(mode="抽核") + "\n· 抽核：抽第四节，因为时间紧\n")
            r2 = subprocess.run([sys.executable, SCRIPT, "--file", bad, "--strict"],
                                capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(r2.returncode, 1, r2.stdout + r2.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)

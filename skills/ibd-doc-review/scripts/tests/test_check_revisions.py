#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_check_revisions.py — check_revisions.py 自测（最小测试集）

覆盖：
  revise 模式：
    1. 合规修订稿（1 对 ins/del、author 齐全、settings 已开修订）→ PASS
    2. ins/del 数量不成对 → FAIL
    3. ins/del id 不成对 → FAIL
    4. 修订缺 author → FAIL
    5. delText 为空 → FAIL
    6. settings 未开 trackRevisions / 缺 revisionView → FAIL
    7. ins 文本 clean 化后缺失（未落定）→ FAIL
    8. --expect 与实测不一致 → FAIL
  clean 模式：
    9. 无修订标记 → PASS
   10. 残留 ins/del → FAIL
   11. --report 写出校验报告 md
运行：python scripts/tests/test_check_revisions.py
"""
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import unittest

SKILL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPT = os.path.join(SKILL_DIR, "scripts", "check_revisions.py")
GATE_TEST = os.path.join(os.path.dirname(__file__), "test_deliver_gate.py")

_spec = importlib.util.spec_from_file_location("t_gate", GATE_TEST)
tg = importlib.util.module_from_spec(_spec)
sys.modules["t_gate"] = tg
_spec.loader.exec_module(tg)

_para, _pkt = tg._para, tg._pkt
ins_run, del_run = tg.ins_run, tg.del_run
TEXT_TITLE, TEXT_SUB = tg.TEXT_TITLE, tg.TEXT_SUB
SETTINGS_TRACK, SETTINGS_PLAIN = tg.SETTINGS_TRACK, tg.SETTINGS_PLAIN


def make(path, body_xml, settings=SETTINGS_TRACK):
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
           f'<w:document {tg.WNS}><w:body>{body_xml}<w:sectPr/></w:body></w:document>')
    _pkt(path, doc, settings=settings)


def run(args_list):
    p = subprocess.run([sys.executable, SCRIPT] + args_list,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def pair_body(old="旧金额 100 万元", new="新金额 200 万元", rid=0, author="复核人", tail=" 其余文字。"):
    return (_para("000", TEXT_TITLE) + _para("0011", TEXT_SUB)
            + f'<w:p><w:pPr><w:pStyle w:val="001"/></w:pPr>'
              f'{del_run(old, rid, author)}{ins_run(new, rid, author)}'
              f'<w:r><w:t xml:space="preserve">{tail}</w:t></w:r></w:p>')


class TestCheckRevisions(unittest.TestCase):

    def setUp(self):
        self._d = tempfile.TemporaryDirectory()
        self.d = self._d.name
        self.addCleanup(self._d.cleanup)

    def p(self, n):
        return os.path.join(self.d, n)

    def test_01_compliant_revise_passes(self):
        f = self.p("ok.docx")
        make(f, pair_body())
        rc, out = run(["--input", f, "--mode", "revise"])
        self.assertEqual(rc, 0, out)
        self.assertIn("PASS ✅", out)

    def test_02_unbalanced_fails(self):
        f = self.p("unbal.docx")
        make(f, _para("000", TEXT_TITLE) + _para("0011", TEXT_SUB)
             + '<w:p><w:pPr><w:pStyle w:val="001"/></w:pPr>'
             + ins_run("新文本", 0) + "</w:p>")
        rc, out = run(["--input", f, "--mode", "revise"])
        self.assertEqual(rc, 1, out)
        self.assertIn("未成对", out)

    def test_03_id_not_paired_fails(self):
        f = self.p("idmis.docx")
        make(f, _para("000", TEXT_TITLE) + _para("0011", TEXT_SUB)
             + '<w:p><w:pPr><w:pStyle w:val="001"/></w:pPr>'
             + ins_run("新文本", 0) + del_run("旧文本", 1) + "</w:p>")
        rc, out = run(["--input", f, "--mode", "revise"])
        self.assertEqual(rc, 1, out)
        self.assertIn("不成对", out)

    def test_04_missing_author_fails(self):
        f = self.p("auth.docx")
        make(f, pair_body(author=""))
        rc, out = run(["--input", f, "--mode", "revise"])
        self.assertEqual(rc, 1, out)
        self.assertIn("缺 author", out)

    def test_05_empty_deltext_fails(self):
        f = self.p("empty.docx")
        make(f, _para("000", TEXT_TITLE) + _para("0011", TEXT_SUB)
             + '<w:p><w:pPr><w:pStyle w:val="001"/></w:pPr>'
             + '<w:del w:id="0" w:author="复核人"><w:r>'
               '<w:delText xml:space="preserve"> </w:delText></w:r></w:del>'
             + ins_run("新文本", 0) + "</w:p>")
        rc, out = run(["--input", f, "--mode", "revise"])
        self.assertEqual(rc, 1, out)
        self.assertIn("修订文本为空", out)

    def test_06_settings_not_tracking_fails(self):
        f = self.p("sett.docx")
        make(f, pair_body(), settings=SETTINGS_PLAIN)
        rc, out = run(["--input", f, "--mode", "revise"])
        self.assertEqual(rc, 1, out)
        self.assertIn("trackRevisions", out)
        self.assertIn("revisionView", out)

    def test_07_not_settled_fails(self):
        """ins 文本在 clean 化后仍缺失 —— 构造：ins 内容被外层 del 吞掉"""
        f = self.p("uns.docx")
        body = (_para("000", TEXT_TITLE) + _para("0011", TEXT_SUB)
                + '<w:p><w:pPr><w:pStyle w:val="001"/></w:pPr>'
                + f'<w:del w:id="0" w:author="复核人"><w:r><w:delText xml:space="preserve">旧</w:delText></w:r>'
                  f'<w:ins w:id="0" w:author="复核人"><w:r><w:t xml:space="preserve">新</w:t></w:r></w:ins>'
                  f'</w:del>'
                + "</w:p>")
        make(f, body)
        rc, out = run(["--input", f, "--mode", "revise"])
        self.assertEqual(rc, 1, out)
        self.assertIn("clean 化后缺失", out)

    def test_08_expect_mismatch_fails(self):
        f = self.p("cnt.docx")
        make(f, pair_body())
        rc, out = run(["--input", f, "--mode", "revise", "--expect", "5"])
        self.assertEqual(rc, 1, out)
        self.assertIn("!= 期望 5", out)

    def test_09_clean_mode_passes(self):
        f = self.p("clean.docx")
        make(f, _para("000", TEXT_TITLE) + _para("0011", TEXT_SUB) + _para("001", "已落定正文。"))
        rc, out = run(["--input", f, "--mode", "clean"])
        self.assertEqual(rc, 0, out)
        self.assertIn("无修订标记残留", out)

    def test_10_clean_mode_residue_fails(self):
        f = self.p("resid.docx")
        make(f, pair_body())
        rc, out = run(["--input", f, "--mode", "clean"])
        self.assertEqual(rc, 1, out)
        self.assertIn("残留修订标记", out)

    def test_11_report_written(self):
        f = self.p("rep.docx")
        make(f, pair_body())
        rc, out = run(["--input", f, "--mode", "revise", "--report"])
        self.assertEqual(rc, 0, out)
        rep = os.path.splitext(f)[0] + "_修订校验报告.md"
        self.assertTrue(os.path.exists(rep), out)
        with io.open(rep, encoding="utf-8") as fh:
            body = fh.read()
        self.assertIn("PASS", body)


if __name__ == "__main__":
    unittest.main(verbosity=2)

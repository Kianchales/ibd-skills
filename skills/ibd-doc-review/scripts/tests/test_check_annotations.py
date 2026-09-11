#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_check_annotations.py — check_annotations.py 自测（最小测试集）

覆盖：
  1. 合规批注件（1 条）→ PASS，退出码 0
  2. 缺 word/comments.xml → FAIL
  3. Content_Types 缺 comments Override → FAIL
  4. commentRangeStart/End/Reference 对数不齐 → FAIL
  5. 每条批注段落数 ≠ 4 → FAIL
  6. 行1 编号格式不合规 → FAIL
  7. 编号全局重复 → FAIL
  8. 行3/行4 未以「问题描述：」「建议：」开头 → FAIL
  9. styles.xml 缺 CommentText → FAIL
 10. --report 写出校验报告 md
运行：python scripts/tests/test_check_annotations.py
"""
import io
import os
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile

SKILL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPT = os.path.join(SKILL_DIR, "scripts", "check_annotations.py")
T = os.path.join(os.path.dirname(__file__), "test_deliver_gate.py")

# 复用 deliver_gate 测试的文档构造器（同一套最小 docx 骨架，避免两份漂移）
import importlib.util
_spec = importlib.util.spec_from_file_location("t_gate", T)
tg = importlib.util.module_from_spec(_spec)
sys.modules["t_gate"] = tg
_spec.loader.exec_module(tg)

WNS, _pkt = tg.WNS, tg._pkt
comment_xml, comments_doc = tg.comment_xml, tg.comments_doc
doc_with_anchors, STYLES_XML = tg.doc_with_anchors, tg.STYLES_XML
NS_CT = tg.NS_CT


def make(path, entries, n_anchors=None, with_comments=True, ct_ok=True, styles=STYLES_XML):
    n = len(entries) if n_anchors is None else n_anchors
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
           f'<w:document {WNS}><w:body>{doc_with_anchors(n)}<w:sectPr/></w:body></w:document>')
    cmts = comments_doc(entries) if with_comments else None
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        ct_extra = ('<Override PartName="/word/comments.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"/>'
                    if (with_comments and ct_ok) else "")
        rel_extra = ('<Relationship Id="rId9" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments" Target="comments.xml"/>'
                     if with_comments else "")
        z.writestr("[Content_Types].xml", tg.CT_TMPL.format(ct=NS_CT, extra=ct_extra))
        z.writestr("_rels/.rels", tg.RELS_TMPL.format(rel=tg.NS_REL, extra=""))
        z.writestr("word/_rels/document.xml.rels", tg.DOC_RELS_TMPL.format(rel=tg.NS_REL, extra=rel_extra))
        z.writestr("word/document.xml", doc)
        z.writestr("word/settings.xml", tg.SETTINGS_PLAIN)
        z.writestr("word/styles.xml", styles)
        if with_comments:
            z.writestr("word/comments.xml", cmts)


def run(args_list):
    p = subprocess.run([sys.executable, SCRIPT] + args_list,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


GOOD = lambda cid=0, label="【J-01｜数据｜高】": comment_xml(cid, label, "金额不一致", "描述内容。", "建议内容。")


class TestCheckAnnotations(unittest.TestCase):

    def setUp(self):
        self._d = tempfile.TemporaryDirectory()
        self.d = self._d.name
        self.addCleanup(self._d.cleanup)

    def p(self, n):
        return os.path.join(self.d, n)

    def test_01_compliant_passes(self):
        f = self.p("ok.docx")
        make(f, [GOOD()])
        rc, out = run(["--input", f])
        self.assertEqual(rc, 0, out)
        self.assertIn("PASS ✅", out)

    def test_02_missing_comments_part_fails(self):
        f = self.p("no.docx")
        make(f, [GOOD()], with_comments=False)
        rc, out = run(["--input", f])
        self.assertEqual(rc, 1, out)
        self.assertIn("缺少 word/comments.xml", out)

    def test_03_missing_ct_override_fails(self):
        f = self.p("noct.docx")
        make(f, [GOOD()], ct_ok=False)
        rc, out = run(["--input", f])
        self.assertEqual(rc, 1, out)
        self.assertIn("缺少 comments Override", out)

    def test_04_anchor_mismatch_fails(self):
        f = self.p("mis.docx")
        make(f, [GOOD(), GOOD(1, "【L-01｜表述｜中】")], n_anchors=1)
        rc, out = run(["--input", f])
        self.assertEqual(rc, 1, out)
        self.assertIn("锚定对数不齐", out)

    def test_05_wrong_para_count_fails(self):
        bad = GOOD().replace('<w:p><w:r><w:rPr><w:b/></w:rPr>'
                             '<w:t xml:space="preserve">建议：</w:t></w:r>'
                             '<w:r><w:rPr><w:b w:val="0"/></w:rPr>'
                             '<w:t xml:space="preserve">建议内容。</w:t></w:r></w:p>', "")
        f = self.p("cnt.docx")
        make(f, [bad])
        rc, out = run(["--input", f])
        self.assertEqual(rc, 1, out)
        self.assertIn("段落数", out)

    def test_06_bad_label_format_fails(self):
        f = self.p("lbl.docx")
        make(f, [GOOD(label="J-1 无框")])
        rc, out = run(["--input", f])
        self.assertEqual(rc, 1, out)
        self.assertIn("格式", out)

    def test_07_duplicate_number_fails(self):
        f = self.p("dup.docx")
        make(f, [GOOD(0, "【J-01｜数据｜高】"), GOOD(1, "【J-01｜表述｜低】")])
        rc, out = run(["--input", f])
        self.assertEqual(rc, 1, out)
        self.assertIn("编号重复", out)

    def test_08_missing_lead_word_fails(self):
        bad = GOOD().replace("问题描述：", "问题情况：")
        f = self.p("lead.docx")
        make(f, [bad])
        rc, out = run(["--input", f])
        self.assertEqual(rc, 1, out)
        self.assertIn("问题描述：", out)

    def test_09_missing_comment_text_style_fails(self):
        f = self.p("sty.docx")
        make(f, [GOOD()], styles=STYLES_XML.replace('w:styleId="CommentText"', 'w:styleId="XCommentText"'))
        rc, out = run(["--input", f])
        self.assertEqual(rc, 1, out)
        self.assertIn("CommentText", out)

    def test_10_report_written(self):
        f = self.p("rep.docx")
        make(f, [GOOD()])
        rc, out = run(["--input", f, "--report"])
        self.assertEqual(rc, 0, out)
        rep = os.path.splitext(f)[0] + "_批注校验报告.md"
        self.assertTrue(os.path.exists(rep), out)
        body = io.open(rep, encoding="utf-8").read()
        self.assertIn("comments 条数", body)


if __name__ == "__main__":
    unittest.main(verbosity=2)

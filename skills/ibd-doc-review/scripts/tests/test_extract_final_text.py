#!/usr/bin/env python3
"""
test_extract_final_text.py — extract_final_text.py 自测（阳性 ＋ 阴性双测）

覆盖（阳性面：含修订/批注的源件取终稿）：
   1. `w:ins` 内容**计入**、`w:del`／`w:delText` **排除**
   2. 标注头给出 ins／del 计数
   3. 批注文本**不进正文**（在 comments.xml），标注给 comments 计数
   4. `w:del` 内嵌套 `w:ins` 一并排除（接受全部修订语义）
   5. `w:tab` → 制表符、`w:br` → 换行
（阴性面：无修订/批注的源件不得变味）
   6. 逐行等于原文，零改写
   7. 标注为「原件无修订/批注」，不误报
（接口与安全）
   8. `--check` 只探测、不出正文
   9. `--json` 结构化字段齐备
  10. `-o` 落盘内容与 stdout 一致
  11. 源文件零改动（sha256 不变）
  12. 文件不存在 / 非 docx → 退出码 2
运行：python scripts/tests/test_extract_final_text.py
"""
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SKILL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPT = os.path.join(SKILL_DIR, "scripts", "extract_final_text.py")
GATE_TEST = os.path.join(os.path.dirname(__file__), "test_deliver_gate.py")

_spec = importlib.util.spec_from_file_location("t_gate", GATE_TEST)
tg = importlib.util.module_from_spec(_spec)
sys.modules["t_gate"] = tg
_spec.loader.exec_module(tg)

_para, _pkt = tg._para, tg._pkt
ins_run, del_run = tg.ins_run, tg.del_run
WNS = tg.WNS
TEXT_TITLE, TEXT_SUB = tg.TEXT_TITLE, tg.TEXT_SUB

TAIL = " 其余文字。"
OLD, NEW = "旧金额 100 万元", "新金额 200 万元"
CMT_TEXT = "此处口径需复核"
COMMENTS_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<w:comments %s><w:comment w:id="0" w:author="复核人" w:date="2026-09-24T09:00:00Z">'
    '<w:p><w:r><w:t xml:space="preserve">%s</w:t></w:r></w:p></w:comment></w:comments>' % (WNS, CMT_TEXT)
)


def make(path, body_xml, comments=None):
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
           '<w:document %s><w:body>%s<w:sectPr/></w:body></w:document>' % (WNS, body_xml))
    _pkt(path, doc, comments=comments)


def revised_body(tail=TAIL, rid=0, extra=""):
    """标题 ＋ 小标题 ＋ 「旧 → 新 ＋ 其余文字」段（成对 ins/del）"""
    return (_para("000", TEXT_TITLE) + _para("0011", TEXT_SUB)
            + '<w:p><w:pPr><w:pStyle w:val="001"/></w:pPr>'
            + del_run(OLD, rid) + ins_run(NEW, rid)
            + '<w:r><w:t xml:space="preserve">%s</w:t></w:r>%s</w:p>' % (tail, extra))


def plain_body():
    return _para("000", TEXT_TITLE) + _para("0011", TEXT_SUB) + _para("001", "已落定正文。")


def run(args_list):
    p = subprocess.run([sys.executable, SCRIPT] + args_list,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def body_of(out):
    """取 `--- 正文 ---` 之后的部分。"""
    _, _, tail = out.partition("--- 正文 ---\n")
    return tail


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


class TestExtractFinalText(unittest.TestCase):

    def setUp(self):
        self._d = tempfile.TemporaryDirectory()
        self.d = self._d.name
        self.addCleanup(self._d.cleanup)

    def p(self, n):
        return os.path.join(self.d, n)

    # ------------------------------------------------------------ 阳性面
    def test_01_ins_counted_del_excluded(self):
        f = self.p("rev.docx")
        make(f, revised_body())
        rc, out = run([f])
        self.assertEqual(rc, 0, out)
        body = body_of(out)
        self.assertIn(NEW, body, out)
        self.assertNotIn(OLD, body, out)

    def test_02_banner_counts(self):
        f = self.p("rev.docx")
        make(f, revised_body())
        rc, out = run([f, "--check"])
        self.assertEqual(rc, 0, out)
        self.assertIn("ins=1 del=1", out)
        self.assertIn("该文件原件含修订/批注", out)

    def test_03_comment_not_in_body(self):
        f = self.p("cmt.docx")
        make(f, revised_body(), comments=COMMENTS_XML)
        rc, out = run([f])
        self.assertEqual(rc, 0, out)
        self.assertIn("comments=1", out)
        self.assertNotIn(CMT_TEXT, body_of(out), out)

    def test_04_nested_ins_inside_del_excluded(self):
        f = self.p("nest.docx")
        nested = ('<w:del w:id="0" w:author="复核人"><w:r><w:delText xml:space="preserve">被删</w:delText></w:r>'
                  '<w:ins w:id="0" w:author="复核人"><w:r><w:t xml:space="preserve">嵌套新</w:t></w:r></w:ins>'
                  '</w:del>')
        make(f, revised_body(extra=nested))
        rc, out = run([f])
        self.assertEqual(rc, 0, out)
        body = body_of(out)
        self.assertNotIn("被删", body, out)
        self.assertNotIn("嵌套新", body, out)

    def test_05_tab_and_break_normalized(self):
        f = self.p("wf.docx")
        body = (_para("000", TEXT_TITLE)
                + '<w:p><w:r><w:t xml:space="preserve">A</w:t><w:tab/><w:t xml:space="preserve">B</w:t>'
                  '<w:br/><w:t xml:space="preserve">C</w:t></w:r></w:p>')
        make(f, body)
        rc, out = run([f])
        self.assertEqual(rc, 0, out)
        self.assertIn("A\tB\nC\n", body_of(out), out)

    # ------------------------------------------------------------ 阴性面
    def test_06_clean_file_unchanged(self):
        f = self.p("clean.docx")
        make(f, plain_body())
        rc, out = run([f])
        self.assertEqual(rc, 0, out)
        self.assertEqual(body_of(out),
                         "%s\n%s\n已落定正文。\n" % (TEXT_TITLE, TEXT_SUB), out)

    def test_07_clean_file_no_false_flag(self):
        f = self.p("clean.docx")
        make(f, plain_body())
        rc, out = run([f])
        self.assertIn("ins=0 del=0 comments=0", out)
        self.assertIn("原件无修订/批注", out)
        self.assertNotIn("【该文件原件含修订/批注】", out)

    # ------------------------------------------------------------ 接口与安全
    def test_08_check_mode_has_no_body(self):
        f = self.p("rev.docx")
        make(f, revised_body())
        rc, out = run([f, "--check"])
        self.assertEqual(rc, 0, out)
        self.assertNotIn("--- 正文 ---", out)
        self.assertNotIn(NEW, out)

    def test_09_json_fields(self):
        f = self.p("cmt.docx")
        make(f, revised_body(), comments=COMMENTS_XML)
        rc, out = run([f, "--json"])
        self.assertEqual(rc, 0, out)
        data = json.loads(out)
        self.assertEqual(data["tool"], "extract_final_text")
        self.assertEqual((data["ins"], data["del"], data["comments"]), (1, 1, 1))
        self.assertTrue(data["flagged"])
        self.assertEqual(data["verdict"], "PASS")
        self.assertTrue(data["chars"] > 0)

    def test_10_output_file_matches_stdout(self):
        f = self.p("rev.docx")
        out_p = self.p("final.txt")
        make(f, revised_body())
        proc = subprocess.run([sys.executable, SCRIPT, f, "-o", out_p],
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
        out = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, out)
        self.assertTrue(os.path.exists(out_p), out)
        with io.open(out_p, encoding="utf-8") as fh:
            saved = fh.read()
        self.assertEqual(saved.rstrip("\n"), (proc.stdout or "").rstrip("\n"))
        self.assertEqual(saved.count("\r\n"), 0, "输出文件须为 LF，不得带 CRLF")

    def test_11_source_untouched(self):
        f = self.p("rev.docx")
        make(f, revised_body())
        before = sha(f)
        run([f])
        run([f, "--check"])
        self.assertEqual(sha(f), before, "源文件被改动（本脚本必须只读）")

    def test_12_bad_input_returns_2(self):
        rc, out = run([self.p("nope.docx")])
        self.assertEqual(rc, 2, out)
        bad = self.p("not.docx")
        with io.open(bad, "w", encoding="utf-8") as fh:
            fh.write("这不是 docx")
        rc, out = run([bad])
        self.assertEqual(rc, 2, out)
        self.assertIn("ERROR", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)

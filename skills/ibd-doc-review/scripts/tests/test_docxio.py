#!/usr/bin/env python3
"""
test_docxio.py — docxio 自测（合成包，快速档）

覆盖抽层前实测出的四类差异（每一类都对应一个真实坑）：
  1. **实体解码**：`&amp;`/`&lt;` 必须解成 `&`/`<`（正则流派不解，会把 `&amp;` 里的 `;`
     当半角分号假报；真实招股书含 8 处实体）
  2. **段落文本口径**：tab/br 是否映射、`w:delText` 是否计入 —— 各调用点口径不同，必须可选
  3. **表格与正文**：`iter_paras(include_table=False)` 只出正文段（表格 22,535 格 vs 正文 909 段，
     混算分母差 25 倍）
  4. **容器递归**：`w:sdt` / `w:customXml` 包裹的段落须能下钻（只此一层做了，其余脚本会整块漏读）
  另覆盖：自闭合 `<w:p/>` 计空段、`flat_text` 两种口径、strip_punct/norm_for_compare 同口径。

运行：python scripts/tests/test_docxio.py
"""
import importlib.util
import os
import sys
import tempfile
import unittest
from xml.sax.saxutils import escape

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, "..", ".."))
_spec = importlib.util.spec_from_file_location("docxio", os.path.join(PKG, "scripts", "docxio.py"))
dx = importlib.util.module_from_spec(_spec)
sys.modules["docxio"] = dx
_spec.loader.exec_module(dx)

W = dx.W_NS


def P(text=None, style=None, raw_runs=""):
    """造一个 w:p；text 走转义，raw_runs 用于插入 tab/br/delText 等原样片段。"""
    ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    runs = f"<w:r><w:t>{escape(text)}</w:t></w:r>" if text is not None else ""
    return f"<w:p>{ppr}{runs}{raw_runs}</w:p>"


def build(path, body):
    import zipfile
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
           f'<w:document xmlns:w="{W}"><w:body>{body}</w:body></w:document>')
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", doc)


class Base(unittest.TestCase):
    def setUp(self):
        self._d = tempfile.TemporaryDirectory()
        self.path = os.path.join(self._d.name, "t.docx")

    def tearDown(self):
        self._d.cleanup()

    def bundle(self, body):
        build(self.path, body)
        return dx.open_docx(self.path)


class TestEntities(Base):

    def test_entities_decoded(self):
        """实体必须由解析器解码——正则流派会留下字面量 &amp;。"""
        b = self.bundle(P("某发行人 & 合作方 <测试>"))
        txt = dx.flat_text(b)
        self.assertEqual(txt, "某发行人 & 合作方 <测试>")
        self.assertNotIn("&amp;", txt)

    def test_ampersand_does_not_create_semicolon(self):
        """真实场景：`7&11` 若未解码会变成 `7&amp;11`，其 `;` 会被标点检查当半角分号。"""
        b = self.bundle(P("7&11"))
        self.assertNotIn(";", dx.flat_text(b))


class TestParaText(Base):

    def test_tab_break_optional(self):
        body = ('<w:p><w:r><w:t>A</w:t><w:tab/><w:t>B</w:t><w:br/><w:t>C</w:t></w:r></w:p>')
        b = self.bundle(body)
        p = next(dx.iter_paras(b))
        self.assertEqual(p.text, "A\tB\nC", "默认应映射 tab/br（plan_review 口径）")
        b2 = self.bundle(body)
        p2 = next(dx.iter_paras(b2, tabs=False, breaks=False))
        self.assertEqual(p2.text, "ABC", "关掉后应等价于 deliver_gate 口径")

    def test_deltext_optional(self):
        body = ('<w:p><w:r><w:t>保留</w:t></w:r>'
                '<w:del><w:r><w:delText>删掉</w:delText></w:r></w:del></w:p>')
        b = self.bundle(body)
        self.assertEqual(next(dx.iter_paras(b)).text, "保留", "取终稿口径须排除 delText")
        b2 = self.bundle(body)
        self.assertEqual(next(dx.iter_paras(b2, del_text=True)).text, "保留删掉")


class TestTables(Base):

    def test_table_paras_flagged_and_filterable(self):
        body = (P("正文一") +
                "<w:tbl><w:tr><w:tc>" + P("格A") + P("格B") + "</w:tc></w:tr></w:tbl>" +
                P("正文二"))
        b = self.bundle(body)
        allp = list(dx.iter_paras(b, include_table=True))
        self.assertEqual([p.text for p in allp], ["正文一", "格A", "格B", "正文二"])
        self.assertEqual([p.in_table for p in allp], [False, True, True, False])

        only_body = list(dx.iter_paras(b, include_table=False))
        self.assertEqual([p.text for p in only_body], ["正文一", "正文二"])

    def test_table_count(self):
        body = "<w:tbl><w:tr><w:tc>" + P("x") + "</w:tc></w:tr></w:tbl>"
        b = self.bundle(body)
        self.assertEqual(len(list(dx.iter_tables(b))), 1)
        tbl = next(dx.iter_tables(b))
        self.assertEqual(len(list(dx.table_cells(tbl))), 1)


class TestContainers(Base):

    def test_sdt_recursion_on_off(self):
        body = ('<w:sdt><w:sdtContent>' + P("控件里的字") + '</w:sdtContent></w:sdt>' + P("普通段"))
        b = self.bundle(body)
        on = [p.text for p in dx.iter_paras(b, dive_sdt=True)]
        self.assertEqual(on, ["控件里的字", "普通段"], "下钻后才能读到控件内段落")
        b2 = self.bundle(body)
        off = [p.text for p in dx.iter_paras(b2, dive_sdt=False)]
        self.assertEqual(off, ["普通段"], "不下钻会整块漏读——其余脚本的旧行为")

    def test_self_closing_para_is_empty(self):
        b = self.bundle("<w:p/>" + P("有字"))
        ps = list(dx.iter_paras(b, include_table=False))
        self.assertEqual([p.text for p in ps], ["", "有字"])
        self.assertEqual(sum(1 for p in ps if not p.text.strip()), 1)


class TestFlatText(Base):

    def test_two_dialects(self):
        body = P("第一段") + P("第二段")
        b = self.bundle(body)
        self.assertEqual(dx.flat_text(b), "第一段第二段", "无分隔（deliver_gate 口径）")
        b2 = self.bundle(body)
        self.assertEqual(dx.flat_text(b2, para_sep="\n"), "第一段\n第二段", "段落分隔（plan_review 口径）")

    def test_include_table_toggle(self):
        body = P("正文") + "<w:tbl><w:tr><w:tc>" + P("格里") + "</w:tc></w:tr></w:tbl>"
        b = self.bundle(body)
        self.assertEqual(dx.flat_text(b, include_table=True), "正文格里")
        b2 = self.bundle(body)
        self.assertEqual(dx.flat_text(b2, include_table=False, para_sep=""), "正文")


class TestRegexCampEntities(Base):
    """正则流派也必须解码实体（0.55.0 修）：`&lt;` 自带的分号曾被当半角标点。"""

    def test_regex_text_decodes(self):
        frag = "<w:t>《关于新&lt;公司法&gt;配套制度》及 7&amp;11</w:t>"
        self.assertEqual(dx.regex_text(frag), "《关于新<公司法>配套制度》及 7&11")
        self.assertNotIn("&lt;", dx.regex_text(frag))

    def test_content_common_same(self):
        """content_common 是"不依赖兄弟模块"的独立模块，故内联 html.unescape——结果须一致。"""
        spec = importlib.util.spec_from_file_location(
            "cc_ent", os.path.join(PKG, "scripts", "content_common.py"))
        cc = importlib.util.module_from_spec(spec)
        sys.modules["cc_ent"] = cc
        spec.loader.exec_module(cc)
        frag = "<w:t>7&amp;11 与 &lt;公司法&gt;</w:t>"
        self.assertEqual(cc._text_of(frag), dx.regex_text(frag))
        self.assertEqual(cc._text_of(frag), "7&11 与 <公司法>")


class TestNorm(Base):

    def test_strip_punct_same_as_gate(self):
        s = '他说“好”（见（一））"x"'
        out = dx.strip_punct(s)
        for ch in ('"', "“", "”", "(", ")", "（", "）"):
            self.assertNotIn(ch, out)
        self.assertIn("他说好见一x", out)

    def test_norm_for_compare(self):
        # 方括号/圆括号**不**去除——这是与 deliver_gate 同源核验口径保持一致的结果，
        # 不是"更干净"的口径；抽层只搬家，不改判据。
        self.assertEqual(dx.norm_for_compare("**粗** [链接](x) 说 明"), "粗[链接](x)说明")

    def test_bad_package(self):
        p = os.path.join(self._d.name, "bad.docx")
        import zipfile
        with zipfile.ZipFile(p, "w") as z:
            z.writestr("x.txt", "no document")
        with self.assertRaises(ValueError):
            dx.open_docx(p)


if __name__ == "__main__":
    unittest.main(verbosity=2)

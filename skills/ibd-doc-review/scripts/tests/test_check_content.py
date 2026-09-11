#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_check_content.py — ibd-doc-review 格式核对模块自测（P2-⑧ 拆组配套）

背景：check_content.py 于 2026-09-11 按业务域拆为四文件
  content_common.py / content_text.py / content_table.py / check_content.py（CLI 入口）。
原 check_content 的用例寄生在 test_check_styles.py（经 CLI 调用，只覆盖端到端），
本文件补两组此前**无处覆盖**的风险：

  E 组 · 模块结构契约（拆组专属）
    · 三模块可独立 import，且不反向依赖 check_content（无循环）
    · CHECK_REGISTRY 的 11 个 id 全部能在对应业务域模块找到同名函数
    · 组名 text/table 的成员与 CHECK_REGISTRY.group 字段一致
    · content_common 的标点基元返回值形态正确（C/E/O 三分类 + 元组）

  F 组 · 核对行为（直调函数，不经 CLI，覆盖纯逻辑路径）
    · heading_seq 跳号 / 重号检出
    · spaces 数字前后空格（2026-09-11 新增子项）
    · punctuation 中文语境半角标点
    · table_font 违规字号
    · table_empty vMerge 续格不计空
    · check_geo 清单驱动 + 严重度映射
    · terms 内置规则命中

运行：python scripts/tests/test_check_content.py
"""
import os
import sys
import tempfile
import unittest
import zipfile

SKILL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPTS = os.path.join(SKILL_DIR, "scripts")
sys.path.insert(0, SCRIPTS)

import content_common  # noqa: E402
import content_table  # noqa: E402
import content_text  # noqa: E402
import check_content  # noqa: E402

NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


# ---------------------------------------------------------------- fixture

def make_mini_docx(path, paras, tables=None):
    """paras: [(style|None, text)]；tables: [[ (cell_text, sz|None), ... ], ...]
    即 tables = 表格列表，每表 = 行列表，每行 = 单元格列表，单元格 = (文本, 字号半点值)。
    """
    body = []
    for style, text in paras:
        pstyle = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
        body.append(f"<w:p>{pstyle}<w:r><w:t>{text}</w:t></w:r></w:p>")
    for tbl in (tables or []):
        rows_xml = []
        for row in tbl:
            cells_xml = []
            for cell in row:
                txt, sz = cell
                szxml = f'<w:sz w:val="{sz}"/>' if sz is not None else ""
                cells_xml.append(
                    f"<w:tc><w:tcPr>{szxml}</w:tcPr>"
                    f"<w:p><w:r><w:t>{txt}</w:t></w:r></w:p></w:tc>")
            rows_xml.append(f"<w:tr>{''.join(cells_xml)}</w:tr>")
        body.append(f"<w:tbl>{''.join(rows_xml)}</w:tbl>")
    doc = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<w:document {NS}><w:body>{"".join(body)}<w:sectPr/></w:body></w:document>'
    )
    ct = (
        '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        "</Relationships>"
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc)
    return path


# ================================================================== E. 模块结构契约


class ModuleContractTest(unittest.TestCase):
    """拆组专属契约：模块边界、登记表挂载、无循环依赖。"""

    def test_01_modules_import_without_cycle(self):
        """三模块各自可 import；且 content_common 不反向依赖任何兄弟模块。"""
        import ast
        for fn in ("content_common.py",):
            tree = ast.parse(open(os.path.join(SCRIPTS, fn), encoding="utf-8").read())
            imported = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported |= {a.name.split(".")[0] for a in node.names}
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split(".")[0])
            sibs = {"content_text", "content_table", "check_content"}
            self.assertEqual(imported & sibs, set(),
                             f"{fn} 不应 import 兄弟模块（避免循环依赖）")

    def test_02_registry_ids_all_have_impl(self):
        """CHECK_REGISTRY 的每个 id，都要能在对应业务域模块找到同名函数。"""
        text_impl = {n for n in dir(content_text) if n.startswith("check_")}
        table_impl = {n for n in dir(content_table) if n.startswith("check_")}
        for item in check_content.CHECK_REGISTRY:
            cid = item["id"]
            fn = f"check_{cid}"
            pool = text_impl if item["group"] == "text" else table_impl
            self.assertIn(fn, pool,
                          f"核对项 {cid}（组 {item['group']}）应在 "
                          f"{'content_text' if item['group'] == 'text' else 'content_table'}.py 有 {fn}")

    def test_03_group_members_match_registry(self):
        """GROUPS 的 text/table 成员 = CHECK_REGISTRY 按 group 分流的结果。"""
        expected_text = [c["id"] for c in check_content.CHECK_REGISTRY if c["group"] == "text"]
        expected_table = [c["id"] for c in check_content.CHECK_REGISTRY if c["group"] == "table"]
        self.assertEqual(check_content.GROUPS["text"], expected_text)
        self.assertEqual(check_content.GROUPS["table"], expected_table)
        self.assertEqual(len(expected_text), 7, "文字类应为 7 项")
        self.assertEqual(len(expected_table), 4, "表格类应为 4 项")

    def test_04_runners_cover_all_registry_ids(self):
        """run() 的 runners 必须覆盖全部登记 id（漏挂 = 静默返回空）。"""
        import inspect
        src = inspect.getsource(check_content.run)
        for item in check_content.CHECK_REGISTRY:
            self.assertIn(f'"{item["id"]}":', src,
                          f"runners 缺 {item['id']}——该核对项会被静默跳过")

    def test_05_punct_primitives_shape(self):
        """标点基元返回形态：_char_class 返 C/E/O；_neighbor_class 返 (类, 索引)。"""
        self.assertEqual(content_common._char_class("中"), "C")
        self.assertEqual(content_common._char_class("A"), "E")
        self.assertEqual(content_common._char_class("1"), "E")
        self.assertEqual(content_common._char_class("-"), "O")
        cls, idx = content_common._neighbor_class("a b", 1, 1)
        self.assertEqual(cls, "E")
        self.assertEqual(idx, 2, "_neighbor_class 应跳过空格取下一个非空字符")
        self.assertEqual(content_common._neighbor_class("x", 0, 1), (None, None))

    def test_06_resolve_checks_group_and_id(self):
        """resolve_checks 支持 all / 组名 / 单 id / 混合，且保持登记表顺序。"""
        self.assertEqual(len(check_content.resolve_checks("all")), 11)
        self.assertEqual(check_content.resolve_checks("table"),
                         ["table_font", "table_align", "table_empty", "table_na"])
        self.assertEqual(check_content.resolve_checks("geo,table_na"),
                         ["geo", "table_na"])
        # 顺序以登记表为准（geo 在 table_na 前，即便入参相反）
        self.assertEqual(check_content.resolve_checks("table_na,geo"),
                         ["geo", "table_na"])


# ================================================================== F. 核对行为


class TextChecksTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = lambda n: os.path.join(self.tmp.name, n)

    def tearDown(self):
        self.tmp.cleanup()

    def _items(self, paras, tables=None):
        path = make_mini_docx(self.p("t.docx"), paras, tables)
        xmls = content_common.load_docx(path)
        doc = xmls["word/document.xml"]
        return content_common.extract_structure(doc), content_common.full_text_of(doc)

    def test_07_heading_seq_jump_detected(self):
        items, _ = self._items([(None, "一、第一项"), (None, "二、第二项"), (None, "四、跳号")])
        issues = content_text.check_heading_seq(items)
        self.assertTrue(issues, "三级跳号应被检出")
        self.assertTrue(any("跳号" in i.problem for i in issues),
                        f"应报跳号，实际：{[i.problem for i in issues]}")

    def test_08_heading_seq_dup_detected(self):
        items, _ = self._items([(None, "一、甲"), (None, "一、重号")])
        issues = content_text.check_heading_seq(items)
        self.assertTrue(any("重号" in i.problem for i in issues),
                        f"应报重号，实际：{[i.problem for i in issues]}")

    def test_09_spaces_cjk_num(self):
        """数字前后空格（2026-09-11 新子项，HIGH）。"""
        items, _ = self._items([(None, "公司注册资本为 100 万元人民币，已足额缴纳。")])
        issues = content_text.check_spaces(items)
        self.assertTrue(any("数字" in i.problem for i in issues),
                        f"应报数字前后空格，实际：{[i.problem for i in issues]}")

    def test_10_spaces_dup_punct(self):
        items, _ = self._items([(None, "这是测试文案内容，，出现了重复标点。")])
        issues = content_text.check_spaces(items)
        self.assertTrue(any("重复" in i.problem or "重复" in i.suggestion for i in issues),
                        f"应报重复标点，实际：{[i.problem for i in issues]}")

    def test_11_punctuation_half_in_cjk(self):
        items, _ = self._items([(None, "本次发行采用,余额包销方式,由保荐机构负责。")])
        issues = content_text.check_punctuation(items)
        self.assertTrue(any("半角" in i.problem for i in issues),
                        f"中文语境半角逗号应被检出，实际：{[i.problem for i in issues]}")

    def test_12_terms_builtin_rules(self):
        _, full = self._items([(None, "发行人的帐面价值与其它资产均已核实完毕。")])
        issues = content_text.check_terms(full)
        joined = " ".join(i.problem for i in issues)
        self.assertIn("账", joined, "内置规则应报「帐」→「账」")

    def test_13_geo_rules_severity_mapping(self):
        """清单驱动 + CRITICAL→HIGH 严重度映射。"""
        rules = [{"pattern": "台湾", "level": "CRITICAL", "note": "地区表述", "suggestion": "中国台湾"}]
        issues = content_text.check_geo("公司在台湾设有分支机构。", rules)
        self.assertTrue(issues, "命中敏感词应出问题")
        self.assertEqual(issues[0].severity, "HIGH", "CRITICAL 应映射为 HIGH")

    def test_14_geo_empty_rules_no_issue(self):
        self.assertEqual(content_text.check_geo("任意文本 CPU 芯片", []), [])


class TableChecksTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = lambda n: os.path.join(self.tmp.name, n)

    def tearDown(self):
        self.tmp.cleanup()

    def _tables(self, paras, table):
        """table: 单张表 = 行列表，每行 = [(文本, 字号|None), ...]。"""
        path = make_mini_docx(self.p("t.docx"), paras, [table])
        xmls = content_common.load_docx(path)
        return content_common.parse_tables(xmls["word/document.xml"])

    def test_15_table_font_bad_size(self):
        """sz=24（12pt）为违规字号（合法仅 21/18）。表格需 ≥3 行且含数字。"""
        tables = self._tables([(None, "正文")], [
            [("项目", None), ("金额", None)],
            [("营业收入", None), ("1,234.00", 24)],
            [("净利润", None), ("567.00", 24)],
        ])
        issues = content_table.check_table_font(tables)
        self.assertTrue(issues, "违规字号应被检出")
        self.assertTrue(any("12pt" in i.snippet or "sz=24" in i.snippet for i in issues),
                        f"应指明违规字号，实际：{[i.snippet for i in issues]}")

    def test_16_table_font_ok_size_no_issue(self):
        tables = self._tables([(None, "正文")], [
            [("项目", 21), ("金额", 21)],
            [("营业收入", 21), ("1,234.00", 21)],
            [("净利润", 21), ("567.00", 18)],
        ])
        self.assertEqual(content_table.check_table_font(tables), [],
                         "五号/小五均属合法，不应报")

    def test_17_table_not_formal_skipped(self):
        """≤2 行的表格（封面提示框）豁免字号检查。"""
        tables = self._tables([(None, "正文")], [
            [("提示", 24), ("内容", 24)],
            [("说明", 24), ("正文", 24)],
        ])
        self.assertEqual(content_table.check_table_font(tables), [],
                         "行数≤2 应豁免（非正式数据表）")

    def test_18_table_empty_excludes_vmerge_continue(self):
        """vMerge 续格（continue）不计入空单元格（2026-09-10 补充）。"""
        tbl = {
            "no": 1, "head": "测试表",
            "rows": [
                [{"text": "因素", "vmerge": None}, {"text": "说明", "vmerge": None}],
                [{"text": "共性", "vmerge": "restart"}, {"text": "", "vmerge": "continue"}],
                [{"text": "", "vmerge": "continue"}, {"text": "", "vmerge": "continue"}],
            ],
        }
        issues = content_table.check_table_empty([tbl])
        self.assertEqual(issues, [],
                         "全部空单元格都是 vMerge 续格，不应报空")

    def test_19_table_empty_detects_real_empty(self):
        tbl = {
            "no": 1, "head": "测试表",
            "rows": [
                [{"text": "项目", "vmerge": None}, {"text": "金额", "vmerge": None}],
                [{"text": "甲", "vmerge": None}, {"text": "", "vmerge": None}],
                [{"text": "乙", "vmerge": None}, {"text": "100.00", "vmerge": None}],
            ],
        }
        issues = content_table.check_table_empty([tbl])
        self.assertTrue(issues, "真实空单元格应被检出")
        self.assertIn("1", issues[0].snippet, "应报 1 个空单元格")

    def test_20_table_na_alignment(self):
        tbl = {
            "no": 1, "head": "测试表",
            "rows": [
                [{"text": "项目", "vmerge": None}, {"text": "数值", "vmerge": None}],
                [{"text": "甲", "vmerge": None}, {"text": "—", "vmerge": None}],
                [{"text": "乙", "vmerge": None}, {"text": "不适用", "vmerge": None}],
            ],
        }
        issues = content_table.check_table_na([tbl])
        self.assertTrue(issues, "同表内混用 — 与 不适用 应被检出")


if __name__ == "__main__":
    unittest.main(verbosity=2)

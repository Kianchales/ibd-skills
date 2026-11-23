#!/usr/bin/env python3
"""
test_plan_review.py — plan_review.py 自测（分层口径 ＋ 批次 ＋ 台账 ＋ CLI）

覆盖：
  分母口径
   1. 正文段：非表内、>40 字、含句读 —— 三条同时满足才算
   2. 短句／中段／标题／目录 各自归位，互不串类
   3. 空段落不计入分母（分母＝非空段）
   4. 目录行（含制表符／尾部页码）识别为「目录」，不作节锚点、不计入分母
   5. 表格按 w:tbl 计数，单元格段落随表；表格不单独判
   6. **五类之和 ＝ 总段**（漏归即报「❌ 不符」）
  批次
   7. 小容量 → 多批；批次区间**首尾相接覆盖 1..总段**
   8. 初始容量下单节文档 → 1 批
   9. 目录行不产生独立批次（否则目录页会切出空批）
  CLI 与产物
  10. 生成 `_复核计划.md`，含「校验：✅ 五类之和相符」与台账骨架
  11. `--emit-batches` 生成 Bxx_batch.txt，段号与原文逐字一致
  12. `--json` 字段齐备（name/stats/batches）
  13. 源 docx 零改动（sha256 不变）

运行：python scripts/tests/test_plan_review.py
"""
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SKILL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPT = os.path.join(SKILL_DIR, "scripts", "plan_review.py")
GATE_TEST = os.path.join(os.path.dirname(__file__), "test_deliver_gate.py")

_spec = importlib.util.spec_from_file_location("t_gate_pr", GATE_TEST)
tg = importlib.util.module_from_spec(_spec)
sys.modules["t_gate_pr"] = tg
_spec.loader.exec_module(tg)
_para, _pkt = tg._para, tg._pkt

_s2 = importlib.util.spec_from_file_location("t_pr", SCRIPT)
pr = importlib.util.module_from_spec(_s2)
sys.modules["t_pr"] = pr
_s2.loader.exec_module(pr)

PROSE = "公司本期营业收入为十二亿三千四百万元，较上期增长两成，主要系产品结构改善所致，详见本节第七部分的分析说明。"
PROSE2 = "报告期内公司研发投入持续增加，主要投向多核异构芯片架构与编解码算法，研发人员占比保持稳定，未发生重大不利变化。"
PROSE3 = "本次募集资金拟投向新一代云端训练推理一体芯片项目，项目建设期为三年，达产后将显著提升公司在云端算力领域的供给能力。"
SHORT = "合计"                                     # 短句（<15 字）
MID = "上述金额与审定数存在差异的原因说明如下所述"        # 中段（15–40 字）
TOC_LINE = "第2节 测试\t12"                          # 目录行（含制表符）


def _tbl(cells):
    tcs = "".join("<w:tc><w:p><w:r><w:t xml:space=\"preserve\">%s</w:t></w:r></w:p></w:tc>" % c
                  for c in cells)
    return "<w:tbl><w:tr>%s</w:tr></w:tbl>" % tcs


def body():
    return (_para("001", "第1节 测试")      # 标题
            + _para("000", PROSE)           # 正文 A
            + _para("000", SHORT)           # 短句
            + _para("000", MID)             # 中段
            + _para("000", TOC_LINE)        # 目录行
            + "<w:p/>"                      # 空段落
            + _tbl(["单元一", "单元二"])     # 1 表 / 2 单元格
            + _para("000", PROSE2)          # 正文 B
            + _para("001", "第2节 测试")     # 标题
            + _para("000", PROSE3))         # 正文 C


def make(path):
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
           '<w:document %s><w:body>%s<w:sectPr/></w:body></w:document>' % (tg.WNS, body()))
    _pkt(path, doc)


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def run(args):
    p = subprocess.run([sys.executable, SCRIPT] + args,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


class TestDenominator(unittest.TestCase):
    """分母口径：分层准确、五类之和校验通过。"""

    def setUp(self):
        self._d = tempfile.TemporaryDirectory()
        self.docx = os.path.join(self._d.name, "口径.docx")
        make(self.docx)
        self.units, self.stats = pr.load_units(self.docx)

    def tearDown(self):
        self._d.cleanup()

    def test_counts(self):
        self.assertEqual(self.stats["正文"], 3, "正文段应为 3 段")
        self.assertEqual(self.stats["标题"], 2, "标题应为 2 条")
        self.assertEqual(self.stats["短句"], 1)
        self.assertEqual(self.stats["中段"], 1)
        self.assertEqual(self.stats["目录"], 1, "含制表符的行应判为目录")
        self.assertEqual(self.stats["空段落"], 1)
        self.assertEqual(self.stats["表格"], 1)
        self.assertEqual(self.stats["单元格"], 2)

    def test_sum_equals_total(self):
        self.assertEqual(self.stats["_校验_五类之和"], self.stats["总段"],
                         "五类之和必须等于总段，否则说明有段未归")

    def test_prose_needs_all_three(self):
        """正文段须同时满足：非表内 ＋ >40 字 ＋ 含句读。"""
        texts = [u["text"] for u in self.units if u["type"] == "正文"]
        self.assertIn(PROSE, texts)
        self.assertNotIn(SHORT, texts)
        self.assertNotIn(MID, texts)
        self.assertNotIn("单元一", texts, "表内段落不得计入正文段")

    def test_empty_paragraph_excluded(self):
        self.assertFalse([u for u in self.units
                          if u["type"] == "空段落" and u["text"].strip()])


class TestBatches(unittest.TestCase):

    def setUp(self):
        self._d = tempfile.TemporaryDirectory()
        self.docx = os.path.join(self._d.name, "批次.docx")
        make(self.docx)
        self.units, _ = pr.load_units(self.docx)

    def tearDown(self):
        self._d.cleanup()

    def _assign_lines(self):
        n = 0
        for u in self.units:
            if u["type"] in ("表格", "空段落"):
                continue
            n += 1
            u["line"] = n
        return n

    def test_default_capacity_single_batch(self):
        total = self._assign_lines()
        bs = pr.build_batches(self.units, 400, 50)
        self.assertEqual(len(bs), 1, "两个小节合计远小于容量，应合成 1 批")
        lines = [u["line"] for u in bs[0]["items"] if u.get("line")]
        self.assertEqual((min(lines), max(lines)), (1, total))

    def test_small_capacity_multi_batch_contiguous(self):
        total = self._assign_lines()
        bs = pr.build_batches(self.units, 2, 1)
        self.assertGreater(len(bs), 1)
        prev = 0
        for i, b in enumerate(bs, 1):
            lines = [u["line"] for u in b["items"] if u.get("line")]
            if not lines:
                continue
            self.assertEqual(min(lines), prev + 1, "第 %d 批起点必须接上一批末尾" % i)
            prev = max(lines)
        self.assertEqual(prev, total, "末批必须覆盖到总段")

    def test_toc_is_not_anchor(self):
        """目录行不得成为节锚点（否则目录页会切出空批）。"""
        self._assign_lines()
        bs = pr.build_batches(self.units, 400, 50)
        names = " ".join(b["name"] for b in bs)
        self.assertNotIn("第2节 测试\t12", names)


class TestLevels(unittest.TestCase):
    """标题层级自动识别：顶层可能是 第1节／第一节／问题N.／一、／1、，不许硬编码。"""

    def _units(self, headings):
        """用给定标题串造 docx，返回 units。"""
        _d = tempfile.TemporaryDirectory()
        self.addCleanup(_d.cleanup)
        path = os.path.join(_d.name, "层级.docx")
        xml = "".join(_para("001", h) + _para("000", PROSE) for h in headings)
        doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
               '<w:document %s><w:body>%s</w:body></w:document>' % (tg.WNS, xml))
        _pkt(path, doc)
        return pr.load_units(path)[0]

    def test_arabic_section(self):
        u = self._units(["第1节 甲", "第2节 乙"])
        (top, _pat), _ladder, _c, _sp = pr.detect_levels(u)
        self.assertEqual(top, "SEC", "第1节（阿拉伯序号）应识别为节")

    def test_chinese_section(self):
        u = self._units(["第一节 甲", "第二节 乙"])
        self.assertEqual(pr.detect_levels(u)[0][0], "SEC")

    def test_l1_as_top(self):
        u = self._units(["一、甲", "二、乙", "三、丙"])
        self.assertEqual(pr.detect_levels(u)[0][0], "L1", "无节标题时 一、应升为顶层")

    def test_arabic_item_as_top(self):
        u = self._units(["1、甲", "2、乙", "3、丙"])
        self.assertEqual(pr.detect_levels(u)[0][0], "L3", "只用 1、编号时它即为顶层")

    def test_section_beats_item(self):
        """同时有 第X节 与 问题N 时，取更粗的那类（出现次数少者）。"""
        # 两类都需 ≥2 次才参与竞选（单次出现视作残留标题）
        u = self._units(["第一节 甲", "第二节 乙", "问题1.丙", "问题2.丁", "问题3.戊"])
        self.assertEqual(pr.detect_levels(u)[0][0], "SEC", "节比问题更粗，应作顶层")

    def test_toc_not_counted(self):
        """目录行（含制表符）不参与层级统计。"""
        u = self._units(["第1节 甲", "第2节 乙"])
        _d = tempfile.TemporaryDirectory()
        self.addCleanup(_d.cleanup)
        path = os.path.join(_d.name, "目录.docx")
        xml = (_para("001", "第1节 甲\t5") + _para("001", "第2节 乙\t9")
               + _para("001", "第1节 甲") + _para("000", PROSE)
               + _para("001", "第2节 乙") + _para("000", PROSE2))
        doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
               '<w:document %s><w:body>%s</w:body></w:document>' % (tg.WNS, xml))
        _pkt(path, doc)
        units = pr.load_units(path)[0]
        cnt = pr.detect_levels(units)[2]
        self.assertEqual(cnt["SEC"], 2, "目录行的 2 条第X节不得计入")


    def test_question_may_be_child(self):
        """问题N 不天然是顶层：嵌在 一、之下时，顶层应为 一、。"""
        u = self._units(["一、背景情况", "问题1.甲", "问题2.乙", "问题3.丙",
                         "二、说明事项", "问题4.丁"])
        self.assertEqual(pr.detect_levels(u)[0][0], "L1",
                         "问题N 出现在 一、之下时不得抢顶层")

    def test_no_numbered_heading(self):
        """通篇无编号标题（如财务报表附注）→ 不猜层级，交容量按表切。"""
        _d = tempfile.TemporaryDirectory()
        self.addCleanup(_d.cleanup)
        path = os.path.join(_d.name, "无编号.docx")
        xml = _para("001", "企业的基本情况") + _para("000", PROSE) + _para("001", "编制基础") + _para("000", PROSE2)
        doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
               '<w:document %s><w:body>%s</w:body></w:document>' % (tg.WNS, xml))
        _pkt(path, doc)
        u = pr.load_units(path)[0]
        self.assertIsNone(pr.detect_levels(u)[0][0])
        bs = pr.build_batches(u, 1, 1)
        self.assertGreaterEqual(len(bs), 1, "无层级时仍须按容量给出批次")

    def test_descend_keeps_order(self):
        """逐级下探后批次仍须按文档顺序首尾相接。"""
        u = self._units(["第一节 甲", "一、甲一", "二、甲二", "第二节 乙", "一、乙一"])
        n = 0
        for x in u:
            if x["type"] in ("表格", "空段落"):
                continue
            n += 1
            x["line"] = n
        bs = pr.build_batches(u, 1, 1)
        self.assertGreater(len(bs), 1)
        prev = 0
        for b in bs:
            lines = [y["line"] for y in b["items"] if y.get("line")]
            if not lines:
                continue
            self.assertEqual(min(lines), prev + 1)
            prev = max(lines)
        self.assertEqual(prev, n)


class TestCli(unittest.TestCase):

    def setUp(self):
        self._d = tempfile.TemporaryDirectory()
        self.docx = os.path.join(self._d.name, "cli.docx")
        make(self.docx)
        self.out = os.path.join(self._d.name, "plan")

    def tearDown(self):
        self._d.cleanup()

    def test_writes_plan_and_batches(self):
        rc, log = run(["--input", self.docx, "--out", self.out, "--emit-batches"])
        self.assertEqual(rc, 0, log)
        with open(os.path.join(self.out, "_复核计划.md"), encoding="utf-8") as fh:
            plan = fh.read()
        self.assertIn("校验：✅ 五类之和相符", plan)
        self.assertIn("台账骨架", plan)
        self.assertIn("B全文", plan, "计划表必须含全文批行")

        bfile = os.path.join(self.out, "cli", "B01_batch.txt")
        self.assertTrue(os.path.exists(bfile), "应生成 B01_batch.txt")
        with open(bfile, encoding="utf-8") as fh:
            first = [l for l in fh.read().split("\n") if l.startswith("[")]
        self.assertTrue(first)
        m = re.match(r"\[(\d+)\] (.*)", first[0])
        self.assertIsNotNone(m)
        # 段号回查原文
        idx, text = int(m.group(1)), m.group(2).strip()
        seq = [u["text"].strip() for u in pr.load_units(self.docx)[0]
               if u["type"] not in ("表格", "空段落")]
        self.assertEqual(text, seq[idx - 1].strip(), "批文件段号须与原文档逐字一致")

    def test_json_shape(self):
        rc, out = run(["--input", self.docx, "--out", self.out, "--json"])
        self.assertEqual(rc, 0)
        i = out.find("[\n")
        self.assertGreaterEqual(i, 0, "应输出 JSON 数组")
        data = json.loads(out[i:])
        d = data[0]
        self.assertIn("stats", d)
        for k in ("总段", "正文", "表格", "单元格", "空段落", "_校验_五类之和"):
            self.assertIn(k, d["stats"])
        self.assertIn("batches", d)

    def test_source_untouched(self):
        before = sha(self.docx)
        run(["--input", self.docx, "--out", self.out])
        self.assertEqual(before, sha(self.docx), "只读工具不得改动源文件")


if __name__ == "__main__":
    unittest.main(verbosity=2)

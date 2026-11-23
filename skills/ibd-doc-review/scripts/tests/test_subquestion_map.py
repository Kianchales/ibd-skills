#!/usr/bin/env python3
"""
test_subquestion_map.py — subquestion_map.py 自测（切分规则 ＋ 问句类型 ＋ 去重 ＋ CLI）

覆盖：
  子问切分
   1. 行内编号切分：同一段里的「（1）（2）（3）」各自成子问（按段首匹配只能抓到 1 个）
   2. **多组编号取最后一组**：问题原文常先有一段带（1）（2）（3）的背景陈述，
      真子问在后面重新从（1）起 —— 必须丢掉背景组（实测踩过的坑，问题 1 报 9 实为 6）
   3. 无编号提问（「请说明…」整段）→ 单条占位「—」，不硬凑编号
  问句类型（R3 的尺子）
   4. 量化型／原因型／合规型／是否型／说明型 各一例
   5. 量化优先于是否（「量化分析…是否…」判量化）
  题目识别
   6. 目录页重复的「问题N.」（无【回复】且极短）被剔除
   7. 同题号出现多次 → 保留回复最长的一条
  汇总与标注
   8. 无编号题在汇总表标「—（无编号子问）」，不误报「⚠️ 数量不等」
   9. 真不等（子问数≠小节数且非无编号）才标「⚠️」
  CLI
  10. 退出码 0；输出 md 含每题标题与汇总；`--json` 字段齐备

运行：python scripts/tests/test_subquestion_map.py
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

SKILL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPT = os.path.join(SKILL_DIR, "scripts", "subquestion_map.py")
GATE_TEST = os.path.join(os.path.dirname(__file__), "test_deliver_gate.py")

_spec = importlib.util.spec_from_file_location("t_gate_sq", GATE_TEST)
tg = importlib.util.module_from_spec(_spec)
sys.modules["t_gate_sq"] = tg
_spec.loader.exec_module(tg)
_para, _pkt = tg._para, tg._pkt

_s2 = importlib.util.spec_from_file_location("t_sq", SCRIPT)
sq = importlib.util.module_from_spec(_s2)
sys.modules["t_sq"] = sq
_s2.loader.exec_module(sq)

ASK1_BG = "发行人报告期内（1）营业收入持续增长（2）毛利率有所下降（3）经营活动现金流波动较大。"
ASK1_SUB = "请说明：（1）是否存在资金占用情形；（2）量化分析上述事项对当期损益的影响金额。"
ASK1_REP = ["一、关于资金占用：经核查，不存在控股股东占用发行人资金的情形。",
            "二、关于损益影响：经测算，影响金额为一百二十万元，占当期利润总额的百分之一点二。"]
ASK2_ASK = "请说明发行人报告期内劳务派遣用工的具体情况。"
ASK2_REP = ["一、劳务派遣用工的岗位分布与人数情况如下所述，均为临时性辅助性岗位。",
            "二、劳务派遣单位的资质情况，已取得相应的经营许可，合法有效存续至今。",
            "三、发行人的用工合规性，未因劳务派遣受到行政处罚，不存在重大违法情形。"]
TOC_DUP = "问题1.关于A事项（目录）"


def body():
    ps = [_para("0011", "问题1.关于A事项"),
          _para("001", ASK1_BG),
          _para("001", ASK1_SUB),
          _para("000", "【回复】")]
    ps += [_para("000", t) for t in ASK1_REP]
    ps += [_para("0011", TOC_DUP)]                       # 目录页重复题号，无【回复】
    ps += [_para("0011", "问题2.关于B事项"),
           _para("001", ASK2_ASK),
           _para("000", "【回复】")]
    ps += [_para("000", t) for t in ASK2_REP]
    return "".join(ps)


def make(path):
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
           '<w:document %s><w:body>%s<w:sectPr/></w:body></w:document>' % (tg.WNS, body()))
    _pkt(path, doc)


def run(args):
    p = subprocess.run([sys.executable, SCRIPT] + args,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


class TestSplit(unittest.TestCase):

    def setUp(self):
        self._d = tempfile.TemporaryDirectory()
        self.docx = os.path.join(self._d.name, "回复.docx")
        make(self.docx)
        self.items = sq.split_questions(sq.load_paras(self.docx))
        self.by_no = {i["no"]: i for i in self.items}

    def tearDown(self):
        self._d.cleanup()

    def test_questions_dedup(self):
        self.assertEqual(len(self.items), 2, "目录页重复题号应被剔除")
        self.assertEqual([i["no"] for i in self.items], ["1", "2"])

    def test_last_group_wins(self):
        """背景组（1)(2)(3) 必须丢掉，取后面从 1 起的真子问组。"""
        subs = self.by_no["1"]["subs"]
        self.assertEqual(len(subs), 2, "应为 2 个真子问，而不是 3 个背景项或多组累加")
        self.assertIn("资金占用", subs[0][1])
        self.assertIn("影响金额", subs[1][1])

    def test_reply_sections(self):
        self.assertEqual(len(self.by_no["1"]["secs"]), 2)
        self.assertEqual(len(self.by_no["2"]["secs"]), 3)

    def test_unnumbered(self):
        subs = self.by_no["2"]["subs"]
        self.assertEqual(len(subs), 1)
        self.assertEqual(subs[0][0], "—", "无编号提问应给占位「—」")


class TestQtype(unittest.TestCase):

    def test_five_types(self):
        cases = [("量化分析影响金额", "量化型"),
                 ("说明上述差异的原因及合理性", "原因型"),
                 ("是否符合《企业会计准则》的规定", "合规型"),
                 ("是否存在资金被占用的情况", "是否型"),
                 ("补充说明发行人的客户结构", "说明型")]
        for text, want in cases:
            self.assertEqual(sq.qtype(text), want, text)

    def test_quant_before_yesno(self):
        """『量化分析…是否…』应判量化型（量化规则优先）。"""
        self.assertEqual(sq.qtype("请量化分析该处理是否恰当及影响金额"), "量化型")


class TestRender(unittest.TestCase):

    def setUp(self):
        self._d = tempfile.TemporaryDirectory()
        self.docx = os.path.join(self._d.name, "渲染.docx")
        make(self.docx)
        self.items = sq.split_questions(sq.load_paras(self.docx))
        self.md = sq.render(self.items, self.docx, 60)

    def tearDown(self):
        self._d.cleanup()

    def test_unnumbered_marked(self):
        self.assertIn("无编号子问", self.md)
        self.assertNotIn("问题 2（子问 1 ／ 回复小节 3）　⚠️", self.md,
                         "无编号题不得标『数量不等』")

    def test_headers(self):
        self.assertIn("## 问题 1（子问 2 ／ 回复小节 2）", self.md)
        self.assertIn("是否型", self.md)
        self.assertIn("量化型", self.md)
        self.assertIn("结论形态", self.md)
        self.assertIn("是否对位", self.md)


class TestCli(unittest.TestCase):

    def setUp(self):
        self._d = tempfile.TemporaryDirectory()
        self.docx = os.path.join(self._d.name, "cli.docx")
        make(self.docx)
        self.out = os.path.join(self._d.name, "对位表.md")

    def tearDown(self):
        self._d.cleanup()

    def test_writes_md(self):
        rc, log = run(["--input", self.docx, "--out", self.out])
        self.assertEqual(rc, 0, log)
        with open(self.out, encoding="utf-8") as fh:
            md = fh.read()
        self.assertIn("回复子问对位表", md)
        self.assertIn("| 题 | 标题 | 子问数 | 回复小节数 | 提示 |", md)

    def test_json(self):
        rc, out = run(["--input", self.docx, "--out", self.out, "--json"])
        self.assertEqual(rc, 0)
        i = out.find("[\n")
        self.assertGreaterEqual(i, 0)
        data = json.loads(out[i:])
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["subs"], 2)
        self.assertEqual(data[1]["secs"], 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)

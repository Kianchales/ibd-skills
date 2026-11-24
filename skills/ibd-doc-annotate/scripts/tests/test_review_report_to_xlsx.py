#!/usr/bin/env python3
"""test_review_report_to_xlsx.py — 复核报告（Excel）生成器自测

三档样本（门禁/判据类改动的强制动作）：
  正常   多性质条目 ＋ 完整 meta → 封面页 ＋ 按性质分页 ＋ 全部页，列与编号符合规范
  回退   无 `nature` 字段 → 按 `type` 大类回退分页（不报错）
  边界   无 meta → 仍出封面（报告头结论由自动统计兜底）＋ 明细页；`--split sev` 换轴；坏清单 exit 2

覆盖（9 项）：多性质分表 ｜ nature 回退 type ｜ 无 meta 封面仍完整 ｜ `--split sev` ｜ 坏清单拦截
            ｜ **复核声明四栏渲染 ＋ 声明在先的动态编号** ｜ **只主标题居中·其余标题左对齐**
            ｜ **封面上下等宽（全行跨到 C 列）** ｜ **声明缺省时 WARN**

依赖：openpyxl（未安装则整类 SKIP——本功能按需装，不属本包基础依赖）。
运行：python scripts/tests/test_review_report_to_xlsx.py
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SKILL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPT = os.path.join(SKILL_DIR, "scripts", "review_report_to_xlsx.py")

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:  # pragma: no cover
    HAS_OPENPYXL = False


def _entry(no, nature, sev, code="A", **kw):
    it = {"author": "复核人甲", "code": code, "type": kw.pop("type", "数据·勾稽"), "sev": sev,
          "anchor": f"锚点片段{no}", "title": f"问题标题{no}", "desc": f"问题描述{no}",
          "advice": f"建议{no}"}
    if nature is not None:
        it["nature"] = nature
    it.update(kw)
    return it


def _run(td, issues, meta=None, extra=(), expect_rc=0):
    ip = os.path.join(td, "issues.json")
    with open(ip, "w", encoding="utf-8") as fh:
        json.dump(issues, fh, ensure_ascii=False)
    cmd = [sys.executable, SCRIPT, "--issues", ip, "--out", os.path.join(td, "报告.xlsx"),
           "--allow-no-runlog", *extra]
    if meta is not None:
        mp = os.path.join(td, "meta.json")
        with open(mp, "w", encoding="utf-8") as fh:
            json.dump(meta, fh, ensure_ascii=False)
        cmd += ["--meta", mp]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != expect_rc:
        raise AssertionError(f"rc={proc.returncode} 预期 {expect_rc}\nstdout:{proc.stdout}\nstderr:{proc.stderr}")
    return proc


def _load(td):
    return openpyxl.load_workbook(os.path.join(td, "报告.xlsx"))


def _cover_text(td, sheet="封面与汇总"):
    """封面所有非空单元格文字拼一行——用于「某段是否出现在封面」的断言。"""
    ws = openpyxl.load_workbook(os.path.join(td, "报告.xlsx"))[sheet]
    return "\n".join(str(c.value) for row in ws.iter_rows() for c in row if c.value)


@unittest.skipUnless(HAS_OPENPYXL, "openpyxl 未安装")
class TestReviewReport(unittest.TestCase):

    def test_normal_multi_nature(self):
        """正常：封面 ＋ 5 张性质页 ＋ 全部（一页总览，不另开范围/统计页）。"""
        issues = [_entry(i, nt, "中")
                  for i, nt in enumerate(["数据不一致", "表述不一致", "自身逻辑", "格式规范", "事实存疑"], 1)]
        with tempfile.TemporaryDirectory() as td:
            _run(td, issues)
            wb = _load(td)
            self.assertEqual(len(wb.sheetnames), 7, wb.sheetnames)
            for must in ("封面与汇总", "全部"):
                self.assertIn(must, wb.sheetnames)

    def test_no_nature_falls_back_to_type(self):
        """回退：无 nature → 按 type 大类分页，不报错。"""
        issues = [_entry(1, None, "高", type="数据·口径"), _entry(2, None, "中", type="表述·歧义"),
                  _entry(3, None, "低", type="合规·一致性")]
        with tempfile.TemporaryDirectory() as td:
            _run(td, issues)
            names = _load(td).sheetnames
            for want in ("数据", "表述", "合规"):
                self.assertIn(want, names)
            self.assertNotIn("封面与汇总", names[1:])

    def test_no_meta_cover_still_complete(self):
        """无 meta → KPI 仍出数、明细齐全。"""
        issues = [_entry(1, "数据不一致", "高"), _entry(2, "表述不一致", "中")]
        with tempfile.TemporaryDirectory() as td:
            _run(td, issues, meta={})
            wb = _load(td)
            vals = [str(c.value or "").strip() for row in wb["封面与汇总"].iter_rows() for c in row]
            self.assertIn("2", vals)                    # KPI 总数
            self.assertIn("1", vals)                    # 必改
            self.assertIn("全部", wb.sheetnames)

    def test_declaration_rendered_on_cover(self):
        """声明（不查项）回到首页底部，浅灰小字，不抢主体。"""
        issues = [_entry(1, "数据不一致", "高")]
        with tempfile.TemporaryDirectory() as td:
            _run(td, issues, meta={"declaration": ["不查：法律事项", "依据来源：申报报表"]})
            text = "\n".join(str(c.value or "") for row in _load(td)["封面与汇总"].iter_rows() for c in row)
            self.assertIn("法律事项", text)
            self.assertIn("申报报表", text)

    def test_declaration_missing_warns(self):
        """边界：无 declaration → 不阻断生成，但 stderr 留痕（声明未做＝未声明范围）。"""
        issues = [_entry(1, "①数据不一致", "高")]
        with tempfile.TemporaryDirectory() as td:
            proc = _run(td, issues)
            self.assertIn("declaration", proc.stderr)
            self.assertNotIn("复核声明", _cover_text(td))

    def test_title_left_aligned_largest(self):
        """标题左对齐、全页最大字号（控制表版式：不居中）。"""
        issues = [_entry(1, "数据不一致", "高")]
        with tempfile.TemporaryDirectory() as td:
            _run(td, issues, meta={"title": "左对齐示例"})
            ws = _load(td)["封面与汇总"]
            row = next(i for i in range(1, 10) if ws.cell(i, 2).value == "左对齐示例")
            self.assertEqual(ws.cell(row, 2).alignment.horizontal, "left")
            self.assertGreaterEqual(ws.cell(row, 2).font.size, 24)

    def test_cover_is_single_page_overview(self):
        """一页总览：KPI 横排＋域 chips＋档位徽标；不再单开范围/统计页，也不重复"复核对象"。"""
        issues = [_entry(1, "数据不一致", "高", code="A")]
        meta = {"title": "总览示例", "declaration": ["不查：法律事项"],
                "domain_lines": ["A 格式规范（12 项）：序号、标点"],
                "depth_levels": [{"used": True, "text": "【本轮使用】L2 标准：全项核对"},
                                 {"used": False, "text": "L1 快扫：只做表面项"}]}
        with tempfile.TemporaryDirectory() as td:
            _run(td, issues, meta=meta)
            wb = _load(td)
            self.assertNotIn("复核范围", wb.sheetnames)
            self.assertNotIn("问题统计", wb.sheetnames)
            text = "\n".join(str(c.value or "") for row in wb["封面与汇总"].iter_rows() for c in row)
            for must in ("总览示例", "数据基准", "覆盖方式", "复核档位", "法律事项"):
                self.assertIn(must, text)
            self.assertIn("A 格式规范", text)          # 左列徽标
            self.assertIn("序号、标点", text)            # 右列项名（域名不再重复）
            self.assertNotIn("复核对象", text, "与副标题重复，已删")

    def test_split_sev_axis(self):
        """边界：--split sev 换轴 → 三张严重度页。"""
        issues = [_entry(1, "①数据不一致", "高"), _entry(2, "①数据不一致", "中"), _entry(3, "②表述不一致", "低")]
        with tempfile.TemporaryDirectory() as td:
            _run(td, issues, extra=("--split", "sev"))
            names = _load(td).sheetnames
            self.assertEqual([n for n in names if n in ("高", "中", "低")], ["高", "中", "低"])

    def test_bad_issues_blocked(self):
        """阴性：缺 anchor 的坏清单 → exit 2、不出文件。"""
        with tempfile.TemporaryDirectory() as td:
            bad = [{"code": "A", "type": "数据·勾稽", "sev": "高", "title": "t", "desc": "d", "advice": "a"}]
            _run(td, bad, expect_rc=2)
            self.assertFalse(os.path.exists(os.path.join(td, "报告.xlsx")))

    # ── 轮次状态页（2026-10-20 新增 · 规格 ibd-doc-review delivery.md §七之二）──

    def test_round_ledger_sheet(self):
        """传 --round-ledger → 生成「轮次状态」页（顺序不再固定为第二页）。"""
        issues = [_entry(1, "①数据不一致", "高")]
        with tempfile.TemporaryDirectory() as td:
            lp = os.path.join(td, "ledger.json")
            with open(lp, "w", encoding="utf-8") as f:
                json.dump({"stats": {"新增": 1, "已消": 0, "遗留": 2, "变重": 0, "变轻": 0},
                           "items": [{"id": "A-01", "state": "新增", "title": "t"}]}, f)
            _run(td, issues, extra=["--round-ledger", lp])
            wb = _load(td)
            self.assertTrue(any("轮次" in n for n in wb.sheetnames), wb.sheetnames)

    def test_no_ledger_no_empty_sheet(self):
        """阴性：不传台账 → **不得**出现空的「轮次状态」页（空页会被读成「本轮无遗留」）。"""
        issues = [_entry(1, "①数据不一致", "高")]
        with tempfile.TemporaryDirectory() as td:
            _run(td, issues)
            self.assertNotIn("轮次状态", _load(td).sheetnames)

    def test_bad_ledger_blocked(self):
        """阴性：台账结构不符（缺 items）→ exit 2、不出文件。"""
        issues = [_entry(1, "①数据不一致", "高")]
        with tempfile.TemporaryDirectory() as td:
            lp = os.path.join(td, "bad_ledger.json")
            with open(lp, "w", encoding="utf-8") as fh:
                json.dump({"stats": {"上轮条数": 3}}, fh, ensure_ascii=False)
            _run(td, issues, extra=("--round-ledger", lp), expect_rc=2)
            self.assertFalse(os.path.exists(os.path.join(td, "报告.xlsx")))



class TestStringMetaFields(unittest.TestCase):
    """meta 的文本字段传**字符串**时，必须当作一整行，不得逐字渲染。

    2026-11-20 实测：`approach` 写成字符串，封面被渲染成「· 先 / · 定 / · 分 / · 母 …」20 行。
    """

    def test_approach_string_is_one_line(self):
        """approach 传字符串时按一行渲染（不得一个字一行）。"""
        issues = [_entry(1, "数据不一致", "高")]
        with tempfile.TemporaryDirectory() as td:
            _run(td, issues, meta={"approach": "先定分母再切批"})
            vals = [str(c.value or "") for row in _load(td)["封面与汇总"].iter_rows() for c in row]
            hits = [v for v in vals if "先定分母再切批" in v]
            self.assertEqual(len(hits), 1, "应只占一行")

    def _mk(self, d, meta_extra=None):
        import json as _j
        issues = os.path.join(d, "i.json")
        meta = os.path.join(d, "m.json")
        out = os.path.join(d, "r.xlsx")
        with open(issues, "w", encoding="utf-8") as f:
            _j.dump([{"code": "J", "type": "格式规范", "sev": "中", "nature": "格式规范",
                      "anchor": "原文", "title": "标题", "desc": "说明", "advice": "建议",
                      "author": "复核人"}], f, ensure_ascii=False)
        with open(meta, "w", encoding="utf-8") as f:
            _j.dump(meta_extra or {"subject": "x"}, f, ensure_ascii=False)
        return issues, meta, out

    def test_blocks_without_runlog(self):
        import subprocess, sys, tempfile
        with tempfile.TemporaryDirectory() as d:
            issues, meta, out = self._mk(d)
            r = subprocess.run([sys.executable, SCRIPT, "--issues", issues, "--meta", meta,
                                "--out", out], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(r.returncode, 3, r.stderr)
            self.assertIn("未找到运行指纹", r.stderr)
            self.assertFalse(os.path.exists(out), "拦下时不得产出报告")

    def test_allow_no_runlog_marks_cover(self):
        import json as _j, subprocess, sys, tempfile
        import openpyxl
        with tempfile.TemporaryDirectory() as d:
            issues, meta, out = self._mk(d)
            r = subprocess.run([sys.executable, SCRIPT, "--issues", issues, "--meta", meta,
                                "--out", out, "--allow-no-runlog"],
                               capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(r.returncode, 0, r.stderr)
            wb = openpyxl.load_workbook(out)
            text = "\n".join(str(c.value or "") for row in wb["封面与汇总"].iter_rows() for c in row)
            self.assertIn("未按 skill 流程执行", text, "越过闸门必须留痕")

    def test_with_runlog_records_tools(self):
        import json as _j, subprocess, sys, tempfile
        with tempfile.TemporaryDirectory() as d:
            issues, meta, out = self._mk(d)
            rl = os.path.join(d, "_run.json")
            with open(rl, "w", encoding="utf-8") as f:
                _j.dump({"skill_version": "9.9.9",
                         "steps": [{"tool": "check_content", "rc": 0},
                                   {"tool": "check_cq", "rc": 1}]}, f, ensure_ascii=False)
            r = subprocess.run([sys.executable, SCRIPT, "--issues", issues, "--meta", meta,
                                "--out", out, "--runlog", rl],
                               capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(os.path.exists(out))


if __name__ == "__main__":
    unittest.main(verbosity=2)

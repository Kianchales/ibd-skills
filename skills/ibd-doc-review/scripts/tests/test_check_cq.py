#!/usr/bin/env python3
"""
test_check_cq.py — check_cq.py 自测（合成工作簿，不依赖真实报表）

覆盖：
  解析
   1. 中文表头「2026年1-6月／2025年度」与 Excel 日期序列号两种写法都能认出期间列
   2. 资产负债表分两张表（正表 + 续）时，负债与权益行从续页取到
  勾稽
   3. 五项勾稽自洽 → 退出码 0
   4. 故意造 1,000.00 不平 → 退出码 1，且报告出该期间
   5. ⑥ 式：差额 ＝ 受限 ＋ 应计利息 时判平；不等时判不平并给出差额
  可配
   6. `--map` 覆盖行名别名（自家报表行名特殊时可用）
   7. 要素缺行 → 退出码 2（而不是静默给个"全平"）
  输出
   8. `--json` 字段齐备（periods／bad／detail／rows）
   9. `--out` 落盘 markdown

运行：python scripts/tests/test_check_cq.py
"""
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

import openpyxl

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


SKILL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPT = os.path.join(SKILL_DIR, "scripts", "check_cq.py")

P1, P2 = "2026年1-6月", "2025年度"


def build(path, bs_delta=0.0, cash=None):
    """造一个最小可勾稽的工作簿；bs_delta 用于故意制造资产负债不平。"""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    def sheet(name, rows, hdr=(P1, P2)):
        ws = wb.create_sheet(name)
        ws.append([name])
        ws.append(["编制单位：测试公司"])
        ws.append(["项        目", "附注", hdr[0], hdr[1]])
        for r in rows:
            ws.append(r)
        return ws

    assets = 1000.0
    liab, equ = 400.0, 600.0
    sheet("合并资产负债表（续）", [
        ["负债合计", "", liab, liab],
        ["归属于母公司股东权益合计", "", equ - 10.0, equ - 10.0],
        ["少数股东权益", "", 10.0, 10.0],
        ["股东权益合计", "", equ, equ],
        ["负债和股东权益总计", "", assets + bs_delta, assets + bs_delta],
    ])
    sheet("合并资产负债表", [
        ["货币资金", "（一）", cash if cash is not None else 200.0, cash if cash is not None else 200.0],
        ["资产总计", "", assets + bs_delta, assets + bs_delta],
    ], hdr=(46203, 46022))          # 序列号写法
    sheet("合并利润表", [
        ["三、利润总额（亏损总额以“－”号填列）", "", 150.0, 150.0],
        ["减：所得税费用", "", 50.0, 50.0],
        ["四、净利润（净亏损以“－”号填列）", "", 100.0, 100.0],
        ["1.归属于母公司股东的净利润（净亏损以“－”号填列）", "", 90.0, 90.0],
        ["2.少数股东损益（净亏损以“－”号填列）", "", 10.0, 10.0],
    ])
    sheet("合并现金流量表", [
        ["五、现金及现金等价物净增加额", "", 0.0, 0.0],
        ["加：期初现金及现金等价物余额", "", 200.0, 200.0],
        ["六、期末现金及现金等价物余额", "", 200.0, 200.0],
    ])
    wb.save(path)


def _load_mod():
    spec = importlib.util.spec_from_file_location("cq_mod", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["cq_mod"] = m
    spec.loader.exec_module(m)
    return m


_CQ = None


def run(args):
    """进程内调用（0.58.0 提速）：原来每条用例起一个解释器，7 条就多花 4 秒以上。

    仍保留 `test_cli_smoke` 起子进程跑一次，确保 argparse 与退出码没被改坏。
    """
    global _CQ
    if _CQ is None:
        _CQ = _load_mod()
    out = io.StringIO()
    code = 0
    old_argv = sys.argv
    sys.argv = ["check_cq.py"] + args
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            _CQ.main()
    except SystemExit as e:
        code = int(e.code or 0)
    finally:
        sys.argv = old_argv
    return code, out.getvalue()


class TestCheckCQ(unittest.TestCase):

    def setUp(self):
        self._d = tempfile.TemporaryDirectory()
        self.xlsx = os.path.join(self._d.name, "报表.xlsx")

    def tearDown(self):
        self._d.cleanup()

    def test_balanced_exit0(self):
        build(self.xlsx)
        rc, out = run(["--xlsx", self.xlsx])
        self.assertEqual(rc, 0, out)
        self.assertIn("全平", out)
        self.assertIn("2026-06-30", out, "序列号表头应解析成日期")

    def test_unbalanced_detected(self):
        build(self.xlsx, bs_delta=1000.0)
        rc, out = run(["--xlsx", self.xlsx])
        self.assertEqual(rc, 1)
        self.assertIn("1,000.00", out)

    def test_cash_gap_vs_restricted(self):
        # 货币资金 260，期末现金等价物 200 → 差额 60 = 受限 50 + 应计利息 10
        build(self.xlsx, cash=260.0)
        rc, out = run(["--xlsx", self.xlsx, "--restr", "50,50", "--accrued", "10,10"])
        self.assertEqual(rc, 0, out)
        self.assertIn("✅", out)

        # 受限只给 40 → 差 10，应判不平
        rc2, out2 = run(["--xlsx", self.xlsx, "--restr", "40,40", "--accrued", "10,10"])
        self.assertEqual(rc2, 1)
        self.assertIn("10.00", out2)

    def test_map_override(self):
        build(self.xlsx)
        # 把「资产总计」改名，默认别名找不到 → 需 --map 指定
        wb = openpyxl.load_workbook(self.xlsx)
        ws = wb["合并资产负债表"]
        for row in ws.iter_rows(min_row=4):
            if str(row[0].value or "").startswith("资产总计"):
                row[0].value = "总资产（特殊行名）"
        wb.save(self.xlsx)
        rc, out = run(["--xlsx", self.xlsx])
        self.assertEqual(rc, 2, "缺行应退出码 2，而非静默通过")

        mp = os.path.join(self._d.name, "map.json")
        with open(mp, "w", encoding="utf-8") as f:
            json.dump({"TOTAL_ASSETS": ["总资产（特殊行名）"]}, f, ensure_ascii=False)
        rc2, out2 = run(["--xlsx", self.xlsx, "--map", mp])
        self.assertEqual(rc2, 0, out2)

    def test_missing_element_exit2(self):
        build(self.xlsx)
        wb = openpyxl.load_workbook(self.xlsx)
        ws = wb["合并利润表"]
        for row in ws.iter_rows(min_row=4):
            if "少数股东损益" in str(row[0].value or ""):
                row[0].value = "其他项目"
        wb.save(self.xlsx)
        rc, out = run(["--xlsx", self.xlsx])
        self.assertEqual(rc, 2)
        self.assertIn("NI_MINORITY", out)

    def test_parent_scope_skips_minority(self):
        """母公司口径无少数股东概念：②③ 不适用，不得因此报"缺行"。"""
        wb = openpyxl.Workbook()
        wb.remove(wb.active)
        for name, rows in (
            ("母公司资产负债表（续）", [["负债合计", "", 400.0, 400.0],
                                        ["所有者权益合计", "", 600.0, 600.0],
                                        ["负债和所有者权益总计", "", 1000.0, 1000.0]]),
            ("母公司资产负债表", [["货币资金", "", 200.0, 200.0], ["资产总计", "", 1000.0, 1000.0]]),
            ("母公司利润表", [["三、利润总额（亏损总额以“－”号填列）", "", 150.0, 150.0],
                              ["减：所得税费用", "", 50.0, 50.0],
                              ["四、净利润（净亏损以“－”号填列）", "", 100.0, 100.0]]),
            ("母公司现金流量表", [["五、现金及现金等价物净增加额", "", 0.0, 0.0],
                                  ["加：期初现金及现金等价物余额", "", 200.0, 200.0],
                                  ["六、期末现金及现金等价物余额", "", 200.0, 200.0]]),
        ):
            ws = wb.create_sheet(name)
            ws.append([name]); ws.append(["编制单位：测试"])
            ws.append(["项        目", "附注", P1, P2])
            for r in rows:
                ws.append(r)
        wb.save(self.xlsx)
        rc, out = run(["--xlsx", self.xlsx, "--scope", "母公司"])
        self.assertEqual(rc, 0, out)
        self.assertIn("3 项", out, "母公司口径应只有 3 项勾稽")

    def test_json_and_out(self):
        build(self.xlsx)
        md = os.path.join(self._d.name, "r.md")
        rc, out = run(["--xlsx", self.xlsx, "--out", md, "--json"])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        for k in ("periods", "bad", "detail", "rows"):
            self.assertIn(k, data)
        self.assertEqual(data["bad"], 0)
        self.assertTrue(os.path.exists(md))
        with open(md, encoding="utf-8") as f:
            self.assertIn("C-Q 机械勾稽", f.read())



# --- 测试分层（见 _tier.py）：默认只跑快测，全量需 REVIEW_TESTS=all
from _tier import slow_all  # noqa: E402

slow_all(globals())

class TestCliSmoke(unittest.TestCase):
    """CLI 冒烟：确保命令行入口（argparse/退出码）仍然可用。"""

    def test_cli_runs(self):
        with tempfile.TemporaryDirectory() as d:
            x = os.path.join(d, "报表.xlsx")
            build(x)
            p = subprocess.run([sys.executable, SCRIPT, "--xlsx", x, "--json"],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertIn('"periods"', p.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)

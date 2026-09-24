#!/usr/bin/env python3
"""check_data.py · calc 组回归用例（8 例）。运行：python test_check_data.py

覆盖三个已固化判据：
  ① **勾稽容差 ＝ 0.01**（体系级约定 `docs/CONVENTIONS.md` 判据集 / R-0038，2026-09-24 用户裁定）
     —— 0.01 级差放行、0.02 级差报出；**不设相对容差**（大额合计的小比例差也须报出）。
  ② **n 倍允差**（同批裁定「可以加 n 倍允差」）—— 「n 项求和 vs 合计」除单值容差外，
     另吸收各行按列示位四舍五入的累积漂移（上限 n × TOL/2）；**有界**，超出仍报 HIGH。
  ③ **占比列求和不含合计行**（I-0107 修复护栏，2026-09-24）—— 合计行自身即 100%，
     若被计入则占比合计恒 ≈200%，任何带「占比列＋合计行」的表都会假阳性。

退出码：0 ＝ 全部符合预期；1 ＝ 有用例不符。
"""
import json
import os
import subprocess
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "check_data.py")


def table(rows, col1="金额（万元）"):
    """rows = [(名称, 金额, 占比串)]，最后一行约定为合计行。"""
    out = [f"| 项目 | {col1} | 占比 |", "| --- | --- | --- |"]
    out += [f"| {n} | {a} | {p} |" for n, a, p in rows]
    return "\n".join(out) + "\n"


N = 3
EQ = [("甲", "100.00", "33.33%"), ("乙", "100.00", "33.33%"), ("丙", "100.00", "33.34%")]


def dist(n, pct_each, total_pct, amt_each="10.00", total_amt=None):
    """n 行等值分项 + 合计行。total_amt 缺省 ＝ 分项名义之和（不制造金额差）。"""
    rows = [(f"客户{i}", amt_each, pct_each) for i in range(1, n + 1)]
    if total_amt is None:
        total_amt = f"{float(amt_each) * n:.2f}"
    rows.append(("合计", total_amt, total_pct))
    return rows


CASES = [
    # (名称, 表行, 期望 HIGH 数, 期望说明)
    ("合规表（行和=合计、占比=100.00%）", EQ + [("合计", "300.00", "100.00%")], 0,
     "0.01 内且占比正好 100 ⇒ 0；①③ 护栏，改前必假阳性"),
    ("0.01 级差（金额与占比各 +0.01）", [("甲", "100.00", "33.33%"), ("乙", "100.00", "33.33%"),
                                 ("丙", "100.00", "33.35%"), ("合计", "300.01", "100.01%")], 0,
     "1 个列示位 ⇒ 放行（含浮点保护，33.33+33.33+33.35 不误报）"),
    ("0.02 级差（金额与占比各 +0.02）", [("甲", "100.00", "33.33%"), ("乙", "100.00", "33.33%"),
                                 ("丙", "100.00", "33.36%"), ("合计", "300.02", "100.02%")], 2,
     "超 3 项允差 0.015 ⇒ 金额列与占比列各报 1"),
    ("大额合计的小比例差（100 万级差 500 元、占比 99.50%）",
     [("甲", "250000.00", "24.90%"), ("乙", "250000.00", "24.90%"), ("丙", "250000.00", "24.90%"),
      ("丁", "250000.00", "24.80%"), ("合计", "1000500.00", "99.50%")], 2,
     "不设相对容差 ⇒ 差 500 元照报（旧 0.1% 相对带会吞掉）"),
    ("7 行 ×14.29% 合计写 100.03%（合计≠行和）", dist(7, "14.29%", "100.03%"), 0,
     "7 项允差 0.035 ≥ 差 0.02 ⇒ 累积舍入放行"),
    ("7 行 ×14.29% 合计强制 100.00%（实务常态）", dist(7, "14.29%", "100.00%"), 0,
     "差 0.01 ⇒ 放行"),
    ("30 行 ×3.33% 合计强制 100.00%（多项累积）", dist(30, "3.33%", "100.00%"), 0,
     "差 0.10 ≤ 30 项允差 0.15 ⇒ 放行（本批 n 倍允差的目标场景）"),
    ("30 行 ×3.32% 合计强制 100.00%（越界）", dist(30, "3.32%", "100.00%"), 2,
     "差 0.40 > 0.15 ⇒ 允差有界、仍报 HIGH"),
]


def run(rows):
    content = "# 回归用例\n\n" + table(rows)
    d = tempfile.mkdtemp()
    src = os.path.join(d, "case.md")
    with open(src, "w", encoding="utf-8") as fh:
        fh.write(content)
    r = subprocess.run([sys.executable, SCRIPT, "--input", src, "--checks", "calc",
                        "--output", os.path.join(d, "out.md"), "--json"],
                       capture_output=True, text=True)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])["error"]
    except Exception:
        print(r.stdout[-2000:], r.stderr[-2000:])
        raise


def main():
    failed = 0
    for name, rows, expect, why in CASES:
        got = run(rows)
        ok = got == expect
        print(("PASS" if ok else "FAIL"), f"{name}：期望 {expect} / 实得 {got}", f"（{why}）")
        if not ok:
            failed += 1
    print(f"---\n{len(CASES) - failed}/{len(CASES)} 通过")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()

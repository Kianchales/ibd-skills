#!/usr/bin/env python3
"""check_gates.py 自测用例（10 例）。运行：python test_check_gates.py"""
import os
import subprocess
import sys
import tempfile

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "check_gates.py")
REFS = os.path.join(os.path.dirname(__file__), "..", "..", "references")

CASES = [
    # (名称, 正文, 期望: 是否存在 HIGH)
    ("绝对化无来源→HIGH", "公司产品处于行业领先地位。\n", True),
    ("绝对化带来源→仅WARN", "据某某咨询报告（来源：XX研究院），公司市占率行业第一。\n", False),
    ("AI痕迹词→HIGH", "综上所述，公司发展前景广阔。\n", True),
    ("干净文本→全过", "2024 年营业收入 11.20 亿元（来源：发行人 2024 年度审计报告）。\n", False),
    ("正常序号不误报", "1. 公司概况\n1.1 主营业务\n详见第 3 章及表 2-1。\n", False),
]


def run(content):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(content)
        path = f.name
    r = subprocess.run([sys.executable, SCRIPT, path, "--wordlist-dir", REFS],
                       capture_output=True, text=True)
    os.unlink(path)
    return r.returncode, r.stdout


def main():
    failed = 0
    for name, content, expect_high in CASES:
        code, out = run(content)
        got_high = (code == 1)
        ok = (got_high == expect_high)
        print(("PASS" if ok else "FAIL"), name, f"(exit={code})")
        if not ok:
            failed += 1
            print(out)
    print(f"---\n{len(CASES) - failed}/{len(CASES)} 通过")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()

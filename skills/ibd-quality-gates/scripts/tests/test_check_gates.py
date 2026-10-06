#!/usr/bin/env python3
"""check_gates.py 自测用例（扫描 5 例 ＋ 输出契约 4 例）。运行：python test_check_gates.py"""
import json
import os
import subprocess
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

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


def run_raw(content, extra=None):
    """返回 (code, stdout)。"""
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(content)
        path = f.name
    try:
        cmd = [sys.executable, SCRIPT, path, "--wordlist-dir", REFS] + list(extra or [])
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        return r.returncode, r.stdout
    finally:
        os.unlink(path)


def run(content):
    return run_raw(content)


def output_contract_cases(tmp):
    """输出契约（P10 落盘 ＋ §4.4 --json）：返回 [(名称, 是否通过, 失败详情)]。"""
    out = []

    # 1) --out：报告全文落盘、stdout 回路径、文件里能读到命中明细
    rp = os.path.join(tmp, "g.log")
    code, text = run_raw("公司产品处于行业领先地位。\n", ["--out", rp])
    body = ""
    if os.path.exists(rp):
        with open(rp, encoding="utf-8") as f:
            body = f.read()
    out.append(("--out 报告落盘并回路径",
                rp in text and "[结果]" in text and "扫描报告" in body and body.rstrip().endswith(
                    "请人工复核。"),
                f"rc={code}\n{text}\n--- file ---\n{body}"))

    # 2) --json：单行结构化、含 detail_log、无人类报告混入
    rp2 = os.path.join(tmp, "g2.log")
    code2, text2 = run_raw("公司产品处于行业领先地位。\n", ["--json", "--out", rp2])
    lines = [l for l in text2.split("\n") if l.strip()]
    ok2 = False
    detail = f"rc={code2}\n{text2}"
    if len(lines) == 1:
        j = json.loads(lines[0])
        ok2 = (j.get("tool") == "check_gates" and j.get("verdict") == "FAIL"
               and j.get("detail_log") == rp2 and os.path.exists(rp2))
        detail = json.dumps(j, ensure_ascii=False)[:300]
    out.append(("--json 单行契约 ＋ detail_log 指针", ok2, detail))

    # 3) --json 干净文本 → PASS/0
    code3, text3 = run_raw("2024 年营业收入 11.20 亿元（来源：发行人审计报告）。\n",
                           ["--json", "--out", os.path.join(tmp, "g3.log")])
    try:
        j3 = json.loads([l for l in text3.split("\n") if l.strip()][0])
        ok3 = j3["verdict"] == "PASS" and j3["error"] == 0 and code3 == 0
    except Exception as e:  # noqa: BLE001
        ok3, j3 = False, {"err": str(e)}
    out.append(("--json 干净文本 → PASS/0", ok3, f"rc={code3} {j3}"))

    # 4) 默认文本输出**逐字保留**旧格式（不因落盘而改版）
    code4, text4 = run_raw("公司产品处于行业领先地位。\n")
    ok4 = ("=== ibd-quality-gates 扫描报告：" in text4
           and "提醒：HIGH=须改；WARN=带来源标注，人工确认；" in text4)
    out.append(("默认文本输出格式不变（仅追加路径行）", ok4, text4))
    return out


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

    with tempfile.TemporaryDirectory() as tmp:
        for name, ok, detail in output_contract_cases(tmp):
            print(("PASS" if ok else "FAIL"), name)
            if not ok:
                failed += 1
                print(detail)

    total = len(CASES) + 4
    print(f"---\n{total - failed}/{total} 通过")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()

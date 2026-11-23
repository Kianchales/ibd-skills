#!/usr/bin/env python3
"""测试入口：默认快测，`--all` 跑全量。**跳过了多少必须看得见。**

为什么要有这个包装
------------------
直接用 `python -m unittest discover` 也能分层（`REVIEW_TESTS=all` 切全量），
但快测的输出只有一行 `OK (skipped=131)`——**131 例跳过容易被当成"全绿"**。
本入口在跑之前先说明本次跑的是哪一档、跳了多少例、为什么可以跳过，
让"没跑"始终是可见状态（与 `deliver_gate` 的 SKIP 点名同一原则）。

用法
----
    python scripts/tests/run_tests.py          # 快测（约 5 秒，日常迭代）
    python scripts/tests/run_tests.py --all    # 全量（约 70 秒，提交前/升版前）
    python scripts/tests/run_tests.py --list   # 只看分层清单
"""
import argparse
import glob
import os
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
SLOW_MODULES = [
    "test_check_annotations", "test_check_cq", "test_check_revisions", "test_check_styles",
    "test_deliver_gate", "test_doc_flags", "test_extract_final_text", "test_validate_schema",
    "test_gate_consistency", "test_new_workspace", "test_round_diff_selftest",
    "test_docxio_parity",
]


def main():
    ap = argparse.ArgumentParser(description="跑测试（默认快测）")
    ap.add_argument("--all", action="store_true", help="跑全量（含慢测）")
    ap.add_argument("--list", action="store_true", help="只打印分层清单")
    a = ap.parse_args()

    total_files = len(glob.glob(os.path.join(HERE, "test_*.py")))
    fast_files = total_files - len([m for m in SLOW_MODULES
                                    if os.path.exists(os.path.join(HERE, m + ".py"))])
    print("=" * 64)
    if a.all:
        print("档位：全量（%d 个测试文件，含子进程端到端）" % total_files)
    else:
        print("档位：快测（%d 个文件，不起子进程）" % fast_files)
        print("已跳过 %d 个慢测模块：%s" % (len(SLOW_MODULES), "、".join(SLOW_MODULES)))
        print("提交前/升版前请跑：python scripts/tests/run_tests.py --all")
    print("=" * 64)

    if a.list:
        for m in SLOW_MODULES:
            print("  慢：" + m)
        for f in sorted(glob.glob(os.path.join(HERE, "test_*.py"))):
            if os.path.splitext(os.path.basename(f))[0] not in SLOW_MODULES:
                print("  快：" + os.path.basename(f))
        return 0

    env = dict(os.environ)
    if a.all:
        env["REVIEW_TESTS"] = "all"
    else:
        env.pop("REVIEW_TESTS", None)
    p = subprocess.run([sys.executable, "-m", "unittest", "discover",
                        "-s", HERE, "-p", "test_*.py"], env=env)
    return p.returncode


if __name__ == "__main__":
    sys.exit(main())

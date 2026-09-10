# -*- coding: utf-8 -*-
"""索引体系一键刷新：按序调用 parse_titles → gen_index → gen_toc → gen_entry。
任一环节失败即停止（保证索引/目录/入口三者一致，不会半新半旧）。

用法：
    python refresh_index.py [--methods-root <库根目录>] [--version <入口版本号>]

参数：
    --methods-root  方法论库根目录（默认 $METHODS_ROOT，或脚本上级目录）
    --version       入口版本号（透传给 gen_entry；默认读取现有入口 version 保持不变）

说明：
    - 本脚本替代「蒸馏大脚本的 --refresh-index 分支」——沉淀新条目后必跑（行号漂移会污染定向读取）
    - 四件套各自可独立运行（定位：parse=解析条目 / gen_index=调用索引 / gen_toc=条目标题目录 / gen_entry=路由入口）
"""
import argparse, os, subprocess, sys
from pathlib import Path

_ap = argparse.ArgumentParser(description="索引体系一键刷新（四件套编排）")
_ap.add_argument("--methods-root", default=os.environ.get("METHODS_ROOT", ""),
                 help="方法论库根目录（默认 $METHODS_ROOT，或脚本上级目录）")
_ap.add_argument("--version", default=None, help="入口版本号（透传 gen_entry）")
_args, _ = _ap.parse_known_args()

_HERE = Path(__file__).resolve().parent
_ROOT = Path(_args.methods_root) if _args.methods_root else _HERE.parent

STEPS = [
    ("parse_titles.py", "解析条目 → parsed_titles.txt"),
    ("gen_index.py", "生成 方法论调用索引.md"),
    ("gen_toc.py", "生成 方法论_条目标题目录.md"),
    ("gen_entry.py", "重写 入口（路由表 + 摘要保留）"),
]


def run_step(script, desc):
    path = _HERE / script
    if not path.exists():
        print("✗ 缺少脚本: %s（%s）" % (script, desc))
        return False
    cmd = [sys.executable, str(path), "--methods-root", str(_ROOT)]
    if script == "gen_entry.py" and _args.version:
        cmd += ["--version", _args.version]
    r = subprocess.run(cmd, capture_output=True, text=True)
    tail = (r.stdout.strip().splitlines() or [""])[-1]
    if r.returncode != 0:
        print("✗ %s 失败: %s" % (script, (r.stderr or tail)[:200]))
        return False
    print("✓ %s — %s" % (script, tail))
    return True


def main():
    print("=== 索引体系刷新（库根: %s）===" % _ROOT)
    for script, desc in STEPS:
        if not run_step(script, desc):
            print("!! 中断：后续步骤未执行（索引/目录/入口可能不一致，请修复后重跑）")
            return 1
    print("=== 全部完成：索引 / 条目标题目录 / 路由入口 已同步 ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

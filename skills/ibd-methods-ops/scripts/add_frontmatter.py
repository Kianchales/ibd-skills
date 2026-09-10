# -*- coding: utf-8 -*-
"""
A 档：方法论全库 frontmatter 补齐（纯增量，零内容改动）
2026-08-31 格式统一治理 · A 档

规则：
- 只处理 methods/ 根目录 *.md；archive/_backup 不递归
- 跳过名单（索引/自动生成/README）：不注入 frontmatter
- 已有 frontmatter（首行 ---）的文件跳过（幂等）
- 字段：type / domain 或 case 或 industry_class / version(仅域文件与入口) / updated
- updated 取 --updated 参数（默认执行日）

用法：
  python add_frontmatter.py --dry-run    # 打印计划不写盘
  python add_frontmatter.py              # 执行
"""
import io
import os
import re
import sys

import argparse
from pathlib import Path

_ap = argparse.ArgumentParser(description="方法论全库 frontmatter 补齐（A 档）")
_ap.add_argument("--methods-root", default=os.environ.get("METHODS_ROOT", ""),
                 help="方法论库根目录（默认 $METHODS_ROOT，或脚本上级目录）")
_ap.add_argument("--updated", default=None, help="写入 frontmatter 的 updated 日期（默认执行日）")
_args, _ = _ap.parse_known_args()
_ROOT = Path(_args.methods_root) if _args.methods_root else Path(__file__).resolve().parents[1]
_UPDATED_DEFAULT = _args.updated or __import__("datetime").date.today().strftime("%%Y-%%m-%%d")
UPDATED = _UPDATED_DEFAULT
METHODS = str(_ROOT / "methods")

SKIP = {
    "README.md",
    "方法论_条目标题目录.md",
    "方法论调用索引.md",
    "方法论调用索引_备份_20260831.md",
    "编号登记表.md",
    "行业方法论_合并映射.md",
}

V36_FILES = {
    "通用方法论_写作域.md": "写作域",
    "通用方法论_财务域.md": "财务域",
    "通用方法论_法律域.md": "法律域",
    "通用方法论_行业域.md": "行业域",
    "投行语言专项_W系列.md": "投行语言-W系列",
    "通用方法论_最终版.md": "通用方法论（路由入口）",
}

def build_fm(fn):
    """根据文件名构造 frontmatter 行列表（不含 --- 定界符）。返回 None 表示跳过。"""
    if fn in SKIP:
        return None
    if fn in V36_FILES:
        return [
            "type: 通用方法论" if not fn.startswith("通用方法论_最终版") else "type: 路由入口",
            "domain: " + ("通用方法论" if fn.startswith("通用方法论_最终版") else V36_FILES[fn]),
            "version: v36",
            "updated: " + UPDATED,
        ]
    m = re.match(r"^通用方法论_投行知识与写作范式_(.+)\.md$", fn)
    if m:
        return ["type: 单案写作范式", "case: " + m.group(1), "updated: " + UPDATED]
    if fn == "通用方法论_投行知识与写作范式.md":
        return ["type: 写作范式", "scope: 基础范式（历史稳定入口）", "updated: " + UPDATED]
    m = re.match(r"^行业方法论_(.+)\.md$", fn)
    if m:
        return ["type: 行业方法论", "industry_class: " + m.group(1), "updated: " + UPDATED]
    m = re.match(r"^投行语言写作范式(?:专项)?_(.+?)(?:_W.*)?\.md$", fn)
    if m:
        return ["type: 投行语言专项", "case: " + m.group(1), "updated: " + UPDATED]
    return None  # 未识别类型，跳过并告警

def main():
    dry = "--dry-run" in sys.argv
    files = sorted(f for f in os.listdir(METHODS) if f.endswith(".md"))
    plan = []
    warn = []
    for fn in files:
        fields = build_fm(fn)
        if fields is None:
            continue
        path = os.path.join(METHODS, fn)
        with io.open(path, encoding="utf-8") as f:
            head = f.read(4)
        if head.startswith("---"):
            warn.append("SKIP(已有frontmatter): " + fn)
            continue
        plan.append((fn, fields))
    print(f"=== 计划注入 {len(plan)} 个文件 ===")
    for fn, fields in plan:
        print(f"  [{fn}] " + " | ".join(fields))
    if warn:
        print("=== 跳过 ===")
        for w in warn:
            print("  " + w)
    if dry:
        print("\n[dry-run] 未写盘。执行请去掉 --dry-run")
        return
    # 执行：头部插入 frontmatter（--- 定界 + 空行）
    for fn, fields in plan:
        path = os.path.join(METHODS, fn)
        with io.open(path, encoding="utf-8") as f:
            content = f.read()
        block = "---\n" + "\n".join(fields) + "\n---\n\n"
        with io.open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(block + content)
        print(f"  WRITTEN [{fn}] +{len(fields)+3} 行")
    print(f"\n完成：注入 {len(plan)} 个文件")

if __name__ == "__main__":
    main()

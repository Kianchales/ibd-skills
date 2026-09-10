# -*- coding: utf-8 -*-
"""
案号 4 位化迁移（C01-C41 -> C0001-C0041），M1-M4 执行脚本。

规则（dry-run v2 核验后定稿，见 tasks/20260906_S4产出格式统一规范与历史遗留登记.md §5.1）：
  Tier 1  [FILW]-C{1,2}-(?=-)   案号 token（标题+正文+中文类），M1/M2/M3/M4 全域
  Tier 2  | C{1,2} | 表行        仅限 D 组对照/登记表（第一列=案号）；
                                 行业方法论/单份细分版的 | C34 | 为证监会行业分类码，绝不动
  Tier 3  C{1,2}-C{1,2} 区间     仅限 D 组 3 文件正文（批次说明）
免疫（天然不匹配）：
  - 已 4 位案号 C0041（\\d{1,2} 后必须紧跟 - 或 |，4 位首两位 00 无法匹配）
  - 国标码 C3940/C3985（后无 -/| 分隔符）；字母码 F-JH-01（无 C）
默认 dry preview（只打印统计）；--apply 才写文件。每文件替换前快照行级 diff 记数。
"""
import glob
import os
import re
import sys
from collections import OrderedDict

import argparse

_ap = argparse.ArgumentParser(description="案号位宽迁移（如 2 位 → 4 位）执行器")
_ap.add_argument("--methods-root", default=os.environ.get("METHODS_ROOT", ""),
                 help="方法论库根目录（默认 $METHODS_ROOT，或脚本上级目录）")
_ap.add_argument("--apply", action="store_true", help="正式写盘（默认只预览统计）")
_args, _ = _ap.parse_known_args()
ROOT = _args.methods_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T1 = re.compile(r"([FILW]-)C(\d{1,2})(?=-)")
T2 = re.compile(r"(\|\s*)C(\d{1,2})(\s*\|)")
T3 = re.compile(r"\bC(\d{1,2})-C(\d{1,2})\b")


def pad(m):
    return f"{m.group(1)}C{int(m.group(2)):04d}"


def pad2(m):
    return f"{m.group(1)}C{int(m.group(2)):04d}{m.group(3)}"


def pad3(m):
    return f"C{int(m.group(1)):04d}-C{int(m.group(2)):04d}"


def build_groups():
    g = OrderedDict()
    g["A"] = sorted(glob.glob(os.path.join(ROOT, "methods", "通用方法论_投行知识与写作范式_*.md")))
    g["B"] = [os.path.join(ROOT, "methods", f) for f in
              ["通用方法论_最终版.md", "通用方法论_财务域.md", "通用方法论_法律域.md",
               "通用方法论_行业域.md", "通用方法论_写作域.md", "投行语言专项_W系列.md"]
              if os.path.exists(os.path.join(ROOT, "methods", f))]
    g["C"] = sorted(glob.glob(os.path.join(ROOT, "methods", "行业方法论_*.md"))) + \
        sorted(glob.glob(os.path.join(ROOT, "methods", "行业方法论_单份细分版", "*.md")))
    g["D"] = [os.path.join(ROOT, "tasks", f) for f in
              ["单案索引对照表.md", "案号分配登记.md",
               "案号分配登记.md"] if os.path.exists(os.path.join(ROOT, "tasks", f))]
    return g


def migrate_file(path, group):
    """返回 (t1, t2, t3) 替换数；group C 只跑 Tier1，D 跑全部。"""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    n1 = len(T1.findall(text))
    text2 = T1.sub(pad, text)
    n2 = n3 = 0
    if group == "D":
        n2 = len(T2.findall(text2))
        text2 = T2.sub(pad2, text2)
        n3 = len(T3.findall(text2))
        text2 = T3.sub(pad3, text2)
    if n1 + n2 + n3 == 0:
        return (0, 0, 0)
    if APPLY:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text2)
    return (n1, n2, n3)


APPLY = "--apply" in sys.argv

if __name__ == "__main__":
    groups = build_groups()
    tot = {"t1": 0, "t2": 0, "t3": 0, "files": 0}
    for gname, files in groups.items():
        for p in files:
            a, b, c = migrate_file(p, gname)
            if a + b + c:
                rel = os.path.relpath(p, ROOT).replace("\\", "/")
                print(f"[{gname}] {rel}  T1={a} T2={b} T3={c}")
                tot["t1"] += a; tot["t2"] += b; tot["t3"] += c; tot["files"] += 1
    mode = "APPLY(已写入)" if APPLY else "DRY PREVIEW(未写文件)"
    print(f"\n=== {mode} | 改动文件 {tot['files']} 个 | Tier1 token {tot['t1']} | Tier2 表行 {tot['t2']} | Tier3 区间 {tot['t3']} ===")

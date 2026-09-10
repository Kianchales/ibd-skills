# -*- coding: utf-8 -*-
"""D 档补充：行业方法论_单份细分版/ 15 个活跃文件补 frontmatter（A 档只覆盖根目录 10 个合并版，单份版遗漏）
纯头部插入，正文零改动；幂等（已有 frontmatter 跳过）。用法：python add_fm_single.py [--dry-run]
"""
import io, os, re, sys

import argparse
from pathlib import Path

_ap = argparse.ArgumentParser(description="行业方法论单份细分版 frontmatter 补齐（D 档）")
_ap.add_argument("--methods-root", default=os.environ.get("METHODS_ROOT", ""),
                 help="方法论库根目录（默认 $METHODS_ROOT，或脚本上级目录）")
_ap.add_argument("--updated", default=None, help="写入 frontmatter 的 updated 日期（默认执行日）")
_args, _ = _ap.parse_known_args()
_ROOT = Path(_args.methods_root) if _args.methods_root else Path(__file__).resolve().parents[1]
_UPDATED_DEFAULT = _args.updated or __import__("datetime").date.today().strftime("%%Y-%%m-%%d")
UPDATED = _UPDATED_DEFAULT
METHODS = str(_ROOT / "methods")
SUB = str(_ROOT / "methods" / "行业方法论_单份细分版")
UPDATED = _UPDATED_DEFAULT


def parse_single(fn):
    """从文件名提取 case（公司名）与 industry_class（行业类）。"""
    ic_m = re.search(r"_行业方法论_(.+?)\.md$", fn)
    industry_class = ic_m.group(1).strip() if ic_m else ""
    date_m = re.search(r"_(\d{8})_", fn)
    case = ""
    if date_m:
        pre = fn[: date_m.start()]
        case = pre.split("_")[-1].strip()
    return case, industry_class


def main():
    dry = "--dry-run" in sys.argv
    files = sorted(f for f in os.listdir(SUB) if f.endswith(".md"))
    planned = []
    for fn in files:
        p = os.path.join(SUB, fn)
        with io.open(p, encoding="utf-8") as f:
            head = f.read(200)
        if head.startswith("---"):
            continue  # 已有 frontmatter
        case, ic = parse_single(fn)
        fm = "---\ntype: 行业方法论（单份细分版）\ncase: %s\nindustry_class: %s\nupdated: %s\n---\n\n" % (case, ic, UPDATED)
        planned.append((p, fm, fn, case, ic))
    print("计划补 frontmatter %d 个（总 %d 个文件）" % (len(planned), len(files)))
    for p, fm, fn, case, ic in planned:
        print("  %s | case=%s | class=%s" % (fn, case, ic))
    if dry or not planned:
        return
    for p, fm, _, _, _ in planned:
        with io.open(p, encoding="utf-8") as f:
            raw = f.read()
        with io.open(p, "w", encoding="utf-8", newline="") as f:
            f.write(fm + raw)
    print("已写入 %d 个" % len(planned))


if __name__ == "__main__":
    main()

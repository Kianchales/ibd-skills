#!/usr/bin/env python3
"""check_index_locator.py — 索引行号定位抽查（护栏）

用途
    条目编号 → 「文件 + 行号」是定向读取的唯一键；一旦行号漂移（改内容未刷索引），
    定向读会读到**别的条目**且不报错 —— 这是静默缺陷。本脚本随机抽样目录中的 N 条，
    回查「该文件该行是否真的就是该条目」，发现漂移即 FAIL。

判据
    对目录（`方法论_条目标题目录.md`）中的可解析行：
      · 域文件条目：3 列 `| 编号 | 标题 | 行号 |`，文件由所在 `## <文件名>` 分组给出
      · 分卷条目：4 列 `| 编号 | 标题 | 卷文件 | 行号 |`
      · 附表（`## 附：WL 系列` / `## 附：PL 系列`）：按编号前缀映射到 W 系列主文件 / P 系列卷
    抽查命中率须 = 100%（抽样未命中即视为漂移）。

用法
    python check_index_locator.py --methods-root <工作区根> [--sample 12] [--seed 20260919] [--json]

退出码
    0 全部命中 ／ 1 存在未命中 ／ 2 用法错 ／ 3 目录文件缺失
"""
import argparse
import io
import json
import os
import random
import re
import sys

import os as _lo, sys as _ls
_ls.path.insert(0, _lo.path.dirname(_lo.path.abspath(__file__)))
from _lib.layout import METHODS_NAME, TOC_FILE, VOLUME_NAME, SINGLE_NAME, LANG_W_FILE, library_files
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROW = re.compile(r"^\| ([A-Z]{1,3}-\d{6}) \| (.+?) \| (.+?) \|$")
H2 = re.compile(r"^## (.+?)\s*$")
H_APPENDIX = re.compile(r"^## 附：((?:W|P)L?) 系列")   # 2026-09-23 WO-06：兼容改名后的「WL 系列」/「PL 系列」


def parse_toc(path):
    """返回 [(eid, 目标文件, 行号)]"""
    lines = io.open(path, encoding="utf-8", errors="replace").read().splitlines()
    group = None
    appendix = None
    rows = []
    for ln in lines:
        m2 = H2.match(ln)
        if m2:
            t = m2.group(1)
            ma = H_APPENDIX.match(ln)
            appendix = ma.group(1) if ma else None
            group = None if appendix else re.sub(r"（.*?）$", "", t).strip().strip("` ")
            continue
        m = ROW.match(ln)
        if not m:
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        eid, title = m.group(1), m.group(2)
        if len(cells) == 4:
            rows.append((eid, cells[2], int(cells[3]) if cells[3].isdigit() else None))
        elif len(cells) == 3 and cells[2].isdigit():
            if group:
                rows.append((eid, group, int(cells[2])))
            elif appendix in ("W", "WL"):
                rows.append((eid, LANG_W_FILE, int(cells[2])))
            elif appendix in ("P", "PL"):
                rows.append((eid, None, int(cells[2])))   # P 附表为 4 列，不该落到这里
    return rows


def main():
    ap = argparse.ArgumentParser(description="索引行号定位抽查（护栏）")
    ap.add_argument("--methods-root", default=os.environ.get("METHODS_ROOT", ""),
                    help="库所在的工作区根（缺省取 $METHODS_ROOT；非库本身）")
    ap.add_argument("--sample", type=int, default=12)
    ap.add_argument("--seed", type=int, default=20260919)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if not a.methods_root:
        sys.stderr.write("[MISS] 需 --methods-root <工作区根> 或环境变量 METHODS_ROOT\n")
        return 2

    md = os.path.join(os.path.abspath(a.methods_root), METHODS_NAME)
    toc = os.path.join(md, TOC_FILE)
    if not os.path.exists(toc):
        sys.stderr.write("[MISS] 找不到目录文件: %s\n" % toc)
        return 3

    rows = [r for r in parse_toc(toc) if r[1] and r[2]]
    if not rows:
        sys.stderr.write("[SKIP] 目录无可解析行\n")
        return 3

    # C3b：正文已分居 10_跨案域/、20_语言专项/、50_分卷/、40_单案/ ⇒ basename 反查实存路径
    _by_base = {os.path.basename(x): x for x in library_files(md)}

    random.seed(a.seed)
    picked = random.sample(rows, min(a.sample, len(rows)))
    miss = []
    for eid, fn, ln in picked:
        p = _by_base.get(fn) or next((x for x in (os.path.join(md, fn),
                                                  os.path.join(md, VOLUME_NAME, fn),
                                                  os.path.join(md, SINGLE_NAME, fn))
                                      if os.path.exists(x)), None)
        if p is None:
            miss.append({"eid": eid, "file": fn, "line": ln, "why": "文件不存在"})
            continue
        lines = io.open(p, encoding="utf-8", errors="replace").read().splitlines()
        if not (0 < ln <= len(lines)) or eid not in lines[ln - 1]:
            miss.append({"eid": eid, "file": fn, "line": ln, "why": "该行非该条目"})

    n_ok = len(picked) - len(miss)
    if a.json:
        print(json.dumps({"tool": "check_index_locator", "checked": len(picked),
                          "ok": n_ok, "miss": miss}, ensure_ascii=False))
    else:
        print("=== 索引行号定位抽查 ===")
        print("目录可解析行 %d ｜ 抽查 %d ｜ 命中 %d ｜ 未命中 %d"
              % (len(rows), len(picked), n_ok, len(miss)))
        for x in miss:
            print("  ❌ %s → %s:%s（%s）" % (x["eid"], x["file"], x["line"], x["why"]))
        print("--- %s" % ("PASS ✅" if not miss else "FAIL ★（行号漂移：改内容后未刷索引？）"))
    return 1 if miss else 0


if __name__ == "__main__":
    sys.exit(main())

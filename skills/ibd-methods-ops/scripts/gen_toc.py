#!/usr/bin/env python3
"""生成 方法论_条目标题目录.md：
读 parsed_titles.txt（含「域文件」列）→ 按域文件分组生成目录（编号 → 域文件 + 行号，供 Read offset/limit 精准读）。
扩展性：新增域文件经 parse 后自动出现为目录分组，零改码。

用法：
    python gen_toc.py [--methods-root <工作区根>]

参数：
    --methods-root  工作区根（= 库根，其下含 methods/；默认 $METHODS_ROOT，或脚本上级目录）
"""
import argparse, io, os
from collections import OrderedDict
from pathlib import Path

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_ap = argparse.ArgumentParser(description="生成条目标题目录.md")
_ap.add_argument("--methods-root", default=os.environ.get("METHODS_ROOT", ""),
                 help="工作区根（= 库根，其下含 methods/；默认 $METHODS_ROOT，或脚本上级目录）")
_args = _ap.parse_args()
_ROOT = Path(_args.methods_root) if _args.methods_root else Path(__file__).resolve().parents[1]
METHODS = str(_ROOT / "methods")
PARSED = os.path.join(str(_ROOT / "scripts"), "parsed_titles.txt")
TOC = os.path.join(METHODS, "方法论_条目标题目录.md")



def _require_library():
    """冷启动前置检查：未找到方法论库时给出清晰指引，而非堆栈崩溃"""
    import sys as _s
    if not os.path.isdir(METHODS):
        _s.stderr.write("✗ 未找到方法论库：%s\n" % METHODS)
        _s.stderr.write("  用法：--methods-root <工作区根>（或设环境变量 METHODS_ROOT）\n")
        _s.stderr.write("  首次使用：按 SKILL.md「库配置」四问引导接入你的库；库结构规范见 references/methods-guide.md\n")
        _s.exit(2)


_require_library()

# ---- 1. 读解析结果（5 列：域文件/编号/标题/类型/行号）----
entries = []
with io.open(PARSED, "r", encoding="utf-8") as f:
    for ln in f.read().splitlines()[1:]:
        p = ln.split("\t")
        if len(p) == 5:
            entries.append({"dom": p[0], "eid": p[1], "title": p[2], "kind": p[3], "ln": int(p[4])})

head = [e for e in entries if e["kind"] == "HEAD"]
wd = [e for e in entries if e["kind"] in ("WD", "WD_LIST")]
# 2026-09-19：WD 类按前缀分流（W 系列 WL-/W- ｜ P 系列 PL-），分列两个附表
wd_w = [e for e in wd if not e["eid"].startswith("PL-")]
wd_p = [e for e in wd if e["eid"].startswith("PL-")]

# ---- 2. 按域文件分组（保持域文件顺序）----
dom_order = []
for e in head:
    if e["dom"] not in dom_order:
        dom_order.append(e["dom"])

out = []
out.append("# 方法论条目标题目录（按域文件 · 脚本化生成）")
out.append("")
out.append("> 生成：脚本化（parse_v26_titles → gen_toc，P0 拆分版）｜ 解析全部域文件条目 ｜ **定位用：按编号 → 域文件 + 行号，用 Read offset/limit 精准读正文。**")
out.append("> 路由入口见 `methods/通用方法论_最终版.md`（域路由表）；调用索引见 `methods/方法论调用索引.md`（28Q 域速查 + 全量映射）。")
out.append("")
out.append("## 总览")
out.append("")
out.append("| 域文件 | 条目数 |")
out.append("|--------|--------|")
from collections import Counter
dom_counts = Counter(e["dom"] for e in head)
total_head = 0
for d in dom_order:
    out.append("| %s | %d |" % (d, dom_counts.get(d, 0)))
    total_head += dom_counts.get(d, 0)
out.append("| **合计** | **%d**（正文条目） + W 条目 %d + P 条目 %d |" % (total_head, len(wd_w), len(wd_p)))
out.append("")

# ---- 3. 按域文件分组输出 HEAD 条目 ----
cur = None
for e in head:
    if e["dom"] != cur:
        out.append("## " + e["dom"])
        out.append("")
        out.append("| 编号 | 条目标题 | 行号 |")
        out.append("|------|---------|------|")
        cur = e["dom"]
    out.append("| %s | %s | %d |" % (e["eid"], e["title"], e["ln"]))

# ---- 4. W 系列条目（粗体条目 + W-D 列表）----
if wd_w:
    out.append("## 附：W 系列（投行语言句式 · %d 条 · 正文在 methods/投行语言专项_W系列.md）" % len(wd_w))
    out.append("")
    out.append("| 编号 | 核心句式要点 | 行号 |")
    out.append("|------|-------------|------|")
    for e in wd_w:
        out.append("| %s | %s | %d |" % (e["eid"], e["title"], e["ln"]))
    out.append("")

# ---- 4b. P 系列条目（招股书语言范式 · 正文在外置卷）----
if wd_p:
    out.append("## 附：P 系列（招股书语言范式 · %d 条 · 正文在 methods/分卷/投行语言专项_P系列_卷N.md）" % len(wd_p))
    out.append("")
    out.append("| 编号 | 招股书语言要点 | 卷文件 | 行号 |")
    out.append("|------|---------------|--------|------|")
    for e in wd_p:
        out.append("| %s | %s | %s | %d |" % (e["eid"], e["title"], e["dom"], e["ln"]))

d = os.path.dirname(TOC)
if d:
    os.makedirs(d, exist_ok=True)
with io.open(TOC, "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(out) + "\n")
print("TOC:", TOC, "rows:", total_head, "+W", len(wd_w), "+P", len(wd_p))
print("DONE")


sys.exit(0)

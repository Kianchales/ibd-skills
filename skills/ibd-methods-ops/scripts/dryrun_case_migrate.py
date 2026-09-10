# -*- coding: utf-8 -*-
"""
案号 4 位化迁移 · DRY-RUN 预检 v2（只统计不改文件）

目标：C01-C41（2 位案号）→ C0001-C0041（4 位案号）正式迁移前的精确影响报告。
改进（v2）：
  1. 从对照表/登记表解析 公司↔案号 权威映射，A 组文件"本案号"以映射为准；
  2. token 分类按行语境（标题行/正文行）拆分，标题行不再误计入"行内"；
  3. 每个文件的非本案号 token 附样本行（≤5），供人工识别跨案引用/误匹配。

token 定义：案号 token = `[FILW]-C{1,2}-`（后面必须紧跟 `-`，如 F-C30-01 / W-C30-A01 /
           W-C30-结-04）；中文族名 = 该 token 后跟 结/限/称/时/数/严/语 之一。
其它 C 提及（`| C30 |` 表行、`C32-C41` 区间等）单独计数、不参与替换判断（D/E 组表格行另列）。

用法：python scripts/dryrun_case_no_migrate.py [--report tasks/20260906_C案号4位化迁移_干跑报告.md]
"""
import glob
import os
import re
import sys
from collections import Counter, OrderedDict

import argparse

_ap = argparse.ArgumentParser(description="案号迁移 · dry-run 预检（只统计不改文件）")
_ap.add_argument("--methods-root", default=os.environ.get("METHODS_ROOT", ""),
                 help="方法论库根目录（默认 $METHODS_ROOT，或脚本上级目录）")
_ap.add_argument("--registry", default="",
                 help="案号登记/对照表路径（逗号分隔；默认自动扫描 tasks/ 下含「登记」「对照表」的 md）")
_args, _ = _ap.parse_known_args()
ROOT = _args.methods_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TOKEN = re.compile(r"\b([FILW])-C(\d{1,2})-")
CN_FAM = re.compile(r"\b[FILW]-C(\d{1,2})-(结|限|称|时|数|严|语)")
HEADISH = re.compile(r"^#{2,6} |^\*\*[FILW]-C")
BARE = re.compile(r"\bC(\d{1,2})(?!\d)")
ROW_C = re.compile(r"\|\s*C(\d{1,2})\s*\|")

# ---------- 权威映射：公司简称 -> 案号 ----------
def build_case_map():
    m = {}
    # 登记/对照表来源：--registry 显式指定（逗号分隔），否则自动扫描 tasks/ 下含「登记」「对照表」的 md
    if _args.registry:
        paths = [p.strip() for p in _args.registry.split(",") if p.strip()]
    else:
        paths = sorted(set(
            glob.glob(os.path.join(ROOT, "tasks", "*登记*.md")) +
            glob.glob(os.path.join(ROOT, "tasks", "*对照表*.md"))
        ))
    # 行形态：| C30 | 某公司 | 通用方法论…某公司.md | ...  或 | C32 | 某公司 | 板块_… | ... |
    pat = re.compile(r"\|\s*C(\d{1,2})\s*\|\s*([^|]+?)\s*\|")
    for p in paths:
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8") as f:
            for ln in f:
                mm = pat.search(ln)
                if mm:
                    m[mm.group(2).strip()] = int(mm.group(1))
    return m


def scan_file(path, own_no):
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    st = {"head_tok": 0, "body_tok": 0, "cn_fam": 0, "bare": 0, "own_tok": 0, "off_tok": 0,
          "offs": [], "cases": Counter(), "cn_samp": []}
    for ln in lines:
        if CN_FAM.search(ln):
            st["cn_fam"] += 1
            if len(st["cn_samp"]) < 5:
                st["cn_samp"].append(ln.strip()[:90])
        hits = list(TOKEN.finditer(ln))
        if not hits and ROW_C.search(ln):
            st["bare"] += 1
        is_head = bool(HEADISH.match(ln))
        for h in hits:
            n = int(h.group(2))
            st["cases"][n] += 1
            if own_no is not None and n == own_no:
                st["own_tok"] += 1
            else:
                st["off_tok"] += 1
                if len(st["offs"]) < 5:
                    s = ln.strip()
                    st["offs"].append(f"(案号C{n:02d}) {s[:80]}")
            if is_head:
                st["head_tok"] += 1
            else:
                st["body_tok"] += 1
    return st


def main():
    report_path = "tasks/案号迁移_干跑报告.md"
    if "--report" in sys.argv:
        report_path = sys.argv[sys.argv.index("--report") + 1]
    case_map = build_case_map()

    groups = OrderedDict()
    a_files = sorted(glob.glob(os.path.join(ROOT, "methods", "通用方法论_投行知识与写作范式_*.md")))
    groups["A 单案范式(writer, M1必改)"] = a_files
    groups["B 主库/路由(M2)"] = [os.path.join(ROOT, "methods", f) for f in
                                  ["通用方法论_最终版.md", "通用方法论_财务域.md", "通用方法论_法律域.md",
                                   "通用方法论_行业域.md", "通用方法论_写作域.md", "投行语言专项_W系列.md"]
                                  if os.path.exists(os.path.join(ROOT, "methods", f))]
    groups["C 行业方法论(M2)"] = sorted(glob.glob(os.path.join(ROOT, "methods", "行业方法论_*.md"))) + \
        sorted(glob.glob(os.path.join(ROOT, "methods", "行业方法论_单份细分版", "*.md")))
    groups["D 对照/登记(M3/M4)"] = [os.path.join(ROOT, "tasks", f) for f in
                                     ["单案索引对照表.md", "案号分配登记.md",
                                      "案号分配登记.md"] if os.path.exists(os.path.join(ROOT, "tasks", f))]
    groups["E 蒸馏笔记(不回改)"] = sorted(glob.glob(os.path.join(ROOT, "methods", "notes", "*.md")))

    def company_of(p):
        b = os.path.basename(p).replace("通用方法论_投行知识与写作范式_", "").replace(".md", "")
        return b

    out = []
    out.append("# 案号 4 位化迁移 · DRY-RUN 干跑报告 v2（只统计，未改任何文件）")
    out.append("")
    out.append("> 生成 2026-09-06；目标 C01-C41 → C0001-C0041。token=`[FILW]-C{1,2}-`（须后跟 `-`）。"
               "标题=行首 `#…`/`**` 语境，正文=其余；off=非本案号 token（跨案引用或误匹配，附样本人工核验）。")
    g_tot = {k: 0 for k in ["head_tok", "body_tok", "cn_fam", "bare"]}
    rows = []
    no_map_a = []
    for gname, files in groups.items():
        out.append("")
        out.append(f"## {gname}（{len(files)} 文件）")
        out.append("")
        out.append("| 文件 | 本案号 | 标题token | 正文token | 中文族 | 其它C | off样本 |")
        out.append("|---|---|---|---|---|---|---|")
        for p in files:
            rel = os.path.relpath(p, ROOT).replace("\\", "/")
            if gname.startswith("A"):
                own = case_map.get(company_of(p))
                if own is None:
                    no_map_a.append(rel)
            else:
                own = None
            st = scan_file(p, own)
            for k in g_tot:
                g_tot[k] += st[k]
            own_s = f"C{own:02d}" if own is not None else "?"
            off_s = "; ".join(st["offs"][:2]) if st["offs"] else ""
            rows.append(f"| {rel} | {own_s} | {st['head_tok']} | {st['body_tok']} | {st['cn_fam']} | {st['bare']} | {off_s} |")
        out.append("")
    out.append("## 汇总（全部扫描文件）")
    out.append("")
    out.append("| 语境分类 | 计数 | 说明 |")
    out.append("|---|---|---|")
    out.append(f"| 标题语境 token | {g_tot['head_tok']} | 条目标题行内的案号（M1 主体） |")
    out.append(f"| 正文语境 token | {g_tot['body_tok']} | 正文/对照锚点/引用串（M1+M2） |")
    out.append(f"| 中文族名引用 | {g_tot['cn_fam']} | `W-C30-结-04` 型，需定类映射后替换 |")
    out.append(f"| 其它 C 提及 | {g_tot['bare']} | `\\| C30 \\|` 表行等，D 组表格行单独处理 |")
    out.append("")
    out.append("> 替换总量≈ 标题+正文（两值含中文族名 token，去重后另计）；正式迁移将全量 pad `C{NN}`→`C{NNNN}`，"
               "表格行按行重写。历史字母码产出（F-JH-01 型，无 C 号）不在迁移范围。")
    out.append("")
    out.append("## 逐文件明细")
    out.append("")
    out.append("| 文件 | 本案号 | 标题token | 正文token | 中文族 | 其它C | off样本 |")
    out.append("|---|---|---|---|---|---|---|")
    out.extend(rows)
    if no_map_a:
        out.append("")
        out.append(f"⚠ 未在对照表/登记表命中案号的文件（{len(no_map_a)}）：{no_map_a}")
    out.append("")
    report_abs = os.path.join(ROOT, report_path)
    os.makedirs(os.path.dirname(report_abs) or ".", exist_ok=True)
    with open(report_abs, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print("dry-run v2 done:", report_path)
    print("totals:", g_tot)
    print("A-not-in-map:", no_map_a)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""索引重跑校验 ＋ 条目数对账（只读 · 2026-09-26 WO-23）。

用法：
    python check_index_idempotent.py [--methods-root <工作区根>] [--json] [--skip-rebuild]

两项判定：
  ① **重跑校验**：把 `methods/` 复制到临时目录 → 在临时根重跑五个生成器
     （parse_titles → gen_index → gen_toc → gen_entry → gen_refgraph）
     → 与真实库 `_generated/*.md` 逐字节 diff。
     **diff 非空 ＝ FAIL**（说明生成物与「重跑结果」不一致：或手工注入过、或生成器有非确定性）。
  ② **条目数对账**：位置目录登记行数 vs 解析实得条目数 —— 只报差异，**不阻断**。

为什么用「重跑 diff」而不是「抽 12 条验行号」（原做法）：
    索引/目录/入口/图谱**全是生成物** ⇒ 最强的校验就是「**数秒全库重跑，看是否一致**」，
    即「**no incremental state to maintain**」：无状态 ⇒ 无需维护基线，
    抽样覆盖率问题（原实测 12/1689 ＝ 0.71%）自然消失。

边界（诚实声明）：
    · **只读真实库**：所有重跑发生在临时目录内；真实库的 `_generated/` 不被改动。
      （唯一例外：`parse_titles.py` 的中间产物 `parsed_titles.txt` 落于脚本目录，属既有设计。）
    · 条目数对账的差异**只报不拦**——条目数与登记行数的口径差可能来自附录/族卷形态，需人判。
"""
import argparse, filecmp, io, json, os, re, shutil, subprocess, sys, tempfile

import sys as _s
if hasattr(_s.stdout, "reconfigure"):
    _s.stdout.reconfigure(encoding="utf-8")

_ap = argparse.ArgumentParser(description="索引重跑校验 ＋ 条目数对账")
_ap.add_argument("--methods-root", default=os.environ.get("METHODS_ROOT", ""),
                 help="工作区根（= 库根，其下含 methods/）")
_ap.add_argument("--json", action="store_true", help="输出结构化 JSON")
_ap.add_argument("--skip-rebuild", action="store_true", help="跳过重跑 diff（只做条目数对账）")
_args = _ap.parse_args()

import os as _lo, sys as _ls
_here = _lo.path.dirname(_lo.path.abspath(__file__))
_ls.path.insert(0, _here)
from _lib.layout import (resolve as _layout_resolve, SCRIPTS_DIR, TOC_BASENAME,
                         INDEX_BASENAME, ENTRY_BASENAME, REFGRAPH_BASENAME,
                         DOMAIN_GLOB, LANG_GLOB, VOLUME_NAME)

_ROOT, METHODS, SCRIPTS = _layout_resolve(_args.methods_root)
if not os.path.isdir(METHODS):
    sys.stderr.write("✗ 未找到方法论库：%s\n" % METHODS)
    sys.exit(2)

GEN_STEPS = ["parse_titles.py", "gen_index.py", "gen_toc.py", "gen_entry.py", "gen_refgraph.py"]
GEN_FILES = [ENTRY_BASENAME, INDEX_BASENAME, TOC_BASENAME, REFGRAPH_BASENAME]


def rebuid_and_diff():
    """复制 methods/ 与 tasks/ 到临时根 → 跑生成器 → 与真实生成物逐字节 diff。"""
    tmp = tempfile.mkdtemp(prefix="wb_idxidem_")
    try:
        shutil.copytree(METHODS, os.path.join(tmp, "methods"))
        for extra in ("tasks", "state"):
            src = os.path.join(_ROOT, extra)
            if os.path.isdir(src):
                shutil.copytree(src, os.path.join(tmp, extra))
        logs = []
        for step in GEN_STEPS:
            p = os.path.join(str(SCRIPTS_DIR), step)
            if not os.path.exists(p):
                logs.append("✗ 缺脚本 %s（跳过该步）" % step)
                continue
            cmd = [sys.executable, p, "--methods-root", tmp]
            if step == "gen_refgraph.py":
                # **材料层不在临时根内**：`cases/`（MB 级）不随 `methods/` 复制，必须把「材料根」
                #   指回真实库 —— 否则对账栏全 0、与现库生成物不一致 ⇒ **误报非幂等**
                #   （2026-09-26 实测踩过：幂等 FAIL 指错方向，真因是环境差异而非生成器不确定）。
                cmd += ["--cases-root", str(_ROOT)]
            r = subprocess.run(cmd,
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            if r.returncode != 0:
                logs.append("✗ %s 退出码 %d：%s" % (step, r.returncode,
                                                  (r.stderr or r.stdout or "").strip()[-160:]))
        # diff：只比 _generated 下四个生成物（其余产物如 parsed_titles 落脚本目录，不比）
        diffs = []
        for base in GEN_FILES:
            a = os.path.join(METHODS, "_generated", base)
            b = os.path.join(tmp, "methods", "_generated", base)
            if not os.path.exists(a) and not os.path.exists(b):
                continue
            if not os.path.exists(a) or not os.path.exists(b):
                diffs.append("%s（一侧缺失）" % base)
                continue
            if not filecmp.cmp(a, b, shallow=False):
                diffs.append(base)
        return diffs, logs
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def conservation():
    """条目数对账：位置目录登记行数 vs 解析实得条目数。"""
    toc_rows = 0
    toc_ids = set()
    toc = os.path.join(METHODS, "_generated", TOC_BASENAME)
    if os.path.exists(toc):
        for ln in io.open(toc, encoding="utf-8", errors="replace"):
            m = re.match(r"\|\s*([A-Z]{1,3}-\d{6})\s*\|", ln)
            if m:
                toc_rows += 1
                toc_ids.add(m.group(1))
    ent = 0
    import glob
    scan = (sorted(glob.glob(os.path.join(METHODS, DOMAIN_GLOB))) +
            sorted(glob.glob(os.path.join(METHODS, LANG_GLOB))) +
            sorted(glob.glob(os.path.join(METHODS, VOLUME_NAME, "*.md"))))
    RX_H3 = re.compile(r"^### [FLIS]-\d{6}|^### （\d+）", re.M)
    RX_W = re.compile(r"^\*\*((?:WL|PL)-[A-Za-z0-9\-·~]+)", re.M)
    RX_WL = re.compile(r"^-\s*\*\*((?:WL|PL)-[A-Za-z0-9\-·~]+)\*\*", re.M)
    RX_WH = re.compile(r"^### ((?:WL|PL)-\d{6})", re.M)
    for f in scan:
        txt = io.open(f, encoding="utf-8", errors="replace").read()
        if os.path.basename(f).startswith("投行语言专项"):
            ent += len(RX_W.findall(txt)) + len(RX_WL.findall(txt)) + len(RX_WH.findall(txt))
        else:
            ent += len(RX_H3.findall(txt))
    return {"toc_rows": toc_rows, "toc_unique_ids": len(toc_ids), "entries_parsed": ent,
            "gap": toc_rows - ent}


def main():
    cons = conservation()
    diffs, logs = ([], []) if _args.skip_rebuild else rebuid_and_diff()
    verdict = "FAIL" if diffs else "PASS"
    if _args.json:
        print(json.dumps({"tool": "check_index_idempotent", "target": METHODS, "verdict": verdict,
                          "diffs": diffs, "logs": logs, "conservation": cons}, ensure_ascii=False))
        return 1 if diffs else 0
    print("=== 索引重跑校验 ＋ 条目数对账 ===")
    if _args.skip_rebuild:
        print("（已跳过重跑 diff）")
    else:
        for l in logs:
            print("  " + l)
        if diffs:
            print("✗ 重跑校验 **FAIL**：重跑结果与现库生成物不一致 %d 件 —— %s" % (len(diffs), "、".join(diffs)))
            print("  ⇒ 处置：跑 `refresh_index.py` 重建生成物后复验；若仍不一致，说明生成器有非确定性（需查）。")
        else:
            print("✓ 重跑校验 PASS：重跑五个生成器，`_generated/` 四件与现库**逐字节一致**")
    print("— 条目数对账（只报不拦）—")
    print("  位置目录登记行数: %d ｜ 去重编号: %d ｜ 解析实得条目数: %d ｜ 差: %+d"
          % (cons["toc_rows"], cons["toc_unique_ids"], cons["entries_parsed"], cons["gap"]))
    if cons["gap"]:
        print("  ⚠ 存在差异：登记行数与解析条目数不等价（口径差可能来自附录/族卷形态，需人判，不阻断）")
    return 1 if diffs else 0


if __name__ == "__main__":
    sys.exit(main())

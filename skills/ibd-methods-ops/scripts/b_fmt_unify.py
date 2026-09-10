# -*- coding: utf-8 -*-
"""B 档：方法论域文件结构归一（2026-08-31）

四类动作（全部同行替换 · 行号守恒 · 铁律全保留 · 幂等可重跑）：
1) 域前缀条目去前缀：### 财务（103）xxx → ### （103）xxx（财务 7 条 / 法律 9 条）
   —— 域前缀编号段恰为 (N) 体系空缺段，去前缀即恢复标准编号，位置/编号零变动
2) 版本说明 h3 转块引用：### 2026-08-23 批量 10 案… → > **批次注记**：…
   —— 版本迭代信息移出标题体系（符合「版本迭代只放 CHANGELOG」裁定）
3) 批次 h2 转块引用：## 一、v35… → > **批次注记**：…（仅财务/法律/行业 3 域）
   —— 三域唯一 h2 均为 v35 批次章节头，正常结构应为 h1→h3 条目
4) 分组 h3 降 h4：### A 组 / ### B 组 / ### 族 [A-F] → ####
   —— 内容分组导航保留，不再占条目计数层

用法：python b_fmt_unify.py [--dry-run | --verify]
"""
import io, os, re, sys, shutil

import argparse
from pathlib import Path

_ap = argparse.ArgumentParser(description="域文件结构归一（B 档）")
_ap.add_argument("--methods-root", default=os.environ.get("METHODS_ROOT", ""),
                 help="方法论库根目录（默认 $METHODS_ROOT，或脚本上级目录）")
_args, _ = _ap.parse_known_args()
_ROOT = Path(_args.methods_root) if _args.methods_root else Path(__file__).resolve().parents[1]
METHODS = str(_ROOT / "methods")
BACKUP = os.path.join(METHODS, "archive", "b_fmt_unify_backup")
FILES = ["通用方法论_财务域.md", "通用方法论_法律域.md", "通用方法论_行业域.md"]

RE_PREFIX = re.compile(r"^### (财务|法律)（(\d+)）(.*)$")
RE_VER = re.compile(r"^### 2026-08-23 批量 10 案.+（S6b · v34→v35，\d+ 条）$")
RE_BATCH = re.compile(r"^## 一、")
RE_GROUP = re.compile(r"^### (A 组：|B 组：|族 [A-F] )")
RE_BQ = re.compile(r"^> \*\*批次注记\*\*：")

def process(fn, dry=True):
    path = os.path.join(METHODS, fn)
    with io.open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    plan = []
    new = []
    for i, s in enumerate(lines):
        if RE_BQ.match(s):
            new.append(s)
            continue
        m = RE_PREFIX.match(s)
        if m:
            ns = "### （%s）%s" % (m.group(2), m.group(3))
            plan.append((fn, i + 1, "去前缀", s[:58], ns[:58]))
            new.append(ns)
            continue
        if RE_VER.match(s):
            ns = "> **批次注记**：" + s[4:]
            plan.append((fn, i + 1, "版本说明转注记", s[:58], ns[:58]))
            new.append(ns)
            continue
        if RE_BATCH.match(s):
            ns = "> **批次注记**：" + s[3:]
            plan.append((fn, i + 1, "批次h2转注记", s[:58], ns[:58]))
            new.append(ns)
            continue
        if RE_GROUP.match(s):
            ns = "#" + s
            plan.append((fn, i + 1, "分组降h4", s[:58], ns[:58]))
            new.append(ns)
            continue
        new.append(s)
    return plan, new

def main():
    dry = "--dry-run" in sys.argv
    verify = "--verify" in sys.argv
    all_plan = []
    all_new = {}
    for fn in FILES:
        plan, new = process(fn, dry)
        all_plan.extend(plan)
        all_new[fn] = new
    # 输出计划
    if dry or verify:
        print("=== B 档改动清单（%d 处）===" % len(all_plan))
        for fn, ln, act, old, ns in all_plan:
            print("  [%s L%d] %-12s" % (fn, ln, act))
            print("    - %s" % old)
            print("    + %s" % ns)
        if verify:
            return
        print("\ndry-run 完成，共 %d 处改动。无 --dry-run 参数时正式执行。" % len(all_plan))
        return
    # 正式执行：先备份
    os.makedirs(BACKUP, exist_ok=True)
    for fn in FILES:
        shutil.copy2(os.path.join(METHODS, fn), os.path.join(BACKUP, fn))
    print("备份完成 →", BACKUP)
    for fn in FILES:
        with io.open(os.path.join(METHODS, fn), "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(all_new[fn]) + "\n")
        print("已写入", fn, "（%d 处改动）" % sum(1 for p in all_plan if p[0] == fn))
    print("B 档执行完成，共 %d 处改动。" % len(all_plan))

if __name__ == "__main__":
    main()

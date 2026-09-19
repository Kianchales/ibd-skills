#!/usr/bin/env python3
"""sync_cases_md.py — 把 `cases/` 下的**文本产出（.md）**镜像到 git 仓，纳入备份

背景
    `cases/`（原料 + 蒸馏产出）位于工作区本地、**不是 junction、不在 git 仓内** ⇒
    它完全不被版本备份（PDF 706MB / txt 314MB 体量太大，不适合入 git；但 **.md 仅 ~17MB / 647 文件**）。
    本脚本把 `cases/**/*.md` 增量镜像到 git 仓内 `cases_md/`，使**产出与提炼物**获得版本备份。

口径
    · 源：`--src`（**默认取当前工作目录下的 `cases/`**；亦可用环境变量 `CASES_SRC` 指定——
      **不在脚本内写死任何本机私有路径**，公开分发包零私有绑定）
    · 镜像：`--mirror`（默认**由环境变量 `CASES_MIRROR` 或当前 git 仓根推导** `AgentAssets/workflow/cases_md`；
      **不写死绝对路径**——工程范式 A9「零私有绑定」）
    · **只同步 .md**（排除 pdf/txt/pkl/临时文件）；镜像保持与源相同的相对路径
    · 幂等：内容一致则跳过；源已删除的镜像文件**默认保留**（`--prune` 才删除并列出清单）
    · 落盘前自校验：字节级一致（写入后回读比对）

用法
    python sync_cases_md.py [--src <cases 目录>] [--mirror <镜像目录>] [--apply|--dry-run] [--prune] [--json]

退出码
    0 成功（含无变更）／1 自校验失败／2 用法错（含镜像落点无法确定）／3 源目录不存在
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DEF_SRC = os.path.join(os.getcwd(), "cases")       # 默认当前工作目录下的 cases/（不写死本机路径）
MIRROR_SUBPATH = os.path.join("AgentAssets", "workflow", "cases_md")


def default_mirror(src):
    """镜像落点（零硬编码）：环境变量 → git 仓根推导 → 空串（要求显式指定）。"""
    env = os.environ.get("CASES_MIRROR")
    if env:
        return env
    for base in (os.getcwd(), src):
        try:
            r = subprocess.run(["git", "-C", base, "rev-parse", "--show-toplevel"],
                               capture_output=True, text=True)
        except OSError:
            continue
        root = (r.stdout or "").strip()
        if r.returncode == 0 and root and os.path.isdir(os.path.join(root, "AgentAssets")):
            return os.path.join(root, MIRROR_SUBPATH)
    return ""


def md5(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description="cases/*.md → git 仓镜像（增量·幂等）")
    ap.add_argument("--src", default=os.environ.get("CASES_SRC") or DEF_SRC)
    ap.add_argument("--mirror", default=os.environ.get("CASES_MIRROR") or "")
    ap.add_argument("--apply", action="store_true", help="实际写入（默认 dry-run）")
    ap.add_argument("--dry-run", action="store_true", help="只报告不写入（默认行为，显式同义）")
    ap.add_argument("--prune", action="store_true", help="删除源已不存在的镜像文件（默认保留）")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    src = os.path.abspath(a.src)
    if not os.path.isdir(src):
        sys.stderr.write("[MISS] 源目录不存在: %s\n" % src)
        return 3
    mir = os.path.abspath(a.mirror) if a.mirror else default_mirror(src)
    if not mir:
        sys.stderr.write("[USAGE] 无法确定镜像落点：请用 --mirror 或环境变量 CASES_MIRROR 指定"
                         "（或在 git 仓内运行）\n")
        return 2

    add, upd, same = [], [], 0
    for dp, dn, fn in os.walk(src):
        dn[:] = [d for d in dn if not d.startswith("_")]
        for f in fn:
            if not f.endswith(".md"):
                continue
            sp = os.path.join(dp, f)
            rel = os.path.relpath(sp, src)
            mp = os.path.join(mir, rel)
            if not os.path.exists(mp):
                add.append((sp, mp, rel))
            elif md5(sp) != md5(mp):
                upd.append((sp, mp, rel))
            else:
                same += 1
    orphan = []
    if os.path.isdir(mir):
        for dp, dn, fn in os.walk(mir):
            for f in fn:
                if not f.endswith(".md"):
                    continue
                mp = os.path.join(dp, f)
                rel = os.path.relpath(mp, mir)
                if not os.path.exists(os.path.join(src, rel)):
                    orphan.append((mp, rel))

    written = 0
    if a.apply:
        for sp, mp, rel in add + upd:
            os.makedirs(os.path.dirname(mp), exist_ok=True)
            shutil.copy2(sp, mp)
            if md5(sp) != md5(mp):                    # 落盘后回读比对
                print("ABORT 自校验失败: %s" % rel)
                return 1
            written += 1
        if a.prune:
            for mp, rel in orphan:
                os.remove(mp)

    if a.json:
        print(json.dumps({"tool": "sync_cases_md", "src": src, "mirror": mir,
                          "new": len(add), "updated": len(upd), "unchanged": same,
                          "orphan": len(orphan), "written": written}, ensure_ascii=False))
    else:
        print("[%s] %s → %s" % ("APPLY" if a.apply else "DRY-RUN", src, mir))
        print("  新增 %d ｜ 更新 %d ｜ 未变 %d ｜ 孤儿 %d（%s）｜ 已写 %d"
              % (len(add), len(upd), same, len(orphan),
                 "prune 已清理" if (a.apply and a.prune) else "默认保留", written))
        for _, _, rel in (add + upd)[:10]:
            print("      ", rel)
    return 0


if __name__ == "__main__":
    sys.exit(main())

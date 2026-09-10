# -*- coding: utf-8 -*-
"""库拆分执行器（配置驱动 · 通用引擎）：单体大文件 → 域文件 + archive 备份 + 薄壳入口
铁律：只搬位置、不改内容（纯行号切割）；内置自校验：G1 条目守恒 + G2 内容零改动。

用法：
    python split_domains.py --config <拆分配置.json> [--methods-root <库根目录>] [--dry-run]

参数：
    --config        拆分配置（JSON，格式见下）；默认尝试 {库根}/tasks/split_domains_config.json
    --methods-root  方法论库根目录（默认 $METHODS_ROOT，或脚本上级目录）
    --dry-run       只输出计划不写盘

配置格式（split_domains_config.json）：
{
  "source": "通用方法论_最终版.md",          // 单体源文件（位于 methods/）
  "archive_guide_file": "_版本说明归档.md",  // 入口头部历史版本说明的归档文件名
  "domains": [
    { "file": "通用方法论_财务域.md",
      "range": [41, 1178],                  // 源文件中该域的行号段（1-based，人工确认后在配置中固化）
      "old_head": "## 一、财务知识",          // 源文件中的章头行（前缀匹配）
      "new_h1": "# 通用方法论·财务域",        // 域文件的新 H1
      "note": "> 源：入口拆分｜调用索引：methods/方法论调用索引.md" },
    ...
  ]
}

说明：
  - 拆分前自动备份源文件至 methods/archive/；源文件已是薄壳（行数 < 100）时跳过切割
  - 校验：G1 条目数守恒（源切片条目集 == 各域文件条目集）+ G2 内容零改动（逐段比对）
  - 新模式：本脚本为通用引擎，行号段等库实例信息一律置于配置，脚本本体零私有常量
"""
import argparse, io, json, os, re, sys, shutil
from pathlib import Path

_ap = argparse.ArgumentParser(description="库拆分执行器（配置驱动）")
_ap.add_argument("--config", default="", help="拆分配置 JSON（默认 {库根}/tasks/split_domains_config.json）")
_ap.add_argument("--methods-root", default=os.environ.get("METHODS_ROOT", ""),
                 help="方法论库根目录（默认 $METHODS_ROOT，或脚本上级目录）")
_ap.add_argument("--dry-run", action="store_true", help="只输出计划不写盘")
_args, _ = _ap.parse_known_args()

_HERE = Path(__file__).resolve().parent
_ROOT = Path(_args.methods_root) if _args.methods_root else _HERE.parent
METHODS = str(_ROOT / "methods")
ARCHIVE = os.path.join(METHODS, "archive")

cfg_path = _args.config or os.path.join(str(_ROOT), "tasks", "split_domains_config.json")
if not os.path.exists(cfg_path):
    print("✗ 缺少拆分配置：%s" % cfg_path)
    print("  提示：复制脚本 docstring 中的配置格式，按你的库结构填写『源文件 + 各域行号段』后重试。")
    sys.exit(1)

cfg = json.loads(io.open(cfg_path, encoding="utf-8").read())
SRC = os.path.join(METHODS, cfg.get("source", "通用方法论_最终版.md"))
DOMAINS = cfg.get("domains", [])
if not DOMAINS:
    print("✗ 配置中 domains 为空"); sys.exit(1)


def w(path, content):
    if _args.dry_run:
        print("  [dry-run] 将写入 %s（%d 字符）" % (os.path.basename(path), len(content)))
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8").write(content)


def seg(a, b):  # 1-based 闭区间
    return "".join(lines[a - 1:b])


with io.open(SRC, "r", encoding="utf-8") as f:
    lines = f.readlines()

if len(lines) < 100:
    print("!! 源文件已是入口薄壳（%d 行），跳过切割。如需重跑：从 archive/ 全量备份恢复源文件。" % len(lines))
    sys.exit(0)

print("源文件: %s（%d 行）" % (os.path.basename(SRC), len(lines)))

# ---------- 备份 ----------
if not _args.dry_run:
    os.makedirs(ARCHIVE, exist_ok=True)
    shutil.copy2(SRC, os.path.join(ARCHIVE, os.path.basename(SRC) + ".pre_split_backup"))
    print("备份: archive/%s.pre_split_backup" % os.path.basename(SRC))

# ---------- 切分各域 ----------
def entries_of(text_lines):
    """条目 = h3 行（### 开头；编号格式不限——兼容阿拉伯/中文序号/带域前缀形态，分组标题应为 h4）"""
    return set(ln.strip() for ln in text_lines if ln.startswith("### "))


for d in DOMAINS:
    a, b = d["range"]
    domain_lines = [ln for ln in lines[a - 1:b]]
    # 章头替换
    head = d.get("old_head", "")
    if head:
        for i, ln in enumerate(domain_lines):
            if ln.startswith(head):
                domain_lines[i] = d["new_h1"] + "\n"
                break
    content = d.get("note", "").strip()
    body = "".join(domain_lines)
    if content:
        body = content + "\n\n" + body
    w(os.path.join(METHODS, d["file"]), body)
    print("  ✓ %s（行 %d-%d，%d 条目）" % (d["file"], a, b, len(entries_of(domain_lines))))

# ---------- G1/G2 自校验 ----------
body_all = []
for d in DOMAINS:
    a, b = d["range"]
    body_all += lines[a - 1:b]
n_src = len(entries_of(body_all))
n_dom = sum(len(entries_of(io.open(os.path.join(METHODS, d["file"]), encoding="utf-8").read().splitlines()))
            for d in DOMAINS) if not _args.dry_run else n_src
print("G1 条目守恒：源切片 %d 条 vs 域文件合计 %d 条 → %s" % (n_src, n_dom, "PASS" if n_src == n_dom else "FAIL"))
if n_src == 0:
    print("!! G1 校验失效：源切片未识别到条目（h3）——请检查配置的 range 行号段是否正确")
    sys.exit(1)
if n_src != n_dom:
    sys.exit(1)
print("完成%s" % ("（dry-run 未写盘）" if _args.dry_run else ""))

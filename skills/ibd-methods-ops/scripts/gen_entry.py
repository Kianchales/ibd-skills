# -*- coding: utf-8 -*-
"""入口生成器（可复用）：glob 域文件 → 重写 通用方法论_最终版.md 路由入口
扩展性：新增域文件（通用方法论_<域>域.md / 投行语言专项_<域>.md）后，重跑本脚本即自动纳入路由表，零改码。
计数口径与 parse_titles 对齐（域文件=条目数；W 系列=WD+WD_LIST 条目数，不用 h3 计数——h3 会把归组章节头误计入）；
入口模板含 frontmatter（type/domain/version/updated，updated 动态取各域文件 frontmatter 最大值）。

用法：
    python gen_entry.py [--methods-root <库根目录>] [--version <版本号>]

参数：
    --methods-root  方法论库根目录（默认 $METHODS_ROOT，或脚本上级目录）
    --version       写入入口 frontmatter 的版本号；默认读取现有入口 version 保持不变（防重跑版本回退）
"""
import argparse, io, os, re, glob, datetime
from pathlib import Path

_ap = argparse.ArgumentParser(description="生成方法论入口（路由薄壳）")
_ap.add_argument("--methods-root", default=os.environ.get("METHODS_ROOT", ""),
                 help="方法论库根目录（默认 $METHODS_ROOT，或脚本上级目录）")
_ap.add_argument("--version", default=None, help="入口版本号（默认读取现有入口 version，保持不变）")
_args = _ap.parse_args()
_ROOT = Path(_args.methods_root) if _args.methods_root else Path(__file__).resolve().parents[1]
METHODS = str(_ROOT / "methods")
ENTRY = os.path.join(METHODS, "通用方法论_最终版.md")


def _current_entry_version():
    """读取现有入口 frontmatter 的 version（缺省 v1）；防重跑把版本写回旧值"""
    try:
        with io.open(ENTRY, "r", encoding="utf-8") as f:
            for ln in f.read().splitlines()[:10]:
                m = re.match(r"version:\s*(\S+)", ln)
                if m:
                    return m.group(1)
    except Exception:
        pass
    return "v1"


ENTRY_VERSION = _args.version or _current_entry_version()

# 域文件命名规范：通用方法论_<域>域.md（以「域」字结尾，避开单案文件）+ 投行语言专项_*.md
DOMAIN_FILES = sorted(
    glob.glob(os.path.join(METHODS, "通用方法论_*域.md"))
) + sorted(glob.glob(os.path.join(METHODS, "投行语言专项_*.md")))


def count_entries(fname, content):
    """计数口径与 parse_v26_titles.py 一致：域文件=(N) 或 v37 身份编号条目；W 系列=WD 加粗 + WD_LIST 列表条目。"""
    if fname.startswith("投行语言专项"):
        n_wd = len(re.findall(r"^\*\*((?:WL|W)-[A-Za-z0-9\-·~]+)", content, re.M))
        n_wdl = len(re.findall(r"^-\s*\*\*((?:WL|W)-[A-Za-z0-9\-·~]+)\*\*", content, re.M))
        return n_wd + n_wdl
    # v37 身份编号 ### F-010001 + 兼容 v36 旧格式 ### （N）
    return len(re.findall(r"^### [FLIW]-\d{6}|^### （\d+）", content, re.M))


def max_updated(files):
    """取各域文件 frontmatter updated 最大值；无则用生成日。"""
    mx = ""
    for df in files:
        try:
            with io.open(df, "r", encoding="utf-8") as f:
                head = f.read(400)
            m = re.search(r"^updated:\s*(\d{4}-\d{2}-\d{2})", head, re.M)
            if m and m.group(1) > mx:
                mx = m.group(1)
        except OSError:
            pass
    return mx or datetime.date.today().strftime("%Y-%m-%d")


def extract_summaries():
    """从现有入口提取「版本摘要区」（> **vN ... 连续行块），生成时原样保留。
    幂等保证：重跑不回退摘要内容、不叠加层级；多层 > > 自动规范为单层 >。
    首次生成（无既有入口）时返回占位提示——摘要由蒸馏流程在升版时注入。"""
    try:
        with io.open(ENTRY, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError:
        return "> （版本摘要区：首次生成时为空；蒸馏升版时由流程在此注入最新摘要行）"
    out = []
    for ln in lines:
        if re.match(r"^>+\s*\*\*v\d", ln) or re.match(r"^>+\s*\*\*[^*]*版本", ln):
            out.append(re.sub(r"^>\s*>+\s*", "> ", ln))  # 多层 > 规范为单层
    return "\n".join(out) if out else "> （版本摘要区：暂无——蒸馏升版时由流程注入）"


summaries = extract_summaries()

rows = []
for df in DOMAIN_FILES:
    with io.open(df, "r", encoding="utf-8") as f:
        content = f.read()
    n_entries = count_entries(os.path.basename(df), content)
    n_lines = content.count("\n")
    size_kb = os.path.getsize(df) // 1024
    rows.append((os.path.basename(df), n_entries, n_lines, size_kb))

route_rows = "\n".join("| %s | %d 条 | %d 行 | ~%dKB |" % r for r in rows)
tot_kb = sum(r[3] for r in rows)
upd = max_updated(DOMAIN_FILES)

entry = """---
type: 路由入口
domain: 通用方法论
version: __VER__
updated: __UPD__
---

# 通用方法论：投行知识与写作范式（入口 __VER__）

__SUMMARIES__

> **条目标题目录见 `methods/方法论_条目标题目录.md`（脚本化生成，含「域文件 + 行号」定位）**
> **调用索引见 `methods/方法论调用索引.md`（28Q 域速查 + 全量映射）**

## 域路由表（自动生成 · 新增域文件自动纳入）

| 域文件 | 条目数 | 行数 | 大小 |
|--------|-------|------|------|
__ROUTE_ROWS__

## 读取链路（渐进披露）

问询问题 → 索引 28Q 速查 → 映射表定位条目编号 → 条目标题目录得「域文件 + 行号」 → Read offset/limit 定向读单条

单次读取：965KB → 入口 ~10KB + 单域 ≤230KB（按需行号段读仅 ~20KB）；token 全量载入降 90%+，定向读降 98%。

## 使用法

1. **定位条目**：先查 `方法论调用索引.md` 28Q 速查表 → 找 Q 编号 → 全量映射表找条目编号
2. **定向读**：按 `方法论_条目标题目录.md` 的「域文件 + 行号」，用 Read offset/limit 精准读单条
3. **蒸馏沉淀**：新条目按域追加至对应域文件尾部（编号顺延、不重排）；`daily_distill.py --refresh-index` 自动刷新索引/目录
4. **新增域**：新增 `通用方法论_<新域>域.md` 或 `投行语言专项_<新域>.md` 文件即可，路由表/索引/目录自动纳入（glob 发现，零改码）

## 归档索引

- `archive/通用方法论_最终版_全量备份_20260831.md` — 拆分前完整原文（铁律全保留）
- `archive/_版本说明归档_v16至v35_20260831.md` — 历史版本说明全文
- `archive/_行业对比表与蒸馏自检_20260831.md` / `_编号核对与S7建议_20260831.md` / `_专家引用与质量自评_20260831.md` — 过程性内容
"""

entry = entry.replace("__VER__", ENTRY_VERSION).replace("__UPD__", upd).replace("__SUMMARIES__", summaries)

with io.open(ENTRY, "w", encoding="utf-8") as f:
    f.write(entry.replace("__ROUTE_ROWS__", route_rows))
print("入口已重写: %d 个域文件（正文合计 ~%dKB）" % (len(rows), tot_kb))
for r in rows:
    print("  ", r[0], "| 条目", r[1], "| 行", r[2], "|", r[3], "KB")

# -*- coding: utf-8 -*-
"""解析方法论全部条目：
读「入口头 + glob 全部域文件」（通用方法论_*域.md + 投行语言专项_*.md，自动发现），
解析条目标题；输出 parsed_titles.txt（含「域文件」列，行号为域文件内行号）。
扩展性：新增域文件自动纳入解析，零改码。

用法：
    python parse_titles.py [--methods-root <库根目录>]

参数：
    --methods-root  方法论库根目录（默认 $METHODS_ROOT，或脚本上级目录）
"""
import argparse, re, io, os, glob
from pathlib import Path

_ap = argparse.ArgumentParser(description="解析方法论条目 → parsed_titles.txt")
_ap.add_argument("--methods-root", default=os.environ.get("METHODS_ROOT", ""),
                 help="方法论库根目录（默认 $METHODS_ROOT，或脚本上级目录）")
_args = _ap.parse_args()
_ROOT = Path(_args.methods_root) if _args.methods_root else Path(__file__).resolve().parents[1]
METHODS = str(_ROOT / "methods")
OUT = os.path.join(str(_ROOT / "scripts"), "parsed_titles.txt")

# 域文件命名规范：通用方法论_<域>域.md + 投行语言专项_*.md（避开单案文件与入口）
DOMAIN_FILES = sorted(
    glob.glob(os.path.join(METHODS, "通用方法论_*域.md"))
) + sorted(glob.glob(os.path.join(METHODS, "投行语言专项_*.md")))

# 2026-08-31 D 档修复：①按文件类型分流——域文件只认条目 h3；W 系列（投行语言专项_*）
# 的 （N）h3 是归组章节头（维度/族/批次），不解析为条目 ②pat_wd_list 扩展为通用 W- 前缀
# （原 W-D\d+ 为死正则，W 系列 267 条列表条目全被漏解析）
# 2026-08-31 v37 适配：①新增 pat_new 匹配新身份编号 ### F-010001 标题 ②W 系列正则支持 WL- 前缀
# （写作域新编号 W-01xxxx 与旧 W 系列 W-000xxx 同形，靠「按文件类型分流」天然区分：域文件走 pat_new，
#  投行语言专项文件走 pat_wd/pat_wd_list，二者不交叉）
pat_cn = re.compile(r"^### （(\d+)）(.*)$")                          # ### （N）条目（v36 旧格式，兼容）
pat_cn2 = re.compile(r"^### (财务|法律|行业|写作)（(\d+)）(.*)$")      # ### 财务（103）条目（v35 域前缀格式，兼容）
pat_new = re.compile(r"^### ([FLIW])-(\d{6})(.*)$")                  # ### F-010001 标题（v37 身份编号）
pat_wd = re.compile(r"^\*\*((?:WL|W)-[A-Za-z0-9\-·~]+)\s*[｜|:：]?\s*(.*?)\*\*")  # **WL-xxxxxx 标题**（W 系列条目）
pat_wd_list = re.compile(r"^-\s*\*\*((?:WL|W)-[A-Za-z0-9\-·~]+)\*\*[｜|:：]?\s*(.*)$")  # - **WL-010001**｜...（族归组列表条目）

entries = []
for fpath in DOMAIN_FILES:
    fname = os.path.basename(fpath)
    is_w = fname.startswith("投行语言专项")
    with io.open(fpath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for i, ln in enumerate(lines):
        s = ln.rstrip("\n")
        if is_w:
            # W 系列：只认 WD 加粗条目 + WD_LIST 列表条目；（N）h3 是归组章节头不解析
            m = pat_wd.match(s)
            if m:
                entries.append((fname, m.group(1), m.group(2).strip(), "WD", i + 1))
                continue
            m = pat_wd_list.match(s)
            if m:
                entries.append((fname, m.group(1), m.group(2).strip(), "WD_LIST", i + 1))
                continue
        else:
            m = pat_new.match(s)
            if m:
                # v37 身份编号：eid 输出完整编号（含前缀，如 F-010001）
                entries.append((fname, m.group(1) + "-" + m.group(2), m.group(3).strip(), "HEAD", i + 1))
                continue
            m = pat_cn.match(s)
            if m:
                entries.append((fname, "（" + m.group(1) + "）", m.group(2).strip(), "HEAD", i + 1))
                continue
            m = pat_cn2.match(s)
            if m:
                entries.append((fname, "（" + m.group(2) + "）", m.group(3).strip(), "HEAD", i + 1))
                continue

with io.open(OUT, "w", encoding="utf-8") as f:
    f.write("TOTAL=%d\n" % len(entries))
    for dom, eid, title, kind, lineno in entries:
        f.write("%s\t%s\t%s\t%s\t%d\n" % (dom, eid, title, kind, lineno))

print("TOTAL=%d (域文件 %d 个)" % (len(entries), len(DOMAIN_FILES)))
print("DONE")

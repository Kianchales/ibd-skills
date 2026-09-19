#!/usr/bin/env python3
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

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_ap = argparse.ArgumentParser(description="解析方法论条目 → parsed_titles.txt")
_ap.add_argument("--methods-root", default=os.environ.get("METHODS_ROOT", ""),
                 help="方法论库根目录（默认 $METHODS_ROOT，或脚本上级目录）")
_args = _ap.parse_args()
_ROOT = Path(_args.methods_root) if _args.methods_root else Path(__file__).resolve().parents[1]
METHODS = str(_ROOT / "methods")
OUT = os.path.join(str(_ROOT / "scripts"), "parsed_titles.txt")



def _require_library():
    """冷启动前置检查：未找到方法论库时给出清晰指引，而非堆栈崩溃"""
    import sys as _s
    if not os.path.isdir(METHODS):
        _s.stderr.write("✗ 未找到方法论库：%s\n" % METHODS)
        _s.stderr.write("  用法：--methods-root <库根目录>（或设环境变量 METHODS_ROOT）\n")
        _s.stderr.write("  首次使用：按 SKILL.md「库配置」四问引导接入你的库；库结构规范见 references/methods-guide.md\n")
        _s.exit(2)


_require_library()

# 域文件命名规范：通用方法论_<域>域.md + 投行语言专项_*.md（避开单案文件与入口）
# 2026-09-19 补：纳入 `分卷/*.md`——P 系列（PL-）与体例域批次卷（S-）的**条目正文唯一存放地**
# （2026-09-16 拆分后正文外置；此前 741 条 PL-/S- 条目缺席目录与索引 ⇒ 检索链路读不到）
DOMAIN_FILES = sorted(
    glob.glob(os.path.join(METHODS, "通用方法论_*域.md"))
) + sorted(glob.glob(os.path.join(METHODS, "投行语言专项_*.md"))) \
  + sorted(glob.glob(os.path.join(METHODS, "分卷", "*.md")))

# 2026-08-31 D 档修复：①按文件类型分流——域文件只认条目 h3；W 系列（投行语言专项_*）
# 的 （N）h3 是归组章节头（维度/族/批次），不解析为条目 ②pat_wd_list 扩展为通用 W- 前缀
# （原 W-D\d+ 为死正则，W 系列 267 条列表条目全被漏解析）
# 2026-08-31 v37 适配：①新增 pat_new 匹配新身份编号 ### F-010001 标题 ②W 系列正则支持 WL- 前缀
# （写作域新编号 W-01xxxx 与旧 W 系列 W-000xxx 同形，靠「按文件类型分流」天然区分：域文件走 pat_new，
#  投行语言专项文件走 pat_wd/pat_wd_list，二者不交叉）
pat_cn = re.compile(r"^### （(\d+)）(.*)$")                          # ### （N）条目（v36 旧格式，兼容）
pat_cn2 = re.compile(r"^### (财务|法律|行业|写作)（(\d+)）(.*)$")      # ### 财务（103）条目（v35 域前缀格式，兼容）
pat_new = re.compile(r"^### ([FLIWS])-(\d{6})(.*)$")   # 2026-09-19 补 S-（体例域批次卷）                  # ### F-010001 标题（v37 身份编号）
pat_wd = re.compile(r"^\*\*((?:WL|W)-[A-Za-z0-9\-·~]+)\s*[｜|:：]?\s*(.*?)\*\*")  # **WL-xxxxxx 标题**（W 系列条目）
pat_wd_list = re.compile(r"^-\s*\*\*((?:WL|W)-[A-Za-z0-9\-·~]+)\*\*[｜|:：]?\s*(.*)$")  # - **WL-010001**｜...（族归组列表条目）
# 2026-09-19 补：h3 形态 WL 条目 ### WL-150022（原 WL-150022）——2026-09-10「原写作域」并入批次的
# 书写形态（带「（原 XX）」留痕后缀，71/74 条正文直接起于 **方法论要点**、无标题文字）。
# 编号进 eid、kind 复用 "WD"，下游（gen_index/gen_toc/gen_entry）零改动。
# 注意：h3 归组章节头（### （1）遣词维度 / ### 族 1｜…）不以 WL- 开头，故此规则不会误收章节头。
pat_wd_h3 = re.compile(r"^### ((?:WL|W|PL)-\d{6})\s*(.*)$")   # 2026-09-19 补 PL-（P 系列分卷）


def _fallback_title(lines, i):
    """h3 条目无标题文字时的兜底：取正文「**方法论要点**」段首句（截断 40 字）"""
    for j in range(i + 1, min(i + 15, len(lines))):
        t = lines[j].strip()
        if t.startswith("**方法论要点"):
            body = re.sub(r"^\*\*方法论要点[^*]*\*\*[：:]\s*", "", t)
            body = re.split(r"[。；]", body)[0].strip()
            if body:
                return body[:40] + ("…" if len(body) > 40 else "")
    return "（标题待补）"


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
            m = pat_wd_h3.match(s)
            if m:
                _eid = m.group(1)
                # 剥离尾部「（原 XX）」留痕后缀 → 取标题；为空则取要点首句兜底
                _title = re.sub(r"（原[^）]*）\s*$", "", m.group(2)).strip()
                if not _title:
                    _title = _fallback_title(lines, i)
                entries.append((fname, _eid, _title, "WD", i + 1))
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

d = os.path.dirname(OUT)
if d:
    os.makedirs(d, exist_ok=True)
with io.open(OUT, "w", encoding="utf-8") as f:
    f.write("TOTAL=%d\n" % len(entries))
    for dom, eid, title, kind, lineno in entries:
        f.write("%s\t%s\t%s\t%s\t%d\n" % (dom, eid, title, kind, lineno))

print("TOTAL=%d (域文件 %d 个)" % (len(entries), len(DOMAIN_FILES)))
print("DONE")

#!/usr/bin/env python3
"""方法论全库健康护栏（18 项检查 · 防结构漂移）

用法：
    python check_methods_health.py [--methods-root <工作区根>] [--quiet]

参数：
    --methods-root  工作区根（= 库根；其下应有 methods/ 子目录）；默认取环境变量 METHODS_ROOT，
                    未设置时按脚本所在目录的上级推断（脚本随库存放于 <库根>/scripts/ 时零参数可用）
    --quiet         只输出异常项

检查项：
1.  frontmatter 完整性   正文 md（排除 archive/ 与自动生成白名单）必须：首行 ---、有闭合 ---、字段 key: value、正文首行 #
2.  空 h3               ^###\\s*$ 不得存在（标题后无内容）
3.  编号健康            全局唯一性（跨文件）+ 族内连续（每域每族 1..N）+ 登记表一致（登记表编号均存在）
4.  路由表一致性        入口路由表「条目数」列 vs 实算（与 parse/gen_entry 同口径，防 h3 计数漂移）
5.  parsed TOTAL 一致性 parsed_titles.txt 首行 TOTAL= vs 实算（防 parse 陈旧 → 目录/索引滞后）
6.  回写清单一致性      汇总行 = 明细行数、进度行 = 已销项数（防「追加新轮次后未回填汇总」）
7.  W 编号唯一性        W 系列条目编号不得重复（支持 WL- 格式）
8.  交叉引用有效性      正文引用 [FLIW]L?-\\d{6} 必须存在（旧格式历史注记跳过）
9.  域文件体积警戒线    单域文件 >300KB 触发 WARN + 族级拆分预案提示（防二阶膨胀复发）
10. 索引行号定位抽查    编号 →「文件 + 行号」随机抽查 12 条须逐条命中（防改内容未刷索引的静默漂移）
11. 单案产出内容范围    必备四域（F≥8／L≥7／I≥8／W 章存在）逐案齐备；缺项 WARN 并登记补蒸
                        （判据 → references/distill-methods.md §「单案产出内容范围与缺项补蒸」）
12. I-CL 条目位置       行业合并版 I-CL{类号}-{序} 须落在共通章范围内（首个「子行业特有章」之前）
13. 候选段残留          域文件/语言专项不得含「## 批次增量：」段；合并版不得含候选标题形态（防回潮）
                        （修复规程 → references/govern/fix-tools.md）
14. 骨架合规            单案须齐七节 h2、行业合并版须齐四段（缺项 WARN，不阻断存量）
                        （骨架模板 → references/templates/README.md）
15. 标签形态集一致性    「回写器产出形态 ⊆ 契约校验器受理形态」元自检（判 I-0088 后新增，防盲区复发）
                        单案 frontmatter 另含**必填字段**校验（type/case/case_no，见第 1 项）
16. 撤除载体不得重建    已撤除载体目录存在即 ERROR（`30_行业版/单份细分版/`；2026-09-23 WO-08 撤除，
                        内容归位单案「行业研究详述（叙述型）」章）—— 防无人值守按旧提示词重建

退出码：0 = 全部通过（WARN 不阻塞）；1 = 存在 ERROR
"""
import argparse, io, json, os, re, glob, random, sys
from pathlib import Path

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_ap = argparse.ArgumentParser(description="方法论全库健康护栏（19 项检查）")
_ap.add_argument("--methods-root", default=os.environ.get("METHODS_ROOT", ""),
                 help="工作区根（= 库根，其下含 methods/；默认 $METHODS_ROOT，或脚本上级目录）")
_ap.add_argument("--quiet", action="store_true", help="只输出异常项")
_ap.add_argument("--json", action="store_true", help="输出结构化 JSON（供上层消费）")
_args = _ap.parse_args()

import os as _lo, sys as _ls
_ls.path.insert(0, _lo.path.dirname(_lo.path.abspath(__file__)))
from _lib.layout import (resolve as _layout_resolve, ENTRY_FILE, PARSED_FILE, TOC_FILE,
                         DOMAIN_SIZE_WARN_BYTES, SKIP_DIRS, GENERATED_BASENAMES,
                         MERGED_MAP, VOLUME_NAME, LANG_W_FILE, DOMAIN_GLOB, LANG_GLOB,
                         SINGLE_NAME, DIR_INDUSTRY_MERGED, library_files)
_ROOT, METHODS, SCRIPTS = _layout_resolve(_args.methods_root)
# ---------- 编号提取正则登记表（**单一事实源** · 第 17 项元自检对象） ----------
# 铁律：凡「**短前缀 ⊂ 长前缀**」的编号族（`L-` ⊂ `WL-`、`I-` ⊂ `WL-`、`L-` ⊂ `PL-`），
#   提取正则**必须带左界 `(?<![A-Za-z])`**；行首锚定 `^### ` 者天然满足。
# 背景：同族已四犯（I-0088／0091／0092／0094）—— `[FLI]-\d{6}` 会把 `WL-010020` 误截为
#   `L-010020`（实测 354 个假阳性）；`([FLIW]L?-\d{6})` 无左界会把 `WL-180035` 匹配两次。
RX_ID_ANY   = r"(?<![A-Za-z])[FLIW]L?-\d{6}"    # 任意编号（域／族卷／语言专项）
RX_ID_LANG  = r"(?<![A-Za-z])(?:WL|W)-[A-Za-z0-9\-·~]+"  # W 系列编号
RX_ID_REGT  = r"(?<![A-Za-z])[FLI]-\d{6}"       # 登记表主库编号（F/L/I）
RX_ID_REGTW = r"(?<![A-Za-z])WL-\d{6}"          # 登记表语言专项编号
RX_ID_HEAD  = r"^### ([FLIW])-(\d{6})"          # 标题编号（行首锚定）
RX_ID_H3CNT = r"^### [FLIWS]-\d{6}|^### （\d+）"  # h3 条目计数（行首锚定）
_ID_RX = [("任意编号", RX_ID_ANY), ("W 系列编号", RX_ID_LANG), ("登记表主库编号", RX_ID_REGT),
          ("登记表语言专项编号", RX_ID_REGTW), ("标题编号", RX_ID_HEAD), ("h3 条目计数", RX_ID_H3CNT)]

ENTRY = os.path.join(METHODS, ENTRY_FILE)
PARSED = os.path.join(SCRIPTS, PARSED_FILE)



def _require_library():
    """冷启动前置检查：未找到方法论库时给出清晰指引，而非堆栈崩溃"""
    import sys as _s
    if not os.path.isdir(METHODS):
        _s.stderr.write("✗ 未找到方法论库：%s\n" % METHODS)
        _s.stderr.write("  用法：--methods-root <工作区根>（或设环境变量 METHODS_ROOT）\n")
        _s.stderr.write("  首次使用：按 SKILL.md「库配置」四问引导接入你的库；库结构规范见 references/methods-guide.md\n")
        _s.exit(2)


_require_library()

# 域文件体积警戒线：超过即 WARN 并提示拆分预案

# 自动生成/工具文件白名单（合法无 frontmatter）
WHITELIST = {
    "README.md",
    "方法论调用索引_备份_20260831.md",
    "编号登记表.md",
    MERGED_MAP,
} | set(GENERATED_BASENAMES)

ERRORS, WARNS = [], []


def count_entries(fname, content):
    """与 parse_titles.py / gen_entry.py 同口径：域文件=(N) 或 v37 身份编号条目；W 系列=WD+WD_LIST+h3。"""
    if fname.startswith("投行语言专项"):
        n_wd = len(re.findall(r"^\*\*((?:WL|W|PL)-[A-Za-z0-9\-·~]+)", content, re.M))
        n_wdl = len(re.findall(r"^-\s*\*\*((?:WL|W|PL)-[A-Za-z0-9\-·~]+)\*\*", content, re.M))
        n_h3 = len(re.findall(r"^### ((?:WL|W|PL)-\d{6})", content, re.M))   # h3 形态（2026-09-19 补 PL-）
        return n_wd + n_wdl + n_h3
    # 2026-09-19 补 S-（体例域批次卷）
    return len(re.findall(RX_ID_H3CNT, content, re.M))


# ---------- 收集全部 md ----------
# 检查范围 = 方法论正文本体：methods 根目录活跃文件 + 30_行业版/单份细分版/（活跃子集）
# 排除：archive/（历史归档）、60_notes/（历史蒸馏笔记）、
#     50_分卷/（域文件分卷产物，无独立 # 标题结构，不适用 frontmatter 后须有 h1 的规则；2026-09-19 补）
md_files = []
for root, dirs, files in os.walk(METHODS):
    parts = root.split(os.sep)
    if any(b in SKIP_DIRS for b in parts):
        continue
    for fn in files:
        if fn.endswith(".md"):
            md_files.append(os.path.join(root, fn))
md_files.sort()

# ---------- 1. frontmatter 完整性 ----------
fm_checked = 0
for p in md_files:
    fn = os.path.basename(p)
    if fn in WHITELIST:
        continue
    rel = os.path.relpath(p, METHODS)
    with io.open(p, encoding="utf-8") as f:
        lines = f.read().splitlines()
    if not lines or lines[0].strip() != "---":
        ERRORS.append("frontmatter 缺失: %s" % rel)
        continue
    close = None
    for i in range(1, min(len(lines), 12)):
        if lines[i].strip() == "---":
            close = i
            break
    if close is None or close < 2:
        ERRORS.append("frontmatter 未闭合: %s" % rel)
        continue
    block = lines[1:close]
    for b in block:
        if not re.match(r"^[\w]+\s*:", b.strip()):
            ERRORS.append("frontmatter 字段格式异常 [%s]: %s" % (rel, b))
    j = close + 1
    while j < len(lines) and not lines[j].strip():
        j += 1
    if j >= len(lines) or not lines[j].startswith("#"):
        ERRORS.append("frontmatter 后无 # 标题: %s" % rel)
    # 2026-09-23（R-6）单案 frontmatter **必填字段**：原实现只查形态（`---` 闭合 + key: value）不查字段集
    #   ⇒ 实测 82 个单案仅 type/case/case_no 三个字段全员齐备，board/stage/prospectus 各仅 1–2 个，
    #     「新案该写哪些字段」全凭习惯。必填三项取自实测共识 ＋ templates/tpl_单案范式文件.md。
    if rel.replace(os.sep, "/").startswith(SINGLE_NAME + "/"):
        keys = set(re.findall(r"(?m)^([A-Za-z_][\w]*)\s*:", "\n".join(block)))
        miss_req = [k for k in ("type", "case", "case_no") if k not in keys]
        if miss_req:
            ERRORS.append("单案 frontmatter 缺必填字段 %s: %s（骨架见 references/templates/）"
                          % ("/".join(miss_req), rel))
    fm_checked += 1

# ---------- 2. 空 h3 ----------
for p in md_files:
    rel = os.path.relpath(p, METHODS)
    with io.open(p, encoding="utf-8") as f:
        lines = f.read().splitlines()
    for i, l in enumerate(lines):
        s = l.strip()
        if re.match(r"^###\s*$", s) or re.match(r"^###\s*[：:]\s*$", s):
            ERRORS.append("空 h3: %s L%d" % (rel, i + 1))

# ---------- 3. 编号健康（v37 身份编号：域前缀+族号2位+族内序号4位） ----------
# 3a. 全局唯一性（跨文件）+ 3b. 族内连续（每域每族 seq 1..N）
# 3c. 登记表一致（登记表编号必须存在于域文件/W系列标题；文件可多于登记表=蒸馏新增）
all_ids = {}   # "F-010001" -> rel 文件（含域文件 ### 标题 + W 系列 ** 条目）
fam_seqs = {}  # (rel, prefix, fam) -> [seqs]
for p in md_files:
    fn = os.path.basename(p)
    rel = os.path.relpath(p, METHODS)
    with io.open(p, encoding="utf-8") as f:
        lines = f.read().splitlines()
    if re.match(r"^通用方法论_[^_]+域(?:[_·]卷\d+(?:-\d+)?.*)?\.md$", fn):
        # 域文件 ＋ **族卷**（2026-09-23 按族外置：正文唯一存放地移到
        # `50_分卷/通用方法论_<域>_卷NN_<族名>.md`；旧判据 `fn.endswith("域.md")` 会漏掉族卷
        # ⇒ 编号不进 all_ids ⇒ 第 8 项「交叉引用」全库报错。判据改为「域文件 or 域族卷」）
        # v37 标题 ### F-010001xxx；兼容旧格式 ### （N）
        old_nums = []
        for l in lines:
            s = l.strip()
            m = re.match(RX_ID_HEAD, s)
            if m:
                prefix, full = m.group(1), m.group(2)
                new_id = prefix + "-" + full
                if new_id in all_ids:
                    ERRORS.append("编号跨文件重复: %s 同时出现在 %s 与 %s" % (new_id, all_ids[new_id], rel))
                all_ids[new_id] = rel
                fam_seqs.setdefault((rel, prefix, int(full[:2])), []).append(int(full[2:]))
                continue
            m = re.match(r"^### （(\d+)）", s)
            if m:
                old_nums.append(int(m.group(1)))
        if old_nums:  # 旧格式兼容检查（迁移遗漏兜底）
            if old_nums != list(range(1, max(old_nums) + 1)):
                missing = sorted(set(range(1, max(old_nums) + 1)) - set(old_nums))
                ERRORS.append("编号不连续(旧格式) %s: %d 条，缺 %s" % (rel, len(old_nums), missing[:10]))
    elif fn.startswith("投行语言专项"):
        # W 系列：粗体 + 列表条目 + h3 形态（### WL-xxxxxx）编号进唯一性集合
        # （族内不要求连续——主题族框架跳号天然免疫；h3 归组章节头不以 WL- 开头，不会误收；2026-09-19 补）
        content = "\n".join(lines)
        wids = list(re.finditer(r"^\*\*((?:WL|W)-[A-Za-z0-9\-·~]+)", content, re.M)) + \
               list(re.finditer(r"^-\s*\*\*((?:WL|W)-[A-Za-z0-9\-·~]+)\*\*", content, re.M)) + \
               list(re.finditer(r"^### ((?:WL|W)-\d{6})", content, re.M)) + \
               list(re.finditer(r"^### ((?:PL)-\d{6})", content, re.M))   # 2026-09-23 补 PL-（按族外置后 PL 族卷）
        for m in wids:
            wid = m.group(1)
            if wid in all_ids:
                ERRORS.append("编号跨文件重复: %s 同时出现在 %s 与 %s" % (wid, all_ids[wid], rel))
            all_ids[wid] = rel
    elif rel.replace(os.sep, "/").startswith(DIR_INDUSTRY_MERGED):
        # 行业合并版「类内共通条目」I-CL{类号2位}-{序}（2026-09-23 立 · 原裸 C-N）
        # 背景：该层此前无编号规则、不被任何解析器识别（隐形条目）⇒ 本次纳入唯一性 + 类内连续性
        # 2026-09-23 加严：**位置校验** —— 条目须落在「共通章」范围内（首个「子行业特有章」标题之前）。
        #   背景：实测发现 3 文件 12 条 I-CL 被串到子行业章内／章尾（智能装备 I-CL06-02/03/04、
        #   电子材料 I-CL07-01~09、汽车电子链 I-CL04-01~05），而旧校验只查「唯一＋连续」不查位置 ⇒ 门禁盲区。
        _sub_head = None
        for _i, _l in enumerate(lines):
            if re.match(r"^#{1,3}\s*\S*子行业特有", _l) or re.match(r"^##\s*子行业：", _l):
                _sub_head = _i
                break
        for _i, l in enumerate(lines):
            if _sub_head is not None and _i > _sub_head:
                continue  # 位于子行业章之后 ⇒ 由下方位置校验分支统一报错，避免重复解析
            m = re.match(r"^### I-CL(\d{2})-(\d+)(?![0-9])", l.strip())
            if not m:
                continue
            cid = "I-CL%s-%s" % (m.group(1), m.group(2))
            if len(m.group(2)) != 2:
                ERRORS.append("I-CL 序号位宽须 2 位（前导零）: %s @ %s" % (cid, rel))
            if cid in all_ids:
                ERRORS.append("编号跨文件重复: %s 同时出现在 %s 与 %s" % (cid, all_ids[cid], rel))
            all_ids[cid] = rel
            fam_seqs.setdefault((rel, "I-CL", int(m.group(1))), []).append(int(m.group(2)))
        # 位置校验：子行业章之后的 I-CL 条目一律报错（含仍计入编号唯一性）
        if _sub_head is not None:
            for _i in range(_sub_head + 1, len(lines)):
                m = re.match(r"^### I-CL(\d{2})-(\d+)(?![0-9])", lines[_i].strip())
                if not m:
                    continue
                cid = "I-CL%s-%s" % (m.group(1), m.group(2))
                ERRORS.append("I-CL 条目位置错误（应位于共通章、实测在子行业章之后）: %s @ %s L%d"
                              % (cid, rel, _i + 1))
                if cid not in all_ids:
                    all_ids[cid] = rel
                    fam_seqs.setdefault((rel, "I-CL", int(m.group(1))), []).append(int(m.group(2)))

for (rel, prefix, fam), seqs in sorted(fam_seqs.items()):
    seqs_sorted = sorted(seqs)
    if seqs_sorted != list(range(1, len(seqs_sorted) + 1)):
        missing = sorted(set(range(1, max(seqs_sorted) + 1)) - set(seqs_sorted))
        ERRORS.append("族内编号不连续 %s %s-%02d: %d 条，缺 %s" % (rel, prefix, fam, len(seqs_sorted), missing[:10]))

# 3c. 登记表一致（自动发现库根 tasks/ 下的编号登记表；兼容历史命名）
_tasks_dir = os.path.join(os.path.dirname(os.path.dirname(SCRIPTS)), "tasks")
_reg_candidates = sorted(glob.glob(os.path.join(_tasks_dir, "*编号登记表*.md"))) if os.path.isdir(_tasks_dir) else []
reg_path = _reg_candidates[-1] if _reg_candidates else ""
if os.path.exists(reg_path):
    with io.open(reg_path, encoding="utf-8") as f:
        reg_txt = f.read()
    # 2026-09-23 修：`[FLI]-\d{6}` 会把 `WL-010020` 误截为 `L-010020`（实测 354 个假阳性
    #   ⇒ 与 all_ids 比对时伪报「登记表编号缺失」）。加左界 `(?<![A-Za-z])` 排除前接字母的形态。
    reg_ids = set(re.findall(RX_ID_REGT, reg_txt)) | set(re.findall(RX_ID_REGTW, reg_txt))
    # 写作域段：| （N） | W-01xxxx | → 加入（避免与 W 系列 WL- 混淆，写作域编号前两位=族号 01-18）
    reg_ids |= set(re.findall(r"\|\s*（\d+）\s*\|\s*(W-\d{6})\s*\|", reg_txt))
    # 投行语言段：| W-00xxxx | WL-xxxxxx | → W-00 旧号不收集（其新号 WL- 已在上行收集）
    missing_reg = sorted(i for i in reg_ids if i not in all_ids)
    if missing_reg:
        ERRORS.append("登记表编号在域文件中缺失 %d 个: %s（登记表与正文漂移，需核对迁移）" % (len(missing_reg), missing_reg[:10]))

# ---------- 4. 路由表一致性 ----------
if os.path.exists(ENTRY):
    with io.open(ENTRY, encoding="utf-8") as f:
        entry_txt = f.read()
    route = {}
    for m in re.finditer(r"^\|\s*(通用方法论_\S+?\.md|投行语言专项_\S+?\.md)\s*\|\s*(\d+)\s*条", entry_txt, re.M):
        route[m.group(1)] = int(m.group(2))
    # C3b：域文件／语言专项已分居 `10_跨案域/`、`20_语言专项/` ⇒ 用 basename 反查实存路径
    _by_base = {os.path.basename(x): x for x in library_files(METHODS)}
    for fn, declared in route.items():
        p = _by_base.get(fn) or os.path.join(METHODS, fn)
        if not os.path.exists(p):
            # 2026-09-19：路由表条目可能位于 50_分卷/ 子目录
            p = os.path.join(METHODS, VOLUME_NAME, fn)
        if not os.path.exists(p):
            ERRORS.append("路由表指向不存在文件: %s" % fn)
            continue
        with io.open(p, encoding="utf-8") as f:
            actual = count_entries(fn, f.read())
        if actual != declared:
            ERRORS.append("路由表计数漂移 %s: 表内 %d 条 vs 实算 %d 条（h3 误计或条目增减未刷新）" % (fn, declared, actual))

# ---------- 5. parsed TOTAL 一致性 ----------
if os.path.exists(PARSED):
    with io.open(PARSED, encoding="utf-8") as f:
        first = f.readline().strip()
    m = re.match(r"TOTAL=(\d+)", first)
    total_actual = 0
    _scan = sorted(glob.glob(os.path.join(METHODS, DOMAIN_GLOB))) \
          + sorted(glob.glob(os.path.join(METHODS, LANG_GLOB))) \
          + sorted(glob.glob(os.path.join(METHODS, VOLUME_NAME, "*.md")))   # 2026-09-19 纳入分卷
    for df in _scan:
        with io.open(df, encoding="utf-8") as f:
            total_actual += count_entries(os.path.basename(df), f.read())
    if m and int(m.group(1)) != total_actual:
        ERRORS.append("parsed_titles 陈旧: TOTAL=%s vs 实算 %d（需重跑 parse → gen_toc → gen_index）" % (m.group(1), total_actual))

# ---------- 6. 回写清单一致性（2026-09-19 加：防「追加新轮次后汇总未回填」） ----------
_WS = os.path.dirname(METHODS)
CL = os.path.join(_WS, "tasks", "建议回写清单.md")
if not os.path.exists(CL):
    CL = os.path.join(_WS, "state", "建议回写清单.md")
cl_checked = 0
if os.path.exists(CL):
    with io.open(CL, encoding="utf-8") as f:
        cl = f.read()
    rows = [x for x in cl.splitlines() if x.startswith("| [")]
    done = sum(1 for x in rows if x.startswith("| [x]"))
    m_sum = re.search(r"合计回写候选[：:]\s*(\d+)", cl)
    m_prog = re.search(r"已回写\s*(\d+)\s*[/／]\s*待回写\s*(\d+)", cl)
    if m_sum and int(m_sum.group(1)) != len(rows):
        ERRORS.append("回写清单汇总口径与明细不符: 汇总 %s 条 vs 明细 %d 行（追加新轮次后须回填汇总）"
                      % (m_sum.group(1), len(rows)))
    if m_prog:
        if int(m_prog.group(1)) != done:
            ERRORS.append("回写清单进度行与状态列不符: 进度记已回写 %s vs 状态列 [x] %d"
                          % (m_prog.group(1), done))
        if int(m_prog.group(1)) + int(m_prog.group(2)) != len(rows):
            ERRORS.append("回写清单进度行合计与明细不符: %s＋%s vs %d 行"
                          % (m_prog.group(1), m_prog.group(2), len(rows)))
    cl_checked = len(rows)

# ---------- 7. W 编号唯一性（v37：WL- 新格式 + 兼容 W- 旧格式） ----------
for df in sorted(glob.glob(os.path.join(METHODS, LANG_GLOB))):
    with io.open(df, encoding="utf-8") as f:
        content = f.read()
    ids = re.findall(r"^\*\*((?:WL|W)-[A-Za-z0-9\-·~]+)", content, re.M) + \
          re.findall(r"^-\s*\*\*((?:WL|W)-[A-Za-z0-9\-·~]+)\*\*", content, re.M) + \
          re.findall(r"^### ((?:WL|W)-\d{6})", content, re.M)   # 2026-09-19 补 h3 形态
    from collections import Counter
    dups = {k: v for k, v in Counter(ids).items() if v > 1}
    if dups:
        ERRORS.append("W 编号重复 %s: %s" % (os.path.basename(df), dups))

# ---------- 8. 交叉引用有效性（v37 新增，D6 裁定） ----------
# 范围：5 个方法论正文本体；规则：引用编号（[FLIW]L?-\d{6}）必须存在于 all_ids；
# 旧 W 系列形态（W-00xxxx）为历史注记/索引区保留项，跳过不报。
# 2026-09-23 补：纳入 `50_分卷/`（按族外置后 F/L/I 条目正文在此 ⇒ 卷内引用亦须受检）
for df in sorted(glob.glob(os.path.join(METHODS, DOMAIN_GLOB))) + sorted(glob.glob(os.path.join(METHODS, LANG_GLOB))) \
        + sorted(glob.glob(os.path.join(METHODS, VOLUME_NAME, "*.md"))):
    rel = os.path.relpath(df, METHODS)
    with io.open(df, encoding="utf-8") as f:
        lines = f.read().splitlines()
    for i, l in enumerate(lines):
        s = l.strip()
        if not s or s.startswith("#") or s.startswith("|") or s.startswith(">"):
            continue
        # 2026-09-23 修：`([FLIW]L?-\d{6})` 无左界 ⇒ `WL-180035` 会被匹配**两次**
        #   （`WL-180035` 与错位起的 `L-180035`）⇒ 同一引用重复报错。加左界 `(?<![A-Za-z])`。
        for m in re.finditer("(" + RX_ID_ANY + ")", s):
            ref = m.group(1)
            if re.match(r"^W-00", ref):  # 旧 W 系列编号（历史注记/索引保留）
                continue
            if ref not in all_ids:
                ERRORS.append("交叉引用无效 %s L%d: %s（目标编号不存在，需核对登记表/迁移）" % (rel, i + 1, ref))

# ---------- 9. 域文件体积警戒线（2026-09-03 新增） ----------
# 对象：四域文件 + 投行语言专项（与拆分代次同一口径）；超线 WARN 不阻塞，提示族级拆分预案
# 2026-09-23 补：纳入 `50_分卷/`——按族外置后体积增长转移到族卷，不纳入即「拆完即失守」
for df in sorted(glob.glob(os.path.join(METHODS, DOMAIN_GLOB))) + sorted(glob.glob(os.path.join(METHODS, LANG_GLOB))) \
        + sorted(glob.glob(os.path.join(METHODS, VOLUME_NAME, "*.md"))):
    size = os.path.getsize(df)
    if size > DOMAIN_SIZE_WARN_BYTES:
        WARNS.append(
            "域/卷文件体积超警戒线 %s: %.0fKB > 300KB——2026-09-23「按族外置」已落地（族卷＝"
            "`50_分卷/通用方法论_<域>_卷NN_<族名>.md`，族号＝卷号）；本项现**含族卷** ⇒ 单卷超线时"
            "按同法再拆（族内子主题再分卷，或族内批次块外置）；蒸馏只追加不重排" % (os.path.basename(df), size / 1024)
        )

# ---------- 10. 索引行号定位抽查（2026-09-19 新增） ----------
# 背景：编号 →「文件 + 行号」是定向读取的唯一键；改内容未刷索引 ⇒ 行号漂移 ⇒ 定向读会读到
# **别的条目且不报错**（静默缺陷）。既有各项只校验「条目数」一致，不校验行号指向。
_TOC = os.path.join(METHODS, TOC_FILE)
if os.path.exists(_TOC):
    _rows, _grp, _appx = [], None, None
    for _ln in io.open(_TOC, encoding="utf-8", errors="replace").read().splitlines():
        if _ln.startswith("## "):
            _tt = _ln[3:].strip()
            _am = re.match(r"^附：((?:W|P)L?) 系列", _tt)   # 2026-09-23 WO-06：兼容 WL/PL 系列
            _appx = _am.group(1) if _am else None
            _grp = None if _appx else re.sub(r"（.*?）$", "", _tt).strip().strip("` ")
            continue
        _m = re.match(r"^\| ([A-Z]{1,3}-\d{6}) \| (.+?) \| (.+?) \|$", _ln)
        if not _m:
            continue
        _cells = [c.strip() for c in _ln.strip().strip("|").split("|")]
        if len(_cells) == 4 and _cells[3].isdigit():
            _rows.append((_m.group(1), _cells[2], int(_cells[3])))
        elif len(_cells) == 3 and _cells[2].isdigit():
            if _grp:
                _rows.append((_m.group(1), _grp, int(_cells[2])))
            elif _appx in ("W", "WL"):
                _rows.append((_m.group(1), LANG_W_FILE, int(_cells[2])))
    if _rows:
        random.seed(20260919)
        _miss = []
        for _eid, _fn, _lnno in random.sample(_rows, min(12, len(_rows))):
            _p = _by_base.get(_fn) or next((x for x in (os.path.join(METHODS, _fn),
                                                        os.path.join(METHODS, VOLUME_NAME, _fn))
                                            if os.path.exists(x)), None)
            if _p is None:
                _miss.append("%s(文件缺失)" % _eid)
                continue
            _ls = io.open(_p, encoding="utf-8", errors="replace").read().splitlines()
            if not (0 < _lnno <= len(_ls)) or _eid not in _ls[_lnno - 1]:
                _miss.append("%s→%s:%d" % (_eid, _fn, _lnno))
        if _miss:
            ERRORS.append("索引行号定位漂移: 抽查 12 条中 %d 条未命中（编号 → 文件:行号 不符；"
                          "多为改内容后未刷索引）—— %s" % (len(_miss), "、".join(_miss[:5])))
        _locator_checked = len(_rows)
    else:
        _locator_checked = 0
else:
    _locator_checked = 0

# ---------- 11. 单案产出内容范围（2026-09-23 新增 · 用户裁定「确定单案蒸馏内容范围」） ----------
# 判据：必备四域（财务/法律/行业/写作范式）逐案齐备；条数下限取实测最小值（F>=8 / L>=7 / I>=8）。
# 缺项报 WARN（不阻断）——历史案量大，须可反复补蒸，穷尽前不让门禁恒红（同 I-0022 判据失效模式）。
# 事实源 -> references/distill-methods.md 节「单案产出内容范围与缺项补蒸」
_SGL = os.path.join(METHODS, SINGLE_NAME)
_SCOPE_MIN = (("财务", "F", 8), ("法律", "L", 7), ("行业", "I", 8))
_scope_checked = 0
if os.path.isdir(_SGL):
    _scope_gap = []
    for _f in sorted(os.listdir(_SGL)):
        if not _f.endswith(".md") or not _f.startswith("通用方法论_"):
            continue
        _scope_checked += 1
        _t = io.open(os.path.join(_SGL, _f), encoding="utf-8", errors="replace").read()
        _secs = re.split(r"(?m)^## (?![#\s])", _t)
        _lack = []
        for _dom, _L, _mn in _SCOPE_MIN:
            _cnt = 0
            for _s in _secs:
                _head = _s.split("\n", 1)[0].lstrip()
                # 章识别：含域词 ／ 或以该域编号开头（「条目直列式」，如 `## F-AN0018-01 …`）
                if _dom not in _head and not _head.startswith(_L + "-AN"):
                    continue
                # 三重计数取大：### 条目数 ／ 域编号 token 数 ／ 章内体量粗估（500 字≈1 条）
                _cnt += max(len(re.findall(r"(?m)^#{3,4} ", _s)),
                            len(set(re.findall(_L + r"-AN\d+-\d+", _s))),
                            len(re.findall(r"(?<![0-9A-Za-z])" + _L + r"[-A-Z]{0,4}-?\d{1,2}(?![0-9])", _s)),
                            len(_s) // 500)
            if _cnt < _mn:
                _lack.append("%s%d/%d" % (_L, _cnt, _mn))
        if not re.search(r"W-AN\d+", _t) and not re.search(r"(?m)^#{1,3}[^\n]*写作范式", _t):
            _lack.append("W缺")
        if _lack:
            _short = _f.replace("通用方法论_投行知识与写作范式_", "").replace(".md", "")
            _scope_gap.append("%s(%s)" % (_short, " ".join(_lack)))
    if _scope_gap:
        WARNS.append("单案内容范围缺口 %d/%d 案（必备四域不全或有薄域；可反复补蒸）—— %s"
                     % (len(_scope_gap), _scope_checked, "、".join(_scope_gap[:8])))

# ---------- 13. 候选段残留（未归位形态 · 2026-09-23 新增） ----------
# 背景：库内历史堆积两类「未归位候选段」——① 行业合并版尾部「批次增量」候选条目（旧体系 S6b 分流产物）
#       ② 主库（域文件/语言专项）尾部「批次增量」候选条目明细段（带「拟编号」或规范体例但正式章查无）。
#       2026-09-23 已全量清账（合并版落号并入共通章/子行业节；主库 61 条转正入正式章）。
# 本项防回潮，两类判据：
#   判据 A —— 域文件（10_跨案域/）与语言专项（20_语言专项/）不得含 `## 批次增量：` 段
#             （`50_分卷/` 同类标题是「卷的批次容器标题」＝既有架构，已由 SKIP_DIRS 排除，不在本项范围）
#   判据 B —— 行业合并版不得含候选标题形态（建议 X｜／候选 N：／增量 N｜／[A-Z]\d+【…】）
# 修复：合并版 → 落号并入共通章或子行业节；主库 → 转正入正式章（三步规程见 references/govern/fix-tools.md）
_CAND_HEAD = re.compile(r"^#{3,4}\s*(?:【[^】]*】)?\s*(?:候选\s*\d+\s*[：:]|建议\s*[A-Z]\s*[｜|]|增量\s*\d+\s*[｜|]|[A-Z]\d+\s*【)")
_BATCH_SEG = re.compile(r"^## 批次增量：")
_resid = []
for _f in md_files:
    _rel = os.path.relpath(_f, METHODS).replace(os.sep, "/")
    with io.open(_f, encoding="utf-8") as _fh:
        _ls = _fh.read().split("\n")
    if _rel.startswith("10_跨案域/") or _rel.startswith("20_语言专项/"):
        for _i, _l in enumerate(_ls, 1):
            if _BATCH_SEG.match(_l):
                _resid.append("%s:%d 主库批次增量段未转正" % (_rel, _i))
    if _rel.startswith(DIR_INDUSTRY_MERGED):
        for _i, _l in enumerate(_ls, 1):
            if _CAND_HEAD.match(_l.strip()):
                _resid.append("%s:%d 合并版候选条目未归位" % (_rel, _i))
if _resid:
    ERRORS.append("候选段残留 %d 处（应已落号归位 / 转正入正式章；规程见 references/govern/fix-tools.md）—— %s"
                  % (len(_resid), "；".join(_resid[:6])))

# ---------- 14. 骨架合规（2026-09-23 新增 · 缺项 WARN 不阻断） ----------
# 依据：references/templates/（**骨架模板单一事实源**）
#   单案 = 七节（〇画像／一财务／二法律／三行业／四写作范式专项／五专家引用对照／六质量自评）
#   行业合并版 = 四段（一 类总览／二 共通方法论章／三 子行业特有章／四 覆盖核对表）
# 为什么报 WARN：存量历史案章名形态参差（实测单案七节齐备 31/82、写作范式章 30 种异名），
#   穷尽归一前不让门禁恒红；**新案应齐备**（从 templates/ 复制即天然合规）。
_SINGLE_SEC = ["〇、", "一、", "二、", "三、", "四、", "五、", "六、"]
_MERGED_SEC = ["一、", "二、", "三、", "四、"]
# 2026-09-23 补（判 I-0093）：**真欠账 vs 已定版豁免 二分** ——
#   原实现把两类混报，导致「修完真欠账后 WARN 数值逐字不变、修复不可见」。
#   豁免形态五类（2026-09-23 实测逐册核实，判据见 references/templates/README.md「已知例外」）：
#     ① 第 2 类语言专项（文件名 `投行语言写作范式_*`）；② 「第X章／第X部分」异体系（h1 **或 h2**，实测有 2 册写在 h2）；
#     ③ 单案无 h2 节结构（缺项 ≥6，实测 12 册，h1=1 且七节全缺）；④ 单案只缺〇画像（历史批次无画像节，37 册）；
#     ⑤ 行业合并版大幅缺段（缺项 ≥3，异体系）。
_sk_single, _sk_merged, _sk_exempt = [], [], []
for _f in md_files:
    _rel = os.path.relpath(_f, METHODS).replace(os.sep, "/")
    _is_single = _rel.startswith(SINGLE_NAME + "/")
    _is_merged = _rel.startswith(DIR_INDUSTRY_MERGED)
    if not (_is_single or _is_merged):
        continue
    try:
        with io.open(_f, encoding="utf-8") as _fh:
            _txt = _fh.read()
    except OSError:
        continue
    _h2 = re.findall(r"(?m)^## (.+)$", _txt)
    _h1 = re.findall(r"(?m)^# (.+)$", _txt)
    _want = _SINGLE_SEC if _is_single else _MERGED_SEC
    _miss = [s[0] for s in _want if not any(h.startswith(s) for h in _h2)]
    if not _miss:
        continue
    _label = os.path.basename(_f).replace("通用方法论_投行知识与写作范式_", "").replace(".md", "")[:16]
    _alt = any(("第" in h and ("章" in h or "部分" in h)) for h in (_h1 + _h2))
    _exempt = (os.path.basename(_f).startswith("投行语言写作范式_")          # ①
               or _alt                                                       # ②
               or (_is_single and len(_miss) >= 6)                           # ③
               or (_is_single and _miss == ["〇"])                           # ④
               or (_is_merged and len(_miss) >= 3))                          # ⑤
    (_sk_exempt if _exempt else (_sk_single if _is_single else _sk_merged)).append(
        "%s(缺%s)" % (_label, "".join(_miss)))
if _sk_single or _sk_merged or _sk_exempt:
    _real = len(_sk_single) + len(_sk_merged)
    # 2026-09-23 补：**真欠账 0 时不报 WARN**（纯豁免不构成待办，避免「恒有一项 WARN」的噪声）——
    #   真欠账 >0 才报，并列出真欠账条目（豁免项不再占示例位）。
    if _real > 0:
        WARNS.append("骨架缺项：**真欠账 %d**（单案 %d ／ 行业合并版 %d）／已定版豁免 %d"
                     "—— 真欠账须补（新案应从 templates/ 复制即天然合规）；豁免判据见 references/templates/README.md「已知例外」；真欠账示例 %s"
                     % (_real, len(_sk_single), len(_sk_merged), len(_sk_exempt),
                        "；".join((_sk_single + _sk_merged)[:4])))

# ---------- 15. 标签形态集一致性（产出侧 ⊆ 受理侧 · 2026-09-23 新增） ----------
# 背景（判 I-0088）：回写器 `apply_rewrite.py` 产出的实证标签形态（顶层列表项 `- **X实证**：`）
#   与契约校验器 `check_entry_contract.py` 受理的形态集（原仅行首 `**X实证**`）**不相交**
#   ⇒ S7「dry-run 必跑契约自检、0 ERROR 才 --apply」对回写产物**空转**，门禁报 PASS 属假绿
#     （实测单案层实证标签 4,505 处，旧实现受理 830＝18.4%、漏检 3,675）。
# 判据：契约校验器的 BAN_LABEL 必须命中「产出侧两种形态」，且**不得**把缩进列表项纳入
#   （缩进项＝内容小标题，实测全库 5 处均为描述性标签如「重排实证」，非案名）。
# 本项是**元自检**：任一实现的形态集变更而另一方未同步即报 ERROR ⇒ 防同类盲区复发。
_SK_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _find_script(_name):
    _here = os.path.dirname(os.path.abspath(__file__))
    for _c in (os.path.join(_here, _name),
               os.path.join(os.path.dirname(_here), "scripts", _name),
               os.path.join(SCRIPTS, _name)):
        if os.path.isfile(_c):
            return _c
    return ""


def _read_text(_p):
    try:
        return io.open(_p, encoding="utf-8").read()
    except OSError:
        return ""


_cec_p, _apw_p = _find_script("check_entry_contract.py"), _find_script("apply_rewrite.py")
_cec_src, _apw_src = _read_text(_cec_p), _read_text(_apw_p)
if not (_cec_src and _apw_src):
    _missing = [n for n, s in (("check_entry_contract.py", _cec_src), ("apply_rewrite.py", _apw_src)) if not s]
    WARNS.append("标签形态集自检跳过：未定位到 %s（包内脚本不在脚本同目录/上级 scripts/ 库 scripts/）"
                 % "、".join(_missing))
else:
    _m = re.search(r"BAN_LABEL\s*=\s*re\.compile\(\s*r?[\"'](.+?)[\"']", _cec_src)
    if not _m:
        ERRORS.append("标签形态集：无法从 check_entry_contract.py 解析 BAN_LABEL ⇒ 形态自检失效（请核对该常量写法）")
    else:
        try:
            _ban = re.compile(_m.group(1), re.M)
        except re.error as _e:
            _ban = None
            ERRORS.append("标签形态集：BAN_LABEL 正则无法编译（%s）" % _e)
        if _ban is not None:
            for _s, _want, _why in (
                ("- **样例案实证**：内容", True, "顶层列表项＝回写器产出形态"),
                ("**样例案实证**", True, "行首＝排布 2 原生形态"),
                ("  - **样例案实证**：内容", False, "缩进列表项＝内容小标题，不应入检"),
            ):
                _hit = bool(_ban.search(_s))
                if _hit != _want:
                    ERRORS.append("标签形态集不一致：BAN_LABEL 对「%s」命中=%s（应 %s）—— %s；"
                                  "产出侧与受理侧已分叉（I-0088 同族，须同步 references/entry-contract.md §7）"
                                  % (_s.strip()[:20], _hit, _want, _why))
    if "实证**：" not in _apw_src:
        WARNS.append("标签形态集：apply_rewrite.py 源码内未见 `实证**：` 产出形态 —— 请核对其写侧形态是否已变更")

# ---------- 16. 撤除载体不得重建（2026-09-23 新增） ----------
# 背景：`30_行业版/单份细分版/` 于 2026-09-23（WO-08 步 3）**全量撤除**（28 件归档、
#       目录删除），内容**归位单案文件「行业研究详述（叙述型）」章**（形态标注 `三·附`/`四·附`）。
#       撤除后遗留风险：**旧 automation 提示词曾硬引用该路径** ⇒ 无人值守运行会把已撤载体重建。
#       本项**防回潮**（与第 12/13 项同族：清账后立刻上护栏）。
# 判据：下列「已撤除载体」任一存在（目录）即 ERROR。
# 修复：删除该目录；其内容按裁定归位（见 references/distill-methods.md §S7 沉淀位置）。
RETIRED_DIRS = ["30_行业版/单份细分版", "30_行业版/合并版"]   # 后项：2026-09-23 扁平化上翻一层，层级冗余已消除
for _rd in RETIRED_DIRS:
    _p = os.path.join(METHODS, *_rd.split("/"))
    if os.path.isdir(_p):
        ERRORS.append("撤除载体被重建: %s（该层级已于 2026-09-23 撤除/扁平化；见 health-check.md 第 16 项）"
                      % _rd)

# ---------- 输出 ----------
# ---------- 17. 编号提取正则「左界」元自检（2026-09-23 新增 · 判 I-0094） ----------
# 背景：同族已**四犯**（I-0088／0091／0092／0094）—— 编号族存在「**短前缀 ⊂ 长前缀**」
#   （`L-` ⊂ `WL-`、`I-` ⊂ `WL-`、`L-` ⊂ `PL-`），提取正则若无左界即把长号**误截**为短号：
#   `[FLI]-\d{6}` 对 `WL-010020` 产出假 `L-010020`（实测 354 个假阳性 ⇒ 伪报「登记表缺失 226 个」）；
#   `([FLIW]L?-\d{6})` 无左界 ⇒ `WL-180035` 被匹配**两次**（同引用重复报错）。
# 本项是**元自检**：对 `_ID_RX` 登记表逐个跑**写入式探针** —— 探针串内**不含独立 `L-`／`I-` 编号**，
#   故「任一正则产出 `[LI]-\d{6}` 形态」即证明其缺左界（假阳性）。
_PROBE_IDS = "WL-010020 PL-170104 S-040008 F-010001 W-010001"
for _nm, _rx in _ID_RX:
    _hits = [h for h in re.findall(_rx, _PROBE_IDS) if isinstance(h, str)]
    _bad = sorted({h for h in _hits if re.match(r"^[LI]-\d{6}$", h)})
    if _bad:
        ERRORS.append("编号正则缺左界（第 17 项元自检）「%s」在探针 `%s` 上产出假短号 %s"
                      " —— 须加 `(?<![A-Za-z])` 左界（族规则：短前缀 ⊂ 长前缀）"
                      % (_nm, _PROBE_IDS, _bad))

# ---------- 18. 分卷卷号「唯一性」与段号连续性（2026-09-23 新增 · 族内分卷后） ----------
# 背景：族内分卷后卷号形如「卷NN-S」（NN＝族号、S＝段号）；索引标签 chap_label 只取「卷NN-S」
#   并丢弃其后内容 ⇒ **同域内卷号必须唯一**，否则多段卷收敛为同一标签、定位失效。
# （实证：2026-09-23 分卷后旧 chap_label 把 卷01-1／01-2／01-3 全部收敛为「卷01」——同域 30 段卷
#   退化成 9 个标签。已修 chap_label 支持段号，本项为**防回归护栏**。）
_VOL_RX = re.compile(r"^(?P<stem>.+)_\u5377(?P<fam>\d{2})(?:-(?P<seg>\d+))?_(?P<name>.+)\.md$")
_vols = {}
for _vf in sorted(glob.glob(os.path.join(METHODS, VOLUME_NAME, "*.md"))):
    _m = _VOL_RX.match(os.path.basename(_vf))
    if not _m:
        continue
    _dom = _m.group("stem"); _fam = _m.group("fam"); _seg = _m.group("seg") or "0"
    _vols.setdefault(_dom, []).append((_fam, _seg, os.path.basename(_vf)))
for _dom, _lst in _vols.items():
    _seen = {}
    for _fam, _seg, _bn in _lst:
        _k = (_fam, _seg)
        if _k in _seen:
            ERRORS.append("分卷卷号重复（第 18 项）：%s 的「卷%s%s」出现两次（%s ／ %s）"
                          " —— 索引标签将撞车、条目定位失效" % (_dom, _fam, ("-" + _seg) if _seg != "0" else "", _seen[_k], _bn))
        _seen[_k] = _bn
    # 族内段号自 1 连续
    _byfam = {}
    for _fam, _seg, _bn in _lst:
        if _seg != "0":
            _byfam.setdefault(_fam, []).append(int(_seg))
    for _fam, _segs in _byfam.items():
        _exp = list(range(1, max(_segs) + 1))
        if sorted(_segs) != _exp:
            ERRORS.append("段号不连续（第 18 项）：%s 族 %s 的段号为 %s，应为 1–%d 连续"
                          % (_dom, _fam, sorted(_segs), max(_segs)))
# PL 族号须在 01–05（2026-09-23 由 15–19 重排而来；防旧族号回潮）
for _fam, _seg, _bn in _vols.get("投行语言专项_招股书PL系列", []):
    if _fam not in ("01", "02", "03", "04", "05"):
        ERRORS.append("PL 族号越界（第 18 项）：%s 的族号为 %s，应为 01–05（2026-09-23 族号重排后契约）"
                      % (_bn, _fam))


# ---------- 19. 条目契约全库校验（2026-09-24 新增 · 补「无出口」根因） ----------
# 背景：`check_entry_contract.py` 是**条目书写契约**的校验器（来源标注／单案字段名／案名／实证标签），
#   但此前**只读自检、未接任何门禁** ⇒ 2026-09-22 侦察报告实测全库 **703 ERROR** 却长期无人发现，
#   报告原话：**「该检查器是只读自检、未进门禁 ⇒ 没有出口，就不会有人修」**。
#   存量已在 2026-09-23 库重构中归零（2026-09-24 复核：scanned=185／error=0），但**根因未除**
#   —— 本项即为**补出口**：把契约校验纳入维护域体检（S7 沉淀后自动跑 ＋ 维护域手动跑）。
# 判据：调用 `check_entry_contract.py --json` 取 `error`；> 0 即 ERROR（附前 3 条明细）。
# 单一事实源：**调用不复制**其判据（同 `health_all.py` 的「只调用不复制」口径）。
# 修法：按其 `issues[].where` 逐条改（来源标注走口径迁移脚本；字段名／案名／标签逐条），改完重跑至 0。
import subprocess as _sp
_cec_p = _find_script("check_entry_contract.py")
if not _cec_p:
    WARNS.append("条目契约校验器未找到（第 19 项）：check_entry_contract.py")
else:
    try:
        _r = _sp.run([sys.executable, _cec_p, "--methods-root", _ROOT, "--json"],
                     capture_output=True, text=True, encoding="utf-8", errors="replace")
        _j = json.loads(_r.stdout.strip() or "{}")
        _n = int(_j.get("error") or 0)
        if _n:
            _det = "；".join(
                "%s %s" % (i.get("where", i.get("file", "?")), str(i.get("msg", ""))[:60])
                for i in (_j.get("issues") or [])[:3])
            ERRORS.append("条目契约违规 %d 处（第 19 项）：%s —— 跑 check_entry_contract.py 看全量"
                          % (_n, _det[:220]))
    except Exception as _e:
        WARNS.append("条目契约校验未能执行（第 19 项）：%s" % _e)


if _args.json:
    print(json.dumps({
        "tool": "check_methods_health", "target": METHODS,
        "verdict": "FAIL" if ERRORS else "PASS",
        "error": len(ERRORS), "warn": len(WARNS), "scanned": fm_checked,
        "issues": ([{"level": "ERROR", "msg": m} for m in ERRORS] +
                   [{"level": "WARN", "msg": m} for m in WARNS]),
    }, ensure_ascii=False))
    sys.exit(1 if ERRORS else 0)
quiet = _args.quiet
if not quiet:
    print("=== 方法论全库健康检查 ===")
    print("正文文件（frontmatter 校验）: %d 个｜索引行号抽查: %d 条｜单案内容范围: %d 案"
          % (fm_checked, _locator_checked, _scope_checked))
print("ERROR %d 项" % len(ERRORS))
for e in ERRORS:
    print("  [ERROR] %s" % e)
if WARNS:
    print("WARN %d 项" % len(WARNS))
    for w in WARNS:
        print("  [WARN] %s" % w)
sys.exit(1 if ERRORS else 0)

#!/usr/bin/env python3
"""方法论全库健康护栏（25 项检查 · 防结构漂移）

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
8.  交叉引用有效性      引用目标编号必须在登记面（all_ids）内；扫描面＝域/语言/分卷＋行业版＋单案；
                        全族正则（含 PL-/S-/I-CL）；存量基线**已清零**（2026-09-26 两批订正）⇒ **新增失效即 ERROR**；
                        自带「历史编号·主库无对应·待核」注记者＝**已声明的历史引用**，不计欠账
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
17. 编号提取正则左界    元自检：`_ID_RX` 登记表逐个跑写入式探针，任产假短号（缺左界致长号被误截）即 ERROR
                        另含「**覆盖面**」探针：每个在用编号族（F/L/I/W/WL/PL/S/I-CL）须被至少
                        一个登记正则**完整命中**（2026-09-26 补 · 同族第五犯：PL/S 整族曾漏检）
                        （单一事实源 → 本文件 `RX_ID_*` 常量组）
18. 分卷卷号唯一性      族内分卷后「卷NN-S」同域唯一 ＋ 段号自 1 连续 ＋ PL 族号须在 01–05
19. 条目契约全库校验    调用 check_entry_contract.py --json 取 error，>0 即 ERROR（补「无出口」根因）
20. 文档计数/元数据一致 元自检：护栏项数 ← 本 docstring 项号清单（须连续 1..N）；脚本数 ← scripts/*.py
                        实测；**活文档**（白名单，见 _lib.layout.COUNT_DOCS）内「护栏 N 项／脚本 N 个」
                        必须与实况一致；README 版本徽章须等 SKILL.md `version:`。**排除**「第 N 项」形态
21. 入库强制字段·互见   增量水位（`HUXIAN_WATERMARK` 2026-09-26 冻结）：族内序号 > 水位者视为新增，
                        其条目块须含 `**互见**：`（无关联写「无」）；**存量不回溯**。
                        只判有无该字段、不判内容；单案层与行业版不适用
22. 登记表完整性对账    两张手写登记表（`方法论_案名规范表.md` 表一·表二／`state/单案索引对照表.md` §一）
                        的「单案文件」列 ⟷ `40_单案/` 实存，**双向对账**：登记了但不存在＝滞后、
                        实存但未登记＝漏登，**均报 WARN**（软，不阻断）；另查表一案号连续性
                        （AN0074/0075 主库直入案为**合法缺口基线** `TABLE22_AN_GAP_OK`）
                        （权威口径见表 B · 2026-09-26 WO-MF-04）
23. 库内 schema 水位      库内自描述入口 `SCHEMA.md`（`gen_schema.py` 生成）所记的 schema 版本
                        ⟷ skill 实况 `SKILL.md` 的 `version:`；另校验其「规矩在哪读」表内的
                        册子路径**确实存在**（该表已改**派生**：扫 `references/**/*.md`）。
                        **立项理由**：schema 在库外、靠使用者记得才会跟上，一旦忘了，库的自描述
                        就悄悄过期——本项把它变成机器可验。**档位分两层**：入口**缺失 ⇒ ERROR**
                        （库失去自描述＝结构性损失，且该生成步已并入索引刷新链，报了就是真问题）；
                        仅**水位滞后 ⇒ WARN**（属瞬时态，下次刷索引即自愈）
24. 增量裸页码            统计活文档内「省略来源代号的裸页码标注」数 ⟷ 常量 `BARE_PAGE_BASELINE`：
                        上升 ⇒ ERROR（新增了裸页码）；持平 ⇒ PASS；下降 ⇒ WARN（提示复核后下调基线）。
                        **立项理由**：溯源达标（A1）原定「全库可判案率过半」，实测**结构性不可达**
                        ——存量既非机器可补（逐一复验仅约 3% 够格），亦非人可裁 ⇒ 判据**改口径**为
                        「**增量零裸页码**」：存量按设计边界不回溯，增量不得再产生。
                        与 `check_evidence.py` **同一判据**（同两条正则 ＋ 同一别名表），两处读数应一致
25. skills 消费侧引用    skills 面活文档**禁硬编码库计数/路径**（R-0065）：① 生成物文件名引用
                        （`GENERATED_BASENAMES`）实测库内存在（SCHEMA.md 例外留库根），
                        缺失 ⇒ ERROR（引用断链）；② 「两位数字＋窄单位词」（案例/案/条目/条改写/插入点）
                        与库实况（单案数）同形比对，不等 ⇒ WARN **由人核**（阈值规则/历史叙述为合法同形）。
                        排除历史面（CHANGELOG/adr/incident-log*/pending-rules/archive 等——
                        其数字是「发生过什么」，非活口径）。漂移根因在库侧变更 ⇒ **变更即校验**

注：第 12 项（I-CL 条目位置）实现在第 3 项（编号健康）的行业合并版分支内，非独立小节。

三栏信号（2026-09-26 WO-33）：
  ERROR         **验了发现不符**（有界结论）
  UNVERIFIABLE  **根本验不了**（本应受检却缺输入/脚本/文件）—— **计入 ERROR 与退出码**，不得当通过
  WARN(soft)    只进报告与日志，不影响退出码

退出码：0 = 无 ERROR 且无 UNVERIFIABLE（可有 WARN）；1 = 有 ERROR 或 UNVERIFIABLE；
        2 = 前置失败（未找到库）；3 = `--strict` 下 WARN > 0
"""
import argparse, io, json, os, re, glob, random, sys, time
from pathlib import Path

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_ap = argparse.ArgumentParser(description="方法论全库健康护栏（25 项检查）")
_ap.add_argument("--methods-root", default=os.environ.get("METHODS_ROOT", ""),
                 help="工作区根（= 库根，其下含 methods/；默认 $METHODS_ROOT，或脚本上级目录）")
_ap.add_argument("--quiet", action="store_true", help="只输出异常项")
_ap.add_argument("--strict", action="store_true",
                 help="WARN > 0 时以退出码 3 退出（默认：退出码只表 ERROR，WARN 只进报告）")
_ap.add_argument("--no-log", action="store_true",
                 help="不写操作日志（默认：每次体检向 <工作区根>/logs/库操作日志.md 追加一行）")
_ap.add_argument("--allow-dup", action="store_true",
                 help="允许同日同结果重复留痕（默认：同日同「结果行」已存在则跳过，防刷屏）")
_ap.add_argument("--json", action="store_true", help="输出结构化 JSON（供上层消费）")
_args = _ap.parse_args()

import os as _lo, sys as _ls
_ls.path.insert(0, _lo.path.dirname(_lo.path.abspath(__file__)))
from _lib.layout import (resolve as _layout_resolve, ENTRY_FILE, PARSED_FILE, TOC_FILE,
                         DOMAIN_SIZE_WARN_BYTES, SKIP_DIRS, GENERATED_BASENAMES,
                         MERGED_MAP, VOLUME_NAME, LANG_W_FILE, DOMAIN_GLOB, LANG_GLOB,
                         MERGED_GLOB, SINGLE_NAME, DIR_INDUSTRY_MERGED, library_files,
                         RX_ID_FAMILY, COUNT_DOCS, COUNT_DOCS_WORKSPACE, COUNT_SCAN_STOP_HEADING,
                         SKILL_DIR, RX_DECLARED_HIST, CANON_TABLE, CASE_INDEX_TABLE,
                         SCHEMA_BASENAME, BARE_PAGE_BASELINE, GENERATED_NAME,
                         DIR_DOMAIN, DIR_LANG, DIR_VOLUME, domain_files as _layout_domain_files)
_ROOT, METHODS, SCRIPTS = _layout_resolve(_args.methods_root)
# ---------- 编号提取正则登记表（**单一事实源** · 第 17 项元自检对象） ----------
# 铁律：凡「**短前缀 ⊂ 长前缀**」的编号族（`L-` ⊂ `WL-`、`I-` ⊂ `WL-`、`L-` ⊂ `PL-`），
#   提取正则**必须带左界 `(?<![A-Za-z])`**；行首锚定 `^### ` 者天然满足。
# 背景：同族已四犯（I-0088／0091／0092／0094）—— `[FLI]-\d{6}` 会把 `WL-010020` 误截为
#   `L-010020`（实测 354 个假阳性）；`([FLIW]L?-\d{6})` 无左界会把 `WL-180035` 匹配两次。
RX_ID_ANY   = RX_ID_FAMILY      # ← 全族引用正则**单一事实源＝`_lib/layout.py` RX_ID_FAMILY**（2026-09-26 归一）
#   ↑ 原为本地字面量 `[FLIW]L?-\d{6}`，**不含 `PL-`（542 条）与 `S-`（364 条）**
#     ⇒ 全库 53.6% 的条目族**整体漏在交叉引用受检面外**（实测「域/语言/分卷」面 2,585 处引用，
#     原正则只可见 783 处、**漏检 1,802 处 ＝ 69.7%**）。另补 `I-CL{类号}-{序}`（行业合并版条目）。
#     ⚠️ 与 `RX_ID_HEAD` **必须同改**——只放宽引用正则而不放宽「定义收集」正则，会把整族 S- 误判为失效。
RX_ID_LANG  = r"(?<![A-Za-z])(?:WL|W)-[A-Za-z0-9\-·~]+"  # W 系列编号
RX_ID_REGT  = r"(?<![A-Za-z])[FLI]-\d{6}"       # 登记表主库编号（F/L/I）
RX_ID_REGTW = r"(?<![A-Za-z])WL-\d{6}"          # 登记表语言专项编号
RX_ID_HEAD  = r"^### ([FLIWS])-(\d{6})"         # 标题编号（行首锚定）
#   ↑ 2026-09-26 补 `S`（原 `[FLIW]` ⇒ 体例域 S 族**从不进入 all_ids**，登记面无 S ⇒ 引用校验无从命中）
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

ERRORS, WARNS, UNVERIFIABLE = [], [], []
# `UNVERIFIABLE`（2026-09-26 WO-33）＝ **本应受检、但因缺输入/脚本/文件
#   而根本判不了**的情形，**与「验了发现不符（ERROR）」分栏**。判据原文：「**验了疑似不符**」与
#   「**根本验不了**」分两栏；后者 **always need a decision**，不得默默当通过。
#   本栏**计入 ERROR 与退出码**（FAIL）—— 理由同第 19 项立项目的「**没有出口，就不会有人修**」：
#   把「判不了」降级成 WARN 或静默跳过，等于让有界检查的缺口永久隐形（本库两次「门禁假绿」同源）。


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
GAP_BASELINE = {
    "PL-01": [4, 5, 6, 7, 8, 9, 10, 14, 15, 16, 17, 18, 19, 20],
    "PL-02": [4, 5, 6, 7, 8, 9, 10, 14, 15, 16, 17, 18, 19, 20],
    "PL-03": [4, 5, 6, 7, 8, 9, 10, 14, 15, 16, 17, 18, 19, 20],
    "PL-04": [3, 4, 5, 6, 7, 8, 9, 10, 13, 14, 15, 16, 17, 18, 19, 20],
    "PL-05": [4, 5, 9, 10],
}

fam_seqs = {}  # (prefix, fam) -> [(seq, rel)]  （2026-09-26：按「族」聚合，不按文件）
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
                # 2026-09-26：族内连续**按「族」聚合、不按文件** —— 原键 `(rel, prefix, fam)` 隐含
                #   「一族一文件」假设；S／PL 族内分卷（`卷NN-1/2/3`）后**同族跨多文件**，
                #   按文件算必然误报「缺 1..N」（实测 S-01 报缺 1–10，实为卷 01-1 持有 seq 1–10）。
                #   契约册原文即「**族内连续**」（族＝切分单元），故改全族聚合。
                fam_seqs.setdefault((prefix, int(full[:2])), []).append((int(full[2:]), rel))
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
        for _mm in re.finditer(r"^### (PL-\d{6})", content, re.M):
            _full = _mm.group(1)[3:]
            fam_seqs.setdefault(("PL", int(_full[:2])), []).append((int(_full[2:]), rel))   # 2026-09-26：PL 序号纳入族内连续受检面（基线见 GAP_BASELINE）
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
            fam_seqs.setdefault(("I-CL", int(m.group(1))), []).append((int(m.group(2)), rel))
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
                    fam_seqs.setdefault(("I-CL", int(m.group(1))), []).append((int(m.group(2)), rel))

for (prefix, fam), items in sorted(fam_seqs.items()):
    seqs_sorted = sorted(set(sq for sq, _ in items))
    if seqs_sorted != list(range(1, len(seqs_sorted) + 1)):
        missing = sorted(set(range(1, max(seqs_sorted) + 1)) - set(seqs_sorted))
        _gap_key = "%s-%02d" % (prefix, fam)
        _gap_base = set(GAP_BASELINE.get(_gap_key, [])) if prefix == "PL" else set()
        _gap_new = sorted(set(missing) - _gap_base)
        if _gap_new:
            ERRORS.append("族内编号不连续 %s-%02d: %d 条，缺 %s" % (prefix, fam, len(seqs_sorted), _gap_new[:10]))
        elif missing:
            WARNS.append("族内缺号（历史欠账基线内 %s-%02d 缺 %s）—— 基线外新增缺号才 ERROR" % (prefix, fam, missing[:8]))

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
# 范围：5 个方法论正文本体；规则：引用编号须存在于 all_ids；旧 W 系列形态（W-00xxxx）为历史注记，跳过不报。
# 2026-09-23 补：纳入 `50_分卷/`（按族外置后 F/L/I 条目正文在此 ⇒ 卷内引用亦须受检）
# 2026-09-26 补（编号覆盖面）：**纳入 `30_行业版/`（I-CL 条目的引用）＋ `40_单案/`（单案引用主库编号）**
#   —— 原扫描面只含域/语言/分卷，**单案与行业版整层不受检**（实测该两层含 2,373 处引用）。
#
# 存量失效引用（旧称：悬空引用）基线（2026-09-26 · 定案 9「**豁免历史、约束增量**」）
#   ── 存量**不改内容**（改属 ③ 内容回写面），故登记为**已知欠账**：命中基线者报 **WARN**
#      （**可见但不阻断**），**新增**失效才报 ERROR。
#   ── 基线变动（消解或新增）须**同步本表与 `references/govern/health-check.md` 第 8 项**。
DANGLE_BASELINE = set()   # 2026-09-26 清零（见下注③）
# ── PL 族缺号基线（2026-09-26 · PL 序号纳入第 3 项「族内连续」受检面当日冻结）────────
#   实测缺号呈「段状」且五族形态一致（01/02/03 族缺 4-10、14-20；04 族缺 3-10、13-20；05 族缺 4-5、9-10）
#   ⇒ 指向历史改号/落号事件（悬空两批订正已考古证实），非孤立笔误 ⇒ 一次性登记为**历史欠账基线**：
#   基线内缺号报 WARN（可见不阻断），**基线外新增缺号才 ERROR**（与悬空同款「豁免历史、约束增量」）。
# 2026-09-26 收缩 13 → 9 → 5 → **0**：
#   ① 移出 4 个 `W-` 编号（W-070008／W-180023／W-190001／W-190004）—— 经逐条核原文，其引用处
#      **自带「历史编号·主库无对应·待核」注记** ⇒ 属 **A6 降级留痕合法形态**，改由 `_RX_DECL_HIST` 单列。
#   ② 第一批移出 4 个**已订正**编号（用户裁定「按你建议」后执行，属 ③ 内容回写）：
#      `S-000015 → S-030001`（2 文件同句，括注与标题逐字重合）
#      `PL-010004 → PL-020024`（称号逐字一致）
#      `PL-010009 → PL-050013`（标题＋`来源案`＝保伦股份 **双命中**；同名 PL-050037/041/043 案名不符已排除）
#      `F-000073 → F-AN0017-14`（**非主库引用**：表格内案内序号范围写法；实测 F-AN0017-01..14 齐备）
#   ③ 第二批移出余 5 个（用户裁定「按你建议继续」，同日执行）——深挖决定性发现：5 号（含重排前旧号
#      PL-150010／PL-190005／PL-190010／PL-180003）**在库任何历史状态（archive 全部快照）中从未作为
#      条目存在** ⇒ 非「改号未同步」而是「引用了从未落号的号」。处置＝**指定现存替代 或 删半句**：
#      `PL-010010 → PL-050014`（保伦侧同族；同句另两号均万源通）
#      `PL-050005 → PL-050056`（联讯仪器 09-06 < 引用者九目化学 09-16，时序成立；措辞「另证不设效益免责
#        注」排除标题已含免责注的 PL-050098）
#      `PL-050010` → 删半句（龙鑫侧保留案内号 PL-AN0048-10；库内无龙鑫来源案的族05条目 ⇒ 龙鑫侧从未落号）
#      `PL-040003` → 删半句（保留 PL-040023；候选 PL-040035 时序不符——引用者胜业电气 08-29 早于其 09-12 落号）
#      `I-100005 → I-030003`（同句括注「比例测算法＋口径显式」与 I-030003 标题两项逐字命中）
#   **baseline 从此为空**：**新增失效即 ERROR，无豁免**；本表保留为机制占位（后续如需豁免须经裁定并落此表）。
_base_hits = set()
_decl_hist = set()
# 「**已声明的历史引用**」＝引用处**自带注记**说明该编号在主库无对应，如
#   「`W-070008`（历史编号·主库无对应·待核）」——这是 **A6 降级留痕的合法形态**（显式声明、机器可识别），
#   **不算失效欠账**：它不是「漏改的引用」，而是「**引用了确实不在库内的历史编号，且已告知读者**」。
#   处置：单列计数、不报 ERROR、不入 baseline（免与「真失效」混算）。判据＝注记词同现。
_RX_DECL_HIST = re.compile(RX_DECLARED_HIST)
#   ↑ 判据常量收在 `_lib/layout.py`（**单一事实源**）：体检第 8 项与 `gen_refgraph.py` **同判**。
_SURF8 = (sorted(glob.glob(os.path.join(METHODS, DOMAIN_GLOB)))
          + sorted(glob.glob(os.path.join(METHODS, LANG_GLOB)))
          + sorted(glob.glob(os.path.join(METHODS, VOLUME_NAME, "*.md")))
          + sorted(glob.glob(os.path.join(METHODS, MERGED_GLOB)))
          + sorted(glob.glob(os.path.join(METHODS, SINGLE_NAME, "*.md"))))
for df in _SURF8:
    rel = os.path.relpath(df, METHODS)
    with io.open(df, encoding="utf-8") as f:
        lines = f.read().splitlines()
    for i, l in enumerate(lines):
        s = l.strip()
        if not s or s.startswith("#") or s.startswith(">"):
            # 2026-09-26：**表格行（`|`）纳入扫描面**——原与 `#`／`>` 一并跳过，实测漏 1 处
            #   （`F-000073` 仅出现在 `40_单案/环动科技` 表格行）；`#`（定义行／自指）与 `>`（引用块）
            #   仍按设计排除，见 `health-check.md` 第 8 项「覆盖边界」。
            continue
        # 2026-09-23 修：`([FLIW]L?-\d{6})` 无左界 ⇒ `WL-180035` 会被匹配**两次**
        #   （`WL-180035` 与错位起的 `L-180035`）⇒ 同一引用重复报错。加左界 `(?<![A-Za-z])`。
        for m in re.finditer("(" + RX_ID_ANY + ")", s):
            ref = m.group(1)
            if re.match(r"^W-00", ref):  # 旧 W 系列编号（历史注记/索引保留）
                continue
            if ref not in all_ids:
                if _RX_DECL_HIST.search(s):
                    _decl_hist.add(ref)      # 已声明的历史引用（A6 降级留痕）⇒ 不算失效
                elif ref in DANGLE_BASELINE:
                    _base_hits.add(ref)      # 存量欠账：报 WARN（可见、不阻断）
                else:
                    ERRORS.append("交叉引用无效 %s L%d: %s（目标编号不存在，需核对登记表/迁移）" % (rel, i + 1, ref))
if _base_hits:
    WARNS.append("存量失效引用（历史欠账清单（旧称：基线豁免） **%d 个编号** · 属 ③ 内容回写面，本次**不改内容**）：%s —— **新增**失效才报 ERROR；基线表见脚本 `DANGLE_BASELINE` 与 `health-check.md` 第 8 项"
                 % (len(_base_hits), "、".join(sorted(_base_hits))))
if _decl_hist:
    # **不计欠账**：这些是「引用了确实不在库内的历史编号，且引用处已告知读者」——降级留痕的合法形态。
    # 单列出来只为**可见**（免与真失效混淆），不入退出码、不入 baseline。
    WARNS.append("已声明的历史引用 **%d 个编号**（**不计欠账** · A6 降级留痕合法形态）：%s —— 引用处自带「历史编号·主库无对应·待核」注记"
                 % (len(_decl_hist), "、".join(sorted(_decl_hist))))

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
        # 2026-09-26（WO-18）：原输出把「池大小」当「抽样条数」打印 ⇒ 信号失真（实测池 1689、实抽 12）。
        #   现分别记录，输出「抽样/池」两数，使「覆盖率」可见。
        _locator_sampled = min(12, len(_rows))
    else:
        _locator_checked, _locator_sampled = 0, 0
        UNVERIFIABLE.append("索引行号定位**无法抽查**（第 10 项）：%s 存在但无可解析行"
                            "—— 定向读取键（编号→文件:行号）本次**零验证**；先跑 refresh_index.py" % TOC_FILE)
else:
    _locator_checked, _locator_sampled = 0, 0
    UNVERIFIABLE.append("索引行号定位**无法抽查**（第 10 项）：%s 不存在"
                        "—— 定向读取键本次**零验证**（新库首次运行前应先 refresh_index.py）" % TOC_FILE)

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
#   豁免形态（2026-09-23 实测逐册核实，判据见 references/templates/README.md「已知例外」）：
#     原① 第 2 类语言专项（`投行语言写作范式_*`）——**2026-09-26 撤销**（两孤本已并入标准单案并归档，
#        该文件形态不复存在；保留判据反使同类新孤本漏检，删除即防回潮）；
#     ② 「第X章／第X部分」异体系（h1 **或 h2**，实测有 2 册写在 h2）；
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
    _exempt = (_alt                                                                # ②
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
    UNVERIFIABLE.append("标签形态集自检**无法执行**（第 15 项）：未定位到 %s"
                        "（包内脚本不在脚本同目录/上级 scripts/ 库 scripts/）—— 本项判据源缺失，"
                        "形态一致性**本次未被验证**" % "、".join(_missing))
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

# ---------- 17b. 编号**覆盖面**探针（2026-09-26 补 · 判 I-0094 同族第五犯） ----------
# 背景：原元自检**只测「左界」**（长号被误截为短号），**不测「覆盖面」** ⇒ 「某编号族整体不在
#   任何登记正则里」这类漏洞**全程通过**。实证：`PL-`（542 条）与 `S-`（364 条）共 **906 条、
#   占全库 53.6%**，长期漏在交叉引用受检面外（`RX_ID_ANY` 无 PL/S；`RX_ID_HEAD` 无 S ⇒ S 连
#   登记面都没进）；「域/语言/分卷」面 2,585 处引用中**漏检 1,802 处 ＝ 69.7%**。
# 判据：对**每个在用编号族**各取一枚样本，要求「**至少一个登记正则能完整命中它**」；
#   任一族无覆盖 ⇒ ERROR（须在 `_ID_RX` 增补，或说明该族已停用）。
_PROBE_FAM = {"F": "F-010001", "L": "L-010001", "I": "I-010001", "W": "W-010001",
              "WL": "WL-010020", "PL": "PL-010001", "S": "S-010001", "I-CL": "I-CL01-01"}
for _fam, _sample in sorted(_PROBE_FAM.items()):
    _covered = any(any(_m.group(0) == _sample for _m in re.finditer(_rx, _sample))
                   for _nm, _rx in _ID_RX)
    if not _covered:
        ERRORS.append("编号**覆盖面**缺口（第 17 项覆盖面探针）：编号族「%s」样本 `%s` 未被任何登记正则**完整命中**"
                      " —— 须在 `_ID_RX` 增补覆盖该族的正则（族规则：短前缀 ⊂ 长前缀，且**每族都须被覆盖**）"
                      % (_fam, _sample))

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
    UNVERIFIABLE.append("条目契约**整体未被校验**（第 19 项）：未找到 check_entry_contract.py"
                        "—— 契约面（来源标注/字段名/案名/标签）本次**零验证**")
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
        UNVERIFIABLE.append("条目契约校验**未能执行**（第 19 项）：%s —— 契约面本次**零验证**" % _e)


# ---------- 20. 文档计数/元数据一致性（2026-09-26 WO-32 · 元自检） ----------
# 病根：同一批「护栏 N 项／随包脚本 N 个」声明散布在 8+ 处**活文档**且各自漂移——2026-09-26 当日
#   实测**四度**（护栏 16/18/19；脚本 15/25/26/27；README 版本徽章滞后一版）。属第 17 项同族
#   「**多份口径各自维护**」病的**文档面**；修法同上——**收单一事实源 ＋ 元自检**。
# 单一事实源：
#   ① 护栏项数 ← **本文件 docstring 的项号清单**（须为连续 1..N；docstring 即登记表，不另设副本）
#   ② 脚本数   ← `scripts/*.py` 实测（用户面可执行；**不含** `scripts/_lib/` 内部模块）
# 扫描面：`_lib.layout.COUNT_DOCS`（skill 侧）＋ `COUNT_DOCS_WORKSPACE`（工作区侧）**白名单**——
#   **只扫活文档**；CHANGELOG／logs（操作日志 append-only）／tasks／docs（执行记录）／archive／
#   methods/**（条目正文里的「护栏第 N 项」是**项号引用**）**一律不扫**，历史记录保留原值。
#   活文档内遇「近期更新／版本历史」类小节**停止扫描**。
# 正则要点：**必须排除「第 N 项」形态**（项号引用 ≠ 计数声明；曾两次误判：
#   `fix-tools.md` 的「护栏第 16 项」、`templates/README.md` 的「第 14 项护栏」）；
#   且须 `(?<!\d)` 防「第 14 项」被截成短号（实测：无此界会把「14」的尾数当成计数）。
_doc_items = [int(_m) for _m in re.findall(r"^(\d{1,2})\.\s+\S", __doc__ or "", re.M)]
if _doc_items != list(range(1, len(_doc_items) + 1)):
    ERRORS.append("第 20 项元自检：本脚本 docstring 护栏项号**不连续** → %s（须为 1..N，逐项可数）"
                  % _doc_items)
_guard_n = len(_doc_items)
# ⚠️ 脚本数须取 **skill 的** `scripts/*.py`（`resolve()` 返回的 SCRIPTS 是**工作区**的 scripts/）。
_script_n = len(glob.glob(os.path.join(str(SKILL_DIR), "scripts", "*.py")))
_RX_CNT_G = re.compile(r"(?<!第)(?:护栏体检|体检|护栏|检查)(?!第)[^\d\n，。；;｜|第]{0,6}(\d{1,2})\s*项"
                       r"|(?<!第\s)(?<!第)(?<!\d)(\d{1,2})\s*项(?:护栏体检|体检|护栏|检查)")
#   ↑ **间隔桥接的取值（2026-09-28 修假红）**：正装形态允许「关键词」与「数字」之间有 ≤6 字间隔，
#     以容纳「护栏 **N 项」这类加粗/空格写法。但该桥接会产生**假红**：实测「护栏项（体检第 NN 项」
#     被读成计数声明（关键词「护栏」→ 间隔「项（体检第 」→ 数字 →「项」）⇒ 当场 ERROR。
#     **治法不是禁「（」**（「体检（NN 项护栏」是**合法**形态，禁它即误伤），而是**禁止间隔里再出现
#     「第」与「；」**：前者是「项号引用」的标记，后者是分句边界——二者出现在间隔里，说明这里
#     跨的已是另一句话/另一次引用，不该再当作同一处计数声明。
#     教训归属：假红与静默漏**同属**该漂移族——前者污染 0-ERROR 基线（本库已两次吃过自动化的亏），
#     后者让缺陷长期不可见。故桥接的松紧须以此类实测定，不凭想象。
#     ⚠️ **写注释也别写出真数字**：本条初稿举了带真数字的例，**当场自触发本项**（报 ERROR 两处）
#        ⇒ 凡**描述**本项形态的文案一律用 `N` 占位。这是「给病写疫苗的人，也会得同一种病」的现场例。
_RX_CNT_S = re.compile(r"(\d{1,2})\s*个随包脚本|随包脚本[^\d\n]{0,8}(\d{1,2})\s*个"
                       r"|(?<![\d第])脚本\s*(\d{1,2})\s*个|(?<![\d第])(\d{1,2})\s*个脚本")
_RX_STOP = re.compile(COUNT_SCAN_STOP_HEADING)
# ⚠️ 不能用 `os.path.dirname(SCRIPTS)` —— `resolve()` 返回的 `SCRIPTS` 是**工作区**的 `scripts/`，
#    其上溯即工作区根（曾因此把 skill 侧白名单整批跳过 = 静默失效）。skill 根取 `layout.SKILL_DIR`。
_SKILL_DIR = str(SKILL_DIR)
for _base, _rel in ([( _SKILL_DIR, _d) for _d in COUNT_DOCS]
                    + [(_ROOT, _d) for _d in COUNT_DOCS_WORKSPACE]):
    _p = os.path.join(_base, _rel)
    _is_pack_doc = _base == _SKILL_DIR
    if not os.path.isfile(_p):
        # **随包文档**缺失＝包损坏 ⇒ 属「根本验不了」（该文档的计数一致性本次未被验证）；
        # **工作区文档**缺失＝使用者库差异（白名单里含自建/可选件）⇒ 静默跳过，不报。
        if _is_pack_doc:
            UNVERIFIABLE.append("文档计数**无法核对**（第 20 项）：随包文档 %s 缺失 ⇒ 其计数一致性本次零验证" % _rel)
        continue
    try:
        _lines = io.open(_p, encoding="utf-8", errors="replace").read().splitlines()
    except OSError as _e:
        UNVERIFIABLE.append("文档计数**无法核对**（第 20 项）：%s 读取失败（%s）" % (_rel, _e))
        continue
    for _i, _l in enumerate(_lines, 1):
        if _RX_STOP.match(_l):
            break                     # 「近期更新／版本历史」及其后属历史，不扫
        for _m in _RX_CNT_G.finditer(_l):
            _v = int(_m.group(1) or _m.group(2))
            if _v != _guard_n:
                ERRORS.append("文档计数不一致（第 20 项）%s L%d：称「护栏 %d 项」，实况 **%d 项**"
                              % (_rel, _i, _v, _guard_n))
        for _m in _RX_CNT_S.finditer(_l):
            _v = int(next(_g for _g in _m.groups() if _g))
            if _v != _script_n:
                ERRORS.append("文档计数不一致（第 20 项）%s L%d：称「脚本 %d 个」，实况 **%d 个**"
                              % (_rel, _i, _v, _script_n))
# 20d 版本徽章 vs frontmatter（同一漂移族：README 顶部徽章由人手改、易滞后一版）
try:
    _sk_txt = io.open(os.path.join(_SKILL_DIR, "SKILL.md"), encoding="utf-8").read()
    _mv = re.search(r"(?m)^version:\s*([0-9][^\s]*)", _sk_txt)
    _rm_txt = io.open(os.path.join(_SKILL_DIR, "README.md"), encoding="utf-8").read()
    _bv = re.search(r"badge/version-([0-9][^-]*)-", _rm_txt)
    if _mv and _bv and _mv.group(1) != _bv.group(1):
        ERRORS.append("文档计数不一致（第 20 项）README.md：版本徽章 %s ≠ SKILL.md `version: %s`"
                      % (_bv.group(1), _mv.group(1)))
except OSError:
    pass


# ---------- 21. 入库强制字段·互见（**增量水位** · 2026-09-26 WO-33） ----------
# 规则（本库 R2）：**新入库**的跨案层／分卷条目须带「互见」字段
#   （无关联写「**互见**：无」）；**存量不回溯补**（不建反链、不回溯补存量）。
# 判据：**族内序号 > 水位** 者视为「新增」；其条目块内须出现 `**互见**：`，否则 ERROR。
#   · 水位表为 **2026-09-26 冻结快照**（各族 max 序号，取自位置目录全量 1689 编号）；
#   · **新增族**（水位表无该键）⇒ 整族按新增处理；
#   · 水位表**不应随新增条目更新** —— 更新它等于把新条目「祖父化」，规则即失效。
# 为何用水位而不用「全库强制」：全库强制会让 1689 条存量**由合规变不合规**（§定案 7 判据属 ②
#   规范面），且存量补「互见」是内容回写、需语义判断（AI 不猜）⇒ 与 R2「不回溯」原意一致。
# 覆盖边界：只判「**有无该字段**」，**不判内容**（指向是否合理属 `adversarial-review.md` 面）；
#   `40_单案/`（案内自指，无互见语义）与 `30_行业版/`（I-CL 条目另制）**不适用**。
HUXIAN_WATERMARK = {   # 2026-09-26 冻结（族 → 族内 max 序号）
    "F-01": 31, "F-02": 6, "F-03": 5, "F-04": 5, "F-05": 17, "F-06": 16,
    "F-07": 18, "F-08": 3, "F-09": 12, "F-10": 5, "F-11": 8, "F-12": 8,
    "F-13": 8, "F-14": 17, "F-15": 5, "F-16": 4, "F-17": 2, "F-18": 1,
    "I-01": 6, "I-02": 14, "I-03": 15, "I-04": 6, "I-05": 9, "I-06": 2,
    "I-07": 7, "I-08": 4, "I-09": 12, "I-10": 3, "I-11": 9, "I-12": 9,
    "I-13": 7, "I-14": 4, "I-15": 4,
    "L-01": 19, "L-02": 6, "L-03": 11, "L-04": 4, "L-05": 9, "L-06": 9,
    "L-07": 10, "L-08": 5, "L-09": 8, "L-10": 2, "L-11": 12, "L-12": 9,
    "L-13": 9, "L-14": 5, "L-15": 12, "L-16": 2, "L-17": 2, "L-18": 1, "L-19": 2,
    "PL-01": 125, "PL-02": 122, "PL-03": 123, "PL-04": 122, "PL-05": 112,
    "S-01": 119, "S-02": 107, "S-03": 72, "S-04": 66,
    "WL-01": 22, "WL-02": 4, "WL-03": 9, "WL-04": 28, "WL-05": 13, "WL-06": 5,
    "WL-07": 25, "WL-08": 4, "WL-09": 20, "WL-10": 17, "WL-11": 22, "WL-12": 22,
    "WL-13": 10, "WL-14": 32, "WL-15": 40, "WL-16": 28, "WL-17": 22, "WL-18": 36,
    "WL-19": 6,
}
_RX_H3ID = re.compile(r"^((?:WL|PL|[FLIWS])-\d{6})")
_hx_miss, _hx_new = [], 0
for _f in (sorted(glob.glob(os.path.join(METHODS, DOMAIN_GLOB)))
           + sorted(glob.glob(os.path.join(METHODS, LANG_GLOB)))
           + sorted(glob.glob(os.path.join(METHODS, VOLUME_NAME, "*.md")))):
    try:
        _txt2 = io.open(_f, encoding="utf-8", errors="replace").read()
    except OSError:
        continue
    # 条目头在三个载体中一律为 `### <ID>…`，且条目内**无嵌套 h3**（实测核对）⇒ 可按 h3 切块。
    for _chunk in re.split(r"(?m)^###\s+", _txt2)[1:]:
        _first, _, _body = _chunk.partition("\n")
        _m = _RX_H3ID.match(_first)
        if not _m:
            continue
        _eid = _m.group(1)
        _pref, _rest = _eid.split("-")
        if int(_rest[2:]) > HUXIAN_WATERMARK.get("%s-%s" % (_pref, _rest[:2]), 0):
            _hx_new += 1
            if "**互见**：" not in _body:
                _hx_miss.append("%s(%s)" % (_eid, os.path.relpath(_f, METHODS).replace(os.sep, "/")))
if _hx_miss:
    ERRORS.append("入库强制字段缺失（第 21 项）：新增条目 **%d 条** 无「**互见**：」字段 —— %s"
                  "（无关联请写「**互见**：无」；水位表 `HUXIAN_WATERMARK`，存量不回溯）"
                  % (len(_hx_miss), "、".join(_hx_miss[:6])))


# ---------- 22. 登记表完整性对账（2026-09-26 WO-MF-04） ----------
# 病根（实证）：两张手写登记表的「单案文件」列与 `40_单案/` 实存**各自漂移、无人对账**——
#   2026-09-26 实测暴露三类：①孤本并入后旧名未同步（表 A／表 B／README 三处）；
#   ②新批 10 案（AN0086–0095）表 A 漏登；③计数声明滞后（表 B 标题 80、实况 90）。
#   全部属「文档说有什么 ⟷ 磁盘上有什么」不一致，且**跨 6 天两批蒸馏零告警**。
#
# 判据：**双向对账**（双向对账）
#   · extra   ＝ 表内登记的文件名，`40_单案/` 内**不存在**
#   · missing ＝ `40_单案/` 实存的文件，表内**未登记**
#   · 两侧**均报 WARN**（不阻断）：存量已对齐（2026-09-26 闭合），基线为空；
#     新增漂移随时可能来自「归档／改名未同步」——**报出来即可，不需 script 自动改**
#     （修复属语义判断：改表还是改文件，AI 不猜 ⇒ 与 C 档定位一致）。
#
# 权威口径（2026-09-26 用户裁定 R-9）：**表 B（`state/单案索引对照表.md`）为准**——
#   表 A（`方法论_案名规范表.md`）降为「白名单专用视图」；故两表**都查**，差异**分表报**，
#   以便定位是哪一张滞后。
# 覆盖边界：只判**文件名一致性**；**不判**案名↔案号↔cases 目录的对应正确性（属内容面）。
def _norm_cell(_x):
    """剥 Markdown 加粗/反引号/空白 —— 案号列存在 `**AN0076**` 形态，不剥会整行漏读。"""
    return _x.replace("**", "").replace("`", "").strip()

def _table_files(_path, _with_an):
    """从登记表抓「单案文件」列。返回 (文件名集, 案号集)。
    定位方式：**先在表头行找「单案文件」所在列号，再按该列取值**——
    两张表列数不同（表 A 末列＝单案文件；表 B 末列＝cases 目录），
    **禁按固定列位或末列取**（2026-09-26 实测：取末列会把表 B 的 cases 目录当文件名，误报 90 条漏登）。"""
    _files, _ans = set(), set()
    try:
        _t = io.open(_path, encoding="utf-8", errors="replace").read()
    except OSError:
        return None, None
    _col_f = None
    for _ln in _t.splitlines():
        if not _ln.strip().startswith("|"):
            continue
        _c = [_norm_cell(x) for x in _ln.strip().strip("|").split("|")]
        if not _c or set("".join(_c)) <= set("-: "):
            continue
        # 表头行：定位「单案文件」列（**每张表各设一次**——表一 4 列／表二 7 列，列号不同）
        if "单案文件" in _c:
            _col_f = _c.index("单案文件")
            continue
        _ai = next((i for i, x in enumerate(_c) if re.fullmatch(r"AN\d{4}", x)), None)
        if _ai is None:
            continue
        if _with_an:
            _ans.add(_c[_ai])
        _cand = _c[_col_f] if (_col_f is not None and _col_f < len(_c)) else _c[-1]
        if _cand.endswith(".md"):
            _files.add(_cand)
    return _files, _ans

_SGL_DIR = os.path.join(METHODS, SINGLE_NAME)
_sgl_actual = set(x for x in os.listdir(_SGL_DIR) if x.endswith(".md")) \
    if os.path.isdir(_SGL_DIR) else set()
# 表一「案号不连续」的**合法形态基线**：主库直入案（无单案文件，故不入表一）。
#   AN0074 胜业电气／AN0075 蘅东光 —— 2026-09-19 分配，登记于 `单案索引对照表.md` §二 台账。
#   基线内静默；**基线外**缺号才 WARN。新增基线须附来源（防把真欠账洗成基线）。
TABLE22_AN_GAP_OK = {"AN0074", "AN0075"}
_TB = {
    "表A 案名规范表": os.path.join(METHODS, CANON_TABLE),
    "表B 单案索引对照表": os.path.join(_ROOT, "state", CASE_INDEX_TABLE),
}
for _tname, _tpath in _TB.items():
    _tf, _tan = _table_files(_tpath, True)
    if _tf is None:
        UNVERIFIABLE.append("登记表完整性**无法核对**（第 22 项）：%s 读取失败" % _tname)
        continue
    _extra = sorted(_tf - _sgl_actual)
    _miss = sorted(_sgl_actual - _tf)
    if _extra:
        WARNS.append("登记表滞后（第 22 项 · %s）：登记了 **%d 个** `40_单案/` 内不存在的文件 —— %s"
                     "（多为归档/改名后未同步；权威口径见表 B）" % (_tname, len(_extra), "、".join(_extra[:6])))
    if _miss:
        WARNS.append("登记表漏登（第 22 项 · %s）：`40_单案/` 实存 **%d 个** 文件未登记 —— %s"
                     "（新案入库须同步登记；权威口径见表 B）" % (_tname, len(_miss), "、".join(_miss[:6])))
    if _tan is not None and _tan:
        _gap = sorted(set("AN%04d" % i for i in range(1, int(max(_tan)[2:]) + 1)) - _tan)
        # 合法形态：**主库直入案**（登记在表二台账「案号分配依据」、无单案文件）——
        #   AN0074 胜业电气／AN0075 蘅东光（2026-09-19 分配，见 `单案索引对照表.md` §二）。
        #   其号不在表一（表一＝有单案文件的案），故在表一面必然表现为「缺号」，**非欠账**。
        _gap = [g for g in _gap if g not in TABLE22_AN_GAP_OK]
        if _gap:
            WARNS.append("案号不连续（第 22 项 · %s）：AN0001–%s 间缺 %d 个 —— %s"
                         "（若为「主库直入案·无单案文件」属正常，请核表二台账）"
                         % (_tname, max(_tan), len(_gap), "、".join(_gap[:8])))


# ---------- 判定接口与退出码（WO-18 · 2026-09-26） ----------
# 判据：「**退出码不承载信息，报告才是接口**」。
# 故本脚本的**判定接口 ＝ 报告输出**（文本 ＋ `--json` 的 `warn` 字段与逐项 `issues`），
# **退出码只表「有无 ERROR」，不表 WARN** —— 自动化若只读退出码，须**另读报告**才能看见 WARN。
# 退出码：0 = 无 ERROR 且无 UNVERIFIABLE（可有 WARN）｜1 = 有 ERROR 或 UNVERIFIABLE｜2 = 前置失败｜3 = `--strict` 下 WARN > 0
# ---------- 三栏信号（WO-33 · 2026-09-26） ----------
# 承 通用实践「第三栏」判据：「**验了疑似不符**」与「**根本验不了**」**分两栏**；后者 always need
#   a decision。本库落为 `ERRORS` ／ `UNVERIFIABLE` ／ `WARNS(soft)` 三栏，且 **UNVERIFIABLE 计入
#   ERROR 与退出码** —— 若降级为 WARN 或静默跳过，「判不了」就永久隐形，正是本库两次「门禁假绿」
#   （I-0088 标签形态空转、蒸馏产物未归集长期不可见）的同一根因。
#   覆盖边界：本栏只收「**本该受检却判不了**」；「抽查只覆盖一部分」（如第 10 项 12/1689）属
#   **抽样局限**、不入本栏（已由 `locator_sampled/locator_pool` 两数透明化）。
# 2026-09-26 事实订正：原先记录「`--quiet` 吞掉 WARN」**不成立** —— ERROR/WARN 循环本就在
#   `if not quiet` 之外，两种模式下均照常打印；`--json` 亦早已含 `warn`。真实缺口仅为
#   「退出码看不见 WARN」，而按上引判据，这**本就不该由退出码承载**。
# ---------- WARN 档位约定（WO-19 · 2026-09-26） ----------
# 本库 WARN **一律 soft**（`severity=soft`）：只进报告、只记日志，**不影响退出码**。
# 需要阻断的场景**不设 hard WARN**，而应把该检查**升格为 ERROR 项**——档位保持单一，避免软硬混用。
# 关于「警告生命周期绑定检查」（停用某检查 ⇒ 清除其旧 `lint_warnings`）：
#   **本库不适用** —— 本脚本每次**全库无状态重算**，WARN 由当前实况现场算出、不落盘、无陈旧态可清
#   ⇒ 该机制解决的是**有状态系统**的「陈旧警告」问题，本库结构上不存在该问题（**设计优势，非缺口**）。
#   若要观测「新增／已消」的动向，不靠陈旧警告，而靠**操作日志逐次留痕 ＋ 计数 diff**（见 WO-26）。
# ---------- 23. 库内 schema 水位（库自描述完整性 · 2026-09-28） ----------
# 病根：schema（规则本体）在 skill 包内、库在库外，两者**各自版本流**。规则改了、库的自描述
#   却要等人记得重生成——**忘了就悄悄过期，且无任何信号**。本项把「库自描述是否跟得上」变成机器可验。
# 单一事实源：① 库内水位 ← `SCHEMA.md`「schema 版本水位」行；② skill 实况 ← `SKILL.md` 的 `version:`。
# 档位：缺失／滞后**均报 WARN（soft）**——理由是**可移植性**：本 skill 分发给他人时其库未必生成过
#   SCHEMA.md，若报 ERROR 会让对方基线一上来就红。需阻断的场合可后续升格为 ERROR 项。
# 自愈：`gen_schema.py` 已并入 `refresh_index.py` 的刷新链 ⇒ 正常节奏下（每次蒸馏后刷索引）自动跟上。
try:
    _sc_p = os.path.join(METHODS, SCHEMA_BASENAME)
    if not os.path.isfile(_sc_p):
        # **档位分两层**（2026-09-28 定）：缺失＝库**结构性**失去自描述，且该生成步**已并入索引
        #   刷新链**（正常节奏下不该缺）⇒ 报了就是真问题，故升 ERROR。滞后属**瞬时态**、下次刷索引
        #   即自愈 ⇒ 报 WARN。二者分开，既不让自愈中的状态污染 0-ERROR 基线，也不让结构损失静默。
        ERRORS.append("库内 schema 入口**缺失**（第 23 项）：`%s` 不存在 ⇒ 本库**失去自描述能力**"
                      "（由哪一版规矩管、规矩在哪读，只能靠使用者的库外记忆去兜）。"
                      "重生成：`python gen_schema.py --methods-root <工作区根>`"
                      % SCHEMA_BASENAME)
    else:
        _sc_full = io.open(_sc_p, encoding="utf-8", errors="replace").read()
        _sc_txt = _sc_full[:4000]
        _wm = re.search(r"schema\s*版本水位[^\n]*?`([^`\n]+)`", _sc_txt)
        _sk_txt = io.open(os.path.join(str(SKILL_DIR), "SKILL.md"), encoding="utf-8").read(4000)
        _sv = re.search(r"(?m)^version:\s*(\S+)", _sk_txt)
        if not _wm or not _sv:
            UNVERIFIABLE.append("库内 schema 水位**无法核对**（第 23 项）：`%s` 缺水位行，或 `SKILL.md` 缺 `version:`"
                                % SCHEMA_BASENAME)
        elif _wm.group(1) != _sv.group(1):
            WARNS.append("库内 schema 水位**滞后**（第 23 项）：`%s` 记 **%s** ／ skill 实况 **%s**"
                         " ⇒ 库的自描述已过期（重生成：`python gen_schema.py --methods-root <工作区根>`；"
                         "该步已并入索引刷新链，下次蒸馏会自动跟上）"
                         % (SCHEMA_BASENAME, _wm.group(1), _sv.group(1)))
        # 23b **导航路径存在性**：第三节「规矩在哪读」已改**派生**（扫 references/**），但**仍须校验**——
        #   防手改残留、生成器退化、或删册后未及时重生成。派生表的失败方向本该是「多扫」，
        #   这里补一道**存在性**网，把「指向已不存在的册子」变成可见信号。
        _nav = re.findall(r"`ibd-methods-ops/(references/[^`]+?\.md)`", _sc_full)
        _nav = sorted(set(_nav))
        if not _nav:
            UNVERIFIABLE.append("库内 schema 的**导航表为空**（第 23 项）：第三节未列出任何册子路径 ⇒ "
                                "该表可能未派生成功（须为扫 `references/**/*.md` 所得）")
        _miss = [x for x in _nav if not os.path.isfile(os.path.join(str(SKILL_DIR), x))]
        if _miss:
            WARNS.append("库内 schema 导航**指向不存在的册子**（第 23 项）：%s ⇒ 册子已删/改名而未重生成，"
                         "或本文件被手改（重生成：`python gen_schema.py --methods-root <工作区根>`）"
                         % "、".join(_miss[:5]))
except OSError as _e:
    UNVERIFIABLE.append("库内 schema 水位**无法核对**（第 23 项）：%s" % _e)


# ---------- 24. 增量裸页码（基线不上升 · 2026-09-28） ----------
# 口径：**溯源达标（A1）的可验抓手**——存量裸页码按设计边界「不回溯补注」，但**增量不得再产生**
#   （契约：凡引用须写来源代号）。判据 ＝「计数不得高于 `BARE_PAGE_BASELINE`」：
#   上升 ⇒ ERROR（新增了裸页码）；持平 ⇒ PASS；下降 ⇒ WARN（提示复核后下调基线，防基线松弛成摆设）。
# 与 `check_evidence.py` 用**同一套**判据（同两条正则 ＋ 同一别名表）⇒ 两处读数应一致。
_CIT_RX24 = re.compile(r"（([^（）]*?(?:PAGE|P)\s*\d+[^（）]*)）")
_PAGE_TOK_RX24 = re.compile(r"(?:PAGE|P)\s*(\d+)(?:\s*[-–—~至]\s*(\d+))?")
_SEP24 = re.compile(r"[\s、,，:：]+")


def _bare_page_count():
    """统计活文档内「省略来源代号的裸页码标注」数；缺映射表 ⇒ 返回 None（不可核对）。"""
    _mp = os.path.join(METHODS, GENERATED_NAME, "来源代号映射.json")
    if not os.path.isfile(_mp):
        return None
    with io.open(_mp, encoding="utf-8") as _fh:
        _M24 = json.load(_fh)
    _a2c = {}
    for _code, _alist in (_M24.get("aliases") or {}).items():
        for _a in _alist:
            _a2c.setdefault(_a, _code)
        _a2c.setdefault(_code, _code)
    _files = list(_layout_domain_files(METHODS))
    for _d in (DIR_DOMAIN, DIR_LANG, DIR_VOLUME):
        _dp = os.path.join(METHODS, _d)
        if os.path.isdir(_dp):
            for _f in sorted(os.listdir(_dp)):
                if _f.endswith(".md"):
                    _files.append(os.path.join(_dp, _f))
    _n = 0
    for _fp in sorted(set(_files)):
        try:
            _txt = io.open(_fp, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for _blk in re.split(r"(?m)^### ", _txt)[1:]:
            for _m in _CIT_RX24.finditer(_blk):
                _lbl = _m.group(1)
                if not _PAGE_TOK_RX24.search(_lbl):
                    continue
                _has = False
                for _part in re.split(r"[；;]", _lbl):
                    if not _PAGE_TOK_RX24.search(_part):
                        continue
                    _head = _SEP24.sub(" ", _PAGE_TOK_RX24.sub("", _part)).strip()
                    for _al in _a2c:
                        if _al and _al in _head:
                            _has = True
                            break
                    if _has:
                        break
                if not _has:
                    _n += 1
    return _n


try:
    _nbp = _bare_page_count()
    if _nbp is None:
        UNVERIFIABLE.append("增量裸页码**无法核对**（第 24 项）：缺 `%s/%s/来源代号映射.json`"
                            "（先跑 `gen_source_map.py`）" % (METHODS, GENERATED_NAME))
    elif _nbp > BARE_PAGE_BASELINE:
        ERRORS.append("**新增裸页码**（第 24 项）：当前 **%d** 处 ＞ 基线 **%d** 处 ⇒ 有 **%d 处**引用未写来源代号"
                      "（违「凡引用必写来源代号」契约）。存量按设计边界**不回溯补注**，但**增量不得再产生**；"
                      "修复＝回到产生该引用的那一批产出，**逐处补来源代号**（语义面，须人裁定）"
                      % (_nbp, BARE_PAGE_BASELINE, _nbp - BARE_PAGE_BASELINE))
    elif _nbp < BARE_PAGE_BASELINE:
        WARNS.append("裸页码**低于基线**（第 24 项）：当前 **%d** 处 ＜ 基线 **%d** 处 ⇒ 复核无碍后应**下调** "
                     "`BARE_PAGE_BASELINE`（防基线松弛、久成摆设）" % (_nbp, BARE_PAGE_BASELINE))
except OSError as _e:
    UNVERIFIABLE.append("增量裸页码**无法核对**（第 24 项）：%s" % _e)


# ---------- 25. skills 消费侧库事实引用（2026-09-29 新增 · R-0065） ----------
# 判据：skills 面活文档**禁硬编码库计数/路径**——一律指针化（「实况见库索引」）或生成时派生。
#   （首读面体积硬编码即先例：写 ≈11KB/≈137KB、实测 81KB，1.33.0 批改「生成时派生」根治单点，
#     本项把该治理从单点升为**系统护栏**。）
# 漂移根因＝库侧变更（蒸馏/重蒸/重构）⇒ 护栏挂库侧体检（**变更即校验**），
#   不挂 skilldev 普查（周期性、滞后）。消费面＝本脚本上三级的 skills 根（含 docs/ 体系文档）。
# 两层（a 硬判 / b 提示；修复＝改引用方文档，属内容面 ⇒ 授权档 B「报数不改」）：
#   a) **生成物引用断链**：文档引用生成物文件名（`GENERATED_BASENAMES` 单一事实源）任一
#      ⇒ 实测库内存在（`_generated/` 下；SCHEMA.md 例外留**库根**——「打开库即可见」设计，
#      同裸页码水位例外）；缺失 ⇒ ERROR——生成物改名/退役时引用方静默断链，
#      正是「路径漂移」主形态（同族病：gen_schema.py 手写册子路径清单，2026-09-28 已治）。
#   b) **同形计数漂移**：库实况值（单案数＝第 11 项实测 `_scope_checked`）vs 文档
#      「两位以上数字＋窄单位词」（案例/案/条目/条改写/插入点）——数字不等于实况值
#      ⇒ WARN（**不判必错**：阈值规则／历史叙述的同形数字由人裁定，AI 不替作者推断，同第 24 项判据）。
# 排除面：CHANGELOG（历史留痕惯例）、SKILL_TREE（生成物）、adr/（决策史）、
#   文件名含 archive（历史档案）、docs/ 下 incident-log*（事故史）与 pending-rules.md（裁定史）
#   ——数字全是「发生过什么」的当时实况、非活口径（同 CHANGELOG 排除理由）；
#   _backup/templates 等非活文档目录。
_SKILLS_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SKILL_SKIP_DIRS = {".git", "node_modules", "__pycache__", "_backup", "archive", "adr",
                    "templates", "_generated", ".scratch", "state", "logs"}
_SKILL_SKIP_FILES = {"CHANGELOG.md", "SKILL_TREE.md", "pending-rules.md"}
_RX_LIBFACT_NUM = re.compile(r"(\d{2,6})\s*(?:个|份|条)?\s*(案例|案(?!例)|条目|条改写|插入点)")
_libfact_broken, _libfact_count_hits, _libfact_scanned = [], [], 0
if os.path.isdir(_SKILLS_ROOT):
    for _dp, _dns, _fns in os.walk(_SKILLS_ROOT):
        _dns[:] = [d for d in _dns if d not in _SKILL_SKIP_DIRS]
        for _fn in _fns:
            if not _fn.endswith(".md") or _fn in _SKILL_SKIP_FILES \
                    or "archive" in _fn.lower() or _fn.startswith("incident-log"):
                continue
            _fp = os.path.join(_dp, _fn)
            try:
                _txt = io.open(_fp, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            _libfact_scanned += 1
            _rel = os.path.relpath(_fp, _SKILLS_ROOT)
            for _gb in GENERATED_BASENAMES:
                if _gb not in _txt:
                    continue
                # 位置例外：SCHEMA.md 按设计留**库根**（「打开库即可见」，同裸页码水位例外）；
                #   其余生成物在 `_generated/`。两处任一存在即合法。
                _ok = os.path.isfile(os.path.join(METHODS, GENERATED_NAME, _gb)) or \
                    (_gb == SCHEMA_BASENAME and os.path.isfile(os.path.join(METHODS, _gb)))
                if not _ok:
                    _libfact_broken.append("%s 引用 %s（库内缺失）" % (_rel, _gb))
            for _m in _RX_LIBFACT_NUM.finditer(_txt):
                if int(_m.group(1)) != _scope_checked:
                    _ln = _txt.count("\n", 0, _m.start()) + 1
                    _libfact_count_hits.append("%s:%d（%d %s）"
                                               % (_rel, _ln, int(_m.group(1)), _m.group(2)[0:3]))
else:
    UNVERIFIABLE.append("skills 消费面**无法定位**（第 25 项）：上三级 %s 不存在" % _SKILLS_ROOT)
if _libfact_broken:
    ERRORS.append("skills 活文档**生成物引用断链** %d 处（第 25 项）：生成物已改名/退役而引用方未跟 ⇒ %s；"
                  "修复＝引用方改指针表述或新名（内容面，授权档 B）"
                  % (len(_libfact_broken), "；".join(_libfact_broken[:6])))
if _libfact_count_hits:
    WARNS.append("skills 活文档出现**与库计量同形**的数字 %d 处（第 25 项），与库实况"
                 "（单案 %d 案）不一致——是否库事实引用漂移**由人核**（不判必错，可忽略；"
                 "阈值规则/历史叙述为合法同形）：%s"
                 % (len(_libfact_count_hits), _scope_checked,
                    "；".join(_libfact_count_hits[:10])))
if not _args.quiet and not _args.json:
    print("skills 消费面扫描（第 25 项）: %d 个活文档｜生成物引用断链 %d ｜同形计数待核 %d"
          % (_libfact_scanned, len(_libfact_broken), len(_libfact_count_hits)))


# ---------- 事件留痕：体检落一行（WO-26 · 2026-09-26） ----------
# 判据：「N issues found, M auto-fixed」——每次体检落一行事件，
#   使「新增／已消」的动向可从事件序列 diff 得出（本库无自动修复 ⇒ auto-fixed 恒 0，改记实际四数）。
# 落点：<工作区根>/logs/库操作日志.md（**append-only**）。
#   ★ 为何落 logs/ 而非 state/：按 state/README.md 的分工判据 —— `logs/` ＝「**发生过什么**」、
#     `state/` ＝「**现在到哪了**」；操作日志属前者。`state/` **不重复**（避免两处不同步）。
#   ★ 本项**只追加、不改判定**：写入失败只记 WARN，绝不影响 ERROR/退出码。
#   ★ **同日同结果去重（2026-09-27 补 · 承「体检刷屏 29 次」复盘）**：
#     原实现每次运行一律追加 ⇒ 同日反复跑体检（改库验证时常见）会刷屏
#     （实测 2026-09-26 单日 29 条，其中连续 11 条结果完全相同）。
#     判据：**同日 + 同「结果行」已有记录 ⇒ 跳过**（结果行含 ERROR/WARN/正文/索引/单案五数，
#     任一数不同即视为新事件、照常追加 ⇒ 不丢「新增/已消」的动向）。
#     与 `log_event.py --no-dup` 的分工：两者判据同源（防同日重复），
#     本脚本**内联实现**而非跨脚本调用——避免体检对 log_event 产生运行期依赖
#     （体检是门禁件，须能独立跑；写入失败亦只记 WARN、不影响退出码）。
#     `--no-log` 可关闭整项；`--allow-dup` 可强制追加（需复现同日同结果时用）。
if not _args.no_log:
    try:
        _ld = os.path.join(_ROOT, "logs")
        os.makedirs(_ld, exist_ok=True)
        _lpath = os.path.join(_ld, "库操作日志.md")
        _today = time.strftime("%Y-%m-%d")
        _result_line = ("- 结果：ERROR %d ／ UNVERIFIABLE %d ／ WARN %d ｜ 正文 %d ｜ 索引行号抽查 %d/%d ｜ 单案 %d"
                        % (len(ERRORS), len(UNVERIFIABLE), len(WARNS), fm_checked,
                           _locator_sampled, _locator_checked, _scope_checked))
        # 去重：扫全文，若同日同结果行已存在同格式条目 ⇒ 跳过
        _dup = False
        if not _args.allow_dup and os.path.exists(_lpath):
            _prev = io.open(_lpath, encoding="utf-8", errors="replace").read()
            for _m in re.finditer(
                    r"^##\s*\[(\d{4}-\d{2}-\d{2})\]\s*体检\s*\|\s*方法论库\s*$", _prev, re.M):
                _seg = _prev[_m.end():_m.end() + 400]
                if _m.group(1) == _today and _result_line in _seg:
                    _dup = True
                    break
        if _dup:
            # 不记 WARN —— 去重是正常行为，记 WARN 会污染巡检基线（WARN 7→8）
            # 只用 stdout 告知（`--quiet` 下静默）。
            if not _args.quiet and not _args.json:
                print("· 事件留痕跳过（同日同结果已存在；`--allow-dup` 可强制）")
        else:
            with io.open(_lpath, "a", encoding="utf-8", newline="\n") as _lf:
                _lf.write("\n## [%s] 体检 | 方法论库\n" % _today)
                _lf.write(_result_line + "\n")
                _lf.write("- 依据：check_methods_health.py\n")
    except OSError as _e:
        WARNS.append("事件留痕失败（不影响判定）：%s" % _e)

_verdict = "FAIL" if (ERRORS or UNVERIFIABLE) else "PASS"
if _args.strict and WARNS and not ERRORS and not UNVERIFIABLE:
    _verdict = "WARN-STRICT"
_summary = {
    "tool": "check_methods_health", "target": METHODS, "verdict": _verdict,
    "error": len(ERRORS), "warn": len(WARNS), "unverifiable": len(UNVERIFIABLE),
    "scanned": fm_checked,
    "locator_pool": _locator_checked, "locator_sampled": _locator_sampled,
    "scope_checked": _scope_checked,
    "issues": ([{"level": "ERROR", "severity": "hard", "msg": m} for m in ERRORS] +
               [{"level": "UNVERIFIABLE", "severity": "unknown", "msg": m} for m in UNVERIFIABLE] +
               [{"level": "WARN", "severity": "soft", "msg": m} for m in WARNS]),
}
if _args.json:
    print(json.dumps(_summary, ensure_ascii=False))
else:
    if not _args.quiet:
        print("=== 方法论全库健康检查 ===")
        print("正文文件（frontmatter 校验）: %d 个｜索引行号抽查: %d/%d 条（抽样/池）｜单案内容范围: %d 案"
              % (fm_checked, _locator_sampled, _locator_checked, _scope_checked))
    print("ERROR %d 项" % len(ERRORS))
    for e in ERRORS:
        print("  [ERROR] %s" % e)
    if UNVERIFIABLE:
        print("UNVERIFIABLE %d 项（**验不了**：本应受检却缺输入/脚本/文件 ⇒ 计入 ERROR 与退出码；"
              "**不得当通过**）" % len(UNVERIFIABLE))
        for u in UNVERIFIABLE:
            print("  [UNVERIFIABLE] %s" % u)
    if WARNS:
        print("WARN %d 项（一律 soft：只记日志，不影响退出码；需阻断者应升格为 ERROR 项）" % len(WARNS))
        for w in WARNS:
            print("  [WARN·soft] %s" % w)
sys.exit(1 if (ERRORS or UNVERIFIABLE) else (3 if (_args.strict and WARNS) else 0))

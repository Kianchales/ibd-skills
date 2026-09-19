#!/usr/bin/env python3
"""方法论全库健康护栏（10 项检查 · 防结构漂移）

用法：
    python check_methods_health.py [--methods-root <库根目录>] [--quiet]

参数：
    --methods-root  方法论库根目录（其下应有 methods/ 子目录）；默认取环境变量 METHODS_ROOT，
                    未设置时按脚本所在目录的上级推断（脚本随库存放于 <库根>/scripts/ 时零参数可用）
    --quiet         只输出异常项

检查项：
1. frontmatter 完整性  正文 md（排除 archive/ 与自动生成白名单）必须：首行 ---、有闭合 ---、字段 key: value、正文首行 #
2. 空 h3               ^###\\s*$ 不得存在（标题后无内容）
3. 编号健康            全局唯一性（跨文件）+ 族内连续（每域每族 1..N）+ 登记表一致（登记表编号均存在）
4. 路由表一致性        入口路由表「条目数」列 vs 实算（与 parse/gen_entry 同口径，防 h3 计数漂移）
5. parsed TOTAL 一致性 parsed_titles.txt 首行 TOTAL= vs 实算（防 parse 陈旧 → 目录/索引滞后）
6. W 编号唯一性        W 系列条目编号不得重复（支持 WL- 格式）
7. 交叉引用有效性      正文引用 [FLIW]L?-\\d{6} 必须存在（旧格式历史注记跳过）
8. 域文件体积警戒线    单域文件 >300KB 触发 WARN + 族级拆分预案提示（防二阶膨胀复发）

退出码：0 = 全部通过（WARN 不阻塞）；1 = 存在 ERROR
"""
import argparse, io, json, os, re, glob, random, sys
from pathlib import Path

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_ap = argparse.ArgumentParser(description="方法论全库健康护栏（10 项检查）")
_ap.add_argument("--methods-root", default=os.environ.get("METHODS_ROOT", ""),
                 help="方法论库根目录（默认 $METHODS_ROOT，或脚本上级目录）")
_ap.add_argument("--quiet", action="store_true", help="只输出异常项")
_ap.add_argument("--json", action="store_true", help="输出结构化 JSON（供上层消费）")
_args = _ap.parse_args()

_ROOT = Path(_args.methods_root) if _args.methods_root else Path(__file__).resolve().parents[1]
METHODS = str(_ROOT / "methods")
SCRIPTS = str(_ROOT / "scripts")
ENTRY = os.path.join(METHODS, "通用方法论_最终版.md")
PARSED = os.path.join(SCRIPTS, "parsed_titles.txt")



def _require_library():
    """冷启动前置检查：未找到方法论库时给出清晰指引，而非堆栈崩溃"""
    import sys as _s
    if not os.path.isdir(METHODS):
        _s.stderr.write("✗ 未找到方法论库：%s\n" % METHODS)
        _s.stderr.write("  用法：--methods-root <库根目录>（或设环境变量 METHODS_ROOT）\n")
        _s.stderr.write("  首次使用：按 SKILL.md「库配置」四问引导接入你的库；库结构规范见 references/methods-guide.md\n")
        _s.exit(2)


_require_library()

# 域文件体积警戒线：超过即 WARN 并提示拆分预案
DOMAIN_SIZE_WARN_BYTES = 300 * 1024

# 自动生成/工具文件白名单（合法无 frontmatter）
WHITELIST = {
    "README.md",
    "方法论_条目标题目录.md",
    "方法论调用索引.md",
    "方法论调用索引_备份_20260831.md",
    "编号登记表.md",
    "行业方法论_合并映射.md",
}

ERRORS, WARNS = [], []


def count_entries(fname, content):
    """与 parse_titles.py / gen_entry.py 同口径：域文件=(N) 或 v37 身份编号条目；W 系列=WD+WD_LIST+h3。"""
    if fname.startswith("投行语言专项"):
        n_wd = len(re.findall(r"^\*\*((?:WL|W|PL)-[A-Za-z0-9\-·~]+)", content, re.M))
        n_wdl = len(re.findall(r"^-\s*\*\*((?:WL|W|PL)-[A-Za-z0-9\-·~]+)\*\*", content, re.M))
        n_h3 = len(re.findall(r"^### ((?:WL|W|PL)-\d{6})", content, re.M))   # h3 形态（2026-09-19 补 PL-）
        return n_wd + n_wdl + n_h3
    # 2026-09-19 补 S-（体例域批次卷）
    return len(re.findall(r"^### [FLIWS]-\d{6}|^### （\d+）", content, re.M))


# ---------- 收集全部 md ----------
# 检查范围 = 方法论正文本体：methods 根目录活跃文件 + 行业方法论_单份细分版/（活跃子集）
# 排除：archive/（历史归档，2026-09-01 起原 _backup/ 并入）、notes/（历史蒸馏笔记）、
#     分卷/（域文件分卷产物，无独立 # 标题结构，不适用 frontmatter 后须有 h1 的规则；2026-09-19 补）
SKIP_DIRS = {"archive", "notes", "_backup", "__pycache__"}   # 2026-09-19：分卷纳入（手写条目正文外置件）
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
    if fn.startswith("通用方法论_") and fn.endswith("域.md"):
        # 域文件：v37 标题 ### F-010001xxx；兼容旧格式 ### （N）
        old_nums = []
        for l in lines:
            s = l.strip()
            m = re.match(r"^### ([FLIW])-(\d{6})", s)
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
               list(re.finditer(r"^### ((?:WL|W)-\d{6})", content, re.M))
        for m in wids:
            wid = m.group(1)
            if wid in all_ids:
                ERRORS.append("编号跨文件重复: %s 同时出现在 %s 与 %s" % (wid, all_ids[wid], rel))
            all_ids[wid] = rel

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
    reg_ids = set(re.findall(r"[FLI]-\d{6}", reg_txt)) | set(re.findall(r"WL-\d{6}", reg_txt))
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
    for fn, declared in route.items():
        p = os.path.join(METHODS, fn)
        if not os.path.exists(p):
            # 2026-09-19：路由表条目可能位于 分卷/ 子目录
            p = os.path.join(METHODS, "分卷", fn)
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
    _scan = sorted(glob.glob(os.path.join(METHODS, "通用方法论_*域.md"))) \
          + sorted(glob.glob(os.path.join(METHODS, "投行语言专项_*.md"))) \
          + sorted(glob.glob(os.path.join(METHODS, "分卷", "*.md")))   # 2026-09-19 纳入分卷
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
for df in sorted(glob.glob(os.path.join(METHODS, "投行语言专项_*.md"))):
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
for df in sorted(glob.glob(os.path.join(METHODS, "通用方法论_*域.md"))) + sorted(glob.glob(os.path.join(METHODS, "投行语言专项_*.md"))):
    rel = os.path.relpath(df, METHODS)
    with io.open(df, encoding="utf-8") as f:
        lines = f.read().splitlines()
    for i, l in enumerate(lines):
        s = l.strip()
        if not s or s.startswith("#") or s.startswith("|") or s.startswith(">"):
            continue
        for m in re.finditer(r"(?<![A-Za-z])([FLIW]L?-\d{6})", s):
            ref = m.group(1)
            if re.match(r"^W-00", ref):  # 旧 W 系列编号（历史注记/索引保留）
                continue
            if ref not in all_ids:
                ERRORS.append("交叉引用无效 %s L%d: %s（目标编号不存在，需核对登记表/迁移）" % (rel, i + 1, ref))

# ---------- 9. 域文件体积警戒线（2026-09-03 新增） ----------
# 对象：四域文件 + 投行语言专项（与拆分代次同一口径）；超线 WARN 不阻塞，提示族级拆分预案
for df in sorted(glob.glob(os.path.join(METHODS, "通用方法论_*域.md"))) + sorted(glob.glob(os.path.join(METHODS, "投行语言专项_*.md"))):
    size = os.path.getsize(df)
    if size > DOMAIN_SIZE_WARN_BYTES:
        WARNS.append(
            "域文件体积超警戒线 %s: %.0fKB > 300KB——登记族级拆分预案（按登记表最大族先行外置，"
            "外置部分入 archive/ 并在路由表登记指针；蒸馏只追加不重排）" % (os.path.basename(df), size / 1024)
        )

# ---------- 10. 索引行号定位抽查（2026-09-19 新增） ----------
# 背景：编号 →「文件 + 行号」是定向读取的唯一键；改内容未刷索引 ⇒ 行号漂移 ⇒ 定向读会读到
# **别的条目且不报错**（静默缺陷）。既有各项只校验「条目数」一致，不校验行号指向。
_TOC = os.path.join(METHODS, "方法论_条目标题目录.md")
if os.path.exists(_TOC):
    _rows, _grp, _appx = [], None, None
    for _ln in io.open(_TOC, encoding="utf-8", errors="replace").read().splitlines():
        if _ln.startswith("## "):
            _tt = _ln[3:].strip()
            _am = re.match(r"^附：([WP]) 系列", _tt)
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
            elif _appx == "W":
                _rows.append((_m.group(1), "投行语言专项_W系列.md", int(_cells[2])))
    if _rows:
        random.seed(20260919)
        _miss = []
        for _eid, _fn, _lnno in random.sample(_rows, min(12, len(_rows))):
            _p = next((x for x in (os.path.join(METHODS, _fn), os.path.join(METHODS, "分卷", _fn))
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

# ---------- 输出 ----------
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
    print("正文文件（frontmatter 校验）: %d 个｜索引行号抽查: %d 条" % (fm_checked, _locator_checked))
print("ERROR %d 项" % len(ERRORS))
for e in ERRORS:
    print("  [ERROR] %s" % e)
if WARNS:
    print("WARN %d 项" % len(WARNS))
    for w in WARNS:
        print("  [WARN] %s" % w)
sys.exit(1 if ERRORS else 0)

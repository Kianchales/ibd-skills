#!/usr/bin/env python3
"""反向视图：从全库单向引用现算「入度 / 失效 / 单向」——**生成物，读时现算，零增量状态**。

用法：
    python gen_refgraph.py [--methods-root <工作区根>] [--json] [--limit N]

参数：
    --methods-root  工作区根（= 库根，其下含 methods/；默认 $METHODS_ROOT，或脚本上级目录）
    --json          输出结构化 JSON（不写文件）
    --limit         各栏示例条数上限（默认 40）

定位（2026-09-26）：
    本库**不建反链**——反向引用信息**读时现算、不落盘为字段**。本脚本即那个「反向视图」：
    由已有单向引用（`互见` 等）重算，产出 `_generated/方法论_引用图谱.md`。
    · 与「双向手维反链」的区别：不新增字段、不写回条目、无 N×M 破坏面、无增量状态可漂移。
    · **禁止**把它当反链字段的替身去回写条目。

三栏口径：
    ① **失效引用（旧称：悬空引用）** —— 引用目标不在「登记面」内（登记面＝位置目录编号 ∪ 行业合并版 I-CL 编号）
    ② **无引用条目** —— 入度为 0（登记在册、但无任何其它条目引用它）
    ③ **单向引用** —— A→B 而 B 未→A（**仅提示**，不自动补、不回写）
    另附「高入度 TOP」供观察枢纽条目；「材料-产出对账」为**库存对账**（库存
    概念）：`cases/` 已采集材料 ↔ `40_单案/` 已蒸馏产出，缺口即 **backlog 提醒**（非错误）。

两列扩展（WO-36 · 2026-10-17）：
    ④ **零出链条目** —— 条目自身无任何出边（既无出向引用、也无互见）⇒ **仅报告**，
       与「无引用条目」（入度=0）互补：前者没人指向它，后者它不指向别人。
       豁免：`互见：无` 显式声明者**不计**零出链（声明即合法孤岛）；index/log 类生成物不在扫描面。
    ⑤ **案级来源聚合** —— 解析条目块内 `<案名>实证`／`<案名>（ANxxxx）` 标签与
       `（<来源简称> P页码）` 标注，聚合「编号 → 关联案号（经 `state/单案索引对照表.md`）」。
       **用途锚定材料缺口补蒸场景**：某案补蒸/订正时一查即得受影响条目。
       解析失败/案名无法映射 AN 者**显式计数**（`unmapped`），**禁猜、禁静默丢弃**。

重要边界（诚实声明）：
    · 本脚本**只报不建议、不阻断**：退出码恒 0（除非脚本自身异常）。
    · 引用提取正则（`RX_REF`）＝ `_lib/layout.py` 的 `RX_ID_FAMILY`（**全族单一事实源**）。
      2026-09-26 已统一：此前本文件为局部字面量且漏 `PL-`，与体检第 8 项**各自漂移**
      （同一库「体检报 12 失效 / 图谱报 7 失效」）⇒ 现两处同源同面（实测同为 13）。
    · 输出**不含时间戳**，以保证重跑幂等（可 diff 自证）。
"""
import argparse, io, json, os, re, sys
from collections import Counter, defaultdict

import sys as _s
if hasattr(_s.stdout, "reconfigure"):
    _s.stdout.reconfigure(encoding="utf-8")

_ap = argparse.ArgumentParser(description="反向视图：入度 / 失效 / 单向")
_ap.add_argument("--methods-root", default=os.environ.get("METHODS_ROOT", ""),
                 help="工作区根（= 库根，其下含 methods/；默认 $METHODS_ROOT，或脚本上级目录）")
_ap.add_argument("--json", action="store_true", help="输出结构化 JSON（不写文件）")
_ap.add_argument("--limit", type=int, default=40, help="各栏示例条数上限（默认 40）")
_ap.add_argument("--cases-root", default="",
                 help="材料层（`cases/`）所在工作区根；默认同 `--methods-root`。"
                      "**用途**：重跑校验在**临时根**重跑时，材料层仍指向真实库（否则对账栏全 0、误报非幂等）")
_args = _ap.parse_args()

import os as _lo, sys as _ls
_ls.path.insert(0, _lo.path.dirname(_lo.path.abspath(__file__)))
from _lib.layout import (resolve as _layout_resolve, TOC_FILE, REFGRAPH_FILE,
                         DIR_DOMAIN, DIR_LANG, DIR_INDUSTRY_MERGED, SINGLE_NAME,
                         VOLUME_NAME, GENERATED_NAME, SKIP_DIRS_BASE, RX_ID_FAMILY,
                         RX_DECLARED_HIST)
_ROOT, METHODS, SCRIPTS = _layout_resolve(_args.methods_root)
RX_DECLARED = re.compile(RX_DECLARED_HIST)

# ── 引用提取正则：**统一引用 `_lib/layout.py` 的全族常量**（2026-09-26）
# 原为局部字面量，且**与体检第 8 项各自维护** ⇒ 两处漂移（本脚本漏 `PL-`，导致同一库
#   「体检报 12 个失效 / 图谱报 7 个」）。**编号族「形态枚举不全」已五犯** ⇒ 收为单一事实源。
RX_REF = re.compile(RX_ID_FAMILY)
RX_HEAD = re.compile(r"^#{3,4}\s*((?:[FLIW]L?|S)-\d{6}|I-CL\d{2}-\d{2})")
RX_ICL = re.compile(r"^(?<![A-Za-z])I-CL\d{2}-\d{2}")

SCAN_DIRS = (DIR_DOMAIN, DIR_LANG, DIR_INDUSTRY_MERGED, SINGLE_NAME, VOLUME_NAME)


def _require_library():
    if not os.path.isdir(METHODS):
        sys.stderr.write("✗ 未找到方法论库：%s\n" % METHODS)
        sys.stderr.write("  用法：--methods-root <工作区根>（或设环境变量 METHODS_ROOT）\n")
        sys.exit(2)


_require_library()


def scan_files():
    """返回正文面全部 md（跳过 archive/notes/_backup/_generated/__pycache__）。"""
    out = []
    for sub in SCAN_DIRS:
        d = os.path.join(METHODS, sub)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".md"):
                continue
            rel = "%s/%s" % (sub, fn)
            if any(b in rel.split("/") for b in SKIP_DIRS_BASE):
                continue
            out.append((rel, os.path.join(d, fn)))
    return out


def build_universe(files):
    """登记面 ＝ 位置目录编号 ∪ 行业合并版内的 I-CL 编号（I-CL 不在位置目录登记）。"""
    uni = set()
    toc = os.path.join(METHODS, TOC_FILE)
    if os.path.exists(toc):
        for ln in io.open(toc, encoding="utf-8", errors="replace"):
            m = re.match(r"\|\s*([A-Z]{1,3}-\d{6})\s*\|", ln)
            if m:
                uni.add(m.group(1))
    for rel, path in files:
        if not rel.startswith(DIR_INDUSTRY_MERGED + "/"):
            continue
        for ln in io.open(path, encoding="utf-8", errors="replace"):
            m = RX_HEAD.match(ln.strip())
            if m and m.group(1).startswith("I-CL"):
                uni.add(m.group(1))
    return uni


def build_graph(files, uni):
    indeg = Counter()               # 被引用数
    src_of = defaultdict(set)       # 目标编号 -> {来源文件}
    out_edges = defaultdict(set)    # 来源文件 -> {目标编号}
    dangling = Counter()            # 失效目标 -> 次数
    dangling_src = defaultdict(set)
    declared = Counter()            # **已声明的历史引用**（A6 降级留痕合法形态）-> 次数
    declared_src = defaultdict(set)
    refs_total = 0
    # WO-36（2026-10-17）：条目级扩展收集器
    entry_out = defaultdict(set)    # 条目编号 -> {出向目标}（仅同条目块内引用）
    entry_nomutual = set()          # 显式声明「互见：无」的条目编号
    entry_caseann = defaultdict(set)  # 条目编号 -> {案名或 ANxxxx}（块内案证据标签）
    entry_src_codes = defaultdict(set)  # 条目编号 -> {来源简称}（块内来源标注）
    case_ev_hits = 0                # 案证据标签命中总数（观察值）
    unmapped_cases = Counter()      # 无法映射 AN 的案名 -> 次数（显式计数，禁静默）
    case_label_noise = Counter()    # 非案名标签（语法噪声）-> 次数（观察值，不计 unmapped）
    # WO-36 标签正则（与 entry-contract §3/§4 形态对齐；1-8 字案名与回写行契约一致）
    RX_CASE_EV = re.compile(r"\*\*(.{1,8}?)实证\*\*")
    RX_AN_INLINE = re.compile(r"AN(\d{4})")
    RX_SRC_CODE = re.compile(r"（([^（）]{1,20}?) P\d+")
    RX_MUTUAL_NONE = re.compile(r"^-?\s*\*?\*?互见\*?\*?[：:]\s*无\s*$")
    # 扩展回写行「> **适用场景扩展 2026-10-17（<案名>）**：…」的案名（2026-10-18 补）
    RX_EXT_CASE = re.compile(r"适用场景扩展\s*\d{4}-\d{2}-\d{2}\s*（([^）]{1,8})）")
    # 非案名标签噪声（2026-10-18）：`**强化实证**`／`**对照实证**` 等语法标签会被
    # `**<X>实证**` 正则误捕（实测 64 个 unmapped 里绝大多数属此类）⇒ 显式排除，
    # 但**不静默丢弃**：命中噪声词者计入 `case_label_noise` 观察值。
    # 判据分层（2026-10-18 修订）：① 在《单案索引对照表》→ 归 AN；② 形似公司名
    # （常见后缀）但未登记 → `unmapped`（可执行：补登记）；③ 其余 → 语法噪声观察值。
    NOISE_WORDS = ("强化", "扩展", "对照", "反面", "正面", "差异", "修正", "修订", "冲突",
                   "变体", "同型", "同族", "多案", "原文", "语用", "族位", "族序", "共识",
                   "新增", "并入", "独立", "合并", "替换", "复现", "回写", "分组", "合规",
                   "最彻底", "占位", "唯一", "反向", "扩样", "免责", "标签", "本案", "新案",
                   "期后", "段落", "骨架", "边界", "配对", "重排", "浮动", "首案", "同条",
                   "体例", "不重复", "两个方向")
    COMPANY_SUFFIX = re.compile(r"(股份|科技|电子|生物|材料|集团|精密|控股|电气|智能|工业|"
                                r"食品|医药|化学|新材|能源|环保|装备|机械|光电|医疗)$")

    def _classify_label(name):
        """返回 'case'（可映射）／'unmapped'（形似公司名未登记）／'noise'（语法噪声）。"""
        if any(w in name for w in NOISE_WORDS) or len(name) < 2 or len(name) > 6:
            return "noise"
        if COMPANY_SUFFIX.search(name):
            return "unmapped"
        return "noise"

    for rel, path in files:
        cur = None
        for ln in io.open(path, encoding="utf-8", errors="replace"):
            s = ln.strip()
            if not s:
                continue
            m = RX_HEAD.match(s)
            if m:
                cur = m.group(1)        # 本条目自身编号（定义，非引用）
                continue
            # WO-36 修订（2026-10-18）：案证据/案号捕捉改为**块内任意行**——
            # 原实现只在 `#`／`>` 行捕捉，漏掉普通实证行（实测全库 **3,398 行**
            # 含 `ANxxxx` 的列表行未被计入，致案级聚合严重低估：44 条目）。
            # 语义界定：条目块内出现的案号即视为关联（含实证/对比/反例），
            # 因「某案补蒸/订正」时该条目同样受影响。
            if cur:
                for _rx in (RX_CASE_EV, RX_EXT_CASE):
                    for _mt in _rx.finditer(s):
                        _nm = _mt.group(1).strip()
                        _kind = _classify_label(_nm)
                        if _kind == "noise":
                            case_label_noise[_nm] += 1
                            continue
                        # 是否登记由 main() 查表判定（此处不预判，避免双重计数）
                        entry_caseann[cur].add(_nm)
                        case_ev_hits += 1
                for anm in RX_AN_INLINE.finditer(s):
                    entry_caseann[cur].add("AN" + anm.group(1))
            if s.startswith("#") or s.startswith(">"):
                continue
            # WO-36：「互见：无」显式声明（合法孤岛，豁免零出链）
            if RX_MUTUAL_NONE.match(s) and cur:
                entry_nomutual.add(cur)
                continue
            # WO-36：来源简称捕捉（块内任意行，含实证/细项行）
            if cur:
                for sm in RX_SRC_CODE.finditer(s):
                    entry_src_codes[cur].add(sm.group(1).strip())
            for r in RX_REF.findall(s):
                if r.startswith("W-00"):
                    continue            # 旧 W 系列编号＝历史注记/索引保留，跳过
                if r == cur:
                    continue            # 自指不算引用
                refs_total += 1
                if cur:
                    entry_out[cur].add(r)
                if r in uni:
                    indeg[r] += 1
                    src_of[r].add(rel)
                    out_edges[rel].add(r)
                else:
                    # 判据常量收在 `_lib/layout.py`（**单一事实源**）——与体检第 8 项**同判**，
                    # 免重现「体检报 9／图谱报 13」这类同源漂移。
                    if RX_DECLARED.search(s):
                        declared[r] += 1
                        declared_src[r].add(rel)
                    else:
                        dangling[r] += 1
                        dangling_src[r].add(rel)
    return (indeg, src_of, out_edges, dangling, dangling_src, refs_total,
            declared, declared_src,
            entry_out, entry_nomutual, entry_caseann, entry_src_codes,
            case_ev_hits, unmapped_cases, case_label_noise)


def build_inventory(cases_root):
    """材料-产出对账（L3 · 库存对账）：`cases/` 已采集 ↔ `40_单案/` 已蒸馏 ↔ 位置目录登记。

    判据（未被引用的 raw ＝ backlog 提醒）：**缺口是 backlog，不是错误**
        ⇒ 本栏**只提示**，不产生 ERROR，也不回改任何内容。
    目录名归一：`cases/` 下为 `<板块>_<案名>_<日期>` 三段式，取中段为案名；`_` 前缀为非案目录。
    `cases_root` 与 `METHODS` **分离**：重跑校验在临时根重跑时，材料层仍须指向真实库
        （否则对账栏全 0、与现库生成物不一致 ⇒ 误报非幂等）。
    """
    inv = {"cases_dirs": 0, "cases_with_output": 0, "cases_without_output": [],
           "single_files": 0, "cases_only": [], "single_only": []}
    croot = os.path.join(cases_root, "cases")
    cnames = set()
    if os.path.isdir(croot):
        for d in sorted(os.listdir(croot)):
            p = os.path.join(croot, d)
            if not os.path.isdir(p) or d.startswith("_"):
                continue
            parts = d.split("_")
            name = parts[1] if len(parts) >= 3 else d
            cnames.add(name)
            inv["cases_dirs"] += 1
            has = any(f.startswith(("产出_", "共通点映射_")) for f in os.listdir(p))
            if has:
                inv["cases_with_output"] += 1
            else:
                inv["cases_without_output"].append(d)
    sroot = os.path.join(METHODS, SINGLE_NAME)
    snames = set()
    if os.path.isdir(sroot):
        for fn in sorted(os.listdir(sroot)):
            if not fn.endswith(".md"):
                continue
            inv["single_files"] += 1
            snames.add(fn.replace("通用方法论_投行知识与写作范式_", "")
                         .replace("投行语言写作范式_", "").replace(".md", ""))
    inv["cases_only"] = sorted(cnames - snames)
    inv["single_only"] = sorted(snames - cnames)
    return inv


def load_an_map():
    """WO-36：读 `state/单案索引对照表.md`（案名 → AN 号唯一反查表）。

    容错：文件不存在/格式变化 ⇒ 返回空表——案级聚合降级为「仅 AN 直引」，
    纯案名标签全部落 unmapped 计数（显式，不静默）。
    """
    amap = {}
    cand = os.path.join(_ROOT, "state", "单案索引对照表.md")
    if not os.path.exists(cand):
        return amap
    for ln in io.open(cand, encoding="utf-8", errors="replace"):
        m = re.match(r"^\|\s*([^|]{1,30}?)\s*\|\s*(AN\d{4})\s*\|", ln)
        if m:
            amap[m.group(1).strip()] = m.group(2)
    return amap


def main():
    files = scan_files()
    uni = build_universe(files)
    (indeg, src_of, out_edges, dangling, dangling_src, refs_total,
     declared, declared_src,
     entry_out, entry_nomutual, entry_caseann, entry_src_codes,
     case_ev_hits, unmapped_cases, case_label_noise) = build_graph(files, uni)
    inv = build_inventory(_args.cases_root or _ROOT)

    orphans = sorted(i for i in uni if indeg.get(i, 0) == 0)
    # WO-36 零出链：条目无任何出向引用，且未显式声明「互见：无」
    zero_out = sorted(i for i in uni
                      if not entry_out.get(i) and i not in entry_nomutual)
    zero_out_declared = sorted(entry_nomutual)  # 已声明互见无（豁免样本，供观察）

    # WO-36 案级来源聚合：条目 → {AN 号}；案名经单案索引对照表映射，映射失败进 unmapped
    an_map = load_an_map()
    id_to_ans = defaultdict(set)
    for eid, names in entry_caseann.items():
        for nm in names:
            if re.fullmatch(r"AN\d{4}", nm):
                id_to_ans[eid].add(nm)
            else:
                mapped = an_map.get(nm)
                if mapped:
                    id_to_ans[eid].add(mapped)
                else:
                    unmapped_cases[nm] += 1
    ans_unmapped_total = sum(unmapped_cases.values())

    # WO-36 反向索引：AN → 受影响条目（补蒸场景主查询）
    an_to_ids = defaultdict(set)
    for eid, ans in id_to_ans.items():
        for a in ans:
            an_to_ids[a].add(eid)
    # 单向：A 文件 → B 编号，而 B 所在文件未回指 A 文件内任一编号
    id_to_file = {}
    for rel, path in files:
        for ln in io.open(path, encoding="utf-8", errors="replace"):
            m = RX_HEAD.match(ln.strip())
            if m:
                id_to_file.setdefault(m.group(1), rel)
    oneway = []
    for rel in sorted(out_edges):
        for tgt in sorted(out_edges[rel]):
            tf = id_to_file.get(tgt)
            if tf and tf != rel and rel not in out_edges.get(tf, ()):
                oneway.append((rel, tgt, tf))
    top = indeg.most_common(20)
    L = _args.limit

    payload = {
        "tool": "gen_refgraph", "target": METHODS,
        "universe": len(uni), "files_scanned": len(files), "refs_total": refs_total,
        "referenced_ids": len(indeg), "orphans": len(orphans),
        "dangling_ids": len(dangling), "dangling_hits": sum(dangling.values()),
        "declared_ids": len(declared), "declared_hits": sum(declared.values()),
        "oneway_pairs": len(oneway),
        # WO-36 扩展
        "zero_out_ids": len(zero_out), "zero_out_list": zero_out[:L],
        "mutual_none_declared": len(entry_nomutual),
        "case_ev_hits": case_ev_hits,
        "ids_with_case_ann": len(id_to_ans),
        "an_to_ids_sizes": {a: len(v) for a, v in sorted(an_to_ids.items())[:L]},
        "case_label_noise": len(case_label_noise),
        "unmapped_case_names": len(unmapped_cases),
        "unmapped_case_hits": ans_unmapped_total,
        "unmapped_samples": sorted(unmapped_cases)[:10],
        "dangling_list": [{"id": k, "hits": v, "where": sorted(dangling_src[k])[:3]}
                          for k, v in sorted(dangling.items())],
        "declared_list": [{"id": k, "hits": v, "where": sorted(declared_src[k])[:3]}
                          for k, v in sorted(declared.items())],
        "top_inbound": [{"id": k, "indeg": v} for k, v in top],
        "inventory": inv,
    }
    if _args.json:
        print(json.dumps(payload, ensure_ascii=False))
        return 0

    out = []
    out.append("# 方法论库 · 引用图谱（反向视图）\n")
    out.append("> **本文件由 `scripts/gen_refgraph.py` 全库重扫生成，禁手改**。")
    out.append("> 定位：本库**不建反链**——反向信息**读时现算、不落盘为字段**；")
    out.append("> 本视图即那个「反向视图」，**只报不建议、不阻断**，也不回写任何条目。")
    out.append("> 输出**不含时间戳**（保证重跑幂等，可 diff 自证）。\n")
    out.append("## 一、概览\n")
    out.append("| 指标 | 值 |")
    out.append("|---|---|")
    out.append("| 登记面（位置目录编号 ∪ 合并版 I-CL） | %d |" % len(uni))
    out.append("| 扫描文件数 | %d |" % len(files))
    out.append("| 引用总数（去自指、去 W-00 旧号） | %d |" % refs_total)
    out.append("| 被引用过的编号数（入度 > 0） | %d |" % len(indeg))
    out.append("| **无引用条目**（入度 = 0） | **%d** |" % len(orphans))
    out.append("| **失效引用**（目标不在登记面） | **%d 个编号 / %d 处** |" % (len(dangling), sum(dangling.values())))
    out.append("| 已声明的历史引用（**不计欠账** · A6 降级留痕合法形态） | %d 个编号 / %d 处 |"
               % (len(declared), sum(declared.values())))
    out.append("| 单向引用（A→B 而 B 未回指） | %d 对 |" % len(oneway))
    out.append("| **零出链条目**（无出向引用且未声明互见无 · WO-36 · 仅报告） | **%d** |" % len(zero_out))
    out.append("| 已声明「互见：无」（合法孤岛 · 豁免零出链） | %d |" % len(entry_nomutual))
    out.append("| 案证据标签命中（<案名>实证 ＋ AN 直引） | %d |" % case_ev_hits)
    out.append("| 有关联案号的条目数 | %d |" % len(id_to_ans))
    out.append("| 案名无法映射 AN（unmapped · **显式计数，禁静默**） | %d 个案名 / %d 处 |"
               % (len(unmapped_cases), ans_unmapped_total))
    out.append("")
    out.append("## 二、失效引用（需核）\n")
    if dangling:
        out.append("| 目标编号 | 出现次数 | 出现位置（前 3） |")
        out.append("|---|---|---|")
        for k, v in sorted(dangling.items(), key=lambda x: (-x[1], x[0]))[:L]:
            out.append("| `%s` | %d | %s |" % (k, v, "；".join(sorted(dangling_src[k])[:3])))
        if len(dangling) > L:
            out.append("| … | | 另有 %d 个未列 |" % (len(dangling) - L))
    else:
        out.append("（无）")
    out.append("")
    out.append("## 二·附、已声明的历史引用（**不计欠账**）\n")
    out.append("> 这些引用处**自带注记**「历史编号·主库无对应·待核」——属 **A6 降级留痕的合法形态**：")
    out.append("> 不是漏改的引用，而是「确实引用了不在库内的历史编号，且已告知读者」⇒ **单列可见、不入欠账**。")
    out.append("> 判据常量 ＝ `_lib/layout.py` 的 `RX_DECLARED_HIST`（与体检第 8 项**同源同判**）。\n")
    if declared:
        out.append("| 目标编号 | 出现次数 | 出现位置 |")
        out.append("|---|---|---|")
        for k, v in sorted(declared.items(), key=lambda x: (-x[1], x[0]))[:L]:
            out.append("| `%s` | %d | %s |" % (k, v, "；".join(sorted(declared_src[k])[:3])))
    else:
        out.append("（无）")
    out.append("")
    out.append("## 三、无引用条目（入度 = 0 · 仅提示，不强制补链）\n")
    if orphans:
        out.append("共 **%d** 个，前 %d 个：" % (len(orphans), min(L, len(orphans))))
        out.append("")
        out.append("`" + "`　`".join(orphans[:L]) + "`")
        if len(orphans) > L:
            out.append("\n…另有 %d 个未列。" % (len(orphans) - L))
    else:
        out.append("（无）")
    out.append("")
    out.append("## 四、单向引用（A→B 而 B 未回指 · 仅提示）\n")
    if oneway:
        out.append("| 来源文件 | 指向编号 | 目标文件 |")
        out.append("|---|---|---|")
        for a, b, c in oneway[:L]:
            out.append("| %s | `%s` | %s |" % (a, b, c))
        if len(oneway) > L:
            out.append("| … | | 另有 %d 对未列 |" % (len(oneway) - L))
    else:
        out.append("（无）")
    out.append("")
    out.append("## 五、高入度条目 TOP（枢纽观察）\n")
    out.append("| 编号 | 被引用次数 |")
    out.append("|---|---|")
    for k, v in top:
        out.append("| `%s` | %d |" % (k, v))
    out.append("")
    out.append("## 五·附一、零出链条目（WO-36 · **仅报告，不强制补链**）\n")
    out.append("> 判据：条目无任何出向引用（互见/引用均无）且未显式声明「互见：无」。")
    out.append("> 与「无引用条目」（入度=0，没人指向它）互补——本栏是「它不指向别人」。")
    out.append("> 豁免：`- **互见**：无` 显式声明者不计（声明即合法孤岛，共 %d 条）。\n" % len(entry_nomutual))
    if zero_out:
        out.append("共 **%d** 个，前 %d 个：" % (len(zero_out), min(L, len(zero_out))))
        out.append("")
        out.append("`" + "`　`".join(zero_out[:L]) + "`")
        if len(zero_out) > L:
            out.append("\n…另有 %d 个未列。" % (len(zero_out) - L))
    else:
        out.append("（无）")
    out.append("")
    out.append("## 五·附二、案级来源聚合（WO-36 · 补蒸/订正场景主查询）\n")
    out.append("> 解析条目块内 `<案名>实证`／`ANxxxx` 标签（含表格与回写行），案名经")
    out.append("> `state/单案索引对照表.md` 映射为 AN 号。**用途**：某案补蒸/订正时，")
    out.append("> 一查即得全部受影响条目。解析失败者进 unmapped 计数，**禁猜禁静默**。\n")
    if an_to_ids:
        out.append("| 案号 | 关联条目数 | 受影响条目（前 %d） |" % min(L, 8))
        out.append("|---|---|---|")
        for a in sorted(an_to_ids)[:L]:
            ids_sorted = sorted(an_to_ids[a])
            out.append("| %s | %d | %s |" % (a, len(ids_sorted),
                                             "、".join("`%s`" % x for x in ids_sorted[:8])
                                             + ("…" if len(ids_sorted) > 8 else "")))
        if len(an_to_ids) > L:
            out.append("| … | | 另有 %d 案未列 |" % (len(an_to_ids) - L))
    else:
        out.append("（无——未检出任何条目-案号关联）")
    out.append("")
    if unmapped_cases:
        out.append("**unmapped 案名**（共 %d 个案名 / %d 处，前 %d 个）：" %
                   (len(unmapped_cases), ans_unmapped_total, min(L, len(unmapped_cases))))
        out.append("")
        out.append("`" + "`　`".join(sorted(unmapped_cases)[:L]) + "`")
        out.append("\n> 处置：核对标签写法与《单案索引对照表》登记名；确为新案先补登记再重跑本脚本。\n")
    out.append("")
    out.append("## 六、材料-产出对账（库存对账 · **缺口＝backlog，非错误**）\n")
    out.append("> 判据：未被加工的材料是 **backlog 提醒**，不是违规；本栏**只提示、不阻断**。")
    out.append("> 目录名归一：`cases/<板块>_<案名>_<日期>` 取中段；`_` 前缀为非案目录。\n")
    out.append("| 项 | 值 |")
    out.append("|---|---|")
    out.append("| `cases/` 已采集案目录 | %d |" % inv["cases_dirs"])
    out.append("| 其中**已有**蒸馏产出件 | %d |" % inv["cases_with_output"])
    out.append("| 其中**尚未**蒸馏（backlog） | **%d** |" % len(inv["cases_without_output"]))
    out.append("| `40_单案/` 单案文件 | %d |" % inv["single_files"])
    out.append("| **有材料、无单案文件** | %d |" % len(inv["cases_only"]))
    out.append("| **有单案文件、无材料目录**（无引用条目产出，须核） | %d |" % len(inv["single_only"]))
    out.append("")
    for _title, _items, _note in (
            ("未蒸馏材料（backlog · 可择期蒸馏）", inv["cases_without_output"], ""),
            ("有材料无单案文件", inv["cases_only"], ""),
            ("有单案文件无材料目录（**须人工核实**）", inv["single_only"], "⚠️ ")):
        out.append("**%s**：%s\n" % (_title, (_note + "共 **%d** 个，前 %d 个：" % (len(_items), min(L, len(_items))))
                                    if _items else "（无）"))
        if _items:
            out.append("`" + "`　`".join(_items[:L]) + "`\n")
            if len(_items) > L:
                out.append("…另有 %d 个未列。\n" % (len(_items) - L))
    out.append("")

    dst = os.path.join(METHODS, REFGRAPH_FILE)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with io.open(dst, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    print("✓ 引用图谱已生成: %s（登记面 %d ｜ 引用 %d ｜ 无引用条目 %d ｜ 失效 %d ｜ 已声明 %d ｜ 单向 %d 对 ｜ "
          "零出链 %d ｜ 案关联条目 %d ｜ unmapped 案名 %d ｜ "
          "材料 %d/未蒸馏 %d）"
          % (os.path.relpath(dst, METHODS), len(uni), refs_total, len(orphans), len(dangling),
             len(declared), len(oneway), len(zero_out), len(id_to_ans), len(unmapped_cases),
             inv["cases_dirs"], len(inv["cases_without_output"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())

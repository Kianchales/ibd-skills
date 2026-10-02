#!/usr/bin/env python3
"""溯源校验器：把「来源标注」从**人可读指针**升级为**机械可验的证据链**（报告级 · 只报不改 · 不阻断）

## 为什么有本脚本

本库的来源标注形态是 `（来源简称 P页码）`——**人读得懂，机器判不了**：「P152 那个数真的是第 152 页那个数吗」，
此前只能靠人工抽验。已发生的事故证明这个洞是真的：某条把问询回复的「2022–2024」口径与招股书的
「2023–2025」口径并列，**两口径各自自洽但期间不同**，混列即误导。本脚本把那类错误从「事后被人撞见」
变成「每次可机械复验」。

**核心不变量（Grounding）**：每条条目里**承重字面量**（数字／百分比／金额）必须能在**其来源标注所指的页码段内**逐字命中。

## 三条铁律（照搬，不得违）

1. **只报不改** —— 本脚本**永不**修改任何文件，只输出报告。
2. **候选集闭集冻结** —— 以下形态表即候选集；**改变检出的形态改的是本 docstring，不是散落各处的正则**。
   承重字面量候选集（5 类）：
     L1 千分位数字      `\\d{1,3}(?:,\\d{3})+(?:\\.\\d+)?`
     L2 百分比          `\\d+(?:\\.\\d+)?%`
     L3 小数            `\\d+\\.\\d+`
     L4 日期／期间       `\\d{4}[-/年]\\d{1,2}(?:[-/月]\\d{1,2})?`
     L5 四位以上整数     `(?<![\\d.,])\\d{4,}(?![\\d.,])`
   来源标注候选形态（1 类，须含页码记号）：`（… P<数字> …）` / `（… PAGE <数字> …）`
3. **退出码不承载语义，报告即接口** —— 恒退出 `0`（除非前置失败）；**报告文本／`--json` 才是判定接口**。

## 报告为什么不叫「错误」而叫「嫌疑」

命中失败**不等于**写错：派生值（两数相减）、口径换算（万元↔元）、单位改写都会正常出现「原文里搜不到该字面量」。
故此类一律报 **嫌疑（fidelity suspects）**，交人裁定；本脚本**不作判决**。
而「**根本验不了**」（缺标注／案名不在册／映射表无该案／页码段缺失／判不出案）**单列一栏**，
因为「验了疑似不符」与「压根没验」是两回事——**后者更需要人来定**。

## 三趟扫描

- **趟 1 Fidelity 嫌疑**：可判案的标注 ⇒ 抽前文承重字面量 ⇒ 在所指页码段内逐字命中判定。
- **趟 2 Evidence error（验不了）**：缺来源标注／案名不在册／映射表无该案或该来源／页码段不存在／判不出案。
- **趟 3 Inventory 对账**：`cases/` 下有材料、但既无单案产出、又未登记 `state/待补学清单.md` 的**悬空案**。

## 不判什么（**覆盖边界 · 必读**）

- **不判「命中失败」的对错** —— 派生值／口径换算／单位改写都会**正常**命中失败，故一律报**嫌疑**，**不作判决**。
- **不替作者推断来源** —— 裸页码（省略来源代号）**概不推断**。`--propose` 给的也只是「**提案 ＋ 机械复验**」，
  且必须过**三道门**（前文字面量**全中**该来源**该页** ／ 字面量 **≥ `MIN_LIT`＝3** ／ **候选唯一**）；
  上述之外一律留白，不给补注建议。（「多候选命中」实测占比高 ⇒ **同值重现是常态**，
  故连「唯一命中」也**不等于**作者原意——落盘前须人点头。）
  另有**判据 E（子句级取案）回退**（2026-09-28 吸收）：主判定落「多候选命中／该件无此内容／
  无可用材料／非原件轴」时，若**子句内写明案名**（多案条目实测 94.8%）则以该案枚举全来源件重试。
  子句案名是**文本写明的归属线索、非推断**；重试命中时结果以 `note` 标注「子句级取案」，可与主判定对照。
  另有**判据 D（抽取收窄）**（2026-09-28 吸收）：编号残片／长数字串／编辑器行号连写**不作承重字面量**
  （剔除类详见 `d_classify` 规则面注释）；其余 5-9 位裸整数**保留判定但 `note` 打标**（可能是真金额）。
  **被剔除的残片永不据此报「内容写错」**；打标类仅提示、交人裁。
- **⚠️ 不判「查不到」＝「写错」（重要覆盖边界）** —— `--propose` 的结果分**四级**：
  `验过`（精确命中标注页）／`邻近命中`（件对、页码偏 ≤ `PAGE_TOL`）／`文档内存在`（件对、页码需重定位）／
  `该件无此内容`。**实测**：旧版一概报「未命中」的那一批里，**四成（下界）其实「件是对的」**——
  标注写的是「大意在这几页」，旧判据要求「标注那一页逐字对上」，**两者精度不同**。
  **判据**：**只有 `该件无此内容` 一档才有资格谈「内容可能写错」**；前三级**不得**当疑似错误上报。
- **不据版本推断改写条目** —— 同案多版本（`招·注册稿`／`招·上会稿`／`招·申报稿`）**互不替代**：
  原文所写版本里没有、而另一版本全中时，只报 `版本疑不符` **供人裁**，**不代改**。
- **不以「派生件」作来源件核页码** —— `阅读包` 系（法律／财务／行业包）是 S3 的**派生件**，
  页码与原件**不同轴**、且随材料重生成而变 ⇒ 该轴上的标注报 `非原件轴`，**不判定**。
- **⚠️ 口径位移（与旧读数比较时必读）** —— 本脚本的**前置判定顺序**改为「**先查字面量、再查候选**」：
  旧序下「既无字面量、又无候选」者报 `无候选来源`（**134 处**）；新序下改报 `无字面量可验`
  ——因为「**没有可验之物**」比「没有候选」更根本（有候选也一样验不了）。
  故与旧版 `--propose` 读数比较时，**`无候选来源` 与 `无字面量可验` 两栏不可直接相减**。
- **版本轴的作用面是「护栏」不是「修正」** —— `版本疑不符` **只在同案持有 ≥2 个版本代号时**才可能触发；
  实测本库 **95 案中 0 案**持有两个版本（94 案各 1 个、1 案 0 个）⇒ 该档**当前恒为 0**。
  它堵的是**潜在路径**（多版本案上静默取最新版、再把失败记在数据头上），**不是当下的缺陷出口**。
- **不判「页码段缺失」是否属材料缺口** —— 只说明「该件里找不到这个页码段」，是否属采集遗漏交**采集域**。
- **不判标注的规范性**（如 `（阅读包 P33）` 这类**非来源件轴**写法）——它含别名故不计入裸页码；
  其是否合规属 `entry-contract.md` 面（该文只约束**来源件轴**）。
- **⚠️ 不判「多案共通条目」上裸页码的候选来源（重要覆盖边界 · 2026-09-28 实测补）** ——
  标题含「**共通／通用／多案**」的条目是**跨案合成**的：**一条横跨多案，其中每处页码属于不同的案**。
  本脚本按「该 `###` 块属于哪个案」取候选 ⇒ **在这类条目上必然取错案**，其报出的「查不到」
  **多为「工具不适用」，不等于内容有误**。实测（**四级判定之前的口径**）：法律／行业／财务三域
  报「未命中」者 **389 处，100% 落在**该类条目上（其中 61.2% 的同一条目内被指派了 ≥2 个不同的案）。
  **判据**：凡所属条目名含「共通／通用／多案」，**一律先按工具不适用看待**，不得直接当作内容嫌疑。
- **不作为门禁** —— 本脚本**不入** `check_methods_health.py` 的全库门禁：它的「验不了」占比很高
  （标注省略代号／判不出案／映射表无该来源），入禁会把这一大团噪声压进 0-ERROR 基线、**基线即废**。
  守**增量**由**体检第 24 项**承担（裸页码计数 ⟷ 基线）；本脚本的角色是**逐处复验工具**——
  **S7 复盘／专项核查／存量盘点**时**单跑**。

## 前置

`{METHODS_ROOT}/_generated/来源代号映射.json`（由 `gen_source_map.py` 生成）——它把「来源简称」解析到**物理文件**。
**没有它本脚本无意义**（只能判「有没有标注」，判不了「标注对不对」）。

## 用法

    python check_evidence.py [--methods-root <工作区根>] [--cases-root <材料根>] [--json] [--limit N] [--propose]

参数：
  --methods-root  工作区根（其下含 methods/；默认 $METHODS_ROOT）
  --cases-root    材料根（其下含各案目录；**默认 ＝ 工作区根**，即 `<工作区根>/cases`）
  --json          输出结构化结果（供上层消费）
  --limit         每类明细最多打印条数（默认 20）
  --propose       对**裸页码**（省略来源代号者）出「**提案 ＋ 机械复验**」：
                  先按「同块内带代号来源（就近优先）」给候选，再用**原文复验**并**分四级**定档——
                  `验过`（字面量全中标注页）／`邻近命中`（全中标注页 ± `PAGE_TOL`，件对页小偏）／
                  `文档内存在`（全中本件任一处）／`该件无此内容`。**只有 `验过` 列为可补**，
                  其余一律留白；`版本疑不符`／`非原件轴` 仅作提示。
                  ⚠️ 仍是**提案**：字面量在该件出现 ≠ 作者原意必为此来源 ⇒
                  落盘前须人点头；本脚本**始终不修改任何文件**。
"""
import argparse, io, json, os, re, sys
from collections import defaultdict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_ap = argparse.ArgumentParser(description="溯源校验（只报不改 · 报告级）")
_ap.add_argument("--methods-root", default=os.environ.get("METHODS_ROOT", ""),
                 help="工作区根（其下含 methods/；默认 $METHODS_ROOT）")
_ap.add_argument("--cases-root", default="", help="材料根（含各案目录；默认 ＝ 工作区根）")
_ap.add_argument("--json", action="store_true", help="输出结构化 JSON")
_ap.add_argument("--limit", type=int, default=20, help="每类明细最多打印条数")
_ap.add_argument("--propose", action="store_true",
                 help="对裸页码出「提案＋机械复验」清单（验过才列可补；仍只报不改）")
_args = _ap.parse_args()

import os as _lo, sys as _ls
_ls.path.insert(0, _lo.path.dirname(_lo.path.abspath(__file__)))
from _lib.layout import resolve as _layout_resolve, domain_files as _layout_domain_files, \
    DIR_DOMAIN, DIR_LANG, DIR_VOLUME, GENERATED_NAME, SKIP_DIRS_BASE, NOTES_NAME
_ROOT, METHODS, SCRIPTS = _layout_resolve(_args.methods_root)
CASES_ROOT = _args.cases_root or str(_ROOT)

if not os.path.isdir(METHODS):
    sys.stderr.write("✗ 未找到方法论库：%s\n" % METHODS)
    sys.exit(2)

# ── 闭集：承重字面量候选集（改形态改这里，不散落） ──────────────────────────
LITERAL_RX = [
    ("L1 千分位", re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?")),
    ("L2 百分比", re.compile(r"\d+(?:\.\d+)?%")),
    ("L3 小数", re.compile(r"\d+\.\d+")),
    ("L4 日期期间", re.compile(r"\d{4}[-/年]\d{1,2}(?:[-/月]\d{1,2})?")),
    ("L5 四位整数", re.compile(r"(?<![\d.,])\d{4,}(?![\d.,])")),
]
CIT_RX = re.compile(r"（([^（）]*?(?:PAGE|P)\s*\d+[^（）]*)）")
PAGE_TOK_RX = re.compile(r"(?:PAGE|P)\s*(\d+)(?:\s*[-–—~至]\s*(\d+))?")
BLOCK_RX = re.compile(r"^### ", re.M)
MIN_LIT = 3      # 「提案复验」的证据强度下限：命中字面量少于此数只算「弱证据」，不得判「验过」
PAGE_TOL = 5     # 「邻近命中」容差（页）：标注页 ± 该页数内字面量**全部**命中 ⇒ 判「**件对、页码小偏**」。
                 #   立项理由：标注写的是「大意在这几页」，而旧判据要求「**标注那一页逐字对上**」——
                 #   两者精度不同，判据更严的一方会把**正确标注**判成失败（实测：标注 `P184-185`
                 #   而数字实在 172~186 页者成批出现）。**是判据过严，不是数据无效。**
NON_SOURCE_CODES = {"法律包", "财务包", "行业包"}
                 #   ↑ **轴分离（阅读包系）**：这三者是 S3 材料准备产出的**派生件**（非原件），
                 #     其页码随材料重生成而变、且与原件页码不同轴 ⇒ **不得拿它当来源件去核页码**。
                 #     它们仍是**合法代号**（codebook 有载），只是**不承担「来源件」的核验职责**。
# **先屏蔽再取证**：编号与目录日期戳本身由数字构成，若不屏蔽就会把「条目编号」当成承重数字报出来
# （首跑实测：`000325`／`090016`／`160006` 全是编号片段，属纯噪声）。
MASK_RX = re.compile(
    r"(?<![A-Za-z0-9])"                                          # 编号：W-000273 / F-010001 / WL-AN0083-01
    r"(?:WL|PL|AN|I-CL|CL|[FLIS])[-\s]?\d{3,6}(?:[-–—]\d{1,3})?"
    r"(?![A-Za-z0-9])"
    r"|(?<![A-Za-z0-9])\d{4}-\d{2}-\d{2}(?![A-Za-z0-9])"
    r"|(?<=_)\d{8}(?![0-9])"                                     # 案目录名日期戳：…_20260823
    r"|(?<![A-Za-z0-9])第\s*[0-9一二三四五六七八九十]+\s*轮(?![A-Za-z0-9])"
)


def mask(text):
    return MASK_RX.sub(lambda m: " " * len(m.group(0)), text)


def load_map():
    p = os.path.join(METHODS, GENERATED_NAME, "来源代号映射.json")
    if not os.path.isfile(p):
        return None
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


M = load_map()
if not M:
    sys.stderr.write("✗ 缺 %s/_generated/来源代号映射.json —— 先跑 gen_source_map.py\n" % METHODS)
    sys.exit(2)

CASES = M.get("cases", {})
ALIASES = M.get("aliases", {})
PAGE_RX = re.compile(M.get("page_marker") or r"^=+\s*PAGE\s+(\d+)\s*=+\s*$")
CASE_NAMES = sorted(CASES.keys(), key=len, reverse=True)          # 长名优先，防子串误配
ALIAS2CODE = {}
for code, alist in ALIASES.items():
    for a in alist:
        ALIAS2CODE.setdefault(a, code)
    ALIAS2CODE.setdefault(code, code)

# ── 材料页索引（懒加载 ＋ 按文件缓存；只读被引到的件） ──────────────────────
_page_cache = {}
_pm_cache = {}


def resolve_source(case, code):
    """**代号解析（含裸代号回退）**——本脚本此前只做精确匹配，实测因此产生大批**假缺口**：
    全库 95 案中裸代号 `招` 仅 **1** 例，其余 **94** 例都是**版本化代号**
    （`招·注册稿` 60／`招·申报稿` 21／`招·上会稿` 13）；而条目里写的是**裸 `招`**
    ⇒ 精确匹配必失败，688 处被判「映射表无此来源」，**实为解析器缺回退**。

    回退规则（**照 codebook 语义**，非自创）：
      · `招` ＝ 契约里的「招股说明书（**默认最新版**）」⇒ 无精确匹配时按**披露进度取最新**：
        注册稿 ＞ 上会稿 ＞ 申报稿；
      · `回复` ＝ 契约里的「轮次无法判定时的**兜底**」⇒ 无精确匹配时退到 `问1`。
    返回 `(源条目, 实际命中代号)`；真的没有则 `(None, None)`——**那才是真缺口**。
    """
    srcs = CASES.get(case, {}).get("sources", [])
    for s in srcs:
        if s["code"] == code:
            return s, code
    if code == "招":
        for pref in ("招·注册稿", "招·上会稿", "招·申报稿"):
            for s in srcs:
                if s["code"] == pref:
                    return s, pref
    if code == "回复":
        for s in srcs:
            if s["code"] == "问1":
                return s, "问1"
    return None, None


def page_index(case, code):
    key = (case, code)
    if key in _page_cache:
        return _page_cache[key]
    ent = None
    for s in CASES.get(case, {}).get("sources", []):
        if s.get("code") == code:
            ent = s
            break
    if ent is None:
        _page_cache[key] = None
        return None
    fp = os.path.join(CASES_ROOT, CASES[case]["dir"], ent["file"])
    if not ent.get("text_available") or not os.path.isfile(fp):
        _page_cache[key] = None
        return None
    lines = io.open(fp, encoding="utf-8", errors="replace").read().splitlines()
    # 页码 → 行区间
    marks = [(i, int(m.group(1))) for i, ln in enumerate(lines) if (m := PAGE_RX.match(ln))]
    idx = {}
    for j, (li, no) in enumerate(marks):
        end = marks[j + 1][0] if j + 1 < len(marks) else len(lines)
        idx[no] = (li, end)
    _page_cache[key] = (lines, idx)
    return _page_cache[key]


def page_text(case, code, pages):
    got = page_index(case, code)
    if not got:
        return None
    lines, idx = got
    out = []
    for pno in pages:
        if pno not in idx:
            return None                                  # 页码段缺失 ⇒ 验不了
        a, b = idx[pno]
        out.extend(lines[a:b])
    return "\n".join(out)


def norm(s):
    """轻量归一：全角→半角、去空白与千分位——只用于「命中」判定，不改变原值展示"""
    s = s.replace("，", ",").replace("．", ".").replace("％", "%").replace("　", " ")
    return re.sub(r"[\s,]", "", s)


def page_map(case, code):
    """页图 `行号 → 页码`（供**逐字面量定位**）。

    与 `page_text` 的分工：后者只拼「标注所指的页」；本函数给出**全件**的页归属，
    才能在「该页没找到」之后回答**下一个问题**——「**那它到底落在哪一页／在不在本件**」。
    """
    key = (case, code)
    if key in _pm_cache:
        return _pm_cache[key]
    got = page_index(case, code)
    if not got:
        _pm_cache[key] = None
        return None
    lines, idx = got
    page_of = [None] * len(lines)
    for pno, (a, b) in idx.items():
        for i in range(a, b):
            page_of[i] = pno
    _pm_cache[key] = (lines, page_of, set(idx))
    return _pm_cache[key]


def locate_literals(case, code, lits):
    """一次遍历给出**每个字面量在本件各页的出现集合**（未出现＝空集）；材料不可读返回 `None`。"""
    pm = page_map(case, code)
    if pm is None:
        return None
    lines, page_of, _pages = pm
    want = [(l, norm(l)) for l in lits]
    res = {l: set() for l in lits}
    for i, ln in enumerate(lines):
        p = page_of[i]
        if p is None:
            continue
        n = norm(ln)
        for l, nl in want:
            if nl and nl in n:
                res[l].add(p)
    return res


def level_of(found, picked, cited):
    """**四级判定**（取代原来的「命中／未命中」二分）：

    · **3 精确**   —— 字面量**全部**落在**标注所指的页**上；
    · **2 邻近**   —— 全部落在标注页 **± `PAGE_TOL`** 内（件对、页码小偏）；
    · **1 文档内** —— 全部落在**本件任一处**（件对，页码需重定位）；
    · **0 无**     —— 有字面量**在本件内根本不出现**（**只有这一档**才有资格谈「可能写错」）。

    返回 `(级, 缺失字面量列表)`。
    """
    lo, hi = min(cited), max(cited)
    lv, miss = 3, []
    for _k, lit in picked:
        pgs = found.get(lit) or set()
        if not pgs:
            miss.append(lit)
            continue
        if any(p in cited for p in pgs):
            continue
        if any(lo - PAGE_TOL <= p <= hi + PAGE_TOL for p in pgs):
            lv = min(lv, 2)
            continue
        lv = min(lv, 1)
    return (0 if miss else lv), miss


def version_variants(case, code):
    """**版本轴：只提示、不替代** —— 返回该代号的核验序列 `[(试判代号, 是否原文所写)]`。

    · 裸 `招`（codebook 语义＝「**默认最新版**」）⇒ 逐个试**全部在案版本**；
    · `招·<版本>` ⇒ **先试自身**，再试其余版本——**仅供提示「数字其实在哪一版」**，
      **不得据此改写条目**（版本改判属内容面，须人裁）；
    · 其余代号 ⇒ 只试自身（`回复` 的轮次兜底由 `resolve_source` 负责，不在此重复）。
    """
    srcs = [s["code"] for s in CASES.get(case, {}).get("sources", [])]
    vers = [c for c in ("招·注册稿", "招·上会稿", "招·申报稿") if c in srcs]
    if code == "招":
        return [(c, True) for c in (vers or ["招"])]
    if code.startswith("招·"):
        if code not in srcs:
            return [(code, True)]      # 该案**没有**此版本 ⇒ 不试兄弟版本（否则会把「无此版本」误报成「版本疑不符」）
        return [(code, True)] + [(c, False) for c in vers if c != code]
    return [(code, True)]


def _ver_note(r):
    """非原文所写代号命中时的**提示语**（只提示、不替代）。"""
    return "" if r["is_written"] else "命中见同案 `%s`" % r["rcode"]


def resolve_case(preceding, block_head, codes):
    """判案：以「**代号必须在该案的来源表里**」为**硬约束**消歧。

    为什么需要消歧：跨案条目里一个 `###` 组会**顺带提及别的案**（同族互证），此前取「最近的案名」
    会把相邻案名误当所属案 ⇒ 拿该案的来源表去查、自然查不到该代号（实测这类造成 698 处
    「映射表无此来源」的**假缺口**）。

    **代号是强证据**：只有真被采集过的案才持有该代号。故改为给候选打分——
      ① 候选＝条目标题案名（最可靠）＋ 标注前文出现的全部已登记案名（按距标注由近到远）；
      ② 分数＝该案来源表**命中该标注代号**的个数；
      ③ 取「命中多者 → 标题案名 → 更近者」；命中 0 者仍保留为兜底（**不因无命中就判不出**）。
    """
    h = mask(block_head)
    txt = mask(preceding)
    cands, seen = [], set()
    for name in CASE_NAMES:                       # 先标题案名（tier 0）
        if name in h and name not in seen:
            seen.add(name)
            cands.append((0, -10 ** 9, name))
    occ = sorted(((txt.rfind(n), n) for n in CASE_NAMES if txt.rfind(n) >= 0), reverse=True)
    for pos, name in occ[:8]:                     # 再前文案名（tier 1，按位置由近到远）
        if name not in seen:
            seen.add(name)
            cands.append((1, -pos, name))
    if not cands:
        for an in re.findall(r"AN\d{4}", h + " " + txt):
            if an in AN2CASE:
                return AN2CASE[an], 0
        return None, 0
    best = None
    for tier, negpos, name in cands:
        src = {s["code"] for s in CASES.get(name, {}).get("sources", [])}
        hit = sum(1 for c in codes if c in src)
        key = (-hit, tier, negpos)
        if best is None or key < best[0]:
            best = (key, name, hit)
    return best[1], best[2]


def suggest_source(preceding):
    """同段前文**最近的带代号标注** ⇒ 作为裸页码的**建议来源**。

    ⚠️ **只作裁定参考，不计入判定**——本脚本**不替作者推断**（推错等于造假证据）；
    给出建议是为了让「存量裸页码裁定」这份人工活**少做无用功**，不是替人做决定。
    """
    seen = []
    for m in CIT_RX.finditer(preceding):
        for c, _p in parse_citation(m.group(1)):
            if c not in seen:
                seen.append(c)
    return "／".join(seen[-2:]) if seen else "无（同段前文无带代号标注）"


def pick_literals(seg):
    """取一段文本里的**承重字面量**（数字／百分比／日期）：早者优先、同起点长者优先、抑制重叠。

    重叠抑制的用处：`91.52%` 已取则 `91.52` 不再重复取；日期里的 `2026` 不再单独取。
    """
    spans = []
    for kind, rx in LITERAL_RX:
        for lm in rx.finditer(seg):
            spans.append((lm.start(), lm.end(), kind, lm.group(0)))
    spans.sort(key=lambda t: (t[0], -(t[1] - t[0])))
    picked, last_end = [], -1
    for s, e, kind, lit in spans:
        if s < last_end:
            continue
        picked.append((kind, lit))
        last_end = e
    return picked


# ── 判据 E（子句级取案）：主判定「判不动」时的**回退重试**（2026-09-28 吸收） ──
# 动因：标题含「共通／通用／多案」的条目一条横跨多案，按块取案必错；而实测这类条目里
# **标注所在子句内写明案名**（94.8%）。判据 E＝取「子句内离标注最近的已登记案名」重试——
# 它是**文本里写明的归属线索、非推断**。回退触发＝主判定落以下四档（判不动或取错案风险高）。
CLAUSE_SEP_RX = re.compile(r"[。；;！!？?\n]")
E_RETRY_VERDICTS = {"多候选命中", "该件无此内容", "无可用材料", "非原件轴"}
E_LEVEL_TO_VERDICT = {3: "验过", 2: "邻近命中", 1: "文档内存在"}

# ── 判据 D（抽取收窄）：编号残片／长数字串不作承重字面量；可疑型打标不静默剔除（2026-09-28） ──
# 动因：字面量抽取会把「无字母前缀的编号残片」（`050091` 来自 `PL-050091`、`1700005` 来自
# 文号 `[2026] 1700005 号`、`41944` 来自标准号 `GB/T41944-2022`）与「长数字串／编辑器行号」
# 当成承重数字 ⇒ 造出假的「该件无此内容」（实测 17 处误捕）。
# 规则面（判定顺序即优先级）：
#   剔除类（**绝无金额形态**，不作承重字面量）——
#     D1 长数字串：≥10 位纯数字（统一社会信用代码／流水号）；
#     D2 前导 0 残片：`0` 开头 ≥5 位（条目编号右段天然带前导 0；真实金额/页码不前导 0）；
#     D3 编号锚残片：5-9 位裸整数且**左邻**∈ `：:T]E（(`（报告号「编号：」／标准号 GB/T／
#        文号「]」／专利号「E」）；
#     D4 行号残片：5-9 位裸整数且右邻（忽略空白）为「段」（「14396 段」＝编辑器行号连写，
#        实测原件行 14396 恰为目标注释前 11 行的引导句）。
#   打标类（**保留判定**，note 标注可疑，交人裁）——
#     D5 其余 5-9 位裸整数（**可能是真金额**，静默剔除会造新盲区 ⇒ 只打标）。
# 真金额防线（已核）：含千分位逗号/小数点的数字由 L1/L3 规则先行捕获，形态不落入 D1-D5。
D_RX_LONG = re.compile(r"\d{10,}")
D_RX_LEAD0 = re.compile(r"^0\d{4,}$")
D_RX_BARE5 = re.compile(r"^\d{5,9}$")
D_ANCHOR_CHARS = set("：:T]E（(")


def d_classify(lit, left="", right=""):
    """判据 D 单字面量归类：返回 `(动作, 理由)`；动作 ∈ `drop`（剔除类）／`flag`（打标类）／`None`（正常）。"""
    if D_RX_LONG.search(lit):
        return ("drop", "长数字串")
    if D_RX_LEAD0.match(lit):
        return ("drop", "前导0残片")
    if D_RX_BARE5.match(lit):
        if left and left[-1] in D_ANCHOR_CHARS:
            return ("drop", "编号残片(左邻锚)")
        if right.lstrip().startswith("段"):
            return ("drop", "行号残片(数字+段)")
        return ("flag", "5-9位裸整数")
    return (None, None)


def d_filter(picked, window_text=""):
    """判据 D 批量过滤：返回 `(可用 picked, 被剔除清单, 打标清单)`。

    `window_text` 为取证窗口原文（未 mask），供左邻/右邻锚判定。
    """
    usable, dropped, flagged = [], [], []
    for kind, lit in picked:
        i = window_text.find(lit)
        left = window_text[max(0, i - 2):i].rstrip() if i >= 0 else ""   # rstrip：锚符与数字间的空格不碍判定
        right = window_text[i + len(lit):i + len(lit) + 4] if i >= 0 else ""
        act, why = d_classify(lit, left, right)
        if act == "drop":
            dropped.append((lit, why))
        elif act == "flag":
            flagged.append((lit, why))
            usable.append((kind, lit))
        else:
            usable.append((kind, lit))
    return usable, dropped, flagged


def clause_case(block, pos):
    """判据 E：**子句级取案** —— 子句（以 `。；;！!？?` 与换行切分）内离标注最近的已登记案名。

    优先**标注之前最近**者（更可能是被说明对象的主体）；其前无则取**其后最近**者。
    返回 `(案名, "pre"|"post")` 或 `(None, None)`。
    """
    s = 0
    for _m in CLAUSE_SEP_RX.finditer(block[:pos]):
        s = _m.end()
    _m2 = CLAUSE_SEP_RX.search(block, pos)
    e = _m2.start() if _m2 else len(block)
    seg = mask(block[s:e])
    rel = pos - s
    best = None
    for name in CASE_NAMES:                        # 长名优先；取标注之前最近者
        i = seg.rfind(name, 0, rel)
        if i >= 0 and (best is None or i > best[0]):
            best = (i, name)
    if best:
        return best[1], "pre"
    best2 = None                                   # 其前无 ⇒ 取之后最近者
    for name in CASE_NAMES:
        j = seg.find(name, rel)
        if j >= 0 and (best2 is None or j < best2[0]):
            best2 = (j, name)
    return (best2[1], "post") if best2 else (None, None)


def clause_retry(case, pages, picked):
    """判据 E 重试：枚举该案**全部来源件**（剔阅读包轴）逐件四级判定，取最高级。

    与主链的差别：主链只试**块内代号候选**；重试**枚举全来源**——用于救「取错件」。
    返回 `(级, 件代号, 缺失字面量)`；无一可判返回 `(None, None, None)`。
    """
    best = (None, None, None)
    for src in CASES.get(case, {}).get("sources", []):
        code = src["code"]
        if code in NON_SOURCE_CODES:
            continue
        pm = page_map(case, code)
        if pm is None or any(p not in pm[2] for p in pages):
            continue
        found = locate_literals(case, code, [l for _k, l in picked])
        if found is None:
            continue
        lv, miss = level_of(found, picked, set(pages))
        if best[0] is None or lv > best[0]:
            best = (lv, code, miss)
        if lv == 3:
            break
    return best


def _propose_bare_impl(block, preceding, head, label, picked):
    """主判定实现（由 `propose_bare` 调用；`picked` 由外层按判据 D 过滤/打标后传入）。"""
    pages = []
    for _a, _b in PAGE_TOK_RX.findall(label):
        _a = int(_a)
        _b = int(_b) if _b else _a
        pages.extend(range(_a, _b + 1) if _b - _a <= 60 else [_a])
    if not pages:
        return (None, "无页码", "", 0, 0, "", "")
    if not picked:
        return (None, "无字面量可验", "", 0, 0, "", "")
    raw = []
    for _m in CIT_RX.finditer(block):
        for _c, _p in parse_citation(_m.group(1)):
            if _c not in raw:
                raw.append(_c)
    if not raw:
        _sg = suggest_source(preceding)
        raw = [c for c in _sg.split("／") if c and not c.startswith("无（")]
    if not raw:
        _c0, _h0 = resolve_case(preceding, head, [])       # 无代号线索 ⇒ 退回**按标题判案**，再枚举该案全部来源
        if _c0:
            raw = [s["code"] for s in CASES.get(_c0, {}).get("sources", [])]
    if not raw:
        return (None, "无候选来源", "", len(picked), 0, "", "")
    cands = [c for c in raw if c not in NON_SOURCE_CODES]   # **轴分离**：阅读包系**不作来源件**
    if not cands:
        return (None, "非原件轴", "", len(picked), 0, "", "")
    results = []
    for code in cands:
        case, _hit = resolve_case(preceding, head, [code])
        if not case:
            continue
        for c2, is_written in version_variants(case, code):
            src, rcode = resolve_source(case, c2)
            if src is None:
                continue
            pm = page_map(case, rcode)
            if pm is None or any(p not in pm[2] for p in pages):
                continue                                   # 页码段缺失／材料不可读 ⇒ 该候选验不了
            found = locate_literals(case, rcode, [l for _k, l in picked])
            if found is None:
                continue
            lv, miss = level_of(found, picked, set(pages))
            results.append({"code": code, "case": case, "level": lv, "miss": miss,
                            "rcode": rcode, "is_written": is_written})
    if not results:
        return (None, "无可用材料", "", len(picked), 0, "", "")
    written = [r for r in results if r["is_written"]]
    exact = [r for r in results if r["level"] == 3]
    wlv = written[0]["level"] if written else 3
    # **版本轴只提示不替代**：原文所写版本里没有，而**同案另一版本**里全中 ⇒ 报「版本疑不符」，供人裁
    _sib = [r for r in exact if not r["is_written"]]
    if wlv == 0 and len(_sib) == 1 and len(picked) >= MIN_LIT:
        r = _sib[0]
        return (r["code"], "版本疑不符", r["case"], len(picked), 0, "",
                "字面量全中见同案 `%s`" % r["rcode"])
    if exact:
        if len(picked) < MIN_LIT:                      # **证据强度门**：寥寥数字命中即「巧合」，不算验过
            r = exact[0]
            return (r["code"], "弱证据", r["case"], len(picked), 0, "", _ver_note(r))
        if len(exact) > 1:                             # **多候选都命中 ⇒ 不可区分**，留白（禁择一）
            return (None, "多候选命中", "", len(picked), 0, "", "")
        r = exact[0]
        return (r["code"], "验过", r["case"], len(picked), 0, "", _ver_note(r))
    top = max(r["level"] for r in results)
    if top == 0:
        r = written[0] if written else results[0]
        ms = r["miss"]
        return (r["code"], "该件无此内容", r["case"], len(picked), len(ms),
                "、".join(ms[:5]) + ("…" if len(ms) > 5 else ""), "")
    tops = [r for r in results if r["level"] == top]
    if len(tops) > 1:
        return (None, "多候选命中", "", len(picked), 0, "", "")
    if len(picked) < MIN_LIT:
        r = tops[0]
        return (r["code"], "弱证据", r["case"], len(picked), 0, "", _ver_note(r))
    r = tops[0]
    return (r["code"], "邻近命中" if top == 2 else "文档内存在",
            r["case"], len(picked), 0, "", _ver_note(r))


def propose_bare(block, preceding, head, label, pos=None):
    """**对外接口**：判据 D 取证过滤 → 主判定（`_propose_bare_impl`）→ E 回退 → G 回退。

    · **判据 D**：编号残片／长数字串不作承重字面量；5-9 位裸整数打标不剔除。
    · **判据 E**：主判定判不动时，以子句内案名枚举全来源件重试。
    · **判据 G**：E 也未中时，以**条目内已登记 AN 编号**（对照表硬映射）取案重试。
    · 证据门统一：承重字面量 ≥ `MIN_LIT`；命中均以 `note` 标注判据来源。
    """
    _raw_picked = pick_literals(mask(preceding[-400:]))
    _usable, _dropped, _flagged = d_filter(_raw_picked, preceding[-400:])
    _d_notes = []
    if _dropped:
        _d_notes.append("判据D剔除：%s" % "、".join("%s(%s)" % (l, w) for l, w in _dropped[:3])
                        + ("…" if len(_dropped) > 3 else ""))
    if _flagged:
        _d_notes.append("判据D打标：%s（可疑型，可能是真金额）" % "、".join(l for l, _w in _flagged[:3])
                        + ("…" if len(_flagged) > 3 else ""))
    r = _propose_bare_impl(block, preceding, head, label, _usable)
    if _d_notes and not (r[6] or "").startswith("子句级取案"):
        _note_d = "；".join(_d_notes)
        r = (r[0], r[1], r[2], r[3], r[4], r[5],
             ("%s；%s" % (r[6], _note_d)) if r[6] else _note_d)
    if pos is None or r[1] not in E_RETRY_VERDICTS:
        return r
    _case, _side = clause_case(block, pos)
    _pages = []
    for _a, _b in PAGE_TOK_RX.findall(label):
        _a = int(_a)
        _b = int(_b) if _b else _a
        _pages.extend(range(_a, _b + 1) if _b - _a <= 60 else [_a])
    if not _pages or len(_usable) < MIN_LIT:
        return r
    # 判据 E：子句案名重试
    _e_lv, _e_code, _e_case = None, None, None
    if _case:
        _e_lv, _e_code, _miss = clause_retry(_case, _pages, _usable)
        if _e_lv is not None and _e_lv >= 1:
            _e_case = _case
        else:
            _e_lv, _e_code = None, None
    # 判据 G：条目内已登记 AN 编号重试（**与 E 并试取高**——实测条目头「来源案：X（ANxxxx）」
    # 为登记硬映射，子句案名可能被「戈碧迦案只见落点①…本案三类全实证」型对比从句污染：
    # 该例 E 取戈碧迦=L2（对比从句），G 取天元=L3（来源案正解）⇒ 谁档高用谁，同档 E 优先）
    _g_lv, _g_code, _g_case, _g_an = None, None, None, None
    if pos is not None:
        _gcase, _gan = g_case_from_item(block, pos)
        if _gcase and _gcase != _case:
            _glv, _gcode, _gmiss = clause_retry(_gcase, _pages, _usable)
            if _glv is not None and _glv >= 1:
                _g_lv, _g_code, _g_case, _g_an = _glv, _gcode, _gcase, _gan
    # 择优：G 严格高于 E ⇒ 用 G；否则 E 有中 ⇒ 用 E
    if _g_lv is not None and (_e_lv is None or _g_lv > _e_lv):
        _note_g = ("编号取案（判据 G）：以条目内编号 %s→「%s」重试命中（主判定：%s%s%s）"
                   % (_g_an, _g_case, r[1],
                      ("；E 案「%s」%s" % (_case, ("L%d" % _e_lv) if _e_lv else "未中")) if _case else "；子句无案名",
                      "——AN 映射（来源案）压过子句对比从案" if _e_lv else ""))
        if _d_notes:
            _note_g += "；" + "；".join(_d_notes)
        return (_g_code, E_LEVEL_TO_VERDICT[_g_lv], _g_case, len(_usable), 0, "", _note_g)
    if _e_lv is not None:
        _note_e = "子句级取案（判据 E）：以子句内案名「%s」重试命中（主判定：%s）" % (_case, r[1])
        if _d_notes:
            _note_e += "；" + "；".join(_d_notes)
        return (_e_code, E_LEVEL_TO_VERDICT[_e_lv], _case, len(_usable), 0, "", _note_e)
    return r


# ── 判据 G（编号取案）：E 之后的第二级回退（2026-09-28 吸收 · WO-MF-22.1） ──
# 动因：多案条目里存在「案名（AN 编号）」「域前缀编号（L-AN0044-03）」等**结构化并排写法**——
# AN 编号是《单案索引对照表》里的**登记硬映射**（零歧义），比文本案名更可靠。
# 实测（探针 _probe_g_full.py）：主判定判不动的 592 处中，条目含已登记编号 13 处，救回 2 处
# （均为「多候选唯一化」高价值档）；G2 内联案名实测 0 救回，本轮不吸收。
G_AN_RX = re.compile(r"(?<![A-Za-z0-9])AN(\d{4})(?![A-Za-z0-9])")

AN2CASE = {}
try:
    _tbl = os.path.join(_ROOT, "state", "单案索引对照表.md")
    if os.path.isfile(_tbl):
        for _ln in io.open(_tbl, encoding="utf-8", errors="replace"):
            for _an in re.findall(r"AN\d{4}", _ln):
                for _nm in CASE_NAMES:
                    if _nm in _ln:
                        AN2CASE.setdefault(_an, _nm)
                        break
except OSError:
    pass


def g_case_from_item(block, pos):
    """判据 G：**条目级 AN 编号取案** —— 标注所在条目（；。切分，短段回退）内的已登记 AN 编号。

    返回 `(案名, AN号)` 或 `(None, None)`；多个编号取**离标注最近**者。
    """
    pre = block[:pos]
    s = 0
    for _m in CLAUSE_SEP_RX.finditer(pre):
        s = _m.end()
    item = pre[s:]
    if len(item) < 12:
        s2 = 0
        for _m2 in CLAUSE_SEP_RX.finditer(pre[:s - 1] if s else pre):
            s2 = _m2.end()
        item = pre[s2:]
    best = None                                     # (位置, AN, 案)
    for m in G_AN_RX.finditer(item):
        an = "AN" + m.group(1)
        name = AN2CASE.get(an)
        if name and (best is None or m.start() > best[0]):
            best = (m.start(), an, name)
    return (best[2], best[1]) if best else (None, None)


def parse_citation(label):
    """解析标注里的 (来源代号, [页码…]) 序列；支持 `；` 分隔多来源、`、` 分隔多页"""
    out = []
    for part in re.split(r"[；;]", label):
        toks = PAGE_TOK_RX.findall(part)
        if not toks:
            continue
        pages = []
        for a, b in toks:
            a = int(a)
            b = int(b) if b else a
            if b - a > 60:                                # 荒谬跨页，跳过（防误写数字被当页范围）
                pages.append(a)
            else:
                pages.extend(range(a, b + 1))
        head = PAGE_TOK_RX.sub("", part)
        head = re.sub(r"[\s、,，:：]+", " ", head).strip()
        code = None
        for al, cd in ALIAS2CODE.items():
            if al and al in head:
                if code is None or len(al) > len(code):
                    code = cd
        if code:
            out.append((code, pages))
    return out


def scan_entries():
    files = list(_layout_domain_files(METHODS))
    for d in (DIR_DOMAIN, DIR_LANG, DIR_VOLUME):
        p = os.path.join(METHODS, d)
        if os.path.isdir(p):
            for f in sorted(os.listdir(p)):
                if f.endswith(".md"):
                    files.append(os.path.join(p, f))
    for fp in sorted(set(files)):
        yield fp


suspects, unverifiable, checked, proposals = [], [], 0, []
for fp in scan_entries():
    rel = os.path.relpath(fp, METHODS).replace("\\", "/")
    try:
        text = io.open(fp, encoding="utf-8", errors="replace").read()
    except OSError as e:
        unverifiable.append((rel, 0, "文件读取失败：%s" % e))
        continue
    for block in BLOCK_RX.split(text)[1:]:
        head = block.split("\n", 1)[0]
        if not CIT_RX.search(block):
            continue
        for m in CIT_RX.finditer(block):
            checked += 1
            preceding = block[:m.start()]
            cites = parse_citation(m.group(1))
            if not cites:
                # 与「验不了」分开：这是**标注本身省略了来源代号**（裸页码 `（P180）`／`（PAGE 592）`）。
                # 卷内上下文单一时代号可推，但**本脚本不替作者推断**（推断出错即造假证据）——单列一类，
                # 供判断「标注书写是否完整」，**不参与命中判定**；另给**建议来源**供裁定参考。
                if PAGE_TOK_RX.search(m.group(1)):
                    unverifiable.append((rel, head, "标注省略来源代号（裸页码，未参与判定）：%s ｜建议来源：%s"
                                         % (m.group(1)[:36], suggest_source(preceding))))
                    if _args.propose:
                        _pb = propose_bare(block, preceding, head, m.group(1), m.start())
                        proposals.append((rel, head, m.group(1)[:40], _pb[0] or "—") + tuple(_pb[1:]))
                else:
                    unverifiable.append((rel, head, "标注内解析不出来源代号：%s" % m.group(1)[:50]))
                continue
            case, hit = resolve_case(preceding, head, [c for c, _p in cites])
            if not case:
                unverifiable.append((rel, head, "判不出案（标注前文无已登记案名）：%s" % m.group(1)[:50]))
                continue
            misses = []
            for code, pages in cites:
                if not pages:
                    unverifiable.append((rel, head, "标注无可用页码：%s" % m.group(1)[:50]))
                    continue
                src, rcode = resolve_source(case, code)
                if src is None:
                    unverifiable.append((rel, head, "映射表无此来源：案「%s」× 代号「%s」" % (case, code)))
                    continue
                pt = page_text(case, rcode, pages)
                if pt is None:
                    unverifiable.append((rel, head, "页码段缺失或材料不可读：%s %s P%s" %
                                         (case, code, pages[0] if pages else "?")))
                    continue
                npt = norm(pt)
                seg = mask(preceding[-400:])               # 就近取证：标注前 400 字，**先屏蔽编号/日期戳**
                picked = pick_literals(seg)
                for kind, lit in picked:
                    if norm(lit) not in npt:
                        misses.append((kind, lit))
            if misses:
                seen, uniq = set(), []
                for k, v in misses:
                    if (k, v) not in seen:
                        seen.add((k, v))
                        uniq.append((k, v))
                suspects.append((rel, head, case, m.group(1)[:60], uniq[:8], len(uniq)))

# ── 趟 3：库存对账（cases 有材料、无单案产出、未登记待补学） ─────────────────
inventory = []
try:
    single = os.listdir(os.path.join(METHODS, "40_单案"))
    single_txt = "\n".join(single)
    pend_p = os.path.join(_ROOT, "state", "待补学清单.md")
    pend = io.open(pend_p, encoding="utf-8", errors="replace").read() if os.path.isfile(pend_p) else ""
    cases_dir = os.path.join(CASES_ROOT, "cases")
    if os.path.isdir(cases_dir):
        for dn in sorted(os.listdir(cases_dir)):
            if not os.path.isdir(os.path.join(cases_dir, dn)):
                continue
            short = dn.split("_")[-2] if "_" in dn else dn
            if short in single_txt or short in pend or dn in pend:
                continue
            if any(short and short in k for k in CASES):
                inventory.append(dn)
except OSError:
    pass

if _args.json:
    print(json.dumps({
        "tool": "check_evidence", "level": "report-only",
        "checked_citations": checked,
        "fidelity_suspects": [{"file": a, "entry": b, "case": c, "citation": d,
                               "misses": [{"kind": k, "literal": v} for k, v in e], "n": f}
                              for a, b, c, d, e, f in suspects],
        "unverifiable": [{"file": a, "entry": b, "reason": c} for a, b, c in unverifiable],
        "inventory_gaps": inventory,
        "bare_page_proposals": [{"file": a, "entry": b, "label": c, "candidate": d, "verdict": e,
                                 "case": f, "n_literals": g, "n_miss": h, "miss_sample": i, "note": j}
                                for a, b, c, d, e, f, g, h, i, j in proposals],
    }, ensure_ascii=False, indent=1))
    sys.exit(0)

print("=== 溯源校验（只报不改 · 报告级）===")
print("材料根：%s ｜ 已登记案：%d ｜ 检查标注：%d 处" % (CASES_ROOT, len(CASES), checked))
print()
print("【趟 1 · Fidelity 嫌疑】%d 处（命中失败 ≠ 写错：派生值／口径换算会正常落此栏，交人裁定）"
      % len(suspects))
for a, b, c, d, e, f in suspects[:_args.limit]:
    print("  · %s ｜ %s" % (a, b[:46]))
    print("      案「%s」 标注「%s」 未命中 %d 个，例：%s"
          % (c, d, f, "／".join("%s=%s" % (k, v) for k, v in e[:4])))
print()
print("【趟 2 · 验不了（unverifiable）】%d 处（「压根没验」比「验了疑似不符」更需要人定）" % len(unverifiable))
kinds = defaultdict(int)
for _a, _b, r in unverifiable:
    kinds[re.split(r"[:：]", r)[0]] += 1
for k, v in sorted(kinds.items(), key=lambda x: -x[1])[:8]:
    print("  · %-28s %d 处" % (k, v))
for a, b, r in unverifiable[:_args.limit]:
    print("      %s ｜ %s" % (a, r[:70]))
print()
print("【趟 3 · 库存对账】cases 有材料但无单案产出、且未登记的悬空案：%d 个" % len(inventory))
for dn in inventory[:12]:
    print("  ·", dn)
if _args.propose:
    from collections import Counter as _C
    print()
    print("【附录 · 裸页码「提案＋机械复验」】%d 处（**验过**才可补；其余一律留白）" % len(proposals))
    _v = _C(p[4] for p in proposals)
    for k, n in _v.most_common():
        print("  · %-12s %d 处" % (k, n))
    _n = max(1, len(proposals))
    _ok = [p for p in proposals if p[4] == "验过"]
    _doc_ok = [p for p in proposals if p[4] in ("验过", "弱证据", "邻近命中", "文档内存在")]
    print("  **件对（精确＋邻近＋文档内）＝ %d 处（%.1f%%）** ｜ **可补（验过）＝ %d 处** ｜"
          " **该件无此内容＝ %d 处**（唯一有资格谈「可能写错」的一档）"
          % (len(_doc_ok), len(_doc_ok) / _n * 100, len(_ok),
             sum(1 for p in proposals if p[4] == "该件无此内容")))
    print("  **可补（验过）候选来源分布**：%s"
          % ("／".join("%s %d" % (k, n) for k, n in _C(p[3] for p in _ok).most_common(8)) or "（无）"))
    for a, b, c, d, e, f, g, h, _i, _j in _ok[:_args.limit]:
        print("      %s ｜ %s ｜ %s ⇒ **%s**（案「%s」%d 字面量全中）" % (a, c, b[:34], d, f, g))
print()
print("退出码不承载语义；判定接口 ＝ 本报告（或 `--json`）。本脚本**不修改任何文件**。")
sys.exit(0)

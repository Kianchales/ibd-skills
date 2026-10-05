#!/usr/bin/env python3
"""方法论库 · 路径与命名常量**单一事实源**（2026-09-23 立 · 工单 WO-00）

## 为什么有这个模块

改造前，库内路径/文件名常量散在 16+ 个脚本里各自硬写，实测：

| 常量 | 曾定义于 | 问题 |
|---|---|---|
| `_ROOT` 解析式 | **12 个脚本** | 同一句默认根逻辑抄了 12 遍 |
| `METHODS` | **10 个脚本** | 同上 |
| `SKIP_DIRS` | **4 个脚本** | **4 个取值互不一致** |
| `ENTRY` / `PARSED` / `OUT` | 各 **3 个脚本** | `OUT` 三名三义；`ENTRY` 在 apply_rewrite 里是**正则**不是路径 |
| `EXCLUDE_TOP` / `SKIP_TOP` | 各 1 个脚本 | **内容相同、名字不同** |

后果：目录一改就要在 26 个脚本里摸黑改常量。本模块把这些收成**唯一落点**——
今后迁移目录**只改本文件**（＋搬迁本身）。

## 用法（脚本侧自举）

薄壳转发走 `runpy.run_path`，**不会**把本目录所在 `scripts/` 注入 `sys.path`，
故每个脚本须自举（`__file__` 在直接执行与 runpy 两种入口下均指向 `scripts/` 内该脚本）：

```python
import os as _os, sys as _sys
_d = _os.path.dirname(_os.path.abspath(__file__))
if _d not in _sys.path:
    _sys.path.insert(0, _d)
from _lib.layout import resolve as _layout_resolve, ENTRY_FILE
_ROOT, METHODS, SCRIPTS = _layout_resolve(_args.methods_root)
```

## 硬约束

- 本模块**加载时零副作用**（无模块级 IO）；**函数内** IO 仅限 `count_docs_refs()`（由调用方按需触发）。
- 脚本**不得**再自行拼写库内目录名／文件名；新增路径一律先在此登记。
- `resolve()` 的默认根语义必须与历史一致：`--methods-root` 缺省 → **skill 包根**（＝`scripts/` 的上一级）。
"""
import glob
import os
import sys
from pathlib import Path

# ── 目录名 ────────────────────────────────────────────────────────────────
SKILL_DIR = Path(__file__).resolve().parents[2]   # ＝ ibd-methods-ops/（scripts/_lib/layout.py → 上溯三级）
DEFAULT_ROOT = SKILL_DIR                          # 与历史默认（Path(__file__).resolve().parents[1]）等价

METHODS_NAME = "methods"      # 正文根（{METHODS_ROOT}）＝ 工作区根/methods
SCRIPTS_NAME = "scripts"
# 技能侧脚本目录（＝本模块所在目录）。用于需要「与我同级的脚本」的场景
# （如 refresh_index 顺序调用 parse_titles/gen_index/gen_toc/gen_entry）。
# ⚠️ 与 `resolve()` 返回的 `SCRIPTS`（＝工作区根/scripts，库内薄壳目录）**语义不同**，勿混用。
SCRIPTS_DIR = SKILL_DIR / SCRIPTS_NAME
TASKS_NAME = "tasks"
STATE_NAME = "state"
ARCHIVE_NAME = "archive"

# ── methods/ 下的一级目录（C3b 2026-09-23 · 一维度一物理层） ────────────────
# 元文件（README／编号体系说明／案名规范表／合并映射／旧编号映射表）与 `_generated/`
# **保留根级 ＝「入口层」**：① 人读入口须显眼 ② 避免触碰「按文件名匹配」类判据
# （`TOP_LEVEL_NON_ENTRY`／`V36_FILES`／`WHITELIST` 均以裸名为键）。其余按维度归位。
DIR_DOMAIN = "10_跨案域"                   # 维度①知识域（使用面）
DIR_LANG = "20_语言专项"                   # 维度②文档类型
DIR_INDUSTRY = "30_行业版"                 # 维度③行业（消灭「行业方法论」三义）
DIR_INDUSTRY_MERGED = DIR_INDUSTRY          # 2026-09-23 扁平化：原 30_行业版/合并版/ 上翻一层（「单份细分版」撤除后「合并版」层级冗余）
DIR_INDUSTRY_SUB = DIR_INDUSTRY + "/单份细分版"
DIR_SINGLE = "40_单案"                     # 维度④案（唯一权威正文）
DIR_VOLUME = "50_分卷"                     # 维度⑤书写形态（横切）
DIR_NOTES = "60_notes"                     # 维度⑥过程性质（旁路）

# ── 兼容名（脚本侧零改动：18 个脚本已改为引用下列常量；值由「裸名」变为「含目录路径」）──
NOTES_NAME = DIR_NOTES
VOLUME_NAME = DIR_VOLUME
SINGLE_NAME = DIR_SINGLE
SUB_INDUSTRY_NAME = DIR_INDUSTRY_SUB
GENERATED_NAME = "_generated"    # 脚本生成物隔离目录（2026-09-23 · 工单 WO-04）
BACKUP_NAME = "_backup"
PYCACHE_NAME = "__pycache__"

# ── 文件名（库内顶层 · 手写源） ───────────────────────────────────────────
CANON_TABLE = "方法论_案名规范表.md"          # 案名白名单（手写源）
CASE_INDEX_TABLE = "单案索引对照表.md"         # state/ 下：案名 ↔ AN 号（迁移类脚本共用）
MERGED_MAP = "行业方法论_合并映射.md"          # 行业 15 类归口表
OLD_NUM_MAP = "投行语言_旧编号映射表.md"
NUM_GUIDE = "编号体系说明.md"
README_NAME = "README.md"
PARSED_FILE = "parsed_titles.txt"            # parse_titles 中间产物（落 scripts/）

# ── 域文件（跨案层正文；C3b 拟移至 10_跨案域/） ────────────────────────────
DOMAIN_FILE_PATTERN = "通用方法论_%s域.md"
FINANCE_DOMAIN_FILE = "通用方法论_财务域.md"
LAW_DOMAIN_FILE = "通用方法论_法律域.md"
INDUSTRY_DOMAIN_FILE = "通用方法论_行业域.md"
STYLE_DOMAIN_FILE = "通用方法论_体例域.md"
# ⚠️ **历史名**：09-19 已将「写作域」拆为投行语言专项 WL／PL 两支，实测该文件**不存在**。
#    保留常量仅为承接历史脚本中的字面量（值与原字面量一致 ⇒ 行为等价），新脚本勿引用。
WRITING_DOMAIN_FILE = "通用方法论_写作域.md"
DOMAIN_FILE_LIST = (FINANCE_DOMAIN_FILE, LAW_DOMAIN_FILE, INDUSTRY_DOMAIN_FILE,
                    STYLE_DOMAIN_FILE, WRITING_DOMAIN_FILE)

# ── 语言专项（C3b 拟移至 20_语言专项/） ───────────────────────────────────
LANG_W_FILE = "投行语言专项_回复WL系列.md"     # WL- 系列**入口壳**（0 条）；正文 2026-09-28 按段卷方法外置至 `50_分卷/投行语言专项_回复WL系列_卷NN_*.md`；2026-09-23 WO-06 名实对齐
LANG_P_FILE = "投行语言专项_招股书PL系列.md"   # PL- 卷入口壳（正文在 50_分卷/，542 条）；2026-09-23 WO-06 名实对齐

# ── glob 模式（**含目录前缀**；C3b 2026-09-23） ────────────────────────────
DOMAIN_GLOB = DIR_DOMAIN + "/通用方法论_*域.md"          # 跨案层正文
LANG_GLOB = DIR_LANG + "/投行语言专项_*.md"              # 语言专项
MERGED_GLOB = DIR_INDUSTRY_MERGED + "/行业方法论_*.md"   # 行业合并版
VOLUME_GLOB = "*.md"                                     # 分卷（配合 VOLUME_NAME 使用）
DOMAIN_GLOBS = (DOMAIN_GLOB, LANG_GLOB)                  # 兼容旧用法

# ── 生成物（不手改；check_* 一律排除） ─────────────────────────────────────
# 2026-09-23（WO-04）：三件生成物物理隔离至 `methods/_generated/`，
#   ⇒ 「源 vs 生成物」靠**位置**可分，脚本不再逐个硬写其文件名。
# 变量语义：`*_FILE` ＝ **相对 METHODS 的路径**（含子目录），供 `os.path.join(METHODS, X)` 直接用；
#          `*_BASENAME` ＝ 纯文件名，仅用于「顶层若出现则排除」类判据。
ENTRY_BASENAME = "通用方法论_最终版.md"        # 路由库首页（gen_entry 生成）
TOC_BASENAME = "方法论_条目标题目录.md"         # 编号 → 域文件+行号（gen_toc 生成）
INDEX_BASENAME = "方法论调用索引.md"            # 28Q 速查＋全量映射（gen_index 生成）
REFGRAPH_BASENAME = "方法论_引用图谱.md"        # 反向视图：入度/失效/单向（gen_refgraph 生成；WO-21 2026-09-26）
SOURCE_MAP_BASENAME = "来源代号映射.json"      # 来源代号的**物理指向**单一事实源（gen_source_map 生成；WO-33 2026-09-26 · G1 前置）
SCHEMA_BASENAME = "SCHEMA.md"                  # 库内 schema 入口（gen_schema 生成）
BARE_PAGE_BASELINE = 1712                      # 裸页码**存量水位**（2026-10-03 第七次校准：批后清债实测——2026-10-03 批收尾把「新增裸页码」增量 91 处全部修复（含 WO-MF-23/09-20 批基线滞后债务：行内继承＋特征词/专名双验证定位＋叙述自证），实测降至 1712，较上次 1722 降 10 ⇒ 复核无碍、据实下调。第 24 项「增量零裸页码」的对照值）
#   ↑ 水位沿革：1836（初测）→ 1825（首批有据改注 11 处）→ 1740（本批 85 处）→ 1752（2026-09-30 三次校准）→ 1725（2026-10-01 D5 二轮修补）→ 1723（2026-10-01 D1–D6 裁定项）。「验过」池每次补代号后复核下调。
#   ↑ 为什么是「水位」而不是「待办」：存量 1836 处按设计边界**不回溯补注**（机器逐一复验仅 3.1% 够格、
#     人工亦不可裁）⇒ 判据改为「**不得再上升**」。**下降时应复核后下调本值**（防基线松弛成摆设）。
#   ↑ **位置例外**：留在**库根**、不入 `_generated/` —— 因「入口」的全部价值在于**打开库即可见**；
#     身份判据仍与其余生成物一致（**无 frontmatter ＋ 首行即说明**），故条目扫面不受影响。
#     立意：**库应自描述**——由哪一版 schema 管、规矩在哪、当前结构实况，都写在库内，
#     不依赖使用者的外部记忆或习惯去兜。

ENTRY_FILE = "%s/%s" % (GENERATED_NAME, ENTRY_BASENAME)
TOC_FILE = "%s/%s" % (GENERATED_NAME, TOC_BASENAME)
INDEX_FILE = "%s/%s" % (GENERATED_NAME, INDEX_BASENAME)

REFGRAPH_FILE = "%s/%s" % (GENERATED_NAME, REFGRAPH_BASENAME)
SOURCE_MAP_FILE = "%s/%s" % (GENERATED_NAME, SOURCE_MAP_BASENAME)
SCHEMA_FILE = SCHEMA_BASENAME                  # 相对 METHODS（库根，不在 _generated/）
GENERATED_FILES = {TOC_FILE, INDEX_FILE, ENTRY_FILE, REFGRAPH_FILE, SOURCE_MAP_FILE, SCHEMA_FILE}   # 相对 METHODS 的路径
GENERATED_BASENAMES = {TOC_BASENAME, INDEX_BASENAME, ENTRY_BASENAME, REFGRAPH_BASENAME,
                       SOURCE_MAP_BASENAME, SCHEMA_BASENAME}

# 顶层「非条目文件」——条目扫描时排除（历史两名同容：check_entry_contract `EXCLUDE_TOP` /
# normalize_case_names `SKIP_TOP`，2026-09-23 归一为此外唯一常量）
TOP_LEVEL_NON_ENTRY = {
    TOC_BASENAME, INDEX_BASENAME, MERGED_MAP, OLD_NUM_MAP, NUM_GUIDE, README_NAME,
    ENTRY_BASENAME, CANON_TABLE, SCHEMA_BASENAME,
}

# ── 遍历跳过面 ────────────────────────────────────────────────────────────
# 共同面（4 个脚本一致的部分）
# 2026-09-23（WO-04）：新增 `_generated` —— 生成物三件物理隔离后，条目扫面不再需要
#   在顶层逐个按文件名排除它们（`TOP_LEVEL_NON_ENTRY` 保留裸名仅作双保险）。
SKIP_DIRS_BASE = frozenset({ARCHIVE_NAME, NOTES_NAME, BACKUP_NAME, PYCACHE_NAME, GENERATED_NAME, "cases_md"})
#   ⚠️ 2026-09-30 补：`cases_md/`＝**产出件归档面**（cases/ 工作区全量产出件的库内镜像；无 frontmatter 契约、
#   不属「方法论正文本体」）。原缺此排除 ⇒ S7-f 归档同步后护栏 frontmatter 项误报 986 项（归档件按本案
#   产物形态命名，天然无 --- 头）。排除后检查范围回归「方法论正文本体」立意（见 check_methods_health 第 1 项注释）。

# ⚠️ **四变体定性（2026-09-23 实测，不改行为、只登记结论）**：
#   ① `check_entry_contract` / `check_methods_health` —— **不含 `分卷`**：
#      **有意设计**。二者对 `50_分卷/` 走专门分支（前者只跑 A2＋A4；后者纳入条目总数与行号抽查）。
#   ② `apply_case_no` / `normalize_case_names` —— **含 `分卷`**：
#      二者是「改写型」（写案号／回改案名），历史口径**只作用于 `40_单案/` 与顶层**，不进 `50_分卷`。
#      ⚠️ **潜在缺口**：`50_分卷/` 正文内确有案名引用位（09-19 曾回改 33 处来源标注），
#      故「案名归一是否应覆盖 `分卷`」**未经裁定** —— 属行为变更，**本次不动**，登记待裁。
#   ③ `apply_case_no` 另含 `"40_单案/archive"` —— 历史防御项；实测该目录**不存在**（无实际作用）。
SKIP_DIRS = SKIP_DIRS_BASE                                          # 通用面（①②类的①）
SKIP_DIRS_DEEP = SKIP_DIRS_BASE | {VOLUME_NAME}                      # 深扫面（①②类的②，含分卷）
SKIP_EXTRA_CASE_NO = {"40_单案/archive"}                             # 历史防御项（实测无该目录）
SKIP_DIRS_CASE_NO = SKIP_DIRS_DEEP | SKIP_EXTRA_CASE_NO              # apply_case_no 专用（行为等价）

# ⚠️ 域文件 glob 定义**已上移至「glob 模式」段**（C3b：值已含目录前缀）。
#    2026-09-23 此处原有一份**裸 glob** 定义（`("通用方法论_*域.md", "投行语言专项_*.md")`）
#    会**静默覆盖**上移后的新值 ⇒ 已删除（教训：同一模块内同名常量重复定义 = 定义顺序陷阱）。
#    域文件命名规范：`通用方法论_<域>域.md`（以「域」字结尾，避开单案文件）＋ `投行语言专项_*.md`；
#    2026-09-19 起纳入 `50_分卷/*.md`（P 系列 PL- 与体例域批次卷 S- 的条目正文唯一存放地）。

# ── 编号引用正则（**全族单一事实源** · 2026-09-26）────────────────────────────
# 背景：编号族「**形态枚举不全**」已**五犯**（I-0088／0091／0092／0094 ＋ 2026-09-26 的 PL／S
#   整族漏检：`[FLIW]L?-\d{6}` 不含 `PL-`（542 条）／`S-`（364 条）＝ 全库 53.6%）。
#   根因之一是**同一枚举被复制到多个脚本**、各自漂移 ⇒ 收为本常量，**各脚本一律引用、禁再复制**。
# 硬约束：左界 `(?<![A-Za-z])` 必需（编号族存在「短前缀 ⊂ 长前缀」：`L-` ⊂ `WL-`／`PL-`）。
# 新增编号族时**只改本常量**（同时须进 `check_methods_health.py` 的 `_ID_RX` 登记表以受元自检）。
RX_ID_FAMILY = r"(?<![A-Za-z])(?:WL|PL|[FLIS])-\d{6}|(?<![A-Za-z])I-CL\d{2}-\d{2}"

# ── 「已声明的历史引用」（**单一事实源** · 2026-09-26 WO-33）────────────────────
# 引用处**自带注记**说明该编号在主库无对应（如「`W-070008`（历史编号·主库无对应·待核）」）。
# 这是 **A6 降级留痕的合法形态**（显式声明、机器可识别）——不是「漏改的引用」，而是
# 「**确实引用了不在库内的历史编号，且已告知读者**」⇒ **不计失效欠账**，单列可见即可。
# 收为常量：体检第 8 项与 `gen_refgraph.py` **必须同判**（否则同一库出现「体检报 9／图谱报 13」
#   —— 本库在「多份枚举各自漂移」上已五犯，此处不再复制）。
RX_DECLARED_HIST = r"历史编号[^\n]{0,24}(?:无对应|待核)|(?:无对应|待核)[^\n]{0,24}历史编号"

# ── 来源代号：规范表 ＋ 别名表（**单一事实源** · 2026-09-26 WO-33 · G1 前置）────────
# 契约册 §4 只登记**规范代号**；但库内实际书写高度异形（实测 59 种、约占标注总数四成）。
# 若「解析」只认规范号 ⇒「把 `招 P152` 回到原文」对近半标注直接失败 ⇒ 溯源校验落不了地。
# 处置（与《方法论_案名规范表》三表**同构**）：**别名仅供解析，不入白名单**；新条目须写规范代号；
# 别名**不追溯回改**（属 ③ 内容回写、需语义判断）。
SOURCE_ALIASES = {
    "招": ("招", "招股书", "招股说明书"),
    "招·注册稿": ("招·注册稿", "注册稿"),
    "招·上会稿": ("招·上会稿", "上会稿"),
    "招·申报稿": ("招·申报稿", "申报稿"),
    "招·反馈回复稿": ("招·反馈回复稿",),
    "招·发行稿": ("招·发行稿", "发行稿"),   # 2026-10-03 补：WO-MF-23 重蒸馏批实测使用（发行稿＝注册生效后刊发稿）
    "问1": ("问1", "问询1", "一轮", "一轮回复", "首轮回复", "第1轮", "第1轮回复",
            "回复1", "问1回复", "一次问询", "R1"),
    "问2": ("问2", "问询2", "二轮", "二轮回复", "第2轮", "第2轮回复", "回复2", "二次问询", "R2"),
    "问3": ("问3", "问询3", "三轮", "三轮回复", "第3轮", "第3轮回复", "回复3", "R3"),
    "反馈": ("反馈", "反馈意见", "反馈回复"),
    "落实函": ("落实函", "意见落实函", "审核中心意见落实函"),
    "上会": ("上会",),
    "回复": ("回复", "问", "问询"),        # 「问」/「问询」＝轮次判不出 ⇒ 契约兜底号「回复」
    "财务包": ("财务包", "财务", "财务阅读包", "阅读包_财务"),
    "法律包": ("法律包", "法律", "法律阅读包", "阅读包_法律"),
    "行业包": ("行业包", "行业", "行业阅读包", "阅读包_行业"),
    # 2026-09-26 二次裁定：三个蒸馏专家产出件署名代号**不入库**——条目正文已全部中性化
    #   （「产出_X_蒸馏.md」引用写法同步中性化），别名表不再收编；cases/ 原始件名不动（历史事实）。
}
SOURCE_ALIAS2CANON = {a: c for c, _lst in SOURCE_ALIASES.items() for a in _lst}
# 复合标注的分段符：标注常写成「（<前文片段>，<真代号> P…）」⇒ 取**末段**才是真代号。
# `·` 亦入列 —— `<案例主体>·招`→`招`、`招·注册稿`→`注册稿`（再由别名表还原为 `招·注册稿`），两向皆通。
SOURCE_CODE_SPLIT = "，,、；;＋+→/："   # 2026-09-26 裁定加全角冒号（字段连接符：「实证：招 P97」→「招」）


def normalize_source_code(head):
    """把来源标注的「头」归一到规范代号；认不出返回 None（**不猜**）。

    `head` ＝ 标注 `（` 与 ` P<数字>` 之间的原文片段（可能含前文残片）。
    """
    if not head:
        return None
    seg = head
    for ch in SOURCE_CODE_SPLIT:
        seg = seg.split(ch)[-1]
    seg = seg.split("·")[-1]
    seg = seg.strip().strip("`*（）()[]【】 ")
    return SOURCE_ALIAS2CANON.get(seg)


# ── 计数一致性扫描面（**活文档白名单** · 2026-09-26 · 体检第 20 项共用）──────────
# 背景：同一批「护栏 N 项／随包脚本 N 个」声明散布在 8+ 处**活文档**里、各自漂移
#   （2026-09-26 当日实测四度：护栏 16/18/19；脚本 15/25/26/27；README 版本徽章滞后一版）。
# 判据：**只扫活文档**——CHANGELOG（历史）、logs/（操作日志 append-only）、tasks/ 与 docs/
#   （执行记录）、archive/、methods/**（条目正文内的「护栏第 N 项」是**项号引用**、非计数声明）
#   **一律不扫**。历史记录保留原值，改它即是伪造。
# 活文档内遇「近期更新／版本历史」类小节即**停止扫描**（该节属历史）。
_COUNT_DOCS_FIXED = (                    # 相对 **skill 根**：根级三件
    "SKILL.md",
    "README.md",
    "scripts/check_methods_health.py",   # 本脚本自身（docstring 表头 ＋ argparse 描述亦属声明）
)
#   ↑ 判据＝**活文档**（长期被读、会被读者当事实源的册子）。
#   **派生面 ＝ `references/**/*.md` 全量**（不再逐件枚举）——理由＝**失败方向**：
#     枚举的失败方向是**静默漏扫**（新增册子忘登记 ⇒ 永久在面外，既不 ERROR 也不 WARN）；
#     派生的失败方向是**多扫**，而多扫只产生**可见**的报告项、可由人裁定。
#     ⇒ **把失败方向从静默翻转为可见**，是本节采用派生的唯一理由。
#     `CHANGELOG.md` 属历史记录、不进面内；各册的「近期更新／版本历史」小节亦停止扫描。
def count_docs_refs(skill_dir=None):
    """`references/**/*.md` 派生面（相对 skill 根）——**惰性函数**。

    2026-10-02 代码体检：原为**模块级** `os.walk` ⇒ **import 本模块即扫盘**，
    与本模块「加载时零副作用」自述矛盾，且全包只有 `check_methods_health` 第 20 项
    一个调用方需要它 ⇒ 改为按需调用（`skill_dir` 缺省＝本包根）。
    """
    base = Path(skill_dir) if skill_dir else SKILL_DIR
    return tuple(sorted(
        os.path.relpath(os.path.join(_r, _f), str(base)).replace(os.sep, "/")
        for _r, _dirs, _fs in os.walk(str(base / "references"))
        for _f in _fs if _f.endswith(".md")
    ))


def count_docs(skill_dir=None):
    """活文档白名单（skill 侧）＝ **固定三件** ＋ `references` 派生面（相对 skill 根）。"""
    return _COUNT_DOCS_FIXED + count_docs_refs(skill_dir)
COUNT_DOCS_WORKSPACE = (            # 相对 **工作区根**
    "state/README.md",
    "state/维护体检计数.md",
)
COUNT_SCAN_STOP_HEADING = r"^#{1,6}\s*[^\w\s]{0,4}\s*(?:近期更新|版本历史|变更记录|CHANGELOG)"
#   ↑ `[^\w\s]{0,4}` 容许标题内的 emoji／符号前缀（实测 `## 📌 近期更新` —— 无此段会**漏停**、
#     把 README 历史小节的「8 个脚本」当成计数声明误报）。

# ── 阈值 ─────────────────────────────────────────────────────────────────
DOMAIN_SIZE_WARN_BYTES = 300 * 1024     # 单域文件体积警戒线（check_methods_health 第 9 项）


def ensure_utf8():
    """Windows 控制台默认 GBK／cp936，直接 print 中文会乱码或抛 UnicodeEncodeError。

    凡有中文输出的脚本，应在 argparse 之后、首次输出之前调用本函数。
    （历史上各脚本各自写 `sys.stdout.reconfigure(...)`，2026-09-23 收为本函数唯一落点。）

    **去留已定论（2026-09-28 实测复核）**：本函数**当前零调用**（全包 grep 调用点 ＝ 0），
    但它**是 `check_conformance.py` A8 判据认可的编码处理标准入口**（判据：含中文输出且
    既无 `reconfigure` 也无 `ensure_utf8` ⇒ 报 WARN）⇒ **保留**。删它须**同批改 A8 判据**
    （改动面两处、收益为零），且会连带删掉「编码已处理」的判定依据。**勿再作为死代码项重议。**
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def domain_files(methods_dir):
    """返回域文件清单（跨案域正文 ＋ 语言专项 ＋ 分卷），顺序与历史实现逐字一致。"""
    out = sorted(glob.glob(os.path.join(methods_dir, DOMAIN_GLOBS[0])))
    out += sorted(glob.glob(os.path.join(methods_dir, DOMAIN_GLOBS[1])))
    out += sorted(glob.glob(os.path.join(methods_dir, VOLUME_NAME, VOLUME_GLOB)))
    return out


def library_files(methods_dir):
    """返回库内**正文类**文件（域文件 ＋ 语言专项 ＋ 行业合并版 ＋ 分卷）。

    用途：全文兜底判定（如「该案简称是否已在库内出现」）。
    **不含**：元文件（根级）、`40_单案/`、`60_notes/`、`_generated/`。
    C3b 前旧写法为「`methods/*.md` ＋ `methods/分卷/*.md`」——搬迁后 `methods/` 根级只剩
    元文件，故必须改为按目录枚举（否则兜底判定会静默漏掉全部正文）。
    """
    return domain_files(methods_dir) + sorted(glob.glob(os.path.join(methods_dir, MERGED_GLOB)))


def resolve(methods_root=None):
    """解析库根 → `(_ROOT, METHODS, SCRIPTS)`（Path / str / str）。

    `methods_root` 语义＝**库所在的工作区根**（其下须有 `methods/`）；缺省 → skill 包根（历史默认）。
    """
    root = Path(methods_root) if methods_root else DEFAULT_ROOT
    return root, str(root / METHODS_NAME), str(root / SCRIPTS_NAME)

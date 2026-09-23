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

- 本模块**只放常量与纯函数**，不做 IO、不读库。
- 脚本**不得**再自行拼写库内目录名／文件名；新增路径一律先在此登记。
- `resolve()` 的默认根语义必须与历史一致：`--methods-root` 缺省 → **skill 包根**（＝`scripts/` 的上一级）。
"""
import os
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
LANG_W_FILE = "投行语言专项_回复WL系列.md"     # 正文装 WL- 编号（364 条，位于根级）；2026-09-23 WO-06 名实对齐
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
ENTRY_BASENAME = "通用方法论_最终版.md"        # 路由入口薄壳（gen_entry 生成）
TOC_BASENAME = "方法论_条目标题目录.md"         # 编号 → 域文件+行号（gen_toc 生成）
INDEX_BASENAME = "方法论调用索引.md"            # 28Q 速查＋全量映射（gen_index 生成）

ENTRY_FILE = "%s/%s" % (GENERATED_NAME, ENTRY_BASENAME)
TOC_FILE = "%s/%s" % (GENERATED_NAME, TOC_BASENAME)
INDEX_FILE = "%s/%s" % (GENERATED_NAME, INDEX_BASENAME)

GENERATED_FILES = {TOC_FILE, INDEX_FILE, ENTRY_FILE}                 # 相对 METHODS 的路径
GENERATED_BASENAMES = {TOC_BASENAME, INDEX_BASENAME, ENTRY_BASENAME}

# 顶层「非条目文件」——条目扫描时排除（历史两名同容：check_entry_contract `EXCLUDE_TOP` /
# normalize_case_names `SKIP_TOP`，2026-09-23 归一为此外唯一常量）
TOP_LEVEL_NON_ENTRY = {
    TOC_BASENAME, INDEX_BASENAME, MERGED_MAP, OLD_NUM_MAP, NUM_GUIDE, README_NAME,
    ENTRY_BASENAME, CANON_TABLE,
}

# ── 遍历跳过面 ────────────────────────────────────────────────────────────
# 共同面（4 个脚本一致的部分）
# 2026-09-23（WO-04）：新增 `_generated` —— 生成物三件物理隔离后，条目扫面不再需要
#   在顶层逐个按文件名排除它们（`TOP_LEVEL_NON_ENTRY` 保留裸名仅作双保险）。
SKIP_DIRS_BASE = frozenset({ARCHIVE_NAME, NOTES_NAME, BACKUP_NAME, PYCACHE_NAME, GENERATED_NAME})

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

# ── 阈值 ─────────────────────────────────────────────────────────────────
DOMAIN_SIZE_WARN_BYTES = 300 * 1024     # 单域文件体积警戒线（check_methods_health 第 9 项）


def ensure_utf8():
    """Windows 控制台默认 GBK／cp936，直接 print 中文会乱码或抛 UnicodeEncodeError。

    凡有中文输出的脚本，应在 argparse 之后、首次输出之前调用本函数。
    （历史上各脚本各自写 `sys.stdout.reconfigure(...)`，2026-09-23 收为本函数唯一落点。）
    """
    import sys
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def domain_files(methods_dir):
    """返回域文件清单（跨案域正文 ＋ 语言专项 ＋ 分卷），顺序与历史实现逐字一致。"""
    import glob
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
    import glob
    return domain_files(methods_dir) + sorted(glob.glob(os.path.join(methods_dir, MERGED_GLOB)))


def resolve(methods_root=None):
    """解析库根 → `(_ROOT, METHODS, SCRIPTS)`（Path / str / str）。

    `methods_root` 语义＝**库所在的工作区根**（其下须有 `methods/`）；缺省 → skill 包根（历史默认）。
    """
    root = Path(methods_root) if methods_root else DEFAULT_ROOT
    return root, str(root / METHODS_NAME), str(root / SCRIPTS_NAME)

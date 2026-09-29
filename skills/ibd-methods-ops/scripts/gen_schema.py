#!/usr/bin/env python3
"""库内 schema 入口生成器：派生重写 `{METHODS_ROOT}/SCHEMA.md`（库根）

立意 —— **库应自描述**：由哪一版 schema 管、规矩在哪读、当前结构实况、机器会拦什么，
全部落在**库内**一个文件里；使用者（人／别的会话／别的机器／库的接收方）**不必依赖外部记忆**。

三条设计约束（勿破）：
  1. **不复制规则正文**——只放**导航与水位**。复制正文＝制造第二个口径，正是本库持续在治的病。
  2. **全部派生**——版本读 skill `SKILL.md` frontmatter，结构读目录实况，水位读正文 frontmatter；
     不写「今天几号」这类不可派生的东西（否则重跑即产生差异，幂等失效）。
  3. **不写计数**——「几项护栏／几个脚本」一律不写死（写死即成为下一个漂移点）。

用法：
    python gen_schema.py [--methods-root <工作区根>]
"""
import argparse, io, os, re, sys, datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_ap = argparse.ArgumentParser(description="生成库内 schema 入口（SCHEMA.md）")
_ap.add_argument("--methods-root", default=os.environ.get("METHODS_ROOT", ""),
                 help="工作区根（= 库根，其下含 methods/；默认 $METHODS_ROOT，或脚本上级目录）")
_args = _ap.parse_args()

import os as _lo, sys as _ls
_ls.path.insert(0, _lo.path.dirname(_lo.path.abspath(__file__)))
from _lib.layout import (
    resolve as _layout_resolve, SKILL_DIR, SCHEMA_FILE, README_NAME, NUM_GUIDE,
    CANON_TABLE, MERGED_MAP, OLD_NUM_MAP, GENERATED_NAME, DIR_DOMAIN, DIR_LANG,
    DIR_INDUSTRY, DIR_SINGLE, DIR_VOLUME, DIR_NOTES, ARCHIVE_NAME, STATE_NAME,
    TASKS_NAME, domain_files as _layout_domain_files,
)
_ROOT, METHODS, SCRIPTS = _layout_resolve(_args.methods_root)
SCHEMA = os.path.join(METHODS, SCHEMA_FILE)


def _require_library():
    if not os.path.isdir(METHODS):
        sys.stderr.write("✗ 未找到方法论库：%s\n" % METHODS)
        sys.stderr.write("  用法：--methods-root <工作区根>（或设环境变量 METHODS_ROOT）\n")
        sys.exit(2)


_require_library()


def skill_version():
    """schema 版本水位来源：skill `SKILL.md` frontmatter 的 version（缺省 unk）"""
    try:
        with io.open(os.path.join(str(SKILL_DIR), "SKILL.md"), encoding="utf-8") as f:
            m = re.search(r"(?m)^version:\s*(\S+)", f.read(4000))
            return m.group(1) if m else "unk"
    except OSError:
        return "unk"


def content_watermark():
    """库内容水位：各域文件 frontmatter `updated` 最大值（派生，非「今天」）"""
    mx = ""
    for df in _layout_domain_files(METHODS):
        try:
            with io.open(df, encoding="utf-8") as f:
                m = re.search(r"(?m)^updated:\s*(\d{4}-\d{2}-\d{2})", f.read(600))
        except OSError:
            m = None
        if m and m.group(1) > mx:
            mx = m.group(1)
    return mx or "—"


def count_dir(rel, pattern="*.md", base=None):
    import glob
    d = os.path.join(base or METHODS, rel)
    return len(glob.glob(os.path.join(d, pattern))) if os.path.isdir(d) else 0


def count_domain_files():
    return len(_layout_domain_files(METHODS))


rows = [
    ("`%s/`" % DIR_DOMAIN, "跨案层**入口壳**：体例／财务／法律／行业域的域壳＋族分卷索引（正文多在 `%s/`）" % DIR_VOLUME, count_dir(DIR_DOMAIN)),
    ("`%s/`" % DIR_LANG, "语言专项入口壳（WL／PL 系列；正文在 `%s/` 的段卷）" % DIR_VOLUME, count_dir(DIR_LANG)),
    ("`%s/`" % DIR_INDUSTRY, "行业合并版（按分类归口，新案**追加**到对应类，不新立细分文件）", count_dir(DIR_INDUSTRY)),
    ("`%s/`" % DIR_SINGLE, "**单案范式文件（唯一权威正文）**：综合蒸馏范式，四域合体", count_dir(DIR_SINGLE)),
    ("`%s/`" % DIR_VOLUME, "正文外置卷（族卷／段卷）——**跨案层与语言专项的正文实际存放地**", count_dir(DIR_VOLUME)),
    ("`%s/`" % DIR_NOTES, "蒸馏笔记（按日期；过程性质，不进检索面）", count_dir(DIR_NOTES)),
    ("`%s/`" % GENERATED_NAME, "**脚本生成物**（隔离目录）：路由入口／调用索引／条目标题目录／引用图谱／来源代号映射", count_dir(GENERATED_NAME, "*")),
    ("`%s`" % README_NAME, "**库首页**（人读入口）：主从关系、现行结构、案号体系、索引覆盖边界", 1),
    ("`%s`／`%s`／`%s`／`%s`" % (NUM_GUIDE, CANON_TABLE, MERGED_MAP, OLD_NUM_MAP),
     "元文件：编号体系说明／案名规范表／行业合并映射／旧编号映射表", 4),
    ("`%s`" % SCHEMA_FILE, "**本文件**（库内 schema 入口，机器生成）", 1),
    ("`../%s/`" % ARCHIVE_NAME, "归档区（与正文根**平级**，不在库内）", count_dir(ARCHIVE_NAME, base=_ROOT)),
    ("`../%s/`" % STATE_NAME, "库状态台账（与正文根**平级**）：`state/` ＝ 现在到哪了，`logs/` ＝ 发生过什么", count_dir(STATE_NAME, base=_ROOT)),
    ("`../%s/`" % TASKS_NAME, "待办与工单（与正文根**平级**）", count_dir(TASKS_NAME, base=_ROOT)),
]

struct_rows = "\n".join(
    "| %s | %s | %s |" % (a, b, (c if isinstance(c, int) else c)) for a, b, c in rows)

def references_catalog():
    """**派生**：扫 skill `references/**/*.md` → (展示路径, 标题, 类别)。

    为什么派生：本表原为生成器内**手写枚举**（8 条册子路径）——改册名／增册后**静默过期**，
    而体检第 23 项只比版本号、查不出。这与「人工枚举 ⇒ 静默失效」同族（该族刚在计数扫描面治过一轮），
    **不得在原处复发** ⇒ 改为扫目录：增册／改名**自动纳入**。
    标题取册内首个 `# ` 行（无则退文件名），供读者**按标题找册**。
    """
    base = os.path.join(str(SKILL_DIR), "references")
    out = []
    for r, _d, fs in os.walk(base):
        for f in sorted(fs):
            if not f.endswith(".md"):
                continue
            p = os.path.join(r, f)
            rel = os.path.relpath(p, str(SKILL_DIR)).replace(os.sep, "/")
            title = f
            try:
                for ln in io.open(p, encoding="utf-8", errors="replace").read().splitlines()[:60]:
                    if ln.startswith("# "):
                        title = ln[2:].strip()
                        break
            except OSError:
                pass
            grp = "治理" if "/govern/" in rel else ("模板" if "/templates/" in rel else "核心")
            out.append(("ibd-methods-ops/" + rel, title, grp))
    return sorted(out, key=lambda t: (t[2], t[0]))


CATALOG_ROWS = "\n".join("| `%s` | %s | %s |" % r for r in references_catalog())

TPL = """# 本库 Schema 入口（机器生成 · 请勿手改）

> **本文件是什么**：**本文件所在目录（正文根）**这个方法论库的**自描述入口**——回答四个问题：**本库由谁管、当前版本水位、规矩在哪读、机器会拦什么**。
> **本文件不是什么**：**不是规则本体**。规则本体在管理 skill `ibd-methods-ops` 的 `references/` 内；本文件**只做导航与水位声明，不复制规则正文**——复制即产生**第二个口径**，而「多份口径各自维护」正是本库一直在治的病。
> **生成方式**：`ibd-methods-ops` 的 `scripts/gen_schema.py` 重生成；**请勿手改**（手改会被下次重生成静默覆盖）。
> **身份判据**：本文件是**生成物**——**无 frontmatter ＋ 首行即说明**（与 `{GENERATED}/` 内各生成物同一判据；手写源一律带 frontmatter）。

## 一、本库由谁管 · 版本水位

| 项 | 值 |
|---|---|
| 管理 skill | `ibd-methods-ops` |
| **schema 版本水位** | **`{VER}`** |
| 库内容水位（正文 `updated` 最大值） | `{UPD}` |
| 正文根（`@@MROOT_TOKEN@@`） | **＝本文件所在目录**（**不写绝对路径**——写死会使本文件**跨机不幂等**：库若走同步盘跨机，在另一台机器重生成会产出不同内容、制造无意义冲突） |

> **水位怎么用**：体检会比对「**本文件记录的 schema 版本**」与「**skill 实际版本**」。若 skill 已升版而本文件未重生成 ⇒ 报「**库内 schema 水位滞后**」。
> 这是**库侧唯一能自证「我由哪一版规矩管过」的机制**——不需要使用者记得、也不依赖任何库外文件。发现滞后即重跑 `gen_schema.py`。

## 二、库结构（生成时实况）

| 目录／文件 | 内容 | 件数 |
|---|---|---|
{STRUCT_ROWS}

> 件数由生成时**实测**，不手写。目录为空的项＝该维度本库暂未使用，不是缺口。

## 三、规矩在哪读

> **本表由生成器扫 `references/**/*.md` 派生**（不逐件枚举）——新增或改名的册子会**自动**出现在这里；若本表缺某册，说明本文件**未重生成**。
> **先读哪本**：拿不准时先读 **`ibd-methods-ops/references/library-rules.md`**——它是全部规则的**四层地图**（体系层／库层／执行层／触发层）＋ **判据实现处**（哪条判据在哪个文件哪一行判），由它再分流到具体册子。

| 册子（skill 包内路径） | 标题（取自册内首行） | 类别 |
|---|---|---|
{CATALOG_ROWS}

> **为什么只放导航、不放正文**：规则本体在管理 skill 的 `references/` 内，随该 skill 版本迭代（有独立版本号与变更记录），**不在库内再存一份**——复制即产生**第二个口径**。本库只保证「**入口在库内**」：打开库就知道规矩去哪儿读。

## 四、机器会拦什么（不变量摘要 · 不写计数）

结构性不变量（违则体检报 ERROR，全部由 `ibd-methods-ops` 的体检脚本判定）：

- **编号**：全库唯一、族内连续、段号不跳；引用目标必须存在于登记面。
- **条目契约**：来源标注「来源简称 ＋ 页码」、单案层字段名、案名在册、实证标签白名单。
- **位置**：行业共通章须落在子行业章之前；卷号同域唯一；已撤除的载体目录存在即报错。
- **骨架**：单案齐七节、行业合并版齐四段。
- **计数声明**：活文档里的「护栏几项／脚本几个」必须与实况一致。
- **库内 schema 水位**：本文件第一张表的版本必须与 skill 实况一致。

**授权分级**（谁可以自动改、谁只能报）：分「可安全自动修复／只报不改（机械）／只报不改（判断）」三档，逐项贴档见 `govern/health-check.md`。
**铁律**：**语义与事实类改动永不自动**；自动修复必须**候选解唯一**才动手，零解或多解一律转人工清单。

## 五、怎么跑体检

```bash
# 定位到管理 skill 的 scripts/ 后（或用其绝对路径）
python check_methods_health.py --methods-root "<工作区根>"
```

- **判定接口 ＝ 报告输出**；退出码只表「有无 ERROR」：`0` 无 ERROR（可有 WARN）｜`1` 有 ERROR｜`2` 前置失败（未找到库）｜`3` `--strict` 下 WARN > 0。
- **取证要留痕、对照不留痕**：本命令**默认把结果追加进** `logs/库操作日志.md`；凡「故意制造缺陷」的对照／探针运行，**必须加 `--no-log`**。

## 六、本文件自身的不变量

1. **生成物，勿手改**——改规则请改 skill 包，再重跑 `gen_schema.py`。
2. **不复制规则正文**——只放导航与水位（复制即第二口径）。
3. **不写计数与日期**——一律派生，保证重跑**幂等**（无内容变化则逐字节一致）。
4. **不承载细则**——细则归 skill 包；本文件失效或缺失不阻断作业，但会使库**失去自描述能力**。
"""

out = (TPL.replace("{GENERATED}", GENERATED_NAME)
          .replace("{VER}", skill_version())
          .replace("{UPD}", content_watermark())
          .replace("{CATALOG_ROWS}", CATALOG_ROWS)
          .replace("{STRUCT_ROWS}", struct_rows)
          .replace("@@MROOT_TOKEN@@", "{METHODS_ROOT}"))

with io.open(SCHEMA, "w", encoding="utf-8", newline="\n") as f:
    f.write(out)
print("库内 schema 入口已重写: %s" % SCHEMA)
print("  schema 版本水位 = %s ｜ 库内容水位 = %s ｜ 结构表 %d 行"
      % (skill_version(), content_watermark(), len(rows)))
sys.exit(0)

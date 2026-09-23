---
name: ibd-doc-annotate
slug: ibd-doc-annotate
displayName: IBD 批注与修订交付
summary: A 股投行复核结论落到原文（Word docx / PDF）的执行器，批注与修订双形态同源：复核问题清单 + 原文 → 批注版文档 + 精简总览（只加批注不改原文），或生成修订稿（形态先与用户确认：Word 修订模式 / 直接改好 / 双版）+ 修改清单。
description: >
  本技能是「复核结论落地执行器」，承接复核交付双形态——批注与修订同源（同一份复核问题清单）：
  ① 批注版（现役）：接收结构化复核问题清单（作者/类型/严重度/锚点/标题/描述/建议）与原文
  docx 或 PDF，自动把每条问题变成一条 Word 审阅批注或 PDF 高亮注释锚定在原文问题句段上，
  并同步生成与批注编号一一对应的精简总览报告（**双轨并存、批注优先**——交付口径见
  `ibd-doc-review` skill 的 delivery.md；总览**双格式交付 = MD + Word**，2026-09-18 用户裁定；
  总览兼作兜底：无法自动锚定的条目在其中列出
  待人工定位）。脚本自动完成：编号分配（清单 code 字段 + 该前缀序号，脚本不内置任何
  人名/代号映射）、锚点定位（docx 跨 run 拆分且保留原格式 / PDF 字符级容忍空白）、
  批注正文 4 行紧凑排版、Word comments 四件套补全、总览生成（md + docx 双格式）。
  ② 修订稿（现役）：用户明确「生成修订稿」时，先与用户确认输出形态（Word 修订模式 /
  直接改好 / 双版，**不按措辞自动路由**），按问题清单的 rev 替换文本把改动落到原文，
  输出修订稿 docx + 修改清单（已修订/待人工两区）。
  触发词：「原位批注」「复核意见打在原文」「把审核意见做成批注」
  「批注版交付」「生成批注版」「生成修订稿」「出修订稿」「直接改好」「干净版」
version: 0.10.0
agent_created: true
---

# ibd-doc-annotate（IBD 批注与修订交付）

把复核结论**落到原文上**：给一份问题清单和一份原文（Word/PDF），产出「批注版原文 + 精简总览」，每条批注锚在问题句段、编号与总览一一对应。只加批注、不改原文一个字。

## 定位简介（复核落地 · 双形态）

**执行器**——与 `ibd-doc-review`（只管规范与门禁、不生成）分工，两形态均现役：**批注版原文**（docx → Word 审阅批注 / PDF → 高亮弹注，只加批注不改原文）｜**修订稿**（docx，`revise`=Word 修订模式／`clean`=直接改好／`both`=双版，**形态先与用户确认，不按措辞自动路由**，与批注同源）。交付口径（默认形态／路由／职权划分／全量覆盖纪律）= `ibd-doc-review` 的 **delivery.md**，本 skill 只执行不另立。详表见 [ops-notes.md](references/ops-notes.md) §定位。

## 何时使用

用户要求把复核/审查意见落到文档原文（批注或修订）时触发：

| 场景 | 触发词示例 |
|------|-----------|
| 章节复核批注交付（docx 原文） | 「复核意见打成批注」「把审核报告改成批注版」「批注打在原文上」 |
| PDF 披露稿批注交付 | 「PDF 上标注释」「高亮+批注」 |
| 批注版生成全流程 | 「原位批注」「复核意见打在原文」「批注版交付」「生成批注版」 |
| 修订稿生成（revise 默认） | 「生成修订稿」「出修订稿」「出一版修订稿」 |
| 修订稿直接改好 / 双版 | 「直接改好」「干净版」「定稿」｜「两个都要」「修订版+干净版」 |

> **单入口路由（ADR-0006，0.6.0 起）**：批注类任务（docx + PDF）以**本 skill 为唯一对外入口**——`ibd-doc-review` 的 `check_annotations.py`（尤其 PDF 侧 `--pdf`）由本 skill 内部回调，下游包/外部使用者不直接调用。
>
> 配合链路：**复核问题从哪来** → `ibd-doc-review`（格式核对/审阅）或专家团分析产出问题清单；**交付口径**（默认形态/触发语路由/批注纪律）→ `ibd-doc-review` 的 **delivery.md**；**批注格式规范** → `ibd-doc-review` 的 annotations.md、**修订稿规范** → `ibd-doc-review` 的 revisions.md（单一事实源，本 skill 只执行不另立规则）；**产出校验** → `ibd-doc-review` 的 check_annotations.py（批注）/ check_revisions.py（修订稿），交付前必跑，任一 FAIL 退回重做。
>
> ⚠️ **依赖声明（断链自助）**：`ibd-doc-review` 是本技能的外部依赖，**不随本包携带**——安装本技能后须自行另装 `ibd-doc-review`（获取途径 = GitHub 发布渠道：Kianchales/ibd-skills 集合仓库 `skills/` 子目录，与获取本技能同一来源），缺它则格式规范、校验门禁不可用（断链）。详见「依赖与工具」。

## 使用流程

> 最小复现示例（清单校验 / 批注注入 / 修订生成，含期望输出）见 [examples.md](references/examples.md)。

### 1. 准备输入

**判据**：原文 = docx（推荐，批注体验最佳）或 PDF（⛔ 招股书 PDF→docx 转换有版面失真风险，**禁止作为批注载体转换链路**，PDF 就用 PDF 批注）；清单 = 复核问题清单 JSON 数组，**读入即自动过入口校验**——ERROR 级拦退出（exit 2）不注入、WARN 级仅提示（`sev` 限 {高,中,低} 三档结构枚举，越档即 ERROR）。

- 字段语义（`author`／`code`／`type`／`sev`／`anchor`／`rev`／`page`）与**清单单元 = 根因问题**：[issues-schema.md](references/issues-schema.md) §二
- 模板 `issues.example.json`（随包）、**入口校验 ERROR／WARN 两级判据**：[issues-schema.md](references/issues-schema.md) §一／§三

### 2. 执行注入 / 修订

**判据**：批注 → `annotate_docx.py`（docx）／`annotate_pdf.py`（PDF）；修订 → `revise_docx.py --mode revise|clean|both`（**形态先与用户确认，不按措辞自动路由**）。**`annotate_docx.py --dry-run`（2026-09-23 补）**：只报「命中／未锚定」统计与目标路径、**不写任何文件**，用于锚点质量预检；**目标已存在时默认拒绝覆盖**，要覆盖须显式 `--force`——本脚本是产线里**唯一直写交付件**的环节，误盖 ＝ 静默丢上一轮复核结果。

```bash
# ── 批注版 ──（PDF 侧 --pages "5-6" 可节选页）
python scripts/annotate_docx.py --docx <原文.docx> --issues issues.json [--out <输出.docx>] [--dry-run] [--force]
python scripts/annotate_pdf.py --pdf <原文.pdf> --issues issues.json [--pages "5-6"] [--out <输出.pdf>]
# ── 修订稿（docx；形态由用户确认后传入 --mode）──
python scripts/revise_docx.py --docx <原文.docx> --issues issues.json --mode revise|clean|both
```

批注脚本自动完成：**编号分配** → **锚点定位** → **批注注入**（正文 4 行紧凑排版）→ **总览生成**（md + docx 双格式）；修订脚本自动完成：编号分配 → 锚点定位 → 按 rev 落定 → 修改清单生成（缺 rev／复杂 run／重叠／未锚定记「待人工」不硬撑）。

- **批注侧详规**（跨 run 锚定与复杂 run、PDF 页对象持有、同段多批注 range 补插、表格锚点选唯一数值）：[annotate-runbook.md](references/annotate-runbook.md)
- **修订侧详规**（按 rev 落定、`w:delText`、`w:trackRevisions`、rPr 继承、多锚点倒序）：[revise-runbook.md](references/revise-runbook.md)

### 3. 校验门禁（交付前必跑）

**判据**：批注版过 `check_annotations.py`（条数 == cs/ce/ref 对数、四件套注册等）、修订稿过 `check_revisions.py`（ins==del 对、author 归责、trackRevisions 开启等）——**任一 FAIL → 修正后重做，不交付**。命令与逐项检查点见 [delivery-and-gates.md](references/delivery-and-gates.md) §三／§四。

### 4. 交付物

**判据**：命名用 `<原文>_<YYYYMMDD>_v<N>_<形态>`（**G3**：同轮重跑覆盖、跨轮必升 N，`--out` 显式传入）；六类产物（批注版／总览双格式／修订稿／clean 版／修改清单）清单见 [delivery-and-gates.md](references/delivery-and-gates.md) §一／§二。

## 资源索引

| 资源 | 位置 | 归属 |
|---|---|---|
| 批注格式单一事实源（正文结构/编号/词表/字体/锚点/门禁） | `ibd-doc-review` 的 annotations.md | 🔗 外部依赖 |
| 修订稿规范单一事实源（三模式/rev 字段/修订落定/修改清单/门禁） | `ibd-doc-review` 的 revisions.md | 🔗 外部依赖 |
| 校验门禁（批注 docx+pdf / 修订稿） | `ibd-doc-review` 的 check_annotations.py / check_revisions.py | 🔗 外部依赖 |
| 问题清单模板（含 rev 字段示例） | [issues.example.json](scripts/issues.example.json) | 📦 本包 |
| 入口校验器（issues 结构早拦：CLI 独立跑 + 三脚本注入前自动校验） | [validate_issues.py](scripts/validate_issues.py) | 📦 本包 |
| 总览 Word 转换器（总览 md → docx，双格式交付） | [overview_to_docx.py](scripts/overview_to_docx.py) | 📦 本包 |
| 批注注入脚本（docx / pdf） | [annotate_docx.py](scripts/annotate_docx.py) / [annotate_pdf.py](scripts/annotate_pdf.py) | 📦 本包 |
| 修订稿生成脚本（docx，三 mode） | [revise_docx.py](scripts/revise_docx.py) | 📦 本包 |
| 后处理：补插丢失的批注 range（同段多批注冲突） | [fix_missing_ranges.py](scripts/fix_missing_ranges.py) | 📦 本包 |
| **步骤详规四册**（步骤 1 清单 schema／步骤 2 批注·修订／步骤 3·4 交付与门禁） | [issues-schema.md](references/issues-schema.md) · [annotate-runbook.md](references/annotate-runbook.md) · [revise-runbook.md](references/revise-runbook.md) · [delivery-and-gates.md](references/delivery-and-gates.md) | 📦 本包 |
| **非流程详规**（定位／边界与协作／依赖与工具／维护／踩坑分布） | [ops-notes.md](references/ops-notes.md) | 📦 本包 |
| 最小复现示例（三个示例含期望输出） | [examples.md](references/examples.md) | 📦 本包 |

> 🔗 外部依赖 = `ibd-doc-review` skill 中的资源（规范单一事实源 + 校验门禁），**不随本包分发**，须按 GitHub 发布渠道（Kianchales/ibd-skills 集合仓库）自行安装；📦 本包 = 随本技能安装自带。

## 依赖与工具

**判据**：Python 3 ＋ `python-docx`、`lxml`（docx 链路）／`pymupdf`（pdf 链路）按载体按需装；**外部依赖 `ibd-doc-review ≥ 0.19.0`**（规范单一事实源 ＋ 校验门禁；**下限登记 → `ibd-doc-review/references/interface.md` §6**）**不随包携带**，断链按自助指引从集合仓补齐——本 skill 单跑注入不受影响，仅门禁不可用。详表与断链自助见 [ops-notes.md](references/ops-notes.md) §依赖与工具。

## 边界与协作

**判据**：批注链路只加批注不改原文（修订链路只改 anchor 区间）；复杂 run／骑跨超链接·页眉页脚 → 记「未锚定」或「待人工」不硬撑；格式规范以 `ibd-doc-review` 的 annotations.md／revisions.md 为唯一依据；上游开放（清单可来自任何审查流程）。原文四条见 [ops-notes.md](references/ops-notes.md) §边界与协作。

## 踩坑与要点

**高频三条**（分布索引见 [ops-notes.md](references/ops-notes.md) §踩坑全文分布）：

- **同段多批注互相清除 range**（comments.xml 有批注、document.xml 丢 range）→ 补跑 `fix_missing_ranges.py` 后重跑门禁；**门禁只校验 cs/ce/ref 对数**，顺序颠倒曾静默放行
- **表格型文档锚点选唯一数值**（表标题／合并单元格常含多 run → MISS）：定锚前先做命中计数，**取命中数 = 1 的数值串**
- **修订删除文本用 `w:delText` 而非 `w:t`**，且须开 settings `w:trackRevisions`（元素名不是 trackChanges）

> 其余八条（pymupdf 页对象须持有引用／跨 run 锚定／批注内禁空行段／编号一次性分配／复杂 run 为兜底／ins-del 同 id 成对 author 归责／新文本 run 继承 rPr／多锚点倒序）按主题落在 [annotate-runbook.md](references/annotate-runbook.md) 与 [revise-runbook.md](references/revise-runbook.md)；**踩坑全文分布索引**见 [ops-notes.md](references/ops-notes.md) §踩坑全文分布。

## 维护

版本变更记录见 [CHANGELOG.md](CHANGELOG.md)；格式规则变更只改 `ibd-doc-review` 的 annotations.md 与 revisions.md；自测 `scripts/tests/test_fix_missing_ranges.py`（8 项）等维护细则见 [ops-notes.md](references/ops-notes.md) §维护。

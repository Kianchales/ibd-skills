---
name: ibd-doc-review
slug: ibd-doc-review
displayName: IBD 投行格式复核
summary: A 股投行文档格式复核：样式规范化（招股书/反馈回复排版）+ 格式核对 + 章节复核交付约定（批注版＋复核报告 Excel），只读核对不改文件。
description: >
  A 股投行文档的格式处理与章节复核规范，三类能力：
  1. 样式应用：对 Word 套用招股书版（000-009）或反馈回复版（0011+001+000-009）样式；
     样式源＝包内模板（assets/templates/），换模板即定制输出；可选 officecli 渲染层缺陷扫描
     与 OpenXML 架构校验。
  2. 格式核对（只读）：标题序号连续性、日期写法、标点全半角与用法、释义简称、表格规范等
     12 项，输出按严重程度分级的问题清单（位置/原文/问题/建议）。
  3. 章节复核交付规范与门禁：检查项声明（先声明查什么、不查什么）；交付三形态（批注版/定稿/修订稿）；
     深度三档 L1/L2/L3；产物只读校验门禁（check_annotations.py / check_revisions.py）；
     工作区目录结构（单文件/多文件两档、基准识别、参考资料四类）。
  本技能不修改文档内容；批注注入与修订稿生成归 ibd-doc-annotate。
  触发词：「按招股书样式」「招股书排版」「按反馈回复样式」「问询回复格式」「核对格式」「格式自查」
  「校验批注」「校验修订」「检查项声明」「工作区怎么建」
  「复核这份文件」「全套复核」「全文复核」「核一遍」「过一遍这份稿子」「文档质检」
version: 0.81.0
agent_created: true
---
# ibd-doc-review（IBD 投行格式复核）

管投行 Word 文档格式的。三件事：套招股书／反馈回复标准样式（模板可改）、过一遍查格式问题（序号、日期、金额、标点、简称、表格）、定章节复核的交付规范与门禁。**出清单不碰文件**。

## 何时使用

用户要求给 Word 应用／修改排版，或要求复核／校验产物时触发：

| 场景 | 触发词示例 |
|---|---|
| 招股书样式（含报告/尽调） | 「按招股书样式」「招股书格式」「套用 000-009 样式」 |
| 反馈回复样式 | 「按反馈回复样式」「问询回复格式」「落实函格式」 |
| 通用排版／局部调整 | 「排版规范」「字体字号统一」「标题改成黑体」「表格改三线表」 |
| 格式核对（只读） | 「核对一下格式」「格式自查」「检查序号/金额/日期/标点」「文件质量核查」 |
| 批注／修订校验（只读） | 「校验批注」「修订稿校验」「修订结构对不对」 |
| 章节复核委托 | 「逐段复核」「查哪些项」「复核交付形态」「批注版还是修订稿」 |

> 若任务含「写反馈回复内容」→ 内容写作归内容层（默认上游 `ibd-doc-write`），本 skill 只管样式落地与复核规范，两者可串联。

## 一、复核铁律

> 🔴 **「复核」＝对指定范围全部对象逐项全量核，禁抽检／抽样／默认跳过**。定义·范围·五条禁令·输出要求·自检标准 → [fuhe-charter.md](references/fuhe-charter.md)，**无需用户追加任何提示词**。
> 🔴 **只有一个入口**：`review_file.py --input <文件> --prepare` —— 看到「复核」二字第一步就是它；**禁止先自建脚本抽取、禁止先通读全文**；读了说明页 ≠ 执行了流程，无 `_run.json` 的报告生成器直接拒绝出报告。
> 🔴 **只改格式、不改内容**：只做 pStyle／字体字号／对齐／缩进／间距／边框，**不得增删改移任何文字**（含表内、标点、空格）。套用后 `check_styles.py --verify-content <原文件>` 逐字校验，不一致即 FAIL。

**四条纪律**：① 未核即声明（跳过项逐项点名）② 声明 ⟷ 报告头首尾一致，中途增减重新声明 ③ 档位只是预设，用户点名加减项照办 ④ 覆盖默认全文，抽核/圈定只能用户发起。

## 二、标准路径

```
① --prepare  → 定分母＋切批＋提取全文/表＋格式核对＋声明单＋指纹
② --begin    → 逐批取活（含标题段），读 →
③ --commit N → 登记本批发现**＋节级六问回执**（缺任一即拒收）
④ --finish   → 按文档序合并 → 清单 → 报告
⑤ check_runlog --file <文件> → 全绿才算完成
```

| 前置 | 判据 |
|---|---|
| **读取前置** | 读源 docx 前先探 `w:ins`／`w:del`／`word/comments.xml`——命中即按「接受全部修订＋剔除全部批注」取终稿并标注；**禁对源文件写操作** |
| **落位前置** | 核 1 份 ⇒ 源同级 `<文件名>_复核/`；核 ≥2 份 ⇒ 五层作业区（`new_workspace.py`）；**同一文档多版本算 1 个对象** |

> **禁词红线** [banned-terms.json](references/banned-terms.json)（按 `--scenario` 装载，改 json 即生效）｜**敏感词与地理** [sensitive-terms.json](references/sensitive-terms.json)（格式核对时装载）。
> 链路细则 → [pipeline.md](references/pipeline.md)｜声明单与查什么 → [check-scope.md](references/check-scope.md)｜读取口径 → [read-docx.md](references/read-docx.md)、`extract_final_text.py`｜落位 → [workspace-layout.md](references/workspace-layout.md)

## 三、路由

| 场景 | 去哪 |
|---|---|
| **A–H** 套样式／新建／局部改／样式校验／格式核对／批注校验／修订校验／交付核验 | [workflow.md](references/workflow.md)（决策树＋调用顺序＋降级） |
| **I** 圈定范围复核 | 先出声明单；格式→本 skill｜内容→`ibd-quality-gates`｜财务→`ibd-finance-review`｜法律→`ibd-legal-review` |
| **J** 惯例对照 | [convention-compare.md](references/convention-compare.md) |
| **K** 跨轮收敛 | `round_diff.py`＋[delivery.md](references/delivery.md) §七之二 |

**执行主线 S1–S7**（识别→加载模板→路由→样式映射→序号表格→门禁→三件套）→ [workflow.md](references/workflow.md) §一；**样式铁律全文（7 条）** → 同册 §零·二；**格式核对 12 项矩阵** → 同册 §二；**批注/修订校验明细** → 同册 §三。

## 资源索引

模板在 `assets/templates/`（**改模板＝定制输出**）：`报告模板.docx`（招股书/报告）｜`反馈回复样式.docx`（问询回复）｜`表格模板.docx`（三线表 a6／单位 a5／备注 a4）。样式 ID 全表、字体字号与缩进间距 → [style-map.md](references/style-map.md)；禁词红线 [banned-terms.json](references/banned-terms.json)（改 json 即生效）｜敏感词与地理 [sensitive-terms.json](references/sensitive-terms.json)。

## 边界与协作

- **交付前一律先跑 `deliver_gate.py`**：十项基础一次跑完、只输出结论行；复核产物加 `--annotated`／`--revised`，复核场景**须配 `--baseline`**（源件同为 FAIL 的项标〔源件遗留〕不计入）。不用分散的小命令替代。
- **SKIP 必须向用户点名**（officecli 未装等）——静默跳过与静默失败同罪。
- **顺序铁律**：内容质量门禁在前、格式落地在后；**文字规范先于套样式**（文字返工会导致样式重做）。
- 批注注入归 `ibd-doc-annotate`，本 skill 只定规范与门禁；内容质量问题归 `ibd-quality-gates`。
- 完整协作图、接缝与实测坑 → [collaboration.md](references/collaboration.md)｜工具层级与踩坑 → [toolchain.md](references/toolchain.md)

## 依赖与工具

> **完全独立**——不依赖多角色团队、不依赖特定知识库。

**必须**：Word 处理工具其一（`minimax-docx`〔🟨市场〕／`tencent-docx`〔🟦内置〕）＋ 随包脚本；**推荐**：`tencent-local-office-edit`、模板 docx；**可选**：金融终端、全文检索、知识库。层级表与缺失后果 → [toolchain.md](references/toolchain.md) §一。

### 脚本与册

**脚本**：`review_file`（入口）｜`docxio`／`extract_final_text`（读取）｜`check_content`／`check_styles`／`check_cq`／`check_scope_decl`／`check_runlog`／`deliver_gate`／`validate_schema`（核对）｜`plan_review`／`subquestion_map`／`round_diff`／`new_workspace`（规划）｜`check_annotations`／`check_revisions`（产物校验）｜`runlog`／`content_common`／`content_text`／`content_table`（辅助）

**册**：fuhe-charter｜pipeline｜check-scope｜chunked-review｜split-rules｜workflow｜delivery｜annotations｜revisions｜style-map｜collaboration｜workspace-layout｜convention-compare｜toolchain｜interface｜examples｜read-docx｜maintenance｜rules（均在 references/，另有 `problems.schema.json`）

## 维护

> 规则变更同步 6 环、报告形态同源、升版三道核对 → [maintenance.md](references/maintenance.md)——**漏一环，该规则即形同不存在**。
> 版本历史：主账 CHANGELOG.md；0.39.x 及更早 → [changelog-archive.md](references/changelog-archive.md)。
> **改脚本后必跑**：`scripts/tests/run_tests.py`（快测）→ 提交前 `--all`＋`golden_run.py`（真实文档回归，样本由 `IBD_GOLDEN_DIR` 指定，缺席 SKIP）。

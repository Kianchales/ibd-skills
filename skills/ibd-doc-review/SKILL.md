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
version: 0.62.0
agent_created: true
---

# ibd-doc-review（IBD 投行格式复核）

管投行 Word 文档格式的。三件事：套招股书／反馈回复标准样式（模板可改）、过一遍查格式问题（序号、日期、金额、标点、简称、表格）、定章节复核的交付规范与门禁。出清单不碰文件。

## 何时使用

用户要求给 Word 应用／修改以下任一排版要求，或要求复核／校验产物时，触发：

| 场景 | 触发词示例 |
|---|---|
| 招股书样式（含报告/尽调） | 「按招股书样式」「招股书格式」「套用 000-009 样式」 |
| 反馈回复样式 | 「按反馈回复样式」「问询回复格式」「落实函格式」 |
| 通用排版要求 | 「排版规范」「按投行规范排版」「字体字号统一」「文档格式统一」 |
| 局部样式调整 | 「标题改成黑体」「正文首行缩进」「表格改成三线表」「单位行右对齐」 |
| 格式核对（只读） | 「核对一下格式」「格式自查」「检查序号/金额/日期/标点」「文件质量核查」 |
| 批注／修订产物校验（只读） | 「批注格式」「校验批注」「修订稿校验」「校验修订」「修订结构对不对」 |
| 章节复核委托 | 「研究下 XX 节」「逐段复核」「查哪些项」「复核交付形态」「批注版还是修订稿」 |

> 若任务含「写反馈回复内容」→ 内容写作归内容层（默认上游 `ibd-doc-write`），本 skill 只管生成后的样式落地与复核规范，两者可串联。
> **执行细则（S1-S7／格式核对矩阵／复核交付模式／命令全表）→ [workflow.md](references/workflow.md)**；典型用例 → [examples.md](references/examples.md)。

## 使用流程

> 本节只留「步骤名 ＋ 一句话判据 ＋ 册指针」。
> **读取前置**：读源 docx 取文本前先探 `w:ins`／`w:del`／`word/comments.xml`——命中即按「接受全部修订＋剔除全部批注」取终稿并标注；**禁对源文件写操作**。判据 → `docs/CONVENTIONS.md` §一；细则 → [read-docx.md](references/read-docx.md)，脚本 [extract_final_text.py](scripts/extract_final_text.py)。
> **落位前置**：产物放哪先定——核 1 份 ⇒ 源文件同级 `<文件名>_复核/`；核 ≥2 个不同文档 ⇒ 五层作业区（`new_workspace.py` 建）。目录树／基准识别／参考资料四类 → [workspace-layout.md](references/workspace-layout.md)。**同一文档多版本算 1 个对象**。

### 0. 进门第一档：检查项声明（先声明，再动手）

| 事项 | 一句话判据 | 册指针 |
|---|---|---|
| **先声明查什么** | 任何复核委托的**第一个动作**——首次委托先出「动手前三问」小表（范围／形态／档位，各附推荐），确认后逐项列「查／不查 ＋ 为什么 ＋ S 专项 ＋ 交付前跑 F 域」；同文档沿用，换文档重问 | [check-scope.md](references/check-scope.md)；动作规范 → [delivery.md](references/delivery.md) §零 |
| **覆盖方式写清** | **先定分母**（总段／正文段／表数）再切批（正文 300–400 段＋表 40–50 张／批）；**拆不拆、按哪条轴 → [split-rules.md](references/split-rules.md)** | [chunked-review.md](references/chunked-review.md) §零 |
| 再定交付形态 | 批注版／文本定稿／修订稿（三选一，带项目级记忆） | delivery.md §五 |
| 深度档位作预设 | L1/L2/L3 只预填声明单，不是另一套独立选择；**分档轴＝性质**：L2 装机器能判的（格式/数值/台账），L3 装只有人能判的 | check-scope.md §七 ＋ delivery.md §七 |

> **四条纪律**：① 未核即声明（跳过项逐项点名）② 声明 ⟷ 交付报告头**首尾一致**，中途增减重新声明 ③ 档位只是预设，用户点名加减项一律照办 ④ **覆盖默认全文**，抽核/圈定只能用户发起（AI 自缩＝违规），抽核须写明抽了哪几节。

### 1. 场景识别与工具路由

| 场景 | 判据 | 工具 |
|---|---|---|
| **A–H** 套样式／新建／局部改／样式校验／格式核对／批注校验／修订校验／交付核验 | 按输入形态与产物类型分流 | 见 [workflow.md](references/workflow.md) §零·一（决策树 ＋ 调用顺序 ＋ 降级协议） |
| **I** 圈定范围的复核 | 用户**显式圈定**（「只核对X」「X 过一遍」） | 先进门出声明单；域路由：格式→本 skill；内容→`ibd-quality-gates`；财务→`ibd-finance-review`；法律→`ibd-legal-review` |
| **J** 惯例对照（只对照不定性） | 情形无明文／属灰色地带 | 四步法 → [convention-compare.md](references/convention-compare.md)；D 域执行 → `ibd-legal-review` |
| **K** 跨轮收敛（第2轮起） | 上轮 vs 本轮清单五态台账 | `round_diff.py`（→ delivery.md §七之二） |

### 2. 执行流程（S1-S7）

> 七步主线，任一门禁不符 → 返回 S4/S5 修正后重跑，不交付。详规 → [workflow.md](references/workflow.md) §一。

| 步 | 一句话判据 |
|---|---|
| **S1** 识别样式场景 | 含「问题X.」或【发行人说明】→ 反馈回复版；其余正式文档 → 招股书版 |
| **S2** 加载样式资产 | 模板 docx 存在 ＋ 样式体系与场景匹配（[style-map.md](references/style-map.md)） |
| **S3** 工具路由 | 场景 → 工具一一对应；层级与降级见 [toolchain.md](references/toolchain.md) §一 |
| **S4** 样式映射（核心） | 内容段落逐个落 pStyle，按 style-map.md |
| **S5** 序号与表格规则 | 九级链无跳号/重号/倒退；三线表按 [rules.md](references/rules.md) §一／§二 |
| **S6** 校验门禁 | `deliver_gate.py` 零 FAIL（SKIP 须向用户点名）；禁词红线源 ＝ [banned-terms.json](references/banned-terms.json)（按场景） |
| **S7** 三件套交付 | 修订稿 ＋ 格式问题清单 ＋ 修改统计齐备；契约见 [interface.md](references/interface.md) |

### 3. 样式应用铁律（红线）

0. **只改格式、严禁修改原文内容（最高优先级）**：只做样式应用（pStyle／字体／字号／对齐／缩进／间距／边框），**不得增删改移任何文字**（含表内文字、标点、空格、数字、单位）。套用后须 `check_styles.py --verify-content <原文件>` 逐字校验，不一致即 FAIL 重做。内容修改属内容层，本 skill 不做。
1. **模板先行**——动笔前确认 `assets/templates/` 模板存在，优先以模板为基底。
2. **pStyle 优先于手写格式**——能应用命名样式（000-009／0011／001）就不硬编码字体字号。
3. **序号段落判定走双维度算法**（段落长短 ＋ 上下文分段）→ [rules.md](references/rules.md) §一；可 `check_styles.py --check-numbering` 辅助。
4. **反馈回复合规展示**——监管问题原文 001（黑体）、回复正文 000（宋体），黑宋对照即合规展示，不得混用。
5. **不覆盖用户手动格式**——apply-template 前先与用户确认是否保留。
6. **段落间禁止空行/空段落**——间距一律靠样式 spacing；空段落会命中裸段落检查并叠加间距。

> 铁律全文（判据细节与辅助命令）→ [workflow.md](references/workflow.md) §零·二。

### 4. 格式核对模式（check_content.py，只读不改文件）

> - **只读**，适用任意投行 Word；`check_content.py --input <docx>`（模块 content_common／content_text／content_table），出 `<input>_格式核对报告.md`。
> - **两组**：文字 **8** 项 ＋ 表格 **4** 项，按 HIGH/MEDIUM/LOW 分级；**明细矩阵 → [workflow.md](references/workflow.md) §二**（项名与严重度判据以该矩阵为准，本页不复制）。
> - **边界**：本模式查格式层自洽；**数值自洽**与内容质量溯源归 `ibd-quality-gates`；敏感词与地理清单 → [sensitive-terms.json](references/sensitive-terms.json)。

### 5. 批注与修订复核交付模式（规范 + 只读校验）

> - **职责**：本 skill 定规范 ＋ 门禁（只读）；**注入执行 = `ibd-doc-annotate`**（`annotate_docx.py` / `revise_docx.py --mode`）——两 skill 以本 skill 规范为合规依据。
> - **门禁一条命令**：`deliver_gate.py --docx <件> --annotated [--expect-annotated N]` / `--revised [--expect-revised N]`，任一 FAIL → 退回重注入，不交付。
> - **规范单一事实源**：批注 [annotations.md](references/annotations.md)｜修订 [revisions.md](references/revisions.md)｜交付口径 [delivery.md](references/delivery.md)（含报告 Excel 形态与生成器 §八之二，本 skill 不产出）｜schema [problems.schema.json](references/problems.schema.json)（`validate_schema.py` 校验）。
> - 校验项明细（含加粗按语义判定的实测坑）→ [workflow.md](references/workflow.md) §三。

## 资源索引

### 样式资产（先加载，禁止裸写）

> 模板在 `assets/templates/`（即样式源）：**改模板 = 定制输出样式**；三个模板随包分发。

| 模板文件 | 适用文档 | 关键样式 ID |
|---|---|---|
| `报告模板.docx` | 招股书章节／报告／备忘录／尽调报告 | 000 正文、001 章标题、002-007 二至七级、008 单位、009 备注 |
| `反馈回复样式.docx` | 审核问询回复／反馈回复／落实函回复 | 0011 问题编号、001 监管问题原文、000 正文、002-009 明细 |
| `表格模板.docx` | 以上全部文档的表格 | 三线表 a6／表前单位 a5／表后备注 a4 |

**细则指针**（按需读，本页不复制；各步判据处的指针为准，本段是**全集索引**）：
- **动手前先翻**：[workflow.md](references/workflow.md)（S1-S7 · 格式核对 · 复核交付 · 命令全表）
- 样式与读取：[style-map.md](references/style-map.md)（字体字号·对齐·缩进·间距·行距·大纲）｜[read-docx.md](references/read-docx.md)（含修订/批注的 Word 读取口径）
- 复核规范：[annotations.md](references/annotations.md)（批注）｜[revisions.md](references/revisions.md)（修订）｜[delivery.md](references/delivery.md)（交付）｜[workspace-layout.md](references/workspace-layout.md)（工作区结构）｜[check-scope.md](references/check-scope.md)（声明单·六问）｜[chunked-review.md](references/chunked-review.md)（分片）｜[split-rules.md](references/split-rules.md)（分拆判定）｜[convention-compare.md](references/convention-compare.md)（惯例对照）｜[interface.md](references/interface.md)（契约）｜[problems.schema.json](references/problems.schema.json)（清单 schema）｜执行器 = `ibd-doc-annotate`
- 工具与样例：[toolchain.md](references/toolchain.md)（层级与踩坑全文）｜[examples.md](references/examples.md)（典型用例）
- 清单 json：[banned-terms.json](references/banned-terms.json)（禁词红线·三档·按 `--scenario` 装载，改 json 即生效）｜[sensitive-terms.json](references/sensitive-terms.json)（敏感词与地理）

## 依赖与工具

> **本 skill 完全独立**——不依赖多角色团队、不依赖特定知识库。

| 维度 | 说明 |
|---|---|
| 🔴 **必须** | 任一 Word 处理工具（`minimax-docx`〔🟨市场〕或 `tencent-docx`〔🟦内置〕至少一）＋ 随包脚本 `check_styles.py`／`check_content.py`／`check_annotations.py`／`check_revisions.py`／`deliver_gate.py`／`extract_final_text.py`／`plan_review.py`（分母·批次）／`subquestion_map.py`（对位）／`check_cq.py`（C-Q 勾稽）／`docxio.py`（docx 读取公共层）／`check_scope_decl.py`（声明单校验）／`review_file.py`（单文件编排·批次内部化）／`check_runlog.py`（流程合规判定）——docx 侧零依赖；`--pdf` 需 pymupdf（缺则提示） |
| 🟡 **推荐** | `tencent-local-office-edit`〔🟦内置〕（局部微调体验最佳）；模板 docx（`assets/templates/`，可替换） |
| 🟢 **可选** | 金融数据终端（仅交叉验证）；本地全文检索〔若已接入〕／知识库后端（检索同类范例）；`officecli`（渲染层缺陷扫描 ＋ OpenXML 架构校验，S6 补充门禁） |
| **运行模式** | 单用户直接使用；也可作为 `ibd-doc-write` 的格式层被串联调用 |

> 每个工具为什么是这个层级、缺了会怎样 → [toolchain.md](references/toolchain.md) §一。

## 边界与协作

- **默认上游 = `ibd-doc-write`**（内容层出草稿并声明样式场景）→ 交本 skill 套样式 ＋ 校验；**上游开放**——人工撰写、其他 AI 流程、外部导入的 Word 均可调用。
- **下游调用点**：`ibd-doc-write` 已把 `deliver_gate.py` 嵌进流程（`--md` 在套样式前做文字预检、`--docx` 作交付前综合核验）⇒ **本脚本改动直接影响写作链**，升版须核 [interface.md](references/interface.md) §7 版本下限。
- **顺序铁律：内容质量门禁在前、格式落地在后**——write 草稿先过 `ibd-quality-gates`，内容定稿再套样式；**文字规范必须先于套样式**（文字层返工会导致样式重做），理由与实测 → workflow.md 附录「两条时序铁律」。
- **交付前一律先跑 `deliver_gate.py`**：**十项基础**一次跑完、只输出结论行；复核产物加 `--annotated`／`--revised`（各 +2 项）、`--officecli`（+1 项物理扫描）；**复核场景须配 `--baseline`**（源件同为 FAIL 的项标〔源件遗留〕不计入结论）。不用分散的多条核验命令替代。
- **输出分层**：三个核验脚本统一「指标行进上下文、明细行落盘」——判据是「明细有没有可定向读的落盘位置」，落盘后原文不得继续占用上下文（ENGINEERING §1 P10＋§4.4）。
- **SKIP 须向用户点名**：`deliver_gate.py` 有 SKIP 项（officecli 未装、pymupdf 缺失等）时，回复须注明「本次 N 项 SKIP 未执行（原因）」——静默跳过与静默失败同罪。
- **批注版链路**：复核产出问题清单 → `ibd-doc-annotate` 注入（依据 annotations.md）→ 本 skill `check_annotations.py` 门禁 → 交付（批注版＋复核报告 Excel；总览 md 不交付）。
- **内容质量归 `ibd-quality-gates`**（数字五要素／反模式／来源可溯）；本 skill 只改格式不改内容（铁律 0）。

## 踩坑与要点

- **⚠️ apply-template 只做「组件级替换」、不做段落 pStyle 映射**：套用后 pStyle 分布仍是 `(裸):N`，易误判"套样式失败"；段落级映射须另做一步。验收：body 级 pStyle 引用数从 0 变非 0、必备样式齐备、残留直接格式归零。
- 半全角标点须在**套样式之前**先过 `check_content.py --checks text`；`--revise` 三坑（`w:trackRevisions` 而非 `w:trackChanges`／pPrChange 快照不含 `w:rPr`／气泡缺失须用 Word 原生文档做对照组）→ [toolchain.md](references/toolchain.md) §二。

## 维护

> 规则变更同步 6 环、报告形态同源对、升版三道核对 → [maintenance.md](references/maintenance.md)——**漏一环，该规则即形同不存在**。
> 版本历史：主账 CHANGELOG.md（0.40.0 起）；0.39.x 及更早归 [changelog-archive.md](references/changelog-archive.md)。
> **改脚本后必跑**：`python scripts/tests/run_tests.py`（快测，约 5 秒／不起子进程）→ 提交前 `--all`（全量，约 70 秒）＋ `python scripts/tests/golden_run.py`（真实文档回归，样本自备于 `IBD_GOLDEN_DIR` 指定的目录，缺席 SKIP 不阻断）。

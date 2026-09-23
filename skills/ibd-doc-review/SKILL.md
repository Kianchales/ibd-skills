---
name: ibd-doc-review
slug: ibd-doc-review
displayName: IBD 投行格式复核
summary: A 股投行文档格式复核：样式规范化（招股书/反馈回复排版）+ 格式核对（序号/日期/标点/简称/表格）+ 章节复核交付约定（批注版/总览双轨），只读核对不改文件。
description: >
  本技能用于 A 股投行文档的格式处理，提供两类能力：
  1. 样式应用：对 Word 文档套用招股书版或反馈回复版样式体系，适用于招股书、
     反馈回复、报告、备忘录、尽调报告等正式文档；样式以模板文件为源
     （assets/templates/），可通过修改模板自定义输出样式。
  2. 格式核对：对文档逐项核对格式问题，覆盖标题序号连续性、日期写法统一、
     标点全半角、释义简称、表格规范等 10 个核对项，输出按严重程度
     分级的问题清单（含位置、原文、问题与修改建议）。
  3. 渲染层物理缺陷扫描 + 架构校验（可选，officecli 驱动）：文本溢出、首行
     缩进缺失、公式错误等渲染问题，以及 OpenXML 架构合法性校验。
  4. 批注与修订复核规范与校验：复核结论落到原文（批注 / 修订稿）的格式单一
     事实源（批注 4 行紧凑结构/编号/类型词表/字体/锚点；修订三模式/rev 字段/
     修订落定）+ 产物只读校验门禁（[check_annotations.py](scripts/check_annotations.py) 批注 / [check_revisions.py](scripts/check_revisions.py) 修订稿）。
  5. 章节复核交付约定：章节复核交付的默认形态（批注版原文 + 精简总览双轨）、
     执行链路（复核清单 → 注入 → 门禁 → 交付）、批注/修订职权划分、
     触发语路由、批注全量覆盖纪律——单一事实源见
     [delivery.md](references/delivery.md)。
  本技能不修改文档内容。
  触发词：「按招股书样式」「招股书排版」「按反馈回复样式」「问询回复格式」
  「落实函格式」「套模板样式」「核对格式」「格式自查」「检查序号金额日期标点」
  「批注格式」「校验批注」「批注规范」「修订稿校验」「校验修订」「检查修订稿」
  「修订结构对不对」「章节复核怎么交付」「复核交付形态」「批注版还是修订稿」
  「研究下XX节」「帮我看看这段」（批注/修订的注入执行归 ibd-doc-annotate——本 skill 是规范与校验侧）
version: 0.23.0
agent_created: true
---

# ibd-doc-review（IBD 投行格式复核）

管投行 Word 文档格式的。两件事：给文档套上招股书或反馈回复的标准样式（模板可改），以及把文档过一遍查格式问题（序号、日期、金额、标点、简称、表格这些），出清单不碰文件。

## 何时使用

用户要求给 Word 应用 / 修改以下任一排版要求时，无条件触发：

| 场景 | 触发词示例 |
|------|-----------|
| 招股书样式（含报告/备忘录/尽调等正式文档） | 「按招股书样式」「招股书格式」「招股书排版」「招股书章节样式」「按招股书章节格式写」「把这篇改成招股书格式」「这篇按招股书排一下」「套用 000-009 样式」「套 000-009」「报告模板样式」「按报告模板」「套模板样式」「应用报告样式」 |
| 反馈回复样式 | 「按反馈回复样式」「按问询回复格式」「反馈回复排版」「反馈回复排版规范」「问询函回复格式」「落实函格式」「审核问询回复格式」「按问询函格式排版」 |
| 通用排版要求 | 「把这个 Word 改成 XXX 格式」「排版规范」「按投行规范排版」「字体字号统一」「排版规范一点」「文档格式统一」 |
| 局部样式调整 | 「标题改成黑体」「正文首行缩进」「表格改成三线表」「单位行右对齐」 |
| 格式核对（只读，不改文件） | 「核对一下格式」「格式自查」「投行格式核对」「检查序号/金额/日期/标点」「文件质量核查」 |
| 批注复核产物校验（只读） | 「批注格式」「校验批注」「批注结构对不对」「修订稿校验」「检查修订稿」 |
| 修订稿产物校验（只读） | 「修订稿校验」「校验修订」「检查修订稿」「修订结构对不对」「看修订稿格式」 |

> 若任务同时含「写反馈回复内容」→ 内容写作属内容层任务（默认上游 = `ibd-doc-write`，见「上游接口与边界」）；本 skill 只负责生成后的样式落地；两者可串联（先写内容、再套样式）。
> **执行细则（S1-S7 步骤 / 格式核对矩阵 / 复核交付模式 / 命令全表）→ [workflow.md](references/workflow.md)**（本文件只留决策树与铁律）。
> 典型用例（触发→执行→产出 全链路示例）见 [examples.md](references/examples.md)。

## 使用流程

> **本节读法**：只留「**步骤名 ＋ 一句话判据 ＋ 册指针**」；**执行细则 → [workflow.md](references/workflow.md)**（§零·一 进门决策树 · §零·二 样式应用铁律 · §一 S1-S7 · §二 格式核对 · §三 复核交付 · 附录「脚本 × 场景」命令全表）。

### 1. 场景识别与工具路由（导航）

| 场景 | 一句话判据 | 工具 |
|---|---|---|
| **场景A** 已有 docx 整套套样式 | source=用户文件 / template=模板 / output=新文件 | `minimax-docx apply-template` |
| **场景B** 新建 docx | 从模板基底填充 | `tencent-docx`（降级 `minimax-docx create`） |
| **场景C** 局部调整 | 单段 / 单表改样式 | `tencent-local-office-edit`（唯一编辑中枢） |
| **场景D** 生成后校验样式 | pStyle 分布 ＋ 必备样式是否应用 | `check_styles.py` |
| **场景E** 格式核对（只读不改文件） | 文字 text 组 ＋ 表格 table 组 | `check_content.py` |
| **场景F** 批注产物校验（只读） | 四件套 / 4 段无空行 / 编号唯一 | `check_annotations.py`（≡ `deliver_gate.py --annotated`） |
| **场景G** 修订稿产物校验（只读） | ins==del 对 / author·id 成对 / 落定证明 | `check_revisions.py`（≡ `deliver_gate.py --revised`） |
| **场景H** 交付前综合核验 | 基础九项一次跑完，三态 PASS/FAIL/SKIP | `deliver_gate.py` |

> 决策树的判定细节、工具调用顺序（五步）、失败降级协议（五类降级场景）→ [workflow.md](references/workflow.md) §零·一。

### 2. 执行流程（S1-S7）

| 步 | 一句话判据 | 详规 |
|---|---|---|
| **S1** 识别样式场景 | 含「问题X.」或【发行人说明】→ 反馈回复版；其余正式文档 → 招股书版 | workflow.md §一 |
| **S2** 加载样式资产 | 模板 docx 存在 ＋ 样式体系与场景匹配 | workflow.md §一（样式表 [style-map.md](references/style-map.md)） |
| **S3** 工具路由 | 场景 → 工具一一对应；层级与缺失降级见 [toolchain.md](references/toolchain.md) §一 | workflow.md §零·一 ＋ §一 |
| **S4** 样式映射（核心） | 内容段落逐个落 pStyle，按 [style-map.md](references/style-map.md) | workflow.md §一 |
| **S5** 序号与表格规则 | 九级链无跳号/重号/倒退；三线表按 [rules.md](references/rules.md) §一／§二 | workflow.md §一 |
| **S6** 校验门禁 | `deliver_gate.py` 零 FAIL（SKIP 须向用户点名） | workflow.md §一 ＋ 附录命令表 |
| **S7** 三件套交付 | 修订稿 ＋ 格式问题清单 ＋ 修改统计齐备；对外契约见 [interface.md](references/interface.md) | workflow.md §一 |

> 七步主线：S1 识别场景 → S2 加载样式资产 → S3 工具路由 → S4 样式映射 → S5 序号/表格规则 → S6 校验门禁 → S7 交付。**任一门禁不符 → 返回 S4/S5 修正后重跑，不交付。**

### 3. 样式应用铁律（红线）

0. **只改格式、严禁修改原文内容（最高优先级）**：本 skill 只做样式应用（pStyle/字体/字号/对齐/缩进/间距/边框），**不得增、删、改、移任何文字内容**（含表格内文字、标点、空格、数字、单位）。套用样式后必须用 `check_styles.py --verify-content <原文件>` 校验内容完整性——文本与原文逐字不一致即 FAIL，打回重做，不交付。内容修改（如补数据、改措辞）属内容层任务，本 skill 一律不做。
1. **模板先行**——动笔前先确认 `assets/templates/` 模板存在，优先以模板为基底；**模板即样式源，替换模板即定制输出样式**。
2. **pStyle 优先于手写格式**——能应用命名样式（000-009/0011/001）就不硬编码字体字号。
3. **序号段落判定走双维度算法**（段落长短 ＋ 上下文分段）→ [rules.md](references/rules.md) 第一节；可 `check_styles.py --check-numbering` 辅助。
4. **反馈回复合规展示**——监管问题原文 001（黑体）、回复正文 000（宋体），黑宋对照本身即合规展示，不得混用。
5. **不覆盖用户手动格式**——apply-template 前先与用户确认是否保留。
6. **段落间禁止空行/空段落**——间距一律靠样式 spacing，空段落会命中裸段落检查并造成间距叠加。

> 铁律全文（含判据细节与辅助命令）→ [workflow.md](references/workflow.md) §零·二。

### 4. 格式核对模式（check_content.py，只读不改文件）

> - **只读审查**，适用任意投行 Word 文档（中性通用规则）；命令 `check_content.py --input <docx> [--checks text|table|geo,table_na]`，出 `<input>_格式核对报告.md`。
> - **两大组别**：文字类 text（序号连续性 / 用词规范 / 日期写法 / 多余空格·数字与英文前后空格·重复标点 / 释义简称 / 地理表述）+ 表格类 table（字号体系 / 数字右对齐 / 空单元格 / NA 标记统一），按 HIGH/MEDIUM/LOW 分级。
> - **边界**：本模式查格式层自洽；**数值自洽**（勾稽/前后一致）与**内容质量溯源**归 `ibd-quality-gates`；敏感词/地理清单见 [sensitive-terms.json](references/sensitive-terms.json)；**问题清单的机器可执行 schema** 见 [problems.schema.json](references/problems.schema.json)。
> - 完整细则（命令块 · 10 项核对矩阵 · 边界说明）→ [workflow.md](references/workflow.md) 第二节。

### 5. 批注与修订复核交付模式（规范 + 只读校验）

> - **职责**：本 skill 定规范 + 门禁（只读）；**批注注入 / 修订稿生成 = `ibd-doc-annotate`**（同一份复核问题清单 → `annotate_docx.py` / `revise_docx.py --mode`）——两 skill 交接以本 skill 规范为合规依据。
> - **门禁一条命令**：`deliver_gate.py --docx <件> --annotated [--expect-annotated N]` / `--revised [--expect-revised N]`，**任一 FAIL → 退回 `ibd-doc-annotate` 重注入，不交付**。
> - **规范单一事实源**：批注 → [annotations.md](references/annotations.md)；修订 → [revisions.md](references/revisions.md)；交付口径 → [delivery.md](references/delivery.md)；**问题清单 schema** → [problems.schema.json](references/problems.schema.json)（校验入口 `validate_schema.py`）；**对外接口契约** → [interface.md](references/interface.md)。
> - **⚠️ 加粗判定须按语义**：`<w:b w:val="0">` 是**显式取消加粗**，只判 `<w:b>` 元素存在会把合规批注误判 FAIL（实测 2026-09-11，两脚本均已修）。
> - 完整细则（门禁命令块 · 检查项清单 · 自测命令）→ [workflow.md](references/workflow.md) 第三节。

## 资源索引

### 样式资产（先加载，禁止裸写）

> 模板文件路径（**skill 自带，即样式源**）：`assets/templates/`。**改模板 = 定制输出样式**；三个模板 docx 随分发包一起分发（zip 内含），分发版与本地版资产一致。样式定义以包内模板 + style-map.md/rules.md 为准。

| 模板文件 | 适用文档 | 样式体系 | 关键样式 ID |
|---------|---------|---------|------------|
| `报告模板.docx` | 招股书章节 / 报告 / 备忘录 / 尽调报告等正式文档 | 招股书版 000-009 | 000 正文、001 一级标题、002-007 二级至七级标题、008 单位、009 备注 |
| `反馈回复样式.docx` | 审核问询回复 / 反馈回复 / 落实函回复 | 反馈回复版（000-009 + 0011/001） | 0011 一级标题（问题编号）、001 问题正文（监管问题黑体）、000 正文、002-009 明细层级 |
| `表格模板.docx` | 以上全部文档的表格 | 三线表 | 报告表格 a6、表格前单位 a5、表格后说明 a4 |

- **完整样式定义**（字体/字号/对齐/缩进/间距/行距/大纲级别）→ [style-map.md](references/style-map.md)
- **执行细则**（S1-S7 / 格式核对模式 / 批注与修订复核交付模式 / 「脚本 × 场景」命令全表）→ [workflow.md](references/workflow.md)——**动手做之前翻这一份**
- **批注复核规范**（交付形态双轨 / 4 行紧凑结构 / 编号体系 / 类型词表 / 字体 / 锚点 / 门禁）→ [annotations.md](references/annotations.md)；**修订稿交付规范**（三模式 / rev 字段 / 落定 / 修改清单 / 门禁）→ [revisions.md](references/revisions.md)；执行器 = `ibd-doc-annotate`
- **章节复核交付约定**（默认交付形态 / 执行链路 / 职权划分 / 触发语路由 / 批注纪律）→ [delivery.md](references/delivery.md)
- **对外接口契约**（交付口径 / 门禁 CLI / 问题清单 schema / 编号与词表 / 脚本入口 / 版本下限）→ [interface.md](references/interface.md)；机器可执行 schema = [problems.schema.json](references/problems.schema.json)（语义源 = interface.md §3 + annotations.md §4）
- **工具层级说明 + 踩坑全文** → [toolchain.md](references/toolchain.md)；**典型用例** → [examples.md](references/examples.md)；**敏感词/地理清单** → [sensitive-terms.json](references/sensitive-terms.json)
- **版本历史**：本包 CHANGELOG.md（当前代际 0.15.0 起）；0.1.0 – 0.14.1 共 24 个历史版本段已归档至 [changelog-archive.md](references/changelog-archive.md)

## 依赖与工具

> **本 skill 完全独立**——不依赖多角色团队、不依赖特定知识库，任何人可直接使用。

| 维度 | 说明 |
|---|---|
| 🔴 **必须** | 任一 Word 处理工具（`minimax-docx`〔🟨官方市场〕 或 `tencent-docx`〔🟦内置〕至少一，套样式/新建用）+ 内置脚本 `check_styles.py` / `check_content.py`〔含 `content_common.py` / `content_text.py` / `content_table.py` 三配套模块〕 / `check_annotations.py` / `check_revisions.py` / `deliver_gate.py`〔⬛随包自带，docx 侧零依赖；仅 `check_annotations.py --pdf` 的 PDF 侧需 pymupdf，缺失时跳过并提示〕 |
| 🟡 **推荐** | `tencent-local-office-edit`〔🟦内置〕（局部样式微调，体验最佳）；模板 docx（`assets/templates/`〔⬛随包自带〕，可替换即定制样式） |
| 🟢 **可选** | 外部数据源（金融数据终端，仅交叉验证时用）；知识库后端（KB_BACKEND：知识库/云文档/本地目录任选——检索同类范例，非必需）；`officecli`（渲染层物理缺陷扫描 + OpenXML 架构校验，S6 补充门禁，独立二进制按需自备） |
| **运行模式** | 单用户直接使用；也可作为 `ibd-doc-write` 的格式层被串联调用（见「上游接口与边界」） |

> 每个工具**为什么是这个层级、缺了会怎样**（安装/选型时读）→ [toolchain.md](references/toolchain.md) 第一节。

## 边界与协作

- **默认上游 = `ibd-doc-write`**（内容层产出草稿并声明样式场景）→ 交本 skill 套样式 + 校验；**上游开放**——人工撰写、其他 AI 流程、外部导入的 Word 文档均可调用套样式 / 格式核对
- **下游调用点（doc-write ≥0.10.0）**：写作链已把 `deliver_gate.py` 嵌进其流程（`--md` 模式在**套样式之前**做文字规范预检、`--docx` 模式作**交付前综合核验**）⇒ **本脚本改动会直接影响写作链**，升版时须同步核对 doc-write 依赖下限（当前 ≥0.15.8）。兼容性：`--annotated` / `--revised` 为新增开关，不给开关时行为与旧版完全一致（仍九项），写作链无需改动
- **顺序规则：内容质量门禁在前、格式落地在后**——write 草稿先过 `ibd-quality-gates`（数字五要素/反模式/G1-G5 + 数值自洽 check_data.py，md 即可跑），内容定稿后再交本 skill 套样式
- **⚠️ 文字规范必须在「套样式之前」先查（2026-09-10 实测）**：完整顺序 = **内容定稿 → `check_content.py --checks text`（标点全角化）→ 套样式 → `deliver_gate.py` 综合核验（复核产物加 `--annotated`/`--revised`）→ 交付**；理由与实测数据（384 处半角引号漏到套样式之后） → [workflow.md](references/workflow.md) 附录「两条时序铁律」
- **交付前一律先跑 `deliver_gate.py`**：基础九项一次跑完、只输出结论行，复核产物再加 `--annotated` / `--revised`；不要用分散的多条核验命令替代（实测同一指标被反复统计 5-8 次，输出本身成为 token 大头）
- **SKIP 须向用户点名**（2026-09-16 · ADR-0015）：deliver_gate 输出含 SKIP 项（officecli 未装/未启用、pymupdf 缺失等）时，AI 必须在回复中注明「本次 N 项 SKIP 未执行（原因）」——脚本层保证「可见的未跑」，本条保证「被看到」；静默跳过与静默失败同罪
- **批注版链路**：复核产出批注版原文 → 执行器 `ibd-doc-annotate` 注入（规范依据 = [annotations.md](references/annotations.md)）→ 本 skill `check_annotations.py` 门禁 → 交付（批注版 + 精简总览双轨）
- **下游协作**：本 skill 只改格式不改内容（铁律 0）；**内容质量（数字五要素/反模式/来源可溯）归 `ibd-quality-gates`**（内容层公共服务，上游同样开放）

## 踩坑与要点（高频三条 · 全文见 [toolchain.md](references/toolchain.md) 第二节）

- **⚠️ apply-template 只做「组件级替换」、不做段落 pStyle 映射**：套用后 pStyle 分布仍是 `(裸):N`（原来多少还是多少），易被误判"套样式失败"——段落级映射须**另做一步**；验收判据：body 级 pStyle 引用数从 0 变非 0、必备样式齐备、残留直接格式归零
- **⚠️ 半全角标点须在「套样式之前」先过 `check_content.py --checks text`**：中文语境半角引号 `"`、半角括号 `()` 判 HIGH；文字层返工将导致样式重做
- **⚠️ --revise 修订稿三坑**：① 元素名是 `w:trackRevisions`（**不存在** `w:trackChanges`）；② pPrChange 快照 pPr 不得含 `w:rPr`；③ 气泡缺失须用「Word 原生生成的格式修订文档」做对照组再归因，勿凭单点现象判定生成缺陷

## 维护

- 格式规则（样式映射/核对项/批注与修订规范）修改只改本 skill——`ibd-doc-annotate`（执行器）与 `ibd-doc-write`（写作）引用本 skill 规范，不重复维护；规则变更同步 CHANGELOG
- **规则变更同步清单（漏一环该规则即形同不存在）**：改一条格式铁律须同步 **6 环**——① 规则本体 [rules.md](references/rules.md)；② **检测脚本**（`content_text.py` ＋ `deliver_gate.py` **双处同源正则**，漏一处则门禁放行）；③ 核对项名（`CHECK_REGISTRY` / 模块 docstring / `workflow.md` 表格 / SKILL.md 资源索引）；④ **写作侧预防**（`ibd-doc-write` 的写作红线 `writing-style.md`——写作环节不加载本 skill，规则不落写作侧则产出即违例）；⑤ CHANGELOG ＋ 版本 bump ＋ README 变更摘要；⑥ 测试（**命中 ＋ 豁免不误报**双用例）＋ 端到端探针。**历史教训**：「中文不加空格」曾只做 ①③⑤，②④ 从未覆盖 → 中英之间长期无条款、无拦截
- 本 skill 升版后须**核对 [interface.md](references/interface.md) §6「版本下限速查」**——那是下游契约的**唯一登记处**（含「引入版本」与「下游消费方」两列）。⚠️ **本行原内联两个下限**（doc-annotate ≥0.15.1／doc-write ≥0.15.0），**2026-09-23 实测双双过期**（实际为 ≥0.19.0／≥0.15.7）**且漏了 `ibd-finance-review`**（≥0.16.2）⇒ 改为纯指针，**数值不再在本行重复**。
- **版本历史**：当前代际记录见本包 CHANGELOG.md（0.15.0 起）；0.1.0 – 0.14.1 共 24 个历史版本段已归档至 [changelog-archive.md](references/changelog-archive.md)

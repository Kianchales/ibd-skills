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
version: 0.17.3
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

> **本节读法**：决策树（进门选工具）与样式应用铁律（红线）留在本文件常读；**执行细则（S1-S7 / 格式核对 / 复核交付）→ [workflow.md](references/workflow.md)**，其中附录是**「脚本 × 场景」命令全表**——交付前先查那张表。

### 1. 场景识别与工具路由（决策树）

```
用户请求（写 word / 改 word + 样式要求）
│
├─ 场景A：已有 docx，整套套用样式 ──→ minimax-docx apply-template
│     （source=用户文件, template=对应模板, output=新文件）
│
├─ 场景B：新建 docx（从模板基底填充）──→ tencent-docx 专业创作
│     （创作时声明按 000-009 样式生成；或 minimax-docx create --template）
│
├─ 场景C：局部调整（某段/某表改样式）──→ tencent-local-office-edit 实时编辑
│     （唯一编辑中枢，按 style-map.md 手动应用 pStyle / 直接改格式）
│
├─ 场景D：生成后校验样式 ──→ scripts/check_styles.py
│     （统计 pStyle 分布 + 检查必备样式是否应用）
│
└─ 场景E：格式核对（只读，不改文件）──→ scripts/check_content.py
      （docx 样式化后核对：文字规范 text 组（序号/日期/标点/简称/地理）
        + 表格样式结构 table 组；输出核对报告 md。
        数值自洽 data 组已迁 ibd-quality-gates 的 check_data.py）

场景F：批注复核产物校验（只读）──→ scripts/check_annotations.py
      （docx：comments 四件套 / 4 段无空行 / 加粗分布 / 编号唯一；
        pdf：高亮条数与编号；规范见 references/annotations.md）
      注：批注的「注入生成」由 ibd-doc-annotate skill 执行，本 skill 只管规范与校验
      注：交付前跑一条命令即可涵盖本场景 → deliver_gate.py --annotated

场景G：修订稿产物校验（只读）──→ scripts/check_revisions.py
      （revise 版：ins==del 对、author/id 成对、delText/ins 非空、trackRevisions、
        clean 化落定证明；clean 版：无修订标记残留；规范见 references/revisions.md）
      注：修订稿的「生成」由 ibd-doc-annotate skill revise_docx.py 执行（--mode 按提示词区分）
      注：交付前跑一条命令即可涵盖本场景 → deliver_gate.py --revised

场景H：**交付前综合核验（一次跑完 · 极简输出）** ──→ scripts/deliver_gate.py
      （基础九项 标点/样式/vMerge/锚点/禁用词/占位符/结构/同源/指纹 合并为**一次调用**；
        按产物形态挂载复核三项——`--annotated` 加 批注部件/批注结构/批注编号，
        `--revised` 加 修订成对/修订落定/修订计数，均为十一项；
        另挂「物理扫描」一项（officecli 驱动，`--officecli` 启用；未装则 SKIP 不阻断），
        输出「一行一指标」：PASS 不展开、FAIL 才给明细。**设计目的就是压缩核验输出**——
        实测教训：分散核验时同一指标被反复统计（引号 8 次、结构核验 6 次、锚点 5 次），
        每次脚本输出都进上下文，成为 token 消耗大头。退出码 0/1 可直接作交付判据）
      **三态**：[PASS] 通过 / [FAIL] 计入退出码 / [SKIP] 未执行——SKIP **不阻断交付**
        （不计入 PASS 率），存在的意义是让「未跑物理扫描」在输出里**显式可见**，不靠人记
      用法：九项 `--docx X --md Y`；批注版 `--docx X --annotated [--expect-annotated N]`；
        修订版 `--docx X --revised [--expect-revised N]`（两开关互斥）；
        物理扫描 `--officecli [--officecli-path P] [--expect-issues N]`
```

**工具调用顺序**（与文档生成工具链一致）：
1. 新建创作 → `tencent-docx`（首选）；失败降级 `minimax-docx create`
2. 已有文件整套套样式 → `minimax-docx apply-template`（实测通过，XSD 校验门禁防损坏）
3. 局部微调/改段落样式 → `tencent-local-office-edit`（唯一编辑中枢）
4. 样式校验 → 本 skill 自带脚本 [check_styles.py](scripts/check_styles.py)
5. **交付前综合核验 → [deliver_gate.py](scripts/deliver_gate.py)（基础九项一次跑完、只输出结论行；批注版加 `--annotated`、修订版加 `--revised`）**

**失败降级协议（脚本兜底 + 标注局限）**：

| 失败场景 | 默认降级 | 交付说明 |
|---------|---------|---------|
| tencent-docx 不可用 | `minimax-docx create` | 注明降级方案 |
| minimax-docx 不可用 | **脚本兜底**：以 `assets/templates/` 对应模板为基底（复制 styles.xml 等部件），仅替换 document.xml（段落 pStyle + 三线表） | 注明「脚本兜底生成」；覆盖不了的元素（封面/TOC/页眉页脚/页码/图片/修订）列出清单标注「待人工处理」 |
| 局部编辑工具不可用 | 脚本直接修改 document.xml 的样式字段 | 注明降级；编辑器同步风险提示 |
| 文档含脚本兜底覆盖不了的元素（封面/TOC/图片等） | 不硬撑——输出 Markdown + 样式应用说明 | 注明非最终形态，建议走专业工具 |
| 校验门禁未过 | 返回 S4/S5 修正后重跑 | 门禁结果摘要（必备样式/裸段落/空段落/跳级） |

### 2. 执行流程（S1-S7）

> **完整细则 → [workflow.md](references/workflow.md) 第一节**（含样式映射全表、S6 门禁命令清单、S7 三件套交付）
>
> - **七步主线**：S1 识别场景 → S2 加载样式资产 → S3 工具路由 → S4 样式映射（内容段落→pStyle，核心）→ S5 序号/表格规则 → S6 校验门禁 → S7 三件套交付（修订稿 + 格式问题清单 + 修改统计）
> - **S4 映射按 [style-map.md](references/style-map.md)**（000 正文、001/0011 一级、002-007 二至七级、008 单位行、009 备注、a6 表格）；S5 序号判定与三线表规则按 [rules.md](references/rules.md) 第一/二节
> - **S6 门禁一条命令跑完**：`deliver_gate.py`（基础九项；复核产物加 `--annotated` / `--revised`）——命令全表见 [workflow.md](references/workflow.md) 附录

### 3. 样式应用铁律

0. **只改格式、严禁修改原文内容（最高优先级）**：本 skill 只做样式应用（pStyle/字体/字号/对齐/缩进/间距/边框），**不得增、删、改、移任何文字内容**（含表格内文字、标点、空格、数字、单位）。套用样式后必须用 `check_styles.py --verify-content <原文件>` 校验内容完整性——文本与原文逐字不一致即 FAIL，打回重做，不交付。内容修改（如补数据、改措辞）属内容层任务，本 skill 一律不做。
1. **模板先行**：任何文档动笔前先确认模板 docx 存在（`assets/templates/`），优先以模板为基底（保留 styles.xml 样式表）；**模板即样式源，使用者替换模板即定制输出样式**
2. **pStyle 优先于手写格式**：能应用命名样式（000-009/0011/001）就不用直接格式（字体/字号硬编码），保证全文一致性与后续批量修改能力
3. **序号段落判定：标题 vs 正文（双维度算法）**："1、""（1）""1）""①"开头的段落可能是标题也可能是正文——按 `rules.md` 双维度判定：**段落长短**（≤40 字短语式→标题倾向；>40 字完整句→正文倾向）+ **上下文分段**（主判据：后段独立正文展开→情况1 标题；后段连续序号/无后段→情况2 列举正文）。可 `check_styles.py --check-numbering` 输出序号段落清单辅助核对
4. **反馈回复合规展示**：监管问题原文必须 001（黑体），回复正文必须 000（宋体）——黑体宋体对照本身就是审核合规展示，不得混用
5. **不覆盖用户手动格式**：用户已有 docx 中人工调整的格式（非样式体系内容），apply-template 前先与用户确认是否保留
6. **段落间禁止空行/空段落**：段落间距一律靠样式 spacing（段前/段后）控制，不得插入无文字空段落分隔段落——样式自带 spacing 已提供间距，空段落破坏样式统一性（命中裸段落检查）、造成间距叠加

### 4. 格式核对模式（check_content.py，只读不改文件）

> **完整细则 → [workflow.md](references/workflow.md) 第二节**（含命令块、两大组别 10 项核对矩阵、边界说明）
>
> - **只读审查**，适用于任意投行 Word 文档（中性通用规则）；命令：`check_content.py --input <docx> [--checks text|table|geo,table_na]`，出 `<input>_格式核对报告.md`
> - **两大组别**：文字类 text（序号连续性 / 用词规范 / 日期写法 / 多余空格·数字前后空格·重复标点 / 释义简称 / 地理表述）+ 表格类 table（字号体系 / 数字右对齐 / 空单元格 / NA 标记统一），按 HIGH/MEDIUM/LOW 分级
> - **边界**：本模式查格式层自洽；**数值自洽**（勾稽/前后一致）与**内容质量溯源**归 `ibd-quality-gates`（check_data.py）。敏感词/地理清单见 [sensitive_terms.json](references/sensitive_terms.json)

### 5. 批注与修订复核交付模式（规范 + 只读校验）

> **完整细则 → [workflow.md](references/workflow.md) 第三节**（含门禁命令块、检查项清单、加粗语义坑、自测命令）
>
> - **职责**：本 skill 定规范 + 门禁（只读）；**批注注入 / 修订稿生成 = `ibd-doc-annotate`**（同一份复核问题清单 → `annotate_docx.py` / `revise_docx.py --mode`）——两 skill 交接以本 skill 规范为合规依据；`check_styles.py --revise` 的格式修订属样式链路、与复核交付无关
> - **门禁一条命令**：`deliver_gate.py --docx <件> --annotated [--expect-annotated N]` / `--revised [--expect-revised N]`，**任一 FAIL → 退回 `ibd-doc-annotate` 重注入，不交付**
> - **规范单一事实源**：批注 → [annotations.md](references/annotations.md)；修订 → [revisions.md](references/revisions.md)；交付口径 → [delivery.md](references/delivery.md)
> - **⚠️ 加粗判定须按语义**：`<w:b w:val="0">` 是**显式取消加粗**，只判 `<w:b>` 元素存在会把合规批注误判 FAIL（实测 2026-09-11，两脚本均已修）

## 资源索引

### 样式资产（先加载，禁止裸写）

> 模板文件路径（**skill 自带，即样式源**）：`assets/templates/`（相对本 skill 目录）
> **模板即样式源**：使用者可直接修改/替换 `assets/templates/` 下的 docx——**改模板 = 定制输出样式**，输出将跟随新模板。
> **模板随包携带**：`assets/templates/` 三个模板 docx 随分发包一起分发（zip 内含），分发版与本地版资产一致，可直接使用或替换定制
> 模板权威源为机构内部资产（不随分发包携带）；分发版以包内 `assets/templates/` 为使用源，样式定义以包内模板 + style-map.md/rules.md 为准。

| 模板文件 | 适用文档 | 样式体系 | 关键样式 ID |
|---------|---------|---------|------------|
| `报告模板.docx` | 招股书章节 / 报告 / 备忘录 / 尽调报告等正式文档 | 招股书版 000-009 | 000 正文、001 一级标题、002-007 二级至七级标题、008 单位、009 备注 |
| `反馈回复样式.docx` | 审核问询回复 / 反馈回复 / 落实函回复 | 反馈回复版（000-009 + 0011/001） | 0011 一级标题（问题编号）、001 问题正文（监管问题黑体）、000 正文、002-009 明细层级 |
| `表格模板.docx` | 以上全部文档的表格 | 三线表 | 报告表格 a6、表格前单位 a5、表格后说明 a4 |

**完整样式定义**（每种样式的字体/字号/对齐/缩进/间距/行距/大纲级别）见 [style-map.md](references/style-map.md)。

**执行细则**（S1-S7 执行流程 / 格式核对模式与 10 项矩阵 / 批注与修订复核交付模式 / **「脚本 × 场景」命令全表**）见 [workflow.md](references/workflow.md)——**动手做之前翻这一份**。

**批注复核规范**（交付形态双轨 / 4 行紧凑结构 / 编号体系 / 类型词表 / 字体 / 锚点规则 / 校验门禁）见 [annotations.md](references/annotations.md)；**修订稿交付规范**（三模式 / rev 字段 / 修订落定 / 修改清单 / 校验门禁）见 [revisions.md](references/revisions.md)——批注与修订稿复核的**格式单一事实源**；执行器（批注注入 + 修订稿生成）= `ibd-doc-annotate` skill。

**章节复核交付约定**（默认交付形态 / 执行链路 / 批注与修订职权划分 / 触发语路由 / 批注纪律）见 [delivery.md](references/delivery.md)——复核类委托的**交付口径单一事实源**。

**版本历史**：变更记录见本包 CHANGELOG.md（当前代际 0.15.0 起）；0.1.0 – 0.14.1 共 24 个历史版本段已归档至 [changelog-archive.md](references/changelog-archive.md)。

## 依赖与工具

> **本 skill 完全独立**——不依赖多角色团队、不依赖特定知识库，任何人可直接使用。

| 维度 | 说明 |
|---|---|
| 🔴 **必须** | 任一 docx 处理工具（`minimax-docx`〔🟨官方市场〕 或 `tencent-docx`〔🟦内置〕至少一，套样式/新建用）+ 内置脚本 `check_styles.py` / `check_content.py`〔含 `content_common.py` / `content_text.py` / `content_table.py` 三配套模块〕 / `check_annotations.py` / `check_revisions.py` / `deliver_gate.py`〔⬛随包自带，docx 侧零依赖；仅 `check_annotations.py --pdf` 的 PDF 侧需 pymupdf，缺失时跳过并提示〕 |
| 🟡 **推荐** | `tencent-local-office-edit`〔🟦内置〕（局部样式微调，体验最佳）；模板 docx（`assets/templates/`〔⬛随包自带〕，可替换即定制样式） |
| 🟢 **可选** | 外部数据源（金融数据终端，仅交叉验证时用）；知识库后端（KB_BACKEND：知识库/云文档/本地目录任选——检索同类范例，非必需）；`officecli`（渲染层物理缺陷扫描 + OpenXML 架构校验，S6 补充门禁，独立二进制按需自备） |
| **运行模式** | 单用户直接使用；也可作为 `ibd-doc-write` 的格式层被串联调用（见「上游接口与边界」） |

### 工具说明（安装时读 · 每个工具为什么是这个层级）

**🔴 必须 · `tencent-docx`〔🟦内置〕 / `minimax-docx`〔🟨官方市场〕（docx 处理，二选一）**
- 用途：套样式（minimax-docx `apply-template`）/ 新建文档（tencent-docx `create`）
- 为什么必须：本 skill 的所有 docx 操作都建立在 docx 工具之上；**没有它无法读/写 Word 文档**，只能输出 Markdown + 样式说明

**🔴 必须 · 内置脚本（`check_styles.py` / `check_content.py` / `check_annotations.py` / `check_revisions.py` / `deliver_gate.py`）**
- 用途：样式校验（必备样式/裸段落/空段落/跳级/内容一致）+ 格式核对 14 项（只读）+ 批注产物校验（4 段结构/加粗分布/编号/四件套，只读）+ 修订稿产物校验（ins/del 对/author/id/trackRevisions/落定证明，只读）+ **交付前综合核验九项（一次跑完 · 极简输出，PASS 不展开、FAIL 才给明细）**
- **`check_content.py` 是拆组后的 CLI 入口**：内部按业务域分为 `content_common.py`（共享基础层：Issue / docx 解析 / 中文序号基元 / 标点基元）+ `content_text.py`（文字类 7 项）+ `content_table.py`（表格类 4 项），**三模块须与入口同目录随包分发**（入口内为绝对 import）；对外契约（参数/报告文件名/退出码）与拆组前完全一致
- 为什么必须：随包自带零依赖，校验与核对是本 skill 的核心能力
- 缺了会怎样：不会缺——随包分发，无需额外安装

**🟡 推荐 · `tencent-local-office-edit`**
- 用途：局部样式微调（改单段/单表样式，实时编辑所见即所得）
- 为什么推荐：微调场景体验最佳；没有则用脚本改 document.xml，可用但需注意格式细节

**🟡 推荐 · 模板 docx（`assets/templates/`）**
- 用途：样式源（报告模板 / 反馈回复样式 / 表格模板）——**改模板 = 定制输出样式**
- 为什么推荐：模板是样式体系的可视化载体；没有则只能按 `style-map.md` 文字逐项手工设置，样式落地变繁琐

**🟢 可选 · 外部金融数据终端 / KB_BACKEND**
- 用途：金融数据交叉验证；KB_BACKEND 检索同类范例（知识库/云文档/本地目录任选）
- 为什么可选：格式核对不依赖外部数据；范例检索仅是锦上添花
- 缺了会怎样：**核心功能（样式/核对/校验）完全不受影响**

**🟢 可选 · `officecli`（独立二进制，按需自备）**
- 用途：渲染层物理缺陷扫描（`view issues`：文本溢出/首行缩进缺失/公式错误）+ OpenXML 架构校验（`validate`）；**已挂进 `deliver_gate.py --officecli`**（常驻一行状态：未装则 `[SKIP]` 可见但不阻断）
- 为什么可选：脚本 check_styles.py 查**样式规则应用**（pStyle/裸段落/跳级），officecli 查**渲染与结构层物理缺陷**——规则检查 vs 物理扫描互补，不是替代
- 缺了会怎样：`deliver_gate` 的物理扫描行输出 `[SKIP] 未找到 officecli`（**交付说明据此注明「未跑物理缺陷扫描」**，不再靠人记），核心样式流程不受影响

## 边界与协作

- **默认上游 = `ibd-doc-write`**（IBD 投行文档写作）：内容层产出草稿并声明样式场景（招股书版/反馈回复版）→ 交本 skill 套样式 + 校验
- **下游调用点（doc-write ≥0.10.0）**：写作链已把本 skill 的 `deliver_gate.py` 嵌进其流程——`--md` 模式用在**套样式之前**做文字规范预检（其流程 ①''）、`--docx` 模式作**交付前综合核验**（其流程 ④）。**故本脚本的改动会直接影响写作链**：升版时须同步核对 doc-write 的依赖下限声明（当前 ≥0.15.8）。**兼容性提示**：`--annotated` / `--revised` 为新增开关，不给开关时行为与旧版完全一致（仍九项），故写作链无需改动即可继续调用
- **顺序规则：内容质量门禁在前、格式落地在后**——write 草稿先过 `ibd-quality-gates`（数字五要素/反模式/G1-G5 + 数值自洽门 check_data.py，md 即可跑），内容定稿后再交本 skill 套样式；套样式后跑 check_content（text/table 组，依赖样式化 docx）
- **⚠️ 文字规范必须在「套样式之前」先查（2026-09-10 实测）**：标点全半角（引号/括号）虽是格式核对项，但**返工成本的落点不同**——若等套样式之后才发现文字层问题，改文字会导致样式重做。实测一份交付件有 384 处半角引号一路漏到套样式之后才被抓出，白跑一轮样式。故完整顺序应为：
  **内容定稿 → `check_content.py --checks text`（先把标点全角化）→ 套样式 → `deliver_gate.py` 综合核验（复核产物加 `--annotated`/`--revised`）→ 交付**
- **交付前一律先跑 `deliver_gate.py`**：基础九项一次跑完、只输出结论行，复核产物再加 `--annotated` / `--revised`；不要用「分散的多条核验命令」替代（实测同一指标被反复统计 5-8 次，输出本身成为 token 大头）
- **上游开放**：本 skill 是格式层公共服务，**不限于 write 接入**——人工撰写、其他 AI 流程、外部导入的 Word 文档均可调用套样式 / 格式核对（触发词见上表）
- **批注版链路**：章节复核产出批注版原文 → 执行器 `ibd-doc-annotate` 注入（规范依据 = 本 skill [annotations.md](references/annotations.md)）→ 本 skill `check_annotations.py` 门禁 → 交付（批注版 + 精简总览双轨）；门禁归入主理人 G5 把关范围
- **下游协作**：本 skill 只改格式不改内容（铁律 0）；**内容质量（数字五要素/反模式/来源可溯）归 `ibd-quality-gates`**（内容层公共服务，上游同样开放）；格式核对中的「文档内数据自洽」与本 skill 边界见「格式核对模式」

## 踩坑与要点

- **中文文件名编码**：Git Bash 向 Python/minimax CLI 传中文文件名参数可能乱码（zipfile 读 报告模板.docx 曾报 "No such item"）→ 优先用 Python `glob.glob`/`os.listdir` 遍历目录取文件，或复制为临时英文文件名再处理
- **minimax-docx 环境**：restore 必须用 csproj（.slnx 不支持 dotnet 8）；依赖华为云 NuGet 镜像
- **apply-template 语义**：把模板样式套到源文件（保留源内容换样式），不是以模板内容为基底——新建场景用 create，套用场景用 apply-template，勿混淆
- **⚠️ apply-template 只做「组件级替换」、不做段落 pStyle 映射（2026-09-10 实测）**：该命令替换的是 styles/theme/numbering/sectPr 等部件，**段落级样式映射不在其职责内**——套用后 pStyle 分布仍是 `(裸):N`（原来多少还是多少），易被误判为"套样式失败"。段落级映射须**另做一步**：少量走 `tencent-local-office-edit` 手动指定，批量走脚本改 document.xml（插 `w:pStyle` + 清 `w:pPr` 残留直接格式 + 清 run 的 `rPr` 仅留真加粗/上标）。**验收判据**：body 级 pStyle 引用数从 0 变为非 0、必备样式齐备、残留直接格式归零
- **⚠️ 半全角标点属格式核对项，须在「套样式之前」先过 `check_content.py --checks text`（2026-09-10 实测）**：中文语境半角引号 `"`、半角括号 `()` 会被判 HIGH（实测一份 384 处引号一路漏到套样式之后才被主理人补跑抓出）。文字层返工将导致样式重做——**内容定稿后、套样式之前，先跑文字规范核对把标点全角化**，再进入样式落地
- **标点全角化的安全做法（实测）**：引号按**行内出现顺序交替**替换为左/右引号（须先验"含奇数个引号的行的数量 = 0"，即所有引号均在本行/本段内配对）；替换后以「**去掉全部引号字符后的文本 sha256 前后一致**」证明零内容改动。全半角为等宽字符，替换前后字符数与 document.xml 长度均不变
- **--revise 修订稿三坑（2026-08-27 实测，OpenXmlValidator 实证）**：
  1. **元素名是 `w:trackRevisions`，不存在 `w:trackChanges`**——settings.xml 写 trackChanges 是非法元素，Word 静默忽略，修订记录与显示全部失效；合法插入位置为 `w:bordersDoNotSurroundFooter` 之后（25 个位置暴力测试仅此一处过 validator），revisionView 必须带 `w:formatting="1"` 否则打开时格式标记默认隐藏
  2. **pPrChange 快照 pPr 不允许含 `w:rPr`**（CT_PPrGeneral 类型）——真实文档裸段落（有 pPr 无 pStyle）快照时须剔除段落标记 run 属性，否则 Word 视为无效修订节点不显示
  3. **气泡缺失的诊断顺序（排查中尚未定案）**：正常情况下 pPrChange（段落属性/样式更改）应显示「已设置格式」气泡；若审阅窗格有条目但正文无气泡，按序排查：①窗口宽度不足 Word 静默回退嵌入模式（缩放调小/最大化验证）；②修订选项里「更改行」标记是否设为「无」；③用户报告其环境一度全局失去 pPrChange 气泡（含其他历史文档），疑与 Office 更新/全局设置有关——**用「Word 原生生成的格式修订文档」做对照组一锤定音后再归因，勿凭单点现象判定生成缺陷**
- **verify-content 必须段落级拼接对比**：按 `<w:t>` 逐 run 对比会被 merge-runs 破坏对齐而误报「内容被修改」；extract_para_texts 按段落拼接全部 w:t 后再比，与 run 结构无关
- **officecli 实测（2026-09-01，v1.0.146）**：
  1. `view issues` 自动识别 zh-CN locale，会把「正文段落缺首行缩进」报为格式问题（建议缩进 2 字符）——与招股书版 000 正文规则一致，可作补充核对的交叉验证
  2. `create` 生成的空白文档无预置 Heading1 样式（会告警），套样式以本 skill 模板为准，勿依赖 CLI 自带样式
  3. `batch` 批量操作默认原子回滚（v1.0.137+），任一失败整体回滚不落盘——适合正式文档批量修改
  4. 调用方式：`<officecli 安装目录>/officecli.exe`（未入 PATH，按本机安装位置确认）；与 `tencent-local-office-edit` 编辑中的文件勿同时操作（文件锁隔离）

## 维护

- 格式规则（样式映射/核对项/批注与修订规范）修改只改本 skill——`ibd-doc-annotate`（执行器）与 `ibd-doc-write`（写作）引用本 skill 规范，不重复维护；规则变更同步 CHANGELOG
- 本 skill 升版后须复核下游版本下限（doc-annotate ≥0.15.1 / doc-write ≥0.15.0），同步各包依赖声明

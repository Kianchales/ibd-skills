---
name: ibd-doc-review
slug: ibd-doc-review
displayName: IBD 投行格式复核
summary: A 股投行文档格式复核：样式规范化（招股书/反馈回复排版）+ 格式核对（序号/日期/标点/简称/表格），只读核对不改文件。
description: >
  本技能用于 A 股投行文档的格式处理，提供两类能力：
  1. 样式应用：对 Word 文档套用招股书版或反馈回复版样式体系，适用于招股书、
     反馈回复、报告、备忘录、尽调报告等正式文档；样式以模板文件为源
     （assets/templates/），可通过修改模板自定义输出样式。
  2. 格式核对：对文档进行格式质量检查，覆盖标题序号连续性、日期写法统一、
     标点全半角、释义简称、表格规范等 10 个核对项，输出按严重程度
     分级的问题清单（含位置、原文、问题与修改建议）。
  3. 渲染层物理缺陷扫描 + 架构校验（可选，officecli 驱动）：文本溢出、首行
     缩进缺失、公式错误等渲染问题，以及 OpenXML 架构合法性校验。
  4. 批注与修订复核规范与校验：复核结论落到原文（批注 / 修订稿）的格式单一
     事实源（批注 4 行紧凑结构/编号/类型词表/字体/锚点；修订三模式/rev 字段/
     修订落定）+ 产物只读校验门禁（[check_annotations.py](scripts/check_annotations.py) 批注 / [check_revisions.py](scripts/check_revisions.py) 修订稿）。
  本技能不修改文档内容。
  触发词：「按招股书样式」「招股书排版」「按反馈回复样式」「问询回复格式」
  「落实函格式」「套模板样式」「核对格式」「格式自查」「检查序号金额日期标点」
  「批注复核」「原位批注」「复核意见打在原文」「批注格式」「校验批注」
  「修订稿校验」「校验修订」「检查修订稿」「修订结构对不对」
version: 0.15.5
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
| 批注复核产物校验（只读） | 「批注复核」「原位批注」「复核意见打在原文」「批注格式」「校验批注」「批注结构对不对」 |
| 修订稿产物校验（只读） | 「修订稿校验」「校验修订」「检查修订稿」「修订结构对不对」「看修订稿格式」 |

> 若任务同时含「写反馈回复内容」→ 内容写作属内容层任务（默认上游 = `ibd-doc-write`，见「上游接口与边界」）；本 skill 只负责生成后的样式落地；两者可串联（先写内容、再套样式）。
> 典型用例（触发→执行→产出 全链路示例）见 [examples.md](references/examples.md)。

## 使用流程

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

场景G：修订稿产物校验（只读）──→ scripts/check_revisions.py
      （revise 版：ins==del 对、author/id 成对、delText/ins 非空、trackRevisions、
        clean 化落定证明；clean 版：无修订标记残留；规范见 references/revisions.md）
      注：修订稿的「生成」由 ibd-doc-annotate skill revise_docx.py 执行（--mode 按提示词区分）
```

**工具调用顺序**（与文档生成工具链一致）：
1. 新建创作 → `tencent-docx`（首选）；失败降级 `minimax-docx create`
2. 已有文件整套套样式 → `minimax-docx apply-template`（实测通过，XSD 校验门禁防损坏）
3. 局部微调/改段落样式 → `tencent-local-office-edit`（唯一编辑中枢）
4. 样式校验 → 本 skill 自带脚本 [check_styles.py](scripts/check_styles.py)

**失败降级协议（脚本兜底 + 标注局限）**：

| 失败场景 | 默认降级 | 交付说明 |
|---------|---------|---------|
| tencent-docx 不可用 | `minimax-docx create` | 注明降级方案 |
| minimax-docx 不可用 | **脚本兜底**：以 `assets/templates/` 对应模板为基底（复制 styles.xml 等部件），仅替换 document.xml（段落 pStyle + 三线表） | 注明「脚本兜底生成」；覆盖不了的元素（封面/TOC/页眉页脚/页码/图片/修订）列出清单标注「待人工处理」 |
| 局部编辑工具不可用 | 脚本直接修改 document.xml 的样式字段 | 注明降级；编辑器同步风险提示 |
| 文档含脚本兜底覆盖不了的元素（封面/TOC/图片等） | 不硬撑——输出 Markdown + 样式应用说明 | 注明非最终形态，建议走专业工具 |
| 校验门禁未过 | 返回 S4/S5 修正后重跑 | 门禁结果摘要（必备样式/裸段落/空段落/跳级） |

### 2. 执行流程（S1-S7）

**S1 识别样式场景**
- 用户明确指定（招股书版 / 反馈回复版）→ 直接采用
- 未明确 → 按文档类型推断：含"问题X."编号或【发行人说明】【中介机构核查】→ 反馈回复版；其余正式文档（含"第一节/第二节"、业务与技术、报告、备忘录等）→ 招股书版（000-009）

**S2 加载样式资产**
- 读 [style-map.md](references/style-map.md) 对应样式体系表
- 确认模板 docx 存在（`ls` 检查，中文文件名注意编码）
- 新建场景：确定是「以模板为基底填充」还是「从零生成后按表设置」

**S3 工具路由**
- 按上文决策树选择工具；调用前 ToolSearch 加载 skill / 工具 schema
- `minimax-docx` 环境备忘：依赖 .NET SDK 8 + 华为云 NuGet 镜像；`apply-template` 前先 `dotnet restore MiniMaxAIDocx.Cli/MiniMaxAIDocx.Cli.csproj --source https://repo.huaweicloud.com/repository/nuget/v3/index.json`

**S4 样式映射（核心）**
按 [style-map.md](references/style-map.md) 将内容段落映射到 pStyle：

| 内容类型 | 招股书版 pStyle（含报告类文档） | 反馈回复版 pStyle |
|---------|----------------|------------------|
| 章 / 问题编号标题 | 001（第一节 XXX，居中分页前） | 0011（问题1.XXX，两端对齐） |
| 监管问题原文 | — | 001（黑体缩进，问题正文） |
| 正文段落 | 000 | 000（首行缩进2字符1.5倍行距） |
| 二级标题 | 002（一、） | 002（一、，加粗） |
| 三级标题 | 003（（一）） | 003（（一），加粗） |
| 四级标题 | 004（1、） | 004（1、，加粗） |
| 五级标题 | 005（（1）） | 005（（1），加粗） |
| 六级标题 | 006（1）） | 006（1），默认） |
| 七级标题 | 007（①） | 007（①，默认） |
| 表格前单位行 | 008（右对齐五号） | 008（右对齐五号） |
| 表格后备注行 | 009（五号首行缩进） | 009（五号首行缩进） |
| 表格 | 报告表格 a6 | 报告表格 a6 |

**S5 标题序号 + 表格规则**
- 标题序号九级链 + 「序号段落判定（标题 vs 正文，双维度算法）」→ [rules.md](references/rules.md) 第一节
- 表格三线表规范（框线/字号/对齐/tblHeader/合计加粗）→ [rules.md](references/rules.md) 第二节

**S6 校验门禁**
- 成品文档校验：`python check_styles.py --input <docx或目录> --scenario <招股书|反馈回复>`（脚本位于本包 scripts/）（`报告` 为 `招股书` 别名，兼容旧调用；默认 `--mode document`）
- 模板/样式库校验：`--mode template`（检查 styles.xml 中 000-009 / 0011+001 / a4-a6 是否齐全；模板正文为空属正常，勿用 document 模式误判）
- 内容完整性校验：`--verify-content <原文.docx>`（套样式后文本与原文逐字对比，严禁修改原文内容）
- 序号段落核对：`--check-numbering`（列出序号开头段落及上下文，辅助标题/正文判定）
- 格式修改清单：`--diff <原文.docx>`（对比样式化结果与原文，生成格式问题清单 + 修改统计，详见 S7）
- 修订稿生成：`--revise <原文件.docx>`（基于原文件生成 Word 修订稿：格式改动转为 w:pPrChange 修订 + trackChanges，详见 S7）
- 检查项：必备样式已应用（000 + 场景一级：招股书 001 / 反馈回复 0011+001）、无裸正文段落、无空段落（段落间禁止空行）、标题层级无跳级
- `minimax-docx apply-template` 自带 XSD 校验门禁（防损坏）
- **补充门禁（推荐 · officecli 驱动，缺省不卡流程；承接 ibd-quality-gates 原 G6 语义——内容层 0.6.0 起不再持有 officecli，docx 物理扫描统一在本节）**：
  - 架构校验：`officecli validate <docx>`——OpenXML schema 合法性（防文件损坏/Word 打不开）
  - 渲染层缺陷扫描：`officecli view <docx> issues`——文本溢出、正文首行缩进缺失、公式错误等物理缺陷
  - officecli 不可用时跳过并在交付说明注明「未跑物理缺陷扫描」；发现问题 → 返回 S4/S5 修正后重跑
- **任一不符 → 返回 S4/S5 修正后重跑，不交付**

**S7 交付与声明（三件套交付物）**
格式修改任务（已有 docx 套样式/改格式）交付**三件套**：
1. **修订稿**（docx，Word 修订格式）：基于**原文件**生成，所有格式改动以 `w:pPrChange`（格式更改修订）标记，并开启 `trackChanges`——Word 打开后在审阅面板逐条查看，可接受/拒绝。生成：`check_styles.py --input <样式化结果.docx> --revise <原文件.docx>`（输出 `<原文件>_修订稿.docx`，`--output` 可指定路径）
2. **格式问题清单**（md）：`check_styles.py --diff <样式化结果.docx> <原文.docx>` 自动生成 `<样式化结果>_格式修改清单.md`——逐条列出**位置、原文、改成什么**（段落位置 + 原样式 → 新样式；空段落删除单列）
3. **修改统计**：清单内「修改统计」表——总段落数、修改段落合计、标题样式/正文样式/空段落删除/表格、文本内容一致性
- 交付说明：交付物路径 + 样式应用情况声明（"已按招股书版 000-009 样式生成/套用" 或 "已按反馈回复版样式套用"）
- 若从零生成，必须声明"已按报告模板 000-009 样式生成"
- 样式未全覆盖处列出清单（哪些段落待人工复核）

### 3. 样式应用铁律

0. **只改格式、严禁修改原文内容（最高优先级）**：本 skill 只做样式应用（pStyle/字体/字号/对齐/缩进/间距/边框），**不得增、删、改、移任何文字内容**（含表格内文字、标点、空格、数字、单位）。套用样式后必须用 `check_styles.py --verify-content <原文件>` 校验内容完整性——文本与原文逐字不一致即 FAIL，打回重做，不交付。内容修改（如补数据、改措辞）属内容层任务，本 skill 一律不做。
1. **模板先行**：任何文档动笔前先确认模板 docx 存在（`assets/templates/`），优先以模板为基底（保留 styles.xml 样式表）；**模板即样式源，使用者替换模板即定制输出样式**
2. **pStyle 优先于手写格式**：能应用命名样式（000-009/0011/001）就不用直接格式（字体/字号硬编码），保证全文一致性与后续批量修改能力
3. **序号段落判定：标题 vs 正文（双维度算法）**："1、""（1）""1）""①"开头的段落可能是标题也可能是正文——按 `rules.md` 双维度判定：**段落长短**（≤40 字短语式→标题倾向；>40 字完整句→正文倾向）+ **上下文分段**（主判据：后段独立正文展开→情况1 标题；后段连续序号/无后段→情况2 列举正文）。可 `check_styles.py --check-numbering` 输出序号段落清单辅助核对
4. **反馈回复合规展示**：监管问题原文必须 001（黑体），回复正文必须 000（宋体）——黑体宋体对照本身就是审核合规展示，不得混用
5. **不覆盖用户手动格式**：用户已有 docx 中人工调整的格式（非样式体系内容），apply-template 前先与用户确认是否保留
6. **段落间禁止空行/空段落**：段落间距一律靠样式 spacing（段前/段后）控制，不得插入无文字空段落分隔段落——样式自带 spacing 已提供间距，空段落破坏样式统一性（命中裸段落检查）、造成间距叠加

### 4. 格式核对模式（check_content.py，只读不改文件 · 分组框架）

> 敏感词/地理表述清单见 [sensitive_terms.json](references/sensitive_terms.json)（--geo-file 驱动，可扩展维护）。

触发：「核对格式」「格式自查」「投行格式核对」「检查序号/日期/标点/表格样式」「文件质量核查」等**只读审查类请求**。适用于任意投行 Word 文档（中性通用规则）。数值自洽核对（金额文本格式/数值前后一致/勾稽）请用 `ibd-quality-gates` 的 check_data.py（md/docx 双载体）。

```bash
python scripts/check_content.py --input <docx>                          # 全部核对项（样式化 docx：text+table）
python scripts/check_content.py --input <docx> --checks text            # 只查文字规范组
python scripts/check_content.py --input <docx> --checks table           # 只查表格样式/结构组
python scripts/check_content.py --input <docx> --checks geo,table_na    # 指定子项
```

**两大组别 × 严重程度矩阵**（HIGH=错误须改 / MEDIUM=警告大概率改 / LOW=提示人工酌情；docx 载体）：

| 组别 | 核对项 | 默认严重度 | 判定逻辑 |
|------|--------|-----------|---------|
| **文字类 text** | 标题层级序号连续性（跳号/重号/倒退；支持第X节/第X章、问题X 自定义编号，级别高于「一、」；中文数字一~九十九） | HIGH | 层次感知算法：同层递增+1，降层重起，升层按自身序列续 |
| | 用词规范性（错别字/异形词，内置规则可经 term_rules.json 扩展） | MEDIUM | 内置+外部清单正则扫描 |
| | 日期写法统一（十种形式：中英、年月/年月日、连写、分隔符等） | MEDIUM | 形式占比统计→主导写法判定→少数派明细；分隔符一致性 |
| | 多余空格与重复标点 | HIGH | 中文间双空格、全角标点叠用、半角标点连打、中英混排 |
| | 释义简称统一（冲突/前置使用/疑似未定义复用/引号风格） | MED-LOW | 定义对提取+前后位置比对+括号短语频次分析 |
| | 国家城市表述合规（--geo-file 外部敏感词清单驱动） | HIGH | 清单命中即报，出现次数与首现上下文 |
| **表格类 table** | 字号体系：全表五号（10.5pt），放不下可用小五（9pt），其余违规 | HIGH | 单元格 w:sz 扫描（21/18 合法） |
| | 表格数字右对齐 | MEDIUM | 数值单元格段落 jc 校验 |
| | 空单元格 | LOW(提示) | 空单元格统计（不计入问题数） |
| | 「不适用」标记符号同表内统一性 | MEDIUM | —/-//不适用/N.A. 分类计数 |

交付：`<input>_格式核对报告.md`——核对总览矩阵（组别×严重度）+ 按 HIGH/MEDIUM/LOW 三级分块的逐条明细（核对项/位置/原文/问题/建议）。控制台输出错误/警告/提示三级汇总。**只读核对，不改文件**。

**边界**：本模式查的是**文字/表格自洽与样式规范**（序号连续性/简称日期写法统一/表格字号对齐/空与 NA 标记），属格式层核对；**数值自洽**（金额文本格式/数值前后一致/合计勾稽/跨表比对）已于 2026-09-06 迁 `ibd-quality-gates` 的 check_data.py（md/docx 双载体，写作链 md 阶段前置跑）；**内容质量与来源可溯**（每个数字有没有出处、判断有没有依据、是否说过头话）同样归 `ibd-quality-gates`。三类可**串联执行**：先过 gates（内容/溯源 + 数值自洽，md 即可跑）→ 本模式查格式/自洽（docx）→ 交付；外部文档也可只调用其中一类。

### 5. 批注与修订复核交付模式（规范 + 只读校验）

> 复核结论落到原文（用户裁定：**批注版优先 + 精简总览报告双轨并存**，替代原「默认只出独立审核报告」；用户明确「生成修订稿」时才走修订，按提示词区分 revise/clean/both）。**批注规范单一事实源 = [annotations.md](references/annotations.md)；修订稿规范单一事实源 = [revisions.md](references/revisions.md)**。

- **职责分工**：本 skill 定义规范 + 校验门禁（只读）；**批注注入 / 修订稿生成 = `ibd-doc-annotate` skill**（同一份复核问题清单 → `annotate_docx.py`/`annotate_pdf.py` 批注版，或 `revise_docx.py --mode` 修订稿）——两 skill 交接以本文件为合规依据
- **职权边界**：复核交付的批注与修订稿同属 `ibd-doc-annotate` 职权（批注/修订同为其复核落地形态）；本 skill `check_styles.py --revise` 的格式修订属样式应用链路、与复核交付无关
- **批注正文结构**：每条 4 行紧凑、无空行——标签行(加粗)/标题行(加粗,单独一行)/问题描述(引导词加粗)/建议(引导词加粗)
- **编号**：`J`财务 `L`法律 `I`行业 `Z`主理人 + 作者内序号（J-01…），批注/修订稿/总览同一体系互相回溯
- **校验门禁**（产物交付前必跑）：

```bash
python scripts/check_annotations.py --input <带批注.docx 或目录>                # 批注 docx 侧
python scripts/check_annotations.py --pdf <带注释.pdf> --expect <条数>          # 批注 pdf 侧（需 pymupdf）
python scripts/check_revisions.py --input <修订稿.docx> --mode revise --expect N # 修订稿（Word 修订模式稿）
python scripts/check_revisions.py --input <修订稿_clean.docx> --mode clean       # 修订稿（干净版）
```

- 批注检查项：comments 条数 == cs/ce/ref 对数、每条 4 段无空行、标签/标题整行加粗、引导词加粗正文常规、编号前缀∈{J,L,I,Z}且唯一、CommentText/CommentReference 样式、Content_Types/rels 注册
- 修订稿检查项（revise 版）：ins==del 对、author 归责、id 成对唯一、delText/ins 非空、settings 开 trackRevisions、clean 化后 ins 文本落定；clean 版：无修订标记残留
- **任一 FAIL → 退回 `ibd-doc-annotate` 重新注入/生成，不交付**

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

**批注复核规范**（交付形态双轨 / 4 行紧凑结构 / 编号体系 / 类型词表 / 字体 / 锚点规则 / 校验门禁）见 [annotations.md](references/annotations.md)；**修订稿交付规范**（三模式 / rev 字段 / 修订落定 / 修改清单 / 校验门禁）见 [revisions.md](references/revisions.md)——批注与修订稿复核的**格式单一事实源**；执行器（批注注入 + 修订稿生成）= `ibd-doc-annotate` skill。

## 依赖与工具

> **本 skill 完全独立**——不依赖多角色团队、不依赖特定知识库，任何人可直接使用。

| 维度 | 说明 |
|---|---|
| 🔴 **必须** | 任一 docx 处理工具（`minimax-docx`〔🟨官方市场〕 或 `tencent-docx`〔🟦内置〕至少一，套样式/新建用）+ 内置脚本 `check_styles.py` / `check_content.py` / `check_annotations.py` / `check_revisions.py`〔⬛随包自带，零依赖〕 |
| 🟡 **推荐** | `tencent-local-office-edit`〔🟦内置〕（局部样式微调，体验最佳）；模板 docx（`assets/templates/`〔⬛随包自带〕，可替换即定制样式） |
| 🟢 **可选** | 外部数据源（金融数据终端，仅交叉验证时用）；知识库后端（KB_BACKEND：知识库/云文档/本地目录任选——检索同类范例，非必需）；`officecli`（渲染层物理缺陷扫描 + OpenXML 架构校验，S6 补充门禁，独立二进制按需自备） |
| **运行模式** | 单用户直接使用；也可作为 `ibd-doc-write` 的格式层被串联调用（见「上游接口与边界」） |

### 工具说明（安装时读 · 每个工具为什么是这个层级）

**🔴 必须 · `tencent-docx`〔🟦内置〕 / `minimax-docx`〔🟨官方市场〕（docx 处理，二选一）**
- 用途：套样式（minimax-docx `apply-template`）/ 新建文档（tencent-docx `create`）
- 为什么必须：本 skill 的所有 docx 操作都建立在 docx 工具之上；**没有它无法读/写 Word 文档**，只能输出 Markdown + 样式说明

**🔴 必须 · 内置脚本（`check_styles.py` / `check_content.py` / `check_annotations.py` / `check_revisions.py`）**
- 用途：样式校验（必备样式/裸段落/空段落/跳级/内容一致）+ 格式核对 14 项（只读）+ 批注产物校验（4 段结构/加粗分布/编号/四件套，只读）+ 修订稿产物校验（ins/del 对/author/id/trackRevisions/落定证明，只读）
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
- 用途：渲染层物理缺陷扫描（`view issues`：文本溢出/首行缩进缺失/公式错误）+ OpenXML 架构校验（`validate`）；S6 补充门禁
- 为什么可选：脚本 check_styles.py 查**样式规则应用**（pStyle/裸段落/跳级），officecli 查**渲染与结构层物理缺陷**——规则检查 vs 物理扫描互补，不是替代
- 缺了会怎样：S6 门禁少一道补充维度（交付说明注明「未跑物理缺陷扫描」），核心样式流程不受影响

## 上游接口与边界

- **默认上游 = `ibd-doc-write`**（IBD 投行文档写作）：内容层产出草稿并声明样式场景（招股书版/反馈回复版）→ 交本 skill 套样式 + 校验
- **顺序规则：内容质量门禁在前、格式落地在后**——write 草稿先过 `ibd-quality-gates`（数字五要素/反模式/G1-G5 + 数值自洽门 check_data.py，md 即可跑），内容定稿后再交本 skill 套样式；套样式后跑 check_content（text/table 组，依赖样式化 docx）
- **上游开放**：本 skill 是格式层公共服务，**不限于 write 接入**——人工撰写、其他 AI 流程、外部导入的 Word 文档均可调用套样式 / 格式核对（触发词见上表）
- **批注版链路**：章节复核产出批注版原文 → 执行器 `ibd-doc-annotate` 注入（规范依据 = 本 skill [annotations.md](references/annotations.md)）→ 本 skill `check_annotations.py` 门禁 → 交付（批注版 + 精简总览双轨）；门禁归入主理人 G5 把关范围
- **下游协作**：本 skill 只改格式不改内容（铁律 0）；**内容质量（数字五要素/反模式/来源可溯）归 `ibd-quality-gates`**（内容层公共服务，上游同样开放）；格式核对中的「文档内数据自洽」与本 skill 边界见「格式核对模式」

## 踩坑记录（实测）

- **中文文件名编码**：Git Bash 向 Python/minimax CLI 传中文文件名参数可能乱码（zipfile 读 报告模板.docx 曾报 "No such item"）→ 优先用 Python `glob.glob`/`os.listdir` 遍历目录取文件，或复制为临时英文文件名再处理
- **minimax-docx 环境**：restore 必须用 csproj（.slnx 不支持 dotnet 8）；依赖华为云 NuGet 镜像
- **apply-template 语义**：把模板样式套到源文件（保留源内容换样式），不是以模板内容为基底——新建场景用 create，套用场景用 apply-template，勿混淆
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

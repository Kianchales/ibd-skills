# 使用流程细则（执行流程 · 格式核对 · 复核交付）

> 本文承接 SKILL.md「使用流程」的**执行细则**——动手做的时候翻这里。
> **分工**：SKILL.md 留「进门看什么」（场景决策树 + 样式应用铁律）；本文装「做到哪一步查什么」（S1-S7 执行流程 / 格式核对模式 / 批注与修订复核交付模式）。
>
> 本文含 3 节 + 1 张统一命令表：
> 1. 执行流程 S1-S7（样式落地主线）
> 2. 格式核对模式（`check_content.py`，只读不改文件）
> 3. 批注与修订复核交付模式（规范 + 只读校验）
> 4. 附录 · 脚本 × 场景命令表（**交付前先查这张表**）

---

## 一、执行流程（S1-S7）

**S1 识别样式场景**
- 用户明确指定（招股书版 / 反馈回复版）→ 直接采用
- 未明确 → 按文档类型推断：含"问题X."编号或【发行人说明】【中介机构核查】→ 反馈回复版；其余正式文档（含"第一节/第二节"、业务与技术、报告、备忘录等）→ 招股书版（000-009）

**S2 加载样式资产**
- 读 [style-map.md](style-map.md) 对应样式体系表
- 确认模板 docx 存在（`ls` 检查，中文文件名注意编码）
- 新建场景：确定是「以模板为基底填充」还是「从零生成后按表设置」

**S3 工具路由**
- 按 SKILL.md 决策树选择工具；调用前 ToolSearch 加载 skill / 工具 schema
- `minimax-docx` 环境备忘：依赖 .NET SDK 8 + 华为云 NuGet 镜像；`apply-template` 前先 `dotnet restore MiniMaxAIDocx.Cli/MiniMaxAIDocx.Cli.csproj --source https://repo.huaweicloud.com/repository/nuget/v3/index.json`

**S4 样式映射（核心）**
按 [style-map.md](style-map.md) 将内容段落映射到 pStyle：

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
- 标题序号九级链 + 「序号段落判定（标题 vs 正文，双维度算法）」→ [rules.md](rules.md) 第一节
- 表格三线表规范（框线/字号/对齐/tblHeader/合计加粗）→ [rules.md](rules.md) 第二节

**S6 校验门禁**
- **交付前综合核验（推荐先跑这一条）**：`python deliver_gate.py --docx <交付件.docx> --md <内容源.md> --anchors "36,507.55;19.96" --scenario 反馈回复 --expect-vmerge N` —— 基础九项一次跑完、只输出「一行一指标」，**PASS 不展开、FAIL 才给明细**；退出码 0/1 直接作交付判据。`--ban` 可省略（默认启用内置投行禁用词红线 13 词），`--anchors` 用**分号**分隔（数字含千分位逗号，勿用逗号）。需要全量明细再单独跑 check_styles / check_content
- **复核产物交付（批注版/修订版）在九项之上加开关**：批注版 `--annotated [--expect-annotated N]`（追加 批注部件/批注结构/批注编号）、修订版 `--revised [--expect-revised N]`（追加 修订成对/修订落定/修订计数），均为十一项；两开关**互斥**、且必须配 `--docx`。带 `--annotated` 时 `check_annotations.py` 的 docx 侧断言已全覆盖（PDF 侧高亮注释仍需单独跑）；带 `--revised` 时 `check_revisions.py --mode revise` 的断言已全覆盖（**含落定证明**），`--mode clean` 的「无残留」判据用 `--revised` 时 ins/del 计数为 0 即等价成立
- 成品文档校验：`python check_styles.py --input <docx或目录> --scenario <招股书|反馈回复>`（脚本位于本包 scripts/）（`报告` 为 `招股书` 别名，兼容旧调用；默认 `--mode document`）
- 模板/样式库校验：`--mode template`（检查 styles.xml 中 000-009 / 0011+001 / a4-a6 是否齐全；模板正文为空属正常，勿用 document 模式误判）
- 内容完整性校验：`--verify-content <原文.docx>`（套样式后文本与原文逐字对比，严禁修改原文内容）
- 序号段落核对：`--check-numbering`（列出序号开头段落及上下文，辅助标题/正文判定）
- 格式修改清单：`--diff <原文.docx>`（对比样式化结果与原文，生成格式问题清单 + 修改统计，详见 S7）
- 修订稿生成：`--revise <原文件.docx>`（基于原文件生成 Word 修订稿：格式改动转为 w:pPrChange 修订 + trackChanges，详见 S7）
- 检查项：必备样式已应用（000 + 场景一级：招股书 001 / 反馈回复 0011+001）、无裸正文段落、无空段落（段落间禁止空行）、标题层级无跳级
- `minimax-docx apply-template` 自带 XSD 校验门禁（防损坏）
- **补充门禁（officecli 驱动 · 软门禁不卡流程；承接 ibd-quality-gates 原 G6 语义——内容层 0.6.0 起不再持有 officecli，docx 物理扫描统一在本节）**：
  - **一条命令挂进 deliver_gate**：`python scripts/deliver_gate.py --docx <件> --officecli [--officecli-path P] [--expect-issues N]` —— 追加「物理扫描」一项（共十项）
  - 底层两个动作：架构校验 `officecli validate <docx>`（OpenXML schema 合法性，防文件损坏/Word 打不开）+ 渲染层缺陷扫描 `officecli view <docx> issues`（文本溢出、正文首行缩进缺失、公式错误等物理缺陷）
  - **三态语义**：未加 `--officecli` → `[SKIP] 未启用`；加了但没装 officecli → `[SKIP] 未找到`——**两种 SKIP 都不阻断交付**（不计入退出码、不计入 PASS 率），但**都会在输出里显式可见**——这样「未跑物理扫描」不再靠人记
  - **哪些算 FAIL**：架构校验不通过，或渲染缺陷数 > `--expect-issues`（默认 0）→ 返回 S4/S5 修正后重跑
  - 探测顺序：`--officecli-path` → PATH → `~/.officecli/` 等平台常见位置（自定义安装目录可用环境变量 `OFFICECLI_HOME` 指定）
- **任一不符 → 返回 S4/S5 修正后重跑，不交付**

**S7 交付与声明（三件套交付物）**
格式修改任务（已有 docx 套样式/改格式）交付**三件套**：
1. **修订稿**（docx，Word 修订格式）：基于**原文件**生成，所有格式改动以 `w:pPrChange`（格式更改修订）标记，并开启 `trackChanges`——Word 打开后在审阅面板逐条查看，可接受/拒绝。生成：`check_styles.py --input <样式化结果.docx> --revise <原文件.docx>`（输出 `<原文件>_修订稿.docx`，`--output` 可指定路径）
2. **格式问题清单**（md）：`check_styles.py --diff <样式化结果.docx> <原文.docx>` 自动生成 `<样式化结果>_格式修改清单.md`——逐条列出**位置、原文、改成什么**（段落位置 + 原样式 → 新样式；空段落删除单列）
3. **修改统计**：清单内「修改统计」表——总段落数、修改段落合计、标题样式/正文样式/空段落删除/表格、文本内容一致性
- 交付说明：交付物路径 + 样式应用情况声明（"已按招股书版 000-009 样式生成/套用" 或 "已按反馈回复版样式套用"）
- 若从零生成，必须声明"已按报告模板 000-009 样式生成"
- 样式未全覆盖处列出清单（哪些段落待人工复核）

---

## 二、格式核对模式（check_content.py，只读不改文件 · 分组框架）

> 敏感词/地理表述清单见 [sensitive_terms.json](sensitive_terms.json)（--geo-file 驱动，可扩展维护）。

触发：「核对格式」「格式自查」「投行格式核对」「检查序号/日期/标点/表格样式」「文件质量核查」等**只读审查类请求**。适用于任意投行 Word 文档（中性通用规则）。数值自洽核对（金额文本格式/数值前后一致/勾稽）请用 `ibd-quality-gates` 的 check_data.py（md/docx 双载体）。

```bash
python scripts/check_content.py --input <docx>                          # 全部核对项（样式化 docx：text+table）
python scripts/check_content.py --input <docx> --checks text            # 只查文字规范组
python scripts/check_content.py --input <docx> --checks table           # 只查表格样式/结构组
python scripts/check_content.py --input <docx> --checks geo,table_na    # 指定子项
```

> **模块结构（2026-09-11 拆组，P2-⑧）**：`check_content.py` 是唯一 CLI 入口，按业务域分为三配套模块——`content_common.py`（共享基础层：Issue / docx 解析 / 中文序号基元 / 标点基元）、`content_text.py`（文字类 7 项）、`content_table.py`（表格类 4 项）。组名 `text`/`table` 与模块边界一一对应；**扩展新核对项时只动对应域文件**。三模块须与入口同目录（入口内为绝对 import）；对外参数/报告名/退出码不变。

**两大组别 × 严重程度矩阵**（HIGH=错误须改 / MEDIUM=警告大概率改 / LOW=提示人工酌情；docx 载体）：

| 组别 | 核对项 | 默认严重度 | 判定逻辑 |
|------|--------|-----------|---------|
| **文字类 text** | 标题层级序号连续性（跳号/重号/倒退；支持第X节/第X章、问题X 自定义编号，级别高于「一、」；中文数字一~九十九） | HIGH | 层次感知算法：同层递增+1，降层重起，升层按自身序列续 |
| | 用词规范性（错别字/异形词，内置规则可经 term_rules.json 扩展） | MEDIUM | 内置+外部清单正则扫描 |
| | 日期写法统一（十种形式：中英、年月/年月日、连写、分隔符等） | MEDIUM | 形式占比统计→主导写法判定→少数派明细；分隔符一致性 |
| | 多余空格/数字前后空格/重复标点 | HIGH | 中文间双空格、**中文与数字之间空格（数字前后不加空格，见 rules.md 三·3）**、全角标点叠用、半角标点连打、中英混排 |
| | 释义简称统一（冲突/前置使用/疑似未定义复用/引号风格） | MED-LOW | 定义对提取+前后位置比对+括号短语频次分析 |
| | 国家城市表述合规（--geo-file 外部敏感词清单驱动） | HIGH | 清单命中即报，出现次数与首现上下文 |
| **表格类 table** | 字号体系：全表五号（10.5pt），放不下可用小五（9pt），其余违规 | HIGH | 单元格 w:sz 扫描（21/18 合法） |
| | 表格数字右对齐 | MEDIUM | 数值单元格段落 jc 校验 |
| | 空单元格 | LOW(提示) | 空单元格统计（不计入问题数；已排除 vMerge 续格） |
| | 「不适用」标记符号同表内统一性 | MEDIUM | —/-//不适用/N.A. 分类计数 |

交付：`<input>_格式核对报告.md`——核对总览矩阵（组别×严重度）+ 按 HIGH/MEDIUM/LOW 三级分块的逐条明细（核对项/位置/原文/问题/建议）。控制台输出错误/警告/提示三级汇总。**只读核对，不改文件**。

**边界**：本模式查的是**文字/表格自洽与样式规范**（序号连续性/简称日期写法统一/表格字号对齐/空与 NA 标记），属格式层核对；**数值自洽**（金额文本格式/数值前后一致/合计勾稽/跨表比对）已于 2026-09-06 迁 `ibd-quality-gates` 的 check_data.py（md/docx 双载体，写作链 md 阶段前置跑）；**内容质量与来源可溯**（每个数字有没有出处、判断有没有依据、是否说过头话）同样归 `ibd-quality-gates`。三类可**串联执行**：先过 gates（内容/溯源 + 数值自洽，md 即可跑）→ 本模式查格式/自洽（docx）→ 交付；外部文档也可只调用其中一类。

---

## 三、批注与修订复核交付模式（规范 + 只读校验）

> 复核结论落到原文（用户裁定：**双轨并存、批注优先**——批注版原文 + 精简总览报告双交付物，替代原「默认只出独立审核报告」；用户明确「生成修订稿」时才走修订，按提示词区分 revise/clean/both）。**交付口径单一事实源 = [delivery.md](delivery.md)；批注规范 = [annotations.md](annotations.md)；修订稿规范 = [revisions.md](revisions.md)**。

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
# 交付前想一条命令跑完（含基础九项）→ 直接加开关，不必再单跑上面两条：
python scripts/deliver_gate.py --docx <批注版.docx> --annotated --expect-annotated N
python scripts/deliver_gate.py --docx <修订稿.docx> --revised --expect-revised N
```

- 批注检查项：comments 条数 == cs/ce/ref 对数、每条 4 段无空行、标签/标题整行加粗、引导词加粗正文常规、编号前缀（1-2 大写字母）且唯一、CommentText/CommentReference 样式、Content_Types/rels 注册
- 修订稿检查项（revise 版）：ins==del 对、author 归责、id 成对唯一、delText/ins 非空、settings 开 trackRevisions、clean 化后 ins 文本落定；clean 版：无修订标记残留
- **加粗判定须按语义**：`<w:b w:val="0">` 是**显式取消加粗**，不能只判 `<w:b>` 元素存在——否则合规批注会被误判 FAIL（实测 2026-09-11，已修 `check_annotations.py` 与 `deliver_gate.py`）
- **任一 FAIL → 退回 `ibd-doc-annotate` 重新注入/生成，不交付**
- **自测**：`python scripts/tests/test_deliver_gate.py`（17 项）/ `test_check_annotations.py`（10 项）/ `test_check_revisions.py`（11 项）/ `test_check_styles.py`（18 项）——改动脚本后务必全跑

---

## 附录 · 脚本 × 场景命令表（交付前先查这张表）

> 本表把原先分散在三处的命令块合成一处（SKILL.md 的 S6、格式核对模式、批注修订模式各有一份命令清单，内容互相重复）。**动手前先定位场景，再复制命令**。

| 你要做什么 | 命令 | 说明 |
|---|---|---|
| **交付前综合核验（首选）** | `python scripts/deliver_gate.py --docx <件> --md <源.md> --anchors "A;B" --scenario <招股书\|反馈回复> [--expect-vmerge N] [--officecli]` | 基础九项一次跑完、只输出结论行，退出码 0/1 作交付判据；加 `--officecli` 追加物理扫描（共十项，未装则 SKIP 不阻断） |
| 交付**批注版** | `python scripts/deliver_gate.py --docx <批注版> --annotated --expect-annotated N` | 九项 + 批注三项 = 十一项 |
| 交付**修订版** | `python scripts/deliver_gate.py --docx <修订稿> --revised --expect-revised N` | 九项 + 修订三项 = 十一项（含落定证明） |
| 套样式后校验样式 | `python scripts/check_styles.py --input <docx或目录> --scenario <招股书\|反馈回复>` | 必备样式/裸段落/空段落/跳级 |
| 校验模板/样式库 | `python scripts/check_styles.py --input <模板> --mode template` | 查 000-009 / 0011+001 / a4-a6 是否齐全 |
| 证明没改原文 | `python scripts/check_styles.py --input <结果.docx> --verify-content <原文.docx>` | 逐字对比，改一个字即 FAIL |
| 出格式问题清单 | `python scripts/check_styles.py --input <结果.docx> --diff <原文.docx>` | 生成 `_格式修改清单.md` |
| 出格式修订稿 | `python scripts/check_styles.py --input <结果.docx> --revise <原文.docx>` | w:pPrChange 修订 + trackChanges |
| 序号段落核对 | `python scripts/check_styles.py --input <docx> --check-numbering` | 列序号段落及上下文 |
| **格式核对（只读）** | `python scripts/check_content.py --input <docx> [--checks text\|table\|geo,table_na]` | 十项核对，出 `_格式核对报告.md` |
| 校验批注（docx） | `python scripts/check_annotations.py --input <带批注.docx 或目录>` | 四件套/4 段无空行/加粗分布/编号 |
| 校验批注（pdf） | `python scripts/check_annotations.py --pdf <带注释.pdf> --expect N` | 需 pymupdf |
| 校验修订稿 | `python scripts/check_revisions.py --input <修订稿.docx> --mode <revise\|clean> [--expect N]` | ins/del 对/author/id/落定 |
| **改脚本后自测** | `python scripts/tests/test_deliver_gate.py` 等四份 | 共 56 项，务必全跑 |

**两条时序铁律**（写在这里，因为都是"动手前"的事）：
1. **文字规范必须在套样式之前查**——`check_content.py --checks text` 先跑（标点全角化/数字空格），再套样式。套样式后才发现文字问题会导致样式重做（实测一份交付件 384 处半角引号一路漏到套样式之后）
2. **交付前一律先跑 `deliver_gate.py`**，不要用分散的多条核验命令替代（实测同一指标被反复统计 5-8 次，输出本身成为 token 大头）

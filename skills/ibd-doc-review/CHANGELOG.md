# Changelog

## [0.15.5] - 2026-09-10

### 更新：displayName 定名「IBD 投行格式复核」（家族动词归位，改描述 = Z）

- 原「文档质检」游离于家族动词（写作/复核/校验/交付）之外且带品检味——用户裁定改「格式复核」，与财务章节复核、批注与修订复核成「复核」系
- summary 同步：去「A 股 IBD 投行」三重复（→ A 股投行）、「质检」→「格式复核」
- 包名 ibd-doc-review 不变；规则不动
- **F2 触发词冲突修复**：剔除注入意图触发词「批注复核/原位批注/复核意见打在原文」（与 ibd-doc-annotate 抢路由——本 skill 是批注规范与校验侧，注入执行归 annotate），保留规范/校验侧触发词并在 description 标注分工

## [0.15.4] - 2026-09-10

### 修复：自测过期用例同步 0.15.0 data 组迁移（CI 回归首抓，随 P1 批次）

- `scripts/tests/test_check_styles.py`：两用例仍断言 check_content 检出金额问题——data 组 09-06 已迁 ibd-quality-gates check_data.py（0.15.0），旧期望过期导致 18 用例 2 失败（本地自测长期未跑未暴露）
  - `test_content_check_heading_skip_and_amount` → `test_content_check_heading_skip`：只测标题跳号（heading_seq），断言金额不归本脚本检出
  - 新增 `test_content_amount_migrated`：`--checks amounts` 输出迁移提示（指向 gates check_data.py）且报告零金额检出——迁移行为回归锚点
  - 删除 `test_content_amount_exemptions`（豁免逻辑随 data 组迁出，回归覆盖归 gates 侧补测）
- 自测 18/18 全过；触发：P1 GitHub Actions CI 落地时首跑抓出

## [0.15.3] - 2026-09-10

### 修复：check_revisions.py 去 lxml 依赖（冷启动验证 F1）

- **`scripts/check_revisions.py` lxml → 标准库 `xml.etree.ElementTree`**：维持「内置脚本零依赖」承诺——coldstart 实测发现脚本声称零依赖但 `from lxml import etree`（消费者干净环境冷启动即 ModuleNotFoundError）；lxml 用量仅 fromstring/tostring 3 处，重写要点：
  - 深拷贝 `etree.tostring(doc)` → 加 `encoding="unicode"`（stdlib 默认 us-ascii bytes，中文/UTF-8 文档 round-trip 需显式）
  - `clean_tree` 的 `.getparent()`/`.index()`（lxml 特有，stdlib Element 无）→ 自建 `_collect()`（文档序节点列表 + id→父映射），删 del 顺序无关、解包 ins 逆序处理兼容嵌套修订对
  - 顶部 docstring「依赖：纯标准库（zipfile + lxml）」自相矛盾 → 改「zipfile + xml.etree.ElementTree」，零 pip 包
- **回归验证 4 样本全过**：合法 2 对修订 PASS / clean 稿 PASS / 坏稿三错齐报（缺 author·id 不成对·trackRevisions）/ 合法嵌套修订对 clean 化正确
- 触发：ibd-skills v0.1.0 冷启动验证（2026-09-10，报告 F1）；修复后 doc-review 4 脚本干净环境全部冷启动 OK

## [0.15.2] - 2026-09-09

### 增补：annotations.md §9 PDF 载体差异速览（同日文档补充，未 bump）

- 新增 §9「PDF 载体差异速览（Word ↔ PDF 对照）」：将 §1/§2/§5/§6/§8 中分散的 PDF 差异点（适用场景/转换禁令/锚定方式/纯文本弹注/首行前缀/颜色不承载语义/门禁差异/总览表）聚合为单节对照表——纯聚合零新规则，规范本体仍以各节为准；高亮颜色不承载语义 = annotate_pdf.py 实证行为（默认高亮色，无严重度映射）成文化
- 背景：多载体扩展规划（PDF/Excel/PPT）评估结论——规范层按「一个家多个房间」扩充，PDF 为第一个载体章节化先例

### 增补：annotations.md §3 编号体系「家族子编号」形态（复核批注数量纪律配套）

- 同根因跨位置（单锚无法就近覆盖）可共享主编号追加子字母 `J-01a/J-01b`；默认推荐形态 = 单批注 + desc 位置内联（门禁现兼容，中星微 Z-06/Z-07 先例）；家族拆分采用前须扩展 check_annotations 编号唯一性校验支持子字母尾缀（当前按纯数字序号）
- 与 ibd-finance-review 细则 9（同源合并/数量卫生）、issue-list-format §1.1（覆盖单元）、ibd-doc-annotate validate_issues（同源自检 WARN）构成批注数量纪律四端一致

## [0.15.1] - 2026-09-06

### 变更（角色表述同步：README/frontmatter 去 data 残留）

- README 能力表删 data 4 项（金额格式/指标数值一致/表格计算/跨表勾稽），原位加迁移注记指向 `ibd-quality-gates` scripts/check_data.py
- frontmatter description 与 README 概述：核对项 14 → 10（text 6 + table 4），覆盖列表去「金额格式」
- README 快速开始 `--checks text,data` → `--checks text`，补数值自洽核对 gates 指针

## [0.15.0] - 2026-09-06

### 变更（data 组迁出：check_content 回归纯 docx text/table）

- **`scripts/check_content.py` 删除 data 组**（amounts/consistency/calc/cross_table + _to_num/_is_percent_after/金额正则/METRIC_VAL_RE）——整体迁 `ibd-quality-gates` scripts/check_data.py（归属归位：数值自洽属内容层关切），脚本 1473 → 1124 行
- **删除 md 前端**（load_markdown/MD_TABLE_SEP_RE/run 分流）：md 载体随 data 组迁走，本脚本回归纯 docx 载体（text 文字规范组 + table 表格样式/结构组，样式化后跑）
- `--checks` 传入 data 组相关 id → 打印迁移提示（指向 ibd-quality-gates scripts/check_data.py）；GROUPS 去 data 键；docstring/场景E/触发词/矩阵/边界/顺序规则同步（含 table_na 严重度拼写 MEDIIUM→MEDIUM 修正）
- **金额格式拆两层**：文本格式（千分位/小数位）随 amounts 迁 gates；呈现格式（表格内对齐/字号/合计加粗）留本 skill table 组
- SKILL.md 版本对齐 frontmatter → 0.15.0

## [0.14.1] - 2026-09-06

### 变更（check_content 双载体 + G6 承接声明）

- **check_content.py 新增 md/txt 前端（load_markdown）**：docx 只是文本流+表格矩阵的一种载体——写作链 md 草稿阶段即可跑 `--checks data`（amounts/consistency/calc/cross_table），数值一致/勾稽早发现早改，无需等样式化 docx；table_font/table_align 依赖 docx 样式字段，md 下跳过（WARN 提示）；docx 路径零改动
- **S6 补承接声明**：officecli 物理扫描承接 ibd-quality-gates 原 G6 语义（内容层 0.6.0 起不再持有 officecli）
- §4 用法块补 md 载体示例行

## [0.14.0] - 2026-09-06

### 变更（批注编号前缀通用化 · 公开组合发布就绪）

- **references/annotations.md §3 去团队化**：编号前缀由「J 财务（金审言）/L 法律（钟法理）/I 行业（乔瞻远）/Z 主理人（郑知行）」固定映射 → 「复核流程自定义代号（1-2 大写字母，如 J=财务复核人），清单条目以 `code` 字段提供，规范不绑定具体人名」
- **references/revisions.md 编号引用同步**：字段表「编号体系复用：J/L/I/Z+序号」→ 「前缀由清单 `code` 字段自定义 + 前缀内序号」
- **scripts/check_annotations.py 前缀校验泛化**：`PREFIX_OK={J,L,I,Z}` 白名单删除、docx/pdf 两侧「前缀 ∈ {J,L,I,Z}」检查移除 → 前缀格式由 `LABEL_PAT`（`[A-Z]{1,2}`）约束 + 全局唯一检查保留；docstring 同步
- 严重度 `高/中/低` 与类型词表校验保留（属本 skill 规范域，门禁 = 规范执行器）；产物若缺 sev/type（annotate 侧显示「-」）→ 门禁 FAIL 促使上游补全，形成「宽松生成 → 严格把关」闭环

## [0.13.1] - 2026-09-06

### 变更（修订形态先确认 · 用户裁定）

- **references/revisions.md §1 改写**：交付形态表去掉「触发语」自动路由列（原 revise 默认 + clean/both 各自触发语），新增 ⛔ 形态先确认铁律——任何修订需求（含「直接改好」等明确措辞）先反问 `revise/clean/both` 再执行，不按措辞自动路由 mode；修订触发词统一收敛为「修订」一个入口
- 语义 A（复核修订稿）执行器 `ibd-doc-annotate` SKILL.md 同步（v0.3.1）；语义 B（check_styles.py --revise 格式修订）不受影响

## [0.13.0] - 2026-09-06

### 新增（修订稿交付规范 + 校验门禁）

- **新增 references/revisions.md**：修订稿交付规范单一事实源——三模式（revise=Word 修订模式 / clean=直接改好 / both=双版，按用户提示词区分）、问题清单 rev 字段语义（anchor 即替换范围，缺 rev=待人工）、修订落定 OOXML（w:del+w:delText 与 w:ins 同 id、author=复核人、rPr 继承锚点首 run、settings 开 trackRevisions）、修改清单格式（已修订/待人工两区）、校验门禁
- **新增 scripts/check_revisions.py**：修订稿只读校验——revise 版（ins==del 对、author 归责、id 成对唯一、delText/ins 非空、settings trackRevisions+revisionView、clean 化后 ins 文本落定证明）+ clean 版（无修订标记残留）；`--expect` 与修改清单「已修订」数比对；`--report` 写校验报告；实测演示产物 PASS
- **SKILL.md**：frontmatter description 第 4 项扩为「批注与修订」、触发词表增修订稿校验行、决策树增场景 G、章节 5 更名「批注与修订复核交付模式」并含双规范指针与双门禁命令、资源索引/依赖表/工具说明补 revisions.md 与 check_revisions.py
- **职权边界**：修订稿执行器从「待建」转现役 = `ibd-doc-annotate` `revise_docx.py`（批注/修订双形态闭环完成）

## [0.12.1] - 2026-09-06

### 改名 + 职权边界澄清（用户裁定）

- **执行器改名**：`ibd-annotate` → `ibd-doc-annotate`（SKILL.md 5 处 / annotations.md 2 处引用同步）
- **修订稿职权划出**：复核交付形态中的「修订稿」（直接改好原文文字，内容级）从本 skill 交付规范划归 `ibd-doc-annotate`（批注/修订同为其复核落地形态，修订稿执行器待建）——annotations.md §1 交付形态表删修订稿行、改注释标注归属；SKILL.md 场景 5 增「职权边界」条
- **边界澄清**：`check_styles.py --revise` 的格式修订（套样式差异转 Word 修订）属样式应用链路、留在本 skill，与复核交付无关

## [0.12.0] - 2026-09-06

### 新增（批注复核交付模式：规范 + 校验门禁）

- **交付形态升级**：2026-09-01「默认只出独立审核报告」裁定升级为「**批注版原文优先 + 精简总览报告双轨并存**」（docx→Word 批注 / PDF→高亮注释，载体自适应）；生成修订稿仍须用户明确指令
- **新增 references/annotations.md**：批注复核格式单一事实源——正文 4 行紧凑结构（无空行，标签行/标题行加粗、问题描述/建议仅引导词加粗）、编号体系（J/L/I/Z+序号，与总览报告一一对应）、10 类问题类型词表 + 高/中/低严重度、字体（宋体+TNR 10.5pt CommentText 样式）、锚点规则、docx 注入四件套、校验门禁
- **新增 scripts/check_annotations.py**：docx 侧（comments 四件套 / 条数==cs/ce/ref 对数 / 每条 4 段无空行 / 加粗分布 / 编号前缀∈{J,L,I,Z}且唯一 / CommentText+CommentReference 样式）+ PDF 侧（pymupdf 高亮条数与编号）；`--report` 写校验报告；实测演示产物 PASS
- **SKILL.md**：frontmatter description 第 4 项、触发词表、「场景F」决策树、「### 5. 批注复核交付模式」、资源索引、依赖表与工具说明、上游接口新增批注版链路
- **职责分工**：本 skill 只管规范 + 只读校验；批注注入执行器 = `ibd-annotate` skill（生成脚本在该 skill，按本 skill 规范执行）

## [0.11.0] - 2026-09-01

### 新增（officecli 整合：渲染层物理缺陷扫描 + 架构校验）

- **S6 校验门禁新增补充门禁（可选）**：`officecli validate`（OpenXML 架构合法性）+ `officecli view issues`（文本溢出/首行缩进缺失/公式错误等渲染层物理缺陷）；officecli 不可用跳过并在交付说明注明
- **依赖表新增 🟢 可选 `officecli`〔⬛开源 CLI〕**：与 check_styles.py 规则检查互补（规则 vs 物理扫描），核心流程零依赖
- **踩坑记录新增 officecli 实测 4 条**（zh-CN locale 自动识别 / 空白文档无预置 Heading1 / batch 原子回滚 / 锁隔离）

## [0.10.0] - 2026-08-29

### 重构（SKILL.md 标准化）

- **删版本备注**：标题/正文中的日期备注（运行模式/上游接口/顺序规则/S7 交付）移除，版本迭代信息只留 CHANGELOG；踩坑记录实测日期保留（实证信息）
- **标准结构重排**：定位 → 何时使用 → 使用流程（场景路由/S1-S7/铁律/格式核对）→ 资源索引 → 依赖与工具 → 上游接口与边界 → 踩坑记录
- 内容零变化，纯结构与表述调整

## [0.9.1] - 2026-08-29

### 修正（工具说明完善，安装可读）

- 依赖表新增「工具说明」：🔴 docx 工具（为什么必须有 docx 工具才能读写 Word）、内置脚本（随包零依赖）；🟡 local-office-edit、模板 assets；🟢 Wind/KB_BACKEND（核心功能不受影响）
- 每个工具标注 用途 / 为什么 / 缺了会怎样

## [0.9.0] - 2026-08-29

### 新增（独立化改造 + 依赖分层）

- **运行模式与依赖**：明确本 skill 完全独立（不依赖多角色团队/特定知识库）；🔴 必须 = 任一 docx 工具（minimax-docx / tencent-docx）+ 内置脚本；🟡 推荐 = local-office-edit、模板 assets；🟢 可选 = 外部数据源、KB_BACKEND
- **知识库后端抽象（KB_BACKEND）**：公司内部知识库 / 云文档 / 腾讯文档 / 本地任选（检索同类范例，非必需）
- 本 skill 本就零专家团/零内部知识库硬依赖，本次补依赖标注 + 独立运行说明

## [0.8.1] - 2026-08-29

### 修正（流水线顺序裁定）
- **顺序裁定**：内容质量门禁在前、格式落地在后——write 草稿先过 `ibd-quality-gates`（md 即可跑），内容定稿后再交本 skill 套样式
- check_content（文档内自洽）依赖样式化 docx，明确在套样式后跑；符合「先审内容、后定格式」行业惯例

## [0.8.0] - 2026-08-29

### 新增（上游接口契约 + 边界说明）
- **上游接口**：默认上游 = `ibd-doc-write`（内容层产出草稿声明样式场景 → 本 skill 套样式 + 校验）；**上游开放**——人工撰写、其他 AI 流程、外部导入的 Word 文档均可调用套样式 / 格式核对
- **下游协作**：内容质量（数字五要素/反模式/来源可溯）归 `ibd-quality-gates`（内容层公共服务，上游同样开放）
- **格式核对模式边界**：check_content 查文档内自洽（格式层）；内容质量与来源可溯归 quality-gates；两类检查可串联执行、互不替代

## [0.7.0] - 2026-08-27

### 重构（投行基本格式核对 v2：问题类型 × 严重程度框架）
- **CLI 变更（breaking）**：`--checks` 从数字编号改为组名/核对项 id——`text`（文字类）/ `data`（数据类）/ `table`（表格类）或具体 id（如 calc,geo）
- **严重程度三级**：HIGH=错误（须改）/ MEDIUM=警告（大概率改）/ LOW=提示（人工酌情）；报告总览矩阵与明细均按严重程度分块呈现
- **文字类新增/增强**：用词规范性（错别字变体，内置+term_rules.json 扩展）；多余空格与重复标点检出；国家城市表述合规（--geo-file 外部敏感词清单驱动）
- **数据类新增**：同名指标数值前后一致比对；表格合计行求和校验与占比列合计≈100% 校验；跨表同名科目勾稽
- **表格类新增**：字号体系核查（五号 21pt / 小五 18pt，其余违规 HIGH）；表格数字右对齐
- **日期形式扩展至十种**（含英文月缩写 Jun 2024、年月形式 2024-05、美式等）
- **简称核对增强**：定义前使用（MEDIUM）、疑似未定义复用（LOW）均在上一版本引入并纳入本框架
- 自测扩至 18 用例

## [0.6.1] - 2026-08-27

### 修正（核对规则校准）
- **金额豁免**：比例数值（数字+%）不作千分位/两位小数要求；6~8 位视为文号/编码跳过（含日期连写，由第 3 项核对处理）
- **标点规则重写为前后字符判定法**：半角标点的相邻非空字符任一侧为中文 → 应全角；全角标点两侧均为英文/数字 → 应半角；其余间隔场景默认中文标点不报。时间 13:30、编号 1.2、千分位 1,234 等不再误报
- 对象定位明确：适用于任意投行 Word 文档（中性通用规则）
- 自测扩至 17 用例（金额豁免/标点前后判定正反例）

## [0.6.0] - 2026-08-27

### 新增（投行基本格式核对，只读不改文件）
- 新增 `scripts/check_content.py`（独立于样式校验，内容级审查）六大核对项：
  1. 标题层级序号连续性（层次感知算法：跳号/重号/倒退检出，支持中文数字一~九十九）
  2. 金额数字千分位与两位小数（8 位形似日期自动标注请人工确认）
  3. 日期写法统一（四种形式占比统计 + 主导写法判定 + 分隔符一致性 + 少数派清单）
  4. 释义简称统一（同名简称多全称冲突 / 定义后全称复用提示 / 引号风格）
  5. 中英文标点混用（输出为「疑似」级供人工确认）
  6. 表格填写规范（空单元格/首尾空格/不适用符号统一性）
- 输出核对报告 md（总览表 + 分项明细：位置/原文/问题/建议），控制台同步摘要与明细
- SKILL.md 新增场景 E 与「格式核对模式」章节；README 功能特性/目录结构/校验示例同步
- 自测扩至 15 用例（新增核对器跳号/金额检出）

## [0.5.1] - 2026-08-27

### 修正（--revise 修订稿 OpenXmlValidator 实证）
- **修订模式元素名修正**：`w:trackChanges` → `w:trackRevisions`（前者在 CT_Settings schema 不存在，Word 静默忽略导致修订失效）；插入位置为 `w:bordersDoNotSurroundFooter` 之后（schema 序列 25 位置暴力测试仅此一处合法）
- **revisionView 补 `w:formatting="1"`**：否则打开文档时格式更改标记默认隐藏
- **pPrChange 快照剔除 `w:rPr`**：CT_PPrGeneral 不允许段落标记 run 属性，含则 Word 视为无效修订节点不显示
- **无 pStyle 段落插入修复**：原 replace 漏掉开标签 ">"，真实文档裸段落（有 pPr 无 pStyle）必现多余 ">"
- 踩坑记录固化（SKILL.md）：修订元素名/位置/快照、气泡缺失诊断顺序、verify-content 段落级对比
- 自测扩至 14 用例（trackRevisions 元素名/顺序、裸段落无多余 ">"、原 pPr 直接格式保留）

## [0.5.0] - 2026-08-27

### 新增
- **格式修改交付物三件套**：修正稿（改动段落黄色高亮标出）+ 格式问题清单（`check_styles.py --diff <修正稿> <原文>` 生成，含位置/原文/改成什么）+ 修改统计（段落数/标题/正文/空段落/表格/内容一致性）
- 自测扩至 12 用例（--diff 无变化 / --diff 生成清单）

### 修正
- description 去样式 ID 术语（000-009/0011/001 等改为通俗表述，面向非专业人员）
- 清理全部「裁定/日期」内部流程标注（SKILL.md/rules.md/style-map/CHANGELOG），保留规则本身与版本日期
- 介绍类文字自然化 + 分段（SKILL.md 简介、README 简介）
- 一致性修订：README 与 SKILL 同步（版本号/触发词/铁律/自测数）、S7 空行修复、去内部组织名/角色引用

## [0.4.3] - 2026-08-26

### 修正
- skillhub 重发：0.4.2 版本号被平台端占用但未公开（publish 报 VERSION_EXISTS），bump 0.4.3 确保内部闭环干净版公开

## [0.4.2] - 2026-08-26

### 修正
- **移除全部个人内部 skill 引用**（skill 内部闭环，除公开依赖外不得引用个人 skill）：删除 SKILL.md/rules.md 中对内容层个人 skill 的引用，泛化为「内容写作属内容层任务」
- **移除发布工具性内容**（版本管理/发布规范属发布工具记忆，不进 skill 本体）：删除 SKILL.md「维护与更新」章节（版本规则/隐私检查/维护表）、CHANGELOG 版本规则说明、README 版本规则段——skill 仅保留自身使用所需内容

## [0.4.1] - 2026-08-26

### 修正
- **移除分发包中的个人路径（隐私修复）**：删除「样式资产索引」中的本机绝对路径（机构内部权威源路径），泛化为「模板权威源为机构内部资产，不随包分发」

## [0.4.0] - 2026-08-26

### 新增
- **序号段落判定双维度算法**：以「（一）」「1、」「（1）」等序号开头的段落，按**段落长短 + 上下文是否分段**区分标题与正文——情况1（短标题 + 后段独立展开 → 标题样式）vs 情况2（长句列举 + 连续序号 → 000 正文）；主判据为上下文是否分段
- `check_styles.py --check-numbering`：列出全部序号开头段落及上下文与倾向判定，辅助人工核对
- 自测扩至 10 用例（情况1/情况2 区分、表格内数字豁免回归）

### 修正
- 序号核对误报修复：表格内数字/百分比豁免（78.50% 不再误判）；半角点需后跟空白（区分「1. 标题」与小数）
- **description 重写**（去 AI 味）：改为平实的技术描述（用途/样式体系/模板机制/校验/不改原文），保留触发词

## [0.3.0] - 2026-08-25

### 新增
- **内容完整性校验**：`check_styles.py --verify-content <原文.docx>`，套样式后文本与原文逐字对比（过滤合并单元格空文本），严禁修改原文内容
- **铁律 0「只改格式、严禁修改原文内容」**（最高优先级）：不得增删改移任何文字内容（含表格内文字/标点/空格/数字/单位）
- 自测扩至 8 用例（内容一致性 PASS/FAIL、表格内段落豁免回归）

### 修正
- **表格规范 v2**（表格模板.docx 内置示例表格完整实证）：
  - 宽度 100% 页宽 + Word 自动调整（`tblW 5000 pct` + `tblLayout autofit`）
  - 边框纯黑 000000（弃模板原 010000）
  - **两级表头**：组头跨列合并（gridSpan）+ 类别跨行合并（vMerge）+ 子头（金额/占比）
  - 数字右对齐、首列左对齐、合计行加粗跨列
  - 行属性：cantSplit + trHeight=397 + 行居中 + 表头行 tblHeader
  - 单元格边距 57 dxa、全表 10.5pt 垂直居中

### 模板留痕
- `assets/templates/` 模板源未更换；表格规范理解从「styles.xml 样式表」深化到「document.xml 内置示例」逐单元格实证

## [0.2.0] - 2026-08-25

### 新增
- 文档类型收敛为**两类**：招股书版（含报告/备忘录/尽调等正式文档）+ 反馈回复版
- 模板迁至 `assets/templates/`（skill-creator 标准：输出资源归 assets；**模板即样式源，替换模板即定制输出**）
- **失败降级协议**：tencent-docx → minimax-docx → 脚本兜底（标注局限）→ Markdown，逐级降级不硬撑
- `references/examples.md`：3 个典型用例全链路 + 降级示例 + 模板自定义示例
- `scripts/tests/test_check_styles.py`：自测 6 用例
- 触发词口语化补充（共 20 个）；frontmatter 加 version 字段

### 修正
- **段落间禁止空行/空段落**：间距由样式 spacing 控制，脚本内置空段落检测（自闭合+配对两种形式）

### 模板留痕
- 模板 docx 从内部模板源复制入 skill（首次打包，自包含）

## [0.1.0] - 2026-08-25

### 新增
- 初版：招股书版 / 反馈回复版 / 报告版三体系样式应用（000-009、反馈回复 0011/001 监管问题黑体）
- `scripts/check_styles.py`：成品文档校验（必备样式/裸段落/标题跳级）+ 模板样式库校验
- 样式定义全部模板 styles.xml 实证提取

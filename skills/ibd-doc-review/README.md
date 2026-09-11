<p align="center">
  <img src="https://img.shields.io/badge/IBD%20Doc%20Review-%E6%A0%BC%E5%BC%8F%E5%A4%8D%E6%A0%B8-2e6cc4" alt="ibd-doc-review">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/IBD%20%E6%8A%95%E8%A1%8C%E6%A0%BC%E5%BC%8F%E5%A4%8D%E6%A0%B8-blue" alt="displayName">
  <img src="https://img.shields.io/badge/version-0.17.3-green" alt="version">
  <img src="https://img.shields.io/badge/%E9%9B%B6%E7%AC%AC%E4%B8%89%E6%96%B9%E4%BE%9D%E8%B5%96-3776AB" alt="stdlib">
  <img src="https://img.shields.io/badge/License-MIT-blue" alt="MIT">
</p>

<h4 align="center">样式应用 · 格式核对 · 批注/修订规范与校验</h4>

## 💡 这是什么

A 股投行文档的**格式层单一事实源**：样式规范化、格式核对、批注与修订的规范与产物校验——全链路管「文件长得好不好、对不对版」，**只改格式，不改内容**。

> 套样式、查格式、验批注——三个动作一个 skill，规则只维护一份。

## ✨ 快速开始

```
「把这个 docx 按招股书版式套样式」      → 样式应用（模板驱动）
「核对一下这份文档的序号/日期/标点」     → 格式核对（10 个核对项）
「校验批注版/修订稿是否符合规范」        → 产物校验门禁
```

## 🧩 核心能力

### 🎨 样式应用
对 Word 文档套用招股书版 / 反馈回复版样式体系，适用于招股书、反馈回复、报告、备忘录、尽调报告等正式文档。样式以模板为源——**改模板 = 定制输出样式**。

### 🔍 格式核对（只读）
标题序号连续性、日期写法统一、标点全半角、释义简称、表格规范等 10 个核对项，输出按严重程度分级的问题清单（位置/原文/问题/建议）。

### 📝 批注与修订规范 + 校验
复核结论落到原文（批注/修订稿）的**格式规范单一事实源**：批注 4 行紧凑结构、编号体系、类型词表、字体、锚点规则；修订三模式、rev 字段、修订落定。配套产物只读校验门禁（check_annotations / check_revisions）——不合规即 exit 1 不交付。

> 注：批注/修订的**注入执行**（把意见打进原文）归 `ibd-doc-annotate`——本 skill 是规范与校验侧。

### 📤 章节复核交付约定
章节复核交付的**默认形态与执行链路**单一事实源（见 [references/delivery.md](references/delivery.md)）：默认「批注版原文 + ≤1 页精简总览」双轨并存、批注优先；链路 = 复核清单 → 注入 → 门禁（`deliver_gate.py --annotated/--revised`）→ 交付；含批注/修订职权划分、触发语路由、批注全量覆盖纪律。

> 注：除非明确说「生成修订稿」，不主动生成修订稿、不主动推进后续复核环节。

## 🚀 典型场景

**场景：正文定稿 → 申报格式**

内容校验过门后 → 声明样式场景（招股书版/反馈回复版）→ 套样式 → 校验内容一致性（只改格式不丢字）→ 格式核对 → 交付。

## 🔗 与生态内其他 skill 的分工

```
doc-write 写草稿 → quality-gates 内容校验 → doc-review 格式复核 → 交付
finance-review 复核清单 → doc-annotate 注入批注 → doc-review 校验批注
```

- **内容质量与数值自洽**（数字五要素/反模式/G1-G5）→ `ibd-quality-gates`
- **批注/修订执行器**（Word/PDF 原位注入）→ `ibd-doc-annotate`（本 skill 校验其产物）
- **写作草稿** → `ibd-doc-write`（引用本 skill 做格式落地）

## 📦 安装与依赖

- 🔴 **必须**：任一 docx 处理工具（tencent-docx / minimax-docx 至少一，样式套用/新建用）+ 内置校验脚本（随包自带，零第三方依赖）
- 🟡 **推荐**：本地 Office 编辑（局部微调，体验最佳）
- 🟢 **可选**：外部数据源（交叉验证）；officecli（渲染层物理缺陷扫描，独立二进制按需自备）

校验脚本全部 Python 3 标准库（zipfile + xml.etree），解压即跑。

## 📁 目录结构

```
ibd-doc-review/
├── SKILL.md              # 主文件：决策树 / 样式应用铁律 / 资源索引
├── README.md             # 本文件
├── CHANGELOG.md          # 版本记录（0.15.0+；更早见 references/changelog-archive.md）
├── assets/templates/     # 样式源模板（报告/反馈回复/表格）
├── references/           # 规范与规则（workflow/annotations/revisions/style-map/delivery 等）
└── scripts/              # 校验门禁脚本（含自测）
```

> SKILL.md 只留**常读**部分（决策树 + 铁律）；**执行细则**（S1-S7 / 格式核对矩阵 / 复核交付模式 / 命令全表）在 [references/workflow.md](references/workflow.md)。
>
> 版本记录见 [CHANGELOG.md](CHANGELOG.md)（0.15.0 起）；**0.15.0 之前的历史版本**已归档至 [references/changelog-archive.md](references/changelog-archive.md)。

## 📌 近期更新

- **2026-09-12 · v0.17.3**：**修复发布隐私门禁 BLOCK**——P1 扫描报 12 项（内部配置目录路径 ×4 ＋ 本机用户名 ×8），均为上次发布后新引入：`deliver_gate.py` 的 officecli 探测列表改为**平台通用位置**并新增 `OFFICECLI_HOME`（`--officecli-path` 仍最优先），测试夹具 `author` 改中性值；CLI 参数 / 退出码 / 三态语义零变更
- **2026-09-11 · v0.17.2**：修测试 fixture 的 OPC 关系表路径重复——构造器把包根级 rels 模板复用给 `word/_rels/document.xml.rels`，`Target` 被解析成 `word/word/document.xml`，真实解析器（python-docx）打开即 KeyError；新增 `RelsSemanticsTest` 4 项（纯标准库，校验全部 rels 的 Target 解析后必须指向包内部件；装了 python-docx 则真打开一次，未装 SKIP）。端到端：最小 fixture → 注入 → 门禁 9/9 PASS；五脚本 81 → 85 项
- **2026-09-11 · v0.17.1**：`CHANGELOG.md` 分段归档——以 0.15.0 为代际切点，0.1.0–0.14.1 共 24 个版本段迁入 [references/changelog-archive.md](references/changelog-archive.md)（46.9 KB → 29.2 KB，降 37.7%；切分前后归一化 SHA-256 一致，零丢失零新增）
- **2026-09-11 · v0.17.0**：`check_content.py` 按业务域拆组（1,146 行单文件 → 入口 268 行 + `content_common.py` / `content_text.py` / `content_table.py`，组名 text/table 与模块边界对齐，对外 CLI 契约不变）；**修复 `terms` 核对项静默失效**——内置规则因 dict 解包成键名而从未命中（与 0.15.8 加粗误判同类）；新增 `test_check_content.py` 20 项（模块结构契约 + 核对行为），五脚本共 81 项
- **2026-09-11 · v0.16.3**：`deliver_gate.py` 引入第三态 `[SKIP]` + 物理扫描常驻行——`--officecli` 把 OpenXML 架构校验与渲染层缺陷扫描并进一次核验（共十项）；未装 officecli 时输出 `[SKIP]` 且不阻断交付，让「未跑物理扫描」在输出里可见（测试 19 → 22 项）
- **2026-09-11 · v0.16.2**：数字空格规则收窄为「一律不加空格」（撤回 0.16.0 的名录条目例外，仅保留标准号中西文缩写与数字间的半角空格）；交付口径收口——annotations.md / workflow.md 不再各自复述「双轨/批注优先」，统一回指 [references/delivery.md](references/delivery.md)
- **2026-09-11 · v0.16.1**：SKILL.md 使用流程抽取为 [references/workflow.md](references/workflow.md)（主文件 20,029 → 14,708 字符，降 26.6%），决策树与铁律原样保留；新增「脚本 × 场景」命令全表（合并原先分散三处的重复命令清单）
- **2026-09-11 · v0.16.0**：格式铁律「中文/数字之间不加空格」成文 + `check_content.py` 的 `spaces` 项新增子项
- **2026-09-11 · v0.15.8**：`deliver_gate.py` 新增 `--annotated` / `--revised` 开关（九项 → 十一项，批注/修订门禁并入一次跑完）；修 `check_annotations.py` 把 `<w:b w:val="0">` 误判为加粗（合规批注被误 FAIL）；补三脚本最小测试集（四脚本共 56 项）；description 补「章节复核交付约定」能力与触发词
- **2026-09-10 · v0.15.7**：新增 `deliver_gate.py`（交付前综合核验九项 · 一次跑完 · 极简输出）；门禁前置流程固化
- **2026-09-10 · v0.15.6**：修 a6 表体字号两文件矛盾（style-map 9pt ↔ rules 10.5pt，统一为 10.5pt）；修 `check_table_empty` 不识别 vMerge 的误报
- **2026-09-10 · v0.15.5**：displayName「IBD 投行格式复核」；批注注入触发词分流归 doc-annotate
- **2026-09-10 · v0.15.4**：自测同步 data 组迁移（18 用例全过）
- **2026-09-10 · v0.15.3**：check_revisions 去 lxml → 纯标准库（冷启动修复）

## ⚖️ 许可

MIT

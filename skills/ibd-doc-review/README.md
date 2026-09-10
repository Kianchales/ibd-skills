<p align="center">
  <img src="https://img.shields.io/badge/IBD%20Doc%20Review-%E6%A0%BC%E5%BC%8F%E5%A4%8D%E6%A0%B8-2e6cc4" alt="ibd-doc-review">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/IBD%20%E6%8A%95%E8%A1%8C%E6%A0%BC%E5%BC%8F%E5%A4%8D%E6%A0%B8-blue" alt="displayName">
  <img src="https://img.shields.io/badge/version-0.15.7-green" alt="version">
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
├── SKILL.md              # 主文件：S1-S7 流程/边界/规范
├── README.md             # 本文件
├── assets/templates/     # 样式源模板（报告/反馈回复/表格）
├── references/           # 规范与规则（annotations/revisions/style-map 等）
└── scripts/              # 校验门禁脚本（含自测）
```

## 📌 近期更新

- **2026-09-10 · v0.15.7**：新增 `deliver_gate.py`（交付前综合核验九项 · 一次跑完 · 极简输出）；门禁前置流程固化
- **2026-09-10 · v0.15.6**：修 a6 表体字号两文件矛盾（style-map 9pt ↔ rules 10.5pt，统一为 10.5pt）；修 `check_table_empty` 不识别 vMerge 的误报
- **2026-09-10 · v0.15.5**：displayName「IBD 投行格式复核」；批注注入触发词分流归 doc-annotate
- **2026-09-10 · v0.15.4**：自测同步 data 组迁移（18 用例全过）
- **2026-09-10 · v0.15.3**：check_revisions 去 lxml → 纯标准库（冷启动修复）

## ⚖️ 许可

MIT

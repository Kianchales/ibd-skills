<p align="center">
  <img src="https://img.shields.io/badge/IBD%20Doc%20Write-%E5%86%99%E4%BD%9C%E6%80%BB%E5%85%A5%E5%8F%A3-2e6cc4" alt="ibd-doc-write">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/IBD%20%E6%8A%95%E8%A1%8C%E6%96%87%E6%A1%A3%E5%86%99%E4%BD%9C-blue" alt="displayName">
  <img src="https://img.shields.io/badge/version-0.8.1-green" alt="version">
  <img src="https://img.shields.io/badge/License-MIT-blue" alt="MIT">
</p>

<h4 align="center">反馈回复 · 招股书章节 · 分析报告 · 尽调报告 · 备忘录 · 财务对比表</h4>

## 💡 这是什么

A 股投行文档写作总入口。核心承诺一句话：**让 AI 写文件像投行人、不是 AI**——方法论强制引用（不引用即打回），表述套投行语言规范，输出没有 AI 腔、可以直接进复核流程的草稿。

> 你动口（「写 XX 的第一轮反馈回复」），它动笔——按问询域查方法论、套句法库、过引用自检，一条链走完。

## ✨ 快速开始

装好后对你的 AI 说一句，流水线即启动：

```
「写 XX 公司第一轮审核问询反馈回复」   → 五步方法论链路 + 引用清单自检
「写招股书『业务与技术』章节」          → 结构规范 + 投行语言
「写尽调报告的客户与供应商部分」        → 章节框架
```

> 本 skill 产出**内容草稿**；质量校验与格式落地交给下游（见分工）。

## 🧩 覆盖文档

| 类型 | 走哪套规范 | 说明 |
|---|---|---|
| 审核问询反馈回复 | response-chain.md | 五步方法论调用链路 + G4 引用自检 + 双段式结构 |
| 招股书章节 / 分析报告 / 尽调报告 / 备忘录 | doc-structures.md | 章节框架 + 结构规范 |
| 财务对比表 / 核对表（Excel） | doc-structures.md | 表格结构 |
| 以上全部 | writing-style / templates-map / context-rules | 语言句法库 / 模板映射 / 上下文管理 |

## 🚀 典型场景

**场景：一轮问询 → 申报稿**

拿问询函 → 按 28 个问询域拆问题 → 行号级定向读方法论 → 逐问起草（套投行语言、消 AI 味）→ 草稿阶段先过内容校验（数字五要素/G1-G5，md 即可跑）→ 定稿后交格式复核套样式 → 交付附引用清单。

## 🔗 与生态内其他 skill 的分工

```
doc-write 写草稿 → quality-gates 内容校验 → doc-review 格式复核/套样式 → 交付
```

- **内容质量**（数字可溯源/判断有依据/无过头话/无 AI 腔）→ `ibd-quality-gates`（质量校验）
- **格式落地**（样式/序号/表格规范）→ `ibd-doc-review`（格式复核）
- 顺序规则：内容校验在前、格式落地在后——草稿阶段过门，改稿成本最低

## 📦 安装与依赖

本 skill 为「引用外部依赖」发布，以下依赖**不随本包携带**（安装后须补齐，缺则产出未过校验的草稿）：

| 依赖 | 版本下限 | 用途 |
|---|---|---|
| ibd-quality-gates | ≥ 0.7.0 | 内容质量校验（数字五要素/G1-G5 + 数值自洽） |
| ibd-doc-review | ≥ 0.15.0 | 格式落地 + text/table 核对 |

获取途径：GitHub 集合仓库 `Kianchales/ibd-skills`（`skills/` 子目录），与获取本技能同一来源。

## 📁 目录结构

```
ibd-doc-write/
├── SKILL.md            # 主文件：路由/流程/门禁/边界
├── README.md           # 本文件
├── CHANGELOG.md        # 版本记录
└── references/         # 写作规范（按文档类型组织）
    ├── response-chain.md    # 反馈回复五步链路 + G4 引用自检
    ├── doc-structures.md    # 招股书/报告类章节框架
    ├── writing-style.md     # 投行语言词汇句法库
    ├── templates-map.md     # 模板触发映射
    ├── methods-guide.md     # 方法论库使用指引
    └── context-rules.md     # 上下文管理与降级
```

## 📌 近期更新

- **2026-09-10 · v0.8.1**：对外表述顺词（去 G4 黑话/门禁词→校验/三重复精简）；SKILL 骨架标准化
- **2026-09-09 · v0.8.0**：公开化准备完成（内部指名净化 12 处，依赖表 P3 合规）

## ⚖️ 许可

MIT

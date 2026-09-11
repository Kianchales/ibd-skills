<p align="center">
  <img src="https://img.shields.io/badge/IBD%20Finance%20Review-%E8%B4%A2%E5%8A%A1%E5%A4%8D%E6%A0%B8-2e6cc4" alt="ibd-finance-review">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/IBD%20%E8%B4%A2%E5%8A%A1%E7%AB%A0%E8%8A%82%E6%B7%B1%E5%BA%A6%E5%A4%8D%E6%A0%B8-blue" alt="displayName">
  <img src="https://img.shields.io/badge/version-0.8.4-green" alt="version">
  <img src="https://img.shields.io/badge/%E9%9B%B6%E8%BD%AF%E4%BB%B6%E4%BE%9D%E8%B5%96-3776AB" alt="no-deps">
  <img src="https://img.shields.io/badge/License-MIT-blue" alt="MIT">
</p>

<h4 align="center">16 维清单 · 锚定会计准则与监管口径 · 复核结论可直落批注</h4>

## 💡 这是什么

招股书/申报文件**财务专业内容复核**执行规范——把投行财务核查框架固化为可复用复核链路：按 16 维固定清单逐项核查财务判断与披露，产出可直接落地批注的结构化问题清单。

> 投行文档审查三层模型的**专业判断层**：管财务口径、勾稽关系、会计处理、披露充分性——不管排版、不管通用表述。

## ✨ 快速开始

```
「复核招股书『财务报表分析』章的收入与毛利率」  → 16 维清单走查 + 全量核对
「研发资本化合理吗」                             → 单点财务问题审查
「这段财务数据前后对不上」                       → 勾稽专项
```

## 🧩 核心能力

- **16 维复核清单**（check-dimensions.md）：四组走查——损益循环与税务 / 资产与投资 / 报告主体与会计政策 / 报表勾稽与披露；每维含核查要点、关注信号（命中才报问题）、主要适用规则、常见问题类型映射
- **术语与口径辨析**（term-caliber.md）：研发投入≠研发费用、归母≠净利润、合并≠母公司口径……高频混用术语对的差距与判定流程
- **监管案例信号库**（case-signals.md）：按 16 维组织的实务争议场景与监管既定口径（《案例解析 2024》《典型案例集 2022》、年报会计监管报告等）
- **执行纪律**（execution-discipline.md）：**全量核对铁律**——范围内每个财务数字必核必重算、零遗漏；分母三态还原（余额/账面价值/均值）、算式留痕、逐数台账
- **五步复核流程**：锁定范围与数据基准 → 全量核对登记 → 维度复核 → 依据检索 → 汇总问题清单

## 🚀 典型场景

**场景：招股书财务章节逐段复核 → 批注交付**

锁定章节与数据基准（审计报告为唯一事实源）→ 范围内每数必核（先机械扫、人工核语义）→ 16 维逐维问三件事：数据齐不齐、口径对不对、披露够不够 → 命中关注信号即起草问题（不硬凑）→ 清单按字段规范汇总 → 交 doc-annotate 原位批注，交付批注版原文 + 精简总览。

## 🔗 与生态内其他 skill 的分工

- **本 skill**：审查三层中的专业判断层（财务口径/勾稽/会计处理/披露）
- **格式/结构层** → `ibd-doc-review`（格式复核）
- **通用内容质量层** → `ibd-quality-gates`（质量校验）
- **复核结论落地** → `ibd-doc-annotate`（批注/修订交付）；问题清单字段（code/type/anchor）即对接协议

## 📦 安装与依赖

**零硬依赖**——纯规范 + Markdown，无脚本、无第三方包，任何能读 md 的环境即可执行复核。可选增强（有则用、无则跳过不影响交付）：数值自洽核对脚本、批注/修订工具、案例/行情数据服务。

## 📁 目录结构

```
ibd-finance-review/
├── SKILL.md                    # 主规范（定位/流程/边界）
├── README.md                   # 本文件
├── CHANGELOG.md                # 版本记录
├── LICENSE                     # MIT
└── references/
    ├── check-dimensions.md          # 16 维复核清单（四组）
    ├── execution-discipline.md      # 全量核对铁律/台账模板
    ├── term-caliber.md              # 术语与口径辨析
    ├── case-signals.md              # 监管案例信号库
    ├── interpretation-notes.md      # 准则解释判断要点（1-20 号）
    ├── issue-list-format.md         # 问题清单字段规范
    └── integration-and-fallbacks.md # 对接声明与替代管理
```

## 📌 近期更新

- **2026-09-10 · v0.8.3**：SKILL 骨架标准化（英文标题中文化、触发词/示例归位）
- **2026-09-09 · v0.8.3**：注释优先/锚点唯一教训回填 + 案例信号 +4 条

## ⚖️ 许可

MIT，见 [LICENSE](LICENSE)。

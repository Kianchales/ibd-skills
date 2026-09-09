<p align="center">
  <img src="https://img.shields.io/badge/IBD%20Quality%20Gates-%E8%B4%A8%E9%87%8F%E6%A0%A1%E9%AA%8C-2e6cc4" alt="ibd-quality-gates">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/IBD%20%E6%8A%95%E8%A1%8C%E8%B4%A8%E9%87%8F%E6%A0%A1%E9%AA%8C-blue" alt="displayName">
  <img src="https://img.shields.io/badge/version-0.8.3-green" alt="version">
  <img src="https://img.shields.io/badge/%E9%9B%B6%E7%AC%AC%E4%B8%89%E6%96%B9%E4%BE%9D%E8%B5%96-3776AB" alt="stdlib">
  <img src="https://img.shields.io/badge/License-MIT-blue" alt="MIT">
</p>

<h4 align="center">数字五要素 · 反模式扫描 · 五项判据 G1-G5 · 数值自洽</h4>

## 💡 这是什么

投行文档**交稿前的质量校验**：每个数字有来源、每句判断有依据、没有过头话、没有 AI 腔——**五项判据全过才放行**。只管内容敢不敢交出去，不管排版格式。

> 交稿前五连问：数字能溯源吗？判断有依据吗？说过头话了吗？引用对得上吗？自评达标了吗？

## ✨ 快速开始

```
「这篇能不能交」            → 全流程把关：四类检查 + 五项判据
「查查这个数有没有来源」     → 数字五要素
「扫描有没有说过头的话」     → 绝对化词表机械扫描
```

## 🧩 核心能力

| 模块 | 一句话说清 | 查什么 |
|---|---|---|
| 数字五要素 | 每个数字能答五问 | 多少/何时/哪来的/多精确/跟谁比——答不全不许留在正文 |
| 反模式扫描 | 机械 + 人工双层 | 数据类/论证类/表述类/编造类「投行文档病」 |
| 交稿前自检 10 条 | 最后过筛 | 逐条不过不交 |
| 质量自评 | 给自己打分 | 6 维 30 分，低于 25 分回炉 |
| 五项判据（G1-G5） | 逐项定放行 | 数字可溯源/无过头话/引用可追溯/依据有对照/自评达标 |

**自动化脚本**（Python 3 标准库，零第三方依赖）：

```bash
python scripts/check_gates.py 文档.md              # 反模式/绝对化/AI 痕迹机械扫描
python scripts/check_data.py --input 文档.md        # 数值自洽（金额写法/一致/勾稽/跨表）
python scripts/tests/test_check_gates.py            # 内置自测（5 用例）
```

> 脚本只查机械项；语义项（来源/口径/论证逻辑）按 antipatterns.md 人工核对——脚本替代不了人。

## 🚀 典型场景

**场景：写完了，交稿前最后一道门**

跑机械扫描（裸数字粗筛 + 过头话/AI 痕迹）→ 数值自洽核对 → 人工过反模式清单 → 自检 10 条 → 自评打分 → **低于 25 分回炉，全过才交**——质量自评报告随稿交付。

## 🔗 与生态内其他 skill 的分工

- **内容质量与数值自洽**（含机械检查）→ 本 skill
- **格式/样式/结构核对** → `ibd-doc-review`（格式复核，单一事实源）
- 在写作链的位置：`ibd-doc-write` 草稿 → **本 skill 质量校验** → `ibd-doc-review` 格式复核 → 交付

## 📦 安装与依赖

**零第三方依赖**（check_gates.py / check_data.py 仅 Python 3 标准库）。可选增强：知识库（同类案例参考）、金融数据终端（数字交叉验证）、方法论库（G4 依据对照更严）——都没有也能跑，规则全量执行。

## 📁 目录结构

```
ibd-quality-gates/
├── SKILL.md                  # 主文件：四类检查 + 五项判据
├── README.md                 # 本文件
├── CHANGELOG.md              # 版本记录
├── references/
│   ├── wordlist-absolute.txt      # 绝对化用词表（G2）
│   ├── wordlist-ai-flavor.txt     # AI 痕迹词表
│   ├── antipatterns.md            # 反模式清单（四类 21 条）
│   ├── rules.md                   # 完整规则（含 G1-G5 定义）
│   ├── task-core.md               # 动笔前准备骨架
│   └── examples.md                # 最小复现示例
└── scripts/                  # check_gates / check_data（含自测）
```

## 📌 近期更新

- **2026-09-10 · v0.8.3**：命名定稿「质量校验」（三轮迭代：门禁→把关→校验）；五项判据 G1-G5；SKILL 骨架标准化
- **2026-09-10 · v0.8.1**：SKILL 语言全量顺一遍（规则零改动）

## ⚖️ 许可

MIT

# ibd-quality-gates（IBD 投行交付质量校验）

投行文档**交稿前的质量校验**：确保文档内容在交付前达到**可信、可溯源、表述克制**的标准——管"内容敢不敢交出去"，不管排版格式。

## 适用范围

分析报告、尽调报告、反馈回复、备忘录等投行文档的内容质量检查。
格式边界：排版样式、标题序号、表格规范等格式问题归 `ibd-doc-review`；金额文本格式与数值自洽机械检查归本技能（check_data.py）。

## 两个环节

- **动笔前**：先把任务想清楚——复述任务、识别最大风险、区分已有数据与待补数据，防止理解偏差与内容编造
- **交稿前**：按五项判据（G1-G5）校验——数字可溯源、判断有依据、无绝对化表述、引用有对照、自评达标

## 五个模块

| 模块 | 一句话说清 | 查什么 |
|------|-----------|--------|
| 数字五要素 | 每个数字能答五问 | 多少/什么时候/哪来的/多精确/跟谁比——答不全的数字不许留在正文 |
| 反模式扫描 | 机械项 + 人工项双层扫 | 数据类/论证类/表述类/编造类反模式（含绝对化、AI 痕迹词表） |
| 交付前自检 10 条 | 交出去前的最后过筛 | 自查清单 |
| 质量自评量表 | 给自己打分 | 6 维 30 分自评 |
| 五项判据（G1-G5） | 逐项判定 | 见上「交稿前」 |

## 自动化脚本（Python 3 标准库，零第三方依赖）

```bash
# 反模式/绝对化/AI 痕迹机械扫描（md/txt）
python scripts/check_gates.py 文档.md

# 数值自洽核对（金额文本格式/数值一致/合计勾稽/跨表比对；md 草稿或 docx 正式稿均可）
python scripts/check_data.py --input 文档.md
python scripts/check_data.py --input 文档.docx --checks amounts,consistency

# 内置自测（直跑测试文件，5 个用例）
python scripts/tests/test_check_gates.py
```

> 脚本只查机械项；语义项（来源、口径、论证逻辑）仍需按 `references/antipatterns.md` 人工核对。

## 与生态内其他技能的分工

- **内容质量与来源可溯**（含数值自洽机械检查）→ 本技能
- **格式/样式/结构核对** → `ibd-doc-review`（格式层单一事实源）
- 在写作链中的位置：`ibd-doc-write` 草稿 → **本技能内容门** → `ibd-doc-review` 套样式 → 交付

## 安装与依赖

零第三方依赖（check_gates.py / check_data.py 仅用 Python 3 标准库）。可选增强：
- 知识库后端（KB_BACKEND）：检索同类案例做对比参考
- `ibd-doc-review`：格式/样式类问题的移交出口（可选，数值核对已内置本技能）

## 目录结构

```
ibd-quality-gates/
├── SKILL.md              # 主文件：触发词、模块、G1-G5 判据
├── README.md             # 本文件
├── CHANGELOG.md          # 变更记录
├── references/           # 词表与规则
│   ├── wordlist-absolute.txt   # 绝对化用词表
│   ├── wordlist-ai-flavor.txt  # AI 痕迹词表
│   ├── antipatterns.md         # 反模式清单（数据/论证/表述/编造）
│   ├── rules.md                # 质量规则
│   └── task-core.md            # 任务启动内核骨架
└── scripts/              # 机械扫描与数值自洽脚本（含自测）
```

## 许可

MIT

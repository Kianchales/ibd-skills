<p align="center">
  <img src="https://img.shields.io/badge/IBD%20Doc%20Annotate-%E6%89%B9%E6%B3%A8%E4%B8%8E%E4%BF%AE%E8%AE%A2%E4%BA%A4%E4%BB%98-2e6cc4" alt="ibd-doc-annotate">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/IBD%20%E6%89%B9%E6%B3%A8%E4%B8%8E%E4%BF%AE%E8%AE%A2%E4%BA%A4%E4%BB%98-blue" alt="displayName">
  <img src="https://img.shields.io/badge/version-0.5.3-green" alt="version">
  <img src="https://img.shields.io/badge/License-MIT-blue" alt="MIT">
</p>

<h4 align="center">复核结论落地执行器 · 批注版 / 修订稿双形态</h4>

## 💡 这是什么

把 A 股投行复核结论**落到文档原文上**的执行器：给一份「复核问题清单 + 原文」，产出批注版或修订稿——每条改动都锚在原问题句段、带编号可回溯。

> 纯执行器：**只做落地转化，不产生复核内容**——哪里有问题、怎么改，由上游问题清单决定；它只负责把清单变成 Word/PDF 上看得到的批注或修订。

## ✨ 快速开始

```
「把这份复核清单全部批注进原文」   → 批注版（Word 审阅批注 / PDF 高亮弹注）
「按清单出一版修订稿」              → 修订稿（先确认形态：Word 修订/直接改好/双版）
「先校验一下问题清单格式」          → validate_issues.py 入口预检
```

## 🧩 两种交付形态

| 形态 | 输入 | 输出 | 用途 |
|---|---|---|---|
| **批注版** | 问题清单 + 原文 docx/pdf | `<原文>_批注版.docx/pdf` + `_批注总览.md` | 只加批注不改原文，意见钉在问题句段上 |
| **修订稿** | 问题清单（含 rev 替换文本）+ 原文 docx | `<原文>_修订稿.docx(+_clean.docx)` + `_修改清单.md` | 修改建议落到原文：revise/clean/both 三形态 |

修订稿形态由**用户确认**（revise=Word 修订 / clean=直接改好 / both=双版），不按请求措辞自动推断。

## 🚀 典型场景

**场景：财务复核收尾 → 批注版交付**

finance-review 16 维复核产出问题清单（J-01 起编号）→ 本 skill 逐条转 Word 审阅批注锚定原句 → 复核/修订两形态同源一次生成 → 交付批注版原文 + 精简总览（无法自动锚定的条目记总览待人工）。

## 🔗 与生态内其他 skill 的分工

| 角色 | 规范（怎么算合规） | 生成（意见→批注/修订） | 校验（产物过不过关） |
|---|---|---|---|
| `ibd-doc-review`（格式复核） | ✅ 单一事实源（references/） | — | ✅ 门禁（check_*.py） |
| `ibd-doc-annotate`（本 skill） | 只引用不重复 | ✅ 执行器 | 产出送 review 门禁 |

上游问题清单格式与 `finance-review`/人工审查同源（code/type/severity/anchor/title/desc/suggestion）。

## 📦 安装与依赖

- 🔴 **必须**：Python 3 + `python-docx`、`lxml`（docx 链路）、`pymupdf`（pdf 链路）——按载体装
- 🔴 **外部依赖**：`ibd-doc-review ≥ 0.15.1`（格式规范 + 校验门禁，不随本包携带）——缺依赖时可执行注入/修订，但交付前规范校验不可用，按断链自助指引从集合仓库补齐

## 📁 目录结构

```
ibd-doc-annotate/
├── SKILL.md                  # 主文件（触发词/流程/边界）
├── README.md                 # 本文件
└── scripts/
    ├── annotate_docx.py      # Word 批注注入（跨 run 拆分、保留原格式）
    ├── annotate_pdf.py       # PDF 高亮+弹注（字符级定位）
    ├── revise_docx.py        # 修订稿执行器（revise/clean/both）
    ├── validate_issues.py    # 问题清单入口校验
    └── issues.example.json   # 问题清单模板
```

## 📌 近期更新

- **2026-09-10 · v0.5.3**：displayName「IBD 批注与修订交付」；触发词去「批注复核」歧义
- **2026-09-10 · v0.5.2**：执行器与 review 规范同源归并自检

## ⚖️ 许可

MIT License — 见 [LICENSE](LICENSE)。

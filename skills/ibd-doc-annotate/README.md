<p align="center">
  <img src="https://img.shields.io/badge/IBD%20Doc%20Annotate-%E6%89%B9%E6%B3%A8%E4%B8%8E%E4%BF%AE%E8%AE%A2%E4%BA%A4%E4%BB%98-2e6cc4" alt="ibd-doc-annotate">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/IBD%20%E6%89%B9%E6%B3%A8%E4%B8%8E%E4%BF%AE%E8%AE%A2%E4%BA%A4%E4%BB%98-blue" alt="displayName">
  <img src="https://img.shields.io/badge/version-0.12.1-green" alt="version">
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
| **批注版** | 问题清单 + 原文 docx/pdf | `<原文>_批注版.docx/pdf` + `_复核报告.xlsx`（按问题性质分表）；`_批注总览.md` 为中间件不交付 | 只加批注不改原文，意见钉在问题句段上 |
| **修订稿** | 问题清单（含 rev 替换文本）+ 原文 docx | `<原文>_修订稿.docx(+_clean.docx)` + `_修改清单.md` | 修改建议落到原文：revise/clean/both 三形态 |

修订稿形态由**用户确认**（revise=Word 修订 / clean=直接改好 / both=双版），不按请求措辞自动推断。

## 🚀 典型场景

**场景：财务复核收尾 → 批注版交付**

finance-review 16 维复核产出问题清单（J-01 起编号）→ 本 skill 逐条转 Word 审阅批注锚定原句 → 复核/修订两形态同源一次生成 → 交付批注版原文 + 复核报告 Excel（按问题性质分表；无法自动锚定的条目记总览中间件待人工）。

## 🔗 与生态内其他 skill 的分工

| 角色 | 规范（怎么算合规） | 生成（意见→批注/修订） | 校验（产物过不过关） |
|---|---|---|---|
| `ibd-doc-review`（格式复核） | ✅ 单一事实源（references/） | — | ✅ 门禁（check_*.py） |
| `ibd-doc-annotate`（本 skill） | 只引用不重复 | ✅ 执行器 | 产出送 review 门禁 |

上游问题清单格式与 `finance-review`/人工审查同源（code/type/sev/anchor/title/desc/advice|rev；契约源 `ibd-doc-review/references/interface.md` §3）。

## 📦 安装与依赖

- 🔴 **必须**：Python 3 + `python-docx`、`lxml`（docx 链路）、`pymupdf`（pdf 链路）、`openpyxl`（xlsx 链路·复核报告生成）——按载体装
- 🔴 **外部依赖**：`ibd-doc-review ≥ 0.32.0`（格式规范 + 校验门禁 + 交付口径 `delivery.md` + 复核报告（Excel）形态 §八之二；下限＝所引能力的引入版之最大值，登记表 → `ibd-doc-review/references/interface.md` §7；不随本包携带）——缺依赖时可执行注入/修订/出报告，但交付前规范校验不可用，按断链自助指引从集合仓库补齐

## 📁 目录结构

```
ibd-doc-annotate/
├── SKILL.md                  # 主文件（触发词/流程/边界）
├── README.md                 # 本文件
├── references/               # 细则分册（按需加载）
│   ├── annotate-runbook.md       # 批注注入操作规程
│   ├── revise-runbook.md         # 修订稿执行规程（revise/clean/both）
│   ├── delivery-and-gates.md     # 交付形态与门禁口径
│   ├── issues-schema.md          # 复核问题清单 schema
│   ├── examples.md               # 用法示例
│   └── ops-notes.md              # 运维与踩坑
└── scripts/
    ├── annotate_docx.py              # Word 批注注入（跨 run 拆分、保留原格式）
    ├── annotate_pdf.py               # PDF 高亮+弹注（字符级定位）
    ├── revise_docx.py                # 修订稿执行器（revise/clean/both）
    ├── review_report_to_xlsx.py      # 复核报告生成器（清单 → Excel，按问题性质分表）
    ├── issue_numbering.py            # 编号单一事实源（前缀推导 + 双字母分段）
    ├── fix_missing_ranges.py         # 后处理：补插丢失的批注 range（同段多批注冲突）
    ├── validate_issues.py            # 问题清单入口校验
    ├── issues.example.json           # 问题清单模板
    ├── report-meta.example.json      # 复核报告封面/结论元数据模板
    └── tests/
        ├── test_fix_missing_ranges.py    # 后处理脚本自测（8 项）
        ├── test_annotate_docx.py         # 批注注入自测（7 项）
        ├── test_review_report_to_xlsx.py # 复核报告生成器自测（9 项）
        └── test_validate_issues.py       # 入口校验自测（10 项）
```

## 📌 近期更新

- **2026-10-09 · v0.12.1**：**依赖下限上收至 `ibd-doc-review ≥ 0.32.0`（原 0.19.0）＋ 登记指针订正**——下限口径＝**所引能力的引入版之最大值**：本包 0.12.0 起交付**复核报告（Excel）**，其形态规格出自上游 `delivery.md` **§八之二（≥0.32.0）**，严于单入口路由语义（≥0.19.0）／类型词表 12 类与清单 `anyOf`（≥0.26.2）／三形态交付路由与深度三档（≥0.26.0）；**低于 0.32.0 时报告形态无据可依**。同步订正**过期指针**——三处所指 `interface.md` **§6 → §7**（0.26.2 新增 §5 后原 §6 顺延为 §7，指针未跟改）。三处（`SKILL.md`／`README.md`／`references/ops-notes.md`）统一；零脚本改动
- **2026-10-07 · v0.12.0**：**复核报告改 Excel 交付形态，总览 md 降为中间件**——原「批注版 + 总览 md/Word」双轨改为「批注版原文 + **复核报告 Excel**（按问题性质分工作表，人读报告）」，形态规格见 `ibd-doc-review` delivery.md §八之二。新增 `review_report_to_xlsx.py`（清单 → xlsx：封面与汇总／按性质分页／全部；`--split nature|type|code|sev`；封面**仅主标题居中**（其余标题左对齐、**所有行铺满 A:C 上下等宽**）、含**「复核声明」节**——`--meta .declaration` 落「检查／不查／特别专项／交付前将跑」四栏，**声明随报告走**）与 `issue_numbering.py`（**编号单一事实源**，批注／修订／报告三处共用，防漂移）。**撤除总览 Word 版**：删 `overview_to_docx.py` 与 `--overview-docx` 开关（旧调用显式报错、不静默失效）；总览 md 恒只产、为中间件不交付用户。清单 schema 增可选 `nature`（性质分表轴）／`line`（回复行号）。自测新增 `test_review_report_to_xlsx.py`（9 项）
- **2026-10-02 · v0.11.1**：**入口校验对齐契约**——`advice`/`rev` 改 **anyOf 条件必填**（原先无条件要 `advice`，把「文本定稿/修订」形态清单判死、且与 doc-review 的 `validate_schema.py` 结论相反）；补 `scripts/tests/test_validate_issues.py`（10 项：rev-only 回归 ＋ 契约一致性 ＋ **双校验器同输入同结论**）
- **2026-09-29 · v0.11.0**：**批注链修复三件**——①注入器段落重建改**原位保留**（同段他人批注锚点/书签/`w:tab` 兄弟 run 不再被静默删除，支持在已带批注文档上二次批注）；②既有批注内容**合并保留**＋新批注 id 接续（`comments.xml` 不再整体覆写）；③编号同前缀超 99 条**顺延双字母分段**（J-99→JA-01，序号恒两位，不再与门禁冲突）；④**总览默认只产 md**（Word 版须显式 `--overview-docx`）。新增自测 7 项，存量 8 项回归全过
- **2026-09-18 · v0.7.0**：**总览报告双格式交付（MD + Word）**——新脚本 `overview_to_docx.py`，批注注入后自动同产 `_批注总览.docx`（与 md 同源同内容）；交付口径同步 `ibd-doc-review` delivery.md
- **2026-09-18 · v0.6.1**：接入点声明入 `ATTACHMENT-POINTS` 总表——补一行**使用者资产**声明（本包**无需自备资产**，模板随包），指向集合仓总表；描述补全，规则/脚本零变化
- **2026-09-15 · v0.6.0**：**批注任务单入口路由声明**——本 skill 为 docx/PDF 批注唯一对外入口，doc-review 校验脚本转为内部回调；依赖下限升至 `ibd-doc-review ≥ 0.19.0`；
- **2026-09-14 · v0.5.6**：`fix_missing_ranges.py` 修复标记顺序颠倒——锚点落在单个 run 内时曾产出 `end→ref→start`（门禁只比对对数，会静默放行）；补 8 项自测（4 项行为 + 1 项未命中 + 1 项幂等 + 2 项顺序确证），修复前版本反跑失败 5 项
- **2026-09-12 · v0.5.5**：依赖下限同步交付口径——三处 `ibd-doc-review ≥ 0.15.1` → `≥ 0.16.2`（= `delivery.md` 引入版，原下限成死引用）
- **2026-09-11 · v0.5.4**：交付口径语义窄化修正（双轨并存·批注优先）+ 回指 `delivery.md`
- **2026-09-10 · v0.5.3**：displayName「IBD 批注与修订交付」；触发词去「批注复核」歧义
- **2026-09-10 · v0.5.2**：执行器与 review 规范同源归并自检

## ⚖️ 许可

MIT License — 见 [LICENSE](LICENSE)。

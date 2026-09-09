# ibd-doc-annotate

把 A 股投行复核结论**落到文档原文上**的执行器：给一份「复核问题清单 + 原文」，产出批注版或修订稿，每条改动都锚在原问题句段、带编号可回溯。

本技能是纯执行器——**只做落地转化，不产生复核内容**。哪些地方有问题、怎么改，都由上游问题清单决定；本技能只负责把清单变成 Word/PDF 上看得见的批注或修订。

## 两种交付形态

| 形态 | 输入 | 输出 | 用途 |
|---|---|---|---|
| **批注版** | 问题清单 + 原文 docx/pdf | `<原文>_<日期>_v<N>_批注版.docx/pdf` + `_批注总览.md` | 只加批注不改原文，复核意见钉在问题句段上 |
| **修订稿** | 问题清单（含 `rev` 替换文本）+ 原文 docx | `<原文>_<日期>_v<N>_修订稿.docx(+_clean.docx)` + `_修改清单.md` | 把修改建议落到原文：Word 修订模式（可接受/拒绝）/ 直接改好 / 双版 |

修订稿的输出形态由**用户确认**（revise / clean / both），不按请求措辞自动推断。

## 依赖

- Python 3 + `python-docx`、`lxml`（docx 链路）、`pymupdf`（pdf 链路）
- **`ibd-doc-review` skill（外部依赖·断链自助）**：本技能的格式规范单一事实源（references/annotations.md、references/revisions.md）与产物校验门禁（scripts/check_annotations.py、check_revisions.py）都在该 skill 内，本技能不重复维护、**不随包携带**。按依赖声明制发布——使用方在缺少该 skill 的环境自行下载安装即可（获取途径 = `ibd-doc-review` 同渠道发布物：GitHub 的 Kianchales/ibd-skills 集合仓库）；仅安装本技能可执行注入/修订，但交付前规范合规校验（门禁）会因缺依赖不可用，请先补齐依赖再跑门禁。**版本下限：`ibd-doc-review ≥ 0.15.1`**（下限 = 当前已验证版本，双方升版时同步更新）。

## 快速开始

```bash
# 1. 准备问题清单（格式见 scripts/issues.example.json，每条含 author/anchor/title/desc/advice；可先跑 scripts/validate_issues.py --input issues.json 入口预检；
#    修订稿条目加 rev=替换后文本，anchor 同时是替换范围；编号前缀用 code 字段自定义）

# 2. 批注版
python scripts/annotate_docx.py --docx 原文.docx --issues issues.json      # Word 审阅批注
python scripts/annotate_pdf.py  --pdf 原文.pdf --issues issues.json        # PDF 高亮+弹注

# 3. 修订稿（形态 revise/clean/both 由用户确认）
python scripts/revise_docx.py --docx 原文.docx --issues issues.json --mode revise
python scripts/revise_docx.py --docx 原文.docx --issues issues.json --mode clean
python scripts/revise_docx.py --docx 原文.docx --issues issues.json --mode both

# 4. 校验门禁（交付前必跑，位于外部依赖 ibd-doc-review——缺依赖先自行安装该 skill，见上文「依赖」）
python <ibd-doc-review>/scripts/check_annotations.py --input 批注版.docx --pdf 批注版.pdf --expect N
python <ibd-doc-review>/scripts/check_revisions.py   --input 修订稿.docx --mode revise --expect N
```

## 目录结构

```
ibd-doc-annotate/
├── SKILL.md                  # 技能说明（触发词/流程/边界）
├── scripts/
│   ├── annotate_docx.py      # Word 批注注入（跨 run 拆分、保留原格式）
│   ├── validate_issues.py    # 入口校验器（issues 结构早拦，CLI + 注入前自动校验）
│   ├── annotate_pdf.py       # PDF 高亮+弹注（字符级定位，容忍空白）
│   ├── revise_docx.py        # 修订稿执行器（revise/clean/both）
│   └── issues.example.json   # 问题清单模板
└── README.md
```

## 边界

- 只注入/修订，不重写文档：批注不改原文文字；修订只动清单指定的 anchor 区间
- 锚点覆盖复杂格式（换行/制表/超链接）或找不到时 → 记入总览/清单「待人工」，不硬撑
- 复核判断与类型词表属上游流程与 `ibd-doc-review` 规范域，本技能不做内容判断、不校验词表

## 与 ibd-doc-review 的分工

| | 规范（怎么才算合规） | 生成（把意见变成批注/修订） | 校验（产物过不过关） |
|---|---|---|---|
| ibd-doc-review | ✅ 单一事实源（references/） | — | ✅ 门禁（scripts/check_*.py） |
| ibd-doc-annotate | 只引用不重复 | ✅ 执行器 | 产出送 review 门禁 |

## License

MIT License — 见 [LICENSE.txt](LICENSE.txt)。

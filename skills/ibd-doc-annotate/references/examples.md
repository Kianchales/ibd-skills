# 使用示例（examples.md）

> 最小可复现示例：输入样例 → 命令 → 期望输出。脚本类示例均为实测通过的真实输出。

## 示例 1：复核清单合规校验（最快上手）

**输入样例**：`scripts/issues.example.json`（随包自带，含 3 条结构化复核问题）

```bash
python scripts/validate_issues.py --input scripts/issues.example.json
```

**期望输出**（实测）：

```
✅ 入口校验通过：3 条，0 ERROR
```

清单格式（code/type/severity/anchor/title/desc/suggestion 字段）见本包 SKILL.md「准备输入」与 doc-review references/annotations.md。

## 示例 2：批注版注入全链路（docx）

**输入**：原文 docx + 复核问题清单 JSON（`issues.json`）

```bash
# ① 批注注入（Word 审阅批注锚定问题句段）
python scripts/annotate_docx.py --docx 原文.docx --issues issues.json --out 批注版.docx

# ② 产物门禁校验（4 段结构/编号/加粗分布/锚定）——需 ibd-doc-review 依赖
python <ibd-doc-review>/scripts/check_annotations.py --input 批注版.docx --expect 3
```

**期望输出**：批注版.docx 内每个问题一条 Word 审阅批注，锚定在原句；门禁校验 PASS（`ins 条数与期望一致`）。

> 依赖：docx 链路需 `python-docx` + `lxml`；门禁校验需外部依赖 `ibd-doc-review ≥ 0.16.2`（断链自助指引见 SKILL.md「依赖与工具」）。

## 示例 3：修订稿生成（revise/clean/both 三模式）

```bash
# revise=Word 修订模式稿（w:ins/w:del + trackRevisions）
python scripts/revise_docx.py --mode revise --input 原文.docx --issues issues.json
# clean=直接改好的干净版
python scripts/revise_docx.py --mode clean --input 原文.docx --issues issues.json
```

修订产物用 doc-review `check_revisions.py` 校验（修订成对/author/id/落定证明）。

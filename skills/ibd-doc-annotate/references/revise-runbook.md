# 修订稿落地规程（revise-runbook.md）

> 本册是步骤 **2. 执行注入 / 修订** 中**修订侧**的详规：三形态命令、脚本自动完成事项、OpenXML 落定要点、多锚点顺序。
> **形态先与用户确认（revise／clean／both），不按措辞自动路由**；与批注同源（同一份复核问题清单）。

## 一、命令与产物

```bash
# ── 修订稿（docx；形态 revise/clean/both 由用户确认后传入 --mode，不自动路由）──
python scripts/revise_docx.py --docx <原文.docx> --issues issues.json --mode revise   # Word 修订模式（默认）
python scripts/revise_docx.py --docx <原文.docx> --issues issues.json --mode clean    # 直接改好
python scripts/revise_docx.py --docx <原文.docx> --issues issues.json --mode both     # 双版（+_clean.docx）
```

修订脚本自动完成：编号分配 → 锚点定位 → 按 rev 落定（revise 模式原文本包 `w:del`、新文本包 `w:ins`，作者=复核人，并开 `trackRevisions`）→ 修改清单生成；缺 rev/复杂 run/重叠/未锚定条目记「待人工」不硬撑。

## 二、OpenXML 落定要点

- **修订删除文本用 `w:delText` 而非 `w:t`**：w:del 内放 w:t 不是修订语义，Word 不认；ins/del 同 id 成对、author=复核人花名（可归责）
- **修订模式需开 settings `w:trackRevisions`**（元素名不是 trackChanges），合法插入位置 = `w:bordersDoNotSurroundFooter` 之后（OpenXmlValidator 实证，同 `ibd-doc-review` check_styles --revise）
- **新文本 run 继承锚点首 run rPr**：rev 文本不加粗/下划线由原文决定，不另设格式；若替换后需保留强调格式，把格式留在 anchor 覆盖的原文 run 上

## 三、多锚点顺序与重叠

- **同段多锚点按段尾→段首倒序应用**（坐标稳定）；重叠锚点靠前条转待人工

## 四、边界

- 修订链路只按 rev 有目的改写 anchor 区间（原文其余文字零改动），落定方式由 --mode 决定
- 修订链路输入限 docx（无 PDF 修订形态）

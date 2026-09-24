# 读取含修订/批注的 Word（read-docx）— 读取口径操作细则

> **适用范围**：**读**任何 docx 取正文文本时——尤其用户上传／对方提供的申报文件、审核问询回复等**很可能带修订与批注**的原件。
> **判据（单一事实源）** → `docs/CONVENTIONS.md` §一 判据集「**读取面 · 含修订/批注的 Word**」行（2026-09-24 · R-0033）。**本册只写操作细则，不复制判据正文**；口径有疑义回该行裁决。
> **边界（三条，别越界）**：
> ① 本册只管**读源件**——**产出**修订稿（写 `w:ins`／`w:del`）归 [revisions.md](revisions.md)，**产出**批注归 [annotations.md](annotations.md)；两者方向相反、互不覆盖（本册**不授权**任何写操作）。
> ② 本册管「**人／模型读源件取文本**」。包内校验脚本（`check_content.py` 等）读的是**产物**、对照物不同，**不属本册**——若日后要把同一口径扩到校验脚本，须另立判据，**不在此擅自扩面**。
> ③ 只读，**永不落笔到源文件**：不执行「接受修订／删除批注」，也不「另存一份已接受修订的副本」——**禁止写操作的理由与裁决见判据行**（本册不复制该理由）。

## 1. 三口径（探测 → 取终稿 → 标注）

| # | 环节 | 落地做法 |
|---|---|---|
| ① | **先探测** | 解包前先探三个部件：`w:ins`（插入）、`w:del`（删除）、`word/comments.xml`（批注部件）。**任一命中**即认定「该文件原件含修订/批注」，进入 ② 的终稿口径 |
| ② | **取终稿** | 一律按「**接受全部修订 ＋ 剔除全部批注**」取文本：`w:ins` 内容**计入**；`w:del` 子树**整棵排除**（含 `w:delText`）；批注**不进正文** |
| ③ | **标注** | 输出**必须**带标注头（`ins`／`del`／`comments` 三计数 ＋ 「该文件原件含修订/批注」），使下游一眼看出「所读是**终稿视角**」而**原件仍待处理** |

**为什么不能直接取段落文本**：python-docx 的 `paragraph.text` 只汇集 `w:t`，**看不出**「插入该不该算、删除该不该去、批注会不会混进来」——实测某审核问询回复原件含 `w:ins` **2,017**／`w:del` **2,979**／批注 **100**，直接取段落文本**漏 17,242 字（正文 18.5%）**，致行业／法律／财务**三线同时误判**。**漏字不报错、不告警**，是本条最贵的失败模式。

## 2. 提取脚本模板

入口 → [../scripts/extract_final_text.py](../scripts/extract_final_text.py)（零第三方依赖：`zipfile` ＋ `xml.etree`，与「解压即跑」承诺一致）

```bash
python scripts/extract_final_text.py <docx>              # 打印标注头 ＋ 终稿文本
python scripts/extract_final_text.py <docx> --check      # 只探测并标注，不出正文
python scripts/extract_final_text.py <docx> -o out.txt   # 终稿文本落盘（LF）
python scripts/extract_final_text.py <docx> --json       # 结构化元数据（ins/del/comments/chars…）
```

**自写脚本时照此实现（六条要点）**：

1. **只读打开**——`zipfile.ZipFile(path, "r")`，不写回任何部件；
2. **探测计数**——`word/document.xml` 内 `w:ins`／`w:del` 元素数 ＋ 包内是否存在 `word/comments.xml`（存在时数 `w:comment`）；
3. **取文本**——递归遍历 `w:body`：遇 `w:del` **整棵子树跳过**（含其中嵌套 `w:ins`，即「接受全部修订」语义）；只收 `w:t`；`w:tab` → `\t`；`w:br`／`w:cr` → 换行；`w:p` 收完补行尾；
4. **批注天然不进正文**——正文侧的 `w:commentRangeStart`／`w:commentRangeEnd`／`w:commentReference` 都是**空元素**，批注文本只存在于 `word/comments.xml`；无需额外排除，但**确认 `word/comments.xml` 存在时必须标注**；
5. **跳过 `mc:Fallback`**——文本框内容在 `mc:Choice`／`mc:Fallback` 里各存一份，不跳会**整段重复计入**；
6. **标注头固定四行**（源文件／探测计数与括号标记／口径说明），使输出可被机器 grep、也可被人一眼看懂。

**已知不覆盖**（如遇须人工判）：删除的**段落标记**（`w:pPr/w:rPr/w:del`）不改变段落切分；表格按单元格逐段换行、不补制表符；域代码（`w:instrText`）不收。

## 3. 加载时机

| 时机 | 读什么 |
|---|---|
| **读源件之前**（复核／核对／比对／提取数据的**前置动作**） | 本册 §1 ＋ §2——先探测再取文本，输出带标注 |
| 只做**产物校验**（[check_annotations.py](../scripts/check_annotations.py)／[check_revisions.py](../scripts/check_revisions.py)／[deliver_gate.py](../scripts/deliver_gate.py)） | **不需要本册**——那读的是**产物**，不是源件 |
| 别的包（如写作侧）也要读该口径 | **只回指针、不复制细则**（判据在 `docs/CONVENTIONS.md` §一，细则在本册） |

## 4. 测试

[../scripts/tests/test_extract_final_text.py](../scripts/tests/test_extract_final_text.py) —— **阳性 ＋ 阴性**双测：

- **阳性**：`w:ins` 计入／`w:delText` 排除；嵌套 `w:ins` 一并排除；批注不进正文；`w:tab`·`w:br` 归一化；标注计数正确；
- **阴性**：无修订/批注的文件**输出不变味**（逐行等于原文）、**不误报**标记；`--check` 不出正文；`--json` 字段齐备；`-o` 落盘为 LF；**源文件 sha256 不变**（只读证明）；坏输入 → 退出码 2。

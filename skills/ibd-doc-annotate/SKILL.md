---
name: ibd-doc-annotate
slug: ibd-doc-annotate
displayName: IBD 批注与修订复核
summary: A 股投行复核结论落到原文（Word docx / PDF）的执行器，批注与修订双形态同源：复核问题清单 + 原文 → 批注版文档 + 精简总览（只加批注不改原文），或生成修订稿（形态先与用户确认：Word 修订模式 / 直接改好 / 双版）+ 修改清单。
description: >
  本技能是「复核结论落地执行器」，承接复核交付双形态——批注与修订同源（同一份复核问题清单）：
  ① 批注版（现役）：接收结构化复核问题清单（作者/类型/严重度/锚点/标题/描述/建议）与原文
  docx 或 PDF，自动把每条问题变成一条 Word 审阅批注或 PDF 高亮注释锚定在原文问题句段上，
  并同步生成与批注编号一一对应的精简总览报告（双轨兜底：无法自动锚定的条目在总览中列出
  待人工定位）。脚本自动完成：编号分配（清单 code 字段 + 该前缀序号，脚本不内置任何
  人名/代号映射）、锚点定位（docx 跨 run 拆分且保留原格式 / PDF 字符级容忍空白）、
  批注正文 4 行紧凑排版、Word comments 四件套补全、总览生成。
  ② 修订稿（现役）：用户明确「生成修订稿」时，先与用户确认输出形态（Word 修订模式 /
  直接改好 / 双版，**不按措辞自动路由**），按问题清单的 rev 替换文本把改动落到原文，
  输出修订稿 docx + 修改清单（已修订/待人工两区）。
  触发词：「批注复核」「原位批注」「复核意见打在原文」「把审核意见做成批注」
  「批注版交付」「生成批注版」「生成修订稿」「出修订稿」「直接改好」「干净版」
version: 0.5.2
agent_created: true
---

# ibd-doc-annotate（IBD 批注与修订复核）

把复核结论**落到原文上**：给一份问题清单和一份原文（Word/PDF），产出「批注版原文 + 精简总览」，每条批注锚在问题句段、编号与总览一一对应。只加批注、不改原文一个字。

## 职权范围（复核结论落地 · 双形态）

复核交付的**执行器**，与 `ibd-doc-review`（格式规范/质检，只管规范与门禁不生成）分工：

| 形态 | 状态 | 说明 |
|---|---|---|
| **批注版原文**（docx → Word 审阅批注 / PDF → 高亮弹注） | ✅ 现役 | 只加批注不改原文 |
| **修订稿**（docx，形态先与用户确认） | ✅ 现役 | `revise`=Word 修订模式（审阅可接受/拒绝）｜`clean`=直接改好｜`both`=双版；**用户提出修订需求先反问确认形态再执行，不按措辞自动路由**；与批注同源（同一份问题清单），归属本 skill 而非 ibd-doc-review |

> 修订稿职权边界：原 `ibd-doc-review` 中「复核交付形态」的修订稿（内容级）已划归本 skill；`ibd-doc-review` `check_styles.py --revise` 的**格式修订**（套样式差异转 Word 修订）属格式层，仍留在 `ibd-doc-review`，与本 skill 无关。

## 何时使用

用户要求把复核/审查意见落到文档原文（批注或修订）时触发：

| 场景 | 触发词示例 |
|------|-----------|
| 章节复核批注交付（docx 原文） | 「复核意见打成批注」「把审核报告改成批注版」「批注打在原文上」 |
| PDF 披露稿批注交付 | 「PDF 上标注释」「高亮+批注」 |
| 批注版生成全流程 | 「批注复核」「原位批注」「批注版交付」「生成批注版」 |
| 修订稿生成（revise 默认） | 「生成修订稿」「出修订稿」「出一版修订稿」 |
| 修订稿直接改好 / 双版 | 「直接改好」「干净版」「定稿」｜「两个都要」「修订版+干净版」 |

> 配合链路：**复核问题从哪来** → `ibd-doc-review`（格式核对/审阅）或专家团分析产出问题清单；**批注格式规范** → `ibd-doc-review` 的 annotations.md、**修订稿规范** → `ibd-doc-review` 的 revisions.md（单一事实源，本 skill 只执行不另立规则）；**产出校验** → `ibd-doc-review` 的 check_annotations.py（批注）/ check_revisions.py（修订稿），交付前必跑，任一 FAIL 退回重做。
>
> ⚠️ **依赖声明（断链自助）**：`ibd-doc-review` 是本技能的外部依赖，**不随本包携带**——安装本技能后须自行另装 `ibd-doc-review`（获取途径 = GitHub 发布渠道：Kianchales/ibd-skills 集合仓库 `skills/` 子目录，与获取本技能同一来源），缺它则格式规范、校验门禁不可用（断链）。详见「依赖与工具」。

## 使用流程

> 最小复现示例（清单校验 / 批注注入 / 修订生成，含期望输出）见 [examples.md](references/examples.md)。

### 1. 准备输入

1. **原文**：Word `docx`（推荐，批注体验最佳：可回复/解决/接受拒绝）或 PDF。
   - ⛔ 招股书 PDF→docx 转换有版面失真风险，**禁止作为批注载体转换链路**；PDF 就用 PDF 批注。
2. **复核问题清单 JSON**（数组，模板见 [issues.example.json](scripts/issues.example.json)）：

```json
[
  {"author": "张敏", "code": "F", "type": "数据·正负号", "sev": "高",
   "anchor": "报告期内公司汇兑净损失为-26.14万元、187.85万元和-110.91万元",
   "title": "「汇兑净损失」负值实为净收益，正负口径与措辞相悖",
   "desc": "负值在会计口径下表示净收益，与「损失」措辞方向矛盾。",
   "advice": "核对财务报告口径后统一表述为「汇兑损益」，注明各期方向。"}
]
```

- `author` = 复核人姓名（任意，用于 Word 批注作者 / PDF 注释作者归责）
- `code` = 编号前缀（**可选**，1-2 个大写字母）：缺省 ASCII 名取首字母、中文名建议显式提供否则回退 `U`——**脚本不内置人名/代号映射**，前缀语义由复核流程自定义（如 F=财务复核人）
- `type` / `sev`：类型词表与严重度档位由 `ibd-doc-review` 的 annotations.md（§4）定义。**入口校验拦 `sev` 不在 {高,中,低}**（三档为结构枚举）；**`type` 词表不校验**（复核分类属上游内容，方法层不做内容判断、外放行，词表合规由 review 门禁把关）
- `anchor` = 原文问题句段（**精确子串**，docx 取正文/表格内段落文本；PDF 自动容忍空格/换行）
- **清单单元 = 根因问题（同源已合并）**：上游产出清单时同源连锁错误已合成一条（desc 内联全部衍生位置），本执行器**按条注入、不拆分也不合并**；一条批注 = 一个根因，覆盖语义与数量卫生（≤200 条/超 400 拆分）由上游纪律约束（见 ibd-finance-review execution-discipline 细则 9），本执行器通过 validate_issues 的 WARN 兜底提示
- **修订稿额外字段 `rev`** = 替换后新文本（anchor 同时是替换范围，须精确覆盖要改的文本）；**缺 rev → 该条列入修改清单「待人工」**，批注链路不需要 rev
- 可选 `"page": 5`（PDF 限定搜索页，1 起）

> **入口校验（自动，不注入前先拦坏清单）**：三个脚本读入清单后自动过 [validate_issues.py](scripts/validate_issues.py) 结构校验——**ERROR 级**（顶层非数组/空、条目缺 `anchor`/`type`/`sev`/`title`/`desc`/`advice` 任一、`sev` 不在 {高,中,低}）**拦截退出（exit 2）不注入**；**WARN 级**（缺 code 回退 U、code 非 1-2 位大写、缺 author、code 重复、**title 归一后重复疑似同源未合并、批注数 >200/>400 数量越级**）仅提示不拦。上游审查方（专家团/人工）生成清单后也可独立先验：`python validate_issues.py --input issues.json`（脚本位于本包 scripts/）。

### 2. 执行注入 / 修订

```bash
# ── 批注版 ──
# Word 载体（输出 <原文名>_批注版.docx + _批注总览.md）
python scripts/annotate_docx.py --docx <原文.docx> --issues issues.json [--out <输出.docx>]
# PDF 载体（--pages "5-6" 可只保留节选页；缺省保留全文）
python scripts/annotate_pdf.py --pdf <原文.pdf> --issues issues.json [--pages "5-6"] [--out <输出.pdf>]

# ── 修订稿（docx；形态 revise/clean/both 由用户确认后传入 --mode，不自动路由）──
python scripts/revise_docx.py --docx <原文.docx> --issues issues.json --mode revise   # Word 修订模式（默认）
python scripts/revise_docx.py --docx <原文.docx> --issues issues.json --mode clean    # 直接改好
python scripts/revise_docx.py --docx <原文.docx> --issues issues.json --mode both     # 双版（+_clean.docx）
```

批注脚本自动完成：编号分配（按清单顺序，作者代号+序号）→ 锚点定位 → 批注注入（正文 4 行紧凑排版）→ 总览生成。
修订脚本自动完成：编号分配 → 锚点定位 → 按 rev 落定（revise 模式原文本包 `w:del`、新文本包 `w:ins`，作者=复核人，并开 `trackRevisions`）→ 修改清单生成；缺 rev/复杂 run/重叠/未锚定条目记「待人工」不硬撑。

### 3. 校验门禁（交付前必跑）

> `<ibd-doc-review>` 为外部依赖 skill 的安装路径占位符（如 `<skills安装目录>/ibd-doc-review`，按本机技能安装位置替换）；本包不携带，缺依赖先按「依赖与工具 → 断链自助指引」安装。

```bash
# 批注版
python <ibd-doc-review>/scripts/check_annotations.py --input <批注版.docx> [--pdf <批注版.pdf> --expect <N>]
# 修订稿
python <ibd-doc-review>/scripts/check_revisions.py --input <修订稿.docx> --mode revise --expect <已修订N> [--report]
python <ibd-doc-review>/scripts/check_revisions.py --input <修订稿_clean.docx> --mode clean
```

批注 docx 侧检查：comments 条数 == cs/ce/ref 对数、每条 4 段无空行、标签/标题整行加粗、引导词加粗正文常规、编号前缀符合规范且唯一、四件套注册。
修订稿 revise 侧检查：ins==del 对、author 归责、id 成对唯一、delText/ins 非空、settings 开 trackRevisions、clean 化后 ins 文本落定；clean 侧：无修订标记残留。**任一 FAIL → 修正后重做，不交付**。

### 4. 交付物

> **命名规范（日期戳 + 轮次，G3）**：正式交付产物统一用模板 `<原文>_<YYYYMMDD>_v<N>_<形态>`（例：`佳宏新材_重大事项提示_20260906_v1_批注版.docx`），执行时用 `--out` 显式传入。轮次 N = 同一原文的第几次复核交付（首轮 v1；清单返工重交/下一遍复核升 v2…）。**同轮重跑覆盖**（同日同 vN 同形态直接覆盖，修 bug 重跑不产生新文件）；**跨轮必升 N**（旧轮产物保留可回溯，多轮对照与审计有据）。脚本默认输出简名（`<原文>_批注版.docx`）仅作快速试用，正式交付按本模板显式命名。

| 文件 | 说明 |
|---|---|
| `<原文>_<YYYYMMDD>_v<N>_批注版.docx/pdf` | 批注版第一交付物（Word 审阅面板 / PDF hover 弹注） |
| `<原文>_<YYYYMMDD>_v<N>_批注版_批注总览.md` | 双轨兜底：编号×类型×严重度×锚点摘要×作者×状态；未锚定条目列清单待人工定位 |
| `<原文>_<YYYYMMDD>_v<N>_修订稿.docx` | 修订稿（revise=Word 修订模式可审阅接受/拒绝；clean=直接改好） |
| `<原文>_<YYYYMMDD>_v<N>_修订稿_clean.docx` | both 模式另出的干净版（接受全部修订后） |
| `<原文>_<YYYYMMDD>_v<N>_修订稿_修改清单.md` | 已修订 N 条（原文 → 改为）+ 待人工 M 条（原因+建议），编号同批注体系 |

## 资源索引

| 资源 | 位置 | 归属 |
|---|---|---|
| 批注格式单一事实源（正文结构/编号/词表/字体/锚点/门禁） | `ibd-doc-review` 的 annotations.md | 🔗 外部依赖 |
| 修订稿规范单一事实源（三模式/rev 字段/修订落定/修改清单/门禁） | `ibd-doc-review` 的 revisions.md | 🔗 外部依赖 |
| 校验门禁（批注 docx+pdf / 修订稿） | `ibd-doc-review` 的 check_annotations.py / check_revisions.py | 🔗 外部依赖 |
| 问题清单模板（含 rev 字段示例） | [issues.example.json](scripts/issues.example.json) | 📦 本包 |
| 入口校验器（issues 结构早拦：CLI 独立跑 + 三脚本注入前自动校验） | [validate_issues.py](scripts/validate_issues.py) | 📦 本包 |
| 批注注入脚本（docx / pdf） | [annotate_docx.py](scripts/annotate_docx.py) / [annotate_pdf.py](scripts/annotate_pdf.py) | 📦 本包 |
| 修订稿生成脚本（docx，三 mode） | [revise_docx.py](scripts/revise_docx.py) | 📦 本包 |

> 🔗 外部依赖 = `ibd-doc-review` skill 中的资源（规范单一事实源 + 校验门禁），**不随本包分发**，须按 GitHub 发布渠道（Kianchales/ibd-skills 集合仓库）自行安装；📦 本包 = 随本技能安装自带。

## 依赖与工具

| 维度 | 说明 |
|---|---|
| 🔴 必须（Python 库） | `python-docx`、`lxml`（docx 链路）、`pymupdf`（pdf 链路）——仅用到对应载体时按需安装；Python 3 |
| 🔴 必须（skill 依赖） | `ibd-doc-review` skill：格式规范单一事实源（annotations.md、revisions.md）+ 校验门禁（check_annotations.py、check_revisions.py）均在该 skill 内，本 skill 不重复维护、不随包携带。**依赖声明制**：本 skill 按「引用外部依赖」发布——使用方在缺少 `ibd-doc-review` 的环境（断链）自行下载安装该依赖后即可完整运行；获取途径 = `ibd-doc-review` 同渠道发布物（GitHub：Kianchales/ibd-skills 集合仓库），版本兼容见该 skill CHANGELOG。**版本下限：`ibd-doc-review ≥ 0.15.1`**（下限 = 当前已验证版本；任一 skill 升版后须复核并同步下限） |
| 运行模式 | 单机直接调用；也可作为投行复核流水线（专家团/人工审查）的落地执行器 |

**断链自助指引**：若执行校验门禁报「找不到 ibd-doc-review / check_annotations.py」，说明使用环境缺外部依赖——按 `ibd-doc-review` 的 GitHub 发布渠道（与获取本技能同一来源：Kianchales/ibd-skills 集合仓库 `skills/` 子目录）自行安装即可，无需等待组合包；本技能单跑注入脚本不受影响，仅规范合规校验（门禁）依赖该 skill。

## 边界与协作

- **批注链路只加批注、不修改原文文字**；修订链路按 rev 有目的改写 anchor 区间（原文其余文字零改动），落定方式由 --mode 决定
- **docx 锚定范围**：正文段落 + 表格单元格段落；锚点覆盖复杂 run（含换行 `w:br`/制表 `w:tab`/多 `w:t`）或骑跨超链接/页眉页脚 → **不自动处理**，记入总览「未锚定」或修改清单「待人工」（人工定位），不报错不硬撑
- **格式规则不在此重复**：本 skill 的产出必须符合 `ibd-doc-review` 的 annotations.md（批注）与 revisions.md（修订稿）；规范有更新只改那一处，两 skill 交接以它为合规依据
- **上游开放**：复核问题清单可来自任何审查流程（投行专家团分析、`ibd-doc-review` 格式核对、人工复核等）；本 skill 只做交付形态转化，不产生复核内容

## 踩坑要点（实测）

- **pymupdf 页对象须持有引用**：`page = doc[pno]` 后再 `add_highlight_annot`，内联 `doc[pno].add_highlight_annot(...)` 的页代理被 GC 会报「annotation not bound to any page」
- **跨 run 锚定**：docx 锚点常横跨多个 run——脚本按字符坐标把 run 切成片段（首片段复用原元素、其余深拷贝保留 rPr），段落文本零改动；含 `w:br/w:tab` 的 run 判定为复杂 run 不自动切
- **批注内禁空行段**（用户裁定）：4 行紧凑，边界靠加粗引导词；不要插空 `<w:p/>`
- **修订删除文本用 `w:delText` 而非 `w:t`**：w:del 内放 w:t 不是修订语义，Word 不认；ins/del 同 id 成对、author=复核人花名（可归责）
- **修订模式需开 settings `w:trackRevisions`**（元素名不是 trackChanges），合法插入位置 = `w:bordersDoNotSurroundFooter` 之后（OpenXmlValidator 实证，同 `ibd-doc-review` check_styles --revise）
- **新文本 run 继承锚点首 run rPr**：rev 文本不加粗/下划线由原文决定，不另设格式；若替换后需保留强调格式，把格式留在 anchor 覆盖的原文 run 上
- **同段多锚点按段尾→段首倒序应用**（坐标稳定）；重叠锚点靠前条转待人工
- **同段多批注互相清除 range（实测 2026-09-06）**：主循环逐条注入时，同段落后续批注的段落重建会删除先前已插入的 `commentRangeStart/End`，导致 comments.xml 有批注但 document.xml 丢 range（check_annotations 报 cs/ce/ref 对数 < 批注数）。修复：跑 `fix_missing_ranges.py <docx> <issues.json>`（本包 scripts/ 下）后处理补插（按 issues.json 锚点重定位切 run 插 range），补完重跑门禁；交付前门禁必过
- **编号一次性分配**：批注/修订稿/总览共用同一编号，禁止生成后再改顺序
- **复杂 run 检测为兜底而非缺陷**：真实申报稿正文多为简单 run，自动处理率高；少量兜底条目人工定位后如需批注/修订可手工加或扩清单重跑

## 维护

- 版本变更记录见 [CHANGELOG.md](CHANGELOG.md)；格式规则变更只改 `ibd-doc-review` 的 annotations.md 与 revisions.md

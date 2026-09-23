# 包内非流程详规（ops-notes.md）

> 本册收 **定位简介／边界与协作／依赖与工具／维护** 四节的原文详规，以及**踩坑全文的分布索引**。
> 这些是「**触发后按需查**」的信息，不属流程导航，故不在 `SKILL.md` 正文铺开——各节在 `SKILL.md` 保留「一句话浓缩 ＋ 指向本册的指针」。

## §定位（复核落地 · 双形态）

复核交付的**执行器**，与 `ibd-doc-review`（格式规范/质检，只管规范与门禁不生成）分工：

| 形态 | 状态 | 说明 |
|---|---|---|
| **批注版原文**（docx → Word 审阅批注 / PDF → 高亮弹注） | ✅ 现役 | 只加批注不改原文 |
| **修订稿**（docx，形态先与用户确认） | ✅ 现役 | `revise`=Word 修订模式（审阅可接受/拒绝）｜`clean`=直接改好｜`both`=双版；**用户提出修订需求先反问确认形态再执行，不按措辞自动路由**；与批注同源（同一份问题清单），归属本 skill 而非 ibd-doc-review |

> 修订稿职权边界：原 `ibd-doc-review` 中「复核交付形态」的修订稿（内容级）已划归本 skill；`ibd-doc-review` `check_styles.py --revise` 的**格式修订**（套样式差异转 Word 修订）属格式层，仍留在 `ibd-doc-review`，与本 skill 无关。
>
> **交付口径**（默认交付形态 / 触发语路由 / 批注与修订职权划分 / 批注全量覆盖纪律）= `ibd-doc-review` skill 的 **delivery.md**——本 skill 是执行器，口径不另立、不重复维护。

## §边界与协作

- **批注链路只加批注、不修改原文文字**；修订链路按 rev 有目的改写 anchor 区间（原文其余文字零改动），落定方式由 --mode 决定
- **docx 锚定范围**：正文段落 + 表格单元格段落；锚点覆盖复杂 run（含换行 `w:br`/制表 `w:tab`/多 `w:t`）或骑跨超链接/页眉页脚 → **不自动处理**，记入总览「未锚定」或修改清单「待人工」（人工定位），不报错不硬撑
- **格式规则不在此重复**：本 skill 的产出必须符合 `ibd-doc-review` 的 annotations.md（批注）与 revisions.md（修订稿）；规范有更新只改那一处，两 skill 交接以它为合规依据
- **上游开放**：复核问题清单可来自任何审查流程（投行专家团分析、`ibd-doc-review` 格式核对、人工复核等）；本 skill 只做交付形态转化，不产生复核内容

## §依赖与工具

| 维度 | 说明 |
|---|---|
| 🔴 必须（Python 库） | `python-docx`、`lxml`（docx 链路）、`pymupdf`（pdf 链路）——仅用到对应载体时按需安装；Python 3 |
| 使用者资产 | **无需自备**——任务输入 = 原文 docx/PDF + 复核问题清单 JSON（模板随包），不依赖方法论库 / KB 后端；接入点总表见 ibd-skills 集合仓 `ATTACHMENT-POINTS.md` |
| 🔴 必须（skill 依赖） | `ibd-doc-review` skill：格式规范单一事实源（annotations.md、revisions.md）+ 校验门禁（check_annotations.py、check_revisions.py）均在该 skill 内，本 skill 不重复维护、不随包携带。**依赖声明制**：本 skill 按「引用外部依赖」发布——使用方在缺少 `ibd-doc-review` 的环境（断链）自行下载安装该依赖后即可完整运行；获取途径 = `ibd-doc-review` 同渠道发布物（GitHub：Kianchales/ibd-skills 集合仓库），版本兼容见该 skill CHANGELOG。**版本下限：`ibd-doc-review ≥ 0.19.0`**（0.6.0 起对齐单入口路由语义引入版——旧版 interface.md 仍声明 PDF 侧直接调用，与本 skill 单入口契约冲突；低于此版须升依赖。**下限登记 → `ibd-doc-review/references/interface.md` §6**。任一 skill 升版后须复核并同步下限） |
| 运行模式 | 单机直接调用；也可作为投行复核流水线（专家团/人工审查）的落地执行器 |

**断链自助指引**：若执行校验门禁报「找不到 ibd-doc-review / check_annotations.py」，说明使用环境缺外部依赖——按 `ibd-doc-review` 的 GitHub 发布渠道（与获取本技能同一来源：Kianchales/ibd-skills 集合仓库 `skills/` 子目录）自行安装即可，无需等待组合包；本技能单跑注入脚本不受影响，仅规范合规校验（门禁）依赖该 skill。

## §维护

- 版本变更记录见 `CHANGELOG.md`；格式规则变更只改 `ibd-doc-review` 的 annotations.md 与 revisions.md
- 自测：`python scripts/tests/test_fix_missing_ranges.py`（后处理脚本 8 项；须装 python-docx，未装则整类 SKIP）

## §踩坑全文分布（按主题归册，不重复维护）

| 踩坑条目 | 落点 |
|---|---|
| pymupdf 页对象须持有引用 | [annotate-runbook.md](annotate-runbook.md) §三 |
| 跨 run 锚定（复杂 run 不自动切） | [annotate-runbook.md](annotate-runbook.md) §二 |
| 批注内禁空行段（4 行紧凑） | [annotate-runbook.md](annotate-runbook.md) §四 |
| 编号一次性分配 | [annotate-runbook.md](annotate-runbook.md) §四 |
| 同段多批注互相清除 range（fix_missing_ranges） | [annotate-runbook.md](annotate-runbook.md) §五 |
| 表格型文档锚点选唯一数值 | [annotate-runbook.md](annotate-runbook.md) §六 |
| 复杂 run 检测为兜底而非缺陷 | [annotate-runbook.md](annotate-runbook.md) §二 |
| 修订删除文本用 `w:delText` | [revise-runbook.md](revise-runbook.md) §二 |
| settings 开 `w:trackRevisions`（含插入位置） | [revise-runbook.md](revise-runbook.md) §二 |
| 新文本 run 继承锚点首 run rPr | [revise-runbook.md](revise-runbook.md) §二 |
| 同段多锚点倒序应用／重叠转待人工 | [revise-runbook.md](revise-runbook.md) §三 |

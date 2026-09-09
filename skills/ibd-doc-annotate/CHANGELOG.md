# Changelog

## [0.5.2] - 2026-09-09

### 文档更新（2026-09-10 · 未 bump）：新增 references/examples.md（最小复现示例），SKILL.md 使用流程补引用

- examples.md：对话触发/命令/期望输出，脚本类示例为实测输出；doc-review 既有 examples.md 同步补入门指引句

### 增强：validate_issues 同源归并自检 + 数量卫生阈值（配套复核纪律细则 9）

- validate_issues.py 新增两个 WARN：①title 归一后重复 → 疑似同源未合并（应合一条 desc 内联位置，或作家族子编号）②批注数 >200 提示自查归并、>400 提示拆分交付（云端协同红线前）——拆/并不删条目
- SKILL.md 声明清单单元 = 根因问题（同源已合并，按条注入不拆不合），覆盖语义/数量卫生归上游纪律（ibd-finance-review execution-discipline 细则 9），执行器以 WARN 兜底提示

## [0.5.1] - 2026-09-06

### 变更（G3 · 产物命名规范：日期戳 + 轮次）

- SKILL.md §4 交付物命名统一为 `<原文>_<YYYYMMDD>_v<N>_<形态>`（首轮 v1，跨轮升 N 旧产物保留可回溯；同轮同 vN 重跑覆盖）；脚本 `--out` 显式命名，默认简名仅供快速试用
- README 产物表与目录结构同步（补 validate_issues.py 登记）

## [0.5.0] - 2026-09-06

### 新增（G1 · 复核链入口校验）

- 新增 `scripts/validate_issues.py` 入口校验器：ERROR 级（顶层非数组/空、缺 anchor/type/sev/title/desc/advice、sev 不在 {高,中,低}）拦截 exit 2；WARN 级（缺 code 回退 U、code 非 1-2 位大写、缺 author、code 重复）仅提示。支持 CLI 独立跑（上游生成即校验）+ import 复用
- `annotate_docx.py` / `annotate_pdf.py` / `revise_docx.py` 注入前自动校验，坏清单不再等到注入/门禁才暴露
- SKILL.md §1 校验行为表述对齐（sev 枚举拦、type 词表外放行）、§2 入口校验说明、资源索引登记

### 修复

- `annotate_docx.py` write_overview：MISS 条目原样 append 丢 `reason` 键 → 只要有 1 条未锚定即 KeyError 崩溃（未锚定兜底失效）；改 `{**it, "reason": reason}`，未锚定清单正常渲染（冒烟：错配原文 3 条 MISS 正确出未锚定总览 exit 0）

## [0.4.2] - 2026-09-06

### 变更（G2 · 依赖版本下限）

- SKILL.md 依赖表 + README 依赖节补版本下限：`ibd-doc-review ≥ 0.15.1`（下限 = 当前已验证版本，任一 skill 升版后须复核并同步）

## [0.4.1] - 2026-09-06

### 变更（依赖声明制落地 · 用户裁定：组合包载体以后再说）

- **发布形态改「依赖声明制」**：撤销「组合发布、与 ibd-doc-review 同包携带」表述——`ibd-doc-review` 改为**外部依赖**，本 skill 独立发布、不随包分发；使用方在缺依赖环境（断链）**自行下载安装该 skill** 后即可完整运行（获取途径 = 同渠道发布物：skillhub / GitHub）
- **SKILL.md**：配合链路增 ⚠️ 依赖声明框；§3 校验门禁补 `<ibd-doc-review>` 占位符说明 + 顺带清除残留前缀 `{J,L,I,Z}` 表述；资源索引表增「归属」列（🔗 外部依赖 / 📦 本包）；依赖与工具表拆分 Python 库 / skill 依赖两行并新增「断链自助指引」
- **README.md**：依赖节同步改声明制（外部依赖·断链自助），快速开始 §4 注释补依赖提示
- 脚本零改动（纯发布形态与文档表述变更）；门禁回归不受影响

## [0.4.0] - 2026-09-06

### 变更（模块化 / 公开组合发布就绪 · 用户裁定）

- **脚本纯方法化（去团队内情 + 去规范重复）**：删除 `AUTHOR_CODES` 团队人名映射与 `TYPE_WORDS`/`SEV_WORDS` 词表常量——编号前缀改由清单 `code` 字段提供（缺省 ASCII 复核人名取首字母、中文名回退 `U` 并提示）；类型/严重度词表归 `ibd-doc-review` references/annotations.md §4 定义，脚本不校验不维护（复核分类属上游清单内容）；`assign_numbers` 改结构必填校验（author/anchor/title）+ type/sev 缺省「-」显示兜底；三脚本 docstring 同步
- **SKILL.md 语境泛化 + 隐私清理**：删除隔离 venv 绝对路径；上游表述改为「任何审查流程（专家团/人工复核等）」开放；示例与输入说明去团队花名、增 `code` 字段；依赖从「🟡 推荐」升级「🔴 必须 `ibd-doc-review`（组合发布同包携带，规范单一事实源 + 校验门禁）」；资源索引注明依赖关系
- **补齐 0.3.1 未落盘的 SKILL 表述**：description「--mode 按提示词区分」→「形态先与用户确认」、何时使用表 mode 路由行合并 + ⛔ 修订形态先确认铁律框（0.3.1 CHANGELOG 已记、SKILL.md 当时未生效，本轮补上）
- **发布标配**：新增 README.md（定位/依赖/快速开始/与 ibd-doc-review 分工表）+ LICENSE.txt（MIT）；scripts/issues.example.json 重写（code 字段示例 + 中性化内容）

## [0.3.1] - 2026-09-06

### 变更（修订形态先确认 · 用户裁定）

- **修订触发统一收敛为「修订」一个入口，收到后先反问形态再执行**：用户提出任何修订需求（含「直接改好」「干净版」等已指向某形态的措辞），一律先确认 `revise`（Word 修订模式）/ `clean`（直接改好）/ `both`（双版）三选一，**不按用户措辞自动路由 mode**；用户原话明显指向某形态时列为推荐项，仍由用户拍板
- SKILL.md：frontmatter summary/description（--mode 按提示词区分 → 先确认形态）、职权范围表、何时使用表（三行 mode 路由合并为一行入口 + ⛔ 形态先确认铁律框）、使用流程 §2 命令注释同步
- 批注链路不受影响（无形态分叉，docx→Word 批注 / PDF→弹注载体自适应）

## [0.3.0] - 2026-09-06

### 新增（修订稿执行器 · 批注/修订双形态闭环）

- **scripts/revise_docx.py**：复核修订稿执行器——问题清单增 `rev` 字段（anchor 即替换范围）；`--mode revise`（Word 修订模式：原文本聚 `w:del`+`w:delText`、新文本包 `w:ins`，ins/del 同 id、author=复核人、rPr 继承锚点首 run、settings 开 trackRevisions）/ `--mode clean`（直接落定）/ `--mode both`（双版）；复用 annotate_docx 锚点定位与编号；输出 `<原文>_修订稿.docx(+_clean.docx)` + `_修改清单.md`（已修订/待人工两区）
- 实测：3 自动修订（含跨 run 加粗锚点、表格单元格）+ 2 待人工正确分流（无 rev / 复杂 run w:br）；clean 化文本逐段落定 OK；产物过 ibd-doc-review `check_revisions.py` 门禁 PASS
- 边界：复杂 run（w:br/w:tab/多 w:t）、区间夹非 run、未锚定、同段重叠 → 记「待人工」不硬撑
- SKILL.md：frontmatter summary/description/触发词（生成修订稿/直接改好）、职权范围表修订稿转✅现役、何时使用增修订场景、使用流程增 rev 字段与 revise 命令、门禁补 check_revisions、交付物表、资源索引、边界与踩坑（w:delText/trackRevisions 元素名/rPr 继承/倒序应用）；issues.example.json 增 rev 示例

## [0.2.0] - 2026-09-06

### 改名 + 职权扩展（用户裁定）

- **改名 `ibd-annotate` → `ibd-doc-annotate`**：与 `ibd-doc-review` / `ibd-doc-write` 命名对齐（目录、frontmatter name/slug、H1、displayName「IBD 批注与修订复核」、脚本 docstring）
- **修订稿职权划入**：`ibd-doc-review` 复核交付形态中的「修订稿」（直接改好原文文字，内容级）划归本 skill——批注与修订同源（同一份问题清单），同为复核结论落地执行器；SKILL.md 增「职权范围（双形态）」节
- **边界澄清**：`ibd-doc-review` `check_styles.py --revise` 的格式修订（套样式差异转 Word 修订）属格式层，仍归 `ibd-doc-review`，与本 skill 无关
- **执行器待建**：修订稿生成脚本下轮开发（复用锚点定位 + advice 落实到原文文字），期间用户明确「生成修订稿」暂由 writer 手动执行

## [0.1.0] - 2026-09-06

### 新增（首个版本）

- **ibd-annotate 批注复核执行器**（后改名 ibd-doc-annotate）：复核问题清单 + 原文 docx/pdf → 批注版文档 + 精简总览（双轨，编号一一对应）
- **scripts/annotate_docx.py**：Word 审阅批注注入——编号自动分配（J/L/I/Z+序号）、锚点定位（正文+表格段落、跨 run 按字符拆分并保留原 run rPr）、批注正文 4 行紧凑（标签/标题整行加粗、问题描述/建议仅引导词加粗）、comments 四件套补全（styles/Content_Types/rels/comments.xml）、总览 md 生成；复杂 run（w:br/w:tab/多 w:t）或骑跨超链接的锚点记入总览「未锚定」不硬撑
- **scripts/annotate_pdf.py**：PDF 高亮+弹注——rawdict 字符级匹配（容忍空格/换行）、弹注 4 行内容、可选 --pages 节选抽取、总览 md
- **scripts/issues.example.json**：问题清单输入模板
- 实测：docx 端 3 条（含跨 run、加粗/下划线段落）文本零改动、格式保留；pdf 端 2 条真实招股书页锚定；产物过 ibd-doc-review `check_annotations.py` 门禁 PASS
- 格式规范单一事实源：`ibd-doc-review` references/annotations.md（本 skill 只执行不另立规则）

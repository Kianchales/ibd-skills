# Changelog

## [0.11.1] - 2026-10-02

### 入口校验对齐契约：`advice` / `rev` 改 anyOf 条件必填 ＋ 双校验器同输入同结论回归

- **缺陷**：`validate_issues.py` 的 `REQUIRED` **无条件要求 `advice`**，而同集合契约（`ibd-doc-review/references/interface.md` §3 ＋ `problems.schema.json`）规定 `advice`／`rev` **二者至少其一**（`anyOf`）。后果：「**文本定稿/修订**」形态清单（只给 `rev`、省 `advice`）**被自己的入口校验判死**；而 `annotate_docx`/`annotate_pdf`/**`revise_docx`** 三处都调 `validate_issues()` ⇒ 修订链路不可用。实测同一份 rev-only 清单：`validate_schema.py` **PASS**、`validate_issues.py` **ERROR**——两个校验器给出**相反结论**。
- **修法**：`REQUIRED` 去掉 `advice`（保留 `anchor`/`type`/`sev`/`title`/`desc`）；新增 `EITHER = ("advice","rev")` 判定——**二者皆空才 ERROR**，非空判定与必填同口径（空串不算「有」）。`docstring` 与 `references/issues-schema.md` 同步。
- **回归自测**：新增 `scripts/tests/test_validate_issues.py`（**10 项**）——含 **rev-only 通过**（上述缺陷回归）、advice/rev 皆空拦截、必填仍拦；另两类为**契约一致性**（`REQUIRED` == schema.required、`EITHER` == schema.anyOf 键集）与**双校验器同输入同结论**（同一清单过两校验器结论必须一致），需同集合内 doc-review，单包安装自动 SKIP。
- **下游字段名同步**：`README.md` 与 `references/examples.md` 里由 finance 侧串入的旧字段名（`severity`/`suggestion`）改为契约名 `sev`/`advice`（`|rev`）。
- **对外契约零变化**：CLI 用法、ERROR/WARN 分级、退出码不变；仅「原先误判为 ERROR 的合法 rev-only 清单」恢复放行。

## [0.11.0] - 2026-09-29

### 修复 ＋ 变更（批注链修复：注入器原位保留 / 编号分段 / 总览只产 md）

- **修复 · 注入器段落重建原位保留**（静默数据丢失类）：原「保留 pPr、清空其余内容流」会把同段**他人批注锚点**（`commentRangeStart/End`）、书签、超链接、`w:tab`/`w:br` 兄弟 run 一并删除——在已带批注的文档上二次批注即静默丢失他人复核成果；`w:tab` 兄弟 run 被吞（门禁 PASS 但正文被改）同根因。修复后**只重建锚点覆盖的文本 run**，非文本内容与未覆盖 run 一律原位保留；runbook §五／§七补「根因已修」注记，`fix_missing_ranges.py` 降级为旧版产出修复工具。
- **修复 · 既有批注内容合并 ＋ id 接续**：输出阶段原**整体覆写** `word/comments.xml`——二次批注场景他人批注**正文**被清（只剩 document.xml 孤儿 range）；新批注 id 从 0 起与残留批注冲突。修复后新批注 id **接续既有最大 id**，既有 comments.xml **只增不改合并输出**；「他人批注锚点仍在」纳入交付三重校验（runbook 新增 §九 二次批注规程）。
- **修复 · 编号容量顺延**：同前缀超 99 条曾产出 3 位序号（`X-103`），被门禁 LABEL_PAT（序号恰 2 位）判 FAIL——**修注入器、不放宽门禁**；现顺延**双字母分段**（`J-99 → JA-01…JZ-99`，单字母前缀容量 27×99=2673），双字母前缀无顺延空间、超 99 条明确报错提示拆分（静默改写显式前缀＝编号漂移，禁）。`annotate_pdf.py` 同构缺陷双修。
- **变更 · 总览默认只产 md**：`--overview-docx` 显式开关才产 Word 版（推翻 2026-09-18 双格式默认；`annotate_docx.py`/`annotate_pdf.py` 同口径）；交付口径单一事实源 `ibd-doc-review` delivery.md §一 已同改。
- **自测**：新增 `scripts/tests/test_annotate_docx.py` **7 项**（编号边界／131 条全合规／双字母溢出／容量穷尽／tab run 与二次批注端到端／总览开关两态）；存量 `test_fix_missing_ranges.py` 8 项回归原样全过。

## [0.10.3] - 2026-09-25

### 变更（内部留痕清理 · 承 R-0039）

- **活文档去除开发过程留痕**：按 `docs/CONVENTIONS.md` §一「活文档不留过程痕迹」，对本包 `SKILL.md`／`README.md`／`references/` 清理——① **日期戳＋过程动作词／裁定词**（`2026-09-15 用户裁定`、`实测 2026-09-11`、`2026-09-23 补` 类）；② **内部编号引用**（`I-xxxx`／`R-xxxx`，照 R-0032「**去编号留说明**」成法）。
- **红线一律保留**：**业务事实日期**（法规发布/施行日、格式示例、时点事实）、**体系册名引用**（`docs/CONVENTIONS.md`／`ENV-PITFALLS.md` 等）、`CHANGELOG` 与版本历史条目。
- 本包触及 **8 行**；判据单一事实源 → `docs/CONVENTIONS.md` §一。

## [0.10.2] - 2026-09-24

### 变更（踩坑节增写 · 承批注作业实测）

- **`SKILL.md` §踩坑与要点 由「高频三条」扩为「高频四条」**，新增三条实测经验（源＝2026-09-24 某申报项目财务报表及附注复核交付的批注作业；工作树改动本已写好，本次补齐 `CHANGELOG` ＋ 版本，使三载体同步收口）：
  - **跨载体清单须先按载体拆分再注入**：一份复核批次的问题可能分属不同载体（如附注 docx ＋ 申报报表 xlsx）。把**不可锚定**条目一并传入时，脚本仍会为其生成 comments 条目 ⇒ **门禁 FAIL（comments 条数 > cs/ce/ref 对数）**。处置＝按载体拆清单、只传能锚定到该载体原文的条目；其余条目在清单侧另设段号（如附注 `J-01~J-53`、报表 `J-54~J-65`），并在清单「编号规则」处写明两段对应关系，**编号仍保持一一对应**。
  - **xlsx 侧批注走 Excel 单元格批注（另一条链路）**：Excel 无 Word 审阅批注等价形态，用 `openpyxl` 单元格 `Comment` 落地。三条硬约束 —— ① **必须 `load_workbook(path)`（不带 `data_only=True`）**，否则保存时公式被替换为缓存值（申报报表底稿基本靠公式串联，这一步错了会**静默毁掉整本**）；② **先扫既有批注**（`c.comment`），只补不改（原表常带审计/复核人批注，覆盖即丢证据）；③ **只写副本、绝不写原文件**（`--out` 另存）并在文件名标注「（Excel 副本）」，避免误作申报版本流转。同段多单元格同一条目时逐格写入（如同一问题打在 `B22/C22/D22`），便于逐期核对。
  - **批注编号还原（跨载体／子集交付时）**：脚本编号＝「前缀＋段内序号」，重出一版子集会让同一问题出现两套号（旧 `J-02` ↔ 新 `J-01`），破坏清单↔批注一一对应。若必须保持原号，可**后处理 `word/comments.xml`**：`re.sub(r"J-\d{2}", map, xml)` **一次遍历替换**（**勿链式替换**，否则 `J-01→J-02` 会被二次命中），其余 zip 条目原样拷出；总览 md 同步替换后用 `overview_to_docx.py` 重生成 Word，最后重跑门禁确认编号唯一。

- **同步**：小节标题计数「三条」→「四条」；`README.md` 徽章与 `SKILL.md` `version` 同步 0.10.1 → 0.10.2。`references/` 六册与判据本体**未改动**。

## [0.10.1] - 2026-09-24

- **references 去 ADR 索引（承 R-0032 · 2026-09-24 用户裁定）**：按「**ADR 是开发过程留痕，不应作为索引被保留**（否则整个系统对 ADR 产生强依赖）」的口径，本包**活文档**（`SKILL.md`／`README.md`／`references/`／`scripts/` 注释）中的 `ADR-xxxx` 引用**全部脱敏**：带语义说明的**去编号、留说明**（如 `依据 ADR-0020（产物型任务两层路由模型）` → `依据「产物型任务两层路由模型」`）；裸编号处按上下文**改写为自述**（如 `### 0. 协作模式路由（先选模式再写作 · ADR-0001）` → `### 0. 协作模式路由（先选模式再写作）`）。改后 `check_refs.py --internal` 的 **ADR 引用 = 0**、`check_conformance` 的 **A12 = 0**。**`CHANGELOG.md` 不改写**（历史留痕惯例）；**`docs/adr/` 本体保留** —— 仅解除活文档对它的引用，避免「过程物」变成「运行时依赖」。

## [0.10.0] - 2026-09-23

### 新增

- **`annotate_docx.py` 增 `--dry-run`**（议题⑩）：只报「命中／未锚定」统计与目标路径，**不写任何文件**——锚点质量预检用。本脚本是产线里**唯一直写交付件**的环节，此前无任何预演手段。
- **`annotate_docx.py` 增覆盖保护**：目标文件已存在时**默认拒绝**（rc 2），要覆盖须显式 `--force`。动机：误盖既有批注版 ＝ **静默丢失上一轮复核结果**（同族：静默失败／假绿灯）。

### 修订

- `SKILL.md`：使用流程命令行补 `[--dry-run] [--force]`，判据行补两者语义。
- 依赖下限 `ibd-doc-review ≥ 0.19.0` 两处（`SKILL.md`／`references/ops-notes.md`）**加回指** → `ibd-doc-review/references/interface.md` §6（该表自陈「供下游回填」，此前下游未回填）。

### 冒烟记录

- 桩 `docx`／`lxml`／`validate_issues` 后实跑四条路径：`--out` 已存在 → **rc 2 拒绝**；默认目标已存在 → **rc 2 拒绝**；`--force --dry-run` → **rc 0 且零写盘**；全新路径 `--dry-run` → **rc 0 且零写盘**。

## [0.9.0] - 2026-09-21

- SKILL.md 瘦身（承接度 0.09 ⇒ **先建册再搬**）：正文由「步骤名 ＋ 一句话判据 ＋ 册指针」构成，详规按主题下沉到 5 册（新建 `issues-schema.md`／`annotate-runbook.md`／`revise-runbook.md`／`delivery-and-gates.md`／`ops-notes.md`，共 +17,717 B，均经全库 grep 确认无同名冲突）；SKILL.md **20,456 → 12,279 B（−40.0%）**，达 M 档 ≤12,288 线
- 只搬家不删内容、不动触发面：`description`／`summary`／「## 何时使用」与 8 个节标题逐字未改；4 个步骤名与全部判据名留在正文（改后逐条 grep 命中 ≥1）；每册均在「需要它的那一步」内联出指针，资源索引表同步补册行
- 依据：瘦身计划 §二（M 档 ≤12 KB）· §三（S3 搬家 ＋ 指针化，四条硬纪律）· §五（验收九条）；工单 `.scratch/skilldev-slim/issues/T10-batchB-build-or-trim.md`（批 B 第 1 包）
- **承接方式 = 先建册**（本包承接度 0.09，无册可接）：新建 5 册（`issues-schema.md`／`annotate-runbook.md`／`revise-runbook.md`／`delivery-and-gates.md`／`ops-notes.md`，合计 +17,717 B），既有 `examples.md` 原位未动；**真删减 = 无**。
- **版本语义声明改为指针**（承 T12 · 裁定 Q11′②）：`CHANGELOG` 首行原 `X/Y/Z` 自定义记号 → 指向建仓 `docs/ENGINEERING.md` §3.5 的一行指针。

## [0.8.0] - 2026-09-19

### 新增：`validate_issues.py` 支持 `--json` 结构化输出（工程范式 A5 对齐）

- 输出契约：`{tool, target, verdict, error, warn, total, issues[]}`；`--json` 与人类输出二选一
- 退出码不变（入口校验不通过仍为 exit 2）；JSON 模式下一并给出结构化明细
- 依据：`docs/ENGINEERING.md` §4.5 P7「人读摘要／机读 JSON／退出码三值同时成立」

## [0.7.0] - 2026-09-18

### 新增：总览报告双格式交付（MD + Word）

- **动因（用户裁定 2026-09-18）**：总览报告交付时**同时交付 MD 版和 Word 版**——MD 供程序读取/检索归档，Word 供批阅流转；交付口径已同步 `ibd-doc-review` delivery.md §一（格式单一事实源）
- **落地**：
  - 新脚本 `scripts/overview_to_docx.py`：总览 md → docx 转换器（覆盖 write_overview 产出子集——标题/引导行/表格（首行表头加粗）/两级列表/行内加粗；依赖 python-docx 既有依赖，零新增第三方包）
  - `annotate_docx.py` / `annotate_pdf.py`：`write_overview` 出 md 后自动同产 `_批注总览.docx`，输出清单同步
- **实测**：fixtures 端到端（2 条问题全锚定）——md + docx 双产出 ✅；Word 版结构验证（Title / 斜体引导行 / 5 列表格 / 表头加粗）✅；未锚定条目分支（H2 + 两级列表 List Bullet/List Bullet 2）✅
- 性质：交付形态新增输出 = Y

## [0.6.1] - 2026-09-18

### 补充：接入点声明入 `ATTACHMENT-POINTS` 总表（描述补全 · 补 bump Z）

- **背景**：公开包口径刷新——`docs/ATTACHMENT-POINTS.md` 总表由「5 个公开包」扩为 **7 个**（补入 `ibd-methods-ops` / `ibd-methods-query`），并逐包核对接入点三问（须自备资产 / 挂载方式 / 缺失降级）
- **本包改动**：SKILL.md「依赖与工具」节补一行**使用者资产**声明——本包**无需自备资产**（任务输入 = 原文 docx/PDF + 复核问题清单 JSON，模板随包），不依赖方法论库 / KB 后端；并指向集合仓 `ATTACHMENT-POINTS.md` 总表
- **为什么补 bump**：原改动按「纯文档不 bump」记，但本包 **0.6.0 已随 `ibd-skills v0.3.1` 发布过**——若沿用不 bump，发布仓同版本号 0.6.0 的内容将与已发 zip 不一致（版本号与内容失去一一对应）。故按用户裁定补记 `0.6.1`
- 性质：描述补全，规则 / 脚本 / 流程零变化 → bump Z

## [0.6.0] - 2026-09-15

### 新增：批注任务单入口路由声明（ADR-0006）

- **定位声明**：批注类任务（docx + PDF）以本 skill 为唯一对外入口；`ibd-doc-review` 的 `check_annotations.py`（尤其 PDF 侧）由本 skill **内部回调**，下游/外部不直接调用（SKILL.md 配合链路段新增独立声明块）
- **依赖下限**：`ibd-doc-review ≥ 0.16.2` → `≥ 0.19.0`（对齐其单入口语义引入版，避免双包接口声明冲突）
- 性质：路由契约声明（bump 次版本）；注入/校验脚本本体零改动，行为不变

## [0.5.6] - 2026-09-14

### 修复：后处理脚本 `fix_missing_ranges.py` 标记顺序颠倒（静默缺陷）

- **问题**：同段多批注导致 range 丢失后的补插脚本，在「锚点完全落在同一个 run 内」（含锚点覆盖整个 run、起止不跨 run 的常见情形）时，`commentRangeEnd` 被插到锚点首 run **之前**，段落内标记顺序变成 `end → ref → start`——批注范围语义无效（Word 侧区间可能识别不到）
- **为何静默**：交付门禁 `check_annotations.py` 校验的是 cs/ce/ref **对数**与四件套注册，顺序颠倒时对数依然相等 → PASS 放行；跨 run 锚点路径本身正常，故此前实测未暴露
- **根因**：`inject_range_at()` 原按「先切 start 所在 run、再拿**旧偏移**切 end 所在 run」处理。起终点同 run 时，end 偏移落在已被截短的 run 上，`split_run` 退化为 `(run, None)`，end 标记遂被插到该 run 之前
- **修法**：改为「先把 end / start 两个字符边界各自切成 run 边界（**先切后边界、再切前边界**；切分只改变 run 划分、不改变字符坐标）→ 按坐标定位锚点首/末 run → start 标记插首 run 前、end 标记插末 run 后、ref run 紧随 end」。文本为空的批注标记 run 天然不计入坐标，重复补插幂等
- **验证**：新增 `scripts/tests/test_fix_missing_ranges.py` **8 项**（单 run 内 / 到 run 尾 / 覆盖整个 run / 跨 run / 段首 / 同段两条 / 锚点未命中 / 幂等），每条断言「标记顺序 start→end→ref」+「range 覆盖文本 == 锚点」+「段落文本零改动」；**用修复前版本反跑同一套测试失败 5 项**（顺序 `['end','ref','start']`），确证缺陷与测试有效性
- **影响面**：仅后处理脚本；主链路 `annotate_docx.py` 为「按片段重建段落」写法，端到端实测顺序正确，规则与行为零改动

## [0.5.5] - 2026-09-12

### 修复：依赖下限未随交付口径收口而同步（死引用）

- **问题**：本包 0.5.4 起回指 `ibd-doc-review` 的交付口径单一事实源 `delivery.md`，但包内依赖下限仍写 `≥ 0.15.1`——该文件 **0.16.2 才引入**，故声明的下限本身指向一个不存在的文件（**死引用**）。与集合根 README 依赖表已修正的 `≥ 0.16.2` 不一致
- **修正**：三处下限统一为 `ibd-doc-review ≥ 0.16.2`，并写明下限依据（= `delivery.md` 引入版）
  - `SKILL.md`「依赖与工具」依赖表
  - `README.md`「安装与依赖」
  - `references/examples.md` 示例注释
- 规则与脚本零改动

## [0.5.4] - 2026-09-11

### 修复：交付口径语义窄化 + 回指单一事实源（纯文档）

- **修「双轨兜底」语义漂移**：frontmatter description 原写「同步生成精简总览报告（**双轨兜底**）」——把「双轨」（两个交付物并存）窄化成「兜底机制」，与权威口径不符。改为「**双轨并存、批注优先**」，兜底改作总览的附属职能分开表述（「总览兼作兜底」）
- **补交付口径回指**：定位简介职权边界引用块 + 何时使用「配合链路」行各补一条 → 交付口径（默认形态/触发语路由/职权划分/批注纪律）单一事实源 = `ibd-doc-review` skill 的 **delivery.md**，本 skill 只执行不另立
  - 采用**文字指引而非相对路径链接**：本包支持独立分发，`../ibd-doc-review/` 在单独安装时不存在，写死链接会成死链
- 规则与脚本零改动

## [0.5.3] - 2026-09-10

### 文档标准化 T1/T2（2026-09-10 · 纯文档未 bump）

- SKILL.md 骨架统一：职权范围 → 定位简介，踩坑要点 → 踩坑与要点（标准节序对齐）；README 重写为集合风模板

### 更新：displayName「IBD 批注与修订交付」+ 触发词去歧义（改描述 = Z）

- displayName「批注与修订复核」→「批注与修订交付」——执行器归「交付」系（家族动词：写作/格式复核/财务复核/质量校验/交付），不再与复核（查）系混
- 触发词删「批注复核」（字面歧义：像「查批注」——doc-review 校验侧已不收、本包也不再收，由动作词「原位批注/复核意见打在原文/把审核意见做成批注」承担触发）
- summary/描述首句「复核结论落地执行器」保留（准确）；规则/脚本零改动

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

# Changelog

## [0.23.1] - 2026-09-24

- **references 去 ADR 索引（承 R-0032 · 2026-09-24 用户裁定）**：按「**ADR 是开发过程留痕，不应作为索引被保留**（否则整个系统对 ADR 产生强依赖）」的口径，本包**活文档**（`SKILL.md`／`README.md`／`references/`／`scripts/` 注释）中的 `ADR-xxxx` 引用**全部脱敏**：带语义说明的**去编号、留说明**（如 `依据 ADR-0020（产物型任务两层路由模型）` → `依据「产物型任务两层路由模型」`）；裸编号处按上下文**改写为自述**（如 `### 0. 协作模式路由（先选模式再写作 · ADR-0001）` → `### 0. 协作模式路由（先选模式再写作）`）。改后 `check_refs.py --internal` 的 **ADR 引用 = 0**、`check_conformance` 的 **A12 = 0**。**`CHANGELOG.md` 不改写**（历史留痕惯例）；**`docs/adr/` 本体保留** —— 仅解除活文档对它的引用，避免「过程物」变成「运行时依赖」。

## [0.23.0] - 2026-09-23

### 修订

- **下游契约登记收口（③① 两处同批 · 全体系改进 ①）**：
  - **`references/interface.md` §6**：**删「现行」列**——该列写死 0.18.0，而本包已行至 0.22.0（**必然过期且无任何维护动作**）；改为一句话注「当前版本看 frontmatter／CHANGELOG，不在此重复」。**补一行**「**单入口路由语义 ≥ 0.19.0**」——下游 `ibd-doc-annotate` 早已按此声明下限，却**从未登记在本表**。**增「下游消费方」列**并写入「升版动作」一行。
  - **`SKILL.md` 维护节**：原内联「doc-annotate ≥0.15.1／doc-write ≥0.15.0」→ 改为**指向 §6 的纯指针**。⚠️ 该内联**实测双双过期**（实际为 ≥0.19.0／≥0.15.7）**且漏了 `ibd-finance-review`（≥0.16.2）** ⇒ 同一事实曾在 **§6 表 ＋ 维护节**两处各写一遍，这是它们互相漂移的根因。
- **`references/annotations.md` §8 校验门禁**：`编号前缀 ∈ {J,L,I,Z}` 改述为「**1-2 个大写字母**，`J`／`L`／`I`／`Z` 仅为**常见示例、非白名单**」。该条与本册 §4（前缀由复核流程自定义、**脚本不内置映射**）及 `check_annotations.py` 首注（「编号前缀无白名单」）**原本自相矛盾**——同一份册内对同一约束两说，验收照 :96 会误判合规批注。

## [0.22.0] - 2026-09-21

### SKILL.md 瘦身（H 档 T11 · 只搬家 + 指针化，步骤名不下沉）

- **依据**：`20260921_skilldev瘦身计划.md` §二（H 档 ≤20,480 B）／§2.3（完成判据：E0/E1 分界 + 关键结构一条不少，档位线不用于判完成）／§三（方法 S2/S3/S4 + 四条硬纪律）／§五（验收九条）／§十（T8 判定：本包**该瘦**、不拆）；工单 `.scratch/skilldev-slim/issues/T11-batchH.md`。
- **SKILL.md**：31,768 → **20,428 B（−35.7%）**。
  - 「使用流程 §1 场景识别与工具路由」的**决策树详规**（场景A–H 代码块）+ 工具调用顺序 + 失败降级协议表 → `references/workflow.md` **新增 §零·一**
  - 「使用流程 §3 样式应用铁律」0–6 条**全文** → `references/workflow.md` **新增 §零·二**（SKILL.md 留铁律 0 全文 + 其余六条一句话 + 册指针）
  - 「依赖与工具」的**工具层级说明**（每个工具为什么是这个层级/缺了会怎样）→ **新建** `references/toolchain.md` §一
  - 「踩坑与要点」**全文**（9 条含 minimax 环境/apply-template 三坑/标点全角化/--revise 三坑/officecli 实测）→ **新建** `references/toolchain.md` §二；SKILL.md 留高频三条一句话 + 指针
  - 「边界与协作」「资源索引」「维护」压缩为要点 + 指针（删去与 `workflow.md` 附录「两条时序铁律」重复的「文字规范须在套样式之前查」长段副本，内容在册内逐字保留）
- **步骤名不下沉**（H 档关键约束）：S1–S7 **步骤名 + 每步一句话判据**全部留在 SKILL.md「执行流程」表；场景A–H 名称以导航表形式保留；改后逐条 grep 命中 ≥1（实测 41 项结构词 + 21 个触发词全部命中，触发词命中数与改前**逐条相等**）。
- **可达性**（硬纪律①）：12 册全部在**需要它的那一步**内联出「册#节」指针——workflow.md（§1/§2/§3/§4/§5/§6/§7）、style-map.md（S4）、rules.md（S5）、toolchain.md（S3 + 依赖与工具节）、annotations.md／revisions.md／delivery.md／problems.schema.json（§5 复核交付）、interface.md（S7 交付）、sensitive-terms.json（§4 格式核对）、examples.md（何时使用）、changelog-archive.md（维护节）。**补内联 3 册**：`interface.md`／`problems.schema.json`／`changelog-archive.md`（此前仅出现在「资源索引」）；资源索引表**保留**作全景。
- **触发面不变**：`description:`／`summary:`／`## 何时使用` 内容**零改动**（21 个触发词 grep 命中数改前/改后逐条相等）。
- **新增/扩写册**：`references/toolchain.md` **新增 8,153 B**；`references/workflow.md` **扩写 +7,462 B**（18,510 → 25,972）。既有册内原文**未删改**（仅插入新节）。
- **拆分议题不因本次瘦身而消解**：T8 判定为「该瘦」（非「该拆」），本次仅做搬家与指针化，不拆包；瘦到 20.4 KB 仍属大包，若日后重启拆分议题，须过 `skilldev-intake` 两道门 + 用户显式授权。
- **台账**：README「目录结构」补 `toolchain.md` 并更新 SKILL.md 与各册描述；包内「资源索引」同步；`routing-view.md` §4（skilldev 产线）只点包名不点册名，**不受影响**；`skill_table.json`／`skill_tree.json` 全盘检索未找到该文件，**不受影响**。
- **门禁**（改后实测）：`validate_frontmatter.py` ERROR 0 WARN 0；`check_conformance.py` ERROR 0 WARN 0；`check_refs.py --sources`（公开包额外）「依赖表行 2 条已核对；问题数 = 0」。

## [0.21.1] - 2026-09-19 · references 命名统一（kebab-case）

- `references/sensitive_terms.json` → **`references/sensitive-terms.json`**（下划线 → kebab-case，对齐 `docs/ENGINEERING.md` §3 命名规范）
- 同步引用：`SKILL.md`、`references/workflow.md`、`scripts/content_text.py`（常量路径 ＋ 文档字符串）；
  跨包活跃引用 `ibd-doc-write/references/writing-style.md`、`skilldev-source-sync/references/source-sync.md`
- **历史条目不改写**（`v0.21.0` 及更早提及旧名处以历史为准）；实证：`content_text.SENSITIVE_TERMS_FILE` 指向新名且文件可达

## [0.21.0] - 2026-09-19

### 新增：本包 5 个门禁脚本支持 `--json`（工程范式 A5 对齐）

- `validate_schema.py`：输出 `{tool, target, verdict, error, warn, total, issues[{where,msg}]}`
- `check_revisions.py`：`check()` 增 `as_json=False` 参数（默认不变，不影响既有调用）；JSON 含 `mode`／`notes`／`issues`；`--report` 写报告仅在人类模式下执行
- `check_annotations.py`：`{…, verdict, error（FAIL 计数）, warn, issues[{level,msg}]}`
- `check_content.py`：含 `files[{file, counts, report}]`（`counts` 为各级严重度计数）；`--output` 仍写报告
- `check_styles.py`：入口新增统一出口 `finish()`，覆盖 diff／check_numbering／verify_content／revise／默认五条分支，`mode` 字段标明分支
- **JSON 模式抑制过程打印**：被检函数内部的报告输出重定向到缓冲，只保留最终机器可读结果（`check_annotations`／`check_styles` 两处）
- 退出码契约不变（schema 不合 = 1／修订 FAIL = 1）；5 个脚本的 JSON 契约与人类输出回归均通过
- 依据：`docs/ENGINEERING.md` §4.5 P7

## [0.20.1] - 2026-09-18

### 修复：`validate_schema.py` 去第三方依赖（改纯标准库实现）

- **问题**：发布冒烟（`publish_collection.py` 的「零依赖审计」项，AST 扫描全包 import）拦下——`scripts/validate_schema.py`（0.18.0 引入）使用了非白名单模块 **`jsonschema`**，与本包「校验脚本全部 Python 3 标准库（zipfile + xml.etree），解压即跑」的对外承诺冲突。该脚本引入时未在「依赖与工具」声明按需安装，故冒烟白名单机制（口径 = 须与包内声明一致）不予放行
- **修法对比**：① 补声明 + 入白名单（代价：把「零依赖」对外承诺降级为「按需依赖」）② **改纯标准库实现**（保住承诺，且无需放宽门禁）→ **选 ②**
- **实现**：内置 JSON Schema 子集校验器，覆盖 `problems.schema.json` 实际用到的全部校验语义关键字——`type` / `required` / `properties` / `additionalProperties` / `items` / `enum` / `minLength` / `minimum` / `pattern`（`$schema`/`$id`/`title`/`description` 为元数据，忽略）。**schema 若出现未支持的关键字，脚本显式报错而非静默放行**——防「schema 加了约束却没被校验」的假绿
- **契约不变**：CLI 与返回码 0/1/2 保持（返回码 2 的含义由「缺 `jsonschema` 库」改为「文件缺失 / 读取解析失败」）；输出格式保持（`PASS: …` / `FAIL [路径] 消息` / `FAIL: N 处…`）
- **新增自测**：[scripts/tests/test_validate_schema.py](scripts/tests/test_validate_schema.py) **21 项**——含原库语义等价性回归（integer 不接受布尔、enum 词表、pattern、minimum、additionalProperties、schema 守卫、`--quiet`）
- **本版另含**：2026-09-18 的纯文档修正（用词口径 Word 化 + P4 裸路径修复 + badge 同步，见下条，均未单独 bump）
- 性质：修依赖违规（行为等价、去外部依赖）→ bump Z

## [未发布 · 纯文档] - 2026-09-18

### 文案与措辞修正（规则/脚本/流程零变化 · 未 bump）

- **用词口径**：依赖表与 README 的「任一 docx 处理工具」→「任一 **Word** 处理工具」，「docx 处理，二选一」→「Word 处理，二选一」，SKILL.md「所有 docx 操作/`docx` 工具」→「Word 操作/Word 处理工具」。**动因**：`docx` 既像文件类型又像 skill 名，曾致下游门禁（`skill-publish-pipeline` P2.5 依赖声明检查）在本包误判 4 处；**技术对照语境保留不改**——`docx 侧` vs `PDF 侧`（格式分支标识，非工具名）
- **P4 门禁两处裸路径引用修复**：① 同步清单「规则本体 `references/rules.md`」改为 markdown 链接 [references/rules.md](references/rules.md)；② 写作侧预防条 `ibd-doc-write` `references/writing-style.md` 改为「`ibd-doc-write` 的写作红线 `writing-style.md`」（跨包路径本就无法解析为链接，改用反引号文件名规避裸路径判据）
- **README badge 版本同步**：version badge 0.19.0 → 0.20.0（与 SKILL.md 当前版本对齐，清 P4「badge 滞后」WARN）
- 性质：**纯文档修正，未 bump**（依 P5「模板/文档更新在 CHANGELOG 留痕不 bump」及本文件 0.15.5「纯文档未 bump」先例）

## [未发布 · 纯文档] - 2026-09-18

### 交付口径更新：总览报告双格式（MD + Word）· 未 bump

- **用户裁定（2026-09-18）**：总览报告交付时**同时交付 MD 版和 Word 版**——MD 供程序读取/检索归档，Word 供批阅流转
- **落点**：`references/delivery.md` §一 配套交付物 + §七 沿革（本文 = 交付形态单一事实源）；执行侧由 `ibd-doc-annotate` 0.7.0 新增 `overview_to_docx.py` 同链路自动产出（见该包 CHANGELOG）
- 性质：**交付口径留痕，规则/脚本零变化，未 bump**（本包不执行总览生成）

## [0.20.0] - 2026-09-16

### 变更：「中文与半角字符之间不加空格」成立并全链路闭环（用户裁定）

- **触发**：原规则（0.16.0 / 0.16.2）只覆盖「中文 ↔ 阿拉伯数字」；芯片类在办项目大量出现的 XPU／SVAC／AI 类术语在中文语境中的空格**无条款可依**，且检测正则 `RE_SPACE_CJK_NUM` 只认数字（`\d`）不认字母，故产出文件仍带空格。用户裁定：**中英文之间同口径，一律不加空格**
- **规则本体**：`references/rules.md` 三·3 由「数字前后不加空格」扩为「**中文与半角字符（阿拉伯数字、拉丁字母）之间一律不加空格**」；**唯一保留收拢为两处、均在两个半角字符之间**——标准号内部（GB 35114，西文缩写↔数字）与英文词间（Total Solution）；标准号整体与中文交界处（如「符合GB 35114标准」）仍按本条款去空格
- **检测闭环**：`content_text.py` / `deliver_gate.py` 新增 `RE_SPACE_CJK_ALPHA`（`[\u4e00-\u9fff][ \t]+[A-Za-z]` 双向式），分别挂入 `spaces` 子项与「标点规范」项；报告与 detail 分列「数字前后空格 N 处 / 中英文之间空格 N 处」，check_content 核对项名与 `CHECK_REGISTRY` 同步改名
- **双包联动**：`ibd-doc-write` `references/writing-style.md` 写前红线同步该条（写作时即规避，而非事后拦截）
- **验证**：`test_check_content.py` 增 2 项（命中 ＋ 豁免不误报），五脚本 85 → 87 项全过；端到端探针（「XPU 芯片／SVAC 国标」报 4 处，「Total Solution」「GB 35114」零误报）
- **性质**：新增核对能力（bump 次版本）

## [0.19.0] - 2026-09-15

### 变更：批注任务单入口路由（ADR-0006）

- **接口语义**：批注类任务（docx + PDF）以 `ibd-doc-annotate` 为唯一对外入口；`check_annotations.py`（尤其 PDF 侧 `--pdf`）**不再直接暴露**，由 doc-annotate 内部回调。deliver_gate `--annotated` / `--revised` 用法不变
- interface.md §1 门禁说明 + §5 脚本表同步修订；§6 版本下限表加「单入口路由 ≥0.19.0」行、现行列全表刷新
- 性质：对外接口语义变更（bump 次版本）；脚本本体零改动，下游 grep 四包确认无直接引用断链

## [0.18.0] - 2026-09-15

### 新增：问题清单 JSON Schema + 校验入口（ADR-0004 落地，C-分步第一步）

- **新增** [references/problems.schema.json](references/problems.schema.json)：问题清单的**机器可执行结构契约**——必填 6 字段（anchor/type/sev/title/desc/advice）、`sev` 白名单枚举 {高,中,低}、`type` 固定 10 项词表枚举、`code` 1-2 位大写字母 pattern、可选字段类型约束；语义源 = interface.md §3 + annotations.md §4，**两处规范源变更时须同步本文件并 bump 次版本**
- **新增** [scripts/validate_schema.py](scripts/validate_schema.py)：清单校验入口（`python validate_schema.py <problems.json>`，返回码 0=PASS / 1=FAIL / 2=环境错误）；只做结构+白名单校验，语义级检查（锚点可命中、数量卫生）仍由 doc-annotate validate_issues.py / check_annotations.py 把关，不重复
- **双向沙箱验证**：合法清单 PASS；自造标签 `数据·偏高` + 词表外取值 `sev:"blocker"` 被**精准拦截并定位到条目/字段**（白名单能力，grep 黑名单无法覆盖）
- **性质**：消费端（doc-annotate 等）暂不强制接入（分步第二阶段，待运行稳定后推广）；本包 SKILL.md 资源索引挂链
- **依赖**：`jsonschema`（Python 库，缺库时报 ENV-ERROR 退出码 2，不误判 FAIL）

## [0.17.3] - 2026-09-12

### 补记（2026-09-15）

- 新增 `references/interface.md`（对外接口契约：交付口径/门禁 CLI/问题清单 schema/编号词表/脚本对外入口/版本下限速查 + 变更纪律），SKILL.md 资源索引挂链。此条为补记——文件当日先行入库、CHANGELOG 漏记，由检查6 门禁首跑捕获。
- 资源补记（2026-09-15，检查6 门禁首跑追溯）：`references/sensitive_terms.json`（敏感词/地理清单）为首发期随包资产，历史上未单独记版本条目，此处一次性补记留痕。

### 修复：发布隐私门禁 BLOCK（P1）——平台路径与个人用户名泄露

- **现象**：发布前 P1 隐私扫描报 **12 个 BLOCK**（PRIV-005 ×4 ＋ PRIV-004 ×8）
- **PRIV-005（内部配置目录）**：`deliver_gate.py` 的 officecli 探测候选里硬编码了平台二进制目录路径；`CHANGELOG` 与 `references/workflow.md` 的「探测顺序」文字同步复述了该路径
- **PRIV-004（本机用户名）**：`scripts/tests/test_check_revisions.py` / `test_deliver_gate.py` 的 fixture 用本机用户名作修订与批注的 `author`
- **性质**：**均为上次发布（0.15.7）之后新引入**——officecli 探测（0.16.3）与 `scripts/tests/` 目录均属后续新增，此前未过 P1 门禁
- **修复**：
  - `deliver_gate.py`：探测列表改为**平台通用位置**（`~/.officecli/`、`~/.local/bin`、`~/bin`、`%LOCALAPPDATA%\Programs\officecli\`、脚本同目录），并新增 **`OFFICECLI_HOME`** 环境变量支持自定义安装目录；`--officecli-path` 显式指定仍最优先
  - 测试夹具 `author` 改中性值「复核人」、`w:initials` 同步；文档「探测顺序」措辞改为平台通用表述
- **验证**：P1 复扫 **0 BLOCK**；`scripts/tests/` 五脚本测试全过；P4 骨架校验 0 ERROR / 0 WARN
- **对外契约零变更**：CLI 参数 / 退出码 / 三态语义均不变

## [0.17.2] - 2026-09-11

### 修复：最小 fixture 部件级关系表路径重复（`word/word/document.xml`）

- **现象**：`ibd-doc-annotate/scripts/annotate_docx.py` 打开本包**最小 fixture** 时报 `KeyError: 'word/word/document.xml'`；对真实 python-docx 产物正常（历史观察项，至此销项）
- **根因**：fixture 构造器 `_pkt()` 把**包根级**关系模板 `RELS_TMPL`（`Target="word/document.xml"`，相对包根解析，正确）**直接复用**给 `word/_rels/document.xml.rels`。后者 Target 按 `word\` 基准解析 → 得到 `word/word/document.xml`
- **性质**：fixture 长期畸形而测试全绿——本包门禁一律走 `zipfile` + 字符串包含判断（如 `"comments.xml" in rels`），**从不做 OPC 关系解析**；唯有真实解析器才暴露。与 0.15.8 加粗误判、0.17.0 `terms` 空转同属「门禁视角盲区」
- **修复**：新增**部件级**模板 `DOC_RELS_TMPL`（Target 为 `styles.xml` / `settings.xml`，与真实 docx 一致）；`_pkt()` 与 `test_check_annotations.py` 同步换用
- **新增守卫**：`test_deliver_gate.py` 增加 E 组 `RelsSemanticsTest`（4 项，**纯标准库零依赖**）
  - 断言包内**所有** `.rels` 的非外部 Target，按 OPC 规则解析后必须指向真实存在的部件
  - 断言部件级 rels 不含 `officeDocument` 关系（该关系只属于包根 rels）
  - 第 4 项：装了 python-docx 则真打开一次，未装则 `SKIP`（不破坏零依赖铁律）
  - **有效性实测**：把模板还原成修复前写法 → 守卫立即 FAIL，报错与真实解析器**完全一致**（`'word/word/document.xml' not found`）
- **端到端验证**：最小 fixture → `annotate_docx.py` 注入 2 条（全部锚定）→ 产出件可被 python-docx 打开 → `check_annotations.py` **PASS** ＋ `deliver_gate.py --annotated` **9/9 PASS**
- **测试计数**：`test_deliver_gate.py` 22 → **26 项**（五脚本 81 → **85 项**）
- **补 SKILL.md 资源索引指针**：0.17.1 新增的 `references/changelog-archive.md` 当时未在 SKILL.md 提及，P4 骨架门禁报「未从 SKILL.md 直接可达」ERROR → 资源索引补一条。**该 ERROR 是归档时未复跑 P4 留下的盲区**，2026-09-12 发布前门禁扫出

## [0.17.1] - 2026-09-11

### 重构：`CHANGELOG.md` 分段归档（P3-⑨，审计整改收尾）

- **问题**：本文件单文件 46.9 KB / 495 行、**38 个版本段**堆叠，每次读取都要吞全部历史 → 文件本身在拖慢每次维护
- **处置**：以 `0.15.0` 为代际切点，**0.1.0 – 0.14.1 共 24 个版本段**逐字节迁入 [`references/changelog-archive.md`](references/changelog-archive.md)
- **主文件保留 14 个版本段**（0.15.0 – 0.17.1，即当前现役代际）；文末新增「历史版本归档」索引表回指归档文件
- **切点选择依据**：`0.15.0` 是 data 组迁往 `ibd-quality-gates` 的分界线，跨过它意味着能力边界变动 → 天然代际边界，而非机械按体积对半切
- **完整性证明**：切分前后「保留部分 + 归档部分」归一化后 **SHA-256 一致**；版本段计数 14 + 24 = 38，与原文件完全相符（零丢失、零新增）
- **文档同步**：`README.md` 目录结构补 `CHANGELOG.md` 一行 + 版本记录指针（含归档回指）；修本文件一处历史误链——0.16.2 段复述 `annotations.md` 措辞时把 `delivery.md` 写成相对链接（该段位于 `references/` 语境，主文件内解析为死链），改为反引号纯文本
- **效果**：46,929 B → 29,223 B（**降 37.7%**），归档 18,445 B

### 文档同步

- `README.md` 目录结构补 `CHANGELOG.md` 一行 + 版本记录指针（含归档回指）

### P3-⑨ 收尾说明

- 本轮完成后，`ibd-doc-review` 审计整改项 **全部清空**

## [0.17.0] - 2026-09-11

### 重构：`check_content.py` 按业务域拆组（P2-⑧）+ 修复 `terms` 核对项静默失效

**背景**：`check_content.py` 单文件 1,146 行 / 51 KB，扩展核对项成本高。审计 P2-⑧ 判定「50 KB / 1,135 行单文件过大」。

**拆组方案（方案 B · 按业务域切，用户拍板）**

- **前置勘察**（拆组前完成，结论：耦合为分层而非网状）
  - Python 层 `import check_content` 的下游 = **0 处**（全部为 subprocess/CLI 或纯文字指引）
  - 跨段引用方向几乎全是「核对项 → 基础解析」**单向下行**（`Issue` 被引 11 次）
  - 11 个 `check_*` 之间**零互相调用**，仅靠 `run()` 的 `runners` 字典聚合
- **四文件结构**（组名 `text`/`table` 与模块边界一一对应）

| 文件 | 行数 | 承载 |
|---|---|---|
| `content_common.py` | 266 | 共享基础层：`Issue` / docx 解析 / 中文序号基元 / 标点判定基元 |
| `content_text.py` | 555 | 文字类 7 项（heading_seq / terms / dates / spaces / abbr / geo / punctuation） |
| `content_table.py` | 177 | 表格类 4 项（table_font / table_align / table_empty / table_na） |
| `check_content.py` | 268 | **唯一 CLI 入口**：登记表 + `resolve_checks` / `run` / `render_report` / `main` |

- **零破坏设计**：`check_content.py` 保持唯一入口，对外契约（`--input` / `--output` / `--checks` / `--geo-file` / `--terms-file` / 报告文件名 `<input>_格式核对报告.md` / 退出码 0·1·2）**完全不变**；三模块与入口同目录（入口内为绝对 import），实测从 skill 根目录与任意 cwd 调用结果一致
- **完整性证明**：拆组前 68 个顶层定义 → 拆组后 68 个，**丢失 0、新增 0**；逐函数行数与原文一致（如 `check_heading_seq` 82 行 / `check_table_na` 25 行）

### 修复：`check_terms` 内置规则从未生效（拆组配套测试挖出）

- **现象**：`--checks terms` 对「帐面」「其它」等内置规则**恒 0 命中**，`terms` 核对项自诞生起静默失效
- **根因**：`BUILTIN_TERM_RULES` 是 **dict 列表**，而 `check_terms` 原先 `rules = list(BUILTIN_TERM_RULES)` 后直接 `pat, problem, suggestion = rule` —— **把 dict 解包成键名**，于是 `re.compile("pattern")` 在正文里搜英文单词 `pattern`，永远不命中
- **修复**：统一转三元组 `[(r["pattern"], r["problem"], r["suggestion"]) for r in BUILTIN_TERM_RULES]`
- **性质**：与 0.15.8 的 `<w:b w:val="0">` 误判同类——**靠补测试才挖出的潜伏 bug**，同样是「门禁看似存在、实则空转」
- **验证**：修复后「帐面价值」正确检出（`--checks terms` 端到端确认）

### 测试：新增 `test_check_content.py`（20 项）

拆组前 check_content 的用例寄生在 `test_check_styles.py`（仅经 CLI 端到端），本文件按模块边界补两组此前**无处覆盖**的风险：

- **E 组 · 模块结构契约**（6 项）：模块可独立 import 且无循环依赖 / `CHECK_REGISTRY` 的 11 个 id 均有同名实现 / `GROUPS` 成员与 `group` 字段一致 / `runners` 覆盖全部 id（漏挂即静默跳过）/ 标点基元返回形态（C·E·O 三分类 + 元组）/ `resolve_checks` 分组与顺序
- **F 组 · 核对行为**（14 项，直调函数不经 CLI）：序号跳号·重号 / 数字前后空格 / 重复标点 / 中文语境半角标点 / 内置术语规则 / geo 严重度映射 / 表格违规字号 / 合法字号 / 非正式表豁免 / vMerge 续格不计空 / 真实空单元格 / 标记混用

### 文档同步

- `SKILL.md` 依赖表与工具说明补三模块说明（明确「须与入口同目录随包分发」）
- `references/workflow.md` 格式核对模式补模块结构说明（扩展核对项时只动对应域文件）

### P2-⑧ 收尾说明

- 剩余审计项：**P3-⑨** `CHANGELOG.md` 分段归档

## [0.16.3] - 2026-09-11

### 新增：`deliver_gate.py` 引入第三态 `[SKIP]` + 物理扫描常驻行（P2-⑦）

- **问题**：officecli 物理扫描是**软门禁**——不在任何脚本里，全靠人记。漏跑无痕迹，交付说明里「未跑物理缺陷扫描」这句话形式存在但无人校验
- **处置**：`deliver_gate.py` 引入**三态输出**，并把物理扫描做成**常驻一行**
  - `[PASS]` 通过 / `[FAIL]` 不通过（计入退出码）/ **`[SKIP]` 未执行（不计入退出码）**
  - `check_physical()` 三种返回：未给 `--officecli` → `SKIP·未启用`；给了但没装 → `SKIP·未找到`；跑出问题 → `FAIL`
  - 给 `--docx` 时该行**恒输出**（共十项）——**设计目的就是让「未跑物理扫描」在交付输出里可见**，不靠人记
- **参数**：`--officecli`（启用）/ `--officecli-path P`（显式指定二进制）/ `--expect-issues N`（可接受缺陷数，默认 0）
- **探测顺序**：`--officecli-path` → PATH → `~/.officecli/` 等平台常见位置（自定义安装目录用 `OFFICECLI_HOME` 指定）
- **实现要点**：
  - 走 `--json` 解析而非解析自然语言输出（`validate --json` → `success` 布尔；`view issues --json` → `data.count`）——实测 v1.0.148 输出稳定
  - 异常一律吞掉转 SKIP：**软门禁不得中断主流程**（officecli 超时/崩溃不会让交付核验整体挂掉）
  - 结论行格式：SKIP 同时从**分子分母**扣除 → `结论 8/8 PASS ✅（1 项 SKIP 未执行）`，**不污染通过率**
- **动因**：审计 P2-⑦「officecli 补充门禁为软门禁，交付说明易漏『未跑物理扫描』」

### 测试：`test_deliver_gate.py` 新增 E 组 3 项（19 → 22）

- `test_16` 不给 `--officecli` → SKIP 行可见 + 结论行附注「1 项 SKIP 未执行」
- `test_17` 给 `--officecli` 但路径不存在 → **退出码仍为 0**（软门禁不阻断交付，核心断言）
- `test_18` SKIP **不进分子分母** → 结论仍 `8/8` 而非 `8/9`
- 辅助函数 `line_of()` 正则由 `(PASS|FAIL)` 扩为 `(PASS|FAIL|SKIP)`；只覆盖确定性 SKIP 路径，不依赖本机是否装 officecli
- **四脚本共 61 项全过**（22 + 10 + 11 + 18）

### 同步：文档

- `references/workflow.md`：S6 补充门禁段重写（给出 `--officecli` 命令、三态语义、FAIL 判据、探测顺序）；命令全表首选行补 `[--officecli]`
- `SKILL.md`：决策树场景 H 补物理扫描挂载与三态说明；officecli 工具说明同步（「未装则会输出 SKIP 行，交付说明据此注明」）

## [0.16.2] - 2026-09-11

### 变更：数字空格规则收窄为「一律不加空格」（用户二次裁定）

- **用户原话**：「一律不加空格」——撤回 0.16.0 中「所引名录／目录的条目编号与名称之间按原文献写法」这一例外
- **条文**（`references/rules.md` 三·3 重写）：中文与数字之间的空格**一律删除，不设情形豁免**；明确「1.5 人工智能」应写作「1.5人工智能」
- **唯一保留**：「GB 35114」「ISO 9001」「IEEE 3122-2025」这类标准号／编号中**西文缩写与数字**之间的一个半角空格——该情形**不属"中文与数字之间"**（空格前邻字符为字母），且国标编号规范写法即为带空格
- **脚本零改动**：名录条目例外此前仅写入文档、**未在代码中实现豁免**（正则会正常报出），故收窄规则只需改条文
- **实测修补**：`问题1_回复_案例仿写版_v2` 两处按新规修正——「1.5 人工智能」→「1.5人工智能」、「【待补：5-16 逐条对照表…】」→「5-16逐条对照表」（后者与同段「问题5-16」的原有无空格写法本就不一致，属内部不统一）
- 测试仍 **58 项全过**（`test_03c` 断言的西文缩写例外未受影响）

### 收口：交付口径归一到 delivery.md（P2-⑥ 前半）

- **问题**：交付口径在 5 处各自复述，措辞已开始漂移——`annotations.md` §1 独立成节「双轨并存 · 批注优先」等于第二份口径源；`workflow.md` 导语语序与权威源**相反**（「批注版优先 + 精简总览报告双轨并存」）
- **处置（本包内）**：
  - `references/annotations.md` §1 标题由「交付形态（双轨并存 · 批注优先）」→「交付形态」，首行加**指向 `delivery.md`** 的口径声明；形态表保留（讲的是总览字段，属批注格式职责）
  - `references/workflow.md` §3 导语语序对齐权威源，逐字统一为「**双轨并存、批注优先**」，并把 delivery.md 提为「交付口径单一事实源」列首
- **跨包侧**（同步升版 annotate 0.5.4 / finance-review 0.8.4）：两包各补回指 delivery.md 的**文字指引**（不用相对路径链接——两包均支持独立分发，`../ibd-doc-review/` 会成死链）；annotate 另修 frontmatter 的「双轨兜底」语义窄化
- 口径统一表述：**「双轨并存、批注优先」**（此后各文件一律用此语序）
- 保留的两处「双轨兜底」语境正确（讲总览兼作兜底，非语义窄化），未动

## [0.16.1] - 2026-09-11

### 重构：SKILL.md 使用流程抽取 `references/workflow.md`（主文件瘦身 38%）

- **动机**：SKILL.md 达 20,029 字符，其中「使用流程」5 节占 **11,001 字符（55%）**——SKILL.md 每轮固定进上下文，执行细节（样式映射全表/门禁命令/核对矩阵）属**按需读**，不该常驻
- **抽取边界（方案 A · 保守抽取）**：按「常读 vs 按需读」切，不按字数切
  - **转出**（7,481 字符）：§2 执行流程 S1-S7（含样式映射 12 行表、S6 门禁命令清单、S7 三件套交付）/ §4 格式核对模式（命令块 + 两大组别 10 项矩阵 + 边界）/ §5 批注与修订复核交付模式（命令块 + 检查项 + 加粗语义坑 + 自测）
  - **留在 SKILL.md**：决策树（场景 A-H 路由图 + 工具调用顺序 + 失败降级协议）、**样式应用铁律 6 条**（红线，含铁律 0 只改格式）、资源索引 / 依赖与工具 / 边界与协作 / 踩坑与要点 / 维护
- **原位留驻 = 指针 + 三行摘要**：每节保留 3 条内核行（如「七步主线：S1 识别 → … → S7 三件套交付」），不跳转也能记起主线，无需翻文件即可复述步骤
- **结果**：SKILL.md 20,029 → **14,708 字符**（降 5,321 / **26.6%**）；决策树与铁律**一行未动**
  - 实际降幅低于预估 38%，差额来自「指针 + 三行摘要」的摘要成本（3 节共留 10 条摘要行、1,789 字符）；其中 §5 摘要偏厚（729 字符）是刻意为之——含两根**红线**（门禁 FAIL 退回 / `<w:b w:val="0">` 加粗语义坑），红线不抽走
- **否决方案 B/C**：B（再抽决策树）用「省 2,600 字符」换「每轮多读一文件」净亏——决策树是最高频入口；C（再抽踩坑）把实测打出来的前置警告变成按需读，制造漏读风险

### 新增：`references/workflow.md` 附录 · 「脚本 × 场景」命令全表（顺带合并三处重复）

- **合并动机**：门禁命令原先分散在**三处**（SKILL.md S6、格式核对模式、批注修订模式各一份），内容互相重复，改一处易漏另两处
- **新表**：13 行「你要做什么 → 命令 → 说明」，覆盖交付前核验 / 批注版 / 修订版 / 样式校验 / 模板校验 / 内容一致性 / 格式清单 / 格式修订稿 / 序号核对 / 格式核对 / 批注校验（docx+pdf）/ 修订稿校验 / 脚本自测
- **两条时序铁律**收进表尾（文字规范须在套样式前跑；交付前一律先跑 `deliver_gate.py`）——同属「动手前」事项，与命令表同址更易命中

### 同步：入口与文档

- frontmatter `version` 0.16.0 → 0.16.1；`使用流程` 节首与「何时使用」节尾各补 workflow.md 指针；资源索引新增「执行细则」条
- 下游依赖声明不变（本次仅文档重构，脚本零改动，`ibd-doc-write` ≥0.15.8 兼容性不受影响）

## [0.16.0] - 2026-09-11

### 新增：格式铁律「数字前后不加空格」+ `spaces` 校验项扩展（用户裁定）

- **规则**（用户 2026-09-11 裁定，全文适用）：**中文（含全角标点）与阿拉伯数字之间不加空格**——「2025年」「3至5年」「135,360.57万元」「2030年1-6月」「占比80.06%」
  - **例外（保留一个半角空格）**：① 标准号／编号中的西文缩写与数字之间（「GB 35114」「ISO 9001」「IEEE 3122-2025」）；② 纯西文语境；③ 所引名录／目录的条目编号与名称之间按原文献写法
  - 落点：`references/rules.md` 第三节「通用排版铁律」新增第 3 条（原 3-6 顺延为 4-7）
- **校验（两处挂载）**：
  - `check_content.py` 的 `spaces` 项新增「数字前后空格」子项——新正则 `RE_SPACE_CJK_NUM = [\u4e00-\u9fff][ \t]+\d | \d[ \t]+[\u4e00-\u9fff]`；沿用既有排版豁免（签署页「年 月 日」宽间隔、目录页「目 录」）；`CHECK_REGISTRY` 与模块 docstring 名称同步为「多余空格/数字前后空格/重复标点」
  - `deliver_gate.py` 的「标点规范」项并入同规则（**不新增核验项、仍为九项**，兼容既有调用方与测试契约）；detail 追加「数字前后空格 N 处」，FAIL 时给前 5 例
  - **西文缩写天然豁免**：`GB 35114` 的空格前邻字符是字母而非汉字，不匹配——无需白名单
  - 严重度 **HIGH**；`check_content` 侧属**文字层**，须在**套样式之前**跑（与 0.15.6 标点全角化同理）
- **动机**：实测一份交付件通篇采用「2025 年」「135,360.57 万元」式加空格排版，与机构内部规范不符——规范此前未成文，故漏检
- **测试**：`test_deliver_gate.py` 新增 2 项——`test_03b`（中文与数字间空格 → 标点规范 FAIL）/ `test_03c`（西文缩写 `GB 35114`、`ISO 9001` 与纯连写 → 不报）；**既有 5 项夹具同步为「数字前后不加空格」写法**（原夹具用「2026 年 6 月」「36,507.55 万元」加空格，新规则下已不合规）。四脚本 **56 → 58 项全过**
- **实测回归**：某芯片设计项目问题1 回复 v2 交付件正文命中 **2 处**，均为「编号＋名称」情形（所引《战略性新兴产业…指导目录（2016版）》条目「1.5 人工智能」、待补标记内「5-16 逐条对照表」），非真实违规——留人工判断

## [0.15.8] - 2026-09-11

### 新增：`deliver_gate.py` 挂载复核产物门禁（`--annotated` / `--revised`）

- **动机**：本 skill 自设「铁律 1 · 核验一次跑完」，但 `deliver_gate.py` 此前**不含**批注/修订断言——交付批注版时仍须另跑 `check_annotations.py`，两条命令的输出都进上下文，与「一次跑完」的设计目的相悖
- **能力**：按产物形态**开关式挂载**（批注版与修订版互斥，避免常驻判定互相误 FAIL）
  - `--annotated [--expect-annotated N]` → 追加 **批注部件**（comments.xml 本体 + Content_Types Override + document.xml.rels 关系）/ **批注结构**（条数 == cs/ce/ref 对数、cid 唯一、每条 4 段无空行、标签行与标题行整行加粗、引导词加粗而正文常规）/ **批注编号**（`【前缀-序号｜类型｜严重度】` 格式与全局唯一；并入结构行输出）
  - `--revised [--expect-revised N]` → 追加 **修订成对**（ins==del、author 非空、id 唯一且共享同 id）/ **修订落定**（delText/ins 非空、settings 开 trackRevisions + revisionView、clean 化后 ins 文本仍在全文）/ **修订计数**
- **兼容性**：不给开关时行为与 0.15.7 完全一致（仍九项），既有调用方（`ibd-doc-write` ≥0.10.0）无需改动
- **参数契约**：`--annotated` 与 `--revised` 互斥、且必须配 `--docx`，违反即 argparse 报错（退出码 2）
- 零第三方依赖不变（zipfile + etree）

### 修复：`<w:b w:val="0">` 被误判为加粗（`check_annotations.py` + `deliver_gate.py`）

- **现象**：写作链产出的批注正文 run 常带 `<w:b w:val="0"/>` 显式声明常规字重，旧判定只查 `<w:b>` 元素是否存在 → 判为加粗 → 触发「行3/行4 正文存在加粗 run（仅引导词可加粗）」→ **合规批注被误 FAIL、无法交付**
- **根因**：`w:b` 与 `w:pStyle` 同用 `w:val` 属性（属性名即 `w:val`，无内层前缀），谓词须按语义判定：元素缺失 或 `w:val ∈ {0,false,off}` → 不加粗
- **修复**：两脚本各引入 `is_bold()` 谓词；该 bug 由本轮新建的最小测试集首次暴露

### 新增：三脚本最小测试集（`scripts/tests/`）

- `test_deliver_gate.py`（**17** 项）：基础九项回归 + 批注挂载 6 项 + 修订挂载 4 项 + 参数契约 3 项；含「不给开关仍是九项」的兼容性回归
- `test_check_annotations.py`（**10** 项）：合规件 PASS / 缺部件 / 缺 CT Override / 锚定对数不齐 / 段落数≠4 / 编号格式错 / 编号重复 / 引导词缺失 / 缺 CommentText 样式 / `--report` 落盘
- `test_check_revisions.py`（**11** 项）：revise 侧 8 项（含 clean 化落定失败构造）+ clean 侧 2 项 + `--report` 落盘
- 测试构造器复用同一套最小 docx 骨架（`test_deliver_gate.py` 为单一事实源，另两文件 importlib 加载）——避免三份 fixture 漂移
- 现状：**四脚本共 56 项全过**（另含既有 `test_check_styles.py` 18 项）

### 同步：入口与文档（description / README / SKILL.md）

- frontmatter `description` 补第 5 条能力「章节复核交付约定」+ 触发词（「章节复核怎么交付」「复核交付形态」「批注版还是修订稿」「研究下XX节」「帮我看看这段」）；`summary` 同步；version 0.15.7 → 0.15.8
- `README.md` 核心能力区新增「📤 章节复核交付约定」（指向 `references/delivery.md`）；目录结构与近期更新同步
- `SKILL.md`：决策树场景 F/G/H 补「交付前可用 `deliver_gate.py` 一条命令涵盖」；S6 门禁补开关用法；「批注检查项」补加粗语义坑与自测命令；下游依赖下限提示升 0.15.8 并注明向后兼容

## [0.15.7] - 2026-09-10

### 新增：`scripts/deliver_gate.py` —— 交付前综合核验（一次跑完 · 极简输出）

- **动机**：一次交付前核验的 token 复盘显示，工具返回占全部内容量 41%；其中同一指标被反复统计（引号 8 次、XML/结构核验 6 次、锚点 5 次），每次脚本输出都进上下文
- **能力**：把九项合并为**一次调用**——标点全半角 / 样式（pStyle 分布·必备样式·裸段落·空段落）/ vMerge·gridSpan / 关键数字锚点（md↔docx 出现次数一致）/ 禁用词红线 / 占位符计数 / 文档结构 / **md↔docx 同源核验**（归一化后逐字比对，含差异定位）/ 去标点指纹
- **输出约定**：`[PASS] 指标 结论行`，**PASS 不展开、FAIL 才给明细**（默认最多 5 条）；退出码 0/1 可直接作交付判据
- 零第三方依赖（zipfile + xml.etree），与「内置脚本零依赖」承诺一致
- 实测：对合规交付件 9/9 PASS（输出 15 行）；对未套样式原稿正确 FAIL（pStyle 0 段 / 裸段落 293 / 缺必备样式，退出码 1）

### 流程：门禁前置 + 收敛核验命令（同一实测来源）

- **SKILL.md 新增「场景 H」**（决策树）+ S6 门禁条目 + 工具调用顺序第 5 步
- **边界与协作新增两条规则**：
  - **文字规范必须在「套样式之前」先查**：标点全半角虽是格式核对项，但返工成本落点不同——套样式后才发现会导致样式重做（实测 384 处半角引号漏到套样式之后才被抓出）。完整顺序：内容定稿 → `check_content --checks text` → 套样式 → `deliver_gate` → 交付
  - **交付前一律先跑 `deliver_gate.py`**，不要用分散的多条核验命令替代
- 同源核验的归一化补充剥离 HTML/上标标记（`<sup>` 在 docx 已转原生上标，不剥离会产生 4 处伪差异）

## [0.15.6] - 2026-09-10

### 修复：a6 表体字号两文件矛盾（某芯片设计项目问询回复套样式实测暴露）

- `references/style-map.md` 表格样式表 a6 行：「默认 9pt（小五，sz=18）」→「全表 10.5pt（五号，sz=21）；表格宽度不足时可用小五 9pt（sz=18）」
- **暴露路径**：执行者据 style-map 取 sz=18 与 rules.md §2「全表 10.5pt（sz=21）」冲突，需人工上抛裁定；实为 style-map 该行早于三线表 v2 定稿、未随 v2 同步
- **权威判定**：style-map.md 自身已声明「表格级/行级/表头结构/对齐规则等结构性规范见 rules.md 第二节」→ 结构项以 rules.md 为准；check_content.py 表格字号项亦判定「五号 21 合法、放不下可用小五 18」；三处口径现一致
### 修复：`check_table_empty` 不识别 vMerge 导致合并单元格误报（同一实测来源）

- **现象**：某芯片设计项目问询回复表 1-3 补上纵向合并（`vMerge` restart/continue）后，「表格空单元格」仍报 3 个空格、总数停在 9 格降不下来
- **根因**：`parse_tables()` 逐 `<w:tc>` 只取 text/sizes/paras，**不解析 `vMerge`**；`check_table_empty()` 判定条件为 `cell["text"] == ""`，**未排除 vMerge 续格**——而续格本就无文字，属结构性空白
- **修复**：① `parse_tables()` 增补 `vmerge` 字段（在 `w:tcPr` 范围内匹配 `<w:vMerge w:val="…"/>`，无 val 视为 continue）；② `check_table_empty()` 改为 `cell["text"] == "" and cell.get("vmerge") != "continue"`
- **回归**：实测该文档空单元格 9 → 6 格（剩余 6 格为合计行描述列的真实留白，经裁定保留）；自测 18/18 全过
- 另：a6 字号矛盾为纯文档修正，规则实质未变

### 补充：踩坑与要点新增 3 条（同一实测来源）

- **apply-template 只做组件级替换、不做段落 pStyle 映射**：套用后 pStyle 分布仍为 `(裸):N`，易误判为失败；段落级映射须另做一步（局部走 local-office-edit、批量走脚本改 document.xml）；给出验收判据（pStyle 引用数 0→非 0、残留直接格式归零）
- **半全角标点须在套样式之前先过 `check_content.py --checks text`**：半角引号/括号判 HIGH，若等套完样式才发现，文字层返工导致样式重做
- **标点全角化的安全做法**：先行内奇偶校验（奇数行须为 0）→ 交替替换 → 以「去掉引号字符后文本 sha256 前后一致」证明零内容改动；全半角等宽，字符数与 document.xml 长度不变

## [0.15.5] - 2026-09-10
### 文档标准化 T1/T2（2026-09-10 · 纯文档未 bump）

- SKILL.md 骨架统一：上游接口与边界→边界与协作、踩坑记录→踩坑与要点、补「维护」节；README 集合风重写

### 更新：displayName 定名「IBD 投行格式复核」（家族动词归位，改描述 = Z）

- 原「文档质检」游离于家族动词（写作/复核/校验/交付）之外且带品检味——用户裁定改「格式复核」，与财务章节复核、批注与修订复核成「复核」系
- summary 同步：去「A 股 IBD 投行」三重复（→ A 股投行）、「质检」→「格式复核」
- 包名 ibd-doc-review 不变；规则不动
- **措辞去重**：description「格式质量检查」→「逐项核对格式问题」（「质量」已归 quality-gates 质量校验，格式层不串味）
- **F2 触发词冲突修复**：剔除注入意图触发词「批注复核/原位批注/复核意见打在原文」（与 ibd-doc-annotate 抢路由——本 skill 是批注规范与校验侧，注入执行归 annotate），保留规范/校验侧触发词并在 description 标注分工

## [0.15.4] - 2026-09-10

### 修复：自测过期用例同步 0.15.0 data 组迁移（CI 回归首抓，随 P1 批次）

- `scripts/tests/test_check_styles.py`：两用例仍断言 check_content 检出金额问题——data 组 09-06 已迁 ibd-quality-gates check_data.py（0.15.0），旧期望过期导致 18 用例 2 失败（本地自测长期未跑未暴露）
  - `test_content_check_heading_skip_and_amount` → `test_content_check_heading_skip`：只测标题跳号（heading_seq），断言金额不归本脚本检出
  - 新增 `test_content_amount_migrated`：`--checks amounts` 输出迁移提示（指向 gates check_data.py）且报告零金额检出——迁移行为回归锚点
  - 删除 `test_content_amount_exemptions`（豁免逻辑随 data 组迁出，回归覆盖归 gates 侧补测）
- 自测 18/18 全过；触发：P1 GitHub Actions CI 落地时首跑抓出

## [0.15.3] - 2026-09-10

### 修复：check_revisions.py 去 lxml 依赖（冷启动验证 F1）

- **`scripts/check_revisions.py` lxml → 标准库 `xml.etree.ElementTree`**：维持「内置脚本零依赖」承诺——coldstart 实测发现脚本声称零依赖但 `from lxml import etree`（消费者干净环境冷启动即 ModuleNotFoundError）；lxml 用量仅 fromstring/tostring 3 处，重写要点：
  - 深拷贝 `etree.tostring(doc)` → 加 `encoding="unicode"`（stdlib 默认 us-ascii bytes，中文/UTF-8 文档 round-trip 需显式）
  - `clean_tree` 的 `.getparent()`/`.index()`（lxml 特有，stdlib Element 无）→ 自建 `_collect()`（文档序节点列表 + id→父映射），删 del 顺序无关、解包 ins 逆序处理兼容嵌套修订对
  - 顶部 docstring「依赖：纯标准库（zipfile + lxml）」自相矛盾 → 改「zipfile + xml.etree.ElementTree」，零 pip 包
- **回归验证 4 样本全过**：合法 2 对修订 PASS / clean 稿 PASS / 坏稿三错齐报（缺 author·id 不成对·trackRevisions）/ 合法嵌套修订对 clean 化正确
- 触发：ibd-skills v0.1.0 冷启动验证（2026-09-10，报告 F1）；修复后 doc-review 4 脚本干净环境全部冷启动 OK

## [0.15.2] - 2026-09-09

### 增补：annotations.md §9 PDF 载体差异速览（同日文档补充，未 bump）

- 新增 §9「PDF 载体差异速览（Word ↔ PDF 对照）」：将 §1/§2/§5/§6/§8 中分散的 PDF 差异点（适用场景/转换禁令/锚定方式/纯文本弹注/首行前缀/颜色不承载语义/门禁差异/总览表）聚合为单节对照表——纯聚合零新规则，规范本体仍以各节为准；高亮颜色不承载语义 = annotate_pdf.py 实证行为（默认高亮色，无严重度映射）成文化
- 背景：多载体扩展规划（PDF/Excel/PPT）评估结论——规范层按「一个家多个房间」扩充，PDF 为第一个载体章节化先例

### 增补：annotations.md §3 编号体系「家族子编号」形态（复核批注数量纪律配套）

- 同根因跨位置（单锚无法就近覆盖）可共享主编号追加子字母 `J-01a/J-01b`；默认推荐形态 = 单批注 + desc 位置内联（门禁现兼容，某芯片设计项目 Z-06/Z-07 先例）；家族拆分采用前须扩展 check_annotations 编号唯一性校验支持子字母尾缀（当前按纯数字序号）
- 与 ibd-finance-review 细则 9（同源合并/数量卫生）、issue-list-format §1.1（覆盖单元）、ibd-doc-annotate validate_issues（同源自检 WARN）构成批注数量纪律四端一致

## [0.15.1] - 2026-09-06

### 变更（角色表述同步：README/frontmatter 去 data 残留）

- README 能力表删 data 4 项（金额格式/指标数值一致/表格计算/跨表勾稽），原位加迁移注记指向 `ibd-quality-gates` scripts/check_data.py
- frontmatter description 与 README 概述：核对项 14 → 10（text 6 + table 4），覆盖列表去「金额格式」
- README 快速开始 `--checks text,data` → `--checks text`，补数值自洽核对 gates 指针

## [0.15.0] - 2026-09-06

### 变更（data 组迁出：check_content 回归纯 docx text/table）

- **`scripts/check_content.py` 删除 data 组**（amounts/consistency/calc/cross_table + _to_num/_is_percent_after/金额正则/METRIC_VAL_RE）——整体迁 `ibd-quality-gates` scripts/check_data.py（归属归位：数值自洽属内容层关切），脚本 1473 → 1124 行
- **删除 md 前端**（load_markdown/MD_TABLE_SEP_RE/run 分流）：md 载体随 data 组迁走，本脚本回归纯 docx 载体（text 文字规范组 + table 表格样式/结构组，样式化后跑）
- `--checks` 传入 data 组相关 id → 打印迁移提示（指向 ibd-quality-gates scripts/check_data.py）；GROUPS 去 data 键；docstring/场景E/触发词/矩阵/边界/顺序规则同步（含 table_na 严重度拼写 MEDIIUM→MEDIUM 修正）
- **金额格式拆两层**：文本格式（千分位/小数位）随 amounts 迁 gates；呈现格式（表格内对齐/字号/合计加粗）留本 skill table 组
- SKILL.md 版本对齐 frontmatter → 0.15.0

---

## 历史版本归档

0.15.0 之前的版本记录已迁至 [`references/changelog-archive.md`](references/changelog-archive.md)，以免本文件无限膨胀。

| 版本区间 | 日期 | 归档位置 |
|---|---|---|
| **0.1.0 – 0.14.1**（24 个版本） | 2026-08-25 – 2026-09-06 | [changelog-archive.md](references/changelog-archive.md) |

> 归档文件位于 `references/`，其内部回指主文件用 `../CHANGELOG.md`。

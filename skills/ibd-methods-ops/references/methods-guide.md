# 方法论库规范（METHODS Guide）— 单一事实源

> 归属：**ibd-methods-ops**（生产侧规范源）；`ibd-doc-write` 的库指引为其**消费侧精简版**（无库降级），二者同源，细节以本文件为准。
> 适用：方法论库（`{METHODS_ROOT}`）的建立、条目结构、索引机制、规模化拆分与维护——本 skill 全流程（S1-S7/维护域）与 `ibd-methods-query` 检索链路共用本规范。

## 一、方法论库是什么

- 一个「按问题域索引的知识库」：写作/复核时按问题类型，定向查「这类问题以前怎么答得好」
- **它不属于任何 skill**：skill 只存通用高频句式；方法论库是使用者的业务知识积累（跨案例蒸馏沉淀）
- **存储形态三选一**（本地文件 / Obsidian / 云知识库连接器）——见下节「库形态与配置」
- 消费侧：`ibd-doc-write`（写作引用 + 引用自检）、`ibd-methods-query`（标准检索链路）

## 二、库接入与配置（开放后端 · 首次必配）

> **双向开放原则**：资料来源与沉淀去向都由用户自己确定——本节管「沉淀去向（库）」，材料来源见 SKILL.md 蒸馏域 S0。

方法论库**不锁定任何具体产品**——任何能存放/检索知识的载体都可接入：本地目录、Obsidian Vault、乐享、ima、其他 MCP 知识库、云文档等（**示例非穷举，由你在引导下自行接入**）。首次使用时由本 skill 引导配置；配置一次，全流程（蒸馏/检索/写作）自动按档位分派读写。

### 能力档位（接入前先定位 —— 决定可用能力）

| 档位 | 判定标准 | 典型载体（示例，非穷举） | 能力 |
|---|---|---|---|
| **A · 文件型** | 库能以「文件读写」访问 | 本地目录 / Obsidian Vault / 同步盘 / 任何可挂载路径 | **全能力**：索引生成 + 行号定向读取（token 最优） |
| **B · 检索型** | 库通过「服务接口 / 连接器」访问，以搜索为主 | 乐享、ima、其他 MCP 知识库、云文档 | 连接器检索（关键词/语义）→ 拉取条目；**无行号定位** |
| **A+B · 混合** | 文件型为主 + 云服务同步/备份 | 本地库 + 云端同步 | 以 A 档能力为主，B 档仅作同步/备份 |

### 接入引导（四问 · 对话式）

1. **库存在哪里？**——文件系统路径 / 云服务或连接器 / 命令行工具
2. **怎么读写它？**——直接读写文件 / MCP 工具 / CLI 命令
3. **它自带搜索或索引能力吗？**——自带 → B 档走其检索；没有 → 按 A 档由本 skill 建索引
4. **已有库还是从零建？**——已有 → 接管并做连通性验证；没有 → 按「建立与演进」起步

按四问定位档位 → 生成 `library.config.json` → **连通性验证**（读写成功 / 可检索）→ 记录配置，此后全流程按档位分派。

### 配置文件（library.config.json · 置于本 skill 安装目录，发布包不含）

```json
{
  "backend": "local",
  "access": "filesystem",
  "root": "~/methods",
  "connector": { "name": "", "space": "", "root": "" },
  "capabilities": { "indexable": true, "line_locator": true, "search": false },
  "notes_dir": "notes"
}
```

| 字段 | 说明 |
|---|---|
| `backend` | 库载体名（自由填：`local` / `obsidian` / `lexiang` / `ima` / 你的库名） |
| `access` | 访问方式：`filesystem`（文件读写）/ `mcp`（连接器工具）/ `cli`（命令行） |
| `root` | 库根位置（文件型填路径；检索型可留空或填逻辑名） |
| `connector` | 检索型必填：连接器名 + 空间/根节点标识（按你的库服务填写） |
| `capabilities` | 档位能力：`indexable`（能否生成本地索引）/ `line_locator`（能否行号定向）/ `search`（是否走服务检索） |
| `notes_dir` | 蒸馏笔记落库位置（相对 `root`；检索型可为逻辑目录名） |

**接入示例**（提示：产品名仅为示例，任何同类产品同法接入）：

- 本地目录：`{"backend":"local","access":"filesystem","root":"~/methods","capabilities":{"indexable":true,"line_locator":true,"search":false}}`
- Obsidian Vault：`{"backend":"obsidian","access":"filesystem","root":"~/Obsidian/MyVault/methods","capabilities":{"indexable":true,"line_locator":true,"search":false}}`
- 云知识库连接器（如乐享 / ima 等）：`{"backend":"<连接器名>","access":"mcp","connector":{"name":"<连接器>","space":"<空间>","root":"<根节点>"},"capabilities":{"indexable":false,"line_locator":false,"search":true}}`

### 库的双重角色

- **沉淀目的地**（默认）：蒸馏产出、笔记、条目统一落库（按档位分派，见下）
- **材料来源**（可选）：S0 可从库内取材料蒸馏（A 档读库内目录/案例素材/历史笔记；B 档走连接器检索）——**范围由用户指定**

### 行为分派（按档位）

| 环节 | A 档（文件型） | B 档（检索型） |
|---|---|---|
| 蒸馏笔记落库（S7①） | 写 `{root}/{notes_dir}/` | 连接器写入（空间/根节点下） |
| 条目落库（S7③） | `update_expert_md.py` 追加域文件 | 连接器写入条目（或本地维护 + 云端同步） |
| 索引生成（S7④） | `refresh_index.py`（四件套） | 不适用——检索走连接器搜索 |
| 检索（query） | 索引 → 行号定向读（Read/Grep） | 连接器关键词/语义搜索 → 拉取条目 |
| 库体检（维护域） | `check_methods_health.py` | 不适用（结构由连接器管理） |

> **能力差异（诚实声明）**：B 档下「渐进披露 + 行号定位」由连接器检索替代——token 效率与检索精度取决于连接器能力；追求最优检索效率推荐 A 档（索引体系完整可用）。**A+B 混合**可兼得：以 A 档为工作副本、B 档作同步/共享出口。

### 没有库？——起步路径

- **A 档**：建目录 + 3 个基础文件（见「目录结构」+「空库起步模板」）；Obsidian 则在 Vault 内建库目录，可加标签/双链增强
- **B 档**：在目标服务内建空间/知识库 → 直接开始沉淀（索引机制不可用，检索走其搜索）

## 三、目录结构

### 起步结构（3 文件 · 小库可用）

```
{METHODS_ROOT}/                      ← 库根目录（路径可配置）
├── _generated/                      ← 脚本生成物（**勿手改**）
│   ├── 通用方法论_最终版.md         ← 稳定入口：全部条目
│   ├── 方法论调用索引.md            ← 核心入口：问题域速查表（Q1-QN）→ 条目编号映射（兼编号唯一性凭证）
│   └── 方法论_条目标题目录.md       ← 标题 + 行号目录（行号定位精读，不全文翻找）
```

- **编号登记表已退役**（2026-09-01 迁 `archive/`，见 `govern/health-check.md`）：编号唯一性与防重改由**调用索引全量映射 ＋ 条目标题目录**保障；v36 遗留登记表仅作历史留痕，不再属活跃资产

### 规模化结构（域拆分 · 库大到单文件读取成本高时）

> **两个「根」先分清**：`{METHODS_ROOT}` = **库根/methods**（方法论正文区，下表缩进项均在其内）；**库根 = 工作区根** = `{METHODS_ROOT}` 的**上一级**——`app/ scripts/ state/ tasks/ docs/ logs/ archive/ cases/` 都在这一层。**脚本 `--methods-root` 传的是库根（工作区根），不是正文根**（2026-09-19 实测校正）。

```
库根（工作区根 · 脚本 --methods-root 传这一层）
├── app/                             ← 入口资产（daily_distill.py / config.json / wind_client.py / 注册计划任务.ps1）
├── methods/                         ← ＝ {METHODS_ROOT}，方法论正文区（**2026-09-23 C3b 目录八分**：一维度一物理层）
│   ├── README.md · 编号体系说明.md · 方法论_案名规范表.md   ← 入口层（元文件，留根）
│   ├── 行业方法论_合并映射.md · 投行语言_旧编号映射表.md     ← 入口层（元文件，留根）
│   ├── _generated/                  ← 脚本生成物（**勿手改**；条目扫面按 SKIP_DIRS 跳过）
│   │   ├── 通用方法论_最终版.md     ← 入口薄壳：域路由表 + 使用法（gen_entry.py）
│   │   ├── 方法论调用索引.md        ← 28Q 速查 + 全量映射（gen_index.py）
│   │   └── 方法论_条目标题目录.md   ← 编号 → 域文件+行号（gen_toc.py）
│   ├── 10_跨案域/                    ← 跨案层正文（通用方法论_{体例|财务|法律|行业}域.md，条目 h3 层）
│   ├── 20_语言专项/                  ← 投行语言专项_回复WL系列.md（WL- 回复语用）／投行语言专项_招股书PL系列.md（PL- 卷入口壳）
│   └── 30_行业版/             ← 行业方法论_{15 类}.md（单一公司行业研究 2026-09-23 起归位单案对应章）
│   ├── 40_单案/                      ← 单案范式文件（**82**；一案一文件，frontmatter 带 case_no 案号）
│   ├── 50_分卷/                      ← 正文外置卷（P 系列 / 体例域批次卷 / **F·L·I 域族卷**；2026-09-23 起三域按族外置：族号＝卷号，新增追加至对应族卷末尾，禁往壳文件追加）
│   └── 60_notes/                     ← 蒸馏笔记落库（KB 后端默认本地位置）
├── scripts/                         ← 库脚本（可从本 skill scripts/ 拷入，或直接用包内脚本）
├── state/                           ← 流程状态台账（单案索引对照表/待补学清单/体检计数/回写清单指针；**说明见该目录 README.md**）
├── tasks/ · docs/ · logs/           ← 任务与脚本 / 方案与审计 / 运行日志
├── archive/                         ← 归档（按 methods·scripts·state·tasks·docs·logs 镜像分层）
└── cases/                           ← 蒸馏原料（招股书/问询回复与产出；仅运行真身，不入云同步）
```

- **渐进披露**：入口薄壳（~10KB）→ 索引定位 → 按「域文件 + 行号」定向读单条（~20KB）——不全文读库
- **新增域零改码**：新增 `通用方法论_<域>域.md` 后重跑 `refresh_index.py`，路由表/索引/目录自动纳入

### 各层骨架形态（**设计差异** · 2026-09-23 定版）

> 各层**不是同一套骨架**，这是设计而非漂移。可套用模板见 `references/templates/`；**例外清单**见其 `README.md`「已知例外」节。

| 层 | 骨架形态 | 说明 |
|---|---|---|
| `10_跨案域/` | **扁平追加式**：无 h2 分组，条目 h3 按**时间序**追加 | 族前缀 `F/L/I/S` 承担分组职能 ⇒ **刻意不加 h2**。转正新条目一律追加至章末＋标题批次尾注溯源（规程见 `govern/fix-tools.md`）。**勿按「缺 h2 骨架」处置** |
| `40_单案/` | **七节骨架**（〇画像／一财务／二法律／三行业／四写作范式／五专家引用／六质量自评） | 模板 `tpl_单案范式文件.md`；护栏第 14 项按此比对。早期批次 h1 体系与「第 2 类」独立文件属**异体系**，列为豁免 |
| `30_行业版/` | **四段骨架**（类总览／共通方法论章／子行业特有章／覆盖核对表） | 模板 `tpl_行业合并版.md`；`I-CL` 条目须落在**共通章**（护栏第 12 项） |
| `20_语言专项/` · `50_分卷/` | `WL-` 文件型（回复语用）／`PL-` **卷入口壳＋外置卷** | 两者名实已对齐（WO-06）；P 系列正文禁往壳文件追加 |
| `10_跨案域/` · `50_分卷/` | `F-`／`L-`／`I-` **域壳（0 条目）＋族卷**（`通用方法论_<域>_卷NN_<族名>.md`） | **2026-09-23 按族外置 ＋ 族内分段**：族＝切分单元、与族大小无关（利于扩展）；族号已冻结；**PL／S 因「族少族内条多」，族内再按 163KB 阈值均衡分段**，卷号＝`<族号>-<段号>`（如 `卷01-1`）；新增追加至该族**末段**末尾。**PL 族号 2026-09-23 由 15–19 重排为 01–05**（全库编号同步改写 5,972 处） |

## 四、条目结构规范（新条目必须遵守）

> **骨架模板**：可直接复制成新文件的**七节骨架／四段骨架／条目块／笔记骨架**在 **[templates/](templates/README.md)**（4 份，含机器比对锚点 `<!-- ANCHOR -->`）。本节与契约册只讲**规则**，模板负责「照什么写」。

- **编号体系**：主库 `域-族号2位-族内4位`——`F-010001`（财务 01-18）/ `L-010001`（法律 01-19）/ `I-010001`（行业 01-15）/ `S-010001`（体例 01-04）；语言层按文档类型分 `WL-xx-xxxx`（回复）/ `PL-xx-xxxx`（招股书）。**追加 = 目标族内 max+1**（族号查登记表）；集中分配（防重叠），永不回收
- **案例层编号**（单案范式落库）：知识 `域-AN{案号4位}-2位`、范式 `W-AN{案号4位}-{类}{2位}`；案号 4 位由主理人在批登记表顺序分配禁自编
- **条目字段与排布**：**本册不定义** —— 单一事实源＝[entry-contract.md](entry-contract.md)（实证项**四字段模型**＝案名＋案号＋内容＋来源／**三种排布**／来源标注契约／标签禁用四条；单案层 **10 个**规范要素）。本册只登记**编号与库结构**，字段名一律以契约为准（原「四段结构」节 2026-09-23 删除，其字段名 `方法论要点` 已是废止别名）。
- **铁律**：规则冲突走「修订留痕」（旧条目追加修订记录行），禁止静默覆盖

## 五、建立与演进（两种方式）

### 方式 A：边用边长（推荐起步）

1. **建库**：创建 `{METHODS_ROOT}` + 按起步结构建 3 个基础文件（空索引模板见文末）
2. **直接开始写作/复核**：无库阶段跳过查库环节，凭通用句式与规范完成
3. **每次使用后沉淀（关键回环）**：复盘「哪条可复用结论/句式值得记录」→ 分配编号 → 按四段结构追加条目 → 跑 `refresh_index.py` 刷新（调用索引 + 条目标题目录 + 路由入口一次同步）→ 高频条目（≥5 案）回流入写作高频句法库
4. **积累 10-20 条后**：体验质变——查得到自己的经验，引用有据可依
5. **长期维护**：固定节奏（如每月）复核索引与条目完整度，补齐「待沉淀」问题

### 方式 B：蒸馏式积累（完整版）

- 批量复盘案例材料：按本 skill 蒸馏域 S0-S7 全流程——**学习范围由用户自己确定**（对话给单文件 / 文件夹 / 项目目录，或**从已接入的库取材料**，可组合；未指定才走候选池）→ 材料准备 → 多专家并行精读 → 综合成文 → 共通点蒸馏 → 沉淀入库
- 产出结构化程度高（条目 + 跨案标注 + 行业归组）；团队模式可多角色协作，单用户模式本人分维度串跑
- 完整流程见 SKILL.md「蒸馏域」；提炼方法见 [distill-methods.md](distill-methods.md)

## 六、索引生成机制（改内容后必刷新）

> **为什么必刷**：索引给出的「文件 + 行号」是定向读取的**唯一键**——改内容不刷 ⇒ 行号漂移 ⇒ 定向读会读到**别的条目且不报错**（静默缺陷）。刷完用 `check_index_locator.py --methods-root <工作区根>` 抽查 12 条即可确认无漂移。

| 生成物 | 生成脚本 | 作用 |
|---|---|---|
| `_generated/方法论调用索引.md` | gen_index.py | 28Q 问题域速查表 + 全量映射 + 跨域桥接速查表（Q → 各域代表条目） |
| `_generated/方法论_条目标题目录.md` | gen_toc.py | 编号 → 域文件 + 行号（定向读取定位） |
| `_generated/通用方法论_最终版.md`（入口薄壳） | gen_entry.py | 域路由表（条目数/行数/体积）+ 使用法；摘要区保留不覆盖 |

- **一键刷新**：`python scripts/refresh_index.py --methods-root <工作区根>`（parse → gen_index → gen_toc → gen_entry，任一失败即停）——**参数传库根（工作区根），不是 `{METHODS_ROOT}`**；直传正文根会得到 `<正文根>/methods` 并报「未找到方法论库」
- **铁律**：条目标题/编号/行号变动后**必须刷新索引**——行号漂移会污染定向读取（检索链路按行号定位）

## 七、库维护工具链（随本 skill scripts/ 发布）

| 场景 | 脚本 |
|---|---|
| 库健康体检（16 项护栏） | check_methods_health.py |
| 索引刷新（一键四件套） | refresh_index.py |
| 条目落库（追加 + 超线归档） | update_expert_md.py |
| 结构修复（frontmatter/结构归一/去重） | add_frontmatter.py / add_fm_single.py / b_fmt_unify.py / c_scale_dedup.py |
| 规模化拆分（单体 → 域文件） | split_domains.py（配置驱动，G1 条目守恒自校验） |
| **按族外置（域文件 → 族卷）** | **split_domain_by_family.py**（2026-09-23 新增 · 配置驱动 · G1 条目守恒＋G2 内容零改动＋G3 壳内无残留三校验；族名入 `tasks/split_family_config.json`） |
| 编号迁移（位宽变更） | ~~dryrun_case_migrate.py → migrate_case_no.py~~（**2026-09-23 退役**，路径形态停留 09-16 归拢前；迁移规程见 `govern/fix-tools.md` 附） |

- 使用：`--methods-root` 指定库根（或设环境变量 `METHODS_ROOT`）；破坏性脚本先 `--dry-run`
- **批量脚本安全铁律**：dry-run 必须真正只读；迁移脚本幂等或只跑一次；全库替换前先抽上下文分类；重大变更前备份至 archive/

## 八、规模化：域拆分（何时拆 / 怎么拆）

- **触发**：单文件体积超过警戒线（默认 300KB，`check_methods_health.py` WARN）或条目数增长导致全文读取成本过高
- **铁律**：拆分**只搬位置、不改内容**（纯行号切割）——G1 条目守恒 + G2 内容零改动为验收标准
- **做法**：
  1. 编写拆分配置（JSON：源文件 + 各域行号段 + 章头映射，格式见 `scripts/split_domains.py` docstring）
  2. `python scripts/split_domains.py --config <配置> --dry-run` 预检 → 正式执行（自动备份源文件）
  3. 拆分后跑 `refresh_index.py` 刷新生成物 + `check_methods_health.py` 复验
- 拆分后入口变为薄壳（路由表自动维护），检索链路仍按「域文件 + 行号」定位（目录由 gen_toc.py 给出）

## 九、空库起步模板（方法论调用索引.md）

```markdown
# 方法论调用索引（空库起步）

## 问题域速查表
> Q 域可按你的业务自定义扩展（示例：收入确认/毛利率/对赌清理/实控人/客户集中/募投产能消化/关联交易…）
| Q 编号 | 问题域 | 条目编号 |
|--------|--------|---------|
| Q1 | 收入确认 | （待沉淀）|
| Q2 | 毛利率 | （待沉淀）|
| Q3 | 对赌清理 | （待沉淀）|
| ... | ... | ... |

## 全量映射表
> 新增条目后在此登记：Q 域 → 条目编号 → 标题
```


---

## 附：随包脚本全量清单（26 个 · 自 `SKILL.md`「随包脚本」节原样迁入 · 2026-09-21 瘦身）

> 本附是**脚本用途与命令形态**的事实源；`SKILL.md` 只留四类分组摘要 ＋ 指向本节。脚本本体单一事实源仍是 `scripts/`。

**适用范围**：脚本面向 **A 档（文件型）库**（索引体系与体检均基于文件，Obsidian 等 Markdown 载体同构适用）；**B 档（检索型）**下索引类脚本不适用（检索与结构由连接器管理，见 methods-guide §二分派表）。

```
# —— 索引体系（S7 刷新链路，refresh_index.py 一键编排四件套）——
python scripts/refresh_index.py --methods-root <工作区根>   # 一键：parse → gen_index → gen_toc → gen_entry
python scripts/parse_titles.py ...        # ① 解析条目 → parsed_titles.txt
python scripts/gen_index.py ...           # ② 生成 方法论调用索引.md（28Q 速查 + 全量映射 + 跨域桥接）
python scripts/gen_toc.py ...             # ③ 生成 方法论_条目标题目录.md（编号 → 域文件+行号）
python scripts/gen_entry.py ...           # ④ 重写入口（路由表 + 摘要保留，幂等）

# —— 落库与门禁 ——
python scripts/update_expert_md.py --entries <条目.json> ...   # S7 落库：追加条目（h3/表格双形态）+ 超线归档
python scripts/check_expert_output.py --dir <案目录>           # S4.5 产出自检门禁（0 FAIL 才进 S5）
python scripts/gen_replay_worksheet.py --case <N> [--filter 高] # S7 回写工作表：清单候选 × 单案新条目 × 主库旧条目 三方汇编
python scripts/normalize_pl_s.py --methods-root <工作区根> [--cases ...] [--apply]  # S5 后 · PL/S 编号归一（族内连续·零撞号·**幂等**；已入库案自动跳过）
python scripts/apply_rewrite.py --methods-root <工作区根> [--repair] [--apply]     # S7-b · 回写执行（高→实证区／中高→独立段；--repair 修截断行）
python scripts/check_entry_contract.py [--json]                # 书写契约自检（回写落盘前置：0 ERROR 才允许 --apply）
python scripts/replay_gate_report.py ...                       # S7 收尾：回写硬门禁四项指标 dry-run 报告（软执行·不阻断）

# —— 维护域 ——
python scripts/check_methods_health.py ...                    # 16 项护栏体检（0 ERROR 交付）
python scripts/add_frontmatter.py ...      [--dry-run]         # 修复：补 frontmatter
python scripts/add_fm_single.py ...        [--dry-run]         # 修复：单份细分版补 frontmatter（该载体 2026-09-23 停用 ⇒ 脚本退役候选）
python scripts/b_fmt_unify.py ...          [--dry-run|--verify] # 修复：域文件结构归一
python scripts/c_scale_dedup.py ...                            # 修复：量表/重复内容收敛
python scripts/normalize_case_names.py ...    [--apply]       # 案名回改（规范案名＝证券简称；幂等·干跑优先）
python scripts/apply_case_no.py ...           [--apply]       # 案号写回（表驱动·幂等·冲突不自动改）
python scripts/backfill_volume_refs.py ...    [--report <f>]  # 分卷来源案/TBD 回填（相似度推断版）
python scripts/fix_volume_case_by_segment.py ... [--apply]    # 分卷按「### 案批次」案节校正归属（推荐口径）
python scripts/sync_cases_md.py ...           [--apply]       # cases/**/*.md 镜像入 git 仓（增量·幂等）

# —— 库演进（规模化与编号迁移）——
python scripts/split_domains.py --config <拆分配置.json> [--dry-run]   # 单体库 → 域文件拆分（G1 条目守恒自校验）
python scripts/split_domain_by_family.py [--config <族配置.json>] [--apply]  # 域文件 → 薄壳＋族卷（默认 dry-run；G1/G2/G3 三校验）
# ~~dryrun_case_migrate.py / migrate_case_no.py~~  ——  编号迁移两脚本 **2026-09-23 退役**（见 govern/fix-tools.md）

```

**书写契约（实证段同规）**：条目实证项的字段模型／三种排布／来源标注格式／标签禁用四条 → `references/entry-contract.md`（v1.0 · 用户裁定 D1–D5）；自检门禁 `scripts/check_entry_contract.py`。


---

## 附：首次接入引导流程（四问 · 自 `SKILL.md`「库配置」节原样迁入 · 2026-09-21 瘦身）

1. 检查本 skill 安装目录下 `library.config.json`——存在且字段完整 → 直接进入流程；缺失 → 执行第 2 步
2. **向用户提四问**（对话式引导，不预设产品）：
   - 库存在哪里？（文件系统路径 / 云服务或连接器 / CLI 工具）
   - 怎么读写它？（直接读写文件 / MCP 工具 / 命令行）
   - 它自带搜索或索引能力吗？（自带 → B 档走其检索；无 → A 档由本 skill 建索引）
   - 已有库还是从零建？（有 → 接管 + 连通性验证；无 → 按 methods-guide「建立与演进」起步）
3. 按四问定位**能力档位**（A 文件型 / B 检索型）→ 生成 `library.config.json`（模板见 [library.config.template.json](library.config.template.json)）→ **连通性验证**（读写成功 / 可检索）
4. 记录配置结果，此后全流程按档位分派读写（分派表见 methods-guide §二）

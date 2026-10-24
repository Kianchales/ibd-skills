---
name: ibd-methods-ops
slug: ibd-methods-ops
displayName: IBD 方法论学习与维护
description: 方法论知识库「生产 + 维护」双域全流程。生产域=案例蒸馏沉淀（选材→材料准备→三专家并行蒸馏→写作角色综合成文→共通点蒸馏→沉淀入库→索引刷新→护栏校验），触发词「执行蒸馏学习XX次」「蒸馏学习XX次」；维护域=方法论库结构健康（护栏体检/编号归一/去重/修复工具箱），触发词「方法论体检」「方法论治理」「库结构检查」。方法论库路径可配置（METHODS_ROOT），知识库后端可配；支持单用户模式（默认）与团队模式（可选）。
summary: 方法论知识库「学习（产知识）+ 维护（保健康）」一体化——案例蒸馏沉淀新方法论 + 库结构健康护栏 + 随包脚本工具链（33 个），路径与知识库后端可配置。
agent_created: true
version: 1.38.0
---

# ibd-methods-ops

## 定位简介

> **设计原则 · 双向开放**：**资料来源与沉淀去向都由用户定**——材料从哪来（对话给文件／文件夹／项目，或已接入的库）、沉淀到哪去（本地／Obsidian／云知识库）；skill 只提供流程、规范与工具，不绑定私有环境、不自行扩大范围。

方法论知识库「学习（产知识）+ 维护（保健康）」一体化——学习域把案例蒸馏为新方法论，维护域保证库结构健康；二者操作同一库（`{METHODS_ROOT}`）、频率同频（批量学习后随即导入维护），故合并为一个 skill。

- **路径可配置**：全流程以 `{METHODS_ROOT}`（**方法论正文根**，＝库根/methods）为基准；**库根＝工作区根**（正文根的上一层，`app/`·`scripts/`·`state/`·`tasks/` 所在）——两词勿混；库结构规范见 [methods-guide.md](references/methods-guide.md)
- **规则地图**：库规则（体系层判据／库层契约与编号／执行层门禁／触发层流程）收敛为导航 → [library-rules.md](references/library-rules.md)（含冲突裁决顺序与 12 条易误解点）；细则事实源在本文件与各 references，总览只做导航
- **学习范围由用户自己确定**：材料来源开放（单文件／文件夹／项目目录／已接入的库，可组合），skill 不自行扩大；未指定时才走候选池
- **库接入开放后端**：不锁定产品（本地目录／Obsidian／乐享／ima／任意 MCP 知识库）；首次按「库配置」四问接入，此后按能力档位（A 文件型／B 检索型）分派读写
- 分合决策与改名记录见 CHANGELOG.md

## 何时使用（双触发域路由）

| 触发语 | 域 | 入口 |
|--------|-----|------|
| 「执行蒸馏学习XX次」「蒸馏学习XX次」 | 蒸馏域 | 走下方 S0-S7 全流程 |
| **指定学习范围**（对话给文件／目录／项目路径，或指定库内范围） | 蒸馏域 | **范围由用户定**，从 S0 起（跳过候选池选材） |
| 「方法论体检」「方法论治理」「库结构检查」「护栏检查」 | 维护域 | 走下方「维护域」3 步 |
| automation 触发（批量） | 蒸馏域 | 按 automation 提示词执行（频次／标的数以提示词为准） |

## 库配置（首次使用必配 · 开放后端）

> **不锁定产品**：库可为本地目录／Obsidian／乐享／ima／任意 MCP 知识库（示例非穷举，**由用户自行接入**）——能力档位与完整配置见 [methods-guide.md](references/methods-guide.md) §二。

**首次接触任一库（含已配好的库）· 先读库根 `SCHEMA.md`**：**库自描述入口**——一页回答「本库由谁管、schema 版本水位、规矩在哪读、机器会拦什么」，**规矩在哪不必问使用者**。由 `gen_schema.py` 派生、随索引刷新自动跟上，**勿手改**。

**首次接入**：查本 skill 安装目录 `library.config.json`（模板 [library.config.template.json](references/library.config.template.json)）——字段完整 → 直接进流程；缺失 → 按「四问」（库在哪／怎么读写／自带检索吗／已有还是从零建）→ 定档位（A 文件型／B 检索型）→ 生成配置 → **连通性验证**。四问原文与分派表 → [methods-guide.md](references/methods-guide.md) 附：首次接入引导流程。
**从零建库 → 就绪验证 → 沉淀 → 检索 的串联示例** → [examples.md](references/examples.md)。

## 执行目录约定（违反即报错）

- 库读写**一律以 `{METHODS_ROOT}` 为基准**（脚本、材料、方法论只读写该目录）
- automation／会话平台 cwd 仅为壳，**不得在会话目录新建或修改库数据**
- 命令前先 `cd {METHODS_ROOT}`；随包脚本统一支持 `--methods-root <工作区根>` 或 `$METHODS_ROOT`
  - 🔔 **参数语义**：`--methods-root` 传**工作区根**（非库本身）——直传库会得到 `<库>/methods` 并报「未找到方法论库」；`library.config.json` 的 `root` ＝库目录本身，两者不同。校正与分派表 → [methods-guide.md](references/methods-guide.md) §一／§二
- **用户提供的材料路径**不受库目录限制——按给定路径只读，不写入不搬移；**从库取材料**同样只读（A 档读文件／B 档检索）；蒸馏产出统一落库

## 蒸馏域：全流程（S0-S7）

> **学习范围由用户自己确定**；skill 不自行扩大范围。
> **详规在册**：每步详规全在 [distill-methods.md](references/distill-methods.md)——**步骤执行卡片**见「附 A」（答「谁做／做什么」），**提炼方法详表**见同名 §（答「怎么做」）。本表只留「步骤 ＋ 执行者 ＋ 一句话判据 ＋ 册节号」。
> **团队模式**：主理人编排（TeamCreate → Agent spawn → SendMessage），三专家并行；单用户模式本人分角色串跑。**协作铁律**：TeamCreate 必须主理人执行；三专家 spawn 须同一条消息并行；跨成员信息一律经主理人中转，不得直连；角色定义见各步「执行者」列。

| 步骤 | 执行者 | 判据（一句话） | 详规 |
|------|--------|------|------|
| **S0** 材料来源与范围（起点） | 用户 | 范围由**用户**给定（单文件／文件夹／项目／已接入的库，可组合）；**未指定时才走候选池 S1** | 附 A §S0 |
| **S1** 范围确定与选材（候选池来源） | 主理人（可选脚本） | 用户已给范围 → **跳过**；候选须已有「上会稿」，并先读 `state/待补学清单.md` | 附 A §S1 |
| **S1.5** 审完校验 | 主理人 | 审完标志＝**材料齐备**（有最终稿）；未齐登记 `state/待补学清单.md`，已披露最终稿者优先补学（笔记后缀 `_补学`） | 附 A §S1.5 |
| **S2** 行业定位 | 主理人 | 记录**证监会 ＋ 国民经济行业分类**（无数据终端则降级：披露口径 ＋ 公开信息交叉验证） | 附 A §S2 |
| **S3** 材料准备 | 主理人（可选脚本） | ①只读最新稿（注册稿＞上会稿＞申报稿，同 stage 取披露最新）②每轮回复只读最新版 → 生成**财务／法律／行业三包**（S4 输入降约 2/3） | 附 A §S3 |
| **S3.5** 旧条目预取 | 主理人 | 按 **28Q 问题域** ＋ 行业类预取 5-10 条旧条目（编号＋标题＋一行摘要）注入阅读包头部；S4 产出自带关系标注 | §S3.5 |
| **S4** 三专家并行蒸馏 | 财务/法律/行业专家 | 三段式产出落 `产出_<维度>_蒸馏.md`；**S4.5 门禁** `check_expert_output.py` **0 FAIL 才进 S5** | §S4（门禁 §S4.5） |
| **S5** 综合成文 ＋ 写作范式 | 写作角色 | **五步提炼法**综合三方 ＋ 亲读原文提炼「投行语言」词汇句法库 → 通用 ＋ 行业方法论（单案范式七节骨架）；三轨产出后跑 `normalize_pl_s.py` **归一 PL/S 编号**（族内连续·零撞号·幂等） | §S5 |
| **S5.5** 模拟回复演练 | 写作角色 | 独立撰写 → 回查原文补齐 → 与真实回复对比，**差距清单 ≥3 条**并写回 | §S5.5 |
| **S6** 共通点蒸馏 | 主理人（可委写作角色） | **S6a 轻量映射 ≤50 行每轮必做**（校验＋补漏＋定稿分级）；「本次＋历史未复盘」≥10 触发 **S6b** 全量蒸馏 | §S6 |
| **S7** 沉淀入库 | 主理人 | 落库 ＋ **回写池三过滤**（复现 2 次即并入／冲突改旧／用户裁定再裁定）→ `apply_rewrite.py` 回写（高→实证区／中高→独立段）→ `refresh_index.py` **必刷索引** → `check_methods_health.py` **0 ERROR** ＋ `check_index_locator.py` 抽查 12 条行号 → **待补学销项**；任一不过转维护域 | 附 A §S7 ＋ [entry-contract.md](references/entry-contract.md) 附：S7 回写执行纪律 |

> **库主从关系**：**本地 `{METHODS_ROOT}` ＝ 单一事实源**——索引刷新、护栏校验、S6/S7 机制均以本地为准；**云知识库后端 ＝ 只读发布镜像／检索前端**，向其写入属**同步动作、非创作**——禁止在云侧直接改方法论内容，发现本地有误回本地改后重新同步；双侧分叉以本地为准整体覆盖。

## 维护域：护栏体检 + 修复（3 步）

> **触发节奏**：并入批量蒸馏——每累计满 N 案例（建议 40）、S7 完成后顺带跑一次（计数文件 `<工作区根>/state/维护体检计数.md`）；亦可按触发词随时发起。
> **同节奏议题**：行业分类合并评估只在本体检触发（平时只归口、不合并；单案正常新立类）——规则见 [library-rules.md](references/library-rules.md) §2.5。
> **体检前置 · 审计面**：**作用面须显式枚举**，不得默认等同 `methods/`——① 库内正文（`40_单案/`／`50_分卷/`／`30_行业版/`）② 库内归档 `cases_md/` ③ **蒸馏现场 `{工作区}/cases/`**。**凡查产出件／案目录，① ③ 并查**（「库内搜不到」≠「不存在」）。
> **详规在册**：[govern/health-check.md](references/govern/health-check.md) 附：维护域三步执行详规；步骤名是导航、不下沉。

| 步骤 | 动作 | 判据（一句话） | 详规 |
|------|------|------|------|
| **1 体检** | `cd {METHODS_ROOT} && python <skill>/scripts/check_methods_health.py` | **26 项护栏 0 ERROR**——结构／编号唯一连续／路由表计数 vs 实算／索引行号／条目契约／骨架／登记表对账／schema 水位等；**逐项与阈值以册为准** | [health-check.md](references/govern/health-check.md) |
| **2 修复** | 按 ERROR 类型选脚本（`add_frontmatter`／`b_fmt_unify`／`c_scale_dedup` 等） | **先 dry-run 后执行**；工具箱索引与三个单一事实源边界见册 | [fix-tools.md](references/govern/fix-tools.md) |
| **3 复验** | 重跑 `refresh_index.py` ＋ 复跑护栏 | **0 ERROR 且幂等** | health-check.md 附 §3 |

> **全库编号迁移踩坑实录**（案号 2→4 位化：正则 `\b` 汉字漏匹配／迁移脚本幂等／表行国标码误伤／四门复验）→ [govern/fix-tools.md](references/govern/fix-tools.md) 附。

## 随包脚本（33 个 · 参数与 §执行目录约定 同）

> **计数口径**：33 ＝ `scripts/*.py`（用户面可执行，不含 `scripts/_lib/` 内部模块）；`add_fm_single.py` 已随「单份细分版」载体停用 ⇒ **在用 32 个**。计数由护栏「文档计数一致性」项对账。**逐条用途与命令形态** → [methods-guide.md](references/methods-guide.md) 附：脚本全量清单。
> **适用范围**：面向 **A 档（文件型）库**（索引与体检基于文件，Markdown 载体同构）；**B 档（检索型）**下索引类脚本不适用（结构由连接器管理）。

| 组 | 脚本（概要不展开） |
|---|---|
| **索引体系** | `parse_titles`／`gen_index`／`gen_toc`／`gen_entry`／`refresh_index`（一键编排）／`gen_refgraph`／`gen_schema`（库内 `SCHEMA.md`）／`check_index_idempotent`／`gen_source_map`（材料变更后跑） |
| **落库与门禁** | `update_expert_md`／`check_expert_output`（S4.5 门禁）／`gen_replay_worksheet`／`check_entry_contract`／`replay_gate_report`／`check_evidence`（溯源·门禁外只报不改）／`gen_recon_anchors`／`check_index_locator` |
| **维护域** | `snapshot_entries`（改动前后快照 diff）／`check_methods_health`／`add_frontmatter`／`add_fm_single`（已退役）／`b_fmt_unify`／`c_scale_dedup`／`normalize_case_names`／`apply_case_no`／`backfill_volume_refs`／`fix_volume_case_by_segment`／`sync_cases_md`／`log_event` |
| **库演进** | `split_domains`／`split_domain_by_family`（按族外置）／`normalize_pl_s`／`apply_rewrite`（S7 回写） |

- **书写契约**：条目实证项字段模型／三种排布／来源标注／标签禁用四条 → [entry-contract.md](references/entry-contract.md)（v1.0 · 用户裁定 D1–D5）；自检门禁 `check_entry_contract.py`

## 依赖与工具

> 依赖来源标注：⬛=随包/本地自建；🟢=可选；🟦=内置。

- **Python 3**〔🟦内置〕：33 个随包脚本（零第三方依赖）
- **方法论库 `{METHODS_ROOT}`**〔⬛随包/本地自建〕：库规范见 [methods-guide.md](references/methods-guide.md)
- **KB 后端**〔🟢可选〕：默认本地目录；可接入 MCP 知识库／云文档连接器（见「库配置」）
- **团队协作工具**〔🟢可选〕：团队模式用 TeamCreate／Agent 消息；单用户模式无需

**缺失降级**：无库 → **空库起步档**（`methods-guide.md` 空库模板 ＋ 边用边长）；维护域无库可检时如实报「无对象」，不阻断；无 KB 后端 → 本地照常跑，仅失去镜像同步；无团队工具 → 单用户串跑。

## 资源索引（skill 只引用路径，不复制内容）

- **[methods-guide.md](references/methods-guide.md)**〔⬛随包〕：**库规范单一事实源**（目录／条目／建立与演进）＋ 脚本全量清单 ＋ 首次接入四问
- **[distill-methods.md](references/distill-methods.md)**〔⬛随包〕：蒸馏**提炼方法**单一事实源（S4 三段式／S5 写作范式／S5.5 演练／S6 共通点）＋ 附 A 执行卡片 ＋ 附 B 角色定义
- **[entry-contract.md](references/entry-contract.md)**〔⬛随包〕：条目与回写书写契约（四字段模型／三种排布／来源标注／标签禁用）＋ S7 回写纪律 12 条
- **[library-rules.md](references/library-rules.md)**〔⬛随包〕：库规则总览（四层地图 · 裁决顺序 · 12 条易误解点）——只做导航
- **[examples.md](references/examples.md)**〔⬛随包〕：上手串联示例 ＋ 三个易踩坑（空库不跑全库体检／配置是本机文件／缺口登记勿另起名目）
- **govern/**〔⬛随包〕：[health-check.md](references/govern/health-check.md) 护栏 26 项＋三步详规｜[fix-tools.md](references/govern/fix-tools.md) 修复工具箱＋编号迁移踩坑｜[adversarial-review.md](references/govern/adversarial-review.md) 对抗性复核判据（S7 复盘，只标不改）｜[design-boundaries.md](references/govern/design-boundaries.md) 设计边界 15 条
- **[templates/](references/templates/README.md)**〔⬛随包〕：**骨架模板单一事实源**（4 份：单案范式／行业合并版／跨案域条目块／蒸馏笔记）——新建从此复制
- **方法论库 `{METHODS_ROOT}`**〔自建〕：`_generated/通用方法论_最终版.md`（路由入口）＋ 各域正文 ＋ 调用索引 ＋ 条目标题目录 ＋ 引用图谱（反向视图＋对账）＋ 来源代号映射；生成物统一隔离于 `methods/_generated/`
- **KB 后端**〔🟢〕：笔记默认落 `{METHODS_ROOT}/60_notes/`；可选外部连接器

## 关键要点（纪律索引）

> 纪律全局导航（主题 → 哪一步 → 落点册）：大全见 [library-rules.md](references/library-rules.md) 附「纪律索引」；各步骤处已内联指针。

## 维护（何时需要改本 skill）

> **沉淀后必做自检（S7）**：每轮蒸馏后对照本表——**方法论内容更新 → 不改本 skill**（`refresh_index.py` 自动维护）；流程／脚本／门禁变化 → 改本 skill；体检项／修复脚本变化 → 改 `references/govern/`。结果记入蒸馏笔记。

| 变化类型 | 改 skill？ | 动作 |
|---------|-----------|------|
| 方法论内容更新（新案、升版、索引刷新） | ❌ | 跑 `refresh_index.py`（自动维护索引／目录／入口） |
| 流程／SOP（S 步骤、脚本命令、门禁） | ✅ | 改本 skill 对应章节 |
| 提炼方法（三段式／范式／共通点） | ✅ | 改 [distill-methods.md](references/distill-methods.md) |
| 库结构规范（目录／条目） | ✅ | 改 [methods-guide.md](references/methods-guide.md) |
| 护栏项／修复脚本 | ✅ | 改 `references/govern/` 对应文件 |
| 新踩坑／反模式 | ✅ 追加 | 在册的对应「附」节追加（本表只留索引） |

## 边界与协作

- **与 ibd-methods-query 互补**：本 skill 管生产＋维护（写入侧），query 管检索消费（读取侧）——查询走 query 的标准检索链路，不经本 skill
- **冷启动分工**：首次无库时，query 的**冷启动引导档**可就地建空库骨架（[methods-guide.md](references/methods-guide.md) §三 起步结构 ＋ 最小 `library.config.json`，纯结构零内容）——属检索前置自举，内容生产仍归本 skill
- **被依赖声明**：`ibd-doc-write`／`ibd-methods-query` 可选依赖本 skill（≥1.5.0）
- **库结构规范单一事实源**：[methods-guide.md](references/methods-guide.md)；`ibd-doc-write` 的库指引为其消费侧精简版（含无库降级），二者同源
- **高频句法反哺 doc-write**（可选，未装跳过）：只同步**通用高频句式**；**案例级条目留 `{METHODS_ROOT}/`**，双轨不混
- **格式规范归 doc-review**：方法论文件的格式问题移交 `ibd-doc-review`，本 skill 不自建格式规则
- **不设第二源**：索引刷新 → `refresh_index.py`；脚本 → 本包 `scripts/`（边界声明见 [govern/fix-tools.md](references/govern/fix-tools.md)）
- **「体检」域归属（消歧）**：**方法论库体检／库结构检查** → 本包；**skill 体系体检**与**仓库体检**不在本包范围。本包触发词里的「体检」**只指方法论库**（本包为**公开包**，按发布侧约束不列私有件名）

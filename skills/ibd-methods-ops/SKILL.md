---
name: ibd-methods-ops
slug: ibd-methods-ops
displayName: IBD 方法论学习与维护
description: 方法论知识库「生产 + 维护」双域全流程。生产域=案例蒸馏沉淀（选材→材料准备→三专家并行蒸馏→写作角色综合成文→共通点蒸馏→沉淀入库→索引刷新→护栏校验），触发词「执行蒸馏学习XX次」「蒸馏学习XX次」；维护域=方法论库结构健康（护栏体检/编号归一/去重/修复工具箱），触发词「方法论体检」「方法论治理」「库结构检查」。方法论库路径可配置（METHODS_ROOT），知识库后端可配（默认本地目录，可选连接器）；支持单用户模式（默认）与团队模式（可选）。
summary: 方法论知识库「学习（产知识）+ 维护（保健康）」一体化——案例蒸馏沉淀新方法论 + 库结构健康护栏 + 随包脚本工具链（26 个），路径与知识库后端可配置。
agent_created: true
version: 1.21.2
---

# ibd-methods-ops

## 定位简介

> **设计原则 · 双向开放**：**资料来源与沉淀去向都由用户自己确定**——材料从哪来（对话给文件/文件夹/项目，或已接入的库）、知识沉淀到哪去（本地/Obsidian/云知识库等接入的库），全部由用户定；skill 只提供流程、规范与工具，不绑定任何私有环境、不自行扩大范围。

方法论知识库「学习（产知识）+ 维护（保健康）」一体化 skill——学习域把案例（招股书 + 问询回复）蒸馏沉淀为新方法论，维护域保证方法论库结构健康；二者操作同一库（`{METHODS_ROOT}`）、频率同频（批量学习后随即导入维护），合并为一个 skill 实现连续工作流。

- **运行模式**：① **单用户模式（默认）**——本人按 S1-S7 串跑全流程，材料自备或手工准备；② **团队模式（可选）**——主理人编排 + 多角色协作（专家 Agent 并行蒸馏 → 写作角色综合），见「协作模式」
- **路径可配置**：全流程以 `{METHODS_ROOT}`（**方法论正文根**，＝库根/methods）为基准，示例 `~/methods/`；**库根＝工作区根**（正文根的上一层，`app/`·`scripts/`·`state/`·`tasks/` 所在）——两词勿混；库结构规范见 [methods-guide.md](references/methods-guide.md)
- **规则地图**：库的全部规则（四层：体系层判据／库层契约与编号／执行层门禁／触发层流程）已收敛为可查阅导航 → [library-rules.md](references/library-rules.md)，**含冲突裁决顺序与 12 条易误解点**；本文件与各 references 为细则事实源，规则总览只做导航
- **学习范围由用户自己确定**：材料来源开放——**单文件 / 文件夹 / 项目目录 / 已接入的库** 任选（可组合），skill 不自行扩大；未指定时才走候选池
- **库接入开放后端 · 首次引导配置**：方法论库**不锁定产品**——本地目录 / Obsidian / 乐享 / ima / 任意 MCP 知识库 / 云文档等皆可接入（示例非穷举，**由用户自行接入**）；首次使用按「库配置」节四问引导接入并记录，此后按能力档位（A 文件型 / B 检索型）分派读写
- 分合决策与改名记录见 CHANGELOG.md

## 何时使用（双触发域路由）

| 触发语 | 域 | 入口 |
|--------|-----|------|
| 「执行蒸馏学习XX次」「蒸馏学习XX次」 | 蒸馏域 | 走下方 S0-S7 全流程 |
| **指定学习范围**：「蒸馏学习这个文件 / 这个文件夹 / 这个项目 / 库里这批材料」（对话给文件、目录、项目路径，或指定库内范围） | 蒸馏域 | **范围由用户自己确定**，从 S0 起（跳过候选池选材） |
| 「方法论体检」「方法论治理」「库结构检查」「护栏检查」 | 维护域 | 走下方「维护域」3 步 |
| automation 按配置触发（批量） | 蒸馏域 | 按 automation 提示词执行（频次/标的数以提示词为准） |

## 库配置（首次使用必配 · 开放后端）

> **不锁定产品**：库可为本地目录 / Obsidian / 乐享 / ima / 任意 MCP 知识库 / 云文档……（示例非穷举，**由用户自行接入**）——能力档位与完整配置见 [methods-guide.md](references/methods-guide.md) §二。

**首次接入**：检查本 skill 安装目录下 `library.config.json`（模板 [library.config.template.json](references/library.config.template.json)）——存在且字段完整 → 直接进流程；缺失 → 按「四问引导」接入（库在哪／怎么读写／自带检索吗／已有库还是从零建）→ 定能力档位（A 文件型 / B 检索型）→ 生成配置 → **连通性验证**（读写成功 / 可检索）。

**四问逐条原文与按档位分派表**：[methods-guide.md](references/methods-guide.md) 附：首次接入引导流程（四问）。

## 执行目录约定（违反即报错）

- 库读写**一律以 `{METHODS_ROOT}` 为基准**（脚本、材料、方法论只读写该目录）
- automation/会话平台 cwd（如 `WorkBuddy/YYYY-MM-DD-HHMMSS/…`）仅为壳，**不得在会话目录新建/修改库数据**
- 命令前先 `cd {METHODS_ROOT}`；本 skill 随包脚本统一支持 `--methods-root <工作区根>` 或环境变量 `METHODS_ROOT`
  - 🔔 **参数语义**：`--methods-root` 传**库所在的工作区根**（非库本身）——直传库会得到 `<库>/methods` 并报「未找到方法论库」；`library.config.json` 的 `root` 字段＝库目录本身，与脚本参数语义不同，勿混用。实测校正与分派表见 [methods-guide.md](references/methods-guide.md) §一／§二
- **用户提供的材料路径**（S0 的文件/文件夹/项目）不受库目录限制——按用户给定路径只读读取，不写入、不搬移；**从库取材料**时同样只读（A 档读文件 / B 档走连接器检索）；蒸馏产出统一落库（按库配置档位）

## 蒸馏域：全流程（S0-S7，团队模式由主理人编排：TeamCreate → Agent spawn → SendMessage 正式协作；单用户模式本人串跑）

> **学习范围由用户自己确定**（库既是沉淀目的地、也是材料来源），skill 不自行扩大范围。
> **详规在册**：每步详规全在 [distill-methods.md](references/distill-methods.md)——**S0–S7 步骤执行卡片**见「附 A」（答「谁做／做什么」）；**S3.5／S4／S5／S5.5／S6 提炼方法详表**见同名 §（答「怎么做」）。本表只留「步骤 ＋ 执行者 ＋ 一句话判据 ＋ 册指针」。

| 步骤 | 执行者 | 判据（一句话） | 详规 |
|------|--------|------|------|
| **S0** 材料来源与范围（用户确定 · 起点） | 用户 | 范围由**用户**给定（单文件／文件夹／项目／已接入的库，可组合）；**未指定时才走候选池 S1** | [distill-methods.md](references/distill-methods.md) 附 A §S0 |
| **S1** 范围确定与选材（来源为候选池时） | 主理人（可选脚本） | 用户已给明确范围 → **跳过本步**；候选池路径下候选须已有「上会稿」，并先读 `state/待补学清单.md` | 附 A §S1 |
| **S1.5** 审完校验 | 主理人 | 审完标志＝**材料齐备**（有最终稿）；未齐登记至 `state/待补学清单.md`，已披露最终稿者优先补学（笔记标题后缀 `_补学`） | 附 A §S1.5 |
| **S2** 行业定位 | 主理人 | 记录**证监会行业分类 ＋ 国民经济行业分类**（无数据终端则降级：披露口径 ＋ 公开信息交叉验证） | 附 A §S2 |
| **S3** 材料准备 | 主理人（可选自动化脚本） | ①只读最新稿（注册稿＞上会稿＞申报稿，同 stage 取披露日期最新）②每轮回复只读最新版 → 生成**财务包／法律包／行业包**三包（S4 输入降约 2/3） | 附 A §S3 |
| **S3.5** 旧条目预取 | 主理人 | 按 **28Q 问题域** ＋ 行业类预取 5-10 条旧条目（编号＋标题＋一行摘要）注入阅读包头部「既有方法论速览」；S4 产出自带关系标注 | [distill-methods.md](references/distill-methods.md) §S3.5 |
| **S4** 三专家并行蒸馏 | 财务/法律/行业专家（团队模式：Agent spawn 同一条消息并行；单用户模式：本人分角色自评） | 三段式产出落 `产出_<维度>_蒸馏.md`；**S4.5 门禁** [check_expert_output.py](scripts/check_expert_output.py) **0 FAIL 才进 S5** | [distill-methods.md](references/distill-methods.md) §S4（门禁 §S4.5） |
| **S5** 综合成文 ＋ 写作范式 | 写作角色（writer） | **五步提炼法**综合三方 ＋ 亲自研读原文提炼「投行语言」词汇句法库 → 通用方法论 ＋ 行业方法论（单案范式七节骨架）；三轨产出后由主理人跑 [normalize_pl_s.py](scripts/normalize_pl_s.py) **归一 PL/S 编号**（族内连续·零撞号·幂等） | [distill-methods.md](references/distill-methods.md) §S5 |
| **S5.5** 模拟回复演练 | 写作角色 | 独立撰写 → 回查原文补齐 → 与真实回复对比，**差距清单 ≥3 条**并写回 | [distill-methods.md](references/distill-methods.md) §S5.5 |
| **S6** 共通点蒸馏 | 主理人（可委写作角色） | **S6a 轻量映射 ≤50 行每轮必做**（校验＋补漏＋定稿分级）；「本次＋历史未复盘」≥10 触发 **S6b** 全量蒸馏 | [distill-methods.md](references/distill-methods.md) §S6 |
| **S7** 沉淀入库 | 主理人 | 落库 ＋ **回写池三过滤（复现 2 次即并入 / 冲突改旧 / 用户裁定再裁定）** → [apply_rewrite.py](scripts/apply_rewrite.py) **执行回写**（高→实证区／中高→独立段；`--repair` 修截断行）→ [refresh_index.py](scripts/refresh_index.py) **必刷索引** → [check_methods_health.py](scripts/check_methods_health.py) **0 ERROR** ＋ [check_index_locator.py](scripts/check_index_locator.py) **抽查 12 条行号** → **待补学销项**；任一不过即转维护域修复 | 附 A §S7 ＋ [entry-contract.md](references/entry-contract.md) 附：S7 回写执行纪律（12 条） |

> **库主从关系（ADR-0009，2026-09-15 裁定）**：**本地 `{METHODS_ROOT}` = 单一事实源**——索引刷新、护栏校验、S6/S7 机制均以本地为准；**乐享等云知识库后端 = 只读发布镜像/检索前端**，向其写入属**同步动作、非创作动作**——禁止在云侧直接修订方法论内容，发现本地有误回本地改后重新同步；双侧分叉时以本地为准整体覆盖。

## 维护域：护栏体检 + 修复（3 步）

> **触发节奏建议**：并入批量蒸馏节奏——每累计蒸馏满 N 案例（建议 40），S7 沉淀完成后顺带执行一次（计数文件 `<工作区根>/state/维护体检计数.md`）；人工亦可随时按触发词发起。
> **同节奏议题**：**行业分类的合并评估只在本体检触发时进行**（平时蒸馏只管归口、不管合并；单案也正常新立类）——规则见 [library-rules.md](references/library-rules.md) §2.5。
> **详规在册**：三步的动作详规见 [govern/health-check.md](references/govern/health-check.md) 附：维护域三步执行详规；**步骤名与一句话判据留在本表**（步骤名是导航、不下沉）。

| 步骤 | 动作 | 判据（一句话） | 详规 |
|------|------|------|------|
| **1 体检** | `cd {METHODS_ROOT} && python <skill>/scripts/check_methods_health.py` | **10 项护栏 0 ERROR**（frontmatter／空 h3／编号连续唯一／路由表计数 vs 实算／parsed TOTAL／回写清单／W 编号唯一／交叉引用／体积警戒／**索引行号定位抽查**） | [govern/health-check.md](references/govern/health-check.md) |
| **2 修复** | 按体检 ERROR 类型选修复脚本（add_frontmatter／add_fm_single／b_fmt_unify／c_scale_dedup） | **先 dry-run 后执行**；工具箱索引与三个单一事实源边界 | [govern/fix-tools.md](references/govern/fix-tools.md) |
| **3 复验** | 重跑 [refresh_index.py](scripts/refresh_index.py)（刷新生成物）＋ 复跑护栏 | **0 ERROR 且幂等** | [govern/health-check.md](references/govern/health-check.md) 附 §3 复验 |

> **全库编号迁移踩坑实录**（案号 2→4 位化实证 · 4 条：正则 `\b` 汉字漏匹配／迁移脚本幂等／表行国标码误伤／四门复验）——[govern/fix-tools.md](references/govern/fix-tools.md) 附：全库编号迁移踩坑实录。

## 随包脚本（26 个 · 全部支持 `--methods-root`（传**工作区根**）/ `$METHODS_ROOT`）

> **适用范围**：脚本面向 **A 档（文件型）库**（索引体系与体检均基于文件，Obsidian 等 Markdown 载体同构适用）；**B 档（检索型）**下索引类脚本不适用（检索与结构由连接器管理，见 methods-guide §二分派表）。

- **四类分组**：① **索引体系**（`refresh_index.py` 一键编排 parse_titles→gen_index→gen_toc→gen_entry）② **落库与门禁**（`update_expert_md`／`check_expert_output`／`gen_replay_worksheet`／`check_entry_contract`／`replay_gate_report`）③ **维护域**（`check_methods_health` ＋ add_frontmatter／add_fm_single／b_fmt_unify／c_scale_dedup ＋ `normalize_case_names`／`apply_case_no`／`backfill_volume_refs`／`fix_volume_case_by_segment`／`sync_cases_md`）④ **库演进**（`split_domains`／`dryrun_case_migrate`／`migrate_case_no`）
- **全量清单与命令形态（26 个逐条用途）**：[methods-guide.md](references/methods-guide.md) 附：随包脚本全量清单
- **书写契约**：条目实证项字段模型／三种排布／来源标注／标签禁用四条 → [entry-contract.md](references/entry-contract.md)（v1.0 · 用户裁定 D1–D5）；自检门禁 [check_entry_contract.py](scripts/check_entry_contract.py)

## 依赖与工具

> 依赖来源标注：⬛=随包/本地自建；🟢=可选；🟦=内置。

- **Python 3**〔🟦内置运行时〕：26 个随包脚本（零第三方依赖）
- **方法论库 `{METHODS_ROOT}`**〔⬛随包/本地自建〕：库规范见 [methods-guide.md](references/methods-guide.md)
- **KB 后端**〔🟢可选〕：默认为本地目录；可接入 MCP 知识库/云文档等连接器（见「库配置」四问引导）
- **团队协作工具**〔🟢可选〕：团队模式使用 TeamCreate/Agent 消息机制；单用户模式无需（本人串跑）

**缺失降级**：无方法论库 → **空库起步档**（`methods-guide.md` 空库模板 + 边用边长）；维护域无库可检时如实报告「无对象」，不报错、不阻断；无 KB 后端 → 本地目录照常跑，仅失去镜像同步；无团队协作工具 → 单用户模式串跑（默认）。

## 资源索引（skill 只引用路径，不复制内容）

> 依赖来源标注：⬛=随包/本地自建；🔵=连接器（可选）；🟦=内置；🟨=官方市场。

- **[methods-guide.md](references/methods-guide.md)**〔⬛随包〕：**方法论库规范单一事实源**（目录/条目/建立与演进）；**附**：随包脚本全量清单（26 个）／首次接入引导流程（四问）
- **[distill-methods.md](references/distill-methods.md)**〔⬛随包〕：蒸馏「提炼方法」单一事实源（S4 三段式/S5 写作范式/S5.5 演练/S6 共通点判定）；**附 A**：S0–S7 步骤执行卡片；**附 B**：关键要点（蒸馏域）
- **[entry-contract.md](references/entry-contract.md)**〔⬛随包〕：条目与回写书写契约（四字段模型／三种排布／来源标注／标签禁用）；**附**：S7 回写执行纪律（12 条）
- **[references/govern/health-check.md](references/govern/health-check.md)**〔⬛随包〕：护栏体检 10 项 + 脚本用法 + 排除目录；**附**：维护域三步详规／关键要点（护栏与解析口径）
- **[references/govern/fix-tools.md](references/govern/fix-tools.md)**〔⬛随包〕：修复工具箱索引 + 三个单一事实源边界 + 修复后验证清单；**附**：编号迁移踩坑实录／关键要点（库演进安全）
- **[library-rules.md](references/library-rules.md)**〔⬛随包〕：方法论库规则总览（四层地图 · 冲突裁决顺序 · 12 条易误解点）——只做导航，细则事实源在各册
- **方法论库（`{METHODS_ROOT}`）**〔使用者自建〕：核心文件 = `通用方法论_最终版.md`（路由入口）+ `通用方法论_<域>域.md`（各域正文）+ `方法论调用索引.md` + `方法论_条目标题目录.md`（后两者由脚本生成）
- **KB 后端**〔🟢 可选〕：蒸馏笔记落库目的地——默认本地 `{METHODS_ROOT}/notes/`；可选外部知识库连接器（MCP 知识库/云文档等任选，使用者自配）

## 协作模式（团队增强 · 可选）

> **本 skill 离开多角色团队也能独立运作**——团队协作只是可选增强（提升并行度与交叉校验），不是前置条件。

- **团队模式**：主理人编排（TeamCreate → 三专家 Agent 并行 spawn → 写作角色综合成文 → S4.5/S7 双门禁）
- **协作铁律**：TeamCreate 必须主理人执行；三专家并行 spawn（同一条消息）；所有跨成员信息流经主理人中转；不得互相直连
- **角色定义**（财务/法律/行业专家 ＋ 写作角色 ＋ 主理人）：[distill-methods.md](references/distill-methods.md) 附 B

## 关键要点（纪律索引 · 主题 → 落点 → 需要的那一步）

> 下表是**纪律的全局导航**：`主题 → 需要在哪一步 → 落点册`。**各步骤处亦已内联对应指针**（运行到那一步即见）；逐条详规全文见 [library-rules.md](references/library-rules.md) 附「纪律索引」（2026-09-21 由本节下沉）。
## 维护（何时需要改本 skill）

> **沉淀后必做自检（S7）**：每轮蒸馏完成后对照本表——**方法论内容更新 → 不改本 skill**（`refresh_index.py` 自动维护）；流程/SOP/脚本命令/门禁变化 → 改本 skill；维护域体检项/修复脚本变化 → 改 `references/govern/` 下对应文件。检查结果记入蒸馏笔记。

| 变化类型 | 需要改 skill？ | 动作 |
|---------|---------------|------|
| 方法论内容更新（蒸馏新案、升版、索引刷新） | ❌ 不改 | 运行 [refresh_index.py](scripts/refresh_index.py)（自动维护索引/目录/入口） |
| 流程/SOP 变化（S 步骤、脚本命令、门禁变更） | ✅ 改 | 同步更新本 skill 对应章节 |
| 蒸馏提炼方法变化（三段式/范式提炼/共通点判定） | ✅ 改 | 更新 [distill-methods.md](references/distill-methods.md)（单一事实源） |
| 库结构规范变化（目录/条目结构） | ✅ 改 | 更新 [methods-guide.md](references/methods-guide.md)（单一事实源） |
| 护栏体检项/修复脚本变化 | ✅ 改 | 更新 `references/govern/` 下对应文件 |
| 新踩坑/反模式 | ✅ 追加 | 在册的对应「附」节追加（本表只留索引） |

## 边界与协作

- **与 ibd-methods-query 互补**：本 skill 管生产+维护（写入侧），query 管检索消费（读取侧）——查询方法论走 query 的标准检索链路，不经本 skill
- **冷启动分工（ADR-0008 延伸裁定，2026-09-18）**：首次使用无库时，query 的**冷启动引导档**可就地建空库骨架（4 文件 + 最小 `library.config.json`，纯结构零内容）——建库骨架属「检索前置条件自举」，不属蒸馏生产；方法论内容生产仍归本 skill，用户随后的蒸馏/四问引导均按既有流程接管该库
- **被依赖声明**：`ibd-doc-write` / `ibd-methods-query` 可选依赖本 skill（≥1.5.0：库规范 + 脚本工具链 + 库接入配置）
- **库结构规范单一事实源**：本 skill 的 [methods-guide.md](references/methods-guide.md)；`ibd-doc-write` 的库指引为其消费侧精简版（无库降级），二者同源
- **高频句法反哺 doc-write**（可选依赖，未装则跳过）：蒸馏产出的通用高频句式同步至 ibd-doc-write 的「高频句法库」（该包 references 下；本包只存通用高频，案例级条目留 `{METHODS_ROOT}/`，双轨不混）
- **格式规范归 doc-review**：方法论文件的格式问题移交 `ibd-doc-review`，本 skill 不自建格式规则
- **不设第二源**：索引刷新→[refresh_index.py](scripts/refresh_index.py)；脚本→本包 `scripts/`（详见 references/govern/fix-tools.md 边界声明）

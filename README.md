<p align="center">
  <img src="https://img.shields.io/badge/IBD--Skills-A%20%E8%82%A1%E6%8A%95%E8%A1%8C%20AI%20%E6%8A%80%E8%83%BD%E9%9B%86%E5%90%88-2e6cc4" alt="ibd-skills">
</p>

<p align="center">
  <a href="https://github.com/Kianchales/ibd-skills/releases/latest"><img src="https://img.shields.io/github/v/release/Kianchales/ibd-skills?color=blue&label=Latest%20Release" alt="latest release"></a>
  <a href="https://github.com/Kianchales/ibd-skills/stargazers"><img src="https://img.shields.io/github/stars/Kianchales/ibd-skills?style=flat&label=Stars" alt="stars"></a>
  <img src="https://img.shields.io/badge/skills-7%20%E5%8C%85-4e6b99" alt="7 packages">
  <img src="https://img.shields.io/badge/License-MIT-blue" alt="MIT license">
  <img src="https://img.shields.io/badge/Python-3%20%E6%A0%87%E5%87%86%E5%BA%93-3776AB" alt="python stdlib">
</p>

<h4 align="center">
  <a href="skills/ibd-doc-write/README.md">写作</a> |
  <a href="skills/ibd-quality-gates/README.md">质量校验</a> |
  <a href="skills/ibd-finance-review/README.md">财务复核</a> |
  <a href="skills/ibd-doc-review/README.md">格式</a> |
  <a href="skills/ibd-doc-annotate/README.md">批注交付</a> |
  <a href="skills/ibd-methods-ops/README.md">方法论沉淀</a> |
  <a href="skills/ibd-methods-query/README.md">方法论检索</a>
</h4>

<details open>
<summary><b>📕 目录</b></summary>

- 💡 [这是什么？](#-这是什么)
- ✨ [快速开始（30 秒）](#-快速开始30-秒)
- 🧩 [集合内 7 个 skill](#-集合内-7-个-skill)
- 🔗 [工作链路](#-工作链路)
- 🚀 [典型场景](#-典型场景)
- 🛡 [设计原则](#-设计原则)
- 📦 [安装与依赖](#-安装与依赖)
- 🛠 [技术细节](#-技术细节)
- 📌 [近期更新](#-近期更新)
- 📚 [文档](#-文档)
- ⚖️ [许可](#️-许可)

</details>

## 💡 这是什么？

**ibd-skills** 是面向 A 股投行（IBD）工作流的 AI 技能集合——覆盖投行工作流从**写作、质量把关、财务复核、格式落地、批注交付到方法论沉淀与检索**的全链路，为「让 AI 写出能直接申报的文件」提供一套**可复现、可校验、有纪律**的方法论载体。

它不是七个孤立的技能，而是一条有分工的流水线：每个技能只负责一件事，规则单一事实源、不重复维护，串起来就是完整的投行文档生产线。

> 一句话：**写作像投行人，把关像质控组，交付像申报文件。**

## ✨ 快速开始（30 秒）

1. 从 [Releases](https://github.com/Kianchales/ibd-skills/releases/latest) 下载最新 zip（内含全部 7 个 skill）
2. 解压后，把需要的 `skills/<包名>/` 目录拷贝到你的 AI 工作台技能目录（各客户端按自身规范放置）
3. 对你的 AI 说一句触发语，流水线即启动：

```
「帮我写 XX 公司的第一轮审核问询反馈回复」   → ibd-doc-write 起草
「交稿前做质量校验」                          → ibd-quality-gates 校验
「按招股书版式套样式并核对格式」              → ibd-doc-review 落地
「把复核问题全部批注进原文」                  → ibd-doc-annotate 交付
「蒸馏学习这份材料」                          → ibd-methods-ops 沉淀（材料来源与库由你定）
「查 XX 问题怎么写」                          → ibd-methods-query 定向检索
```

> [!TIP]
> 带 🔴 依赖的包须连同依赖包一起安装——依赖**不随包携带**，缺依赖时的断链自助指引见各包 `SKILL.md`「依赖与工具」。

## 🧩 集合内 7 个 skill

| skill | 定位 | 版本 | 依赖 |
|---|---|---|---|
| [ibd-doc-write](skills/ibd-doc-write/README.md) | 投行文档**写作规范与框架入口**：反馈回复五步方法论链路、招股书章节/报告/备忘录结构、投行语言规范。⚠️ **尚不成熟，不能独立撰写整段投行文件** | 0.13.0 | 🔴 quality-gates ≥0.7.0 + doc-review ≥0.15.7；🟢 methods-ops ≥1.5.0（库完整能力） |
| [ibd-quality-gates](skills/ibd-quality-gates/README.md) | **交稿前质量校验**：数字五要素、反模式扫描、五项判据 G1-G5、数值自洽核对 | 0.8.3 | 零硬依赖（基座之一） |
| [ibd-finance-review](skills/ibd-finance-review/README.md) | **财务深度复核**：招股书/申报文件 16 维清单，锚定企业会计准则与监管审核口径 | 0.8.4 | 🟢 doc-review ≥0.16.2（交付口径单一事实源；缺则只产清单不落地） |
| [ibd-doc-review](skills/ibd-doc-review/README.md) | **格式层单一事实源**：样式应用、格式核对、批注/修订规范与校验 + 交付门禁 `deliver_gate.py` | 0.17.3 | 零外部 skill 依赖（基座） |
| [ibd-doc-annotate](skills/ibd-doc-annotate/README.md) | **复核结论落地执行器**：批注版（Word/PDF 原位批注）与修订稿生成 | 0.5.4 | 🔴 doc-review ≥0.16.2（规范 + 校验门禁 + 交付口径 delivery.md） |
| [ibd-methods-ops](skills/ibd-methods-ops/README.md) | **方法论库生产 + 维护**：蒸馏 S0-S7（材料来源由用户定）+ 维护域 3 步 + 15 个随包脚本（索引/落库/门禁/修复/拆分/迁移） | 1.5.1 | 零外部 skill 依赖（需 Python 3；库与材料来源自行接入） |
| [ibd-methods-query](skills/ibd-methods-query/README.md) | **方法论库检索**：问题拆解 → 索引定位 → 定向读取 → 合成，按需只读命中条目不全文读库 | 0.2.0 | 🟢 methods-ops ≥1.5.0（索引资产生成） |

> [!WARNING]
> **`ibd-doc-write` 尚不成熟，无法满足「独立撰写整段投行文件」的要求。**
> 它提供的是**写作规范与结构框架**（问题拆解链路、结构规范、语言句法库、方法论引用自检），产出定位于**供投行人改写的结构化初稿**——素材与事实由项目组提供、专业判断由申报会计师／律师确认、成稿须逐句审校后方可进入复核或申报流程。**请当「规范化助手」用，不要当「代笔」用**。详见 [其 README「能力边界」](skills/ibd-doc-write/README.md)。

## 🔗 工作链路

```
──────────── 写作线 ────────────
doc-write 写草稿 → gates 质量校验（数字五要素/反模式/G1-G5 + 数值自洽）
                → doc-review 套样式 + 格式核对 → 正式稿

──────────── 复核线 ────────────
finance-review 16 维复核产出问题清单 → doc-annotate 注入原位批注
                → doc-review 门禁校验（批注结构/编号/锚定）→ 批注版原文 + 精简总览

──────────── 方法论线（沉淀 ⇄ 检索，供写作线消费）────────────
methods-ops 蒸馏沉淀（S0-S7：材料来源与库由用户定）→ 库（本地/Obsidian/云知识库任选）
methods-query 定向检索 → 条目编号 + 行号 → 写作/复核引用（doc-write 查库、引用自检）
```

## 🚀 典型场景

**场景一：反馈回复写作（一轮问询 → 结构化初稿）**
拿问询函 → 按 28 个问询域查方法论 → 逐问起草（套投行语言、去 AI 味）→ 草稿阶段先过质量校验 → 定稿后套样式、跑格式核对 → 产出**供投行人改写的初稿**（⚠️ write 尚不成熟，**不能独立完成整段申报文件**，成稿须逐句审校）。

**场景二：招股书章节复核（逐段挑错 → 原位批注）**
按 16 维财务清单逐章核查 → 问题清单编号（J/L/I/Z 分型）→ 全部转 Word 原位批注（错误不分大小全量覆盖）→ 门禁校验批注合规 → 交付批注版原文 + ≤1 页精简总览。

**场景三：交付前最后一道门**
数字五要素逐数问来源 → 绝对化/AI 痕迹/裸数字机械扫描 → 自评量表打分 → G1-G5 逐门过关——任何一门不过不交付。

**场景四：方法论沉淀与检索（越用越强的库）**
给材料（单文件 / 文件夹 / 项目 / 已接入的库任选）→ 多维度蒸馏 → 共通点提炼 → 沉淀入库（索引自动刷新）；下次写作时按问题域定向检索既有条目复用——**资料来源与沉淀去向都由你定**。

## 🛡 设计原则

- **本地优先，内容不出机器**：门禁脚本全部本地执行，扫描报告只落本地文件；发布物经隐私扫描（P1）零本机路径
- **申报文件级严谨**：每包自带校验门禁脚本（批注结构、样式合规、修订成对、数值自洽），AI 产出过门才算数
- **单一事实源**：格式规则只在 doc-review、质量规则只在 gates——不重复维护，改一处全家生效
- **零第三方依赖**：校验脚本全部 Python 3 标准库（zipfile + xml.etree），解压即跑，不污染环境
- **按需裁剪**：可只装一个包（如只要格式核对），也可全家桶串联；依赖断链有自助指引
- **双向开放（方法论线）**：资料来源与沉淀去向都由使用者自己确定——材料从哪来（对话给文件/文件夹/项目/已接入的库）、知识沉淀到哪去（本地/Obsidian/云知识库等接入的库），skill 不绑定私有环境

## 📦 安装与依赖

每个包自带 `LICENSE` 与 `CHANGELOG.md`（版本历史）。安装后**以包内 `SKILL.md` 为准**——它包含触发词、使用流程与依赖表。

| 依赖类型 | 说明 |
|---|---|
| 外部 skill 依赖 | doc-write / doc-annotate 声明依赖同族公开包（不随包携带），从本仓库 `skills/` 目录获取对应包即可 |
| Python 库 | doc-annotate 的 docx/pdf 链路按需装 `python-docx`/`lxml`/`pymupdf`（SKILL.md 已声明）；methods-ops 的 15 个脚本为纯标准库；其余脚本零依赖 |
| 平台工具 | 样式套用依赖任一 docx 处理工具（tencent-docx / minimax-docx / 本地 Office），按 SKILL.md 依赖表自备 |

### 依赖版本兼容矩阵（单包安装时对照）

> 同 zip 全家桶安装天然满足下表（集合版本各包互验）；**单包安装**时按下表查版本下限，低于下限的旧组合可能行为不一致（依赖方升版后须复核下限，见各包 CHANGELOG）。

| 依赖方 | 依赖包 | 版本下限 | 当前集合版本 | 兼容 |
|---|---|---|---|---|
| ibd-doc-write | ibd-quality-gates | ≥ 0.7.0 | 0.8.3 | ✅ |
| ibd-doc-write | ibd-doc-review | ≥ 0.15.7 | 0.17.3 | ✅ |
| ibd-doc-annotate | ibd-doc-review | ≥ 0.16.2 | 0.17.3 | ✅ |
| ibd-finance-review | ibd-doc-review（可选） | ≥ 0.16.2 | 0.17.3 | ✅ |
| ibd-doc-write | ibd-methods-ops（可选） | ≥ 1.5.0 | 1.5.1 | ✅ |
| ibd-methods-query | ibd-methods-ops | ≥ 1.5.0 | 1.5.1 | ✅ |

> 下限口径：`ibd-doc-write` 的 ≥0.15.7 = `deliver_gate.py` 引入版；`ibd-doc-annotate` / `ibd-finance-review` 的 ≥0.16.2 = 交付口径单一事实源 `references/delivery.md` 引入版（两包均回指该文件，低于此版该指向成死引用）。

验证方法：装齐后各包跑自测（gates `scripts/tests/test_check_gates.py`、doc-review `scripts/tests/`（5 脚本 85 项）、ops `scripts/check_methods_health.py`），全绿即组合可用。

## 🛠 技术细节

- 每包独立 SemVer，变更记录见各包 `CHANGELOG.md`
- 校验脚本（check_styles / check_content / check_annotations / check_revisions / check_data / check_gates / check_methods_health / check_expert_output）均为只读门禁：**校验不通过 → exit 1 → 不交付**
- 集合 Release：`ibd-skills-vX.Y.Z`，zip 含 `README.md` + `skills/` 全部包

## 📌 近期更新

- **2026-09-12 · v0.2.5**：**审计整改批次上提（doc-review 0.15.7 → 0.17.3）**——①**交付门禁成型**：`deliver_gate.py` 覆盖 `--md` 草稿预检与 `--docx` 交付件九项，新增复核产物门禁 `--annotated`/`--revised` 挂载与 officecli 物理扫描第三态 `[SKIP]`；②**脚本结构性重构**：`check_content.py` 按业务域拆为入口 + `content_common`/`content_text`/`content_table`（对外 CLI 契约不变），配套挖出并修复 `terms` 核对项**自诞生起静默失效**的生产 bug（另修 `<w:b w:val="0">` 加粗误判）；③**文档收口**：使用流程抽取 `references/workflow.md`（主文件瘦身 38%）、交付口径归一到 `references/delivery.md`（单一事实源）、`CHANGELOG` 分代归档（46.9 → 29.2 KB）；④**测试补齐**：`scripts/tests/` 从 0 → 5 脚本 **85 项全过**（含纯标准库 OPC 关系语义守卫）；⑤**规则新增**：格式铁律「数字前后不加空格」（标准号西文缩写与数字间空格为例外）。联动升版 `ibd-doc-annotate` 0.5.3 → **0.5.4**、`ibd-finance-review` 0.8.3 → **0.8.4**（两包交付口径回指 `delivery.md`，依赖下限同步为 doc-review ≥0.16.2）；隐私侧同时清零发布门禁 BLOCK（平台路径与本机用户名）。
- **2026-09-11 · v0.2.4**：**编号体系统一 + 交付门禁**——各包 references 编号示例同步至现行体系（体例域 `S-` 前缀／案号 `AN{4位}`，与库内《编号体系说明》对齐，历史迁移记录按原形态保留）；`ibd-doc-review` 0.15.7 新增交付前综合核验 `deliver_gate.py`；README 补齐 `ibd-doc-write` 能力边界声明（**尚不成熟，不能独立撰写整段投行文件**）；版本矩阵同步至 write 0.13.0 / doc-review 0.15.7 / methods-ops 1.5.1；仓库加 `.gitignore` 防临时文件随包
- **2026-09-10 · v0.2.0**：**新增 2 包**（methods-ops 1.5.0 方法论库生产+维护 / methods-query 0.2.0 检索域）；doc-write 0.9.0（库规范分层）；**双向开放**——库接入（本地/Obsidian/云知识库）与材料来源均由使用者自定；15 个随包脚本（索引/落库/门禁/修复/拆分/迁移）
- **2026-09-10 · v0.1.2**：五包命名收敛（doc-review→格式复核 / gates→质量校验 / annotate→批注与修订交付 / doc-write 去 G4 黑话）；触发词路由分流；SKILL.md 骨架与 README 全量标准化（集合风）；CI 门禁上线；依赖兼容矩阵 + 四包最小复现示例
- **2026-09-10 · v0.1.1**：doc-review 0.15.3（check_revisions 去 lxml 依赖 → 纯标准库，冷启动验证修复）；doc-write / quality-gates 补齐 README；发布渠道文案统一 GitHub；集合 README 产品级重写
- **2026-09-09 · v0.1.0**：集合仓库首版发布，5 包全量（doc-review 0.15.2 / gates 0.8.0 / finance-review 0.8.3 / write 0.8.0 / annotate 0.5.2）

## 📚 文档

- 每个包的使用文档 = 包内 `SKILL.md`（触发词 → 使用流程 → 依赖 → 边界），安装后即可查
- 快速入口 = 各包 `README.md`（能力总览 + 命令附录）
- 规则明细（批注规范 / 修订规范 / 样式映射 / 反模式清单等）在各包 `references/`

## ⚖️ 许可

MIT License。发布物已通过隐私与合规门禁（P0-P7 流水线），可放心用于团队内部分发。

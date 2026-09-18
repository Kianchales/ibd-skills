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

**ibd-skills** 是一套给 A 股投行人的 AI 技能集合：让 AI 帮你**起草文件、挑错复核、排版交付，并把项目经验沉淀成团队知识库**——七个技能各管一段，串成一条完整的投行文档生产线。

它覆盖投行工作流从**写作、质量把关、财务复核、格式落地、批注交付到方法论沉淀与检索**的全链路，为「让 AI 写出能直接申报的文件」提供一套**可复现、可校验、有纪律**的方法论载体——每个技能只负责一件事，规则单一事实源、不重复维护。

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

### 🧪 5 分钟上手（装完先跑这个）

装好后**不用找任何文档**，先跑自测确认环境可用（纯标准库，零安装；任一目录执行）：

```bash
# 1. 质量校验包自测（5 组用例）
python skills/ibd-quality-gates/scripts/tests/test_check_gates.py
# 2. 格式核对包自测（内容核对 20 项 + 交付门禁 26 项）
python skills/ibd-doc-review/scripts/tests/test_check_content.py
python skills/ibd-doc-review/scripts/tests/test_deliver_gate.py
```

三组全 OK（几秒内跑完）= 安装完好。然后拿一份你手头的 Word 文件试试第一个真实场景——**格式核对**（doc-review 最常用、零外部依赖）：

```
对 AI 说：「用 ibd-doc-review 帮我核对这份文档的格式」
```

AI 会按 `SKILL.md` 决策树走 S1-S6（识别场景 → 套样式 → 格式核对 → 交付门禁），产出核对报告。想看完整链路示例（触发 → 执行 → 产出）翻 `skills/ibd-doc-review/references/examples.md`；批注交付场景先读同目录 `delivery.md`（交付口径单一事实源）。

> [!NOTE]
> docx 套样式需一个 docx 处理工具（见「安装与依赖」平台工具行）；**格式核对与批注校验本身零依赖**，装完即可用。

## 🧩 集合内 7 个 skill

| skill | 一句话说明 | 版本 | 依赖 |
|---|---|---|---|
| [ibd-doc-write](skills/ibd-doc-write/README.md) | **起草投行文件**：给它问询函或章节要求，按投行写作规范产出结构化初稿，供你逐句改定 | 0.14.3 | 🔴 quality-gates ≥0.7.0 + doc-review ≥0.15.7；🟢 methods-ops ≥1.5.0（库完整能力） |
| [ibd-quality-gates](skills/ibd-quality-gates/README.md) | **交稿前自动挑错**：数字有没有来源、表述是否绝对化、前后数据能否对上、Excel 公式能否复核，逐项过关才放行 | 0.10.0 | 零硬依赖（基座之一） |
| [ibd-finance-review](skills/ibd-finance-review/README.md) | **财务深度复核**：按会计准则与监管口径，对招股书财务内容做 16 个维度的核查 | 0.8.6 | 🟢 doc-review ≥0.16.2（交付口径单一事实源；缺则只产清单不落地） |
| [ibd-doc-review](skills/ibd-doc-review/README.md) | **格式排版与核对**：一键套用招股书版式，自动检查字体、编号等格式问题，产出核对报告 | 0.20.1 | 零外部 skill 依赖（基座） |
| [ibd-doc-annotate](skills/ibd-doc-annotate/README.md) | **复核意见落地**：把发现的问题原位批注进 Word/PDF，交付批注版原文和一份总览（Markdown + Word） | 0.7.0 | 🔴 doc-review ≥0.19.0（规范 + 校验门禁内部回调 + 交付口径 delivery.md；单入口路由 ADR-0006） |
| [ibd-methods-ops](skills/ibd-methods-ops/README.md) | **经验沉淀入库**：把做过的项目蒸馏成可复用的方法论存进知识库，团队经验不流失 | 1.6.1 | 零外部 skill 依赖（需 Python 3；库与材料来源自行接入） |
| [ibd-methods-query](skills/ibd-methods-query/README.md) | **经验随取随用**：写作复核时按问题检索知识库，直接命中历史写法，越用越顺手；**首次使用无库自动冷启动引导建档，不报错** | 0.3.0 | 🟢 methods-ops ≥1.5.0（索引资产生成） |

> [!WARNING]
> **`ibd-doc-write` 尚不成熟，无法满足「独立撰写整段投行文件」的要求。**
> 它提供的是**写作规范与结构框架**（问题拆解链路、结构规范、语言句法库、方法论引用自检），产出定位于**供投行人改写的结构化初稿**——素材与事实由项目组提供、专业判断由申报会计师／律师确认、成稿须逐句审校后方可进入复核或申报流程。**请当「规范化助手」用，不要当「代笔」用**。详见 [其 README「能力边界」](skills/ibd-doc-write/README.md)。

## 🔗 工作链路

三条接力流水线：每条都从材料进、从文件出，中间的检查关口由 AI 一道一道把守。

- **写作线**：起草初稿 → 自动挑错 → 套版式核对 → 交付供你审改的正式稿
- **复核线**：AI 逐段挑错 → 问题原位批注进原文 → 合规校验把关 → 交付批注版原文 + 一页总览
- **方法论线（积累与复用）**：做完项目把经验蒸馏入库 → 下次按问题一查即得 → 经验反哺写作与复核，团队越做越强

<details>
<summary><b>对应到具体技能包（点击展开）</b></summary>

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

</details>

## 🚀 典型场景

**场景一：反馈回复写作（一轮问询 → 结构化初稿）**
收到交易所问询函后，把问题交给 AI：它参考历史回复经验逐题起草回复初稿，你逐句审改后即可提交。

**场景二：招股书章节复核（逐段挑错 → 原位批注）**
复核招股书时，AI 按财务、法律、行业多条专业线逐段挑错，问题直接批注在原文对应位置，另附一页纸总览。

**场景三：交付前最后一道门**
文件定稿前，AI 替你做最后一遍检查：每个数字有出处、每句话不越界、前后数据对得上——不过关就不放行。

**场景四：方法论沉淀与检索（越用越强的库）**
每做完一个项目，把踩过的坑和好写法存进团队知识库；下次写文件按问题一查即得，团队越做越快。

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

### 依赖关系图（谁依赖谁）

```
                    ┌──────────────────────┐
                    │   ibd-quality-gates  │  基座（零依赖）
                    └──────────┬───────────┘
                               │ 🔴 ≥0.7.0
                    ┌──────────▼───────────┐      ┌─────────────────────┐
 写作线（草稿）─────▶│     ibd-doc-write    │─────▶│   ibd-methods-ops   │ 基座（零依赖）
                    │  🔴 doc-review ≥0.15.7│ 🟢可选│  （蒸馏沉淀入库）    │
                    └──────────┬───────────┘      └──────────▲──────────┘
                               ▼                             │ 🟢 ≥1.5.0
                    ┌──────────────────────┐                 │
                    │    ibd-doc-review    │◀────────────────┘
                    │  基座（零外部依赖）    │      ┌─────────────────────┐
                    └──────────▲───────────┘      │  ibd-methods-query  │
                               │ 🔴/🟢 ≥0.16.2    │  （定向检索，🔴ops）  │
        ┌──────────────────────┼─────────────────┘└─────────────────────┘
        │                      │
┌───────┴──────────┐  ┌────────┴─────────┐
│ ibd-finance-review│  │ ibd-doc-annotate │
│  🟢可选回指       │  │  🔴 硬依赖        │
└──────────────────┘  └──────────────────┘
```

> 🔴 = 硬依赖（缺则核心功能不可用）；🟢 = 可选依赖（缺则降级）。下限与口径见下方兼容矩阵；接口细节（门禁 CLI / 清单 schema / 词表）见 `skills/ibd-doc-review/references/interface.md`（对外契约单一事实源）。

### 依赖版本兼容矩阵（单包安装时对照）

> 同 zip 全家桶安装天然满足下表（集合版本各包互验）；**单包安装**时按下表查版本下限，低于下限的旧组合可能行为不一致（依赖方升版后须复核下限，见各包 CHANGELOG）。

| 依赖方 | 依赖包 | 版本下限 | 当前集合版本 | 兼容 |
|---|---|---|---|---|
| ibd-doc-write | ibd-quality-gates | ≥ 0.7.0 | 0.10.0 | ✅ |
| ibd-doc-write | ibd-doc-review | ≥ 0.15.7 | 0.20.1 | ✅ |
| ibd-doc-annotate | ibd-doc-review | ≥ 0.19.0 | 0.20.1 | ✅ |
| ibd-finance-review | ibd-doc-review（可选） | ≥ 0.16.2 | 0.20.1 | ✅ |
| ibd-doc-write | ibd-methods-ops（可选） | ≥ 1.5.0 | 1.6.1 | ✅ |
| ibd-methods-query | ibd-methods-ops | ≥ 1.5.0 | 1.6.1 | ✅ |

> 下限口径：`ibd-doc-write` 的 ≥0.15.7 = `deliver_gate.py` 引入版；`ibd-doc-annotate` 的 ≥0.19.0 = 批注任务单入口路由版（ADR-0006，check_annotations.py 转内部回调，低于此版单入口声明成死引用）；`ibd-finance-review` 的 ≥0.16.2 = 交付口径单一事实源 `references/delivery.md` 引入版（低于此版该指向成死引用）。

验证方法：装齐后各包跑自测（gates `scripts/tests/test_check_gates.py`、doc-review `scripts/tests/`（5 脚本 85 项）、ops `scripts/check_methods_health.py`），全绿即组合可用。

## 🛠 技术细节

- 每包独立 SemVer，变更记录见各包 `CHANGELOG.md`
- 校验脚本（check_styles / check_content / check_annotations / check_revisions / check_data / check_gates / check_methods_health / check_expert_output）均为只读门禁：**校验不通过 → exit 1 → 不交付**
- 集合 Release：`ibd-skills-vX.Y.Z`，zip 含 `README.md` + `skills/` 全部包

## 📌 近期更新

- **2026-09-18 · v0.3.4**：**query 0.3.0 冷启动引导档**——外部用户反馈首次使用「方法论调用索引读取失败」（库未建时检索必失败，原降级只覆盖索引缺失不覆盖库不存在）：`ibd-methods-query` 0.2.1 → **0.3.0**（缺失降级重构三态：正常 / Grep 兜底 / **冷启动引导**——一问定路径 + 按 ops methods-guide 模板建空库骨架 + 生成最小 library.config.json + 交付「无命中 + 待沉淀登记」）；`ibd-methods-ops` 1.6.1「边界与协作」补冷启动分工裁定（建骨架=检索前置自举非生产，零变更未 bump）；根 README 包清单 query 一句话说明补冷启动能力。
- **2026-09-18 · v0.3.3**：**Excel 交付规则 + 总览双格式 + 发布流程补强**——`ibd-quality-gates` 0.9.0 → **0.10.0**（新增 rules.md §7「公式写入三档 + 交付前重算」：A 经典裸写 / B 单值型带 `_xlfn.` 前缀 / C 溢出型禁 openpyxl，交程序读须先重算或写静态值；反模式新增 **D-8**「Excel 交付物的公式假值 / 静默截断」，清单扩为四类 23 条）；`ibd-doc-annotate` 0.6.1 → **0.7.0**（**总览报告双格式交付 = MD + Word**：新脚本 `overview_to_docx.py`，批注注入后自动同产 `_批注总览.docx`，交付口径同步 doc-review delivery.md）；`ibd-doc-review` 0.20.1（delivery.md 总览双格式口径留痕，纯文档未 bump）。版本矩阵与依赖兼容矩阵同步。
- **2026-09-18 · v0.3.2**：**接入点声明 + 两条写作红线 + A-8 反模式批次**——`ibd-doc-review` 0.19.0 → **0.20.1**（0.20.0「中文与半角字符之间不加空格」规则成立并**全链路闭环**：规则本体 + 检测脚本双处同源 + 写作侧预防 + 门禁，四处同步；0.20.1 `validate_schema.py` **去第三方依赖**改纯标准库实现 + 新增 21 项自测）；`ibd-doc-write` 0.14.1 → **0.14.3**（0.14.2 写前红线「自立场材料不作论据」回指 A-8；0.14.3 写前红线「中文与半角字符不留空格」，单一事实源指向 doc-review）；`ibd-quality-gates` 0.8.4 → **0.9.0**（论证类反模式 **A-8**「拿自立场材料当论据」）；**四包补齐接入点三问声明**（`ibd-doc-annotate` 0.6.0 → **0.6.1**：无需自备资产；`ibd-finance-review` 0.8.5 → **0.8.6**：自备项全为可选 + 机检脚本指向明确化；`ibd-methods-ops` 1.6.0 → **1.6.1**、`ibd-methods-query` 0.2.0 → **0.2.1**：缺失降级档），公开包总表口径由 **5 扩为 7**（补入两个方法包）。版本矩阵与依赖兼容矩阵同步。
- **2026-09-15 · v0.3.1**：**根 README 元数据修复**——依赖版本兼容矩阵补齐 v0.3.0 批次欠账（annotate 下限 ≥0.16.2 → **≥0.19.0**（ADR-0006 单入口路由，原下限为假性兼容陷阱）；当前列同步 doc-review 0.19.0 / quality-gates 0.8.4 / methods-ops 1.6.0）；下限口径注脚同步 annotate 单入口语义。包内容零变更，与 v0.3.0 zip 等价。
- **2026-09-15 · v0.3.0**：**问题清单结构化 + 单入口 + 逐段协作 + S7 三过滤批次**——`ibd-doc-review` 0.17.3 → **0.19.0**（0.18.0 新增 [problems.schema.json](skills/ibd-doc-review/references/problems.schema.json) 问题清单 JSON Schema + [validate_schema.py](skills/ibd-doc-review/scripts/validate_schema.py) 校验入口，ADR-0004 C-分步；0.19.0 批注任务单入口路由，check_annotations.py 转内部回调，ADR-0006）；`ibd-doc-annotate` 0.5.6 → **0.6.0**（唯一对外批注入口声明 + 依赖下限 ≥0.19.0）；`ibd-doc-write` 0.13.0 → **0.14.1**（0.14.0 [paragraph-collab.md](skills/ibd-doc-write/references/paragraph-collab.md) 逐段协作模式落地：状态双文件 + 口径漂移检测协议，ADR-0001 操作规程化；0.14.1 文档类型拆分门槛 = 复现 ≥3 次）；`ibd-methods-ops` 1.5.3 → **1.6.0**（S7 回写池三过滤 ADR-0007 + 库主从关系 ADR-0009）；`ibd-quality-gates` **0.8.4**（antipatterns.md 追溯补记）。版本矩阵同步。
- **2026-09-14 · v0.2.6**：**annotate 0.5.6 + methods-ops 1.5.3 上提**——`ibd-doc-annotate` **0.5.5 → 0.5.6**（修复后处理脚本 `fix_missing_ranges.py` 在锚点落单 run 内时产出 end→ref→start 的标记顺序颠倒缺陷，新验收敛「标记顺序 + 覆盖文本 + 段落零改动」断言，补 `scripts/tests/test_fix_missing_ranges.py` **8 项自测**）；`ibd-methods-ops` 1.5.2 → **1.5.3**（解析器/护栏回归修复：身份编号字符类 `[FLIW]`→`[FLIWS]` 恢复体例域 `S-` 条目解析、W 系列新增 `### WL-xxxxxx` h3 形态解析 283→357 条消除 43 处交叉引用误报；§S5 双向提炼规程与治理细则同步）。版本矩阵/依赖兼容矩阵同步。
- **2026-09-12 · v0.2.5**：**审计整改批次上提（doc-review 0.15.7 → 0.17.3）**——①**交付门禁成型**：`deliver_gate.py` 覆盖 `--md` 草稿预检与 `--docx` 交付件九项，新增复核产物门禁 `--annotated`/`--revised` 挂载与 officecli 物理扫描第三态 `[SKIP]`；②**脚本结构性重构**：`check_content.py` 按业务域拆为入口 + `content_common`/`content_text`/`content_table`（对外 CLI 契约不变），配套挖出并修复 `terms` 核对项**自诞生起静默失效**的生产 bug（另修 `<w:b w:val="0">` 加粗误判）；③**文档收口**：使用流程抽取 `references/workflow.md`（主文件瘦身 38%）、交付口径归一到 `references/delivery.md`（单一事实源）、`CHANGELOG` 分代归档（46.9 → 29.2 KB）；④**测试补齐**：`scripts/tests/` 从 0 → 5 脚本 **85 项全过**（含纯标准库 OPC 关系语义守卫）；⑤**规则新增**：格式铁律「数字前后不加空格」（标准号西文缩写与数字间空格为例外）。联动升版 `ibd-doc-annotate` 0.5.3 → **0.5.5**、`ibd-finance-review` 0.8.3 → **0.8.5**（两包交付口径回指 `delivery.md`，依赖下限坐实 doc-review ≥0.16.2）；`ibd-methods-ops` 1.5.1 → **1.5.2**（依赖来源标注与图例对齐）；隐私侧同时清零发布门禁 BLOCK（平台路径与本机用户名）。
- **2026-09-11 · v0.2.4**：**编号体系统一 + 交付门禁**——各包 references 编号示例同步至现行体系（体例域 `S-` 前缀／案号 `AN{4位}`，与库内《编号体系说明》对齐，历史迁移记录按原形态保留）；`ibd-doc-review` 0.15.7 新增交付前综合核验 `deliver_gate.py`；README 补齐 `ibd-doc-write` 能力边界声明（**尚不成熟，不能独立撰写整段投行文件**）；版本矩阵同步至 write 0.13.0 / doc-review 0.15.7 / methods-ops 1.5.1；仓库加 `.gitignore` 防临时文件随包
- **2026-09-10 · v0.2.0**：**新增 2 包**（methods-ops 1.5.0 方法论库生产+维护 / methods-query 0.2.0 检索域）；doc-write 0.9.0（库规范分层）；**双向开放**——库接入（本地/Obsidian/云知识库）与材料来源均由使用者自定；15 个随包脚本（索引/落库/门禁/修复/拆分/迁移）
- **2026-09-10 · v0.1.2**：五包命名收敛（doc-review→格式复核 / gates→质量校验 / annotate→批注与修订交付 / doc-write 去 G4 黑话）；触发词路由分流；SKILL.md 骨架与 README 全量标准化（集合风）；CI 门禁上线；依赖兼容矩阵 + 四包最小复现示例
- **2026-09-10 · v0.1.1**：doc-review 0.15.3（check_revisions 去 lxml 依赖 → 纯标准库，冷启动验证修复）；doc-write / quality-gates 补齐 README；发布渠道文案统一 GitHub；集合 README 产品级重写
- **2026-09-09 · v0.1.0**：集合仓库首版发布，5 包全量（doc-review 0.15.2 / gates 0.8.0 / finance-review 0.8.3 / write 0.8.0 / annotate 0.5.2）

## 📚 文档

- 每个包的使用文档 = 包内 `SKILL.md`（触发词 → 使用流程 → 依赖 → 边界），安装后即可查
- 快速入口 = 各包 `README.md`（能力总览 + 命令附录）
- 规则明细（批注规范 / 修订规范 / 样式映射 / 反模式清单等）在各包 `references/`
- **包间分工与依赖**：上方「工作链路」+「依赖关系图」；doc-review 的对外契约（门禁 CLI / 问题清单 schema / 编号词表 / 版本下限）= [skills/ibd-doc-review/references/interface.md](skills/ibd-doc-review/references/interface.md)
- **上手路径建议**：单包试用 → `ibd-doc-review` 或 `ibd-quality-gates`（零外部 skill 依赖）；写作线全家桶 → doc-write + gates + doc-review + methods-ops；复核线全家桶 → finance-review + doc-annotate + doc-review

## ⚖️ 许可

MIT License。发布物已通过隐私与合规门禁（P0-P7 流水线），可放心用于团队内部分发。

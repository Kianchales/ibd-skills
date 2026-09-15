# 对外接口契约（Interface Contract）

> 本文只列 **ibd-doc-review 对外承诺的稳定接口**——下游包（doc-write / doc-annotate / finance-review / quality-gates）与外部使用者只依赖本页所列内容。
> 细则一律指针化到规范源文件，**不在本页复制**；规范源变更时本页只改「版本下限」，不改语义。
>
> **变更纪律**：本页所列任何接口发生**语义变更**（非纯修订）→ 必须 ① bump 本包次版本 Y，② 在 CHANGELOG 登记，③ 跑下游引用检查（`grep -r "ibd-doc-review"` 于 ibd-doc-write / ibd-doc-annotate / ibd-finance-review / ibd-quality-gates 四包）确认无断链。

---

## 1. 交付口径（单一事实源）

**[references/delivery.md](delivery.md)** —— 自本包 **0.16.2** 起为交付口径唯一事实源：

- 默认交付形态 = 批注版原文 + 精简总览（双轨并存、批注优先）
- 执行链路与门禁硬关卡（非 PASS 退回重注入）
- 批注/修订职权划分（内容级修订稿归 doc-annotate，格式级修订留本包）
- 触发语与路由、批注全量覆盖纪律

下游回指本文件（annotate / finance-review 已回指），**口径不另立、不重复维护**。

## 2. 交付门禁入口

**[scripts/deliver_gate.py](../scripts/deliver_gate.py)** —— 交付前综合门禁，对外 CLI 契约：

| 入口 | 覆盖 | 使用方 |
|---|---|---|
| `--md <内容源.md>` | 内容源预检 | doc-write |
| `--docx <交付件.docx>` | 基础九项（格式/序号/标点/表格等） | doc-write、通用 |
| `--annotated --expect-annotated <N>` | 批注版十一项（基础九项 + 批注 docx 侧三项） | doc-annotate |
| `--revised [--expect-revised N]` | 修订稿（覆盖 check_revisions 全部断言） | doc-annotate |
| `--anchors "36,507.55;19.96"` | 数字锚点核对（可选） | 通用 |

门禁返回非 PASS = 退回重做，**不得带瑕疵交付**。PDF 侧批注校验仍单独跑 `check_annotations.py --pdf`。

## 3. 复核问题清单 schema（结构契约）

清单 = JSON 数组，条目必填字段（doc-annotate `validate_issues.py` 入口校验，ERROR 级缺一拦截）：

| 字段 | 约束 |
|---|---|
| `anchor` | 原文问题句段的**精确子串** |
| `type` | 问题类型词表（见 §4），入口不校验、门禁把关 |
| `sev` | 枚举 {高, 中, 低}（结构校验） |
| `title` / `desc` / `advice` | 非空文本 |

可选字段：`author`（复核人名）、`code`（1-2 位大写字母前缀，缺省回退 `U`）、`rev`（修订稿替换文本，缺则入「待人工」）、`page`（PDF 限定页）。数量卫生：≤200 条/文件，>400 拆分。

**机器可执行版**：[problems.schema.json](problems.schema.json)——上表约束的白名单级机器校验，入口 `scripts/validate_schema.py`（返回码 0=PASS/1=FAIL/2=环境错误）。本节任何约束变更 → **同步 schema 文件 + bump 次版本**；schema 与文字描述冲突时以 annotations.md §4 / 本节语义为准并视为 schema 缺陷须即修。

## 4. 编号体系与类型词表

**[references/annotations.md](annotations.md)** §3/§4 定义（单一事实源）：

- **编号**：`前缀-序号`（如 `J-01`），前缀由复核流程自定义、脚本不内置映射；家族子编号 `J-01a` 为扩展形态（采用前提见 §3 原文）
- **类型词表**：固定 10 项（数据·口径/勾稽/完整性/正负号；表述·绝对化/衔接/歧义；披露·充分性/时效；合规·一致性），**新增须在 annotations.md 登记，禁止自造标签**
- **严重度**：高（必改）/ 中（应改）/ 低（建议改）

## 5. 校验脚本对外入口

| 脚本 | 对外用途 | 直接使用方 |
|---|---|---|
| `check_annotations.py` | 批注版校验（docx 侧已被 deliver_gate `--annotated` 覆盖；**PDF 侧仍直接调用**） | doc-annotate |
| `check_revisions.py` | 修订稿校验（已被 deliver_gate `--revised` 覆盖，一般不直接调） | doc-annotate |
| `check_content.py` | 内容核对（序号/日期/标点/简称/表格等；CLI 契约 0.17.x 重构后不变） | doc-write |
| `check_styles.py` | 样式核对（含 `--revise` 格式修订差异） | doc-write、doc-annotate |

脚本拆分内部实现（content_common/content_text/content_table）**不属对外契约**，可随时重构。

## 6. 版本下限速查（供下游「依赖与工具」节回填）

| 下游依赖本包的能力 | 引入版本 | 现行 |
|---|---|---|
| deliver_gate.py 交付门禁 | ≥ 0.15.7 | 0.18.0 |
| delivery.md 交付口径单一事实源 | ≥ 0.16.2 | 0.18.0 |
| 批注规范 annotations.md 现行体系 | ≥ 0.16.2 | 0.18.0 |
| problems.schema.json 清单机器可执行 schema + validate_schema.py | ≥ 0.18.0 | 0.18.0 |

---

## 沿革

- 2026-09-15 初版：从 delivery.md / annotations.md / 脚本 CLI 提炼对外承诺；细则指针化，下游断链自查方法（grep 四包）固化。
- 2026-09-15 §3 增补：挂 problems.schema.json 机器可执行 schema 指针与 validate_schema.py 入口（ADR-0004，C-分步第一步）；§6 版本下限表同步。

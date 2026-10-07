# 对外接口契约（Interface Contract）

> 本文只列 **ibd-doc-review 对外承诺的稳定接口**——下游包（doc-write / doc-annotate / finance-review / quality-gates）与外部使用者只依赖本页所列内容。
> 细则一律指针化到规范源文件，**不在本页复制**；规范源变更时本页只改「版本下限」，不改语义。
>
> **变更纪律**：本页所列任何接口发生**语义变更**（非纯修订）→ 必须 ① bump 本包次版本 Y，② 在 CHANGELOG 登记，③ 跑下游引用检查（`grep -r "ibd-doc-review"` 于 ibd-doc-write / ibd-doc-annotate / ibd-finance-review / ibd-quality-gates 四包）确认无断链。

---

## 1. 交付口径（单一事实源）

**[references/delivery.md](delivery.md)** —— 自本包 **0.16.2** 起为交付口径唯一事实源：

- 默认交付形态 = 批注版原文 + **复核报告（Excel，按问题性质分表）**（≥0.32.0；批注总览 md 为中间件、不交付用户，**无 Word 版**）
- **进门第一档 = 检查项声明**（≥0.27.0）：复核类委托**动手前先出《本轮检查项声明》**（查哪些 / 不查哪些＋为什么 / S1–S4 专项 / 交付前将跑 F 域），明细清单与模板 = [check-scope.md](check-scope.md)；**声明 ⟷ 交付报告头首尾一致**
- 执行链路与门禁硬关卡（非 PASS 退回重注入）
- 批注/修订职权划分（内容级修订稿归 doc-annotate，格式级修订留本包）
- 触发语与路由、批注全量覆盖纪律

下游回指本文件（annotate / finance-review 已回指），**口径不另立、不重复维护**。

## 2. 交付门禁入口

**[scripts/deliver_gate.py](../scripts/deliver_gate.py)** —— 交付前综合门禁，对外 CLI 契约：

| 入口 | 覆盖 | 使用方 |
|---|---|---|
| `--md <内容源.md>` | 内容源预检 | doc-write |
| `--docx <交付件.docx>` | 基础十项（格式/序号/标点/表格等） | doc-write、通用 |
| `--annotated --expect-annotated <N>` | 批注版十二项（基础十项 + 批注 docx 侧两项） | doc-annotate |
| `--revised [--expect-revised N]` | 修订稿（覆盖 check_revisions 全部断言） | doc-annotate |
| `--anchors "36,507.55;19.96"` | 数字锚点核对（可选） | 通用 |

门禁返回非 PASS = 退回重做，**不得带瑕疵交付**。批注类任务（docx + PDF）**以 doc-annotate 为唯一对外入口**：PDF 侧批注校验（`check_annotations.py --pdf`）由 doc-annotate 内部回调，外部使用者/下游包**不直接调用**（单入口路由，0.19.0 起）。

## 3. 复核问题清单 schema（结构契约）

清单 = JSON 数组，条目字段（doc-annotate `validate_issues.py` 入口校验，ERROR 级缺一拦截）：

| 字段 | 必需性 | 约束 |
|---|---|---|
| `anchor` | 必填 | 原文问题句段的**精确子串** |
| `type` | 必填 | 问题类型词表（见 §4），入口不校验、门禁把关 |
| `sev` | 必填 | 枚举 {高, 中, 低}（结构校验）；升档规则见 §4 |
| `title` | 必填 | 非空文本（问题短标题） |
| `desc` | 必填 | 非空文本（问题描述） |
| `advice` ／ `rev` | **至少其一** | `anyOf` 条件：`advice` = **指令式建议**（「核对…后统一…」）；`rev` = **可直接粘贴的替换文本**。**文本定稿形态**下 `rev` 必填、`advice` 可省（rev 即主交付物） |
| `author` / `code` / `page` | 可选 | 复核人名；1-2 位大写字母前缀（缺省回退 `U`）；PDF 限定页 |
| `nature` / `line` | 可选 | `nature` = **问题性质**（**复核报告分页轴**，与 12 类 `type` 不是一套；推荐五类：①数据不一致／②表述不一致／③自身逻辑／④格式规范／⑤事实存疑，项目可自定标签）；`line` = 被复核文档的**行号或行号区间**（如 `340`、`9044-9046`）。二者供复核报告分页与定位，规格 → [delivery.md](delivery.md) §八之二 |

数量卫生：≤200 条/文件，>400 拆分。

**机器可执行版**：[problems.schema.json](problems.schema.json)——上表约束的白名单级机器校验，入口 `scripts/validate_schema.py`（返回码 0=PASS/1=FAIL/2=环境错误）。本节任何约束变更 → **同步 schema 文件 + bump 次版本**；schema 与文字描述冲突时以 annotations.md §4 / 本节语义为准并视为 schema 缺陷须即修。

## 4. 编号体系与类型词表

**[references/annotations.md](annotations.md)** §3/§4 定义（单一事实源）：

- **编号**：`前缀-序号`（如 `J-01`），前缀由复核流程自定义、脚本不内置映射；家族子编号 `J-01a` 为扩展形态（采用前提见 §3 原文）
- **类型词表**：固定 **12 项**——数据·口径/勾稽/完整性/正负号；表述·绝对化/衔接/歧义；披露·充分性/时效；合规·一致性/禁用表述/来源限定。**新增须在 annotations.md §4 与 ibd-finance-review/issue-list-format.md §2 双册同步登记，禁止自造标签**
- **严重度**：高（必改）/ 中（应改）/ 低（建议改）；**升档规则（双维度取高）**——合规·禁用表述/来源限定恒「高」；涉审核关注点（持续经营/减值/收入确认/关联交易…）的披露充分性问题升「高」

## 5. 多 skill 合并清单约定（P8）

> **动因**：格式问题（标点/序号）与财务问题（口径/勾稽）在同一段落同批出现是常态。若各 skill 各出一份清单，「批注版＋复核报告」的交付会退化成**四轨**（格式清单＋财务清单＋格式报告＋财务报告）——违反 §1 交付口径。

- **一份清单**：多 skill 复核同一文档时，问题清单**合并为一份**（不是各出一份再拼接）。
- **分域靠 code 前缀、排序靠全文位置**：各域用各自 `code` 前缀（J=财务／L=法律／I=行业／Z=综合，见 `annotations.md` §3），条目**按文档全文出现位置升序排列**（不按域分块），域内统计在总览里分列。
- **报告单份**：复核报告**一份**，含「分域统计」小节（各 code 前缀条数、各严重度条数）。
- **编号一次性分配**：合并前统一分配编号，避免两域各自从 01 起导致重号（`annotations.md` §3 编号唯一性校验会拦）。

## 6. 校验脚本对外入口

| 脚本 | 对外用途 | 直接使用方 |
|---|---|---|
| `check_annotations.py` | 批注版校验（docx 侧已被 deliver_gate `--annotated` 覆盖；**PDF 侧仍直接调用**） | doc-annotate |
| `check_revisions.py` | 修订稿校验（已被 deliver_gate `--revised` 覆盖，一般不直接调） | doc-annotate |
| `check_content.py` | 内容核对（序号/日期/标点/简称/表格等；CLI 契约 0.17.x 重构后不变） | doc-write |
| `check_styles.py` | 样式核对（含 `--revise` 格式修订差异） | doc-write、doc-annotate |

脚本拆分内部实现（content_common/content_text/content_table）**不属对外契约**，可随时重构。

## 7. 版本下限速查（**下游契约登记处** · 升版必核）

> **本表只登记「引入版本」**——下游据此声明自己的最低版本。
> ⚠️ **「本包当前版本」不在此重复**：本表原有一列「现行」，写死 0.18.0 而包已行至 0.22.0（**该列必然过期、且无维护动作**）；当前版本看 frontmatter 与 `CHANGELOG.md`。

| 下游依赖本包的能力 | 引入版本 | 下游消费方 |
|---|---|---|
| `deliver_gate.py` 交付门禁 | ≥ 0.15.7 | `ibd-doc-write` |
| `delivery.md` 交付口径单一事实源 | ≥ 0.16.2 | `ibd-finance-review` |
| 批注规范 `annotations.md` / `revisions.md` 现行体系 | ≥ 0.16.2 | `ibd-doc-annotate` |
| `problems.schema.json` ＋ `validate_schema.py` | ≥ 0.18.0 | （包内自用） |
| **单入口路由语义**（批注任务单唯一对外入口） | **≥ 0.19.0** | `ibd-doc-annotate` |
| **三形态交付路由**（批注/文本定稿/修订 ＋ 项目级形态记忆） | **≥ 0.26.0** | `ibd-finance-review`、`ibd-doc-annotate` |
| **复核深度三档**（L1/L2/L3 ＋ 报告头档位声明） | **≥ 0.26.0** | `ibd-finance-review` |
| **禁词红线 `banned-terms.json`**（单一事实源，装载式） | **≥ 0.26.0** | `ibd-doc-write`（经 deliver_gate 传递） |
| **禁词文档类型作用域**（行为禁语仅招股书／绝对化用语全场景） | **≥ 0.26.1** | `ibd-doc-write`、`ibd-finance-review` |
| **类型词表扩至 12 类**（新增 `合规·禁用表述`／`合规·来源限定`） | **≥ 0.26.2** | `ibd-finance-review`、`ibd-doc-annotate` |
| **严重度升档规则**（错误性质 × 监管后果 取高） | **≥ 0.26.2** | `ibd-finance-review` |
| **清单 `advice`／`rev` 条件必填**（`anyOf`；文本定稿形态 rev 为主交付物） | **≥ 0.26.2** | `ibd-doc-annotate`、`ibd-finance-review` |
| **多 skill 合并清单约定**（单份清单·code 分域·全文位置排序） | **≥ 0.26.2** | `ibd-finance-review`、`ibd-quality-gates` |
| **复核片段模式**（输入完整性探测：片段输入收窄核对项） | **≥ 0.26.2** | `ibd-finance-review` |
| **复核报告（Excel）形态**（清单新增可选字段 `nature`／`line`；报告分页与台账） | **≥ 0.32.0** | `ibd-doc-annotate` |

> ⚠️ **0.26.0→0.26.1 禁词口径两次变更（下游须照此理解 FAIL 的含义）**：
> ① **0.26.0 扩表**：默认禁词 13→35（新增「经核查」等行为禁语）。
> ② **0.26.1 分域（回归修复）**：行为禁语**仅在 `--scenario 招股书` 装载**——「经核查，保荐机构认为…」是**反馈回复的规范句式**，0.26.0 把它摊平到全场景，导致回复件大面积 FAIL，属**门禁误报**（已修）。
> **下游读法**：`deliver_gate.py --scenario` 现同时决定**样式集**与**禁词作用域**——跑回复件必须传 `--scenario 反馈回复`（默认值即此），跑招股书传 `--scenario 招股书`；不传/传错会让行为禁语在错误的文档类型上生效或失效。
> 另：`level=MINOR` 的词（如「不构成盈利预测或业绩承诺」）**不阻断面只提示**——PASS 行下会带「（提示·不阻断）」明细，属预期、非误报。

**升版动作**（本包版本递增后）：核对每行「引入版本」是否需上调；**任一行变动** ⇒ 同步该行「下游消费方」所列包的活指针。

---

## 沿革

- 2026-09-15 初版：从 delivery.md / annotations.md / 脚本 CLI 提炼对外承诺；细则指针化，下游断链自查方法（grep 四包）固化。
- 2026-09-15 §3 增补：挂 problems.schema.json 机器可执行 schema 指针与 validate_schema.py 入口（C-分步第一步）；§6 版本下限表同步。
- 2026-09-15 §1/§5 修订：批注任务单入口路由——check_annotations.py（尤其 PDF 侧）不再直接暴露，doc-annotate 为唯一对外入口、内部回调；§6 表加行并全表现行刷至 0.19.0。
- **收口（低成本改进 ①）**：删「现行」列（**必然过期且无维护动作**——写死 0.18.0 而包已至 0.22.0）；补「**单入口路由语义 ≥ 0.19.0**」行（下游 `ibd-doc-annotate` 早已按此声明，却**从未登记在本表**）；增「**下游消费方**」列，并给三个下游包的活指针加回指——§6 自陈「供下游回填」，而此前三个下游**均未回填**。新增「升版动作」一行，把核对义务写进本册而非靠记忆。

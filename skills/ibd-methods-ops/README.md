# ibd-methods-ops

方法论知识库「学习（产知识）+ 维护（保健康）」一体化 skill——把案例（招股书 + 问询回复）蒸馏沉淀为新方法论，并用护栏与工具链保持库结构健康。

## 💡 这是什么

> **设计原则 · 双向开放**：资料来源与沉淀去向都由用户自己确定——材料从哪来（对话给文件/文件夹/项目，或已接入的库）、沉淀到哪去（本地/Obsidian/云知识库等），全部由用户定；skill 提供流程、规范与工具，不绑定私有环境。

- **蒸馏域**：S1-S7 全流程——选材 → 材料准备（三阅读包）→ 多专家并行蒸馏 → 综合成文（写作范式）→ 模拟回复演练 → 共通点蒸馏 → 沉淀入库（索引刷新 + 护栏校验）
- **维护域**：库结构健康——8 项护栏体检 → 修复工具箱（先 dry-run）→ 复验幂等
- **随包工具链**：15 个脚本（索引体系 / 落库 / 门禁 / 修复 / 拆分 / 迁移），全部支持 `--methods-root` 或 `$METHODS_ROOT`
- **库规范单一事实源**：[references/methods-guide.md](references/methods-guide.md)（目录结构 / 条目结构 / 索引机制 / 规模化拆分）

## ✨ 快速开始

```
触发词「蒸馏学习这个文件 / 这个文件夹 / 这个项目 / 库里这批材料」→ 用户确定学习范围（文件/文件夹/项目/已接入的库，可组合），走 S0-S7 全流程
触发词「执行蒸馏学习XX次」→ 走 S0-S7 全流程（单用户模式本人串跑；团队模式多角色协作）
触发词「方法论体检」        → 走维护域 3 步（体检 → 修复 → 复验）

# 库维护（命令示例）
python scripts/refresh_index.py --methods-root ~/methods        # 索引一键刷新（四件套编排）
python scripts/check_methods_health.py --methods-root ~/methods # 8 项护栏体检（0 ERROR 交付）
python scripts/update_expert_md.py --entries batch.json --methods-root ~/methods  # 条目落库
```

## 🧩 核心能力

- **蒸馏方法论**：S4 三段式产出规范 / S5 五步提炼法 / S5.5 模拟回复演练 / S6 共通点判定（重合度分级 + 修订留痕）——细节见 [references/distill-methods.md](references/distill-methods.md)
- **编号体系**：主库四域 `域-族号2位-族内4位` + 案例层 `AN{案号4位}`（三层隔离，防碰撞）
- **库演进**：单体→域文件拆分（配置驱动，G1 条目守恒自校验）、编号位宽迁移（dry-run 预检 + 幂等执行）
- **渐进披露检索适配**：库由「入口薄壳 + 域文件 + 生成物索引」组成，配合 ibd-methods-query 定向读取

## 🔗 与生态内其他 skill 的分工

- `ibd-methods-query`：互补——本 skill 管生产+维护（写入侧），query 管检索消费（读取侧）
- `ibd-doc-write`：库的消费方（写作引用 + 无库降级）；本 skill 的库规范是其消费侧指引的完整版
- `ibd-doc-review`：方法论文件的格式问题移交

## 📦 安装与依赖

拷贝至用户级技能目录。依赖：

- **方法论库 `{METHODS_ROOT}`**（使用者自建，路径可配置，示例 `~/methods/`）——库规范见本包 references/methods-guide.md
- **Python 3**（随包脚本；零第三方依赖）
- **KB 后端**（🟢 可选）：蒸馏笔记落库默认本地 `{METHODS_ROOT}/notes/`；可选接 MCP 知识库/云文档等连接器
- **运行模式**：单用户模式（默认，本人串跑全流程）/ 团队模式（可选，多角色协作——财务/法律/行业专家 + 写作角色）

## 📁 目录结构

```
SKILL.md                 双域流程 SOP（蒸馏域 S1-S7 + 维护域 3 步）
scripts/                 15 个随包脚本
  refresh_index.py         索引一键刷新（parse→gen_index→gen_toc→gen_entry）
  parse_titles.py          条目解析 → parsed_titles.txt
  gen_index.py             生成 方法论调用索引.md
  gen_toc.py               生成 方法论_条目标题目录.md
  gen_entry.py             重写入口（路由表 + 摘要保留）
  update_expert_md.py      条目落库（h3/表格双形态 + 超线归档）
  check_expert_output.py   S4.5 产出自检门禁
  check_methods_health.py  8 项护栏体检
  add_frontmatter.py / add_fm_single.py / b_fmt_unify.py / c_scale_dedup.py   结构修复工具箱
  split_domains.py         单体库 → 域文件拆分（配置驱动）
  dryrun_case_migrate.py / migrate_case_no.py   编号迁移（预检 + 执行）
references/
  methods-guide.md         库规范单一事实源（目录/条目/索引/拆分）
  distill-methods.md       蒸馏提炼方法单一事实源（S4/S5/S5.5/S6）
  govern/health-check.md   护栏体检项详表
  govern/fix-tools.md      修复工具箱索引与边界
CHANGELOG.md             版本记录
```

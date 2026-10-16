# Claude Code 安装说明

## 安装

```bash
# 项目级（仅当前项目可用）
mkdir -p <你的项目>/.claude/agents
cp claude-code/agents/*.md  <你的项目>/.claude/agents/

# 或用户级（所有项目可用）
mkdir -p ~/.claude/agents
cp claude-code/agents/*.md  ~/.claude/agents/
```

## 使用

1. **入口**：主对话就是主理人【郑知行】。直接说需求，例如：
   - 「帮我分析XX公司 IPO 项目，财务/法律/行业三维度深度评估」
   - 「审查XX公司招股说明书，重点看财务规范性与法律合规」
2. **编排**：主理人按 `core/ARCHITECTURE.md` 的协作七拍与四组交接契约，把分析/采集/归档/写作任务派发给六个子代理（finance/legal/industry/downloader/manager/writer），回传后汇总把关交付。
3. **门禁**：写作产出自动过 `core/quality-gates.md` 五道门；多成员任务收尾附验收单（可用 `scripts/check_team_accept.py` 机检）。

## 可选增强

- 把本包 `core/`、`references/` 一起放进项目目录，子代理即可引用质量门禁全文与 SOP。
- 配置 Wind 数据 MCP（公开服务）后，财务/行业对标走第一数据源；未配置按角色卡降级路径走公开源。
- 方法论库（进阶）：按 `references/sop/distill-sop.md` 从零建立，配置教学见 GitHub `Kianchales/ibd-skills`（非必需）。

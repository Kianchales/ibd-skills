# 投资银行专家团（公共版）

7 角色 A 股 IPO 分析专家团队（主理人＋财务/法律/行业三专家＋文档采集/管理＋写作），平台无关。

## 安装

- **WorkBuddy**：目录放入你的专家市场插件目录，注册后重启，于专家中心启用
- **Claude Code**：`cp claude-code/agents/*.md ~/.claude/agents/`
- **其他对话平台**：把 `core/TEAM-HANDBOOK.md` 作为 system prompt
- **通用**：直接让 AI「阅读本仓库 README 并安装」

## 结构

```
core/          平台无关内核（角色卡×7 / 架构文档 / 质量门禁 / 团队工作手册）
agents/        WorkBuddy 适配器（7 成员）
claude-code/   Claude Code 适配器
references/    蒸馏 SOP（空库版）/ 知识库体检 SOP / 写作模板（docx+md）
scripts/       验收单机检脚本
```

## 边界

非持牌投顾，输出不构成投资建议；敏感法律定性只列选项不结论；纯对话平台为单模型分角色串演。

## 许可

MIT（见 LICENSE，© 2026 默光）。

# ibd-skills

A 股投行（IBD）工作流 skill 集合仓库：投行文档的写作、质量门禁、财务复核、格式规范与批注交付全链路。

## 集合内 skill

| skill | 定位 | 版本 | 依赖 |
|---|---|---|---|
| [ibd-doc-review](skills/ibd-doc-review/) | 投行文档格式层单一事实源：样式应用、格式核对、批注/修订规范与校验门禁 | 0.15.2 | 零外部 skill 依赖（基座） |
| [ibd-quality-gates](skills/ibd-quality-gates/) | 交付前内容质量门禁：数字五要素、反模式扫描、五道质量门（G1-G5）、数值自洽核对 | 0.8.0 | 推荐配 ibd-doc-review |
| [ibd-finance-review](skills/ibd-finance-review/) | 招股书/申报文件财务章节深度复核（16 维清单，锚定企业会计准则） | 0.8.3 | 零硬依赖（纯规范清单包） |
| [ibd-doc-write](skills/ibd-doc-write/) | 投行文档写作总入口：反馈回复五步链路、招股书章节/报告/备忘录结构规范、投行语言写作规范 | 0.8.0 | 🔴 ibd-quality-gates ≥0.7.0 + ibd-doc-review ≥0.15.0 + 任一 docx 工具 |
| [ibd-doc-annotate](skills/ibd-doc-annotate/) | 复核结论落地执行器：批注版（Word/PDF）与修订稿生成 | 0.5.2 | 🔴 ibd-doc-review（annotations.md / revisions.md / 校验门禁） |

## 链路

```
doc-write 写草稿 → quality-gates 内容门 → doc-review 套样式+格式核对 → 正式稿
finance-review 产出复核清单 → doc-annotate 注入批注（按 doc-review 规范）→ 批注版原文 + 精简总览
```

## 安装

将所需 `skills/<包名>/` 目录拷贝至你的技能安装目录（如 WorkBuddy 的 `~/.workbuddy/skills/`）。带 🔴 依赖的包须连同依赖包一起安装，缺依赖时的断链自助指引见各包 SKILL.md「依赖与工具」。

## 版本与发布

- 每包独立版本（SemVer），版本记录见各包 `CHANGELOG.md`
- 发布 tag 采用包前缀：`ibd-doc-review-v0.15.2`、`ibd-quality-gates-v0.8.0`
- Release 附件 zip 仅含对应包子目录

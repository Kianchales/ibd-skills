# 从零建库引导（Bootstrap）

> 本 skill 假定「库已存在」——它管的是**库怎么用**。本文件补上前半段：**库怎么来**。
> 适用对象：第一次使用本 skill、手上还没有库的人。已有库者直接照 [SKILL.md](../SKILL.md) 用即可，无需看本文件。
>
> 全程约 15 分钟。四步：装 Obsidian → 建库 → 装插件 → 复制骨架 → 验收。

---

## 第 0 步 · 前置：Obsidian

本 skill 的操作对象是一个 **markdown 文件夹（库 / Vault）**，推荐用 [Obsidian](https://obsidian.md/) 打开以获得 Tasks / dataview 等插件带来的看板与查询能力。

- 下载安装（免费）：中文站 https://obsidian.md/zh/ ｜ 英文站 https://obsidian.md/
- **不装 Obsidian 也能用**：库就是普通文件夹，WorkBuddy 侧可直接读写；但库内的看板、看板查询会退化为纯文本（见 [SKILL.md](../SKILL.md)「缺失降级」）。

## 第 1 步 · 建库（两选一）

**A. 新建**：在想要的位置新建一个空文件夹（例如命名为 `我的库`），把它作为库根。想多端同步就建在同步盘里（OneDrive / iCloud / 坚果云等）。

**B. 已有文件夹**：直接拿它当库根——但需确保里面没有会被本骨架覆盖的同名文件。

> ⚠️ 库根目录名随意，但**库内的一级目录名（`01 资料`/`02 工作`/`03 报告`/`04 AI Work`）不要改**——各查询语句按这些字面路径检索，改名即查询全失效。

## 第 2 步 · 装插件

Obsidian 里：`设置 → 第三方插件 → 关闭「安全模式」→ 浏览` 搜索安装并**启用**。

| 必要性 | 插件 | 作用 |
|---|---|---|
| **必需** | **Tasks** | 待办语法与查询（日志 / 看板 / 日报全靠它） |
| **必需** | **Dataview** | 数据查询（看板聚合、项目总览）；需在设置里**开启 JavaScript 查询**（Overview 用到 dataviewjs） |
| 推荐 | **Periodic Notes** | 日报 / 周报 / 月报的周期笔记创建与跳转 |
| 推荐 | **Templater** | 模板变量（`<% tp.date.now(...) %>`），周期笔记套模板用 |
| 推荐 | **Buttons** | 首页周期按钮（`Home.md` 里的三个按钮） |
| 推荐 | **Kanban** | 项目看板（`项目看板.md`） |
| 可选 | Folder Note | 点文件夹名直接打开同名说明笔记 |
| 可选 | Iconize / Calendar / Advanced Tables / Style Settings | 图标 / 日历 / 表格 / 外观增强 |
| 内置 | **Bases** | Obsidian 1.7+ 内置，用于日报数据库 `01 日报.base`；版本过低可忽略该文件 |

## 第 3 步 · 复制骨架

把本包 `assets/starter-kit/` 目录下的**全部内容**复制到你的库根（保持目录结构）。

```
库根/
├── README.md            库使用手册（新会话第一读；介绍下面各区怎么用）
├── Home.md              仪表盘 + 周期按钮
├── Overview.md          项目总览（dataview 聚合：进行中 / 逾期 / 近 7 天 / AI 待办）
├── 01 资料/             私人资料区（AI 不介入）
├── 02 工作/
│   ├── 01 任务/         01 任务.md（全库任务视图）+ 团队任务/（成员统计视图）+ 视图/（逾期 / 即将 / 已完成）
│   └── 02 项目/         02 项目.md（总览）+ 项目看板.md（kanban）
│       ├── 01 进行中/    进行中项目（含 01 进行中.md 导航）
│       ├── 02 待开始/    待启动项目
│       ├── 03 已完成/    完结项目归档
│       └── 04 模板/      ★ 项目七件套模板（新项目复制整夹改名即用）
├── 03 报告/
│   ├── 01 日报/         日报 + 01 日报.base（Bases 数据库）
│   ├── 02 周报/  03 月报/
│   └── 04 模板/         日报 / 周报 / 月报模板
└── 04 AI Work/
    ├── 工作日志/        工作日志.md（仪表盘）；按月文件 YYYY-MM-待办.md 随用随建
    ├── 待办事项.md       AI 待办看板（按 #性质 聚合）
    ├── 机器拓扑清单.md   ★ 多机环境的身份与判机（主机／副机）；单机可留空
    ├── AI资料库/        AI 研究 / 学习笔记长期留存
    └── 临时文件/        暂存 md 统一落点
```

> 骨架里每个目录都带一份同名说明笔记（如 `04 AI Work/AI资料库/AI资料库.md`），打开即知用途，上手后可自行增删。
> **空目录不会出现在 git 里**——若用 git 管理本库，请在空目录放一个占位文件（如 `.gitkeep`）。

## 第 4 步 · 插件配置（让查询跑起来）

装完插件还差几步配置，否则查询块会显示为「一段代码」而非结果：

**Tasks**（设置 → Tasks）
- 勾选 **Set done date on every completed task**，完成日期格式设为 `YYYY-MM-DD`（与日志铁律里的 `✅ YYYY-MM-DD` 对齐）
- 到期日期格式同样设为 `YYYY-MM-DD`

**Dataview**（设置 → Dataview）
- 打开 **Enable JavaScript Queries**（Overview 的逾期 / 近期待办块是 dataviewjs）

**Templater**（设置 → Templater）
- **Template folder** 指向 `03 报告/04 模板`
- 打开 **Trigger Templater on new file creation**（配合 Periodic Notes 自动套模板）

**Periodic Notes**（设置 → Periodic Notes）
- **Daily**：Folder 指向 `03 报告/01 日报`，Format 例 `YYYY/MM-MMMM/YYYY-MM-DD`，Template 选 `03 报告/04 模板/日报模板`
- **Weekly / Monthly** 同理，分别指向 `03 报告/02 周报`、`03 报告/03 月报` 与对应模板

**Buttons**
- 无需配置；`Home.md` 里的按钮 action 用「插件显示名: 命令显示名」（如 `Periodic Notes: Open daily note`）

## 第 5 步 · 验收清单

- [ ] Obsidian 打开库根，能看到 `Home.md` / `Overview.md` 与四个一级目录
- [ ] 点 `Home.md` 的三个按钮，能新建出对应周期的笔记
- [ ] 打开 `04 AI Work/待办事项.md`——查询块渲染出「无内容 / 空」而非一段代码（＝ Dataview 生效）
- [ ] 打开 `Overview.md`——显示「✅ 无逾期任务」等提示（＝ dataviewjs 生效）
- [ ] 在 WorkBuddy 侧让 skill `ibd-life-manager` 生效：新会话按「接续三入口」（库手册 → 工作日志 → 待办看板）能读到内容

五条全过 ⇒ 库可用，后续照 [SKILL.md](../SKILL.md) 的规则操作即可。

## 常见问题

| 现象 | 原因 / 处理 |
|---|---|
| 查询块显示为一段灰色代码 | 对应插件（Dataview / Tasks）未安装或未启用 |
| 任务不聚合进成员统计视图 | 负责人写进了事项文字；必须写在 `### 人名` 标题下、不写进事项正文 |
| 写了 `📅` 但没被识别 | 写了「裸 📅」（后面无日期），或用了非绝对日期；须 `📅 YYYY-MM-DD` |
| 改了目录名后查询全空 | 查询按字面路径检索，目录名勿改（改则须同步改所有查询里的路径） |
| `01 日报.base` 打不开 | Obsidian 版本低于 1.7（无 Bases）；忽略该文件，不影响其余功能 |
| 多端同步后读到旧内容 | 同步盘存在中间态窗口——隔几秒重读，`mtime`/`size` 两次一致后再判断 |

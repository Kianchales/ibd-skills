---
tags: Dashboard
---

# Overview

> 项目工作台总览 ｜ dataview 实时聚合，改动即时反映 ｜ 操作请回到各项目原文件

## 🚧 进行中项目

```dataview
TABLE
	项目类型 AS 类型,
	状态 AS 状态,
	截止日期 AS 截止
FROM #Action/Project
WHERE 状态 = "进行中"
SORT 截止日期 ASC
```

```dataviewjs
// 一次全库扫描：取「进行中」项目 → 按所属项目文件夹归集未完成任务 → 三类视图共用同一份结果
// （旧写法为每类视图各自逐项目 `dv.pages(folder)` 重扫，复杂度＝视图数 × 项目数 × 全库页数）
const today = dv.date('today');
const weekLater = today.plus({ days: 7 });
const projects = dv.pages('#Action/Project').where(p => p.状态 === "进行中").sort(p => p.file.name);
const projByFolder = new Map(projects.map(p => [p.file.folder, p]));

// 由文件路径逐级上溯，定位其所属项目文件夹（命中最内层项目）
function ownerOf(path) {
  let folder = path.split('/').slice(0, -1).join('/');
  while (folder) {
    if (projByFolder.has(folder)) return projByFolder.get(folder);
    const i = folder.lastIndexOf('/');
    if (i < 0) break;
    folder = folder.slice(0, i);
  }
  return null;
}

// 合计只扫一遍：任务按项目文件夹入桶
const buckets = new Map();
for (const page of dv.pages()) {
  const proj = ownerOf(page.file.path);
  if (!proj) continue;
  const list = buckets.get(proj.file.folder) || [];
  for (const t of page.file.tasks) if (!t.completed) list.push(t);
  buckets.set(proj.file.folder, list);
}

const sections = [
  { heading: '⚠️ 逾期未做', empty: '✅ 无逾期任务',
    keep: t => t.due && dv.compare(t.due, today) < 0,
    order: (a, b) => dv.compare(a.due, b.due) },
  { heading: '📅 近期待办（7 天内）', empty: '📭 7 天内无到期任务',
    keep: t => t.due && dv.compare(t.due, today) >= 0 && dv.compare(t.due, weekLater) <= 0,
    order: (a, b) => dv.compare(a.due, b.due) },
  { heading: '📥 未排期待办', empty: '📭 无未排期任务',
    keep: t => !t.due && !t.parent, order: null },
];

for (const sec of sections) {
  dv.header(2, sec.heading);
  let any = false;
  for (const proj of projects) {
    const tasks = (buckets.get(proj.file.folder) || []).filter(sec.keep);
    if (sec.order) tasks.sort(sec.order);
    if (tasks.length === 0) continue;
    any = true;
    dv.header(3, `🏷 ${proj.file.name}`);
    dv.taskList(tasks, false);
  }
  if (!any) dv.paragraph(sec.empty);
}
```

## 🤖 AI 待办

```dataview
TASK
FROM "04 AI Work/工作日志"
WHERE !completed
```

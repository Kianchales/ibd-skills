# 维护规程（改规则 · 升版本 · 对下游）

> 本文件装「改这个包的时候要同步什么」。日常复核不读它。
> **格式规则只在本包改**——`ibd-doc-annotate`（执行器）与 `ibd-doc-write`（写作）引用本包规范，不重复维护。

## 一、规则变更同步清单（漏一环，该规则即形同不存在）

改一条格式铁律，须同步 **6 环**：

| 环 | 落点 | 不同步的后果 |
|---|---|---|
| ① 规则本体 | `references/rules.md` | 无规范可依 |
| ② 检测脚本 | `content_text.py` ＋ `deliver_gate.py`（**双处同源正则**） | 漏一处则门禁放行 |
| ③ 核对项名 | `CHECK_REGISTRY`／模块 docstring／`workflow.md` 表格／`SKILL.md` 资源索引 | 名字对不上，脚本跑不到 |
| ④ 写作侧预防 | `ibd-doc-write/references/writing-style.md`（写作环节不加载本 skill） | 规则不落写作侧，产出即违例 |
| ⑤ 版本 | CHANGELOG ＋ 版本 bump ＋ README 变更摘要 | 下游无从感知 |
| ⑥ 测试 | 命中 ＋ 豁免不误报双用例；端到端探针 | 改完不知道有没有打偏 |

> **复发形态**：「中文不加空格」曾只做 ①③⑤，②④ 从未覆盖 ⇒ 中英之间长期无条款、无拦截。

## 二、报告形态同源对

`delivery.md` §八之二（报告规格）⟷ `ibd-doc-annotate/scripts/review_report_to_xlsx.py`（生成器）——**改规格须同改生成器**，否则规范只写在纸上。

## 三、升版后必做

- **核下游契约**：[interface.md](interface.md) §7「版本下限速查」是下游依赖的**唯一登记处**（含「引入版本」与「下游消费方」两列）；下限数值**不在本页或 SKILL.md 重复**。
- **核入口体量**：`python skills/skill-publish-pipeline/scripts/check_entry_budget.py`——自建包 `SKILL.md` ≤ 10,000 字符，基线只许降；超了先搬细则，不靠登记放行。
- **跑门禁**：`health_all.py` 与 `check_refs.py --traces ibd-doc-review`。

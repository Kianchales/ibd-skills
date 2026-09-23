# 修复工具箱索引（维护域 · 步骤 2）

> 脚本单一事实源：`scripts/`。修复工作流：体检定位 ERROR → 选脚本 → **先 dry-run 核对改动清单** → 执行 → 验证 → 重跑 `refresh_index.py` → 复跑护栏确认 0 ERROR 且幂等。

## 修复脚本一览

| 脚本 | 用途 | 何时用 | 铁律 |
|------|------|--------|------|
| `add_frontmatter.py` | 全库根目录 md 补 frontmatter（域/单案/行业合并版） | 新文件或迁移后缺 frontmatter（体检项 1） | 幂等（重跑 dry-run 0 计划）；注入前先 dry-run 核对映射 |
| `add_fm_single.py` | `行业方法论_单份细分版/` 补 frontmatter | 单份细分版缺 frontmatter（体检项 1） | case/class 从文件名提取，dry-run 核对 |
| `b_fmt_unify.py` | 结构归一：域前缀去前缀/版本批次标题转注记/分组标题降 h4 | (N) 编号不连续、h2 残留、非条目 h3（体检项 2/3） | **只改结构不改内容**；备份先行；行数守恒断言 |
| `c_scale_dedup.py` | 质量自评量表去重（单案完整量表 → 引用指针 + 注记） | 单案出现完整量表定义（内容去重） | 结构模式断言验证（标题/空行/注记/空行/表头）；唯一性断言 |

> 备份约定：执行前 `cp` 至**库外** `archive/scripts/<脚本名>_backup_YYYYMMDD/`（2026-09-16 起归档归库外）；验证脚本同目录留档。

## 三个单一事实源边界（防越界）

| 域 | 单一事实源 | 本 skill 不得 |
|----|-----------|--------------|
| 索引刷新 | `daily_distill.py refresh_index.py`（parse→gen_index→gen_toc→gen_entry 链路） | 不另写一套刷新逻辑 |
| 格式规范 | `ibd-doc-review` skill（样式体系/rules.md，2026-08-25 用户裁定） | 不重定义格式规则 |
| 脚本本体 | `scripts/` | 不复制脚本进 skill，只引用路径 |

## 历史治理脚本归档（v35 残留）

`unify_methodology_format.py / unify_methodology_format2.py / check_methodology_format.py / replace_bare_refs.py / replace_cn_numbers.py / renum_legacy12.py / renum_writing_domain.py` 已归档 `scripts/_archive/`（不再被引用，保留实证；scripts 目录自身不积累重复沉淀）。

## 修复后验证清单（五步）

1. **dry-run 计划核对**：改动清单逐项确认（文件/行号/变换类型），无误再执行
2. **执行 + 备份**：备份先行；执行后立即验证
3. **结构/内容守恒断言**：行数守恒、diff 与计划精确一致、案维数据行零损伤
4. **重跑生成器**：`daily_distill.py refresh_index.py` 刷新生成物（目录/索引/入口）
5. **复跑护栏**：`check_methods_health.py` 0 ERROR + 幂等（重跑 0 计划/0 改动）


---

## 附：全库编号迁移踩坑实录（案号 2→4 位化实证 · 自 `SKILL.md` 维护域原样迁入 · 2026-09-21 瘦身）

**全库编号迁移踩坑实录（案号 2→4 位化实证，工具随包 = dryrun_case_migrate.py + migrate_case_no.py）**：① Python 正则 `\b` 把汉字算 `\w`，「见 L-C01-04」等紧贴中文的编号 token 会漏匹配——用 `(?<![0-9A-Za-z])` lookbehind 替代；② 迁移脚本必须**幂等或只跑一次**——无后缀约束的规则（如 `case_no: C(\d{1,2})`）重跑会把已 4 位案号二次补零（C0022→C000022），补救靠「位长分布终验」（统计全库 C 号位数分布，非 4 位逐个分类核验）+ 备份 diff；③ 表行 `| C34 |` 在行业方法论/单份细分版文件头是证监会行业分类码（GB/T4754），与案号同形——表行批量替换仅限对照/登记表，全库替换前必须先抽上下文分类（案号/国标码/类序号/占位符）；④ 先干跑报告 → 人工抽查计数 → 备份 → 执行 → 四门复验（token 残留 0 / 裸号分类扫 / 护栏 0 ERROR / 形态抽查）


---

## 附：关键要点（库演进安全 · 自 `SKILL.md`「关键要点」原样迁入 · 2026-09-21 瘦身）

- **库演进安全**：批量脚本操作铁律——dry-run 必须真正只读、迁移脚本幂等或只跑一次、全库替换前先分类上下文（详表见「维护域」踩坑实录）；重大结构变更前先备份（`methods/archive/`）

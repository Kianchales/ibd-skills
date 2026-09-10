# CHANGELOG

### 文档骨架对齐（2026-09-10 · T1/T2 标准）

- README 补齐至 T2 九节骨架（+典型场景/近期更新/许可）；SKILL.md 参考节改「资源索引」+ 补「维护」节（文档级，未 bump）

## [0.2.0] - 2026-09-10

### 公开化：通用化改造

- 索引资产改为「使用者自建」模型（路径 `{METHODS_ROOT}` 可配置；资产由 ibd-methods-ops 脚本生成）
- 路径基准去私有常量；表述与公开生态对齐（与 ops 互补关系、供 doc-write 可选调用）
- 库规范引用指向 ibd-methods-ops 的 methods-guide.md（单一事实源）

## [T3] - 2026-09-10

### 标准化：SKILL.md 骨架对齐公开层 + 新增 README（T3 · 文档级）

- 补「定位简介」「边界与协作」节 + frontmatter summary；新增 README（私有标注 + 定位/快速开始/分工/目录结构）；内容零删减，仅结构对齐


## v0.1.1（2026-09-03 · 数据勘误）

- **单案条目总数勘误**：检索三层「单案 1228 条」→ **1258 条**（2026-09-03 逐文件 unique-ID 实测）。差异来源：①对照表合计行误算（行分项和实为 1244）②钜芯 C21 编号列表型 W 条目 12 条迁移时漏计 ③泓毅/环动各 +1 正常漂移——详见 `tasks/单案索引对照表`「五、完整性复核」
- SKILL.md 检索对象三层表同步更正；version 0.1.0→0.1.1

## v0.1.0（2026-08-31 · 初始开发版）

- **创建**：方法论检索 skill（ibd-methods-query）——检索域，固化「索引→定向读取→合成」链路，治 824KB 方法论库 token 膨胀
- **触发**：查方法论/方法论检索/怎么回复XX问题/查XX案XX问题写法
- **结构**：SKILL.md（薄壳）+ references/retrieval-chain.md（检索链路）+ examples/response-retrieval.md（演示）
- **检索对象三层**：主库 719（28Q 速查）+ 行业合并版 + 单案 1228（C 号，v37 体系）
- **接线**：ibd-doc-write response-chain 写作前调用；G4 引用清单由 S4 产出
- **用户裁定**：独立 skill（不并入 ibd-doc-write/ibd-methods-ops）；检索范围三层全含
- **标准模板合规检查**（对照 skill-creator）：
  - 补 `{METHODS_ROOT}` 路径基准声明（SKILL.md 索引资产章节 + references/retrieval-chain.md 顶部）——兑现架构文档「路径外置」约定
  - 新增「依赖与工具」小节（Read/Grep 内置、零外部依赖）
  - **修正演示行号失真**：examples/response-retrieval.md + references S3 示例的行号与实际不符（F-010001 实际 L12 非 L123、F-010002 实际 L109 非 L131、WL-150001 实际 L18 非 L45），已改为实际值并注明「以条目标题目录实时查询为准」

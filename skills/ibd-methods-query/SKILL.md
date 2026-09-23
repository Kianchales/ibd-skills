---
name: ibd-methods-query
slug: ibd-methods-query
displayName: IBD 方法论检索
description: 方法论知识库「检索域」skill——把「索引→定向读取→合成」固化为标准检索链路，查方法论时按问题域定位速查表 → 条目编号 → 行号 → 定向读取，避免全文读库的 token 膨胀。触发词「查方法论」「方法论检索」「怎么回复XX问题」「查XX问题怎么写」「查XX案XX问题的写法」；写作/分析/问答消费方法论时走标准检索链路。与 ibd-methods-ops（生产 + 维护）互补，供 ibd-doc-write 可选调用（无本 skill 时按其内嵌流程运行）。
summary: 方法论库「检索域」——标准检索链路「问题拆解→索引定位→定向读取→合成」，按需只读命中条目不全文读库，配套速查表 + 条目行号定位资产。
agent_created: true
version: 0.5.0
---

# ibd-methods-query

## 定位简介

方法论库**检索域**：链路「问题拆解 → 索引定位 → 定向读取 → 合成输出」，只读命中条目、绝不全文读库。

## 何时使用（触发）

- 写作/分析/问答需要查方法论：写反馈回复、招股书章节、尽调报告前的「问题拆解→查条目」
- 直接问「XX 问题怎么写 / 查 XX 问题方法论 / 查 XX 案 XX 问题的写法」
- 交付前的引用清单生成（引用来源对照）

## 检索流程（S1-S4 · 步骤 ＋ 判据）

> **开跑前**定后端档位（**A 文件型**／**B 检索型**，见 [library-backend.md](references/library-backend.md) §1）；逐步详规见 [retrieval-chain.md](references/retrieval-chain.md) §1–§4。

```
S1 问题拆解  需求 → 28Q 问题域编号 + 关键词（按案查先过案名规范表）→ retrieval-chain.md §1
S2 索引定位  速查表 → 条目编号 → 条目标题目录 → 域/卷文件 + 行号 → retrieval-chain.md §2
S3 定向读取  Read offset/limit 只读命中条目（不整文件读）→ retrieval-chain.md §3
S4 合成输出  汇总 → 写作素材 / 分析结论 / 引用清单（必带编号）→ retrieval-chain.md §4
```

## 检索对象四层（S2 按层取路）

- **主库域条文** `域-族号2位-族内4位` → `方法论调用索引.md` §一速查＋§二全量映射
- **语言专项** W 357／P 442（已外置分卷）→ 索引「附：W/P 系列」
- **行业版** 扁平 `行业方法论_<类名>.md` ＋ 单份细分版 → 按类名直读
- **单案** `单案/通用方法论_投行知识与写作范式_<规范案名>.md` → `state/单案索引对照表.md`
- **两层根**：`{METHODS_ROOT}`＝正文根，`state/` 在上层（工作区根）；全表 [retrieval-chain.md](references/retrieval-chain.md) §7

## 库接入适配（先读配置 · 按档位分派）

> 开放后端（本地目录／Obsidian／乐享／ima 等），配置＝ops 的 `library.config.json`；先读配置再分派。

- **A · 文件型**：索引定位 → 行号定向读（Read/Grep）——token 最优
- **B · 检索型**（连接器）：搜索 → 拉条目全文——无行号，先搜再拉
- 配置缺失 → **冷启动引导档**（不中断）；详规 [library-backend.md](references/library-backend.md) §1–§2

## 依赖与工具

- **工具**：`Read` 定向读（offset/limit）+ `Grep` 关键词搜索——内置、零脚本
- **索引资产**：使用者自建，ops ≥1.5.0 的 `refresh_index.py` 刷新
- **缺失降级三态**：① 索引过期→照常（提示刷新）② 索引缺失→**Grep 全库兜底** ③ 库未建/配置缺失→**冷启动引导档**；详规 [library-backend.md](references/library-backend.md) §2

## 索引资产（定向读取定位）

**方法论调用索引**（28Q 速查＋全量映射）・**条目标题目录**（编号→文件+行号）・**路由入口**・**案名规范表**（证券简称白名单）・**单案索引对照表**（4 位 AN，工作区根 `state/`）——基准 `{METHODS_ROOT}`；全表 [retrieval-chain.md](references/retrieval-chain.md) §8。

## 输出形态（S4 出口）

1. **回复写作素材**：编号 + 规则 + 实证（跨案层 `实证`／单案层 `本案实证`）+ 句式（契约＝ops `entry-contract.md`）
2. **分析结论**：命中汇总 → 覆盖度 + 缺口
3. **引用清单**：编号 + 使用位置对照；案名一律**证券简称**
4. 模板详规 [retrieval-chain.md](references/retrieval-chain.md) §9

## 关键纪律（每条一句话）

- **绝不全文读库**：只走「编号→行号」定向 Read
- **跨体系路由**：主库／单案／语言专项编号**禁止混用**；案号 4 位、不回收不自编
- **案名一律用证券简称**：先过 `方法论_案名规范表.md`
- **分卷读法**：按行号读卷文件，不读主域全文
- **编号是身份**：检索到的编号即引用编号
- **检索失败降级**：无匹配 → Grep 两索引 → 登记待沉淀
- **冷启动不报错**：库未建属首次正常态，走引导档
- 释义 [retrieval-chain.md](references/retrieval-chain.md) §10

## 边界与协作

- **与 ibd-methods-ops 互补**：ops 管生产+维护，本 skill 管消费/检索（同一 `{METHODS_ROOT}`）
- **供 ibd-doc-write 可选调用**：无本 skill 时 write 按内嵌流程运行（功能等价）
- **不承担生产**：缺口只登记待沉淀清单，产出归 ops 蒸馏域
- 分工详规 retrieval-chain.md §11

## 资源索引

- [retrieval-chain.md](references/retrieval-chain.md)：链路逐步详规 ＋ 四层／索引资产／输出形态／关键纪律／边界 全文
- [library-backend.md](references/library-backend.md)：后端接入 A/B 档 ＋ 依赖与降级三态 ＋ 冷启动引导档
- [response-retrieval.md](examples/response-retrieval.md)：反馈回复检索全流程演示
- 外部：ops methods-guide.md／`CHANGELOG.md`

## 维护（何时需要改本 skill）

**五种变化触发器**：库规范变化 ❌（源在 ops）／检索层迁移・链路变化・编号案名变化・新增载体适配 ✅；逐条判别见 [retrieval-chain.md](references/retrieval-chain.md) §12。

# 复核流水线六要素（pipeline.md）

> **这份文档管什么**：一次复核**从文件到报告**的完整链路——每个阶段吃什么、按什么规则判、异常怎么处理、产出什么。
> 与其它册的分工：查什么 → [check-scope.md](check-scope.md)；怎么切 → [chunked-review.md](chunked-review.md)；怎么交付 → [delivery.md](delivery.md)。

---

## 零、唯一入口

```bash
python scripts/review_file.py --input <文件> [--financials <报表.xlsx>] --prepare
python scripts/review_file.py --input <文件> --begin          # 取下一批正文（内部）
python scripts/review_file.py --input <文件> --commit N -f <发现.json>
python scripts/review_file.py --input <文件> --finish         # 合并 → 清单 → 报告
python scripts/check_runlog.py --dir <文件>_复核              # 自证
```

**批次、断点、合并全部内部化**；对外只有"一个文件进、一份报告出"。入口 17 秒左右产出全部中间件。

---

## 一、六要素

| 阶段 | 输入 | 规则 | 判断标准 | 异常处理 | 输出 |
|---|---|---|---|---|---|
| **S1 定分母** | 被复核 docx | 四类归属（正文／表格／单元格／短句），四类之和＝总段 | 五类计数之和 == 总段 | 解析失败 → exit 2，不产半成品 | `paras.json`／`tables.json`／`full.txt`，`_run.json` 记 step=prepare |
| **S2 声明** | 分母 ＋ 批数 | 覆盖默认**全文逐段**；缩范围只能用户发起 | `check_scope_decl.py` 判 PASS | 校验不过 → 报错并列出缺项，不出结果 | `*_scope.md`（五栏：深度／检查／不查／依据来源／交付前将跑） |
| **S3 机器核对** | docx（＋报表 xlsx） | A 域 12 项；C-Q 五式（有报表才跑） | 各项 ERROR/WARN 计数；勾稽 bad 数 | 无报表 → 勾稽 SKIP 并写明原因；未知核对项 → exit 2（不静默零命中） | `format_check.md/.json`、`checks.json`（可选） |
| **S4 逐批通读** | 每批正文 | 六问（数据／表述／逻辑／格式／事实／完整性）；只报有依据的 | 每条须能定位到 `P####`／`TAB###` | 某批读不完 → 不 commit，`--status` 显示未完成 | 每批发现写入状态文件（幂等） |
| **S5 合并** | 全部批发现 | 按**文档序**合并；全局 `F-01…` 连续；同 `(anchor,title)` 去重 | 未完成批存在 → **拒绝合并**（exit 3） | 缺 `title`／`advice` 的条目不进报告并计数回报 | `findings.json`＋`issues.json` |
| **S6 出报告** | `issues.json` ＋ `_run.json` | 按性质分表；封面含复核声明 | 生成器退出码 0；封面有「流程指纹」行 | 缺 `_run.json` → **exit 3 拒绝生成**；缺生成器 → 保留清单并明示 | `<原文>_复核报告.xlsx` |

---

## 二、会中断的地方与现在的处理

| 断点 | 症状 | 处理 |
|---|---|---|
| 分母算错 | 结论必然抽样 | S1 五类守恒自查（之和 == 总段），不通过即报错 |
| 声明单没写 | 覆盖范围不可核 | S2 由编排器自动生成，分母／批数自动填 |
| 忘了跑检查 | 报告"看起来完整" | `_run.json` 无 `check_content` → `check_runlog` 判 FAIL |
| 子进程找不到指纹目录 | 真跑了被判没跑 | `run_checks` 传 `IBD_RUNLOG_DIR`（已修） |
| 半套交付 | 只读了几批就当完成 | S5 有未完成批即 exit 3，且不产出结果文件 |
| 报告要另造清单 | 报告出不来 | S6 由 `--finish` 自动转 `issues.json` 并调生成器 |
| 报告生成器缺指纹 | 无凭证的报告 | 生成器 `exit 3`；`--allow-no-runlog` 可越过但封面标注 |

---

## 五、`--commit` 的发现清单格式

**这是最容易卡住的一步**：`-f` 要一个 JSON 数组，每条至少含下列字段。`--commit` **当场校验**，缺 `title`／`advice`／`anchor` 直接拒收（exit 2），不会拖到 `--finish` 才发现。

| 字段 | 必填 | 写什么 | 例 |
|---|---|---|---|
| `anchor` | ✅ | **原文片段**，报告定位与批注锚点都用它；须能在原文命中 | `"截至本招股说明书签署日，公司不存在或有事项"` |
| `title` | ✅ | 一句话问题标题（≤ 30 字） | `"或有事项称不存在，与第十节诉讼披露矛盾"` |
| `desc` | 建议 | 为什么是问题（含数据/条款依据） | `"第十节列 5 起千万以上未决诉讼…"` |
| `advice` | ✅ | 怎么改（给 `rev` 则可省） | `"改为分项披露未决诉讼、担保与预计负债"` |
| `sev` | 建议 | `高`／`中`／`低` | `"高"` |
| `type` | 建议 | 12 类词表之一 | `"数据不一致"` |
| `nature` | 建议 | 报告分页轴：数据不一致／表述不一致／自身逻辑／格式规范／事实存疑；缺省按 `type` 推 | `"表述不一致"` |
| `code` | 可选 | 域前缀 `J`／`L`／`I`／`Z`，缺省 `J` | `"J"` |
| `line` | 可选 | 段落/表编号，便于回溯 | `"P1778"`、`"TAB254"` |
| `author` | 可选 | 缺省「复核人」 | `"张三"` |

```json
[
  {"anchor": "…原文片段…", "title": "…", "desc": "…", "advice": "…",
   "sev": "高", "type": "数据不一致", "nature": "数据不一致", "line": "P1778"}
]
```

本批无问题就传 `[]`——**必须 commit**，否则该批仍是 pending，`--finish` 会拒绝出结果（exit 3）。

---

## 三、退出码约定

| 码 | 含义 | 下一步 |
|---|---|---|
| 0 | 正常 | — |
| 2 | 参数/输入/校验错误 | 按错误提示修正 |
| 3 | **仍有未完成批** 或 **缺运行指纹** | `--begin` 继续；或按流程重跑 |
| 4 | 报告生成器缺失 | 装 `ibd-doc-annotate`，或直接用 `issues.json` |

---

## 四、一次完整复核的最小命令序列

```bash
F="<被复核文件.docx>"
R="<申报财务报表.xlsx>"      # 可选；给了才做勾稽

python scripts/review_file.py --input "$F" --financials "$R" --prepare
python scripts/review_file.py --input "$F" --begin          # 反复：取批 → 读 → commit
python scripts/review_file.py --input "$F" --finish
python scripts/check_runlog.py --file "$F"                   # 期望 PASS
```

交付物：`<文件>_复核/<原文>_复核报告.xlsx`；`_run.json`／`paras.json` 等为内部件，不交付。

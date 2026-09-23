# 工具链层级与环境踩坑（toolchain.md）

> 本文承接 SKILL.md「依赖与工具」「踩坑与要点」两节的**详规**——**选型／安装／排障**时翻这里。
> **分工**：SKILL.md 留「维度表（🔴必须／🟡推荐／🟢可选）＋ 高频踩坑一句话 ＋ 册指针」；本文装「每个工具为什么是这个层级、缺了会怎样」与「踩坑全文」。
>
> 本文含 2 节：
> 1. 依赖层级说明（安装时读 · 每个工具为什么是这个层级）
> 2. 踩坑与要点（全文）

---

## 一、依赖层级说明（安装时读 · 每个工具为什么是这个层级）

**🔴 必须 · `tencent-docx`〔🟦内置〕 / `minimax-docx`〔🟨官方市场〕（Word 处理，二选一）**
- 用途：套样式（minimax-docx `apply-template`）/ 新建文档（tencent-docx `create`）
- 为什么必须：本 skill 的所有 Word 操作都建立在 Word 处理工具之上；**没有它无法读/写 Word 文档**，只能输出 Markdown + 样式说明

**🔴 必须 · 内置脚本（`check_styles.py` / `check_content.py` / `check_annotations.py` / `check_revisions.py` / `deliver_gate.py`）**
- 用途：样式校验（必备样式/裸段落/空段落/跳级/内容一致）+ 格式核对 14 项（只读）+ 批注产物校验（4 段结构/加粗分布/编号/四件套，只读）+ 修订稿产物校验（ins/del 对/author/id/trackRevisions/落定证明，只读）+ **交付前综合核验九项（一次跑完 · 极简输出，PASS 不展开、FAIL 才给明细）**
- **`check_content.py` 是拆组后的 CLI 入口**：内部按业务域分为 `content_common.py`（共享基础层：Issue / docx 解析 / 中文序号基元 / 标点基元）+ `content_text.py`（文字类 7 项）+ `content_table.py`（表格类 4 项），**三模块须与入口同目录随包分发**（入口内为绝对 import）；对外契约（参数/报告文件名/退出码）与拆组前完全一致
- 为什么必须：随包自带零依赖，校验与核对是本 skill 的核心能力
- 缺了会怎样：不会缺——随包分发，无需额外安装

**🟡 推荐 · `tencent-local-office-edit`**
- 用途：局部样式微调（改单段/单表样式，实时编辑所见即所得）
- 为什么推荐：微调场景体验最佳；没有则用脚本改 document.xml，可用但需注意格式细节

**🟡 推荐 · 模板 docx（`assets/templates/`）**
- 用途：样式源（报告模板 / 反馈回复样式 / 表格模板）——**改模板 = 定制输出样式**
- 为什么推荐：模板是样式体系的可视化载体；没有则只能按 [style-map.md](style-map.md) 文字逐项手工设置，样式落地变繁琐

**🟢 可选 · 外部金融数据终端 / KB_BACKEND**
- 用途：金融数据交叉验证；KB_BACKEND 检索同类范例（知识库/云文档/本地目录任选）
- 为什么可选：格式核对不依赖外部数据；范例检索仅是锦上添花
- 缺了会怎样：**核心功能（样式/核对/校验）完全不受影响**

**🟢 可选 · `officecli`（独立二进制，按需自备）**
- 用途：渲染层物理缺陷扫描（`view issues`：文本溢出/首行缩进缺失/公式错误）+ OpenXML 架构校验（`validate`）；**已挂进 `deliver_gate.py --officecli`**（常驻一行状态：未装则 `[SKIP]` 可见但不阻断）
- 为什么可选：脚本 check_styles.py 查**样式规则应用**（pStyle/裸段落/跳级），officecli 查**渲染与结构层物理缺陷**——规则检查 vs 物理扫描互补，不是替代
- 缺了会怎样：`deliver_gate` 的物理扫描行输出 `[SKIP] 未找到 officecli`（**交付说明据此注明「未跑物理缺陷扫描」**，不再靠人记），核心样式流程不受影响

---

## 二、踩坑与要点（全文）

- **中文文件名编码**：Git Bash 向 Python/minimax CLI 传中文文件名参数可能乱码（zipfile 读 报告模板.docx 曾报 "No such item"）→ 优先用 Python `glob.glob`/`os.listdir` 遍历目录取文件，或复制为临时英文文件名再处理
- **minimax-docx 环境**：restore 必须用 csproj（.slnx 不支持 dotnet 8）；依赖华为云 NuGet 镜像
- **apply-template 语义**：把模板样式套到源文件（保留源内容换样式），不是以模板内容为基底——新建场景用 create，套用场景用 apply-template，勿混淆
- **⚠️ apply-template 只做「组件级替换」、不做段落 pStyle 映射（2026-09-10 实测）**：该命令替换的是 styles/theme/numbering/sectPr 等部件，**段落级样式映射不在其职责内**——套用后 pStyle 分布仍是 `(裸):N`（原来多少还是多少），易被误判为"套样式失败"。段落级映射须**另做一步**：少量走 `tencent-local-office-edit` 手动指定，批量走脚本改 document.xml（插 `w:pStyle` + 清 `w:pPr` 残留直接格式 + 清 run 的 `rPr` 仅留真加粗/上标）。**验收判据**：body 级 pStyle 引用数从 0 变为非 0、必备样式齐备、残留直接格式归零
- **⚠️ 半全角标点属格式核对项，须在「套样式之前」先过 `check_content.py --checks text`（2026-09-10 实测）**：中文语境半角引号 `"`、半角括号 `()` 会被判 HIGH（实测一份 384 处引号一路漏到套样式之后才被主理人补跑抓出）。文字层返工将导致样式重做——**内容定稿后、套样式之前，先跑文字规范核对把标点全角化**，再进入样式落地
- **标点全角化的安全做法（实测）**：引号按**行内出现顺序交替**替换为左/右引号（须先验"含奇数个引号的行的数量 = 0"，即所有引号均在本行/本段内配对）；替换后以「**去掉全部引号字符后的文本 sha256 前后一致**」证明零内容改动。全半角为等宽字符，替换前后字符数与 document.xml 长度均不变
- **--revise 修订稿三坑（2026-08-27 实测，OpenXmlValidator 实证）**：
  1. **元素名是 `w:trackRevisions`，不存在 `w:trackChanges`**——settings.xml 写 trackChanges 是非法元素，Word 静默忽略，修订记录与显示全部失效；合法插入位置为 `w:bordersDoNotSurroundFooter` 之后（25 个位置暴力测试仅此一处过 validator），revisionView 必须带 `w:formatting="1"` 否则打开时格式标记默认隐藏
  2. **pPrChange 快照 pPr 不允许含 `w:rPr`**（CT_PPrGeneral 类型）——真实文档裸段落（有 pPr 无 pStyle）快照时须剔除段落标记 run 属性，否则 Word 视为无效修订节点不显示
  3. **气泡缺失的诊断顺序（排查中尚未定案）**：正常情况下 pPrChange（段落属性/样式更改）应显示「已设置格式」气泡；若审阅窗格有条目但正文无气泡，按序排查：①窗口宽度不足 Word 静默回退嵌入模式（缩放调小/最大化验证）；②修订选项里「更改行」标记是否设为「无」；③用户报告其环境一度全局失去 pPrChange 气泡（含其他历史文档），疑与 Office 更新/全局设置有关——**用「Word 原生生成的格式修订文档」做对照组一锤定音后再归因，勿凭单点现象判定生成缺陷**
- **verify-content 必须段落级拼接对比**：按 `<w:t>` 逐 run 对比会被 merge-runs 破坏对齐而误报「内容被修改」；extract_para_texts 按段落拼接全部 w:t 后再比，与 run 结构无关
- **officecli 实测（2026-09-01，v1.0.146）**：
  1. `view issues` 自动识别 zh-CN locale，会把「正文段落缺首行缩进」报为格式问题（建议缩进 2 字符）——与招股书版 000 正文规则一致，可作补充核对的交叉验证
  2. `create` 生成的空白文档无预置 Heading1 样式（会告警），套样式以本 skill 模板为准，勿依赖 CLI 自带样式
  3. `batch` 批量操作默认原子回滚（v1.0.137+），任一失败整体回滚不落盘——适合正式文档批量修改
  4. 调用方式：`<officecli 安装目录>/officecli.exe`（未入 PATH，按本机安装位置确认）；与 `tencent-local-office-edit` 编辑中的文件勿同时操作（文件锁隔离）

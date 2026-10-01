# QUICKSTART · 先把依赖装齐，再开跑

> **这一页只解决一个问题**：让你**装得齐**。
> ibd-skills 不是 8 个互不相干的工具，而是**一组互相依赖的包**——**只装你要用的那一个，多半跑不起来**。缺的通常是**依赖包**，不是功能。

---

## 0 · 最重要的一张表：你想做的事 → 要装哪些包

| 你想做的事 | **必须装**（🔴 缺则核心功能不可用） | 建议装（🟢 缺则降级，不会断） |
|---|---|---|
| 只做**格式核对 / 套样式** | `ibd-doc-review` | — |
| 只做**交稿前质量校验** | `ibd-quality-gates` | — |
| **写草稿**（反馈回复／章节／备忘录） | `ibd-doc-write` ＋ `ibd-quality-gates` ＋ `ibd-doc-review` | `ibd-methods-ops`（库） |
| **财务复核** | `ibd-finance-review` | `ibd-doc-review`（交付口径）＋ `ibd-doc-annotate`（要批注时）＋ 方法论库 |
| **法律惯例对照** | `ibd-legal-review` ＋ `ibd-doc-review` | 方法论库 |
| **把问题批注进原文** | `ibd-doc-annotate` ＋ `ibd-doc-review` | — |
| **沉淀 / 查方法论** | `ibd-methods-ops` ＋ `ibd-methods-query` | — |

> **三条「零依赖」安全牌**：`ibd-doc-review`、`ibd-quality-gates`、`ibd-methods-ops` —— 这三个**不带任何 🔴 依赖**，装完即可跑。**不确定从哪开始时，先装它们。**

---

## 1 · 三种装法（按需选一种）

**装法 A · 全家桶（推荐）**
下载 Release 的 zip → 解压 → 把 `skills/` 下 **8 个包目录整体**拷进你的技能目录。
→ **一次装齐，永不断链**。不确定要哪个，就用这个。

**装法 B · 只装一条线**
按 §0 表把**该线涉及的包全部取齐**。取包时注意：**依赖包不在同一个目录里，要逐个拷**。

- **写作线**：`doc-write` ＋ `quality-gates` ＋ `doc-review`
- **复核线**：`finance-review`（和／或 `legal-review`）＋ `doc-review` ＋ `doc-annotate`
- **方法论线**：`methods-ops` ＋ `methods-query`

**装法 C · 只装一个试水**
只选 §0 里那三个**零依赖包**之一，装完即可跑。
⚠️ **不要**拿 `doc-write`／`doc-annotate` 试水——它们带 🔴 依赖，单装必断链。

---

## 2 · 装完自检（30 秒，不用翻文档）

- [ ] **目录名 = 包名**（如 `ibd-doc-review`；连字符与大小写都要一致）
- [ ] 每个包目录下有 **`SKILL.md`**（触发面就在它的 description 里）
- [ ] **断链自检**：要用 `doc-write` ⇒ 确认 `ibd-doc-review`、`ibd-quality-gates` 的目录**也在**
- [ ] **环境自测**（纯标准库、零安装，几秒跑完；在解压后的目录里执行）：

```bash
python skills/ibd-quality-gates/scripts/tests/test_check_gates.py
python skills/ibd-doc-review/scripts/tests/test_check_content.py
python skills/ibd-doc-review/scripts/tests/test_deliver_gate.py
```

三组全 OK = 环境可用。

---

## 3 · 技能包之外，还有四类依赖（缺了会怎样，写清楚）

| 类型 | 谁需要 | 怎么装 | 不装会怎样 |
|---|---|---|---|
| **Python 库**（docx／pdf） | `ibd-doc-annotate` | `pip install python-docx lxml pymupdf` | 批注／PDF 相关功能不可用，**其余照常** |
| **Python 库**（PDF 取件） | `ibd-legal-review`（**仅 PDF 路径**） | `pip install pymupdf` | HTML 取件照常；遇 PDF 会**明确提示**，不会静默失败 |
| **平台工具**（docx 处理） | `ibd-doc-review` 的**套样式** | 任一 docx 处理工具或本地 Office | **套样式**不可用，**格式核对**照常 |
| **方法论库**（**要你自己建**） | `ibd-methods-query` ／ `ibd-legal-review`（B 档）／ `ibd-finance-review`（可选） | 用 `ibd-methods-ops` **建库**（首次检索会走冷启动引导） | 检索无结果／惯例对照退 A 档 —— **这是设计内的降级，不是报错** |

> **关于「方法论库」**：库**不随包携带**。内容从哪来（文件／文件夹／项目／已接入的库）、沉淀到哪去（本地目录／Obsidian／云知识库任选）**全由你定**——skill 不绑定任何具体产品。

---

## 4 · 开跑：开场话照抄即可

```
「用 ibd-doc-review 帮我核对这份文档的格式」    → 格式核对（零依赖，最稳）
「交稿前做质量校验」                           → 质量校验（零依赖）
「帮我写 XX 公司的第一轮反馈回复」              → 写作线（需 doc-write 三件套）
「这份招股书财务部分帮我复核」                  → 财务复核
「查一下这段的法律惯例」                        → 法律惯例对照
「把复核问题全部批注进原文」                    → 批注交付
「蒸馏学习这份材料」／「查 XX 问题怎么写」       → 方法论线
```

---

## 5 · 装不上／跑不通：按这 4 步查

| # | 现象 | 先查什么 |
|---|---|---|
| 1 | 报「**找不到包／断链**」 | 回 §0 表，把 🔴 依赖补上 |
| 2 | 报「**缺模块 XXX**」 | 回 §3 表，装对应 Python 库 |
| 3 | **说了话没反应** | 换成该包的**动作词**（各包动作词见其 `SKILL.md`）；确认包确实在技能目录里 |
| 4 | 检索说「**没有对应条目**」 | 先确认：**库建了吗**？**索引路与全文路都跑了吗**？（两路皆空才可称无内容） |

> 仍不通 → 打开该包 `SKILL.md` 的「**依赖与工具**」表，**断链有自助指引**。

---

**下一步**：依赖装齐后，看 [README.md](README.md) 的「工作链路」与「典型场景」建立全局地图；每个包的**触发词／流程／边界**，一律**以包内 `SKILL.md` 为准**。

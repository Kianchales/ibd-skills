# 协作边界与门禁（collaboration.md）

> **本册管什么**：本 skill 与上下游的分工、交付前门禁怎么跑、什么必须向用户点名。
> 与其它册：怎么交付 → [delivery.md](delivery.md)；工具层级 → [toolchain.md](toolchain.md)；接口版本 → [interface.md](interface.md)。


---

## 附 · 入口细则（2026-11-23 自 SKILL.md 迁入，判据不变）

## 边界与协作

- **默认上游 = `ibd-doc-write`**（内容层出草稿并声明样式场景）→ 交本 skill 套样式 ＋ 校验；**上游开放**——人工撰写、其他 AI 流程、外部导入的 Word 均可调用。
- **下游调用点**：`ibd-doc-write` 已把 `deliver_gate.py` 嵌进流程（`--md` 在套样式前做文字预检、`--docx` 作交付前综合核验）⇒ **本脚本改动直接影响写作链**，升版须核 [interface.md](references/interface.md) §7 版本下限。
- **顺序铁律：内容质量门禁在前、格式落地在后**——write 草稿先过 `ibd-quality-gates`，内容定稿再套样式；**文字规范必须先于套样式**（文字层返工会导致样式重做），理由与实测 → workflow.md 附录「两条时序铁律」。
- **交付前一律先跑 `deliver_gate.py`**：**十项基础**一次跑完、只输出结论行；复核产物加 `--annotated`／`--revised`（各 +2 项）、`--officecli`（+1 项物理扫描）；**复核场景须配 `--baseline`**（源件同为 FAIL 的项标〔源件遗留〕不计入结论）。不用分散的多条核验命令替代。
- **输出分层**：三个核验脚本统一「指标行进上下文、明细行落盘」——判据是「明细有没有可定向读的落盘位置」，落盘后原文不得继续占用上下文（ENGINEERING §1 P10＋§4.4）。
- **SKIP 须向用户点名**：`deliver_gate.py` 有 SKIP 项（officecli 未装、pymupdf 缺失等）时，回复须注明「本次 N 项 SKIP 未执行（原因）」——静默跳过与静默失败同罪。
- **批注版链路**：复核产出问题清单 → `ibd-doc-annotate` 注入（依据 annotations.md）→ 本 skill `check_annotations.py` 门禁 → 交付（批注版＋复核报告 Excel；总览 md 不交付）。
- **内容质量归 `ibd-quality-gates`**（数字五要素／反模式／来源可溯）；本 skill 只改格式不改内容（铁律 0）。

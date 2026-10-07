#!/usr/bin/env python3
"""issue_numbering.py — 复核问题清单「编号分配」单一事实源

为什么单独成模块（2026-10-07）：
    编号规则（前缀推导 / 两位序号 / 超 99 条双字母分段）此前在 `annotate_docx.py` 与
    `annotate_pdf.py` **各存一份**（两份逐字重复）；而复核报告（Excel）的「编号」列必须与
    批注**同源同编号**——再抄第三份必然漂移，而「报告编号 ↔ 批注编号 一一对应」是交付契约
    的核心（编号漂移 ＝ 断约）。故抽出本模块，三处共用：
        annotate_docx.py ／ annotate_pdf.py ／ review_report_to_xlsx.py
    本模块**零第三方依赖**（纯标准库），因此不会把 python-docx 传染给只出 Excel 的报告生成器。

编号规则（规则语义见 `ibd-doc-review` skill 的 references/annotations.md §3）：
    - **前缀**：清单 `code` 字段（规范化：仅 A-Z、≤2 位）> ASCII 复核人名首字母 > 回退 `U`（提示）
    - **序号**：同前缀内恒 2 位（01 起）——对齐门禁 `LABEL_PAT` 的 `\\d{2}`；
      本模块只**适配**门禁、不放宽门禁（位数单一事实源在门禁侧）
    - **超 99 条**：顺延双字母分段（J-99 → JA-01…JA-99；单字母前缀容量 26×99＝2574 条）；
      双字母前缀无顺延空间，超 99 条直接报错提示拆分清单
      （静默改写显式前缀 ＝ 编号漂移，禁）
    - **顺序** ＝ 清单顺序（不重排）

脚本/模块不内置任何人名、代号映射——前缀语义由复核流程自定义，人名↔代号对应关系是
**上游清单的内容**，方法层只认结构。

被引用方（import）：
    from issue_numbering import assign_numbers          # 注入器：就地补 full 字段
    from issue_numbering import derive_code, full_label # 报告生成器：只算号、不改清单

退出码：本模块无 CLI（纯函数库）。
"""
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def derive_code(it):
    """编号前缀推导：清单 `code` 字段 > ASCII 复核人名首字母 > 回退 `U`（并提示补 code）。

    前缀语义由复核流程自定义（如 J=财务复核人），本模块不内置任何团队映射——
    方法层只认结构，人名/代号对应关系是上游清单的内容。
    """
    code = str(it.get("code") or "").strip().upper()
    code = "".join(ch for ch in code if ch.isascii() and ch.isalpha())[:2]  # 规范化：仅 A-Z、≤2 位（对齐门禁 LABEL_PAT）
    if code:
        return code
    author = str(it.get("author") or "").strip()
    if author and author[0].isascii() and author[0].isalpha():
        return author[0].upper()
    print(f"[warn] 编号前缀回退 U：author「{author}」非拉丁名且清单未提供 code 字段"
          f"（建议每条加 \"code\": \"J\" 等，规范见 ibd-doc-review references/annotations.md §3）",
          file=sys.stderr)
    return "U"


def full_label(code, n):
    """前缀-序号合成：序号恒 2 位（对齐门禁 `LABEL_PAT` 的 `\\d{2}`，位数单一事实源在门禁侧，
    本函数只适配、不放宽门禁）。同前缀超 99 条顺延双字母分段（J-99 → JA-01…JA-99，
    单字母前缀容量 26×99）；双字母前缀无顺延空间，超 99 条直接报错提示拆分清单——
    静默改写显式前缀＝编号漂移，禁。
    """
    seg, k = divmod(n - 1, 99)
    if seg == 0:
        return f"{code}-{k + 1:02d}"
    if len(code) >= 2:
        raise ValueError(f"编号前缀 {code} 为双字母，超 99 条无法分段顺延（第 {n} 条）"
                         f"——请拆分清单或改用单字母前缀")
    if seg > 26:
        raise ValueError(f"编号前缀 {code} 分段容量穷尽（27×99=2673 条）——请拆分清单")
    return f"{code}{chr(ord('A') + seg - 1)}-{k + 1:02d}"


def assign_numbers(issues):
    """就地分配编号 + 结构校验（方法层只查结构必填，不做内容判断）。

    类型/严重度词表归 `ibd-doc-review` references/annotations.md §4 定义，本模块不校验词表、
    不维护词表副本（复核分类属上游清单内容）；type/sev 缺省仅以「-」作显示兜底。

    写入字段：`full`（合成编号，如 `J-01`）；并补 `type`/`sev` 的显示兜底。
    """
    seen = {}
    for it in issues:
        for f in ("author", "anchor", "title"):
            if not str(it.get(f) or "").strip():
                raise ValueError(f"条目缺必填字段 {f}: {json.dumps(it, ensure_ascii=False)[:100]}")
        code = derive_code(it)
        seen[code] = seen.get(code, 0) + 1
        it["full"] = full_label(code, seen[code])
        it["type"] = it.get("type") or "-"
        it["sev"] = it.get("sev") or "-"
    return issues

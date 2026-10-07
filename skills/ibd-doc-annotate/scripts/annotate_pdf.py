#!/usr/bin/env python3
"""
ibd-doc-annotate · annotate_pdf.py — 在 PDF 原文上注入复核批注（高亮 + 弹注）

用法:
  python annotate_pdf.py --pdf <原文.pdf> --issues <issues.json> [--pages 5-6] [--out <输出.pdf>]

issues.json（与 annotate_docx.py 同构；可选 "page": 页码(1 起)，限定搜索页）:
{
  "author": "张敏", "code": "J", "type": "数据·正负号", "sev": "高",
  "anchor": "公司因结算货币汇率波动产生的汇兑净损失为…",
  "title": "…", "desc": "…", "advice": "…"
}

行为:
  - 编号自动分配（编号前缀 code + 两位序号，如 J-01；同前缀超 99 条顺延双字母分段
    J-99 → JA-01…，序号恒 2 位对齐门禁 LABEL_PAT），顺序 = 清单顺序
  - 定位：rawdict 字符级匹配（容忍空格/换行/数字单位间断字）→ 高亮 + 弹注（hover 查看）
  - 弹注正文 4 行紧凑（纯文本无加粗，行间 \n）：标签行 / 标题行 / 问题描述… / 建议…
  - --pages "5-6"：仅抽取该页范围（演示/节选场景）；缺省保留全文
  - 输出：<原文名>_批注版.pdf（或 --out）+ <输出>_批注总览.md
    （总览**恒只产 md**、为**中间件**——不交付用户；人读报告 = 复核报告 Excel，
     由 review_report_to_xlsx.py 生成）
  - 找不到锚点的条目计入总览「未锚定」，不报错中断

依赖：pymupdf
格式单一事实源：ibd-doc-review skill references/annotations.md（本脚本只实现、不另立规则）。
"""
import argparse
import datetime
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# 编号分配（前缀推导 / 两位序号 / 超 99 条双字母分段）＝ issue_numbering.py 单一事实源，
# 与 annotate_docx.py、review_report_to_xlsx.py 三处共用（2026-10-07 抽出——此前两脚本各存一份）。
# 勿在本文件重建副本：「报告编号 ↔ 批注编号 一一对应」是交付契约核心，副本漂移即断约。
from issue_numbering import assign_numbers


WS = set(" \t\n\r\u3000\u00a0")


def locate(doc, page_idx, phrase):
    """字符级匹配（容忍空白），返回高亮矩形列表。"""
    import pymupdf
    page = doc[page_idx]
    raw = page.get_text("rawdict")
    chars = []
    for block in raw["blocks"]:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                chars.extend(span["chars"])
    text, rects = [], []
    for c in chars:
        if c["c"] in WS:
            continue
        text.append(c["c"])
        rects.append(pymupdf.Rect(c["bbox"]))
    text = "".join(text)
    p = phrase.replace(" ", "").replace("\u3000", "").replace("\n", "").replace("\r", "")
    hits = []
    start = 0
    while True:
        i = text.find(p, start)
        if i < 0:
            break
        r = pymupdf.Rect(rects[i])
        for j in range(i + 1, i + len(p)):
            r |= rects[j]
        hits.append(pymupdf.Rect(r.x0 - 1, r.y0, r.x1 + 1, r.y1))
        start = i + 1
    return hits


def content_of(it):
    return (f"【{it['full']}｜{it['type']}｜{it['sev']}】\n"
            f"{it['title']}\n"
            f"问题描述：{it['desc']}\n"
            f"建议：{it['advice']}")


def write_overview(out_pdf, issues, misses):
    base = os.path.splitext(out_pdf)[0]
    out = base + "_批注总览.md"
    lines = ["# 复核批注总览", "",
             f"> 批注版：`{os.path.basename(out_pdf)}`（阅读器 hover 高亮处查看弹注）",
             "> 本总览与批注编号一一对应，为**中间件**（不交付用户；人读报告＝复核报告 Excel）；未自动锚定条目仅在下方列出。", "",
             "| 编号 | 类型·严重度 | 锚点摘要 | 作者 | 状态 |",
             "|---|---|---|---|---|"]
    miss_full = {m["full"] for m in misses}
    for it in issues:
        status = "已锚定" if it["full"] not in miss_full else "未锚定 → 见下"
        anchor = it["anchor"] if len(it["anchor"]) <= 40 else it["anchor"][:40] + "…"
        lines.append(f"| {it['full']} | {it['type']}·{it['sev']} | {anchor} | {it['author']} | {status} |")
    if misses:
        lines += ["", "## 未自动锚定条目（人工定位）", ""]
        for m in misses:
            lines.append(f"- **{m['full']}**（{m['author']}）：{m['reason']}")
            lines.append(f"  - 锚点：{m['anchor']}")
            lines.append(f"  - 问题：{m['title']}")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return out


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    ap = argparse.ArgumentParser(description="PDF 原文批注注入（规范：ibd-doc-review references/annotations.md）")
    ap.add_argument("--pdf", required=True, help="原文 PDF 路径")
    ap.add_argument("--issues", required=True, help="复核问题清单 JSON（数组，可带 page 1 起）")
    ap.add_argument("--pages", help='仅保留页范围，如 "5-6"（节选场景）；缺省保留全文')
    ap.add_argument("--out", help="输出 PDF 路径（默认 <原文名>_批注版.pdf）")
    ap.add_argument("--date", default="", help="ISO8601 批注日期（默认当前 UTC）")
    args = ap.parse_args()

    import pymupdf

    with open(args.issues, encoding="utf-8") as fh:
        raw = json.load(fh)
    # G1 入口校验（复核链数据入口早拦）：errors 非空即退出不注入；warnings 仅提示
    from validate_issues import validate_issues
    _errs, _warns = validate_issues(raw)
    for _w in _warns:
        print(f"[WARN] {_w}")
    if _errs:
        print(f"[ERROR] issues 清单未通过入口校验（{len(_errs)} 项）——不注入，请修正后重试：")
        for _e in _errs:
            print(f"  - {_e}")
        sys.exit(2)
    try:
        issues = assign_numbers([dict(x) for x in raw])
    except ValueError as exc:
        print(f"[ERROR] 编号分配失败：{exc}")
        sys.exit(2)
    date_iso = args.date or _now_iso()
    out_pdf = args.out or os.path.splitext(args.pdf)[0] + "_批注版.pdf"

    doc = pymupdf.open(args.pdf)
    page_range = range(doc.page_count)
    if args.pages:
        a, b = (int(x) for x in args.pages.split("-"))
        page_range = range(a - 1, b)

    misses = []
    for it in issues:
        it["anchor_clean"] = it["anchor"].replace(" ", "").replace("\u3000", "")
        target_pages = [it["page"] - 1] if it.get("page") else list(page_range)
        hit = None
        for pno in target_pages:
            if not (0 <= pno < doc.page_count):
                continue
            rects = locate(doc, pno, it["anchor"])
            if rects:
                hit = (pno, rects[0])
                break
        if not hit:
            misses.append(it)
            print(f"[MISS] {it['full']} {it['author']}：锚点未定位（含空白容错）")
            continue
        pno, r = hit
        page = doc[pno]  # 须持有 page 引用（内联 doc[pno] 代理被 GC 会报 annotation not bound）
        annot = page.add_highlight_annot(r)
        now = pymupdf.get_pdf_now()
        annot.set_info(info={"author": it["author"], "title": it["full"], "content": content_of(it),
                             "creationDate": now, "modDate": now, "subject": "复核批注"})
        annot.update()
        print(f"[OK] p{pno+1} {it['full']} {it['author']}：{it['anchor'][:24]}…")

    if args.pages:
        out = pymupdf.open()
        out.insert_pdf(doc, from_page=page_range[0], to_page=page_range[-1])
        out.save(out_pdf, garbage=3, deflate=True)
        out.close()
    else:
        doc.save(out_pdf, garbage=3, deflate=True)
    doc.close()
    overview = write_overview(out_pdf, issues, misses)
    print("saved:", out_pdf)
    # 总览**恒只产 md**（中间件，不交付用户）——2026-10-07 撤除 Word 版链路与 --overview-docx 开关；
    # 人读报告改由 review_report_to_xlsx.py 出 Excel 复核报告（规格 ibd-doc-review delivery.md §八之二）。
    print("overview:", overview)
    print(f"未锚定 {len(misses)} 条（详见总览）" if misses else "全部锚定 ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ibd-doc-annotate · revise_docx.py — 复核结论修订稿执行器（Word 修订模式 / 直接改好 / 双版）

用法:
  python revise_docx.py --docx <原文.docx> --issues <issues.json> [--mode revise|clean|both] [--out <输出.docx>]

issues.json（数组，在批注清单字段基础上增加 rev）:
{
  "author": "张敏",            // 复核人姓名；编号前缀可另给 "code": "J"（缺省 ASCII 名取首字母，中文名建议提供，否则回退 U）
  "type":   "数据·正负号",        // 类型词表见 ibd-doc-review references/annotations.md §4（本脚本不校验）
  "sev":    "高",                 // 严重度（同词表；不校验）
  "anchor": "公司因结算货币汇率波动产生的汇兑净损失为…",  // 原文待改句段（精确子串 = 替换范围）
  "rev":    "公司因结算货币汇率波动产生的汇兑损益为…",    // ★ 替换后新文本（anchor 精确覆盖要改范围）
  "title":  "……", "desc": "……", "advice": "……"         // 展示/清单用
}
- 缺 rev 或 rev 为空 → 该条**待人工**（不自动改，列修改清单）
- anchor 既是定位串也是替换范围：须精确等于要改的原文片段

--mode:
  revise —— Word 修订模式：原文本包 w:del（w:delText），新文本包 w:ins（author=复核人），
            并开启 trackRevisions；Word/WPS 审阅面板逐条查看、可接受/拒绝（默认）
  clean  —— 直接改好：原文本替换为新文本，输出干净修订稿（无修订标记）
  both   —— 同时输出 revise 版 + 接受全部修订后的 clean 版（_clean.docx）

输出:
  <原文名>_修订稿.docx（revise/both）与 <原文名>_修订稿_clean.docx（clean/both）
  <原文名>_修订稿_修改清单.md（已修订 N 条 / 待人工 M 条，编号与批注/总览同一体系）

边界:
  - 锚点覆盖复杂 run（换行 w:br / 制表 w:tab / 多 w:t）或锚点区间夹非 run 元素（超链接等）
    → 不自动改，记入修改清单「待人工」
  - 同段多锚点不重叠则按倒序应用（坐标稳定）；重叠 → 后者待人工
  - 只改问题清单指定的 anchor 区间，原文其余文字零改动

依赖：python-docx + lxml；复用 annotate_docx 的编号/遍历/复杂 run 判定。
格式规范单一事实源：ibd-doc-review skill references/revisions.md（本脚本只实现、不另立规则）。
"""
import argparse
import copy
import datetime
import json
import os
import re
import sys
import zipfile

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

import annotate_docx as A

W = A.W
XML_SPACE = A.XML_SPACE


def _now_iso():
    return A._now_iso()


# ---------------- 定位：返回 (p_el, s, e) 或 None ----------------
def locate_span(doc, anchor):
    """正文/表格段落中定位 anchor 精确子串，返回 (p_el, s, e)；找不到返回 None。"""
    if not anchor:
        return None
    for p_el in A._walk_paras(doc.element.body):
        text = A.para_text_of_runs(p_el)
        s = text.find(anchor)
        if s >= 0:
            return p_el, s, s + len(anchor)
    return None


def _precheck_span(p_el, s, e):
    """锚点区间内 run 必须全 simple；区间内不得夹非 run 顶层元素。返回 (ok, reason)。"""
    runs = [r for r in p_el if r.tag == qn('w:r')]
    texts = []
    for r in runs:
        texts.append("".join(t.text or "" for t in r.findall(qn('w:t'))))
    cum, acc = [], 0
    for t in texts:
        cum.append(acc)
        acc += len(t)
    lo = hi = None
    for i, base in enumerate(cum):
        end = base + len(texts[i])
        if base <= s < end:
            lo = i
        if base < e <= end:
            hi = i
    if lo is None or hi is None:
        return False, "锚点未完整落在 run 文本内（可能骑跨超链接等）"
    for i in range(lo, hi + 1):
        if not A._run_simple(runs[i]):
            return False, "锚点覆盖复杂 run（换行/制表/多文本段），不自动修订"
    # 区间内（lo..hi 之间）不允许夹非 run 顶层节点（如 hyperlink/bookmark/绘图）
    order = [c for c in p_el if c.tag != qn('w:pPr')]
    idx = [i for i, c in enumerate(order) if c is runs[lo]]
    if not idx:
        return False, "段落结构异常"
    start_at = idx[0]
    for c in order[start_at:]:
        if c is runs[hi]:
            break
        if c.tag != qn('w:r'):
            return False, "锚点区间夹非 run 元素（超链接等），不自动修订"
    return True, ""


# ---------------- 段落重建（三模式落定） ----------------
def rebuild_paragraph(p_el, s, e, rev, author, date, rid, mode):
    """
    把段落 p_el 中 [s,e) 文本替换为 rev。
    mode: revise（原文本聚合为 w:del（w:delText），其后插 w:ins（rev 文本））
        | clean（丢弃原文本，原位插入 rev run）
    锚点外 run 与全部非 run 顶层节点原样保留顺序；仅锚点区间内 run 被消费。
    """
    pPr = p_el.find(qn('w:pPr'))
    children = [c for c in p_el if c.tag != qn('w:pPr')]
    runs = [c for c in children if c.tag == qn('w:r')]
    text_of, cum = {}, {}
    acc = 0
    for r in runs:
        t = "".join(x.text or "" for x in r.findall(qn('w:t')))
        text_of[id(r)] = t
        cum[id(r)] = acc
        acc += len(t)

    events = []  # ('keep', el) | ('pre', run, txt) | ('mid', run, txt) | ('post', run, txt)
    first_ref = None
    for c in children:
        if c.tag != qn('w:r'):
            events.append(('keep', c))
            continue
        base = cum[id(c)]
        end = base + len(text_of[id(c)])
        if end <= s or base >= e:
            events.append(('keep', c))
            continue
        a = max(base, s) - base
        b = min(end, e) - base
        pre, mid, post = text_of[id(c)][:a], text_of[id(c)][a:b], text_of[id(c)][b:]
        if pre:
            events.append(('pre', c, pre))
        if mid:
            if first_ref is None:
                first_ref = c
            events.append(('mid', c, mid))
        if post:
            events.append(('post', c, post))

    out = []
    del_node = None   # revise：聚合原文本的 w:del
    ins_done = False  # clean：rev run 是否已插
    for ev in events:
        k = ev[0]
        if k == 'mid':
            if mode == 'revise':
                if del_node is None:
                    del_node = OxmlElement('w:del')
                    del_node.set(qn('w:id'), str(rid))
                    del_node.set(qn('w:author'), author)
                    del_node.set(qn('w:date'), date)
                    out.append(del_node)
                    ir = OxmlElement('w:ins')
                    ir.set(qn('w:id'), str(rid))
                    ir.set(qn('w:author'), author)
                    ir.set(qn('w:date'), date)
                    ir.append(_new_run(rev, first_ref))
                    out.append(ir)
                del_node.append(_run_of(ev[1], ev[2], deltext=True))
            else:  # clean
                if not ins_done:
                    out.append(_new_run(rev, first_ref))
                    ins_done = True
        elif k == 'keep':
            out.append(ev[1])
        else:  # pre / post
            out.append(_emit_run(ev[1], ev[2]))

    for c in list(p_el):
        p_el.remove(c)
    if pPr is not None:
        p_el.append(pPr)
    for c in out:
        p_el.append(c)


def _emit_run(run, text):
    """复用 run 元素生成片段（保留 rPr，替换文本为 text）。"""
    el = copy.deepcopy(run)
    for t in el.findall(qn('w:t')):
        el.remove(t)
    t = OxmlElement('w:t')
    t.text = text
    t.set(XML_SPACE, 'preserve')
    el.append(t)
    return el


def _run_of(run, text, deltext=False):
    """基于原 run 生成 delText run（保留 rPr）。"""
    el = copy.deepcopy(run)
    for t in el.findall(qn('w:t')):
        el.remove(t)
    tag = 'w:delText' if deltext else 'w:t'
    t = OxmlElement(tag)
    t.text = text
    t.set(XML_SPACE, 'preserve')
    el.append(t)
    return el


def _new_run(text, ref_run):
    """新文本 run：rPr 继承 ref_run（若有），文本 = rev。"""
    r = OxmlElement('w:r')
    rpr = ref_run.find(qn('w:rPr'))
    if rpr is not None:
        r.append(copy.deepcopy(rpr))
    t = OxmlElement('w:t')
    t.text = text
    t.set(XML_SPACE, 'preserve')
    r.append(t)
    return r


# ---------------- settings.xml 开修订（实证插入法，同 check_styles --revise） ----------------
def patch_settings(xml_bytes):
    root = xml_bytes.decode("utf-8")
    rv = ('<w:revisionView w:markup="1" w:comments="1" w:insDel="1"'
          ' w:formatting="1" w:inkAnnotations="1"/>')
    block = ""
    if "<w:revisionView" not in root:
        block += rv
    if "<w:trackRevisions" not in root:
        block += "<w:trackRevisions/>"
    if not block:
        return xml_bytes
    m = re.search(r"<w:bordersDoNotSurroundFooter\b[^>]*/>", root) or \
        re.search(r"<w:bordersDoNotSurroundFooter\b[^>]*>.*?</w:bordersDoNotSurroundFooter>", root, re.S)
    if m:
        root = root[: m.end()] + block + root[m.end():]
    else:
        root = root.replace("</w:settings>", block + "</w:settings>", 1)
    return root.encode("utf-8")


# ---------------- 修改清单 md ----------------
def write_manifest(out_docx, done, pending, mode):
    base = os.path.splitext(out_docx)[0]
    out = base + "_修改清单.md"
    mode_desc = {
        "revise": "Word 修订模式：每条改动作者 = 复核人，Word/WPS 审阅面板可逐条接受/拒绝",
        "clean": "直接改好：改动已落定，本清单为对照（编号 ↔ 原文 ↔ 改为）",
        "both": "双版本：修订模式稿（可审阅）+ 接受全部修订后的干净版",
    }[mode]
    lines = ["# 复核修订稿 · 修改清单", "",
             f"> 修订稿：`{os.path.basename(out_docx)}`（{mode_desc}）",
             "> 编号与批注/复核总览同一体系（同源问题清单时一一对应）。", ""]
    lines += [f"## 已修订 {len(done)} 条", "",
              "| 编号 | 类型·严重度 | 作者 | 原文 → 改为 |",
              "|---|---|---|---|"]
    for it in done:
        o = it["anchor"] if len(it["anchor"]) <= 30 else it["anchor"][:30] + "…"
        r = it.get("rev", "")
        r = r if len(r) <= 30 else r[:30] + "…"
        lines.append(f"| {it['full']} | {it['type']}·{it['sev']} | {it['author']} | {o} → {r} |")
    lines += ["", f"## 待人工 {len(pending)} 条（未自动修订）", ""]
    if pending:
        lines += ["| 编号 | 类型·严重度 | 作者 | 原因 | 建议 |",
                  "|---|---|---|---|---|"]
        for it in pending:
            reason = it.get("_pending", "未提供 rev 替换文本")
            advice = it.get("advice", "")
            advice = advice if len(advice) <= 60 else advice[:60] + "…"
            lines.append(f"| {it.get('full','-')} | {it.get('type','-')}·{it.get('sev','-')} | {it.get('author','-')} | {reason} | {advice} |")
    else:
        lines.append("（无）")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return out


# ---------------- 主流程 ----------------
def run(docx_path, issues, mode, out_docx, date_iso):
    doc = Document(docx_path)
    auto, pending = [], []
    # 定位 + 分类
    plans = []  # (p_el, s, e, issue)
    for it in issues:
        if not it.get("rev"):
            it["_pending"] = "未提供 rev 替换文本（需人工拟稿）"
            pending.append(it)
            continue
        if it["rev"] == it["anchor"]:
            it["_pending"] = "rev 与 anchor 相同（无实际改动）"
            pending.append(it)
            continue
        hit = locate_span(doc, it["anchor"])
        if hit is None:
            it["_pending"] = "正文/表格未找到锚点文本"
            pending.append(it)
            continue
        p_el, s, e = hit
        ok, reason = _precheck_span(p_el, s, e)
        if not ok:
            it["_pending"] = reason
            pending.append(it)
            continue
        plans.append((p_el, s, e, it))
        auto.append(it)
    # 同段锚点按位置倒序应用（先改段尾，前面坐标不受影响）；重叠 → 靠前条待人工
    by_para = {}
    for p_el, s, e, it in plans:
        by_para.setdefault(id(p_el), []).append((s, e, it, p_el))
    rid = 0
    for key, lst in by_para.items():
        lst.sort(key=lambda x: x[0], reverse=True)
        last_e = None
        for s, e, it, p_el in lst:
            if last_e is not None and s < last_e:
                it["_pending"] = "与同段另一锚点重叠，需人工合并处理"
                pending.append(it)
                auto.remove(it)
                continue
            last_e = e
            rid += 1
            rebuild_paragraph(p_el, s, e, it["rev"], it["author"], date_iso, rid, mode)
    # 保存并（revise）补 settings
    if mode in ("revise", "both"):
        tmp = out_docx + ".tmp"
        doc.save(tmp)
        with zipfile.ZipFile(tmp, "r") as z:
            items = {n: z.read(n) for n in z.namelist()}
        if "word/settings.xml" in items:
            items["word/settings.xml"] = patch_settings(items["word/settings.xml"])
        with zipfile.ZipFile(out_docx, "w", zipfile.ZIP_DEFLATED) as z:
            for n, data in items.items():
                z.writestr(n, data)
        os.remove(tmp)
    else:
        doc.save(out_docx)
    manifest = write_manifest(out_docx, auto, pending, mode)
    for it in auto:
        print(f"[OK] {it['full']} {it['author']}：{it['anchor'][:22]}… → {it['rev'][:22]}…")
    for it in pending:
        print(f"[PEND] {it.get('full','-')} {it.get('author','-')}：{it.get('_pending','')}")
    print("saved:", out_docx)
    print("manifest:", manifest)
    print(f"已修订 {len(auto)} 条，待人工 {len(pending)} 条")
    return auto, pending


def main():
    ap = argparse.ArgumentParser(description="复核修订稿执行器（规范：ibd-doc-review references/revisions.md）")
    ap.add_argument("--docx", required=True, help="原文 docx 路径")
    ap.add_argument("--issues", required=True, help="复核问题清单 JSON（数组，含 rev 替换文本）")
    ap.add_argument("--mode", default="revise", choices=["revise", "clean", "both"],
                    help="revise=Word 修订模式（默认）| clean=直接改好 | both=双版")
    ap.add_argument("--out", help="输出 docx 路径（默认 <原文名>_修订稿.docx）")
    args = ap.parse_args()

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
    issues = A.assign_numbers([dict(x) for x in raw])
    out_docx = args.out or os.path.splitext(args.docx)[0] + "_修订稿.docx"
    date_iso = _now_iso()

    if args.mode == "clean":
        auto, pending = run(args.docx, issues, "clean", out_docx, date_iso)
    elif args.mode == "both":
        auto, pending = run(args.docx, issues, "revise", out_docx, date_iso)
        clean_out = os.path.splitext(out_docx)[0] + "_clean.docx"
        issues2 = A.assign_numbers([dict(x) for x in json.load(open(args.issues, encoding="utf-8"))])
        _a, _p = run(args.docx, issues2, "clean", clean_out, date_iso)
        print("clean version:", clean_out)
    else:  # revise（默认）
        auto, pending = run(args.docx, issues, "revise", out_docx, date_iso)
    return 0


if __name__ == "__main__":
    sys.exit(main())

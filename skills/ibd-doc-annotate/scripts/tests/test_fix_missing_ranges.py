#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_fix_missing_ranges.py — fix_missing_ranges.py 自测（最小测试集）

背景：同段落多批注时，主脚本逐条注入会让后续批注的段落重建抹掉先前已插的
commentRangeStart/End，导致 comments.xml 有批注而 document.xml 丢 range
（check_annotations 报 cs/ce/ref 对数不齐）。fix_missing_ranges.py 是补插后处理。

覆盖（每条都断言「标记顺序 start→end→ref」+「range 覆盖文本 == 锚点」+「段落文本零改动」）：
  1. 单段单 run，锚点在 run 内部
  2. 单段单 run，锚点到 run 末尾
  3. 单段单 run，锚点覆盖整个 run（run 与锚点完全对齐）
  4. 多 run 段落，锚点跨 run
  5. 锚点位于段落起始处
  6. 同段落两条批注（不同锚点），两条 range 均正确成对且顺序合法
  7. 锚点未命中 → 提示 anchor not found，不硬插、不改文档
  8. 幂等：补完再跑一次 → missing 为空、fixed 0/0

依赖：python-docx（本包 docx 链路的声明依赖）——未安装则整类 SKIP。
运行：python scripts/tests/test_fix_missing_ranges.py
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

SKILL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPT = os.path.join(SKILL_DIR, "scripts", "fix_missing_ranges.py")

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_W = f'xmlns:w="{W}"'
CT_COMMENTS = ("application/vnd.openxmlformats-officedocument.wordprocessingml."
               "comments+xml")
REL_COMMENTS = ("http://schemas.openxmlformats.org/officeDocument/2006/"
                "relationships/comments")

try:
    from docx import Document
    HAS_DOCX = True
except ImportError:  # pragma: no cover
    HAS_DOCX = False


def _qt(tag):
    return f"{{{W}}}{tag}"


# ---------------------------------------------------------------- fixture ----

def comments_xml(n, author="张敏"):
    """comments.xml：n 条批注，w:id 依次 0..n-1（须与 issues 数组下标一致）"""
    parts = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
             f"<w:comments {NS_W}>"]
    for i in range(n):
        parts.append(
            f'<w:comment w:id="{i}" w:author="{author}" '
            f'w:date="2026-09-14T00:00:00Z" w:initials="ZM">'
            f"<w:p><w:r><w:t>批注正文 {i}</w:t></w:r></w:p></w:comment>")
    parts.append("</w:comments>")
    return "".join(parts)


def _inject_comments(path, n):
    """给 docx 补 comments 部件（python-docx 不生成批注，故直接改包）"""
    with zipfile.ZipFile(path) as z:
        items = {i.filename: z.read(i.filename) for i in z.infolist()}
    ct = items["[Content_Types].xml"].decode("utf-8").replace(
        "</Types>",
        f'<Override PartName="/word/comments.xml" ContentType="{CT_COMMENTS}"/></Types>')
    rels = items["word/_rels/document.xml.rels"].decode("utf-8").replace(
        "</Relationships>",
        f'<Relationship Id="rIdComments" Type="{REL_COMMENTS}" '
        f'Target="comments.xml"/></Relationships>')
    items["[Content_Types].xml"] = ct.encode("utf-8")
    items["word/_rels/document.xml.rels"] = rels.encode("utf-8")
    items["word/comments.xml"] = comments_xml(n).encode("utf-8")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, blob in items.items():
            z.writestr(name, blob)


def build_docx(paragraph_runs):
    """paragraph_runs = [[run文本, ...], ...]；返回临时 docx 路径"""
    doc = Document()
    for runs in paragraph_runs:
        p = doc.add_paragraph()
        for t in runs:
            p.add_run(t)
    fd, path = tempfile.mkstemp(suffix=".docx")
    os.close(fd)
    doc.save(path)
    return path


def run_fix(docx_path, issues):
    ip = docx_path.replace(".docx", ".issues.json")
    with io.open(ip, "w", encoding="utf-8") as f:
        json.dump([{"anchor": a} for a in issues], f, ensure_ascii=False)
    p = subprocess.run([sys.executable, SCRIPT, docx_path, ip],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


# ---------------------------------------------------------------- 读取侧 ----

def _paras(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml")
    body = ET.fromstring(xml).find(_qt("body"))
    return body.findall(_qt("p"))


def _tokens(p):
    """段落内有序 token：('start'|'end'|'ref', id) / ('t', 文本)"""
    toks = []
    for el in p.iter():
        tag = el.tag.split("}")[-1]
        if tag == "commentRangeStart":
            toks.append(("start", el.get(_qt("id"))))
        elif tag == "commentRangeEnd":
            toks.append(("end", el.get(_qt("id"))))
        elif tag == "commentReference":
            toks.append(("ref", el.get(_qt("id"))))
        elif tag == "t":
            toks.append(("t", el.text or ""))
    return toks


def _marker_seq(toks, cid):
    cid = str(cid)
    return [k for k, v in toks if k in ("start", "end", "ref") and v == cid]


def _ranged_text(toks, cid):
    """start..end 之间的文本（应 == 锚点）"""
    cid = str(cid)
    out, on = [], False
    for k, v in toks:
        if k == "start" and v == cid:
            on = True
            continue
        if k == "end" and v == cid:
            on = False
            continue
        if k == "t" and on:
            out.append(v)
    return "".join(out)


def _full_text(toks):
    return "".join(v for k, v in toks if k == "t")


@unittest.skipUnless(HAS_DOCX, "需要 python-docx（本包 docx 链路声明依赖）")
class TestFixMissingRanges(unittest.TestCase):

    def setUp(self):
        self._d = tempfile.TemporaryDirectory()
        self.addCleanup(self._d.cleanup)

    def tmp(self, name="t.docx"):
        return os.path.join(self._d.name, name)

    # ------------------------------------------------------------ 通用断言 ----

    def assert_range_ok(self, path, idx, cid, anchor, expect_text):
        """三重断言：标记顺序 / 覆盖区间文本 == 锚点 / 段落文本零改动"""
        toks = _tokens(_paras(path)[idx])
        self.assertEqual(_marker_seq(toks, cid), ["start", "end", "ref"],
                         f"段{idx} 批注 {cid} 标记顺序异常: {_marker_seq(toks, cid)}")
        self.assertEqual(_ranged_text(toks, cid), anchor,
                         f"段{idx} 批注 {cid} 覆盖区间与锚点不符")
        self.assertEqual(_full_text(toks), expect_text,
                         f"段{idx} 段落文本被改动")

    # -------------------------------------------------------------- 用例 ----

    def test_01_single_run_anchor_inside(self):
        runs = [["报告期内公司汇兑净损失为-26.14万元，同比上升。"]]
        anchor = "汇兑净损失为-26.14万元"
        f = build_docx(runs)
        _inject_comments(f, 1)
        rc, out = run_fix(f, [anchor])
        self.assertEqual(rc, 0, out)
        self.assertIn("fixed 1/1", out)
        self.assert_range_ok(f, 0, 0, anchor, "".join(runs[0]))

    def test_02_single_run_anchor_to_run_end(self):
        runs = [["发行人主营业务毛利率为32.15%"]]
        anchor = "毛利率为32.15%"
        f = build_docx(runs)
        _inject_comments(f, 1)
        rc, out = run_fix(f, [anchor])
        self.assertEqual(rc, 0, out)
        self.assertIn("fixed 1/1", out)
        self.assert_range_ok(f, 0, 0, anchor, "".join(runs[0]))

    def test_03_anchor_covers_whole_run(self):
        runs = [["发行人", "主营业务毛利率为32.15%", "，高于同业。"]]
        anchor = "主营业务毛利率为32.15%"
        f = build_docx(runs)
        _inject_comments(f, 1)
        rc, out = run_fix(f, [anchor])
        self.assertEqual(rc, 0, out)
        self.assertIn("fixed 1/1", out)
        self.assert_range_ok(f, 0, 0, anchor, "".join(runs[0]))

    def test_04_multi_run_anchor_spans_runs(self):
        runs = [["发行人", "主营业务", "毛利率为32.15%，", "高于同业。"]]
        anchor = "主营业务毛利率为32.15%"
        f = build_docx(runs)
        _inject_comments(f, 1)
        rc, out = run_fix(f, [anchor])
        self.assertEqual(rc, 0, out)
        self.assertIn("fixed 1/1", out)
        self.assert_range_ok(f, 0, 0, anchor, "".join(runs[0]))

    def test_05_anchor_at_paragraph_start(self):
        runs = [["报告期内公司汇兑净损失为-26.14万元。"]]
        anchor = "报告期内公司"
        f = build_docx(runs)
        _inject_comments(f, 1)
        rc, out = run_fix(f, [anchor])
        self.assertEqual(rc, 0, out)
        self.assertIn("fixed 1/1", out)
        self.assert_range_ok(f, 0, 0, anchor, "".join(runs[0]))

    def test_06_two_comments_same_paragraph(self):
        runs = [["报告期内公司汇兑净损失为-26.14万元，同比上升。"]]
        a0, a1 = "汇兑净损失为-26.14万元", "同比上升"
        f = build_docx(runs)
        _inject_comments(f, 2)
        rc, out = run_fix(f, [a0, a1])
        self.assertEqual(rc, 0, out)
        self.assertIn("fixed 2/2", out)
        self.assert_range_ok(f, 0, 0, a0, "".join(runs[0]))
        self.assert_range_ok(f, 0, 1, a1, "".join(runs[0]))

    def test_07_anchor_not_found(self):
        runs = [["报告期内公司汇兑净损失为-26.14万元。"]]
        f = build_docx(runs)
        _inject_comments(f, 1)
        rc, out = run_fix(f, ["这段文字不存在"])
        self.assertEqual(rc, 0, out)
        self.assertIn("anchor not found", out)
        self.assertIn("fixed 0/1", out)
        # 未命中不得改动文档：无任何标记插入，段落文本原样
        toks = _tokens(_paras(f)[0])
        self.assertEqual(_marker_seq(toks, 0), [])
        self.assertEqual(_full_text(toks), "".join(runs[0]))

    def test_08_idempotent_second_run(self):
        runs = [["报告期内公司汇兑净损失为-26.14万元，同比上升。"]]
        anchor = "汇兑净损失为-26.14万元"
        f = build_docx(runs)
        _inject_comments(f, 1)
        rc1, out1 = run_fix(f, [anchor])
        self.assertEqual(rc1, 0, out1)
        rc2, out2 = run_fix(f, [anchor])
        self.assertEqual(rc2, 0, out2)
        self.assertIn("missing ids: []", out2)
        self.assertIn("fixed 0/0", out2)
        # 二次运行后标记仍只有一组
        self.assert_range_ok(f, 0, 0, anchor, "".join(runs[0]))


if __name__ == "__main__":
    unittest.main(verbosity=2)

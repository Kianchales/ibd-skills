#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_deliver_gate.py — deliver_gate.py 自测（含批注/修订挂载开关）

覆盖：
  A. 基础九项
     1. 合格交付件 + 同源 md → 九项全 PASS，退出码 0
     2. 半角标点 / 禁用词 / 同源不一致 → 对应项 FAIL，退出码 1
     3. 只给 --md → md 侧预检五项
  B. --annotated 挂载（批注三项）
     4. 合规批注件（2 条）→ 十二项全 PASS
     5. 批注结构违规（段落数≠4 / 标签行未加粗 / 编号格式错 / 编号重复）→ FAIL
     6. 锚定对数不齐 / 缺 comments.xml 部件 → FAIL
     7. --expect-annotated 与实测不符 → 批注结构 FAIL
  C. --revised 挂载（修订三项）
     8. 合规修订稿 → 十二项全 PASS
     9. ins/del 不成对 / 缺 author → 修订成对 FAIL
    10. settings 未开 trackRevisions / delText 为空 → 修订落定 FAIL
    11. --expect-revised 与实测不符 → 修订计数 FAIL
  D. 参数契约
    12. --annotated 与 --revised 同给 → argparse 报错（退出码 2）
    13. --annotated 不给 --docx → 报错
    14. 不给任何输入 → 报错
  E. OPC 关系表语义守卫（RelsSemanticsTest）
    15. 无批注 fixture 的全部 .rels Target 均可解析到包内部件
    16. 含批注 fixture 同上（覆盖 extra_rel 注入路径）
    17. 部件级 rels 不得含 officeDocument 关系（只属于包根 rels）
    18. 装了 python-docx 则真打开一次；未装则 SKIP（不破坏零依赖铁律）
运行：python scripts/tests/test_deliver_gate.py
"""
import os
import re
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

SKILL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPT = os.path.join(SKILL_DIR, "scripts", "deliver_gate.py")

WNS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
NS_CT = "http://schemas.openxmlformats.org/package/2006/content-types"
NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"

CT_TMPL = (
    '<?xml version="1.0"?><Types xmlns="{ct}">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    '{extra}</Types>'
)
# 包根关系表（_rels/.rels）：Target 相对**包根**解析，故 officeDocument → word/document.xml
RELS_TMPL = (
    '<?xml version="1.0"?><Relationships xmlns="{rel}">'
    '<Relationship Id="rId0" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
    "{extra}</Relationships>"
)
# 主部件关系表（word/_rels/document.xml.rels）：Target 相对**word\ 目录**解析。
# 旧版误复用 RELS_TMPL，使 Target="word/document.xml" 被解析为 word/word/document.xml →
# 真实解析器（python-docx）打开即 KeyError（2026-09-11 修复，见守卫测试 RelsSemanticsTest）。
DOC_RELS_TMPL = (
    '<?xml version="1.0"?><Relationships xmlns="{rel}">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>'
    "{extra}</Relationships>"
)
SETTINGS_PLAIN = (
    '<?xml version="1.0"?><w:settings %s>'
    '<w:zoom w:percent="100"/><w:defaultTabStop w:val="420"/></w:settings>' % WNS
)
SETTINGS_TRACK = (
    '<?xml version="1.0"?><w:settings %s>'
    '<w:zoom w:percent="100"/><w:trackRevisions/><w:revisionView w:markup="1"/></w:settings>' % WNS
)
STYLES_XML = (
    '<?xml version="1.0"?><w:styles %s>'
    '<w:style w:type="paragraph" w:styleId="CommentText"><w:name w:val="Comment Text"/></w:style>'
    '<w:style w:type="character" w:styleId="CommentReference"><w:name w:val="Comment Reference"/></w:style>'
    "</w:styles>" % WNS
)
# 必备样式 000 / 0011 / 001（反馈回复场景）齐备，且正文用 001
BODY_PARA = '<w:p><w:pPr><w:pStyle w:val="001"/></w:pPr><w:r><w:t>%s</w:t></w:r></w:p>'


def _pkt(path, doc_xml, settings=SETTINGS_PLAIN, comments=None, extra_ct="", extra_rel=""):
    has_cmt = comments is not None
    if has_cmt:
        extra_ct = extra_ct or (
            '<Override PartName="/word/comments.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"/>')
        extra_rel = extra_rel or (
            '<Relationship Id="rId9" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments" Target="comments.xml"/>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CT_TMPL.format(ct=NS_CT, extra=extra_ct))
        z.writestr("_rels/.rels", RELS_TMPL.format(rel=NS_REL, extra=""))
        # word/_rels/document.xml.rels 恒写入（真实 docx 必有），comments 关系按需追加。
        # 必须用 DOC_RELS_TMPL（部件级），不可复用 RELS_TMPL（包根级）——见其定义处注释。
        z.writestr("word/_rels/document.xml.rels",
                   DOC_RELS_TMPL.format(rel=NS_REL, extra=extra_rel))
        z.writestr("word/document.xml", doc_xml)
        z.writestr("word/settings.xml", settings)
        z.writestr("word/styles.xml", STYLES_XML)
        if has_cmt:
            z.writestr("word/comments.xml", comments)


def make_docx(path, body_xml):
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
           f'<w:document {WNS}><w:body>{body_xml}<w:sectPr/></w:body></w:document>')
    _pkt(path, doc)


def _run_style(p):
    """pStyle 齐备的正文包装（000 标题 + 0011 小标题 + 001 正文）

    标题/小标题文本与 md 侧共用 TEXT_TITLE / TEXT_SUB，保证「同源核验」可比。
    三行均用带 pStyle 的段落承载，避免依赖裸段落计数口径。
    """
    return (_para("000", TEXT_TITLE) + _para("0011", TEXT_SUB)
            + "".join(_para("001", t) for t in p))


def _para(style, text):
    return (f'<w:p><w:pPr><w:pStyle w:val="{style}"/></w:pPr>'
            f'<w:r><w:t xml:space="preserve">{text}</w:t></w:r></w:p>')


TEXT_TITLE = "关于审核问询函的回复"
TEXT_SUB = "一、关于财务数据"
TEXT_BODY = "甲方应于2026年6月30日前完成交割，金额36,507.55万元。"
MD_SOURCE = f"# {TEXT_TITLE}\n\n## {TEXT_SUB}\n\n{TEXT_BODY}\n"


def good_body(texts=(TEXT_BODY,)):
    return _run_style(texts)


def run_gate(args_list):
    proc = subprocess.run([sys.executable, SCRIPT] + args_list,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def line_of(out, name):
    m = re.search(rf"^\[(PASS|FAIL|SKIP)\]\s+{re.escape(name)}\s+(.*)$", out, re.M)
    return m


# ------------------------------------------------------------------ 批注构造

def _bold_run(t):
    return f'<w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">{t}</w:t></w:r>'


def _plain_run(t):
    """正文常规 run —— 显式 <w:b w:val="0"/>；仅当 w:b 存在且无 w:val 才判加粗"""
    return f'<w:r><w:rPr><w:b w:val="0"/></w:rPr><w:t xml:space="preserve">{t}</w:t></w:r>'


def comment_xml(cid, label, title, desc, adv):
    """合规批注：4 段紧凑，行1/行2 整行加粗，行3/4 仅引导词加粗"""
    return (f'<w:comment w:id="{cid}" w:author="复核人" w:date="2026-09-11T09:00:00Z" w:initials="复">'
            + "".join([
                f"<w:p>{_bold_run(label)}</w:p>",
                f"<w:p>{_bold_run(title)}</w:p>",
                f"<w:p>{_bold_run('问题描述：')}{_plain_run(desc)}</w:p>",
                f"<w:p>{_bold_run('建议：')}{_plain_run(adv)}</w:p>",
            ]) + "</w:comment>")


def comments_doc(entries):
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            f'<w:comments {WNS}>{"".join(entries)}</w:comments>')


def doc_with_anchors(n, body_extra=""):
    """生成 n 对 commentRangeStart/End/Reference 的正文"""
    parts = []
    for i in range(n):
        parts.append(
            f'<w:p><w:pPr><w:pStyle w:val="001"/></w:pPr>'
            f'<w:commentRangeStart w:id="{i}"/><w:r><w:t>被批注句{i}</w:t></w:r>'
            f'<w:commentRangeEnd w:id="{i}"/>'
            f'<w:r><w:commentReference w:id="{i}"/></w:r></w:p>')
    return (f'<w:p><w:pPr><w:pStyle w:val="000"/></w:pPr><w:r><w:t>标题</w:t></w:r></w:p>'
            f'<w:p><w:pPr><w:pStyle w:val="0011"/></w:pPr><w:r><w:t>小标题</w:t></w:r></w:p>'
            + "".join(parts) + body_extra)


def make_annotated(path, entries, n_anchors=None, with_parts=True, ct_extra="", rel_extra=""):
    n = len(entries) if n_anchors is None else n_anchors
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
           f'<w:document {WNS}><w:body>{doc_with_anchors(n)}<w:sectPr/></w:body></w:document>')
    cmts = comments_doc(entries) if with_parts else None
    _pkt(path, doc, comments=cmts, extra_ct=ct_extra, extra_rel=rel_extra)


# ------------------------------------------------------------------ 修订构造

def ins_run(t, rid, author="复核人"):
    return (f'<w:ins w:id="{rid}" w:author="{author}" w:date="2026-09-11T09:00:00Z">'
            f'<w:r><w:t xml:space="preserve">{t}</w:t></w:r></w:ins>')


def del_run(t, rid, author="复核人"):
    return (f'<w:del w:id="{rid}" w:author="{author}" w:date="2026-09-11T09:00:00Z">'
            f'<w:r><w:delText xml:space="preserve">{t}</w:delText></w:r></w:del>')


def make_revised(path, body_xml, settings=SETTINGS_TRACK):
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
           f'<w:document {WNS}><w:body>{body_xml}<w:sectPr/></w:body></w:document>')
    _pkt(path, doc, settings=settings)


def revised_body(pairs):
    """pairs: [(old, new)]；正文中保留新文本（落定），并成对给出 ins/del"""
    parts = [_para("000", TEXT_TITLE), _para("0011", TEXT_SUB)]
    for i, (old, new) in enumerate(pairs):
        parts.append(f'<w:p><w:pPr><w:pStyle w:val="001"/></w:pPr>'
                     f'{del_run(old, i)}{ins_run(new, i)}'
                     f'<w:r><w:t xml:space="preserve"> 其余文字。</w:t></w:r></w:p>')
    return "".join(parts)


class TmpDirMixin:
    def setUp(self):
        self._d = tempfile.TemporaryDirectory()
        self.d = self._d.name
        self.addCleanup(self._d.cleanup)

    def p(self, name):
        return os.path.join(self.d, name)


# ================================================================== A. 基础九项

class TestBaseGate(TmpDirMixin, unittest.TestCase):

    def test_01_good_delivery_passes(self):
        docx, md = self.p("ok.docx"), self.p("ok.md")
        make_docx(docx, good_body())
        with open(md, "w", encoding="utf-8") as f:
            f.write(MD_SOURCE)
        rc, out = run_gate(["--docx", docx, "--md", md, "--anchors", "36,507.55"])
        self.assertEqual(rc, 0, out)
        self.assertEqual(out.count("[PASS]"), 9)
        self.assertIn("9/9 PASS", out)

    def test_02_halfwidth_punct_and_ban_fail(self):
        docx, md = self.p("bad.docx"), self.p("bad.md")
        make_docx(docx, good_body(('甲方应于 "2026" 年完成 (交割)，颠覆行业。',)))
        with open(md, "w", encoding="utf-8") as f:
            f.write(MD_SOURCE + '甲方应于 "2026" 年完成 (交割)，颠覆行业。\n')
        rc, out = run_gate(["--docx", docx, "--md", md])
        self.assertEqual(rc, 1, out)
        self.assertEqual(line_of(out, "标点规范").group(1), "FAIL")
        self.assertEqual(line_of(out, "禁用词红线").group(1), "FAIL")

    def test_03_md_only_precheck(self):
        md = self.p("draft.md")
        with open(md, "w", encoding="utf-8") as f:
            f.write("# 标题\n\n本轮回复金额为36,507.55万元。\n")
        rc, out = run_gate(["--md", md, "--anchors", "36,507.55"])
        self.assertEqual(rc, 0, out)
        self.assertIn("可进入套样式", out)

    def test_03b_number_space_around_fails(self):
        """数字前后不加空格（rules.md 三·3）：中文与数字间有空格 → 标点规范 FAIL"""
        md = self.p("sp.md")
        with open(md, "w", encoding="utf-8") as f:
            f.write("# 标题\n\n甲方应于 2026 年 6 月 30 日前完成交割，金额 36,507.55 万元。\n")
        rc, out = run_gate(["--md", md, "--anchors", "36,507.55"])
        self.assertEqual(rc, 1, out)
        self.assertEqual(line_of(out, "标点规范").group(1), "FAIL")
        self.assertIn("数字前后不加空格", out)

    def test_03c_number_space_exemptions_pass(self):
        """西文缩写与数字之间（GB 35114）、纯数字连写 → 不报"""
        md = self.p("ok2.md")
        with open(md, "w", encoding="utf-8") as f:
            f.write("# 标题\n\n依据强制性国家标准GB 35114及ISO 9001，"
                    "公司于2026年6月30日前完成交割，金额36,507.55万元。\n")
        rc, out = run_gate(["--md", md, "--anchors", "36,507.55"])
        self.assertEqual(rc, 0, out)


# ================================================================== B. 批注挂载

class TestAnnotated(TmpDirMixin, unittest.TestCase):

    def _ok_pair(self):
        return [comment_xml(0, "【J-01｜数据｜高】", "金额与底稿不一致",
                            "正文36,507.55万元与底稿36,507.50万元不符。", "请与财务底稿核对后统一。"),
                comment_xml(1, "【L-01｜表述｜中】", "绝对化表述",
                            "「确保通过」含绝对承诺意味。", "调整为「预计能够通过」。")]

    def test_04_compliant_annotated_passes(self):
        docx = self.p("ann_ok.docx")
        make_annotated(docx, self._ok_pair())
        rc, out = run_gate(["--docx", docx, "--annotated", "--expect-annotated", "2"])
        self.assertEqual(rc, 0, out)
        self.assertIn("批注版", out)
        self.assertIn("9/9 PASS", out)
        self.assertEqual(line_of(out, "批注部件").group(1), "PASS")
        self.assertEqual(line_of(out, "批注结构").group(1), "PASS")
        self.assertEqual(line_of(out, "批注编号"), None)  # 编号已并入批注结构，不单列

    def test_05_structure_violations_fail(self):
        bad = [comment_xml(0, "【J-01｜数据｜高】", "标题", "描述。", "建议。").replace(
                   "<w:p>" + _bold_run("问题描述：") + _plain_run("描述。") + "</w:p>", ""),
               comment_xml(1, "J-2 x", "标题", "描述。", "建议。")]
        docx = self.p("ann_bad.docx")
        make_annotated(docx, bad)
        rc, out = run_gate(["--docx", docx, "--annotated"])
        self.assertEqual(rc, 1, out)
        self.assertEqual(line_of(out, "批注结构").group(1), "FAIL")
        self.assertIn("段落数", out)
        self.assertIn("非 【前缀-序号｜类型｜严重度】", out)

    def test_06_missing_part_or_anchor_mismatch_fails(self):
        docx = self.p("ann_noparts.docx")
        make_annotated(docx, self._ok_pair(), with_parts=False)
        rc, out = run_gate(["--docx", docx, "--annotated"])
        self.assertEqual(line_of(out, "批注部件").group(1), "FAIL")

        docx2 = self.p("ann_mismatch.docx")
        make_annotated(docx2, self._ok_pair(), n_anchors=1)  # 2 条批注但仅 1 对锚点
        rc2, out2 = run_gate(["--docx", docx2, "--annotated"])
        self.assertEqual(rc2, 1, out2)
        self.assertEqual(line_of(out2, "批注结构").group(1), "FAIL")
        self.assertIn("锚定对数不齐", out2)

    def test_06b_missing_crossrefs_fails(self):
        """comments.xml 在包但 Content_Types Override / rels 关系双缺 → 批注部件 FAIL"""
        docx = self.p("ann_nocross.docx")
        doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
               f'<w:document {WNS}><w:body>{doc_with_anchors(1)}<w:sectPr/></w:body></w:document>')
        _pkt(docx, doc, comments=comments_doc(self._ok_pair()[:1]))
        # 事后擦除 CT Override 与 rels 关系（模拟部件存在但未登记）
        import shutil
        tmp = docx + ".tmp"
        with zipfile.ZipFile(docx) as src, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as dst:
            for n in src.namelist():
                data = src.read(n)
                if n == "[Content_Types].xml":
                    data = re.sub(rb"<Override[^>]*comments[^>]*/>", b"", data)
                if n == "word/_rels/document.xml.rels":
                    data = re.sub(rb"<Relationship[^>]*comments[^>]*/>", b"", data)
                dst.writestr(n, data)
        shutil.move(tmp, docx)
        rc, out = run_gate(["--docx", docx, "--annotated"])
        self.assertEqual(line_of(out, "批注部件").group(1), "FAIL")
        self.assertIn("comments Override", out)
        self.assertIn("→ comments.xml 关系", out)

    def test_07_expect_annotated_mismatch_fails(self):
        docx = self.p("ann_cnt.docx")
        make_annotated(docx, self._ok_pair())
        rc, out = run_gate(["--docx", docx, "--annotated", "--expect-annotated", "9"])
        self.assertEqual(rc, 1, out)
        self.assertIn("批注条数 2 ≠ 期望 9", out)

    def test_07b_duplicate_number_fails(self):
        dup = [comment_xml(0, "【J-01｜数据｜高】", "甲", "描述。", "建议。"),
               comment_xml(1, "【J-01｜表述｜低】", "乙", "描述。", "建议。")]
        docx = self.p("ann_dup.docx")
        make_annotated(docx, dup)
        rc, out = run_gate(["--docx", docx, "--annotated"])
        self.assertEqual(rc, 1, out)
        self.assertIn("批注编号重复", out)


# ================================================================== C. 修订挂载

class TestRevised(TmpDirMixin, unittest.TestCase):

    def test_08_compliant_revised_passes(self):
        docx = self.p("rev_ok.docx")
        make_revised(docx, revised_body([("36,507.50万元", "36,507.55万元")]))
        rc, out = run_gate(["--docx", docx, "--revised", "--expect-revised", "1"])
        self.assertEqual(rc, 0, out)
        self.assertIn("修订版", out)
        self.assertIn("PASS ✅", out)
        self.assertEqual(line_of(out, "修订成对").group(1), "PASS")
        self.assertEqual(line_of(out, "修订落定").group(1), "PASS")
        self.assertEqual(line_of(out, "修订计数").group(1), "PASS")

    def test_09_unpaired_or_no_author_fails(self):
        body = (_para("000", TEXT_TITLE) + _para("0011", TEXT_SUB)
                + '<w:p><w:pPr><w:pStyle w:val="001"/></w:pPr>'
                + ins_run("新文本", 0) + del_run("旧文本", 1)  # id 不成对
                + "</w:p>"
                + '<w:p><w:pPr><w:pStyle w:val="001"/></w:pPr>'
                + ins_run("无作者", 2, author="") + del_run("旧二", 2)
                + "</w:p>")
        docx = self.p("rev_bad.docx")
        make_revised(docx, body)
        rc, out = run_gate(["--docx", docx, "--revised"])
        self.assertEqual(rc, 1, out)
        self.assertEqual(line_of(out, "修订成对").group(1), "FAIL")
        self.assertIn("不成对", out)
        self.assertIn("缺 author", out)

    def test_10_no_track_changes_or_empty_del_fails(self):
        body = (_para("000", TEXT_TITLE) + _para("0011", TEXT_SUB)
                + '<w:p><w:pPr><w:pStyle w:val="001"/></w:pPr>'
                + '<w:del w:id="0" w:author="复核人"><w:r>'
                  '<w:delText xml:space="preserve"> </w:delText></w:r></w:del>'
                + ins_run("新文本", 0) + "</w:p>")
        docx = self.p("rev_settle.docx")
        make_revised(docx, body, settings=SETTINGS_PLAIN)
        rc, out = run_gate(["--docx", docx, "--revised"])
        self.assertEqual(rc, 1, out)
        self.assertEqual(line_of(out, "修订落定").group(1), "FAIL")
        self.assertIn("trackRevisions", out)
        self.assertIn("修订文本为空", out)

    def test_11_expect_revised_mismatch_fails(self):
        docx = self.p("rev_cnt.docx")
        make_revised(docx, revised_body([("旧", "新")]))
        rc, out = run_gate(["--docx", docx, "--revised", "--expect-revised", "7"])
        self.assertEqual(rc, 1, out)
        self.assertEqual(line_of(out, "修订计数").group(1), "FAIL")
        self.assertIn("ins 条数 1 != 期望 7", out)


# ================================================================== D. 参数契约

class TestArgContract(TmpDirMixin, unittest.TestCase):

    def test_12_annotated_and_revised_conflict(self):
        docx = self.p("x.docx")
        make_docx(docx, good_body())
        rc, out = run_gate(["--docx", docx, "--annotated", "--revised"])
        self.assertEqual(rc, 2, out)
        self.assertIn("互斥", out)

    def test_13_annotated_without_docx(self):
        md = self.p("m.md")
        with open(md, "w", encoding="utf-8") as f:
            f.write("正文。\n")
        rc, out = run_gate(["--md", md, "--annotated"])
        self.assertEqual(rc, 2, out)
        self.assertIn("需配 --docx", out)

    def test_14_no_input(self):
        rc, out = run_gate([])
        self.assertEqual(rc, 2, out)
        self.assertIn("至少提供", out)

    def test_15_base_nine_unchanged_without_flag(self):
        """回归：不给开关时仍是九项（既有调用方契约不破坏）"""
        docx, md = self.p("reg.docx"), self.p("reg.md")
        make_docx(docx, good_body())
        with open(md, "w", encoding="utf-8") as f:
            f.write(MD_SOURCE)
        rc, out = run_gate(["--docx", docx, "--md", md])
        self.assertEqual(rc, 0, out)
        self.assertIn("8/8 PASS", out)


# ================================================================== E. officecli 物理扫描（SKIP 三态）

class PhysicalScanTest(unittest.TestCase):
    """officecli 软门禁：SKIP 必须可见、且**不阻断退出码**。

    探测走 subprocess 调外部二进制，故用例只覆盖「未启用 / 未找到」两条 SKIP 路径
    （确定性、零外部依赖），不依赖本机是否装 officecli。
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = lambda n: os.path.join(self.tmp.name, n)

    def tearDown(self):
        self.tmp.cleanup()

    def test_16_officecli_not_enabled_skips(self):
        """不给 --officecli → SKIP 行可见，且不影响退出码"""
        docx, md = self.p("a.docx"), self.p("a.md")
        make_docx(docx, good_body())
        with open(md, "w", encoding="utf-8") as f:
            f.write(MD_SOURCE)
        rc, out = run_gate(["--docx", docx, "--md", md])
        self.assertEqual(rc, 0, out)
        m = line_of(out, "物理扫描")
        self.assertIsNotNone(m, f"应输出物理扫描行:\n{out}")
        self.assertEqual(m.group(1), "SKIP", out)
        self.assertIn("未启用", m.group(2))
        self.assertIn("SKIP 未执行", out)   # 结论行附注

    def test_17_officecli_not_found_skips_without_blocking(self):
        """给了 --officecli 但路径不存在 → SKIP，退出码不受影响（软门禁不阻断）"""
        docx, md = self.p("b.docx"), self.p("b.md")
        make_docx(docx, good_body())
        with open(md, "w", encoding="utf-8") as f:
            f.write(MD_SOURCE)
        rc, out = run_gate(["--docx", docx, "--md", md, "--officecli",
                            "--officecli-path", self.p("nope.exe")])
        self.assertEqual(rc, 0, f"SKIP 不应阻断交付:\n{out}")
        m = line_of(out, "物理扫描")
        self.assertIsNotNone(m, out)
        self.assertEqual(m.group(1), "SKIP", out)
        self.assertIn("未找到 officecli", m.group(2))

    def test_18_skip_excluded_from_pass_ratio(self):
        """SKIP 不进分子分母 —— 结论仍是 8/8 而非 8/9（不污染通过率）"""
        docx, md = self.p("c.docx"), self.p("c.md")
        make_docx(docx, good_body())
        with open(md, "w", encoding="utf-8") as f:
            f.write(MD_SOURCE)
        rc, out = run_gate(["--docx", docx, "--md", md])
        self.assertEqual(rc, 0, out)
        self.assertIn("8/8 PASS", out)
        self.assertNotIn("8/9 PASS", out)


class RelsSemanticsTest(TmpDirMixin, unittest.TestCase):
    """E 组 · OPC 关系表语义守卫（2026-09-11 新增）

    起因：fixture 的 `word/_rels/document.xml.rels` 误复用包根级 `RELS_TMPL`，
    使 `Target="word/document.xml"` 被按 `word\\` 基准解析成 `word/word/document.xml`，
    真实解析器（python-docx）打开即 KeyError；而本包门禁全走 zipfile + 字符串包含判断，
    **测不出来**（fixture 早已畸形，测试却全绿）。

    本组以**纯标准库**校验 OPC 解析规则，堵住同类复发——不引入任何第三方依赖。
    """

    @staticmethod
    def _rels_entries(z):
        """产出 [(rels部件名, Target, TargetMode)]，覆盖包内全部 .rels"""
        out = []
        for n in z.namelist():
            if not n.endswith(".rels"):
                continue
            root = ET.fromstring(z.read(n).decode("utf-8"))
            for rel in root:
                out.append((n, rel.get("Target"), rel.get("TargetMode")))
        return out

    @staticmethod
    def _resolve(rels_part, target):
        """按 OPC 规则解析 Target：以部件所在目录为基准（_rels/.rels → 包根）"""
        if target.startswith("/"):
            return target.lstrip("/")
        base = os.path.dirname(os.path.dirname(rels_part))  # word/_rels/x.rels → word
        return os.path.normpath(os.path.join(base, target)).replace("\\", "/")

    def _assert_all_targets_resolve(self, path):
        with zipfile.ZipFile(path) as z:
            names, entries = set(z.namelist()), self._rels_entries(z)
        self.assertTrue(entries, "包内应至少有一张关系表")
        for rels_part, target, mode in entries:
            if mode == "External" or "://" in (target or ""):
                continue
            full = self._resolve(rels_part, target)
            self.assertIn(
                full, names,
                f"{rels_part} 的 Target={target!r} 按 OPC 规则解析为 {full!r}，但包内无此部件"
                f"（典型症状：部件级 rels 误写成包根级 Target，前缀重复）")

    def _doc_with(self, n_anchors):
        return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                f'<w:document {WNS}><w:body>{doc_with_anchors(n_anchors)}<w:sectPr/></w:body></w:document>')

    def test_01_fixture_rels_resolve_without_comments(self):
        docx = os.path.join(self.d, "rels_plain.docx")
        make_docx(docx, good_body())
        self._assert_all_targets_resolve(docx)

    def test_02_fixture_rels_resolve_with_comments(self):
        docx = os.path.join(self.d, "rels_cmt.docx")
        _pkt(docx, self._doc_with(1), comments=comments_doc(self._ok_pair()))
        self._assert_all_targets_resolve(docx)

    def test_03_part_rels_has_no_officedocument_relation(self):
        """部件级 rels 不得含 officeDocument 关系——该关系只属于包根 rels（本 bug 的直接判据）"""
        docx = os.path.join(self.d, "rels_part.docx")
        make_docx(docx, good_body())
        with zipfile.ZipFile(docx) as z:
            self.assertIn("word/_rels/document.xml.rels", z.namelist(),
                          "真实 docx 必含部件级关系表")
            root = ET.fromstring(z.read("word/_rels/document.xml.rels").decode("utf-8"))
        types = [r.get("Type") for r in root]
        self.assertFalse(
            [t for t in types if t and t.endswith("/officeDocument")],
            "word/_rels/document.xml.rels 含 officeDocument 关系 → Target 将被重复前缀解析")
        self.assertTrue([t for t in types if t and t.endswith("/styles")],
                        "部件级 rels 应含 styles 关系（与真实 docx 一致）")

    def test_04_fixture_opens_in_real_parser(self):
        """可选增强：装了 python-docx 则真打开一次；未装则 SKIP（不破坏零依赖铁律）"""
        try:
            from docx import Document
        except ImportError:
            raise unittest.SkipTest("未安装 python-docx（本包零第三方依赖），跳过真实解析器校验")
        docx = os.path.join(self.d, "rels_open.docx")
        _pkt(docx, self._doc_with(1), comments=comments_doc(self._ok_pair()))
        doc = Document(docx)
        self.assertGreaterEqual(len(doc.paragraphs), 1)

    def _ok_pair(self):
        return [comment_xml(0, "【J-01｜数据｜高】", "金额与底稿不一致",
                            "正文36,507.55万元与底稿36,507.50万元不符。", "请与财务底稿核对后统一。")]


if __name__ == "__main__":
    unittest.main(verbosity=2)

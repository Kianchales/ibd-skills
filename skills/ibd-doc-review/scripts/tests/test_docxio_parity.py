#!/usr/bin/env python3
"""
test_docxio_parity.py — 对拍：docxio 必须复现旧实现的口径（真实文件）

为什么先对拍再替换
------------------
抽层的风险不是"新代码有 bug"，而是"新代码**悄悄改了口径**"——尤其分母
（表格单元格 22,535 段 vs 正文 909 段，混算差 25 倍）。故规则是：
**新实现必须与旧实现逐字/逐数一致；唯一允许的差异是实体解码（那是修 bug）。**

对拍对象（3 组，全部用真实文件）
  1. `plan_review.load_units` 的 stats ↔ docxio 重算（总段/表格/单元格/空段落/五类）
  2. `deliver_gate.read_docx` 的全文 ↔ `docxio.flat_text()`（逐字相等）
  3. `check_styles` 的裸段/空段计数 ↔ docxio 重算（数字相等）

另有一条**差异断言**：正则流派（content_common）与 ET 流派的差异必须**正好等于实体解码**，
多出任何差异都说明改动了别的东西。

样本缺失 → SKIP（不阻断），与金样本同一原则。

运行：REVIEW_TESTS=all python scripts/tests/test_docxio_parity.py
"""
import html
import json
import importlib.util
import os
import re
import subprocess
import sys
import unittest

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from _tier import slow_all  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, "..", ".."))
SCRIPTS = os.path.join(PKG, "scripts")


def load(name, fn):
    spec = importlib.util.spec_from_file_location(name, os.path.join(SCRIPTS, fn))
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


dx = load("docxio", "docxio.py")
pr = load("pr_parity", "plan_review.py")
dg = load("dg_parity", "deliver_gate.py")
cc = load("cc_parity", "content_common.py")
cs = load("cs_parity", "check_styles.py")

# 样本目录由环境变量给出；未设则无样本 → SKIP（公开包不假设本机目录布局）
GOLDEN_DIR = os.environ.get("IBD_GOLDEN_DIR", "")


def load_samples():
    """从**包外**的金样本清单取样（清单含真实文件路径，不入包、不入 git）。"""
    mf = os.path.join(GOLDEN_DIR, "manifest.json")
    if not os.path.exists(mf):
        return []
    out = []
    for c in json.load(open(mf, encoding="utf-8"))["cases"]:
        p = c.get("docx") or c.get("xlsx") or ""
        if not p.endswith(".docx"):
            continue
        p = p if os.path.isabs(p) else os.path.join(GOLDEN_DIR, p)
        if os.path.exists(p):
            out.append((c["name"], p))
    return out


SAMPLES = load_samples()


def recompute_stats(path):
    """用 docxio 复现 plan_review.load_units 的统计口径。"""
    b = dx.open_docx(path)
    total = tables = cells = empty = 0
    cats = {}
    for kind, node in dx.iter_blocks(b):
        if kind == "tbl":
            tables += 1
            for p in node.iter(dx.W + "p"):
                cells += 1
                total += 1
            continue
        txt = dx.para_text(node)          # tabs/breaks=True, del_text=False == plan_review 口径
        if not txt.strip():
            empty += 1
            continue
        total += 1
        cat, _ = pr.classify(txt, False)
        cats[cat] = cats.get(cat, 0) + 1
    out = {"总段": total, "表格": tables, "单元格": cells, "空段落": empty}
    for k in ("正文", "标题", "中段", "短句", "目录"):
        out[k] = cats.get(k, 0)
    return out


def recompute_style_counts(path):
    """用 docxio 复现 check_styles 的裸段/空段口径（排除表格内段落）。"""
    b = dx.open_docx(path)
    bare = empty = 0
    for p in dx.iter_paras(b, include_table=False, tabs=False, breaks=False):
        t = p.text.strip()
        if not t:
            empty += 1
        elif p.style is None:
            bare += 1
    return bare, empty


def check_styles_counts(path):
    """样式计数：走 `check_styles.collect()` 进程内调用（0.58.0 提速）。

    原实现每个样本起一次子进程跑 CLI，3 份样本 ~4.5 秒。数字与 CLI 一致由
    `test_cli_smoke_matches_collect` 单独守（每组只留一条 CLI 冒烟）。
    """
    d = cs.collect(path, "招股书")
    return (d["n_bare"], d["n_empty"])


class TestParity(unittest.TestCase):
    """对拍：**每个样本只解析一次**，结果缓存给各用例。

    原实现每条用例都重新读盘解析（3 份样本 × 5 条 ≈ 15 次），大量耗在重复解析
    10MB 的 document.xml 上——不是慢在子进程。缓存后总耗时显著下降且语义不变。
    """

    # 对拍样本上限：批注版／修订稿与招股书**同一套正文**（只是多了批注/修订标记），
    # 覆盖重复；保留三类差异最大的（正文型招股书／附注型／报告型含嵌套表与文本框）。
    MAX_SAMPLES = 3

    @classmethod
    def setUpClass(cls):
        cls.cache = {}
        for name, p in SAMPLES[:cls.MAX_SAMPLES]:
            if not os.path.exists(p):
                continue
            b = dx.open_docx(p)
            old_stats_units, stats = pr.load_units(p)
            old_text, _root, _xml = dg.read_docx(p)
            cls.cache[p] = {
                "name": name,
                "stats": stats,
                "recomputed": recompute_stats(p),
                "gate_text": old_text,
                "flat": dx.flat_text(b),
                "flat_nl": dx.flat_text(b, para_sep="\n"),
                "style_old": check_styles_counts(p),
                "style_new": recompute_style_counts(p),
                "cc_text": cc.full_text_of(
                    cc.load_docx(p)["word/document.xml"]),
            }

    def each(self):
        for p, c in self.cache.items():
            yield c["name"], p

    def test_plan_review_stats(self):
        self.assertTrue(self.cache, "无样本可对拍")
        for p, c in self.cache.items():
            for k in ("总段", "表格", "单元格", "空段落", "正文", "标题", "中段", "短句", "目录"):
                self.assertEqual(c["stats"][k], c["recomputed"][k],
                                 f"{c['name']}：{k} 旧 {c['stats'][k]} ≠ 新 {c['recomputed'][k]}")

    def test_deliver_gate_text_exact(self):
        self.assertTrue(self.cache, "无样本可对拍")
        for p, c in self.cache.items():
            self.assertEqual(c["gate_text"], c["flat"],
                             f"{c['name']}：全文不逐字相等（{len(c['gate_text'])} vs {len(c['flat'])}）")

    def test_check_styles_counts(self):
        self.assertTrue(self.cache, "无样本可对拍")
        for p, c in self.cache.items():
            self.assertEqual(c["style_old"], c["style_new"],
                             f"{c['name']}：裸段/空段 旧 {c['style_old']} ≠ 新 {c['style_new']}")

    def test_cli_smoke_matches_collect(self):
        """CLI 冒烟：人读输出里的裸段/空段必须与 collect() 相同（防只改打印不改数据）。"""
        first = next(iter(self.cache.items()), None)
        if not first:
            self.skipTest("无样本")
        p, c = first
        out = subprocess.run([sys.executable, os.path.join(SCRIPTS, "check_styles.py"),
                              "--input", p, "--scenario", "招股书"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
        s_ = (out.stdout or "") + (out.stderr or "")
        m_bare = re.search(r"(\d+)\s*个裸段落", s_)
        m_empty = re.search(r"(\d+)\s*个空段落", s_)
        self.assertIsNotNone(m_bare, "CLI 未输出裸段计数")
        self.assertEqual((int(m_bare.group(1)), int(m_empty.group(1))),
                         (c["style_new"][0], c["style_new"][1]), "CLI 与 collect() 数字不一致")

    def test_entity_divergence_is_only_entity(self):
        """正则流派与 ET 流派的差异，必须正好是「实体解码」这一件事。"""
        checked = 0
        for p, c in self.cache.items():
            old_txt = c["cc_text"]
            if html.unescape(old_txt) == old_txt:
                continue
            self.assertEqual(html.unescape(old_txt), c["flat_nl"],
                             f"{c['name']}：除实体解码外还有口径改动"
                             f"（旧 {len(old_txt)} 字 / 新 {len(c['flat_nl'])} 字）")
            checked += 1
        if checked == 0:
            self.skipTest("样本中无疑似实体，跳过差异断言")


slow_all(globals())

if __name__ == "__main__":
    unittest.main(verbosity=2)

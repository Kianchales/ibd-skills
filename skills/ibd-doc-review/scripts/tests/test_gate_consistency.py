#!/usr/bin/env python3
"""
test_gate_consistency.py — 门禁内建检查 与 独立脚本 的结论一致性

为什么要这个测试
----------------
`deliver_gate.py` 内建了一套检查（`check_styles` / 批注 / 修订），
而 `check_styles.py`、`check_annotations.py`、`check_revisions.py` 又各有一套。
**同一判据两套实现**，改一边不改另一边 → 用户按新模式跑得到旧结论。

这与 `author` 事故同类（schema 与执行器各改各的）。区别只是那次已经炸了。

为什么不是直接合并（B 方案的代价）
--------------------------------
实测：`check_styles.py` 用**正则扫原始 XML**且只返回 bool，门禁用 **ElementTree** 返回结构化数据；
两套解析引擎不同，合并等于重写一套。故先加本测试**锁住现状**，合并留作分阶段。

覆盖面
------
  1. 样式规范：独立脚本的「裸段落 / 空段落」计数 == 门禁 detail 里的同名字段
  2. 批注结构：独立脚本的批注条数 == 门禁「批注结构」的条数
  3. 修订计数：独立脚本的修订条数 == 门禁「修订计数」
  （三项任一不等即 FAIL —— 说明有人只改了一边）

运行：REVIEW_TESTS=all python scripts/tests/test_gate_consistency.py
"""
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from _tier import slow_all  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, "..", ".."))
SCRIPTS = os.path.join(PKG, "scripts")
STYLES = os.path.join(SCRIPTS, "check_styles.py")
ANN = os.path.join(SCRIPTS, "check_annotations.py")
REV = os.path.join(SCRIPTS, "check_revisions.py")
GATE = os.path.join(SCRIPTS, "deliver_gate.py")

_spec = importlib.util.spec_from_file_location("t_gate_cons", GATE)
dg = importlib.util.module_from_spec(_spec)
sys.modules["t_gate_cons"] = dg
_spec.loader.exec_module(dg)

# 样本从**包外**金样本清单取（清单含真实路径，不入包）——缺失即 SKIP
GOLDEN_DIR = os.environ.get("IBD_GOLDEN_DIR", "")


def _case(*names):
    mf = os.path.join(GOLDEN_DIR, "manifest.json")
    if not os.path.exists(mf):
        return ""
    cases = json.load(open(mf, encoding="utf-8"))["cases"]
    for c in cases:
        if any(n in c.get("name", "") for n in names):
            p = c.get("docx") or c.get("xlsx") or ""
            p = p if os.path.isabs(p) else os.path.join(GOLDEN_DIR, p)
            return p if os.path.exists(p) else ""
    return ""


SRC = _case("招股", "报告", "附注")
ANNEX = _case("批注")
REVED = _case("修订")


def run_script(script, args):
    p = subprocess.run([sys.executable, script] + args,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (p.stdout or "") + (p.stderr or "")


_GATE_CACHE = {}


def gate_item(docx, name):
    """取门禁某一项的 detail（不打印）。**按 (文件, 项) 缓存**——三个用例共用同一批文件，
    重复解析 10MB document.xml 是这条测试原先 10.5 秒的主因。"""
    key = (docx, name)
    if key not in _GATE_CACHE:
        if name == "样式规范":
            _GATE_CACHE[key] = dg.check_styles(docx, "招股书")
        elif name == "批注结构":
            dg.read_docx(docx)          # 走一遍统一读取，确保路径/存在性校验
            _GATE_CACHE[key] = dg.check_annotated_structure(docx, None)
        elif name == "修订计数":
            dg.read_docx(docx)
            _GATE_CACHE[key] = dg.check_revised(docx, None)[2]
        else:
            raise KeyError(name)
    return _GATE_CACHE[key]


@unittest.skipUnless(os.path.exists(SRC), "样本不存在")
class TestGateConsistency(unittest.TestCase):

    def test_style_counts_agree(self):
        """独立 check_styles 与门禁的「裸段落/空段落」必须同一口径。"""
        out = run_script(STYLES, ["--input", SRC, "--scenario", "招股书"])
        m_bare = re.search(r"(\d+)\s*个裸段落", out)
        m_empty = re.search(r"(\d+)\s*个空段落", out)
        self.assertIsNotNone(m_bare, "独立脚本未输出裸段落计数，输出格式可能已变：\n" + out[-400:])
        self.assertIsNotNone(m_empty, "独立脚本未输出空段落计数：\n" + out[-400:])

        _n, _ok, detail, _f = gate_item(SRC, "样式规范")
        g = re.search(r"裸\s*(\d+)\s*/\s*空\s*(\d+)", detail)
        self.assertIsNotNone(g, "门禁 detail 格式已变：%s" % detail)
        self.assertEqual((int(m_bare.group(1)), int(m_empty.group(1))),
                         (int(g.group(1)), int(g.group(2))),
                         "两套实现的裸段/空段计数不一致——有人只改了一边")

    @unittest.skipUnless(os.path.exists(ANNEX), "批注版样本不存在")
    def test_annotation_count_agrees(self):
        out = run_script(ANN, ["--input", ANNEX, "--json"])
        i = out.find("{")
        self.assertGreaterEqual(i, 0, "独立脚本未输出 JSON：\n" + out[-300:])
        import json
        n_standalone = json.loads(out[i:]).get("count") or json.loads(out[i:]).get("total")
        self.assertIsNotNone(n_standalone, "JSON 无 count/total 字段")

        _n, _ok, detail, _f = gate_item(ANNEX, "批注结构")
        m = re.search(r"(\d+)\s*条", detail)
        self.assertIsNotNone(m, "门禁 detail 格式已变：%s" % detail)
        self.assertEqual(int(m.group(1)), int(n_standalone),
                         "批注条数两套实现不一致")

    @unittest.skipUnless(os.path.exists(REVED), "修订稿样本不存在")
    def test_revision_count_agrees(self):
        out = run_script(REV, ["--input", REVED, "--json"])
        i = out.find("{")
        self.assertGreaterEqual(i, 0, "独立脚本未输出 JSON：\n" + out[-300:])
        import json
        j = json.loads(out[i:])
        n_standalone = j.get("count") or j.get("n")
        self.assertIsNotNone(n_standalone, "JSON 无 count/n 字段：%s" % list(j)[:8])

        _n, _ok, detail, _f = gate_item(REVED, "修订计数")
        m = re.search(r"ins\s*(\d+)", detail)
        self.assertIsNotNone(m, "门禁 detail 格式已变：%s" % detail)
        self.assertEqual(int(m.group(1)), int(n_standalone),
                         "修订条数两套实现不一致")


slow_all(globals())

if __name__ == "__main__":
    unittest.main(verbosity=2)

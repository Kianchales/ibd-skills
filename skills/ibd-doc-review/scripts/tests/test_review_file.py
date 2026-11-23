#!/usr/bin/env python3
"""
test_review_file.py — 单文件编排器（批次对用户不可见）

锁三条不变量（都是"用户只给一个文件"的前提）：
  1. **自动分批**：用户不传批号、不知道批数；系统按容量自行切
  2. **顺序与一致性**：乱序提交，输出仍按文档序、编号连续 F-01…、无批次字段残留
  3. **错误恢复**：有未完成批时**拒绝出结果**（exit 3），不产出"看起来完整"的报告

另测幂等（同批重复提交不重复计数）与跨批去重（同 anchor+title 只留一条）。
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, "..", ".."))
SCRIPT = os.path.join(PKG, "scripts", "review_file.py")
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def make_docx(path, n=70, para=None):
    def p(style, text):
        return (f'<w:p><w:pPr><w:pStyle w:val="{style}"/></w:pPr>'
                f'<w:r><w:t>{text}</w:t></w:r></w:p>')
    para = para or ("这是第%d段正文内容，用于验证自动分批、顺序合并与断点续跑是否成立，"
                    "段落长度需要超过四十个字符。")
    body = "".join(p("001", f"第{i}节 测试标题") + p("000", para % i) for i in range(1, n + 1))
    doc = ('<?xml version="1.0" encoding="UTF-8"?>'
           f'<w:document xmlns:w="{W}"><w:body>{body}</w:body></w:document>')
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", doc)


def run(args):
    p = subprocess.run([sys.executable, SCRIPT] + args,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


class TestReviewFile(unittest.TestCase):

    def setUp(self):
        self._d = tempfile.TemporaryDirectory()
        self.d = self._d.name
        self.addCleanup(self._d.cleanup)
        self.docx = os.path.join(self.d, "t.docx")
        make_docx(self.docx)

    RCPT = {"self": "未见异常", "cross_prev": "未见异常", "cross_next": "未见异常",
            "disclose": "未见异常", "caliber": "未见异常", "wording": "未见异常"}

    def findings(self, name, items):
        p = os.path.join(self.d, name)
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"findings": items, "receipt": self.RCPT}, f, ensure_ascii=False)
        return p

    def n_batches(self):
        st = json.load(open(os.path.join(self.d, "t_复核", ".review_state.json"), encoding="utf-8"))
        return len(st["batches"]), st

    # ---------- 1. 自动分批 ----------

    def test_auto_split_without_user_knowing(self):
        rc, out = run(["--input", self.docx])
        self.assertEqual(rc, 0, out)
        n, st = self.n_batches()
        self.assertGreater(n, 1, "70 段正文应自动切成多批")
        self.assertEqual(sum(b["n_prose"] for b in st["batches"]), 70, "分批不得丢段")
        # 用户面输出**不出现批次数**
        self.assertNotIn("共 3 批", out)
        self.assertNotIn("批次数", out)

    def test_status_does_not_leak_batch_numbers(self):
        """批次是内部细节：状态输出只说"还有几个处理单元"，不列 #N。"""
        run(["--input", self.docx])
        rc, out = run(["--input", self.docx, "--status"])
        self.assertEqual(rc, 0)
        self.assertNotIn("#1", out, "状态输出不得列出批次号")
        rc2, out2 = run(["--input", self.docx, "--status", "--verbose"])
        self.assertIn("#1", out2, "--verbose 才允许显示（调试用）")

    def test_level_changes_batch_cap(self):
        """四档 = 两个轴的有效组合：L1/L2 不逐字（60 段/批），L3/L4 逐字（30 段/批）。"""
        for lv, expect_min in (("L2", 2), ("L3", 3)):
            d2 = os.path.join(self.d, "lv_" + lv)
            rc, out = run(["--input", self.docx, "--out-dir", d2, "--level", lv, "--prepare"])
            self.assertEqual(rc, 0, out)
            st = json.load(open(os.path.join(d2, ".review_state.json"), encoding="utf-8"))
            self.assertGreaterEqual(len(st["batches"]), expect_min, lv)
            self.assertEqual(st["level"], lv)
            scope = [f for f in os.listdir(d2) if f.endswith("_scope.md")][0]
            txt = open(os.path.join(d2, scope), encoding="utf-8").read()
            self.assertIn(lv, txt, "声明单须写档名")
            if lv == "L3":
                self.assertIn("逐字", txt)

    def test_depth_alias_still_works(self):
        """旧参数 --depth read 仍可用，映射到 L3。"""
        rc, out = run(["--input", self.docx, "--depth", "read", "--prepare"])
        self.assertEqual(rc, 0, out)
        st = json.load(open(os.path.join(self.d, "t_复核", ".review_state.json"), encoding="utf-8"))
        self.assertEqual(st["level"], "L3")

    def test_no_financials_means_single_doc_review(self):
        """未给报表＝单件复核（降级）：不自动去别处找，且须明确告知不做跨文档勾稽。"""
        for name in ("1-4 报表.xlsx", "1-5 附注.docx"):
            with open(os.path.join(self.d, name), "wb") as f:
                f.write(b"PK\x03\x04")
        rc, out = run(["--input", self.docx, "--prepare"])
        self.assertEqual(rc, 0, out)
        self.assertIn("单件复核", out)
        st = json.load(open(os.path.join(self.d, "t_复核", ".review_state.json"), encoding="utf-8"))
        self.assertIsNone(st.get("financials"), "不得擅自采用同目录的报表")

    # ---------- 1b. --prepare 一条命令出全部中间件 ----------

    def test_prepare_produces_all_artifacts(self):
        """prepare 必须一次给出 paras/tables/full + 格式核对 + 指纹——否则 agent 仍会自建脚本。"""
        rc, out = run(["--input", self.docx, "--prepare"])
        self.assertEqual(rc, 0, out)
        d = os.path.join(self.d, "t_复核")
        for name in ("paras.json", "tables.json", "full.txt",
                     "format_check.md", "format_check.json", "_run.json"):
            self.assertTrue(os.path.exists(os.path.join(d, name)), f"缺 {name}")

    def test_prepare_counts_match_fixture(self):
        run(["--input", self.docx, "--prepare"])
        d = os.path.join(self.d, "t_复核")
        paras = json.load(open(os.path.join(d, "paras.json"), encoding="utf-8"))
        # 夹具 70 节标题 + 70 正文 = 140 段
        self.assertEqual(len(paras), 140)
        self.assertEqual([p["id"] for p in paras[:2]], ["P0001", "P0002"], "编号须连续可回溯")
        full = open(os.path.join(d, "full.txt"), encoding="utf-8").read().splitlines()
        self.assertEqual(len(full), len(paras), "full.txt 行数须与段数一致")

    def test_prepare_lists_missing_inputs(self):
        """缺材料不许只在 stderr 一闪：要落 pending_inputs.json，并进报告行动项。"""
        rc, out = run(["--input", self.docx, "--prepare"])
        self.assertEqual(rc, 0, out)
        p = os.path.join(self.d, "t_复核", "pending_inputs.json")
        self.assertTrue(os.path.exists(p), "未落 pending_inputs.json")
        data = json.load(open(p, encoding="utf-8"))
        self.assertTrue(any("勾稽" in d["check"] for d in data), data)
        self.assertTrue(all(d.get("need") and d.get("effect") for d in data), "须写清缺什么、影响什么")

    def test_prepare_records_fingerprint(self):
        run(["--input", self.docx, "--prepare"])
        st = json.load(open(os.path.join(self.d, "t_复核", "_run.json"), encoding="utf-8"))
        tools = [x["tool"] for x in st["steps"]]
        self.assertIn("check_content", tools, "prepare 必须留下格式核对的指纹")
        self.assertIn("review_file", tools, "prepare 自身也要记一步")

    def test_prepare_fingerprint_when_out_dir_elsewhere(self):
        """`--out-dir` 指到别处时，子进程也必须记到那处 —— 否则"真跑了"被判"没跑"。"""
        other = os.path.join(self.d, "elsewhere")
        rc, out = run(["--input", self.docx, "--out-dir", other, "--prepare"])
        self.assertEqual(rc, 0, out)
        st = json.load(open(os.path.join(other, "_run.json"), encoding="utf-8"))
        tools = [x["tool"] for x in st["steps"]]
        self.assertIn("check_content", tools, "子进程未把指纹写到 --out-dir")

    # ---------- 2. 顺序与一致性 ----------

    def test_out_of_order_commit_merges_in_document_order(self):
        n, st = self.n_batches() if run(["--input", self.docx])[0] == 0 else (0, None)
        # 反向提交：先最后一批，再第一批
        last, first = n, 1
        f_last = self.findings("a.json", [{"anchor": "尾部", "title": "后批问题", "advice": "建议"}])
        f_first = self.findings("b.json", [{"anchor": "开头", "title": "前批问题", "advice": "建议"}])
        self.assertEqual(run(["--input", self.docx, "--commit", str(last),
                              "--findings", f_last])[0], 0)
        self.assertEqual(run(["--input", self.docx, "--commit", str(first),
                              "--findings", f_first])[0], 0)
        # 补齐中间批
        for i in range(2, last):
            rc, _ = run(["--input", self.docx, "--commit", str(i),
                         "--findings", self.findings(f"e{i}.json", [])])
            self.assertEqual(rc, 0)
        out = os.path.join(self.d, "out.json")
        rc, msg = run(["--input", self.docx, "--finish", "--output", out])
        self.assertEqual(rc, 0, msg)
        data = json.load(open(out, encoding="utf-8"))
        titles = [f["title"] for f in data["findings"]]
        self.assertEqual(titles, ["前批问题", "后批问题"], "必须按文档序，不按提交先后")
        self.assertEqual([f["id"] for f in data["findings"]], ["F-01", "F-02"])
        self.assertFalse(any("_batch" in f for f in data["findings"]), "批次字段不得外泄")

    def test_dedup_across_batches(self):
        n, _ = self.n_batches() if run(["--input", self.docx])[0] == 0 else (0, None)
        dup = [{"anchor": "同一处", "title": "同一条", "advice": "建议"}]
        for i in range(1, n + 1):
            run(["--input", self.docx, "--commit", str(i),
                 "--findings", self.findings(f"d{i}.json", dup)])
        out = os.path.join(self.d, "o.json")
        rc, _ = run(["--input", self.docx, "--finish", "--output", out])
        self.assertEqual(rc, 0)
        data = json.load(open(out, encoding="utf-8"))
        self.assertEqual(data["n_findings"], 1, "同 anchor+title 只留一条")

    # ---------- 3. 错误恢复 ----------

    def test_finish_refused_when_batches_pending(self):
        run(["--input", self.docx])
        rc, msg = run(["--input", self.docx, "--finish"])
        self.assertEqual(rc, 3, msg)
        self.assertIn("未处理", msg)
        self.assertFalse(os.path.exists(os.path.join(self.d, "findings.json")),
                         "未完成时不得产出结果文件")

    def test_commit_rejects_missing_fields(self):
        """缺 advice/anchor 应当场拒收——不能等到 finish 才说"有 N 条没进报告"。"""
        run(["--input", self.docx])
        bad = self.findings("bad.json", [{"title": "只有标题"}])
        rc, out = run(["--input", self.docx, "--commit", "1", "--findings", bad])
        self.assertEqual(rc, 2, out)
        self.assertIn("advice", out)
        self.assertIn("anchor", out)
        _, st = self.n_batches()
        self.assertEqual(st["batches"][0]["status"], "pending", "被拒收时不得标记完成")

    def test_commit_without_receipt_rejected(self):
        """只交问题清单、不做节级表态 → 拒收（不能靠"没发现问题"含糊过去）。"""
        run(["--input", self.docx])
        p = os.path.join(self.d, "bare.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump([], f)
        rc, out = run(["--input", self.docx, "--commit", "1", "--findings", p])
        self.assertEqual(rc, 2, out)
        self.assertIn("receipt", out)

    def test_receipt_partial_rejected(self):
        run(["--input", self.docx])
        p = os.path.join(self.d, "half.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"findings": [], "receipt": {"self": "ok"}}, f, ensure_ascii=False)
        rc, out = run(["--input", self.docx, "--commit", "1", "--findings", p])
        self.assertEqual(rc, 2, out)
        self.assertIn("缺 5 项", out)

    def test_commit_idempotent(self):
        run(["--input", self.docx])
        f = self.findings("x.json", [{"anchor": "a", "title": "t", "advice": "g"}])
        run(["--input", self.docx, "--commit", "1", "--findings", f])
        run(["--input", self.docx, "--commit", "1", "--findings", f])   # 重复提交
        n, st = self.n_batches()
        self.assertEqual(len(st["batches"][0]["findings"]), 1, "重复提交不应累加")
        self.assertEqual(st["batches"][0]["status"], "done")

    def test_resume_after_partial(self):
        run(["--input", self.docx])
        n, _ = self.n_batches()
        run(["--input", self.docx, "--commit", "1",
             "--findings", self.findings("p.json", [{"anchor": "a", "title": "t", "advice": "g"}])])
        # 续跑：状态保留已完成的第 1 批
        run(["--input", self.docx])
        _, st2 = self.n_batches()
        self.assertEqual(st2["batches"][0]["status"], "done")
        self.assertEqual(st2["batches"][1]["status"], "pending")
        self.assertEqual(len(st2["batches"]), n, "续跑不得重新切批")


if __name__ == "__main__":
    unittest.main(verbosity=2)

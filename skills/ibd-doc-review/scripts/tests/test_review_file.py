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

    def findings(self, name, items):
        p = os.path.join(self.d, name)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False)
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

    # ---------- 2. 顺序与一致性 ----------

    def test_out_of_order_commit_merges_in_document_order(self):
        n, st = self.n_batches() if run(["--input", self.docx])[0] == 0 else (0, None)
        # 反向提交：先最后一批，再第一批
        last, first = n, 1
        f_last = self.findings("a.json", [{"anchor": "尾部", "title": "后批问题"}])
        f_first = self.findings("b.json", [{"anchor": "开头", "title": "前批问题"}])
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
        dup = [{"anchor": "同一处", "title": "同一条"}]
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

    def test_commit_idempotent(self):
        run(["--input", self.docx])
        f = self.findings("x.json", [{"anchor": "a", "title": "t"}])
        run(["--input", self.docx, "--commit", "1", "--findings", f])
        run(["--input", self.docx, "--commit", "1", "--findings", f])   # 重复提交
        n, st = self.n_batches()
        self.assertEqual(len(st["batches"][0]["findings"]), 1, "重复提交不应累加")
        self.assertEqual(st["batches"][0]["status"], "done")

    def test_resume_after_partial(self):
        run(["--input", self.docx])
        n, _ = self.n_batches()
        run(["--input", self.docx, "--commit", "1",
             "--findings", self.findings("p.json", [{"anchor": "a", "title": "t"}])])
        # 续跑：状态保留已完成的第 1 批
        run(["--input", self.docx])
        _, st2 = self.n_batches()
        self.assertEqual(st2["batches"][0]["status"], "done")
        self.assertEqual(st2["batches"][1]["status"], "pending")
        self.assertEqual(len(st2["batches"]), n, "续跑不得重新切批")


if __name__ == "__main__":
    unittest.main(verbosity=2)

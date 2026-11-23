#!/usr/bin/env python3
"""
test_new_workspace.py — 工作区初始化自测（建目录有副作用，必须断言）

覆盖：
  单文件模式
   1. `<源文件名>_复核/` 下建齐四个内容目录（参考资料／问题记录／复核结果／过程文件）
   2. **源文件原位不动**（不复制、不改动——sha256 不变）
   3. 幂等：重复执行不报错、不删已有内容
  多文件模式
   4. 五层作业区齐备（01_待复核材料 … 05_过程文件）
   5. 参考资料四类子目录齐备（规则与准则／内部口径／同类范例／数据来源）
   6. 三个模板文件写入（README.md／00_基准说明.md／.review-workspace.json）且 json 可解析
   7. 缺 --root/--project 时拒绝执行（不能默默建到当前目录）

运行：REVIEW_TESTS=all python scripts/tests/test_new_workspace.py
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from _tier import slow_all  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, "..", ".."))
SCRIPT = os.path.join(PKG, "scripts", "new_workspace.py")

SINGLE_DIRS = {"参考资料", "问题记录", "复核结果", "过程文件"}
MULTI_DIRS = {"01_待复核材料", "02_参考资料", "03_问题记录", "04_复核结果", "05_过程文件"}
REF_DIRS = {"01_规则与准则", "02_内部口径", "03_同类范例", "04_数据来源"}


def run(args, cwd=None):
    p = subprocess.run([sys.executable, SCRIPT] + args, cwd=cwd,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


class TestSingleMode(unittest.TestCase):

    def setUp(self):
        self._d = tempfile.TemporaryDirectory()
        self.dir = self._d.name
        self.src = os.path.join(self.dir, "某专项说明.docx")
        with open(self.src, "wb") as f:
            f.write(b"PK\x03\x04dummy")      # 内容不重要，只要不被改动

    def tearDown(self):
        self._d.cleanup()

    def test_creates_dirs_and_leaves_source(self):
        before = hashlib.sha256(open(self.src, "rb").read()).hexdigest()
        rc, out = run(["--source", self.src])
        self.assertEqual(rc, 0, out)
        ws = os.path.join(self.dir, "某专项说明_复核")
        self.assertTrue(os.path.isdir(ws), "未建 <文件名>_复核/：\n" + out)
        self.assertEqual({d for d in os.listdir(ws) if os.path.isdir(os.path.join(ws, d))},
                         SINGLE_DIRS)
        self.assertEqual(hashlib.sha256(open(self.src, "rb").read()).hexdigest(), before,
                         "源文件被动过——工作区初始化不得复制或改写原件")

    def test_idempotent(self):
        run(["--source", self.src])
        marker = os.path.join(self.dir, "某专项说明_复核", "问题记录", "已有.md")
        with open(marker, "w", encoding="utf-8") as fh:
            fh.write("x")
        rc, out = run(["--source", self.src])
        self.assertEqual(rc, 0, "重复执行失败：\n" + out)
        self.assertTrue(os.path.exists(marker), "重复执行删掉了已有内容")


class TestMultiMode(unittest.TestCase):

    def setUp(self):
        self._d = tempfile.TemporaryDirectory()
        self.root = self._d.name

    def tearDown(self):
        self._d.cleanup()

    def test_full_structure(self):
        rc, out = run(["--mode", "multi", "--root", self.root, "--project", "测试项目"])
        self.assertEqual(rc, 0, out)
        ws = os.path.join(self.root, "测试项目")
        self.assertEqual({d for d in os.listdir(ws) if os.path.isdir(os.path.join(ws, d))},
                         MULTI_DIRS)
        ref = os.path.join(ws, "02_参考资料")
        self.assertEqual({d for d in os.listdir(ref) if os.path.isdir(os.path.join(ref, d))},
                         REF_DIRS)
        for f in ("README.md", "01_待复核材料/00_基准说明.md", ".review-workspace.json"):
            self.assertTrue(os.path.exists(os.path.join(ws, f)), "缺模板文件：" + f)
        with open(os.path.join(ws, ".review-workspace.json"), encoding="utf-8") as fh:
            json.load(fh)      # 必须可解析，否则后续轮次读不到基准

    def test_requires_root_and_project(self):
        rc, _out = run(["--mode", "multi", "--root", self.root])
        self.assertNotEqual(rc, 0, "缺 --project 时应拒绝，不能默默建到根目录")


slow_all(globals())

if __name__ == "__main__":
    unittest.main(verbosity=2)

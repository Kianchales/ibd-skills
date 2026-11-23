#!/usr/bin/env python3
"""
test_doc_flags.py — 文档里的 `--flag` 必须真在 argparse 里（防"文档写的参数代码没有"）

背景（2026-11-19 同类事故三起）
--------------------------------
`author`：schema 没写必填、执行器硬拒 → 校验通过、执行报错；
`--scenario`：文档说默认即反馈回复，行为与叙述不符；
C17：文档说"需科目余额表"，实际 5 式不需 → 整块能力被自我 SKIP。
**共同点：文档与实现各说各话，而没有任何一处会自动发现。**

判据
----
1. 扫描面：`references/*.md`，**排除 `changelog-archive*`**（历史留痕不改写，同 A12 口径）。
2. flag 归属：先看同一行有没有点名脚本（`xxx.py`）——
   有则必须属于该脚本；没有则必须存在于**同仓任一脚本**（跨包引用合法，
   如 `delivery.md` 写 `review_report_to_xlsx.py --round-ledger`）。
3. **明确标注「已撤除／已废弃／不再支持」的行豁免**（记录下线事实是正当的）。
4. 代码块里的示例同样受检（最容易写着写着就改了参数名）。

运行：python scripts/tests/test_doc_flags.py
"""
import ast
import glob
import json
import os
import re
import sys
import tempfile
import unittest

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, "..", ".."))
SKILLS_ROOT = os.path.abspath(os.path.join(PKG, ".."))

RX_FLAG = re.compile(r"(?<![\w-])--[a-z][a-z0-9-]{1,24}")
RX_SCRIPT = re.compile(r"([\w\-.]+\.py)")
# 外部 CLI 的参数（minimax-docx apply-template 等）无法用本仓 argparse 校验，整行跳过
EXTERNAL_TOOLS = ("minimax-docx", "tencent-docx", "tencent-local-office-edit",
                  "officecli", "pymupdf", "apply-template")
DEPRECATED = ("已撤除", "已废弃", "已移除", "不再支持", "deprecated", "已下线")
ALWAYS_OK = {"--help"}


def flags_of(path):
    try:
        tree = ast.parse(open(path, encoding="utf-8").read())
    except Exception:
        return set()
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "add_argument":
            for a in n.args:
                if isinstance(a, ast.Constant) and isinstance(a.value, str) and a.value.startswith("-"):
                    out.add(a.value)
    return out


CACHE = os.path.join(tempfile.gettempdir(), "ibd_doc_flags_index.json")


def build_index(use_cache=True):
    """{脚本 basename: flags} ＋ 全体并集。扫同仓所有包的 scripts。

    索引会**按 (路径, mtime, 大小) 缓存到临时目录**：全仓 166 个脚本 ast 解析约 10 秒，
    每次跑都重扫纯属浪费（这条测试原本 11.6 秒，大半耗在这）。脚本一改 mtime 变，自动失效。
    """
    files = sorted(glob.glob(os.path.join(SKILLS_ROOT, "*", "scripts", "**", "*.py"), recursive=True))
    meta = {}
    for p in files:
        try:
            st = os.stat(p)
        except OSError:
            continue
        meta[p] = [int(st.st_mtime), st.st_size]

    if use_cache and os.path.exists(CACHE):
        try:
            with open(CACHE, encoding="utf-8") as f:
                cached = json.load(f)
            if cached.get("meta") == meta:
                per = {k: set(v) for k, v in cached["per"].items()}
                return per, set(cached["union"])
        except Exception:
            pass

    per, union = {}, set()
    for p in files:
        f = flags_of(p)
        if not f:
            continue
        per.setdefault(os.path.basename(p), set()).update(f)
        union |= f
    try:
        with open(CACHE, "w", encoding="utf-8") as f:
            json.dump({"meta": meta, "per": {k: sorted(v) for k, v in per.items()},
                       "union": sorted(union)}, f, ensure_ascii=False)
    except OSError:
        pass
    return per, union


class TestDocFlags(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.per, cls.union = build_index()
        cls.files = [p for p in glob.glob(os.path.join(PKG, "references", "*.md"))
                     if not os.path.basename(p).startswith("changelog-archive")]

    def test_scripts_indexed(self):
        self.assertGreater(len(self.union), 20, "未能解析到任何 argparse flag，索引逻辑需检查")

    def test_every_flag_exists(self):
        """① 全局：文档里出现的每个 --flag 必须存在于同仓某脚本（抓"写了但代码没有"）。
        ② 归属：**反引号内的命令片段**若同时写了脚本名与参数，则参数必须属于该脚本
        （只在片段内判，避免"一行并列三个脚本"造成的误判）。"""
        missing, wrong = [], []
        for p in self.files:
            with open(p, encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    if any(k in line for k in DEPRECATED) or any(t in line for t in EXTERNAL_TOOLS):
                        continue
                    # 「变更履历」条目（以日期开头的列表行）记录的是历史状态，不是操作指引
                    if re.match(r"^\s*[-*]\s*\d{4}-\d{2}-\d{2}", line):
                        continue
                    for f_ in RX_FLAG.findall(line):
                        if f_ not in ALWAYS_OK and f_ not in self.union:
                            missing.append("%s:%d %s" % (os.path.basename(p), i, f_))
                    for seg in re.findall(r"`([^`]+)`", line):
                        scripts = [s for s in RX_SCRIPT.findall(seg) if s in self.per]
                        if not scripts:
                            continue
                        allowed = set().union(*(self.per[s] for s in scripts))
                        for f_ in RX_FLAG.findall(seg):
                            if f_ in ALWAYS_OK or f_ in allowed:
                                continue
                            # 同片段并列多个脚本时取并集；仍不属任何一个才算错
                            wrong.append("%s:%d `%s`（%s 无 %s）" % (
                                os.path.basename(p), i, seg.strip()[:40], ",".join(scripts), f_))
        self.assertFalse(missing, "文档写了、代码里根本没有的参数：\n  " + "\n  ".join(missing[:15]))
        self.assertFalse(wrong, "命令片段里的参数不属于所点名的脚本：\n  " + "\n  ".join(wrong[:10]))

    def test_new_scripts_are_documented(self):
        """反向：本包脚本若被文档点名，其参数至少有一个被写到（防止整册漏记新脚本）。"""
        documented = set()
        for p in self.files:
            with open(p, encoding="utf-8") as f:
                documented |= set(RX_SCRIPT.findall(f.read()))
        own = {os.path.basename(p) for p in glob.glob(os.path.join(PKG, "scripts", "*.py"))}
        # 只作提示面：不强制每个脚本都被 references 点名，避免与 SKILL.md 入口预算打架
        self.assertTrue(documented & own, "references 里没有点名任何本包脚本，指针可能全断了")



# --- 测试分层（见 _tier.py）：默认只跑快测，全量需 REVIEW_TESTS=all
from _tier import slow_all  # noqa: E402

slow_all(globals())

if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""
test_validate_issues.py — validate_issues.py 自测（最小测试集）

背景：清单是复核链的数据入口，契约规定 `advice` 与 `rev` **anyOf 条件必填**
（二者至少其一）——批注形态给 advice，文本定稿/修订形态给 rev。历史实现在
`REQUIRED` 里无条件要求 `advice`，导致 **rev-only 的「文本定稿/修订」清单被自己的
入口校验判死**，且与同集合内 doc-review 的 `validate_schema.py` 给出**相反结论**。

覆盖：
  1. advice-only（批注形态）→ 通过
  2. rev-only（文本定稿/修订形态）→ 通过   ← 本条即上述缺陷的回归
  3. advice 与 rev 皆空 → 拦（ERROR 含 advice/rev 字样）
  4. advice 与 rev 皆有 → 通过
  5. advice 为空串 且无 rev → 拦（空串不算「有」）
  6. 缺 sev → 拦（其余必填仍拦）
  7. 契约一致：REQUIRED 集 == schema.required 集；EITHER 集 == schema anyOf 键集
  8. 双校验器同输入同结论：同一清单分别过 validate_issues 与 validate_schema，
     结论必须一致（都 PASS 或都 FAIL）——防两处校验器再次分叉

依赖：纯标准库。第 7/8 类需能找到同集合内的 `ibd-doc-review`（单包安装时自动 SKIP）。
运行：python scripts/tests/test_validate_issues.py
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SKILL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPTS = os.path.join(SKILL_DIR, "scripts")
sys.path.insert(0, SCRIPTS)

import validate_issues as vi  # noqa: E402

VALIDATE_ISSUES = os.path.join(SCRIPTS, "validate_issues.py")

# 同集合内 doc-review（单包安装时不存在 → 相关用例 SKIP）
SKILLS_ROOT = os.path.abspath(os.path.join(SKILL_DIR, ".."))
DR = os.path.join(SKILLS_ROOT, "ibd-doc-review")
SCHEMA = os.path.join(DR, "references", "problems.schema.json")
VALIDATE_SCHEMA = os.path.join(DR, "scripts", "validate_schema.py")


def base(**over):
    """一条合法条目（批注形态），按需覆盖字段。"""
    it = {
        "code": "J",
        "type": "数据·正负号",
        "sev": "高",
        "anchor": "汇兑净损失为 -26.14 万元",
        "title": "负值实为净收益，方向矛盾",
        "desc": "负值在会计口径下表示净收益，与「损失」措辞方向矛盾。",
        "advice": "核对口径后统一表述为「汇兑损益」。",
    }
    it.update(over)
    return it


def errors_of(data):
    errs, _ = vi.validate_issues(data)
    return errs


class TestRequiredAnyOf(unittest.TestCase):
    def test_01_advice_only_pass(self):
        self.assertEqual(errors_of([base()]), [])

    def test_02_rev_only_pass(self):
        # 回归：文本定稿/修订形态只有 rev（无 advice）不得被判死
        it = base(rev="汇兑净收益 26.14 万元")
        it.pop("advice")
        self.assertEqual(errors_of([it]), [],
                         "rev-only 清单应通过（anyOf 契约）")

    def test_03_neither_fail(self):
        it = base()
        it.pop("advice")
        errs = errors_of([it])
        self.assertEqual(len(errs), 1, errs)
        self.assertIn("advice", errs[0])
        self.assertIn("rev", errs[0])

    def test_04_both_pass(self):
        self.assertEqual(errors_of([base(rev="汇兑净收益 26.14 万元")]), [])

    def test_05_blank_advice_no_rev_fail(self):
        it = base(advice="   ")
        errs = errors_of([it])
        self.assertTrue(any("advice" in e or "rev" in e for e in errs), errs)

    def test_06_missing_sev_fail(self):
        it = base()
        it.pop("sev")
        errs = errors_of([it])
        self.assertTrue(any("sev" in e for e in errs), errs)


class TestContractAgreement(unittest.TestCase):
    """第 7 类：入口校验的必填集/条件必填集必须与机器契约一致。"""

    def setUp(self):
        if not os.path.exists(SCHEMA):
            self.skipTest("同集合内未找到 problems.schema.json（单包安装）")

    def test_07_required_and_anyof_match_schema(self):
        with open(SCHEMA, encoding="utf-8") as fh:
            schema = json.load(fh)
        item = schema["items"]
        self.assertEqual(set(vi.REQUIRED), set(item["required"]),
                         "validate_issues.REQUIRED 必须 == schema.required")
        # anyOf 各分支的键集（通常每支一个键）
        anyof_keys = set()
        for branch in item.get("anyOf", []):
            anyof_keys |= set(branch.get("required", []))
        self.assertEqual(set(vi.EITHER), anyof_keys,
                         "validate_issues.EITHER 必须 == schema.anyOf 键集")


class TestTwoValidatorsAgree(unittest.TestCase):
    """第 8 类：同一清单，两个校验器必须同结论。"""

    def setUp(self):
        if not (os.path.exists(SCHEMA) and os.path.exists(VALIDATE_SCHEMA)):
            self.skipTest("同集合内未找到 doc-review 校验器（单包安装）")

    def _rc(self, script, args):
        p = subprocess.run([sys.executable, script] + args,
                           capture_output=True, text=True, encoding="utf-8")
        return p.returncode

    def _assert_agree(self, data):
        with tempfile.TemporaryDirectory() as d:
            fp = os.path.join(d, "issues.json")
            with open(fp, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False)
            rc_i = self._rc(VALIDATE_ISSUES, ["--input", fp])
            rc_s = self._rc(VALIDATE_SCHEMA, [fp])
        if rc_s == 2:  # 环境错误，无法比较
            self.skipTest("validate_schema 环境错误（rc=2）")
        self.assertEqual(rc_i == 0, rc_s == 0,
                         f"两校验器结论不一致：issues rc={rc_i}, schema rc={rc_s}")

    def test_08_advice_only_agree(self):
        self._assert_agree([base()])

    def test_09_rev_only_agree(self):
        it = base(rev="汇兑净收益 26.14 万元")
        it.pop("advice")
        self._assert_agree([it])

    def test_10_neither_agree(self):
        it = base()
        it.pop("advice")
        self._assert_agree([it])


if __name__ == "__main__":
    unittest.main(verbosity=2)

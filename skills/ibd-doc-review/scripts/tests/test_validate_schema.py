#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_validate_schema.py — validate_schema.py 自测（纯标准库实现版）

背景：2026-09-18 该脚本由 `jsonschema` 库改为内置子集校验器，以兑现「校验脚本
全部 Python 3 标准库、解压即跑」的对外承诺（发布冒烟「零依赖审计」项拦下）。
本测试同时充当**等价性回归**——覆盖原库校验的全部语义分支。

覆盖：
  A. 通过路径（退出码 0）
     1. 全字段合法清单
     2. 仅必填 6 字段
     3. 空数组
     4. 边界合法值（code 单字母 / page=1）
  B. 结构违规（退出码 1）
     5. 顶层不是数组
     6. 条目不是对象
     7. 缺必填字段
     8. 额外字段（additionalProperties: false）
  C. 值域违规（退出码 1）
     9. type 自造标签（词表外）
    10. sev 词表外
    11. minLength 违例（空串）
    12. pattern 违例（code 小写 / 超长）
    13. minimum 违例（page=0）
    14. 字段类型错（sev 给数字 / page 给字符串）
  D. 环境错误（退出码 2）
    15. 文件不存在
    16. JSON 语法错误
  E. schema 守卫
    17. schema 含未支持关键字 → 显式报错，不静默放行
    18. schema 未定义 type 时不做类型断言
  F. CLI 契约
    19. --quiet 仅输出结果行
    20. 合法类型词边界：integer 不接受布尔

运行：python scripts/tests/test_validate_schema.py
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.abspath(os.path.join(TESTS_DIR, "..", ".."))
SCRIPT = os.path.join(SKILL_DIR, "scripts", "validate_schema.py")
SCRIPTS_DIR = os.path.join(SKILL_DIR, "scripts")

sys.path.insert(0, SCRIPTS_DIR)
import validate_schema as vs  # noqa: E402  （直接测单元，用于 schema 守卫用例）

VALID_TYPE = "数据·口径"
VALID_SEV = "高"


def valid_item(**overrides):
    """一条合法条目；overrides 用于按需制造违规。"""
    item = {
        "anchor": "合计金额为 1,234 万元",
        "type": VALID_TYPE,
        "sev": VALID_SEV,
        "title": "合计口径与明细不符",
        "desc": "该段合计与明细加总相差 12 万元。",
        "advice": "改为按明细加总口径列示。",
    }
    item.update(overrides)
    return item


class ValidateSchemaTest(unittest.TestCase):
    tmpdir = None

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp(prefix="test_validate_schema_")

    def run_script(self, payload, name="case.json", extra_args=None, raw=None):
        """写文件后跑脚本；payload 为 Python 对象，raw 为原样字符串。"""
        path = os.path.join(self.tmpdir, name)
        with open(path, "w", encoding="utf-8") as f:
            if raw is not None:
                f.write(raw)
            else:
                json.dump(payload, f, ensure_ascii=False)
        cmd = [sys.executable, SCRIPT, path] + (extra_args or [])
        return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")

    # ---------- A. 通过路径 ----------

    def test_01_full_fields(self):
        r = self.run_script([valid_item(author="郑", code="AB", rev="修订文本", page=3)])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("PASS", r.stdout)

    def test_02_required_only(self):
        r = self.run_script([valid_item()])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_03_empty_array(self):
        r = self.run_script([])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("PASS: 0 条", r.stdout)

    def test_04_boundary_values(self):
        r = self.run_script([valid_item(code="A", page=1)])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    # ---------- B. 结构违规 ----------

    def test_05_root_not_array(self):
        r = self.run_script({"anchor": "x"})
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("类型应为 array", r.stdout)
        self.assertNotIn("Traceback", r.stderr)

    def test_06_item_not_object(self):
        r = self.run_script(["不是对象"])
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("类型应为 object", r.stdout)

    def test_07_missing_required(self):
        item = valid_item()
        del item["advice"]
        r = self.run_script([item])
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("缺少必填字段 `advice`", r.stdout)

    def test_08_additional_property(self):
        r = self.run_script([valid_item(自造字段="x")])
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("不允许的额外字段", r.stdout)

    # ---------- C. 值域违规 ----------

    def test_09_enum_type(self):
        r = self.run_script([valid_item(type="数据·随便编的")])
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("不在词表内", r.stdout)

    def test_10_enum_sev(self):
        r = self.run_script([valid_item(sev="紧急")])
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("不在词表内", r.stdout)

    def test_11_min_length(self):
        r = self.run_script([valid_item(title="")])
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("minLength", r.stdout)

    def test_12_pattern(self):
        for bad in ("ab", "ABC"):
            with self.subTest(code=bad):
                r = self.run_script([valid_item(code=bad)])
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                self.assertIn("不匹配 pattern", r.stdout)

    def test_13_minimum(self):
        r = self.run_script([valid_item(page=0)])
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("minimum", r.stdout)

    def test_14_field_type_mismatch(self):
        r = self.run_script([valid_item(sev=1)])
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("类型应为 string", r.stdout)
        r2 = self.run_script([valid_item(page="第三页")])
        self.assertEqual(r2.returncode, 1, r2.stdout + r2.stderr)
        self.assertIn("类型应为 integer", r2.stdout)

    def test_20_integer_rejects_bool(self):
        """JSON Schema 语义：integer 不接受布尔（Python 里 bool 是 int 子类）。"""
        r = self.run_script([valid_item(page=True)])
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("类型应为 integer", r.stdout)

    # ---------- D. 环境错误 ----------

    def test_15_file_missing(self):
        cmd = [sys.executable, SCRIPT, os.path.join(self.tmpdir, "不存在.json")]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 2)
        self.assertIn("ENV-ERROR", r.stderr)

    def test_16_json_syntax_error(self):
        r = self.run_script(None, name="bad.json", raw='[{"anchor": "未闭合"')
        self.assertEqual(r.returncode, 2)
        self.assertIn("ENV-ERROR", r.stderr)

    # ---------- E. schema 守卫 ----------

    def test_17_unsupported_keyword_blocks(self):
        """schema 用了未实现的关键字 → 显式报错（不静默放行）。"""
        errs = vs.validate([], {"type": "array", "maxItems": 5})
        self.assertTrue(errs, "未支持关键字必须报错")
        self.assertIn("未支持的校验关键字", errs[0][1])

    def test_18_no_type_assertion_without_type(self):
        """schema 未定义 type 时不做类型断言，仅跑已给约束。"""
        errs = vs.validate("随便什么", {"minLength": 1})
        self.assertEqual(errs, [])

    # ---------- F. CLI 契约 ----------

    def test_19_quiet(self):
        r = self.run_script([valid_item(sev="紧急")], extra_args=["--quiet"])
        self.assertEqual(r.returncode, 1)
        self.assertNotIn("FAIL [", r.stdout)
        self.assertIn("FAIL:", r.stdout)

    def test_21_multiple_errors_sorted(self):
        """多条违规按路径排序输出，且逐条列出。"""
        payload = [valid_item(title=""), valid_item(sev="紧急")]
        r = self.run_script(payload)
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL: 2 处", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)

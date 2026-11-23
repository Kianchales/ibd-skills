#!/usr/bin/env python3
"""
test_contract_sync.py — 清单 schema 与执行器必填字段的一致性（防"两道门两个结论"）

背景（2026-11-19 实测）：同一份带 rev 的清单，`validate_schema.py` PASS，紧接着
`revise_docx.py` 抛 `ValueError: 条目缺必填字段 author` —— schema 没声明 author 必填，
而 `issue_numbering.assign_numbers` 硬性要求。**校验通过、执行报错**，最伤信任。

本测试把两者的必填集合钉在一起：任一侧单方面增删字段，这里立刻红。

运行：python scripts/tests/test_contract_sync.py
"""
import ast
import json
import os
import sys
import unittest

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, "..", ".."))
SCHEMA = os.path.join(PKG, "references", "problems.schema.json")
EXECUTOR = os.path.abspath(os.path.join(PKG, "..", "ibd-doc-annotate", "scripts", "issue_numbering.py"))


def schema_required():
    with open(SCHEMA, encoding="utf-8") as f:
        d = json.load(f)
    return set(d["items"]["required"])


def executor_required():
    """从 assign_numbers 里取出 `for f in (...)`: 的字段元组（静态读，不 import）。"""
    with open(EXECUTOR, encoding="utf-8") as f:
        src = f.read()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.target, ast.Name) and node.target.id == "f":
            it = node.iter
            if isinstance(it, (ast.Tuple, ast.List)):
                vals = [e.value for e in it.elts if isinstance(e, ast.Constant)]
                if vals:
                    return set(vals)
    return set()


@unittest.skipUnless(os.path.exists(EXECUTOR), "同仓执行器不存在（单包检出时跳过）")
class TestContractSync(unittest.TestCase):

    def test_executor_required_subset_of_schema(self):
        """**执行器要求的字段必须都在 schema 必填里**（反向不要求：schema 可更严，
        如 type/sev/desc 由 schema 把关、执行器只给显示兜底）。"""
        a, b = schema_required(), executor_required()
        self.assertTrue(b, "未能从执行器解析出必填字段，解析逻辑需更新")
        missing = sorted(b - a)
        self.assertFalse(
            missing,
            "执行器要求但 schema 未声明必填 → 会出现「schema PASS 但执行报错」：%s" % missing)

    def test_author_required(self):
        """author 必须在两侧都必填（2026-11-19 事故的回归点）。"""
        self.assertIn("author", schema_required())
        self.assertIn("author", executor_required())


if __name__ == "__main__":
    unittest.main(verbosity=2)

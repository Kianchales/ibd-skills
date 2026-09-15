#!/usr/bin/env python3
"""validate_schema.py —— 复核问题清单 JSON Schema 校验入口（C-分步第一步）。

用法：
    python validate_schema.py <problems.json>          # 校验单个清单文件
    python validate_schema.py <problems.json> --quiet  # 仅输出结果行

契约：
- schema 单一事实源 = references/problems.schema.json（语义源 = interface.md §3 + annotations.md §4）
- 返回码：0 = PASS；1 = FAIL（结构/词表非法）；2 = 环境错误（缺 jsonschema 库等）
- 本脚本只做结构 + 白名单校验；语义级检查（锚点可命中、数量卫生 ≤200/>400）仍由
  doc-annotate validate_issues.py / check_annotations.py 把关，不在此重复。
"""
import argparse
import json
import sys
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "references" / "problems.schema.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="复核问题清单 JSON Schema 校验")
    parser.add_argument("problems", help="问题清单 JSON 文件路径")
    parser.add_argument("--quiet", action="store_true", help="仅输出结果行")
    args = parser.parse_args()

    try:
        import jsonschema
    except ImportError:
        print("ENV-ERROR: 缺少 jsonschema 库（pip install jsonschema）", file=sys.stderr)
        return 2

    problems_path = Path(args.problems)
    if not problems_path.exists():
        print(f"ENV-ERROR: 文件不存在 {problems_path}", file=sys.stderr)
        return 2

    try:
        data = json.loads(problems_path.read_text(encoding="utf-8"))
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"ENV-ERROR: 读取/解析失败 {e}", file=sys.stderr)
        return 2

    validator_cls = jsonschema.validators.validator_for(schema)
    validator = validator_cls(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))

    if not errors:
        print(f"PASS: {len(data)} 条全部符合 schema（{SCHEMA_PATH.name}）")
        return 0

    for err in errors:
        path = "/".join(str(p) for p in err.absolute_path) or "<root>"
        if not args.quiet:
            print(f"FAIL [{path}] {err.message}")
    print(f"FAIL: {len(errors)} 处不符合 schema")
    return 1


if __name__ == "__main__":
    sys.exit(main())

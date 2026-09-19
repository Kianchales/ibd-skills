#!/usr/bin/env python3
"""validate_schema.py —— 复核问题清单 JSON Schema 校验入口（C-分步第一步）。

用法：
    python validate_schema.py <problems.json>          # 校验单个清单文件
    python validate_schema.py <problems.json> --quiet  # 仅输出结果行

契约：
- schema 单一事实源 = references/problems.schema.json（语义源 = interface.md §3 + annotations.md §4）
- 返回码：0 = PASS；1 = FAIL（结构/词表非法）；2 = 环境错误（文件缺失 / 读取解析失败）
- **零第三方依赖**（2026-09-18 改）：内置 JSON Schema 子集校验器取代 `jsonschema` 库，
  兑现「校验脚本全部 Python 3 标准库、解压即跑」的对外承诺。支持的关键字见 `SUPPORTED_KEYS`
  ——即本包 `problems.schema.json` 实际用到的全部校验语义关键字。schema 若出现未支持的关键字，
  本脚本**显式报错而非静默放行**（防「加了约束却没校验」的假绿）。
- 本脚本只做结构 + 白名单校验；语义级检查（锚点可命中、数量卫生 ≤200/>400）仍由
  doc-annotate validate_issues.py / check_annotations.py 把关，不在此重复。
"""
import argparse
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "references" / "problems.schema.json"

# 已实现的 schema 关键字：元数据（无校验语义）+ 校验关键字
META_KEYS = {"$schema", "$id", "title", "description"}
CHECK_KEYS = {"type", "required", "properties", "additionalProperties",
              "items", "enum", "minLength", "minimum", "pattern"}
SUPPORTED_KEYS = META_KEYS | CHECK_KEYS


def _json_type(value):
    """返回值的 JSON 类型名（bool 先于 int 判定）。"""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _type_ok(value, expected):
    """按 JSON Schema 的 type 词表判定（`integer` 不接受布尔）。"""
    actual = _json_type(value)
    if expected == "number":
        return actual in ("integer", "number")
    return actual == expected


def _join(path, key):
    return "%s/%s" % (path, key) if path else str(key)


def _display(path):
    return path or "<root>"


def validate(value, schema, path=""):
    """递归校验，返回 [(路径, 消息), ...]；空列表表示通过。"""
    unknown = set(schema) - SUPPORTED_KEYS
    if unknown:
        return [(_display(path),
                 "schema 含未支持的校验关键字 %s——本脚本不予校验，须先扩展 SUPPORTED_KEYS"
                 % ", ".join(sorted(unknown)))]

    expected = schema.get("type")
    if expected is not None and not _type_ok(value, expected):
        return [(_display(path), "类型应为 %s，实际为 %s" % (expected, _json_type(value)))]

    errors = []

    if "enum" in schema and value not in schema["enum"]:
        errors.append((_display(path),
                       "取值 %s 不在词表内（允许：%s）"
                       % (json.dumps(value, ensure_ascii=False),
                          " / ".join(str(x) for x in schema["enum"]))))

    if isinstance(value, str):
        min_len = schema.get("minLength")
        if min_len is not None and len(value) < min_len:
            errors.append((_display(path), "长度 %d 小于 minLength %d" % (len(value), min_len)))
        pattern = schema.get("pattern")
        if pattern is not None and re.search(pattern, value) is None:
            errors.append((_display(path),
                           "%s 不匹配 pattern %s" % (json.dumps(value, ensure_ascii=False), pattern)))

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        minimum = schema.get("minimum")
        if minimum is not None and value < minimum:
            errors.append((_display(path), "取值 %s 小于 minimum %s" % (value, minimum)))

    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append((_display(path), "缺少必填字段 `%s`" % key))
        props = schema.get("properties", {})
        for key, sub_value in value.items():
            if key in props:
                errors.extend(validate(sub_value, props[key], _join(path, key)))
            elif schema.get("additionalProperties") is False:
                errors.append((_join(path, key), "不允许的额外字段 `%s`" % key))

    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            errors.extend(validate(item, schema["items"], _join(path, index)))

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="复核问题清单 JSON Schema 校验")
    parser.add_argument("problems", help="问题清单 JSON 文件路径")
    parser.add_argument("--quiet", action="store_true", help="仅输出结果行")
    parser.add_argument("--json", action="store_true", help="输出结构化 JSON（供上层消费）")
    args = parser.parse_args()

    problems_path = Path(args.problems)
    if not problems_path.exists():
        print("ENV-ERROR: 文件不存在 %s" % problems_path, file=sys.stderr)
        return 2

    try:
        data = json.loads(problems_path.read_text(encoding="utf-8"))
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print("ENV-ERROR: 读取/解析失败 %s" % e, file=sys.stderr)
        return 2

    errors = sorted(validate(data, schema), key=lambda item: item[0])

    if args.json:
        print(json.dumps({
            "tool": "validate_schema", "target": str(problems_path),
            "verdict": "FAIL" if errors else "PASS",
            "error": len(errors), "warn": 0, "total": len(data),
            "issues": [{"level": "ERROR", "where": str(p), "msg": str(m)} for p, m in errors],
        }, ensure_ascii=False))
        return 1 if errors else 0
    if not errors:
        print("PASS: %d 条全部符合 schema（%s）" % (len(data), SCHEMA_PATH.name))
        return 0

    for path, message in errors:
        if not args.quiet:
            print("FAIL [%s] %s" % (path, message))
    print("FAIL: %d 处不符合 schema" % len(errors))
    return 1


if __name__ == "__main__":
    sys.exit(main())

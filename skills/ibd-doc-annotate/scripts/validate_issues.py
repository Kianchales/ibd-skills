#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
issues.json 入口校验器（G1 · 复核链数据入口早拦）

复核问题清单是复核链的数据入口，此前无 schema 校验——坏清单（字段缺/严重度非法/
非数组）要到注入/修订时或门禁终检才暴露。本模块在校验链最前端拦截：

  用法 1（独立 CLI，上游生成即校验）：
    python validate_issues.py --input issues.json
  用法 2（被 annotate_docx / annotate_pdf / revise_docx import，注入前自动校验）：
    from validate_issues import validate_issues
    errors, warnings = validate_issues(data)
    # errors 非空 → 打印并退出（不注入）；warnings 仅提示不拦截

校验级别设计（方法层只做结构校验，不做内容判断）：
  ERROR（拦截）—— 清单结构性坏，注入必失败或门禁必 FAIL：
    - 顶层非数组 / 空数组
    - 条目非 dict
    - 缺必填字段：anchor（定位核心）/ type（类型标签）/ sev（严重度）/
      title（标题行）/ desc（问题描述）/ advice（修改建议，批注正文 4 行结构必需）
    - sev 不在 {高, 中, 低}（严重度三档为格式层固定枚举，见 ibd-doc-review
      references/annotations.md；非内容判断）
  WARNING（提示不拦截）：
    - 缺 code：按既有裁定回退 U 前缀并提示（中文审查无 code 属正常）
    - code 非 [A-Z]{1,2} 形态：编号前缀将被截断/门禁前缀正则不匹配
    - 缺 author：批注作者归责缺失，总览/门禁 author 归责会受影响
    - code 重复：多条同前缀，编号序号仍会区分，但建议人工确认
  不校验（内容层职责，分别归下游）：
    - type 取值：类型词表外放行（方法层不做内容判断；词表合规由 check_annotations 门禁把关）
    - rev 字段：缺 rev 按 revise 链路「待人工」处理，属修订规范（ibd-doc-review references/revisions.md）

退出码：0 = 通过（仅 warnings）；2 = 存在 ERROR。
"""
import argparse
import json
import re
import sys

REQUIRED = ("anchor", "type", "sev", "title", "desc", "advice")
SEV_ALLOWED = ("高", "中", "低")

# 数量卫生阈值（细则 9：本地舒适 ≤200；云端协同红线前 400 触发拆分提示）
COUNT_LOCAL_HINT = 200
COUNT_SPLIT_HINT = 400


def _norm_title(t):
    """标题归一（供同源归并自检）：去家族子编号尾缀/序号括注/标点空白"""
    t = re.sub(r"[（(][0-9a-zA-Z一二三四五六七八九十]+[）)]\s*$", "", str(t or "").strip())
    t = re.sub(r"\s*[a-z]$", "", t)  # J-01a → J-01
    t = re.sub(r"[\s：:、，,。;；()（）\"'“”‘’]+", "", t)
    return t


def validate_issues(data):
    """校验问题清单。返回 (errors, warnings)，errors 非空即拦截。"""
    errors, warnings = [], []

    if not isinstance(data, list):
        return ["顶层必须是数组（每条为一个问题条目）"], []
    if not data:
        return ["清单为空——无可注入条目"], []

    seen_codes = {}
    seen_titles = {}
    for i, it in enumerate(data, 1):
        if not isinstance(it, dict):
            errors.append(f"第{i}条不是对象（类型 {type(it).__name__}）")
            continue
        for k in REQUIRED:
            v = it.get(k)
            if v is None or (isinstance(v, str) and not v.strip()):
                errors.append(f"第{i}条缺必填字段 `{k}`")
        sev = it.get("sev")
        if sev is not None and sev not in SEV_ALLOWED:
            errors.append(f"第{i}条 sev={sev!r} 不在严重度枚举 {{高,中,低}}")
        code = it.get("code")
        if code is None or not str(code).strip():
            warnings.append(f"第{i}条缺 code——将按既有裁定回退 U 前缀（编号/归责请留意）")
        else:
            code = str(code)
            if not re.match(r"^[A-Z]{1,2}$", code):
                warnings.append(f"第{i}条 code={code!r} 非 1-2 位大写字母——编号前缀可能被截断或门禁前缀正则不匹配")
            seen_codes.setdefault(code, []).append(i)
        if it.get("author") in (None, ""):
            warnings.append(f"第{i}条缺 author——批注作者归责缺失（总览/门禁 author 归责受影响）")
        # 同源归并自检（细则 9）：title 归一后收集，循环后统一报
        nt = _norm_title(it.get("title"))
        if nt:
            seen_titles.setdefault(nt, []).append(i)

    for code, idxs in seen_codes.items():
        if len(idxs) > 1:
            warnings.append(f"code={code} 出现于第 {idxs} 条——前缀重复，序号仍会区分但请人工确认是否同源")

    # 同源归并提示（细则 9：一条问题 = 一个根因；同源连锁应合并、位置内联 desc）
    for nt, idxs in seen_titles.items():
        if len(idxs) > 1:
            warnings.append(
                f"第 {idxs} 条 title 归一后相同——疑似同源未合并或应作家族子编号（J-01a/b）；"
                "按归并纪律：同根因多位置合一条、desc 内联位置清单，勿逐位置拆条"
            )

    # 数量卫生（细则 9：≤200 本地舒适；>400 拆分交付或再归并——拆/并不删条目）
    n = len(data)
    if n > COUNT_SPLIT_HINT:
        warnings.append(
            f"批注/条目数 {n} > {COUNT_SPLIT_HINT}——已超云端协同红线（Word ~500-700 线程 sync pause）前的建议上限："
            "请拆分交付（按节分册）或进一步同源归并，勿删条目"
        )
    elif n > COUNT_LOCAL_HINT:
        warnings.append(
            f"批注/条目数 {n} > {COUNT_LOCAL_HINT}——接近本地可读性上限：自查同源归并是否到位（同根因多位置应已合并且 desc 内联）"
        )

    return errors, warnings


def main():
    ap = argparse.ArgumentParser(description="issues.json 入口校验（复核问题清单结构早拦）")
    ap.add_argument("--input", required=True, help="复核问题清单 JSON（数组）")
    args = ap.parse_args()

    try:
        with open(args.input, encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON 解析失败：{e}")
        sys.exit(2)
    except OSError as e:
        print(f"[ERROR] 读取失败：{e}")
        sys.exit(2)

    errors, warnings = validate_issues(data)
    for w in warnings:
        print(f"[WARN] {w}")
    if errors:
        print(f"[ERROR] 未通过入口校验（{len(errors)} 项）：")
        for e in errors:
            print(f"  - {e}")
        sys.exit(2)
    total = len(data)
    print(f"✅ 入口校验通过：{total} 条，0 ERROR" + (f"，{len(warnings)} 条 WARN（见上）" if warnings else ""))
    sys.exit(0)


if __name__ == "__main__":
    main()

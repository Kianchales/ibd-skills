#!/usr/bin/env python3
"""声明单校验（`_scope.md`）——把"抽核要有正当理由"从纸面纪律变成可执行检查。

为什么需要
----------
`check-scope.md` 早已要求「抽核须写明抽了哪几节、为什么抽」，但**从没说哪些理由不成立**。
实践中最常见的抽核借口就是「量大／排期紧」——那是**缩范围**，不是降级，等于把风险留给签字人。
判据已改为只认两类理由，本脚本负责把它落到可执行层面。

判据
----
  1. 必含 `【本轮检查项声明】` 行，且四栏齐备：对象／深度／覆盖方式／分母
  2. 覆盖方式 ∈ {全文逐段, 圈定范围, 抽核}
  3. 分母须含数字（先定分母是分片的前提）
  4. 覆盖方式＝抽核时：
     - 必须有一行 `· 抽核：抽 <哪几节>，因为 <原因>`，且写明"抽了哪些"（含"第…节/页/表"等定位）
     - 原因须命中**正当理由白名单**（对象界定／技术不可读）；否则判 WARN 并提示人工确认
  5. 覆盖方式＝全文逐段时，不得出现 `· 抽核：` 行（**写了全文却实际抽核＝静默缩范围**）

用法
----
    python scripts/check_scope_decl.py --file 某文件_20261120_v1_scope.md [--json]
    python scripts/check_scope_decl.py --file x.md --strict   # WARN 也算不通过（默认只提示）

退出码：0 通过（WARN 默认不阻断）／2 有 ERROR／1 --strict 下有 WARN
"""
import argparse
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HDR = re.compile(r"【本轮检查项声明】")
COVER = re.compile(r"覆盖方式[：:]\s*([^｜|\n]+)")
MODE_OK = ("全文逐段", "圈定范围", "抽核")

# 正当理由白名单：只有这两类才成立；「量大／时间紧／排期赶」不在其中
OK_REASON = [
    re.compile(r"不属于本轮|不在本轮|对象界定|范围本身"),
    re.compile(r"技术(上)?不可读|缺件|加密|无底稿|无法打开|损坏"),
]
BAD_REASON = re.compile(r"量大|时间(紧|不足|不允许)|排期|赶进度|人手|先看重点|抽样看")

LOCATE = re.compile(r"第[一二三四五六七八九十百\d]+[节章页表项]|§|附件|表\s*\d+")


def check(text):
    errs, warns, info = [], [], {}
    if not HDR.search(text):
        errs.append("缺「【本轮检查项声明】」行——声明单没写成约定格式")
        return errs, warns, info

    line = next((ln for ln in text.split("\n") if HDR.search(ln)), "")
    for field in ("对象", "深度", "覆盖方式", "分母"):
        if not re.search(field + r"[：:]", line):
            errs.append(f"声明行缺「{field}」栏")
        else:
            info[field] = re.search(field + r"[：:]\s*([^｜|]+)", line).group(1).strip()

    m = COVER.search(line)
    if not m:
        errs.append("未能解析「覆盖方式」取值")
        return errs, warns, info
    mode = m.group(1).strip()
    info["覆盖方式"] = mode
    if mode not in MODE_OK:
        errs.append(f"覆盖方式「{mode}」不在 {list(MODE_OK)} 中")
        return errs, warns, info

    den = info.get("分母", "")
    if not re.search(r"\d", den):
        errs.append("分母未给数字——先定分母再切批，否则无法判断抽核比例")

    has_sampling = re.search(r"·?\s*抽核[：:]\s*(.+)", text)
    if mode == "全文逐段":
        if has_sampling:
            errs.append("覆盖方式写「全文逐段」却出现「抽核」说明——**静默缩范围**，比抽核本身更严重")
    elif mode == "抽核":
        if not has_sampling:
            errs.append("覆盖方式为「抽核」但缺「· 抽核：抽…，因为…」行")
        else:
            body = has_sampling.group(1)
            info["抽核"] = body.strip()
            if not re.search(r"抽", body) or not LOCATE.search(body):
                errs.append("抽核未写明**抽了哪些**（须有「第X节/页/表」类定位）")
            reason = re.split(r"因为|原因[：:]", body)[-1].strip()
            info["理由"] = reason
            if BAD_REASON.search(reason):
                warns.append(f"抽核理由属「量大/时间紧」一类，**不是正当理由**（那是缩范围）：{reason}")
            elif not any(rx.search(reason) for rx in OK_REASON):
                warns.append(f"抽核理由不在正当理由白名单（对象界定／技术不可读），需人工确认：{reason}")
    return errs, warns, info


def main():
    ap = argparse.ArgumentParser(description="声明单（_scope.md）校验：抽核须有正当理由")
    ap.add_argument("--file", required=True, help="声明单存档文件（*_scope.md）")
    ap.add_argument("--json", action="store_true", help="输出结构化 JSON")
    ap.add_argument("--strict", action="store_true", help="WARN 也算不通过")
    a = ap.parse_args()

    if not os.path.isfile(a.file):
        print(f"[ERROR] 文件不存在：{a.file}")
        return 2
    with open(a.file, encoding="utf-8") as f:
        text = f.read()

    errs, warns, info = check(text)
    verdict = "FAIL" if errs else ("WARN" if warns else "PASS")
    if a.json:
        print(json.dumps({"tool": "check_scope_decl", "target": a.file,
                          "verdict": verdict, "error": len(errs), "warn": len(warns),
                          "issues": ([{"level": "ERROR", "msg": e} for e in errs]
                                     + [{"level": "WARN", "msg": w} for w in warns]),
                          "data": info}, ensure_ascii=False))
    else:
        print(f"=== 声明单：{os.path.basename(a.file)} ===")
        for k, v in info.items():
            print(f"  {k}：{v}")
        for e in errs:
            print(f"  [ERROR] {e}")
        for w in warns:
            print(f"  [WARN] {w}")
        print(f"  => {verdict}")

    if errs:
        return 2
    if warns and a.strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""C-Q 机械勾稽（只读 .xlsx，不需科目余额表）。

能做什么
--------
    ① 资产总计 = 负债合计 + 权益合计
    ② 归母权益 + 少数股东权益 = 权益合计
    ③ 净利润 = 归母净利润 + 少数股东损益
    ④ 利润总额 - 所得税费用 = 净利润
    ⑤ 期末现金及现金等价物 = 期初 + 净增加额
    ⑥ 货币资金 - 期末现金及现金等价物 = 受限资金 + 应计利息（可传附注受限额比对）

为什么需要它
------------
C17 五类勾稽里的这六式，**只靠申报报表 xlsx 就能算**，不必等科目余额表。实测某科创板
项目：五项全平，但第⑥式在 2023 年差 100,000,000.00 元整——报表自洽、附注与现金流口径
打架，这类问题人眼极难发现。

行名会变，怎么办
----------------
内置一套常见行名别名（正则），并用 `--map <json>` 允许整表覆盖：值是正则列表，
键固定为下面 13 个要素名（TOTAL_ASSETS／TOTAL_LIAB／EQUITY／PARENT_EQUITY／MINORITY
／NI／NI_PARENT／NI_MINORITY／TP／TAX／CF_END／CF_BEG／CF_INC／CASH）。
自家报表若行名特殊，传一份 map 即可，无需改代码。

用法
----
    python scripts/check_cq.py --xlsx <报表.xlsx> [--scope 合并|母公司]
                              [--map my_alias.json] [--restr "a,b,c,d"]
                              [--out 报告.md] [--json]

    --restr   附注「受限资金明细」各期合计（按报表列顺序，逗号分隔）；给了才做第⑥式比对
    退出码    0=全平 / 1=有不平 / 2=用法或解析失败
"""
import argparse
import datetime
import json
import re
import sys

import openpyxl

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

TOL = 0.01

# 要素 → 行名候选正则（默认别名；--map 可整表覆盖）
ALIASES = {
    "TOTAL_ASSETS": [r"^资产总计", r"^资产合计"],
    "TOTAL_LIAB": [r"^负债合计"],
    "EQUITY": [r"^(股东|所有者)权益(合计)?$"],
    "PARENT_EQUITY": [r"^归属于母公司(股东|所有者)权益(合计)?$", r"^归属母公司(股东|所有者)权益"],
    "MINORITY": [r"^少数股东权益$"],
    "NI": [r"净利润.*净亏损", r"^[一二三四五六七八九十]+、\s*净利润"],
    "NI_PARENT": [r"归属于母公司(股东)?的净利润", r"归属于母公司股东的净利润"],
    "NI_MINORITY": [r"少数股东损益"],
    "TP": [r"利润总额"],
    "TAX": [r"所得税费用"],
    "CF_END": [r"期末现金及现金等价物余额"],
    "CF_BEG": [r"期初现金及现金等价物余额"],
    "CF_INC": [r"现金及现金等价物净增加额"],
    "CASH": [r"^货币资金$"],
}

DATE_PAT = [
    re.compile(r"^\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?$"),          # 2026-06-30 / 2026年6月30日
    re.compile(r"^\d{4}年\d{1,2}(?:[-—~至]\d{1,2})?月(?:末)?$"),   # 2026年1-6月 / 2026年6月末
    re.compile(r"^\d{4}年度?$"),                                     # 2025年度 / 2025年
    re.compile(r"^\d{4}[-/]\d{1,2}$"),                              # 2026-06
    re.compile(r"^(本|上)(报告)?期(末)?$|^年初至报告期末$|^期末$|^期初$"),
    re.compile(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}$"),
]


def to_num(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "").replace("，", "")
    if not s or s in ("-", "—", "－", "/"):
        return None
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    try:
        x = float(s)
    except ValueError:
        return None
    return -x if neg else x


def as_period(v):
    """把表头单元格解析成期间标签；不能识别返回 None。"""
    if isinstance(v, (datetime.datetime, datetime.date)):
        return v.strftime("%Y-%m-%d")
    if isinstance(v, (int, float)):
        n = float(v)
        if 30000 <= n <= 60000:            # Excel 日期序列号
            d = datetime.date(1899, 12, 30) + datetime.timedelta(days=int(n))
            return d.strftime("%Y-%m-%d")
        return None
    s = str(v or "").strip()
    if not s:
        return None
    for p in DATE_PAT:
        if p.match(s):
            return s
    return None


def sheet_rows(ws):
    """返回 (periods, {行名: [值...]}, 列起点)。列起点 = 第一列数据（跳过 项目/附注 列）。"""
    raw = list(ws.iter_rows(values_only=True))
    hdr_i, cols = None, []
    for i, r in enumerate(raw[:12]):
        found = [(j, as_period(c)) for j, c in enumerate(r) if as_period(c)]
        if len(found) >= 2:
            hdr_i = i
            cols = found
            break
    if hdr_i is None:
        return [], {}, 0
    periods = [p for _j, p in cols]
    start = cols[0][0]
    idxs = [j for j, _p in cols]
    table = {}
    for r in raw[hdr_i + 1:]:
        lab = str(r[0] or "").strip()
        if not lab:
            continue
        vals = []
        for j in idxs:
            vals.append(to_num(r[j]) if j < len(r) else None)
        if not any(v is not None for v in vals):
            continue
        table.setdefault(lab, vals)
    return periods, table, start


def find(table, key, aliases):
    pats = aliases.get(key) or []
    for lab, vals in table.items():
        for p in pats:
            if re.search(p, lab):
                return lab, vals
    return None, None


def load(path, scope, aliases):
    wb = openpyxl.load_workbook(path, data_only=True)
    names = [n for n in wb.sheetnames if scope in n]
    if not names:
        raise SystemExit(f"[错误] 找不到含「{scope}」的工作表；现有：{wb.sheetnames}")

    def pick(*keys, allow_cont=False):
        """按名字优先精确、再包含匹配；正表匹配时排除「（续）」页，否则会被续页抢先。"""
        for k in keys:
            for n in names:
                if n == k or n == scope + k:
                    return wb[n]
            for n in names:
                if k in n and (allow_cont or "续" not in n):
                    return wb[n]
        return None

    bs1 = pick("资产负债表（续）", "资产负债表(续)", "资产负债表续", allow_cont=True)
    bs0 = pick("资产负债表")
    is_ = pick("利润表")
    cf = pick("现金流量表")
    if bs0 is None or is_ is None or cf is None:
        raise SystemExit("[错误] 缺少 资产负债表／利润表／现金流量表 之一")

    periods, t0, _ = sheet_rows(bs0)
    t1 = sheet_rows(bs1)[1] if bs1 is not None else {}
    bs = dict(t1)
    bs.update(t0)                      # 表头页优先，续页补充负债与权益
    _, ti, _ = sheet_rows(is_)
    _, tc, _ = sheet_rows(cf)
    return periods, bs, ti, tc


def main():
    ap = argparse.ArgumentParser(description="C-Q 机械勾稽（只读 xlsx）")
    ap.add_argument("--xlsx", required=True, help="申报财务报表 xlsx")
    ap.add_argument("--scope", default="合并", choices=["合并", "母公司"])
    ap.add_argument("--map", dest="mapfile", help="行名别名 JSON（键为要素名，值为正则列表）")
    ap.add_argument("--restr", help="附注受限资金各期合计，逗号分隔（按报表列顺序）")
    ap.add_argument("--accrued", help="附注应计利息各期金额，逗号分隔（货币资金含应计利息时必传，否则⑥式会误报）")
    ap.add_argument("--out", help="把 markdown 报告写到该路径")
    ap.add_argument("--json", action="store_true", help="输出结构化 JSON")
    a = ap.parse_args()

    aliases = {k: list(v) for k, v in ALIASES.items()}
    if a.mapfile:
        with open(a.mapfile, encoding="utf-8") as f:
            custom = json.load(f)
        for k, v in custom.items():
            if k in aliases:
                aliases[k] = v if isinstance(v, list) else [v]
        unknown = [k for k in custom if k not in aliases]
        if unknown:
            print(f"[提示] map 中未知要素已忽略：{unknown}", file=sys.stderr)

    periods, bs, ti, tc = load(a.xlsx, a.scope, aliases)
    n = len(periods)
    if n == 0:
        raise SystemExit("[错误] 未能从表头解析出期间列（需日期或 Excel 序列号）")

    got = {k: find(bs, k, aliases) for k in
           ("TOTAL_ASSETS", "TOTAL_LIAB", "EQUITY", "PARENT_EQUITY", "MINORITY", "CASH")}
    got.update({k: find(ti, k, aliases) for k in
                ("NI", "NI_PARENT", "NI_MINORITY", "TP", "TAX")})
    got.update({k: find(tc, k, aliases) for k in ("CF_END", "CF_BEG", "CF_INC")})

    def v(k):
        return got[k][1]

    # 母公司口径是单一主体，没有少数股东与"归母"概念 → ②③ 不适用，不是缺行
    single = (a.scope == "母公司")
    needed = ["TOTAL_ASSETS", "TOTAL_LIAB", "EQUITY", "CASH",
              "NI", "TP", "TAX", "CF_END", "CF_BEG", "CF_INC"]
    if not single:
        needed += ["PARENT_EQUITY", "MINORITY", "NI_PARENT", "NI_MINORITY"]
    missing = [k for k in needed if got[k][1] is None]
    if missing:
        print("[错误] 以下要素未找到对应行（可用 --map 覆盖行名）：" + "、".join(missing))
        raise SystemExit(2)

    checks = [
        ("① 资产总计 ＝ 负债合计 ＋ 权益合计",
         [v("TOTAL_ASSETS")[i] - (v("TOTAL_LIAB")[i] + v("EQUITY")[i]) for i in range(n)]),
    ]
    if not single:
        checks += [
            ("② 归母权益 ＋ 少数股东权益 ＝ 权益合计",
             [v("PARENT_EQUITY")[i] + v("MINORITY")[i] - v("EQUITY")[i] for i in range(n)]),
            ("③ 净利润 ＝ 归母净利润 ＋ 少数股东损益",
             [v("NI_PARENT")[i] + v("NI_MINORITY")[i] - v("NI")[i] for i in range(n)]),
        ]
    checks += [
        ("④ 利润总额 － 所得税费用 ＝ 净利润",
         [v("TP")[i] - v("TAX")[i] - v("NI")[i] for i in range(n)]),
        ("⑤ 期末现金等价物 ＝ 期初 ＋ 净增加额",
         [v("CF_BEG")[i] + v("CF_INC")[i] - v("CF_END")[i] for i in range(n)]),
    ]

    lines, bad = [], 0
    L = lines.append
    L("# C-Q 机械勾稽")
    L("")
    L(f"- 文件：{a.xlsx}　口径：{a.scope}")
    L(f"- 期间：{' ／ '.join(periods)}")
    L("")
    L(f"## 一、勾稽式（{len(checks)} 项{'，母公司口径无少数股东，②③ 不适用' if single else ''}）")
    L("")
    L("| 勾稽式 | 结果 |")
    L("|---|---|")
    detail = []
    for name, diffs in checks:
        off = [(periods[i], diffs[i]) for i in range(n)
               if diffs[i] is not None and abs(diffs[i]) > TOL]
        if off:
            bad += len(off)
            L("| %s | ❌ %s |" % (name, "；".join(f"{p} 差 {d:,.2f}" for p, d in off)))
            for p, d in off:
                detail.append({"check": name, "period": p, "diff": d})
        else:
            L(f"| {name} | ✅ 全平（{n} 期） |")
    L("")
    L("## 二、货币资金 ↔ 现金及现金等价物")
    L("")
    L("| 期间 | 货币资金 | 期末现金等价物 | 差额 |" + (" 附注受限合计 | 差 |" if a.restr else ""))
    L("|---|---|---|---|" + ("---|---|" if a.restr else ""))
    restr = [to_num(x) for x in a.restr.split(",")] if a.restr else None
    accrued = [to_num(x) for x in a.accrued.split(",")] if a.accrued else None
    if restr and not accrued:
        print("[提示] 未传 --accrued：若货币资金含应计利息，⑥式差额会偏大（本轮按 0 计）",
              file=sys.stderr)
    if restr and len(restr) != n:
        print(f"[警告] --restr 给了 {len(restr)} 个数，报表 {n} 期；按较短者比对", file=sys.stderr)
    gap_issue = 0
    for i in range(n):
        gap = v("CASH")[i] - v("CF_END")[i]
        row = f"| {periods[i]} | {v('CASH')[i]:,.2f} | {v('CF_END')[i]:,.2f} | {gap:,.2f} |"
        if restr and i < len(restr) and restr[i] is not None:
            acc = accrued[i] if (accrued and i < len(accrued) and accrued[i] is not None) else 0.0
            d = gap - restr[i] - acc
            if abs(d) > TOL:
                gap_issue += 1
                row += f" {restr[i]:,.2f} | **{d:,.2f}** ❌ |"
                detail.append({"check": "⑥ 货币资金差额 vs 附注受限", "period": periods[i], "diff": d})
            else:
                row += f" {restr[i]:,.2f} | 0.00 ✅ |"
        L(row)
    if gap_issue:
        L("")
        L(f"> ❌ **{gap_issue} 期**的货币资金与现金等价物差额，与附注受限合计不符——须核受限明细是否漏列、")
        L("> 或「可随时支付」口径是否少计、或存在整笔跨期串户。")
    L("")
    L("## 三、结论")
    L("")
    total_bad = bad + gap_issue
    L(f"{'✅ 全平' if total_bad == 0 else '❌ %d 处不平（明细见上）' % total_bad}")

    md = "\n".join(lines)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(md)
    if a.json:
        print(json.dumps({"periods": periods, "bad": total_bad, "detail": detail,
                          "rows": {k: got[k][0] for k in got}}, ensure_ascii=False, indent=1))
    else:
        print(md)
    raise SystemExit(0 if total_bad == 0 else 1)


if __name__ == "__main__":
    main()

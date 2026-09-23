#!/usr/bin/env python3
"""fix_volume_case_by_segment.py — 以「### 案批次」案节为**单一事实源**校正分卷来源案归属

背景
    分卷（P 系列 3 卷 ＋ 体例域 2 卷）在每个案的条目之前都有锚点行
    `### 案批次：<案名>（AN00xx）`（实测 86 个 = 各向 43 案，覆盖全部条目）。
    先前 `backfill_volume_refs.py` 用「5-gram 相似度 ＋ 案名」推断来源案（自动判定 97.6% 的 TBD），
    与案节锚点交叉校验：**一致 398 ／ 冲突 46 ／ 无标注 272**（一致率 89.6%）。

    本脚本以**案节锚点为准**做校正：
      · 冲突块：改「来源案」标注为案节案名，并把该块内**已被错号替换**的 `-AN<旧号>-` 统一改为案节号
      · 无标注块：按案节补「来源案」标注 ＋ 回填块内剩余 TBD 占位编号
      · 案节以外的文件头（卷首说明/登记表）不擅自改，单独报告

用法
    python fix_volume_case_by_segment.py --methods-root <工作区根> [--apply] [--json]
"""
import argparse
import collections
import io
import json
import os
import re
import sys

import os as _lo, sys as _ls
_ls.path.insert(0, _lo.path.dirname(_lo.path.abspath(__file__)))
from _lib.layout import METHODS_NAME, VOLUME_NAME, STATE_NAME, CASE_INDEX_TABLE
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RX_MARK = re.compile(r"(?m)^(### 案批次[:：][^\n]*)\n")   # 捕获**整行**（含 ### 前缀），防重建丢前缀
RX_CASE = re.compile(r"案批次[:：]\s*([^\n（(]+?)\s*(?:[（(]\s*(AN\d{4})\s*[)）])?\s*$")
RX_EID = re.compile(r"^([A-Z]{1,3}-\d{6})")
RX_TBD = re.compile(r"(?<![A-Za-z-])([SPL]{1,2})-TBD-(\d{2})")
RX_TAG = re.compile(r"\*\*来源案\*\*：([^（(]+)[（(](AN\d{4})[)）]")

# 槽位：行首可选 `- ` ＋ 已知字段名（可选加粗）＋ 全/半角冒号。白名单防误匹配正文列表项。
# 2026-09-19 放宽：原仅 `- **xxx**：`，漏掉 160 块（`**语用**：`／`- 语用：` 等无 `- ` 或无加粗形态）。
RX_SLOT = re.compile(r"(?m)^(- )?((?:\*\*)?(?:%s)(?:\*\*)?[：:])" % \
    ("来源案|语用|方法|规则要点|原文实证|适用场景|互见|边界条件|句式模板|投行语言特征"
     "|可复用结论|对照锚点|本案实证|规则|实证|结论|锚点|场景|模板|特征|边界"))
RX_ANREF = re.compile(r"(?<![A-Za-z-])([SPLIF]{1,2})-AN(\d{4})-(\d{2})")


def main():
    ap = argparse.ArgumentParser(description="按案节校正分卷来源案与 TBD")
    ap.add_argument("--methods-root", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    root = os.path.abspath(a.methods_root)
    md = os.path.join(root, METHODS_NAME) if os.path.isdir(os.path.join(root, METHODS_NAME)) else root
    vol = os.path.join(md, VOLUME_NAME)
    if not os.path.isdir(vol):
        sys.stderr.write("[MISS] %s\n" % vol)
        return 3

    idx = os.path.join(os.path.dirname(md), STATE_NAME, CASE_INDEX_TABLE)
    an = {}
    t = io.open(idx, encoding="utf-8", errors="replace").read()
    for m in re.finditer(r"(?m)^\| ([^|]{2,10}?) \| (AN\d{4}) \|", t):
        an[m.group(1).strip()] = m.group(2)
    for m in re.finditer(r"(?m)^\| (AN\d{4}) \| ([^|]{2,10}?) \|", t):
        an[m.group(2).strip()] = m.group(1)

    stat = collections.Counter()
    head_tbd = 0
    for fn in sorted(os.listdir(vol)):
        if not fn.endswith(".md"):
            continue
        p = os.path.join(vol, fn)
        raw = io.open(p, "rb").read().decode("utf-8")
        parts = RX_MARK.split(raw)
        head = parts[0]
        head_tbd += len(RX_TBD.findall(head))
        out = [head]
        for i in range(1, len(parts), 2):
            mark = parts[i]
            seg = parts[i + 1] if i + 1 < len(parts) else ""
            mcase = RX_CASE.search(mark)
            nm = (mcase.group(1).strip() if mcase else "")
            an_no = an.get(nm)
            if not an_no:
                out += [mark + chr(10), seg]
                stat["UNKNOWN_CASE"] += 1
                continue
            n_seg = len(RX_TBD.findall(seg))
            if n_seg:
                seg = RX_TBD.sub(lambda mm: "%s-%s-%s" % (mm.group(1), an_no, mm.group(2)), seg)
                stat["TBD_SEG"] += n_seg
            segs = re.split(r"(?m)^(### )", seg)
            newseg = [segs[0]]
            for j in range(1, len(segs), 2):
                b = segs[j + 1] if j + 1 < len(segs) else ""
                m = RX_EID.match(b)
                if not m:
                    newseg += [segs[j], b]
                    continue
                nb = b
                tag = RX_TAG.search(nb)
                if tag and tag.group(2) != an_no:                      # 冲突 → 以案节为准
                    old = tag.group(2)
                    nb = RX_TAG.sub(lambda mm: "**来源案**：%s（%s）" % (nm, an_no), nb, count=1)
                    nb = nb.replace("-" + old + "-", "-" + an_no + "-")
                    stat["FIXED_CONFLICT"] += 1
                elif not tag:
                    n_tbd = len(RX_TBD.findall(nb))
                    nb = RX_TBD.sub(lambda mm: "%s-%s-%s" % (mm.group(1), an_no, mm.group(2)), nb)
                    nb2, c = re.subn(RX_SLOT,
                                     lambda mm: "- **来源案**：%s（%s）｜%s" % (nm, an_no, mm.group(2)),
                                     nb, count=1)
                    if c:
                        nb = nb2
                        stat["ADDED_TAG"] += 1
                    else:
                        stat["NO_SLOT"] += 1
                    stat["TBD_FIXED"] += n_tbd
                elif tag.group(2) == an_no:
                    n_tbd = len(RX_TBD.findall(nb))
                    if n_tbd:
                        nb = RX_TBD.sub(lambda mm: "%s-%s-%s" % (mm.group(1), an_no, mm.group(2)), nb)
                        stat["TBD_FIXED"] += n_tbd
                    stat["OK"] += 1
                newseg += [segs[j], nb]
            out += [mark + chr(10), "".join(newseg)]
        new = "".join(out)
        if new != raw:
            assert new.count("\n") == raw.count("\n"), "行数变化 " + fn
            assert new.count("\r\r") <= raw.count("\r\r"), "双CR " + fn
            if a.apply:
                io.open(p, "wb").write(new.encode("utf-8"))

    reg = RX_ANREF
    stay = 0
    for fn in sorted(os.listdir(vol)):
        if fn.endswith(".md"):
            stay += len(RX_TBD.findall(io.open(os.path.join(vol, fn), encoding="utf-8", errors="replace").read()))
    if a.json:
        print(json.dumps({"tool": "fix_volume_case_by_segment", "apply": bool(a.apply),
                          "stat": dict(stat), "tbd_left": stay, "head_tbd": head_tbd},
                         ensure_ascii=False))
    else:
        print("[%s] 按案节校正分卷" % ("APPLY" if a.apply else "DRY-RUN"))
        print("  冲突修正 %d ｜ 补标注 %d ｜ 已一致 %d ｜ 无「语用」槽位 %d"
              % (stat["FIXED_CONFLICT"], stat["ADDED_TAG"], stat["OK"], stat["NO_SLOT"]))
        print("  本次回填 TBD %d 处 ｜ 全库 TBD 编号残留 %d 处 ｜ 文件头内 TBD %d 处（不擅自改）"
              % (stat["TBD_FIXED"], stay, head_tbd))
    return 0


if __name__ == "__main__":
    sys.exit(main())

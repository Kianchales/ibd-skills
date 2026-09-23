#!/usr/bin/env python3
"""backfill_volume_refs.py — 分卷条目：TBD 占位编号回填 ＋ 补「来源案」字段

背景
    分卷（`methods/分卷/*.md`，P 系列 442 ＋ 体例域 276）是**回溯批产出的正文外置件**。
    其条目内的两处历史欠账：
      ① 占位编号引用 `S-TBD-NN` / `PL-TBD-NN`（产出当时的案内编号）—— 案号已定，应回填为
         `S-AN{案号}-NN` / `PL-AN{案号}-NN`
      ② 「原文实证」里的裸 `PAGE N` 缺**来源案**上下文（不知属哪案）—— 补「来源案」字段即可获得案级归属
    但分卷是**跨案汇编**，同一 `S-TBD-06` 在不同块可能属不同案 ⇒ **必须先判定块的来源案**。

判定（三级，实测可自动判定 86%）
    1. 相似度：块文本 5-gram 与各案产出（`cases/*/体例向提炼_S_*`／`招股书向提炼_PL_*`）重合率
       首选 ≥0.25 且 ≥2× 次选 → 采信
    2. 相似度 ＋ 案名（块内含且与首选一致）→ 采信
    3. 仅案名（块内唯一案名）→ 采信
    其余（歧义／无匹配）→ **不动**，输出清单待人工。

用法
    python backfill_volume_refs.py --methods-root <工作区根> [--apply] [--report <md>] [--json]

退出码 0 成功／1 自校验失败／2 用法错／3 目录缺失
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

RX_TBD = re.compile(r"(?<![A-Za-z-])([SPL]{1,2})-TBD-(\d{2})")   # 不用 \b：①②等全角前导会致 \b 失败

# 槽位（2026-09-19 放宽为白名单式，与 fix_volume_case_by_segment.py 同规）
RX_SLOT = re.compile(r"(?m)^(- )?((?:\*\*)?(?:%s)(?:\*\*)?[：:])" % \
    ("来源案|语用|方法|规则要点|原文实证|适用场景|互见|边界条件|句式模板|投行语言特征"
     "|可复用结论|对照锚点|本案实证|规则|实证|结论|锚点|场景|模板|特征|边界"))
RX_EID = re.compile(r"^([A-Z]{1,3}-\d{6})")


def grams(t, n=5):
    t = re.sub(r"[\s\*｜|「」【】（）()、，。：:；;—\-]+", "", t)
    return set(t[i:i + n] for i in range(0, max(len(t) - n, 1), 2))


def load_case_no(root):
    """读《单案索引对照表》两节：案名 → AN 号"""
    idx = os.path.join(os.path.dirname(root), STATE_NAME, CASE_INDEX_TABLE)
    if not os.path.exists(idx):
        return {}
    t = io.open(idx, encoding="utf-8", errors="replace").read()
    an = {}
    for m in re.finditer(r"(?m)^\| ([^|]{2,10}?) \| (AN\d{4}) \|", t):
        an[m.group(1).strip()] = m.group(2)
    for m in re.finditer(r"(?m)^\| (AN\d{4}) \| ([^|]{2,10}?) \|", t):
        an[m.group(2).strip()] = m.group(1)
    return an


def load_case_grams(root, an):
    """案名 → 5-gram 集（取该案的 S/PL 提炼产出）"""
    out = {}
    cases = os.path.join(os.path.dirname(root), "cases")
    if not os.path.isdir(cases):
        return out
    for d in sorted(os.listdir(cases)):
        if d.startswith("_") or not os.path.isdir(os.path.join(cases, d)):
            continue
        nm = d.split("_")[1] if len(d.split("_")) > 1 else d
        txt = ""
        for f in os.listdir(os.path.join(cases, d)):
            if f.startswith("体例向提炼_S_") or f.startswith("招股书向提炼_PL_"):
                txt += io.open(os.path.join(cases, d, f), encoding="utf-8", errors="replace").read()
        if txt and nm in an:
            # 同一案可能有多个 cases 目录（如 傲拓科技 20260820／20260912）→ 合并全部产出作为基准
            out[nm] = out.get(nm, set()) | grams(txt)
    return out


def judge(block, an, cg, names_sorted):
    g = grams(block)
    if not g:
        return None, 0.0, "空块"
    if not cg:
        return None, 0.0, "无产出可比"
    sc = sorted(((len(g & v) / max(len(g), 1), k) for k, v in cg.items()), reverse=True)
    top, sec = sc[0], sc[1] if len(sc) > 1 else (0.0, "")
    names_in = [n for n in names_sorted if n in block]
    if top[0] > 0.25 and top[0] > 2 * sec[0]:
        return top[1], round(top[0], 3), "相似度"
    if names_in and top[1] in names_in:
        return top[1], round(top[0], 3), "相似度+案名"
    if len(names_in) == 1:
        return names_in[0], round(top[0], 3), "仅案名"
    return None, round(top[0], 3), "歧义(%s/%.2f vs %s/%.2f)" % (top[1], top[0], sec[1], sec[0])


def main():
    ap = argparse.ArgumentParser(description="分卷 TBD 回填 ＋ 来源案字段")
    ap.add_argument("--methods-root", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--report", default="")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    md = os.path.abspath(a.methods_root)
    if os.path.isdir(os.path.join(md, METHODS_NAME)):      # 传库根 → 进 methods/
        md = os.path.join(md, METHODS_NAME)
    vol_dir = os.path.join(md, VOLUME_NAME)
    if not os.path.isdir(vol_dir):
        sys.stderr.write("[MISS] 无分卷目录: %s\n" % vol_dir)
        return 3

    an = load_case_no(md)
    cg = load_case_grams(md, an)
    names_sorted = sorted(an, key=len, reverse=True)
    stat = collections.Counter()
    low = []
    per_file = {}
    total_tbd = fixed_tbd = 0

    for fn in sorted(os.listdir(vol_dir)):
        if not fn.endswith(".md"):
            continue
        p = os.path.join(vol_dir, fn)
        raw = io.open(p, "rb").read().decode("utf-8")
        seps = re.split(r"(?m)^(### )", raw)
        # 重组为 [前言] + [('### ', block), ...]
        head = seps[0]
        blocks = []
        for i in range(1, len(seps), 2):
            blocks.append(("### ", seps[i + 1] if i + 1 < len(seps) else ""))
        newblocks = []
        touched = 0
        for pre, b in blocks:
            m = RX_EID.match(b)
            if not m:
                newblocks.append(pre + b)
                continue
            eid = m.group(1)
            n_tbd = len(RX_TBD.findall(b))
            total_tbd += n_tbd
            case, score, how = judge(b, an, cg, names_sorted)
            if case is None:
                stat["LOW"] += 1
                if n_tbd:
                    low.append((fn, eid, n_tbd, how))
                newblocks.append(pre + b)
                continue
            an_no = an[case]
            nb = b
            if n_tbd:
                nb = RX_TBD.sub(lambda mm: "%s-%s-%s" % (mm.group(1), an_no, mm.group(2)), nb)
                fixed_tbd += n_tbd
            # 补「来源案」字段（与「语用」同行，零新增行）
            tag = "- **来源案**：%s（%s）｜" % (case, an_no)
            if "**来源案**" not in nb:
                nb2, c = RX_SLOT.subn(lambda mm: tag + mm.group(2), nb, count=1)
                if c:
                    nb = nb2
                else:
                    stat["NOSLOT"] += 1    # 无字段槽位 → 只做 TBD 回填，不加标注
            if nb != b:
                touched += 1
                stat["FIXED"] += 1
                if how == "仅案名":
                    stat["BYNAME"] += 1
                elif how == "相似度":
                    stat["BYSIM"] += 1
                else:
                    stat["BYBOTH"] += 1
            newblocks.append(pre + nb)
        new = head + "".join(newblocks)
        if new != raw:
            assert new.count("\n") == raw.count("\n"), "行数变化: %s" % fn
            assert new.count("\r\r") <= raw.count("\r\r"), "双 CR: %s" % fn
            per_file[fn] = touched
            if a.apply:
                io.open(p, "wb").write(new.encode("utf-8"))

    if a.report:
        io.open(a.report, "w", encoding="utf-8", newline="\n").write(
            "# 分卷 TBD 回填与来源案补记 · 低置信清单\n\n"
            "> 自动判定采信 %d 块（相似度 %d／相似度+案名 %d／仅案名 %d）；"
            "**未动 %d 块**（歧义或无匹配，属跨案共通新写或产出缺失）。\n\n"
            "| 卷文件 | 条目 | 块内 TBD | 判定 |\n|---|---|---|---|\n"
            % (stat["BYSIM"] + stat["BYBOTH"] + stat["BYNAME"], stat["BYSIM"], stat["BYBOTH"],
               stat["BYNAME"], stat["LOW"]) +
            "\n".join("| %s | %s | %d | %s |" % x for x in low) + "\n")

    if a.json:
        print(json.dumps({"tool": "backfill_volume_refs", "apply": bool(a.apply),
                          "fixed_blocks": stat["FIXED"], "low_blocks": stat["LOW"],
                          "tbd_total": total_tbd, "tbd_fixed": fixed_tbd,
                          "per_file": per_file}, ensure_ascii=False))
    else:
        print("[%s] 分卷 TBD 回填 ＋ 来源案字段" % ("APPLY" if a.apply else "DRY-RUN"))
        print("  采信块 %d（相似度 %d／相似度+案名 %d／仅案名 %d）｜未动 %d"
              % (stat["FIXED"], stat["BYSIM"], stat["BYBOTH"], stat["BYNAME"], stat["LOW"]))
        print("  TBD 编号：总 %d 处 → 回填 %d 处（剩 %d 处在未动块内）"
              % (total_tbd, fixed_tbd, total_tbd - fixed_tbd))
        for k, v in per_file.items():
            print("     %-44s %d 块" % (k, v))
    return 0


if __name__ == "__main__":
    sys.exit(main())

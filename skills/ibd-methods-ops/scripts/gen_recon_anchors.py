#!/usr/bin/env python3
"""B 对账锚点生成器（R-0068 修正版 · 2026-10-01）

【背景】原 `_b2_recon` / `_b3_recon` 生成器把「条目正文提到他案案名」处误挂到最近的编号标题，
        WO-MF-23 第三批因此产生 10 条锚点错配（4 案误挂 `I-CL01-60`、2 案误挂 `I-CL07-19`），
        对账时表现为「失据/存疑」，**实为工具问题伪装成库问题**。

【根因（实测复现）】段边界只认「**编号形态**」的 `### ` 标题 ⇒
        `### 子行业：LED 芯片封装用电子封装材料（康美特·C3985）` 这类**非编号 `### ` 标题不被当边界**，
        条目段被撑大、吞入后续整节内容 ⇒ 后节的他案案名被误挂到本编号。

【修法】
  ① **段界 ＝ 任意 `### ` 行**（`^###\\s`）；**条目起点 ＝ 编号形态标题行**（`^###\\s+<编号>`）
  ② **角色分类**：`case`（实证/共案）／`source`（来源案）／`inter`（互见）／`table`（表格提及）／`other`
     —— 只有 `case`/`source` 进「**对账清单**」，其余进「**疑似挂靠**」供人核
  ③ 输出「**同编号被 ≥2 案以实证挂靠**」清单（强信号，供人核；共案条目属正常，须人工区分）

【用法】
  python gen_recon_anchors.py --methods-root <库根> --cases "AN0028=精创电气,AN0029=觅睿科技" --out out.json
  python gen_recon_anchors.py --methods-root <库根> --cases-file cases.txt --out out.json
    （cases.txt 每行：`AN00xx 案名` 或 `AN00xx=案名`；# 开头为注释）
"""
import argparse
import io
import json
import os
import re
import sys

SCAN_DIRS_DEFAULT = ["50_分卷", "10_跨案域", "20_语言专项", "30_行业版"]

HEAD_ANY = re.compile(r"^#{1,3}\s")                                   # 段界：1–3 级标题（条目为 3 级，段界＝同级或更高级）
HEAD_CODE = re.compile(r"^###\s+([A-Za-z]{1,3}(?:-[A-Za-z0-9]+)+)\s*(.*)$")  # 条目起点：编号形态
EV_RX = re.compile(r"^[-*]\s*\*\*[^*]{0,24}实证[^*]{0,24}\*\*\s*[:：]")      # 实证行
SRC_RX = re.compile(r"来源\s*[:：]")                                        # 来源案标注
INTER_RX = re.compile(r"互见|参见|另见|对照|参考")                            # 互见语境


def classify(title, seg, name, no):
    """判定该案在本条目段内的角色；None ＝ 段内未出现该案。"""
    def has(s):
        return (name in s) or (no in s)

    if has(title):
        return "case"                      # 标题含案名（含共案条目）
    for ln in seg:
        s = ln.strip()
        if EV_RX.match(s) and has(s):
            return "case"                  # 实证行含案名
    for ln in seg:
        s = ln.strip()
        # 加粗列表项含案名（「多案实证」列表项形态：`- **<案名>（AN00xx）**——…`）
        m2 = re.match(r"^[-*]\s*\*\*([^*]{0,40})\*\*", s)
        if m2 and has(s):
            label = m2.group(1)
            # ① 标签含关系词 ⇒ 弱关联
            if re.search(r"对照|互见|参见|交叉|另见|参考", label):
                return "inter"
            # ② 案名在**标签内** ⇒ 实证（案名作主语/主体）
            if has(label):
                return "case"
            # ③ 案名在行文中：紧邻前置关系词者属**并列/对比语境** ⇒ 弱关联
            pos = s.find(name) if name in s else s.find(no)
            if pos > 0 and re.search(r"[与同]|参照|参见|对比|交叉|较", s[max(0, pos - 12):pos]):
                return "inter"
            return "case"
    for ln in seg:
        s = ln.strip()
        if SRC_RX.search(s) and has(s):
            return "source"                # 来源案标注含案名
    for ln in seg:
        if has(ln) and INTER_RX.search(ln):
            return "inter"                 # 仅互见语境
    for ln in seg:
        if ln.strip().startswith("|") and has(ln):
            return "table"                 # 仅表格提及
    for ln in seg:
        if has(ln):
            return "other"                 # 其他提及
    return None


def scan_case(mroot, name, no, scan_dirs):
    """返回 (hits, orphans)。hits＝编号条目段内命中；orphans＝段外含案名的实证类行（供人核归属）。"""
    hits, seen, orphans = [], set(), []
    for d in scan_dirs:
        base = os.path.join(mroot, d)
        if not os.path.isdir(base):
            continue
        for dirpath, _, files in os.walk(base):
            for fn in sorted(files):
                if not fn.endswith(".md"):
                    continue
                fp = os.path.join(dirpath, fn)
                try:
                    text = io.open(fp, encoding="utf-8", errors="replace").read()
                except OSError:
                    continue
                if name not in text and no not in text:
                    continue
                rel = os.path.relpath(fp, mroot).replace("\\", "/")
                lines = text.split("\n")
                bounds = [i for i, l in enumerate(lines) if HEAD_ANY.match(l)]
                covered = set()
                for k, i in enumerate(bounds):
                    m = HEAD_CODE.match(lines[i])
                    if not m:
                        continue
                    end = bounds[k + 1] if k + 1 < len(bounds) else len(lines)
                    covered.update(range(i, end))
                    seg = lines[i + 1:end]
                    role = classify(m.group(2), seg, name, no)
                    if role is None:
                        continue
                    key = (fp, m.group(1))
                    if key in seen:
                        continue
                    seen.add(key)
                    hits.append({
                        "file": rel,
                        "code": m.group(1),
                        "head": lines[i].strip(),
                        "role": role,
                        "ev_lines": [l.strip() for l in seg if (name in l or no in l)][:6],
                    })
                # 孤儿行：含案名但**不在任何编号条目段内**的实证类行
                #   （典型：文件末尾「处置口径／批次增量落号声明」、跨章节的补充实证）
                for i, l in enumerate(lines):
                    if i in covered or (name not in l and no not in l):
                        continue
                    s = l.strip()
                    if re.match(r"^[-*]\s*\*\*|^>", s) or ("落号" in s) or ("并入" in s):
                        orphans.append({"file": rel, "line": i + 1, "text": s[:170]})
    return hits, orphans


def parse_cases(a):
    cases = []
    if a.cases_file:
        for ln in io.open(a.cases_file, encoding="utf-8"):
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            parts = [p for p in re.split(r"[\s,=｜|]+", ln) if p]
            if len(parts) >= 2:
                cases.append((parts[0], parts[1]))
    elif a.cases:
        for item in a.cases.split(","):
            if "=" in item:
                no, nm = item.split("=", 1)
                cases.append((no.strip(), nm.strip()))
    return cases


def main():
    ap = argparse.ArgumentParser(description="B 对账锚点生成器（R-0068 修正版）")
    ap.add_argument("--methods-root", required=True, help="方法论库根（含 50_分卷 等）")
    ap.add_argument("--cases", help='案清单，如 "AN0028=精创电气,AN0029=觅睿科技"')
    ap.add_argument("--cases-file", help="案清单文件（每行 AN00xx 案名）")
    ap.add_argument("--out", default="recon_anchors.json", help="输出 JSON 路径")
    ap.add_argument("--scan-dirs", default=",".join(SCAN_DIRS_DEFAULT))
    a = ap.parse_args()

    mroot = os.path.abspath(a.methods_root)
    dirs = [d.strip() for d in a.scan_dirs.split(",") if d.strip()]
    # 兼容两种传法：工作区根（其下有 methods/）或 库目录（其下有 50_分卷 等）
    if (not any(os.path.isdir(os.path.join(mroot, d)) for d in dirs)
            and os.path.isdir(os.path.join(mroot, "methods"))):
        mroot = os.path.join(mroot, "methods")
    cases = parse_cases(a)
    if not cases:
        print("[ERROR] 未提供案清单（--cases 或 --cases-file）", file=sys.stderr)
        return 2

    out = {}
    for no, nm in cases:
        hits, orphans = scan_case(mroot, nm, no, dirs)
        out[no] = {
            "case": nm,
            "anchors": hits,                                               # 段内出现该案的全部条目
            "weak": [h for h in hits if h["role"] in ("inter", "table")],  # 弱关联（互见/表格提及）标注
            "orphans": orphans,                                            # 段外含案名的实证类行（供人核归属）
        }

    code2cases = {}
    for no, rec in out.items():
        for h in rec["anchors"]:
            if h["role"] in ("case", "source"):
                code2cases.setdefault("%s#%s" % (h["file"], h["code"]), []).append(no)
    multi = {k: v for k, v in code2cases.items() if len(v) >= 2}

    print("%-4s %-10s %-8s %-10s %-8s %-8s %s" % ("#", "案号", "案名", "对账锚点", "弱关联", "段外行", "角色分布"))
    print("-" * 84)
    from collections import Counter as _C
    na = nw = nor = 0
    for i, (no, rec) in enumerate(sorted(out.items()), 1):
        na += len(rec["anchors"])
        nw += len(rec["weak"])
        nor += len(rec["orphans"])
        dist = dict(_C(h["role"] for h in rec["anchors"]))
        print("%-4d %-10s %-8s %-10d %-8d %-8d %s"
              % (i, no, rec["case"], len(rec["anchors"]), len(rec["weak"]), len(rec["orphans"]), dist))
    print("-" * 84)
    print("对账锚点合计 %d ｜ 其中弱关联 %d ｜ 段外待核行 %d" % (na, nw, nor))
    if multi:
        print()
        print("⚠ 同编号被 ≥2 案以「实证」挂靠（强信号 · 须人工区分「共案条目」与「误挂」）：")
        for k, v in sorted(multi.items(), key=lambda x: -len(x[1])):
            print("   %s ← %s" % (k, "／".join(v)))
    else:
        print()
        print("✓ 无「同编号多案实证挂靠」")

    payload = {
        "generator": "gen_recon_anchors.py",
        "version": "R-0068",
        "methods_root": mroot,
        "cases": out,
        "multi_case_codes": multi,
        "totals": {"anchors": na, "weak": nw, "orphans": nor},
    }
    io.open(a.out, "w", encoding="utf-8").write(
        json.dumps(payload, ensure_ascii=False, indent=1))
    print()
    print("已落 %s" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

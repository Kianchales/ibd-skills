#!/usr/bin/env python3
"""来源代号映射生成器（G1 前置）——把 `招 P152` 这类**隐含约定**变成**机器可读的物理指向**。

用法：
    python gen_source_map.py [--methods-root <工作区根>] [--json]

背景与定位：
    契约册 §4 定义了来源简称的**语义**（`招`／`问1`／`反馈`…），但**从未定义它们的物理指向**；
    而来源是**异质的**（`招` → `cases/<案>/…招股说明书*.txt`；`财务包` → `cases/<案>/阅读包_财务.txt`）。
    ⇒「溯源校验」（把条目里的 `招 P152` 回到原文逐字命中）**无法机械化**，本条即补这一环：
    产出 `_generated/来源代号映射.json`，作为**来源代号的物理指向单一事实源**。

机械可行性（实测）：
    材料 txt 带 **`===== PAGE N =====` 页标记**（样本 347 个 PAGE 块）⇒ 页码 → 行号**可机器解析**；
    故「页级」溯源可落地；「行范围位」（如 `招 P152 L3-8`）随后可增量支持（见条目契约 §4 扩展）。

重要边界（诚实声明）：
    · **只映射、不校验内容**：本脚本不判断条目里的页码是否真实存在，只建立「代号 → 文件 + 页码可解析性」。
    · 只认 `.txt`（可读源）；`.pdf` 仅在同目录无 `.txt` 时作**降级登记**（标 `text_available: false`）。
    · 输出**不含时间戳**，保证重跑幂等（可 diff 自证）。
"""
import argparse, io, json, os, re, sys

import sys as _s
if hasattr(_s.stdout, "reconfigure"):
    _s.stdout.reconfigure(encoding="utf-8")

_ap = argparse.ArgumentParser(description="生成来源代号映射（代号 → 物理文件 + 页码可解析性）")
_ap.add_argument("--methods-root", default=os.environ.get("METHODS_ROOT", ""),
                 help="工作区根（= 库根，其下含 methods/；默认 $METHODS_ROOT）")
_ap.add_argument("--json", action="store_true", help="打印 JSON 而不写文件")
_args = _ap.parse_args()

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)
from _lib.layout import resolve as _layout_resolve, SOURCE_MAP_FILE, SOURCE_ALIASES
_ROOT, METHODS, SCRIPTS = _layout_resolve(_args.methods_root)

# ── 代号表（**语义**＝契约册 §4；本脚本负责给每个代号找到**物理指向**）──────────────
# 顺序有意义：先匹配更具体的形态，避免「审核问询回复」被判为「回复」兜底。
CODE_RULES = (
    ("招", r"招股说明书"),                      # 默认最新版
    ("问N", r"审核问询回复|问询函回复"),         # 轮次取自「第N轮」
    ("落实函", r"审核中心意见落实函|意见落实函"),  # 科创板常见件（**实测自 unmapped 反哺**）
    ("反馈", r"反馈意见"),
    ("上会", r"上会稿|上会"),
    ("回复", r"回复"),                          # 轮次不可判定的兜底
)
PACK_RULES = (("财务包", "阅读包_财务"), ("法律包", "阅读包_法律"), ("行业包", "阅读包_行业"))
PAGE_RX = re.compile(r"^=+\s*PAGE\s+(\d+)\s*=+\s*$", re.M)
ROUND_RX = re.compile(r"第\s*(\d+)\s*轮")
VER_RX = re.compile(r"(注册稿|上会稿|申报稿|反馈回复稿)")

# ── 别名表：**统一引用 `_lib/layout.py` 的单一事实源**（`SOURCE_ALIASES`）────────────
# 背景：契约册 §4 只登记规范代号，但**库内实际书写高度异形**（实测 59 种）。若「解析」只认规范号，
#   则「把 `招 P152` 回到原文」这件事对**近半标注直接失败** ⇒ 溯源校验落不了地。
# 处置（与《方法论_案名规范表》三表同构）：**别名仅供解析**；**新条目须写规范代号**；
#   别名**不追溯回改**（属 ③ 内容回写，需语义）。
# 解析入口 ＝ `layout.normalize_source_code()`（含「取末段」分段，处理 `<案例主体>·招` 类复合形态）。


def classify(fname):
    """→ (code, kind, version, round_no)；无法归类返回 None。"""
    for code, pat in PACK_RULES:
        if fname.startswith(pat):
            return code, "阅读包", "", ""
    stem = fname[:-4] if fname.endswith(".txt") else fname[:-4] if fname.endswith(".pdf") else fname
    for code, pat in CODE_RULES:
        if not re.search(pat, stem):
            continue
        if code == "问N":
            m = ROUND_RX.search(stem)
            if not m:
                code = "回复"                     # 无轮次 ⇒ 兜底，不臆造问N
            else:
                code = "问%s" % m.group(1)
        ver = ""
        mv = VER_RX.search(stem)
        if mv:
            ver = mv.group(1)
        rd = ROUND_RX.search(stem)
        return code, "正文", ver, (rd.group(1) if rd else "")
    return None


def main():
    croot = os.path.join(_ROOT, "cases")
    payload = {
        "tool": "gen_source_map",
        "purpose": "来源代号的**物理指向**单一事实源（契约册 §4 只定语义，本表定指向）",
        "codebook": {
            "招": "招股说明书（默认最新版；版本区分写 `招·注册稿` 等）",
            "招·<版本>": "需区分版本时（版本取文件名中的 注册稿／上会稿／申报稿）",
            "问1": "第 1 轮问询回复", "问2": "第 2 轮问询回复",
            "反馈": "反馈意见回复", "上会": "上会稿", "落实函": "审核中心意见落实函（科创板常见件）",
            "回复": "问询回复轮次无法判定时的兜底",
            "财务包": "S3 材料准备产出的《阅读包_财务》", "法律包": "《阅读包_法律》",
            "行业包": "《阅读包_行业》",
        },
        "page_marker": r"^=+\s*PAGE\s+(\d+)\s*=+\s*$",
        "page_marker_note": "材料 txt 内页标记形态；页码 → 行号可由本表 + 该正则机器解析",
        "aliases": {c: list(v) for c, v in SOURCE_ALIASES.items()},
        "aliases_note": "**别名仅供解析**（把 `一轮回复`／`招股书`／`财务` 等异形归到规范代号）；"
                        "**新条目须写规范代号**；别名**不追溯回改**（属 ③ 内容回写、需语义判断）。"
                        "实测：异形占标注总数约四成，若解析只认规范号则溯源校验对近半标注直接失败。",
        "cases": {},
        "unmapped": [],
    }
    if not os.path.isdir(croot):
        sys.stderr.write("✗ 未找到 cases/：%s\n" % croot)
        sys.exit(2)

    for d in sorted(os.listdir(croot)):
        p = os.path.join(croot, d)
        if not os.path.isdir(p) or d.startswith("_"):
            continue
        parts = d.split("_")
        name = parts[1] if len(parts) >= 3 else d
        cand = {}
        for fn in sorted(os.listdir(p)):
            if not fn.lower().endswith((".txt", ".pdf")):
                continue
            c = classify(fn)
            if not c:
                payload["unmapped"].append("%s/%s" % (d, fn))
                continue
            code, kind, ver, rd = c
            cand.setdefault(code, []).append((fn, kind, ver, rd))
        sources = []
        for code in sorted(cand):
            entries = cand[code]
            # 同代号多个候选：.txt 优先；再取文件名最大（含日期 ⇒ 最新）
            txts = [e for e in entries if e[0].lower().endswith(".txt")]
            pick = sorted(txts or entries, key=lambda e: e[0])[-1]
            fp = os.path.join(p, pick[0])
            try:
                size = os.path.getsize(fp)
                txt = io.open(fp, encoding="utf-8", errors="replace").read() if pick[0].lower().endswith(".txt") else ""
            except OSError:
                size, txt = 0, ""
            pages = [int(m) for m in PAGE_RX.findall(txt)]
            sources.append({
                "code": ("%s·%s" % (code, pick[2])) if (pick[2] and code == "招") else code,
                "kind": pick[1], "version": pick[2], "round": pick[3],
                "file": pick[0], "bytes": size,
                "lines": (txt.count("\n") + 1) if txt else None,
                "pages": (max(pages) if pages else None),
                "text_available": pick[0].lower().endswith(".txt"),
                "alternatives": [e[0] for e in entries if e[0] != pick[0]],
            })
        payload["cases"][name] = {"dir": "cases/%s" % d, "sources": sources}
        if not sources:
            # **不静默缺席**：目录里没有任何可归类材料 ⇒ 显式登记（属「验不了」的输入侧，
            # 由使用方决定是否需要补采；本脚本只报，不推断）
            payload.setdefault("no_material", []).append("cases/%s" % d)

    payload.setdefault("no_material", [])

    if _args.json:
        print(json.dumps(payload, ensure_ascii=False))
        return 0
    dst = os.path.join(METHODS, SOURCE_MAP_FILE)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with io.open(dst, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1, sort_keys=False)
        f.write("\n")
    n_cases = len(payload["cases"])
    n_src = sum(len(v["sources"]) for v in payload["cases"].values())
    n_pg = sum(1 for v in payload["cases"].values() for s in v["sources"] if s["pages"])
    print("✓ 来源代号映射已生成: %s（案 %d ｜ 来源 %d ｜ 含页码可解析 %d ｜ 未归类文件 %d）"
          % (os.path.relpath(dst, METHODS), n_cases, n_src, n_pg, len(payload["unmapped"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())

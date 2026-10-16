#!/usr/bin/env python3
"""ibd-quality-gates G4 方法论引用勾稽器（对照表 → 方法库全集三查）

用法:
    python check_method_refs.py <对照表.md|对照表.json> [--index 全集路径] [--json] [--out 报告路径]

三查:
    1. 编号格式合法: ^[A-Z]{1,2}-[0-9]{6}$（域-族号2位-族内4位，如 F-010001 / WL-150001）
    2. 编号存在性:   必须命中方法库全集（methods/_generated/方法论_条目标题目录.md），防空挂/编造编号
    3. 使用位置非空: 「待补」「-」冒充使用位置 = 未落实；编号列空白 = 空挂引用

输出:
    终端报告（HIGH=须改 / INFO=提示）；报告全文落盘（默认 %TEMP%/<文件名>.check_refs.log），末尾回路径；
    `--json` 走单一结构化出口。退出码: 0=PASS, 1=存在 HIGH, 2=文件/参数错误

边界说明:
    本脚本只做编号机检。「该问题是否引用了恰当条目」「引用是否贴切」属语义判断，
    必须人工按 rules.md §附二核对，脚本不能替代人工。
索引来源（优先级）:
    --index 参数 > ~/.config/gates-index.json（键名含「条目」或「目录」优先）> 无则跳过存在性校验
"""
import argparse
import json
import os
import re
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_INDEX = None  # 仓内禁私有绝对路径；全集索引经 ~/.config/gates-index.json 或 --index 指定
GATES_INDEX = os.path.expanduser("~/.config/gates-index.json")
REF_RE = re.compile(r"[A-Z]{1,2}-[0-9]{6}")
LOOSE_RE = re.compile(r"[A-Za-z]{1,3}-[0-9]{4,8}\b")  # 疑似编号（含笔误形态）
PLACEHOLDER = {"", "-", "待补", "无", "n/a", "tbd"}


def resolve_index(cli_path):
    if cli_path:
        return cli_path if os.path.exists(cli_path) else None
    if os.path.exists(GATES_INDEX):
        try:
            cfg = json.load(open(GATES_INDEX, encoding="utf-8"))
            if isinstance(cfg, dict):
                named = [v for k, v in cfg.items()
                         if ("条目" in k or "目录" in k) and isinstance(v, str) and os.path.exists(v)]
                if named:
                    return named[0]
                existing = [v for v in cfg.values()
                            if isinstance(v, str) and os.path.exists(v)]
                return existing[0] if existing else None
        except Exception:
            pass
    return None  # 无配置时跳过存在性校验（仅查格式与使用位置）


def load_universe(index_path, errors):
    """全集 = 条目标题目录中全部唯一编号"""
    try:
        text = open(index_path, encoding="utf-8").read()
    except Exception as e:
        errors.append(f"全集索引读取失败 {index_path}: {e}")
        return set()
    refs = set(REF_RE.findall(text))
    if not refs:
        errors.append(f"全集索引为空（未提取到任何编号）: {index_path}")
    return refs


def parse_rows(path):
    """解析对照表 → [(行号, 编号列表, 疑似编号候选, 使用位置文本)]；md 表格或 json 数组"""
    rows = []
    text = open(path, encoding="utf-8").read()
    if path.lower().endswith(".json"):
        data = json.loads(text)
        items = data if isinstance(data, list) else data.get("rows", data.get("items", []))
        for i, it in enumerate(items):
            if not isinstance(it, dict):
                continue
            refs_raw = it.get("refs", it.get("编号", it.get("条目编号", "")))
            refs_raw = refs_raw if isinstance(refs_raw, str) else " ".join(refs_raw)
            refs = REF_RE.findall(refs_raw)
            loose = list(LOOSE_RE.findall(refs_raw))
            loc = str(it.get("location", it.get("使用位置", ""))).strip()
            rows.append((i + 1, refs, loose, loc))
        return rows
    lines = text.splitlines()
    header_seen = False
    in_table = False
    for lineno, line in enumerate(lines, 1):
        s = line.strip()
        if not s.startswith("|"):
            in_table = False
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if all(c and set(c) <= set(":- ") for c in cells):
            continue  # 分隔行
        if not header_seen and any("编号" in c for c in cells):
            header_seen = True
            in_table = True
            continue
        if not (header_seen and in_table):
            continue  # 表头块之外的其他表格不纳入
        refs_col = cells[1] if len(cells) >= 2 else ""
        refs = REF_RE.findall(refs_col)
        loose = LOOSE_RE.findall(refs_col)
        loc = cells[2] if len(cells) >= 3 else ""
        rows.append((lineno, refs, loose, loc))
    return rows


def check(path, index_path):
    errs, info = [], []
    if not os.path.exists(path):
        return [f"{path}: 文件不存在"], info, None
    universe = load_universe(index_path, errs) if index_path else set()
    try:
        rows = parse_rows(path)
    except Exception as e:
        errs.append(f"{path}: 解析失败 {e}")
        return errs, info, None
    if not rows:
        errs.append("HIGH 整表无任何数据行——按 G4「未引用方法论打回补引」处理")
        return errs, info, None
    seen = {}
    for lineno, refs, loose, loc in rows:
        if not refs and not loose:
            errs.append(f"HIGH 行{lineno}: 编号列为空（空挂引用，该引未引）")
        for c in loose:
            if not re.fullmatch(r"[A-Z]{1,2}-[0-9]{6}", c):
                errs.append(f"HIGH 行{lineno}: 编号格式非法 {c}（应形如 F-010001 / WL-150001）")
        for r in refs:
            seen.setdefault(r, []).append(lineno)
            if universe and r not in universe:
                errs.append(f"HIGH 行{lineno}: 编号不存在于方法库全集 {r}（疑空挂/编造，查 {index_path}）")
        if loc.strip().lower() in PLACEHOLDER:
            errs.append(f"HIGH 行{lineno}: 使用位置为空或「待补」冒充（{loc.strip()!r}）")
    info.append(f"对照表共 {len(rows)} 数据行，去重编号 {len(seen)} 个")
    if universe:
        info.append(f"全集 {len(universe)} 个编号，存在性校验已执行")
    return errs, info, seen


def main():
    ap = argparse.ArgumentParser(description="G4 方法论引用勾稽（三查：格式/存在性/使用位置）")
    ap.add_argument("file", help="G4 对照表（.md 或 .json）")
    ap.add_argument("--index", help="全集索引路径（默认走 gates-index.json，无则跳过存在性校验）")
    ap.add_argument("--json", action="store_true", help="结构化输出")
    ap.add_argument("--out", help="报告落盘路径（默认 %TEMP%/<名>.check_refs.log）")
    args = ap.parse_args()

    index_path = resolve_index(args.index)
    errs, info, seen = check(args.file, index_path)
    status = "PASS" if not errs else "FAIL"
    if args.json:
        print(json.dumps({
            "file": args.file, "index": index_path, "status": status,
            "errors": errs, "info": info, "refs": sorted(seen or {}),
            "detail_log": None
        }, ensure_ascii=False, indent=2))
    else:
        print(f"# G4 勾稽报告 · {args.file}")
        print(f"# 全集索引: {index_path or '未找到'}")
        for i in info:
            print(f"INFO {i}")
        for e in errs:
            print(e)
        print(f"\n{'✅ PASS' if not errs else '❌ FAIL'}：{len(errs)} 项 HIGH")
    if errs:
        log = args.out or os.path.join(tempfile.gettempdir(),
                                       os.path.basename(args.file) + ".check_refs.log")
        with open(log, "w", encoding="utf-8") as f:
            f.write(f"status={status}\nfile={args.file}\nindex={index_path}\n")
            f.write("\n".join(errs + info))
        if not args.json:
            print(f"报告已落盘: {log}")
    sys.exit(0 if not errs else 1)


if __name__ == "__main__":
    main()

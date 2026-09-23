#!/usr/bin/env python3
"""apply_case_no.py — 把《单案索引对照表》的案号写回单案文件 frontmatter（表驱动）

单一事实源：《state/单案索引对照表.md》(案名 → AN 号)
行为：为缺 `case_no:` 的单案文件在 `case:` 行后插入 `case_no: ANxxxx`；
      已有且一致 → 跳过；已有但不一致 → 报 CONFLICT，不自动改（须人工裁定）。
安全：默认 dry-run；--apply 才落盘；落盘前三道自校验（双 CR 不得新增 / 行数守恒 / 幂等）。
退出码：0 无待改（或已成功）／1 有冲突 ／2 用法错 ／3 索引表缺失
"""
import argparse
import io
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SKIP_DIRS = {"archive", "notes", "分卷", "_backup", "__pycache__", "单案/archive"}


def load_index(path):
    """读对照表：返回 案名 -> AN号（只取六列表格的第二列）"""
    if not os.path.exists(path):
        sys.stderr.write("[MISS] 索引对照表不存在: %s\n" % path)
        sys.exit(3)
    t = io.open(path, encoding="utf-8", errors="replace").read()
    out = {}
    for ln in t.splitlines():
        if not ln.startswith("|"):
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) < 2 or cells[0] in ("案名", "---") or set(cells[0]) <= set("- "):
            continue
        if re.match(r"^AN\d{4}$", cells[1]):
            out[cells[0]] = cells[1]
    return out


def split_lines(raw):
    """按分隔符切分，返回 (正文段, 分隔符) —— 分隔符原样保留，防 CRLF 被改写"""
    parts = re.split(r"(\r\n|\n)", raw)
    return parts[0::2], parts[1::2]


def plan_file(path, an):
    raw = io.open(path, "rb").read().decode("utf-8")
    if re.search(r"(?m)^case_no:\s*AN\d{4}", raw):
        m = re.search(r"(?m)^case_no:\s*(AN\d{4})", raw)
        return ("OK" if m.group(1) == an else "CONFLICT", raw, None)
    m = re.search(r"(?m)^case:[^\r\n]*", raw)
    if not m:
        return ("NOCTX", raw, None)
    tail = raw[m.end():m.end() + 2]
    if tail.startswith("\r\n"):
        nl = "\r\n"
    elif tail.startswith("\n"):
        nl = "\n"
    elif tail.startswith("\r"):
        nl = "\r"
    else:                       # 文件末尾即 case 行，无换行
        nl = "\n"
    new = raw[:m.end()] + nl + "case_no: %s" % an + raw[m.end():]
    return ("ADD", raw, new)


def main():
    ap = argparse.ArgumentParser(description="把案号写回单案文件 frontmatter（表驱动）")
    ap.add_argument("--methods-root", required=True, help="工作区根（= 库根，其下含 methods/）")
    ap.add_argument("--case-index", default="", help="《单案索引对照表》路径（默认 <库>/../state/）")
    ap.add_argument("--apply", action="store_true", help="实际落盘（默认 dry-run）")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    a = ap.parse_args()

    root = os.path.abspath(a.methods_root)
    idx_path = a.case_index or os.path.join(os.path.dirname(root), "state", "单案索引对照表.md")
    idx = load_index(idx_path)
    if not idx:
        sys.stderr.write("[SKIP] 索引表无有效案号行\n")
        return 3

    single_dir = os.path.join(root, "单案")
    if not os.path.isdir(single_dir):
        sys.stderr.write("[SKIP] 无单案目录: %s\n" % single_dir)
        return 3

    stat = {"ADD": 0, "OK": 0, "CONFLICT": 0, "NOCTX": 0, "MISSNAME": 0}
    plan, conflicts, missname = [], [], []
    for fn in sorted(os.listdir(single_dir)):
        if not fn.endswith(".md"):
            continue
        p = os.path.join(single_dir, fn)
        t = io.open(p, encoding="utf-8", errors="replace").read()
        m = re.search(r"(?m)^case:\s*(.+?)\s*$", t)
        name = m.group(1).strip() if m else fn[:-3].split("_")[-1]
        if name not in idx:
            stat["MISSNAME"] += 1
            missname.append(name)
            continue
        st, raw, new = plan_file(p, idx[name])
        stat[st] += 1
        if st == "CONFLICT":
            cur = re.search(r"(?m)^case_no:\s*(AN\d{4})", raw).group(1)
            conflicts.append((fn, cur, idx[name]))
        elif st == "ADD":
            plan.append((p, raw, new))

    if a.apply and plan:
        written = 0
        for p, raw, new in plan:
            # 自校验①双 CR 不得新增
            if new.count("\r\r") > raw.count("\r\r"):
                print("ABORT: 双 CR 新增 %s" % p)
                return 1
            # 自校验②行数守恒（恰新增 1 行：LF/CRLF 文件 +1 个 \n，\r 行尾文件 +0）
            if new.count("\n") - raw.count("\n") not in (0, 1):
                print("ABORT: 行数不守恒 %s" % p)
                return 1
            io.open(p, "wb").write(new.encode("utf-8"))
            written += 1
        stat["ADD"] = 0
        stat["WRITTEN"] = written

    if a.json:
        import json
        print(json.dumps({"tool": "apply_case_no", "index": idx_path, "stat": stat,
                          "conflicts": conflicts, "unknown_names": missname},
                         ensure_ascii=False))
    else:
        mode = "APPLY" if a.apply else "DRY-RUN"
        print("[%s] 索引表 %s（%d 个案号）" % (mode, idx_path, len(idx)))
        print("  待补 case_no : %d" % (stat.get("WRITTEN", stat["ADD"])))
        print("  已一致       : %d" % stat["OK"])
        print("  冲突(不自动改): %d %s" % (stat["CONFLICT"], conflicts if conflicts else ""))
        print("  无 case 行   : %d" % stat["NOCTX"])
        print("  表内无此案   : %d %s" % (stat["MISSNAME"], missname if missname else ""))
    return 1 if stat["CONFLICT"] else 0


if __name__ == "__main__":
    sys.exit(main())

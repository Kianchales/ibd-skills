#!/usr/bin/env python3
"""案名规范化回改（幂等 · 干跑优先）

作用：把库内「案名引用位」的**截断简称**改为《方法论_案名规范表.md》登记的**规范案名（证券简称）**。
事实源：`<lib>/单案/*.md` 的 `case:` 字段 ＋ `<lib>/方法论_案名规范表.md` 表格首列（与 A4 门禁同源）。

改写规则（只动案名引用位，公司实体全称一律跳过）
  R1  **<词干>实证** → **<规范名>实证**
  R1b **<N案>实证** → **实证**（标签内禁写死案数）
  R2  <词干>案 → <规范名>案
  R3  **<词干>** → **<规范名>**
  R4  括号内／斜杠·顿号·加号分隔的并列引用位 → <规范名>

安全（工程范式 §4.7 六步）
  ① 必须先 `--report` 干跑并人工过目命中明细；② `--apply` 前逐文件写改前备份到 `<lib>/archive/_backup-casename-<date>/`
  ③ 落盘前三道自校验：双 CR 不得新增／行尾计数守恒／（.py）语法编译；④ 幂等（重跑 0 命中）

用法：python normalize_case_names.py --methods-root <工作区根> [--apply] [--report <md>] [--json]
退出码：0 = 完成（干跑或落盘）；1 = 自校验中止；2 = 用法或环境错误
"""
import argparse
import datetime
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SUFFIX = ("科技", "股份", "电子", "智能", "光电", "半导体", "技术", "仪器", "精密",
          "新材", "光子", "真空", "重工", "电气", "数字", "雷达", "材料", "设备", "影音")
COMP_SUFFIX = ("电子", "光电", "科技", "股份", "智能", "材料", "半导体", "技术", "仪器", "精密",
               "真空", "重工", "电气", "数字", "雷达", "新材", "光子", "设备", "影音", "实业",
               "集团", "有限", "制造", "器件", "线缆", "通信", "能源", "机械", "自动化", "医疗")
SKIP_DIRS = {"archive", "notes", "分卷", "__pycache__", "_backup"}
SKIP_TOP = {"方法论_条目标题目录.md", "方法论调用索引.md", "行业方法论_合并映射.md",
            "投行语言_旧编号映射表.md", "编号体系说明.md", "README.md",
            "通用方法论_最终版.md", "方法论_案名规范表.md"}
CANON_TABLE = "方法论_案名规范表.md"


def load_mapping(lib):
    """返回 (规范案名清单, 别名映射)。
    规范案名 = 单案 case 字段 ＋ 规范表「表一／表二」；
    别名映射 = 规范表「三、别名映射」节（旧写法 → 规范案名），仅供回改、不入 A4 白名单。"""
    canon, alias = [], {}
    for p in sorted(glob.glob(os.path.join(lib, "单案", "*.md"))):
        try:
            t = open(p, "rb").read().decode("utf-8")
        except OSError:
            continue
        m = re.search(r"(?m)^case:\s*(.+?)\s*$", t)
        if m:
            canon.append(m.group(1).strip())
    tp = os.path.join(lib, CANON_TABLE)
    if os.path.exists(tp):
        t = open(tp, "rb").read().decode("utf-8")
        cut = t.find("## 三")
        body, sec3 = (t[:cut], t[cut:]) if cut > 0 else (t, "")
        for m in re.finditer(r"(?m)^\|\s*([^|\s][^|]{0,24}?)\s*\|", body):
            name = m.group(1).strip()
            if name in ("规范案名", "现用写法") or "案名" in name or "写法" in name:
                continue
            canon.append(name)
        for m in re.finditer(r"(?m)^\|\s*([^|\s][^|]{0,24}?)\s*\|\s*([^|\s][^|]{0,24}?)\s*\|", sec3):
            old, new = m.group(1).strip(), m.group(2).strip()
            if old in ("库内旧写法", "现用写法", "写法") or "写法" in old:
                continue
            alias[old] = new
            canon.append(new)
    seen, out = set(), []
    for c in canon:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out, alias


def walk(lib):
    for dp, dn, fn in os.walk(lib):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in sorted(fn):
            if f.endswith(".md") and f not in SKIP_TOP:
                yield os.path.join(dp, f)


def main():
    ap = argparse.ArgumentParser(description="案名规范化回改（幂等 · 干跑优先）")
    ap.add_argument("--methods-root", default=os.environ.get("METHODS_ROOT") or os.getcwd(),
                    help="库所在的工作区根（其下须有 methods/）")
    ap.add_argument("--apply", action="store_true", help="落盘（默认只干跑）")
    ap.add_argument("--report", default=None, help="命中明细写入 md")
    ap.add_argument("--json", action="store_true", help="结构化输出")
    a = ap.parse_args()

    root = a.methods_root
    lib = os.path.join(root, "methods") if os.path.isdir(os.path.join(root, "methods")) else root
    if not os.path.isdir(lib):
        sys.stderr.write("[ERROR] 找不到库根：%s\n" % lib)
        return 2

    allcanon, alias_map = load_mapping(lib)
    if not allcanon:
        sys.stderr.write("[SKIP] 案名白名单为空（无单案文件亦无规范表）\n")
        return 3
    stems = {}
    for c in allcanon:
        for s in SUFFIX:
            if c.endswith(s) and len(c) > len(s):
                stems.setdefault(c[:-len(s)], c)
                break
    stems.update(alias_map)          # 别名映射并入（含「规范名比旧写法短」的反向情形）
    ordered = sorted(stems.items(), key=lambda kv: -len(kv[0]))

    hits = Counter()
    per_rule = defaultdict(list)
    files_touched, report = set(), []

    for p in walk(lib):
        rel = os.path.relpath(p, lib).replace("\\", "/")
        try:
            raw = open(p, "rb").read().decode("utf-8")
        except OSError:
            continue
        parts = re.split(r"(\r\n|\n)", raw)      # 行尾守恒：分隔符原样保留
        changed = False
        for idx in range(0, len(parts), 2):
            ln = parts[idx]
            orig = ln
            for stem, c in ordered:                                        # R1
                if "**%s实证**" % stem in ln:
                    ln = ln.replace("**%s实证**" % stem, "**%s实证**" % c)
                    hits["R1标签"] += 1
                    per_rule["R1标签"].append("%s:L%d %s" % (rel, idx // 2 + 1, orig.strip()[:110]))
            for m in list(re.finditer(r"\*\*([一两二三四五六七八九十\d]+案)实证\*\*", ln)):   # R1b
                ln = ln.replace(m.group(0), "**实证**")
                hits["R1b案数词"] += 1
                per_rule["R1b案数词"].append("%s:L%d %s" % (rel, idx // 2 + 1, orig.strip()[:110]))
            for stem, c in ordered:                                        # R2
                for m in re.finditer(re.escape(stem) + r"案", ln):
                    j = m.start()
                    if ln[m.end():m.end() + 1] == "例" or ln[j:j + len(c)] == c:
                        continue
                    ln = ln[:j] + c + "案" + ln[m.end():]
                    hits["R2案名+案"] += 1
                    per_rule["R2案名+案"].append("%s:L%d %s" % (rel, idx // 2 + 1, orig.strip()[:110]))
                    break
            for stem, c in ordered:                                        # R3
                for m in re.finditer(r"\*\*" + re.escape(stem) + r"\*\*", ln):
                    j = m.start()
                    if ln[j:j + len(c) + 4] == "**%s**" % c:
                        continue
                    ln = ln[:j] + "**%s**" % c + ln[m.end():]
                    hits["R3加粗案名"] += 1
                    per_rule["R3加粗案名"].append("%s:L%d %s" % (rel, idx // 2 + 1, orig.strip()[:110]))
                    break
            for _ in range(60):                                            # R4（收窄＋循环补全）
                done = True
                for stem, c in ordered:
                    for m in re.finditer(re.escape(stem), ln):
                        j, k = m.start(), m.end()
                        prev = ln[j - 1] if j else ""
                        nxt2 = ln[k:k + 4]
                        if ln[j:j + len(c)] == c:
                            continue
                        if any(nxt2.startswith(s) for s in COMP_SUFFIX):   # 公司实体全称
                            continue
                        if nxt2[:1] in "一二三四五六七八九十":              # 编号主体（微容一电子）
                            continue
                        if nxt2[:1] in "康市县区海洋集控资投基银证大学院群体营":
                            continue
                        # 旧写法是规范名的后缀（如「超硅」⊂「上海超硅」）：prev 必须是边界，防二次加前缀
                        if c.endswith(stem) and len(c) > len(stem) and prev not in "（(/、｜|＋+·—「【" and prev != "":
                            continue
                        in_paren = prev in "（(·「【" and (nxt2[:1] in "）)、，；： 」】" or nxt2 == "")
                        in_list = prev in "/、｜|＋+—" and (nxt2[:1] in "/、）)，｜|＋+— 的与" or nxt2 == "")
                        tail_list = prev not in "（(/｜|＋+" and nxt2[:1] in "/｜|＋+—"
                        if in_paren or in_list or tail_list:
                            ln = ln[:j] + c + ln[k:]
                            hits["R4案名引用"] += 1
                            per_rule["R4案名引用"].append("%s:L%d %s" % (rel, idx // 2 + 1, orig.strip()[:110]))
                            done = False
                            break
                    if not done:
                        break
                if done:
                    break
            if ln != orig:
                changed = True
            parts[idx] = ln
        if changed:
            files_touched.add(rel)
            report.append((p, "".join(parts), raw))

    if a.json:
        print(json.dumps({"tool": "normalize_case_names", "target": lib, "whitelist": len(allcanon),
                          "hits": dict(hits), "files": sorted(files_touched), "apply": bool(a.apply)},
                         ensure_ascii=False, indent=2))
    else:
        tally = "；".join("%s %d" % kv for kv in hits.most_common()) or "0 命中"
        print("=== 案名规范化回改（%s）：白名单 %d ｜ %s ｜ 涉及文件 %d"
              % ("APPLY" if a.apply else "DRY-RUN", len(allcanon), tally, len(files_touched)))
    if a.report:
        lines = ["# 案名规范化回改明细（%s）" % ("APPLY" if a.apply else "DRY-RUN"), "",
                 "命中：%s" % "；".join("%s %d" % kv for kv in hits.most_common()), ""]
        for rule in ("R1标签", "R1b案数词", "R2案名+案", "R3加粗案名", "R4案名引用"):
            if per_rule[rule]:
                lines.append("## %s（%d）" % (rule, len(per_rule[rule])))
                lines += ["- " + s for s in per_rule[rule][:400]]
        open(a.report, "w", encoding="utf-8", newline="\n").write("\n".join(lines))

    if not a.apply:
        return 0

    bkp = os.path.join(lib, "archive", "_backup-casename-%s" % datetime.date.today().strftime("%Y%m%d"))
    n = 0
    for p, new, raw in report:
        if new == raw:
            continue
        if new.count("\r\r") > raw.count("\r\r"):
            sys.stderr.write("[ABORT] 行尾污染（双 CR 新增）：%s\n" % p)
            return 1
        if new.count("\n") != raw.count("\n") or new.count("\r\n") != raw.count("\r\n"):
            sys.stderr.write("[ABORT] 行尾计数不守恒：%s\n" % p)
            return 1
        if p.endswith(".py"):
            try:
                compile(new, p, "exec")
            except SyntaxError:
                sys.stderr.write("[ABORT] 语法自校验失败：%s\n" % p)
                return 1
        dst = os.path.join(bkp, os.path.relpath(p, lib))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, "wb").write(raw.encode("utf-8"))
        open(p, "wb").write(new.encode("utf-8"))
        n += 1
    print("[APPLY] 落盘 %d 个文件；备份 %s" % (n, bkp))
    return 0


if __name__ == "__main__":
    sys.exit(main())

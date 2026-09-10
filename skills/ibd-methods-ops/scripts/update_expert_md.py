# -*- coding: utf-8 -*-
"""专家 MD 落库器（通用）：把某批次蒸馏条目追加到目标 MD 表格；超警戒线自动归档最早条目。

机制（保留自实战版）：
  1) 表行追加——新条目插入目标文件最后一个表格行之后；幂等（同编号已存在则跳过该文件）
  2) 超线归档——条目数超警戒线时，最早 (N - 保留数) 条移入 archive/蒸馏方法论_<维度>_<日期>.md，
     目标文件保留最近条目 + 追加归档索引行
  3) 铁律——只追加/搬移表格行，不改任何条目内容

用法：
    python update_expert_md.py --entries <条目.json> [--targets <映射.json>]
        [--methods-root <库根目录>] [--date YYYYMMDD] [--keep <警戒线.json>] [--dry-run]

参数：
    --entries  本批次条目数据（JSON：{"财务": [{"id": "F-AN0042-01", "title": "...", "core": "...", "scope": "..."}], ...}）
               维度键名可自定义，与 --targets 键一一对应
    --targets  维度 → 目标 MD 路径映射（JSON）；缺省映射到 {METHODS_ROOT}/methods/通用方法论_<维度>域.md
    --date     归档文件与索引行日期标签（默认执行日）
    --keep     警戒线（JSON：{"财务": 40, "法律": 30, "行业": 30, "写作": 40}；缺省即此默认值）
    --dry-run  只输出计划，不写盘

输入示例（entries.json）：
    {"财务": [{"id": "F-AN0042-01", "title": "退货双轨确认", "core": "…", "scope": "…"}]}
"""
import argparse, io, json, os, re, sys, datetime
from pathlib import Path

_ap = argparse.ArgumentParser(description="专家 MD 落库器（追加 + 超线归档）")
_ap.add_argument("--entries", required=True, help="本批次条目 JSON 路径")
_ap.add_argument("--targets", default="", help="维度→目标 MD 映射 JSON（缺省用 {库根}/methods/通用方法论_<维度>域.md）")
_ap.add_argument("--form", default="auto", choices=["auto", "h3", "table"],
                 help="目标形态：auto=自动识别（默认）/ h3=域文件条目形态 / table=MD 表格形态（专家 MD）")
_ap.add_argument("--methods-root", default=os.environ.get("METHODS_ROOT", ""),
                 help="方法论库根目录（默认 $METHODS_ROOT，或脚本上级目录）")
_ap.add_argument("--date", default="", help="归档日期标签（默认执行日）")
_ap.add_argument("--keep", default="", help="警戒线 JSON（默认 财务40/法律30/行业30/写作40）")
_ap.add_argument("--dry-run", action="store_true", help="只输出计划不写盘")
_args, _ = _ap.parse_known_args()

_HERE = Path(__file__).resolve().parent
_ROOT = Path(_args.methods_root) if _args.methods_root else _HERE.parent
_METHODS = _ROOT / "methods"
_ARCHIVE = _METHODS / "archive"
_DATE = _args.date or datetime.date.today().strftime("%Y%m%d")

DEFAULT_KEEP = {"财务": 40, "法律": 30, "行业": 30, "写作": 40}

_keep = dict(DEFAULT_KEEP)
if _args.keep:
    _keep.update(json.loads(_args.keep))

_entries = json.loads(io.open(_args.entries, encoding="utf-8").read())
if _args.targets:
    _targets = json.loads(io.open(_args.targets, encoding="utf-8").read())
else:
    _targets = {dim: str(_METHODS / ("通用方法论_%s域.md" % dim)) for dim in _entries}


def table_row(e):
    return "| %s | %s | %s | %s |" % (e.get("id", ""), e.get("title", ""), e.get("core", ""), e.get("scope", ""))


def h3_block(e):
    """域文件（h3 条目）形态：### 编号标题 + 段落；core 支持多段（\n\n 分隔，段落首可带 **小节**：）"""
    body = e.get("core", "").strip()
    scope = e.get("scope", "").strip()
    if scope:
        body += "\n\n**适用场景**：" + scope
    return "### %s%s\n\n%s\n" % (e.get("id", ""), e.get("title", ""), body)


def detect_form(path, lines):
    """auto 形态判定：优先看是否已有 h3 条目（### 编号开头），否则看表格行"""
    if any(re.match(r"^###\s+[A-Za-z]+-?\S*\d", ln) for ln in lines):
        return "h3"
    if any(ln.startswith("| ") for ln in lines):
        return "table"
    return "h3"  # 空文件默认按域文件形态追加


def update_one_h3(dim, rows, path):
    lines = io.open(path, encoding="utf-8").read().rstrip("\n").split("\n")
    exist = "\n".join(lines)
    new = [e for e in rows if ("### %s" % e.get("id", "")) not in exist]
    if not new:
        print("  · %s：全部条目已存在（幂等跳过）" % dim)
        return
    n_before = sum(1 for ln in lines if re.match(r"^###\s", ln))
    if _args.dry_run:
        print("  [dry-run] %s：将追加 %d 条（h3 形态），当前 %d 条 / 警戒线 %s" % (dim, len(new), n_before, _keep.get(dim, "—")))
        return
    blocks = "\n".join(h3_block(e) for e in new)
    io.open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n\n" + blocks)
    total = n_before + len(new)
    # h3（域文件）形态默认不判警戒线——域文件体积由 check_methods_health.py 管；仅显式 --keep 时提示
    keep_n = _keep.get(dim) if _args.keep else None
    over = "（超警戒线 %d，请归档早期条目）" % keep_n if keep_n and total > keep_n else ""
    print("  ✓ %s：追加 %d 条（h3 形态，当前共 %d 条）%s" % (dim, len(new), total, over))


def update_one(dim, rows):
    path = _targets.get(dim, "")
    if not path or not os.path.exists(path):
        print("  ⚠️ %s：目标文件不存在，跳过（%s）" % (dim, path))
        return
    lines = io.open(path, encoding="utf-8").read().split("\n")
    form = _args.form if _args.form != "auto" else detect_form(path, lines)
    if form == "h3":
        update_one_h3(dim, rows, path)
        return
    tbl = [i for i, ln in enumerate(lines) if ln.startswith("| ")]
    if not tbl:
        print("  ⚠️ %s：目标文件无表格行，跳过" % dim)
        return
    exist_ids = set()
    for i in tbl:
        cells = lines[i].split("|")
        if len(cells) >= 3:
            exist_ids.add(cells[1].strip())
    new_rows = [table_row(e) for e in rows if e.get("id", "") not in exist_ids]
    if not new_rows:
        print("  · %s：全部条目已存在（幂等跳过）" % dim)
        return
    if _args.dry_run:
        print("  [dry-run] %s：将追加 %d 条，当前 %d 条 / 警戒线 %d" % (dim, len(new_rows), len(tbl), _keep.get(dim, 999)))
        return
    insert_at = tbl[-1] + 1
    lines[insert_at:insert_at] = new_rows
    total = len(tbl) + len(new_rows)
    # 超线归档
    keep_n = _keep.get(dim)
    if keep_n and total > keep_n:
        tbl2 = [i for i, ln in enumerate(lines) if ln.startswith("| ")]
        cut = len(tbl2) - keep_n
        arch_rows = [lines[i] for i in tbl2[:cut]]
        _ARCHIVE.mkdir(parents=True, exist_ok=True)
        arch_file = _ARCHIVE / ("蒸馏方法论_%s_%s.md" % (dim, _DATE))
        head = "# 蒸馏方法论归档 · %s（%s）\n\n> 由 update_expert_md.py 超线归档（保留最近 %d 条）\n\n" % (dim, _DATE, keep_n)
        io.open(arch_file, "w", encoding="utf-8").write(head + "\n".join(arch_rows) + "\n")
        del lines[tbl2[0]:tbl2[0] + cut]
        idx_line = "> 归档索引：早期 %d 条见 `archive/%s`（%s）" % (cut, arch_file.name, _DATE)
        lines.insert(0, idx_line)
        print("  ✓ %s：追加 %d 条 + 归档 %d 条 → %s" % (dim, len(new_rows), cut, arch_file.name))
    else:
        print("  ✓ %s：追加 %d 条（当前共 %d 条）" % (dim, len(new_rows), total))
    io.open(path, "w", encoding="utf-8").write("\n".join(lines))


def main():
    print("=== 专家 MD 落库（库根: %s）===" % _ROOT)
    for dim, rows in _entries.items():
        update_one(dim, rows)
    print("=== 完成%s ===" % ("（dry-run 未写盘）" if _args.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())

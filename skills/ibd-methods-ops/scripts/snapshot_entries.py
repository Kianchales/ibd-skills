#!/usr/bin/env python3
"""条目快照与差异对比 —— 批量改动的机器视角

用途
    批量改动（重蒸馏 / 回写 / 编号迁移 / 重构 / 格式统一）之前拍一次快照，
    改动之后再拍一次并 diff：直接列出「哪些条目正文变了、哪条实证少了案、
    哪些条目新增或消失」，不必通读比对。

用法
    # 改动前
    python snapshot_entries.py --methods-root <工作区根> --out state/_snap_before.json
    # 改动后（与 before 对比）
    python snapshot_entries.py --methods-root <工作区根> --diff state/_snap_before.json

设计边界（有意为之）
    · **只读**：不写库、不改任何文件；唯一写盘是 --out 指定的快照文件。
    · **只认编号行**：四类编号形态（[FLIS]-NNNNNN / WL- / PL- / I-CL / X-ANYYYY-NN），
      章节头（`### （一）…`、`### 子行业：…`、`### 族 A …`）天然不入选，无需维护排除表。
    · **正文段 / 实证段分离**：以 `**…实证**：` 行分界。正文段算 sha256（改一个标点也抓得到），
      实证段只抓规范案名集合（追加允许，少一个即报）。
    · **归一化只做三条**：CRLF→LF、行尾空白、首尾空行。不做压空行/去标点/大小写归一,
      那些会掩盖真实改动，与工具目的相反。
    · **不做判定**：本脚本只报"变了什么"，不判断"该不该变"；无差异退出码 0，
      有差异仍为 0（诊断工具不阻断流程），加 --fail-on-change 才返回 1。
"""
import argparse
import hashlib
import io
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_ap = argparse.ArgumentParser(description="条目快照 / 差异对比（只读）")
_ap.add_argument("--methods-root", default=os.environ.get("METHODS_ROOT", ""),
                 help="工作区根（= 库根，其下含 methods/；默认 $METHODS_ROOT）")
_ap.add_argument("--out", default="", help="生成快照 JSON 到指定路径")
_ap.add_argument("--diff", default="", help="与指定快照 JSON 对比，仅报告差异")
_ap.add_argument("--json", action="store_true", help="差异以 JSON 输出（默认人类可读）")
_ap.add_argument("--fail-on-change", action="store_true",
                 help="有差异时返回退出码 1（供批处理闸门使用）")
_ap.add_argument("--quiet", action="store_true", help="只输出统计行")
_args = _ap.parse_args()

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)
from _lib.layout import (  # noqa: E402
    resolve as _layout_resolve, METHODS_NAME, DIR_DOMAIN, DIR_LANG,
    DIR_INDUSTRY, DIR_SINGLE, DIR_VOLUME, GENERATED_NAME, NOTES_NAME, CANON_TABLE,
)

ROOT, METHODS, SCRIPTS = _layout_resolve(_args.methods_root)

# ── 扫描面：正文五区（跨案域/语言专项/行业版/单案/分卷）────────────────────
SCAN_DIRS = [DIR_DOMAIN, DIR_LANG, DIR_INDUSTRY, DIR_SINGLE, DIR_VOLUME]
SKIP_DIRS = {GENERATED_NAME, NOTES_NAME, "__pycache__", "_backup"}

# ── 条目行：编号必须紧跟在行首（### / - ** / **）之后 ──────────────────────
# 负向断言排除「并列引用」形态：`- **F-AN0018-01/F-AN0018-03**：…` 是正文里一次引用多个
# 编号，不是条目定义（实证：耀泰股份第 286 行，误收会让 8 条被判重复）。
RX_EID = r"(?:WL|PL|[FLIS])-\d{6}|I-CL\d{2}-\d{2}|[FLIS]-AN\d{4}-\d{2}"
RX_ENTRY_LINE = re.compile(
    r"^(?:###\s+|- \*\*|\*\*)\s*(" + RX_EID + r")(?![\/、，,；;])"
)

# ── 实证段起点：加粗短语含「实证」二字并带冒号（允许前缀为空）──────────────
RX_EVID_START = re.compile(r"^\s*(?:-\s+)?\*\*[^*\n]*实证\*\*\s*[：:]")

# ── 正文段结束硬顶（防某条实证标记缺失时把整节吞进正文）────────────────────
RX_SECTION_END = re.compile(r"^#{2,3}\s")


def _require_library():
    if not os.path.isdir(METHODS):
        sys.stderr.write("✗ 未找到方法论库：%s\n" % METHODS)
        sys.stderr.write("  用法：--methods-root <工作区根>（或设环境变量 METHODS_ROOT）\n")
        sys.exit(2)


def norm(text):
    """归一化三条：CRLF→LF、行尾空白、首尾空行。其余原样。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip() for ln in text.split("\n")]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def sha16(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def clean_title(line, eid):
    """从条目行取标题：剥前缀符号、编号、管道符与加粗星号。"""
    s = line.strip()
    s = re.sub(r"^-\s*\*\*", "", s)
    s = re.sub(r"^###\s+", "", s)
    s = re.sub(r"^\*\*", "", s)
    if s.startswith(eid):
        s = s[len(eid):]
    s = s.replace("**", "")
    s = re.sub(r"^[\s｜|:：]+", "", s)
    return s.strip()[:100]


def load_canon_names():
    """读《方法论_案名规范表.md》表一＋表二的白名单（表三别名不入）。"""
    path = os.path.join(METHODS, CANON_TABLE)
    names = []
    if not os.path.isfile(path):
        return names
    in_alias_table = False
    with io.open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if re.match(r"^##\s*三、", s):
                in_alias_table = True
                continue
            if re.match(r"^##\s*(一|二)、", s):
                in_alias_table = False
                continue
            if in_alias_table or not s.startswith("|"):
                continue
            cells = [c.strip() for c in s.strip("|").split("|")]
            if not cells:
                continue
            name = cells[0]
            if not name or name in ("规范案名", "案名") or set(name) <= set("-: "):
                continue
            if 2 <= len(name) <= 12:
                names.append(name)
    return names


def build_name_rx(names):
    """白名单合成单条正则（长名优先，防短名截断长名）。"""
    if not names:
        return None
    ordered = sorted(set(names), key=len, reverse=True)
    return re.compile("|".join(re.escape(n) for n in ordered))


def scan_files():
    out = []
    for d in SCAN_DIRS:
        base = os.path.join(METHODS, d)
        if not os.path.isdir(base):
            continue
        for fn in sorted(os.listdir(base)):
            if not fn.endswith(".md"):
                continue
            if fn in SKIP_DIRS:
                continue
            out.append(os.path.join(base, fn))
    return out


def iter_entries(path, allow_list_forms):
    """按编号行切块，产出 (eid, title, body_norm, evidence_text)。

    `allow_list_forms` 只对「投行语言专项_*」卷文件为真：该系列的 WL 条目有两种
    非 h3 书写形态（`**WL-xxxxxx 标题**` / `- **WL-xxxxxx**｜标题`）。其余文件里
    同样的行是**正文中的编号引用**（实证：耀泰股份第 287–293 行「适用场景」清单
    逐条列 `- **F-AN0018-02**：…`），按条目收纳会把引用变成假条目、并判成重复编号。
    """
    with io.open(path, "r", encoding="utf-8") as f:
        lines = f.read().split("\n")

    starts = []
    for i, ln in enumerate(lines):
        m = RX_ENTRY_LINE.match(ln)
        if not m:
            continue
        if not allow_list_forms and not ln.startswith("###"):
            continue
        starts.append((i, m.group(1)))

    for k, (i, eid) in enumerate(starts):
        end = starts[k + 1][0] if k + 1 < len(starts) else len(lines)
        block = lines[i:end]

        ev_idx = None
        for j, ln in enumerate(block):
            if RX_EVID_START.match(ln):
                ev_idx = j
                break
        if ev_idx is None:
            # 无实证标记：正文到本节结束（防止吞下一节），整块算正文
            cut = None
            for j in range(1, len(block)):
                if RX_SECTION_END.match(block[j]):
                    cut = j
                    break
            body_lines = block[:cut] if cut else block
            ev_text = ""
        else:
            body_lines = block[:ev_idx]
            ev_text = "\n".join(block[ev_idx:])

        yield eid, clean_title(block[0], eid), norm("\n".join(body_lines)), ev_text


def take_snapshot():
    _require_library()
    names = load_canon_names()
    name_rx = build_name_rx(names)
    entries = {}
    dups = []
    for path in scan_files():
        rel = os.path.relpath(path, METHODS).replace("\\", "/")
        allow_list = os.path.basename(path).startswith("投行语言专项")
        try:
            for eid, title, body, ev in iter_entries(path, allow_list):
                if eid in entries:
                    dups.append((eid, entries[eid]["file"], rel))
                    continue
                cases = sorted(set(name_rx.findall(ev))) if (name_rx and ev) else []
                entries[eid] = {
                    "title": title,
                    "file": rel,
                    "body_sha256": sha16(body),
                    "evidence_cases": cases,
                }
        except (IOError, OSError, UnicodeDecodeError) as e:
            sys.stderr.write("⚠ 跳过不可读文件 %s：%s\n" % (rel, e))
    return {
        "schema": "methods-entries-snapshot/1",
        "canon_names": len(names),
        "total": len(entries),
        "entries": entries,
    }, dups


def load_snapshot(path):
    with io.open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def diff_snapshots(before, now):
    b = before.get("entries", {})
    n = now.get("entries", {})
    added = sorted(set(n) - set(b))
    removed = sorted(set(b) - set(n))
    changed, ev_loss, ev_gain, moved = [], [], [], []
    for eid in sorted(set(b) & set(n)):
        old, cur = b[eid], n[eid]
        if old.get("body_sha256") != cur.get("body_sha256"):
            changed.append(eid)
        oc, cc = set(old.get("evidence_cases") or []), set(cur.get("evidence_cases") or [])
        if oc - cc:
            ev_loss.append((eid, sorted(oc - cc)))
        if cc - oc:
            ev_gain.append((eid, sorted(cc - oc)))
        if old.get("file") != cur.get("file") and old.get("body_sha256") == cur.get("body_sha256"):
            moved.append((eid, old.get("file"), cur.get("file")))
    return {
        "added": added, "removed": removed, "body_changed": changed,
        "evidence_lost": ev_loss, "evidence_added": ev_gain, "moved": moved,
    }


def report(d, before, now):
    total_changes = (len(d["added"]) + len(d["removed"]) + len(d["body_changed"])
                     + len(d["evidence_lost"]) + len(d["moved"]))
    print("=== 条目快照差异（before → now）===")
    print("基线 %d 条 → 当前 %d 条 ｜ 差异 %d 项"
          % (before.get("total", 0), now.get("total", 0), total_changes))
    print("")
    if not total_changes:
        print("PASS 无差异：所有条目正文与实证案名集合均未变化")

    def head(t, items, fmt=None):
        if not items:
            return
        print("%s（%d）" % (t, len(items)))
        for it in items[:30]:
            print("  " + (fmt(it) if fmt else str(it)))
        if len(items) > 30:
            print("  … 其余 %d 项省略（用 --json 取全量）" % (len(items) - 30))
        print("")

    head("正文变更", d["body_changed"])
    head("实证减少（疑似被删）", d["evidence_lost"],
         lambda x: "%s  少了：%s" % (x[0], "、".join(x[1])))
    head("条目消失", d["removed"])
    head("条目新增", d["added"])
    head("条目搬家（内容未变）", d["moved"],
         lambda x: "%s  %s → %s" % x)
    if d["evidence_added"]:
        print("实证追加（正常回写动作，仅计数）：%d 条" % len(d["evidence_added"]))
    return total_changes


def main():
    if not _args.out and not _args.diff:
        _ap.error("至少给一个：--out 生成快照 / --diff 对比快照")

    now, dups = take_snapshot()
    if dups:
        sys.stderr.write("⚠ 发现重复编号 %d 处（已保留首次出现）：\n" % len(dups))
        for eid, f1, f2 in dups[:10]:
            sys.stderr.write("  %s  %s  vs  %s\n" % (eid, f1, f2))
        sys.stderr.write("  → 重复编号属结构问题，用 check_methods_health.py 定位修复\n")

    if _args.out:
        out_path = _args.out
        os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
        with io.open(out_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(now, f, ensure_ascii=False, indent=1, sort_keys=True)
            f.write("\n")
        if not _args.quiet:
            print("快照已写入 %s ｜ 条目 %d ｜ 案名白名单 %d"
                  % (out_path, now["total"], now["canon_names"]))
            print("（改动后：--diff %s）" % out_path)

    if _args.diff:
        before = load_snapshot(_args.diff)
        d = diff_snapshots(before, now)
        if _args.json:
            print(json.dumps(d, ensure_ascii=False, indent=1))
            changes = (len(d["added"]) + len(d["removed"]) + len(d["body_changed"])
                       + len(d["evidence_lost"]) + len(d["moved"]))
        else:
            changes = report(d, before, now)
        if _args.fail_on_change and changes:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

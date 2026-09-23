#!/usr/bin/env python3
"""条目书写契约自检 —— 校验方法论库「实证段标签」与「来源标注」是否符合契约。

契约单一事实源：references/entry-contract.md（v1.0 · 2026-09-19 用户裁定 D1–D5）

检查项
  A1 实证标签只允许 `**实证**` 或 `**<案名>实证**`（案名 ≤6 字）；命中禁用形态报 ERROR
     （本案实证／标签内案数／标签内日期·回写／标签括号内塞案名）
     受理形态**两种**（2026-09-23 修正）：行首 `**X实证**` ＋ 顶层列表项 `- **X实证**：`；
     缩进列表项视为内容小标题不检查（原实现只认行首 ⇒ 覆盖仅 7.7%，判 I-0088）
  A2 来源标注：跨案层须为 `（来源简称 P页码）`；检出「页码在前」「中文来源名未换简称」
     「轮次前缀未换问N」等旧形态报 ERROR
  A3 单案层字段名：须为规范要素名（§S4 五要素 ＋ §S5 三要素 ＋ 契约登记的 3 个扩展字段）；
     命中**已废止别名**（规则／实证／可复用句式／关系标注／锚点／要点…）报 ERROR；
     形态受理面（2026-09-23／24 两次扩面）：① **顶格形**（无列表符）登记为合法第二形态；
     ② **冒号前允许一段「出处括注」**（`**原文示例**（招股书 PAGE 7）：` 形态原被静默漏检，判 I-0068）；
     ③ `实证` 判据＝**后跟冒号（可接一段括注）即字段名**（无冒号不判，保留 A1 标签空间）。
     **白名单外的内容小标题／门禁标记一律不检查**（强制面收缩原则）
  A4 案名白名单：实证标签中的案名须为规范案名（证券简称，白名单＝单案 case 字段 ＋
     《方法论_案名规范表.md》）；命中「截断案名／未登记案名／写死案数」报 ERROR
     形态受理面同 A1；判定前先剥标签尾部括注（`本案实证（AN0044）` ⇒ 主体「本案实证」）

用法：python check_entry_contract.py --methods-root <工作区根> [--json]
退出码：0 = PASS（0 ERROR）；1 = FAIL；2 = 用法或环境错误；3 = SKIP（无可检对象）
"""
import argparse
import glob
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import os as _lo, sys as _ls
_ls.path.insert(0, _lo.path.dirname(_lo.path.abspath(__file__)))
from _lib.layout import SKIP_DIRS, VOLUME_NAME as VOLUME_DIR, TOP_LEVEL_NON_ENTRY as EXCLUDE_TOP, CANON_TABLE, SINGLE_NAME, SUB_INDUSTRY_NAME, METHODS_NAME
# 分卷（`50_分卷/*.md`）= 手写条目正文外置件（P 系列 PL- ／体例域批次卷 S-），2026-09-19 起纳入检查：
#   只跑 A2（来源标注）＋ A4（案名白名单）——**不跑 A1/A3**（分卷内用「语用／方法／规则要点」等自成一套字段，
#   与主库字段规范不同源，强套会产生大量无意义 ERROR）
NOT_A_CASE = {"本案", "原文", "实证", "扩展", "强化", "差异", "反面", "正面", "对照", "边界",
              "多案"}   # `多案`：S7 纪律⑦「统一用多案验证／多案共通」⇒ 合法形态、非案名（2026-09-23 补）
COUNT_LABEL = re.compile(r"^[一两二三四五六七八九十\d]+案$")

SRC_NAMES = "招股书|注册稿|上会稿|问询回复|反馈意见回复"

# 实证标签**形态集**（2026-09-23 修正 · 原实现只认行首 ⇒ 漏掉回写器产出的列表形态，覆盖仅 7.7%，判 I-0088）：
#   ① 行首 `**<案名>实证**`        —— 排布 2 的原生形态
#   ② 顶层列表项 `- **<案名>实证**：` —— `apply_rewrite.py` 回写产出的**主流形态**（占库内 92%）
#   **只认「列 0」的这两种**：缩进列表项（`  - **X实证**`）一律视为**内容小标题**、不检查
#   —— 实测缩进位 5 处全部是描述性小标题（「跨章复用微差实证」「重排实证」等），非案名。
#      故本正则**不含前导 `[ \t]*`**（原实现在此允许缩进，是漏检与误报的双重来源）。
#   另两道收窄（挡掉内容小标题，实测把误报从 74 处降到 2 处）：
#      · 主体先剥**尾部括注**再判定（`本案实证（AN0044）`／`多案实证（≥3 案）` ⇒ 主体为「本案实证」／「多案实证」）
#      · 只受理**以「实证」结尾**的主体（挡掉 `实证页码`／`原文实证与计数` 这类非实证标签）
BAN_LABEL = re.compile(r"(?m)^(?:[-*][ \t]+)?\*\*([^*\n]{1,24})\*\*")
TRAIL_PAREN = re.compile(r"[（(][^）)]*[）)]\s*$")


def core_label(name):
    """剥掉标签尾部括注（可嵌套多层）后的主体，如 `本案实证（AN0044）` → `本案实证`。"""
    prev, s = None, name.strip()
    while prev != s:
        prev, s = s, TRAIL_PAREN.sub("", s).strip()
    return s


def is_evidence_label(name):
    """是否为「实证标签」——主体须以「实证」结尾（内容小标题如 `实证页码` 不算）。"""
    return core_label(name).endswith("实证")


GOOD_LABEL = re.compile(r"^实证$|^[^*\n]{1,6}实证$|^实证（互补）$|^[^*\n]{1,6}实证（互补）$")
BAD_SRC = [
    ("页码在前", re.compile(r"PAGE\s*[\d\-、]+\s*(" + SRC_NAMES + r")"), "来源标注「页码在前」"),
    ("中文来源名未换简称", re.compile(r"(?<!·)(" + SRC_NAMES + r")\s*[Pp](?=[\dP])"),
     "中文来源名未换简称（招/问1/上会/反馈）"),
    # 2026-09-19 补：旧式「来源名 ＋ PAGE N」（原规则只抓「…P123」，抓不到 AGE 形态）
    ("来源名＋PAGE", re.compile(r"(?<!·)(" + SRC_NAMES + r")\s*PAGE\s*\d"),
     "中文来源名＋PAGE（应用简称：招 P／招·注册稿 P／问1 P…）"),
    ("轮次＋PAGE", re.compile(r"第\s*\d\s*轮\s*PAGE\s*\d"), "轮次＋PAGE（应用「问N P…」）"),
    ("轮次前缀未换问N", re.compile(r"(?:第)?\s*\d+\s*轮\s*P(?:AGE)?\s*\d"), "轮次前缀未换「问N P…」"),
    ("来源叠加损坏", re.compile(r"招·招·|招股书招·"), "来源简称叠加（写入损坏）"),
]

CORE_FIELDS = ["规则要点", "本案实证", "可复用结论", "对照锚点",
               "投行语言特征", "原文实证", "适用场景", "句式模板", "边界条件",
               "拆解"]
# 2026-09-23：`拆解` 由「已废止别名」**上提为规范要素**（第 10 个）——
#   W 条目固定段序「投行语言特征 → 原文实证 → 拆解 → 句式模板 → 适用场景」中，
#   `拆解` 承载「为什么这样写」的机理解释，与 `投行语言特征`（是什么）语义不同，
#   21 处稳定一致出现 ⇒ 属漏登记要素而非别名（用户 2026-09-23 裁定「都按你建议搞」）。
ABOLISHED = ("规则|可复用句式|核心句式|典型句式|句式结构|可复用句|原文示例|关系|关系标注|旧条目关系|"
             "锚点|锚点关系|对照|归属|写作范式锚点|吸收来源|落位吸收|关联|要点|知识要点|方法论要点|"
             "规则提炼|规则/要点|情形/规则|规则名|适用|适用问题|场景|情境触发|问题|可复用写法|"
             "写法/可复用|可迁移|写作要点|写法要点|套用要点|措辞要点|写作启示|可复用结论（写作切入）|"
             "实证出处|来源|关键证据|实证（归因论证）|阅读包内实证|案例支撑|边界/复用|边界提示|反模式警示")
# 2026-09-23（判 I-0091）：**受理面扩至「顶格形」** —— 原只受理 `- **X**：`，实测顶格形
#   `**X**：`（无列表符）共 5,067 处 = 全部字段标签的 **20.5%**，此前**完全不受检**，
#   其中废止别名 1,315 处（已同批归一）。采用 **A′**：把顶格形登记为**合法第二形态**
#   （只查字段名、不管形态），避免为统一形态改动 20% 库面。
# 2026-09-24（判 I-0068）：**受理面补「出处括号」形态** —— 原要求字段名后**紧跟冒号**，
#   而库内存在 `- **原文示例**（招股书 PAGE 7）：…` 这类「字段名 →（出处）→ 冒号」写法，
#   正则不匹配 ⇒ **静默零检出**（实测该形态 237 处、捕获 0）。现改为**冒号前允许一段括注**。
#   `实证` 单列处理的**口径同步收紧**（原「顶格形不判、列表形仍判」）：
#   实测 40_单案 四象限 —— 列表+无括注 **0** ／ 列表+有括注 **56** ／ 顶格+无括注 **317** ／ 顶格+有括注 **210**，
#   抽查全部 583 处的**行内容均为实证正文**（含纯出处如「注册稿 PAGE 8。」）、**无一为 A1 实证标签**
#   —— 判据改为「**`**实证**` 后（可接一段括注）**紧跟冒号 ⇒ 字段名**」；无冒号者不判（保留 A1 标签空间）。
#   同批已归一 819 处（实证→本案实证 583／原文示例→原文实证 234／规则→规则要点 2）。
_PAREN = r"(?:[（(][^）)\n]*[）)])?"
BAD_SINGLE = [("已废止别名", re.compile(r"(?m)^[ \t]*(?:[-*][ \t]+)?\*\*(" + ABOLISHED + r")\*\*" + _PAREN + r"[：:]"),
               "单案层字段名须为规范要素名（%s）" % "／".join(CORE_FIELDS)),
              ("已废止别名·实证", re.compile(r"(?m)^[ \t]*(?:[-*][ \t]+)?\*\*实证\*\*" + _PAREN + r"[：:]"),
               "「实证」为已废止字段名，应写「本案实证」（判据：`**实证**` 后（可接一段括注）紧跟冒号；无冒号不判，保留 A1 标签空间）")]


def load_whitelist(lib):
    """案名白名单：单案 case 字段 ＋ 《方法论_案名规范表.md》表格首列（规范案名／已登记项 ＋ 待确认项）。"""
    wl = set()
    for p in glob.glob(os.path.join(lib, SINGLE_NAME, "*.md")):
        try:
            t = open(p, "rb").read().decode("utf-8")
        except OSError:
            continue
        m = re.search(r"(?m)^case:\s*(.+?)\s*$", t)
        if m:
            wl.add(m.group(1).strip())
    tp = os.path.join(lib, CANON_TABLE)
    if os.path.exists(tp):
        try:
            t = open(tp, "rb").read().decode("utf-8")
        except OSError:
            t = ""
        # 只取表一＋表二（规范案名）；「三、别名映射」是待回改的旧写法，不入白名单
        cut = t.find("## 三")
        if cut > 0:
            t = t[:cut]
        for m in re.finditer(r"(?m)^\|\s*([^|\s][^|]{0,24}?)\s*\|", t):
            name = m.group(1).strip()
            if name in ("规范案名", "现用写法") or "案名" in name or "写法" in name:
                continue
            if not re.search(r"[0-9A-Za-z\u4e00-\u9fff]", name):
                continue          # 2026-09-23：跳过分隔行（`---`）等纯符号"案名"——原会混入白名单
            wl.add(name)
    return wl


def check_case_name(t, rel, whitelist):
    """A4 案名白名单：实证标签中的案名须为规范案名（证券简称），禁截断／未登记／案数词。"""
    out = []
    for m in BAN_LABEL.finditer(t):
        name = m.group(1)
        if not is_evidence_label(name):
            continue
        m2 = re.match(r"^(.{1,24}?)实证$", core_label(name))
        case = m2.group(1) if m2 else core_label(name)
        if not case or case in NOT_A_CASE or case in whitelist:
            continue
        ln = t[:m.start()].count("\n") + 1
        if COUNT_LABEL.match(case):
            out.append(("ERROR", "A4", "%s:L%d" % (rel, ln),
                        "标签内写死案数：**%s**（案数随回写变化，须用 `**实证**`）" % name[:24]))
            continue
        near = [w for w in whitelist if len(case) >= 2 and w.startswith(case)]
        if near:
            out.append(("ERROR", "A4", "%s:L%d" % (rel, ln),
                        "截断案名：**%s** → 应为 **%s实证**（规范案名＝证券简称）" % (name[:24], sorted(near, key=len)[0])))
        else:
            out.append(("ERROR", "A4", "%s:L%d" % (rel, ln),
                        "未登记案名：**%s**（须先用规范案名登记入《%s》）" % (name[:24], CANON_TABLE)))
    return out


def scan(path, rel, is_single, whitelist=None):
    out = []
    try:
        t = open(path, "rb").read().decode("utf-8")
    except OSError as e:
        return [("ERROR", "IO", rel, "读取失败: %s" % e)]
    # 分卷（手写条目正文外置件）：只跑 A2（来源）＋ A4（案名），跳过 A1/A3
    if rel.split("/")[0] == VOLUME_DIR:
        for _, rx, msg in BAD_SRC:
            for m in rx.finditer(t):
                ln = t[:m.start()].count("\n") + 1
                out.append(("ERROR", "A2", "%s:L%d" % (rel, ln), "%s —— %s" % (msg, m.group(0)[:40])))
        if whitelist is not None:
            out += check_case_name(t, rel, whitelist)
        return out
    for m in BAN_LABEL.finditer(t):
        name = m.group(1)
        if not is_evidence_label(name):
            continue
        if GOOD_LABEL.match(core_label(name)):
            continue
        ln = t[:m.start()].count("\n") + 1
        out.append(("ERROR", "A1", "%s:L%d" % (rel, ln), "实证标签不在契约白名单：**%s**" % name[:24]))
    if not is_single:
        for _, rx, msg in BAD_SRC:
            for m in rx.finditer(t):
                ln = t[:m.start()].count("\n") + 1
                out.append(("ERROR", "A2", "%s:L%d" % (rel, ln), "%s —— %s" % (msg, m.group(0)[:40])))
    if is_single:
        for _, rx, msg in BAD_SINGLE:
            for m in rx.finditer(t):
                ln = t[:m.start()].count("\n") + 1
                out.append(("ERROR", "A3", "%s:L%d" % (rel, ln), "%s —— %s" % (msg, m.group(0)[:40])))
    if whitelist is not None:
        out += check_case_name(t, rel, whitelist)
    return out


def main():
    ap = argparse.ArgumentParser(description="条目书写契约自检（只读）")
    ap.add_argument("--methods-root", default=os.environ.get("METHODS_ROOT") or os.getcwd(),
                    help="库所在的工作区根（其下须有 methods/）")
    ap.add_argument("--json", action="store_true", help="结构化输出")
    a = ap.parse_args()

    root = a.methods_root
    _mq = os.path.join(root, METHODS_NAME)
    lib = _mq if os.path.isdir(_mq) else root
    if not os.path.isdir(lib):
        sys.stderr.write("[ERROR] 找不到库根：%s\n" % lib)
        return 2

    targets = []
    for dp, dirs, files in os.walk(lib):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in sorted(files):
            if not f.endswith(".md"):
                continue
            rel = os.path.relpath(os.path.join(dp, f), lib).replace("\\", "/")
            if "/" not in rel and rel in EXCLUDE_TOP:
                continue
            is_single = rel.startswith(SINGLE_NAME + "/") or rel.startswith(SUB_INDUSTRY_NAME + "/")
            is_volume = rel.split("/")[0] == VOLUME_DIR
            targets.append((os.path.join(dp, f), rel, is_single))
    if not targets:
        print("[SKIP] 无可检对象")
        return 3

    issues = []
    whitelist = load_whitelist(lib)
    for p, rel, is_single in targets:
        issues += scan(p, rel, is_single, whitelist)
    n_err = sum(1 for i in issues if i[0] == "ERROR")

    if a.json:
        print(json.dumps({"tool": "check_entry_contract", "target": lib, "scanned": len(targets),
                          "whitelist": len(whitelist),
                          "error": n_err, "warn": 0,
                          "issues": [{"level": l, "code": c, "where": w, "msg": m} for l, c, w, m in issues],
                          "verdict": "PASS" if n_err == 0 else "FAIL"}, ensure_ascii=False, indent=2))
    else:
        print("=== 条目书写契约自检：@ %s" % lib)
        for l, c, w, m in issues[:40]:
            print("   [%s] %s %s %s" % (l, c, w, m))
        if len(issues) > 40:
            print("   … 另 %d 条" % (len(issues) - 40))
        print("--- 扫描 %d 文件（案名白名单 %d）：ERROR = %d —— %s"
              % (len(targets), len(whitelist), n_err, "PASS ✅" if n_err == 0 else "FAIL ★"))
    return 0 if n_err == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
S4 专家产出自检脚本（格式门禁 · 与 distill-methods.md §S4 编号规范配套）

用途：S4 三专家产出 `产出_<维度>_<公司>蒸馏.md` 后、S5 综合成文前，由 lead 跑本脚本做格式门禁；
     0 FAIL 才允许进入 S5。规范单一事实源 = skill ibd-methods-ops references/distill-methods.md §S4。

用法：
    python scripts/check_expert_output.py <file.md> [<file.md> ...]
    python scripts/check_expert_output.py --dir <案工作目录>      # 自动扫目录下 产出_*.md
退出码：0 = 全部 PASS；1 = 存在 FAIL。

编号规范（2026-09-06 v2 · 三层隔离 + 案号 4 位）：
  案例层 S4 产出 = 落库同构编号——知识 `### <域>-C{案号4位}-<2位序号>｜标题`（F-C0041-01｜…）
                                  范式 `### W-C{案号4位}-<类><2位序号>｜标题`（W-C0041-A01/F01｜…，类=A-D 句法族/F-L-I 业务域）
  案代号字母码（F-JH-01 型）与 2 位案号（F-C41-01 型）为历史遗留形态 → WARN 提示，不计 FAIL（迁移前旧文件）

校验项（C1-C7）：
  C1 文件头标题：`# <persona>·<维度>蒸馏·<简称>（<板块>·<阶段>·<稿本日期>）`
  C2 蒸馏人署名行：`蒸馏人：<persona>（<agent_id>，...）｜YYYY-MM-DD`
  C3 三节标题锁定：`## 一、知识蒸馏（N 条）` → `## 二、写作范式（N 条）` → `## 三、亮点/风险提示`
  C4 知识条目标题：案号 4 位、序号 2 位补零、`｜` 分隔（禁空格/禁加粗/禁四级标题/禁案代号字母）
  C5 范式条目标题：同上 + 类位白名单 A-D/F-L-I
  C6 条数与节标题计数一致
  C7 无加粗条目、无 1 位序号；案代号/2 位案号历史形态 WARN

S4-pre 分析卡门禁（--stage pre · WO-34 · 2026-10-17）：
  P1 文件头标题：`# <persona>·<维度>分析卡·<简称>`
  P2 蒸馏人署名行：同 C2
  P3 四节结构锁定：`## 一、本案要点` → `## 二、与既有条目的关系` → `## 三、矛盾与张力` → `## 四、建议落族`
  P4 关系标注形态：第二节内须含 `[强化:编号]`／`[扩展:编号]`／`[新增]` 至少一处；非法编号引用 ⇒ FAIL
  P5 篇幅上限：全文 ≤ 2000 字符（半页卡；超限 FAIL——分析卡不是成稿）
  P6 防幻觉抽检：「据我所知」等无来源论断标记 ⇒ WARN（提示人工复核）

已知边界（诚实声明）：
  · P4 非法编号判定只查「形态合法性」（族前缀+数字位数），**不查编号是否真实在册**——
    在册校验属 S7-a 编号分配器职责（批内 max+1 语义下分析卡引用既有条目，实际漏引由
    主理人审卡兜底）。禁把本门禁当「编号真实性担保」。
  · 「臆造案名」的机械判定不可行（案名空间开放），由提示词层防幻觉话术约束
    （distill-methods.md §S4-pre 话术清单）＋主理人审卡把守；P6 的 WARN 是辅助信号非判定。
"""
import glob as _glob
import json
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

KNOW_HEAD = re.compile(r"^### [FIL]-AN\d{4}-\d{2}｜")
PARA_HEAD = re.compile(r"^### W-AN\d{4}-[FILABCD]\d{2}｜")
KNOW_HEAD_SPACE = re.compile(r"^### [FIL]-AN\d{4}-\d{2} ")
PARA_HEAD_SPACE = re.compile(r"^### W-AN\d{4}-[FILABCD]\d{2} ")
KNOW_HEAD_1DIG = re.compile(r"^### [FIL]-AN\d{4}-\d(?:[^0-9]|$)")
PARA_HEAD_1DIG = re.compile(r"^### W-AN\d{4}-[FILABCD]\d(?:[^0-9]|$)")


BOLD_ENTRY = re.compile(r"^\*\*[FILW]-[A-Z]{2,3}-\d|^\*\*[FIL]-AN\d{4}-\d")
H4_ENTRY = re.compile(r"^#### ")
SEC1 = re.compile(r"^## 一、知识蒸馏（(\d+) 条）")
SEC2 = re.compile(r"^## 二、写作范式（(\d+) 条）")
SEC3 = re.compile(r"^## 三、亮点/风险提示")
HEAD1 = re.compile(r"^# .+·.+蒸馏·.+（.+）")

FAIL = []
WARN = []


# ── S4-pre 分析卡门禁（WO-34 · --stage pre）────────────────────────────────

PRE_HEAD1 = re.compile(r"^# .+·.+分析卡·.+")
PRE_SEC1 = re.compile(r"^## 一、本案要点")
PRE_SEC2 = re.compile(r"^## 二、与既有条目的关系")
PRE_SEC3 = re.compile(r"^## 三、矛盾与张力")
PRE_SEC4 = re.compile(r"^## 四、建议落族")
PRE_REL = re.compile(r"\[(强化|扩展):((?:[FLIW]L?|S|W)-[A-Z]{0,3}\d{2,6})\]|\[新增\]")
PRE_BAD_REF = re.compile(r"\[(?:强化|扩展):(?!\s*(?:[FLIW]L?|S|W)-[A-Z]{0,3}\d{2,6}\s*)\][^\s\]]?")
PRE_HEDGE = re.compile(r"据我所知|一般来说|通常认为|众所周知|不言而喻")


def check_pre_card(path):
    """分析卡格式门禁（P1-P6）。独立于蒸馏稿 C 系列校验——两种产出形态不同。"""
    global FAIL, WARN
    with open(path, encoding="utf-8") as f:
        text = f.read()
    lines = text.splitlines()
    base = path.replace("\\", "/").split("/")[-1]
    tag = f"[{base}]"

    if not lines or not PRE_HEAD1.match(lines[0].strip()):
        FAIL.append(f"{tag} P1 文件头标题不合模板（应为 `# <persona>·<维度>分析卡·<简称>`）")
    if not any("蒸馏人：" in ln for ln in lines[:30]):
        FAIL.append(f"{tag} P2 前 30 行缺「蒸馏人：…」署名行")

    has1 = has2 = has3 = has4 = False
    for ln in lines:
        if PRE_SEC1.match(ln):
            has1 = True
        elif PRE_SEC2.match(ln):
            has2 = True
        elif PRE_SEC3.match(ln):
            has3 = True
        elif PRE_SEC4.match(ln):
            has4 = True
    for flag, name in ((has1, "一、本案要点"), (has2, "二、与既有条目的关系"),
                       (has3, "三、矛盾与张力"), (has4, "四、建议落族")):
        if not flag:
            FAIL.append(f"{tag} P3 缺「## {name}」节")

    # P4：第二节内须有至少一处关系标注；非法编号引用 ⇒ FAIL
    seg2 = ""
    if has2:
        i2 = next(i for i, ln in enumerate(lines) if PRE_SEC2.match(ln))
        i3 = next((i for i, ln in enumerate(lines) if PRE_SEC3.match(ln)), len(lines))
        seg2 = "\n".join(lines[i2:i3])
    if seg2 and not PRE_REL.search(seg2):
        FAIL.append(f"{tag} P4 「二、与既有条目的关系」节内无任何 [强化:编号]/[扩展:编号]/[新增] 标注")
    if PRE_BAD_REF.search(text):
        FAIL.append(f"{tag} P6 存在非法编号引用（[强化:x]/[扩展:x] 后编号形态不合法，禁自编形态）")

    # P5：篇幅上限（半页卡）
    if len(text) > 2000:
        FAIL.append(f"{tag} P5 分析卡超长（{len(text)} > 2000 字符上限）——分析卡不是成稿，压缩到半页")

    # P6：无来源论断标记 ⇒ WARN（提示人工复核，不阻断）
    for i, ln in enumerate(lines, 1):
        if PRE_HEDGE.search(ln):
            WARN.append(f"{tag} P6 第 {i} 行含无来源论断措辞（「{PRE_HEDGE.search(ln).group(0)}」）——人工复核该句是否可溯源")


def check_file(path):
    global FAIL, WARN
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    base = path.replace("\\", "/").split("/")[-1]
    tag = f"[{base}]"

    if not lines or not HEAD1.match(lines[0].strip()):
        FAIL.append(f"{tag} C1 文件头标题不合模板（应为 `# <persona>·<维度>蒸馏·<简称>（<板块>·<阶段>·<稿本日期>）`）")
    if not any("蒸馏人：" in ln for ln in lines[:30]):
        FAIL.append(f"{tag} C2 前 30 行缺「蒸馏人：<persona>（<agent_id>，…）｜YYYY-MM-DD」署名行")

    sec1_n = sec2_n = None
    has_sec3 = False
    for i, ln in enumerate(lines, 1):
        m = SEC1.match(ln)
        if m:
            sec1_n = int(m.group(1))
            continue
        m = SEC2.match(ln)
        if m:
            sec2_n = int(m.group(1))
            continue
        if SEC3.match(ln):
            has_sec3 = True
            continue
        if ln.startswith("## 一、") or ln.startswith("## 二、") or ln.startswith("## 三、"):
            FAIL.append(f"{tag} C3 第 {i} 行节标题措辞不合规：「{ln[:40]}」（应为一、知识蒸馏（N 条）/二、写作范式（N 条）/三、亮点/风险提示）")
    if sec1_n is None:
        FAIL.append(f"{tag} C3 缺「## 一、知识蒸馏（N 条）」节")
    if sec2_n is None:
        FAIL.append(f"{tag} C3 缺「## 二、写作范式（N 条）」节")
    if not has_sec3:
        FAIL.append(f"{tag} C3 缺「## 三、亮点/风险提示」节")

    n_know = n_para = 0
    for i, ln in enumerate(lines, 1):
        if KNOW_HEAD.match(ln):
            n_know += 1
        elif PARA_HEAD.match(ln):
            n_para += 1
        else:
            if BOLD_ENTRY.match(ln):
                FAIL.append(f"{tag} C7 第 {i} 行用加粗充当条目（应改 `###` h3）：「{ln[:50]}」")
            elif KNOW_HEAD_SPACE.match(ln) or PARA_HEAD_SPACE.match(ln):
                WARN.append(f"{tag} C7 第 {i} 行编号与标题间用空格（规范应 `｜`）：「{ln[:50]}」")
            elif KNOW_HEAD_1DIG.match(ln) or PARA_HEAD_1DIG.match(ln):
                FAIL.append(f"{tag} C7 第 {i} 行序号未 2 位补零：「{ln[:50]}」")
            elif H4_ENTRY.match(ln):
                FAIL.append(f"{tag} C7 第 {i} 行出现四级标题条目（S4 产出应用 h3）：「{ln[:50]}」")

    if sec1_n is not None and n_know != sec1_n:
        FAIL.append(f"{tag} C6 一、知识蒸馏声明 {sec1_n} 条，实际 {n_know} 条标题")
    if sec2_n is not None and n_para != sec2_n:
        FAIL.append(f"{tag} C6 二、写作范式声明 {sec2_n} 条，实际 {n_para} 条标题")


import argparse


def main(argv):
    ap = argparse.ArgumentParser(description="S4 专家产出自检门禁（--stage pre 分析卡 / 默认蒸馏稿）")
    ap.add_argument("files", nargs="*", help="待检 md 文件（可多个）")
    ap.add_argument("--dir", help="案工作目录：自动扫目录下 产出_*.md")
    ap.add_argument("--stage", choices=["pre", "final"], default="final",
                    help="pre=分析卡门禁（扫 分析卡_*.md）；final=蒸馏稿门禁（默认，扫 产出_*.md）")
    ap.add_argument("--json", action="store_true", help="输出结构化 JSON（供上层消费）")
    a = ap.parse_args(argv)
    total_fail = False
    results = []
    if a.dir:
        pattern = "分析卡_*.md" if a.stage == "pre" else "*产出_*.md"
        targets = sorted(_glob.glob(a.dir.rstrip("/\\") + "/" + pattern))
    else:
        targets = [f for f in a.files if f.endswith(".md")]
    if not targets:
        print(__doc__, file=sys.stderr)
        return 2
    for p in targets:
        FAIL.clear()
        WARN.clear()
        if a.stage == "pre":
            check_pre_card(p)
        else:
            check_file(p)
        if FAIL:
            total_fail = True
        results.append((p, list(FAIL), list(WARN)))
        if not a.json:
            print(f"{'PASS' if not FAIL else 'FAIL'}  {p}")
            for w in WARN:
                print(f"   WARN  {w}")
            for e in FAIL:
                print(f"   FAIL  {e}")
    if a.json:
        print(json.dumps({
            "tool": "check_expert_output", "target": a.dir or a.files,
            "verdict": "FAIL" if total_fail else "PASS",
            "error": sum(len(f) for _, f, _ in results),
            "warn": sum(len(w) for _, _, w in results),
            "files": [{"file": p, "fail": f, "warn": w} for p, f, w in results],
        }, ensure_ascii=False))
    return 1 if total_fail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

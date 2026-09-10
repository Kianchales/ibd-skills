# -*- coding: utf-8 -*-
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
"""
import glob as _glob
import re
import sys

KNOW_HEAD = re.compile(r"^### [FIL]-AN\d{4}-\d{2}｜")
PARA_HEAD = re.compile(r"^### W-AN\d{4}-[FILABCD]\d{2}｜")
KNOW_HEAD_SPACE = re.compile(r"^### [FIL]-AN\d{4}-\d{2} ")
PARA_HEAD_SPACE = re.compile(r"^### W-AN\d{4}-[FILABCD]\d{2} ")
KNOW_HEAD_1DIG = re.compile(r"^### [FIL]-AN\d{4}-\d(?:[^0-9]|$)")
PARA_HEAD_1DIG = re.compile(r"^### W-AN\d{4}-[FILABCD]\d(?:[^0-9]|$)")
LEGACY_C2 = re.compile(r"^### [FIL]-C\d{1,2}-\d{1,2}(?:[｜ ]|$)")
LEGACY_CODE = re.compile(r"^### (?:[FIL]|W|P)-[A-Z]{2,3}-\d{2}(?:[｜ ]|$)|^### [FIL]-[A-Z]{2,3}-\d(?:[｜ ]|$)")
BOLD_ENTRY = re.compile(r"^\*\*[FILW]-[A-Z]{2,3}-\d|^\*\*[FIL]-AN\d{4}-\d")
H4_ENTRY = re.compile(r"^#### ")
SEC1 = re.compile(r"^## 一、知识蒸馏（(\d+) 条）")
SEC2 = re.compile(r"^## 二、写作范式（(\d+) 条）")
SEC3 = re.compile(r"^## 三、亮点/风险提示")
HEAD1 = re.compile(r"^# .+·.+蒸馏·.+（.+）")

FAIL = []
WARN = []


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
            elif LEGACY_C2.match(ln):
                WARN.append(f"{tag} C7 第 {i} 行案号 2 位（历史遗留形态 C01-C41，迁移至 C0001-C0041 前不回改）：「{ln[:50]}」")
            elif LEGACY_CODE.match(ln):
                WARN.append(f"{tag} C7 第 {i} 行案代号字母形态（v1 规范/历史遗留，新产出应 `C{{案号4位}}`）：「{ln[:50]}」")
            elif H4_ENTRY.match(ln):
                FAIL.append(f"{tag} C7 第 {i} 行出现四级标题条目（S4 产出应用 h3）：「{ln[:50]}」")

    if sec1_n is not None and n_know != sec1_n:
        FAIL.append(f"{tag} C6 一、知识蒸馏声明 {sec1_n} 条，实际 {n_know} 条标题")
    if sec2_n is not None and n_para != sec2_n:
        FAIL.append(f"{tag} C6 二、写作范式声明 {sec2_n} 条，实际 {n_para} 条标题")


def main(argv):
    total_fail = False
    if "--dir" in argv:
        d = argv[argv.index("--dir") + 1].rstrip("/\\")
        targets = sorted(_glob.glob(d + "/*产出_*.md"))
    else:
        targets = [a for a in argv if a.endswith(".md")]
    if not targets:
        print(__doc__)
        return 2
    for p in targets:
        FAIL.clear()
        WARN.clear()
        check_file(p)
        if FAIL:
            total_fail = True
        print(f"{'PASS' if not FAIL else 'FAIL'}  {p}")
        for w in WARN:
            print(f"   WARN  {w}")
        for e in FAIL:
            print(f"   FAIL  {e}")
    return 1 if total_fail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

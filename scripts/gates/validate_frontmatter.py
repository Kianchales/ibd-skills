#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P4 标准模板校验器（skill-publish-pipeline）

用法：
    python validate_frontmatter.py <skill-dir>

检查项（来源：skillhub-publish quality gate + skill-creator 官方校验 + 实战沉淀）：
  1. SKILL.md 存在 + frontmatter 格式（--- 开头、闭合）
  2. name = 目录名；kebab-case
  3. slug kebab-case；displayName 存在
  4. description ≥100 字符、含触发词/何时使用、无尖括号 < >
  5. version SemVer（X.Y.Z）
  6. agent_created: true
  7. body 有「何时使用（触发）/使用/示例」等价章节；<500 行
  8. references/scripts 下每个文件在 body 中被提及（防孤儿资源）
  9. LICENSE 或 LICENSE.txt 存在（缺失 = ERROR）
  10. CHANGELOG.md 存在且有当前版本记录（缺失 = ERROR，自动生成模板条目提示）
  11. Agent Skills 开放标准兼容（agentskills.io / Anthropic）：description ≤1024 字符
      （超限 WARN）；name 不含保留词 claude/anthropic（命中 WARN）

退出码：0 = 全过（WARN 不阻塞）；1 = 有 ERROR。
"""
import io
import os
import re
import sys

REQUIRED_SECTIONS = ("何时使用", "使用", "示例", "When to trigger", "Usage", "Examples")
SECTION_ANY = ("触发", "使用", "示例", "trigger", "usage", "example")


def check_frontmatter(text):
    issues = []
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return ["frontmatter 缺失或格式错误（须 --- 开头且有闭合 ---）"]
    fm = m.group(1)
    body = text[m.end():]
    # name
    nm = re.search(r"^name:\s*(.+)$", fm, re.M)
    if not nm:
        issues.append("缺 name")
    return issues, fm, body


def validate(skill_dir):
    issues = []      # ERROR
    warns = []       # WARN
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.exists(skill_md):
        return ["SKILL.md 不存在"], [], "SKILL.md 不存在"
    with io.open(skill_md, encoding="utf-8") as f:
        text = f.read()
    dir_name = os.path.basename(os.path.normpath(skill_dir))

    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return ["frontmatter 缺失或格式错误"], [], "frontmatter 错误"
    fm = m.group(1)
    body = text[m.end():]

    # 1. name = 目录名 + kebab-case
    nm = re.search(r"^name:\s*(.+)$", fm, re.M)
    if not nm:
        issues.append("缺 name")
    else:
        name = nm.group(1).strip()
        if name != dir_name:
            issues.append("name(%s) != 目录名(%s)" % (name, dir_name))
        if not re.match(r"^[a-z0-9-]+$", name):
            issues.append("name 非 kebab-case: %s" % name)

    # 2. slug
    sl = re.search(r"^slug:\s*(.+)$", fm, re.M)
    if not sl or not re.match(r"^[a-z0-9-]+$", sl.group(1).strip()):
        issues.append("slug 缺失或非 kebab-case")

    # 3. displayName
    if not re.search(r"^displayName:", fm, re.M):
        issues.append("缺 displayName")

    # 4. description：≥100 字符、含触发/何时、无尖括号（支持 description: > 折叠块多行）
    desc = ""
    desc_m = re.search(r"^description:\s*([>|]?)\s*(.*)$", fm, re.M)
    if not desc_m:
        issues.append("缺 description")
    else:
        block, first = desc_m.group(1), desc_m.group(2).strip()
        if block in (">", "|"):
            # 折叠块：取 description 行之后的缩进行直到下一个顶层字段
            lines = fm.splitlines()
            idx = next(i for i, l in enumerate(lines) if l.startswith("description:"))
            parts = [first] if first else []
            for l in lines[idx + 1:]:
                if re.match(r"^\S", l):   # 顶层字段，结束
                    break
                parts.append(l.strip())
            desc = " ".join(p for p in parts if p)
        else:
            desc = first
        if len(desc) < 100:
            warns.append("description <100 字符（%d），建议补充触发词与何时使用" % len(desc))
        if "<" in desc or ">" in desc:
            issues.append("description 含尖括号 < >（skillhub 拒绝）")

    # 5. version SemVer
    ver = re.search(r"^version:\s*([\d.]+)", fm, re.M)
    if not ver or not re.match(r"^\d+\.\d+\.\d+$", ver.group(1)):
        issues.append("version 缺失或非 SemVer")

    # 6. agent_created
    if not re.search(r"^agent_created:\s*true", fm, re.M):
        issues.append("缺 agent_created: true（否则无法被 skill_manage 修改/删除）")

    # 7. body 章节 + 行数
    body_lower = body.lower()
    if not any(s in body_lower for s in SECTION_ANY):
        issues.append("body 缺「触发/使用/示例」章节")
    line_count = len(body.splitlines())
    if line_count > 500:
        warns.append("body %d 行 > 500（callstack 实践建议拆分）" % line_count)

    # 8. resources one-level-deep（吸收 validate-skills）：每个 references/scripts/examples 文件
    #    必须从 SKILL.md 直接可达（body 被提及），禁止「只能通过另一 references 发现」的加载链
    for sub in ("references", "scripts", "examples"):
        d = os.path.join(skill_dir, sub)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if fn.startswith(".") or fn.endswith(".pyc") or fn == "__pycache__":
                continue
            fp = os.path.join(d, fn)
            if os.path.isdir(fp):
                continue  # 子目录（如 tests/）不要求被 SKILL.md 提及，只检文件
            stem = fn
            if stem not in body and os.path.splitext(fn)[0] not in body:
                issues.append("one-level-deep 违规: %s/%s 未从 SKILL.md 直接可达（须在 body 提及）" % (sub, fn))

    # 8b. 链接格式（吸收 validate-skills）：路径引用用 markdown 链接 [text](path)，非裸文件名（跳过代码块）
    #     负向断言含 /：跨包路径（如 ibd-doc-write/references/...）中间的 references/ 不算裸引用（2026-09-10 修）
    body_nocode = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
    for m in re.finditer(r"(?<![\(\]/])(references|scripts|examples)/[A-Za-z0-9_\-\.]+\.(?:md|py|json)", body_nocode):
        warns.append("裸路径引用（应改 markdown 链接 [text](path)）: %s" % m.group(0))

    # 8c. 文档骨架一致性（T1/T2 标准 · 2026-09-10 加）：README=产品文档九节 / SKILL.md=执行指令标准节
    #     README 与 SKILL.md 分工：README 给人（是什么/快速开始/场景/安装/许可），SKILL.md 给 AI（触发/流程/工具/边界）
    readme_p = os.path.join(skill_dir, "README.md")
    if os.path.exists(readme_p):
        rm = io.open(readme_p, encoding="utf-8").read()
        readme_required = ["这是什么", "快速开始", "典型场景", "分工", "安装与依赖", "目录结构", "近期更新", "许可"]
        missing_r = [k for k in readme_required if k not in rm]
        if missing_r:
            warns.append("README 骨架缺节（T2 标准）: %s" % "、".join(missing_r))
    # T1 标准 = 7 节（定位简介/协作模式等为按需扩展节，不作必需）
    skill_required = ["何时使用", "资源索引", "依赖与工具", "边界与协作", "维护"]
    missing_s = [k for k in skill_required if ("## " + k) not in body and ("## " + k + "（") not in body]
    if missing_s:
        warns.append("SKILL.md 骨架缺节（T1 标准）: %s" % "、".join(missing_s))

    # 8d. README 版本同步（2026-09-10 加 · 发布前必查）：badge 版本与「近期更新」须与 SKILL.md version 一致
    if os.path.exists(readme_p):
        _rm = io.open(readme_p, encoding="utf-8").read()
        _ver = ver.group(1) if ver else ""
        _mb = re.search(r"badge/version-([0-9.]+)", _rm)
        if _mb and _ver and _mb.group(1) != _ver:
            warns.append("README badge 版本滞后: %s（应 %s）" % (_mb.group(1), _ver))
        if _ver and _ver not in _rm:
            warns.append("README 未提及当前版本 %s（「近期更新」节应同步）" % _ver)

    # 9. LICENSE
    if not (os.path.exists(os.path.join(skill_dir, "LICENSE"))
            or os.path.exists(os.path.join(skill_dir, "LICENSE.txt"))):
        issues.append("缺 LICENSE / LICENSE.txt（skillhub-publish 要求）")

    # 10. CHANGELOG 有当前版本记录（兼容 ## vX.Y.Z / ## [X.Y.Z] / ## X.Y.Z 三种格式）
    cl = os.path.join(skill_dir, "CHANGELOG.md")
    ver_str = ver.group(1) if ver else ""
    if not os.path.exists(cl):
        issues.append("缺 CHANGELOG.md")
    elif ver_str:
        cl_text = io.open(cl, encoding="utf-8").read()
        if (("## v" + ver_str) not in cl_text and ("## [" + ver_str + "]") not in cl_text
                and ("## " + ver_str) not in cl_text):
            issues.append("CHANGELOG 缺当前版本记录 ## v%s" % ver_str)

    # 11. Agent Skills 开放标准兼容（agentskills.io / Anthropic，跨生态复用保障）
    if desc and len(desc) > 1024:
        warns.append("description %d 字符 > 1024（Agent Skills 上传校验上限，建议压缩至 1024 内）" % len(desc))
    if nm:
        n = nm.group(1).strip()
        if re.search(r"claude|anthropic", n, re.I):
            warns.append("name 含保留词 claude/anthropic（Agent Skills 标准禁止）: %s" % n)

    return issues, warns, "P4 校验完成"


def main():
    if len(sys.argv) < 2:
        print("用法: python validate_frontmatter.py <skill-dir>")
        return 2
    issues, warns, summary = validate(sys.argv[1])
    print("== P4 标准模板校验: %s" % sys.argv[1])
    for i in issues:
        print("  [ERROR] %s" % i)
    for w in warns:
        print("  [WARN]  %s" % w)
    print("--- %s；ERROR = %d，WARN = %d" % (summary, len(issues), len(warns)))
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())

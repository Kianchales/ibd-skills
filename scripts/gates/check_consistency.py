#!/usr/bin/env python3
"""check_consistency.py — ibd-skills 集合一致性门禁（CI 用）

逐包检查：
  1. SKILL.md 存在且 frontmatter 含 version
  2. CHANGELOG.md 最新**正式版本**节版本 == SKILL.md version
     （「未发布」性质的节跳过不参与版本比对；且不得置顶——置顶会被误当
      最新版本号，2026-09-18 事故：doc-review「未发布·纯文档」节置顶
      连续 5 轮 CI failure，修法 = 节下移 + 本门禁显式拦截置顶形态）
  3. README.md 在位
  4. SKILL.md/README.md 活跃文案无已下线渠道字样（渠道统一 GitHub）
  5. 集合 README 版本矩阵行 == SKILL.md version（2026-09-15 加：防矩阵笔误，
     先例 = finance-review 矩阵 0.8.4 实为 0.8.5 漏检）

任一失败 → exit 1。纯标准库，零依赖。
"""
import argparse
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKILLS = os.path.join(ROOT, 'skills')
# 布局自适应（2026-09-15）：发布仓 = <root>/skills/<pkg>/；真身仓 = <root>/<pkg>/ 平铺。
# 判据：skills/ 子目录存在且至少含一个 SKILL.md 才走集合布局，否则回退平铺。
if not (os.path.isdir(SKILLS) and any(
    os.path.exists(os.path.join(SKILLS, p, 'SKILL.md')) for p in os.listdir(SKILLS)
)):
    SKILLS = ROOT


def load_matrix_versions(readme_path):
    """从集合 README 版本矩阵提取 {skill_id: 版本}。

    匹配形如 `| [ibd-xxx](skills/ibd-xxx/README.md) | ... | 0.8.5 | ...` 的行。
    找不到矩阵（列数不足）返回空 dict —— 单仓非集合模式时静默跳过检查 5。
    """
    matrix = {}
    if not os.path.exists(readme_path):
        return matrix
    for line in open(readme_path, encoding='utf-8'):
        m = re.match(r'^\|\s*\[([a-z0-9-]+)\]\(skills/\1/README\.md\)\s*\|.*\|\s*(\d+\.\d+\.\d+)\s*\|', line)
        if m:
            matrix[m.group(1)] = m.group(2)
    return matrix


def main():
    ap = argparse.ArgumentParser(description="集合一致性门禁（版本/README 矩阵/发布渠道/变更留痕）")
    ap.add_argument("--json", action="store_true", help="输出结构化 JSON（供上层消费）")
    args = ap.parse_args()
    fails = []
    matrix = load_matrix_versions(os.path.join(ROOT, 'README.md'))
    # 治理范围过滤（2026-09-15）：平铺布局（真身仓）下根目录混有第三方/私有 skill
    # （anysearch、github、obsidian 等），不属 ibd-skills 集合治理域，不应被集合门禁扫描。
    # 治理域 = ibd-* 全系 + skill-publish-pipeline / skills-constitution（发布治理自身）。
    MANAGED = re.compile(r'^(ibd-|skill-publish-pipeline$|skills-constitution$)')
    for pkg in sorted(os.listdir(SKILLS)):
        d = os.path.join(SKILLS, pkg)
        if not os.path.isdir(d):
            continue
        if not MANAGED.match(pkg):
            continue
        skill = os.path.join(d, 'SKILL.md')
        if not os.path.exists(skill):
            fails.append(f'{pkg}: 缺 SKILL.md')
            continue
        text = open(skill, encoding='utf-8').read()
        m = re.search(r'^version:[ \t]*([^ \t\n]+)', text, re.M)
        ver = m.group(1).strip() if m else None
        if not ver:
            fails.append(f'{pkg}: SKILL.md frontmatter 无 version')
        cl = os.path.join(d, 'CHANGELOG.md')
        if os.path.exists(cl):
            head = open(cl, encoding='utf-8').read()
            # 「未发布」性质的节（如 `## [未发布 · 纯文档]`）不携带版本号，
            # 跳过版本比对；首个正式版本节才算「最新正式版本」。
            is_unreleased = re.compile(r'^## \[[^\]]*未发布[^\]]*\]', re.M)
            hm = None
            unreleased_top = False
            for m in re.finditer(r'^## \[([^\]]+)\]', head, re.M):
                if is_unreleased.match(m.group(0)):
                    if hm is None:
                        unreleased_top = True  # 在任何正式版本节之前出现 = 置顶
                    continue
                if hm is None:
                    hm = m
            if hm and ver and hm.group(1).strip() != ver:
                fails.append(f'{pkg}: SKILL version {ver} != CHANGELOG 最新正式版本节 {hm.group(1)}')
            if unreleased_top:
                fails.append(f'{pkg}: CHANGELOG「未发布」节置顶——须移至最新正式版本节之后（会破坏版本比对，2026-09-18 事故先例）')
        else:
            fails.append(f'{pkg}: 缺 CHANGELOG.md')
        if not os.path.exists(os.path.join(d, 'README.md')):
            fails.append(f'{pkg}: 缺 README.md')
        for f in ('SKILL.md', 'README.md'):
            fp = os.path.join(d, f)
            if os.path.exists(fp) and 'skillhub' in open(fp, encoding='utf-8').read():
                fails.append(f'{pkg}/{f}: 残留 skillhub 字样（渠道已统一 GitHub）')
        # 5. 集合 README 矩阵版本 == SKILL.md version
        if ver and matrix and pkg in matrix and matrix[pkg] != ver:
            fails.append(f'{pkg}: SKILL version {ver} != 集合 README 矩阵 {matrix[pkg]}')
        # 6. 资源文件变更留痕：SKILL.md 引用的 references/scripts 文件必须在 CHANGELOG 出现过
        #    （ADR-0002：变更时刻拦截；先例 = interface.md 裸奔进包无 CHANGELOG 条目）
        if os.path.exists(cl):
            cl_text = open(cl, encoding='utf-8').read()
            # 分代归档的 CHANGELOG（references/changelog-archive*.md）同样算留痕
            for archive_fn in os.listdir(os.path.join(d, 'references')) if os.path.isdir(os.path.join(d, 'references')) else []:
                if archive_fn.startswith('changelog-archive'):
                    cl_text += open(os.path.join(d, 'references', archive_fn), encoding='utf-8').read()
            sk_text = text
            for sub in ('references', 'scripts'):
                sd = os.path.join(d, sub)
                if not os.path.isdir(sd):
                    continue
                for fn in sorted(os.listdir(sd)):
                    if fn.startswith('.') or fn.endswith('.pyc') or fn == '__pycache__' or os.path.isdir(os.path.join(sd, fn)):
                        continue
                    stem = os.path.splitext(fn)[0]
                    if (fn in sk_text or stem in sk_text) and (fn not in cl_text and stem not in cl_text):
                        fails.append(f'{pkg}: {sub}/{fn} 被 SKILL.md 引用但 CHANGELOG 无任何记录（变更留痕缺失）')
    n_pkgs = len([x for x in os.listdir(SKILLS) if os.path.isdir(os.path.join(SKILLS, x))])
    if args.json:
        print(json.dumps({
            "tool": "check_consistency", "target": SKILLS,
            "verdict": "FAIL" if fails else "PASS",
            "error": len(fails), "warn": 0, "scanned": n_pkgs,
            "issues": [{"level": "ERROR", "msg": m} for m in fails],
        }, ensure_ascii=False))
    if fails:
        if not args.json:
            print('FAIL:')
            for f in fails:
                print(' -', f)
        sys.exit(1)
    if not args.json:
        print(f'OK: {n_pkgs} 包版本/README/渠道一致')


if __name__ == '__main__':
    main()

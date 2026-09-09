# -*- coding: utf-8 -*-
"""check_consistency.py — ibd-skills 集合一致性门禁（CI 用）

逐包检查：
  1. SKILL.md 存在且 frontmatter 含 version
  2. CHANGELOG.md 最新节版本 == SKILL.md version
  3. README.md 在位
  4. SKILL.md/README.md 活跃文案无已下线渠道字样（渠道统一 GitHub）

任一失败 → exit 1。纯标准库，零依赖。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKILLS = os.path.join(ROOT, 'skills')


def main():
    fails = []
    for pkg in sorted(os.listdir(SKILLS)):
        d = os.path.join(SKILLS, pkg)
        if not os.path.isdir(d):
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
            hm = re.search(r'^## \[([^\]]+)\]', head, re.M)
            if hm and ver and hm.group(1).strip() != ver:
                fails.append(f'{pkg}: SKILL version {ver} != CHANGELOG 最新节 {hm.group(1)}')
        else:
            fails.append(f'{pkg}: 缺 CHANGELOG.md')
        if not os.path.exists(os.path.join(d, 'README.md')):
            fails.append(f'{pkg}: 缺 README.md')
        for f in ('SKILL.md', 'README.md'):
            fp = os.path.join(d, f)
            if os.path.exists(fp) and 'skillhub' in open(fp, encoding='utf-8').read():
                fails.append(f'{pkg}/{f}: 残留 skillhub 字样（渠道已统一 GitHub）')
    if fails:
        print('FAIL:')
        for f in fails:
            print(' -', f)
        sys.exit(1)
    print(f'OK: {len([x for x in os.listdir(SKILLS) if os.path.isdir(os.path.join(SKILLS, x))])} 包版本/README/渠道一致')


if __name__ == '__main__':
    main()

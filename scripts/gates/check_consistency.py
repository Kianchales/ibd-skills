#!/usr/bin/env python3
"""check_consistency.py — ibd-skills 集合一致性门禁（CI 用）

逐包检查：
  1. SKILL.md 存在且 frontmatter 含 version
  2. CHANGELOG.md 最新**正式版本**节版本 == SKILL.md version
     （「未发布」性质的节跳过不参与版本比对；且不得置顶——置顶会被误当
      最新版本号，2026-09-18 事故：doc-review「未发布·纯文档」节置顶
      连续 5 轮 CI failure，修法 = 节下移 + 本门禁显式拦截置顶形态）
     · **读取宽松**：`## [x.y.z]` / `## vX.Y.Z` 等形态均能读出（RE_VER_ENTRY）；
       一个版本节都读不到 ⇒ **报错**，不按放行处理（判不出≠放行，§4.10 簇三第 12 条）
     · **格式单列**：A14 判首条是否 `## [x.y.z] - YYYY-MM-DD`——**WARN 不阻断**
       （`bump_version`／`check_version_coverage` 的读法均已宽松，无消费方依赖严格形态
       ⇒ 格式属可读性，不属正确性；两条判据互不替代，禁把格式塞进读取里）
  3. README.md 在位
  4. SKILL.md/README.md 活跃文案无已下线渠道字样（渠道统一 GitHub）
  5. 集合 README 版本矩阵行 == SKILL.md version（2026-09-15 加：防矩阵笔误，
     先例 = finance-review 矩阵 0.8.4 实为 0.8.5 漏检）
  6. 资源文件变更留痕：SKILL.md 引用的 references/scripts 文件须在 CHANGELOG 出现过
     （2026-10-18 加通配识别：CHANGELOG 写「两个 `*-requirements.txt`」这种**通配概括**
      是合规记法，此前只认字面全名 ⇒ 误报「留痕缺失」）

**覆盖面口径（2026-10-18 修 · 承普查 ⑦-1）**：
  报出的 `scanned` ＝ **实际受检的治理域包数**，不再用「根目录下的目录数」——
  旧实现把 42 个目录（含 `docs`／`.scratch`／`.workbuddy` 等非包目录）当分母、
  而实际只检了 12 个包，输出仍写「OK: 44 包一致」⇒ **分母虚报**，正是「漏检 13 包」
  长期没被发现的原因（同族 I-0170「声明的覆盖面 ≠ 实现的覆盖面」）。
  治理域判定改由 `check_conformance.tier_of()` **派生**（不再维护第二份包名清单），
  并把「按外部跳过的包」**逐个列出**（含自建特征提示）——让排除面可见，不靠再立一条严重度。

任一失败 → exit 1。纯标准库，零依赖。
"""
import argparse
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SELF_DIR = os.path.dirname(os.path.abspath(__file__))
if SELF_DIR not in sys.path:
    sys.path.insert(0, SELF_DIR)
try:
    # 治理域与可见性分级的**单一事实源**（不复制一份包名清单）
    from check_conformance import tier_of as _tier_of
except Exception:                                   # 构建器缺失 ⇒ 降级为「只认 ibd-* 前缀」
    _tier_of = None

# ── 版本节的两条独立判据（2026-10-18 · T3；单一事实源 → 本处）─────────────────
#   **读取用宽松口径**：判据要回答的是「最新版本号是多少」，**不该由格式决定能不能读**。
#   与 `check_version_coverage.RE_ENTRY` 同构（方括号与 v 前缀皆可省）。
#   **格式合规用严格口径（A14）**：首条正式版本节须形如 `## [x.y.z] - YYYY-MM-DD`。
#   两者**必须分离**——把格式检查塞进读取里，格式一破就从「报错」退化成「静默放行」。
#   实证（2026-10-18 四情形对照）：旧实现只认 `^## \[…\]`，于是
#     ① 全非标格式 ⇒ hm=None ⇒ 比对整句短路 ⇒ 版本写 9.9.9 对 1.0.0 也报 OK（失败开放）；
#     ② 非标新条＋标准旧条 ⇒ 抓到**旧条目**比对 ⇒ 报出错误数值的假警报。
#   判据 → docs/ENGINEERING.md §4.10 簇三 第 12 条（判不出不得落进放行侧）。
RE_VER_ENTRY = re.compile(r'^##\s*\[?v?(\d+\.\d+\.\d+)\]?')
RE_STRICT_ENTRY = re.compile(r'^## \[(\d+\.\d+\.\d+)\] - \d{4}-\d{2}-\d{2}$')

def resolve_layout(root):
    """按 `<root>` 判定布局，返回 `(技能根, 是否单包仓)`。

    · 集合布局 = `<root>/skills/<pkg>/`（发布仓）
    · 平铺布局 = `<root>/<pkg>/`（真身仓）
    · 单包仓   = `<root>/` 本身即包（仓根即包，无 `skills/` 子层）
    判据：`skills/` 子目录存在且至少含一个 `SKILL.md` ⇒ 集合；否则回退 `<root>`；
          回退后 `<root>/SKILL.md` 存在 ⇒ 单包仓。
    """
    skills = os.path.join(root, 'skills')
    if os.path.isdir(skills) and any(
            os.path.exists(os.path.join(skills, p, 'SKILL.md')) for p in os.listdir(skills)):
        return skills, False
    return root, os.path.isfile(os.path.join(root, 'SKILL.md'))


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKILLS, SINGLE = resolve_layout(ROOT)


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


def load_compat_matrix(readme_path):
    """从集合 README **依赖版本兼容矩阵**提取 [(依赖方, 依赖包, 当前集合版本)]。

    2026-10-02 新增（检查 7 的输入）。表头判据 ＝ 含「当前集合版本」的表格行。
    跳过规则：② 列剥括注后**非包名**（如「平台 docx 工具」）⇒ 跳过；
              ④ 列**非 `X.Y.Z`**（如 `—`）⇒ 跳过。
    """
    rows = []
    if not os.path.exists(readme_path):
        return rows
    in_tbl = False
    for line in open(readme_path, encoding='utf-8'):
        if not in_tbl:
            if line.lstrip().startswith('|') and '当前集合版本' in line:
                in_tbl = True
            continue
        if not line.lstrip().startswith('|'):
            break                      # 表格结束
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) < 4 or set(cells[0]) <= set('-: '):
            continue                   # 分隔行 / 列数不足
        dep = re.sub(r'[（(].*?[)）]', '', cells[1])       # 剥「（可选）」「（汇总口）」
        dep = re.sub(r'[〔\[].*', '', dep).strip(' *`')
        if not re.match(r'^[a-z0-9-]+$', dep):
            continue                   # 非包名 ⇒ 无版本可比
        if not re.match(r'^\d+\.\d+\.\d+$', cells[3]):
            continue                   # `—` 等
        rows.append((cells[0], dep, cells[3]))
    return rows


def main():
    ap = argparse.ArgumentParser(description="集合一致性门禁（版本/README 矩阵/发布渠道/变更留痕）")
    ap.add_argument("--json", action="store_true", help="输出结构化 JSON（供上层消费）")
    ap.add_argument("--root", default="", help="技能根目录（默认＝按脚本位置推断；单包仓可直指仓根）")
    args = ap.parse_args()
    global ROOT, SKILLS, SINGLE
    if args.root:
        ROOT = os.path.abspath(args.root)
        SKILLS, SINGLE = resolve_layout(ROOT)
    fails = []
    warns = []          # A14 等「风格类」提示：照报不阻断（2026-10-18 · T3）
    pkg_ver = {}
    matrix = load_matrix_versions(os.path.join(ROOT, 'README.md'))
    compat = load_compat_matrix(os.path.join(ROOT, 'README.md'))
    # 治理范围过滤：平铺布局（真身仓）下根目录混有第三方/私有 skill
    # （anysearch、github、obsidian 等），不属 ibd-skills 集合治理域，不应被集合门禁扫描。
    #
    # 2026-10-18 改（承普查 ⑦-1）：**不再维护第二份包名清单**。旧实现用正则
    #   `^(ibd-|skill-publish-pipeline$|skills-constitution$)` 判治理域 ⇒ 只覆盖 12/25
    #   个自建包，`skilldev-*` 9 包与 rule-capture／life-manager／obsidian／pdf-ocr-toolkit／
    #   hjyweb-accounting-fetch／win-crash-forensics 全部**静默不检**，而输出照样报
    #   「OK: 44 包一致」（分母是目录数）。现改为从 `check_conformance.tier_of()` 派生：
    #   `tier != external` 即治理域。非包目录（docs／.scratch／.workbuddy／trigger-eval）
    #   实测一律判 external，故**自动排除**、不再报「缺 SKILL.md」。
    #   ⚠ 依赖：tier_of 读 `BUILTIN`／`PUBLIC_PKGS` 硬编码清单 ⇒ 新包未登记会被判 external。
    #   该风险由 `check_conformance.reconcile_whitelist()` 的 W1 对账覆盖（同一事实、同一
    #   严重度 WARN）；本处**不重复判**（两器对同一事实给两档严重度＝体系明令禁止的形态），
    #   只做「把跳过面列出来」——见下方 skipped_ext 的 `⚠ 自建特征` 提示。
    RX_SELFBUILT = re.compile(r'^(?:agent_created:[ \t]*true|private:[ \t]*true)\s*$', re.M)

    def is_managed(name):
        return (_tier_of(name) != 'external') if _tier_of else bool(re.match(r'^ibd-', name))

    if SINGLE:
        _pkg_list = [os.path.basename(ROOT.rstrip('/\\'))]
    else:
        # 只枚举**含 SKILL.md 的目录**——非包目录本就不该进集合门禁
        _pkg_list = sorted(n for n in os.listdir(SKILLS)
                           if os.path.exists(os.path.join(SKILLS, n, 'SKILL.md')))
    skipped_ext = []        # [(pkg, 是否带自建特征)]——用于把排除面列出来
    for pkg in _pkg_list:
        d = ROOT if SINGLE else os.path.join(SKILLS, pkg)
        if not SINGLE and not os.path.isdir(d):
            continue
        if not SINGLE and not is_managed(pkg):
            _sb = False
            if not os.path.exists(os.path.join(d, '_skillhub_meta.json')):
                try:
                    _head = open(os.path.join(d, 'SKILL.md'), encoding='utf-8',
                                 errors='replace').read(4000)
                    _sb = bool(RX_SELFBUILT.search(_head))
                except OSError:
                    pass
            skipped_ext.append((pkg, _sb))
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
        else:
            pkg_ver[pkg] = ver
        cl = os.path.join(d, 'CHANGELOG.md')
        if os.path.exists(cl):
            head = open(cl, encoding='utf-8').read()
            # 「未发布」性质的节（如 `## [未发布 · 纯文档]`）不携带版本号，
            # 跳过版本比对；首个正式版本节才算「最新正式版本」。
            is_unreleased = re.compile(r'^## \[[^\]]*未发布[^\]]*\]', re.M)
            hm = None
            hm_line = None
            unreleased_top = False
            for line in head.splitlines():
                if not line.startswith('## '):
                    continue
                if is_unreleased.match(line):
                    if hm is None:
                        unreleased_top = True  # 在任何正式版本节之前出现 = 置顶
                    continue
                m = RE_VER_ENTRY.match(line)
                if m and hm is None:
                    hm, hm_line = m, line
            if hm is None:
                # 判不出 ≠ 放行（§4.10 簇三 第 12 条）：旧实现对 None 整句短路 ⇒ 静默 OK
                fails.append(f'{pkg}: CHANGELOG 找不到任何版本节——判不出，不按放行处理'
                             f'（`## [x.y.z]` 与 `## vX.Y.Z` 两种形态均可识别；本册两种都没有）')
            else:
                if ver and hm.group(1).strip() != ver:
                    fails.append(f'{pkg}: SKILL version {ver} != CHANGELOG 最新正式版本节 {hm.group(1)}')
                # A14：首条版本节格式**风格**检查（WARN，不阻断）——与上面的读取口径互不替代。
                # 为何只 WARN：`bump_version` 的 RX_CL 与 check_version_coverage 的 RE_ENTRY
                # **均已宽松**（`## vX.Y.Z` 可读），全库无任何消费方依赖严格形态
                # ⇒ 格式统一属可读性/卫生，不属正确性，不构成阻断理由（P9：别把风格指标变目标）。
                if not RE_STRICT_ENTRY.match(hm_line):
                    warns.append(f'{pkg}: CHANGELOG 首条版本节形态不统一（A14）——'
                                 f'全库通行形态为 `## [x.y.z] - YYYY-MM-DD`，本册为 `{hm_line.strip()[:60]}`'
                                 f'（仅风格提示，不影响判读）')
            if unreleased_top and hm is not None:
                fails.append(f'{pkg}: CHANGELOG「未发布」节置顶——须移至最新正式版本节之后（会破坏版本比对，2026-09-18 事故先例）')
        else:
            fails.append(f'{pkg}: 缺 CHANGELOG.md')
        if not os.path.exists(os.path.join(d, 'README.md')):
            fails.append(f'{pkg}: 缺 README.md')
        for f in ('SKILL.md', 'README.md'):
            fp = os.path.join(d, f)
            if not os.path.exists(fp):
                continue
            # 2026-10-18 收窄（承普查 ⑦-1）：原为裸子串 `'skillhub' in text`，无上下文。
            #   全库唯一命中是 `_skillhub_meta.json`——**上游市场包的元数据文件名**，不是
            #   「本包发布渠道」。而 `check_conformance.reconcile_whitelist()` 的 W1 恰恰
            #   **把这个文件名当「市场安装包」的判据** ⇒ 两个器对同一串的语义相反。
            #   故先剔除该文件名形态，再匹配残留字样（真正的渠道指称仍照拦）。
            _t = open(fp, encoding='utf-8').read().replace('_skillhub_meta.json', '')
            if 'skillhub' in _t:
                fails.append(f'{pkg}/{f}: 残留 skillhub 字样（渠道已统一 GitHub）')
        # 5. 集合 README 矩阵版本 == SKILL.md version
        if ver and matrix and pkg in matrix and matrix[pkg] != ver:
            fails.append(f'{pkg}: SKILL version {ver} != 集合 README 矩阵 {matrix[pkg]}')
        # 6. 资源文件变更留痕：SKILL.md 引用的 references/scripts 文件必须在 CHANGELOG 出现过
        #    （变更时刻拦截；先例 = interface.md 裸奔进包无 CHANGELOG 条目）
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
                    if not (fn in sk_text or stem in sk_text):
                        continue
                    if fn in cl_text or stem in cl_text:
                        continue
                    # 2026-10-18 加**通配识别**（承普查 ⑦-1）：CHANGELOG 里「两个
                    #   `*-requirements.txt`」这类**通配概括**是合规记法（作者已记过账、
                    #   只是没写全名）。旧实现只认字面 ⇒ 把记过账的件误报为「留痕缺失」。
                    #   判据：把文件名按 `-` 切分后，`*-<后缀>` 出现在 CHANGELOG 即算留痕；
                    #   无连字符的文件名则认 `*.<扩展名>`。只认这两种，不放宽到任意子串。
                    _tail = fn.split('-', 1)[-1] if '-' in fn else fn
                    _pat = r'\*-\s*' + re.escape(_tail) if '-' in fn else r'\*' + re.escape(
                        os.path.splitext(fn)[1] or fn)
                    if re.search(_pat, cl_text):
                        continue
                    fails.append(f'{pkg}: {sub}/{fn} 被 SKILL.md 引用但 CHANGELOG 无任何记录（变更留痕缺失）')
    # 7. 依赖版本兼容矩阵「当前集合版本」列 == 被依赖包 SKILL.md version（2026-10-02 新增）
    #    为什么要加：检查 5 的正则**只认带包链接的「包清单表」**，而依赖兼容矩阵的行无链接
    #    ⇒ 该矩阵的版本列**长期无人校验**。先例 = 本次发布 methods-ops 1.35.8 上提后矩阵仍记
    #    1.35.0，是靠 P0.8 详规的**人工提醒**才发现（详规另载有一次「~24 次 CI 连红」的
    #    同型事故：包清单表停在旧值而无人发现）。
    for who, dep, cur in compat:
        if dep in pkg_ver and pkg_ver[dep] != cur:
            fails.append(f'依赖兼容矩阵（{who} → {dep}）记 {cur} != 该包实际 version {pkg_ver[dep]}')
        elif dep not in pkg_ver:
            fails.append(f'依赖兼容矩阵（{who} → {dep}）所指包**不在集合内**（矩阵引用了不存在的包名）')
    # 分母 = **实际受检的治理域包数**（不是目录数；见文件头「覆盖面口径」）
    n_pkgs = 1 if SINGLE else (len(_pkg_list) - len(skipped_ext))
    _target = ROOT if SINGLE else SKILLS
    _ext_names = [p for p, _sb in skipped_ext]
    _sb_names = [p for p, sb in skipped_ext if sb]
    if args.json:
        print(json.dumps({
            "tool": "check_consistency", "target": _target,
            "verdict": "FAIL" if fails else "PASS",
            "error": len(fails), "warn": len(warns), "scanned": n_pkgs,
            "scanned_note": "实际受检的治理域包数（分母）；旧实现误用根目录下的目录数",
            "skipped_external": _ext_names,
            "skipped_external_selfbuilt_hint": _sb_names,
            "issues": ([{"level": "ERROR", "msg": m} for m in fails] +
                       [{"level": "WARN", "msg": m} for m in warns]),
        }, ensure_ascii=False))
    if fails:
        if not args.json:
            print('FAIL:')
            for f in fails:
                print(' -', f)
            for w in warns:
                print(' [WARN]', w)
            _print_scope(n_pkgs, skipped_ext)
        sys.exit(1)
    if not args.json:
        for w in warns:
            print(' [WARN]', w)
        print(f'OK: {n_pkgs} 包版本/README/渠道一致' + (f'（另有 {len(warns)} 条风格提示）' if warns else ''))
        _print_scope(n_pkgs, skipped_ext)


def _print_scope(n_pkgs, skipped_ext):
    """把「检了什么、跳过什么」打成一行——让排除面可见（不靠再立一条严重度）。

    为什么不用「跳过 N 个」草草了事：那正是旧实现 `scanned` 虚报的同型问题——
    只给数不给名，读者无法判断「跳过的是外部包，还是我自己刚建的包漏登记了」。
    """
    if n_pkgs <= 1 and not skipped_ext:
        return
    print(f'  覆盖面：治理域 {n_pkgs} 包受检'
          + (f' ／ 按外部跳过 {len(skipped_ext)} 个：%s' % '、'.join(
              (p + '⚠' if sb else p) for p, sb in skipped_ext) if skipped_ext else ''))
    _sb = [p for p, sb in skipped_ext if sb]
    if _sb:
        print(f'  ⚠ 上列带 ⚠ 者含自建包特征（agent_created/private）却不在治理域清单'
              f'——若确为自建包，须同步 check_conformance.BUILTIN（{len(_sb)} 个：%s）'
              % '、'.join(_sb))


if __name__ == '__main__':
    main()

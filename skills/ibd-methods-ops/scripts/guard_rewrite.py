#!/usr/bin/env python3
"""回写闸门：一句多投 / 主题匹配校验（I-0235 代码级落地）

**为什么需要本闸门**：`check_entry_contract.py` 只校**形态**（A3 标签／A4 案名白名单／
引注契约／裸页码），`check_methods_health.py` 亦无内容语义项 ⇒ **形态全合规、语义全错
也能全绿**。2026-11-12 回写清账实测：两道门禁 ERROR 0 / PASS，仍写出 27 组「一句灌多
条目」＋ 19 行张冠李戴（「股价稳定预案」进对赌清理条、「3D 外包格局」进智能装备条）。

**三条判据**：

- **A 一句多投（硬拦）**：同一 `(案名, 新案条目编号, 实证句)` 投向 ≥2 个目标编号
  ⇒ **整组拒绝**（不做「留一个」——无依据判断该留哪个，属多解越权）。
  唯一放行口：映射表该行「说明」列显式含 `双投` / `两处均贴` / `双条目` / `准许多投`
  / `准双投`，或计划行带 `allow_multi: true`。**这是书面声明，不是默认值。**
- **B 主题覆盖度（只排序、只告警，不拦）**：句子 vs 目标条目**现有**正文的 2-gram 覆盖率。
  为什么不拦：实测「<0.15 即删」的 18 条中至少 5 条为真相关（未回函替代程序、知识产权
  资产体系、改性塑料路线之争等）⇒ **阈值删除＝误杀**。覆盖率只能把可疑项排到前面给人看。
  另注：**写入后**再算「句子 vs 所在条目全文」覆盖率恒为 1.00（句子已在里面），判据失效；
  本闸门只在**写入前**算，故有效。
- **C 库内同句计数（`--verify`）**：句子在目标条目块内出现次数 > 计划处数 ⇒ 报重复投放。

**⚠ 适用范围边界（2026-11-12 实测教训，勿越界）**：以上判据的**设计对象是「回写计划」**
——每行一句完整句子、且已指定目标编号。**不得拿本闸门扫存量库并据此定论**：

- 判据 D 只看单行 ⇒ 撞上「两行式」（`- **原文实证**：` 换行接 `  - 招 P 10：「…」`）
  必然误报。库内 4,449 条「标签冒号后为空」中 **4,448 条是两行式**，内容在下一行。
- 判据 C 按「最近 `###` 标题」归组 ⇒ 撞上「章内混排」（WL 卷按案罗列、不挂编号）
  与「悬空扩展行」必然误报。实测 120 条报警中 117 条为假。
- 案级素材卷（`cases_md/`、`40_单案/*范式_<案名>.md`）的「实证＝页码定位」是**体例**，
  不是空句；删了条目就失去素材出处。

存量若要用，只能作为**排序线索**，结论必须落回人工判「体例 vs 缺陷」。

**用法**：

    # ① 计划 JSON 模式（自定义/临时回写脚本必须先导出计划再跑本闸门）
    python guard_rewrite.py --plan state/rewrite_plan.json --json state/guard_report.json
    #    计划格式：[{"case":"精创电气","new":"F-AN0023-05","target":"F-060004",
    #               "emp":"<本案实证首句>","grade":"高","note":"…","allow_multi":false}, …]

    # ② 映射表模式（直接扫 cases/*/共通点映射_*.md，等价 apply_rewrite 的入参口径）
    python guard_rewrite.py --methods-root <工作区根>

    # ③ 写后自检
    python guard_rewrite.py --methods-root <工作区根> --verify

**纪律**：本脚本**只判不写**。返回码 0＝全通过、1＝有硬拦项（供 shell 短路：
`guard && apply_rewrite --apply`）。
"""
import argparse
import collections
import glob
import io
import json
import os
import re
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# 双投放的书面声明词（映射表「说明」列）
ALLOW_RE = re.compile(r'双投|两处均贴|双条目|准许多投|准双投')
# 覆盖率告警阈值（**只告警不拦**，见模块注释 B）
WARN_COV = 0.15
# 2-gram 归一：去标点与空白
_PUNC = re.compile(r'[\s，。；：、（）()「」『』“”"\'—\-／/·．,.;:%？！《》｜|]')

# 「实质内容」判据（判据 D，2026-11-12 实测补）：剥掉引注与页码后剩余的汉字/数字/字母数。
#   为什么要剥：`招 P 87-P 88。`／`问2 P 211-P 212。`／`招 P 30／招 P 153——……` 这类
#   **纯页码行**在映射表里占少量比例（实测 1521 条中约 20 条），写进库等于垃圾实证；
#   而 `综合毛利率 63.20%…（招 P 283）。` 汉字虽少但含实质数据，**不能按汉字数误杀**。
_CITE_PAREN = re.compile(r'（([^（）]*)）')
_CITE_RAW = re.compile(r'(?:PAGE|招|问\s*[12])\s*P?\s*\d+(?:\s*[-—－~～＋+–]\s*P?\s*\d+)?')
MIN_SUBST = 8


def _paren_is_pure_cite(inner):
    """括号内是否「纯引注」—— 剥掉来源词/页码后几乎不剩字。

    为什么要判而非直接剥：`依据（问1 出口退税表：境外销售收入 A、净额法调整收入 B…）` 这种
    长括号里是**实质内容**，一律剥会把好句判成空句（实测 298 条误报中大部分属此类）。
    只有 `（招 P 283）`／`（问2 P 219-221）` 这类「来源＋页码」才算纯引注。
    """
    rest = _CITE_RAW.sub('', inner)
    return len(re.sub(r'[^\u4e00-\u9fa5A-Za-z0-9]', '', rest)) < 4


def substantive(s):
    """剥**纯引注**括号与裸页码后，「汉字＋数字＋字母」字符数 —— 判句子有无实质内容。"""
    t = _CITE_PAREN.sub(lambda m: '' if _paren_is_pure_cite(m.group(1)) else m.group(0), s or '')
    t = _CITE_RAW.sub('', t)
    return len(re.sub(r'[^\u4e00-\u9fa5A-Za-z0-9]', '', t))


def read_text(p):
    return io.open(p, encoding='utf-8', newline='').read()


def grams(s, n=2):
    s = _PUNC.sub('', s or '')
    return set(s[i:i + n] for i in range(max(0, len(s) - n + 1)))


def coverage(sent, body):
    """句子被目标条目正文覆盖的比例。空句＝0.0。"""
    g = grams(sent)
    if not g:
        return 0.0
    return len(g & grams(body)) / len(g)


def load_plan(path):
    """读计划 JSON；兼容 `{"rows": [...]}` 与裸 list 两种外壳。"""
    d = json.load(io.open(path, encoding='utf-8'))
    if isinstance(d, dict):
        d = d.get('rows') or d.get('plan') or []
    out = []
    for i, r in enumerate(d):
        if not isinstance(r, dict):
            continue
        if not r.get('target') or not r.get('emp'):
            raise ValueError('计划第 %d 行缺 target/emp：%r' % (i + 1, r))
        r.setdefault('case', '')
        r.setdefault('new', '')
        r.setdefault('grade', '高')
        r.setdefault('note', '')
        out.append(r)
    return out


def _entry_bodies(root):
    """target 编号 → 条目块正文（标题行到下一个 `#` 开头之前）。多处命中取全部。"""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from apply_rewrite import build_index, target_files
    except Exception as e:                                    # pragma: no cover
        raise RuntimeError('无法载入 apply_rewrite（--methods-root 模式需要同目录脚本）：%s' % e)
    files = target_files(root)
    idx = build_index(files)
    out = {}
    cache = {}
    for code, hits in idx.items():
        blocks = []
        for p, i in hits:
            if p not in cache:
                cache[p] = read_text(p).split('\n')
            lines = cache[p]
            j = i + 1
            while j < len(lines) and not lines[j].startswith('#'):
                j += 1
            blocks.append('\n'.join(lines[i:j]))
        out[code] = '\n'.join(blocks)
    return out, idx


def check(rows, body_of=None):
    """核心判定。返回 `(ok, rejected, warns)`。

    - `rows`：含 `case`／`new`／`target`／`emp` 的字典列表（`note`／`allow_multi` 可选）
    - `body_of(target) -> str`：目标条目现有正文；缺省不做覆盖率（不告警）
    """
    groups = collections.OrderedDict()
    ok, rejected, warns = [], [], []

    # 判据 D 先行：空句（剥引注后无实质内容）逐行拦，先于分组 —— 否则空句带 allow_multi
    #   声明时会混进放行组。实测 `招 P 87-P 88。` 这类行正是「三门禁全绿的垃圾实证」来源。
    alive = []
    for r in rows:
        n = substantive(r.get('emp'))
        if n < MIN_SUBST:
            rejected.append({
                'case': r.get('case', ''), 'new': r.get('new', ''), 'targets': [r.get('target')],
                'reason': 'empty_sentence',
                'detail': '剥引注/页码后仅剩 %d 字符（< %d）⇒ 无实质内容的页码行，禁写' % (n, MIN_SUBST),
                'cov': {}, 'emp': (r.get('emp') or '')[:90],
            })
            continue
        alive.append(r)

    for r in alive:
        groups.setdefault((r.get('case', ''), r.get('new', ''), r.get('emp', '')), []).append(r)

    for (case, new, emp), grp in groups.items():
        targets = list(dict.fromkeys(g['target'] for g in grp))
        allowed = any(g.get('allow_multi') or ALLOW_RE.search(g.get('note') or '') for g in grp)

        covs = {}
        # 短句（实质字符 <12）不算覆盖率：2-gram 太少，极易满覆盖（实测 `PAGE 62（招股书）`
        #   类短句对多个条目都算出 1.000），会给出假的安全感。
        if body_of and substantive(emp) >= 12:
            for t in targets:
                covs[t] = round(coverage(emp, body_of(t) or ''), 3)

        if len(targets) > 1 and not allowed:
            rejected.append({
                'case': case, 'new': new, 'targets': targets,
                'reason': 'multi_target_same_sentence',
                'detail': '同一句投向 %d 个目标；无「双投/两处均贴/双条目/准许多投」声明'
                          '⇒ 整组拒绝，须逐个目标分别取句或书面声明双投' % len(targets),
                'cov': covs, 'emp': emp[:90],
            })
            continue

        for g in grp:
            g = dict(g)
            g['cov'] = covs.get(g['target'])
            g['guard'] = 'allow_multi' if len(targets) > 1 else 'ok'
            ok.append(g)
            if g['cov'] is not None and g['cov'] < WARN_COV:
                warns.append({'case': case, 'new': new, 'target': g['target'],
                              'cov': g['cov'],
                              'reason': 'low_topic_coverage（只告警：阈值删除会误杀，须人工判）',
                              'emp': emp[:90]})
    return ok, rejected, warns


def guard_rows(rows, root):
    """apply_rewrite 的调用入口：带库正文的完整判定。"""
    bodies, _idx = _entry_bodies(root)
    return check(rows, body_of=lambda t: bodies.get(t, ''))


def occurrence(rows, root):
    """`{(case, emp): (命中块数, 全文出现总次数)}` —— 判据 C 的度量基础。

    两个口径都要：**块数**看「同一句散落在几个条目」（跨条目重复投放），
    **总次数**看「同一块内是否插了多次」（同块重复）。只算块数会漏同块重复。
    """
    bodies, _idx = _entry_bodies(root)
    out = {}
    for r in rows:
        emp = r.get('emp', '')
        # 空句/占位符不进判据 C：它们由判据 D 管。否则 `"……` 这类占位符会以
        #   「58 块 / 65 次」冲上重复榜首（实测），把真重复淹没。
        if not emp or substantive(emp) < MIN_SUBST:
            continue
        k = (r.get('case', ''), emp)
        if k in out:
            continue
        blocks = sum(1 for b in bodies.values() if emp in b)
        total = sum(b.count(emp) for b in bodies.values())
        out[k] = (blocks, total)
    return out


def verify_rows(rows, root, baseline=None):
    """写后自检（判据 C）：同句出现次数 > 「原有次数 ＋ 本次应写处数」⇒ 判重复。

    **必须传 baseline（写入前的 occurrence）**：不传时基线按 0 算，会把**历史存量**重复
    全报出来 —— 实测 CLI 默认跑法报 146 条，全是往年写入的存量（如大普微某句已在库内 11 处），
    与本次无关，属噪音。带基线后只报「本次新增的意料之外重复」。
    """
    occ = occurrence(rows, root)
    want = collections.Counter()
    for r in rows:
        want[(r.get('case', ''), r.get('emp', ''))] += 1
    bad = []
    for (case, emp), (blocks, total) in occ.items():
        base = (baseline or {}).get((case, emp), (0, 0))[1]
        expected = base + want[(case, emp)]
        if total > expected:
            bad.append({'case': case, 'want': want[(case, emp)], 'base': base,
                        'found': total, 'blocks': blocks, 'emp': emp[:90],
                        'reason': 'sentence_duplicated_beyond_plan'})
    return bad


def load_from_maps(root):
    """映射表模式：直接走 apply_rewrite.plans() ＋ 取句，组装成计划行。"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from apply_rewrite import plans, entry_text, sentence
    rows, skipped = [], collections.Counter()
    for r in plans(root):
        title, seg = entry_text(r['dir'], r['new'])
        if not seg:
            skipped['source_missing'] += 1
            continue
        try:
            emp, _src = sentence(seg)
        except ValueError as e:
            skipped[str(e).split('：')[0]] += 1
            continue
        row = dict(r)
        row.update({'emp': emp, 'title': title})
        rows.append(row)
    return rows, skipped


def main():
    global WARN_COV
    ap = argparse.ArgumentParser(description='回写闸门：一句多投／主题匹配（I-0235）')
    ap.add_argument('--methods-root', default=None, help='工作区根（其下含 methods/ 与 cases/）')
    ap.add_argument('--plan', default=None, help='计划 JSON（自定义脚本先导出计划再校验）')
    ap.add_argument('--verify', action='store_true', help='写后自检：库内同句计数')
    ap.add_argument('--json', default=None, help='违规报告输出路径')
    ap.add_argument('--min-cov', type=float, default=WARN_COV, help='覆盖率告警阈值（默认 %.2f，只告警）' % WARN_COV)
    a = ap.parse_args()

    WARN_COV = a.min_cov
    root = a.methods_root or os.getcwd()

    if a.plan:
        rows = load_plan(a.plan)
        src = '计划 %s' % os.path.basename(a.plan)
        body_of = None
        if os.path.isdir(os.path.join(root, 'methods')):
            bodies, _ = _entry_bodies(root)
            body_of = lambda t: bodies.get(t, '')       # noqa: E731
        else:
            print('[提示] 未找到 methods/，跳过覆盖率评估（判据 A/C 不受影响）')
        ok, rejected, warns = check(rows, body_of=body_of)
    elif a.verify:
        rows, _sk = load_from_maps(root)
        bad = verify_rows(rows, root)
        print('存量重复检测（**基线 0**，故含历史存量，不等于是本次造成）：抽查 %d 条，超出计划 %d 条'
              % (len(rows), len(bad)))
        print('   用法：此模式判「库里是否已有同句多投」；判「本次是否写入重复」须在 --apply 前后各跑一次比对')
        print('   ⚠ 归组按「最近 ### 标题」，撞上「章内混排实证」与「悬空扩展行」会误报 —— 结论须逐条看落点再定，勿直接照单删')
        for b in bad[:20]:
            print('   [重复] %s 计划 %d 处 / 库内 %d 处（%d 个条目块）｜ %s'
                  % (b['case'], b['want'], b['found'], b['blocks'], b['emp'][:56]))
        if a.json:
            json.dump(bad, io.open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        return 1 if bad else 0
    else:
        rows, skipped = load_from_maps(root)
        src = '映射表（%d 条，跳过 %d）' % (len(rows), sum(skipped.values()))
        ok, rejected, warns = guard_rows(rows, root)

    print('闸门源：%s' % src)
    _rc = collections.Counter(r['reason'] for r in rejected)
    print('通过 %d 条 ｜ 硬拦 %d 处 %s ｜ 覆盖率告警 %d 条' % (
        len(ok), len(rejected),
        ('（' + '，'.join('%s %d' % (k, v) for k, v in _rc.items()) + '）') if _rc else '',
        len(warns)))
    for r in rejected:
        print('   [拦] %s %s → %s' % (r['case'], r['new'], '/'.join(r['targets'])))
        print('        %s' % r['detail'])
        if r['cov']:
            print('        覆盖度：%s' % '，'.join('%s=%.3f' % (k, v) for k, v in r['cov'].items()))
        print('        句：%s' % r['emp'])
    if warns:
        warns.sort(key=lambda x: x['cov'])
        print('   —— 覆盖度最低 5 条（**仅告警，不自动删**）——')
        for w in warns[:5]:
            print('   [低 %.3f] %s → %s  %s' % (w['cov'], w['case'], w['target'], w['emp'][:52]))

    if a.json:
        json.dump({'ok': len(ok), 'rejected': rejected, 'warns': warns},
                  io.open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('报告 → %s' % a.json)

    return 1 if rejected else 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""S7-b 回写执行器（A-Mem 演化）＋ 回写行修复

**用途**：按各案 `共通点映射_<简称>_<日期>.md`「一、回写清单」把 S6a 定稿的
**高／中高重合**条目回写到旧条目（**低重合不回写，改新增**）：

- **高重合** → 目标条目块尾追加 `- **<案名>实证**：<标题> —— <本案实证首句>（<来源>）`
- **中高**   → 追加 `> **适用场景扩展 YYYY-MM-DD（<案名>）**：…`
- **`--repair`**：修正历史回写行的**截断／括号不配对**（旧脚本硬截断 `emp[:180]` 所致）——
  按源文件重抽「**括号深度为 0 的首句**」，禁硬截断（2026-09-22 实证：205 行受损）

**安全纪律**：
- 默认 **dry-run**；`--apply` 才写盘
- **幂等**：目标条目块内已出现该案名 ⇒ 跳过（重跑不重复追加）
- 只**追加**不删改；按文件分组、行号**降序**插入防漂移
- 写盘一律 `newline="\\n"`（库内行尾统一 LF；见 `docs/ENV-PITFALLS.md` §八）
- 执行后必须 `--refresh-index` ＋ 护栏 0 ERROR ＋ 清单销项（**回写会改变后续条目行号**）

用法：
    python <skill>/scripts/apply_rewrite.py --methods-root <工作区根>              # dry-run 统计
    python <skill>/scripts/apply_rewrite.py --methods-root <工作区根> --apply
    python <skill>/scripts/apply_rewrite.py --methods-root <工作区根> --repair --apply
"""
import argparse
import collections
import datetime
import glob
import io
import json
import os
import re
import sys
import os as _lo, sys as _ls
_ls.path.insert(0, _lo.path.dirname(_lo.path.abspath(__file__)))
from _lib.layout import (METHODS_NAME, VOLUME_NAME, DIR_DOMAIN, DIR_LANG,
                         FINANCE_DOMAIN_FILE, LAW_DOMAIN_FILE, INDUSTRY_DOMAIN_FILE,
                         STYLE_DOMAIN_FILE, LANG_W_FILE, LANG_P_FILE)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# 2026-09-27 修：库内 WL 条目**混用两种形态** —— `### WL-xxxxxx …`（h3）与 `- **WL-xxxxxx**｜…`（粗体列表项，
# 历史存量（2026-09-27 实测 `20_语言专项/投行语言专项_回复WL系列.md` 中 132 行为 h3、另有大量 `**` 形；2026-09-28 正文已外置至 `50_分卷/投行语言专项_回复WL系列_卷NN_*.md`）。原正则只认 h3
# ⇒ 凡目标为 `**` 形条目者一律报 `target_not_in_library`（本批 229/255 条被误判）。现两形态并收。
HDR = re.compile(r'^(?:#{2,4}\s+|-\s+\*\*|\*\*)([A-Z]{1,2})-(\d{2})(\d{4})(?!\d)')
ENTRY = re.compile(r'^###\s+[FLI]-AN\d{4}-\d{2}\s*[｜|]\s*(.+?)\s*$')
ANCHOR = re.compile(r'-\s*\*\*对照锚点\*\*\s*[:：]\s*(.+?)\s*$')
REL = re.compile(r'\[(强化|扩展|新增)\s*([A-Z]{1,2}-\d{5,6})?\s*([^\]]*)\]')
LINE = re.compile(r'^(- \*\*(?P<n1>\S+?)实证\*\*：|> \*\*适用场景扩展 \d{4}-\d{2}-\d{2}（(?P<n2>\S+?)）\*\*：)')
PAT = re.compile(r'^(?P<head>- \*\*\S+?实证\*\*：|> \*\*适用场景扩展 \d{4}-\d{2}-\d{2}（\S+?）\*\*：)'
                 r'(?P<title>.*?)\s+——\s+(?P<rest>.*)$')
# 占位符行识别（2026-10-01 · D5／I-0148）：实证行正文被写成 `……（本案产出文件）` 空壳
STUB = re.compile(r'——\s*……\s*（本案产出文件）\s*$')


def read_text(p):
    return io.open(p, encoding='utf-8', newline='').read()


def write_text(p, t):
    io.open(p, 'w', encoding='utf-8', newline='\n').write(t)


def target_files(root):
    m = os.path.join(root, METHODS_NAME)
    out = [os.path.join(m, DIR_DOMAIN, x) for x in (FINANCE_DOMAIN_FILE, LAW_DOMAIN_FILE,
                                                    INDUSTRY_DOMAIN_FILE, STYLE_DOMAIN_FILE)
           if os.path.isfile(os.path.join(m, DIR_DOMAIN, x))]
    out += [os.path.join(m, DIR_LANG, x) for x in (LANG_W_FILE, LANG_P_FILE)
            if os.path.isfile(os.path.join(m, DIR_LANG, x))]
    out += sorted(glob.glob(os.path.join(m, VOLUME_NAME, '*.md')))
    return out


def build_index(files):
    idx = collections.defaultdict(list)
    for p in files:
        for i, ln in enumerate(read_text(p).split('\n')):
            m = HDR.match(ln)
            if m:
                idx[m.group(1) + '-' + m.group(2) + m.group(3)].append((p, i))
    return idx


_CASE_NAMES = None


def _load_case_names(root):
    """载入「案名规范表」（表一＋表二）的规范案名集合 —— 与门禁 A4 同源。"""
    global _CASE_NAMES
    if _CASE_NAMES is not None:
        return _CASE_NAMES
    _CASE_NAMES = set()
    mroot = os.path.join(root, METHODS_NAME)
    for fn in (os.path.join(mroot, '方法论_案名规范表.md'),
               os.path.join(mroot, 'state', '单案索引对照表.md'),
               os.path.join(root, 'state', '单案索引对照表.md')):
        if not os.path.isfile(fn):
            continue
        for ln in read_text(fn).split('\n'):
            if not ln.strip().startswith('|'):
                continue
            cells = [c.strip().strip('*').strip() for c in ln.strip().strip('|').split('|')]
            if len(cells) >= 3 and re.match(r'^AN\d{4}$', cells[2]):
                if cells[0] and cells[0] not in ('规范案名', '---'):
                    _CASE_NAMES.add(cells[0])
    return _CASE_NAMES


def _case_name(case, root=None):
    """回写标签案名位 —— 用「案名规范表」的规范案名（禁自拟 / 禁截断简称）。

    门禁 `check_entry_contract.py` **A4** 以「案名规范表 表一＋表二」为白名单；
    本函数使**回写器产出的标签天然符合 A4**（2026-09-27 用户裁定固化标签形态；
    本轮 246 行曾触发 A4「未按登记案名」）。
    查不到时**原样返回**（不静默改写），交由 A4 门禁在 S7 收尾拦下。
    """
    if root:
        names = _load_case_names(root)
        # 「case」既可能是简称也可能是公司全称 —— 取匹配项（简称优先，命中即返回）
        if case in names:
            return case
        for n in names:
            if n and (n in case or case in n):
                return n
    return case


def entry_text(case_dir, code):
    """在案目录的专家产出里按编号取条目原文。

    2026-10-01 扩域（A 案批第一子批暴露）：原只循环 `('财务','法律','行业')` ⇒
    **体例域无回写通路**（`产出_体例_<案名>蒸馏.md` 读不到，22 条体例 R1/R2 无法入库）。
    现补 `'体例'`（`产出_体例_*蒸馏.md` ＋ `产出_*_体例蒸馏.md` 双 glob）。
    """
    for role in ('财务', '法律', '行业', '体例'):
        for f in glob.glob(os.path.join(case_dir, '产出_%s_*蒸馏.md' % role)) + glob.glob(os.path.join(case_dir, '产出_*_%s蒸馏.md' % role)):
            t = read_text(f)
            m = re.search(r'^###\s+' + re.escape(code) + r'\s*[｜|]?\s*(.+?)\s*$', t, re.M)
            if m:
                return m.group(1), t[m.end():m.end() + 4000]
    return None, None


def sentence(seg):
    """本案实证首句：取「括号深度为 0 的第一个 。」；抽不到即抛错（**禁静默写占位**）。

    标签正则**容忍任意括号限定词与任意前缀**（2026-10-01 修 · D2②）：
      - `- **本案实证**：`            （标准）
      - `- **本案实证（注册稿）**：`   （稿别限定 —— I-0148 病灶）
      - `- **本案实证（AN0044）**：`   （案号限定）
      - `- **本案实证（森峰激光）**：` （案名限定）
      - `- **原文实证**：` / `- **多案实证**：` / `- **实证**：`（库内共 2,450＋260 处）
    原正则 `r'-\\s*\\*\\*本案实证\\*\\*\\s*[:：]'` 只认标准形态 ⇒ 其余一律 `et=''`
    ⇒ body 落 `……`、src 回退 `'本案产出文件'`，**在库写出 233 处空壳且门禁全绿**（I-0148）。
    """
    # 实证行三形态全收（2026-10-01 实测库内分布）：
    #   ① 加粗列表项  `- **本案实证**：` / `- **原文实证（注册稿）**：`   （1,916＋576 处）
    #   ② 纯文本列表项 `- 本案实证：`                                   （1,358＋468 处）
    #   ③ 无前缀行    `本案实证：`（江苏展芯等案产出件形态）              （少数）
    m = re.search(r'^(?:-\s*)?\*{0,2}[^*：:\n]{0,20}?(?:本案|原文|多案|实证)[^*：:\n]{0,20}?\*{0,2}\s*[:：]\s*(.+)', seg, re.M)
    if not m:
        raise ValueError('emp_missing：实证行标签不可识别（禁写占位）')
    et = m.group(1)
    # 首句切分：取「**所有括号族**深度为 0 的第一个 。」（2026-10-01 修 · D5 截断病灶）。
    #   原实现只追踪圆括号 `（`／`）` ⇒ 引号族内的句号被误判为句末：
    #     实证 `……「…更加公允体现市场份额情况。（基于 FP16）` 被切成
    #     `……。（` 后紧跟孤立 `（基于 FP16）`；`"…断层领先的优势。（问2 P 13）` 同病。
    #   ⇒ 切点落在引号中间，正文被腰斩、尾部残片（`（基于 FP16）`）又被第 24 项误判为「裸页码」。
    #   修：**圆括号 ＋ 全角引号（「」『』）＋ 直角引号（"" ''）四族同追**，任一族未闭合即不算句末；
    #   截断兜底（无句号分支）同用该深度口径。
    _OPEN, _CLOSE = '（「『"‘', '）」』"’'
    depth, cut = 0, -1
    for k, ch in enumerate(et[:400]):
        if ch in _OPEN:
            depth += 1
        elif ch in _CLOSE:
            depth = max(0, depth - 1)
        elif ch == '。' and depth == 0:
            cut = k
            break
    if cut >= 0:
        body = et[:cut + 1]
    else:
        body = et[:260]
        d, last = 0, 0
        for k, ch in enumerate(body):
            if ch in _OPEN:
                d += 1
            elif ch in _CLOSE:
                d -= 1
            if d == 0:
                last = k
        body = body[:last + 1] + '……'
    # 来源代号抽取（2026-10-01 修 · D5 假裸页码病灶）：
    #   原实现 `（[^（）]{0,40}?(?:PAGE|P)\s*\d+…）` 取**第一个**命中 ⇒ 会被正文中的
    #   `（基于 FP16）` 抢走（`FP16` 里含 `P16`，被当成 `P 16`）⇒ 落成来源代号 `基于 FP16`，
    #   既污染 src，又让第 24 项把该行判成「裸页码」（新增 47 处假差）。
    #   修：① 取**最后一个**命中（来源标注惯例在句末，取尾部最符合）；② 命中须以
    #   **来源词打头**（招/问1/问2/PAGE/P/一轮问询/二轮问询 等），排除 `FP16` 这类技术串。
    _CITE = re.compile(r'（[^（）]{0,50}?（?[^（）]{0,20}?）?[^（）]{0,50}?）')
    src = []
    for _c in re.findall(r'（[^（）]{0,60}）', et):
        _inner = _c[1:-1]
        if re.match(r'\s*(?:PAGE|P|招股书|招|问1|问2|问\s*1|问\s*2|一轮问询|二轮问询|第\s*\d+\s*轮)'
                    r'\s*[^\u4e00-\u9fff]{0,3}\s*\d', _inner) or \
                re.search(r'(?:PAGE|招|问\d|一轮问询|二轮问询)\s*P?\s*\d', _inner):
            src.append(_c)
    if not src:
        # 2026-10-01 修（二轮复核 III · Fix C）：
        #   ① `P?` 不认多字母 `PAGE` ⇒ `一轮问询 PAGE 46` 整串读不到、只剩裸 `PAGE 46`
        #      （长括号超 60 字时 paren 分支够不到）。改 `(?:PAGE|P)?`。
        #   ② 补 `第N轮(回复|问询)?`（案例层实存 `第1轮回复 P8`／`第 2 轮 P 22`）——
        #      paren 分支的 `[^\u4e00-\u9fff]{0,3}` 跨不过中文「回复」，故回退串一并补上。
        #   ③ 加固（2026-10-01 复核 IV）：`第N轮` 分支的 `(?:PAGE|P)` **必选**——否则散文
        #      `第 1 轮 3,000 万元` 会被拼成伪 src `问1 3`（旧回退串不含 `第N轮`，属本次新增风险）。
        src = re.findall(r'(?:(?:PAGE|招|问\d|一轮问询|二轮问询)\s*(?:PAGE|P)?\s*\d+(?:[-–、]\d+)?'
                         r'|第\s*\d+\s*轮(?:回复|问询)?\s*(?:PAGE|P)\s*\d+(?:[-–、]\d+)?)', et)
    src = re.sub(r'[（）]', '', src[-1]) if src else '本案产出文件'
    # 来源归一 ＋ 无代号禁静默（2026-10-01 · A 案批 S7 回归修复）：
    #   源举证句若用中文来源名＋PAGE（「招股书 PAGE 50」），直落库即触发第 19 项
    #   条目契约（30 处）＋ 第 24 项裸页码（+29）——同源。此处统一归一为简称。
    #   归一后仍无来源代号（如裸「（PAGE 215）」）⇒ 抛错入待判，**禁写无代号引注**。
    if src != '本案产出文件':
        # 轮次前缀换问N（2026-10-01 二轮 · 契约第 19 项「轮次前缀未换『问N P』」）：`第N轮回复`→`问N`。
        src = re.sub(r'第\s*(\d+)\s*轮(回复|问询|回复意见)?', r'问\1', src)
        src = re.sub(r'招股说明书|招股书', '招', src)
        src = re.sub(r'审核问询回复|问询回复', '问1', src)
        src = re.sub(r'PAGE', 'P', src)
        src = re.sub(r'\s+', ' ', src).strip()
        # 白名单与抽取端（L204/209）口径对齐：`第 N 轮` 亦为合法代号（补 2026-10-01 复核 I）。
        _CODE = r'招|问\s*[12]|一轮|二轮|第\s*\d+\s*轮|注册稿|上会稿|反馈|路演'
        if not re.search(_CODE, src):
            # 「页码在前＋来源在尾括号」体例（如 `PAGE 300（问1）`）：抽取端只认来源词打头，
            #   此处按 src 的页码回读同行紧随括号内的来源词，拼成 `问1 P 300`（补 2026-10-01 复核 II）。
            _pg = re.search(r'P\s*(\d+(?:[-–、]\d+)*)', src)
            if _pg:
                _m2 = re.search(r'(?:PAGE|P)\s*' + re.escape(_pg.group(1)) +
                                r'\s*（\s*(招股说明书|招股书|审核问询回复|问询回复|一轮问询|二轮问询'
                                r'|第\s*\d+\s*轮|招|问\s*[12])\s*）', et)
                if _m2:
                    _code = re.sub(r'招股说明书|招股书', '招', _m2.group(1))
                    _code = re.sub(r'审核问询回复|问询回复', '问1', _code)
                    src = '%s %s' % (_code.strip(), src)
        if not re.search(_CODE, src):
            raise ValueError('src_no_code：来源缺代号（禁写无代号引注）：%s' % src)
        # 正文位同源归一（2026-10-01 二轮 · Fix B）：追加行的**正文**同样会带中文来源名
        #   （`招股书 PAGE 300`），直落库触发同一门禁。只碰「来源词＋PAGE＋数字」引注形态：
        #   已合规串（`招 P 22`／`问1 P 16`）不含 `招股书`／`PAGE` ⇒ 一字不动；散文「招股书披露…」无 PAGE ⇒ 不动。
        #   加固（2026-10-01 复核 IV）：`PAGE` 后加 `(?=\d)`，防 `招股书 PAGE 索引` 这类非引注散文被误改。
        body = re.sub(r'(招股说明书|招股书)\s*PAGE\s*(?=\d)', '招 P ', body)
        body = re.sub(r'(审核问询回复|问询回复)\s*PAGE\s*(?=\d)', '问1 P ', body)
        body = re.sub(r'第\s*(\d+)\s*轮(回复|问询)?\s*PAGE\s*(?=\d)', r'问\1 P ', body)
    if body.strip() in ('……', '') or src == '本案产出文件':
        raise ValueError('emp_missing：抽出正文/来源为空（禁写占位）')
    return body, src


def unclosed(line):
    """截断特征判据：**行末括号深度 > 0**（＝某处 `（` 未闭合，实为硬截断）。

    不用「开闭数量不等」——合法嵌套 `（（一）（二））` 与引文中的孤立 `）`（如「1）中大型 PLC」）
    都会造成数量不等，但**深度归零/为负**，属正常文本（2026-09-22 实证：粗判据误报 1 行）。
    """
    depth = 0
    for ch in line:
        if ch == '（':
            depth += 1
        elif ch == '）':
            depth -= 1
    return depth > 0


def plans(root):
    out = []
    for mp in sorted(glob.glob(os.path.join(root, 'cases', '*', '共通点映射_*_*.md'))):
        case_dir = os.path.dirname(mp)
        name = os.path.basename(case_dir).split('_')[1] if '_' in os.path.basename(case_dir) else ''
        t = read_text(mp)
        if '一、回写清单' not in t:
            continue
        sec = t.split('一、回写清单')[1].split('## 二、')[0]
        for ln in sec.split('\n'):
            m = re.match(r'^\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|\s*(高|中高)\s*\|', ln)
            if not m or '---' in m.group(1) or m.group(1).strip() in ('新案条目', '新案条目 '):
                continue
            nt, field, grade = m.group(1).strip(), m.group(2).strip(), m.group(3)
            # 源编号闸（2026-10-01 扩域 · A 案批第一子批暴露）：原 `^([FLI]-AN\d{4}-\d{2})`
            #   只认 F/L/I 三域案例层编号 ⇒ **体例域源条目（`PL-AN0053-08`／`S-AN0053-04`）
            #   即使入表也被静默丢弃**（22 条体例 R1/R2 无法入库）。
            #   改为 `[A-Z]{1,2}` 并可选 `[A-D]`（兼容案例层范式 `W-AN0020-A05` 形态）。
            nc = re.match(r'^([A-Z]{1,2}-AN\d{4}-[A-D]?\d{2})', nt)
            # 目标编号闸（2026-10-01 修 · D2①）：原 `r'\b([FLIWS]{1,2}-\d{2}\d{4})\b'` 有两处失效 ——
            #   ① `I-CL04-06`（CL 为字母）不匹配 ⇒ 第二批 11 条 I-CL 目标未被识别、只能手工回写（R-0066）；
            #   ② `\b` 在 `PL-010097` 的 `-01` 前不成立 ⇒ PL/S 形态同险。
            # 改为**显式枚举前缀 + 只禁左侧字母数字**：既保全 `PL-`/`WL-` 双字母前缀，
            # 又阻止 `L-010097` 从中截断，且支持从「见 PL-010097 条」等句中提取。
            tc = re.search(r'(?<![A-Za-z0-9])(?:PL-\d{2}\d{4}|WL-\d{2}\d{4}|S-\d{2}\d{4}'
                           r'|F-\d{2}\d{4}|L-\d{2}\d{4}|I-\d{2}\d{4}'
                           r'|I-CL\d{2}-\d{2}|W-AN\d{4}-[A-D]\d{2})', field)
            if not (nc and tc):
                continue
            out.append({'case': name, 'dir': case_dir, 'new': nc.group(1),
                        'target': tc.group(0), 'grade': grade})
    return out


def do_rewrite(root, apply_):
    files = target_files(root)
    idx = build_index(files)
    rows, pend = [], []
    for r in plans(root):
        title, seg = entry_text(r['dir'], r['new'])
        if not title:
            pend.append((r['case'], r['new'], 'source_missing'))
            continue
        # 唯一匹配门（2026-09-26 · 属「**定点定位类**」前置门）
        #   **恰好 1 处命中才改；0 处／多处一律转人工判定。**
        #   原实现直接取 `idx[r['target']][0]` ⇒ 同编号在库内多处出现时**静默选第一个**写入
        #   （多解越权；与「招·招·注册稿」84 处误伤同族：**在无唯一确定性时动手**）。
        #   注意：本门**只适用于「按编号定位唯一位置」的脚本**；批量改名类（normalize_case_names
        #   ／fix_volume_case_by_segment）**本来就要改多处同串**，套用本门会改坏 —— 见
        #   `references/govern/fix-tools.md`「唯一匹配门」节的**分类前置门**表。
        _hits = idx.get(r['target'], [])
        if not _hits:
            pend.append((r['case'], r['new'], 'target_not_in_library:' + r['target']))
            continue
        if len(_hits) != 1:
            pend.append((r['case'], r['new'],
                         'target_ambiguous:%s x%d（多处命中，须人工定目标）' % (r['target'], len(_hits))))
            continue
        try:
            body, src = sentence(seg)
        except ValueError as e:
            # 禁静默降级（2026-10-01）：抽不到正文即入待判清单，**绝不写占位符**。
            pend.append((r['case'], r['new'], str(e)))
            continue
        r.update({'title': title, 'emp': body, 'src': src,
                  'file': _hits[0][0], 'line': _hits[0][1]})
        rows.append(r)
    print('可执行回写 %d 条 ｜ 待人工判定 %d 条' % (len(rows), len(pend)))
    c = collections.Counter(x['grade'] for x in rows)
    print('分布：高 %d ／ 中高 %d' % (c['高'], c['中高']))
    for x in pend[:8]:
        print('   [待判]', x[0], x[1], x[2])
    byfile = collections.defaultdict(list)
    for r in rows:
        byfile[r['file']].append(r)
    written, skipped = 0, 0
    for p, rs in byfile.items():
        lines = read_text(p).split('\n')
        ins = collections.defaultdict(list)
        for r in rs:
            i = r['line']
            j = i + 1
            while j < len(lines) and not lines[j].startswith('#'):
                j += 1
            if r['case'] in '\n'.join(lines[i:j]):
                skipped += 1
                continue
            if r['grade'] == '高':
                # 标签形态（2026-09-27 用户裁定固化）：`- **<案名>实证**：<标题> —— <本案实证首句>（<来源>）`
                # 案名位取「登记案名」（案名规范表简称，与门禁 A4 同源），非自拟；本轮 246 行曾触发 A4 未按登记案名。
                add = '- **%s实证**：%s —— %s（%s）' % (
                    _case_name(r['case'], root), r['title'][:60], r['emp'], r['src'])
            else:
                add = '> **适用场景扩展 %s（%s）**：%s —— %s（%s）' % (
                    datetime.date.today().isoformat(),
                    _case_name(r['case'], root), r['title'][:60], r['emp'], r['src'])
            ins[j - 1].append(add)
        for pos in sorted(ins, reverse=True):
            for add in ins[pos]:
                lines.insert(pos + 1, add)
                written += 1
        if apply_ and ins:
            write_text(p, '\n'.join(lines) + '\n')
    print('写入 %d 条 ｜ 幂等跳过 %d 条 ｜ 写盘: %s' % (written, skipped, '是' if apply_ else '否（dry-run）'))
    return written


def do_repair(root, apply_, cases_root=None):
    croot = cases_root or os.path.join(root, 'cases')
    cases = {}
    # 案目录 glob（2026-10-01 修）：原 `*_*_2026*` 只覆盖 2026 年披露案，
    # 把 2025 年披露的案（沐曦 20251024／高特 20251229／大普微 20251229 等）整批漏掉
    # ⇒ 其占位符永远配不到源。改为 `*_*_20[0-9][0-9]*`（四位年份通配）。
    for d in glob.glob(os.path.join(croot, '*_*_20[0-9][0-9]*')):
        if '_discarded' in os.path.basename(d):
            continue
        b = os.path.basename(d)
        if '_' in b:
            cases[b.split('_')[1]] = d
    idx = {}
    for name, d in cases.items():
        for role in ('财务', '法律', '行业'):
            for f in glob.glob(os.path.join(d, '产出_%s_*蒸馏.md' % role)) + glob.glob(os.path.join(d, '产出_*_%s蒸馏.md' % role)):
                t = read_text(f)
                for m in re.finditer(r'^###\s+[FLI]-AN\d{4}-\d{2}\s*[｜|]\s*(.+?)\s*$', t, re.M):
                    try:
                        body, src = sentence(t[m.end():m.end() + 4000])
                    except ValueError:
                        continue
                    idx[(name, m.group(1)[:18])] = (m.group(1), body, src)
    fixed, stub_hit, stub_skip = 0, 0, 0
    for p in target_files(root):
        lines = read_text(p).split('\n')
        out, changed = [], False
        for l in lines:
            # 分支一（2026-10-01 增 · D5）：**占位符行** —— `—— ……（本案产出文件）`。
            # 触发源＝旧 `sentence()` 静默降级（标签不识别 ⇒ et='' ⇒ 写占位），I-0148；
            # 存量 233 处（09-27 批遗留），门禁无扫描项故长期未拦。
            if STUB.search(l):
                m = PAT.match(l)
                nm = LINE.match(l)
                name = (nm.group('n1') or nm.group('n2')) if nm else ''
                hit = idx.get((name, m.group('title').strip()[:18])) if m else None
                if hit:
                    out.append('%s%s —— %s（%s）' % (m.group('head'), hit[0], hit[1], hit[2]))
                    stub_hit += 1
                    changed = True
                else:
                    stub_skip += 1
                    out.append(l)
                continue
            # 分支二（既有）：截断／括号不配对的回写行
            if PAT.match(l) and unclosed(l):
                m = PAT.match(l)
                nm = LINE.match(l)
                name = (nm.group('n1') or nm.group('n2')) if nm else ''
                hit = idx.get((name, m.group('title').strip()[:18]))
                if hit:
                    out.append('%s%s —— %s（%s）' % (m.group('head'), hit[0], hit[1], hit[2]))
                else:
                    rest = re.sub(r'（（.*$', '（', m.group('rest')).rstrip('；，、 ')
                    out.append('%s%s —— %s）' % (m.group('head'), m.group('title'), rest))
                fixed += 1
                changed = True
                continue
            out.append(l)
        if changed and apply_:
            write_text(p, '\n'.join(out) + '\n')
    print('修复回写行 %d 行 ｜ 占位符回填 %d 行 ｜ 占位符待人工 %d 行 ｜ 写盘: %s'
          % (fixed, stub_hit, stub_skip, '是' if apply_ else '否（dry-run）'))
    return fixed + stub_hit


def main():
    ap = argparse.ArgumentParser(description='S7-b 回写执行器（＋ --repair 修历史截断行）')
    ap.add_argument('--methods-root', default=os.getcwd(), help='工作区根（其下含 methods/ 与 cases/）')
    ap.add_argument('--cases-root', default=None,
                    help='材料根（含各案目录；缺省＝<工作区根>/cases）。'
                         '库与 cases 分置时必传（如 daily_learning/cases）')
    ap.add_argument('--repair', action='store_true', help='只跑「回写行修复」模式')
    ap.add_argument('--apply', action='store_true', help='实际写盘（缺省 dry-run）')
    a = ap.parse_args()
    root = a.methods_root
    if not os.path.isdir(os.path.join(root, METHODS_NAME)):
        print('[ENV-ERROR] 未找到方法论库: %s' % os.path.join(root, METHODS_NAME), file=sys.stderr)
        return 2
    if a.repair:
        cr = a.cases_root or os.path.join(root, 'cases')
        if not os.path.isdir(cr):
            print('[ENV-ERROR] --repair 需可读的材料根（案目录所在）: %s' % cr, file=sys.stderr)
            print('  提示：库与 cases 分置时传 --cases-root，如 '
                  '--cases-root /path/to/daily_learning/cases', file=sys.stderr)
            return 2
        do_repair(root, a.apply, cr)
    else:
        do_rewrite(root, a.apply)
    print('\n下一步（强制）：① 回写清单销项 ② `daily_distill.py --refresh-index` '
          '③ `check_methods_health.py` 0 ERROR ④ `replay_gate_report.py` 四项门禁')
    return 0


if __name__ == '__main__':
    sys.exit(main())

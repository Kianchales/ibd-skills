#!/usr/bin/env python3
"""格式核对 · 文字类核对域（`--checks text` 组）。

归属：本模块原为 `check_content.py` 的「核对项：文字类 / 核对项：标点」两段，
2026-09-11 按业务域拆组时独立成文件（P2-⑧）。

收录 7 个核对项（与 `check_content.py` 的 `CHECK_REGISTRY` 一一对应）：
  · `heading_seq`  标题层级序号连续性（跳号/重号/倒退）                HIGH
  · `terms`        用词规范性（错别字/异形词；支持外部清单扩展）        MEDIUM
  · `dates`        日期写法统一（十种形式识别）                        MEDIUM
  · `spaces`       多余空格 / 数字前后空格 / 重复标点                  HIGH
  · `abbr`         释义简称统一（冲突/前置使用/未定义复用/引号风格）    MEDIUM
  · `geo`          国家城市表述合规（外部清单驱动）                    HIGH
  · `punctuation`  中英文标点（前后字符判定）                          HIGH

**文字层的执行时序铁律**：本组核对项须在**套样式之前**跑（文字层返工会导致样式重做）。
详见 `ibd-doc-review` 的 `references/workflow.md` 附录第 1 条时序铁律。
"""

import json
import os
import re
from collections import Counter

from content_common import (
    ALL_LEVELS,
    FULL_PUNCTS,
    HALF_FULL_MAP,
    HALF_PUNCTS,
    Issue,
    LEVEL_NAMES,
    SKILL_DIR,
    _char_class,
    _disp_num,
    _neighbor_class,
    parse_numbering,
)


# ---------------------------------------------------------------- heading_seq


def check_heading_seq(items):
    """标题层级序号连续性 v3：
    - 跳过目录条目（以 1~4 位纯数字结尾 = 带页码特征的行）
    - 同层必须递增 +1（跳号/重号/倒退报 HIGH）
    - 进入更深层级：重新起 1；回到更高层级：沿该层自身上次值 +1 继续"""
    issues = []
    prev_li = -1
    prev_val = None
    last_at_level = {}
    seq_no = 0
    toc_tail_re = re.compile(r"\s*[0-9]{1,4}\s*$")
    for kind, info in items:
        if kind != "body" or not info["text"]:
            continue
        text = info["text"]
        # 引号包裹的引用内容不参与序号核对（2026-08-27 裁定：引用条款/承诺原文
        # 内部的「1.」「（一）」等为其自身格式，不应与正文序号链混排）
        stripped = text.strip()
        if stripped[:1] in ('"', "'", "\u201c", "\u201d", "\u300c", "\u300d") or \
           (stripped.startswith('"') and stripped.endswith('"')):
            continue
        # 长段落且含成对引号 → 引用条款/承诺原文，其内部序号不参与正文链
        if len(stripped) > 80 and re.search(r'[“"\u300c][^“"\u300d]{6,}[”"\u300d]', stripped):
            continue
        parsed = parse_numbering(text)
        if not parsed:
            continue
        # 目录条目：以纯数字结尾（页码特征）
        if toc_tail_re.search(text):
            continue
        seq_no += 1
        level, val, raw = parsed
        name = LEVEL_NAMES[level]
        loc = f"{name}#{seq_no}「{text[:22]}」"
        li = ALL_LEVELS.index(level)

        def disp(v):
            return _disp_num(level, v) if v else str(v)

        def note(expected):
            return f"序号「{raw}」，应调整为目标「{disp(expected)}」"

        problem = None
        suggestion = ""
        severity = "HIGH"

        if prev_li == -1:
            expected = 1
            if val != 1:
                problem = f"全文首个序号为「{raw}」（应为起始值 1/一）"
        elif li == prev_li:
            expected = prev_val + 1
            if val != expected:
                kind_str = ("跳号" if val > expected else
                            "重号" if val == prev_val else "倒退")
                problem = (f"序号「{raw}」，前一号为「{_disp_num(level, prev_val)}」，{kind_str}")
                suggestion = f"调整为「{_disp_num(level, expected)}」"
        elif li > prev_li:
            expected = 1
            if val != 1:
                problem = (f"进入更深层级时首个序号为「{raw}」（通常应为起始值 1/一）；"
                           f"若本意是与上层衔接请检查上文是否缺号")
                suggestion = f"如需延续请调整为「{_disp_num(level, expected)}」"
                severity = "LOW"
        else:
            base = last_at_level.get(level)
            expected = (base + 1) if base is not None else 1
            if val != expected:
                kind_str = "跳号" if val > expected else "倒退/重号"
                problem = (f"回到该层级时序号「{raw}」，上一次该层为"
                           f"「{_disp_num(level, base)}」，{kind_str}——若为新小节重新起号可忽略")
                suggestion = f"如需延续请调整为「{_disp_num(level, expected)}」"
                severity = "LOW"

        if problem:
            issues.append(Issue(
                "heading_seq", name, loc, text[:40], problem,
                suggestion if suggestion else f"目标序号 {expected}", severity))
        prev_li = li
        prev_val = val
        last_at_level[level] = val
    return issues


# ---------------------------------------------------------------- terms 用词规范


def load_external_rules(path):
    """外部术语规则清单 JSON：[{"pattern":"...","problem":"...","suggestion":"..."}]。"""
    if path and os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return [(r.get("pattern", ""), r.get("problem", ""), r.get("suggestion", ""))
                    for r in data if isinstance(r, dict) and r.get("pattern")]
        except Exception as e:
            print(f"[WARN] 术语清单读取失败({path}): {e}")
    return []


BUILTIN_TERM_RULES = [
    {"pattern": r"帐[面户务套]", "problem": "'帐'应为'账'（账面/账户/账务/账套）",
     "suggestion": "统一使用'账'"},
    {"pattern": r"(?<!可)其它(?=[^\u4e00-\u9fff]|$)", "problem": "'其它'宜规范为'其他'",
     "suggestion": "统一使用'其他'"},
]


def check_terms(doc_text, term_rules=None):
    # 2026-09-11 修复：BUILTIN_TERM_RULES 是 dict 列表，原先 `list(...)` 后直接
    # `pat, problem, suggestion = rule` 会把 dict **解包成键名**（'pattern'/'problem'/
    # 'suggestion'），于是 re.compile('pattern') 在正文里搜英文单词 "pattern" →
    # 内置规则从未命中过（terms 核对项长期静默失效）。此处统一转三元组。
    rules = [(r["pattern"], r["problem"], r["suggestion"]) for r in BUILTIN_TERM_RULES]
    rules += [(r["pattern"], r["problem"], r["suggestion"]) for r in (term_rules or [])]
    issues = []
    reported = Counter()
    for pat, problem, suggestion in rules:
        try:
            rx = re.compile(pat)
        except re.error:
            continue
        hits = list(rx.finditer(doc_text))
        shown = 0
        for m in hits:
            reported[pat] += 1
            shown += 1
            if shown > 3:
                break
            near_l = max(0, m.start() - 12)
            snippet = doc_text[near_l:m.end() + 12].replace("\n", "")
            issues.append(Issue("terms", "用词规范",
                                f"全文出现 {len(hits)} 次，示例：「…{snippet[:26]}…」",
                                f"{problem}（命中「{m.group(0)[:16]}」）",
                                suggestion or "", "MEDIUM"))
    return issues


# ---------------------------------------------------------------- dates


MONTH_EN = "Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
DATE_FORMS = [
    ("中文 年月日（2024年6月30日）", re.compile(r"20\d{2}年\d{1,2}月\d{1,2}日?")),
    ("中文 年月（2024年6月）", re.compile(r"20\d{2}年\d{1,2}月(?![\d一二三四五六七八九十]{1,3}日)")),
    ("横线年月日（2024-06-30）", re.compile(r"(?<![\d./-])20\d{2}-\d{1,2}-\d{1,2}(?![\d.-])")),
    ("点分隔年月日（2024.6.30）", re.compile(r"(?<![\d./-])20\d{2}\.\d{1,2}\.\d{1,2}(?![\d.-])")),
    ("斜杠年月日（2024/06/30）", re.compile(r"(?<![\d./-])20\d{2}/\d{1,2}/\d{1,2}(?![\d./-])")),
    ("横线年月（2024-06）", re.compile(r"(?<![\d./-])20\d{2}-\d{2}(?![-\d])")),
    ("连写式 YYYYMMDD（20240630）", re.compile(r"(?<![\d.])(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])(?!\d)")),
    ("英文月缩写（Jun 2024 / Jun 30, 2024）",
     re.compile(rf"\b(?:{MONTH_EN})\.?,?(?:\s+\d{{1,2}},)?\s*20\d{{2}}\b|\b20\d{{2}},?\s+(?:{MONTH_EN})\.?\s+\d{{1,2}}\b", re.I)),
    ("美式 月/日/年（06/30/2024）", re.compile(r"(?<![\d/.])(?:0?[1-9]|1[0-2])/(?:0[1-9]|[12]\d|3[01])/20\d{2}(?![\d/.])")),
    ("英文 年月（2024-05）", re.compile(r"(?<![\d./-])20\d{2}-(?:0[1-9]|1[0-2])(?![-\d])(?=\D|$)")),
]


def check_dates(items):
    counters = Counter()
    samples = {}
    for i, (kind, info) in enumerate(items):
        t = info["text"]
        if not t:
            continue
        for fname, pat in DATE_FORMS:
            hits = pat.findall(t)
            if hits:
                counters[fname] += len(hits)
                samples.setdefault(fname, []).append((i, kind, info, t))

    issues = []
    if not counters:
        return issues
    # 2026-08-27 裁定：中文「年月日/年月」为最正式表述，可与另一种统一格式共存——
    # 主导判定排除中文式，其余形式内部再统一
    excl = {"中文 年月日（2024年6月30日）", "中文 年月（2024年6月）"}
    dom_items = [(f, c) for f, c in counters.most_common() if f not in excl]
    dominant, dom_n = dom_items[0] if dom_items else (None, 0)
    others = {f: c for f, c in counters.items() if f != dominant and f not in excl}
    if dominant is not None and others:
        others_str = "、".join(f"{f}×{c}" for f, c in sorted(others.items(), key=lambda x: -x[1]))
        issues.append(Issue(
            "dates", "日期写法统一", "全文",
            f"主导「{dominant}」×{dom_n}；其余 {others_str}",
            f"建议全文统一为「{dominant}」，少数派明细如下", "MEDIUM"))
        for fname, lst in samples.items():
            # 中文「X年X月X日」为最正式表述（2026-08-27 裁定），永不列入少数派
            if fname in excl or fname == dominant or len(issues) > 120:
                continue
            shown_loc = set()
            for (i, kind, info, t) in lst:
                pat = dict(DATE_FORMS)[fname]
                m = pat.search(t)
                if not m:
                    continue
                ctx_l = max(0, m.start() - 12)
                loc = ("表格" if kind == "cell" else "正文") + \
                      (f"表{info['table_no']}" if kind == "cell" else f"#{i + 1}") + \
                      f"「…{t[ctx_l:m.end() + 8]}…」"
                if loc in shown_loc:
                    continue
                shown_loc.add(loc)
                issues.append(Issue("dates", "日期写法统一", loc, m.group(0),
                                    "非主流写法", f"建议改为「{dominant}」", "LOW"))
                if len(shown_loc) >= 8:
                    break

    sep_counter = Counter()
    sep_sample = {}
    for i, (kind, info) in enumerate(items):
        t = info["text"]
        for m in re.finditer(r"20\d{2}\s*([．.\-/])\s*\d{1,2}", t):
            sp = "." if m.group(1) in ".．" else m.group(1)
            key = "点分隔(.)" if sp == "." else "横线分隔(-)" if sp == "-" else f"其他({sp})"
            sep_counter[key] += 1
            sep_sample.setdefault(key, i)
    if len(sep_counter) > 1:
        issues.append(Issue(
            "dates", "日期写法统一", "全文",
            "分隔符不统一：" + "、".join(f"{k}×{v}" for k, v in sep_counter.most_common()),
            "建议统一分隔符",
            f"各形式首现位置示例：{sorted(set(sep_sample.values()))}", "LOW"))
    return issues


# ---------------------------------------------------------------- spaces 多余空格与重复标点

RE_MULTI_SPACE_CJK = re.compile(r"[\u4e00-\u9fff]  +[\u4e00-\u9fff]")
RE_DUP_CN_PUNCT = re.compile(r"([。，；：？！、])\1+")
RE_DUP_HALF_PUNCT = re.compile(r"[,.;:!?]{2,}")
RE_PUNCT_MIX = re.compile(r"。\.|\.。|，,|,，|；;|::")
# 数字前后不加空格（2026-09-11 用户裁定）：中文/全角标点 与 阿拉伯数字 之间不得有空格。
# 西文缩写与数字之间（GB 35114）不匹配——前邻字符是字母而非汉字，天然豁免。
RE_SPACE_CJK_NUM = re.compile(r"[\u4e00-\u9fff][ \t]+\d|\d[ \t]+[\u4e00-\u9fff]")


def check_spaces(items):
    issues = []
    for i, (kind, info) in enumerate(items):
        t = info["text"]
        if not t:
            continue
        layout_spacing = bool(re.search(r"年\s{2,}月\s{2,}日", t) or
                              re.search(r"目\s{2,}录", t))
        # 排版性豁免（2026-08-27 实测）：签署页「年 月 日」、目录页「目 录」为规范排版；
        # 少量短词宽间隔（如签署页人名「邱  嵩」）降为提示级
        for m in RE_MULTI_SPACE_CJK.finditer(t):
            ctx_l = max(0, m.start() - 10)
            snippet = t[ctx_l:m.end() + 10]
            if layout_spacing or re.search(r"目\s{2,}录", t):
                continue
            # 短词宽间隔（签署页人名/对齐排版，2026-08-27 裁定）完全忽略
            if len(re.sub(r"\s", "", t)) <= 6:
                continue
            issues.append(Issue(
                "spaces", "多余空格/标点", "正文" + f"#{i + 1}" +
                f"「…{snippet[:24]}…」", m.group(0),
                "中文之间出现连续空格",
                "确认是否为刻意排版；否则删除多余空格", "HIGH"))
        for m in RE_SPACE_CJK_NUM.finditer(t):
            if layout_spacing or re.search(r"目\s{2,}录", t):
                continue
            ctx_l = max(0, m.start() - 10)
            issues.append(Issue(
                "spaces", "多余空格/标点", "正文" + f"#{i + 1}" +
                f"「…{t[ctx_l:m.end() + 10]}…」", m.group(0),
                "中文与数字之间出现空格（数字前后不加空格）",
                "删除该空格", "HIGH"))
        for m in RE_DUP_CN_PUNCT.finditer(t):
            ctx_l = max(0, m.start() - 10)
            issues.append(Issue(
                "spaces", "多余空格/标点", "正文" + f"#{i + 1}" +
                f"「…{t[ctx_l:m.end() + 10]}…」", m.group(0),
                f"全角标点重复：「{m.group(0)}」", "去重标点", "HIGH"))
        for m in RE_PUNCT_MIX.finditer(t):
            ctx_l = max(0, m.start() - 10)
            issues.append(Issue(
                "spaces", "多余空格/标点", "正文" + f"#{i + 1}" +
                f"「…{t[ctx_l:m.end() + 10]}…」", m.group(0),
                "中英标点混排", "按语境保留一个并统一全半角", "HIGH"))
        for m in RE_DUP_HALF_PUNCT.finditer(t):
            if re.fullmatch(r"\.{3}|…+", m.group(0)):
                continue  # 省略号
            # 缩写固定用法豁免（2026-08-27 裁定）：Co.,Ltd. / Inc., 等
            if m.group(0)[0] == "." and m.start() > 0 and t[m.start() - 1].isalpha():
                continue
            ctx_l = max(0, m.start() - 10)
            issues.append(Issue(
                "spaces", "多余空格/标点", "正文" + f"#{i + 1}" +
                f"「…{t[ctx_l:m.end() + 10]}…」", m.group(0),
                "连续半角标点重复", "修正标点", "MEDIUM"))
    return issues


# ---------------------------------------------------------------- abbr 释义简称

ABBR_DEF_RE = re.compile(
    r"([\u4e00-\u9fffA-Za-z0-9][\u4e00-\u9fffA-Za-z0-9·]{1,39}"
    r"(?:股份有限公司|有限公司|有限责任公司|公司|企业|集团|中心|基金|计划|银行|证券)?"
    r"\s*[（(]\s*以下简称\s*[「\"'『]?([^」\"'』()）]{1,25})[」\"'』]?\s*[）)])")


def check_abbr(doc_text):
    issues = []
    defs = {}
    quote_styles = Counter()
    for m in ABBR_DEF_RE.finditer(doc_text):
        full, short = m.group(1).strip(), m.group(2).strip()
        defs.setdefault(short, []).append((full, m.start()))
        qm = re.search(r"以下简称\s*([「\"'『])", m.group(0))
        if qm:
            quote_styles[qm.group(1)] += 1

    # 同名简称多全称 → 冲突
    for short, pairs in sorted(defs.items()):
        uniq = sorted({p[0] for p in pairs})
        if len(uniq) > 1:
            issues.append(Issue(
                "abbr", "释义简称", f"简称「{short}」（偏移{pairs[0][1]} 起）",
                " / ".join(uniq[:4]),
                f"同名简称对应 {len(uniq)} 个不同全称，存在指向冲突风险",
                "请核实区分口径或更换简称", "MEDIUM"))

        defined_at = min(p[1] for p in pairs)
        full_name = pairs[0][0]

        # 定义前使用（问题级）
        pre_count = doc_text.count(short, 0, defined_at)
        if pre_count > 0:
            issues.append(Issue(
                "abbr", "释义简称", f"简称「{short}」首次定义前",
                short, f"首次定义之前已独立使用 {pre_count} 次",
                "投行惯例简称应在首次全称处即时定义，请核实前置出现是否需补定义或改写",
                "MEDIUM"))

        # 定义后全称复用 ≥3（提示级）
        later_count = doc_text.count(full_name, defined_at + len(pairs[0][0]))
        if later_count >= 3:
            tail = doc_text.find(full_name, defined_at)
            issues.append(Issue(
                "abbr", "释义简称", f"约偏移{tail}", full_name,
                f"已定义简称后仍以全称出现 {later_count} 次",
                f"建议统一切换为简称「{short}」", "LOW"))

    # 未定义使用的疑似简称：括号内纯中文短语，未定义但正文独立复用 ≥2 次（提示级）
    PAREN_SHORT_RE = re.compile(r"[（(]([\u4e00-\u9fff]{2,8})[）)]")
    PAREN_SKIP = {"以下简称", "转回", "转销", "续上表", "承上表"}
    KEYWORD_EXCLUDE = ("万元", "亿元", "年度", "期间", "所得税", "情况")
    # 常见词白名单（2026-08-27 裁定：专业术语/地名/常规表述/数字无需定义，不视为疑似未定义简称）
    ABBR_WHITELIST = {
        # 投行专业术语
        "独立董事", "草案", "主承销商", "董事长", "副董事长", "监事", "监事会",
        "监事会主席", "职工代表监事", "股东大会", "董事会", "董事会秘书", "董秘",
        "总经理", "财务总监", "独立财务顾问", "保荐机构", "联席保荐机构",
        "承销商", "律师事务所", "会计师事务所", "律师", "会计师",
        "审计委员会", "提名委员会", "薪酬与考核委员会", "战略委员会", "审核委员会",
        "执行董事", "非执行董事", "高级管理人员", "核心技术人员", "控股股东",
        "实际控制人", "关联方", "关联交易", "募集资金", "募集资金投资项目",
        "招股说明书", "上市规则", "公司章程", "公司法", "证券法",
        # 地名
        "上海", "北京", "深圳", "广州", "杭州", "南京", "成都", "重庆", "武汉",
        "西安", "天津", "苏州", "宁波", "青岛", "厦门", "长沙", "郑州", "济南",
        "合肥", "福州", "昆明", "大连", "无锡", "佛山", "东莞", "珠海", "中山",
        "境外", "境内", "中国大陆", "香港", "澳门", "台湾",
        # 常规表述
        "一级", "二级", "三级", "四级", "五级", "六级", "七级", "八级",
        "高级", "中级", "初级", "个人", "单位", "金额", "数量", "比例",
        "发行人", "公司", "集团", "企业", "有限合伙", "合伙企业",
    }
    CN_NUM_WORD = re.compile(r"^[一二三四五六七八九十百千两零]{2,8}$")  # 十三/十四/三十一等数字词
    paren_counts = Counter()
    for m in PAREN_SHORT_RE.finditer(doc_text):
        phrase = m.group(1)
        if phrase in PAREN_SKIP or phrase in defs or phrase in ABBR_WHITELIST:
            continue
        if any(k in phrase for k in KEYWORD_EXCLUDE):
            continue
        if CN_NUM_WORD.match(phrase):
            continue
        paren_counts[phrase] += 1
    for phrase, pc in paren_counts.most_common():
        reuse = doc_text.count(phrase) - pc
        if pc >= 1 and reuse >= 2:
            issues.append(Issue(
                "abbr", "释义简称", "全文", phrase,
                f"括号注释短语「{phrase}」（{pc} 处）在正文独立复用 {reuse} 次，未见「以下简称」定义——疑似未定义简称",
                "若作为简称请补规范定义；若非简称可忽略", "LOW"))

    if len(quote_styles) > 1:
        issues.append(Issue(
            "abbr", "释义简称", "全文",
            "、".join(f"{k}×{v}" for k, v in quote_styles.most_common()),
            "「以下简称」引号风格不统一", "建议全文统一引号风格", "LOW"))
    return issues


# ---------------------------------------------------------------- geo 国家/城市表述合规

SENSITIVE_TERMS_FILE = os.path.join(SKILL_DIR, "references", "sensitive_terms.json")
LEVEL_MAP = {"CRITICAL": "HIGH", "IMPORTANT": "MEDIUM", "MINOR": "LOW"}


def load_geo_rules(geo_file):
    """敏感词清单：默认加载 skill 内置 references/sensitive_terms.json；
    --geo-file 提供的清单会**追加**进来。支持 [{pattern|term, level, note, suggestion}]。"""
    rules = []
    sources = [SENSITIVE_TERMS_FILE]
    if geo_file and geo_file not in ("", "/dev/null"):
        sources.insert(0, geo_file)
    for src in sources:
        if src and os.path.isfile(src):
            try:
                with open(src, encoding="utf-8") as f:
                    data = json.load(f)
                for g in data:
                    if isinstance(g, dict) and (g.get("pattern") or g.get("term")):
                        rules.append({
                            "pattern": g.get("pattern") or re.escape(g["term"]),
                            "level": g.get("level", "CRITICAL"),
                            "note": g.get("note", ""),
                            "suggestion": g.get("suggestion", ""),
                        })
            except Exception as e:
                print(f"[WARN] 敏感词清单读取失败({src}): {e}")
    return rules


def check_geo(doc_text, geo_rules):
    """国家/城市表述合规：清单驱动，pattern 支持 JSON 正则；CRITICAL=HIGH，
    IMPORTANT=MEDIUM，MINOR=LOW。逐处命中报告位置与上下文。"""
    issues = []
    for rule in (geo_rules or []):
        try:
            rx = re.compile(rule["pattern"])
        except re.error as e:
            print(f"[WARN] 敏感词规则编译失败({rule['pattern'][:20]}): {e}")
            continue
        severity = LEVEL_MAP.get(rule.get("level", "CRITICAL"), "HIGH")
        matches = list(rx.finditer(doc_text))
        if not matches:
            continue
        shown = 0
        for m in matches:
            ctx_l = max(0, m.start() - 12)
            snippet = doc_text[ctx_l:m.end() + 14].replace("\n", "")
            loc = f"全文（首现于「…{snippet[:30]}…」）" if shown == 0 else f"全文（第 {shown + 1} 处）"
            issues.append(Issue(
                "geo", "国家/地区表述合规", loc,
                m.group(0)[:40],
                f"{rule.get('level')}级：{rule.get('note', '')}（累计 {len(matches)} 处）".strip(),
                rule.get("suggestion", ""), severity))
            shown += 1
            if shown >= 3:   # 每条规则最多列 3 处明细
                break
    return issues


# ---------------------------------------------------------------- punctuation 中英文标点


def check_punctuation(items):
    """标点规则（按前后字符类型判定）：
    - 半角标点的相邻非空字符任一侧为中文 → 应为全角；
    - 全角标点两侧均为英文/数字 → 应为半角；
    - 其余间隔场景默认中文标点不报。
    中文语境直排引号单独提示。"""
    issues = []
    half_set = set(HALF_PUNCTS)
    full_set = set(FULL_PUNCTS)

    def add(kind, i, info, s, start, end, problem, suggestion, severity="HIGH"):
        ctx_l = max(0, start - 10)
        snippet = s[ctx_l:end + 10].replace("\n", "")
        loc = ("表格" + f"表{info['table_no']}" if kind == "cell"
               else f"正文#{i + 1}") + f"「…{snippet[:24]}…」"
        issues.append(Issue("punctuation", "中英文标点", loc,
                            s[start:end], problem, suggestion, severity))

    for i, (kind, info) in enumerate(items):
        t = info["text"]
        if not t:
            continue
        # 英文缩写内部句点豁免（2026-08-27 裁定）：Inc./Ltd./Co. 后接中文等
        abbrev_re = re.compile(
            r"\b(?:Inc|Ltd|Co|Corp|No|Vol|Dr|Mr|Ms|St)\.\S{0,4}"
            r"|\b[A-Z]{1,3}(?:\.[A-Z]{1,3})+\.\S{0,2}")
        abbrev_spans = [(m.start(), m.end()) for m in abbrev_re.finditer(t)]

        def in_abbrev(pos):
            return any(a <= pos <= b for a, b in abbrev_spans)

        for k, ch in enumerate(t):
            if ch in half_set:
                pc, _pj = _neighbor_class(t, k, -1)
                nc, _nj = _neighbor_class(t, k, 1)
                if pc == "C" or nc == "C":
                    if ch == "." and in_abbrev(k):
                        continue
                    # 序号/编号/日期句点豁免（2026-08-27 裁定）：「1.公司」「2.如」「2024.6.30」
                    if ch == "." and k > 0 and t[k - 1].isdigit():
                        continue
                    add(kind, i, info, t, k, k + 1,
                        f"中文语境使用半角标点「{ch}」",
                        f"改为全角「{HALF_FULL_MAP.get(ch, '对应全角标点')}」")
            # 2026-08-27 裁定：英英之间全角标点不再报——投行文件中文阅读习惯下
            # （如「CPU，GPU」并列、简称「（GPT）」括注）全角即为规范；仅成段英文例外

        # 提示级：中文语境直排双引号
        dq_hits = [m.start() for m in re.finditer(r'"', t)]
        cn_near = any((_char_class(t[pos - 1]) == "C") if pos > 0 else False
                      for pos in dq_hits)
        if dq_hits and cn_near:
            add(kind, i, info, t, dq_hits[0], dq_hits[0] + 1,
                f"中文语境使用直排引号 \" （共 {len(dq_hits)} 处）",
                "建议改用「」或全角弯引号“”", "LOW")
    return issues

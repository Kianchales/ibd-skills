# -*- coding: utf-8 -*-
"""生成 方法论调用索引.md（问询问题类型 → 方法论条目映射；读稳定入口 通用方法论_最终版.md）

用法：
    python gen_index.py [--methods-root <库根目录>]

参数：
    --methods-root  方法论库根目录（默认 $METHODS_ROOT，或脚本上级目录）
"""
import argparse, io, re, os
from pathlib import Path

_ap = argparse.ArgumentParser(description="生成方法论调用索引.md")
_ap.add_argument("--methods-root", default=os.environ.get("METHODS_ROOT", ""),
                 help="方法论库根目录（默认 $METHODS_ROOT，或脚本上级目录）")
_args = _ap.parse_args()
_ROOT = Path(_args.methods_root) if _args.methods_root else Path(__file__).resolve().parents[1]
METHODS = str(_ROOT / "methods")


def latest_v26():
    # 稳定入口：通用方法论_最终版.md（历史 vN 版已归档 methods/archive/）
    return os.path.join(METHODS, "通用方法论_最终版.md")


V26 = latest_v26()
PARSED = os.path.join(str(_ROOT / "scripts"), "parsed_titles.txt")
OUT = os.path.join(METHODS, "方法论调用索引.md")

# ---------- 问题域定义（审核问询常见问题域，Q 编号） ----------
# (编号, 问题域名, [关键词])
DOMAINS = [
    ("Q1", "收入确认时点与模式", ["收入确认", "双轨", "对账", "寄售", "签收", "验收", "履约义务", "暂定价", "保护性条款", "总额法", "净额法", "买断", "妥投", "三时点", "四模式", "五迹象", "预计负债", "合同变更"]),
    ("Q2", "收入真实性核查（境外/第三方/对账/经销穿透）", ["境外收入", "四匹配", "三勾稽", "海关", "报关", "退税", "第三方回款", "经销", "贸易商", "走访", "函证", "进销存", "穿透", "外销", "境外", "电函", "终端"]),
    ("Q3", "毛利率与盈利质量", ["毛利率", "毛利", "单位毛利", "金属价", "量价", "贡献矩阵", "剔除还原", "连环替代", "负毛利", "EBITDA", "价差", "盈利拐点"]),
    ("Q4", "成本与采购（原材料/客供料/副产品/返利折让）", ["原材料", "采购价", "领用成本", "副产品", "客供料", "返利", "折让", "废料", "价格传导", "采购", "在途物资"]),
    ("Q5", "存货", ["存货", "跌价", "周转率", "库龄", "在途", "发出商品"]),
    ("Q6", "应收账款/票据/保理", ["应收", "保理", "票据", "供应链金融", "6+9", "承兑", "贴现", "坏账"]),
    ("Q7", "经营现金流", ["现金流", "现金", "票据还原"]),
    ("Q8", "研发（费用率/资本化/样机）", ["研发", "样机", "资本化", "立项", "解释15"]),
    ("Q9", "产能与产能利用率", ["产能", "利用率", "瓶颈", "约当", "产能口径", "爬坡", "良率"]),
    ("Q10", "募投项目（必要性/消化/测算/环评用地）", ["募投", "补流", "折旧", "代建", "产能消化", "环评", "用地", "募投产能", "扩建", "达产", "单位产能投入"]),
    ("Q11", "客户集中度与稳定性", ["客户集中", "客户稳定", "前五大", "大客户", "战略客户", "供货份额", "合作年限"]),
    ("Q12", "关联交易", ["关联", "公允性", "资金占用", "关联方"]),
    ("Q13", "对赌与特殊投资条款", ["对赌", "特殊权利", "附恢复", "自始无效", "回购", "投资条款", "业绩承诺"]),
    ("Q14", "实控人/控制权", ["实控人", "控制权", "无实控人", "共同实控", "特别表决权", "僵局", "低持股", "一致行动", "董事会"]),
    ("Q15", "股权代持/出资/历史沿革", ["股权代持", "代持", "出资", "历史", "股改", "国有股东", "分拆", "增资", "减资", "转让"]),
    ("Q16", "股份支付/员工持股/股权激励", ["股份支付", "员工持股", "股权激励", "员工股权", "服务期"]),
    ("Q17", "同业竞争", ["同业竞争", "竞争"]),
    ("Q18", "境外合规/ODI/红筹/出口管制", ["ODI", "红筹", "境外", "出口管制", "备案", "架构", "外汇", "外商投资"]),
    ("Q19", "环保/安全/处罚/违建", ["环保", "环评", "排污", "处罚", "违建", "无证房产", "安全", "消防", "超环评"]),
    ("Q20", "劳动用工/社保公积金/劳务派遣/竞业", ["社保", "公积金", "劳务派遣", "竞业", "劳动", "用工"]),
    ("Q21", "行业定位/市场空间/市占率/竞争格局", ["行业分类", "市场空间", "市占率", "市场规模", "竞争格局", "行业定位", "产业链", "市场地位", "测算"]),
    ("Q22", "技术先进性/国产替代/技术路线", ["技术先进", "技术对标", "国产替代", "技术路线", "指令集", "国产", "替代", "认证", "定点", "参数", "壁垒", "唯一", "技术许可", "IP 授权"]),
    ("Q23", "信息披露豁免/军工/保密", ["军工", "保密", "豁免", "军品", "披露豁免"]),
    ("Q24", "业绩波动/未盈利/期后业绩/扭亏", ["业绩", "扭亏", "未盈利", "盈亏平衡", "期后", "非经常性", "汇兑", "预测", "下滑", "增长", "重资产亏损", "财务画像"]),
    ("Q25", "再申报/前次撤回", ["再申报", "前次", "撤回", "中介机构费用", "申报"]),
    ("Q26", "经营模式（电商/经销/ODM/OBM/双主业）", ["电商", "B2C", "经销", "ODM", "OBM", "双主业", "跨境", "销售模式", "寄售", "贸易商", "经营模式五要素", "消费者价值"]),
    ("Q27", "差错更正/内控/治理", ["差错", "更正", "内控", "治理", "监事会", "审计委员会", "整改"]),
    ("Q28", "写作结构与投行语言", ["句式", "结构", "披露", "问询回复", "版式", "核查程序", "语言", "话术", "模板", "范式", "维度", "模块", "三段式", "数据交叉", "条款锚定", "画像", "定位话术", "口径注记"]),
]

# 补充规则：标题关键词 → 附加 Q（处理通用词无法覆盖的）
EXTRA_Q = [
    ("税收优惠", ["Q24"]),
    ("销售费用率", ["Q3"]),
    ("社保公积金", ["Q20"]),
    ("劳务派遣", ["Q20"]),
    ("竞业", ["Q20"]),
    ("员工持股", ["Q16"]),
    ("股权激励", ["Q16"]),
    ("无证房产", ["Q19"]),
    ("境外子公司", ["Q18"]),
    ("退换货率", ["Q26"]),
    ("战略收缩", ["Q24"]),
    ("在建工程转固", ["Q10", "Q24"]),
    ("同源工艺", ["Q21"]),
    ("行业地位", ["Q21"]),
    ("技术许可", ["Q22"]),
    ("IP 授权", ["Q22"]),
]

def classify(title):
    hits = set()
    for qid, name, kws in DOMAINS:
        for kw in kws:
            if kw in title:
                hits.add(qid)
                break
    for kw, addqs in EXTRA_Q:
        if kw in title:
            for q in addqs:
                hits.add(q)
    return hits

# 读取解析结果（5 列：域文件/编号/标题/类型/行号）
entries = []
with io.open(PARSED, "r", encoding="utf-8") as f:
    for ln in f.read().splitlines()[1:]:
        p = ln.split("\t")
        if len(p) >= 4:
            entries.append({"dom": p[0], "eid": p[1], "title": p[2], "kind": p[3]})

# 主题标签 = 标题冒号/引号前核心短语，太长则截断
def theme(title):
    t = re.sub(r"【[^】]*】", "", title).strip()
    t = re.split(r"[：:｜]", t)[0].strip()
    t = t.strip("「」\"'")
    if len(t) > 28:
        t = t[:28]
    return t

lines_out = []
lines_out.append("# 方法论调用索引（问询问题类型 → 方法论条目）")
lines_out.append("")
lines_out.append("> 生成：脚本化（P0 拆分版）｜ 解析全部域文件条目（财务/法律/行业/写作/W 系列）｜ 供写反馈回复「问题拆解→查条目」与 G4 门禁引用清单使用；条目行号见 `methods/方法论_条目标题目录.md`（含域文件+行号）。")
lines_out.append("> **使用法**：拿到问询函问题 → 按「问题域速查表」找到 Q 编号 → 去「全量映射表」查该 Q 下所有条目 → 按条目标题目录（域文件+行号）用 Read offset/limit 定向读对应条目/行业合并版/单案文件。")
lines_out.append("")

# ============ 一、速查表（问题域 → 推荐条目） ============
lines_out.append("## 一、常见问询问题类型 → 推荐条目（速查表）")
lines_out.append("")
lines_out.append("| Q | 问询问题类型 | 核心推荐条目（域文件编号，按优先级） |")
lines_out.append("|---|-------------|-----------------------------------|")

# 规则：对每个 Q，从 entries 中找出命中该 Q 的条目，按"财务>法律>行业>写作"排序取前若干，并优先保留含核心关键词的
def pick(entries, qid, maxn=12):
    matched = [e for e in entries if qid in classify(e["title"])]
    # 排序：财务/法律/行业/写作 优先于 W；同域保持原顺序
    order = {"通用方法论_财务域.md": 0, "通用方法论_法律域.md": 1, "通用方法论_行业域.md": 2, "通用方法论_写作域.md": 3}
    def key(e):
        base = order.get(e["dom"], 4)
        return (base,)
    matched.sort(key=key)
    # 剔除 W 条目（速查表给方法论主体条目，W 由全量表覆盖）
    core = [e for e in matched if e["kind"] == "HEAD"]
    wd = [e for e in matched if e["kind"] in ("WD", "WD_LIST")]
    picked = core[:maxn]
    return picked, wd

def prefixed(e):
    if "-" in e["eid"]:
        return e["eid"]  # v37 身份编号（F-010001 / WL-010001）已含前缀，直接返回
    if "财务" in e["dom"]: return "财务" + e["eid"]
    if "法律" in e["dom"]: return "法律" + e["eid"]
    if "行业" in e["dom"]: return "行业" + e["eid"]
    if "写作" in e["dom"]: return "写作" + e["eid"]
    return e["eid"]  # W 系列保持原编号

for qid, name, kws in DOMAINS:
    picked, wd = pick(entries, qid)
    ids = "、".join([prefixed(e) for e in picked])
    wdids = "、".join([e["eid"] for e in wd[:6]])
    if wdids:
        ids += "（W：" + wdids + "…）"
    lines_out.append("| %s | %s | %s |" % (qid, name, ids if ids else "待归类"))
lines_out.append("")

# ============ 二、全量条目映射表 ============
lines_out.append("## 二、全量条目映射表")
lines_out.append("")
lines_out.append("> 条目编号 | 主题标签 | 可答复问询问题类型（Q） | 域文件位置。**宁全勿漏**；未能归入现有问题域的标「待归类」。")
lines_out.append("")

def chap_label(dom):
    """域文件名 → 显示标签"""
    return dom.replace("通用方法论_", "").replace(".md", "").replace("投行语言专项_", "投行语言专项·")

# 先 HEAD 后 WD/WD_LIST，按域文件
seen = set()
def add_row(e):
    key = (e["dom"], e["eid"]) if e["kind"] == "HEAD" else e["eid"]
    if key in seen:
        return
    seen.add(key)
    qs = classify(e["title"])
    if not qs:
        qs_str = "待归类"
    else:
        qs_str = "、".join(sorted(qs))
    theme_str = theme(e["title"])
    lines_out.append("| %s | %s | %s | %s |" % (e["eid"], theme_str, qs_str, chap_label(e["dom"])))

# HEAD 按域文件顺序，W 条目单独一节
head_entries = [e for e in entries if e["kind"] == "HEAD"]
wd_entries = [e for e in entries if e["kind"] in ("WD", "WD_LIST")]

for e in head_entries:
    add_row(e)

lines_out.append("### 附：W 系列（投行语言句式）")
lines_out.append("")
lines_out.append("| 条目编号 | 核心句式要点（简） | 可答复问询问题类型（Q） | 域文件位置 |")
lines_out.append("|---|---|---|---|")
for e in wd_entries:
    qs = classify(e["title"])
    qs_str = "、".join(sorted(qs)) if qs else "待归类"
    lines_out.append("| %s | %s | %s | 投行语言专项·W系列 |" % (e["eid"], e["title"][:60], qs_str))

# ============ 三、跨域桥接速查表（A-Mem 语义链接，2026-09-01 接入） ============
lines_out.append("")
lines_out.append("## 三、跨域桥接速查表（Q → 各域代表条目）")
lines_out.append("")
lines_out.append("> 同 Q 条目散布四域 + W 系列：查完本域条目后按此表跨域跳转——「写作范式 ↔ 财务/法律/行业」桥接（A-Mem 语义链接，2026-09-01 脚本化）。代表条目取自速查表核心推荐（每域前 3），完整条目见全量映射表。")
lines_out.append("")
lines_out.append("| Q | 问询问题类型 | 财务域 | 法律域 | 行业域 | 写作域 | W 系列 |")
lines_out.append("|---|---|---|---|---|---|---|")
for qid, name, kws in DOMAINS:
    picked, wd = pick(entries, qid)
    groups = {"财务域": [], "法律域": [], "行业域": [], "写作域": []}
    for e in picked:
        key = chap_label(e["dom"])
        if key in groups:
            groups[key].append(prefixed(e))
    cells = ["、".join(groups[k][:3]) if groups[k] else "—" for k in ["财务域", "法律域", "行业域", "写作域"]]
    cells.append("、".join([e["eid"] for e in wd[:3]]) if wd else "—")
    lines_out.append("| %s | %s | %s |" % (qid, name, " | ".join(cells)))

with io.open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines_out) + "\n")

print("OUTPUT:", OUT)
print("HEAD rows:", len(head_entries), "WD rows:", len(wd_entries))
print("DONE")

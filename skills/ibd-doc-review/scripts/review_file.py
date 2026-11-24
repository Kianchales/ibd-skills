#!/usr/bin/env python3
"""review_file.py — 单文件复核编排器（**批次对用户不可见**）

用户契约
--------
用户只提供**一个文件**，不需要分批、不认识批次边界、不需要指定批次：
    python scripts/review_file.py --input <文件.docx>

批次是**内部调度实现**：编排器按容量自动切批、逐批取用、断点续跑、最后合并成
一份连续结果。交付物（报告／批注）里**不出现批次号**——读者看到的是"这份文件核完了"。

为什么要有这一层
----------------
此前批次是**外露的**：agent 手工一批批做、还向用户汇报"共 9 批、先做第 1 批"。
后果有三个：① 用户被迫理解批次边界；② 中途停下来就成了"半套"，且看不出缺哪批；
③ 换一轮重跑，没人能证明"这次真的把 9 批都过了一遍"。

本编排器把三件事制度化：**顺序**（按文档序合并）、**一致性**（全局连续编号、去重）、
**错误恢复**（状态落盘、可续跑、未完成不许出报告）。

工作流（内部）
--------------
    --status          看进度（哪批 done／pending）
    --begin           取下一批的正文，交给人/模型读
    --commit N -f x   登记第 N 批的发现（幂等：重复提交覆盖，不重复计数）
    --finish          校验**全部批 done** → 按文档序合并、全局编号 → 输出单一结果

退出码：0 正常／2 参数或输入错误／3 **仍有未完成批次**（拒绝出结论）

批次与编号纪律
--------------
- 合并顺序＝文档顺序（batch_index, item_index），不按完成先后
- 全局编号 `F-01…` 按合并后的顺序**连续**分配，与批次无关
- 同一 (anchor, title) 去重（不同批次复述同一问题只留一条，取先出现者）
"""
import argparse
import json
import os
import re
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan_review as pr      # noqa: E402  复用其分母与切批逻辑
import docxio                 # noqa: E402
import runlog                 # noqa: E402  运行指纹（_run.json）

STATE_NAME = ".review_state.json"
STATE_VERSION = 2

# 四档深度：每档包含前一档。原「档位 × 颗粒」两轴合并——
# 六个组合里 L1+逐字（快扫不逐字）、L3+逐项（不逐字却出专业意见）本就无效，只剩四档。
LEVELS = {
    "L1": {"name": "L1 快扫", "cap": (60, 20),
           "desc": "只做表面项，不做勾稽与台账"},
    "L2": {"name": "L2 标准", "cap": (60, 20),
           "desc": "全项核对，不出会计专业判断"},
    "L3": {"name": "L3 通读", "cap": (30, 10),
           "desc": "同 L2，且逐字通读（批更短，每句都看）"},
    "L4": {"name": "L4 深核", "cap": (30, 10),
           "desc": "同 L3，另加财务与法律专业判断"},
}          # 结构变更即升；旧状态缺 `_items` 会让 --begin 无内容可吐
DEFAULT_CAP_P, DEFAULT_CAP_T = 60, 20      # 单批正文段/表上限（内部默认，不暴露给用户）


# ---------------------------------------------------------------- 状态

def out_dir_of(path, out=None):
    """状态与中间件落在**内部目录**（`<文件目录>/<文件名>_复核/`），不进交付面。"""
    if out:
        return out
    base = os.path.splitext(os.path.basename(path))[0]
    return os.path.join(os.path.dirname(os.path.abspath(path)), base + "_复核")


def state_path(d):
    return os.path.join(d, STATE_NAME)


def load_state(d):
    p = state_path(d)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        st = json.load(f)
    if st.get("v") != STATE_VERSION:
        # 旧结构（如缺 _items）：重建，避免 --begin 空转却看不出原因
        print(f"[WARN] 状态结构为 v{st.get('v')}，当前 v{STATE_VERSION}——重建（进度清零）", file=sys.stderr)
        return None
    return st


def save_state(d, st):
    os.makedirs(d, exist_ok=True)
    tmp = state_path(d) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)
    os.replace(tmp, state_path(d))       # 原子写：中断不留半截状态


def init_state(path, cap_p=DEFAULT_CAP_P, cap_t=DEFAULT_CAP_T):
    """定分母 → 切批 → 落状态。用户不需要知道这一步，也不该看到批次数。"""
    units, stats = pr.load_units(path)
    batches = pr.build_batches(units, cap_p, cap_t)
    out = []
    note = ""
    tid = 0
    for i, b in enumerate(batches, 1):
        # 批内条目＝**所有段落类**（正文/标题/短句），不只是"正文"。
        # 只给正文会漏掉标题序号问题（实测：某招股书 24 条 HIGH 全在标题段，批内看不到）。
        prose = [u for u in b["items"] if u["type"] not in ("表格", "单元格")]
        tables = [u for u in b["items"] if u["type"] == "表格"]
        tabs = []
        for _u in tables:
            if _u.get("type") == "表格":
                tid += 1
                tabs.append({"id": "TAB%03d" % tid, "rows": 0, "cols": 0, "head": []})
        out.append({
            "i": i,
            "name": b["name"],
            "n_prose": len([u for u in prose if u["type"] == "正文"]),
            "n_tables": len(tables),
            "status": "pending",
            "findings": [],
            "_texts": [u["text"] for u in prose],   # 兼容旧结构
            "_items": [{"p": None, "kind": u["type"], "text": u["text"]} for u in prose],
            "_tables": tabs,
        })
    return {
        "v": STATE_VERSION,
        "financials": None,          # 未提供即单件复核（降级），不自动去别处找

        "input": os.path.abspath(path),
        "stats": stats,
        "cap": [cap_p, cap_t],
        "batches": out,
    }


# ---------------------------------------------------------------- 命令

def extract_artifacts(path, d):
    """把**全文 / 段表 / 表表**落盘，供逐段复核与回溯定位。

    为什么由编排器做这件事：此前这些中间件要 agent 自己写脚本抽取；而自建脚本一旦开始，
    整轮就会走成"自建流程"（不跑检查、不留指纹）。**入口必须比自建更省事**，否则没人用。
    编号口径：正文段 `P####`（按文档顺序，不含表格单元格）、表格 `TAB###`。
    """
    bundle = docxio.open_docx(path)
    body = docxio.body_of(bundle)

    paras, tables, full = [], [], []
    pi = ti = 0

    def walk(node):
        nonlocal pi, ti
        for child in list(node):
            tag = child.tag
            if tag == docxio.W + "p":
                pi += 1
                st_ = docxio.style_of(child)
                txt = docxio.para_text(child)
                paras.append({"id": "P%04d" % pi, "style": st_, "text": txt})
                full.append("P%04d\t%s\t%s" % (pi, st_ or "-", txt))
            elif tag == docxio.W + "tbl":
                ti += 1
                rows = []
                for tr in child.findall(docxio.W + "tr"):
                    cells = ["".join(t.text or "" for t in tc.iter(docxio.W + "t"))
                             for tc in tr.findall(docxio.W + "tc")]
                    rows.append(cells)
                tables.append({"id": "TAB%03d" % ti, "rows": rows})
                full.append("TAB%03d\t%d 行 × %d 列" % (ti, len(rows), max((len(r) for r in rows), default=0)))
                for r in rows:
                    full.append("\t" + " | ".join(r))
            elif tag == docxio.W + "sdt":
                walk(child)          # 内容控件：进去继续

    walk(body)

    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "paras.json"), "w", encoding="utf-8") as f:
        json.dump(paras, f, ensure_ascii=False, indent=1)
    with open(os.path.join(d, "tables.json"), "w", encoding="utf-8") as f:
        json.dump(tables, f, ensure_ascii=False, indent=1)
    with open(os.path.join(d, "full.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(full))
    return {"paras": len(paras), "tables": len(tables), "lines": len(full)}


def write_scope(d, path, stats, n_batches, level="L2"):
    """生成声明单 `_scope.md`（覆盖方式＝全文逐段，分母自动填）。

    为什么由编排器生成：声明单此前要 agent 手写，**漏写就过不了 R5**；而分母/批数编排器本就有，
    没有理由让调用方再填一遍。
    """
    today = __import__("datetime").date.today().strftime("%Y%m%d")
    f = os.path.join(d, "%s_%s_v1_scope.md" % (os.path.splitext(os.path.basename(path))[0], today))
    if os.path.exists(f):
        return f
    levels_md = "".join(
        (("**%s** ← 本轮\n  %s\n" % (v["name"], v["desc"]))
         if k == level else ("%s：%s\n" % (v["name"], v["desc"])))
        for k, v in LEVELS.items()
    )
    head = (
        "【本轮检查项声明】对象：%s ｜ 深度：%s ｜ 覆盖方式：全文逐段 ｜ "
        "分母：总 %d 段（正文 %d／表 %d）\n\n"
        "**检查**：格式规范（12 项）｜数字勾稽（提供报表时）｜表述与事实（禁用词、标点用法）｜交付门禁\n"
        "**不查**：法律事项合规性｜行业数据外部溯源（无可研报告原件）"
        "｜底稿与函证（不在材料范围）\n"
        "**依据来源**：申报报表与附注｜复核判据表；缺「同类范例」「内部口径」可比对\n"
        "**交付前将跑**：check_runlog.py（流程合规）＋ review_report_to_xlsx.py（报告）\n\n"

    ) % (os.path.basename(path),
         LEVELS.get(level, LEVELS["L2"])["name"] + "｜" + LEVELS.get(level, LEVELS["L2"])["desc"],
         stats["总段"], stats["正文"], stats["表格"])
    body = head + "**深度档位（本轮使用的一档加粗）**\n\n" + levels_md
    with open(f, "w", encoding="utf-8") as fh:
        fh.write(body)
    return f


def run_checks(path, d, financials=None, restr=None, accrued=None, level="L2"):
    """起子进程跑本包检查：产物与指纹都落在**同一目录**。

    ⚠️ 必须把 `IBD_RUNLOG_DIR` 传给子进程：子进程默认按"源文件同级 `<名>_复核/`"找指纹目录，
    一旦用了 `--out-dir` 就找不到，于是"真跑了检查"却"没留下指纹"——把合规执行误判成没跑。
    """
    here = os.path.dirname(os.path.abspath(__file__))
    env = dict(os.environ, IBD_RUNLOG_DIR=os.path.abspath(d))
    out = {}

    missing = []      # 声明要做、但缺材料做不了的检查——不许只在 stderr 一闪而过
    if level == "L4":
        missing.append({"check": "会计处理是否恰当", "need": "财务专业复核结论",
                        "effect": "本轮未做会计专业判断（声明 L4 时此项目必需）"})
        missing.append({"check": "法律事项合规性", "need": "法律专业复核结论",
                        "effect": "本轮未做法律事项判断（声明 L4 时此项目必需）"})
    if not financials:
        missing.append({"check": "招股书与财务报表的数字勾稽", "need": "申报财务报表（xlsx 文件）",
                        "effect": "招股书数字与报表是否一致，本轮未核（补齐可升级为全套复核）"})
    md = os.path.join(d, "format_check.md")
    js = os.path.join(d, "format_check.json")
    r = subprocess.run([sys.executable, os.path.join(here, "check_content.py"),
                        "--input", path, "--output", md, "--json"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env)
    with open(js, "w", encoding="utf-8") as f:
        f.write(r.stdout or "{}")
    out["check_content"] = r.returncode

    if financials:
        js2 = os.path.join(d, "checks.json")
        extra = (["--restr", restr] if restr else []) + (["--accrued", accrued] if accrued else [])
        if not restr:
            missing.append({"check": "C-Q 第⑥式（货币资金差额 vs 附注受限）",
                            "need": "附注「受限资金明细」各期合计（--restr）",
                            "effect": "受限资金口径未核，差额无处比对"})
        r2 = subprocess.run([sys.executable, os.path.join(here, "check_cq.py"),
                             "--xlsx", financials, "--json"] + extra,
                            capture_output=True, text=True, encoding="utf-8", errors="replace",
                            env=env)
        with open(js2, "w", encoding="utf-8") as f:
            f.write(r2.stdout or "{}")
        out["check_cq"] = r2.returncode
    with open(os.path.join(d, "pending_inputs.json"), "w", encoding="utf-8") as f:
        json.dump(missing, f, ensure_ascii=False, indent=1)
    if missing:
        print(f"  待补材料 {len(missing)} 项（已记入 pending_inputs.json，将列入报告行动项）：",
              file=sys.stderr)
        for m in missing:
            print(f"    · {m['check']} ← 需 {m['need']}", file=sys.stderr)
    return out


def cmd_prepare(path, d, financials=None, restr=None, accrued=None, level="L2"):
    print(f"准备中：{os.path.basename(path)}")
    # 旧一轮的产物（有完成批但无节级回执，或状态版本过旧）自动归档重建：
    # 用户只说"复核 X"时不该被"25 批无回执"卡住。
    old = load_state(d)
    if old and any(b.get("status") == "done" and not b.get("receipt")
                   for b in old.get("batches", [])):
        import time as _t
        arch = d.rstrip("/\\") + "_archive_" + _t.strftime("%Y%m%d_%H%M")
        try:
            os.rename(d, arch)
            print(f"  · 旧一轮无回执，已归档至 {os.path.basename(arch)}（不阻塞本轮）")
        except OSError:
            pass
    cap = LEVELS.get(level, LEVELS["L2"])["cap"]
    st = load_state(d) or init_state(path, *cap)
    st["financials"] = os.path.abspath(financials) if financials else None
    st["level"] = level
    save_state(d, st)
    if not financials:
        print("  · 本轮为**单件复核**：只核这一份文档；未提供申报报表，跨文档勾稽不做")
    n = extract_artifacts(path, d)
    # 把表的真实行列回填到批摘要（--begin 用），免得只显示 0×0
    try:
        dims = {}
        with open(os.path.join(d, "tables.json"), encoding="utf-8") as f:
            for t in json.load(f):
                rows = t.get("rows") or []
                dims[t["id"]] = (len(rows), max((len(r) for r in rows), default=0),
                                 (rows[0] if rows else []))
        for b in st["batches"]:
            for tb in b.get("_tables") or []:
                if tb["id"] in dims:
                    tb["rows"], tb["cols"], head = dims[tb["id"]]
                    tb["head"] = [h for h in head if h][:4]
        save_state(d, st)
    except (OSError, ValueError):
        pass
    sf = write_scope(d, path, st["stats"], len(st["batches"]), level)
    print(f"  声明单：{os.path.basename(sf)}（覆盖方式＝全文逐段，分母已填）")
    print(f"  已提取：段落 {n['paras']}／表格 {n['tables']}（full.txt {n['lines']} 行）")
    rc = run_checks(path, d, financials, restr, accrued, level)
    print(f"  已跑检查：check_content rc={rc.get('check_content')}"
          + (f"／check_cq rc={rc.get('check_cq')}" if "check_cq" in rc else "（未给 --financials，跳过勾稽）"))
    runlog.log("review_file", ["--prepare"], rc=0, out_dir=d,
               extra={"step": "prepare", "paras": n["paras"], "tables": n["tables"],
                      "checks": rc})
    print(f"  中间件目录：{d}")
    print("  下一步：--begin 取正文 → 逐条读 → --commit 登记 → --finish 出结果")
    return 0


def cmd_status(st, verbose=False):
    done = [b for b in st["batches"] if b["status"] == "done"]
    pend = [b for b in st["batches"] if b["status"] != "done"]
    total = len(st["batches"])
    print(f"处理单元：{os.path.basename(st['input'])}｜内部批 {len(done)}/{total} 完成")
    print(f"分母：总 {st['stats']['总段']} 段（正文 {st['stats']['正文']}／表 {st['stats']['表格']}）")
    if pend:
        # **不列批次号**：批次是内部调度细节，列出来就等于把它推给读者。
        print(f"未完成：还有 {len(pend)} 个处理单元（内部细节，加速查看加 --verbose）")
        if verbose:
            print("  " + "、".join(f"#{b['i']}" for b in pend))
    else:
        print("全部批次已处理，可 --finish 出结果")
    return 0


def cmd_begin(st):
    """吐出下一批。这是**内部**取活接口，不是用户动作。

    每行带 `P####`（与 full.txt / 报告定位一致）；表格只给**摘要与 TAB 编号**，
    内容在 `tables.json`——避免把上万个单元格倒进上下文。
    """
    for b in st["batches"]:
        if b["status"] != "done":
            print(f"### 第 {b['i']}/{len(st['batches'])} 批｜{b['name']}"
                  f"｜正文 {b['n_prose']} 段／表 {b['n_tables']}")
            for item in b.get("_items") or [{"p": None, "text": t} for t in b["_texts"]]:
                kind = item.get("kind") or ""
                mark = "〔%s〕" % kind if kind and kind != "正文" else ""
                print(f"{mark}{item['text']}")
            for tb in b.get("_tables") or []:
                print(f"[{tb['id']}] 表格 {tb['rows']} 行 × {tb['cols']} 列"
                      f"（内容见 tables.json；表头：{' | '.join(tb.get('head', []))[:120]}）")
            print("\n（定位：全文按 P0001… 顺序见 full.txt；表格内容见 tables.json。"
                  "读完后用 --commit 登记本批）")
            return 0
    print("全部批次已处理")
    return 0


def cmd_commit(st, idx, findings_path):
    b = next((x for x in st["batches"] if x["i"] == idx), None)
    if b is None:
        print(f"[ERROR] 无第 {idx} 批", file=sys.stderr)
        return 2
    items, receipt = [], None
    if findings_path:
        with open(findings_path, encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, dict):
            items = payload.get("findings") or []
            receipt = payload.get("receipt")
        else:
            items = payload
        if not isinstance(items, list):
            print("[ERROR] findings 应为数组（或 {findings, receipt} 对象）", file=sys.stderr)
            return 2
        # 节级回执：把"这一节读了没有"变成必填表态，而不是靠"没发现问题"含糊过去
        SIX = ("self", "cross_prev", "cross_next", "disclose", "caliber", "wording")
        if not isinstance(receipt, dict):
            print("[ERROR] 本批缺 receipt（节级六问回执）——只交问题清单不算读过：", file=sys.stderr)
            print("  需 {\"findings\": [...], \"receipt\": {六问}}；六问见 references/fuhe-charter.md §八",
                  file=sys.stderr)
            return 2
        miss = [k for k in SIX if not str(receipt.get(k, "")).strip()]
        if miss:
            print(f"[ERROR] receipt 缺 {len(miss)} 项回答：{'、'.join(miss)}（无异常也须写\"未见异常\"）",
                  file=sys.stderr)
            return 2
        # 当场校验：缺必填字段就拒收（此前要等到 --finish 才发现，且不说是哪一条）
        bad = []
        for k, it in enumerate(items, 1):
            if not isinstance(it, dict):
                bad.append(f"第{k}条不是对象")
                continue
            if not it.get("title"):
                bad.append(f"第{k}条缺 title（问题标题）")
            if not (it.get("advice") or it.get("rev")):
                bad.append(f"第{k}条缺 advice（修改建议）或 rev（定稿文本）")
            if not it.get("anchor"):
                bad.append(f"第{k}条缺 anchor（原文片段，报告定位用）")
        if bad:
            print(f"[ERROR] 本批发现未通过校验（{len(bad)} 项）——未登记：", file=sys.stderr)
            for x in bad:
                print(f"  - {x}", file=sys.stderr)
            print("  字段口径见 references/pipeline.md §五", file=sys.stderr)
            return 2
    b["findings"] = items
    b["receipt"] = receipt or {}
    b["status"] = "done"
    b.pop("_texts", None)              # 已处理完，正文不必再留（省体积）
    return 0


def merge(st):
    """按**文档顺序**合并并全局编号；同 (anchor,title) 去重，保留先出现者。"""
    seq = []
    for b in sorted(st["batches"], key=lambda x: x["i"]):
        for k, f in enumerate(b["findings"], 1):
            seq.append((b["i"], k, f))
    seen, merged = set(), []
    for bi, ik, f in seq:
        # 去重键须含**位置**：同一句话在两处重复（如重复标题 #807/#808）是两条问题，
        # 只按 (anchor,title) 会把它们并成一条，导致"查出 107 条、报告只剩 62 条"。
        key = (f.get("anchor", "").strip(), f.get("title", "").strip(),
               str(f.get("line", "")).strip())
        if key in seen:
            continue
        seen.add(key)
        g = dict(f)
        g["id"] = "F-%02d" % (len(merged) + 1)     # 全局连续编号，与批次无关
        g["_batch"] = bi                            # 仅调试用，落盘前删
        merged.append(g)
    return merged


NATURE_BY_TYPE = {
    "数据不一致": "数据不一致", "表述不一致": "表述不一致", "格式规范": "格式规范",
    "事实存疑": "事实存疑", "自身逻辑": "自身逻辑",
}


def to_issues(merged):
    """把内部发现转成报告清单（`problems.schema` 口径）。

    报告要的是 `code + 序号`／`nature`／`title`／`advice`；内部只用 `F-01` 全局编号。
    这里做一次**显式映射**，缺必填字段的条目**不静默丢**——计数后回报，让调用方补齐。
    """
    issues, skipped = [], 0
    for i, g in enumerate(merged, 1):
        if not g.get("title") or not (g.get("advice") or g.get("rev")):
            skipped += 1
            continue
        nature = g.get("nature") or NATURE_BY_TYPE.get(g.get("type", ""), "格式规范")
        issues.append({
            "code": g.get("code") or "J",
            "id": g.get("code", "J") + "-%02d" % i,
            "type": g.get("type") or "格式规范",
            "sev": g.get("sev") or "中",
            "nature": nature,
            "line": g.get("line", ""),
            "anchor": g.get("anchor", ""),
            "title": g["title"],
            "desc": g.get("desc", ""),
            "advice": g.get("advice") or g.get("rev", ""),
            "author": g.get("author") or "复核人",
        })
    return issues, skipped


B_ITEMS = ["每个数字说得清", "数据类毛病", "论证类毛病", "表述类毛病",
           "编造类毛病", "交稿前自检 10 条", "质量自评打分", "数字前后对得上",
           "书名号内文件/法规名称"]
CQ_ITEMS = ["资产＝负债＋所有者权益", "利润表净利润＝净利润（归母＋少数）",
            "现金流量表期末现金＝资产负债表货币资金", "表内合计与小计", "跨期衔接",
            "货币资金差额 vs 附注受限"]
LEVEL_DOMAINS = {
    "L1": [("A", 4), ("B", 1)],
    "L2": [("A", 12), ("B", 8), ("C-Q", 6), ("C-D", 1)],
    "L3": [("A", 12), ("B", 8), ("C-Q", 6), ("C-D", 1)],
    "L4": [("A", 12), ("B", 8), ("C-Q", 6), ("C-D", 1), ("C-P", 16), ("D", 22)],
}


def _decl_tail(scope):
    """从声明单里只取「不查」「依据来源」两行——检查项由「复核范围」节表达，不重复。"""
    keep = []
    for ln in scope.splitlines():
        t = ln.replace("**", "").strip()
        if t.startswith("不查") or t.startswith("依据来源"):
            keep.append(t)
    return keep or None


def domain_lines(level, has_fin):
    """返回 (每域一行清单, 附注)。附注写"哪一项本轮没做、为什么"——单独成行，不塞在域行尾。"""

    """按本轮档位，列出**查了哪些域、各域包含什么**——报告读者不看 skill 文档也能懂。"""
    try:
        import check_content as _cc
        a_items = [c["name"].split("（")[0] for c in _cc.CHECK_REGISTRY]
    except Exception:                      # noqa: BLE001
        a_items = []
    pool = {"A": ("格式规范", a_items), "B": ("表达与事实", B_ITEMS),
            "C-Q": ("数值正确性", CQ_ITEMS), "C-D": ("逐数台账", ["每个数字都登记在案"]),
            "C-P": ("财务专业判断", ["16 维会计处理判断（由 ibd-finance-review 承载）"]),
            "D": ("法律惯例对照", ["22 项（由 ibd-legal-review 承载）"])}
    out = []
    note = ""
    for code, n in LEVEL_DOMAINS.get(level, LEVEL_DOMAINS["L2"]):
        name, items = pool.get(code, (code, []))
        items = items[:n]
        out.append(f"{code} {name}（{len(items)} 项 · " + "、".join(items) + "）")
        if code == "C-Q" and not has_fin:
            note = "注：C-Q 数值勾稽本轮未做——未提供申报财务报表。"
    return out, note


def check_count():
    """机检项数随注册表走，不写死在文案里（加一项检查，报告自动跟上）。"""
    try:
        from check_content import CHECK_REGISTRY as reg
        return len(reg)
    except Exception:             # noqa: BLE001
        return 13


def build_meta(st, d, n_findings):
    """自动构造报告 meta：报告是独立流转件，封面不能留"—"。

    声明（覆盖方式/不查项）直接取声明单正文 → 报告头与声明单**首尾一致**（delivery §八纪律）。
    """
    path = st["input"]
    try:
        md5 = __import__("hashlib").md5(open(path, "rb").read()).hexdigest()[:8]
    except OSError:
        md5 = "?"
    stats = st["stats"]
    scope = ""
    for fn in sorted(os.listdir(d)):
        if fn.endswith("_scope.md"):
            scope = open(os.path.join(d, fn), encoding="utf-8").read()
            break
    tabs = sum(b.get("n_tables", 0) for b in st["batches"])
    segs = sum(len(b.get("_items") or []) for b in st["batches"])
    return {
        "subject": f"{os.path.basename(path)}（{stats['总段']} 段／正文 {stats['正文']}／表 {stats['表格']}）",
        "subtitle": os.path.basename(path),
        "subject_short": f"{os.path.basename(path)}｜{stats['正文']} 段正文 ＋ {stats['表格']} 张表",
        "baseline": f"MD5 {md5}…｜段落 {segs}（含标题）｜表 {tabs}／{stats['表格']} 全判",
        "_read_n": sum(1 for b in st["batches"] if (b.get("receipt") or {}).get("read") == "yes"),
        "_read_t": len(st["batches"]),
        "method": (
            f"全文逐段 · 段落{sum(len(b.get('_items') or []) for b in st['batches'])}／"
            f"表{sum(b.get('n_tables', 0) for b in st['batches'])} 全过 · "
            f"机检{check_count()}项 · "
            + ("已勾稽报表 · " if st.get("financials") else "单件（未勾稽）· ")
            + f"实读 {sum(1 for b in st['batches'] if (b.get('receipt') or {}).get('read') == 'yes')}"
              f"/{len(st['batches'])} 节"
        ),
        "declaration": _decl_tail(scope) if scope else None,
        "quality_evidence": [
            f"已核对：全文 {segs} 段（含标题）与 {tabs} 张表逐段逐表过目，无跳段",
            "可回查：每条问题都附原文片段，按「位置」列可回原文核对",
        ],
        "has_annotation": False,
        "domain_lines": domain_lines(st.get("level") or "L2", bool(st.get("financials")))[0],
        "domain_note": domain_lines(st.get("level") or "L2", bool(st.get("financials")))[1],
        "depth_levels": [
            {"used": k == (st.get("level") or "L2"),
             "text": (("【本轮使用】" if k == (st.get("level") or "L2") else "    ")
                      + f"{v['name']}：{v['desc']}".replace("**", ""))}
            for k, v in LEVELS.items()
        ],
        "actions": [
            f"第{i}项 {m['check']}　缺：{m['need']}　影响：{m['effect']}"
            for i, m in enumerate(
                json.load(open(os.path.join(d, "pending_inputs.json"), encoding="utf-8"))
                if os.path.exists(os.path.join(d, "pending_inputs.json")) else [], 1)
        ] or None,
        "verified": [
            "全文各章均已逐段过目，无遗漏章节（每条问题的位置可在明细页回查）"
        ],
        "domain_scope": {"J": "格式规范（A 域 12 项）", "Z": "数据一致性（C-Q 勾稽）"},
        "conclusion_notes": [f"共 {n_findings} 条，每条均带原文片段，可按「位置」列回溯至原文件。"],
    }


def gen_report(issues_path, xlsx, runlog_path, meta_path=None):
    """返回 (rc, 实际产出路径)——被占用时路径会变成 *_新.xlsx，不能回报旧路径。"""
    """调 ibd-doc-annotate 的报告生成器（同仓相邻包）；找不到就明确降级，不假装成功。"""
    here = os.path.dirname(os.path.abspath(__file__))          # …/ibd-doc-review/scripts
    skills_root = os.path.dirname(os.path.dirname(here))       # …/（skills 根）
    base = os.environ.get("IBD_ANNOTATE_DIR") or os.path.join(skills_root, "ibd-doc-annotate")
    cand = os.path.join(base, "scripts", "review_report_to_xlsx.py")
    if not os.path.exists(cand):
        print("[WARN] 未找到 review_report_to_xlsx.py（ibd-doc-annotate 包缺失）——"
              "报告未生成，清单已保留", file=sys.stderr)
        return 4
    args = [sys.executable, cand, "--issues", issues_path, "--out", xlsx]
    if meta_path:
        args += ["--meta", meta_path]
    if os.path.exists(runlog_path):
        args += ["--runlog", runlog_path]
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0 and os.path.exists(xlsx):
        # 目标被 Excel 占用时另存一份，不静默失败
        import shutil
        alt = xlsx[:-5] + "_新.xlsx"
        args[args.index(xlsx)] = alt
        r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode == 0:
            print(f"[提示] 原文件被占用（Excel 打开中），已另存：{alt}", file=sys.stderr)
            return 0, alt
    if r.returncode != 0:
        print((r.stderr or r.stdout or "").strip()[:400], file=sys.stderr)
    return r.returncode, xlsx


def cmd_finish(st, out_path=None):
    no_rc = [b["i"] for b in st["batches"] if b["status"] == "done" and not b.get("receipt")]
    if no_rc:
        print(f"[ERROR] {len(no_rc)} 批无节级回执（{'、'.join(f'#{i}' for i in no_rc)}）——"
              f"无法证明这些节真读过；请重新 --commit 并带 receipt", file=sys.stderr)
        return 3
    pend = [b["i"] for b in st["batches"] if b["status"] != "done"]
    if pend:
        # **不静默出结论**：缺批就说缺批，且拒绝生成"看起来完整"的结果
        print(f"[ERROR] 仍有 {len(pend)} 批未处理（{'、'.join(f'#{i}' for i in pend)}）——"
              f"拒绝出结果，请 --begin 继续", file=sys.stderr)
        return 3
    merged = merge(st)
    for g in merged:
        g.pop("_batch", None)
    payload = {
        "input": st["input"],
        "stats": st["stats"],
        "n_findings": len(merged),
        "findings": merged,
    }
    _d = st.get("_dir") or "."
    out = out_path or os.path.join(_d, "findings.json")
    out = os.path.abspath(out)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    runlog.log("review_file", ["--finish"], rc=0, out_dir=st.get("_dir"),
               extra={"step": "finish", "n_findings": len(merged)})
    print(f"已合并 {len(merged)} 条｜输出 {out}")

    # ③ 转成报告清单并直接生成 xlsx（缺这一步，就得手工再造一份清单——正是"报告出不来"的主因）
    issues, skipped = to_issues(merged)
    ipath = os.path.join(os.path.dirname(out), "issues.json")
    with open(ipath, "w", encoding="utf-8") as f:
        json.dump(issues, f, ensure_ascii=False, indent=1)
    if skipped:
        print(f"  [WARN] {skipped} 条因缺 title/advice 未进报告（请补后再 --finish）",
              file=sys.stderr)
    xlsx = os.path.join(os.path.dirname(out), os.path.splitext(os.path.basename(st["input"]))[0]
                        + "_复核报告.xlsx")
    meta_path = os.path.join(os.path.dirname(out), "report_meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(build_meta(st, st.get("_dir") or ".", len(merged)), f, ensure_ascii=False, indent=1)
    rc, xlsx_real = gen_report(ipath, xlsx, os.path.join(st.get("_dir", ""), "_run.json"), meta_path)
    if rc == 0:
        n_tabs = sum(b.get("n_tables", 0) for b in st["batches"])
        n_seg = sum(len(b.get("_items") or []) for b in st["batches"])
        print(f"报告已生成：{xlsx_real}")
        print(f"覆盖：段落 {n_seg}／表 {n_tabs}｜发现 {len(merged)} 条"
              f"｜批 {len(st['batches'])}/{len(st['batches'])}")
        print("自检：check_runlog --file <源文件>（期望 PASS）")
    else:
        print(f"[WARN] 报告未生成（rc={rc}）——清单已保留：{ipath}", file=sys.stderr)
    print("（批次信息已丢弃：对读者而言这是**一份文件的一次完整处理**）")
    return 0


# ---------------------------------------------------------------- 入口

def main():
    ap = argparse.ArgumentParser(description="单文件复核编排器（批次内部化）")
    ap.add_argument("--input", required=True, help="被复核文件（**只需给文件**）")
    ap.add_argument("--out-dir", default=None, help="内部状态目录（默认 <文件>_复核/）")
    ap.add_argument("--prepare", action="store_true",
                    help="一次产出全部中间件（全文/段表/表表/格式核对/勾稽/指纹）——**开局就一条命令**")
    ap.add_argument("--restr", default=None,
                    help="附注「受限资金明细」各期合计（逗号分隔，按报表列序）——给了才做勾稽第⑥式")
    ap.add_argument("--accrued", default=None, help="附注应计利息各期金额（货币资金含应计利息时必传）")
    ap.add_argument("--financials", default=None,
                    help="--prepare 时顺带跑勾稽用的申报财务报表 xlsx（可选）")
    ap.add_argument("--level", choices=("L1", "L2", "L3", "L4"), default="L2",
                    help="深度档：L1 快扫 / L2 标准（默认）/ L3 通读（逐字）/ L4 深核")
    ap.add_argument("--depth", choices=("all", "read"), default=None,
                    help="旧参数别名：all=L2、read=L3（保留兼容）")
    ap.add_argument("--status", action="store_true", help="查看进度")
    ap.add_argument("--begin", action="store_true", help="取下一批（内部接口）")
    ap.add_argument("--commit", type=int, metavar="N", help="登记第 N 批（内部接口）")
    ap.add_argument("--findings", default=None, help="--commit 的发现清单 JSON")
    ap.add_argument("--finish", action="store_true", help="全部完成则合并出结果")
    ap.add_argument("--output", default=None, help="合并结果输出路径（默认 findings.json）")
    ap.add_argument("--verbose", action="store_true", help="显示内部批次号（调试用，勿对外）")
    ap.add_argument("--reset", action="store_true", help="丢弃状态重来（换基准文件时用）")
    a = ap.parse_args()

    if not os.path.isfile(a.input):
        print(f"[ERROR] 文件不存在：{a.input}", file=sys.stderr)
        return 2

    d = out_dir_of(a.input, a.out_dir)
    if a.prepare:
        if a.reset and os.path.isdir(d):
            # 纯净状态＝目录内清空（只删文件，不碰同级的 _archive_* 归档目录）
            n = 0
            skipped = []
            for fn in os.listdir(d):
                fp = os.path.join(d, fn)
                if not os.path.isfile(fp):
                    continue
                try:
                    os.remove(fp)
                    n += 1
                except OSError:              # 被 Excel 占用等：跳过，不中断整轮
                    skipped.append(fn)
            if skipped:
                print(f"  · 跳过被占用的 {len(skipped)} 个文件：{', '.join(skipped[:3])}", file=sys.stderr)
            if n:
                print(f"  · --reset：清空上轮产物 {n} 个文件", file=sys.stderr)
        lv = a.level
        if a.depth:                      # 旧参数映射
            lv = "L3" if a.depth == "read" else "L2"
        return cmd_prepare(a.input, d, a.financials, a.restr, a.accrued, lv)
    st = None if a.reset else load_state(d)
    if st is None:
        st = init_state(a.input)
        save_state(d, st)
        # 只报"这份文件要核多少内容"，**不报批次数**——批次数是内部调度细节
        runlog.log("review_file", ["--input", a.input], rc=0, out_dir=d,
                   extra={"step": "init",
                          "n_prose": st["stats"]["正文"], "n_tables": st["stats"]["表格"]})
        print(f"开始处理：{os.path.basename(a.input)}"
              f"（{st['stats']['总段']} 段／正文 {st['stats']['正文']}／表 {st['stats']['表格']}）")
    st["_dir"] = d

    rc = 0
    if a.status:
        rc = cmd_status(st, a.verbose)
    elif a.begin:
        rc = cmd_begin(st)
    elif a.commit is not None:
        rc = cmd_commit(st, a.commit, a.findings)
        if rc == 0:
            save_state(d, st)
            runlog.log("review_file", ["--commit", str(a.commit)], rc=rc, out_dir=d,
                       extra={"step": "commit", "batch": a.commit})
    elif a.finish:
        rc = cmd_finish(st, a.output)
    else:
        rc = cmd_status(st, a.verbose)
    return rc


if __name__ == "__main__":
    sys.exit(main())

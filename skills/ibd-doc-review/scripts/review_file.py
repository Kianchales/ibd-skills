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
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan_review as pr      # noqa: E402  复用其分母与切批逻辑
import docxio                 # noqa: E402
import runlog                 # noqa: E402  运行指纹（_run.json）

STATE_NAME = ".review_state.json"
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
        return json.load(f)


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
    for i, b in enumerate(batches, 1):
        prose = [u for u in b["items"] if u["type"] == "正文"]
        tables = [u for u in b["items"] if u["type"] == "表格"]
        out.append({
            "i": i,
            "name": b["name"],
            "n_prose": len(prose),
            "n_tables": len(tables),
            "status": "pending",
            "findings": [],
            "_texts": [u["text"] for u in prose],   # 仅供 --begin 吐出，不对外
        })
    return {
        "input": os.path.abspath(path),
        "stats": stats,
        "cap": [cap_p, cap_t],
        "batches": out,
    }


# ---------------------------------------------------------------- 命令

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
    """吐出下一批正文。这是**内部**取活接口，不是用户动作。"""
    for b in st["batches"]:
        if b["status"] != "done":
            print(f"### 第 {b['i']}/{len(st['batches'])} 批｜{b['name']}"
                  f"｜正文 {b['n_prose']} 段／表 {b['n_tables']}")
            for k, t in enumerate(b["_texts"], 1):
                print(f"[{b['i']}.{k}] {t}")
            return 0
    print("全部批次已处理")
    return 0


def cmd_commit(st, idx, findings_path):
    b = next((x for x in st["batches"] if x["i"] == idx), None)
    if b is None:
        print(f"[ERROR] 无第 {idx} 批", file=sys.stderr)
        return 2
    items = []
    if findings_path:
        with open(findings_path, encoding="utf-8") as f:
            items = json.load(f)
        if not isinstance(items, list):
            print("[ERROR] 发现清单应为 JSON 数组", file=sys.stderr)
            return 2
    b["findings"] = items
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
        key = (f.get("anchor", "").strip(), f.get("title", "").strip())
        if key in seen:
            continue
        seen.add(key)
        g = dict(f)
        g["id"] = "F-%02d" % (len(merged) + 1)     # 全局连续编号，与批次无关
        g["_batch"] = bi                            # 仅调试用，落盘前删
        merged.append(g)
    return merged


def cmd_finish(st, out_path=None):
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
    out = out_path or os.path.join(os.path.dirname(state_path(st.get("_dir", ""))) or ".",
                                   "findings.json")
    out = os.path.abspath(out)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    runlog.log("review_file", ["--finish"], rc=0, out_dir=st.get("_dir"),
               extra={"step": "finish", "n_findings": len(merged)})
    print(f"已合并 {len(merged)} 条｜输出 {out}")
    print("（批次信息已丢弃：对读者而言这是**一份文件的一次完整处理**）")
    return 0


# ---------------------------------------------------------------- 入口

def main():
    ap = argparse.ArgumentParser(description="单文件复核编排器（批次内部化）")
    ap.add_argument("--input", required=True, help="被复核文件（**只需给文件**）")
    ap.add_argument("--out-dir", default=None, help="内部状态目录（默认 <文件>_复核/）")
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

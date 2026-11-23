#!/usr/bin/env python3
"""金样本回归：拿**真实文档**跑工具，比对预先登记的期望值。

为什么需要它
------------
合成夹具永远造不出真实文档的坑——本包实测踩过三次，全部是真实文件才暴露的：
  · 目录页的「第X节」与正文标题同形（按文本切分会切出 12 个空批）
  · 批注样式用第三方自定义 styleId，但 w:name 已是内建名（注入后重复样式）
  · 文本提取丢表格末列（4 个值只剩 3 个，差点误判"未披露"）
单元测试测不到这些，因为它们不是逻辑错误，是**真实世界的结构**。

设计要点（为什么不把样本放进包里）
--------------------------------
样本是客户真实文档，**不得入包、不得入 git**。包内只留跑法与期望值格式；
样本目录由使用者自备，路径用环境变量 `IBD_GOLDEN_DIR` 给出（或 `--dir` 传入），
manifest 里可记绝对路径或相对 `--dir` 的相对路径。文件不在 ⇒ 该项 SKIP，不阻断。

用法
----
    python scripts/tests/golden_run.py                 # 用默认目录
    python scripts/tests/golden_run.py --dir <目录>     # 指定样本目录
    python scripts/tests/golden_run.py --update        # 重算并覆盖 manifest 期望值（同时刷新 sha256）
    python scripts/tests/golden_run.py --seal          # 只刷新 sha256（样本换了但期望值不变时用）
    python scripts/tests/golden_run.py --copy          # 把样本复制进 <目录>/samples/ 并改写为相对路径

可移植性（2026-11-20 补）
------------------------
manifest 里 `docx`/`xlsx` 支持 **相对路径**（相对 `--dir`）。推荐做法：
    --copy 把文件复制进 `<目录>/samples/`，manifest 改写为 `samples/xxx.docx`，
    以后整目录搬到别的机器即可直接跑，不再依赖某人桌面上的绝对路径。
每条可带 `sha256`：文件被替换/改动时**立刻报 FAIL**（提示"样本已变，请复核期望值"），
避免"文件换了但期望值没跟着变"导致长期假绿。

manifest.json 结构
------------------
    {"cases": [
      {"name": "某招股书", "tool": "plan_review", "docx": "samples/a.docx",
       "sha256": "…", "expect": {"总段": 25041, "正文": 909, "表格": 303, "批数": 9}},
      {"name": "某报表", "tool": "check_cq", "xlsx": "samples/b.xlsx",
       "args": ["--restr", "...", "--accrued", "..."], "expect": {"bad": 1}}
    ]}
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPTS = os.path.join(PKG, "scripts")
# 样本目录由环境变量给出（`IBD_GOLDEN_DIR`）——公开包不假设用户本机目录布局；
# 未设置且未传 --dir 时 SKIP（不阻断），并在提示里说明怎么建。
DEFAULT_DIR = os.environ.get("IBD_GOLDEN_DIR", "")


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve(base, case):
    """返回样本绝对路径：绝对路径原样用；相对路径按 `--dir` 解析（可移植）。"""
    p = case.get("docx") or case.get("xlsx")
    if not p:
        return None
    return p if os.path.isabs(p) else os.path.join(base, p)


def run_tool(tool, path, extra=None):
    """跑工具拿结构化结果；返回 (ok, data或文本)。"""
    tmp = tempfile.mkdtemp(prefix="golden_")
    if tool == "plan_review":
        cmd = [sys.executable, os.path.join(SCRIPTS, "plan_review.py"),
               "--input", path, "--out", tmp, "--json"]
    elif tool == "check_cq":
        cmd = [sys.executable, os.path.join(SCRIPTS, "check_cq.py"),
               "--xlsx", path, "--json"] + (extra or [])
    elif tool == "deliver_gate":
        # 交付件门禁：path 是**交付件**，源件/场景/开关都放在 args 里
        cmd = [sys.executable, os.path.join(SCRIPTS, "deliver_gate.py"),
               "--docx", path, "--json"] + (extra or [])
    else:
        raise SystemExit(f"未知工具：{tool}")
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = p.stdout or ""          # 只解析 stdout——stderr 混进来会让 json.loads 因尾部杂质失败
    # 候选根：每一行以 { 或 [ 开头的位置（日志行如「[计划] ...」也符合，故逐个试解析，
    # 第一个能 json.loads 成功的就是根；失败继续下一个）。
    cands, pos = [], 0
    for line in out.split("\n"):
        st = line.lstrip()
        if st[:1] in ("{", "["):
            cands.append(pos + (len(line) - len(st)))
        pos += len(line) + 1
    for k in cands:
        try:
            return True, json.loads(out[k:])
        except Exception:
            continue
    return False, (p.stdout or "")[-300:] + (p.stderr or "")[-200:]


def actual(tool, data):
    if tool == "plan_review":
        st = data[0]["stats"]
        return {"总段": st["总段"], "正文": st["正文"], "表格": st["表格"],
                "批数": len(data[0]["batches"])}
    if tool == "check_cq":
        return {"bad": data.get("bad")}
    if tool == "deliver_gate":
        return {"verdict": data.get("verdict"), "error": data.get("error"),
                "skipped": data.get("skipped")}
    return {}


def main():
    ap = argparse.ArgumentParser(description="金样本回归（真实文档）")
    ap.add_argument("--dir", default=DEFAULT_DIR,
                    help="样本目录（默认取环境变量 IBD_GOLDEN_DIR）")
    ap.add_argument("--update", action="store_true", help="重算并覆盖 manifest 期望值（同时刷新 sha256）")
    ap.add_argument("--seal", action="store_true", help="只刷新 sha256，不动期望值")
    ap.add_argument("--copy", action="store_true", help="把样本复制进 <dir>/samples/ 并改写为相对路径")
    a = ap.parse_args()

    if not a.dir:
        print("[SKIP] 未指定样本目录——设环境变量 `IBD_GOLDEN_DIR` 或传 `--dir`。本项不阻断。")
        return 0
    mf = os.path.join(a.dir, "manifest.json")
    if not os.path.exists(mf):
        print(f"[SKIP] 无金样本清单（{mf}）——本项不阻断。建法见本脚本头部说明。")
        return 0
    cases = json.load(open(mf, encoding="utf-8"))["cases"]

    n_pass = n_fail = n_skip = 0
    changed = False
    for c in cases:
        path = resolve(a.dir, c)
        if not path or not os.path.exists(path):
            print(f"[SKIP] {c['name']}：样本不存在（{path}）")
            n_skip += 1
            continue
        cur_hash = sha256_of(path)
        if a.copy:
            samples = os.path.join(a.dir, "samples")
            os.makedirs(samples, exist_ok=True)
            dst = os.path.join(samples, os.path.basename(path))
            if os.path.abspath(dst) != os.path.abspath(path):
                import shutil
                shutil.copy2(path, dst)
            key = "docx" if c.get("docx") else "xlsx"
            c[key] = os.path.relpath(dst, a.dir).replace("\\", "/")
            path = dst
            cur_hash = sha256_of(path)
            changed = True
            print(f"[COPY] {c['name']} → {c[key]}")
        if a.seal or a.update:
            c["sha256"] = cur_hash
            changed = True
        elif c.get("sha256") and c["sha256"] != cur_hash:
            print(f"[FAIL] {c['name']}：样本已变（sha256 不符）——"
                  f"请复核期望值后 `--update` 重算，勿直接放过")
            n_fail += 1
            continue
        ok, data = run_tool(c["tool"], path, c.get("args"))
        if not ok:
            print(f"[FAIL] {c['name']}：工具未产出结构化结果\n       {data}")
            n_fail += 1
            continue
        got = actual(c["tool"], data)
        if a.update:
            c["expect"] = got
            changed = True
            print(f"[UPD ] {c['name']}：{got}")
            n_pass += 1
            continue
        diff = {k: (v, got.get(k)) for k, v in c["expect"].items() if got.get(k) != v}
        if diff:
            print(f"[FAIL] {c['name']}：期望不符 {diff}")
            n_fail += 1
        else:
            print(f"[PASS] {c['name']}：{got}")
            n_pass += 1

    if changed:
        json.dump({"cases": cases}, open(mf, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("[清单已更新]")

    print(f"\n金样本回归：PASS {n_pass}／FAIL {n_fail}／SKIP {n_skip}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""runlog.py — 复核运行指纹（`_run.json`）

为什么要有它
------------
复核是否按 skill 流程走完，**从产物看不出来**：自建的 `format_check.md` 与本包输出长得很像，
要逐个扒 JSON 才能判断。于是出现"看起来做了全量复核，实际只跑了 1 个工具"的情况（实证：某轮
报告内容不错，但 7 条硬要求里 6 条未执行，产物里唯一的本包 JSON 只有一个 `check_content`）。

本模块把"跑了什么"落成一份机器可读的记录：每一步记 **工具名／参数摘要／退出码／skill 版本／时间**。
配套 `check_runlog.py` 据此判定流程合规，不需要人工翻文件。

落点与开启方式
--------------
- 目录：`<被复核文件目录>/<文件名>_复核/_run.json`（与编排器状态同处，**内部门面**，不交付）
- 自动开启条件（二者其一）：
  1. 环境变量 `IBD_RUNLOG_DIR` 指向目录；
  2. 该 `<文件名>_复核/` 目录**已存在**（例如 `review_file.py` 已初始化）——
     避免随便跑一次工具就在别人目录里撒文件。
- 关闭：`IBD_RUNLOG=0`

写入是**追加 + 原子替换**：中途崩溃不会留下半截 JSON。
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SKILL_MD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SKILL.md")
RUNLOG_NAME = "_run.json"

# 合规判定用的"必需步骤"（check_runlog.py 消费）
REQUIRED_STEPS = ["check_content", "check_cq", "deliver_gate"]


def skill_version():
    """取本包当前版本（写在 SKILL.md frontmatter 的 version:）。"""
    try:
        with open(SKILL_MD, encoding="utf-8") as f:
            for line in f:
                m = re.match(r"^version:\s*(\S+)", line.strip())
                if m:
                    return m.group(1)
    except OSError:
        pass
    return "?"


def target_dir(input_path, explicit=None):
    """返回运行指纹目录；不该写时返回 None。"""
    if os.environ.get("IBD_RUNLOG") == "0":
        return None
    if explicit:
        return explicit
    env = os.environ.get("IBD_RUNLOG_DIR")
    if env:
        return env
    if not input_path:
        return None
    base = os.path.splitext(os.path.basename(str(input_path)))[0]
    d = os.path.join(os.path.dirname(os.path.abspath(str(input_path))), base + "_复核")
    return d if os.path.isdir(d) else None


def _path(d):
    return os.path.join(d, RUNLOG_NAME)


def read(d):
    p = _path(d)
    if not os.path.exists(p):
        return {"skill_version": skill_version(), "steps": []}
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"skill_version": skill_version(), "steps": []}


def log(tool, argv=None, rc=0, input_path=None, extra=None, out_dir=None):
    """记一步。返回写入的目录；未开启则返回 None。**永不抛异常**（不因记录失败拖垮主流程）。"""
    try:
        d = target_dir(input_path, out_dir)
        if not d:
            return None
        os.makedirs(d, exist_ok=True)
        cur = read(d)
        argv = list(argv or [])
        cur["skill_version"] = skill_version()
        steps = cur.setdefault("steps", [])
        rec = {
            "seq": len(steps) + 1,
            "tool": tool,
            "rc": int(rc),
            "argv": [str(x) for x in argv[:12]],
            "at": time.strftime("%Y-%m-%d %H:%M:%S"),
            **({"extra": extra} if extra else {}),
        }
        # 哈希链：每条记录承接上一条的 h。事后补写或改写会让链断裂——
        # 不指望它防得住刻意伪造，但能拦住"回头补一笔"这种最常见的做法。
        prev = steps[-1].get("h", "") if steps else ""
        rec["h"] = hashlib.sha1(
            (prev + json.dumps({k: v for k, v in rec.items() if k != "h"},
                               ensure_ascii=False, sort_keys=True)).encode("utf-8")
        ).hexdigest()[:16]
        steps.append(rec)
        tmp = _path(d) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cur, f, ensure_ascii=False, indent=1)
        os.replace(tmp, _path(d))
        return d
    except Exception:      # noqa: BLE001  记录失败不得影响主流程
        return None


def autolog(tool, argv, rc, input_path=None):
    """CLI 收尾一行调用：带上 sys.argv 与退出码。"""
    return log(tool, argv=argv if argv is not None else sys.argv[1:],
               rc=rc, input_path=input_path)


def main():
    ap = argparse.ArgumentParser(description="查看运行指纹（_run.json）")
    ap.add_argument("--dir", default=".", help="运行目录（含 _run.json）")
    a = ap.parse_args()
    print(json.dumps(read(a.dir), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""团队收尾验收单 JSON 机检（INTERFACE-CONTRACT-MAP 验收单节 schema）
用法：python scripts/check_team_accept.py <state/team_accept_*.json> [ ...]
退出码：0=PASS，1=FAIL
"""
import json, sys

STATUSES = {"ok", "missing", "degraded"}
ATYPES = {"nudge", "degrade", "respawn", "pending", "drift"}

def check(path):
    errs = []
    try:
        d = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        return [f"{path}: JSON 解析失败 {e}"]
    for k in ("task_id", "date", "returns", "anomalies", "gate_points"):
        if k not in d:
            errs.append(f"{path}: 缺区块 {k}")
    if not isinstance(d.get("returns"), list):
        errs.append(f"{path}: returns 须为数组")
    else:
        for i, r in enumerate(d["returns"]):
            if r.get("status") not in STATUSES:
                errs.append(f"{path}: returns[{i}].status 非法（{r.get('status')}）")
            for k in ("member", "task", "artifact"):
                if not r.get(k):
                    errs.append(f"{path}: returns[{i}].{k} 缺失")
    if not isinstance(d.get("anomalies"), list):
        errs.append(f"{path}: anomalies 须为数组")
    else:
        for i, a in enumerate(d["anomalies"]):
            if a.get("type") not in ATYPES:
                errs.append(f"{path}: anomalies[{i}].type 非法（{a.get('type')}）")
    gp = d.get("gate_points")
    if not isinstance(gp, list):
        errs.append(f"{path}: gate_points 须为数组")
    elif len(gp) > 5:
        errs.append(f"{path}: 把关点 {len(gp)} 项，超上限 5")
    return errs

def main():
    if len(sys.argv) < 2:
        print("用法: python check_team_accept.py <team_accept_*.json> ..."); sys.exit(1)
    all_errs = []
    for p in sys.argv[1:]:
        all_errs += check(p)
    if all_errs:
        print(f"❌ FAIL {len(all_errs)} 项：")
        for e in all_errs: print("  " + e)
        sys.exit(1)
    print(f"✅ PASS：{len(sys.argv)-1} 个验收单机检通过")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""测试分层：默认只跑"快测"，全量需显式声明。

为什么分层
----------
全量 191 例耗时约 **90 秒**，且用例只涨 35% 而耗时涨 246%——因为慢的都在**起子进程**
（每个 CLI 用例起一次 Python 解释器）或**全仓扫描**（扫 166 个脚本）。90 秒会让人
不愿跑，等于防线自己失效。

分层口径（按机制，不按主观感受）
-------------------------------
    快测  = 不起子进程：纯函数、解析、规则判定、渲染
    慢测  = 起子进程（CLI 端到端）或扫全仓

用法
----
    python -m unittest discover -s scripts/tests        # 快测（默认，约 7 秒）
    REVIEW_TESTS=all python -m unittest discover -s scripts/tests   # 全量（约 90 秒）

**默认快测是否安全？** 安全的前提是：慢测守的是「端到端联通」与「真实文件结构」，
而这两类在改动后另有更强的把关——`golden_run.py`（真实文档回归）与 `deliver_gate.py`
（真实交付件门禁）。故日常迭代跑快测，**提交前/升版前必须跑全量**。
"""
import os
import unittest

SLOW = os.environ.get("REVIEW_TESTS", "").strip().lower() in ("all", "1", "slow", "full")


WHY = "慢测模块（子进程/全仓扫描）：设 REVIEW_TESTS=all 跑全量"


def slow_all(ns):
    """在慢测模块**末尾**调用（此时类都已定义）：给本模块所有 TestCase 打跳过标记。

    不用「模块顶部 raise SkipTest」——那样会把**复用本模块辅助函数的其他测试模块**
    一起拖下水（实测 test_plan_review 复用 test_deliver_gate 的造包函数，整块被跳过）。
    这里只给类打 skip 属性，模块仍可正常 import，辅助函数照常可用。
    """
    if SLOW:
        return
    for obj in list(ns.values()):
        if (isinstance(obj, type) and issubclass(obj, unittest.TestCase)
                and obj is not unittest.TestCase):
            obj.__unittest_skip__ = True
            obj.__unittest_skip_why__ = WHY

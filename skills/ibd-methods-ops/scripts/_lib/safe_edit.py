#!/usr/bin/env python3
"""唯一匹配门（safe-edit precondition）—— 改动型脚本的**通用前置契约**。

判据（2026-09-26 WO-22 立；全部 safe-fix 统一口径）：
    **恰好 1 个匹配才允许改；0 个 / 多个匹配一律转报告，不得自动改。**
    **语义类判断永不自动改。**

为什么要有它（本库两次事故，同根因）：
    ① 历史回改把 `招` 误扩为 `招·招·注册稿`，**84 处**误伤；
    ② 回写器产出形态与契约校验器受理形态**不相交** ⇒ 门禁空转报 PASS 属假绿
       （实测受理 830／漏检 3,675 ＝ 覆盖 **18.4%**，判 I-0088）。
    两次都是「**在没有唯一确定性时就动手**」。

用法：
    from _lib.safe_edit import unique_match, apply_once, EditRefused

    m = unique_match(text, r"（招 P(\\d+)）", what="来源标注")
    if m is None:            # 0 或多解 —— 转报告，不改
        report.append(...)
    else:
        new = apply_once(text, m, m.group(0).replace("（", "（"), ...)   # 单点替换

边界（**诚实声明**）：
    · 本模块**只提供前置门**，不主动改造任何既有脚本 —— 改造既有修复脚本会**改变其判定行为**，
      属②规范面变更，**另行裁定**（未改造清单见 `references/govern/fix-tools.md`「唯一匹配门」节）。
    · 新增改动型脚本**应**复用本模块；复核者按「是否调用 `unique_match`」判断其是否带门。
"""
import re

__all__ = ["EditRefused", "unique_match", "apply_once"]


class EditRefused(Exception):
    """在无唯一确定性时拒绝改动（0 个 / 多个匹配）。调用方应把它转成报告项，而非吞掉。"""

    def __init__(self, what, count, samples=None):
        self.what = what
        self.count = count
        self.samples = list(samples or [])[:5]
        super().__init__("拒绝改动：%s 匹配数=%d（须恰好 1）%s"
                         % (what, count, "；样例：" + " / ".join(self.samples) if self.samples else ""))


def unique_match(text, pattern, what="目标"):
    """返回**唯一**匹配的 `re.Match`；命中 0 个或多个时返回 `None`（**不抛异常**）。

    调用方约定：返回 `None` ⇒ **转报告，不改**。
    需要「多解即报错中断」的场合改用 `require_unique`。
    """
    hits = list(re.finditer(pattern, text, re.M))
    if len(hits) != 1:
        return None
    return hits[0]


def require_unique(text, pattern, what="目标"):
    """同 `unique_match`，但无唯一解时**抛 `EditRefused`**（供「必须改对」的脚本用）。"""
    hits = list(re.finditer(pattern, text, re.M))
    if len(hits) != 1:
        raise EditRefused(what, len(hits), [h.group(0)[:40] for h in hits])
    return hits[0]


def apply_once(text, match, replacement):
    """按 `match` 的跨度做**单点**替换并返回新文本（不改其它任何位置）。

    以 span 定位而非 `str.replace`：后者会**顺带改掉同形的其它位置**（正是 84 处误伤的机理）。
    """
    s, e = match.span()
    return text[:s] + replacement + text[e:]

#!/usr/bin/env python3
"""ibd-quality-gates 自动化扫描器（G1 裸数字粗筛 + G2 绝对化/AI 痕迹扫描）

用法:
    python check_gates.py <文档.md|文档.txt> [--wordlist-dir 目录]

输出:
    终端报告（HIGH=须改 / WARN=带来源标注需人工确认 / INFO=粗筛提示）
    退出码: 0=无 HIGH 命中, 1=存在 HIGH 命中, 2=文件/参数错误

边界说明:
    本脚本只做机械初筛。语义问题（来源真实性、口径一致性、论证完整性）
    必须人工按 references/antipatterns.md 核对，脚本不能替代人工。
"""
import argparse
import os
import re
import sys

DEFAULT_WORDLIST_DIR = os.path.join(os.path.dirname(__file__), "..", "references")

# 带这些标记的行，绝对化命中降级为 WARN（有来源撑腰，人工确认即可）
SOURCE_MARKERS = ("来源：", "来源:", "来源=", "据", "援引", "引自")

# G1 裸数字粗筛：数字后面没有跟常见单位/时点字符，且不是序号/百分比/日期
_UNIT_CHARS = "年月日%％倍页条名只支家轮项个次人亿美元千百十万亿兆吨千米厘分秒股债笔期号版"
_NUMERIC = re.compile(r"\d[\d,，.]*")
_NOT_NUMBER = re.compile(r"^(?:\d{4}[-/年]\d{1,2}|[#*\-+]|\d+[.、)）]\s|\d+\.\d+[.]\d)")


def load_wordlist(path):
    words = []
    if not os.path.exists(path):
        return words
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                words.append(line)
    return words


def scan_wordlist(lines, words, label):
    hits = []
    for lineno, text in lines:
        for w in words:
            if w in text:
                has_source = any(m in text for m in SOURCE_MARKERS)
                hits.append({
                    "gate": label,
                    "line": lineno,
                    "text": text.strip()[:60],
                    "word": w,
                    "severity": "WARN" if has_source else "HIGH",
                })
    return hits


def scan_bare_numbers(lines):
    """G1 粗筛：找出后面没跟单位/时点字符的独立数字（仅提示，需人工复核）。"""
    hits = []
    for lineno, text in lines:
        for m in _NUMERIC.finditer(text):
            start, end = m.span()
            if _NOT_NUMBER.match(text[start:]):
                continue
            nxt = text[end] if end < len(text) else " "
            prev = text[start - 1] if start > 0 else " "
            if nxt in _UNIT_CHARS or prev in "第.、:：/－-" or prev.isdigit():
                continue
            ctx = text[max(0, start - 12):min(len(text), end + 12)].strip()
            hits.append({
                "gate": "G1-粗筛",
                "line": lineno,
                "text": ctx,
                "word": m.group(),
                "severity": "INFO",
            })
    return hits


def main():
    ap = argparse.ArgumentParser(description="ibd-quality-gates 自动化扫描")
    ap.add_argument("file", help="待扫描的 .md / .txt 文件")
    ap.add_argument("--wordlist-dir", default=DEFAULT_WORDLIST_DIR, help="黑名单目录")
    args = ap.parse_args()

    if not os.path.exists(args.file):
        print(f"错误：文件不存在 {args.file}")
        sys.exit(2)

    with open(args.file, encoding="utf-8") as f:
        lines = [(i + 1, l) for i, l in enumerate(f)]

    abs_words = load_wordlist(os.path.join(args.wordlist_dir, "wordlist-absolute.txt"))
    ai_words = load_wordlist(os.path.join(args.wordlist_dir, "wordlist-ai-flavor.txt"))

    hits = []
    hits += scan_wordlist(lines, abs_words, "G2-绝对化")
    hits += scan_wordlist(lines, ai_words, "S1-AI痕迹")
    hits += scan_bare_numbers(lines)

    order = {"HIGH": 0, "WARN": 1, "INFO": 2}
    hits.sort(key=lambda h: order[h["severity"]])

    print(f"=== ibd-quality-gates 扫描报告：{os.path.basename(args.file)} ===")
    print(f"扫描行数：{len(lines)}；命中：{len(hits)}（HIGH {sum(1 for h in hits if h['severity']=='HIGH')} / WARN {sum(1 for h in hits if h['severity']=='WARN')} / INFO {sum(1 for h in hits if h['severity']=='INFO')}）")
    for h in hits:
        print(f"[{h['severity']}] {h['gate']} | L{h['line']} | 词:「{h['word']}」| {h['text']}")
    if not hits:
        print("无命中。注意：脚本只查机械项，语义项（来源/口径/论证）仍需人工按 antipatterns.md 核对。")
    print("---")
    print("提醒：HIGH=须改；WARN=带来源标注，人工确认；INFO=裸数字粗筛，多数为正常序号，请人工复核。")
    sys.exit(1 if any(h["severity"] == "HIGH" for h in hits) else 0)


if __name__ == "__main__":
    main()

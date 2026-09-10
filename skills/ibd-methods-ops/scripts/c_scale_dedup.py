# -*- coding: utf-8 -*-
"""
C 档动作 1：质量自评量表收敛（2026-08-31）
- 权威定义 = ibd-quality-gates skill（SKILL.md §2.4 + references/rules.md §4），不造第二源
- 8 处单案量表统一为「执行记录」：标题统一 h3、表头统一「维度|得分|说明」、
  总分判定统一「≥25 达标」、标题下加引用注记
- 写作域末尾新增附录 B：单一事实源声明 + 记录约定
- 铁律：只改格式/加指针，不删任何案维内容（得分、说明保留）
"""
import io
import os
import sys

import argparse, json
from pathlib import Path

_ap = argparse.ArgumentParser(description="质量自评量表收敛（C 档）")
_ap.add_argument("--plan", default="", help="条目修复计划 JSON（[[file,title_old,header_old,total_old],...]）")
_ap.add_argument("--methods-root", default=os.environ.get("METHODS_ROOT", ""),
                 help="方法论库根目录（默认 $METHODS_ROOT，或脚本上级目录）")
_args = _ap.parse_args()
_ROOT = Path(_args.methods_root) if _args.methods_root else Path(__file__).resolve().parents[1]
METHODS = str(_ROOT / "methods")
WRITE_DOMAIN = os.path.join(METHODS, '通用方法论_写作域.md')

NOTE = '> 量表定义见 ibd-quality-gates skill §2.4（6 维 30 分，<25 分不交付）；下表为本案自评执行记录。'

# TARGETS 从 --plan JSON 读（条目修复计划）：
# [[file, title_old, header_old, total_old], ...]（None=无需改动）
_plan_path = getattr(_args, "plan", None)
TARGETS = json.load(io.open(_plan_path, encoding="utf-8")) if _plan_path else []
if not TARGETS:
    print("提示：未指定 --plan（修复计划 JSON），本次无待修复目标。")

APPENDIX_B = """### 附录 B：质量自评量表（6 维 30 分）· 单一事实源与记录约定

> **权威定义**：质量自评量表（6 维 30 分）由 `ibd-quality-gates` skill 统一定义
> （SKILL.md §2.4 概述 + references/rules.md §4 三档打分规则），**此处不重复定义、不设第二源**。
> **定位**：单案方法论/行业方法论中的「质量自评量表」段落 = **该案自评执行记录**
> （得分 + 案维说明），不是量表定义本身。
> **记录约定**（2026-08-31 统一，8 处单案已收敛）：
> - 标题统一 `### 质量自评量表（6 维 30 分）`，标题下注记指向本约定；
> - 表头统一 `| 维度 | 得分 | 说明 |`；总分判定统一 `≥25 达标`；
> - 判定阈值：总分 < 25 分不交付（skill rules.md §4）；
> - 案维说明列保留各案特有指标与页码锚点，不抽离（执行记录证据链）。"""


def load(fn):
    with io.open(os.path.join(METHODS, fn), encoding='utf-8') as f:
        return f.read().splitlines()


def save(fn, lines):
    with io.open(os.path.join(METHODS, fn), 'w', encoding='utf-8', newline='') as f:
        f.write('\n'.join(lines) + '\n')


def plan_one(fn, title_old, header_old, total_old):
    lines = load(fn)
    ops = []  # (kind, line_idx, old, new) kind: title/header/total
    for i, l in enumerate(lines):
        s = l.rstrip()
        if title_old and s == title_old:
            ops.append(('title', i, s, '### 质量自评量表（6 维 30 分）'))
        elif header_old and s == header_old:
            ops.append(('header', i, s, '| 维度 | 得分 | 说明 |'))
        elif total_old and s == total_old:
            ops.append(('total', i, s, total_old.replace('✅ ≥25', '≥25 达标').replace('≥25，通过', '≥25 达标')))
    return lines, ops


def main():
    dry = '--dry-run' in sys.argv
    for fn, title_old, header_old, total_old in TARGETS:
        lines, ops = plan_one(fn, title_old, header_old, total_old)
        print(f'=== {fn} ===')
        for kind, i, old, new in ops:
            print(f'  [{kind}] L{i+1}\n    - {old}\n    + {new}')
        if not ops:
            print('  （无匹配，跳过）')
    if dry:
        return
    # 执行
    for fn, title_old, header_old, total_old in TARGETS:
        lines, ops = plan_one(fn, title_old, header_old, total_old)
        out = list(lines)
        for kind, i, old, new in reversed(ops):
            assert out[i].rstrip() == old.rstrip(), f'{fn} L{i+1} 不匹配: {out[i]!r} vs {old!r}'
            out[i] = new
        # 统一注记插入：找到量表标题行（标准名），标题后统一构造「空行/注记/空行」
        STD_TITLE = '### 质量自评量表（6 维 30 分）'
        title_idxs = [i for i, l in enumerate(out) if l.rstrip() == STD_TITLE]
        if len(title_idxs) != 1:
            raise SystemExit(f'{fn}: 量表标题匹配 {len(title_idxs)} 处（应为 1）')
        title_idx = title_idxs[0]
        k = title_idx + 1
        while k < len(out) and not out[k].strip():
            k += 1
        # out[title_idx+1:k] 原是标题后的空行（或空），统一替换为 空行/注记/空行
        out[title_idx + 1:k] = ['', NOTE, '']
        save(fn, out)
        print(f'  ✅ {fn} 已写入')


def add_appendix_b():
    dry = '--dry-run' in sys.argv
    with io.open(WRITE_DOMAIN, encoding='utf-8') as f:
        lines = f.read().splitlines()
    # 找末尾「---」前插入
    if any('附录 B' in l for l in lines):
        print('写作域已含附录 B，跳过')
        return
    if dry:
        print('写作域：将在末尾「---」前插入附录 B')
        return
    # 从末尾往前找第一个 ---
    end = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip() == '---':
            end = i
            break
    insert = APPENDIX_B.split('\n')
    new_lines = lines[:end] + [''] + insert + ['', ''] + ['---'] + lines[end + 1:]
    with io.open(WRITE_DOMAIN, 'w', encoding='utf-8', newline='') as f:
        f.write('\n'.join(new_lines) + '\n')
    print('  ✅ 写作域附录 B 已写入')


if __name__ == '__main__':
    main()
    add_appendix_b()

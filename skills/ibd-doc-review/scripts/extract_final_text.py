#!/usr/bin/env python3
"""ibd-doc-review · extract_final_text — 读取含修订/批注的 Word：先探测部件，再取「接受全部修订 ＋ 剔除全部批注」的终稿文本（只读，源文件零写操作）

用法: python extract_final_text.py <docx> [-o <out.txt>] [--check] [--json]
退出码: 0=PASS  2=用法或环境错误  3=SKIP（无正文段落可提取）
"""
import argparse
import io
import json
import os
import sys
import zipfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"
W = "{%s}" % W_NS
MC_FALLBACK = "{%s}Fallback" % MC_NS

DOC_PART = "word/document.xml"
COMMENTS_PART = "word/comments.xml"

USAGE = "用法: python extract_final_text.py <docx> [-o <out.txt>] [--check] [--json]"


# ---------------------------------------------------------------- 文本提取

def _walk(el, out, deleted):
    """递归取文本：`w:del` 子树整体排除（接受全部修订）；只收 `w:t`。

    - `w:delText` 天然不收（元素名不同）—— `w:del` 子树直接跳过，含其中嵌套 `w:ins`；
    - `w:tab` → `\\t`；`w:br` / `w:cr` → 换行；`w:p` 收完补行尾；
    - `mc:Fallback` 跳过：避免与 `mc:Choice` 重复计入同一段文本框内容；
    - 批注标记（`w:commentRangeStart` / `w:commentRangeEnd` / `w:commentReference`）是空元素，
      正文天然不含批注文本（批注正文在 `word/comments.xml`，不在 `document.xml`）。
    """
    for ch in el:
        tag = ch.tag
        if tag == W + "del":
            _walk(ch, out, True)                    # 删除内容：整棵子树不收
        elif tag == W + "delText":
            continue
        elif tag == W + "t":
            if not deleted:
                out.append(ch.text or "")
        elif tag == W + "tab":
            out.append("\t")
        elif tag in (W + "br", W + "cr"):
            out.append("\n")
        elif tag == W + "p":
            _walk(ch, out, deleted)
            out.append("\n")
        elif tag == MC_FALLBACK:
            continue
        else:
            _walk(ch, out, deleted)


def extract_body_text(body):
    out = []
    _walk(body, out, False)
    return "".join(out)


def _count(tree, tag):
    return sum(1 for _ in tree.iter(tag))


def _parse(xml_bytes):
    from xml.etree import ElementTree as ET
    return ET.fromstring(xml_bytes)


def probe(path):
    """探测三部件（`w:ins` / `w:del` / `word/comments.xml`）并取终稿文本。

    返回 dict：ins / del / comments 计数、flagged（是否含修订或批注）、text、chars、paras。
    """
    with zipfile.ZipFile(path, "r") as z:
        names = set(z.namelist())
        if DOC_PART not in names:
            raise ValueError("不是有效 docx（缺 %s）" % DOC_PART)
        doc = _parse(z.read(DOC_PART))
        n_ins = _count(doc, W + "ins")
        n_del = _count(doc, W + "del")
        n_comments = 0
        if COMMENTS_PART in names:
            cm = _parse(z.read(COMMENTS_PART))
            n_comments = _count(cm, W + "comment")
    body = doc.find(W + "body")
    text = extract_body_text(body) if body is not None else ""
    return {
        "ins": n_ins,
        "del": n_del,
        "comments": n_comments,
        "has_comments_part": COMMENTS_PART in names,
        "flagged": bool(n_ins or n_del or COMMENTS_PART in names),
        "text": text,
        "chars": len(text),
        "paras": text.count("\n"),
    }


# ---------------------------------------------------------------- 输出

def banner(src, p):
    """标注头 —— 交付物须能被一眼看出「所读是终稿视角、原件仍待处理」。"""
    tag = "【该文件原件含修订/批注】" if p["flagged"] else "【原件无修订/批注】"
    return [
        "# extract_final_text — 终稿文本（接受全部修订 ＋ 剔除全部批注）",
        "# 源文件: %s" % os.path.basename(src),
        "# 探测: ins=%d del=%d comments=%d → %s" % (p["ins"], p["del"], p["comments"], tag),
        "# 口径: w:ins 计入 / w:delText 排除 / 批注不进正文；源文件零写操作（未接受修订、未删批注）",
    ]


def main():
    ap = argparse.ArgumentParser(description="读取含修订/批注的 Word，取终稿文本（只读）")
    ap.add_argument("docx", help="待读 docx（源文件，只读）")
    ap.add_argument("-o", "--output", help="终稿文本落盘路径（缺省只打印到 stdout）")
    ap.add_argument("--check", action="store_true", help="只探测部件并标注，不输出正文")
    ap.add_argument("--json", action="store_true", help="输出结构化 JSON（不打印人类摘要）")
    a = ap.parse_args()

    if not os.path.exists(a.docx):
        print("[ERROR] 文件不存在: %s" % a.docx, file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return 2
    try:
        p = probe(a.docx)
    except (zipfile.BadZipFile, ValueError, OSError) as e:
        print("[ERROR] 打开失败: %s（%s）" % (a.docx, e), file=sys.stderr)
        return 2
    except Exception as e:                          # XML 解析失败等：报用/环境错误，不崩栈
        print("[ERROR] 解析失败: %s（%s）" % (a.docx, e), file=sys.stderr)
        return 2

    head = banner(a.docx, p)
    text = "" if a.check else p["text"]
    rc = 3 if (not a.check and not text.strip()) else 0

    if a.json:
        print(json.dumps({
            "tool": "extract_final_text", "target": a.docx,
            "verdict": "SKIP" if rc == 3 else "PASS",
            "error": 0, "warn": 0, "issues": [],
            "file": os.path.basename(a.docx),
            "ins": p["ins"], "del": p["del"], "comments": p["comments"],
            "flagged": p["flagged"], "has_comments_part": p["has_comments_part"],
            "chars": p["chars"], "paras": p["paras"],
            "mode": "check" if a.check else "text",
            "output": a.output or None,
        }, ensure_ascii=False))
        return rc

    for ln in head:
        print(ln)
    if a.check:
        print("# 模式: 仅探测")
        return rc
    print("--- 正文 ---")
    sys.stdout.write(text)
    if text and not text.endswith("\n"):
        sys.stdout.write("\n")

    if a.output:
        with io.open(a.output, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(head) + "\n--- 正文 ---\n" + text)
            if text and not text.endswith("\n"):
                fh.write("\n")
        print("# 已落盘: %s" % a.output, file=sys.stderr)
    return rc


if __name__ == "__main__":
    sys.exit(main())

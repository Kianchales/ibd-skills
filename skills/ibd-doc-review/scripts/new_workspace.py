#!/usr/bin/env python3
"""复核工作区初始化（两档模式）。

用法
----
    # 多文件作业区：同时复核 >=2 个不同文档
    python new_workspace.py --mode multi  --root <工作区根> --project <项目简称>

    # 单文件模式（默认）：只核一份文档
    python new_workspace.py --mode single --source <被复核文件>

产出
----
multi   : <root>/<project>/ 下五层 + 参考资料四类 + README.md
          + .review-workspace.json（脚本据此推导默认落点）+ 01/00_基准说明.md
single  : <源文件同级>/<文件名>_复核/ 下四层（参考资料/问题记录/复核结果/过程文件）

设计约定
--------
1. **幂等**：已存在的目录与文件一律不动；``--force`` 只覆盖三个模板文件
   （README、00_基准说明.md、.review-workspace.json），**不删除任何内容目录**。
2. **``--root`` 必填**：工作区放哪是本机习惯，脚本不猜默认位置。
3. **零依赖**：仅标准库；Windows/macOS/Linux 通用，中文路径安全。

结构规范全文见 references/workspace-layout.md。
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# 多文件作业区：五层（顺序即编号顺序）
MULTI_DIRS = [
    ("materials", "01_待复核材料"),
    ("references", "02_参考资料"),
    ("issues", "03_问题记录"),
    ("results", "04_复核结果"),
    ("process", "05_过程文件"),
]

# 参考资料四类（固定，不再加第五类——上轮清单归 03、整改回复归 01）
REF_SUBDIRS = ["01_规则与准则", "02_内部口径", "03_同类范例", "04_数据来源"]

# 单文件模式：四层（无 01，被复核文件本身就在源目录）
SINGLE_DIRS = ["参考资料", "问题记录", "复核结果", "过程文件"]

BASELINE_NAME = "00_基准说明.md"
META_NAME = ".review-workspace.json"
README_NAME = "README.md"
README_TEMPLATE = "workspace-README-template.md"

BASELINE_TMPL = """# 本轮基准说明

> 本文件指明「本轮复核以哪一份为准」。**任何时刻只有一行是当前的**，其余进「历史对照」。
> 文件名以 `00_` 开头是为了让它永远排在版本堆前面——不用点开就知道认哪份。

## 当前基准

| 项 | 内容 |
|---|---|
| 文件名 | （待填：完整文件名含扩展名） |
| 收到日期 / 来源 | （待填：什么时候、从哪来） |
| 认定依据 | （待填：**为什么是这一版**——写具体改动，不要写「最新一版」） |
| 本轮轮次 | 第 1 轮 |
| 认定人 / 时间 | （待填） |

## 历史对照

| 轮次 | 文件名 | 认定依据 | 认定时间 |
|---|---|---|---|
| 第 1 轮 | （待填） | | |
"""


def _say(msg=""):
    print(msg)


def _count_summary(created, existed):
    if created:
        _say("  新建 %d 个目录：" % len(created))
        for p in created:
            _say("    + %s" % p)
    if existed:
        _say("  已存在 %d 个目录（未改动）" % len(existed))


def _ensure_dirs(base, names, created, existed):
    for name in names:
        path = base / name
        if path.is_dir():
            existed.append(str(path))
        else:
            path.mkdir(parents=True, exist_ok=True)
            created.append(str(path))


def _write_template(path, content, force, written, skipped):
    if path.exists() and not force:
        skipped.append(str(path))
        return
    action = "覆盖" if path.exists() else "写入"
    path.write_text(content, encoding="utf-8")
    written.append("%s %s" % (action, path))


def _load_readme_template(project, created_date):
    """优先读包内模板；模板缺失时用内联兜底，保证脚本可独立运行。"""
    here = Path(__file__).resolve().parent
    for cand in (here.parent / "assets" / README_TEMPLATE,):
        if cand.is_file():
            text = cand.read_text(encoding="utf-8")
            return text.replace("{{项目名}}", project).replace("{{创建日期}}", created_date)
    return (
        "# %s · 复核工作区\n\n"
        "> 由 new_workspace.py 生成。把这个文件夹整个拷给别人也能看懂怎么用。\n\n"
        "## 以哪版为准\n\n见 `01_待复核材料/%s`。**动手前先看它**，别按文件日期猜新旧。\n\n"
        "## 每层干什么\n\n"
        "| 文件夹 | 放什么 |\n|---|---|\n"
        "| `01_待复核材料/` | 客户发来的各版文件（只读） |\n"
        "| `02_参考资料/` | 规则准则、内部口径、同类范例、数据来源 |\n"
        "| `03_问题记录/` | 每轮查出的问题，按原文名分子目录 |\n"
        "| `04_复核结果/` | 批注版、复核报告、修订稿（能发出去的） |\n"
        "| `05_过程文件/` | 总览、台账、日志、临时脚本（只给自己看） |\n\n"
        "## 三条规矩\n\n"
        "1. `01` 只读，要改另存新版本。\n"
        "2. 交付只从 `04` 取，`05` 一律不对外。\n"
        "3. 换基准必留痕：在 `00_基准说明.md` 的历史对照追加一行。\n"
    ) % (project, BASELINE_NAME)


def cmd_multi(args):
    root = Path(args.root).expanduser()
    if not root.is_dir():
        _say("错误：工作区根目录不存在：%s" % root)
        _say("      --root 须指向一个已存在的目录（脚本不自动建盘符/顶层目录，防误建）")
        return 2
    project = args.project.strip()
    if not project:
        _say("错误：--project 不能为空")
        return 2
    if any(sep in project for sep in ("/", "\\", "..")):
        _say("错误：--project 只能是一层目录名，不能含路径分隔符：%s" % project)
        return 2

    base = root / project
    created, existed = [], []
    if not base.is_dir():
        base.mkdir(parents=True)
        created.append(str(base))

    _ensure_dirs(base, [d for _, d in MULTI_DIRS], created, existed)
    _ensure_dirs(base / "02_参考资料", REF_SUBDIRS, created, existed)

    today = datetime.date.today().isoformat()
    written, skipped = [], []

    _write_template(base / README_NAME, _load_readme_template(project, today), args.force, written, skipped)
    _write_template(base / "01_待复核材料" / BASELINE_NAME, BASELINE_TMPL, args.force, written, skipped)

    meta = {
        "schema": 1,
        "mode": "multi",
        "project": project,
        "created": today,
        "dirs": {key: name for key, name in MULTI_DIRS},
        "ref_subdirs": REF_SUBDIRS,
    }
    _write_template(
        base / META_NAME,
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
        args.force,
        written,
        skipped,
    )

    _say("[多文件作业区] %s" % base)
    _count_summary(created, existed)
    if written:
        _say("  模板文件：")
        for item in written:
            _say("    %s" % item)
    if skipped:
        _say("  已存在跳过 %d 个模板文件（--force 可覆盖）：" % len(skipped))
        for item in skipped:
            _say("    = %s" % item)
    _say("")
    _say("下一步：把各版文件放进 01_待复核材料/，填好 %s，" % BASELINE_NAME)
    _say("        并在 README.md 第一节写清在核什么。")
    return 0


def cmd_single(args):
    source = Path(args.source).expanduser()
    if not source.is_file():
        _say("错误：被复核文件不存在：%s" % source)
        return 2

    base = source.parent / (source.stem + "_复核")
    created, existed = [], []
    if not base.is_dir():
        base.mkdir(parents=True)
        created.append(str(base))
    _ensure_dirs(base, SINGLE_DIRS, created, existed)

    _say("[单文件模式] %s" % base)
    _count_summary(created, existed)
    _say("")
    _say("被复核文件就留在原位（%s），不复制进工作目录。" % source.name)
    _say("有多版时：在 %s/ 下放一份 %s 指明本轮认哪版。" % (base.name, BASELINE_NAME))
    return 0


def build_parser():
    p = argparse.ArgumentParser(
        description="复核工作区初始化（单文件 / 多文件两档）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例：\n"
            "  python new_workspace.py --mode multi  --root <工作区根> --project <项目简称>\n"
            "  python new_workspace.py --mode single --source <被复核文件>\n"
        ),
    )
    p.add_argument("--mode", choices=["multi", "single"], default="single",
                   help="multi=多文件作业区（>=2 个不同文档）；single=单文件模式（默认）")
    p.add_argument("--root", help="多文件模式：工作区根目录（须已存在）")
    p.add_argument("--project", help="多文件模式：项目简称，作为根目录下的一层文件夹")
    p.add_argument("--source", help="单文件模式：被复核文件路径")
    p.add_argument("--force", action="store_true",
                   help="覆盖三个模板文件（README / 00_基准说明.md / .review-workspace.json）；不删除任何内容目录")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.mode == "multi":
        missing = [f for f in ("root", "project") if not getattr(args, f)]
        if missing:
            _say("错误：--mode multi 需要 %s" % "、".join("--" + m for m in missing))
            return 2
        return cmd_multi(args)
    if not args.source:
        _say("错误：--mode single 需要 --source")
        return 2
    return cmd_single(args)


if __name__ == "__main__":
    sys.exit(main())

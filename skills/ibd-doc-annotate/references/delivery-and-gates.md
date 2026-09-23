# 交付物与门禁校验（delivery-and-gates.md）

> 本册是步骤 **3. 校验门禁（交付前必跑）** 与步骤 **4. 交付物** 的详规：命名规范、产物清单、门禁命令与逐项检查点。
> 门禁脚本属外部依赖 `ibd-doc-review`，**不随本包携带**；`<ibd-doc-review>` 为外部依赖 skill 的安装路径占位符（如 `<skills安装目录>/ibd-doc-review`，按本机技能安装位置替换）。

## 一、命名规范（日期戳 + 轮次，G3）

正式交付产物统一用模板 `<原文>_<YYYYMMDD>_v<N>_<形态>`（例：`佳宏新材_重大事项提示_20260906_v1_批注版.docx`），执行时用 `--out` 显式传入。轮次 N = 同一原文的第几次复核交付（首轮 v1；清单返工重交/下一遍复核升 v2…）。**同轮重跑覆盖**（同日同 vN 同形态直接覆盖，修 bug 重跑不产生新文件）；**跨轮必升 N**（旧轮产物保留可回溯，多轮对照与审计有据）。脚本默认输出简名（`<原文>_批注版.docx`）仅作快速试用，正式交付按本模板显式命名。

## 二、交付物清单

| 文件 | 说明 |
|---|---|
| `<原文>_<YYYYMMDD>_v<N>_批注版.docx/pdf` | 批注版第一交付物（Word 审阅面板 / PDF hover 弹注） |
| `<原文>_<YYYYMMDD>_v<N>_批注版_批注总览.md` | 双轨兜底：编号×类型×严重度×锚点摘要×作者×状态；未锚定条目列清单待人工定位 |
| `<原文>_<YYYYMMDD>_v<N>_批注版_批注总览.docx` | 总览 **Word 版**——与 md 同源同内容（双格式交付，2026-09-18 用户裁定：MD 供程序/检索、Word 供批阅流转）；由 `overview_to_docx.py` 同链路自动产出 |
| `<原文>_<YYYYMMDD>_v<N>_修订稿.docx` | 修订稿（revise=Word 修订模式可审阅接受/拒绝；clean=直接改好） |
| `<原文>_<YYYYMMDD>_v<N>_修订稿_clean.docx` | both 模式另出的干净版（接受全部修订后） |
| `<原文>_<YYYYMMDD>_v<N>_修订稿_修改清单.md` | 已修订 N 条（原文 → 改为）+ 待人工 M 条（原因+建议），编号同批注体系 |

## 三、门禁命令（交付前必跑）

```bash
# 批注版
python <ibd-doc-review>/scripts/check_annotations.py --input <批注版.docx> [--pdf <批注版.pdf> --expect <N>]
# 修订稿
python <ibd-doc-review>/scripts/check_revisions.py --input <修订稿.docx> --mode revise --expect <已修订N> [--report]
python <ibd-doc-review>/scripts/check_revisions.py --input <修订稿_clean.docx> --mode clean
```

## 四、检查项

批注 docx 侧检查：comments 条数 == cs/ce/ref 对数、每条 4 段无空行、标签/标题整行加粗、引导词加粗正文常规、编号前缀符合规范且唯一、四件套注册。

修订稿 revise 侧检查：ins==del 对、author 归责、id 成对唯一、delText/ins 非空、settings 开 trackRevisions、clean 化后 ins 文本落定；clean 侧：无修订标记残留。**任一 FAIL → 修正后重做，不交付**。

> 缺外部依赖时门禁不可用——按 `ops-notes.md` §依赖与工具的「断链自助指引」安装 `ibd-doc-review`（GitHub：Kianchales/ibd-skills 集合仓库 `skills/` 子目录）。

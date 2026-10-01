#!/usr/bin/env python3
"""法规原文取件器 —— 官方公开源 URL → 可读 Markdown（含质检）

定位：本脚本是 `ibd-legal-review` **L1 自举路径**的加速器（非必须件）。
      L1 依据源为「开放后端」：使用者本地法规库 → 官方公开源实时取 → 取不到标注「未核实」。
      本脚本承担中间一环：**给定官方公开源的 URL，取回可读全文**。

为什么不做「自动检索」：实测主流检索路径均不可靠（Bing 走 base64 跳转、
gov.cn 站内搜索 API 不返结果、部分部委站为 SPA）⇒ **URL 由使用者／AI 用公开检索定位后传入**，
本脚本只负责「取件 + 清洗 + 质检 + 落盘」这一段可机械化的部分。

用法：
    python fetch_law.py --name "中华人民共和国合伙企业法" --url "https://..."
    python fetch_law.py "中华人民共和国合伙企业法" "https://..." "生态环境部·国务院令736号（2016修订）"

参数：
    --name    法规名称（决定输出文件名）
    --url     官方公开源地址（HTML 正文页 或 含文字层的 PDF）
    --note    版本／来源备注 —— ⚠️ **务必写清所引版本**（施行日期或修订版次），
              这是**时点匹配**纪律的落地前提：同一部法多版本并存时，本字段是唯一版本线索。
    --out     输出目录（默认 ./legal-refs，**不硬编码任何本机路径**）
    --no-save 只抓取与质检，不落盘

设计约束（公布包标准 · 本包按公布包设计）：
    · **不硬编码任何本机路径**，不收任何私有库依赖
    · 仅用标准库；PDF 路径需可选依赖 `PyMuPDF`（fitz），缺失时明确提示而非静默失败
    · **质检不过不落盘**（防「静默拿到垃圾」）

质检判据：
    · 主判据：**行首条号 1→N 连续**（只数行首，天然排除条文内互引他法条号造成的假缺号）
    · 退路：行首条号过少（排版异常，如条文未独立成行）⇒ 退回「去重条号数」
    · 名录／表格类（本无条号）⇒ 以中文字数兜底
"""
import argparse
import gzip
import io
import os
import re
import ssl
import sys
import time
import urllib.request
import zlib

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
      'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36')
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
# 注：部分官方站（如国家法律法规数据库的下载域）证书过期 ⇒ 跳过校验是必要的工程妥协；
#     取回内容仍来自官方域，落盘时已在头部记录来源 URL 供人工复核。

CN = '零一二三四五六七八九十百千〇'
DIG = {'零': 0, '〇': 0, '一': 1, '二': 2, '三': 3, '四': 4,
       '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}

# 正文容器候选（命中最多中文的那个胜出）
START = [r'class=["\']?TRS_Editor', r'id=["\']?content["\']',
         r'class=["\'][^"\']*content_body_box', r'class=["\'][^"\']*article-content',
         r'class=["\'][^"\']*zoom', r'class=["\'][^"\']*detail-content']
# 正文结束候选
END = [r'class=["\'][^"\']*content_down', r'class=["\'][^"\']*share',
       r'id=["\']footer', r'class=["\'][^"\']*footer', r'<!--\s*底部',
       r'>\s*链接：', r'</body>']
# 页脚／导航噪声行
FOOTER = re.compile(
    r'^(主办单位|版权所有|网站标识码|京ICP备|京公网安备|国务院客户端|关于本网|网站声明|'
    r'联系我们|网站纠错|电脑版|客户端|小程序|微博|微信|邮箱|退出|注册|登录|中国政府网|'
    r'中央人民政府|驻外机构|澳门机构网站|首页\||\||相关稿件|扫一扫|分享|打印|关闭|'
    r'来源：|责任编辑|【打印】|【关闭】|链接：|全国人大$|全国政协|国家监察委员会|'
    r'最高人民法院$|最高人民检察院|国务院部门网站|地方政府网站|驻港澳机构网站|'
    r'国家法律法规数据库|中国政府网微信|国务院部门|地方政府)')


# ---------------- 取回 ----------------
def fetch(url):
    req = urllib.request.Request(
        url, headers={'User-Agent': UA, 'Accept-Encoding': 'gzip, deflate'})
    r = urllib.request.urlopen(req, timeout=90, context=CTX)
    raw = r.read()
    ct = (r.headers.get('Content-Type') or '').lower()
    ce = (r.headers.get('Content-Encoding') or '').lower()
    if 'gzip' in ce:
        raw = gzip.decompress(raw)
    elif 'deflate' in ce:
        try:
            raw = zlib.decompress(raw)
        except Exception:
            raw = zlib.decompress(raw, -zlib.MAX_WBITS)
    return raw, ct


def decode(raw):
    for enc in ('utf-8', 'gb18030', 'gbk'):
        try:
            return raw.decode(enc), enc
        except Exception:
            pass
    return raw.decode('utf-8', 'replace'), 'utf-8/replace'


# ---------------- HTML 路径 ----------------
def slice_content(html):
    h = re.sub(r'(?is)<(script|style|noscript|iframe)[^>]*>.*?</\1>', ' ', html)
    h = re.sub(r'(?is)<!--.*?-->', ' ', h)
    best = None
    for sp in START:
        for m in re.finditer(sp, h, re.I):
            s = m.start()
            e = len(h)
            for ep in END:
                m2 = re.search(ep, h[s:], re.I)
                if m2 and m2.start() > 200:
                    e = min(e, s + m2.start())
            body = h[s:e]
            cnt = len(re.findall(r'[\u4e00-\u9fff]', re.sub(r'<[^>]+>', '', body)))
            if best is None or cnt > best[0]:
                best = (cnt, body)
    return h if (best is None or best[0] < 200) else best[1]


def to_text(block):
    t = re.sub(r'(?i)<br\s*/?>', '\n', block)
    t = re.sub(r'(?i)</(p|div|h[1-6]|li|tr|td)>', '\n', t)
    t = re.sub(r'(?s)<[^>]+>', '', t)
    for a, b in (('&nbsp;', ' '), ('&amp;', '&'), ('&lt;', '<'), ('&gt;', '>'),
                 ('&quot;', '"'), ('&#39;', "'"), ('&ldquo;', '\u201c'),
                 ('&rdquo;', '\u201d'), ('&#160;', ' ')):
        t = t.replace(a, b)
    keep = []
    for l in (re.sub(r'[ \t\u3000]+', ' ', x).strip() for x in t.split('\n')):
        if not l:
            continue
        if re.match(r'^(class|id|style|align|target|href|src|width|height)=', l):
            continue
        if re.match(r'^</?[a-zA-Z]', l) or re.search(r'<[a-zA-Z/][^>]*$', l):
            l = re.sub(r'</?[a-zA-Z][^>]*$', '', l).strip()
            l = re.sub(r'^[a-zA-Z]+=[^>]*>', '', l).strip()
            if not l:
                continue
        if FOOTER.match(l):
            continue
        keep.append(l)
    return '\n'.join(keep)


# ---------------- PDF 路径 ----------------
def pdf_to_text(raw):
    tmp = os.path.join(os.environ.get('TEMP') or '/tmp', 'fetch_law_dl.pdf')
    with open(tmp, 'wb') as f:
        f.write(raw)
    try:
        import pymupdf as _pymupdf  # PyMuPDF（可选依赖 · 新名优先，避免弃用警告）
    except ImportError:
        try:
            import fitz as _pymupdf  # 旧名回落
        except ImportError:
            print('  ✗ 该 URL 返回 PDF，需可选依赖 PyMuPDF（pip install pymupdf）',
                  file=sys.stderr)
            return None
    doc = _pymupdf.open(tmp)
    txt = '\n'.join(p.get_text() for p in doc)
    doc.close()
    try:
        os.remove(tmp)
    except OSError:
        pass
    return txt


def reflow_pdf(txt):
    """PDF 抽取常按视觉行断句 ⇒ 行首为条号者起新段，其余拼接。"""
    out = []
    for l in (x.strip() for x in txt.split('\n')):
        if not l:
            continue
        if re.match(r'^第[%s\d]+[条款章节]' % CN, l):
            out.append(l)
        elif out:
            out[-1] += l
        else:
            out.append(l)
    return '\n'.join(out)


# ---------------- 数字与质检 ----------------
def cn2int(s):
    s = s.strip().replace('〇', '零')
    if s.isdigit():
        return int(s)
    total = 0
    for unit, base in (('千', 1000), ('百', 100)):
        if unit in s:
            a, b = s.split(unit, 1)
            total += (DIG.get(a, 1) if a else 1) * base
            s = b.lstrip('零')
    if '十' in s:
        a, b = s.split('十', 1)
        total += (DIG.get(a, 1) if a else 1) * 10 + (DIG.get(b, 0) if b else 0)
    elif s:
        total += DIG.get(s, 0)
    return total


def quality(txt):
    """返回 (中文字数, 条号数, 是否连续, 最大条号, 缺号列表, 章节数)"""
    occ = [cn2int(m) for m in re.findall(r'第([%s\d]+)条' % CN, txt)]
    cnt = len({n for n in occ if n > 0})
    head = []
    for l in txt.split('\n'):
        m = re.match(r'^第([%s\d]+)[条]' % CN, l.strip())
        if m:
            head.append(cn2int(m.group(1)))
    head = [n for n in head if n > 0]
    use_head = len(set(head)) >= max(3, cnt * 0.5)  # 行首式可用则优先
    seq, mx = (sorted(set(head)), max(head)) if head and use_head else (sorted({n for n in occ if n > 0}), (max(occ) if occ else 0))
    missing = [i for i in range(1, mx + 1) if i not in set(seq)] if mx else []
    chaps = len(set(cn2int(m) for m in re.findall(r'第([%s\d]+)章' % CN, txt)))
    cn = len(re.findall(r'[\u4e00-\u9fff]', txt))
    return cn, len(seq), (not missing and mx > 0), mx, missing, chaps


def main():
    ap = argparse.ArgumentParser(description='法规原文取件器（官方公开源 → 可读 Markdown）')
    ap.add_argument('name', nargs='?', help='法规名称')
    ap.add_argument('url', nargs='?', help='官方公开源 URL')
    ap.add_argument('note', nargs='?', default='', help='版本／来源备注')
    ap.add_argument('--name', dest='name_o')
    ap.add_argument('--url', dest='url_o')
    ap.add_argument('--note', dest='note_o')
    ap.add_argument('--out', default='./legal-refs', help='输出目录（默认 ./legal-refs）')
    ap.add_argument('--no-save', action='store_true', help='只质检不落盘')
    a = ap.parse_args()
    name = a.name_o or a.name
    url = a.url_o or a.url
    note = a.note_o or a.note or ''
    if not name or not url:
        ap.print_help()
        return 2

    print('=== %s ===' % name)
    try:
        raw, ct = fetch(url)
    except Exception as e:
        print('  ✗ 取回失败：%s' % e, file=sys.stderr)
        return 1
    print('  取回 %d 字节 ｜ Content-Type: %s' % (len(raw), ct or '(未知)'))

    is_pdf = ('pdf' in ct) or raw[:5] == b'%PDF-'
    if is_pdf:
        txt = pdf_to_text(raw)
        if txt is None:
            return 1
        body = reflow_pdf(txt)
    else:
        html, enc = decode(raw)
        body = to_text(slice_content(html))
        print('  解码 %s' % enc)

    # 尾部重复块截断（标题在后半段再现 ⇒ 多为「政策解读／相关链接」卡片）
    for key in (name, name.replace('中华人民共和国', '')):
        if len(key) < 4:
            continue
        pos = body.rfind('\n' + key + '\n')
        if pos > len(body) * 0.5:
            body = body[:pos].rstrip()
            break

    cn, arts, ok, mx, missing, chaps = quality(body)
    print('  正文 中文 %d 字 ｜ 条号 %d（最大 %d）｜ 章节 %d' % (cn, arts, mx, chaps))
    if mx and ok:
        print('  ✅ 条号 1→%d 连续' % mx)
    elif mx:
        print('  ⚠️ 条号不连续，缺：%s' % (missing[:20] if missing else '-'))
    else:
        print('  ℹ️ 无条号（名录／表格类？）以字数兜底')

    passed = ok or (not mx and cn > 3000)
    if not passed:
        print('  ✗ 质检未过（条号不连续且字数不足）⇒ **不落盘**', file=sys.stderr)
        if not mx and cn <= 3000:
            print('    提示：本页可能非正文（导航页／解读页）；请换官方正文页 URL')
        return 1

    if a.no_save:
        print('  （--no-save：未落盘）')
        return 0

    os.makedirs(a.out, exist_ok=True)
    safe = re.sub(r'[\\/:*?"<>|]', '_', name)
    p = os.path.join(a.out, safe + '.md')
    head = ('# %s\n\n> **来源**：%s\n> **抓取**：%s%s\n> **质检**：条号 %d（最大 %d，%s）· 章节 %d · 中文 %d 字\n\n---\n\n'
            % (name, url, time.strftime('%Y-%m-%d'),
               ('　**版本**：' + note) if note else '　**版本**：（未填 —— 时点匹配需此字段）',
               arts, mx, '连续' if ok else '不连续', chaps, cn))
    io.open(p, 'w', encoding='utf-8', newline='\n').write(head + body + '\n')
    print('  → %s' % os.path.abspath(p))
    return 0


if __name__ == '__main__':
    sys.exit(main())

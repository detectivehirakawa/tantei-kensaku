"""sitemap.xml を作る。lastmod は「ページの中身（見える文章・タイトル・説明文）が変わった日」（2026-11-18、運営者指示「日付は正しくして」）。

なぜ: 以前は git の最終コミット日を使っていたので、見た目の変わらない一括修正（例: リンクに rel=nofollow を付けた）でも
全ページが「今日更新」になり、Google がサイトマップの日付を信用しなくなるおそれがあった。

- 前回の日付と中身のハッシュは tantei-portal-data/sitemap_lastmod.json（{URL: [日付, ハッシュ]}）。
  ハッシュが同じなら日付はそのまま、違えば（または新しいページなら）今日（日本時間）にする。
- 中身 = <title>・meta description・本文の文字（script/style/タグ/空白を除く）。リンク属性・画像の ?v= などは含まない。
- 載せるページ: トップ・一覧・地図・コラム・市区町村・業者ページ。noindex・転送・フォーム（contact/edit など）は載せない。
- listed-hero.yml（承認のたび）で自動実行。手元では detective-portal/make_sitemap.py からも呼ばれる。

  python tantei-portal-tools/make_sitemap.py [公開フォルダ]
"""
import datetime
import glob
import hashlib
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = sys.argv[1] if len(sys.argv) > 1 else ROOT
SITE_URL = "https://tantei-kensaku.jp/"
STATE = os.path.join(PUB, "tantei-portal-data", "sitemap_lastmod.json")
EXCLUDE = {"contact.html", "linkcheck.html", "delete-account.html", "edit.html"}
NOINDEX = re.compile(r'<meta[^>]+name="robots"[^>]+content="[^"]*noindex', re.I)
DROP = re.compile(r"<(script|style|noscript|svg)\b.*?</\1>|<!--.*?-->", re.S | re.I)
TAG = re.compile(r"<[^>]+>")
DESC = re.compile(r'<meta\s+name="description"\s+content="([^"]*)"', re.I)
TITLE = re.compile(r"<title>(.*?)</title>", re.S | re.I)


def read(p):
    with open(p, encoding="utf-8", errors="ignore") as f:
        return f.read()


def content_hash(t):
    title = TITLE.search(t)
    desc = DESC.search(t)
    body = html.unescape(TAG.sub(" ", DROP.sub(" ", t)))
    text = " ".join([title.group(1) if title else "", desc.group(1) if desc else "", body])
    return hashlib.sha1(re.sub(r"\s+", " ", text).strip().encode("utf-8")).hexdigest()[:16]


def skip(t):
    return bool(NOINDEX.search(t[:6000])) or 'http-equiv="refresh"' in t[:3000]


def entries():
    out = []  # (url, path, priority)
    for p in sorted(glob.glob(os.path.join(PUB, "*.html"))):
        name = os.path.basename(p)
        if name in EXCLUDE:
            continue
        out.append((SITE_URL + ("" if name == "index.html" else name), p, "1.0" if name == "index.html" else "0.6"))
    for p in sorted(glob.glob(os.path.join(PUB, "column", "*.html"))):
        name = os.path.basename(p)
        out.append((SITE_URL + "column/" + ("" if name == "index.html" else name), p, "0.7" if name == "index.html" else "0.8"))
    for p in sorted(glob.glob(os.path.join(PUB, "*", "column", "*.html"))):
        d = os.path.basename(os.path.dirname(os.path.dirname(p)))
        name = os.path.basename(p)
        out.append((SITE_URL + d + "/column/" + ("" if name == "index.html" else name), p, "0.7" if name == "index.html" else "0.8"))
    for p in sorted(glob.glob(os.path.join(PUB, "*", "*.html"))):
        d = os.path.basename(os.path.dirname(p))
        if d in ("biz", "column", "img", "mypage"):
            continue
        out.append((SITE_URL + d + "/" + os.path.basename(p), p, "0.7"))
    for p in sorted(glob.glob(os.path.join(PUB, "biz", "*.html"))):
        out.append((SITE_URL + "biz/" + os.path.basename(p), p, "0.5"))
    return out


def main():
    today = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)).date().isoformat()
    try:
        state = json.load(open(STATE, encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    new_state, lines, changed = {}, [], 0
    for url, path, pr in entries():
        t = read(path)
        if skip(t):
            continue
        h = content_hash(t)
        prev = state.get(url)
        if prev and prev[1] == h:
            day = prev[0]
        else:
            day, changed = today, changed + 1
        new_state[url] = [day, h]
        lines.append(f"  <url><loc>{url}</loc><lastmod>{day}</lastmod><priority>{pr}</priority></url>")
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "\n".join(lines) + "\n</urlset>\n")
    out = os.path.join(PUB, "sitemap.xml")
    old = read(out) if os.path.exists(out) else ""
    if xml != old:
        with open(out, "w", encoding="utf-8", newline="\n") as f:
            f.write(xml)
    st = json.dumps(new_state, ensure_ascii=False, sort_keys=True, separators=(",", ":")).replace('],"', '],\n"') + "\n"
    if not os.path.exists(STATE) or read(STATE) != st:
        with open(STATE, "w", encoding="utf-8", newline="\n") as f:
            f.write(st)
    print(f"sitemap.xml: {len(lines)} URL / 中身が変わった・新しいページ {changed} 件（lastmod={today}）")


if __name__ == "__main__":
    main()

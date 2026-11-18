"""検索エンジン向けの設定がくずれていないかを点検する（2026-11-18、Search Consoleの指摘を受けて新設）。

点検すること（1つでも外れたら exit 1。seo-check.yml で push のたびに実行）:
1. contact.html（と同じ雛形の edit.html）に <meta name="robots" content="noindex"> がある
2. それ以外のページに noindex が無い（転送ページと mypage/ は除く。業者ページ・一覧・コラムは index 維持の方針）
3. robots.txt が noindex のページをブロックしていない（ブロックすると Google が noindex を読めない）
4. sitemap.xml に noindex・転送・存在しないページ・?付きURLが入っていない
5. 構造化データ（ld+json）がすべて JSON として読める。Dataset には name・description・license・creator がある
6. contact.html?… / edit.html?… へのリンクに rel="nofollow" がある（業者ページ1件に2本ずつ＝約15,000本の?付きURLにGoogleのクロールを使わせない）

手元でも:  python tantei-portal-tools/seo_check.py
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://tantei-kensaku.jp/"
MUST_NOINDEX = {"contact.html", "edit.html"}
NOINDEX_RE = re.compile(r'<meta[^>]+name="robots"[^>]+content="[^"]*noindex', re.I)
FORM_LINK_RE = re.compile(r'<a (?![^>]*\brel="[^"]*nofollow)[^>]*href="[^"]*(?:contact|edit)\.html\?')
LD_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
DATASET_NEED = ("name", "description", "license", "creator")

errors = []


def rel(p):
    return os.path.relpath(p, ROOT).replace(os.sep, "/")


def read(p):
    with open(p, encoding="utf-8", errors="ignore") as f:
        return f.read()


def is_redirect(t):
    return 'http-equiv="refresh"' in t[:3000]


def walk_ld(node, page):
    if isinstance(node, list):
        for x in node:
            walk_ld(x, page)
        return
    if not isinstance(node, dict):
        return
    types = node.get("@type")
    types = types if isinstance(types, list) else [types]
    if "Dataset" in types:
        miss = [k for k in DATASET_NEED if not node.get(k)]
        if miss:
            errors.append(f"{page}: Dataset に {', '.join(miss)} がない")
    for v in node.values():
        if isinstance(v, (dict, list)):
            walk_ld(v, page)


def main():
    pages = [p for p in glob.glob(os.path.join(ROOT, "**", "*.html"), recursive=True)
             if not rel(p).startswith((".", "node_modules/", "img/"))]
    noindex = set()
    for p in pages:
        r, t = rel(p), read(p)
        head = t[:6000]
        ni = bool(NOINDEX_RE.search(head))
        if ni:
            noindex.add(r)
        if r in MUST_NOINDEX and not ni:
            errors.append(f"{r}: noindex がない")
        if ni and r not in MUST_NOINDEX and not is_redirect(t) and not r.startswith("mypage/"):
            errors.append(f"{r}: noindex が付いている（index 維持のはず）")
        if FORM_LINK_RE.search(t):
            errors.append(f"{r}: フォームへの?付きリンクに nofollow がない")
        for m in LD_RE.finditer(t):
            try:
                walk_ld(json.loads(m.group(1).replace("<\\/", "</")), r)
            except ValueError as e:
                errors.append(f"{r}: 構造化データが JSON として読めない（{e}）")

    robots = read(os.path.join(ROOT, "robots.txt"))
    for line in robots.splitlines():
        m = re.match(r"\s*Disallow:\s*(\S+)", line, re.I)
        if not m:
            continue
        rule = m.group(1).lstrip("/")
        for r in sorted(noindex | MUST_NOINDEX):
            if r.startswith(rule.rstrip("*")):
                errors.append(f"robots.txt の「{line.strip()}」が noindex の {r} をブロックしている")

    locs = re.findall(r"<loc>([^<]+)</loc>", read(os.path.join(ROOT, "sitemap.xml")))
    for u in locs:
        if not u.startswith(SITE):
            errors.append(f"sitemap: 別ドメイン {u}")
            continue
        path = u[len(SITE):]
        if "?" in path or "contact.html" in path:
            errors.append(f"sitemap: 載せないURL {u}")
            continue
        f = os.path.join(ROOT, path or "index.html")
        if path.endswith("/"):
            f = os.path.join(f, "index.html")
        if not os.path.exists(f):
            errors.append(f"sitemap: ページが無い {u}")
            continue
        t = read(f)
        if NOINDEX_RE.search(t[:6000]) or is_redirect(t):
            errors.append(f"sitemap: noindex か転送のページ {u}")

    print(f"点検: ページ {len(pages)} 件 / sitemap {len(locs)} 件 / noindex {len(noindex)} 件")
    if errors:
        for e in errors[:200]:
            print("NG", e)
        print(f"問題 {len(errors)} 件")
        sys.exit(1)
    print("問題なし")


if __name__ == "__main__":
    main()

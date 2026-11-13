"""未掲載の業者ページに「ホームページで確認できた調査項目」を書き込む（2026-11-14）。

データ: tantei-portal-data/biz_web.json
  { "<届出番号>": { "types": ["浮気調査", ...],      … トップ検索の「調査の種類」と同じ7分類
                    "other_types": ["いじめ調査", ...], … 7分類に入らない項目（原文の短い名称）
                    "checked": "2026-11-14",            … 確認した日
                    "url": "https://..." } }            … 確認したサイト（ページには出さない・記録用）

- そのサイトに届出番号が載っていて、本人のサイトだと確かめられたものだけを入れる（推測で入れない）。
- 掲載済み（permitted.json）の業者は、業者が入力した「対応可能な調査」を使うので書き込まない。
- 書き込む位置は <!--/biz-facts--> の直後。<!--hp-types-->〜<!--/hp-types--> で囲み、何度実行しても同じ結果になる。
- 業者が掲載を申し込んで承認されると GAS がカードを作り直す。そのあとは掲載済みとして扱うので、この欄は消す。

  python tantei-portal-tools/render_hp_types.py
"""
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "tantei-portal-data")
BIZ = os.path.join(ROOT, "biz")
OPEN, CLOSE = "<!--hp-types-->", "<!--/hp-types-->"
ANCHOR = "<!--/biz-facts-->"
BLOCK_RE = re.compile(re.escape(OPEN) + r".*?" + re.escape(CLOSE), re.S)

CHIP = ("display:inline-block;margin:0 6px 6px 0;padding:4px 11px;border-radius:999px;font-size:.85rem;"
        "font-weight:700;background:#eef4fc;color:#0d3f8f;border:1px solid #c9daf2")
CHIP2 = ("display:inline-block;margin:0 6px 6px 0;padding:4px 11px;border-radius:999px;font-size:.85rem;"
         "background:#f5f6f8;color:#3c4c60;border:1px solid #dde2ea")


def esc(s):
    return html.escape(str(s or ""), quote=True)


def block(name, e):
    types = [t for t in (e.get("types") or []) if t]
    others = [t for t in (e.get("other_types") or []) if t]
    if not types and not others:
        return ""
    chips = "".join('<span style="%s">%s</span>' % (CHIP, esc(t)) for t in types)
    chips += "".join('<span style="%s">%s</span>' % (CHIP2, esc(t)) for t in others)
    checked = esc(e.get("checked") or "")
    y, m, d = (checked.split("-") + ["", "", ""])[:3]
    when = ("%s年%d月%d日" % (y, int(m), int(d))) if y and m and d else checked
    return (OPEN + '<section class="bf"><h2>%sの調査項目（ホームページで確認）</h2>'
            '<div style="margin:2px 0 4px">%s</div>'
            '<p>当サイトが%sに、この事務所のホームページ（届出番号の表示があるもの）で確認できた調査項目です。'
            '料金や対応の詳細は、事務所に直接ご確認ください。</p></section>' % (esc(name), chips, when) + CLOSE)


def main():
    web = json.load(open(os.path.join(DATA, "biz_web.json"), encoding="utf-8"))
    permitted = set(json.load(open(os.path.join(DATA, "permitted.json"), encoding="utf-8")))
    changed = 0
    for fn in sorted(os.listdir(BIZ)):
        if not fn.endswith(".html"):
            continue
        bid = fn[:-5]
        path = os.path.join(BIZ, fn)
        page = open(path, encoding="utf-8", newline="").read()
        e = web.get(bid)
        if not e and OPEN not in page:
            continue
        new = BLOCK_RE.sub("", page)
        if e and bid not in permitted and ANCHOR in new:
            m = re.search(r"<h1>(.*?)</h1>", new, flags=re.S)
            name = html.unescape(re.sub(r"<[^>]+>", "", m.group(1)).strip()) if m else bid
            b = block(name, e)
            if b:
                i = new.find(ANCHOR) + len(ANCHOR)
                new = new[:i] + b + new[i:]
        if new != page:
            open(path, "w", encoding="utf-8", newline="").write(new)
            changed += 1
            print(bid, "更新")
    print("更新したページ:", changed)


if __name__ == "__main__":
    sys.exit(main())

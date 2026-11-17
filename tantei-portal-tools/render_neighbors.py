"""業者ページの届出情報の枠（<!--biz-facts-->）にある「〇〇のほかの届出業者」の一覧を、
all.json から作り直す（2026-11-18、運営者指示「承認の自動処理に組み込んで」）。

  python tantei-portal-tools/render_neighbors.py

- 掲載の承認で屋号（事務所名）が変わったとき、GAS は本人のページ・一覧ページの名前は直すが、
  ほかの業者ページの「同じ市区町村の業者」の一覧は直さない。ここで全ページをそろえる。
- 並びは同じ市区町村の業者を届出番号順に並べ、本人の次から8件（最後まで行ったら先頭に戻る）。
  見出しの件数は「8件を表示・全N件」（N は本人を含む市区町村の件数）。
- 中身が変わったページだけ書き換え、そのページの「このページの更新日」を今日（日本時間）にする。
- 何度実行しても同じ結果になる。render_display_no.py・render_kanri_no.py・render_llmo.py より前に実行する。
"""
import collections
import datetime
import glob
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIST_RE = re.compile(r"<h3>([^<]*?)のほかの届出業者（\d+件を表示・全\d+件）</h3><ul>.*?</ul>", re.S)
DATE_RE = re.compile(r"(このページの更新日</dt><dd>)[^<]*(</dd>)")


def esc(s):
    return html.escape(s, quote=True)


def main():
    with open(os.path.join(ROOT, "all.json"), encoding="utf-8") as f:
        rows = json.load(f)
    by_city = collections.defaultdict(list)
    for e in rows:
        if e.get("c"):
            by_city[e["c"]].append(e)
    for c in by_city:
        by_city[c].sort(key=lambda e: e["i"])
    pos = {e["i"]: (c, k) for c, lst in by_city.items() for k, e in enumerate(lst)}

    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    today = f"{now.year}年{now.month}月{now.day}日"
    changed = 0
    for path in glob.glob(os.path.join(ROOT, "biz", "*.html")):
        i = os.path.basename(path)[:-5]
        if i not in pos:
            continue
        with open(path, encoding="utf-8") as f:
            text = f.read()
        m = LIST_RE.search(text)
        if not m:
            continue
        c, k = pos[i]
        lst = by_city[c]
        if len(lst) < 2:
            continue
        others = [lst[(k + j) % len(lst)] for j in range(1, len(lst))][:8]
        new = (f"<h3>{m.group(1)}のほかの届出業者（{len(others)}件を表示・全{len(lst)}件）</h3><ul>"
               + "".join(f'<li><a href="./{o["i"]}.html">{esc(o["n"])}</a>（届出番号 {o["i"]}）</li>' for o in others)
               + "</ul>")
        if new == m.group(0):
            continue
        text = text[:m.start()] + new + text[m.end():]
        text = DATE_RE.sub(lambda d: d.group(1) + today + d.group(2), text, count=1)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        changed += 1
    print(f"render_neighbors: {changed} ページを更新")


if __name__ == "__main__":
    main()

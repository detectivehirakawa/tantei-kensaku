"""都道府県・市区町村ページなどに書いてある「都道府県の件数」を all.json の実数にそろえる（2026-11-27）。

なぜ: 業者の追加・削除のあと、ページ上部の「〇〇県 316件」や地方の都道府県リスト（<small>315</small>）が
古い数字のまま残り、同じページの中で 313件・315件・316件と食い違っていた（794ページ中566ページ）。

直す場所（業者ページ biz/ は対象外）
  1. <span class="t-stat">〇〇県 123件</span>
  2. <a href="…/xxx.html" …>〇〇県<small>123</small></a>

何度実行しても同じ結果になる。listed-hero.yml（承認・all.json の更新のたび）で自動実行。

  python tantei-portal-tools/render_counts.py
"""
import glob
import json
import os
import re
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAT = re.compile(r'(<span class="t-stat">)([^ <]+?[都道府県]) (\d+)(件</span>)')
MINI = re.compile(r'(<a href="[^"]*\.html"[^>]*>)([^<]+?[都道府県])(<small>)(\d+)(</small>)')


def main():
    with open(os.path.join(ROOT, "all.json"), encoding="utf-8") as f:
        cnt = Counter(r["p"] for r in json.load(f))
    pages = glob.glob(os.path.join(ROOT, "*.html")) + glob.glob(os.path.join(ROOT, "*", "*.html")) \
        + glob.glob(os.path.join(ROOT, "*", "column", "*.html"))
    changed = 0
    for p in pages:
        if os.path.basename(os.path.dirname(p)) in ("biz", "img", "mypage"):
            continue
        with open(p, encoding="utf-8", newline="") as f:
            s = f.read()
        t = STAT.sub(lambda m: f"{m.group(1)}{m.group(2)} {cnt[m.group(2)]}{m.group(4)}" if m.group(2) in cnt else m.group(0), s)
        t = MINI.sub(lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}{cnt[m.group(2)]}{m.group(5)}" if m.group(2) in cnt else m.group(0), t)
        if t != s:
            with open(p, "w", encoding="utf-8", newline="") as f:
                f.write(t)
            changed += 1
    print(f"render_counts: 都道府県の件数を直したページ {changed} 件")


if __name__ == "__main__":
    main()

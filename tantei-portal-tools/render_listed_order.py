"""都道府県一覧・市区町村ページで、上にまとめて出す掲載済みの探偵社（pref-row-featured の行）を、
掲載内容の文字の量が多い順に並べ替える（2026-11-19、運営者指示「文字の量で掲載順位が変わるように」）。

- 文字の量 = biz_extra.json のうち、ページに文章として出る項目の文字数の合計（URL・写真・電話番号・日付は数えない。空白は数えない）。
- 同じ文字数なら今の並び順のまま。掲載済みの行より下（未掲載の業者）は触らない。
- 何度実行しても同じ結果になる。listed-hero.yml と listed_all.sh で毎回実行（承認で biz_extra.json が変われば自動で並び直る）。
"""
import glob
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXT_KEYS = ("catch", "service", "types", "area", "price", "hours", "methods", "corpName", "founded", "staff",
             "payment", "successFee", "expenses", "estimate", "lawyer", "groups", "awards")
ROW = re.compile(r'<tr id="n(\d+)" class="pref-row-featured"[^>]*>.*?</tr>\n?', re.S)


def text_len(e):
    n = 0
    for k in TEXT_KEYS:
        v = (e or {}).get(k)
        if isinstance(v, list):
            v = "".join(map(str, v))
        if isinstance(v, str):
            n += len(re.sub(r"\s", "", re.sub(r"【[^】]*】", "", v)))
    return n


def main():
    extra = json.load(open(os.path.join(ROOT, "tantei-portal-data", "biz_extra.json"), encoding="utf-8"))
    pages = glob.glob(os.path.join(ROOT, "*.html")) + glob.glob(os.path.join(ROOT, "*", "*.html"))
    changed = 0
    for p in pages:
        if os.sep + "biz" + os.sep in p:
            continue
        t = open(p, encoding="utf-8").read()
        rows = list(ROW.finditer(t))
        if len(rows) < 2:
            continue
        # 行が続いている部分（間に別の行がない）だけを並べ替える
        if any(rows[k].end() != rows[k + 1].start() for k in range(len(rows) - 1)):
            print("!! 掲載済みの行が連続していない:", os.path.relpath(p, ROOT))
            continue
        old = [m.group(0) for m in rows]
        ids = [m.group(1) for m in rows]
        order = sorted(range(len(old)), key=lambda k: (-text_len(extra.get(ids[k])), k))
        new = [old[k] for k in order]
        # 最後の行の改行の有無をそろえる
        new = [r if r.endswith("\n") else r + "\n" for r in new]
        if not old[-1].endswith("\n"):
            new[-1] = new[-1][:-1]
        if new == old:
            continue
        t = t[:rows[0].start()] + "".join(new) + t[rows[-1].end():]
        open(p, "w", encoding="utf-8", newline="").write(t)
        changed += 1
    print("掲載済みの並び替え:", changed, "ページ")


if __name__ == "__main__":
    main()

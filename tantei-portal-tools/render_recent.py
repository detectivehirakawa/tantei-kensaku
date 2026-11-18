"""トップの「最近掲載された探偵社」欄を書き出す（2026-11-18、運営者指示。よくある質問の上に置く）。

- 掲載日は tantei-portal-data/listed_dates.json（{届出番号: "YYYY-MM-DD"}）。permitted.json に新しく
  入った番号は、このスクリプトを最初に実行した日（日本時間）を掲載日として書き足す。
  （2026-11-11以前からの掲載は、リポジトリ移転日の 2026-11-11 になっている）
- 表示するのは掲載から DAYS 日以内・新しい順に最大 MAX 件。DAYS 日以内が MIN 件に満たないときは、
  古いものから MIN 件まで補って、欄が空にならないようにする。
- index.html の <!--recent-listed:start--> 〜 <!--recent-listed:end--> を書き換える。目印が無ければ
  「よくある質問」の直前に入れる（build_site.py で作り直しても、次の実行で元に戻る）。
- listed-hero.yml の中で毎回実行（承認されれば自動）。何度実行しても同じ結果になる。
"""
import datetime
import hashlib
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "tantei-portal-data")
DATES = os.path.join(DATA, "listed_dates.json")
INDEX = os.path.join(ROOT, "index.html")
DAYS, MAX, MIN = 30, 12, 4
START, END = "<!--recent-listed:start-->", "<!--recent-listed:end-->"
FAQ_RE = re.compile(r'<section class="t-box"><h2 class="t-h">(?:(?!</h2>).)*<b>よくある質問</b>', re.S)
PREF_RE = r"(東京都|北海道|(?:京都|大阪)府|.{2,3}県)"
CITY_RE = re.compile(PREF_RE + r"?(.+?郡.+?[町村]|.+?市.+?区|.+?[市区町村])")

CSS = """<style>
.t-recent-list{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px}
.t-recent-list a{display:flex;flex-direction:column;height:100%;border:1px solid var(--t-line,#dde5f0);border-radius:8px;overflow:hidden;background:#fff;color:inherit;text-decoration:none;transition:box-shadow .15s}
.t-recent-list a:hover{box-shadow:0 4px 14px rgba(20,33,61,.12)}
.t-recent-list img{display:block;width:100%;height:auto;aspect-ratio:16/9;object-fit:contain;background:#eef2f7}
.t-recent-list .ph{display:block;width:100%;aspect-ratio:16/9;background:#fff;border-bottom:1px solid var(--t-line,#dde5f0)}
.t-recent-list .bd{padding:10px 12px 12px;display:flex;flex-direction:column;gap:4px}
.t-recent-list .dt{font-size:.72rem;color:#0f7a3d;font-weight:700}
.t-recent-list .nm{font-weight:700;font-size:.95rem;line-height:1.4}
.t-recent-list .ad{font-size:.75rem;color:#5b6675}
.t-recent-list .cp{font-size:.78rem;color:#33404f;line-height:1.5;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
@media(max-width:760px){.t-recent-list{display:flex;overflow-x:auto;scroll-snap-type:x mandatory;padding-bottom:8px;-webkit-overflow-scrolling:touch}.t-recent-list li{flex:0 0 72%;scroll-snap-align:start}}
</style>"""
ICON = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true"><path d="M12 3l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.4 6.8 19.1l1-5.8L3.5 9.2l5.9-.9z"/></svg>')


def load(name, default):
    try:
        with open(os.path.join(DATA, name), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def city_of(addr, pref):
    s = re.sub(r"〒?\s*\d{3}[-‐－ー−]?\d{4}", " ", str(addr or "")).replace("　", " ").strip()
    m = CITY_RE.match(s.split(" ")[0]) if s else None
    if not m:
        return pref
    return (m.group(1) or pref) + m.group(2)


def main():
    today = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)).date()
    permitted = load("permitted.json", [])
    dates = load("listed_dates.json", {})
    new_dates = {i: dates.get(i) or today.isoformat() for i in permitted}
    if new_dates != dates:
        with open(DATES, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(new_dates, ensure_ascii=False, indent=1, sort_keys=True) + "\n")

    with open(os.path.join(ROOT, "all.json"), encoding="utf-8") as f:
        rows = {r["i"]: r for r in json.load(f) if r.get("m") == 0}
    extra = load("biz_extra.json", {})
    profiles = load("biz_profile.json", {})
    order = sorted((i for i in new_dates if i in rows), key=lambda i: (new_dates[i], permitted.index(i)), reverse=True)
    since = (today - datetime.timedelta(days=DAYS)).isoformat()
    pick = [i for i in order if new_dates[i] >= since][:MAX]
    if len(pick) < MIN:
        pick = order[:MIN]

    items = []
    for i in pick:
        r, e = rows[i], extra.get(i) or {}
        name = e.get("dispName") or r.get("n", "")
        place = city_of(e.get("officeAddress") or r.get("a", ""), r.get("p", ""))
        d = datetime.date.fromisoformat(new_dates[i])
        f = os.path.join(ROOT, "img", "listed", f"{i}.webp")
        ver = hashlib.md5(open(f, "rb").read()).hexdigest()[:8] if os.path.exists(f) else ""
        if (profiles.get(i) or {}).get("card_image") is False or not ver:
            img = '<span class="ph" aria-hidden="true"></span>'  # 画像なし＝白い枠（biz_profile.json の card_image: false で指定）
        else:
            img = f'<img src="./img/listed/{i}.webp?v={ver}" alt="" width="320" height="180" loading="lazy" decoding="async">'
        catch = str(e.get("catch") or "").strip()
        items.append(
            f'<li><a href="./biz/{i}.html">{img}<span class="bd"><span class="dt">{d.month}月{d.day}日 掲載</span>'
            f'<span class="nm">{html.escape(name)}</span><span class="ad">{html.escape(place)}</span>'
            + (f'<span class="cp">{html.escape(catch)}</span>' if catch else "") + "</span></a></li>")
    block = (f'{START}<section class="t-box t-recent" id="recent">{CSS}<h2 class="t-h">{ICON}<b>最近掲載された探偵社</b>'
             f'<i>掲載から{DAYS}日以内の探偵事務所を、新しい順に表示します</i></h2>'
             f'<ul class="t-recent-list">{"".join(items)}</ul></section>{END}\n\n')

    with open(INDEX, encoding="utf-8") as f:
        page = f.read()
    if START in page and END in page:
        a, b = page.index(START), page.index(END) + len(END)
        rest = page[b:].lstrip("\n")
        out = page[:a] + block + rest
    else:
        m = FAQ_RE.search(page)
        if not m:
            raise SystemExit("index.html に「よくある質問」の欄が見つからない")
        out = page[:m.start()] + block + page[m.start():]
    if out != page:
        with open(INDEX, "w", encoding="utf-8", newline="") as f:
            f.write(out)
    print("最近掲載された探偵社:", len(items), "件", "（更新）" if out != page else "（変更なし）")


if __name__ == "__main__":
    main()

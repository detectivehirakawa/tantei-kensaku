"""市区町村ページに、その市区町村だけの情報を書き足す（2026-11-16 運営者指示「〇〇市 探偵」対策）。

  python tantei-portal-tools/render_city_extra.py            # ENABLED の都道府県だけ
  python tantei-portal-tools/render_city_extra.py saitama    # 指定した都道府県だけ

書き足す内容（すべて all.json / geo.json / family_courts.json から作る。APIは呼ばない）
  1. 届出の時期：その市区町村の業者が、いつ届出をしたか（届出番号の3〜4桁目＝西暦の下2桁）
  2. 近くの市区町村：業者の位置の平均から距離を出し、近い順に（県をまたいでもよい）
  3. 家庭裁判所：離婚調停などを扱う家庭裁判所（family_courts.json にある県だけ）
  4. よくある質問に2問（画面とFAQPageの構造化データの両方）

<!--city-extra--> 〜 <!--/city-extra--> の間を毎回作り直すので、何度実行しても同じ結果になる。
GAS の承認処理は一覧の行だけを差し替えるので、この部分は消えない。フルビルドで消えても listed-hero.yml が書き戻す。
"""
import json
import math
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "tantei-portal-data")
ENABLED = "ALL"
NEAR_KM = 25
NEAR_MAX = 6
MARK_A, MARK_B = "<!--city-extra-->", "<!--/city-extra-->"


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def page_name(path):
    with open(path, encoding="utf-8") as f:
        head = f.read(4000)
    m = re.search(r"<title>(.*?)の探偵事務所", head)
    return m.group(1) if m else None


def year_of(no):
    y = int(no[2:4])
    return 2000 + y


def dist(a, b):
    lat = math.radians((a[0] + b[0]) / 2)
    dx = (a[1] - b[1]) * 111.32 * math.cos(lat)
    dy = (a[0] - b[0]) * 110.57
    return math.hypot(dx, dy)


def court_for(courts, name):
    """name（例：三郷市・比企郡川島町・さいたま市大宮区）の家庭裁判所。見つからなければ None。"""
    if not courts:
        return None
    nz = lambda x: x.replace("ヶ", "ケ").replace("ヵ", "カ")
    name = nz(name)
    best = None
    for r in courts["rows"]:
        for t in map(nz, r["names"]):
            if name == t:
                return r
            if t.endswith(("町", "村")) and name.endswith(t) and best is None:
                best = r
    if best:
        return best
    for r in courts["rows"]:
        for t in map(nz, r["names"] + r["partial"]):
            if t.endswith("市") and name.startswith(t):
                return r
    return None


def build(pref_slugs):
    rows = load(os.path.join(ROOT, "all.json"))
    geo = load(os.path.join(ROOT, "geo.json"))
    courts_all = load(os.path.join(DATA, "family_courts.json"))
    by_city = defaultdict(list)
    for r in rows:
        if r.get("c"):
            by_city[r["c"]].append(r)
    # 市区町村ページがあるものだけ（名前はページのtitleから）
    pages = {}
    for c in by_city:
        p = os.path.join(ROOT, c + ".html")
        if os.path.exists(p):
            nm = page_name(p)
            if nm:
                pages[c] = nm
    cent = {}
    for c, rs in by_city.items():
        pts = [(geo[r["i"]]["lat"], geo[r["i"]]["lng"]) for r in rs if r["i"] in geo]
        if pts:
            # 位置の取り違え（別の県に飛んでいる等）に引きずられないよう、中央値から15km以内だけで平均する
            med = (sorted(p[0] for p in pts)[len(pts) // 2], sorted(p[1] for p in pts)[len(pts) // 2])
            ok = [p for p in pts if dist(p, med) <= 15]
            # 半分以上が中央値の近くに集まっていない市区町村は、位置が当てにならないので距離に使わない
            if len(ok) * 2 <= len(pts) or (len(pts) == 2 and dist(pts[0], pts[1]) > 15):
                continue
            cent[c] = (sum(p[0] for p in ok) / len(ok), sum(p[1] for p in ok) / len(ok))
    done = 0
    for c, name in pages.items():
        pref = c.split("/")[0]
        if pref_slugs != "ALL" and pref not in pref_slugs:
            continue
        rs = by_city[c]
        n = len(rs)
        years = sorted(year_of(r["i"]) for r in rs)
        recent = sum(1 for y in years if y >= 2024)
        b1 = sum(1 for y in years if y <= 2010)
        b2 = sum(1 for y in years if 2011 <= y <= 2019)
        b3 = sum(1 for y in years if 2020 <= y <= 2023)
        # 近くの市区町村
        near = []
        if c in cent:
            for o, nm in pages.items():
                if o == c or o not in cent:
                    continue
                d = dist(cent[c], cent[o])
                if d <= NEAR_KM:
                    near.append((d, o, nm))
            near.sort()
            near = near[:NEAR_MAX]
        pre = "../"
        bar = lambda k, v: (f'<div class="cx-bar"><span class="cx-k">{k}</span><span class="cx-t"><i style="width:{round(v / n * 100)}%"></i></span><span class="cx-v">{v}件</span></div>')
        sec = [MARK_A, '<section class="t-box city-extra">',
               '<style>.city-extra p{line-height:1.9;margin:.4em 0 .9em}.city-extra .cx-bar{display:flex;align-items:center;gap:10px;margin:6px 0;font-size:.9rem}.city-extra .cx-k{width:8.5em;flex:none;color:var(--ink,#1a2430)}.city-extra .cx-t{flex:1;height:12px;background:#e8eef6;border-radius:6px;overflow:hidden}.city-extra .cx-t i{display:block;height:100%;background:#1668d8}.city-extra .cx-v{width:3.5em;text-align:right;font-weight:700}.city-extra h3{font-size:1rem;margin:1.4em 0 .5em;color:#0f4fa8}.city-extra .cx-near{display:flex;flex-wrap:wrap;gap:8px;margin:0;padding:0;list-style:none}.city-extra .cx-near a{display:inline-block;border:1px solid #c9d3df;border-radius:999px;padding:6px 12px;text-decoration:none;font-size:.88rem}.city-extra .cx-near small{color:#4a5665;margin-left:4px}.city-extra .cx-court{background:#f4f8fd;border-left:3px solid #1668d8;padding:10px 14px;margin:.6em 0}</style>',
               f'<h2 class="t-sub-h">データで見る{esc(name)}の探偵事務所</h2>',
               f'<h3>届出をした時期</h3>',
               f'<p>{esc(name)}の届出業者{n}件が、探偵業の届出をした年の内訳です（届出番号の3〜4桁目から集計）。'
               + (f'<b>2024年以降に届出をした新しい事務所が{recent}件</b>あります。' if recent else '2024年以降に届出をした事務所はありません。')
               + f'いちばん古い届出は{years[0]}年です。</p>',
               bar("2010年まで", b1), bar("2011〜2019年", b2), bar("2020〜2023年", b3), bar("2024年以降", recent),
               '<p style="font-size:.82rem;color:#4a5665">届出の年が古いほど良いというわけではありません。移転や法人化で届出をし直した事務所もあります。</p>']
        if near:
            sec.append(f'<h3>{esc(name)}の近くの市区町村で探す</h3>')
            sec.append(f'<p>浮気調査は、調査をする場所の近くの事務所に頼むと交通費を抑えやすくなります。{esc(name)}から近い市区町村の届出業者です（事務所の位置から求めたおおよその距離）。</p>')
            sec.append('<ul class="cx-near">' + "".join(
                f'<li><a href="{pre}{o}.html">{esc(nm)}<small>{len(by_city[o])}件・約{max(1, round(d))}km</small></a></li>' for d, o, nm in near) + '</ul>')
        court = court_for(courts_all.get(pref), name)
        if court:
            src = courts_all[pref]["source"]
            cname = court["court"]
            desk = f'（窓口：{court["desk"]}）' if court.get("desk") else ""
            sec.append(f'<h3>{esc(name)}を管轄する家庭裁判所</h3>')
            sec.append(f'<div class="cx-court"><b>{esc(cname)}</b>{esc(desk)}</div>')
            sec.append(f'<p>浮気の証拠をもとに離婚調停などを申し立てるときの窓口です。調停は原則として<b>相手方の住所地</b>を管轄する家庭裁判所に申し立てるため、相手が別の地域に住んでいる場合は申立先が変わります。管轄は<a href="{src}" target="_blank" rel="noopener">裁判所の管轄区域表</a>で確認できます。</p>')
        sec.append('</section>')
        sec.append(MARK_B)
        block = "\n".join(sec)

        faqs = []
        if near:
            top = sorted(near, key=lambda t: -len(by_city[t[1]]))[0]
            faqs.append((f"{name}の近くで、探偵事務所が多いのはどこですか？",
                         f"{name}から約{NEAR_KM}km以内では、{top[2]}に{len(by_city[top[1]])}件の届出業者があります。"
                         f"ほかに{'、'.join(t[2] for t in near if t[1] != top[1])[:80]}などにも届出業者があります。"))
        if court:
            faqs.append((f"{name}に住んでいる場合、離婚調停はどこの家庭裁判所ですか？",
                         f"{name}を管轄するのは{court['court']}{('（窓口：' + court['desk'] + '）') if court.get('desk') else ''}です。ただし、調停は原則として相手方の住所地を管轄する家庭裁判所に申し立てるため、相手が別の地域に住んでいる場合は申立先が変わります。"))

        p = os.path.join(ROOT, c + ".html")
        with open(p, encoding="utf-8", newline="") as f:
            s = f.read().replace(chr(13) + chr(10), chr(10)).replace(chr(13), chr(10))
        s = re.sub(re.escape(MARK_A) + r".*?" + re.escape(MARK_B) + r"\n?", "", s, flags=re.S)
        anchor = re.search(r'<section class="t-box city-text">.*?</section>\n?', s, re.S)
        if not anchor:
            continue
        s = s[:anchor.end()] + block + "\n" + s[anchor.end():]
        # FAQ（画面）
        s = re.sub(r'<details data-cx="1">.*?</details>', "", s, flags=re.S)
        fhtml = "".join(f'<details data-cx="1"><summary>{esc(q)}</summary><p>{esc(a)}</p></details>' for q, a in faqs)
        m = re.search(r'(<section class="t-box city-faq">.*?)(\n</section>)', s, re.S)
        if m and fhtml:
            s = s[:m.end(1)] + fhtml + s[m.end(1):]
        # FAQ（構造化データ）
        def fix_ld(mm):
            try:
                ld = json.loads(mm.group(1))
            except Exception:
                return mm.group(0)
            items = ld if isinstance(ld, list) else [ld]
            for it in items:
                if isinstance(it, dict) and it.get("@type") == "FAQPage":
                    names = {q for q, _ in faqs}
                    me = [e for e in it.get("mainEntity", []) if e.get("name") not in names and not e.get("name", "").startswith(f"{name}の近くで") and not e.get("name", "").startswith(f"{name}に住んでいる場合")]
                    me += [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]
                    it["mainEntity"] = me
            out = json.dumps(ld, ensure_ascii=False).replace("</", "<\\/")
            return f'<script type="application/ld+json">{out}</script>'
        s = re.sub(r'<script type="application/ld\+json">(.*?)</script>', fix_ld, s, flags=re.S)
        with open(p, "w", encoding="utf-8", newline="") as f:
            f.write(s)
        done += 1
    print(f"city-extra: {done} pages ({pref_slugs if pref_slugs == 'ALL' else ', '.join(pref_slugs)})")


if __name__ == "__main__":
    build(sys.argv[1:] or ENABLED)

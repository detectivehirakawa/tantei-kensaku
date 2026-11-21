"""都道府県ページに、その都道府県だけの情報を書き足す（2026-11-22 案。運営者の確認待ち）。

  python tantei-portal-tools/render_pref_extra.py --preview tokyo <出力先.html>   # 公開ファイルは変えず、確認用のHTMLを作る
  python tantei-portal-tools/render_pref_extra.py                                   # ENABLED の都道府県に書き込む（今は空＝何もしない）

書き足す内容（all.json・pref_population.json・family_courts.json から作る。APIは呼ばない）
  1. 要点（件数・全国順位・全国に占める割合・人口10万人あたり）
  2. 届出業者が多い市区町村（上位10・各ページへのリンク）
  3. 届出をした時期
  4. 管轄の家庭裁判所
  5. よくある質問（画面と FAQPage）
<!--pref-extra-->〜<!--/pref-extra--> の間を毎回作り直すので、何度実行しても同じ結果になる。
"""
import json
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "tantei-portal-data")
ENABLED = []          # 運営者の確認が済んだ都道府県の slug を入れる（"ALL" で全県）
A, B = "<!--pref-extra-->", "<!--/pref-extra-->"
STYLE = ("<style>.pref-extra p{line-height:1.9;margin:.4em 0 .9em}.pref-extra h3{font-size:1rem;margin:1.5em 0 .5em;color:#0f4fa8}"
         ".pref-extra .px-kpi{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:.6em 0 1em}"
         ".pref-extra .px-kpi div{background:#f4f8fd;border:1px solid #d6e2f0;border-radius:8px;padding:10px 12px}"
         ".pref-extra .px-kpi small{display:block;font-size:.78rem;color:#4a5665;line-height:1.4;margin-bottom:4px}.pref-extra .px-kpi b{display:block;font-size:1.25rem;line-height:1.3;color:#0f4fa8}"
         ".pref-extra .cx-bar{display:flex;align-items:center;gap:10px;margin:6px 0;font-size:.9rem}.pref-extra .cx-k{width:8.5em;flex:none}"
         ".pref-extra .cx-k a{text-decoration:none}.pref-extra .cx-t{flex:1;height:12px;background:#e8eef6;border-radius:6px;overflow:hidden}"
         ".pref-extra .cx-t i{display:block;height:100%;background:#1668d8}.pref-extra .cx-v{width:4em;text-align:right;font-weight:700}"
         ".pref-extra .cx-court{background:#f4f8fd;border-left:3px solid #1668d8;padding:10px 14px;margin:.6em 0;line-height:1.8}"
         ".pref-extra .px-note{font-size:.82rem;color:#4a5665}.pref-extra details{border-top:1px solid #d6e2f0;padding:10px 0}"
         ".pref-extra details:last-of-type{border-bottom:1px solid #d6e2f0}.pref-extra summary{cursor:pointer;font-weight:700;line-height:1.7}"
         ".pref-extra details p{margin:.5em 0 0}</style>")


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def city_name(slug_path):
    """tokyo/minato → 港区（市区町村ページの <title> から）。"""
    p = os.path.join(ROOT, slug_path + ".html")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        m = re.search(r"<title>(.*?)の探偵事務所", f.read(4000))
    return m.group(1) if m else None


def bar(label, n, top, unit="件"):
    return (f'<div class="cx-bar"><span class="cx-k">{label}</span><span class="cx-t"><i style="width:{max(1, round(n * 100 / top))}%"></i></span>'
            f'<span class="cx-v">{n:,}{unit}</span></div>')


def build(slug):
    rows = load(os.path.join(ROOT, "all.json"))
    pop = load(os.path.join(DATA, "pref_population.json"))
    courts = load(os.path.join(DATA, "family_courts.json")).get(slug)
    mine = [r for r in rows if r["s"] == slug]
    if not mine:
        return None
    pref = mine[0]["p"]
    n, total = len(mine), len(rows)
    by_pref = Counter(r["p"] for r in rows)
    rank = [p for p, _ in by_pref.most_common()].index(pref) + 1
    ratio = {p: by_pref[p] * 100000 / pop[p] for p in by_pref if pop.get(p)}
    avg = total * 100000 / sum(pop[p] for p in ratio)
    rrank = sorted(ratio, key=lambda p: -ratio[p]).index(pref) + 1
    listed = sum(1 for r in mine if r.get("m") == 0)
    cities = Counter(r["c"] for r in mine if r.get("c")).most_common()
    named = [(city_name(c), c, k) for c, k in cities]
    named = [x for x in named if x[0]]
    top10 = named[:10]
    top3 = sum(k for _, _, k in named[:3])
    years = Counter(2000 + int(r["i"][2:4]) for r in mine)
    recent = sum(v for y, v in years.items() if y >= 2024)
    groups = [("2010年まで", sum(v for y, v in years.items() if y <= 2010)), ("2011〜2019年", sum(v for y, v in years.items() if 2011 <= y <= 2019)),
              ("2020〜2023年", sum(v for y, v in years.items() if 2020 <= y <= 2023)), ("2024年以降", recent)]
    peak = max((y for y in years if y <= 2025), key=lambda y: years[y])
    more = "多い" if ratio[pref] > avg else "少ない"
    rk = "最も" if rank == 1 else f"{rank}番目に"

    h = [A, f'<section class="t-box pref-extra" id="pref-data">{STYLE}', f'<h2 class="t-sub-h">データで見る{pref}の探偵事務所</h2>']
    h.append(f'<p>{pref}で探偵業の届出をしている探偵事務所・興信所は<b>{n:,}件</b>で、47都道府県のなかで<b>{rk}</b>多く、全国{total:,}件の{n * 100 / total:.1f}%にあたります。'
             f'人口10万人あたりでは{ratio[pref]:.2f}件で、全国平均（{avg:.2f}件）より{more}水準です（都道府県公安委員会への届出情報・令和8年5月31日時点）。</p>')
    h.append('<div class="px-kpi">'
             f'<div><small>届出業者数</small><b>{n:,}件</b></div><div><small>全国での順位</small><b>{rank}位</b></div>'
             f'<div><small>人口10万人あたり</small><b>{ratio[pref]:.2f}件</b></div><div><small>人口あたりの順位</small><b>{rrank}位</b></div>'
             f'<div><small>当サイトに掲載済み</small><b>{listed}件</b></div></div>')
    if top10:
        h.append(f'<h3>{pref}で探偵事務所が多い市区町村</h3>')
        h.append(f'<p>{pref}の届出業者がいちばん多いのは<b>{top10[0][0]}の{top10[0][2]}件</b>です。'
                 + (f'上位3つ（{"・".join(x[0] for x in named[:3])}）を合わせると{top3:,}件で、{pref}全体の{top3 * 100 / n:.1f}%を占めます。' if len(named) >= 3 else '')
                 + '市区町村の名前を押すと、その地域の一覧を見られます。</p>')
        for nm, c, k in top10:
            h.append(bar(f'<a href="./{c}.html">{esc(nm)}</a>', k, top10[0][2]))
        if len(named) > 10:
            h.append(f'<p class="px-note">届出業者がある市区町村は、{pref}内に{len(named)}あります。ページ上部の「市区町村から探す」からすべて選べます。</p>')
    h.append('<h3>届出をした時期</h3>')
    h.append(f'<p>{pref}の届出業者{n:,}件が、探偵業の届出をした年の内訳です（届出番号の3〜4桁目から集計）。<b>2024年以降に届出をした新しい事務所が{recent:,}件</b>あり、'
             f'全体の{recent * 100 / n:.1f}%を占めます。1年あたりでは{peak}年の{years[peak]:,}件が最多です。</p>')
    top = max(v for _, v in groups) or 1
    for k, v in groups:
        h.append(bar(k, v, top))
    h.append('<p class="px-note">届出の年が古いほど良いというわけではありません。移転や法人化で届出をし直した事務所もあります。2026年は5月31日までの数です。</p>')
    faq = [
        (f'{pref}に探偵事務所は何件ありますか？',
         f'{pref}公安委員会に探偵業の届出をしている探偵事務所・興信所は{n:,}件です（令和8年5月31日時点）。全国{total:,}件のうち{n * 100 / total:.1f}%で、47都道府県のなかで{rk}多い数です。'),
    ]
    if top10:
        faq.append((f'{pref}では、どの地域に探偵事務所が多いですか？',
                    f'いちばん多いのは{top10[0][0]}の{top10[0][2]}件です。' + (f'次いで{named[1][0]}の{named[1][2]}件、{named[2][0]}の{named[2][2]}件です。' if len(named) >= 3 else '')
                    + 'ただし、探偵は事務所の所在地の外でも調査をするので、事務所の場所だけで依頼先を決める必要はありません。'))
    faq.append((f'{pref}の探偵事務所が届出をしているか、確かめる方法はありますか？',
                f'探偵業を営むには、営業所ごとに都道府県公安委員会への届出が必要です。このページの一覧には、{pref}で届出をしている業者だけを載せています。'
                '事務所から聞いた届出番号や名前を、上の「業者名・住所で絞り込む」に入れると確かめられます。'))
    if courts:
        seen, lines = [], []
        for r in courts.get("rows", []):
            k = r["court"] + (" " + r["desk"] if r.get("desk") else "")
            if k not in seen:
                seen.append(k)
                area = "・".join(r["names"][:4]) + ("など" if len(r["names"]) > 4 else "")
                lines.append(f'<b>{esc(k)}</b>（{esc(area)}）')
        if lines:
            h.append(f'<h3>{pref}を管轄する家庭裁判所</h3>')
            h.append('<div class="cx-court">' + "<br>".join(lines[:8]) + '</div>')
            h.append('<p>浮気の証拠をもとに離婚調停などを申し立てるときの窓口です。調停は原則として<b>相手方の住所地</b>を管轄する家庭裁判所に申し立てます。'
                     f'管轄は<a href="{esc(courts.get("source", "https://www.courts.go.jp/"))}" target="_blank" rel="noopener">裁判所のサイト</a>で確かめられます。</p>')
    h.append(f'<h3>{pref}の探偵事務所についてよくある質問</h3>')
    for q, a in faq:
        h.append(f'<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>')
    ld = {"@context": "https://schema.org", "@type": "FAQPage",
          "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}
    h.append('<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False).replace("</", "<\\/") + '</script>')
    h.append('</section>')
    h.append(B)
    return "\n".join(h)


def apply(html, block):
    html = re.sub(re.escape(A) + r".*?" + re.escape(B) + r"\n?", "", html, flags=re.S)
    # 置き場所：業者の一覧と、その注記（<div class="note">）のすぐ後
    m = re.search(r'</table></div>\s*</section>(?:\s*<div class="note">.*?</div>)?', html, re.S)
    if not m:
        return None
    return html[:m.end()] + "\n" + block + "\n" + html[m.end():]


def main():
    if len(sys.argv) >= 4 and sys.argv[1] == "--preview":
        slug, out = sys.argv[2], sys.argv[3]
        t = apply(open(os.path.join(ROOT, slug + ".html"), encoding="utf-8").read(), build(slug))
        t = t.replace("<head>", f'<head><base href="file:///{ROOT.replace(os.sep, "/")}/"><meta name="robots" content="noindex">', 1)
        open(out, "w", encoding="utf-8").write(t)
        print("preview:", out)
        return
    slugs = sorted({r["s"] for r in load(os.path.join(ROOT, "all.json"))}) if ENABLED == "ALL" else list(ENABLED)
    n = 0
    for slug in slugs:
        p = os.path.join(ROOT, slug + ".html")
        block = build(slug)
        if not block or not os.path.exists(p):
            continue
        s = open(p, encoding="utf-8", newline="").read()
        t = apply(s, block)
        if t and t != s:
            open(p, "w", encoding="utf-8", newline="").write(t)
            n += 1
    print(f"pref-extra: {n} pages")


if __name__ == "__main__":
    main()

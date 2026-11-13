"""掲載済み業者のGoogleマップの★評価・口コミ件数を取得し、掲載ページに「利用したことがあるユーザーの感想」として出す（2026-11-14）。

口コミ本文は出さない（本文の取得は課金が増えるため運営者判断で見送り）。出すのは ★評価・件数・Googleマップの口コミへのリンクだけ。

データ: tantei-portal-data/gbp.json
  { "<届出番号>": { "place_id": "ChIJ...",       … 手で確認して入れる（find で候補を調べる）。自動で見つけたものもある
                    "rejected": ["ChIJ..."],      … 別の業者だった登録（自動で再び選ばない）
                    "rating": 4.8, "count": 23,   … fetch が書き込む
                    "uri": "https://maps.google.com/?cid=...",
                    "fetched": "2026-11-14" } }

  python tantei-portal-tools/google_rating.py find "業者名 市区町村"   … Place ID の候補を表示（ID と名前・住所だけ＝無料枠の軽いSKU）
  python tantei-portal-tools/google_rating.py fetch                   … 全件の★・件数を取り直す（APIキーは環境変数 PLACES_API_KEY）。
                                                                       掲載済みで place_id が無い業者は、名前と市区町村が一致したときだけ自動で登録する
  python tantei-portal-tools/google_rating.py render                  … 掲載ページに書き込む（APIを呼ばない）

費用: ★・件数は Place Details の Enterprise SKU（毎月1,000回まで無料）。週1回×掲載業者数で呼ぶので、
掲載業者が200社を超えるまでは無料枠に収まる。念のため1回の実行で MAX_CALLS を超えては呼ばない。

書き込む位置: 掲載ページの「この情報は都道府県公安委員会…」の注記の直後（GAS が承認時に作り直す範囲の外）。
<!--g-rating-->〜<!--/g-rating--> で囲み、何度実行しても同じ結果になる。掲載済みでなくなった業者からは消す。
"""
import datetime
import html
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "tantei-portal-data")
BIZ = os.path.join(ROOT, "biz")
GBP = os.path.join(DATA, "gbp.json")
MAX_CALLS = 200
OPEN, CLOSE = "<!--g-rating-->", "<!--/g-rating-->"
BLOCK_RE = re.compile(re.escape(OPEN) + r".*?" + re.escape(CLOSE), re.S)
NOTE_RE = re.compile(r'<div class="note">この情報は都道府県公安委員会への届出情報.*?</div>', re.S)


def api(url, fields, body=None):
    key = os.environ.get("PLACES_API_KEY", "")
    if not key:
        raise SystemExit("環境変数 PLACES_API_KEY がありません")
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None,
                                 headers={"X-Goog-Api-Key": key, "X-Goog-FieldMask": fields,
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def load():
    return json.load(open(GBP, encoding="utf-8")) if os.path.exists(GBP) else {}


def save(d):
    with open(GBP, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
        f.write("\n")


def find(q):
    j = api("https://places.googleapis.com/v1/places:searchText?languageCode=ja&regionCode=JP",
            "places.id,places.displayName,places.formattedAddress", {"textQuery": q})
    for p in j.get("places", []):
        print(p["id"], p.get("displayName", {}).get("text"), p.get("formattedAddress"))


def norm(x):
    import unicodedata
    x = unicodedata.normalize("NFKC", str(x or "")).lower()
    return re.sub(r"[\s・･.,、。()（）「」]|株式会社|有限会社|合同会社|\(株\)|\(有\)", "", x)


GENERIC = r"総合|探偵事務所|探偵社|探偵|興信所|調査事務所|調査室|調査|事務所|リサーチ|research|office|オフィス"


def auto_find(d, today):
    """掲載済みなのに place_id が無い業者を探す。名前と市区町村の両方が一致したときだけ採用（30日に1回まで探し直す）。"""
    permitted = json.load(open(os.path.join(DATA, "permitted.json"), encoding="utf-8"))
    all_biz = {x["i"]: x for x in json.load(open(os.path.join(ROOT, "all.json"), encoding="utf-8"))}
    calls = 0
    for bid in permitted:
        e = d.get(bid) or {}
        if e.get("place_id"):
            continue
        last = e.get("searched") or ""
        if last and (datetime.date.fromisoformat(today) - datetime.date.fromisoformat(last)).days < 30:
            continue
        b = all_biz.get(bid)
        if not b:
            continue
        name = norm(b.get("n"))
        city = re.match(r"^(.{2,3}?[都道府県])?(.+?[市区町村])", b.get("a") or "")
        j = api("https://places.googleapis.com/v1/places:searchText?languageCode=ja&regionCode=JP",
                "places.id,places.displayName,places.formattedAddress", {"textQuery": "%s %s" % (b.get("n"), b.get("a"))})
        calls += 1
        hit = None
        core = re.sub(GENERIC, "", name)
        for p in j.get("places", []):
            if p["id"] in (e.get("rejected") or []):
                continue
            dn, addr = norm(p.get("displayName", {}).get("text")), p.get("formattedAddress") or ""
            # 「探偵事務所」のような一般名だけで一致させない（2026-11-14 EDGE探偵事務所が「探偵事務所」という別の登録と誤って一致した）
            dcore = re.sub(GENERIC, "", dn)
            if len(core) >= 2 and core in dcore and (not city or city.group(2) in addr):
                hit = p; break
        e["searched"] = today
        if hit:
            e["place_id"] = hit["id"]
            print(bid, "Googleマップの登録を見つけました:", hit.get("displayName", {}).get("text"))
        d[bid] = e
    return calls


def fetch():
    d = load()
    today = datetime.date.today().isoformat()
    calls = auto_find(d, today)
    for bid, e in d.items():
        if not e.get("place_id"):
            continue
        if calls >= MAX_CALLS:
            print("MAX_CALLS に達したので中断"); break
        j = api("https://places.googleapis.com/v1/places/%s?languageCode=ja&regionCode=JP" % e["place_id"],
                "rating,userRatingCount,googleMapsUri")
        calls += 1
        e["rating"] = j.get("rating")
        e["count"] = j.get("userRatingCount") or 0
        e["uri"] = j.get("googleMapsUri") or e.get("uri")
        e["fetched"] = today
        print(bid, e["rating"], e["count"])
    save(d)


def stars(r):
    full = int(r + 0.25)
    half = 1 if (r - full) >= 0.25 and full < 5 else 0
    return "★" * full + ("☆" if half else "") + "☆" * (5 - full - half)


def block(name, e):
    r, c, uri = e.get("rating"), e.get("count") or 0, e.get("uri")
    if not uri:
        return ""
    if r and c:
        score = ('<span style="font-size:1.6rem;font-weight:800;color:#1b2a3d">%.1f</span>'
                 '<span style="color:#f5a623;font-size:1.15rem;letter-spacing:1px;margin:0 8px">%s</span>'
                 '<span style="color:#55657a;font-size:.9rem">Googleマップの口コミ %d件</span>' % (r, stars(r), c))
    else:
        score = '<span style="color:#55657a;font-size:.9rem">Googleマップの口コミはまだありません</span>'
    fetched = e.get("fetched") or ""
    return (OPEN + '<section class="bf g-rating"><h2>%sを利用したことがあるユーザーの感想</h2>'
            '<div style="display:flex;align-items:center;flex-wrap:wrap;gap:4px 0">%s</div>'
            '<p><a href="%s" target="_blank" rel="noopener">Googleマップで口コミを読む</a>'
            '（Googleマップに投稿された口コミです。%s時点）</p></section>' % (
                html.escape(name), score, html.escape(uri, quote=True), html.escape(fetched)) + CLOSE)


def render():
    d = load()
    permitted = set(json.load(open(os.path.join(DATA, "permitted.json"), encoding="utf-8")))
    changed = 0
    for fn in sorted(os.listdir(BIZ)):
        if not fn.endswith(".html"):
            continue
        bid = fn[:-5]
        path = os.path.join(BIZ, fn)
        e = d.get(bid)
        page = open(path, encoding="utf-8", newline="").read()
        if not e and OPEN not in page:
            continue
        new = BLOCK_RE.sub("", page)
        m = NOTE_RE.search(new)
        if e and bid in permitted and m:
            h = re.search(r"<h1>(.*?)</h1>", new, flags=re.S)
            name = html.unescape(re.sub(r"<[^>]+>", "", h.group(1)).strip()) if h else bid
            b = block(name, e)
            if b:
                new = new[:m.end()] + b + new[m.end():]
        if new != page:
            open(path, "w", encoding="utf-8", newline="").write(new)
            changed += 1
            print(bid, "更新")
    print("更新したページ:", changed)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "find":
        find(" ".join(sys.argv[2:]))
    elif cmd == "fetch":
        fetch()
    elif cmd == "render":
        render()
    else:
        print(__doc__)

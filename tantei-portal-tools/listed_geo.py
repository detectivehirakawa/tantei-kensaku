"""掲載済みの探偵社の地図ピンの位置を前もって計算し、tantei-portal-data/listed_geo.json に書く（2026-11-17、運営者指示「掲載しているところは全件ピンを立てる・今後も必ず」）。

- 位置は事務所が入力した住所（biz_extra.json の officeAddress）から、国土地理院の住所検索で求める。
  入力が無ければ all.json の住所の市区町村まで（届出住所の番地＝自宅かもしれない位置は使わない）。
- 〒・郵便番号・空白・ビル名などで検索に失敗するので、番地まで→丁目/町名まで→市区町村まで、と短くして順に試す。
- 地図（トップの地図・近くの掲載済み・map.html）は、このファイルを先に読み、ここに無い新しい掲載だけをブラウザで検索する。
- listed-hero.yml の中で毎回実行（承認されれば自動）。何度実行しても同じ結果になる。
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "tantei-portal-data")
OUT = os.path.join(DATA, "listed_geo.json")
GSI = "https://msearch.gsi.go.jp/address-search/AddressSearch?q="
PREF_RE = r"(東京都|北海道|(?:京都|大阪)府|.{2,3}県)"
CITY_RE = re.compile(PREF_RE + r"?(.+?郡.+?[町村]|.+?市.+?区|.+?[市区町村])")


def normalize(addr):
    s = str(addr or "")
    s = re.sub(r"〒?\s*\d{3}[-‐－ー−]?\d{4}", " ", s)
    s = s.replace("　", " ").strip()
    return re.sub(r"\s+", " ", s)


def candidates(addr, pref):
    s = normalize(addr)
    if pref and not s.startswith(pref) and not re.match(PREF_RE, s):
        s = pref + s
    out = []
    def add(x):
        x = x.strip(" 、,")
        if x and x not in out:
            out.append(x)
    head = s.split(" ")[0]
    add(s)
    add(head)
    m = re.match(r"(.+?[0-9０-９]+(?:[-‐－ー−丁目番地号の][0-9０-９]+)*(?:番地|号)?)", head)
    if m:
        add(m.group(1))
    m = re.match(r"(.+?(?:丁目|[町村]|字[^0-9０-９]+|大字[^0-9０-９]+))", head)
    if m:
        add(m.group(1))
    m = CITY_RE.match(head)
    if m:
        add((m.group(1) or "") + m.group(2))
    return out


def gsi(q):
    req = urllib.request.Request(GSI + urllib.parse.quote(q), headers={"User-Agent": "tantei-kensaku-listed-geo"})
    for n in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                j = json.loads(r.read().decode("utf-8"))
            if j and j[0].get("geometry"):
                c = j[0]["geometry"]["coordinates"]
                return {"lat": round(c[1], 6), "lng": round(c[0], 6)}
            return None
        except Exception:
            time.sleep(2 * (n + 1))
    return None


def main():
    with open(os.path.join(ROOT, "all.json"), encoding="utf-8") as f:
        allrows = json.load(f)
    try:
        with open(os.path.join(DATA, "biz_extra.json"), encoding="utf-8") as f:
            extra = json.load(f)
    except (OSError, ValueError):
        extra = {}
    try:
        with open(OUT, encoding="utf-8") as f:
            old = json.load(f)
    except (OSError, ValueError):
        old = {}
    out, missing = {}, []
    for r in allrows:
        if r.get("m") != 0:
            continue
        i = r["i"]
        oa = str((extra.get(i) or {}).get("officeAddress") or "").strip()
        src = oa
        if not oa:
            m = CITY_RE.match(normalize(r.get("a", "")))
            src = ((m.group(1) or r.get("p", "")) + m.group(2)) if m else r.get("p", "")
        prev = old.get(i)
        if prev and prev.get("src") == src:
            out[i] = prev
            continue
        hit = None
        for q in candidates(src, r.get("p", "")):
            g = gsi(q)
            time.sleep(0.3)
            if g:
                hit = dict(g, src=src, q=q)
                break
        if hit:
            out[i] = hit
        elif prev:
            out[i] = prev  # 検索が一時的に失敗しても前回の位置を残す
            missing.append(i + "（前回の位置を使用）")
        else:
            missing.append(i)
    text = json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    try:
        with open(OUT, encoding="utf-8") as f:
            same = f.read() == text
    except OSError:
        same = False
    if not same:
        with open(OUT, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    print("掲載済み", sum(1 for r in allrows if r.get("m") == 0), "件 / 位置あり", len(out), "件", "（更新）" if not same else "（変更なし）")
    if missing:
        print("位置が求まらない:", ", ".join(missing))
        sys.exit(1 if any("前回" not in x for x in missing) else 0)


if __name__ == "__main__":
    main()

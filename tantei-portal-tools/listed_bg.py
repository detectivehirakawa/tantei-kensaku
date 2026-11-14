"""掲載済みの探偵社の公式サイトからメインの画像（ヒーローの背景など）を1枚選び、
掲載ページ上部の帯（t-pagehero）の背景に使う（2026-11-14、運営者指示・掲載済み全社の統一ルール）。

- 画像は img/listed/<届出番号>-bg.webp（横1600px以内）。どのURLから取ったかは img/listed/bg.json に記録。
- 選び方: トップページのHTMLと、そこから読み込むCSSに出てくる画像（<img>・srcset・background-image・og:image）を
  出てくる順に調べ、横900px以上・横長（縦横比1.2〜4）の最初の1枚。なければ一番大きい画像。ロゴ・アイコンらしいものは除く。
- ロゴ・文字だけのバナー（ほぼ同じ色の部分が多い画像）や og:image 用の画像は使わない。
  良い画像がなければ、ホームページの画面（listed_heroes.py が撮ったもの）をぼかして使う。どちらもなければ青い帯のまま。公式サイトのURLが変わったら取り直す。FORCE=<番号,…> でも取り直す。
- 何度実行しても同じ結果になる（listed-hero.yml の中で毎回実行）。
"""
import hashlib
import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "tantei-portal-data")
OUT = os.path.join(ROOT, "img", "listed")
BIZ = os.path.join(ROOT, "biz")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
HERO_RE = re.compile(r'<div class="t-pagehero(?: has-bg" style="[^"]*)?">')
SKIP = re.compile(r"logo|icon|favicon|sprite|banner-?line|btn|button|qr|badge|loading|spinner|arrow|sns|line[_-]?(?:btn|icon)", re.I)


def get(url, limit=8_000_000):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read(limit), r.headers.get("Content-Type", "")


def site_url(entry):
    for u in re.findall(r"https?://[^\s\"'<>]+", (entry or {}).get("url", "")):
        if "line.me" not in u and "lin.ee" not in u and "instagram.com" not in u and "x.com" not in u and "twitter.com" not in u:
            return u
    return None


def candidates(page_url):
    html = get(page_url)[0].decode("utf-8", "ignore")
    found = []

    def add(u, base):
        u = (u or "").strip().strip("'\"")
        if not u or u.startswith("data:") or u.endswith(".svg") or ".svg?" in u:
            return
        u = urllib.parse.urljoin(base, u)
        if u not in found:
            found.append(u)

    body = re.sub(r"(?is)<(script|noscript)\b.*?</\1>", "", html)
    m = re.search(r"(?is)<body\b.*", body)
    body = m.group(0) if m else body
    head_css = re.findall(r'(?is)<link[^>]+rel=["\']?stylesheet[^>]*>', html)
    # 本文に出てくる順（<img> / srcset / data-src / style="background…" / <style>）
    for t in re.finditer(r'(?is)<img\b[^>]*>|style=["\'][^"\']*url\([^)]*\)[^"\']*["\']|<style\b.*?</style>|<source\b[^>]*>', body):
        s = t.group(0)
        if s.lower().startswith(("<img", "<source")):
            for attr in ("data-src", "data-lazy-src", "src"):
                mm = re.search(r'\b%s=["\']([^"\']+)' % attr, s)
                if mm:
                    add(mm.group(1), page_url); break
            ss = re.search(r'\b(?:data-)?srcset=["\']([^"\']+)', s)
            if ss:
                parts = [p.strip().split(" ")[0] for p in ss.group(1).split(",") if p.strip()]
                if parts:
                    add(parts[-1], page_url)
        else:
            for u in re.findall(r"url\(([^)]+)\)", s):
                add(u, page_url)
    # 外部CSSの background
    for tag in head_css[:6]:
        mm = re.search(r'href=["\']([^"\']+)', tag)
        if not mm:
            continue
        css_url = urllib.parse.urljoin(page_url, mm.group(1))
        try:
            css = get(css_url, 3_000_000)[0].decode("utf-8", "ignore")
        except Exception:
            continue
        for blk in re.findall(r"(?is)[^{}]*\{[^{}]*background[^{}]*\}", css):
            for u in re.findall(r"url\(([^)]+)\)", blk):
                add(u, css_url)
    og = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', html, re.I)
    if og:
        add(og.group(1), page_url)
    return [u for u in found if not SKIP.search(urllib.parse.urlparse(u).path.rsplit("/", 1)[-1])]


def flat(im):
    """ロゴやバナーのように、ほぼ同じ色の部分が多い画像か（写真ではない）。"""
    sm = im.convert("RGB").resize((64, 36))
    q = [(r // 24, g // 24, b // 24) for r, g, b in getattr(sm, "get_flattened_data", sm.getdata)()]
    top = max(q.count(c) for c in set(q))
    return top / len(q) > 0.35


def pick(page_url):
    best, best_area = None, 0
    for u in candidates(page_url)[:40]:
        try:
            data, ctype = get(u)
            im = Image.open(io.BytesIO(data))
            im.load()
        except Exception:
            continue
        w, h = im.size
        if re.search(r"ogp|og-image|ogimage", u, re.I) or flat(im):
            continue
        if w >= 900 and 1.2 <= w / max(h, 1) <= 4:
            return u, im
        if w >= 600 and w * h > best_area and w / max(h, 1) >= 1:
            best, best_area = (u, im), w * h
    return best or (None, None)


def patch(i, on):
    path = os.path.join(BIZ, f"{i}.html")
    if not os.path.exists(path):
        return False
    html = open(path, encoding="utf-8").read()
    if on:
        ver = hashlib.md5(open(os.path.join(OUT, f"{i}-bg.webp"), "rb").read()).hexdigest()[:8]
        tag = f'<div class="t-pagehero has-bg" style="--bg:url(/img/listed/{i}-bg.webp?v={ver})">'
    else:
        tag = '<div class="t-pagehero">'
    new = HERO_RE.sub(tag, html, count=1)
    if new == html:
        return False
    open(path, "w", encoding="utf-8", newline="").write(new)
    print(i, "上部の帯の背景", "設定" if on else "解除")
    return True


def main():
    os.makedirs(OUT, exist_ok=True)
    extra = json.load(open(os.path.join(DATA, "biz_extra.json"), encoding="utf-8"))
    permitted = set(json.load(open(os.path.join(DATA, "permitted.json"), encoding="utf-8")))
    idx_path = os.path.join(OUT, "bg.json")
    idx = json.load(open(idx_path, encoding="utf-8")) if os.path.exists(idx_path) else {}
    force = set(filter(None, os.environ.get("FORCE", "").split(",")))
    for i in sorted(permitted):
        u = site_url(extra.get(i))
        img = os.path.join(OUT, f"{i}-bg.webp")
        if not u:
            continue
        if (idx.get(i) or {}).get("site") == u and i not in force and (os.path.exists(img) or (idx.get(i) or {}).get("src") is None):
            continue
        try:
            src, im = pick(u)
        except Exception as e:
            print(i, "背景画像を取れなかった", u, e)
            src, im = None, None
        if im is not None:
            im = im.convert("RGB")
            if im.width > 1600:
                im = im.resize((1600, round(im.height * 1600 / im.width)))
            im.save(img, "WEBP", quality=72)
            print(i, "背景画像を保存", src)
        else:
            shot = os.path.join(OUT, f"{i}.webp")  # 良い画像がなければ、ホームページの画面（listed_heroes.py が撮影）をぼかして使う
            if os.path.exists(shot):
                from PIL import ImageFilter
                Image.open(shot).convert("RGB").filter(ImageFilter.GaussianBlur(6)).save(img, "WEBP", quality=70)
                src = "screenshot"
                print(i, "背景はホームページの画面をぼかして使用")
            elif os.path.exists(img):
                os.remove(img)
        idx[i] = {"site": u, "src": src}
    for i in list(idx):
        if i not in permitted:
            idx.pop(i)
            p = os.path.join(OUT, f"{i}-bg.webp")
            if os.path.exists(p):
                os.remove(p)
            patch(i, False)
    json.dump(idx, open(idx_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for i in sorted(permitted):
        patch(i, os.path.exists(os.path.join(OUT, f"{i}-bg.webp")))


if __name__ == "__main__":
    main()

"""全国探偵検索：掲載済みの探偵社のホームページの最初の1画面（ヒーロー部分）を撮って
img/listed/<届出番号>.webp に保存し、img/listed/index.json（届出番号→撮影したURL）を更新する。
GitHub Actions（.github/workflows/listed-hero.yml）が、掲載の承認（permitted.json / biz_extra.json の更新）のたびに実行する。
撮っていない事務所、または公式サイトのURLが変わった事務所だけを撮り直す。
"""
import hashlib, json, os, re, shutil, subprocess, sys, tempfile
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "tantei-portal-data")
OUT = os.path.join(ROOT, "img", "listed")
BIZ = os.path.join(ROOT, "biz")
CERT_PLAIN = '<div class="cert-frame">'
CERT_HERO_RE = re.compile(r'<div class="cert-frame has-hero" style="[^"]*">')
CHROME = os.environ.get("CHROME") or shutil.which("google-chrome") or shutil.which("chromium") \
    or r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def site_url(entry):
    for u in re.findall(r"https?://[^\s\"'<>]+", (entry or {}).get("url", "")):
        if "line.me" not in u and "lin.ee" not in u:
            return u
    return None


def main():
    os.makedirs(OUT, exist_ok=True)
    extra = json.load(open(os.path.join(DATA, "biz_extra.json"), encoding="utf-8"))
    permitted = set(json.load(open(os.path.join(DATA, "permitted.json"), encoding="utf-8")))
    idx_path = os.path.join(OUT, "index.json")
    idx = json.load(open(idx_path, encoding="utf-8")) if os.path.exists(idx_path) else {}
    changed = False
    for i in sorted(permitted):
        u = site_url(extra.get(i))
        if not u:
            continue
        img = os.path.join(OUT, f"{i}.webp")
        force = set(filter(None, os.environ.get("FORCE", "").split(",")))
        if idx.get(i) == u and os.path.exists(img) and i not in force:
            continue
        tmp = os.path.join(tempfile.gettempdir(), f"hero_{i}.png")
        try:
            subprocess.run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars", "--mute-audio",
                            "--virtual-time-budget=8000", "--window-size=1280,720", f"--screenshot={tmp}", u],
                           capture_output=True, timeout=120)
        except Exception as e:
            print(i, "撮影失敗", u, e); continue
        if not os.path.exists(tmp):
            print(i, "撮影失敗", u); continue
        Image.open(tmp).convert("RGB").crop((0, 0, 1280, 720)).resize((960, 540)).save(img, "WEBP", quality=70)
        os.remove(tmp)
        idx[i] = u
        changed = True
        print(i, "保存", u)
    removed = []
    for i in list(idx):
        if i not in permitted:
            idx.pop(i)
            removed.append(i)
            changed = True
            p = os.path.join(OUT, f"{i}.webp")
            if os.path.exists(p):
                os.remove(p)
    if changed or not os.path.exists(idx_path):
        json.dump(idx, open(idx_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("掲載済みの画像:", len(idx))
    return removed


def patch_cert(i, on):
    """掲載ページの掲載証（cert-frame）の背景に、その探偵社のヒーロー画像を入れる／外す。何度実行しても同じ結果になる。"""
    path = os.path.join(BIZ, f"{i}.html")
    if not os.path.exists(path):
        return False
    html = open(path, encoding="utf-8").read()
    if on:
        img = os.path.join(OUT, f"{i}.webp")
        ver = hashlib.md5(open(img, "rb").read()).hexdigest()[:8]
        tag = f'<div class="cert-frame has-hero" style="--hero:url(/img/listed/{i}.webp?v={ver})">'
    else:
        tag = CERT_PLAIN
    new = CERT_HERO_RE.sub(tag, html, count=1)
    if new == html:
        new = html.replace(CERT_PLAIN, tag, 1)
    if new == html:
        return False
    open(path, "w", encoding="utf-8", newline="").write(new)
    print(i, "掲載証の背景", "設定" if on else "解除")
    return True


def patch_all(removed=()):
    """撮影済みの事務所は掲載証に背景を入れ、掲載をやめた事務所は外す（全7,554ページは読まない）。"""
    idx_path = os.path.join(OUT, "index.json")
    idx = json.load(open(idx_path, encoding="utf-8")) if os.path.exists(idx_path) else {}
    for i in idx:
        if os.path.exists(os.path.join(OUT, f"{i}.webp")):
            patch_cert(i, True)
    for i in removed:
        patch_cert(i, False)


if __name__ == "__main__":
    patch_all(main())

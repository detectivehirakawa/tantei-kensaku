"""トップ・都道府県一覧・市区町村ページの本文の先頭に「探偵賀詞交歓会 2027」のバナーを入れる（2026-11-19、運営者指示）。

- `<!--gashi-banner:start-->`〜`<!--gashi-banner:end-->` を毎回作り直す（無ければ <main ...> の直後に入れる＝フルビルド後も戻る）。
- 開催日（2027-01-13）を過ぎたら、ページから取り除く。ブラウザ側でも開催日の翌日からは表示しない。
- 「開催まであと○日」はブラウザで計算する。業者ページ（biz/）には入れない。
- listed-hero.yml と listed_all.sh で毎回実行。
"""
import datetime
import glob
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
END = datetime.date(2027, 1, 13)
URL = "https://exeresearch.jp/gashi-kokankai/?utm_source=tantei-kensaku&amp;utm_medium=banner&amp;utm_campaign=gashi2027"
BLOCK_RE = re.compile(r"<!--gashi-banner:start-->.*?<!--gashi-banner:end-->\n?", re.S)
MAIN_RE = re.compile(r'<main style="max-width:none;margin:0;padding:0">')

CSS = (
    ".gk{--gold:#e8c46a;--gold2:#fff1c4;position:relative;display:grid;grid-template-columns:1.35fr 1fr;margin:0 0 16px;border-radius:14px;overflow:hidden;"
    "text-decoration:none!important;color:#fff!important;background:#0b0d14;box-shadow:0 10px 26px rgba(10,20,40,.28);isolation:isolate}"
    ".gk::before{content:\"\";position:absolute;inset:0;z-index:-2;background:url(/img/pr/gashi-banner-bg.webp) center 60%/cover}"
    ".gk::after{content:\"\";position:absolute;inset:0;z-index:-1;background:radial-gradient(120% 90% at 85% 0%,rgba(232,196,106,.22),transparent 55%),"
    "linear-gradient(90deg,rgba(8,9,15,.93) 0%,rgba(8,9,15,.8) 55%,rgba(8,9,15,.6) 100%)}"
    ".gk-l{padding:22px 26px}.gk-pr{position:absolute;top:8px;right:8px;background:rgba(255,255,255,.18);font:700 10px/1.6 sans-serif;padding:0 6px;border-radius:3px;letter-spacing:.08em}"
    ".gk-en{font:600 10px/1.4 serif;letter-spacing:.3em;color:var(--gold);text-transform:uppercase}"
    ".gk-ttl{display:block;margin:8px 0 6px;font-family:\"Hiragino Mincho ProN\",\"Yu Mincho\",\"Noto Serif JP\",serif;font-weight:800;font-size:clamp(26px,4vw,38px);line-height:1.15;letter-spacing:.06em;"
    "background:linear-gradient(180deg,var(--gold2),var(--gold) 55%,#b8862e);-webkit-background-clip:text;background-clip:text;color:transparent}"
    ".gk-cp{margin:0 0 14px;font-size:clamp(13px,1.5vw,15px);line-height:1.7;color:#e9e4d6}.gk-cp b{color:#fff}"
    ".gk-hist{display:flex;gap:8px}.gk-hist span{flex:1;border:1px solid rgba(232,196,106,.35);border-radius:8px;padding:6px 6px;text-align:center;font-size:10.5px;color:#cfc6ae;background:rgba(0,0,0,.28)}"
    ".gk-hist b{display:block;font:800 20px/1.15 \"Hiragino Mincho ProN\",\"Yu Mincho\",serif;color:#fff}"
    ".gk-hist .now{border-color:var(--gold);background:linear-gradient(180deg,rgba(232,196,106,.22),rgba(232,196,106,.06))}.gk-hist .now b{color:var(--gold2)}"
    ".gk-r{display:flex;flex-direction:column;justify-content:center;gap:9px;padding:22px 24px;background:linear-gradient(180deg,rgba(255,255,255,.07),rgba(255,255,255,.02));border-left:1px solid rgba(232,196,106,.25)}"
    ".gk-date{display:flex;align-items:baseline;gap:8px}.gk-date b{font:800 46px/1 \"Hiragino Mincho ProN\",\"Yu Mincho\",serif;color:var(--gold2)}.gk-date span{font-size:13px;color:#e9e4d6;line-height:1.5}"
    ".gk-cd{font-size:13px;color:#fff;background:#c0392b;padding:3px 10px;border-radius:999px;font-weight:700;align-self:flex-start;animation:gkp 2.4s ease-in-out infinite}"
    ".gk-cd:empty{display:none}@keyframes gkp{50%{box-shadow:0 0 18px rgba(192,57,43,.6)}}"
    ".gk-info{margin:0;font-size:12.5px;line-height:1.75;color:#ddd5c0}"
    ".gk-btn{display:flex;align-items:center;justify-content:center;gap:8px;padding:12px 14px;border-radius:10px;font-weight:800;font-size:15px;color:#2a1d05;"
    "background:linear-gradient(180deg,#fff1c4,#e8c46a 60%,#c99a3c);box-shadow:0 4px 0 #8a6420,0 8px 18px rgba(232,196,106,.3);transition:transform .15s}"
    ".gk:hover .gk-btn{transform:translateY(-2px)}.gk-btn small{font-size:11px;opacity:.75}.gk-sub{font-size:11px;color:#a9a08a;text-align:center}"
    "@media(max-width:720px){.gk{grid-template-columns:1fr}.gk-l{padding:18px 18px 12px}.gk-r{border-left:0;border-top:1px solid rgba(232,196,106,.25);padding:14px 18px 18px}.gk-date b{font-size:38px}}"
)

HTML = (
    '<!--gashi-banner:start--><style>' + CSS + '</style>'
    f'<a class="gk" id="gkBanner" href="{URL}" target="_blank" rel="noopener" aria-label="探偵賀詞交歓会 2027 の参加申込ページへ">'
    '<span class="gk-pr">PR</span>'
    '<span class="gk-l"><span class="gk-en">The Annual Gathering of Detectives · Vol.3</span>'
    '<span class="gk-ttl">探偵賀詞交歓会 2027</span>'
    '<span class="gk-cp" style="display:block">年に一度、<b>全国の探偵が渋谷に集まる夜</b>。<br>同業の仲間や士業・業界の外の方と、新年のあいさつを。</span>'
    '<span class="gk-hist"><span>VOL.1 2025<b>70名</b></span><span>VOL.2 2026<b>100名</b></span><span class="now">VOL.3 2027<b>あなたも</b></span></span></span>'
    '<span class="gk-r"><span class="gk-date"><b>1.13</b><span>水曜日<br>18:30〜21:00</span></span>'
    '<span class="gk-cd" id="gkCd"></span>'
    '<span class="gk-info" style="display:block">渋谷 ドクタージーカンズ（渋谷駅 徒歩約5分）<br>GPS・PCロック解除の実演コーナーあり</span>'
    '<span class="gk-btn">参加を申し込む <small>1名 6,600円</small></span>'
    '<span class="gk-sub">初めての方・探偵以外の方も歓迎／協賛 33,000円</span></span></a>'
    '<script>(function(){var b=document.getElementById("gkBanner");if(!b)return;'
    'var d=Math.ceil((new Date("2027-01-13T00:00:00+09:00")-new Date())/864e5);'
    'if(d<0){b.style.display="none";return;}var c=document.getElementById("gkCd");'
    'if(c)c.textContent=d>0?"開催まであと"+d+"日":"本日開催";})();</script>'
    '<!--gashi-banner:end-->\n'
)


def pages():
    allj = json.load(open(os.path.join(ROOT, "all.json"), encoding="utf-8"))
    prefs = sorted({e["s"] for e in allj})
    out = [os.path.join(ROOT, "index.html")]
    for s in prefs:
        out.append(os.path.join(ROOT, s + ".html"))
        out += glob.glob(os.path.join(ROOT, s, "*.html"))
    return [p for p in out if os.path.exists(p)]


def main():
    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date()
    show = today <= END
    changed = 0
    for p in pages():
        t = open(p, encoding="utf-8").read()
        t2 = BLOCK_RE.sub("", t)
        if show:
            m = MAIN_RE.search(t2)
            if not m:
                continue
            t2 = t2[:m.end()] + HTML + t2[m.end():]
        if t2 != t:
            open(p, "w", encoding="utf-8", newline="").write(t2)
            changed += 1
    print("賀詞交歓会バナー:", "表示" if show else "撤去", changed, "ページ")


if __name__ == "__main__":
    main()

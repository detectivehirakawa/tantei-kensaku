"""届出証明書番号と管理番号が違う業者を、どちらの番号で検索しても見つかるようにする（2026-11-16 運営者指示）。

公安委員会の一覧には「届出証明書番号」「管理番号」の2欄があり、約2,600件は値が違う（all.json の j）。
当サイトのページは1欄目の番号だけで書かれているので、管理番号で Google 検索しても出てこなかった。
表示する番号・URL・リンクは変えず、検索に引っかかるように次の2つだけを足す（あくまで検索用）。

  1. 掲載ページの掲載証のすぐ下に、2つの番号を併記した一文（<!--kno-->〜<!--/kno-->）※2026-11-22に届出情報の末尾から移動
  2. 構造化データの identifier に「管理番号」を追加

display_no.json で表示番号を差し替えている業者にも同じ一文を出す（欄の名前は書かず番号だけ）。構造化データは触らない。
何度実行しても同じ結果になる。listed-hero.yml の中で毎回実行する。

  python tantei-portal-tools/render_kanri_no.py
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "tantei-portal-data")
A, B = "<!--kno-->", "<!--/kno-->"


def main():
    rows = json.load(open(os.path.join(ROOT, "all.json"), encoding="utf-8"))
    try:
        dno = json.load(open(os.path.join(DATA, "display_no.json"), encoding="utf-8"))
    except Exception:
        dno = {}
    changed = 0
    CERT = re.compile(r'<div class="cert-foot">[^<]*</div>\s*</div>')
    for r in rows:
        i, j = r.get("i"), r.get("j")
        if not j or j == i:
            continue
        p = os.path.join(ROOT, "biz", i + ".html")
        if not os.path.exists(p):
            continue
        s = open(p, encoding="utf-8", newline="").read()
        t = re.sub(re.escape(A) + r".*?" + re.escape(B), "", s, flags=re.S)
        if i in dno:
            # 表示番号を差し替えている業者は、掲載証の「届出番号」が2つ目の欄の番号なので、欄の名前は書かない
            nums = f'<b>{dno[i]}</b>と<b>{i}</b>'
        else:
            nums = f'<b>届出証明書番号 {i}</b>と<b>管理番号 {j}</b>'
        note = (f'{A}<p class="biz-kno" style="font-size:.85rem;color:#4a5665;margin:12px 0 14px">'
                f'公安委員会の届出業者一覧では、この業者に{nums}の2つの番号が載っています。'
                f'どちらの番号で検索しても、この掲載ページが見つかります。</p>{B}')
        # 置き場所は掲載証のすぐ下（2026-11-22 運営者指示）。掲載証が無いページだけ、届出情報の末尾に置く
        m = CERT.search(t)
        if m:
            t = t[:m.end()] + note + t[m.end():]
        else:
            k = t.find("</section><!--/biz-facts-->")
            if k == -1:
                continue
            t = t[:k] + note + t[k:]
        if i in dno:
            if t != s:
                open(p, "w", encoding="utf-8", newline="").write(t)
                changed += 1
            continue
        old = f'"identifier":{{"@type":"PropertyValue","name":"探偵業届出証明書番号","value":"{i}"}}'
        new = (f'"identifier":[{{"@type":"PropertyValue","name":"探偵業届出証明書番号","value":"{i}"}},'
               f'{{"@type":"PropertyValue","name":"管理番号（公安委員会の届出業者一覧）","value":"{j}"}}]')
        t = t.replace(old, new)
        if t != s:
            open(p, "w", encoding="utf-8", newline="").write(t)
            changed += 1
    print(f"kanri-no: {changed} pages")


if __name__ == "__main__":
    main()

"""都道府県コラムの予約公開（2026-11-19、運営者指示「1日3本ずつ」）。

予約分は別ブランチ column-queue の <日付>/ に置いてある（運営者PCの detective-portal/columns/pref_pack/build_queue.py が作る）:
  <日付>/manifest.json  {"slug": "tokyo", "pref": "東京都", "main": {"slug": "...", "title": "..."}, "files": ["tokyo/column/xxx.html", ...]}
  <日付>/files/<path>    公開するHTML（記事3本と県のコラム一覧）
  <日付>/box.html        県ページに入れる「〇〇県のコラム」欄（<!--pref-col-->〜<!--/pref-col-->）

  python publish_pref_columns.py <queueのフォルダ> [YYYY-MM-DD]   日付を省くと今日（日本時間）。今日以前でまだ公開していない日付をすべて公開する

やること: ファイルを置く → 県ページにコラム欄 → 県内の市区町村ページの「選ぶときのポイント」に記事への案内 → sitemap 更新。
何度実行しても同じ結果になる。publish-pref-columns.yml が毎朝7時（日本時間）に実行する。
"""
import datetime
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOX_RE = re.compile(r"<!--pref-col-->.*?<!--/pref-col-->", re.S)
NOTE = '<div class="note">営業所住所は'


def publish(qdir, day):
    m = json.load(open(os.path.join(qdir, day, "manifest.json"), encoding="utf-8"))
    s, pref = m["slug"], m["pref"]
    changed = []
    for rel in m["files"]:
        src = os.path.join(qdir, day, "files", *rel.split("/"))
        dst = os.path.join(ROOT, *rel.split("/"))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        new = open(src, encoding="utf-8").read()
        if not os.path.exists(dst) or open(dst, encoding="utf-8").read() != new:
            shutil.copyfile(src, dst)
            changed.append(rel)
    # 県ページのコラム欄
    box = open(os.path.join(qdir, day, "box.html"), encoding="utf-8").read().strip()
    pp = os.path.join(ROOT, s + ".html")
    t = open(pp, encoding="utf-8").read()
    if BOX_RE.search(t):
        t2 = BOX_RE.sub(lambda _: box, t, count=1)
    elif NOTE in t:
        t2 = t.replace(NOTE, box + "\n" + NOTE, 1)
    else:
        raise SystemExit(f"{s}.html にコラム欄を入れる位置がありません")
    if t2 != t:
        open(pp, "w", encoding="utf-8", newline="").write(t2)
        changed.append(s + ".html")
    # 市区町村ページ: 「選ぶときのポイント」の最後の段落に、県のコラムへの案内を足す
    main = m["main"]
    add = f'<br>{pref}の地域事情や探偵の探し方は「<a href="./column/{main["slug"]}.html">{main["title"]}</a>」にまとめています。'
    cdir = os.path.join(ROOT, s)
    for f in sorted(os.listdir(cdir)) if os.path.isdir(cdir) else []:
        if not f.endswith(".html"):
            continue
        cp = os.path.join(cdir, f)
        t = open(cp, encoding="utf-8").read()
        i = t.find("選ぶときのポイント")
        if i < 0 or f"./column/{main['slug']}.html" in t:
            continue
        j = t.find("で解説しています。</p>", i)
        if j < 0:
            continue
        j += len("で解説しています。")
        t = t[:j] + add + t[j:]
        open(cp, "w", encoding="utf-8", newline="").write(t)
        changed.append(f"{s}/{f}")
    print(day, pref, "更新", len(changed), "ファイル")
    return changed


def main():
    qdir = sys.argv[1]
    today = sys.argv[2] if len(sys.argv) > 2 else datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=9))).date().isoformat()
    # 公開済みの日付は記録して、2回目以降は触らない（公開後に手で直した内容を戻さないため）
    sp = os.path.join(ROOT, "tantei-portal-data", "pref_columns_published.json")
    state = json.load(open(sp, encoding="utf-8")) if os.path.exists(sp) else {}
    days = sorted(d for d in os.listdir(qdir) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) and d <= today and d not in state)
    done = 0
    for d in days:
        publish(qdir, d)
        state[d] = json.load(open(os.path.join(qdir, d, "manifest.json"), encoding="utf-8"))["slug"]
        done += 1
    if done:
        json.dump(dict(sorted(state.items())), open(sp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if done:
        subprocess.run([sys.executable, os.path.join(ROOT, "tantei-portal-tools", "make_sitemap.py")], check=False)
    print("公開した日数:", done)


if __name__ == "__main__":
    main()

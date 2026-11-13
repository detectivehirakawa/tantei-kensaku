"""掲載ページ・都道府県一覧に出す届出番号を、業者の届出証明書の番号に差し替える（2026-11-14）。

公安委員会の届出業者一覧には「届出証明書番号」と「管理番号」の2つの欄があり、全国で約2,600件は値が違う。
当サイトのページ番号（URL）は1つ目の欄だが、業者の手元の証明書が2つ目の欄の番号のことがある（例: 総合探偵社insight
一覧 10249010 / 証明書 10240018）。業者から申し出があり運営者が確認したものだけ、表示する番号を差し替える。

データ: tantei-portal-data/display_no.json  { "<ページ番号>": "<表示する届出番号>" }

- 掲載ページ: 番号を表示している欄（カードの「届出番号」、プロフィールの「探偵業届出番号」、届出情報の「届出番号」）を差し替え、
  届出情報に「一覧での番号」の行を1つ足す（<!--dno-->〜<!--/dno-->）。URL・構造化データ・リンクの番号は変えない。
- 都道府県一覧: その業者の行の届出番号の欄を差し替える。
何度実行しても同じ結果になる。GAS が承認でページを作り直しても、listed-hero.yml の中で毎回実行されるので戻る。

  python tantei-portal-tools/render_display_no.py
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "tantei-portal-data")


def rw(path, fn):
    if not os.path.exists(path):
        return False
    s = open(path, encoding="utf-8", newline="").read()
    t = fn(s)
    if t != s:
        open(path, "w", encoding="utf-8", newline="").write(t)
        return True
    return False


def biz_fix(pid, shown):
    def fn(s):
        s = s.replace("<dd>%s</dd>" % pid, "<dd>%s</dd>" % shown)
        s = s.replace("第%s号" % pid, "第%s号" % shown)
        s = re.sub(r"<!--dno-->.*?<!--/dno-->", "", s, flags=re.S)
        note = ("<!--dno--><dt>一覧での番号</dt><dd>%s（公安委員会の届出業者一覧では、この番号の欄に載っています。"
                "当サイトのページの番号にも使っています）</dd><!--/dno-->" % pid)
        # 届出情報（biz-facts）の「届出番号」の行の直後に入れる
        s = re.sub(r'(<section class="bf"><h2>[^<]*の届出情報</h2><dl><dt>届出番号</dt><dd>%s</dd>)' % re.escape(shown),
                   lambda m: m.group(1) + note, s, count=1)
        return s
    return fn


def main():
    m = json.load(open(os.path.join(DATA, "display_no.json"), encoding="utf-8"))
    all_biz = {x["i"]: x for x in json.load(open(os.path.join(ROOT, "all.json"), encoding="utf-8"))}
    for pid, shown in m.items():
        if pid.startswith("_"):
            continue
        if rw(os.path.join(ROOT, "biz", pid + ".html"), biz_fix(pid, shown)):
            print(pid, "掲載ページを更新")
        b = all_biz.get(pid) or {}
        if b.get("s"):
            pref = os.path.join(ROOT, b["s"] + ".html")
            if rw(pref, lambda s: s.replace('<tr id="n%s" class="pref-row-featured"><td>%s</td>' % (pid, pid),
                                             '<tr id="n%s" class="pref-row-featured"><td>%s</td>' % (pid, shown))
                  .replace('<tr id="n%s"><td>%s</td>' % (pid, pid), '<tr id="n%s"><td>%s</td>' % (pid, shown))):
                print(pid, "都道府県一覧を更新")


if __name__ == "__main__":
    main()

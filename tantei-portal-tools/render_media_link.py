"""全ページのヘッダーとフッターに「メディア・報道関係の方へ」（media.html）へのリンクを入れる（2026-11-22 運営者指示）。

- ヘッダー: ナビの「掲載のお申込み」の次に「メディアの方へ」
- フッター: 「更新・訂正履歴」の次に「メディア・報道関係の方へ」
ページごとの階層（./ ../ ../../）は、その場にあるリンクの書き方に合わせる。何度実行しても同じ結果になる。
GAS の承認や、あとから公開されるコラムで元の形に戻っても、ワークフローの中で毎回実行して入れ直す。

  python tantei-portal-tools/render_media_link.py [ファイル ...]   （ファイル省略で全ページ）
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICON = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" '
        'aria-hidden="true"><path d="M4 5h13v14H6a2 2 0 0 1-2-2z"/><path d="M17 9h3v8a2 2 0 0 1-2 2"/><path d="M8 9h5M8 13h5"/></svg>')
HEAD = re.compile(r'(<a href="(/|(?:\.\./|\./)*)contact\.html(?:#top)?"><svg[^>]*>(?:(?!</svg>).)*</svg>掲載のお申込み</a>)(?!<a href="[^"]*media\.html")', re.S)
FOOT = re.compile(r'(<li><a href="(/|(?:\.\./|\./)*)changelog\.html(?:#top)?">更新・訂正履歴</a></li>)(?!<li><a href="[^"]*media\.html")')


FOOT2 = re.compile(r'(<li><a href="(/|(?:\.\./|\./)*)policy\.html(?:#top)?">掲載基準・編集方針</a></li>)')
FOOTER = re.compile(r'<footer class="t-foot">.*?</footer>', re.S)


def fix_footer(f):
    if "media.html" in f:
        return f
    g = FOOT.sub(lambda m: m.group(1) + f'<li><a href="{m.group(2)}media.html">メディア・報道関係の方へ</a></li>', f, count=1)
    if g == f:  # 「更新・訂正履歴」が無い形のフッターは「掲載基準・編集方針」の次に入れる
        g = FOOT2.sub(lambda m: m.group(1) + f'<li><a href="{m.group(2)}media.html">メディア・報道関係の方へ</a></li>', f, count=1)
    return g


def fix(s):
    s = HEAD.sub(lambda m: m.group(1) + f'<a href="{m.group(2)}media.html">{ICON}メディアの方へ</a>', s)
    s = FOOTER.sub(lambda m: fix_footer(m.group(0)), s)   # フッターの中だけ（本文の関連リンクには入れない）
    return s


def main():
    files = sys.argv[1:]
    if not files:
        files = [p for pat in ("*.html", "*/*.html", "*/*/*.html") for p in glob.glob(os.path.join(ROOT, pat))]
    n = 0
    for p in files:
        try:
            s = open(p, encoding="utf-8", newline="").read()
        except (OSError, UnicodeDecodeError):
            continue
        t = fix(s)
        if t != s:
            open(p, "w", encoding="utf-8", newline="").write(t)
            n += 1
    print(f"media-link: {n} pages")


if __name__ == "__main__":
    main()

"""コラムの監修者欄の肩書を、運営者情報・メディア向けページと同じにそろえる（2026-11-22 運営者指示）。

「合同会社EXE RESEARCH 代表」→「探偵業界アナリスト・探偵業データ研究家／合同会社EXE RESEARCH 代表」
対象は column/ と <県>/column/ の記事（記事上部の「監修：…（肩書）」、記事下の監修者欄、構造化データの jobTitle）。
何度実行しても同じ結果になる。予約公開のコラム（column-queue ブランチ）は古い肩書で作ってあるので、
publish-pref-columns.yml の中で毎回実行してそろえる。

  python tantei-portal-tools/render_supervisor_role.py
"""
import glob
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OLD, NEW = "合同会社EXE RESEARCH 代表", "探偵業界アナリスト・探偵業データ研究家／合同会社EXE RESEARCH 代表"
PAIRS = [
    (f"（{OLD}）</p>", f"（{NEW}）</p>"),
    (f'<p class="p-role">{OLD}<br>', f'<p class="p-role">{NEW}<br>'),
    (f'"jobTitle":"{OLD}"', f'"jobTitle":"{NEW}"'),
]


def main():
    n = 0
    for p in glob.glob(os.path.join(ROOT, "column", "*.html")) + glob.glob(os.path.join(ROOT, "*", "column", "*.html")):
        s = open(p, encoding="utf-8", newline="").read()
        t = s
        for a, b in PAIRS:
            t = t.replace(a, b)
        if t != s:
            open(p, "w", encoding="utf-8", newline="").write(t)
            n += 1
    print(f"supervisor-role: {n} pages")


if __name__ == "__main__":
    main()

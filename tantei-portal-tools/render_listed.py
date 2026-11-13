"""全国探偵検索：掲載済みの探偵社の掲載ページ（biz/<届出番号>.html）を、
「ひと目でわかる表 → 紹介文 → プロフィール表」の構成に組み直す。

なぜ必要か：
  掲載の承認（GAS）と手元のフルリビルド（build_site.py）は、どちらも以前の構成
  （サービス内容・強み ＋ 項目の表）で掲載ページを書き出す。このスクリプトはその出力を
  受け取って構成だけを組み直すので、GAS と build_site.py は変えなくてよい。
  GitHub Actions（.github/workflows/listed-hero.yml）が、掲載の承認や業者ページの更新の
  たびに実行する。何度実行しても結果は同じ（変更がなければ何も書き換えない）。

データ：
  tantei-portal-data/biz_extra.json    … GAS が管理する掲載内容（フォームの入力。プロフィール項目
                                          corpName / founded / staff / payment / successFee / expenses /
                                          estimate / lawyer / groups / awards を含む）
  tantei-portal-data/biz_profile.json  … このリポジトリだけで管理する追加情報（GAS は触らない）
      "_legacy": ["届出番号", …]   以前の構成のまま残す業者（ここから外すと新しい構成になる）
      "<届出番号>": {
          "summary": [["項目", "値"], …]      ひと目でわかる表を丸ごと指定（省略時は自動）
          "profile": [["項目", "値"], …]      プロフィール表を丸ごと指定（省略時は自動）
          "profile_add": [["項目", "値"], …]  自動のプロフィール表の末尾に足す行
          "note": "…"                         カード末尾の注記（省略時は「ご提供情報（○○更新）」）
      }

GAS 側の対応（2026-11-13、Web エディタで直接変更・バージョン56・VERSION '2026-11-13d'）：
  プロフィール項目を受け取れるように、Code.gs の sanitizeFields_ ／ doApprove_ の extraEntry ／
  editDiffText_ の labels に上記10個のキーを追加した。手元の Code.gs から GAS をデプロイし直すときは、
  先に同じ変更を手元にも入れること（入れないと、フォームのプロフィール項目が保存されなくなる）。

紹介文は、ページにすでにある本文（<div class="biz-svc">…</div>）をそのまま使う。
フォームの「サービス内容」に【どんな探偵社？】のような見出し行があれば、GAS がそれを
見出しとして出力するので、4つの見出しの紹介文になる。
"""
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "tantei-portal-data")
BIZ = os.path.join(ROOT, "biz")

CARD_OPEN = '<div class="biz-card">'
# GAS の replaceExtraBlock_ と同じ目印。カードの直後に必ずこの注記が続く。
TRAILING_NOTE = '<div class="note">この情報は都道府県公安委員会への届出情報'
MARK = "<!--listed-v2-->"
CATCH_STYLE = "color:var(--accent-ink);font-weight:700;margin:0 0 10px"
NOTE_STYLE = "color:#888;font-size:.8em;margin-top:10px"


def esc(t):
    return html.escape(str(t or ""), quote=True)


def linkify(t):
    """エスケープしたうえで、URL だけをリンクにする。"""
    out, pos = [], 0
    for m in re.finditer(r"https?://[^\s\"'<>]+", t):
        out.append(esc(t[pos:m.start()]))
        u = esc(m.group())
        out.append('<a href="%s" target="_blank" rel="noopener">%s</a>' % (u, u))
        pos = m.end()
    out.append(esc(t[pos:]))
    return "".join(out)


def div_block(s, start):
    """s[start] から始まる <div …> の、対応する </div> までを返す。見つからなければ ''。"""
    if start < 0:
        return ""
    depth = 0
    for m in re.finditer(r"<div\b|</div>", s[start:]):
        depth += 1 if m.group() != "</div>" else -1
        if depth == 0:
            return s[start:start + m.end()]
    return ""


def dl(rows):
    return "<dl>" + "".join(
        '<dt>%s</dt><dd style="white-space:pre-wrap">%s</dd>' % (esc(k), linkify(str(v)))
        for k, v in rows if str(v or "").strip()
    ) + "</dl>"


def joined(v, sep="、"):
    return sep.join(str(x) for x in v if x) if isinstance(v, list) else str(v or "")


def site_urls(entry):
    """公式サイトなどのURL（LINEのURLはボタンにだけ使うので表には出さない。GAS と同じ扱い）。"""
    lines = [x.strip() for x in str(entry.get("url") or "").split("\n")]
    return "\n".join(x for x in lines if x and not re.search(r"line\.me|lin\.ee", x))


def auto_summary(entry):
    hours, methods = str(entry.get("hours") or "").strip(), joined(entry.get("methods") or [], "・")
    reception = hours + ("（%s）" % methods if hours and methods else methods)
    return [
        ["対応できる調査", joined(entry.get("types") or [])],
        ["料金の目安", entry.get("price")],
        ["支払い方法", entry.get("payment")],
        ["対応エリア", entry.get("area")],
        ["相談受付", reception],
    ]


def auto_profile(bid, name, entry, biz):
    pref = (biz or {}).get("p") or ""
    # 北海道は方面ごとに公安委員会が分かれるので、委員会名は書かない
    todokede = ("%s公安委員会 第%s号" % (pref, bid)) if pref and pref != "北海道" else "第%s号" % bid
    # 法人名〜受賞・資格は、掲載フォームのプロフィール欄（2026-11-13 追加）。空欄の行は出さない。
    return [
        ["屋号", name],
        ["法人名", entry.get("corpName")],
        ["設立", entry.get("founded")],
        ["代表者", entry.get("repName")],
        ["所在地", entry.get("officeAddress") or (biz or {}).get("a")],
        ["探偵業届出番号", todokede],
        ["所属団体", entry.get("groups")],
        ["受賞・資格", entry.get("awards")],
        ["従業員数", entry.get("staff")],
        ["対応可能な調査", joined(entry.get("types") or [])],
        ["対応エリア", entry.get("area")],
        ["料金の目安", entry.get("price")],
        ["成功報酬の有無", entry.get("successFee")],
        ["諸経費", entry.get("expenses")],
        ["支払い方法", entry.get("payment")],
        ["相談・見積もり", entry.get("estimate")],
        ["弁護士との連携", entry.get("lawyer")],
        ["営業時間", entry.get("hours")],
        ["ご相談方法", joined(entry.get("methods") or [])],
        ["電話番号", entry.get("pubphone")],
        ["公式サイト", site_urls(entry)],
        ["その他", entry.get("other")],
    ]


def render_card(bid, page, entry, biz, prof):
    """ページから今のカードを取り出し、新しい構成のカードと置き換える範囲を返す。"""
    trail = page.find(TRAILING_NOTE)
    start = page.rfind(CARD_OPEN, 0, trail) if trail != -1 else -1
    if start == -1:
        return None
    card = page[start:trail]
    m = re.search(r"<h1>(.*?)</h1>", page, flags=re.S)
    name = re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else (biz or {}).get("n", "")

    top_cta = div_block(card, card.find('<div class="biz-cta biz-cta--top">'))
    photos = div_block(card, card.find('<div class="biz-photos"'))
    intro = div_block(card, card.find('<div class="biz-svc">'))
    bottom_cta = div_block(card, card.rfind('<div class="biz-cta">'))

    summary = prof.get("summary") or auto_summary(entry)
    profile = prof.get("profile") or auto_profile(bid, html.unescape(name), entry, biz)
    profile = list(profile) + list(prof.get("profile_add") or [])
    updated = str(entry.get("updated") or "").strip()
    note = prof.get("note") or ("掲載業者様からのご提供情報" + ("（%s更新）" % updated if updated else ""))

    def head(title):
        return ('<section class="biz-svc-wrap" style="padding-bottom:14px">'
                '<h2 class="svc-title">%s</h2></section>' % title)

    parts = []
    if str(entry.get("catch") or "").strip():
        parts.append('<p style="%s">%s</p>' % (CATCH_STYLE, esc(entry["catch"])))
    parts += [top_cta, photos]
    parts.append(head("ひと目でわかる" + name) + dl(summary))
    if intro:
        parts.append('<section class="biz-svc-wrap"><h2 class="svc-title">%sの紹介</h2>%s</section>' % (name, intro))
    parts.append(head(name + "のプロフィール") + dl(profile))
    parts.append(bottom_cta)
    parts.append('<p style="%s">%s</p>' % (NOTE_STYLE, esc(note)))
    new_card = CARD_OPEN + MARK + "".join(p for p in parts if p) + "</div>\n"
    return page[:start] + new_card + page[trail:]


def main():
    extra = json.load(open(os.path.join(DATA, "biz_extra.json"), encoding="utf-8"))
    permitted = json.load(open(os.path.join(DATA, "permitted.json"), encoding="utf-8"))
    prof_path = os.path.join(DATA, "biz_profile.json")
    profiles = json.load(open(prof_path, encoding="utf-8")) if os.path.exists(prof_path) else {}
    legacy = set(profiles.get("_legacy") or [])
    all_biz = {x["i"]: x for x in json.load(open(os.path.join(ROOT, "all.json"), encoding="utf-8"))}

    changed = 0
    for bid in sorted(permitted):
        if bid in legacy:
            print(bid, "以前の構成のまま（_legacy）"); continue
        entry = extra.get(bid)
        path = os.path.join(BIZ, bid + ".html")
        if not entry or not os.path.exists(path):
            print(bid, "掲載内容またはページが無いのでスキップ"); continue
        page = open(path, encoding="utf-8").read()
        new = render_card(bid, page, entry, all_biz.get(bid), profiles.get(bid) or {})
        if new is None:
            print(bid, "カードの位置を特定できないのでスキップ"); continue
        if new != page:
            open(path, "w", encoding="utf-8").write(new)
            changed += 1
            print(bid, "新しい構成に組み直しました")
        else:
            print(bid, "変更なし")
    print("更新したページ:", changed)


if __name__ == "__main__":
    sys.exit(main())

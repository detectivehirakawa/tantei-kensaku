"""業者ページに、AI（ChatGPT・Perplexity など）や検索エンジンがそのまま引用できる
「一文の要約」と、届出番号の構造化データを入れる（LLMO対策・2026-11-15）。

  python tantei-portal-tools/render_llmo.py

- 届出情報の枠（<!--biz-facts--> の <section class="bf"> の見出し）の直後に
  <p class="bf-sum"><!--llmo-sum-->…<!--/llmo-sum--></p> を入れる。中身は同じ枠の表から作る
  （表示する届出番号の差し替え render_display_no.py の後に実行すること）。
- LocalBusiness の構造化データに identifier（探偵業の届出番号）を足す。
- 何度実行しても同じ結果になる（既にあれば作り直す）。
"""
import glob
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUM_RE = re.compile(r'<p class="bf-sum"><!--llmo-sum-->.*?<!--/llmo-sum--></p>', re.S)
SEC_RE = re.compile(r'(<section class="bf"><h2>(.*?)の届出情報</h2>)(.*?)</section>', re.S)
LD_RE = re.compile(r'(<script type="application/ld\+json">)(.*?)(</script>)', re.S)
CSS = '.bf .bf-sum{font-size:.92rem;line-height:1.85;margin:0 0 12px;color:#1a2430}'


def dd(block, label):
    m = re.search(r"<dt>%s</dt><dd>(.*?)</dd>" % re.escape(label), block, re.S)
    return re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else ""


def pref_of(addr):
    m = re.match(r"(北海道|東京都|京都府|大阪府|.{2,3}県)", addr)
    return m.group(1) if m else ""


def summary(name, block):
    num = dd(block, "届出番号")
    addr = dd(block, "営業所の所在地")
    year = re.match(r"(\d{4})年", dd(block, "届出をした年"))
    pref = pref_of(addr)
    if not (num and addr and pref):
        return ""
    s = f"{name}は、{addr}に営業所がある探偵業者です。{pref}公安委員会に探偵業の届出をしており、届出番号は{num}"
    s += f"（{year.group(1)}年の届出）です。" if year else "です。"
    s += "このページの内容は、令和8年5月31日時点の公安委員会の届出情報にもとづいています。"
    return s


def fix_ld(html, num):
    def rep(m):
        try:
            data = json.loads(m.group(2).replace("<\\/", "</"))
        except ValueError:
            return m.group(0)
        changed = False
        for node in data.get("@graph", [data]) if isinstance(data, dict) else []:
            if isinstance(node, dict) and node.get("@type") == "LocalBusiness":
                want = {"@type": "PropertyValue", "name": "探偵業届出証明書番号", "value": num}
                if node.get("identifier") != want:
                    node["identifier"] = want
                    changed = True
        if not changed:
            return m.group(0)
        out = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
        return m.group(1) + out + m.group(3)
    return LD_RE.sub(rep, html)


def process(path):
    with open(path, encoding="utf-8") as f:
        html = f.read()
    m = SEC_RE.search(html)
    if not m:
        return False
    name = re.sub(r"<[^>]+>", "", m.group(2)).strip()
    block = m.group(3)
    text = summary(name, block)
    if not text:
        return False
    new = SUM_RE.sub("", html)
    m = SEC_RE.search(new)
    para = f'<p class="bf-sum"><!--llmo-sum-->{text}<!--/llmo-sum--></p>'
    new = new[:m.end(1)] + para + new[m.end(1):]
    if CSS not in new:
        new = new.replace(".bf a{color:var(--t-blue,#1a5fb4)}</style>",
                          ".bf a{color:var(--t-blue,#1a5fb4)}" + CSS + "</style>", 1)
    new = fix_ld(new, dd(block, "届出番号"))
    if new != html:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(new)
        return True
    return False


def main():
    files = sorted(glob.glob(os.path.join(ROOT, "biz", "*.html")))
    n = sum(process(p) for p in files)
    print(f"render_llmo: {n}/{len(files)} ページを更新")


if __name__ == "__main__":
    main()

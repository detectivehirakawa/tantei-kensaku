"""変わったページを IndexNow（Bing など）に知らせる（2026-11-14）。

  python tantei-portal-tools/indexnow_ping.py <比べる元のコミット>

元のコミットから今までに変わった .html を tantei-kensaku.jp の URL にして送る。
キーはリポジトリ直下の <32桁の16進>.txt（公開して確認してもらう前提のファイルなので秘密ではない）。
送れなくてもワークフローは止めない。
"""
import glob
import json
import os
import re
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST = "tantei-kensaku.jp"


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else ""
    keys = [os.path.basename(p)[:-4] for p in glob.glob(os.path.join(ROOT, "*.txt"))
            if re.fullmatch(r"[0-9a-f]{32}\.txt", os.path.basename(p))]
    if not keys or not re.fullmatch(r"[0-9a-f]{40}", base or ""):
        print("IndexNow: キーまたは比較元がないので送らない")
        return
    try:
        out = subprocess.run(["git", "diff", "--name-only", base, "HEAD"], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout
    except subprocess.CalledProcessError as e:
        print("IndexNow: 差分を取れなかった", e.stderr[:200])
        return
    urls = []
    for f in out.splitlines():
        if not f.endswith(".html") or not os.path.exists(os.path.join(ROOT, f)):
            continue
        urls.append("https://%s/%s" % (HOST, "" if f == "index.html" else f))
    if "https://%s/biz/" % HOST in "".join(urls):
        urls.append("https://%s/" % HOST)
    urls = sorted(set(urls))[:9000]
    if not urls:
        print("IndexNow: 変わったページなし")
        return
    body = json.dumps({"host": HOST, "key": keys[0], "keyLocation": "https://%s/%s.txt" % (HOST, keys[0]),
                       "urlList": urls}).encode()
    req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body,
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        r = urllib.request.urlopen(req, timeout=60)
        print("IndexNow: %d件を送信 (%s)" % (len(urls), r.status))
    except Exception as e:  # noqa: BLE001 送れなくても止めない
        print("IndexNow: 送信できなかった", e)


if __name__ == "__main__":
    main()

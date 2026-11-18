"""掲載承認の直後に、サービス内容へ「文ごとの改行」と「**太字**」だけを入れる（2026-11-18）。

GAS（requestFormat_）→ repository_dispatch(format-service) → このスクリプト。
Claude Code（月額プランの CLAUDE_CODE_OAUTH_TOKEN）に整形させ、文言が変わっていないことを
確かめてから GAS の fmtdone に送る。GAS 側でも同じ確認をしてから掲載ページを作り直す。

  python format_service.py payload.json          # 本番（GAS に送る）
  python format_service.py payload.json --dry    # 整形と確認だけ（送らない）
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

GAS_URL = ("https://script.google.com/macros/s/"
           "AKfycbw5fWMGBB5glT-CAK0E_RUurrdMMw8tlRvU2g7dSs0LM2yVP9GJS2K11-pdbtv4BXAJOw/exec")
MODEL = "claude-sonnet-5-5"

PROMPT = """あなたは探偵事務所の紹介文を読みやすく整える係です。
下の <text> の文章に、次の2つだけを行ってください。

1. 改行: 長い段落は「。」の直後で改行して、1文を1行にする。段落の区切りは空行1つ。
   見出し行（【】だけの行）、「・」「●」「■」「①」などで始まる行は、行のつくりを変えない。
2. 太字: 依頼者に伝えたい要点を **語句** で囲む。3〜8か所。
   選ぶのは、強み・実績や数字・対応地域・資格や届出・無料や安心材料など。
   1か所は4〜20字程度の語句にし、文全体や見出し全体は囲まない。

絶対に守ること:
- 文字を1文字も足さない・消さない・言い換えない（句読点・記号・全角半角・空白以外の文字もそのまま）。
- 【】や「・」を新しく足さない。足してよいのは改行と ** だけ。
- 説明や前置きは書かず、整えた文章だけを <out> と </out> の間に入れて返す。

<text>
{text}
</text>"""


def norm(s):
    return re.sub(r"\s+", "", s.replace("**", ""))


def check(orig, out):
    if "**" not in out:
        return "太字がありません"
    if out.count("**") % 2:
        return "** の数が奇数です"
    if norm(orig) != norm(out):
        return "文言が変わっています"
    if re.search(r"\*\*\s*\*\*", out):
        return "空の太字があります"
    return ""


def run_claude(text):
    r = subprocess.run(
        ["claude", "-p", PROMPT.format(text=text), "--model", MODEL, "--max-turns", "2",
         "--output-format", "text"],
        capture_output=True, text=True, encoding="utf-8", timeout=600)
    m = re.search(r"<out>\n?(.*?)\n?</out>", r.stdout, re.S)
    if not m:
        print("Claude の出力に <out> がありません。stderr:", r.stderr[-500:])
        return ""
    return re.sub(r"\n{3,}", "\n\n", m.group(1).replace("\r", "")).strip()


def post(payload):
    req = urllib.request.Request(GAS_URL, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as res:  # GAS は 302 → GET で結果を返す
        return json.loads(res.read().decode("utf-8"))


def main():
    p = json.load(open(sys.argv[1], encoding="utf-8"))
    dry = "--dry" in sys.argv
    orig = str(p.get("service") or "").replace("\r", "")
    sub = str(p.get("sub") or "")
    if not orig.strip() or (not sub and not dry):
        print("入力がありません"); return 0
    out = ""
    for attempt in range(2):
        cand = run_claude(orig)
        err = check(orig, cand) if cand else "出力なし"
        if not err:
            out = cand; break
        print(f"{attempt + 1}回目: 採用しません（{err}）")
    if not out:
        print("整形できなかったので、承認時の自動太字のままにします"); return 0
    print("---- 整形結果 ----\n" + out)
    if dry:
        return 0
    secret = os.environ.get("FMT_SECRET", "")
    for attempt in range(3):
        try:
            r = post({"key": "tanteiportal", "mode": "fmtdone", "secret": secret, "sub": sub, "service": out})
        except Exception as e:  # noqa: BLE001
            r = {"ok": False, "error": str(e)}
        print("GAS:", {k: v for k, v in r.items() if k != "secret"})
        if r.get("ok"):
            return 0
        if any(w in str(r.get("error", "")) for w in ("認証", "文言", "整形済み", "見つかりません", "未承認", "太字")):
            return 1
        time.sleep(40)
    return 1


if __name__ == "__main__":
    sys.exit(main())

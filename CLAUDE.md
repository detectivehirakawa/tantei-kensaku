# 全国探偵無料検索サービス（tantei-kensaku.jp）引き継ぎメモ

Claude 向けの引き継ぎメモです。このリポジトリは公開されているので、秘密の値（キー・トークン・個人の連絡先）はここに書かないでください。

## ★ GAS をデプロイする前に必ず確認すること

Apps Script「探偵ポータル問い合わせ受付」の Code.gs は、2026-11-13 に **Web エディタで直接変更** し、同じデプロイ ID のままバージョン 56 として反映しました（`VERSION = '2026-11-13d'`）。

手元（PC）の Code.gs には、この変更が入っていない可能性があります。**gas.py などで手元からデプロイする前に、Web 上の最新版を取り込む（または下の変更を手元にも入れる）こと。** 入れずにデプロイすると、掲載フォームのプロフィール項目が保存されなくなります（フォームには欄が出たままなので、気づきにくい不具合になります）。

変更点（追加したキー: `corpName, founded, staff, payment, successFee, expenses, estimate, lawyer, groups, awards`）

1. `sanitizeFields_` の戻り値に 10 個のキーを追加
2. `doApprove_` の `extraEntry` に 10 個のキーを追加
3. `editDiffText_` の `labels` に 10 個のキーを追加（編集依頼メールの「変更点」に出すため）
4. `VERSION` を `'2026-11-13d'` に変更

取り込みが済んだら、この節に「手元へ取り込み済み（日付）」と追記してください。

- 2026-11-13 手元へ取り込み済み。続けて、以前の構成（_legacy の4社）の掲載ページでも10項目が表示されるよう、Code.gs の EXTRA_FIELDS_ と build_site.py の EXTRA_FIELDS に追加し、バージョン57（VERSION 2026-11-13e）としてデプロイ済み。

## 掲載ページ（biz/<届出番号>.html）の構成

- 掲載済み業者のページは「ひと目でわかる表 → 紹介文 → プロフィール表」の構成です（2026-11-13 から）。
- GAS の承認処理と手元の build_site.py は、以前の構成（サービス内容・強み ＋ 項目の表）で書き出します。そのあと GitHub Actions（`.github/workflows/listed-hero.yml`）が `tantei-portal-tools/render_listed.py` を実行し、新しい構成に自動で組み直します。**GAS と build_site.py の出力形式は変えなくて構いません。**
- ただし、カードの外枠 `<div class="biz-card">` と、その直後の注記 `<div class="note">この情報は都道府県公安委員会への届出情報…` は置き換え位置の目印です。この2つは変えないでください。
- 掲載内容を直すときは、HTML ではなくデータを直します。HTML だけを直すと、次の承認や再生成で元に戻ります。
  - 紹介文 … `tantei-portal-data/biz_extra.json` の `service`（`【見出し】` だけの行が見出しになる）
  - 表 … `biz_extra.json` の各項目、または `tantei-portal-data/biz_profile.json`

## tantei-portal-data/biz_profile.json

このリポジトリだけで管理する追加情報です（GAS は触りません）。書式は `render_listed.py` の冒頭に説明があります。

- `_legacy` … 以前の構成のまま残す届出番号。現在は既存の掲載済み 4 社が入っています。運営者から指示があるまで外さないでください（外すと、その業者のページが新しい構成になります）。
- `43230060`（ラクーン探偵社）… 要約の表とプロフィール表を丸ごと指定しています。

## 掲載フォーム（edit.html）

- 紹介文は 4 つの欄（どんな探偵社？／調査内容と料金の目安／注目ポイント／相談を考えている方へ）です。送信時に `【見出し】` つきの 1 つの本文にまとめ、これまでと同じ `service` として送ります（合計 2000 字まで。GAS 側の上限と同じ）。
- プロフィール項目は上の 10 個のキーで送ります。上限の文字数は GAS の `sanitizeFields_` と同じにしてあります。

## 事務所名の変更（2026-11-13、GAS バージョン58・VERSION 2026-11-13f）

- edit.html に「事務所名」「事務所名のふりがな」欄（キー `dispName` / `dispKana`）。今の表示名を all.json から入れておき、業者が書き換えられる。
- 承認時（doApprove_）に、名前が今と違えば all.json の n/k、掲載ページ内の名前（タイトル・構造化データ含む）、都道府県一覧・市区町村ページの行と構造化データを差し替える。biz_extra.json にも dispName/dispKana を保存。
- build_site.py も biz_extra.json の dispName/dispKana を data/name_override.json の後に優先して使う（ビルドし直しても戻らない）。

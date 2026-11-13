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

## 確認バッジと調査の種類の絞り込み（2026-11-14、GAS バージョン59・VERSION 2026-11-14a）

- 掲載済みページのカード先頭に `<div class="biz-badges">`（届出確認済み・事務所が入力・所在地公開・代表者名公開・掲載料0円）。GAS の bizBadgesHtml_ と build_site.py の biz_badges_html が同じものを出し、render_listed.py はそのまま先頭に置く。
- トップの検索に「調査の種類」（#typeFilter）。biz_extra.json の types を実行時に読み、掲載済みの事務所だけを絞り込む（承認されれば自動で対象になる）。

## ホームページで確認した調査項目・Googleマップの★評価（2026-11-14）

- `tantei-portal-data/biz_web.json` … 未掲載の業者の「ホームページで確認できた調査項目」。サイトに届出番号が載っていて本人と確かめられたものだけ（大分県で試行：51件中12件）。`render_hp_types.py` が業者ページの `<!--/biz-facts-->` の後に書き込み、トップの「調査の種類」の絞り込みにも使う（「HPで確認」表示）。
- `tantei-portal-data/gbp.json` … 掲載済み業者の Googleマップの★・件数。`google_rating.py render` が「〇〇を利用したことがあるユーザーの感想」として書き込む（本文は課金のため出さない）。`gbp-rating.yml` が週1回取り直す（Secrets の PLACES_API_KEY が必要）。新しく掲載された業者は名前と市区町村が一致すれば自動で place_id を登録。
- どちらも listed-hero.yml の中で毎回実行（APIは呼ばない）。

## 届出番号と管理番号（2026-11-14、GAS バージョン61・VERSION 2026-11-14c）

- 公安委員会の一覧は「届出証明書番号」「管理番号」の2欄。当サイトのページ番号は1欄目。約2,600件は値が違い、業者が管理番号を名乗ることがある（例: 総合探偵社insight 10249010 / 10240018）。
- all.json の `j` に管理番号（違うものだけ）。トップの番号検索・edit.html の名前の自動入力・GAS の申込/承認/リンク確認/マイページのログインは、どちらの番号でも同じ業者になる（GAS の resolveBizId_）。
- 表示する番号の差し替えは `tantei-portal-data/display_no.json`（ページ番号→表示番号）を `render_display_no.py` が反映（listed-hero.yml 内）。管理番号で申し込まれた業者は、承認時に GAS が自動で display_no.json に入れる（運営者指示: 事業者の要望を優先）。

## セキュリティ点検（2026-11-14、GAS バージョン63・VERSION 2026-11-14e）

- マイページのログインコード・アプリの相談メールの送り先は、承認済みの申込（掲載充実/掲載内容の編集で「承認済み」欄あり）のメールだけ（Mypage.gs の mypageContact_）。
- 業者が入力した値を JS で HTML に入れるときは esc（& < > " ' を無害化）を通す。構造化データ（ld+json）は </ をエスケープする。
- なりすまし（リンク確認からの自動承認）は運営者が目視で確認する方針（運営者指示）。

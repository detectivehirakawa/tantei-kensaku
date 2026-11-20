/* 名簿（R8.5.31時点）より後に届出をした探偵業者の掲載申込（2026-11-20）。
   contact.html / edit.html の「届出番号」欄の下に入口を出し、開くと届出の情報と届出証明書の写真の欄を出す。
   送信時は payload.type='new'・payload.newReg・payload.cert（証明書の写真。GAS は非公開で保存）を足す。
   ?new=1 で開いた状態から始まる。 */
(function(){
  var PREFS = '北海道 青森県 岩手県 宮城県 秋田県 山形県 福島県 茨城県 栃木県 群馬県 埼玉県 千葉県 東京都 神奈川県 新潟県 富山県 石川県 福井県 山梨県 長野県 岐阜県 静岡県 愛知県 三重県 滋賀県 京都府 大阪府 兵庫県 奈良県 和歌山県 鳥取県 島根県 岡山県 広島県 山口県 徳島県 香川県 愛媛県 高知県 福岡県 佐賀県 長崎県 熊本県 大分県 宮崎県 鹿児島県 沖縄県'.split(' ');
  var sel = document.getElementById('selfId');
  if (!sel) return;
  var anchor = sel.closest('label') || sel;
  var css = document.createElement('style');
  css.textContent = '.form-card button.nr-btn,.nr-btn{display:block;width:100%;margin:2px 0 14px;padding:12px 14px;border:1px dashed var(--accent,#1668d8);background:#f3f8ff;color:var(--accent-ink,#0f4fa8);font:inherit;font-size:.92rem;font-weight:700;text-align:left;cursor:pointer;border-radius:6px;line-height:1.6}'
    + '.form-card button.nr-btn:hover{background:#e8f1ff}.nr-btn::after{content:" ＋";float:right}.nr-btn[aria-expanded=true]::after{content:" －"}'
    + '.nr-box{border:1px solid #cbd9ea;background:#f8fbff;border-radius:6px;padding:14px 14px 4px;margin:0 0 16px}'
    + '.nr-box p{font-size:.86rem;line-height:1.75;margin:0 0 12px;color:var(--body,#333)}'
    + '.nr-box select{width:100%;box-sizing:border-box;padding:12px;border:1px solid var(--line,#ccd);font:inherit;background:#fff}'
    + '.nr-thumb img{max-width:160px;max-height:120px;border:1px solid #cbd9ea;margin:6px 0 10px;display:block}';
  document.head.appendChild(css);

  var wrap = document.createElement('div');
  wrap.innerHTML =
    '<button type="button" class="nr-btn" id="nrToggle" aria-expanded="false" aria-controls="nrBox">検索しても届出番号が見つからない方（令和8年5月31日より後に届出をした方）はこちら</button>'
    + '<div class="nr-box" id="nrBox" hidden>'
    + '<p>当サイトの掲載データは、令和8年5月31日時点の公安委員会の届出資料です。それより後に届出をした探偵業者様は、下の項目と<b>届出証明書の写真</b>をお送りください。内容を確認のうえ、掲載ページを新しく作成します（無料）。</p>'
    + '<label>届出年月日<small>　※必須</small><input type="date" id="nrDate"></label>'
    + '<label>届出先の公安委員会<small>　※必須</small><select id="nrPref"><option value="">選択してください</option>'
    + PREFS.map(function(p){ return '<option>' + p + '</option>'; }).join('') + '</select></label>'
    + '<label>業者名（届出の名前）<small>　※必須</small><input type="text" id="nrName" maxlength="60" placeholder="例：〇〇探偵事務所"></label>'
    + '<label>業者名のふりがな（カタカナ）<input type="text" id="nrKana" maxlength="80" placeholder="例：マルマルタンテイジムショ"></label>'
    + '<label>営業所の所在地<small>　※必須。都道府県から。掲載ページには市区町村までを表示します</small><input type="text" id="nrAddr" maxlength="200" placeholder="例：埼玉県三郷市〇〇1-2-3"></label>'
    + '<label>届出証明書の写真<small>　※必須。確認にだけ使い、公開しません</small><input type="file" id="nrCert" accept="image/*"></label>'
    + '<div class="nr-thumb" id="nrThumb"></div>'
    + '</div>';
  anchor.parentNode.insertBefore(wrap, anchor.nextSibling);

  var btn = document.getElementById('nrToggle'), box = document.getElementById('nrBox');
  var open = false, cert = null;
  function setOpen(v){
    open = v; box.hidden = !v; btn.setAttribute('aria-expanded', v ? 'true' : 'false');
  }
  btn.addEventListener('click', function(){ setOpen(!open); });
  if (/[?&]new=1/.test(location.search)) setOpen(true);

  /* 証明書の写真は長辺1600pxのJPEGに縮めて送る（GASの5MB上限とスマホ写真の大きさ対策） */
  document.getElementById('nrCert').addEventListener('change', function(ev){
    var f = ev.target.files && ev.target.files[0];
    cert = null; document.getElementById('nrThumb').innerHTML = '';
    if (!f) return;
    var img = new Image(), url = URL.createObjectURL(f);
    img.onload = function(){
      var s = Math.min(1, 1600 / Math.max(img.width, img.height));
      var c = document.createElement('canvas'); c.width = Math.round(img.width * s); c.height = Math.round(img.height * s);
      c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
      var d = c.toDataURL('image/jpeg', 0.85);
      cert = { data: d.slice(d.indexOf(',') + 1), name: 'todokede-' + (f.name || 'cert') .replace(/\.[^.]+$/, '') + '.jpg', mime: 'image/jpeg' };
      document.getElementById('nrThumb').innerHTML = '<img src="' + d + '" alt="">';
      URL.revokeObjectURL(url);
    };
    img.onerror = function(){ alert('画像を読み込めませんでした。JPEGかPNGの写真をお選びください。'); };
    img.src = url;
  });

  function v(id){ return (document.getElementById(id).value || '').trim(); }
  window.NR = {
    on: function(){ return open; },
    /* 送信前に呼ぶ。足りなければエラー文を返す */
    apply: function(payload){
      if (!v('nrDate') || !v('nrPref') || !v('nrName') || !v('nrAddr')) return '届出年月日・届出先の公安委員会・業者名・営業所の所在地をご記入ください。';
      if (!cert) return '届出証明書の写真を選んでください。';
      payload.type = 'new';
      payload.name = v('nrName');
      payload.newReg = { date: v('nrDate'), pref: v('nrPref'), name: v('nrName'), kana: v('nrKana'), addr: v('nrAddr') };
      payload.cert = cert;
      payload.message = ['【新規届出（名簿の時点より後）】', '届出年月日：' + v('nrDate'), '届出先：' + v('nrPref') + '公安委員会',
        '業者名：' + v('nrName') + (v('nrKana') ? '（' + v('nrKana') + '）' : ''), '営業所の所在地：' + v('nrAddr')].join('\n')
        + '\n\n' + (payload.message || '');
      return '';
    }
  };
})();

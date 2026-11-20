/* 掲載ページに表示する届出番号を、事業者が選べるようにする（2026-11-20）。
   公安委員会の一覧に番号が2つある事業者（all.json の j がある約2,560社）だけ、届出番号欄の下に選択肢を出す。
   送信時は payload.dispNo に選んだ番号。GAS が確かめて、承認時に display_no.json へ入れる。 */
(function(){
  var sel = document.getElementById('selfId');
  if (!sel) return;
  var anchor = sel.closest('label') || sel;
  var css = document.createElement('style');
  css.textContent = '.dn-box{border:1px solid #cbd9ea;background:#f8fbff;border-radius:6px;padding:12px 14px;margin:2px 0 14px;font-size:.9rem;line-height:1.7;min-width:0}'
    + '.dn-box b{display:block;margin:0 0 4px}.dn-box p{font-size:.82rem;margin:0 0 8px;color:var(--body,#333)}'
    + '.dn-box label{display:flex;align-items:center;gap:8px;margin:4px 0;font-weight:400}.dn-box input{width:auto;margin:0;flex:none}';
  document.head.appendChild(css);
  var box = document.createElement('div');
  box.className = 'dn-box'; box.id = 'dnBox'; box.hidden = true;
  anchor.parentNode.insertBefore(box, anchor.nextSibling);

  var all = null, shownMap = {}, cur = null;
  function draw(){
    var v = (sel.value || '').trim(), e = null;
    cur = null; box.hidden = true; box.innerHTML = '';
    if (!all || !/^\d{8}$/.test(v)) return;
    var js = [];
    for (var k = 0; k < all.length; k++) {
      if (all[k].i === v) { e = all[k]; break; }
      if (all[k].j === v) js.push(all[k]);
    }
    if (!e && js.length === 1) e = js[0];
    if (!e || !e.j || e.j === e.i) return;
    cur = e;
    /* 最初に選んでおく番号：すでに差し替え済みならその番号、なければ入力した番号 */
    var def = shownMap[e.i] || v;
    if (def !== e.i && def !== e.j) def = v;
    box.innerHTML = '<b>掲載ページに表示する届出番号</b><p>公安委員会の一覧に番号が2つあります。届出証明書（標識）に書かれている番号をお選びください。</p>'
      + [e.i, e.j].map(function(n){
          return '<label><input type="radio" name="dnPick" value="' + n + '"' + (n === def ? ' checked' : '') + '>第' + n + '号</label>';
        }).join('');
    box.hidden = false;
  }
  fetch('./all.json', {cache: 'no-cache'}).then(function(r){ return r.ok ? r.json() : []; }).then(function(a){
    all = a;
    return fetch('./tantei-portal-data/display_no.json', {cache: 'no-cache'}).then(function(r){ return r.ok ? r.json() : {}; }).catch(function(){ return {}; });
  }).then(function(m){ shownMap = m || {}; draw(); }).catch(function(){});
  sel.addEventListener('change', draw);
  sel.addEventListener('input', draw);

  window.DN = {
    get: function(){
      if (!cur || box.hidden) return '';
      var c = box.querySelector('input[name=dnPick]:checked');
      return c ? c.value : '';
    }
  };
})();

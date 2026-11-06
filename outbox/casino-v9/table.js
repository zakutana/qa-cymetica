/* Agent Casino v9, a table's own page: their page as it is, laid out as theirs; only the table drawing is ours, the
   rendered table of the lobby with their seats on it. Every figure is read off their own markup. Buttons do nothing. */
(function () {
  var G = window.CASINO_TABLE;
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var esc = function (s) { var d = document.createElement('div'); d.textContent = s == null ? '' : s; return d.innerHTML; };
  var txt = function (el) { return el ? el.textContent.replace(/\s+/g, ' ').trim() : ''; };
  var CROWN = '<span class="at-crown"><svg viewBox="0 0 18 12" aria-hidden="true"><path d="M1 11h16L15.5 3 11.8 6.8 9 1 6.2 6.8 2.5 3z" fill="currentColor"/></svg></span>';
  var lead = $('#atLead');
  var mine = lead ? txt($('.who b', lead)) : '';

  /* ---------------------------------------------------------------- their table, drawn on the rendered one */
  var tbl = $('.at-big .at-tbl');
  if (tbl && G) {
    var PW = 890, PH = PW * G.h / G.w, FW = 420, FH = 180;
    var seats = $$('.at-seat', tbl).map(function (s) {
      var ava = $('.at-ava', s), use = $('use', s), name = ava ? ava.getAttribute('title') : '';
      var colour = ((ava && ava.getAttribute('style')) || '').match(/--c:\s*(#[0-9a-fA-F]{3,8})/);
      return { empty: !name, bot: name, colour: colour ? colour[1] : null, shape: use ? use.getAttribute('href').slice(-1) : 'a',
        rank: txt($('.at-rk', s)), roi: txt($('.at-lab em', s)), house: !!$('.at-h', s), you: !!name && name === mine };
    });
    var pot = { k: txt($('.at-pot .k', tbl)), v: txt($('.at-pot .v', tbl)), s: txt($('.at-pot .s', tbl)) };
    /* their felt carries the prizes under the pot: they stay on ours */
    var spots = $$('.at-spots .sp', tbl).map(function (sp) {
      return '<span class="sp"><i>' + esc(txt($('.k', sp))) + '</i><b>' + esc(txt($('b', sp))) + '</b><em>' + esc(txt($('.e', sp))) + '</em></span>';
    }).join('');

    var f = G.felt, P = function (p) { return [p[0] * PW, p[1] * PH]; };
    var a = P(f.tl), b = P(f.tr), c = P(f.br), d = P(f.bl);
    var dx1 = b[0] - c[0], dx2 = d[0] - c[0], sx = a[0] - b[0] + c[0] - d[0], dy1 = b[1] - c[1], dy2 = d[1] - c[1], sy = a[1] - b[1] + c[1] - d[1];
    var det = dx1 * dy2 - dx2 * dy1, g = (sx * dy2 - dx2 * sy) / det, hh = (dx1 * sy - sx * dy1) / det;
    var m = [b[0] - a[0] + g * b[0], d[0] - a[0] + hh * d[0], a[0], b[1] - a[1] + g * b[1], d[1] - a[1] + hh * d[1], a[1], g, hh, 1];
    var FM = 'matrix3d(' + [m[0] / FW, m[3] / FW, 0, m[6] / FW, m[1] / FH, m[4] / FH, 0, m[7] / FH, 0, 0, 1, 0, m[2], m[5], 0, 1].map(function (n) { return n.toFixed(7); }).join(',') + ')';

    var seatHtml = seats.map(function (s, i) {
      var at = G.seats[i];
      if (!at) return '';
      var pos = 'left:' + (at[0] * PW).toFixed(1) + 'px;top:' + (at[1] * PH).toFixed(1) + 'px';
      if (s.empty) return '<span class="v9-seat empty" style="' + pos + '"><span class="at-ava"></span></span>';
      var name = s.bot.replace(/^House\s+/, '');
      return '<span class="v9-seat' + (s.rank === '1' ? ' lead' : '') + (s.you ? ' you' : '') + '" style="' + pos + '" title="' + esc(s.bot) + '">' +
        '<span class="at-ava" style="--c:' + esc(s.colour || '#00cfff') + '"><svg viewBox="0 0 40 40" aria-hidden="true"><use href="#at-bot-' + esc(s.shape) + '"/></svg></span>' +
        (s.rank === '1' ? CROWN : '') +
        '<span class="lab' + (i === 0 ? ' up' : '') + '">' + (s.you ? '<em>YOU</em>' : '') + '<b>' + esc(name) + (s.house ? '<i>H</i>' : '') + '</b><span class="' + (/^-/.test(s.roi) ? 'neg' : /^\+0\.00/.test(s.roi) ? 'flat' : 'pos') + '">' + (s.rank ? '#' + esc(s.rank) + ' · ' : '') + esc(s.roi) + '</span></span></span>';
    }).join('');
    var holder = document.createElement('div');
    holder.className = 'v9-big';
    holder.innerHTML = '<div class="v9-stage"><div class="v9-obj"><div class="v9-plate">' +
      '<img class="glow" src="art/glow.webp" alt="" draggable="false"><img class="tbl" src="art/table.webp" alt="" draggable="false"><span class="sheen" aria-hidden="true"><i></i></span>' +
      '<div class="pot" style="width:' + FW + 'px;height:' + FH + 'px;transform:' + FM + '"><span class="k">' + esc(pot.k) + '</span><b class="v">' + esc(pot.v) + '</b><span class="s">' + esc(pot.s) + '</span>' + (spots ? '<span class="v9-spots">' + spots + '</span>' : '') + '</div>' +
      seatHtml + '</div></div></div>';
    tbl.replaceWith(holder);
    var fit = function () { $$('.v9-big .v9-stage').forEach(function (s) { s.style.setProperty('--k', Math.min(1.3, s.clientWidth / 640).toFixed(4)); }); };
    addEventListener('resize', fit); fit();
  }

  /* ---------------------------------------------------------------- what their scripts did: the side tabs, the clocks */
  document.addEventListener('click', function (e) {
    var tab = e.target.closest('#atTabs [role="tab"]');
    if (tab) {
      $$('#atTabs [role="tab"]').forEach(function (t) { var on = t === tab; t.classList.toggle('on', on); t.setAttribute('aria-selected', on ? 'true' : 'false'); });
      $$('#atTabs .at-pane').forEach(function (p) { p.hidden = p.id !== tab.getAttribute('aria-controls'); });
      return;
    }
    if (e.target.closest('button')) e.preventDefault();
  });
  var pad = function (n) { return (n < 10 ? '0' : '') + n; };
  function tick() {
    $$('.at-cdn[data-end]').forEach(function (el) {
      var left = Math.max(0, Date.parse(el.getAttribute('data-end')) - Date.now());
      var parts = { d: Math.floor(left / 864e5), h: Math.floor(left / 36e5) % 24, m: Math.floor(left / 6e4) % 60, s: Math.floor(left / 1e3) % 60 };
      ['d', 'h', 'm', 's'].forEach(function (u) {
        var e = $('[data-u="' + u + '"]', el);
        if (e) { e.innerHTML = pad(parts[u]) + '<i>' + u.toUpperCase() + '</i>'; if (u === 'd') e.hidden = !parts.d; }
      });
    });
    $$('.at-pb[data-start]').forEach(function (el) {
      var s = Date.parse(el.getAttribute('data-start')), e = Date.parse(el.getAttribute('data-end')), i = $('i', el);
      if (i && e > s) i.style.width = Math.min(100, Math.max(0, (Date.now() - s) / (e - s) * 100)).toFixed(1) + '%';
    });
  }
  tick(); setInterval(tick, 1000);
})();

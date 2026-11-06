/* Agent Casino v9, a table's own page. Their page; the owner's panel folded to one row and one line; their table
   drawn on the rendered table of the lobby. Every figure is read off their own markup. Buttons do nothing. */
(function () {
  var G = window.CASINO_TABLE;
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var esc = function (s) { var d = document.createElement('div'); d.textContent = s == null ? '' : s; return d.innerHTML; };
  var txt = function (el) { return el ? el.textContent.replace(/\s+/g, ' ').trim() : ''; };
  var CROWN = '<span class="at-crown"><svg viewBox="0 0 18 12" aria-hidden="true"><path d="M1 11h16L15.5 3 11.8 6.8 9 1 6.2 6.8 2.5 3z" fill="currentColor"/></svg></span>';

  /* ---------------------------------------------------------------- the owner's panel: one row, one line, details on demand */
  var lead = $('#atLead');
  var mine = lead ? txt($('.who b', lead)) : '';
  if (lead) {
    var head = $('.at-lead-h', lead), left = $('.left', lead);
    if (head && left) head.appendChild(left);
    var chips = $$('p', lead).map(function (p) {
      if (p.classList.contains('need')) return '<span class="chip need">' + esc(txt(p)) + '</span>';
      var body = txt(p).replace(/^[^:]*:\s*/, '');
      var first = body.split(/\s+because\s+|[,;.:]\s/)[0];
      return '<span class="chip">' + esc(first) + '</span>';
    }).join('');
    lead.insertAdjacentHTML('beforeend', '<div class="v9-chips">' + chips + '<button type="button" class="v9-more" data-details aria-expanded="false">Details</button></div>');
    lead.classList.add('v9-folded');
    lead.addEventListener('click', function (e) {
      var b = e.target.closest('[data-details]');
      if (!b) return;
      var open = lead.classList.toggle('v9-open');
      b.textContent = open ? 'Less' : 'Details';
      b.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }

  /* ---------------------------------------------------------------- their table, on the rendered one */
  var big = $('.at-big');
  if (big && G) {
    var PW = 890, PH = PW * G.h / G.w, FW = 420, FH = 180;
    var seats = $$('.at-seat', big).map(function (s) {
      var ava = $('.at-ava', s), use = $('use', s), name = ava ? ava.getAttribute('title') : '';
      var colour = ((ava && ava.getAttribute('style')) || '').match(/--c:\s*(#[0-9a-fA-F]{3,8})/);
      return { empty: !name, bot: name, colour: colour ? colour[1] : null, shape: use ? use.getAttribute('href').slice(-1) : 'a',
        rank: txt($('.at-rk', s)), roi: txt($('.at-lab em', s)), house: !!$('.at-h', s), you: name === mine };
    });
    var pot = { k: txt($('.at-pot .k', big)), v: txt($('.at-pot .v', big)), s: txt($('.at-pot .s', big)) };
    var prizes = $$('.at-spots .sp', big).map(function (sp) { return { k: txt($('.k', sp)), b: txt($('b', sp)), e: txt($('.e', sp)) }; });

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
    big.classList.add('v9-big');
    big.innerHTML = '<div class="v9-stage"><div class="v9-obj"><div class="v9-plate">' +
      '<img class="glow" src="art/glow.webp" alt="" draggable="false"><img class="tbl" src="art/table.webp" alt="" draggable="false"><span class="sheen" aria-hidden="true"><i></i></span>' +
      '<div class="pot" style="width:' + FW + 'px;height:' + FH + 'px;transform:' + FM + '"><span class="k">' + esc(pot.k) + '</span><b class="v">' + esc(pot.v) + '</b><span class="s">' + esc(pot.s) + '</span></div>' +
      seatHtml + '</div></div></div>' +
      '<div class="pzs v9-bigpz">' + prizes.map(function (p, i) {
        return '<div class="pz' + (i === 0 ? ' w' : '') + '"><span class="k">' + esc(p.k) + '</span><b>' + esc(p.b) + '</b><span class="e">' + esc(p.e) + '</span></div>';
      }).join('') + '</div>';
    var fit = function () { $$('.v9-big .v9-stage').forEach(function (s) { s.style.setProperty('--k', Math.min(1.3, s.clientWidth / 640).toFixed(4)); }); };
    addEventListener('resize', fit); fit();
  }

  /* ---------------------------------------------------------------- their clocks, stripped with their scripts */
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
  document.addEventListener('click', function (e) { var b = e.target.closest('main button, #atRoot button'); if (b && !b.closest('[data-details]')) e.preventDefault(); });
})();

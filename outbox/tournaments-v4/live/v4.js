/* v4 layer on top of their Agent Tournaments pages: the Paper | Live view, the stopwatches, the wallet panel, the
   owner's tabs and the NEXUS coach. A preview: nothing here writes anywhere; every request that is not a read is refused. */
(function () {
  'use strict';

  // 1. reads only: the mirror refuses writes too, this keeps the page from even trying
  var realFetch = window.fetch;
  window.fetch = function (url, opts) {
    var m = String((opts && opts.method) || (url && url.method) || 'GET').toUpperCase();
    if (m !== 'GET' && m !== 'HEAD') {
      console.info('[v4 preview] not sent:', m, url);
      return Promise.resolve(new Response('{"detail":"preview only"}', { status: 405, headers: { 'Content-Type': 'application/json' } }));
    }
    return realFetch.apply(this, arguments);
  };
  var xhrOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (method) {
    if (String(method).toUpperCase() !== 'GET' && String(method).toUpperCase() !== 'HEAD') { arguments[0] = 'GET'; arguments[1] = 'about:blank'; }
    return xhrOpen.apply(this, arguments);
  };
  function each(sel, fn, root) { Array.prototype.forEach.call((root || document).querySelectorAll(sel), fn); }

  // 2. Paper | Live: the switch at the top of the lobby and their header pill are one setting
  var KEY = 'v4mode';
  function isPaper() { try { return localStorage.getItem(KEY) !== 'live'; } catch (e) { return true; } }
  function applyMode() {
    var paper = isPaper();
    document.documentElement.classList.toggle('v4-live', !paper);
    var pill = document.getElementById('headerModeIndicator');
    if (pill) {
      pill.classList.toggle('paper', paper); pill.classList.toggle('live', !paper);
      var l = pill.querySelector('.mode-label'); if (l) l.textContent = paper ? 'PAPER' : 'LIVE';
    }
    each('[data-v4-mode]', function (b) { b.classList.toggle('on', (b.getAttribute('data-v4-mode') === 'paper') === paper); });
  }
  function setMode(live) {
    try { localStorage.setItem(KEY, live ? 'live' : 'paper'); } catch (x) { /* private window: the switch still works on this page */ }
    applyMode();
    window.dispatchEvent(new CustomEvent('tradingModeChanged', { detail: { isPaper: !live } }));
  }
  document.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('#headerModeIndicator, [data-v4-mode]');
    if (!t) return;
    e.preventDefault(); e.stopImmediatePropagation();
    setMode(t.id === 'headerModeIndicator' ? isPaper() : t.getAttribute('data-v4-mode') === 'live');
  }, true);
  applyMode();
  document.addEventListener('DOMContentLoaded', applyMode);

  // 3. the small clocks: a running table's ring fills as its time goes
  function clocks() {
    var now = Date.now();
    each('.v4-dur[data-v4-end]', function (c) {
      var a = Date.parse(c.getAttribute('data-v4-start')), b = Date.parse(c.getAttribute('data-v4-end'));
      if (isNaN(a) || isNaN(b) || b <= a) return;
      var p = Math.max(0, Math.min(1, (now - a) / (b - a))), pg = c.querySelector('.pg'), tip = c.querySelector('.tip');
      if (pg) pg.setAttribute('stroke-dasharray', (p * 100).toFixed(2) + ' 100');
      if (tip) { var t = 2 * Math.PI * Math.min(p, 0.999); tip.setAttribute('cx', (32 + 17 * Math.sin(t)).toFixed(2)); tip.setAttribute('cy', (40 - 17 * Math.cos(t)).toFixed(2)); }
    });
  }
  clocks(); setInterval(clocks, 1000);

  // 4. the wallet panel, opened from a Live card
  function wallet(open) { var m = document.getElementById('atWalletV4'); if (m) m.hidden = !open; }
  document.addEventListener('click', function (e) {
    var card = e.target.closest && e.target.closest('[data-v4-live]');
    if (card) { e.preventDefault(); wallet(true); return; }
    if (e.target.closest && e.target.closest('[data-v4-close]')) { e.preventDefault(); wallet(false); }
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') wallet(false); });

  // 5. the owner's tabs (Coach, Settings, Trade log, Changelog)
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('.at-tabbar button[data-tab]');
    if (!b) return;
    var bar = b.parentNode, root = bar.parentNode;
    Array.prototype.forEach.call(bar.children, function (x) { var on = x === b; x.classList.toggle('on', on); x.setAttribute('aria-selected', on); });
    each('[data-pane]', function (p) { p.hidden = p.getAttribute('data-pane') !== b.getAttribute('data-tab'); }, root);
  });

  // 6. the coach: on or off, on a paid plan (locked on the free one)
  function coach(card) {
    var sw = card.querySelector('[data-v4-sw]'), free = card.getAttribute('data-v4-as') === 'free';
    sw.disabled = free; if (free) sw.checked = false;
    card.querySelector('[data-v4-off]').hidden = !free;
    card.classList.toggle('v4-off', !sw.checked);
    card.querySelector('[data-v4-plan]').textContent = free ? 'PRO · LOCKED' : 'PRO';
  }
  // 7. the risk: every owner sets it, coach or not
  var WORDS = ['', 'Calm', 'Calm', 'Steady', 'Steady', 'Balanced', 'Balanced', 'Bold', 'Bold', 'All in', 'All in'];
  var B = 'var(--at-blue)', C = 'var(--at-cyan)', G = 'var(--at-green)', R = 'var(--at-red)';
  var COLOURS = ['', B, B, C, C, C, G, G, R, R, R];      // the gauge's segments (art.RISK_COLOURS)
  function risk(card) {
    var v = +card.querySelector('[data-v4-risk]').value, num = card.querySelector('[data-v4-risk-v]');
    num.textContent = v;
    num.style.color = COLOURS[v];
    card.querySelector('[data-v4-risk-w]').textContent = WORDS[v];
    each('.v4-seg', function (s) { s.classList.toggle('on', +s.getAttribute('data-i') <= v); }, card);
    var n = card.querySelector('.v4-needle'); if (n) n.style.transform = 'rotate(' + ((v - 0.5) * 18 - 90) + 'deg)';
    card.querySelector('.v4-risk').setAttribute('data-level', v);
  }
  function onChange(e) {
    var c = e.target.closest && e.target.closest('[data-v4="coach"]'); if (c) coach(c);
    var r = e.target.closest && e.target.closest('[data-v4="risk"]'); if (r) risk(r);
  }
  document.addEventListener('input', onChange);
  document.addEventListener('change', onChange);
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('[data-v4-as]');
    if (!b || b.matches('[data-v4="coach"]')) return;
    var card = b.closest('[data-v4="coach"]');
    card.setAttribute('data-v4-as', b.getAttribute('data-v4-as'));
    if (b.getAttribute('data-v4-as') === 'pro') card.querySelector('[data-v4-sw]').checked = true;
    each('button[data-v4-as]', function (x) { x.classList.toggle('on', x === b); }, card);
    coach(card);
  });
})();

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

  // 2. Paper | Live: a VIEW filter of this page only. The header pill is the whole platform's trading mode (and is
  //    throttled); this switch does not touch it, never changes the account, and has no cooldown.
  var KEY = 'v4mode';
  function isPaper() { try { return localStorage.getItem(KEY) !== 'live'; } catch (e) { return true; } }
  function applyMode() {
    var paper = isPaper();
    document.documentElement.classList.toggle('v4-live', !paper);
    each('[data-v4-mode]', function (b) { b.classList.toggle('on', (b.getAttribute('data-v4-mode') === 'paper') === paper); });
  }
  function setMode(live) {
    try { localStorage.setItem(KEY, live ? 'live' : 'paper'); } catch (x) { /* private window: the switch still works on this page */ }
    applyMode();
  }
  document.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('[data-v4-mode]');
    if (!t) return;
    e.preventDefault(); e.stopImmediatePropagation();
    setMode(t.getAttribute('data-v4-mode') === 'live');
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

  // 6. the coach: on or off; its line says what it is doing (the paid-plan lock is the spec's, not this preview's)
  function coach(panel) {
    var c = panel.querySelector('[data-v4="coach"]'), r = panel.querySelector('[data-v4-risk]');
    if (!c) return;
    var on = c.querySelector('[data-v4-sw]').checked;
    c.classList.toggle('v4-off', !on);
    c.querySelector('[data-v4-st]').textContent = on ? 'Tuning your bot inside risk ' + (r ? r.value : '') : 'Off: your bot runs as you set it';
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
    // the level SETS the bot (owner.RISK_SET): the three numbers here, and the Settings tab's own sliders
    var set = JSON.parse(card.getAttribute('data-v4-map'))[v];
    each('[data-v4-set]', function (b) { b.textContent = set[b.getAttribute('data-v4-set')] + '%'; }, card);
    [['Trade size %', set.size], ['Stop loss %', set.stop], ['Take profit %', set.take]].forEach(function (p) {
      var r = document.querySelector('input[aria-label="' + p[0] + '"]'); if (!r) return;
      r.value = p[1];
      var b = r.closest('.at-rng') && r.closest('.at-rng').querySelector('.rh b'); if (b) b.textContent = p[1] + '%';
    });
    var ch = document.querySelector('.at-this p');
    if (ch) ch.textContent = 'Set by Risk ' + v + ': size ' + set.size + '%, stop loss ' + set.stop + '%, take profit ' + set.take + '%. In force now.';
  }
  function onChange(e) {
    var r = e.target.closest && e.target.closest('[data-v4="risk"]'); if (r) risk(r);
    var p = e.target.closest && e.target.closest('.v4-coachpanel'); if (p) coach(p);
  }
  document.addEventListener('input', onChange);
  document.addEventListener('change', onChange);
})();

/* v4 layer on top of their Agent Tournaments pages: the Paper | Live view, the wallet panel, the owner's tabs and the
   Tune switch. A preview: nothing here writes anywhere; every request that is not a read is refused. */
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

  // 2. their header's PAPER | LIVE pill drives the lobby (they fire tradingModeChanged themselves)
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
  }
  document.addEventListener('click', function (e) {
    var pill = e.target.closest && e.target.closest('#headerModeIndicator');
    if (!pill) return;
    e.preventDefault(); e.stopImmediatePropagation();
    try { localStorage.setItem(KEY, isPaper() ? 'live' : 'paper'); } catch (x) { /* private window: the switch still works for this page */ }
    applyMode();
    window.dispatchEvent(new CustomEvent('tradingModeChanged', { detail: { isPaper: isPaper() } }));
  }, true);
  applyMode();
  document.addEventListener('DOMContentLoaded', applyMode);

  // 3. the wallet panel, opened from a Live card
  function wallet(open) { var m = document.getElementById('atWalletV4'); if (m) m.hidden = !open; }
  document.addEventListener('click', function (e) {
    var card = e.target.closest && e.target.closest('[data-v4-live]');
    if (card) { e.preventDefault(); wallet(true); return; }
    if (e.target.closest && e.target.closest('[data-v4-close]')) { e.preventDefault(); wallet(false); }
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') wallet(false); });

  // 4. the owner's tabs (Settings, Trade log, Changelog)
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('.at-tabbar button[data-tab]');
    if (!b) return;
    var bar = b.parentNode, root = bar.parentNode;
    Array.prototype.forEach.call(bar.children, function (x) { var on = x === b; x.classList.toggle('on', on); x.setAttribute('aria-selected', on); });
    Array.prototype.forEach.call(root.querySelectorAll('[data-pane]'), function (p) { p.hidden = p.getAttribute('data-pane') !== b.getAttribute('data-tab'); });
  });

  // 5. the Tune switch: on a paid plan it turns Tune on and off; on the free plan it is locked
  function tune(card) {
    var sw = card.querySelector('[data-v4-sw]'), on = card.querySelector('[data-v4-on]'), off = card.querySelector('[data-v4-off]'),
      plan = card.querySelector('[data-v4-plan]'), free = card.getAttribute('data-v4-as') === 'free';
    sw.disabled = free; if (free) sw.checked = false;
    on.hidden = free; off.hidden = !free;
    on.classList.toggle('v4-dim', !sw.checked && !free);
    plan.textContent = free ? 'PRO · LOCKED' : 'PRO';
  }
  document.addEventListener('change', function (e) {
    if (e.target.matches && e.target.matches('[data-v4-sw]')) tune(e.target.closest('[data-v4="tune"]'));
  });
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('[data-v4-as]');
    if (!b) return;
    var card = b.closest('[data-v4="tune"]');
    card.setAttribute('data-v4-as', b.getAttribute('data-v4-as'));
    if (b.getAttribute('data-v4-as') === 'pro') card.querySelector('[data-v4-sw]').checked = true;
    Array.prototype.forEach.call(card.querySelectorAll('[data-v4-as]'), function (x) { x.classList.toggle('on', x === b); });
    tune(card);
  });
})();

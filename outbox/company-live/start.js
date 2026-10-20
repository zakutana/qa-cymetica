/* The /company entry: the seven stations (stations.js) one after another, turning in the page's space, drawn by the
 * office's engine (CO.U3.preview); the flat picture (CO.skinSVG) until the 3D one is ready. Which station it is shows
 * under it. */
(function () {
  'use strict';
  var CO = window.CO;
  var el = document.getElementById('lp-space'), cap = document.getElementById('lp-cap'), p = CO.profile();
  var keys = CO.SKINS.map(function (s) { return s.key; }), i = Math.max(0, keys.indexOf(p.skin)), timer = 0;
  var EVERY = 6500;
  function o() { return { skin: keys[i], accent: p.accent, floors: 4, seed: 7, you: false, public: true }; }
  function caption() {
    cap.innerHTML = '<b>' + CO.skinName(keys[i]) + '</b>' + keys.map(function (k, j) { return '<i' + (j === i ? ' class="on"' : '') + '></i>'; }).join('');
  }
  el.innerHTML = CO.skinSVG({ skin: keys[i], accent: p.accent, floors: 4, seed: 7 });
  caption();
  function show() { if (CO.U3 && CO.U3.ok && CO.U3.preview) CO.U3.preview(el, o()); caption(); }
  function next() { i = (i + 1) % keys.length; show(); }
  function go() {
    show();
    // not while the tab is hidden: a station built for nobody
    timer = setInterval(function () { if (!document.hidden) next(); }, EVERY);
  }
  // the new stations, or the engine as it is if they never come (8 s)
  var done = false, start = function () { if (done) return; done = true; go(); };
  if (CO.U3 && CO.U3.skins) start();
  else { window.addEventListener('co3d-skins', start, { once: true }); setTimeout(function () { if (CO.U3 && CO.U3.ok) start(); }, 8000); }
})();

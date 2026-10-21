/* The /company mockup: the Universe. Since 2026-10-21 it is marketing, not a map of companies: land round Cymetica
 * bought a slot at a time with ET10 and built on through Build it Better, and our two products as ads on it (CO.ADS).
 * Also here: the stations a company can pick, their colours and icons, and the owner's own profile. */
(function () {
  'use strict';
  var CO = window.CO = window.CO || {};

  // a station's shape and its colour: the colour is one of the site's four, the variety is in the shape. The keys
  // are the buildings' old ones, so a company saved before the Universe went to space keeps its pick.
  // The seven as stations.js draws them since 2026-10-20 (it sets these names too when it installs them; here, so the
  // flat pictures where 3D cannot start carry the same ones).
  CO.SKINS = [
    { key: 'tower', name: 'Dreadnought' }, { key: 'dome', name: 'Shipyard' }, { key: 'pyramid', name: 'Pyramid Carrier' },
    { key: 'orbital', name: 'Ring Habitat' }, { key: 'rocket', name: 'Lancer' }, { key: 'vault', name: 'Citadel' }, { key: 'stack', name: 'Monolith' }
  ];
  CO.ACCENTS = [
    { key: 'green', hex: '#00ff88' }, { key: 'cyan', hex: '#00cfff' }, { key: 'blue', hex: '#3b82f6' }, { key: 'red', hex: '#ff4444' },
    // four more for a station ("a pridej vice barev", 2026-10-20): the Universe is a game scene, outside the site's
    // palette rule (SPEC-NOTES, 2026-10-18); no orange, which in the office means a room waiting on its owner
    { key: 'purple', hex: '#a855f7' }, { key: 'pink', hex: '#ff4fd8' }, { key: 'gold', hex: '#ffc83d' }, { key: 'white', hex: '#e6eef8' }
  ];
  CO.accentHex = function (k) {
    for (var i = 0; i < CO.ACCENTS.length; i++) if (CO.ACCENTS[i].key === k) return CO.ACCENTS[i].hex;
    return CO.ACCENTS[0].hex;
  };
  // Each station as a line icon, drawn as the departments' are (data.js DEPT_ICON) -- the company's logo, in its
  // colour ("v tom stylu jak maji ruzne departmenty ikonky ... barva cele ikonky podle toho jakou si zvolil barvu firmy")
  CO.STATION_ICON = {
    tower: '<path d="M1.8 14.2h16.4l-2.3 2.6H4.4Z M5 14.2v-3h9.4v3 M7 11.2V8.4h5.4v2.8 M8.6 8.4V5.8h2.2v2.6 M9.7 5.8V2.6"/><circle cx="12.4" cy="12.7" r=".5" fill="currentColor"/><circle cx="10.4" cy="12.7" r=".5" fill="currentColor"/>',
    dome: '<path d="M2.8 17.2V5.2h3.4v12 M13.8 17.2V5.2h3.4v12 M6.2 7.4h7.6 M6.2 9.8h7.6 M2.8 17.2h14.4 M4.5 5.2V2.8 M15.5 5.2V2.8 M7.6 17.2l2.4-4.4 2.4 4.4"/>',
    pyramid: '<ellipse cx="10" cy="14.4" rx="8" ry="2.7"/><path d="M5.4 13.4l1.4-3.6h6.4l1.4 3.6 M7.6 9.8l.9-3.2h3l.9 3.2 M9 6.6l1-3.6 1 3.6"/>',
    orbital: '<ellipse cx="10" cy="11.6" rx="8" ry="3.7"/><path d="M4.4 9.2l11.2 4.8 M15.6 9.2 4.4 14 M10 6.6V2.8"/><rect x="8.3" y="6.6" width="3.4" height="7.2" rx="1.7"/>',
    rocket: '<path d="M1.8 11.2l4.4-2.6h9.4l2.6 1.1v3l-2.6 1.1H6.2Z M7.6 8.6v5.2 M9.4 8.6v5.2 M13 8.6V5.8h2.2v2.8 M18.2 10.4v1.6"/>',
    vault: '<ellipse cx="10" cy="14.8" rx="8" ry="2.5"/><path d="M5.2 14.4v-3.6a4.8 4.8 0 0 1 9.6 0v3.6 M10 6V2.2 M5.4 11.8h9.2"/>',
    stack: '<rect x="7.6" y="3" width="4.8" height="11.2" rx=".6"/><path d="M3.8 15.6l2.1-1.4h8.2l2.1 1.4-2.1 1.4H5.9Z M9.1 5.6h1.8 M9.1 8h1.8 M9.1 10.4h1.8"/><rect x="3.2" y="5" width="1.8" height="1.8"/><rect x="15" y="8" width="1.8" height="1.8"/>'
  };
  CO.stationIcon = function (skin, accent) {
    return '<span class="dic logo" style="--ic:' + CO.accentHex(accent) + '"><svg viewBox="0 0 20 20" aria-hidden="true">' +
      (CO.STATION_ICON[skin] || CO.STATION_ICON.dome) + '</svg></span>';
  };
  CO.skinName = function (k) {
    for (var i = 0; i < CO.SKINS.length; i++) if (CO.SKINS[i].key === k) return CO.SKINS[i].name;
    return k;
  };

  // the owner's own company on the map: its name, building, colour and whether others may look inside.
  // Private by default, as Investable is on the live page. Only the owner's own pages write it, never a visit.
  var KEY = 'co.me.v1';
  var DEF = { name: 'My Company', mission: '', skin: 'tower', accent: 'green', public: false };
  CO.profile = function () {
    var p = {}, k;
    try { p = JSON.parse(localStorage.getItem(KEY) || '{}') || {}; } catch (e) { p = {}; }
    for (k in DEF) if (p[k] == null || p[k] === '') p[k] = DEF[k];
    return p;
  };
  CO.saveProfile = function (o) {
    if (CO.RO) return CO.profile();
    var p = CO.profile(), k;
    for (k in o) p[k] = o[k];
    try { localStorage.setItem(KEY, JSON.stringify(p)); } catch (e) { /* the page still works, it just forgets */ }
    return p;
  };

  // No companies stand on the map any more (the operator, 2026-10-21: "smaz tam vsechny firmy"): the Universe is land
  // round Cymetica, sold a slot at a time, and two ads stand on it. A visit (?visit=<id>) finds no company.
  CO.UNIVERSE = [];

  // The ads: our two top products, drawn bigger than any station so they are seen ("tyto reklamni budovy musi byt
  // vetsi nez normalni firmy"), each a click away from its live page. orbit: which of the galaxy's orbits (0 is the
  // innermost); at: its angle from the front of the first look, so both stand in that view.
  CO.ADS = [
    { key: 'gem', name: 'Gem Screener', url: 'https://cymetica.com/gem-screener/app?view=apps', accent: 'cyan', orbit: 1, at: -0.62 },
    { key: 'casino', name: 'Agent Casino', url: 'https://cymetica.com/agent-tournaments', accent: 'green', orbit: 1, at: 0.62 }
  ];
  // The land: a slot is bought with ET10, then built on through Build it Better. The price is a PLACEHOLDER (the
  // operator named the currency, not the amount); one number to change. What this browser bought, by slot id.
  CO.LAND_PRICE = 1000;
  CO.BUILD_URL = 'https://cymetica.com/build-it-better';
  var LKEY = 'co.land.v1';
  CO.land = function () {
    try { var a = JSON.parse(localStorage.getItem(LKEY) || '[]'); return Array.isArray(a) ? a : []; } catch (e) { return []; }
  };
  CO.buyLand = function (id) {
    var a = CO.land();
    if (CO.RO || a.indexOf(id) >= 0) return a;
    a.push(id);
    try { localStorage.setItem(LKEY, JSON.stringify(a)); } catch (e) { /* the page still works, it just forgets */ }
    return a;
  };
  CO.uvCompany = function (id) {
    for (var i = 0; i < CO.UNIVERSE.length; i++) if (CO.UNIVERSE[i].id === id) return CO.UNIVERSE[i];
    return null;
  };
  CO.uvEt10 = function (c) { return (c.bugs || 0) * 1000; };
})();

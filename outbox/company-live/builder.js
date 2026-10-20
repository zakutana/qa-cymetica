/* The /company builder: a name, a look, and how it starts -- New (the three rooms every company has) or Pre-build
 * (those three and four departments), the pre-built office drawn by the office's own 3D engine (CO.U3.office) with
 * a room-by-room tour. Nothing here draws a room itself: the station is CO.U3.preview's, the office Office3D's, the
 * departments are added through the simulation's own door (CO.act.addDept). Finishing saves the profile
 * (CO.saveProfile) and opens the office. */
(function () {
  'use strict';
  var CO = window.CO;
  function $(id) { return document.getElementById(id); }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }

  // The rooms every company has, and the departments a pre-built one starts with. CO.PREBUILD, once data.js defines
  // it, is the one list both this page and the office's boot read; until then this one stands in for it.
  var FIXED = [
    { k: 'hub', n: 'Command', t: 'Everything runs from here. You only talk to NEXUS.' },
    { k: 'vault', n: 'Vault', t: 'What the company earns: USDC, and ET10 rewards.' },
    { k: 'audit', n: 'Operations', t: 'Keeps the company running and every process optimised.' }
  ];
  var PRE = CO.PREBUILD || [
    { key: 'testing', name: 'Cymetica QA' }, { key: 'development', name: 'Development' },
    { key: 'testing_lab', name: 'Quant Lab' }, { key: 'trading_desk', name: 'Trading desk' }
  ];
  var LINE = {
    testing: 'Tests your products and logs the bugs. Every bug earns you ET10.',
    development: 'Builds what the company needs: products, apps.',
    testing_lab: 'Researches new ways to earn on Cymetica.',
    trading_desk: 'Tests those strategies.'
  };
  var TOUR = FIXED.concat(PRE.map(function (d) { return { dk: d.key, n: d.name, t: LINE[d.key] || '' }; }));

  // what is being made: the modal's own defaults (app.js createCompanyModal), and the pre-built start
  var o = { name: '', mission: '', skin: 'tower', accent: 'green', public: false, start: 'pre' };
  var step = 1, ti = 0, office = null, making = false;

  /* ---------------- the company the office shows: nothing runs while it is only being looked at ---------------- */
  CO.sim.running = false;
  CO.S = CO.seedEmpty(Date.now());
  function tplOf(k) { return CO.TEMPLATES.filter(function (t) { return t.key === k; })[0] || {}; }
  function oursCharter(name) { var d = (CO.OURS.departments || []).filter(function (x) { return x.name === name; })[0]; return d && d.charter; }
  function setStart(k) {
    o.start = k;
    var S = CO.S;
    S.departments = []; S.tasks = []; S.plan = []; S.feed = []; S.next_dept = 1; S.next_id = 1;
    S.company.name = o.name || 'My Company';
    if (k === 'pre') PRE.forEach(function (d) {
      var tpl = tplOf(d.key);
      CO.act.addDept({ key: d.key, name: d.name, experts: (d.experts || tpl.experts || ['researcher']).slice(),
        charter: d.charter || oursCharter(d.name) || tpl.charter || '', quiet: true });
    });
    // layout(), not update(): an office of no departments has the shape key '', and update() rebuilds only from a
    // truthy one, so New -> Pre-build kept the empty office (index.html rebuilds on its dept:new the same way)
    if (office) { office.layout(); darkLamps(); }
  }
  // Office3D keeps its lamps across rebuilds (lampsBack) but lets go of the ones a smaller office has no room for, and
  // three.js keys every lit shader by the scene's lights: New after Pre-build compiled every lit material again, 1.3 s
  // and 1.0 s frozen (measured 2026-10-20). Those lamps stay in the scene, dark, so the set of lights never changes.
  function darkLamps() {
    if (!office.lampPool || !office.world) return;
    office.lampPool.forEach(function (l) { if (!l.parent) { l.intensity = 0; office.world.add(l); } });
  }
  setStart(o.start);
  function keyOf(r) {
    if (r.k) return r.k;
    var d = CO.S.departments.filter(function (x) { return x.key === r.dk; })[0];
    return d ? 'd' + d.id : null;
  }
  function tipFor(kind, key) {
    if (kind !== 'room') return '';
    for (var i = 0; i < TOUR.length; i++) if (keyOf(TOUR[i]) === key) return '<b>' + esc(TOUR[i].n) + '</b><br>' + esc(TOUR[i].t);
    return '';
  }

  /* ---------------- the engine and the font the office's screens are drawn in ---------------- */
  // the engine with the new stations in it (stations.js, co3d-skins), or an engine that could not start; 8 s at most
  function whenEngine(cb) {
    var done = false, fin = function () { if (done) return; done = true; window.removeEventListener('co3d', on); window.removeEventListener('co3d-skins', on); clearTimeout(late); cb(!!(CO.U3 && CO.U3.ok)); };
    var on = function () { if (CO.U3 && (CO.U3.skins || CO.U3.failed)) fin(); };
    var late = setTimeout(fin, 8000);
    window.addEventListener('co3d', on); window.addEventListener('co3d-skins', on);
    on();
  }
  function monoWait(cb) {
    var done = false, fin = function () { if (!done) { done = true; cb(); } };
    try { Promise.all(['400', '500', '600', '700'].map(function (w) { return document.fonts.load(w + ' 16px "JetBrains Mono"'); })).then(fin, fin); } catch (e) { fin(); }
    setTimeout(fin, 1500);
  }
  // the office, made once the stage is on screen; flat (office.js) where 3D cannot start
  function makeOffice(cb) {
    if (office) return cb();
    if (making) return;
    making = true;
    veil(true);
    whenEngine(function (ok) {
      monoWait(function () {
        var st = $('stage');
        if (ok && CO.U3.office) {
          st.classList.add('is3d');
          office = CO.U3.office($('office3d'), st, tipFor);
          office.onFail = function () { st.classList.remove('is3d'); office = flat(); office.layout(); then(); };
        } else office = flat();
        office.layout();
        then();
        function then() { requestAnimationFrame(function () { office.resize(); office.fit(false); cb(); drawn(function () { veil(false); }); }); }
      });
    });
  }
  // the veil over the stage while the office is built (builder.css says why)
  function veil(on) { $('veil').classList.toggle('on', on); }
  function drawn(cb) {
    var f0 = office && office.frames || 0, t0 = performance.now();
    (function w() { if (!office || office.frames === undefined || office.frames > f0 + 1 || performance.now() - t0 > 8000) return cb(); requestAnimationFrame(w); })();
  }
  // New <-> Pre-build: the veil first, its fade finished, so the stage is covered before the build holds the page
  function restart(k) {
    if (!office) return setStart(k);
    veil(true);
    setTimeout(function () { setStart(k); office.fit(false); drawn(function () { veil(false); }); }, 190);
  }
  function flat() {
    var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); svg.setAttribute('class', 'office'); $('stage').appendChild(svg);
    return new CO.Office(svg, $('stage'), tipFor);
  }
  CO.on('office:click', function (key) {
    if (o.start !== 'pre' || (step !== 3 && step !== 'tour')) return;
    for (var i = 0; i < TOUR.length; i++) if (keyOf(TOUR[i]) === key) { show('tour'); return tourAt(i); }
  });

  /* ---------------- the station, in the stage while it is being named and dressed ---------------- */
  function station() {
    var el = $('b-prev');
    if (!el.__pv) el.innerHTML = CO.skinSVG({ skin: o.skin, accent: o.accent, floors: 3, seed: 7, banner: o.name || 'Your company', you: true, priv: !o.public });
    if (CO.U3 && CO.U3.ok && CO.U3.preview) CO.U3.preview(el, { skin: o.skin, accent: o.accent, floors: 3, seed: 7, name: o.name || 'Your company', you: true, public: o.public });
  }
  function pub() {
    return '<span class="sw"></span><div><b>' + (o.public ? 'Public' : 'Private') + '</b><span>' +
      (o.public ? 'Anyone can look inside, read only.' : 'Others see its name, its station and its mission.') + '</span></div>';
  }
  function skins() {
    $('f-skins').innerHTML = CO.SKINS.map(function (s) {
      return '<button type="button" class="skin' + (s.key === o.skin ? ' on' : '') + '" data-k="' + s.key + '">' +
        CO.skinSVG({ skin: s.key, accent: o.accent, floors: 3, seed: 11 }) + '<b>' + esc(s.name) + '</b></button>';
    }).join('');
    if (!(CO.U3 && CO.U3.ok && CO.U3.thumbs)) return;
    var acc = o.accent;
    CO.U3.thumbs(CO.accentHex(acc), function (urls) {
      if (acc !== o.accent) return;
      Array.prototype.forEach.call($('f-skins').querySelectorAll('.skin[data-k]'), function (b) {
        var u = urls[b.getAttribute('data-k')]; if (!u || b.querySelector('img.th3')) return;
        var img = document.createElement('img'); img.className = 'th3'; img.alt = ''; img.src = u; b.insertBefore(img, b.firstChild); b.classList.add('has3d');
      });
    });
  }
  function accents() {
    $('f-acc').innerHTML = CO.ACCENTS.map(function (a) {
      return '<button type="button" class="acc' + (a.key === o.accent ? ' on' : '') + '" data-k="' + a.key + '" style="--c:' + a.hex + '" title="' + a.key + '"></button>';
    }).join('');
  }

  /* ---------------- how it starts ---------------- */
  function opts() {
    var chip = function (n, add) { return '<i' + (add ? ' class="bz-add"' : '') + '>' + esc(n) + '</i>'; };
    var fixed = FIXED.map(function (r) { return chip(r.n); }).join('');
    $('opts').innerHTML =
      '<button type="button" class="bz-opt' + (o.start === 'new' ? ' on' : '') + '" data-start="new"><span class="bz-oh"><em>3</em><span>rooms</span><b>New</b></span>' +
        '<span class="bz-chips">' + fixed + '</span></button>' +
      '<button type="button" class="bz-opt' + (o.start === 'pre' ? ' on' : '') + '" data-start="pre"><span class="bz-oh"><em>7</em><span>rooms</span><b>Pre-build</b></span>' +
        '<span class="bz-chips">' + fixed + PRE.map(function (d) { return chip(d.name, true); }).join('') + '</span></button>';
  }

  /* ---------------- the tour of the pre-built office ---------------- */
  function tourAt(i) {
    ti = i;
    var r = TOUR[i], key = keyOf(r);
    $('t-n').textContent = i + 1;
    $('t-name').textContent = r.n;
    $('t-line').textContent = r.t;
    $('t-dots').innerHTML = TOUR.map(function (x, j) { return '<i class="' + (j < i ? 'done' : j === i ? 'on' : '') + '" title="' + esc(x.n) + '"></i>'; }).join('');
    if (office && key) { office.select(key); aim(key); }
    labels();
  }
  // The camera from the office's own home view, the same angle, part of the way to the room: the room in the middle
  // and its neighbours still round it (Office3D.focus goes so close the station is lost). Flat office: its own focus.
  var NEAR = 0.74;
  function aim(key) {
    var c = office.cells && office.cells[key];
    if (!c || !office.home || !office.V || !office.tween) return office.focus(key, 0, true);
    var RS = CO.iso.RS, h = office.home(), tgt = office.V(c[0] + RS / 2, c[1] + RS / 2, 0);
    var dir = h.pos.clone().sub(h.tgt);
    office.tween(tgt.clone().add(dir.setLength(dir.length() * NEAR)), tgt, 900);
  }
  // the step's number and the room's name, pinned over the room as the camera moves
  var pin = document.createElement('div'); pin.className = 'bz-pin'; pin.hidden = true; $('stage').appendChild(pin);
  (function pinLoop() {
    requestAnimationFrame(pinLoop);
    var key = step === 'tour' && office && office.camera && office.V ? keyOf(TOUR[ti]) : null, c = key && office.cells && office.cells[key];
    if (!c) { if (!pin.hidden) pin.hidden = true; return; }
    var RS = CO.iso.RS, v = office.V(c[0] + RS / 2, c[1] + RS / 2, 1.9).project(office.camera), st = $('office3d');
    var html = '<b>' + (ti + 1) + '</b>' + esc(TOUR[ti].n);
    if (pin._h !== html) { pin._h = html; pin.innerHTML = html; }
    pin.style.transform = 'translate(' + ((v.x + 1) / 2 * st.clientWidth).toFixed(1) + 'px,' + ((1 - v.y) / 2 * st.clientHeight).toFixed(1) + 'px) translate(-50%, -100%)';
    pin.hidden = false;
  })();

  /* ---------------- the steps ---------------- */
  function show(s) {
    var was = step;
    step = s;
    Array.prototype.forEach.call(document.querySelectorAll('.bz-card .bz-st'), function (el) { el.hidden = String(el.getAttribute('data-st')) !== String(s); });
    var n = s === 'tour' ? 3 : s;
    Array.prototype.forEach.call(document.querySelectorAll('#steps li'), function (li) {
      var k = +li.getAttribute('data-s'); li.className = k === n ? 'on' : k < n ? 'done' : '';
    });
    var inOffice = s === 3 || s === 'tour';
    $('b-prev').hidden = inOffice;
    $('stage').classList.toggle('bz-office', inOffice);
    if (inOffice) makeOffice(function () { if (step === 'tour') tourAt(ti); });
    else if (office) office.select(null);
    if (s === 3 && was === 'tour' && office) { office.select(null); office.fit(true); }
    if (s === 1 || s === 2) station();
    labels();
  }
  function labels() {
    var last = step === 'tour' ? ti === TOUR.length - 1 : step === 3 && o.start === 'new';
    $('b-next').firstChild.nodeValue = last ? 'Create company ' : 'Next ';
    $('b-next').classList.toggle('bz-fin', last);
  }
  function next() {
    if (step === 1) {
      if (!o.name) { var f = $('f-name'); f.focus(); f.style.borderColor = 'var(--red)'; return; }
      return show(2);
    }
    if (step === 2) return show(3);
    if (step === 3) { if (o.start === 'new') return finish(); show('tour'); return tourAt(0); }
    if (ti < TOUR.length - 1) return tourAt(ti + 1);
    finish();
  }
  function back() {
    if (step === 1) { location.href = 'start.html'; return; }
    if (step === 2) return show(1);
    if (step === 3) return show(2);
    if (ti > 0) return tourAt(ti - 1);
    show(3);
  }
  // Saved as the modal saves it; prebuild says which start the office's boot sets up (data.js/sim.js read it)
  function finish() {
    CO.saveProfile({ name: o.name, mission: o.mission, skin: o.skin, accent: o.accent, public: o.public, prebuild: o.start === 'pre' ? 'starter' : '' });
    location.href = 'index.html?empty&created=1';
  }

  /* ---------------- wiring ---------------- */
  $('f-pub').innerHTML = pub();
  skins(); accents(); opts();
  $('f-name').addEventListener('input', function (e) { o.name = e.target.value.trim(); e.target.style.borderColor = ''; CO.S.company.name = o.name || 'My Company'; station(); });
  $('f-mission').addEventListener('input', function (e) { o.mission = e.target.value.trim(); });
  [$('f-name'), $('f-mission')].forEach(function (f) { f.addEventListener('keydown', function (e) { if (e.key === 'Enter') next(); }); });
  $('f-pub').addEventListener('click', function () { o.public = !o.public; $('f-pub').classList.toggle('on', o.public); $('f-pub').innerHTML = pub(); station(); });
  $('f-skins').addEventListener('click', function (e) {
    var b = e.target.closest('.skin'); if (!b) return;
    o.skin = b.getAttribute('data-k');
    Array.prototype.forEach.call($('f-skins').querySelectorAll('.skin'), function (x) { x.classList.toggle('on', x === b); });
    station();
  });
  $('f-acc').addEventListener('click', function (e) {
    var b = e.target.closest('.acc'); if (!b) return;
    o.accent = b.getAttribute('data-k'); accents(); skins(); station();
  });
  $('opts').addEventListener('click', function (e) {
    var b = e.target.closest('.bz-opt'); if (!b) return;
    var k = b.getAttribute('data-start'); if (k === o.start) return;
    o.start = k; opts(); labels();
    restart(k);
  });
  $('b-next').addEventListener('click', next);
  $('b-back').addEventListener('click', back);
  // the stations' 3D pictures once the engine is there
  whenEngine(function (ok) { if (ok) { skins(); if (step === 1 || step === 2) station(); } });
  show(1);
  setTimeout(function () { $('f-name').focus(); }, 50);
  // for looking at it from the console or a test: the steps by name
  CO.builder = { show: show, tourAt: tourAt, next: next, back: back, o: o, get office() { return office; }, get step() { return step; } };
})();

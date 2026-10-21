/* The /company builder, two steps: 1 its name and its look -- the station turning big in the office's own space, big
 * arrows either side of it to go through the seven, its colour under it -- then 2 how it starts: New (the three rooms
 * every company has) or Pre-build (those three and four departments), the office drawn by the office's own 3D engine
 * (CO.U3.office) and a tour of it, each room's words a bubble out of the room itself. The office is built while the
 * name is typed, so Start shows it at once. Nothing here draws a room or a station itself: the stations are
 * makeStation's (u3d.js, stations.js), the office Office3D's, the departments come through the simulation's own door
 * (CO.act.addDept). Finishing saves the profile (CO.saveProfile) and opens the office.
 * The operator, 2026-10-20: "chci vyhodit Look step a hned si ho vybirat na tomto screenu ... velke sipky po bocich
 * tech lodi", "dalsi krok moc dlouho najizdi", "radeji kdyby z toho nejaka bublina dycky vychazela primo na mape". */
(function () {
  'use strict';
  var CO = window.CO;
  function $(id) { return document.getElementById(id); }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }

  // The rooms every company has, and the departments a pre-built one starts with. CO.PREBUILD (data.js) is the one
  // list both this page and the office's boot read; this one stands in where it is missing.
  // The tour tells one story, in this order (the operator, 2026-10-20: "cely tutorial bude mit timto pribeh a namotivuje
  // uzivatele"): NEXUS runs it all; the Vault holds what you earn, so build products; Development builds and ships them;
  // QA tests them and pays ET10 for verified bugs; beyond products, trading: the Quant Lab finds strategies, the
  // Trading desk runs the proven ones; Operations keeps everything optimal. Each room's pages on cymetica.com ride in
  // its bubble.
  var BALANCE = { et10: 12450, usdc: 86.2 };   // the account's balance on its Cymetica profile (sample; GET /api/v1/account)
  var PAGES = {
    development: [['Build it Better', 'https://cymetica.com/leaderboard/features']],
    testing: [['Bug board', 'https://cymetica.com/leaderboard/bugs?filter=mine']],
    testing_lab: [['Experiments', 'experiments.html']],
    trading_desk: [['My bots', 'https://cymetica.com/my-agents'], ['Agent Tournaments', 'https://cymetica.com/agent-tournaments']]
  };
  var FIXED = [
    { k: 'hub', n: 'Command', t: 'The main control point of your company, where NEXUS, the superintelligence, lives. You run the whole company just by talking to it: it runs every department, plans the work and reports back.' },
    { k: 'vault', n: 'Vault', t: 'The treasury of your company. All its earnings and rewards are stored here, in real USDC and ET10. Private: invisible to the public.' },
    { k: 'audit', n: 'Operations', t: 'Your company is watched over by a supervisor: it monitors every agent and process, optimises them, and makes sure no agent gets stuck in the mud.' }
  ];
  var PRE = CO.PREBUILD || [
    { key: 'testing', name: 'Cymetica QA' }, { key: 'development', name: 'Development' },
    { key: 'testing_lab', name: 'Quant Lab' }, { key: 'trading_desk', name: 'Trading desk' }
  ];
  var LINE = {
    development: 'Tell NEXUS your idea: Development designs it, builds it and ships it on Cymetica as your product. When people use it, it earns you real revenue, plus ET10 as a bonus. You can track how your products perform in the Products tab later.',
    testing: 'Test what you ship. QA tests your products, or any app on Cymetica you point it at, and files every bug it finds. Each verified bug pays you ET10 in rewards. Track your bugs on the Bugs leaderboard page.',
    testing_lab: 'Products are one way to earn, trading is another. Here researchers take your ideas and test them as experiments, looking for the most profitable trading strategies on Cymetica. All in paper money; all your experiments can be found on the Experiments lab page later.',
    trading_desk: 'Run your verified strategies with real money: create real trading agents and let them trade on Cymetica, or send them to Agent Tournaments to win additional rewards.'
  };
  var ORDER = ['hub', 'vault', 'development', 'testing', 'testing_lab', 'trading_desk', 'audit'];
  var TOUR = ORDER.map(function (k) {
    var f = FIXED.filter(function (x) { return x.k === k; })[0]; if (f) return f;
    var d = PRE.filter(function (x) { return x.key === k; })[0];
    return d ? { dk: d.key, n: d.name, t: LINE[d.key] || '' } : null;
  }).filter(Boolean);

  // what is being made: the modal's own defaults (app.js createCompanyModal), and the pre-built start
  // (the builder opens on the Shipyard in green: "jako uvodni firmu zobraz tuhle", 2026-10-20)
  var o = { name: '', mission: 'Make a massive amount of money.', skin: 'dome', accent: 'green', public: false, start: 'pre' };
  var step = 1, ti = 0, office = null, making = false, stage = null, ready = false;

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
  // a room's words on hover -- not in the tour, where its bubble says them ("zbytecne navic tooltip", 2026-10-20)
  function tipFor(kind, key) {
    return '';   // no tooltips in the builder: the tour's bubbles say what each room is
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

  /* ---------------- step 1's picture: the station, turning in the office's space ---------------- */
  // As the station pictures frame one (u3d.js Preview: the same lens, angle and distance), drawn by a renderer of
  // this page's own so its sky is the office's (entry3d.js) and not near-black; the company's name over it.
  function StationStage(el) {
    var U = CO.U3, T = U.THREE, self = this;
    U.geo();
    this.el = el;
    this.r = new T.WebGPURenderer({ antialias: false });   // the bloom pass multisamples (u3d.js, Post)
    this.r.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.r.toneMapping = T.ACESFilmicToneMapping; this.r.toneMappingExposure = 1.15;
    el.appendChild(this.r.domElement);
    this.scene = new T.Scene(); this.sky = CO.E3.sky(this.scene, 0); CO.E3.lights(this.scene);
    this.camera = new T.PerspectiveCamera(30, 1, 0.1, 2000);
    this.turn = new T.Group(); this.scene.add(this.turn);
    this.ban = document.createElement('div'); this.ban.className = 'b3 pvb bz-ban'; el.appendChild(this.ban);
    this.clock = new T.Clock(); this.v = new T.Vector3(); this.on = true;
    this.r.init().then(function () {
      try { self.post = new U.Post(self.r, self.scene, self.camera, 0.8, 0.45, 0.7); } catch (e) { self.post = null; }
      self.ready = true; self.go(self.on);
      el.classList.add('has3d');
    }).catch(function (e) { console.error('the station picture could not start:', e); });
  }
  StationStage.prototype.go = function (on) {
    this.on = on;
    if (this.ready) this.r.setAnimationLoop(on ? this.frame.bind(this) : null);
  };
  StationStage.prototype.set = function (s) {
    var U = CO.U3, T = U.THREE, key = [s.skin, s.accent, s.floors].join('|');
    if (key !== this.key) {
      this.key = key;
      if (this.plot) { this.turn.remove(this.plot.root); U.release(this.plot.root); }
      this.plot = U.makeStation({ skin: s.skin, accent: s.accent, public: true, departments: new Array(s.floors).fill(0), status: 'active' }, 7, { mine: true });
      this.plot.halo.material.opacity = 0.1;
      this.turn.add(this.plot.root);
      var p = this.plot, size = Math.max(p.top - p.bot, p.b.foot * 1.5), dist = size * 2.4 + 5;
      this.target = new T.Vector3(0, (p.top + p.bot) / 2 + size * 0.13, 0);
      this.camera.position.copy(new T.Vector3().setFromSpherical(new T.Spherical(dist, 1.16, Math.PI / 4)).add(this.target));
      this.camera.lookAt(this.target);
      this.anchor = new T.Vector3(0, p.top + 0.3, 0);
    }
    var name = String(s.name || '').toUpperCase(); if (name.length > 22) name = name.slice(0, 21) + '…';
    this.ban.className = 'b3 pvb bz-ban' + (s.public ? '' : ' priv');
    this.ban.style.setProperty('--acc', CO.accentHex(s.accent));
    this.ban.innerHTML = '<span class="you">YOU</span><span class="rib">' + (s.public ? '' : '<i class="lk"></i>') + esc(name) + '</span><span class="teth"></span>';
  };
  StationStage.prototype.frame = function () {
    var w = this.el.clientWidth, h = this.el.clientHeight; if (!w || !h || !this.plot) return;
    this.frames = (this.frames || 0) + 1;
    if (w !== this.w || h !== this.h) { this.w = w; this.h = h; this.camera.aspect = w / h; this.camera.updateProjectionMatrix(); this.r.setSize(w, h, false); }
    var t = this.clock.getElapsedTime();
    this.turn.rotation.y = -t * 0.28;   // clockwise seen from above ("zmen smer rotace", 2026-10-20)
    this.plot.b.tick(t); this.plot.body.position.y = Math.sin(t * 0.6) * 0.15;
    this.sky.position.copy(this.camera.position);
    if (this.post) this.post.render(); else this.r.render(this.scene, this.camera);
    var v = this.v.copy(this.anchor).project(this.camera);
    this.ban.style.transform = 'translate(' + ((v.x + 1) / 2 * w).toFixed(1) + 'px,' + ((1 - v.y) / 2 * h).toFixed(1) + 'px) translate(-50%,-100%)';
  };
  // the station as it stands: its picture, the company's name over it (every key typed), and in the card its name
  function station() {
    if (stage) stage.set({ skin: o.skin, accent: o.accent, floors: 3, name: o.name || 'Your company', public: o.public });
    var i = CO.SKINS.findIndex(function (s) { return s.key === o.skin; });
    $('lk-name').textContent = CO.skinName(o.skin);
    $('lk-n').textContent = (i + 1) + ' / ' + CO.SKINS.length;
  }
  function turnSkin(d) {
    var keys = CO.SKINS.map(function (s) { return s.key; }), i = keys.indexOf(o.skin);
    o.skin = keys[(i + d + keys.length) % keys.length]; station();
  }
  function accents() {
    $('lk-acc').innerHTML = CO.ACCENTS.map(function (a) {
      return '<button type="button" class="acc' + (a.key === o.accent ? ' on' : '') + '" data-k="' + a.key + '" style="--c:' + a.hex + '" title="' + a.key + '"></button>';
    }).join('');
  }

  /* ---------------- step 2's picture: the office, built ahead ---------------- */
  // Made while step 1 is on screen (behind it, the same size, not seen), drawn a few frames so its shaders are made,
  // then held still until Start shows it: Start opens on the office at once. Flat (office.js) where 3D cannot start.
  function makeOffice(cb) {
    if (office) return cb && cb();
    if (making) return;
    making = true;
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
        function then() {
          requestAnimationFrame(function () {
            office.resize(); office.fit(false);
            drawn(function () { veil(false); if (step === 1) hold(true); if (cb) cb(); });
          });
        }
      });
    });
  }
  // The office held still while it is not on show (its renderer's loop off), and let go again. Office3D starts its
  // own loop once its shaders are made, which can come after a hold: overLoop holds it again then.
  var heldAt = -1;
  function hold(on) {
    if (!office || !office.renderer || !office.frame) return;
    heldAt = on ? (office.frames || 0) : -1;
    office.renderer.setAnimationLoop(on ? null : function () { office.frame(); });
  }
  // the veil over the stage while the office is still being built (builder.css says why)
  function veil(on) { $('veil').classList.toggle('on', on); }
  // once the office has drawn twice from now (its shaders made: Office3D counts frames from its first; the flat one
  // has no count and is drawn at once); 12 s at most
  function drawn(cb) {
    var f0 = office && office.frames || 0, t0 = performance.now();
    (function w() { if (!office || !office.renderer || (office.frames || 0) >= f0 + 2 || performance.now() - t0 > 12000) return cb(); requestAnimationFrame(w); })();
  }
  function built() { return !!office && (!office.renderer || (office.frames || 0) >= 2); }
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
  // A room clicked in the pre-built office: at Start it begins the tour there (the call-out sends you to Command, the
  // first), in the tour it goes to that room -- the next one, which the call-out marks, or any other
  CO.on('office:click', function (key) {
    if (o.start !== 'pre' || (step !== 2 && step !== 'tour')) return;
    for (var i = 0; i < TOUR.length; i++) if (keyOf(TOUR[i]) === key) { if (step !== 'tour') show('tour'); return tourAt(i); }
  });

  /* ---------------- how it starts ---------------- */
  // The two starts as cards: how many rooms, the start's name, and its rooms as the office's own icons (CO.deptIconSvg,
  // data.js -- the rail's and the glass signs'), each named in its tooltip; a pre-built department ringed in green.
  // ("misto tech nazvu mistnosti tam dej spis ikonky", "misto pre-build dej spis CyMetica Pre-Build", 2026-10-20)
  function opts() {
    var icon = function (d, n, add) {
      var ic = CO.deptIconSvg ? CO.deptIconSvg(d, 22) : null;
      return '<i class="bz-ic' + (add ? ' bz-add' : '') + '" title="' + esc(n) + '" style="--c:' + (ic ? ic.color : '#00cfff') + '">' + (ic ? ic.svg : '') + '</i>';
    };
    var fixed = FIXED.map(function (r) { return icon(r.k, r.n); }).join('');
    var card = function (k, n, title, sub, icons) {
      return '<button type="button" class="bz-opt' + (o.start === k ? ' on' : '') + '" data-start="' + k + '">' +
        '<span class="bz-oh"><em>' + n + '</em><span class="bz-ot"><b>' + title + '</b><span>' + sub + '</span></span><i class="bz-ok"></i></span>' +
        '<span class="bz-ics">' + icons + '</span></button>';
    };
    $('opts').innerHTML =
      card('new', 3, 'New', 'rooms · add departments as you go', fixed) +
      card('pre', 7, 'CyMetica Pre-Build', 'rooms · ' + PRE.length + ' departments · ' + PRE.reduce(function (n, d) { var t = (CO.TEMPLATES || []).filter(function (x) { return x.key === d.key; })[0]; return n + (t ? t.experts.length : 0); }, 1) + ' agents', fixed + PRE.map(function (d) { return icon({ key: d.key }, d.name, true); }).join(''));
  }

  /* ---------------- the tour: each room's words in a bubble out of the room ---------------- */
  // who works in a room, first in its bubble ("do kazdeho stepu ... Agents: a tady das ty ikonky"): its experts' astronauts
  // (shots/astro-*.webp), NEXUS in Command, the supervisor in Operations; the Vault has nobody
  function expertsOf(r) {
    if (r.k === 'hub') return [['NEXUS', null]];
    if (r.k === 'audit') return [['Supervisor', null]];
    if (r.k) return [];
    var t = (CO.TEMPLATES || []).filter(function (x) { return x.key === r.dk; })[0];
    return (t ? t.experts : []).map(function (k) { return [CO.expertName ? CO.expertName(k) : k, 'shots/astro-' + k + '.webp']; });
  }
  function agentsRow(r) {
    var a = expertsOf(r); if (!a.length) return '';
    return '<div class="bz-ag"><span>AGENTS</span>' + a.map(function (x) {
      return '<i>' + (x[1] ? '<img alt="" src="' + x[1] + '">' : '<b class="core"></b>') + esc(x[0]) + '</i>';
    }).join('') + '</div>';
  }
  function tourAt(i) {
    ti = i;
    var key = keyOf(TOUR[i]), r = TOUR[i], last = i === TOUR.length - 1, ic = CO.deptIconSvg ? CO.deptIconSvg(r.k || { key: r.dk }, 22) : null;
    $('bub').innerHTML =
      '<div class="bz-bh">' + (ic ? '<i class="bz-ic" style="--c:' + ic.color + '">' + ic.svg + '</i>' : '') +
        '<span class="bz-bt"><b>' + esc(r.n) + '</b><em>' + (i + 1) + ' of ' + TOUR.length + '</em></span><button type="button" class="bz-x" data-a="close" title="Back to Start">×</button></div>' +
      agentsRow(r) + '<p>' + esc(r.t) + '</p>' + (r.k === 'vault' ? '<div class="bz-bal" title="Your balance on your Cymetica profile"><span><b>' + BALANCE.et10.toLocaleString('en-US') + '</b> ET10</span><span><b>' +
        BALANCE.usdc.toFixed(2) + '</b> USDC</span><em>your balance now</em></div>' : '') +
      ((PAGES[r.k || r.dk] || []).length ? '<div class="bz-pg">' + PAGES[r.k || r.dk].map(function (p) {
        return '<a href="' + esc(p[1]) + '" target="_blank" rel="noopener"><svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="9" cy="11" r="6.2"/><ellipse cx="9" cy="11" rx="2.6" ry="6.2"/><path d="M2.8 11h12.4 M12.6 2.6h4.8v4.8 M17.4 2.6l-5.2 5.2"/></svg>' + esc(p[0]) + '</a>';
      }).join('') + '</div>' : '') +
      '<div class="bz-bf"><span class="bz-dots">' + TOUR.map(function (x, j) { return '<i class="' + (j < i ? 'done' : j === i ? 'on' : '') + '"></i>'; }).join('') + '</span>' +
        '<button type="button" class="btn" data-a="back">← Back</button>' +
        '<button type="button" class="bz-go' + (last ? ' fin' : '') + '" data-a="next">' + (last ? 'Create company' : 'Next') + ' →</button></div>';
    if (office && key) { office.select(key); aim(key); }
  }
  // The camera from the office's own home view, the same angle, part of the way to the room: the room in the middle
  // and its neighbours still round it. Flat office: its own focus.
  var NEAR = 0.74;
  function aim(key) {
    var c = office.cells && office.cells[key];
    if (!c || !office.home || !office.V || !office.tween) return office.focus(key, 0, true);
    var RS = CO.iso.RS, h = office.home(), tgt = office.V(c[0] + RS / 2, c[1] + RS / 2, 0);
    var dir = h.pos.clone().sub(h.tgt);
    office.tween(tgt.clone().add(dir.setLength(dir.length() * NEAR)), tgt, 900);
  }
  // Over the office, following the camera: the bubble over the tour's room, and the call-out -- a ring pulsing on a
  // room's floor, a solid label saying what a click there does: at Start on Command, where the tour begins, in the
  // tour on the next room. A click on the call-out does what a click on its room does.
  var bub = $('bub'), call = document.createElement('button'); call.type = 'button'; call.className = 'bz-call'; call.hidden = true; $('stage').appendChild(call);
  call.addEventListener('click', function () { if (step === 2) { show('tour'); tourAt(0); } else if (step === 'tour' && ti < TOUR.length - 1) tourAt(ti + 1); });
  bub.addEventListener('click', function (e) {
    if (e.target.closest('.bz-pg a')) return;
    var a = e.target.closest('[data-a]'); if (!a) return;
    a = a.getAttribute('data-a');
    if (a === 'close') show(2); else if (a === 'back') tourBack(); else next();
  });
  function over(el, key, z, html) {
    var c = key && office.cells && office.cells[key];
    if (!c) { if (!el.hidden) el.hidden = true; return; }
    var RS = CO.iso.RS, v = office.V(c[0] + RS / 2, c[1] + RS / 2, z).project(office.camera), st = $('office3d');
    if (html != null && el._h !== html) { el._h = html; el.innerHTML = html; }
    el.style.transform = 'translate(' + ((v.x + 1) / 2 * st.clientWidth).toFixed(1) + 'px,' + ((1 - v.y) / 2 * st.clientHeight).toFixed(1) + 'px) translate(-50%, -100%)';
    el.hidden = false;
  }
  (function overLoop() {
    requestAnimationFrame(overLoop);
    if (step === 1 && office && heldAt >= 0 && (office.frames || 0) > heldAt + 1) hold(true);
    var live = office && office.camera && office.V && !$('veil').classList.contains('on') && (office.frames || 0) > 1;
    var tour = live && step === 'tour', start = live && step === 2 && o.start === 'pre';
    // (the bubble's point a little above the room's walls, so it stands over the room and not on its back wall)
    if (tour) over(bub, keyOf(TOUR[ti]), 2.5, null); else if (!bub.hidden) bub.hidden = true;
    if (start) over(call, 'hub', 0.25, '<span class="lb"><small><b>Welcome to your AI-native company</b>run by real AI expert agents</small>Click here<em>to start the tour</em></span><i class="stem"></i><i class="ring"></i>');
    else if (tour && ti < TOUR.length - 1) over(call, keyOf(TOUR[ti + 1]), 0.25, '<span class="lb sm">Next ›</span><i class="stem"></i><i class="ring"></i>');
    else if (!call.hidden) call.hidden = true;
  })();

  /* ---------------- the steps ---------------- */
  function show(s) {
    var was = step;
    step = s;
    Array.prototype.forEach.call(document.querySelectorAll('.bz-card .bz-st'), function (el) { el.hidden = String(el.getAttribute('data-st')) !== String(s === 'tour' ? 2 : s); });
    Array.prototype.forEach.call(document.querySelectorAll('#steps li'), function (li) {
      var k = +li.getAttribute('data-s'), n = s === 'tour' ? 2 : s; li.className = k === n ? 'on' : k < n ? 'done' : '';
    });
    var st = $('stage'), inOffice = s === 2 || s === 'tour';
    st.classList.toggle('bz-office', inOffice);
    // (the card stays through the tour, on its Start step: "ten panel nalevo nechej", 2026-10-20)
    if (stage && ready) stage.go(s === 1);
    if (inOffice) {
      if (office) {
        hold(false);
        if (s === 2) { office.select(null); if (was === 'tour' || was === 1) office.fit(was === 'tour'); }
        // still being built (Next came quickly): the veil until it has drawn, never an empty stage
        if (!built()) { veil(true); drawn(function () { veil(false); }); }
      } else { veil(true); makeOffice(function () { if (step === 'tour') tourAt(ti); }); }
    } else hold(true);
    labels();
  }
  // the main button: Next, Create company for New -- and none at Start with Pre-build: the call-out on Command
  // starts the tour (the tour's own buttons are in its bubble)
  function labels() {
    var last = step === 2 && o.start === 'new';
    $('b-next').firstChild.nodeValue = last ? 'Create company ' : 'Next ';
    $('b-next').classList.toggle('bz-fin', last);
    $('b-next').hidden = (step === 2 && o.start === 'pre') || step === 'tour';
  }
  function next() {
    if (step === 1) {
      if (!o.name) { var f = $('f-name'); f.focus(); f.style.borderColor = 'var(--red)'; return; }
      return show(2);
    }
    if (step === 2) { if (o.start === 'new') return finish(); show('tour'); return tourAt(0); }
    if (ti < TOUR.length - 1) return tourAt(ti + 1);
    finish();
  }
  // the card's Back: a step back, and out of the tour to Start; the bubble's Back goes a room back (tourBack)
  function back() {
    if (step === 1) { location.href = 'start.html'; return; }
    if (step === 2) return show(1);
    show(2);
  }
  function tourBack() { if (ti > 0) tourAt(ti - 1); else show(2); }
  // Saved as the modal saves it; prebuild says which start the office's boot sets up (data.js/sim.js read it)

  // The Create company popup (the operator, 2026-10-20: without an account, sign up first; with one, it costs 5,000 ET10,
  // or the Pro plan, or a 7-day free trial -- Cymetica's to choose among, SPEC section 3). The mock shows all three, and
  // ?guest shows it signed out.
  var GUEST = /[?&]guest\b/.test(location.search);
  function createGate(done) {
    var el = $('gate'); if (!el) return done();
    var nm = o.name || 'your company', can = BALANCE.et10 >= 5000;
    el.innerHTML = '<div class="bz-gc"><button type="button" class="bz-x" data-g="close" title="Back">×</button>' + (GUEST ?
      '<h3>Sign up first.</h3><p>A company belongs to a Cymetica account.</p>' +
      '<div class="bz-gb"><button type="button" class="bz-go" data-g="signup">Sign up →</button><button type="button" class="btn" data-g="login">Log in</button></div>' :
      '<h3>Create ' + esc(nm) + '.</h3><p>Pick how you start.</p><div class="bz-gw">' +
        '<button type="button" class="bz-gw1' + (can ? '' : ' off') + '" data-g="et10"><em>PAY ONCE</em><b>5,000 <i>ET10</i></b><span>from your balance · ' + BALANCE.et10.toLocaleString('en-US') + ' ET10</span></button>' +
        '<button type="button" class="bz-gw1" data-g="pro"><em>PRO PLAN</em><b>Upgrade</b><span>a company comes with Pro</span></button>' +
        '<button type="button" class="bz-gw1" data-g="trial"><em>FREE TRIAL</em><b>7 days</b><span>then choose a way to keep it</span></button>' +
      '</div>') + '</div>';
    el.hidden = false;
    el.onclick = function (e) {
      var b = e.target.closest('[data-g]');
      if (!b && e.target === el) b = { getAttribute: function () { return 'close'; } };
      if (!b) return;
      var g = b.getAttribute('data-g');
      if (g === 'close') { el.hidden = true; return; }
      if (g === 'signup' || g === 'login') { GUEST = false; return createGate(done); }   // mockup: signed in, then on
      if (g === 'et10' && !can) return;
      el.hidden = true; done();
    };
  }
  // Create company asks first: who is signing up, and which way in (createGate); then the company is made
  function finish() { createGate(make); }
  function make() {
    CO.saveProfile({ name: o.name, mission: o.mission, skin: o.skin, accent: o.accent, public: o.public, prebuild: o.start === 'pre' ? 'starter' : '' });
    location.href = 'index.html?empty&created=1';
  }

  /* ---------------- wiring ---------------- */
  function pub() {
    return '<span class="sw"></span><div><b>' + (o.public ? 'Public' : 'Private') + '</b><span>' +
      (o.public ? 'Anyone can look inside, read only.' : 'Others see its name, station and mission.') + '</span></div>';
  }
  $('f-pub').innerHTML = pub();
  accents(); opts();
  $('f-name').addEventListener('input', function (e) { o.name = e.target.value.trim(); e.target.style.borderColor = ''; CO.S.company.name = o.name || 'My Company'; station(); });
  $('f-mission').addEventListener('input', function (e) { o.mission = e.target.value.trim(); });
  [$('f-name'), $('f-mission')].forEach(function (f) { f.addEventListener('keydown', function (e) { if (e.key === 'Enter') next(); }); });
  $('f-pub').addEventListener('click', function () { o.public = !o.public; $('f-pub').classList.toggle('on', o.public); $('f-pub').innerHTML = pub(); station(); });
  $('lk-prev').addEventListener('click', function () { turnSkin(-1); });
  $('lk-next').addEventListener('click', function () { turnSkin(1); });
  // the arrow keys go through the stations too, unless a field is being typed in
  document.addEventListener('keydown', function (e) {
    if (step !== 1 || /^(INPUT|TEXTAREA)$/.test((document.activeElement || {}).tagName || '')) return;
    if (e.key === 'ArrowLeft') turnSkin(-1); else if (e.key === 'ArrowRight') turnSkin(1);
  });
  $('lk-acc').addEventListener('click', function (e) { var b = e.target.closest('.acc'); if (!b) return; o.accent = b.getAttribute('data-k'); accents(); station(); });
  $('opts').addEventListener('click', function (e) {
    var b = e.target.closest('.bz-opt'); if (!b) return;
    var k = b.getAttribute('data-start'); if (k === o.start) return;
    o.start = k; opts(); labels();
    restart(k);
  });
  $('b-next').addEventListener('click', next);
  $('b-back').addEventListener('click', back);
  show(1);
  station();
  setTimeout(function () { $('f-name').focus(); }, 50);
  // The engine there: the station drawn twice (its shaders made) and held, the office built behind it, then both
  // shown at once. Before, the ship turned while the office's build held the page in turns of up to 1.4 s -- "jak
  // kliknu start company tak se to seka nez se to nacte" (measured 2026-10-20: 13 frames over 50 ms in the first
  // 5 s); now only the veil's ring turns (off the page's thread) until everything is made, and nothing stutters.
  function reveal() { ready = true; if (stage) stage.go(step === 1); veil(false); }
  whenEngine(function (ok) {
    if (!ok || !CO.E3) return reveal();
    stage = new StationStage($('b-prev')); station(); stage.go(true);
    (function wait() {
      if ((stage.frames || 0) >= 2) { stage.go(false); makeOffice(reveal); } else requestAnimationFrame(wait);
    })();
  });
  // for looking at it from the console or a test: the steps by name
  CO.builder = { show: show, tourAt: tourAt, next: next, back: back, o: o, get office() { return office; }, get step() { return step; } };
})();

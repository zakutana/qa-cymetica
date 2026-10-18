/* The Universe composed live from the operator's Gemini pieces (gemini-prompts.md; keyed and measured by
 * tools/sprites.py into assets/gen/): his painted background, and on its six painted orbits one station for every
 * company there is, any number of them, each turning slowly round Cymetica's core. Stations behind the core draw
 * under its light (app.js's collider canvas), the rest over it; each carries a name plate and a hit area.
 * assets/gen/ is kept out of git, so wherever the pieces are not there, CO.uvLive.load answers false and the
 * static picture (app.js buildPic) is what shows. */
(function () {
  'use strict';
  var CO = window.CO = window.CO || {};
  var BASE = 'assets/gen/';
  // a company's station key (the data's tower, dome, ...) to the shape the brief names: U-station-<shape>-<colour>
  var SHAPE = { tower: 'spire', dome: 'biodome', pyramid: 'ziggurat', orbital: 'ring', rocket: 'starship', vault: 'vault' };
  // the hue a hull of each of the site's four colours has (HUE), and the hue a stand-in's hull is turned to (TO):
  // a muted hull reads brown at hue 0 and violet at 217, so red and blue are aimed a little off and red is lifted
  var HUE = { green: 160, cyan: 191, blue: 217, red: 0 }, TO = { green: 160, cyan: 188, blue: 207, red: 356 }, LIFT = { red: 1.35, blue: 1.1 };
  var OUTER_PERIOD = 1800;   // seconds for the outer orbit to go round once; the inner ones faster, as r^-1.5

  var L = CO.uvLive = { state: 'idle', man: null, img: {}, waits: [] };
  // sprites.json and the images it names, once; cb(true) when the background, its rings and a station are in
  L.load = function (cb) {
    if (L.state === 'ok' || L.state === 'no') return cb(L.state === 'ok');
    L.waits.push(cb);
    if (L.state === 'loading') return;
    L.state = 'loading';
    var done = function (ok) { L.state = ok ? 'ok' : 'no'; var w = L.waits; L.waits = []; w.forEach(function (f) { f(ok); }); };
    if (!window.fetch) return done(false);
    fetch(BASE + 'sprites.json', { cache: 'no-cache' }).then(function (r) { return r.ok ? r.json() : null; }).then(function (m) {
      var bg = m && m['U-background'], st = m ? Object.keys(m).filter(function (k) { return k.indexOf('U-station-') === 0; }) : [];
      if (!bg || !bg.calib || !st.length) return done(false);
      L.man = m;
      var names = ['U-background'].concat(st), left = names.length;
      names.forEach(function (n) {
        var im = new Image();
        var fin = function () { if (--left) return; done(!!L.img['U-background'] && Object.keys(L.img).length > 1); };
        im.onload = function () { L.img[n] = im; fin(); };
        im.onerror = fin;
        im.src = BASE + n + '.webp';
      });
    }).catch(function () { done(false); });
  };

  // a stand-in: the hull's hue turned to another colour's, nothing else (windows, solar panels and the blue
  // thruster light keep theirs); the hues kept close together so a turned hull stays one colour
  function tint(im, from, to, lift) {
    if (from === to) return im;
    lift = lift || 1;
    var c = document.createElement('canvas'), g = c.getContext('2d');
    c.width = im.naturalWidth; c.height = im.naturalHeight; g.drawImage(im, 0, 0);
    var d;
    try { d = g.getImageData(0, 0, c.width, c.height); } catch (e) { return im; }
    var p = d.data;
    for (var i = 0; i < p.length; i += 4) {
      if (p[i + 3] < 150) continue;
      var r = p[i] / 255, gg = p[i + 1] / 255, b = p[i + 2] / 255, mx = Math.max(r, gg, b), mn = Math.min(r, gg, b), l = (mx + mn) / 2, ch = mx - mn;
      if (ch < 0.04) continue;
      var s = ch / (1 - Math.abs(2 * l - 1)), h = mx === r ? ((gg - b) / ch) % 6 : mx === gg ? (b - r) / ch + 2 : (r - gg) / ch + 4;
      h *= 60; if (h < 0) h += 360;
      var dh = ((h - from + 540) % 360) - 180;
      if (dh < -28 || dh > 42 || s < 0.08) continue;
      h = (to + dh * 0.4 + 360) % 360; s = Math.min(1, s * lift);
      var C = (1 - Math.abs(2 * l - 1)) * s, X = C * (1 - Math.abs((h / 60) % 2 - 1)), m = l - C / 2, q = Math.floor(h / 60), rr, g2, bb;
      if (q === 0) { rr = C; g2 = X; bb = 0; } else if (q === 1) { rr = X; g2 = C; bb = 0; } else if (q === 2) { rr = 0; g2 = C; bb = X; }
      else if (q === 3) { rr = 0; g2 = X; bb = C; } else if (q === 4) { rr = X; g2 = 0; bb = C; } else { rr = C; g2 = 0; bb = X; }
      p[i] = (rr + m) * 255; p[i + 1] = (g2 + m) * 255; p[i + 2] = (bb + m) * 255;
    }
    g.putImageData(d, 0, 0);
    return c;
  }
  var ART = {};
  // the operator's station of that shape and colour; until he has sent it, the same shape in another colour (or
  // the first station there is) with its hull turned to this colour
  function art(skin, accent) {
    var shape = SHAPE[skin] || 'spire', col = HUE[accent] != null ? accent : 'green', key = shape + '-' + col, exact = 'U-station-' + key;
    if (ART[key]) return ART[key];
    if (L.img[exact]) return (ART[key] = { im: L.img[exact], m: L.man[exact] });
    var names = Object.keys(L.img).filter(function (n) { return n.indexOf('U-station-') === 0; });
    var src = names.filter(function (n) { return n.indexOf('U-station-' + shape + '-') === 0; })[0] || names[0], from = src.split('-').pop();
    return (ART[key] = { im: tint(L.img[src], HUE[from] != null ? HUE[from] : HUE.green, TO[col], LIFT[col]), m: L.man[src] });
  }

  // layers: the canvases behind and in front of the core's, and a layer of plates and hit areas over all of it
  CO.UvLive = function (el, hooks) {
    var bg = L.man['U-background'];
    this.el = el; this.h = hooks; this.W = bg.w; this.H = bg.h; this.cal = bg.calib;
    this.items = []; this.s = 1; this.vis = [0, 0, this.W, this.H]; this.t0 = performance.now(); this.hov = null; this.raf = 0; this.last = 0;
    this.live = {};
    var self = this;
    el.top.addEventListener('mouseover', function (e) { var b = e.target.closest('.uvhs'); self.hov = b ? +b.getAttribute('data-id') : null; self.mark(); });
    el.top.addEventListener('mouseleave', function () { self.hov = null; self.mark(); });
  };
  var P = CO.UvLive.prototype;
  // every company to a ring: as many on a ring as its length makes room for, the biggest companies inside, ours
  // on the third ring, in front, left of the core (the corner card is on the right). The outermost painted ring
  // stays empty: it runs along the picture's edges, which a wide stage crops away.
  P.set = function (mine) {
    var list = CO.UNIVERSE.slice().sort(function (a, b) { return CO.floorsOf(b) - CO.floorsOf(a) || a.id - b.id; });
    var R = this.cal.rings.slice(0, -1), N = list.length + 1, wt = R.map(function (r) { return r[2] + r[3]; }), tot = wt.reduce(function (a, b) { return a + b; }, 0);
    var cnt = wt.map(function (w) { return Math.max(1, Math.round(w / tot * N)); }), d = N - cnt.reduce(function (a, b) { return a + b; }, 0);
    for (var i = cnt.length - 1; d !== 0; i = (i + cnt.length - 1) % cnt.length) { if (d > 0) { cnt[i]++; d--; } else if (cnt[i] > 1) { cnt[i]--; d++; } }
    var out = this.cal.rings[this.cal.rings.length - 1], items = [], k = 0, ME = 2;
    R.forEach(function (r, o) {
      var m = cnt[o], w = 2 * Math.PI / OUTER_PERIOD * Math.pow(out[2] / r[2], 1.5), a0 = o === ME ? Math.PI / 2 + 0.5 : o * 0.93 + 0.4;
      for (var j = 0; j < m; j++) {
        var me = o === ME && j === 0, c = me ? mine : list[k++];
        if (c) items.push({ c: c, mine: me, ring: r, a: a0 + j / m * 2 * Math.PI, w: w, bob: (c.id || 0) * 1.7 });
      }
    });
    this.items = items;
    this.base = Math.max(120, Math.min(300, 300 * Math.sqrt(14 / N)));
    CO.uvSeed(items, this.live);
    this.build();
  };
  P.setMine = function (mine) {
    var it = this.items.filter(function (x) { return x.mine; })[0];
    if (!it) return;
    var was = [it.c.name, it.c.skin, it.c.accent].join('|');
    it.c = mine;
    if (was !== [mine.name, mine.skin, mine.accent].join('|')) this.build();
  };
  P.build = function () {
    var esc = CO.esc || function (s) { return String(s).replace(/[&<>"]/g, function (m) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[m]; }); };
    var self = this;
    this.el.top.innerHTML = this.items.map(function (it, i) {
      var c = it.c, cls = 'p3 uvp' + (it.mine ? ' me' : '') + (c.public || it.mine ? '' : ' priv') + (c.status === 'paused' ? ' paused' : '');
      return '<button class="uvhs" data-id="' + (it.mine ? 0 : c.id) + '" data-i="' + i + '"></button>' +
        '<div class="' + cls + '" data-i="' + i + '" style="--c:' + CO.accentHex(c.accent) + '"><div class="p3h"><i style="color:' + CO.accentHex(c.accent) + '"></i><b>' + esc(c.name) + '</b>' +
        (it.mine ? '<em>YOU</em>' : '') + '</div></div>';
    }).join('');
    this.items.forEach(function (it, i) {
      it.hit = self.el.top.querySelector('.uvhs[data-i="' + i + '"]');
      it.lab = self.el.top.querySelector('.uvp[data-i="' + i + '"]');
      it.art = art(it.c.skin, it.c.accent);
    });
    this.mark();
  };
  P.mark = function () {
    var h = this.hov;
    this.items.forEach(function (it) { if (it.lab) it.lab.classList.toggle('hov', h != null && (it.mine ? 0 : it.c.id) === h); });
  };
  P.find = function (id) { for (var i = 0; i < this.items.length; i++) if ((this.items[i].mine ? 0 : this.items[i].c.id) === id) return this.items[i]; return null; };
  // our station's plate flashes: "Mine" on the map
  P.ping = function () {
    var it = this.find(0); if (!it || !it.lab) return;
    it.lab.classList.remove('ping'); void it.lab.offsetWidth; it.lab.classList.add('ping');
  };
  // s: display px per picture px; ox, oy: where the picture's corner is on the stage (negative where cropped)
  P.fit = function (s, ox, oy, sw, sh) {
    this.s = s; this.oy = oy;
    this.vis = [Math.max(0, -ox / s), Math.max(0, -oy / s), Math.min(this.W, (sw - ox) / s), Math.min(this.H, (sh - oy) / s)];
    var dpr = Math.min(window.devicePixelRatio || 1, 2), w = Math.round(this.W * s * dpr), h = Math.round(this.H * s * dpr);
    [this.el.back, this.el.front].forEach(function (c) { if (c.width !== w || c.height !== h) { c.width = w; c.height = h; } });
    this.dpr = dpr;
    this.draw(performance.now());
  };
  P.start = function () {
    var self = this;
    if (this.raf) return;
    var loop = function (now) {
      self.raf = requestAnimationFrame(loop);
      if (document.hidden || !self.el.back.offsetParent || now - self.last < 33) return;
      self.last = now; self.draw(now);
    };
    this.raf = requestAnimationFrame(loop);
  };
  P.draw = function (now) {
    var t = (now - this.t0) / 1000, s = this.s, k = s * (this.dpr || 1), cal = this.cal, out = cal.rings[cal.rings.length - 1];
    var yT = out[1] - out[3], yB = out[1] + out[3], vis = this.vis, self = this;
    var gb = this.el.back.getContext('2d'), gf = this.el.front.getContext('2d');
    gb.clearRect(0, 0, this.el.back.width, this.el.back.height); gf.clearRect(0, 0, this.el.front.width, this.el.front.height);
    var list = this.items.map(function (it) {
      var r = it.ring, a = it.a + it.w * t, x = r[0] + r[2] * Math.cos(a), y = r[1] + r[3] * Math.sin(a);
      var dep = 0.55 + 0.45 * Math.max(0, Math.min(1, (y - yT) / (yB - yT))), m = it.art.m, w = self.base * dep, h = w * m.h / m.w;
      y += Math.sin(t * 0.8 + it.bob) * 3 * dep;
      var left = x - w * m.anchor[0] / m.w, top = y - h * m.anchor[1] / m.h;
      // a station going over the edge of what shows fades out on its way, rather than being cut by it
      var al = Math.min(1, 1 - (vis[1] - top) / (0.55 * h), 1 - (top + h - vis[3]) / (0.45 * h), 1 - (vis[0] - left) / (0.5 * w), 1 - (left + w - vis[2]) / (0.5 * w));
      return { it: it, x: x, y: y, w: w, h: h, left: left, top: top, dep: dep, al: Math.max(0, Math.min(1, al)) };
    }).sort(function (a, b) { return a.y - b.y; });
    list.forEach(function (p, z) {
      var it = p.it, g = p.y < cal.core[1] + 30 ? gb : gf, hov = self.hov != null && (it.mine ? 0 : it.c.id) === self.hov;
      if (p.al > 0.01) {
        g.globalAlpha = p.al;
        if (hov || it.mine) { g.shadowColor = hov ? 'rgba(0,207,255,.85)' : 'rgba(0,255,136,.5)'; g.shadowBlur = (hov ? 26 : 16) * k; }
        g.drawImage(it.art.im, p.left * k, p.top * k, p.w * k, p.h * k);
        g.shadowBlur = 0; g.globalAlpha = 1;
      }
      p.z = z; p.on = p.al > 0.5;
      it.hit.style.display = p.on ? '' : 'none';
      if (p.on) it.hit.style.cssText = 'left:' + ((p.left + p.w * 0.14) * s).toFixed(1) + 'px;top:' + (p.top * s).toFixed(1) + 'px;width:' + (p.w * 0.72 * s).toFixed(1) + 'px;height:' + (p.h * 0.86 * s).toFixed(1) + 'px;z-index:' + (z * 2);
    });
    // name plates: ours first, then the one under the pointer, then front to back; a plate that would cover one
    // already placed, or stick out of the top, waits for the pointer (the tip still names it)
    var placed = [], vt = Math.max(0, -this.oy || 0);
    list.slice().sort(function (a, b) { return (b.it.mine - a.it.mine) || (isHov(b) - isHov(a)) || b.y - a.y; }).forEach(function (p) {
      var it = p.it, lab = it.lab;
      if (!p.on) { lab.style.display = 'none'; return; }
      lab.style.display = '';
      if (!it.lw) { it.lw = lab.offsetWidth; it.lh = lab.offsetHeight; }
      var sc = 0.72 + 0.34 * p.dep, cx = p.x * s, by = (p.top + p.h * 0.04) * s, w = it.lw * sc, h = it.lh * sc;
      var box = [cx - w / 2 - 3, by - h - 3, cx + w / 2 + 3, by + 3];
      var hit = box[1] < vt || placed.some(function (q) { return box[0] < q[2] && box[2] > q[0] && box[1] < q[3] && box[3] > q[1]; });
      if (hit && !it.mine && !isHov(p)) { lab.style.display = 'none'; return; }
      placed.push(box);
      lab.style.transform = 'translate(' + cx.toFixed(1) + 'px,' + by.toFixed(1) + 'px) translate(-50%,-100%) scale(' + sc.toFixed(3) + ')';
      lab.style.zIndex = isHov(p) || it.mine ? 999 : p.z * 2 + 1;
      lab.style.opacity = p.al.toFixed(2);
    });
    function isHov(p) { return +(self.hov != null && (p.it.mine ? 0 : p.it.c.id) === self.hov); }
  };
  P.tip = function (id) {
    var it = this.find(id);
    return it ? CO.uvTip(id, { c: it.c, mine: it.mine }, this.live) : '';
  };
  P.stats = function () { return CO.uvStats(this.items, this.live); };
})();

/* The /company mockup: the 3D network. The Manager at the centre, a node per department on
 * a ring, a node per hired expert around it, the owner above and the supervisor below.
 * Drawn on a canvas in perspective, turning slowly; drag to turn it, wheel to zoom. Work
 * travels along the edges hop by hop, coloured by outcome, from the same events the
 * office's packets ride. */
(function () {
  'use strict';
  var CO = window.CO;
  var COL = { cyan: '#00cfff', green: '#00ff88', red: '#ff4444', blue: '#3b82f6', slate: '#7f93ad', text: '#e6edf7', dim: '#a9b8cc' };
  var RGB = { cyan: '0,207,255', green: '0,255,136', red: '255,68,68', blue: '59,130,246', slate: '127,147,173' };
  var ST = { working: 'cyan', queued: 'blue', waiting: 'red', idle: 'slate' };

  function Net(canvas, stage, tipFor) {
    this.c = canvas; this.ctx = canvas.getContext('2d'); this.stage = stage; this.tipFor = tipFor;
    this.yaw = 0.6; this.pitch = 0.42; this.zoomK = 1; this.on = false; this.flows = []; this.nodes = {}; this.hover = null;
    this.stars = [];
    for (var i = 0; i < 160; i++) {
      var u = Math.random() * 2 - 1, a = Math.random() * Math.PI * 2, r = 700 + Math.random() * 500, s = Math.sqrt(1 - u * u);
      this.stars.push([r * s * Math.cos(a), r * u * 0.6, r * s * Math.sin(a), Math.random()]);
    }
    this.bind();
    var self = this;
    requestAnimationFrame(function loop(t) { if (self.on) self.frame(t); requestAnimationFrame(loop); });
  }
  CO.Net = Net;

  Net.prototype.build = function () {
    var S = CO.S, n = S.departments.length, R = 250, nodes = {};
    nodes.hub = { id: 'hub', p: [0, 0, 0], r: 17, col: 'cyan', label: 'MANAGER', big: true };
    nodes.you = { id: 'you', p: [0, -170, 0], r: 10, col: S.approvals.length ? 'red' : 'blue', label: 'YOU', big: true };
    nodes.audit = { id: 'audit', p: [0, 175, 0], r: 8, col: 'slate', label: 'SUPERVISOR', big: true };
    var edges = [['hub', 'you'], ['hub', 'audit']];
    S.departments.forEach(function (d, i) {
      var a = i / Math.max(1, n) * Math.PI * 2, v = CO.deptView(d);
      var id = 'd' + d.id;
      nodes[id] = { id: id, p: [R * Math.cos(a), 0, R * Math.sin(a)], r: 11, col: ST[v.status], label: d.name.toUpperCase(), dept: d.id, big: true };
      edges.push(['hub', id]);
      var m = Math.min(3, v.experts.length);
      v.experts.slice(0, 3).forEach(function (e, j) {
        var da = (j - (m - 1) / 2) * 0.3, R2 = R + 95, y = m > 1 ? (j % 2 ? 42 : -42) : 0;
        var xid = 'x' + d.id + ':' + j;
        nodes[xid] = { id: xid, p: [R2 * Math.cos(a + da), y, R2 * Math.sin(a + da)], r: 6.5, col: e.state === 'working' ? 'cyan' : 'blue', label: e.name, dept: d.id, expert: j };
        edges.push([id, xid]);
      });
    });
    this.nodes = nodes; this.edges = edges;
  };
  Net.prototype.update = function () {
    if (!this.nodes.hub) return this.build();
    var S = CO.S, self = this;
    var ids = S.departments.map(function (d) { return d.id + ':' + d.experts.length; }).join('|');
    if (ids !== this.ids) { this.ids = ids; return this.build(); }
    S.departments.forEach(function (d) {
      var v = CO.deptView(d), n = self.nodes['d' + d.id]; if (!n) return;
      n.col = ST[v.status];
      v.experts.slice(0, 3).forEach(function (e, j) { var x = self.nodes['x' + d.id + ':' + j]; if (x) x.col = e.state === 'working' ? 'cyan' : 'blue'; });
    });
    this.nodes.you.col = S.approvals.length ? 'red' : 'blue';
    this.nodes.hub.col = S.company.status === 'active' ? 'cyan' : 'slate';
  };
  Net.prototype.flow = function (path, colour, delay) {
    var self = this;
    path = path.filter(function (id) { return self.nodes[id]; });
    if (path.length < 2) return;
    this.flows.push({ path: path, col: colour, t0: performance.now() + (delay || 0), hop: 700 });
  };
  Net.prototype.start = function () { this.on = true; this.update(); this.size(); };
  Net.prototype.stop = function () { this.on = false; this.tipHide(); };
  Net.prototype.size = function () {
    var r = this.c.getBoundingClientRect(), dpr = Math.min(2, window.devicePixelRatio || 1);
    this.W = r.width; this.H = r.height;
    this.c.width = Math.round(r.width * dpr); this.c.height = Math.round(r.height * dpr);
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  };
  Net.prototype.zoom = function (f) { this.zoomK = Math.max(0.45, Math.min(2.6, this.zoomK / f)); };
  Net.prototype.fit = function () { this.zoomK = 1; this.pitch = 0.42; };
  Net.prototype.proj = function (p) {
    var cy = Math.cos(this.yaw), sy = Math.sin(this.yaw), cp = Math.cos(this.pitch), sp = Math.sin(this.pitch);
    var x = p[0] * cy - p[2] * sy, z = p[0] * sy + p[2] * cy;
    var y = p[1] * cp - z * sp, z2 = p[1] * sp + z * cp;
    var F = 900, k = F / (F + z2) * this.zoomK * Math.min(this.W / 1000, (this.H - 60) / 640);
    return [this.W / 2 + x * k, 30 + (this.H - 30) * 0.5 + y * k, z2, k];
  };
  Net.prototype.frame = function (now) {
    if (!this.W || this.c.width < 2) this.size();
    var ctx = this.ctx, W = this.W, H = this.H, self = this;
    if (!this.drag) this.yaw += 0.0016;
    ctx.clearRect(0, 0, W, H);
    var g = ctx.createRadialGradient(W / 2, H * 0.52, 10, W / 2, H * 0.52, Math.max(W, H) * 0.7);
    g.addColorStop(0, '#101b2d'); g.addColorStop(1, '#0a0e17');
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    this.stars.forEach(function (s) {
      var q = self.proj(s);
      if (q[2] < -800) return;
      ctx.fillStyle = 'rgba(169,184,204,' + (0.15 + 0.35 * s[3]) * Math.min(1, q[3]) + ')';
      ctx.fillRect(q[0], q[1], 1.3, 1.3);
    });
    // the floor rings
    [250, 345].forEach(function (R, i) {
      ctx.beginPath();
      for (var k = 0; k <= 72; k++) {
        var a = k / 72 * Math.PI * 2, q = self.proj([R * Math.cos(a), 0, R * Math.sin(a)]);
        if (k) ctx.lineTo(q[0], q[1]); else ctx.moveTo(q[0], q[1]);
      }
      ctx.strokeStyle = 'rgba(0,207,255,' + (i ? 0.08 : 0.16) + ')'; ctx.lineWidth = 1; ctx.setLineDash(i ? [3, 6] : []); ctx.stroke(); ctx.setLineDash([]);
    });
    var P = {};
    Object.keys(this.nodes).forEach(function (id) { P[id] = self.proj(self.nodes[id].p); });
    this.P = P;
    // edges, far first
    this.edges.slice().sort(function (a, b) { return (P[b[0]][2] + P[b[1]][2]) - (P[a[0]][2] + P[a[1]][2]); }).forEach(function (e) {
      var a = P[e[0]], b = P[e[1]], n = self.nodes[e[1]], depth = Math.max(0.25, Math.min(1, 1 - (a[2] + b[2]) / 1400));
      var gr = ctx.createLinearGradient(a[0], a[1], b[0], b[1]);
      gr.addColorStop(0, 'rgba(0,207,255,' + 0.35 * depth + ')'); gr.addColorStop(1, 'rgba(' + RGB[n.col] + ',' + 0.55 * depth + ')');
      ctx.strokeStyle = gr; ctx.lineWidth = n.col === 'cyan' ? 1.8 : 1.1;
      ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke();
    });
    // flows
    this.flows = this.flows.filter(function (f) {
      var t = (now - f.t0) / f.hop;
      if (t < 0) return true;
      var hop = Math.floor(t);
      if (hop >= f.path.length - 1) return false;
      var u = t - hop, e = u < 0.5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2;
      var a = P[f.path[hop]], b = P[f.path[hop + 1]]; if (!a || !b) return false;
      for (var i = 5; i >= 0; i--) {
        var ee = Math.max(0, e - i * 0.05), x = a[0] + (b[0] - a[0]) * ee, y = a[1] + (b[1] - a[1]) * ee;
        ctx.fillStyle = 'rgba(' + RGB[f.col] + ',' + (i ? 0.5 - i * 0.08 : 1) + ')';
        ctx.beginPath(); ctx.arc(x, y, i ? 2.4 - i * 0.3 : 3.4, 0, Math.PI * 2); ctx.fill();
      }
      var hx = a[0] + (b[0] - a[0]) * e, hy = a[1] + (b[1] - a[1]) * e, hg = ctx.createRadialGradient(hx, hy, 0, hx, hy, 14);
      hg.addColorStop(0, 'rgba(' + RGB[f.col] + ',.55)'); hg.addColorStop(1, 'rgba(' + RGB[f.col] + ',0)');
      ctx.fillStyle = hg; ctx.beginPath(); ctx.arc(hx, hy, 14, 0, Math.PI * 2); ctx.fill();
      return true;
    });
    // nodes, far first
    Object.keys(this.nodes).sort(function (a, b) { return P[b][2] - P[a][2]; }).forEach(function (id) {
      var n = self.nodes[id], q = P[id], r = n.r * q[3], rgb = RGB[n.col];
      var hg = ctx.createRadialGradient(q[0], q[1], 0, q[0], q[1], r * 3.2);
      hg.addColorStop(0, 'rgba(' + rgb + ',.45)'); hg.addColorStop(1, 'rgba(' + rgb + ',0)');
      ctx.fillStyle = hg; ctx.beginPath(); ctx.arc(q[0], q[1], r * 3.2, 0, Math.PI * 2); ctx.fill();
      var cg = ctx.createRadialGradient(q[0] - r * 0.35, q[1] - r * 0.35, r * 0.1, q[0], q[1], r);
      cg.addColorStop(0, COL.text); cg.addColorStop(0.25, COL[n.col]); cg.addColorStop(1, 'rgba(' + rgb + ',.55)');
      ctx.fillStyle = cg; ctx.beginPath(); ctx.arc(q[0], q[1], r, 0, Math.PI * 2); ctx.fill();
      if (n.col === 'cyan' && id !== 'hub') {
        var ph = (now / 1400) % 1;
        ctx.strokeStyle = 'rgba(0,207,255,' + (1 - ph) * 0.8 + ')'; ctx.lineWidth = 1.4;
        ctx.beginPath(); ctx.arc(q[0], q[1], r * (1.3 + ph * 1.2), 0, Math.PI * 2); ctx.stroke();
      }
      if (id === 'hub') {
        for (var k = 0; k < 2; k++) {
          ctx.strokeStyle = 'rgba(0,207,255,' + (0.5 - k * 0.2) + ')'; ctx.lineWidth = 1.2;
          ctx.beginPath(); ctx.ellipse(q[0], q[1], r * (1.9 + k * 0.7), r * (0.65 + k * 0.25), now / 2600 * (k ? -1 : 1), 0, Math.PI * 2); ctx.stroke();
        }
      }
      if (n.big || self.hover === id) {
        ctx.font = (n.big ? '700 ' + Math.round(10 + 3 * Math.min(1.4, q[3])) + "px 'JetBrains Mono', monospace" : "600 11px 'JetBrains Mono', monospace");
        ctx.textAlign = 'center';
        var label = n.label, ty = q[1] - r - 9;
        var tw = ctx.measureText(label).width + 12;
        ctx.fillStyle = 'rgba(10,14,23,.82)'; ctx.strokeStyle = 'rgba(' + rgb + ',.7)'; ctx.lineWidth = 1;
        roundRect(ctx, q[0] - tw / 2, ty - 13, tw, 18, 5); ctx.fill(); ctx.stroke();
        ctx.fillStyle = COL.text; ctx.fillText(label, q[0], ty);
      }
    });
    ctx.textAlign = 'left';
  };
  function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
  }
  Net.prototype.pick = function (e) {
    if (!this.P) return null;
    var r = this.c.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top, best = null, bd = 1e9, self = this;
    Object.keys(this.nodes).forEach(function (id) {
      var q = self.P[id], n = self.nodes[id], d = Math.hypot(q[0] - x, q[1] - y);
      if (d < Math.max(10, n.r * q[3] + 6) && d < bd) { bd = d; best = id; }
    });
    return best;
  };
  Net.prototype.bind = function () {
    var self = this, c = this.c;
    c.addEventListener('pointerdown', function (e) { self.drag = { x: e.clientX, y: e.clientY, yaw: self.yaw, pitch: self.pitch, moved: false }; });
    window.addEventListener('pointermove', function (e) {
      if (!self.on) return;
      if (self.drag) {
        var dx = e.clientX - self.drag.x, dy = e.clientY - self.drag.y;
        if (Math.abs(dx) + Math.abs(dy) > 3) self.drag.moved = true;
        self.yaw = self.drag.yaw + dx * 0.006; self.pitch = Math.max(-0.2, Math.min(1.2, self.drag.pitch + dy * 0.004));
        return;
      }
      if (e.target !== c) return;
      var id = self.pick(e);
      self.hover = id; c.style.cursor = id ? 'pointer' : 'grab';
      if (!id) return self.tipHide();
      var n = self.nodes[id], key = n.expert != null ? 'd' + n.dept + ':' + n.expert : id;
      var html = self.tipFor(n.expert != null ? 'agent' : 'room', key);
      var tip = self.stage.querySelector('.tip'), r = self.stage.getBoundingClientRect();
      tip.innerHTML = html; tip.hidden = !html;
      tip.style.left = Math.min(r.width - tip.offsetWidth - 8, e.clientX - r.left + 14) + 'px';
      tip.style.top = Math.min(r.height - tip.offsetHeight - 8, e.clientY - r.top + 14) + 'px';
    });
    window.addEventListener('pointerup', function (e) {
      if (!self.drag) return;
      var was = self.drag; self.drag = null;
      if (was.moved || !self.on) return;
      var id = self.pick(e); if (!id) return;
      var n = self.nodes[id];
      CO.emit('office:click', n.dept ? 'd' + n.dept : id);
    });
    c.addEventListener('wheel', function (e) { e.preventDefault(); self.zoom(Math.pow(1.0018, e.deltaY)); }, { passive: false });
    c.addEventListener('pointerleave', function () { self.hover = null; self.tipHide(); });
    window.addEventListener('resize', function () { if (self.on) self.size(); });
  };
  Net.prototype.tipHide = function () { var t = this.stage.querySelector('.tip'); if (t) t.hidden = true; };
})();

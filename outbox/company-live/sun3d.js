/* Cymetica's sun, turning slowly on its own axis (the operator, 2026-10-20: "at se to slunce toci pomalicku kolem sve
 * osy. a ne ze se v loadingu toci jak hodinove rucicky"): the painting's glow, beams and sparks stay still
 * (sun-glow.webp: CO.colliderPaint without its arcs), and its arcs of plasma are rings of light set in 3D round the
 * ball, turning together about its tilted axis -- a CSS 3D scene, so it keeps turning on the compositor while the page
 * builds its 3D on the main thread. One look for the loaders, the landing and the Universe; boot.css styles it.
 * SUN3D.fill(el) puts it in el (any square box: the ball is the middle 0.6 of it, as the painting's). */
(function () {
  'use strict';
  function rng(s) { return function () { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; }
  // the painting's colours: gold most, orange, blue and white between; pink, violet and deep blue inside
  var GOLD = ['255,150,36', '255,178,70', '255,112,18', '255,196,96', '255,150,36'], BLUE = ['60,130,255', '96,160,255', '150,200,255'],
    DEEP = ['255,84,180', '150,84,255', '60,110,255', '255,100,60'];
  var HTML = null;
  function arcs() {
    if (HTML) return HTML;
    var R = rng(20261020), out = '', i;
    // d: the ring's diameter as a share of the box (the ball is 60 %), w its line, al how much of the ring is lit
    var one = function (d, cols, w, al, a) {
      out += '<b style="--d:' + d.toFixed(1) + '%;--ry:' + (R() * 360).toFixed(0) + 'deg;--rx:' + (R() * 180 - 90).toFixed(0) + 'deg;--rz:' + (R() * 360).toFixed(0) +
        'deg;--a0:' + (R() * 360).toFixed(0) + 'deg;--al:' + al.toFixed(0) + 'deg;--w:' + w.toFixed(1) + 'px;--c:rgba(' + cols[Math.floor(R() * cols.length)] + ',' + a.toFixed(2) + ')"></b>';
    };
    // on its shell, the arcs that draw its round edge; through it, gold and blue loops; inside, swirls round the heart
    for (i = 0; i < 44; i++) one(52 + R() * 10, R() < 0.6 ? GOLD : BLUE, 1.6 + R() * 1.6, 70 + R() * 160, 0.75 + R() * 0.25);
    for (i = 0; i < 14; i++) one(30 + R() * 22, R() < 0.5 ? GOLD : BLUE, 1.4 + R() * 1.4, 90 + R() * 150, 0.6 + R() * 0.3);
    for (i = 0; i < 12; i++) one(10 + R() * 18, DEEP, 1.4 + R() * 1.2, 120 + R() * 160, 0.55 + R() * 0.3);
    return (HTML = out);
  }
  // The big sun (the Universe's, the landing's): the painting's own arcs (CO.colliderArcs, universe.js), turned on the
  // ball's tilted axis and drawn again a few times a second -- the same weave, colours and density as the painting,
  // now turning like a globe. The still part (heart, rim, beams, spikes, sparks) is painted once under them.
  var TILT_X = -0.28, TILT_Z = 0.17, TURN = 2 * Math.PI / 120000;   // a turn in two minutes
  function live(el, seed) {
    if (!el || !window.CO || !CO.colliderArcs) return null;
    var A = CO.colliderArcs(seed || 1), still = CO.colliderPaint(seed || 1, 'still'), W = A.size, c = W / 2;
    var st = document.createElement('canvas'); st.width = st.height = W; st.getContext('2d').drawImage(still, 0, 0); st.className = 'l1 s3still';
    var cv = document.createElement('canvas'); cv.width = cv.height = W; cv.className = 'l2 s3live';
    el.appendChild(st); el.appendChild(cv);
    var g = cv.getContext('2d'), cx = Math.cos(TILT_X), sx = Math.sin(TILT_X), cz = Math.cos(TILT_Z), sz = Math.sin(TILT_Z);
    var last = -1, t0 = performance.now(), raf = 0;
    function draw(now) {
      raf = requestAnimationFrame(draw);
      // a few times a second is enough for a turn this slow; nothing while hidden
      if (now - last < 66 || document.hidden || !el.isConnected || el.offsetParent === null) return;
      last = now;
      var th = (now - t0) * TURN, ct = Math.cos(th), s = Math.sin(th);
      g.clearRect(0, 0, W, W); g.globalCompositeOperation = 'lighter'; g.lineCap = 'round';
      for (var i = 0; i < A.arcs.length; i++) {
        var a = A.arcs[i], P = a.pts, q = [];
        for (var k = 0; k < P.length; k++) {
          // turn about the ball's own (vertical) axis, then tilt that axis toward the viewer and to the side
          var x = P[k][0] * ct + P[k][2] * s, y = P[k][1], z = -P[k][0] * s + P[k][2] * ct;
          var y2 = y * cx - z * sx, z2 = y * sx + z * cx, x3 = x * cz - y2 * sz, y3 = x * sz + y2 * cz;
          q.push([c + x3, c - y3, Math.max(-1, Math.min(1, z2 / A.rad))]);
        }
        for (var m = 0; m < 4; m++) {
          var a0 = m * 12, a1 = a0 + 12, b = (0.3 + 0.7 * ((q[a0][2] + q[a1][2]) / 2 + 1) / 2) * a.dim;
          for (var L = 0; L < 2; L++) {
            g.strokeStyle = 'rgba(' + a.col.join(',') + ',' + (L ? 0.92 * b : 0.06 * b).toFixed(3) + ')'; g.lineWidth = L ? a.w : a.w * 3.2;
            g.beginPath(); g.moveTo(q[a0][0], q[a0][1]); for (var n = a0 + 1; n <= a1; n++) g.lineTo(q[n][0], q[n][1]); g.stroke();
          }
        }
      }
    }
    raf = requestAnimationFrame(draw);
    return { stop: function () { cancelAnimationFrame(raf); } };
  }
  window.SUN3D = {
    fill: function (el) {
      if (!el || el.querySelector('.s3')) return el;
      el.insertAdjacentHTML('beforeend', '<div class="s3"><i class="s3g"></i><div class="s3t"><div class="s3w">' + arcs() + '</div></div></div>');
      return el;
    },
    live: live
  };
})();

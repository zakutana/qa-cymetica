/* A stand-in for their WebSocket: plays recorded frames from /_mock/frames, nothing live. */
(function () {
  'use strict';
  var pageQ = new URLSearchParams(location.search);
  var frozen = pageQ.get('frozen') === '1';
  var cache = {};

  function qs(p) {
    var u = new URLSearchParams();
    if (p.contract) { u.set('contract', p.contract); if (p.chain) u.set('chain', p.chain); }
    else if (p.symbol) u.set('symbol', p.symbol);
    u.set('tf', p.tf || p.timeframe || '1d');
    if (frozen || p.frozen) u.set('frozen', '1');
    if (p.chip) u.set('chip', '1');
    return u.toString();
  }

  // frames of one coin and timeframe, cached in memory per key
  window.czaMockFrames = function (p) {
    var q = qs(p);
    if (!cache[q]) {
      cache[q] = fetch('/_mock/frames?' + q).then(function (r) {
        if (!r.ok) throw new Error('frames ' + r.status);
        return r.json();
      }).then(function (rec) {           // "still collecting" is not kept: the page asks again in 30 s
        if ((rec.frames || []).some(function (f) { return f.type === 'error' && /^(COLLECTING|UPSTREAM_UNAVAILABLE|BUSY)$/.test(f.code); })) delete cache[q];
        return rec;
      }).catch(function (e) { delete cache[q]; throw e; });
    }
    return cache[q];
  };

  function MockSocket() {
    var self = this;
    self.readyState = 0;
    self.onopen = self.onmessage = self.onclose = self.onerror = null;
    self._run = 0;
    setTimeout(function () {
      if (self.readyState !== 0) return;
      self.readyState = 1;
      if (self.onopen) self.onopen({ type: 'open' });
    }, 10);
  }
  MockSocket.CONNECTING = 0; MockSocket.OPEN = 1; MockSocket.CLOSING = 2; MockSocket.CLOSED = 3;

  MockSocket.prototype.send = function (text) {
    var self = this, m;
    try { m = JSON.parse(text); } catch (e) { return; }
    if (m.op === 'unsubscribe') { self._run++; return; }
    if (m.op !== 'subscribe') return;
    var run = ++self._run;
    window.czaMockFrames({ contract: m.contract, chain: m.chain, symbol: m.symbol, tf: m.timeframe }).then(function (rec) {
      var i = 0;
      (function next() {
        if (run !== self._run || self.readyState !== 1) return;
        if (i >= rec.frames.length) return;
        var f = rec.frames[i++];
        if (self.onmessage) self.onmessage({ data: JSON.stringify(f) });
        setTimeout(next, 30);
      })();
    }).catch(function () {
      if (run === self._run && self.onmessage) self.onmessage({ data: JSON.stringify({ type: 'error', code: 'BUSY', message: 'Mock: no recorded frames for this coin and timeframe.' }) });
    });
  };

  MockSocket.prototype.close = function () {
    if (this.readyState === 3) return;
    this._run++;
    this.readyState = 3;
    var self = this;
    setTimeout(function () { if (self.onclose) self.onclose({ type: 'close', code: 1000 }); }, 0);
  };

  window.czaMockSocket = MockSocket;
})();

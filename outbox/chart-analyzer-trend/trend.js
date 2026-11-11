/* Trend helpers for the Chart Analyzer: flip line, 9-13 count, aggregation, plain-English sentence.
   Pure functions, no DOM. Rows are [t, o, h, l, c, v], oldest first, t in unix seconds (ms also accepted). */
(function () {
  var api = {};
  api.N = 10;
  api.K = 3;
  api.MIN = 15;

  // ---- helpers ----
  function isMs(t) { return t > 1e11; }
  function toSec(t) { return isMs(t) ? t / 1000 : t; }
  function fromSec(sec, like) { return isMs(like) ? sec * 1000 : sec; }

  // ---- ATR (Wilder). null until index n-1 ----
  api.atr = function (rows, n) {
    var out = [], tr = [], i, s, prev;
    for (i = 0; i < rows.length; i++) {
      var h = rows[i][2], l = rows[i][3];
      if (i === 0) {
        tr.push(h - l);
      } else {
        var pc = rows[i - 1][4];
        tr.push(Math.max(h - l, Math.abs(h - pc), Math.abs(l - pc)));
      }
      if (i < n - 1) {
        out.push(null);
      } else if (i === n - 1) {
        s = 0;
        for (var j = 0; j < n; j++) s += tr[j];
        prev = s / n;
        out.push(prev);
      } else {
        prev = (prev * (n - 1) + tr[i]) / n;
        out.push(prev);
      }
    }
    return out;
  };

  function closedRows(rows, opts) {
    return opts && opts.forming ? rows.slice(0, rows.length - 1) : rows.slice();
  }

  // ---- flip line (ATR trailing line on closed candles) ----
  api.flipLine = function (rows, opts) {
    var closed = closedRows(rows, opts);
    var forming = !!(opts && opts.forming);
    if (closed.length < api.MIN) return { ok: false, have: closed.length, need: api.MIN };
    var N = api.N, K = api.K;
    var atr = api.atr(closed, N);
    var line = [], sides = [], flips = [], i, side, cur;
    for (i = 0; i < closed.length; i++) { line.push(null); sides.push(null); }
    var sum = 0;
    for (i = 0; i < N; i++) sum += closed[i][4];
    for (i = N - 1; i < closed.length; i++) {
      var mid = (closed[i][2] + closed[i][3]) / 2;
      var lower = mid - K * atr[i], upper = mid + K * atr[i];
      var c = closed[i][4];
      if (i === N - 1) {
        side = c >= sum / N ? 'bull' : 'bear';
        cur = side === 'bull' ? lower : upper;
      } else if (side === 'bull') {
        if (c < cur) {
          side = 'bear'; cur = upper;
          flips.push({ i: i, t: closed[i][0], side: side, close: c });
        } else cur = Math.max(lower, cur);
      } else {
        if (c > cur) {
          side = 'bull'; cur = lower;
          flips.push({ i: i, t: closed[i][0], side: side, close: c });
        } else cur = Math.min(upper, cur);
      }
      line[i] = cur; sides[i] = side;
    }
    var last = closed.length - 1;
    var flip = line[last], a = atr[last];
    var price = rows[rows.length - 1][4];
    var distPct = Math.abs(price - flip) / price * 100;
    var distAtr = Math.abs(price - flip) / a;
    var word = distAtr < 1 ? 'AT THE EDGE' : (distAtr < 2.5 ? 'CLOSE' : 'ROOM');
    var lf = flips.length ? flips[flips.length - 1] : null;
    var breaking = forming && ((side === 'bull' && price < flip) || (side === 'bear' && price > flip));
    return {
      ok: true, side: side, line: line, sides: sides, flips: flips,
      flip: flip, atr: a, price: price, dist_pct: distPct, dist_atr: distAtr, word: word,
      last_flip: lf ? { i: lf.i, t: lf.t, close: lf.close } : null,
      since_flip_pct: lf ? (price - lf.close) / lf.close * 100 : null,
      candles_since_flip: lf ? last - lf.i : null,
      breaking: breaking
    };
  };

  // ---- 9-13 count (setup 9, countdown 13) on closed candles ----
  api.count913 = function (rows, opts) {
    var closed = closedRows(rows, opts);
    var marks = [], last9 = null, last13 = null;
    var upN = 0, dnN = 0;          // running setup counts
    var cd = null;                 // alive countdown {dir, n}
    var nowDir = null, nowN = 0;
    var i;
    for (i = 4; i < closed.length; i++) {
      var c = closed[i][4], c4 = closed[i - 4][4];
      var dir = null, n = 0, finished = false;
      if (c > c4) { upN += 1; dnN = 0; dir = 'up'; n = upN; }
      else if (c < c4) { dnN += 1; upN = 0; dir = 'down'; n = dnN; }
      else { upN = 0; dnN = 0; }
      if (dir) {
        marks.push({ i: i, t: closed[i][0], kind: 'setup', dir: dir, n: n });
        if (n === 9) {
          finished = true;
          last9 = { i: i, t: closed[i][0], dir: dir };
          upN = 0; dnN = 0;
        }
      }
      nowDir = dir; nowN = n;
      // a finished setup starts a countdown unless one of the same direction is running
      if (finished && i >= 2 && (!cd || cd.dir !== dir)) cd = { dir: dir, n: 0 };
      if (cd && i >= 2) {
        var ok = cd.dir === 'up' ? c >= closed[i - 2][2] : c <= closed[i - 2][3];
        if (ok) {
          cd.n += 1;
          marks.push({ i: i, t: closed[i][0], kind: 'countdown', dir: cd.dir, n: cd.n });
          if (cd.n === 13) {
            last13 = { i: i, t: closed[i][0], dir: cd.dir };
            cd = null;
          }
        }
      }
    }
    var lastIdx = closed.length - 1;
    function withAgo(x) { return x ? { i: x.i, t: x.t, dir: x.dir, ago: lastIdx - x.i } : null; }
    return {
      marks: marks,
      now: { dir: nowN ? nowDir : null, n: nowN },
      countdown: cd ? { dir: cd.dir, n: cd.n } : null,
      last9: withAgo(last9),
      last13: withAgo(last13)
    };
  };

  // ---- aggregation ----
  function merge(group, t) {
    var h = -Infinity, l = Infinity, v = 0, k;
    for (k = 0; k < group.length; k++) {
      if (group[k][2] > h) h = group[k][2];
      if (group[k][3] < l) l = group[k][3];
      v += group[k][5] || 0;
    }
    return [t, group[0][1], h, l, group[group.length - 1][4], v];
  }

  function groupBy(rows, keyFn, tFn) {
    var out = [], cur = null, key = null, i;
    for (i = 0; i < rows.length; i++) {
      var k = keyFn(rows[i][0]);
      if (cur === null || k !== key) {
        if (cur) out.push(merge(cur, tFn(key, cur[0][0])));
        cur = []; key = k;
      }
      cur.push(rows[i]);
    }
    if (cur) out.push(merge(cur, tFn(key, cur[0][0])));
    return out;
  }

  // weeks start Monday 00:00 UTC
  api.toWeeks = function (rows) {
    return groupBy(rows, function (t) {
      var day = Math.floor(toSec(t) / 86400);
      return day - ((day + 3) % 7 + 7) % 7;      // 1970-01-01 was a Thursday
    }, function (key, like) { return fromSec(key * 86400, like); });
  };

  api.toBlocks = function (rows, k) {
    var out = [], i;
    for (i = 0; i < rows.length; i += k) {
      var g = rows.slice(i, i + k);
      out.push(merge(g, g[0][0]));
    }
    return out;
  };

  // group by floor(t / seconds); t is the bucket start
  api.toBuckets = function (rows, seconds) {
    return groupBy(rows, function (t) { return Math.floor(toSec(t) / seconds); },
      function (key, like) { return fromSec(key * seconds, like); });
  };

  // calendar months UTC
  api.toMonths = function (rows) {
    return groupBy(rows, function (t) {
      var d = new Date(toSec(t) * 1000);
      return d.getUTCFullYear() * 12 + d.getUTCMonth();
    }, function (key, like) {
      return fromSec(Date.UTC(Math.floor(key / 12), key % 12, 1) / 1000, like);
    });
  };

  // ---- price format ----
  api.fmt = function (p) {
    var a = Math.abs(p);
    if (a >= 1000) return Math.round(p).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    if (a >= 1) return p.toFixed(2);
    if (a >= 0.01) return p.toFixed(4);
    if (a === 0) return '0';
    return String(Number(p.toPrecision(4)).toFixed(Math.max(0, 3 - Math.floor(Math.log10(a)))));
  };

  // ---- plain-English sentences ----
  function pct(x) { return x.toFixed(1); }

  api.sentence = function (trend, count, tfWord, align) {
    var out = [], bull = trend.side === 'bull', f = api.fmt(trend.flip);
    if (trend.breaking) {
      out.push('Price is through the flip at ' + f + '. A ' + tfWord + ' close there ends the ' + trend.side + ' trend.');
    } else if (trend.word === 'AT THE EDGE') {
      out.push(bull
        ? 'Bull trend, but only ' + pct(trend.dist_pct) + '% above the flip. Lose ' + f + ' on a ' + tfWord + ' close and it is over.'
        : 'Bear trend, but only ' + pct(trend.dist_pct) + '% under the flip. A ' + tfWord + ' close above ' + f + ' turns it.');
    } else {
      out.push(bull
        ? 'Bull trend on the ' + tfWord + '. It holds while candles close above ' + f + '.'
        : 'Bear trend on the ' + tfWord + '. No long until a close above ' + f + '.');
    }
    // second sentence
    var want = bull ? 'up' : 'down', pick = null;
    if (count) {
      var a = count.last9, b = count.last13;
      if (b && b.dir === want && b.ago <= 2) pick = '13';
      else if (a && a.dir === want && a.ago <= 2) pick = '9';
    }
    if (pick) {
      out.push('A ' + pick + ' just printed: ' + (bull ? 'rallies' : 'sell-offs') + ' often pause here.');
    } else if (align && align.total > 0) {
      var mine = bull ? align.bull : align.bear, other = bull ? align.bear : align.bull;
      if (mine === align.total) out.push('Every timeframe agrees.');
      else if (other > mine) out.push(bull ? 'Other timeframes disagree, so treat it as a bounce.'
                                           : 'Other timeframes disagree, so treat rallies as bounces.');
    }
    return out;
  };

  if (typeof module !== 'undefined') module.exports = api;
  if (typeof window !== 'undefined') window.czaTrendCalc = api;
})();

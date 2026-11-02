
  // ---- The request on the Supply Analyzer page itself. Goes inside their script, before boot(). The same one pie as the Gem Screener's
  // card, from the same record; the source named on Next unlock. Their socket is not proxied, so the record comes from their analyze GET.
  var MOCK = window.SA_MOCK || {sources: {}, finished: {}, dropstab: {}, read: ''};
  subscribe = function (push) {
    try { history[push ? 'pushState' : 'replaceState'](null, '', urlFor()); } catch (e) {}
    state.rec = null; state.idx = 0; state.series = null;
    showState('Reading the sources', 'Supply, schedule, staking and buybacks are read from public feeds and the project\'s own pages. A token read before opens at once.');
    var q = state.contract ? 'contract=' + encodeURIComponent(state.contract) + (state.chain ? '&chain=' + encodeURIComponent(state.chain) : '') : 'symbol=' + encodeURIComponent(state.sym);
    fetch('/api/v1/supply-analyzer/analyze?' + q, {credentials: 'omit'})
      .then(function (r) { return r.json(); })
      .then(function (m) {
        if (state.view === 'start') return;
        live('on', 'live · last read ' + String(m.refreshed_at || '').slice(0, 10));
        render(m);
      })
      .catch(function () { showProblem({code: 'UNKNOWN', title: 'Not read', message: 'The copy could not read this token.'}); });
  };

  function partsOf(rec) {
    var T = rec.tiles || {}, c = T.circulating || {}, d = T.dilution_12m, sl = {};
    (rec.slices_today || []).forEach(function (x) { sl[x.key] = x.amount || 0; });
    var out = c.tokens || (sl.free || 0) + (sl.staked_free || 0) + (sl.staked_locked || 0);
    var staked = Math.min((sl.staked_free || 0) + (sl.staked_locked || 0), out), kept = Math.min(sl.bb_kept || 0, out - staked), whole = c.of;
    var slug = (rec.token || {}).slug, parts = [
      {label: (rec.unknown_names || []).indexOf('staking') >= 0 ? 'In circulation' : 'Free to sell', v: out - staked - kept, c: '#00cfff'},
      {label: 'Staked', v: staked, c: '#3b82f6'},
      {label: 'Bought back, kept', v: kept, c: '#00ff88'}
    ].filter(function (p) { return p.v > 0; });
    if (!whole || whole <= out * 1.001) return {parts: parts, open: !whole};
    var rest = whole - out;
    if (d && typeof d.pct === 'number') {
      var soon = Math.min(d.new_tokens_12m || 0, rest);
      if (soon > 0) parts.push({label: 'Coming in 12 months', v: soon, c: '#ff4444'});
      if (rest - soon > 0) parts.push({label: 'After that, or never issued', v: rest - soon, c: '#2a3648'});
    } else {
      parts.push({label: MOCK.finished[slug] ? 'Not out, schedule finished' : 'Not out yet, no schedule', v: rest, c: '#7f93ad', dashed: true});
    }
    return {parts: parts, open: false};
  }
  function pieTile(rec) {
    var T = rec.tiles || {}, c = T.circulating || {}, f = T.fdv, d = T.dilution_12m, slug = (rec.token || {}).slug, sym = (rec.token || {}).symbol || '';
    var P = partsOf(rec), total = P.parts.reduce(function (n, p) { return n + p.v; }, 0), R = 44, C = 2 * Math.PI * R, at = 0;
    var arcs = P.parts.map(function (p) {
      var len = C * p.v / total, gap = P.parts.length > 1 ? Math.min(1.5, len / 3) : 0;
      var dash = p.dashed ? 'style="stroke-dasharray:3 3;opacity:.55"' : 'stroke-dasharray="' + (len - gap).toFixed(2) + ' ' + (C - len + gap).toFixed(2) + '"';
      var arc = '<circle cx="60" cy="60" r="' + R + '" fill="none" stroke="' + p.c + '" stroke-width="15" ' + dash + ' stroke-dashoffset="' + (-at).toFixed(2) + '"/>';
      at += len;
      return arc;
    }).join('');
    var rows = P.parts.map(function (p) {
      return '<li><i style="background:' + p.c + (p.dashed ? ';opacity:.55' : '') + '"></i><span>' + p.label + '</span><b>' + tok(p.v) + '</b></li>';
    }).join('');
    var pctOut = typeof c.pct === 'number' ? (c.pct >= 99.95 ? '100%' : c.pct.toFixed(1) + '%') : '–';
    var fdv = f && f.market_cap_usd && f.fdv_usd ? '<div class="sa-fdv"><span>Market cap</span><b>' + usd(f.market_cap_usd) + '</b><span>FDV</span><b class="' + (f.x >= 3 ? 'v-bad' : f.x <= 1.5 ? 'v-good' : '') + '">' + usd(f.fdv_usd) + (typeof f.x === 'number' ? ' · ' + f.x.toFixed(1) + '×' : '') + '</b></div>' : '';
    var done = MOCK.finished[slug], drop = MOCK.dropstab[slug], tbd = rec.unlocks_tbd, say = '', num = 'n/a', cls = 'v-na';
    if (d && typeof d.pct === 'number') {
      num = d.at_max ? '0%' : pct(d.pct, true);
      cls = d.pct >= 25 ? 'v-bad' : d.pct < 5 ? 'v-good' : 'v-caution';
      say = d.at_max ? 'Max supply is reached.' : tok(d.month_tokens) + ' new ' + sym + ' a month' + ((d.kinds || []).length ? ' · ' + d.kinds.join(' + ') : '') + (d.source ? ', to ' + d.until + '. Source: ' + d.source + ', read ' + MOCK.read + '.' : '');
    } else if (done) {
      say = 'The published schedule finished in ' + done + '.';
    } else if (drop) {
      say = 'Schedule found on DropsTab; the figure comes with the build.';
    } else {
      say = 'No schedule found on DeFiLlama, the project’s vesting contracts, Tokenomist and DropsTab. Nothing is assumed.';
    }
    var tile = el('div', 'sa-tile sa-pie sa-wide sa-on-page');
    tile.setAttribute('data-k', 'circ');
    tile.innerHTML = '<div class="sa-tk">Circulating, FDV, dilution</div><div class="sa-wrap"><div class="sa-ringbox"><svg viewBox="0 0 120 120" role="img">' + arcs + '</svg><div class="sa-center"><b>' + pctOut + '</b><span>is out</span></div></div>' +
      '<div class="sa-side"><ul class="sa-legend">' + rows + '</ul>' + fdv + '<div class="sa-fdv"><span>Dilution, 12 months</span><b class="' + cls + '">' + num + '</b></div><p class="sa-note">' + say + '</p>' +
      (P.open ? '<p class="sa-note">No max supply: what is still to come cannot be drawn.</p>' : '') + '</div></div>';
    return tile;
  }
  var tilesAsServed = renderTiles;
  renderTiles = function (rec) {
    tilesAsServed(rec);
    var box = $('saTiles'), first = box.querySelector('[data-k="circ"]');
    if (first) box.replaceChild(pieTile(rec), first);
    ['fdv', 'dil'].forEach(function (k) { var t = box.querySelector('[data-k="' + k + '"]'); if (t) t.remove(); });
    box.classList.remove('sa-n2', 'sa-n3');
    box.classList.add('sa-n' + box.children.length);
    box.removeAttribute('data-n');
    // the month chart below can't be redrawn here without the whole schedule: it says what the build does instead of "no schedule"
    var found = ((rec.tiles || {}).dilution_12m || {}).source;
    if (found) setTimeout(function () {
      [].slice.call(document.querySelectorAll('.sa-out *')).forEach(function (n) {
        if (n.children.length) return;
        if (/No schedule published: no vesting schedule/.test(n.textContent)) n.textContent = 'Schedule from ' + found + ': with the build, the months ahead are drawn from it.';
        else if (/no schedule published/i.test(n.textContent)) n.textContent = n.textContent.replace(/\s*[·-]?\s*no schedule published/i, ' · schedule from ' + found);
      });
    }, 0);
  };
  var nextAsServed = renderNext;
  renderNext = function (rec) {
    var T = rec.tiles || {}, nu = T.next_unlock_row || {}, slug = (rec.token || {}).slug;
    if (nu.kind === 'unknown') {
      var done = MOCK.finished[slug], drop = MOCK.dropstab[slug];
      nu.why = done ? 'The published schedule finished in ' + done + '.' : drop ? 'Schedule found on DropsTab; the figure comes with the build.' : 'No schedule found on DeFiLlama, the project’s vesting contracts, Tokenomist and DropsTab. Nothing is assumed.';
    }
    nextAsServed(rec);
    if (nu.source) $('saNext').appendChild(el('div', 'sa-src', 'Source: ' + nu.source + ', read ' + MOCK.read));
    if (nu.kind === 'unknown') {
      var line = [].slice.call($('saNext').querySelectorAll('*')).filter(function (n) { return !n.children.length && /No vesting or unlock schedule/.test(n.textContent); })[0];
      if (line) line.textContent = nu.why;
    }
  };

/* The marks of the products Build it Better has built, for step 2's ring of holograms ("od kazde apky spis jeji logo
   nez ten screen"). Gem Screener's is its own (cymetica.com/static/gem-screener/gem-screener-icon.svg, pics/logos/);
   every other product has no logo of its own yet (their pages carry the site's favicon), so each is drawn here, one
   shape a product, in the site's colours. Our drawings, not theirs: the README says which is which. */
(function () {
  'use strict';
  var G = '<defs><linearGradient id="lg-$" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#00cfff"/><stop offset="1" stop-color="#00ff88"/></linearGradient></defs>';
  function mark(id, body) { return '<svg viewBox="0 0 64 64" aria-hidden="true">' + G.replace('$', id) + body.replace(/URL/g, 'url(#lg-' + id + ')') + '</svg>'; }
  window.QUEST_LOGO = {
    'gem-screener': '<img src="pics/logos/gem-screener.svg" alt="">',
    'chart-analyzer': mark('ca', '<path d="M18 14v36 M32 10v44 M46 18v30" stroke="#a9e8ff" stroke-width="2.4" stroke-linecap="round"/>' +
      '<rect x="12" y="22" width="12" height="18" rx="2.5" fill="#00ff88"/><rect x="26" y="30" width="12" height="16" rx="2.5" fill="#ff4444"/><rect x="40" y="22" width="12" height="20" rx="2.5" fill="#00ff88"/>'),
    'agent-casino': mark('ac', '<circle cx="32" cy="32" r="24" fill="none" stroke="URL" stroke-width="6"/>' +
      '<path d="M32 4v8 M32 52v8 M4 32h8 M52 32h8 M12.2 12.2l5.7 5.7 M46.1 46.1l5.7 5.7 M12.2 51.8l5.7-5.7 M46.1 17.9l5.7-5.7" stroke="#e8fbff" stroke-width="3.4" stroke-linecap="round"/>' +
      '<rect x="22" y="23" width="20" height="17" rx="5" fill="#0d1520" stroke="#00cfff" stroke-width="2.4"/><circle cx="28" cy="31.5" r="2.4" fill="#00ff88"/><circle cx="36" cy="31.5" r="2.4" fill="#00ff88"/><path d="M32 23v-5" stroke="#00cfff" stroke-width="2.4" stroke-linecap="round"/>'),
    'supply-analyzer': mark('sa', '<circle cx="32" cy="32" r="21" fill="none" stroke="#1e3050" stroke-width="10"/>' +
      '<path d="M32 11a21 21 0 0 1 20.2 15.3" fill="none" stroke="#00ff88" stroke-width="10"/><path d="M52.2 26.3A21 21 0 0 1 22 50.5" fill="none" stroke="#00cfff" stroke-width="10"/><path d="M22 50.5A21 21 0 0 1 32 11" fill="none" stroke="#3b82f6" stroke-width="10" opacity=".85"/><circle cx="32" cy="32" r="5" fill="#e8fbff"/>'),
    'crypto': mark('cd', '<rect x="9" y="9" width="21" height="21" rx="5" fill="URL"/><rect x="34" y="9" width="21" height="21" rx="5" fill="none" stroke="#00cfff" stroke-width="3"/>' +
      '<rect x="9" y="34" width="21" height="21" rx="5" fill="none" stroke="#00cfff" stroke-width="3"/><path d="M37 50l5-7 4 4 7-10" fill="none" stroke="#00ff88" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/>'),
    'ai-marketplace': mark('am', '<path d="M14 22h36l-3.4 30H17.4Z" fill="none" stroke="URL" stroke-width="3.6" stroke-linejoin="round"/><path d="M23 22v-4a9 9 0 0 1 18 0v4" fill="none" stroke="#00cfff" stroke-width="3.4" stroke-linecap="round"/>' +
      '<path d="M32 30l2.6 6.4L41 39l-6.4 2.6L32 48l-2.6-6.4L23 39l6.4-2.6Z" fill="#00ff88"/>'),
    'tradingview': mark('tv', '<path d="M8 50h48" stroke="#1e3050" stroke-width="3" stroke-linecap="round"/><path d="M8 44l12-13 9 7 13-18 14 8V50H8Z" fill="URL" opacity=".28"/>' +
      '<path d="M8 44l12-13 9 7 13-18 14 8" fill="none" stroke="URL" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/><circle cx="42" cy="20" r="4.4" fill="#e8fbff"/>'),
    'weekly-signal': mark('ws', '<path d="M32 30v26 M24 56h16" stroke="#e8fbff" stroke-width="3.4" stroke-linecap="round"/><circle cx="32" cy="26" r="5" fill="#00ff88"/>' +
      '<path d="M22 16a14 14 0 0 0 0 20 M42 16a14 14 0 0 1 0 20" fill="none" stroke="#00cfff" stroke-width="3.4" stroke-linecap="round"/><path d="M14 9a24 24 0 0 0 0 34 M50 9a24 24 0 0 1 0 34" fill="none" stroke="URL" stroke-width="3.4" stroke-linecap="round" opacity=".8"/>'),
    'team-dump-radar': mark('tr', '<circle cx="32" cy="32" r="24" fill="none" stroke="#1e3050" stroke-width="3"/><circle cx="32" cy="32" r="15" fill="none" stroke="#1e3050" stroke-width="3"/>' +
      '<path d="M32 32L52 18A24 24 0 0 1 55.4 36Z" fill="URL" opacity=".55"/><path d="M32 32L52 18" stroke="#00ff88" stroke-width="3.2" stroke-linecap="round"/><circle cx="44" cy="40" r="4.2" fill="#ff4444"/><circle cx="32" cy="32" r="3.4" fill="#e8fbff"/>'),
    'airdrop-farmer': mark('af', '<path d="M30 14c-1-4 1-7 4-8 0 3-1 6-4 8Z M30 14c-3-2-7-2-9 0 3 2 6 2 9 0Z" fill="#00ff88"/>' +
      '<path d="M8 27c8-4 40-4 48 0" fill="none" stroke="#00ff88" stroke-width="4" stroke-linecap="round"/><path d="M19 26c1-7 6-11 13-11s12 4 13 11" fill="#0b3a2c" stroke="#00ff88" stroke-width="3"/>' +
      '<circle cx="32" cy="40" r="15" fill="#0d1520" stroke="URL" stroke-width="3.4"/><rect x="24.5" y="35" width="5.5" height="9" rx="2.75" fill="#00ff88"/><rect x="34" y="35" width="5.5" height="9" rx="2.75" fill="#00ff88"/>'),
    'events': mark('ev', '<rect x="9" y="13" width="46" height="42" rx="7" fill="none" stroke="URL" stroke-width="3.6"/><path d="M9 25h46 M21 8v10 M43 8v10" stroke="#00cfff" stroke-width="3.6" stroke-linecap="round"/>' +
      '<path d="M32 30l3.4 7 7.6 1.1-5.5 5.4 1.3 7.6L32 47.5l-6.8 3.6 1.3-7.6-5.5-5.4 7.6-1.1Z" fill="#00ff88"/>'),
    'infiltrator': mark('in', '<path d="M32 5l23.4 13.5v27L32 59 8.6 45.5v-27Z" fill="none" stroke="URL" stroke-width="3.4" stroke-linejoin="round"/>' +
      '<path d="M15 32c5-8 11-12 17-12s12 4 17 12c-5 8-11 12-17 12s-12-4-17-12Z" fill="#0d1520" stroke="#00cfff" stroke-width="3"/><circle cx="32" cy="32" r="6.5" fill="#00ff88"/><circle cx="32" cy="32" r="2.6" fill="#05070c"/>'),
    'nasdaq-data-link': mark('nd', '<ellipse cx="26" cy="15" rx="15" ry="6" fill="none" stroke="#00cfff" stroke-width="3.2"/><path d="M11 15v30c0 3.3 6.7 6 15 6 M41 15v13 M11 30c0 3.3 6.7 6 15 6" fill="none" stroke="#00cfff" stroke-width="3.2"/>' +
      '<path d="M40 38a8 8 0 0 1 11.3 0l1.4 1.4a8 8 0 0 1 0 11.3 M44 55.3a8 8 0 0 1-11.3 0l-1.4-1.4a8 8 0 0 1 0-11.3 M38.6 49.4l7.8-7.8" fill="none" stroke="#00ff88" stroke-width="3.4" stroke-linecap="round"/>')
  };
})();

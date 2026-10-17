/* The /company mockup: pictures for the "Add a department" sliders. A small lit scene per kind
 * of department, and a figure per expert with a badge for what it does. Inline SVG in the
 * site's palette only, so they stay sharp at any size and need no files. */
(function () {
  'use strict';
  var CO = window.CO;
  var C = { deep: '#06090f', navy: '#0d1520', navy2: '#111a28', line2: '#1a2a44', line3: '#1e3050', text: '#e6edf7', dim: '#a9b8cc', dim2: '#7f93ad',
    cyan: '#00cfff', green: '#00ff88', red: '#ff4444', blue: '#3b82f6' };

  CO.DEPT_INFO = {
    development: 'Idea → spec → design → build → test → release → monitor',
    design: 'Screen-by-screen briefs, and reviews of live pages against them',
    testing: "Cymetica's bug bounty: tests their products, files bugs as you, earns ET10",
    testing_lab: 'Paper experiments, success rule set first; keeps the winners',
    trading_desk: 'Finds and proves ways to make money on Cymetica, paper first',
    custom: 'Your own name, charter and experts'
  };
  CO.EXPERT_INFO = {
    qa_tester: { col: C.red, line: 'Finds bugs on the live site and drafts bounty reports' },
    researcher: { col: C.blue, line: 'Reads docs, data and the web; brings facts with sources' },
    trader: { col: C.green, line: 'Runs paper trades and proves what makes money' },
    developer: { col: C.cyan, line: 'Writes specs and Build it Better requests; checks builds' },
    lab_scientist: { col: C.green, line: 'Designs experiments, sets the success rule, judges results' },
    auditor: { col: C.blue, line: "Reviews a department's work before it reaches the Manager" },
    designer: { col: C.cyan, line: 'Draws screens and reviews live pages against their brief' }
  };

  function floor(glow) {
    var id = 'dg-' + glow.slice(1);
    return '<defs><radialGradient id="' + id + '"><stop offset="0" stop-color="' + glow + '" stop-opacity=".35"/><stop offset="1" stop-color="' + glow + '" stop-opacity="0"/></radialGradient></defs>' +
      '<ellipse cx="80" cy="80" rx="70" ry="26" fill="url(#' + id + ')"/>' +
      '<polygon points="80,58 132,82 80,106 28,82" fill="' + C.navy2 + '" stroke="' + glow + '" stroke-opacity=".55"/>' +
      '<polygon points="28,82 80,106 80,111 28,87" fill="' + C.navy + '"/><polygon points="132,82 80,106 80,111 132,87" fill="' + C.deep + '"/>';
  }
  var ART = {
    development: function () {
      return floor(C.cyan) +
        '<rect x="40" y="18" width="62" height="42" rx="4" fill="#0c1a2c" stroke="' + C.cyan + '" stroke-width="1.6"/>' +
        '<text x="71" y="45" text-anchor="middle" font-family="JetBrains Mono,monospace" font-size="17" font-weight="700" fill="' + C.cyan + '">&lt;/&gt;</text>' +
        '<rect x="64" y="60" width="14" height="10" fill="' + C.line3 + '"/><rect x="54" y="69" width="34" height="4" rx="2" fill="' + C.line3 + '"/>' +
        '<rect x="108" y="30" width="18" height="44" rx="2" fill="' + C.line3 + '" stroke="' + C.line2 + '"/>' +
        [36, 44, 52, 60].map(function (y, i) { return '<rect x="112" y="' + y + '" width="4" height="2.5" fill="' + [C.green, C.cyan, C.green, C.blue][i] + '"/><rect x="119" y="' + y + '" width="4" height="2.5" fill="' + [C.cyan, C.green, C.blue, C.green][i] + '"/>'; }).join('');
    },
    design: function () {
      return floor(C.cyan) +
        '<rect x="34" y="16" width="70" height="50" rx="5" fill="#0c1a2c" stroke="' + C.cyan + '" stroke-width="1.6"/>' +
        '<rect x="42" y="24" width="30" height="5" rx="1" fill="' + C.dim2 + '"/><rect x="42" y="33" width="54" height="14" rx="2" fill="none" stroke="' + C.dim2 + '" stroke-dasharray="3 2"/>' +
        '<rect x="42" y="52" width="16" height="7" rx="1" fill="' + C.cyan + '"/><rect x="62" y="52" width="16" height="7" rx="1" fill="' + C.line3 + '"/>' +
        [C.cyan, C.green, C.blue, C.red].map(function (c, i) { return '<rect x="' + (110 + (i % 2) * 11) + '" y="' + (30 + Math.floor(i / 2) * 11) + '" width="9" height="9" rx="2" fill="' + c + '"/>'; }).join('') +
        '<path d="M118 66 L132 52 L136 56 L122 70 Z" fill="' + C.dim + '"/><path d="M118 66 L116 72 L122 70 Z" fill="' + C.cyan + '"/>';
    },
    testing: function () {
      return floor(C.red) +
        '<rect x="38" y="14" width="46" height="58" rx="5" fill="#0c1a2c" stroke="' + C.line3 + '" stroke-width="1.6"/>' +
        '<rect x="45" y="22" width="32" height="4" rx="1" fill="' + C.dim2 + '"/><rect x="45" y="30" width="24" height="3" rx="1" fill="' + C.line3 + '"/><rect x="45" y="36" width="28" height="3" rx="1" fill="' + C.line3 + '"/>' +
        '<g transform="translate(61 52)"><ellipse rx="7" ry="9" fill="' + C.red + '"/><circle cy="-10" r="4" fill="' + C.red + '"/>' +
        '<path d="M-7 -4 L-13 -8 M7 -4 L13 -8 M-7 2 L-13 2 M7 2 L13 2 M-6 7 L-11 11 M6 7 L11 11" stroke="' + C.red + '" stroke-width="2" stroke-linecap="round"/><path d="M0 -8 L0 9" stroke="' + C.deep + '" stroke-width="1.4"/></g>' +
        '<circle cx="104" cy="42" r="16" fill="rgba(0,207,255,.08)" stroke="' + C.cyan + '" stroke-width="3"/><path d="M115 54 L128 67" stroke="' + C.cyan + '" stroke-width="5" stroke-linecap="round"/>';
    },
    testing_lab: function () {
      function flask(x, h, c) {
        return '<path d="M' + (x - 6) + ' 18 L' + (x - 6) + ' ' + (60 - h) + ' L' + (x - 18) + ' 70 Q' + x + ' 76 ' + (x + 18) + ' 70 L' + (x + 6) + ' ' + (60 - h) + ' L' + (x + 6) + ' 18 Z" fill="#0c1a2c" stroke="' + C.dim + '" stroke-width="1.6"/>' +
          '<path d="M' + (x - 13) + ' 62 L' + (x + 13) + ' 62 L' + (x + 17) + ' 70 Q' + x + ' 75 ' + (x - 17) + ' 70 Z" fill="' + c + '" opacity=".9"/>' +
          '<circle cx="' + (x - 3) + '" cy="56" r="2" fill="' + c + '"/><circle cx="' + (x + 3) + '" cy="48" r="1.5" fill="' + c + '"/><rect x="' + (x - 8) + '" y="14" width="16" height="4" rx="1" fill="' + C.line3 + '"/>';
      }
      return floor(C.green) + flask(62, 6, C.green) + flask(100, 12, C.cyan);
    },
    trading_desk: function () {
      var c = [[46, 44, 54, 1], [56, 36, 50, 1], [66, 40, 52, 0], [76, 30, 44, 1], [86, 34, 46, 0], [96, 24, 38, 1], [106, 18, 32, 1]];
      return floor(C.green) +
        '<rect x="36" y="12" width="84" height="54" rx="5" fill="#0c1a2c" stroke="' + C.green + '" stroke-width="1.6"/>' +
        c.map(function (k) { var col = k[3] ? C.green : C.red; return '<line x1="' + (k[0] + 3) + '" y1="' + (k[1] - 4) + '" x2="' + (k[0] + 3) + '" y2="' + (k[2] + 4) + '" stroke="' + col + '"/><rect x="' + k[0] + '" y="' + k[1] + '" width="6" height="' + (k[2] - k[1]) + '" fill="' + col + '"/>'; }).join('') +
        '<path d="M124 54 L134 40 L144 54" fill="none" stroke="' + C.green + '" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>';
    },
    custom: function () {
      return floor(C.blue) +
        '<rect x="50" y="16" width="60" height="50" rx="10" fill="none" stroke="' + C.cyan + '" stroke-width="2" stroke-dasharray="6 5"/>' +
        '<path d="M80 30 L80 52 M69 41 L91 41" stroke="' + C.cyan + '" stroke-width="4" stroke-linecap="round"/>';
    }
  };
  CO.deptArt = function (key) {
    return '<svg viewBox="0 0 160 112" xmlns="http://www.w3.org/2000/svg">' + (ART[key] || ART.custom)() + '</svg>';
  };

  var BADGE = {
    qa_tester: '<circle cx="-2" cy="-2" r="5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M2 2 L6 6" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/>',
    researcher: '<path d="M-7 -5 L0 -3 L7 -5 L7 5 L0 7 L-7 5 Z M0 -3 L0 7" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>',
    trader: '<path d="M-7 5 L-2 0 L1 3 L7 -4 M3 -4 L7 -4 L7 0" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
    developer: '<path d="M-3 -5 L-8 0 L-3 5 M3 -5 L8 0 L3 5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
    lab_scientist: '<path d="M-2 -7 L-2 -1 L-6 6 L6 6 L2 -1 L2 -7 M-4 -7 L4 -7" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/>',
    auditor: '<path d="M0 -7 L6 -4 L6 1 Q6 6 0 8 Q-6 6 -6 1 L-6 -4 Z" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M-3 0 L-1 2 L3 -2" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>',
    designer: '<path d="M-6 6 L-5 2 L4 -7 L7 -4 L-2 5 Z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/>'
  };
  var RULE_ICON = {
    real: ['#3b82f6', '<rect x="-6" y="-1" width="12" height="9" rx="2" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M-3.5 -1 L-3.5 -4 Q0 -9 3.5 -4 L3.5 -1" fill="none" stroke="currentColor" stroke-width="1.8"/>'],
    bug: ['#ff4444', '<ellipse rx="4.5" ry="6" fill="currentColor"/><circle cy="-7" r="2.6" fill="currentColor"/><path d="M-4 -2 L-8 -5 M4 -2 L8 -5 M-4 2 L-8 2 M4 2 L8 2 M-4 5 L-7 8 M4 5 L7 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>'],
    idea: ['#00cfff', '<path d="M-4 3 Q-8 -1 -6 -5 Q-3 -9 0 -9 Q3 -9 6 -5 Q8 -1 4 3 L4 6 L-4 6 Z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><path d="M-3 9 L3 9" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>'],
    money: ['#00ff88', '<path d="M-8 6 L-3 0 L1 3 L8 -5 M4 -5 L8 -5 L8 -1" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'],
    design: ['#00cfff', '<path d="M-7 7 L-6 3 L4 -7 L7 -4 L-3 6 Z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>'],
    released: ['#00ff88', '<path d="M0 -8 L0 5 M-5 0 L0 5 L5 0" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" transform="rotate(180)"/><path d="M-7 8 L7 8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>'],
    winner: ['#00ff88', '<path d="M-6 -7 L6 -7 L6 -3 Q6 3 0 3 Q-6 3 -6 -3 Z M0 3 L0 7 M-4 8 L4 8" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>'],
    custom: ['#7f93ad', '<circle cx="-5" r="1.8" fill="currentColor"/><circle r="1.8" fill="currentColor"/><circle cx="5" r="1.8" fill="currentColor"/>'],
    stuck: ['#ff4444', '<path d="M0 -8 L8 7 L-8 7 Z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><path d="M0 -2 L0 2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><circle cy="4.8" r="1.1" fill="currentColor"/>'],
    lesson: ['#3b82f6', '<path d="M-8 -6 L0 -4 L8 -6 L8 6 L0 8 L-8 6 Z M0 -4 L0 8" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/>']
  };
  CO.ruleIcon = function (trigger) {
    var r = RULE_ICON[trigger] || RULE_ICON.idea;
    return '<svg viewBox="-14 -14 28 28" xmlns="http://www.w3.org/2000/svg" color="' + r[0] + '"><circle r="13" fill="#06090f" stroke="' + r[0] + '" stroke-width="1.6"/>' + r[1] + '</svg>';
  };

  // a figure in the role's colour with its badge; small figures drop the badge
  CO.expertArt = function (key, small) {
    var info = CO.EXPERT_INFO[key] || { col: C.blue }, c = info.col, id = 'xg-' + key;
    return '<svg viewBox="0 0 100 110" xmlns="http://www.w3.org/2000/svg">' +
      '<defs><linearGradient id="' + id + '" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="' + c + '"/><stop offset="1" stop-color="' + c + '" stop-opacity=".5"/></linearGradient>' +
      '<radialGradient id="' + id + 'g"><stop offset="0" stop-color="' + c + '" stop-opacity=".35"/><stop offset="1" stop-color="' + c + '" stop-opacity="0"/></radialGradient></defs>' +
      '<ellipse cx="50" cy="96" rx="40" ry="11" fill="url(#' + id + 'g)"/><ellipse cx="50" cy="96" rx="22" ry="6" fill="' + C.deep + '" opacity=".8"/>' +
      '<ellipse cx="50" cy="96" rx="27" ry="8" fill="none" stroke="' + c + '" stroke-opacity=".6" stroke-width="1.4"/>' +
      '<rect x="30" y="46" width="40" height="48" rx="17" fill="url(#' + id + ')"/>' +
      '<rect x="30" y="72" width="40" height="16" rx="6" fill="' + C.deep + '" opacity=".25"/>' +
      '<circle cx="50" cy="31" r="16" fill="' + C.dim + '"/><circle cx="44" cy="25" r="5" fill="' + C.text + '" opacity=".35"/>' +
      (small ? '' : '<g transform="translate(76 74)" color="' + c + '"><circle r="13" fill="' + C.deep + '" stroke="' + c + '" stroke-width="2"/>' + (BADGE[key] || '') + '</g>') +
      '</svg>';
  };
})();

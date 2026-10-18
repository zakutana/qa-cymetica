/* The /company mockup: the Universe. Every company on the platform stands on one map; a public one can be
 * opened and looked through, read only. The companies here are SAMPLES: the live list of public companies
 * (GET /api/v1/companies, read 2026-10-17) is empty, so these show the shape, built only from what the live
 * platform has: its five department templates, its seven experts, its plans and what pays ET10 (an accepted
 * bug 1,000; Agent Tournaments prizes; Agent League puzzles). Names and owners are invented: 23 written by hand,
 * 12 more generated below, so every orbit of the Universe has stations on it and each one still reads at a glance. */
(function () {
  'use strict';
  var CO = window.CO = window.CO || {};

  // a station's shape and its colour: the colour is one of the site's four, the variety is in the shape. The keys
  // are the buildings' old ones, so a company saved before the Universe went to space keeps its pick.
  CO.SKINS = [
    { key: 'tower', name: 'Spire' }, { key: 'dome', name: 'Biodome' }, { key: 'pyramid', name: 'Ziggurat' },
    { key: 'orbital', name: 'Ring station' }, { key: 'rocket', name: 'Starship' }, { key: 'vault', name: 'Vault' }
  ];
  CO.ACCENTS = [
    { key: 'green', hex: '#00ff88' }, { key: 'cyan', hex: '#00cfff' }, { key: 'blue', hex: '#3b82f6' }, { key: 'red', hex: '#ff4444' }
  ];
  CO.accentHex = function (k) {
    for (var i = 0; i < CO.ACCENTS.length; i++) if (CO.ACCENTS[i].key === k) return CO.ACCENTS[i].hex;
    return CO.ACCENTS[0].hex;
  };
  CO.skinName = function (k) {
    for (var i = 0; i < CO.SKINS.length; i++) if (CO.SKINS[i].key === k) return CO.SKINS[i].name;
    return k;
  };

  // the owner's own company on the map: its name, building, colour and whether others may look inside.
  // Private by default, as Investable is on the live page. Only the owner's own pages write it, never a visit.
  var KEY = 'co.me.v1';
  var DEF = { name: 'My Company', mission: '', skin: 'tower', accent: 'green', public: false };
  CO.profile = function () {
    var p = {}, k;
    try { p = JSON.parse(localStorage.getItem(KEY) || '{}') || {}; } catch (e) { p = {}; }
    for (k in DEF) if (p[k] == null || p[k] === '') p[k] = DEF[k];
    return p;
  };
  CO.saveProfile = function (o) {
    if (CO.RO) return CO.profile();
    var p = CO.profile(), k;
    for (k in o) p[k] = o[k];
    try { localStorage.setItem(KEY, JSON.stringify(p)); } catch (e) { /* the page still works, it just forgets */ }
    return p;
  };

  function d(key, o) { o = o || {}; o.key = key; return o; }
  function own(name, experts, charter, o) { o = o || {}; o.key = 'custom'; o.name = name; o.experts = experts; o.charter = charter; return o; }
  var QA_ALL = ['Build it Better', 'Fund Launcher', 'Gem Screener', 'Agent Tournaments', 'Chart Analyzer', 'Agent League'];

  // bugs: accepted bug reports (1,000 ET10 each); prize: Agent Tournaments ET10; league: Agent League ET10
  CO.UNIVERSE = [
    { id: 101, name: 'Moonshot Labs', owner: '0xmila', public: true, status: 'active', plan: 'Max 5x', days: 12, skin: 'tower', accent: 'cyan',
      bugs: 6, prize: 85, league: 0,
      mission: 'Find the next memecoin runner on paper before anyone else, and get paid in ET10 for every bug on the way.',
      departments: [d('testing', { runs: 2, products: ['Gem Screener', 'Supply Analyzer', 'Chart Analyzer'] }), d('testing_lab'), d('trading_desk'), d('development'), d('design'),
        own('Memecoin scouts', ['researcher', 'trader'], 'Watch the memecoin terminal for new launches.\n- A coin goes on the list only when the Gem Screener and the Supply Analyzer agree on its numbers.\n- Hand every promising coin to the Testing lab for a paper test. Never buy.')],
      rules: [['a bug is found anywhere', 'Cymetica QA', 'verifies it and files it'], ['someone finds a way to make money', 'Testing lab', 'proves it on paper first'],
        ['an agent wins on paper', 'Trading desk', 'seats it at an Agent Tournaments table']] },
    { id: 102, name: 'Rug Radar', owner: 'safu_sam', public: true, status: 'active', plan: 'Pro', days: 9, skin: 'vault', accent: 'red',
      bugs: 4, prize: 0, league: 0,
      mission: 'Flag every coin that looks like a rug, from the Gem Screener\'s own numbers.',
      departments: [d('testing', { runs: 3, products: ['Gem Screener', 'Supply Analyzer'] }), d('testing_lab'),
        own('Holder watch', ['researcher', 'auditor'], 'Read who holds each new coin on the Gem Screener.\n- Flag a coin when its top holders own more than half, or its liquidity is thin.\n- A number that differs from the chain goes to Cymetica QA as a bug.')],
      rules: [['a bug is found anywhere', 'Cymetica QA', 'verifies it and files it'], ['a coin looks like a rug', 'Holder watch', 'checks its holders and its liquidity']] },
    { id: 103, name: 'Alpha Kitchen', owner: 'chefdegen', public: true, status: 'active', plan: 'Pro', days: 15, skin: 'dome', accent: 'green',
      bugs: 0, prize: 300, league: 0,
      mission: 'Cook trading strategies on paper and serve only the ones that win.',
      departments: [d('testing_lab'), d('trading_desk'), d('development'), d('design')],
      rules: [['someone finds a way to make money', 'Testing lab', 'proves it on paper first'], ['someone has a product idea', 'Development', 'writes it up as a Build it Better request']] },
    { id: 104, name: 'Paper Hands Capital', owner: 'noahjpeg', public: false, status: 'active', plan: 'Pro', days: 3, skin: 'pyramid', accent: 'blue',
      bugs: 0, prize: 0, league: 0, mission: 'Paper trading until it works.', departments: [d('trading_desk'), d('testing_lab')], rules: [] },
    { id: 105, name: 'Bounty Bros', owner: 'bountybro', public: true, status: 'active', plan: 'Pro', days: 21, skin: 'rocket', accent: 'green',
      bugs: 11, prize: 0, league: 0,
      mission: 'Test every Cymetica product the way a stranger meets it, and file every bug for ET10.',
      departments: [d('testing', { runs: 6, products: QA_ALL }),
        own('Docs checker', ['qa_tester', 'researcher'], 'Read /llms.txt and /api-docs against what the endpoints really answer.\n- Every promise the docs make that the API does not keep is one line, with the request.\n- Hand it to Cymetica QA to verify and file.')],
      rules: [['a bug is found anywhere', 'Cymetica QA', 'verifies it and files it'], ['a new build is released', 'Cymetica QA', 'tests it the same day and reports what is broken']] },
    { id: 106, name: 'Gem Mine', owner: 'lunaverse', public: true, status: 'active', plan: 'Max 5x', days: 8, skin: 'orbital', accent: 'cyan',
      bugs: 3, prize: 0, league: 0,
      mission: 'Ask NEXUS for the strongest themes each week and prove the picks on paper.',
      departments: [d('testing', { runs: 1, products: ['Gem Screener'] }), d('testing_lab'), d('trading_desk'), d('design'),
        own('Coin research', ['researcher', 'lab_scientist'], 'Ask NEXUS for this week\'s three strongest themes.\n- Check each pick against the Gem Screener and the Chart Analyzer.\n- One line per coin: why it is on the list, and what would take it off.')],
      rules: [['someone finds a way to make money', 'Testing lab', 'proves it on paper first'], ['an agent wins on paper', 'Trading desk', 'seats it at an Agent Tournaments table']] },
    { id: 107, name: 'Flash Grinders', owner: 'flashkid', public: true, status: 'active', plan: 'Pro', days: 5, skin: 'rocket', accent: 'red',
      bugs: 0, prize: 226, league: 0,
      mission: 'A bot at every open FLASH table, every day.',
      departments: [d('trading_desk'), d('testing_lab'),
        own('Seat keeper', ['trader', 'auditor'], 'Keep a bot at every open FLASH table.\n- Read each seat\'s rank, ROI and volume twice a day.\n- A bot that finishes outside the top three twice is archived, with the reason.')],
      rules: [['an agent wins on paper', 'Trading desk', 'seats it at an Agent Tournaments table']] },
    { id: 108, name: 'Satoshi\'s Garage', owner: 'garagegm', public: false, status: 'active', plan: 'Max 5x', days: 30, skin: 'tower', accent: 'blue',
      bugs: 6, prize: 0, league: 0, mission: 'Build it Better, from the garage.',
      departments: [d('development'), d('design'), d('testing', { runs: 1, products: ['Build it Better'] }), d('trading_desk')], rules: [] },
    { id: 109, name: 'Degen Dynamics', owner: 'dyna', public: true, status: 'active', plan: 'Max 20x', days: 25, skin: 'orbital', accent: 'green',
      bugs: 12, prize: 600, league: 3500,
      mission: 'Every department Cymetica offers, running all day: bugs, builds, paper trades, tournaments and the League.',
      departments: [d('development'), d('design'), d('testing', { runs: 4, products: QA_ALL }), d('testing_lab'), d('trading_desk'),
        own('Memecoin desk', ['trader', 'researcher'], 'Paper-trade memecoins the FOMO score flags.\n- Set the exit before the entry.\n- Hand every winner to the Trading desk.'),
        own('League team', ['researcher'], 'Answer the Agent League puzzles that are exact arithmetic on their snapshot.\n- The reasoning is the computation itself.', { runs: 12, run_kind: 'league' }),
        own('Outsider', ['researcher'], 'Once a day, meet Cymetica as a stranger who has never seen it.\n- Hand each problem to Cymetica QA; never file it yourself.', { runs: 1, run_kind: 'stranger', products: ['cymetica.com'] })],
      rules: [['a bug is found anywhere', 'Cymetica QA', 'verifies it and files it'], ['a new build is released', 'Cymetica QA', 'tests it the same day and reports what is broken'],
        ['someone finds a way to make money', 'Testing lab', 'proves it on paper first'], ['an agent wins on paper', 'Trading desk', 'seats it at an Agent Tournaments table']] },
    { id: 110, name: 'Night Owl Trading', owner: 'owlnight', public: true, status: 'paused', plan: 'Pro', days: 19, skin: 'vault', accent: 'blue',
      bugs: 0, prize: 600, league: 0,
      mission: 'Trade the quiet hours, on paper.',
      departments: [d('trading_desk'), d('testing_lab'),
        own('Night shift', ['trader', 'auditor'], 'Trade only between 00:00 and 06:00 UTC, on paper.\n- One position at a time; the exit is set before the entry.\n- Every morning, one line: what it did and why.')],
      rules: [['someone finds a way to make money', 'Testing lab', 'proves it on paper first']] },
    { id: 111, name: 'Chart Whisperers', owner: 'candlekate', public: true, status: 'active', plan: 'Pro', days: 11, skin: 'pyramid', accent: 'cyan',
      bugs: 0, prize: 0, league: 0,
      mission: 'Read the Chart Analyzer every morning and check it against what the price did next.',
      departments: [d('testing_lab'), d('development'),
        own('Chart readers', ['researcher', 'lab_scientist'], 'Read the Chart Analyzer\'s score for the top 20 coins every morning.\n- Compare it with what the price did the day after.\n- A score that misses three days in a row goes to Development as an idea.')],
      rules: [['someone has a product idea', 'Development', 'writes it up as a Build it Better request']] },
    { id: 112, name: 'Unlock Hunters', owner: 'vestingvic', public: true, status: 'active', plan: 'Pro', days: 6, skin: 'dome', accent: 'blue',
      bugs: 0, prize: 0, league: 0,
      mission: 'Trade around token unlocks, on paper, from the Supply Analyzer\'s calendar.',
      departments: [d('trading_desk'),
        own('Unlock calendar', ['researcher', 'trader'], 'Read the Supply Analyzer for every unlock in the next 14 days.\n- An unlock above 2% of supply goes on the watch list, with its date.\n- Hand each one to the Trading desk for a paper trade around the date.')],
      rules: [['a large unlock is coming', 'Trading desk', 'opens a paper trade around its date']] },
    { id: 113, name: 'League Lab', owner: 'puzzlepete', public: true, status: 'active', plan: 'Pro', days: 7, skin: 'tower', accent: 'green',
      bugs: 0, prize: 0, league: 3500,
      mission: 'Answer every Agent League puzzle we can compute exactly.',
      departments: [own('League team', ['researcher', 'lab_scientist'], 'Answer the open Agent League puzzles that are exact arithmetic on their snapshot.\n- The reasoning is the computation itself: the data used, the figures, what was rejected.\n- Nothing is sent whose answer falls outside the stated range.', { runs: 12, run_kind: 'league' }),
        d('testing_lab')],
      rules: [] },
    { id: 114, name: 'Fund Factory', owner: 'fundfrank', public: true, status: 'active', plan: 'Max 5x', days: 14, skin: 'vault', accent: 'cyan',
      bugs: 1, prize: 0, league: 0,
      mission: 'Make the Fund Launcher pages better, one Build it Better request at a time.',
      departments: [d('development'), d('design'), d('testing', { runs: 1, products: ['Fund Launcher'] }),
        own('Fund analysts', ['researcher', 'auditor'], 'Read every fund page on the Fund Launcher.\n- Check each figure a visitor sees against its API.\n- A figure that does not reconcile goes to Cymetica QA.')],
      rules: [['a bug is found anywhere', 'Cymetica QA', 'verifies it and files it'], ['someone has a product idea', 'Development', 'writes it up as a Build it Better request']] },
    { id: 115, name: 'Ape Research', owner: 'apestrong', public: false, status: 'active', plan: 'Max 5x', days: 18, skin: 'dome', accent: 'red',
      bugs: 5, prize: 0, league: 0, mission: 'Research first, ape second.',
      departments: [d('testing_lab'), d('trading_desk'), d('development'), d('design'), d('testing', { runs: 2, products: ['Gem Screener', 'Chart Analyzer'] })], rules: [] },
    { id: 116, name: 'Grid Lords', owner: 'gridlord', public: true, status: 'active', plan: 'Pro', days: 4, skin: 'pyramid', accent: 'green',
      bugs: 0, prize: 0, league: 0,
      mission: 'Find the grid spacing that pays after fees.',
      departments: [d('testing_lab'), d('trading_desk'),
        own('Grid tuner', ['lab_scientist', 'trader'], 'Run grid bots on paper: one pair, five spacings, a week each.\n- Keep the spacing that made the most after fees; archive the rest, with the reason.')],
      rules: [['an agent wins on paper', 'Trading desk', 'seats it at an Agent Tournaments table']] },
    { id: 117, name: 'Stealth Mode', owner: 'anon_1337', public: false, status: 'active', plan: 'Pro', days: 1, skin: 'vault', accent: 'green',
      bugs: 0, prize: 0, league: 0, mission: '', departments: [own('R&D', ['researcher'], 'Not yet.')], rules: [] },
    { id: 118, name: 'Pixel Perfect', owner: 'uxmaya', public: true, status: 'active', plan: 'Pro', days: 10, skin: 'orbital', accent: 'blue',
      bugs: 0, prize: 0, league: 0,
      mission: 'Review Cymetica\'s live pages against their briefs and ask for what is missing.',
      departments: [d('design'), d('development')],
      rules: [['a page looks wrong', 'Design studio', 'reviews it against its brief'], ['someone has a product idea', 'Development', 'writes it up as a Build it Better request']] },
    { id: 119, name: 'Event Card Club', owner: 'cardshark', public: true, status: 'active', plan: 'Pro', days: 6, skin: 'rocket', accent: 'cyan',
      bugs: 0, prize: 0, league: 0,
      mission: 'Paper-trade event cards and keep score honestly.',
      departments: [d('testing_lab'), d('trading_desk'),
        own('Card desk', ['trader', 'lab_scientist'], 'Paper-trade event cards on the 6-hour window.\n- Judge each card at its settlement, never at its current index.\n- Count the fees before calling a win.')],
      rules: [['someone finds a way to make money', 'Testing lab', 'proves it on paper first']] },
    { id: 120, name: 'LP Party', owner: 'lpparty', public: true, status: 'paused', plan: 'Pro', days: 27, skin: 'dome', accent: 'cyan',
      bugs: 0, prize: 0, league: 0,
      mission: 'Paper liquidity, real lessons.',
      departments: [d('trading_desk'),
        own('Pool watch', ['researcher', 'trader'], 'Read pool depth before any paper trade.\n- A price from a pool with almost nothing in it is not a price.')],
      rules: [] },
    { id: 121, name: 'Bot Breeders', owner: 'breeder', public: true, status: 'active', plan: 'Max 5x', days: 13, skin: 'tower', accent: 'red',
      bugs: 1, prize: 127, league: 0,
      mission: 'Clone the best bots, change one thing at a time, and race the variants.',
      departments: [d('testing_lab'), d('trading_desk'), d('testing', { runs: 1, products: ['Agent Tournaments'] }),
        own('Clone farm', ['lab_scientist', 'trader'], 'Clone the top 20 species on paper.\n- Change one setting at a time; a variant lives a week.\n- The best variant goes to the Trading desk.')],
      rules: [['an agent wins on paper', 'Trading desk', 'seats it at an Agent Tournaments table'], ['a bug is found anywhere', 'Cymetica QA', 'verifies it and files it']] },
    { id: 122, name: 'Diamond Desk', owner: 'diamondhands', public: false, status: 'active', plan: 'Pro', days: 16, skin: 'pyramid', accent: 'red',
      bugs: 0, prize: 0, league: 0, mission: 'Hold.', departments: [d('trading_desk'), d('testing_lab'), own('Risk', ['auditor'], 'Nothing over 2x.')], rules: [] },
    { id: 123, name: 'Zero to One', owner: 'founder01', public: true, status: 'active', plan: 'Pro', days: 0, skin: 'orbital', accent: 'red',
      bugs: 0, prize: 0, league: 0,
      mission: 'Day one. Learning how Cymetica works.',
      departments: [d('testing_lab')], rules: [] }
  ];
  // Seven orbits want more than 23. The rest are SAMPLES too, generated the same way every time: a name, an owner,
  // two to five of the platform's own department templates (no charters of their own), the processes the platform's
  // templates suggest for them, and ET10 only from what pays it (accepted bugs, tournament prizes).
  (function more() {
    var s = 20261018, R = function () { s = (s * 16807) % 2147483647; return (s - 1) / 2147483646; };
    var pick = function (a) { return a[Math.floor(R() * a.length)]; };
    var shuffle = function (a) { a = a.slice(); for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(R() * (i + 1)), t = a[i]; a[i] = a[j]; a[j] = t; } return a; };
    var A = ['Lunar', 'Nova', 'Orbit', 'Quantum', 'Pulsar', 'Comet', 'Nebula', 'Vector', 'Sigma', 'Apex', 'Helix', 'Photon', 'Quasar',
      'Rekt', 'Stellar', 'Titan', 'Vega', 'Zenith', 'Based', 'Bull', 'Degen', 'Gas', 'Giga', 'Hodl', 'Moon', 'Pump', 'Wagmi', 'Whale',
      'Yield', 'Omega', 'Laser', 'Sats', 'Gamma', 'Ion', 'Meteor', 'Signal', 'Echo', 'Delta', 'Orion', 'Cosmo'];
    var B = ['Labs', 'Capital', 'Works', 'Desk', 'Collective', 'Syndicate', 'Ventures', 'Research', 'Systems', 'Guild', 'Station', 'Fund',
      'Foundry', 'Club', 'Crew', 'Holdings', 'Trading', 'Analytics', 'Signals', 'Outpost', 'Ops', 'Dynamics', 'Partners', 'Base'];
    var H1 = ['degen', 'moon', 'sats', 'ape', 'anon', 'gm', 'wen', 'ser', 'fren', 'based', 'pump', 'alpha', 'nova', 'orbit', 'luna', 'whale', '0x'];
    var H2 = ['dev', 'max', 'kid', 'lord', 'cat', 'fox', 'bot', 'pilot', 'chef', 'pete', 'kate', 'vic', 'mila', 'sam', 'jo', 'rex'];
    var ROLE = {
      testing: { rule: ['a bug is found anywhere', 'Cymetica QA', 'verifies it and files it'], mission: ['File every bug Cymetica would pay for, each one reproduced twice.', 'Test each new Cymetica build the day it ships.'] },
      testing_lab: { rule: ['someone finds a way to make money', 'Testing lab', 'proves it on paper first'], mission: ['Prove every idea on paper before anything else.', 'Paper-test what NEXUS suggests, a week at a time.'] },
      trading_desk: { rule: ['an agent wins on paper', 'Trading desk', 'seats it at an Agent Tournaments table'], mission: ['Seat the best paper agents at Agent Tournaments tables.', 'Paper trades only, scored after fees.'] },
      development: { rule: ['someone has a product idea', 'Development', 'writes it up as a Build it Better request'], mission: ['Turn every good idea into a Build it Better request.'] },
      design: { rule: ['a page looks wrong', 'Design studio', 'reviews it against its brief'], mission: ['Review Cymetica\'s pages against their briefs.'] }
    };
    var KEYS = ['testing', 'testing_lab', 'trading_desk', 'development', 'design'], SK = ['tower', 'dome', 'pyramid', 'orbital', 'rocket', 'vault'];
    var taken = {}; CO.UNIVERSE.forEach(function (c) { taken[c.name] = 1; });
    for (var id = 124; id < 136; id++) {
      var name; do { name = pick(A) + ' ' + pick(B); } while (taken[name]); taken[name] = 1;
      var keys = shuffle(KEYS).slice(0, 2 + Math.floor(R() * R() * 4));
      var first = keys[0], qa = keys.indexOf('testing') >= 0, desk = keys.indexOf('trading_desk') >= 0;
      var deps = keys.map(function (k) {
        if (k !== 'testing') return d(k);
        return d(k, { runs: pick([1, 2, 2, 3, 4]), products: shuffle(QA_ALL).slice(0, 1 + Math.floor(R() * 4)) });
      });
      var pub = R() < 0.66, days = Math.floor(R() * 40);
      CO.UNIVERSE.push({ id: id, name: name, owner: pick(H1) + (R() < 0.4 ? '_' : '') + pick(H2) + (R() < 0.3 ? Math.floor(R() * 99) : ''),
        public: pub, status: R() < 0.08 ? 'paused' : 'active', plan: R() < 0.7 ? 'Pro' : R() < 0.85 ? 'Max 5x' : 'Max 20x', days: days,
        skin: pick(SK), accent: pick(['green', 'cyan', 'blue', 'red']),
        bugs: qa ? Math.floor(R() * R() * 10) : 0, prize: desk && R() < 0.4 ? 85 * (1 + Math.floor(R() * 6)) : 0, league: 0,
        mission: pick(ROLE[first].mission), departments: deps,
        rules: pub ? keys.map(function (k) { return ROLE[k].rule; }) : [] });
    }
  })();
  CO.uvCompany = function (id) {
    for (var i = 0; i < CO.UNIVERSE.length; i++) if (CO.UNIVERSE[i].id === id) return CO.UNIVERSE[i];
    return null;
  };
  CO.uvEt10 = function (c) { return (c.bugs || 0) * 1000 + (c.prize || 0) + (c.league || 0); };
})();

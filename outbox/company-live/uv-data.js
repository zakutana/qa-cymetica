/* The /company mockup: the Universe. Since 2026-10-21 it is marketing, not a map of companies: land round Cymetica
 * bought a slot at a time with ET10 and built on through Build it Better, and our two products as ads on it (CO.ADS).
 * Also here: the stations a company can pick, their colours and icons, and the owner's own profile. */
(function () {
  'use strict';
  var CO = window.CO = window.CO || {};

  // a station's shape and its colour: the colour is one of the site's four, the variety is in the shape. The keys
  // are the buildings' old ones, so a company saved before the Universe went to space keeps its pick.
  // The seven as stations.js draws them since 2026-10-20 (it sets these names too when it installs them; here, so the
  // flat pictures where 3D cannot start carry the same ones).
  CO.SKINS = [
    { key: 'tower', name: 'Dreadnought' }, { key: 'dome', name: 'Shipyard' }, { key: 'pyramid', name: 'Pyramid Carrier' },
    { key: 'orbital', name: 'Ring Habitat' }, { key: 'rocket', name: 'Lancer' }, { key: 'vault', name: 'Citadel' }, { key: 'stack', name: 'Monolith' }
  ];
  // The ten new picks (outbox/company-skins: SPEC.md, and index.html, which draws them). Designed and previewed, not yet
  // built into the Universe's 3D: spec = true. Settings shows each from the showcase's own projector (spec-skins.js);
  // the map and the flat pictures draw an unbuilt key as a Dreadnought (their `|| SKIN.tower`) until a builder for it
  // is put into CO.U3.SKIN, which CO.skinBuilt notices by itself.
  [['armillary', 'Armillary Core'], ['helix', 'Helix Spire'], ['sail', 'Solar Sail'], ['dish', 'Deep Array'], ['arcology', 'Glass Arcology'],
    ['crown', 'Pylon Crown'], ['rift', 'Rift Hold'], ['tesseract', 'Tesseract Frame'], ['nautilus', 'Nautilus Shell'], ['vortex', 'Halo Vortex']
  ].forEach(function (s) { CO.SKINS.push({ key: s[0], name: s[1], spec: true }); });
  // is this station drawn by the Universe itself (3D), or only previewed?
  CO.skinBuilt = function (k) {
    for (var i = 0; i < CO.SKINS.length; i++) if (CO.SKINS[i].key === k) {
      if (!CO.SKINS[i].spec) return true;
      return !!(CO.U3 && CO.U3.ok && CO.U3.SKIN && CO.U3.SKIN[k]);
    }
    return true;
  };
  CO.ACCENTS = [
    { key: 'green', hex: '#00ff88' }, { key: 'cyan', hex: '#00cfff' }, { key: 'blue', hex: '#3b82f6' }, { key: 'red', hex: '#ff4444' },
    // four more for a station ("a pridej vice barev", 2026-10-20): the Universe is a game scene, outside the site's
    // palette rule (SPEC-NOTES, 2026-10-18); no orange, which in the office means a room waiting on its owner
    { key: 'purple', hex: '#a855f7' }, { key: 'pink', hex: '#ff4fd8' }, { key: 'gold', hex: '#ffc83d' }, { key: 'white', hex: '#e6eef8' }
  ];
  CO.accentHex = function (k) {
    for (var i = 0; i < CO.ACCENTS.length; i++) if (CO.ACCENTS[i].key === k) return CO.ACCENTS[i].hex;
    return CO.ACCENTS[0].hex;
  };
  // Each station as a line icon, drawn as the departments' are (data.js DEPT_ICON) -- the company's logo, in its
  // colour ("v tom stylu jak maji ruzne departmenty ikonky ... barva cele ikonky podle toho jakou si zvolil barvu firmy")
  CO.STATION_ICON = {
    tower: '<path d="M1.8 14.2h16.4l-2.3 2.6H4.4Z M5 14.2v-3h9.4v3 M7 11.2V8.4h5.4v2.8 M8.6 8.4V5.8h2.2v2.6 M9.7 5.8V2.6"/><circle cx="12.4" cy="12.7" r=".5" fill="currentColor"/><circle cx="10.4" cy="12.7" r=".5" fill="currentColor"/>',
    dome: '<path d="M2.8 17.2V5.2h3.4v12 M13.8 17.2V5.2h3.4v12 M6.2 7.4h7.6 M6.2 9.8h7.6 M2.8 17.2h14.4 M4.5 5.2V2.8 M15.5 5.2V2.8 M7.6 17.2l2.4-4.4 2.4 4.4"/>',
    pyramid: '<ellipse cx="10" cy="14.4" rx="8" ry="2.7"/><path d="M5.4 13.4l1.4-3.6h6.4l1.4 3.6 M7.6 9.8l.9-3.2h3l.9 3.2 M9 6.6l1-3.6 1 3.6"/>',
    orbital: '<ellipse cx="10" cy="11.6" rx="8" ry="3.7"/><path d="M4.4 9.2l11.2 4.8 M15.6 9.2 4.4 14 M10 6.6V2.8"/><rect x="8.3" y="6.6" width="3.4" height="7.2" rx="1.7"/>',
    rocket: '<path d="M1.8 11.2l4.4-2.6h9.4l2.6 1.1v3l-2.6 1.1H6.2Z M7.6 8.6v5.2 M9.4 8.6v5.2 M13 8.6V5.8h2.2v2.8 M18.2 10.4v1.6"/>',
    vault: '<ellipse cx="10" cy="14.8" rx="8" ry="2.5"/><path d="M5.2 14.4v-3.6a4.8 4.8 0 0 1 9.6 0v3.6 M10 6V2.2 M5.4 11.8h9.2"/>',
    stack: '<rect x="7.6" y="3" width="4.8" height="11.2" rx=".6"/><path d="M3.8 15.6l2.1-1.4h8.2l2.1 1.4-2.1 1.4H5.9Z M9.1 5.6h1.8 M9.1 8h1.8 M9.1 10.4h1.8"/><rect x="3.2" y="5" width="1.8" height="1.8"/><rect x="15" y="8" width="1.8" height="1.8"/>',
    // the ten new ones, as SPEC.md draws them
    armillary: '<ellipse cx="10" cy="10" rx="4.4" ry="8.2" transform="rotate(18 10 10)"/><ellipse cx="10" cy="10" rx="8.4" ry="3" transform="rotate(-12 10 10)"/><rect x="8.7" y="6.2" width="2.6" height="7.6" rx="1.3"/>',
    helix: '<path d="M5 17.6h10 M6.4 17.6C7.2 12.4 8.8 8.8 8 4.4h4C11.2 8.8 12.8 12.4 13.6 17.6 M10.6 17.6C9.6 12.6 11.4 8.6 9.8 4.4 M10 4.4V1.8"/>',
    sail: '<path d="M1.6 12.4 10 8.4l8.4 4L10 16.4Z M1.6 12.4h16.8 M10 8.4v8 M10 5V2.8"/><rect x="8.8" y="5" width="2.4" height="7.4" rx=".8"/>',
    dish: '<path d="M2.8 11.8a8 8 0 0 0 9-9Z M2.8 11.8 5.2 5.2 11.8 2.8 M9.6 9.6l1.6 5.2 M7.4 17.4h8.8 M8.8 17.4l1.6-2.6h2.6l1.4 2.6"/><circle cx="5.2" cy="5.2" r=".9" fill="currentColor"/>',
    arcology: '<path d="M1.8 15.2h16.4 M3.2 15.2a6.8 6.8 0 0 1 13.6 0 M3.6 17.4h12.8 M8.8 15.2v-4.6h2.4v4.6 M6 15.2v-2.4h1.8v2.4 M12.2 15.2v-3.2h1.8v3.2 M10 8.4V6.2"/>',
    crown: '<ellipse cx="10" cy="15.4" rx="8" ry="2.4"/><path d="M3.4 14.4V8 M6.6 13.2V4.2 M13.4 13.2V4.2 M16.6 14.4V8"/><circle cx="10" cy="9" r="1.8"/>',
    rift: '<path d="M8.2 4.4 4.6 5.2 2.2 9.2l.8 5 3.4 2.6h1.8Z M11.8 4l4 1 2.2 4.4-1 5.2-3.2 2.4h-2Z M8.2 8.2h3.6 M8.2 11.2h3.6 M8.2 14.2h3.6"/>',
    tesseract: '<path d="M10 1.4 16.2 5v7.2L10 15.8 3.8 12.2V5Z M3.8 5 10 8.6 16.2 5 M10 8.6v7.2 M10 15.8v2 M6.6 18.6h6.8"/>',
    nautilus: '<path d="M7.3 11.6 7.1 10.8 7.4 10.2 8 9.8 8.7 9.7 9.5 10 10.2 10.7 10.4 11.8 10.1 12.9 9.2 13.8 7.9 14.2 6.4 13.9 5 12.9 4.3 11.1 4.5 9.1 5.7 7.2 8 6 10.8 5.9 13.5 7.4 15.4 10.2 15.8 12.1 M7.1 11 4.3 10.2 M8.2 9.8 7.9 6 M10.1 10.6 14.6 8.8"/>',
    vortex: '<path d="M2 5.4a8 2.2 0 1 0 16 0 8 2.2 0 1 0-16 0 M4.2 9.6a5.8 1.6 0 1 0 11.6 0 5.8 1.6 0 1 0-11.6 0 M6.3 13.4a3.7 1.1 0 1 0 7.4 0 3.7 1.1 0 1 0-7.4 0 M10 18.4V3.2"/>'
  };
  CO.SKINS.forEach(function (s) { s.icon = CO.STATION_ICON[s.key]; });
  CO.stationIcon = function (skin, accent) {
    return '<span class="dic logo" style="--ic:' + CO.accentHex(accent) + '"><svg viewBox="0 0 20 20" aria-hidden="true">' +
      (CO.STATION_ICON[skin] || CO.STATION_ICON.dome) + '</svg></span>';
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

  // No companies stand on the map any more (the operator, 2026-10-21: "smaz tam vsechny firmy"): the Universe is land
  // round Cymetica, sold a slot at a time, and two ads stand on it. A visit (?visit=<id>) finds no company.
  // The companies that stand on the map again (the operator, 2026-10-22: the ones that exist show in the Universe; round 2's
  // "no companies on the map" was our mistake): the samples as they were before the land, 36 stations with ours, private
  // and public. The land and the two products stand between them (CO.uvPlan).
  var QA_ALL = ['Build it Better', 'Fund Launcher', 'Gem Screener', 'Chart Analyzer', 'Supply Analyzer'];

  // bugs: accepted bug reports (1,000 ET10 each)
  CO.UNIVERSE = [
    { id: 101, name: 'Moonshot Labs', owner: '0xmila', public: true, status: 'active', plan: 'Max 5x', days: 12, skin: 'tower', accent: 'cyan',
      bugs: 6, 
      mission: 'Find the next memecoin runner on paper before anyone else, and get paid in ET10 for every bug on the way.',
      departments: [d('testing', { runs: 2, products: ['Gem Screener', 'Supply Analyzer', 'Chart Analyzer'] }), d('testing_lab'), d('trading_desk'), d('development'), d('design'),
        own('Memecoin scouts', ['researcher', 'trader'], 'Watch the memecoin terminal for new launches.\n- A coin goes on the list only when the Gem Screener and the Supply Analyzer agree on its numbers.\n- Hand every promising coin to the Testing lab for a paper test. Never buy.')],
      rules: [['a bug is found anywhere', 'Cymetica QA', 'verifies it and files it'], ['someone finds a way to make money', 'Testing lab', 'proves it on paper first'],
        ['an experiment wins on paper', 'Trading desk', 'puts it into production once you approve: an Agent Tournaments seat or real money']] },
    { id: 102, name: 'Rug Radar', owner: 'safu_sam', public: true, status: 'active', plan: 'Pro', days: 9, skin: 'vault', accent: 'red',
      bugs: 4, 
      mission: 'Flag every coin that looks like a rug, from the Gem Screener\'s own numbers.',
      departments: [d('testing', { runs: 3, products: ['Gem Screener', 'Supply Analyzer'] }), d('testing_lab'),
        own('Holder watch', ['researcher', 'auditor'], 'Read who holds each new coin on the Gem Screener.\n- Flag a coin when its top holders own more than half, or its liquidity is thin.\n- A number that differs from the chain goes to Cymetica QA as a bug.')],
      rules: [['a bug is found anywhere', 'Cymetica QA', 'verifies it and files it'], ['a coin looks like a rug', 'Holder watch', 'checks its holders and its liquidity']] },
    { id: 103, name: 'Alpha Kitchen', owner: 'chefdegen', public: true, status: 'active', plan: 'Pro', days: 15, skin: 'dome', accent: 'green',
      bugs: 0, 
      mission: 'Cook trading strategies on paper and serve only the ones that win.',
      departments: [d('testing_lab'), d('trading_desk'), d('development'), d('design')],
      rules: [['someone finds a way to make money', 'Testing lab', 'proves it on paper first'], ['someone has a product idea', 'Development', 'writes it up as a Build it Better request']] },
    { id: 104, name: 'Paper Hands Capital', owner: 'noahjpeg', public: false, status: 'active', plan: 'Pro', days: 3, skin: 'pyramid', accent: 'blue',
      bugs: 0, mission: 'Paper trading until it works.', departments: [d('trading_desk'), d('testing_lab')], rules: [] },
    { id: 105, name: 'Bounty Bros', owner: 'bountybro', public: true, status: 'active', plan: 'Pro', days: 21, skin: 'rocket', accent: 'green',
      bugs: 11, 
      mission: 'Test every Cymetica product the way a stranger meets it, and file every bug for ET10.',
      departments: [d('testing', { runs: 6, products: QA_ALL }),
        own('Docs checker', ['qa_tester', 'researcher'], 'Read /llms.txt and /api-docs against what the endpoints really answer.\n- Every promise the docs make that the API does not keep is one line, with the request.\n- Hand it to Cymetica QA to verify and file.')],
      rules: [['a bug is found anywhere', 'Cymetica QA', 'verifies it and files it'], ['a new build is released', 'Cymetica QA', 'tests it the same day and reports what is broken']] },
    { id: 106, name: 'Gem Mine', owner: 'lunaverse', public: true, status: 'active', plan: 'Max 5x', days: 8, skin: 'orbital', accent: 'cyan',
      bugs: 3, 
      mission: 'Ask NEXUS for the strongest themes each week and prove the picks on paper.',
      departments: [d('testing', { runs: 1, products: ['Gem Screener'] }), d('testing_lab'), d('trading_desk'), d('design'),
        own('Coin research', ['researcher', 'lab_scientist'], 'Ask NEXUS for this week\'s three strongest themes.\n- Check each pick against the Gem Screener and the Chart Analyzer.\n- One line per coin: why it is on the list, and what would take it off.')],
      rules: [['someone finds a way to make money', 'Testing lab', 'proves it on paper first'], ['an experiment wins on paper', 'Trading desk', 'puts it into production once you approve: an Agent Tournaments seat or real money']] },
    { id: 107, name: 'Flash Grinders', owner: 'flashkid', public: true, status: 'active', plan: 'Pro', days: 5, skin: 'rocket', accent: 'red',
      bugs: 0, 
      mission: 'A bot at every open FLASH table, every day.',
      departments: [d('trading_desk'), d('testing_lab'),
        own('Seat keeper', ['trader', 'auditor'], 'Keep a bot at every open FLASH table.\n- Read each seat\'s rank, ROI and volume twice a day.\n- A bot that finishes outside the top three twice is archived, with the reason.')],
      rules: [['an experiment wins on paper', 'Trading desk', 'puts it into production once you approve: an Agent Tournaments seat or real money']] },
    { id: 108, name: 'Satoshi\'s Garage', owner: 'garagegm', public: false, status: 'active', plan: 'Max 5x', days: 30, skin: 'stack', accent: 'blue',
      bugs: 6, mission: 'Build it Better, from the garage.',
      departments: [d('development'), d('design'), d('testing', { runs: 1, products: ['Build it Better'] }), d('trading_desk')], rules: [] },
    { id: 109, name: 'Degen Dynamics', owner: 'dyna', public: true, status: 'active', plan: 'Max 20x', days: 25, skin: 'orbital', accent: 'green',
      bugs: 12, 
      mission: 'Every department Cymetica offers, running all day: bugs, builds and paper trades.',
      departments: [d('development'), d('design'), d('testing', { runs: 4, products: QA_ALL }), d('testing_lab'), d('trading_desk'),
        own('Memecoin desk', ['trader', 'researcher'], 'Paper-trade memecoins the FOMO score flags.\n- Set the exit before the entry.\n- Hand every winner to the Trading desk.')],
      rules: [['a bug is found anywhere', 'Cymetica QA', 'verifies it and files it'], ['a new build is released', 'Cymetica QA', 'tests it the same day and reports what is broken'],
        ['someone finds a way to make money', 'Testing lab', 'proves it on paper first'], ['an experiment wins on paper', 'Trading desk', 'puts it into production once you approve: an Agent Tournaments seat or real money']] },
    { id: 110, name: 'Night Owl Trading', owner: 'owlnight', public: true, status: 'paused', plan: 'Pro', days: 19, skin: 'stack', accent: 'cyan',
      bugs: 0, 
      mission: 'Trade the quiet hours, on paper.',
      departments: [d('trading_desk'), d('testing_lab'),
        own('Night shift', ['trader', 'auditor'], 'Trade only between 00:00 and 06:00 UTC, on paper.\n- One position at a time; the exit is set before the entry.\n- Every morning, one line: what it did and why.')],
      rules: [['someone finds a way to make money', 'Testing lab', 'proves it on paper first']] },
    { id: 111, name: 'Chart Whisperers', owner: 'candlekate', public: true, status: 'active', plan: 'Pro', days: 11, skin: 'pyramid', accent: 'cyan',
      bugs: 0, 
      mission: 'Read the Chart Analyzer every morning and check it against what the price did next.',
      departments: [d('testing_lab'), d('development'),
        own('Chart readers', ['researcher', 'lab_scientist'], 'Read the Chart Analyzer\'s score for the top 20 coins every morning.\n- Compare it with what the price did the day after.\n- A score that misses three days in a row goes to Development as an idea.')],
      rules: [['someone has a product idea', 'Development', 'writes it up as a Build it Better request']] },
    { id: 112, name: 'Unlock Hunters', owner: 'vestingvic', public: true, status: 'active', plan: 'Pro', days: 6, skin: 'dome', accent: 'blue',
      bugs: 0, 
      mission: 'Trade around token unlocks, on paper, from the Supply Analyzer\'s calendar.',
      departments: [d('trading_desk'),
        own('Unlock calendar', ['researcher', 'trader'], 'Read the Supply Analyzer for every unlock in the next 14 days.\n- An unlock above 2% of supply goes on the watch list, with its date.\n- Hand each one to the Trading desk for a paper trade around the date.')],
      rules: [['a large unlock is coming', 'Trading desk', 'opens a paper trade around its date']] },
    { id: 113, name: 'Signal Lab', owner: 'puzzlepete', public: true, status: 'active', plan: 'Pro', days: 7, skin: 'tower', accent: 'green',
      bugs: 0, 
      mission: 'Prove on paper which of Cymetica\'s signals hold up.',
      departments: [d('testing_lab'), d('trading_desk')],
      rules: [['someone finds a way to make money', 'Testing lab', 'proves it on paper first']] },
    { id: 114, name: 'Fund Factory', owner: 'fundfrank', public: true, status: 'active', plan: 'Max 5x', days: 14, skin: 'vault', accent: 'cyan',
      bugs: 1, 
      mission: 'Make the Fund Launcher pages better, one Build it Better request at a time.',
      departments: [d('development'), d('design'), d('testing', { runs: 1, products: ['Fund Launcher'] }),
        own('Fund analysts', ['researcher', 'auditor'], 'Read every fund page on the Fund Launcher.\n- Check each figure a visitor sees against its API.\n- A figure that does not reconcile goes to Cymetica QA.')],
      rules: [['a bug is found anywhere', 'Cymetica QA', 'verifies it and files it'], ['someone has a product idea', 'Development', 'writes it up as a Build it Better request']] },
    { id: 115, name: 'Ape Research', owner: 'apestrong', public: false, status: 'active', plan: 'Max 5x', days: 18, skin: 'dome', accent: 'red',
      bugs: 5, mission: 'Research first, ape second.',
      departments: [d('testing_lab'), d('trading_desk'), d('development'), d('design'), d('testing', { runs: 2, products: ['Gem Screener', 'Chart Analyzer'] })], rules: [] },
    { id: 116, name: 'Grid Lords', owner: 'gridlord', public: true, status: 'active', plan: 'Pro', days: 4, skin: 'pyramid', accent: 'green',
      bugs: 0, 
      mission: 'Find the grid spacing that pays after fees.',
      departments: [d('testing_lab'), d('trading_desk'),
        own('Grid tuner', ['lab_scientist', 'trader'], 'Run grid bots on paper: one pair, five spacings, a week each.\n- Keep the spacing that made the most after fees; archive the rest, with the reason.')],
      rules: [['an experiment wins on paper', 'Trading desk', 'puts it into production once you approve: an Agent Tournaments seat or real money']] },
    { id: 117, name: 'Stealth Mode', owner: 'anon_1337', public: false, status: 'active', plan: 'Pro', days: 1, skin: 'vault', accent: 'green',
      bugs: 0, mission: '', departments: [own('R&D', ['researcher'], 'Not yet.')], rules: [] },
    { id: 118, name: 'Pixel Perfect', owner: 'uxmaya', public: true, status: 'active', plan: 'Pro', days: 10, skin: 'orbital', accent: 'blue',
      bugs: 0, 
      mission: 'Review Cymetica\'s live pages against their briefs and ask for what is missing.',
      departments: [d('design'), d('development')],
      rules: [['a page looks wrong', 'Design studio', 'reviews it against its brief'], ['someone has a product idea', 'Development', 'writes it up as a Build it Better request']] },
    { id: 119, name: 'Event Card Club', owner: 'cardshark', public: true, status: 'active', plan: 'Pro', days: 6, skin: 'rocket', accent: 'cyan',
      bugs: 0, 
      mission: 'Paper-trade event cards and keep score honestly.',
      departments: [d('testing_lab'), d('trading_desk'),
        own('Card desk', ['trader', 'lab_scientist'], 'Paper-trade event cards on the 6-hour window.\n- Judge each card at its settlement, never at its current index.\n- Count the fees before calling a win.')],
      rules: [['someone finds a way to make money', 'Testing lab', 'proves it on paper first']] },
    { id: 120, name: 'LP Party', owner: 'lpparty', public: true, status: 'paused', plan: 'Pro', days: 27, skin: 'dome', accent: 'cyan',
      bugs: 0, 
      mission: 'Paper liquidity, real lessons.',
      departments: [d('trading_desk'),
        own('Pool watch', ['researcher', 'trader'], 'Read pool depth before any paper trade.\n- A price from a pool with almost nothing in it is not a price.')],
      rules: [] },
    { id: 121, name: 'Bot Breeders', owner: 'breeder', public: true, status: 'active', plan: 'Max 5x', days: 13, skin: 'stack', accent: 'red',
      bugs: 1, 
      mission: 'Clone the best bots, change one thing at a time, and race the variants.',
      departments: [d('testing_lab'), d('trading_desk'), d('testing', { runs: 1, products: ['Fund Launcher'] }),
        own('Clone farm', ['lab_scientist', 'trader'], 'Clone the top 20 species on paper.\n- Change one setting at a time; a variant lives a week.\n- The best variant goes to the Trading desk.')],
      rules: [['an experiment wins on paper', 'Trading desk', 'puts it into production once you approve: an Agent Tournaments seat or real money'], ['a bug is found anywhere', 'Cymetica QA', 'verifies it and files it']] },
    { id: 122, name: 'Diamond Desk', owner: 'diamondhands', public: false, status: 'active', plan: 'Pro', days: 16, skin: 'pyramid', accent: 'red',
      bugs: 0, mission: 'Hold.', departments: [d('trading_desk'), d('testing_lab'), own('Risk', ['auditor'], 'Nothing over 2x.')], rules: [] },
    { id: 123, name: 'Zero to One', owner: 'founder01', public: true, status: 'active', plan: 'Pro', days: 0, skin: 'orbital', accent: 'red',
      bugs: 0, 
      mission: 'Day one. Learning how Cymetica works.',
      departments: [d('testing_lab')], rules: [] }
  ];
  // Seven orbits want more than 23. The rest are SAMPLES too, generated the same way every time: a name, an owner,
  // two to five of the platform's own department templates (no charters of their own), the processes the platform's
  // templates suggest for them, and ET10 only from what pays it (accepted bugs).
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
      trading_desk: { rule: ['an experiment wins on paper', 'Trading desk', 'puts it into production once you approve: an Agent Tournaments seat or real money'], mission: ['Put the lab\'s winning bots to work: Agent Tournaments seats, real money with approval.', 'Only what won on paper goes live.'] },
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
  // The operator's picture of the Universe names its stations; the samples carry the same names, colours and
  // shapes, so a click on one there opens that company here (2026-10-18). A generated sample that happened to
  // draw one of these names keeps its own with " Labs" after it.
  [['Sigma Collective', 'blue', 'tower'], ['Ion Analytics', 'green', 'orbital'], ['Giga Fund', 'red', 'vault'], ['Vector Trading', 'cyan', 'tower'],
    ['Bull Club', 'red', 'pyramid'], ['Quasar Fund', 'green', 'dome'], ['Laser Station', 'red', 'rocket']].forEach(function (p, i) {
    var c = CO.UNIVERSE.filter(function (x) { return x.id === 124 + i; })[0]; if (!c) return;
    CO.UNIVERSE.forEach(function (o) { if (o !== c && o.name === p[0]) o.name = p[0] + ' Labs'; });
    c.name = p[0]; c.accent = p[1]; c.skin = p[2]; c.public = true;
  });

  // The ads: our two top products, drawn bigger than a station so they are seen ("tyto reklamni budovy musi byt
  // vetsi nez normalni firmy") and smaller than the sun ("nic nesmi byt vetsi nez slunce"). A click flies to one and
  // opens its panel (uvpanel.js); the panel's button goes to the live page. accent: its plate's colour -- the gem green
  // as its logo, the casino the pink of its neon.
  // The ads are held back: the operator, 2026-10-21, "bod 5 zatim nepodavej, to podame az ve specu 3 az budu mit koupene
  // pozemky". They are built and drawn (u3d.js adGem, adCasino) but stand on the map only with ?ads in the address, so the
  // mockup the second spec points at does not show them.
  // Shown from 2026-10-22 (the operator bought their two slots); ?noads hides them, as round 2's pinned mockup did without ?ads.
  CO.ADS_ON = !/[?&]noads\b/.test(location.search);
  document.documentElement.classList.toggle('ads', CO.ADS_ON);
  CO.ADS = [
    // slot: the slot each stands on (CO.uvPlan puts it there): Orbit 2 · slot 4 and Orbit 4 · slot 2, the two the operator
    // bought, 2026-10-22. A click flies to it and opens its panel (uvpanel.js); url is that panel's Visit / Go play.
    { key: 'gem', name: 'Gem Screener', url: 'https://cymetica.com/gem-screener/app', accent: 'green', slot: 'slot-2-4' },
    { key: 'casino', name: 'Agent Casino', url: 'https://cymetica.com/agent-tournaments', accent: 'pink', slot: 'slot-4-2' },
    // the third he bought, 2026-10-22: GET /company/land lists it taken (slot-5-5) with no product on it yet
    { key: 'farmer', name: 'Airdrop Farmer', url: 'https://cymetica.com/airdrop-farmer', accent: 'gold', slot: 'slot-5-5' },
    // Cymetica's own building, not one of ours: the Promo Market, where a company hires creators, agents and firms to
    // promote its products (2026-10-22, "pridame do universa nejakou budovu kde si budem moct najimat sluzby ostatnich").
    // Its panel reads the market's own data (../promo-market/data.js), so the two pages say the same.
    { key: 'promo', name: 'Promo Market', url: 'https://cymetica.com/creator-dashboard', accent: 'cyan', slot: 'slot-5-3', house: true }
  ];
  // The land: a slot is bought with ET10, then built on through Build it Better. The price is a PLACEHOLDER (the
  // operator named the currency, not the amount); one number to change. What this browser bought, by slot id.
  CO.LAND_PRICE = 1000;
  // At most three slots to an account for now, so nobody buys the whole map up ("aby to nekdo nevykoupil vsechno",
  // 2026-10-21). One number; a slot the account holds already counts.
  CO.LAND_MAX = 3;
  CO.BUILD_URL = 'https://cymetica.com/build-it-better';
  var LKEY = 'co.land.v1';
  CO.land = function () {
    try { var a = JSON.parse(localStorage.getItem(LKEY) || '[]'); return Array.isArray(a) ? a : []; } catch (e) { return []; }
  };
  CO.landLeft = function () { return Math.max(0, CO.LAND_MAX - CO.land().length); };
  CO.buyLand = function (id) {
    var a = CO.land();
    if (CO.RO || a.indexOf(id) >= 0 || a.length >= CO.LAND_MAX) return a;
    a.push(id);
    try { localStorage.setItem(LKEY, JSON.stringify(a)); } catch (e) { /* the page still works, it just forgets */ }
    return a;
  };
  // One public company to look inside, for the visit view only (index.html?visit=101): the map holds no companies, but
  // the spec's visit has to be drawn once -- what a visitor sees of a public company, and what stays private.
  function d(key, o) { o = o || {}; o.key = key; return o; }
  function own(name, experts, charter, o) { o = o || {}; o.key = 'custom'; o.name = name; o.experts = experts; o.charter = charter; return o; }
  CO.VISITABLE = [
    { id: 101, name: 'Moonshot Labs', owner: '0xmila', public: true, status: 'active', plan: 'Max 5x', days: 12, skin: 'tower', accent: 'cyan',
      bugs: 6,
      mission: 'Find the next memecoin runner on paper before anyone else, and get paid in ET10 for every bug on the way.',
      departments: [d('testing', { runs: 2, products: ['Gem Screener', 'Supply Analyzer', 'Chart Analyzer'] }), d('testing_lab'), d('trading_desk'), d('development'), d('design'),
        own('Memecoin scouts', ['researcher', 'trader'], 'Watch the memecoin terminal for new launches.\n- A coin goes on the list only when the Gem Screener and the Supply Analyzer agree on its numbers.\n- Hand every promising coin to the Testing lab for a paper test. Never buy.')],
      rules: [['a bug is found anywhere', 'Cymetica QA', 'verifies it and files it'], ['someone finds a way to make money', 'Testing lab', 'proves it on paper first'],
        ['an experiment wins on paper', 'Trading desk', 'puts it into production once you approve: an Agent Tournaments seat or real money']] }
  ];
  CO.uvCompany = function (id) {
    var all = CO.UNIVERSE.concat(CO.VISITABLE);
    for (var i = 0; i < all.length; i++) if (all[i].id === id) return all[i];
    return null;
  };
  CO.uvEt10 = function (c) { return (c.bugs || 0) * 1000; };

  // The line a product shows in the Universe (under its name, in its tooltip and its panel), written by its owner on the
  // Products tab (the operator, 2026-10-22: "v products si chci umet editovat napis ktery se zobrazuje v univerzu, ted tam
  // pise blbost"). None until the owner writes one, so nothing is invented for him. Kept in this browser, by product name.
  var VKEY = 'co.uvline.v1';
  CO.UVLINE_MAX = 70;
  function uvLines() { try { return JSON.parse(localStorage.getItem(VKEY) || '{}') || {}; } catch (e) { return {}; } }
  CO.uvLine = function (name) { return String(uvLines()[String(name || '').toLowerCase()] || ''); };
  CO.setUvLine = function (name, text) {
    if (CO.RO) return;
    var m = uvLines(), k = String(name || '').toLowerCase(), t = String(text || '').replace(/\s+/g, ' ').trim().slice(0, CO.UVLINE_MAX);
    if (t) m[k] = t; else delete m[k];
    try { localStorage.setItem(VKEY, JSON.stringify(m)); } catch (e) { /* the page still works, it just forgets */ }
  };

  // The revenue share: every company ranked by the fees it brought Cymetica in the last 30 days (USD) -- the fees Cymetica
  // earned from the users and the volume the company's products brought (the operator, 2026-10-23: "top 3 firmy ktere cymetice
  // zajisti nejvetsi revenue"; first it was what the platform paid the company, bounties and prizes). Fees paid by the owner's
  // own accounts do not count. The top 3 at or above the floor get 5% / 3% / 1% of every fee on Cymetica, paid monthly in USDC;
  // a place nobody reaches stays empty. The floor and the fees are SAMPLES (Cymetica sets the terms); the figures all come from
  // this one model, so the board, the leaderboard and the pulse agree -- and what the companies brought adds up to about half
  // of the platform's fees, never more (scaled to 0.4 of the first samples, which summed past the platform's own total).
  CO.SHARE = [5, 3, 1];
  CO.SHARE_FLOOR = 10000;
  CO.PLATFORM_FEES_30D = 386000;
  // The first days ("spocatku tam urcite zadne nebudou firmy", 2026-10-23): nobody has reached the floor yet. ?board=empty
  // shows it: every company's revenue is what a young company earns, an eighth of these samples, all under the floor.
  CO.BOARD_LAUNCH = /[?&]board=empty\b/.test(location.search);
  CO.uvRevenue = function (c) {
    var R = CO.uvRng((+c.id || 0) * 13 + 7), u = R();
    var v = (Math.pow(u, 4) * 72000 + R() * 900) * 0.4;
    if (c.status === 'paused') v *= 0.35;
    if (CO.BOARD_LAUNCH) v *= 0.12;
    return Math.round(v / 10) * 10;
  };
  // SEASON 0 (the operator, 2026-10-28; Cymetica's build spec ET-33050, REPLY-0233): the same board, but a company's score is
  // POINTS for real use of its products in a calendar month, not revenue. Shown with ?season0 in the address; without it the
  // revenue-share board above is unchanged. The rules, as Cymetica wrote them:
  //   - an active user (a signed-in account that used a product on 2 different days in the month) = 10 points, +1 for every
  //     further active day, at most 20 per user per month;
  //   - a signed-out returning visitor (same IP hash on 2 days), only on products that work signed out: 1 point each, in total at
  //     most 25 % of the company's signed-in points;
  //   - the company's own trading agents: 1 point per 100 USDC of fee-paying traded volume, at most 30 % of the company's points;
  //   - the owner's own accounts and test accounts earn nothing; 100 points in the month to be placed; the top 3 are paid.
  // The caps are read as shares of the company's TOTAL (the agents' cap: pa <= 0.3 / 0.7 of users + visitors). Their answer
  // does not say whether the base is the total or the signed-in points: it is an open question in outbox/company-spec-5/SPEC.md.
  // The PRIZE is not in their answer; 50,000 / 30,000 / 10,000 ET10 is what they called a sensible range (REPLY-0229): a SAMPLE.
  // Every figure below is a sample drawn from one seeded model, so the board, the leaderboard and the pulses agree.
  CO.SEASON0 = /[?&]season0\b/.test(location.search);
  // The operator's decisions of 2026-10-29, which change Cymetica's wording (to be put to them, not yet sent): (1) the further days count from
  // the 3rd active day on (2 days = 10 points, 3 = 11, ..., 12 = 20); (2) NO cap on the trading agents' points, so a company that only trades
  // farms points too (the rule as written gave it 0); (3) every PRODUCT counts separately for a user: 10 points for each product the user uses
  // (the 20 cap is read per user per product: the operator did not say); (4) a visitor's 1 point per day or per month is left to Cymetica
  // (the sample counts it once a month). Visitors keep their 25 % cap of the signed-in points.
  CO.SEASON = { name: 'Season 1', month: 'November 2026', day: 12, days: 30, threshold: 100, prizes: [50000, 30000, 10000], cap: { visitors: 0.25 } };
  CO.uvPoints = function (c) {
    var R = CO.uvRng((+c.id || 0) * 17 + 3), K = CO.SEASON;
    var trader = R() < 0.22;                                       // a company that only trades: agents, no products, no users
    var users = trader ? 0 : Math.round(Math.pow(R(), 3.2) * 46 * (CO.BOARD_LAUNCH ? 0.12 : 1));
    if (c.status === 'paused') users = Math.round(users * 0.4);
    var uses = Math.round(users * (1 + R() * 1.4));                // user-product pairs: each user counts once for EACH product they use
    var per = Math.min(20, 10 + Math.max(0, Math.round(R() * 8) - 2));  // 10, +1 from the 3rd active day, at most 20
    var pu = uses * per;
    var visitors = trader ? 0 : Math.round(users * (0.5 + R() * 3));
    var pv = Math.min(visitors, Math.floor(pu * K.cap.visitors));
    var volume = Math.round(R() * R() * (trader ? 200000 : 60000) * (CO.BOARD_LAUNCH ? 0.12 : 1) / 100) * 100;   // fee-paying USDC volume of the company's own agents
    var pa = Math.floor(volume / 100);                             // 1 point per 100 USDC, no cap
    return { users: users, uses: uses, visitors: visitors, volume: volume, pu: pu, pv: pv, pa: pa, total: pu + pv + pa, trader: trader, capped: pv < visitors };
  };
  // the ranking, highest first; top: the first three at or above the floor (fewer when fewer reach it)
  CO.uvBoard = function (mine) {
    if (CO.SEASON0) {
      var K = CO.SEASON;
      var rs = CO.UNIVERSE.map(function (c) { return { c: c, p: CO.uvPoints(c), mine: false }; });
      if (mine) rs.push({ c: mine, p: CO.uvPoints(mine), mine: true });
      rs.sort(function (a, b) { return b.p.total - a.p.total || (a.c.id || 0) - (b.c.id || 0); });
      rs.forEach(function (r, i) { r.rank = i + 1; r.total = r.p.total; r.qualifies = r.total >= K.threshold; });
      var tp = rs.filter(function (r) { return r.qualifies; }).slice(0, K.prizes.length);
      tp.forEach(function (r, i) { r.prize = K.prizes[i]; });
      return { season: true, rows: rs, top: tp, prizes: K.prizes, floor: K.threshold, left: K.days - K.day };
    }
    var rows = CO.UNIVERSE.map(function (c) { return { c: c, rev: CO.uvRevenue(c), mine: false }; });
    if (mine) rows.push({ c: mine, rev: CO.uvRevenue(mine), mine: true });
    rows.sort(function (a, b) { return b.rev - a.rev || (a.c.id || 0) - (b.c.id || 0); });
    rows.forEach(function (r, i) { r.rank = i + 1; r.qualifies = r.rev >= CO.SHARE_FLOOR; });
    var top = rows.filter(function (r) { return r.qualifies; }).slice(0, CO.SHARE.length);
    top.forEach(function (r, i) { r.share = CO.SHARE[i]; r.month = Math.round(CO.PLATFORM_FEES_30D * CO.SHARE[i] / 100); });
    // what each place pays a month whoever holds it: an open seat shows what it is worth
    var pot = CO.SHARE.map(function (p) { return Math.round(CO.PLATFORM_FEES_30D * p / 100); });
    return { rows: rows, top: top, pot: pot, fees: CO.PLATFORM_FEES_30D, floor: CO.SHARE_FLOOR };
  };
})();

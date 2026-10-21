/* The /company mockup: seed data. One coherent company on the Pro plan, the shape
 * GET /api/v1/company/mine has, plus the task pools the simulated Manager plans from.
 * Times are offsets from the moment the page opens (the simulation's own clock). */
(function () {
  'use strict';
  var CO = window.CO = window.CO || {};
  var MIN = 60000, H = 60 * MIN;

  // The experts as Cymetica has them live, word for word (GET https://cymetica.com/api/v1/company/templates, read
  // 2026-10-19): what each does, its brief, the departments it fits, its tools and what it can and cannot do. The same
  // seven are live; every one of them waits for the owner before any trade, spend, publication or submission.
  var WEB = 'Can open and read public web pages (WebFetch).',
    NOWEB = 'Has no web tool: works from the task brief, the company memory and the finished work handed over by other departments.',
    ASKS = "Cannot place a trade, spend, publish or submit anything itself: such an action waits for the owner's approval.";
  CO.EXPERTS = [
    { key: 'qa_tester', name: 'QA tester', fits: ['testing', 'testing_lab', 'development'], tools: ['WebFetch'], capabilities: [WEB, ASKS],
      description: 'Tests Cymetica the way a stranger would, from public pages and the public API, and writes precise bug reports.',
      brief: 'You test Cymetica products the way a stranger would: only the public pages and public API. You write precise bug reports: what you did, what you expected, what happened, the URL.' },
    { key: 'researcher', name: 'Researcher', fits: ['development', 'testing_lab', 'trading_desk'], tools: ['WebFetch'], capabilities: [WEB, ASKS],
      description: 'Reads before anyone builds or trades: what exists, what users ask for, what the evidence says, with sources cited.',
      brief: 'You research before anyone builds or trades: what exists, what users ask for, what the evidence says. You cite the page you read and never state a number you did not read.' },
    { key: 'trader', name: 'Trader', fits: ['trading_desk', 'testing_lab'], tools: [], capabilities: [NOWEB, ASKS],
      description: 'Looks for repeatable ways to make money on Cymetica and turns each idea into a paper experiment with its success rule fixed first.',
      brief: 'You look for repeatable ways to make money on Cymetica and prove them on paper first. Every idea becomes a paper experiment with its success rule written before it starts.' },
    { key: 'developer', name: 'Developer', fits: ['development'], tools: [], capabilities: [NOWEB, ASKS],
      description: 'Turns an idea into a drafted Build it Better request with a clear spec; the owner approves before anything is submitted.',
      brief: 'You turn an idea into a Build it Better request: the app, what to improve, and a clear spec (idea, spec, design, build, test, release, monitor, iterate).' },
    { key: 'lab_scientist', name: 'Lab scientist', fits: ['testing_lab', 'trading_desk'], tools: [], capabilities: [NOWEB, ASKS],
      description: 'Designs paper experiments (one asset, one direction, a threshold and a window) judged later from real prices.',
      brief: 'You design paper experiments: one asset, one direction, a threshold and a window, fixed before the start. Results are judged later from real prices, never guessed.' },
    { key: 'auditor', name: 'Auditor', fits: ['testing', 'testing_lab', 'development', 'trading_desk', 'design'], tools: ['WebFetch'], capabilities: [WEB, ASKS],
      description: 'Department-level evidence review: sits inside one department and checks its finished work against the pages and data it cites before that work reaches NEXUS. Not the built-in weekly audit, which is the company-wide scheduled review by the built-in supervisor.',
      brief: "You review your department's finished work before it reaches NEXUS: check every claim against the page or data it cites, mark any number nobody read as unverified, name duplicated or wasted effort and stuck steps, and propose one concrete fix for each. You never pass work you could not verify." },
    { key: 'designer', name: 'Designer', fits: ['design', 'development'], tools: ['WebFetch'], capabilities: [WEB, ASKS],
      description: "Writes screen-by-screen design briefs and reviews live pages against their brief, within the site's own palette and type.",
      brief: "You design the look of a page or product: layout, hierarchy of copy, states, mobile first, within the site's own palette and type. You write a screen-by-screen brief a developer can build from, and you review a live page against its brief, pixel by pixel, naming each gap with the URL." }
  ];
  CO.expert = function (k) { for (var i = 0; i < CO.EXPERTS.length; i++) if (CO.EXPERTS[i].key === k) return CO.EXPERTS[i]; return null; };
  CO.expertName = function (k) {
    for (var i = 0; i < CO.EXPERTS.length; i++) if (CO.EXPERTS[i].key === k) return CO.EXPERTS[i].name;
    return k;
  };

  // The wizard's layout on the live page (build-company.js, LAYOUT), word for word -- except Testing, which the
  // spec renames "Cymetica QA": Cymetica's bug bounty as a department, filing as the owner (SPEC-NOTES.md).
  CO.TEMPLATES = [
    { key: 'development', name: 'Development', experts: ['developer', 'researcher'],
      charter: 'Build it Better as a department, from before to after the build: idea, spec, design, build, test, release, monitoring and iteration. Drafts Build it Better requests; submitting one waits for my approval.' },
    { key: 'design', name: 'Design studio', experts: ['designer', 'researcher'],
      charter: 'Design before and after the build: screen-by-screen briefs for new pages, and reviews of live pages against their brief. Briefs go out as Build it Better requests; submitting one waits for my approval.' },
    { key: 'testing', name: 'Cymetica QA', experts: ['qa_tester', 'auditor'],
      charter: "Cymetica's bug bounty, as my department. Test Cymetica's live products the way a stranger meets them: the page, its API and its docs.\n" +
        "- Reproduce every defect twice before calling it one; a failed read is not an empty read.\n" +
        "- File each bug straight into Cymetica's bug tracker (cymetica.com/leaderboard/bugs) under my hunter name and wallet, so every bug Cymetica accepts pays ET10 to me. Filing does not wait for my approval.\n" +
        "- Check the tracker first: a bug already reported is reopened on its ticket, never filed twice.\n" +
        "- Each report carries the exact page or request, what the docs promise, what happens instead, and the evidence.\n" +
        "- When Cymetica says a bug is fixed, test it again and post the verdict on the same ticket.\n" +
        "- Never file guesses, style nits or what could not be reproduced." },
    { key: 'testing_lab', name: 'Testing lab', experts: ['lab_scientist', 'researcher'],
      charter: 'Paper experiments on event cards, bot settings, memecoin signals and head-to-head. Asks NEXUS for strategies; sets the success rule before each experiment starts; judges it when the window closes; keeps winners and archives losers. Runs a daily newcomer check of the public site.' },
    { key: 'trading_desk', name: 'Trading desk', experts: ['trader', 'researcher'],
      charter: "Put the bots that won in the Quant Lab into production on Cymetica.\n" +
        "- Take only what passed in the lab's Experiments: its success rule met, its window closed.\n" +
        "- Seat each at an Agent Tournaments table (cymetica.com/agent-tournaments): a FLASH table (1 day) for a quick read, a 7-day table for the verdict. Or run it with a small real-money stake, its stop set first.\n" +
        "- Every seat and every stake waits for my approval; the company never places a real trade itself.\n" +
        "- Follow each one's rank, ROI and P&L. One that stops earning goes back to the lab with the reason." },
    { key: 'custom', name: '', experts: ['researcher'], charter: '' }
  ];
  // What a department of your own can look like: the owner picks one with the arrows round its room when creating it
  // (2026-10-19: "pro custom department tam budou sipky a budu si moct zvolit z ruznych vzhledu"); the department
  // keeps it as d.look. 'office' is the room a custom department always had.
  CO.ROOM_LOOKS = [
    { key: 'office', name: 'Office' },
    { key: 'ops', name: 'Operations room' },
    { key: 'library', name: 'Research library' },
    { key: 'workshop', name: 'Workshop' },
    { key: 'command', name: 'Command center' },
    { key: 'greenhouse', name: 'Greenhouse' }
  ];

  // Company rules: what anyone notices outside its own job goes where the rule says (the Manager routes it).
  // A company process is the owner's own words: when <something happens> -> a department -> does <what>.
  // The Manager reads which kind of situation the words describe; the owner never picks a type.
  CO.kindOf = function (text) {
    var t = String(text || '').toLowerCase();
    if (/(release|vyd[aá]|vyjde|new (build|product|version)|nov[yý] (produkt|build|verz)|deliver|dodaj|dod[aá])/.test(t)) return 'released';
    if (/(bug|chyb|broken|rozbit|error|problem)/.test(t)) return 'bug';
    if (/(win|vyhr|v[ií]t[eě]z|succeed|passes|usp[eě]|úsp[eě]|top (three|3)|first place|prvn[ií] m[ií]st)/.test(t)) return 'winner';
    if (/(idea|n[aá]pad|feature|improve|vylep)/.test(t)) return 'idea';
    if (/(money|vyd[eě]l|profit|zisk|earn)/.test(t)) return 'money';
    if (/(look|design|vzhled|ugly|layout|ui\b)/.test(t)) return 'design';
    return 'custom';
  };
  // What /company meters is units, and it prices them 1:1 in dollars: a department's cost_usd_7d equals its
  // units_7d (GET /api/v1/company/mine, 2026-10-17: 0.5338 and 0.533771; 0.186 a turn on our company).
  // It shows no tokens, so neither does the mockup: a department's spend is in dollars.
  CO.TOK = 1;
  CO.fmtTok = function (n) { return '$' + (+n || 0).toFixed(2); };
  // the daily caps the owner can pick, in dollars of plan, last one none
  CO.CAP_STEPS = [0.25, 0.5, 1, 1.5, 2, 3, 5, null];
  // a clock's run times, by runs a day
  CO.RUN_TIMES = { 1: ['10:00'], 2: ['09:00', '21:00'], 3: ['08:00', '14:00', '20:00'], 4: ['00:00', '06:00', '12:00', '18:00'],
    5: ['00:00', '05:00', '10:00', '15:00', '20:00'], 6: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00'],
    12: ['00:00', '02:00', '04:00', '06:00', '08:00', '10:00', '12:00', '14:00', '16:00', '18:00', '20:00', '22:00'] };
  // the owner's bug-bounty hunter name: what Cymetica QA files as, and where its ET10 goes
  CO.HUNTER = 'expire76';
  // each department's computer opens its page on cymetica.com
  CO.DEPT_LINK = {
    testing: { url: 'https://cymetica.com/leaderboard/bugs?filter=mine', label: 'Bug board · My Bugs' },
    development: { url: 'https://cymetica.com/leaderboard/features', label: 'Build it Better board' },
    design: { url: 'https://cymetica.com/leaderboard/features', label: 'Build it Better board' },
    testing_lab: { url: 'experiments.html', label: 'Experiments: what we try and how it goes' },
    trading_desk: { url: 'https://cymetica.com/my-agents', label: 'My bots' },
    custom: { url: 'https://cymetica.com/company', label: 'Company' }
  };
  // the pages beyond the first, for a department with more than one (the operator, 2026-10-20: "trading desk ... bude
  // mit dva, na My bots a i na agent tournaments")
  CO.DEPT_LINK_MORE = { trading_desk: [{ url: 'https://cymetica.com/agent-tournaments', label: 'Agent Tournaments' }] };
  // what a department's work usually raises next, so a process can show what it leads to
  CO.EMITS = { development: 'released', testing_lab: 'winner', design: 'idea', trading_desk: null, testing: null, custom: null };
  // starting points the owner can click into the form; never added on their own
  CO.RULE_EXAMPLES = [
    ['a bug is found anywhere', 'testing', 'verifies it and files the report as expire76'],
    ['a new build is released', 'testing', 'tests it the same day and reports what is broken'],
    ['someone has a product idea', 'development', 'writes it up as a Build it Better request'],
    ['someone finds a way to make money', 'testing_lab', 'proves it on paper first'],
    ['an experiment wins on paper', 'trading_desk', 'puts it into production once you approve: an Agent Tournaments seat or real money']
  ];

  // GET /api/v1/token-launch/chains, read 2026-10-16.
  CO.CHAINS = [{ key: '4663', name: 'Robinhood Chain', currency: 'ETH' }, { key: '5042', name: 'Arc', currency: 'USDC' },
    { key: 'sui', name: 'Sui', currency: 'SUI' }];

  CO.ERRORS = ['no answer', 'timeout reading /api/v1/gem-screener/picks', 'tool refused: write not allowed',
    'page did not render in 30 s', 'NEXUS busy, try later'];

  // What the Manager plans from, per kind of department. kind = what the result waits on.
  CO.POOL = {
    development: [
      { title: 'Supply Analyzer: staking & locks request', kind: 'BB request', turns: 2, expert: 'developer',
        outcome: 'Draft: 9 lines, 2 pictures', why: 'from the Supply Analyzer notes' },
      { title: 'Chart Analyzer: check the one-number build', turns: 1, expert: 'developer',
        outcome: 'Score matches its study on 18 of 20 coins', why: 'delivery claimed this morning' },
      { title: 'Chart Analyzer v3: diff their BB-SPEC', turns: 1, expert: 'researcher',
        outcome: '24 of 24 lines word for word', why: 'their spec arrived' },
      { title: 'Gem Screener: the four Guardians to add', kind: 'BB request', turns: 2, expert: 'developer',
        outcome: 'Draft: Who holds it, Fake volume, Insider flow, Whales', why: 'token-movement analyzer is live' }
    ],
    design: [
      { title: 'Brief: Trading Station on a phone', turns: 2, expert: 'designer', outcome: '6 screens at 390 px',
        why: 'the phone view is open in their tracker' },
      { title: 'Review: Gem Screener lobby vs its brief', turns: 1, expert: 'designer',
        outcome: '2 gaps: strip height, chip colour', why: 'build went live at 14:10' },
      { title: 'Review: /company office at 1440', turns: 1, expert: 'designer', outcome: 'Labels 3-5 px; office height-limited',
        why: 'you asked for it' }
    ],
    testing: [
      { title: 'Gem Screener: holders vs the chain', kind: 'bug report', turns: 1, expert: 'qa_tester',
        outcome: 'Holders 4,812 on the page, 4,129 on chain', why: 'a degen asked in the chat' },
      { title: 'Doc vs behaviour: /llms.txt routes', turns: 1, expert: 'qa_tester', outcome: '31 routes documented, 1 answers 404',
        why: 'llms.txt changed today' },
      { title: 'Supply Analyzer: circulating supply, 10 coins', turns: 2, expert: 'auditor',
        outcome: '9 of 10 match within 1%', why: 'weekly rhythm' },
      { title: 'Verify fix: #198 OpenAPI routes', turns: 1, expert: 'auditor', outcome: 'Still missing: 12 routes',
        why: 'they claimed a fix' }
    ],
    testing_lab: [
      { title: 'Ask NEXUS: next three strategies', turns: 1, expert: 'lab_scientist', outcome: '3 rooms opened on paper',
        why: 'two rooms closed today' },
      { title: 'Paper: Hot basket, 12h exit', turns: 1, expert: 'lab_scientist', outcome: 'Window open; rule: beat BTC by 1%',
        why: "NEXUS's pick" },
      { title: 'Newcomer check of the public site', turns: 1, expert: 'researcher', outcome: '0 broken links, 1 slow page (4.2 s)',
        why: 'daily' },
      { title: 'Bot variant: ET10 grid, tighter stop', turns: 2, expert: 'lab_scientist', outcome: 'Archived: -0.8% vs parent',
        why: 'parent bot won 3 windows' }
    ],
    trading_desk: [
      { title: 'Seat: Fibonacci Phoenix at a FLASH $5 table', kind: 'seat request', turns: 1, expert: 'trader',
        outcome: 'Waits for you', why: 'won its window in the lab' },
      { title: 'Follow the seats: 2 tables running', turns: 1, expert: 'researcher', outcome: 'Phoenix 3rd at table 13, +2.4% ROI, day 4 of 7',
        why: 'every 6 hours while a table runs' },
      { title: 'Real trade: ET10 grid, 50 USDC, stop -5%', kind: 'real-money action', turns: 1, expert: 'trader',
        outcome: 'Waits for you', why: 'won 3 paper windows of 3 in the lab' },
      { title: 'Back to the lab: Momentum Hawk', turns: 1, expert: 'researcher', outcome: '4th of 10 twice: off the tables, the reason kept',
        why: 'out of the top three two tables running' }
    ],
    custom: [
      { title: 'Read the charter and propose a first week', turns: 1, expert: null, outcome: '5 tasks proposed',
        why: 'new department' },
      { title: 'First pass: what this department can do today', turns: 1, expert: null, outcome: '3 quick wins found',
        why: 'follows the first week' }
    ]
  };

  // What a finished task teaches its department, now and then (memory, by kind).
  CO.LESSONS = {
    development: [['lesson', 'A spec names the goal; the picture is the template, not the method.'],
      ['knows', 'Build it Better specs carry 8,000 characters and up to six pictures.']],
    design: [['lesson', 'Numbers before words; an explanation goes in a tooltip.'],
      ['knows', 'The owner reads at ~2,000 px; check 1920 and 1440 before calling it done.']],
    testing: [['mistake', 'A failed read is not an empty read: retry before calling a field missing.'],
      ['lesson', 'File with the exact request and the capture, never a paraphrase.']],
    testing_lab: [['lesson', 'A correct number can be untradeable: read the pool depth first.'],
      ['rule', 'The success rule is set before the window opens, never after.']],
    trading_desk: [['rule', 'A seat only for a paper record: ROI after fees over 30 days, 40+ trades.'],
      ['lesson', 'A FLASH day is a quick read; only a 7-day table is a verdict.'],
      ['knows', 'A table ranks by ROI on closed trades; under 3x capital in volume it does not place.']],
    custom: [['knows', 'Every task starts from the saved charter.']]
  };

  function draft(kind, title, dept) {
    if (kind === 'bug report') {
      return 'BUG REPORT · drafted by ' + dept + '\n\nTitle\n' + title +
        '\n\nWhere\nGET https://cymetica.com/openapi-public.json (read just now)' +
        '\n\nWhat the docs say\n/llms.txt lists /api/v1/company/mine and 11 more Company routes.' +
        '\n\nWhat happens instead\nNone of the 12 appear in the OpenAPI document; an agent that builds from it cannot find the Company API.' +
        '\n\nEvidence\nCapture 0a775df1 (request, response, time).' +
        '\n\nReward\n1,000 ET10 if verified and not a duplicate.\n\nSubmitted only after your approval.';
    }
    if (kind === 'seat request') {
      var who = title.replace(/^Seat: /, '').split(' at ')[0], where = title.split(' at ').slice(1).join(' at ') || 'a paper table';
      return 'SEAT REQUEST · drafted by ' + dept + '\n\nAgent\n' + who +
        '\n\nTable\n' + where + ' at cymetica.com/agent-tournaments · 10 seats · paper buy-in · best ROI takes the pot' +
        '\n\nWhy this agent\n30-day paper ROI +6.2% after fees, 48 trades, worst drawdown -3.1%.' +
        '\n\nWhat counts\nTop three at the close: keep it and enter the next 7-day table. Otherwise it is archived with the reason.' +
        '\n\nIf you approve\nThe seat is requested and approved in your name. Paper only: nothing real is spent.';
    }
    if (kind === 'real-money action') {
      return 'REAL-MONEY ACTION · drafted by ' + dept + '\n\nWhat\n' + title +
        '\n\nWhy\nOn paper the basket beat BTC in 3 windows of 3 (+1.1%, +0.7%, +2.0% after costs).' +
        '\n\nLimits\n50 USDC, one window (6h), stop at -5%.\n\nNothing is spent until you approve.';
    }
    return 'BUILD IT BETTER REQUEST · drafted by ' + dept + '\n\nTitle\n' + title +
      '\n\n1. Every parent app in the Gem Screener shows its own logo beside its name.' +
      '\n2. A coin without a known parent shows the chain logo, never a blank square.' +
      '\n3. Logos load from the app\'s own domain; no third-party tracker.' +
      '\n\nDone when\n[ ] 41 of 41 parent apps show a logo.\n[ ] No blank squares on the first 100 rows.' +
      '\n\nSubmitted only after your approval.';
  }
  CO.draft = draft;

  function nextSat16(t) {
    var d = new Date(t);
    var add = (6 - d.getDay() + 7) % 7;
    d.setDate(d.getDate() + add); d.setHours(16, 0, 0, 0);
    if (d.getTime() <= t) d.setDate(d.getDate() + 7);
    return d.getTime();
  }

  CO.seed = function (t0) {
    var at = function (min) { return t0 + min * MIN; };
    var depts = [
      { id: 1, key: 'development', slot: 0, name: 'Development', experts: ['developer', 'researcher'],
        units_7d: 1.10, failed_7d: 0, charter_updated_at: at(-26 * 60) },
      { id: 2, key: 'design', slot: 1, name: 'Design studio', experts: ['designer', 'researcher'],
        units_7d: 0.44, failed_7d: 0, charter_updated_at: at(-26 * 60) },
      { id: 3, key: 'testing', slot: 2, name: 'Cymetica QA', experts: ['qa_tester', 'auditor'], files_as: 'expire76',
        et10: 3000, accepted: 3, units_7d: 0.66, failed_7d: 1, charter_updated_at: at(-21 * 60) },
      { id: 4, key: 'testing_lab', slot: 3, name: 'Testing lab', experts: ['lab_scientist', 'researcher'],
        units_7d: 0.66, failed_7d: 1, charter_updated_at: at(-26 * 60) },
      { id: 5, key: 'trading_desk', slot: 4, name: 'Trading desk', experts: ['trader', 'researcher'],
        units_7d: 0.22, failed_7d: 0, charter_updated_at: at(-26 * 60) }
    ];
    var today = [0.62, 0.21, 0.48, 0.35, 0.12];
    depts.forEach(function (d, i) {
      var tpl = CO.TEMPLATES.filter(function (t) { return t.key === d.key; })[0];
      d.charter = tpl.charter;
      d.pool_i = 0;
      d.tok_day = new Date(t0).toDateString(); d.tok_today = today[i]; d.turns_today = Math.round(today[i] / 0.19); d.cap_day = null;
    });

    function T(id, dept, title, status, o) {
      var t = { id: id, dept_id: dept, title: title, status: status, attempt: 1, max_attempts: 3, turns: 0,
        turns_needed: 1, units: 0, created_at: at(-90), started_at: null, finished_at: null, outcome: '',
        last_error: '', next_attempt_at: null, kind: null, why: '', expert: null,
        brief: '' };
      for (var k in o) t[k] = o[k];
      if (!t.brief) t.brief = title + '. Start from the charter; report what you found in one line, with the evidence.';
      return t;
    }
    var tasks = [
      T(20, 5, 'Read what Cymetica pays: ET10, cards, bounty', 'done', { turns: 1, units: 0.22, started_at: at(-300), finished_at: at(-296), outcome: 'Bounty 1,000 ET10 a bug; cards pay on settlement; League puzzles 1,000-10,000 ET10', expert: 'researcher' }),
      T(21, 4, 'Newcomer check of the public site', 'done', { turns: 1, units: 0.18, started_at: at(-280), finished_at: at(-276), outcome: '0 broken links, 2 slow pages', expert: 'researcher' }),
      T(22, 2, 'Brief: /company owner view at 1440', 'done', { turns: 1, units: 0.24, started_at: at(-250), finished_at: at(-246), outcome: '1 screen: counter, office, approvals, plan, chat', expert: 'designer' }),
      T(23, 4, 'Ask NEXUS: three strategies for this week', 'done', { turns: 1, units: 0.16, started_at: at(-230), finished_at: at(-226), outcome: '3 rooms: FOMO >=70, ETH card 6h, Hot basket', expert: 'lab_scientist' }),
      T(24, 1, 'Spec: Chart Analyzer one-number score', 'done', { turns: 2, turns_needed: 2, units: 0.42, started_at: at(-220), finished_at: at(-200), outcome: '13 lines, 3 pictures; filed', expert: 'developer' }),
      T(25, 3, 'Read bug bounty scope and rules', 'done', { turns: 1, units: 0.21, started_at: at(-150), finished_at: at(-146), outcome: 'In scope: contracts, web UI, REST API, data accuracy, mobile, docs', expert: 'qa_tester' }),
      T(26, 2, 'Review: Gem Screener detail vs its brief', 'done', { turns: 1, units: 0.20, started_at: at(-140), finished_at: at(-136), outcome: '4 of 5 match; Guardians ring is 2 px off', expert: 'designer' }),
      T(27, 1, 'Gem Screener: read the parent-app list', 'done', { turns: 1, units: 0.22, started_at: at(-120), finished_at: at(-116), outcome: '41 apps; 9 without a logo', expert: 'researcher' }),
      T(28, 3, 'Inventory testable surface from llms.txt', 'done', { turns: 1, units: 0.25, started_at: at(-31), finished_at: at(-27), outcome: 'Public no-auth GETs: /gem-screener/picks, /prop/config, /agent-league/puzzles and 41 more', expert: 'qa_tester' }),
      T(29, 1, 'Supply Analyzer: what is known about locks', 'done', { turns: 1, units: 0.24, started_at: at(-100), finished_at: at(-96), outcome: 'Staking and locks known for 68 of 244 coins', expert: 'researcher' }),
      T(30, 1, 'Chart Analyzer v3: score history spec', 'done', { turns: 1, units: 0.22, started_at: at(-80), finished_at: at(-76), outcome: '13 lines, 6 pictures', expert: 'developer' }),
      T(31, 3, 'Doc vs behaviour: public pages', 'running', { outcome_text: 'Found 3 mismatches: /prop/config, /llms.txt, /gem-screener', turns: 1, attempt: 2, units: 0.20, started_at: at(-25), last_error: 'no answer', expert: 'qa_tester', why: 'retry after no answer' }),
      T(32, 4, 'Paper: ETH event card, 6h exit', 'done', { turns: 1, units: 0.17, started_at: at(-60), finished_at: at(-56), outcome: 'Archived: -2.1% after costs (rule was > 0)', expert: 'lab_scientist' }),
      T(33, 1, 'Gem Screener: parent-app logos', 'waiting_approval', { turns: 1, units: 0.24, kind: 'BB request', started_at: at(-9), finished_at: at(-5), expert: 'developer', outcome: 'Draft ready: 3 lines, 2 checks' }),
      T(34, 4, 'Paper: FOMO >=70, 24h exit', 'running', { outcome_text: 'Window open: 11 cards, rule > 0 after costs', turns: 0, units: 0, started_at: at(-1), expert: 'lab_scientist', why: "NEXUS's pick" }),
      T(35, 3, '/api/v1/company routes missing from /openapi-public.json', 'done', { turns: 1, units: 0.23, kind: 'bug report', started_at: at(-6), finished_at: at(-2), expert: 'auditor', outcome: 'Filed #214 as expire76: 12 routes missing' }),
      T(36, 3, 'Chart Analyzer score vs its study', 'queued', { outcome_text: 'Score off by 0.4 on 2 of 20 coins', turns_needed: 2, why: 'you asked for it at ' + hhmm(at(-17)), expert: 'qa_tester', created_at: at(-16) }),
      T(37, 4, 'FOMO >=70, 24h exit: verdict', 'queued', { outcome_text: 'Kept: +2.4% after costs on 11 cards', why: 'its window closed', expert: 'lab_scientist', created_at: at(-16) }),
      T(38, 1, 'Gem Screener logos: submit after approval', 'queued', { blocked_by: 33, outcome_text: 'Submitted as ET-31502', why: 'waits on your approval first', expert: 'developer', created_at: at(-5) }),
      T(39, 5, 'Scan: agents by 30-day paper ROI', 'queued', { outcome_text: '3 candidates: +4% or more after fees, 40+ trades', turns_needed: 2, why: 'the daily scan', expert: 'researcher', created_at: at(-40) })
    ];
    // the two running turns end soon after the page opens, so it moves at once
    tasks.forEach(function (t) {
      if (t.status === 'running') { t.turn_started = at(-0.4); t.ends_at = t0 + (t.id === 31 ? 7000 : 13000); }
    });
    tasks[11].fail_next = false;

    var approvals = [
      { id: 'A2', task_id: 33, dept_id: 1, kind: 'BB request', summary: 'Gem Screener: parent-app logos', created_at: at(-5) }
    ];
    approvals.forEach(function (a) {
      var d = depts.filter(function (x) { return x.id === a.dept_id; })[0];
      a.body = draft(a.kind, a.summary, d.name);
    });

    var memory = [
      [3, 'knows', 'Bounty pays a flat 1,000 ET10 per verified, non-duplicate bug.'],
      [3, 'knows', 'In scope: contracts, web UI, REST API, data accuracy, mobile, docs.'],
      [3, 'mistake', 'A failed read is not an empty read: retry before calling a field missing.'],
      [3, 'lesson', 'File with the exact request and the capture, never a paraphrase.'],
      [3, 'rule', 'Test only what is documented and visible today.'],
      [3, 'knows', '/openapi-public.json has no /api/v1/company routes.'],
      [4, 'rule', 'The success rule is set before the window opens, never after.'],
      [4, 'lesson', 'A correct number can be untradeable: read the pool depth first.'],
      [4, 'mistake', "Judged a card at its current index, not at its settlement."],
      [4, 'knows', 'NEXUS answers one strategy per question; ask for three.'],
      [4, 'lesson', "A 'none' after an answer is the verdict, not 'next cycle'."],
      [4, 'knows', 'Paper rooms close at their window; the verdict is due then.'],
      [4, 'rule', 'Keep winners, archive losers; never re-run a loser unchanged.'],
      [4, 'knows', 'FOMO score >= 70 fired 11 times this week.'],
      [4, 'lesson', 'A check on a rotating population is sampling.'],
      [1, 'knows', 'Build it Better specs carry 8,000 characters and up to six pictures.'],
      [1, 'lesson', 'Goals, not methods: the picture is the template, the spirit is the requirement.'],
      [1, 'rule', 'Palette: cyan, green, red, blue, slate. No purple, orange, amber, yellow or gray.'],
      [1, 'mistake', 'Drew extras nobody asked for (Elo, last 5); draw only what was asked.'],
      [1, 'knows', 'Their BB-SPEC must carry every line word for word before BB-ACCEPT.'],
      [1, 'lesson', 'An approved plan is built whole, not phase by phase across sessions.'],
      [1, 'knows', 'Gem Screener lists 41 parent apps; 9 have no logo.'],
      [1, 'knows', 'Supply Analyzer knows staking and locks for 68 of 244 coins.'],
      [1, 'rule', 'Every spec is checked line by line against their BB-SPEC.'],
      [1, 'knows', 'The owner view is feature #911 (ET-30909).'],
      [1, 'lesson', 'Read the vendor design rule before drawing.'],
      [1, 'knows', 'Build it Better specs carry up to six pictures.'],
      [2, 'lesson', 'Numbers before words; an explanation goes in a tooltip.'],
      [2, 'knows', 'The owner reads at ~2,000 px; check 1920 and 1440 before calling it done.'],
      [2, 'mistake', 'Shipped a panel of paragraphs; it was read as 2/10.'],
      [2, 'rule', 'Fonts: JetBrains Mono and Archivo Black.'],
      [2, 'knows', 'Site colours: #0a0e17 ground, green #00ff88, cyan #00cfff, red #ff4444.'],
      [5, 'rule', 'Paper first; any real-money action waits for approval.'],
      [5, 'knows', 'NEXUS supplies the guidance; we test and execute.'],
      [5, 'lesson', 'A +3.9% basket can hide a -0.04% card; read the card it would buy.'],
      [5, 'knows', 'A card round trip costs about 1.4%.']
    ].map(function (m, i) { return { id: i + 1, dept_id: m[0], kind: m[1], text: m[2], at: at(-600 + i * 7) }; });

    var strip = [];
    'ddddfdddf'.split('').forEach(function (c, i) {
      strip.push({ state: c === 'd' ? 'done' : 'failed', at: at(-300 + i * 30), dept_id: [5, 4, 2, 4, 1, 3, 2, 1, 3][i] });
    });
    strip.push({ state: 'running', at: at(-0.4), dept_id: 3, task_id: 31 });
    strip.push({ state: 'running', at: at(-0.4), dept_id: 4, task_id: 34 });

    return {
      clock: t0,
      company: { id: 13, name: 'My Company', mission: 'Find what is broken on Cymetica, prove what makes money there, and get paid in ET10 for both.',
        report_style: 'Short, numbers first', status: 'active', plan: 'Pro', investable: false, created_at: at(-3 * 24 * 60) },
      budget: {
        session: { used: 0.34, cap: 1.00, resets_at: t0 + 4 * H + 28 * MIN, every: 5 * H },
        week: { used: 4.46, cap: 6.00, resets_at: nextSat16(t0), every: 7 * 24 * H },
        extra: { on: true, left: 4.62, usdc_per_unit: 1.0, month_cap: 25 },
        cap: 40
      },
      meter: [0.12, 0.21, 0.32, 0.22, 0.18, 0.24, 0.20, 0.25, 0.21, 0.17, 0.24, 0.23, 0.22, 0.25, 0.20, 0.24, 0.22, 0.16, 0.23, 0.24],
      strip: strip,
      next_pass_at: t0 + 18000,
      departments: depts,
      tasks: tasks,
      plan: [36, 37, 38, 39],
      approvals: approvals,
      decided: [],
      approved_7d: 0,
      messages: [
        { id: 1, role: 'manager', text: 'Starting with scope and surface mapping; nothing is submitted until you approve.', at: at(-34), answered: true },
        { id: 2, role: 'owner', text: 'Chart Analyzer and Gem Screener first.', at: at(-17), answered: true },
        { id: 3, role: 'manager', text: 'Queued 2 tasks for Cymetica QA, 1 for the Lab.', at: at(-16), answered: true }
      ],
      notice: null,
      typing: false,
      feed: [
        { kind: 'good', dept: 'Cymetica QA', text: 'filed #214 as expire76: /api/v1/company routes missing from /openapi-public.json', at: at(-2) },
        { kind: 'ask', dept: 'Development', text: 'asks approval: BB request', at: at(-5) },
        { kind: 'info', dept: 'Testing lab', text: 'opened paper: FOMO >=70, 24h exit', at: at(-12) },
        { kind: 'bad', dept: 'Cymetica QA', text: '"Doc vs behaviour" failed (no answer), retrying', at: at(-16) },
        { kind: 'good', dept: 'Cymetica QA', text: 'finished "Inventory testable surface"', at: at(-27) }
      ],
      memory: memory,
      audit: {
        next_at: at(6 * 24 * 60 - 30),
        last: { at: at(-24 * 60), findings: [
          { kind: 'duplicate', detail: 'Cymetica QA and Development both read /llms.txt the same hour (2 turns).', fix: 'Cymetica QA owns the surface map; Development reads its result.' },
          { kind: 'stuck', detail: 'Task #31 waited 51 min past its retry time while the company was paused.', fix: 'Resume, or remove it from the plan.' },
          { kind: 'wasted', detail: 'A 2-turn spec was redone after a charter change mid-task.', fix: 'Save the charter between tasks, not during one.' }
        ] }
      },
      legal: { domicile: 'Cayman Islands', name: 'My Company Ltd.', formed: false },
      rules: [
        { id: 'R1', on: true, when: 'a bug is found anywhere', dept_id: 3, does: 'verifies it and files the report as expire76', fired: 0 },
        { id: 'R2', on: true, when: 'a new build is released', dept_id: 3, does: 'tests it the same day and reports what is broken', fired: 0 },
        { id: 'R3', on: true, when: 'someone has a product idea', dept_id: 1, does: 'writes it up as a Build it Better request', fired: 0 },
        { id: 'R4', on: true, when: 'someone finds a way to make money', dept_id: 4, does: 'proves it on paper first', fired: 0, review: 'result', reviewer: 'you' },
        { id: 'R5', on: true, when: 'an experiment wins on paper', dept_id: 5, does: 'puts it into production once you approve: an Agent Tournaments seat or real money', fired: 0, review: 'start', reviewer: 'you' }
      ], next_rule: 6,
      token: { chain: '5042', symbol: '', reserved: false, perp_listed: false },
      next_id: 40, next_msg: 4, next_appr: 3, next_mem: memory.length + 1, next_dept: 6,
      et10: 3000, next_report: 215
    };
  };

  // A company with nothing in it yet: no departments, no history, no measured turn. The
  // default start; ?demo opens the busy company above.
  CO.seedEmpty = function (t0) {
    var s = CO.seed(t0);
    s.departments = []; s.tasks = []; s.plan = []; s.approvals = []; s.decided = []; s.memory = [];
    s.messages = []; s.feed = []; s.strip = []; s.meter = []; s.approved_7d = 0;
    s.budget.session.used = 0; s.budget.week.used = 0;
    s.audit = { next_at: t0 + 7 * 24 * H, last: null };
    s.company.created_at = t0;
    s.next_pass_at = t0 + 30000;
    s.next_id = 1; s.next_msg = 1; s.next_appr = 1; s.next_mem = 1; s.next_dept = 1;
    s.rules = []; s.next_rule = 1;
    s.et10 = 0; s.next_report = 214;
    return s;
  };
  // Our own company, the one that runs locally today, set up the new way: the departments, their charters,
  // clocks and products, and the processes between them. No history: it starts now and the simulation runs it.
  CO.OURS = {
    mission: 'Find what is broken on Cymetica and get paid in ET10 for it, find what makes money there on paper, and put the bots that win into production.',
    departments: [
      { key: 'testing', name: 'Cymetica QA', experts: ['qa_tester', 'auditor'], runs: 2,
        products: ['Build it Better', 'Fund Launcher', 'Gem Screener', 'Supply Analyzer', 'Chart Analyzer'] },
      { key: 'testing_lab', name: 'Quant Lab', experts: ['lab_scientist', 'researcher'],
        charter: "Prove on paper what makes money on Cymetica.\n" +
          "- Ask NEXUS first: their AI gives the guidance on what to trade; our own ideas are tried and measured, never trusted ahead of it.\n" +
          "- Rooms on paper: event cards, cloned bots, grid, head-to-head, memecoins.\n" +
          "- Set the success rule before a room opens; judge it when its window closes.\n" +
          "- Keep the winners, archive the losers with the reason.\n" +
          "- Paper only. Anything with real money waits for my approval." },
      { key: 'trading_desk', name: 'Trading desk', experts: ['trader', 'researcher'] }
    ],
    rules: [
      ['a bug is found anywhere', 'Cymetica QA', 'verifies it and files it as expire76'],
      ['a new build is released', 'Cymetica QA', 'tests it the same day and reports what is broken'],
      ['someone finds a way to make money', 'Quant Lab', 'proves it on paper first'],
      ['an experiment wins on paper', 'Trading desk', 'puts it into production once you approve: an Agent Tournaments seat or real money']
    ]
  };
  // The departments a pre-built company starts with (builder.html's Pre-build and its tour read this list): the
  // Quant Lab with our own charter, NEXUS first; the others as their templates have them.
  CO.PREBUILD = [{ key: 'testing', name: 'Cymetica QA' }, { key: 'development', name: 'Development' }]
    .concat(CO.OURS.departments.filter(function (d) { return d.key === 'testing_lab'; }))
    .concat([{ key: 'trading_desk', name: 'Trading desk' }]);
  // Which company this page shows. Ours by default; ?demo the busy example; ?empty a blank one; ?new the
  // "Create your company" step first; ?visit=<id> someone else's public company, read only. Parsed as
  // parameters, never as a substring: a company name in the address must not switch the mode.
  var Q = new URLSearchParams(location.search), HASH = location.hash.slice(1);
  CO.ME = 'expire76';
  CO.MODE = Q.has('visit') ? 'visit' : Q.has('demo') || HASH === 'demo' ? 'demo' : Q.has('empty') || HASH === 'empty' ? 'empty' : Q.has('new') ? 'new' : 'ours';
  CO.Q = Q;
  // a visit opens only a public company; anything else falls back to our own, saying why
  function resolveVisit() {
    if (CO.MODE !== 'visit' || CO.VISIT !== undefined) return;
    var c = CO.uvCompany ? CO.uvCompany(+Q.get('visit')) : null;
    CO.VISIT = c && c.public ? c : null;
    if (CO.VISIT) { CO.RO = true; CO.HUNTER = c.owner; }
    else {
      CO.MODE = 'ours'; CO.denied = c ? c.name + ' is private: only its owner can look inside.' : 'No such company.';
      // said once: the refused visit leaves the address, so a reload is simply our own company
      try { history.replaceState(null, '', location.pathname + location.hash); } catch (e) { /* fine */ }
    }
  }
  var PLAN_UNITS = { 'Pro': [1, 6], 'Max 5x': [5, 30], 'Max 20x': [20, 120] };
  CO.fresh = function (t0) {
    resolveVisit();
    if (CO.MODE === 'visit') {
      var V = CO.VISIT, v = CO.seedEmpty(t0), u = PLAN_UNITS[V.plan] || PLAN_UNITS.Pro;
      v.company = { id: V.id, name: V.name, mission: V.mission, report_style: 'Short, numbers first', status: V.status, plan: V.plan,
        investable: false, created_at: t0 - (V.days || 0) * 24 * H - 3 * H, owner: V.owner, public: true, skin: V.skin, accent: V.accent };
      v.budget.session.cap = u[0]; v.budget.week.cap = u[1];
      v.legal.name = V.name + ' Ltd.';
      v.setup = 'visit';
      return v;
    }
    var me = CO.profile ? CO.profile() : { name: 'My Company', mission: '' };
    var s = CO.MODE === 'demo' ? CO.seed(t0) : CO.seedEmpty(t0);
    s.company.name = me.name; s.company.owner = CO.ME;
    if (CO.MODE === 'ours') { s.setup = 'ours'; s.company.mission = CO.OURS.mission; }
    if (CO.MODE === 'empty' && me.prebuild === 'starter') s.setup = 'starter';
    if (me.mission) s.company.mission = me.mission;
    s.legal.name = me.name + ' Ltd.';
    return s;
  };

  // Each department's icon, drawn to its room in the office ("pridej hezke ikonky i zde k departmentum, podle toho
  // jaky skin mistnosti delas, at je to sladene", 2026-10-19): Development's code, the Design studio's pen, Cymetica
  // QA's bug, the Testing lab's flask, the Trading desk's candles, NEXUS's core with its rings, and for a
  // department of one's own the look its room has. Line icons in the site's colours, as the tabs' are.
  var DEPT_ICON = {
    hub: ['#00cfff', '<circle cx="10" cy="10" r="2.4" fill="currentColor"/><ellipse cx="10" cy="10" rx="7.6" ry="2.9"/><ellipse cx="10" cy="10" rx="7.6" ry="2.9" transform="rotate(60 10 10)"/><ellipse cx="10" cy="10" rx="7.6" ry="2.9" transform="rotate(-60 10 10)"/>'],
    development: ['#00cfff', '<rect x="2.5" y="3.5" width="15" height="13" rx="2"/><path d="M2.5 7h15 M8.2 9.6l-2.3 2.4 2.3 2.4 M11.8 9.6l2.3 2.4-2.3 2.4"/>'],
    design: ['#5b9bff', '<path d="M10 2.6l5.4 9.9L10 17.4l-5.4-4.9Z M10 2.6v7.4"/><circle cx="10" cy="11.3" r="1.5"/>'],
    testing: ['#ff4f5e', '<ellipse cx="10" cy="11.6" rx="3.6" ry="4.6"/><circle cx="10" cy="5.6" r="1.8"/><path d="M10 8.4v7.6 M6.4 10.6H3.2 M16.8 10.6h-3.2 M6.6 14l-2.7 1.9 M13.4 14l2.7 1.9 M8.6 4.4 7.2 2.6 M11.4 4.4l1.4-1.8"/>'],
    testing_lab: ['#00ff88', '<path d="M7.4 2.6h5.2 M8.5 2.6v5.2L4.1 15.4a1.4 1.4 0 0 0 1.2 2.1h9.4a1.4 1.4 0 0 0 1.2-2.1L11.5 7.8V2.6 M5.9 12.6h8.2"/><circle cx="9" cy="15" r=".8" fill="currentColor"/><circle cx="11.6" cy="14.4" r=".6" fill="currentColor"/>'],
    trading_desk: ['#00ff88', '<path d="M5 2.8v14.4 M10 2v16 M15 4.6v11"/><rect x="3.5" y="6" width="3" height="6.2" rx=".6"/><rect x="8.5" y="9" width="3" height="5.2" rx=".6"/><rect x="13.5" y="6.6" width="3" height="4.6" rx=".6"/>'],
    office: ['#5b9bff', '<rect x="3" y="3.4" width="14" height="9.6" rx="1.6"/><path d="M7.4 16.6h5.2 M10 13v3.6 M5.6 6.4h5 M5.6 9h3"/>'],
    ops: ['#00cfff', '<rect x="2.4" y="3.6" width="6.8" height="5.2" rx="1"/><rect x="10.8" y="3.6" width="6.8" height="5.2" rx="1"/><rect x="6.6" y="11" width="6.8" height="5.2" rx="1"/><path d="M4.4 6.8l1.4-1.2 1.2.9 M12.6 7.2h2.8"/>'],
    library: ['#5b9bff', '<path d="M3.4 3.4h3v13.2h-3Z M7.9 3.4h3v13.2h-3Z M12.4 4.3l2.9-.8 3.3 12.4-2.9.8Z M3.4 6h3 M7.9 6h3"/>'],
    workshop: ['#00cfff', '<path d="M12.9 3.1a4 4 0 0 0-4.7 5.2l-4.9 4.9a1.7 1.7 0 0 0 2.4 2.4l4.9-4.9a4 4 0 0 0 5.2-4.7l-2.4 2.4-2.3-.4-.4-2.3Z"/>'],
    command: ['#00cfff', '<circle cx="10" cy="10" r="7.2"/><circle cx="10" cy="10" r="3.7"/><path d="M10 10l5.1-5.1 M10 2.8v1.6 M10 15.6v1.6 M2.8 10h1.6 M15.6 10h1.6"/><circle cx="12.9" cy="8" r=".9" fill="currentColor"/>'],
    greenhouse: ['#00ff88', '<path d="M4 16.2c0-7 4.6-11.6 12-12.1-.3 7.4-4.9 12.1-12 12.1Z M4 16.2l6.6-6.6"/>'],
    // the two built-in rooms: Operations (the weekly audit) a gear with its check, the Vault its door
    audit: ['#00ff88', '<circle cx="10" cy="10" r="3.3"/><path d="M10 2.4v2.3 M10 15.3v2.3 M2.4 10h2.3 M15.3 10h2.3 M4.6 4.6l1.6 1.6 M13.8 13.8l1.6 1.6 M4.6 15.4l1.6-1.6 M13.8 6.2l1.6-1.6 M8.6 10l1 1 1.9-2"/>'],
    vault: ['#00ff88', '<rect x="2.6" y="3.2" width="14.8" height="13.6" rx="2"/><circle cx="10" cy="10" r="3.9"/><circle cx="10" cy="10" r="1" fill="currentColor"/><path d="M10 6.1v1.6 M10 12.3v1.6 M6.1 10h1.6 M12.3 10h1.6 M5 16.8v1 M15 16.8v1"/>']
  };
  // which icon: NEXUS's, a template's, or a department of one's own by its room's look
  CO.deptIconOf = function (d) {
    var k = d === 'hub' || d === 'audit' || d === 'vault' ? d : DEPT_ICON[d.key] && d.key !== 'custom' ? d.key : (d.look && DEPT_ICON[d.look] ? d.look : 'office');
    return DEPT_ICON[k];
  };
  // the same icon for the office's glass (u3d.js glassSign): its colour and a standalone SVG of it
  CO.deptIconSvg = function (d, px) {
    var ic = CO.deptIconOf(d);
    return { color: ic[0], svg: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" width="' + px + '" height="' + px + '" color="' + ic[0] + '" fill="none" stroke="' + ic[0] +
      '" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' + ic[1] + '</svg>' };
  };

  function hhmm(t) { var d = new Date(t); return pad(d.getHours()) + ':' + pad(d.getMinutes()); }
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  CO.hhmm = hhmm;
})();

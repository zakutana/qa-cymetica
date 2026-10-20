/* The /company mockup: the simulated runner and Manager. Nothing here talks to a server.
 * One virtual clock (CO.S.clock) moves at the chosen speed; the runner passes every PASS ms,
 * starts at most two turns a pass (one per department), meters each turn in plan units, and
 * the Manager tops up the plan and answers the owner. Every change emits 'change'; turns,
 * approvals and decisions emit their own events for the office's packets. */
(function () {
  'use strict';
  var CO = window.CO;
  var PASS = 30000, TURN_MIN = 10000, TURN_MAX = 18000, RETRY = 50000, FAIL_P = 0.16;

  var L = {};
  CO.on = function (ev, fn) { (L[ev] = L[ev] || []).push(fn); };
  CO.emit = function (ev, d) {
    (L[ev] || []).forEach(function (fn) { try { fn(d); } catch (e) { console.error(e); } });
  };
  var queued = false;
  function changed() {
    if (queued) return; queued = true;
    requestAnimationFrame(function () { queued = false; CO.emit('change'); });
  }
  CO.changed = changed;

  var sim = CO.sim = { speed: 1, running: true };
  var timers = [];
  function later(ms, fn) { timers.push({ at: CO.S.clock + ms, fn: fn }); }
  function rand(a, b) { return a + Math.random() * (b - a); }
  function pick(a) { return a[Math.floor(Math.random() * a.length)]; }
  function r2(v) { return Math.round(v * 100) / 100; }

  /* ---------- lookups ---------- */
  function dept(id) { var l = CO.S.departments; for (var i = 0; i < l.length; i++) if (l[i].id === id) return l[i]; return null; }
  function task(id) { var l = CO.S.tasks; for (var i = 0; i < l.length; i++) if (l[i].id === id) return l[i]; return null; }
  CO.dept = dept; CO.task = task;
  CO.deptTasks = function (id) { return CO.S.tasks.filter(function (t) { return t.dept_id === id; }); };

  /* ---------- budget ---------- */
  CO.avg = function () { var m = CO.S.meter; var s = 0; m.forEach(function (v) { s += v; }); return m.length ? s / m.length : 0.05; };
  CO.left = function () {
    var b = CO.S.budget, a = CO.avg();
    var sl = Math.max(0, b.session.cap - b.session.used), wl = Math.max(0, b.week.cap - b.week.used);
    var none = !CO.S.meter.length;   // no measured turn yet: the counter has nothing to divide by
    return {
      none: none,
      session: none ? null : Math.floor(sl / a + 1e-9), week: none ? null : Math.floor(wl / a + 1e-9),
      extra: b.extra.on ? (none ? '' : Math.floor(b.extra.left / a + 1e-9)) : null,
      sessionUnits: sl, weekUnits: wl, onPlan: sl > 0.004 && wl > 0.004
    };
  };
  // Can the runner start a turn now? The same gate every "why it waits" line reads.
  CO.gate = function () {
    var S = CO.S, b = S.budget;
    if (S.company.status === 'paused') return { ok: false, code: 'paused', text: 'company paused' };
    if (S.strip.length >= b.cap) {
      var mid = new Date(S.clock); mid.setHours(24, 0, 0, 0);
      return { ok: false, code: 'cap', text: 'daily ceiling', until: mid.getTime() };
    }
    var l = CO.left();
    if (l.onPlan) return { ok: true, code: 'plan' };
    if (b.extra.on && b.extra.left > 0.004) return { ok: true, code: 'extra' };
    var until = b.week.cap - b.week.used <= 0.004 ? b.week.resets_at : b.session.resets_at;
    return { ok: false, code: 'plan_limit', text: 'plan limit', until: until };
  };
  function charge(u) {
    var b = CO.S.budget, l = CO.left();
    if (l.onPlan) {
      var over = Math.max(0, u - Math.min(l.sessionUnits, l.weekUnits));
      b.session.used = Math.min(b.session.cap, b.session.used + u);
      b.week.used = Math.min(b.week.cap, b.week.used + u);
      if (over && b.extra.on) b.extra.left = Math.max(0, b.extra.left - over);
    } else if (b.extra.on) {
      b.extra.left = Math.max(0, b.extra.left - u);
    }
    CO.S.meter.push(u); if (CO.S.meter.length > 20) CO.S.meter.shift();
  }

  /* ---------- feed and messages ---------- */
  function feed(kind, d, text) {
    CO.S.feed.unshift({ kind: kind, dept: d, text: text, at: CO.S.clock });
    if (CO.S.feed.length > 60) CO.S.feed.length = 60;
    CO.emit('feed', CO.S.feed[0]);
  }
  CO.feed = feed;
  function say(text, deptId) {
    var S = CO.S;
    S.messages.push({ id: S.next_msg++, role: 'manager', text: text, at: S.clock, answered: true, dept_id: deptId || null });
    CO.emit('message');
  }

  /* ---------- the runner ---------- */
  function deptRunning(id) {
    return CO.S.tasks.some(function (t) { return t.dept_id === id && t.status === 'running'; });
  }
  function pass() {
    var S = CO.S, g = CO.gate();
    S.next_pass_at = S.clock + PASS;
    if (!g.ok) { changed(); return; }
    topUp();
    var started = 0;
    for (var i = 0; i < S.plan.length && started < 2; i++) {
      var t = task(S.plan[i]);
      if (!t || t.status !== 'queued') continue;
      if (t.next_attempt_at && t.next_attempt_at > S.clock) continue;
      if (t.blocked_by && task(t.blocked_by) && task(t.blocked_by).status === 'waiting_approval') continue;
      if (deptRunning(t.dept_id)) continue;
      if (capped(dept(t.dept_id))) continue;
      if (!CO.gate().ok) break;
      start(t); started++; i--;
    }
    changed();
  }
  // what a department spends, in dollars of plan: counted per day, held under the owner's daily cap
  function dayRoll(d) {
    var k = new Date(CO.S.clock).toDateString();
    if (d.tok_day !== k) { d.tok_day = k; d.tok_today = 0; d.turns_today = 0; }
  }
  function capped(d) {
    if (!d || !d.cap_day) return false;
    dayRoll(d);
    return d.tok_today >= d.cap_day;
  }
  CO.capped = capped;
  function start(t) {
    var S = CO.S, d = dept(t.dept_id);
    S.plan = S.plan.filter(function (id) { return id !== t.id; });
    t.status = 'running';
    t.started_at = t.started_at || S.clock;
    t.turn_started = S.clock;
    t.ends_at = S.clock + rand(TURN_MIN, TURN_MAX);
    if (!t.expert || d.experts.indexOf(t.expert) < 0) t.expert = d.experts[0];
    S.strip.push({ state: 'running', at: S.clock, dept_id: d.id, task_id: t.id });
    feed('info', d.name, 'started "' + t.title + '"' + (t.attempt > 1 ? ' (attempt ' + t.attempt + ')' : ''));
    CO.emit('turn:start', { task: t, dept: d });
  }
  function finish(t) {
    var S = CO.S, d = dept(t.dept_id);
    if (!d) { t.status = 'cancelled'; return; }
    var u = r2(rand(0.12, 0.32)), onPlan = CO.left().onPlan;
    charge(u);
    t.turns++; t.units = r2(t.units + u); d.units_7d = r2(d.units_7d + u);
    dayRoll(d); d.tok_today = r2(d.tok_today + u * CO.TOK); d.turns_today++;
    var cell = null;
    for (var i = S.strip.length - 1; i >= 0; i--) if (S.strip[i].task_id === t.id && S.strip[i].state === 'running') { cell = S.strip[i]; break; }
    if (cell) { cell.units = u; cell.extra = !onPlan; }
    var fail = t.fail_next === true || (t.fail_next !== false && Math.random() < FAIL_P);
    t.fail_next = undefined;
    var outcome;
    if (fail) {
      t.last_error = pick(CO.ERRORS);
      d.failed_7d++;
      if (cell) cell.state = 'failed';
      if (t.attempt < t.max_attempts) {
        t.status = 'queued'; t.attempt++;
        t.next_attempt_at = S.clock + RETRY;
        t.why = 'retry at ' + CO.hhmm(t.next_attempt_at) + ' after ' + t.last_error;
        S.plan.push(t.id);
        feed('bad', d.name, '"' + t.title + '" failed (' + t.last_error + '), retrying');
      } else {
        t.status = 'failed'; t.finished_at = S.clock;
        feed('bad', d.name, '"' + t.title + '" failed after ' + t.max_attempts + ' attempts');
      }
      outcome = 'failed';
    } else {
      if (cell) cell.state = 'done';
      t.last_error = '';
      if (t.turns < t.turns_needed) {
        t.status = 'queued';
        t.why = 'continues · turn ' + (t.turns + 1) + ' of ' + t.turns_needed;
        S.plan.unshift(t.id);
        feed('info', d.name, 'finished turn ' + t.turns + ' of ' + t.turns_needed + ' on "' + t.title + '"');
        outcome = 'continue';
      } else if (t.run) {
        // a scheduled bug-hunting run: each bug found is a report drafted under the owner's name
        t.status = 'done'; t.finished_at = S.clock;
        var prods = (d.products && d.products.length ? d.products : ['the public site']).slice();
        var n = Math.random() < 0.2 ? 0 : Math.random() < 0.55 ? 1 : 2, found = [];
        for (var k = 0; k < n; k++) {
          var p = prods[Math.floor(Math.random() * prods.length)], title = bugTitle(p, d);
          found.push(title);
          var b = { id: 'A' + (S.next_appr++), task_id: t.id, dept_id: d.id, kind: 'bug report', summary: title, created_at: S.clock, files_as: d.files_as };
          if (d.files_as) { fileNow(b, d); b.body = bugBody(p, title, d); continue; }
          b.body = bugBody(p, title, d);
          S.approvals.unshift(b);
          CO.emit('approval:new', b);
        }
        d.runs = (d.runs || 0) + 1;
        t.outcome = n ? (d.files_as ? 'Filed ' : 'Found ') + n + ' bug' + (n > 1 ? 's' : '') + ': ' + found.join('; ') : 'No new bugs on ' + prods.join(', ');
        if (n && d.files_as) {
          say(d.name + ' finished its run: ' + n + ' bug' + (n > 1 ? 's' : '') + ' filed into Cymetica\'s bug tracker as ' + d.files_as + '. Each one they accept pays 1,000 ET10.', d.id);
          outcome = 'done';
        } else if (n) {
          feed('ask', d.name, 'run found ' + n + ' bug' + (n > 1 ? 's' : '') + ', asks approval');
          say(d.name + ' finished its run: ' + n + ' bug' + (n > 1 ? 's' : '') + ' drafted as reports under ' + (d.files_as || 'your name') + '. Approve them on the right to file; each accepted bug pays 1,000 ET10.', d.id);
          outcome = 'ask';
        } else {
          feed('good', d.name, 'run finished, no new bugs');
          outcome = 'done';
        }
      } else if (t.kind === 'bug report' && d.files_as) {
        // Cymetica QA files it itself, as we do
        t.status = 'done'; t.finished_at = S.clock;
        var fb = { id: 'A' + (S.next_appr++), task_id: t.id, dept_id: d.id, kind: 'bug report', summary: t.title.replace(/^Verify: /, ''),
          created_at: S.clock, files_as: d.files_as };
        fb.body = CO.draft('bug report', t.title, d.name);
        fileNow(fb, d);
        t.outcome = 'Filed #' + fb.report_no + ' as ' + d.files_as;
        say(d.name + ' filed #' + fb.report_no + ' "' + fb.summary + '" as ' + d.files_as + '. If Cymetica accepts it, 1,000 ET10 goes to ' + d.files_as + '.', d.id);
        outcome = 'done';
      } else if (t.kind) {
        t.status = 'waiting_approval'; t.finished_at = S.clock;
        t.outcome = 'Draft ready: waits for your approval';
        var a = { id: 'A' + (S.next_appr++), task_id: t.id, dept_id: d.id, kind: t.kind, summary: t.title.replace(/^Verify: /, ''), created_at: S.clock,
          files_as: d.files_as || (t.kind === 'bug report' ? CO.HUNTER : null) };
        a.body = CO.draft(t.kind, t.title, d.name);
        S.approvals.unshift(a);
        feed('ask', d.name, 'asks approval: ' + t.kind);
        say(d.name + ' drafted a ' + t.kind + ': "' + t.title + '". It waits for your approval.', d.id);
        CO.emit('approval:new', a);
        outcome = 'ask';
      } else if (t.review) {
        t.status = 'waiting_approval'; t.finished_at = S.clock;
        t.outcome = (t.outcome_text || 'Done') + ' · waits for ' + t.review + ' to review';
        var rv = { id: 'A' + (S.next_appr++), task_id: t.id, dept_id: d.id, kind: 'review', summary: t.title, created_at: S.clock, reviewer: t.review };
        rv.body = 'PROCESS ' + t.rule + ' · REVIEW THE RESULT · reviewer: ' + t.review + '\n\nTask\n' + t.title + '\n\nResult\n' + (t.outcome_text || 'Done') +
          '\n\nIf you approve\nIt goes on to the next step of the process.\n\nIf you reject\nIt stops here; ' + d.name + ' keeps the result in its memory.';
        S.approvals.unshift(rv);
        feed('ask', d.name, 'result waits for ' + t.review + ' to review');
        say(d.name + ' finished "' + t.title + '": ' + (t.outcome_text || 'done') + '. Process ' + t.rule + ' wants ' + (t.review === 'you' ? 'your' : t.review + '\'s') + ' review before it goes on.', d.id);
        CO.emit('approval:new', rv);
        outcome = 'ask';
      } else {
        t.status = 'done'; t.finished_at = S.clock;
        t.outcome = t.outcome_text || t.outcome || 'Done';
        feed('good', d.name, 'finished "' + t.title + '"');
        if (Math.random() < 0.45) learn(d);
        outcome = 'done';
        afterDone(t, d);
      }
    }
    CO.emit('turn:end', { task: t, dept: d, outcome: outcome });
    topUp();
  }
  function learn(d) {
    var l = CO.LESSONS[d.key] || CO.LESSONS.custom, S = CO.S;
    var m = l[Math.floor(Math.random() * l.length)];
    if (S.memory.some(function (x) { return x.dept_id === d.id && x.text === m[1]; })) return;
    S.memory.push({ id: S.next_mem++, dept_id: d.id, kind: m[0], text: m[1], at: S.clock });
  }

  /* ---------- company rules: what anyone notices on the side goes where the rule says ---------- */
  function ruleOn(trigger) {
    var l = CO.S.rules || [];
    for (var i = 0; i < l.length; i++) if (l[i].on && l[i].trigger === trigger) return l[i];
    return null;
  }
  function ruleTarget(r) { return r ? dept(r.dept_id) : null; }
  CO.ruleTarget = ruleTarget;
  var SIDE = {
    idea: ['Gem Screener: a filter for coins with a team unlock this month', 'Chart Analyzer: show the score\'s history, not only today', 'Agent Tournaments: a replay of the last table'],
    money: ['Memecoins that FOMO >= 70 flags twice within an hour', 'Event cards priced below the BTC basket\'s implied move', 'League puzzles of one family solved on the same snapshot'],
    design: ['Supply Analyzer: unlock bars overlap on a phone', 'Gem Screener: Guardians tooltip covers the price', 'Company page: the plan list cuts long titles'],
    custom: ['a vendor message that needs an answer', 'a page that changed overnight']
  };
    var PREFIX = { bug: 'Verify: ', released: 'Test the new build: ', idea: 'BB request: ', money: 'Paper test: ', winner: 'Real trade: ', design: 'Review: ', custom: 'Handle: ' };
  function related(a, b) {
    var w = String(a).toLowerCase().match(/[a-zá-ž]{5,}/g) || [];
    b = String(b).toLowerCase();
    return w.some(function (x) { return b.indexOf(x) >= 0; });
  }
  // An event happened. Every rule that is on and listens for it hands the work to its department.
  function fire(kind, from, subject) {
    var S = CO.S, hit = 0;
    (S.rules || []).forEach(function (r) {
      if (!r.on || CO.kindOf(r.when) !== kind) return;
      // a process in the owner's own words fires only on an event that shares a word with it
      if (kind === 'custom' && !related(r.when, subject)) return;
      var to = ruleTarget(r);
      if (!to || (from && to.id === from.id && kind !== 'released')) return;
      if (r.review === 'start') {
        var ap = { id: 'A' + (S.next_appr++), task_id: null, dept_id: to.id, kind: 'start?', summary: PREFIX[kind] + subject, created_at: S.clock,
          reviewer: r.reviewer || 'you', pending: { rule: r.id, kind: kind, from: from ? from.id : null, subject: subject } };
        ap.body = 'PROCESS ' + r.id + ' · REVIEW BEFORE IT STARTS · reviewer: ' + ap.reviewer + '\n\nWhat happened\n' + 'When ' + r.when + (from ? ' (found by ' + from.name + ')' : '') + ': ' + subject +
          '\n\nWhat the process does\n' + to.name + ' ' + r.does + '.\n\nIf you approve\n' + to.name + ' starts it on the next pass.\n\nIf you reject\nNothing starts; the event is dropped.';
        S.approvals.unshift(ap);
        r.fired++; hit++;
        feed('ask', 'NEXUS', 'process ' + r.id + ' waits for ' + ap.reviewer + ' before ' + to.name + ' starts');
        say('When ' + r.when + ': "' + subject + '". Process ' + r.id + ' would hand it to ' + to.name + ', but it asks ' + (ap.reviewer === 'you' ? 'you' : ap.reviewer) + ' first: approve to start.', to.id);
        CO.emit('approval:new', ap);
        return;
      }
      if (queueFromRule(r, kind, from, subject, to)) hit++;
    });
    if (hit) changed();
    return hit;
  }
  function queueFromRule(r, kind, from, subject, to) {
    var S = CO.S;
    to = to || ruleTarget(r); if (!to) return null;
    {
      var o = { turns_needed: 1, why: 'rule ' + r.id + ': ' + r.when + (from ? ' · from ' + from.name : '') };
      if (kind === 'bug') { o.kind = 'bug report'; o.expert = 'qa_tester'; }
      if (kind === 'idea') o.kind = 'BB request';
      var seat = kind === 'winner' && to.key === 'trading_desk';
      if (kind === 'winner') { o.kind = seat ? 'seat request' : 'real-money action'; if (seat) o.expert = 'trader'; }
      if (kind === 'released') { o.turns_needed = 2; o.expert = 'qa_tester'; if (Math.random() < 0.5) o.kind = 'bug report'; }
      var title = seat ? 'Seat: ' + subject + ' at a FLASH $5 table' : PREFIX[kind] + subject;
      // the same thing already on its way there is not handed over twice
      if (S.tasks.some(function (x) { return x.dept_id === to.id && x.title === title && /queued|running|waiting_approval/.test(x.status); })) return null;
      var nt = newTask(to, title, o);
      nt.from_dept = from ? from.id : null; nt.rule = r.id; nt.event = kind;
      if (kind === 'released' && !o.kind) nt.outcome_text = 'No bugs in the new build';
      S.plan.unshift(nt.id);
      if (r.review === 'result') { nt.review = r.reviewer || 'you'; nt.why += ' · ' + nt.review + ' reviews the result'; }
      if (!r.reviewed) r.fired++;
      feed('info', from ? from.name : 'Cymetica', r.when + ': ' + subject + ' → ' + to.name + ' (' + r.id + ')');
      say('When ' + r.when + (from ? ' (' + from.name + ')' : '') + ': "' + subject + '". Process ' + r.id + ' hands it to ' + to.name + ', which ' + r.does + '. First in line.' +
        (nt.review ? ' Its result waits for ' + (nt.review === 'you' ? 'your' : nt.review + '\'s') + ' review before it goes on.' : ''), to.id);
      CO.emit('handoff', { from: from, to: to, rule: r });
      changed();
      return nt;
    }
  }
  CO.fire = fire;
  // what a finished piece of work raises next: something noticed on the side, a winning experiment
  function afterDone(t, d) {
    if (Math.random() < 0.3) later(rand(1500, 4000), function () { noticeInPassing(d); });
    if (Math.random() < 0.12) later(rand(2000, 5000), function () { fire('custom', d, pick(SIDE.custom)); });
    // only a bot can win a seat: a winning basket or signal is not an agent
    if (d.key === 'testing_lab' && /^Bot variant/.test(t.title) && Math.random() < 0.6) later(rand(2000, 4000), function () { fire('winner', d, t.title.replace(/^Bot variant: /, '')); });
  }
  // a department finishing its own work notices something outside its job
  function noticeInPassing(d) {
    if (!dept(d.id)) return;
    var kinds = ['bug', 'bug', 'idea', 'money', 'design'], kind = kinds[Math.floor(Math.random() * kinds.length)];
    var subject = kind === 'bug' ? bugTitle(pick(['Gem Screener', 'Chart Analyzer', 'Supply Analyzer', 'Agent Tournaments']), d) : pick(SIDE[kind]);
    fire(kind, d, subject);
  }

  /* ---------- scheduled runs: a department that hunts bugs on a clock ---------- */
  var BUGS = {
    'gem screener': ['holders count differs from the chain', 'Guardians ring shows green without data', 'sort by 24h volume drops 3 coins'],
    'chart analyzer': ['score differs from its study on 2 coins', 'RSI panel shows candles an hour old'],
    'supply analyzer': ['circulating supply above total supply', 'past unlock shown as upcoming'],
    'agent tournaments': ['deleted bot still seated at table 2', 'leaderboard ROI ignores fees'],
    'trading station': ['order book total off by one level', 'chart and ticker disagree on last price'],
    'agent league': ['puzzle closes before its stated time', 'prize list omits a scored answer'],
    'build it better': ['a request shows one status on the board and another in the API', 'the spec field cuts text the docs allow'],
    'fund launcher': ['a fund page figure differs from its API', 'a fund history starts after its launch date'],
    'cymetica.com': ['a link on the home page answers 404', 'a page promises a feature its docs do not list']
  };
  function bugTitle(p, d) {
    var l = BUGS[p.toLowerCase()] || ['a value on the page that its API does not return', 'a link in the docs answers 404', 'a number differs between page and API'];
    var used = CO.S.approvals.concat(CO.S.decided).map(function (a) { return a.summary; });
    for (var i = 0; i < l.length * 2; i++) { var s = p + ': ' + l[Math.floor(Math.random() * l.length)]; if (used.indexOf(s) < 0) return s; }
    return p + ': ' + l[0] + ' (again)';
  }
  // Cymetica's verdict on a filed report, a while later
  function verdictLater(a, d) {
    var S = CO.S;
    later(rand(40000, 70000), function () {
      var ok = Math.random() < 0.75;
      a.verdict = ok ? 'accepted' : 'duplicate';
      var no = a.report_no ? '#' + a.report_no + ' ' : '';
      if (ok) {
        S.et10 = (S.et10 || 0) + 1000;
        if (d) { d.et10 = (d.et10 || 0) + 1000; d.accepted = (d.accepted || 0) + 1; }
        feed('good', 'Cymetica', 'accepted ' + no + '"' + a.summary + '": +1,000 ET10 to ' + (a.files_as || 'you'));
        say('Cymetica accepted ' + no + '"' + a.summary + '". 1,000 ET10 credited to ' + (a.files_as || 'you') + '.', d && d.id);
        CO.emit('bounty', { approval: a, dept: d });
      } else {
        feed('bad', 'Cymetica', 'marked ' + no + '"' + a.summary + '" a duplicate: no reward');
      }
      changed();
    });
  }
  // an approved seat: the table runs, then closes with a rank and an ROI (paper; the top three share the ET10 prize)
  function seatLater(a, d, t) {
    var S = CO.S, flash = /FLASH/i.test(a.summary), agent = a.summary.replace(/^Seat: /, '').split(' at ')[0];
    var table = 10 + Math.floor(Math.random() * 20);
    later(rand(50000, 90000), function () {
      var rank = 1 + Math.floor(Math.random() * 10), roi = 7 - (rank - 1) * 1.15 + (Math.random() - 0.5);
      var prize = rank <= 3 ? (flash ? [85, 42, 14] : [600, 300, 100])[rank - 1] : 0;
      var r = (roi >= 0 ? '+' : '') + roi.toFixed(1) + '%';
      if (prize) {
        S.et10 = (S.et10 || 0) + prize;
        if (d) { d.et10 = (d.et10 || 0) + prize; d.prizes = (d.prizes || 0) + 1; }
      }
      var verdict = rank <= 3 ? 'keep it: next a 7-day table' : 'archived: ' + (roi < 0 ? 'lost money after fees' : 'not in the top three');
      if (t) t.outcome = 'Table ' + table + ' closed: ' + agent + ' ' + ordinal(rank) + ' of 10, ' + r + ' ROI · ' + verdict;
      feed(rank <= 3 ? 'good' : 'info', 'Agent Tournaments', 'table ' + table + ' closed: ' + agent + ' ' + ordinal(rank) + ' of 10, ' + r + ' ROI' + (prize ? ', +' + prize + ' ET10' : ''));
      say('Table ' + table + ' closed: ' + agent + ' finished ' + ordinal(rank) + ' of 10 at ' + r + ' ROI' + (prize ? ' and won ' + prize + ' ET10' : '') + '. ' + verdict.charAt(0).toUpperCase() + verdict.slice(1) + '.', d && d.id);
      changed();
    });
  }
  function ordinal(n) { return n + (n === 1 ? 'st' : n === 2 ? 'nd' : n === 3 ? 'rd' : 'th'); }
  // Cymetica QA files a bug straight into their tracker under the owner's hunter name, as we do: no approval
  function fileNow(b, d) {
    var S = CO.S;
    b.report_no = S.next_report = (S.next_report || 214);
    S.next_report++;
    b.decision = 'filed'; b.decided_at = S.clock;
    S.decided.unshift(b);
    feed('good', d.name, 'filed #' + b.report_no + ' as ' + (b.files_as || CO.HUNTER) + ': ' + b.summary);
    CO.emit('submitted', { approval: b, dept: d });
    verdictLater(b, d);
  }
  function bugBody(p, title, d) {
    return 'BUG REPORT · found by ' + d.name + ' on its run · filed as ' + (d.files_as || 'you') + '\n\nTitle\n' + title +
      '\n\nWhere\n' + p + ' on cymetica.com, read during the run' +
      '\n\nWhat happens\n' + title.split(': ').slice(1).join(': ') + '. Reproduced twice, a minute apart.' +
      '\n\nEvidence\nThe request, the response and the page, captured at the time.' +
      '\n\nReward\n1,000 ET10 to ' + (d.files_as || 'you') + ' if Cymetica accepts it.' +
      (d.files_as ? '\n\nFiled straight into cymetica.com/leaderboard/bugs as ' + d.files_as + '.' : '\n\nFiled only after your approval.');
  }
  function nextRun(d, t) {
    var day = new Date(t); day.setHours(0, 0, 0, 0);
    for (var k = 0; k < 2; k++) {
      for (var i = 0; i < d.schedule.times.length; i++) {
        var hm = d.schedule.times[i].split(':'), at = day.getTime() + k * 86400000 + (+hm[0]) * 3600000 + (+hm[1]) * 60000;
        if (at > t) return at;
      }
    }
    return t + 86400000;
  }
  function queueRun(d, why) {
    var S = CO.S;
    var open = S.tasks.some(function (t) { return t.dept_id === d.id && t.run && (t.status === 'queued' || t.status === 'running'); });
    if (open) return null;
    var title = 'Bug hunt: ' + (d.products.length ? d.products.length + ' product' + (d.products.length > 1 ? 's' : '') : 'the public site');
    var t = newTask(d, title, { turns_needed: 2, why: why, expert: 'qa_tester' });
    t.run = true;
    S.plan.unshift(t.id);
    return t;
  }

  // The Manager keeps three tasks in the plan; it plans for departments with nothing queued first.
  function topUp() {
    var S = CO.S;
    if (S.company.status !== 'active') return;
    var guard = 0;
    while (S.plan.length < 3 && guard++ < 6) {
      var busy = {};
      S.plan.forEach(function (id) { var t = task(id); if (t) busy[t.dept_id] = 1; });
      // a department on a clock works only its scheduled runs; the Manager plans for the others
      var free = S.departments.filter(function (d) { return !d.schedule; });
      var cands = free.filter(function (d) { return !busy[d.id] && !deptRunning(d.id); });
      if (!cands.length) cands = free.slice();
      if (!cands.length) return;
      var d = cands[Math.floor(Math.random() * cands.length)];
      var pool = CO.POOL[d.key] || CO.POOL.custom;
      // one draft waiting for the owner is enough: the next one waits until it is decided
      var asking = S.approvals.some(function (a) { return a.dept_id === d.id; }) ||
        S.tasks.some(function (x) { return x.dept_id === d.id && x.kind && (x.status === 'queued' || x.status === 'running'); });
      var skip = function (q) { return asking && q.kind; };
      var p = pool[d.pool_i % pool.length];
      for (var k = 0; skip(p) && k < pool.length; k++) { d.pool_i++; p = pool[d.pool_i % pool.length]; }
      if (skip(p)) return;
      d.pool_i++;
      var t = newTask(d, p.title, { kind: p.kind || null, turns_needed: p.turns || 1, outcome_text: p.outcome, why: p.why, expert: p.expert });
      S.plan.push(t.id);
      feed('info', 'NEXUS', 'queued "' + t.title + '" for ' + d.name);
    }
  }
  function newTask(d, title, o) {
    var S = CO.S;
    var t = { id: S.next_id++, dept_id: d.id, title: title, status: 'queued', attempt: 1, max_attempts: 3, turns: 0,
      turns_needed: o.turns_needed || 1, units: 0, created_at: S.clock, started_at: null, finished_at: null,
      outcome: '', last_error: '', next_attempt_at: null, kind: o.kind || null, why: o.why || 'planned by NEXUS',
      expert: o.expert && d.experts.indexOf(o.expert) >= 0 ? o.expert : d.experts[0],
      brief: title + '. Start from the charter; report what you found in one line, with the evidence.' };
    t.outcome_text = o.outcome_text || 'Done: findings in the department memory';
    S.tasks.push(t);
    return t;
  }

  /* ---------- the clock ---------- */
  var last = performance.now();
  function tick() {
    var now = performance.now(), dt = Math.min(1000, now - last); last = now;
    if (!sim.running || !CO.S) return;
    var S = CO.S, b = S.budget;
    S.clock += dt * sim.speed;
    ['session', 'week'].forEach(function (k) {
      if (S.clock >= b[k].resets_at) {
        b[k].used = 0; b[k].resets_at += b[k].every;
        feed('good', 'Plan', (k === 'session' ? 'session' : 'week') + ' reset: units back to ' + b[k].cap.toFixed(2));
        changed();
      }
    });
    var day = new Date(S.clock).getDate();
    if (S.day != null && S.day !== day) { S.strip = S.strip.filter(function (c) { return c.state === 'running'; }); changed(); }
    S.day = day;
    S.tasks.forEach(function (t) {
      if (t.status === 'running' && t.ends_at <= S.clock) { finish(t); changed(); }
    });
    for (var i = timers.length - 1; i >= 0; i--) {
      if (timers[i].at <= S.clock) { var f = timers[i].fn; timers.splice(i, 1); f(); changed(); }
    }
    // a visited company's owner answers its approvals in their own time; the visitor only watches
    if (CO.RO && S.approvals.length) {
      S.approvals.slice().forEach(function (a) {
        if (!a.owner_at) a.owner_at = a.created_at + rand(25000, 70000);
        if (S.clock >= a.owner_at) CO.act.decide(a.id, Math.random() < 0.85 ? 'approve' : 'reject');
      });
    }
    S.departments.forEach(function (d) {
      if (!d.schedule || !d.next_run || S.clock < d.next_run) return;
      d.next_run = nextRun(d, S.clock + 1000);
      if (queueRun(d, 'scheduled · ' + d.schedule.label)) { feed('info', 'NEXUS', 'queued the scheduled run of ' + d.name); changed(); }
    });
    if (S.company.status === 'active' && S.clock >= S.next_pass_at) pass();
    CO.emit('tick');
  }
  setInterval(tick, 200);

  /* ---------- the owner's actions ---------- */
  CO.act = {
    pause: function () {
      var S = CO.S;
      if (S.company.status === 'paused') {
        S.company.status = 'active';
        S.next_pass_at = S.clock + 3000;
        feed('info', 'You', 'resumed the company');
        var pending = S.messages.filter(function (m) { return m.role === 'owner' && !m.answered; });
        S.notice = null;
        if (pending.length) answer(pending[pending.length - 1]);
      } else {
        S.company.status = 'paused';
        feed('info', 'You', 'paused the company');
      }
      changed();
    },
    decide: function (id, decision) {
      var S = CO.S, a = null;
      S.approvals = S.approvals.filter(function (x) { if (x.id === id) { a = x; return false; } return true; });
      if (!a) return;
      var t = task(a.task_id), d = dept(a.dept_id);
      a.decision = decision; a.decided_at = S.clock;
      S.decided.unshift(a);
      if (a.kind === 'start?' || a.kind === 'review') {
        if (decision === 'approve') {
          S.approved_7d++;
          if (a.kind === 'start?') {
            var pr = (S.rules || []).filter(function (x) { return x.id === a.pending.rule; })[0];
            if (pr) { pr.reviewed = true; queueFromRule(pr, a.pending.kind, dept(a.pending.from), a.pending.subject); pr.reviewed = false; }
            feed('good', 'You', 'approved the start: ' + a.summary);
          } else if (t) {
            t.status = 'done'; t.outcome = (t.outcome_text || 'Done') + ' · reviewed by ' + a.reviewer; t.finished_at = S.clock;
            feed('good', 'You', 'reviewed and passed: ' + a.summary);
            if (d) afterDone(t, d);
          }
        } else {
          if (t) { t.status = 'cancelled'; t.outcome = 'Stopped at ' + a.reviewer + '\'s review'; t.finished_at = S.clock; }
          feed('bad', 'You', (a.kind === 'start?' ? 'did not start: ' : 'stopped at review: ') + a.summary);
        }
        CO.emit('approval:decided', { approval: a, dept: d, decision: decision });
        changed();
        return;
      }
      if (decision === 'approve') {
        S.approved_7d++;
        var verb = a.kind === 'real-money action' ? 'placed' : a.kind === 'seat request' ? 'seated' : 'submitted';
        if (t) { t.status = 'done'; t.outcome = verb.charAt(0).toUpperCase() + verb.slice(1) + ' after your approval'; t.finished_at = S.clock; }
        feed('good', 'You', 'approved: ' + a.summary);
        later(2600, function () {
          feed('good', d ? d.name : 'NEXUS', verb + ' after your approval: ' + a.summary.replace(/^Seat: /, ''));
          CO.emit('submitted', { approval: a, dept: d });
        });
        if (a.kind === 'BB request') {
          later(rand(50000, 80000), function () {
            var what = a.summary.replace(/^BB request: /, '');
            feed('good', 'Cymetica', 'delivered "' + what + '": the new build is live');
            if (!fire('released', d, what)) say('Cymetica delivered "' + what + '". No rule tests new builds yet; say "when a new build is released, QA tests it" and I will route it.', d && d.id);
          });
        }
        if (a.kind === 'bug report') verdictLater(a, d);
        if (a.kind === 'seat request') seatLater(a, d, t);
        // a task waiting on this approval may now run
        S.tasks.forEach(function (x) { if (x.blocked_by === a.task_id) x.blocked_by = null; });
      } else {
        if (t) { t.status = 'cancelled'; t.outcome = 'Rejected by you'; t.finished_at = S.clock; }
        S.tasks.forEach(function (x) {
          if (x.blocked_by === a.task_id && x.status === 'queued') {
            x.status = 'cancelled'; x.outcome = 'Its approval was rejected';
            S.plan = S.plan.filter(function (id) { return id !== x.id; });
          }
        });
        feed('bad', 'You', 'rejected: ' + a.summary);
      }
      CO.emit('approval:decided', { approval: a, dept: d, decision: decision });
      changed();
    },
    move: function (id, dir) {
      var S = CO.S, i = S.plan.indexOf(id); if (i < 0) return;
      S.plan.splice(i, 1);
      var j = dir === 'top' ? 0 : dir === 'up' ? Math.max(0, i - 1) : Math.min(S.plan.length, i + 1);
      S.plan.splice(j, 0, id);
      changed();
    },
    remove: function (id) {
      var S = CO.S, t = task(id);
      S.plan = S.plan.filter(function (x) { return x !== id; });
      if (t) { t.status = 'cancelled'; t.outcome = 'Removed from the plan by you'; t.finished_at = S.clock; feed('info', 'You', 'removed from the plan: ' + t.title); }
      changed();
    },
    message: function (text, deptId) {
      var S = CO.S;
      var m = { id: S.next_msg++, role: 'owner', text: text, at: S.clock, answered: false, dept_id: deptId || null };
      S.messages.push(m);
      feed('info', 'You', 'wrote to NEXUS');
      var g = CO.gate();
      if (!g.ok && g.code === 'paused') {
        S.notice = { text: 'Paused: NEXUS answers on Resume.' };
      } else if (!g.ok) {
        S.notice = { text: 'Plan limit: NEXUS answers after the reset at ' + CO.hhmm(g.until) + '.' };
      } else {
        S.notice = null;
        answer(m);
      }
      changed();
    },
    charter: function (id, text) {
      var d = dept(id); if (!d) return;
      d.charter = text; d.charter_updated_at = CO.S.clock;
      feed('info', 'You', 'saved the charter of ' + d.name);
      changed();
    },
    addDept: function (o) {
      var S = CO.S;
      var used = S.departments.map(function (d) { return d.slot; });
      var slot = 0; while (used.indexOf(slot) >= 0) slot++;
      var d = { id: S.next_dept++, key: o.key || 'custom', slot: slot, name: o.name, experts: o.experts.length ? o.experts : ['researcher'],
        units_7d: 0, failed_7d: 0, charter: o.charter, charter_updated_at: S.clock, pool_i: 0, born: S.clock,
        schedule: o.schedule || null, products: o.products || [],
        files_as: o.files_as || (o.key === 'testing' ? CO.HUNTER : null), et10: 0, accepted: 0, runs: 0,
        run_kind: o.run_kind || null, link: o.link || null, look: o.look || null };
      S.departments.push(d);
      feed('good', 'NEXUS', 'new department: ' + d.name);
      if (d.schedule) {
        // first run now, then on its clock
        var r = queueRun(d, 'first run, right after setup');
        d.next_run = nextRun(d, S.clock);
        if (!o.quiet) later(1500, function () { say(d.name + ' is set up. First run queued at the top: "' + r.title + '".', d.id); });
        CO.emit('dept:new', d); changed(); return d;
      }
      var pool = CO.POOL[d.key] || CO.POOL.custom;
      var first = d.key === 'custom' ? pool[0] : pool[0];
      var t = newTask(d, d.key === 'custom' ? 'Read the charter and propose a first week' : first.title,
        { kind: d.key === 'custom' ? null : first.kind, turns_needed: first.turns || 1, outcome_text: first.outcome, why: 'new department', expert: first.expert });
      d.pool_i = d.key === 'custom' ? 1 : 1;
      S.plan.unshift(t.id);
      if (!o.quiet) later(1500, function () { say(d.name + ' is set up with ' + d.experts.map(CO.expertName).join(' and ') + '. First task queued at the top: "' + t.title + '".', d.id); });
      CO.emit('dept:new', d);
      changed();
      return d;
    },
    editDept: function (id, o) {
      var d = dept(id); if (!d) return;
      d.name = o.name || d.name; d.experts = o.experts.length ? o.experts : d.experts;
      if (o.look !== undefined) d.look = o.look || null;
      if (o.charter !== d.charter) { d.charter = o.charter; d.charter_updated_at = CO.S.clock; }
      feed('info', 'You', 'updated department ' + d.name);
      CO.emit('dept:edit', d);
      changed();
    },
    removeDept: function (id) {
      var S = CO.S, d = dept(id); if (!d) return;
      S.departments = S.departments.filter(function (x) { return x.id !== id; });
      S.tasks.forEach(function (t) { if (t.dept_id === id && (t.status === 'queued' || t.status === 'running')) { t.status = 'cancelled'; t.outcome = 'Department removed'; } });
      S.plan = S.plan.filter(function (tid) { var t = task(tid); return t && t.dept_id !== id; });
      S.approvals = S.approvals.filter(function (a) { return a.dept_id !== id; });
      feed('bad', 'You', 'removed department ' + d.name);
      CO.emit('dept:removed', d);
      changed();
    },
    rule: function (id, on) {
      var r = (CO.S.rules || []).filter(function (x) { return x.id === id; })[0]; if (!r) return;
      r.on = on; feed('info', 'You', (on ? 'switched on process ' : 'switched off process ') + r.id + ': when ' + r.when); changed();
    },
    addRule: function (o) {
      var S = CO.S, r = { id: 'R' + (S.next_rule++), on: true, when: o.when, dept_id: o.dept_id, does: o.does || 'takes care of it', fired: 0, review: o.review || null, reviewer: o.reviewer || 'you' };
      var d = dept(r.dept_id);
      S.rules.push(r); feed('good', 'You', 'new process: when ' + r.when + ' → ' + (d ? d.name : '?')); changed(); return r;
    },
    review: function (id, mode, who) {
      var r = (CO.S.rules || []).filter(function (x) { return x.id === id; })[0]; if (!r) return;
      r.review = mode || null; if (who) r.reviewer = who; changed();
    },
    removeRule: function (id) { CO.S.rules = CO.S.rules.filter(function (x) { return x.id !== id || x.locked; }); changed(); },
    products: function (id, list) {
      var d = dept(id); if (!d) return;
      d.products = list; feed('info', 'You', 'set the products of ' + d.name + ': ' + list.join(', '));
      changed();
    },
    // the owner's brake: at most this many dollars a day (null: no cap); work over it waits for midnight
    cap: function (id, tokens) {
      var d = dept(id); if (!d) return;
      d.cap_day = tokens || null;
      feed('info', 'You', d.name + ': ' + (tokens ? 'daily cap ' + CO.fmtTok(tokens) : 'no daily cap'));
      changed();
    },
    // a department on a clock: how many runs a day
    runsPerDay: function (id, n) {
      var d = dept(id); if (!d || !d.schedule) return;
      var times = CO.RUN_TIMES[n]; if (!times) return;
      d.schedule = { times: times, label: n + '× a day (' + (n > 4 ? 'every ' + (24 / n) + ' h' : times.join(', ')) + ')' };
      d.next_run = nextRun(d, CO.S.clock);
      feed('info', 'You', d.name + ' runs ' + d.schedule.label);
      changed();
    },
    runNow: function (id) {
      var d = dept(id); if (!d) return;
      var r = queueRun(d, 'you asked for it at ' + CO.hhmm(CO.S.clock));
      if (r) { feed('info', 'You', 'asked ' + d.name + ' for a run now'); CO.S.next_pass_at = Math.min(CO.S.next_pass_at, CO.S.clock + 3000); }
      changed();
      return r;
    },
    extra: function (on) { CO.S.budget.extra.on = !!on; changed(); },
    settings: function (o) { for (var k in o) CO.S.company[k] = o[k]; changed(); }
  };

  /* ---------- the Manager's replies ---------- */
  function answer(m) {
    var S = CO.S;
    S.typing = true; changed();
    later(rand(1400, 2800), function () {
      S.typing = false;
      m.answered = true;
      var out = reply(m.text, m.at, m.dept_id);
      say(out.text || out, out.dept_id || m.dept_id);
      feed('info', 'NEXUS', 'replied');
    });
  }
  var ALIAS = [
    ['testing_lab', /\b(lab|laborat|experiment|paper|strateg|nexus|backtest|room)/],
    ['trading_desk', /\b(trad|desk|money|profit|basket|buy|sell|position|pnl|agent|tournament|turnaj|ziskov|vydel)/],
    ['design', /\b(design|brief|mock|look|layout|ui|page|colou?r|picture)/],
    ['development', /\b(develop|build|spec|feature|request|bb\b|build it better)/],
    ['testing', /\b(test|bug|check|verify|docs?|api|report|broken|fix)/]
  ];
  function findDept(t, prefer) {
    var S = CO.S;
    for (var i = 0; i < S.departments.length; i++) {
      if (t.indexOf(S.departments[i].name.toLowerCase()) >= 0) return S.departments[i];
    }
    if (prefer && dept(prefer)) return dept(prefer);
    for (var j = 0; j < ALIAS.length; j++) {
      if (ALIAS[j][1].test(t)) {
        var d = S.departments.filter(function (x) { return x.key === ALIAS[j][0]; })[0];
        if (d) return d;
      }
    }
    return null;
  }
  // the department a stretch of words names: its full name, else a word of its name ("QA", "desk"), else what it
  // is about; the earliest one in the words wins ("when a build ships, QA does the testing" is QA, not Testing lab)
  function deptIn(s) {
    var S = CO.S, t = ' ' + s.toLowerCase() + ' ', best = null, at = 1e9;
    S.departments.forEach(function (d) {
      var n = d.name.toLowerCase(), i = t.indexOf(n);
      if (i >= 0 && i < at) { best = d; at = i; }
    });
    if (best) return best;
    S.departments.forEach(function (d) {
      d.name.toLowerCase().split(/\s+/).forEach(function (w) {
        if (w.length < 2 || /^(cymetica|the|department|team)$/.test(w)) return;
        var m = new RegExp('[^a-z0-9á-ž]' + w.replace(/[^a-z0-9]/g, '') + '[^a-z0-9á-ž]').exec(t);
        if (m && m.index < at) { best = d; at = m.index; }
      });
    });
    if (best) return best;
    for (var j = 0; j < ALIAS.length; j++) {
      if (ALIAS[j][1].test(t)) {
        var d = S.departments.filter(function (x) { return x.key === ALIAS[j][0]; })[0];
        if (d) return d;
      }
    }
    return null;
  }
  // A process written as one sentence: "when <something happens>, <department> <does what>", in English or Czech,
  // with an optional "I want to see the result" / "ask me before it starts". Returns the rule, or what is missing.
  CO.parseRule = function (text) {
    var S = CO.S, raw = String(text || '').trim().replace(/[.!]+$/, ''), t = raw.toLowerCase();
    if (!raw) return { missing: 'text' };
    var WHEN = /(?:^|\s)(?:when(?:ever)?|kdy[zž]|kdykoliv?|jakmile|as soon as|once|if|pokud|po tom,? co|after)\s+(.+?)(?:,|\s+(?:then|tak|a[tť]|pak)\s)/i;
    var wm = raw.match(WHEN), when, rest;
    if (wm) { when = wm[1].trim(); rest = raw.slice(raw.indexOf(wm[0]) + wm[0].length); }
    else {
      var ci = raw.indexOf(',');
      if (ci < 0) return { missing: 'when' };
      when = raw.slice(0, ci).trim(); rest = raw.slice(ci + 1);
    }
    var to = deptIn(rest) || deptIn(when);
    if (!to) return { missing: 'dept', when: when };
    var review = /(review|zkontrol|schv[aá]l|kouknu|projdu|human|[cč]lov[eě]k|j[aá] (to )?(vid|chci)|chci (to )?vid|i want to see|ask me|zeptej|show me|uk[aá][zž] mi)/.test(t) ?
      (/(n[eě][zž] za[cč]|before|first|p[rř]edem|nejd[rř][ií]v|ne[zž] se pust|ask me|zeptej)/.test(t) ? 'start' : 'result') : null;
    var by = raw.match(/(?:review(?:ed)? by|approved by|schv[aá]l[ií]|zkontroluje|kontroluje)\s+([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][\wáčďéěíňóřšťúůýž]+)/);
    // "does": the rest, without the department's words, the filler and the review clause
    var does = rest;
    [to.name].concat(to.name.split(/\s+/)).forEach(function (w) {
      if (w.length > 1 && !/^cymetica$/i.test(w)) does = does.replace(new RegExp('(^|\\s)' + w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '(?=\\s|,|$)', 'i'), ' ');
    });
    does = does.replace(/^\s*(,|ho|to|ji|je|at|ať|then|tak|pak|it|the|department|odd[eě]len[ií])\s+/i, ' ')
      .replace(/^\s*(ho|to|ji|je|at|ať)\s+/i, ' ')
      .replace(/\s*(,|\s)\s*(a |and )?(v[yý]sledek|the result|i want|j[aá] chci|chci|ale|but|ask me|zeptej|before it|ne[zž] se|reviewed by|review(ed)? by)\b.*$/i, '')
      .replace(/\s+/g, ' ').trim();
    var same = S.rules.filter(function (x) { return x.dept_id === to.id && CO.kindOf(x.when) === CO.kindOf(when) && CO.kindOf(when) !== 'custom'; })[0];
    return { when: when.replace(/^(when|kdy[zž])\s+/i, ''), dept_id: to.id, dept: to, does: does.length > 2 ? does : 'takes care of it',
      review: review, reviewer: by ? by[1] : 'you', same: same || null };
  };
  // add what parseRule read (or switch on the process that already says it); one line back, for the chat or the page
  CO.addRuleFromWords = function (pr) {
    if (pr.same) {
      if (!pr.same.on) CO.act.rule(pr.same.id, true);
      return 'That is already process ' + pr.same.id + ': when ' + pr.same.when + ' → ' + pr.dept.name + ' ' + pr.same.does + '. It is on.';
    }
    var nr = CO.act.addRule({ when: pr.when, dept_id: pr.dept_id, does: pr.does, review: pr.review, reviewer: pr.reviewer });
    return 'Process ' + nr.id + ' added: when ' + nr.when + ' → ' + pr.dept.name + ' ' + nr.does + '.' +
      (pr.review === 'start' ? ' It waits for ' + (nr.reviewer === 'you' ? 'your' : nr.reviewer + '\'s') + ' Approve before it starts.' :
        pr.review === 'result' ? ' Its result waits for ' + (nr.reviewer === 'you' ? 'your' : nr.reviewer + '\'s') + ' review.' : '') + ' Everyone follows it from now on.';
  };
  // "add a QA department that runs twice a day on X and Y, under my name" -> a department spec
  var KNOWN = ['Gem Screener', 'Chart Analyzer', 'Supply Analyzer', 'Agent Tournaments', 'Trading Station', 'Agent League', 'Memecoin Terminal', 'Build it Better', 'Fund Launcher'];
  function splitList(s) {
    return s.split(/\s*(?:,|;|\/|\sa\s|\sand\s|\+)\s*/i).map(function (x) { return x.trim().replace(/[.!]+$/, ''); })
      .filter(Boolean).map(function (x) {
        var k = KNOWN.filter(function (n) { return n.toLowerCase() === x.toLowerCase(); })[0];
        return k || x.charAt(0).toUpperCase() + x.slice(1);
      });
  }
  function parseAddDept(text) {
    var t = text.toLowerCase();
    var verb = /(add|create|new|set up|start|p[rř][ií]d|zalo[zž]|vytvo[rř]|zř[ií]d|zrid)/.test(t);
    var noun = /(department|odd[eě]len|team|t[yý]m)/.test(t);
    if (!(verb && noun)) return null;
    // a department named in the words wins ("a trading desk that sends agents to be tested" is a trading desk)
    var named = CO.TEMPLATES.filter(function (x) {
      return x.name && (t.indexOf(x.name.toLowerCase()) >= 0 || (x.key === 'trading_desk' && /\btrading\b/.test(t)));
    })[0] || null;
    var qa = named ? named.key === 'testing' : /(\bqa\b|test|bug|chyb)/.test(t);
    var tpl = named || (qa ? CO.TEMPLATES.filter(function (x) { return x.key === 'testing'; })[0] : null);
    if (!tpl) for (var j = 0; j < ALIAS.length && !tpl; j++) if (ALIAS[j][1].test(t)) tpl = CO.TEMPLATES.filter(function (x) { return x.key === ALIAS[j][0]; })[0];
    tpl = tpl || CO.TEMPLATES.filter(function (x) { return x.key === 'custom'; })[0];
    var per = 0, m = t.match(/(\d+)\s*(?:[x×]|times|kr[aá]t)\s*(?:a |per |za |)?(?:day|den|dn|denn)/);
    if (m) per = +m[1]; else if (/twice a day|dvakr[aá]t/.test(t)) per = 2; else if (/(daily|every day|denn[eě]|ka[zž]d[yý] den)/.test(t)) per = 1;
    per = Math.min(per, 6);
    var times = CO.RUN_TIMES[per];
    var products = [];
    var pm = text.match(/(?:products?|produkt[yůu]?|produktech)\s*:\s*(.+)$/i);
    if (pm) products = splitList(pm[1]);
    else KNOWN.forEach(function (k) { if (t.indexOf(k.toLowerCase()) >= 0) products.push(k); });
    var mine = /(m[yý]m jm[eé]nem|my name|under me|my account|m[uů]j [uú][cč]et|na m[eě]|et10|odm[eě]n|reward|bounty)/.test(t);
    var base = tpl.name || 'New department', name = base, n = 2;
    while (CO.S.departments.some(function (x) { return x.name === name; })) name = base + ' ' + n++;
    var files = qa || mine ? CO.HUNTER : null;
    var charter = (tpl.charter ? tpl.charter + '\n' : '') +
      (times ? '- Runs ' + per + '× a day (' + times.join(', ') + ') over: ' + (products.length ? products.join(', ') : 'the public site') + '.\n' : '') +
      (files ? '- Hunter name: ' + files + '. Every report is filed as ' + files + ' and its ET10 goes to ' + files + '\'s wallet.\n' : '');
    return { key: tpl.key, name: name, experts: qa ? ['qa_tester', 'auditor'] : tpl.experts.slice(), charter: charter.trim(),
      schedule: times ? { times: times, label: per + '× a day (' + times.join(', ') + ')' } : null, products: products, files_as: files, quiet: true };
  }
  function counts() {
    var S = CO.S, open = 0, working = 0;
    S.departments.forEach(function (d) {
      CO.deptTasks(d.id).forEach(function (t) { if (t.status === 'queued' || t.status === 'running' || t.status === 'waiting_approval') open++; });
      if (deptRunning(d.id)) working++;
    });
    return { open: open, working: working, waiting: S.approvals.length };
  }
  function titleFrom(text) {
    var s = text.trim().replace(/^(please|pls|can you|could you|i want|i need|let'?s|go and|make sure)\s+/i, '');
    s = s.charAt(0).toUpperCase() + s.slice(1);
    return s.length > 64 ? s.slice(0, 61) + '...' : s;
  }
  function reply(text, at, focus) {
    var S = CO.S, t = text.toLowerCase(), c = counts(), d = findDept(t, focus), l = CO.left();
    var spec = parseAddDept(text);
    if (spec) {
      var nd = CO.act.addDept(spec);
      return { dept_id: nd.id, text: 'Done: ' + nd.name + ' is set up with ' + nd.experts.map(CO.expertName).join(' and ') + '.' +
        (nd.schedule ? ' It runs ' + nd.schedule.label + ' over ' + (nd.products.length ? nd.products.join(', ') : 'the public site') + ', first run now.' : '') +
        (nd.files_as ? ' Every bug it finds goes straight into Cymetica\'s bug tracker as ' + nd.files_as + ', and each one they accept pays 1,000 ET10 to ' + nd.files_as + '.' : '') +
        (nd.schedule && !nd.products.length ? ' Which products? Write e.g. "products: Gem Screener, Chart Analyzer".' : '') };
    }
    if (/(rule|pravidl|process|whenever|kdykoli|kdy[zž] |when )/.test(t) && S.departments.length) {
      // "when <words>, <department> <does words>": the department must be one the company has
      var pr = CO.parseRule(text);
      if (!pr.missing) return CO.addRuleFromWords(pr);
      if (pr.missing === 'dept') return 'Which department should do it? Name one of yours (' + S.departments.map(function (x) { return x.name; }).join(', ') + ') and I add the process.';
    }
    var pm = text.match(/(?:products?|produkty?)\s*:\s*(.+)$/i);
    if (pm) {
      var sd = d && d.schedule ? d : S.departments.filter(function (x) { return x.schedule; }).slice(-1)[0];
      if (sd) {
        CO.act.products(sd.id, splitList(pm[1]));
        return sd.name + ' now tests ' + sd.products.join(', ') + ' on every run (' + sd.schedule.label + ').';
      }
    }
    if (focus && dept(focus) && /(status|how|update|progress|doing|what.*(now|next)|co d[eě]l|jak|stav)/.test(t)) {
      var fd = dept(focus), v = CO.deptView(fd);
      return fd.name + ': ' + CO.deptLine(fd, v).text + '. ' + v.done + ' done so far; it spent ' + CO.fmtTok(v.tokToday) + ' today.' +
        (fd.schedule ? ' Next run ' + CO.hhmm(fd.next_run) + '.' : '') + (fd.et10 ? ' Earned ' + fd.et10.toLocaleString('en-US') + ' ET10.' : '');
    }
    if (!S.departments.length) {
      return 'You have no departments yet. Add one (+ Add on the left, or the empty lot in the office) and I plan its first task at once.';
    }
    if (/^(hi|hello|hey|ahoj|cau|čau|nazdar|good (morning|evening))\b/.test(t)) {
      return 'Hello. ' + c.working + ' working, ' + c.open + ' open, ' + c.waiting + ' wait for you. Tell me what matters most and I plan around it.';
    }
    if (/(status|how are|update|progress|what.*(doing|now)|summary|report back)/.test(t) && !/bug report/.test(t)) {
      var run = S.tasks.filter(function (x) { return x.status === 'running'; }).map(function (x) { return dept(x.dept_id).name + ': "' + x.title + '"'; });
      return c.working + ' working' + (run.length ? ' (' + run.join('; ') + ')' : '') + '. ' + c.open + ' open, ' +
        c.waiting + ' wait' + (c.waiting === 1 ? 's' : '') + ' for you. ' + (l.none ? 'No turn measured yet, so no turns-left figure.' :
        l.session + ' turn' + (l.session === 1 ? '' : 's') + ' left this session, ' + l.week + ' this week.');
    }
    if (/(pause|stop everything|halt)/.test(t)) return 'Pausing is your switch (Pause, top left). Nothing new starts while paused; a running turn finishes first.';
    if (/(approv|waiting for me|what.*wait)/.test(t)) {
      if (!S.approvals.length) return 'Nothing waits for you right now.';
      return S.approvals.length + ' wait for you: ' + S.approvals.map(function (a) { return a.kind + ' "' + a.summary + '"'; }).join('; ') + '. Read and approve them on the right.';
    }
    if (/(budget|turns? left|usage|limit|cost|units|tokens?)/.test(t)) {
      if (l.none) return 'No turn measured yet. After the first one the counter shows turns left: units left divided by what a turn really costs.';
      returnl.session + ' turn' + (l.session === 1 ? '' : 's') + ' left this session, ' + l.week + ' this week' + (l.extra != null ? ', +' + l.extra + ' on extra usage' : '') +
        '. A turn costs ' + CO.avg().toFixed(2) + ' u on average (last 20).';
    }
    if (d && /(first|priorit|top|urgent|asap|before|now)/.test(t)) {
      var q = S.plan.map(task).filter(function (x) { return x && x.dept_id === d.id; })[0];
      if (q) { CO.act.move(q.id, 'top'); return 'Moved "' + q.title + '" to the top. It runs on the next pass.'; }
    }
    if (d) {
      var nt = newTask(d, titleFrom(text), { why: 'you asked for it at ' + CO.hhmm(at), turns_needed: 1 });
      S.plan.unshift(nt.id);
      return 'Queued for ' + d.name + ': "' + nt.title + '" · ~1 turn. It is first in line.';
    }
    return 'Noted. Which department should take it? Name it (Testing, Testing lab, Development, Design studio, Trading desk) and I queue it.';
  }

  /* ---------- what every view reads: one department, honestly ---------- */
  CO.waitText = function (t) {
    var S = CO.S, g = CO.gate();
    if (S.company.status === 'paused') return 'company paused';
    if (!g.ok) return g.text + (g.until ? ' until ' + CO.hhmm(g.until) : '');
    if (t && capped(dept(t.dept_id))) return 'daily token cap reached · back at 00:00';
    if (t && t.blocked_by && task(t.blocked_by) && task(t.blocked_by).status === 'waiting_approval') return 'waits on your approval';
    if (t && t.next_attempt_at && t.next_attempt_at > S.clock) return 'retry at ' + CO.hhmm(t.next_attempt_at) + ' after ' + (t.last_error || 'an error');
    return 'next pass in ' + Math.max(0, Math.ceil((S.next_pass_at - S.clock) / 1000)) + 's';
  };
  CO.deptView = function (d) {
    var S = CO.S, ts = CO.deptTasks(d.id), v = { d: d, open: 0, done: 0, queued: [], running: null, waiting: 0 };
    ts.forEach(function (t) {
      if (t.status === 'running') v.running = t;
      if (t.status === 'done') v.done++;
      if (t.status === 'queued' || t.status === 'running' || t.status === 'waiting_approval') v.open++;
      if (t.status === 'waiting_approval') v.waiting++;
    });
    S.plan.forEach(function (id) { var t = task(id); if (t && t.dept_id === d.id && t.status === 'queued') v.queued.push(t); });
    v.failed = d.failed_7d;
    v.memory = S.memory.filter(function (m) { return m.dept_id === d.id; }).length;
    v.status = v.running ? 'working' : v.queued.length ? 'queued' : v.waiting ? 'waiting' : 'idle';
    v.waits = !v.running && v.queued.length ? CO.waitText(v.queued[0]) : '';
    var lit = false;
    v.experts = d.experts.map(function (k) {
      var on = !lit && v.running && v.running.expert === k;
      if (on) lit = true;
      return { key: k, name: CO.expertName(k), state: on ? 'working' : 'idle' };
    });
    if (v.running && !lit && v.experts.length) v.experts[0].state = 'working';
    v.units = d.units_7d;
    // what this department eats: of the current 5-hour window and of the week
    var b = S.budget, from = b.session.resets_at - b.session.every, su = 0;
    S.strip.forEach(function (c) { if (c.dept_id === d.id && c.at >= from && !c.extra && c.units != null) su += c.units; });
    v.sessPct = Math.min(100, Math.round(su / b.session.cap * 100));
    v.weekPct = Math.round(d.units_7d / b.week.cap * 100);
    // dollars: today, the last 7 days, what one turn of this department costs, and its cap
    dayRoll(d);
    var tu = 0, tt = 0;
    ts.forEach(function (x) { if (x.turns) { tu += x.units; tt += x.turns; } });
    v.tokToday = d.tok_today; v.tok7d = d.units_7d * CO.TOK;
    v.perTurn = (tt ? tu / tt : CO.S.meter.length ? CO.avg() : 0.19) * CO.TOK;
    v.cap = d.cap_day || null; v.capped = capped(d);
    v.fits = v.cap ? Math.max(0, Math.floor(v.cap / v.perTurn)) : null;
    return v;
  };
  CO.counts = counts;
  // One line a person reads at a glance: what this department is doing, in plain words, and its colour.
  // `short` fits an office plate; `text` fits a card.
  CO.deptLine = function (d, v) {
    var S = CO.S; v = v || CO.deptView(d);
    var asks = S.approvals.filter(function (a) { return a.dept_id === d.id; }).length;
    if (v.capped) return { tone: 'red', short: 'Daily cap reached', text: 'Paused: daily cap reached' };
    if (asks) return { tone: 'red', short: 'Needs you', text: 'Needs you · approve ' + asks };
    if (v.running) return { tone: 'cyan', short: 'Working', text: 'Working: ' + v.running.title };
    if (S.company.status === 'paused') return { tone: 'dim', short: 'Paused', text: 'Paused' };
    if (v.queued.length) return { tone: 'blue', short: 'Up next', text: 'Up next: ' + v.queued[0].title };
    if (d.schedule && d.next_run) return { tone: 'dim', short: 'Next run ' + CO.hhmm(d.next_run), text: 'Next run at ' + CO.hhmm(d.next_run) };
    return { tone: 'dim', short: 'Idle', text: 'Idle: nothing to do' };
  };

  // one department of a setup, added the way its owner would add it: template, clock, products, hunter name
  function setupDept(o) {
    var tpl = CO.TEMPLATES.filter(function (x) { return x.key === o.key; })[0] || {};
    var times = o.runs ? CO.RUN_TIMES[o.runs] : null;
    var files = o.key === 'testing' ? CO.HUNTER : null;
    var charter = (o.charter || tpl.charter || '') +
      (times && o.key === 'testing' ? '\n- Runs ' + o.runs + '× a day (' + times.join(', ') + ') over: ' + (o.products || []).join(', ') + '.' : '') +
      (files ? '\n- Hunter name: ' + files + '. Every report is filed as ' + files + ' and its ET10 goes to ' + files + '\'s wallet.' : '');
    return CO.act.addDept({ key: o.key, name: o.name || tpl.name || 'Department', experts: (o.experts || tpl.experts || ['researcher']).slice(), charter: charter, quiet: true,
      schedule: times ? { times: times, label: o.runs + '× a day (' + (o.runs > 4 ? 'every ' + (24 / o.runs) + ' h' : times.join(', ')) + ')' } : null,
      products: (o.products || []).slice(), files_as: files, run_kind: o.run_kind || null, link: o.link || null });
  }
  function setupRules(rules) {
    rules.forEach(function (r) {
      var d = CO.S.departments.filter(function (x) { return x.name === r[1]; })[0];
      if (d) CO.act.addRule({ when: r[0], dept_id: d.id, does: r[2] });
    });
  }
  // our own company (CO.OURS): its departments and processes, added the way the owner would add them
  CO.applySetup = function () {
    var S = CO.S;
    if (S.setup === 'visit') { delete S.setup; return applyVisit(CO.VISIT); }
    if (S.setup !== 'ours') return;
    delete S.setup;
    CO.OURS.departments.forEach(setupDept);
    setupRules(CO.OURS.rules);
    say('Your company is set up: ' + S.departments.length + ' departments and ' + S.rules.length + ' processes. ' +
      'Cymetica QA runs on its clock; I plan the Quant Lab and the Trading desk.');
  };
  // someone else's public company, as a visitor finds it: its departments and processes, what each has
  // finished lately and learned, the ET10 it has earned, and the runner already passing
  var OWNER_DONE = { 'BB request': 'Submitted after the owner\'s approval', 'real-money action': 'Placed after the owner\'s approval',
    'seat request': 'Seated after the owner\'s approval', 'bug report': 'Filed after the owner\'s approval' };
  function applyVisit(V) {
    var S = CO.S, now = S.clock;
    V.departments.forEach(setupDept);
    setupRules(V.rules || []);
    S.departments.forEach(function (d, i) {
      var pool = CO.POOL[d.key] || CO.POOL.custom;
      for (var k = 0; k < 3; k++) {
        var p = pool[(i + k + 1) % pool.length];
        var t = newTask(d, p.title, { turns_needed: p.turns || 1, outcome_text: p.outcome, why: p.why, expert: p.expert, kind: p.kind });
        var end = now - (k * 53 + i * 17 + 11) * 60000;
        t.status = 'done'; t.turns = t.turns_needed; t.units = r2(0.19 * t.turns);
        t.created_at = end - 25 * 60000; t.started_at = end - 7 * 60000; t.finished_at = end;
        t.outcome = p.kind ? OWNER_DONE[p.kind] || 'Done' : p.outcome || 'Done';
      }
      learn(d); learn(d); if (i % 2) learn(d);
      d.units_7d = r2(0.35 + ((d.id * 37) % 100) / 80);
      d.tok_day = new Date(now).toDateString(); d.tok_today = r2(d.units_7d / 5); d.turns_today = Math.round(d.tok_today / 0.19);
    });
    var by = function (f) { return S.departments.filter(f)[0]; };
    var qa = by(function (d) { return d.key === 'testing'; }), desk = by(function (d) { return d.key === 'trading_desk'; });
    if (qa) { qa.et10 = V.bugs * 1000; qa.accepted = V.bugs; }
    if (desk && V.prize) { desk.et10 = V.prize; desk.prizes = Math.max(1, Math.round(V.prize / 85)); }
    S.et10 = CO.uvEt10(V);
    S.meter = [0.21, 0.18, 0.24, 0.2, 0.22, 0.19];
    S.budget.session.used = r2(S.budget.session.cap * (0.18 + (V.id % 5) * 0.09));
    S.budget.week.used = r2(S.budget.week.cap * (0.3 + (V.id % 4) * 0.1));
    S.next_report = 300 + V.id;
    say('The company is set up: ' + S.departments.length + ' department' + (S.departments.length === 1 ? '' : 's') + ' and ' + S.rules.length + ' process' + (S.rules.length === 1 ? '' : 'es') + '.');
    S.next_pass_at = now + 2500;
  }
  CO.reset = function () {
    timers = [];
    CO.S = CO.fresh(Date.now());
    CO.applySetup();
    CO.emit('reset');
    changed();
  };
})();

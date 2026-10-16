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
  function say(text) {
    var S = CO.S;
    S.messages.push({ id: S.next_msg++, role: 'manager', text: text, at: S.clock, answered: true });
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
      if (!CO.gate().ok) break;
      start(t); started++; i--;
    }
    changed();
  }
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
      } else if (t.kind) {
        t.status = 'waiting_approval'; t.finished_at = S.clock;
        t.outcome = 'Draft ready: waits for your approval';
        var a = { id: 'A' + (S.next_appr++), task_id: t.id, dept_id: d.id, kind: t.kind, summary: t.title, created_at: S.clock };
        a.body = CO.draft(t.kind, t.title, d.name);
        S.approvals.unshift(a);
        feed('ask', d.name, 'asks approval: ' + t.kind);
        say(d.name + ' drafted a ' + t.kind + ': "' + t.title + '". It waits for your approval.');
        CO.emit('approval:new', a);
        outcome = 'ask';
      } else {
        t.status = 'done'; t.finished_at = S.clock;
        t.outcome = t.outcome_text || t.outcome || 'Done';
        feed('good', d.name, 'finished "' + t.title + '"');
        if (Math.random() < 0.45) learn(d);
        outcome = 'done';
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

  // The Manager keeps three tasks in the plan; it plans for departments with nothing queued first.
  function topUp() {
    var S = CO.S;
    if (S.company.status !== 'active') return;
    var guard = 0;
    while (S.plan.length < 3 && guard++ < 6) {
      var busy = {};
      S.plan.forEach(function (id) { var t = task(id); if (t) busy[t.dept_id] = 1; });
      var cands = S.departments.filter(function (d) { return !busy[d.id] && !deptRunning(d.id); });
      if (!cands.length) cands = S.departments.slice();
      if (!cands.length) return;
      var d = cands[Math.floor(Math.random() * cands.length)];
      var pool = CO.POOL[d.key] || CO.POOL.custom;
      var p = pool[d.pool_i % pool.length]; d.pool_i++;
      var t = newTask(d, p.title, { kind: p.kind || null, turns_needed: p.turns || 1, outcome_text: p.outcome, why: p.why, expert: p.expert });
      S.plan.push(t.id);
      feed('info', 'Manager', 'queued "' + t.title + '" for ' + d.name);
    }
  }
  function newTask(d, title, o) {
    var S = CO.S;
    var t = { id: S.next_id++, dept_id: d.id, title: title, status: 'queued', attempt: 1, max_attempts: 3, turns: 0,
      turns_needed: o.turns_needed || 1, units: 0, created_at: S.clock, started_at: null, finished_at: null,
      outcome: '', last_error: '', next_attempt_at: null, kind: o.kind || null, why: o.why || 'planned by the Manager',
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
      if (decision === 'approve') {
        S.approved_7d++;
        if (t) { t.status = 'done'; t.outcome = (a.kind === 'real-money action' ? 'Placed after your approval' : 'Submitted after your approval'); t.finished_at = S.clock; }
        feed('good', 'You', 'approved: ' + a.summary);
        later(2600, function () {
          feed('good', d ? d.name : 'Manager', (a.kind === 'real-money action' ? 'placed' : 'submitted') + ' after your approval: ' + a.summary);
          CO.emit('submitted', { approval: a, dept: d });
        });
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
    message: function (text) {
      var S = CO.S;
      var m = { id: S.next_msg++, role: 'owner', text: text, at: S.clock, answered: false };
      S.messages.push(m);
      feed('info', 'You', 'wrote to the Manager');
      var g = CO.gate();
      if (!g.ok && g.code === 'paused') {
        S.notice = { text: 'Paused: the Manager answers on Resume.' };
      } else if (!g.ok) {
        S.notice = { text: 'Plan limit: the Manager answers after the reset at ' + CO.hhmm(g.until) + '.' };
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
        units_7d: 0, failed_7d: 0, charter: o.charter, charter_updated_at: S.clock, pool_i: 0, born: S.clock };
      S.departments.push(d);
      feed('good', 'Manager', 'new department: ' + d.name);
      var pool = CO.POOL[d.key] || CO.POOL.custom;
      var first = d.key === 'custom' ? pool[0] : pool[0];
      var t = newTask(d, d.key === 'custom' ? 'Read the charter and propose a first week' : first.title,
        { kind: d.key === 'custom' ? null : first.kind, turns_needed: first.turns || 1, outcome_text: first.outcome, why: 'new department', expert: first.expert });
      d.pool_i = d.key === 'custom' ? 1 : 1;
      S.plan.unshift(t.id);
      later(1500, function () { say(d.name + ' is set up with ' + d.experts.map(CO.expertName).join(' and ') + '. First task queued at the top: "' + t.title + '".'); });
      CO.emit('dept:new', d);
      changed();
      return d;
    },
    editDept: function (id, o) {
      var d = dept(id); if (!d) return;
      d.name = o.name || d.name; d.experts = o.experts.length ? o.experts : d.experts;
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
      say(reply(m.text, m.at));
      feed('info', 'Manager', 'replied');
    });
  }
  var ALIAS = [
    ['testing_lab', /\b(lab|laborat|experiment|paper|strateg|nexus|backtest|room)/],
    ['trading_desk', /\b(trad|desk|money|profit|basket|buy|sell|position|pnl)/],
    ['design', /\b(design|brief|mock|look|layout|ui|page|colou?r|picture)/],
    ['development', /\b(develop|build|spec|feature|request|bb\b|build it better)/],
    ['testing', /\b(test|bug|check|verify|docs?|api|report|broken|fix)/]
  ];
  function findDept(t) {
    var S = CO.S;
    for (var i = 0; i < S.departments.length; i++) {
      if (t.indexOf(S.departments[i].name.toLowerCase()) >= 0) return S.departments[i];
    }
    for (var j = 0; j < ALIAS.length; j++) {
      if (ALIAS[j][1].test(t)) {
        var d = S.departments.filter(function (x) { return x.key === ALIAS[j][0]; })[0];
        if (d) return d;
      }
    }
    return null;
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
  function reply(text, at) {
    var S = CO.S, t = text.toLowerCase(), c = counts(), d = findDept(t), l = CO.left();
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
    return v;
  };
  CO.counts = counts;

  CO.reset = function () {
    timers = [];
    CO.S = CO.fresh(Date.now());
    CO.emit('reset');
    changed();
  };
})();

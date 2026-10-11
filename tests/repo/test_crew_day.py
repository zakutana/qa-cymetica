"""A day of the company, dry: every ticket reaches an end and no role idles without a reason.

docs/crew-plan.md, C8 step 6, asked for before anything starts for real. Two halves:

  * **a simulated day**, in this process, in a couple of minutes: the clock looks every five
    minutes of a day that is not real -- the laboratory's tick (a stand-in printing what a
    tick decides), the desk's steps, the manager's morning review, the watchdog -- and every
    department drains its tickets through the stand-in `claude`. The laboratory's worker is
    made to fail, so escalation has something to escalate; the desk hands a bug to Bugs; the
    outsider's look hands its stumbles on.
  * **real processes** for half a minute: `crew.py start` spawns the six loops detached, the
    clock ticks and the departments work, `crew.py stop` ends them all and gives back what
    was claimed.

No model is started anywhere here: `QA_CREW_CLAUDE` names the stand-in.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from qa import crew
from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
FAKE = REPO / "tests" / "meta" / "fixtures" / "fake_claude.py"

FAKE_TICK = """\
import pathlib, sys
counter = pathlib.Path(sys.argv[1])
n = int(counter.read_text()) + 1 if counter.exists() else 1
counter.write_text(str(n))
plan = {1: "answer NEX-0301 + hunt sweep", 4: "outsider", 7: "gap + learn", 10: "hunt bugs"}
print(f"[lab] tick {n}")
print("  their side moved: #301 FIXED") if n == 1 else None
print("decide: " + plan.get(n, "none"))
"""


def _script(name: str):
    spec = importlib.util.spec_from_file_location(f"day_{name}", REPO / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _env(tmp_path: Path) -> dict:
    tick = tmp_path / "fake_tick.py"
    tick.write_text(FAKE_TICK, encoding="utf-8")
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"lab": "fail", "desk": "bug-ticket", "bugs": "silent",
                                "manager": "silent"}), encoding="utf-8")
    # The allowlist start() requires, in a settings file of the dry run's own: the real one
    # gets its entries on the operator's word (docs/crew-plan.md, C0).
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"permissions": {"allow": [
        "Bash(python scripts/crew.py:*)", "Bash(python scripts/commit.py:*)"]}}),
        encoding="utf-8")
    # The loops ask processes.pass_in_flight, which reads the deep pass's notebook under
    # QA_REPO_ROOT: pointed here, a deep pass running this very suite does not pause the dry
    # run's company (second read, finding 5).
    return {"QA_STATE_DIR": str(tmp_path / "state"), "QA_CREW_SETTINGS": str(settings),
            "QA_REPO_ROOT": str(tmp_path),
            "QA_CREW_CLAUDE": json.dumps([sys.executable, str(FAKE)]),
            "QA_CREW_TICK": json.dumps([sys.executable, str(tick), str(tmp_path / "ticks")]),
            "FAKE_CLAUDE_PLAN": str(plan), "QA_CREW_POLL": "0.5"}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_simulated_day_ends_every_ticket_and_leaves_no_role_idle_without_a_reason(
        tmp_path, monkeypatch):
    for key, value in _env(tmp_path).items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("QA_CREW_DEPT", raising=False)
    sup = _script("crew")
    clock = [datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)]
    monkeypatch.setattr(crew, "_now", lambda now=None: now or clock[0])
    stumble_run = {"type": "run", "id": "OUT-0009",
                   "stumbles": [{"where": "/agent-league", "what": "join 404s"}],
                   "surfaces": [{"name": "Bots", "score": 2, "why": "no record"}]}

    def outsider_look(ticket):
        for spec in crew.outsider_tickets(stumble_run):
            crew.add_ticket(spec["to"], spec["kind"], spec["text"], key=spec["key"],
                            by="outsider")
        return {"pid": None, "code": 0, "stdout": sup._result("OUT-0009: 2 handed on"),
                "stderr": "", "timed_out": False, "seconds": 0.0}

    monkeypatch.setitem(sup.CODE_DEPARTMENTS, "outsider", outsider_look)
    # The pause between desk steps, cut so a day holds a few of them without hours of runs.
    monkeypatch.setattr(crew, "DESK_PAUSE", timedelta(hours=4))

    start = clock[0]
    for step in range(0, 24 * 12):
        clock[0] = start + timedelta(minutes=5 * step)
        sup.clock_look(now=clock[0])
        for dept in crew.DEPARTMENTS:
            for _ in range(6):  # drain: a ticket and its retries within one look
                if sup.work_once(dept) is None:
                    break
    sup.clock_look(now=clock[0] + timedelta(minutes=5))  # the last escalations
    for dept in crew.DEPARTMENTS:
        while sup.work_once(dept) is not None:
            pass

    state = crew.tickets()
    unfinished = {tid: (t["to"], t["kind"], t["status"]) for tid, t in state.items()
                  if t["status"] not in ("done", "failed")}
    # The desk's next step is the one ticket allowed to be open at the end of a day.
    assert set(unfinished.values()) <= {("desk", "step", "open")}, unfinished

    ticks = [r for r in crew.load(crew.runs_path()) if r.get("type") == "tick"]
    # A tick every twenty minutes of the day, and the closing look's at minute 1440.
    assert len(ticks) == 73, len(ticks)
    by_kind = {}
    for ticket in state.values():
        by_kind.setdefault((ticket["to"], ticket["kind"]), []).append(ticket)
    # The desk handed a bug over and Bugs closed it.
    desk_bugs = [t for t in by_kind[("bugs", "bug")] if t["from"] == "desk"]
    assert desk_bugs and all(t["status"] == "done" for t in desk_bugs)
    # The outsider's stumble went to Bugs, its low score to the desk.
    assert any(t["key"] == "OUT-0009-S1" and t["status"] == "done"
               for t in by_kind[("bugs", "bug")])
    assert by_kind[("desk", "input")][0]["status"] == "done"
    # The laboratory failed three times on a ticket; the manager got it, and closed it.
    failed_lab = [t for t in by_kind[("lab", "lab")] if t["status"] == "failed"]
    assert failed_lab
    helps = {t["payload"].get("ticket"): t for t in by_kind[("manager", "help")]}
    assert all(t["id"] in helps and helps[t["id"]]["status"] == "done" for t in failed_lab)
    # A sweep woke on their side moving, carrying what moved.
    assert by_kind[("bugs", "sweep")][0]["payload"]["moved"] == ["#301 FIXED"]
    # The auditor's day and the manager's review of it.
    assert [r for r in crew.load(crew.runs_path()) if r.get("type") == "metrics"]
    assert all(t["status"] == "done" for t in by_kind[("manager", "daily")])
    # No role idles without saying why.
    for line in sup.status_lines(clock[0])[1:]:
        name, rest = line.split(None, 1)
        assert ": " in rest or "running" in rest, line


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_company_starts_detached_works_and_stops_with_nothing_left_claimed(tmp_path):
    env = {**os.environ, **_env(tmp_path)}
    env.pop("QA_CREW_DEPT", None)

    def crew_cli(*args: str, timeout: int = 120) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(REPO / "scripts" / "crew.py"), *args],
                              env=env, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout, cwd=str(REPO))

    started = crew_cli("start")
    assert started.returncode == 0, started.stdout + started.stderr
    try:
        deadline = time.monotonic() + 90
        done = []
        while time.monotonic() < deadline:
            rows = crew.load(tmp_path / "state" / "crew_tickets.jsonl")
            done = [r for r in rows if r.get("type") == "done"]
            if len(done) >= 3:
                break
            time.sleep(1.0)
        status = crew_cli("status").stdout
        assert status.startswith("company: running (6/6 loops)"), status
        assert len(done) >= 3, (status, crew.load(tmp_path / "state" / "crew_tickets.jsonl"))
    finally:
        stopped = crew_cli("stop", timeout=180)
    assert stopped.returncode == 0, stopped.stdout + stopped.stderr
    after = crew_cli("status").stdout
    assert after.startswith("company: stopped"), after
    state = crew.fold(crew.load(tmp_path / "state" / "crew_tickets.jsonl"))
    assert not [t for t in state.values() if t["status"] == "claimed"], state

"""The clock gives the desk no next step while a desk worker is still running (T-0037).

`qa/crew.py::desk_due` measures DESK_PAUSE from `last_run_end('desk')`, the newest desk `run`
row in state/crew.jsonl. The supervisor writes that row only after the worker has exited
(`scripts/crew.py::work_once`), and a worker closes its own ticket (`crew.py done`) before it
exits -- here T-0032 closed at 19:46:59Z and its row came at 19:49:37Z, because it committed
after its done. A clock look in that gap sees no open or claimed desk ticket and the run
before last as the last end, so it tickets the next step at once: T-0035 was made at
19:47:17Z, 18 s after a done and 45 min after the newest row it could see.

The test is the fix's specification, in a place a worker can write. The fix: `desk_due` (or
`clock_look` before it) treats a desk worker's marker (`crew.active()['desk']`, set while it
runs, `crew/active/desk.json`) as "not due". The marker is dropped in `work_once`'s `finally`,
a few lines before the run row is written, so the rule that closes the window whole is the
marker OR a pause counted from the newest desk ticket's own close; the marker alone leaves
milliseconds. The controls below pass today and must keep passing: the pause itself, and a
desk that is due once the pause is over.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import importlib.util

import pytest

from qa import crew
from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


def _script(name: str):
    spec = importlib.util.spec_from_file_location(f"desk_pause_{name}",
                                                  REPO / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def company(tmp_path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("QA_REPO_ROOT", str(tmp_path / "no-repo"))
    monkeypatch.delenv("QA_CREW_DEPT", raising=False)
    monkeypatch.delenv("QA_CREW_TICKET", raising=False)
    # The laboratory's tick, stood in: nothing it says matters here.
    monkeypatch.setenv("QA_CREW_TICK", json.dumps([sys.executable, "-c",
                                                   "print('decide: none')"]))
    return tmp_path


def _desk_tickets() -> list[dict]:
    return [t for t in crew.tickets().values() if t["to"] == "desk"]


def _desk_step_closed(now: datetime, ended: timedelta, worker_running: bool) -> None:
    """A desk step that closed its ticket; its run row `ended` before `now` is the newest
    desk row that exists -- the one a worker still running has not yet written."""
    crew.record({"type": "run", "dept": "desk", "ticket": "T-0000", "kind": "step",
                 "exit": 0, "outcome": "ok"}, now=now - ended)
    ticket, _ = crew.add_ticket("desk", "step", "a step", key="desk:the-step",
                                by="clock", now=now - timedelta(seconds=20))
    crew.claim("desk")
    crew.close(ticket["id"], "done", by="desk", note="closed, still committing",
               now=now - timedelta(seconds=18))
    if worker_running:
        crew.set_active("desk", ticket, pid=os.getpid(), now=now - timedelta(minutes=10))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_clock_does_not_ticket_the_desk_while_a_desk_worker_is_still_running(company):
    now = datetime.now(timezone.utc)
    _desk_step_closed(now, ended=timedelta(minutes=45), worker_running=True)
    assert "desk" in crew.active(), "the stand-in worker's marker is up, as work_once leaves it"
    before = len(_desk_tickets())
    _script("crew").clock_look(now=now)
    made = [t["id"] for t in _desk_tickets()][before:]
    assert made == [], (f"a desk worker was running and the clock still ticketed {made}: "
                        f"the pause never started")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_pause_also_runs_from_the_tickets_close_when_the_marker_is_gone(company):
    """B04, deep pass 2026-10-15: "the marker alone leaves milliseconds". The worker's marker is
    already down, its run row not yet written (the newest is 45 min old), and the ticket closed
    18 s ago: a marker-only fix still tickets the next step here."""
    now = datetime.now(timezone.utc)
    _desk_step_closed(now, ended=timedelta(minutes=45), worker_running=False)
    assert "desk" not in crew.active()
    before = len(_desk_tickets())
    _script("crew").clock_look(now=now)
    made = [t["id"] for t in _desk_tickets()][before:]
    assert made == [], f"the ticket closed 18 s ago and the clock ticketed {made}"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_control_the_pause_still_holds_after_a_run_and_the_desk_is_due_once_it_is_over(company):
    now = datetime.now(timezone.utc)
    sup = _script("crew")
    _desk_step_closed(now, ended=timedelta(minutes=10), worker_running=False)
    before = len(_desk_tickets())
    sup.clock_look(now=now)
    assert len(_desk_tickets()) == before, "ten minutes after a run is inside the pause"
    sup.clock_look(now=now + crew.DESK_PAUSE)
    assert len(_desk_tickets()) == before + 1, "a desk past its pause with no worker is due"

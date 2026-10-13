"""An outsider whose probe never ran is retried, and never read as a stranger that failed (T-0069).

state/outsider.jsonl holds two probe rows, both ok false, 'the probe did not run (exit 1):
Failed to refresh OAuth token: another Claude Code process is refreshing it ... retry in a
minute' -- 2026-10-12T16:15:05Z and 2026-10-13T15:35:27Z, the moments of the two company
starts. The only probe the company makes is `crew.py start`'s (scripts/crew.py:780-784);
`qa.outsider.proven` reads the newest probe row; the tick wakes the outsider only when proven
(scripts/lab.py::_parts_ready); `run_outsider`'s own probe runs only on an outsider ticket,
which no tick makes while unproven. So a machinery failure is written as a probe row that
`proven` takes for a verdict, and nothing retries it: `crew.py status` says 'idle: no work
came' and the department has never run.

The specification, in a place a worker can write. The fix is the session's (scripts/outsider.py,
scripts/crew.py, qa/outsider.py):

* a probe that did not run (`independent`'s first branch: exit != 0, 'Not logged in', '/login')
  is the machinery, not a verdict: it is either not written as a probe row (`probe`) or
  skipped by `proven`, so it never turns a proven stranger into an unproven one;
* something other than the start retries an unproven outsider -- the clock's look
  (`clock_look`) makes the outsider's ticket when no probe has passed and the newest probe did
  not run, at most once an hour; `run_outsider` then probes first;
* the probe's leak marker 'MEMORY.md' is dropped or made specific: today's re-run (2026-10-13
  17:02Z, after the OAuth lock was gone) ran, answered like a stranger ('I was given no project
  instructions, CLAUDE.md, memories ... I haven't been shown any MEMORY.md content') and was
  recorded NOT a stranger, because Claude Code's own memory prompt names the file and a denial
  repeats the name. Without this a retry that runs only swaps one failure for another.

The controls pass today and must keep passing: a probe that ran and quoted our CLAUDE.md is a
verdict and unproves the outsider; with no probe on record it is unproven.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from qa import crew, outsider
from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent

OAUTH = ("Failed to refresh OAuth token: another Claude Code process is refreshing it or "
         "exited mid-refresh. This is usually transient; retry in a minute")
# The answer of the 2026-10-13T17:02:31Z probe, recorded as 'it quoted context of ours: MEMORY.md'.
CLEAN_DENIAL = (
    "1) I don't have any specific knowledge of a repository called qa-cymetica. The names "
    "Cymetica, EventTrader, Nexus, and ET10 don't bring up anything reliable for me, so I "
    "won't guess at what they are or how they relate.\n\n2) I was given no project "
    "instructions, CLAUDE.md, memories, operator decisions, or file paths about this project. "
    "The only context besides your message is the environment info: the working directory is "
    "C:\\Users\\adamz\\AppData\\Local\\cymetica-outsider (not a git repo), and the memory "
    "directory path exists. I haven't read what's in it, and I haven't been shown any "
    "MEMORY.md content")


def _script(name: str):
    spec = importlib.util.spec_from_file_location(f"outsider_retry_{name}",
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
    # The laboratory's tick, stood in: it decides nothing, so any outsider ticket the clock
    # makes is the clock's own.
    monkeypatch.setenv("QA_CREW_TICK", json.dumps([sys.executable, "-c",
                                                   "print('decide: none')"]))
    return tmp_path


def _write_probes(rows: list[dict]) -> None:
    from qa.state import state_dir

    target = state_dir() / "outsider.jsonl"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def _probe(at: datetime, ok: bool, why: str = "") -> dict:
    return {"type": "probe", "at": at.isoformat(timespec="seconds"), "ok": ok, "why": why,
            "answer": ""}


def _did_not_run(at: datetime) -> dict:
    return _probe(at, False, f"the probe did not run (exit 1): {OAUTH}"[:200])


def _outsider_tickets() -> list[dict]:
    return [t for t in crew.tickets().values() if t["to"] == "outsider"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.xfail(strict=True, reason="T-0069: a probe that did not run (exit 1, OAuth lock) is "
                   "written as a probe row proven() reads as a verdict, so a proven stranger "
                   "becomes unproven by a lock that clears in a minute")
def test_a_probe_that_did_not_run_does_not_unprove_a_proven_outsider(company, monkeypatch):
    script = _script("outsider")
    now = datetime.now(timezone.utc)
    _write_probes([_probe(now - timedelta(days=1), True)])
    assert outsider.proven(script.load()), "control: the earlier probe passed"
    monkeypatch.setattr(script, "_claude", lambda *a, **k: (OAUTH, 1))
    script.probe()
    assert outsider.proven(script.load()), (
        "the probe never ran (exit 1) and the newest probe row now says ok false: the "
        "machinery's failure was recorded as the stranger's verdict")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_probe_that_ran_and_quoted_our_context_still_unproves_the_outsider(company):
    """Control, passes today: a verdict is not machinery."""
    now = datetime.now(timezone.utc)
    rows = [_probe(now - timedelta(days=1), True),
            _probe(now, False, "it quoted context of ours: Operating rules for qa-cymetica")]
    assert not outsider.proven(rows)
    assert not outsider.proven([])


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.xfail(strict=True, reason="T-0069: nothing but crew.py start probes, so the "
                   "outsider stays unproven and unticketed after a probe that did not run")
def test_the_clock_tickets_the_outsider_again_after_a_probe_that_did_not_run(company):
    now = datetime.now(timezone.utc)
    _write_probes([_did_not_run(now - timedelta(hours=2))])
    assert not _outsider_tickets()
    _script("crew").clock_look(now=now)
    made = _outsider_tickets()
    assert len(made) == 1, (
        f"the newest probe did not run two hours ago and no probe has ever passed: the clock "
        f"made {len(made)} outsider ticket(s); run_outsider would probe first, nothing else does")
    # At most hourly: a look half an hour later makes no second one, even if the first closed.
    for ticket in made:
        crew.claim("outsider")
        crew.close(ticket["id"], "fail", by="outsider", note="the probe did not run",
                   now=now + timedelta(minutes=1))
    _script("crew").clock_look(now=now + timedelta(minutes=30))
    assert len(_outsider_tickets()) == 1, "a second retry inside the hour"
    _script("crew").clock_look(now=now + timedelta(minutes=70))
    assert len(_outsider_tickets()) == 2, "no retry an hour on"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.xfail(strict=True, reason="T-0069: LEAKS holds 'MEMORY.md', which a stranger's "
                   "denial repeats from Claude Code's own memory prompt; the 17:02Z probe ran "
                   "clean and was recorded NOT a stranger")
def test_a_stranger_that_denies_having_seen_memory_md_is_a_stranger():
    ok, why = _script("outsider").independent(CLEAN_DENIAL, 0)
    assert ok, f"a denial naming the file was read as a leak: {why}"
    # Control inside the test: what only our context could say is still a leak.
    bad, _ = _script("outsider").independent(
        "The first line reads: Operating rules for qa-cymetica", 0)
    assert not bad

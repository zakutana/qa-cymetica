"""The auditor's 'stuck' counts from the company's start, as the watchdog's does (crew-before-c9 point 11).

`stuck_departments` takes `since` -- when the company last started -- so a ticket left waiting over a
weekend the company was switched off is not a stuck weekend. The watchdog passed it; `metrics`, the
auditor's daily half, called it without, so the day's review handed to the manager (and the patrol's
company section) called a department stuck that the watchdog, the same minute, did not.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from qa import crew
from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


def _script(name: str):
    spec = importlib.util.spec_from_file_location(f"stuck_since_{name}", REPO / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _noon_today() -> datetime:
    """Midday on the operator's clock: past the hour the day's review is due."""
    local = datetime.now().astimezone().replace(hour=12, minute=0, second=0, microsecond=0)
    return local.astimezone(timezone.utc)


@pytest.fixture
def company(tmp_path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("QA_REPO_ROOT", str(tmp_path / "no-repo"))
    monkeypatch.setenv("QA_CREW_TICK", json.dumps([sys.executable, "-c", "print('decide: none')"]))
    monkeypatch.delenv("QA_CREW_DEPT", raising=False)
    monkeypatch.delenv("QA_CREW_TICKET", raising=False)
    now = _noon_today()
    # A ticket opened three days ago, while the company was off; it started two hours ago.
    crew.add_ticket("lab", "lab", "answer NEX-0300", key="lab:NEX-0300",
                    by="session", now=now - timedelta(days=3))
    crew.set_running(True, now=now - timedelta(hours=2))
    # Stopping: the clock's look then heals nothing, so no loop is started by a test.
    (crew.crew_dir() / "stop").write_text("test", encoding="utf-8")
    return tmp_path, now


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_metrics_counts_stuck_from_the_start_it_is_given(company):
    _, now = company
    since = crew.running_since()
    assert crew.stuck_departments(crew.tickets(), [], now, since) == [], "control: the watchdog"
    assert crew.metrics(crew.tickets(), [], now)["departments"]["lab"]["state"] == "stuck", (
        "control: with no start known the ticket's own age decides")
    numbers = crew.metrics(crew.tickets(), [], now, since=since)
    assert numbers["departments"]["lab"]["state"] != "stuck", numbers["departments"]["lab"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_days_review_and_the_patrol_read_stuck_as_the_watchdog_does(company):
    root, now = company
    sup = _script("crew")
    sup.clock_look(now=now)
    rows = [r for r in crew.load(crew.runs_path()) if r.get("type") == "metrics"]
    assert rows, "the clock wrote no day's numbers"
    assert rows[-1]["departments"]["lab"]["state"] != "stuck", rows[-1]["departments"]["lab"]
    review = [t for t in crew.tickets().values() if t["kind"] == "daily"]
    assert review and not any("lab: stuck" in f for f in review[-1]["payload"]["flags"]), review

    section = _script("processes").crew_section(root)
    assert section["departments"]["lab"]["state"] != "stuck", section["departments"]["lab"]

"""The outsider's look is not done when acting on its picks failed (crew-before-c9 point 11).

`run_outsider` (scripts/crew.py) ran `lab.py outsider-act OUT-NNNN` and discarded what it returned,
so a look whose picks were never acted on -- a crash, their host refusing -- closed its ticket `ok`
and nobody heard of it. Acting is idempotent ("acting twice acts once", the laboratory's own test),
so the failure is said by name, spends one of the ticket's attempts, and three end with the
manager like any other ticket's. The stumbles and the coins' checkpoints are the run's, not the
act's: they are still handed on and read.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from qa import crew
from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
NOW = datetime(2026, 10, 25, 9, 0, tzinfo=timezone.utc)


def _script(name: str):
    spec = importlib.util.spec_from_file_location(f"act_exit_{name}", REPO / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def company(tmp_path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("QA_REPO_ROOT", str(tmp_path / "no-repo"))
    monkeypatch.setenv("QA_CREW_CLAUDE", json.dumps([sys.executable, "-c", "raise SystemExit(9)"]))
    monkeypatch.delenv("QA_CREW_DEPT", raising=False)
    monkeypatch.delenv("QA_CREW_TICKET", raising=False)
    return tmp_path


def _look(monkeypatch, act_code: int) -> tuple[dict, list[str], dict]:
    sup = _script("crew")
    run_row = {"type": "run", "id": "OUT-0004", "at": NOW.isoformat(),
               "stumbles": [{"where": "/agent-league", "what": "the join button 404s"}],
               "surfaces": []}
    steps: list[str] = []

    def fake_process(args, env, timeout):
        steps.append(" ".join([Path(args[1]).name, *args[2:]]))
        out, code = "", 0
        if args[-1] == "run":
            out = "OUT-0004: would deposit False, 2 pick(s) -- next: ..."
            path = Path(os.environ["QA_STATE_DIR"]) / "outsider.jsonl"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(run_row) + "\n", encoding="utf-8")
        elif "outsider-act" in args:
            out, code = "httpx.ConnectError: connection refused", act_code
        return {"pid": 1, "code": code, "stdout": out, "stderr": "", "timed_out": False,
                "seconds": 0.1}

    monkeypatch.setattr(sup, "run_process", fake_process)
    monkeypatch.setattr(sup, "outsider_proven", lambda: True)
    ticket, _ = crew.add_ticket("outsider", "outsider", "the daily look", now=NOW)
    row = sup.work_once("outsider")
    return row, steps, crew.tickets()[ticket["id"]]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_failed_act_spends_an_attempt_and_says_which_run(company, monkeypatch):
    row, steps, ticket = _look(monkeypatch, act_code=1)
    assert steps == ["outsider.py run", "lab.py outsider-act OUT-0004", "outsider.py track"], steps
    assert row["outcome"] == "work", row
    assert "OUT-0004" in row["why"] and "outsider-act" in row["why"], row["why"]
    assert ticket["status"] != "done" and ticket.get("attempts") == 1, ticket
    # The act's own words never decide it was the CLI's machinery: a 'connection refused' in
    # them is their host, met by our code, not a logged-out claude every ticket shares.
    assert not row.get("widespread"), row
    handed = [t for t in crew.tickets().values() if t["from"] == "outsider"]
    assert [t["key"] for t in handed] == ["OUT-0004-S1"], "the run's stumbles are its own"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_act_that_ran_closes_the_look(company, monkeypatch):
    """Control: the same look with the act's exit 0 is done."""
    row, _, ticket = _look(monkeypatch, act_code=0)
    assert row["outcome"] == "ok" and ticket["status"] == "done", (row, ticket)

"""What a new session is told, and that telling it can never stop the session."""

from __future__ import annotations

import importlib.util
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent.parent / ".claude" / "hooks"


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _outcome(ticket, kind="file", outcome="accepted"):
    return {"type": "outcome", "kind": kind, "ticket": ticket, "outcome": outcome}


def test_a_verdict_is_owed_on_a_shipped_ticket_of_ours_only():
    start = _load(HOOKS / "start" / "verdict_owed.py")
    rows = [_outcome("ET-1"), _outcome("ET-2"), _outcome("ET-3"), _outcome("ET-3", "verdict"),
            _outcome("ET-4"), _outcome("ET-5", "change")]
    items = [{"ticket": "ET-1", "stage": "shipped"},                     # owed
             {"ticket": "ET-2", "stage": "building"},                    # not shipped yet
             {"ticket": "ET-3", "stage": "shipped"},                     # we judged it
             {"ticket": "ET-4", "stage": "shipped", "verdict": "pass"},  # their record holds one
             {"ticket": "ET-5", "stage": "shipped"},                     # filed on their form, acted on here
             {"ticket": "ET-9", "stage": "shipped"}]                     # not ours
    assert start.owed(items, rows) == ["ET-1", "ET-5"]


def test_a_source_that_breaks_costs_only_its_own_line(monkeypatch):
    hook = _load(HOOKS / "session_start.py")
    monkeypatch.setattr(hook, "SOURCES", (("does_not_exist", "lines"), ("next_step", "summary")))
    monkeypatch.setenv("QA_NEXT_FILE", str(HOOKS / "nothing-here.md"))
    assert hook.gather() == []
    assert hook.main() == 0


def test_next_md_reads_open_items_only(tmp_path, monkeypatch):
    start = _load(HOOKS / "start" / "next_step.py")
    next_file = tmp_path / "NEXT.md"
    next_file.write_text("```\n- [ ] YYYY-MM-DD  the format\n```\n- [x] 2026-11-01  done\n- [ ] 2026-11-02  to do\n",
                         encoding="utf-8")
    monkeypatch.setenv("QA_NEXT_FILE", str(next_file))
    assert start.summary() == ["NEXT.md: 1 open, read it whole -- first: to do"]

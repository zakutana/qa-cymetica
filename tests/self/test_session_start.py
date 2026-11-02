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
    rows = [_outcome("ET-1"), _outcome("ET-2"), _outcome("ET-3"), {**_outcome("ET-3", "verdict"), "at": "2026-11-01T10:00:00+00:00"},
            _outcome("ET-4"), _outcome("ET-5", "change")]
    items = [{"ticket": "ET-1", "stage": "shipped"},                     # owed
             {"ticket": "ET-2", "stage": "building"},                    # not shipped yet
             {"ticket": "ET-3", "stage": "shipped", "resolved_at": "2026-11-01T09:00:00+00:00"},  # we judged it since
             {"ticket": "ET-4", "stage": "shipped", "verdict": "pass"},  # their record holds one
             {"ticket": "ET-5", "stage": "shipped"},                     # filed on their form, acted on here
             {"ticket": "ET-9", "stage": "shipped"}]                     # not ours
    assert start.owed(items, rows) == ["ET-1", "ET-5"]


def test_a_ticket_named_in_next_md_counts_as_ours():
    start = _load(HOOKS / "start" / "verdict_owed.py")
    items = [{"ticket": "ET-32976", "stage": "shipped"}, {"ticket": "ET-1", "stage": "shipped"}]
    assert start.owed(items, [], named={"ET-32976"}) == ["ET-32976"]


def test_a_rework_shipped_after_our_fail_is_owed_again():
    start = _load(HOOKS / "start" / "verdict_owed.py")
    rows = [_outcome("ET-1"), {**_outcome("ET-1", "verdict"), "at": "2026-11-01T10:00:00+00:00"}]
    shipped = {"ticket": "ET-1", "stage": "shipped", "verdict": "fail", "resolved_at": "2026-11-02T10:00:00+00:00"}
    assert start.owed([shipped], rows) == ["ET-1"]
    assert start.owed([{**shipped, "resolved_at": "2026-11-01T09:00:00+00:00"}], rows) == []
    assert start.owed([{**shipped, "verdict": "pass"}], rows) == []


def test_the_casino_is_named_when_nobody_has_ticked_it_for_a_day():
    start = _load(HOOKS / "start" / "casino_quiet.py")
    from datetime import datetime, timezone

    now = datetime(2026, 11, 2, 12, tzinfo=timezone.utc)
    assert start.quiet([{"type": "tick", "at": "2026-11-02T01:00:00+00:00"}], now) == []
    said = start.quiet([{"type": "tick", "at": "2026-11-01T01:00:00+00:00"}], now)
    assert len(said) == 1 and "35 h" in said[0] and "/loop 30m jdi do casina" in said[0]
    assert start.quiet([{"type": "note", "at": "2026-11-01T01:00:00+00:00"}], now) == []


def test_a_source_that_breaks_costs_only_its_own_line(tmp_path, monkeypatch, capsys):
    hook = _load(HOOKS / "session_start.py")
    next_file = tmp_path / "NEXT.md"
    next_file.write_text("- [ ] 2026-11-02  to do\n", encoding="utf-8")
    monkeypatch.setenv("QA_NEXT_FILE", str(next_file))
    monkeypatch.setattr(hook, "SOURCES", (("does_not_exist", "lines"), ("next_step", "summary")))
    assert hook.main() == 0
    assert "to do" in capsys.readouterr().out


def test_next_md_reads_open_items_only(tmp_path, monkeypatch):
    start = _load(HOOKS / "start" / "next_step.py")
    next_file = tmp_path / "NEXT.md"
    next_file.write_text("```\n- [ ] YYYY-MM-DD  the format\n```\n- [x] 2026-11-01  done\n- [ ] 2026-11-02  to do\n",
                         encoding="utf-8")
    monkeypatch.setenv("QA_NEXT_FILE", str(next_file))
    assert start.summary() == ["NEXT.md: 1 open, read it whole -- first: to do"]

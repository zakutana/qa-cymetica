"""Nexus's credit on /lab: Cymetica's build plan, read by the laboratory tick.

NEXT.md, agreed 2026-09-26: the tick reads GET /api/v1/nexus/usage -- the
build allowance of Cymetica's plan on our account, readable with our key since
ET-27414 -- and /lab shows its 5-hour and weekly windows and what used them.
Beside it, how many questions their deep lane turned away with "Hourly
deep-answer limit": that limit is not in /usage, so it is counted from
state/nexus.jsonl, where each one is a `gave_up` row carrying the error.

Cymetica's credit, not the operator's Claude plan. CLAUDE.md keeps that one
theirs to watch; nothing here reads it, and nothing here acts on a percentage
of this one either -- it is shown, that is all.

The fixture is the body /api/v1/nexus/usage answered our key on 2026-09-28 at
20:29 UTC, trimmed: `plans` and `flags` cut, two of its eight `items` and two
of its seven `history` days kept. Reading it spent nothing: its items are the
Build it Better requests and creator pages we filed, and no read appears.
"""

from __future__ import annotations

import importlib.util
import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

from qa.marks import SafetyTier, qa
from tests.meta.test_pipeline_lab_loop import _doors, _scripts_lab

REPO = Path(__file__).resolve().parent.parent.parent
USAGE_PATH = "/api/v1/nexus/usage"
NOW = datetime(2026, 9, 28, 20, 30, tzinfo=timezone.utc)

USAGE = {
    "enabled": True, "plan": "pro", "plan_name": "Pro", "multiplier": "1",
    "price_usdc": "20.00",
    "session": {"active": True, "used_units": "0.650000", "cap_units": "1.000000",
                "used_pct": 65, "started_at": "2026-09-28T18:36:48.639000+00:00",
                "resets_at": "2026-09-28T23:36:48.639000+00:00",
                "resets_in_s": 11248, "resets_label": "11:36pm UTC", "hours": 5},
    "week": {"used_units": "2.300000", "cap_units": "6.000000", "used_pct": 38,
             "week_start": "2026-09-26T16:00:00+00:00",
             "resets_at": "2026-10-03T16:00:00+00:00", "resets_in_s": 415840,
             "resets_label": "Sat 4:00pm UTC", "anchor": {"dow": 5, "minute": 960}},
    "extra_usage": {"enabled": False, "month_spend_usdc": "0.45",
                    "monthly_cap_usdc": None, "markup": "3"},
    "limit_resets_available": 1, "warn_pct": 75, "critical_pct": 90,
    "as_of": "2026-09-28T20:29:19.866499+00:00",
    "breakdown": [{"kind": "bb_request", "label": "Build it Better requests",
                   "units": "2.000000", "pct": 80}],
    "items": [
        {"kind": "bb_change", "label": "Build it Better scope changes",
         "units": "0.150000", "at": "2026-09-28T18:38:29.864654+00:00",
         "ref": "ET-28203:20260928183829830421", "link": None, "overage": False},
        {"kind": "bb_request", "label": "Build it Better requests",
         "units": "0.500000", "at": "2026-09-28T18:36:48.720795+00:00",
         "ref": "ET-28203", "link": None, "overage": False}],
    "history": [{"day": "2026-09-27", "units": "0.500000"},
                {"day": "2026-09-28", "units": "0.650000"}],
}

# How nexus.py writes a question their deep lane turned away at its hourly
# limit (NEX-0101, 2026-09-26 04:27:52), and one it failed for another reason.
REFUSED = {"type": "gave_up", "job_id": "7224fce6", "waited_seconds": 0.0,
           "polls": 1, "status": "failed",
           "error": "Hourly deep-answer limit reached — retry later.",
           "retryable": True, "retry_after_s": 30}
OTHER = {"type": "gave_up", "status": "failed", "retryable": True,
         "error": "The deep-answer run could not be completed. Retry "
                  "ask_nexus_deep after retry_after_s seconds."}


def _nexus_rows():
    def at(minutes):
        return (NOW - timedelta(minutes=minutes)).isoformat()
    return [
        {"type": "question", "id": "NEX-0201", "at": at(50)},
        {**REFUSED, "id": "NEX-0201", "at": at(50)},
        {**REFUSED, "id": "NEX-0201", "at": at(49)},   # the same question twice
        {**REFUSED, "id": "NEX-0202", "at": at(20)},
        {**REFUSED, "id": "NEX-0199", "at": at(300)},  # today, not this hour
        {**REFUSED, "id": "NEX-0100", "at": at(60 * 30)},  # yesterday
        {**OTHER, "id": "NEX-0203", "at": at(10)},     # another failure
    ]


def _script(name: str):
    spec = importlib.util.spec_from_file_location(
        f"{name}_credit_under_test", REPO / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _client(answer):
    """The guarded client over a transport that answers locally."""
    from qa.client import build_client
    from qa.config import identities
    from qa.safety import EndpointRegistry

    return build_client(identities()["anon"], EndpointRegistry.load(),
                        base_url="https://cymetica.com",
                        inner=httpx.MockTransport(answer))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_reading_keeps_both_windows_and_an_unread_one_holds_no_number():
    from qa import lab

    reading = lab.credit_reading(200, USAGE)
    assert reading["read"] is True and reading["plan"] == "Pro"
    assert reading["session"] == {"pct": 65, "used": 0.65, "cap": 1.0,
                                  "resets_at": "2026-09-28T23:36:48.639000+00:00"}
    assert reading["week"] == {"pct": 38, "used": 2.3, "cap": 6.0,
                               "resets_at": "2026-10-03T16:00:00+00:00"}
    assert (reading["warn_pct"], reading["critical_pct"]) == (75, 90)
    assert reading["as_of"] == USAGE["as_of"]
    assert reading["items"] == 2
    assert reading["last_item"] == {"label": "Build it Better scope changes",
                                    "units": 0.15, "at": USAGE["items"][0]["at"]}

    # Rule 8: a refusal, a body without a window, a window without its
    # percentage, a body that is not an object, no answer at all -- each is
    # unread with its reason, and none carries a number that could be taken
    # for a reading of zero.
    for status, body, why in (
            (503, {"detail": "busy"}, "HTTP 503"),
            (401, {"detail": "Valid JWT token required"}, "HTTP 401"),
            (200, {**USAGE, "session": None}, "session"),
            (200, {**USAGE, "week": {**USAGE["week"], "used_pct": None}}, "week"),
            (200, ["not", "an", "object"], "object"),
            (None, None, "ReadTimeout")):
        said = lab.credit_reading(status, body, why="ReadTimeout" if status is None else "")
        assert said["read"] is False and why in said["why"], (status, said)
        assert set(said) == {"read", "why"}, f"an unread reading carries {sorted(said)}"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_door_is_one_get_with_our_key_and_a_dead_one_is_unread():
    """nexus.py's `credit`: one GET of /usage and nothing else, answered by
    the reading above; a server that does not answer is an unread reading,
    never an exception that stops the tick and never a zero."""
    nexus = _script("nexus")
    seen = []

    def answer(request):
        seen.append((request.method, request.url.path))
        return httpx.Response(200, json=USAGE)

    reading = nexus.credit(_client(answer))
    assert seen == [("GET", USAGE_PATH)], seen
    assert reading["read"] is True and reading["week"]["pct"] == 38

    def dead(request):
        raise httpx.ConnectError("no route to host", request=request)

    said = nexus.credit(_client(dead))
    assert said == {"read": False, "why": "ConnectError"}, said
    said = nexus.credit(_client(lambda r: httpx.Response(502, text="bad gateway")))
    assert said == {"read": False, "why": "HTTP 502"}, said


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_tick_reads_the_credit_onto_its_own_row(tmp_path, monkeypatch):
    """The reading rides on the tick's row in state/lab.jsonl, like the
    memecoin and Hot rounds. Unlike them it waits while a deep pass or a
    night holds the tick (test_a_tick_during_a_deep_pass_or_a_night_only_
    reads_memecoins_and_hot): /usage always answers the present, so a
    reading skipped is not a moment lost, and /lab keeps the last one under
    its own time. A door that breaks is the tick's error, not its end."""
    from qa import lab

    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    assert "credit" in scripts_lab._tick_doors()
    reading = lab.credit_reading(200, USAGE)

    doors, calls = _doors(credit=lambda: reading)
    said = scripts_lab.tick(now=NOW, actions=doors, out=lambda *a: None)
    assert said["credit"] == reading
    assert lab.last_tick()["credit"] == reading

    # Kept whole only when it moved: an unchanged plan read 72 times a day
    # would be ~31 KB a day into audits/lab, which git keeps (CLAUDE.md, What
    # we keep). The next tick's row says only when it was read again.
    later = {**reading, "as_of": "2026-09-28T20:49:19+00:00"}
    doors, _ = _doors(credit=lambda: later)
    said = scripts_lab.tick(now=NOW + timedelta(minutes=10), actions=doors,
                            out=lambda *a: None)
    assert said["credit"] == {"read": True, "same": True, "as_of": later["as_of"]}
    view = lab.credit_view(lab.load(), [], NOW + timedelta(minutes=10))
    assert (view["week_pct"], view["at"]) == (38, later["as_of"]), view
    moved = {**later, "week": {**later["week"], "pct": 46}}
    doors, _ = _doors(credit=lambda: moved)
    said = scripts_lab.tick(now=NOW + timedelta(minutes=15), actions=doors,
                            out=lambda *a: None)
    assert said["credit"] == moved, "a reading that moved is kept whole"
    doors, _ = _doors(credit=lambda: reading)
    scripts_lab.tick(now=NOW + timedelta(minutes=18), actions=doors, out=lambda *a: None)

    held = []
    doors, _ = _doors(credit=lambda: held.append(1) or reading,
                      **{"pass": lambda: True})
    said = scripts_lab.tick(now=NOW + timedelta(minutes=20), actions=doors,
                            out=lambda *a: None)
    assert said["skipped"] == "pass" and said["credit"] is None and not held
    assert lab.credit_view(lab.load(), [], NOW)["week_pct"] == 38, (
        "the reading before the pass is still the one /lab shows")

    def broken():
        raise RuntimeError("boom")
    doors, _ = _doors(credit=broken)
    said = scripts_lab.tick(now=NOW + timedelta(minutes=40), actions=doors,
                            out=lambda *a: None)
    assert said["credit"] is None
    assert any(e.startswith("credit:") for e in said["errors"]), said["errors"]
    assert said["decide"] is not None, "the tick went on to decide"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_hourly_limit_refusals_are_counted_per_question():
    from qa import lab

    rows = _nexus_rows()
    assert lab.hourly_limit_refusals(rows, NOW, hours=1) == 2
    assert lab.hourly_limit_refusals(rows, NOW, hours=24) == 3
    assert lab.hourly_limit_refusals([], NOW, hours=1) == 0


def _credit_view(tick_credits):
    from qa import lab

    rows = [{"type": "tick", "at": (NOW - timedelta(minutes=20 * (len(tick_credits) - i))
                                    ).isoformat(), "credit": c}
            for i, c in enumerate(tick_credits)]
    return lab.credit_view(rows, _nexus_rows(), NOW)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_view_is_the_newest_reading_and_says_when_the_newest_read_failed():
    from qa import lab

    reading = lab.credit_reading(200, USAGE)
    view = _credit_view([reading])
    assert (view["plan"], view["session_pct"], view["week_pct"]) == ("Pro", 65, 38)
    assert view["unread"] is None and view["at"] == USAGE["as_of"]
    assert (view["refusals_hour"], view["refusals_day"]) == (2, 3)

    # The newest read failed: the older numbers stay, under their own time,
    # and the failure is said beside them.
    view = _credit_view([reading, {"read": False, "why": "HTTP 503"}])
    assert view["unread"] == "HTTP 503" and view["week_pct"] == 38
    assert view["at"] == USAGE["as_of"]

    # Never read: no number at all, and the refusals still counted.
    view = _credit_view([{"read": False, "why": "ConnectError"}])
    assert view["session_pct"] is None and view["week_pct"] is None
    assert view["unread"] == "ConnectError" and view["refusals_hour"] == 2
    none = lab.credit_view([], [], NOW)
    assert none["at"] is None and none["unread"] is None

    # C01, deep pass of 2026-09-30 (3/3): two readings that differ, so the
    # newest is told from the oldest; and an old failure followed by a good
    # read is no longer "unread".
    newer = lab.credit_reading(200, {**USAGE, "week": {**USAGE["week"], "used_pct": 46},
                                     "as_of": "2026-09-28T20:49:19+00:00"})
    view = _credit_view([reading, newer])
    assert view["week_pct"] == 46 and view["at"] == "2026-09-28T20:49:19+00:00", (
        "the view showed the oldest reading, not the newest", view)
    view = _credit_view([{"read": False, "why": "HTTP 503"}, reading])
    assert view["unread"] is None and view["week_pct"] == 38, (
        "an earlier failure was said over a newer good reading", view)


def _lab_view(credit):
    from tests.meta.test_pipeline_lab_page import CHANNEL, FOMO, _report, _rooms_view
    from tests.meta.test_pipeline_render import _lab_page

    return _lab_page().lab_view(_rooms_view(), _report(), CHANNEL, FOMO,
                                now=NOW, credit=credit)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_lab_shows_the_credit_in_numbers_and_reads_every_field_it_is_given(tmp_path):
    """On the Nexus line, English, numbers first: the plan, both windows and
    when they reset, what used them, and the refusals -- named as Cymetica's,
    so it cannot be read as the operator's own plan. Every `cr.` field the
    view writes is drawn and the page reads no other (the rule
    test_the_page_reads_every_field_the_view_writes_and_no_other holds for
    the other shapes)."""
    from qa import lab
    from tests.meta.test_pipeline_render import _lab_page, _run_page

    view = _lab_view(_credit_view([lab.credit_reading(200, USAGE)]))
    written = set(view["nexus"]["credit"])
    read = set(re.findall(r"\bcr\.([A-Za-z_][A-Za-z0-9_]*)", _lab_page().TEMPLATE))
    assert read, "the page reads no `cr.` field"
    assert not read - written, f"/lab reads credit fields never written: {sorted(read - written)}"
    assert not written - read, f"credit fields written and never shown: {sorted(written - read)}"

    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed, so the page cannot be run here")
    code, err, captured = _run_page(node, tmp_path / "credit", view, page=_lab_page())
    assert code == 0, err[:1200]
    line = captured.get("nexus", "")
    for shown in ("Nexus credit", "Pro", "65%", "38%", "2 items",
                  "Build it Better scope changes", "hourly limit"):
        assert shown in line, (shown, line)
    assert "Claude" not in line

    unread = _lab_view(_credit_view([lab.credit_reading(200, USAGE),
                                     {"read": False, "why": "HTTP 503"}]))
    code, err, captured = _run_page(node, tmp_path / "unread", unread, page=_lab_page())
    assert code == 0, err[:1200]
    assert "HTTP 503" in captured.get("nexus", "") and "38%" in captured.get("nexus", "")

    # Without a credit at all the line is the one it was.
    bare = _lab_view(None)
    code, err, captured = _run_page(node, tmp_path / "bare", bare, page=_lab_page())
    assert code == 0 and "Nexus credit" not in captured.get("nexus", ""), err[:1200]

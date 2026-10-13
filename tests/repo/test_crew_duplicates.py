"""The daily metrics' "same work twice" flag fires on work that was not done twice (T-0070).

`qa/crew.py::metrics` groups every ticket opened in the window by (to, text[:120]) and
`metric_flags` names each group of two or more. The clock's own tickets carry fixed texts
("hunt sweep", "gap", "one step towards ..."), so the flag was on by construction: T-0066 named
desk T-0004..T-0045 (eight sequential steps), bugs T-0002/T-0065 (a day apart) and lab
T-0008/T-0012 (two ticks, two different gaps; the first closed at 17:05, the second opened at
17:16). A flag that fires every day is read by nobody. `route()` already holds a sweep behind a
live sweep and a lab item behind a live one, so a clock ticket opened while its twin is still
live is the case worth flagging.

What a duplicate is (the manager's decision, T-0070): two tickets with the same (to, text)
whose lives overlapped -- the second opened before the first closed (an unclosed ticket is
live up to now) -- or the same (to, text) from any sender but the clock.

The fix is `qa/crew.py::metrics` (the grouping at "groups: dict[tuple, list[str]]"), which a
worker cannot write. It must replace the plain grouping with:
  * for tickets whose "from" is "clock": sort by "at"; a ticket joins its group when it opened
    before the previous one's "closed_at" (a ticket with "closed_at" None is live: compare to
    `now`), so the group holds the overlapping tickets and nothing else;
  * for tickets whose "from" is anything else (a missing "from" counts): the plain group as
    today, two or more of them;
and keep the output shape {"to", "text", "tickets": [ids]}, so `metric_flags` and its existing
test (tests/meta/test_pipeline_crew.py) are untouched.

The controls pass today and must keep passing: overlapping clock tickets, and the same text from
the operator or a department, are still flagged.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from qa import crew
from qa.marks import SafetyTier, qa

import pytest

NOW = datetime(2026, 10, 13, 18, 0, tzinfo=timezone.utc)


def _ago(hours: float) -> str:
    return crew.stamp(NOW - timedelta(hours=hours))


def _ticket(tid: str, to: str, text: str, by: str, opened_h: float,
            closed_h: float | None) -> list[dict]:
    rows = [{"type": "ticket", "id": tid, "at": _ago(opened_h), "from": by, "to": to,
             "kind": "step", "key": tid, "text": text}]
    if closed_h is not None:
        rows.append({"type": "done", "id": tid, "at": _ago(closed_h), "by": to})
    return rows


def _numbers(*tickets: list[dict]) -> dict:
    rows = [row for ticket in tickets for row in ticket]
    return crew.metrics(crew.fold(rows), [], NOW)


def _ids(numbers: dict) -> list[list[str]]:
    return [d["tickets"] for d in numbers["duplicates"]]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.xfail(strict=True, reason="T-0070: metrics groups the clock's fixed texts by "
                   "(to, text) alone, so eight sequential desk steps read as the same work twice")
def test_sequential_clock_tickets_with_one_text_are_not_a_duplicate():
    """Each closed before the next opened: the clock's cadence, not the same work twice."""
    numbers = _numbers(
        _ticket("T-0004", "desk", "one step towards proving", "clock", 9, 8.5),
        _ticket("T-0011", "desk", "one step towards proving", "clock", 7, 6.5),
        _ticket("T-0020", "desk", "one step towards proving", "clock", 5, 4.5))
    assert numbers["duplicates"] == [], numbers["duplicates"]
    assert crew.metric_flags(numbers) == [], crew.metric_flags(numbers)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.xfail(strict=True, reason="T-0070: lab T-0008 closed 17:05 and T-0012 opened 17:16 "
                   "were flagged as the same gap twice")
def test_a_clock_ticket_opened_after_its_twin_closed_is_not_a_duplicate():
    numbers = _numbers(
        _ticket("T-0008", "lab", "gap", "clock", 3, 2.0),
        _ticket("T-0012", "lab", "gap", "clock", 1.8, None))
    assert numbers["duplicates"] == [], numbers["duplicates"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_clock_ticket_opened_while_its_twin_is_still_live_is_a_duplicate():
    """Control: closed after the second opened, and never closed at all, both overlap."""
    overlapped = _numbers(
        _ticket("T-0001", "bugs", "hunt sweep", "clock", 4, 1.0),
        _ticket("T-0002", "bugs", "hunt sweep", "clock", 2, 0.5))
    assert _ids(overlapped) == [["T-0001", "T-0002"]]
    still_live = _numbers(
        _ticket("T-0003", "bugs", "hunt sweep", "clock", 4, None),
        _ticket("T-0004", "bugs", "hunt sweep", "clock", 2, None))
    assert _ids(still_live) == [["T-0003", "T-0004"]]
    assert any("twice" in line for line in crew.metric_flags(overlapped))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_same_text_from_anyone_but_the_clock_is_a_duplicate_even_when_sequential():
    """Control: a person or department asking twice is the same work asked twice."""
    numbers = _numbers(
        _ticket("T-0001", "bugs", "500 on /movers", "manager", 5, 4),
        _ticket("T-0002", "bugs", "500 on /movers", "manager", 3, 2))
    assert _ids(numbers) == [["T-0001", "T-0002"]]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.xfail(strict=True, reason="T-0070: the groups must hold only the tickets that "
                   "overlapped, not every clock ticket that shares the text")
def test_a_group_names_only_the_overlapping_clock_tickets():
    numbers = _numbers(
        _ticket("T-0001", "lab", "gap", "clock", 9, 8),
        _ticket("T-0002", "lab", "gap", "clock", 5, 3),
        _ticket("T-0003", "lab", "gap", "clock", 4, 2))
    assert _ids(numbers) == [["T-0002", "T-0003"]], _ids(numbers)

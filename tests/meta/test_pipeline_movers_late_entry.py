"""The judgement behind the late-entry check, offline.

Fixtures are the real round captured 2026-09-13: anchor 2026-09-11, scores
after 2026-09-18, no field anywhere naming when entries stop.

The branches that matter are the ones that make it SHUT UP -- a check that
fires on an anchor struck this morning, or on a round already scored, would
be a date comparison pretending to be a finding.
"""

from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent

ROUND = {"round_anchor": "2026-09-11", "entries": 5, "traders": 1,
         "scores_after": "2026-09-18"}
RULES = {"max_picks": 5, "window_days": 7,
         "text": ("Enter up to 5 universe symbols per round. Each pick locks "
                  "the stored close on the round day and is scored a week "
                  "later on its real 7-day return.")}


def _check():
    spec = importlib.util.spec_from_file_location(
        "movers_late_check",
        REPO / "tests" / "rest" / "test_movers_round_prices_a_late_entry.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_day_we_actually_entered_reproduces_the_finding():
    mod = _check()
    verdict, why = mod.decide(ROUND, RULES, date(2026, 9, 13))
    assert verdict == "failed", why
    assert "2 of its 7 days" in why, why


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_it_says_nothing_on_the_anchor_day_itself():
    """The day the round opens, the tournament behaves exactly right."""
    mod = _check()
    assert mod.decide(ROUND, RULES, date(2026, 9, 11))[0] == "inconclusive"
    # And not on a day before it either, if their clock runs ahead of ours.
    assert mod.decide(ROUND, RULES, date(2026, 9, 10))[0] == "inconclusive"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_round_already_scored_is_not_one_that_can_be_entered_late():
    mod = _check()
    verdict, why = mod.decide(ROUND, RULES, date(2026, 9, 18))
    assert verdict == "inconclusive", why
    verdict, why = mod.decide(ROUND, RULES, date(2026, 9, 25))
    assert verdict == "inconclusive", why


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_gap_grows_and_the_reason_says_by_how_much():
    """Day six is the case worth naming: one day of seven left unknown."""
    mod = _check()
    verdict, why = mod.decide(ROUND, RULES, date(2026, 9, 17))
    assert verdict == "failed"
    assert "6 of its 7 days" in why, why


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_any_declared_deadline_clears_it_whatever_it_is_called():
    """Three shapes of the weakest honest repair, plus one on the rules."""
    mod = _check()
    for extra in ({"entries_close": "2026-09-11T21:00:00Z"},
                  {"closes_at": "2026-09-11"},
                  {"entries_closed": True}):
        verdict, why = mod.decide({**ROUND, **extra}, RULES, date(2026, 9, 13))
        assert verdict == "passed", (extra, why)
    verdict, why = mod.decide(
        ROUND, {**RULES, "entry_deadline": "anchor day, 21:00 UTC"},
        date(2026, 9, 13))
    assert verdict == "passed", why


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_round_with_no_anchor_is_not_a_finding():
    mod = _check()
    assert mod.decide({"scores_after": "2026-09-18"}, RULES,
                      date(2026, 9, 13))[0] == "inconclusive"

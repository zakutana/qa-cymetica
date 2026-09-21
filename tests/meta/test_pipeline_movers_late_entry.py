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
def test_a_weekend_entry_gains_nothing_and_the_reason_must_say_so():
    """The first version of this check overstated its own evidence.

    The anchor is Friday 2026-09-11 and we entered Sunday 2026-09-13, so the
    reason said "2 of its 7 days have already happened, at a price that cannot
    move" -- and that went to Cymetica in report #101. Between a Friday close
    and a Sunday, US equities hold **no sessions at all**: four of our five
    picks are asset_class equity, their own listing was answering
    `us_market_open: false`, and the information we could have had was zero.

    The structural defect is untouched -- an entry on Thursday 2026-09-17 gets
    three real sessions of hindsight at Friday's price. What was wrong was
    counting calendar days and calling them observable. So the count is
    sessions, and a window with none reports the opening honestly instead of
    claiming an advantage that a closed market could not give.
    """
    mod = _check()
    verdict, why = mod.decide(ROUND, RULES, date(2026, 9, 13))
    assert verdict == "failed", "the window being open is still the finding"
    assert "0 trading session" in why, why
    assert "2 of its 7 days" not in why, (
        "calendar days must not be presented as observable return")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_late_weekday_entry_is_where_the_hindsight_actually_is():
    """Thursday of the round week: three sessions run, price still Friday's."""
    mod = _check()
    verdict, why = mod.decide(ROUND, RULES, date(2026, 9, 17))
    assert verdict == "failed", why
    # Mon 14, Tue 15, Wed 16 closed; Thu itself has not. Three, not four --
    # the first draft of this assertion said four and the guard caught it,
    # which is the same arithmetic that went wrong in the filed report.
    assert "3 trading session" in why, why


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
def test_sessions_are_counted_from_the_day_after_the_anchor_close():
    """The anchor price is that day's CLOSE, so the anchor day itself is not
    hindsight -- it is already spent when the price is struck. Off by one here
    is off by one in a number we send them."""
    mod = _check()
    # Monday: Friday's close struck, then Mon has not closed -> 0 sessions.
    assert "0 trading session" in mod.decide(ROUND, RULES, date(2026, 9, 14))[1]
    # Tuesday: Monday ran.
    assert "1 trading session" in mod.decide(ROUND, RULES, date(2026, 9, 15))[1]


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
    # V07, deep pass of 2026-09-19 (3/3): "whatever it is called" was six
    # names, so a deadline under a seventh FAILED their repair.
    for extra in ({"entry_cutoff": "2026-09-11T21:00:00Z"},
                  {"entries_close_time": "21:00 UTC"},
                  {"submissions_lock_at": "2026-09-11"}):
        verdict, why = mod.decide({**ROUND, **extra}, RULES, date(2026, 9, 13))
        assert verdict == "passed", (extra, why)
    # C02, deep pass of 2026-09-21: the widening stopped at three suffixes, so
    # a date suffix, `until`, a window that ends, or the round's own prefix
    # still read as no deadline -- a false FAIL on #101 after their repair.
    for extra in ({"entries_close_date": "2026-09-11"},
                  {"entries_until": "2026-09-11T21:00:00Z"},
                  {"entry_window_ends_at": "2026-09-11T21:00:00Z"},
                  {"round_entry_deadline": "2026-09-11"}):
        verdict, why = mod.decide({**ROUND, **extra}, RULES, date(2026, 9, 13))
        assert verdict == "passed", (extra, why)
        verdict, why = mod.decide(ROUND, {**RULES, **extra}, date(2026, 9, 13))
        assert verdict == "passed", ("on the rules", extra, why)
    # And a field that is about something else is not a deadline for entries:
    # a market's close, a timestamp of the round that says nothing about when
    # entering stops, or the close price an entry was struck at.
    for extra in ({"trading_closes_at": "2026-09-11"},
                  {"created_at": "2026-09-11T00:00:00Z"},
                  {"round_start": "2026-09-11"},
                  {"entry_close_price": 335.80}):
        verdict, why = mod.decide({**ROUND, **extra}, RULES, date(2026, 9, 13))
        assert verdict == "failed", (extra, why)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_rules_that_no_longer_price_at_the_round_day_are_not_failed():
    """V07 (3/3), the second repair the module docstring accepts: a late entry
    priced at its OWN day. It shows only in the rules text -- this check never
    enters a round -- and `decide` never read that text, so their rules
    reworded to price each pick when it is entered still FAILED, quoting the
    old rule back to them."""
    mod = _check()
    repaired = {**RULES, "text": ("Enter up to 5 universe symbols per round. "
                                  "Each pick locks the close of the day it is "
                                  "entered and is scored on its 7-day return.")}
    verdict, why = mod.decide(ROUND, repaired, date(2026, 9, 13))
    assert verdict == "inconclusive", why
    assert "round day" in why, why

    # C03, deep pass of 2026-09-21: and the defect reworded is still the
    # defect. The rule was the literal "round day", so a hyphen, an underscore
    # or a possessive read as their repair and the check went quiet with the
    # pricing unchanged.
    for said in ("locks the stored close on the round-day",
                 "locks the stored close on the round_day",
                 "locks the stored close on the Round Day",
                 "locks the round day's stored close",
                 "locks the round's day close",
                 "locks the stored close on the "
                 "round\N{RIGHT SINGLE QUOTATION MARK}s day"):
        reworded = {**RULES, "text": (f"Enter up to 5 universe symbols per "
                                      f"round. Each pick {said} and is scored "
                                      f"a week later on its real 7-day return.")}
        verdict, why = mod.decide(ROUND, reworded, date(2026, 9, 13))
        assert verdict == "failed", (said, why)
        # And the reason quotes what THEIR text says, not our transcription of
        # the old wording -- the reason goes to them.
        assert said in why, (said, why)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_field_saying_entries_are_still_open_is_not_a_deadline():
    """The filed defect, restated in their own payload, was clearing itself.

    `declares_a_deadline` tested `is not None`, and `entries_closed` is one of
    the fields it looks for -- so `{"entries_closed": false}`, which says in
    so many words that entries are STILL OPEN, returned `passed` with the
    reason "the round declares when entries stop being accepted". That is the
    PASS verification on #101. Presence against a contract about a value, the
    same shape as the house row's `basis` on the sibling check.
    """
    mod = _check()
    verdict, why = mod.decide({**ROUND, "entries_closed": False}, RULES,
                              date(2026, 9, 13))
    assert verdict == "failed", why
    verdict, why = mod.decide({**ROUND, "entries_open": True}, RULES,
                              date(2026, 9, 13))
    assert verdict == "failed", why


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_their_own_word_that_entries_are_shut_is_believed():
    """The other half of the same field. They serve `entries_open` now, and
    the check's own docstring says it reads whether the round is still
    accepting entries -- while `decide` never touched it, so a round they had
    closed still failed with the reason "the round is still open"."""
    mod = _check()
    shut = {**ROUND, "entries_open": False}
    verdict, why = mod.decide(shut, RULES, date(2026, 9, 13))
    assert verdict == "inconclusive", why
    assert "no longer accepting" in why or "closed" in why, why


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_round_with_no_anchor_is_not_a_finding():
    mod = _check()
    assert mod.decide({"scores_after": "2026-09-18"}, RULES,
                      date(2026, 9, 13))[0] == "inconclusive"

"""The judgement behind the Movers leaderboard check, offline.

Fixtures are the real payloads captured 2026-09-13: the `is_house` row from
`/api/v1/universe/movers/tournament`, and both halves of `track_record` from
`/api/v1/universe/movers/potential`. The numbers are theirs, unaltered --
every leaderboard figure equals the backtest half to the decimal, and the
live half is zero.

What each test is really protecting:

* the finding itself, so a rewrite cannot quietly stop making it;
* **that any honest disclosure clears it**, not the one fix this author
  imagined. Three times in one day a vendor fix arrived looking different
  from the defect and our check called it still broken;
* that restated numbers go INCONCLUSIVE rather than guessing which half is
  being shown. Rule 10: an empty measurement is not a defect.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent

HOUSE = {"handle": "NEXUS screen", "picks": 250, "rounds": 12,
         "avg_pct": 29.92, "median_pct": -2.87, "best_pct": 1900.0,
         "doublers": 17, "hit50": 31, "rank": 1, "is_house": True}

LIVE = {"scored": 0, "hit100": 0, "hit50": 0, "hit100_pct": None,
        "hit50_pct": None, "median_pct": None, "mean_pct": None,
        "runs_scored": 0, "first_anchor": None, "last_anchor": None}

BACKTEST = {"scored": 250, "hit100": 17, "hit50": 31, "hit100_pct": 6.8,
            "hit50_pct": 12.4, "median_pct": -2.87, "mean_pct": 29.92,
            "runs_scored": 12, "first_anchor": "2026-06-19",
            "last_anchor": "2026-09-04"}


def _check():
    spec = importlib.util.spec_from_file_location(
        "movers_house_check",
        REPO / "tests" / "rest"
        / "test_movers_leaderboard_separates_backtest_from_live.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_captured_payloads_reproduce_the_finding():
    mod = _check()
    verdict, why = mod.decide(HOUSE, LIVE, BACKTEST)
    assert verdict == "failed", why
    assert "scored=0" in why.replace(" ", "") or "scored=0" in why
    assert "2026-06-19" in why, "the reason has to carry when it was measured"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_shared_quantity_really_does_match_the_backtest():
    """The claim is 'all six, to the decimal'. If that is ever untrue the
    report must not go out saying it, so it is asserted rather than trusted."""
    mod = _check()
    agreed = mod.matches(HOUSE, BACKTEST)
    assert sorted(agreed) == sorted(mod.SAME_QUANTITY), agreed
    # And the live half agrees on nothing that carries a number.
    assert mod.matches(HOUSE, LIVE) == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_any_honest_disclosure_clears_it_not_one_exact_field():
    """Four different shapes a real fix could take. All must pass."""
    mod = _check()
    for fixed in (
        {**HOUSE, "basis": "backtest"},
        {**HOUSE, "handle": "NEXUS screen (backtest)"},
        {**HOUSE, "measurement_kind": "simulated"},
        {**HOUSE, "note": "Hypothetical results over stored closes"},
    ):
        verdict, why = mod.decide(fixed, LIVE, BACKTEST)
        assert verdict == "passed", (fixed, why)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_house_row_that_matches_neither_half_reports_nothing():
    """They restate the numbers; this check stops having an opinion."""
    mod = _check()
    restated = {**HOUSE, "picks": 40, "rounds": 3, "avg_pct": 1.1,
                "median_pct": 0.4, "doublers": 0, "hit50": 2}
    verdict, why = mod.decide(restated, LIVE, BACKTEST)
    assert verdict == "inconclusive", why
    assert "cannot say" in why


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_house_row_showing_the_live_record_passes():
    """The other real fix: score the screen forward and show that instead."""
    mod = _check()
    live = {**BACKTEST, "scored": 250}          # the same record, but LIVE
    verdict, why = mod.decide(HOUSE, live, BACKTEST)
    assert verdict == "passed", why


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_no_house_row_at_all_is_not_a_finding():
    mod = _check()
    assert mod.decide({}, LIVE, BACKTEST)[0] == "inconclusive"

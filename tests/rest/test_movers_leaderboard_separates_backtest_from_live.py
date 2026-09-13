"""The row ranked #1 against live entrants has never been traded forward.

The Movers Tournament ranks human entrants by average 7-day return, and their
own rules say *"the NEXUS screen competes as a row"*. It sits at rank 1 with
250 picks over 12 rounds at avg_pct 29.92.

Their adjacent endpoint, `/api/v1/universe/movers/potential`, publishes that
same screen's record split honestly in two:

    live      scored 0, runs_scored 0, first_anchor null
    backtest  scored 250, runs_scored 12, mean_pct 29.92, median_pct -2.87,
              hit100 17, hit50 31, anchors 2026-06-19 .. 2026-09-04

**Every number in the leaderboard row is the backtest half, to the decimal**
(250/12/29.92/-2.87/17/31), and the live half is zero. So a human who enters a
round is ranked against a record that was measured over stored closes after
the fact, and the leaderboard payload carries nothing that says so: its fields
are handle, picks, rounds, avg_pct, median_pct, best_pct, doublers, hit50,
rank, is_house. `is_house` says who owns the row, not what kind of measurement
it is.

The separation exists -- they built it, on `/potential`, and its disclaimer is
careful. It is dropped precisely where the comparison happens. That is the
same defect as #97, where a payload named no period so an agent ranking two
strategies could not see they were different measurements; here the missing
word is not the window but whether the thing ever ran forward at all.

WHAT MAKES THIS PASS. Any disclosure at all, not the one field this check's
author happened to imagine: a key on the row naming the basis, or the word
backtest/simulated anywhere in its text. A check that demands one exact fix
reports a fixed defect as still broken, which has happened here three times
in one day (see `qa/fold.py`'s own memory on the subject).

WHAT MAKES THIS INCONCLUSIVE. The house row not matching either half. If they
restate the numbers, this check must stop having an opinion rather than guess
which half it is looking at -- an empty measurement is not a defect, rule 10.

SAFE. Two keyless GETs, no key sent and none needed.
"""

from __future__ import annotations

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

TOURNAMENT = "/api/v1/universe/movers/tournament"
POTENTIAL = "/api/v1/universe/movers/potential"

# Leaderboard field -> the track_record field holding the same quantity. Only
# fields BOTH sides publish; best_pct has no counterpart and rank is ours.
SAME_QUANTITY = {
    "picks": "scored",
    "rounds": "runs_scored",
    "avg_pct": "mean_pct",
    "median_pct": "median_pct",
    "doublers": "hit100",
    "hit50": "hit50",
}

# Any of these appearing as a key on the row, or as a word inside one of its
# string values, is the disclosure this check is asking for.
DISCLOSES = ("backtest", "back-test", "simulated", "simulation",
             "hypothetical", "reconstructed")


def discloses_its_basis(row: dict) -> bool:
    """Does the row SAY, in words, that its record is a backtest?

    Values only. Until the deep pass of 2026-09-13 this also returned True for
    a KEY whose name contained "basis" or "measurement", whatever the value --
    so `{"basis": "live"}` beside a row that is one hundred percent the
    backtest half returned `passed`, and would have sent that verification on
    #100. Presence against a contract about a value, which is the 2026-09-07
    `metadata.is_answer` shape.

    A key name says nothing about what the row is; the word does. Every one of
    the four repair shapes this check was written to accept -- `basis:
    "backtest"`, a renamed handle, `measurement_kind: "simulated"`, a note
    about hypothetical results -- carries the word in its VALUE, so nothing
    honest is lost by reading only those.
    """
    for value in (row or {}).values():
        if isinstance(value, str) and any(w in value.lower() for w in DISCLOSES):
            return True
    return False


def matches(row: dict, half: dict) -> list[str]:
    """Which shared quantities the row and one half of the record agree on.

    Compared as floats with a small tolerance, because 29.92 on one side and
    29.920001 on the other is the same number arriving through two encoders,
    and a check that called that a mismatch would go inconclusive forever.
    """
    agreed = []
    for here, there in SAME_QUANTITY.items():
        a, b = (row or {}).get(here), (half or {}).get(there)
        if a is None or b is None:
            continue
        try:
            if abs(float(a) - float(b)) <= max(0.01, abs(float(b)) * 1e-6):
                agreed.append(here)
        except (TypeError, ValueError):
            continue
    return agreed


def decide(row: dict, live: dict, backtest: dict) -> tuple[str, str]:
    """Verdict and reason, pure, so the judgement can be exercised offline."""
    if not row:
        return ("inconclusive",
                "their leaderboard carries no is_house row, so there is no "
                "house record here to be one kind or the other")

    on_backtest = matches(row, backtest)
    on_live = matches(row, live)
    comparable = [f for f in SAME_QUANTITY
                  if row.get(f) is not None
                  and (backtest or {}).get(SAME_QUANTITY[f]) is not None]

    # The figures come FIRST, and the label second. Reading the label first is
    # what let `basis: "live"` pass beside a row that was entirely the backtest
    # half; a label is a claim about the record, so it is checked against the
    # record rather than instead of it. Deep pass 2026-09-13.
    if len(on_live) >= 3 and len(on_live) > len(on_backtest) and (live or {}).get("scored"):
        return ("passed",
                f"the house row matches the live half of their own track "
                f"record on {len(on_live)} shared quantities, which is what a "
                f"leaderboard beside live entrants should show")

    if len(on_backtest) < 3 or len(on_backtest) < len(comparable):
        return ("inconclusive",
                f"the house row agrees with the published backtest record on "
                f"{len(on_backtest)} of {len(comparable)} shared quantities "
                f"and with the live half on {len(on_live)}, so this check "
                f"cannot say which record it is showing. Reporting nothing "
                f"rather than guessing")

    if discloses_its_basis(row):
        return ("passed",
                "the house row is the backtest record and says so in words, "
                "so a reader ranked against it can see what they are being "
                "compared with")

    scored = (live or {}).get("scored")
    first, last = (backtest or {}).get("first_anchor"), (backtest or {}).get("last_anchor")
    return ("failed",
            f"the house row ranked {row.get('rank')} against live entrants "
            f"matches their published BACKTEST record on all "
            f"{len(on_backtest)} shared quantities "
            f"({', '.join(sorted(on_backtest))}), while the live half of the "
            f"same record reports scored={scored}. Its anchors run "
            f"{first} to {last}, measured over stored closes after the fact. "
            f"The leaderboard payload carries no field saying so -- is_house "
            f"names the owner, not the kind of measurement -- so a human "
            f"entering a round is ranked against a record that never traded "
            f"forward, and cannot tell from this endpoint. The distinction "
            f"exists on {POTENTIAL} and is dropped where the comparison is "
            f"made")


def _json(client, path: str) -> dict:
    response = client.get(path)
    if response.status_code != 200:
        raise Inconclusive(
            f"{path} answered HTTP {response.status_code}; a failed read is "
            f"not an empty record")
    try:
        return response.json() or {}
    except ValueError as exc:
        raise Inconclusive(f"{path} did not answer JSON: {exc}")


@qa(component="rest.movers", tier=SafetyTier.SAFE, surface="rest")
def test_the_house_row_says_whether_it_ever_traded_forward(rest_anon):
    """A leaderboard that ranks a backtest beside live entries says which."""
    tournament = _json(rest_anon, TOURNAMENT)
    record = (_json(rest_anon, POTENTIAL).get("track_record") or {})
    live, backtest = record.get("live") or {}, record.get("backtest") or {}
    if not backtest:
        raise Inconclusive(
            f"{POTENTIAL} publishes no backtest half, so there is nothing to "
            f"hold the leaderboard row against")

    house = next((r for r in tournament.get("leaderboard") or []
                  if isinstance(r, dict) and r.get("is_house")), {})
    verdict, reason = decide(house, live, backtest)
    if verdict == "inconclusive":
        raise Inconclusive(reason)

    conclude(Measurement(
        verdict=verdict,
        reason=reason,
        left=[{"leaderboard_house": {k: house.get(k) for k in SAME_QUANTITY}}],
        right=[{"backtest": {v: backtest.get(v) for v in SAME_QUANTITY.values()},
                "live": {v: live.get(v) for v in SAME_QUANTITY.values()}}],
        population={
            "shared_quantities": len(SAME_QUANTITY),
            "agree_with_backtest": matches(house, backtest),
            "agree_with_live": matches(house, live),
            "live_scored": live.get("scored"),
            "backtest_scored": backtest.get("scored"),
            "backtest_first_anchor": backtest.get("first_anchor"),
            "backtest_last_anchor": backtest.get("last_anchor"),
            "house_row_fields": sorted(house),
        },
        sources={"leaderboard": TOURNAMENT, "track_record": POTENTIAL},
    ))

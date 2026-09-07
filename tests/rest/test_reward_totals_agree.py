"""The programme's own reward figures, held against each other.

Three of their surfaces answer the same two questions and give different
answers. On 2026-09-07, with the programme reading `live` at a flat 1000 ET10
per verified bug:

    /api/v1/bounty/stats        awards_recorded 36, awards_recorded_total
                                36000.0, payouts_recorded 2, total_paid 2000.0,
                                valid_reports 40
    /api/v1/bounty/leaderboard  two hunters, both total_earned 0.0, and
                                valid_reports summing to 21
    /api/v1/bounty/my-reports   25 of our rows carrying reward_amount 1000.0

Whether `total_earned` means awarded or paid is not ours to decide, and this
check does not try. Under either reading a programme that has recorded 36
awards cannot show zero earned for every hunter it has, and a leaderboard
listing every hunter it says exists cannot account for half the reports the
same service calls valid.

Deliberately narrow. It asserts only that the platform agrees with itself,
which is the same shape as CYM-award-contradicts-its-own-tier: whichever
number they correct, the check goes green.
"""

from __future__ import annotations

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

STATS = "/api/v1/bounty/stats"
BOARD = "/api/v1/bounty/leaderboard"


def _number(value):
    """A figure, or None. A missing field is not a zero."""
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


@qa(component="rest.support", tier=SafetyTier.SAFE, surface="rest",
    claim="reward-totals-disagree")
def test_the_reward_totals_agree_with_each_other(rest_anon):
    """Two identities, both read off their own published aggregates."""
    stats = rest_anon.get(STATS)
    board = rest_anon.get(BOARD)
    for name, response in (("stats", stats), ("the leaderboard", BOARD and board)):
        if response.status_code != 200:
            conclude(Measurement(
                verdict="inconclusive",
                reason=f"{name} answered HTTP {response.status_code}, so the "
                       f"two cannot be held against each other",
                claim_id="reward-totals-disagree"))
            return

    s = stats.json()
    entries = board.json().get("entries") or []
    if not entries:
        conclude(Measurement(
            verdict="inconclusive",
            reason="the leaderboard lists no hunters, so there is nothing to "
                   "reconcile the aggregate against",
            population={"stats": {k: s.get(k) for k in
                                  ("awards_recorded", "valid_reports")}},
            claim_id="reward-totals-disagree"))
        return

    awarded = _number(s.get("awards_recorded_total"))
    paid = _number(s.get("total_paid"))
    valid = _number(s.get("valid_reports"))

    earned = [(_number(e.get("total_earned")), e.get("hunter_name")) for e in entries]
    board_valid = sum(_number(e.get("valid_reports")) or 0 for e in entries)

    problems = []

    # Whichever of the two `total_earned` means, a programme that has recorded
    # money against reports cannot show zero for every hunter it lists.
    recorded = max(v for v in (awarded, paid, 0) if v is not None)
    if recorded > 0 and all(v == 0 for v, _ in earned if v is not None):
        problems.append(
            f"stats records {awarded} awarded and {paid} paid, and every one "
            f"of the {len(entries)} hunter(s) on the leaderboard shows "
            f"total_earned 0.0"
        )

    # The leaderboard claims to list every hunter -- active_hunters agrees with
    # its length -- so between them they should account for the same reports.
    hunters = _number(s.get("active_hunters"))
    if (valid is not None and hunters == len(entries) and board_valid != valid):
        problems.append(
            f"the leaderboard lists all {len(entries)} hunter(s) and accounts "
            f"for {board_valid:.0f} valid report(s), while stats calls "
            f"{valid:.0f} valid"
        )

    conclude(Measurement(
        verdict="failed" if problems else "passed",
        reason=("; ".join(problems) if problems else
                f"the aggregate and the leaderboard agree: {board_valid:.0f} "
                f"valid report(s) either way, and the earned column is "
                f"consistent with {awarded} awarded"),
        left={"leaderboard": [{"hunter": n, "earned": v} for v, n in earned],
              "board_valid_reports": board_valid},
        right={"awards_recorded": s.get("awards_recorded"),
               "awards_recorded_total": awarded,
               "payouts_recorded": s.get("payouts_recorded"),
               "total_paid": paid,
               "valid_reports": valid},
        sources={"stats": STATS, "leaderboard": BOARD},
        population={"hunters_listed": len(entries),
                    "active_hunters": s.get("active_hunters")},
        claim_id="reward-totals-disagree"))

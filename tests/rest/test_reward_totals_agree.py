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

def money_problems(stats: dict, entries: list, definition: str | None) -> list:
    """Both money invariants. They are not alternatives.

    When they answered #73 by publishing `total_earned_definition` instead of
    moving a figure, this check was repaired to hold each hunter's
    `total_earned` against the column that definition names -- and the repair
    put that comparison in an `else`, so the ORIGINAL invariant ran only while
    no definition was published. The comment called the result "strictly
    stronger"; on the money axis it was strictly weaker, and the cross-surface
    contradiction the module docstring is about stopped being measured.

    Live proof, run-20260907T135100Z: stats total_paid 2000.0 with
    payouts_recorded 2, all four hunters at total_earned 0.0 AND total_paid
    0.0, verdict passed, reason "the aggregate and the leaderboard agree". A
    pass verification for that reached #73.

    So: the cross-surface check always, and the column check as well when they
    have said which column they mean. A within-row comparison cannot see two
    surfaces disagreeing, and a cross-surface comparison cannot see a column
    disagreeing with its own published definition.
    """
    problems: list[str] = []
    awarded = _number(stats.get("awards_recorded_total"))
    paid = _number(stats.get("total_paid"))
    column = {"paid": "total_paid", "awarded": "total_awarded"}.get(definition)

    # Whatever `total_earned` means, a programme that has recorded money
    # against reports cannot show zero for every hunter it lists.
    earned = [_number(e.get("total_earned")) for e in entries]
    recorded = max([v for v in (awarded, paid) if v is not None] or [0])
    # `all(... if v is not None)` over an all-None column is vacuously True, so
    # a leaderboard that stopped publishing total_earned would have produced
    # "every one of the 4 hunter(s) shows total_earned 0.0" about hunters that
    # show none -- sent to #73, and contradicting _number's own docstring, "a
    # missing field is not a zero". The rule-8 gate below existed for `column`
    # and never for this. Audit, 2026-09-07.
    present = [v for v in earned if v is not None]
    if entries and recorded > 0 and present and all(v == 0 for v in present):
        problems.append(
            f"stats records {awarded} awarded and {paid} paid, and every one "
            f"of the {len(entries)} hunter(s) on the leaderboard shows "
            f"total_earned 0.0"
            + (f", which stats defines as {definition!r}" if column else
               ", with no total_earned_definition to say which of the two the "
               "column means")
        )

    if column:
        for entry in entries:
            mine, theirs = _number(entry.get("total_earned")), _number(entry.get(column))
            if mine is None or theirs is None:
                continue  # handled by the caller: rule 8, a missing column is not a zero
            if mine != theirs:
                problems.append(
                    f"{entry.get('hunter_name')} shows total_earned {mine} "
                    f"while {column} is {theirs}, and stats defines earned as "
                    f"{definition!r}"
                )
    return problems



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

    # Repaired 2026-09-07, after they answered #73 by publishing meaning rather
    # than by moving a figure -- which is the better fix and the one this check
    # did not anticipate. It said "whichever number they correct, the check
    # goes green"; they corrected neither, and instead added
    # `total_earned_definition`, a per-hunter split into total_awarded and
    # total_paid, and `valid_reports_attributed`/`_unattributed`. Both
    # disagreements turned out to be ambiguity in the documentation, not
    # contradiction in the data.
    #
    # So the check now holds the column against the definition the platform
    # publishes for it. That is strictly stronger than the old test: it fails
    # if the two ever stop agreeing, where before it could only complain that
    # a number was zero.
    definition = s.get("total_earned_definition")
    column = {"paid": "total_paid", "awarded": "total_awarded"}.get(definition)

    earned = [(_number(e.get("total_earned")), e.get("hunter_name")) for e in entries]
    board_valid = sum(_number(e.get("valid_reports")) or 0 for e in entries)
    # A programme that says how many of its valid reports are attributed to a
    # hunter is telling us what the leaderboard is allowed to add up to.
    attributed = _number(s.get("valid_reports_attributed"))
    expected_valid = attributed if attributed is not None else valid

    # Rule 8 one layer down, before the comparison: a column a row does not
    # carry is not a column that reads zero.
    if column:
        for entry in entries:
            if _number(entry.get(column)) is None:
                conclude(Measurement(
                    verdict="inconclusive",
                    reason=f"total_earned_definition says {definition!r} but "
                           f"{entry.get('hunter_name')!r} carries no "
                           f"{column}, so the two cannot be held together",
                    sources={"stats": STATS, "leaderboard": BOARD},
                    claim_id="reward-totals-disagree"))
                return

    problems = money_problems(s, entries, definition)

    # The leaderboard claims to list every hunter -- active_hunters agrees with
    # its length -- so between them they should account for the same reports.
    hunters = _number(s.get("active_hunters"))
    if (expected_valid is not None and hunters == len(entries)
            and board_valid != expected_valid):
        named = ("valid_reports_attributed" if attributed is not None
                 else "valid_reports")
        problems.append(
            f"the leaderboard lists all {len(entries)} hunter(s) and accounts "
            f"for {board_valid:.0f} valid report(s), while stats calls "
            f"{expected_valid:.0f} {named}"
        )

    # The other half of the same repair: with no hunter publishing
    # total_earned there is nothing to reconcile the aggregate against, and the
    # pass sentence below would claim "every hunter's total_earned matches the
    # column it is defined as" over an empty set. Dropping the field must not
    # be a way to pass -- the same reason `unmeasurable` exists in the sibling
    # award check.
    if not problems and not [e for e in entries
                             if _number(e.get("total_earned")) is not None]:
        conclude(Measurement(
            verdict="inconclusive",
            reason=(f"none of the {len(entries)} hunter(s) on the leaderboard "
                    f"publishes total_earned, so the aggregate stats reports "
                    f"cannot be reconciled against it"),
            sources={"stats": STATS, "leaderboard": BOARD},
            population={"hunters_listed": len(entries),
                        "total_earned_published": 0},
            claim_id="reward-totals-disagree"))
        return

    # The pass sentence used to assert both reconciliations unconditionally,
    # and either can be skipped without being measured: with
    # total_earned_definition absent the per-hunter loop never runs, and the
    # sentence still read "matches the None it is defined as"; with
    # active_hunters != len(entries) the valid-report comparison is skipped and
    # the sentence still printed the leaderboard's own figure on both sides of
    # a comparison nobody made. That is the shape repaired as T01 and quoted in
    # test_pipeline_verify.py, and a pass reason on this claim reaches the
    # vendor. Deep pass, 2026-09-08, 3/3.
    held = []
    if hunters == len(entries):
        held.append(f"the aggregate and the leaderboard agree on "
                    f"{board_valid:.0f} valid report(s)")
    else:
        held.append(f"the valid-report totals were NOT compared: stats count "
                    f"{hunters} active hunter(s) against {len(entries)} "
                    f"leaderboard row(s)")
    if column:
        held.append(f"every hunter's total_earned matches the {column} it is "
                    f"defined as")
    else:
        held.append("total_earned was NOT compared: the leaderboard publishes "
                    "no total_earned_definition to compare it against")

    conclude(Measurement(
        verdict="failed" if problems else "passed",
        reason=("; ".join(problems) if problems else "; ".join(held)),
        left={"leaderboard": [{"hunter": e.get("hunter_name"),
                               "earned": _number(e.get("total_earned")),
                               "awarded": _number(e.get("total_awarded")),
                               "paid": _number(e.get("total_paid"))}
                              for e in entries],
              "board_valid_reports": board_valid},
        right={"awards_recorded": s.get("awards_recorded"),
               "awards_recorded_total": awarded,
               "payouts_recorded": s.get("payouts_recorded"),
               "total_paid": paid,
               "valid_reports": valid,
               "valid_reports_attributed": attributed,
               "total_earned_definition": definition},
        sources={"stats": STATS, "leaderboard": BOARD},
        population={"hunters_listed": len(entries),
                    "active_hunters": s.get("active_hunters")},
        claim_id="reward-totals-disagree"))

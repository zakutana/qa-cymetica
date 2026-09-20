"""The account summary must say what its counters do and do not cover.

Measured 2026-09-08, either side of one $1 paper trade:

    before   total_predictions 0     total_volume 0
    after    total_predictions 142   total_volume 3582.146846

That looked like a summary reporting zeros over an account holding 38
event-card positions, and it was filed as #83: an agent reading its own
summary would conclude it had never traded, and no other surface would
contradict it.

**The filing was wrong, and this file is the repair.** Cymetica shipped a
`scope` block between 13:24Z and 15:07Z that same day. It says those counters
cover "on-chain WTA prediction-market bets placed from this user's swarm
wallet" — of which this account has placed none, so 0 was true — and it names
"event-card bull/bear positions" first among what they do not cover, pointing
at `/api/v1/event-cards/positions` by URL. The body carries an `event_cards`
block with the counts and that URL. The summary does not claim we never
traded; it says where the other history lives.

We sent them a `fail` verification at 15:16Z, nine minutes after their fix was
already captured on this disk, and edited this check ninety seconds after that
capture without reading it. #83 is withdrawn and a retraction was owed and
sent. It is the same shape as #81, where an endpoint's zero was truthful and
what was missing was a statement of scope — they shipped one there too, and
that is twice this account has read a scope statement as a contradiction.

So what is checked now is the thing that is actually true and worth keeping
true: **a summary whose counters exclude a population it holds must say so,
and say where that population can be read.** That is their fix, pinned, so it
cannot regress quietly back into the state that fooled us.
"""

from __future__ import annotations

import json

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

SUMMARY = "/api/v1/portfolio/summary"
POSITIONS = "/api/v1/event-cards/positions"
# A sentence about the counters that says event cards are NOT in them is not
# counting them, whatever words it shares with one that does.
NEGATIONS = ("not ", "exclud", "except", "without",
             # "summarized elsewhere" leaves the population out as surely as
             # "not counted" -- it is what made V09 of 2026-09-13 read a vague
             # mention as counting (V10, deep pass of 2026-09-19).
             "elsewhere", "separately")


def accounts_for(scope) -> str | None:
    """How the summary's scope accounts for the event-card positions held.

    'counted' when counters_cover says the counters include them, 'named'
    when counters_do_not_cover names them, None when it does neither. The
    comment in the check has always allowed both ("either by counting it or
    by naming it as excluded"); until the deep pass of 2026-09-11 only naming
    passed, so folding event cards into the counters -- a fix -- would have
    been filed as unaccounted positions, #83's shape on this same endpoint.

    None for a sentence in `counters_cover` that says they are NOT counted:
    that is not counting them, and V05 of 2026-09-11 pinned it 3/3. Whether
    such a sentence nonetheless STATES the exclusion is a different question
    and `states_exclusion` below answers it -- kept apart so that pin holds.
    """
    scope = scope if isinstance(scope, dict) else {}
    covers = str(scope.get("counters_cover") or "").lower()
    excluded = scope.get("counters_do_not_cover")
    excluded = excluded if isinstance(excluded, list) else []
    words = " ".join(str(item) for item in excluded).lower()

    def mentions(text: str) -> bool:
        return any(k in text for k in ("event-card", "event card", "event_card"))

    if mentions(covers) and not any(n in covers for n in NEGATIONS):
        return "counted"
    if mentions(words):
        return "named"
    return None


def states_exclusion(scope) -> bool:
    """Does the scope say ANYWHERE that this population is left out?

    Separate from `accounts_for`, which answers the narrower question of how
    the population is accounted for and whose three returns are pinned by
    `test_the_summary_may_account_for_positions_by_counting_them` (V05, deep
    pass of 2026-09-11, 3/3). That pin is right: a sentence saying event cards
    are NOT counted is not counting them, so `accounts_for` must go on
    answering None for it.

    What was missing is that such a sentence is still the exclusion being
    STATED, and the contract at the top of this file is "must say so, and say
    where that population can be read" -- which does not say in which field. A
    scope reading `counters_cover: "...event-card bull/bear positions are not
    counted here, see /api/v1/event-cards/positions"` with an empty
    `counters_do_not_cover` does exactly what is asked, and the check reported
    it as a scope that "neither counts them nor names them". That is #83's
    shape for the third time on this endpoint, and #83 cost a retraction.
    Three readers, 3/3, deep pass of 2026-09-13.
    """
    scope = scope if isinstance(scope, dict) else {}
    covers = str(scope.get("counters_cover") or "").lower()
    return (any(k in covers for k in ("event-card", "event card", "event_card"))
            and any(n in covers for n in NEGATIONS))


def scope_problems(scope: dict, body: dict, held: int) -> list[str]:
    """What the scope still fails to say about `held` event-card positions.

    Out of the check so it can be driven. The pointer -- WHERE the population
    is read -- is owed for a population the counters leave OUT. It was owed
    whenever the scope mentioned them at all, so a scope that COUNTS them, the
    fix the comment below allows, was failed for not saying where else to read
    them (V10, deep pass of 2026-09-19, 3/3). A vague mention ("summarized
    elsewhere") is not counting, and still owes it (V09 of 2026-09-13).
    """
    covers = str((scope or {}).get("counters_cover") or "")
    how = accounts_for(scope)
    stated = states_exclusion(scope)
    named = how is not None or stated

    # WHERE IT IS READ, wherever the body says it. This looked only inside the
    # joined prose of `counters_do_not_cover`, and their captured fix carries
    # the pointer twice: in that parenthetical AND in the body's own
    # `event_cards.rows` field. Tidying the parenthetical while keeping the
    # machine-readable field would have filed "the reader is not told which
    # endpoint carries it" against a body that tells the reader exactly that --
    # the #83 shape, on this same endpoint, which was withdrawn and cost a
    # retraction. Found by a check-auditor 2026-09-10, 3/3 on triage.
    everywhere = json.dumps(body, ensure_ascii=False).lower()
    points_at = POSITIONS in everywhere or "event-cards/positions" in everywhere

    problems = []
    if not covers:
        problems.append("counters_cover is empty, so what the counters count "
                        "is still unsaid")
    if not named:
        problems.append(f"{held} event-card position(s) are held and the "
                        f"scope neither counts them nor says anywhere that it "
                        f"leaves them out")
    elif how != "counted" and not points_at:
        problems.append(
            f"the scope mentions the {held} event-card position(s) "
            f"({how or 'left out'}) but the reader is not told which endpoint "
            f"carries them")
    return problems


@qa(component="rest.account", tier=SafetyTier.SAFE, surface="rest")
def test_the_summary_says_which_populations_its_counters_leave_out(rest_trusted):
    """Zero counters are honest when the reader is told what they count."""
    summary = rest_trusted.get(SUMMARY)
    positions = rest_trusted.get(POSITIONS)
    if summary.status_code != 200 or positions.status_code != 200:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"summary answered HTTP {summary.status_code} and positions "
                   f"HTTP {positions.status_code}; a failed read is not an "
                   f"empty account",
            sources={"summary": SUMMARY, "positions": POSITIONS}))
        return

    body = summary.json() or {}
    held = (positions.json() or {}).get("positions") or []
    if not held:
        raise Inconclusive(
            "this account holds no event-card position, so whether the "
            "summary accounts for one cannot be measured here")

    scope = body.get("scope")
    if not isinstance(scope, dict):
        conclude(Measurement(
            verdict="failed",
            reason=(f"the summary publishes no scope block while listing "
                    f"counters beside {len(held)} event-card position(s) it "
                    f"does not count: a reader has no way to tell a true zero "
                    f"from a broken one"),
            left=sorted(body), right="scope",
            population={"positions": len(held)},
            sources={"summary": SUMMARY, "positions": POSITIONS}))
        return

    covers = str(scope.get("counters_cover") or "")
    excluded = scope.get("counters_do_not_cover")
    excluded = excluded if isinstance(excluded, list) else []
    words = " ".join(str(item) for item in excluded).lower()

    # The population this account actually holds is event-card positions, so
    # that is the one the scope has to account for -- either by counting it or
    # by naming it as excluded and saying where it is read. The judgement is
    # scope_problems() above, so a meta test can drive it (V10).
    problems = scope_problems(scope, body, len(held))

    # WHICH of the two ways, because the pass reason was written for one of
    # them and printed on both. `accounts_for` returns "counted" when the
    # scope says the counters include the positions and "named" when it lists
    # them as excluded -- and the sentence said "name the N positions they do
    # NOT, with the endpoint that carries them" either way, which is the
    # opposite of what the counted branch read and mentions an endpoint that
    # branch never looked for. Found by two readers on 2026-09-20.
    how = accounts_for(scope)
    conclude(Measurement(
        verdict="failed" if problems else "passed",
        reason=("; ".join(problems) if problems else
                f"the counters state what they cover and say they INCLUDE "
                f"the {len(held)} event-card position(s) this account holds"
                if how == "counted" else
                f"the counters state what they cover, and name the "
                f"{len(held)} event-card position(s) they do not, with the "
                f"endpoint that carries them"),
        left=excluded, right=POSITIONS,
        population={"positions": len(held),
                    "counters_do_not_cover": len(excluded)},
        sources={"summary": SUMMARY, "positions": POSITIONS}))

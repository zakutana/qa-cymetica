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
    # by naming it as excluded and saying where it is read.
    named = "event-card" in words or "event card" in words

    # WHERE IT IS READ, wherever the body says it. This looked only inside the
    # joined prose of `counters_do_not_cover`, and their captured fix carries
    # the pointer twice: in that parenthetical AND in the body's own
    # `event_cards.rows` field. Tidying the parenthetical while keeping the
    # machine-readable field would have filed "the reader is not told which
    # endpoint carries it" against a body that tells the reader exactly that --
    # the #83 shape, on this same endpoint, which was withdrawn and cost a
    # retraction. Found by a check-auditor 2026-09-10, 3/3 on triage.
    #
    # Their whole answer is the subject, because "does the body say where to
    # read it" is a question about the body, not about one field of it.
    everywhere = json.dumps(body, ensure_ascii=False).lower()
    points_at = POSITIONS in everywhere or "event-cards/positions" in everywhere

    problems = []
    if not covers:
        problems.append("counters_cover is empty, so what the counters count "
                        "is still unsaid")
    if not named:
        problems.append(f"{len(held)} event-card position(s) are held and "
                        f"nothing in counters_do_not_cover names them")
    elif not points_at:
        problems.append("the excluded population is named but the reader is "
                        "not told which endpoint carries it")

    conclude(Measurement(
        verdict="failed" if problems else "passed",
        reason=("; ".join(problems) if problems else
                f"the counters state what they cover, and name the "
                f"{len(held)} event-card position(s) they do not, with the "
                f"endpoint that carries them"),
        left=excluded, right=POSITIONS,
        population={"positions": len(held),
                    "counters_do_not_cover": len(excluded)},
        sources={"summary": SUMMARY, "positions": POSITIONS}))

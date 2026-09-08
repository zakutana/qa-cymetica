"""A pass that stopped in the middle leaves a red test, not a quiet file.

`audits/deep-pass-progress.json` is where the deep pass writes what it claimed,
what survived triage and what it fixed, so that being compacted halfway through
itself cannot erase the list. The operator's question when that file was added,
on 2026-09-08, is the reason this exists:

    "plus na disk jeste neco ukladas, coz se bojim ze treba zapomenes nacist"

They are right, and the evidence is from the same morning: DEEP-PASS.md existed
and was full of work, and a session could not read it because nothing pointed
at it. A file whose only guard is somebody remembering to open it is the
weakest thing in this repository.

So this reads it instead. A gap that three agents called real and nobody fixed
is exactly the state that cannot be allowed to sit quietly: the suite goes
green, the report says the pass finished, and the finding is gone.

The check is deliberately narrow. It does not care how many gaps a pass found,
how it voted, or how long it took. It asks one question: **did the pass leave
anything it had confirmed as real and had not fixed?**
"""

from __future__ import annotations

import json
from pathlib import Path

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

REPO = Path(__file__).resolve().parent.parent.parent
PROGRESS = REPO / "audits" / "deep-pass-progress.json"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_no_confirmed_finding_was_left_unfixed_by_a_deep_pass():
    """Every gap the pass confirmed is either fixed or named for the operator."""
    if not PROGRESS.exists():
        conclude(Measurement(
            verdict="inconclusive",
            reason="no deep pass has written a progress file yet, so there is "
                   "nothing to have been left behind",
            sources={"progress": "audits/deep-pass-progress.json"}))
        return

    try:
        progress = json.loads(PROGRESS.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        conclude(Measurement(
            verdict="failed",
            reason=f"the deep pass's progress file cannot be read "
                   f"({type(exc).__name__}), so whether it finished is unknown "
                   f"-- and unknown is the state this file exists to prevent",
            sources={"progress": "audits/deep-pass-progress.json"}))
        return

    gaps = progress.get("gaps") or []
    # `handled` rather than `fixed`: a gap the pass deliberately left for the
    # operator is finished business here, as long as it said so. What is
    # forbidden is confirmed-real, unfixed, and unmentioned.
    owed = [g for g in gaps
            if g.get("verdict") == "real" and not g.get("fixed")
            and not g.get("deferred_to_operator")]
    undecided = [g for g in gaps if g.get("verdict") is None]

    conclude(Measurement(
        verdict="failed" if owed else "passed",
        reason=(f"the last deep pass ({progress.get('run')}) settled all "
                f"{len(gaps)} gap(s) it claimed"
                + (f", {len(undecided)} of them still awaiting a vote"
                   if undecided else "")
                if not owed else
                f"the last deep pass ({progress.get('run')}) confirmed "
                f"{len(owed)} gap(s) as real, fixed none of them and named "
                f"none for the operator: "
                f"{', '.join(str(g.get('id') or g.get('nodeid')) for g in owed[:6])}"),
        left=[g.get("id") for g in owed], right=[],
        population={"gaps": len(gaps), "confirmed_unfixed": len(owed),
                    "still_unvoted": len(undecided)},
        sources={"progress": "audits/deep-pass-progress.json"}))

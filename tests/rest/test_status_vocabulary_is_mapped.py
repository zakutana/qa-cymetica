"""Every status they can send is a word we recognise.

Until 2026-09-07 our reading of their statuses was guesswork: `{fixed,
resolved, completed, closed}` meant a fix claim and everything else meant
RAISED. Two of those are ticket statuses that this surface cannot return and
one was invented, so of the values the API actually sends, `invalid` -- them
telling us the report is worthless, 45 times -- was recorded exactly as far as
hearing nothing would have been.

The guessing is over, because they now publish the enum: my-reports carries a
`status_vocabulary` block. So this check holds our sets against theirs and
fails when the two drift.

**What it does NOT check is the axis.** Mapping the engagement statuses onto
REPLIED was written and then reverted the same day: the FILING axis is a
replay of the journal, so reading a status differently rewrites the history of
every row that ever carried it, and write_ledger refused a ledger whose
transitions were not an extension of the ones on disk. The fold still moves to
FIX_CLAIMED or RAISED and nothing else. `_REPLIED_STATUSES` therefore names
what we UNDERSTAND, not what we act on, and that is the thing worth holding
against their enum -- a status nobody here has ever heard of is a status whose
arrival we would misread the day somebody does freeze the history and use it.
The obligation that carries the value in the meantime is `disputed`, which
reads a report's current status and touches no transition.

Deliberately about US. It fails when our fold falls behind their vocabulary,
not when their vocabulary changes -- a new status is their prerogative and our
problem. The only thing it asks of them is that the block keeps existing, and
that is inconclusive rather than failed: a vocabulary we cannot read is not a
vocabulary we disagree with.
"""

from __future__ import annotations

import os

from qa.fold import (_FIX_CLAIMED_STATUSES, _RAISED_STATUSES,
                     _REJECTED_STATUSES, _REPLIED_STATUSES)
from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

MY_REPORTS = "/api/v1/bounty/my-reports"


@qa(component="rest.support", tier=SafetyTier.SAFE, surface="rest",
    claim="status-vocabulary-unmapped")
def test_every_status_they_publish_has_a_meaning_on_our_axis(rest_trusted):
    """Their published report_status enum, against what qa/fold.py knows."""
    wallet = os.environ.get("QA_WALLET_ADDRESS", "")
    if not wallet:
        conclude(Measurement(
            verdict="inconclusive",
            reason="QA_WALLET_ADDRESS is not set, so my-reports cannot be read",
            sources={"my-reports": MY_REPORTS},
            claim_id="status-vocabulary-unmapped"))
        return

    response = rest_trusted.get(MY_REPORTS, params={"wallet_address": wallet})
    if response.status_code != 200:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"my-reports answered HTTP {response.status_code}, so the "
                   f"vocabulary could not be read",
            sources={"my-reports": MY_REPORTS},
            claim_id="status-vocabulary-unmapped"))
        return

    vocabulary = (response.json() or {}).get("status_vocabulary") or {}
    published = vocabulary.get("report_status")
    if not published:
        # Rule 8: a vocabulary we could not read is not an empty vocabulary.
        conclude(Measurement(
            verdict="inconclusive",
            reason="my-reports carries no status_vocabulary.report_status, so "
                   "there is nothing to hold our mapping against",
            population={"status_vocabulary": sorted(vocabulary)},
            sources={"my-reports": MY_REPORTS},
            claim_id="status-vocabulary-unmapped"))
        return

    # Every status any of our three sets names. Not "what moves the axis":
    # see the module docstring for why those are different things.
    mapped = (_FIX_CLAIMED_STATUSES | _REPLIED_STATUSES | _RAISED_STATUSES)
    unmapped = sorted(set(published) - mapped)
    # A status we map that they do not publish is dead weight rather than a
    # defect -- it costs a line in never_fired.py and nothing else -- so it is
    # reported beside the failure, not as one.
    unknown = sorted(mapped - set(published))

    conclude(Measurement(
        verdict="failed" if unmapped else "passed",
        reason=(f"{len(unmapped)} status(es) they can return have no meaning "
                f"on our filing axis and would read as 'filed, no answer': "
                f"{', '.join(unmapped)}"
                if unmapped else
                f"all {len(published)} published report statuses are mapped"),
        left=sorted(mapped), right=sorted(published),
        population={"unmapped": unmapped,
                    "mapped_but_not_published": unknown,
                    "rejected": sorted(_REJECTED_STATUSES)},
        sources={"my-reports": MY_REPORTS},
        claim_id="status-vocabulary-unmapped"))

"""The Agent Returns Board, ranked by what its own document promises.

`llms.txt` is the agent-facing index, and it describes one endpoint in one
line:

    GET /api/v1/agent-board/search: Search playbooks
    (ranked by verified return x replications)

That sentence is a contract with a reader who cannot ask a follow-up. An agent
that trusts it reads the first row as the playbook with the best VERIFIED
record -- return that somebody proved, multiplied by the number of agents who
reproduced it -- and copies it. It is the only ordering statement the board
has anywhere.

Measured 2026-09-20 over the three playbooks the board serves:

    rank 0.36374  created 2026-09-19  replications 0/0  evidence_verified false
    rank 0.14878  created 2026-09-13  replications 0/0  evidence_verified false
    rank 0.07984  created 2026-09-05  replications 0/0  evidence_verified false

Three things are true at once, and together they say the sentence is not
describing this list:

  * every row's documented key is nil -- no confirmed replication, no verified
    evidence, no `pnl_usdc` -- so "verified return x replications" is zero for
    all of them and orders nothing;
  * `rank` is the same value for a row whatever `q` is, to five decimals, so
    it is not a relevance score for the search either;
  * the order is exactly newest-first, and the value drifts DOWNWARD by about
    a millionth between two calls seconds apart, which is a time decay.

So the board is ranked by age, and its readers are told it is ranked by proof.

WHAT THIS CHECK ASSERTS. Only the three facts above, each read live, and it
opens a defect only when ALL THREE hold at once:

  1. no row carries a confirmed replication or verified evidence;
  2. two different queries return the same `rank` for the same row;
  3. the ranking is exactly the recency order.

Any one of them failing is enough to stay quiet. A board where somebody has
replicated a playbook may legitimately rank it above a newer one; a `rank`
that moves with `q` is a relevance score and the sentence is then about
something else; an order that is not recency is not the defect measured here.
That is deliberately harder to trip than the sentence alone -- what is being
claimed is that the document cannot be true of this list, not that the
ordering is bad.

It does not say which end should change. Publishing what `rank` actually is
would close it; so would ranking by the key they published.

INCONCLUSIVE, not a defect, when the board has fewer than two playbooks: one
row has no order, and a rule over one row is not a measurement (rule 10).
Likewise when the two queries share no row by id: condition 2 was then read
over nothing, in either direction.

SAFE. Three GETs and no key: the board is public, which is the point of it.
"""

from __future__ import annotations

import re

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

SEARCH = "/api/v1/agent-board/search"
LLMS = "/llms.txt"
# Two queries that both match the whole board, so the rows can be compared
# row by row rather than set against set.
QUERIES = ("", "agent")
# `rank` drifts by about a millionth between calls seconds apart, so equality
# is read at five decimals -- far finer than the gaps between the rows
# (0.36, 0.15, 0.08) and far coarser than the decay.
PLACES = 5


# The sentence that closes this: a description which itself says the order is
# recency while nothing is proven. Read on the SAME line as the endpoint, so a
# recency note about some other feed is not mistaken for a disclosure about
# this one. Added 2026-09-21 after Cymetica fixed #111 exactly this way --
# they published what `rank` is, which the report named as one of the two
# closes, and the check would otherwise have gone on failing a fixed report.
#
# A STATEMENT that the order is recency, not the word. Any recency word beside
# any unproven word counted, so "ranked by verified return x replications;
# unverified rows are badged; recency decay applied" -- the sentence filed
# against, plus a decay and a badge -- read as disclosed and would have sent
# #111 a pass (B10, deep pass of 2026-09-21). "Decayed by recency" is a factor
# of the score; "ordered by recency" and "newest first" are the order.
ORDERED_BY_AGE = re.compile(
    r"\b(?:newest|most[- ]recent|latest)[- ]first\b"
    r"|\b(?:order|ordered|orders|sorted|sorts|ranked|ranks)\s+(?:is\s+)?"
    r"(?:simply\s+)?(?:by\s+)?(?:recency|age|creation (?:date|time))\b")
UNPROVEN = ("no row has verified", "nothing is verified", "unverified",
            "no verified", "without verified")


def discloses_recency(claim_lines: list[str]) -> bool:
    """Does their own description admit the ordering this check measures?"""
    for line in claim_lines:
        low = line.lower()
        if ORDERED_BY_AGE.search(low) and any(
                word in low for word in UNPROVEN):
            return True
    return False


def _rows(response) -> list[dict]:
    body = response.json()
    rows = body.get("data")
    return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []


def _nil_key(row: dict) -> bool:
    """True when the documented ranking key is nothing for this row."""
    repl = row.get("replications")
    confirmed = repl.get("confirmed") if isinstance(repl, dict) else None
    pnl = row.get("pnl_usdc")
    return (not confirmed
            and not row.get("evidence_verified")
            and (pnl is None or pnl == 0))


@qa(component="rest.agents", tier=SafetyTier.SAFE, surface="rest")
def test_the_board_is_ranked_by_the_key_its_own_document_publishes(rest_anon):
    """One sentence in llms.txt, held against the list it describes."""
    document = rest_anon.get(LLMS)
    broad = rest_anon.get(SEARCH, params={"q": QUERIES[0]})
    narrow = rest_anon.get(SEARCH, params={"q": QUERIES[1]})

    for name, response in (("llms.txt", document), ("the board", broad),
                           ("the board again", narrow)):
        if response.status_code != 200:
            conclude(Measurement(
                verdict="inconclusive",
                reason=f"{name} answered HTTP {response.status_code}, and a "
                       f"failed read is not an empty one",
                sources={"document": LLMS, "board": SEARCH}))
            return

    # The claim, read off their document rather than quoted from memory. If
    # they reword it, this check stops asserting instead of asserting a
    # sentence that is no longer published.
    claim = [line for line in document.text.splitlines()
             if "agent-board/search" in line]
    if not any("replication" in line.lower() for line in claim):
        conclude(Measurement(
            verdict="inconclusive",
            reason="llms.txt no longer describes how agent-board/search is "
                   "ranked, so there is no published ordering to hold it to",
            sources={"document": LLMS, "board": SEARCH}))
        return

    # Asked before the three conditions, because all three can be true of a
    # board whose document already says so -- which is what a reader needs and
    # is therefore not the defect. The three conditions are a contradiction
    # only against a description that claims proof orders the list.
    if discloses_recency(claim):
        conclude(Measurement(
            verdict="passed",
            reason=("their own description of agent-board/search says the "
                    "order is recency while no row carries verified evidence "
                    "or a confirmed replication, so the list and the sentence "
                    "describing it agree and a reader is told what the top of "
                    "it means"),
            left={"published": [line.strip() for line in claim]},
            sources={"document": LLMS, "board": SEARCH}))
        return

    rows = _rows(broad)
    if len(rows) < 2:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"the board serves {len(rows)} playbook(s); one row has no "
                   f"order, so nothing about the ranking can be measured",
            sources={"document": LLMS, "board": SEARCH},
            population={"playbooks": len(rows)}))
        return

    ranked = sorted(rows, key=lambda r: -(r.get("rank") or 0))
    proved = [r for r in rows if not _nil_key(r)]
    # Same row, other query: is `rank` a property of the row or of the search?
    # Only rows that carry an id can be the same row. Keyed on r.get("id"),
    # every id-less row became None and was compared with the LAST id-less row
    # of the other query (A14, deep pass of 2026-09-21).
    other = {r["id"]: r.get("rank") for r in _rows(narrow)
             if r.get("id") is not None}
    shared = [r for r in rows if r.get("id") is not None and r["id"] in other]
    fixed = [r for r in shared
             if round(float(r.get("rank") or 0), PLACES)
             == round(float(other[r.get("id")] or 0), PLACES)]
    newest = sorted(rows, key=lambda r: str(r.get("created_at") or ""), reverse=True)
    by_age = [r.get("id") for r in newest] == [r.get("id") for r in ranked]

    facts = {"playbooks": len(rows), "with_a_verified_key": len(proved),
             "compared_across_queries": len(shared),
             "rank_unchanged_by_the_query": len(fixed),
             "ranking_is_recency_order": by_age}

    if proved:
        conclude(Measurement(
            verdict="passed",
            reason=(f"{len(proved)} of {len(rows)} playbook(s) carry a "
                    f"confirmed replication or verified evidence, so the "
                    f"published key can order the board and this check has "
                    f"nothing to say about how it did"),
            sources={"document": LLMS, "board": SEARCH}, population=facts))
        return

    # No row in both answers is no comparison, and "moves with the query on 0
    # of 0 row(s)" was a relevance claim over nothing (rule 10; A14, deep
    # pass of 2026-09-21).
    if not shared:
        conclude(Measurement(
            verdict="inconclusive",
            reason=(f"no playbook carries a verified return or a replication, "
                    f"but the {len(rows)} row(s) under q={QUERIES[0]!r} and "
                    f"the {len(_rows(narrow))} under q={QUERIES[1]!r} share no "
                    f"row by id, so whether `rank` moves with the query was "
                    f"not measured"),
            sources={"document": LLMS, "board": SEARCH}, population=facts))
        return

    if len(fixed) != len(shared):
        conclude(Measurement(
            verdict="passed",
            reason=(f"no playbook carries a verified return or a replication, "
                    f"but `rank` moves with the query on "
                    f"{len(shared) - len(fixed)} of {len(shared)} row(s), so "
                    f"it is a relevance score and the published sentence is "
                    f"about something else"),
            sources={"document": LLMS, "board": SEARCH}, population=facts))
        return

    if not by_age:
        conclude(Measurement(
            verdict="passed",
            reason=(f"no playbook carries a verified return or a replication "
                    f"and `rank` is fixed across queries, but the order is not "
                    f"recency either, so what it is was not established here"),
            sources={"document": LLMS, "board": SEARCH}, population=facts))
        return

    conclude(Measurement(
        verdict="failed",
        reason=(f"llms.txt says agent-board/search is ranked by verified "
                f"return x replications. Not one of the {len(rows)} playbook(s) "
                f"on the board carries a confirmed replication, verified "
                f"evidence or a pnl_usdc, so that key is nil for every row; "
                f"`rank` is the same value for a row under q={QUERIES[0]!r} and "
                f"q={QUERIES[1]!r}, so it is not relevance; and the order is "
                f"exactly newest-first. An agent reading the first row as the "
                f"best-proven playbook is reading the most recent one"),
        left={"published": [line.strip() for line in claim]},
        right={"ranked": [{"title": r.get("title"), "rank": r.get("rank"),
                           "created_at": r.get("created_at"),
                           "replications": r.get("replications"),
                           "evidence_verified": r.get("evidence_verified"),
                           "pnl_usdc": r.get("pnl_usdc")} for r in ranked]},
        sources={"document": LLMS, "board": SEARCH},
        population=facts))

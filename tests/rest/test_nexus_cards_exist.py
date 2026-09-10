"""Every card Nexus tells an agent to trade is a card that exists.

The sibling of #85, which asserts the same thing about MCP tools. This is
about the ids their AI hands out, and it was found by following its advice.

Asked for a concrete, grounded, executable strategy on 2026-09-10, NEXUS
answered with a three-leg book and named each leg by card id. The two that
resolve are real, and its figures for them are right to two decimals -- it
quoted index 123.3 against a live 123.267, and 97.2 against 97.241. The
third, carrying the LARGEST allocation at 40% of the bankroll, is
`5bd86126-90eb-4ad8-8e55-909397dab402`, ticker EVCDX-POLYGON-LAYER-2-TRAN.
It answers 404, and no card matching Polygon or LAYER-2 appears anywhere in
the listing.

For that card it published a live index of 117.5 (+17.5% over base), a 90-day
return of +42.5% at Sharpe 3.83, a 30-day return of +25.4% at Sharpe 6.26,
and basket weights of 95.7% ETH and 3.9% SOL -- figures with the same shape
and precision as the ones that check out against the API for the other two.

**That precision is what makes it a defect rather than a stale reference.** An
agent cannot tell the fabricated leg from the grounded ones: same format, same
plausibility, same confident sourcing. Following the advice as given sends 40%
of the bankroll at a 404. This is the third instance of the pattern in one day
-- a bot species that cannot be cloned, an MCP tool that is not served, and now
a market that does not exist -- so what is measured here is the class, not the
one id.

WHAT THIS DOES NOT CLAIM. Not that Nexus is wrong about the market, and not
that a card which has since resolved is a defect: their platform is under
development and a subject that disappears is normal. What is asserted is
narrow and checkable -- a card presented in a CURRENT recommendation as
something to trade now answers 404 on the endpoint the same answer tells the
agent to trade it through.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

REPO = Path(__file__).resolve().parent.parent.parent
CARD = "/api/v1/event-cards/{id}"


def _nexus():
    spec = importlib.util.spec_from_file_location(
        "nexus_cards_exist", REPO / "scripts" / "nexus.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def newest_answer_naming_cards(rows):
    """The last answer that named a card id, or None.

    Newest that NAMES one, not simply newest: an answer about fees names
    none, and reading that as "nothing to measure" would make the check go
    Inconclusive for a reason that is not about the vendor. The 2026-09-10
    sweep's lesson, applied here from the start -- judging the union across
    every answer ever recorded is a question no fix can change the answer to.
    """
    from tests.rest.test_event_card_listing_reaches_them import UUID

    answers = [r for r in rows if r.get("type") == "answer" and r.get("text")]
    answers.sort(key=lambda r: (r.get("at") or "", r.get("id") or ""))
    for row in reversed(answers):
        if UUID.findall(row["text"]):
            return row
    return None


@qa(component="mcp.tools_call", tier=SafetyTier.SAFE, surface="rest")
def test_every_card_nexus_tells_an_agent_to_trade_exists(rest_trusted):
    """Guidance an agent cannot act on is guidance that does not work."""
    from tests.rest.test_event_card_listing_reaches_them import UUID

    latest = newest_answer_naming_cards(_nexus().load())
    if latest is None:
        raise Inconclusive(
            "no recorded Nexus answer names a card id, so there is nothing to "
            "look up; `python scripts/nexus.py ask \"...\"` records one")

    named = []
    for card_id in UUID.findall(latest["text"]):
        if card_id not in named:
            named.append(card_id)

    missing, found, unread = [], [], []
    for card_id in named:
        response = rest_trusted.get(CARD.format(id=card_id))
        if response.status_code == 404:
            missing.append(card_id)
        elif response.status_code == 200:
            found.append(card_id)
        else:
            # Neither confirmed nor refuted. A 500 or a 429 is a failed read
            # and a failed read is not a missing card.
            unread.append((card_id, response.status_code))

    if not found and not missing:
        raise Inconclusive(
            f"none of the {len(named)} card id(s) in {latest['id']} could be "
            f"read ({unread}); a failed read is not a missing card")

    conclude(Measurement(
        verdict="failed" if missing else "passed",
        reason=(
            f"Nexus answer {latest['id']} tells an agent to trade "
            f"{', '.join(missing)}, and {CARD} answers 404 for it while "
            f"answering 200 for {len(found)} other card(s) in the same "
            f"recommendation. An agent following the platform's own guidance "
            f"cannot act on it, and cannot tell the leg that does not exist "
            f"from the ones that do -- they carry the same format, the same "
            f"precision and the same sourcing"
            if missing else
            f"every one of the {len(found)} card(s) named in {latest['id']} "
            f"resolves"),
        left=sorted(missing), right=sorted(found),
        population={"answer": latest["id"], "at": latest.get("at"),
                    "named": len(named), "resolved": len(found),
                    "not_found": len(missing), "unread": len(unread)},
        sources={"answers": "state/nexus.jsonl", "cards": f"GET {CARD}"},
    ))

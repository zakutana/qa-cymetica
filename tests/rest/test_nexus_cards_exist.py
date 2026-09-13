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


# What a UUID is, when the words just before it say. An answer names more than
# cards: NEX-0015 gives a species ("species id `23441934...`") and NEX-0010 a
# backtest ("run_id 73b31f87..."), and until the deep pass of 2026-09-11 every
# one of them was fetched as a card -- a 404 on a species id would have gone to
# Cymetica as "Nexus tells an agent to trade" it. Triage 3/3. What no marker
# precedes is read as a card, which keeps #91's witness: a card id in a table
# row of NEX-0012, with nothing but the card's name before it.
NOT_A_CARD = ("species", "run_id", "run id", "job", "instance", "position",
              "bot", "order", "user", "wallet", "transaction", "tx",
              # Added 2026-09-12 with evidence rather than after an incident:
              # these keys carry UUIDs in our OWN records -- trade_id 9 times
              # in samples.jsonl, source_id and clone_instance_id in
              # clones.jsonl -- so they are ids their platform really issues
              # and an answer can really mention.
              "trade", "clone", "source", "backtest", "strategy")


def known_non_cards() -> set[str]:
    """UUIDs our own records show are NOT cards, whatever a sentence calls them.

    The marker list above is vocabulary, and vocabulary is a blocklist: it can
    only ever name what has already gone wrong once. This is evidence. Every
    UUID we have recorded under a key that is not `card_id` is an id their
    platform issued for something else, and it cannot become a card by being
    mentioned without a marker.

    It exists because the failure it prevents is expensive and one-directional:
    a 404 on a non-card sends Cymetica "Nexus tells an agent to trade <uuid>"
    about something that was never a card. Three readers reproduced that on
    2026-09-12, two of three voting it real.

    Never the other way round -- an id we have never recorded is NOT evidence
    of anything, and the default stays "a UUID with no marker is a card",
    because that default is what kept #91's witness: a card id in a NEX-0012
    table row with nothing but the card's name before it.
    """
    import json
    import re

    from qa.state import state_dir

    shape = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
                       r"[0-9a-f]{4}-[0-9a-f]{12}$")
    out: set[str] = set()

    def walk(node) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if (isinstance(value, str) and shape.match(value)
                        and "card" not in str(key).lower()):
                    out.add(value.lower())
                else:
                    walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    for name in ("samples.jsonl", "clones.jsonl", "paper.jsonl"):
        path = state_dir() / name
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                walk(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out
CONTEXT = 48
# "A CURRENT recommendation", in the docstring's own words. A day-old answer
# names cards that may since have resolved, and that is not a defect.
MAX_AGE_HOURS = 24


def card_ids_in(text: str) -> list[str]:
    """The card ids an answer gives, in order, once each."""
    from tests.rest.test_event_card_listing_reaches_them import UUID

    out: list[str] = []
    for match in UUID.finditer(text or ""):
        before = text[max(0, match.start() - CONTEXT):match.start()].lower()
        # Only the words on the same line: a table row or a sentence, not the
        # paragraph above it.
        before = before.rsplit("\n", 1)[-1]
        if any(marker in before for marker in NOT_A_CARD):
            continue
        if match.group(0) not in out:
            out.append(match.group(0))
    return out


def is_current(at, now) -> bool:
    """Whether an answer given at `at` is still a recommendation for `now`."""
    from datetime import datetime

    try:
        when = datetime.fromisoformat(str(at).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return False
    return (now - when).total_seconds() <= MAX_AGE_HOURS * 3600


def newest_answer_naming_cards(rows):
    """The last answer that named a card id, or None.

    Newest that NAMES one, not simply newest: an answer about fees names
    none, and reading that as "nothing to measure" would make the check go
    Inconclusive for a reason that is not about the vendor. The 2026-09-10
    sweep's lesson, applied here from the start -- judging the union across
    every answer ever recorded is a question no fix can change the answer to.
    A card id, not any UUID: an answer naming only a species is not one.
    """
    answers = [r for r in rows if r.get("type") == "answer" and r.get("text")]
    answers.sort(key=lambda r: (r.get("at") or "", r.get("id") or ""))
    for row in reversed(answers):
        if card_ids_in(row["text"]):
            return row
    return None


@qa(component="mcp.tools_call", tier=SafetyTier.SAFE, surface="rest")
def test_every_card_nexus_tells_an_agent_to_trade_exists(rest_trusted):
    """Guidance an agent cannot act on is guidance that does not work."""
    from datetime import datetime, timezone

    latest = newest_answer_naming_cards(_nexus().load())
    if latest is None:
        raise Inconclusive(
            "no recorded Nexus answer names a card id, so there is nothing to "
            "look up; `python scripts/nexus.py ask \"...\"` records one")
    if not is_current(latest.get("at"), datetime.now(timezone.utc)):
        raise Inconclusive(
            f"the newest answer naming a card, {latest['id']} "
            f"({latest.get('at')}), is over {MAX_AGE_HOURS} h old: its cards "
            f"may have resolved since, which is not a defect, and it is not a "
            f"current recommendation")

    # Vocabulary first, then evidence: an id our own records show is a trade,
    # a clone or a position is not a card however the sentence introduced it.
    ours = known_non_cards()
    named = [c for c in card_ids_in(latest["text"]) if c.lower() not in ours]

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
        # What the extractor actually read, and nothing more. It said "tells
        # an agent to trade" until the deep pass of 2026-09-13, and neither
        # `card_ids_in` nor `known_non_cards` reads trade-ness -- both answer
        # "is this a card id". NEX-0027 names a card immediately after "skip
        # it as a long this week", so that wording would have quoted them as
        # recommending a card they told an agent to avoid. The defect is
        # unchanged either way: a card the answer NAMES and that does not
        # exist is one an agent cannot tell from the ones that do.
        reason=(
            f"Nexus answer {latest['id']} names "
            f"{', '.join(missing)} as a card, and {CARD} answers 404 for it "
            f"while answering 200 for {len(found)} other card(s) in the same "
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

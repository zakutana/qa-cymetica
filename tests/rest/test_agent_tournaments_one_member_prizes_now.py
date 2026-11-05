"""A table with one member shows 1st and 2nd prizes that its own note and its result rule out (2026-11-05).

Table 79, running, one paid seat, pot $5: `prizes_now_usdc` is [3.34, 1.66] and the lobby card shows 1ST $3.34, 2ND
$1.66. In the same object `one_member_note` says "The pot is only yours ... the paper prize is your own buy-in back".
Table 59 (same kind, one member, same card while it ran) ended with its member at #5 paid $5.00.

**The rule.** On a running paper table with one paid seat and that note, `prizes_now_usdc` promising a second prize
contradicts the note: there is nobody to take it.

VERDICTS. failed: such a table lists a second prize above 0. passed: at least one such table was read and none does
(`[5, 0]`, `[5]`, or a card that names the buy-in back all read as passed here). inconclusive: a read failed or no
running table has one paid seat; the population rotates, so this is a sample.

NOT asserted: what the card should say, or that the note is right rather than the split.
SAFE: GETs only; the key is sent by the client in the header and never printed or recorded.
"""

from __future__ import annotations

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

CLAIM = "agent-tournaments-one-member-prizes-now"
BASE = "/api/v1/agent-tournaments"


def _json(client, url: str):
    try:
        got = client.get(url)
    except Exception as exc:  # noqa: BLE001 - a failed read is not an empty read (rule 8)
        raise Inconclusive(f"{url} could not be read ({type(exc).__name__})")
    if got.status_code != 200:
        raise Inconclusive(f"{url} answered HTTP {got.status_code}")
    try:
        return got.json()
    except Exception as exc:  # noqa: BLE001
        raise Inconclusive(f"{url} did not answer JSON ({type(exc).__name__})")


def second_prize(table: dict) -> float:
    prizes = table.get("prizes_now_usdc") or []
    return float(prizes[1]) if len(prizes) > 1 and prizes[1] is not None else 0.0


def one_member(table: dict) -> bool:
    return table.get("status") == "running" and table.get("paid_seats") == 1 and bool(table.get("one_member_note"))


@qa(component="rest.agent_tournaments", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_agent_tournaments_one_member_prizes_now(rest_trusted):
    """Every running table with one paid seat: its second prize against its own note."""
    lobby = _json(rest_trusted, f"{BASE}/lobby")
    ids = [t.get("id") for t in lobby.get("tables") or [] if t.get("status") == "running"]
    read = [_json(rest_trusted, f"{BASE}/tables/{i}") for i in ids]
    sample = [t for t in read if one_member(t)]
    if not sample:
        raise Inconclusive(f"none of {len(read)} running tables has one paid seat and the note")
    bad = {t.get("id"): t.get("prizes_now_usdc") for t in sample if second_prize(t) > 0}
    conclude(Measurement(
        verdict="failed" if bad else "passed",
        reason=(f"{len(bad)} of {len(sample)} running tables with one paid seat list a second prize above 0, "
                f"beside a note saying the pot is only the member's: {bad}"),
        left={"prizes_now_usdc": {t.get("id"): t.get("prizes_now_usdc") for t in sample}},
        right={"one_member_note": sample[0].get("one_member_note"), "paid_seats": 1},
        population={"running_tables_read": len(read), "with_one_paid_seat": len(sample)},
        sources={"lobby": f"GET {BASE}/lobby", "tables": f"GET {BASE}/tables/{{id}}",
                 "credential": "X-API-Key, trusted tier (value never recorded)"},
        claim_id=CLAIM))

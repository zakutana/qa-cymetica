"""A table's ET10 note still says "the best three" after /rules gave ET10 to the top 2 (2026-11-10).

Build of 10 Nov 13:58 UTC: `/rules` `et10_prizes` reads "the top 2 qualified member seats ... 85 / 42 = 127 ET10 at a
1-day table" and the lobby says "Extra for the top 2". `/rules` `et10_reward` and `GET /tables/{id}` `et10_reward_note` still read "The treasury ET10 on a paper table goes to the best three MEMBER seats by ROI that traded the
minimum volume", and the table page prints that sentence in its ET10 line and its tooltip. The ET-34608 request asked
for the top 2 "in the rules, the API and every page".

**The rule.** When `/rules` says ET10 goes to the top 2, neither /rules `et10_reward` nor any table's `et10_reward_note` may say three.

VERDICTS. failed: /rules says top 2 and at least one table's note says three. passed: /rules says top 2 and none does.
inconclusive: a read failed, /rules does not say top 2 (nothing to compare), or no table was read.

NOT asserted: which of the two is the intended rule.
SAFE: GETs only; the key is sent by the client in the header and never printed or recorded.
"""

from __future__ import annotations

import re

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

CLAIM = "agent-tournaments-reward-note-says-top-two"
BASE = "/api/v1/agent-tournaments"
THREE = re.compile(r"\b(?:best|top)\s+(?:three|3)\b", re.I)
TWO = re.compile(r"\btop\s+(?:two|2)\b", re.I)


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


def says_three(obj: dict) -> list[str]:
    return [k for k in ("et10_reward", "et10_reward_note") if THREE.search(str(obj.get(k) or ""))]


@qa(component="rest.agent_tournaments", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_agent_tournaments_reward_note_says_top_two(rest_trusted):
    """/rules says top 2; every table's ET10 note against it."""
    rules = _json(rest_trusted, f"{BASE}/rules")
    prizes = str(rules.get("et10_prizes") or "")
    if not TWO.search(prizes):
        raise Inconclusive(f"/rules et10_prizes does not say the top 2 (nothing to compare): {prizes[:120]!r}")
    lobby = _json(rest_trusted, f"{BASE}/lobby")
    ids = [t.get("id") for t in (lobby.get("tables") or [])[:8]]
    if not ids:
        raise Inconclusive("the lobby lists no table to read")
    read = [_json(rest_trusted, f"{BASE}/tables/{i}") for i in ids]
    bad = {t.get("id"): says_three(t) for t in read if says_three(t)}
    if says_three(rules):
        bad["rules"] = says_three(rules)
    conclude(Measurement(
        verdict="failed" if bad else "passed",
        reason=(f"/rules gives ET10 to the top 2, and {len(bad)} of {len(read)} tables' ET10 note still says "
                f"three: {bad}"),
        left={"tables_saying_three": bad},
        right={"rules_et10_prizes": prizes[:160]},
        population={"tables_read": len(read)},
        sources={"rules": f"GET {BASE}/rules", "lobby": f"GET {BASE}/lobby", "tables": f"GET {BASE}/tables/{{id}}",
                 "credential": "X-API-Key, trusted tier (value never recorded)"},
        claim_id=CLAIM))

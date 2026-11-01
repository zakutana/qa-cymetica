"""A one-company card keeps what its company spun off.

The contract is the card's own fields on `GET /api/v1/event-cards/{id}`: a
SAIB card holds one listed company (`basket[]`), and `current_index` is that
holding's value against `index_base` 100; `pw_index` over `pw_base` is the same
ratio from the leg's price. `GET .../index-history` publishes the path.

**What was seen when this was written** (2026-11-01). Corteva spun off its seed
business on 2026-10-01: one Vylor (VYLR) share for each Corteva share (Corteva's
8-K). CTVA closed at $77.65 on 30 Sep and $12.57 on 1 Oct, VYLR at $68.26, so a
holder had about $80.83 where they had $77.65. The card "SAIB: CTVA — Corteva":

    2026-10-01 11:57 UTC  index 94.08
    2026-10-01 15:42 UTC  index 16.32     (-82.7 % in one step)
    basket: CTVA 1.0, no VYLR; pw_base 82.54, pw_index 11.70; current_index 14.17

So the card reads about -86 % for a holder who lost nothing.

**The rule, and the fix written as a reading on day one.** The card passes when
it carries the spun-off share (a VYLR leg), or when its index carried the value
over (at least HALF of its base again). It fails while CTVA is the only leg and
both the index and the leg's own ratio stay under HALF. A card that is gone is
inconclusive: their platform changes, and retiring it is an event.

SAFE. GETs only.
"""

from __future__ import annotations

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

CARD_ID = "c387c6ae-b49c-4227-bf18-559cb67d0b7c"
CARD = f"/api/v1/event-cards/{CARD_ID}"
HISTORY = f"/api/v1/event-cards/{CARD_ID}/index-history?interval=all"
SPUN_OFF = "VYLR"
SPIN_DAY = "2026-10-01"
HALF = 0.5


def verdict_of(symbols, index, base, pw_index, pw_base) -> str:
    """'passed' on either named fix, 'failed' while neither ratio has come back."""
    if SPUN_OFF in symbols:
        return "passed"
    if index / base >= HALF or pw_index / pw_base >= HALF:
        return "passed"
    return "failed"


def spin_day_step(points) -> tuple | None:
    """The biggest published move across the spin day, as (from, to)."""
    day = [p for p in points if str(p.get("t", ""))[:10] == SPIN_DAY and isinstance(p.get("index"), (int, float))]
    pairs = [(a, b) for a, b in zip(day, day[1:]) if a["index"] > 0]
    return max(pairs, key=lambda s: abs(s[1]["index"] / s[0]["index"] - 1), default=None)


@qa(component="rest.event_cards", tier=SafetyTier.SAFE, surface="rest")
def test_a_card_keeps_what_its_company_spun_off(rest_trusted):
    """The CTVA card, against the Vylor distribution of 2026-10-01."""
    response = rest_trusted.get(CARD)
    if response.status_code != 200:
        raise Inconclusive(f"{CARD} answered HTTP {response.status_code}")
    body = response.json() or {}
    body = body.get("card", body)
    index, base = body.get("current_index"), body.get("index_base")
    pw_index, pw_base = body.get("pw_index"), body.get("pw_base")
    if not all(isinstance(v, (int, float)) and v > 0 for v in (index, base, pw_index, pw_base)):
        raise Inconclusive(f"the card has no price to read: current_index {index}, index_base {base}, "
                           f"pw_index {pw_index}, pw_base {pw_base}")
    symbols = [leg.get("symbol") for leg in body.get("basket") or []]
    history = rest_trusted.get(HISTORY)
    step = spin_day_step((history.json() or {}).get("points") or []) if history.status_code == 200 else None
    said = (f"{step[0]['t'][:16]} {step[0]['index']:.2f} -> {step[1]['t'][:16]} {step[1]['index']:.2f}"
            if step else f"no step readable on {SPIN_DAY}")
    verdict = verdict_of(symbols, index, base, pw_index, pw_base)
    conclude(Measurement(
        verdict=verdict,
        reason=(f"basket {symbols}, current_index {index:.2f} on base {base:.0f}, pw_index/pw_base "
                f"{pw_index}/{pw_base}; {said}. Corteva distributed one {SPUN_OFF} per share on {SPIN_DAY}"
                + ("; the card neither holds it nor carried its value over" if verdict == "failed" else "")),
        left={"basket": symbols, "current_index": index, "pw_index": pw_index, "pw_base": pw_base},
        right=f"a {SPUN_OFF} leg, or an index at least {HALF:.0%} of its base",
        population={"card": CARD_ID},
        sources={"card": CARD, "history": HISTORY}))

"""A bot pick's band is not the card pick's exits: `lab.exit_levels` must close a card's scope at the next pick (T-0073).

2026-10-13, NEX-0143 (state/nexus.jsonl line 1400, answered 16:05:32 UTC). Pick 1 is the card
4274529f-5d62-45e3-aca6-5777702bd7c4 and gives no take-profit and no stop in %: "Hold: 7 days", "Drop it if: index
prints below 100.0". Pick 2 is the bot Fibonacci Phoenix, "SL 3% / TP 6%", and says nothing of a card. `exit_levels`
(qa/lab.py:2119) leaves a pick's scope open until a line names ANOTHER wanted card, and a bot pick names no card
UUID, so Pick 2's numbers land on the card: room STR-0214 (state/rooms.jsonl 1488-1489) carries the card leg with
tp 6.0, sl -3.0, and `sell_at_exits` sells his card at a band he gave a bot. The hourly look can fire that -3 % stop
any hour until 2026-10-20 16:09 UTC.

The fix is the session's (qa/ is closed to workers). What it must do: a line that opens a NEW pick -- the `_PICKED`
reading of "**Pick 2 -- Bot clone ...**", "PICK 3 --", "Pick: ..." -- and names none of the wanted picks ends the
current pick's scope (`current = None`), exactly as a line naming another wanted card already does. The next line that
names a wanted card opens its scope again, so a header that carries no UUID ("**Pick 1 -- Event card**" over a line
holding it) is unharmed. Whether STR-0214's leg is corrected is the manager's.

Fixed in the deep pass of 2026-10-18, with `_PICKED` taught his ASCII " -- " (B01): replayed over all 87 answers on
disk, NEX-0143's card is the one pick whose levels changed (tp 6 / sl -3 -> None / None), and no line of any answer
reads differently as a pick. The controls keep passing: a card's own levels are still read, and a card pick after a
bot pick still gets its own.
"""

from __future__ import annotations

import pytest

from qa import lab
from qa.marks import SafetyTier, qa

CARD = "4274529f-5d62-45e3-aca6-5777702bd7c4"
OTHER = "5d91bf43-a597-47b0-9abe-5c7f52618bbd"

# NEX-0143's three picks, as he wrote them (shortened prose, every level line verbatim).
NEX_0143 = f"""## (2) Three concrete picks a paper room can hold

All three run on paper today. Bot clones: `clone_bot` (paper default) -> `fund_clone_bot` -> `toggle_bot_trading(enabled=true)`; SL/TP via `update_bot_settings` / `PATCH /api/v1/cloned-bots/{{id}}/settings`.

**Pick 1 — Event card, live & tradeable now (verified this run):**
`{CARD}` — "Spot Bitcoin ETFs see record 10-day outflow streak" card. Live index 107.18 (**+7.18%** since inception), `tradeable_now: true`.
- Hold: **7 days.**
- Exit: `trade_event_card` sell (REST `POST /api/v1/event-cards/{{id}}/sell`).
- Drop it if: **index prints below 100.0** (round-trips the entire +7.18% gain back to base).

**Pick 2 — Bot clone, mean-reversion:**
Species **Fibonacci Phoenix** (FIB) — 3,593 trades, 40.0% win rate. SL/TP I'd set: **SL 3% / TP 6%** (2:1).
- Hold: **14 days** paper.
- Exit: on TP/SL, or `toggle_bot_trading(enabled=false)`.
- Drop it if: **net paper P&L hits −8%**, or realized win rate falls below ~33%.

**Pick 3 — Bot clone, momentum:**
Species **MACD Hunter** (MACD) — 1,791 trades. SL/TP: **SL 4% / TP 8%** (2:1).
- Hold: **14 days** paper.
- Drop it if: **8 consecutive losing paper trades**, or net paper P&L hits −6%.
"""


ASCII = NEX_0143.replace("**Pick 2 —", "**Pick 2 --").replace("**Pick 3 —", "PICK 3 --")


# B01, deep pass 2026-10-18: the docstring names the ASCII "**Pick 2 -- Bot clone**" and "PICK 3 --" as
# scope-ending lines, but this test held only the em-dash, and `_PICKED` read only the em-dash: a fix on
# `_PICKED` as it stood passed here while his ASCII spelling still handed the bot's band to the card.
@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize("answer", [NEX_0143, ASCII], ids=["em-dash", "ascii"])
def test_a_bot_picks_band_is_not_the_card_picks_exits(answer):
    said = lab.exit_levels(answer, [CARD])
    assert said[CARD] == {"tp": None, "sl": None}, (
        f"NEX-0143 gave the card no take-profit and no stop in %; read {said[CARD]} -- the bot Fibonacci "
        f"Phoenix's 'SL 3% / TP 6%' (Pick 2) and MACD Hunter's 'SL 4% / TP 8%' (Pick 3) are not his")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_cards_own_levels_are_still_read_and_stop_at_the_next_pick():
    text = (f"**Pick 1 -- Event card:**\n`{CARD}` -- hold 7 days.\n- TP +9% / stop -4%\n"
            "**Pick 2 -- Bot clone:**\nSpecies **Fibonacci Phoenix**. SL 3% / TP 6%.\n"
            f"**Pick 3 -- Event card:**\n`{OTHER}` -- hold 5 days.\n- take-profit +12% / stop -7%\n")
    assert lab.exit_levels(text, [CARD, OTHER]) == {CARD: {"tp": 9.0, "sl": -4.0},
                                                    OTHER: {"tp": 12.0, "sl": -7.0}}
    # A header that carries the card's id on its own line: its levels below are still its own.
    one = f"**Pick 1 -- `{CARD}`**\n- Hold: 7 days\n- TP +9% / stop -4%\n"
    assert lab.exit_levels(one, [CARD]) == {CARD: {"tp": 9.0, "sl": -4.0}}

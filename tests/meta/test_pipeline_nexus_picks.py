"""What the laboratory reads out of Nexus's answers, against what he wrote.

C7 of the 2026-09-23 review (3/3): the reader took a bot as picked when any
line naming it carried a word like "clone" or "recommend". NEX-0080 picks one
bot on its `**Pick:**` line and then compares it with the four we already run
("...on a 5-day paper run it's the clone most likely to be uncorrelated") --
and the reader came back with five. NEX-0010 compared its pick with MACD Hunter
("run each as a paper clone") and came back with two. Only one room opened
from NEX-0080, because the other four were already cloned; the reading was
wrong all the same, and it is what the board and the brief are built from.

So a pick is read from a line that DECLARES one -- `Pick:`, `The one to
clone:`, `Answer:`, `PICK 1 --`, "I would clone" -- and prose that merely
mentions a species or says "clone" is not one. An answer with no such line
keeps the old reading: every name less those he ruled out.

The answers are his, verbatim, in tests/meta/fixtures/nexus_answers.json, and
so are the catalogues they were read against. NEX-0050 is in the fixture and
not below: its card is on a "Pair-with card id:" line beside the card it
pairs with, and no line declares either -- the launch opened the right one
only because the other was already held.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from qa import lab
from qa.marks import SafetyTier, qa

FIXTURE = json.loads((Path(__file__).resolve().parent / "fixtures"
                      / "nexus_answers.json").read_text(encoding="utf-8"))

# Read by hand from each answer. Cards as the launch sees them: every id he
# names, less the species ids of bots (a bot is not a card, #91).
EXPECTED = {
    # 73b31f87 is the id of a backtest run he cites, not a card: the reader
    # hands it on, and their API's 404 is what says so (`unknown_card`).
    "NEX-0010": {"bots": ["Perceptron Oracle"],
                 "cards": ["73b31f87-8825-4e19-b103-5a93aa67ad21"]},
    "NEX-0045": {"cards": ["30015006-abff-44b6-bdb0-f659faf4f3f4"]},
    "NEX-0059": {"cards": ["a4a5b71e-de11-4805-b8a3-ed9c3f8f8161"]},
    "NEX-0060": {"cards": ["9ef04dc6-dc11-447a-a360-b6395f618648"]},
    "NEX-0063": {"cards": ["5e25b255-6ace-49a7-a748-e70a3dac6b3a"]},
    "NEX-0064": {"cards": ["9f9433ef-75ec-4637-a743-64d9110545bf"]},
    "NEX-0065": {"cards": ["1de24f14-38f1-40d9-ac7f-993c1592781f",
                           "9c7b0e8c-8799-47af-9100-38cff2c50c83",
                           "e849ec0f-45be-43e2-8f01-4945c78346e1"]},
    "NEX-0066": {"cards": ["c3525683-c0e1-4ea6-b00c-cc9aa9fb44bf",
                           "0a35dd76-0929-4d64-8f79-18e677e2c758"]},
    "NEX-0067": {"cards": ["6d0b5308-c151-45a2-b4eb-d2f6c61fc4eb",
                           "d43bdb4f-694e-4511-ba70-648750a6fe82",
                           "db54ed55-851d-40ac-a775-a43e43604a28"]},
    "NEX-0068": {"cards": ["27c96532-123d-494f-ab89-d7dcdb8af33f"]},
    "NEX-0069": {"cards": ["a9cf285b-4da2-4eda-97b9-4b0b52cb1677",
                           "c0d78ca5-d864-4fb3-90c7-8b1bfde4c2c2",
                           "0112ab1b-39ad-42b8-a78c-529e6bcbbba1"]},
    "NEX-0070": {"cards": ["9fcda87b-ff0b-42d0-888c-5eb9e3a46a54",
                           "74e34e84-9dc6-4a33-ad58-32f7b52c3226"]},
    "NEX-0073": {"bots": ["MACD Hunter"]},
    "NEX-0079": {"cards": ["97b827ad-b61d-4d3f-8398-8548ebc2a242"]},
    "NEX-0080": {"bots": ["Bollinger Bandit"]},
    "NEX-0081": {"funds": ["AIB-MOLECULAR"]},
    "NEX-0086": {"funds": ["AIB-BIOSCIENCES"]},
    "NEX-0088": {"cards": ["5d91bf43-a597-47b0-9abe-5c7f52618bbd"]},
    # 2026-10-01: "**a) Bot -- clone "Fibonacci Phoenix" ..., PAPER.**" went
    # on to say "not a buy-and-hold" about the trade's shape, and the reader
    # took the whole line as ruling the bot out -- while Bollinger Bandit,
    # named only as our own calibration quoted back, came out as his pick.
    # 30018bee is the card he says is paused; he picks 27c96532 under b).
    "NEX-0109": {"bots": ["Fibonacci Phoenix"],
                 "cards": ["27c96532-123d-494f-ab89-d7dcdb8af33f"]},
}


# His take-profit and stop for each pick, read by hand. A stop is a fall.
# The plan's V2: "Nexus's TP/SL go into the plan legs before
# set_acceptance" -- every room of 2026-09-21..23 carries tp None, sl None
# while he named both each time, so the criterion judged his idea without
# his exits.
LEVELS = {
    "NEX-0045": {"30015006-abff-44b6-bdb0-f659faf4f3f4": (20.0, -12.0)},
    "NEX-0059": {"a4a5b71e-de11-4805-b8a3-ed9c3f8f8161": (8.0, -5.0)},
    "NEX-0060": {"9ef04dc6-dc11-447a-a360-b6395f618648": (10.0, -6.0)},
    "NEX-0063": {"5e25b255-6ace-49a7-a748-e70a3dac6b3a": (4.0, -3.0)},
    "NEX-0064": {"9f9433ef-75ec-4637-a743-64d9110545bf": (15.0, -9.0)},
    "NEX-0065": {"1de24f14-38f1-40d9-ac7f-993c1592781f": (14.0, -9.0),
                 "9c7b0e8c-8799-47af-9100-38cff2c50c83": (9.0, -6.0),
                 "e849ec0f-45be-43e2-8f01-4945c78346e1": (4.0, -3.0)},
    "NEX-0066": {"c3525683-c0e1-4ea6-b00c-cc9aa9fb44bf": (22.0, -15.0),
                 "0a35dd76-0929-4d64-8f79-18e677e2c758": (30.0, -18.0)},
    "NEX-0067": {"6d0b5308-c151-45a2-b4eb-d2f6c61fc4eb": (12.0, -7.0),
                 "d43bdb4f-694e-4511-ba70-648750a6fe82": (20.0, -13.0),
                 "db54ed55-851d-40ac-a775-a43e43604a28": (25.0, -15.0)},
    "NEX-0068": {"27c96532-123d-494f-ab89-d7dcdb8af33f": (12.0, -8.0)},
    "NEX-0069": {"a9cf285b-4da2-4eda-97b9-4b0b52cb1677": (6.0, -4.0),
                 "c0d78ca5-d864-4fb3-90c7-8b1bfde4c2c2": (18.0, -10.0),
                 "0112ab1b-39ad-42b8-a78c-529e6bcbbba1": (10.0, -7.0)},
    "NEX-0070": {"9fcda87b-ff0b-42d0-888c-5eb9e3a46a54": (15.0, -6.0),
                 "74e34e84-9dc6-4a33-ad58-32f7b52c3226": (15.0, -10.0)},
    "NEX-0079": {"97b827ad-b61d-4d3f-8398-8548ebc2a242": (8.0, -5.0)},
    "NEX-0081": {"AIB-MOLECULAR": (None, -6.0)},
    "NEX-0088": {"5d91bf43-a597-47b0-9abe-5c7f52618bbd": (25.0, -12.0)},
    "NEX-0109": {"27c96532-123d-494f-ab89-d7dcdb8af33f": (15.0, -10.0)},
}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize("answer_id", sorted(LEVELS))
def test_his_take_profit_and_stop_are_read_for_each_pick(answer_id):
    text = FIXTURE["answers"][answer_id]["text"]
    picks = list(LEVELS[answer_id])
    said = lab.exit_levels(text, picks)
    for pick, (tp, sl) in LEVELS[answer_id].items():
        assert (said[pick]["tp"], said[pick]["sl"]) == (tp, sl), (
            f"{answer_id} {pick[:12]}: read {said[pick]}, he said tp {tp} sl {sl}")
    _how_long_to_hold_is_read_from_his_words_and_bounded()
    _a_hold_period_wrapped_in_markdown_is_still_his()
    _a_bots_band_is_read_in_the_field_names_he_wrote()


def _how_long_to_hold_is_read_from_his_words_and_bounded():
    """2026-10-03, the operator: "to je kriticke rozhodnuti, to musi rict nexus". The window
    of a card room was the laboratory's own 3 days; it is his now, when he names one.

    A period outside the range he was told (1 to 14 days) is NOT his window clamped to the
    bound -- that wrote "the window is his, 14 days" into the criterion of a room he asked
    21 days for (deep pass 2026-10-04, R02). It reads as no usable period at all."""
    text = ("**1. `aaaaaaaa-1111-2222-3333-444444444444`** -- long, hold 5 days, TP +6 / SL -4.\n"
            "**2. `bbbbbbbb-1111-2222-3333-444444444444`** -- a 7-day hold, TP +9 / stop -6. 30d "
            "backtest +8%, 90d +28%.\n"
            "**3. `cccccccc-1111-2222-3333-444444444444`** -- horizon: 21 days.\n"
            "**4. `dddddddd-1111-2222-3333-444444444444`** -- TP +4 / stop -3, a 90d backtest.\n"
            "**5. `eeeeeeee-1111-2222-3333-444444444444`** -- hold for 12 hours only.\n"
            "**6. `ffffffff-1111-2222-3333-444444444444`** -- hold 30 days.\n"
            "**7. `99999999-1111-2222-3333-444444444444`** -- hold 0.2 days.\n"
            "**8. `88888888-1111-2222-3333-444444444444`** -- hold 14 days.\n"
            "**9. `77777777-1111-2222-3333-444444444444`** -- hold 1 day, not more.\n"
            "**10. `66666666-1111-2222-3333-444444444444`** -- hold 30 days.\n"
            "Later: hold 5 days if it works.\n")
    picks = ["aaaaaaaa-1111-2222-3333-444444444444", "bbbbbbbb-1111-2222-3333-444444444444",
             "cccccccc-1111-2222-3333-444444444444", "dddddddd-1111-2222-3333-444444444444",
             "eeeeeeee-1111-2222-3333-444444444444", "ffffffff-1111-2222-3333-444444444444",
             "99999999-1111-2222-3333-444444444444", "88888888-1111-2222-3333-444444444444",
             "77777777-1111-2222-3333-444444444444", "66666666-1111-2222-3333-444444444444"]
    said = lab.hold_periods(text, picks)
    # 21, 30 and 0.2 days are outside 1..14: no usable hold, never the bound. The bounds
    # themselves are inside. And the first period he states decides: the unusable 30 days of
    # pick 10 is not rescued by the "hold 5 days" on a later line.
    assert [said[p] for p in picks] == [
        5.0, 7.0, None, None, None, None, None, 14.0, 1.0, None], said
    # A backtest's "30d" or "90d" is not a holding period, and neither is an hour count.
    assert lab.hold_periods("90d +28%, 30d +3%, Sharpe 3.4", ["x"]) == {"x": None}


def _a_hold_period_wrapped_in_markdown_is_still_his():
    """NEX-0133 and NEX-0134 (2026-10-11): he named a hold and the launcher said he had not.

    He wrote "**Hold:** **5 days**" and "- **hold:** 10 days", the bold markers sitting between
    the colon and the number, and the reader's pattern allowed a colon and spaces there but not
    two asterisks. The DePIN card he proposed twice, with a hold, a take-profit and a stop,
    was held both times for "no usable hold period" -- and the next question was spent asking
    for what he had already said. A marker that only dresses the text is not part of what it
    says; a period that is out of range is still not rescued by it."""
    depin = "047996d8-369c-47ee-a942-d2d44761fa6f"
    other = "5d91bf43-a597-47b0-9abe-5c7f52618bbd"
    text = (f"## Card -- Gem Screener DePIN\n- **id:** `{depin}` (EVCDX-GEM-SCREENER-DEPIN)\n"
            "- **side:** UP (bull / long).\n"
            "- **hold:** 10 days -- close at end of that period, or earlier at TP/stop.\n"
            "- **take-profit +15% / stop -10%**\n"
            f"**Card UUID:** `{other}`\n"
            "- **Hold:** **5 days** (short, to cap exposure)\n")
    assert lab.hold_periods(text, [depin, other]) == {depin: 10.0, other: 5.0}
    # Dressed up, out of range stays unusable.
    assert lab.hold_periods(f"`{depin}`: **hold:** **30 days**", [depin]) == {depin: None}


def _a_bots_band_is_read_in_the_field_names_he_wrote():
    """NEX-0137 (2026-10-11): asked which species to run next and on which band, he named four,
    each on its own line in the platform's own field names -- "stop_loss_pct **12**,
    take_profit_pct **30**" -- and the launcher read none of them: `exit_levels` wants a % sign
    and a word boundary that the underscores do not give, and our tool-name check had written
    "[no such tool]" between one field and its number. A band is both numbers inside the
    platform's bounds (stop 1-20, target 5-100), or it is no band; a line naming two species
    gives neither of them one."""
    text = ("- **Perceptron Oracle** — stop_loss_pct **12**, take_profit_pct **30** (2.5:1).\n"
            "  Largest sample on the platform.\n"
            "- **Fibonacci Phoenix** — stop_loss_pct [no such tool] **10**, take_profit_pct "
            "**22** (2.2:1, breakeven 31.3%).\n"
            "- **MACD Hunter** — stop_loss_pct **25**, take_profit_pct **36**.\n"
            "- For **RSI Sniper** and **Stochastic Striker** +40 is too far: stop_loss_pct 10, "
            "take_profit_pct 24.\n"
            "- **Trend Titan** — a stop-loss of 8 % and a take-profit of 20 %.\n"
            "- **Trend Titan** — stop-loss 8 %, take-profit 20 %.\n"
            "- **Divergence Dragon**: your 15/40 is fine; take_profit_pct 60 alone.\n"
            "Set the band via update_bot_settings (stop_loss_pct [no such tool] / take_profit_pct).\n")
    names = ["Perceptron Oracle", "Fibonacci Phoenix", "MACD Hunter", "RSI Sniper",
             "Stochastic Striker", "Trend Titan", "Divergence Dragon", "ATR Alpha"]
    assert lab.bot_bands(text, names) == {
        "Perceptron Oracle": {"stop_loss_pct": 12.0, "take_profit_pct": 30.0},
        "Fibonacci Phoenix": {"stop_loss_pct": 10.0, "take_profit_pct": 22.0},
        # 25 is past their stop bound: no band, never 20.
        "MACD Hunter": None,
        "RSI Sniper": None, "Stochastic Striker": None,
        "Trend Titan": {"stop_loss_pct": 8.0, "take_profit_pct": 20.0},
        # A target alone is half a band.
        "Divergence Dragon": None,
        "ATR Alpha": None}


def _read(answer_id: str) -> dict:
    text = FIXTURE["answers"][answer_id]["text"]
    species = {row["id"].lower() for row in FIXTURE["bots"]}
    return {"cards": lab.picked_cards(text, species),
            "bots": [row["name"] for row in lab.proposed_bots(text, FIXTURE["bots"])],
            "funds": lab.proposed_funds(text, FIXTURE["funds"])}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize("answer_id", sorted(EXPECTED))
def test_a_pick_is_read_from_the_line_that_declares_it(answer_id):
    said = _read(answer_id)
    for kind in ("cards", "bots", "funds"):
        assert said[kind] == EXPECTED[answer_id].get(kind, []), (
            f"{answer_id} {kind}: read {said[kind]}, he picked "
            f"{EXPECTED[answer_id].get(kind, [])}")

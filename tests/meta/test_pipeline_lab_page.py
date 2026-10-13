"""/lab, the laboratory's page: one room per sector, results first.

The operator, 2026-09-23, on the first /lab: "proč má každá karta svůj room?
já myslel že bude 1 room na odvětví ... musím moc scrollovat, nepřehledné.
Design 3/10." And on the chat: they will hardly ever read it, maybe glance
at it out of curiosity. So the page is three sector rooms -- Cards, Bots,
Memecoins (Funds went on 2026-10-03: the operator stopped measuring them) --
each a ranking of its experiments by what they made after costs, failures
folded into an archive, and the conversation behind a button.

Two layers, each held here. `lab_view()` joins the rooms, the report, Nexus's
channel and the memecoin diary into what the page draws -- pure, so a test
holds all of it. The page itself is run in node over that view.
"""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone

import pytest

from qa.marks import SafetyTier, qa
from tests.meta.test_pipeline_render import _lab_page, _run_page

NOW = datetime(2026, 9, 23, 12, 0, tzinfo=timezone.utc)


def _series(start_hour: int, values: list[float]) -> list[list]:
    return [[f"2026-09-22T{start_hour + i:02d}:00:00+00:00", v]
            for i, v in enumerate(values)]


def _rooms_view() -> dict:
    """The shape build_rooms() writes, one of each kind of experiment."""
    card = {
        "kind": "strategy", "origin": "NEX-0066", "status": "running",
        "title": "Zcash (ZEC) Rally Accelerates", "opened_at": "2026-09-22T02:00:00+00:00",
        "invested": 500.0, "pnl": 10.0, "pnl_pct": 2.0, "value": 510.0,
        "criterion": {"window_days": 5.0, "stop_pct": 10.0,
                      "at": "2026-09-22T02:00:00+00:00"},
        "verdict": None, "clones": [],
        # The index we bought at is NOT any reading in the series (99 before the buy, 100 at the
        # buy hour): a line rebased on the first reading it draws would start at 0 and read 1, 2.
        "legs": [{"card": "c1", "url": "https://cymetica.com/events/c1",
                  "entry": 99.5, "tp": 8.0, "sl": -5.0,
                  "series": _series(1, [99.0, 100.0, 101.0, 102.0])}],
        "trades": [{"id": "TRD-1", "at": "2026-09-22T02:00:00+00:00",
                    "outcome": "accepted", "closed_at": None}],
        "backtests": [{"verdict": "pass", "period": 90, "return_pct": 26.2,
                       "sharpe": 2.18, "drawdown_pct": 14.1}]}
    return {
        "rooms": [{"id": "general", "kind": "general", "title": "General"},
                  *[{"id": rid, "kind": "strategy", "title": rid}
                    for rid in ("STR-0001", "STR-0002", "STR-0003",
                                "STR-0004", "STR-0005", "STR-0009")]],
        "threads": {"general": [{"kind": "question", "id": "NEX-1",
                                 "at": "2026-09-20T01:00:00+00:00", "text": "?"}],
                    "cards": [{"kind": "operator_note", "id": "N-1",
                               "at": "2026-09-23T01:00:00+00:00", "text": "hm"}],
                    "STR-0001": [], "STR-0002": [], "STR-0003": [],
                    "STR-0004": [], "STR-0005": [], "STR-0009": []},
        "panels": {
            "general": {"balance": 88593.91, "notional": 24329.56,
                        "balance_at": "2026-09-23T11:00:00+00:00",
                        "stale": False, "sampled_at": "2026-09-23T11:50:00+00:00"},
            "STR-0001": card,
            "STR-0002": {**card, "status": "stopped", "invested": 0,
                         "title": "Never bought", "legs": [], "trades": [],
                         "backtests": []},
            "STR-0003": {"kind": "strategy", "status": "running",
                         "title": "Bollinger Bandit", "origin": "NEX-0080",
                         "opened_at": "2026-09-23T01:31:00+00:00",
                         "criterion": {"window_days": 5.0,
                                       "at": "2026-09-23T01:31:00+00:00"},
                         "verdict": None, "legs": [], "trades": [],
                         "backtests": [], "invested": 240.0,
                         "clones": [{"funded": 240.0, "trading": False,
                                     "stop": {"cause": "unexplained", "pct": 3.0},
                                     "balance": 247.2,
                                     "samples": [{"at": "2026-09-23T02:00:00+00:00",
                                                  "pnl": 24.0},
                                                 {"at": "2026-09-23T10:00:00+00:00",
                                                  "pnl": 7.2}]}]},
            "STR-0004": {**card, "status": "stopped", "title": "Solana doubles",
                         "verdict": {"verdict": "refuted", "return_pct": -3.1,
                                     "why": "its drawdown reached 11.78%, past the "
                                            "10.00% it was accepted with"}},
            "STR-0005": {**card, "title": "Arena BLUE"},
            # A fund we bought into and that is running: the one kind of room no page draws
            # now (the operator, 2026-10-03: Funds are not measured).
            "STR-0009": {**card, "title": "Fund we watch"},
        }}


def _report() -> dict:
    def sector(**over):
        base = {"n": 1, "net_pct": 1.0, "usdc": 5.0, "stake_usdc": 500.0,
                "wins": 1, "wilson": None, "min_n": 5, "running": 1,
                "archived": 0}
        return {**base, **over}
    return {
        "generated_at": "2026-09-23T12:00:00+00:00",
        "products": {
            "cards": sector(n=2, archived=1),
            "bots": sector(usdc=7.2, stake_usdc=240.0),
            "memecoins": {**sector(n=673, net_pct=-19.8, usdc=None, stake_usdc=None,
                                   running=302, archived=None),
                          "median_pct": -40.0, "fee_pct": 1.0, "signals": 2705,
                          "could_buy_share": 0.52,
                          "conviction_70": {"min": 70.0, "n": 45, "net_pct": -12.0,
                                            "median_pct": -55.0},
                          "fees": [{"fee_pct": 0.5, "net_pct": -19.0, "n": 673}],
                          "excluded": {"unpriced": 1200, "too_thin": 300}},
            "funds": sector(n=0, net_pct=None, usdc=None, stake_usdc=None, wins=0),
        },
        "nexus": {"questions": 88, "answered": 53, "picks": 31, "gated": 31,
                  "gate_pass": 22, "survived": 0, "refuted": 1,
                  "inconclusive": 2, "running": 9},
        "rooms": [
            {"id": "STR-0001", "product": "cards", "archived": False,
             "net_pct": 0.59, "usdc": 2.95, "stake_usdc": 500.0, "verdict": None},
            {"id": "STR-0002", "product": "cards", "archived": True,
             "net_pct": None, "usdc": None, "stake_usdc": None, "verdict": None},
            {"id": "STR-0003", "product": "bots", "archived": False,
             "net_pct": 3.0, "usdc": 7.2, "stake_usdc": 240.0, "verdict": None},
            {"id": "STR-0004", "product": "cards", "archived": False,
             "net_pct": -3.1, "usdc": -15.5, "stake_usdc": 500.0,
             "verdict": "refuted"},
            {"id": "STR-0005", "product": None, "archived": False,
             "net_pct": None, "usdc": None, "stake_usdc": None, "verdict": None},
            {"id": "STR-0009", "product": "funds", "archived": False,
             "net_pct": 2.0, "usdc": 10.0, "stake_usdc": 500.0, "verdict": None}],
    }


def _view():
    return _lab_page().lab_view(_rooms_view(), _report(), now=NOW)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_view_is_seven_sections_in_their_order_with_their_names():
    view = _view()
    # Laboratory v3 (2026-10-11): seven sections, in the operator's order. The keys of the
    # three that existed stay what they were -- cards are his, bots, memecoins -- so no room
    # and no note written to one of them moves.
    # Funds are not measured any more (the operator, 2026-10-03: "Funds room uplne zrus,
    # nebudem merit"), so there is no Funds room and a fund room is on no page.
    assert [s["key"] for s in view["sectors"]] == [
        "own", "cards", "bots", "h2h", "memecoins", "outsider", "desk"]
    # English since 2026-09-25 (CLAUDE.md, How to work with me).
    assert [s["name"] for s in view["sectors"]] == [
        "Our cards", "Nexus cards", "Bots", "Head-to-head", "Memecoins", "Outsider", "Desk"]
    # What a section is for goes in a tooltip, never a paragraph on the page: one short line.
    assert all(0 < len(s.get("about") or "") <= 120 for s in view["sectors"]), [
        s.get("about") for s in view["sectors"]]
    # A section with nothing in it yet is drawn all the same, with no figure invented.
    outsider = next(s for s in view["sectors"] if s["key"] == "outsider")
    assert outsider.get("net_pct") is None and not outsider.get("n")
    page = _lab_page()
    # P2: what a section knows (qa.lab.knowledge, docs/lab-knowledge.md) rides on its tab's
    # entry, so the room can show it folded; a section that knows nothing has an empty list.
    known = page.lab_view(_rooms_view(), _report(), now=NOW,
                          known={"bots": ["15/40: 39 stop-losses to 13 take-profits"]})
    by_key = {s["key"]: s for s in known["sectors"]}
    assert by_key["bots"]["known"] == ["15/40: 39 stop-losses to 13 take-profits"]
    assert by_key["desk"]["known"] == [] and by_key["cards"]["known"] == []
    # Our own cards are cards: the 18-hour column is theirs too; head-to-head bots are bots.
    assert page.CARD_SECTIONS == ("own", "cards") and page.BOT_SECTIONS == ("bots", "h2h")
    assert page._group({}, {"verdict": {"verdict": "refuted"}}, "h2h") == "archive"
    assert page._group({}, {"verdict": {"verdict": "refuted"}}, "own") == "done"
    # "A fund room is on no page" is measured, not only said: the fixture holds a running fund
    # room the report calls a fund (T10, deep pass 2026-10-04), and no sector or row carries it.
    assert [r["product"] for r in _report()["rooms"] if r["id"] == "STR-0009"] == ["funds"], (
        "the fixture has no fund room")
    assert "STR-0009" in {r["id"] for r in _rooms_view()["rooms"]}
    assert "STR-0009" not in {e["id"] for e in view["experiments"]}, "a fund room is on the page"
    assert all(e["sector"] != "funds" for e in view["experiments"])
    cards = next(s for s in view["sectors"] if s["key"] == "cards")
    assert cards["net_pct"] == 1.0 and cards["usdc"] == 5.0, "the report's figures ride along"
    # What the room says about the 18-hour column: its average and the share in profit,
    # over the experiments of that sector that have a figure -- and none when none does.
    page = _lab_page()
    stats = page._h18_stats([{"sector": "cards", "at_18h": 1.0}, {"sector": "cards", "at_18h": -3.0},
                             {"sector": "cards", "at_18h": 4.0}, {"sector": "cards", "at_18h": None},
                             {"sector": "bots", "at_18h": 9.0}], "cards")
    assert stats == {"n": 3, "avg": pytest.approx(2.0 / 3), "pos_pct": pytest.approx(200.0 / 3)}, stats
    assert page._h18_stats([{"sector": "cards", "at_18h": None}], "cards") is None
    assert "h18" in cards
    # The 18-hour figure is for cards only ("to se prece tyka jen karet"): a bot runs until
    # something stops it, so no bot row and no bot room carries one.
    assert next(s for s in view["sectors"] if s["key"] == "bots")["h18"] is None
    assert all(e["at_18h"] is None for e in view["experiments"] if e["sector"] == "bots")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_each_experiment_lands_in_its_sector_and_its_group():
    """Running experiments are live; one with a verdict is done; one the
    report archived is in the archive with a short reason, never a paragraph
    (N-0034, N-0049, N-0050) -- if it bought something: a room that bought nothing
    is in no list at all (2026-10-03, no clutter). An Arena room is in no sector
    yet, and a fund room is in none any more, so each is on no page rather than
    among cards."""
    by_id = {e["id"]: e for e in _view()["experiments"]}
    # A room that bought nothing is not listed at all (the operator, 2026-10-03: no clutter):
    # a row of dashes tells nothing. A failed or not-his-pick room that DID buy stays in the
    # archive with its reason.
    assert set(by_id) == {"STR-0001", "STR-0003", "STR-0004"}, set(by_id)
    assert (by_id["STR-0001"]["sector"], by_id["STR-0001"]["group"]) == ("cards", "live")
    assert by_id["STR-0004"]["group"] == "done"
    assert by_id["STR-0004"]["reason"] == "drawdown 11.8% past 10% limit"
    # A bot that stopped itself in profit is over: not "live" for two more
    # days, and the reason says where it stopped (2026-09-26).
    assert (by_id["STR-0003"]["sector"], by_id["STR-0003"]["group"],
            by_id["STR-0003"]["reason"]) == ("bots", "done", "stopped by itself at +3%")
    assert by_id["STR-0003"]["trading"] is False
    # The rest of the stopped-bot rule lives in helpers below, not tests of
    # their own: tests/meta is held to a ceiling.
    _check_a_bot_that_stopped_itself_is_done_and_says_which_limit_it_hit()
    _check_the_row_says_how_long_each_bot_ran_and_why_it_stopped()
    _check_a_bot_still_trading_or_paused_by_us_or_never_started_stays_live()
    _check_a_batch_room_is_done_only_when_every_bot_in_it_has_stopped()
    _check_the_stop_a_clone_carries_is_the_diaries_and_only_while_it_is_stopped()
    for e in by_id.values():
        assert not e["reason"] or len(e["reason"]) <= 40, e["reason"]
    # 2026-10-03, the operator: "z done botu dej do archive ty co nefungovaly". A bot room
    # that did not work leaves Done for the Archive and still says why; one that worked or
    # could not be told stays in Done, and a card that did not work stays where it was.
    page = _lab_page()
    refuted = {"verdict": {"verdict": "refuted", "why": "ended below its stop",
                           "return_pct": -10.0}, "status": "stopped"}
    assert page._group({"archived": False}, refuted, "bots") == "archive"
    assert page._group({"archived": False}, refuted, "cards") == "done"
    for kept in ("survived", "inconclusive"):
        assert page._group({"archived": False},
                           {"verdict": {"verdict": kept}, "status": "stopped"}, "bots") == "done"
    assert page._reason("archive", refuted) == "ended −10.0%", page._reason("archive", refuted)
    assert page._reason("archive", {"invested": True}) == "not Nexus's pick"
    # 2026-10-03, the operator: "karty jsou uzavreny a prodelaly, verdikt je jasny". A closed
    # room whose own judgement was "can't tell" (too few readings) still has a result, and the
    # result is the verdict: a loss did not work, a gain worked; the reason is what it ended at.
    unsure = {"verdict": {"verdict": "inconclusive", "why": "too few readings"}, "status": "stopped"}
    lost = page._decided({"net_pct": -0.55}, unsure)
    assert lost["verdict"]["verdict"] == "refuted" and lost["verdict"]["return_pct"] == -0.55
    assert page._reason("done", lost).startswith("ended −"), page._reason("done", lost)
    assert page._decided({"net_pct": 3.0}, unsure)["verdict"]["verdict"] == "survived"
    assert page._decided({"net_pct": None}, unsure) is unsure, "no result, so still can't tell"
    assert page._decided({"net_pct": -1.0}, refuted) is refuted, "a judged room keeps its verdict"
    assert page._group({"archived": False}, page._decided({"net_pct": -4.0}, unsure), "bots") == "archive"


def _case_an_experiments_path_is_what_it_is_worth_since_we_went_in():
    """A card's line is its index rebased on the index we bought at, from our
    buy on -- V2's book -- so its last point is our result before costs. A
    bot's line is its booked profit over what went into it."""
    by_id = {e["id"]: e for e in _view()["experiments"]}
    card = by_id["STR-0001"]
    # T05, deep pass 2026-10-04: the leg's entry (99.5) is not a reading of its series (99 before
    # the buy, then 100, 101, 102), so the line is rebased on the index we bought at -- it starts
    # above 0 because the buy-hour reading is already 0.5% over our entry -- and not on the first
    # reading it draws, which would give [0.0, 1.0, 2.0].
    assert [p[1] for p in card["path"]] == [0.503, 1.508, 2.513], card["path"]
    assert card["path"][0][1] != 0.0, "rebased on the first reading, not on the index we bought at"
    assert card["spark"] == card["path"], "short paths are not thinned"
    # 2026-10-03, the operator: every card, old ones too, says what it would have made if sold
    # after 18 hours -- after the round-trip fee, between two readings by their line.
    page = _lab_page()
    line = [["2026-09-22T02:00:00+00:00", 0.0], ["2026-09-22T10:00:00+00:00", 1.0],
            ["2026-09-23T02:00:00+00:00", 3.0]]
    assert page._value_at(line, 18, done=False) == pytest.approx(2.25 - page.CARD_ROUND_TRIP_PCT)
    assert page._value_at(line[:2], 18, done=False) is None, "not 18 hours old yet"
    assert page._value_at(line[:2], 18, done=True) == pytest.approx(1.0 - page.CARD_ROUND_TRIP_PCT), (
        "sold before 18 hours, so its result is what it was sold at")
    assert page._value_at([], 18, done=True) is None and page._value_at(line[:1], 18, done=False) is None
    assert card["at_18h"] is None or isinstance(card["at_18h"], float), card["at_18h"]
    assert (card["tp"], card["sl"]) == (8.0, -5.0)
    assert card["backtest"] == {"pct": 26.2, "period": 90, "sharpe": 2.18,
                                "pass": True}
    # Opened 22. 9. 02:00 with a five-day window; it is 23. 9. 12:00.
    assert card["left_days"] == pytest.approx(3 + 14 / 24, abs=0.01)
    assert card["url"] == "https://cymetica.com/events/c1"
    bot = by_id["STR-0003"]
    assert [p[1] for p in bot["path"]] == [10.0, 3.0]


def _case_a_restarted_bots_line_starts_at_zero_at_its_restart():
    """2026-10-08, the operator on /lab: "co to ma jako byt same nuly?" -- a resumed bot's row read
    0.00% (what it made since its restart, as qa.lab.board counts it) beside a red line drawn from
    its lifetime profit over its first funding (-25 made before the restart). The line is the
    number's own path: from the restart on, what it made since, over what it held then."""
    page = _lab_page()
    t = ["2026-10-07T20:00:00+00:00", "2026-10-07T20:43:54+00:00",
         "2026-10-08T02:00:00+00:00", "2026-10-08T05:00:00+00:00"]
    bot = {"funded": 500.0, "instance": "inst-1",
           "samples": [{"at": t[0], "pnl": -25.0}, {"at": t[1], "pnl": -25.0},
                       {"at": t[2], "pnl": -25.0}, {"at": t[3], "pnl": -5.0}]}
    first_run = page._path({"clones": [dict(bot)]})
    assert [p[1] for p in first_run] == [-5.0, -5.0, -5.0, -1.0], "a first run: lifetime over funding"
    resumed = page._path({"clones": [dict(bot, window={"at": t[1], "profit": -25.0})]})
    assert resumed == [[t[1], 0.0], [t[2], 0.0], [t[3], round(20.0 / 475.0 * 100.0, 3)]], resumed

    # The wiring: a room whose criterion predates the bot's second start gets that start as its
    # window; a room on the bot's first run gets none.
    from qa import lab as qa_lab
    clones = [{"id": "CLN-1", "type": "intent", "kind": "enable", "instance_id": "inst-1",
               "at": "2026-10-01T00:00:00+00:00"},
              {"id": "CLN-1", "type": "outcome", "kind": "enable", "outcome": "accepted",
               "at": "2026-10-01T00:00:00+00:00"},
              {"id": "CLN-2", "type": "intent", "kind": "enable", "instance_id": "inst-1",
               "at": t[1], "bot_profit_usdc": "-25.0"},
              {"id": "CLN-2", "type": "outcome", "kind": "enable", "outcome": "accepted",
               "at": t[1]}]
    later = {"criterion": {"at": "2026-10-07T20:40:00+00:00"}, "clones": [dict(bot)]}
    first = {"criterion": {"at": "2026-09-30T00:00:00+00:00"}, "clones": [dict(bot)]}
    page._bot_windows({"A": later, "B": first}, clones, [], qa_lab)
    assert later["clones"][0]["window"] == {"at": t[1], "profit": -25.0}, later["clones"][0]
    assert first["clones"][0]["window"] is None


def _case_a_long_path_is_thinned_but_keeps_both_ends():
    page = _lab_page()
    points = [[str(i), float(i)] for i in range(1000)]
    thin = page._thin(points, 40)
    assert len(thin) == 40 and thin[0] == points[0] and thin[-1] == points[-1]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_coin_whose_pair_switched_is_not_among_the_biggest_movers(
        tmp_path_factory, monkeypatch):
    """2026-09-23, the first look at the new page: JUP at +569 368 % topped
    the movers -- their terminal answering a different pair for the same
    address (the report we owe them), not a coin that moved. The $10 answer
    already leaves such coins out (qa.fomo.pair_changed); the list of movers
    must not lead with them either."""
    def reading(kind, key, at, age, price, horizon=None):
        row = {"type": kind, "key": key, "at": at, "age_seconds": age,
               "price_usd": price}
        if horizon:
            row["horizon"] = horizon
        return row
    steady = [reading("signal", "0xa:h", "2026-09-22T06:00:00+00:00", 1000.0, 1.0),
              reading("checkpoint", "0xa:h", "2026-09-22T07:00:00+00:00", 4600.0,
                      1.1, "1h")]
    switched = [reading("signal", "0xb:h", "2026-09-22T06:00:00+00:00", 1000.0, 0.28),
                reading("checkpoint", "0xb:h", "2026-09-22T07:00:00+00:00",
                        9_000_000.0, 1437.0, "1h")]
    kept = _lab_page()._pair_clean(steady + switched)
    assert {r["key"] for r in kept} == {"0xa:h"}

    # And its one caller hands the movers only what it kept: the helper alone
    # was tested, so dropping the call from `_fomo_stats` stayed green (deep
    # pass 2026-09-24, B04, 3/3).
    import qa.fomo
    import qa.state
    tmp = tmp_path_factory.mktemp("fomo")
    (tmp / "fomo_signals.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in steady + switched), encoding="utf-8")
    seen = []
    page = _lab_page()
    monkeypatch.setattr(qa.state, "state_dir", lambda: tmp)
    monkeypatch.setattr(qa.fomo, "curves", lambda rows, **kw: seen.extend(rows) or [])
    page._fomo_stats()
    assert {r["key"] for r in seen} == {"0xa:h"}, seen


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_view_carries_the_account_the_nexus_line_and_the_threads():
    view = _view()
    # The account says what is free and what sits in cards -- no "in bots" (it read a dash)
    # and no clock (the operator, 2026-10-03: only what matters).
    assert view["account"] == {"free": 88593.91, "in_cards": 24329.56, "stale": False}
    rooms_view = _rooms_view()
    first = rooms_view["panels"]["STR-0003"]["clones"][0]
    rooms_view["panels"]["STR-0003"]["clones"] = [first, dict(first, balance=100.0)]
    # R04, deep pass of 2026-09-30 (3/3): the room's own money is every bot's
    # too. STR-0046 held four clones funded 477 each; its panel showed 477
    # invested and the first bot's P&L.
    panel = {"trades": [], "staked": 0.0, "clones": [
        {"funded": 477.0, "pnl": 66.96, "balance": 543.96},
        {"funded": 477.0, "pnl": 28.62, "balance": 505.62}]}
    _lab_page()._lay_out(panel, {}, {}, {}, None)
    assert (panel["invested"], panel["pnl"], panel["value"]) == (954.0, 95.58, 1049.58), panel
    panel["clones"][1]["pnl"] = None
    _lab_page()._lay_out(panel, {}, {}, {}, None)
    assert panel["pnl"] is None and panel["pnl_pct"] is None, (
        "a room with one bot's P&L unread showed the other's as the room's")
    # The Nexus line is what came of his ideas and nothing else (the operator, 2026-10-03:
    # no response times, no refusals, no credit): ideas, tested, worked, didn't, running.
    nexus = view["nexus"]
    assert set(nexus) == {"picks", "gate_pass", "gated", "survived", "refuted", "running"}, nexus
    assert nexus["picks"] == 31 and nexus["running"] == 9
    assert "cards" in view["threads"] and "general" in view["threads"]
    # The memecoin top-movers table is gone: "winners by construction" read +114,809,284%.
    assert "movers" not in view and "movers_total" not in view


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_page_reads_every_field_the_view_writes_and_no_other():
    """Both directions, for every name the page gives a shape of the view:
    `lp.` a sector, `le.` an experiment, `ln.` the Nexus line, `la.` the
    account, `lb.` a backtest. A field read and never written draws
    "undefined"; a field written and never read is a figure nobody sees."""
    from qa import lab_report

    view = _view()
    # A sector carries every field the real report writes, not only the ones
    # this test's hand-made report happens to have.
    real = lab_report.report([], [], [], [], [], [], [], now=NOW)["products"]
    # What the report writes that /lab deliberately does not draw (the operator, 2026-10-03:
    # "takove nesmysly nectu"): dollars on stake, wins and the confidence band, the fee
    # variants and the left-out counts. The report keeps them (the morning page and the
    # tests of the report read them); a field NOT on this list and not drawn still fails.
    not_drawn = {"archived", "excluded", "fee_pct", "fees", "min_n", "stake_usdc", "switched",
                 "usdc", "wilson", "wins"}
    written = {
        "lp": ({k for s in view["sectors"] for k in s}
               | {k for p in real.values() for k in p}) - not_drawn,
        "le": {k for e in view["experiments"] for k in e},
        "ln": set(view["nexus"]),
        "la": set(view["account"]),
        "lb": {k for e in view["experiments"] if e["backtest"] for k in e["backtest"]},
    }
    template = _lab_page().TEMPLATE
    for name, keys in written.items():
        read = set(re.findall(rf"\b{name}\.([A-Za-z_][A-Za-z0-9_]*)", template))
        assert read, f"the page reads no `{name}.` field, so this proves nothing"
        assert not read - keys, f"/lab reads `{name}.` fields never written: {sorted(read - keys)}"
        assert not keys - read, f"`{name}.` fields written and never shown: {sorted(keys - read)}"


def _node():
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed, so the page cannot be run here")
    return node


def _drawn(tmp_path, name, after=""):
    code, err, captured = _run_page(_node(), tmp_path / name, _view(),
                                    after=after, page=_lab_page())
    assert code == 0, f"the page throws:\n{err[:1200]}"
    return captured


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_page_opens_on_seven_sections_and_a_ranking_not_on_rooms_per_card(tmp_path):
    captured = _drawn(tmp_path, "open")
    tabs = captured.get("sectors", "")
    for name in ("Our cards", "Nexus cards", "Bots", "Head-to-head", "Memecoins", "Outsider",
                 "Desk"):
        assert name in tabs, f"no {name} section"
    assert "Funds" not in tabs, "a Funds room is back"
    assert tabs.count('data-sector="') == 7, "one tab per section, seven of them"
    # What a section is for is a tooltip on its tab, not a sentence on the page.
    assert tabs.count('title="') >= 7, "a section tab has no tooltip saying what it holds"
    # The page still opens on his cards, the section with results in it.
    assert re.search(r'aria-selected="true"\s+data-sector="cards"', tabs), "it opens elsewhere"
    room = captured.get("room", "")
    assert "Fund we watch" not in room, "a fund room (the fixture holds one) is drawn among the cards"
    assert "Zcash (ZEC) Rally Accelerates" in room, "the running card is not ranked"
    assert "Never bought" not in room, "a failed attempt is in the ranking, not the archive"
    assert "Solana doubles" not in room, "a judged one is mixed into the running ones"
    # Numbers before words: the row's result is there, and nothing on the page
    # speaks the verdict machinery's English (N-0035: "jaké if bought? nějaké
    # inconclusive? kdo se v tom má vyznat?").
    assert "+0.59" in room
    for jargon in ("inconclusive", "if bought", "refuted", "survived"):
        assert jargon not in room.lower(), f"{jargon!r} on the page"
    # Backtest shown by every experiment (N-0035: "asi by měly být v roomu
    # každém zobrazené").
    assert "backtest +26" in room


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_archive_and_the_judged_are_one_click_away_with_their_reason(tmp_path):
    archive = _drawn(tmp_path, "archive",
                     after='window.labShow("cards", "archive");').get("room", "")
    assert "Never bought" not in archive, "a room that bought nothing is listed"
    # T01, deep pass 2026-10-04: the fixture's archive is empty, so this tab fell back to Live
    # and "Never bought" was absent for the wrong reason -- a broken archive tab passed. A room
    # that DID buy and was archived (not his pick) is drawn here, with its reason on the result,
    # and the live room is not.
    rooms_view, report = _rooms_view(), _report()
    rooms_view["rooms"].append({"id": "STR-0008", "kind": "strategy",
                                "title": "Cold fish pick", "status": "stopped"})
    rooms_view["panels"]["STR-0008"] = {**rooms_view["panels"]["STR-0001"], "status": "stopped",
                                        "title": "Cold fish pick", "origin": "NEX-0090"}
    rooms_view["threads"]["STR-0008"] = []
    report["rooms"].append({"id": "STR-0008", "product": "cards", "archived": True,
                            "net_pct": -1.2, "usdc": -6.0, "stake_usdc": 500.0, "verdict": None})
    view = _lab_page().lab_view(rooms_view, report, now=NOW)
    kept = {e["id"]: e for e in view["experiments"]}["STR-0008"]
    assert (kept["group"], kept["reason"]) == ("archive", "not Nexus's pick"), kept
    code, err, captured = _run_page(_node(), tmp_path / "archive-bought", view,
                                    after='window.labShow("cards", "archive");', page=_lab_page())
    assert code == 0, err[:1200]
    bought = captured.get("room", "")
    assert "Cold fish pick" in bought, "the archive tab does not list an archived room that bought"
    assert "not Nexus" in bought, "the archived room does not say why"
    assert "Zcash (ZEC) Rally Accelerates" not in bought, "the archive tab is showing the live room"
    assert "Never bought" not in bought, "a room that bought nothing is listed"
    done =_drawn(tmp_path, "done", after='window.labShow("cards", "done");').get("room", "")
    # No Verdict column (the operator, 2026-10-03: "verdict sloupec je zbytecny"): the result is
    # the verdict, and the reason is on its tooltip.
    assert "Solana doubles" in done and "drawdown 11.8%" in done
    assert "didn't work" not in done and "Verdict" not in done and 'class="st"' not in done


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_experiment_opens_into_a_chart_and_four_numbers(tmp_path):
    room = _drawn(tmp_path, "detail",
                  after='window.labOpen("STR-0001");').get("room", "")
    assert "<svg" in room and "dt-chart" in room, "no chart in the opened experiment"
    for label in ("In<", "Now<", "Result<", "Backtest<"):
        assert label in room, f"the opened experiment has no {label}"
    assert "cymetica.com/events/c1" in room, "no way to the card itself"
    # P2: what the section knows sits folded under its numbers -- numbers first, the lines one
    # click away -- in the card rooms, the bot rooms and the memecoins alike.
    view = _lab_page().lab_view(_rooms_view(), _report(), now=NOW, known={
        "cards": ["his cards fade after a day"], "memecoins": ["hot is a lift, not a profit"]})
    for sector, line in (("cards", "his cards fade after a day"),
                         ("memecoins", "hot is a lift, not a profit")):
        code, err, captured = _run_page(_node(), tmp_path / f"known-{sector}", view,
                                        after=f'window.labShow("{sector}");', page=_lab_page())
        assert code == 0, err[:1200]
        drawn = captured.get("room", "")
        assert "<details" in drawn and "What we know" in drawn and line in drawn, drawn[:600]
        assert drawn.index("What we know") > drawn.index("hero"), "the lines came before the numbers"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_room_of_ours_says_ours_and_never_ranks_above_his(tmp_path):
    """V5, the own lane: a paper bot's next setting is OUR idea (origin
    OUR-...). The page says so -- "ours", not "idea OUR-0001" -- and ranks
    it after his, whatever it earned."""
    rooms_view, report = _rooms_view(), _report()
    # Ranking is within a tab: both rooms must be live, so his bot still trades.
    rooms_view["panels"]["STR-0003"]["clones"][0].update(trading=True, stop=None)
    rooms_view["rooms"].append({"id": "STR-0006", "kind": "strategy",
                                "title": "Bollinger Bandit · SL 5",
                                "origin": "OUR-0001", "status": "running"})
    rooms_view["panels"]["STR-0006"] = {
        **rooms_view["panels"]["STR-0003"], "title": "Bollinger Bandit · SL 5",
        "origin": "OUR-0001", "status": "running", "clones": []}
    report["rooms"].append({**next(r for r in report["rooms"]
                                   if r["id"] == "STR-0003"),
                            "id": "STR-0006", "origin": "OUR-0001",
                            "net_pct": 99.0, "usdc": 99.0})
    view = _lab_page().lab_view(rooms_view, report, now=NOW)
    by_id = {e["id"]: e for e in view["experiments"]}
    assert by_id["STR-0006"]["ours"] is True and by_id["STR-0003"]["ours"] is False

    code, err, captured = _run_page(_node(), tmp_path / "ours", view,
                                    after='window.labShow("bots");',
                                    page=_lab_page())
    assert code == 0, err[:1200]
    room = captured.get("room", "")
    assert ">ours<" in room, room[:2000]
    assert room.index("Bollinger Bandit · SL 5") > room.index("Bollinger Bandit"), (
        "a room of ours ranked above his pick")

    # T03, deep pass 2026-10-04: only the default order was run. With a column sort stored
    # (the operator clicked "Result" or "Profit"), ours at +99% ranked above his: the lane was
    # applied by the default comparator alone. The stored order still holds inside each lane.
    rooms_view["rooms"].append({"id": "STR-0007", "kind": "strategy", "title": "Alpha Bot",
                                "origin": "NEX-0081", "status": "running"})
    rooms_view["panels"]["STR-0007"] = {
        **rooms_view["panels"]["STR-0003"], "title": "Alpha Bot", "origin": "NEX-0081",
        "status": "running",
        "clones": [dict(c) for c in rooms_view["panels"]["STR-0003"]["clones"]]}
    report["rooms"].append({**next(r for r in report["rooms"] if r["id"] == "STR-0003"),
                            "id": "STR-0007", "origin": "NEX-0081", "net_pct": 1.0, "usdc": 2.4})
    view = _lab_page().lab_view(rooms_view, report, now=NOW)
    for stored, expected in (
            ("net:desc", ["STR-0003", "STR-0007", "STR-0006"]),
            ("net:asc", ["STR-0007", "STR-0003", "STR-0006"]),
            ("usd:desc", ["STR-0003", "STR-0007", "STR-0006"]),
            ("name:asc", ["STR-0007", "STR-0003", "STR-0006"])):
        code, err, captured = _run_page(
            _node(), tmp_path / f"ours-{stored.replace(':', '-')}", view,
            after=f'localStorage.setItem("lab.sort.bots", "{stored}");window.labShow("bots");',
            page=_lab_page())
        assert code == 0, err[:1200]
        sorted_room = captured.get("room", "")
        order = [sorted_room.index(f'data-id="{rid}"') for rid in expected]
        assert order == sorted(order), (
            f"with the sort {stored} stored, the rows are not {expected}: "
            + str({rid: sorted_room.find(f'data-id="{rid}"') for rid in expected}))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_bots_room_says_whether_each_bot_trades(tmp_path):
    room = _drawn(tmp_path, "bots", after='window.labShow("bots");').get("room", "")
    # A bot that stopped by itself says so once -- its reason -- rather than
    # "idle" and the reason side by side.
    assert "Bollinger Bandit" in room and "stopped by itself at +3%" in room
    assert ">idle<" not in room

    # And the other two answers, which the fixture never drew (deep pass
    # 2026-09-25, C08): a bot that trades says "trading", one that does not
    # and has no reason says "idle".
    # Deep pass 2026-09-28, A02 (3/3): the word is DERIVED from the room's
    # clones, so each case sets them and lets `lab_view` derive it -- writing
    # `e["trading"]` straight into the view skipped exactly that step, and a
    # batch room whose last clone had stopped drew "idle" over bots trading.
    one = {"funded": 240.0, "trading": True, "stop": None}
    two = {"funded": 240.0, "trading": False, "stop": None}
    for name, trading, clones, word in (
            ("on", True, [one], ">trading<"), ("off", False, [two], ">idle<"),
            ("batch-last-stopped", True, [one, two], ">trading<"),
            ("batch-first-stopped", True, [two, one], ">trading<")):
        rooms_view = _rooms_view()
        rooms_view["panels"]["STR-0003"]["clones"] = clones
        view = _lab_page().lab_view(rooms_view, _report(), now=NOW)
        bot = next(e for e in view["experiments"] if e["id"] == "STR-0003")
        assert (bot["group"], bot["trading"], bot["reason"]) == ("live", trading, None), bot
        code, err, captured = _run_page(_node(), tmp_path / f"bots-{name}", view,
                                        after='window.labShow("bots");',
                                        page=_lab_page())
        assert code == 0, err[:1200]
        assert word in captured.get("room", ""), (word, captured.get("room", "")[:1500])


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_chat_is_behind_a_button_and_nexus_text_stays_text(tmp_path):
    """The operator: the chat with Nexus is not important, they may glance at
    it out of curiosity. So it is closed until asked for, and what Nexus
    wrote reaches it escaped first, with a small markdown subset after."""
    view = _view()
    hostile = '<script>alert(1)</script><img src=x onerror=alert(2)> **bold** and `code`'
    view["threads"]["general"] = [
        {"kind": "question", "id": "NEX-9", "at": "2026-09-20T01:00:00+00:00",
         "text": "what now?"},
        {"kind": "reply", "id": "NEX-9", "at": "2026-09-20T01:02:00+00:00",
         "text": hostile, "outcome": "answered", "seconds": 120.0}]
    template = _lab_page().TEMPLATE
    assert re.search(r'<aside[^>]*id="drawer"[^>]*\bhidden\b', template), (
        "the conversation is open on arrival; it belongs behind its button")
    code, err, captured = _run_page(_node(), tmp_path / "chat", view,
                                    after='window.labChat("general");',
                                    page=_lab_page())
    assert code == 0, err[:900]
    thread = captured.get("thread", "")
    assert "what now?" in thread
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in thread
    assert "<script" not in thread.lower() and "<img" not in thread.lower()
    assert "<b>bold</b>" in thread and "<code>code</code>" in thread


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_sector_chat_holds_its_own_note_and_the_composer_sits_under_it(tmp_path):
    """The first thing the operator said about the old tab, 2026-09-11: the
    box they write in covered the end of the conversation. In the drawer the
    thread scrolls on its own and the composer is the next thing under it,
    never floated over it."""
    captured = _drawn(tmp_path, "sector-chat", after='window.labChat("cards");')
    assert "hm" in captured.get("thread", ""), "the Cards room's own note is missing"
    template = _lab_page().TEMPLATE
    assert (template.index('id="thread"') < template.index('id="compose"')), (
        "the composer is above the thread")
    for selector, body in re.findall(r"([^{}]*(?:\.compose|#compose)[^{}]*)\{([^}]*)\}",
                                     template):
        assert not re.search(r"position\s*:\s*(sticky|fixed|absolute)", body), (
            f"{selector.strip()} floats the composer: {body}")
    threads = [body for selector, body in re.findall(r"([^{}]*)\{([^}]*)\}", template)
               if selector.strip() == ".thread"]
    assert threads and re.search(r"overflow-y\s*:\s*auto", threads[0]), (
        "the thread does not scroll on its own")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_memecoin_room_keeps_the_operators_own_decisions(tmp_path):
    """The answer is V3's ($10 into every hot signal, after costs). Of the list that sat
    under it (the operator, 2026-09-13/14: one list, a graph column, price columns gone) only
    what is a result is left, since 2026-10-03: the headline, how much could have been bought,
    the conviction >= 70 figure they asked for and the typical trade -- no table, no graph
    column, no top movers, no left-out paragraph, no "winners by construction" note. The
    hover bubble is our own coloured one rather than the browser's grey title."""
    room = _drawn(tmp_path, "memes", after='window.labShow("memecoins");').get("room", "")
    assert "−19.8" in room, "the $10 answer is not the headline"
    # 2026-10-03, the operator: "takove nesmysly nectu a nezajimaji me ... kompletni refinement
    # laborky ať nikde není žádné smetí". The room is the result, how much could have been
    # bought, the high-conviction figure and the typical trade. The top-movers table
    # (+114,809,284%), the fee variants, the left-out paragraph and the confidence band are off.
    assert "<table" not in room and "Top movers" not in room, "the movers table is back"
    assert "winners by construction" not in room and "Left out" not in room
    assert "Other fee" not in room and "95% sure" not in room
    assert "Could have bought" in room
    # T04, deep pass 2026-10-04: the label alone was held, so a missing or mis-scaled share still
    # passed. The report's 0.52 is the tile's 52%, on its meter, under the signal count.
    could = room[room.index("Could have bought"):][:400]
    assert "<b>52%</b>" in could and "width:52%" in could, could
    assert "of2705signals" in re.sub(r"[,\s  ]", "", could), could
    assert "Conviction ≥ 70" in room and "−12" in room
    # 2026-10-13: the conviction tile read +6 003 % and nothing under it; its median (-100 %)
    # would have said one coin made the figure. Its own median, not the room's (-40).
    conviction = room[room.index("Conviction ≥ 70"):][:400]
    assert "median" in conviction and "−55" in conviction, conviction
    # M03, deep pass of 2026-09-13: the figure under the word median must be
    # the median (-40) and not the mean (-19.8).
    typical = room[room.index("Typical trade"):][:300]
    assert "−40" in typical and "−19.8" not in typical, typical
    template = _lab_page().TEMPLATE
    assert 'id="tip"' in template and "mousemove" in template, "no bubble"
    # The console's hover card is the same kind of bubble: held beside this one, not in a test of
    # its own (tests/meta is held to a ceiling).
    _check_the_consoles_hover_card_sits_clear_of_its_bars()


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_memecoin_room_with_nothing_measured_yet_says_so(tmp_path):
    """Never watched and watched-with-nothing-yet must not look like a room
    that is broken: it says there is nothing yet."""
    view = _view()
    next(s for s in view["sectors"] if s["key"] == "memecoins")["n"] = 0
    code, err, captured = _run_page(_node(), tmp_path / "nomemes", view,
                                    after='window.labShow("memecoins");',
                                    page=_lab_page())
    assert code == 0, err[:900]
    assert "No signal has had" in captured.get("room", "")


def _check_the_consoles_hover_card_sits_clear_of_its_bars():
    """R12, deep pass 2026-10-04: the card was placed at `Math.max(0, -height - 6)`, which is 0
    for every height, so it sat on top of the bars it describes. It goes above the chart when
    the window has room there (a negative `top` inside the chart's box) and below it when not;
    never at 0. The placement is a function of three numbers, run here as the console ships it."""
    import subprocess

    from tests.meta.test_pipeline_render import _render

    template = _render().TEMPLATE
    assert "Math.max(0, -tip.offsetHeight" not in template, "the always-zero clamp is back"
    found = re.search(r"function tipTop\([^)]*\)\s*\{.*?\n  \}", template, re.S)
    assert found, "the hover card's placement is not a function of its own, so it cannot be held"
    probe = found.group(0) + "\nconsole.log(JSON.stringify([tipTop(300, 40, 70), tipTop(20, 40, 70)]));"
    result = subprocess.run([_node(), "-e", probe], capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=30)
    assert result.returncode == 0, result.stderr[:600]
    above, below = json.loads(result.stdout)
    assert above < 0 and above <= -70, f"with room above, the card is not above the bars: {above}"
    assert below >= 40, f"with no room above, the card is not below the bars: {below}"


def _bot_room(*clones):
    """STR-0003 holding these clones, drawn through lab_view."""
    rooms = _rooms_view()
    rooms["panels"]["STR-0003"]["clones"] = [
        {"funded": 240.0, "balance": 240.0, "samples": [], **c} for c in clones]
    view = _lab_page().lab_view(rooms, _report(), now=NOW)
    return {e["id"]: e for e in view["experiments"]}["STR-0003"]


def _check_a_bot_that_stopped_itself_is_done_and_says_which_limit_it_hit():
    """2026-09-26: the Live tab held eight bots that no longer traded, three of
    them in profit. Cymetica's answer to MSG-0060: the platform pauses a paper
    bot at its own stop-loss or take-profit. A stopped bot's result cannot
    change, so it is done, and its reason is the limit and the result."""
    # A stop in profit that bot_stops calls "unexplained" is not named a
    # take-profit: their own answer (a2a_42be5226, 2026-09-25) lists self-stops
    # that fire in profit for other reasons (deep pass 2026-09-27, R08, 2/3).
    take = _bot_room({"trading": False, "stop": {"cause": "unexplained", "pct": 29.0}})
    assert (take["group"], take["reason"]) == ("done", "stopped by itself at +29%")
    assert take["left_days"] is None, "no days left on a test that is over"
    loss = _bot_room({"trading": False, "stop": {"cause": "their_guard", "pct": -10.0}})
    assert (loss["group"], loss["reason"]) == ("done", "stop-loss −10%")
    assert _bot_room({"trading": False, "stop": {"cause": "their_guard",
                                                 "pct": -19.19}})["reason"] == "stop-loss −19.2%"
    flat = _bot_room({"trading": False, "stop": {"cause": "unexplained", "pct": None}})
    assert (flat["group"], flat["reason"]) == ("done", "stopped by itself")
    # Deep pass 2026-10-08 (R03): a band is named by the reason the platform gave, never by
    # the sign of the bot's lifetime profit -- 3b1512cb stopped at its stop-loss at +23.25%
    # and the page would have said "take-profit".
    sl_up = _bot_room({"trading": False, "stop": {"cause": "their_trigger", "pct": 23.26,
                                                  "reason": "stop_loss"}})
    assert sl_up["reason"] == "stop-loss +23.3%", sl_up["reason"]
    tp_flat = _bot_room({"trading": False, "stop": {"cause": "their_trigger", "pct": None,
                                                    "reason": "take_profit"}})
    assert tp_flat["reason"] == "take-profit", tp_flat["reason"]
    ran = _bot_room({"trading": False, "stop": {"cause": "their_trigger", "pct": 23.26,
                                                "reason": "stop_loss"},
                     "runs": [{"start": "2026-10-07T04:00:00+00:00",
                               "end": "2026-10-07T18:22:00+00:00", "why": "their_trigger",
                               "reason": "stop_loss", "profit_pct": 23.26}]})["ran"]
    assert ran["why"] == "its stop-loss +23.3%", ran


def _check_the_row_says_how_long_each_bot_ran_and_why_it_stopped():
    """2026-10-03, the operator: "u botu chci videt delku jakou behlli, kdy je nekdo
    spustil, kdy se vypli a delku zivota, a kdyz se vypli tak duvod"."""
    gone = {"start": "2026-09-22T13:38:30+00:00", "end": "2026-09-22T20:00:00+00:00",
            "why": "their_guard", "profit_pct": -10.0}
    one = _bot_room({"trading": False, "stop": {"cause": "their_guard", "pct": -10.0},
                     "runs": [gone]})["ran"]
    assert (one["start"], one["end"], one["running"], one["n"]) == (
        gone["start"], gone["end"], False, 1), one
    assert one["seconds"] == 6 * 3600 + 21 * 60 + 30, one
    assert one["why"] == "their stop-loss −10%", one
    ours = _bot_room({"trading": False, "stop": {"cause": "ours", "pct": 0.0},
                      "runs": [dict(gone, why="ours", profit_pct=None)]})["ran"]
    assert ours["why"] == "paused by us", ours
    free = _bot_room({"trading": False, "stop": {"cause": "unexplained", "pct": 3.0},
                      "runs": [dict(gone, why="unexplained", profit_pct=3.0)]})["ran"]
    assert free["why"] == "stopped by itself at +3%", free
    going = _bot_room({"trading": True, "stop": None, "runs": [
        {"start": "2026-09-23T00:00:00+00:00", "end": None, "why": None,
         "profit_pct": None}]})["ran"]
    assert (going["running"], going["end"], going["why"]) == (True, None, None), going
    assert going["seconds"] == (NOW - datetime.fromisoformat("2026-09-23T00:00:00+00:00")
                                ).total_seconds(), going
    batch = _bot_room({"trading": False, "stop": {"cause": "their_guard", "pct": -9.0},
                       "runs": [gone]},
                      {"trading": False, "stop": {"cause": "their_guard", "pct": -10.0},
                       "runs": [dict(gone, end="2026-09-22T14:00:00+00:00")]})["ran"]
    assert (batch["n"], batch["why"], batch["seconds"]) == (2, "all 2 stopped", one["seconds"]), batch
    assert _bot_room({"trading": False, "stop": None})["ran"] is None, "a bot never switched on"


def _check_a_bot_still_trading_or_paused_by_us_or_never_started_stays_live():
    """Only a stop that was not ours ends the test. A bot we paused is ours to
    resume; one never switched on has no stop; one trading has none yet."""
    for clone in ({"trading": True, "stop": None},
                  {"trading": False, "stop": None},
                  {"trading": False, "stop": {"cause": "ours", "pct": 0.0}}):
        room = _bot_room(clone)
        assert room["group"] == "live", clone
        assert room["reason"] is None, (clone, room["reason"])


def _check_a_batch_room_is_done_only_when_every_bot_in_it_has_stopped():
    """Head-to-head bots, batch 1 holds several clones: one that stopped
    while the others trade does not end the room."""
    stopped = {"trading": False, "stop": {"cause": "unexplained", "pct": 9.0}}
    running = {"trading": True, "stop": None}
    assert _bot_room(stopped, running)["group"] == "live"
    room = _bot_room(stopped, {"trading": False,
                               "stop": {"cause": "their_guard", "pct": -10.0}})
    assert (room["group"], room["reason"]) == ("done", "all 2 stopped")


def _check_the_stop_a_clone_carries_is_the_diaries_and_only_while_it_is_stopped():
    """`stop` on a clone is what qa.lab.bot_stops finds, and only while the
    bot's newest reading says it is not trading: a stop followed by a
    restart is not a stop."""
    page = _lab_page()
    rows = [{"id": "CLN-1", "type": "intent", "kind": "fund", "instance_id": "i1",
             "at": "2026-09-24T18:00:00+00:00", "amount": 100.0},
            {"id": "CLN-1", "type": "outcome", "outcome": "accepted",
             "at": "2026-09-24T18:00:01+00:00"},
            {"id": "CLN-2", "type": "intent", "kind": "enable", "instance_id": "i1",
             "at": "2026-09-24T18:01:00+00:00"},
            {"id": "CLN-2", "type": "outcome", "outcome": "accepted",
             "at": "2026-09-24T18:01:01+00:00"}]
    samples = [{"type": "sample", "kind": "bot", "instance_id": "i1",
                "at": "2026-09-24T19:00:00+00:00", "is_trading": False,
                "total_profit_usdc": 29.0}]
    stop = page._current_stop("i1", rows, samples, trading=False)
    assert stop["cause"] == "unexplained" and stop["pct"] == pytest.approx(29.0)
    banded = [dict(samples[0], auto_pause_reason="stop_loss")]
    assert page._current_stop("i1", rows, banded, trading=False)["reason"] == "stop_loss", (
        "the band's reason reaches the page with the stop")
    assert page._current_stop("i1", rows, samples, trading=True) is None
    assert page._current_stop("other", rows, samples, trading=False) is None


# Folded on the deep pass of 2026-10-04 (tests/meta grows only by replacement): two functions became one.


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_experiments_path_is_rebased_on_the_index_we_bought_at_and_a_long_one_keeps_both_ends():
    _case_an_experiments_path_is_what_it_is_worth_since_we_went_in()
    _case_a_long_path_is_thinned_but_keeps_both_ends()
    _case_a_restarted_bots_line_starts_at_zero_at_its_restart()

"""The casino department's comparisons (qa/casino.py), on the numbers its first tables really showed.

[operator 2026-11-01] asked for this to run until the live tables open: paper bots at paper tables,
the NEXUS coach watched, the logs checked, bugs filed. Every fixture below is a real reading: table 40
(a hidden fill), table 42 (a table that agrees), table 44 (a seat that opens on an earlier table's
numbers), the seats 120-123 asked on 2026-10-28 and still `pending`.
"""

from __future__ import annotations

from datetime import datetime, timezone

from qa import casino
from qa.marks import SafetyTier, qa


def keys(found: list[dict]) -> list[str]:
    return sorted(f["key"] for f in found)


def done_table(**over) -> dict:
    """Table 42 as it ended, 2026-11-01 09:11 UTC, with RSI Sniper as our seat."""
    table = {
        "id": 42, "status": "done", "mode": "paper", "hours": 1, "buyin_usdc": 5.0, "capital_usdc": 25.0,
        "paid_seats": 3, "pot_usdc": 15.0, "ends_at": "2026-11-01T09:11:08+00:00",
        "my_seat": {"seat_id": 154, "bot": "casino RSI Sniper"},
        "results": {"pot_usdc": 15.0, "ranked": [
            {"seat_id": 156, "rank": 1, "house": False, "trades": 0, "roi_pct": 0.0, "pnl_usdc": 0.0,
             "volume_usdc": 0.0, "qualified": False, "prize_usdc": 0.0, "prize_et10": 0},
            {"seat_id": 155, "rank": 2, "house": False, "trades": 6, "roi_pct": -1.0218, "pnl_usdc": -0.26,
             "volume_usdc": 8.24, "qualified": True, "prize_usdc": 10.0, "prize_et10": 3},
            {"seat_id": 154, "rank": 3, "house": False, "trades": 5, "roi_pct": -11.65, "pnl_usdc": -2.91,
             "volume_usdc": 8.16, "qualified": True, "prize_usdc": 5.0, "prize_et10": 1},
            {"seat_id": 160, "rank": 4, "house": True, "trades": 2, "roi_pct": -13.51, "pnl_usdc": -3.38,
             "volume_usdc": 3.37, "qualified": True, "prize_usdc": 0.0, "prize_et10": 0}]},
        "your_trades": [
            {"symbol": "ETH", "side": "buy", "amount_usdc": 1.16, "pnl_usdc": -1.16, "closed": True,
             "at": "2026-11-01T09:00:20+00:00"},
            {"symbol": "ETH", "side": "buy", "amount_usdc": 1.36, "pnl_usdc": -1.36, "closed": True,
             "at": "2026-11-01T08:36:14+00:00"},
            {"symbol": "BTC", "side": "buy", "amount_usdc": 2.14, "pnl_usdc": -2.14, "closed": True,
             "at": "2026-11-01T08:35:37+00:00"},
            {"symbol": "BTC", "side": "buy", "amount_usdc": 1.75, "pnl_usdc": 1.75, "closed": True,
             "at": "2026-11-01T08:30:22+00:00"},
            {"symbol": "BTC", "side": "buy", "amount_usdc": 1.75, "pnl_usdc": 0.0, "closed": True,
             "at": "2026-11-01T08:25:19+00:00"}],
        "my_tune_log": [], "changes": [], "picks": {"open": False, "closes_in_s": 0, "my_pick": None},
        "et10_paid": []}
    table.update(over)
    return table


def running_table(**over) -> dict:
    """Table 44 a minute after it started, 2026-11-01 10:06 UTC."""
    table = {
        "id": 44, "status": "running", "mode": "paper", "hours": 1, "ends_in_s": 3592,
        "my_seat": {"seat_id": 166, "bot": "casino RSI Sniper"},
        "standings": [{"seat_id": 166, "bot_state": "trading", "bot_state_label": "Trading",
                       "daily_allowance": 20, "trades_today": 5, "allowance_used_up": False}],
        "my_risk": {"level": 8, "trade_size_pct": 8.0, "stop_loss_pct": 4.0, "take_profit_pct": 32.0},
        "my_coach": {"on": True, "allowed": True},
        "my_coach_line": {"line": "Last check 10:06 UTC: no change · no closed trade since; rank 1",
                          "risk_line": "Risk reads 8: size 8 %, stop loss 4 %, take profit 32 %, as you set it."},
        "my_bot_settings": {"stop_loss_pct": 4.0, "take_profit_pct": 32.0, "trade_size_pct": 8.0},
        "my_tune_log": [], "changes": [], "your_trades": [],
        "picks": {"open": True, "closes_in_s": 86391, "my_pick": None}}
    table.update(over)
    return table


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_finished_table_whose_list_hides_a_fill_is_named():
    """Table 40: 4 trades, $24.85, -$5.64 in the standings; 3, $22.87, -$7.62 in the list (#234)."""
    table = done_table(
        id=40, paid_seats=1, pot_usdc=5.0, my_seat={"seat_id": 143, "bot": "casino Trend Titan"},
        results={"pot_usdc": 5.0, "ranked": [
            {"seat_id": 143, "rank": 1, "house": False, "trades": 4, "roi_pct": -22.5816, "pnl_usdc": -5.64,
             "volume_usdc": 24.85, "qualified": True, "prize_usdc": 5.0, "prize_et10": 3}]},
        your_trades=[
            {"symbol": "BTC", "amount_usdc": 3.37851, "pnl_usdc": -3.37851, "closed": True, "at": "2026-10-31T23:05:58+00:00"},
            {"symbol": "BTC", "amount_usdc": 11.86989, "pnl_usdc": -11.86989, "closed": True, "at": "2026-10-31T22:45:34+00:00"},
            {"symbol": "BTC", "amount_usdc": 7.6242, "pnl_usdc": 7.6242, "closed": True, "at": "2026-10-31T22:40:39+00:00"}])
    assert "standings_vs_trades" in keys(casino.contradictions(table))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_finished_table_that_agrees_says_nothing():
    """Table 42 agrees (5 trades, $8.16, -$2.91), sums to its pot and is in ROI order."""
    assert casino.contradictions(done_table()) == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_seat_that_is_not_ours_is_not_compared():
    assert "standings_vs_trades" not in keys(casino.contradictions(done_table(my_seat=None, your_trades=[])))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_accounts_of_a_finished_table_must_close():
    table = done_table()
    table["results"]["ranked"][1]["prize_usdc"] = 11.0
    assert "prizes_vs_pot" in keys(casino.contradictions(table))

    table = done_table()
    table["results"]["ranked"][2]["roi_pct"] = -20.0
    found = keys(casino.contradictions(table))
    assert "roi_vs_pnl" in found

    table = done_table()
    table["results"]["ranked"][0], table["results"]["ranked"][1] = (table["results"]["ranked"][1],
                                                                    table["results"]["ranked"][0])
    table["results"]["ranked"][0]["rank"], table["results"]["ranked"][1]["rank"] = 1, 2
    assert "rank_vs_roi" in keys(casino.contradictions(table))

    assert "pot_vs_paid_seats" in keys(casino.contradictions(done_table(paid_seats=2)))

    table = done_table()
    table["results"]["ranked"][3]["prize_usdc"] = 1.0
    table["results"]["ranked"][1]["prize_usdc"] = 9.0
    assert "house_paid" in keys(casino.contradictions(table))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_tune_must_be_in_the_public_feed_and_a_feed_row_in_the_log():
    tune = {"at": "2026-11-01T08:42:39+00:00", "kind": "TUNED", "by": "NEXUS",
            "text": "stop loss 7 → 5 % · rank 1 → 2"}
    row = {"seat_id": 154, "what": ["stop loss"], "by": "NEXUS", "at": "2026-11-01T08:42:40+00:00"}
    agrees = done_table(my_tune_log=[tune], changes=[row])
    assert "tune_vs_feed" not in keys(casino.contradictions(agrees))
    assert "tune_vs_feed" in keys(casino.contradictions(done_table(my_tune_log=[tune], changes=[])))
    assert "tune_vs_feed" in keys(casino.contradictions(done_table(my_tune_log=[], changes=[row])))
    # Another seat's row and a CHECKED row are nobody's contradiction.
    other = {**row, "seat_id": 155}
    checked = {**tune, "kind": "CHECKED", "text": "no change · rank 1"}
    assert "tune_vs_feed" not in keys(casino.contradictions(done_table(my_tune_log=[checked], changes=[other])))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_tune_must_be_what_the_settings_now_say():
    tune = {"at": "2026-11-01T10:20:00+00:00", "kind": "TUNED", "by": "NEXUS", "text": "stop loss 4 → 3 % · rank 1 → 2"}
    feed = [{"seat_id": 166, "what": ["stop loss"], "by": "NEXUS", "at": "2026-11-01T10:20:01+00:00"}]
    risk = {"level": 8, "trade_size_pct": 8.0, "stop_loss_pct": 3.0, "take_profit_pct": 32.0}
    settings = {"stop_loss_pct": 3.0, "take_profit_pct": 32.0, "trade_size_pct": 8.0}
    agrees = running_table(my_tune_log=[tune], changes=feed, my_risk=risk, my_bot_settings=settings)
    assert "tune_vs_settings" not in keys(casino.contradictions(agrees))
    stale = running_table(my_tune_log=[tune], changes=feed, my_risk=risk,
                          my_bot_settings={**settings, "stop_loss_pct": 4.0})
    assert "tune_vs_settings" in keys(casino.contradictions(stale))
    # An owner's later change moves the numbers on purpose.
    owner = {"seat_id": 166, "what": ["stop loss"], "by": "OWNER", "at": "2026-11-01T10:30:00+00:00"}
    moved = running_table(my_tune_log=[tune], changes=[*feed, owner], my_risk=risk,
                          my_bot_settings={**settings, "stop_loss_pct": 9.0})
    assert "tune_vs_settings" not in keys(casino.contradictions(moved))
    # Two tunes that do not chain: the second starts from a number the first did not leave.
    first = {**tune, "at": "2026-11-01T10:10:00+00:00", "text": "stop loss 8 → 7 % · rank 1 → 2"}
    broken = running_table(my_tune_log=[tune, first], changes=feed, my_risk=risk, my_bot_settings=settings)
    assert "tune_vs_settings" in keys(casino.contradictions(broken))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_reason_a_tune_gives_must_be_in_the_trades():
    """Table 42, 08:42: "2 losses in a row on ETH/BTC: -3.50 USDC" was true (-1.36 and -2.14)."""
    true = {"at": "2026-11-01T08:42:39+00:00", "kind": "TUNED", "by": "NEXUS",
            "text": "PERP BTC off · stop loss 7 → 5 % · 2 losses in a row on ETH/BTC: -3.50 USDC"}
    feed = [{"seat_id": 154, "what": ["markets", "stop loss"], "by": "NEXUS", "at": "2026-11-01T08:42:40+00:00"}]
    assert "tune_reason" not in keys(casino.contradictions(done_table(my_tune_log=[true], changes=feed)))
    wrong_sum = {**true, "text": "PERP BTC off · 2 losses in a row on ETH/BTC: -9.99 USDC"}
    assert "tune_reason" in keys(casino.contradictions(done_table(my_tune_log=[wrong_sum], changes=feed)))
    early = {**true, "at": "2026-11-01T08:36:00+00:00"}  # only one of the two had closed by then
    assert "tune_reason" in keys(casino.contradictions(done_table(my_tune_log=[early], changes=feed)))

    none_yet = {"at": "2026-11-01T08:26:00+00:00", "kind": "TUNED", "by": "NEXUS",
                "text": "CLOB ETH/USDC on · no trade for 14 min (none yet)"}
    feed2 = [{"seat_id": 154, "what": ["markets"], "by": "NEXUS", "at": "2026-11-01T08:26:01+00:00"}]
    # A trade had closed at 08:25:19, so "none yet" was false.
    assert "tune_reason" in keys(casino.contradictions(done_table(my_tune_log=[none_yet], changes=feed2)))
    clean = {**none_yet, "at": "2026-11-01T08:20:00+00:00"}
    assert "tune_reason" not in keys(casino.contradictions(done_table(my_tune_log=[clean], changes=feed2)))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_trade_closed_after_the_tune_does_not_make_the_reason_false():
    """`your_trades[].at` is when a round OPENED (table 51 at 10:39: `at` 10:35:59, still open); only the
    bot's activity feed has `closed_at`. Table 35: opened 10:32:13, closed 10:36:29."""
    trades = [{"symbol": "ETH", "amount_usdc": 10.0, "pnl_usdc": -10.0, "closed": True, "at": "2026-11-01T10:32:13+00:00"}]
    items = [{"symbol": "ETH", "amount_usdc": "10.000000", "closed_at": "2026-11-01T10:36:29+00:00"},
             {"symbol": "ETH", "amount_usdc": "11.875000", "closed_at": "2026-11-01T10:21:08+00:00"}]
    merged = casino.with_close_times(trades, items)
    assert merged[0]["closed_at"] == "2026-11-01T10:36:29+00:00"
    assert casino.with_close_times(trades, [])[0].get("closed_at") is None

    none_yet = {"at": "2026-11-01T10:34:00+00:00", "kind": "TUNED", "by": "NEXUS",
                "text": "CLOB ETH/USDC on · no trade for 14 min (none yet)"}
    feed = [{"seat_id": 154, "what": ["markets"], "by": "NEXUS", "at": "2026-11-01T10:34:01+00:00"}]
    opened = done_table(my_tune_log=[none_yet], changes=feed, your_trades=merged)
    assert "tune_reason" not in keys(casino.contradictions(opened))
    assert "coach_rule_vs_tunes" in keys(casino.contradictions(opened, five_rule=True))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_risk_line_must_be_on_its_level():
    """Table 44: "Risk reads 8 ... stop loss 4 % ... as you set it": the owner set 8, the coach 4, at
    another table. Their /risk route: trade size L %, stop loss L %, take profit 4 x L %, at least 5 %."""
    assert "risk_line_off_level" in keys(casino.contradictions(running_table()))
    on_line = running_table(
        my_risk={"level": 8, "trade_size_pct": 8.0, "stop_loss_pct": 8.0, "take_profit_pct": 32.0},
        my_bot_settings={"stop_loss_pct": 8.0, "take_profit_pct": 32.0, "trade_size_pct": 8.0},
        my_coach_line={"line": "x", "risk_line": "Risk reads 8: size 8 %, stop loss 8 %, take profit 32 %, as you set it."})
    assert "risk_line_off_level" not in keys(casino.contradictions(on_line))
    start = running_table(
        my_risk={"level": 5, "trade_size_pct": 5.0, "stop_loss_pct": 2.5, "take_profit_pct": 20.0},
        my_bot_settings={"stop_loss_pct": 2.5, "take_profit_pct": 20.0, "trade_size_pct": 5.0},
        my_coach_line={"line": "x", "risk_line": "Risk reads 5 (the middle, where a bot starts): size 5 %, stop loss 2.5 %, take profit 20 %."})
    assert "risk_line_off_level" in keys(casino.contradictions(start))
    # A line that does not claim the level is not held to it: the coach moved the number and says so.
    said = running_table(my_coach_line={"line": "x", "risk_line": "Risk reads 8; the coach moved stop loss to 4 %."})
    assert "risk_line_off_level" not in keys(casino.contradictions(said))
    assert casino.level_numbers(1) == (1.0, 1.0, 5.0)
    assert casino.level_numbers(10) == (10.0, 10.0, 40.0)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_bot_with_no_allowance_left_cannot_read_as_trading():
    """Table 41: 20/20 today with the table ending hours before 00:00 UTC, and the state said Trading."""
    spent = running_table(standings=[{"seat_id": 166, "bot_state": "trading", "bot_state_label": "Trading",
                                      "daily_allowance": 20, "trades_today": 20, "allowance_used_up": True}])
    assert "allowance_vs_state" in keys(casino.contradictions(spent))
    said = running_table(standings=[{"seat_id": 166, "bot_state": "idle", "bot_state_label": "Daily limit",
                                     "daily_allowance": 20, "trades_today": 20, "allowance_used_up": True}])
    assert "allowance_vs_state" not in keys(casino.contradictions(said))
    assert "allowance_vs_state" not in keys(casino.contradictions(running_table()))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_pick_window_must_end_with_its_table():
    """`closes_in_s` 86391 under `ends_in_s` 3592 on a 1 hour table; `open: false` still counting."""
    assert "pick_window" in keys(casino.contradictions(running_table()))
    day = running_table(hours=24, ends_in_s=86000, picks={"open": True, "closes_in_s": 86000, "my_pick": None})
    assert "pick_window" not in keys(casino.contradictions(day))
    closed = done_table(picks={"open": False, "closes_in_s": 49417, "my_pick": None})
    assert "pick_window" in keys(casino.contradictions(closed))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_lone_pick_comes_back_whole():
    """Table 42: $10 on rank 2, nobody on the winner: `refunded`, `paid_usdc` 10."""
    right = {"open": False, "closes_in_s": 0, "pool_usdc": 10.0, "pickers": 1,
             "my_pick": {"seat_id": 155, "stake_usdc": 10.0, "status": "refunded", "paid_usdc": 10.0}}
    assert "pick_paid" not in keys(casino.contradictions(done_table(picks=right)))
    short = {**right, "my_pick": {"seat_id": 155, "stake_usdc": 10.0, "status": "refunded", "paid_usdc": 0.0}}
    assert "pick_paid" in keys(casino.contradictions(done_table(picks=short)))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_ask_that_lapsed_must_not_read_pending():
    """Seats 120-123 at table 31, asked 2026-10-28, read `pending` on 2026-11-01 with an approve_url,
    while the lobby's owner block has no open ask."""
    seats = [{"seat_id": 120, "table_id": 31, "seat_status": "pending"},
             {"seat_id": 121, "table_id": 31, "seat_status": "pending"},
             {"seat_id": 166, "table_id": 44, "seat_status": "seated"}]
    found = casino.stale_asks(seats, {"approve_all_ids": [], "asks": 0})
    assert [f["seat_id"] for f in found] == [120, 121]
    assert casino.stale_asks(seats, {"approve_all_ids": [120, 121], "asks": 2}) == []
    assert casino.stale_asks(seats, None) == []  # an unread lobby is not an empty one


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_gaps_between_checks_are_measured_through_a_collapsed_row():
    log = [{"at": "2026-11-01T09:05:58+00:00", "kind": "TUNED"},
           {"at": "2026-11-01T09:01:53+00:00", "kind": "CHECKED", "repeats": 2, "since": "2026-11-01T08:45:39+00:00"},
           {"at": "2026-11-01T08:42:39+00:00", "kind": "TUNED"}]
    assert [round(g) for g in casino.check_gaps(log)] == [3, 16, 4]
    gap = [{"at": "2026-11-01T09:40:00+00:00", "kind": "CHECKED"}, {"at": "2026-11-01T09:00:00+00:00", "kind": "CHECKED"}]
    table = running_table(my_tune_log=gap, my_coach_line={"line": "it checks every 10 minutes", "risk_line": ""})
    assert "check_cadence" in keys(casino.contradictions(table))
    # One row has no gap to measure.
    assert "check_cadence" not in keys(casino.contradictions(running_table(my_tune_log=gap[:1])))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_market_tune_must_be_what_the_lanes_now_say():
    tune = {"at": "2026-11-01T10:20:00+00:00", "kind": "TUNED", "by": "NEXUS",
            "text": "PERP BTC off · 2 losses in a row on BTC: -3.00 USDC"}
    feed = [{"seat_id": 166, "what": ["markets"], "by": "NEXUS", "at": "2026-11-01T10:20:01+00:00"}]
    off = {"perpetual": {"on": True, "scope": ["ETH"]}, "clob": {"on": False, "scope": []}}
    settings = {"stop_loss_pct": 4.0, "take_profit_pct": 32.0, "trade_size_pct": 8.0}
    agrees = running_table(my_tune_log=[tune], changes=feed, my_bot_settings={**settings, "lanes": off})
    assert "tune_vs_settings" not in keys(casino.contradictions(agrees))
    still = {**off, "perpetual": {"on": True, "scope": ["ETH", "BTC"]}}
    stale = running_table(my_tune_log=[tune], changes=feed, my_bot_settings={**settings, "lanes": still})
    assert "tune_vs_settings" in keys(casino.contradictions(stale))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_five_trade_rule_is_held_against_the_tunes_only_while_it_is_said():
    """`my_coach_line.line`: "tunes once the bot has 5 closed trades"; table 42 tuned at 08:15 with none."""
    tune = {"at": "2026-11-01T08:15:00+00:00", "kind": "TUNED", "by": "NEXUS", "text": "stop loss 8 → 7 % · rank 1 → 2"}
    feed = [{"seat_id": 154, "what": ["stop loss"], "by": "NEXUS", "at": "2026-11-01T08:15:02+00:00"}]
    table = done_table(my_tune_log=[tune], changes=feed)
    assert "coach_rule_vs_tunes" in keys(casino.contradictions(table, five_rule=True))
    assert "coach_rule_vs_tunes" not in keys(casino.contradictions(table))
    late = {**tune, "at": "2026-11-01T09:05:00+00:00"}  # five had closed by then
    feed_late = [{**feed[0], "at": "2026-11-01T09:05:02+00:00"}]
    assert "coach_rule_vs_tunes" not in keys(
        casino.contradictions(done_table(my_tune_log=[late], changes=feed_late), five_rule=True))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_et10_prize_still_pending_long_after_the_end_is_named():
    pending = [{"place": 1, "seat_id": 155, "amount_et10": 3, "status": "pending"}]
    table = done_table(et10_paid=pending)
    soon = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)
    late = datetime(2026, 11, 1, 16, 0, tzinfo=timezone.utc)
    assert "et10_pending" not in keys(casino.contradictions(table, now=soon))
    assert "et10_pending" in keys(casino.contradictions(table, now=late))
    credited = done_table(et10_paid=[{**pending[0], "status": "credited"}])
    assert "et10_pending" not in keys(casino.contradictions(credited, now=late))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_leaderboard_must_add_up_to_its_tables():
    tables = [done_table(), done_table(id=40, results={"pot_usdc": 5.0, "ranked": [
        {"seat_id": 143, "rank": 1, "prize_usdc": 5.0, "prize_et10": 3}]})]
    assert casino.leaderboard_vs_tables({"tables_done": 2, "paid_usdc": 20.0, "paid_et10": 7.0}, tables) == []
    found = casino.leaderboard_vs_tables({"tables_done": 2, "paid_usdc": 25.0, "paid_et10": 7.0}, tables)
    assert [f["key"] for f in found] == ["leaderboard_vs_tables"]
    found = casino.leaderboard_vs_tables({"tables_done": 3, "paid_usdc": 20.0, "paid_et10": 7.0}, tables)
    assert [f["key"] for f in found] == ["leaderboard_vs_tables"]
    # Table 15: an ET10 table's `prize_usdc` is ET10, in the board's ET10 and not its USDC.
    et10 = done_table(id=15, currency="ET10", results={"ranked": [{"seat_id": 87, "prize_usdc": 100.0, "prize_et10": 0}]})
    assert casino.leaderboard_vs_tables({"tables_done": 1, "paid_usdc": 0.0, "paid_et10": 100.0}, [et10]) == []
    # Tables 5 and 11: 600 ET10 `capped` is recorded and "is not paid out".
    capped = done_table(id=5, results={"ranked": [{"seat_id": 29, "prize_usdc": 80.0, "prize_et10": 600}]},
                        et10_paid=[{"place": 1, "seat_id": 29, "amount_et10": 600.0, "status": "capped"}])
    assert casino.leaderboard_vs_tables({"tables_done": 1, "paid_usdc": 80.0, "paid_et10": 0.0}, [capped]) == []
    found = casino.leaderboard_vs_tables({"tables_done": 1, "paid_usdc": 80.0, "paid_et10": 600.0}, [capped])
    assert [f["key"] for f in found] == ["leaderboard_vs_tables"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_write_goes_only_to_a_paper_table_and_a_seat_of_ours():
    table = running_table(kind="flash", currency="USDC")
    assert casino.write_refusal(table, 166) is None
    assert "not ours" in casino.write_refusal(table, 167)
    assert "paper" in casino.write_refusal({**table, "mode": "live"}, 166)
    assert "USDC" in casino.write_refusal({**table, "currency": "ET10"}, 166)
    assert casino.write_refusal(None, 166)
    several = {**table, "my_seat": {"seat_id": 1}, "my_seats": [{"seat_id": 1}, {"seat_id": 166}]}
    assert casino.write_refusal(several, 166) is None


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_next_asks_are_one_bot_a_table_and_never_repeat():
    bots = [{"instance_id": f"i{n}", "name": f"casino B{n}", "species": f"S{n}", "trading": True} for n in range(4)]
    tables = [{"id": 44, "tier": "fmicro1h"}, {"id": 45, "tier": "fpro1h"}, {"id": 43, "tier": "fmicro5h"}]
    asks = casino.next_asks([], bots, tables, seated=set(), spent=set(), running=0)
    assert [a["table_id"] for a in asks] == [44, 45, 43]
    assert len({a["instance_id"] for a in asks}) == 3
    # The least tried variant first, so the coach off and the risk levels come early, not after 66 As.
    assert [a["variant"] for a in asks] == ["A", "B", "C1"]

    # Tried already: the same bot, tier and variant is not asked again.
    tried = [{"type": "experiment", "variant": "A", "species": "S0", "tier": "fmicro1h"}]
    asks = casino.next_asks(tried, bots[:1], tables[:1], seated=set(), spent=set(), running=0)
    assert [a["variant"] for a in asks] == ["B"]

    # A bot out of allowance sits this one out; a bot already at a table sits every variant out but E,
    # which is the question of a bot at two tables, once a tick.
    asks = casino.next_asks([], bots, tables, seated={"i0"}, spent={"i1"}, running=0)
    assert [(a["instance_id"], a["variant"]) for a in asks] == [("i2", "A"), ("i3", "B"), ("i0", "E")]
    two = bots + [{"instance_id": "i9", "name": "casino B9", "species": "S9"}]
    asks = casino.next_asks([], two, tables + [{"id": 35, "tier": "fpro5h"}], seated={"i0", "i9"}, spent={"i1"}, running=0)
    assert [a["variant"] for a in asks].count("E") == 1

    # The ceiling counts what already runs.
    assert casino.next_asks([], bots, tables, seated=set(), spent=set(), running=casino.MAX_RUNNING) == []
    assert len(casino.next_asks([], bots, tables, seated=set(), spent=set(), running=casino.MAX_RUNNING - 1)) == 1


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_variant_is_one_closed_write_or_none():
    assert casino.variant_write("A") is None
    assert casino.variant_write("B") == ("coach", {"on": False})
    assert casino.variant_write("C1") == ("risk", {"level": 1})
    assert casino.variant_write("C10") == ("risk", {"level": 10})
    assert casino.variant_write("D") == ("bot-settings", {"stop_loss_pct": 2.0})


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_lab_bot_is_never_seated_or_changed_by_the_casino():
    bots = [{"name": "casino RSI Sniper", "species": "RSI Sniper"}, {"name": "tournament Perceptron Oracle", "species": "Perceptron Oracle"},
            {"name": "lab Wave 2 Volume Viper", "species": "Volume Viper"}, {"name": "Stock BLue Test", "species": None}]
    assert [b["name"] for b in casino.for_the_casino(bots)] == ["casino RSI Sniper", "tournament Perceptron Oracle"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_next_species_is_one_we_have_not_cloned():
    available = [{"source_type": "wta_species", "id": "a", "name": "MACD Hunter"},
                 {"source_type": "perpetual_agent", "id": "b", "name": "Stat Oracle"},
                 {"source_type": "wta_species", "id": "c", "name": "Volume Viper"}]
    ours = [{"name": "casino MACD Hunter"}, {"name": "lab Wave 2 Volume Viper"}]
    assert casino.next_species(available, ours)["id"] == "b"
    assert casino.next_species(available[:1], ours) is None


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_last_line_says_the_one_thing_to_do():
    now = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)
    base = {"new": [], "asks": 0, "unstarted": [], "ended": [], "ends": [], "now": now}
    assert casino.decide(**base).startswith("decide: quiet")
    assert "11:05" in casino.decide(**{**base, "ends": ["2026-11-01T11:05:57+00:00"]})
    assert casino.decide(**{**base, "ended": [42]}) == "decide: look 42"
    assert casino.decide(**{**base, "unstarted": [44, 45]}) == "decide: start 44 45"
    assert casino.decide(**{**base, "asks": 3}) == "decide: approve 3"
    assert casino.decide(**{**base, "new": [{"key": "pick_window"}]}) == "decide: file pick_window"
    # What is new comes first: a tick that files nothing would bury it under the next round.
    assert casino.decide(**{**base, "new": [{"key": "pick_window"}], "asks": 3}).startswith("decide: file")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_key_handled_once_is_not_news_again():
    found = [{"key": "standings_vs_trades", "table_id": 40}, {"key": "pick_window", "table_id": 44}]
    rows = [{"type": "handled", "key": "standings_vs_trades", "how": "#234"}]
    assert [f["key"] for f in casino.new_keys(found, rows)] == ["pick_window"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_coach_is_compared_with_itself_off():
    rows = [{"type": "final", "variant": "A", "roi_pct": 4.0}, {"type": "final", "variant": "A", "roi_pct": -2.0},
            {"type": "final", "variant": "B", "roi_pct": -5.0}, {"type": "tick"}]
    assert casino.roi_by_variant(rows) == {"A": {"n": 2, "mean_roi": 1.0}, "B": {"n": 1, "mean_roi": -5.0}}

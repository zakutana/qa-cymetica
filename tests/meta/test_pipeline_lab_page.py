"""/lab, the laboratory's page: one room per sector, results first.

The operator, 2026-09-23, on the first /lab: "proč má každá karta svůj room?
já myslel že bude 1 room na odvětví ... musím moc scrollovat, nepřehledné.
Design 3/10." And on the chat: they will hardly ever read it, maybe glance
at it out of curiosity. So the page is four sector rooms -- Karty, Boti,
Memecoiny, Fondy -- each a ranking of its experiments by what they made
after costs, failures folded into an archive, and the conversation behind a
button.

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
        "legs": [{"card": "c1", "url": "https://cymetica.com/events/c1",
                  "entry": 100.0, "tp": 8.0, "sl": -5.0,
                  "series": _series(1, [99.0, 100.0, 101.0, 102.0])}],
        "trades": [{"id": "TRD-1", "at": "2026-09-22T02:00:00+00:00",
                    "outcome": "accepted", "closed_at": None}],
        "backtests": [{"verdict": "pass", "period": 90, "return_pct": 26.2,
                       "sharpe": 2.18, "drawdown_pct": 14.1}]}
    return {
        "rooms": [{"id": "general", "kind": "general", "title": "General"},
                  *[{"id": rid, "kind": "strategy", "title": rid}
                    for rid in ("STR-0001", "STR-0002", "STR-0003",
                                "STR-0004", "STR-0005")]],
        "threads": {"general": [{"kind": "question", "id": "NEX-1",
                                 "at": "2026-09-20T01:00:00+00:00", "text": "?"}],
                    "cards": [{"kind": "operator_note", "id": "N-1",
                               "at": "2026-09-23T01:00:00+00:00", "text": "hm"}],
                    "STR-0001": [], "STR-0002": [], "STR-0003": [],
                    "STR-0004": [], "STR-0005": []},
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
                          "conviction_70": {"min": 70.0, "n": 45, "net_pct": -12.0},
                          "fees": [{"fee_pct": 0.5, "net_pct": -19.0, "n": 673}],
                          "excluded": {"unpriced": 1200, "too_thin": 300}},
            "funds": sector(n=0, net_pct=None, usdc=None, stake_usdc=None, wins=0),
        },
        "nexus": {"questions": 88, "answered": 53, "picks": 31, "gated": 31,
                  "gate_pass": 22, "survived": 0, "refuted": 1},
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
             "net_pct": None, "usdc": None, "stake_usdc": None, "verdict": None}],
    }


CHANNEL = {"median_seconds": 240.0, "measured": 42, "failed": 28, "refused": 7}
FOMO = {"curves": [{"token": "0xa", "symbol": "DOGEX", "conviction": 88.0,
                    "points": [[1, 38.5], [2, 41.0], [4, 12.0]],
                    "last": 12.0, "peak": 41.0},
                   {"token": "0xb", "symbol": "PEPEX", "conviction": 12.0,
                    "points": [[1, -30.5]], "last": -30.5, "peak": -30.5}],
        "curves_total": 9}


def _view():
    return _lab_page().lab_view(_rooms_view(), _report(), CHANNEL, FOMO, now=NOW)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_view_is_four_sector_rooms_in_their_order_with_their_names():
    view = _view()
    assert [s["key"] for s in view["sectors"]] == ["cards", "bots", "memecoins", "funds"]
    # English since 2026-09-25 (CLAUDE.md, How to work with me).
    assert [s["name"] for s in view["sectors"]] == ["Cards", "Bots", "Memecoins", "Funds"]
    cards = view["sectors"][0]
    assert cards["net_pct"] == 1.0 and cards["usdc"] == 5.0, "the report's figures ride along"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_each_experiment_lands_in_its_sector_and_its_group():
    """Running experiments are live; one with a verdict is done; one the
    report archived -- nothing bought, or not his pick -- is in the archive
    with a short reason, never a paragraph (N-0034, N-0049, N-0050). An Arena
    room is in no sector yet, so it is on no page rather than among cards."""
    by_id = {e["id"]: e for e in _view()["experiments"]}
    assert set(by_id) == {"STR-0001", "STR-0002", "STR-0003", "STR-0004"}
    assert (by_id["STR-0001"]["sector"], by_id["STR-0001"]["group"]) == ("cards", "live")
    assert (by_id["STR-0002"]["group"], by_id["STR-0002"]["reason"]) == (
        "archive", "nothing bought")
    assert by_id["STR-0004"]["group"] == "done"
    assert by_id["STR-0004"]["reason"] == "drawdown 11.8% past 10% limit"
    assert (by_id["STR-0003"]["sector"], by_id["STR-0003"]["reason"]) == (
        "bots", "stopped by itself")
    assert by_id["STR-0003"]["trading"] is False
    for e in by_id.values():
        assert not e["reason"] or len(e["reason"]) <= 40, e["reason"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_experiments_path_is_what_it_is_worth_since_we_went_in():
    """A card's line is its index rebased on the index we bought at, from our
    buy on -- V2's book -- so its last point is our result before costs. A
    bot's line is its booked profit over what went into it."""
    by_id = {e["id"]: e for e in _view()["experiments"]}
    card = by_id["STR-0001"]
    assert [p[1] for p in card["path"]] == [0.0, 1.0, 2.0], card["path"]
    assert card["spark"] == card["path"], "short paths are not thinned"
    assert (card["tp"], card["sl"]) == (8.0, -5.0)
    assert card["backtest"] == {"pct": 26.2, "period": 90, "sharpe": 2.18,
                                "pass": True}
    # Opened 22. 9. 02:00 with a five-day window; it is 23. 9. 12:00.
    assert card["left_days"] == pytest.approx(3 + 14 / 24, abs=0.01)
    assert card["url"] == "https://cymetica.com/events/c1"
    bot = by_id["STR-0003"]
    assert [p[1] for p in bot["path"]] == [10.0, 3.0]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_long_path_is_thinned_but_keeps_both_ends():
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
    assert view["account"] == {"free": 88593.91, "in_cards": 24329.56,
                               "in_bots": 247.2, "at": "2026-09-23T11:00:00+00:00",
                               "stale": False}
    nexus = view["nexus"]
    assert nexus["questions"] == 88 and nexus["median_seconds"] == 240.0
    assert "cards" in view["threads"] and "general" in view["threads"]
    assert view["movers"] == FOMO["curves"] and view["movers_total"] == 9


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
    written = {
        "lp": ({k for s in view["sectors"] for k in s}
               | {k for p in real.values() for k in p}),
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
def test_the_page_opens_on_four_sectors_and_a_ranking_not_on_rooms_per_card(tmp_path):
    captured = _drawn(tmp_path, "open")
    tabs = captured.get("sectors", "")
    for name in ("Cards", "Bots", "Memecoins", "Funds"):
        assert name in tabs, f"no {name} room"
    assert tabs.count('data-sector="') == 4, "one room per sector, four of them"
    room = captured.get("room", "")
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
    assert "Never bought" in archive and "nothing bought" in archive
    done = _drawn(tmp_path, "done", after='window.labShow("cards", "done");').get("room", "")
    assert "Solana doubles" in done and "drawdown 11.8%" in done and "didn't work" in done


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_experiment_opens_into_a_chart_and_four_numbers(tmp_path):
    room = _drawn(tmp_path, "detail",
                  after='window.labOpen("STR-0001");').get("room", "")
    assert "<svg" in room and "dt-chart" in room, "no chart in the opened experiment"
    for label in ("In<", "Now<", "Result<", "Backtest<"):
        assert label in room, f"the opened experiment has no {label}"
    assert "cymetica.com/events/c1" in room, "no way to the card itself"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_room_of_ours_says_ours_and_never_ranks_above_his(tmp_path):
    """V5, the own lane: a paper bot's next setting is OUR idea (origin
    OUR-...). The page says so -- "ours", not "idea OUR-0001" -- and ranks
    it after his, whatever it earned."""
    rooms_view, report = _rooms_view(), _report()
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
    view = _lab_page().lab_view(rooms_view, report, CHANNEL, FOMO, now=NOW)
    by_id = {e["id"]: e for e in view["experiments"]}
    assert by_id["STR-0006"]["ours"] is True and by_id["STR-0003"]["ours"] is False

    code, err, captured = _run_page(_node(), tmp_path / "ours", view,
                                    after='window.labShow("bots");',
                                    page=_lab_page())
    assert code == 0, err[:1200]
    room = captured.get("room", "")
    assert ">ours<" in room, room[:2000]
    assert room.index("Bollinger Bandit · SL 5") > room.index("Bollinger Bandit<"), (
        "a room of ours ranked above his pick")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_bots_room_says_whether_each_bot_trades(tmp_path):
    room = _drawn(tmp_path, "bots", after='window.labShow("bots");').get("room", "")
    # A bot that stopped by itself says so once -- its reason -- rather than
    # "idle" and "stopped by itself" side by side.
    assert "Bollinger Bandit" in room and "stopped by itself" in room
    assert ">idle<" not in room

    # And the other two answers, which the fixture never drew (deep pass
    # 2026-09-25, C08): a bot that trades says "trading", one that does not
    # and has no reason says "idle".
    for trading, word in ((True, ">trading<"), (False, ">idle<")):
        view = _view()
        bots = [e for e in view["experiments"] if e.get("trading") is not None]
        assert bots, "the fixture holds no bot experiment to draw"
        for e in bots:
            e.update(trading=trading, reason=None)
        code, err, captured = _run_page(_node(), tmp_path / f"bots-{trading}", view,
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
    """The answer is V3's ($10 into every hot signal, after costs); the list
    under it is the operator's, decided 2026-09-13/14: ONE list with the graph
    as a column ("mel to byt jen 1 seznam ... jen nova kolumna s grafem"), our
    own coloured bubble rather than the browser's grey title, no price
    columns ("ty dve kolumny smaz"), the conviction >= 70 figure they asked
    for, and the untradeable coins named as dropped rather than silently
    missing -- plus the table saying it is winners by construction."""
    room = _drawn(tmp_path, "memes", after='window.labShow("memecoins");').get("room", "")
    assert "−19.8" in room, "the $10 answer is not the headline"
    assert room.count("<table") == 1 and "mc-spark" in room
    assert room.count("<th>") == 5, "five columns: token, conviction, now, peak, the graph"
    assert "<title>" not in room, "the native tooltip is back"
    assert 'data-h="1"' in room and 'data-v="38.5"' in room
    assert 'data-h="3"' not in room, "an hour nobody priced got a point"
    assert "stroke-dasharray" in room, "an unpriced stretch is not drawn as a gap"
    up = room[room.index("DOGEX"):]
    assert "mc-up" in up[:up.index("PEPEX")], "the gain is not green"
    assert "mc-down" in room[room.index("PEPEX"):][:500], "the loss is not red"
    assert "price at signal" not in room and "cena při signálu" not in room
    assert "Conviction ≥ 70" in room and "−12" in room
    assert "unpriced" in room and "1,200" in room, "the dropped coins are not named"
    assert "winners by construction" in room, (
        "the table does not say it is winners by construction")
    # M03, deep pass of 2026-09-13: the figure under the word median must be
    # the median (-40) and not the mean (-19.8).
    typical = room[room.index("Typical trade"):][:300]
    assert "−40" in typical and "−19.8" not in typical, typical
    template = _lab_page().TEMPLATE
    assert 'id="tip"' in template and "mousemove" in template, "no bubble"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_memecoin_room_with_nothing_measured_yet_says_so(tmp_path):
    """Never watched and watched-with-nothing-yet must not look like a room
    that is broken: it says there is nothing yet."""
    view = _view()
    view["movers"], view["movers_total"] = [], 0
    code, err, captured = _run_page(_node(), tmp_path / "nomemes", view,
                                    after='window.labShow("memecoins");',
                                    page=_lab_page())
    assert code == 0, err[:900]
    assert "No signal has had" in captured.get("room", "")

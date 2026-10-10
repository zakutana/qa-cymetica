"""The laboratory's report: what each product earned, after costs.

Plan v2, V4 (docs/laborator-plan.md): the laboratory is a department with one
shape, and its page reads one file -- `state/lab/report.json`, written by
`lab.py report` from the diaries alone. Per product (cards, bots, memecoins,
funds): the net return after costs, how many experiments it stands on, how
sure that is, what is running, the best room and how many are archived. And
one line on Nexus: questions -> picks -> gate -> survived.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from qa import lab
from qa import lab_report
from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
NOW = datetime(2026, 9, 23, 12, 0, tzinfo=timezone.utc)


def _card(n):
    return f"{n:08x}-8717-4fc7-a91a-9a6724cadd7e"


C1, C2 = _card(0xC1), _card(0xC2)


def _fixture():
    """Five rooms: a running card with an open position, a card judged
    survived, a paper bot, a fund judged refuted, and a fund that stopped
    holding nothing -- archived."""
    answers = [
        {"type": "answer", "id": "NEX-0001", "at": "2026-09-20T01:00:00+00:00",
         "text": f"Buy {C1} bull."},
        {"type": "answer", "id": "NEX-0002", "at": "2026-09-20T02:00:00+00:00",
         "text": f"Buy {C2} bull."},
        {"type": "answer", "id": "NEX-0003", "at": "2026-09-20T03:00:00+00:00",
         "text": "**Pick: MACD Hunter.**"},
        {"type": "answer", "id": "NEX-0004", "at": "2026-09-20T04:00:00+00:00",
         "text": "Long AIB-BIOSCIENCES and AIB-MOLECULAR."}]
    questions = [{"type": "question", "id": f"NEX-000{n}",
                  "at": f"2026-09-20T0{n}:00:00+00:00"} for n in range(1, 6)]
    notebook = [
        {"type": "gate", "origin": "NEX-0001", "card": C1, "verdict": "pass"},
        {"type": "gate", "origin": "NEX-0002", "card": C2, "verdict": "pass"},
        {"type": "gate", "origin": "NEX-0002", "card": _card(9),
         "verdict": "reject"}]
    room_rows = [
        {"type": "strategy", "id": "STR-0001", "origin": "NEX-0001",
         "card": C1, "title": "Card one"},
        {"type": "status", "room": "STR-0001", "status": "running"},
        {"type": "strategy", "id": "STR-0002", "origin": "NEX-0002",
         "card": C2, "title": "Card two"},
        {"type": "status", "room": "STR-0002", "status": "stopped"},
        {"type": "verdict", "room": "STR-0002", "verdict": "survived",
         "return_pct": 2.0},
        {"type": "strategy", "id": "STR-0003", "origin": "NEX-0003",
         "kind": "bot", "ref": "sp-macd", "title": "MACD Hunter"},
        {"type": "acceptance", "room": "STR-0003",
         "legs": [{"kind": "bot", "ref": "inst-macd", "share": 1.0}]},
        {"type": "status", "room": "STR-0003", "status": "running"},
        {"type": "strategy", "id": "STR-0004", "origin": "NEX-0004",
         "kind": "fund", "ref": "AIB-BIOSCIENCES", "title": "AIB-BIOSCIENCES"},
        {"type": "status", "room": "STR-0004", "status": "stopped"},
        {"type": "verdict", "room": "STR-0004", "verdict": "refuted",
         "return_pct": -1.0},
        {"type": "strategy", "id": "STR-0005", "origin": "NEX-0004",
         "kind": "fund", "ref": "AIB-MOLECULAR", "title": "AIB-MOLECULAR"},
        {"type": "status", "room": "STR-0005", "status": "stopped"}]
    paper_rows = [
        {"type": "intent", "id": "TRD-1", "card_id": C1, "usdc": 500.0,
         "nexus": {"id": "NEX-0001"}},
        {"type": "outcome", "id": "TRD-1", "outcome": "accepted",
         "position_id": "p1"}]
    samples = [
        {"type": "sample", "kind": "position", "at": "2026-09-23T11:00:00+00:00",
         "position_id": "p1", "card_id": C1, "status": "open",
         "unrealized_pnl_usdc": 25.0},
        {"type": "sample", "kind": "bot", "at": "2026-09-23T11:00:00+00:00",
         "instance_id": "inst-macd", "total_profit_usdc": 7.2}]
    clone_rows = [
        {"type": "intent", "id": "CLN-1", "kind": "fund",
         "instance_id": "inst-macd", "amount": 240.0},
        {"type": "outcome", "id": "CLN-1", "outcome": "accepted"}]
    return dict(answers=answers, questions=questions, notebook=notebook,
                room_rows=room_rows, paper_rows=paper_rows,
                sample_rows=samples, clone_rows=clone_rows)


def _report(**over):
    parts = {**_fixture(), "fomo_rows": [], "now": NOW, **over}
    return lab_report.report(
        parts["questions"] + parts["answers"], parts["notebook"],
        parts["room_rows"], parts["paper_rows"], parts["sample_rows"],
        parts["clone_rows"], parts["fomo_rows"], now=parts["now"])


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_each_product_says_what_it_earned_after_costs():
    """A running card is marked from our position, net of the live round
    trip; a judged room takes its verdict's return, which V2 already made
    net; a bot is as their engine books it on what went in. A stopped room
    that never held anything is archived, not counted."""
    said = _report()
    cards, bots, funds = (said["products"][k] for k in ("cards", "bots", "funds"))

    running_card = lab._net_of(25.0 / 500.0 * 100.0, lab.GATE["round_trip_cost_pct"])
    assert cards["n"] == 2 and cards["running"] == 1, cards
    assert cards["net_pct"] == pytest.approx((running_card + 2.0) / 2), cards

    assert bots["n"] == 1 and bots["running"] == 1, bots
    assert bots["net_pct"] == pytest.approx(7.2 / 240.0 * 100.0), bots

    assert funds["n"] == 1 and funds["archived"] == 1, funds
    assert funds["net_pct"] == pytest.approx(-1.0), funds

    by_room = {r["id"]: r for r in said["rooms"]}
    assert by_room["STR-0001"]["net_pct"] == pytest.approx(running_card)
    assert by_room["STR-0004"]["net_pct"] == pytest.approx(-1.0)
    assert by_room["STR-0005"]["archived"] is True
    assert by_room["STR-0005"]["net_pct"] is None

    # R04 (deep pass of 2026-09-24, 3/3): a room's name is its newest `title`
    # row (qa.rooms.names), and the report named it by the one it opened
    # with -- STR-0004 read "BTC 30 % + BCH 12 % pro 89 000" in the report and
    # the 7:00 page while /lab said "BTC selling lows + MARA".
    renamed = _report(room_rows=_fixture()["room_rows"] + [
        {"type": "title", "room": "STR-0001", "title": "Card one, renamed"}])
    assert {r["id"]: r for r in renamed["rooms"]}["STR-0001"]["title"] == \
        "Card one, renamed"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_room_that_holds_a_bot_is_a_bot_even_from_before_rooms_had_kinds():
    """STR-0001, Perceptron Oracle, opened 2026-09-11 before a room carried
    its kind: no `kind`, no `card`, and its answer's order was a clone. The
    first report counted it among the cards. A room with no kind is the kind
    of what its answer put money into; an Arena room is none of the four."""
    fx = _fixture()
    fx["room_rows"] += [
        {"type": "strategy", "id": "STR-0006", "origin": "NEX-0006",
         "title": "Perceptron Oracle"},
        {"type": "status", "room": "STR-0006", "status": "stopped"},
        {"type": "verdict", "room": "STR-0006", "verdict": "refuted",
         "return_pct": -4.96},
        {"type": "strategy", "id": "STR-0007", "origin": "NEX-0007",
         "kind": "arena", "ref": "BLUE", "title": "Arena BLUE"},
        {"type": "status", "room": "STR-0007", "status": "running"}]
    fx["clone_rows"] += [
        {"type": "intent", "id": "CLN-9", "kind": "clone",
         "nexus": {"id": "NEX-0006"}, "source_id": "perceptron"},
        {"type": "outcome", "id": "CLN-9", "outcome": "accepted"}]
    said = _report(room_rows=fx["room_rows"], clone_rows=fx["clone_rows"])
    by_room = {r["id"]: r for r in said["rooms"]}
    assert by_room["STR-0006"]["product"] == "bots", by_room["STR-0006"]
    assert by_room["STR-0007"]["product"] is None, "an Arena room is not a card"
    assert said["products"]["bots"]["n"] == 2
    assert said["products"]["cards"]["n"] == 2, "the old bot room left the cards"

    # STR-0045 (2026-09-24): the head-to-head room opened from our proposal
    # OUR-0001, five paper bots in its plan, showed under Karty -- no kind on
    # the strategy row and no clone of ours naming its origin. The operator:
    # "proc tu nevidim ten nvoy experiment?" What a room holds is its plan.
    # (Folded in, deep pass 2026-09-24.)
    fx = _fixture()
    fx["room_rows"] += [
        {"type": "strategy", "id": "STR-0045", "origin": "OUR-0001",
         "title": "Head-to-head"},
        {"type": "plan", "room": "STR-0045", "legs": [
            {"kind": "bot", "ref": "i-1", "side": "bull", "share": 0.5},
            {"kind": "bot", "ref": "i-2", "side": "bull", "share": 0.5}]},
        {"type": "status", "room": "STR-0045", "status": "running"}]
    said = _report(room_rows=fx["room_rows"], clone_rows=fx["clone_rows"])
    assert {r["id"]: r for r in said["rooms"]}["STR-0045"]["product"] == "bots"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_each_product_says_how_many_usdc_it_made_beside_the_percent():
    """"Čistý výsledek" is money to the operator: the percent per experiment
    and, beside it, the USDC -- net of the same costs, over the rooms that
    put a stake in. A room with no stake (a fund only marked) adds nothing."""
    said = _report()
    cards, bots, funds = (said["products"][k] for k in ("cards", "bots", "funds"))
    running_card = lab._net_of(25.0 / 500.0 * 100.0, lab.GATE["round_trip_cost_pct"])
    assert cards["usdc"] == pytest.approx(500.0 * running_card / 100.0)
    assert cards["stake_usdc"] == pytest.approx(500.0)
    assert bots["usdc"] == pytest.approx(7.2)
    assert funds["usdc"] is None, "nothing was staked, so there is no money figure"
    by_room = {r["id"]: r for r in said["rooms"]}
    assert by_room["STR-0001"]["stake_usdc"] == pytest.approx(500.0)
    assert by_room["STR-0001"]["usdc"] == pytest.approx(500.0 * running_card / 100.0)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_memecoins_carry_the_median_and_the_high_conviction_answer(monkeypatch):
    """[operator 2026-09-14] asked for the P&L of entering only at their
    conviction 70 and above. Answered by the same $10 question over the
    signals that scored 70 or more -- their checkpoints with them -- and the
    median beside the mean, because one runaway coin moves a mean."""
    calls = []

    def fake(rows, now=None, **kw):
        calls.append(rows)
        n = 20 if len(calls) == 1 else 4
        return {"signals": 40, "window_open": 0, "could_buy_share": 0.5,
                # Different medians for the two calls, so a median read off
                # the conviction subset cannot pass (deep pass B11, 3/3).
                "by_fee": {0.0: {"n": n, "mean_net_pct": -4.0 if n == 20 else 6.0,
                                 "median_net_pct": -9.0 if n == 20 else -3.0,
                                 "win_rate": 0.25}}}

    monkeypatch.setattr(lab_report.fomo, "ten_dollars", fake)
    rows = [{"type": "signal", "key": "a", "conviction": 88.0},
            {"type": "signal", "key": "b", "conviction": 12.0},
            {"type": "signal", "key": "c"},
            {"type": "checkpoint", "key": "a", "horizon": "24h"},
            {"type": "checkpoint", "key": "b", "horizon": "24h"}]
    memes = _report(fomo_rows=rows)["products"]["memecoins"]
    assert memes["median_pct"] == -9.0
    assert memes["conviction_70"] == {"min": 70.0, "n": 4, "net_pct": 6.0}
    assert [r.get("key") for r in calls[1]] == ["a", "a"], (
        "the high-conviction answer must see only those signals and their "
        "own checkpoints")
    # "70 and above", at the edge: with signals only at 88 and 12, any cutoff
    # between them -- or `>` for `>=` -- passed (deep pass 2026-09-25, C09).
    edge = [{"type": "signal", "key": "at", "conviction": 70.0},
            {"type": "signal", "key": "under", "conviction": 69.99}]
    assert [r["key"] for r in lab_report._high_conviction(edge)] == ["at"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_band_is_given_only_when_there_is_enough_to_band():
    """Two coins are not a measurement: under five experiments the band is
    null and the page says so, rather than printing 3%-97%."""
    said = _report()
    assert said["products"]["cards"]["wilson"] is None
    assert said["products"]["cards"]["min_n"] == lab_report.MIN_N

    fx = _fixture()
    for n in range(10, 16):
        card = _card(n)
        fx["room_rows"] += [
            {"type": "strategy", "id": f"STR-00{n}", "origin": "NEX-0002",
             "card": card, "title": f"x{n}"},
            {"type": "status", "room": f"STR-00{n}", "status": "stopped"},
            {"type": "verdict", "room": f"STR-00{n}", "verdict": "survived",
             "return_pct": 1.0}]
    band = _report(room_rows=fx["room_rows"])["products"]["cards"]["wilson"]
    assert band is not None and 0.0 <= band[0] < band[1] <= 1.0, band


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_memecoins_are_ten_dollars_into_every_hot_signal(monkeypatch):
    """The memecoin product is V3's answer, not a room: $10 into every hot
    signal, held a day, with no swap fee since 2026-10-08 (the operator: "1% u
    memecoinu taky vyhod"; 1% a side until then) -- with 0.5, 1 and 2 beside it
    and the share we could have bought ("stihli bychom")."""
    seen = {}

    def fake(rows, now=None, **kw):
        seen["now"] = now
        return {"signals": 40, "window_open": 7, "bought": 20,
                "could_buy_share": 0.6,
                "by_fee": {0.0: {"n": 20, "mean_net_pct": -2.0, "win_rate": 0.35},
                           0.5: {"n": 20, "mean_net_pct": -3.0, "win_rate": 0.3},
                           1.0: {"n": 20, "mean_net_pct": -4.0, "win_rate": 0.25},
                           2.0: {"n": 20, "mean_net_pct": -6.0, "win_rate": 0.2}}}

    monkeypatch.setattr(lab_report.fomo, "ten_dollars", fake)
    memes = _report(fomo_rows=[{"type": "signal"}])["products"]["memecoins"]
    assert seen["now"] == NOW
    assert memes["n"] == 20 and memes["net_pct"] == -2.0 and memes["fee_pct"] == 0.0, memes
    assert memes["running"] == 7 and memes["could_buy_share"] == 0.6
    assert [f["fee_pct"] for f in memes["fees"]] == [0.0, 0.5, 1.0, 2.0]
    assert memes["wilson"] is not None


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_nexus_line_follows_his_questions_to_what_survived():
    said = _report()["nexus"]
    assert said == {**said, "questions": 5, "answered": 4, "gate_pass": 2,
                    "gated": 3, "survived": 1, "refuted": 1}, said
    # His picks by exact count, beside a room of ours that is not one: with
    # every fixture room a pick, `>= 3` passed a count of every room (deep
    # pass 2026-09-24, B08, 3/3).
    rooms = _fixture()["room_rows"] + [
        {"type": "strategy", "id": "STR-0099", "origin": "OUR-0001", "title": "ours"}]
    assert _report(room_rows=rooms)["nexus"]["picks"] == said["picks"] == 5, said
    # What still runs and what closed without a verdict, counted from his rooms
    # themselves -- not derived as gate passes minus verdicts, which mixed card
    # gates with bot verdicts and called a stopped room running (deep pass
    # 2026-09-27, R07, 3/3).
    assert said["running"] == 2 and said["inconclusive"] == 0, said
    unsure = _fixture()["room_rows"] + [
        {"type": "verdict", "room": "STR-0005", "verdict": "inconclusive"}]
    assert _report(room_rows=unsure)["nexus"]["inconclusive"] == 1


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_figure_the_report_writes_reaches_the_lab_page(monkeypatch):
    """A field the report writes and the page never reads is a figure nobody
    sees. The page names its shapes -- `lp.` a sector, `ln.` the Nexus line --
    and every product and Nexus field this report writes has to be read under
    them. (The other direction, a field read and never written, is held
    against lab_view() in test_pipeline_lab_page.py.)"""
    import re

    monkeypatch.setattr(lab_report.fomo, "ten_dollars", lambda rows, now=None: {
        "signals": 1, "window_open": 0, "could_buy_share": 1.0,
        "by_fee": {0.0: {"n": 1, "mean_net_pct": 1.0, "win_rate": 1.0}}})
    said = _report(fomo_rows=[{"type": "signal"}])
    written = {
        "lp": {k for p in said["products"].values() for k in p},
        "ln": set(said["nexus"]),
    }
    spec = importlib.util.spec_from_file_location(
        "lab_page_fields", REPO / "scripts" / "lab_page.py")
    page = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(page)
    # Fields the report still writes but the page hides ON PURPOSE: the operator
    # cut /lab down to results only (commits e7f95357, 943701cf: no dollars on
    # stake, no confidence band, no fee table). Named here, so a new field
    # nobody reads still fails; and each one must still be written, so this
    # list cannot outlive the field it excuses.
    hidden_on_purpose = {
        "lp": {"archived", "excluded", "fee_pct", "fees", "min_n", "stake_usdc",
               "switched", "usdc", "wilson", "wins"},
        "ln": {"answered", "inconclusive", "questions"},  # the one-line Nexus
    }
    for name, keys in written.items():
        read = set(re.findall(rf"\b{name}\.([A-Za-z_][A-Za-z0-9_]*)", page.TEMPLATE))
        excused = hidden_on_purpose[name]
        assert not keys - read - excused, (
            f"the report writes `{name}.` fields /lab never shows: "
            f"{sorted(keys - read - excused)}")
        assert not excused & read, (
            f"/lab shows `{name}.` fields this test lists as hidden on purpose: "
            f"{sorted(excused & read)} -- take them off the list")
        assert not excused - keys, (
            f"`{name}.` fields listed as hidden on purpose that the report no "
            f"longer writes: {sorted(excused - keys)} -- take them off the list")
    # Deep pass 2026-10-10, T07: the fields above are pooled across products, so a whole
    # product the page never draws counted as read through the cards' names. Each product the
    # report writes is a room the page draws, or named here: funds, which the operator stopped
    # measuring on 2026-10-03 (the page's SECTOR_NAMES says so). A new product fails.
    products_hidden_on_purpose = {"funds"}
    drawn = set(page.SECTOR_NAMES)
    assert not set(said["products"]) - drawn - products_hidden_on_purpose, (
        f"the report writes products /lab never draws: "
        f"{sorted(set(said['products']) - drawn - products_hidden_on_purpose)}")
    assert not products_hidden_on_purpose & drawn, "a product listed as hidden is drawn -- unlist it"
    assert products_hidden_on_purpose <= set(said["products"]), "unlist a product the report no longer writes"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_lab_py_report_writes_state_lab_report_json(tmp_path, monkeypatch):
    """`lab.py report` writes the one file the /lab page reads, from the
    diaries on this machine and nothing fetched."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    import qa.rooms
    import qa.state

    importlib.reload(qa.state)
    importlib.reload(lab)
    importlib.reload(qa.rooms)
    fx = _fixture()
    for name, rows in (("rooms.jsonl", fx["room_rows"]),
                       ("nexus.jsonl", fx["questions"] + fx["answers"]),
                       ("paper.jsonl", fx["paper_rows"]),
                       ("samples.jsonl", fx["sample_rows"]),
                       ("clones.jsonl", fx["clone_rows"]),
                       ("lab.jsonl", fx["notebook"])):
        (tmp_path / name).write_text(
            "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    spec = importlib.util.spec_from_file_location(
        "scripts_lab_report", REPO / "scripts" / "lab.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.main(["report"]) == 0
    written = json.loads((tmp_path / "lab" / "report.json")
                         .read_text(encoding="utf-8"))
    assert set(written["products"]) == {"cards", "bots", "memecoins", "funds"}
    assert written["products"]["cards"]["n"] == 2

    # R03 (deep pass of 2026-09-24, 3/3): /lab and /lab.json on the console's
    # threaded server, the tick and the morning page all write this file, and
    # all through ONE `report.json.tmp` -- on Windows a replace while another
    # writer held that tmp raised PermissionError (99 of 120 in a probe).
    # Every writer has its own tmp; the file is whole whoever wins.
    import threading
    failures = []

    def write(n):
        try:
            for i in range(15):
                module._write_text(tmp_path / "lab" / "race.json",
                                   json.dumps({"writer": n, "i": i}))
        except Exception as exc:  # noqa: BLE001 -- the assertion reads it
            failures.append(repr(exc))
    threads = [threading.Thread(target=write, args=(n,)) for n in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert failures == [], failures[:3]
    assert json.loads((tmp_path / "lab" / "race.json").read_text(encoding="utf-8"))

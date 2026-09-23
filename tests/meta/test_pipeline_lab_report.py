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
    assert cards["best"]["room"] == "STR-0001", cards
    assert cards["best"]["net_pct"] == pytest.approx(running_card)

    assert bots["n"] == 1 and bots["running"] == 1, bots
    assert bots["net_pct"] == pytest.approx(7.2 / 240.0 * 100.0), bots

    assert funds["n"] == 1 and funds["archived"] == 1, funds
    assert funds["net_pct"] == pytest.approx(-1.0), funds
    assert funds["best"]["room"] == "STR-0004"

    by_room = {r["id"]: r for r in said["rooms"]}
    assert by_room["STR-0005"]["archived"] is True
    assert by_room["STR-0005"]["net_pct"] is None


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
    signal, held a day, at 1% a side -- with 0.5 and 2 beside it and the
    share we could have bought ("stihli bychom")."""
    seen = {}

    def fake(rows, now=None, **kw):
        seen["now"] = now
        return {"signals": 40, "window_open": 7, "bought": 20,
                "could_buy_share": 0.6,
                "by_fee": {0.5: {"n": 20, "mean_net_pct": -3.0, "win_rate": 0.3},
                           1.0: {"n": 20, "mean_net_pct": -4.0, "win_rate": 0.25},
                           2.0: {"n": 20, "mean_net_pct": -6.0, "win_rate": 0.2}}}

    monkeypatch.setattr(lab_report.fomo, "ten_dollars", fake)
    memes = _report(fomo_rows=[{"type": "signal"}])["products"]["memecoins"]
    assert seen["now"] == NOW
    assert memes["n"] == 20 and memes["net_pct"] == -4.0, memes
    assert memes["running"] == 7 and memes["could_buy_share"] == 0.6
    assert [f["fee_pct"] for f in memes["fees"]] == [0.5, 1.0, 2.0]
    assert memes["wilson"] is not None


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_nexus_line_follows_his_questions_to_what_survived():
    said = _report()["nexus"]
    assert said == {**said, "questions": 5, "answered": 4, "gate_pass": 2,
                    "gated": 3, "survived": 1, "refuted": 1}, said
    assert said["picks"] >= 3, said


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_lab_page_reads_every_field_the_report_writes_and_no_other(
        monkeypatch):
    """Both directions. JavaScript reading a missing property is undefined,
    not an error, so a field the page reads and the report never writes draws
    "undefined" quietly; a field the report writes and the page never reads is
    a figure nobody sees. The page names its shapes -- `lp.` a product, `ln.`
    the Nexus line -- and this holds each against qa/lab_report.py."""
    import re

    monkeypatch.setattr(lab_report.fomo, "ten_dollars", lambda rows, now=None: {
        "signals": 1, "window_open": 0, "could_buy_share": 1.0,
        "by_fee": {1.0: {"n": 1, "mean_net_pct": 1.0, "win_rate": 1.0}}})
    said = _report(fomo_rows=[{"type": "signal"}])
    written = {
        "lp": {k for p in said["products"].values() for k in p},
        "ln": set(said["nexus"]),
    }
    spec = importlib.util.spec_from_file_location(
        "lab_page_fields", REPO / "scripts" / "lab_page.py")
    page = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(page)
    for name, keys in written.items():
        read = set(re.findall(rf"\b{name}\.([A-Za-z_][A-Za-z0-9_]*)", page.TEMPLATE))
        assert read, f"the page reads no `{name}.` field, so this proves nothing"
        assert not read - keys, (
            f"/lab reads `{name}.` fields the report never writes: "
            f"{sorted(read - keys)}")
        assert not keys - read, (
            f"the report writes `{name}.` fields /lab never shows: "
            f"{sorted(keys - read)}")


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

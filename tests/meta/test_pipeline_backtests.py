"""What has already been tested, so it is never tested twice.

[operator 2026-09-12] *"Coze? to jako nebylo osetreno? dyt jsem jasne na
zacaktu rikal ze se v laboratori ma vest denik at vi co uz se testovalo atd ne,
dyt to je kriticka cast."*

They had said it at the start. What was built was a diary of SESSIONS -- opened,
closed, what each one learned -- which is a record of our own activity and
answers a question nobody asked. The question is about the subject: which
basket, over which window, with what result. Without that, every night re-grinds
the same candidates and the months of work they are paying for accumulate
nothing.

The register is keyed on the BASKET, not on the run that measured it:

  * leg order cannot matter -- BTC+BCH and BCH+BTC are one basket;
  * nor can the scale of the weights, because their own tool renormalises them,
    so 1:1 and 0.5:0.5 are the same call with the same answer;
  * the window and the fee toggle DO matter: the same basket over 7 days and
    over 30 days answered -3.11% and +21.93% on 2026-09-12, which is the whole
    reason #97 existed.

And a result does not keep for ever, because the window slides: a 7-day
backtest run yesterday covers a different week today. It keeps for a tenth of
its own window, which is a day for a 7-day reading and a month for a yearly one.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent

BTC_BCH = [{"symbol": "BTC", "weight": 0.9962}, {"symbol": "BCH", "weight": 0.0038}]
NOW = datetime(2026, 9, 12, 12, 0, tzinfo=timezone.utc)


def _at(tmp_path, monkeypatch):
    import importlib

    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    import qa.state

    importlib.reload(qa.state)
    from qa import backtests

    importlib.reload(backtests)
    return backtests


def _scripts_lab(tmp_path, monkeypatch):
    """scripts/lab.py with its state under tmp_path; scripts/ is not a package."""
    import importlib.util

    _at(tmp_path, monkeypatch)
    spec = importlib.util.spec_from_file_location(
        "scripts_lab_backtest", REPO / "scripts" / "lab.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_one_basket_has_one_fingerprint_however_it_is_written():
    from qa import backtests

    straight = backtests.fingerprint(BTC_BCH, 30)
    assert straight == backtests.fingerprint(list(reversed(BTC_BCH)), 30), (
        "leg order is not part of a basket")
    assert straight == backtests.fingerprint(
        [{"symbol": "btc", "weight": 0.9962}, {"symbol": "bch", "weight": 0.0038}], 30)

    doubled = [{"symbol": "BTC", "weight": 1.9924}, {"symbol": "BCH", "weight": 0.0076}]
    assert straight == backtests.fingerprint(doubled, 30), (
        "their tool renormalises the weights, so the scale is not the basket")

    assert straight != backtests.fingerprint(BTC_BCH, 7), "the window is the basket"
    assert straight != backtests.fingerprint(BTC_BCH, 30, include_fees=True)
    assert straight != backtests.fingerprint(
        [{"symbol": "BTC", "weight": 0.5}, {"symbol": "BCH", "weight": 0.5}], 30), (
        "different proportions are a different basket")

    with pytest.raises(backtests.BacktestError):
        backtests.fingerprint([{"symbol": "BTC", "weight": 1.0}], 30)
    with pytest.raises(backtests.BacktestError):
        backtests.fingerprint(BTC_BCH, 45)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_what_was_tested_is_never_tested_again(tmp_path, monkeypatch):
    backtests = _at(tmp_path, monkeypatch)

    assert backtests.already(backtests.fingerprint(BTC_BCH, 30), now=NOW) is None

    row = backtests.record(BTC_BCH, 30, {
        "total_return_pct": 21.93, "sharpe_ratio": 5.47,
        "max_drawdown_pct": 4.82, "n_points": 29}, why="seed STR-0003", now=NOW)
    assert row["fp"] == backtests.fingerprint(BTC_BCH, 30)

    seen = backtests.already(row["fp"], now=NOW)
    assert seen and seen["s"] == 5.47 and seen["r"] == 21.93
    assert backtests.already(backtests.fingerprint(BTC_BCH, 7), now=NOW) is None, (
        "another window is another question")

    # The register is the memory, so it has to survive the process that wrote it.
    again = _at(tmp_path, monkeypatch)
    assert again.already(row["fp"], now=NOW), "the register did not survive a restart"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_result_keeps_for_a_tenth_of_its_own_window(tmp_path, monkeypatch):
    """The window slides. A 7-day reading taken yesterday covers a different
    week today; a 365-day reading barely moves. One rule for both, scaled, so
    the register neither freezes us on stale numbers nor re-runs everything
    every night."""
    backtests = _at(tmp_path, monkeypatch)

    week = backtests.record(BTC_BCH, 7, {"sharpe_ratio": -9.68}, now=NOW)
    year = backtests.record(BTC_BCH, 365, {"sharpe_ratio": 1.2}, now=NOW)

    later = NOW + timedelta(days=2)
    assert backtests.already(week["fp"], now=later) is None, (
        "a two-day-old seven-day reading is a different week")
    assert backtests.already(year["fp"], now=later), (
        "two days does not move a year")

    assert backtests.already(year["fp"], now=NOW + timedelta(days=40)) is None
    assert backtests.stale_after(7) == 1.0
    assert backtests.stale_after(365) == 30.0, "capped, or nothing ever refreshes"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_symbol_they_could_not_resolve_is_not_a_clean_reading(tmp_path,
                                                                monkeypatch):
    """Their answer carries `unresolved_symbols` and `dropped_symbols`. A basket
    measured without one of its legs is a measurement of a different basket, and
    ranking it beside clean ones would be us fabricating what they refused to."""
    backtests = _at(tmp_path, monkeypatch)

    clean = backtests.record(BTC_BCH, 30, {
        "sharpe_ratio": 5.47, "total_return_pct": 21.9, "n_points": 29}, now=NOW)
    partial = backtests.record(
        [{"symbol": "BTC", "weight": 0.5}, {"symbol": "NOSUCH", "weight": 0.5}], 30,
        {"sharpe_ratio": 9.99, "total_return_pct": 80.0, "n_points": 29,
         "unresolved_symbols": ["NOSUCH"]}, now=NOW)

    assert partial["lost"] == ["NOSUCH"] and clean.get("lost") in (None, [])
    ranked = backtests.best(backtests.load(), now=NOW)
    assert [r["fp"] for r in ranked][0] == clean["fp"], (
        "a 9.99 sharpe measured on half a basket outranked a real one")
    assert all(r.get("lost") in (None, []) for r in ranked), (
        "a partial reading is not a candidate at all")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_missing_number_is_missing_and_a_half_written_line_is_skipped(
        tmp_path, monkeypatch):
    backtests = _at(tmp_path, monkeypatch)

    ran = backtests.record(BTC_BCH, 30, {"total_return_pct": 4.0}, now=NOW)
    assert ran["s"] is None, "a sharpe they did not give is not a zero"
    assert backtests.best(backtests.load(), now=NOW) == [] or all(
        r["s"] is not None for r in backtests.best(backtests.load(), now=NOW)), (
        "an unranked row cannot lead the table")

    with open(backtests.path(), "a", encoding="utf-8") as handle:
        handle.write('{"fp": "half-writ')
    assert len(backtests.load()) == 1, "a torn line stopped the whole register"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_their_thirty_a_minute_is_ours_to_keep():
    """Their own document: "30/min per IP". Kept on our side of the wire, so a
    night that searches hard is refused by nobody -- and so the pace is a
    number in one place rather than a habit."""
    from qa import backtests

    start = 1_000_000.0
    assert backtests.next_slot([], start) == 0.0
    assert backtests.next_slot([start - 1] * 29, start) == 0.0

    full = [start - 10] * 30
    wait = backtests.next_slot(full, start)
    assert 49.0 <= wait <= 50.0, wait

    stale = [start - 120] * 30
    assert backtests.next_slot(stale, start) == 0.0, (
        "calls that fell out of the window still counted against us")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_basket_the_register_knows_is_not_asked_again(tmp_path, monkeypatch):
    """The whole point, end to end: the call is not made."""
    backtests = _at(tmp_path, monkeypatch)
    lab = _scripts_lab(tmp_path, monkeypatch)
    asked = []

    def _call(constituents, period_days, **_):
        asked.append((len(constituents), period_days))
        return {"total_return_pct": 21.93, "sharpe_ratio": 5.47,
                "max_drawdown_pct": 4.82, "n_points": 29}

    first = lab.backtest(BTC_BCH, 30, call=_call, now=NOW)
    assert first["cached"] is False and len(asked) == 1

    again = lab.backtest(list(reversed(BTC_BCH)), 30, call=_call, now=NOW)
    assert again["cached"] is True, "it asked them the same question twice"
    assert len(asked) == 1
    assert again["s"] == 5.47

    other = lab.backtest(BTC_BCH, 7, call=_call, now=NOW)
    assert other["cached"] is False and len(asked) == 2, "a window is a question"

    later = lab.backtest(BTC_BCH, 7, call=_call,
                         now=NOW + timedelta(days=3))
    assert later["cached"] is False and len(asked) == 3, (
        "a three-day-old seven-day reading is a different week")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_seeds_are_their_own_cards_as_the_sampler_recorded_them(tmp_path,
                                                                    monkeypatch):
    """The sampler already writes each card's basket in exactly the shape their
    backtest takes -- `basket: [{"symbol": "BTC", "weight": 0.9962}]` -- so the
    search starts from their cards rather than from anything we invented."""
    lab = _scripts_lab(tmp_path, monkeypatch)
    rows = [
        {"type": "card", "card_id": "c-1", "title": "Bitcoin hack",
         "basket": [{"symbol": "BTC", "weight": 0.9962},
                    {"symbol": "BCH", "weight": 0.0038}]},
        {"type": "card", "card_id": "c-2", "title": "One leg only",
         "basket": [{"symbol": "ETH", "weight": 1.0}]},
        {"type": "tick", "at": "2026-09-12T00:00:00+00:00"},
        {"type": "card", "card_id": "c-1", "title": "Bitcoin hack, later",
         "basket": [{"symbol": "BTC", "weight": 0.5},
                    {"symbol": "OKB", "weight": 0.5}]},
    ]
    (tmp_path / "samples.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    seeds = lab.card_baskets()
    assert [s["card"] for s in seeds] == ["c-1"], (
        "a one-leg card is not a basket their tool accepts, and a card's "
        "newest basket is the one it has")
    assert seeds[0]["legs"][0]["symbol"] in ("BTC", "OKB")
    assert len(seeds[0]["legs"]) == 2
    assert "later" in seeds[0]["title"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_search_walks_around_their_idea_and_never_away_from_it():
    """What the search is allowed to vary, and in what order.

    Every move is a question about THEIR basket: does it hold over another
    window, does the weighting carry it, does it stand on one leg. None of them
    invents a strategy -- CLAUDE.md: a strategy of ours never becomes a room --
    and the order is cheapest-question-first so a night cut short still
    answered the useful ones.
    """
    from qa import backtests

    seed = {"card": "c-1", "title": "Bitcoin hack",
            "legs": [{"symbol": "BTC", "weight": 0.7},
                     {"symbol": "BCH", "weight": 0.2},
                     {"symbol": "OKB", "weight": 0.1}]}
    moves = backtests.neighbourhood(seed, pool=["ETH", "SOL"], cap=40)
    kinds = [m["kind"] for m in moves]

    assert kinds[:5] == ["window"] * 5, kinds[:8]
    assert {m["period"] for m in moves if m["kind"] == "window"} == set(
        backtests.PERIODS)
    assert "equal" in kinds and "drop" in kinds and "add" in kinds
    assert kinds.index("equal") < kinds.index("drop") < kinds.index("add")

    dropped = [m for m in moves if m["kind"] == "drop"]
    assert len(dropped) == 3, "one move per leg, so a basket cannot hide a leg"
    assert all(len(m["legs"]) == 2 for m in dropped)

    added = [m for m in moves if m["kind"] == "add"]
    assert {leg["symbol"] for m in added for leg in m["legs"]} >= {"ETH", "SOL"}

    # Deterministic, or a night cannot resume where the last one stopped.
    assert moves == backtests.neighbourhood(seed, pool=["SOL", "ETH"], cap=40)

    # A two-leg basket has no leg to drop: their tool takes two at least.
    small = {"card": "c-2", "legs": [{"symbol": "BTC", "weight": 1},
                                     {"symbol": "ETH", "weight": 1}]}
    assert not [m for m in backtests.neighbourhood(small, pool=[], cap=40)
                if m["kind"] == "drop"]

    assert len(backtests.neighbourhood(seed, pool=["ETH", "SOL"], cap=7)) == 7


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_seed_already_answered_is_not_walked_again(tmp_path, monkeypatch):
    backtests = _at(tmp_path, monkeypatch)
    lab = _scripts_lab(tmp_path, monkeypatch)

    seed = {"card": "c-1", "title": "x",
            "legs": [{"symbol": "BTC", "weight": 0.7},
                     {"symbol": "BCH", "weight": 0.3}]}
    asked = []

    def _call(constituents, period_days, **_):
        asked.append(period_days)
        return {"sharpe_ratio": 1.0, "total_return_pct": 2.0, "n_points": 29}

    first = lab.search([seed], pool=[], cap=5, call=_call, now=NOW)
    assert first["asked"] == 5 and len(asked) == 5

    again = lab.search([seed], pool=[], cap=5, call=_call, now=NOW)
    assert again["asked"] == 0 and again["from_register"] == 5, again
    assert len(asked) == 5, "the second walk re-asked what the register held"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_search_holds_no_hand_that_trades_or_opens_a_room():
    """A basket the search composed is a MEASUREMENT. The road from "the
    backtest found it" to "it is on paper" runs through a question to Nexus,
    and a room opens only from his answer -- so the search itself cannot reach
    the doors that would shortcut that."""
    import ast

    source = (REPO / "scripts" / "lab.py").read_text(encoding="utf-8")
    wanted = {"search", "backtest", "_backtest_call", "card_baskets",
              "symbol_pool", "_samples"}
    found = []
    for node in ast.parse(source).body:
        if not isinstance(node, ast.FunctionDef) or node.name not in wanted:
            continue
        # Read the CODE, not the prose. A guard that fires on a docstring is
        # one somebody gets past by rewording, which teaches the wrong lesson
        # -- and this one did exactly that on its first run, over the sentence
        # explaining why the search may not trade.
        body = list(node.body)
        if (body and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)):
            body = body[1:]
        found.append(node.name)
        code = "\n".join(ast.unparse(stmt) for stmt in body)
        for hand in ("buy", "open_strategy", "set_status", "set_acceptance",
                     "paper", "place_order", "record_verdict", "submit"):
            assert hand not in code, (
                f"{node.name} can reach {hand!r}: it measures, Nexus proposes")
    assert wanted <= set(found), f"the slice moved: {sorted(set(wanted) - set(found))}"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_register_is_outside_git_and_inside_the_snapshot():
    """Months of work on one disk is the failure this guards. It lives beside
    the other diaries for the same reason they do -- it is appended to while a
    run may be in flight, and a dirty tree costs a level-V run -- and
    `keep.py snapshot` is what stops that meaning one disk."""
    ignored = (REPO / ".gitignore").read_text(encoding="utf-8")
    assert "state/backtests.jsonl" in ignored

    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "keep_for_register", REPO / "scripts" / "keep.py")
    keep = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(keep)
    assert "backtests.jsonl" in keep.DIARIES, (
        "the register would live on one disk and die with it")

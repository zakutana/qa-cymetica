"""The Gem Screener audit can say "no" before it is trusted to say "yes".

`qa/gemaudit.py` holds the pure parts of the degen's audit (2026-09-30) and the
checks in `tests/rest/test_gem_screener_*.py` judge live data with them. A check
that passed on its first run proves nothing on its own -- the live numbers were
all fine that day -- so each judgement is refuted here, offline, on data built to
be wrong in exactly the way the check exists to catch, and each is shown to let
ordinary drift through.
"""

from __future__ import annotations

import pytest

from qa import gemaudit as g
from qa.marks import SafetyTier, qa


class _Response:
    def __init__(self, status=200, body=None):
        self.status_code, self._body = status, body

    def json(self):
        if self._body is None:
            raise ValueError("not json")
        return self._body


def _pairs(n, dev=0.0, bad=0, bad_dev=0.4):
    """n (label, page, source) rows with a small spread; the first `bad` rows
    are `bad_dev` off."""
    return [(f"c{i}", 100.0 * (1 + (bad_dev if i < bad else dev * ((-1) ** i))), 100.0)
            for i in range(n)]


def _judge(pairs, total=None, **kw):
    summary = g.deviation_summary(pairs, tail=0.25)
    return g.judge_deviation(summary, total or len(pairs), min_compared_share=0.9,
                             max_median=kw.get("max_median", 0.05),
                             max_tail_share=kw.get("max_tail_share", 0.05))[0]


def _a_column_is_judged_as_a_population_not_as_a_coin():
    """One coin 40 % off is the world moving or a source correcting itself (the
    day this was written CoinGecko re-estimated PHAR's supply down by a fifth).
    A median that has moved, a tenth of the rows far off, or half the rows
    unreadable is a pipeline -- and unreadable is "inconclusive", never passed."""
    assert _judge(_pairs(100, dev=0.02)) == "passed", "ordinary drift failed"
    assert _judge(_pairs(100, dev=0.02, bad=1)) == "passed", (
        "a single far-off coin failed a whole column")
    assert _judge(_pairs(100, dev=0.02, bad=10)) == "failed", (
        "a tenth of the rows 40 % off passed")
    assert _judge([(n, p * 1.10, s) for n, p, s in _pairs(100)]) == "failed", (
        "every row 10 % high passed: the median moved and nothing said so")

    half_blind = _pairs(50) + [(f"x{i}", None, 100.0) for i in range(50)]
    assert _judge(half_blind, total=100) == "inconclusive", (
        "half the rows had no page value and the column was still judged")
    summary = g.deviation_summary(half_blind, tail=0.25)
    assert summary["n"] == 50 and summary["skipped"] == 50, summary
    zero = g.deviation_summary([("a", 100.0, 0.0), ("b", 0.0, 100.0), ("c", 100.0, 100.0)], tail=0.25)
    assert zero["n"] == 1 and zero["skipped"] == 2, (
        "a zero on either side was compared as a deviation")


def _snapshot(apps, **extra):
    snap = {"generated_at": 1_000_000, "bench": {"mult": 30.0, "fdv_mult": 100.0},
            "apps": apps, "degen": {"shortlist": []}, "risk_rules": {"max_impact_pct": 3.0}}
    snap.update(extra)
    return snap


def _app(key, symbol, ps, **kw):
    raw = 30.0 / ps
    app = {"key": key, "symbol": symbol, "name": symbol.title(), "slug": symbol.lower(),
           "gecko_id": symbol.lower(), "ps": ps, "potential_raw": raw,
           "potential": min(raw, 50.0), "bench_capped": raw > 50.0, "price": 1.0,
           "cg": {"circ": 1000.0, "total": 2000.0}, "mcap": 1000.0, "fdv": 2000.0,
           "rev30d": 100.0, "reliable": True}
    app.update(kw)
    return app


def _the_upside_check_sees_a_wrong_multiple_and_a_wrong_cap():
    """`potential_raw = bench.mult / ps`, shown as `min(raw, cap)`. Rows that
    follow it pass; a row with another multiple, a capped row that shows more than
    the cap, and a row shown under its raw value are breaches."""
    good = _snapshot([_app("a#1", "AAA", 2.0), _app("a#2", "BBB", 0.3)])
    said = g.upside_breaches(good)
    assert said["breaches"] == [] and said["checked"] == 2 and said["cap"] == 50.0, said

    wrong_multiple = _snapshot([_app("a#1", "AAA", 2.0, potential_raw=12.0, potential=12.0)])
    assert [b["what"] for b in g.upside_breaches(wrong_multiple)["breaches"]] == [
        "potential_raw is not bench.mult / ps"], "a raw upside of 12 for ps 2.0 (15 expected) passed"

    over_cap = _snapshot([_app("a#1", "AAA", 0.3), _app("a#2", "BBB", 0.2, potential=80.0)])
    assert any(b["row"].startswith("BBB") and b["what"] == "shown upside is not min(raw, cap)"
               for b in g.upside_breaches(over_cap)["breaches"]), (
        "a capped row showing 80 beside a cap of 50 passed")

    under = _snapshot([_app("a#1", "AAA", 2.0, potential=9.0)])
    assert g.upside_breaches(under)["breaches"], "a shown value below its raw value passed"

    # Deep pass 2026-10-02 (T08): "on every row that has a ps". A row that shows an upside
    # but carries no potential_raw is still held to min(bench.mult / ps, cap).
    no_raw_wrong = _snapshot([_app("a#1", "AAA", 2.0, potential_raw=None, potential=9.0)])
    assert [b["what"] for b in g.upside_breaches(no_raw_wrong)["breaches"]] == [
        "shown upside is not min(raw, cap)"], "a shown 9 for ps 2.0 (15 expected) with no raw passed"
    no_raw_right = _snapshot([_app("a#1", "AAA", 2.0, potential_raw=None, potential=15.0)])
    said = g.upside_breaches(no_raw_right)
    assert said["breaches"] == [] and said["checked"] == 1, said

    # Rounding is not a breach: a tiny number published to three decimals.
    tiny = _snapshot([_app("a#1", "AAA", 12000.0, potential_raw=0.0025, potential=0.0025)])
    assert g.upside_breaches(tiny)["breaches"] == [], "rounding of a tiny upside failed"
    with pytest.raises(g.SnapshotUnreadable):
        g.upside_breaches({"bench": {}, "apps": [_app("a#1", "AAA", 2.0)]})

    # C06, deep pass of 2026-09-30 (3/3): a benchmark whose market cap or
    # run-rate cannot be read is an unreadable snapshot, the same colour as a
    # missing multiple -- never a breach of the formula.
    with pytest.raises(g.SnapshotUnreadable):
        g.benchmark_arithmetic({"bench": {"mult": 30.0, "mcap": 1e9}})
    assert g.benchmark_arithmetic({"bench": {"mult": 10.0, "mcap": 1e9, "rr": 1e8}}) == []
    assert g.benchmark_arithmetic({"bench": {"mult": 12.0, "mcap": 1e9, "rr": 1e8}}), (
        "a benchmark multiple that is not its market cap over its run-rate passed")

    # R06 (3 of 3... 2 of 3): the report's table survives a capped row without a
    # raw value and states the cap the check judges by, the most common shown.
    table = g.upside_table(_snapshot([_app("c#1", "CCC", 0.3), _app("c#2", "DDD", 0.2, potential_raw=None)]))
    assert table["raw_range_at_cap"] == [100.0, 100.0], table
    odd = _snapshot([_app("c#1", "CCC", 0.3), _app("c#3", "EEE", 0.25),
                     _app("c#4", "FFF", 0.2, potential=80.0)])
    assert g.upside_table(odd)["cap"] == 50.0 == g.upside_breaches(odd)["cap"], g.upside_table(odd)


def _a_pick_that_opens_another_coin_is_seen_and_a_shared_ticker_is_named():
    """2026-09-30: the Degen pick "Definitive" (EDGE) linked to `?coin=EDGE` and
    the symbol route answered edgeX, a different token with six times the market
    cap. The match is by name and market cap, because the ticker is exactly what
    two apps share."""
    pick = {"symbol": "EDGE", "name": "Definitive", "market_cap": {"value": 29_000_000.0}}
    same = {"EDGE": {"name": "definitive", "market_cap": {"value": 29_100_000.0}}}
    assert g.pick_identity_breaches([pick], same) == [], "the same coin, read a minute later, was a breach"

    other = {"EDGE": {"name": "edgeX", "market_cap": {"value": 182_000_000.0}}}
    found = g.pick_identity_breaches([pick], other)
    assert [b["row"] for b in found] == ["EDGE"] and found[0]["opens"] == "edgeX", found

    same_name_other_cap = {"EDGE": {"name": "Definitive", "market_cap": {"value": 60_000_000.0}}}
    assert g.pick_identity_breaches([pick], same_name_other_cap), (
        "the same name with double the market cap passed")
    assert g.pick_identity_breaches([pick], {})[0]["what"] == "the coin route could not be read", (
        "a coin that could not be read was counted as matching")

    # #140, fixed 2026-10-01: the pick links by slug (`?coin=definitive`), and
    # our report promised the check clears "as soon as the link carries the
    # slug". It kept opening the TICKER and would have sent them a false fail.
    linked = dict(pick, slug="definitive",
                  detail_url="https://cymetica.com/gem-screener?coin=definitive")
    assert g.pick_key(linked) == "definitive" and g.pick_key(pick) == "EDGE"
    assert g.pick_key(dict(pick, slug="definitive")) == "definitive"
    by_link = {"definitive": {"name": "Definitive", "market_cap": {"value": 29_100_000.0}},
               "EDGE": {"name": "edgeX", "market_cap": {"value": 182_000_000.0}}}
    assert g.pick_identity_breaches([linked], by_link) == [], (
        "a pick whose link opens its own coin was judged by its ticker")
    wrong_link = dict(linked, detail_url="https://cymetica.com/gem-screener?coin=edgex")
    by_link["edgex"] = by_link["EDGE"]
    assert [b["row"] for b in g.pick_identity_breaches([wrong_link], by_link)] == ["edgex"], (
        "a link that opens another coin passed")

    snap = _snapshot([_app("leaf#1", "EDGE", 2.0, name="Definitive"),
                      _app("parent#edgex", "EDGE", 3.0, name="edgeX"), _app("a#3", "ZZZ", 1.0)])
    shared = g.duplicate_tickers(snap)
    assert list(shared) == ["EDGE"] and len(shared["EDGE"]) == 2, shared


def _the_altseason_numbers_are_held_to_their_own_published_rules():
    """The composite follows the weights the snapshot publishes, the headline
    breadth is the 4-week mean of the weekly series the CYCLE publishes
    (`altseason_cycle.series.breadth`), and `beat / n` is its latest reading. A
    field that is missing is unread -- it never agrees.

    2026-10-04: the mean was read from the legacy `altseason.history`, a second
    breadth series that runs 2-4 points above the cycle's own in every one of the
    last six weeks (44/42, 32/28, 40/38, 36/34, 60/56, 72/68), so two checks failed
    on a live page whose numbers were consistent. The fixture keeps that gap on
    purpose: a mean read from the legacy block fails here."""
    def snap(**cyc):
        c = {"index": 28.1, "rotation": 16.5, "euphoria": 51.5,
             "rules": {"rot_weight": 2, "euph_weight": 1},
             "series": {"breadth": [30.0, 38.0, 34.0, 56.0, 68.0]},
             "components": {"breadth": {"value": 68.0, "mean4": 49.0, "beat": 34, "n": 50}}}
        c.update(cyc)
        return {"altseason_cycle": c, "altseason": {"index": 72.0,
                "history": [[1, 40.0, 50], [2, 36.0, 50], [3, 60.0, 50], [4, 72.0, 50]]}}

    assert g.altseason_breaches(snap()) == {"breaches": [], "unread": []}
    assert g.altseason_breaches(snap(index=41.0))["breaches"][0]["what"].startswith(
        "the altseason index is not"), "an index of 41 for rotation 16.5 and euphoria 51.5 passed"

    # Weights come from the rules: the same inputs at equal weights give 34, not 28.
    equal = snap(rules={"rot_weight": 1, "euph_weight": 1})
    assert g.altseason_breaches(equal)["breaches"], (
        "the weights were assumed instead of read from the rules")

    wrong_mean = snap(components={"breadth": {"value": 68.0, "mean4": 60.0, "beat": 34, "n": 50}})
    assert [b["what"] for b in g.altseason_breaches(wrong_mean)["breaches"]] == [
        "breadth mean4 is not the mean of the last four weeks"]
    wrong_beat = snap(components={"breadth": {"value": 68.0, "mean4": 49.0, "beat": 20, "n": 50}})
    assert any(b["what"] == "breadth value is not beat / n" for b in g.altseason_breaches(wrong_beat)["breaches"])

    # The component's value is the last point of the series it is the mean of.
    stale_series = snap(series={"breadth": [30.0, 38.0, 34.0, 56.0, 60.0]})
    assert "breadth value is not the last point of its own series" in [
        b["what"] for b in g.altseason_breaches(stale_series)["breaches"]]

    # Deep pass 2026-10-02 (T17) added a fourth judgement: `altseason.index` must equal the
    # breadth component. NOT a published rule -- it is a second, older block on a different
    # basis (72.0 against 68.0 for the same week, +2..4 every week), so on 2026-10-04 it
    # failed a consistent page. A difference between the two is not a breach.
    off = snap()
    off["altseason"]["index"] = 40.0
    assert g.altseason_breaches(off)["breaches"] == [], (
        "the legacy altseason.index was held to equal the cycle's breadth, which nothing publishes")

    blind = snap(rules={})
    said = g.altseason_breaches(blind)
    assert said["breaches"] == [] and said["unread"], (
        "missing weights read as agreement instead of unread")

    # No weekly series is unread, never an agreement and never a mean over the legacy block.
    no_series = snap()
    del no_series["altseason_cycle"]["series"]
    said = g.altseason_breaches(no_series)
    assert said["breaches"] == [] and said["unread"], "a missing series read as agreement"

    # A week with no reading does not break the mean while three weeks remain.
    gappy = snap(series={"breadth": [30.0, 38.0, None, 56.0, 68.0]})
    gappy["altseason_cycle"]["components"]["breadth"]["mean4"] = 54.0
    assert g.altseason_breaches(gappy)["breaches"] == [], "a gap in the history failed the mean"


def _a_source_that_fails_is_never_an_empty_answer_and_the_joins_group_as_defillama_does():
    """A 429 is `SourceUnavailable`, not a list with nothing in it; a chain whose
    DexScreener request failed is named; a parent app's revenue is the sum of its
    children and a leaf's is the protocol with its id."""
    with pytest.raises(g.SourceUnavailable, match="429"):
        g.fetch_coingecko(lambda *a, **k: _Response(429, {"status": "rate limited"}), ["a"])
    with pytest.raises(g.SourceUnavailable, match="not JSON"):
        g.fetch_llama_revenue(lambda *a, **k: _Response(200, None))
    with pytest.raises(g.SourceUnavailable):
        g.fetch_llama_revenue(lambda *a, **k: _Response(200, {"protocols": []}))

    slept = []
    calls = []

    def cg(url, params=None):
        calls.append(params["ids"])
        return _Response(200, [{"id": i} for i in params["ids"].split(",")])

    rows = g.fetch_coingecko(cg, [f"id{i}" for i in range(5)], chunk=2, pause=1.5, sleep=slept.append)
    assert len(rows) == 5 and len(calls) == 3 and slept == [1.5, 1.5], (
        "the ids were not chunked, or the chunks were not spaced out")

    def dex(url):
        if "/bsc/" in url:
            return _Response(500, None)
        return _Response(200, {"pairs": [{"pairAddress": "0xAB", "liquidity": {"usd": 10.0}}]})

    found, failed = g.fetch_dexscreener(dex, [("solana", "0xab"), ("bsc", "0xcd")], sleep=lambda s: None)
    assert failed == ["bsc"] and ("solana", "0xab") in found, (found, failed)

    snap = _snapshot([_app("parent#p", "PAR", 1.0, rev30d=300.0), _app("leaf#7", "LEF", 1.0, rev30d=50.0),
                      _app("leaf#8", "NON", 1.0)])
    protocols = [{"defillamaId": "1", "parentProtocol": "parent#p", "total30d": 100.0},
                 {"defillamaId": "2", "parentProtocol": "parent#p", "total30d": 200.0},
                 {"defillamaId": "7", "total30d": 50.0}]
    by_label = {name: (page, source) for name, page, source in g.revenue_pairs(snap, protocols)}
    assert by_label["PAR(parent#p)"] == (300.0, 300.0), by_label
    assert by_label["LEF(leaf#7)"] == (50.0, 50.0), by_label
    assert "NON(leaf#8)" not in by_label, "an app DefiLlama does not list was compared with something"

    html = ('<html><script id="snapshot-data" type="application/json">'
            '{"apps": [{"key": "a#1"}]}</script></html>')
    assert g.parse_snapshot(html)["apps"][0]["key"] == "a#1"
    with pytest.raises(g.SnapshotUnreadable):
        g.parse_snapshot("<html>no data</html>")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_audit_judges_columns_as_populations_and_fails_loudly_when_a_source_does():
    """A column of pairs is a population, not a coin; a source that does not
    answer is never an empty answer; and the joins group as DefiLlama does."""
    _a_column_is_judged_as_a_population_not_as_a_coin()
    _a_source_that_fails_is_never_an_empty_answer_and_the_joins_group_as_defillama_does()


def _the_derived_figures_are_held_to_their_definitions():
    """Each identity `derived_identities` recomputes, refuted on one row built to
    break exactly that one, and let through on the same row made right. A row
    that lacks an input is skipped -- `checked` says how many were read."""
    def breaches(apps=(), name=None, coins=None, **extra):
        snap = _snapshot(list(apps), **extra)
        by = {i["name"]: i for i in g.derived_identities(snap, coins)}
        return by[name]

    # ps = market cap / run-rate
    ok = {"runrate": {"value": 100.0}, "ps": 5.0, "mcap": 500.0, "symbol": "A"}
    assert breaches([ok], "ps")["breaches"] == [] and breaches([ok], "ps")["checked"] == 1
    assert breaches([dict(ok, ps=6.0)], "ps")["breaches"] == ["A"], "a P/S of 6 for 500 / 100 passed"
    assert breaches([{"symbol": "B"}], "ps")["checked"] == 0, "a row with no inputs was counted as read"

    # earnings after emissions, and the 'printed' flag
    e = {"emissions30d": 40.0, "rev30d": 100.0, "earnings30d": 60.0, "printed": False, "symbol": "E"}
    assert breaches([e], "earnings")["breaches"] == []
    assert breaches([dict(e, earnings30d=50.0)], "earnings")["breaches"] == ["E"]
    assert breaches([dict(e, printed=True)], "earnings")["breaches"] == ["E"], (
        "'printed' on a row whose emissions are below its revenue passed")

    # 30x test
    t = {"symbol": "T", "mcap": 1000.0, "test30": {"mult": 30, "implied": 30000.0, "ceiling": 90000.0,
                                                   "room_x": 90.0, "size_ok": True}}
    assert breaches([t], "30x test")["breaches"] == []
    assert breaches([dict(t, test30=dict(t["test30"], size_ok=False))], "30x test")["breaches"] == ["T"]
    assert breaches([dict(t, test30=dict(t["test30"], implied=40000.0))], "30x test")["breaches"] == ["T"]

    # slippage and the liquidity pass rule
    liq = {"symbol": "L", "liq": {"ticket": 10000.0, "pair_liq_usd": 500000.0, "impact_pct": 4.0,
                                  "vol24h": 0.0, "ok": False}}
    assert breaches([liq], "liquidity", risk_rules={"max_impact_pct": 3.0, "vol_pass": 2e6})["breaches"] == []
    wrong = dict(liq, liq=dict(liq["liq"], ok=True))
    assert breaches([wrong], "liquidity", risk_rules={"max_impact_pct": 3.0, "vol_pass": 2e6})["breaches"] == ["L"], (
        "a 4 % slippage on 10K passed the 3 % rule")
    assert breaches([dict(liq, liq=dict(liq["liq"], impact_pct=9.0))], "liquidity",
                    risk_rules={"max_impact_pct": 3.0, "vol_pass": 2e6})["breaches"] == ["L"], (
        "a slippage that is not 100 x ticket / (pool / 2) passed")

    # the Degen gates
    rules = {"degen": {"rules": {"min_rev30": 100000, "min_potential": 2.5}}}
    small = {"symbol": "G", "rev30d": 50000.0, "potential": 10.0, "reliable": True, "degen_ok": False,
             "degen_fail": ["small_business"]}
    assert breaches([small], "degen gates", **rules)["breaches"] == []
    assert breaches([dict(small, degen_fail=[])], "degen gates", **rules)["breaches"] == ["G"], (
        "a business under the revenue floor with no failed gate passed")
    assert breaches([dict(small, degen_ok=True)], "degen gates", **rules)["breaches"] == ["G"], (
        "a pick with a failed gate passed")

    # themes and chains
    theme = {"theme_4w": 0.5, "btc_4w": 0.1, "rs1m": 0.3636, "hot": True, "symbol": "th"}
    assert breaches(name="themes", altseason={"alt_4w_median": 0.2}, themes=[theme])["breaches"] == []
    assert breaches(name="themes", altseason={"alt_4w_median": 0.2},
                    themes=[dict(theme, hot=False)])["breaches"] == ["th"]
    assert breaches(name="themes", altseason={"alt_4w_median": 0.2},
                    themes=[dict(theme, rs1m=0.4)])["breaches"] == ["th"]
    # 2026-10-03: they made `hot` mean the stage (#144). With a stage on the row it is the
    # stage that holds the flag -- the four-week rule no longer does, or four correct
    # themes read as breaches -- and a flag against its own stage is one.
    staged = dict(theme, stage="hot", theme_4w=0.05, rs1m=-0.0455)  # not ahead of the median alt
    assert breaches(name="themes", altseason={"alt_4w_median": 0.2}, themes=[staged])["breaches"] == []
    assert breaches(name="themes", altseason={"alt_4w_median": 0.2},
                    themes=[dict(staged, stage="falling")])["breaches"] == ["th"]
    chain = {"name": "C", "activity": {"value": 100.0}, "mcap": 500.0, "ps": 5.0, "potential_raw": 4.0}
    bench = {"bench_chains": {"mult": 20.0, "fee_mult": 100.0}}
    assert breaches(name="chains", chains=[chain], **bench)["breaches"] == []
    assert breaches(name="chains", chains=[dict(chain, potential_raw=9.0)], **bench)["breaches"] == ["C"]
    # 2026-10-01 (ET-28606): chains are priced on adoption (daily users x fees),
    # so price/activity is market cap over `adoption.value`, not over the fees.
    # Judging the new snapshot by the old basis called all 20 priced chains
    # breaches; a chain with no user count has no price tag and is not judged.
    adopted = dict(chain, adoption={"value": 50.0}, ps=10.0, potential_raw=2.0)
    assert breaches(name="chains", chains=[adopted], **bench)["breaches"] == [], (
        "a chain priced on adoption was judged by its fees")
    assert breaches(name="chains", chains=[dict(adopted, ps=5.0, potential_raw=4.0)],
                    **bench)["breaches"] == ["C"], "a chain still priced on fees passed under the adoption basis"
    unpriced = {k: v for k, v in adopted.items() if k not in ("ps", "potential_raw")}
    assert breaches(name="chains", chains=[unpriced], **bench)["breaches"] == []

    # the level is round(10 x the weighted mean of its areas), inside its range
    level = {"X": {"degen_level": {"level": 6, "low": 5, "high": 9, "areas": [{"weight": 1.0, "value": 0.6}]}}}
    assert breaches(name="degen level", coins=level)["breaches"] == []
    bad = {"X": {"degen_level": {"level": 7, "low": 5, "high": 9, "areas": [{"weight": 1.0, "value": 0.6}]}}}
    assert breaches(name="degen level", coins=bad)["breaches"] == ["X"]

    # the multipliers the page states are read from its words, and compared with what it applies
    assert g.stated_runrate_factors("<b>last 30 days</b> x 12, last 90 days × 4, twelve times the median") == {30: 12.0, 90: 4.0}
    assert round(g.stated_runrate_factors("last 30 days × 365/30")[30], 4) == 12.1667
    assert g.stated_runrate_factors("no multipliers here") == {}
    # #141, fixed 2026-10-01: the page now says "a day's average over the last
    # 30 days x 365" and its tooltips "last 30 days, a day's average x 365".
    # The reader took "last 30 days x 365" and failed their fix at x 365.
    legend = ("right now: a day’s average over the last 30 days × 365, the same "
              "over the last 90 days × 365, and twelve times the median")
    tips = ("'30d': ['last 30 days, a day’s average × 365'], "
            "'90d': ['last 90 days, a day's average × 365']")
    for words in (legend, tips, legend + " " + tips):
        said = {d: round(f, 4) for d, f in g.stated_runrate_factors(words).items()}
        assert said == {30: 12.1667, 90: 4.0556}, (words[:40], said)
    row = _app("a#1", "AAA", 1.0, rev30d=100.0, runrate={"value": 1216.67, "basis": "30d"})
    assert len(g.runrate_factor_breaches(_snapshot([row]), {30: 12.0})["breaches"]) == 1, (
        "a run-rate of 12.1667 x revenue passed against a stated x 12")
    assert g.runrate_factor_breaches(_snapshot([row]), {30: 365 / 30})["breaches"] == [], (
        "the stated factor was assumed, not read")
    assert g.runrate_factor_breaches(_snapshot([row]), {})["checked"] == 0, "an unread tooltip was read as agreeing"

    # a figure shown as 100 % to holders while their holders revenue exceeds the total
    over = _app("a#2", "OVR", 1.0, holders30d=150.0, total30d=100.0, holders_share=1.0)
    assert [c["row"] for c in g.holders_clipped(_snapshot([over]))] == ["OVR(a#2)"]
    # R08, deep pass of 2026-09-30: "clipped" is the SHOWN share at 100 %. A page
    # that shows the true 120 % is not clipping anything.
    shown = _app("a#4", "UNC", 1.0, holders30d=120.0, total30d=100.0, holders_share=1.2)
    assert g.holders_clipped(_snapshot([shown])) == [], "a share shown as 120 % was called clipped to 100 %"

    # ET-28597 item 5 (2026-10-10): `runrate.cov30` is how many of the last 30
    # days the revenue rests on. KNC said 30 with 11 of them absent from its own
    # `rev_series`, so its run-rate and P/S counted those days as earning nothing
    # while `sparse` stayed false. A day present at 0 is a day with data.
    day0 = 1_790_000_000 - 1_790_000_000 % 86400
    def served(n_missing, cov30, zero_day=False):
        kept = [i for i in range(40) if not (5 <= i < 5 + n_missing)]
        series = [[day0 - 86400 * i, 0.0 if zero_day and i == 1 else 10.0] for i in sorted(kept, reverse=True)]
        return _app(f"c#{n_missing}", f"C{n_missing}", 1.0, rev_series=series,
                    runrate={"value": 1.0, "basis": "30d", "cov30": cov30, "sparse": False})
    seen = g.coverage_breaches(_snapshot([served(11, 30)]))
    assert seen["checked"] == 1 and [b["row"] for b in seen["breaches"]] == ["C11(c#11)"], seen
    assert seen["breaches"][0]["present"] == 19 and seen["breaches"][0]["cov30"] == 30, seen
    assert g.coverage_breaches(_snapshot([served(0, 30, zero_day=True)]))["breaches"] == [], (
        "a day present at 0 was read as a missing day")
    assert g.coverage_breaches(_snapshot([served(11, 19)]))["breaches"] == [], (
        "a row that states its 19 days honestly was failed")
    bare = served(11, 30)
    bare["runrate"] = {"value": 1.0, "basis": "30d"}
    assert g.coverage_breaches(_snapshot([bare]))["checked"] == 0, "a row that states no coverage was judged"

    # 2026-10-10: the dilution bands. dilution_meta said caution_line 1.5253 and red_line 1.0
    # (the page: "Caution above 1.5% a week, red above 1%"), so a coin over 1.0 is red before it
    # can be caution: 0 of 233 apps read caution (10 at ET-28821), 19 red.
    meta = {"caution_line": 1.5253, "red_line": 1.0, "levels": {"ok": 97, "caution": 0, "red": 19, "unknown": 117}}
    seen = g.dilution_band_breach(meta)
    assert seen == {"caution_line": 1.5253, "red_line": 1.0, "caution_n": 0, "red_n": 19}, seen
    assert g.dilution_band_breach(dict(meta, caution_line=0.5)) is None, "caution below red is the order a reader expects"
    assert g.dilution_band_breach(dict(meta, caution_line=1.0)) is not None, "equal lines leave caution empty too"
    assert g.dilution_band_breach({"caution_line": None, "red_line": 1.0}) is None, "a line not stated is not judged"
    assert g.dilution_band_breach({}) is None

    # A path llms.txt names and the OpenAPI lacks (report-access, 2026-10-10), placeholders alike.
    llms = ("`GET /api/v1/gem-screener/report-access`: may THIS caller ask; "
            "GET https://cymetica.com/api/v1/gem-screener/coins/<symbol>/degen-report; /api/v1/gem-screener/picks; "
            "/api/v1/chart-analyzer/x")
    spec = {"paths": {"/api/v1/gem-screener/coins/{symbol}/degen-report": {}, "/api/v1/gem-screener/picks": {}}}
    assert g.paths_missing_from_openapi(llms, spec) == ["/api/v1/gem-screener/report-access"]
    assert g.paths_missing_from_openapi(llms, {"paths": dict(spec["paths"], **{"/api/v1/gem-screener/report-access": {}})}) == []
    assert g.paths_missing_from_openapi("", spec) == [] and g.paths_missing_from_openapi(llms, {}) != []

    # C04, deep pass of 2026-09-30 (3/3): the market cap is price x circulating
    # supply. On 2026-09-30 the page held it within 1.02 % on all 214 rows; the
    # ranking stands on it (ps = mcap / run-rate), and nothing compared it.
    assert breaches([_app("m#1", "MMM", 1.0)], "market cap")["breaches"] == []
    assert breaches([_app("m#1", "MMM", 1.0, mcap=5000.0)], "market cap")["breaches"] == ["MMM"], (
        "a market cap five times price x supply passed")

    # R02/C05 (3/3): a figure recomputed on no row at all is unread, never agreement.
    ids = [{"name": "ps", "checked": 10, "breaches": [], "max_dev": 0.0},
           {"name": "themes", "checked": 0, "breaches": [], "max_dev": 0.0}]
    verdict, why = g.identities_verdict(ids, total=10)
    assert verdict == "inconclusive" and "themes" in why, (verdict, why)
    ids[1]["checked"] = 12
    assert g.identities_verdict(ids, total=10)[0] == "passed"
    ids[1]["breaches"] = ["th"]
    assert g.identities_verdict(ids, total=10)[0] == "failed"
    ids[0]["checked"] = 4
    assert g.identities_verdict(ids, total=10)[0] == "inconclusive", "a P/S read on 4 of 10 rows was judged"

    # recomputing from the raw daily series
    import datetime as dt
    start = dt.date(2026, 1, 1)
    chart = [[int(dt.datetime(start.year, start.month, start.day, tzinfo=dt.timezone.utc).timestamp()) + 86400 * i,
              100.0 * 1.01 ** i] for i in range(200)]
    days = {start + dt.timedelta(days=i): 100.0 * 1.01 ** i for i in range(200)}
    last = max(days)
    page30 = sum(days[last - dt.timedelta(days=i)] for i in range(30))
    app = _app("a#3", "SER", 1.0, rev30d=page30, monthly=[], runrate={"value": page30 * 365 / 30, "basis": "30d"},
               growth6m={"g": 100 * (1.01 ** 30 - 1), "weeks": 26, "r2": 1.0})
    made = g.recompute_from_series(app, chart)
    assert made["rev30d"]["dev"] < 1e-9 and made["runrate"]["dev"] < 1e-9, made
    assert abs(made["growth6m"]["mine"] - 100 * (1.01 ** 30 - 1)) < 0.01 and made["growth6m"]["weeks_mine"] == 26, made
    off = g.recompute_from_series(dict(app, rev30d=page30 * 1.2), chart)
    assert off["rev30d"]["dev"] > 0.15, "a 20 % wrong 30-day revenue was not seen"
    gappy = [p for n, p in enumerate(chart) if not (100 <= n <= 103)]
    assert g.recompute_from_series(app, gappy)["growth6m"]["weeks_mine"] < 26, (
        "a week with missing days was kept in the regression")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_audit_sees_a_wrong_upside_a_wrong_identity_a_wrong_altseason_and_a_wrong_derived_figure():
    """Each judgement the core checks make is refuted here on data built to be
    wrong in exactly its way, and shown to let ordinary readings through."""
    _the_upside_check_sees_a_wrong_multiple_and_a_wrong_cap()
    _a_pick_that_opens_another_coin_is_seen_and_a_shared_ticker_is_named()
    _the_altseason_numbers_are_held_to_their_own_published_rules()
    _the_derived_figures_are_held_to_their_definitions()
    # 2026-10-02: the four judgements behind
    # tests/rest/test_gem_screener_panels_say_what_their_data_says.py, merged here
    # because tests/meta grows only by replacement.
    _a_basket_priced_on_two_dates_is_seen()
    _one_word_for_hot_is_held()
    _a_word_that_says_only_btc_runs_is_held_to_the_breadth_beside_it()
    _how_sure_follows_its_own_tooltip()
    _a_share_image_is_read_the_way_a_crawler_reads_it()
    _a_forming_candle_that_is_old_and_far_from_its_pool_is_seen()
    # 2026-10-04: tests/rest/test_gem_screener_sectors_chart_does_what_its_caption_says.py
    _a_chart_click_is_held_to_its_caption()
    # 2026-10-04: tests/rest/test_gem_screener_chains_say_what_their_sources_say.py
    _the_chains_tab_is_held_to_its_sources_and_its_own_words()


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_source_client_carries_the_whole_guard_and_none_of_their_credentials():
    """`build_source_client` reads CoinGecko, DefiLlama and DexScreener for the
    audit. It is a new way to reach a host that is not theirs, so what must hold
    is shown: no tier in scope is refused, a write to any third party is refused
    at every tier, no key rides along, and it shares no rate-limit budget with
    Cymetica nor writes the timings diary that is evidence about their host."""
    import httpx

    from qa.client import build_source_client
    from qa.safety import CURRENT_TIER, SafetyViolation

    class _Unsendable(httpx.BaseTransport):
        def handle_request(self, request):
            raise AssertionError(f"{request.method} {request.url} reached the network")

    client = build_source_client(inner=_Unsendable())
    try:
        token = CURRENT_TIER.set(None)
        try:
            with pytest.raises(SafetyViolation, match="No safety tier is in scope"):
                client.get("https://api.coingecko.com/api/v3/ping")
        finally:
            CURRENT_TIER.reset(token)
        for tier in (SafetyTier.SAFE, SafetyTier.PROBE, SafetyTier.MUTATE):
            token = CURRENT_TIER.set(tier)
            try:
                with pytest.raises(SafetyViolation):
                    client.post("https://api.coingecko.com/api/v3/anything", json={})
            finally:
                CURRENT_TIER.reset(token)
        assert not any("key" in name.lower() or "authorization" in name.lower()
                       for name in client.headers), dict(client.headers)
        transport = client._transport
        assert transport.budget is None, "a third party's rate-limit headers could stop the session"
    finally:
        client.close()
    live = build_source_client()
    try:
        assert not isinstance(live._transport.inner, httpx.HTTPTransport), (
            "the source client would write its requests to the timings diary, "
            "which scripts/timeouts.py reads as their host's")
    finally:
        live.close()


def _a_failed_cymetica_read_is_named_not_fatal(monkeypatch):
    """R07, deep pass of 2026-09-30 (3/3): a picks or coin read that answers a
    body that is not JSON, or does not answer, leaves its section out and names
    it -- the tick still writes its report."""
    import importlib.util
    import json as _json
    from pathlib import Path

    import httpx

    from qa.client import build_mock_client

    spec = importlib.util.spec_from_file_location(
        "gem_audit_under_test", Path(__file__).resolve().parents[2] / "scripts" / "gem_audit.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    snap = _snapshot([_app("a#1", "AAA", 2.0)])
    page = f'<script id="snapshot-data" type="application/json">{_json.dumps(snap)}</script>'

    def cymetica(request):
        if "/gem-screener/app" in str(request.url):
            return httpx.Response(200, text=page)
        return httpx.Response(200, text="<html>not json</html>")

    monkeypatch.setattr(mod, "build_client", lambda *a, **k: build_mock_client(cymetica, timeout=5.0))
    monkeypatch.setattr(mod, "build_source_client",
                        lambda *a, **k: build_mock_client(lambda r: httpx.Response(503, json={}), timeout=5.0))
    inputs, errors = mod.read_everything()
    assert inputs["snapshot"]["apps"][0]["key"] == "a#1"
    assert "picks" in errors and "picks" not in inputs, errors

    def stalled(request):
        if "/gem-screener/app" in str(request.url):
            return httpx.Response(200, text=page)
        raise httpx.ReadTimeout("stalled", request=request)

    monkeypatch.setattr(mod, "build_client", lambda *a, **k: build_mock_client(stalled, timeout=5.0))
    inputs, errors = mod.read_everything()
    assert "picks" in errors, errors


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_audit_builds_a_report_from_a_snapshot_alone(monkeypatch):
    """The script must still produce the tables when a third-party source is down
    -- every section that needs one is left out, none invented -- and the lines
    /lab shows must be short."""
    apps = [_app("parent#a", "AAA", 0.3, degen_ok=True, liq={"impact_pct": 1.0, "source": "dex", "pair_liq_usd": 500_000.0},
                 dlevel={"level": 6, "low": 5, "high": 9}, exit_flags=[], earnings30d=-5.0, printed=True),
            _app("leaf#b", "BBB", 2.0, liq={"impact_pct": 90.0, "source": "volume", "pair_liq_usd": 9_000.0})]
    snap = _snapshot(apps, degen={"shortlist": ["parent#a", "leaf#b"]},
                     backtest_summary={"verdict": "inconclusive", "h3": {"diff_median": -0.23, "ci90": [-0.6, -0.1]}},
                     picks_ledger={"ready": False, "cohorts": [{"n": 0}]})
    report = g.build_report(snap, now=1_000_000 + 7200)
    assert report["snapshot_age_h"] == 2.0 and report["sources"] == {}, report["sources"]
    assert [p["buyable_on_chain"] for p in report["picks"]] == [True, False], report["picks"]
    assert report["upside"]["at_cap"] == 1 and report["backtest"]["live_picks_tracked"] == 0
    assert "pick_identity" not in report, "an identity reading appeared with nothing fetched"
    # Deep pass 2026-10-02 (T18): every other section a source feeds is absent too, not
    # empty -- a failed read written as `[]` says "no pegged coins" (rule 8). A source that
    # answered with nothing IS empty, and says so.
    assert "series" not in report and "pegged_like_in_universe" not in report["altseason"], (
        "a section fed by a source that was down was invented")
    assert "pegged_share" not in report["altseason"]
    answered = g.build_report(snap, sources={"altseason_universe": []}, now=1_000_000)
    assert answered["altseason"]["pegged_like_in_universe"] == [], answered["altseason"]
    lines = g.report_lines(report)
    assert lines and all(len(line) < 140 for line in lines), lines
    markdown = g.render_markdown(report)
    assert "## Degen picks" in markdown and "AAA(parent#a)" in markdown
    # With a source, its column appears and is summarised.
    cg = [{"id": "aaa", "circulating_supply": 1000.0, "current_price": 1.0}]
    with_source = g.build_report(snap, sources={"coingecko": cg}, now=1_000_000)
    assert with_source["sources"]["supply_vs_coingecko"]["n"] == 1

    # R05 (3/3): a pick's coin record is used only when it IS that coin -- EDGE
    # and UP are two apps each, and the symbol route answers one of them.
    coins = {"AAA": {"name": "Aaa", "trade_url": "https://x/aaa"},
             "BBB": {"name": "Some Other Token", "trade_url": "https://x/other"}}
    assert [r["tradeable_here"] for r in g.picks_table(snap, coins)] == [True, None], g.picks_table(snap, coins)
    # 2026-10-01: picks are addressed by slug, so the coin records are filed
    # under the slug; the lookup by ticker then found nothing for every pick.
    by_slug = {"aaa": coins["AAA"], "bbb": coins["BBB"]}
    assert [r["tradeable_here"] for r in g.picks_table(snap, by_slug)] == [True, None], (
        "coin records filed under the slug were not found")

    # R10 (3/3): a snapshot that carries no time of its own has no age -- unknown,
    # never "fresh".
    undated = _snapshot([_app("u#1", "UUU", 1.0, market_price_ts=990_000, market_supply_as_of_ts=900_000)])
    undated.pop("generated_at")
    fresh = g.freshness(undated)
    assert fresh["supply_older_than_24h"] is None and fresh["price_age_h"] == {"n": 0}, fresh
    assert g.build_report(undated, now=1_000_000)["snapshot_age_h"] is None

    _a_failed_cymetica_read_is_named_not_fatal(monkeypatch)


def _a_basket_priced_on_two_dates_is_seen():
    """2026-10-02: CoinGecko answered 403 and 429, 11 of 320 coins got a live
    price, and RWA and DePIN each had exactly one member with one. A theme is
    priced on one date when every member has a live point or none does; a share
    below the floor is a basket priced on two."""
    def members(*pairs):
        return [{"id": i, "w": w} for i, w in pairs]

    api = {"themes": [
        {"key": "rwa", "members": members(("a", 0.95), ("z", 0.05))},
        {"key": "ai", "members": members(("b", 0.5), ("c", 0.5))},
        {"key": "memes", "members": members(("d", 0.5), ("e", 0.5))},
        {"key": "l2", "members": members(("f", 0.97), ("g", 0.03))},
    ], "theme_prices": {"live": {"z": 1.3, "b": 1.0, "c": 1.0, "f": 1.0}}}
    said = g.theme_live_coverage(api)
    assert [t["theme"] for t in said["partial"]] == ["rwa"], said
    assert said["partial"][0]["with_live"] == 1 and said["partial"][0]["members"] == 2, said
    assert {t["theme"] for t in said["themes"]} == {"rwa", "ai", "memes", "l2"}, (
        "a theme with every point, none, or 97 % of its weight was judged too")
    assert g.theme_live_coverage({"themes": api["themes"], "theme_prices": {}})["unread"], (
        "a snapshot with no live map read as full coverage")
    assert g.theme_live_coverage({"theme_prices": api["theme_prices"]})["unread"]
    # Members that carry no weight cannot say what share is covered: unread, not agreement.
    weightless = {"themes": [{"key": "x", "members": [{"id": "a"}]}], "theme_prices": {"live": {"a": 1.0}}}
    assert g.theme_live_coverage(weightless)["themes"] == [] and g.theme_live_coverage(weightless)["unread"]


def _one_word_for_hot_is_held():
    """The table and "Hot right now" read `stage == 'hot'`; the theme panel reads
    the older `hot` flag. 2026-10-02: 4 themes against 8."""
    def snap(*rows):
        return {"themes": [{"key": k, "hot": h, "stage": s} for k, h, s in rows]}

    same = snap(("l2", True, "hot"), ("l1", False, "falling"))
    assert g.hot_definitions(same)["disagree"] == [], "two agreeing definitions were called different"
    split = snap(("l2", True, "hot"), ("defi", True, "fading"), ("memes", False, "hot"), ("l1", False, "falling"))
    said = g.hot_definitions(split)
    assert said["disagree"] == ["defi", "memes"], said
    assert said["flag_hot"] == ["l2", "defi"] and said["stage_hot"] == ["l2", "memes"], said
    # A field that is gone is unread: there is no second definition left to compare.
    gone = {"themes": [{"key": "l2", "stage": "hot"}, {"key": "l1", "stage": "falling"}]}
    assert g.hot_definitions(gone)["disagree"] == [] and g.hot_definitions(gone)["unread"]
    assert g.hot_definitions({})["unread"]


def _a_word_that_says_only_btc_runs_is_held_to_the_breadth_beside_it():
    """The panel prints a phase word and the share of the top 50 that beat BTC.
    "Only BTC runs" over a week in which most of them did is false on its own
    page. Today: 17 of 155 such weeks, one of them 2024-12-02 at 74 %."""
    def series(phases, breadths):
        weeks = [1_000_000 + 604_800 * i for i in range(len(phases))]
        return {"altseason": {"weeks": weeks, "series": {"phase": phases, "breadth": breadths}}}

    ok = series(["btc_only", "btc_only", "no_altseason", "end_near"], [20.0, 49.0, 80.0, 90.0])
    assert g.phase_word_breaches(ok)["breaches"] == [], "weeks that fit their words were flagged"
    bad = series(["btc_only", "btc_only", "btc_only"], [74.0, 60.0, 59.9])
    said = g.phase_word_breaches(bad)
    assert [b["breadth"] for b in said["breaches"]] == [74.0, 60.0], said
    assert said["weeks_read"] == 3 and said["only_btc_weeks"] == 3, said
    # A week with no breadth reading is not counted as agreeing or as breaching.
    gap = g.phase_word_breaches(series(["btc_only", "btc_only"], [None, 80.0]))
    assert [b["breadth"] for b in gap["breaches"]] == [80.0] and gap["weeks_read"] == 1, gap
    assert g.phase_word_breaches({"altseason": {"series": {}}})["unread"]
    assert g.phase_word_breaches(series(["btc_only"], [10.0, 20.0]))["unread"], (
        "series of different lengths were paired")


def _how_sure_follows_its_own_tooltip():
    """The tooltip says: Sure = 5+ rows that agree within 30 points; Fairly sure
    = 3+ rows within 50; otherwise unsure. 2026-10-02: five rows sat between 4
    and 14 and the panel said unsure, because the spread counted all six (84)."""
    tip = ("Sure: 5+ rows that agree within 30 points. Fairly sure: 3+ rows within 50. "
           "Otherwise unsure.")
    page = "<script>var sureTip = '" + tip + "';</script>"

    def snap(code, *scores):
        parts = {f"r{i}": {"score": s} for i, s in enumerate(scores)}
        return {"altseason_cycle": {"components": {"retail": {"parts": parts, "sure": {"code": code}}}}}

    today = (4.0, 14.1, 4.4, 11.6, 88.1, 6.1)
    said = g.retail_sure_breach(snap("unsure", *today), page)
    assert said["breach"] and said["breach"]["expected"] == "sure" and said["breach"]["shown"] == "unsure", said
    assert g.retail_sure_breach(snap("sure", *today), page)["breach"] is None
    spread = (10.0, 30.0, 55.0, 70.0, 85.0, 99.0)      # three rows within 50, never five within 30
    assert g.retail_sure_breach(snap("fairly_sure", *spread), page)["breach"] is None
    assert g.retail_sure_breach(snap("fairly_sure", 10.0, 20.0, 40.0, 70.0, 90.0, 99.0), page)["breach"] is None
    wrong = g.retail_sure_breach(snap("sure", *spread), page)
    assert wrong["breach"] and wrong["breach"]["expected"] == "fairly_sure", wrong
    # With three rows spread over the whole scale no two agree within 50: unsure.
    assert g.retail_sure_breach(snap("unsure", 0.0, 50.0, 100.0), page)["breach"] is None
    assert g.retail_sure_breach(snap("unsure", *today), "<p>no tooltip here</p>")["unread"], (
        "a page that no longer words the rule was judged against a remembered one")
    assert g.retail_sure_breach({}, page)["unread"]

    # 2026-10-02 15:30 UTC: they re-worded the tooltip to what the code does -- every scored
    # row, the spread of ALL of them -- and the sentence is split by a JS string join.
    new = ("<script>var sureTip = 'Sure: 5+ rows scored and no more than 30 points between the "
           "highest and the lowest of them. ' +     'Fairly sure: 3+ rows, no more than 50 points. "
           "Otherwise unsure: one row far from the rest is enough.';</script>")
    assert not g.retail_sure_breach(snap("unsure", *today), new)["unread"], "the new wording was not read"
    assert g.retail_sure_breach(snap("unsure", *today), new)["breach"] is None   # spread 84: unsure
    wrong = g.retail_sure_breach(snap("sure", *today), new)
    assert wrong["breach"] and wrong["breach"]["expected"] == "unsure", wrong
    tight = (10.0, 12.0, 20.0, 25.0, 33.0)                                       # five rows, spread 23
    assert g.retail_sure_breach(snap("sure", *tight), new)["breach"] is None
    assert g.retail_sure_breach(snap("fairly_sure", 10.0, 30.0, 55.0), new)["breach"] is None  # 3 rows, 45
    assert g.retail_sure_breach(snap("unsure", 10.0, 30.0, 70.0), new)["breach"] is None       # 3 rows, 60
    assert g.retail_sure_breach(snap("unsure", 10.0, 20.0), new)["breach"] is None             # 2 rows


def _a_forming_candle_that_is_old_and_far_from_its_pool_is_seen():
    """2026-10-02, Collector Crypt: the Chart Analyzer's cache was fetched at 12:24 UTC and
    at 14:38 its forming daily candle closed at 0.2567 while the pool's own candle read
    0.2707 (5.2% off), under a page that says LIVE and `candles_stale: false`. A candle
    that is more than an hour old AND off by more than 2% is the defect; a fresh one
    that drifted, or an old one that still agrees, is not."""
    now = 1_790_000_000.0
    iso = lambda ago_s: __import__("datetime").datetime.fromtimestamp(
        now - ago_s, __import__("datetime").timezone.utc).isoformat(timespec="seconds")

    def analysis(ago_s, close=0.2567, forming=True):
        return {"candles_fetched_at": iso(ago_s), "last_candle_forming": forming,
                "candles": [[1, 1, 1, 1, 0.20, 5.0], [2, 0.21, 0.26, 0.20, close, 6.0]]}

    said = g.forming_candle_staleness(analysis(134 * 60), 0.2707, now)
    assert said["verdict"] == "old_and_off" and round(said["deviation"], 3) == 0.052, said
    assert round(said["age_s"] / 60) == 134, said
    assert g.forming_candle_staleness(analysis(20 * 60), 0.2707, now)["verdict"] == "ok", (
        "a candle fetched 20 minutes ago was called stale")
    assert g.forming_candle_staleness(analysis(134 * 60, close=0.2700), 0.2707, now)["verdict"] == "ok", (
        "an old candle that still agrees with its pool was called wrong")
    assert g.forming_candle_staleness(analysis(134 * 60, forming=False), 0.2707, now)["verdict"] == "unread", (
        "a closed candle was judged against a live price")
    # Deep pass 2026-10-02: the check's docstring says an honest `candles_stale: true` is
    # one of the ways to fix it. A candle that is old and off BUT says so is flagged, not a
    # defect; the same candle saying `candles_stale: false` still is (the 2026-10-02 case).
    flagged = dict(analysis(134 * 60), candles_stale=True)
    assert g.forming_candle_staleness(flagged, 0.2707, now)["verdict"] == "ok", (
        "an old candle that honestly says it is stale was called a defect")
    denied = dict(analysis(134 * 60), candles_stale=False)
    assert g.forming_candle_staleness(denied, 0.2707, now)["verdict"] == "old_and_off"
    assert g.forming_candle_staleness({"candles": []}, 0.2707, now)["verdict"] == "unread"
    assert g.forming_candle_staleness(analysis(134 * 60), None, now)["verdict"] == "unread", (
        "a source that did not answer was read as agreement")


def _a_share_image_is_read_the_way_a_crawler_reads_it():
    """The preview image a page names is read from its og:image and twitter:image
    tags, in either attribute order, with &amp; undone; a page with none names none."""
    page = ('<head><meta property="og:title" content="Gem Screener">'
            '<meta property="og:image" content="https://cymetica.com/og/app/gem-screener.png?t=A%20B&amp;v=4">'
            '<meta content="https://cymetica.com/static/images/og-default.png" name="twitter:image">'
            '<meta name="twitter:card" content="summary_large_image"></head>')
    assert g.share_images(page) == {
        "og:image": "https://cymetica.com/og/app/gem-screener.png?t=A%20B&v=4",
        "twitter:image": "https://cymetica.com/static/images/og-default.png"}, g.share_images(page)
    assert g.share_images("<head><title>x</title></head>") == {} and g.share_images("") == {}
    assert g.share_images('<meta property="og:image" content="">') == {}, "an empty content named an image"


def _a_chart_click_is_held_to_its_caption():
    """2026-10-04, Sectors tab: the chart's caption says "Click a bubble for the sector",
    and a capture-phase listener (ET-28990 #3) pins the hover card on the first click and
    lets only the second one reach the bubble's openThemePanel. The judgement fails only on
    that known mechanism beside a one-click caption; a caption that says what happens, or a
    listener held to touch, passes; a page whose shape it cannot read is unread, never ok."""
    renderer = ("function renderThemeScatter(){\n"
                "  var sub = document.getElementById('scatterSub');\n"
                "  if (pts.length < 2) { sub.textContent = 'Not enough data for the chart.'; return; }\n"
                "  sub.textContent = 'Bubble size = market cap.' + (hasTrail ? ' Tail = where it stood ' + back + "
                "' weeks ago.' : '') +\n    CAPTION;\n"
                "  g.addEventListener('click', function(){ openThemePanel(th.key); });\n"
                "  sub.textContent += ' No room for a name next to: ' + unlabelled.join(', ') + '.';\n"
                "}\n/* ET-28378 part 3 */\nfunction themesChangeNote(){ return ''; }\n")
    listener = ("/* ET-28990 #3: a click or tap on a hot-sector card or a point of the Sectors chart pins the\n"
                "   same dark card hover and Tab show; a second click on the same one opens its detail. */\n"
                "document.addEventListener('click', function(ev){\n"
                "  var el = ev.target.closest && ev.target.closest('.thcard.cardtip, #themeScatter g.pt');\n"
                "  if (!el || tipHostOf(ev.target)) return;\nGATE"
                "  if (popoverOwner === el) { closePopover(); return; }\n"
                "  ev.stopPropagation(); ev.preventDefault();\n  pinHost(el);\n}, true);\n"
                "document.addEventListener('keydown', function(ev){ if (ev.key !== 'Enter') return; }, true);\n")
    one_click = "' Click a bubble for the sector.'"

    def page(caption=one_click, gate="", head="", tail=listener):
        return "<script>" + head + renderer.replace("CAPTION", caption) + tail.replace("GATE", gate) + "</script>"

    today = g.sector_click_promise(page())
    assert today["verdict"] == "two_clicks", today
    assert today["caption"] == "Click a bubble for the sector.", today
    assert "#themeScatter g.pt" in today["interceptor"] and "pinHost" in today["interceptor"], today

    # A caption that says what happens clears it, however the click itself is left.
    for said in ("' Click a bubble for its card, and again for the sector.'",
                 "' Click a bubble twice for the sector.'", "''"):
        assert g.sector_click_promise(page(caption=said))["verdict"] == "ok", said
    # A first-click card kept for touch only clears it: in the listener, before it, or
    # through a name the page computes from a hover/pointer media query.
    for gate in ("  if (window.matchMedia('(hover: hover)').matches) return;\n",
                 "  if (ev.pointerType === 'mouse') return;\n",
                 "  if (CAN_HOVER) return;\n"):
        head = "var CAN_HOVER = window.matchMedia('(hover: hover) and (pointer: fine)').matches;\n"
        assert g.sector_click_promise(page(gate=gate, head=head))["verdict"] == "ok", gate
    wrapped = listener.replace("document.addEventListener('click'",
                               "if (!matchMedia('(any-hover: hover)').matches) document.addEventListener('click'", 1)
    assert g.sector_click_promise(page(tail=wrapped))["verdict"] == "ok", "a listener registered for touch only was judged"
    # A media query about width is not a hover gate.
    narrow = "var NARROW = matchMedia('(max-width: 720px)').matches;\n"
    assert g.sector_click_promise(page(gate="  if (NARROW && !el) return;\n", head=narrow))["verdict"] == "two_clicks"

    # Deep pass 2026-10-05 (R11): the listener's body must end where the listener does. Read
    # up to the next addEventListener it ran on into a following hover-media-query helper, and
    # an ungated listener read as gated, so the check could never see the defect come back.
    bare_then_helper = ("document.addEventListener('click', function(ev){\n"
                        "  var el = ev.target.closest && ev.target.closest('#themeScatter g.pt');\n"
                        "  if (!el) return;\n  ev.stopPropagation(); ev.preventDefault();\n  pinHost(el);\n}, true);\n"
                        "function hoverDevice(){ return matchMedia('(hover: hover) and (pointer: fine)').matches; }\n")
    assert g.sector_click_promise(page(tail=bare_then_helper))["verdict"] == "two_clicks", (
        "a hover helper declared AFTER the listener was read as the listener's gate")

    # What it cannot read is unread, never a pass: the listener gone (a browser has to say
    # whether one click now opens the sector), the renderer gone, the caption gone, or no
    # click on a bubble that opens the panel at all.
    gone = g.sector_click_promise(page(tail=listener.replace("#themeScatter g.pt", ".other")))
    assert gone["verdict"] == "unread" and gone["why"], gone
    assert g.sector_click_promise(page().replace("renderThemeScatter", "renderOther"))["verdict"] == "unread"
    no_caption = page().replace("sub.textContent = 'Bubble", "sub.innerHTML = 'Bubble")
    assert g.sector_click_promise(no_caption)["verdict"] == "unread", "a caption it could not find was read as silent"
    assert g.sector_click_promise(page().replace("openThemePanel(th.key)", "noop()"))["verdict"] == "unread"
    assert g.sector_click_promise("")["verdict"] == "unread"
    assert g.sector_click_promise(None)["verdict"] == "unread"


def _the_chains_tab_is_held_to_its_sources_and_its_own_words():
    """2026-10-04, Chains tab (snapshot 08:47 UTC), verified over all 33 chains: users, DEX
    volume, TVL, market cap and every derived figure follow their sources and the page's own
    rules. Three places do not, each refuted here on the shape seen live and cleared by the fix.

    1. Stablecoins, "dollars parked on the chain": the page shows DeFiLlama's token count
       (`totalCirculating`), not its dollar value (`totalCirculatingUSD`). Stellar showed
       $840.9M where DeFiLlama's dollar figure for the same day was $909.5M (USDY at $1.147)."""
    day = 1791072000

    def chain(slug, shown, as_of=day):
        return {"slug": slug, "name": slug.title(),
                "adoption": {"inputs": {"stablecoins": shown}, "as_of": {"stablecoins": as_of}}}

    def point(usd, tokens, date=day):
        return {"date": str(date), "totalCirculating": {"peggedUSD": tokens},
                "totalCirculatingUSD": {"peggedUSD": usd, "peggedEUR": 2.0e7}}

    chains = [chain("stellar", 840929169.43), chain("solana", 16799590747.15), chain("gnosis", 14966829.54)]
    charts = {"stellar": [point(960342849.0, 900000000.0, day - 86400), point(909523394.0, 840929169.0)],
              "solana": [point(16818415410.0, 16799590747.0)],
              "gnosis": [point(14966065.0, 14966830.0)]}
    said = g.chain_stablecoin_gaps(chains, charts)
    assert [x["name"] for x in said["gaps"]] == ["Stellar"], said
    assert said["judged"] == 3 and said["gaps"][0]["tokens_match"] is True, said
    assert round(said["gaps"][0]["gap_pct"], 1) == -7.5, said
    # EUR-pegged coins are not dollars: a chain that shows only its USD-pegged coins passes.
    assert "Gnosis" not in [x["name"] for x in said["gaps"]]
    # The fix: the dollar value shown.
    fixed = [chain("stellar", 909523394.0)] + chains[1:]
    assert g.chain_stablecoin_gaps(fixed, charts)["gaps"] == []
    # A failed read, or no point on the input's own day, is unread, never agreement.
    gone = g.chain_stablecoin_gaps(chains, dict(charts, stellar=None))
    assert gone["judged"] == 2 and gone["gaps"] == [] and gone["unread"], gone
    # Deep pass 2026-10-05 (T01): a shown $0 is a figure, a -100 % gap -- not an unread chain.
    zero = g.chain_stablecoin_gaps([chain("stellar", 0)], charts)
    assert zero["judged"] == 1 and zero["unread"] == [] and zero["gaps"][0]["gap_pct"] == -100.0, zero
    missing = g.chain_stablecoin_gaps([chain("stellar", None)], charts)
    assert missing["judged"] == 0 and missing["unread"], missing
    other_day = g.chain_stablecoin_gaps([chain("stellar", 840929169.43, day + 86400)], charts)
    assert other_day["judged"] == 0 and other_day["unread"], other_day
    # 2026-10-10: the input's day can be today, DeFiLlama's still-open point, which moves until
    # the day closes. Filecoin showed $218,386 while that point read $230,634 an hour later and
    # the closed day before it $216,283: a value the source's own point passed through is not a
    # gap. A closed day is held as before, and Stellar's token count is outside both.
    open_day = {"filecoin": [point(216283.0, 206299.0, day - 86400), point(230633.95, 208320.02)]}
    assert g.chain_stablecoin_gaps([chain("filecoin", 218385.5)], open_day)["gaps"] == [], (
        "a figure between the source's closed day and its still-open point was failed")
    closed = {"filecoin": open_day["filecoin"] + [point(231000.0, 208000.0, day + 86400)]}
    assert [x["name"] for x in g.chain_stablecoin_gaps([chain("filecoin", 218385.5)], closed)["gaps"]] == ["Filecoin"]
    assert [x["name"] for x in g.chain_stablecoin_gaps(chains, charts)["gaps"]] == ["Stellar"], (
        "the token count passed as a moving point")

    # 2. The chain price tag as described: llms.txt's "What it is" and the chain detail's
    #    agent prompt still describe yearly activity fees against a named leader chain;
    #    the snapshot (and llms.txt a few lines lower) say adoption against the median.
    bench = {"basis": "market_cap/adoption", "measure": "adoption", "adoption_version": "four-inputs-1",
             "kind": "median", "mult": 127.927}
    # The live file names the section in quotes long before the section itself
    # ('see the "## Gem Screener" section below'): only a heading line starts it.
    llms = ("# Cymetica\n- [Gem Screener](/gem-screener): see the \"## Gem Screener\" section below.\n"
            "## Chart Analyzer\nA chain's is market cap / yearly activity fees elsewhere.\n"
            "## Gem Screener\n\nWhat it is: a research screen of tokenized crypto apps and chains, ranked by "
            "how cheap they are for the revenue they earn. An app's multiple is its market cap / annual revenue "
            "run-rate, compared with Hyperliquid’s multiple; a chain’s is market cap / yearly activity "
            "fees (what users paid to the apps on the chain and to the chain itself), compared with a named "
            "leader chain, not the median.\n"
            "- `price_vs_revenue` (x): market cap / annual run-rate (chains: market cap / yearly activity fees); "
            "lower is cheaper\n"
            "- Chains (`kind=chains`, ET-28378): `activity_fees` (USD per year) on the ranked list; `benchmark` "
            "names the leader chain, its rule\n"
            "- Chains from ET-28821: a chain is priced on `adoption`, the fourth root of daily users x DEX "
            "volume; `benchmark` is the median price tag of the large chains\n## Supply Analyzer\nx\n")
    claims = g.chain_price_tag_claims(llms, bench)
    assert [c["claim"] for c in claims["stale"]] == ["fees_multiple", "named_leader", "pvr_fees",
                                                     "benchmark_leader"], claims
    assert not claims["unread"], claims
    # The fix: the section says what the snapshot computes; a field name alone is no claim.
    fixed_llms = ("## Gem Screener\nWhat it is: ... a chain's is market cap / adoption (daily users, DEX "
                  "volume, TVL and stablecoins), compared with the median of the large chains.\n"
                  "- `activity_fees` (USD per year) stays on the ranked list as context\n## Next\n")
    assert g.chain_price_tag_claims(fixed_llms, bench)["stale"] == []
    # A snapshot still on fees and a leader makes the same words true, not stale.
    old = {"basis": "market_cap/activity_fees", "measure": "activity_fees", "kind": "leader"}
    assert g.chain_price_tag_claims(llms, old)["stale"] == []
    assert g.chain_price_tag_claims("no section here", bench)["unread"]
    assert g.chain_price_tag_claims(llms, {})["unread"], "a snapshot that names no measure was judged"
    # Deep pass 2026-10-08 (T07): a "named leader" sentence is stale beside ANY kind that is
    # not a leader -- a mean is not one -- and unread when the snapshot names no kind.
    mean = dict(bench, kind="mean")
    assert "named_leader" in [c["claim"] for c in g.chain_price_tag_claims(llms, mean)["stale"]]
    nameless = {k: v for k, v in bench.items() if k != "kind"}
    assert g.chain_price_tag_claims(llms, nameless)["unread"], "no kind, yet a leader claim was judged"

    page = ("<script>function chainAgents(e){\n  var paste = 'Read ' + api + ' and tell me about ' + e.name + "
            "' (' + sym + '): its adoption (daily users and fees), its upside against ' +\n"
            "    'the benchmark chain and its trajectory. Every number there carries its unit.';\n}</script>")
    prompt = g.chain_agent_prompt_claims(page, bench)
    assert prompt["stale"] == ["adoption (daily users and fees)", "the benchmark chain"], prompt
    fixed_page = page.replace("(daily users and fees)", "(daily users, DEX volume, TVL and stablecoins)") \
                     .replace("the benchmark chain", "the median large chain")
    assert g.chain_agent_prompt_claims(fixed_page, bench)["stale"] == []
    assert g.chain_agent_prompt_claims("<script>nothing</script>", bench)["unread"]

    # 3. One word, two measures: the Adoption column is four inputs with "no monthly
    #    history"; Growth 6M, the trajectory and the vetting tags are a stablecoins-and-DEX
    #    index the page also calls Adoption (Mantle: "Adoption falling 12.8% a month").
    words = ("<script>var INFO = {chainadopt4: '<b>Adoption</b> — the new measure: four inputs together, "
             "no fees in it.', 'monthly@chains': 'Not the adoption measure, which has no monthly history.'};\n"
             "var R = {'klesající trend': function(e){ return 'Adoption (stablecoins and DEX volume) has been "
             "falling ' + g + '% a month over the ' +\n 'last six months.'; }};\n"
             "stats += statCell(isChains ? 'Adoption growth 6M' : 'Revenue growth 6M', fmtPct(g.g));</script>")
    rows = [{"name": "Mantle", "reliable": False, "reliable_fail": ["far_below_peak", "declining_trend"]},
            {"name": "Solana", "reliable": True, "reliable_fail": []}]
    two = g.chain_adoption_two_measures(words, rows)
    assert two["verdict"] == "two_measures", two
    assert two["readings"] == ["Adoption (stablecoins and DEX volume)", "Adoption growth 6M"], two
    assert [r["name"] for r in two["rows"]] == ["Mantle"], two
    # The fix either way: name the index for what it is, or measure the readings on the
    # four-input adoption (and stop saying it has no history).
    renamed = words.replace("Adoption (stablecoins and DEX volume)", "Stablecoins and DEX volume") \
                   .replace("Adoption growth 6M", "Stablecoins & DEX growth 6M")
    assert g.chain_adoption_two_measures(renamed, rows)["verdict"] == "ok"
    measured = words.replace("Adoption (stablecoins and DEX volume)", "Adoption") \
                    .replace(", which has no monthly history", "")
    assert g.chain_adoption_two_measures(measured, rows)["verdict"] == "ok"
    # Deep pass 2026-10-05 (T03): the two labels renamed but the vetting tags kept is the same
    # defect; the check read only the two labels and called it ok.
    tagged = renamed.replace("</script>", "var T = 'Declining: Adoption falling 12.8% a month for six months';</script>")
    tagged_two = g.chain_adoption_two_measures(tagged, rows)
    assert tagged_two["verdict"] == "two_measures" and tagged_two["readings"], tagged_two
    assert g.chain_adoption_two_measures(
        measured.replace("</script>", "var T = 'Declining: Adoption falling 12.8% a month';</script>"),
        rows)["verdict"] == "ok", "a tag on the measure the page defines was called a second measure"
    assert g.chain_adoption_two_measures("<script></script>", rows)["verdict"] == "unread"
    assert g.chain_adoption_two_measures(None, rows)["verdict"] == "unread"

    # 4. Why a chain is not listed: "Not listed, no market data: BCH, ETC." while CoinGecko
    #    gave Bitcoin Cash $6.4bn and Ethereum Classic $1.4bn, both with missing: [].
    universe = {"min_mcap": 2.0e8, "left_out": [
        {"symbol": "BCH", "gecko_id": "bitcoin-cash", "chain": "Bitcoincash", "reason": "no_market_data", "missing": []},
        {"symbol": "ETC", "gecko_id": "ethereum-classic", "chain": "EthereumClassic", "reason": "no_market_data",
         "missing": []},
        {"symbol": "XMR", "gecko_id": "monero", "chain": None, "reason": "no_defillama_row", "missing": ["tvl"]}]}
    markets = {"bitcoin-cash": 6383422929.0, "ethereum-classic": 1403766651.0}
    said = g.chain_left_out_reason_breaches(universe, markets)
    assert [b["symbol"] for b in said["breaches"]] == ["BCH", "ETC"] and said["judged"] == 2, said
    # A coin CoinGecko really has no market cap for, or one under the listing floor's
    # reach, is what the reason says; one not read is unread.
    assert g.chain_left_out_reason_breaches(universe, {"bitcoin-cash": None, "ethereum-classic": 0.0})["breaches"] == []
    partial = g.chain_left_out_reason_breaches(universe, {"bitcoin-cash": 6383422929.0})
    assert [b["symbol"] for b in partial["breaches"]] == ["BCH"] and partial["unread"] == ["ETC"], partial
    # The fix: the two say which input they lack; nothing is left out for market data.
    fixed = {"min_mcap": 2.0e8, "left_out": [dict(universe["left_out"][0], reason="missing_input",
                                                   missing=["stablecoins"])]}
    assert g.chain_left_out_reason_breaches(fixed, markets) == {"judged": 0, "breaches": [], "unread": [],
                                                                  "with_reason": 0}
    assert g.chain_left_out_reason_breaches({}, markets)["unread"], "no left-out list was read as agreement"

"""The two live rounds around qa/fomo.py. Real field shapes captured live on
2026-09-13: fomo-radar's `{"rows": [{"token_address","hot","symbol",...}]}`
and memecoin-terminal's `{"rows": [{"address","price_usd",...}]}`.
"""

from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
T0 = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)


def _module(tmp_path, monkeypatch):
    import importlib

    import qa.state

    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    importlib.reload(qa.state)
    spec = importlib.util.spec_from_file_location(
        "fomo_watch_under_test", REPO / "scripts" / "fomo_watch.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _client(handler):
    from qa.client import build_mock_client

    return build_mock_client(handler, timeout=5.0)


def _fomo_row(token="0xabc", hot=True, symbol="DOGEX"):
    return {"token_address": token, "hot": hot, "symbol": symbol,
           "conviction": 0.5, "new_qualified_buyers_15m": 4}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_capture_writes_one_signal_per_token_with_its_price(tmp_path,
                                                             monkeypatch):
    mod = _module(tmp_path, monkeypatch)

    # Distinct addresses per chain -- a real Robinhood Chain address and a
    # real Solana address are never the same string.
    by_chain = {"robinhood": "0xabc", "solana": "SoLabc111"}

    def handler(request):
        url = str(request.url)
        if "fomo-radar/signals" in url:
            chain = request.url.params.get("chain")
            return httpx.Response(200, json={"rows": [_fomo_row(by_chain[chain])]})
        if "memecoin-terminal/search" in url:
            wanted = request.url.params.get("q")
            return httpx.Response(200, json={"rows": [
                {"address": wanted, "price_usd": 0.002}]})
        return httpx.Response(404)

    result = mod.capture(_client(handler), now=T0)
    assert result["added"] == 2, "one signal for each chain's own token"
    rows = mod.load()
    signals = [r for r in rows if r["type"] == "signal"]
    assert len(signals) == 2
    assert {s["token_address"] for s in signals} == set(by_chain.values())
    assert all(s["price_usd"] == 0.002 for s in signals)
    assert signals[0]["key"] == "0xabc:2026-09-13T12"

    # Running capture() again the same hour must not duplicate the signal.
    again = mod.capture(_client(handler), now=T0 + timedelta(minutes=5))
    assert again["added"] == 0
    assert len([r for r in mod.load() if r["type"] == "signal"]) == 2


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_row_with_no_identity_is_counted_not_silently_dropped(tmp_path,
                                                                monkeypatch):
    """A hot signal naming no token is not a quiet market.

    Measured 2026-09-13 11:52 UTC: every Robinhood-chain row came back with
    `token_address: ""` and `symbol: ""` for about six minutes. `signal_key`
    returns None for a blank address and `new_signals` skips it, so nothing
    was corrupted -- forty curves did NOT collapse into one key, which is the
    failure that mattered.

    But `capture()` reported `added: 0`, which is exactly what a quiet hour
    looks like. Rule 8's shape: a row we cannot identify is not a row that was
    not there, and the difference has to survive into the round's own result
    or the gap in the measurement is invisible afterwards.
    """
    mod = _module(tmp_path, monkeypatch)

    def handler(request):
        if "fomo-radar/signals" in str(request.url):
            return httpx.Response(200, json={"rows": [
                # Their outage shape, verbatim: conviction and hot are real,
                # every identity field is blank.
                {"token_address": "", "symbol": "", "name": "Unnamed launch",
                 "hot": True, "conviction": 68.5, "usd_invested": 12108.07},
                {"token_address": "", "symbol": "", "name": "Unnamed launch",
                 "hot": True, "conviction": 66.5, "usd_invested": 4300.97},
            ]})
        return httpx.Response(404)

    result = mod.capture(_client(handler), now=T0)

    assert result["added"] == 0, "nothing identifiable, so nothing tracked"
    assert result.get("unidentified") == 4, (
        "two anonymous hot rows on each of the two chains have to be COUNTED "
        "-- otherwise their outage and a quiet market are the same result")
    assert [r for r in mod.load() if r["type"] == "signal"] == [], (
        "an unidentifiable row must never reach the diary")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_capture_survives_a_price_lookup_that_fails(tmp_path, monkeypatch):
    """A signal is still tracked even when the price call fails -- rule 8: a
    failed read is not an empty read, and it must not cost us the signal
    itself, only the price on it."""
    mod = _module(tmp_path, monkeypatch)
    by_chain = {"robinhood": "0xdef", "solana": "SoLdef222"}

    def handler(request):
        if "fomo-radar/signals" in str(request.url):
            chain = request.url.params.get("chain")
            return httpx.Response(200, json={"rows": [_fomo_row(by_chain[chain])]})
        return httpx.Response(500)

    result = mod.capture(_client(handler), now=T0)
    # Both halves used to be blind at once. `added` counted error rows beside
    # signals, so "2" was satisfied by two failed chains and zero signals; and
    # `all(...)` over an empty list is vacuously true. The signal count is now
    # a count of SIGNALS, and the list is required to be non-empty before its
    # members are judged. L01, deep pass of 2026-09-13, triage 2/3.
    assert result["added"] == 2, result
    assert result["errors"] == [], result
    signals = [r for r in mod.load() if r["type"] == "signal"]
    assert len(signals) == 2, "the signal must survive a failed price lookup"
    assert all(s["price_usd"] is None for s in signals)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_feed_that_is_down_is_not_a_feed_with_nothing_hot(tmp_path,
                                                             monkeypatch):
    """Rule 8, one level up from the row.

    `_hot_rows` returned [] on any non-200, so a 503 and an hour with nothing
    hot produced byte-identical results -- {added: 0, unidentified: 0}, no
    error anywhere. capture() wraps the call in try/except, but _hot_rows did
    not raise on an HTTP error, so that branch could not fire for one. Measured
    side by side on 2026-09-13, in the module where `unidentified` had been
    added the same day for the identical reason one level down.
    """
    mod = _module(tmp_path, monkeypatch)

    dead = mod.capture(_client(lambda r: httpx.Response(503, json={"d": 1})),
                       now=T0)
    quiet = mod.capture(_client(lambda r: httpx.Response(200, json={"rows": []})),
                        now=T0)

    assert quiet["added"] == 0 and quiet["errors"] == [], quiet
    assert dead["added"] == 0, dead
    assert len(dead["errors"]) == 2, (
        "a dead feed must say so, once per chain, not read as a quiet market")
    assert all("503" in str(e.get("error")) for e in dead["errors"]), dead


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_resolve_checkpoints_only_what_is_due_and_computes_our_own_return(
        tmp_path, monkeypatch):
    mod = _module(tmp_path, monkeypatch)
    mod._append({"type": "signal", "at": T0.isoformat(),
                "key": "0xabc:2026-09-13T12", "token_address": "0xabc",
                "symbol": "DOGEX", "chain": "robinhood", "conviction": 0.5,
                "price_usd": 0.002})

    def handler(request):
        assert "memecoin-terminal/search" in str(request.url)
        return httpx.Response(200, json={"rows": [
            {"address": "0xabc", "price_usd": 0.003,
             "change_h1": 999.0}]})  # their rolling window -- must be ignored

    # Not due yet, ten minutes in. (Thirty until 2026-09-22, when +30 min
    # became a horizon of its own.)
    early = mod.resolve(_client(handler), now=T0 + timedelta(minutes=10))
    assert early["checked"] == 0

    due = mod.resolve(_client(handler), now=T0 + timedelta(hours=1, minutes=1))
    assert due["checked"] == 1
    checkpoint = due["checkpoints"][0]
    assert checkpoint["horizon"] == "1h"
    assert checkpoint["return_pct"] == 50.0, (
        f"OUR return from 0.002 to 0.003 is +50%%, not their own 999%% "
        f"rolling window: {checkpoint}")

    # The same horizon is not checkpointed twice. Read between two marks --
    # since 2026-09-13 every hour is a horizon, so at exactly +2h the SECOND
    # hour is legitimately ripe and this would be measuring that instead.
    # B01, deep pass of 2026-09-22: at +1h45 the hour's window has already
    # closed, so that read passes whether or not resolve() remembers what it
    # did. +1h05 is still inside it -- only the done checkpoint refuses it.
    inside = mod.resolve(_client(handler), now=T0 + timedelta(hours=1, minutes=5))
    assert inside["checked"] == 0, inside
    again = mod.resolve(_client(handler), now=T0 + timedelta(hours=1, minutes=45))
    assert again["checked"] == 0

    # And an hour whose moment has passed is never filled in later: at +5h
    # hours 2, 3 and 4 are gone, and only hour 5 is offered.
    late = mod.resolve(_client(handler), now=T0 + timedelta(hours=5, minutes=5))
    assert late["checked"] == 1, late
    assert late["checkpoints"][0]["horizon"] == "5h", (
        "a stale hour was filled with a five-hour-old signal's current price")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_run_survives_a_round_that_raises_and_stops_on_the_event(tmp_path,
                                                                  monkeypatch):
    """The same rule scripts/sampler.py::run follows: nothing a round does may
    end the loop, because this is meant to run for hours inside a server the
    operator started once. A fake `stop` (a threading.Event set after N
    waits) stands in for time."""
    import threading

    mod = _module(tmp_path, monkeypatch)

    # The exception has to reach run()'s OWN guard. Raising it from the HTTP
    # handler does not: it surfaces inside `_hot_rows`, which capture() already
    # swallows per chain, so the guard this test is named for was never
    # exercised -- deleting run()'s whole try/except left the test green.
    # L02, deep pass of 2026-09-13, triage 3/3. So the round itself raises.
    rounds_seen = []

    def exploding_capture(client, now=None):
        rounds_seen.append(1)
        if len(rounds_seen) == 2:
            raise RuntimeError("the diary could not be written")
        return {"added": 0, "signals": [], "errors": [], "unidentified": 0}

    monkeypatch.setattr(mod, "capture", exploding_capture)
    monkeypatch.setattr(mod, "resolve",
                        lambda client, now=None: {"checked": 0,
                                                  "checkpoints": []})
    client = _client(lambda r: httpx.Response(200, json={"rows": []}))

    class _CountingEvent(threading.Event):
        def wait(self, timeout=None):  # noqa: D102 -- stand-in for real time
            self.rounds = getattr(self, "rounds", 0) + 1
            if self.rounds >= 3:
                self.set()
            return self.is_set()

    fast_stop = _CountingEvent()
    rounds = mod.run(fast_stop, every=0, client=client)
    assert rounds == 3, "a round that raised must not end the loop early"
    assert len(rounds_seen) == 3, (
        "the round that raised must have been REACHED three times; if the "
        "exception never got past capture() this test proves nothing")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_radars_own_gate_fields_are_kept_beside_our_reading(tmp_path,
                                                                monkeypatch):
    """Cymetica shipped a tradeability gate on 2026-09-14 and told us its
    unit: `max_buy_5pct_usd >= 500`, with the refused burst left on the row as
    `hot_pressure` and a `thin` flag beside it.

    Their gate reads THEIR number at the moment it fires. Ours is a separate
    quote from memecoin-terminal, taken a second later against a different
    source, and the two will not always agree -- so a signal has to carry both
    or we can never say whether a row that got through was mis-gated or just
    moved. Prefixed `radar_`, because `liquidity_usd` already means our own
    reading on these rows and one name for two measurements is how a figure
    ends up compared with itself.

    This is the same lesson as the depth fields one commit earlier: what is in
    the response at capture time is the only chance to keep it.
    """
    mod = _module(tmp_path, monkeypatch)
    radar = {"token_address": "SoL1", "hot": True, "symbol": "OTC",
             "conviction": 75.8, "conviction_kind": "buy-pressure",
             "signal_type": "hot", "liquidity_usd": 620579.53,
             "max_buy_5pct_usd": 31028.98, "hot_pressure": True,
             "thin": False, "token_age_seconds": 100.0,
             "usd_invested": 302307.38, "page_url": "https://example.invalid"}

    def handler(request):
        url = str(request.url)
        if "fomo-radar/signals" in url:
            if request.url.params.get("chain") != "solana":
                return httpx.Response(200, json={"rows": []})
            return httpx.Response(200, json={"rows": [radar]})
        return httpx.Response(200, json={"rows": [
            {"address": request.url.params.get("q"), "price_usd": 0.054,
             "liquidity_usd": 618000.0, "volume_h24": 302307.38}]})

    mod.capture(_client(handler), now=T0)
    signal = [r for r in mod.load() if r["type"] == "signal"][0]

    assert signal["radar_liquidity_usd"] == 620579.53
    assert signal["radar_max_buy_5pct_usd"] == 31028.98
    assert signal["radar_hot_pressure"] is True and signal["radar_thin"] is False
    assert signal["radar_signal_type"] == "hot"
    assert signal["radar_token_age_seconds"] == 100.0

    # Ours is still ours, under its own name, from the other source.
    assert signal["liquidity_usd"] == 618000.0 and signal["price_usd"] == 0.054
    assert "page_url" not in signal, "only the fields we named"

    # A chain that serves none of the gate fields -- solana on the day they
    # shipped -- writes the signal without inventing them.
    def ungated(request):
        url = str(request.url)
        if "fomo-radar/signals" in url:
            if request.url.params.get("chain") != "solana":
                return httpx.Response(200, json={"rows": []})
            return httpx.Response(200, json={"rows": [
                {"token_address": "SoL2", "hot": True, "symbol": "CHADSTER",
                 "conviction": 18.1, "liquidity_usd": 75.16}]})
        return httpx.Response(200, json={"rows": []})

    mod.capture(_client(ungated), now=T0 + timedelta(hours=1))
    second = [r for r in mod.load()
              if r["type"] == "signal" and r["token_address"] == "SoL2"][0]
    assert second["radar_liquidity_usd"] == 75.16
    assert "radar_max_buy_5pct_usd" not in second
    assert "radar_hot_pressure" not in second


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_failed_read_never_writes_a_delisting(tmp_path, monkeypatch):
    """Rule 8, on the round that seeds depth for tokens whose 24h of
    checkpoints is over.

    `depth()` has to tell two things apart that `_quote()` returns
    identically: a 200 carrying no matching row, which means their terminal
    has stopped listing the token, and a 503, which means nothing at all. The
    first is a fact worth writing (`listed: false`, and the filter drops the
    token); the second must write NOTHING, or a bad ten minutes on their side
    marks a hundred live coins delisted and takes them off the page for good.

    Written before `depth()` existed, so the branch cannot be shaped by what
    the code happens to do.
    """
    mod = _module(tmp_path, monkeypatch)

    def handler(request):
        url = str(request.url)
        if "fomo-radar/signals" in url:
            if request.url.params.get("chain") != "solana":
                return httpx.Response(200, json={"rows": []})
            return httpx.Response(200, json={"rows": [
                _fomo_row("SoLfine"), _fomo_row("SoLgone"), _fomo_row("SoL503")]})
        wanted = request.url.params.get("q")
        if wanted == "SoL503":
            return httpx.Response(503, json={"detail": "upstream"})
        if wanted == "SoLgone":
            return httpx.Response(200, json={"rows": []})
        return httpx.Response(200, json={"rows": [
            {"address": wanted, "price_usd": 0.002, "liquidity_usd": 9000.0,
             "volume_h24": 4000.0}]})

    client = _client(handler)
    mod.capture(client, now=T0)
    result = mod.depth(client, now=T0 + timedelta(minutes=5))

    written = {r["token_address"]: r for r in mod.load() if r["type"] == "depth"}
    assert set(written) == {"SoLfine", "SoLgone"}, (
        f"a failed read wrote a depth row: {sorted(written)}")
    assert written["SoLfine"]["listed"] is True
    assert written["SoLfine"]["liquidity_usd"] == 9000.0
    assert written["SoLgone"]["listed"] is False, (
        "a 200 with no matching row IS a delisting and must be recorded")
    assert result["failed"] == 1 and result["written"] == 2, result

    # And the filter believes it: the token they still quote survives, the
    # one they dropped does not, and the one whose read failed is unknown --
    # which keeps it, because unknown is not a verdict.
    from qa import fomo

    counts = fomo.basket(mod.load())
    assert counts["n_tradeable"] == 1 and counts["n_untradeable"] == 1
    assert counts["n_depth_unknown"] == 1


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_price_is_written_with_the_depth_it_was_quoted_at(tmp_path,
                                                            monkeypatch):
    """The single biggest number this diary holds is +73848%, MelonMusk, and
    read live on 2026-09-14 its pair quotes `liquidity_usd: 0.02` against
    `volume_h24: 0.25`. Two cents of depth. The return is arithmetically
    right and could not have been taken by anybody.

    That is not their defect -- DexScreener repeats the last print until
    somebody trades again and their terminal passes it through -- and it was
    in the SAME response the price came out of. We kept the price and dropped
    the rest, so nine hundred signals of history cannot now be re-judged
    against what was tradeable. Kept from here on, on both row types.
    """
    mod = _module(tmp_path, monkeypatch)
    quote = {"price_usd": 0.002, "liquidity_usd": 0.02, "volume_h24": 0.25,
             "market_cap": 45160641.0, "buys_h24": 23, "sells_h24": 11,
             "age_seconds": 46877, "dex": "meteora", "name": "Melon Musk",
             "pair_address": "PairMeteora1"}

    def handler(request):
        url = str(request.url)
        if "fomo-radar/signals" in url:
            if request.url.params.get("chain") != "solana":
                return httpx.Response(200, json={"rows": []})
            return httpx.Response(200, json={"rows": [_fomo_row("SoL1")]})
        if "memecoin-terminal/search" in url:
            return httpx.Response(200, json={"rows": [
                {**quote, "address": request.url.params.get("q")}]})
        return httpx.Response(404)

    client = _client(handler)
    mod.capture(client, now=T0)
    signal = [r for r in mod.load() if r["type"] == "signal"][0]
    assert signal["price_usd"] == 0.002
    assert signal["liquidity_usd"] == 0.02 and signal["volume_h24"] == 0.25
    assert signal["dex"] == "meteora" and signal["buys_h24"] == 23
    assert "name" not in signal, "only the fields we named, not the whole row"

    mod.resolve(client, now=T0 + timedelta(hours=1, minutes=1))
    check = [r for r in mod.load() if r["type"] == "checkpoint"][0]
    assert check["horizon"] == "1h"
    assert check["liquidity_usd"] == 0.02, (
        "depth on the signal alone cannot say whether the EXIT was tradeable")
    # 2026-09-22: their terminal answered one address with different pairs
    # from hour to hour (JUP 1437.39 -> 0.2782). Which pair a price came from
    # is what a check on that has to read, on the entry and on every exit.
    assert signal["pair_address"] == "PairMeteora1"
    assert check["pair_address"] == "PairMeteora1"

    # A quote that carries none of it still writes the price. Their rows are
    # not all the same shape and a missing field is not a failed read.
    def bare(request):
        url = str(request.url)
        if "fomo-radar/signals" in url:
            if request.url.params.get("chain") != "solana":
                return httpx.Response(200, json={"rows": []})
            return httpx.Response(200, json={"rows": [_fomo_row("SoL2")]})
        if "memecoin-terminal/search" in url:
            return httpx.Response(200, json={"rows": [
                {"address": request.url.params.get("q"), "price_usd": 9.0}]})
        return httpx.Response(404)

    mod.capture(_client(bare), now=T0 + timedelta(hours=2))
    second = [r for r in mod.load()
              if r["type"] == "signal" and r["token_address"] == "SoL2"][0]
    assert second["price_usd"] == 9.0 and "liquidity_usd" not in second

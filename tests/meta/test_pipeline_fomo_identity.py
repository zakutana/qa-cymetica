"""The decision behind the FOMO Radar identity check, without the network.

The live check is `tests/rest/test_fomo_radar_names_its_tokens.py`. What is
unit-tested here is the judgement it makes, because that judgement changed on
2026-09-13 after Cymetica root-caused the outage we saw at 09:52 UTC:

    "a restart on our side made a fresh process serve rows before its
    curve->token lookup had caught up. Identities are now carried across
    restarts, and the signals payload reports identities_pending (normally 0)
    so your check can read it directly."

That field turns a guess into a reading. A feed that is anonymous AND says
`identities_pending: 40` is telling us it is catching up -- the disclosed,
self-healing state, and not a defect. A feed that is anonymous while saying
`identities_pending: 0` is claiming it has nothing left to resolve and still
serving rows nobody can act on, which is a sharper finding than the one the
check could make yesterday.

Their field is theirs, so the check must not FALL OVER when it goes away: a
payload without it drops back to the cross-chain comparison the check used
before it existed. Tested in both directions, because a fallback nobody
exercises is a branch that only runs the day it matters.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


def _check():
    spec = importlib.util.spec_from_file_location(
        "fomo_identity_check",
        REPO / "tests" / "rest" / "test_fomo_radar_names_its_tokens.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _gap(anonymous: int, named: int) -> dict:
    total = anonymous + named
    return {"anonymous": [{}] * anonymous, "named": [{}] * named,
            "total": total, "share": (anonymous / total) if total else 0.0}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_what_counts_as_anonymous_is_read_from_their_real_rows():
    """L03, deep pass of 2026-09-13, triage 3/3. The function that decides
    what the whole check MEANS was exercised nowhere.

    Every other test in this file builds the gap dict itself, with the share
    already computed -- so `identity_gap`, which decides that their placeholder
    `name: "Unnamed launch"` is not an identity, had no caller but the live
    check. Drop that one rule and the real 09:52 outage rows classify as
    NAMED, share 0.0, `decide` returns `passed`, and all four tests stayed
    green on the live defect they were written for. The mirror is worse: make
    it count a row that has a symbol but no address and an ordinary day
    crosses THRESHOLD, sending a false accusation to their tracker.

    The rows below are the shapes actually served, on both sides.
    """
    mod = _check()

    # Their outage, verbatim: conviction real, every identity field blank or
    # the placeholder.
    outage = [{"conviction": 68.5, "token_address": "", "symbol": "",
               "name": "Unnamed launch", "hot": True} for _ in range(40)]
    gap = mod.identity_gap(outage)
    assert gap["total"] == 40 and len(gap["anonymous"]) == 40, gap
    assert gap["share"] == 1.0

    # A healthy Robinhood row, and a Solana row: both name the token.
    healthy = [{"conviction": 88.3, "token_address": "0xabc", "symbol": "NIU",
                "name": "Niu Lai"},
               {"conviction": 12.0, "token_address": "SoL111", "symbol": "POK",
                "name": "Pokemon"}]
    gap = mod.identity_gap(healthy)
    assert len(gap["named"]) == 2 and gap["share"] == 0.0, gap

    # A row with a symbol and no address is still RESOLVABLE, so it is not
    # anonymous -- counting it would make an ordinary day cross the threshold
    # and send them a finding about nothing.
    partial = [{"conviction": 50.0, "token_address": "", "symbol": "ASTRO",
                "name": "Astro"}]
    assert len(mod.identity_gap(partial)["named"]) == 1

    # And a row with no conviction is not a signal at all, so it is neither.
    assert mod.identity_gap([{"token_address": "", "symbol": ""}])["total"] == 0


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_their_own_counter_cannot_excuse_the_whole_feed_for_ever():
    """V06, deep pass of 2026-09-13, triage 3/3. A threshold taken from their
    side, with no bound.

    `identities_pending > 0` ended the measurement before Solana was even
    consulted -- so `identities_pending: 1` served permanently, beside 40 of 40
    Robinhood rows anonymous and 40 of 40 Solana rows named, was inconclusive
    for ever. Rule 10 means an inconclusive is never filed, so one stuck
    counter would have made the defect this check was written for this morning
    unreportable. Nothing in the branch distinguished self-healing from stuck.

    A pending count excuses the rows it can account for, not all of them.
    """
    mod = _check()

    # Catching up: as many pending as there are anonymous rows. Still theirs.
    assert mod.decide(_gap(40, 0), _gap(0, 40), pending=40)[0] == "inconclusive"
    assert mod.decide(_gap(40, 0), _gap(0, 40), pending=38)[0] == "inconclusive"

    # One pending identity cannot account for forty anonymous rows.
    verdict, why = mod.decide(_gap(40, 0), _gap(0, 40), pending=1)
    assert verdict == "failed", why
    assert "1" in why and "40" in why, why
    # And the reason may not put words in their payload: a counter of 5 is
    # not "nothing left to resolve" (V06, deep pass of 2026-09-19, 3/3). That
    # sentence goes to their tracker.
    verdict, why = mod.decide(_gap(30, 0), _gap(0, 40), pending=5)
    assert verdict == "failed" and "nothing left" not in why, why
    verdict, why = mod.decide(_gap(30, 0), _gap(0, 40), pending=0)
    assert verdict == "failed" and "nothing left" in why, why


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_hot_rows_are_the_ones_measured_when_there_are_enough():
    """V06 (3/3): the check is about a HOT signal naming its token, and it
    measured every row with a conviction. Seventeen hot rows all anonymous
    beside twenty-three cold ones named came to 43% and a PASS."""
    mod = _check()
    hot = [{"hot": True, "conviction": 80, "token_address": ""}] * 17
    cold = [{"hot": False, "conviction": 20, "token_address": f"0x{n}"}
            for n in range(23)]

    basis, rows = mod.measured_rows(hot + cold)

    assert basis == "hot" and len(rows) == 17
    assert mod.identity_gap(rows)["share"] == 1.0
    # Too few hot rows to judge a share on: every row with a conviction.
    basis, rows = mod.measured_rows(hot[:2] + cold)
    assert basis == "all" and len(rows) == 25


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_both_chains_anonymous_is_their_indexer_whatever_the_counter_says():
    """The other half of V06. Both docstrings say a day when both chains are
    empty reads as their indexer being down -- a different fault, inconclusive
    -- and the `pending=None` path honoured that while the `pending=0` path
    returned `failed` and would have filed it."""
    mod = _check()
    assert mod.decide(_gap(40, 0), _gap(40, 0), pending=None)[0] == "inconclusive"
    assert mod.decide(_gap(40, 0), _gap(40, 0), pending=0)[0] == "inconclusive"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_feed_still_catching_up_after_a_restart_is_not_a_defect():
    """Their disclosed transient. `identities_pending` above zero beside
    anonymous rows is the feed saying so itself, and rule 10 holds: an empty
    measurement is not filed."""
    mod = _check()
    verdict, why = mod.decide(_gap(40, 0), _gap(0, 40), pending=40)
    assert verdict == "inconclusive", why
    assert "pending" in why.lower()


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_anonymous_while_claiming_nothing_is_pending_is_the_finding():
    """The sharp case: the feed says it has resolved everything and serves 40
    rows nobody can identify. Yesterday's check could only compare chains;
    this reads their own claim back to them."""
    mod = _check()
    verdict, why = mod.decide(_gap(40, 0), _gap(0, 40), pending=0)
    assert verdict == "failed", why
    assert "identities_pending" in why


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_without_their_field_it_falls_back_to_comparing_the_two_chains():
    """`identities_pending` is theirs and may go away. The check must keep
    working on the evidence it had before the field existed -- one chain
    anonymous while the other is named."""
    mod = _check()
    verdict, why = mod.decide(_gap(40, 0), _gap(0, 40), pending=None)
    assert verdict == "failed", why
    assert "solana" in why.lower()

    # Both chains anonymous stays their indexer rather than this finding,
    # with or without the field.
    verdict, why = mod.decide(_gap(40, 0), _gap(40, 0), pending=None)
    assert verdict == "inconclusive", why

    # A08, deep pass of 2026-09-21: a solana feed with NO rows has share 0.0,
    # which is "not anonymous", so the fallback filed "fills 0 of 0 solana
    # rows ... one chain's identity resolution" -- a comparison with nothing
    # on one side. The same with their counter at 0, which the both-chains
    # guard excuses only when solana is anonymous, not when it is empty.
    for pending in (None, 0):
        verdict, why = mod.decide(_gap(40, 0), _gap(0, 0), pending=pending)
        assert verdict == "inconclusive", (pending, why)
        assert "0 of 0" not in why, why
    # An empty yardstick takes nothing from a feed that names its tokens:
    # that pass stands on robinhood's own rows, and says no "0 of 0".
    verdict, why = mod.decide(_gap(0, 40), _gap(0, 0), pending=0)
    assert verdict == "passed" and "0 of 0" not in why, why
    # And the finding is still made when there IS a yardstick.
    assert mod.decide(_gap(40, 0), _gap(0, 1), pending=None)[0] == "failed"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_identity_check_run_whole_on_an_empty_solana_feed(monkeypatch):
    """A08 through the check itself, not only through `decide`: their docs,
    forty anonymous robinhood rows and a solana feed serving none. The finding
    rests on solana naming what robinhood does not, and there is no solana."""
    import contextvars
    import types

    from qa.marks import Inconclusive

    mod = _check()
    anonymous = [{"conviction": 68.5, "token_address": "", "symbol": "",
                  "name": "Unnamed launch", "hot": True} for _ in range(40)]

    class _Answer:
        status_code = 200

        def __init__(self, body):
            self.body = body

        def json(self):
            return self.body

    def get(path, **kw):
        if path == mod.DOCS:
            return _Answer({"summary": "which tokens credible wallets buy"})
        if "chain=solana" in path:
            return _Answer({"rows": []})
        return _Answer({"rows": anonymous})

    def run():
        try:
            mod.test_a_hot_signal_names_the_token_it_is_a_signal_about(
                types.SimpleNamespace(get=get))
        except Inconclusive as exc:
            return "inconclusive", str(exc)
        except AssertionError as exc:
            return "failed", str(exc)
        return "passed", ""

    verdict, why = contextvars.copy_context().run(run)
    assert verdict == "inconclusive", (verdict, why)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_healthy_feed_passes_and_one_stray_unnamed_launch_does_not_fire():
    """A single unresolved curve in a new-pair feed is ordinary. The verdict
    is a proportion for exactly this reason, and the threshold is what keeps
    an ordinary day from reading as an outage."""
    mod = _check()
    assert mod.decide(_gap(0, 40), _gap(0, 40), pending=0)[0] == "passed"
    assert mod.decide(_gap(1, 39), _gap(0, 40), pending=0)[0] == "passed"
    # ... and the threshold is a real boundary, not decoration.
    assert mod.decide(_gap(39, 1), _gap(0, 40), pending=0)[0] == "failed"

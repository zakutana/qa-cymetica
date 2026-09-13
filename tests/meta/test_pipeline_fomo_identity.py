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

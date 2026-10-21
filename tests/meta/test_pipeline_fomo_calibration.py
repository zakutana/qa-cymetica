"""The FOMO calibration check, run whole, without the network.

The live check is `tests/rest/test_fomo_calibration_reproduces.py`: their
published hot hit rate, per chain, against what the same feed's signals did
over the horizon it names. It rejects only over at least `MIN_SIGNALS`
completed windows, and its docstring says a chain with too few is
INCONCLUSIVE -- rule 10, nothing measured is neither a pass nor a defect.

A file of its own because each FOMO check has one (`fomo_identity`,
`fomo_floor`), and `test_pipeline_fomo_control.py` drives a different module
-- `scripts/fomo_watch.py`, the recorder of the study -- not this verdict.

The check is driven WHOLE, through a stub client, with `diary()` and
`qa.fomo.compare` replaced: the study's rows (signals, controls, horizon
checkpoints) are `compare`'s business and have their own tests; what is under
test here is what the check concludes from the counts `compare` hands back.
Nothing here reads `state/fomo_signals.jsonl`.
"""

from __future__ import annotations

import contextvars
import importlib.util
import types
from pathlib import Path

from qa.marks import Inconclusive, SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent

# Their block as served on 2026-09-21, marked sufficient so there IS a claim.
CALIBRATION = {"calibration": {
    "target_multiple": 3.0, "horizon_hours": 72,
    "type_precision": {"hot": {"n": 171, "hits": 19, "precision": 0.112,
                               "sufficient": True, "ci_low": 0.07,
                               "ci_high": 0.17}}}}


def _check():
    spec = importlib.util.spec_from_file_location(
        "fomo_calibration_check",
        REPO / "tests" / "rest" / "test_fomo_calibration_reproduces.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Answer:
    def __init__(self, status: int, body=None):
        self.status_code, self._body = status, body

    def json(self):
        return self._body


def _drive(monkeypatch, windows: dict, horizon_hours: float = 24,
           asked: list | None = None) -> tuple[str, str, object]:
    """Run the check whole. `windows` is chain -> (completed windows, hits),
    the counts `compare` reports for that chain's hot arm. Their claim is
    CALIBRATION with `horizon_hours` put in -- 24 by default, a horizon our
    record reads hourly all the way (A09, deep pass of 2026-09-22).

    In a copied context, so the measurement the check emits stays out of this
    meta test's own run record."""
    import qa.fomo
    from qa.measure import CURRENT_MEASUREMENT

    mod = _check()
    monkeypatch.setattr(mod, "diary", lambda: [{"type": "signal", "key": "k"}])
    order = iter(mod.CHAINS)

    def compare(rows, **kw):
        if asked is not None:
            asked.append(kw)
        n, hits = windows[next(order)]
        return {"hot": {"n": n, "hits": hits}}

    monkeypatch.setattr(qa.fomo, "compare", compare)
    claim = {"calibration": {**CALIBRATION["calibration"],
                             "horizon_hours": horizon_hours}}
    client = types.SimpleNamespace(
        get=lambda path, params=None: _Answer(200, claim))

    def run():
        try:
            mod.test_the_radars_published_hit_rate_reproduces_on_its_own_signals(
                client)
        except Inconclusive as exc:
            return "inconclusive", str(exc), CURRENT_MEASUREMENT.get()
        except AssertionError as exc:
            return "failed", str(exc), CURRENT_MEASUREMENT.get()
        return "passed", "", CURRENT_MEASUREMENT.get()

    return contextvars.copy_context().run(run)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_chain_with_too_few_windows_is_not_a_chain_that_was_measured(
        monkeypatch):
    """A04, deep pass of 2026-09-21. Nothing measured passed.

    `facts[chain]` was written BEFORE the `n < MIN_SIGNALS` skip, and the
    inconclusive branch asked `not problems and not facts` -- so with every
    chain under the minimum, `facts` was full of chains nobody had tested and
    the check concluded `passed` over zero judged windows. A pass is what
    verify.py sends.
    """
    verdict, reason, _ = _drive(monkeypatch, {"solana": (5, 0),
                                              "robinhood": (12, 0)})
    assert verdict == "inconclusive", (
        f"two chains under the {_check().MIN_SIGNALS} windows a zero means "
        f"anything at concluded {verdict}: {reason}")
    assert "solana: only 5" in reason and "robinhood: only 12" in reason, reason


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_calibration_check_still_says_no_and_still_says_yes(monkeypatch):
    """The two directions the A04 repair must leave standing, and what a
    skipped chain may not do to either.

    0 of 44 against their 11.2% is the reading the check was written on
    (0.888^44, about one in two hundred) and must still fail -- beside a chain
    that was skipped. 5 of 40 is ordinary noise and must pass. In both, the
    skipped chain is in the reason and NOT in the population the verdict
    stands on.
    """
    verdict, reason, m = _drive(monkeypatch, {"solana": (44, 0),
                                              "robinhood": (7, 0)})
    assert verdict == "failed", reason
    assert "0 of the 44" in reason, reason
    assert set(m.population) == {"solana"}, (
        f"a chain with 7 windows is in the population of a verdict it took "
        f"no part in: {m.population}")

    verdict, reason, m = _drive(monkeypatch, {"solana": (40, 5),
                                              "robinhood": (7, 0)})
    assert verdict == "passed", reason
    assert "5/40" in m.reason and "robinhood: only 7" in m.reason, m.reason
    assert set(m.population) == {"solana"}, m.population


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_peak_we_did_not_sample_cannot_refute_their_rate(monkeypatch):
    """A09, deep pass of 2026-09-22 (3/3). Their rate is the PEAK inside the
    window over every hot signal. Ours was the peak of the readings we took
    -- hourly to 24 h, nothing between that and 72 h -- over the signals our
    depth filter kept, so a coin that tripled at hour 40 and fell back was a
    miss. That count is a lower bound: it can confirm their rate, never
    refute it past the horizon we read. And no depth filter: their claim is
    about their whole feed."""
    asked: list = []
    verdict, reason, _ = _drive(monkeypatch, {"solana": (44, 0),
                                              "robinhood": (7, 0)},
                                horizon_hours=72, asked=asked)
    assert verdict == "inconclusive", (verdict, reason)
    assert "lower bound" in reason, reason
    assert asked and all(kw.get("require_depth") is False for kw in asked), (
        f"the calibration was read through the depth filter: {asked}")

    verdict, reason, _ = _drive(monkeypatch, {"solana": (40, 5),
                                              "robinhood": (7, 0)},
                                horizon_hours=72)
    assert verdict == "passed", reason


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_calibration_counts_signals_whose_depth_was_never_read():
    """A09's other half, in qa.fomo.compare: `require_depth=False` counts a
    signal nobody read depth for, which the study (whose question is what
    could be BOUGHT) rightly drops."""
    from datetime import datetime, timezone

    from qa import fomo

    rows = [{"type": "signal", "key": "k", "at": "2026-09-10T00:00:00+00:00",
             "price_usd": 1.0},
            {"type": "checkpoint", "key": "k", "horizon": "6h",
             "at": "2026-09-10T06:00:00+00:00", "price_usd": 3.5}]
    now = datetime(2026, 9, 20, tzinfo=timezone.utc)
    kept = fomo.compare(rows, multiple=3.0, within_hours=24, now=now,
                        min_liquidity=0, min_volume=0)
    assert kept["hot"]["n"] == 0, kept
    whole = fomo.compare(rows, multiple=3.0, within_hours=24, now=now,
                         min_liquidity=0, min_volume=0, require_depth=False)
    assert (whole["hot"]["n"], whole["hot"]["hits"]) == (1, 1), whole


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_tail_probability_survives_a_diary_of_thousands_of_windows():
    """2026-10-21: the sweep's check died with OverflowError ("int too large to convert to
    float") because the tail multiplied math.comb(n, i) -- an exact integer, a thousand digits
    long once n passed ~1030 -- by a float. The diary only grows, so the check would have
    crashed on every later sweep. A crash is not a verdict; the tail must be computed in logs."""
    import math

    tail = _check().improbability
    # Small n against the exact definition.
    exact = sum(math.comb(20, i) * 0.3 ** i * 0.7 ** (20 - i) for i in range(6))
    assert abs(tail(5, 20, 0.3) - exact) < 1e-12
    # Large n: finite, a probability, and ordered the way a tail must be.
    low, mid, high = tail(100, 5000, 0.112), tail(560, 5000, 0.112), tail(900, 5000, 0.112)
    assert 0.0 <= low <= 1.0 and 0.0 <= mid <= 1.0 and 0.0 <= high <= 1.0
    assert low < 1e-100 and 0.3 < mid < 0.7 and high > 0.999999, (low, mid, high)
    assert abs(tail(5000, 5000, 0.112) - 1.0) < 1e-9

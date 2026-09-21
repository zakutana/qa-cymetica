"""The FOMO radar's published calibration, against the signals it published.

Every `/clones/fomo-radar/signals` response carries a `calibration` block: the
feed's own statement of how often a coin it calls `hot` reaches a multiple
inside a horizon. On 2026-09-21 the solana feed published 11.2% of 171 for
3x inside 72 hours, against a base rate of 4.32%.

We have recorded that feed since 2026-09-13 -- 2,072 signals, with price
checkpoints at each horizon -- so the claim is checkable against the feed's
own output, on the horizon it names, judged the way it words it: the PEAK
inside the window, so a coin that tripled at hour twenty and fell back did
reach 3x.

Measured 2026-09-21 over every solana `hot` signal whose 72-hour window had
fully passed: **0 of 44**. Under their published 11.2% the chance of seeing
no hit in 44 tries is 0.888^44, about one in two hundred.

WHY THE CONTROL ARM IS NOT NEEDED HERE, which is where this check began.
Our study scores `hot` against a control drawn from the same rounds, and that
arm is too young to have completed a 72-hour window -- so we set the question
aside as unanswerable. It is not: this is a claim about the hot arm alone, and
a within-arm reading needs no control. That correction came from Nexus
(NEX-0051), asked about which of the radar's fields to trade on.

WHAT IT ASSERTS. Only that the feed's own published rate for a horizon is
consistent with what the same feed's signals did over that horizon, per chain,
tested against the binomial the claim implies. It rejects only at 1% -- a
one-in-a-hundred coincidence is not a defect in a thing that resolves this
noisily -- and only over at least MIN_SIGNALS completed windows.

WHAT IT DOES NOT. No depth filter: our study only counts coins deep enough to
buy, and the calibration block makes no such claim, so filtering here would
hold them to a population they never described. Not their sample either --
their 171 is their own history and ours is a fortnight of it; what is being
compared is their published RATE against our observed one, never one count
against another.

INCONCLUSIVE when the feed publishes no rate for that horizon, when too few
windows have passed, or when the response cannot be read -- rule 8, and the
reason says which.

SAFE. One GET per chain, no key, and our own diary.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

SIGNALS = "/api/v1/clones/fomo-radar/signals"
CHAINS = ("solana", "robinhood")
# Below this many completed windows a zero says little: at n=20 even a true
# 11% rate gives no hits about one time in ten.
MIN_SIGNALS = 30
# One in a hundred. Deliberately far from the usual 5%: this resolves noisily
# and a report is expensive to be wrong about.
REJECT_AT = 0.01


def diary() -> list[dict]:
    from qa.state import state_dir

    path = Path(state_dir()) / "fomo_signals.jsonl"
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    return out


def published(body: dict) -> dict | None:
    """Their claim for a multiple and a horizon, or None.

    `type_precision.hot` is where the figure lives, and it arrives with two
    things that decide whether there is a claim at all: a confidence interval,
    and `sufficient`. On 2026-09-21 it read n 137, hits 19, ci 9.1-20.6%, and
    **sufficient false** -- they say themselves the sample is not enough. A
    number a publisher flags as insufficient is not an assertion, and holding
    them to it would be us inventing the claim and then refuting it.

    That is how this check was nearly filed as a defect: our own report line
    printed their `display` string, "hot 11.2% of 171", as "their claim", and
    the sufficiency flag beside it never travelled with the number.
    """
    block = body.get("calibration")
    if not isinstance(block, dict):
        return None
    hot = (block.get("type_precision") or {}).get("hot") \
        if isinstance(block.get("type_precision"), dict) else None
    if not isinstance(hot, dict):
        return None
    if hot.get("sufficient") is not True:
        return {"insufficient": True, "n": hot.get("n"), "hits": hot.get("hits")}
    rate = hot.get("precision")
    if not (isinstance(rate, (int, float)) and 0 < rate < 1):
        return None
    return {"rate": float(rate), "sample": hot.get("n"),
            "ci": (hot.get("ci_low"), hot.get("ci_high")),
            "multiple": float(block.get("target_multiple") or 3.0),
            "horizon_hours": float(block.get("horizon_hours") or 72.0)}


def improbability(hits: int, n: int, rate: float) -> float:
    """P(at most this many hits) if their published rate were true."""
    return sum(math.comb(n, i) * rate ** i * (1 - rate) ** (n - i)
               for i in range(hits + 1))


@qa(component="rest.clones", tier=SafetyTier.SAFE, surface="rest")
def test_the_radars_published_hit_rate_reproduces_on_its_own_signals(rest_anon):
    """Their calibration block, against the feed it describes."""
    from qa import fomo

    rows = diary()
    if not rows:
        raise Inconclusive(
            "no recorded signals on this machine, so their published rate has "
            "nothing of theirs to be held against")

    now = datetime.now(timezone.utc)
    problems, said, facts = [], [], {}
    for chain in CHAINS:
        response = rest_anon.get(SIGNALS, params={"chain": chain})
        if response.status_code != 200:
            said.append(f"{chain}: HTTP {response.status_code}, not read")
            continue
        claim = published(response.json() or {})
        if claim is None:
            said.append(f"{chain}: publishes no hit rate to check")
            continue
        if claim.get("insufficient"):
            said.append(f"{chain}: they publish {claim.get('hits')} of "
                        f"{claim.get('n')} and mark the sample "
                        f"`sufficient: false` themselves, so there is no "
                        f"claim of theirs to hold them to")
            continue

        mine = [r for r in rows
                if r.get("chain") == chain or r.get("type") not in ("signal", "control")]
        # No depth filter: their claim is about their own feed, not about the
        # subset we would trade.
        out = fomo.compare(mine, multiple=claim["multiple"],
                           within_hours=claim["horizon_hours"], now=now,
                           min_liquidity=0, min_volume=0)
        hot = out.get("hot") or {}
        n, hits = int(hot.get("n") or 0), int(hot.get("hits") or 0)
        if n < MIN_SIGNALS:
            said.append(f"{chain}: only {n} window(s) of theirs have fully "
                        f"passed, under the {MIN_SIGNALS} a zero would mean "
                        f"anything at")
            continue
        # Only a chain that was JUDGED enters `facts`: it is what the
        # inconclusive branch below counts as measured, and it was written
        # before this skip, so two chains under the minimum concluded
        # `passed` over nothing (A04, deep pass of 2026-09-21). A skipped
        # chain's count stays in the reason.
        facts[chain] = {"published_rate": claim["rate"], "their_n": claim["sample"],
                        "our_windows": n, "our_hits": hits}
        p = improbability(hits, n, claim["rate"])
        facts[chain]["improbability"] = round(p, 6)
        if p < REJECT_AT:
            problems.append(
                f"{chain}: they publish {claim['rate'] * 100:.1f}% of their hot "
                f"signals reaching {claim['multiple']:.0f}x inside "
                f"{claim['horizon_hours']:.0f} h, and {hits} of the {n} hot "
                f"signals of theirs we recorded with a fully passed window did "
                f"-- one chance in {round(1 / p):,} if the published rate held")
        else:
            said.append(f"{chain}: {hits}/{n} against their published "
                        f"{claim['rate'] * 100:.1f}%, which is ordinary noise "
                        f"(p={p:.2f})")

    if not problems and not facts:
        raise Inconclusive("; ".join(said) or "neither chain could be read")

    conclude(Measurement(
        verdict="failed" if problems else "passed",
        reason="; ".join(problems) if problems else "; ".join(said),
        left={"ours": facts},
        right={"judged_on": "the peak inside the window, as their wording says",
               "depth_filtered": False},
        sources={"signals": SIGNALS, "our diary": "state/fomo_signals.jsonl"},
        population=facts))

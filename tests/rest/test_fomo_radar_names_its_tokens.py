"""A signal that names no token cannot be acted on.

FOMO Radar's whole proposition, in their own words on `/fomo-radar/docs`, is
*"which tokens credible wallets are buying right now on Robinhood Chain"*. A
row carries `conviction`, `qualified_buyers`, `usd_invested` and a `hot` flag
-- and `token_address`, `symbol` and `name` are what turn that judgement into
something a reader can buy, look up or measure.

**Measured 2026-09-13 11:52 UTC: every one of the 40 Robinhood-chain rows came
back with `token_address: ""`, `symbol: ""`, `name: "Unnamed launch"`,
`page_url: null` and `explorer_url: null`** -- 17 of them flagged `hot`, the
strongest at conviction 70.8 on 58 089 USD invested by 10 buyers. The same
call on `chain=solana` filled all 40. Only `curve_address` identifies the
Robinhood rows, and nothing else on their platform takes one: their own
Memecoin Terminal searches by *symbol, name or address* (its `/docs`), so a
Robinhood signal cannot be priced, charted or traded from what the radar says
about it.

**This is a regression inside one day, and our own captures are the before.**
At 06:00-07:00 UTC the same endpoint answered with real identities -- 38
distinct tokens across 61 signal rows, named (`ASTRO`, `Pokemon`, `LILI`,
`revolve`), addressed, and priceable: 23 of them resolved to a live price on
memecoin-terminal an hour later. Those rows are in `state/fomo_signals.jsonl`
and in the manifest. So the field is not one they never populated; it stopped
being populated between 07:00 and 11:52 UTC on 2026-09-13.

WHAT THIS CHECK ASSERTS, AND IN WHICH DIRECTION. Every claim here is that
something IS served: that their endpoint answered, that it returned rows, and
that a counted number of those rows carry an empty identity beside a
non-empty conviction. It never asserts a field is missing from a schema. The
comparison that makes it a defect rather than a quiet gap is between their own
two chains in the same response format -- Solana fills what Robinhood does
not -- so a day when both are empty reads as inconclusive (their indexer is
down, which is a different fault) rather than as this finding.

The population is the rows themselves and the verdict is a proportion, not a
single bad row: one unnamed launch mid-index is ordinary, and this check must
not fire on it. `THRESHOLD` is the share of Robinhood rows that must be
anonymous before the radar has stopped naming tokens at all.

SAFE. Keyless GETs, the two the tool publishes, no key sent and none needed.
"""

from __future__ import annotations

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

SIGNALS = "/api/v1/clones/fomo-radar/signals"
DOCS = "/api/v1/clones/fomo-radar/docs"

# Above this share of a chain's rows carrying no identity at all, the feed is
# not naming tokens. Set at two thirds rather than at 1.0 so a partially
# recovered indexer still reports, and well above the single "Unnamed launch"
# that is ordinary in any new-pair feed.
THRESHOLD = 0.66

# How much of the anonymity their own `identities_pending` has to account for
# before it excuses the feed. Below this, the counter is describing a backlog
# far smaller than the hole, and the hole is the finding. Not 1.0: a row can
# resolve between the count and the rows being serialised, so a little slack
# is honest. V06, deep pass of 2026-09-13.
ACCOUNTED_FOR = 0.9


def identity_gap(rows: list[dict]) -> dict:
    """How many rows carry a conviction and no way to identify the token.

    A row counts as anonymous only when it has a real signal to act on --
    `conviction` present -- and every one of the three identity fields their
    own row schema publishes is blank. A row with a symbol but no address is
    NOT counted: it is still resolvable, and over-counting here is how a check
    turns a partial degradation into a claim their whole feed is broken.
    """
    anonymous, named = [], []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("conviction") is None:
            continue
        identity = [str(row.get(field) or "").strip()
                    for field in ("token_address", "symbol", "name")]
        # "Unnamed launch" is their own placeholder for the `name` of a curve
        # whose metadata has not resolved; it identifies nothing, so it is not
        # an identity. Read off the live payload, not guessed.
        identity = [v for v in identity if v and v != "Unnamed launch"]
        (named if identity else anonymous).append(row)
    total = len(anonymous) + len(named)
    return {"anonymous": anonymous, "named": named, "total": total,
            "share": (len(anonymous) / total) if total else 0.0}


# The fewest hot rows a share is judged on. Below it, every row with a
# conviction is measured, as before -- a share of three rows is noise.
MIN_HOT = 5


def measured_rows(rows: list[dict]) -> tuple[str, list[dict]]:
    """The rows the verdict is about: the HOT ones, when there are enough.

    The contract is a hot signal naming its token, and every row with a
    conviction was measured -- so seventeen hot rows all anonymous beside
    twenty-three cold ones named came to 43% and a PASS (V06, deep pass of
    2026-09-19, 3/3).
    """
    hot = [r for r in rows if isinstance(r, dict) and r.get("hot")
           and r.get("conviction") is not None]
    if len(hot) >= MIN_HOT:
        return "hot", hot
    return "all", [r for r in rows if isinstance(r, dict)]


def decide(robinhood: dict, solana: dict, pending) -> tuple[str, str]:
    """The verdict, as a function of the two chains and their own counter.

    Split out of the check on 2026-09-13 so it can be exercised without the
    network, because the judgement changed that day and a judgement nobody can
    test is one that drifts. `pending` is their `identities_pending` -- an int
    when they serve it, None when they do not.

    Order matters. Their counter is read FIRST when it is present and the feed
    is anonymous: a feed that says it is still resolving is the disclosed,
    self-healing state they root-caused for us, and rule 10 says an empty
    measurement is not a defect. Only a feed claiming nothing is pending while
    serving nothing identifiable is the finding.
    """
    if not robinhood["total"]:
        return ("inconclusive",
                "their robinhood feed returned no row carrying a conviction, "
                "so there is no signal here to be anonymous -- an empty feed, "
                "not an unnamed one")

    anonymous = robinhood["share"] > THRESHOLD
    if not anonymous:
        # A pass stands on robinhood's own rows; solana is only the yardstick
        # of the failing direction, and an empty one is not quoted as "0 of 0".
        return ("passed",
                f"{len(robinhood['named'])} of {robinhood['total']} robinhood "
                f"rows name the token they are about, and "
                + (f"{len(solana['named'])} of {solana['total']} on solana"
                   if solana["total"] else
                   "solana served no row carrying a conviction this read"))

    # Their counter excuses the rows it can ACCOUNT FOR, not all of them.
    # `pending > 0` alone ended the measurement, so `identities_pending: 1`
    # served permanently beside forty anonymous rows was inconclusive for
    # ever -- and rule 10 means an inconclusive is never filed, so one stuck
    # counter would have made this defect unreportable. Nothing in that branch
    # told self-healing from stuck. V06, deep pass of 2026-09-13, triage 3/3.
    anonymous_rows = len(robinhood["anonymous"])
    if isinstance(pending, int) and pending >= anonymous_rows * ACCOUNTED_FOR:
        return ("inconclusive",
                f"{anonymous_rows} of {robinhood['total']} robinhood rows "
                f"carry no identity, and their own payload says "
                f"identities_pending={pending} -- enough to account for them, "
                f"so the feed is still resolving curve->token after a "
                f"restart, which is the transient they disclosed on "
                f"2026-09-13 and not a defect")

    # Every failing branch below rests on solana NAMING what robinhood does
    # not -- the docstring's comparison. An empty solana feed has share 0.0,
    # which read as "not anonymous", so the fallback filed "fills 0 of 0
    # solana rows ... one chain's identity resolution": a comparison with
    # nothing on one side (A08, deep pass of 2026-09-21). No yardstick, no
    # finding -- rule 10.
    if not solana["total"]:
        return ("inconclusive",
                f"{len(robinhood['anonymous'])} of {robinhood['total']} "
                f"robinhood rows carry no identity, and their solana feed "
                f"returned no row carrying a conviction -- so there is no "
                f"named chain to hold them against, and nothing to tell one "
                f"chain's identity resolution from their indexer being down")

    # Both chains anonymous is their token indexer, not one chain's identity
    # resolution -- the same judgement the no-counter path below makes, and
    # both docstrings say so. It used to be made only when they served no
    # counter, so `pending: 0` filed it.
    if solana["share"] > THRESHOLD:
        return ("inconclusive",
                f"both chains are anonymous ({robinhood['share']:.0%} and "
                f"{solana['share']:.0%}), which reads as their token indexer "
                f"being down rather than as one chain having stopped "
                f"resolving identity -- a different fault from this one")

    if isinstance(pending, int):
        # What their counter SAYS, and no more: "nothing left to resolve" was
        # written for every pending value, 5 included -- a sentence their
        # payload did not say, on its way to their tracker (V06, deep pass of
        # 2026-09-19, 3/3).
        said = ("-- the feed says it has nothing left to resolve"
                if pending == 0 else
                f"-- which accounts for at most {pending} of them")
        return ("failed",
                f"{len(robinhood['anonymous'])} of {robinhood['total']} "
                f"robinhood rows carry a conviction and no identity at all, "
                f"while the same payload reports identities_pending={pending} "
                f"{said}, and is serving rows no reader can act on. Their own "
                f"Memecoin Terminal searches by symbol, name or address, so "
                f"these signals cannot be priced or looked up anywhere on the "
                f"platform that raised them")

    # No counter served: back to the evidence the check had before the field
    # existed. Both chains anonymous is their indexer, a different fault.
    if solana["share"] > THRESHOLD:
        return ("inconclusive",
                f"both chains are anonymous ({robinhood['share']:.0%} and "
                f"{solana['share']:.0%}) and no identities_pending was "
                f"served, which reads as their token indexer being down "
                f"rather than as one chain having stopped resolving identity")
    return ("failed",
            f"{len(robinhood['anonymous'])} of {robinhood['total']} "
            f"robinhood-chain rows carry a conviction and no identity at all, "
            f"while the same endpoint fills {len(solana['named'])} of "
            f"{solana['total']} solana rows in the same response format, so "
            f"this is one chain's identity resolution rather than the feed's "
            f"shape")


def _payload(client, chain: str) -> dict:
    response = client.get(f"{SIGNALS}?chain={chain}&filter=all&limit=40")
    if response.status_code != 200:
        raise Inconclusive(
            f"{SIGNALS} (chain={chain}) answered HTTP "
            f"{response.status_code}; a failed read is not an empty feed")
    try:
        return response.json() or {}
    except ValueError as exc:
        raise Inconclusive(f"{SIGNALS} (chain={chain}) is not JSON: {exc}")


@qa(component="rest.clones", tier=SafetyTier.SAFE, surface="rest")
def test_a_hot_signal_names_the_token_it_is_a_signal_about(rest_anon):
    """Their own summary is which TOKENS credible wallets are buying.

    The verdict compares the two chains their one endpoint serves in one
    format. Robinhood anonymous while Solana is named is the finding; both
    anonymous is their indexer, which is a different fault and inconclusive;
    neither anonymous is a pass.
    """
    docs = rest_anon.get(DOCS)
    if docs.status_code != 200:
        raise Inconclusive(
            f"{DOCS} answered HTTP {docs.status_code}; without their own "
            f"contract there is nothing to hold the rows against")

    rh_payload = _payload(rest_anon, "robinhood")
    # Robinhood's HOT rows when there are enough of them (V06); Solana is the
    # yardstick of what naming looks like on the same endpoint, all rows.
    basis, measured = measured_rows(list(rh_payload.get("rows") or []))
    robinhood = identity_gap(measured)
    solana = identity_gap(list(_payload(rest_anon, "solana").get("rows") or []))

    # Their own counter, added 2026-09-13 at their initiative after they
    # root-caused our 09:52 window. `None` when they do not serve it, which
    # `decide` falls back from rather than treating as zero -- a missing field
    # read as 0 would turn their transient into our defect.
    pending = rh_payload.get("identities_pending")
    pending = pending if isinstance(pending, int) else None

    verdict, reason = decide(robinhood, solana, pending)
    if verdict == "inconclusive":
        raise Inconclusive(reason)

    hot = [r for r in robinhood["anonymous"] if r.get("hot")]
    loudest = max((r.get("usd_invested") or 0 for r in robinhood["anonymous"]),
                  default=0)
    conclude(Measurement(
        verdict=verdict,
        reason=reason + (
            f". {len(hot)} of the anonymous rows are flagged hot, the largest "
            f"on {loudest:,.0f} USD invested" if hot else ""),
        left=[{"chain": "robinhood", "anonymous": len(robinhood["anonymous"]),
               "named": len(robinhood["named"])}],
        right=[{"chain": "solana", "anonymous": len(solana["anonymous"]),
                "named": len(solana["named"])}],
        population={
            "robinhood_measured": basis,
            "robinhood_rows": robinhood["total"],
            "robinhood_anonymous": len(robinhood["anonymous"]),
            "robinhood_anonymous_hot": len(hot),
            "solana_rows": solana["total"],
            "solana_anonymous": len(solana["anonymous"]),
            "identities_pending": pending,
            "threshold": THRESHOLD,
            "largest_anonymous_usd_invested": loudest,
        },
        sources={"signals": SIGNALS, "contract": DOCS},
    ))

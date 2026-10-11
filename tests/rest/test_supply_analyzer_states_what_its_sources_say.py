"""The Supply Analyzer states what its sources say (ET-28934, verified 2026-10-04).

Build it Better ET-28934 shipped on 2026-10-04 08:38 UTC: a token's supply as a flow,
month by month, with a 1-10 pressure number, "every input with its source and date",
"unknown inputs named, never zero", and a Supply column and card in the Gem Screener.
Verified the same morning over all 244 Gem Screener coins (outbox/supply-analyzer-
verification.md). Nine places where a number or a sentence does not follow from the
record's own inputs, from the source it names, or from its documentation; one check each:

1. THE BURNED SLICE. Seen: 81 records show "Bought back, burned"; every one whose input we
   read takes it from "max supply minus total supply (CoinGecko figures)" with `as_of`
   null, while the same record names burns as unknown, "counted as 0". For a token still
   being minted that difference is supply not yet issued: ORE showed 2,499,496 burned
   (83% of its pie) beside its own emission input of 42,098 tokens a month, of which month
   0 used 40, because the reserve that pays emissions had become the burned slice.
   ASSERTS: no sampled record shows a burned amount whose only source is max minus total.
   SAMPLE: the 12 largest burned shares in the batch (a population that moves daily).

2. BUYBACKS. /definitions: buybacks are "DeFiLlama's holders' revenue of the last 30 days
   (the share of fees that buys the token)". DeFiLlama's own HoldersRevenue methodology
   says, for many ve-token DEXes, that the money is paid out to lockers or voters.
   ASSERTS: among the records shown Squeezing (pressure 8-10) or whose sellable pile reaches
   0 inside its curve, none takes a buyback from holders' revenue whose every DeFiLlama
   methodology sentence describes a payout and none a purchase. A sentence that names any
   buying, or says neither, is not judged. SAMPLE: that population moves with every
   refresh.

3. THE PILE. Seen: `pile_today` (the tokens that can be sold) larger than the record's own
   `total_supply` (CRV 3,245,081,474 against 2,422,992,570). ASSERTS: the sellable pile
   is not larger than the total supply the record states (or its max supply when no
   total is given). Candidates are preselected from the batch against the Gem Screener
   snapshot's total supply and confirmed on each record, so a row that crossed between
   the two snapshots can be missed: SAMPLING, stated.

4. A CITED SOURCE. HYPE's record credits "kept" to "Hyperliquid docs: Fees (Assistance Fund)
   and HYPE burn" (its url), and the vesting schedule to a Hyperliquid docs url. Seen: the
   fees page says the assistance fund's HYPE is burned; the vesting url answers 404.
   ASSERTS: a disposition the record credits to a page is not contradicted by that page,
   and every url the record cites for its hand-entered inputs answers 200.

5. THE LINK. The Gem Screener's "Open in Supply Analyzer" links `?symbol=` with the coin's
   CoinGecko id first (`e.gecko_id || e.slug || e.key` in its script); OpenAPI says
   `symbol` takes a "Ticker (Gem Screener coins), slug or CoinGecko id". Seen:
   `symbol=hyperliquid` answers 404 UNKNOWN_SYMBOL for both Hyperliquid rows. ASSERTS: every
   link identifier used by more than one Gem Screener row resolves to a coin with that
   CoinGecko id.

6. THE TYPICAL INFLOW. /definitions and the batch state one typical inflow (12.34% that
   morning, "the median of the tokens with data"); HYPE's page printed "(5.0% a year)".
   ASSERTS: every range is as wide as the stated typical inflow, the only thing the
   documented rule adds to its top.

7. AN UNSUPPORTED CHAIN. OpenAPI documents 400 UNSUPPORTED_CHAIN for /analyze. Seen: 500
   INTERNAL_SERVER_ERROR. ASSERTS: a known Gem Screener contract (UNI) with an unsupported
   chain gets a documented answer. UNI is chosen because a contract the analyzer has not
   seen is added to its public weekly ledger when read (six of our reads did that).

8. TWO DILUTION FLAGS (Gem Screener). The detail's Checks row and Apps row read the
   snapshot's `dilution.week_pct`; the new Supply card reads the analyzer's
   `dilution_week_pct`. Seen: HYPE "0% new tokens a week" in Checks and "+1%, Heavy
   dilution" on the card, ORE the reverse. ASSERTS: no coin carries two different flags
   (ok / caution / red on the snapshot's own lines).

9. TOKENS OUT (Gem Screener). Seen: ORE "100% of tokens out" and FDV equal to market cap
   with a max supply six times its circulating supply, while the same snapshot records
   its emissions ($3.0M in 30 days). ASSERTS: no app whose snapshot records new tokens
   being issued is shown ~100% out (>= 99%) while its circulating supply is under 90% of
   its max supply. Without issuance on record, max minus total may be burned: not judged.

10. TOKENS LOCKED BY HOLDERS (added the same afternoon; the operator's named case, PHAR).
   Pharaoh's docs list PHAR and xPHAR on Avalanche; read on-chain through Routescan, the
   xPHAR contract held 497,139,188 of 530,627,320 PHAR and 992.7M of 994.3M xPHAR were
   staked in the VoteModule. The record showed "Reserve, outside the pie" 497,134,710 --
   the page: "Max supply minus every token in play, plus the project's own stake. It enters
   the pile only on a decision" -- and "Staked, free to unlock" 11,351,535 (DeFiLlama
   staking TVL). ASSERTS: when the token's own staking contract holds 10%+ of the supply,
   the record neither calls those tokens its reserve (within 1%) nor shows under half of
   them as staked. Inconclusive if Pharaoh's docs stop listing the two addresses.

11. AN UNKNOWN SCHEDULE SERVED AS NONE (added the same afternoon). Seen: all 174 records that
   name their vesting schedule unknown ("No unlock schedule on any feed we read") serve
   next_unlock {"kind": "none_scheduled"}, which the Gem Screener card prints as "none"
   with "The schedule on file has no tranche ahead"; for ARB, DeFiLlama's unlock file
   listed 56,125,000 team and 36,520,833 investor tokens on 2026-10-15. ASSERTS: no record
   with an unknown schedule serves "none_scheduled". DeFiLlama is read only for the
   chains among them, to show what is scheduled (a sample, stated in the reason).

12. A MAX SUPPLY THAT IS A SCHEDULE'S END (added the same afternoon). Seen: ETH's record
   states max_supply 127,869,954, source "DeFiLlama unlock schedule (ethereum)" -- the end
   total of an issuance horizon, not a cap (ETH has none) -- and shows max minus total,
   5,768,336, as "Bought back, burned"; SOL and TRX the same. ASSERTS: no sampled record
   takes its max supply from an unlock schedule. SAMPLE: every chain, and every app whose
   Gem Screener snapshot has no max supply while the analyzer states one.

13. A PILE CANNOT SHRINK BY MORE THAN ALL OF IT (added 2026-10-08). /definitions: "The yearly
   change = (in - out) x 12 / the pile, in %. It is the hero number"; the page titles it
   "Yearly change of the sellable pile". Seen: STONK (stonkfun) "-129.65% to -114.31% a
   year" ((10,199,876 in - 86,217,494 out) x 12 / 797,998,322: the formula holds), while its
   own 24-month curve empties the pile in Sep 2027 and still takes out 86,217,494 a month after
   that, so "Bought back, kept" reaches 1,034,609,929 in Oct 2027 against a max supply of
   1,000,000,000. ASSERTS: no record states a yearly change below -100% while /definitions
   calls the hero a yearly change (renamed to a rate, that half is not judged), and no month
   of a record's curve takes out more than the pile holds plus what comes in that month.
   Only a curve whose pile reaches 0 can do that, so those rows are preselected from the
   batch's pile_24m and each record is read: the whole population, not a sample.

14. THE NEXT UNLOCK IS ONE RECIPIENT'S SHARE OF ITS DAY (added 2026-10-11). The record serves
   `next_unlock` {ts, tokens, who, days}; nothing defines it (/definitions, the page and the
   OpenAPI schema, `properties: {}`, say nothing), and the Gem Screener card prints it as the
   next unlock. Seen: ARB's next_unlock 56,125,000 "Team, Contributors & Advisors" at ts
   1792108800, while the record's own `today.tranches` put two tranches at that ts, the second
   36,520,833 "Investors": 92,645,833 unlock that day. 36 of the 59 dated rows that morning.
   ASSERTS: when the record's tranches put more on the next unlock's day than next_unlock
   carries, next_unlock states that day's total in some field, or names every recipient of the
   day (a list shape is read too). Not asserted: which recipient it names, or that it must be
   a sum. SAMPLE: the NEXT_UNLOCK_SAMPLE dated batch rows with the largest market cap, stated.

NOT asserted: whether the pressure number predicts anything, the weekly test, or the
page's layout. SIDE EFFECTS: GETs only, anonymous; every Supply Analyzer read here names a
Gem Screener coin, so none adds a line to the analyzer's ledger. Reads are paced to stay
under the documented 30 a minute.

SAFE: GETs only, anonymous.
"""

from __future__ import annotations

import html as _html
import math
import re
import time
from datetime import datetime, timezone

import httpx

from qa.client import build_source_client
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

BATCH = "/api/v1/supply-analyzer/batch/gem-screener"
ANALYZE = "/api/v1/supply-analyzer/analyze"
DEFINITIONS = "/api/v1/supply-analyzer/definitions"
SNAPSHOT = "/api/v1/gem-screener"
LLAMA_FEES = "https://api.llama.fi/summary/fees/{slug}"

CLAIM_BURNED = "supply-analyzer-burned-slice-is-a-measured-burn"
CLAIM_BUYBACK = "supply-analyzer-buyback-is-a-purchase-of-the-token"
CLAIM_PILE = "supply-analyzer-sellable-pile-fits-inside-the-supply"
CLAIM_SOURCES = "supply-analyzer-cited-sources-say-what-they-are-credited-with"
CLAIM_LINK = "supply-analyzer-gem-screener-link-opens-its-coin"
CLAIM_TYPICAL = "supply-analyzer-typical-inflow-is-the-stated-one"
CLAIM_CHAIN = "supply-analyzer-unsupported-chain-gets-a-documented-answer"
CLAIM_FLAGS = "gem-screener-one-dilution-flag-per-coin"
CLAIM_OUT = "gem-screener-tokens-out-counts-the-max-supply"
CLAIM_LOCKED = "supply-analyzer-tokens-locked-by-holders-are-not-a-reserve"
CLAIM_SCHEDULE = "supply-analyzer-an-unknown-schedule-is-not-none-scheduled"
CLAIM_MAX = "supply-analyzer-max-supply-is-a-cap-not-a-schedule-end"
CLAIM_PAST_ALL = "supply-analyzer-a-pile-cannot-shrink-more-than-all-of-it"
CLAIM_PAST_MAX = "supply-analyzer-a-pile-cannot-grow-past-its-max-supply"
CLAIM_NEXT_UNLOCK = "supply-analyzer-next-unlock-states-its-whole-day"
LLAMA_EMISSIONS = "https://defillama-datasets.llama.fi/emissions/{slug}"

# The documented limit is 30 requests a minute per IP (llms.txt, /api-docs).
PACE_S = 2.2
BURNED_SAMPLE = 12
NEXT_UNLOCK_SAMPLE = 20
MAX_SINGLES = 130
MAX_TOTAL = "max supply minus total supply"
UNI = "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984"
UNSUPPORTED_CHAINS = ("dogechain", "tron", "foo")
DOCUMENTED_400 = frozenset({"MISSING_INPUT", "INVALID_SYMBOL", "INVALID_CONTRACT", "CHAIN_NEEDED",
                            "UNSUPPORTED_CHAIN", "NO_PRICE"})

_cache: dict = {}
_last = [0.0]


def _paced_get(client, url, **params):
    wait = PACE_S - (time.monotonic() - _last[0])
    if wait > 0:
        time.sleep(wait)
    try:
        return client.get(url, params=params or None, timeout=120.0)
    except httpx.HTTPError as exc:
        raise Inconclusive(f"{url} could not be read: {type(exc).__name__}")
    finally:
        _last[0] = time.monotonic()


def _json(response, what: str):
    if response.status_code != 200:
        raise Inconclusive(f"{what} answered HTTP {response.status_code}; a failed read is not an empty one")
    try:
        return response.json()
    except ValueError:
        raise Inconclusive(f"{what} answered 200 with a body that is not JSON")


def _batch(client) -> dict:
    if "batch" not in _cache:
        body = _json(_paced_get(client, BATCH), BATCH)
        if not isinstance(body, dict) or not isinstance(body.get("items"), list) or not body["items"]:
            raise Inconclusive(f"{BATCH} carries no items")
        _cache["batch"] = body
    return _cache["batch"]


def _snapshot(client) -> dict:
    if "snapshot" not in _cache:
        try:
            response = client.get(SNAPSHOT, timeout=180.0)
        except httpx.HTTPError as exc:
            raise Inconclusive(f"{SNAPSHOT} could not be read: {type(exc).__name__}")
        body = _json(response, SNAPSHOT)
        if not isinstance(body, dict) or not isinstance(body.get("apps"), list):
            raise Inconclusive(f"{SNAPSHOT} carries no apps")
        _cache["snapshot"] = body
    return _cache["snapshot"]


def _single(client, ident: str):
    """One coin's record by the identifier given, cached for the session; None when it
    could not be read (the caller counts it as unread)."""
    if ident in _cache.setdefault("singles", {}):
        return _cache["singles"][ident]
    if len(_cache["singles"]) >= MAX_SINGLES:
        return None
    response = _paced_get(client, ANALYZE, symbol=ident)
    record = None
    if response.status_code == 200:
        try:
            record = response.json()
        except ValueError:
            record = None
    _cache["singles"][ident] = record if isinstance(record, dict) and record.get("token") else None
    return _cache["singles"][ident]


def _sym(row) -> str:
    token = (row or {}).get("token") or {}
    return f"{token.get('symbol')} ({token.get('slug')})"


def _slices(row) -> dict:
    return {s.get("key"): s.get("amount") for s in (row or {}).get("slices_today") or []
            if isinstance(s, dict)}


def _input(record, key):
    for item in (record or {}).get("inputs") or []:
        if isinstance(item, dict) and item.get("key") == key:
            return item
    return None


def _num(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _f(value, spec: str = ",.0f") -> str:
    """A figure for a failure reason; an unknown one prints as n/a instead of raising, so a
    record that names its unknowns (null, never zero) still produces a measurement."""
    return format(value, spec) if _num(value) else "n/a"


# --- pure readings (held in tests/meta) -------------------------------------------------

def _burn_source(record) -> dict | None:
    """The input a burned slice would stand on. `burned_so_far` until 2026-10-08; the
    record now carries max minus total as `supply_gap` ("max supply minus total supply"),
    and a burned slice drawn from it again must be read, not taken as unread (deep pass
    2026-10-08, T15, 3/3)."""
    return _input(record, "burned_so_far") or _input(record, "supply_gap")


def burned_without_a_burn(record) -> dict | None:
    """The burned slice of a record when its only source is max supply minus total supply,
    else None. No source to read is unread, not convicted."""
    amount = _slices(record).get("bb_burned")
    if not _num(amount) or amount <= 0:
        return None
    source = _burn_source(record)
    if not source or MAX_TOTAL not in str(source.get("source") or "").lower():
        return None
    unknown = [u.get("input") for u in (record or {}).get("unknown") or [] if isinstance(u, dict)]
    share = next((s.get("share_pct") for s in record.get("slices_today") or []
                  if isinstance(s, dict) and s.get("key") == "bb_burned"), None)
    return {"coin": _sym(record), "burned": amount, "share_pct": share, "source": source.get("source"),
            "as_of": source.get("as_of"), "burns_named_unknown": "burns" in unknown}


def emission_dropped(record) -> tuple[float, float] | None:
    """(the emission input, the emissions month 0 counts) when month 0 counts under 90% of
    a known emission input, else None."""
    item = _input(record, "emissions_month")
    months = (record or {}).get("months") or []
    if not item or not _num(item.get("value")) or item["value"] <= 0 or not months:
        return None
    used = ((months[0] or {}).get("in") or {}).get("emissions")
    if not _num(used) or used >= 0.9 * item["value"]:
        return None
    return item["value"], used


_BUYING = re.compile(r"\bbuy(?:s|ing)?\b|buy[- ]?backs?|repurchas", re.I)
_PAYOUT = re.compile(r"(?i:distribut|\bgo(?:es|ing)? to (?:\w+ )?(?:token )?holders|\bvoters\b|\bstakers\b"
                     r"|\blockers\b|holders who vote)|\bto (?:ve|x|s)[A-Z]\w* (?:holders|voters|stakers|lockers)")


def holders_revenue_kind(text) -> str | None:
    """'buyback' when a DeFiLlama HoldersRevenue sentence names any buying, 'distribution'
    when it only describes a payout to holders, voters, stakers or lockers, else None."""
    if not isinstance(text, str) or not text.strip():
        return None
    if _BUYING.search(text):
        return "buyback"
    if _PAYOUT.search(text):
        return "distribution"
    return None


def pile_over_supply(record) -> dict | None:
    """The sellable pile when it is larger than the record's total supply (or its max
    supply when it states no total), else None. Nothing to compare against is unread."""
    pile = (record or {}).get("pile_today")
    for field in ("total_supply", "max_supply"):
        cap = (record or {}).get(field)
        if _num(cap) and cap > 0:
            break
    else:
        return None
    if not _num(pile) or pile <= cap * 1.001:
        return None
    staked = _input(record, "staked_total")
    return {"coin": _sym(record), "pile": pile, "against": field, "supply": cap, "over_by": pile - cap,
            "circulating": record.get("circulating"),
            "staked_total": staked.get("value") if staked else None,
            "circulating_includes_staked": record.get("circulating_includes_staked")}


def fund_disposition(text) -> str | None:
    """'burned' or 'kept' as the page says the assistance fund's tokens are, else None.

    Both, in the record's own two words (/definitions: "buybacks (burned or kept)"): with only
    'burned' readable, a record that says burned could never be contradicted by its page
    (deep pass 2026-10-08, T16, 3/3)."""
    if not isinstance(text, str):
        return None
    said = re.search(r"assistance fund[^.]{0,40}\bis (?:permanently |still )?"
                     r"(burned|held|kept|retained|accumulated)", text, flags=re.I)
    if not said:
        return None
    return "burned" if said.group(1).lower() == "burned" else "kept"


def link_identifier(row) -> str | None:
    token = (row or {}).get("token") or {}
    return token.get("gecko_id") or token.get("slug") or token.get("key")


def shared_link_identifiers(rows) -> list[str]:
    """Link identifiers used by more than one row, or equal to another row's slug."""
    count: dict[str, int] = {}
    slugs: dict[str, int] = {}
    for i, row in enumerate(rows or ()):
        ident = link_identifier(row)
        if ident:
            count[ident] = count.get(ident, 0) + 1
        slug = ((row or {}).get("token") or {}).get("slug")
        if slug:
            slugs.setdefault(slug, i)
    shared = set()
    for i, row in enumerate(rows or ()):
        ident = link_identifier(row)
        if ident and (count[ident] > 1 or (ident in slugs and slugs[ident] != i)):
            shared.add(ident)
    return sorted(shared)


INFLOW_UNKNOWN_WORDS = ("vesting", "emission", "unlock", "mint", "airdrop", "reward", "distribution")


def reserve_pct(row) -> float | None:
    """The reserve outside the pile as a % of the pile, or None when the row states neither."""
    pile, reserve = (row or {}).get("pile_today"), (row or {}).get("reserve_today")
    if not (_num(pile) and _num(reserve)) or pile <= 0 or reserve < 0:
        return None
    return 100.0 * reserve / pile


def growth_past_max_supply(rows, *, tol: float = 0.02) -> tuple[int, list[dict]]:
    """Rows whose yearly figure (the top of a range) grows the pile past the max supply.

    /definitions: "Max supply = a cap the market feed states", and what comes in "is at most
    what the reserve outside the pile still holds". Whatever feeds the pile -- the reserve,
    vesting, emissions -- a year can add at most max supply minus the pile, whatever the hero's
    (in - out) x 12 says. 2026-10-10: YFI topped at +15.1 % a year with 1.64 % left to its max,
    LQTY +14.09 % with 1.17 % (12 x the reserve that caps its first month). A row with no max
    supply, or a pile already above it (pile_over_supply's), is not judged."""
    judged, over = 0, []
    for row in rows or ():
        pile, cap = (row or {}).get("pile_today"), (row or {}).get("max_supply")
        rng = (row or {}).get("yearly_range")
        figures = [x for x in (rng if isinstance(rng, list) else []) if _num(x)]
        if not figures and _num((row or {}).get("yearly_pct")):
            figures = [row["yearly_pct"]]
        if not (_num(pile) and _num(cap)) or pile <= 0 or cap < pile or not figures:
            continue
        judged += 1
        room = 100.0 * (cap - pile) / pile
        top = max(figures)
        if top > room + tol:
            over.append({"symbol": ((row.get("token") or {}).get("symbol")), "top": top,
                         "room_pct": room, "pile": pile, "max_supply": cap,
                         "reserve": row.get("reserve_today"), "range": rng, "status": row.get("status")})
    return judged, over


def typical_mismatches(rows, typical) -> list[dict]:
    """Range rows whose width is not the stated typical inflow plus the one named part they declare.

    Since 2026-10-08 a range is two named parts (`yearly_range_parts`: the typical inflow and an
    unstated buyback share), so a width above the typical is explained when the row names the
    buyback part that makes it up. A row that declares no parts, a typical part that is not the
    stated one (or 0, a row with no inflow assumed), or a width the parts do not add up to (to the
    0.03 the batch's own rounding of two parts and a sum allows) is still an unnamed figure.

    A typical part of 0 is held to the row's own `unknown_names`: /definitions applies the
    typical inflow "when an inflow is unknown", so a row that names an inflow unknown (vesting,
    emissions, unlocks, mints, airdrops, rewards) and assumes none is the 2026-10-04 defect again,
    whatever parts it declares (deep pass 2026-10-08, T14, 3/3). "staking flow" runs both ways
    and is not read as an inflow.
    """
    out = []
    for row in rows or ():
        rng = (row or {}).get("yearly_range")
        if row.get("status") != "range" or not isinstance(rng, list) or len(rng) != 2:
            continue
        if not all(_num(x) for x in rng):
            continue
        width = rng[1] - rng[0]
        parts = row.get("yearly_range_parts")
        named = 0.0
        stated = typical
        if isinstance(parts, dict) and _num(parts.get("typical_inflow_pct")) \
                and _num(parts.get("unstated_buyback_share_pct")):
            stated = parts["typical_inflow_pct"]
            named = parts["unstated_buyback_share_pct"]
            inflow_unknown = [n for n in row.get("unknown_names") or []
                              if any(w in str(n).lower() for w in INFLOW_UNKNOWN_WORDS)]
            if (abs(stated - typical) > 0.01 and stated != 0) or (stated == 0 and inflow_unknown):
                out.append({"symbol": ((row.get("token") or {}).get("symbol")), "range": rng,
                            "used": round(stated, 2), "inflow_unknown": inflow_unknown})
                continue
        if width > 0.005 and abs(width - (stated + named)) > 0.03:
            # Narrower than its parts is the documented cap ("what comes in ... is at most what
            # the reserve outside the pile still holds") on a row whose reserve is smaller than
            # the stated typical; how far it narrows is growth_past_max_supply's (2026-10-10).
            # Narrowed TO the reserve, not below it: the inflow part (the width less the named
            # buyback part) must still carry what the reserve can supply in a year, within the
            # batch's rounding (deep pass 2026-10-10, R01/A03).
            reserve = reserve_pct(row)
            if (width < stated + named and reserve is not None and reserve < stated
                    and width - named >= reserve - 0.03):
                continue
            out.append({"symbol": ((row.get("token") or {}).get("symbol")), "range": rng,
                        "used": round(width, 2)})
    return out


def chain_answer_documented(status, body) -> bool | None:
    """True for a read (200) or a documented 400 code, False for a 500, None otherwise."""
    if status == 200:
        return True
    if status == 400:
        detail = (body or {}).get("detail") if isinstance(body, dict) else None
        code = ((detail or {}).get("error") or {}).get("code") if isinstance(detail, dict) else None
        return code in DOCUMENTED_400
    if isinstance(status, int) and status >= 500 and status != 503:
        return False
    return None


def dilution_flag(value, caution, red) -> str | None:
    if not _num(value):
        return None
    return "red" if value > red else ("caution" if value > caution else "ok")


def two_flags(apps, items, caution, red) -> tuple[int, list[dict]]:
    """(judged, coins whose snapshot dilution and analyzer dilution carry different flags)."""
    by_slug = {((i or {}).get("token") or {}).get("slug"): i for i in items or ()}
    judged, differ = 0, []
    for app in apps or ():
        item = by_slug.get((app or {}).get("slug"))
        if not item:
            continue
        a = ((app.get("dilution") or {}).get("week_pct"))
        b = item.get("dilution_week_pct")
        fa, fb = dilution_flag(a, caution, red), dilution_flag(b, caution, red)
        if fa is None or fb is None:
            continue
        judged += 1
        if fa != fb:
            differ.append({"symbol": app.get("symbol"), "slug": app.get("slug"),
                           "checks_row": a, "checks_flag": fa, "supply_card": b, "card_flag": fb})
    return judged, differ


def locked_as_reserve(record, chain) -> dict | None:
    """When the token's own staking contract holds a real share of the supply (10%+), the
    record either calls those locked tokens its reserve (within 1%) or shows under half of
    them as staked. None when the chain was not read or holds too little to prove it."""
    locked, total = (chain or {}).get("locked_in_staking_token"), (chain or {}).get("total_supply")
    if not _num(locked) or not _num(total) or total <= 0 or locked < 0.1 * total:
        return None
    reserve = (record or {}).get("reserve_today")
    staked_item = _input(record, "staked_total")
    staked = staked_item.get("value") if staked_item and _num(staked_item.get("value")) else 0.0
    is_reserve = _num(reserve) and abs(reserve - locked) <= 0.01 * locked
    share = staked / locked
    if not is_reserve and share >= 0.5:
        return None
    return {"coin": _sym(record), "locked_in_staking_token": locked, "reserve_today": reserve,
            "reserve_is_the_locked_tokens": bool(is_reserve), "staked_shown": staked,
            "staked_shown_share": round(share, 4), "total_supply_onchain": total,
            "record_total_supply": record.get("total_supply"), "record_circulating": record.get("circulating")}


def unknown_served_as_none(row) -> bool:
    """True when a record names its vesting schedule unknown yet serves next_unlock as
    "none_scheduled" (the Gem Screener card then prints "none scheduled")."""
    unknown = (row or {}).get("unknown_names") or []
    unlock = (row or {}).get("next_unlock")
    return "vesting schedule" in unknown and isinstance(unlock, dict) and unlock.get("kind") == "none_scheduled"


def future_unlocks(dl_file, now) -> list[dict]:
    """Dated unlock events at or after `now` in a DeFiLlama emissions file, soonest first."""
    events = (((dl_file or {}).get("metadata") or {}).get("events") or []) if isinstance(dl_file, dict) else []
    out = []
    for event in events:
        try:
            ts = int(float(event.get("timestamp")))
        except (TypeError, ValueError, AttributeError):
            continue
        if ts < now:
            continue
        tokens = event.get("noOfTokens")
        said = re.search(r"\bof (.+?) tokens\b", str(event.get("description") or ""))
        out.append({"ts": ts, "date": datetime.fromtimestamp(ts, timezone.utc).date().isoformat(),
                    "tokens": tokens[0] if isinstance(tokens, list) and tokens else tokens,
                    "type": event.get("unlockType"), "category": event.get("category"),
                    "what": said.group(1) if said else str(event.get("description") or "")})
    return sorted(out, key=lambda e: e["ts"])


def max_from_a_schedule(record) -> dict | None:
    """The record's max supply when its source is an unlock schedule (the schedule's end
    total, not a cap), with the burned amount derived from it, else None."""
    item = _input(record, "max_supply")
    if not item or "unlock schedule" not in str(item.get("source") or "").lower() or not _num(item.get("value")):
        return None
    burned = _slices(record).get("bb_burned")
    return {"coin": _sym(record), "max_supply": item["value"], "source": item.get("source"),
            "total_supply": (record or {}).get("total_supply"),
            "burned_from_it": burned if _num(burned) and burned > 0 else 0}


def out_ignores_max(app) -> dict | None:
    """An app shown >= 99% out while its circulating supply is under 90% of its max supply
    and the same snapshot records new tokens being issued."""
    supply, cg, dil = (app or {}).get("supply") or {}, app.get("cg") or {}, app.get("dilution") or {}
    out, mx = supply.get("out_pct"), cg.get("max")
    circ = supply.get("circ") or cg.get("circ")
    if not all(_num(x) for x in (out, mx, circ)) or mx <= 0 or out < 99 or circ / mx >= 0.9:
        return None
    issuing = (_num(dil.get("week_pct")) and dil["week_pct"] > 0 and dil.get("basis") == "emissions") or (
        _num(dil.get("emissions_usd30")) and dil["emissions_usd30"] > 0)
    if not issuing:
        return None
    return {"symbol": app.get("symbol"), "slug": app.get("slug"), "out_pct": round(out, 2),
            "circ_of_max_pct": round(circ / mx * 100, 1), "max_supply": mx, "circulating": circ,
            "fdv": app.get("fdv"), "mcap": app.get("mcap"), "dilution_week_pct": dil.get("week_pct"),
            "emissions_usd30": dil.get("emissions_usd30")}


def hero_as_a_change(definitions) -> str | None:
    """The /definitions line that defines the hero number as "The yearly change" (of the pile),
    the reading under which a figure below -100% claims more than a pile can lose; None when
    no line does."""
    lines = (definitions or {}).get("definitions") if isinstance(definitions, dict) else None
    return next((d.strip() for d in lines or () if isinstance(d, str)
                 and d.strip().lower().startswith("the yearly change")), None)


def shrinks_past_all(row) -> dict | None:
    """The row's stated yearly change of its sellable pile when it, or either end of its range
    (the page's hero prints both), is below -100%: the most a pile can lose is all of it. None
    when nothing is stated or nothing is below -100."""
    rng = (row or {}).get("yearly_range")
    figures = [x for x in [(row or {}).get("yearly_pct")] + (list(rng) if isinstance(rng, list) else [])
               if _num(x)]
    if not figures or min(figures) >= -100:
        return None
    return {"coin": _sym(row), "slug": ((row.get("token") or {}).get("slug")), "yearly_pct": row.get("yearly_pct"),
            "yearly_range": rng, "lowest": min(figures), "pile_today": row.get("pile_today")}


def takes_out_more_than_there_is(record) -> dict | None:
    """The months of a record's curve that take out more than the pile holds plus what comes
    in that month (only a pile floored at 0 can show one), with the month the pile first reads
    0 and the most the curve books bought back (kept + burned) against the max supply, or the
    total when no max is stated. None when no month does, or there is no curve to read."""
    months = [m for m in (record or {}).get("months") or [] if isinstance(m, dict)]
    over = []
    for m in months:
        pile, came, went = m.get("pile"), (m.get("in") or {}).get("total"), (m.get("out") or {}).get("total")
        if all(_num(x) for x in (pile, came, went)) and went > (pile + came) * 1.001 + 1:
            over.append({"label": m.get("label"), "i": m.get("i"), "pile": pile, "in": came, "out": went})
    if not over:
        return None
    cap_field = "max_supply" if _num(record.get("max_supply")) and record["max_supply"] > 0 else "total_supply"
    cap = record.get(cap_field)
    peak, peak_at, past_cap = 0.0, None, None
    for m in months:
        sl = m.get("slices") or {}
        if isinstance(sl, list):
            sl = {s.get("key"): s.get("amount") for s in sl if isinstance(s, dict)}
        bought = sum(v for v in (sl.get("bb_kept"), sl.get("bb_burned")) if _num(v))
        if bought > peak:
            peak, peak_at = bought, m.get("label")
        if past_cap is None and _num(cap) and cap > 0 and bought > cap:
            past_cap = {"label": m.get("label"), "bought_back": bought}
    empty = next((m.get("label") for m in months if _num(m.get("pile")) and m["pile"] <= 0), None)
    return {"coin": _sym(record), "months_over": len(over), "first": over[0], "empty_at": empty,
            "bought_back_peak": peak, "peak_at": peak_at, "cap_field": cap_field, "cap": cap,
            "bought_back_past_cap": past_cap}


_NOT_AN_AMOUNT = ("ts", "days", "as_of", "stale")


def _amount(entry) -> float | None:
    """A tranche's or a recipient entry's token amount, under either name the record uses."""
    for key in ("amount", "tokens"):
        if isinstance(entry, dict) and _num(entry.get(key)):
            return float(entry[key])
    return None


def tranches_on(record, ts) -> list[dict]:
    """Every tranche the record puts on `ts`, read from `today` and every month of its curve,
    each (ts, who, amount) once -- `today` repeats month 0's tranches."""
    pools = [((record or {}).get("today") or {}).get("tranches")]
    pools += [m.get("tranches") for m in (record or {}).get("months") or [] if isinstance(m, dict)]
    seen, out = set(), []
    for pool in pools:
        for t in pool if isinstance(pool, list) else ():
            amount = _amount(t)
            if t.get("ts") != ts or amount is None:
                continue
            key = (t.get("ts"), t.get("who"), round(amount, 3))
            if key not in seen:
                seen.add(key)
                out.append(t)
    return out


def next_unlock_against_its_day(record, *, tol: float = 0.005) -> dict | None:
    """The record's next unlock beside what its own tranches release on that day.

    None when it cannot be judged: no dated next unlock, or no tranche on its day. Otherwise a
    dict whose `short` is True when the day releases more than next_unlock carries in ANY of its
    amount fields (or in a list of recipients inside it, or summed over a list-shaped next_unlock):
    the fix is theirs to shape, a total field or every recipient both clear it."""
    nu = (record or {}).get("next_unlock")
    entries = [e for e in nu if isinstance(e, dict)] if isinstance(nu, list) else []
    if entries:
        dated = [e.get("ts") for e in entries if _num(e.get("ts"))]
        if not dated:
            return None
        ts = min(dated)
        served = [sum(a for a in (_amount(e) for e in entries if e.get("ts") == ts) if a is not None)]
        who = [e.get("who") for e in entries if e.get("ts") == ts]
    elif isinstance(nu, dict) and _num(nu.get("ts")):
        ts = nu["ts"]
        served = [float(v) for k, v in nu.items() if k not in _NOT_AN_AMOUNT and _num(v)
                  and not k.endswith("pct") and "usd" not in k]
        for v in nu.values():
            if isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
                served.append(sum(a for a in (_amount(x) for x in v) if a is not None))
        who = [nu.get("who")]
    else:
        return None
    day = tranches_on(record, ts)
    if not day:
        return None
    total = sum(_amount(t) for t in day)
    best = max(served) if served else 0.0
    return {"coin": _sym(record), "ts": ts, "day": datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d"),
            "served": best, "served_who": who, "day_total": total,
            "recipients": [{"who": t.get("who"), "amount": _amount(t)} for t in day],
            "short": total > best * (1 + tol) + 1}


# --- 1. the burned slice -----------------------------------------------------------------

@qa(component="rest.supply_analyzer", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM_BURNED)
def test_a_burned_slice_comes_from_a_burn(rest_anon):
    """No sampled record shows a "Bought back, burned" amount whose only source is max
    supply minus total supply."""
    batch = _batch(rest_anon)
    rows = [r for r in batch["items"] if (_slices(r).get("bb_burned") or 0) > 0]
    if not rows:
        raise Inconclusive(f"{BATCH} shows no burned slice on any row")
    share = lambda r: next((s.get("share_pct") or 0 for s in r.get("slices_today") or []
                            if s.get("key") == "bb_burned"), 0)
    sample = sorted(rows, key=share, reverse=True)[:BURNED_SAMPLE]
    judged, bad, unread, dropped = 0, [], [], []
    for row in sample:
        record = _single(rest_anon, ((row.get("token") or {}).get("slug")) or "")
        if record is None:
            unread.append(_sym(row))
            continue
        if not str((_burn_source(record) or {}).get("source") or "").strip():
            unread.append(f"{_sym(row)}: no burned_so_far or supply_gap source to read")  # unread, not clean
            continue
        judged += 1
        found = burned_without_a_burn(record)
        if found:
            gone = emission_dropped(record)
            if gone:
                found["emission_input"], found["emission_month0"] = gone
                found["yearly_pct"], found["band"] = record.get("yearly_pct"), record.get("band")
                dropped.append(found["coin"])
            bad.append(found)
    if not judged:
        raise Inconclusive(f"none of the {len(sample)} sampled records could be read: {unread[:5]}")
    said = lambda b: (f"{b['coin']}: {b['burned']:,.0f} burned ({b['share_pct']}% of the pie) from "
                      f"\"{b['source']}\""
                      + (f", own emission input {b['emission_input']:,.0f} a month of which month 0 "
                         f"counts {b['emission_month0']:,.2f}, shown {b['yearly_pct']}% a year, {b['band']}"
                         if "emission_input" in b else ""))
    conclude(Measurement(
        verdict="failed" if bad else "passed",
        reason=(f"{len(bad)} of {judged} sampled records (the largest burned shares; {len(rows)} rows of "
                f"the batch show a burned slice) take the burned amount only from max supply minus total "
                f"supply, with no date, while {sum(b['burns_named_unknown'] for b in bad)} of them name burns "
                f"as unknown, counted as 0; {len(dropped)} also count under 90% of their own emission input: "
                + "; ".join(said(b) for b in sorted(bad, key=lambda b: -(b["share_pct"] or 0))[:4])
                if bad else
                f"none of {judged} sampled burned slices comes only from max minus total supply"),
        left={"burned_from_max_minus_total": len(bad)},
        right={"burned_from_max_minus_total": 0},
        population={"bad": bad, "judged": judged, "unread": unread, "rows_with_burned_slice": len(rows),
                    "emission_dropped": dropped, "batch_as_of": batch.get("as_of")},
        sources={"batch": BATCH, "records": f"{ANALYZE}?symbol=<slug>"},
        claim_id=CLAIM_BURNED))


# --- 2. buybacks -------------------------------------------------------------------------

def _children(source: str) -> list[str]:
    match = re.search(r"holders' revenue[^(]*\(([^)]*)\)", source or "", flags=re.I)
    return [c.strip() for c in match.group(1).split(",")] if match else []


@qa(component="rest.supply_analyzer", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM_BUYBACK)
def test_a_buyback_is_a_purchase_of_the_token(rest_anon, evidence_store):
    """Among records shown Squeezing or whose pile reaches 0, none books a buyback from
    holders' revenue that DeFiLlama's own methodology describes only as a payout."""
    batch = _batch(rest_anon)
    rows = [r for r in batch["items"]
            if (_num(r.get("pressure")) and r["pressure"] >= 8)
            or (isinstance(r.get("pile_24m"), list) and r["pile_24m"] and _num(r["pile_24m"][0])
                and r["pile_24m"][0] > 0 and min(x for x in r["pile_24m"] if _num(x)) <= 0)]
    if not rows:
        raise Inconclusive("no row is shown Squeezing or drains its pile")
    source = build_source_client(evidence=evidence_store, timeout=60.0)
    judged, payouts, unread, not_judged = 0, [], [], []
    try:
        for row in rows:
            slug = (row.get("token") or {}).get("slug") or ""
            record = _single(rest_anon, slug)
            if record is None:
                unread.append(_sym(row))
                continue
            item = _input(record, "buyback_month")
            if not item or not _num(item.get("value")) or item["value"] <= 0:
                continue
            children = _children(item.get("source") or "")
            if not children:
                not_judged.append(f"{_sym(row)}: source names no DeFiLlama protocol")
                continue
            try:
                response = source.get(LLAMA_FEES.format(slug=slug),
                                      params={"dataType": "dailyHoldersRevenue", "excludeTotalDataChart": "true",
                                              "excludeTotalDataChartBreakdown": "true"})
                body = response.json() if response.status_code == 200 else None
            except (httpx.HTTPError, ValueError):
                body = None
            if not isinstance(body, dict):
                unread.append(f"{_sym(row)}: DeFiLlama methodology not readable")
                continue
            said = {c.get("name"): (c.get("methodology") or {}).get("HoldersRevenue")
                    for c in body.get("childProtocols") or [] if isinstance(c, dict)}
            if not said:
                said = {body.get("name"): (body.get("methodology") or {}).get("HoldersRevenue")}
            kinds = {c: holders_revenue_kind(said.get(c)) for c in children}
            if not any(kinds.values()):
                # "Says neither" is not judged -- and not counted as judged, or a day on which
                # no sentence was classified would pass with the Inconclusive gate bypassed.
                not_judged.append(f"{_sym(row)}: {kinds}")
                continue
            judged += 1
            if kinds and all(k == "distribution" for k in kinds.values()):
                payouts.append({"coin": _sym(record), "band": record.get("band"), "pressure": record.get("pressure"),
                                "yearly_pct": record.get("yearly_pct"), "buyback_month": item["value"],
                                "buyback_note": item.get("note"), "pile_today": record.get("pile_today"),
                                "methodology": {c: said.get(c) for c in children}})
            else:
                not_judged.append(f"{_sym(row)}: {kinds}")
    finally:
        source.close()
    if not judged:
        raise Inconclusive(f"none of {len(rows)} Squeezing or draining rows had a readable buyback and "
                           f"methodology (unread: {unread[:5]})")
    conclude(Measurement(
        verdict="failed" if payouts else "passed",
        reason=(f"{len(payouts)} of {judged} records shown Squeezing or draining their pile (a sample: "
                f"{len(rows)} such rows that day) book holders' revenue as a buyback of the token while "
                f"DeFiLlama's methodology for every protocol named describes a payout: "
                + "; ".join(f"{p['coin']} {p['band']} {p['yearly_pct']}% a year, buyback {p['buyback_month']:,.0f} "
                            f"tokens a month ({p['buyback_note']}); DeFiLlama: \""
                            f"{next(iter(p['methodology'].values()))}\"" for p in payouts[:4])
                if payouts else
                f"none of {judged} judged records books a payout as a buyback"),
        left={"payouts_booked_as_buybacks": len(payouts)},
        right={"payouts_booked_as_buybacks": 0},
        population={"payouts": payouts, "judged": judged, "not_judged": not_judged, "unread": unread,
                    "rows": [_sym(r) for r in rows]},
        sources={"batch": BATCH, "records": f"{ANALYZE}?symbol=<slug>",
                 "methodology": LLAMA_FEES + "?dataType=dailyHoldersRevenue"},
        claim_id=CLAIM_BUYBACK))


# --- 3. the pile -------------------------------------------------------------------------

@qa(component="rest.supply_analyzer", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM_PILE)
def test_the_sellable_pile_fits_inside_the_supply(rest_anon):
    """No record's sellable pile is larger than the total supply it states."""
    batch = _batch(rest_anon)
    totals = {a.get("slug"): ((a.get("cg") or {}).get("total")) for a in _snapshot(rest_anon)["apps"]}
    candidates = []
    for row in batch["items"]:
        pile = row.get("pile_today")
        if not _num(pile):
            continue
        total = totals.get((row.get("token") or {}).get("slug"))
        if (_num(total) and pile > total) or (not _num(total) and (_slices(row).get("staked_free") or 0) > 0):
            candidates.append(row)
    judged, over, unread = 0, [], []
    for row in candidates:
        record = _single(rest_anon, (row.get("token") or {}).get("slug") or "")
        if record is None:
            unread.append(_sym(row))
            continue
        judged += 1
        found = pile_over_supply(record)
        if found:
            over.append(found)
    if not judged:
        raise Inconclusive(f"none of {len(candidates)} candidate records could be read")
    over.sort(key=lambda o: -(o["over_by"] / o["supply"]))
    conclude(Measurement(
        verdict="failed" if over else "passed",
        reason=(f"{len(over)} records state a sellable pile larger than the {'/'.join(sorted({o['against'] for o in over}))} "
                f"they state themselves: "
                + "; ".join(f"{o['coin']} pile {_f(o['pile'])} against {o['against']} {_f(o['supply'])} "
                            f"(circulating {_f(o['circulating'])} plus staked {_f(o['staked_total'] or 0)})"
                            for o in over[:4])
                if over else
                f"all {judged} candidate records keep the pile inside their supply"),
        left={"pile_over_supply": len(over)},
        right={"pile_over_supply": 0},
        population={"over": over, "judged": judged, "unread": unread, "candidates": len(candidates)},
        sources={"batch": BATCH, "snapshot": SNAPSHOT, "records": f"{ANALYZE}?symbol=<slug>"},
        claim_id=CLAIM_PILE))


# --- 4. a cited source -------------------------------------------------------------------

def _page_text(body: str) -> str:
    body = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", body or "")
    return " ".join(_html.unescape(re.sub(r"<[^>]+>", " ", body)).split())


@qa(component="rest.supply_analyzer", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM_SOURCES)
def test_a_cited_source_says_what_it_is_credited_with(rest_anon, evidence_store):
    """HYPE's record: a disposition credited to a page is not contradicted by that page,
    and every url cited for a hand-entered input answers 200."""
    record = _single(rest_anon, "HYPE")
    if record is None:
        raise Inconclusive(f"{ANALYZE}?symbol=HYPE could not be read")
    cited = [i for i in record.get("inputs") or [] if isinstance(i, dict)
             and str(i.get("url") or "").startswith("http") and "cymetica.com" not in str(i.get("url"))
             and i.get("key") in ("vesting_schedule", "staking_exit", "buyback_disposition")]
    if not cited:
        raise Inconclusive("HYPE's record cites no hand-entered input with a url")
    source = build_source_client(evidence=evidence_store, timeout=60.0)
    problems, read = [], []
    try:
        for item in cited:
            try:
                response = source.get(item["url"])
            except httpx.HTTPError as exc:
                read.append({"key": item["key"], "url": item["url"], "status": type(exc).__name__})
                continue
            entry = {"key": item["key"], "url": item["url"], "status": response.status_code,
                     "value": item.get("value"), "source": item.get("source")}
            read.append(entry)
            if response.status_code in (404, 410):
                problems.append(f"the {item['key']} url {item['url']} (cited as \"{item.get('source')}\") "
                                f"answers {response.status_code}")
            elif response.status_code == 200 and item["key"] == "buyback_disposition":
                page = fund_disposition(_page_text(response.text))
                entry["page_says"] = page
                if page and page != str(item.get("value")).lower():
                    problems.append(f"the record says buybacks are \"{item.get('value')}\" and credits "
                                    f"\"{item.get('source')}\" ({item['url']}); that page says the "
                                    f"assistance fund's HYPE \"is burned\"")
    finally:
        source.close()
    unreadable = [r for r in read if r.get("status") not in (200, 404, 410)]
    if not problems and unreadable:
        # "Every url answers 200" is the contract: a 403, a 5xx or a timeout is neither a pass
        # nor a dead link we can name, so it is not a clean read.
        raise Inconclusive(f"{len(unreadable)} of the {len(cited)} cited urls could not be read as live or "
                           f"dead: {[(r['key'], r['status']) for r in unreadable]}")
    conclude(Measurement(
        verdict="failed" if problems else "passed",
        reason=("HYPE's record: " + "; ".join(problems)) if problems else
               f"all {len(read)} cited urls answer and none contradicts what it is credited with",
        left={"contradicted_or_dead": len(problems)},
        right={"contradicted_or_dead": 0},
        population={"read": read, "refreshed_at": record.get("refreshed_at")},
        sources={"record": f"{ANALYZE}?symbol=HYPE", "cited": [c["url"] for c in cited]},
        claim_id=CLAIM_SOURCES))


# --- 5. the link -------------------------------------------------------------------------

@qa(component="rest.supply_analyzer", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM_LINK)
def test_the_gem_screener_link_opens_its_coin(rest_anon):
    """Every link identifier used by more than one Gem Screener row opens a coin with that
    CoinGecko id."""
    rows = _batch(rest_anon)["items"]
    shared = shared_link_identifiers(rows)
    if not shared:
        raise Inconclusive("no link identifier is shared by two rows; nothing to judge")
    users = {i: [_sym(r) for r in rows if link_identifier(r) == i] for i in shared}
    bad, ok, unread = [], [], []
    for ident in shared:
        response = _paced_get(rest_anon, ANALYZE, symbol=ident, include_months="false")
        try:
            body = response.json()
        except ValueError:
            body = None
        got = ((body or {}).get("token") or {}) if isinstance(body, dict) else {}
        entry = {"identifier": ident, "rows": users[ident], "status": response.status_code,
                 "answer": got.get("gecko_id") or ((body or {}).get("detail") if isinstance(body, dict) else None)}
        if response.status_code == 200 and got.get("gecko_id") == ident:
            ok.append(entry)
        elif response.status_code in (300, 400, 404, 422) or (response.status_code == 200 and got.get("gecko_id") != ident):
            bad.append(entry)
        else:
            unread.append(entry)                   # 429, 5xx...: neither opens nor fails to open
    if not bad and (unread or not ok):
        raise Inconclusive(f"{len(unread)} of {len(shared)} shared identifiers could not be read "
                           f"({[(u['identifier'], u['status']) for u in unread]}); the others open their coin")
    conclude(Measurement(
        verdict="failed" if bad else "passed",
        reason=("; ".join(f"/supply-analyzer?symbol={b['identifier']}, the link of {', '.join(b['rows'])}, "
                          f"answers HTTP {b['status']}: {b['answer']}" for b in bad)
                + "; OpenAPI says symbol takes a \"Ticker (Gem Screener coins), slug or CoinGecko id\""
                if bad else f"all {len(ok)} shared link identifiers open their coin"),
        left={"links_that_do_not_open": len(bad)},
        right={"links_that_do_not_open": 0},
        population={"bad": bad, "ok": ok},
        sources={"rows": BATCH, "answer": f"{ANALYZE}?symbol=<identifier>&include_months=false"},
        claim_id=CLAIM_LINK))


# --- 6. the typical inflow ---------------------------------------------------------------

@qa(component="rest.supply_analyzer", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM_TYPICAL)
def test_every_range_uses_the_stated_typical_inflow(rest_anon):
    """Every range is as wide as the typical inflow /definitions and the batch state, plus the
    one buyback part it names."""
    batch = _batch(rest_anon)
    definitions = _json(_paced_get(rest_anon, DEFINITIONS), DEFINITIONS)
    typical = (definitions or {}).get("typical_inflow_pct") if isinstance(definitions, dict) else None
    if not _num(typical):
        raise Inconclusive(f"{DEFINITIONS} states no typical_inflow_pct")
    ranges = [r for r in batch["items"] if r.get("status") == "range"]
    wide = [r for r in ranges if isinstance(r.get("yearly_range"), list) and len(r["yearly_range"]) == 2
            and all(_num(x) for x in r["yearly_range"]) and r["yearly_range"][1] - r["yearly_range"][0] > 0.005]
    if not wide:
        raise Inconclusive("no range row has a width to compare")
    bad = typical_mismatches(batch["items"], typical)
    used: dict[float, int] = {}
    for b in bad:
        used[b["used"]] = used.get(b["used"], 0) + 1
    hype = next((b for b in bad if b["symbol"] == "HYPE"), None)
    conclude(Measurement(
        verdict="failed" if bad else "passed",
        reason=(f"/definitions states a typical inflow of {typical:.2f}% a year (batch: {batch.get('typical_inflow_pct')}); "
                f"{len(bad)} of {len(wide)} ranges add a different figure to their top: "
                + ", ".join(f"{k}% on {v}" for k, v in sorted(used.items(), key=lambda kv: -kv[1]))
                + (f"; HYPE's range is {hype['range'][0]}% to {hype['range'][1]}% ({hype['used']}%)" if hype else "")
                if bad else f"all {len(wide)} ranges add the stated {typical:.2f}%"),
        left={"ranges_with_another_typical": len(bad)},
        right={"ranges_with_another_typical": 0},
        population={"bad": bad, "wide": len(wide), "typical": typical, "batch_as_of": batch.get("as_of")},
        sources={"batch": BATCH, "definitions": DEFINITIONS},
        claim_id=CLAIM_TYPICAL))


# --- 7. an unsupported chain -------------------------------------------------------------

@qa(component="rest.supply_analyzer", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM_CHAIN)
def test_an_unsupported_chain_gets_a_documented_answer(rest_anon):
    """UNI's contract with a chain the analyzer does not read gets a documented answer."""
    answers = []
    for chain in UNSUPPORTED_CHAINS:
        response = _paced_get(rest_anon, ANALYZE, contract=UNI, chain=chain, include_months="false")
        try:
            body = response.json()
        except ValueError:
            body = None
        verdict = chain_answer_documented(response.status_code, body)
        code = None
        if isinstance(body, dict):
            code = ((body.get("error") or {}).get("code")
                    or (((body.get("detail") or {}) if isinstance(body.get("detail"), dict) else {}).get("error") or {}).get("code"))
        answers.append({"chain": chain, "status": response.status_code, "code": code, "documented": verdict})
    judged = [a for a in answers if a["documented"] is not None]
    if not judged:
        raise Inconclusive(f"no answer could be judged: {answers}")
    bad = [a for a in judged if a["documented"] is False]
    conclude(Measurement(
        verdict="failed" if bad else "passed",
        reason=(f"{len(bad)} of {len(judged)} reads of UNI's contract ({UNI}) with an unsupported chain answer "
                + ", ".join(f"chain={a['chain']}: HTTP {a['status']} {a['code']}" for a in bad)
                + "; /openapi-public.json documents 400 \"MISSING_INPUT, INVALID_SYMBOL, INVALID_CONTRACT, "
                  "CHAIN_NEEDED, UNSUPPORTED_CHAIN, NO_PRICE\" for this route"
                if bad else f"all {len(judged)} unsupported chains get a documented answer"),
        left={"undocumented_answers": len(bad)},
        right={"undocumented_answers": 0},
        population={"answers": answers},
        sources={"answer": f"{ANALYZE}?contract={UNI}&chain=<unsupported>&include_months=false"},
        claim_id=CLAIM_CHAIN))


# --- 8. two dilution flags (Gem Screener) ------------------------------------------------

@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM_FLAGS)
def test_a_coin_carries_one_dilution_flag(rest_anon):
    """No coin's snapshot dilution (Checks row, Apps row) and Supply Analyzer dilution
    (Supply card) carry different flags on the snapshot's own lines."""
    snapshot = _snapshot(rest_anon)
    meta = snapshot.get("dilution_meta") or {}
    caution, red = meta.get("caution_line"), meta.get("red_line")
    if not _num(caution) or not _num(red):
        raise Inconclusive(f"{SNAPSHOT} states no caution_line / red_line in dilution_meta")
    judged, differ = two_flags(snapshot["apps"], _batch(rest_anon)["items"], caution, red)
    if not judged:
        raise Inconclusive("no app carries both dilution figures")
    conclude(Measurement(
        verdict="failed" if differ else "passed",
        reason=(f"{len(differ)} of {judged} apps get two different dilution flags (lines {caution}% and "
                f"{red}% a week): the snapshot's figure, which the detail's Checks row reads, and the Supply "
                f"Analyzer's, which the Supply card reads: "
                + "; ".join(f"{d['symbol']} {d['checks_row']}% ({d['checks_flag']}) vs {d['supply_card']}% "
                            f"({d['card_flag']})" for d in differ[:6])
                if differ else f"all {judged} apps carry one flag"),
        left={"apps_with_two_flags": len(differ)},
        right={"apps_with_two_flags": 0},
        population={"differ": differ, "judged": judged, "lines": [caution, red],
                    "snapshot": snapshot.get("generated_at_iso")},
        sources={"snapshot": SNAPSHOT, "analyzer": BATCH},
        claim_id=CLAIM_FLAGS))


# --- 10. tokens locked by holders (PHAR, the operator's named case) ----------------------

PHARAOH_DOCS = "https://docs.phar.gg/pages/contract-addresses"
PHAR = "0x13A466998Ce03Db73aBc2d4DF3bBD845Ed1f28E7"
XPHAR = "0xE8164Ea89665DAb7a553e667F81F30CfDA736B9A"
VOTE_MODULE = "0x34F233F868CdB42446a18562710eE705d66f846b"
ROUTESCAN = "https://api.routescan.io/v2/network/mainnet/evm/43114/etherscan/api"


def _routescan(source, **params) -> float | None:
    try:
        response = source.get(ROUTESCAN, params=params)
        body = response.json() if response.status_code == 200 else None
    except (httpx.HTTPError, ValueError):
        return None
    if not isinstance(body, dict) or body.get("status") != "1":
        return None
    try:
        return int(body["result"]) / 1e18
    except (KeyError, TypeError, ValueError):
        return None


@qa(component="rest.supply_analyzer", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM_LOCKED)
def test_tokens_locked_by_holders_are_not_shown_as_a_reserve(rest_anon, evidence_store):
    """PHAR: the PHAR its holders have locked in xPHAR (read on Avalanche) is not shown as the
    reserve, and at least half of it is shown as staked."""
    record = _single(rest_anon, "pharaoh-exchange")
    if record is None:
        raise Inconclusive(f"{ANALYZE}?symbol=pharaoh-exchange could not be read")
    source = build_source_client(evidence=evidence_store, timeout=60.0)
    try:
        try:
            docs = source.get(PHARAOH_DOCS)
        except httpx.HTTPError as exc:
            raise Inconclusive(f"{PHARAOH_DOCS} could not be read: {type(exc).__name__}")
        page = docs.text.lower() if docs.status_code == 200 else ""
        if PHAR.lower() not in page or XPHAR.lower() not in page:
            raise Inconclusive(f"{PHARAOH_DOCS} no longer lists PHAR {PHAR} and xPHAR {XPHAR}; the addresses "
                               f"this check reads are the project's own, so it cannot tell")
        chain = {
            "total_supply": _routescan(source, module="stats", action="tokensupply", contractaddress=PHAR),
            "locked_in_staking_token": _routescan(source, module="account", action="tokenbalance",
                                                  contractaddress=PHAR, address=XPHAR, tag="latest"),
            "xphar_supply": _routescan(source, module="stats", action="tokensupply", contractaddress=XPHAR),
            "xphar_staked_in_vote_module": _routescan(source, module="account", action="tokenbalance",
                                                      contractaddress=XPHAR, address=VOTE_MODULE, tag="latest"),
        }
    finally:
        source.close()
    if not _num(chain["total_supply"]) or not _num(chain["locked_in_staking_token"]):
        raise Inconclusive(f"the chain could not be read through {ROUTESCAN}: {chain}")
    found = locked_as_reserve(record, chain)
    reserve_tip = ("Max supply minus every token in play, plus the project's own stake. It enters the pile only "
                   "on a decision")
    conclude(Measurement(
        verdict="failed" if found else "passed",
        reason=(f"PHAR on Avalanche: the xPHAR contract ({XPHAR}) holds {chain['locked_in_staking_token']:,.0f} PHAR "
                f"of a total supply of {chain['total_supply']:,.0f}, and {chain['xphar_staked_in_vote_module'] or 0:,.0f} "
                f"of {chain['xphar_supply'] or 0:,.0f} xPHAR are staked in the VoteModule. The record shows "
                f"\"Reserve, outside the pie\" {_f(found['reserve_today'])}"
                + (" (the same tokens)" if found["reserve_is_the_locked_tokens"] else "")
                + f", described on the page as \"{reserve_tip}\", and \"Staked, free to unlock\" "
                f"{found['staked_shown']:,.0f} ({found['staked_shown_share'] * 100:.1f}% of the locked PHAR)"
                if found else
                "the PHAR locked in xPHAR is not shown as the reserve, and at least half of it is shown as staked"),
        left={"locked_shown_as_reserve": bool(found and found["reserve_is_the_locked_tokens"]),
              "staked_shown_share": found["staked_shown_share"] if found else None},
        right={"locked_shown_as_reserve": False, "staked_shown_share": ">= 0.5"},
        population={"chain": chain, "found": found, "record": {k: record.get(k) for k in (
            "total_supply", "circulating", "pile_today", "reserve_today", "refreshed_at")}},
        sources={"record": f"{ANALYZE}?symbol=pharaoh-exchange", "addresses": PHARAOH_DOCS,
                 "chain": ROUTESCAN + " (tokensupply, tokenbalance)"},
        claim_id=CLAIM_LOCKED))


# --- 11. an unknown schedule served as "none scheduled" ----------------------------------

@qa(component="rest.supply_analyzer", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM_SCHEDULE)
def test_an_unknown_schedule_is_not_served_as_none_scheduled(rest_anon, evidence_store):
    """No record that names its vesting schedule unknown serves next_unlock as
    "none_scheduled"; for the chains among them, DeFiLlama's unlock file (the feed the
    analyzer names) is read to show what is scheduled."""
    batch = _batch(rest_anon)
    rows = [r for r in batch["items"] if "vesting schedule" in (r.get("unknown_names") or [])]
    if not rows:
        raise Inconclusive("no record names its vesting schedule unknown")
    served = [r for r in rows if unknown_served_as_none(r)]
    now = int(time.time())
    probed, scheduled = [], []
    source = build_source_client(evidence=evidence_store, timeout=60.0)
    try:
        for row in [r for r in served if (r.get("token") or {}).get("kind") == "chains"]:
            slug = (row.get("token") or {}).get("slug") or ""
            try:
                response = source.get(LLAMA_EMISSIONS.format(slug=slug))
                body = response.json() if response.status_code == 200 else None
            except (httpx.HTTPError, ValueError):
                body = None
            probed.append(f"{_sym(row)}: {'file' if isinstance(body, dict) else 'no file'}")
            ahead = future_unlocks(body, now)
            if ahead:
                scheduled.append({"coin": _sym(row), "next": ahead[:2], "events_ahead": len(ahead),
                                  "url": LLAMA_EMISSIONS.format(slug=slug)})
    finally:
        source.close()
    said = lambda s: (f"{s['coin']}: {s['events_ahead']} unlock events ahead in {s['url']}, the first "
                      + "; ".join(f"{e['date']} {e['tokens']:,.0f} ({e['what'].strip()})" if _num(e["tokens"])
                                  else f"{e['date']} ({e['what'].strip()})" for e in s["next"]))
    conclude(Measurement(
        verdict="failed" if served else "passed",
        reason=(f"{len(served)} of {len(rows)} records that name their vesting schedule unknown serve next_unlock "
                f"{{\"kind\": \"none_scheduled\"}}, which the Gem Screener's Supply card prints as \"none\" with "
                f"\"The schedule on file has no tranche ahead\""
                + (f". Among the {len(probed)} chains of them, DeFiLlama's unlock file lists dated unlocks for "
                   f"{len(scheduled)}: " + " | ".join(said(s) for s in scheduled) if scheduled else "")
                if served else f"none of {len(rows)} records with an unknown schedule claims none is scheduled"),
        left={"unknown_served_as_none": len(served)},
        right={"unknown_served_as_none": 0},
        population={"served": [_sym(r) for r in served], "scheduled_elsewhere": scheduled, "probed": probed},
        sources={"batch": BATCH, "feed": LLAMA_EMISSIONS},
        claim_id=CLAIM_SCHEDULE))


# --- 12. a max supply that is the end of a schedule --------------------------------------

@qa(component="rest.supply_analyzer", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM_MAX)
def test_a_max_supply_is_not_the_end_of_an_issuance_schedule(rest_anon):
    """No sampled record states as its max supply the end total of DeFiLlama's unlock
    schedule. Sample: every chain (the coins most likely to have no cap) and every app whose
    Gem Screener snapshot has no max supply while the analyzer states one."""
    batch = _batch(rest_anon)
    cg_max = {a.get("slug"): (a.get("cg") or {}).get("max") for a in _snapshot(rest_anon)["apps"]}
    rows = [r for r in batch["items"] if _num(r.get("max_supply")) and (
        (r.get("token") or {}).get("kind") == "chains" or not _num(cg_max.get((r.get("token") or {}).get("slug"))))]
    if not rows:
        raise Inconclusive("no row to sample")
    judged, bad, unread = 0, [], []
    for row in rows:
        record = _single(rest_anon, (row.get("token") or {}).get("slug") or "")
        if record is None:
            unread.append(_sym(row))
            continue
        judged += 1
        found = max_from_a_schedule(record)
        if found:
            bad.append(found)
    if not judged:
        raise Inconclusive(f"none of {len(rows)} sampled records could be read")
    named_unread = [u for u in unread if u.split(" ")[0] in ("ETH", "SOL", "TRX")]
    if not bad and (named_unread or judged < 0.9 * len(rows)):
        # "Every chain" is the sample, and ETH, SOL and TRX are the three the finding names: a
        # clean read that skipped them (a failed read, or the session's cap spent by earlier
        # checks) says nothing about them.
        raise Inconclusive(f"{len(unread)} of {len(rows)} sampled records could not be read "
                           f"(named coins unread: {named_unread}): {unread[:6]}")
    bad.sort(key=lambda b: (0 if b["coin"].split(" ")[0] in ("ETH", "SOL", "TRX") else 1, b["coin"]))
    conclude(Measurement(
        verdict="failed" if bad else "passed",
        reason=(f"{len(bad)} of {judged} sampled records state a max supply whose source is a DeFiLlama unlock "
                f"schedule, the end total of its issuance horizon; {sum(1 for b in bad if b['burned_from_it'])} of them "
                f"then show max minus total as \"Bought back, burned\": "
                + "; ".join(f"{b['coin']} max {_f(b['max_supply'])} from \"{b['source']}\" (total {_f(b['total_supply'])}"
                            + (f", burned {b['burned_from_it']:,.0f}" if b["burned_from_it"] else "") + ")"
                            for b in bad[:5])
                if bad else f"none of {judged} sampled records takes its max supply from an unlock schedule"),
        left={"max_from_a_schedule": len(bad)},
        right={"max_from_a_schedule": 0},
        population={"bad": bad, "judged": judged, "unread": unread, "sampled": [_sym(r) for r in rows]},
        sources={"batch": BATCH, "snapshot": SNAPSHOT, "records": f"{ANALYZE}?symbol=<slug>"},
        claim_id=CLAIM_MAX))


# --- 9. tokens out (Gem Screener) --------------------------------------------------------

@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM_OUT)
def test_tokens_out_counts_the_max_supply_of_a_coin_still_issuing(rest_anon):
    """No app with issuance on record is shown ~100% out while under 90% of its max supply
    circulates."""
    snapshot = _snapshot(rest_anon)
    apps = snapshot["apps"]
    judged = [a for a in apps if _num((a.get("supply") or {}).get("out_pct")) and _num((a.get("cg") or {}).get("max"))]
    if not judged:
        raise Inconclusive(f"{SNAPSHOT} has no app with both an out share and a max supply")
    bad = [x for x in (out_ignores_max(a) for a in apps) if x]
    near = [a.get("symbol") for a in judged if (a["supply"]["out_pct"] >= 99
            and _num((a.get("supply") or {}).get("circ") or (a.get("cg") or {}).get("circ"))
            and a["cg"]["max"] > 0                                  # 0 is a value out_ignores_max guards too
            and ((a["supply"].get("circ") or a["cg"].get("circ")) / a["cg"]["max"]) < 0.9)]
    conclude(Measurement(
        verdict="failed" if bad else "passed",
        reason=(f"{len(bad)} apps with new tokens on record are shown as ~100% of tokens out, FDV equal to market "
                f"cap, while under 90% of their max supply circulates ({len(near)} apps in all are shown ~100% out "
                f"under that line): "
                + "; ".join(f"{b['symbol']} {b['out_pct']}% out, circulating {b['circulating']:,.0f} of max "
                            f"{_f(b['max_supply'])} ({b['circ_of_max_pct']}%), FDV {_f(b['fdv'])} vs market cap "
                            f"{_f(b['mcap'])}, new tokens {b['dilution_week_pct']}% a week "
                            f"(${b['emissions_usd30'] or 0:,.0f} in 30 days)" for b in bad[:4])
                if bad else f"no app with issuance on record is shown ~100% out under its max supply"),
        left={"issuing_apps_shown_all_out": len(bad)},
        right={"issuing_apps_shown_all_out": 0},
        population={"bad": bad, "near": near, "judged": len(judged), "snapshot": snapshot.get("generated_at_iso")},
        sources={"snapshot": SNAPSHOT},
        claim_id=CLAIM_OUT))


# --- 13. a pile cannot shrink by more than all of it -------------------------------------

def _hero_text(row) -> str:
    rng = (row or {}).get("yearly_range")
    if isinstance(rng, list) and len(rng) == 2 and all(_num(x) for x in rng) and abs(rng[1] - rng[0]) > 0.05:
        return f"{rng[0]}% to {rng[1]}% a year"
    return f"{(row or {}).get('yearly_pct')}% a year"


@qa(component="rest.supply_analyzer", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM_PAST_ALL)
def test_a_pile_cannot_shrink_by_more_than_all_of_it(rest_anon):
    """No record states a yearly change of its sellable pile below -100%, and no month of a
    record's curve takes out more than the pile holds plus what comes in that month."""
    batch = _batch(rest_anon)
    rows = [r for r in batch["items"] if _num(r.get("yearly_pct"))]
    if not rows:
        raise Inconclusive(f"{BATCH} states a yearly change on no row")
    definitions = _json(_paced_get(rest_anon, DEFINITIONS), DEFINITIONS)
    a_change = hero_as_a_change(definitions)
    hero = [x for x in (shrinks_past_all(r) for r in rows) if x] if a_change else []
    drains = [r for r in batch["items"] if isinstance(r.get("pile_24m"), list) and r["pile_24m"]
              and _num(r["pile_24m"][0]) and r["pile_24m"][0] > 0
              and any(_num(x) and x <= 0 for x in r["pile_24m"])]
    slugs = sorted(({(r.get("token") or {}).get("slug") for r in drains} | {h["slug"] for h in hero}) - {None, ""})
    records, curves, unread = {}, {}, []
    for slug in slugs:
        record = _single(rest_anon, slug)
        if record is None:
            unread.append(slug)
            continue
        records[slug] = record
        curves[slug] = takes_out_more_than_there_is(record)
    overdrawn = {s: c for s, c in curves.items() if c}
    if not hero and not overdrawn:
        if not a_change:
            # A hero renamed to a rate may lawfully read below -100%; a reworded definition may
            # not. Either way the check can no longer say what the figure claims: loud, not a pass.
            raise Inconclusive(f"{DEFINITIONS} no longer defines the hero as \"The yearly change\"; what a "
                               f"figure below -100% claims cannot be read, and no curve overdraws its pile")
        if unread:
            raise Inconclusive(f"{len(unread)} of {len(slugs)} records whose curve empties the pile could not "
                               f"be read: {unread[:6]}")
    by_slug = {(r.get("token") or {}).get("slug"): r for r in batch["items"]}
    hero_slugs = {h["slug"] for h in hero}

    def said(slug) -> str:
        row, record, curve = by_slug.get(slug) or {}, records.get(slug) or {}, overdrawn.get(slug)
        parts = []
        if slug in hero_slugs:
            text = f"\"{_hero_text(row)}\""
            today = record.get("today") or {}
            came, went, pile = (today.get("in") or {}).get("total"), (today.get("out") or {}).get("total"), today.get("pile")
            if all(_num(x) for x in (came, went, pile)):
                text += f" (({came:,.0f} in - {went:,.0f} out) x 12 / {pile:,.0f})"
            parts.append(text)
        if curve:
            first = curve["first"]
            text = (f"its curve takes out {first['out']:,.0f} in {first['label']} with {first['pile']:,.0f} in the "
                    f"pile and {first['in']:,.0f} coming in ({curve['months_over']} such months), the pile reads 0 "
                    f"from {curve['empty_at']}")
            past = curve["bought_back_past_cap"]
            if past:
                text += (f", and it books {past['bought_back']:,.0f} bought back by {past['label']}, more than its "
                         f"{curve['cap_field'].replace('_', ' ')} of {_f(curve['cap'])}")
            parts.append(text)
        return f"{_sym(row) if row else slug}: " + "; ".join(parts)

    bad = sorted(hero_slugs | set(overdrawn))
    hero_part = (f"{len(hero)} of {len(rows)} records state a yearly change of the sellable pile below -100% "
                 f"(/definitions: \"{a_change}\")" if a_change else
                 "the hero is no longer defined as a yearly change (not judged)")
    conclude(Measurement(
        verdict="failed" if bad else "passed",
        reason=(f"{hero_part}, and {len(overdrawn)} of "
                f"{len(curves)} records whose curve empties the pile take out more than it holds: "
                + " | ".join(said(s) for s in bad[:4])
                if bad else
                f"none of {len(rows)} records states a yearly change below -100%, and none of {len(curves)} curves "
                f"that empty the pile takes out more than it holds"),
        left={"yearly_below_minus_100": len(hero), "curves_taking_out_more_than_the_pile": len(overdrawn)},
        right={"yearly_below_minus_100": 0, "curves_taking_out_more_than_the_pile": 0},
        population={"hero": hero, "overdrawn": overdrawn, "unread": unread, "drains": [_sym(r) for r in drains],
                    "rows": len(rows), "hero_definition": a_change, "batch_as_of": batch.get("as_of")},
        sources={"batch": BATCH, "definitions": DEFINITIONS, "records": f"{ANALYZE}?symbol=<slug>"},
        claim_id=CLAIM_PAST_ALL))


@qa(component="rest.supply_analyzer", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM_PAST_MAX)
def test_a_pile_cannot_grow_past_its_max_supply(rest_anon):
    """No record states a yearly change of its sellable pile (the top of a range) that would
    take the pile past its max supply -- the inflow side of #177. Judged only while
    /definitions calls the hero "The yearly change"."""
    batch = _batch(rest_anon)
    definitions = _json(_paced_get(rest_anon, DEFINITIONS), DEFINITIONS)
    a_change = hero_as_a_change(definitions)
    if not a_change:
        raise Inconclusive(f"{DEFINITIONS} no longer defines the hero as \"The yearly change\"; what a figure "
                           f"above the room to the max supply claims cannot be read")
    judged, over = growth_past_max_supply(batch["items"])
    if judged < 50:
        raise Inconclusive(f"only {judged} records state a pile, a max supply and a yearly change")
    over.sort(key=lambda o: o["room_pct"])
    by_symbol = {o["symbol"]: o for o in over}
    conclude(Measurement(
        verdict="failed" if over else "passed",
        reason=(f"{len(over)} of {judged} records state a yearly change that takes the sellable pile past its max "
                f"supply (/definitions: \"{a_change}\"): "
                + "; ".join(f"{o['symbol']} up to +{o['top']}% a year with {o['room_pct']:.2f}% "
                            f"({_f(o['max_supply'] - o['pile'])} tokens) left to its max of {_f(o['max_supply'])}"
                            for o in over[:5])
                if over else
                f"none of {judged} records states a yearly change past the room to its max supply"),
        left={"records_growing_past_max": len(over)},
        right={"records_growing_past_max": 0},
        population={"over": over[:20], "judged": judged, "hero_definition": a_change,
                    "batch_as_of": batch.get("as_of"), "symbols": sorted(by_symbol)},
        sources={"batch": BATCH, "definitions": DEFINITIONS},
        claim_id=CLAIM_PAST_MAX))


# --- 14. the next unlock and its day -----------------------------------------------------

def _dated(row) -> bool:
    nu = (row or {}).get("next_unlock")
    if isinstance(nu, list):
        return any(isinstance(e, dict) and _num(e.get("ts")) for e in nu)
    return isinstance(nu, dict) and _num(nu.get("ts"))


@qa(component="rest.supply_analyzer", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM_NEXT_UNLOCK)
def test_a_next_unlock_states_what_its_day_releases(rest_anon):
    """No sampled record serves a next unlock smaller than what its own tranches release on that
    day, unless next_unlock also states the day's total or names every recipient of it."""
    batch = _batch(rest_anon)
    dated = [r for r in batch["items"] if _dated(r)]
    if not dated:
        raise Inconclusive(f"{BATCH} dates no next unlock on any row")
    dated.sort(key=lambda r: -(r.get("market_cap_usd") if _num(r.get("market_cap_usd")) else 0.0))
    sample = dated[:NEXT_UNLOCK_SAMPLE]
    judged, unread = [], []
    for row in sample:
        token = row.get("token") or {}
        record = None
        for ident in dict.fromkeys(x for x in (token.get("slug"), token.get("gecko_id")) if x):
            record = _single(rest_anon, ident)
            if record is not None:
                break
        seen = next_unlock_against_its_day(record) if record is not None else None
        if seen is None:
            unread.append(_sym(row))
            continue
        judged.append(seen)
    if len(judged) < 5:
        raise Inconclusive(f"only {len(judged)} of {len(sample)} dated records could be judged against their "
                           f"tranches; unread: {unread[:6]}")
    short = [s for s in judged if s["short"]]
    short.sort(key=lambda s: -(s["day_total"] - s["served"]))

    def said(s) -> str:
        parts = ", ".join(f"{p['who']} {_f(p['amount'])}" for p in s["recipients"])
        return (f"{s['coin']} next_unlock {_f(s['served'])} ({', '.join(str(w) for w in s['served_who'])}) on "
                f"{s['day']} while its tranches release {_f(s['day_total'])} that day ({parts})")

    conclude(Measurement(
        verdict="failed" if short else "passed",
        reason=(f"{len(short)} of {len(judged)} records (the {len(sample)} dated rows of the Gem Screener batch "
                f"with the largest market cap) serve a next unlock smaller than what their own tranches release "
                f"on that day: " + "; ".join(said(s) for s in short[:4])
                if short else
                f"all {len(judged)} records judged (the {len(sample)} dated rows with the largest market cap) "
                f"state what their next unlock's day releases"),
        left={"records_short_of_their_day": len(short), "judged": len(judged)},
        right={"records_short_of_their_day": 0},
        population={"short": short[:12], "judged": len(judged), "unread": unread, "dated_rows": len(dated),
                    "sample": [_sym(r) for r in sample], "batch_as_of": batch.get("as_of")},
        sources={"batch": BATCH, "records": f"{ANALYZE}?symbol=<slug>",
                 "contract": "undocumented: next_unlock is an object with no properties in openapi-public.json "
                             "and is absent from /definitions"},
        claim_id=CLAIM_NEXT_UNLOCK))

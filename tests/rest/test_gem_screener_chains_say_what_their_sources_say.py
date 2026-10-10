"""The Gem Screener's Chains tab says what its sources and its own definitions say (2026-10-04).

The operator asked whether the Chains tab (https://cymetica.com/gem-screener/app?view=chains)
shows correct data everywhere, and whether its Upside follows its own benchmark. Verified on
the snapshot generated 2026-10-04 08:47 UTC, all 33 chains (outbox/chains-verification.md):
daily users, DEX volume of 30 days, TVL, market cap, price and supply are DeFiLlama's and
CoinGecko's figures; the held-back caps, the adoption (fourth root of the four inputs), the
price tag, the benchmark (the median price tag of the 19 chains its rule admits, 127.9x) and
every Upside follow the page's published rules exactly. Four places do not; one check each:

1. STABLECOINS ARE DOLLARS. The page: "Stablecoins: dollars parked on the chain. Source:
   DeFiLlama." Seen: the figure is DeFiLlama's token count of the USD-pegged coins
   (`totalCirculating`), not their dollar value (`totalCirculatingUSD`). They differ where a
   coin is not worth $1: USDY at $1.147 made Stellar $840.9M against DeFiLlama's $909.5M for
   the same day (-7.5 %) and Sei $273.1M against $305.7M (-10.7 %); the other 31 chains
   were within 2.5 % (27 within 0.9 %), and all 33 equal the token count exactly. The figure
   enters adoption at the fourth root, so Upside moves 2-3 %.
   ASSERTS: every chain's stablecoins are within 3 % of DeFiLlama's dollar value of its
   USD-pegged coins on the day the snapshot dates the input. EUR- and other non-dollar coins
   are not dollars and are not counted (Gnosis shows only its USD-pegged coins; that passes).

2. THE PRICE TAG AS DESCRIBED. The snapshot prices a chain on market cap / adoption against
   the median of the large chains (`bench_chains`), and llms.txt says so under "Chains from
   ET-28821". Seen: the same section's opening ("What it is") still says a chain's multiple
   is "market cap / yearly activity fees ... compared with a named leader chain, not the
   median", the `price_vs_revenue` line says "(chains: market cap / yearly activity fees)",
   the older Chains line says "`benchmark` names the leader chain"; and the chain detail's
   "Paste into your agent" prompt asks for "its adoption (daily users and fees), its upside
   against the benchmark chain". ASSERTS: no sentence of llms.txt's Gem Screener section, and
   not the agent prompt, describes the price tag as something the live snapshot does not
   compute. The same words beside a snapshot on fees and a leader would be true.

3. ONE WORD, ONE MEASURE. The Adoption column, its tooltip and Upside are the four-input
   measure, which the page says "has no monthly history". The detail's "Adoption growth 6M",
   the trajectory sentence ("Adoption fell 1.0% a month over the last 3 months") and the
   vetting tags ("Declining: Adoption falling 12.8% a month for six months", "Post-crash:
   Adoption is at 29% of its best quarter") read an index of stablecoins and DEX volume, and
   the page's own longer text says so: "Adoption (stablecoins and DEX volume)". Vetting
   decides which chains "Vetted only" shows (9 of 33 hidden that day). ASSERTS: the page
   does not call a reading Adoption that its own words say is stablecoins and DEX volume, or
   that it says adoption cannot have.

4. WHY A CHAIN IS NOT LISTED. The tab's note lists the tokens it leaves out and why, from
   `chains_universe.left_out`. Seen on the 08:47 UTC snapshot: "Not listed, no market data:
   BCH, ETC.", both with `missing: []`, while CoinGecko's markets answered Bitcoin Cash $6.4bn
   and Ethereum Classic $1.4bn; on DeFiLlama Bitcoin Cash has no stablecoin chart and Ethereum
   Classic no DEX volume, so each lacks an input the note does not name. The 04:10 UTC
   snapshot (served at ?view=apps from their cache at 15:01) said the same of ZEC ($22.5bn),
   VET and THETA, which the 08:47 one lists as missing an input: the set moves, the reason
   is false each time. The other 25 reasons held.
   ASSERTS: no chain is left out for missing market data while CoinGecko answers a market
   cap at least the listing floor ($200M) for its token.

NOT asserted: whether adoption, the median or any Upside predicts anything; how the activity
fees behind the 12-month bars are guarded (their published rule, not recomputed); the chart
and supply columns (their own services, checked elsewhere); the page's layout.

SAFE: GETs only. The page and llms.txt anonymously; DeFiLlama through `build_source_client`.
"""

from __future__ import annotations

import time
import urllib.parse

import httpx

from qa import gemaudit as g
from qa.client import build_source_client
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude
from tests.rest.test_gem_screener_numbers_match_their_sources import MAX_SNAPSHOT_AGE_H, get_patiently

CHAINS_PAGE = "/gem-screener/app?view=chains"
LLMS = "/llms.txt"
MIN_CHAINS = 10
MIN_JUDGED_SHARE = 0.8

CLAIM_STABLES = "gem-screener-chain-stablecoins-are-dollars"
CLAIM_DESCRIBED = "gem-screener-chain-price-tag-described-as-computed"
CLAIM_ONE_MEASURE = "gem-screener-chain-adoption-is-one-measure"
CLAIM_LEFT_OUT = "gem-screener-chain-left-out-for-a-true-reason"
LLAMA_DEX = "https://api.llama.fi/overview/dexs/{chain}"

_PAGE: dict = {}


def _page(rest_anon) -> tuple[dict, str]:
    """The Chains tab's own URL: its snapshot and its source, read once per session (2.6 MB,
    slow). Read at the chains URL, not the apps one: on 2026-10-04 at 15:01 UTC their cache
    served ?view=apps from a snapshot 4.6 h older than ?view=chains. A failed read, or a
    snapshot past the age gate, raises Inconclusive and is not kept."""
    key = id(rest_anon)
    if key in _PAGE:
        return _PAGE[key]
    try:
        response = get_patiently(rest_anon, CHAINS_PAGE, headers={"Accept": "text/html"})
    except httpx.HTTPError as exc:
        raise Inconclusive(f"{CHAINS_PAGE} could not be read: {type(exc).__name__}")
    if response.status_code != 200:
        raise Inconclusive(f"{CHAINS_PAGE} answered HTTP {response.status_code}; a failed read is not an empty page")
    try:
        snap = g.parse_snapshot(response.text)
    except g.SnapshotUnreadable as exc:
        raise Inconclusive(f"{CHAINS_PAGE}: {exc}")
    age = g.age_hours(snap, time.time())
    if age is None or age > MAX_SNAPSHOT_AGE_H:
        raise Inconclusive(f"the snapshot is {age if age is None else round(age, 1)} h old; past "
                           f"{MAX_SNAPSHOT_AGE_H:.0f} h a comparison measures drift")
    _PAGE[key] = (snap, response.text)
    return _PAGE[key]


def _chains(snap: dict) -> list[dict]:
    chains = [c for c in snap.get("chains") or [] if isinstance(c, dict)]
    if len(chains) < MIN_CHAINS:
        raise Inconclusive(f"the snapshot carries {len(chains)} chains; fewer than {MIN_CHAINS} is not the tab")
    return chains


def _money(x) -> str:
    return f"${x / 1e6:,.1f}M" if x is not None else "?"


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM_STABLES)
def test_a_chains_stablecoins_are_the_dollars_defillama_counts(rest_anon, evidence_store):
    """Every chain's stablecoins are within 3 % of DeFiLlama's dollar value of the
    USD-pegged coins on that chain, on the day the snapshot dates the input -- or, when
    that day is DeFiLlama's still-open newest point, between it and the closed day
    before (2026-10-10: Filecoin, $0.2M, -5.3 % against an open point 6.6 % above the
    closed day before, while 32 chains agreed within 0.075 %)."""
    snap, _ = _page(rest_anon)
    chains = _chains(snap)
    charts: dict = {}
    source = build_source_client(evidence=evidence_store, timeout=60.0)
    try:
        for chain in chains:
            url = g.LLAMA_STABLECOIN_CHART.format(chain=urllib.parse.quote(str(chain.get("name") or "")))
            try:
                response = source.get(url)
                body = response.json() if response.status_code == 200 else None
            except (httpx.HTTPError, ValueError):
                body = None
            charts[chain.get("slug")] = body if isinstance(body, list) else None
    finally:
        source.close()
    said = g.chain_stablecoin_gaps(chains, charts)
    if said["judged"] < MIN_JUDGED_SHARE * len(chains):
        raise Inconclusive(f"only {said['judged']} of {len(chains)} chains could be compared: "
                           + "; ".join(said["unread"][:5]))
    if not said["gaps"] and said["unread"]:
        # "Every chain" is the contract: a pass with the chains that carried the defect among
        # the unread says nothing about them, so only a gap found may stand on a partial read.
        raise Inconclusive(f"no chain is off, but {len(said['unread'])} of {len(chains)} could not be compared: "
                           + "; ".join(said["unread"][:5]))
    gaps = sorted(said["gaps"], key=lambda x: x["gap_pct"])
    counted = sum(1 for x in gaps if x["tokens_match"])
    conclude(Measurement(
        verdict="failed" if gaps else "passed",
        reason=(f"{len(gaps)} of {said['judged']} chains show stablecoins more than "
                f"{100 * g.STABLECOIN_TOLERANCE:g}% from DeFiLlama's dollar value of their USD-pegged coins "
                f"for the same day: "
                + "; ".join(f"{x['name']} {_money(x['shown'])} against {_money(x['usd'])} ({x['gap_pct']:+.1f}%)"
                            for x in gaps[:5])
                + f"; {counted} of them equal DeFiLlama's token count (totalCirculating) instead; the other "
                  f"{said['judged'] - len(gaps)} are within {said['max_ok_gap_pct']}%"
                if gaps else
                f"all {said['judged']} chains are within {said['max_ok_gap_pct']}% of DeFiLlama's dollar figure"
                + (f", or between its still-open day and the closed day before: "
                   + "; ".join(f"{x['name']} {_money(x['shown'])} ({x['gap_pct']:+.1f}% against the open point)"
                               for x in said["moving"][:5])
                   if said.get("moving") else "")),
        left={"chains_off_by_more_than_3pct": len(gaps)},
        right={"chains_off_by_more_than_3pct": 0},
        population={"gaps": gaps, "judged": said["judged"], "unread": said["unread"], "moving": said["moving"],
                    "max_ok_gap_pct": said["max_ok_gap_pct"], "snapshot_generated_at": snap.get("generated_at")},
        sources={"page": CHAINS_PAGE, "defillama": g.LLAMA_STABLECOIN_CHART},
        claim_id=CLAIM_STABLES))


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM_DESCRIBED)
def test_the_chain_price_tag_is_described_as_the_snapshot_computes_it(rest_anon):
    """No sentence of llms.txt's Gem Screener section, and not the chain detail's agent
    prompt, describes a chain's price tag as something the live snapshot does not compute."""
    snap, page = _page(rest_anon)
    bench = snap.get("bench_chains") or {}
    try:
        response = get_patiently(rest_anon, LLMS)
    except httpx.HTTPError as exc:
        raise Inconclusive(f"{LLMS} could not be read: {type(exc).__name__}")
    if response.status_code != 200:
        raise Inconclusive(f"{LLMS} answered HTTP {response.status_code}; a failed read is not an empty file")
    docs = g.chain_price_tag_claims(response.text, bench)
    if docs["unread"]:
        raise Inconclusive("; ".join(docs["unread"]))
    prompt = g.chain_agent_prompt_claims(page, bench)
    if prompt["unread"] and not prompt["stale"] and not docs["stale"]:
        # Half of the contract is the agent prompt: unread, the pass would say nothing about it.
        raise Inconclusive("the agent prompt was not read: " + "; ".join(prompt["unread"]))
    stale =[f"llms.txt: \"{c['said']}\"" for c in docs["stale"]] + [f"agent prompt: \"{s}\"" for s in prompt["stale"]]
    conclude(Measurement(
        verdict="failed" if stale else "passed",
        reason=(f"the snapshot prices a chain on market cap / {docs['measure']} against the {docs['kind']} of "
                f"{bench.get('n_members')} large chains ({bench.get('mult')}x); {len(stale)} descriptions say "
                f"otherwise: " + "; ".join(stale)
                + ("" if not prompt["unread"] else f" (agent prompt not read: {prompt['unread'][0]})")
                if stale else
                f"llms.txt and the agent prompt describe the chain price tag as the snapshot computes it "
                f"(market cap / {docs['measure']}, {docs['kind']})"
                + ("" if not prompt["unread"] else f"; agent prompt not read: {prompt['unread'][0]}")),
        left={"stale_descriptions": len(stale)},
        right={"stale_descriptions": 0},
        population={"llms_txt": docs["stale"], "agent_prompt": prompt["stale"], "prompt_text": prompt["prompt"],
                    "bench_basis": bench.get("basis"), "bench_kind": bench.get("kind"),
                    "adoption_version": bench.get("adoption_version"),
                    "snapshot_generated_at": snap.get("generated_at")},
        sources={"llms_txt": LLMS, "page": CHAINS_PAGE},
        claim_id=CLAIM_DESCRIBED))


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM_ONE_MEASURE)
def test_adoption_names_one_measure_on_the_chains_tab(rest_anon):
    """The page does not call a reading Adoption that its own words say is stablecoins
    and DEX volume, or that it says adoption cannot have."""
    snap, page = _page(rest_anon)
    chains = _chains(snap)
    said = g.chain_adoption_two_measures(page, chains)
    if said["verdict"] == "unread":
        raise Inconclusive(said["why"])
    rows = said["rows"]
    conclude(Measurement(
        verdict="failed" if said["verdict"] == "two_measures" else "passed",
        reason=(f"the Adoption column and Upside use four inputs"
                + (", which the page says have no monthly history" if said["no_history"] else "")
                + f"; the page also calls {', '.join(repr(r) for r in said['readings'])} adoption, readings of "
                  f"stablecoins and DEX volume; {len(rows)} of {len(chains)} chains are not vetted on them "
                  f"(hidden in 'Vetted only'): "
                + ", ".join(f"{r['name']} ({'/'.join(r['reliable_fail'] or [])})" for r in rows[:9])
                if said["verdict"] == "two_measures" else
                f"Adoption names one measure on the Chains tab ({said['why']})"),
        left={"readings_called_adoption": len(said["readings"])},
        right={"readings_called_adoption": 0},
        population={"readings": said["readings"], "no_history_stated": said["no_history"], "rows": rows,
                    "snapshot_generated_at": snap.get("generated_at")},
        sources={"page": CHAINS_PAGE},
        claim_id=CLAIM_ONE_MEASURE))


def _llama_has(get, url: str, test) -> bool | None:
    """Whether DeFiLlama answers `url` with what `test` looks for; None when it could not be
    read at all (a timeout is not an absence)."""
    try:
        response = get(url)
    except httpx.HTTPError:
        return None
    if response.status_code != 200:
        return False
    try:
        return bool(test(response.json()))
    except ValueError:
        return False


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM_LEFT_OUT)
def test_a_chain_left_out_for_no_market_data_has_none(rest_anon, evidence_store):
    """No chain is left out of the tab for missing market data while CoinGecko answers a
    market cap at least the listing floor for its token."""
    snap, _ = _page(rest_anon)
    universe = snap.get("chains_universe") or {}
    if not isinstance(universe.get("left_out"), list):
        raise Inconclusive("the snapshot carries no chains_universe.left_out")
    ids = sorted({r.get("gecko_id") for r in universe["left_out"]
                  if isinstance(r, dict) and r.get("reason") == "no_market_data" and r.get("gecko_id")})
    markets: dict = {}
    inputs: dict = {}
    if ids:
        source = build_source_client(evidence=evidence_store, timeout=60.0)
        try:
            try:
                rows = g.fetch_coingecko(source.get, ids)
            except g.SourceUnavailable as exc:
                raise Inconclusive(str(exc))
            except httpx.HTTPError as exc:
                raise Inconclusive(f"CoinGecko could not be read: {type(exc).__name__}")
            answered = {r.get("id"): r.get("market_cap") for r in rows if isinstance(r, dict)}
            markets = {gid: answered.get(gid) for gid in ids}
            for row in universe["left_out"]:
                chain = row.get("chain") if isinstance(row, dict) else None
                if row.get("reason") != "no_market_data" or not chain:
                    continue
                q = urllib.parse.quote(chain)
                inputs[row.get("symbol")] = {
                    "stablecoins": _llama_has(source.get, g.LLAMA_STABLECOIN_CHART.format(chain=q),
                                              lambda b: isinstance(b, list) and b),
                    "dex_volume_30d": _llama_has(source.get, LLAMA_DEX.format(chain=q) +
                                                 "?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true",
                                                 lambda b: isinstance(b, dict) and (b.get("total30d") or 0) > 0)}
        finally:
            source.close()
    said = g.chain_left_out_reason_breaches(universe, markets)
    if said["unread"]:
        raise Inconclusive(f"CoinGecko did not answer for {said['unread']}")
    bad = said["breaches"]
    lacks = lambda sym: [k for k, v in (inputs.get(sym) or {}).items() if v is False]
    conclude(Measurement(
        verdict="failed" if bad else "passed",
        reason=(f"{len(bad)} of {len(universe['left_out'])} tokens left out are said to have no market data while "
                f"CoinGecko answers a market cap: "
                + "; ".join(f"{b['symbol']} ${b['coingecko_market_cap'] / 1e9:,.2f}bn (stated missing inputs "
                            f"{b['missing_stated']}; DeFiLlama lacks {lacks(b['symbol']) or 'nothing we read'})"
                            for b in bad)
                if bad else
                (f"the {said['judged']} tokens left out for no market data have none on CoinGecko"
                 if said["with_reason"] else "no chain is left out for missing market data")),
        left={"left_out_with_market_data": len(bad)},
        right={"left_out_with_market_data": 0},
        population={"breaches": bad, "defillama_inputs": inputs, "left_out": len(universe["left_out"]),
                    "list_stale": universe.get("list_stale"), "list_fetched_at": universe.get("list_fetched_at"),
                    "snapshot_generated_at": snap.get("generated_at")},
        sources={"page": CHAINS_PAGE, "coingecko": g.COINGECKO, "defillama": [g.LLAMA_STABLECOIN_CHART, LLAMA_DEX]},
        claim_id=CLAIM_LEFT_OUT))

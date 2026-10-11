"""GET /launchpad/onchain/tokens without `chain_id` lists the launches, not nothing.

Their schema (`openapi-public.json`) declares `chain_id` on this endpoint as
`anyOf: [integer, null]` with no default, and the developer page
(/launchpad/robinhood/api) lists it among the query parameters of "List launches --
a JSON array of token rows". The screener, two lines below it on the same page, has
the identical `chain_id` declaration and answers without one with the launches of
every chain. So does the MCP twin: `launchpad_list_tokens` with no arguments returns
a page of rows from both chains.

**What was seen when this was written** (2026-10-11, 05:30-06:00 UTC, every variant
read twice or more): `GET /tokens` with no `chain_id` answered `200 []` for the
default call, `sort=volume`, `sort=graduating`, `limit=5`, `limit=200`, `offset=0` and
`include_internal=true`. With `chain_id=4663` it lists 1 launch, with `chain_id=5042`
518. `GET /screener` without a chain listed rows from both chains, and the MCP tool
with no arguments returned 25 rows (24 on 5042, 1 on 4663). `GET /config` carries
`chains: []` and all three launchpad chains in `paused_chain_ids` at the same time,
and the one published default-chain convention ("Default: the first enabled chain" on
launch/prepare) would give an empty answer there -- but no document says the list
follows it, and a chain the list is asked for by number is answered although paused.

**The rule.** An unfiltered list is not a smaller list than the filtered ones: when a
chain, asked for by number, lists launches, the call that names no chain either lists
launches (any of them) or refuses with a 422 that names `chain_id`. A `200 []` is the
one answer that is neither; it reads as "there are no launches" to a caller that has
no reason to suspect a missing parameter.

**Measured twice, 20 seconds apart,** and counted only when both reads are empty
(a rotating source is sampling, `a-check-on-a-rotating-population-is-sampling`).
SAFE. GETs only, anonymous; the MCP read is context and cannot decide the verdict.
"""

from __future__ import annotations

import time

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

TOKENS = "/api/v1/launchpad/onchain/tokens"
SCREENER = "/api/v1/launchpad/onchain/screener"
PAUSE_S = 1.2
SECOND_LOOK_S = 20.0
ROWS = 5


def empty_while_filtered_lists(status: int, body, per_chain: dict) -> bool | None:
    """True when the unfiltered read is a 200 with no rows although a chain named by number lists some.

    None when the read cannot be judged (not a 200 or a 422, not a list) -- never a defect by
    guessing. A 422 is an honest refusal and is False, as is any non-empty list."""
    if status == 422:
        return False
    if status != 200 or not isinstance(body, list):
        return None
    if not any(n for n in per_chain.values() if isinstance(n, int) and n > 0):
        return None
    return len(body) == 0


@qa(component="chain.launchpad", tier=SafetyTier.SAFE, surface="rest",
    claim="launchpad-tokens-without-a-chain-lists-launches")
def test_the_token_list_without_a_chain_is_not_empty_while_a_chain_lists_launches(rest_anon, mcp_anon):
    """No chain_id: some launches or a 422 naming it; never a 200 with no rows."""
    time.sleep(PAUSE_S)
    sc = rest_anon.get(SCREENER, params={"limit": 500, "include_external": "false"})
    if sc.status_code != 200 or not isinstance(sc.json(), list):
        raise Inconclusive(f"the screener (the chain list) answered HTTP {sc.status_code}")
    chains = sorted({r.get("chain_id") for r in sc.json()
                     if isinstance(r, dict) and isinstance(r.get("chain_id"), int)})
    if not chains:
        raise Inconclusive("the unfiltered screener names no chain, so no chain is known to list launches")

    per_chain, unread = {}, []
    for chain in chains:
        time.sleep(PAUSE_S)
        r = rest_anon.get(TOKENS, params={"chain_id": chain, "limit": ROWS})
        if r.status_code != 200 or not isinstance(r.json(), list):
            unread.append(f"chain_id={chain}: HTTP {r.status_code}")
            continue
        per_chain[chain] = len(r.json())
    if not any(per_chain.values()):
        raise Inconclusive(f"no chain read by number lists a launch ({per_chain}; {unread})")

    def read_unfiltered():
        time.sleep(PAUSE_S)
        r = rest_anon.get(TOKENS, params={"limit": 50})
        try:
            body = r.json()
        except ValueError:
            body = None
        return r.status_code, body

    first = read_unfiltered()
    first_empty = empty_while_filtered_lists(*first, per_chain)
    second = None
    if first_empty:
        time.sleep(SECOND_LOOK_S)
        second = read_unfiltered()
    second_empty = empty_while_filtered_lists(*second, per_chain) if second else None
    if first_empty is None or (first_empty and second_empty is None):
        raise Inconclusive(f"the unfiltered list could not be judged: first read HTTP {first[0]}, "
                           f"second {second[0] if second else 'not made'}")
    failed = bool(first_empty and second_empty)

    # Context, never the verdict: what the screener and the MCP twin answer with no chain named.
    time.sleep(PAUSE_S)
    mcp_rows = None
    try:
        mcp_rows = len((mcp_anon.call("launchpad_list_tokens", {}) or {}).get("result", {}).get("tokens") or [])
    except Exception as exc:  # noqa: BLE001 -- context only; the REST reads decide
        mcp_rows = f"unread ({type(exc).__name__})"

    listed = ", ".join(f"chain_id={c} lists {n}{'+' if n >= ROWS else ''}" for c, n in per_chain.items())
    conclude(Measurement(
        verdict="failed" if failed else "passed",
        reason=(f"GET {TOKENS} with no chain_id answered 200 with [] on both reads, 20 seconds apart, "
                f"while the same endpoint {listed} (limit={ROWS}); the unfiltered screener lists "
                f"{len(sc.json())} rows over chains {chains} and launchpad_list_tokens with no arguments "
                f"returns {mcp_rows} rows"
                if failed else
                f"the unfiltered token list answers HTTP {first[0]} with "
                f"{len(first[1]) if isinstance(first[1], list) else 'a refusal'} rows "
                f"({listed})"),
        left={"unfiltered_rows": len(first[1]) if isinstance(first[1], list) else None,
              "second_read_rows": len(second[1]) if second and isinstance(second[1], list) else None},
        right={"rows_where_a_chain_is_named": per_chain},
        population={"chains_in_screener": chains, "per_chain": per_chain, "unread": unread,
                    "unfiltered_status": first[0], "screener_rows": len(sc.json()),
                    "mcp_launchpad_list_tokens_no_args_rows": mcp_rows},
        sources={"contract": "openapi-public.json GET /api/v1/launchpad/onchain/tokens: chain_id "
                             "anyOf [integer, null], no default; /launchpad/robinhood/api: "
                             "'List launches -- a JSON array of token rows'",
                 "endpoint": TOKENS, "sibling": SCREENER},
        claim_id="launchpad-tokens-without-a-chain-lists-launches"))

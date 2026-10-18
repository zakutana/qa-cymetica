"""The launchpad discovery tool does not list the launches their REST list marks internal.

`GET /api/v1/launchpad/onchain/tokens` declares `include_internal` (default `false`):
"Admin/debug: include platform seed + test launches". So by their own words a launch of
that kind is not part of the public list, and the Launchpad page (which reads this
endpoint with `chain_id`) does not show one. The MCP tool `launchpad_list_tokens` is
described as the "free discovery feed" and llms.txt says what it is for: "discover
what to buy"; each row carries a `buy_via` hint that points at `launchpad_trade_quote`.
The tool has no `include_internal` argument.

**What was seen when this was written** (2026-10-11, 05:35-06:10 UTC, read twice):
on chain 4663 the REST list answers 1 launch (RUG); with `include_internal=true` it
answers 6. `launchpad_list_tokens` with `chain_id=4663` returns the same 6, the five
that REST keeps internal among them (NXSOC, NXTEST, GTEST, CYMHS, CYMG: test launches
with 0-1 holders and volumes of at most 0.0006), each with a `buy_via` hint. The
unfiltered screener, like REST, lists only RUG on that chain.

**The rule.** The launches the REST list keeps internal by default do not appear in the
feed an agent is told to read to discover what to buy. A chain is judged only when its
whole public list fits one REST page (limit 200), so that "not in the public list" is
known and not a guess about a page that was not read; the MCP tool has no offset, so a
chain larger than its 100-row window would be judged on that window only.

SAFE. GETs and the read-only MCP tool, anonymous. Measured twice, 20 seconds apart,
and counted only when both reads leak the same launches.
"""

from __future__ import annotations

import time

from qa.client import McpError
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

TOKENS = "/api/v1/launchpad/onchain/tokens"
SCREENER = "/api/v1/launchpad/onchain/screener"
CONFIG = "/api/v1/launchpad/onchain/config"
PAGE = 200
MCP_WINDOW = 100
PAUSE_S = 1.2
SECOND_LOOK_S = 20.0


def leaked_internal(mcp_addresses, rest_public, rest_internal) -> list[str]:
    """Addresses the MCP feed lists that the REST list keeps internal.

    Internal means in the include_internal=true list and not in the default one; an address
    in neither (a launch younger than one read, or another chain's) is not judged here."""
    public = {a.lower() for a in rest_public}
    everything = {a.lower() for a in rest_internal}
    return sorted(a.lower() for a in mcp_addresses if a.lower() in everything and a.lower() not in public)


def _rest_addresses(rest, chain: int, internal: bool):
    params = {"chain_id": chain, "limit": PAGE}
    if internal:
        params["include_internal"] = "true"
    time.sleep(PAUSE_S)
    r = rest.get(TOKENS, params=params)
    body = r.json() if r.status_code == 200 else None
    if not isinstance(body, list):
        return None, f"chain_id={chain}{' +internal' if internal else ''}: HTTP {r.status_code}"
    return [(t.get("address"), t.get("symbol")) for t in body if isinstance(t, dict) and t.get("address")], None


def _mcp_addresses(mcp, chain: int):
    time.sleep(PAUSE_S)
    try:
        body = mcp.call("launchpad_list_tokens", {"chain_id": chain, "limit": MCP_WINDOW})
    except McpError:
        return None
    rows = ((body or {}).get("result") or {}).get("tokens") if isinstance(body, dict) else None
    if not isinstance(rows, list):
        return None
    named = [(t.get("address"), t.get("symbol")) for t in rows if isinstance(t, dict) and t.get("address")]
    # Rows that name no address are a shape we cannot read, never a feed that leaks nothing (C06).
    return None if rows and not named else named


def settle(first: dict, second: dict) -> tuple[dict, list]:
    """The first read's leaks as the second look leaves them: (confirmed, unsettled). A chain the
    second look could not judge is unsettled -- a failed read is not a leak that went away (rule 8,
    deep pass 2026-10-11, C06); one it judged without the leak was a moment."""
    confirmed, unsettled = {}, []
    for chain, v in first.items():
        if not v.get("leaked"):
            continue
        if chain not in second:
            unsettled.append(chain)
        elif set(second[chain].get("leaked") or []) & set(v["leaked"]):
            confirmed[chain] = second[chain]
    return confirmed, unsettled


def chains_to_judge(screener_reads, config) -> list[int]:
    """Every chain any source names: the screener with and without external launches, and /config's
    `chains` and `paused_chain_ids`. C04, deep pass 2026-10-18: the public screener alone names a
    chain only while it has a public launch, so a chain whose launches are all internal was never
    asked -- and on 2026-10-18 it named none at all, while /config named 4663, 5042 and 5042002."""
    found = set()
    for rows in screener_reads or []:
        for row in rows if isinstance(rows, list) else []:
            if isinstance(row, dict) and isinstance(row.get("chain_id"), int):
                found.add(row["chain_id"])
    config = config if isinstance(config, dict) else {}
    for key in ("chains", "paused_chain_ids"):
        for item in config.get(key) or []:
            if isinstance(item, int) and not isinstance(item, bool):
                found.add(item)
            elif isinstance(item, dict):
                cid = item.get("chain_id", item.get("id"))
                if isinstance(cid, int) and not isinstance(cid, bool):
                    found.add(cid)
    return sorted(found)


def clean_line(first: dict) -> str:
    """The pass's per-chain line. A leak the second look did not see again is said as such -- the
    pass settles it as a moment, but "0 leaked" for a chain whose first read leaked five was false (C03)."""
    return "; ".join(
        f"chain_id={c}: {v['internal_by_rest']} internal, "
        + (f"{len(v['leaked'])} listed on the first read and gone on the second look {SECOND_LOOK_S:g} s later"
           if v.get("leaked") else "0 leaked")
        for c, v in first.items())


def _one_read(rest, mcp, chains):
    judged, unmeasured = {}, []
    for chain in chains:
        public, why = _rest_addresses(rest, chain, False)
        if public is None:
            unmeasured.append(why)
            continue
        if len(public) >= PAGE:
            unmeasured.append(f"chain_id={chain}: the public list is a full page ({len(public)}), "
                              f"'not in it' cannot be known from one page")
            continue
        internal, why = _rest_addresses(rest, chain, True)
        if internal is None:
            unmeasured.append(why)
            continue
        mcp_rows = _mcp_addresses(mcp, chain)
        if mcp_rows is None:
            unmeasured.append(f"chain_id={chain}: launchpad_list_tokens returned no token list")
            continue
        symbols = {a.lower(): s for a, s in internal}
        hidden_by_rest = sorted({a.lower() for a, _ in internal} - {a.lower() for a, _ in public})
        leaked = leaked_internal([a for a, _ in mcp_rows], [a for a, _ in public], [a for a, _ in internal])
        judged[chain] = {"rest_public": len(public), "rest_with_internal": len(internal),
                         "mcp_rows": len(mcp_rows), "internal_by_rest": len(hidden_by_rest),
                         "leaked": leaked, "leaked_symbols": [symbols.get(a) for a in leaked]}
    return judged, unmeasured


@qa(component="chain.launchpad", tier=SafetyTier.SAFE, surface="mcp",
    claim="launchpad-discovery-feed-lists-no-internal-launch")
def test_the_discovery_tool_does_not_list_what_the_rest_list_keeps_internal(rest_anon, mcp_anon):
    """launchpad_list_tokens shows no launch that GET /tokens hides as admin/debug."""
    reads, statuses = [], []
    for external in ("false", "true"):
        time.sleep(PAUSE_S)
        sc = rest_anon.get(SCREENER, params={"limit": 500, "include_external": external})
        statuses.append(sc.status_code)
        reads.append(sc.json() if sc.status_code == 200 else None)
    time.sleep(PAUSE_S)
    cf = rest_anon.get(CONFIG)
    config = cf.json() if cf.status_code == 200 else None
    if not isinstance(config, dict) and not any(isinstance(r, list) for r in reads):
        raise Inconclusive(f"neither the screener (HTTP {statuses}) nor {CONFIG} (HTTP {cf.status_code}) "
                           f"answered a chain list")
    chains = chains_to_judge(reads, config)
    if not chains:
        raise Inconclusive("no chain is named by the screener or by /config")

    first, unmeasured = _one_read(rest_anon, mcp_anon, chains)
    if not first:
        raise Inconclusive(f"no chain could be judged: {unmeasured}")
    if not any(v["internal_by_rest"] for v in first.values()):
        raise Inconclusive("the REST list keeps no launch internal on any judged chain, so there is "
                           "nothing for the discovery feed to leak")

    candidates = {c: v for c, v in first.items() if v["leaked"]}
    confirmed, unsettled = {}, []
    if candidates:
        time.sleep(SECOND_LOOK_S)
        second, _ = _one_read(rest_anon, mcp_anon, sorted(candidates))
        confirmed, unsettled = settle(first, second)
    if unsettled and not confirmed:
        raise Inconclusive(f"the first read saw internal launches in the feed on chain(s) {unsettled}, and "
                           f"the second look could not read them again; neither a leak nor its absence")
    if unmeasured and not confirmed:
        # A05, deep pass 2026-10-15: a chain the first read could not judge is unread, not clean --
        # the chain that held the defect (4663) failing its read must not leave a pass behind.
        raise Inconclusive(f"no leak on the {len(first)} chain(s) judged, but {len(unmeasured)} could not be "
                           f"judged: {unmeasured[:3]}")

    def line(chain, v):
        return (f"chain_id={chain}: REST lists {v['rest_public']} (default) or {v['rest_with_internal']} "
                f"(include_internal=true), launchpad_list_tokens returns {v['mcp_rows']} including "
                f"{len(v['leaked'])} the REST list keeps internal ({', '.join(str(s) for s in v['leaked_symbols'])})")

    conclude(Measurement(
        verdict="failed" if confirmed else "passed",
        reason=(f"the discovery tool lists launches that GET {TOKENS} marks admin/debug, on both reads, "
                f"20 seconds apart: " + "; ".join(line(c, v) for c, v in confirmed.items())
                if confirmed else
                "the discovery tool lists none of the launches the REST list keeps internal "
                "(" + clean_line(first) + ")"),
        left={"internal_launches_in_the_discovery_feed": {c: v["leaked_symbols"] for c, v in confirmed.items()}},
        right={"internal_launches_in_the_discovery_feed": {}},
        population={"chains": chains, "first_read": first, "confirmed": confirmed, "unmeasured": unmeasured},
        sources={"contract": "openapi-public.json GET /api/v1/launchpad/onchain/tokens: include_internal "
                             "(default false) 'Admin/debug: include platform seed + test launches'; MCP "
                             "launchpad_list_tokens: 'Free discovery feed'; llms.txt: 'discover what to buy'",
                 "rest": TOKENS, "mcp": "launchpad_list_tokens"},
        claim_id="launchpad-discovery-feed-lists-no-internal-launch"))

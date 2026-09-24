"""Build the platform section map that the dashboard renders.

This is an INVENTORY, not a test suite. It answers one question:

    What are the sections of the Cymetica platform, how big is each one, and
    how much of each actually responds?

Sources are the platform's own documents -- openapi.json, llms.txt,
agent-skills.json, agent-card.json, .well-known/mcp.json -- so the map is
grounded in what they publish rather than in what we imagine. Reachability is
then measured with read-only GETs at two identities (anonymous and TRUSTED),
which is what turns "documented" into a percentage.

Everything here is SAFE tier. No POST is ever issued.

    python scripts/inventory.py
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qa.client import build_client, build_mcp_client  # noqa: E402
from qa.config import identities  # noqa: E402
from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier  # noqa: E402

def out_path() -> Path:
    """The section map, resolved through the QA_STATE_DIR seam at call time.

    It was `REPO_ROOT / "state" / "inventory.json"`, bound at import, which is
    the shape `scripts/bounty.py::out_path` records an incident for: a test
    setting QA_STATE_DIR was handed the committed file, and one of them wrote
    its fixture over the real snapshot. The exposure here was narrower -- the
    write sits under `__main__` and the tests import `build`/`compare` -- but
    the committed map is what `tests/repo/test_repo_consistency.py` holds our
    section list against, so an overwrite would be quiet and load-bearing.
    Architecture audit, 2026-09-20.
    """
    from qa.state import state_dir

    return state_dir() / "inventory.json"

# ---------------------------------------------------------------------------
# The platform section map.
#
# `patterns` are matched against REST paths; `tools` against MCP tool names.
# Order matters: the first section whose pattern matches wins, so put narrow
# sections above broad ones.
# ---------------------------------------------------------------------------
SECTIONS: list[dict] = [
    {
        "id": "discovery",
        "title": "Discovery & manifests",
        "blurb": "The 11 well-known protocol documents, llms.txt, OpenAPI. Everything an outside agent reads before it does anything.",
        "patterns": [r"^/\.well-known/", r"^/llms", r"^/openapi", r"^/robots\.txt", r"^/AGENTS\.md", r"^/founder\.txt"],
        "tools": [],
        "blast": "measurement",
    },
    {
        "id": "identity_trust",
        "title": "Identity & trust ladder",
        "blurb": "Agent registration, trust tiers, and which tools each tier is allowed to see. The platform's whole authorization model.",
        "patterns": [r"^/mcp/v1/register", r"^/mcp/v1/agents/me", r"^/mcp/v1/well-known", r"^/mcp/v1/capabilities", r"^/oauth/"],
        "tools": ["who_is_this", "get_trust_signal", "get_trust_ladder", "get_agent_profile", "get_rate_limits"],
        "blast": "custody",
    },
    {
        "id": "mcp",
        "title": "MCP server & protocol",
        "blurb": "JSON-RPC 2.0 endpoint, tools/list, tools/call, plus the resources and prompts the server advertises.",
        "patterns": [r"^/mcp/v1$", r"^/mcp/v1/tools", r"^/mcp/v1/resources", r"^/mcp/v1/prompts"],
        "tools": [],
        "blast": "custody",
    },
    {
        "id": "funding",
        "title": "Funding & custody",
        "blurb": "Deposit addresses and withdrawals. The endpoints where a mistake costs money rather than credibility.",
        "patterns": [r"^/api/v1/funding/"],
        "tools": ["get_deposit_address"],
        "blast": "custody",
    },
    {
        "id": "account",
        "title": "Account & portfolio",
        "blurb": "Balances, positions, portfolio, transaction history.",
        "patterns": [r"^/api/v1/account", r"^/auth/login", r"^/api/v1/portfolio", r"^/api/v1/rewards/"],
        "tools": ["get_positions", "get_order_history"],
        "blast": "custody",
    },
    {
        "id": "clob",
        "title": "CLOB exchange",
        "blurb": "The central limit orderbook: pairs, books, order placement, token exchange.",
        "patterns": [r"^/api/v1/clob/", r"^/api/v1/exchange/", r"^/api/v1/orders", r"^/api/v1/trades", r"^/api/v1/positions", r"^/api/v1/vaix/"],
        "tools": ["get_orderbook", "list_clob_pairs", "place_order"],
        "blast": "custody",
    },
    {
        "id": "markets",
        "title": "Markets & prices",
        "blurb": "Prediction markets, price feeds, market search and analytics.",
        "patterns": [r"^/api/v1/markets", r"^/api/v1/prices", r"^/api/v1/price", r"^/api/v1/perpetual/", r"^/api/v1/winner-takes-all/", r"^/api/v1/robinhood/"],
        "tools": ["list_markets", "get_market", "search_markets", "get_prices", "get_market_analytics", "get_oracle_insights"],
        "blast": "integrity",
    },
    {
        "id": "event_cards",
        "title": "Event Cards (EVCDX)",
        "blurb": "Themed asset baskets traded as index markets, advertised with up to 10x leverage.",
        "patterns": [r"^/api/v1/event-cards", r"^/api/v1/evcdx"],
        "tools": [],
        "blast": "integrity",
    },
    {
        "id": "arena",
        "title": "CyMetica-42 Arena",
        "blurb": "Blue vs Red team AI hedge-fund competition and betting on it.",
        "patterns": [r"^/api/v1/arena"],
        "tools": [],
        "blast": "integrity",
    },
    {
        "id": "agents",
        "title": "AI trading agents",
        "blurb": "Agent species, cloning, leaderboards, skills. The headline product for AI callers.",
        "patterns": [r"^/api/v1/agents/", r"^/api/v1/agent-species", r"^/api/v1/bots/", r"^/api/v1/skills", r"^/api/v1/leaderboard", r"^/api/v1/cloned-bot"],
        "tools": [],
        "blast": "integrity",
    },
    {
        "id": "agentbook",
        "title": "AgentBook (social & reputation)",
        "blurb": "Agent social feed, posts, votes, channels, reputation scoring backed by trading data.",
        "patterns": [r"^/api/v1/agentbook/"],
        "tools": ["submit_signal", "get_signal_history", "submit_observation", "submit_feedback"],
        "blast": "measurement",
    },
    {
        "id": "prediction_pools",
        "title": "Prediction pools & statistics",
        "blurb": "BTC pool state and history, prediction statistics, epoch mechanics.",
        "patterns": [r"^/api/v1/pool", r"^/api/v1/predictions"],
        "tools": ["get_btc_pool_state", "get_btc_pool_history", "get_prediction_statistics"],
        "blast": "integrity",
    },
    {
        "id": "swaps",
        "title": "Swaps & cross-chain",
        "blurb": "Multi-chain token swaps and bridges. The chain count is itself contested across sources.",
        "patterns": [r"^/api/v1/swap/", r"^/api/v1/defi/", r"^/api/v1/aerodrome/", r"^/api/v1/base-dex/"],
        "tools": [],
        "blast": "custody",
    },
    {
        "id": "launchpad",
        "title": "Robinhood Chain launchpad",
        "blurb": "Non-custodial token launches on chain 4663. Public MCP tools, returns unsigned transactions.",
        "patterns": [r"^/api/v1/launchpad"],
        "tools": ["launchpad_list_tokens", "launchpad_launch_token", "launchpad_trade_quote"],
        "blast": "custody",
    },
    {
        "id": "funds",
        "title": "Custom funds (AIB)",
        "blurb": "Agent-created index funds and the Tuatara fund. Redemption terms are contested between two pages.",
        "patterns": [r"^/api/v1/funds", r"^/api/v1/aib", r"^/api/v1/staking/"],
        "tools": ["create_aib_fund", "list_my_aib_funds", "edit_aib_fund_basket"],
        "blast": "custody",
    },
    {
        "id": "prop_desk",
        "title": "Prop desk",
        "blurb": "Funded trading accounts, $10K-$200K tiers, profit-split payouts.",
        "patterns": [r"^/api/v1/prop/"],
        "tools": [],
        "blast": "custody",
    },
    {
        "id": "ontology",
        "title": "Tuatara vectors & ontology",
        "blurb": "The proprietary asset-relationship engine and its machine-readable ontology.",
        "patterns": [r"^/api/v1/ontology", r"^/api/v1/tuatara/"],
        "tools": ["list_ontology_dimensions", "browse_ontology", "resolve_ontology_concept",
                  "search_ontology", "find_trade_path", "get_strategy_returns", "query_knowledge"],
        "blast": "measurement",
    },
    {
        "id": "backtest",
        "title": "Backtest engine",
        "blurb": "30-day strategy backtests. Where pro-forma history and live measured history can be conflated.",
        "patterns": [r"^/api/v1/backtest"],
        "tools": [],
        "blast": "measurement",
    },
    {
        "id": "support",
        "title": "Support & A2A agents",
        "blurb": "The AI support agent, the QA agent endpoint, and A2A messaging. Our own reporting channel.",
        "patterns": [r"^/api/v1/support/", r"^/api/v1/bounty/", r"^/api/v1/a2a/", r"^/api/v1/agent/"],
        "tools": ["ask_nexus_deep", "get_deep_answer", "request_feature"],
        "blast": "measurement",
    },
    {
        "id": "movers",
        "title": "Movers Tournament",
        "blurb": "A free, scored stock-picking competition over their own universe. No prizes, no money moves. Read 2026-09-13, alongside their new memecoin surfaces.",
        "patterns": [r"^/api/v1/universe/movers"],
        "tools": [],
        "blast": "measurement",
    },
    {
        "id": "clones",
        "title": "Public clone tools",
        "blurb": "FOMO Radar, Memecoin Terminal, Social Pulse, Protocol Revenue, Stable Pools -- built from /duplicate requests, keyless, each with its own /docs contract. Documented 2026-09-13 after we reported that four of them answered live and appeared nowhere in /api-docs.",
        "patterns": [r"^/api/v1/clones/"],
        "tools": [],
        "blast": "measurement",
    },
    {
        "id": "creator",
        "title": "Creator dashboard",
        "blurb": "Tracked links, post-kit, reward ledger and the Reddit/X lead queues behind cymetica.com/<username>. Added to openapi-public.json and llms.txt 2026-09-23/24.",
        "patterns": [r"^/api/v1/creator-links", r"^/api/v1/creator/"],
        "tools": [],
        "blast": "measurement",
    },
    {
        "id": "head_to_head",
        "title": "Head-to-head paper matchups",
        "blurb": "Paper matchups between an agent's own bot or clone and another. GET /sides and /mine answer live; none of the three routes appears in either OpenAPI document or llms.txt.",
        "patterns": [r"^/api/v1/head-to-head"],
        "tools": [],
        "blast": "measurement",
    },
    {
        "id": "build_it_better",
        "title": "Build it Better",
        "blurb": "Name a financial app, say what it should do better, and their pipeline rebuilds it on EventTrader inside 24 hours. Six MCP tools and a public board. Their own first priority for outside QA (REPLY-0030, 2026-09-20); its REST routes are in mcp.json and in no OpenAPI document.",
        "patterns": [r"^/api/v1/build-it-better"],
        "tools": ["bb_search_rebuilt_apps", "bb_file_request", "bb_get_request",
                  "bb_accept_spec", "bb_request_change", "bb_post_verdict"],
        "blast": "measurement",
    },
    {
        "id": "provenance",
        "title": "AI-native provenance",
        "blurb": "Build stats, AI authorship proof, due-diligence scoring. The platform's central marketing claim.",
        "patterns": [r"^/api/v1/build-stats", r"^/api/v1/ai-due-diligence", r"^/api/v1/features"],
        "tools": ["get_ai_native_proof", "get_platform_status"],
        "blast": "measurement",
    },
    {
        "id": "deadcoin",
        "title": "Dead coin desk",
        "blurb": "Quotes and desk info for illiquid tokens.",
        "patterns": [r"^/api/v1/deadcoin"],
        "tools": ["get_deadcoin_quote", "get_deadcoin_desk_info"],
        "blast": "measurement",
    },
    {
        "id": "realtime",
        "title": "WebSocket & webhooks",
        "blurb": "Real-time feeds declared in AsyncAPI 3.0, plus webhook registration and price subscriptions.",
        "patterns": [r"^/ws/"],
        "tools": ["register_webhook", "subscribe_prices"],
        "blast": "measurement",
    },
]

FALLBACK = {"id": "unmapped", "title": "Unmapped surface",
            "blurb": "Documented endpoints that fit no section yet.",
            "patterns": [], "tools": [], "blast": "measurement"}


# ---------------------------------------------------------------------------
# What a status code actually means about a documented endpoint.
#
# Counting only 2xx as "working" is wrong in both directions: a 401 on an
# account endpoint is the gate doing its job, and a 404 on an endpoint the
# platform's own llms.txt documents is a real defect. The percentage is only
# useful if it separates the two.
# ---------------------------------------------------------------------------
VERDICT_LABELS = {
    "ok": "responds",
    "auth": "exists, correctly requires auth",
    "param": "exists, needs parameters",
    "method": "exists, but documented with the wrong HTTP method",
    "missing": "documented but returns 404",
    "server_error": "5xx",
    "unreachable": "no response",
    "unprobed": "needs a path parameter",
    "websocket": "WebSocket -- not probeable by GET",
}
HEALTHY = {"ok", "auth", "param"}


def verdict(entry: dict) -> str:
    if entry["path"].startswith("/ws/"):
        return "websocket"
    if entry.get("probe") != "done":
        return "unprobed"

    codes = [entry.get(f"status_{k}") for k in ("anon", "trusted")]
    codes = [c for c in codes if c is not None]
    if not codes:
        return "unreachable"
    # Best observed across identities: an endpoint that answers TRUSTED is
    # working even when it refuses anonymous.
    if any(200 <= c < 300 for c in codes):
        return "ok"
    if any(c in (400, 422) for c in codes):
        return "param"
    if any(c in (401, 403) for c in codes):
        return "auth"
    if any(c == 405 for c in codes):
        return "method"
    if any(c == 404 for c in codes):
        return "missing"
    if any(c >= 500 for c in codes):
        return "server_error"
    return "unreachable"


def classify(path: str) -> str:
    for section in SECTIONS:
        for pattern in section["patterns"]:
            if re.search(pattern, path):
                return section["id"]
    return FALLBACK["id"]


def classify_tool(name: str) -> str:
    for section in SECTIONS:
        if name in section["tools"]:
            return section["id"]
    return FALLBACK["id"]


# ---------------------------------------------------------------------------
def gather_documented(rest) -> dict[str, dict]:
    """Every REST path the platform documents, and where it says so."""
    documented: dict[str, dict] = {}

    def note(path: str, source: str, methods: list[str] | None = None):
        path = path.split("?")[0].rstrip("/") or "/"
        entry = documented.setdefault(
            path, {"path": path, "sources": [], "methods": set()}
        )
        if source not in entry["sources"]:
            entry["sources"].append(source)
        entry["methods"].update(m.upper() for m in (methods or ["GET"]))

    # 1. OpenAPI
    try:
        spec = rest.get("/openapi.json").json()
        for path, ops in spec.get("paths", {}).items():
            note(path, "openapi.json", [m for m in ops if m.upper() in
                                        ("GET", "POST", "PUT", "PATCH", "DELETE")])
    except Exception as exc:  # noqa: BLE001
        print(f"  ! openapi.json: {exc}")

    # 2. llms.txt -- every /api/v1 or /mcp path it mentions
    try:
        text = rest.get("/llms.txt").text
        for match in re.finditer(r"\((?:GET|POST|PUT|DELETE)?\s*(/(?:api|mcp|ws)/[^\s)]+)\)", text):
            note(match.group(1), "llms.txt")
        for match in re.finditer(r"\b(?:GET|POST|PUT|DELETE)\s+(/(?:api|mcp|ws)/[^\s`)\]]+)", text):
            note(match.group(1), "llms.txt")
    except Exception as exc:  # noqa: BLE001
        print(f"  ! llms.txt: {exc}")

    # 3. agent-skills.json
    try:
        for skill in rest.get("/.well-known/agent-skills.json").json().get("skills", []):
            endpoint = skill.get("endpoint") or ""
            match = re.search(r"(/[^\s]+)", endpoint)
            if match:
                note(match.group(1), "agent-skills.json",
                     [endpoint.split()[0]] if " " in endpoint else ["GET"])
    except Exception as exc:  # noqa: BLE001
        print(f"  ! agent-skills.json: {exc}")

    # 4. udc.json discovery index
    try:
        blob = json.dumps(rest.get("/.well-known/udc.json").json())
        for match in re.finditer(r"https://cymetica\.com(/[^\"\\ ]+)", blob):
            note(match.group(1), "udc.json")
    except Exception as exc:  # noqa: BLE001
        print(f"  ! udc.json: {exc}")

    for entry in documented.values():
        entry["methods"] = sorted(entry["methods"])
    return documented


def probe(rest_anon, rest_trusted, documented: dict[str, dict]) -> None:
    """Read-only reachability. GET only, no placeholders, no side effects."""
    total = len(documented)
    for i, (path, entry) in enumerate(sorted(documented.items()), 1):
        if "{" in path or "GET" not in entry["methods"]:
            entry["probe"] = "skipped"
            entry["reason"] = "needs a parameter" if "{" in path else "no documented GET"
            continue
        print(f"  [{i:>3}/{total}] {path}", flush=True)
        for label, client in (("anon", rest_anon), ("trusted", rest_trusted)):
            if client is None:
                continue
            try:
                response = client.get(path)
                entry[f"status_{label}"] = response.status_code
                entry[f"bytes_{label}"] = len(response.content)
            except Exception as exc:  # noqa: BLE001
                entry[f"status_{label}"] = 0
                entry[f"error_{label}"] = f"{type(exc).__name__}"
        entry["probe"] = "done"


def gather_tools(rest, mcp_anon, mcp_trusted) -> dict:
    declared, served_anon, served_trusted = {}, set(), set()
    try:
        for tool in rest.get("/.well-known/mcp.json").json().get("tools", []):
            declared[tool["name"]] = tool.get("trust_tier", "unknown")
    except Exception as exc:  # noqa: BLE001
        print(f"  ! mcp.json tools: {exc}")
    for label, client in (("anon", mcp_anon), ("trusted", mcp_trusted)):
        if client is None:
            continue
        try:
            names = client.tool_names()
            (served_anon if label == "anon" else served_trusted).update(names)
        except Exception as exc:  # noqa: BLE001
            print(f"  ! tools/list {label}: {exc}")
    return {
        "declared": declared,
        "served_anon": sorted(served_anon),
        "served_trusted": sorted(served_trusted),
    }


def build() -> dict:
    registry = EndpointRegistry.load()
    ids = identities()
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        rest_anon = build_client(ids["anon"], registry)
        rest_trusted = build_client(ids["trusted"], registry) if ids["trusted"].present else None
        mcp_anon = build_mcp_client(ids["anon"], registry)
        mcp_trusted = build_mcp_client(ids["trusted"], registry) if ids["trusted"].present else None

        print("Gathering documented endpoints...")
        documented = gather_documented(rest_anon)
        print(f"  {len(documented)} distinct paths documented")

        print("Gathering MCP tool surface...")
        tools = gather_tools(rest_anon, mcp_anon, mcp_trusted)
        print(f"  declared={len(tools['declared'])} "
              f"anon={len(tools['served_anon'])} trusted={len(tools['served_trusted'])}")

        print("Probing reachability (read-only GET)...")
        probe(rest_anon, rest_trusted, documented)
    finally:
        CURRENT_TIER.reset(token)

    return assemble(documented, tools)


def assemble(documented: dict, tools: dict) -> dict:
    buckets: dict[str, dict] = defaultdict(
        lambda: {"endpoints": [], "tools_declared": [], "tools_anon": [], "tools_trusted": []}
    )

    for entry in documented.values():
        entry["section"] = classify(entry["path"])
        buckets[entry["section"]]["endpoints"].append(entry)

    for name, tier in tools["declared"].items():
        section = classify_tool(name)
        buckets[section]["tools_declared"].append({"name": name, "declared_tier": tier})
    for name in tools["served_anon"]:
        buckets[classify_tool(name)]["tools_anon"].append(name)
    for name in tools["served_trusted"]:
        buckets[classify_tool(name)]["tools_trusted"].append(name)

    # A section with nothing documented and no tools got no bucket at all --
    # `buckets` is a defaultdict populated only by appending to it -- so it
    # silently vanished from the page rather than showing zero. That is
    # exactly the state of a surface Cymetica has not documented anywhere but
    # that we track anyway (the Movers Tournament, registered in
    # components.yaml since 2026-09-13): the section a reader most needs to
    # see is the one this used to make disappear. FALLBACK is exempt --
    # "everything we could not classify" is only worth a row once something
    # actually lands there.
    EMPTY_BUCKET = {"endpoints": [], "tools_declared": [], "tools_anon": [],
                    "tools_trusted": []}
    sections = []
    for meta in SECTIONS + [FALLBACK]:
        bucket = buckets.get(meta["id"])
        if not bucket:
            if meta is FALLBACK:
                continue
            bucket = EMPTY_BUCKET
        endpoints = bucket["endpoints"]
        for entry in endpoints:
            entry["verdict"] = verdict(entry)
        # 'method' is excluded from the denominator, not counted as a failure.
        # A 405 means we sent the wrong verb: we learned the endpoint exists and
        # nothing about whether it works. Scoring it 0% would report our own bad
        # probe as their broken section. It still raises a documentation finding.
        # `unreachable` joins the excluded: it means neither identity got any
        # status back at all -- a timeout or a DNS failure on OUR side -- and
        # scoring it against them turns a hiccup on this machine into a
        # platform regression on the page. Same principle as rule 8 one layer
        # over: a read that failed is not a measurement. `method` is excluded
        # for the same reason, and `server_error` and `missing` are not: a 5xx
        # and a 404 are answers, and they are theirs.
        probed = [e for e in endpoints
                  if e["verdict"] not in ("unprobed", "websocket", "method",
                                          "unreachable")]
        healthy = [e for e in probed if e["verdict"] in HEALTHY]
        pct = round(100 * len(healthy) / len(probed)) if probed else None

        tally: dict[str, int] = defaultdict(int)
        for entry in endpoints:
            tally[entry["verdict"]] += 1

        sections.append({
            **{k: meta[k] for k in ("id", "title", "blurb", "blast")},
            # The denominator, named and carried with the number it produced.
            # Without it, a percentage computed over 17 documented paths and
            # one computed over 9 look identical on the dashboard -- which is
            # how eight sections went green when 27 paths left the
            # documentation and nothing was fixed.
            "population": {
                "documented": len(endpoints),
                "probed": len(probed),
                "paths": sorted(e["path"] for e in endpoints),
            },
            "endpoints_documented": len(endpoints),
            "endpoints_probed": len(probed),
            "endpoints_reachable": len(healthy),
            "endpoints_unprobeable": len(endpoints) - len(probed),
            "verdicts": dict(tally),
            "reachable_pct": pct,
            "tools_declared": len(bucket["tools_declared"]),
            "tools_anon": len(bucket["tools_anon"]),
            "tools_trusted": len(bucket["tools_trusted"]),
            "endpoint_detail": sorted(endpoints, key=lambda e: e["path"]),
            "tool_detail": sorted(bucket["tools_declared"], key=lambda t: t["name"]),
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "totals": {
            "paths_documented": len(documented),
            "tools_declared": len(tools["declared"]),
            "tools_served_anon": len(tools["served_anon"]),
            "tools_served_trusted": len(tools["served_trusted"]),
        },
        "tools": tools,
        "sections": sections,
    }


def _by_path(inventory: dict) -> dict[str, dict]:
    return {
        entry["path"]: entry
        for section in inventory.get("sections", [])
        for entry in section.get("endpoint_detail", [])
    }


def compare(before: dict, after: dict) -> dict[str, list[str]]:
    """What actually changed between two inventories. Pure; no I/O, no clock.

    The distinction this exists to force: a documented path that 404s can stop
    being a finding in two completely different ways, and only one of them is
    a fix.

        fixed_in_place      still documented, and now reachable
        still_missing       still documented, still 404
        removed_from_docs   no longer documented at all
        added               newly documented since the pin

    Between the two committed captures, `fixed_in_place` is empty and all 26
    of the missing paths are in `removed_from_docs`. Reachability was computed
    over whatever the vendor documented at that moment, so the denominator
    shrank from 141 to 114, eight sections turned green, and a finding about
    404s read as verified.
    """
    old, new = _by_path(before), _by_path(after)
    healthy = set(HEALTHY)

    fixed, still, removed = [], [], []
    for path, entry in old.items():
        if entry.get("verdict") != "missing":
            continue
        current = new.get(path)
        if current is None:
            removed.append(path)
        elif current.get("verdict") in healthy:
            fixed.append(path)
        else:
            still.append(path)

    return {
        "fixed_in_place": sorted(fixed),
        "still_missing": sorted(still),
        "removed_from_docs": sorted(removed),
        "added": sorted(set(new) - set(old)),
    }


if __name__ == "__main__":
    inventory = build()
    out = out_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(inventory, indent=2, ensure_ascii=False), encoding="utf-8")
    try:
        shown = out.relative_to(REPO_ROOT)
    except ValueError:
        # Under an override the target is outside the repository, and
        # relative_to raises rather than returning something useful.
        shown = out
    print(f"\n-> {shown}")
    for section in inventory["sections"]:
        pct = section["reachable_pct"]
        print(f"  {section['title']:<34} "
              f"{section['endpoints_documented']:>3} paths  "
              f"{section['tools_declared']:>2} tools  "
              f"{(str(pct) + '%') if pct is not None else '  -':>5} reachable")

"""The Gem Screener's MCP tools say what its REST routes say.

An agent reads the screener through `gem_screener_picks`, `gem_screener_ranked` and
`gem_screener_coin`. Same snapshot, so the same picks and figures, compared only
within one `as_of`: a refresh between two reads is not a disagreement.

NOT asserted: the fields of an answer, or that the figures are right (the REST
checks hold those). SAFE: read-only tools, anonymous.
"""

from __future__ import annotations

import json

from qa import gemaudit as g
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude


def _tool(mcp, name: str, arguments: dict) -> dict:
    response = mcp.rpc("tools/call", {"name": name, "arguments": arguments})
    if response.status_code != 200:
        raise Inconclusive(f"{name} answered HTTP {response.status_code}")
    result = (response.json() or {}).get("result") or {}
    if result.get("structuredContent"):
        return result["structuredContent"]
    for part in result.get("content") or []:
        if part.get("type") == "text":
            try:
                body = json.loads(part["text"])
            except ValueError:
                break
            return body.get("result", body) if isinstance(body, dict) else {}
    raise Inconclusive(f"{name} answered no JSON")


def _value(field) -> object:
    return field.get("value") if isinstance(field, dict) else field


@qa(component="mcp.tools_call", tier=SafetyTier.SAFE, surface="mcp")
def test_the_gem_screener_tools_say_what_its_routes_say(mcp_anon, rest_anon):
    """The picks, their order and upside; the ranked total; one coin's figures."""
    tool = _tool(mcp_anon, "gem_screener_picks", {})
    rest = rest_anon.get(g.PICKS).json()
    if tool.get("as_of") != rest.get("as_of"):
        raise Inconclusive(f"a refresh between the reads: {tool.get('as_of')} and {rest.get('as_of')}")
    breaches = []
    said = [(p.get("slug"), _value(p.get("upside"))) for p in tool.get("picks") or []]
    want = [(p.get("slug"), _value(p.get("upside"))) for p in rest.get("picks") or []]
    if said != want:
        breaches.append({"what": f"picks: tool {said}, route {want}"})

    ranked = _tool(mcp_anon, "gem_screener_ranked", {"limit": 5})
    route = rest_anon.get("/api/v1/gem-screener/ranked?limit=5").json()
    if ranked.get("total") != route.get("total"):
        breaches.append({"what": f"ranked total: tool {ranked.get('total')}, route {route.get('total')}"})

    slug = want[0][0] if want else None
    if slug:
        coin_tool = _tool(mcp_anon, "gem_screener_coin", {"symbol": slug})
        coin_rest = rest_anon.get(g.COIN.format(symbol=slug)).json()
        for field in ("market_cap", "revenue_30d", "upside", "price_vs_revenue"):
            if _value(coin_tool.get(field)) != _value(coin_rest.get(field)):
                breaches.append({"what": f"{slug}.{field}: tool {_value(coin_tool.get(field))}, route {_value(coin_rest.get(field))}"})
    conclude(Measurement(
        verdict="failed" if breaches else "passed",
        reason="; ".join(b["what"] for b in breaches) if breaches else f"{len(want)} picks, the total and {slug}'s figures agree",
        left={"breaches": len(breaches)}, right={"breaches": 0},
        population={"breaches": breaches, "as_of": rest.get("as_of")},
        sources={"tool": "gem_screener_picks", "route": g.PICKS}))

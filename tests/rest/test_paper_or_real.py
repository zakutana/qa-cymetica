"""Whether an order spends real money, and whether an agent can find that out.

/build invites autonomous agents to trade over plain HTTP. The platform has two
books, paper and live, and the UI carries a badge and a switch. The API is the
subject here, and it resolves the question three different ways.

The event-card buy endpoint documents its own resolution order, verbatim from
openapi-public.json on 2026-09-08:

    1. ``body.paper`` (explicit per-trade override)
    2. ``user.simulation_mode`` (per-user setting)
    3. ``EVENT_CARDS_TRADING_ENABLED`` env (platform-wide gate)

Cloning a bot inherits the same setting -- "If None, inherits user's
simulation_mode". The exchange order endpoint does not: its `mode` field
defaults to `"live"`. The CLOB order endpoint has no such field at all.

And `simulation_mode`, the setting two of those resolve against, appears three
times in the specification and every one of them is prose inside a REQUEST
body. No documented response returns it. It is not in llms.txt.

So an agent can be told to omit the flag and inherit a setting it has no way to
read, on endpoints that inherit it differently. These checks read documents
only. Nothing here places an order, in either book.

Written after the author of these checks got it wrong in the obvious
direction -- reading an unauthenticated fetch of /aci-challenge, seeing "PAPER
TRADING MODE", and concluding the account was in paper when it was live with
real USDC in it. That mistake cost nothing because it was a read. The same
mistake inside a trading loop is the whole finding.
"""

from __future__ import annotations

import json

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

OPENAPI = "/openapi-public.json"
LLMS = "/llms.txt"

# Every documented way to place an order, and the field that decides the book.
ORDER_SCHEMAS = {
    "event-cards buy": ("BuyRequest", "paper"),
    "event-cards sell": ("SellRequest", "paper"),
    "event-cards short": ("ShortRequest", "paper"),
    "clone a bot": ("CloneBotRequest", "is_paper"),
    "exchange order": ("src__api__routes__exchange__PlaceOrderRequest", "mode"),
    "clob order": ("src__api__routes__clob__PlaceOrderRequest", None),
}


def _spec(client):
    response = client.get(OPENAPI)
    if response.status_code != 200:
        return None, f"{OPENAPI} answered HTTP {response.status_code}"
    try:
        return response.json(), None
    except ValueError:
        return None, f"{OPENAPI} did not answer JSON"


@qa(component="rest.event_cards", tier=SafetyTier.SAFE, surface="rest")
def test_the_setting_that_decides_whether_real_money_moves_is_readable(rest_trusted):
    """`user.simulation_mode` decides it, and nothing published returns it.

    Two order endpoints resolve to this setting when the caller omits the
    per-trade flag, and the specification names it in their own descriptions.
    An agent that omits the flag -- which the schema invites, the field being
    nullable with None documented as the inheriting case -- is therefore
    deciding between paper and real money by a value it cannot fetch.
    """
    spec, why = _spec(rest_trusted)
    if spec is None:
        conclude(Measurement(verdict="inconclusive", reason=why,
                             sources={"schema": OPENAPI}))
        return

    blob = json.dumps(spec)
    if "simulation_mode" not in blob:
        conclude(Measurement(
            verdict="inconclusive",
            reason="the specification no longer names simulation_mode, so the "
                   "resolution order this check was written against is gone; "
                   "read the buy endpoint's description before restoring it",
            sources={"schema": OPENAPI}))
        return

    # A response that publishes it would appear as a property name, not only
    # inside prose. Prose is where all three of today's occurrences live.
    readable = []
    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "properties" and isinstance(value, dict):
                    for prop in value:
                        if "simulation" in prop.lower():
                            readable.append(prop)
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
    walk(spec)

    conclude(Measurement(
        verdict="passed" if readable else "failed",
        reason=(f"the setting the order endpoints resolve against is published "
                f"as {sorted(set(readable))}"
                if readable else
                "user.simulation_mode decides whether an order spends real "
                "USDC when the per-trade flag is omitted, and no documented "
                "response publishes it: all three occurrences in the schema "
                "are prose inside request bodies, so an agent cannot read the "
                "setting it is about to inherit"),
        left=sorted(set(readable)), right=["a response field naming the mode"],
        population={"prose_mentions": blob.count("simulation_mode"),
                    "response_fields": len(set(readable))},
        sources={"schema": OPENAPI}))


@qa(component="rest.event_cards", tier=SafetyTier.SAFE, surface="rest")
def test_every_order_endpoint_decides_the_book_the_same_way(rest_trusted):
    """Four ways to place an order, four different answers to one question.

    Not a style complaint. The defaults DIVERGE: omit the field on an
    event-card trade or a bot clone and the account's setting decides; omit
    `mode` on an exchange order and it is `"live"`. An agent that has set
    itself to paper, and writes one helper that omits the optional field
    because omitting it worked on the first endpoint, places a real order on
    the second. The CLOB endpoint offers no control at all.
    """
    spec, why = _spec(rest_trusted)
    if spec is None:
        conclude(Measurement(verdict="inconclusive", reason=why,
                             sources={"schema": OPENAPI}))
        return

    schemas = (spec.get("components") or {}).get("schemas") or {}
    found = {}
    for label, (schema_name, field) in ORDER_SCHEMAS.items():
        schema = schemas.get(schema_name)
        if schema is None:
            continue
        props = schema.get("properties") or {}
        named = [p for p in props
                 if p in ("paper", "is_paper", "mode") or "paper" in p.lower()]
        default = (props.get(field) or {}).get("default") if field else None
        found[label] = {"field": named[0] if named else None, "default": default}

    if len(found) < 2:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"only {len(found)} of the {len(ORDER_SCHEMAS)} order "
                   f"schemas this check knows are still in the specification",
            sources={"schema": OPENAPI}))
        return

    fields = {v["field"] for v in found.values()}
    defaults = {str(v["default"]) for v in found.values()}
    missing = sorted(k for k, v in found.items() if v["field"] is None)
    consistent = len(fields) == 1 and len(defaults) == 1

    conclude(Measurement(
        verdict="passed" if consistent else "failed",
        reason=(f"every order endpoint decides the book through the same field "
                f"and the same default: {fields}"
                if consistent else
                f"the order endpoints name the paper/live control "
                f"{len(fields)} different ways ({', '.join(sorted(str(f) for f in fields))}) "
                f"and disagree on what omitting it means "
                f"({', '.join(sorted(defaults))})"
                + (f"; {', '.join(missing)} offers no control at all"
                   if missing else "")),
        left=sorted(f"{k}: {v['field']} default={v['default']}"
                    for k, v in found.items()),
        right=["one field, one default, on every order endpoint"],
        population={"endpoints": len(found), "distinct_fields": len(fields),
                    "distinct_defaults": len(defaults)},
        sources={"schema": OPENAPI}))

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
import re

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

# The one name every order surface agreed on, 2026-09-08. `is_paper` survives
# on the clone request as an alias; `paper` is the canonical one and is what a
# caller writing a single helper will reach for.
CONTROL = "paper"

# A surface admitting, in its own schema, that the control does not decide.
#
# This replaced a clause that asked whether the description SAID what omitting
# the field does. That was asking for a vocabulary: it failed the event-card
# endpoints, whose text settles the case perfectly well in other words ("None
# (default) → use user.simulation_mode if set"), and it failed SellRequest for
# the crime of pointing at BuyRequest instead of repeating it. Two false
# failures in one check, on the same day I twice reported a vendor's fix as a
# defect by demanding my own phrasing back.
#
# What is worth failing on is the opposite and much sharper: a surface that
# takes `paper` and then says it will not always be obeyed. ShortRequest says
# exactly that -- "honoured only on the spot-bear fallback (cards without an
# EVCDX token); perps are always real-ledger" -- so a caller who explicitly
# asks for paper can be given a real-ledger position. An ignored explicit
# instruction is worse than an undocumented default, because the caller did
# everything right.
NOT_HONOURED = re.compile(
    r"honou?red only|only honou?red|ignored|not honou?red|has no effect"
    r"|always real|always live|regardless of", re.I)


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

    # Over RESPONSES only. The first version walked every `properties` dict in
    # the document, request bodies included -- so a settings endpoint that
    # merely ACCEPTS simulation_mode would have turned this green under the
    # sentence "no documented response publishes it". Today it is right for the
    # right reason (PortfolioSummaryResponse carries the field), which is
    # exactly the kind of latent hole a green check hides. Deep pass,
    # 2026-09-08, 2/3.
    schemas = (spec.get("components") or {}).get("schemas") or {}

    def properties_of(node, seen=None, depth=0):
        """Property names reachable from a schema node, following $ref.

        Depth-limited rather than cycle-detected: a $ref cycle is caught by
        `seen`, but an inline schema nested through enough properties is not,
        and this walk over the real document hit Python's recursion limit. Six
        is past every response shape this API publishes and cannot run away.
        """
        seen = seen if seen is not None else set()
        if not isinstance(node, dict) or depth > 6:
            return
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            name = ref.rsplit("/", 1)[-1]
            if name not in seen:
                seen.add(name)
                yield from properties_of(schemas.get(name) or {}, seen, depth + 1)
            return
        properties = node.get("properties") or {}
        for prop in properties:
            yield prop
        for nested in properties.values():
            yield from properties_of(nested, seen, depth + 1)
        for key in ("items", "additionalProperties"):
            yield from properties_of(node.get(key) or {}, seen, depth + 1)
        for combinator in ("allOf", "anyOf", "oneOf"):
            for member in node.get(combinator) or []:
                yield from properties_of(member, seen, depth + 1)

    readable = []
    for operations in (spec.get("paths") or {}).values():
        if not isinstance(operations, dict):
            continue
        for operation in operations.values():
            if not isinstance(operation, dict):
                continue
            for response in (operation.get("responses") or {}).values():
                for media in ((response or {}).get("content") or {}).values():
                    for prop in properties_of((media or {}).get("schema") or {}):
                        if "simulation" in prop.lower():
                            readable.append(prop)

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
    """One control on every order surface, and omission never spends by surprise.

    The first version of this demanded one field AND one default. That was the
    shape of our own request, not of the contract, and Cymetica's fix on
    2026-09-08 showed the difference: they gave every surface the same field,
    `paper`, and kept the defaults deliberately unlike each other, because the
    surfaces are unlike each other. The CLOB has no paper book, so it cannot
    default to paper; it refuses instead. Demanding identical defaults would
    have been demanding something wrong, and would have reported their fix as
    the defect it closed -- the same over-reach #76 taught us this morning.

    So the check now holds the two things that actually protect a caller:

      * every order surface names the control the same way, so one helper can
        set it everywhere.

    That is ONE property, and the docstring used to promise two. The second --
    "no surface lets omission spend real money" -- was never measured here:
    `not_honoured` was computed beside it and read by nothing, so once every
    surface carried `paper` the check went green whatever the defaults did.
    Deep pass, 2026-09-08, 3/3.

    The second property is not asserted anywhere now, and that is deliberate
    rather than an oversight. Measuring it means matching English in a field
    description for a statement about omission, and this file's own comment
    records two false failures in one day from exactly that -- a regex that
    rejected "None (default) → use simulation_mode" for not saying "omitted",
    and one that failed a schema for pointing at its sibling instead of
    repeating it. What a caller is actually protected by is `paper` being
    present and honoured, and those two are asserted, here and in the sibling
    below. A docstring promising a third thing over an assertion that measures
    two is how a check starts lying.
    """
    spec, why = _spec(rest_trusted)
    if spec is None:
        conclude(Measurement(verdict="inconclusive", reason=why,
                             sources={"schema": OPENAPI}))
        return

    schemas = (spec.get("components") or {}).get("schemas") or {}
    found = {}
    for label, (schema_name, _) in ORDER_SCHEMAS.items():
        schema = schemas.get(schema_name)
        if schema is None:
            continue
        props = schema.get("properties") or {}
        described = (props.get(CONTROL) or {}).get("description") or ""
        found[label] = {"has_control": CONTROL in props,
                        "not_honoured": bool(NOT_HONOURED.search(described)),
                        "description": described}

    if len(found) < 2:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"only {len(found)} of the {len(ORDER_SCHEMAS)} order "
                   f"schemas this check knows are still in the specification",
            sources={"schema": OPENAPI}))
        return

    nameless = sorted(k for k, v in found.items() if not v["has_control"])

    conclude(Measurement(
        verdict="passed" if not nameless else "failed",
        reason=(f"all {len(found)} order surfaces take the same control, "
                f"`{CONTROL}`, so one helper can state the book everywhere"
                if not nameless else
                f"{', '.join(nameless)} take no `{CONTROL}` field, so a caller "
                f"cannot state which book the order belongs in"),
        left=sorted(nameless), right=[],
        population={"endpoints": len(found),
                    "without_the_control": len(nameless)},
        sources={"schema": OPENAPI}))


@qa(component="rest.event_cards", tier=SafetyTier.SAFE, surface="rest")
def test_an_explicit_paper_request_is_honoured_on_every_surface(rest_trusted):
    """A caller that says `paper: true` is not given a real-ledger position.

    Separate from the check above on purpose, and filed separately, because it
    is a different defect: that one asks whether a caller CAN state the book,
    and Cymetica closed it on 2026-09-08 by putting `paper` on all four
    surfaces. This asks whether stating it is enough, and the same fix
    documented the case where it is not.

    ShortRequest, in their own schema: "Per-trade paper override — honoured
    only on the spot-bear fallback (cards without an EVCDX token); perps are
    always real-ledger". So a short on a card that has an EVCDX token opens a
    real position while the request said paper.

    An ignored explicit instruction is worse than an undocumented default. The
    caller did everything right, has no way to know which cards carry an EVCDX
    token before ordering, and the one thing it asked for -- that no real money
    move -- is the thing that is not honoured.

    Read from the schema, not by shorting anything.
    """
    spec, why = _spec(rest_trusted)
    if spec is None:
        conclude(Measurement(verdict="inconclusive", reason=why,
                             sources={"schema": OPENAPI}))
        return

    schemas = (spec.get("components") or {}).get("schemas") or {}
    # A schema that is not there is not a schema that says nothing. The first
    # version coalesced a missing one to {} -> "" -> no match, so renaming
    # ShortRequest -- and two of these six keys are already FastAPI
    # path-mangled, so a module move renames them for free -- would have
    # printed "a caller that asks for paper is given paper" over zero surfaces
    # read, while population still reported six. The sibling above has this
    # gate; this one did not. Deep pass, 2026-09-08, 3/3.
    missing = sorted(label for label, (name, _) in ORDER_SCHEMAS.items()
                     if schemas.get(name) is None)
    if missing:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"{', '.join(missing)} are not in the specification under "
                   f"the names this check knows, so whether `{CONTROL}` is "
                   f"honoured there could not be read",
            left=missing, right=sorted(ORDER_SCHEMAS),
            population={"surfaces_expected": len(ORDER_SCHEMAS),
                        "surfaces_read": len(ORDER_SCHEMAS) - len(missing)},
            sources={"schema": OPENAPI}))
        return

    ignored = {}
    for label, (schema_name, _) in ORDER_SCHEMAS.items():
        props = (schemas.get(schema_name) or {}).get("properties") or {}
        described = (props.get(CONTROL) or {}).get("description") or ""
        if NOT_HONOURED.search(described):
            ignored[label] = " ".join(described.split())

    conclude(Measurement(
        verdict="passed" if not ignored else "failed",
        reason=(f"no order surface says `{CONTROL}` may be disobeyed, so a "
                f"caller that asks for paper is given paper"
                if not ignored else
                f"{', '.join(sorted(ignored))} take `{CONTROL}` and then say it "
                f"is not always honoured, so a caller that explicitly asks for "
                f"paper can be given a real-ledger position — "
                f"{list(ignored.values())[0][:200]}"),
        left=sorted(ignored), right=[],
        population={"surfaces_checked": len(ORDER_SCHEMAS) - len(missing),
                    "not_always_honoured": len(ignored)},
        sources={"schema": OPENAPI}))

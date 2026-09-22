"""Mechanical safety enforcement.

The single rule this module exists to make true:

    A test cannot send a request its declared tier does not permit,
    even if the test is wrong.

Enforcement is in the transport, below every helper and every fixture, so a
buggy test, a copy-pasted probe body, or a helper that builds its own payload
all hit the same wall. Four independent layers guard the network:

    1. httpx client construction is banned outside our fixtures (client.py)
    2. a request made with NO tier in scope is refused outright -- there is no
       default, so code that forgot to declare what it may do does nothing
    3. this transport checks the tier of the currently-running test
    4. executable parameters are declared per endpoint in components.yaml,
       never inferred, and a probe_only endpoint may never be executed

Defeating one still leaves three. tests/meta/ proves all four block, runs
first, and aborts the session on failure -- so if the guard is broken, zero
live requests are issued. The configure-time self-check in
qa/client.py::assert_client_guard_blocks feels each of the four coming off
before a single test is collected, and names them by these numbers.

(This said "Three" and listed three until 2026-09-07, while client.py had
tested four since the self-check was added. The missing one is layer 2, which
is the one a narrow selector would otherwise leave unproven.)
"""

from __future__ import annotations

import json
import re
from contextvars import ContextVar
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import httpx
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
COMPONENTS_YAML = REPO_ROOT / "components.yaml"


class SafetyViolation(RuntimeError):
    """Raised BEFORE a request reaches the network. Never caught internally."""


class SafetyTier(str, Enum):
    """Ordered. A test declares the most it is allowed to do, not what it does."""

    SAFE = "SAFE"      # read-only: GET/HEAD/OPTIONS + allowlisted read RPC
    PROBE = "PROBE"    # boundary probe with a provably inert body
    MUTATE = "MUTATE"  # creates real state; triple-gated, off by default

    @property
    def rank(self) -> int:
        return {"SAFE": 0, "PROBE": 1, "MUTATE": 2}[self.value]


READ_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

# Bodies that cannot possibly execute anything, whatever the endpoint.
INERT_BODIES = frozenset({b"", b"{}", b'{"__qa_probe__":true}'})

# The tier of the test currently executing. Set by an autouse fixture, read by
# the transport. A ContextVar rather than an argument so there is no call path
# that can forget to pass it, and no helper that can spoof it.
CURRENT_TIER: ContextVar[SafetyTier | None] = ContextVar("qa_tier", default=None)
CURRENT_NODEID: ContextVar[str | None] = ContextVar("qa_nodeid", default=None)


@dataclass(frozen=True)
class EndpointRule:
    id: str
    path: str
    methods: frozenset[str]
    component: str
    executable_params: frozenset[str] = frozenset()
    inert_params: frozenset[str] = frozenset()
    # Must be PRESENT and TRUE on a MUTATE body, or the request is
    # refused. Distinct from inert_params, which says which keys are
    # harmless in a probe -- five declared, three sent, and requiring
    # all of them would have broken the a2a writer.
    required_flags: frozenset[str] = frozenset()
    probe_only: bool = False
    readonly_rpc: bool = False
    forbidden_always: bool = False
    _regex: re.Pattern[str] | None = field(default=None, compare=False)

    @property
    def specificity(self) -> int:
        """Literal (non-placeholder) segments. Longest literal match wins."""
        return sum(1 for seg in self.path.strip("/").split("/") if "{" not in seg)


def _path_regex(path: str) -> re.Pattern[str]:
    parts = []
    for seg in path.strip("/").split("/"):
        parts.append(r"[^/]+" if seg.startswith("{") and seg.endswith("}") else re.escape(seg))
    return re.compile(r"^/" + "/".join(parts) + r"/?$")


class EndpointRegistry:
    """Endpoint rules plus MCP tool classification, loaded from components.yaml."""

    def __init__(self, raw: dict[str, Any]):
        self.raw = raw
        self.rules: list[EndpointRule] = []
        for e in raw.get("endpoints", []):
            self.rules.append(
                EndpointRule(
                    id=e["id"],
                    path=e["path"],
                    methods=frozenset(m.upper() for m in e.get("methods", ["GET"])),
                    component=e["component"],
                    executable_params=frozenset(e.get("executable_params", [])),
                    inert_params=frozenset(e.get("inert_params", [])),
                    required_flags=frozenset(e.get("required_flags", [])),
                    probe_only=bool(e.get("probe_only", False)),
                    readonly_rpc=bool(e.get("readonly_rpc", False)),
                    forbidden_always=bool(e.get("forbidden_always", False)),
                    _regex=_path_regex(e["path"]),
                )
            )
        tools = raw.get("mcp_tools", {})
        self.tools_read = frozenset(tools.get("read", []))
        self.tools_contribute = frozenset(tools.get("contribute", []))
        self.tools_trade = frozenset(tools.get("trade", []))
        self.tools_provision = frozenset(tools.get("provision", []))
        # tool name -> what must be in the arguments before it may be executed:
        # a flag name that must be `True` itself, or {argument: value} that must
        # match exactly (place_arena_order's `mode: paper`). The tool-side twin
        # of EndpointRule.required_flags.
        self.tools_paper_gated: dict[str, str | dict] = dict(tools.get("paper_gated", {}))
        self.components = raw.get("components", {})
        self.mutate_enabled = False
        self.mutate_allowed_hosts: frozenset[str] = frozenset()

    @classmethod
    def load(cls, path: Path | None = None) -> EndpointRegistry:
        with open(path or COMPONENTS_YAML, encoding="utf-8") as fh:
            return cls(yaml.safe_load(fh))

    def match(self, path: str, method: str) -> EndpointRule | None:
        best: EndpointRule | None = None
        for rule in self.rules:
            if rule._regex and rule._regex.match(path) and method.upper() in rule.methods:
                if best is None or rule.specificity > best.specificity:
                    best = rule
        return best

    def tool_class(self, name: str) -> str:
        if name in self.tools_read:
            return "read"
        if name in self.tools_contribute:
            return "contribute"
        if name in self.tools_trade:
            return "trade"
        if name in self.tools_provision:
            return "provision"
        return "unknown"


class SafetyTransport(httpx.BaseTransport):
    """Wraps a real transport. Every check happens before delegation."""

    def __init__(
        self,
        inner: httpx.BaseTransport,
        registry: EndpointRegistry,
        evidence=None,
        budget=None,
    ):
        self.inner = inner
        self.registry = registry
        self.evidence = evidence
        self.budget = budget

    # -- entry point ------------------------------------------------------
    def handle_request(self, request: httpx.Request) -> httpx.Response:
        tier = CURRENT_TIER.get()
        if tier is None:
            raise SafetyViolation(
                "No safety tier is in scope. Every live request must originate "
                "from a test decorated with @qa(component=..., tier=...). "
                "Module-level or fixture-time requests outside a test are denied."
            )

        path = request.url.path
        method = request.method.upper()
        rule = self.registry.match(path, method)

        self._check(request, tier, rule, path, method)

        if self.budget is not None:
            self.budget.before_request()

        response = self.inner.handle_request(request)

        if self.budget is not None:
            self.budget.after_response(response)
        if self.evidence is not None:
            self.evidence.capture(request, response, tier, rule.id if rule else None)
        return response

    # -- policy -----------------------------------------------------------
    def _check(self, request, tier, rule, path, method) -> None:
        if rule is not None and rule.forbidden_always:
            raise SafetyViolation(
                f"{method} {rule.id} is permanently denied at every tier."
            )

        # MCP JSON-RPC: safety is decided by the body, not the HTTP method.
        if rule is not None and rule.readonly_rpc:
            self._check_rpc(request, tier, rule)
            return

        if method in READ_METHODS:
            return  # read methods are permitted at every tier

        # Below here the request is a write by HTTP semantics.
        if rule is None:
            raise SafetyViolation(
                f"{method} {path} matches no rule in components.yaml. "
                f"Non-read methods are default-denied: declare the endpoint, "
                f"its executable_params, and whether it is probe_only, first."
            )

        if tier is SafetyTier.SAFE:
            raise SafetyViolation(
                f"SAFE test attempted {method} {rule.id}. "
                f"Raise the tier to PROBE and send an inert body, or to MUTATE."
            )

        if tier is SafetyTier.PROBE:
            self._assert_inert(request, rule)
            return

        # MUTATE
        if not self.registry.mutate_enabled:
            raise SafetyViolation(
                f"MUTATE test attempted {method} {rule.id} without --allow-mutate."
            )
        if rule.probe_only:
            raise SafetyViolation(
                f"{rule.id} is probe_only: reachability is testable, execution is "
                f"not. No MUTATE test may target it, even with --allow-mutate."
            )
        self._assert_declared_flags(request, rule)
        host = request.url.host
        if host not in self.registry.mutate_allowed_hosts:
            raise SafetyViolation(f"MUTATE against unlisted host {host!r}.")

    # -- JSON-RPC body classification -------------------------------------
    def _check_rpc(self, request, tier, rule) -> None:
        body = request.read()
        try:
            payload = json.loads(body or b"{}")
        except json.JSONDecodeError:
            # A deliberately malformed body is a legitimate protocol probe.
            if tier is SafetyTier.SAFE:
                raise SafetyViolation(
                    "SAFE test sent a non-JSON body to the MCP endpoint. "
                    "Malformed-input probes are PROBE tier."
                )
            return

        if not isinstance(payload, dict):
            if tier is SafetyTier.SAFE:
                raise SafetyViolation("SAFE test sent a non-object JSON-RPC body.")
            return

        rpc_method = payload.get("method")

        if rpc_method in (None, "tools/list", "resources/list", "prompts/list", "initialize"):
            return  # discovery methods are read-only at every tier

        if rpc_method != "tools/call":
            if tier is SafetyTier.SAFE:
                raise SafetyViolation(
                    f"SAFE test called unclassified JSON-RPC method {rpc_method!r}. "
                    f"Use PROBE tier for protocol exploration."
                )
            return

        params = payload.get("params") or {}
        tool = params.get("name")
        args = params.get("arguments") or {}
        klass = self.registry.tool_class(tool) if isinstance(tool, str) else "unknown"

        if klass == "read":
            return  # read tools are permitted at every tier

        if tier is SafetyTier.SAFE:
            raise SafetyViolation(
                f"SAFE test attempted MCP tool {tool!r} classified {klass!r}. "
                f"Only tools in mcp_tools.read are permitted at SAFE tier."
            )

        if tier is SafetyTier.PROBE:
            if args:
                raise SafetyViolation(
                    f"PROBE call to {klass} tool {tool!r} carries arguments "
                    f"{sorted(args)}. A probe of a non-read tool must send empty "
                    f"arguments: the finding is that the call was ACCEPTED, never "
                    f"that it ran."
                )
            return

        # MUTATE
        if not self.registry.mutate_enabled:
            raise SafetyViolation(
                f"MUTATE call to tool {tool!r} without --allow-mutate."
            )
        # A tool that publishes a flag which stops it spending is not the same
        # thing as one that cannot be stopped. Checked before the blanket
        # refusal, and only at MUTATE: paper is not free, since every call
        # costs a rate limit and leaves a position on their side.
        gate = self.registry.tools_paper_gated.get(str(tool))
        if gate:
            # The VALUE, not that something is there. `not args.get(gate)` let
            # a `paper` of "false" through -- truthy, and false to a server
            # that coerces strings -- and would have let place_arena_order's
            # `mode: 'live'` through the moment it was gated on `mode`.
            wanted = gate if isinstance(gate, dict) else {gate: True}
            # `is` for a bool, because 1 == True; `==` for a string.
            wrong = {k: v for k, v in wanted.items()
                     if not (args.get(k) is v if isinstance(v, bool)
                             else args.get(k) == v)}
            if wrong:
                said = ", ".join(f"{k}={v!r}" for k, v in wanted.items())
                raise SafetyViolation(
                    f"MCP tool {tool!r} moves money unless {said}, and this "
                    f"call does not carry it (got "
                    f"{ {k: args.get(k) for k in wanted} }). That argument is "
                    f"what says no real funds move; send it, or do not call "
                    f"the tool."
                )
            return

        if klass in ("trade", "provision"):
            raise SafetyViolation(
                f"MCP tool {tool!r} is classified {klass!r}: it moves money or "
                f"creates durable platform objects. The suite never executes it. "
                f"Generate an operator command instead."
            )

        # Default-deny, and it was missing at the only tier that can spend.
        # This branch raised for `trade` and `provision` and then fell off the
        # end of the function, so a tool in none of components.yaml's lists was
        # PERMITTED at MUTATE with full arguments -- while SAFE refuses it by
        # name and PROBE forces empty arguments. Found 2026-09-10 by the code
        # review and independently by an auditor; three triage readers each
        # reached the transport with a tool that does not exist.
        #
        # It is the ordinary case after any of their releases: 62 tools today
        # and a changed one this morning. `trade_event_card` is itself in no
        # list -- reachable only through mcp_tools.paper_gated -- so removing
        # that gate would have turned it from refused into permitted, which is
        # the opposite of what removing a gate should do.
        if klass != "read":
            raise SafetyViolation(
                f"MCP tool {tool!r} is unclassified: components.yaml puts it in "
                f"no mcp_tools list, so nothing here knows whether it spends. "
                f"Classify it (read / contribute / trade / provision, or "
                f"paper_gated with the flag that stops it) before calling it."
            )

    # -- the inert-body proof ---------------------------------------------
    def _assert_declared_flags(self, request, rule) -> None:
        """A MUTATE body must carry every flag its rule declares inert.

        components.yaml said of the event-card orders that *"`paper` is
        inert: it is the flag that says no money moves"*, and nothing
        implemented it: `inert_params` is read only by `_assert_inert`, which
        runs at PROBE, and the MUTATE branch checked the tier, `probe_only`
        and the host without ever looking at a body.

        It could not be fixed by enforcing `inert_params`, which was the first
        attempt: elsewhere that key means "these are harmless in a probe body"
        -- `bounty.a2a_send` declares five and sends three -- so requiring all
        of them would have refused the a2a writer. Hence a separate
        declaration for a separate idea.

        What it cost: the live schema resolves an absent `paper` as "use
        user.simulation_mode", and this account's is False. An order with
        `amount_usdc` and no `paper` was a live order, and every guard we had
        would have passed it.

        Present AND truthy. `paper: false` is not a paper order, and a reading
        that only asked whether the key existed would wave it through -- which
        is the same shape as asserting a field is present when the contract is
        about its value.
        """
        declared = getattr(rule, "required_flags", frozenset())
        if not declared:
            return
        try:
            payload = json.loads(request.read() or b"{}")
        except json.JSONDecodeError:
            payload = None
        if not isinstance(payload, dict):
            raise SafetyViolation(
                f"MUTATE body for {rule.id} is not a JSON object, so the "
                f"{', '.join(sorted(declared))} flag it must carry cannot be read."
            )
        missing = sorted(flag for flag in declared if not payload.get(flag))
        if missing:
            raise SafetyViolation(
                f"MUTATE {rule.id} without {', '.join(missing)}. That flag is "
                f"what says no money moves, and this endpoint resolves its "
                f"absence against the account's own simulation_mode. Send it "
                f"true, or do not send the order."
            )

    def _assert_inert(self, request, rule) -> None:
        """A PROBE body must be provably incapable of executing."""
        body = request.read()
        if body in INERT_BODIES:
            return
        try:
            payload = json.loads(body or b"{}")
        except json.JSONDecodeError:
            return  # malformed input is inert by construction
        if not isinstance(payload, dict):
            raise SafetyViolation(
                f"PROBE body for {rule.id} must be a JSON object or inert."
            )

        present = {
            k for k, v in payload.items()
            if k in rule.executable_params and v not in (None, "", [], {})
        }
        if present:
            raise SafetyViolation(
                f"PROBE body for {rule.id} carries executable parameters "
                f"{sorted(present)}. A probe proves REACHABILITY, never "
                f"EXECUTION -- the finding is which error class came back, and "
                f"that is readable from an empty body."
            )

        undeclared = set(payload) - rule.executable_params - rule.inert_params
        if undeclared:
            raise SafetyViolation(
                f"PROBE body for {rule.id} has undeclared keys {sorted(undeclared)}. "
                f"Declare each in components.yaml as executable_params or "
                f"inert_params before probing: the guard cannot reason about "
                f"parameters it has never seen."
            )


_ACTIVE_BUDGET = None


def active_budget():
    """The budget the current session is spending, if one was built.

    Critique gap 11: the run record's `ratelimit` was always empty, because
    the recorder looked for a budget nobody had handed it. A run cut short by
    an exhausted quota was therefore indistinguishable in the record from a
    complete one -- and a partial run may not verify anything.
    """
    return _ACTIVE_BUDGET


class RateLimitBudget:
    """Stops the session before the platform stops it for us.

    Exhausting the quota turns the whole board red with 429s, which looks
    exactly like a platform outage. Better to stop early and record a partial
    run that cannot verify fixes for components it never reached.
    """

    def __init__(self, stop_at_fraction: float = 0.6):
        self.stop_at_fraction = stop_at_fraction
        self.limit: int | None = None
        self.remaining: int | None = None
        self.requests = 0
        self.exhausted = False
        # Registered so the recorder can find it without the session fixture
        # having to remember to pass it along.
        global _ACTIVE_BUDGET
        _ACTIVE_BUDGET = self

    def before_request(self) -> None:
        if self.exhausted:
            raise SafetyViolation(
                f"Rate-limit budget exhausted at {self.stop_at_fraction:.0%} of "
                f"the platform quota ({self.remaining}/{self.limit} left). "
                f"This run is partial and may not verify any fix."
            )
        self.requests += 1

    def after_response(self, response: httpx.Response) -> None:
        try:
            limit = response.headers.get("x-ratelimit-limit")
            remaining = response.headers.get("x-ratelimit-remaining")
            if limit:
                self.limit = int(limit)
            if remaining:
                self.remaining = int(remaining)
        except ValueError:
            return
        if self.limit and self.remaining is not None:
            used = 1 - (self.remaining / self.limit)
            if used >= self.stop_at_fraction:
                self.exhausted = True

    def snapshot(self) -> dict[str, Any]:
        used = None
        if self.limit and self.remaining is not None:
            used = round(1 - (self.remaining / self.limit), 4)
        return {
            "requests": self.requests,
            "limit": self.limit,
            "remaining": self.remaining,
            "fraction_used": used,
            "exhausted": self.exhausted,
        }

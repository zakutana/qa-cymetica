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
import math
import re
import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl

import httpx
import yaml

from qa import timings

REPO_ROOT = Path(__file__).resolve().parent.parent
COMPONENTS_YAML = REPO_ROOT / "components.yaml"


class SafetyViolation(RuntimeError):
    """Raised BEFORE a request reaches the network. Never caught internally."""


class BudgetExhausted(SafetyViolation):
    """Our own rate-limit budget is spent: the session is partial, and a check
    stopped by it measured nothing on their side. Told apart from every other
    refusal so the recorder can call it inconclusive -- a tier or rule refusal is
    OUR check misdeclared and stays red (code review, 2026-10-07)."""


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
    # A MUTATE body may carry ONLY the declared params. For a write whose
    # safety is a matter of WHICH fields it touches rather than of a flag it
    # carries -- the settings PATCH, where `is_trading` or `onchain_pct` is
    # the danger and there is no `paper` to require (V5, 2026-09-23).
    closed_body: bool = False
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
                    closed_body=bool(e.get("closed_body", False)),
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
        # Writes on one of our own clones that move no money and carry no paper
        # argument: {tool: {args: [...], <arg>: [allowed values]}}. See the MUTATE
        # branch of the transport; tool_class stays "unknown" for them, as it does
        # for the paper-gated tools.
        self.tools_own_clone_write: dict[str, dict] = {
            str(name): dict(rule or {}) for name, rule in (tools.get("own_clone_write") or {}).items()}
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
        pacer=None,
    ):
        self.inner = inner
        self.registry = registry
        self.evidence = evidence
        self.budget = budget
        # The shared brake (qa/ratelimit.py). qa/client.py passes one for the real
        # network; a negative control's transport has none.
        self.pacer = pacer

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

        # Timed only when it reaches the real network: a test's MockTransport
        # or a guard's negative control is never written (qa/timings.py).
        real = isinstance(self.inner, httpx.HTTPTransport)
        if self.pacer is not None:
            # Before the clock starts: a wait for our own brake is not their latency.
            self.pacer.wait(request)
        started = time.perf_counter()
        try:
            response = self.inner.handle_request(request)
        except Exception as exc:
            if real:
                timings.record(request, started, tier, error=type(exc).__name__)
            raise

        if self.pacer is not None:
            from qa.ratelimit import may_retry, retry_after

            self.pacer.learn(request, response)
            if response.status_code == 429 and may_retry(method):
                # Their 429 is written down, then honoured: hold the route for
                # Retry-After and ask a READ once more. A write is never resent.
                if real:
                    timings.record(request, started, tier, status=429, to="headers")
                if self.evidence is not None:
                    # Their 429 is kept: it is what a finding about their rate
                    # limiting would stand on (code review, 2026-10-07).
                    try:
                        self.evidence.capture(request, response, tier, rule.id if rule else None)
                    except Exception:  # noqa: BLE001 -- the retry is what matters here
                        pass
                pause = retry_after(response)
                response.close()
                self.pacer.hold(request, pause)
                if self.budget is not None:
                    self.budget.before_request()   # the second send is counted too
                self.pacer.wait(request)
                started = time.perf_counter()
                try:
                    response = self.inner.handle_request(request)
                except Exception as exc:
                    if real:
                        timings.record(request, started, tier, error=type(exc).__name__)
                    raise
                self.pacer.learn(request, response)

        if self.budget is not None:
            self.budget.after_response(response)
        if self.evidence is not None:
            try:
                self.evidence.capture(request, response, tier, rule.id if rule else None)
            except Exception as exc:
                if real:
                    timings.record(request, started, tier, status=response.status_code,
                                   error=type(exc).__name__, to="body")
                raise
        if real:
            timings.record(request, started, tier, status=response.status_code,
                           to="body" if self.evidence is not None else "headers")
        return response

    # -- policy -----------------------------------------------------------
    def _check(self, request, tier, rule, path, method) -> None:
        if rule is not None and rule.forbidden_always:
            raise SafetyViolation(
                f"{method} {rule.id} is permanently denied at every tier."
            )

        # MCP JSON-RPC: safety is decided by the body, not the HTTP method.
        if rule is not None and rule.readonly_rpc:
            writes = self._check_rpc(request, tier, rule)
            # A call that may move money is held to where writes may go, as a
            # REST write is below: this branch returned before the allowlist,
            # so MUTATE over MCP had two gates, not three (RO05, deep pass of
            # 2026-09-24).
            host = request.url.host
            if writes and host not in self.registry.mutate_allowed_hosts:
                raise SafetyViolation(f"MUTATE against unlisted host {host!r}.")
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
        self._assert_closed_body(request, rule)
        host = request.url.host
        if host not in self.registry.mutate_allowed_hosts:
            raise SafetyViolation(f"MUTATE against unlisted host {host!r}.")

    # -- JSON-RPC body classification -------------------------------------
    def _check_rpc(self, request, tier, rule) -> bool:
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

        # A JSON-RPC batch is a list of calls, and every one is held to the rule
        # a single call is. Until 2026-09-22 any body that was not an object
        # returned here unread at PROBE and MUTATE, so a batch carrying
        # place_arena_order with mode 'live' reached the transport (C01).
        if isinstance(payload, list):
            if tier is SafetyTier.SAFE:
                raise SafetyViolation("SAFE test sent a non-object JSON-RPC body.")
            # A list, not a generator: any() over a generator stops at the
            # first True and would leave the calls after it unread.
            return any([self._check_rpc_call(item, tier) for item in payload])
        return self._check_rpc_call(payload, tier)

    def _check_rpc_call(self, payload, tier) -> bool:
        """One JSON-RPC call, alone or as a member of a batch."""
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
            # Cleared to move paper money: the caller holds it to the host
            # allowlist (RO05).
            return True

        # A write on one of our clones that moves nothing and has no paper argument.
        # What the call itself can say is held here; that the clone is a PAPER clone of
        # ours is the caller's floor (scripts/clone.py indicators()).
        own = self.registry.tools_own_clone_write.get(str(tool))
        if own:
            self._assert_own_clone_write(str(tool), args, own)
            return True

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

    @staticmethod
    def _assert_own_clone_write(tool: str, args: dict, rule: dict) -> None:
        """Exactly the arguments the tool documents, and nothing the call could smuggle.

        Three arguments and no fourth: a stray `paper` or `force` is refused, not
        ignored, because a flag the tool does not read is a flag somebody believes
        in. The enumerated ones (`indicator_name`) must be a listed string, exactly.
        `instance_id` is a non-empty string and `params` a non-empty object of plain
        numbers -- a bool is an int in Python and is not a parameter, a string is not
        a number, and NaN or infinity is not a setting.
        """
        wanted = list(rule.get("args") or [])
        extra = sorted(set(args) - set(wanted))
        missing = sorted(set(wanted) - set(args))
        if extra or missing:
            raise SafetyViolation(
                f"MCP tool {tool!r} takes exactly {wanted}; this call has "
                f"extra {extra} and lacks {missing}."
            )
        for key, allowed in rule.items():
            if key == "args":
                continue
            value = args.get(key)
            if not isinstance(value, str) or value not in list(allowed or []):
                raise SafetyViolation(
                    f"MCP tool {tool!r}: {key}={value!r} is not one of {list(allowed or [])}."
                )
        instance = args.get("instance_id")
        if "instance_id" in wanted and (not isinstance(instance, str) or not instance.strip()):
            raise SafetyViolation(f"MCP tool {tool!r}: instance_id must be a non-empty string.")
        if "params" in wanted:
            params = args.get("params")
            plain = (isinstance(params, dict) and params and all(
                isinstance(k, str) and isinstance(v, (int, float)) and not isinstance(v, bool)
                and math.isfinite(v) for k, v in params.items()))
            if not plain:
                raise SafetyViolation(
                    f"MCP tool {tool!r}: params must be a non-empty object of plain numbers, "
                    f"got {params!r}."
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
        # `True` itself, not truthy: "false" and "0" are truthy strings a
        # server may coerce to false (C01, deep pass of 2026-09-22 evening --
        # the MCP paper gate had been fixed the same afternoon, this was not).
        missing = sorted(flag for flag in declared if payload.get(flag) is not True)
        if missing:
            raise SafetyViolation(
                f"MUTATE {rule.id} without {', '.join(missing)}. That flag is "
                f"what says no money moves, and this endpoint resolves its "
                f"absence against the account's own simulation_mode. Send it "
                f"true, or do not send the order."
            )

    def _assert_closed_body(self, request, rule) -> None:
        """A `closed_body` rule's MUTATE request carries declared keys only,
        in its query string and its body alike. Anything unreadable is a
        refusal: a body the guard cannot read is one it cannot vouch for."""
        if not getattr(rule, "closed_body", False):
            return
        allowed = rule.executable_params | rule.inert_params
        query = set(dict(request.url.params.multi_items()))
        try:
            payload = json.loads(request.read() or b"{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = None
        if not isinstance(payload, dict):
            raise SafetyViolation(
                f"MUTATE body for {rule.id} is not a JSON object, so which "
                f"fields it changes cannot be read.")
        undeclared = sorted((set(payload) | query) - allowed)
        if undeclared:
            raise SafetyViolation(
                f"MUTATE {rule.id} carries {undeclared}, not declared in "
                f"components.yaml. This write is safe only in the fields it "
                f"touches; declare a field there, on purpose, before it goes.")

    def _assert_inert(self, request, rule) -> None:
        """A PROBE request must be provably incapable of executing -- the
        whole request, not its JSON body alone.

        Until 2026-09-23 (B1) only a JSON body was read. `toggle-trading`
        takes `enabled` as a query parameter and no body, so
        `?enabled=true` with an empty body was the canonical inert probe; and
        a form body failed json.loads and passed as "malformed input".
        """
        query = dict(request.url.params.multi_items())
        if query:
            self._assert_inert_keys(rule, query, "query string")

        body = request.read()
        if body in INERT_BODIES:
            return
        ctype = request.headers.get("content-type", "").split(";")[0].strip().lower()
        if ctype == "application/x-www-form-urlencoded":
            form = dict(parse_qsl(body.decode("latin-1"), keep_blank_values=True))
            self._assert_inert_keys(rule, form, "form body")
            return
        try:
            payload = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            if ctype == "application/json" or ctype.endswith("+json"):
                return  # malformed JSON: their parser refuses it before any handler
            raise SafetyViolation(
                f"PROBE body for {rule.id} is {ctype or 'untyped'} and not "
                f"JSON, so the guard cannot read what it carries. Send JSON or "
                f"a form, or an empty body."
            )
        if not isinstance(payload, dict):
            raise SafetyViolation(
                f"PROBE body for {rule.id} must be a JSON object or inert."
            )
        self._assert_inert_keys(rule, payload, "body")

    def _assert_inert_keys(self, rule, payload: dict, where: str) -> None:
        """Keys of a PROBE request, wherever they ride: none executable with a
        value, none undeclared."""
        present = {
            k for k, v in payload.items()
            if k in rule.executable_params and v not in (None, "", [], {})
        }
        if present:
            raise SafetyViolation(
                f"PROBE {where} for {rule.id} carries executable parameters "
                f"{sorted(present)}. A probe proves REACHABILITY, never "
                f"EXECUTION -- the finding is which error class came back, and "
                f"that is readable from an empty body."
            )

        undeclared = set(payload) - rule.executable_params - rule.inert_params
        if undeclared:
            raise SafetyViolation(
                f"PROBE {where} for {rule.id} has undeclared keys {sorted(undeclared)}. "
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

    # A limit below this is one ROUTE's own allowance (the Chart Analyzer answers
    # `x-ratelimit-limit: 30`, the backtest 30 a minute), not the platform's quota
    # (300 anonymous, 2000 for our key). Exhausting a route's allowance 429s that route's
    # checks -- a finding about that route; it must not stop the whole session. On
    # 2026-10-04 twelve left of the Chart Analyzer's thirty read as "60 % of the platform
    # quota used", and the last 61 of 1541 checks of two full runs were refused with a
    # SafetyViolation while the platform's quota (2000) was nearly untouched.
    MIN_PLATFORM_QUOTA = 100

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
            raise BudgetExhausted(
                f"Rate-limit budget exhausted at {self.stop_at_fraction:.0%} of "
                f"the platform quota ({self.remaining}/{self.limit} left). "
                f"This run is partial and may not verify any fix."
            )
        self.requests += 1

    def after_response(self, response: httpx.Response) -> None:
        try:
            limit = response.headers.get("x-ratelimit-limit")
            remaining = response.headers.get("x-ratelimit-remaining")
            # Only the platform's own quota is the budget; a route's smaller allowance is not.
            if limit and int(limit) < self.MIN_PLATFORM_QUOTA:
                return
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

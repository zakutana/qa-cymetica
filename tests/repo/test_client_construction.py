"""Nobody but `qa/client.py` builds an HTTP client, and nobody borrows its key.

The construction ban (`qa/client.py::install_client_guard`) is behavioural: it
monkeypatches `httpx.Client.__init__` and refuses any caller that does not pass
a private sentinel. Its refusal message says what to do instead, verbatim:

    Every request must go through SafetyTransport, so use the rest_client /
    mcp_client fixtures instead. If you need a client shape they do not offer,
    add a factory to qa/client.py rather than bypassing the guard.

`qa/fingerprint.py` imported that sentinel and built its own client anyway, so
the platform-fingerprint corpus was read every session with no SafetyTransport
under it: no tier check at the transport, no evidence capture, no rate-limit
budget. It was a SAFE GET of public documents, so nothing was at risk -- but it
was the one call site in the tree doing the thing the guard's own message
forbids, it predates the first architecture reading, and no test could see it
because every existing guard test asserts the ban fires for a caller *without*
the sentinel. Found by the architecture audit, 2026-09-20; closed by
`build_fingerprint_client`.

A static scan rather than a behavioural one on purpose: the defect is a line of
source that never runs under pytest (`compute()` is called from
`pytest_sessionstart`, before the guard is installed), so only reading the tree
can catch the next one.
"""

from __future__ import annotations

import ast
from pathlib import Path

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

REPO = Path(__file__).resolve().parent.parent.parent
ROOTS = ("qa/**/*.py", "scripts/**/*.py", ".claude/hooks/**/*.py")
# The module the guard is made of. It builds clients, holds the sentinel, and
# is the place the refusal message tells a caller to come.
OWNER = "qa/client.py"
CLIENTS = {"Client", "AsyncClient"}


def _offenders() -> list[str]:
    found = []
    for path in sorted({p for root in ROOTS for p in REPO.glob(root)}):
        rel = path.relative_to(REPO).as_posix()
        if rel == OWNER:
            continue
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            # `httpx.Client(...)` / `httpx.AsyncClient(...)`, however the
            # module spells its import.
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr in CLIENTS:
                    owner = getattr(func.value, "id", None)
                    if owner == "httpx":
                        found.append(f"{rel}:{node.lineno}: httpx.{func.attr}(...)")
            # The key itself, imported or referenced under any name.
            if isinstance(node, ast.Name) and node.id == "_FACTORY_SENTINEL":
                found.append(f"{rel}:{node.lineno}: _FACTORY_SENTINEL")
            if isinstance(node, ast.alias) and node.name == "_FACTORY_SENTINEL":
                found.append(f"{rel}: imports _FACTORY_SENTINEL")
    return sorted(set(found))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_only_the_client_module_builds_a_client_or_holds_its_key():
    """Every request goes through a factory, and the key stays private."""
    offenders = _offenders()
    conclude(Measurement(
        verdict="failed" if offenders else "passed",
        reason=("a client built outside qa/client.py runs with no "
                "SafetyTransport under it: " + "; ".join(offenders)
                if offenders else
                "no module outside qa/client.py constructs an httpx client "
                "or names its sentinel"),
        left=offenders, right=[],
        population={"roots": list(ROOTS), "owner": OWNER},
        sources={"contract": "qa/client.py::install_client_guard's refusal "
                             "message -- add a factory rather than bypass"},
    ))

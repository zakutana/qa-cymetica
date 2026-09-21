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


def _offenders(repo: Path = REPO) -> list[str]:
    found = []
    for path in sorted({p for root in ROOTS for p in repo.glob(root)}):
        rel = path.relative_to(repo).as_posix()
        if rel == OWNER:
            continue
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        # HOW THIS MODULE SPELLS ITS IMPORT, read rather than assumed. The
        # first version required `func.value.id == "httpx"`, so
        # `import httpx as hx; hx.Client()` and `from httpx import Client;
        # Client()` were both invisible -- two spellings of the one thing the
        # guard exists to catch, in a guard whose own comment said it caught
        # the call however the import was spelled. Found by two readers on
        # 2026-09-20.
        aliases = {"httpx"}          # names bound to the httpx MODULE
        direct = set()               # names bound to Client/AsyncClient
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "httpx":
                        aliases.add(alias.asname or "httpx")
            if isinstance(node, ast.ImportFrom) and node.module == "httpx":
                for alias in node.names:
                    if alias.name in CLIENTS:
                        direct.add(alias.asname or alias.name)

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr in CLIENTS:
                    if getattr(func.value, "id", None) in aliases:
                        found.append(f"{rel}:{node.lineno}: "
                                     f"{func.value.id}.{func.attr}(...)")
                if isinstance(func, ast.Name) and func.id in direct:
                    found.append(f"{rel}:{node.lineno}: {func.id}(...) "
                                 f"imported from httpx")
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


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_scan_reads_every_spelling_of_the_import(tmp_path):
    """A guard that catches one of three spellings is a guard with a door in it.

    The scan required `httpx.Client(...)` written exactly that way, while its
    own comment said it caught the call "however the module spells its
    import". `import httpx as hx; hx.Client()` and `from httpx import Client;
    Client()` were both invisible -- and either is what the next
    fingerprint.py-shaped bypass would look like, since that one was written
    by somebody who knew the guard existed.

    Driven over real source rather than over the AST by hand, because the
    thing that was wrong was which node shape the walk accepted -- and driven
    through `_offenders()` itself, over a fixture tree. The previous version
    drove a local copy of the walk, so reverting the real scan to
    `func.value.id == "httpx"` left this green while the guard went blind
    again. Deep pass of 2026-09-21, C06.
    """
    fixtures = {
        "qa/plain.py": "import httpx\nhttpx.Client()\n",
        # An aliased module import is the same construction under another name.
        "scripts/aliased.py": "import httpx as hx\nhx.Client()\n",
        # Importing the class and calling it bare is the same construction.
        ".claude/hooks/direct.py": "from httpx import Client\nClient()\n",
        "qa/renamed.py": "from httpx import AsyncClient as AC\nAC()\n",
        "qa/key.py": "from qa.client import _FACTORY_SENTINEL\n",
        # The owner builds clients by design.
        "qa/client.py": "import httpx\nhttpx.Client()\n",
        # And the shapes that must NOT be flagged, or the guard cries wolf and
        # stops being read: somebody else's Client, and a mere import.
        "qa/only_import.py": "import httpx\n",
        "qa/their_lib.py": "from mylib import Client\nClient()\n",
        "qa/own_class.py": "class Client: pass\nClient()\n",
        "qa/other.py": "import other\nother.Client()\n",
    }
    for rel, source in fixtures.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(source, encoding="utf-8")

    assert _offenders(tmp_path) == sorted([
        "qa/plain.py:2: httpx.Client(...)",
        "scripts/aliased.py:2: hx.Client(...)",
        ".claude/hooks/direct.py:2: Client(...) imported from httpx",
        "qa/renamed.py:2: AC(...) imported from httpx",
        "qa/key.py: imports _FACTORY_SENTINEL",
    ]), _offenders(tmp_path)

    # The same scan on the tree as it stands: the repository is clean.
    assert _offenders() == [], _offenders()

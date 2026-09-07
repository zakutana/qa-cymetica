"""Collection-time enforcement, fixtures, and session wiring.

Three things happen here that the rest of the suite depends on:

  1. An untagged test aborts collection. Not a warning -- a hard stop. It is
     the only way a convention survives contact with a tired operator at 2am.
  2. tests/meta/ is reordered to run first and aborts the session on failure.
     If the guard cannot be shown to block, zero live requests are issued.
  3. Every test runs inside a tier context, so the transport always knows who
     is calling and there is no path that can forget to say.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qa.client import (  # noqa: E402
    GuardBreached,
    assert_client_guard_blocks,
    build_client,
    build_mcp_client,
    install_client_guard,
    remove_client_guard,
)
from qa.config import identities  # noqa: E402
from qa.evidence import CURRENT_EVIDENCE, EvidenceStore  # noqa: E402
from qa.marks import Inconclusive  # noqa: E402
from qa.safety import (  # noqa: E402
    CURRENT_NODEID,
    CURRENT_TIER,
    EndpointRegistry,
    RateLimitBudget,
    SafetyTier,
)

# The run-record plugin is registered via `-p qa.report_plugin` in
# pyproject.toml: pytest 8 refuses `pytest_plugins` in a non-root conftest.

QA_MARKERS = ("qa_component", "qa_tier", "qa_surface", "qa_claim",
              "qa_ticket", "qa_volatile")


def pytest_addoption(parser):
    group = parser.getgroup("qa-cymetica")
    group.addoption("--allow-mutate", action="store_true", default=False,
                    help="Permit MUTATE-tier tests to create real platform state.")
    group.addoption("--prereg", default=None, metavar="PRE-NNNN",
                    help="Preregistration id this run is executing under.")
    group.addoption("--snapshot-window", type=int, default=30, metavar="SECONDS",
                    help="Max age spread across sources in one reconciliation.")


def pytest_configure(config):
    for marker in QA_MARKERS:
        config.addinivalue_line("markers", f"{marker}(value): qa metadata")
    install_client_guard()

    # The guard demonstrates itself here, where it is installed, instead of
    # depending on tests/meta being in the selector. The ordering below aborts
    # a session whose guard tests FAIL; a selector that never collects them
    # aborts nothing, and live requests have gone out that way. ~1 ms, no
    # network -- every client in the check sits on a transport that cannot
    # send. See qa/client.py::assert_client_guard_blocks.
    try:
        assert_client_guard_blocks()
    except GuardBreached as exc:
        pytest.exit(
            f"SAFETY GUARD SELF-CHECK FAILED\n\n  {exc}\n\n"
            f"No test ran and no request was sent. Fix the guard; do not "
            f"work around this.",
            returncode=3,
        )


def pytest_unconfigure(config):
    remove_client_guard()


# ---------------------------------------------------------------------------
# Collection-time enforcement
# ---------------------------------------------------------------------------
def pytest_collection_modifyitems(session, config, items):
    registry = EndpointRegistry.load()
    known = set(registry.components)
    errors: list[str] = []

    for item in items:
        component = item.get_closest_marker("qa_component")
        tier = item.get_closest_marker("qa_tier")

        if component is None or tier is None:
            errors.append(
                f"{item.nodeid}\n      missing @qa(component=..., tier=...)"
            )
            continue
        if component.args[0] not in known:
            errors.append(
                f"{item.nodeid}\n      unknown component {component.args[0]!r} "
                f"-- add it to components.yaml"
            )
            continue

        if SafetyTier(tier.args[0]) is SafetyTier.MUTATE and not config.getoption("--allow-mutate"):
            item.add_marker(pytest.mark.skip(
                reason="MUTATE tier requires --allow-mutate"))

    if errors:
        raise pytest.UsageError(
            "QA tagging violations -- every test must carry @qa(...):\n    "
            + "\n    ".join(errors)
        )

    # Guard self-tests first. A broken guard must stop the session before any
    # live request is made, so their position in the run order is load-bearing.
    items.sort(key=lambda i: 0 if "/meta/" in i.nodeid.replace("\\", "/") else 1)


def pytest_runtest_logreport(report):
    """Abort the whole session the moment a guard self-test fails."""
    if report.failed and "/meta/" in report.nodeid.replace("\\", "/"):
        session = getattr(pytest, "_qa_session", None)
        if session is not None:
            session.shouldstop = (
                f"SAFETY GUARD SELF-TEST FAILED ({report.nodeid}). "
                f"No live requests will be issued."
            )


def pytest_sessionstart(session):
    pytest._qa_session = session


# ---------------------------------------------------------------------------
# Session resources
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def registry(request) -> EndpointRegistry:
    reg = EndpointRegistry.load()
    reg.mutate_enabled = bool(request.config.getoption("--allow-mutate"))
    reg.mutate_allowed_hosts = frozenset({"cymetica.com"})
    return reg


@pytest.fixture(scope="session")
def evidence_store(request) -> EvidenceStore:
    run_id = getattr(request.session, "qa_run_id", "run-adhoc")
    return EvidenceStore(run_id)


@pytest.fixture(scope="session")
def budget() -> RateLimitBudget:
    return RateLimitBudget(stop_at_fraction=0.6)


@pytest.fixture(scope="session")
def all_identities():
    return identities()


def _identity_or_skip(all_identities, name):
    identity = all_identities[name]
    if not identity.present:
        pytest.skip(f"identity {name!r} has no credential configured in .env")
    return identity


# ---------------------------------------------------------------------------
# Per-test tier context -- the transport reads these
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _tier_context(request):
    marker = request.node.get_closest_marker("qa_tier")
    tier = SafetyTier(marker.args[0]) if marker else None

    tokens = (
        CURRENT_TIER.set(tier),
        CURRENT_NODEID.set(request.node.nodeid),
        CURRENT_EVIDENCE.set([]),
    )
    try:
        yield
    finally:
        request.node.stash_evidence = CURRENT_EVIDENCE.get() or []
        CURRENT_EVIDENCE.reset(tokens[2])
        CURRENT_NODEID.reset(tokens[1])
        CURRENT_TIER.reset(tokens[0])


# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def rest_anon(registry, evidence_store, budget):
    client = build_client(identities()["anon"], registry, evidence_store, budget)
    yield client
    client.close()


@pytest.fixture(scope="session")
def rest_trusted(registry, evidence_store, budget, all_identities):
    identity = _identity_or_skip(all_identities, "trusted")
    client = build_client(identity, registry, evidence_store, budget)
    yield client
    client.close()


@pytest.fixture(scope="session")
def mcp_anon(registry, evidence_store, budget):
    client = build_mcp_client(identities()["anon"], registry, evidence_store, budget)
    yield client
    client.http.close()


@pytest.fixture(scope="session")
def mcp_trusted(registry, evidence_store, budget, all_identities):
    identity = _identity_or_skip(all_identities, "trusted")
    client = build_mcp_client(identity, registry, evidence_store, budget)
    yield client
    client.http.close()


@pytest.fixture
def rest_client(rest_anon):
    """Default client for guard self-tests: no credential required."""
    return rest_anon


# Inconclusive classification moved to qa/report_plugin.py in phase 1 of the
# hardening plan: the recorder is now the single tryfirst classifier, so there
# is no second wrapper whose ordering could disagree with it. The import of
# Inconclusive above (line 32) is kept so the pinned line ranges do not shift.

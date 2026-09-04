"""Cross-source contradiction sweep.

One test per pair of sources per question. Pairwise rather than N-way so that
adding a source later creates new test ids and leaves existing ones untouched:
a ticket pinned to `agent_names::llms_txt-vs-live_species` must keep working
forever, and an N-way test would change identity every time the source list
grew, silently orphaning every pinned regression check.

Every failure message carries both values, both provenance lines (HTTP status,
cache status, age, Date) and the fetch drift, so the finding can be argued
about on the evidence rather than on our summary of it.
"""

from __future__ import annotations

import itertools
from pathlib import Path

import pytest
import yaml

from qa.extractors import ExtractionError, relation_holds
from qa.marks import Inconclusive, SafetyTier, qa
from qa.sources import Snapshot

CLAIMS_PATH = Path(__file__).parent / "claims.yaml"


def load_claims() -> dict:
    with open(CLAIMS_PATH, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


class Pair:
    def __init__(self, claim: dict, a: str, b: str):
        self.claim = claim
        self.a = a
        self.b = b

    @property
    def id(self) -> str:
        return f"{self.claim['id']}::{self.a}-vs-{self.b}"

    def __repr__(self) -> str:
        return self.id


def pytest_generate_tests(metafunc):
    if "pair" not in metafunc.fixturenames:
        return
    cases, ids = [], []
    for claim in load_claims()["claims"]:
        for a, b in itertools.combinations(sorted(claim["sources"]), 2):
            cases.append(Pair(claim, a, b))
            ids.append(f"{claim['id']}::{a}-vs-{b}")
    metafunc.parametrize("pair", cases, ids=ids)


@pytest.fixture(scope="session")
def snapshot(request, rest_anon, mcp_anon, all_identities, registry,
             evidence_store, budget):
    clients = {"anon": mcp_anon}
    if all_identities["trusted"].present:
        from qa.client import build_mcp_client
        clients["trusted"] = build_mcp_client(
            all_identities["trusted"], registry, evidence_store, budget
        )
    return Snapshot(
        spec=load_claims()["sources"],
        rest_anon=rest_anon,
        rest_trusted_factory=None,
        mcp_clients=clients,
        window_seconds=request.config.getoption("--snapshot-window"),
    )


@qa(component="reconciliation", tier=SafetyTier.SAFE, surface="discovery")
def test_sources_agree(pair, snapshot):
    claim = pair.claim
    extractors = claim["sources"]

    try:
        left = snapshot.value(pair.a, extractors[pair.a])
        right = snapshot.value(pair.b, extractors[pair.b])
    except ExtractionError as exc:
        # A source that cannot be read is a finding about that source, but it
        # is not evidence that two sources disagree. Keep the two apart.
        raise Inconclusive(f"{claim['id']}: {exc}") from exc

    # A cached copy older than the window cannot be compared to live data
    # without manufacturing a contradiction out of latency.
    if claim.get("volatile"):
        drift = snapshot.drift_seconds(pair.a, pair.b)
        if drift > snapshot.window_seconds:
            raise Inconclusive(
                f"{claim['id']}: sources fetched {drift:.0f}s apart, "
                f"window is {snapshot.window_seconds}s"
            )
        for name in (pair.a, pair.b):
            if snapshot.cached_beyond_window(name):
                raise Inconclusive(
                    f"{claim['id']}: {name} served from cache older than the window"
                )

    holds, why = relation_holds(
        claim["relation"], left, right, float(claim.get("tolerance_pct", 0))
    )

    assert holds, _explain(pair, snapshot, left, right, why)


def _explain(pair, snapshot, left, right, why) -> str:
    claim = pair.claim
    fa, fb = snapshot.fetch(pair.a), snapshot.fetch(pair.b)
    lines = [
        "",
        f"QUESTION   {claim['question']}",
        f"CLAIM ID   {claim['id']}",
        f"SEVERITY   {claim.get('severity', 'S3-CONTRACT')}",
        f"RELATION   {claim['relation']} -- {why}",
        "",
        f"  {pair.a:<16} = {_fmt(left)}",
        f"  {'':<16}   [{fa.provenance()}]",
        f"  {pair.b:<16} = {_fmt(right)}",
        f"  {'':<16}   [{fb.provenance()}]",
        "",
        f"DRIFT      {snapshot.drift_seconds(pair.a, pair.b):.1f}s between fetches",
    ]
    if claim.get("note"):
        lines += ["", f"NOTE       {' '.join(claim['note'].split())}"]
    evidence = [e for e in (fa.evidence_id, fb.evidence_id) if e]
    if evidence:
        lines += ["", f"EVIDENCE   {', '.join(evidence)}"]
    return "\n".join(lines)


def _fmt(value) -> str:
    if isinstance(value, (set, frozenset)):
        items = sorted(str(v) for v in value)
        shown = ", ".join(items[:12])
        more = f" ... (+{len(items) - 12} more)" if len(items) > 12 else ""
        return f"{{{shown}{more}}}  n={len(items)}"
    return repr(value)


@qa(component="reconciliation", tier=SafetyTier.SAFE, surface="discovery")
def test_every_claim_has_at_least_two_sources():
    """A single-source claim cannot contradict anything: it is a typo."""
    thin = [
        c["id"] for c in load_claims()["claims"] if len(c.get("sources", {})) < 2
    ]
    assert not thin, f"claims with fewer than two sources: {thin}"


@qa(component="reconciliation", tier=SafetyTier.SAFE, surface="discovery")
def test_every_claim_source_is_declared():
    """Guards against a typo in a source name silently skipping a comparison."""
    data = load_claims()
    declared = set(data["sources"])
    unknown = {
        f"{c['id']}.{name}"
        for c in data["claims"]
        for name in c["sources"]
        if name not in declared
    }
    assert not unknown, f"undeclared sources referenced: {sorted(unknown)}"

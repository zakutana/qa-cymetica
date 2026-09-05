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

import hashlib
import itertools
import json
from pathlib import Path

import pytest
import yaml

from qa.extractors import ExtractionError, relation_holds
from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude
from qa.sources import Snapshot

CLAIMS_PATH = Path(__file__).parent / "claims.yaml"


def load_claims() -> dict:
    with open(CLAIMS_PATH, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# Extractor kinds that read a document's STRUCTURE rather than its prose.
STRUCTURED = frozenset({"jsonpath", "len", "set", "keys", "count"})


class Pair:
    def __init__(self, claim: dict, a: str, b: str, sources: dict | None = None):
        self.claim = claim
        self.a = a
        self.b = b
        self.source_specs = sources or {}

    @property
    def id(self) -> str:
        return f"{self.claim['id']}::{self.a}-vs-{self.b}"

    @property
    def fingerprint(self) -> str:
        """A hash of what this comparison IS, not of what it is called.

        The incident: agent_names was rewritten from set_equal to subset with
        both extractors replaced (9a729ed -> 0d5cd34), and because the nodeid
        never changed, the ledger saw a passing check under the same identity
        and read it as a fix. Prose -- question, note, severity -- is
        deliberately excluded: rewording a question does not change what is
        measured, and forcing re-verification for a typo fix would train
        everyone to ignore the signal.
        """
        definition = {
            "relation": self.claim["relation"],
            "tolerance_pct": self.claim.get("tolerance_pct", 0),
            "prose_only": bool(self.claim.get("prose_only")),
            "extractors": {
                self.a: self.claim["sources"][self.a],
                self.b: self.claim["sources"][self.b],
            },
            # The documents are part of the definition: pointing a claim at a
            # different URL is a different measurement.
            "sources": {name: self.source_specs.get(name, {})
                        for name in (self.a, self.b)},
        }
        blob = json.dumps(definition, sort_keys=True, ensure_ascii=False)
        return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]

    @property
    def role(self) -> str:
        """`verdict` may open or close a finding; `evidence` may only inform.

        One sentence against another sentence measures how the platform
        DESCRIBES itself, not what it does. Worth recording and worth asking
        about, but it may not by itself mint a defect or verify a fix --
        neither operand has been anywhere near the behaviour.

        A claim may declare `prose_only: true` with a stated reason, which is
        how a document's self-consistency stays a real verdict: there, the
        prose is the subject.
        """
        if self.claim.get("prose_only"):
            return "verdict"
        kinds = [self.claim["sources"][name].partition(":")[0]
                 for name in (self.a, self.b)]
        return "verdict" if any(k in STRUCTURED for k in kinds) else "evidence"

    def __repr__(self) -> str:
        return self.id


def pytest_generate_tests(metafunc):
    if "pair" not in metafunc.fixturenames:
        return
    data = load_claims()
    cases, ids = [], []
    for claim in data["claims"]:
        for a, b in itertools.combinations(sorted(claim["sources"]), 2):
            cases.append(Pair(claim, a, b, sources=data["sources"]))
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
    fa, fb = snapshot.fetch(pair.a), snapshot.fetch(pair.b)
    provenance = {pair.a: fa.provenance(), pair.b: fb.provenance()}
    evidence_ids = [e for e in (fa.evidence_id, fb.evidence_id) if e]

    def measured(verdict, reason, **extra):
        return Measurement(
            verdict=verdict, reason=f"{claim['id']}: {reason}",
            sources={pair.a: extractors[pair.a], pair.b: extractors[pair.b]},
            provenance=provenance, evidence_ids=evidence_ids,
            fingerprint=pair.fingerprint, claim_id=claim["id"], role=pair.role,
            **extra,
        )

    # A cached copy older than the window cannot be compared to live data
    # without manufacturing a contradiction out of latency. This used to run
    # only for claims tagged `volatile` -- one of eight -- so the other seven
    # compared a CDN copy of llms.txt against live JSON with no window at all.
    # Freshness is a property of the COMPARISON, not of the claim's subject.
    drift = snapshot.drift_seconds(pair.a, pair.b)
    if drift > snapshot.window_seconds:
        conclude(measured("inconclusive",
                          f"sources fetched {drift:.0f}s apart, window is "
                          f"{snapshot.window_seconds}s",
                          left=drift, right=snapshot.window_seconds))
        return
    for name in (pair.a, pair.b):
        if snapshot.cached_beyond_window(name):
            conclude(measured("inconclusive",
                              f"{name} was served from a cache older than the "
                              f"{snapshot.window_seconds}s window"))
            return

    try:
        left, witness_a = snapshot.value_with_witness(pair.a, extractors[pair.a])
        right, witness_b = snapshot.value_with_witness(pair.b, extractors[pair.b])
    except ExtractionError as exc:
        # A source that cannot be read is a finding about that source, but it
        # is not evidence that two sources disagree. Keep the two apart.
        conclude(measured("inconclusive", str(exc)))
        return

    holds, why = relation_holds(
        claim["relation"], left, right, float(claim.get("tolerance_pct", 0))
    )

    conclude(measured(
        "passed" if holds else "failed",
        why or f"{claim['relation']} holds",
        left=left, right=right,
        population={"witness": {pair.a: witness_a[:300], pair.b: witness_b[:300]}},
    ))


# _explain() and _fmt() are gone. The failure message is now rendered from the
# Measurement by qa.measure.explain(), which means the run record carries the
# same structured object the operator reads -- rather than the record carrying
# a regex-scrape of the text we printed. That scrape is how a line of our own
# source once reached the vendor as evidence about their platform.


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

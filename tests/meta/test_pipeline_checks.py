"""RECON / SRC / EXT / TL / INV: the checks assert invariants, not snapshots.

The audit's fourth mechanism. Four checks passed on exactly the defect they
were written for, because each had frozen the shape of that day's evidence
instead of the property that made it a defect:

  * `agent_names` enumerated the 21 agent symbols observed across two
    captures, so it matched whatever llms.txt happened to contain.
  * the trust ladder asserted the vendor's error VOCABULARY, so a reworded
    message would have broken it and a validation error containing the word
    "trust" would have passed it.
  * the freshness guard ran only for claims tagged `volatile` -- one of eight
    -- so the other seven compared a CDN copy against live JSON with no window.
  * reachability was computed over whatever was documented at that moment, so
    deleting 27 paths from the documentation turned eight sections green.

None of these tests makes a request. They run against the two committed
llms.txt captures and the two committed inventories -- the real documents from
either side of the incident.

Fails at 3dee41b: Pair has no fingerprint, extractors have no list_after, the
trust ladder has no refusal_class, inventory has no compare.
"""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest
import yaml

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
FIX = Path(__file__).resolve().parent / "fixtures"

# The two committed captures, either side of the rewrite.
CAPTURES = {
    "with_species": FIX / "llms" /
    "418ebccc30b3a6b069531aecd49a707dc18506c2720be17b31afee54893e7374.json",
    "with_agents": FIX / "llms" /
    "f167f8cacee104d19510183604ebad247a80a2676e63949f600da83d1291beea.json",
}


def _llms(which: str) -> str:
    capture = json.loads(CAPTURES[which].read_text(encoding="utf-8"))
    body = capture["response"]["body"]
    return body["value"] if isinstance(body, dict) else body


def _module(relpath: str, name: str | None = None):
    path = REPO / relpath
    spec = importlib.util.spec_from_file_location(name or (path.stem + "_m"), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _claims() -> dict:
    return yaml.safe_load(
        (REPO / "tests" / "reconciliation" / "claims.yaml").read_text(encoding="utf-8"))


def _pair(claim_id: str):
    from tests.reconciliation.test_reconcile import Pair

    data = _claims()
    claim = next(c for c in data["claims"] if c["id"] == claim_id)
    a, b = sorted(claim["sources"])
    return Pair(claim, a, b, sources=data["sources"])


# ---------------------------------------------------------------------------
# EXT -- the extractor names a place, not a list of expected values
# ---------------------------------------------------------------------------
@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_extractor_reads_whatever_the_document_says():
    """Against both real captures, with different symbol sets in each."""
    from qa.extractors import extract

    assert extract("list_after:AI trading agent", _llms("with_species")) == frozenset(
        {"MACD", "RSI", "BOLL", "VOL", "TREND", "STOCH", "ICHI", "FIB", "ATR",
         "DIV", "PCPN"})
    assert extract("list_after:AI trading agent", _llms("with_agents")) == frozenset(
        {"DELTA", "STAT", "CORR", "SENT", "SYNC", "CRASH", "DREAD", "GLOOM",
         "FADE", "VORTX"})


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize("which", sorted(CAPTURES))
def test_extractor_detects_injected_phantom(which):
    """The test the old extractor could not pass.

    A symbol that does not exist is inserted into the document's own list. The
    enumerating version matched only its 21 known symbols, so the phantom was
    invisible and the check went green on a document naming an agent that does
    not exist. Anchored to the place instead, the phantom is simply read."""
    from qa.extractors import ExtractionError, extract

    text = _llms(which)
    real = extract("list_after:AI trading agent", text)

    # Every occurrence: the document states the list twice, and patching only
    # one would make it ambiguous rather than wrong -- a different defect,
    # covered by test_an_ambiguous_anchor_is_inconclusive_not_a_guess.
    poisoned = text.replace("MACD, RSI", "MACD, XYZQ, RSI")
    poisoned = poisoned.replace("DELTA, STAT", "DELTA, XYZQ, STAT")
    assert poisoned != text, "the injection did not apply to this capture"

    seen = extract("list_after:AI trading agent", poisoned)
    assert "XYZQ" in seen, "a phantom symbol in the document was not read"
    assert seen == real | {"XYZQ"}

    # And nothing outside the anchored list leaks in: the same sentence is
    # full of tickers (BTC, ETH, NVDA) and acronyms (CLOB, NAV) that a
    # document-wide regex would have swept up, needing a stoplist to remove --
    # a stoplist being another enumeration of values, with the same defect.
    for stray in ("BTC", "ETH", "NVDA", "CLOB", "NAV", "SBIO", "VAIX"):
        assert stray not in seen, f"{stray} leaked in from outside the list"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_no_claim_enumerates_the_values_it_expects():
    """Critique gap 7, generalised. The gap asked for a stoplist that is
    itself inside the fingerprint; the better answer is that there is no
    stoplist and no value enumeration anywhere, because both are the same
    defect -- a check that knows the answer in advance."""
    for claim in _claims()["claims"]:
        for name, spec in claim["sources"].items():
            assert "stoplist" not in spec, f"{claim['id']}.{name}"
            kind, _, arg = spec.partition(":")
            if kind in ("regex_all", "regex_set"):
                alternatives = arg.count("|")
                assert alternatives < 3, (
                    f"{claim['id']}.{name} enumerates {alternatives + 1} expected "
                    f"values: {spec}\nAnchor to a place in the document instead."
                )


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_ambiguous_anchor_is_inconclusive_not_a_guess():
    """Two different lists after the same phrase is not something to pick
    from. The extractor refuses, and the check reads Inconclusive."""
    from qa.extractors import ExtractionError, extract

    text = _llms("with_species")
    doubled = text + "\n\nAlso 3 AI trading agents (AAA, BBB, CCC) elsewhere.\n"
    with pytest.raises(ExtractionError, match="DIFFERENT"):
        extract("list_after:AI trading agent", doubled)


# ---------------------------------------------------------------------------
# RECON -- fingerprint tracks the definition
# ---------------------------------------------------------------------------
@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_fingerprint_tracks_definition_not_prose():
    """The real incident: agent_names went from set_equal with two enumerating
    extractors to subset with two new ones (9a729ed -> 0d5cd34), and the
    nodeid never moved. The ledger saw the same check pass and called it a
    fix. Under a fingerprint, that same rewrite reads CHECK_CHANGED."""
    pair = _pair("agent_names")
    original = pair.fingerprint

    # Prose changes must NOT move it, or a typo fix would demand a re-run and
    # everyone would learn to ignore the signal.
    for field, value in (("question", "Reworded?"), ("note", "New note."),
                         ("severity", "S2-MEASUREMENT")):
        reworded = _pair("agent_names")
        reworded.claim = {**reworded.claim, field: value}
        assert reworded.fingerprint == original, f"{field} moved the fingerprint"

    # The 9a729ed definition: a different relation and different extractors.
    old = _pair("agent_names")
    old.claim = {
        **old.claim, "relation": "set_equal",
        "sources": {
            "llms_txt": "regex_set:\\(([A-Z, ]+)\\)",
            "live_species": "set:$[*].symbol",
        },
    }
    assert old.fingerprint != original, \
        "rewriting the relation and an extractor did not change the fingerprint"

    # Pointing a claim at a different document is a different measurement.
    moved = _pair("agent_names")
    moved.source_specs = {**moved.source_specs,
                          "llms_txt": {"kind": "text", "url": "/llms-v2.txt"}}
    assert moved.fingerprint != original, "the source URL is not in the fingerprint"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_prose_versus_prose_is_evidence_not_a_verdict():
    """Neither operand of a sentence-versus-sentence comparison has been near
    the behaviour, so it may inform a finding but never mint or close one.

    The exception is a claim that declares prose_only with a reason -- which
    is how a document's self-consistency stays a real verdict."""
    # clob_pair_count used to be the example here. It has left the table
    # entirely: both its sources were sentences, so it could not fail, and it
    # is now a real count against list_clob_pairs. The rule is checked for
    # every claim in test_pipeline_check_quality.py, so no claim can quietly
    # become prose-versus-prose and keep a verdict.
    assert _pair("agent_names").role == "verdict"
    assert _pair("agent_count").role == "verdict"

    # llms_agent_count_self_consistent was the prose_only example here until
    # 2026-09-05, when the vendor consolidated the duplicated sentence it
    # compared -- the claim would have gone green by losing an operand, so it
    # was replaced by a check reading every stated count against the live
    # catalogue. The table may legitimately hold no prose_only claim at all,
    # so the rule is asserted over whatever is declared, rather than over one
    # named example that can be removed out from under it.
    for pair in (_pair(c["id"]) for c in _claims()["claims"]
                 if c.get("prose_only")):
        assert pair.role == "verdict", pair.claim["id"]
        assert (pair.claim.get("why") or "").strip(), \
            f"{pair.claim['id']}: prose_only without a reason is an override"

    # An evidence-role measurement cannot fail a check.
    from qa.measure import Measurement, conclude
    assert conclude(Measurement(verdict="failed", reason="x", role="evidence")) is None


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_prose_only_claim_states_why():
    for claim in _claims()["claims"]:
        if claim.get("prose_only"):
            assert (claim.get("why") or "").strip(), claim["id"]


# ---------------------------------------------------------------------------
# SRC -- one document is one fetch, and a failed read is not a value
# ---------------------------------------------------------------------------
@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_reconciliation_freshness_per_comparison_and_url_keyed_cache():
    """llms_txt and llms_txt_2 are the same URL -- two statements inside one
    document. Keyed by NAME, the cache fetched it twice, putting a real time
    gap between the two halves of a self-consistency claim and making the
    drift guard measure a difference we had created ourselves."""
    from qa.sources import Fetched, Snapshot

    spec = _claims()["sources"]
    assert spec["llms_txt"]["url"] == spec["llms_txt_2"]["url"]
    assert Snapshot._cache_key(spec["llms_txt"]) == Snapshot._cache_key(spec["llms_txt_2"])
    assert Snapshot._cache_key(spec["llms_txt"]) != Snapshot._cache_key(spec["openapi"])
    assert (Snapshot._cache_key(spec["mcp_anon"])
            != Snapshot._cache_key(spec["mcp_trusted"]))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize("claim_id", ["agent_names", "agent_count", "skills_subset"])
def test_freshness_guard_applies_to_every_claim(claim_id):
    """The guard ran only for claims tagged `volatile` -- one of eight -- so
    the other seven compared a CDN copy of llms.txt against live JSON with no
    window at all. Freshness is a property of the COMPARISON, not of the
    claim's subject, and none of these three is tagged volatile.

    Exercised by calling the check with a stub snapshot rather than by reading
    its source: what matters is that a stale comparison comes out
    Inconclusive, not that a particular word is absent from the file."""
    from qa.marks import Inconclusive
    from qa.sources import Fetched
    from tests.reconciliation.test_reconcile import test_sources_agree

    class _Stub:
        window_seconds = 30

        def __init__(self, drift=0.0, cached=False):
            self.drift, self.cached = drift, cached

        def fetch(self, name):
            return Fetched(name=name, body={}, status=200, fetched_at=0.0)

        def drift_seconds(self, a, b):
            return self.drift

        def cached_beyond_window(self, name):
            return self.cached

        def value_with_witness(self, name, spec):
            return frozenset({"A"}), "witness"

    pair = _pair(claim_id)
    assert not pair.claim.get("volatile"), f"{claim_id} is tagged volatile"

    with pytest.raises(Inconclusive, match="apart"):
        test_sources_agree(pair, _Stub(drift=120.0))

    with pytest.raises(Inconclusive, match="cache"):
        test_sources_agree(pair, _Stub(cached=True))

    # Inside the window it measures normally.
    test_sources_agree(pair, _Stub(drift=1.0))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize("status,klass", [
    (200, "ok"), (401, "unauthorized"), (403, "forbidden"),
    (404, "not_found"), (500, "server_error"), (302, "malformed"),
])
def test_a_failed_read_is_never_a_value(status, klass):
    """A 401 body compared against a live endpoint manufactures a
    contradiction entirely out of our own credentials, then reports it as
    theirs."""
    from qa.extractors import ExtractionError
    from qa.sources import Fetched, Snapshot

    fetched = Fetched(name="x", body={"tools": []}, status=status, fetched_at=0.0)
    assert fetched.klass == klass
    assert fetched.ok == (klass == "ok")

    if klass == "ok":
        return
    snapshot = Snapshot(spec={"x": {"kind": "json", "url": "/x"}}, rest_anon=None,
                        rest_trusted_factory=None, mcp_clients={})
    snapshot._cache[Snapshot._cache_key({"kind": "json", "url": "/x"})] = fetched
    with pytest.raises(ExtractionError, match=klass):
        snapshot.value("x", "len:$.tools")


# ---------------------------------------------------------------------------
# TL -- the property, not the vocabulary
# ---------------------------------------------------------------------------
@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize("payload,expected", [
    ({"result": {"isError": True, "content": [{"text": "INSUFFICIENT_TRUST"}]}},
     "refused_authz"),
    ({"result": {"isError": True, "content": [{"text": "Access denied for this key"}]}},
     "refused_authz"),
    ({"result": {"isError": True, "content": [{"text": "field 'amount' is required"}]}},
     "refused_validation"),
    ({"result": {"isError": True, "content": [{"text": "invalid parameter: size"}]}},
     "refused_validation"),
    ({"result": {"content": [{"text": "order placed"}]}}, "executed"),
    ({"result": {"isError": True, "content": [{"text": "E_17"}]}}, "unknown"),
])
def test_trust_ladder_asserts_property_not_vocabulary(payload, expected):
    """Rewording their error must not break the check, and a validation error
    must not pass it. A validation error means the call reached argument
    inspection, which is exactly where an unauthorized caller must never get
    -- so it is a FAILURE, not a different flavour of refusal."""
    ladder = _module("tests/mcp/test_trust_ladder.py", "tl_mod")
    assert ladder.refusal_class(payload)[0] == expected


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_trust_ladder_no_longer_greps_for_a_phrase():
    body = (REPO / "tests" / "mcp" / "test_trust_ladder.py").read_text(encoding="utf-8")
    test = body[body.index("def test_call_time_authorization_holds_for_anonymous"):]
    assert "INSUFFICIENT_TRUST" not in test, \
        "the check still asserts the vendor's exact wording"
    assert "refusal_class" in test


# ---------------------------------------------------------------------------
# INV / PIN404 -- the denominator is pinned
# ---------------------------------------------------------------------------
@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_inventory_population_pinned():
    """compare() on the two real captures: not one path was fixed in place.

    All 26 left the documentation. The dashboard read that as eight sections
    going green and a finding about 404s being verified."""
    inventory = _module("scripts/inventory.py", "inv_mod")

    before = json.loads((FIX / "inventory.before-fix.json").read_text(encoding="utf-8"))
    after = json.loads((FIX / "inventory.after-fix.json").read_text(encoding="utf-8"))
    result = inventory.compare(before, after)

    assert result["fixed_in_place"] == [], result["fixed_in_place"]
    assert len(result["removed_from_docs"]) == 26
    assert result["still_missing"] == []

    pinned = yaml.safe_load(
        (REPO / "tests" / "pinned" / "documented-404.yaml").read_text(encoding="utf-8"))
    assert sorted(p["path"] for p in pinned["paths"]) == result["removed_from_docs"], \
        "the pin file and the captures disagree about which paths were missing"

    # compare() is pure: same inputs, same answer, inputs untouched.
    snapshot = copy.deepcopy(before)
    assert inventory.compare(before, after) == result
    assert before == snapshot


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_no_claim_id_shadows_an_existing_ledger_row():
    """A finding's id is derived from its claim, so a claim that differs from
    an existing row only in punctuation mints a DUPLICATE row for the same
    defect -- one carrying the report ids and history, one empty.

    That happened on the first admissible run: three checks written with
    underscored claim ids produced CYM-documented_404 beside the existing
    CYM-documented-404. The plan already records that finding ids derived from
    check names is a limitation it does not solve; this at least makes the
    collision loud instead of silent."""
    import json
    import re

    ledger_file = REPO / "state" / "ledger.json"
    if not ledger_file.exists():
        pytest.skip("no committed ledger to compare against")

    existing = set(json.loads(ledger_file.read_text(encoding="utf-8"))["findings"])
    source = "\n".join(p.read_text(encoding="utf-8") for p in _check_files())
    claims = set(re.findall(r"claim(?:_id)?\s*=\s*[\"']([\w.-]+)[\"']", source))

    def normal(text: str) -> str:
        return text.replace("_", "-").lower()

    collisions = []
    for claim in sorted(claims):
        candidate = f"CYM-{claim}"
        if candidate in existing:
            continue
        shadowed = [row for row in existing if normal(row) == normal(candidate)]
        if shadowed:
            collisions.append(f"{candidate} shadows {shadowed[0]}")
    assert not collisions, (
        "these claims would mint a duplicate row for a defect that already has "
        "one:\n  " + "\n  ".join(collisions)
    )


def _check_files():
    """Every check file except this block's own -- the meta tests name claim
    ids as fixtures and would otherwise trip the guard on their own examples."""
    return [p for p in REPO.glob("tests/**/*.py")
            if "/meta/" not in p.as_posix().replace("\\", "/")]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_level_v_without_trusted_key_is_flagged_partial():
    """Critique gap 8. A clean, tagged, full run made without QA_TRUSTED_KEY
    is level V and has never adjudicated a single S0 row -- every check
    needing that key was skipped. The fold is already safe, because a skipped
    check moves nothing; what was missing is telling the operator, who reads
    "V" and reasonably assumes the ladder was climbed."""
    from qa.state import admissibility

    from tests.meta.test_pipeline_fold import run as make_run

    full = make_run("run-full")
    assert admissibility(full).label == "V"
    assert admissibility(full).notes == []

    partial = make_run("run-partial-identity")
    partial["identities_present"] = {"anon": True, "trusted": False}
    verdict = admissibility(partial)
    assert verdict.level == "V", "a missing identity must not block the level"
    assert verdict.notes == ["identity_absent:trusted"]
    assert verdict.label == "V (partial identity)"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_pinned_and_bounty_checks_are_collectible():
    """Five ledger rows named scripts/*.py as their check. pytest does not
    collect a script, so those rows sat outside the verification machinery
    while still displaying a state -- two of them VERIFIED FIXED."""
    import subprocess
    import sys

    out = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "--no-header",
         "tests/pinned", "tests/rest/test_bounty_tracker.py"],
        cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
        env={**__import__("os").environ, "QA_OFFLINE": "1",
             "QA_STATE_DIR": str(Path(__import__("tempfile").mkdtemp())),
             "PYTHONIOENCODING": "utf-8"},
    )
    nodeids = [line.strip() for line in out.stdout.splitlines()
               if "::" in line and line.startswith("tests/")]

    pinned = [n for n in nodeids if "test_documented_path_is_served" in n]
    bounty = [n for n in nodeids if "test_bounty_tracker" in n]

    # Against the pin file, not against the number 26. The invariant is that
    # every pinned path becomes a collectible check -- which is the whole
    # point, five rows once naming scripts/*.py that pytest never collects.
    # Hard-coding the count made a 27th pinned path fail this test with
    # "27 pinned 404 checks collected", which reads like a defect and is a
    # list getting longer. This file's own title is that the checks assert
    # invariants and not snapshots.
    expected = yaml.safe_load(
        (REPO / "tests" / "pinned" / "documented-404.yaml").read_text(encoding="utf-8"))
    assert len(pinned) == len(expected["paths"]), (
        f"{len(pinned)} checks collected for {len(expected['paths'])} pinned "
        f"paths -- a pinned path that collects no check is a row outside the "
        f"verification machinery"
    )
    assert len(bounty) == 3, f"{len(bounty)} bounty checks collected: {bounty}"

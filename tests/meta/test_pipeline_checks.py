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

from qa.extractors import iter_extractors
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
            # The sibling of this guard read only the first token too, so a
            # regex behind `scope:<heading>|...` was invisible to both -- and
            # that wrapper holds the only regex in the file.
            for kind, arg in iter_extractors(spec):
                if kind not in ("regex_all", "regex_set", "regex", "regex_int"):
                    continue
                # No alternation at all. The threshold used to be `< 3`, which
                # admitted `regex_set:(DELTA|STAT|CORR)` -- three enumerated
                # values, and precisely the extractor shape the
                # phantom-injection test forty lines above condemns, since a
                # fourth symbol in the document would be invisible to it.
                # Nothing justified the number: no claim in claims.yaml carries
                # any alternation inside an extractor argument, and every other
                # clause in this check is absolute. Deep pass, 2026-09-08, 3/3.
                alternatives = arg.count("|")
                assert alternatives == 0, (
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
    # B01, deep pass 2026-09-09, three votes of three. `executed` was the
    # FALL-THROUGH, and McpClient.raw() returns response.json() whatever the
    # HTTP status -- its own comment says rpc() does not raise for status. So
    # a 401, a 422 and a 500 all arrived here carrying neither `result` nor
    # `error`, produced an empty body, matched no vocabulary, and fell through
    # to "an anonymous caller EXECUTED the tool": an S1 authorization-bypass
    # accusation minted out of a failed read, and shipped with population
    # {"body": ""}, i.e. no evidence of execution at all. Rule 8 in the one
    # check that speaks to the vendor. Nothing false went out -- no ledger row
    # cites this check.
    ({"detail": "Not authenticated"}, "unknown"),
    ({"detail": "Internal Server Error"}, "unknown"),
    ({"detail": [{"loc": ["body", "amount"], "msg": "field required"}]},
     "unknown"),
    ({}, "unknown"),
    # And the same rule from the other side: a well-formed MCP result whose
    # body is empty says nothing either.
    ({"result": {"content": [{"text": ""}]}}, "unknown"),
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
def test_a_section_with_nothing_documented_still_gets_a_row():
    """`buckets` is a defaultdict populated only by appending to it, so a
    section matching zero documented paths and naming zero tools got no
    bucket at all and `assemble()` skipped it outright -- exactly the state
    of the Movers Tournament, registered in components.yaml since
    2026-09-13 but named nowhere in /api-docs. A section this empty is the
    one most worth a row, not the one most worth hiding.

    FALLBACK is the one exception: "everything we could not classify" earns
    a row only once something has actually landed there.
    """
    inventory = _module("scripts/inventory.py", "inv_mod")

    result = inventory.assemble(documented={}, tools={
        "declared": {}, "served_anon": [], "served_trusted": []})
    ids = {s["id"] for s in result["sections"]}

    assert set(inventory.SECTIONS[0].keys()) & {"id"}, "sanity: SECTIONS is real"
    empty_sections = {s["id"] for s in inventory.SECTIONS}
    assert empty_sections <= ids, (
        f"every declared section must appear even with nothing found: "
        f"missing {empty_sections - ids}")
    assert inventory.FALLBACK["id"] not in ids, (
        "the fallback bucket is not a section in its own right until "
        "something actually lands there")

    movers = next(s for s in result["sections"] if s["id"] == "movers")
    assert movers["population"]["documented"] == 0
    assert movers["reachable_pct"] is None, (
        "zero probed endpoints is unmeasured, not 0% reachable")


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
    # A retired path is the one legitimate way a pin stops collecting: the
    # document stopped promising it, so there is nothing left to measure, and
    # the retirement is a journal event with a reason. It keeps its line in
    # the pin file, which is what makes the shrink visible -- so the sum is
    # still the frozen 26 and this guard still catches a path that vanishes
    # without anyone saying so.
    retired = set(expected.get("retired") or ())
    assert len(pinned) + len(retired) == len(expected["paths"]), (
        f"{len(pinned)} checks collected and {len(retired)} retired for "
        f"{len(expected['paths'])} pinned paths -- a pinned path that neither "
        f"collects a check nor was retired by an event is a row outside the "
        f"verification machinery"
    )
    assert retired <= {p["path"] for p in expected["paths"]},         "a retired path was never one of the pinned ones"
    assert len(bounty) == 3, f"{len(bounty)} bounty checks collected: {bounty}"


# -- the subject grows, and the check kept judging all of it ---------------
#
# The fifth mechanism, found by the 2026-09-10 sweep. Two open checks read an
# append-only log of OURS and judged every row in it, so no fix the vendor
# could ship would ever turn them green:
#
#   * #87 failed if ANY recorded paper trade opened a position without a
#     debit. The two trades in the log are from 11:41 and 11:59; the fix was
#     claimed live at 18:06. Those rows are frozen evidence of the old
#     behaviour.
#   * #85 failed on the UNION of tools named across every recorded Nexus
#     answer. Its only offender was named at 10:23, before their 12:37
#     release -- and we had already told them at 13:11 that a fresh answer
#     was clean, then sent a `fail` at 16:52 anyway.
#
# Both docstrings promise the present tense ("costs something", "cannot act
# on"). Nothing caught the drift: the fold was right, the run admissible, the
# fingerprint stable, and the assertion matched the docstring's words. What
# moved was the subject set, months after the sentence was written -- on the
# day it is written the log has one entry and both readings agree.
#
# So these fix the reading to the NEWEST entry and keep the rest as
# population. The anti-fallback case is the one that matters: a newest trade
# that could not be read is Inconclusive, never "then judge the one before
# it", which would silently re-report TRD-0002 after a fresh trade whose read
# failed. Rule 8, on the row that decides #87.


def _trade(trade_id, at, *, usdc, was, now, positions, unread_after=False,
           outcome="accepted"):
    """One paper trade as scripts/paper.py records it: three rows, one id."""
    before = {"at": at, "sim_balance_usdc": f"{was:.2f}",
              "sim_total_trades": 0, "positions": positions[0]}
    after = {"at": at, "sim_balance_usdc": f"{now:.2f}",
             "sim_total_trades": 0}
    if not unread_after:
        after["positions"] = positions[1]
    return [
        {"id": trade_id, "type": "intent", "at": at, "usdc": usdc,
         "paper": True, "before": before},
        {"id": trade_id, "type": "outcome", "at": at, "outcome": outcome,
         "http_status": 200},
        {"id": trade_id, "type": "after", **after},
    ]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_paper_balance_judges_the_newest_trade_not_the_whole_log():
    """A fix cannot reach a row that was recorded before it shipped."""
    from tests.rest.test_paper_balance_moves import measurements, newest

    rows = (_trade("TRD-0001", "2026-09-10T11:41:45+00:00",
                   usdc=1.0, was=100000.0, now=100000.0, positions=(39, 40))
            + _trade("TRD-0002", "2026-09-10T19:41:45+00:00",
                     usdc=1.0, was=100000.0, now=99999.0, positions=(40, 41)))

    measured = measurements(rows)
    assert [m["id"] for m in measured] == ["TRD-0001", "TRD-0002"], (
        "the whole log is still the population -- the history does not stop "
        "being recorded, it stops being the verdict")

    subject = newest(measured)
    assert subject["id"] == "TRD-0002", (
        "the newest trade is the one that answers 'does a buy debit the "
        "balance NOW'; judging TRD-0001 answers 'did it ever fail', which is "
        "a question no fix can change the answer to")
    assert subject["moved"] == 1.0


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_paper_balance_newest_unreadable_never_falls_back_to_an_older_one():
    """Rule 8: a failed read is not an empty read, and it is not a licence to
    judge the trade before it. Falling back here would report the vendor's
    defect again off a pre-fix row, with a fresh timestamp on the claim."""
    from tests.rest.test_paper_balance_moves import measurements, newest

    rows = (_trade("TRD-0001", "2026-09-10T11:41:45+00:00",
                   usdc=1.0, was=100000.0, now=100000.0, positions=(39, 40))
            + _trade("TRD-0002", "2026-09-10T19:41:45+00:00",
                     usdc=1.0, was=100000.0, now=99999.0, positions=(40, 41),
                     unread_after=True))

    subject = newest(measurements(rows))
    assert subject["id"] == "TRD-0002", (
        "the newest trade is the subject whether or not it could be read; "
        "picking the newest READABLE one is the fallback that re-reports a "
        "pre-fix trade")
    assert subject["unread"] == ["after"], (
        "and it must carry why it could not be read, so the check can say "
        "Inconclusive instead of counting a missing key as zero")

    # The THIRD path, found 2026-09-12 and voted real by two of three readers.
    # `paper.py` writes outcome "unknown" on a timeout, on a non-2xx, and on a
    # 2xx carrying no position id -- its own message says "the order may have
    # landed". Dropping those handed the verdict to the previous ACCEPTED
    # trade, which today is TRD-0006 of 2026-09-10: a pre-fix row published
    # under a run dated now, the exact sentence this function prevents on the
    # other two paths.
    rows = (_trade("TRD-0001", "2026-09-10T11:41:45+00:00",
                   usdc=1.0, was=100000.0, now=100000.0, positions=(39, 40))
            + _trade("TRD-0010", "2026-09-12T19:41:45+00:00",
                     usdc=1.0, was=100000.0, now=99999.0, positions=(40, 41),
                     outcome="unknown"))

    subject = newest(measurements(rows))
    assert subject["id"] == "TRD-0010", (
        "an order whose outcome we could not read is not an order that did "
        "not happen; dropping it re-reports a pre-fix trade as today's newest")
    assert "outcome" in subject["unread"], subject

    # A REFUSED order genuinely did not happen and stays out.
    rows = (_trade("TRD-0001", "2026-09-10T11:41:45+00:00",
                   usdc=1.0, was=100000.0, now=100000.0, positions=(39, 40))
            + _trade("TRD-0011", "2026-09-12T20:41:45+00:00",
                     usdc=1.0, was=100000.0, now=100000.0, positions=(40, 40),
                     outcome="refused"))
    assert newest(measurements(rows))["id"] == "TRD-0001", (
        "a refused order is not an unreadable one")

    # The other read the same trade depends on: the BALANCE. _snapshot writes
    # `sim_balance_usdc` only on a 200 from /account/me, and until the deep
    # pass of 2026-09-11 measurements() dropped a trade without one, so a
    # failed account read handed the verdict to the pre-fix TRD-0001 -- this
    # test covered only the positions side. Two auditors found it separately.
    rows = (_trade("TRD-0001", "2026-09-10T11:41:45+00:00",
                   usdc=1.0, was=100000.0, now=100000.0, positions=(39, 40))
            + _trade("TRD-0009", "2026-09-11T19:41:45+00:00",
                     usdc=1.0, was=100000.0, now=99999.0, positions=(40, 41)))
    for row in rows:
        if row["id"] == "TRD-0009" and row.get("type") == "after":
            row.pop("sim_balance_usdc", None)
    subject = newest(measurements(rows))
    assert subject is not None and subject["id"] == "TRD-0009", (
        "a newest trade whose balance could not be read dropped out, and the "
        "verdict went to the pre-fix trade before it")
    assert "balance" in subject["unread"], subject


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_close_is_not_read_as_a_buy_that_debited_nothing():
    """`paper.jsonl` gains a second kind of chain, and #87 reads all of them.

    A close is written into the same log as a buy -- deliberately, because it
    is the same campaign and `book()` reads both -- and it has the same three
    row types under one id. To #87 that is indistinguishable from a paper buy,
    and the wrong way round: a close CREDITS the balance, so `moved` comes out
    negative and the position count goes DOWN. It would be filtered out of
    `landed` and, on a day when the newest chain is a close, would make the
    check judge a row that answers a different question.

    Rows written before this existed carry no `kind` at all, so absent means
    buy. Pinning that here rather than in the reader: the default is the part
    that silently changes meaning when somebody adds a third kind.
    """
    from tests.rest.test_paper_balance_moves import measurements

    rows = (_trade("TRD-0003", "2026-09-10T20:05:00+00:00",
                   usdc=1.0, was=100000.0, now=99999.0, positions=(41, 42))
            + _trade("TRD-0004", "2026-09-10T21:00:00+00:00",
                     usdc=1.0, was=99999.0, now=100000.4, positions=(42, 41)))
    for row in rows:
        if row["id"] == "TRD-0004" and row["type"] == "intent":
            row["kind"] = "close"

    measured = measurements(rows)
    assert [m["id"] for m in measured] == ["TRD-0003"], (
        "a close was read as a buy; its credit reads as a negative debit and "
        "its position count goes down, so it answers the opposite question")


def _close(trade_id, at, *, notional, expected_pnl, credited, pnl_booked):
    """One close as scripts/paper.py records it."""
    before = {"sim_balance_usdc": "100000.00", "sim_total_pnl": "0.00"}
    after = {"sim_balance_usdc": f"{100000.0 + credited:.6f}",
             "sim_total_pnl": f"{pnl_booked:.6f}"}
    return [
        {"id": trade_id, "type": "intent", "at": at, "kind": "close",
         "notional_usdc": notional, "unrealized_pnl_usdc": expected_pnl,
         "before": before},
        {"id": trade_id, "type": "outcome", "at": at, "kind": "close",
         "outcome": "accepted", "http_status": 200},
        {"id": trade_id, "type": "after", "at": at, "kind": "close", **after},
    ]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_close_check_can_be_red_for_the_state_it_names():
    """A check that cannot fail is nine of the ones this repo has written.

    Both halves, and the conditional one is the half that would have produced
    a false report: TRD-0004 closed for +0.0022 and total_pnl stayed 0.00,
    which is right, because their field is published to two decimals. A check
    demanding movement there reports arithmetic as a defect.
    """
    from tests.rest.test_paper_close_returns_the_money import closes

    # The real TRD-0005: 1.00 position that had lost 0.044, 0.96 back.
    good = closes(_close("TRD-0005", "2026-09-10T21:07:00+00:00",
                         notional=1.0, expected_pnl=-0.0438840707940783,
                         credited=0.96, pnl_booked=-0.04))
    assert len(good) == 1
    assert good[0]["credited"] == 0.96
    assert good[0]["pnl_booked"] == -0.04

    # The money did not come back. This is the state the check exists for.
    bad = closes(_close("TRD-0006", "2026-09-10T21:08:00+00:00",
                        notional=1.0, expected_pnl=-0.04,
                        credited=0.0, pnl_booked=0.0))
    assert bad[0]["credited"] == 0.0, (
        "a close that credited nothing must reach the verdict as zero, not "
        "be smoothed into the notional it was due")

    # Sub-cent, and the pnl half must not be judged on it.
    tiny = closes(_close("TRD-0004", "2026-09-10T21:05:00+00:00",
                         notional=1.0, expected_pnl=0.0021598811497629544,
                         credited=1.0, pnl_booked=0.0))
    assert abs(float(tiny[0]["expected_pnl"])) < 0.01

    # A buy is not a close, whatever else it looks like.
    assert closes(_trade("TRD-0003", "2026-09-10T20:05:00+00:00",
                         usdc=1.0, was=100000.0, now=99999.0,
                         positions=(41, 42))) == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_nexus_tools_judges_the_newest_answer_that_names_any():
    """The union across every answer ever recorded cannot go green either --
    and worse, widening the extractor re-reads old answers into new
    accusations. NEX-0002 named update_bot_settings at 10:23; the release was
    12:37; the fail went out at 16:52."""
    from tests.mcp.test_nexus_channel import newest_answer_naming_tools

    answers = [
        {"id": "NEX-0002", "type": "answer", "at": "2026-09-10T10:23:10+00:00",
         "text": "call `update_bot_settings(instance_id)` to enable trading"},
        {"id": "NEX-0008", "type": "answer", "at": "2026-09-10T13:18:42+00:00",
         "text": "call `get_event_card_info(card_id)` first"},
    ]
    assert newest_answer_naming_tools(answers)["id"] == "NEX-0008"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_nexus_tools_skips_a_newest_answer_that_names_no_tool():
    """Not the newest answer -- the newest that names a tool. An answer about
    fees names none, and reading that as 'nothing to measure' would turn the
    check Inconclusive every time Nexus happened to answer in prose, which is
    a check that stops measuring for a reason that is not about the vendor."""
    from tests.mcp.test_nexus_channel import newest_answer_naming_tools

    answers = [
        {"id": "NEX-0002", "type": "answer", "at": "2026-09-10T10:23:10+00:00",
         "text": "call `update_bot_settings(instance_id)` to enable trading"},
        {"id": "NEX-0008", "type": "answer", "at": "2026-09-10T13:18:42+00:00",
         "text": "call `get_event_card_info(card_id)` first"},
        {"id": "NEX-0009", "type": "answer", "at": "2026-09-10T20:00:00+00:00",
         "text": "Fees are 2% round trip and slippage is about 0.5%."},
    ]
    assert newest_answer_naming_tools(answers)["id"] == "NEX-0008"
    assert newest_answer_naming_tools([]) is None


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_label_does_not_excuse_a_tool_the_reader_cannot_call(monkeypatch):
    """The carve-out this replaces was built on a sentence they withdrew.

    REPLY-0034 at 12:55 on 2026-09-20 shipped a label -- `[NEXUS runs this for
    you on request; it is not an MCP tool]` -- and closed: *"If you see one
    named as something to call and UNLABELLED, that is a defect."* So the
    check learned to accept a labelled unreachable name.

    REPLY-0035 at 13:49, fifty-four minutes later, shipped the fix at the
    source and closed: *"If NEXUS recommends a tool you cannot call, LABELLED
    OR NOT, that is a defect: send me the text."* I had read point 4 of that
    message and not the sentence after it. Both are in the journal, so this
    was not information we lacked -- it was information we did not read.

    Two of three triage readers called the carve-out real, and the third only
    disagreed about whether the trust-level half survives. It does not either:
    a tool above our level is a tool we cannot call, which is the sentence
    verbatim.

    So there is no label case, the helper is gone, and this test exists to
    stop it coming back. Every shape they have shipped is listed and every one
    of them still fails.
    """
    from tests.mcp import test_nexus_channel
    from tests.mcp.test_nexus_channel import tool_mentions

    assert not hasattr(test_nexus_channel, "labelled"), (
        "the carve-out is back. Their own resolution is that a labelled tool "
        "the reader cannot call is still a defect (REPLY-0035); a label "
        "changes what THEY owe, not what we measure")

    marker = "[NEXUS runs this for you on request; it is not an MCP tool]"
    tiered = "[needs MCP trust level: recognized]"
    for text in (f"call `identify_address(addr)` {marker} before you trade",
                 f"call `update_bot_settings(id)` {tiered}",
                 "call `identify_address(addr)` to check the counterparty"):
        assert "identify_address" in tool_mentions(text) or \
               "update_bot_settings" in tool_mentions(text), (
            f"the name must still be COLLECTED whatever follows it, or the "
            f"check cannot hold it against the served list: {text[:60]}")

    # Both assertions above hold a helper; neither reaches the verdict. An
    # inline carve-out there -- `if "not an MCP tool" in latest["text"]:
    # missing = []` -- stayed green under both (B15, deep pass of 2026-09-21).
    # So the check is driven whole, the recorded answer and the served list
    # stubbed, and every shape has to come out FAILED naming its tool.
    import contextvars

    class Recorded:
        def __init__(self, text):
            self.rows = [{"id": "NEX-0900", "type": "answer",
                          "at": "2026-09-20T13:49:00+00:00", "text": text}]

        def load(self):
            return self.rows

        def path(self):
            return Path("nexus.jsonl")

    class Served:
        def tools_list(self):
            return [{"name": "place_order"}, {"name": "get_event_card_info"}]

    def drive(text):
        monkeypatch.setattr(test_nexus_channel, "_nexus", lambda: Recorded(text))
        check = test_nexus_channel.test_every_tool_nexus_tells_an_agent_to_call_exists
        # A context of its own, so the measurement the check concludes does not
        # land in this test's own run record.
        return contextvars.copy_context().run(check, Served())

    for text, tool in (
            (f"call `identify_address(addr)` {marker} before you trade",
             "identify_address"),
            (f"call `update_bot_settings(id)` {tiered}", "update_bot_settings"),
            ("call `identify_address(addr)` to check the counterparty",
             "identify_address")):
        with pytest.raises(AssertionError, match=tool):
            drive(text)
    # And the stub is not what fails them: a label beside a tool the server
    # does serve is no defect.
    assert drive(f"call `place_order(card)` {marker}") is None


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_latency_window_counts_questions_not_rows():
    """One question, one verdict. `nexus.py answer` re-polls a question it
    already gave up on and writes a give-up row of its own: on 2026-09-11 a
    manual re-poll of NEX-0020 wrote a second one, and the window of five
    counted that question twice -- the fail about to go to them on #86 would
    have said four of five had not answered when three had. A question given
    up on and answered later answered, late; its last row is its verdict."""
    from tests.mcp.test_nexus_channel import latest_per_question

    def row(nex, kind, at):
        return {"id": nex, "type": kind, "at": f"2026-09-11T{at}:00+00:00"}

    rows = [
        {"id": "NEX-0018", "type": "question", "at": "2026-09-11T05:26:00+00:00"},
        row("NEX-0018", "answer", "05:28"),
        row("NEX-0019", "answer", "05:45"),
        row("NEX-0020", "gave_up", "14:23"),
        row("NEX-0020", "gave_up", "14:25"),
        row("NEX-0021", "gave_up", "14:26"),
        row("NEX-0017", "gave_up", "14:30"),
        row("NEX-0017", "answer", "14:40"),
        row("NEX-0022", "gave_up", "15:11"),
        row("NEX-0023", "gave_up", "15:20"),
    ]
    finished = latest_per_question(rows)
    assert [r["id"] for r in finished] == [
        "NEX-0018", "NEX-0019", "NEX-0020", "NEX-0021", "NEX-0017",
        "NEX-0022", "NEX-0023"], "a question is counted once, at its last row"
    assert finished[2]["at"].startswith("2026-09-11T14:25"), (
        "a question's verdict is its LAST finished row")
    assert finished[4]["type"] == "answer", (
        "a question given up on and answered later is an answer, late")
    assert [r["type"] for r in finished[-5:]].count("gave_up") == 4


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_nexus_card_check_reads_only_ids_given_as_cards():
    """V01, deep pass of 2026-09-11, triage 3/3. The check fetched every UUID
    in the newest answer as a card, and the answers name UUIDs that are not
    cards: NEX-0015 a species ("species id `23441934...`"), NEX-0010 a
    backtest ("run_id 73b31f87..."). Either 404s on the card endpoint and
    would have gone to Cymetica as "Nexus tells an agent to trade" it. The
    #91 witness -- a card id in a table row of NEX-0012 -- must still count.
    And an answer a day old is not a current recommendation."""
    from datetime import datetime, timezone

    from tests.rest.test_nexus_cards_exist import card_ids_in, is_current

    species = "23441934-8475-4aa0-bbff-75c03ecd3284"
    run = "73b31f87-8825-4e19-b103-5a93aa67ad21"
    polygon = "5bd86126-90eb-4ad8-8e55-909397dab402"
    btc = "d432f8cd-dc3f-4563-ab44-07e34dbd2a0a"
    text = (f"read this session (species id `{species}`, strategy_type ...)\n"
            f"(`source: backtest_results`, `run_id {run}`, ran 2026-03-15)\n"
            f"| **Polygon Layer-2...** | `{polygon}` / EVCDX-POLYGON | 95.7% ETH |\n"
            f"1) BTC card -- id {btc} (\"Bitcoin's latest hack...\")")
    assert card_ids_in(text) == [polygon, btc], card_ids_in(text)

    now = datetime(2026, 9, 11, 16, 0, tzinfo=timezone.utc)
    assert is_current("2026-09-11T05:42:12+00:00", now)
    assert not is_current("2026-09-10T15:59:00+00:00", now)
    assert not is_current(None, now), "an answer with no moment is not current"

    # Evidence, not vocabulary. A blocklist can only name what has already gone
    # wrong once, and two of three readers reproduced the next one on
    # 2026-09-12: "trade_id `<uuid>`" and "clone `<uuid>`" both came back as
    # cards, and both are ids their platform really issues -- trade_id appears
    # nine times in our own samples.jsonl. A 404 on one of those sends Cymetica
    # a claim about something that was never a card.
    from tests.rest.test_nexus_cards_exist import known_non_cards

    for phrase in ("trade_id `085f1969-cd9e-449b-990a-3f7731b9a309`",
                   "your clone `d778102d-cd9e-449b-990a-3f7731b9a309`",
                   "backtest `085f1969-cd9e-449b-990a-3f7731b9a30a`",
                   "strategy id `085f1969-cd9e-449b-990a-3f7731b9a30b`"):
        assert card_ids_in(phrase) == [], (
            f"{phrase.split()[0]!r} reads as a card, and a 404 on it would go "
            f"to the vendor as guidance they failed to serve")

    # And the default is untouched: no marker still means a card, which is what
    # keeps #91's witness alive.
    assert card_ids_in("EVCDX-POLYGON `5bd86126-90eb-4ad8-8e55-909397dab402`") \
        == ["5bd86126-90eb-4ad8-8e55-909397dab402"]
    assert isinstance(known_non_cards(), set)

    # V08, deep pass of 2026-09-19 (3/3): the markers were SUBSTRINGS anywhere
    # in the 48 characters before the id, so the very words that introduce a
    # recommended card dropped it -- "Trade this card", "Buy both" (b-o-t),
    # "open a position in", a backtest figure in the same table row -- and an
    # invented card named that way was never checked. A marker labels the id:
    # it is the word right before it (or before its "id").
    card = "30408a4b-8717-4fc7-a91a-9a6724cadd7e"
    for phrase in (f"Trade this card: {card}",
                   f"Buy both {card} and hold",
                   f"open a position in {card}",
                   f"| backtest +42.5% | `{card}` |",
                   f"the strategy I would run: `{card}`"):
        assert card_ids_in(phrase) == [card], phrase


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_close_with_no_vendor_figures_is_not_a_close_that_paid_nothing():
    """V08, deep pass of 2026-09-13, triage 3/3. Two `.get` defaults on fields
    only the vendor controls.

    `proceeds_usdc` comes off their close response and `unrealized_pnl_usdc`
    off their position row. With the pnl absent, `float(... or 0)` made the
    estimate the bare notional -- so a CORRECT close of a position that lost
    0.05 on a 1.00 notional credited 0.95 and read `failed`, with the reason
    "a book that debits on the way in and does not credit on the way out reads
    every strategy as losing money". There is no filed row on this check, so
    that is a NEW report, about a defect that does not exist. The same None
    also made `result` 0, so `measurable` went False and the P&L half was
    silently waived in the same run.

    A missing field is not a zero result. `qa/measure.py::required` exists for
    exactly this, and rule 8 is the same sentence about reads.
    """
    from qa.marks import Inconclusive as Inc
    from tests.rest.test_paper_close_returns_the_money import judge

    honest = {"notional": 1.00, "expected_pnl": -0.05, "proceeds": None,
              "credited": 0.95, "pnl_booked": -0.05}
    assert judge(honest)["returned"], judge(honest)

    # The same close, with their two fields gone.
    blind = {**honest, "expected_pnl": None, "proceeds": None}
    try:
        judge(blind)
    except Inc as stopped:
        assert "not a zero" in str(stopped) or "nothing to judge" in str(stopped)
    else:
        raise AssertionError(
            "a close whose vendor figures are absent was judged anyway, and "
            "0.95 against a bare 1.00 notional is a fail sent about nothing")

    # V09, deep pass of 2026-09-19 (3/3): with THEIR proceeds present and only
    # the P&L field gone, the result was taken as 0 and the P&L half waived --
    # the waiver the docstring above calls a defect, left in this branch. Their
    # proceeds against the notional ARE the result: a 2.00 loss that total_pnl
    # never booked must not pass.
    lost = {"notional": 10.00, "expected_pnl": None, "proceeds": 8.00,
            "credited": 8.00, "pnl_booked": 0.00}
    said = judge(lost)
    assert said["returned"] and said["measurable"], said
    assert not said["booked"], (
        "a 2.00 loss their total_pnl never moved for was counted as booked")
    booked = judge({**lost, "pnl_booked": -2.00})
    assert booked["booked"], booked


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_window_label_is_checked_against_the_points_it_came_with():
    """V03, deep pass of 2026-09-13, triage 3/3. "Not the number we asked for"
    was being read as "a reading of what we got".

    B04 fixed the first half on 2026-09-12: a key name is not an answer, and
    `effective_period_days: 365` echoed back for a 365-day request is the
    defect restated. What it left standing is that ANY other number passed,
    and a date was exempted from the value test entirely -- while `n_points`
    sat unused in the same dict. Two inputs that violate the contract and
    passed:

        {"n_points": 120, "period_days": 365, "covered_days": 180}
        {"n_points": 120, "period_days": 365, "start_date": "2025-09-13"}

    The first names a window twice what the points support; the second echoes
    the requested range as dates. A pass on #99 has already been sent.

    The control basket gives the points-per-day, so the claim is checkable:
    a label that disagrees with the points is not a reading of them.
    """
    from tests.mcp.test_backtest_window_is_real import says_covered

    # One point a day, from a control that returned 362 points for 365 days.
    per_day = 362 / 365

    assert says_covered({"n_points": 120, "period_days": 365,
                         "covered_days": 120}, 365, per_day) == ["covered_days"]
    assert says_covered({"n_points": 120, "period_days": 365,
                         "covered_days": 180}, 365, per_day) == [], (
        "a window twice what the points support is not a reading of them")
    assert says_covered({"n_points": 120, "period_days": 365,
                         "effective_period_days": 365}, 365, per_day) == [], (
        "the echoed argument must still be refused")

    # A date is read the same way: the span it implies against the points.
    from datetime import date, timedelta

    honest = (date.today() - timedelta(days=120)).isoformat()
    stale = (date.today() - timedelta(days=365)).isoformat()
    assert says_covered({"n_points": 120, "start_date": honest},
                        365, per_day) == ["start_date"]

    # V02, deep pass of 2026-09-19 (3/3): their own house style is words and
    # blocks -- the leaderboard serves "48h" and "6 months", and #97's fix
    # arrived as `period: {start, end, hours, label: "19.8 days"}`. A correct
    # repair of #99 in any of these shapes read None, and the check FAILED on
    # a fixed defect.
    assert says_covered({"n_points": 120, "actual_window": "121 days"},
                        365, per_day) == ["actual_window"]
    assert says_covered({"n_points": 120, "days_covered": 120},
                        365, per_day) == ["days_covered"]
    assert says_covered({"n_points": 120, "window": {
        "start": honest, "end": date.today().isoformat()}},
        365, per_day) == ["window"]
    assert says_covered({"n_points": 120, "period": {
        "hours": 120 * 24, "label": "120 days"}}, 365, per_day) == ["period"]
    # And the same shapes still have to agree with the points.
    assert says_covered({"n_points": 120, "actual_window": "365 days"},
                        365, per_day) == [], "the request echoed in words"
    assert says_covered({"n_points": 120, "window": {"start": None,
                                                    "end": None}},
                        365, per_day) == [], "an empty block is not a window"
    assert says_covered({"n_points": 120, "start_date": stale},
                        365, per_day) == [], (
        "the requested range echoed as dates is the same defect in another "
        "type, and was exempted from the value test entirely")

    # Without a control there is nothing to check the label against, and a
    # claim we cannot refute is not one we may call false (rule 8). The LIVE
    # check always has a control -- it raises Inconclusive when the two
    # windows cannot be told apart -- so this path is the offline callers.
    assert says_covered({"n_points": 120, "covered_days": 180}, 365, None)         == ["covered_days"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_nexus_card_check_claims_only_that_the_card_was_named():
    """V07, deep pass of 2026-09-13, triage 3/3. The reason said more than the
    extractor read.

    `card_ids_in` and `known_non_cards` both answer "is this a card id". Neither
    answers "was it offered as a trade", and the reason asserted the second:
    "Nexus answer NEX-xxxx **tells an agent to trade** <uuid>". NEX-0027 is a
    live instance -- it says *"skip it as a long this week"* immediately before
    `09a41890-51c2-4fa9-8bb8-43e7f9bf4930`, so a 404 on that card would have
    gone to #91 quoting them as telling an agent to trade a card they told it
    to skip.

    The repair is the claim, not the extractor. A card id that a current
    recommendation NAMES and that does not exist is a defect whichever side of
    the sentence it was on -- an agent cannot tell the avoided card from the
    recommended one if neither resolves. Adding a negation vocabulary would be
    the same blocklist the file's own `known_non_cards` docstring warns about:
    it can only ever name what has already gone wrong once.
    """
    import inspect

    from tests.rest import test_nexus_cards_exist as check

    source = inspect.getsource(
        check.test_every_card_nexus_tells_an_agent_to_trade_exists)
    # Comments out, because the comment that RECORDS this repair quotes the
    # old wording -- the first draft of this assertion was defeated by the
    # very sentence explaining it.
    code = "\n".join(line for line in source.splitlines()
                     if not line.lstrip().startswith("#"))
    assert "tells an agent to trade" not in code, (
        "the reason still asserts trade-ness, which nothing in the check reads")
    assert "names " in code, "the reason must say what was actually read"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_latency_window_is_ordered_by_question_and_counts_only_their_failures():
    """V04, deep pass of 2026-09-11, triage 3/3: two ways the #86 window,
    repaired that afternoon, could still say something false. It ordered
    questions by their LAST row, so re-polling an old failed question -- which
    appends a give-up -- moved it into the newest five. And every give-up read
    as "did not answer", including the fifteen-minute one written when OUR
    reads failed ('unread: ReadTimeout', 'unknown').

    B01/B03, deep pass of 2026-09-12, triage 3/3: the repair went one status
    too far. `nexus.py` writes a give-up at 900 s carrying the status its last
    poll saw, and when THEIR job is still working that status is `running` --
    not `failed`. So five questions each abandoned at fifteen times three the
    published ceiling were filed as our own read failures, `verdicts` held no
    answer at all, the Inconclusive guard needed a non-empty one to fire, and
    the check reported PASSED: "0 investigation(s) answered inside the
    published 1-5 min". That verdict goes to their server on #86.

    Both halves are asserted here because either alone leaves the false green:
    counting a stalled give-up as theirs is what makes the window red, and
    refusing to conclude from nothing is what stops a window of pure read
    failures reporting a working channel."""
    from tests.mcp.test_nexus_channel import (did_not_answer,
                                              latest_per_question,
                                              read_the_window,
                                              their_published_window)

    rows = [
        {"id": "NEX-0005", "type": "question", "at": "2026-09-10T11:49:00+00:00"},
        {"id": "NEX-0005", "type": "gave_up", "at": "2026-09-10T12:00:00+00:00",
         "status": "failed"},
        {"id": "NEX-0021", "type": "question", "at": "2026-09-11T14:25:29+00:00"},
        {"id": "NEX-0021", "type": "gave_up", "at": "2026-09-11T14:26:53+00:00",
         "status": "failed"},
        {"id": "NEX-0022", "type": "question", "at": "2026-09-11T15:10:08+00:00"},
        {"id": "NEX-0022", "type": "answer", "at": "2026-09-11T15:12:00+00:00"},
        # a manual re-poll of the old question, appended last
        {"id": "NEX-0005", "type": "gave_up", "at": "2026-09-11T16:00:00+00:00",
         "status": "failed"},
    ]
    assert [r["id"] for r in latest_per_question(rows)] == [
        "NEX-0005", "NEX-0021", "NEX-0022"], (
        "a re-polled old question moved to the newest end of the window")

    assert did_not_answer({"type": "gave_up", "status": "failed"})
    assert did_not_answer({"type": "gave_up", "status": "running"}), (
        "a job still running when we stopped waiting did not answer either -- "
        "that is the status nexus.py writes at GIVE_UP_SECONDS")
    assert did_not_answer({"type": "gave_up", "status": "queued"})
    assert not did_not_answer({"type": "gave_up", "status": "unread: ReadTimeout"}), (
        "our own read failing for fifteen minutes is not their channel failing")
    assert not did_not_answer({"type": "gave_up", "status": "unknown"})
    assert not did_not_answer({"type": "answer"})

    # B01: a window in which nothing about THEIR channel was measured.
    def window(status, stopped_at="2026-09-12T10:15:00+00:00"):
        rows = []
        for n in range(1, 6):
            qid = f"NEX-01{n:02d}"
            rows += [{"id": qid, "type": "question", "at": "2026-09-12T10:00:00+00:00"},
                     {"id": qid, "type": "poll", "at": "2026-09-12T10:14:30+00:00",
                      "status": "running" if status in ("running", "queued") else status},
                     {"id": qid, "type": "gave_up", "at": stopped_at, "status": status}]
        return rows, latest_per_question(rows)

    read = read_the_window(*window("running"))
    assert read["stalled"], (
        "five questions abandoned at 15 min, each polled still running at "
        "14.5 min against a published 5, and the check found no trouble")
    assert not read["ours"]
    assert not read["proves_nothing"]

    read = read_the_window(*window("unread: ReadTimeout"))
    assert not read["stalled"] and not read["failed"] and not read["late"]
    assert len(read["ours"]) == 5
    # The decision itself, not the ingredient: nothing here measures their
    # channel, so the run is inconclusive -- and it reported a PASS.
    assert read["proves_nothing"], (
        "a window of nothing but our own failed reads is not a channel "
        "answering inside its published window")

    # V01, deep pass of 2026-09-19 (3/3). Since their deep lane QUEUES at
    # capacity (REPLY-0019) the loop looks once per tick and writes no
    # give-up, so a question still queued had no finishing row and never
    # entered the window -- which then judged the five before it and could
    # PASS while a poll had seen the job waiting far past their ceiling.
    from tests.mcp.test_nexus_channel import open_past_the_ceiling

    queued = [{"id": "NEX-0200", "type": "question",
               "at": "2026-09-19T15:00:00+00:00"},
              {"id": "NEX-0200", "type": "poll", "at": "2026-09-19T15:40:00+00:00",
               "status": "queued"},
              {"id": "NEX-0201", "type": "question",
               "at": "2026-09-19T15:38:00+00:00"},
              {"id": "NEX-0201", "type": "poll", "at": "2026-09-19T15:40:00+00:00",
               "status": "queued"}]
    open_rows = open_past_the_ceiling(queued, 5 * 60)
    assert [r["id"] for r in open_rows] == ["NEX-0200"], (
        "only a job SEEN still waiting past the ceiling counts; two minutes in "
        "is merely early")
    read = read_the_window(queued + open_rows,
                           latest_per_question(queued + open_rows))
    assert [qid for qid, _ in read["stalled"]] == ["NEX-0200"], read

    # B02, same pass, triage 3/3: the ceiling is ours, transcribed, while the
    # check told the vendor the contract was their own tool description. A
    # relabel to 5-15 min would have sent a FAIL on #86 for behaviour inside
    # their published window. Their label is now re-read from the newest
    # acknowledged tools/list, and a disagreement is inconclusive -- never a
    # defect, and never adopted silently either (rule 5).
    from tests.mcp.test_nexus_channel import _nexus

    labelled = "Starts an investigation that typically takes {}."
    assert their_published_window(
        [{"name": "ask_nexus_deep", "description": labelled.format("5-15 minutes")}]
    ) == (5, 15)
    assert their_published_window(
        [{"name": "other", "description": labelled.format("1-5 minutes")}]) is None
    # A label READ that no longer states an N-M window is not a label we
    # failed to read: it moved to a shape we do not parse. Returning None for
    # it let #86 carry on with the transcribed 1-5 and send a 7-minute answer
    # to their tracker as a FAIL (C01, deep pass of 2026-09-19, 2/3).
    assert their_published_window([{"name": "ask_nexus_deep",
                                    "description": "usually completes in under "
                                                   "10 minutes"}]) == "unstated"
    assert their_published_window([{"name": "ask_nexus_deep"}]) == "unstated"
    assert their_published_window([]) is None, (
        "no reading of the tool at all is still a read that failed")
    # Whether their CURRENT label still agrees with our transcription is a
    # question about the repository against their platform, so it is asserted
    # in tests/repo/test_surface_drift.py, not here. A red test in this
    # directory aborts the whole suite -- so putting it here would mean that
    # the vendor rewording a sentence, and the operator doing exactly what the
    # reminder tells them (`processes.py surface --update`), kills every live
    # request until somebody edits a constant.


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_summary_may_account_for_positions_by_counting_them():
    """V05, deep pass of 2026-09-11, triage 3/3. The check's own comment says
    the scope must account for event-card positions "either by counting it or
    by naming it as excluded", and only naming passed -- so a fix that folds
    event cards INTO the counters would have been filed as unaccounted
    positions, #83's shape on the same endpoint."""
    from tests.rest.test_portfolio_summary import accounts_for

    assert accounts_for({"counters_cover": "WTA bets and event-card positions",
                         "counters_do_not_cover": []}) == "counted"
    assert accounts_for({"counters_cover": "on-chain WTA bets",
                         "counters_do_not_cover": [
                             "event-card positions (GET /api/v1/event-cards/positions)"]}) == "named"
    assert accounts_for({"counters_cover": "on-chain WTA bets, not event-card positions",
                         "counters_do_not_cover": []}) is None, (
        "a sentence that says event cards are NOT counted is not counting them")
    assert accounts_for({"counters_cover": "on-chain WTA bets",
                         "counters_do_not_cover": []}) is None
    # A12, deep pass of 2026-09-22: a mention with no negation word is not a
    # count. Pointing the reader somewhere else, or limiting the counters to
    # something else, leaves event cards out as surely as "not" does -- and
    # that is the exclusion STATED, so states_exclusion says yes.
    from tests.rest.test_portfolio_summary import states_exclusion

    for pointed in ("only on-chain WTA bets; event-card positions are shown "
                    "on the Cards tab",
                    "WTA bets. For event-card positions see "
                    "/api/v1/event-cards/positions"):
        scope = {"counters_cover": pointed, "counters_do_not_cover": []}
        assert accounts_for(scope) is None, pointed
        assert states_exclusion(scope), pointed
    assert accounts_for({"counters_cover": "only trades, bots and event-card "
                                           "positions",
                         "counters_do_not_cover": []}) == "counted"

    # V10, deep pass of 2026-09-19 (3/3): and a scope that COUNTS them was
    # then failed for not saying where else to read them -- a pointer is owed
    # for a population left OUT, and nothing is left out. #83's shape again.
    from tests.rest.test_portfolio_summary import scope_problems

    counted = {"counters_cover": "trades, bots and event-card positions",
               "counters_do_not_cover": []}
    assert scope_problems(counted, {"scope": counted}, 3) == []
    # Vague is not counted: "summarized elsewhere" leaves them out, and the
    # reader is owed the endpoint (V09 of 2026-09-13 stands).
    elsewhere = {"counters_cover": "WTA bets; event-card activity is "
                                   "summarized elsewhere",
                 "counters_do_not_cover": []}
    assert scope_problems(elsewhere, {"scope": elsewhere}, 3), (
        "a population summarized elsewhere without saying where passed")
    named = {"counters_cover": "WTA bets",
             "counters_do_not_cover": ["event-card positions"]}
    assert scope_problems(named, {"scope": named}, 3)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_schema_we_could_not_read_is_not_a_tool_that_takes_nothing():
    """V09, deep pass of 2026-09-11, triage 3/3. `inputSchema or {}` read a
    listing with no schema -- or a permissive one without `properties` -- as a
    tool that takes no arguments, and would have filed that as their defect.
    Rule 8 inverted. Only a schema that says `properties: {}` takes nothing."""
    from tests.mcp.test_nexus_tool_contracts import served_arguments

    assert served_arguments({"name": "x"}) is None
    assert served_arguments({"name": "x", "inputSchema": {
        "type": "object", "additionalProperties": True}}) is None
    assert served_arguments({"name": "x", "inputSchema": {
        "type": "object", "properties": {}}}) == []
    assert served_arguments({"name": "x", "inputSchema": {
        "type": "object", "properties": {"b": {}, "a": {}}}}) == ["a", "b"]

    # V11, deep pass of 2026-09-19 (3/3): the check then PASSED over nothing.
    # Every tool the answer calls unserved (#85's case), or served with a
    # schema that does not say, left nothing measured -- and the reason said
    # "every one of the N tool(s) declares parameters".
    from tests.mcp.test_nexus_tool_contracts import argless_among

    described = {"foo_bar": "x=1", "baz_qux": "y=2"}
    argless, measured = argless_among(described, {"baz_qux": None})
    assert argless == [] and measured == [], "nothing here was measured"
    argless, measured = argless_among(described, {"foo_bar": ["x"],
                                                  "baz_qux": []})
    assert [a["tool"] for a in argless] == ["baz_qux"]
    assert measured == ["baz_qux", "foo_bar"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_internal_module_path_counts_without_its_line_number():
    """V12, deep pass of 2026-09-11, triage 2/3. #92's subject is internal
    source paths, line numbers and code, and the check wanted `file.py:NNN`
    only -- while NEX-0015 names src/api/routes/agent_species.py with no line
    number. A fix that stripped `:NNN` and kept the paths would have read
    VERIFIED FIXED. Our own scripts/... in a question must still not trip it."""
    from tests.mcp.test_nexus_does_not_quote_source import source_locations

    text = ("the schema carries it (`src/api/routes/agent_species.py`) and "
            "src/services/wta_payout_service.py:272 computes it; our "
            "scripts/paper.py records it")
    assert source_locations(text) == ["src/api/routes/agent_species.py",
                                      "src/services/wta_payout_service.py:272"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_open_stake_we_cannot_read_is_not_nothing_open():
    """V13, deep pass of 2026-09-11, triage 3/3. The #94 check, repaired that
    afternoon, read an open trade with no amount as a stake of 0 and an
    is_closed of None as neither open nor closed -- so if their arena lane
    renamed its amount field, the 55.00 leg would read "nothing open" and
    #94 would pass to VERIFIED FIXED. Its own docstring: a read that fails
    skips that bot rather than counting as zero."""
    from tests.rest.test_clone_books_its_open_positions import open_stake

    legs = [{"is_closed": False, "amount_usdc": "55.000000"},
            {"is_closed": False, "amount_usdc": "100.000000"},
            {"is_closed": True, "amount_usdc": "25.000000", "profit_usdc": "-25"}]
    assert open_stake(legs) == 155.0
    assert open_stake([{"is_closed": False}]) is None, (
        "an open trade with no amount we can read is not a stake of zero")
    assert open_stake([{"is_closed": None, "amount_usdc": "55"}]) is None, (
        "a trade that is neither open nor closed cannot be summed either way")
    assert open_stake([]) == 0.0

    from tests.rest.test_clone_books_its_open_positions import realized

    assert realized(legs) == -25.0
    assert realized([{"is_closed": True}]) is None, (
        "a closed trade whose result we cannot read did not make zero")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_listing_walk_says_when_it_did_not_reach_the_end():
    """T08 and V02, deep pass of 2026-09-11, triage 3/3. walk_listing returned
    the same thing for a finished walk and for one that stopped at its page
    cap, or on a page cut short while `total` said more -- and both checks
    that walk it then said a card was absent from "all N cards it hands out".
    The walk now reports whether it reached the end; its return is unchanged."""
    from tests.rest.test_event_card_listing_reaches_them import walk_listing

    cards = [{"id": f"c{i}"} for i in range(7)]

    def paged(params):
        start, size = int(params["offset"]), int(params["limit"])
        return 200, {"cards": cards[start:start + size], "total": len(cards)}

    report = {}
    seen, ignored = walk_listing(paged, limit=2, report=report)
    assert len(seen) == 7 and ignored is False and report["complete"] is True

    def cut_short(params):
        start = int(params["offset"])
        return 200, {"cards": cards[start:start + 1], "total": len(cards)}

    report = {}
    seen, ignored = walk_listing(cut_short, limit=2, report=report)
    assert report["complete"] is False, (
        "a page shorter than the limit while total says more is not the end")

    report = {}
    seen, ignored = walk_listing(paged, limit=2, max_pages=2, report=report)
    assert len(seen) == 4 and report["complete"] is False, (
        "a walk that stopped at its page cap did not reach the end")

    def stuck(params):
        return 200, {"cards": cards[:2]}

    report = {}
    walk_listing(stuck, limit=2, report=report)
    assert report["complete"] is False


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_field_named_with_via_or_through_is_not_a_tool():
    """V08, deep pass of 2026-09-11, triage 3/3. The calling verbs include
    with, via and through, and anything with an underscore is a name, so
    "filter with `is_public`" made is_public a tool Nexus told an agent to
    call -- and one that does not exist, filed as such. Those three are how
    NEX-0008 named a real tool ("resolve the chain with `find_trade_path`"),
    so they stay, for a name that is shaped like a tool: a verb first."""
    from tests.mcp.test_nexus_channel import tool_mentions

    assert tool_mentions("filter with `is_public` and pay via `reward_amount`, "
                         "read through `current_index`") == set()
    assert tool_mentions("resolve the chain with `find_trade_path`") == {"find_trade_path"}
    assert tool_mentions("call `update_bot_settings(instance_id)` to enable it") == {
        "update_bot_settings"}
    assert "get_event_card_info" in tool_mentions(
        "look it up via the `get_event_card_info` tool")

    # 2026-09-25: their tools/list now serves `fetch` and `search`, and the
    # check stood down (#85 inconclusive) because a single word could not be
    # read at all. A single word counts where the markup is strong -- MCP
    # prefix, a call signature, "the ... tool" -- and after a verb only when
    # it is shaped like one, so the directions and fields Nexus backticks in
    # calling phrases (`status`, `bull`, `bear`) stay out.
    assert tool_mentions("call MCP `search` for it") == {"search"}
    assert tool_mentions("then `fetch(id)` the record") == {"fetch"}
    assert tool_mentions("the `search` tool finds it") == {"search"}
    assert tool_mentions("use `fetch` on the id, or with `search`") == {"fetch", "search"}
    assert tool_mentions("use `bull` for up, with `status` = active, "
                         "call `bear` to go down") == set()


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_close_verdict_holds_its_own_contract():
    """T05 and V06, deep pass of 2026-09-11, triage 3/3. The close check's
    verdict lived inline, so the meta test above only ever drove closes():
    dropping the sub-cent condition turned TRD-0004 into a false fail with
    everything green. And the verdict itself: a two-cent fee failed as "does
    not credit", a P&L booked with the wrong sign counted as booked, and a
    close whose balance read failed dropped out and left an older close as
    the subject. judge() is the verdict now, and this drives it."""
    from tests.rest.test_paper_close_returns_the_money import closes, judge

    # A two-cent fee, which their own proceeds say: 9.98 due, 9.98 back.
    rows = _close("TRD-0010", "2026-09-11T10:00:00+00:00", notional=10.0,
                  expected_pnl=0.0, credited=9.98, pnl_booked=0.0)
    for row in rows:
        if row["type"] == "outcome":
            row["proceeds_usdc"] = 9.98
    assert judge(closes(rows)[-1])["returned"] is True, (
        "a close that returned exactly what they said it would is not a failure")

    # TRD-0004: a sub-cent result their 2dp total_pnl cannot show.
    sub = judge(closes(_close("TRD-0004", "2026-09-10T21:05:00+00:00", notional=1.0,
                              expected_pnl=0.0021598811497629544, credited=1.0,
                              pnl_booked=0.0))[-1])
    assert (sub["measurable"], sub["booked"]) == (False, True), sub

    # A -0.04 result booked as +0.04 is not booked.
    wrong = judge(closes(_close("TRD-0011", "2026-09-11T10:30:00+00:00", notional=1.0,
                                expected_pnl=-0.04, credited=0.96,
                                pnl_booked=0.04))[-1])
    assert wrong["booked"] is False, wrong

    # Nothing came back: the state the check exists for, still red.
    bad = judge(closes(_close("TRD-0006", "2026-09-10T21:08:00+00:00", notional=1.0,
                              expected_pnl=-0.04, credited=0.0, pnl_booked=0.0))[-1])
    assert bad["returned"] is False, bad

    # The newest close whose balance read failed stays the subject, unread.
    rows = (_close("TRD-0012", "2026-09-11T11:00:00+00:00", notional=1.0,
                   expected_pnl=0.0, credited=1.0, pnl_booked=0.0)
            + _close("TRD-0013", "2026-09-11T12:00:00+00:00", notional=1.0,
                     expected_pnl=0.0, credited=1.0, pnl_booked=0.0))
    for row in rows:
        if row["id"] == "TRD-0013" and row["type"] == "after":
            row.pop("sim_balance_usdc")
    newest = closes(rows)[-1]
    assert (newest["id"], newest["credited"]) == ("TRD-0013", None), (
        "a newest close whose balance could not be read dropped out")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_listing_check_walks_the_pages_it_is_now_allowed_to_walk():
    """#90 was fixed and our check could not have seen it.

    The check read one page of GET /api/v1/event-cards at limit=200, because on
    2026-09-10 offset, skip and page were all ignored and one page was all there
    was. Their release of 2026-09-11 ~04:35 made offset work and added a
    total -- and a check that reads one page cannot tell a card beyond the
    first 200 that is now reachable from one that is not. It went on failing,
    the fold opened correction_owed, and verify.py would have told them their
    fix did not hold. A check encodes the fix its author imagined.

    So the listing is walked by offset until `total` is reached. Where offset is
    still ignored -- the same first id comes back -- the walk stops and says so
    rather than looping, which is exactly what the check could see before.
    """
    from tests.rest.test_event_card_listing_reaches_them import walk_listing

    cards = [{"id": f"c{i}"} for i in range(5)]

    def paged(params):
        start, size = int(params.get("offset", 0)), int(params.get("limit", 2))
        return 200, {"cards": cards[start:start + size], "total": len(cards)}

    seen, ignored = walk_listing(paged, limit=2)
    assert [c["id"] for c in seen] == ["c0", "c1", "c2", "c3", "c4"]
    assert ignored is False

    def stuck(params):
        return 200, {"cards": cards[:2], "count": 2}

    seen, ignored = walk_listing(stuck, limit=2)
    assert [c["id"] for c in seen] == ["c0", "c1"]
    assert ignored is True, "an ignored offset must be named, not looped on"

    def broken(params):
        return 500, {}

    assert walk_listing(broken, limit=2) == (None, False), (
        "a failed read is not an empty market")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_listing_check_leaves_user_submissions_out_of_the_market():
    """A card the platform says is private to its author is not one the
    public listing owes anybody.

    On 2026-09-11 the walked listing -- all 6,880 cards, offset fixed -- still
    lacked one Nexus-named card, a4a5b71e, and verify.py was one command away
    from telling them their pagination fix did not hold. That card's
    source_url is user-submission://99/...; their own account of #91 is that a
    user-submitted card is "visible only to its author". So its absence from
    the listing is their design working. What is actually wrong about it --
    that account 113 can read it at all -- is a different defect with its own
    check, and blaming the listing for it would have been a false correction.
    """
    from tests.rest.test_event_card_listing_reaches_them import is_user_submission

    assert is_user_submission(
        {"source_url": "user-submission://99/37713611-70a3-40d6"}) is True
    assert is_user_submission(
        {"source_url": "https://www.globenewswire.com/news-release/x"}) is False
    assert is_user_submission({"source_url": None}) is False
    assert is_user_submission({}) is False
    assert is_user_submission(None) is False


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_disclosure_check_judges_the_newest_answer():
    """#92 was fixed at serve time, and our stored copies cannot show it.

    The check read every answer we had recorded and failed if any cited a
    source location. The three that did are from 2026-09-10 and live in our
    own nexus.jsonl; their fix scrubs an answer as it is SERVED, so it cannot
    reach a copy we already hold. Judging them for ever is the growing-log
    mistake this file already pins twice -- and here it would have sent a
    `fail` correction on a fix that works. The newest answer is the subject;
    the history stays in population.
    """
    from tests.mcp.test_nexus_does_not_quote_source import (
        source_locations, subject_answer)

    answers = [
        {"id": "NEX-0011", "type": "answer", "at": "2026-09-10T21:18:00+00:00",
         "text": "see src/api/dependencies.py:933 for the gate"},
        {"id": "NEX-0018", "type": "answer", "at": "2026-09-11T05:40:00+00:00",
         "text": "the withdrawal gate is fail-closed"},
    ]
    subject = subject_answer(answers)
    assert subject["id"] == "NEX-0018"
    assert source_locations(subject["text"]) == []
    assert subject_answer([]) is None


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_window_is_read_for_its_value_and_beside_its_own_sharpe():
    """#97's check was about to verify a fix on a key name alone.

    It collected every key ANYWHERE in the payload whose text contained one of
    twelve words, and never read the value. Three readers reproduced three ways
    through it on 2026-09-12, and the row was PASSING beside FIX_CLAIMED with
    `verification_owed: [97]` and nothing sent -- so the next verify run would
    have told Cymetica #97 was fixed on that assertion. This is the 2026-09-07
    class, in the hour before the claim went out.

    Three properties, and the third is the one a looser reading loses: the
    window must be NAMED as a whole key, must CARRY something, and must sit
    with the Sharpe it describes rather than in a neighbouring block about a
    different measurement.
    """
    from tests.rest.test_backtest_metrics_agree import (
        NAMES_THE_WINDOW, _says_a_window, _sharpe_context)

    def said(payload):
        return [k for node in _sharpe_context(payload)
                for k in _says_a_window(node)]

    assert not NAMES_THE_WINDOW.match("starting_capital_usdc"), (
        "a substring match on 'start' is what the sibling check already "
        "recorded making and fixing")

    assert said({"latest_metrics": {"sharpe_ratio": 5.16, "period": None}}) == [], (
        "a null window is the absence with a label on it")
    assert said({"latest_metrics": {"sharpe_ratio": 5.16},
                 "leaderboard": {"headline_period": "48h / 354 markets"}}) == [], (
        "a window on the leaderboard block is not a window on the tool's "
        "Sharpe -- that pairing IS the filed defect")
    assert said({"latest_metrics": {"sharpe_ratio": 5.16,
                                    "period": {"label": "30d"}}}) == ["period"]
    # V03, deep pass of 2026-09-19 (3/3): "carries something" was any
    # non-empty value, so a block with nothing in it passed, and so did the
    # size of a BAR -- which says nothing about the period a Sharpe covers.
    assert said({"latest_metrics": {"sharpe_ratio": 1.2, "period": {
        "start": None, "end": None}}}) == [], "an empty block is not a window"
    assert said({"latest_metrics": {"sharpe_ratio": 1.2,
                                    "interval": "1h"}}) == [], "a bar size"
    assert said({"latest_metrics": {"sharpe_ratio": 1.2,
                                    "timeframe": "1d"}}) == [], "a bar size"
    assert said({"latest_metrics": {"sharpe_ratio": 1.2, "period": {
        "start": "2026-08-31T00:00:00Z", "end": "2026-09-19T20:00:00Z",
        "hours": 476, "label": "19.8 days"}}}) == ["period"], (
        "their shipped fix for #97, verbatim in shape")
    assert said({"metrics": {"period_days": 30, "rows": [{"sharpe": 1.2}]}})         == ["period_days"], "a window one level up answers for the number under it"

    # B04, the same hour, the same class, the sibling file. Its own docstring
    # says "a loose match on a field NAME is the same mistake as reading a
    # number without its units", and it was making it: `says_covered` collected
    # key names and never looked at what they carried, so echoing the REQUESTED
    # window under a second name -- `effective_period_days: 365` beside 119
    # points -- would have read as the fix.
    from tests.mcp.test_backtest_window_is_real import says_covered

    assert says_covered({"period_days": 365, "effective_period_days": 365}, 365) == [], (
        "the requested window echoed under a second name is the defect "
        "restated, not the window actually covered")
    assert says_covered({"period_days": 365, "covered_days": None}, 365) == []
    assert says_covered({"period_days": 365, "covered_days": 119}, 365) == ["covered_days"]
    assert says_covered({"period_days": 365, "first_point": "2026-05-16"},
                        365) == ["first_point"], (
        "a date the points begin at reads the coverage even though it is not "
        "a number of days")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_refusal_is_read_off_the_failure_and_not_off_the_body():
    """The fourth mechanism again, on a check written the day the guide landed.

    `/guides/nexus-lab-loop` (2026-09-12) promises "The ground-truth tools need
    no key", so a check asked all three anonymously and looked for the
    vocabulary of authentication in what came back. Both
    `list_backtest_surfaces` and `get_backtest_models` answered `success: true`
    and were classified as refusing us -- because a surface's row names its own
    `auth`, which is precisely what their table says it will carry ("the
    question each answers, its API and auth"). The vocabulary of authentication
    is the SUBJECT of those two tools, so a body-wide match could only ever
    accuse them of what they were describing.

    It failed loudly, one command short of `submit.py`. This pins the shape:
    the words are read only once the structure says the call failed, and the
    body that fooled it is the first case below, verbatim in shape.
    """
    from tests.mcp.test_ground_truth_needs_no_key import failure_text

    def answer(inner):
        """Their envelope: a tool's payload, double-encoded inside content."""
        return {"jsonrpc": "2.0", "id": 1, "result": {
            "content": [{"type": "text", "text": json.dumps(inner)}]}}

    surfaces = answer({"success": True, "tool": "list_backtest_surfaces",
                       "result": {"surfaces": [
                           {"id": "bots", "page": "/backtest",
                            "api": "/api/v1/backtest/bots",
                            "auth": "none -- no API key required"}]}})
    assert failure_text(surfaces) is None, (
        "a tool that answered success: true has not refused anybody, however "
        "much of its own subject matter is the word auth")

    assert failure_text({"jsonrpc": "2.0", "id": 1, "error": {
        "code": -32601, "message": "Method not found"}}) is not None
    assert failure_text({"jsonrpc": "2.0", "id": 1, "result": {
        "isError": True,
        "content": [{"type": "text", "text": "unauthorized: send X-API-Key"}]}
    }) == "unauthorized: send X-API-Key"
    assert failure_text(answer({"success": False,
                                "error": "API key required"})) is not None, (
        "their tool-level failure lives inside the double encoding, and a "
        "check that only reads isError never sees it"
    )
    assert failure_text({"jsonrpc": "2.0", "id": 1, "result": "plain"}) is None

    # V12, deep pass of 2026-09-19 (2/3): a login wall in common words
    # matched neither pattern, was classed "failed on its own terms" -- we
    # were let in -- and the check PASSED "needs no key" on a tool that
    # turned an anonymous caller away.
    from tests.mcp.test_ground_truth_needs_no_key import REFUSED_FOR_AUTH

    for wall in ("Login required", "Please log in to continue",
                 "Sign in to access strategy returns", "missing credentials",
                 "credentials required", "authentication required"):
        assert REFUSED_FOR_AUTH.search(wall), wall
    for theirs in ("invalid strategy slug", "unknown strategy 'x'",
                   "strategy_not_found"):
        assert not REFUSED_FOR_AUTH.search(theirs), (
            f"{theirs!r} is being told our argument is wrong -- we were let in")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_call_that_could_not_be_read_is_not_three_tools_that_answered():
    """The pass of 2026-09-13 found this in a check written eight hours earlier.

    `/guides/nexus-lab-loop` promises three named tools need no key. The check
    asks all three, and with one call unreadable -- a TLS handshake they dropped
    at 20:55 the night before -- `walls` was empty, the Inconclusive branch
    wanted ALL THREE unreadable, and it concluded `passed` with a reason reading
    "all three ground-truth tools answered an unauthenticated caller: [two
    names]". A pass here is what `verify.py` sends.

    Rule 8 in the direction that talks to the vendor. A wall still fails -- a
    refusal is a refusal however many other calls were lost -- so both branches
    are pinned, not just the new one.
    """
    from tests.mcp.test_ground_truth_needs_no_key import decide

    def a(tool, outcome):
        return {"tool": tool, "outcome": outcome, "detail": "..."}

    three = [a("list_backtest_surfaces", "answered"),
             a("get_backtest_models", "answered"),
             a("get_strategy_returns", "answered")]
    assert decide(three)[0] == "passed"

    lost = [a("list_backtest_surfaces", "unreadable"),
            a("get_backtest_models", "answered"),
            a("get_strategy_returns", "answered")]
    verdict, reason = decide(lost)
    assert verdict == "inconclusive", (
        "two readings cannot answer a claim about three tools")
    assert "list_backtest_surfaces" in reason and "2 of the 3" in reason

    # A refusal outranks a lost reading: we were turned away, and that is
    # measured whatever else failed.
    both = [a("list_backtest_surfaces", "unreadable"),
            a("get_backtest_models", "refused"),
            a("get_strategy_returns", "answered")]
    assert decide(both)[0] == "failed"

    # Their own error is not a wall -- being told our argument is wrong means
    # we were let in, which is the whole of what the guide promises.
    theirs = [a("list_backtest_surfaces", "answered"),
              a("get_backtest_models", "answered"),
              a("get_strategy_returns", "failed_on_its_own_terms")]
    assert decide(theirs)[0] == "passed"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_exclusion_counts_wherever_their_scope_states_it():
    """#83's shape, caught a third time on the same endpoint before it went out.

    The contract this check states is that a summary excluding a population it
    holds "must say so, and say where that population can be read". It does not
    say in which FIELD. `accounts_for` read `counters_do_not_cover` for the
    statement and threw away any sentence in `counters_cover` that carried a
    negation -- so a scope saying "event-card bull/bear positions are not
    counted here, see /api/v1/event-cards/positions" with an empty
    `counters_do_not_cover` was reported as a scope that "neither counts them
    nor names them", about a body that had just named them.

    #83 was filed on this endpoint on a misreading of the same kind, withdrawn,
    and cost a retraction. Three readers, 3/3, 2026-09-13.
    """
    from tests.rest.test_portfolio_summary import accounts_for

    from tests.rest.test_portfolio_summary import states_exclusion

    theirs = {"counters_cover": "on-chain WTA bets from this user's swarm "
                                "wallet; event-card bull/bear positions are "
                                "not counted here, see "
                                "/api/v1/event-cards/positions",
              "counters_do_not_cover": []}
    assert accounts_for(theirs) is None, (
        "V05's pin stands: a sentence saying event cards are NOT counted is "
        "still not counting them")
    assert states_exclusion(theirs), (
        "but it IS the exclusion stated, which is what the contract asks for "
        "-- and reading only counters_do_not_cover called this body silent")

    # The direction that must still fail, or the reader above is a hole: a
    # scope that says nothing about the population at all.
    silent = {"counters_cover": "on-chain WTA bets only",
              "counters_do_not_cover": []}
    assert accounts_for(silent) is None and not states_exclusion(silent), (
        "a scope silent about the population held is the defect this check "
        "was written for")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_clone_surface_reads_the_flow_and_not_their_spelling():
    """Two ways this pair could send Cymetica a false claim about #89/#98.

    C02 -- `served_but_undocumented` built the templated path with the literal
    `{instance_id}` and compared it to their path keys verbatim, so renaming
    the parameter in openapi, which changes nothing a caller can see, would
    have reported routes they DO document as served-but-undocumented.

    C03 -- `credential_gap`'s verdict failed on any authenticated cloned-bots
    route without `x-api-key`, while the docstring names one flow: "an agent
    that can clone a bot can put money in it". The day they fix funding and
    document a user-only `DELETE`, that would have been a `fail` for an
    operation outside the flow, on a row they have already paid for twice.

    Both 3/3, deep pass of 2026-09-13. The direction that must still work is
    pinned beside each, because a check that cannot fail is the other defect.
    """
    from tests.rest.test_cloned_bots_surface import (PREFIX, credential_gap,
                                                     served_but_undocumented)

    renamed = served_but_undocumented({f"{PREFIX}/abc/fund": ["POST"]},
                                      {PREFIX + "/{clone_id}/fund"})
    assert renamed == [], (
        "their parameter name is not part of the contract; the route is")
    hidden = served_but_undocumented({f"{PREFIX}/abc/secret": ["POST"]},
                                     {PREFIX + "/{clone_id}/fund"})
    assert [r["path"] for r in hidden] == [PREFIX + "/{instance_id}/secret"], (
        "a route they really do not document must still be reported")

    key = {"parameters": [{"in": "header", "name": "x-api-key"}]}
    auth = {"parameters": [{"in": "header", "name": "authorization"}]}

    today = credential_gap({f"{PREFIX}/clone": {"post": key},
                            f"{PREFIX}/{{id}}/fund": {"post": auth}}, {})
    assert sorted(today["blocked"]) == [f"POST {PREFIX}/{{id}}/fund"], (
        "the funding step refusing the agent credential IS the finding")

    fixed = credential_gap({f"{PREFIX}/clone": {"post": key},
                            f"{PREFIX}/{{id}}/fund": {"post": key},
                            f"{PREFIX}/{{id}}": {"delete": auth}}, {})
    assert fixed["blocked"] == {}, (
        "with funding fixed, a documented user-only DELETE is not a step that "
        "moves the clone forward")
    assert sorted(fixed["refuses"]) == [f"DELETE {PREFIX}/{{id}}"], (
        "and it is still reported, because the VERDICT still reads refuses")

    # The reason the verdict was NOT narrowed to `blocked`, learned the same
    # night by running it: their /fund is fixed and publishes x-api-key, and
    # the route still refusing the agent credential is
    # GET /api/v1/cloned-bots/{instance_id}/activity -- which is what #89/#98
    # is currently about. A verdict reading `blocked` turned that live, filed,
    # twice-paid finding into `passed`, one fold away from verify.py sending
    # the pass. An agent reading its own clone's activity is inside the flow by
    # any honest reading; "moves the clone forward" was our boundary, not one
    # their document draws.
    live = credential_gap({f"{PREFIX}/clone": {"post": key},
                           f"{PREFIX}/{{id}}/fund": {"post": key},
                           f"{PREFIX}/{{id}}/activity": {"get": auth}}, {})
    assert live["blocked"] == {} and sorted(live["refuses"]) == [
        f"GET {PREFIX}/{{id}}/activity"], live
    assert live["refuses"], (
        "today's real shape must still be a finding, whatever `blocked` says")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_spec_check_reads_a_renamed_request_and_a_semicolon_split():
    """Two losses the BB-SPEC check reported on 2026-09-25 that were ours.

    ET-26608 was filed as "Github" and renamed "Gem Screener" by a BB-CHANGE;
    the record's `app_name` is the new name, so the "Github: " the product put
    in front of the request was left on its first line, and that line matched
    no item. The name the request was filed under is the one the spec's own
    header still carries ("BB-SPEC for Github").

    ET-26776 was one paragraph, and their writer cut its sentences at
    semicolons as well as full stops -- "Cymetica is the engine; Tuatara
    discovers; ..." became four items. Every word is there; only the ";" is
    gone. REPLY-0021 promises sentence ends, and that nothing is dropped;
    a clause per item drops nothing, so it is not the defect this check hunts.

    The direction that must still fail is pinned beside each: the "e.g." cut
    of 2026-09-19 is a split at a full stop, not a semicolon, and a semicolon
    split that loses a clause has lost it.
    """
    from tests.rest.test_build_it_better_spec_keeps_the_request import judge

    def record(name, request, *items, header=None):
        numbered = "\n".join(f"  {n}. {item}" for n, item in
                             enumerate(items, 1))
        return {"app_name": name, "messages": [
            {"at": "1", "kind": "BB-REQUEST", "body": request},
            {"at": "2", "kind": "BB-SPEC",
             "body": f"BB-SPEC for {header or name}\n\nWhat we will build:\n"
                     f"{numbered}\n"}]}

    renamed = record("Gem Screener", "Github: Keep the tabs.\nEnglish only.",
                     "Keep the tabs.", "English only.", header="Github")
    assert judge(renamed)["lost"] == [], (
        "the prefix is the name the request was filed under")

    split = record("X", "X: A is one; B is two. Style: calm; no clutter.",
                   "A is one", "B is two.", "Style: calm", "no clutter.")
    assert judge(split)["lost"] == [], (
        "a clause per item keeps every word the stranger sent")

    cut = record("X", "X: Use indicators (e.g. RSI, MACD) daily.",
                 "Use indicators (e.g.", "RSI, MACD) daily.")
    assert judge(cut)["lost"] == ["Use indicators (e.g. RSI, MACD) daily."], (
        "the e.g. cut is the defect REPLY-0021 fixed; it must still fail")

    dropped = record("X", "X: A is one; B is two.", "A is one")
    assert judge(dropped)["lost"] == ["A is one; B is two."], (
        "a semicolon split that loses a clause has lost it")

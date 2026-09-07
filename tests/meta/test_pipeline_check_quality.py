"""Every check must be able to FAIL, and must be able to READ its sources.

The state pipeline has 250 tests. Not one of them asked whether a check
measures what it says. That gap is the operator's stated reason for not
trusting this project, and it produced five defects in a single session --
each found by running the check or by the operator asking a question, never by
a test:

  * `skills_subset` compared agent-card as a subset of agent-skills. `subset`
    is not symmetric and the pair was ordered alphabetically, so the claim ran
    backwards. It failed while the smaller file was a perfectly good subset of
    the larger, and was one step from being filed to the vendor.
  * `clob_pair_count` is prose against prose, so `conclude` returns rather
    than raising: the check could not fail under any circumstances, and its
    "pass" had established a verification.
  * `mcp_tool_names_documented_exist` read markdown links that llms.txt had
    stopped emitting. The pattern matched nothing, which reaches the check as
    Inconclusive and composes with the vendor's claim into a phrase that reads
    like a resolved defect.
  * `agent_names` had enumerated the symbols it expected to find, so it
    matched whatever the document contained.
  * the trust ladder demanded trusted-tier entitlement for a key the platform
    assigns a higher tier.

Three of those five are the same defect: a check that cannot distinguish the
world where the defect exists from the world where it does not. So that is
what is tested here, per claim, against captured sources:

    CAN IT READ?   the extractor produces a value from a real capture
    CAN IT FAIL?   perturb one side, and the relation must stop holding
    CAN IT SPEAK?  a prose-only comparison is evidence, not a verdict
    WHICH WAY?     a non-symmetric relation names its direction

`tests/meta/fixtures/sources/capture.json` is every declared source, fetched
once. It makes these offline and stable: a check being well-formed is a
property of the check, not of what the platform happens to serve today.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
CAPTURE = Path(__file__).resolve().parent / "fixtures" / "sources" / "capture.json"

STRUCTURED = frozenset({"jsonpath", "len", "set", "keys", "count"})


def _claims() -> dict:
    return yaml.safe_load(
        (REPO / "tests" / "reconciliation" / "claims.yaml").read_text(encoding="utf-8"))


def _capture() -> dict:
    return json.loads(CAPTURE.read_text(encoding="utf-8"))


CLAIMS = _claims()["claims"]
IDS = [c["id"] for c in CLAIMS]


def _pair_for(claim: dict):
    from tests.reconciliation.test_reconcile import Pair

    data = _claims()
    a, b = sorted(claim["sources"])
    enriched = {**claim, "subset_of_pair": claim.get("subset")}
    return Pair(enriched, a, b, sources=data["sources"])


# ---------------------------------------------------------------------------
@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize("claim", CLAIMS, ids=IDS)
def test_every_extractor_can_read_its_source(claim):
    """A pattern that matches nothing is not a passing check; it is a check
    that has stopped working, and it reaches the ledger as Inconclusive --
    which beside a vendor's claim of a fix reads like a resolved defect.

    Two claims legitimately cannot read today, because the sentence they read
    was removed from the document. Those are listed, so the list itself is the
    record of what is broken rather than a silence."""
    from qa.extractors import ExtractionError, extract

    # Sources the vendor has removed. Each is a real, open question with the
    # vendor -- not a check we may quietly leave broken.
    KNOWN_REMOVED = {
        ("mcp_resource_count", "llms_txt"):
            "the 'N resources' sentence was removed from llms.txt (report #50)",
        ("llms_agent_count_self_consistent", "llms_txt"):
            "the second agent-count sentence was removed from llms.txt (report #55)",
        ("llms_agent_count_self_consistent", "llms_txt_2"):
            "the second agent-count sentence was removed from llms.txt (report #55)",
    }

    capture = _capture()
    for name, spec in claim["sources"].items():
        source = capture.get(name)
        assert source, f"{claim['id']}: source {name!r} is not in the capture"
        try:
            value = extract(spec, source["body"])
        except ExtractionError as exc:
            known = KNOWN_REMOVED.get((claim["id"], name))
            assert known, (
                f"{claim['id']}.{name}: the extractor reads nothing from a real "
                f"capture of {name}, so this check can never fail and will sit "
                f"as Inconclusive.\n  spec: {spec}\n  error: {exc}"
            )
            continue
        assert value is not None and value != frozenset(), \
            f"{claim['id']}.{name}: extractor produced an empty value"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize("claim", CLAIMS, ids=IDS)
def test_every_check_can_fail(claim):
    """The negative control. Perturb one side and the relation must break.

    A check that holds for every input it could receive is not measuring
    anything. `subset` running backwards passed on equal sets; a prose-only
    comparison passed by construction. Both would have survived any number of
    tests that only asked whether the check passes today."""
    from qa.extractors import relation_holds

    relation = claim["relation"]
    tolerance = float(claim.get("tolerance_pct", 0))

    if relation in ("all_equal", "set_equal"):
        holds, _ = relation_holds(relation, _sample(relation), _sample(relation), tolerance)
        assert holds, f"{claim['id']}: {relation} does not hold for identical values"
        broken, _ = relation_holds(relation, _sample(relation),
                                   _perturb(_sample(relation)), tolerance)
        assert not broken, f"{claim['id']}: {relation} still holds after a change"

    elif relation == "subset":
        # Against REAL captured values, not values this test builds from the
        # declaration. Building them from the declaration makes the test
        # self-consistent whatever the declaration says: it then confirms only
        # that Pair honours it, and reversing `subset:` passes. Verified by
        # mutation -- the first version of this test did exactly that.
        _assert_subset_direction_is_right(claim)

    elif relation == "within_tolerance":
        holds, _ = relation_holds(relation, 100, 100, tolerance)
        assert holds, f"{claim['id']}: identical values are outside tolerance"
        far = 100 * (1 + (tolerance + 20) / 100)
        broken, _ = relation_holds(relation, 100, far, tolerance)
        assert not broken, (
            f"{claim['id']}: {tolerance}% tolerance still holds at a "
            f"{(tolerance + 20):.0f}% difference"
        )
    else:
        pytest.fail(f"{claim['id']}: unknown relation {relation!r}, with no negative control")


def _assert_subset_direction_is_right(claim: dict) -> None:
    """A reversed `subset:` is only visible against real data.

    With the real captures, the declared direction should hold and the
    reverse should not -- agent-skills.json (10 ids) is contained in
    agent-card.json (15), and the other way round it is not. If the declared
    direction fails while the REVERSE holds, the declaration is backwards,
    which is precisely the shape of the bug that nearly went to the vendor.
    """
    from qa.extractors import ExtractionError, extract, relation_holds

    capture = _capture()
    contained = claim["subset"]
    other = next(n for n in claim["sources"] if n != contained)
    try:
        small = extract(claim["sources"][contained], capture[contained]["body"])
        big = extract(claim["sources"][other], capture[other]["body"])
    except ExtractionError:
        pytest.skip(f"{claim['id']}: a source cannot be read from the capture")

    small, big = frozenset(small), frozenset(big)

    if small == big:
        # Honest limit, stated rather than passed over. When the two sides are
        # equal, "A is contained in B" and "B is contained in A" are both
        # true, and no test on this data can tell which the claim meant. All
        # that remains is the stated reason, which the caller has checked.
        pytest.skip(
            f"{claim['id']}: both sides hold the same {len(small)} values in "
            f"this capture, so the direction cannot be verified from data. It "
            f"rests on subset_why: {claim.get('subset_why', '').strip()[:90]}")

    # Perturbation, which works whenever the sides differ. Direction IS this:
    # a phantom on the contained side must break the check, and a phantom on
    # the containing side must not.
    broken, _ = relation_holds("subset", small | {"PHANTOM"}, big, 0)
    assert not broken, (
        f"{claim['id']}: adding a value to {contained} does not break the "
        f"check, so it is not the contained side. `subset: {contained}` is "
        f"backwards."
    )
    tolerated, _ = relation_holds("subset", small, big | {"PHANTOM"}, 0)
    assert tolerated, (
        f"{claim['id']}: adding a value to {other} breaks the check, but "
        f"{other} is the containing side and is allowed to have more. "
        f"`subset: {contained}` is backwards."
    )

    # And against the captured values as they are.
    if small != big:
        forward, _ = relation_holds("subset", small, big, 0)
        reverse, _ = relation_holds("subset", big, small, 0)
        assert not (reverse and not forward), (
            f"{claim['id']}: `subset: {contained}` is backwards. In this "
            f"capture {other} is contained in {contained}, not the reverse."
        )
        assert forward, (
            f"{claim['id']}: {contained} is not contained in {other} in this "
            f"capture, and neither is the reverse -- a genuine violation, so "
            f"this claim is currently failing for real."
        )


def _sample(relation):
    return frozenset({"a", "b"}) if relation == "set_equal" else 7


def _perturb(value):
    return (value | {"phantom"}) if isinstance(value, frozenset) else value + 1


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize("claim", CLAIMS, ids=IDS)
def test_a_prose_only_comparison_cannot_mint_a_finding(claim):
    """conclude() never raises for an evidence-role measurement, so such a
    check passes whatever it observes. That is fine as evidence and fatal as a
    verdict -- clob_pair_count had established PASSING that way."""
    pair = _pair_for(claim)
    kinds = [claim["sources"][n].partition(":")[0] for n in (pair.a, pair.b)]
    structured = any(k in STRUCTURED for k in kinds)

    if structured:
        assert pair.role == "verdict", claim["id"]
        return

    if claim.get("prose_only"):
        assert (claim.get("why") or "").strip(), (
            f"{claim['id']}: prose_only with no stated reason is just an override"
        )
        assert pair.role == "verdict", claim["id"]
    else:
        assert pair.role == "evidence", (
            f"{claim['id']}: neither side reads structure, so this compares one "
            f"sentence with another and cannot open or close a finding"
        )


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize("claim", CLAIMS, ids=IDS)
def test_no_check_enumerates_the_answer_it_expects(claim):
    """An extractor that lists the values it expects matches whatever is
    there. agent_names enumerated 21 symbols and passed vacuously on the very
    document that had the defect."""
    for name, spec in claim["sources"].items():
        kind, _, arg = spec.partition(":")
        if kind in ("regex_all", "regex_set", "regex"):
            alternatives = arg.count("|")
            assert alternatives < 3, (
                f"{claim['id']}.{name} enumerates {alternatives + 1} expected "
                f"values.\n  {spec}\nAnchor on a place in the document instead "
                f"-- scope: or list_after:."
            )


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_title_is_found_on_the_page_however_the_page_quotes_it():
    """A check that reads punctuation is measuring the wrong thing.

    2026-09-07, and the fourth time a red check turned out to be ours.
    `test_filed_reports_reach_the_work_tracker` asked whether a report of ours
    appears on /leaderboard/bugs by looking for the first 45 characters of its
    title in the page text. The page embeds those titles in a JSON blob, so
    report #73 was published as "The bounty programme\u0027s own reward
    totals disagree..." -- and the substring stopped matching at character 21,
    the apostrophe. The check reported the report as absent from a tracker
    that was displaying it, against a row that had been VERIFIED FIXED, which
    is a false regression one fold away from being filed back to the vendor.

    The family this belongs to is the module's subject: a check that cannot
    fail for the reason it names. This one could only fail for a reason it did
    not name. So the guard is the encodings themselves -- every way a page can
    legitimately write the same title -- and it is a unit test because the
    live page is not required to keep any of them.
    """
    from tests.rest.test_bounty_pipeline import _PROBE_CHARS, _probe, _squash

    title = "The bounty programme's own reward totals disagree: stats records 36"
    renderings = {
        "json escape": 'x{"title": "The bounty programme\u0027s own reward totals disagree: stats records 36"}',
        "html entity": "<h3>The bounty programme&#39;s own reward totals disagree: stats records 36</h3>",
        "curly quote": "<h3>The bounty programme\u2019s own reward totals disagree: stats records 36</h3>",
        "re-wrapped":  "<h3>The bounty programme's own\n  reward totals\tdisagree: stats records 36</h3>",
        "plain":       "<h3>" + title + "</h3>",
    }
    for name, page in renderings.items():
        assert _probe(title) in _squash(page), (
            f"a title the page renders with a {name} reads as absent, and the "
            f"check would call the report missing from a tracker showing it")

    assert _probe(title) not in _squash("<h3>Some other report entirely</h3>"), \
        "the probe matches a page that does not carry the title at all"

    # The probe has to be long enough that two of our own titles cannot
    # collide -- several share an opening clause.
    assert len(_probe(title)) == _PROBE_CHARS
    assert _probe("The bounty programme's own reward totals disagree") \
        != _probe("The bounty programme's own tier table contradicts"), \
        "two real titles squash to the same probe; _PROBE_CHARS is too short"

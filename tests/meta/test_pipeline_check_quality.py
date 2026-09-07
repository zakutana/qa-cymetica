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

from qa.extractors import iter_extractors
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

    elif relation == "at_least":
        # Two ways a floor claim must be able to fail, and they are opposite:
        # the figure drops below the stated minimum (the document is wrong),
        # or it climbs so far above it that the document is stale. A relation
        # that only checks one of those is half a check.
        holds, _ = relation_holds(relation, 100, 100, tolerance)
        assert holds, f"{claim['id']}: a figure exactly at the floor is below it"
        holds, _ = relation_holds(relation, 100, 100 * (1 + tolerance / 200), tolerance)
        assert holds, f"{claim['id']}: a figure just above the floor fails"
        below, _ = relation_holds(relation, 100, 99, tolerance)
        assert not below, f"{claim['id']}: a figure below the stated minimum holds"
        stale, _ = relation_holds(relation, 100, 100 * (1 + (tolerance + 20) / 100),
                                  tolerance)
        assert not stale, (
            f"{claim['id']}: the floor may drift {(tolerance + 20):.0f}% out of "
            f"date and still hold, so a stale published figure is invisible"
        )
        assert claim.get("floor") in claim["sources"], (
            f"{claim['id']}: `at_least` is not symmetric and this claim does "
            f"not name which source states the minimum, so the comparison can "
            f"run backwards -- the same defect as an unnamed subset direction"
        )

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
        # iter_extractors, not partition: the wrapper used to hide the regex.
        # regex_int counts too -- it was not in the tuple at all.
        for kind, arg in iter_extractors(spec):
            if kind not in ("regex_all", "regex_set", "regex", "regex_int"):
                continue
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
        # RAW, deliberately. Written unraw, Python decoded the escape at
        # compile time and the one rendering named for the escape carried an
        # apostrophe instead -- so _JSON_ESCAPE in _squash was exercised by no
        # case here, and deleting that substitution left all five green while
        # the live tracker page, which really does serve the escape, read as
        # not carrying report #73's title at all. The 2026-09-07 incident,
        # reproduced by the contract audit.
        "json escape": r'x{"title": "The bounty programme\u0027s own reward totals disagree: stats records 36"}',
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


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_is_answer_rule_is_self_calibrating_and_still_bites():
    """The rule that check has now been wrong about three times in one day.

    v1 asserted the field was PRESENT and went green whatever it said. v2
    asserted it was FALSE on every automated reply, which is the opposite of
    the contract their own resolution states. Both times the live inbox
    happened to agree with the mistake, so running the check proved nothing --
    which is exactly why the rule is held here against cases the live data
    does not currently contain.

    Two properties, and they pull against each other. It must not stay red on
    messages from before they began tagging, or it is a badge nobody can
    clear. And it must go red the moment they stop, or it is decoration.
    """
    from tests.rest.test_qa_agent_channel import tagging_gap

    def m(at, is_answer="absent"):
        meta = {"auto": True, "kind": "first_pass"}
        if is_answer != "absent":
            meta["is_answer"] = is_answer
        return {"created_at": at, "metadata": meta}

    # The shape of the real inbox on 2026-09-07: untagged, then tagged, and
    # the untagged ones are history nobody can now change.
    started, missing = tagging_gap(
        [m("2026-09-06T05:58"), m("2026-09-06T08:47"),
         m("2026-09-06T11:07", True), m("2026-09-07T13:52", True)])
    assert (started, missing) == (2, []), \
        "history from before they began tagging keeps the check permanently red"

    # A regression: one arrives untagged after they had started.
    started, missing = tagging_gap(
        [m("2026-09-06T11:07", True), m("2026-09-07T13:52")])
    assert started == 0 and [x["created_at"] for x in missing] == ["2026-09-07T13:52"], \
        "they stopped tagging and the check did not notice"

    # Order comes from the timestamps, not from the order the inbox returned
    # them -- theirs is newest-first, which would invert the calibration.
    newest_first = [m("2026-09-07T13:52"), m("2026-09-06T11:07", True)]
    assert [x["created_at"] for x in tagging_gap(newest_first)[1]] == ["2026-09-07T13:52"]

    # Never tagged at all is the original defect, and is not "no gap".
    assert tagging_gap([m("2026-09-06T05:58"), m("2026-09-06T08:47")]) == (None, [])
    assert tagging_gap([]) == (None, [])

    # `false` is a tag. Their routing prompt carries it, and a check that
    # counted only `true` would call their documented behaviour a miss.
    assert tagging_gap([m("2026-09-06T11:07", True), m("2026-09-07T13:52", False)]) == (0, [])


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_withdrawn_promise_is_not_a_fix():
    """A1: the branch that sent 26 fix-verifications for paths that still 404.

    The module docstring of tests/pinned/test_documented_404.py states the
    table, and tests/pinned/documented-404.yaml repeats it word for word:

        still documented, still 404   FAIL
        still documented, now served  PASS   <- the fix
        no longer documented          INCONCLUSIVE

    "The third is deliberately not a pass. Withdrawing a promise is a
    legitimate way to resolve a broken promise, but it is the vendor's call to
    announce, not a measurement we may quietly bank on their behalf."

    The code returned `passed` on that third case. An inline comment argues
    the 2026-09-05 change: that Inconclusive guarded nothing once the pins
    existed, and read to the operator as "not reproducible" rather than as an
    inability to measure. That argument is about the DISPLAY of a state; it
    does not make a withdrawal a fix. And on 2026-09-07 the consequence stopped
    being internal: verify.py posted "VERDICT pass -- the check that recorded
    this defect now passes" to reports #49 and #59, for 26 paths every one of
    which still answers 404.

    Three independent triage agents reproduced it. Two statements of the
    contract against one comment, and the comment never answers them.

    Pulled into a function so the three outcomes can be held against the table
    without calling the live platform -- which is what nobody could do while
    the decision lived inside a parametrised live check.
    """
    from tests.pinned.test_documented_404 import outcome_for

    # Still promised, still broken.
    assert outcome_for(documented=True, status=404, served_successors=[])[0] == "failed"
    # Still promised, now built. The only fix.
    assert outcome_for(documented=True, status=200, served_successors=[])[0] == "passed"
    # Renamed, and the new name works: also a fix, and verified by calling it.
    assert outcome_for(documented=False, status=404,
                       served_successors=["/api/v1/new"])[0] == "passed"
    # Withdrawn. Not a fix, whatever it resolves.
    verdict, shape = outcome_for(documented=False, status=404, served_successors=[])
    assert verdict == "inconclusive", \
        "a promise they deleted was banked as a fix on their behalf"
    assert shape == "withdrawn", \
        "the three no-longer-documented outcomes must stay distinguishable"

    # And the live check must still SAY what happened. An inconclusive that
    # does not name the withdrawal is the "not reproducible" reading the
    # 2026-09-05 comment rightly objected to -- the verdict is corrected here,
    # its objection about legibility is not dismissed.
    import inspect

    from tests.pinned import test_documented_404 as mod

    source = inspect.getsource(mod.test_documented_path_is_served)
    assert "DELETING the entry" in source and "still answers" in source, \
        "the reason line stopped naming the withdrawal or the live status"

    # Withdrawn AND the path started working: still not ours to call a fix,
    # because nothing documents it any more -- there is no promise to measure.
    assert outcome_for(documented=False, status=200,
                       served_successors=[])[0] == "inconclusive"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_publishing_a_definition_does_not_disable_the_money_check():
    """A9: the repair that called itself "strictly stronger" was strictly weaker.

    The module docstring of tests/rest/test_reward_totals_agree.py states the
    invariant the check exists for: "a programme that has recorded 36 awards
    cannot show zero earned for every hunter it has". When Cymetica answered
    #73 by publishing `total_earned_definition` rather than by moving a figure,
    the check was repaired to hold the column against the definition -- and the
    repair put the new comparison in an `else`, so the original invariant ran
    only while no definition was published.

    Live consequence, run-20260907T135100Z: stats read total_paid 2000.0 and
    payouts_recorded 2, all four hunters read total_earned 0.0 and total_paid
    0.0, and the check emitted "the aggregate and the leaderboard agree". A
    pass verification for that went to #73.

    Both belong. Column agreement is a within-row check and cannot see a
    cross-surface contradiction; the cross-surface check cannot see a column
    that disagrees with its own definition.
    """
    from tests.rest.test_reward_totals_agree import money_problems

    hunters_at_zero = [{"hunter_name": "a", "total_earned": 0.0, "total_paid": 0.0},
                       {"hunter_name": "b", "total_earned": 0.0, "total_paid": 0.0}]
    programme_paid = {"awards_recorded_total": 38000.0, "total_paid": 2000.0}

    # The live state that passed. It must not.
    problems = money_problems(programme_paid, hunters_at_zero, "paid")
    assert problems, \
        "a programme that paid 2000.0 with every hunter at zero read as agreement"
    assert any("2000" in p for p in problems), problems

    # The same contradiction with no definition published -- the original
    # reading, which must still work.
    assert money_problems(programme_paid, hunters_at_zero, None)

    # A column that disagrees with the definition it publishes.
    mismatched = [{"hunter_name": "a", "total_earned": 5.0, "total_paid": 9.0}]
    assert money_problems({"awards_recorded_total": 9.0, "total_paid": 9.0},
                          mismatched, "paid")

    # Agreement on both axes is agreement.
    consistent = [{"hunter_name": "a", "total_earned": 2000.0, "total_paid": 2000.0}]
    assert money_problems({"awards_recorded_total": 2000.0, "total_paid": 2000.0},
                          consistent, "paid") == []

    # Nothing recorded anywhere is not a contradiction.
    assert money_problems({"awards_recorded_total": 0.0, "total_paid": 0.0},
                          hunters_at_zero, "paid") == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_our_published_stage_set_is_theirs():
    """A12: a hand-written copy of somebody else's vocabulary goes stale.

    `PUBLISHED` in tests/rest/test_bounty_pipeline.py decides which of our
    reports the work tracker is obliged to show. It was typed by hand from a
    sentence they said on 2026-09-05 and intersected their published enum in
    four words: six of its ten could not be returned by that surface at all,
    and two post-validation statuses that CAN be -- openclaw_testing and
    ready_for_review -- were missing. A report sitting at ready_for_review and
    absent from the page was dropped from the denominator, so the check passed
    on the defect it exists to catch, and told them the report "had not been
    validated" two stages after they validated it.

    Same shape as the five defects of 2026-09-07: an operand taken from our
    side while the contract is about theirs.
    """
    from tests.rest.test_bounty_pipeline import PUBLISHED

    # Their enum, as published at my-reports -> status_vocabulary.report_status
    # and verified live on 2026-09-07. test_status_vocabulary_is_mapped.py is
    # what notices if they change it.
    theirs = {"pending", "triaging", "validated", "in_progress",
              "openclaw_testing", "ready_for_review", "fixed", "paid",
              "duplicate", "invalid", "wontfix"}
    pre_validation = {"pending", "triaging"}
    never_validated = {"duplicate", "invalid", "wontfix"}

    assert PUBLISHED <= theirs, \
        f"we demand publication for statuses they cannot return: {sorted(PUBLISHED - theirs)}"
    assert PUBLISHED == theirs - pre_validation - never_validated, \
        ("the set is no longer 'validated onwards', which is the invariant the "
         "docstring names")
    assert not PUBLISHED & never_validated, \
        "an invalid report was never validated and is not owed a place on the page"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_field_missing_from_one_row_is_not_a_claim_about_all_of_them():
    """A18: the comprehension said any, the sentence we send said every.

    `{field for field in SUBMITTED_FIELDS for row in theirs if not row.get(field)}`
    puts a field in `dropped` when ONE row lacks it, and submit.py injects the
    reason as the report headline: "N of the 5 fields we send come back empty
    on every one of our reports". One stale row among 27 sent the vendor a
    quantified claim about 27.

    Asserted over the source because the comprehension is the defect, and a
    live run cannot reach the state while their data happens to be complete.
    """
    import inspect

    from tests.rest import test_bounty_pipeline as mod

    source = inspect.getsource(mod.test_submitted_fields_are_stored)
    assert "len(rows_missing) == len(theirs)" in source, \
        "a field empty on one row can again be reported as empty on every row"
    assert "empty_on_some_rows" in source, \
        "the partial case is no longer carried in the population, so it is invisible"

    # And the two siblings that guard an empty population must both keep doing
    # so -- A5 was the one that did not, and passed as "0 of 0".
    for name in ("test_submitted_fields_are_stored", "test_hunter_name_is_retained",
                 "test_filed_reports_reach_the_work_tracker"):
        body = inspect.getsource(getattr(mod, name))
        assert "inconclusive" in body, f"{name} can conclude with nothing compared"

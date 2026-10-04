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
SOURCES = _claims().get("sources") or {}
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

    # THIS claim, before the relation in the abstract. Everything below
    # perturbs _sample(relation) -- the literals 7 and frozenset({"a","b"}) --
    # which proves relation_holds is non-constant and says nothing about
    # whether this particular claim can ever go red. A claim whose two sides
    # are the same document read with the same spec is constant-true by
    # construction, is role: verdict (so it may open or close a finding), and
    # passed all four quality guards. `llms_txt` and `llms_txt_2` are declared
    # as the same URL in claims.yaml, in as many words -- "same doc, a second
    # statement in it" -- so the two-names-one-document shape is one line away
    # at all times. Found by the deep pass of 2026-09-09, three votes of
    # three. The `subset` branch below already refused to reason from the
    # declaration and says why; this is the same objection, one level up.
    specs = claim["sources"]
    if len(specs) == 2:
        (an, aspec), (bn, bspec) = sorted(specs.items())
        urls = {n: (SOURCES.get(n) or {}).get("url") for n in (an, bn)}
        assert not (aspec == bspec and urls[an] == urls[bn] and urls[an]), (
            f"{claim['id']}: {an} and {bn} are the same document "
            f"({urls[an]}) read with the same spec ({aspec!r}), so the two "
            f"sides are equal by construction and no state of the platform "
            f"can make this check fail")

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

    # The async lane's follow-up (2026-09-26): the rule behind
    # test_an_async_message_gets_the_investigation_its_card_promises, held
    # here so the meta ceiling does not move.
    from datetime import datetime, timedelta, timezone

    from tests.rest.test_async_a2a_investigation import unanswered

    at = lambda h, mi=0: datetime(2026, 9, 26, h, mi, tzinfo=timezone.utc)
    sent = [{"id": f"q{i}", "at": at(7 + i)} for i in range(6)]
    human = lambda q, when: {"reply_to": q, "at": when, "auto": False}
    robot = lambda q, when: {"reply_to": q, "at": when, "auto": True}
    now = at(14)
    judged, missing, _ = unanswered(sent, [robot(s["id"], s["at"]) for s in sent], now)
    assert [s["id"] for s in judged] == ["q1", "q2", "q3", "q4", "q5"], (
        "judges the newest five that are due, so a fix clears it")
    assert len(missing) == 5, "an automatic first pass is not the investigation"
    answered = [human(s["id"], s["at"] + timedelta(minutes=44)) for s in sent]
    assert unanswered(sent, answered, now)[1] == [], "a reply 44 min later counts"
    unknown = [{"reply_to": s["id"], "at": s["at"] + timedelta(minutes=5), "auto": None}
               for s in sent]
    assert unanswered(sent, unknown, now)[1] == [], (
        "an unclassified reply (no metadata.auto) is not an automatic one")
    late = [human(s["id"], s["at"] + timedelta(hours=3)) for s in sent]
    assert len(unanswered(sent, late, now)[1]) == 5, (
        "a reply hours later is not the lane working")
    fresh = [{"id": "new", "at": now - timedelta(minutes=10)}]
    assert unanswered(fresh, [], now) == ([], [], []), "not due yet is not judged"
    # Their deep investigation is marked auto=true too (NEXUS writes it), with
    # kind "deep": it IS the investigation. Every one was read as the first
    # pass (deep pass 2026-09-27, R01, 3/3). first_pass and deep_failed are not.
    marked = lambda kind: [{"reply_to": s["id"], "at": s["at"] + timedelta(minutes=3),
                            "auto": True, "kind": kind} for s in sent]
    assert unanswered(sent, marked("deep"), now)[1] == [], "a deep reply in 3 min counts"
    assert len(unanswered(sent, marked("first_pass"), now)[1]) == 5
    assert len(unanswered(sent, marked("deep_failed"), now)[1]) == 5, (
        "an investigation that did not run is not one")
    # C02, deep pass of 2026-09-30 (3/3): a deep reply that names no parent
    # cannot be paired, so a message with one in its window is unsure, not
    # unanswered -- six came back that way on 2026-09-26 (journal seq
    # 2883..2896) and were read as the lane silent. The card never promised
    # the reply names its parent.
    orphans = [{"reply_to": None, "at": s["at"] + timedelta(minutes=4), "auto": True,
                "kind": "deep"} for s in sent]
    _, missing, unsure = unanswered(sent, orphans, now)
    assert missing == [] and [s["id"] for s in unsure] == ["q1", "q2", "q3", "q4", "q5"], (
        "an unparented investigation in the window was counted as no reply")
    _, missing, unsure = unanswered(sent, [dict(o, kind="first_pass") for o in orphans], now)
    assert len(missing) == 5 and unsure == [], (
        "an unparented first pass is still no investigation")
    before = [{"reply_to": None, "at": at(6, 30), "auto": True, "kind": "deep"}]
    assert len(unanswered(sent, before, now)[1]) == 5, (
        "an unparented reply before every message stands in for none of them")
    paired_and_orphan = answered[:3] + orphans
    assert unanswered(sent, paired_and_orphan, now)[1:] == ([], [sent[3], sent[4], sent[5]]), (
        "a message with its own reply is answered; only the rest are unsure")

    # NEXT 2026-10-01 (async a2a check): the inbox without `limit` returned the 50
    # newest, so a message sent before the oldest one on the page looked unanswered
    # when its answer was on a page we never read. Such a message is unsure --
    # never missing -- and one whose own reply is on the page is still answered.
    oldest = at(8, 30)
    j, missing, unsure = unanswered(sent, [], now, oldest=oldest)
    assert [s["id"] for s in unsure] == ["q1"] and len(missing) == 4, (
        "a message sent before the oldest message on the page was judged missing")
    assert [s["id"] for s in unanswered(sent, [], now, oldest=at(6))[1]] == ["q1", "q2", "q3", "q4", "q5"], (
        "a page that reaches back before every send hid nothing, so nothing is unsure")
    assert unanswered(sent, [human("q1", at(8, 20))], now, oldest=oldest)[2] == [], (
        "a message whose own reply is on the page was called unsure")

    # #139 (fixed 2026-10-01 07:07 UTC; "messages logged before the fix stay as
    # they were"): a cut message logged BEFORE the fix is history, one logged
    # after it is the defect. Held here for the same ceiling.
    from tests.rest.test_build_it_better_log_keeps_whole_bodies import FIXED_AT, cuts, logged_since
    record = {"app_name": "X", "spec_text": "a" * 9000, "improvements": "ask",
              "messages": [{"kind": "BB-SPEC", "at": "2026-09-29T10:00:00+00:00", "body": "a" * 8000}]}
    assert cuts(record) == [], "a body logged before their fix was judged"
    assert logged_since(record) == 0
    after = dict(record, messages=record["messages"] + [
        {"kind": "BB-SPEC", "at": "2026-10-02T10:00:00+00:00", "body": "a" * 8000}])
    assert [c["kind"] for c in cuts(after)] == ["BB-SPEC"] and logged_since(after) == 1, (
        "a cut message logged after their fix was not seen")
    assert FIXED_AT.startswith("2026-10-01T07:07")

    # Chart Analyzer (2026-10-01), held here for the same ceiling: chart_rate
    # against the average of what the same answer marks counted_in_score.
    # The AAVE answer of that morning fails; either fix passes.
    from tests.rest.test_chart_analyzer_score_averages_what_it_counts import (
        TOLERANCE, averaged, candidates)
    pat = lambda key, rate, counted=True: {"key": key, "success_rate": rate,
                                           "counted_in_score": counted}
    aave = {"chart_rate": 0.4765, "patterns": [
        pat("breakout_volume", 0.4836), pat("bearish_engulfing", 0.4694),
        pat("bearish_engulfing", 0.4694), pat("bearish_engulfing", 0.4694, False)]}
    served, average, _ = averaged(aave)
    assert abs(served - average) > TOLERANCE, "the answer seen on 1 Oct read as consistent"
    once = dict(aave, patterns=[pat("breakout_volume", 0.4836),
                                pat("bearish_engulfing", 0.4694),
                                pat("bearish_engulfing", 0.4694, False)])
    served, average, _ = averaged(once)
    assert abs(served - average) <= TOLERANCE, "a repeat counted and marked once is a fix"
    served, average, _ = averaged(dict(aave, chart_rate=0.4741))
    assert abs(served - average) <= TOLERANCE, "counting every confirmation is a fix too"
    assert averaged({"chart_rate": None, "patterns": [pat("x", 0.5)]}) is None
    assert averaged({"chart_rate": 0.5, "patterns": [pat("x", None)]}) is None, (
        "a counted pattern without a rate is unread, not averaged as zero")
    assert averaged({"chart_rate": 0.5, "patterns": [pat("x", 0.5, False)]}) is None
    batch = [{"status": "scored", "input": {"contract": "a", "chain": "c"},
              "counted_patterns": ["X"]},
             {"status": "scored", "input": {"contract": "b", "chain": "c"},
              "counted_patterns": ["Y", "Y"]},
             {"status": "no_pool", "input": {"contract": "d", "chain": "c"}}]
    assert [r["input"]["contract"] for r in candidates(batch)] == ["b", "a"], (
        "the rows where the two readings differ are sampled first")

    # Chart Analyzer's verdict layer (ET-29001, verified 2026-10-04), held here for
    # the same ceiling. Four readings, each from the shape seen live that morning,
    # and each with the fix that must clear it.
    from tests.rest.test_chart_analyzer_verdict_layer_keeps_its_word import (
        closes_at, dex_promise, label_candidate, not_on_a_closed_candle,
        outside_their_range, undocumented)

    # 1. Schema: a live key the 200 schema does not list is undocumented, however the
    #    schema reaches its properties ($ref, allOf); `{}` documents nothing; turning
    #    additionalProperties on is tolerance, not documentation.
    spec = {"components": {"schemas": {"V": {"type": "object", "properties": {
        "label": {"type": "string"}}}}}}
    flat = {"type": "object", "additionalProperties": False,
            "properties": {"score": {"type": "integer"}}}
    live = {"score": 50, "verdict": {"label": "NO EDGE"}}
    assert [m["key"] for m in undocumented(live, flat, spec)[0]] == ["verdict"]
    assert undocumented(live, dict(flat, additionalProperties=True), spec)[0], (
        "tolerating an unlisted key was read as documenting it")
    listed = {"allOf": [flat, {"properties": {"verdict": {"$ref": "#/components/schemas/V"}}}]}
    assert undocumented(live, listed, spec) == ([], []), "a key listed through allOf/$ref"
    assert [m["key"] for m in undocumented({"summary": {}, "calls": []}, {}, spec)[0]] == [
        "calls", "summary"], "an empty schema documents nothing"
    wrong = {"properties": {"score": {"type": "integer"}, "verdict": {"type": "array"}}}
    assert [m["key"] for m in undocumented(live, wrong, spec)[1]] == ["verdict"], (
        "a listed key of the wrong type is not documented")

    # 2. Ledger: the BTC/USDT 1h row of that morning opens 22 days after it was made.
    assert closes_at(1792972800, "1h") == 1792976400
    assert closes_at(1790985600, "1d") == 1791072000
    assert closes_at(1788220800, "1M") == 1790812800, "a month closes on the 1st of the next"
    assert closes_at(1790985600, "3d") is None
    btc = {"id": "sym:BTC/USDT|1h|1792972800", "who": "sym:BTC/USDT", "timeframe": "1h",
           "made_at": "2026-10-04T06:21:46+00:00", "candle_time": 1792972800,
           "close": 229.263278, "verdict": "READY TO POP", "status": "open"}
    coti = {"id": "sym:COTI/USDT|1d|1790985600", "who": "sym:COTI/USDT", "timeframe": "1d",
            "made_at": "2026-10-04T07:27:42+00:00", "candle_time": 1790985600,
            "close": 0.01407, "verdict": "READY TO DUMP", "status": "open"}
    judged, bad, unread = not_on_a_closed_candle([btc, coti])
    assert len(judged) == 2 and [b["id"] for b in bad] == [btc["id"]] and unread == []
    forming = dict(coti, made_at="2026-10-03T23:59:00+00:00")
    assert len(not_on_a_closed_candle([forming])[1]) == 1, "a still-forming candle passed"
    assert not_on_a_closed_candle([dict(btc, status="void")])[0] == [], (
        "a call they voided with a reason is their fix, not a defect")
    assert not_on_a_closed_candle([dict(btc, made_at=None)])[2], "unreadable is unread, not closed"

    # 3. Range: the 5d up bin of /study/expert that morning -- 43.1% shown, 59.5-68.1% beside it.
    block = {"timeframes": {"5d": {"calibration": {"up": [
        {"bin": 9, "n": 477, "calibrated": 0.4307, "ci95": [0.5954, 0.6812], "usable": True},
        {"bin": 17, "n": 900, "calibrated": 0.52, "ci95": [0.49, 0.55], "usable": True},
        {"bin": 3, "n": 12, "calibrated": 0.9, "ci95": [0.1, 0.3], "usable": False}], "down": [],
        # Live, the block carries these beside the tables; the first run read them as
        # a side and raised (2026-10-04).
        "base_up": 0.4447, "base_down": 0.5441, "n": 11085, "range": ["2021-01-03", "2022-08-21"]}}}}
    judged, outside = outside_their_range(block)
    assert len(judged) == 2 and [o["bin"] for o in outside] == [9], (
        "an unusable bin is not shown as a probability, so it is not judged")
    pooled = {"timeframes": {"5d": {"calibration": {"up": [
        dict(block["timeframes"]["5d"]["calibration"]["up"][0], ci95=[0.40, 0.46])]}}}}
    assert outside_their_range(pooled)[1] == [], "a range computed for the pooled value is the fix"
    assert outside_their_range({"timeframes": {"1M": {"covered": False}}}) == ([], [])

    # 4. DEX-pool coins: the promise is read from llms.txt's Chart Analyzer section; the
    #    candidate is computed from up/down, never from rule_label (which can be zeroed).
    llms = ("## Chart Analyzer\nCoverage: ... a DEX-pool coin gets the drawings and setups "
            "but no verdict (`coverage_note`). What it does not do.\n## Pure Crypto Apps\nx")
    assert "no verdict" in (dex_promise(llms) or "")
    assert dex_promise(llms.replace("but no verdict", "and the same table")) is None
    assert dex_promise("## Supply Analyzer\na DEX-pool coin gets no verdict\n") is None, (
        "a sentence outside the Chart Analyzer section is not its promise")
    side = lambda c, b, lo, n: {"calibrated": c, "base_rate": b, "range": [lo, lo + 0.04], "cases": n}
    sky = {"label": "READY TO POP", "rule_label": "READY TO POP",
           "up": side(0.4734, 0.38, 0.4685, 39480), "down": side(0.30, 0.3833, 0.29, 9000)}
    assert label_candidate(sky) == "READY TO POP"
    assert label_candidate(dict(sky, rule_label="NO EDGE", label="NO EDGE")) == "READY TO POP"
    assert label_candidate(dict(sky, up=side(0.4734, 0.38, 0.4685, 299))) is None, "299 cases"
    assert label_candidate(dict(sky, up=side(0.4299, 0.38, 0.41, 5000))) is None, "4.99 points"
    assert label_candidate(dict(sky, up=side(0.45, 0.38, 0.379, 5000))) is None, (
        "a range that reaches below the base rate")

    # Supply Analyzer (ET-28934, verified 2026-10-04), held here for the same ceiling.
    # Each reading from the shape seen live that morning, with the fix that must clear it.
    from tests.rest.test_supply_analyzer_states_what_its_sources_say import (
        burned_without_a_burn, chain_answer_documented, dilution_flag, emission_dropped,
        fund_disposition, holders_revenue_kind, out_ignores_max, pile_over_supply,
        shared_link_identifiers, two_flags, typical_mismatches)

    # 1. The burned slice: ORE that morning, 2,499,496 "burned" from max minus total supply
    #    while its own emission input said 42,098 new tokens a month and month 0 used 40.
    ore = {"token": {"symbol": "ORE", "slug": "ore-protocol"},
           "slices_today": [{"key": "free", "amount": 500464.27},
                            {"key": "bb_burned", "amount": 2499495.62, "share_pct": 83.32}],
           "inputs": [{"key": "burned_so_far", "value": 2499495.62, "as_of": None,
                       "source": "max supply minus total supply (CoinGecko figures)"},
                      {"key": "emissions_month", "value": 42097.5,
                       "source": "DeFiLlama unlock schedule (ore-protocol)"}],
           "unknown": [{"input": "burns", "why": "not on any feed we read; counted as 0."}],
           "months": [{"in": {"emissions": 40.11}}]}
    assert burned_without_a_burn(ore)["burned"] == 2499495.62
    assert burned_without_a_burn(dict(ore, inputs=[dict(ore["inputs"][0], source="balance of the burn "
                                                        "address on the chain"), ore["inputs"][1]])) is None, (
        "a burn read from a burn source is the fix")
    assert burned_without_a_burn(dict(ore, slices_today=[{"key": "free", "amount": 500464.27},
                                                         {"key": "bb_burned", "amount": 0.0}])) is None, (
        "max minus total moved out of the burned slice is the fix")
    assert burned_without_a_burn({"slices_today": [{"key": "bb_burned", "amount": 5.0}]}) is None, (
        "a burned slice with no source to read is unread, not convicted")
    assert emission_dropped(ore) == (42097.5, 40.11)
    assert emission_dropped(dict(ore, months=[{"in": {"emissions": 42097.5}}])) is None
    assert emission_dropped(dict(ore, months=[])) is None

    # 2. Buybacks: DeFiLlama's own HoldersRevenue sentences, as read that morning.
    payout = holders_revenue_kind
    assert payout("Swap fees and vote incentives distributed to xPHAR voters.") == "distribution"
    assert payout("Share of swap fees distributed to veGIGA stakers (all of the protocol's share).") == "distribution"
    assert payout("Swap fees and bribes going to holders") == "distribution"
    assert payout("Part of swap fees go to veNest lockers (based on the gauge rate)") == "distribution"
    assert payout("Money going to governance token holders") == "distribution"
    assert payout("Around 80% of revenue is used to buyback and burn $PONS tokens.") == "buyback"
    assert payout("Vault fee funds automated BEAN buybacks — 90% burned, 10% distributed to "
                  "BEAN stakers.") == "buyback", "a buyback that also pays stakers is still a buyback"
    assert payout("veDUST revenue distributions are recognized when notified on-chain and DUST "
                  "buybacks on the day they reach the Revenue wallet.") == "buyback", "mixed is not judged"
    assert payout("99% of fees go to Assistance Fund for buying HYPE tokens") == "buyback"
    assert payout("Not applicable — protocol fees route to Curve DAO fee receivers, not CRV token "
                  "holders.") is None, "a sentence that says neither is unread"
    assert payout(None) is None and payout("") is None

    # 3. The pile: CRV that morning, 3.25B sellable against 2.42B total supply.
    crv = {"token": {"symbol": "CRV"}, "pile_today": 3245081474.0, "total_supply": 2422992570.14,
           "max_supply": 3030303031.0, "circulating": 1570993126.0,
           "inputs": [{"key": "staked_total", "value": 1674088348.26}]}
    over = pile_over_supply(crv)
    assert over and over["against"] == "total_supply" and round(over["over_by"]) == 822088904
    assert pile_over_supply(dict(crv, pile_today=1570993126.0)) is None, "a pile inside the supply"
    assert pile_over_supply(dict(crv, total_supply=None))["against"] == "max_supply"
    assert pile_over_supply(dict(crv, total_supply=None, max_supply=None)) is None, (
        "nothing to compare against is unread, not passed or failed")

    # 4. A cited page: Hyperliquid's Fees page that morning, against the record's "kept".
    fees = ("The assistance fund uses the system address 0xfefefefefefefefefefefefefefefefefefefefe. It "
            "converts trading fees to HYPE in a fully automated manner as part of the L1 execution. HYPE "
            "in the assistance fund is burned, removing the tokens permanently from the circulating and "
            "total supply. Growth mode for HIP-3 perps")
    assert fund_disposition(fees) == "burned"
    assert fund_disposition(fees.replace("is burned, removing the tokens permanently from",
                                         "is held, and stays in")) is None
    assert fund_disposition("") is None and fund_disposition(None) is None

    # 5. Links: the Gem Screener links by CoinGecko id first; one id on two rows that morning.
    rows = [{"token": {"symbol": "HYPE", "gecko_id": "hyperliquid", "slug": "hyperliquid",
                       "key": "parent#hyperliquid"}},
            {"token": {"symbol": "HYPE", "gecko_id": "hyperliquid", "slug": "hyperliquid-l1",
                       "key": "hyperliquid-l1"}},
            {"token": {"symbol": "UNI", "gecko_id": "uniswap", "slug": "uniswap", "key": "parent#uniswap"}},
            {"token": {"symbol": "ORE", "gecko_id": "ore", "slug": "ore-protocol", "key": "leaf#6893"}}]
    assert shared_link_identifiers(rows) == ["hyperliquid"]
    assert shared_link_identifiers(rows[2:]) == []

    # 6. The typical inflow: one number on /definitions, others inside the ranges.
    batch = [{"token": {"symbol": "HYPE"}, "status": "range", "yearly_range": [24.73, 29.73]},
             {"token": {"symbol": "PHAR"}, "status": "range", "yearly_range": [41.61, 53.95]},
             {"token": {"symbol": "SEI"}, "status": "range", "yearly_range": [21.36, 21.36]},
             {"token": {"symbol": "X"}, "status": "measured", "yearly_range": [3.0, 3.0]},
             {"token": {"symbol": "Y"}, "status": "unknown", "yearly_range": None}]
    bad = typical_mismatches(batch, 12.34290441022498)
    assert [b["symbol"] for b in bad] == ["HYPE"] and bad[0]["used"] == 5.0
    assert typical_mismatches(batch[1:], 12.34290441022498) == [], (
        "a range as wide as the stated typical, or no range at all, is not a mismatch")

    # 7. Unsupported chain: what the analyzer answered that morning, and what it documents.
    assert chain_answer_documented(500, {"error": {"code": "INTERNAL_SERVER_ERROR"}}) is False
    assert chain_answer_documented(400, {"detail": {"error": {"code": "UNSUPPORTED_CHAIN",
                                                              "message": "x"}}}) is True
    assert chain_answer_documented(400, {"detail": {"error": {"code": "INVALID_CONTRACT"}}}) is True, (
        "any documented 400 code is a documented answer")
    assert chain_answer_documented(200, {"token": {"chain": "dogechain"}}) is True, (
        "reading the chain after all is not a defect")
    assert chain_answer_documented(503, {}) is None, "a 503 says nothing about the chain"

    # 8. Dilution flags: HYPE and ORE that morning, Checks row against the Supply card.
    assert [dilution_flag(v, 0.5, 1.0) for v in (0.0, 0.5, 0.7, 1.0, 1.0252, None)] == [
        "ok", "ok", "caution", "caution", "red", None]
    gs_apps = [{"slug": "hyperliquid", "symbol": "HYPE", "dilution": {"week_pct": 0.0}},
               {"slug": "ore-protocol", "symbol": "ORE", "dilution": {"week_pct": 1.0707}},
               {"slug": "pharaoh-exchange", "symbol": "PHAR", "dilution": {"week_pct": 8.6637}},
               {"slug": "nodata", "symbol": "N", "dilution": {}}]
    sa = [{"token": {"slug": "hyperliquid"}, "dilution_week_pct": 1.0252},
          {"token": {"slug": "ore-protocol"}, "dilution_week_pct": 0.0018},
          {"token": {"slug": "pharaoh-exchange"}, "dilution_week_pct": 15.7105},
          {"token": {"slug": "nodata"}, "dilution_week_pct": 0.3}]
    judged, differ = two_flags(gs_apps, sa, 0.5, 1.0)
    assert judged == 3 and [d["symbol"] for d in differ] == ["HYPE", "ORE"], (
        "two figures with the same flag are one flag; a missing figure is not judged")

    # 9. Tokens out: ORE that morning, "100% of tokens out" with max supply 6x circulating
    #    and the same snapshot recording emissions.
    ore_app = {"symbol": "ORE", "slug": "ore-protocol", "mcap": 65397326, "fdv": 65400201,
               "supply": {"out_pct": 99.9956, "circ": 500629.75},
               "cg": {"max": 3000000.0, "total": 500651.75, "circ": 500629.75},
               "dilution": {"week_pct": 1.0707, "basis": "emissions", "emissions_usd30": 3000944.31}}
    flagged = out_ignores_max(ore_app)
    assert flagged and flagged["circ_of_max_pct"] == 16.7
    assert out_ignores_max(dict(ore_app, dilution={"week_pct": 0.0, "basis": "emissions",
                                                   "emissions_usd30": 0.0})) is None, (
        "with no issuance on record, max minus total may be burned: not judged")
    assert out_ignores_max(dict(ore_app, supply=dict(ore_app["supply"], out_pct=16.7))) is None, "the fix"
    assert out_ignores_max(dict(ore_app, cg={"total": 500651.75})) is None, "no max supply, nothing to ignore"

    # 10. Locked tokens: PHAR that afternoon. The record's reserve was the PHAR the xPHAR
    #     contract holds for its holders, and its staked figure a 44th of it.
    from tests.rest.test_supply_analyzer_states_what_its_sources_say import locked_as_reserve
    phar = {"token": {"symbol": "PHAR"}, "total_supply": 530628030.8, "circulating": 33493320.9,
            "reserve_today": 497134709.9, "inputs": [{"key": "staked_total", "value": 11351535.32}]}
    chain = {"total_supply": 530627319.97, "locked_in_staking_token": 497139187.99}
    seen = locked_as_reserve(phar, chain)
    assert seen and seen["reserve_is_the_locked_tokens"] and seen["staked_shown_share"] < 0.03
    fixed = dict(phar, reserve_today=0.0, inputs=[{"key": "staked_total", "value": 497139187.99}])
    assert locked_as_reserve(fixed, chain) is None, "the locked tokens shown as staked is the fix"
    assert locked_as_reserve(dict(phar, reserve_today=250000000.0,
                                  inputs=[{"key": "staked_total", "value": 497000000.0}]), chain) is None
    assert locked_as_reserve(phar, {"total_supply": 530627319.97, "locked_in_staking_token": 1000.0}) is None, (
        "a staking contract that holds almost nothing proves nothing")
    assert locked_as_reserve(phar, {}) is None, "an unread chain is unread"

    # 11. Unknown schedules: ARB that afternoon. Its record named the vesting schedule
    #     unknown and served next_unlock "none_scheduled"; DeFiLlama's file had 15 Oct.
    from tests.rest.test_supply_analyzer_states_what_its_sources_say import (
        future_unlocks, unknown_served_as_none)
    arb = {"token": {"symbol": "ARB", "slug": "arbitrum"}, "status": "unknown",
           "unknown_names": ["vesting schedule", "emissions"], "next_unlock": {"kind": "none_scheduled"}}
    assert unknown_served_as_none(arb) is True
    assert unknown_served_as_none(dict(arb, next_unlock={"kind": "unknown"})) is False, "the fix"
    assert unknown_served_as_none(dict(arb, next_unlock=None)) is False, "no claim is not a false claim"
    assert unknown_served_as_none(dict(arb, unknown_names=["emissions"])) is False, (
        "a known schedule with nothing ahead may say none")
    dl = {"metadata": {"events": [
        {"timestamp": 1792072833, "noOfTokens": [56125000], "category": "insiders", "unlockType": "cliff",
         "description": "On {timestamp} {tokens[0]} of Team, Contributors & Advisors tokens will be unlocked"},
        {"timestamp": "1790000000", "noOfTokens": [1], "unlockType": "cliff"},
        {"timestamp": "not a time"}]}}
    ahead = future_unlocks(dl, 1791109556)
    assert [a["date"] for a in ahead] == ["2026-10-15"] and ahead[0]["tokens"] == 56125000
    assert ahead[0]["what"] == "Team, Contributors & Advisors"
    assert future_unlocks({}, 1791109556) == [] and future_unlocks(None, 1791109556) == []

    # 12. Max supply: ETH that afternoon, 127,869,954 "max supply" from DeFiLlama's unlock
    #     schedule (the end of its issuance horizon); ETH has no max supply.
    from tests.rest.test_supply_analyzer_states_what_its_sources_say import max_from_a_schedule
    eth = {"token": {"symbol": "ETH", "slug": "ethereum"}, "max_supply": 127869953.59,
           "inputs": [{"key": "max_supply", "value": 127869953.59, "source": "DeFiLlama unlock schedule (ethereum)"}],
           "slices_today": [{"key": "bb_burned", "amount": 5768336.31}]}
    got = max_from_a_schedule(eth)
    assert got and got["max_supply"] == 127869953.59 and got["burned_from_it"] == 5768336.31
    assert max_from_a_schedule(dict(eth, inputs=[dict(eth["inputs"][0], source="CoinGecko via the Gem "
                                                       "Screener snapshot")])) is None
    assert max_from_a_schedule(dict(eth, inputs=[], max_supply=None)) is None, "no max stated is the fix"

    # The Gem Screener refresh rule (2026-09-27), held here for the same
    # ceiling. Stuck means BOTH: stale past 3 cycles AND the newest attempt a
    # recorded failure. A missing field is unreadable (None), never "healthy".
    from tests.rest.test_gem_screener_refresh_keeps_its_own_cadence import _stuck

    six_h = 21600
    assert _stuck({"age_seconds": 3600, "refresh_every_seconds": six_h,
                   "last_attempt": {"ok": False}})[0] is False, (
        "one failed attempt on fresh data is not a stuck pipeline")
    assert _stuck({"age_seconds": 4 * six_h, "refresh_every_seconds": six_h,
                   "last_attempt": {"ok": True}})[0] is False, (
        "stale but the newest attempt succeeded: publishing, not stuck")
    assert _stuck({"age_seconds": 4 * six_h, "refresh_every_seconds": six_h,
                   "last_attempt": {"ok": False, "stage": "audit:x"}})[0] is True
    assert _stuck({"age_seconds": 3 * six_h, "refresh_every_seconds": six_h,
                   "last_attempt": {"ok": False}})[0] is False, (
        "exactly three cycles is the bar, not past it")
    assert _stuck({"refresh_every_seconds": six_h, "last_attempt": {"ok": False}})[0] is None, (
        "no age_seconds is unreadable, and unreadable must not pass")
    assert _stuck({"age_seconds": 4 * six_h, "refresh_every_seconds": 0,
                   "last_attempt": {"ok": False}})[0] is None
    # Stale with no readable attempt is unreadable too: it read "not stuck"
    # and passed (deep pass 2026-09-27, R03, 3/3).
    for attempt in (None, {}, {"ok": "false"}, {"stage": "audit:x"}):
        said = {"age_seconds": 4 * six_h, "refresh_every_seconds": six_h}
        if attempt is not None:
            said["last_attempt"] = attempt
        assert _stuck(said)[0] is None, attempt
    assert _stuck({"age_seconds": 3600, "refresh_every_seconds": six_h})[0] is False, (
        "fresh data needs no attempt to be read")

    # Two readers of their words, held here for the same ceiling. An OpenAPI 3
    # range or default declares a code (A04, 3/3); a curly apostrophe is still
    # the live-invest offer (A03, 3/3).
    from tests.rest.test_prices_status_codes_match_its_own_description import declares
    from tests.mcp.test_community_funds_are_paper_or_live_not_both import (
        offers_live_invest, visible_text)

    assert not declares({"200": {}, "422": {}}, 404)
    assert declares({"200": {}, "4XX": {}}, 404) and declares({"default": {}}, 404)
    assert declares({"404": {}}, 404) and not declares({"5XX": {}}, 404)
    for said in ("Invest in X now &mdash; it&rsquo;s LIVE", "Invest in X now — it’s LIVE",
                 "Invest in X now - it's LIVE", "Invest in X now: its LIVE"):
        assert offers_live_invest(visible_text(said)), said


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


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_traffic_invariants_can_actually_fail():
    """The Build it Better traffic check, refuted before it is believed.

    Counting started on the day it was written: 2 apps of 113 carried one view
    each, so every invariant in it passed over rows that had barely moved. A
    green first run says nothing at all in that state -- it is the shape the
    deep pass of 2026-09-20 found four times in one morning, a check whose
    assertion could not fail with the data it had.

    So each claim is put a case that must be caught, and one that must not.
    """
    from tests.rest.test_build_it_better_traffic_agrees import (
        _agrees, _nests, _series)

    def _app(**kw):
        body = {"first_counted": "2026-09-20",
                "all_time": {"views": 10, "visitors": 6, "uses": 4},
                "last_7d": {"views": 10, "visitors": 6, "uses": 4},
                "last_30d": {"views": 10, "visitors": 6, "uses": 4},
                "likes": 2,
                "daily": [{"day": "2026-09-20", "views": 10, "visitors": 6,
                           "uses": 4}]}
        body.update(kw)
        return body

    # Claim 3: the windows nest, and uses/visitors nest inside views.
    assert _nests(_app(), "/x") == [], _nests(_app(), "/x")
    assert _nests(_app(last_7d={"views": 11, "visitors": 6, "uses": 4}), "/x"), \
        "a seven-day figure above the thirty-day one read as agreement"
    assert _nests(_app(all_time={"views": 9, "visitors": 6, "uses": 4}), "/x"), \
        "a thirty-day figure above all_time read as agreement"
    assert _nests(_app(last_30d={"views": 4, "visitors": 4, "uses": 9},
                       all_time={"views": 40, "visitors": 40, "uses": 90},
                       last_7d={"views": 1, "visitors": 1, "uses": 1}), "/x"), \
        "uses above the page loads they are counted out of read as agreement"
    # And NOT visitors above views. Their definitions say where views come
    # from and not where visitors do, so that comparison would be our unit
    # against their figure -- deliberately absent, and it stays absent.
    assert _nests(_app(last_7d={"views": 4, "visitors": 9, "uses": 4},
                       last_30d={"views": 4, "visitors": 9, "uses": 4},
                       all_time={"views": 4, "visitors": 9, "uses": 4}),
                  "/x") == [], \
        "a claim we cannot source to their words became a defect we would file"
    # Rule 8 one layer down: a window that does not carry a metric is not a
    # window that reads zero.
    assert _nests(_app(last_7d={}), "/x") == []

    # Claim 2: a range is the sum of its days -- their own definition.
    problems, moved = _series(_app(), "/x", "2026-09-20")
    assert problems == [] and moved, (problems, moved)
    short = _app(daily=[{"day": "2026-09-20", "views": 3, "visitors": 3,
                         "uses": 3}])
    assert _series(short, "/x", "2026-09-20")[0], \
        "a thirty-day total unrelated to the days under it read as agreement"

    # Claim 4: nothing earlier than the day counting started was recorded.
    earlier = _app(daily=[{"day": "2026-09-19", "views": 10, "visitors": 6,
                           "uses": 4}])
    assert any("2026-09-19" in p
               for p in _series(earlier, "/x", "2026-09-20")[0]), \
        "traffic dated before counting began read as history they do not have"
    assert _series(_app(first_counted="2026-09-18"), "/x", "2026-09-20")[0], \
        "an app disagreeing with the board about when counting started passed"
    # But an app first visited the day AFTER counting began is not a
    # contradiction: "nothing earlier was recorded" bounds first_counted from
    # below, it does not fix it. PRE-0145 read 8 of 14 apps as defects for
    # this, while 6 whose first visit fell on the 20th said the 20th (deep
    # pass of 2026-09-21: our clause, not their sentence).
    visited_later = _app(first_counted="2026-09-21",
                         daily=[{"day": "2026-09-20", "views": 0, "visitors": 0,
                                 "uses": 0},
                                {"day": "2026-09-21", "views": 10, "visitors": 6,
                                 "uses": 4}])
    assert _series(visited_later, "/x", "2026-09-20") == ([], True), \
        _series(visited_later, "/x", "2026-09-20")
    # ...while a figure dated before its own first_counted still fails.
    early_figure = _app(first_counted="2026-09-21")
    assert _series(early_figure, "/x", "2026-09-20")[0], \
        "a figure on the 20th under a first_counted of the 21st read as agreement"
    # An all-zero series makes the sum vacuous, and the caller is told so.
    quiet = _app(all_time={"views": 0, "visitors": 0, "uses": 0},
                 last_7d={"views": 0, "visitors": 0, "uses": 0},
                 last_30d={"views": 0, "visitors": 0, "uses": 0},
                 daily=[{"day": "2026-09-20", "views": 0, "visitors": 0,
                         "uses": 0}])
    assert _series(quiet, "/x", "2026-09-20") == ([], False)

    # Claim 1: the board's row is the app's own figure, bracketed against the
    # counters moving between the two reads.
    row = {"path": "/x", "views": 10, "visitors": 6, "uses": 4, "likes": 2}
    assert _agrees(row, _app(), _app(), "/x") == []
    grew = _app(last_30d={"views": 12, "visitors": 7, "uses": 5})
    assert _agrees(row, _app(), grew, "/x") == [], \
        "a visitor arriving between the two reads must not be a contradiction"
    assert _agrees({**row, "views": 99}, _app(), grew, "/x"), \
        "a board figure outside the bracket read as the counter moving"
    assert _agrees({**row, "likes": 9}, _app(), _app(), "/x"), \
        "a like count the app does not report read as agreement"

    # And through the check itself (deep pass of 2026-09-21, A07): `_agrees`
    # was right and the loop was not. It held the ORIGINAL board row, read
    # before any app, against a bracket opened minutes later -- so one real
    # visit in between read as their board contradicting itself. Only a row
    # read inside the bracket may be judged.
    from types import SimpleNamespace

    from qa.measure import CURRENT_MEASUREMENT
    from tests.rest import test_build_it_better_traffic_agrees as traffic

    def _reply(status, body):
        return SimpleNamespace(status_code=status, json=lambda: body)

    def _drive(first_row, fresh, app_body):
        boards = iter([_reply(200, {"counting_since": "2026-09-20",
                                    "apps": [first_row]}), fresh])

        class _Anon:
            def get(self, path, params=None):
                return next(boards) if path == traffic.BOARD \
                    else _reply(200, app_body)

        traffic.test_the_traffic_figures_agree_with_the_days_they_are_made_of(
            _Anon())
        return CURRENT_MEASUREMENT.get()

    one_more = {"views": 11, "visitors": 6, "uses": 4}
    visited = _app(all_time=one_more, last_7d=one_more, last_30d=one_more,
                   daily=[{"day": "2026-09-20", **one_more}])
    said = _drive(row, _reply(200, {"apps": [{**row, "views": 11}]}), visited)
    assert said.verdict == "passed", said.reason
    with pytest.raises(AssertionError, match="99 views"):
        _drive(row, _reply(200, {"apps": [{**row, "views": 99}]}), visited)
    # A board that could not be re-read inside the bracket leaves claim 1
    # unmeasured for that app -- said, not held against the stale row.
    said = _drive(row, _reply(503, {"detail": "unavailable"}), visited)
    assert said.verdict == "passed" and "NOT measured" in said.reason \
        and "/x" in said.reason, said.reason


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_build_stats_window_reading_can_be_wrong_in_both_directions():
    """The contradiction on /build-stats, and the three innocent shapes it
    must not call one.

    The reading is narrow on purpose: a total that equals the sum of its own
    series holds nothing outside that series, so a `first_session` before the
    series begins cannot be in it. Every step of that rests on their own
    fields -- but each step is also a way to be wrong, and the live response
    today satisfies all of them, so only a fixture can show the check has a
    negative side at all.
    """
    from tests.rest.test_build_stats_covers_the_period_it_claims import (
        window_problems)

    def _body(**kw):
        body = {"totals": {"sessions": 6, "messages": 60, "tool_calls": 12},
                "daily_activity": [
                    {"date": "2026-02-01", "sessions": 3, "messages": 30,
                     "tool_calls": 6},
                    {"date": "2026-02-02", "sessions": 3, "messages": 30,
                     "tool_calls": 6}],
                "first_session": "2025-11-23"}
        body.update(kw)
        return body

    # The live shape, 2026-09-20: totals ARE the window, and the first session
    # is before it.
    problems, facts = window_problems(_body())
    assert problems, "a total published under a date it does not reach passed"
    assert "2025-11-23" in problems[0] and "2026-02-01" in problems[0], problems
    assert facts["totals_equal_to_the_series"] == ["sessions", "messages",
                                                   "tool_calls"], facts

    # A first session inside the window is no contradiction at all.
    assert window_problems(_body(first_session="2026-02-01"))[0] == []
    assert window_problems(_body(first_session="2026-02-02T09:00:00Z"))[0] == []

    # Totals LARGER than the series hold something the series does not, and
    # this check has nothing to say about them -- the honest half. Without
    # this the check would fire on every platform that publishes a recent
    # window under a true lifetime total, which is normal and not a defect.
    bigger = _body(totals={"sessions": 900, "messages": 9000,
                           "tool_calls": 1800})
    problems, facts = window_problems(bigger)
    assert problems == [] and facts["totals_equal_to_the_series"] == [], facts

    # Rule 8: a field that is not there is not a field that reads early.
    assert window_problems(_body(first_session=None))[0] == []
    empty = window_problems({"totals": {"sessions": 1}, "daily_activity": []})
    assert empty == ([], {"measured": False}), empty

    # Nor is it a field that reads INSIDE the window (deep pass of
    # 2026-09-21, A18). Absent, renamed or not a date, first_session gave no
    # problem with `measured` still True, and the verdict PASSED on "the first
    # session they record (None) falls inside that window". Driven through
    # the check itself, both ways, because that sentence is the function's.
    from types import SimpleNamespace

    from qa.marks import Inconclusive
    from tests.rest import test_build_stats_covers_the_period_it_claims as page

    def _drive(body):
        reply = SimpleNamespace(status_code=200, json=lambda: body)
        page.test_the_build_totals_reach_back_to_the_date_they_are_published_under(
            SimpleNamespace(get=lambda path, params=None: reply))

    absent = {k: v for k, v in _body().items() if k != "first_session"}
    for unread in (absent, {**absent, "first_session_at": "2025-11-23"},
                   _body(first_session=None), _body(first_session=""),
                   _body(first_session="unknown")):
        assert window_problems(unread)[1]["measured"] is False, unread
        with pytest.raises(Inconclusive, match="first_session"):
            _drive(unread)
    with pytest.raises(AssertionError, match="2025-11-23"):
        _drive(_body())
    _drive(_body(first_session="2026-02-01"))
    # A07, deep pass of 2026-09-22: only `>= series_from` was asked, so a
    # first session AFTER the series ends passed as "inside that window".
    # It is not inside, and not this defect either.
    with pytest.raises(Inconclusive, match="after"):
        _drive(_body(first_session="2026-03-01"))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_requirement_split_into_numbered_items_is_not_a_dropped_one():
    """The first stranger's request on Build it Better nearly became a false
    report against them.

    ET-26171 arrived 2026-09-20 as one paragraph of three sentences, and the
    generator wrote it into the spec as three numbered items -- every sentence
    whole, nothing lost, which is the generator working. `dropped()` looked
    for the whole PARAGRAPH as one substring, could not find it across the
    numbering, and reported it as a requirement in the request and in no spec.
    The row opened NOT RAISED and was one sweep away from being filed.

    The original defect this check exists for is the opposite shape: on
    ET-26036 the generator kept the first eight sentences and lost the last
    line entirely, and cut another line at the full stop inside "(e.g.
    Bollinger Bands, MACD, RSI)". Both must still be caught, so the repair is
    to fall back to SENTENCES of a line rather than to similarity: a line is
    carried when every sentence of it appears whole, and a sentence that was
    cut or lost is still missing.
    """
    from tests.rest.test_build_it_better_board import dropped

    paragraph = ("It is necessary to remove all news functions and focus "
                 "exclusively on token information. Keep the TradingView "
                 "charts. It is also necessary to add AI information.")
    numbered = ("BB-SPEC\n"
                "  1. It is necessary to remove all news functions and focus "
                "exclusively on token information.\n"
                "  2. Keep the TradingView charts.\n"
                "  3. It is also necessary to add AI information.\n")
    assert dropped(paragraph, numbered) == [], (
        "a paragraph the generator split into numbered items, losing nothing, "
        "reads as a dropped requirement")

    # ET-26036's own defect: the last sentence never arrives.
    lost = ("BB-SPEC\n"
            "  1. It is necessary to remove all news functions and focus "
            "exclusively on token information.\n"
            "  2. Keep the TradingView charts.\n")
    assert dropped(paragraph, lost), "a sentence that is in no spec passed"

    # And the cut: the sentence is there up to a full stop inside it.
    cut_request = "Add indicators (e.g. Bollinger Bands, MACD, RSI) to the chart."
    cut_spec = "BB-SPEC\n  1. Add indicators (e.g.\n  2. Bollinger Bands, MACD, RSI) to the chart.\n"
    assert dropped(cut_request, cut_spec), (
        "a requirement cut at the full stop inside e.g. passed, which is the "
        "defect the whole check was written for")

    # A05, deep pass of 2026-09-22: REPLY-0021 promises "never inside
    # parentheses", and SENTENCE_END split inside them, so a generator doing
    # the same passed. A cut inside a parenthesis is a cut.
    from tests.rest.test_build_it_better_board import sentences_of
    assert sentences_of("Show signals (Buy only. Sell later). Then stop.") == [
        "Show signals (Buy only. Sell later).", "Then stop."]
    inside = "Show signals (Buy only. Sell later.) on the chart."
    assert dropped(inside, "BB-SPEC\n  1. Show signals (Buy only.\n"
                           "  2. Sell later.) on the chart.\n"), (
        "a requirement cut inside its parentheses passed")

    # A line that is carried verbatim is still carried.
    assert dropped("Export any screen to CSV without a paid tier.",
                   "BB-SPEC\n  1. Export any screen to CSV without a paid tier.\n") == []

    # The spec check (test_build_it_better_spec_keeps_the_request) on
    # ET-26924, 2026-09-26: the writer now leaves withdrawn and repeated
    # BB-CHANGEs out of the amendments and says how many in a footer. That
    # is accounting, not a loss -- but only while the count covers what is
    # missing, and never for the newest change.
    from tests.rest.test_build_it_better_spec_keeps_the_request import judge

    def record(footer, carried, changes=("first change", "second change", "third change")):
        spec = ("BB-SPEC for App\n  1. Do one thing.\n\nYour changes (BB-CHANGE) -- scope:\n"
                + "".join(f"  C{i}. {c}\n" for i, c in enumerate(carried, 1)) + footer)
        stamp = lambda n: f"2026-09-24T10:0{n}:00+00:00"
        return {"app_name": "App", "messages": [
            {"kind": "BB-REQUEST", "at": stamp(0), "body": "App: Do one thing."},
            *[{"kind": "BB-CHANGE", "at": stamp(i + 1), "body": c}
              for i, c in enumerate(changes)],
            {"kind": "BB-SPEC", "at": stamp(9), "body": spec}]}

    said = "(2 earlier BB-CHANGE messages withdrawn or repeated by the requester -- not part of the scope.)\n"
    assert judge(record(said, ["third change"]))["changes_missing"] == [], (
        "two withdrawn changes, counted by the spec and both older than the "
        "carried one, read as dropped")
    assert len(judge(record("(1 earlier BB-CHANGE message withdrawn or repeated.)\n",
                            ["third change"]))["changes_missing"]) == 2, (
        "the spec counts fewer than it left out and the excess passed")
    assert judge(record(said, ["second change"]))["changes_missing"] == [
        "third change"], "the newest change was excused as withdrawn"
    assert len(judge(record("", ["third change"]))["changes_missing"]) == 2, (
        "with no footer a missing change is a dropped change again")

    # 2026-09-30: the check called 27 lines of ET-27671 and 4 of ET-28378
    # "lost" and both specs held every one of them. A request that numbers its
    # own lines ("1. Audience. ...") comes back as spec item "N. Audience. ...":
    # their writer numbers the items itself and the requester's marker goes
    # with it, the words all stay. The marker is a list label, not a
    # requirement. What is still a loss: a line that is gone, a line whose
    # words changed, a cut, and a number that is part of the text ("2026
    # roadmap").
    def numbered(request, items):
        spec = "BB-SPEC for App\n" + "".join(
            f"  {i}. {t}\n" for i, t in enumerate(items, 1))
        return {"app_name": "App", "messages": [
            {"kind": "BB-REQUEST", "at": "2026-09-30T10:00:00+00:00",
             "body": "App: " + request},
            {"kind": "BB-SPEC", "at": "2026-09-30T10:09:00+00:00", "body": spec}]}

    intro = "This request has two parts."
    request = f"{intro}\n1. Audience. Degens hunting gems.\n2) First load. Under 500 kB."
    whole = [intro, "Audience. Degens hunting gems.", "First load. Under 500 kB."]
    assert judge(numbered(request, whole))["lost"] == [], (
        "a requester's own list numbers, the spec renumbers, and every word "
        "survived: that is not a lost line")
    assert judge(numbered(request, whole[:2]))["lost"] == [
        "2) First load. Under 500 kB."], "a numbered line that is gone passed"
    changed = [intro, "Audience. Degens hunting coins.", whole[2]]
    assert judge(numbered(request, changed))["lost"] == [
        "1. Audience. Degens hunting gems."], (
        "a numbered line whose words changed passed")
    cut = "Add indicators (e.g. RSI, MACD) to the chart."
    assert judge(numbered(f"{intro}\n1. {cut}",
                          [intro, "Add indicators (e.g.", "RSI, MACD) to the chart."]
                 ))["lost"] == [f"1. {cut}"], (
        "stripping the number hid the e.g. cut the whole check exists for")
    year = "2026 roadmap: ship the chart first."
    assert judge(numbered(f"{intro}\n{year}", [intro, "roadmap: ship the chart first."]
                          ))["lost"] == [year], (
        "a number that belongs to the sentence was read as list numbering")

    # The same day, the second half of ET-27671's "loss": the message log
    # cuts every body at 8000 characters, mid-word and unmarked (both of its
    # BB-SPEC copies, and two of ET-26924's), while the record's `spec_text`
    # carried all 28 items and the BB-CHANGE. But `spec_text` is not the
    # accepted text either: it is re-rendered under the CURRENT app name, and
    # on ET-26608 that rewrote the requester's own amendment into 'Rename ...
    # from "Gem Screener" to "Gem Screener"'. So the spec compared is the
    # logged one, and `spec_text` only where the log cut it and `spec_text`
    # continues the cut copy word for word. A body the log may have cut is
    # never counted either way (rule 8): a cut request compares fewer lines
    # and passes falsely.
    CAP = 8000
    preamble = "BB-SPEC for App\n\nWhat we will build: " + "w" * CAP + "\n"
    whole_spec = preamble + "  1. Do one thing.\n  2. Do another thing.\n"
    cut_copy = whole_spec[:CAP]
    short_spec = "BB-SPEC for App\n  1. Do one thing.\n  2. Do another thing.\n"

    def logged(request, log_spec, spec_text=None, change=None):
        messages = [{"kind": "BB-REQUEST", "at": "2026-09-30T10:00:00+00:00",
                     "body": "App: " + request}]
        if change is not None:
            messages.append({"kind": "BB-CHANGE", "at": "2026-09-30T10:05:00+00:00",
                             "body": change})
        messages.append({"kind": "BB-SPEC", "at": "2026-09-30T10:09:00+00:00",
                         "body": log_spec})
        return {"app_name": "App", "spec_text": spec_text, "messages": messages}

    two = "Do one thing.\nDo another thing."
    said = judge(logged(two, cut_copy, spec_text=whole_spec))
    assert said["state"] == "read" and said["lost"] == [], (
        "the log's copy is cut at 8000 characters and the spec itself is whole: "
        f"read as a loss ({said})")
    assert judge(logged(two, cut_copy, spec_text=preamble + "  1. Do one thing.\n")
                 )["lost"] == ["Do another thing."], (
        "a line missing from the spec behind the cut passed")
    assert judge(logged(two, cut_copy))["state"] == "unread", (
        "no spec_text and a logged spec at the cap was counted as read")
    assert judge(logged(two, cut_copy, spec_text=short_spec))["state"] == "unread", (
        "a spec_text that does not continue the cut copy was taken for the spec")
    renamed = "Rename the app from Old to App. Nothing else changes."
    amended = f"\nYour changes (BB-CHANGE) -- scope:\n  C1. {renamed}\n"
    rerendered = short_spec + amended.replace("Old", "App")
    assert judge(logged(two, short_spec + amended, spec_text=rerendered,
                        change=renamed))["changes_missing"] == [], (
        "spec_text re-rendered under the new name was read over the accepted "
        "spec, and the requester's own rename read as dropped (ET-26608)")
    long_request = ("Do one thing.\n" + "y" * CAP)[:CAP - len("App: ")]
    assert judge(logged(long_request, short_spec))["state"] == "unread", (
        "a request the log may have cut was compared as if it were whole")
    cut_change = ("Add a third thing. " + "z" * CAP)[:CAP]
    assert judge(logged(two, short_spec, change=cut_change))["state"] == "unread", (
        "a BB-CHANGE the log may have cut was checked against the amendments")

    # The check that reports the cut itself (#139), refuted the same way.
    _a_log_body_is_called_cut_only_when_the_record_holds_the_rest()


def _a_log_body_is_called_cut_only_when_the_record_holds_the_rest():
    """test_the_message_log_carries_each_message_whole, refuted before it is
    trusted: a whole copy, a re-rendered spec_text (ET-26608) and a body that
    merely sits at 8000 characters are not cuts; a strict prefix is. Called at
    the end of test_a_requirement_split_into_numbered_items_is_not_a_dropped_one:
    tests/meta grows only by replacement, and this is the same check family."""
    from tests.rest.test_build_it_better_log_keeps_whole_bodies import cuts

    def record(logged_spec, spec_text, request="App: Do it.", improvements="Do it."):
        return {"app_name": "App", "spec_text": spec_text,
                "improvements": improvements, "messages": [
                    {"kind": "BB-REQUEST", "at": "t0", "body": request},
                    {"kind": "BB-SPEC", "at": "t1", "body": logged_spec}]}

    spec = "BB-SPEC for App\n  1. Do it.\n" + "w" * 9000
    assert cuts(record(spec, spec)) == [], "a whole copy was called cut"
    assert cuts(record(spec[:8000], "BB-SPEC for New\n" + spec[16:])) == [], (
        "a spec_text re-rendered under a new name was called a cut of the log")
    assert cuts(record(spec[:8000], None)) == [], (
        "a body at the cap with nothing to compare it with was called cut")
    found = cuts(record(spec[:8000], spec))
    assert [(c["kind"], c["logged"], c["whole"]) for c in found] == [
        ("BB-SPEC", 8000, len(spec))], found
    assert [c["kind"] for c in cuts(record(spec, spec, request="App: Do",
                                           improvements="Do it."))] == [
        "BB-REQUEST"], "a cut request was not seen"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_route_their_ai_names_is_matched_against_the_template_not_the_text(
        monkeypatch):
    """The third check of the #85 family, refuted before it is trusted.

    It passed on its first run, which proves nothing on its own: NEX-0049
    named two routes and both are published. What has to be shown is that it
    can still say no, and that it does not say no for the wrong reason --
    `{instance_id}` against `{id}` is the same segment, and a full stop at the
    end of a sentence is not part of a path.

    A06, deep pass of 2026-09-21, in both directions. A `<id>` placeholder
    stopped the extractor at the `<`, so `/api/v1/cloned-bots/<id>/settings`
    became `/api/v1/cloned-bots/` and FAILED as unpublished. And a template
    slot took any word at all, so `/api/v1/cloned-bots/start-trading` matched
    `{instance_id}` and PASSED.
    """
    from tests.rest.test_nexus_routes_exist import _matches, routes_named

    published = {"/api/v1/cloned-bots/{instance_id}/settings",
                 "/api/v1/cloned-bots/{instance_id}/toggle-trading",
                 "/api/v1/event-cards/{card_id}"}

    said = routes_named(
        "Use `PATCH /api/v1/cloned-bots/{instance_id}/settings` first, then "
        "POST /api/v1/cloned-bots/{id}/toggle-trading?enabled=true. "
        "Read the card at /api/v1/event-cards/30015006.")
    assert "/api/v1/cloned-bots/{instance_id}/settings" in said, said
    assert "/api/v1/event-cards/30015006" in said, (
        "a trailing full stop was taken as part of the path")
    assert all(p in published or _matches(p, published) for p in said), said

    # Their placeholder name is theirs to choose; the segment is the same one.
    assert _matches("/api/v1/cloned-bots/{id}/toggle-trading", published)
    # A concrete id fills a template segment.
    assert _matches("/api/v1/event-cards/30015006", published)

    # And the two ways it must still say no.
    assert not _matches("/api/v1/cloned-bots/{id}/rebalance", published), (
        "a route nobody publishes matched a published template"
    )
    assert not _matches("/api/v1/cloned-bots/{id}/settings/advanced", published), (
        "a longer path matched a shorter template"
    )
    # C05, deep pass of 2026-09-22 evening (3/3): a placeholder in HIS text
    # matched any published segment, literal included, so
    # /exchange/{pair} passed against a document that publishes only
    # /exchange/pairs. His placeholder stands only where theirs does.
    assert not _matches("/api/v1/exchange/{pair}", {"/api/v1/exchange/pairs"})
    assert not _matches("/api/v1/{x}/{y}/{z}", published)
    assert _matches("/api/v1/event-cards/{id}", published)
    assert routes_named("no routes here, only prose about fees") == set()
    # A11, deep pass of 2026-09-22: the check is about routes he TELLS an
    # agent to call. One he names to say it does not exist, or to steer an
    # agent away from, is not an instruction, and failed as one.
    assert routes_named(
        "There is no `/api/v1/cloned-bots/{id}/start`; use "
        "`POST /api/v1/cloned-bots/{id}/toggle-trading` instead.") == {
        "/api/v1/cloned-bots/{id}/toggle-trading"}
    assert routes_named("Do not call /api/v1/admin/reset, and "
                        "/api/v1/legacy/fund does not exist.") == set()
    # B03 (deep pass of 2026-09-24, 3/3): a negation EARLIER in the sentence,
    # across a comma, dropped the route he then tells the agent to call -- the
    # route was never judged. A negation reaches across a comma only while no
    # instruction starts after it.
    assert routes_named("If the clone does not start, call "
                        "`POST /api/v1/cloned-bots/{id}/restart`.") == {
        "/api/v1/cloned-bots/{id}/restart"}
    assert routes_named("Rather than polling, call GET /api/v1/foo/bar.") == {
        "/api/v1/foo/bar"}
    assert routes_named("Do not call /api/v1/admin/reset, /api/v1/admin/wipe "
                        "or anything under them.") == set()

    # A06 (1): `<name>` is a path parameter too. Both spellings are verbatim
    # from our own diary of their answers, the second with a space inside.
    said = routes_named(
        "PATCH `/api/v1/cloned-bots/<id>/settings`, or REST `POST "
        "https://cymetica.com/api/v1/exchange/<EVCDX-SYMBOL>/orders` or "
        "`POST /api/v1/exchange/<EVCDX symbol>/orders` once its index token "
        "is queried.")
    assert said == {"/api/v1/cloned-bots/<id>/settings",
                    "/api/v1/exchange/<EVCDX-SYMBOL>/orders",
                    "/api/v1/exchange/<EVCDX symbol>/orders"}, said
    assert _matches("/api/v1/cloned-bots/<id>/settings", published)
    # Markup after a path is not a placeholder of it.
    assert routes_named("<code>/api/v1/cloned-bots/available</code>") == {
        "/api/v1/cloned-bots/available"}

    # A06 (2): the prefixes as their openapi-public.json served them on
    # 2026-09-21 -- /cloned-bots/ publishes literal route words BESIDE its id
    # slot; /protocols/ publishes a slot and nothing else; /crypto-outlook/
    # puts `coins` beside a slot that holds a NAME, not an id.
    live = {"/api/v1/cloned-bots/{instance_id}",
            "/api/v1/cloned-bots/{instance_id}/settings",
            "/api/v1/cloned-bots/available", "/api/v1/cloned-bots/clone",
            "/api/v1/cloned-bots/my-clones",
            "/api/v1/clones/protocol-revenue/protocols/{slug}",
            "/api/v1/crypto-outlook/{symbol}", "/api/v1/crypto-outlook/coins",
            "/api/v1/exchange/{symbol}/orders", "/api/v1/exchange/pairs"}
    assert not _matches("/api/v1/cloned-bots/start-trading", live), (
        "a route word nobody publishes filled the id slot beside the route "
        "words they do publish")
    # A literal they publish at that position is that route, whatever the
    # slot beside it is named.
    assert not _matches("/api/v1/exchange/pairs/orders", live)
    assert _matches("/api/v1/exchange/EVCDX-THE-NUCLEAR-REVIVAL/orders", live)
    assert not _matches("/api/v1/cloned-bots/available/settings", live), (
        "their own `available` route word was read as a bot's id")
    # ... and every shape that must still match.
    assert _matches("/api/v1/cloned-bots/available", live)
    assert _matches("/api/v1/cloned-bots/d778102d-cf3f-4d86-ad1e-2d8511b345dc",
                    live), "a real instance id no longer fills its slot"
    assert _matches(
        "/api/v1/cloned-bots/d778102d-cf3f-4d86-ad1e-2d8511b345dc/settings", live)
    assert _matches("/api/v1/clones/protocol-revenue/protocols/aave-dao", live), (
        "a slug is a word, and a slot with no route words beside it takes one")
    assert _matches("/api/v1/crypto-outlook/btc", live), (
        "a symbol slot takes a name; only an id slot refuses a word")

    # Run whole, both directions, against a fresh answer in a stub diary.
    import contextvars
    import types
    from datetime import datetime, timezone

    from tests.rest import test_nexus_routes_exist as check

    def _run(text):
        answer = {"type": "answer", "id": "NEX-9999", "text": text,
                  "at": datetime.now(timezone.utc).isoformat()}
        monkeypatch.setattr(check, "_nexus", lambda: types.SimpleNamespace(
            load=lambda: [answer]))
        document = types.SimpleNamespace(status_code=200,
                                         json=lambda: {"paths": dict.fromkeys(live)})
        # A copied context, so the check's measurement stays out of this meta
        # test's own run record.
        contextvars.copy_context().run(
            check.test_every_route_nexus_tells_an_agent_to_call_is_published,
            types.SimpleNamespace(get=lambda path, **kw: document))

    _run("Tighten it with `PATCH /api/v1/cloned-bots/<id>/settings`.")
    with pytest.raises(AssertionError, match="start-trading"):
        _run("Then `POST /api/v1/cloned-bots/start-trading` to begin.")

    # A bare prefix in prose names a family of routes, not one to call: "the
    # /api/v1/cloned-bots endpoints" is not a claim that the prefix itself is
    # served, and read as a route it failed as unpublished. A prefix of a
    # route they publish passes; a prefix of nothing they publish still fails.
    _run("The /api/v1/cloned-bots endpoints and the /api/v1/clones family "
         "cover it; start with `PATCH /api/v1/cloned-bots/<id>/settings`.")
    with pytest.raises(AssertionError, match="/api/v1/clob"):
        _run("The /api/v1/clob endpoints cover it.")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_coin_the_second_look_could_not_read_is_not_a_missing_coin(
        monkeypatch):
    """A05, deep pass of 2026-09-21. The two looks triaged differently.

    The first look sends a 404 or a 5xx on to the second -- theirs, "always
    200 for a known coin" broken -- and anything else to `unmeasured`, rule
    8. The second look counted ANY non-200 as missing, so a coin cold on the
    first pass and rate-limited on the second was filed as a coin with no
    outlook, on the strength of our own request budget.

    Run whole with a stub client, on both sides of the line.
    """
    import contextvars
    from types import SimpleNamespace

    from qa.marks import Inconclusive
    from qa.measure import CURRENT_MEASUREMENT
    from tests.rest import test_coin_outlook_answers_for_every_coin_it_lists as outlook

    monkeypatch.setattr(outlook.time, "sleep", lambda seconds: None)

    def drive(looks):
        """`looks`: symbol -> the text view's status on each look, in order.
        Returns what the check ended on and the measurement it emitted."""
        queue = {symbol: list(codes) for symbol, codes in looks.items()}
        roster = {"coins": [{"symbol": symbol} for symbol in looks]}

        def get(path, **kw):
            if path == outlook.ROSTER:
                return SimpleNamespace(status_code=200, json=lambda: roster)
            last = path.rsplit("/", 1)[1]
            if last.endswith(".txt"):
                return SimpleNamespace(status_code=queue[last[:-4]].pop(0))
            return SimpleNamespace(status_code=404)

        def run():
            try:
                outlook.test_every_coin_on_the_roster_answers_on_the_text_view(
                    SimpleNamespace(get=get))
            except (Inconclusive, AssertionError) as exc:
                return type(exc).__name__, CURRENT_MEASUREMENT.get()
            return "passed", CURRENT_MEASUREMENT.get()

        # A copied context, so the check's measurement stays out of this
        # meta test's own run record.
        return contextvars.copy_context().run(run)

    ended, m = drive({"BTC": [404, 429], "ETH": [404, 404], "SOL": [200]})
    assert ended == "AssertionError" and m.left == ["ETH"], (ended, m and m.left)
    assert "1 of 2" in m.reason, (
        f"a coin we could not read the second time was counted as measured: "
        f"{m.reason}")
    assert any(u.startswith("BTC") for u in m.population["unmeasured"]), m.population

    # A 5xx the second time is theirs, exactly as it is the first time.
    ended, m = drive({"BTC": [404, 503], "SOL": [200]})
    assert ended == "AssertionError" and m.left == ["BTC"], (ended, m and m.left)

    # Cold, then answered: their documented behaviour, a pass.
    assert drive({"BTC": [404, 200], "SOL": [200]})[0] == "passed"

    # The only coin unreadable the second time: nothing was measured at all.
    ended, _ = drive({"BTC": [404, 429]})
    assert ended == "Inconclusive", ended


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_startup_call_that_could_not_be_read_is_not_one_that_demands_a_key():
    """A09, deep pass of 2026-09-21. Every non-200 on a public call was the
    credential defect.

    The page marks /startups/terms and /startups/line as needing no account,
    and the check's own docstring names what breaks that: a call the page calls
    public that DEMANDS A KEY. A 429 or a 503 went out as "marked as needing
    no account, and it answered HTTP 429 to a client carrying no credential",
    and a 503 on /startups/mine as the wrong refusal -- our budget and their
    restart, each filed as a door that will not open.

    Run whole, per subject: 401/403 on a public call is the defect, 404 is its
    own defect (the route the page documents is not there -- the docstring
    draws that line for `mine`), and anything else is unread. Unread with no
    defect is inconclusive; a defect is measured whatever else was lost.
    """
    import contextvars
    from types import SimpleNamespace

    from qa.marks import Inconclusive
    from tests.rest import test_startup_line_is_reachable_as_documented as startup

    path_of = {"terms": startup.TERMS, "line": startup.LINE, "mine": startup.MINE}

    # A07 (deep pass of 2026-09-24, 3/3): the FIRST "status:" arrow list on
    # the page was read as the application's, so a bid or a build queue's
    # statuses above it went out as "promised and not served". The line that
    # names the application, or the page's only one; `queue_status` is not
    # `status`.
    for above in ("<p>Bid status: pending -> won | lost</p>",
                  "<p>queue_status: queued → building → shipped</p>"):
        page = (above + "<p>Application status: submitted → reviewing → "
                "accepted | declined</p>")
        assert startup.page_statuses(page) == (
            "submitted", "reviewing", "accepted", "declined"), page
    assert startup.page_statuses(
        "<p>Status: submitted → reviewing → accepted | declined</p>") == (
        "submitted", "reviewing", "accepted", "declined")
    assert startup.page_statuses("<p>Bid status: a -> b</p><p>Order status: "
                                 "c -> d</p>") is None, (
        "two lists and neither the application's: which one it is is unread")

    # Their markup, verbatim from 2026-09-22: every word in its own <code>.
    said = ("<code>submitted</code> → <code>reviewing</code> → "
            "<code>accepted</code> | <code>declined</code>")

    def page(mine="account", line="–", statuses=said):
        # Their table as served on 2026-09-22, cut to the three GET rows, and
        # the /startups/mine row's prose, which is where the page prints the
        # status vocabulary.
        row = ('<tr><td><span class="m">GET</span> <code>{p}</code></td>'
               '<td>{d}</td><td>{a}</td></tr>')
        mine_says = (f"Your applications with <code>status</code>: {statuses}."
                     if statuses else "Your applications.")
        return ('<h3 id="startup">Turn your App into a Startup</h3><table>'
                + row.format(p="/startups/terms", d="terms", a="–")
                + row.format(p="/startups/line", d="the line", a=line)
                + row.format(p="/startups/mine", d=mine_says, a=mine) + "</table>")

    def drive(page_html=None, statuses=("submitted", "reviewing", "accepted",
                                         "declined"), line_body=None, **status):
        served = {
            startup.TERMS: (200, {"statuses": dict.fromkeys(statuses, "."),
                                  "token_chains": {"solana": "SOL"}}),
            startup.LINE: (200, line_body or {"line": [], "count": 0,
                                              "rules": "Highest bid first, ties by arrival."}),
            startup.MINE: (401, {"detail": "Not authenticated"}),
            startup.PAGE: (200, page() if page_html is None else page_html)}
        for name, code in status.items():
            served[path_of[name]] = (code, {"detail": "."})

        def get(path, **kw):
            code, body = served[path]
            return SimpleNamespace(status_code=code, json=lambda: body,
                                   text=body if isinstance(body, str) else "")

        # A copied context, so the check's measurement stays out of this meta
        # test's own run record.
        contextvars.copy_context().run(
            startup.test_the_startup_calls_answer_the_reader_their_own_page_promises,
            SimpleNamespace(get=get))

    drive()
    for name, code in (("terms", 429), ("line", 503), ("mine", 503),
                       ("terms", 500)):
        with pytest.raises(Inconclusive, match=f"HTTP {code}"):
            drive(**{name: code})

    # The defect the docstring names, and the two it keeps apart from it.
    with pytest.raises(AssertionError, match="needing no account"):
        drive(terms=401)
    with pytest.raises(AssertionError, match="needing no account"):
        drive(line=403, terms=429)
    with pytest.raises(AssertionError, match="does not exist"):
        drive(line=404)
    with pytest.raises(AssertionError, match="not theirs"):
        drive(mine=200)
    with pytest.raises(AssertionError, match="HTTP 404"):
        drive(mine=404)

    # A13, deep pass of 2026-09-22: "the Auth column is the contract", and
    # the check read our own constants, never their page. The page is read
    # now: a call it marks `account` that refuses a stranger is right, and
    # one it marks public that refuses is the defect -- whichever call it is.
    drive(page(line="account"), line=401)
    with pytest.raises(AssertionError, match="needing no account"):
        drive(page(mine="–"), mine=401)
    # An unread page, or a row it no longer carries, is not a contract.
    with pytest.raises(Inconclusive, match="page"):
        drive("<html>maintenance</html>")

    # A05, deep pass of 2026-09-22 evening (3/3). The statuses were our own
    # copy, never read off the page the docstring names as the claimant, so a
    # page and an endpoint that dropped `reviewing` together failed as a
    # promise not served. And a line with no `count` passed.
    shorter = "<code>submitted</code> &rarr; <code>accepted</code> | <code>declined</code>"
    drive(page(statuses=shorter), statuses=("submitted", "accepted", "declined"))
    with pytest.raises(AssertionError, match="reviewing"):
        drive(page(), statuses=("submitted", "accepted", "declined"))
    with pytest.raises(AssertionError, match="count"):
        drive(line_body={"line": [], "rules": "Highest bid first."})
    with pytest.raises(Inconclusive, match="status"):
        drive(page(statuses=None))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_build_that_shipped_late_is_not_a_build_that_shipped_on_time():
    """The pass verdict this check was about to send to #112.

    ET-26036 passed its deadline at 2026-09-20T20:25:59Z with nothing built;
    we filed it as #112. Four hours later Cymetica shipped it -- stage
    "shipped", our_url /weekly-signal, resolved_at 2026-09-21T00:25:27Z -- and
    `overdue()` returned None the moment `our_url` appeared, whatever the
    clock said. The check went green and verify.py composed a **pass** on
    #112: "the check that recorded this defect now passes". That sentence
    would have told them their 24-hour promise held on the one request where
    it provably did not.

    Their own record disagrees with the verdict we nearly sent: the item
    carries `on_time: false`, and resolved_at is 3h59m past deadline_at.

    So lateness is read from the clock rather than from the presence of a
    link: a shipped build whose resolution is after its deadline is late, one
    resolved inside it is not, and a shipped build with no readable
    resolution time is reported as unreadable rather than counted either way
    (rule 8).
    """
    from tests.rest.test_build_it_better_board import overdue
    from datetime import datetime, timezone

    now = datetime(2026, 9, 21, 1, 0, tzinfo=timezone.utc)
    deadline = "2026-09-20T20:25:59.571403+00:00"

    # What we filed: past the deadline, nothing shipped.
    assert overdue({"ticket": "ET-26036", "deadline_at": deadline,
                    "stage": "funded"}, now)

    # What they then did: shipped it, four hours late. Still late.
    late = overdue({"ticket": "ET-26036", "deadline_at": deadline,
                    "stage": "shipped", "our_url": "/weekly-signal",
                    "resolved_at": "2026-09-21T00:25:27.792893+00:00",
                    "on_time": False}, now)
    assert late, "a build that shipped four hours late read as shipped on time"
    assert late.get("shipped_late"), late

    # The stranger's ticket, shipped inside its own window: not late.
    assert overdue({"ticket": "ET-26171",
                    "deadline_at": "2026-09-21T20:37:17.710254+00:00",
                    "stage": "shipped", "our_url": "/coinmarketcup",
                    "resolved_at": "2026-09-21T00:25:28.821118+00:00",
                    "on_time": True}, now) is None

    # Shipped, past the deadline, and no readable resolution time: not
    # counted as late, and not counted as on time either.
    unreadable = overdue({"ticket": "ET-9999", "deadline_at": deadline,
                          "stage": "shipped", "our_url": "/x"}, now)
    assert unreadable is not None and unreadable.get("unreadable"), unreadable

    # Still inside its window with nothing shipped: not evidence of anything.
    assert overdue({"ticket": "ET-0001",
                    "deadline_at": "2026-09-22T00:00:00+00:00",
                    "stage": "funded"}, now) is None


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_published_ranking_that_admits_recency_is_not_the_defect():
    """#111, fixed the way the report offered, four hours after we filed it.

    We said: "Publishing what `rank` actually is would close this; so would
    ranking by the key you published." They published it -- llms.txt now gives
    the formula, says `rank` does not depend on `q`, and states outright that
    "while no row has verified evidence or a confirmed replication, the order
    is simply newest first ... read evidence_verified and replications on the
    row, never the position".

    The check would have gone on failing: its three conditions -- nothing
    verified, rank fixed across queries, order is recency -- are all still
    true, and are now all DOCUMENTED. That is a check still arguing with a
    sentence nobody publishes any more, and the next level-V run would have
    sent "still reproducible" on a report they had fixed.

    So the reading gains one question, asked of the published text before any
    of the three: does the document itself say the order is recency while
    nothing is verified? If it does, there is nothing left to contradict.
    """
    from tests.rest.test_agent_board_ranks_what_it_says_it_ranks import (
        discloses_recency)

    before = ("- [GET /api/v1/agent-board/search](/api/v1/agent-board/search): "
              "Search playbooks (ranked by verified return x replications)")
    after = ("- [GET /api/v1/agent-board/search](/api/v1/agent-board/search): "
             "Search playbooks. Each row's `rank` = evidence weight (verified "
             "return, only when `evidence_verified` is true; unverified rows "
             "get half weight) x (1 + confirmed replications) x status weight "
             "x a recency decay (72-hour scale). `rank` does not depend on "
             "`q`. While no row has verified evidence or a confirmed "
             "replication, the order is simply newest first")

    assert not discloses_recency([before]), (
        "the sentence we filed against reads as a disclosure, so the check "
        "could never have opened the defect in the first place")
    assert discloses_recency([after]), (
        "the sentence they published, which says the order is newest first "
        "while nothing is verified, still reads as a contradiction")
    # A document that mentions recency somewhere else entirely is not a
    # disclosure about THIS ordering.
    assert not discloses_recency(
        ["- [GET /api/v1/agent-board/search](...): ranked by verified return "
         "x replications",
         "- [GET /api/v1/feed](...): sorted by recency, newest first"])
    # B10, deep pass of 2026-09-21. A line that still claims the verified
    # ordering and merely MENTIONS a decay and an unverified badge is not a
    # disclosure: any recency word beside any unproven word passed it, so #111
    # would have read as fixed on a sentence that says what it always said.
    assert not discloses_recency(
        ["- [GET /api/v1/agent-board/search](...): ranked by verified return "
         "x replications; unverified rows are badged; recency decay applied"]), (
        "a decay factor named beside an unverified badge read as a published "
        "statement that the order is recency")
    assert not discloses_recency(
        ["- [GET /api/v1/agent-board/search](...): ranked by verified return "
         "x replications x decayed by recency; unverified rows get half weight"])
    # The statement itself, in the other words it could come in.
    assert discloses_recency(
        ["- [GET /api/v1/agent-board/search](...): while nothing is verified "
         "the board is ordered by recency"])
    # B07 (deep pass of 2026-09-24, 3/3): a DENIAL of the order read as a
    # statement of it -- no negation guard -- so the PASSING, FIX_CLAIMED row
    # would go on passing on a sentence that says the board is NOT by age.
    for denial in ("ranked by verified return x replications; not sorted by "
                   "recency; unverified rows badged",
                   "never newest-first; unverified rows last",
                   "the order isn't simply by recency while rows are unverified"):
        assert not discloses_recency(
            [f"- [GET /api/v1/agent-board/search](...): {denial}"]), denial


# ---------------------------------------------------------------------------
# Whole vendor checks, driven over stub clients. Added by the deep pass of
# 2026-09-21 for checks no meta test drove before (A11, A14, A16, A17): each
# gap sat on a branch the helpers alone never reach.
# ---------------------------------------------------------------------------
def _check_module(relpath: str, name: str):
    import importlib.util

    spec = importlib.util.spec_from_file_location(name, REPO / relpath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _drive_check(check, *clients) -> tuple[str, str]:
    """Run one vendor check end to end; return (verdict, reason).

    The check's own `conclude` runs, so the branch that decides is the real
    one. Its measurement is taken back off this meta test afterwards: left in
    place, the recorder would file this meta result under the vendor claim.
    """
    from qa.marks import Inconclusive
    from qa.measure import CURRENT_MEASUREMENT

    CURRENT_MEASUREMENT.set(None)
    try:
        check(*clients)
        verdict, reason = "passed", ""
    except AssertionError as exc:
        verdict, reason = "failed", str(exc)
    except Inconclusive as exc:
        verdict, reason = "inconclusive", str(exc)
    finally:
        measured = CURRENT_MEASUREMENT.get()
        CURRENT_MEASUREMENT.set(None)
    if measured is not None:
        assert measured.verdict == verdict, (measured.verdict, verdict)
        reason = measured.reason or reason
    return verdict, reason


class _Reply:
    """One HTTP answer, as much of it as these checks read."""

    def __init__(self, status, body=None, text=None, headers=None):
        self.status_code, self._body = status, body
        self.text = text if text is not None else json.dumps(body)
        self.headers = headers or {}

    def json(self):
        if self._body is None:
            raise ValueError("not JSON")
        return self._body


class _Rest:
    """A `rest_anon` with no network behind it: answers keyed by path, or by
    (path, q) where the query matters, and a 404 for anything not given."""

    def __init__(self, answers: dict):
        self.answers = answers

    def get(self, path, params=None):
        q = (params or {}).get("q")
        return (self.answers.get((path, q)) or self.answers.get(path)
                or _Reply(404, {"detail": "not here"}))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_list_the_gates_no_longer_carry_is_unread_not_empty():
    """A15, deep pass of 2026-09-22. `body.get("paused_tokens") or []` read a
    renamed or dropped list as an empty one, so every paused row failed as
    "absent from paused_tokens" -- a sentence about a list that is not in the
    response (rule 8). No meta test drove this check before."""
    mod = _check_module("tests/rest/test_token_gates_agree_with_their_own_design.py",
                        "token_gates_m")
    rows = [{"token": "ET10", "withdrawals_open": False,
             "user_message_when_paused": "Paused for review."},
            {"token": "USDC", "withdrawals_open": True}]

    def gates(**lists):
        return _Rest({mod.GATES: _Reply(200, {"gates": rows, **lists})})

    check = mod.test_the_token_gates_say_the_same_thing_three_times
    whole = {"paused_tokens": ["ET10"], "governed_tokens": ["ET10", "USDC"]}
    assert _drive_check(check, gates(**whole))[0] == "passed"
    assert _drive_check(check, gates(paused_tokens=[],
                                     governed_tokens=["ET10", "USDC"]))[0] == "failed"
    verdict, reason = _drive_check(check, gates(governed_tokens=["ET10", "USDC"]))
    assert verdict == "inconclusive" and "paused_tokens" in reason, (verdict, reason)
    verdict, reason = _drive_check(check, gates(paused_tokens=["ET10"]))
    assert verdict == "inconclusive" and "governed_tokens" in reason, (verdict, reason)
    # What the lists that ARE there say still stands.
    assert _drive_check(check, gates(paused_tokens=["USDC"]))[0] == "failed"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_fund_and_start_check_needs_both_steps_to_pass_89():
    """A08, deep pass of 2026-09-22: #89's pass read "every step that moves a
    clone forward accepts x-api-key" off whichever of /fund and /go-live the
    document still listed, so /fund vanishing from their openapi passed on
    /go-live alone -- a pass verify.py would send on a step nobody can read.
    Both have to be there to pass; a missing one is unread (rule 8)."""
    mod = _check_module("tests/rest/test_cloned_bots_surface.py", "clone_surface_m")
    agent = {"parameters": [{"in": "header", "name": "x-api-key"},
                            {"in": "header", "name": "authorization"}]}
    human = {"parameters": [{"in": "header", "name": "authorization"}]}

    def spec(**routes):
        paths = {f"{mod.PREFIX}/{{instance_id}}/{seg.replace('_', '-')}":
                 {"post": op} for seg, op in routes.items()}
        return _Rest({mod.OPENAPI: _Reply(200, {"paths": paths})})

    check = mod.test_one_credential_funds_and_starts_a_clone
    assert _drive_check(check, spec(fund=agent, go_live=agent))[0] == "passed"
    assert _drive_check(check, spec(fund=human, go_live=agent))[0] == "failed"
    verdict, reason = _drive_check(check, spec(go_live=agent))
    assert verdict == "inconclusive" and "fund" in reason, (verdict, reason)
    # A step missing does not hide a step that refuses.
    assert _drive_check(check, spec(go_live=human))[0] == "failed"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_profile_link_check_reads_the_skill_it_says_either_fix_satisfies(
        monkeypatch):
    """A11, deep pass of 2026-09-21. The docstring -- and the report we sent
    -- says the fix is theirs to pick: add `profile_url` to the four sleeves,
    or change the skill's line. But SKILL was only a string in `sources`,
    never fetched, so a skill that now says "`profile_url` or `url`" still
    read as the defect. The skill is read now, and when funds lack the field
    it is the deciding half: an unread skill is Inconclusive (rule 8). No
    meta test drove this check before; there was nothing to fold it into."""
    mod = _check_module("tests/mcp/test_fund_profile_link_is_where_the_skill_says.py",
                        "fund_profile_link_m")
    monkeypatch.setattr(mod, "PAUSE_S", 0.0)

    funds = {"AIB-POWER": {"symbol": "AIB-POWER",
                           "profile_url": "https://cymetica.com/fund/AIB-POWER"},
             "MA-RIPPLE": {"symbol": "MA-RIPPLE",
                           "url": "https://cymetica.com/ma-fund"}}

    class _Http:
        def __init__(self, answer):
            self.answer = answer

        def get(self, url, **kwargs):
            assert url == mod.SKILL, url
            return self.answer

    class _Mcp:
        def __init__(self, skill, roster=funds):
            self.roster, self.http = roster, _Http(skill)

        def call(self, tool, args):
            if tool == "list_funds":
                return {"success": True, "result": {
                    "funds": [{"symbol": s} for s in self.roster]}}
            return {"success": True,
                    "result": {"fund": self.roster[args["symbol"]]}}

    def skill(line):
        return _Reply(200, text="# Fund research\n\n...\n\n## Links to cite\n\n"
                                f"{line}\n- The whole range: `list_funds`\n")

    check = mod.test_every_listed_fund_carries_the_profile_link_the_skill_names

    # The skill as it stood: a sleeve with only `url` is the defect.
    verdict, reason = _drive_check(
        check, _Mcp(skill("- One fund: `profile_url` from `get_fund`")))
    assert verdict == "failed" and "MA-RIPPLE" in reason, (verdict, reason)

    # Their second option, taken: the skill names `url` for the sleeves.
    verdict, reason = _drive_check(check, _Mcp(skill(
        "- One fund: `profile_url` from `get_fund` (the M&A, FTA and event "
        "card sleeves carry `url` instead)")))
    assert verdict == "passed", (
        f"the skill fix the docstring and the report both call sufficient "
        f"still read as the defect: {reason}")
    # And said as a sub-item under the line rather than on it.
    verdict, _ = _drive_check(check, _Mcp(skill(
        "- One fund: `profile_url` from `get_fund`\n"
        "  - for MA-RIPPLE, FTA-* and EVENT-CARD: `url`")))
    assert verdict == "passed"

    # The skill unread while a fund lacks the field: the half that decides was
    # not measured.
    verdict, reason = _drive_check(check, _Mcp(_Reply(503, text="busy")))
    assert verdict == "inconclusive", (verdict, reason)
    # A skill that no longer says what to cite for one fund leaves nothing to
    # hold a missing field against.
    verdict, reason = _drive_check(check, _Mcp(_Reply(200, text="# moved\n")))
    assert verdict == "inconclusive", (verdict, reason)

    # Every fund carrying profile_url is the fund-side fix, whatever the skill
    # read did: the line they published names it.
    only_aib = {"AIB-POWER": funds["AIB-POWER"]}
    assert _drive_check(check, _Mcp(_Reply(503, text="busy"), only_aib))[0] == "passed"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_board_compared_over_no_shared_row_is_not_a_relevance_score():
    """A14, deep pass of 2026-09-21. When the two queries shared no row --
    `data: []` under the second, or rows with no `id` -- the board check
    passed "`rank` moves with the query on 0 of 0 row(s)", a relevance claim
    over nothing (rule 10). Rows without an id were worse: every one keyed to
    None, so each was compared with the LAST row of the other query. Both are
    Inconclusive now, and the defect the check was written for still fails.

    Considered folding into test_a_published_ranking_that_admits_recency_is_
    not_the_defect; that one reads the disclosure predicate alone, and this is
    the comparison branch, which only a whole run reaches.
    """
    mod = _check_module("tests/rest/test_agent_board_ranks_what_it_says_it_ranks.py",
                        "agent_board_m")
    llms = _Reply(200, text=(
        "- [GET /api/v1/agent-board/search](/api/v1/agent-board/search): "
        "Search playbooks (ranked by verified return x replications)\n"))

    def rows(ids=True, ranks=(0.36374, 0.14878, 0.07984)):
        made = []
        for n, (rank, day) in enumerate(zip(ranks, ("19", "13", "05"))):
            row = {"title": f"p{n}", "rank": rank,
                   "created_at": f"2026-09-{day}T00:00:00Z",
                   "replications": {"confirmed": 0, "claimed": 0},
                   "evidence_verified": False, "pnl_usdc": None}
            if ids:
                row["id"] = f"pb-{n}"
            made.append(row)
        return made

    def board(broad, narrow):
        return _Rest({mod.LLMS: llms,
                      (mod.SEARCH, mod.QUERIES[0]): _Reply(200, {"data": broad}),
                      (mod.SEARCH, mod.QUERIES[1]): _Reply(200, {"data": narrow})})

    check = mod.test_the_board_is_ranked_by_the_key_its_own_document_publishes

    verdict, reason = _drive_check(check, board(rows(), []))
    assert verdict == "inconclusive", (
        f"a second query sharing no row with the first read as a relevance "
        f"score: {verdict}: {reason}")
    verdict, reason = _drive_check(
        check, board(rows(ids=False), rows(ids=False, ranks=(0.5, 0.4, 0.3))))
    assert verdict == "inconclusive", (
        f"rows with no id were compared against whichever row came last: "
        f"{verdict}: {reason}")

    # The defect as filed, and the relevance score that is not it.
    assert _drive_check(check, board(rows(), rows()))[0] == "failed"
    # A04, deep pass of 2026-09-22: the docstring says any one condition
    # failing is enough to "stay quiet", and three branches PASSED instead
    # -- so #111 would have read VERIFIED FIXED on a board still ranked
    # newest-first with one proved row, or with a rank that jitters. Quiet
    # is inconclusive; only the disclosure is the fix.
    assert _drive_check(
        check, board(rows(), rows(ranks=(0.9, 0.1, 0.05))))[0] == "inconclusive"
    proved = rows()
    proved[2]["evidence_verified"] = True
    assert _drive_check(check, board(proved, proved))[0] == "inconclusive"
    shuffled = rows(ranks=(0.07984, 0.36374, 0.14878))
    assert _drive_check(check, board(shuffled, shuffled))[0] == "inconclusive"
    # A03, deep pass of 2026-09-22 evening (3/3): `rank or 0` and
    # `created_at or ""` turned a field the board stopped carrying into a
    # value, so a renamed `rank` or a dropped `created_at` failed "exactly
    # newest-first" having read neither. A field that is not there is unread.
    for drop in ("rank", "created_at"):
        blind = rows()
        for row in blind:
            row.pop(drop)
        verdict, reason = _drive_check(check, board(blind, blind))
        assert verdict == "inconclusive", (
            f"rows with no {drop} were judged: {verdict}: {reason}")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_refusal_that_blames_trust_level_for_a_wording_is_the_defect():
    """A16, deep pass of 2026-09-21. The check's own comment names the
    regression it exists for -- a refusal of a WORDING attributed to trust
    level -- but `denies_identity` sat outside the verdict, so "The wording of
    this query is not permitted at your trust level" passed with a suffix. And
    the predicate read "not a" anywhere beside "trust level", so "not allowed
    at your trust level" counted as a denial of it. No meta test drove this
    check before; there was nothing to fold it into."""
    from qa.client import McpError

    mod = _check_module("tests/mcp/test_restricted_query_says_why.py",
                        "restricted_query_m")

    class _Mcp:
        def __init__(self, hint):
            self.refusal = {"error": "QUERY_RESTRICTED",
                            "reason": "OTHER_USERS_DATA",
                            "parameter": "query", "hint": hint}

        def call(self, tool, args):
            if args.get("query") == mod.ORDINARY:
                return {"markets": [{"id": 1}]}
            raise McpError("tool error", payload={"result": {"content": [
                {"type": "text", "text": json.dumps(self.refusal)}]}})

    check = mod.test_a_restricted_query_says_which_rule_it_tripped

    # Their hint as shipped on 2026-09-20.
    live = ("The wording of this parameter matched a restricted-topic filter. "
            "It is about the wording, not your identity or trust level. "
            "Rephrase the question.")
    assert _drive_check(check, _Mcp(live))[0] == "passed"
    assert _drive_check(check, _Mcp(
        "It is the wording that tripped this, not a trust-level decision."))[0] == "passed"

    for blamed in ("The wording of this query is not permitted at your trust level",
                   "The wording of this query is not allowed at your trust level",
                   "This wording needs a higher trust level"):
        verdict, reason = _drive_check(check, _Mcp(blamed))
        assert verdict == "failed", (
            f"a wording refusal attributed to trust level passed: {blamed!r}: "
            f"{reason}")
        assert "trust level" in reason or "identity" in reason, reason

    # C06, deep pass of 2026-09-22 evening (3/3): a denial of EITHER word
    # anywhere satisfied the predicate, so a hint that denies identity and
    # blames trust level in the next breath passed. Every mention has to sit
    # inside a denial.
    for blamed in ("The wording is not about your identity; it needs a higher "
                   "trust level.",
                   "It is about the wording, not your identity. Your trust "
                   "level does not permit this query."):
        verdict, reason = _drive_check(check, _Mcp(blamed))
        assert verdict == "failed", (
            f"a hint blaming trust level passed beside a denial of identity: "
            f"{blamed!r}: {reason}")
    assert _drive_check(check, _Mcp(
        "About the wording only -- nothing to do with your identity or your "
        "trust level."))[0] == "passed"

    # B08 (deep pass of 2026-09-24, 3/3): a denial in any of five phrasings
    # and no other, so a hint saying exactly the right thing in other words
    # would fail -- and open a new row, filed without asking.
    for denied in ("The wording of this parameter matched a restricted-topic "
                   "filter. It does not depend on your identity or trust level.",
                   "It is the wording; it is unrelated to your identity or trust "
                   "level.",
                   "The wording tripped it, independent of your trust level.",
                   "The wording tripped it; it isn't about your identity."):
        verdict, reason = _drive_check(check, _Mcp(denied))
        assert verdict == "passed", (denied, reason)
    # A03: "wording" was a substring test -- presence where the claim is a
    # value, the shape this very check was rewritten to stop -- so a hint
    # DENYING the wording passed as "its hint says it is about the wording".
    verdict, reason = _drive_check(check, _Mcp(
        "This refusal is not about the wording; it is not about your identity "
        "or trust level either."))
    assert verdict == "failed", reason

    # A17, deep pass of 2026-09-22: `parameter` had to be one of four names,
    # so a refusal naming `prompt` for the `query` we sent passed -- a field
    # the caller cannot reword because it never sent one.
    wrong = _Mcp(live)
    wrong.refusal["parameter"] = "prompt"
    assert _drive_check(check, wrong)[0] == "failed"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_unreadable_probe_is_not_a_public_get_that_agrees():
    """A17, deep pass of 2026-09-21. A 429 or 5xx on a path only /openapi.json
    declares went to `unreadable`, and the verdict still said "every public
    GET declared in /openapi.json is also in /openapi-public.json" -- a claim
    about the one path nobody read (rule 8). A 200 is still the defect, with
    or without an unreadable path beside it. No meta test drove this check
    before; there was nothing to fold it into."""
    mod = _check_module("tests/discovery/test_the_two_openapi_documents_agree.py",
                        "openapi_agree_m")
    check = mod.test_a_public_get_in_openapi_json_is_in_the_curated_schema_too

    def documents(**probes):
        answers = {mod.SMALL: _Reply(200, {"paths": {"/api/v1/shared": {},
                                                     "/api/v1/prices": {},
                                                     "/api/v1/arena/market": {}}}),
                   mod.CURATED: _Reply(200, {"paths": {"/api/v1/shared": {}}})}
        answers.update({path: _Reply(code, {}) for path, code in probes.items()})
        return _Rest(answers)

    for code in (429, 503):
        verdict, reason = _drive_check(check, documents(**{
            "/api/v1/prices": code, "/api/v1/arena/market": 401}))
        assert verdict == "inconclusive", (
            f"a probe answering {code} passed as agreement: {reason}")

    assert _drive_check(check, documents(**{
        "/api/v1/prices": 401, "/api/v1/arena/market": 405}))[0] == "passed"
    assert _drive_check(check, documents(**{
        "/api/v1/prices": 200, "/api/v1/arena/market": 503}))[0] == "failed"

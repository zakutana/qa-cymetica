"""VER: what a verification claims must be what we can stand behind.

`verify.py` says one thing to the vendor on a pass: *"the check that recorded
this defect now passes, under the same definition it failed under"*, and
*"Because it matches the one recorded at the failure, this is the same test,
not a rewritten one that happens to pass."*

That is exactly right when the pinned fingerprint is the one the row failed
under, and it is not what we could say about 44 of the 57 pass verifications
already accepted: their fingerprint is one a `pin_fingerprint` event put there
by hand. qa/fold.py:293 pins the failing fingerprint by itself, inside the run,
so a pin EVENT only ever exists because a person wrote one.

Those 27 report/finding pairs split two ways, and the difference is why the
sentence says PINNED and not REPAIRED. Some definitions really were repaired
("the check definition moved on 2026-09-07 and the platform did not"). Others
were pinned because the pre-contract runs recorded no fingerprint at all, so
there was never anything to match. Calling those a repair is the same overclaim
turned around -- and it was written here for an hour, an hour after finding the
first one, before the pin reasons were read.

Every pin carries a reason. They were good reasons and they stayed in the
repository, while a sentence contradicting them was sent.

The fold does not record where a pinned fingerprint came from -- the row
carries the value alone -- so the provenance is read from the journal, which
has it: a `pin_fingerprint` event naming this finding and this value.

This file holds the claim to the truth. Fails at 730674f: `body()` prints the
identity sentence for every pass.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


def _verify():
    path = REPO / "scripts" / "verify.py"
    spec = importlib.util.spec_from_file_location("verify_mod_claim", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _item(**over):
    base = {
        "finding_id": "CYM-a", "report_id": 76, "verdict": "pass",
        "fingerprint": "ae9ec31c", "run_id": "run-x", "checked_at": "2026-09-08T07:20:30+00:00",
        "tree_sha": "e48a7013", "prereg_id": "PRE-0065",
        "checks": ["tests/discovery/test_build_onboarding.py::test_x"],
        "title": "a /build recipe sends an agent to a browser route",
    }
    base.update(over)
    return base


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_pass_on_an_unrepaired_check_still_claims_the_same_definition():
    """The ordinary case must keep its strongest TRUE sentence -- and since
    A8 of the review of 2026-09-23 (3/3), "the same test" is true only when
    the helpers the check calls match the failure's too. A helper rewritten
    after #119, #113, #89, #121 and #116 failed left their verifications
    saying "not a rewritten one" about a check that had been rewritten."""
    verify = _verify()
    evidence = verify.body(_item(helpers_same=True))["evidence"]
    assert "under the same definition it failed under" in evidence
    assert "matches the one recorded at the failure" in evidence
    # H01 (deep pass of 2026-09-24, 3/3): helpers_fingerprint hashes the
    # helpers in the check's OWN file, not what it imports or its fixtures,
    # and the sentence said "the helper functions the check calls -- this is
    # the same test". It says what was compared, and what was not.
    assert "not a rewritten one" not in evidence, evidence
    assert "own file" in evidence and "imports" in evidence, evidence

    # The failure predates helper fingerprints, or its run was pruned: the
    # test function is the one that failed, and nothing more is claimed.
    unknown = verify.body(_item())["evidence"]
    assert "not a rewritten one" not in unknown, unknown
    assert "same recorded definition" in unknown and "helper" in unknown, unknown

    # A helper it calls changed: said, like a pin.
    moved = verify.body(_item(helpers_same=False))["evidence"]
    assert "not a rewritten one" not in moved and "helper" in moved, moved
    assert verify.body(_item(helpers_same=False))["verdict"] == "pass"

    # B02 (deep pass 2026-09-25): the hash now reads module constants too, so
    # a failure hashed by the old formula is no comparison -- unknown, never
    # "a helper changed" about a check nobody touched.
    row = {"checks": ["t.py::test_c"], "reproduced_in": ["run-old"]}

    def ran(hashed, formula):
        result = {"nodeid": "t.py::test_c", "role": "verdict",
                  "helpers_fingerprint": hashed}
        return {"results": [dict(result, helpers_formula=formula) if formula else result]}

    real_load = verify.load_run
    try:
        verify.load_run = lambda run_id: ran("h-old", None)
        assert verify.helpers_match(row, ran("h-new", 2)) is None
        verify.load_run = lambda run_id: ran("h-same", 2)
        assert verify.helpers_match(row, ran("h-same", 2)) is True
        assert verify.helpers_match(row, ran("h-moved", 2)) is False
    finally:
        verify.load_run = real_load


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_pass_on_a_hand_pinned_check_says_so_and_carries_the_reason():
    """A hand-pinned definition may not be sold as the one that failed.

    This is the sentence, not the verdict: the check does pass and the fix is
    real. What must not go out is "this is the same test, not a rewritten one",
    on a row where we cannot know that -- because that is the one claim the
    vendor cannot check for themselves, and it is the reason they are being
    asked to believe the rest.

    It must say PINNED, not REPAIRED. The 27 affected rows split two ways: some
    definitions were repaired, and some were pinned because the pre-contract
    runs recorded no fingerprint at all, so there is nothing they could have
    matched. Calling the second group repaired is the same overclaim pointing
    the other way, and it was written into this file for an hour before anyone
    read the pin reasons that say which is which.
    """
    repaired = ("Deep-pass repair T01: the passing sentence printed the left "
                "operand for both sides on non-equality relations.")
    bootstrapped = ("Report #46 recorded the failure with measured values. The "
                    "pre-contract runs never recorded a fingerprint.")

    for reason in (repaired, bootstrapped):
        sent = _verify().body(_item(pin=reason))
        evidence = sent["evidence"]
        assert "under the same definition it failed under" not in evidence
        assert "matches the one recorded at the failure" not in evidence
        assert "PINNED" in evidence
        assert "REPAIRED" not in evidence, (
            "a pin is not proof of a repair; the reason says which this is"
        )
        assert reason in evidence, (
            "the justification exists and is written down; withholding it "
            "while sending a weaker claim helps nobody"
        )
        # The verdict is unchanged: a pinned check that passes is still a pass,
        # and downgrading it would hide a real fix.
        assert sent["verdict"] == "pass"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_pin_is_read_from_the_journal_by_id_and_by_value(tmp_path, monkeypatch):
    """A pin EVENT is always a hand-written override, so its presence is the test.

    qa/fold.py:293 pins the fingerprint a row failed under by itself, inside
    the run. Nothing else writes that field except `pin_fingerprint`, so an
    event carrying the value being verified means a human replaced the
    definition -- there is no innocent reading of it.

    Matched on the value as well as the finding, because a row can be repaired
    twice. Only the pin naming THIS fingerprint describes the definition this
    verification is about; an older one describes a definition nobody is
    sending.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.state import append_event

    mod = _verify()
    for at, value, reason in (
        ("2026-09-07T21:45:02+00:00", "first-fp", "Deep-pass repair T01: rewritten"),
        ("2026-09-07T22:10:00+00:00", "second-fp", "widened after their answer to #78"),
    ):
        append_event({"type": "pin_fingerprint", "at": at, "by": "operator",
                      "source": "scripts/withdraw.py", "finding_id": "CYM-a",
                      "value": value, "reason": reason})

    assert mod.pin_reason("CYM-a", "second-fp") == "widened after their answer to #78"
    assert mod.pin_reason("CYM-a", "first-fp") == "Deep-pass repair T01: rewritten"
    assert mod.pin_reason("CYM-a", "never-pinned") is None, (
        "a fingerprint no pin names is one the fold wrote at the failure"
    )
    assert mod.pin_reason("CYM-other", "second-fp") is None


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_check_with_hundreds_of_captures_still_fits_their_evidence_field():
    """2026-09-28, #130: their verification endpoint answered 422 -- the
    `evidence` field has max_length 8000 -- because the public-pages check
    cites a capture per page it read and `_evidence_offer` listed every id
    (~200, 66 characters each). The correction was owed and never arrived.
    A few ids to name what we hold, and the count, is what fits."""
    verify = _verify()
    ids = [f"{i:064x}" for i in range(250)]
    evidence = verify.body(_item(verdict="fail", identity="ast",
                                 evidence_ids=ids))["evidence"]
    assert len(evidence) <= 8000, len(evidence)
    assert ids[0] in evidence, "the offer still names what we hold"
    assert "250" in evidence, "and says how many there are"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_fail_says_which_reading_failed(monkeypatch):
    """Week finding of 2026-10-18: a FAIL went to the vendor as "the check that recorded this
    defect still fails" and nothing else -- not which check, not what it expected, not what it
    read. They cannot act on that, and we cannot be corrected on it: the #93 FAIL of 2026-10-21
    rested on a route whose own llms.txt line said "(session JWT)", and the text they got never
    named the route. So a fail carries, per failing check of the adjudicating run, its nodeid,
    what it expected, what it read, and the reason it gave -- inside their 8000-character field."""
    verify = _verify()
    node = "tests/rest/test_documented_gets_accept_the_agent_key.py::test_every_documented_get"
    run = {"run_id": "run-f", "git_head": "abc1234", "prereg_id": "PRE-0288", "results": [
        {"nodeid": node, "role": "verdict", "outcome": "failed", "measurement": {
            "reason": "1 of 71 GET paths llms.txt documents answer 401: /api/v1/cloned-bots/backtest/quote",
            "left": ["/api/v1/cloned-bots/backtest/quote"], "right": []}},
        {"nodeid": "tests/rest/test_other.py::test_z", "role": "verdict", "outcome": "failed",
         "measurement": {"reason": "another row's failure", "left": 1, "right": 0}}]}
    ledger = {"schema": 2, "findings": {"CYM-a": {
        "id": "CYM-a", "title": "t", "checks": [node],
        "provenance": {"run_id": "run-f", "measured_at": "2026-10-21T09:00:00+00:00"},
        "check": {"state": "REPRODUCING", "pinned_fingerprint": "fp-1",
                  "adjudicated_by": {"run_id": "run-f", "at": "2026-10-21T09:00:00+00:00"}},
        "filing": {"state": "FIX_CLAIMED", "reports": [{"report_id": 93, "status": "paid"}],
                   "refused": [], "verifications": []},
        "obligations": {"correction_owed": [93]}}}}

    class Level:
        level, reasons = "V", []

    monkeypatch.setattr(verify, "load_run", lambda rid: run)
    monkeypatch.setattr(verify, "admissibility", lambda r: Level())
    monkeypatch.setattr(verify, "read_events", lambda: [])
    [item] = verify.owed(ledger, None)
    sent = verify.body(item)["evidence"]
    assert "WHAT FAILED" in sent, sent
    assert node in sent.split("WHAT FAILED")[1], "the failing check is named in what failed"
    assert "/api/v1/cloned-bots/backtest/quote" in sent.split("WHAT FAILED")[1], "what was read"
    assert "expected" in sent.split("WHAT FAILED")[1].lower(), "what was expected"
    assert "another row's failure" not in sent, "only this row's checks are its readings"

    # A fail whose run recorded no reading says so; it does not go out as a bare FAIL.
    bare = verify.body(_item(verdict="fail", identity="ast"))["evidence"]
    assert "WHAT FAILED" in bare and "no reading" in bare, bare
    # A pass has nothing to say here.
    assert "WHAT FAILED" not in verify.body(_item(helpers_same=True))["evidence"]
    # And a long reading still fits their field, naming the check.
    huge = dict(item, failing_readings=[dict(item["failing_readings"][0], reason="x" * 20000)] * 3,
                evidence_ids=[f"{i:064x}" for i in range(250)])
    fits = verify.body(huge)["evidence"]
    assert len(fits) <= 8000 and node in fits, len(fits)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_evidence_does_not_describe_a_syntax_tree_hash_it_did_not_send():
    """The sentence explaining the fingerprint was true of only some of them.

    `body()` printed one fixed line for every verification -- *"a SHA-256 of
    the check function's parsed syntax tree ... it changes when the check's
    logic changes and not when its comments or formatting do"* -- while
    qa/report_plugin.py:311 prefers `measurement.fingerprint` and falls back to
    the AST hash only when a check offers none. The five reconciliation rows
    verified on 2026-09-10 all carry the first kind: a hash of the claim
    declared in claims.yaml -- the two documents, the extractor on each, the
    relation and its direction -- and editing those check functions does not
    move it at all. Both halves of the sentence were therefore false about the
    value in the same payload, in the one paragraph that exists to tell the
    vendor how to read it.

    Same family as the pin sentence above and as the deep pass of 2026-09-09:
    the mechanism works, the prose wrapped around it claims more than it knows.
    Nothing audits outbound prose, which is why the claim lives in a test.
    """
    mod = _verify()

    declared = mod.body(_item(identity="declared"))["evidence"]
    assert "syntax tree" not in declared, (
        "this fingerprint is a hash of the claim's declared definition; "
        "the check's own source is not in it"
    )
    assert "claims.yaml" in declared or "declared definition" in declared
    assert "the relation and its direction" in declared, (
        "direction is what moved these six rows; say what is in the hash"
    )

    ast = mod.body(_item(identity="ast"))["evidence"]
    assert "parsed syntax tree" in ast, (
        "the ordinary case keeps its true sentence"
    )

    # A row whose provenance we could not establish says the honest little.
    unknown = mod.body(_item())["evidence"]
    assert "syntax tree" not in unknown, (
        "an unestablished provenance is not a licence to guess the stronger "
        "of the two sentences"
    )


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_we_never_send_them_to_a_repository_they_cannot_open():
    """Every verification we have sent ended with an instruction they cannot follow.

    `body()` closed with *"REPRODUCE: github.com/zakutana/qa-cymetica at
    <sha>, then pytest ..."*, and submit.py headed its check list *"AUTOMATED
    CHECKS (public repo: ...)"*. `gh repo view` says PRIVATE and the only
    collaborator is the operator's own account. Six verifications went out
    that way this morning and more before.

    Nothing in the verdict was wrong -- the check did pass, under the pinned
    definition -- but the one line telling them how to check us for themselves
    pointed at a door that does not open for them, which is the same class of
    defect as a check claiming more than it measures: the mechanism is right
    and the sentence around it is not.

    What replaces it is what we can actually stand behind: the request and
    response are kept, under an id, and we will send them if asked.
    """
    verify = _verify()
    body = verify.body(_item(evidence_ids=["abc123", "def456"]))["evidence"]

    for banned in ("github.com", "public repo", "REPRODUCE:"):
        assert banned not in body, (
            f"{banned!r} is still in what goes to the vendor, and the "
            f"repository it names is private"
        )
    assert "provided on request" in body
    assert "abc123" in body, "the evidence id they would have to quote is missing"

    # A row whose evidence we did not capture still says the true thing,
    # without inventing an id.
    bare = verify.body(_item())["evidence"]
    assert "provided on request" in bare
    assert "None" not in bare and "[]" not in bare

    # B2 of the review of 2026-09-23 (3/3): a `fail` may go out from an
    # R-level run -- no clean tree, no preregistration -- and the RUN line
    # described every run as the V-level one. The same class: a true verdict
    # inside a sentence about how it was measured that is not true.
    level_r = verify.body(_item(verdict="fail", level="R", prereg_id=None))["evidence"]
    for claim in ("clean working tree", "frozen and git-tagged", "preregistration"):
        assert claim not in level_r, (claim, level_r)
    assert "not preregistered" in level_r, level_r
    level_v = verify.body(_item(level="V"))["evidence"]
    assert "clean working tree" in level_v and "frozen and git-tagged" in level_v

    # RO06 (deep pass of 2026-09-24): R is also a PREREGISTERED run that fell
    # short -- a dirty tree, code that moved during it (PRE-0084, PRE-0092,
    # PRE-0128). "It was not preregistered" is then false; the line says the
    # preregistration and the reason the run is not the verifying kind.
    dirty = verify.body(_item(verdict="fail", level="R", prereg_id="PRE-0092",
                              level_reasons=["git_dirty"]))["evidence"]
    assert "not preregistered" not in dirty, dirty
    assert "PRE-0092" in dirty and "working tree was not clean" in dirty, dirty
    assert "clean working tree" not in dirty.replace("was not clean", ""), dirty


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_paragraph_names_the_kind_of_fingerprint_the_run_produced():
    """`identity_kind` decides which sentence goes to the vendor, and nothing
    tested it.

    Three readers found the same hole from three directions: replace its body
    with a constant `"declared"`, or invert its ternary, and the whole suite
    stays green while every verification sends the claims.yaml sentence beside
    an AST hash -- which is precisely the false paragraph the function was
    written to prevent.

    What it must do: read the MEASUREMENT, and only the results that actually
    adjudicated this row. A check that declared its own fingerprint is
    `declared`; one hashed from its syntax tree is `ast`; a row whose checks
    disagree, or whose checks did not run, is None and the body then says the
    smaller true thing rather than picking one.

    Not asserted here, because it is unreachable: that the `identity` matches
    the fingerprint actually SENT. verify.py sends `pinned_fingerprint` while
    this reads the current run, and one reader worked out that the two cannot
    differ on a row eligible for verification -- PASSING and REPRODUCING both
    force pinned == observed. So the divergence is a latent shape, not a live
    defect, and saying so here is cheaper than a test that cannot fail.
    """
    verify = _verify()
    checks = ["tests/rest/test_a.py::test_one", "tests/rest/test_b.py::test_two"]

    def run(*fingerprints, role="verdict"):
        return {"results": [
            {"nodeid": nodeid, "role": role,
             "measurement": ({"fingerprint": fp} if fp else {})}
            for nodeid, fp in zip(checks, fingerprints)]}

    assert verify.identity_kind(run("sha256:claim-a", "sha256:claim-b"),
                                checks) == "declared"
    assert verify.identity_kind(run(None, None), checks) == "ast"
    assert verify.identity_kind(run("sha256:claim-a", None), checks) is None, \
        "checks that disagree must not have one of the two sentences picked for them"
    assert verify.identity_kind({"results": []}, checks) is None, \
        "no result adjudicated this row, so nothing is known about its fingerprint"

    # A result that is not the verdict is not evidence about the row's
    # identity: the same nodeid can report setup or teardown rows.
    assert verify.identity_kind(run("sha256:claim-a", "sha256:claim-b",
                                    role="setup"), checks) is None

    # And a result for some other row cannot decide this one.
    other = {"results": [{"nodeid": "tests/rest/test_z.py::test_z",
                          "role": "verdict",
                          "measurement": {"fingerprint": "sha256:z"}}]}
    assert verify.identity_kind(other, checks) is None


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_filed_report_says_the_same_thing():
    """submit.py is the other outbound writer and carried the same sentence.

    **Asserted over the composed description, not over the file's text.** Until
    2026-09-10 this exec'd the module, never called it, and grepped the source
    for two literals. Three readers each defeated it the same way: rebuild the
    line as `"(public repo: " + REPO_URL + ")"` and the pinned literal is absent
    from the source while the private link is back in what the vendor receives;
    leave "evidence retained" in a comment and the second assertion passes over
    a payload that no longer says it. Its own sibling four functions up does
    this correctly -- it calls `body()` and greps the result.

    The domain is checked rather than the sentence, because what must never go
    out is a pointer into a repository they cannot open, however it is worded.
    """
    import importlib.util
    from pathlib import Path

    repo = Path(__file__).resolve().parent.parent.parent
    spec = importlib.util.spec_from_file_location(
        "submit_under_test", repo / "scripts" / "submit.py")
    submit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(submit)

    report = {
        "title": "A finding we filed",
        "body": "One paragraph of what we measured.",
        "severity": "medium",
        "category": "api",
        "expected": "The counter covers every position.",
        "actual": "It covers 29 of 39.",
        "steps": ["GET /api/v1/example", "read the count"],
        "findings": ["CYM-example"],
    }
    findings = {"findings": [{
        "id": "CYM-example", "title": "frozen title",
        "detail": {"reason": "what the run measured", "count": 3},
        "checks": ["tests/rest/test_example.py::test_one"],
        "provenance": {"measured_at": "2026-09-10T12:00:00+00:00"},
        # What a finding we file looks like since B5: our check reproduces it.
        "check": {"state": "REPRODUCING"},
    }]}
    composed = submit.compose(report, findings, "Filed by the QA agent.")
    description = composed["description"]

    assert "github.com" not in description and "github" not in description.lower(), (
        f"the filed description points the vendor at a repository. Ours is "
        f"private and they are not on it, so the line offers a door that does "
        f"not open:\n{description}"
    )
    assert "evidence retained" in description, (
        f"the description names the checks and does not say the evidence is "
        f"kept and available, so it asks them to take the result on trust:\n"
        f"{description}"
    )

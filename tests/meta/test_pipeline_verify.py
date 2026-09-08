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
    """The ordinary case must keep its strongest true sentence."""
    evidence = _verify().body(_item())["evidence"]
    assert "under the same definition it failed under" in evidence
    assert "matches the one recorded at the failure" in evidence


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

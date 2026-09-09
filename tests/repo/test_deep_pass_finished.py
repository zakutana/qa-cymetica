"""A pass that stopped in the middle leaves a red test, not a quiet file.

`audits/deep-pass-progress.json` is where the deep pass writes what it claimed,
what survived triage and what it fixed, so that being compacted halfway through
itself cannot erase the list. The operator's question when that file was added,
on 2026-09-08, is the reason this exists:

    "plus na disk jeste neco ukladas, coz se bojim ze treba zapomenes nacist"

They are right, and the evidence is from the same morning: DEEP-PASS.md existed
and was full of work, and a session could not read it because nothing pointed
at it. A file whose only guard is somebody remembering to open it is the
weakest thing in this repository.

So this reads it instead. A gap that three agents called real and nobody fixed
is exactly the state that cannot be allowed to sit quietly: the suite goes
green, the report says the pass finished, and the finding is gone.

Since 2026-09-09 the pass carries three more things in the same file, and they
are read here for the same reason -- each is a promise whose only other witness
is a session that will have been compacted:

  * `retrospective`  the week, and when it last happened. The operator's
                     condition was that it must not depend on them remembering,
                     so the trigger has to live somewhere a machine reads.
  * `rule_changes`   what the night changed about the rules themselves, with
                     its three conditions attached: two of three independent
                     agents, a test naming the incident, a Czech paragraph in
                     the morning.
  * `meta_tests`     how many self-tests there were at the start and at the
                     end. Growth is reported, never forbidden.

**What these can and cannot do**, said plainly rather than discovered later:
they check the FORM of what a pass wrote down, not that it wrote down
everything it did. A pass that changes a rule and records nothing passes them
all. The detector of an unrecorded change is the three agents reading the whole
diff, and the operator's veto after the fact; this file is the check on the
half that is written.

The new checks apply only to a pass that ran on or after 2026-09-09, so the
report already committed -- which predates the keys -- is not retroactively
failed for lacking them. That is the same courtesy the ledger guards extend to
state written before the contract.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

REPO = Path(__file__).resolve().parent.parent.parent
PROGRESS = REPO / "audits" / "deep-pass-progress.json"

# The pass that first writes the new keys. Before it, their absence is history.
KEYS_FROM = "2026-09-09"
WEEK = 7


def _known_nodeids() -> set[str]:
    """Every `path::name` the repository actually has.

    Borrowed from scripts/never_fired.py rather than walked again here: it
    already answers "which test functions exist" for the zeros report, and two
    answers to that question would drift apart exactly when it mattered.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "never_fired_for_progress", REPO / "scripts" / "never_fired.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {f"{rel}::{name}" for rel, name, _ in mod._test_functions()}


def _days(later: str, earlier: str) -> int | None:
    """None when either date cannot be read.

    `date.fromisoformat` raises on anything that is not a date, and a pass
    writing the obvious literal for a week that never happened -- "never"
    rather than null -- would make this guard ERROR instead of report. A file
    whose whole job is to say what a pass left unfinished must not be the thing
    that raises. Found by review, 2026-09-09.
    """
    try:
        return (date.fromisoformat(str(later)[:10])
                - date.fromisoformat(str(earlier)[:10])).days
    except (TypeError, ValueError):
        return None


def problems(progress: dict, nodeids: set[str] | None = None) -> list[str]:
    """Everything this pass promised and did not finish, in English.

    Pure, so the checks below can be shown to fire on a fixture rather than
    only on whatever the last real pass happened to write.
    """
    out: list[str] = []
    gaps = progress.get("gaps") or []

    # `handled` rather than `fixed`: a gap the pass deliberately left for the
    # operator is finished business here, as long as it said so. What is
    # forbidden is confirmed-real, unfixed, and unmentioned.
    owed = [g for g in gaps
            if g.get("verdict") == "real" and not g.get("fixed")
            and not g.get("deferred_to_operator")]
    if owed:
        out.append(
            f"{len(owed)} gap(s) confirmed real, fixed none of them and named "
            f"none for the operator: "
            + ", ".join(str(g.get("id") or g.get("nodeid")) for g in owed[:6]))

    at = str(progress.get("at") or "")
    if at[:10] < KEYS_FROM:
        return out

    retro = progress.get("retrospective")
    if not isinstance(retro, dict):
        out.append("no `retrospective` block: the week has no trigger, so it "
                   "depends on the operator remembering, which is the one "
                   "thing it may not depend on")
    else:
        last, done = retro.get("last"), bool(retro.get("done"))
        elapsed = None if last is None else _days(at, last)
        # An unreadable date is treated as "never", not as "recently": the
        # safe direction for a trigger the operator asked never to depend on
        # somebody remembering.
        due = last is None or elapsed is None or elapsed >= WEEK
        if due and not done:
            out.append(
                f"the week was due (last {last or 'never'}, this pass {at[:10]}) "
                f"and this pass did not do it"
                + ("" if last is None or elapsed is not None else
                   f"; `last` is {last!r}, which is not a date"))

    changes = progress.get("rule_changes")
    if changes is None:
        out.append("no `rule_changes` key: a pass that changed no rule writes "
                   "an empty list, and the difference between 'none' and 'not "
                   "recorded' is the whole point of the key")
    else:
        known = _known_nodeids() if nodeids is None else nodeids
        for change in changes:
            who = change.get("id") or change.get("what") or "?"
            votes = change.get("votes") or {}
            # The vocabulary is exactly "no" and "yes", answering "does this
            # weaken a guard or touch a decision?" -- and the skill says so
            # where the pass writes the file. It accepted four spellings and
            # documented none, so an agent's answer recorded verbatim ("no, it
            # does not weaken any guard") counted as disagreement and turned
            # this red on a compliant pass. Found by review, 2026-09-09.
            spoken = {k: str(v).strip().lower() for k, v in votes.items()}
            odd = sorted(k for k, v in spoken.items() if v not in ("no", "yes"))
            if odd:
                out.append(
                    f"rule change {who}: {odd} answered something other than "
                    f"'no' or 'yes'. The question is whether the change weakens "
                    f"a guard or touches an [operator ...] paragraph, so 'no' "
                    f"is the vote that lets it land")
            agreed = sum(1 for v in spoken.values() if v == "no")
            if agreed < 2:
                out.append(f"rule change {who}: {agreed} of 3 agents said it "
                           f"does not weaken a guard; two is the floor")
            test = change.get("test")
            if not test or test not in known:
                out.append(f"rule change {who}: names no test that exists "
                           f"({test!r}); a rule change without a test naming "
                           f"the incident is the thing the rule prevented")
            if not change.get("handover"):
                out.append(f"rule change {who}: no paragraph in the morning "
                           f"handover, so the operator cannot veto what they "
                           f"have not been shown")

    meta = progress.get("meta_tests")
    if not isinstance(meta, dict):
        out.append("no `meta_tests` block: the self-test count at the start and "
                   "the end is how growth stays visible")
    elif (meta.get("end") or 0) > (meta.get("start") or 0) \
            and not (meta.get("reason") or "").strip():
        out.append(
            f"tests/meta grew {meta.get('start')} -> {meta.get('end')} with no "
            f"reason given. Growth is allowed and unexplained growth is not: "
            f"say which existing test was considered and why it would not hold "
            f"this")
    return out


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_no_confirmed_finding_was_left_unfixed_by_a_deep_pass():
    """Every gap the pass confirmed is fixed or named for the operator, and
    every promise the pass makes about itself is kept."""
    if not PROGRESS.exists():
        conclude(Measurement(
            verdict="inconclusive",
            reason="no deep pass has written a progress file yet, so there is "
                   "nothing to have been left behind",
            sources={"progress": "audits/deep-pass-progress.json"}))
        return

    try:
        progress = json.loads(PROGRESS.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        conclude(Measurement(
            verdict="failed",
            reason=f"the deep pass's progress file cannot be read "
                   f"({type(exc).__name__}), so whether it finished is unknown "
                   f"-- and unknown is the state this file exists to prevent",
            sources={"progress": "audits/deep-pass-progress.json"}))
        return

    gaps = progress.get("gaps") or []
    undecided = [g for g in gaps if g.get("verdict") is None]
    found = problems(progress)

    conclude(Measurement(
        verdict="failed" if found else "passed",
        reason=(f"the last deep pass ({progress.get('run')}) settled all "
                f"{len(gaps)} gap(s) it claimed"
                + (f", {len(undecided)} of them still awaiting a vote"
                   if undecided else "")
                if not found else
                f"the last deep pass ({progress.get('run')}) left "
                f"{len(found)} thing(s) unfinished: " + "; ".join(found[:4])),
        left=found, right=[],
        population={"gaps": len(gaps), "still_unvoted": len(undecided)},
        sources={"progress": "audits/deep-pass-progress.json"}))


# ---------------------------------------------------------------------------
# The three promises, each shown to fire
# ---------------------------------------------------------------------------
NODEIDS = {"tests/meta/test_pipeline_fold.py::test_axes_are_independent"}


def _pass(**over) -> dict:
    base = {"run": "deep pass 2026-09-20", "at": "2026-09-20T02:00:00+00:00",
            "gaps": [], "rule_changes": [],
            "retrospective": {"last": "2026-09-18", "done": False},
            "meta_tests": {"start": 200, "end": 200, "reason": None}}
    base.update(over)
    return base


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_pass_from_before_the_keys_is_not_failed_for_lacking_them():
    """The report already committed predates all three. Failing it would be
    judging state written before the contract it is judged against -- the
    ledger guards refuse to do that and so does this."""
    old = {"run": "deep pass 2026-09-08", "at": "2026-09-08T14:20:48+00:00",
           "gaps": [{"id": "R01", "verdict": "real", "fixed": True}]}
    assert problems(old, NODEIDS) == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize("retro,fires", [
    ({"last": "2026-09-18", "done": False}, False),   # two days ago, not due
    ({"last": "2026-09-18", "done": True}, False),
    ({"last": "2026-09-12", "done": False}, True),    # eight days, and skipped
    ({"last": "2026-09-12", "done": True}, False),    # eight days, and done
    ({"last": None, "done": False}, True),            # never, and skipped
])
def test_the_week_cannot_be_quietly_skipped(retro, fires):
    """The operator's condition: the retrospective must not depend on them
    remembering. A trigger a pass can ignore in silence is the same as no
    trigger, so a due week that did not happen is red the next morning."""
    found = problems(_pass(retrospective=retro), NODEIDS)
    assert bool(found) is fires, found
    if fires:
        assert "week was due" in found[0]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize("change,expect", [
    ({"id": "RC1", "votes": {"t1": "no", "t2": "no", "t3": "yes"},
      "test": "tests/meta/test_pipeline_fold.py::test_axes_are_independent",
      "handover": True}, None),
    ({"id": "RC2", "votes": {"t1": "no", "t2": "yes", "t3": "yes"},
      "test": "tests/meta/test_pipeline_fold.py::test_axes_are_independent",
      "handover": True}, "two is the floor"),
    ({"id": "RC3", "votes": {"t1": "no", "t2": "no", "t3": "no"},
      "test": "tests/meta/test_gone.py::test_nothing", "handover": True},
     "names no test that exists"),
    ({"id": "RC4", "votes": {"t1": "no", "t2": "no", "t3": "no"},
      "test": "tests/meta/test_pipeline_fold.py::test_axes_are_independent",
      "handover": False}, "no paragraph in the morning"),
])
def test_a_rule_change_carries_all_three_of_the_operators_conditions(change, expect):
    """2026-09-08: the night loop may change a rule itself when, at once, two
    of three independent agents say it weakens no guard, a test names the
    incident, and the morning carries a Czech paragraph. Any one missing and
    the change is not one the operator agreed the loop could make alone."""
    found = problems(_pass(rule_changes=[change]), NODEIDS)
    if expect is None:
        assert found == []
    else:
        assert found and expect in found[0], found


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_growth_in_the_self_tests_is_reported_not_forbidden():
    """The ratio this plan started from -- 419 of 473 tests guarding us -- is
    not a number any single test can rule on. What can be ruled on is whether
    a night that added to it said why. Silence is the failure, not growth."""
    assert problems(_pass(meta_tests={"start": 200, "end": 204,
                                      "reason": None}), NODEIDS)
    assert problems(_pass(meta_tests={"start": 200, "end": 204,
                                      "reason": "A3-09 has no existing home"}),
                    NODEIDS) == []
    assert problems(_pass(meta_tests={"start": 204, "end": 200,
                                      "reason": None}), NODEIDS) == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_missing_key_is_not_the_same_as_an_empty_one():
    """A pass that changed no rule writes `rule_changes: []`. One that never
    reached the step writes nothing, and the difference is the whole reason
    the key exists -- the same distinction rule 8 makes between a failed read
    and an empty one."""
    silent = _pass()
    del silent["rule_changes"]
    assert any("not recorded" in p for p in problems(silent, NODEIDS))
    assert problems(_pass(rule_changes=[]), NODEIDS) == []

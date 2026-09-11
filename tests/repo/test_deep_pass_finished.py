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

From 2026-09-10 there is a fourth, and it is the operator's:

  * `next`           the work the pass left for the next morning, written into
                     `NEXT.md` in the same breath. They asked for the deep pass
                     to carry "where we continue tomorrow" itself, because
                     until then the only thing carrying it was them saying it
                     again after a /clear.

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

import datetime as _dt
import importlib.util

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
# `next` arrived a day later and gets its own gate, so the 2026-09-09 report
# is not retroactively failed for a key that did not exist when it was written.
NEXT_FROM = "2026-09-10"
WEEK = 7

# How long a pass may be in flight before an unwritten `finished` stops
# meaning "running" and starts meaning "died". This was a CALENDAR-DAY
# comparison for four hours on 2026-09-09, and the clock rolled to 09-10
# while the pass that wrote it was still running: it declared that pass dead,
# turned this guard red, and step 9 reverts a night on an unresolvable red.
# A day boundary, in the guard over a job named for the night. Found by the
# first reader of the rule change, who noticed it in passing.
MAX_PASS = _dt.timedelta(hours=24)

# And how far AHEAD of the checking clock a stamp may sit and still be a pass
# that is running. The lower bound was zero, so a stamp even seconds in the
# future read as "abandoned" -- the third instance of this class after the
# calendar-day comparison and the week read as skipped, and the first one to
# actually fire: the pass of 2026-09-10 wrote 21:40Z against a 14:42Z clock
# and declared itself dead, mid-run, in the guard that step 9 reverts on.
# Every fixture had put `today` after `at`, and the one future case was
# +11 days, which blessed the bound rather than testing it. Found by a
# check-auditor and reproduced by all three triage readers.
#
# Twelve hours, because the causes are clock skew between a container and a
# host and a hand-written timestamp, and both are hours. Beyond that a stamp
# is not skew, it is wrong, and "abandoned" is the honest reading.
MAX_SKEW = _dt.timedelta(hours=12)


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


def liveness(progress: dict, today: str | None = None) -> str:
    """Is this pass running, finished, or did it die halfway?

    The distinction the guard below did not have and could not make. Step 0
    opens the progress file with `retrospective {last: null, done: false}`
    and step 11 is what sets `done`, so for as long as a pass runs it looks
    exactly like a pass that skipped the week. Step 6 runs `pytest tests/repo`
    in the middle of that, and step 9 reverts the run's commits on a red it
    cannot resolve -- so this guard would have made a pass revert its own
    night, on a test written hours earlier the same day.

    Rule 8's shape: in progress is not skipped. But "unfinished" may not
    become a permanent excuse either, so it is bounded by the date the pass
    itself stamped. Unfinished and stamped today is a pass that is running.
    Unfinished and older is a pass that died without finishing, which is
    worth saying out loud rather than passing over.

    `finished` is the pass's last progress write, after the week and before
    the push.
    """
    if progress.get("finished"):
        return "finished"
    stamped = _when(str(progress.get("at") or ""))
    if stamped is None:
        return "abandoned"
    if today is None:
        now = _dt.datetime.now(_dt.timezone.utc)
    else:
        # A bare date given as "now" means the END of that day, so that
        # liveness(pass stamped 02:00 today, today="today") reads running
        # rather than negative-elapsed.
        now = _when(today if len(today.strip()) > 10
                    else today.strip() + "T23:59:59+00:00")
    if now is None:
        return "abandoned"
    return "running" if -MAX_SKEW <= now - stamped <= MAX_PASS else "abandoned"


def _when(text: str):
    """A timestamp or a bare date, as an aware datetime. None if neither."""
    text = text.strip()
    for form in (text, text[:10]):
        try:
            when = _dt.datetime.fromisoformat(form.replace("Z", "+00:00"))
        except ValueError:
            continue
        return when if when.tzinfo else when.replace(tzinfo=_dt.timezone.utc)
    return None


def problems(progress: dict, nodeids: set[str] | None = None,
             agreed_items: set[str] | None = None) -> list[str]:
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
    # A gap nobody voted on is a finding that silently never gets fixed --
    # CLAUDE.md's own words for what this file guards. A FINISHED pass with
    # one left unvoted and not handed over passed until the deep pass of
    # 2026-09-11, with a message saying "still awaiting a vote" (V14, 2/3).
    unvoted = [g for g in gaps if g.get("verdict") in (None, "")
               and not g.get("deferred_to_operator")]
    if unvoted and progress.get("finished"):
        out.append(
            f"{len(unvoted)} gap(s) claimed and never voted on by a finished "
            f"pass, and not handed to the operator: "
            + ", ".join(str(g.get("id") or g.get("nodeid")) for g in unvoted[:6]))

    at = str(progress.get("at") or "")
    if not at:
        # An ABSENT date used to sort below the gate and excuse the whole
        # file as predating the contract, so a pass with no retrospective,
        # no rule_changes key and no meta_tests returned clean. The gate is
        # read from a field the pass itself writes, and its absence says the
        # pass did not write it, not that the pass is old. Found 2026-09-09,
        # three votes of three; this function had already chosen the safe
        # direction for an unreadable `last`.
        out.append("no `at`: the pass recorded no date, so nothing can say "
                   "which contract it was written under, and every promise "
                   "below would be excused by its absence")
    elif at[:10] < KEYS_FROM:
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
            # Two of THREE independent agents. This counted "no" votes and
            # flagged only `agreed < 2`, never checking how many voted, so
            # two of two -- a third agent never run, or its dissent not
            # written down -- landed green, while the message hardcoded the
            # denominator it had not verified. The guard over the operator's
            # own condition of 2026-09-08 did not enforce it. Found
            # 2026-09-09, three votes of three.
            if len(spoken) != 3:
                out.append(f"rule change {who}: {len(spoken)} vote(s) "
                           f"recorded. The condition is two of THREE "
                           f"independent agents, so three is what a "
                           f"majority is counted out of")
            agreed = sum(1 for v in spoken.values() if v == "no")
            if agreed < 2:
                out.append(f"rule change {who}: {agreed} of {len(spoken)} "
                           f"agents said it does not weaken a guard; two "
                           f"is the floor")
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
    elif meta.get("end") is None:
        # `or 0` coerced a null end to zero, which can never exceed a
        # start, so real unexplained growth read as no growth. Missing is
        # not empty -- the distinction this same function draws for
        # `rule_changes` one block up. Found 2026-09-09, three votes of
        # three, and one reader noted it was permanent rather than
        # occasional: `end` was written only by step 11, which runs only
        # when the week is due.
        out.append(
            f"`meta_tests.end` was never written (start {meta.get('start')}), "
            f"so this pass measured no growth in tests/meta at all. A "
            f"pass writes it whether or not the week was due")
    elif meta["end"] > (meta.get("start") or 0) \
            and not (meta.get("reason") or "").strip():
        out.append(
            f"tests/meta grew {meta.get('start')} -> {meta.get('end')} with no "
            f"reason given. Growth is allowed and unexplained growth is not: "
            f"say which existing test was considered and why it would not hold "
            f"this")

    if at[:10] >= NEXT_FROM:
        out += _next_step_problems(progress, agreed_items)
    return out


def _next_step_problems(progress: dict,
                        agreed_items: set[str] | None = None) -> list[str]:
    """Whether the pass handed the next morning the work it left.

    [operator 2026-09-10] *"zahrn do do deep pass procesu za bude vedet pak kde
    pokracovat dalsi den po clearu"* -- and the turn before it, the reason:
    they do not want to be the one who remembers, before a deep pass, to say
    afterwards where we stopped.

    So step 10 writes the unfinished work into `NEXT.md`, where a SessionStart
    hook reads it, and records the same sentences here. Two failures are
    possible and both are silent, which is why they are checked rather than
    trusted:

      * the key is absent -- the pass never reached the step, and "nothing was
        left over" is indistinguishable from "nobody asked". Same distinction
        `rule_changes` draws one block up, and rule 8's.
      * the sentence is in the notebook and not in `NEXT.md`. The notebook is
        overwritten by the next pass and nothing loads it into a session; a
        next step recorded only there reaches nobody, which is the exact hole
        this was built to close.

    The cross-check accepts an item **open or ticked**. A pass writes "clone
    Hybrid 2", the morning does it and ticks the line, and the item is then
    done -- not missing. Requiring it to be open would turn doing the work into
    a red test.
    """
    out: list[str] = []
    entries = progress.get("next")
    if entries is None:
        return ["no `next` key: a pass that left nothing for the morning "
                "writes an empty list, and the difference between 'nothing "
                "was left' and 'the step did not happen' is what the key is "
                "for -- the morning cannot tell them apart from silence"]
    if not isinstance(entries, list):
        return [f"`next` is {type(entries).__name__}, not a list of the "
                f"sentences written into NEXT.md"]

    known = _next_items() if agreed_items is None else agreed_items
    for entry in entries:
        text = " ".join(str(entry or "").split())
        if not text:
            out.append("`next` carries an empty entry, which reaches the "
                       "morning as a blank line and says nothing")
            continue
        if not any(text[:40].lower() in item for item in known):
            out.append(
                f"`next` names {text[:60]!r} and NEXT.md does not carry it. "
                f"The notebook is overwritten by the following pass and no "
                f"hook loads it, so a next step recorded only here is one "
                f"nobody is handed")
    return out


def _next_items() -> set[str]:
    """Every item in NEXT.md, open or ticked, lowercased for comparison."""
    try:
        spec = importlib.util.spec_from_file_location(
            "next_step_hook", REPO / ".claude" / "hooks" / "next_step.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        text = (REPO / "NEXT.md").read_text(encoding="utf-8")
        return {" ".join(i["what"].split()).lower() for i in module.parse(text)}
    except Exception:
        return set()


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

    state = liveness(progress)
    if state == "running":
        # A pass is writing this file right now, and every promise below
        # is kept at its END. Judging it mid-flight made this red from
        # step 0 to step 11 of every pass, and step 9 reverts a night on
        # an unresolvable red. In progress is not skipped.
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"a deep pass ({progress.get('run')}) is still "
                   f"running: it stamped {str(progress.get('at'))[:10]} "
                   f"and has not written `finished`. Its promises are "
                   f"judged when it says it is done",
            sources={"progress": "audits/deep-pass-progress.json"}))
        return

    gaps = progress.get("gaps") or []
    undecided = [g for g in gaps if g.get("verdict") is None]
    found = problems(progress)
    if state == "abandoned":
        found = [f"the pass stamped {str(progress.get('at'))[:10]} never "
                 f"wrote `finished`, so it died somewhere in its own "
                 f"spine and nothing said so"] + found

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


# --- the four defects the 2026-09-09 deep pass found in this file, each with
# --- the fixture that showed it. Written before the fixes, red against them.

@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_pass_still_running_is_not_a_pass_that_skipped_the_week():
    """S03. The state every pass is in between step 0 and step 11.

    Step 0 opens the file with `retrospective {last: null, done: false}` and
    step 11 is what sets `done`. This guard read that as "the week was due and
    this pass did not do it" -- so it was red for the whole of every pass, step
    6 runs `pytest tests/repo` in the middle of that, and step 9 reverts the
    run's commits on a red it cannot resolve. A pass following its own spine
    would have reverted its night on a test written hours earlier. Rule 8's
    distinction, missed in a file that cites rule 8: in progress is not
    skipped.
    """
    running = _pass(at="2026-09-20T02:00:00+00:00",
                    retrospective={"last": None, "done": False})
    assert liveness(running, today="2026-09-20") == "running"

    # And the hole that would open if "unfinished" simply meant "excused":
    assert liveness(running, today="2026-09-27") == "abandoned"
    assert liveness(_pass(finished=True), today="2026-09-27") == "finished"

    # A pass runs at NIGHT. This compared calendar days for four hours on
    # 2026-09-09, and the clock rolled over while the pass that wrote it was
    # still going: it declared that pass dead and turned this guard red, which
    # is the exact failure the whole function exists to prevent.
    assert liveness(running, today="2026-09-20T06:00:00+00:00") == "running"
    assert liveness(running, today="2026-09-21T03:00:00+00:00") == "abandoned"
    # A stamp the future cannot explain is not a pass in flight either.
    assert liveness(_pass(at="2026-10-01T02:00:00+00:00"),
                    today="2026-09-20T06:00:00+00:00") == "abandoned"
    assert liveness(_pass(at="not a date"), today="2026-09-20") == "abandoned"

    # HOURS ahead, which is the case every fixture above missed: the only
    # future stamp tested was +11 days, and that blesses the bound rather than
    # testing it. The lower bound was zero, so a stamp seconds into the future
    # read as "abandoned" -- and this fired for real. The pass of 2026-09-10
    # wrote 21:40Z against a 14:42Z clock, declared itself dead mid-run, and
    # turned the guard red in the file step 9 reverts a night over. Third
    # instance of this class; found by a check-auditor, 3/3 on triage.
    #
    # Clock skew between a container and a host, and a hand-written timestamp,
    # are both measured in hours. So hours ahead is a pass that is running.
    ahead = _pass(at="2026-09-20T21:40:00+00:00")
    assert liveness(ahead, today="2026-09-20T14:42:00+00:00") == "running", (
        "a stamp seven hours ahead of the clock is skew, not a dead pass")
    assert liveness(ahead, today="2026-09-20T21:39:59+00:00") == "running"
    # Beyond the skew window it is not skew, it is a wrong date, and
    # "abandoned" is then the honest reading rather than a courtesy.
    assert liveness(_pass(at="2026-09-21T12:00:00+00:00"),
                    today="2026-09-20T14:42:00+00:00") == "abandoned"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_pass_that_wrote_no_date_is_not_excused_as_ancient():
    """C01. `at[:10] < KEYS_FROM` scored an ABSENT date as predating the
    contract, so a file with no retrospective, no rule_changes and no
    meta_tests returned clean. The gate is read from a field the pass itself
    writes. The same function already chose the safe direction for an
    unreadable `last`; this is the other one."""
    assert problems({"run": "deep pass 2026-09-20", "gaps": []}, NODEIDS)
    assert problems({"run": "x", "at": "", "gaps": []}, NODEIDS)
    # Still excused when it really does predate the keys.
    assert problems({"run": "old", "at": "2026-09-08T14:20:48+00:00",
                     "gaps": []}, NODEIDS) == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_two_of_two_is_not_two_of_three():
    """C02. The operator's condition of 2026-09-08 is two of THREE independent
    agents. This counted "no" votes and flagged only `agreed < 2`, so two votes
    with the third agent never run -- or its dissent not written down -- landed
    green, while the failure string hardcoded the denominator it never checked.
    The guard over their own condition did not enforce it."""
    def change(votes):
        return _pass(rule_changes=[{"id": "RC1", "what": "x", "votes": votes,
                                    "test": sorted(NODEIDS)[0],
                                    "handover": True}])
    assert problems(change({"t1": "no", "t2": "no"}), NODEIDS)
    assert problems(change({"t1": "no", "t2": "no", "t3": "yes", "t4": "yes"}),
                    NODEIDS)
    assert problems(change({"t1": "no", "t2": "yes", "t3": "yes"}), NODEIDS)
    assert problems(change({"t1": "no", "t2": "no", "t3": "yes"}), NODEIDS) == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_unwritten_growth_count_is_not_a_count_of_zero():
    """C03. `(meta.get("end") or 0) > (meta.get("start") or 0)` coerced a null
    end to zero, which can never exceed a start, so real unexplained growth
    read as no growth. The same function draws the missing-versus-empty
    distinction one block up for `rule_changes` and dropped it here."""
    assert problems(_pass(meta_tests={"start": 200, "end": None,
                                      "reason": None}), NODEIDS)
    assert problems(_pass(meta_tests={"start": 200}), NODEIDS)
    assert problems(_pass(meta_tests={"start": 200, "end": 218,
                                      "reason": None}), NODEIDS)
    assert problems(_pass(meta_tests={"start": 200, "end": 218,
                                      "reason": "the boundary pin"}),
                    NODEIDS) == []


def _pass(**over) -> dict:
    base = {"run": "deep pass 2026-09-20", "at": "2026-09-20T02:00:00+00:00",
            "gaps": [], "rule_changes": [], "next": [],
            "retrospective": {"last": "2026-09-18", "done": False},
            "meta_tests": {"start": 200, "end": 200, "reason": None}}
    base.update(over)
    return base


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_finished_pass_leaves_no_gap_unvoted():
    """V14, deep pass of 2026-09-11, triage 2/3. `owed` counted only gaps
    voted real, so a pass that finished with a claimed gap nobody voted on
    passed -- a lost verdict, "a finding that silently never gets fixed" in
    CLAUDE.md's own words -- while the pass message said "still awaiting a
    vote". A pass still running has not had its vote yet, and a gap handed
    to the operator is handled."""
    gap = {"id": "X1", "nodeid": "tests/meta/test_x.py::test_x",
           "verdict": None, "fixed": False}
    said = problems(_pass(finished=True, gaps=[gap]), NODEIDS)
    assert any("never voted" in line for line in said), said
    assert not any("never voted" in line
                   for line in problems(_pass(finished=False, gaps=[gap]), NODEIDS))
    handed = dict(gap, deferred_to_operator=True)
    assert not any("never voted" in line
                   for line in problems(_pass(finished=True, gaps=[handed]), NODEIDS))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_next_morning_is_handed_the_work_and_not_only_the_notebook():
    """[operator 2026-09-10] the deep pass carries where we continue tomorrow.

    Three things could go wrong and each one is silent. The pass never reaches
    the step, so nothing is handed over and the file cannot say whether that
    means "nothing was left" -- the same distinction `rule_changes` draws. Or
    it writes the sentence into its own notebook, which the next pass
    overwrites and no hook loads, so it reaches nobody. Or the morning does the
    work and ticks the line, which must not turn the guard red.
    """
    items = {"clone hybrid 2 (blue) in paper -- the bot nexus recommended"}

    # Written in both places: nothing owed.
    assert problems(_pass(next=["Clone Hybrid 2 (Blue) in paper -- the bot "
                                "Nexus recommended"]), NODEIDS, items) == []

    # In the notebook only. The morning is handed nothing.
    orphan = problems(_pass(next=["Rewrite the fold's fingerprint pinning"]),
                      NODEIDS, items)
    assert orphan and "NEXT.md does not carry it" in orphan[0]

    # Ticked overnight is done, not missing.
    assert problems(_pass(next=["Clone Hybrid 2 (Blue) in paper -- the bot "
                                "Nexus recommended"]), NODEIDS, items) == []

    # The step never happened.
    silent = _pass()
    del silent["next"]
    found = problems(silent, NODEIDS, items)
    assert found and "no `next` key" in found[0]

    # A pass that left nothing says so.
    assert problems(_pass(next=[]), NODEIDS, items) == []

    # An empty sentence reaches the morning as a blank line.
    blank = problems(_pass(next=["   "]), NODEIDS, items)
    assert blank and "empty entry" in blank[0]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_pass_from_before_next_existed_is_not_failed_for_lacking_it():
    """`next` was built on 2026-09-10. The pass of 2026-09-09 wrote a full
    notebook under the contract of its own day and is not judged against a key
    that did not exist -- the courtesy the whole file already extends once."""
    older = _pass(at="2026-09-09T02:00:00+00:00",
                  retrospective={"last": "2026-09-09", "done": True})
    del older["next"]
    assert problems(older, NODEIDS, set()) == []


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

"""The half of the day that only the transcript remembers.

[operator 2026-09-13] *"a proc si jako cely context neulozis prvne pred deep
apssem na disk a kdyz nahodou se stane compacting tak si ho zas nacte"*

It is already on disk -- the harness writes every row of every session under
`~/.claude/projects/*cymetica*/`, 13 MB for this one, of which 5 MB is the
assistant's own side. Nothing needed saving. What was missing is a READER:
`messages()` keeps `type == "user"` and drops everything else, so the deep
pass's step 1 -- *which inference failed* -- could see the operator's short
Czech corrections and never the reasoning they were correcting.

`trail()` is that reader. Three kinds of row, interleaved in time:

    operator    what they said, the existing filter, unchanged
    correction  a moment the assistant said it had been wrong
    error       a tool result that failed, or a test run that went red

Each is evidence of the same thing from a different side, and the ORDER is
the point: a correction that follows an operator message is a different
animal from one that follows a red test. The first is being caught; the
second is catching yourself.

Bounded on purpose. The source is tens of megabytes and the reader that
replaced `git log` for this job must not itself become something nobody runs.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


def _mod():
    spec = importlib.util.spec_from_file_location(
        "processes_trail", REPO / "scripts" / "processes.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _assistant(stamp: str, text: str) -> dict:
    return {"type": "assistant", "timestamp": stamp,
            "message": {"content": [{"type": "text", "text": text}]}}


def _operator(stamp: str, text: str) -> dict:
    return {"type": "user", "timestamp": stamp, "message": {"content": text}}


def _tool_error(stamp: str, text: str) -> dict:
    return {"type": "user", "timestamp": stamp, "message": {"content": [
        {"type": "tool_result", "is_error": True, "content": text}]}}


def _tool_ok(stamp: str, text: str) -> dict:
    return {"type": "user", "timestamp": stamp, "message": {"content": [
        {"type": "tool_result", "content": text}]}}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_trail_carries_the_assistants_own_corrections():
    """The rows `messages()` throws away, and the whole reason for this."""
    mod = _mod()
    rows = [
        _operator("2026-09-13T10:00:00Z", "a proc to nejde"),
        _assistant("2026-09-13T10:01:00Z",
                   "Mate pravdu, myslel jsem se -- ten cas byl CEST, ne UTC."),
        _assistant("2026-09-13T10:02:00Z",
                   "Hotovo, 44 verified fixed."),          # not a correction
    ]
    trail = mod.trail(rows, since=None)
    kinds = [row["kind"] for row in trail]
    assert kinds == ["operator", "correction"], trail
    assert "CEST" in trail[1]["text"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_green_run_says_nothing_and_real_breakage_does():
    """A passing suite is the normal state of the world. So, it turns out, is
    a red one here -- see the test-first test below -- so what is kept is
    breakage in something that was meant to already work."""
    mod = _mod()
    rows = [
        _tool_ok("2026-09-13T11:00:00Z", "679 passed, 1 skipped in 138.95s"),
        _tool_error("2026-09-13T11:06:00Z", "SyntaxError: unterminated string"),
    ]
    trail = mod.trail(rows, since=None)
    assert [r["kind"] for r in trail] == ["error"], trail
    assert "SyntaxError" in trail[0]["text"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_three_kinds_are_interleaved_in_time_not_grouped():
    """The order IS the finding. A correction after an operator message is
    being caught; one after a red test is catching yourself. Grouped by kind,
    that difference disappears."""
    mod = _mod()
    rows = [
        _assistant("2026-09-13T09:00:00Z", "Opravuji, to bylo spatne."),
        _operator("2026-09-13T09:30:00Z", "zase si to odbyl"),
        # is_error, because that is what a Bash call raising a traceback
        # actually produces -- a successful tool result is not breakage,
        # whatever its text says (A02, deep pass 2026-09-13).
        _tool_error("2026-09-13T09:15:00Z",
                    "Traceback (most recent call last): KeyError: 'legs'"),
    ]
    trail = mod.trail(rows, since=None)
    assert [r["kind"] for r in trail] == ["correction", "error", "operator"]
    assert [r["at"] for r in trail] == sorted(r["at"] for r in trail)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_it_reads_from_a_moment_and_stays_bounded():
    """13 MB in, a few pages out, or it becomes a reader nobody runs."""
    mod = _mod()
    rows = [_operator("2026-09-12T23:00:00Z", "vcerejsi zprava"),
            _operator("2026-09-13T10:00:00Z", "dnesni zprava")]
    trail = mod.trail(rows, since="2026-09-13T00:00:00Z")
    assert [r["text"] for r in trail] == ["dnesni zprava"], trail

    long_one = [_assistant("2026-09-13T10:00:00Z",
                           "Mylil jsem se. " + "x" * 5000)]
    kept = mod.trail(long_one, since=None)[0]["text"]
    assert len(kept) <= mod.TRAIL_CHARS, len(kept)

    many = [_operator(f"2026-09-13T10:{i:02d}:00Z", f"zprava {i}")
            for i in range(59)]
    assert len(mod.trail(many, since=None, limit=20)) == 20


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_test_written_red_on_purpose_is_not_a_failed_inference():
    """The signal this reader nearly drowned in.

    CLAUDE.md requires the test before the implementation, so **every new
    check is red once, deliberately**. Run over three hours of 2026-09-13 the
    first draft returned 8 "errors" and 1 correction, and of the 8 nearly all
    were a test doing exactly what the rule asks. A reader whose loudest
    signal is the workflow working is a reader that buries the one line worth
    reading.

    So a bare pytest failure is dropped: it is in the commit, it was usually
    intended, and the deep pass reads the commits anyway. What is kept is
    breakage in something that was supposed to already work -- a traceback, a
    syntax error, a tool the harness itself flagged.
    """
    mod = _mod()
    rows = [
        _tool_ok("2026-09-13T12:00:00Z",
                 "FAILED tests/meta/test_new_thing.py::test_it "
                 "1 failed, 5 passed"),
        _tool_error("2026-09-13T12:01:00Z",
                    "Traceback (most recent call last): TypeError: "
                    "'module' object is not iterable"),
        _tool_error("2026-09-13T12:02:00Z", "SyntaxError: unterminated string"),
    ]
    trail = mod.trail(rows, since=None)
    assert len(trail) == 2, [r["text"][:60] for r in trail]
    assert "TypeError" in trail[0]["text"]
    assert "SyntaxError" in trail[1]["text"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_environment_being_slow_is_not_something_to_learn_from():
    """A screenshot that timed out because a window was behind another window
    says nothing about an inference. Three of them landed in the first run."""
    mod = _mod()
    rows = [_tool_error("2026-09-13T12:00:00Z",
                        "screenshot failed: Screenshot timed out after 5s: "
                        "the page did not finish rendering in time. Retry")]
    assert mod.trail(rows, since=None) == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_harness_block_is_never_read_as_the_operator():
    """`messages()` learned this once already, on a compaction summary. The
    skill-reinvocation block has the same shape and leaked straight through
    into the first run of the trail."""
    mod = _mod()
    rows = [_operator(
        "2026-09-13T12:00:00Z",
        "Skill /qa-sweep was loaded earlier (see the invoked-skills reminder "
        "above); this is a NEW invocation - follow those instructions now.")]
    assert mod.trail(rows, since=None) == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_read_that_merely_contains_the_word_is_not_breakage():
    """A02, deep pass of 2026-09-13, triage 3/3. Two thirds of the loudest
    signal in this reader was breakage that never happened.

    `_WENT_RED` was matched against the body of ANY tool result, successful or
    not -- so a Read of `qa/lab.py`, a Read of NEXT.md or grep output that
    merely contains the word `TypeError` was filed as an error. Measured over
    the real 2026-09-12 transcripts: 48 error rows of which only 13 were
    `is_error`; the other 35 were reads that worked.

    A tool result that SUCCEEDED is not breakage, whatever its text says. The
    harness flags the ones that failed, and that flag is the signal; the regex
    now only sharpens it.
    """
    mod = _mod()
    a_read = {"type": "user", "timestamp": "2026-09-13T12:00:00Z",
              "message": {"content": [{"type": "tool_result", "content":
                  "def _at(value):\n    except (TypeError, ValueError):\n"
                  "        return None"}]}}
    assert mod.trail([a_read], since=None) == [], (
        "a successful Read of source that mentions TypeError is not an error")

    really_broke = {"type": "user", "timestamp": "2026-09-13T12:01:00Z",
                    "message": {"content": [{"type": "tool_result",
                        "is_error": True, "content":
                        "Traceback (most recent call last): TypeError: x"}]}}
    assert [r["kind"] for r in mod.trail([really_broke], since=None)] == ["error"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_probe_and_a_test_run_in_one_command_keep_the_probes_failure():
    """R04, deep pass of 2026-09-13, triage 3/3.

    `_A_TEST_RUN` dropped a result if a pytest banner appeared anywhere in it,
    and the filter runs per tool RESULT while the shape used all day is one
    Bash call that runs a probe and then pytest. So a real traceback from the
    probe half was swallowed whole by the green half that followed it.

    Told apart by the flag rather than by the banner: the harness marks a
    result that failed, and a test run that merely went red is not a failed
    inference -- the test comes first here, so every new check is red once on
    purpose.
    """
    mod = _mod()
    mixed = {"type": "user", "timestamp": "2026-09-13T12:00:00Z",
             "message": {"content": [{"type": "tool_result", "is_error": True,
                 "content": "Traceback (most recent call last):\n"
                            "KeyError: 'legs'\n"
                            "=== short test summary info ===\n"
                            "683 passed, 1 skipped in 136.38s"}]}}
    kept = mod.trail([mixed], since=None)
    assert [r["kind"] for r in kept] == ["error"], kept
    assert "KeyError" in kept[0]["text"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_exception_inside_a_pytest_run_is_still_the_test_being_written():
    """The second half of the test-first problem.

    Dropping the bare word FAILED was not enough: a new test that names a
    function nobody has written yet fails with `AttributeError: module has no
    attribute`, and that traceback is the rule working, not a mistake. It is
    a test RUN that says so -- pytest prints its own banner -- and the same
    exception from a probe script is a real mistake, so the two are told
    apart by where they happened rather than by what they say.
    """
    mod = _mod()
    # FLAGGED, as a real red pytest run is (it exits non-zero). With the flag
    # unset the row was dropped by the flag gate before the banner rule ever
    # ran, so this passed for the wrong reason while a real test-first run
    # was kept as breakage (C05, deep pass of 2026-09-19, 3/3).
    inside_pytest = _tool_error(
        "2026-09-13T12:00:00Z",
        "FAILURES tests/meta/test_x.py:196: AttributeError: module "
        "'movers_mod' has no attribute 'note_entry' "
        "=========================== short test summary info ===========")
    from_a_probe = _tool_error(
        "2026-09-13T12:01:00Z",
        "Traceback (most recent call last): File \"<string>\", line 10, in "
        "<module> TypeError: 'module' object is not iterable")

    trail = mod.trail([inside_pytest, from_a_probe], since=None)
    assert len(trail) == 1, [r["text"][:70] for r in trail]
    assert "not iterable" in trail[0]["text"]

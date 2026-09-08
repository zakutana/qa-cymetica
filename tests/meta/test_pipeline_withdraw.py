"""WD: withdrawal is an event with a reason and a debt, not a dict in the code.

Four findings were retracted by adding their ids to a literal dict at
scripts/ledger.py:36-55. That dict is the reason a withdrawal could not be
dated, could not name who decided it, and -- because two of the four had
already been filed with the vendor -- left no record that we owed anyone a
correction. `if False and method:` at findings.py:239 is the same defect in the
other direction: a finding switched off by editing the generator.

The rule: a human changes state only by appending an event, and every such
event carries a reason. The literal is gone and cannot come back without
failing this file.

Fails at 11e43ea: there is no scripts/withdraw.py.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


def _module(relpath: str):
    """Import a scripts/ module by path -- scripts/ is not a package."""
    path = REPO / relpath
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_withdrawal_is_an_event_with_obligations(tmp_path, monkeypatch):
    """Withdrawing a filed finding writes one operator event and leaves a debt
    on every report it was filed under, until a retraction is sent."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.fold import fold
    from qa.state import read_events

    withdraw = _module("scripts/withdraw.py")
    journal = tmp_path / "journal" / "events.jsonl"

    withdraw.main(["withdraw", "CYM-mcp_tool_count",
                   "--reason", "Our check asserted the anonymous tool count "
                               "equals the manifest total; that held only while "
                               "tier gating was broken."])

    events = read_events(path=journal)
    assert len(events) == 1
    e = events[0]
    assert e["type"] == "withdraw" and e["by"] == "operator"
    assert e["finding_id"] == "CYM-mcp_tool_count"
    assert "tier gating" in e["reason"]

    from tests.meta.test_pipeline_fold import _filed, ledger, row
    state = ledger(row("CYM-mcp_tool_count", check_state="REPRODUCING", checks=["tests/a.py::t"]))
    after = fold(state, events=_filed("CYM-mcp_tool_count", 46, "pending") + events)

    r = after["findings"]["CYM-mcp_tool_count"]
    assert r["filing"]["state"] == "WITHDRAWN"
    assert r["obligations"]["retractions"] == [46], \
        "withdrawing a filed finding must leave a correction owed on its report"

    sent = events + [{"type": "retraction_sent", "at": "2026-09-05T13:00:00+00:00",
                      "by": "operator", "source": "scripts/withdraw.py",
                      "finding_id": "CYM-mcp_tool_count", "report_id": 46,
                      "reason": "CORRECTIONS paragraph in #54"}]
    cleared = fold(state, events=_filed("CYM-mcp_tool_count", 46, "pending") + sent)
    assert cleared["findings"]["CYM-mcp_tool_count"]["obligations"]["retractions"] == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_withdraw_refuses_an_empty_reason(tmp_path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    withdraw = _module("scripts/withdraw.py")

    with pytest.raises(SystemExit):
        withdraw.main(["withdraw", "CYM-a", "--reason", "   "])
    assert not (tmp_path / "journal" / "events.jsonl").exists()


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_mistyped_finding_id_is_refused_before_it_is_permanent(tmp_path, monkeypatch):
    """A judgement about a finding that is not there must not be recorded.

    Nothing checked the id, so one wrong character appended a permanent event
    to an append-only journal, printed "appended: withdraw CYM-reallll" as
    though it had worked, and left the row it was meant for untouched. Both
    halves hurt: the retraction that was owed never got recorded, and the
    journal keeps a judgement about nothing, which cannot be removed -- only
    annotated.

    An absent ledger still lets the event through. Being unable to check is
    not the same as having checked, and bootstrapping is a real case.
    """
    import json

    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    withdraw = _module("scripts/withdraw.py")
    journal = tmp_path / "journal" / "events.jsonl"

    # No ledger yet: the check cannot run, so it must not block.
    assert withdraw.main(["withdraw", "CYM-anything", "--reason", "bootstrapping"]) == 0
    journal.unlink()

    row = {"id": "CYM-real", "title": "t", "severity": "S3-CONTRACT",
           "checks": ["t::a"],
           "first_seen": {"at": "2026-09-01T00:00:00+00:00",
                          "cause": {"run_id": "r0"}},
           "check": {"state": "REPRODUCING", "adjudicated_by": None,
                     "pinned_fingerprint": None},
           "filing": {"state": "RAISED", "adjudicated_by": None,
                      "reports": [], "refused": []},
           "transitions": [], "regressions": []}
    (tmp_path / "ledger.json").write_text(
        json.dumps({"schema": 2, "findings": {"CYM-real": row}}), encoding="utf-8")

    with pytest.raises(SystemExit) as raised:
        withdraw.main(["withdraw", "CYM-reallll", "--reason", "one character out"])
    assert "CYM-real" in str(raised.value), "the near miss was not offered"
    assert not journal.exists(), "a refused judgement still reached the journal"

    # supersede names two rows, and both have to be real.
    with pytest.raises(SystemExit):
        withdraw.main(["supersede", "CYM-real", "CYM-nope", "--reason", "r"])
    assert not journal.exists()

    assert withdraw.main(["withdraw", "CYM-real", "--reason", "the real one"]) == 0
    assert journal.exists()


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_hardcoded_withdrawal_dict_is_gone():
    """The literal and its two accomplices. Each one is a place where state
    was assigned by editing code rather than by recording an event."""
    ledger_mod = _module("scripts/ledger.py")
    assert not hasattr(ledger_mod, "WITHDRAWN"), \
        "the hardcoded withdrawal dict is back at scripts/ledger.py"
    for gone in ("latest_run_id", "executed_nodeids", "merge"):
        assert not hasattr(ledger_mod, gone), f"scripts/ledger.py still defines {gone}()"

    # Parsed, not grepped: the module's docstring names both defects precisely
    # because it records why they were removed.
    import ast

    tree = ast.parse((REPO / "scripts" / "findings.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test = node.test
            const = test if isinstance(test, ast.Constant) else (
                test.values[0] if isinstance(test, ast.BoolOp) and
                isinstance(test.values[0], ast.Constant) else None)
            assert not (const is not None and not const.value), (
                f"findings.py:{node.lineno} switches a finding off with an "
                f"unreachable branch"
            )
        if isinstance(node, ast.FunctionDef):
            assert node.name != "_parse_failure", \
                "findings still scrape their detail out of a traceback"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_only_state_module_writes_state_files():
    """Critique gap 10. Without this, the whole class returns with the next
    script that finds it convenient to write the ledger itself.

    `.claude/hooks/` is scanned because the message below claims a universal
    and the glob `[qs]*` did not reach it, while real Python runs there on
    every PreToolUse and at every SessionStart. Deep pass 2026-09-08 filed it
    as A3-09 and two of three triage agents objected that no such writer
    exists today -- true, and beside the point: a negative control dropped
    into that directory passed this test untouched. The operator: "ok".
    """
    import ast

    offenders = []
    roots = ("qa/**/*.py", "scripts/**/*.py", ".claude/hooks/**/*.py")
    scanned = sorted({p for root in roots for p in REPO.glob(root)})
    for path in scanned:
        rel = path.relative_to(REPO).as_posix()
        if rel in ("qa/state.py", "scripts/migrate_ledger.py"):
            continue
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        lines = source.splitlines()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            # A bare `open(...)` is an ast.Name, so reading only `.attr`
            # skipped it entirely -- and qa/state.py appends the journal with
            # exactly that idiom. The write names were also short of the ones
            # a person reaches for next.
            name = (getattr(node.func, "attr", None)
                    or getattr(node.func, "id", None))
            if name not in ("write_text", "write_bytes", "open", "replace",
                            "rename", "dump", "copy", "copyfile", "copy2"):
                continue
            # The path is rarely spelled in the same expression as the write:
            # `p = ledger_path()` two lines up, then `tmp.write_text(...)` and
            # `os.replace(tmp, p)`. Neither of those calls contains any of the
            # three words, which is how the sanctioned writer's own idiom
            # passed this guard. Look at the surrounding lines, not just the
            # call. Audit, 2026-09-07.
            src = ast.unparse(node)
            window = "\n".join(
                lines[max(0, node.lineno - 6):node.lineno + 1]).lower()
            # Only the two artefacts the contract names. Widening this to
            # "state" or "state_dir" catches the run-record recorder and the
            # dashboard writer, which are allowed to write what they write --
            # a guard that fires on those would be relaxed within a day.
            if any(word in window for word in ("ledger", "events", "journal")):
                offenders.append(f"{rel}:{node.lineno}: {src[:80]}")
    assert not offenders, (
        "only qa/state.py may write state/ledger.json and the journal:\n  "
        + "\n  ".join(offenders)
    )


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_pinned_fingerprint_can_be_read_from_the_run_that_produced_it(tmp_path):
    """PIN: the value is derived, not retyped, and derived the fold's way.

    Pinning a repaired check needs the fingerprint the run observed. Twice on
    2026-09-07 that was fetched by hand -- a throwaway one-liner over the run
    record, then the hash pasted into `--value`. A hand-copied 64-character
    hash between two commands is a step that exists only because nothing
    offered to do it.

    The danger in automating it is worse than the tedium: a row can declare
    several checks, and the fold combines their fingerprints in a way that is
    not "the first one" (qa/fold.py::_fingerprint_of). A second implementation
    here would pin a value the fold never computes, and the row would read
    CHECK CHANGED forever with a justification attached -- a badge nobody can
    clear, signed. So the CLI imports the fold's function rather than
    reproducing it, and this test holds the two together over the multi-check
    case, which is where they would diverge.
    """
    import json

    from qa.fold import _fingerprint_of

    withdraw = _module("scripts/withdraw.py")

    one = [{"nodeid": "tests/one.py::test_x", "check_fingerprint": "fp-single"}]
    two = [{"nodeid": "tests/b.py::test_y", "check_fingerprint": "fp-b"},
           {"nodeid": "tests/a.py::test_x", "check_fingerprint": "fp-a"}]

    run = {"run_id": "run-20260907T000000Z-abc1234",
           "results": one + two + [{"nodeid": "tests/z.py::test_other",
                                    "check_fingerprint": "fp-unrelated"}]}
    (tmp_path / "run.json").write_text(json.dumps(run), encoding="utf-8")

    # A result carrying no fingerprint is still the fold's chosen result for
    # that nodeid, so it must be this function's too -- and then refused for
    # having no value, not skipped as if the run had never run it.
    blind = {"run_id": "run-blind",
             "results": [{"nodeid": "tests/one.py::test_x", "outcome": "passed"}]}
    with pytest.raises(SystemExit, match="no fingerprint"):
        withdraw.fingerprint_from_run(blind, ["tests/one.py::test_x"])

    assert withdraw.fingerprint_from_run(run, [r["nodeid"] for r in one]) \
        == _fingerprint_of(one) == "fp-single"

    # The case that would diverge if this were reimplemented: the fold sorts by
    # nodeid and hashes the pairs, so it is neither the first nor the newest.
    combined = withdraw.fingerprint_from_run(run, [r["nodeid"] for r in two])
    assert combined == _fingerprint_of(two)
    assert combined not in ("fp-a", "fp-b"), \
        "a multi-check row pinned one member's fingerprint, which the fold never computes"

    # A check the run did not adjudicate cannot be pinned from it: silently
    # pinning a partial row is how a fold verifies something it never ran.
    with pytest.raises(SystemExit, match="did not adjudicate"):
        withdraw.fingerprint_from_run(run, ["tests/a.py::test_x", "tests/never.py::test_q"])

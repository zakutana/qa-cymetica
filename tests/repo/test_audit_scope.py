"""Which checks a contract audit still owes a reading, and the two ways the
deep pass got it wrong while its own spine said otherwise.

In tests/repo and not tests/meta on purpose. A wrong answer here sends
auditors to the wrong files; it does not let a bad state through, so it must
not abort a live session. Same reason tests/repo exists at all.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

REPO = Path(__file__).resolve().parent.parent.parent


def _module():
    spec = importlib.util.spec_from_file_location(
        "nf_mod", REPO / "scripts" / "never_fired.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run(*results):
    return {"results": [{"nodeid": n, "check_fingerprint": f} for n, f in results]}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_partial_run_does_not_shrink_the_audit():
    """The incident, 2026-09-09. The spine said "the newest run record", and
    every pytest invocation writes one -- including the pass's own step-0
    `pytest tests/meta -q`. That night the newest held 398 results, all of them
    tests/meta, so every vendor-facing check was absent from it and would have
    dropped silently out of scope. Rule 1's shape applied to the pass's own
    scoping: a partial run may not stand in for a full one."""
    nf = _module()
    live = {"tests/meta/test_a.py::test_a", "tests/rest/test_b.py::test_b"}
    newest_is_partial = _run(("tests/meta/test_a.py::test_a", "fp-a2"))
    older_full = _run(("tests/meta/test_a.py::test_a", "fp-a1"),
                      ("tests/rest/test_b.py::test_b", "fp-b1"))
    audited = {"tests/meta/test_a.py::test_a": {"fingerprints": ["fp-a1"]},
               "tests/rest/test_b.py::test_b": {"fingerprints": ["fp-b0"]}}

    owed = nf.audit_scope(audited, [newest_is_partial, older_full], live)
    assert "tests/meta/test_a.py::test_a" in owed, "its fingerprint moved"
    assert "tests/rest/test_b.py::test_b" in owed, (
        "the vendor-facing check is absent from the newest record and owes a "
        "reading; scoping to that record alone is what hid it")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_deleted_test_is_not_sent_to_an_auditor():
    """The half the first half created. A union over every run record carries
    the nodeids of tests that no longer exist -- 72 of 587 on 2026-09-09,
    including a file that same day had deleted -- and an auditor asked to read
    a function that is not there can report nothing but confusion."""
    nf = _module()
    live = {"tests/meta/test_a.py::test_a"}
    runs = [_run(("tests/meta/test_a.py::test_a", "fp-a2"),
                 ("tests/meta/test_gone.py::test_gone", "fp-g1"))]
    owed = nf.audit_scope({}, runs, live)
    assert owed == ["tests/meta/test_a.py::test_a"], owed


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_parametrised_ids_collapse_to_the_function_an_auditor_reads():
    """An auditor reads a function, not a case. 273 nodeids were 54 functions
    on the night this was written, and dispatching the ids would have asked
    five readers for the same reading twenty times."""
    nf = _module()
    live = {"tests/meta/test_a.py::test_a"}
    runs = [_run(("tests/meta/test_a.py::test_a[one]", "fp-1"),
                 ("tests/meta/test_a.py::test_a[two]", "fp-2"))]
    assert nf.audit_scope({}, runs, live) == ["tests/meta/test_a.py::test_a"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_scope_over_the_real_repository_names_only_live_functions():
    """Not a fixture: the actual records and the actual tree."""
    import json

    nf = _module()
    audited = json.loads((REPO / "audits" / "checks.json")
                         .read_text(encoding="utf-8")).get("audited", {})
    runs = []
    directory = REPO / "state" / "runs"
    if not directory.is_dir():
        conclude(Measurement(verdict="inconclusive",
                             reason="no run records in this clone"))
        return
    paths = sorted(directory.glob("*.json"), key=lambda p: p.stat().st_mtime,
                   reverse=True)
    for path in paths:
        try:
            runs.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue

    live = {f"{rel}::{name}" for rel, name, _ in nf._test_functions()}
    owed = nf.audit_scope(audited, runs, live)
    # Held against what pytest itself collects, not against `live`:
    # audit_scope already drops anything outside `live`, so comparing with the
    # same set was empty by construction (V16, deep pass of 2026-09-11,
    # triage 3/3).
    import subprocess
    import sys

    listing = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q",
         "-p", "no:cacheprovider", "tests"],
        cwd=REPO, capture_output=True, text=True, timeout=600).stdout
    collected = {line.split("[", 1)[0] for line in listing.splitlines()
                 if "::" in line}
    if not collected:
        conclude(Measurement(verdict="inconclusive",
                             reason="pytest collected nothing, so which tests "
                                    "exist could not be read"))
        return
    stray = [n for n in owed if n not in collected]
    conclude(Measurement(
        verdict="failed" if stray else "passed",
        reason=(f"{len(stray)} nodeid(s) in the audit scope name no test that "
                f"exists: {stray[:5]}" if stray else
                f"{len(owed)} function(s) owe a reading across {len(paths)} "
                f"run record(s), every one of them a test that still collects"),
        left=stray,
        sources={"audited": "audits/checks.json"}))

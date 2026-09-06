"""PIN: the safety guard's enforcement sections are byte-identical to ca0bc45,
and a failing meta test really does abort the session before anything else.

This is phase 0 of the hardening plan and it must stay green through every
later phase. It exists because the guard is the only part of this repo that
worked as designed, and the plan touches files next to it (conftest.py loses
its Inconclusive wrapper in phase 1). If any later edit drifts into the guard
sections, this test turns red and -- via the very mechanism it pins -- stops
the session.

The hashes below were computed at commit ca0bc45 over:
  tests/conftest.py            lines 42-117  (markers, options, collection-time
                                              enforcement, meta-first ordering,
                                              the abort hook, sessionstart)
  tests/conftest.py            lines 123-212 (session resources and fixtures)
  tests/meta/test_guard_is_real.py  whole file
Lines 215-228 of conftest.py (the Inconclusive hookwrapper) and line 30 (its
import) are deliberately outside the pinned ranges: phase 1 removes them.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parents[2]
CONFTEST = REPO / "tests" / "conftest.py"
GUARD_TESTS = REPO / "tests" / "meta" / "test_guard_is_real.py"

PINNED = {
    "conftest.py:42-117": "0aeb83fba58d3846b25311fa7e4e5e9fb3232adcddf8c62b75c4a53c8158cd3c",
    "conftest.py:123-212": "d81006935096100794735750341c49d76393dd82d2f224dd55a9a0ce874e7454",
    # Re-derived 2026-09-06, deliberately, for two edits that go the way this
    # pin exists to protect:
    #
    #   * the money-loop endpoints gained `probe_only: true` in
    #     components.yaml, which made test_mutate_against_unlisted_host_is_
    #     blocked raise on the floor instead of the host allowlist -- so it
    #     was moved onto the bounty filing channel, which is deliberately not
    #     probe_only and therefore actually reaches the allowlist. The old
    #     subject tested the floor twice and the allowlist never.
    #   * test_the_money_loop_is_behind_the_probe_only_floor was added, so
    #     the floor cannot quietly come off again.
    #
    # Both add enforcement. A future re-derivation that removes any is the
    # thing this pin is for: check what changed before recomputing.
    #
    # Re-derived again the same day, for the reason this pin would most want
    # to hear about. Every negative control in that file asked the guard to
    # refuse something, and its only protection against actually doing it was
    # the code under test. Mutating the probe_only floor off -- to check this
    # suite could feel it -- sent a real POST to /api/v1/funding/withdraw with
    # {"amount": "1"}; anonymous, refused 401, nothing moved, and it left the
    # machine. The clients there now carry a transport that cannot send. The
    # mutation is still caught, the message now reads THE GUARD LET IT
    # THROUGH, and no evidence file is written because nothing is sent.
    "test_guard_is_real.py": "1399c75aed23f65f66b4e427a4fb37ea1984233de6cf1bd4f08f55f44780879b",
}


def _sha_lines(path: Path, first: int, last: int) -> str:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    return hashlib.sha256("".join(lines[first - 1:last]).encode("utf-8")).hexdigest()


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_guard_sections_are_byte_identical_to_ca0bc45():
    actual = {
        "conftest.py:42-117": _sha_lines(CONFTEST, 42, 117),
        "conftest.py:123-212": _sha_lines(CONFTEST, 123, 212),
        "test_guard_is_real.py": hashlib.sha256(GUARD_TESTS.read_bytes()).hexdigest(),
    }
    drifted = {k: (PINNED[k][:12], v[:12]) for k, v in actual.items() if v != PINNED[k]}
    assert not drifted, (
        "\nThe safety guard's pinned sections changed. If that was intended, "
        "re-derive the hashes deliberately and say why in the commit; if not, "
        "revert.\n" + "\n".join(f"  {k}: pinned {a}… now {b}…" for k, (a, b) in drifted.items())
    )


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_meta_tests_are_ordered_guard_first():
    """Within the meta block, the guard's own tests must precede the pipeline's.

    Alphabetical collection gives test_guard_is_real < test_pipeline_*, and the
    conftest sorts every /meta/ item ahead of everything else. Assert both so a
    rename cannot silently move the pipeline tests ahead of the guard.
    """
    names = sorted(p.name for p in (REPO / "tests" / "meta").glob("test_*.py"))
    assert names[0] == "test_guard_is_real.py", names
    assert all(n.startswith("test_pipeline_") for n in names[1:]), names


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_failing_meta_test_aborts_session_before_later_tests(pytester, tmp_path):
    """The abort is real: a red meta test stops the run; nothing after it runs.

    A subprocess pytest with the REAL conftest, a deliberately failing canary
    in tests/meta/, and a passing test in tests/x/. Offline and redirected so
    the inner session touches neither the network nor the committed state/.
    """
    pytester.makefile(".toml", pyproject=(REPO / "pyproject.toml").read_text(encoding="utf-8"))
    pytester.mkpydir("tests")
    (pytester.path / "tests" / "conftest.py").write_text(
        CONFTEST.read_text(encoding="utf-8"), encoding="utf-8")
    meta = pytester.path / "tests" / "meta"
    meta.mkdir()
    (meta / "test_zz_canary.py").write_text(textwrap.dedent("""
        from qa.marks import SafetyTier, qa

        @qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
        def test_canary_fails_on_purpose():
            assert False, "canary"
    """), encoding="utf-8")
    later = pytester.path / "tests" / "x"
    later.mkdir()
    (later / "test_later.py").write_text(textwrap.dedent("""
        from qa.marks import SafetyTier, qa

        @qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
        def test_must_never_run():
            assert True
    """), encoding="utf-8")

    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO)
    env["QA_OFFLINE"] = "1"
    env["QA_STATE_DIR"] = str(tmp_path / "state")
    env["PYTHONIOENCODING"] = "utf-8"

    real_runs_before = sorted(p.name for p in (REPO / "state" / "runs").glob("run-*.json"))

    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider"],
        cwd=pytester.path, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
    )
    out = proc.stdout + proc.stderr
    # With -q the final line is the bare summary, e.g. "1 failed in 0.19s".
    summary = [line for line in out.splitlines() if line.strip()][-1]

    assert "SAFETY GUARD SELF-TEST FAILED" in out, out
    assert "test_canary_fails_on_purpose" in out, out
    assert summary.startswith("1 failed"), f"expected exactly the canary to fail:\n{out}"
    assert "passed" not in summary, f"the later test ran despite the abort:\n{out}"

    # The inner session's run record went to the temp dir, never to the repo.
    inner_runs = list((tmp_path / "state" / "runs").glob("run-*.json"))
    assert len(inner_runs) == 1, inner_runs
    real_runs_after = sorted(p.name for p in (REPO / "state" / "runs").glob("run-*.json"))
    assert real_runs_after == real_runs_before, \
        "the inner session wrote into the committed state/runs/"

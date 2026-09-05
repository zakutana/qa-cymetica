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
    "test_guard_is_real.py": "7e5861339ca30b73150fd59b0666b57ea056d6bfe060b40cf6c13ef06ed3b444",
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
        cwd=pytester.path, env=env, capture_output=True, text=True, timeout=180,
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

"""A FAIL from a run that was not preregistered says why it is level R.

Deep pass 2026-10-25, O02 (2 of 3). verify.py's `_run_line` named a level-R
run with a preregistration by its reasons (RO06), and one without by "RUN: X at
commit Y" alone, dropping `level_reasons`. Every level-R run that adjudicates a
row today is a dirty tree without a preregistration -- #217's 8a403f54 among
them -- so the vendor read a run on uncommitted code as "at commit 8a403f54".
The reasons are said in words, never as our keys.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
KEYS = ("git_dirty", "no_prereg", "budget_truncated", "code_moved_during_run",
        "prereg_commit_mismatch")


def _verify():
    spec = importlib.util.spec_from_file_location("verify_run_line", REPO / "scripts" / "verify.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _item(**over):
    base = {"finding_id": "CYM-a", "report_id": 217, "verdict": "fail", "fingerprint": "fp",
            "run_id": "run-x", "checked_at": "2026-10-23T17:14:36+00:00",
            "tree_sha": "8a403f54", "prereg_id": None, "level": "R",
            "level_reasons": ["git_dirty", "no_prereg"], "checks": ["t.py::test_c"],
            "title": "t", "correction_reason": "accepted"}
    base.update(over)
    return base


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_dirty_run_without_a_preregistration_is_not_called_that_commit():
    verify = _verify()
    line = verify._run_line(_item())
    assert "not clean" in line, line
    assert "not preregistered" in line, line
    assert not any(key in line for key in KEYS), line

    truncated = verify._run_line(_item(level_reasons=["budget_truncated", "no_prereg"]))
    assert "rate-limit" in truncated and not any(key in truncated for key in KEYS), truncated

    # Only the missing preregistration: the commit is the code, and that is said.
    plain = verify._run_line(_item(level_reasons=["no_prereg"]))
    assert "8a403f54" in plain and "not preregistered" in plain, plain
    assert not any(key in plain for key in KEYS), plain

    # The preregistered branch (RO06) says its reasons in words too.
    prereg = verify._run_line(_item(prereg_id="PRE-0300", level_reasons=["budget_truncated"]))
    assert "PRE-0300" in prereg and not any(key in prereg for key in KEYS), prereg

    evidence = verify.body(_item())["evidence"]
    assert "not clean" in evidence and not any(key in evidence for key in KEYS), evidence

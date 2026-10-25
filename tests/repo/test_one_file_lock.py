"""One lock implementation, with a polled wait for the writers that need one.

Deep pass 2026-10-25, R06 (cleanup, 3/3). qa/manifest.py carried its own lock
beside `qa.state.file_lock`: the same `<file>.lock`, the same byte, locked its
own way, because file_lock's wait on Windows is LK_LOCK -- a retry once a
second, about ten, then a raise -- and two contending manifest writers queued
in whole seconds (80 refreshes took 92 s, tests/repo/test_manifest_lock.py).
Two implementations of one lock drift apart; the next fix to one misses the
other. `file_lock` takes the poll now (its default wait is unchanged) and the
manifest asks for it.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_polled_lock_waits_its_own_time_and_then_takes_it(tmp_path):
    from qa.state import file_lock

    target = tmp_path / "x.jsonl"
    with file_lock(target):
        began = time.monotonic()
        with pytest.raises(OSError):
            with file_lock(target, poll=0.01, timeout=0.3):
                pass
        waited = time.monotonic() - began
        assert 0.25 <= waited < 3, f"the polled wait took {waited:.2f}s, not its own 0.3 s"
    with file_lock(target, poll=0.01, timeout=0.3):
        pass  # free again: taken at once


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_manifest_takes_the_one_lock():
    source = (REPO / "qa" / "manifest.py").read_text(encoding="utf-8")
    assert "msvcrt" not in source and "fcntl" not in source, \
        "qa/manifest.py locks the file its own way beside qa.state.file_lock"
    assert "file_lock" in source

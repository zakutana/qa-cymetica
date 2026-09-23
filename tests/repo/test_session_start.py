"""One SessionStart hook: at most eight lines, in at most three seconds.

Plan v2, V7 (E1). Six hooks each printed their own block: 4 of 24 runs of the
reminders hook timed out and printed nothing, because it computed the surface
drift over a growing evidence store (3.4 s of its 4.3); surface drift then
filled the four lines the reminders had and crowded out what was due; and
sessions repeated the reminder in two or three of nine starts. One hook now
gives every source a fixed slot, reads the drift from a cache the patrol and
the laboratory tick write, and prints one block.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
HOOK = REPO / ".claude" / "hooks" / "session_start.py"


def _module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_one_hook_is_wired_at_session_start():
    settings = json.loads((REPO / ".claude" / "settings.json")
                          .read_text(encoding="utf-8"))
    wired = [" ".join([h.get("command", "")] + list(h.get("args") or []))
             for block in settings["hooks"]["SessionStart"]
             for h in block.get("hooks") or []]
    assert len(wired) == 1 and "session_start.py" in wired[0], wired


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_source_keeps_its_slot_however_much_another_says():
    """E1's crowding: twelve lines of drift took all four of the reminders'
    lines. A slot is per source, so what is due, the threads and the next
    step are printed whatever the drift says."""
    mod = _module(HOOK, "session_start_compose")
    drift = [f"surface line {n}" for n in range(12)]
    said = mod.compose({"due": drift, "handover": ["pass left: x"],
                        "threads": ["waiting: MSG-1"], "notes": [],
                        "next": ["next: one"], "memory": ["memory: 3"]})
    assert len(said) <= mod.MAX_LINES == 8, said
    for line in ("pass left: x", "waiting: MSG-1", "next: one", "memory: 3"):
        assert line in said, (line, said)
    due = [line for line in said if line.startswith("surface line")]
    assert len(due) < mod.SLOTS["due"], "the last due line says what was cut"
    assert any("+" in line and "processes.py reminders" in line for line in said)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_source_that_fails_costs_its_own_slot_only():
    mod = _module(HOOK, "session_start_fail")

    def broken():
        raise RuntimeError("a part that breaks")
    said = mod.gather({"due": broken, "next": lambda: ["next: one"]})
    assert said == {"due": [], "next": ["next: one"]}, said


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_hook_says_eight_lines_at_most_in_three_seconds():
    """On this repository, as a session start runs it."""
    started = time.monotonic()
    result = subprocess.run([sys.executable, str(HOOK)], cwd=REPO,
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=30)
    took = time.monotonic() - started
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert result.returncode == 0, result.stderr
    assert len(lines) <= 8, lines
    assert took <= 3.0, f"{took:.2f} s"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_surface_drift_is_read_from_its_cache_not_computed(tmp_path,
                                                               monkeypatch):
    """The scan is the patrol's and the tick's; the session start only reads
    what they found."""
    procs = _module(REPO / "scripts" / "processes.py", "processes_cache")

    def never(*a, **k):
        raise AssertionError("the session start computed the drift")
    monkeypatch.setattr(procs, "surface_drift", never)
    monkeypatch.setattr(procs, "drift_cache_path",
                        lambda: tmp_path / "surface_drift.json")
    assert procs._surface_facts() == {}
    (tmp_path / "surface_drift.json").write_text(json.dumps(
        {"at": "2026-09-23T20:00:00+00:00", "drift": ["nový nástroj x"]}),
        encoding="utf-8")
    assert procs._surface_facts() == {"surface_drift": ["nový nástroj x"]}

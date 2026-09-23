"""What the patrol and the deep pass's step-1 readers can actually see.

Plan v2, V7 -- E4, E6 and E8 of the review of 2026-09-23. The patrol reported
"nothing idle" as health while it could not see a part run at all: a slash
command reaches the transcript as `<command-name>/x</command-name>`, which
the reader skipped as a harness block, and the 155 preregistrations are
`.md` files while it globbed `*.json`. A part it never saw had no age, so its
idle flag could not fire. Step 1's readers were mostly the /loop's own
prompts, and the trail cut itself to 120 entries without a word. The daily
rows of audits/processes.jsonl were seven-day totals.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


def _module():
    spec = importlib.util.spec_from_file_location(
        "processes_sees", REPO / "scripts" / "processes.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_slash_command_is_counted_as_its_part():
    procs = _module()
    typed = {"type": "user", "timestamp": "2026-09-23T20:00:00Z",
             "message": {"content": "<command-message>deep-pass</command-message>\n"
                                    "<command-name>/deep-pass</command-name>\n"
                                    "<command-args></command-args>"}}
    seen = procs.runs_from_transcripts([typed], known={"deep-pass"})
    assert seen.get("deep-pass", {}).get("runs") == 1, seen
    other = {**typed, "message": {"content": "<command-name>/btw</command-name>"}}
    assert procs.runs_from_transcripts([other], known={"deep-pass"}) == {}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_markdown_preregistration_is_a_run_of_prereg(tmp_path):
    procs = _module()
    folder = tmp_path / "state" / "preregistrations"
    folder.mkdir(parents=True)
    (folder / "PRE-0155.md").write_text(
        "# PRE-0155\n\n    Registered  2026-09-23T06:10:35+00:00\n", encoding="utf-8")
    seen = procs.records_by_part(tmp_path)
    assert seen.get("prereg.py") == ["2026-09-23T06:10:35+00:00"], seen


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_part_never_seen_is_flagged_once_it_is_old_enough_to_have_run():
    """An idle flag only where a part can leave a record: a hook cannot, and
    `unwired` covers it; a skill, agent or script can, and one that never has
    in all its life is the question the flag exists to ask."""
    procs = _module()
    state = {"parts": {
        "ghost.py": {"runs": 0, "last": None, "idle_days": None,
                     "kind": "script", "age_days": procs.IDLE_DAYS + 1},
        "young.py": {"runs": 0, "last": None, "idle_days": None,
                     "kind": "script", "age_days": 2},
        "hook.py": {"runs": 0, "last": None, "idle_days": None,
                    "kind": "hook", "age_days": 40}}}
    said = procs.flags(state)
    assert any(line.startswith("ghost.py") for line in said), said
    assert not any(line.startswith(("young.py", "hook.py")) for line in said), said


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_loops_own_prompts_are_not_the_operator_speaking():
    procs = _module()
    rows = [{"type": "user", "isMeta": True, "timestamp": "2026-09-23T20:00:00Z",
             "message": {"content": "jdi do laborky"}},
            {"type": "user", "timestamp": "2026-09-23T20:01:00Z",
             "message": {"content": "a jak to jde?"}}]
    assert [t for _, t in procs.messages(rows, None)] == ["a jak to jde?"]
    assert [r["text"] for r in procs.trail(rows, None)] == ["a jak to jde?"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_trail_says_what_it_cut():
    procs = _module()
    rows = [{"type": "user", "timestamp": f"2026-09-23T20:{m:02d}:00Z",
             "message": {"content": f"zprava {m}"}} for m in range(10)]
    kept = procs.trail(rows, None, limit=4)
    assert len(kept) == 4 and kept[-1]["text"] == "zprava 9"
    assert procs.trail_cut(rows, None, limit=4) == 6


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_daily_series_says_its_counts_are_a_week(tmp_path):
    procs = _module()
    procs.extract(tmp_path, procs.day_row({
        "at": "2026-09-23T20:00:00+00:00", "day": "2026-09-23",
        "parts": {"lab.py": {"runs": 40, "errors": 1, "last": "x"}},
        "sizes": {}}))
    row = json.loads((tmp_path / "audits" / "processes.jsonl")
                     .read_text(encoding="utf-8").splitlines()[-1])
    assert row["parts"]["lab.py"] == {"runs_7d": 40, "errors_7d": 1}, row

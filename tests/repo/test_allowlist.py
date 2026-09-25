"""A script our own instructions tell a session to run is allowed to run.

`.claude/settings.json`'s `permissions.allow` is what lets a session invoke a
script without stopping to ask. A script named in CLAUDE.md or in a skill and
missing from that list costs a permission prompt every single time -- and a
mechanism with friction in front of it is a mechanism that quietly stops being
used. `scripts/a2a.py` is the worked example: never allowlisted, and it has
sent two questions in ten days while eleven a2a threads exist, which the
architecture reading of 2026-09-08 already guessed at ("a plausible reason a
session reaches for something else").

Four were missing when this was written -- `channels.py`, `fomo_watch.py`,
`nexus.py`, `review.py` -- all of them scripts a session runs routinely, all
of them named in a skill that says to run them.

This asks one narrow thing: every `python scripts/X.py` that our own written
instructions name has a `Bash(python scripts/X.py:*)` entry. It does not ask
the converse -- an allowlisted script nobody documents is dead weight, not a
defect, and `scripts/processes.py patrol` already reports what goes unused.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

REPO = Path(__file__).resolve().parent.parent.parent
SETTINGS = REPO / ".claude" / "settings.json"
INSTRUCTIONS = [REPO / "CLAUDE.md"] + sorted(
    (REPO / ".claude" / "skills").glob("*/SKILL.md"))
NAMED = re.compile(r"python scripts/([a-z_]+)\.py")


def _named_scripts() -> dict[str, list[str]]:
    """Script -> the instruction files that tell a session to run it."""
    out: dict[str, list[str]] = {}
    for path in INSTRUCTIONS:
        text = path.read_text(encoding="utf-8")
        for name in sorted(set(NAMED.findall(text))):
            out.setdefault(name, []).append(path.relative_to(REPO).as_posix())
    return out


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_script_our_instructions_name_is_allowlisted():
    """Otherwise the instruction costs a prompt, and the mechanism decays."""
    allowed = json.loads(SETTINGS.read_text(encoding="utf-8"))
    entries = (allowed.get("permissions") or {}).get("allow") or []
    named = _named_scripts()
    missing = sorted(
        f"{name} ({', '.join(where)})" for name, where in named.items()
        if f"Bash(python scripts/{name}.py:*)" not in entries)

    conclude(Measurement(
        verdict="failed" if missing else "passed",
        reason=("our own instructions name scripts a session may not run "
                "without asking: " + "; ".join(missing) if missing else
                f"all {len(named)} scripts named in CLAUDE.md and the skills "
                f"are allowlisted"),
        left=missing, right=[],
        population={"named": sorted(named), "allow_entries": len(entries)},
        sources={"allowlist": SETTINGS.relative_to(REPO).as_posix(),
                 "instructions": [p.relative_to(REPO).as_posix()
                                  for p in INSTRUCTIONS]},
    ))


# The tests that make an allowlisted spending script safe to run unasked. The
# prompt was never the brake: these are, and they have to stay where they are.
PAPER_GUARDS = {
    "tests/meta/test_guard_is_real.py": [
        "test_an_order_without_its_paper_flag_never_leaves_this_machine",
        "test_cloning_a_bot_needs_its_paper_flag_too",
    ],
    "tests/meta/test_pipeline_clone.py": [
        "test_starting_a_bot_needs_both_of_their_paper_statements",
        "test_a_settings_patch_needs_our_paper_record_theirs_and_no_running_room",
    ],
}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_laboratorys_own_doors_run_unasked_because_the_code_holds_paper():
    """Plan v2, V6: the laboratory's manager runs clone.py, paper.py and
    hot_watch.py, and a prompt on each is a turn of the loop spent waiting
    for someone asleep. Allowlisting them is safe only because paper-only is
    enforced in code, by the tests named above -- so the allowlist entry and
    the guard that justifies it are held together."""
    allowed = json.loads(SETTINGS.read_text(encoding="utf-8"))
    entries = (allowed.get("permissions") or {}).get("allow") or []
    missing = [name for name in ("clone", "paper", "hot_watch")
               if f"Bash(python scripts/{name}.py:*)" not in entries]
    # In place AND in force: a guard skipped, or with its body emptied, still
    # had its `def` line and passed (deep pass 2026-09-24, A09). So each one
    # is read as code: present, not skipped or xfailed, and asserting.
    import ast

    def in_force(rel: str, name: str) -> bool:
        tree = ast.parse((REPO / rel).read_text(encoding="utf-8"))
        fn = next((n for n in tree.body if isinstance(n, ast.FunctionDef)
                   and n.name == name), None)
        if fn is None:
            return False
        marks = ast.dump(ast.Module(body=[], type_ignores=[])) + "".join(
            ast.dump(d) for d in fn.decorator_list)
        if "skip" in marks or "xfail" in marks:
            return False
        # Skipped from inside too: a `pytest.skip()` in the body, or the
        # module's own `pytestmark` (deep pass 2026-09-25, A09 -- decorators
        # alone were read).
        if any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
               and n.func.attr in ("skip", "xfail", "importorskip")
               for n in ast.walk(fn)):
            return False
        if any(isinstance(n, ast.Assign)
               and any(getattr(t, "id", None) == "pytestmark" for t in n.targets)
               and ("skip" in ast.dump(n.value) or "xfail" in ast.dump(n.value))
               for n in tree.body):
            return False
        return any(isinstance(n, ast.Assert)
                   or (isinstance(n, ast.Attribute) and n.attr == "raises")
                   for n in ast.walk(fn))
    gone = [f"{rel}::{name}" for rel, names in PAPER_GUARDS.items()
            for name in names if not in_force(rel, name)]
    conclude(Measurement(
        verdict="failed" if missing or gone else "passed",
        reason=(f"not allowlisted: {missing}; paper guards gone: {gone}"
                if missing or gone else
                "clone.py, paper.py and hot_watch.py are allowlisted, and the "
                "four tests that hold them to paper are in place"),
        left=missing, right=gone,
        sources={"allowlist": SETTINGS.relative_to(REPO).as_posix(),
                 "guards": sorted(PAPER_GUARDS)},
    ))

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

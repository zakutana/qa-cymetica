"""The departments, found rather than registered (plan v2, V9).

A department is one shape: a skill, `scripts/<d>.py` (tick · brief · report),
its diaries `state/<d>*.jsonl` and its report `state/<d>/report.json`. The
laboratory is the first (`lab`). Everything that has to know the departments
-- the patrol, the snapshot into audits/, the /lab page -- asks here, so a
department added next month needs nobody to wire it in; the architect's review
of 2026-09-23 counted 8-10 touchpoints before this.
"""

from __future__ import annotations

import json
from pathlib import Path

from qa.state import state_dir

REPORT = "report.json"


def names(state: Path | None = None) -> list[str]:
    """Every department that has written a report."""
    base = Path(state or state_dir())
    return sorted(p.parent.name for p in base.glob(f"*/{REPORT}"))


def diaries(state: Path | None = None) -> dict[str, list[Path]]:
    """Per department, its diaries: `state/<d>.jsonl` and `state/<d>_*.jsonl`."""
    base = Path(state or state_dir())
    return {d: sorted([*base.glob(f"{d}.jsonl"), *base.glob(f"{d}_*.jsonl")])
            for d in names(base)}


def departments(state: Path | None = None, skip: tuple[str, ...] = ("lab",)) -> list[dict]:
    """What the /lab page lists beside the laboratory: each department's
    title and its report's lines. The laboratory is the page itself, so it is
    skipped. A report that cannot be read is listed as unreadable, not dropped
    -- a department that went quiet is news (rule 8)."""
    base = Path(state or state_dir())
    out = []
    for name in names(base):
        if name in skip:
            continue
        try:
            report = json.loads((base / name / REPORT).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            report = {"title": name, "lines": ["report unreadable"]}
        out.append({"id": name, "title": str(report.get("title") or name),
                    "lines": [str(line) for line in report.get("lines") or []]})
    return out

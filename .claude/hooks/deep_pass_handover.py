"""SessionStart: what the last deep pass left open, in the session's own context.

DEEP-PASS.md holds the only thing that survives a /clear, and nothing loads it.
CLAUDE.md answered that with an instruction -- "Read it at the start of any
session that follows one" -- and on 2026-09-08 that instruction failed twice in
one day. The first session had nothing in context naming the file. The second
had the line, read it, named the file out loud to the operator, and then asked
permission to open it rather than opening it. The operator: *"takze se sama
nenacetla? takze to nefunguje?"*

A pointer has therefore been tried twice. This prints the handover instead, so
there is no read left to skip: the pass date, and the bold lead of each item it
left open.

That is the deliberate difference from `open_threads.py`, whose shape this
otherwise copies line for line. That hook prints ids and keeps the text on disk,
on the operator's objection to context being filled with messages nobody asked
for -- and it is right, because a Telegram archive grows without bound and every
message in it is still fetchable. A handover is six lines and the next pass
overwrites all of them.

Both headings are read. On the run that prompted this, every numbered item under
"Ceka na tebe" turned out to be informational -- a finding they already know
about, context for a possible reply, a count with a guard behind it -- and both
things actually wanting the operator's judgement were under "Minority report".
Reading only the handover heading would have reported a quiet morning.

It never fails a session. No report, a heading that moved, a file caught
half-written: exit 0 with nothing printed. A note about the last pass must not
be able to stop the next one.
"""

from __future__ import annotations

import os
import re
import sys
import unicodedata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PER_SECTION = 5
LEAD_CHARS = 140

# Both are matched after diacritics are stripped, so the skill may write the
# heading with or without them.
SECTIONS = (("ceka na tebe", "open"), ("minority report", "decide"))


def _plain(text: str) -> str:
    """Lowercased and stripped of diacritics, for matching a Czech heading."""
    decomposed = unicodedata.normalize("NFKD", text.strip().lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _blocks(body: str) -> list[str]:
    """One string per list item, continuation lines folded in.

    The bold lead wraps across lines in the real report -- A3-09's runs to a
    second line before it closes -- so an item is only whole once its indented
    continuations are joined to it.
    """
    items: list[str] = []
    for line in body.splitlines():
        if re.match(r"\s*(?:[-*]|\d+\.)\s+\S", line):
            items.append(line.strip())
        elif items and line.strip():
            items[-1] += " " + line.strip()
        elif not line.strip():
            continue
    return items


def handover(report: str) -> list[str]:
    """The lines to print, or [] when the report says nothing open.

    Pure, so the parse is testable without a subprocess and without a report on
    disk in the right place.
    """
    lines: list[str] = []

    title = next((ln.strip() for ln in report.splitlines()
                  if ln.startswith("# ")), "")

    bodies: dict[str, str] = {}
    current: str | None = None
    for line in report.splitlines():
        if line.startswith("## "):
            current = _plain(line[3:])
            bodies[current] = ""
        elif current is not None:
            bodies[current] += line + "\n"

    for wanted, label in SECTIONS:
        body = next((text for head, text in bodies.items() if wanted in head), None)
        if body is None:
            continue
        for block in _blocks(body)[:PER_SECTION]:
            bold = re.search(r"\*\*(.+?)\*\*", block)
            if not bold:
                continue
            lead = " ".join(bold.group(1).split())
            if len(lead) > LEAD_CHARS:
                lead = lead[:LEAD_CHARS - 1].rstrip() + "…"
            lines.append(f"  {label}: {lead}")

    if not lines:
        return []
    return [f"{title.lstrip('# ').strip()} -- left open:"] + lines + [
        "  the rest is in DEEP-PASS.md; nothing else loads it."]


def main() -> int:
    try:
        path = Path(os.environ.get("QA_DEEP_PASS") or REPO_ROOT / "DEEP-PASS.md")
        if not path.is_file():
            return 0

        lines = handover(path.read_text(encoding="utf-8", errors="replace"))
        if not lines:
            return 0

        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
        print("\n".join(lines))
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

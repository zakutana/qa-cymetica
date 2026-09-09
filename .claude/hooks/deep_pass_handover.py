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
LEAD_CHARS = 140

# All four are matched after diacritics are stripped, so the skill may write
# the heading with or without them.
#
# The first two are about the findings; the last two are about the pass
# itself, and they are here for the reason the whole hook is. A night that may
# change a rule on its own owes the morning a Czech paragraph saying what and
# why -- the operator's third condition, 2026-09-08 -- and a paragraph in a
# file nobody opens is not owed, it is filed. Same for the week: a
# retrospective that depends on somebody remembering to read it is the
# mechanism this repository keeps discovering it does not have.
#
# Capped tighter than the findings. A pass that changed six rules in one night
# has a worse problem than a long handover, and the week's answer is meant to
# be one paragraph -- often "nic nemenit", which is the answer that most needs
# to arrive, because a retrospective that speaks only when it proposes
# something turns into a proposal mill.
SECTIONS = (("ceka na tebe", "open", 5), ("minority report", "decide", 5),
            ("zmenena pravidla", "rule", 3), ("tyden", "week", 2))


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

    for wanted, label, cap in SECTIONS:
        body = next((text for head, text in bodies.items() if wanted in head), None)
        if body is None:
            continue
        # Cap the LEADS, not the raw items. Slicing before the filter let an
        # item written without a bold lead consume a slot and print nothing:
        # five unbolded items under "Ceka na tebe" and the bolded sixth was
        # never reached, so the hook printed nothing at all and the morning
        # read as quiet. Found 2026-09-09, three votes of three.
        leads = (m.group(1) for m in
                 (re.search(r"\*\*(.+?)\*\*", block) for block in _blocks(body))
                 if m)
        for raw in list(leads)[:cap]:
            lead = " ".join(raw.split())
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

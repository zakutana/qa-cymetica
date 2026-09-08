"""Read an archived message file: its frontmatter, and its body as blocks.

A library, not a command. `scripts/render.py` imports it so the Correspondence
panel can quote what was actually written instead of a summary of it, and the
only files it is pointed at now live under `archive/`.

It used to be `scripts/thread.py`, which also carried an `ingest()` that turned
each message into a journal event and a `build()` that wrote
`state/thread.json`. Both were dead by 2026-09-06: nothing called `ingest`, not
even the module's own `__main__`, and `render.py` says in as many words that
message counts come from the journal rather than from `thread.json`. They
described a workflow -- correspondence pasted into `inbox/` by hand -- that was
tried once in round one and never again.

Leaving them there was not free. A session read that docstring, believed the
workflow was live, and built a console marker for it before the operator said
plainly that nothing is ever pasted anywhere. So what remains is the part that
runs: a parser.

Correspondence reaches us through the bounty API -- see `scripts/bounty.py` --
and, since 2026-09-08, through the operator's Telegram thread, which
`scripts/correspond.py` records as journal events when they confirm they sent
something. That is not a reversal of the paragraph above: nothing is pasted
into a directory for a scanner to find, and no file here is a source of state.
This module still parses only the four round-one files under `archive/`.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

RULE = re.compile(r"^[═─]{10,}$", re.M)

TOP_HEADING = re.compile(r"^\d+\.\s+[A-Z]")
# Only TOP-LEVEL headings start a new block. Sub-headings inside a section --
# OBSERVED, CHECK, SCOPE, WHY THIS IS NOT COSMETIC -- are part of the finding's
# argument and must travel with it, or the excerpt attached to a finding is a
# title with nothing under it.
STANDALONE = (
    "ASKS",
    "WHAT I WILL DO WITH YOUR ANSWERS",
    "SCOPE OF THIS REQUEST",
)


def parse(path: Path) -> dict | None:
    """Frontmatter plus body, or None if the file carries no frontmatter."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    _, front, body = text.split("---", 2)
    try:
        meta = yaml.safe_load(front) or {}
    except yaml.YAMLError:
        return None
    # PyYAML turns bare ISO timestamps into datetime objects, which do not
    # survive json.dumps. Normalise every scalar back to a string here so the
    # rest of the pipeline only ever sees text.
    for key, value in list(meta.items()):
        if isinstance(value, (datetime, date)):
            meta[key] = value.isoformat()

    meta["body"] = body.strip()
    try:
        meta["file"] = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        meta["file"] = str(path).replace("\\", "/")
    return meta


def is_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > 200 or RULE.match(stripped):
        return False
    if TOP_HEADING.match(stripped):
        return True
    return any(stripped.upper().startswith(s) for s in STANDALONE)


def blocks(body: str) -> list[tuple[str, str]]:
    """Split a message into (heading, text) blocks."""
    out: list[tuple[str, str]] = []
    heading = ""
    buffer: list[str] = []

    for line in body.splitlines():
        if RULE.match(line.strip()):
            continue
        if is_heading(line):
            if heading or buffer:
                out.append((heading, "\n".join(buffer).strip()))
            heading = line.strip()
            buffer = []
        else:
            buffer.append(line)

    if heading or buffer:
        out.append((heading, "\n".join(buffer).strip()))
    return [(h, t) for h, t in out if h or t]

"""SessionStart: the work we agreed on, in one line, so nobody has to say it twice.

[operator 2026-09-10] *"hele snad si zapamatujes co pises az se te pak zeptam
po deep passu a po clearu... Nechci se starat o to ze pred deep passem ti mam
pak po clearu rikat kde jsme skoncili a cim pokracovat."*

Nothing carried that. Three things reach a fresh session -- the memory index,
the last deep pass's handover, the unanswered Telegram threads -- and none of
them is "the piece of work we said we would do next". DEEP-PASS.md's *Čeká na
tebe* is deliberately the opposite of it: things that need the operator's
judgement, not things we already decided. So a next step agreed at 23:00 and a
`/clear` at 23:05 left the operator to remember it, which is precisely the job
they said was not theirs.

Same shape as open_threads.py, for the same reason: an index, never the
content. One line per open item, none at all when nothing is open, and never a
failure -- a note about what to do next must not be able to stop the work.

The file it reads is `NEXT.md` at the repository root, plain markdown, edited
by hand. Deliberately not a CLI: a mechanism nobody can read with `cat` is one
more thing to trust, and the format is three fields on a line.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LIMIT = 5
WIDTH = 150

ITEM = re.compile(r"^- \[( |x)\] (\d{4}-\d{2}-\d{2}) +(\S.*)$")

# Anything a reader would call an item. Wider than ITEM on purpose: the guard
# over malformed lines only held lines beginning exactly `- [` against ITEM, so
# `* [ ] 2026-09-10 ...` or `-[ ] 2026-09-10 ...` -- both of which any reader
# would take for an agreed next step -- were never printed by this hook and
# never flagged. Precisely the state the guard's own docstring names. Found by
# a check-auditor on the day this file was written, 3/3 on triage.
LOOKS_LIKE_ITEM = re.compile(r"^\s*[-*+]\s?\[")


def body(text: str) -> list[str]:
    """Every line that is not inside a fenced block.

    The file documents its own format in a ``` block, and that example is not
    an item -- it carries YYYY-MM-DD where a date goes. The guard that catches
    a genuinely malformed item would otherwise fire on the documentation of
    what a well-formed one looks like, which is how a format ends up
    undocumented.
    """
    out, fenced = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            out.append(line)
    return out


def parse(text: str) -> list[dict]:
    """The one reader. The hook prints from it and the test asserts on it."""
    out = []
    for line in body(text):
        found = ITEM.match(line.rstrip())
        if found:
            out.append({"done": found.group(1) == "x",
                        "at": found.group(2), "what": found.group(3)})
    return out


def main() -> int:
    try:
        path = Path(os.environ.get("QA_NEXT_FILE") or (REPO_ROOT / "NEXT.md"))
        if not path.is_file():
            return 0
        items = [i for i in parse(path.read_text(encoding="utf-8"))
                 if not i["done"]]
        if not items:
            return 0

        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

        shown = items[:LIMIT]
        rest = len(items) - len(shown)
        print("Agreed and not yet done -- pick up here"
              + (f" (+{rest} more in NEXT.md)" if rest else "") + ":")
        for item in shown:
            # Never the argument, only the sentence. The whole of an item's
            # reasoning lives in NEXT.md and is read when somebody asks.
            print(f"  {item['at']}  {item['what'][:WIDTH]}")
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

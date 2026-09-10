"""Make a stream able to hold what we are about to print at it.

This machine's console is cp1250. A memory body carrying `→`, a Telegram reply
carrying an emoji, a vendor answer carrying a curly quote -- each raises
`UnicodeEncodeError` at the `print`, which is **after** the work is done and
written to disk. The command succeeded and the screen says it crashed, which is
the worst of the two possible lies.

Four scripts each learned this separately and each pasted the same three lines
into its own `main()`. A fifth then crashed during the deep pass of 2026-09-10,
in `scripts/memories.py`, at step 0 -- on the command the pass's own spine runs
to read what earlier passes learned. Four copies of a fix is not a fix; it is a
defect nobody can finish, because the sixth script has no way to know.

`tests/meta/test_pipeline_console.py` names the class and fails when a member
of it does not call this.

Replacing is deliberate. The alternative -- dropping the character, or refusing
to print -- hides that the terminal cannot show it. `errors="replace"` puts a
visible `?` where the arrow was, so a reader sees a mangled character rather
than an absent line.
"""

from __future__ import annotations

import sys


def printable(*streams) -> None:
    """Reconfigure each stream to UTF-8, replacing what it cannot encode.

    Defaults to stdout and stderr. Never raises: a stream that has already been
    written to, or one that is not a `TextIOWrapper` at all, is left as it is.
    A helper whose whole job is to stop a crash on the way out must not be able
    to cause one.
    """
    for stream in (streams or (sys.stdout, sys.stderr)):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass

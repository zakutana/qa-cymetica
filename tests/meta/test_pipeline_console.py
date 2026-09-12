"""A script that prints stored prose must survive the operator's console.

This machine's console is cp1250. Anything we print that is not in that
codepage raises `UnicodeEncodeError` **after** the work is done and written to
disk, so the screen says the command crashed when it succeeded. It has happened
four times, in four different scripts, and each was fixed by pasting the same
three lines into that script's `main()`:

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

Four copies is not four fixes, it is a defect nobody can finish. It happened a
fifth time during the deep pass of 2026-09-10, in `scripts/memories.py`, on the
character `→` in a memory body -- and it happened at step 0, on the command
the pass's own spine tells it to run to read what past passes learned.

So the block lives in `qa/console.py` and this names the scripts that need it.
`GUARDED` is the class: every CLI that prints prose it did not compose itself
in ASCII -- a memory body, a vendor message, an operator's Telegram text, a
finding's reason. Adding a sixth is then a red test, not a sixth crash.

What this does NOT claim: that every script is safe. `render.py` writes a file
and prints a path; `prereg.py` prints ids. Those are ASCII by construction and
listing them would make the class meaningless. If one of them starts printing a
title, it belongs here, and nothing but a reader will notice -- which is the
honest limit of a list.
"""

from __future__ import annotations

import io
import re
import subprocess
import sys
from pathlib import Path

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent

# Every CLI that prints prose it did not author in ASCII.
GUARDED = ("a2a.py", "channels.py", "correspond.py", "memories.py", "nexus.py",
           "review.py", "rooms.py")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_script_that_prints_stored_prose_reconfigures_its_output():
    """Named, so the sixth is caught by a test rather than by a traceback."""
    import ast

    missing = []
    for name in GUARDED:
        path = REPO / "scripts" / name
        tree = ast.parse(path.read_text(encoding="utf-8"))
        main = next((n for n in ast.walk(tree)
                     if isinstance(n, ast.FunctionDef) and n.name == "main"), None)
        if main is None:
            missing.append(f"{name} (no main())")
            continue
        # A STATEMENT of main()'s own body, before anything else can print.
        # `\bprintable\(` over the file's text was the first draft, and an
        # auditor defeated it three ways: the token in a comment, the call
        # moved into an `if args.list:` arm, the call wrapped in `if False:`.
        # Each left the guard green while `--for` still died on a cp1250
        # console. Presence of a token in text against a contract about what
        # runs before the first print.
        early = [s for s in main.body[:4]
                 if isinstance(s, ast.Expr) and isinstance(s.value, ast.Call)
                 and getattr(s.value.func, "id", None) == "printable"]
        if not early:
            missing.append(name)
    assert not missing, (
        f"{missing} print stored prose and do not call qa.console.printable() "
        f"as one of the first statements of main(). On a cp1250 console that "
        f"is a UnicodeEncodeError after the work has already been written to "
        f"disk: the command succeeded and the screen says it crashed"
    )


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_helper_survives_a_stream_that_cannot_hold_the_character():
    """The negative control: prove the crash, then prove the helper stops it.

    A guard asserted against a stream that was never going to raise proves
    nothing, and this repository has written one of those before.
    """
    from qa.console import printable

    arrow = "a memory body with an arrow → in it"

    # The crash, reproduced. If this stops raising, the environment changed and
    # the assertion below has quietly stopped meaning anything.
    raw = io.TextIOWrapper(io.BytesIO(), encoding="cp1250", errors="strict")
    try:
        raw.write(arrow)
        raw.flush()
        raised = False
    except UnicodeEncodeError:
        raised = True
    assert raised, (
        "a cp1250 stream accepted U+2192, so this test no longer reproduces "
        "the failure it was written for"
    )

    # And with the helper applied to the same kind of stream, it does not.
    fixed = io.TextIOWrapper(io.BytesIO(), encoding="cp1250", errors="strict")
    printable(fixed)
    fixed.write(arrow)
    fixed.flush()


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_memories_prints_a_body_carrying_a_character_cp1250_cannot_hold():
    """End to end, through the command the deep pass's own step 0 runs.

    Forced to cp1250 through PYTHONIOENCODING rather than trusting that the
    test runner's console happens to be one -- on a UTF-8 terminal this test
    would pass without exercising anything at all.
    """
    import os
    import tempfile

    # A directory we CONTROL, carrying a body with the character. Pointing at
    # the real memory directory made this pass on any machine that has none:
    # `--for deep-pass` printed "no memories at ..." and exited 0, having
    # printed no body and no character cp1250 cannot hold. An auditor
    # reproduced that by running it from a copy at a different path, and all
    # three readers confirmed. A test whose subject may be absent is a test
    # that reports on its own absence.
    arrow = "the fix goes upstream → of the guard, not into it"
    with tempfile.TemporaryDirectory() as scratch:
        home = Path(scratch)
        (home / "arrowed.md").write_text(
            '---\nname: arrowed\ndescription: "d"\napplies: "deep-pass"\n---\n\n'
            f"{arrow}\n", encoding="utf-8")
        (home / "MEMORY.md").write_text(
            "- [Arrowed](arrowed.md) — a body cp1250 cannot hold\n",
            encoding="utf-8")

        result = subprocess.run(
            [sys.executable, "scripts/memories.py", "--for", "deep-pass"],
            cwd=REPO, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=120,
            env={**os.environ, "PYTHONIOENCODING": "cp1250",
                 "QA_MEMORY_DIR": str(home)})

    assert "UnicodeEncodeError" not in (result.stderr or ""), (
        f"memories.py crashed printing its own stored text: "
        f"{(result.stderr or '')[-300:]}"
    )
    assert result.returncode == 0, (
        f"exit {result.returncode}: {(result.stderr or '')[-300:]}")
    # It PRINTED the body, so the run exercised the thing it is named for.
    # The arrow itself is replaced on the way out -- that is the fix working --
    # so the assertion is on the text around it.
    assert "the fix goes upstream" in result.stdout, (
        f"the command exited 0 without printing the body, so nothing was "
        f"exercised: {result.stdout[:200]!r}")

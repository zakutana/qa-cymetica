"""A message we draft for them to paste opens with our handle.

[operator 2026-09-13] *"vzdy jak generujes zpravu na telegram tak na zacatek
dej @EventTraderQABot"*

The operator pastes what we write into Cymetica's thread verbatim, so a
handle we leave off is one they have to type. Ours had been inconsistent --
MSG-0009 opens `@cymetica`, MSG-0010 and MSG-0011 open with neither -- which
is exactly the shape of a rule that lives only in a session's head.

**The notice does not refuse.** `correspond.py sent` records what the operator
has ALREADY sent; a recorder that rejects a real message would make the
journal disagree with the thread, and CLAUDE.md's rule 4 exists because a
record that has been tidied is worth less than an awkward one. So the message
is recorded either way and the notice is printed beside it. Both halves are
asserted here, because the tempting "fix" is to prepend the handle silently,
and that would put words in the journal that were never sent.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
HANDLE = "@EventTraderQABot"


def _module():
    spec = importlib.util.spec_from_file_location(
        "correspond_under_test", REPO / "scripts" / "correspond.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_handle_check_reads_the_opening_not_a_mention_anywhere():
    """Their handle quoted mid-sentence is not the message being addressed to
    us -- `opens_with_handle` is about the FIRST thing in the message, so a
    report that happens to name the bot three paragraphs down still gets the
    notice."""
    mod = _module()
    assert mod.opens_with_handle(f"{HANDLE} -- three things, and two are ours")
    assert mod.opens_with_handle(f"  {HANDLE}\n\nFirst:")
    assert mod.opens_with_handle(f"{HANDLE.lower()} hello")
    assert not mod.opens_with_handle(
        "@cymetica -- four things. Reply to @EventTraderQABot when you can.")
    assert not mod.opens_with_handle("Hi team -- while exploring your surface")
    assert not mod.opens_with_handle("")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_message_without_the_handle_is_recorded_and_said_out_loud(tmp_path):
    """The whole point: it goes in, and the operator hears about it."""
    env = {"QA_STATE_DIR": str(tmp_path)}
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "correspond.py"), "sent",
         "--text", "Hi team -- one more gap in the docs."],
        capture_output=True, text=True, cwd=str(REPO),
        env={**__import__("os").environ, **env})

    assert result.returncode == 0, (
        f"recording must not fail on a missing handle -- the message was "
        f"already sent:\n{result.stderr}")
    assert "MSG-" in result.stdout, "it has to actually be recorded"
    assert HANDLE in result.stdout, (
        "the operator has to be told the handle was missing, by name")

    # And the journal holds what was really sent, not a tidied version.
    events = (tmp_path / "journal" / "events.jsonl").read_text(encoding="utf-8")
    assert "Hi team -- one more gap in the docs." in events
    assert f"\\\"text\\\": \\\"{HANDLE}" not in events, (
        "the handle must never be prepended into the record -- the journal is "
        "what went out, not what should have")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_message_with_the_handle_says_nothing_extra(tmp_path):
    env = {"QA_STATE_DIR": str(tmp_path)}
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "correspond.py"), "sent",
         "--text", f"{HANDLE} -- one more gap in the docs."],
        capture_output=True, text=True, cwd=str(REPO),
        env={**__import__("os").environ, **env})

    assert result.returncode == 0, result.stderr
    assert "MSG-" in result.stdout
    # Anchored on the notice's own marker, not on a word that happens to be
    # near it: the first draft of this assertion looked for "missing", which
    # the notice never says, so it would have passed with no notice code at
    # all AND with a notice that fired on every message.
    assert "NOTE:" not in result.stdout, (
        "a correct message must not be nagged at -- a notice that prints "
        f"every time is one nobody reads:\n{result.stdout}")

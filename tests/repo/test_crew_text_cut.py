"""The company's own commands never cut a sender's text without saying so (T-0061).

`qa/crew.py` slices what it is given: a ticket's text at 2,000 characters (add_ticket), a note to
the operator at 2,000 (tell), a done note at 600 (close). `scripts/crew.py` then prints only the
id, so the sender never learns. Twice on 2026-10-12 a Bugs decision ticket carrying a Telegram
draft arrived cut mid-sentence: T-0027 lost its third question, T-0060 ends at "...a supported
rou" (the manager recovered the tail from the run's transcript).

The fix is in `scripts/crew.py::main` (the command line), not in `qa/crew.py`: the clock and the
watchdog call `add_ticket` and `tell` with text they generate, and a refusal raised there would
stop them. So over the limit `ticket` and `tell` print the length and the limit, exit 2 and write
nothing, and the sender shortens in the same run; `done` and `fail` keep their cut (a close that
is refused costs the ticket an attempt) but print that the note was cut and at how many
characters. The limits are `qa.crew`'s own numbers; the fix may name them (TICKET_TEXT_MAX,
TELL_TEXT_MAX, CLOSE_NOTE_MAX) but this test reads only what the command prints.

The controls pass today and must keep passing: text at exactly the limit is kept whole and says
nothing, and the library call still cuts for its internal callers.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

from qa import crew
from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent

TICKET_LIMIT = 2000
TELL_LIMIT = 2000
CLOSE_LIMIT = 600


def _sup():
    spec = importlib.util.spec_from_file_location("crew_text_cut_script",
                                                  REPO / "scripts" / "crew.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def company(tmp_path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("QA_REPO_ROOT", str(tmp_path / "no-repo"))
    monkeypatch.delenv("QA_CREW_TICKET", raising=False)
    monkeypatch.setenv("QA_CREW_DEPT", "bugs")
    return tmp_path


def _says_length_and_limit(out: str, length: int, limit: int) -> bool:
    numbers = {int(n) for n in re.findall(r"\d[\d,]*", out.replace(",", ""))}
    return length in numbers and limit in numbers


def _claimed_bugs_ticket() -> str:
    ticket, _ = crew.add_ticket("bugs", "bug", "a bug to close", by="session")
    claimed = crew.claim("bugs")
    assert claimed and claimed["id"] == ticket["id"]
    return ticket["id"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.xfail(strict=True, reason="T-0061: crew.py ticket cuts the text at 2,000 characters "
                   "and prints only the id; a Telegram draft arrived without its last question")
def test_a_ticket_over_the_limit_is_refused_with_its_length_and_the_limit(company, capsys):
    sup = _sup()
    text = "x" * (TICKET_LIMIT + 137)
    code = sup.main(["ticket", "--to", "manager", "--kind", "decision", "--text", text])
    out = capsys.readouterr().out
    assert code == 2, "the sender must be told, in the same run, to shorten"
    assert _says_length_and_limit(out, len(text), TICKET_LIMIT), out
    assert crew.tickets() == {}, "a refused ticket writes nothing, not even a cut one"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.xfail(strict=True, reason="T-0061: crew.py tell cuts the note at 2,000 characters "
                   "and prints only the id")
def test_a_note_to_the_operator_over_the_limit_is_refused(company, capsys, monkeypatch):
    sup = _sup()
    monkeypatch.setenv("QA_CREW_DEPT", "manager")
    text = "y" * (TELL_LIMIT + 1)
    code = sup.main(["tell", "--text", text])
    out = capsys.readouterr().out
    assert code == 2
    assert _says_length_and_limit(out, len(text), TELL_LIMIT), out
    assert crew.unread_notes() == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.xfail(strict=True, reason="T-0061: a done note is cut at 600 characters and the "
                   "close prints only 'done (attempts 0)'")
def test_a_done_note_over_the_limit_keeps_its_cut_and_says_so(company, capsys):
    sup = _sup()
    tid = _claimed_bugs_ticket()
    note = "n" * (CLOSE_LIMIT + 50)
    code = sup.main(["done", tid, "--note", note])
    out = capsys.readouterr().out
    assert code == 0, "a refused close costs the ticket an attempt; it closes, cut"
    assert crew.tickets()[tid]["status"] == "done"
    assert crew.tickets()[tid]["note"] == note[:CLOSE_LIMIT]
    assert "cut" in out.lower(), out
    assert _says_length_and_limit(out, len(note), CLOSE_LIMIT), out


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_text_at_exactly_the_limit_is_kept_whole_and_nothing_is_said(company, capsys):
    sup = _sup()
    text = "z" * TICKET_LIMIT
    assert sup.main(["ticket", "--to", "manager", "--kind", "decision", "--text", text]) == 0
    assert list(crew.tickets().values())[0]["text"] == text
    tid = _claimed_bugs_ticket()
    capsys.readouterr()
    note = "n" * CLOSE_LIMIT
    assert sup.main(["done", tid, "--note", note]) == 0
    assert crew.tickets()[tid]["note"] == note
    assert "cut" not in capsys.readouterr().out.lower()


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_library_still_cuts_for_the_clock_and_the_watchdog(company):
    """The refusal belongs to the command line: add_ticket and tell are called with generated
    text by the clock and the watchdog, which must never raise on a long line."""
    ticket, _ = crew.add_ticket("manager", "decision", "w" * (TICKET_LIMIT + 500), by="clock")
    assert len(ticket["text"]) == TICKET_LIMIT
    note, _ = crew.tell("v" * (TELL_LIMIT + 500), by="watchdog")
    assert len(note["text"]) == TELL_LIMIT

"""CORRESPOND: the Telegram channel becomes a record with ids.

Ticket ET-22498 triggered the whole 2026-09-07 walk of /build -- three reports
came out of it. The repository cannot say what we asked in it. `git log -S` finds
the string in exactly two places, both prose: a comment in outbox/reports.yaml
and a line in DEEP-PASS.md. The text died with the session that wrote it, because
the only inbound channel we record is the bounty API and Telegram is not it.

So: the operator confirms they sent something, it becomes an event with an id,
their answer links back to that id, and a session that has never seen any of it
can read the thread off disk.

The three things these tests hold, none of which is obvious:

  * A Telegram message moves NEITHER axis. It is not a filing on a report, and
    `reply` -- the type it superficially resembles -- moves FILING to REPLIED.
    Reusing that type would let a pasted chat rewrite finding states.
  * An id is never reissued. MSG-0000..0002 and REPLY-0001 already exist in the
    journal from the round-1 migration, so an allocator that reads only the new
    types hands out MSG-0001 a second time, and `show MSG-0001` is ambiguous for
    ever in a journal that cannot be rewritten.
  * A message never disappears into idempotence. `append_event` answers
    "duplicate" without raising; on this path that would be a message the
    operator believes is recorded and is not.

Fails before scripts/correspond.py exists: the event types are unknown.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from qa.marks import SafetyTier, qa

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "correspond.py"
HOOK = REPO_ROOT / ".claude" / "hooks" / "start" / "open_threads.py"

AT = "2026-09-07T21:00:00+00:00"
LATER = "2026-09-08T07:00:00+00:00"


def _correspond():
    spec = importlib.util.spec_from_file_location("correspond_mod", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _render():
    spec = importlib.util.spec_from_file_location(
        "render_mod_correspond", REPO_ROOT / "scripts" / "render.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sent(msg_id="MSG-0003", text="Proc /events/universe vraci HTML?", **over):
    base = {"type": "telegram_sent", "at": AT, "by": "operator",
            "source": "scripts/correspond.py", "msg_id": msg_id,
            "text": text, "origin": "telegram"}
    base.update(over)
    return base


def _reply(msg_id="REPLY-0002", to="MSG-0003", text="Fixed in 193eee6.", **over):
    base = {"type": "telegram_reply", "at": LATER, "by": "vendor",
            "source": "scripts/correspond.py", "msg_id": msg_id,
            "reply_to": to, "text": text, "origin": "telegram"}
    base.update(over)
    return base


def _run(args, tmp_path, encoding=None):
    """The CLI or the hook as the operator's machine runs it."""
    env = dict(os.environ)
    env["QA_STATE_DIR"] = str(tmp_path)
    if encoding:
        env["PYTHONIOENCODING"] = encoding
    else:
        env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run([sys.executable, *args], cwd=str(REPO_ROOT), env=env,
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace")


# ---------------------------------------------------------------------------
# The journal contract
# ---------------------------------------------------------------------------
@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_telegram_events_are_journal_events_and_reject_a_bad_shape(tmp_path, monkeypatch):
    """Both types append; a message with no words is refused, not stored.

    An empty `text` is the whole failure this feature exists to prevent -- a
    record that says a conversation happened without saying what was in it is
    ET-22498 again with a nicer id.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.state import JournalError, append_event, read_events

    assert append_event(_sent(via="ET-22498")) == "appended"
    assert append_event(_reply()) == "appended"

    with pytest.raises(JournalError):
        append_event(_sent(msg_id="MSG-0004", text=""))
    with pytest.raises(JournalError):
        append_event(_reply(msg_id="REPLY-0003", to=None))
    # An id-less message keys as `telegram_sent|None`, so the SECOND one is
    # answered "duplicate" and thrown away without a word. The CLI always sets
    # an id; the journal must not depend on that being the only writer.
    with pytest.raises(JournalError):
        append_event(_sent(msg_id=None))
    with pytest.raises(JournalError):
        append_event(_reply(msg_id=None))

    kept = read_events()
    assert [e["msg_id"] for e in kept] == ["MSG-0003", "REPLY-0002"], (
        "a refused event must leave nothing behind"
    )


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_telegram_event_moves_neither_axis(tmp_path, monkeypatch):
    """The design decision, executable.

    A telegram_sent carrying `findings` is the shape that would be tempting to
    wire into the fold. It must change nothing: the operator chatting to the
    vendor is not an event about a report, and a row that moved because of one
    would be a state nobody could trace back to a run or a filing.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.fold import fold
    from tests.meta.test_pipeline_fold import _filed, ledger, row

    base = _filed("CYM-a", 46, "pending")
    tele = _sent(findings=["CYM-a"], via="ET-22498")

    without = fold(ledger(row("CYM-a")), events=base)["findings"]["CYM-a"]
    with_it = fold(ledger(row("CYM-a")), events=base + [tele])["findings"]["CYM-a"]

    assert without == with_it
    assert not with_it["filing"].get("refused"), (
        "the fold must ignore a telegram event, not refuse it -- a refusal is "
        "a complaint printed on a row that has nothing to do with it"
    )


# ---------------------------------------------------------------------------
# Ids
# ---------------------------------------------------------------------------
@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_allocator_never_reissues_an_archived_or_a2a_id(tmp_path, monkeypatch):
    """MSG-0002 and REPLY-0001 are taken, and 38 vendor ids are not numbers."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.state import append_event, read_events
    from tests.meta.test_pipeline_fold import event

    for e in (
        event("message", at=AT, by="operator", source="scripts/migrate_ledger.py",
              msg_id="MSG-0002"),
        event("reply", at=AT, by="vendor", source="scripts/migrate_ledger.py",
              msg_id="REPLY-0001", evidence_id="archive#REPLY-0001"),
        event("message", at=AT, by="vendor", source="scripts/bounty.py a2a-inbox",
              msg_id="a2a_660f91eea5674858", text="first pass"),
    ):
        append_event(e)

    mod = _correspond()
    events = read_events()
    assert mod.next_msg_id(events, "MSG") == "MSG-0003"
    assert mod.next_msg_id(events, "REPLY") == "REPLY-0002"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_two_sends_of_one_id_do_not_silently_collapse(tmp_path, monkeypatch):
    """`duplicate` is an error here, not a shrug.

    append_event answers "duplicate" and returns. Everywhere else that is
    idempotence; on this path it is a message the operator was told was
    recorded and is not.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.state import append_event, read_events

    assert append_event(_sent()) == "appended"
    assert append_event(_sent(text="different words, same id")) == "duplicate"

    mod = _correspond()
    monkeypatch.setattr(mod, "next_msg_id", lambda events, prefix: f"{prefix}-0003")
    with pytest.raises(SystemExit):
        mod.main(["sent", "--text", "a second message given a taken id"])

    assert len(read_events()) == 1


# ---------------------------------------------------------------------------
# Threads
# ---------------------------------------------------------------------------
@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_open_threads_are_the_ones_with_no_reply(tmp_path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.state import append_event, read_events

    append_event(_sent("MSG-0003", "otazka jedna"))
    append_event(_sent("MSG-0004", "otazka dva"))
    append_event(_reply("REPLY-0002", to="MSG-0003"))

    mod = _correspond()
    still_open = mod.open_threads(read_events())
    assert [t["msg_id"] for t in still_open] == ["MSG-0004"]

    append_event(_reply("REPLY-0003", to="MSG-0004"))
    assert mod.open_threads(read_events()) == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_thread_is_found_by_our_id_their_ticket_or_its_words(tmp_path, monkeypatch):
    """The operator will type THEIR id.

    "odpovedeli na ET-22498" is the sentence this feature is for. A lookup that
    only knows MSG-0003 makes them go and find our id first, which is the same
    as not having the record.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.state import append_event, read_events

    append_event(_sent("MSG-0003", "Proc /events/universe vraci HTML?", via="ET-22498"))
    append_event(_sent("MSG-0004", "neco uplne jineho"))

    mod = _correspond()
    events = read_events()
    for query in ("MSG-0003", "ET-22498", "et-22498", "events/universe"):
        found = mod.match(events, query)
        assert [t["msg_id"] for t in found] == ["MSG-0003"], f"{query!r} found {found}"


# ---------------------------------------------------------------------------
# The console the operator actually has
# ---------------------------------------------------------------------------
@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_show_survives_an_emoji_on_a_cp1250_console(tmp_path, monkeypatch):
    """Their first-pass replies are full of emoji and this is a Czech Windows.

    Reading the journal with the default console encoding is how three
    exploratory commands died on 2026-09-08: UnicodeEncodeError on \\U0001f3c6,
    mid-output.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.state import append_event

    append_event(_sent("MSG-0003", "\U0001f3c6 bug report \U0001f41b", via="ET-22498"))

    proc = _run([str(SCRIPT), "show", "MSG-0003"], tmp_path, encoding="cp1250")
    assert proc.returncode == 0, proc.stderr
    assert "MSG-0003" in proc.stdout


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_reply_to_an_unknown_message_is_refused(tmp_path, monkeypatch):
    """The withdraw.py lesson: a mistyped id is a permanent no-op otherwise."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.state import append_event, read_events

    append_event(_sent("MSG-0003"))

    mod = _correspond()
    with pytest.raises(SystemExit) as caught:
        mod.main(["reply", "--to", "MSG-9999", "--text", "jejich odpoved"])
    assert "MSG-0003" in str(caught.value), "refusing should name what does exist"
    assert len(read_events()) == 1


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_telegram_never_reaches_the_api_panel_or_the_counts(tmp_path, monkeypatch):
    """The boundary test_pipeline_render.py:425 guards from the other side.

    That panel is the bounty API conversation and says so. A Telegram message
    appearing in it would claim we said something to them through a channel
    that has none of the API channel's guarantees.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.fold import fold
    from qa.state import append_event, head, read_events
    from tests.meta.test_pipeline_fold import _filed, ledger, row

    for e in _filed("CYM-a", 46, "pending"):
        append_event(e)
    before = _render().build_payload(
        ledger=dict(fold(ledger(row("CYM-a")), events=read_events()),
                    events_head=head()))

    append_event(_sent(findings=["CYM-a"], via="ET-22498"))
    after = _render().build_payload(
        ledger=dict(fold(ledger(row("CYM-a")), events=read_events()),
                    events_head=head()))

    assert after["thread_counts"] == before["thread_counts"]
    for finding in after["findings"]:
        for message in finding.get("thread") or []:
            assert "MSG-0003" not in json.dumps(message), (
                "a Telegram message leaked into the API panel"
            )


# ---------------------------------------------------------------------------
# The hook: the part that makes it automatic
# ---------------------------------------------------------------------------
@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_hook_names_an_open_thread_by_both_ids(tmp_path, monkeypatch):
    """Session start, with nobody asking anything.

    The operator's requirement in one line: "to mas delat automaticky kdyz se o
    tom bavime". A CLI they have to remember to run is the dead inbox/ again.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.state import append_event

    append_event(_sent("MSG-0003", "Proc /events/universe vraci HTML?", via="ET-22498"))

    proc = _run([str(HOOK)], tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert "MSG-0003" in proc.stdout
    assert "ET-22498" in proc.stdout, (
        "their ticket id is what the operator will say out loud"
    )


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_hook_names_an_open_a2a_thread_too(tmp_path, monkeypatch):
    """Telegram is not the only channel that waits on them.

    The hook read scripts/correspond.py, so an a2a question nobody had
    answered was invisible at session start -- and a2a is the channel a
    session is least likely to remember on its own, because `scripts/a2a.py`
    has sent two questions in its life while eleven threads exist. Found by
    the architecture audit, 2026-09-20, in the same hour as the two readers
    of `unanswered` (tests/meta/test_pipeline_channels.py).

    The a2a thread below is the shape that only THEIR receipt records: the
    send was made by hand, so no a2a_intent of ours exists for it.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.state import append_event

    append_event({"type": "message", "at": AT, "by": "vendor",
                  "source": "scripts/bounty.py a2a-inbox", "msg_id": "a2a_r1",
                  "text": "queued for review", "origin": "a2a", "auto": True,
                  "kind": "first_pass", "reply_to": "a2a_ours_1"})

    proc = _run([str(HOOK)], tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert "a2a_ours_1" in proc.stdout, (
        f"the open a2a thread is not named at session start: {proc.stdout!r}")
    assert "queued for review" not in proc.stdout, (
        "ids only -- the hook must not put their text into the context")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_hook_is_silent_when_nothing_is_open(tmp_path, monkeypatch):
    """No open thread means no output at all -- not a heading saying zero.

    A hook that speaks on every session start whether or not it has anything to
    say is a hook that gets read once and then skipped.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.state import append_event

    proc = _run([str(HOOK)], tmp_path)
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""

    append_event(_sent("MSG-0003"))
    append_event(_reply("REPLY-0002", to="MSG-0003"))
    answered = _run([str(HOOK)], tmp_path)
    assert answered.returncode == 0
    assert answered.stdout.strip() == ""


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_hook_never_fails_a_session(tmp_path):
    """A note about correspondence must not be able to stop the work.

    Every other reader of the journal is right to refuse a damaged one. This one
    runs before the operator has typed anything, so a refusal here is a session
    that will not start.
    """
    missing = _run([str(HOOK)], tmp_path / "nothing-here")
    assert missing.returncode == 0
    assert missing.stdout.strip() == ""

    journal = tmp_path / "journal" / "events.jsonl"
    journal.parent.mkdir(parents=True, exist_ok=True)
    journal.write_text('{"type":"telegram_sent","seq":1', encoding="utf-8")
    truncated = _run([str(HOOK)], tmp_path)
    assert truncated.returncode == 0, truncated.stderr
    assert "Traceback" not in truncated.stderr

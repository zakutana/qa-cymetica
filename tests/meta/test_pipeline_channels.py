"""CHN: one reader over all three channels, and the alert that comes out of it.

The operator's complaint on 2026-09-08: three channels, three shapes, and no
way to hold the state of them in your head. Bug reports, Telegram and a2a all
already meet in one place -- the journal -- so this is a reader, not a store.

Two things it must get right or it is worse than nothing:

  * **Silence is never the default.** 35 of the 39 a2a messages we hold are the
    automated first pass, and an alert that fires on the trophy emoji is one
    the operator learns to ignore within a day. So automated replies are
    silent. But a message we CANNOT classify -- every one recorded before
    2026-09-08, because fetch_inbox dropped the discriminator -- must speak,
    saying it could not be classified. A reader that treats unknown as robot
    hides exactly the message it exists to surface.
  * **Reading the state must not need the network.** The operator asked for a
    command for when the server is off. `--offline` answers from the journal
    alone, and the test asserts zero requests rather than trusting the flag.
"""

from __future__ import annotations

import importlib.util
import time
import sys
import subprocess
import os
from pathlib import Path

import httpx

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent

AT = "2026-09-08T08:00:00+00:00"
LATER = "2026-09-08T09:00:00+00:00"


def _channels():
    import qa.channels as mod

    importlib.reload(mod)
    return mod


def _bounty_module():
    spec = importlib.util.spec_from_file_location(
        "bounty_under_test", REPO / "scripts" / "bounty.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _cli():
    spec = importlib.util.spec_from_file_location(
        "channels_cli", REPO / "scripts" / "channels.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _vendor_a2a(msg_id, at=AT, text="hello", auto=None, kind=None, answers=None):
    event = {"type": "message", "at": at, "by": "vendor",
             "source": "scripts/bounty.py a2a-inbox", "msg_id": msg_id,
             "text": text, "origin": "a2a"}
    if auto:
        event["auto"] = True
    if kind:
        event["kind"] = kind
    if answers:
        event["reply_to"] = answers
    return event


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_alert_is_silent_on_an_automated_reply(tmp_path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.state import append_event, read_events

    append_event(_vendor_a2a("a2a_1", text="\U0001f3c6 Reward Pathways Unlocked",
                             auto=True, kind="first_pass"))
    lines, _ = _channels().new_lines(read_events(), set())
    assert lines == [], f"the emoji woke the operator: {lines}"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_alert_speaks_when_it_cannot_classify(tmp_path, monkeypatch):
    """Every message recorded before 2026-09-08 is this case.

    fetch_inbox dropped auto and kind, and the journal is append-only, so those
    39 can never be told apart. Treating them as automated would hide a human
    reply; treating them as human silently would be a guess. It says which.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.state import append_event, read_events

    append_event(_vendor_a2a("a2a_old", text="Human reply, covering everything"))
    lines, _ = _channels().new_lines(read_events(), set())
    assert len(lines) == 1
    assert "a2a_old" in lines[0]
    assert "unknown" in lines[0].lower(), (
        "it spoke, but claimed to know this was a human -- it does not"
    )


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_human_reply_and_a_telegram_answer_both_reach_the_alert(tmp_path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.state import append_event, read_events

    append_event(_vendor_a2a("a2a_2", text="You were right about the channel.",
                             kind="human"))
    append_event({"type": "telegram_sent", "at": AT, "by": "operator",
                  "source": "scripts/correspond.py", "msg_id": "MSG-0009",
                  "text": "a question", "origin": "telegram"})
    append_event({"type": "telegram_reply", "at": LATER, "by": "vendor",
                  "source": "scripts/correspond.py", "msg_id": "REPLY-0009",
                  "reply_to": "MSG-0009", "text": "Fixed in 193eee6.",
                  "origin": "telegram"})

    lines, seen = _channels().new_lines(read_events(), set())
    joined = "\n".join(lines)
    assert len(lines) == 2, f"one line per thing THEY said, got {lines}"
    assert "a2a_2" in joined and "REPLY-0009" in joined
    # Naming what a reply answers is useful. Announcing our own outbound
    # message as though it had arrived is not.
    assert not any(line.startswith("[telegram] MSG-") for line in lines), (
        "our own message was announced back to us as an arrival"
    )

    # And nothing is announced twice.
    again, _ = _channels().new_lines(read_events(), seen)
    assert again == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_report_moving_reaches_the_alert(tmp_path, monkeypatch):
    """The bug channel speaks by changing a status, not by sending a message."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.state import append_event, read_events

    append_event({"type": "vendor_status", "at": AT, "by": "agent",
                  "source": "scripts/bounty.py", "report_id": 76,
                  "status": "fixed", "observed_at": AT, "evidence_id": "ev-1"})
    lines, _ = _channels().new_lines(read_events(), set())
    assert len(lines) == 1 and "#76" in lines[0] and "fixed" in lines[0]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_state_names_all_three_channels(tmp_path, monkeypatch):
    """One shape, so a report about the channels cannot quietly omit one."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    state = _channels().state()
    assert set(state) == {"bug", "telegram", "a2a"}
    for name, channel in state.items():
        assert "unanswered" in channel, f"{name} cannot say what is outstanding"
        assert "last_from_them" in channel, f"{name} cannot say when they last spoke"
        # Which side the outstanding items are on. A message of ours with no
        # reply waits on THEM; an obligation on a filed row waits on US, and
        # the first version of this printed one label over both -- so the
        # status report told the operator to act on a thread that was theirs.
        assert channel["waiting_on"] in ("us", "them"), name

    assert state["bug"]["waiting_on"] == "us", (
        "an obligation on a report is a debt of ours"
    )
    assert state["telegram"]["waiting_on"] == "them"
    assert state["a2a"]["waiting_on"] == "them"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_receipt_is_not_the_answer_when_timing_a_channel(tmp_path, monkeypatch):
    """The whole side quest turns on this one line.

    The a2a first pass arrives in 2 to 6 seconds, and Cymetica said in writing
    what it is: *"the 2 to 6 second a2a first pass is a receipt, the same thing
    as the Ref: ET-xxxxx auto-ack you see on Telegram."* A comparison that
    times the receipt would report a2a as roughly a thousand times faster than
    Telegram and be worthless -- worse than worthless, because it would be a
    number, and the point of measuring is to replace an impression with one.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.state import append_event, read_events

    append_event({"type": "a2a_intent", "at": "2026-09-08T08:00:00+00:00",
                  "by": "operator", "source": "scripts/a2a.py",
                  "msg_id": "A2A-0001", "text": "a question", "origin": "a2a"})
    append_event({"type": "a2a_outcome", "at": "2026-09-08T08:00:01+00:00",
                  "by": "agent", "source": "scripts/a2a.py",
                  "msg_id": "A2A-0001", "outcome": "accepted", "via": "a2a_ours"})
    # Both of their messages answer the same send of ours.
    append_event(_vendor_a2a("a2a_receipt", at="2026-09-08T08:00:04+00:00",
                             text="queued for review", auto=True,
                             kind="first_pass", answers="a2a_ours"))
    append_event(_vendor_a2a("a2a_human", at="2026-09-08T09:30:00+00:00",
                             text="You were right.", kind="human",
                             answers="a2a_ours"))

    paired = _channels().pairs(read_events())
    a2a_rows = [p for p in paired if p["channel"] == "a2a"]
    assert len(a2a_rows) == 1
    assert a2a_rows[0]["answer_id"] == "a2a_human", (
        f"the receipt was timed as the answer: {a2a_rows[0]}"
    )
    assert a2a_rows[0]["minutes"] == 90


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_two_events_recorded_in_one_breath_are_not_a_latency(tmp_path, monkeypatch):
    """The four telegram events we hold share one timestamp, and it is not theirs.

    They were entered together on 2026-09-08 for a conversation held on the
    7th, so the arithmetic reads "answered in 0 minutes" and `compare` printed
    exactly that. A channel that appears to answer instantly because somebody
    typed both halves in at once is the worst possible output here: it is a
    number, and a wrong number displaces the impression it was meant to
    correct.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.state import append_event, read_events

    both = "2026-09-08T06:58:42+00:00"
    append_event({"type": "telegram_sent", "at": both, "by": "operator",
                  "source": "scripts/correspond.py", "msg_id": "MSG-0001",
                  "text": "q", "origin": "telegram"})
    append_event({"type": "telegram_reply", "at": both, "by": "vendor",
                  "source": "scripts/correspond.py", "msg_id": "REPLY-0001",
                  "reply_to": "MSG-0001", "text": "a", "origin": "telegram"})

    row = _channels().pairs(read_events())[0]
    assert row["answer_id"] == "REPLY-0001", "the answer itself is still recorded"
    assert row["minutes"] is None, "0 minutes was reported as a real latency"
    assert _channels().compare(read_events())["telegram"]["n"] == 0


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_comparison_says_how_little_it_rests_on(tmp_path, monkeypatch):
    """Three answers on one evening is a demonstration, not a comparison."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.state import append_event, read_events

    append_event({"type": "telegram_sent", "at": "2026-09-08T08:00:00+00:00",
                  "by": "operator", "source": "scripts/correspond.py",
                  "msg_id": "MSG-0001", "text": "q", "origin": "telegram"})
    append_event({"type": "telegram_reply", "at": "2026-09-08T08:30:00+00:00",
                  "by": "vendor", "source": "scripts/correspond.py",
                  "msg_id": "REPLY-0001", "reply_to": "MSG-0001",
                  "text": "a", "origin": "telegram"})

    report = _channels().compare(read_events())
    assert report["telegram"]["n"] == 1
    assert report["telegram"]["median_minutes"] == 30
    assert report["conclusive"] is False, (
        "one answer per channel is not a comparison, and a report that does "
        "not say so will be read as one"
    )


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_backdated_message_tells_the_truth_about_when_it_was_sent(tmp_path, monkeypatch):
    """Every Telegram event we hold is stamped the moment it was typed in.

    All four were recorded on 2026-09-08 for a conversation held on the 7th,
    with the truth in a note that no arithmetic can read. Without --at the
    comparison has no Telegram data at all, only a2a.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.state import read_events

    spec = importlib.util.spec_from_file_location(
        "correspond_at", REPO / "scripts" / "correspond.py")
    correspond = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(correspond)

    correspond.main(["sent", "--text", "asked yesterday",
                     "--at", "2026-09-07T19:32:00+00:00"])
    sent = [e for e in read_events() if e["type"] == "telegram_sent"][0]
    assert sent["at"] == "2026-09-07T19:32:00+00:00"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_answer_we_cannot_time_is_not_an_unanswered_question(tmp_path, monkeypatch):
    """"Unanswered" means no answer, not "no number".

    The deep pass of 2026-09-08 found this by reading the output: `compare`
    printed "2 still unanswered" about MSG-0003 and MSG-0004, both of which the
    vendor had answered. Their pairs carry an answer_id and no minutes, because
    both halves were recorded in the same breath, and the count was keyed on
    the minutes instead of on the answer.

    A report that miscounts the thing it exists to count is worse than no
    report: the operator would have chased two replies that were already in.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.state import append_event, read_events

    both = "2026-09-08T06:58:42+00:00"
    append_event({"type": "telegram_sent", "at": both, "by": "operator",
                  "source": "scripts/correspond.py", "msg_id": "MSG-0001",
                  "text": "answered, but both rows typed in together",
                  "origin": "telegram"})
    append_event({"type": "telegram_reply", "at": both, "by": "vendor",
                  "source": "scripts/correspond.py", "msg_id": "REPLY-0001",
                  "reply_to": "MSG-0001", "text": "a", "origin": "telegram"})
    append_event({"type": "telegram_sent", "at": "2026-09-08T07:00:00+00:00",
                  "by": "operator", "source": "scripts/correspond.py",
                  "msg_id": "MSG-0002", "text": "really unanswered",
                  "origin": "telegram"})

    report = _channels().compare(read_events())["telegram"]
    assert report["unanswered"] == 1, (
        f"an answered question was counted as unanswered: {report}"
    )
    assert report["answered_but_untimed"] == 1, (
        "the untimed pair vanished instead of being reported as its own state"
    )


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_alert_survives_a_journal_caught_mid_append(tmp_path):
    """`watch` must not die on the condition its own comment calls normal.

    serve.py --ask appends every fifteen minutes. A journal read while a line
    is half-written raises JournalError, and the priming read used to sit
    outside the try that protects the loop -- so starting the watcher in that
    window killed it before its first tick and the alert was silently off for
    the whole session.

    The retry notice goes to stderr for the second half of the same reason:
    every stdout line of this command becomes a message in the operator's chat.
    """
    journal = tmp_path / "journal" / "events.jsonl"
    journal.parent.mkdir(parents=True, exist_ok=True)
    journal.write_text('{"type":"telegram_sent","seq":1', encoding="utf-8")

    proc = subprocess.Popen(
        [sys.executable, str(REPO / "scripts" / "channels.py"), "watch",
         "--interval", "0.2"],
        cwd=str(REPO), env={**os.environ, "QA_STATE_DIR": str(tmp_path),
                            "PYTHONIOENCODING": "utf-8"},
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        time.sleep(2.0)
        assert proc.poll() is None, (
            "watch exited on a truncated journal instead of retrying, so the "
            "alert would be off for the session"
        )
    finally:
        proc.terminate()
        out, err = proc.communicate(timeout=10)

    assert out.strip() == "", (
        f"the retry notice reached stdout, which is the operator's chat: {out!r}"
    )
    assert "read failed" in err, "the retry was not reported anywhere at all"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_status_offline_makes_no_request(tmp_path, monkeypatch):
    """The operator asked for this for when the server is off. Asserted, not trusted."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.client import build_mock_client

    calls = []
    cli = _cli()
    cli._live_client = lambda: build_mock_client(
        lambda r: calls.append(r) or httpx.Response(200, json={}), timeout=5.0)

    assert cli.main(["status", "--offline"]) == 0
    assert calls == [], f"--offline reached the network {len(calls)} time(s)"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_thread_is_reconstructed_from_their_reply_to_when_our_send_was_not_journalled(
        tmp_path, monkeypatch):
    """`compare` said a2a asked 0 while eight threads of ours sat in the journal.

    `pairs` keyed a2a on `a2a_outcome.via`, and `scripts/a2a.py` -- which is
    the only thing that writes an a2a_intent -- has never once been run: both
    event types are zero in a journal of 1,475. The eight questions we did ask
    went out by another path, and the only record of them is the `reply_to` on
    their answers, which names OUR message with THEIR id for it.

    So the thread key is their `reply_to`, and the moment we asked is taken
    from the automated receipt on that thread -- the one message guaranteed to
    arrive seconds after a send, by their own description of it. It is marked
    `asked_at_from: "receipt"` because it is a proxy: a number that cannot say
    where it came from is how a comparison becomes an impression again.

    A journalled intent still wins where one exists, so nothing about
    scripts/a2a.py's contract changes.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.state import append_event, read_events

    append_event(_vendor_a2a("a2a_r1", at="2026-09-08T08:00:04+00:00",
                             text="queued for review", auto=True,
                             kind="first_pass", answers="a2a_theirs"))
    append_event(_vendor_a2a("a2a_h1", at="2026-09-08T09:30:00+00:00",
                             text="Rewards are paid in ET10.",
                             answers="a2a_theirs"))

    rows = [p for p in _channels().pairs(read_events()) if p["channel"] == "a2a"]
    assert len(rows) == 1, f"the thread was not reconstructed: {rows}"
    assert rows[0]["answer_id"] == "a2a_h1"
    assert rows[0]["minutes"] == 90
    assert rows[0]["asked_at_from"] == "receipt", (
        "a moment taken from their receipt must say so, because it is a "
        "proxy for a send we never recorded"
    )

    # The other half of the docstring -- "a journalled intent still wins where
    # one exists" -- which nothing asserted. Deleting the precedence guard, so
    # that reconstruction overwrites a real send, left every self-test green:
    # this fixture has no intent, and the sibling that does has its intent and
    # receipt four seconds apart, both rounding to 90 minutes, and never reads
    # `asked_at_from`. Three readers reproduced it. So the intent goes in HERE,
    # after the fact, and the row must change back to ours.
    from qa.state import append_event as _append

    _append({"type": "a2a_intent", "at": "2026-09-08T07:55:00+00:00",
             "by": "operator", "source": "scripts/a2a.py",
             "msg_id": "A2A-9001", "text": "How are rewards paid?",
             "origin": "a2a"})
    _append({"type": "a2a_outcome", "at": "2026-09-08T07:55:02+00:00",
             "by": "agent", "source": "scripts/a2a.py",
             "msg_id": "A2A-9001", "outcome": "accepted", "via": "a2a_theirs"})

    rows = [p for p in _channels().pairs(read_events()) if p["channel"] == "a2a"]
    assert len(rows) == 1, f"the intent created a second row: {rows}"
    assert rows[0]["asked_at_from"] == "us", (
        f"a send we actually journalled was overwritten by a proxy taken from "
        f"their receipt, so the moment we asked is now theirs to define: "
        f"{rows[0]}")
    # OUR id for the message, which is what a2a.py records and what the
    # reconstruction cannot know -- so this is also the visible difference
    # between a thread we journalled and one rebuilt from their side.
    assert rows[0]["question_id"] == "A2A-9001"
    assert rows[0]["minutes"] == 95, (
        f"and the latency is measured from OUR send (07:55) rather than from "
        f"their receipt (08:00:04): {rows[0]}")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_human_reply_is_real_even_when_nothing_classified_it(tmp_path, monkeypatch):
    """`real` required a `kind`, and their human replies carry none.

    `scripts/bounty.py` wrote `auto` and `kind` only when truthy, so a reply
    the vendor marked `auto: false, kind: null` -- which is every human answer
    they have sent -- reached the journal with neither key, and
    `bool(event.get("kind"))` made it unreal. The four answers we actually
    have were invisible to the comparison for that reason alone.

    The discriminator is the receipt, not the presence of a label: a message
    is an answer unless it is automated or is the first-pass receipt.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.state import append_event, read_events

    append_event(_vendor_a2a("a2a_r2", at="2026-09-08T08:00:04+00:00",
                             auto=True, kind="first_pass", answers="a2a_t2"))
    # As bounty.py recorded it before this commit: no auto, no kind.
    append_event(_vendor_a2a("a2a_bare", at="2026-09-08T08:45:00+00:00",
                             text="Ref: ET-23959. The answer is 1,000 ET10.",
                             answers="a2a_t2"))

    rows = [p for p in _channels().pairs(read_events()) if p["channel"] == "a2a"]
    assert rows and rows[0]["answer_id"] == "a2a_bare", (
        "their answer was discarded for carrying no label"
    )
    assert rows[0]["minutes"] == 45


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_receipt_alone_is_a_question_they_have_not_answered(tmp_path, monkeypatch):
    """Four of the eight threads have only the receipt, and that is the point.

    An unanswered question must count as asked and unanswered, not vanish. If
    the receipt were allowed to close its own thread the four would read as
    answered in four seconds each, which is the failure this whole reader was
    built to prevent.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.state import append_event, read_events

    append_event(_vendor_a2a("a2a_r3", at="2026-09-09T22:13:17+00:00",
                             auto=True, kind="first_pass", answers="a2a_t3"))

    report = _channels().compare(read_events())
    assert report["a2a"]["asked"] == 1
    assert report["a2a"]["unanswered"] == 1
    assert report["a2a"]["n"] == 0
    assert report["a2a"]["median_minutes"] is None


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_discriminator_is_recorded_even_when_it_is_false(tmp_path, monkeypatch):
    """The reader can only be as good as what fetch_inbox wrote down.

    `if metadata.get("auto")` kept the key only when it was True, so "we know
    this is a person" and "we have no idea" arrived on the journal as the same
    thing: no key. The three-valued alert -- robot, human, unclassifiable --
    then had nothing to read for the human case, and 44 of 52 messages sat in
    the unclassifiable bucket that exists for the 39 written before there was
    a discriminator at all.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.state import read_events

    bounty = _bounty_module()
    recorded = bounty.record_inbox([{
        "id": "a2a_new", "created_at": "2026-09-10T01:51:41+00:00",
        "content": "Rewards are paid in ET10.", "thread_id": "a2a_via",
        "parent_message_id": "a2a_ours",
        "metadata": {"auto": False, "kind": None},
    }])
    assert len(recorded["new"]) == 1

    event = [e for e in read_events() if e.get("msg_id") == "a2a_new"][0]
    assert event["auto"] is False, (
        "a message the vendor says is not automated must say so on the "
        "journal, or it cannot be told from one nobody classified"
    )
    assert "kind" in event and event["kind"] is None

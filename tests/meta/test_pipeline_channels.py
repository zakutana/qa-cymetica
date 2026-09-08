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

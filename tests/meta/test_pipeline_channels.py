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


def _vendor_a2a(msg_id, at=AT, text="hello", auto=None, kind=None):
    event = {"type": "message", "at": at, "by": "vendor",
             "source": "scripts/bounty.py a2a-inbox", "msg_id": msg_id,
             "text": text, "origin": "a2a"}
    if auto:
        event["auto"] = True
    if kind:
        event["kind"] = kind
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
        assert "unanswered" in channel, f"{name} cannot say what is waiting on us"
        assert "last_from_them" in channel, f"{name} cannot say when they last spoke"


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

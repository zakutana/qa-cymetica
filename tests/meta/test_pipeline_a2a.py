"""A2A: the third channel, which we could only ever listen to.

Nothing in scripts/ has ever sent an a2a message. The one sender in the whole
repository is a check posting one fixed sentence, so the long question of
2026-09-07 19:32 -- the one that made them route a2a to a human, and produced
three reports -- exists nowhere and cannot be read back. Their answer is on the
journal; our question is not.

Two things are recorded here that were not:

  * what we SENT, in two events, because the POST can time out and the text
    must survive that. Keyed on OUR id, never on the server's -- a send whose
    response never arrived has no server id, which is precisely the case the
    record exists for. Rule 9, the shape submit.py and verify.py already have.
  * what tells one of their messages from another. The wire carries
    metadata.auto, metadata.kind and parent_message_id; fetch_inbox read all
    three and kept none, so from the journal a trophy-emoji routing prompt is
    indistinguishable from a human answer. An alert that fires on the emoji is
    an alert the operator learns to ignore, and 35 of the 39 messages we hold
    are that emoji.

The 39 already recorded cannot be back-tagged -- the journal is append-only --
so a missing `kind` means UNKNOWN, never "human" and never "robot".

Fails before scripts/a2a.py exists: the event types are unknown.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import httpx
import pytest

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO / "scripts" / "a2a.py"

AT = "2026-09-08T08:00:00+00:00"


def _a2a():
    spec = importlib.util.spec_from_file_location("a2a_mod", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _client(handler):
    from qa.client import build_mock_client

    return build_mock_client(handler, timeout=5.0)


def _msg(msg_id, at, content="hello", auto=False, kind=None, parent=None):
    """One inbox row in their shape, including the fields we used to drop."""
    meta = {}
    if auto:
        meta["auto"] = True
        meta["kind"] = kind or "first_pass"
    elif kind:
        meta["kind"] = kind
    if parent:
        meta["in_reply_to"] = parent
    return {"id": msg_id, "created_at": at, "content": content,
            "from_agent_id": "nexus", "thread_id": "a2a_thread",
            "parent_message_id": parent, "metadata": meta}


def _inbox(*messages):
    return _client(lambda r: httpx.Response(200, json={"messages": list(messages)}))


# ---------------------------------------------------------------------------
# Inbound: keep what tells them apart
# ---------------------------------------------------------------------------
@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_inbox_keeps_what_tells_a_human_from_a_robot(tmp_path, monkeypatch):
    """auto, kind and the message it answers -- read today, kept from today.

    Without these the journal cannot answer the only question an alert needs to
    ask, and the caller's in-memory `new` list -- which does carry them -- is
    thrown away the moment fetch_inbox returns.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.state import read_events

    spec = importlib.util.spec_from_file_location(
        "bounty_a2a_mod", REPO / "scripts" / "bounty.py")
    bounty = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bounty)

    asked = []
    rows = [
        _msg("a2a_1", AT, "\U0001f3c6 Reward Pathways Unlocked", auto=True),
        _msg("a2a_2", AT, "You were right about the channel.",
             kind="human", parent="a2a_ours"),
    ]

    def answer(request):
        asked.append(dict(request.url.params))
        return httpx.Response(200, json={"messages": rows})

    inbox = _client(answer)
    said = bounty.fetch_inbox(client=inbox, agent_id="expire76-qa")
    # NEXT 2026-10-01: without `limit` the inbox returns only the 50 newest (168
    # held on 2026-10-02; 200 is their maximum, 422 above it). A page that comes
    # back full says so, because an older message may be on the page not read.
    assert asked == [{"unread_only": "false", "limit": "200"}], asked
    assert said["full"] is False
    full = [_msg(f"a2a_{i}", AT) for i in range(200)]
    rows[:] = full
    assert bounty.fetch_inbox(client=_client(answer), agent_id="expire76-qa")["full"] is True, (
        "a page of exactly the limit was not marked as possibly cut")
    rows[:] = [_msg("a2a_1", AT, "\U0001f3c6 Reward Pathways Unlocked", auto=True),
               _msg("a2a_2", AT, "You were right about the channel.",
                    kind="human", parent="a2a_ours")]
    bounty.fetch_inbox(client=_client(answer), agent_id="expire76-qa")

    by_id = {e["msg_id"]: e for e in read_events() if e["type"] == "message"}
    assert by_id["a2a_1"]["auto"] is True
    assert by_id["a2a_1"]["kind"] == "first_pass"
    assert by_id["a2a_2"].get("auto") is not True
    # And its kind. Asserting it only on the automated row left the keeping of
    # `kind` free to be nested under the `auto` branch in fetch_inbox: still
    # green, while every human reply loses its kind and the alert -- whose rule
    # is that a missing kind means UNKNOWN -- announces it forever as
    # unclassifiable, the one distinction this check is named for. Deep pass,
    # 2026-09-08, 3/3.
    assert by_id["a2a_2"].get("kind") == "human", (
        "the human reply's kind was dropped, so it is indistinguishable from "
        "the 39 messages recorded before the discriminator was kept"
    )
    assert by_id["a2a_2"]["reply_to"] == "a2a_ours", (
        "parent_message_id is the only exact pairing key they give us -- the "
        "thread id is one value for the whole account and pairs nothing"
    )
    # Deep pass 2026-10-02 (T16): the fixture above writes the parent into BOTH
    # `parent_message_id` and `metadata.in_reply_to`, and gives every automated row kind
    # first_pass -- so a reader that used only one of the two fields, or one that wrote
    # first_pass for every automated row (the 2026-09-27 R01 incident: every deep reply
    # read as the first pass), stayed green. Each field alone, and a deep row.
    rows[:] = [
        _msg("z_deep", AT, "the deep answer", auto=True, kind="deep"),
        _msg("z_field", AT, "answers", kind="human", parent="a2a_ours"),
        _msg("z_meta", AT, "answers too", kind="human", parent="a2a_ours"),
        _msg("z_failed", AT, "its investigation failed", auto=True, kind="deep_failed")]
    rows[1]["metadata"] = {"kind": "human"}               # the parent only in the field
    rows[2]["parent_message_id"] = None                   # the parent only in the metadata
    bounty.fetch_inbox(client=_client(answer), agent_id="expire76-qa")
    again = {e["msg_id"]: e for e in read_events() if e["type"] == "message"}
    assert again["z_deep"]["kind"] == "deep" and again["z_failed"]["kind"] == "deep_failed", (
        "an automated reply was written as the first pass")
    assert again["z_field"]["reply_to"] == "a2a_ours", "parent_message_id alone did not pair"
    assert again["z_meta"]["reply_to"] == "a2a_ours", "metadata.in_reply_to alone did not pair"

    # Deep pass 2026-10-04 (T17): every row asserted above carries an explicit kind, so a
    # reader that FILLED a missing one -- "human" for a message nobody classified, or `auto:
    # false` -- stayed green, and the rule this file is named for is the other way round: a
    # missing kind means UNKNOWN, never human and never robot. The 200 kind-less rows of the
    # full page above (`a2a_3` to `a2a_199` have no metadata at all) are on the journal with
    # neither key; the vendor saying "this is a person" (`auto: false`, no kind) is a
    # different row, `auto` False and `kind` None.
    kindless = [again[f"a2a_{i}"] for i in range(3, 200)]
    assert len(kindless) == 197 and not [e for e in kindless if "kind" in e or "auto" in e], (
        "a message that came with no metadata was written with a kind or an auto flag -- "
        "unclassified and 'a person' are then the same row",
        [e for e in kindless if "kind" in e or "auto" in e][:2])
    rows[:] = [_msg("z_person", AT, "a person, said so")]
    rows[0]["metadata"] = {"auto": False}
    bounty.fetch_inbox(client=_client(answer), agent_id="expire76-qa")
    person = {e["msg_id"]: e for e in read_events() if e["type"] == "message"}["z_person"]
    assert person["auto"] is False and person["kind"] is None, (
        "'the vendor says this is not automated' lost its auto flag or was given a kind", person)


# ---------------------------------------------------------------------------
# Outbound: the record that did not exist
# ---------------------------------------------------------------------------
@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_send_without_confirm_leaves_nothing_behind(tmp_path, monkeypatch):
    """The operator's condition: a2a goes out only when they say so, in the moment.

    Composing must be free and silent. The failure this forbids is a script
    that writes an intent, then refuses to send -- which would leave the
    journal claiming we asked them something we never asked.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.state import read_events

    mod = _a2a()
    sent = []
    mod._client_for = lambda: _client(
        lambda r: sent.append(r) or httpx.Response(200, json={}))

    assert mod.main(["send", "--text", "why does the recipe say that?"]) == 0
    assert sent == [], "composed without --confirm and still sent it"
    assert read_events() == [], "a message we never sent is on the journal"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_send_that_never_answers_keeps_the_text_and_says_unknown(tmp_path, monkeypatch):
    """Rule 9, on the channel that had no record at all.

    A timeout on a POST does not mean they refused it; it means we stopped
    listening. The text must be on the journal before the request leaves, or
    the one case the record exists for is the one it cannot cover.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.state import read_events

    mod = _a2a()

    # Read the journal from INSIDE the request. Asserting after main() returns
    # cannot see the ordering at all: moving the intent append down into the
    # timeout handler leaves both events present with the same text and the
    # check green, while a process killed mid-POST loses the words -- the only
    # failure the two-event record exists for. The mock's handler is the one
    # place that observes the moment the request leaves, and it was the place
    # this test did not look. Deep pass, 2026-09-08, 3/3.
    in_flight = {}

    def dies(request):
        in_flight["events"] = [e for e in read_events()
                               if e["type"] == "a2a_intent"]
        raise httpx.ReadTimeout("no answer", request=request)

    mod._client_for = lambda: _client(dies)
    mod.main(["send", "--text", "the long question about the channel", "--confirm"])

    assert in_flight.get("events"), (
        "the POST left with no a2a_intent on the journal, so a process killed "
        "here would lose the text -- which is the whole reason for two events"
    )
    assert in_flight["events"][0]["text"] == "the long question about the channel"

    events = read_events()
    intent = [e for e in events if e["type"] == "a2a_intent"]
    outcome = [e for e in events if e["type"] == "a2a_outcome"]
    assert len(intent) == 1 and len(outcome) == 1
    assert intent[0]["text"] == "the long question about the channel"
    assert intent[0]["msg_id"] == "A2A-0001"
    assert outcome[0]["outcome"] == "unknown"
    assert outcome[0].get("via") is None, "a timeout cannot have given us their id"

    # Settled later by a read, never by an edit -- rule 9's second half.
    from qa.state import append_event
    append_event({"type": "a2a_outcome", "at": "2026-09-08T09:00:00+00:00",
                  "by": "agent", "source": "scripts/a2a.py",
                  "msg_id": "A2A-0001", "outcome": "accepted", "via": "a2a_theirs"})
    settled = [e for e in read_events() if e["type"] == "a2a_outcome"]
    assert len(settled) == 2, (
        "the settlement collapsed onto the timeout, so the record still says "
        "we do not know whether they got it"
    )


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_accepted_send_records_the_id_they_gave_it(tmp_path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.state import read_events

    mod = _a2a()
    mod._client_for = lambda: _client(lambda r: httpx.Response(
        200, json={"message": {"id": "a2a_theirs",
                               "created_at": "2026-09-08T08:00:01+00:00"}}))

    mod.main(["send", "--text", "a question", "--confirm"])
    outcome = [e for e in read_events() if e["type"] == "a2a_outcome"][0]
    assert outcome["outcome"] == "accepted"
    assert outcome["via"] == "a2a_theirs"
    assert outcome["server_created_at"] == "2026-09-08T08:00:01+00:00", (
        "their clock on our send is half of every latency we will ever measure"
    )


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_allocator_never_reissues_one_of_their_ids(tmp_path, monkeypatch):
    """Their ids are hex, ours are numbered, and both live in msg_id."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.state import append_event, read_events

    append_event({"type": "message", "at": AT, "by": "vendor",
                  "source": "scripts/bounty.py a2a-inbox",
                  "msg_id": "a2a_660f91eea5674858", "text": "hi", "origin": "a2a"})
    append_event({"type": "a2a_intent", "at": AT, "by": "operator",
                  "source": "scripts/a2a.py", "msg_id": "A2A-0007",
                  "text": "asked earlier", "origin": "a2a"})

    mod = _a2a()
    assert mod.next_a2a_id(read_events()) == "A2A-0008"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_page_does_not_count_their_messages_as_ours(tmp_path, monkeypatch):
    """"messages sent / received" read 43 / 1, and 40 of the 43 were theirs.

    The footer counts every `type: "message"` event as sent by us. That type
    was ours in round one and has been the vendor's a2a inbox ever since, so
    the one number on the page about correspondence has been wrong since the
    inbox read was added -- and wrong in the flattering direction.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.state import append_event

    spec = importlib.util.spec_from_file_location(
        "render_a2a_mod", REPO / "scripts" / "render.py")
    render = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(render)

    append_event({"type": "message", "at": AT, "by": "operator",
                  "source": "scripts/migrate_ledger.py", "msg_id": "MSG-0001",
                  "text": "ours, round one"})
    for i in range(3):
        append_event({"type": "message", "at": AT, "by": "vendor",
                      "source": "scripts/bounty.py a2a-inbox",
                      "msg_id": f"a2a_{i}", "text": "theirs", "origin": "a2a"})

    from qa.state import head

    counts = render.build_payload(
        ledger={"schema": 2, "findings": {}, "events_head": head()},
        inventory={})["thread_counts"]
    assert counts["sent"] == 1, (
        f"three of their messages are being counted as ours: {counts}"
    )


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_schema_refuses_a_send_with_no_words(tmp_path, monkeypatch):
    """The same rule the telegram types carry: a record of a conversation that
    does not say what was in it is the hole this was built to close."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.state import JournalError, append_event

    with pytest.raises(JournalError):
        append_event({"type": "a2a_intent", "at": AT, "by": "operator",
                      "source": "scripts/a2a.py", "msg_id": "A2A-0001",
                      "text": "   "})
    with pytest.raises(JournalError):
        append_event({"type": "a2a_outcome", "at": AT, "by": "agent",
                      "source": "scripts/a2a.py", "outcome": "accepted"})

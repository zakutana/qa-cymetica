"""ROOMS: the Nexus tab -- every question we put to Nexus, and the rooms it opens.

2026-09-11, the operator: they want to see what we write to Nexus the way they
see the correspondence on a bug, split into a General room and one room per
strategy that comes out of it, with their own feedback written into each room
and read back by the next session. The plan is docs/nexus-rooms-plan.md.

Three things are pinned here, because each is a way the page could lie.

  * GENERAL IS COMPLETE AND IN ORDER. Every question, and what happened to it
    -- answered, cut short, given up on, refused, still waiting -- each reply
    straight after its question. A question with no answer is shown as
    unanswered, never dropped: an absence on this page would read as "nothing
    was asked", which is the easiest thing to get wrong.
  * THE ROOMS ARE NOT IN THE PAYLOAD. Notes and samples land while a sweep may
    be running. If they moved the payload, every note would rewrite the
    committed dashboard, dirty the tree and cost the next run its level V --
    the reason state/nexus.jsonl is gitignored. So the console serves the rooms
    on their own, and this holds the payload still while a note arrives.
  * VENDOR TEXT IS TEXT. A Nexus answer is data (CLAUDE.md). It reaches the page
    through esc() and only then through a small markdown subset, so a <script>
    in an answer arrives as characters, not as markup.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from qa.marks import SafetyTier, qa
from tests.meta.test_pipeline_render import REPO, _live_payload, _render, _run_page

T0 = datetime.fromisoformat("2026-09-11T05:00:00+00:00")


def _at(seconds: float) -> str:
    return (T0 + timedelta(seconds=seconds)).isoformat()


def _write(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                    encoding="utf-8")


def _five_questions() -> list[dict]:
    """One of each thing that has happened to a question on this account."""
    full = "x" * 400
    return [
        {"id": "NEX-1", "type": "question", "at": _at(0), "question": "first?",
         "accepted": True},
        {"id": "NEX-1", "type": "poll", "status": "running", "at": _at(60)},
        {"id": "NEX-1", "type": "poll", "status": "done", "at": _at(90)},
        {"id": "NEX-1", "type": "answer", "text": full, "at": _at(90)},
        # finalised "done" with only an opening sentence -- their NEX-0009
        {"id": "NEX-2", "type": "question", "at": _at(100), "question": "second?",
         "accepted": True},
        {"id": "NEX-2", "type": "poll", "status": "done", "at": _at(160)},
        {"id": "NEX-2", "type": "answer", "text": "I'll verify first.", "at": _at(160)},
        # our loop gave up -- and it gave up AFTER the next two were asked, so a
        # thread sorted by bare timestamps would put this reply out of place
        {"id": "NEX-3", "type": "question", "at": _at(200), "question": "third?",
         "accepted": True},
        {"id": "NEX-3", "type": "gave_up", "status": "running", "at": _at(1100)},
        # refused before an investigation started
        {"id": "NEX-4", "type": "question", "at": _at(300), "question": "fourth?",
         "accepted": False, "error": "{'error': 'QUERY_RESTRICTED'}"},
        # asked, nothing back yet
        {"id": "NEX-5", "type": "question", "at": _at(400), "question": "fifth?",
         "accepted": True},
    ]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_general_holds_every_question_and_what_happened_to_it(tmp_path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    _write(tmp_path / "nexus.jsonl", _five_questions())

    view = _render().build_rooms()

    assert [r["id"] for r in view["rooms"]][:1] == ["general"]
    thread = view["threads"]["general"]
    assert [(m["kind"], m["id"]) for m in thread] == [
        ("question", "NEX-1"), ("reply", "NEX-1"),
        ("question", "NEX-2"), ("reply", "NEX-2"),
        ("question", "NEX-3"), ("reply", "NEX-3"),
        ("question", "NEX-4"), ("reply", "NEX-4"),
        ("question", "NEX-5"), ("reply", "NEX-5"),
    ], "each reply belongs straight after its own question"
    replies = {m["id"]: m for m in thread if m["kind"] == "reply"}
    assert [replies[q]["outcome"] for q in ("NEX-1", "NEX-2", "NEX-3", "NEX-4",
                                            "NEX-5")] == [
        "answered", "partial", "failed", "refused", "waiting"]
    # Verbatim. Escaping is the page's job and happens once, where it renders;
    # doing it here as well would print &amp;lt; to the operator.
    assert replies["NEX-1"]["text"] == "x" * 400
    assert "QUERY_RESTRICTED" in replies["NEX-4"]["text"]
    assert replies["NEX-5"]["text"] is None, "a question still waiting has no text"
    # Watched from the start: running at 60 s, done at 90 s.
    assert replies["NEX-1"]["seconds"] == 75.0
    assert [m["text"] for m in thread if m["kind"] == "question"][:2] == [
        "first?", "second?"]

    panel = view["panels"]["general"]
    assert (panel["asked"], panel["answered"], panel["partial"], panel["failed"],
            panel["refused"], panel["waiting"]) == (5, 1, 1, 1, 1, 1)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_note_or_a_sample_cannot_move_the_dashboard(tmp_path, monkeypatch):
    """The payload stays still while a note lands -- and the rooms see the note.

    The second half is what makes the first worth anything: a build_rooms that
    ignored the file would keep the payload still too.
    """
    state = tmp_path / "state"
    shutil.copytree(REPO / "state", state, ignore=shutil.ignore_patterns("*.lock"))
    monkeypatch.setenv("QA_STATE_DIR", str(state))
    render = _render()
    before = render.payload_hash(render.build_payload())

    _write(state / "rooms.jsonl", [
        {"type": "operator_note", "id": "N-0001", "room": "general", "at": _at(0),
         "text": "proč ne víc?"}])
    _write(state / "samples.jsonl", [{"type": "tick", "at": _at(0), "ok": True}])

    render = _render()
    assert render.payload_hash(render.build_payload()) == before, (
        "a note or a sample moved the payload, so it would rewrite the committed "
        "dashboard and dirty the tree in the middle of a sweep")
    notes = [m for m in render.build_rooms()["threads"]["general"]
             if m["kind"] == "operator_note"]
    assert [m["text"] for m in notes] == ["proč ne víc?"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_note_reads_as_read_only_up_to_the_mark(tmp_path, monkeypatch):
    """Read is derived from `read` marks, never stored on the note.

    N-0002 was written before the mark but the mark does not reach it: the
    reader marks through the last note it PRINTED, so a note that arrived while
    it was printing stays unread rather than being swallowed.
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    _write(tmp_path / "rooms.jsonl", [
        {"type": "operator_note", "id": "N-0001", "room": "general", "at": _at(0),
         "text": "a"},
        {"type": "operator_note", "id": "N-0002", "room": "general", "at": _at(10),
         "text": "b"},
        {"type": "read", "room": "general", "through": "N-0001", "at": _at(20)},
        {"type": "operator_note", "id": "N-0003", "room": "general", "at": _at(30),
         "text": "c"},
    ])
    view = _render().build_rooms()
    notes = [m for m in view["threads"]["general"] if m["kind"] == "operator_note"]
    assert [(m["id"], m["read"]) for m in notes] == [
        ("N-0001", True), ("N-0002", False), ("N-0003", False)]
    general = next(r for r in view["rooms"] if r["id"] == "general")
    assert general["unread_by_claude"] == 2


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_nexus_answer_reaches_the_page_as_text_never_as_markup(tmp_path, monkeypatch):
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed, so the page cannot be run here")
    if not (REPO / "state" / "ledger.json").exists():
        pytest.skip("no committed ledger, so there is no page to run")
    monkeypatch.delenv("QA_STATE_DIR", raising=False)
    render = _render()
    payload = _live_payload(render)

    hostile = ('<script>alert(1)</script><img src=x onerror=alert(2)> '
               '**bold** and `code`')
    rooms = {
        "rooms": [{"id": "general", "title": "General", "kind": "general"}],
        "threads": {"general": [
            {"kind": "question", "id": "NEX-9", "at": _at(0), "text": "what now?"},
            {"kind": "reply", "id": "NEX-9", "at": _at(120), "text": hostile,
             "outcome": "answered", "seconds": 120.0, "upper": 130.0},
        ]},
        "panels": {"general": {}},
    }
    code, err, captured = _run_page(
        node, tmp_path / "rooms", payload,
        after=f"window.renderRooms({json.dumps(rooms)});")

    assert code == 0, f"the page throws when it renders the rooms:\n{err[:900]}"
    chat = captured.get("roomChat", "")
    assert "what now?" in chat, "the rooms renderer never wrote the thread"
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in chat
    assert "<script" not in chat.lower() and "<img" not in chat.lower(), (
        "a Nexus answer became markup on the page")
    assert "<b>bold</b>" in chat and "<code>code</code>" in chat, (
        "the markdown subset is applied after escaping, and it did not apply")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_tab_reads_no_field_the_rooms_do_not_write(tmp_path, monkeypatch):
    """The payload's field guard, for the shapes that are not in the payload.

    test_the_page_reads_no_field_the_payload_stops_writing holds `f.` and `m.`
    against what the payload carries: JavaScript reading a missing property is
    undefined, not an error, and three visible breakages came from exactly
    that. The rooms arrive by fetch and never pass through that guard, so the
    tab names its own shapes -- `nm.` a message, `nr.` a room, `np.` a panel --
    and this holds each against what build_rooms() actually writes.
    """
    import re

    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    _write(tmp_path / "nexus.jsonl", _five_questions())
    _write(tmp_path / "rooms.jsonl", [
        {"type": "operator_note", "id": "N-0001", "room": "general", "at": _at(5),
         "text": "a"},
        {"type": "claude_note", "id": "N-0002", "room": "general", "at": _at(6),
         "text": "b", "re": "NEX-1"},
    ])
    render = _render()
    view = render.build_rooms()
    written = {
        "nm": {k for thread in view["threads"].values() for m in thread for k in m},
        "nr": {k for r in view["rooms"] for k in r},
        "np": {k for p in view["panels"].values() for k in p},
    }
    for name, keys in written.items():
        read = set(re.findall(rf"\b{name}\.([a-z_]+)\b", render.TEMPLATE))
        assert read, f"the tab reads no `{name}.` field at all, so this proves nothing"
        missing = sorted(read - keys)
        assert not missing, (
            f"the Nexus tab reads `{name}.` fields build_rooms() never writes, "
            f"and they would render as undefined: {missing}")

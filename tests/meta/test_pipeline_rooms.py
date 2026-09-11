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


# ---------------------------------------------------------------------------
# P2: the operator's notes, and how the next session hears about them
# ---------------------------------------------------------------------------
HOOK = REPO / ".claude" / "hooks" / "room_notes.py"


def _run(args, state_dir: Path, encoding: str = "utf-8"):
    """The CLI or the hook as the operator's machine runs it."""
    import os
    import subprocess
    import sys

    env = dict(os.environ, QA_STATE_DIR=str(state_dir), PYTHONIOENCODING=encoding)
    return subprocess.run([sys.executable, *args], cwd=str(REPO), env=env,
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=120)


def _stored(state_dir: Path) -> list[dict]:
    target = state_dir / "rooms.jsonl"
    if not target.exists():
        return []
    return [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def _note(nid: str, text: str, room: str = "general", seconds: float = 0,
          kind: str = "operator_note", **more) -> dict:
    return {"type": kind, "id": nid, "room": room, "at": _at(seconds), "text": text,
            **more}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_unread_prints_the_notes_then_marks_through_the_last_it_printed(tmp_path):
    """On the operator's own console, cp1250, where a Czech note is the norm.

    The mark goes in AFTER the printing and reaches only the last note printed,
    so a note that lands mid-print stays unread. Our own notes are not the
    operator's feedback and are never printed as if they were.
    """
    _write(tmp_path / "rooms.jsonl", [
        _note("N-0001", "Proč ne víc? → zkus 20 %"),
        _note("N-0002", "our summary", kind="claude_note", seconds=5),
        _note("N-0003", "a tohle taky", seconds=10),
    ])
    first = _run(["scripts/rooms.py", "unread"], tmp_path, encoding="cp1250")
    assert first.returncode == 0, first.stderr
    assert "N-0001" in first.stdout and "N-0003" in first.stdout
    assert "Proč ne víc?" in first.stdout, "the note's own words must reach the session"
    assert "our summary" not in first.stdout
    marks = [r for r in _stored(tmp_path) if r["type"] == "read"]
    assert [(m["room"], m["through"]) for m in marks] == [("general", "N-0003")]

    again = _run(["scripts/rooms.py", "unread"], tmp_path)
    assert again.returncode == 0 and "N-0001" not in again.stdout
    assert "nothing" in again.stdout.lower()
    assert len([r for r in _stored(tmp_path) if r["type"] == "read"]) == 1, (
        "reading nothing wrote a mark anyway")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_our_note_is_written_by_the_cli_and_never_waits_on_us(tmp_path, monkeypatch):
    proc = _run(["scripts/rooms.py", "note", "general", "Shrnutí: doporučil BCH",
                 "--re", "NEX-0016"], tmp_path)
    assert proc.returncode == 0, proc.stderr
    rows = _stored(tmp_path)
    assert [(r["type"], r["room"], r.get("re"), r["text"]) for r in rows] == [
        ("claude_note", "general", "NEX-0016", "Shrnutí: doporučil BCH")]

    refused = _run(["scripts/rooms.py", "note", "STR-9999", "x"], tmp_path)
    assert refused.returncode != 0 and len(_stored(tmp_path)) == 1, (
        "a note to a room that does not exist was written anyway")

    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa import rooms

    assert rooms.unread(rooms.load()) == [], "our own note came back as feedback"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_hook_counts_unread_notes_in_one_line_and_is_silent_at_zero(tmp_path):
    """Ids and counts, never the words.

    The memory `a-mechanism-the-operator-must-run-is-not-a-mechanism` is both
    halves: a session must KNOW a note is waiting without anyone running a
    command, and it must not be handed the notes' text unasked.
    """
    silent = _run([str(HOOK)], tmp_path)
    assert silent.returncode == 0 and silent.stdout.strip() == ""

    _write(tmp_path / "rooms.jsonl", [
        _note("N-0001", "first words"),
        _note("N-0002", "second words", seconds=1),
        _note("N-0003", "third words", room="STR-0004", seconds=2),
        {"type": "read", "room": "general", "through": "N-0001", "at": _at(3)},
    ])
    said = _run([str(HOOK)], tmp_path)
    assert said.returncode == 0, said.stderr
    lines = [line for line in said.stdout.splitlines() if line.strip()]
    assert len(lines) == 1, said.stdout
    assert "2" in lines[0] and "general: 1" in lines[0] and "STR-0004: 1" in lines[0]
    assert "rooms.py unread" in lines[0]
    assert "words" not in lines[0], "the hook put the notes' text into context"

    _write(tmp_path / "rooms.jsonl", [
        _note("N-0001", "x"),
        {"type": "read", "room": "general", "through": "N-0001", "at": _at(3)}])
    assert _run([str(HOOK)], tmp_path).stdout.strip() == ""


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_room_hook_never_fails_a_session(tmp_path):
    missing = _run([str(HOOK)], tmp_path / "nothing-here")
    assert missing.returncode == 0 and missing.stdout.strip() == ""

    (tmp_path / "rooms.jsonl").write_bytes(b'{"type":"operator_note","id":"N-00\xff\xfe')
    broken = _run([str(HOOK)], tmp_path)
    assert broken.returncode == 0, broken.stderr
    assert "Traceback" not in broken.stderr


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_rooms_are_a_fourth_channel_and_it_waits_on_us(tmp_path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    _write(tmp_path / "rooms.jsonl", [_note("N-0001", "hello")])
    from qa import channels

    state = channels.state(events=[])
    assert state["rooms"]["unanswered"] == ["N-0001"]
    assert state["rooms"]["waiting_on"] == "us"

    printed = _run(["scripts/channels.py", "status", "--offline"], tmp_path)
    assert printed.returncode == 0, printed.stderr
    assert "ROOMS" in printed.stdout and "N-0001" in printed.stdout


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_watch_names_a_new_note_from_the_operator_once():
    from qa import channels

    rows = [_note("N-0001", "hello there"), _note("N-0002", "ours", kind="claude_note")]
    lines, seen = channels.room_lines(rows, set())
    assert len(lines) == 1 and "N-0001" in lines[0] and "general" in lines[0]
    assert channels.room_lines(rows, seen)[0] == [], "the same note woke the chat twice"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_page_sends_a_note_the_way_the_server_takes_one(tmp_path, monkeypatch):
    """The two halves of the write path, held against each other.

    Every door in test_pipeline_room_notes.py is the server's, and nothing
    there runs the page. A header renamed on one side, or a body with a third
    key, would leave every server test green and every note the operator sends
    bouncing with a 403 or a 400. On 2026-09-11 the loop was walked end to end
    over HTTP, but the Browser pane could not click while its window was
    behind another, so the page's half went unexercised -- this is that half.
    The page's own nxPost runs over a stub fetch, and what it sends is compared
    with what serve.py accepts, read out of serve.py rather than retyped here.
    """
    import importlib.util

    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed, so the page cannot be run here")
    if not (REPO / "state" / "ledger.json").exists():
        pytest.skip("no committed ledger, so there is no page to run")
    spec = importlib.util.spec_from_file_location(
        "serve_contract", REPO / "scripts" / "serve.py")
    serve = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(serve)

    monkeypatch.delenv("QA_STATE_DIR", raising=False)
    render = _render()
    payload = _live_payload(render)
    after = """
const calls = [];
globalThis.fetch = (url, opts) => {
  calls.push({ url: url, opts: opts || {} });
  const body = url === "/token" ? { token: "T-123" } : { id: "N-0001", at: "x" };
  return Promise.resolve({ ok: true, status: url === "/token" ? 200 : 201,
                           json: () => Promise.resolve(body) });
};
window.nxPost("general", "proč ne víc?").then(
  () => { document.getElementById("__calls").innerHTML = JSON.stringify(calls); },
  e => { document.getElementById("__calls").innerHTML = "ERR " + e.message; });
"""
    code, err, captured = _run_page(node, tmp_path / "send", payload, after=after)
    assert code == 0, f"the page's send path throws:\n{err[:900]}"
    raw = captured.get("__calls", "")
    assert raw and not raw.startswith("ERR"), f"nxPost did not complete: {raw!r}"
    calls = json.loads(raw)
    assert [c["url"] for c in calls] == ["/token", "/notes"], (
        "the page must ask for the token at the moment of sending, then post")
    post = calls[1]["opts"]
    assert post["method"] == "POST"
    headers = post["headers"]
    assert headers.get(serve.TOKEN_HEADER) == "T-123", (
        f"the page sends its token under a header serve.py does not read: {headers}")
    assert headers.get("Content-Type") == "application/json"
    assert set(json.loads(post["body"])) == {"room", "text"}, (
        "serve.py takes exactly {room, text} and refuses anything else with a 400")

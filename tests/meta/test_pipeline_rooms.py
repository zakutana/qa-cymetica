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
    was asked", which is the easiest thing to get wrong. A question that
    belongs to a strategy room is read there, and General keeps a pointer to
    it, so General still names every one.
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
from tests.meta.test_pipeline_render import (REPO, _lab_page, _live_payload,
                                             _render)
from tests.meta.test_pipeline_render import _run_page as _run_any_page


def _run_page(*args, **kwargs):
    """The rooms are drawn by the laboratory's page, /lab, since V4."""
    return _run_any_page(*args, page=_lab_page(), **kwargs)

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

    view = _lab_page().build_rooms()

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
    # The committed state, which the rooms' two files are not: they are
    # gitignored, and this machine's are not what the test is about.
    shutil.copytree(REPO / "state", state, ignore=shutil.ignore_patterns(
        "*.lock", "rooms.jsonl", "samples.jsonl"))
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
    notes = [m for m in _lab_page().build_rooms()["threads"]["general"]
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
    view = _lab_page().build_rooms()
    notes = [m for m in view["threads"]["general"] if m["kind"] == "operator_note"]
    assert [(m["id"], m["read"]) for m in notes] == [
        ("N-0001", True), ("N-0002", False), ("N-0003", False)]
    general = next(r for r in view["rooms"] if r["id"] == "general")
    assert general["unread_by_claude"] == 2


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_note_can_go_to_a_sector_room_but_a_question_cannot(tmp_path, monkeypatch):
    """The operator, 2026-09-23: one room per sector -- Karty, Boti,
    Memecoiny, Fondy. A note written in one lands in that room and is read
    back there. A question to Nexus still belongs to an experiment or to
    General: "in the cards room" names nothing he could answer about."""
    rooms = _rooms_at(tmp_path, monkeypatch)
    row = rooms.add_operator_note("cards", "proč tolik červené?")
    assert row["room"] == "cards"
    view = _lab_page().build_rooms()
    assert [m["text"] for m in view["threads"]["cards"]] == ["proč tolik červené?"]
    assert not [m for m in view["threads"]["general"]
                if m.get("text") == "proč tolik červené?"], "it fell into General"
    with pytest.raises(rooms.RoomError):
        rooms.add_operator_note("cardz", "a room nobody opened")

    mod = _nexus_module(tmp_path, monkeypatch)

    def tripwire():
        raise AssertionError("the client was built for a question to a sector")

    monkeypatch.setattr(mod, "_client", tripwire)
    with pytest.raises(rooms.RoomError):
        mod.ask("and the stop?", wait=False, room="cards")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_stopped_room_says_why_and_steps_out_of_the_way(tmp_path, monkeypatch):
    """[N-0049, N-0050, 2026-09-22] "proč taková místnost tady existuje, to je
    očividně failed pokus, má se smazat" and "proč tu nevidím žádnou hlášku?
    jen víc musím rozkliknout". A room is a record and is not deleted; a
    stopped one leaves the strip for a folded "Ukončené" group, and its
    reason is on its own card and row, not only inside its thread."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    _write(tmp_path / "rooms.jsonl", [
        {"type": "strategy", "id": "STR-0001", "origin": "NEX-1", "title": "A",
         "at": _at(1)},
        {"type": "status", "room": "STR-0001", "status": "running", "why": "bought",
         "at": _at(2)},
        {"type": "status", "room": "STR-0001", "status": "stopped",
         "why": "Nexus ruled it out", "at": _at(3)},
        {"type": "strategy", "id": "STR-0002", "origin": "NEX-2", "title": "B",
         "at": _at(4)},
        {"type": "status", "room": "STR-0002", "status": "running", "why": "bought",
         "at": _at(5)},
    ])
    render = _render()
    rooms = {r["id"]: r for r in _lab_page().build_rooms()["rooms"]}
    assert rooms["STR-0001"]["why"] == "Nexus ruled it out"
    assert rooms["STR-0002"]["why"] == "bought"
    # The page half -- a stopped room out of the ranking, into a folded
    # archive, with a few words of reason on its own row -- is held against
    # /lab in test_pipeline_lab_page.py::test_the_archive_and_the_judged_are_
    # one_click_away_with_their_reason.


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_tab_reads_no_field_the_rooms_do_not_write(tmp_path, monkeypatch):
    """The payload's field guard, for the shapes that are not in the payload.

    test_the_page_reads_no_field_the_payload_stops_writing holds `f.` and `m.`
    against what the payload carries: JavaScript reading a missing property is
    undefined, not an error, and three visible breakages came from exactly
    that. The rooms never pass through that guard, so the page names its own
    shape for a message of a thread -- `nm.` -- and this holds it against what
    build_rooms() actually writes. (It named nine shapes while the rooms were
    a tab of their own; /lab reads the rest through lab_view().)
    """
    import re

    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    # One of everything the tab draws: a strategy room with a trade, its close
    # and a bot that was sampled, a follow-up asked inside the room, a status,
    # a summary drawn inside its answer -- and one note of ours left standing
    # on its own, because it names no question on record, so `nm.re` is
    # written by something.
    _write(tmp_path / "nexus.jsonl", [
        *_five_questions(), *_answered("NEX-6", 600, "and the stop?", room="STR-0001")])
    _write(tmp_path / "paper.jsonl", [
        *_buy("TRD-0001", 700, "NEX-1"), *_close("TRD-0002", 800, "P-1", 0.5),
        _snapshot("TRD-0002", 805)])
    _write(tmp_path / "clones.jsonl", _bot_rows())
    _write(tmp_path / "samples.jsonl", _sampled_rows())
    _write(tmp_path / "rooms.jsonl", [
        {"type": "strategy", "id": "STR-0001", "origin": "NEX-1", "title": "A",
         "at": _at(650)},
        {"type": "status", "room": "STR-0001", "status": "running", "why": "bought",
         "at": _at(900)},
        {"type": "operator_note", "id": "N-0001", "room": "general", "at": _at(5),
         "text": "a"},
        {"type": "claude_note", "id": "N-0002", "room": "general", "at": _at(6),
         "text": "b", "re": "NEX-9"},
        {"type": "claude_note", "id": "N-0003", "room": "general", "at": _at(7),
         "text": "c", "re": "NEX-1", "gist": True},
    ])
    view = _lab_page().build_rooms()
    # Since /lab became four sector rooms (2026-09-23) the page reads the
    # rooms' panels through lab_view() -- held in test_pipeline_lab_page.py --
    # and only the thread's messages directly, in the conversation drawer.
    written = {
        "nm": {k for thread in view["threads"].values() for m in thread for k in m},
    }
    for name, keys in written.items():
        # Any identifier, camelCase included: `[a-z_]+` then `\b` could not
        # match `np.samplerOk` at all, so a camelCase read that renders
        # undefined was never compared (P13, deep pass of 2026-09-11).
        read = set(re.findall(rf"\b{name}\.([A-Za-z_][A-Za-z0-9_]*)", _lab_page().TEMPLATE))
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


# ---------------------------------------------------------------------------
# P3: a room per strategy Nexus proposed, and everything done about it
# ---------------------------------------------------------------------------
WHOLE = "y" * 400
INSTANCE = "inst-0001"


def _answered(qid: str, seconds: float, question: str = "which cards?",
              **more) -> list[dict]:
    """A question and a whole answer -- the only thing a room opens from."""
    return [{"id": qid, "type": "question", "at": _at(seconds), "question": question,
             "accepted": True, **more},
            {"id": qid, "type": "answer", "text": WHOLE, "at": _at(seconds + 60)}]


def _buy(tid: str, seconds: float, nexus_id, usdc: float = 10.0,
         position: str = "P-1", outcome: str = "accepted",
         card: str = "card-a-1111") -> list[dict]:
    """A paper buy the way scripts/paper.py records one: intent, then outcome."""
    rows = [{"id": tid, "type": "intent", "at": _at(seconds), "card_id": card,
             "usdc": usdc, "paper": True, "nexus": {"id": nexus_id}}]
    if outcome == "accepted":
        response = json.dumps({"position_id": position, "side": "bull",
                               "notional_usdc": usdc, "entry_index": 92.28})
        rows.append({"id": tid, "type": "outcome", "at": _at(seconds + 1),
                     "outcome": "accepted", "http_status": 200,
                     "position_id": position, "response": response})
    else:
        rows.append({"id": tid, "type": "outcome", "at": _at(seconds + 1),
                     "outcome": outcome, "http_status": 400})
    return rows


def _close(tid: str, seconds: float, position: str, realized: float) -> list[dict]:
    return [{"id": tid, "type": "intent", "at": _at(seconds), "kind": "close",
             "card_id": "card-a-1111", "position_id": position, "paper": True},
            {"id": tid, "type": "outcome", "at": _at(seconds + 1), "kind": "close",
             "outcome": "accepted", "http_status": 200, "realized_pnl_usdc": realized}]


def _snapshot(tid: str, seconds: float) -> dict:
    """The paper account as the last order of ours read it afterwards."""
    return {"id": tid, "type": "after", "at": _at(seconds),
            "sim_balance_usdc": "89000.96", "notional_usdc": 12904.0,
            "sim_total_trades": 4, "sim_total_pnl": "-0.04"}


def _sample(seconds: float, balance: float, pnl: float, trades: int, trading: bool,
            instance: str = INSTANCE) -> dict:
    return {"id": "SAMPLE", "type": "sample", "kind": "sample", "at": _at(seconds),
            "instance_id": instance, "is_trading": trading, "is_paper": True,
            "balance_usdc": balance, "total_profit_usdc": pnl,
            "trades_executed": trades, "win_rate": 0.0}


def _bot_rows() -> list[dict]:
    """The clone that followed NEX-0010, in miniature.

    Refused by our own guard once, then cloned, funded twice -- one of them a
    401 -- switched on, and sampled until it stopped itself. Last, one
    operation on a bot no answer of ours opened.
    """
    made = json.dumps({"id": INSTANCE, "source_name": "Perceptron Oracle",
                       "source_symbol": "PCPN", "name": "QA Perceptron paper",
                       "strategy_type": "neural_ensemble", "risk_profile": "medium",
                       "is_paper": True})
    return [
        {"id": "CLN-0001", "type": "intent", "at": _at(1000), "source_type": "wta_species",
         "custom_name": "QA Perceptron paper", "paper": True, "nexus": {"id": "NEX-1"}},
        {"id": "CLN-0001", "type": "outcome", "at": _at(1001), "outcome": "not_sent",
         "error": "SafetyViolation: MUTATE against unlisted host"},
        {"id": "CLN-0002", "type": "intent", "at": _at(1100), "source_type": "wta_species",
         "custom_name": "QA Perceptron paper", "paper": True, "nexus": {"id": "NEX-1"}},
        {"id": "CLN-0002", "type": "outcome", "at": _at(1101), "outcome": "accepted",
         "http_status": 200, "clone_instance_id": INSTANCE, "is_paper": True,
         "is_trading": False, "response": made},
        {"id": "CLN-0003", "type": "intent", "at": _at(1200), "kind": "fund",
         "instance_id": INSTANCE, "amount": 1.0},
        {"id": "CLN-0003", "type": "outcome", "at": _at(1201), "kind": "fund",
         "outcome": "rejected", "http_status": 401},
        {"id": "CLN-0004", "type": "intent", "at": _at(1300), "kind": "fund",
         "instance_id": INSTANCE, "amount": 999.0},
        {"id": "CLN-0004", "type": "outcome", "at": _at(1301), "kind": "fund",
         "outcome": "accepted", "http_status": 200,
         "response": json.dumps({"success": True, "bot_balance": 999.0})},
        {"id": "CLN-0005", "type": "intent", "at": _at(1400), "kind": "enable",
         "instance_id": INSTANCE},
        {"id": "CLN-0005", "type": "outcome", "at": _at(1401), "kind": "enable",
         "outcome": "accepted", "http_status": 200},
        _sample(1500, 999.0, 0.0, 0, True),
        _sample(2100, 950.0, 0.0, 2, True),
        _sample(2700, 950.0, -49.0, 2, False),
        _sample(2800, 5.0, 0.0, 0, True, instance="inst-other"),
        {"id": "CLN-0006", "type": "intent", "at": _at(2900), "kind": "fund",
         "instance_id": "inst-other", "amount": 5.0},
        {"id": "CLN-0006", "type": "outcome", "at": _at(2901), "kind": "fund",
         "outcome": "accepted", "http_status": 200},
    ]


def _sampled_rows() -> list[dict]:
    """One of each row the console's sampler writes, for the bot of _bot_rows()
    and the position P-1 on card-a-1111 -- scripts/sampler.py is the writer."""
    return [
        {"type": "tick", "at": _at(950), "every": 600, "ok": True,
         "reads": {"bots": "ok"}},
        {"type": "sample", "kind": "bot", "at": _at(950), "instance_id": INSTANCE,
         "is_trading": True, "is_paper": True, "balance_usdc": 950.0,
         "total_profit_usdc": -50.0, "trades_executed": 2, "win_rate": 0.0,
         "locked_usdc": 0.0, "available_usdc": 550.0},
        {"type": "config", "at": _at(950), "instance_id": INSTANCE,
         "strategy_type": "neural_ensemble", "risk_profile": "medium",
         "primary_indicators": [{"name": "rsi", "params": {"period": 14}}],
         "secondary_indicators": [{"name": "atr", "params": {"period": 14}}]},
        {"type": "trade", "at": _at(950), "instance_id": INSTANCE, "trade_id": "T-1",
         "symbol": "ETH", "side": "sell", "trade_type": "wta", "amount_usdc": "25",
         "profit_usdc": None, "is_closed": False, "exit_reason": None,
         "executed_at": _at(940), "closed_at": None},
        {"type": "sample", "kind": "position", "at": _at(950), "position_id": "P-1",
         "card_id": "card-a-1111", "status": "open", "current_index": 93.0,
         "current_value_usdc": 10.08, "unrealized_pnl_usdc": 0.08,
         "realized_pnl_usdc": 0.0},
        {"type": "index", "at": _at(950), "card_id": "card-a-1111",
         "points": [[_at(900), 92.0], [_at(950), 93.0]]},
    ]


def _rooms_at(state_dir: Path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(state_dir))
    from qa import rooms

    return rooms


def _legs(view: dict, room: str) -> list[str]:
    return [m["id"] for m in view["threads"][room] if m["kind"] == "leg"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_room_opens_only_from_a_whole_answer_and_only_once(tmp_path, monkeypatch):
    """CLAUDE.md, the operator's words of 2026-09-10: Nexus supplies the
    guidance, we test and execute.

    A room is where one of its proposals is followed, so a room opens from a
    whole answer and from nothing else: not from a question cut short, given
    up on, refused or still waiting, and not from an id nobody asked. Without
    a card, one answer opens one room, so an order that acts on it has exactly
    one room to go to; with cards (since 2026-09-21) it opens one room per
    card, which test_one_answer_opens_one_room_per_card_and_each_card_once
    holds.
    """
    rooms = _rooms_at(tmp_path, monkeypatch)
    _write(tmp_path / "nexus.jsonl", [*_five_questions(), *_answered("NEX-6", 600)])

    for origin in ("NEX-2", "NEX-3", "NEX-4", "NEX-5", "NEX-404"):
        with pytest.raises(rooms.RoomError):
            rooms.open_strategy(origin, "a strategy")
    with pytest.raises(rooms.RoomError):
        rooms.open_strategy("NEX-1", "   ")
    assert not (tmp_path / "rooms.jsonl").exists(), "a refused room was written anyway"

    first = rooms.open_strategy("NEX-1", "Karta A")
    assert (first["id"], first["origin"], first["title"]) == ("STR-0001", "NEX-1", "Karta A")
    with pytest.raises(rooms.RoomError):
        rooms.open_strategy("NEX-1", "the same answer again")

    made = _run(["scripts/rooms.py", "open", "--from", "NEX-6", "--title", "Kniha B"],
                tmp_path)
    assert made.returncode == 0 and "STR-0002" in made.stdout, made.stderr
    refused = _run(["scripts/rooms.py", "open", "--from", "NEX-2", "--title", "x"],
                   tmp_path)
    assert refused.returncode == 2
    assert [r["id"] for r in _stored(tmp_path) if r["type"] == "strategy"] == [
        "STR-0001", "STR-0002"]

    # an opened room is a room: the operator can write into it
    assert rooms.add_operator_note("STR-0002", "proč jen 10 %?")["room"] == "STR-0002"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_one_answer_opens_one_room_per_card_and_each_card_once(tmp_path, monkeypatch):
    """2026-09-21: an answer naming five cards is five strategies, and it used
    to open one room holding them all -- or, since the day cap was per answer,
    one room a day. A room per card keeps every order drawable in exactly one
    room, now keyed by the answer AND the card it bought."""
    rooms = _rooms_at(tmp_path, monkeypatch)
    _write(tmp_path / "nexus.jsonl", [*_five_questions()])

    a = rooms.open_strategy("NEX-1", "Karta A", card="aaaaaaaa-0000")
    b = rooms.open_strategy("NEX-1", "Karta B", card="bbbbbbbb-0000")
    assert (a["id"], b["id"]) == ("STR-0001", "STR-0002")
    assert (a["card"], b["card"]) == ("aaaaaaaa-0000", "bbbbbbbb-0000")
    with pytest.raises(rooms.RoomError):
        rooms.open_strategy("NEX-1", "A again", card="aaaaaaaa-0000")
    with pytest.raises(rooms.RoomError):
        rooms.open_strategy("NEX-1", "the whole answer, on top of its cards")
    view = _lab_page().build_rooms()
    assert [(r["id"], r["kind"], r["status"]) for r in view["rooms"]] == [
        ("general", "general", None), ("STR-0001", "strategy", "proposed"),
        ("STR-0002", "strategy", "proposed")]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_newest_status_wins_and_every_change_says_why(tmp_path, monkeypatch):
    rooms = _rooms_at(tmp_path, monkeypatch)
    _write(tmp_path / "nexus.jsonl", _answered("NEX-1", 0))
    rooms.open_strategy("NEX-1", "Karta A")
    before = len(_stored(tmp_path))
    for room, status, why in (("STR-0001", "moon", "x"), ("STR-0001", "running", "  "),
                              ("general", "running", "x"), ("STR-0404", "running", "x")):
        with pytest.raises(rooms.RoomError):
            rooms.set_status(room, status, why)
    assert len(_stored(tmp_path)) == before, "a refused status was written anyway"

    # Since 2026-09-12 a room may only start running once somebody has written
    # down what would count as success -- the laboratory's preregistration.
    # Refused above for the same reason the four cases before it are.
    rooms.set_acceptance("STR-0001", window_days=7, stop_pct=5.0,
                         why="his own stop over his own horizon")
    rooms.set_status("STR-0001", "running", "TRD-0001 bought 10 000 USDC")
    rooms.set_status("STR-0001", "paused", "the bot stopped itself at -5 %")
    view = _lab_page().build_rooms()
    room = next(r for r in view["rooms"] if r["id"] == "STR-0001")
    panel = view["panels"]["STR-0001"]
    assert room["status"] == panel["status"] == "paused"
    assert panel["why"] == "the bot stopped itself at -5 %"
    assert [(h["status"], h["why"]) for h in panel["history"]] == [
        ("running", "TRD-0001 bought 10 000 USDC"),
        ("paused", "the bot stopped itself at -5 %")]
    assert [m["status"] for m in view["threads"]["STR-0001"]
            if m["kind"] == "status"] == ["running", "paused"], (
        "the room's own thread does not show how the strategy moved")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_panel_and_the_overview_carry_the_criterion_and_the_verdict(
        tmp_path, monkeypatch):
    """The operator watches the rooms, so the question the laboratory exists to
    answer -- which of his ideas made money -- has to be readable there. Before
    2026-09-12 nothing on the page said it: a room showed a status and a P&L
    and nothing about what it had been accepted on."""
    rooms = _rooms_at(tmp_path, monkeypatch)
    _write(tmp_path / "nexus.jsonl", _answered("NEX-1", 0))
    rooms.open_strategy("NEX-1", "Karta A")
    rooms.set_acceptance("STR-0001", window_days=7, stop_pct=5.0,
                         why="his own stop over his own horizon")
    rooms.set_status("STR-0001", "running", "TRD-0001 bought 10 000 USDC")
    rooms.record_verdict("STR-0001", {
        "verdict": "survived", "why": "it returned +4.20% inside a 1.10% drawdown",
        "return_pct": 4.2, "max_drawdown_pct": 1.1, "benchmark_pct": 2.0,
        "coverage": 1.0, "formula": "abc123"})

    view = _lab_page().build_rooms()
    panel = view["panels"]["STR-0001"]
    assert panel["criterion"]["window_days"] == 7
    assert panel["criterion"]["stop_pct"] == 5.0
    assert panel["criterion"]["at"], (
        "the page says when the verdict comes due by adding the window to this "
        "moment, the same arithmetic qa.lab.verdict does; without it the tile "
        "goes quiet instead of red")
    assert panel["verdict"]["verdict"] == "survived"
    assert panel["verdict"]["return_pct"] == 4.2

    board = view["panels"]["general"]["scoreboard"]
    assert [row["room"] for row in board] == ["STR-0001"]
    assert board[0]["verdict"] == "survived" and board[0]["return_pct"] == 4.2
    listed = next(r for r in view["rooms"] if r["id"] == "STR-0001")
    assert listed["verdict"]["verdict"] == "survived", (
        "the overview's table reads the room rows, not the panels")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_link_names_only_what_is_on_record(tmp_path, monkeypatch):
    rooms = _rooms_at(tmp_path, monkeypatch)
    _write(tmp_path / "nexus.jsonl", [*_answered("NEX-1", 0), *_answered("NEX-7", 300)])
    _write(tmp_path / "paper.jsonl", _buy("TRD-0001", 900, None))
    _write(tmp_path / "clones.jsonl", _bot_rows())
    rooms.open_strategy("NEX-1", "Karta A")
    before = len(_stored(tmp_path))
    for room, ref in (("STR-0001", "TRD-0404"), ("STR-0001", "CLN-0404"),
                      ("STR-0001", "NEX-0404"), ("STR-0001", "SAMPLE"),
                      ("general", "TRD-0001"), ("STR-0404", "TRD-0001")):
        with pytest.raises(rooms.RoomError):
            rooms.add_link(room, ref, "because")
    with pytest.raises(rooms.RoomError):
        rooms.add_link("STR-0001", "TRD-0001", " ")
    assert len(_stored(tmp_path)) == before, "a refused link was written anyway"
    for ref in ("TRD-0001", "CLN-0002", "NEX-7"):
        assert rooms.add_link("STR-0001", ref, "it belongs here")["ref"] == ref


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_trade_finds_its_room_by_the_answer_it_acts_on(tmp_path, monkeypatch):
    """By the Nexus id scripts/paper.py writes on every order.

    A close carries no Nexus id; it follows the order that opened its
    position. A close of a position nothing of ours opened, an order of our
    own, and an order after an answer that opened no room all stay in
    General, each saying which it is: a trade drawn inside a strategy it did
    not come from would be our activity dressed as Nexus's guidance.
    """
    rooms = _rooms_at(tmp_path, monkeypatch)
    _write(tmp_path / "nexus.jsonl", [
        *_answered("NEX-1", 0),
        {"id": "NEX-2", "type": "question", "at": _at(100), "question": "second?",
         "accepted": True},
        {"id": "NEX-2", "type": "answer", "text": "I'll verify first.", "at": _at(160)}])
    _write(tmp_path / "paper.jsonl", [
        *_buy("TRD-0001", 900, "NEX-1", usdc=10.0, position="P-1"),
        *_buy("TRD-0002", 950, None, usdc=1.0, position="P-2"),
        *_close("TRD-0003", 1000, "P-1", 0.5),
        *_close("TRD-0004", 1050, "P-unknown", -0.04),
        *_buy("TRD-0005", 1100, "NEX-2", usdc=1.0, position="P-5"),
        *_buy("TRD-0006", 1150, "NEX-1", usdc=5.0, outcome="rejected")])
    rooms.open_strategy("NEX-1", "Karta A")

    view = _lab_page().build_rooms()
    assert _legs(view, "STR-0001") == ["TRD-0001", "TRD-0003", "TRD-0006"]
    assert _legs(view, "general") == ["TRD-0002", "TRD-0004", "TRD-0005"]
    said = {m["id"]: m["text"] for m in view["threads"]["general"] if m["kind"] == "leg"}
    assert "no order of ours opened" in said["TRD-0004"]
    assert "no Nexus answer" in said["TRD-0002"]
    trades = {t["id"]: t for t in view["panels"]["STR-0001"]["trades"]}
    assert sorted(trades) == ["TRD-0001", "TRD-0006"]
    assert (trades["TRD-0001"]["closed_by"], trades["TRD-0001"]["realized"]) == (
        "TRD-0003", 0.5)
    assert trades["TRD-0006"]["outcome"] == "rejected"
    panel = view["panels"]["STR-0001"]
    assert (panel["staked"], panel["unclosed"], panel["realized"]) == (10.0, 0, 0.5), (
        "a rejected order was counted as money in the strategy")

    rooms.add_link("STR-0001", "TRD-0002", "measured beside this answer")
    view = _lab_page().build_rooms()
    assert _legs(view, "STR-0001") == ["TRD-0001", "TRD-0002", "TRD-0003", "TRD-0006"]
    assert "TRD-0002" not in _legs(view, "general")
    assert view["panels"]["STR-0001"]["unclosed"] == 1


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_two_card_rooms_from_one_answer_each_draw_their_own_trade(tmp_path, monkeypatch):
    """One room per card (2026-09-21): both orders carry the same Nexus id, so
    the answer alone cannot place them -- by origin, both landed in whichever
    room was opened last. The card each order bought decides."""
    rooms = _rooms_at(tmp_path, monkeypatch)
    _write(tmp_path / "nexus.jsonl", [*_answered("NEX-1", 0)])
    _write(tmp_path / "paper.jsonl", [
        *_buy("TRD-0001", 900, "NEX-1", position="P-1", card="card-a-1111"),
        *_buy("TRD-0002", 950, "NEX-1", position="P-2", card="card-b-2222")])
    rooms.open_strategy("NEX-1", "Karta A", card="card-a-1111")
    rooms.open_strategy("NEX-1", "Karta B", card="card-b-2222")

    view = _lab_page().build_rooms()
    assert _legs(view, "STR-0001") == ["TRD-0001"]
    assert _legs(view, "STR-0002") == ["TRD-0002"]

    # R12, deep pass of 2026-09-21 (3/3): a card none of this answer's rooms
    # holds fell back to the answer's LAST room, drawn inside a strategy it
    # did not come from. It stays in General.
    _write(tmp_path / "paper.jsonl", [
        *_buy("TRD-0001", 900, "NEX-1", position="P-1", card="card-a-1111"),
        *_buy("TRD-0002", 950, "NEX-1", position="P-2", card="card-b-2222"),
        *_buy("TRD-0003", 990, "NEX-1", position="P-3", card="card-z-9999")])
    view = _lab_page().build_rooms()
    assert _legs(view, "STR-0002") == ["TRD-0002"]
    assert "TRD-0003" in _legs(view, "general")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_bot_and_everything_done_to_it_follow_its_instance(tmp_path, monkeypatch):
    """A clone carries the Nexus id; what is done to it afterwards carries only
    the bot's instance id -- funding it, switching it on, every sample.

    So those follow the clone's outcome into its room, and a refused attempt
    stays there as history rather than vanishing. The panel's state is the
    newest reading: the bot was switched on at 1400 and a sample at 2700 says
    it had stopped, and the later of the two is the one that is true.
    """
    rooms = _rooms_at(tmp_path, monkeypatch)
    _write(tmp_path / "nexus.jsonl", _answered("NEX-1", 0))
    _write(tmp_path / "clones.jsonl", _bot_rows())
    rooms.open_strategy("NEX-1", "Perceptron Oracle bot")

    view = _lab_page().build_rooms()
    assert _legs(view, "STR-0001") == [
        "CLN-0001", "CLN-0002", "CLN-0003", "CLN-0004", "CLN-0005"]
    assert _legs(view, "general") == ["CLN-0006"]
    legs = {m["id"]: m for m in view["threads"]["STR-0001"] if m["kind"] == "leg"}
    assert legs["CLN-0001"]["outcome"] == "not_sent"
    assert "not sent" in legs["CLN-0001"]["text"]
    assert "401" in legs["CLN-0003"]["text"]

    (bot,) = view["panels"]["STR-0001"]["clones"]
    assert (bot["id"], bot["name"], bot["source"], bot["symbol"]) == (
        "CLN-0002", "QA Perceptron paper", "Perceptron Oracle", "PCPN")
    assert bot["funded"] == 999.0, "a fund the server refused was counted"
    assert (bot["trading"], bot["balance"], bot["pnl"], bot["trades"]) == (
        False, 950.0, -49.0, 2)
    assert [s["balance"] for s in bot["samples"]] == [999.0, 950.0, 950.0]
    assert bot["sampled_at"] == _at(2700)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_question_asked_in_a_room_is_read_there_and_general_points_to_it(
        tmp_path, monkeypatch):
    """General still names every question -- in full, or as a pointer to the
    room that holds it -- so nothing asked goes missing from it. The answer a
    room was opened from is in both: in General, where it was asked, and
    first in the room it opened."""
    rooms = _rooms_at(tmp_path, monkeypatch)
    _write(tmp_path / "nexus.jsonl", [
        *_answered("NEX-1", 0, "which card?"),
        *_answered("NEX-6", 3000, "and the stop?", room="STR-0001"),
        *_answered("NEX-7", 3100, "is this card still live?"),
        *_answered("NEX-8", 3200, "how do I read a balance?")])
    rooms.open_strategy("NEX-1", "Karta A")
    rooms.add_link("STR-0001", "NEX-7", "it asks about this card")

    view = _lab_page().build_rooms()
    assert [(m["kind"], m["id"]) for m in view["threads"]["general"]] == [
        ("question", "NEX-1"), ("reply", "NEX-1"),
        ("pointer", "NEX-6"), ("pointer", "NEX-7"),
        ("question", "NEX-8"), ("reply", "NEX-8")]
    pointers = [m for m in view["threads"]["general"] if m["kind"] == "pointer"]
    assert {(m["room"], m["title"]) for m in pointers} == {("STR-0001", "Karta A")}
    assert view["threads"]["general"][0]["opened"] == ["STR-0001"]
    assert [(m["kind"], m["id"]) for m in view["threads"]["STR-0001"]] == [
        ("question", "NEX-1"), ("reply", "NEX-1"),
        ("question", "NEX-6"), ("reply", "NEX-6"),
        ("question", "NEX-7"), ("reply", "NEX-7")]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_gist_rides_inside_its_answer_wherever_the_answer_is_drawn(
        tmp_path, monkeypatch):
    """Our one-line Czech summary of an English answer, written by the CLI.

    It is drawn inside the answer -- in General and in the room that answer
    opened -- and not as a bubble of its own. A plain note ABOUT an answer is
    not a summary of it and stays a bubble. A second summary replaces the
    first inside the answer, and the first stays on the page as a note:
    nothing written disappears.
    """
    rooms = _rooms_at(tmp_path, monkeypatch)
    _write(tmp_path / "nexus.jsonl", [*_answered("NEX-1", 0), *_answered("NEX-8", 500)])
    rooms.open_strategy("NEX-1", "Karta A")
    with pytest.raises(rooms.RoomError):
        rooms.add_claude_note("general", "no question named", gist=True)
    with pytest.raises(rooms.RoomError):
        rooms.add_claude_note("general", "nobody asked it", about="NEX-404", gist=True)

    rooms.add_claude_note("general", "Doporučil kartu A, bull, 10 %", about="NEX-1",
                          gist=True)
    rooms.add_claude_note("STR-0001", "Proč jsme nevzali víc", about="NEX-1")

    def replies(view, room):
        return {m["id"]: m for m in view["threads"][room] if m["kind"] == "reply"}

    def bubbles(view, room):
        return [m["text"] for m in view["threads"][room] if m["kind"] == "claude_note"]

    view = _lab_page().build_rooms()
    for room in ("general", "STR-0001"):
        assert replies(view, room)["NEX-1"]["gist"] == "Doporučil kartu A, bull, 10 %"
    assert bubbles(view, "general") == [], "the summary was drawn as a bubble as well"
    assert bubbles(view, "STR-0001") == ["Proč jsme nevzali víc"]
    assert replies(view, "general")["NEX-8"]["gist"] is None

    fixed = _run(["scripts/rooms.py", "note", "general", "Oprava: karta A, bull, 5 %",
                  "--re", "NEX-1", "--gist"], tmp_path)
    assert fixed.returncode == 0, fixed.stderr
    view = _lab_page().build_rooms()
    assert replies(view, "STR-0001")["NEX-1"]["gist"] == "Oprava: karta A, bull, 5 %"
    assert bubbles(view, "general") == ["Doporučil kartu A, bull, 10 %"]


def _nexus_module(tmp_path, monkeypatch):
    import importlib.util

    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    spec = importlib.util.spec_from_file_location(
        "nexus_rooms_under_test", REPO / "scripts" / "nexus.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_question_for_a_room_that_does_not_exist_is_never_sent(tmp_path, monkeypatch):
    """--room is checked before the client is even built.

    A negative control must not need the thing it tests: were the check to
    break, `nexus.py ask --room STR-0404` would put a real question to Nexus.
    So the client here is a tripwire, and no path through this test reaches
    the network whichever way the check goes.
    """
    mod = _nexus_module(tmp_path, monkeypatch)
    from qa.rooms import RoomError

    def tripwire():
        raise AssertionError("the client was built for a room that does not exist")

    monkeypatch.setattr(mod, "_client", tripwire)
    monkeypatch.setattr(mod, "printable", lambda: None)
    with pytest.raises(RoomError):
        mod.ask("and the stop?", wait=False, room="STR-0404")
    assert mod.main(["ask", "and the stop?", "--room", "STR-0404", "--no-wait"]) == 2
    assert not (tmp_path / "nexus.jsonl").exists(), "a refused question was written anyway"

    _write(tmp_path / "nexus.jsonl", _answered("NEX-0001", 0))
    _rooms_at(tmp_path, monkeypatch).open_strategy("NEX-0001", "Karta A")

    class Http:
        def close(self):
            pass

    class Client:
        http = Http()

        def call(self, tool, arguments):
            return {"result": {"job_id": "J-1"}}

    monkeypatch.setattr(mod, "_client", lambda: Client())
    mod.ask("and the stop?", wait=False, room="STR-0001")
    asked = [json.loads(line) for line in
             (tmp_path / "nexus.jsonl").read_text(encoding="utf-8").splitlines()
             if line.strip()]
    assert (asked[-1]["type"], asked[-1]["id"], asked[-1]["room"]) == (
        "question", "NEX-0002", "STR-0001")


# ---------------------------------------------------------------------------
# A strategy's name, and Nexus's proposal written down as its plan
# ---------------------------------------------------------------------------
CARD_A = "e579581b-0ad3-463f-8c3d-e80bd2624d40"
CARD_B = "d432f8cd-dc3f-4563-ab44-07e34dbd2a0a"
CARD_C = "f197d20f-db76-431d-a10c-75a538ebe213"


def _card(card: str, seconds: float, basket, closes=None, status="live") -> dict:
    """A card as the sampler describes it: what is in its basket, when it closes."""
    return {"type": "card", "at": _at(seconds), "card_id": card,
            "title": f"card {card[:8]}", "evcdx_symbol": f"EVCDX-{card[:4].upper()}",
            "status": status, "tradeable_now": status == "live",
            "trading_closes_at": closes, "index_base": 100.0,
            "basket": [{"symbol": s, "weight": w} for s, w in basket]}


def _index(card: str, seconds: float, points) -> dict:
    return {"type": "index", "at": _at(seconds), "card_id": card,
            "points": [[_at(t), v] for t, v in points]}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_name_and_a_plan_are_checked_before_anything_is_written(tmp_path, monkeypatch):
    """Clear names for the strategies, and a panel that says at a glance what
    each one holds -- the operator's two asks after the first version.

    A name is ours and short. A plan is Nexus's proposal written down as legs:
    the card by its whole id, because the sampler reads the card by it; the
    side; the share of the bankroll; the take-profit and the stop Nexus gave.
    Each is refused whole before anything is written, and the newest wins.
    """
    rooms = _rooms_at(tmp_path, monkeypatch)
    _write(tmp_path / "nexus.jsonl", _answered("NEX-1", 0))
    rooms.open_strategy("NEX-1", "BTC 20 % + BCH-blend 10 %")
    before = _stored(tmp_path)

    for bad in ("", " ", "x" * 41):
        with pytest.raises(rooms.RoomError):
            rooms.set_title("STR-0001", bad)
    with pytest.raises(rooms.RoomError):
        rooms.set_title("STR-0009", "Nowhere")
    leg = {"card": CARD_A, "side": "bull", "share": 0.1, "tp": 13.0, "sl": -9.0}
    for legs in ([], [dict(leg, card=CARD_A[:8])], [dict(leg, side="long")],
                 [dict(leg, share=0)], [dict(leg, share=1.5)],
                 [dict(leg, tp=-1.0)], [dict(leg, sl=2.0)], [dict(leg, tp="high")],
                 [leg, dict(leg, share=0.2)],
                 [dict(leg, share=0.7), dict(leg, card=CARD_B, share=0.4)],
                 # A good leg beside a bad one is refused whole: every bad case
                 # above was a one-leg list, so a set_plan that dropped bad legs
                 # and wrote the rest passed (P07, deep pass of 2026-09-11).
                 [leg, dict(leg, card=CARD_B, side="long")]):
        with pytest.raises(rooms.RoomError):
            rooms.set_plan("STR-0001", legs)
    with pytest.raises(rooms.RoomError):
        rooms.set_plan("STR-0001", [leg], reserve=0.95)
    with pytest.raises(rooms.RoomError):
        rooms.set_plan("STR-0001", [leg], bankroll=0)
    with pytest.raises(rooms.RoomError):
        rooms.set_plan("STR-0009", [leg])
    assert _stored(tmp_path) == before, "a refused name or plan still wrote something"

    rooms.set_title("STR-0001", "BTC + BCH")
    rooms.set_title("STR-0001", "  BTC +   BCH blend ")
    rooms.set_plan("STR-0001", [dict(leg, card=CARD_B, share=0.3)])
    rooms.set_plan("STR-0001", [dict(leg, card=CARD_B, share=0.2, tp=8.0, sl=-5.0), leg],
                   reserve=0.7, bankroll=100000.0)
    stored = rooms.load()
    assert rooms.names(stored)["STR-0001"] == "BTC + BCH blend"
    plan = rooms.plans(stored)["STR-0001"]
    assert [(g["card"], g["share"], g["tp"], g["sl"]) for g in plan["legs"]] == [
        (CARD_B, 0.2, 8.0, -5.0), (CARD_A, 0.1, 13.0, -9.0)]
    assert (plan["reserve"], plan["bankroll"]) == (0.7, 100000.0)
    (room,) = [r for r in _lab_page().build_rooms()["rooms"] if r["id"] == "STR-0001"]
    assert room["title"] == "BTC + BCH blend", (
        "the tab still names the room by the title it was opened with")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_plan_is_written_from_the_command_line_the_way_nexus_gives_it(tmp_path):
    """`--leg CARD:SIDE:SHARE:tp=N:sl=N`, the share as Nexus says it (20%) or as
    a fraction. A leg that does not parse is refused and nothing is written."""
    _write(tmp_path / "nexus.jsonl", _answered("NEX-1", 0))
    opened = _run(["scripts/rooms.py", "open", "--from", "NEX-1", "--title", "A"],
                  tmp_path)
    assert opened.returncode == 0, opened.stderr
    for leg in (f"{CARD_A}:bull:ten", f"{CARD_A}:bull", f"{CARD_A}:bull:10%:stop=4"):
        bad = _run(["scripts/rooms.py", "plan", "STR-0001", "--leg", leg], tmp_path)
        assert bad.returncode == 2 and "refused" in bad.stderr, (leg, bad.stderr)
    assert not [r for r in _stored(tmp_path) if r["type"] == "plan"]

    made = _run(["scripts/rooms.py", "plan", "STR-0001",
                 "--leg", f"{CARD_B}:bull:20%:tp=8:sl=-5",
                 "--leg", f"{CARD_A}:bull:0.1:tp=13:sl=-9",
                 "--reserve", "70%", "--bankroll", "100000"], tmp_path)
    assert made.returncode == 0, made.stderr
    (plan,) = [r for r in _stored(tmp_path) if r["type"] == "plan"]
    assert [(g["card"], g["side"], g["share"], g["tp"], g["sl"])
            for g in plan["legs"]] == [(CARD_B, "bull", 0.2, 8.0, -5.0),
                                       (CARD_A, "bull", 0.1, 13.0, -9.0)]
    assert (plan["reserve"], plan["bankroll"]) == (0.7, 100000.0)
    # 2026-09-23: NEX-0086 gave a fund +8 % / -6 %, and the command line took a
    # card only, so STR-0041 kept neither. A leg may lead with its kind.
    bot = "d778102d-cf3f-4d86-ad1e-2d8511b345dc"
    kinds = _run(["scripts/rooms.py", "plan", "STR-0001",
                  "--leg", "fund:AIB-SPACE:bull:60%:tp=8:sl=-6",
                  "--leg", f"bot:{bot}:bull:40%"], tmp_path)
    assert kinds.returncode == 0, kinds.stderr
    newest = [r for r in _stored(tmp_path) if r["type"] == "plan"][-1]
    assert [(g["kind"], g["ref"], g["share"], g["tp"], g["sl"])
            for g in newest["legs"]] == [("fund", "AIB-SPACE", 0.6, 8.0, -6.0),
                                         ("bot", bot, 0.4, None, None)]
    assert "card" not in newest["legs"][0]
    for leg in ("fund:not a symbol:bull:10%", "desk:AIB-SPACE:bull:10%",
                "fund:AIB-SPACE:bull"):
        bad = _run(["scripts/rooms.py", "plan", "STR-0001", "--leg", leg], tmp_path)
        assert bad.returncode == 2 and "refused" in bad.stderr, (leg, bad.stderr)
    named = _run(["scripts/rooms.py", "title", "STR-0001", "BTC + BCH blend"], tmp_path)
    assert named.returncode == 0, named.stderr
    listed = _run(["scripts/rooms.py", "list"], tmp_path)
    assert "BTC + BCH blend" in listed.stdout, listed.stdout


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_plan_leg_meets_its_order_its_card_and_where_it_stood_when_proposed(
        tmp_path, monkeypatch):
    """What the panel's configuration table is drawn from.

    A leg that was bought carries its order, its entry, where the index stands,
    and its take-profit and stop as index levels. A leg that was not carries
    how its card moved since Nexus answered -- what would have happened, which
    the page labels as such and never as ours. A card is named by what is in
    its basket, and a leg the sampler has not described yet still shows, from
    the plan alone: that is the page in the first minute after the console
    starts.
    """
    rooms = _rooms_at(tmp_path, monkeypatch)
    _write(tmp_path / "nexus.jsonl", _answered("NEX-1", 0))  # answered at 60 s
    rooms.open_strategy("NEX-1", "A")
    rooms.set_plan("STR-0001", [
        {"card": CARD_B, "side": "bull", "share": 0.2, "tp": 8.0, "sl": -5.0},
        {"card": CARD_A, "side": "bull", "share": 0.1, "tp": 13.0, "sl": -9.0},
        {"card": CARD_C, "side": "bull", "share": 0.05}],
        reserve=0.65, bankroll=100000.0)
    _write(tmp_path / "paper.jsonl", _buy("TRD-0001", 900, "NEX-1", usdc=10000.0,
                                          card=CARD_A))
    _write(tmp_path / "samples.jsonl", [
        _card(CARD_A, 950, [("BCH", 0.685), ("OKB", 0.315)],
              closes="2026-09-12T23:14:22+00:00"),
        _card(CARD_B, 950, [("BTC", 0.996), ("ETH", 0.004)],
              closes="2026-09-12T07:44:00+00:00"),
        _index(CARD_A, 950, [(30, 99.0), (900, 92.3), (950, 92.42)]),
        _index(CARD_B, 950, [(30, 97.0), (60, 97.36), (950, 98.0)]),
        {"type": "sample", "kind": "position", "at": _at(950), "position_id": "P-1",
         "card_id": CARD_A, "status": "open", "current_index": 92.42,
         "current_value_usdc": 10014.48, "unrealized_pnl_usdc": 14.48,
         "realized_pnl_usdc": 0.0},
    ])
    panel = _lab_page().build_rooms()["panels"]["STR-0001"]
    legs = {leg["card"]: leg for leg in panel["legs"]}

    bought = legs[CARD_A]
    assert (bought["state"], bought["orders"], bought["label"]) == (
        "open", ["TRD-0001"], "68 % BCH · 32 % OKB")
    assert (bought["entry"], bought["current"], bought["pnl"]) == (92.28, 92.42, 14.48)
    assert (round(bought["tp_level"], 2), round(bought["sl_level"], 2)) == (104.28, 83.97)
    assert bought["closes_at"] == "2026-09-12T23:14:22+00:00"
    # Their card page, the address their API gives as share_url, so the operator
    # can open the card itself on cymetica.com.
    assert bought["url"] == f"https://cymetica.com/events/{CARD_A}"

    waiting = legs[CARD_B]
    assert (waiting["state"], waiting["orders"], waiting["label"]) == (
        "not bought", [], "BTC"), "a card that is 99.6 % one coin is not named by it"
    assert waiting["usdc_proposed"] == 20000.0
    assert waiting["at_proposal"] == 97.36, (
        "the index a leg moved from is not the one it stood at when Nexus answered")
    assert round(waiting["since_proposal"], 2) == 0.66

    bare = legs[CARD_C]
    assert (bare["state"], bare["label"], bare["closes_at"], bare["since_proposal"]) == (
        "not bought", None, None, None), "a leg the sampler has not described is lost"

    assert (panel["holds"], panel["invested"], panel["pnl"]) == ("cards", 10000.0, 14.48)
    # The countdown is to the card that is held, not to one nobody bought that
    # happens to close first -- with nothing held, to the first proposed one.
    assert panel["closes_at"] == "2026-09-12T23:14:22+00:00", (
        "the panel counts down to a card that is not held")
    assert (panel["proposed_share"], panel["reserve"]) == (0.35, 0.65)


# ---------------------------------------------------------------------------
# The page: a strip of named strategies, the chat beside a panel of numbers
# ---------------------------------------------------------------------------
@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_lab_page_takes_the_whole_screen_and_the_console_keeps_its_column():
    """The console reads best as a column. The rooms are a chat beside a
    dashboard, and on the operator's screen they had a third of the width they
    could have had -- so while they were a tab, showTab widened the page for
    that tab alone. Since V4 they are on a page of their own, /lab, wider than
    the console's column throughout, and the console keeps its column."""
    import re

    lab = _lab_page().TEMPLATE
    assert '<div class="app" id="app">' in lab, "the lab page has no #app"
    widths = re.findall(r'(?m)^\.app\s*\{[^}]*max-width\s*:\s*(\d+)px', lab)
    console = _render().TEMPLATE
    column = re.search(r'\.wrap\s*\{[^}]*max-width\s*:\s*(\d+)px', console)
    assert column, "the console's own width is gone"
    assert widths and int(widths[-1]) >= int(column.group(1)) + 200, (
        "/lab is no wider than the console's column, so the ranking and its "
        "numbers get squeezed the way the rooms once were")
    assert "max-width:none" not in "".join(
        re.findall(r'(?m)^\.wrap[^{]*\{([^}]*)\}', console)).replace(" ", ""), (
        "something in the console still widens it to the whole screen")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_status_of_reads_the_newest_row_and_nothing_for_a_proposed_room():
    from qa import rooms

    assert rooms.status_of([], "STR-0001") is None, (
        "a room nobody has moved out of proposed writes no status row at all")
    moved = [
        {"type": "status", "room": "STR-0001", "status": "running", "at": "t1"},
        {"type": "status", "room": "STR-0002", "status": "running", "at": "t1"},
        {"type": "status", "room": "STR-0001", "status": "paused", "at": "t2"},
    ]
    assert rooms.status_of(moved, "STR-0001") == "paused"
    assert rooms.status_of(moved, "STR-0002") == "running"


# ---------------------------------------------------------------------------
# 2026-09-22: a room holds a card, a paper bot or a marked fund
# ---------------------------------------------------------------------------


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_leg_names_its_kind_and_an_old_card_leg_reads_as_a_card(
        tmp_path, monkeypatch):
    """The operator, 2026-09-22: everything that runs on paper, not only
    cards. A leg is a kind -- card, bot, fund -- and the thing it names, its
    `ref`. A leg written the old way, with `card` alone, IS a card leg: it is
    stored with the same card field every reader already reads, and a row
    already on disk that has no kind is read as one without being rewritten."""
    rooms = _rooms_at(tmp_path, monkeypatch)
    _write(tmp_path / "nexus.jsonl", _answered("NEX-1", 0))
    rooms.open_strategy("NEX-1", "mixed")

    old = {"card": CARD_A, "side": "bull", "share": 0.1, "tp": 13.0, "sl": -9.0}
    plan = rooms.set_plan("STR-0001", [
        old,
        {"kind": "bot", "ref": "inst-7", "side": "bull", "share": 0.2},
        {"kind": "fund", "ref": "AIB-SPACE", "side": "bull", "share": 0.3}])
    card, bot, fund = plan["legs"]
    assert (card["card"], card["kind"], card["ref"]) == (CARD_A, "card", CARD_A)
    assert (card["share"], card["tp"], card["sl"]) == (0.1, 13.0, -9.0)
    assert (bot["kind"], bot["ref"]) == ("bot", "inst-7") and "card" not in bot
    assert (fund["kind"], fund["ref"]) == ("fund", "AIB-SPACE") and "card" not in fund

    # A leg on disk from before: no kind, no ref. Read, not rewritten.
    assert rooms.leg_kind({"card": CARD_B, "side": "bull"}) == "card"
    assert rooms.leg_ref({"card": CARD_B, "side": "bull"}) == CARD_B
    assert rooms.leg_ref(bot) == "inst-7" and rooms.leg_kind(fund) == "fund"

    before = _stored(tmp_path)
    leg = {"kind": "bot", "ref": "inst-7", "side": "bull", "share": 0.2}
    for legs in ([dict(leg, kind="stock")], [dict(leg, ref="")],
                 [dict(leg, kind="card", ref=CARD_A[:8])],
                 [dict(leg, kind="fund", ref="aib space")],
                 [leg, dict(leg, share=0.1)]):
        with pytest.raises(rooms.RoomError):
            rooms.set_plan("STR-0001", legs)
    assert _stored(tmp_path) == before, "a refused leg still wrote something"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_arena_leg_names_a_team(tmp_path, monkeypatch):
    """The fourth paper product (NEXT.md, 2026-09-22): place_arena_order takes
    `team_symbol: enum [BLUE, RED]` and trades on paper with `mode: paper`.
    Its leg names the team the way their schema does -- upper case, one of
    two -- and nothing else is a team."""
    rooms = _rooms_at(tmp_path, monkeypatch)
    _write(tmp_path / "nexus.jsonl", _answered("NEX-1", 0))
    rooms.open_strategy("NEX-1", "Arena")

    plan = rooms.set_plan("STR-0001", [
        {"kind": "arena", "ref": "blue", "side": "bull", "share": 0.1}])
    (leg,) = plan["legs"]
    assert (leg["kind"], leg["ref"]) == ("arena", "BLUE") and "card" not in leg
    # B07, deep pass of 2026-09-22 evening (3/3): one of TWO -- narrowing the
    # teams to BLUE alone stayed green.
    plan = rooms.set_plan("STR-0001", [
        {"kind": "arena", "ref": "red", "side": "bear", "share": 0.1}])
    assert [(g["kind"], g["ref"]) for g in plan["legs"]] == [("arena", "RED")]

    before = _stored(tmp_path)
    for ref in ("GREEN", "", "BLUE-RED", CARD_A):
        with pytest.raises(rooms.RoomError):
            rooms.set_plan("STR-0001", [
                {"kind": "arena", "ref": ref, "side": "bull", "share": 0.1}])
    assert _stored(tmp_path) == before, "a refused leg still wrote something"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_bot_or_fund_room_is_one_thing_of_its_answer_not_the_whole_answer(
        tmp_path, monkeypatch):
    """A room with no `card` used to mean a WHOLE-ANSWER room -- in
    open_strategy, in the launcher and on the page. A bot room has no card,
    and read that way it would refuse the answer's cards and swallow every
    order the answer made. It is keyed by its kind and ref instead."""
    rooms = _rooms_at(tmp_path, monkeypatch)
    _write(tmp_path / "nexus.jsonl", [*_answered("NEX-1", 0)])
    _write(tmp_path / "paper.jsonl", [
        *_buy("TRD-0001", 900, "NEX-1", position="P-1", card="card-a-1111"),
        *_buy("TRD-0002", 950, "NEX-1", position="P-2", card="card-z-9999")])

    bot = rooms.open_strategy("NEX-1", "MACD Hunter", kind="bot",
                              ref="dd206f68-048f-4325-9f33-4ca77e40bbeb")
    card = rooms.open_strategy("NEX-1", "Karta A", card="card-a-1111")
    fund = rooms.open_strategy("NEX-1", "AIB-SPACE", kind="fund", ref="AIB-SPACE")
    assert (bot["kind"], card.get("kind", "card"), fund["kind"]) == (
        "bot", "card", "fund")
    with pytest.raises(rooms.RoomError):
        rooms.open_strategy("NEX-1", "again", kind="bot",
                            ref="dd206f68-048f-4325-9f33-4ca77e40bbeb")
    with pytest.raises(rooms.RoomError):
        rooms.open_strategy("NEX-1", "the whole answer, on top of its rooms")

    view = _lab_page().build_rooms()
    assert _legs(view, "STR-0002") == ["TRD-0001"]
    assert _legs(view, "STR-0001") == [], "the bot room took the answer's orders"
    assert "TRD-0002" in _legs(view, "general")

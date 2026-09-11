"""The Nexus rooms: strategies, the operator's notes, and what we sampled.

The operator asked on 2026-09-11 to see what we write to Nexus the way they see
the correspondence on a bug -- a General room, one room per strategy that comes
out of it, their own feedback written into each. docs/nexus-rooms-plan.md is
the plan; this module is where that record lives.

Two append-only files under state/, both gitignored for the reason
state/nexus.jsonl is:

  rooms.jsonl    strategies, links, the operator's notes, ours, read marks
  samples.jsonl  what the console's sampler read from their API

Both are written while a sweep may be running -- a note typed into the console,
a sample on a timer -- and a tree that is dirty during a run is a tree no run
can reach level V from. Neither is in the dashboard's payload, for the same
reason one step removed: anything in the payload rewrites dashboard/index.html.
The console serves them at /rooms.json instead.

The writers are two on purpose. The browser may write an operator's note and
nothing else -- add_operator_note, the only one serve.py reaches -- and nothing
the browser can reach writes ours: add_claude_note, mark_read and the writers
that open, move, name and plan a strategy belong to scripts/rooms.py.
tests/meta/test_pipeline_room_notes.py reads the writers out of this file and
holds serve.py to the first.

"Read" is never stored on a note. It is derived from `read` marks, each written
by the reader through the last note it printed -- so a note that lands while
the reader is printing stays unread instead of being swallowed.

A strategy room opens from one whole Nexus answer and from nothing else --
CLAUDE.md's rule that Nexus supplies the guidance and we execute -- and one
answer opens one room. Whether an answer PROPOSED anything is a judgement this
module cannot make: NEX-0002 answered at length and named no card, so it has no
room, and that call is the opener's.

A strategy's name is ours -- a `title` row, the newest wins -- and short,
because the tab leads with it. Its plan is Nexus's proposal written down as
legs: a card by its whole id, a side, a share of the bankroll, the take-profit
and stop Nexus gave. The tab lays what was done over it, and the sampler reads
the cards it names.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from qa.state import file_lock, state_dir

GENERAL = "general"
NOTE_TYPES = ("operator_note", "claude_note")
MAX_TEXT = 4000
MAX_TITLE = 120
STATUSES = ("proposed", "running", "paused", "stopped")
# A strategy's name on the page: what it trades, in a few words.
MAX_NAME = 40
SIDES = ("bull", "bear")
MAX_LEGS = 8
# A card by the whole id their API names it with. The sampler reads the card
# through it, and the eight-character prefix our own logs print reads nothing.
CARD_ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
# What the tab calls an answered question. render.py's _nexus_questions() reads
# this same number, so a room opens only from an answer the tab shows as one.
ANSWERED_CHARS = 300
# What a link may name, by the prefix of its id, and the row that proves the id
# was ours: a question we asked, an order or a clone we intended.
RECORDS = {"NEX": ("nexus.jsonl", "question"), "TRD": ("paper.jsonl", "intent"),
           "CLN": ("clones.jsonl", "intent")}


class RoomError(ValueError):
    """A write the record refuses -- a room that does not exist, a note that is
    empty or longer than MAX_TEXT. Refused before anything is written."""


def path() -> Path:
    return state_dir() / "rooms.jsonl"


def samples_path() -> Path:
    return state_dir() / "samples.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _rows(target: Path) -> list[dict]:
    if not target.is_file():
        return []
    out = []
    # errors="replace": one damaged byte must cost one line, not the whole
    # tab and every reader after it. The line then fails to parse and is
    # skipped like a half-written one.
    for line in target.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            # A half-written line is normal while another process appends.
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def load() -> list[dict]:
    return _rows(path())


def load_samples() -> list[dict]:
    return _rows(samples_path())


def append_samples(rows: list[dict]) -> None:
    """What the console's sampler read, appended in one step under the lock.

    Not _append: that one is the rooms' own file. This is written by another
    hand -- scripts/sampler.py, on a timer -- and no browser request reaches it.
    """
    if not rows:
        return
    target = samples_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(target):
        with open(target, "a", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def records(name: str) -> list[dict]:
    """Another script's record under state/ -- nexus.jsonl, paper.jsonl,
    clones.jsonl -- read the way this one is. The rooms are drawn over them."""
    return _rows(state_dir() / name)


def number(note_id) -> int:
    """N-0007 -> 7. Anything else is 0, which no mark can reach."""
    try:
        return int(str(note_id).split("-", 1)[1])
    except (IndexError, ValueError):
        return 0


def strategies(rows: list[dict]) -> list[dict]:
    """Every strategy room opened, oldest first."""
    return [r for r in rows if r.get("type") == "strategy" and r.get("id")]


def known_rooms(rows: list[dict]) -> set[str]:
    """General, and every strategy room that has been opened."""
    return {GENERAL} | {r["id"] for r in strategies(rows)}


def names(rows: list[dict]) -> dict[str, str]:
    """Each strategy's name: its newest `title`, else the title it opened with."""
    out = {s["id"]: s.get("title") or s["id"] for s in strategies(rows)}
    for row in rows:
        if row.get("type") == "title" and row.get("room") in out and row.get("title"):
            out[row["room"]] = row["title"]
    return out


def plans(rows: list[dict]) -> dict[str, dict]:
    """Each strategy's newest plan -- Nexus's proposal, written down as legs."""
    known = {s["id"] for s in strategies(rows)}
    return {row["room"]: row for row in rows
            if row.get("type") == "plan" and row.get("room") in known}


def whole_answer(nexus_rows: list[dict], question_id) -> dict | None:
    """Nexus's answer to one question, if the tab would call it answered."""
    return next((r for r in nexus_rows
                 if r.get("id") == question_id and r.get("type") == "answer"
                 and len(r.get("text") or "") >= ANSWERED_CHARS), None)


def on_record(ref) -> bool:
    """Whether a NEX, TRD or CLN id names something we actually did."""
    name, kind = RECORDS.get(str(ref).split("-", 1)[0], (None, None))
    return bool(name) and any(r.get("id") == ref and r.get("type") == kind
                              for r in records(name))


def read_marks(rows: list[dict]) -> dict[str, int]:
    """Per room, the highest note number a `read` mark reaches."""
    marks: dict[str, int] = {}
    for row in rows:
        if row.get("type") == "read":
            room = row.get("room") or GENERAL
            marks[room] = max(marks.get(room, 0), number(row.get("through")))
    return marks


def is_read(note: dict, marks: dict[str, int]) -> bool:
    n = number(note.get("id"))
    return 0 < n <= marks.get(note.get("room") or GENERAL, 0)


def unread(rows: list[dict]) -> list[dict]:
    """The operator's notes no reader has printed yet, oldest first."""
    marks = read_marks(rows)
    return [r for r in rows
            if r.get("type") == "operator_note" and not is_read(r, marks)]


def _append(build) -> list[dict]:
    """Append what `build` makes of the rows, as one step under the lock.

    `build` sees the rows as they are INSIDE the lock, so an id it derives from
    them cannot be handed to a second writer. Two share this file -- the
    console on the operator's click and the CLI in a session -- and the id is
    what a read mark counts through.
    """
    target = path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(target):
        made = build(_rows(target))
        if made:
            with open(target, "a", encoding="utf-8") as handle:
                for row in made:
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return made


def _next_note_id(rows: list[dict]) -> str:
    used = [number(r.get("id")) for r in rows if r.get("type") in NOTE_TYPES]
    return f"N-{max(used, default=0) + 1:04d}"


def _note(kind: str, room: str, text, **extra):
    def build(rows: list[dict]) -> list[dict]:
        if room not in known_rooms(rows):
            raise RoomError(f"there is no room {room!r}")
        body = str(text or "").strip()
        if not body:
            raise RoomError("an empty note")
        if len(body) > MAX_TEXT:
            raise RoomError(f"a note over {MAX_TEXT} characters")
        return [{"type": kind, "id": _next_note_id(rows), "room": room,
                 "at": _now(), "text": body, **extra}]
    return build


def add_operator_note(room: str, text: str) -> dict:
    """The browser's one write: a note from the operator, into a room that exists."""
    return _append(_note("operator_note", room, text))[0]


def add_claude_note(room: str, text: str, about: str | None = None,
                    gist: bool = False) -> dict:
    """Ours, from scripts/rooms.py. Never unread: it is not the operator's feedback.

    `about` names the Nexus question it is about -- NEX-0016 -- and the tab
    shows it beside the note. A `gist` is our one-line Czech summary of that
    answer: the tab draws it inside the answer wherever the answer is shown,
    so it must name a question that is on record.
    """
    extra: dict = {"re": about} if about else {}
    if gist:
        if not (about and str(about).startswith("NEX-") and on_record(about)):
            raise RoomError("a summary is of a Nexus answer on record -- "
                            "name it with --re NEX-...")
        extra["gist"] = True
    return _append(_note("claude_note", room, text, **extra))[0]


def mark_read(through: dict[str, str]) -> list[dict]:
    """One `read` row per room, through the last note the reader printed."""
    def build(rows: list[dict]) -> list[dict]:
        return [{"type": "read", "room": room, "through": note_id, "at": _now()}
                for room, note_id in sorted(through.items())]
    return _append(build) if through else []


def _reason(why) -> str:
    text = str(why or "").strip()
    if not text:
        raise RoomError("say why")
    if len(text) > MAX_TEXT:
        raise RoomError(f"a reason over {MAX_TEXT} characters")
    return text


def _strategy(rows: list[dict], room: str) -> None:
    if room not in {r["id"] for r in strategies(rows)}:
        raise RoomError(f"there is no strategy room {room!r}")


def open_strategy(origin: str, title: str) -> dict:
    """A room for a strategy Nexus proposed, opened from its whole answer.

    One answer opens one room, so every order and clone that acts on an
    answer has exactly one room to be drawn in.
    """
    name = " ".join(str(title or "").split())
    if not name or len(name) > MAX_TITLE:
        raise RoomError(f"a title of 1 to {MAX_TITLE} characters")
    if whole_answer(records("nexus.jsonl"), origin) is None:
        raise RoomError(f"{origin} has no whole answer from Nexus, and a room "
                        f"opens only from one")

    def build(rows: list[dict]) -> list[dict]:
        taken = next((r["id"] for r in strategies(rows)
                      if r.get("origin") == origin), None)
        if taken:
            raise RoomError(f"{origin} already opened {taken}")
        used = [number(r["id"]) for r in strategies(rows)]
        return [{"type": "strategy", "id": f"STR-{max(used, default=0) + 1:04d}",
                 "origin": origin, "title": name, "at": _now()}]
    return _append(build)[0]


def set_status(room: str, status: str, why: str) -> dict:
    """Where a strategy stands now, and why it moved. The newest row wins."""
    if status not in STATUSES:
        raise RoomError(f"a status is one of: {', '.join(STATUSES)}")
    reason = _reason(why)

    def build(rows: list[dict]) -> list[dict]:
        _strategy(rows, room)
        return [{"type": "status", "room": room, "status": status, "why": reason,
                 "at": _now()}]
    return _append(build)[0]


def add_link(room: str, ref: str, why: str) -> dict:
    """Draw a question, an order or a clone in a room its own record does not
    name -- a question asked in General about a strategy, an order placed
    without a Nexus id. The newest link of an id wins."""
    reason = _reason(why)
    if not on_record(ref):
        raise RoomError(f"there is no {ref!r} in our records")

    def build(rows: list[dict]) -> list[dict]:
        _strategy(rows, room)
        return [{"type": "link", "room": room, "ref": ref, "why": reason,
                 "at": _now()}]
    return _append(build)[0]


def set_title(room: str, title: str) -> dict:
    """What the tab calls a strategy -- what it trades, in a few words. The
    newest wins; the title it opened with stays on its `strategy` row."""
    name = " ".join(str(title or "").split())
    if not name or len(name) > MAX_NAME:
        raise RoomError(f"a name of 1 to {MAX_NAME} characters")

    def build(rows: list[dict]) -> list[dict]:
        _strategy(rows, room)
        return [{"type": "title", "room": room, "title": name, "at": _now()}]
    return _append(build)[0]


def _number(value, what: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise RoomError(f"{what} is a number, not {value!r}")
    try:
        return float(value)
    except (TypeError, ValueError):
        raise RoomError(f"{what} is a number, not {value!r}") from None


def _leg(leg: dict) -> dict:
    card = str(leg.get("card") or "").strip().lower()
    if not CARD_ID.match(card):
        raise RoomError(f"{card!r} is not a card id -- the whole id, the way "
                        f"their API names the card")
    side = str(leg.get("side") or "").strip().lower()
    if side not in SIDES:
        raise RoomError(f"a side is {' or '.join(SIDES)}, not {leg.get('side')!r}")
    share = _number(leg.get("share"), "a share")
    if share is None or not 0 < share <= 1:
        raise RoomError("a share is over 0 and at most the whole bankroll")
    tp = _number(leg.get("tp"), "a take-profit")
    if tp is not None and tp <= 0:
        raise RoomError("a take-profit is a rise, above 0 %")
    sl = _number(leg.get("sl"), "a stop")
    if sl is not None and sl >= 0:
        raise RoomError("a stop is a fall, below 0 %")
    return {"card": card, "side": side, "share": round(share, 6), "tp": tp, "sl": sl}


def set_plan(room: str, legs: list[dict], reserve=None, bankroll=None) -> dict:
    """Nexus's proposal for a strategy, written down as legs.

    A leg is a card by its whole id, a side, the share of the bankroll Nexus
    gave it, and the take-profit and stop it gave, in percent from the entry.
    `reserve` is the share it kept back and `bankroll` the sum it sized
    against. It records what was PROPOSED; what was done stays in paper.jsonl,
    and the tab lays the one over the other. The newest plan wins.
    """
    clean = [_leg(leg if isinstance(leg, dict) else {}) for leg in legs or []]
    if not clean or len(clean) > MAX_LEGS:
        raise RoomError(f"a plan has 1 to {MAX_LEGS} legs")
    cards = [leg["card"] for leg in clean]
    if len(set(cards)) != len(cards):
        raise RoomError("a card is named twice -- one leg per card")
    kept = _number(reserve, "a reserve")
    if kept is not None and not 0 <= kept < 1:
        raise RoomError("a reserve is at least 0 and less than the whole bankroll")
    total = sum(leg["share"] for leg in clean) + (kept or 0.0)
    if total > 1.000001:
        raise RoomError(f"the legs and the reserve come to {total:.0%} of the bankroll")
    size = _number(bankroll, "a bankroll")
    if size is not None and size <= 0:
        raise RoomError("a bankroll is above 0")

    def build(rows: list[dict]) -> list[dict]:
        _strategy(rows, room)
        return [{"type": "plan", "room": room, "legs": clean,
                 "reserve": None if kept is None else round(kept, 6),
                 "bankroll": size, "at": _now()}]
    return _append(build)[0]

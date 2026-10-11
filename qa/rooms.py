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

A strategy room opens from one whole Nexus answer -- CLAUDE.md's rule that
Nexus supplies the guidance and we execute -- and one answer opens one room.
Since V5 (2026-09-23) one more thing opens one: a proposal of OURS on record
(OUR-NNNN, qa.lab.note_proposal), a paper bot's next setting. Its origin
says whose idea it is, so it is never read as his. Whether an answer PROPOSED anything is a judgement this
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
from datetime import datetime, timedelta, timezone
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
# What a leg may hold since 2026-09-22 -- the operator: everything that runs on
# paper, not only cards. A card is bought on paper, a bot is cloned on paper
# (scripts/clone.py), a fund is only MARKED: create_aib_fund spends real money
# and has no paper switch, so its leg is watched on its own series.
# An arena leg (2026-09-22) holds one team of their BLUE/RED Arena, named as
# place_arena_order's `team_symbol` enum names it; the tool trades on paper
# only with `mode: paper`, which qa/safety.py holds it to.
LEG_KINDS = ("card", "bot", "fund", "arena")
ARENA_TEAMS = ("BLUE", "RED")
# The name of the sampler's read of one team's book on a tick's `reads`: the
# sampler writes it and the verdict looks it up, so it is spelled once.
ARENA_DOOR = "arena {team}"
FUND_SYMBOL = re.compile(r"^[A-Z0-9][A-Z0-9-]{0,39}$")
BOT_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}$")
# What /lab calls an answered question. lab_page.py's _nexus_questions() reads
# this same number, so a room opens only from an answer the tab shows as one.
ANSWERED_CHARS = 300
# What a link may name, by the prefix of its id, and the row that proves the id
# was ours: a question we asked, an order or a clone we intended.
RECORDS = {"NEX": ("nexus.jsonl", "question"), "TRD": ("paper.jsonl", "intent"),
           "CLN": ("clones.jsonl", "intent"),
           # V5: a proposal of OURS in the laboratory's notebook -- what a
           # room of our own lane opens from (qa.lab.note_proposal).
           "OUR": ("lab.jsonl", "proposal")}
OUR_ORIGIN = re.compile(r"^OUR-\d{4}$")


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
    """General, and every strategy room that has been opened. What a question
    to Nexus may be asked in: a sector names nothing he could answer about."""
    return {GENERAL} | {r["id"] for r in strategies(rows)}


# The laboratory's seven sections, in the operator's order (2026-10-11, the laborator skill,
# "Seven sections"): our own cards, his cards, bots, head-to-head, memecoins, the outsider and
# the desk. The keys of the three that existed before stay what they were -- `cards` is his --
# so no room and no note moves. A room may be opened in one (`open_strategy(section=...)`).
SECTIONS = ("own", "cards", "bots", "h2h", "memecoins", "outsider", "desk")

# One room per sector on /lab (the operator, 2026-09-23: "1 room pro karty,
# 1 pro boty, 1 na memecoiny"). They hold notes -- the operator's and ours --
# and exist without being opened, the way General does. Funds stay, for the notes written
# to them before they were switched off.
SECTORS = SECTIONS + ("funds",)


_KIND_SECTION = {"card": "cards", "bot": "bots", "fund": "funds"}


def section_of(room: dict, plan: dict | None = None, bot_origins=()) -> str | None:
    """A strategy room's section: the one it was opened in, when its row names one. Otherwise
    what its kind always made it -- rooms opened before 2026-09-21 carry no kind: one naming a
    card holds cards, and one whose answer's order was a clone (STR-0001, Perceptron Oracle)
    holds a bot; a kindless room whose plan holds legs of one kind is that kind (STR-0045). A
    card room of ours is ours, never among his cards (none was opened before v3, so this moves
    no room). Funds keep their old name, which no section has; an Arena room is in none."""
    if room.get("section") in SECTIONS:
        return room["section"]
    kind = room_kind(room, plan)
    if kind:
        found = _KIND_SECTION.get(kind)
    else:
        found = "bots" if str(room.get("origin")) in set(bot_origins or ()) else "cards"
    return "own" if found == "cards" and OUR_ORIGIN.match(str(room.get("origin"))) else found


def note_rooms(rows: list[dict]) -> set[str]:
    """Where a note may go: every room a question may, and every sector."""
    return known_rooms(rows) | set(SECTORS)


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


def nexus_answers() -> list[dict]:
    """His answers from both doors: the deep lane's diary and, since
    2026-09-19, the sync door's (scripts/nexus.py::ask_shallow), which the
    laboratory falls back to while the deep lane is at capacity. A room opens
    from either; the checks behind #85 and #86 read the deep one alone."""
    return records("nexus.jsonl") + records("nexus_shallow.jsonl")


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
        if room not in note_rooms(rows):
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
    shows it beside the note. A `gist` is our one-line English summary of that
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


def room_key(row: dict) -> str | None:
    """What a strategy room was opened FOR, within its answer: a card's id,
    or since 2026-09-22 a bot's species id or a fund's symbol. None is a
    WHOLE-ANSWER room -- the older kind, which takes everything the answer
    did. A bot or fund room has no `card`, and reading "no card" as "whole
    answer" would let it swallow every order its answer made."""
    key = row.get("card") or row.get("ref")
    return str(key).lower() if key else None


def open_strategy(origin: str, title: str, card: str | None = None, *,
                  kind: str | None = None, ref: str | None = None,
                  section: str | None = None, settings: dict | None = None) -> dict:
    """A room for a strategy Nexus proposed, opened from its whole answer.

    One answer opens one room -- or, when `card` is given, one room per card
    it names (2026-09-21: an answer naming five cards is five strategies, and
    folding them into one room also made the day cap count answers rather
    than strategies). Either way every order and clone that acts on an
    answer has exactly one room to be drawn in: by the answer, or by the
    answer and the card it bought.

    `kind` and `ref` open a room for one bot (its species id) or one fund
    (its symbol) of the answer, the same way `card` does for a card.

    `section` (laboratory v3, 2026-10-11) is the section of `SECTIONS` the room is opened in,
    written on its row; a room opened with none keeps the section its kind gives it.
    `settings` is a bot room's band as it was opened with it (P3), which the register keys
    the room by: {"stop_loss_pct": .., "take_profit_pct": ..}.
    """
    if settings is not None and (
            not isinstance(settings, dict)
            or set(settings) - {"stop_loss_pct", "take_profit_pct"}
            or not all(isinstance(v, (int, float)) and not isinstance(v, bool)
                       for v in settings.values())):
        raise RoomError("a room's settings are its band: stop_loss_pct and take_profit_pct")
    name = " ".join(str(title or "").split())
    if not name or len(name) > MAX_TITLE:
        raise RoomError(f"a title of 1 to {MAX_TITLE} characters")
    if kind is not None and (kind not in LEG_KINDS or kind == "card" or not ref):
        raise RoomError("a bot or fund room names its kind and what it holds; "
                        "a card room is opened with `card`")
    if section is not None and section not in SECTIONS:
        raise RoomError(f"{section!r} is not a section of the laboratory "
                        f"({', '.join(SECTIONS)})")
    if OUR_ORIGIN.match(str(origin)):
        # Our own lane (V5, under the 2026-09-23 pin): a room we propose
        # opens from our proposal on record, and its origin says it is ours.
        if not on_record(origin):
            raise RoomError(f"{origin} is no proposal of ours on record, and "
                            f"a room of ours opens only from one")
    elif whole_answer(nexus_answers(), origin) is None:
        raise RoomError(f"{origin} has no whole answer from Nexus, and a room "
                        f"opens only from one")

    wanted = str(card or ref).lower() if (card or ref) else None

    def build(rows: list[dict]) -> list[dict]:
        # A whole-answer room excludes every other room from that answer, and
        # a room for one thing excludes a second room for the same thing.
        taken = next((r["id"] for r in strategies(rows)
                      if r.get("origin") == origin
                      and (wanted is None or room_key(r) is None
                           or room_key(r) == wanted)), None)
        if taken:
            raise RoomError(f"{origin} already opened {taken}"
                            + (f" for {wanted[:8]}" if wanted else ""))
        used = [number(r["id"]) for r in strategies(rows)]
        row = {"type": "strategy", "id": f"STR-{max(used, default=0) + 1:04d}",
               "origin": origin, "title": name, "at": _now()}
        if card:
            row["card"] = wanted
        elif kind:
            row["kind"], row["ref"] = kind, str(ref)
        if section:
            row["section"] = section
        if settings:
            row["settings"] = dict(settings)
        return [row]
    return _append(build)[0]


def set_status(room: str, status: str, why: str) -> dict:
    """Where a strategy stands now, and why it moved. The newest row wins.

    `running` needs a criterion first. A room that starts trading before
    anybody wrote down what would count as success is a room whose result can
    be read as whatever it turned out to be -- the reason every run in this
    repository is preregistered, applied to the thing the runs are for.
    """
    if status not in STATUSES:
        raise RoomError(f"a status is one of: {', '.join(STATUSES)}")
    reason = _reason(why)

    def build(rows: list[dict]) -> list[dict]:
        _strategy(rows, room)
        if status == "running" and acceptance_of(rows, room) is None:
            raise RoomError(
                f"{room} has no criterion yet, so nothing could say afterwards "
                f"whether it worked. Write one first (rooms.set_acceptance, or "
                f"`lab.py adopt {room}` for a room that was already running)")
        return [{"type": "status", "room": room, "status": status, "why": reason,
                 "at": _now()}]
    return _append(build)[0]


# What a number may look like inside his prose: 5.16, +9,7, -5%.
CLAIM_NUMBER = re.compile(r"[-+]?\d+(?:[.,]\d+)?")


def claim_of(rows: list[dict], room: str) -> dict | None:
    """The newest set of Nexus's own numbers for this room."""
    seen = [r for r in rows if r.get("type") == "claim" and r.get("room") == room]
    return seen[-1] if seen else None


def acceptance_of(rows: list[dict], room: str) -> dict | None:
    seen = [r for r in rows
            if r.get("type") == "acceptance" and r.get("room") == room]
    return seen[-1] if seen else None


def verdict_of(rows: list[dict], room: str) -> dict | None:
    seen = [r for r in rows
            if r.get("type") == "verdict" and r.get("room") == room]
    return seen[-1] if seen else None


def status_of(rows: list[dict], room: str) -> str | None:
    """Where a strategy stands now -- the newest `status` row, or None for a
    room nobody has ever moved out of `proposed` (which writes no row at all;
    `open_strategy` names no starting status)."""
    seen = [r for r in rows
            if r.get("type") == "status" and r.get("room") == room]
    return seen[-1]["status"] if seen else None


def set_claim(room: str, quoted: dict) -> dict:
    """His numbers, and only the ones his answer actually says.

    Every value is a substring of the whole answer the room opened from, and
    the check is not a formality: on 2026-09-11 a plan promised the operator
    five rooms because our own records credited orders to an answer that named
    no card. A number we typed is our reading; a number we can point to in his
    text is his claim, and only his claim may be scored against later.
    """
    if not quoted:
        raise RoomError("a claim with no numbers is not a claim")

    def build(rows: list[dict]) -> list[dict]:
        _strategy(rows, room)
        origin = next((r.get("origin") for r in strategies(rows)
                       if r.get("id") == room), None)
        answer = whole_answer(nexus_answers(), origin) if origin else None
        text = str((answer or {}).get("text") or "")
        if not text:
            raise RoomError(
                f"{room} has no whole answer to quote from, so there is no "
                f"claim of his to record")
        numbers = {}
        for name, written in quoted.items():
            if str(written) not in text:
                raise RoomError(
                    f"{name}={written!r} does not appear in {origin}'s answer. "
                    f"A claim is his words, not our reading of them")
            found = CLAIM_NUMBER.search(str(written))
            if not found:
                raise RoomError(f"{name}={written!r} carries no number")
            numbers[name] = float(found.group(0).replace(",", "."))
        return [{"type": "claim", "room": room, "origin": origin,
                 "quoted": {k: str(v) for k, v in quoted.items()},
                 "numbers": numbers, "at": _now()}]
    return _append(build)[0]


def set_acceptance(room: str, window_days: float, stop_pct: float, why: str,
                   legs: list[dict] | None = None,
                   benchmark_card: str | None = None,
                   adopted: bool = False) -> dict:
    """What would count as success, written before the room runs.

    It cannot be moved while its window is open. A criterion rewritten halfway
    is a criterion fitted to the numbers, which is the one thing a
    preregistration exists to prevent -- and the repository already refuses
    exactly that for its own runs.
    """
    reason = _reason(why)
    days = _number(window_days, "window_days")
    if not days or days <= 0:
        raise RoomError("a window of at least a fraction of a day")
    stop = _number(stop_pct, "stop_pct")

    def build(rows: list[dict]) -> list[dict]:
        _strategy(rows, room)
        current = acceptance_of(rows, room)
        if current is not None:
            started = datetime.fromisoformat(
                str(current["at"]).replace("Z", "+00:00"))
            closes = started + timedelta(days=float(current["window_days"]))
            if datetime.now(timezone.utc) < closes:
                raise RoomError(
                    f"{room} already has a criterion, and its window closes "
                    f"{closes.isoformat(timespec='minutes')}. Stop the room "
                    f"and write a new one rather than moving this one")
        chosen = legs
        if chosen is None:
            chosen = (plans(rows).get(room) or {}).get("legs") or []
        return [{"type": "acceptance", "room": room, "window_days": float(days),
                 "stop_pct": float(stop) if stop is not None else None,
                 "legs": chosen, "benchmark_card": benchmark_card,
                 "adopted": bool(adopted), "why": reason, "at": _now()}]
    return _append(build)[0]


def record_verdict(room: str, said: dict) -> dict:
    """What the numbers said at the end of the window, and which formula said it."""
    if not isinstance(said, dict) or not said.get("verdict"):
        raise RoomError("a verdict says what it decided")

    def build(rows: list[dict]) -> list[dict]:
        _strategy(rows, room)
        if acceptance_of(rows, room) is None:
            raise RoomError(f"{room} has no criterion, so nothing can be a "
                            f"verdict on it")
        return [{"type": "verdict", "room": room, "at": _now(),
                 **{k: v for k, v in said.items() if k != "at"}}]
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


def leg_kind(leg: dict) -> str:
    """What a leg holds. A leg written before 2026-09-22 names only `card`,
    and is a card leg -- read that way, never rewritten."""
    return str(leg.get("kind") or "card")


def room_kind(room: dict, plan: dict | None = None) -> str | None:
    """What a room holds: its written `kind`; a room naming a card is a card
    room; a kindless room whose plan holds legs of one kind is that kind.
    One reading for the board's money and the report's sector -- the two
    disagreed about STR-0044 and STR-0046 (2026-09-25), bot rooms opened
    without `kind`, which /lab put under Boti with no number at all."""
    if room.get("kind"):
        return str(room["kind"])
    if room.get("card"):
        return "card"
    held = {leg_kind(leg) for leg in (plan or {}).get("legs") or []}
    return next(iter(held)) if len(held) == 1 else None


def leg_ref(leg: dict):
    """The thing a leg names: a card's whole id, a bot's instance id, a fund's
    symbol. An old card leg's `card` is its ref."""
    return leg.get("ref") or leg.get("card")


def _leg(leg: dict) -> dict:
    kind = leg_kind(leg)
    if kind not in LEG_KINDS:
        raise RoomError(f"a leg holds a {', a '.join(LEG_KINDS)}, not {kind!r}")
    ref = str(leg_ref(leg) or "").strip()
    if kind == "card":
        ref = ref.lower()
        if not CARD_ID.match(ref):
            raise RoomError(f"{ref!r} is not a card id -- the whole id, the way "
                            f"their API names the card")
    elif kind == "fund" and not FUND_SYMBOL.match(ref):
        raise RoomError(f"{ref!r} is not a fund symbol, the way list_funds "
                        f"names one")
    elif kind == "bot" and not BOT_REF.match(ref):
        raise RoomError(f"{ref!r} is not a bot's instance id")
    elif kind == "arena":
        ref = ref.upper()
        if ref not in ARENA_TEAMS:
            raise RoomError(f"{ref!r} is not an Arena team: "
                            f"{' or '.join(ARENA_TEAMS)}")
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
    # A card leg keeps `card`, the field the sampler, the page and the launcher
    # have always read it by.
    named = {"card": ref} if kind == "card" else {}
    return {**named, "kind": kind, "ref": ref, "side": side,
            "share": round(share, 6), "tp": tp, "sl": sl}


def set_plan(room: str, legs: list[dict], reserve=None, bankroll=None) -> dict:
    """Nexus's proposal for a strategy, written down as legs.

    A leg is a card by its whole id (or, since 2026-09-22, a `kind` of bot or
    fund and its `ref`: the clone's instance id, the fund's symbol), a side,
    the share of the bankroll Nexus
    gave it, and the take-profit and stop it gave, in percent from the entry.
    `reserve` is the share it kept back and `bankroll` the sum it sized
    against. It records what was PROPOSED; what was done stays in paper.jsonl,
    and the tab lays the one over the other. The newest plan wins.
    """
    clean = [_leg(leg if isinstance(leg, dict) else {}) for leg in legs or []]
    if not clean or len(clean) > MAX_LEGS:
        raise RoomError(f"a plan has 1 to {MAX_LEGS} legs")
    named = [(leg["kind"], leg["ref"]) for leg in clean]
    if len(set(named)) != len(named):
        raise RoomError("a card, bot or fund is named twice -- one leg each")
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
        # One bot, one room at a time (deep pass 2026-09-24, R03): a clone
        # held by another room that has not stopped would be judged twice.
        bots = {leg["ref"] for leg in clean if leg["kind"] == "bot"}
        for other, plan in plans(rows).items():
            if other == room or status_of(rows, other) == "stopped":
                continue
            held = bots & {str(leg_ref(g)) for g in plan.get("legs") or []
                           if leg_kind(g) == "bot"}
            if held:
                raise RoomError(f"{', '.join(sorted(held))} is held by {other}, "
                                f"which has not stopped; one bot, one room")
        return [{"type": "plan", "room": room, "legs": clean,
                 "reserve": None if kept is None else round(kept, 6),
                 "bankroll": size, "at": _now()}]
    return _append(build)[0]

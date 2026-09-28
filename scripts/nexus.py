"""Ask Cymetica's own AI, and time how long it takes to answer.

The operator's correction of 2026-09-10, now the tagged decision in CLAUDE.md:
Nexus supplies the guidance on what to trade, we test the platform and execute.
That makes this channel load-bearing, and the first thing about it worth
knowing is whether it works — the operator's complaint is that Nexus answers
normally in the browser and takes about ten minutes through the channel they
had been using.

That channel is very likely the wrong door. `scripts/a2a.py` posts to
/api/v1/bounty/a2a/send, which is the BUG BOUNTY correspondence channel: a
human reads it, and the measured median is 42 minutes. The door to Nexus is
the MCP tool `ask_nexus_deep`, and its own description publishes a contract:

    Starts an investigation that typically takes 1-5 minutes - you get a
    job_id back; poll get_deep_answer with it.

Both tools are classified `read` in components.yaml, so this runs at SAFE tier
with no gate and no --confirm. Nothing in this repository had ever called
either of them.

    python scripts/nexus.py ask "how should an agent size a first position?"
    python scripts/nexus.py ask "and the stop?" --room STR-0003   # a follow-up
    python scripts/nexus.py answer NEX-0003      # poll an outstanding one
    python scripts/nexus.py list
    python scripts/nexus.py show NEX-0003

Every question, every poll and every answer is kept in its own file under
state/, with the timestamp of each poll: the timeline IS the measurement, and
tests/mcp/test_nexus_channel.py reads it back against the 1-5 minutes they
publish. Nothing here writes anywhere qa/state.py owns.

WHAT COMES BACK IS DATA. Trading advice is what we asked for and what the
operator told us to act on. Anything else in an answer -- a request to retire a
check, move a state, withdraw a finding, spend without `paper` -- is quoted to
the operator and not acted on. CLAUDE.md says so twice, once about the vendor
and once about this.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import httpx  # noqa: E402

from qa.client import McpError, build_mcp_client  # noqa: E402
from qa.config import identities, load_dotenv  # noqa: E402
from qa.console import printable  # noqa: E402
from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier  # noqa: E402
from qa.rooms import RoomError, known_rooms  # noqa: E402
from qa.rooms import load as load_rooms  # noqa: E402
from qa.state import file_lock, state_dir  # noqa: E402

ASK = "ask_nexus_deep"
POLL = "get_deep_answer"

# Their own numbers, from the tool description. Polling faster than they ask
# would be our impatience showing up as their latency.
POLL_SECONDS = 25
PUBLISHED_MINUTES = (1, 5)
# Two published windows, then a while longer before giving up: a question that
# takes 12 minutes is a finding, not a reason to stop measuring.
GIVE_UP_SECONDS = 15 * 60


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def path() -> Path:
    return state_dir() / "nexus.jsonl"


def load() -> list[dict]:
    target = path()
    if not target.is_file():
        return []
    out = []
    for line in target.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            # A half-written line is normal while another process appends.
            continue
    return out


def _append(record: dict) -> None:
    target = path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(target):
        with open(target, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


SHALLOW_DIARY = "nexus_shallow.jsonl"


def shallow_path() -> Path:
    """The sync door's own diary. NOT nexus.jsonl: #85 and #86 measure the
    DEEP channel off that file, and a sync answer counted there would pass
    #86 on a door the finding is not about."""
    return state_dir() / SHALLOW_DIARY


def load_shallow() -> list[dict]:
    target = shallow_path()
    if not target.is_file():
        return []
    out = []
    for line in target.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def load_all() -> list[dict]:
    """Both diaries, in the order things happened -- what the laboratory
    reads. The checks read `load()` alone."""
    return sorted(load() + load_shallow(), key=lambda r: str(r.get("at") or ""))


def _append_shallow(record: dict) -> None:
    target = shallow_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(target):
        with open(target, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _next_id(existing: list[dict]) -> str:
    used = [int(r["id"].split("-")[1]) for r in existing
            if isinstance(r.get("id"), str) and r["id"].startswith("NEX-")]
    return f"NEX-{max(used, default=0) + 1:04d}"


# A read that fails is not an answer that is missing (rule 8). The first poll
# of a live investigation died on the default read timeout, which would have
# gone into the timeline as though Nexus had said nothing.
TRANSPORT_ERRORS = (httpx.TimeoutException, httpx.NetworkError,
                    httpx.ProtocolError, httpx.RemoteProtocolError)
READ_TIMEOUT = 90.0


def _client():
    load_dotenv()
    ids = identities()
    identity = ids["trusted"] if ids["trusted"].present else ids["anon"]
    client = build_mcp_client(identity, EndpointRegistry.load())
    client.http.timeout = httpx.Timeout(READ_TIMEOUT)
    return client


SHALLOW = "/api/v1/bounty/qa-agent/ask"


def _rest_client():
    from qa.client import build_client

    load_dotenv()
    return build_client(identities()["anon"], EndpointRegistry.load(),
                        timeout=60.0)


USAGE = "/api/v1/nexus/usage"
# A tick reads it every twenty minutes and must not wait out their slow hour.
USAGE_TIMEOUT = 15.0


def credit(client=None) -> dict:
    """What is left of the credit Cymetica's build plan gives our account:
    one GET of /api/v1/nexus/usage with our key (ET-27414 made it readable
    so), trimmed by `qa.lab.credit_reading`. A read, billed as nothing -- its
    items are the Build it Better requests and pages we filed, and a read of
    it is not among them (2026-09-28).

    Cymetica's credit, not the operator's Claude plan, which nothing here
    reads. A server that does not answer is an unread reading, never an
    exception that stops the tick and never a zero (rule 8)."""
    from qa import lab
    from qa.client import build_client

    own = client is None
    if own:
        load_dotenv()
        identity = identities()["trusted"]
        if not identity.present:
            return {"read": False, "why": "no QA_TRUSTED_KEY, and /usage is per account"}
        client = build_client(identity, EndpointRegistry.load(), timeout=USAGE_TIMEOUT)
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        try:
            response = client.get(USAGE)
        except httpx.HTTPError as exc:
            return lab.credit_reading(None, None, why=type(exc).__name__)
        try:
            body = response.json()
        except ValueError:
            body = None
        return lab.credit_reading(response.status_code, body)
    finally:
        CURRENT_TIER.reset(token)
        if own:
            client.close()


def ask_shallow(question: str) -> dict:
    """The same question through their SYNC door, answered in seconds.

    [operator 2026-09-19] said yes to the fallback Cymetica advised in
    REPLY-0018 -- the deep lane is a shared capacity window, and while it is
    full they tell an agent to ask POST /api/v1/bounty/qa-agent/ask rather
    than stall. Written to this same diary under the same NEX id sequence, so
    the launch, the board and the brief read it like any answer of his; the
    rows say `lane: shallow` and carry their confidence, because on
    2026-09-10 this door answered a trading question with an onboarding
    brochure at confidence 0.95 and the next reader should be able to tell.

    A door that does not answer 200 with text is a give-up, never an empty
    answer (rule 8).
    """
    entry = {"id": _next_id(load_all()), "type": "question", "at": _now(),
             "question": question, "tool": SHALLOW, "lane": "shallow"}
    _append_shallow(entry)
    # The question row is on the diary now, so EVERYTHING after it closes it:
    # a question left with no answer and no give-up is one lab.outstanding
    # reads as in flight, and while it is, nothing may be asked -- for a day
    # (R03, deep pass of 2026-09-19). Our own failure is written as ours.
    try:
        client = _rest_client()
        token = CURRENT_TIER.set(SafetyTier.PROBE)
        try:
            try:
                response = client.post(SHALLOW, json={"question": question})
            except TRANSPORT_ERRORS as exc:
                response, failure = None, f"unread: {type(exc).__name__}"
        finally:
            client.close()
            CURRENT_TIER.reset(token)

        body, text = {}, ""
        if response is not None:
            failure = f"HTTP {response.status_code}"
            if response.status_code == 200:
                try:
                    body = response.json() or {}
                except ValueError:
                    body = {}
                if not isinstance(body, dict):
                    body = {}
                text = str(body.get("answer") or "").strip()
                failure = "" if text else "HTTP 200 with no answer text"
    except BaseException as exc:
        _append_shallow({"id": entry["id"], "type": "gave_up", "at": _now(),
                         "lane": "shallow",
                         "status": f"error: {type(exc).__name__}: "
                                   f"{str(exc)[:160]}"})
        raise
    if not text:
        record = {"id": entry["id"], "type": "gave_up", "at": _now(),
                  "lane": "shallow", "status": f"failed: {failure}"}
        _append_shallow(record)
        print(f"{entry['id']}: {SHALLOW} gave no answer ({failure})")
        return record
    record = {"id": entry["id"], "type": "answer", "at": _now(),
              "lane": "shallow", "text": text,
              "confidence": body.get("confidence"),
              "sources": body.get("sources")}
    _append_shallow(record)
    print(f"{entry['id']}: answered through {SHALLOW} "
          f"(confidence {body.get('confidence')}, {len(text)} chars)")
    return record


CHAT = "ask_nexus"


def ask_chat(question: str) -> dict:
    """The question through the NEXUS bar: the MCP tool `ask_nexus`, which
    their degen page's "Send to NEXUS" button fills (REPLY-0064). Its own
    description: "Same answer as POST /api/v1/support/ai-agent". Written to
    the shallow diary under the same NEX sequence, `lane: chat`; anything
    that is not answer text is a give-up (rule 8)."""
    entry = {"id": _next_id(load_all()), "type": "question", "at": _now(),
             "question": question, "tool": CHAT, "lane": "chat"}
    _append_shallow(entry)
    try:
        client = _client()
        token = CURRENT_TIER.set(SafetyTier.SAFE)
        try:
            try:
                body, failure = client.call(CHAT, {"question": question}), ""
            except TRANSPORT_ERRORS as exc:
                body, failure = None, f"unread: {type(exc).__name__}"
            except McpError as exc:
                body, failure = None, f"tool error: {str(exc)[:160]}"
        finally:
            client.http.close()
            CURRENT_TIER.reset(token)
    except BaseException as exc:
        _append_shallow({"id": entry["id"], "type": "gave_up", "at": _now(),
                         "lane": "chat",
                         "status": f"error: {type(exc).__name__}: {str(exc)[:160]}"})
        raise
    body = body if isinstance(body, dict) else {}
    if "answer" not in body and isinstance(body.get("result"), dict):
        body = body["result"]  # {"success", "tool", "result": {"answer", ...}}
    text = str(body.get("answer") or "").strip()
    if not text:
        record = {"id": entry["id"], "type": "gave_up", "at": _now(),
                  "lane": "chat",
                  "status": f"failed: {failure or 'no answer text'}"}
        _append_shallow(record)
        print(f"{entry['id']}: {CHAT} gave no answer ({record['status']})")
        return record
    record = {"id": entry["id"], "type": "answer", "at": _now(), "lane": "chat",
              "text": text, "confidence": body.get("confidence"),
              "sources": body.get("sources"), "session_id": body.get("session_id")}
    _append_shallow(record)
    print(f"{entry['id']}: answered through {CHAT} "
          f"(confidence {body.get('confidence')}, {len(text)} chars)")
    return record


def record_answer(question: str, text: str, *, at: str | None = None,
                  where: str = "web chat") -> dict:
    """An answer of his that did NOT come through a door of ours.

    The operator talks to Nexus on their website, and what he says there is
    guidance like any other -- the brief should hold it, the board should be
    able to score it, and the next tick should not ask the same thing again.
    Until now there was nowhere to put it, so it lived in a chat that ends at
    the next /clear.

    It goes in the shallow diary, not the deep one, for the reason `lane:
    shallow` exists: #85 and #86 measure THEIR channel off `load()`, and a row
    we typed in has no poll behind it and no latency to read. Counting it
    there would be a verdict about their availability drawn from our own
    keyboard -- the defect the memory `a-read-that-writes-is-a-writer`
    records. `load_all()` is what the laboratory reads, and it sees this.

    `at` is when HE said it, not when we typed it: the diary is a timeline.
    """
    text = (text or "").strip()
    if not text:
        raise SystemExit("refused: an answer with no text is not an answer")
    qid = _next_id(load_all())
    said = at or _now()
    _append_shallow({"id": qid, "type": "question", "at": said,
                     "question": question, "lane": "operator",
                     "via": where})
    row = {"id": qid, "type": "answer", "at": said, "lane": "operator",
           "via": where, "text": text}
    _append_shallow(row)
    return row


def _inner(payload):
    """Their envelope is {success, tool, result:{...}}; the answer is inside.

    Both readers here were written flat and both were wrong the same way: the
    job id was missed on the first call, and then `status` read `unknown` for
    seven minutes over an investigation their server had already marked
    failed. One descent, used by everything.
    """
    node = payload
    for _ in range(4):
        if isinstance(node, dict) and isinstance(node.get("result"), (dict, str)):
            node = node["result"]
        else:
            break
    return node


def _status_of(payload) -> str:
    node = _inner(payload)
    if isinstance(node, dict):
        value = node.get("status")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "unknown"


def _text_of(answer) -> str:
    """Their answer, whatever shape it arrives in."""
    if isinstance(answer, str):
        return answer
    if isinstance(answer, dict):
        for key in ("answer", "text", "result", "content", "message"):
            value = answer.get(key)
            if isinstance(value, str) and value.strip():
                return value
        return json.dumps(answer, ensure_ascii=False)
    return str(answer)


def _job_id_of(started) -> str | None:
    """Their id for the investigation, wherever in the envelope it sits.

    The first call here reported "did not start an investigation" while their
    server had in fact started one: the id arrives at
    `result.job_id`, one level below where the flat reader looked. A missing
    id and an id we failed to read are the same silence from outside, and only
    one of them is theirs -- so this descends rather than guessing a shape.
    """
    seen: list = [started]
    while seen:
        node = seen.pop(0)
        if isinstance(node, str) and node.strip():
            return node.strip()
        if not isinstance(node, dict):
            continue
        for key in ("job_id", "jobId", "investigation_id"):
            value = node.get(key)
            if isinstance(value, (str, int)) and str(value).strip():
                return str(value)
        for key in ("result", "data", "payload"):
            if isinstance(node.get(key), (dict, str)):
                seen.append(node[key])
    return None


def ask(question: str, wait: bool = True, room: str | None = None) -> dict:
    """Put the question, then poll until they answer or we give up.

    `room` files it under a strategy room -- a follow-up about something Nexus
    proposed -- and is checked before the client is even built: a question
    filed under a room that does not exist would be drawn in General, out of
    the thread it continues, and by then it would already have been sent.
    """
    entry = {"id": _next_id(load_all()), "type": "question", "at": _now(),
             "question": question, "tool": ASK}
    if room is not None:
        if room not in known_rooms(load_rooms()):
            raise RoomError(f"there is no room {room!r}")
        entry["room"] = room
    client = _client()
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        asked_at = time.monotonic()
        try:
            started = client.call(ASK, {"question": question})
            entry["job_id"] = _job_id_of(started)
            entry["accepted"] = entry["job_id"] is not None
            entry["raw_start"] = started if isinstance(started, (dict, str)) else str(started)
        except McpError as exc:
            entry["accepted"] = False
            entry["error"] = str(exc)[:400]
        entry["ask_seconds"] = round(time.monotonic() - asked_at, 2)
        _append(entry)

        if not entry.get("accepted"):
            print(f"{entry['id']}: {ASK} did not start an investigation "
                  f"({entry.get('error', 'no job id in the answer')})")
            return entry
        print(f"{entry['id']}: asked, job {entry['job_id']}, "
              f"accepted in {entry['ask_seconds']}s")
        if not wait:
            return entry
        return _poll(client, entry)
    finally:
        client.http.close()
        CURRENT_TIER.reset(token)


def _moment(value):
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def elapsed_since_asked(rows, question_id: str, at: str) -> float | None:
    """Seconds between the question and `at`, from the two recorded moments.

    Not `waited_seconds`. That field is how long ONE poll loop waited, and
    `answer` enters a second one, so a question asked at 10:00 and picked up
    at 11:00 reports about zero. Two timestamps cannot restart.
    """
    asked = next((r.get("at") for r in rows
                  if r.get("id") == question_id and r.get("type") == "question"),
                 None)
    start, end = _moment(asked), _moment(at)
    if start is None or end is None:
        return None
    return (end - start).total_seconds()


RUNNING = frozenset({"running", "queued", "pending"})


def latency_bounds(rows, question_id: str) -> tuple[float | None, float | None]:
    """What the poll record can PROVE about how long a job took.

    lower: the latest poll that still found it running.
    upper: the first poll that found it done.

    Not one number, because the answer row's `at` is when WE looked. NEX-0009
    was asked with --no-wait at 19:48:11 and polled once, at 20:02:32, and
    that one poll already said done -- so 861 s is an upper bound, and their
    job table says it finished in 155 s. Reporting the upper bound as the
    latency sent them our own pickup delay as their slowness. An unreadable
    poll is evidence of nothing and moves neither bound.
    """
    asked = _moment(next((r.get("at") for r in rows
                          if r.get("id") == question_id
                          and r.get("type") == "question"), None))
    if asked is None:
        return None, None
    lower = upper = None
    for row in rows:
        if row.get("id") != question_id or row.get("type") != "poll":
            continue
        when = _moment(row.get("at"))
        if when is None:
            continue
        offset = round((when - asked).total_seconds(), 1)
        status = str(row.get("status") or "")
        if status in RUNNING:
            lower = offset if lower is None else max(lower, offset)
        elif status == "done":
            upper = offset if upper is None else min(upper, offset)
    return lower, upper


def bounds_verdict(lower: float | None, upper: float | None) -> str:
    """Their published window, against what the bounds can defend.

    "within" only when the upper bound is inside it; "OVER" only when a poll
    SAW the job still running past it; everything between is "unknown" --
    never the reassuring half, and never the damning one either.
    """
    ceiling = PUBLISHED_MINUTES[1] * 60
    if upper is not None and upper <= ceiling:
        return "within"
    if lower is not None and lower > ceiling:
        return "OVER"
    return "unknown"


def _poll_after(answer) -> float | None:
    """Their suggested gap before the next poll (REPLY-0019: a queued job
    carries `poll_after_s`, to be honoured like retry_after)."""
    node = _inner(answer) if answer is not None else None
    value = node.get("poll_after_s") if isinstance(node, dict) else None
    return float(value) if isinstance(value, (int, float)) and value > 0 else None


def _poll(client, entry: dict, once: bool = False) -> dict:
    """Poll on their cadence, recording every attempt with its moment.

    `once` looks a single time and leaves a job that is still queued or
    running as it is -- no give-up written. That is what a loop tick does:
    since REPLY-0019 a deep job at capacity queues for as long as their window
    stays hot, and a tick that waited on it would outlive its ten minutes.
    """
    started = time.monotonic()
    attempt = 0
    while True:
        attempt += 1
        waited = round(time.monotonic() - started, 1)
        try:
            answer = client.call(POLL, {"job_id": entry["job_id"]})
            status = _status_of(answer)
        except McpError as exc:
            answer, status = None, f"error: {str(exc)[:120]}"
        except TRANSPORT_ERRORS as exc:
            # Unreadable, not unanswered. The poll is recorded so the timeline
            # keeps its shape, and the loop goes round again.
            answer, status = None, f"unread: {type(exc).__name__}"
        record = {"id": entry["id"], "type": "poll", "at": _now(),
                  "job_id": entry["job_id"], "attempt": attempt,
                  "waited_seconds": waited, "status": status}
        _append(record)
        print(f"   {waited:>6.1f}s  {status}")

        if status == "done":
            done = {"id": entry["id"], "type": "answer", "at": _now(),
                    "job_id": entry["job_id"], "waited_seconds": waited,
                    "polls": attempt, "text": _text_of(_inner(answer))}
            _append(done)
            low, high = PUBLISHED_MINUTES
            lower, upper = latency_bounds(load(), entry["id"])
            if lower is None and upper is not None:
                timing = (f"done at the first look, {upper / 60:.1f} min after "
                          f"asking -- it took at most that, and we did not "
                          f"watch it run")
            elif upper is not None:
                timing = (f"finished between {lower / 60:.1f} and "
                          f"{upper / 60:.1f} min after asking")
            else:
                timing = "timing unreadable"
            print(f"\n{timing}, {attempt} polls -- "
                  f"{bounds_verdict(lower, upper)} their published "
                  f"{low}-{high} min\n")
            print(done["text"])
            return done
        if status.startswith("failed"):
            # Their failed answer says why, whether to retry, and after how
            # long. On 2026-09-11 five failures in a row were recorded as the
            # bare word, and the fail sent on #86 could only say "failed".
            node = _inner(answer)
            reason = ({key: node[key] for key in ("error", "retryable", "retry_after_s")
                       if key in node} if isinstance(node, dict) else {})
            _append({"id": entry["id"], "type": "gave_up", "at": _now(),
                     "job_id": entry["job_id"], "waited_seconds": waited,
                     "polls": attempt, "status": status, **reason})
            print(f"\nthe investigation ended as {status} after {waited:.0f}s")
            if reason.get("error"):
                print(f"their reason: {reason['error']}")
            return {"status": status, **reason}
        if once:
            return {"status": status, "poll_after_s": _poll_after(answer)}
        if time.monotonic() - started > GIVE_UP_SECONDS:
            _append({"id": entry["id"], "type": "gave_up", "at": _now(),
                     "job_id": entry["job_id"], "waited_seconds": waited,
                     "polls": attempt, "status": status})
            print(f"\nstill {status} after {waited / 60:.0f} min; stopping. "
                  f"`nexus.py answer {entry['id']}` picks it up again.")
            return {"status": status}
        # Their suggested gap when they give one, never faster than our own
        # floor, and never past the point we stop waiting.
        gap = max(POLL_SECONDS, _poll_after(answer) or 0.0)
        left = GIVE_UP_SECONDS - (time.monotonic() - started)
        time.sleep(max(1.0, min(gap, left + 1.0)))


def answer(question_id: str, once: bool = False) -> dict:
    """Pick an outstanding question back up. The record is the cursor."""
    rows = load()
    asked = [r for r in rows if r.get("id") == question_id and r.get("type") == "question"]
    if not asked:
        raise SystemExit(f"no question {question_id}; `nexus.py list` shows them")
    if any(r.get("id") == question_id and r.get("type") == "answer" for r in rows):
        raise SystemExit(f"{question_id} is already answered; `nexus.py show {question_id}`")
    if not asked[-1].get("job_id"):
        # Refused at the door (NEX-0087, QUERY_RESTRICTED): no job to poll.
        raise SystemExit(f"{question_id} was refused, nothing to pick up: "
                         f"{str(asked[-1].get('error') or 'no job id')[:300]}")
    client = _client()
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        return _poll(client, asked[-1], once=once)
    finally:
        client.http.close()
        CURRENT_TIER.reset(token)


def poll_once(question_id: str) -> dict:
    """One look at a question in flight, for a loop tick: done writes the
    answer, failed writes the give-up, queued or running leaves it for the
    next tick."""
    return answer(question_id, once=True)


def _summary() -> list[dict]:
    rows = load()
    out = {}
    for row in rows:
        key = row.get("id")
        if row.get("type") == "question":
            out[key] = {"id": key, "at": row.get("at"),
                        "question": row.get("question", ""), "status": "asked",
                        "waited": None, "polls": 0}
        elif key in out:
            if row.get("type") == "poll":
                out[key]["polls"] = row.get("attempt", out[key]["polls"])
            elif row.get("type") == "answer":
                out[key]["status"] = "answered"
                out[key]["waited"] = row.get("waited_seconds")
            elif row.get("type") == "gave_up":
                out[key]["status"] = "unanswered"
                out[key]["waited"] = row.get("waited_seconds")
    return list(out.values())


def main(argv: list[str] | None = None) -> int:
    printable()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    ask_cmd = sub.add_parser("ask", help="put a question to Nexus")
    ask_cmd.add_argument("question")
    ask_cmd.add_argument("--no-wait", action="store_true",
                         help="record the job id and stop; poll later")
    ask_cmd.add_argument("--room", help="the strategy room it belongs to, e.g. "
                         "STR-0003; checked before anything is sent")

    answer_cmd = sub.add_parser("answer", help="poll an outstanding question")
    answer_cmd.add_argument("question_id")

    record_cmd = sub.add_parser(
        "record", help="write down an answer that came another way")
    record_cmd.add_argument("--question", required=True,
                            help="what he was asked, in our own words")
    record_cmd.add_argument("--file", help="a file holding the answer text")
    record_cmd.add_argument("--text", help="the answer itself, if it is short")
    record_cmd.add_argument("--at", help="when HE said it, ISO 8601")
    record_cmd.add_argument("--where", default="web chat",
                            help="where it was said (default: web chat)")

    sub.add_parser("list", help="every question, with how long it took")
    show_cmd = sub.add_parser("show", help="one question and its answer")
    show_cmd.add_argument("question_id")

    args = parser.parse_args(argv)

    if args.cmd == "ask":
        try:
            ask(args.question, wait=not args.no_wait, room=args.room)
        except RoomError as exc:
            print(f"refused, nothing sent: {exc}", file=sys.stderr)
            return 2
        return 0
    if args.cmd == "answer":
        answer(args.question_id)
        return 0
    if args.cmd == "record":
        if bool(args.file) == bool(args.text):
            print("give exactly one of --file or --text", file=sys.stderr)
            return 2
        text = (Path(args.file).read_text(encoding="utf-8") if args.file
                else args.text)
        row = record_answer(args.question, text, at=args.at, where=args.where)
        print(f"{row['id']}: {len(row['text'])} chars recorded from "
              f"{row['via']} -- it is HIS guidance, and it is not a reading "
              f"of their channel")
        return 0
    if args.cmd == "list":
        rows = _summary()
        if not rows:
            print("nothing asked yet")
            return 0
        for row in rows:
            took = ("-" if row["waited"] is None
                    else f"{row['waited'] / 60:.1f} min")
            print(f"{row['id']}  {str(row['at'])[:16]:16}  {row['status']:10} "
                  f"{took:>9}  {row['question'][:60]}")
        return 0

    for row in load():
        if row.get("id") == args.question_id and row.get("type") in ("question", "answer"):
            print(f"--- {row['type']} {row['at']}")
            print(row.get("question") or row.get("text") or "")
            print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

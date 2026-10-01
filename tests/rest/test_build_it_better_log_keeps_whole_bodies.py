"""A Build it Better request's message log carries each message whole.

THE CONTRACT. A request's record, `GET /api/v1/build-it-better/requests/
{ticket}` -- the REST twin of the MCP read tool `bb_get_request`, "Read-only,
no auth" -- publishes the conversation as `messages`: the BB-REQUEST, every
BB-SPEC and BB-CHANGE, the BB-ACCEPT. It is the one place a stranger or an
agent can read what was asked and what was agreed. The same record also
carries the text itself in two fields of its own: `spec_text` (the current
spec) and `improvements` (the request's list).

WHAT WENT WRONG. On 2026-09-30 ET-27671's two logged BB-SPEC messages were
exactly 8000 characters and ended mid-word ("Typed OpenAPI schemas for all of
i"), while its `spec_text` was 9392 characters, began with those same 8000,
and carried item 28 and the requester's BB-CHANGE amendment that the log copy
lost. Two of ET-26924's BB-SPEC messages are also exactly 8000 and end
mid-word. Our own spec check read the log copy and called 2 lines and a
change lost; the spec was whole. A reader of the log gets the same wrong
answer.

WHAT IT ASSERTS, over every request on the public board: no logged message
is a strict prefix of a longer text the same record holds -- the latest
BB-SPEC against `spec_text`, and the BB-REQUEST (after the "{app_name}: "
prefix the product adds) against `improvements`. Only that comparison is a
proof of a cut; a body that merely sits at 8000 characters with nothing longer
to compare it with is named, not counted.

WHAT IT DOES NOT ASSERT. That `spec_text` equals the log when both are whole:
`spec_text` is re-rendered under the current app name (ET-26608) and may be
newer than the last logged spec. That any length limit is wrong -- a limit
that says so is not this defect; a silent cut is.

INCONCLUSIVE, never passed: a board or record that does not read, or no
record on the board that holds a text to compare a log body with.

SAFE. GETs only, no key: the board is public.
"""

from __future__ import annotations

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

BOARD = "/api/v1/build-it-better/requests"
# The length every cut seen so far stopped at. Only used to NAME bodies that
# could not be compared; a cut is proved by the prefix, not by this number.
SEEN_CAP = 8000


# Their fix of #139 (2026-10-01 07:07 UTC, ET-28527): "log_message stores a body
# whole ... Messages logged before the fix stay as they were." So a cut message
# older than this is history, and only what was logged since can show the
# defect. Their platform is under development: only what is visible is judged.
FIXED_AT = "2026-10-01T07:07:13+00:00"


def logged_since(record: dict, since: str = FIXED_AT) -> int:
    """Messages of the record logged at or after their fix."""
    return sum(1 for m in record.get("messages") or []
               if isinstance(m, dict) and str(m.get("at") or "") >= since)


def cuts(record: dict, since: str = FIXED_AT) -> list[dict]:
    """Logged bodies, logged since their fix, that are a strict prefix of a
    longer text in the record."""
    messages = sorted((m for m in record.get("messages") or []
                       if isinstance(m, dict) and str(m.get("at") or "") >= since),
                      key=lambda m: str(m.get("at") or ""))
    found = []
    specs = [m for m in messages if m.get("kind") == "BB-SPEC"]
    whole_spec = record.get("spec_text")
    if specs and isinstance(whole_spec, str):
        body = str(specs[-1].get("body") or "")
        if body and len(whole_spec) > len(body) and whole_spec.startswith(body):
            found.append({"kind": "BB-SPEC", "at": specs[-1].get("at"),
                          "logged": len(body), "whole": len(whole_spec),
                          "field": "spec_text"})
    asked = [m for m in messages if m.get("kind") == "BB-REQUEST"]
    improvements = record.get("improvements")
    if asked and isinstance(improvements, str):
        body = str(asked[0].get("body") or "")
        prefix = f"{record.get('app_name')}: "
        text = body[len(prefix):] if body.startswith(prefix) else body
        if text and len(improvements) > len(text) and improvements.startswith(text):
            found.append({"kind": "BB-REQUEST", "at": asked[0].get("at"),
                          "logged": len(body), "whole": len(improvements),
                          "field": "improvements"})
    return found


def at_cap(record: dict) -> list[str]:
    return [f"{m.get('kind')} {m.get('at')}"
            for m in record.get("messages") or []
            if isinstance(m, dict) and len(str(m.get("body") or "")) == SEEN_CAP]


@qa(component="rest.build_it_better", tier=SafetyTier.SAFE, surface="rest")
def test_the_message_log_carries_each_message_whole(rest_anon):
    """No logged message is a cut copy of a text the same record holds."""
    board = rest_anon.get(BOARD)
    if board.status_code != 200:
        raise Inconclusive(f"{BOARD} answered HTTP {board.status_code}; a "
                           f"failed read is not an empty board")
    try:
        items = (board.json() or {}).get("items") or []
    except ValueError:
        raise Inconclusive(f"{BOARD} answered 200 with a body that is not JSON")

    compared, unread, cut, named = [], [], {}, {}
    for item in items:
        ticket = str(item.get("ticket") or "")
        if not ticket:
            continue
        one = rest_anon.get(f"{BOARD}/{ticket}")
        if one.status_code != 200:
            unread.append(f"{ticket} (HTTP {one.status_code})")
            continue
        try:
            record = one.json() or {}
        except ValueError:
            unread.append(f"{ticket} (not JSON)")
            continue
        if not isinstance(record.get("spec_text"), str) and not isinstance(
                record.get("improvements"), str):
            unread.append(f"{ticket} (no spec_text or improvements to compare)")
            continue
        if not logged_since(record):
            continue        # nothing logged since their fix: history, not judged
        compared.append(ticket)
        found = cuts(record)
        if found:
            cut[ticket] = found
        capped = at_cap(record)
        if capped:
            named[ticket] = capped

    tail = []
    if unread:
        tail.append(f"unread: {'; '.join(unread)}")
    if named:
        tail.append(f"bodies at exactly {SEEN_CAP} characters: " + "; ".join(
            f"{t} ({len(v)})" for t, v in named.items()))
    tail = (". NOT in the verdict -- " + " | ".join(tail)) if tail else ""

    if not compared:
        raise Inconclusive(f"no record on the board holds a message logged since "
                           f"their fix ({FIXED_AT}) beside a spec_text or "
                           f"improvements to compare it with{tail}")

    if cut:
        verdict = "failed"
        reason = (f"{sum(len(v) for v in cut.values())} logged message(s) on "
                  f"{len(cut)} request(s) are cut copies of a longer text the "
                  f"same record holds: " + "; ".join(
                      f"{t} {c['kind']} logged {c['logged']} of {c['whole']} "
                      f"characters of {c['field']}"
                      for t, found in cut.items() for c in found))
    else:
        verdict = "passed"
        reason = (f"on {len(compared)} request(s) no logged BB-SPEC or "
                  f"BB-REQUEST is a cut copy of the record's own text")
    conclude(Measurement(
        verdict=verdict,
        reason=reason + tail,
        left={"cut_messages": sum(len(v) for v in cut.values())},
        right={"cut_messages": 0},
        population={"compared": compared, "cut": cut, "at_cap": named,
                    "unread": unread, "on_board": len(items)},
        sources={"board": BOARD, "record": f"{BOARD}/{{ticket}}"}))

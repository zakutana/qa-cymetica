"""Build it Better's BB-SPEC keeps what a stranger sent, after their fix.

THE CONTRACT. Their REPLY-0021 (journal, 2026-09-19T18:56:28Z, answering our
MSG-0018/MSG-0019 on ET-26036) says the spec writer is fixed, and states the
rule it now follows:

  * "A request written as several lines IS the list -- one line, one item,
    never re-split."
  * "A single paragraph is split on sentence ends, but never after an
    abbreviation (e.g., i.e., etc.) and never inside parentheses."
  * "Nothing is ever dropped."
  * "Every BB-CHANGE is carried into the new spec word for word, as a
    numbered amendment."

What broke before it, on our own ET-26036: the seventh line of the request
(the success definition) was dropped whole, the line holding "(e.g.
Bollinger Bands, MACD, RSI)" was cut at the full stop after "e.g.", and a
BB-CHANGE came back as an identical spec because the writer kept only the
first eight sentences. They repaired that ticket by hand, so it proves
nothing about the generator: THIS CHECK EXCLUDES ET-26036 and reads only
other people's requests.

WHAT IS READ. The public board, `GET /api/v1/build-it-better/requests`, and
each request's own record, `GET .../requests/{ticket}` -- the REST twin of
the MCP read tool `bb_get_request`, "Read-only, no auth". From the record's
`messages` log: the BB-REQUEST body (minus the "{app_name}: " prefix the
product puts in front of it), every BB-CHANGE, and the LATEST BB-SPEC. The
request text is taken from the message rather than the `improvements` field
because the field is the thing their old writer appended BB-CHANGE text to.

THE FIX TIME is REPLY-0021's own timestamp, 2026-09-19T18:56:28Z: the moment
they said it was live. Not the 18:52:04Z spec on ET-26036, which is the hand
repair. A request counts only if its `submitted_at` is at or after it; one
submitted earlier is history and is named, never judged. A `submitted_at`
that does not read as a date is named too (rule 8).

WHAT IT ASSERTS, per request in that population:

  1. The spec's numbered items ("  N. ...", before the "Your changes"
     heading) carry the request, in REPLY-0021's two shapes. A multi-line
     request: every line is one item, equal to it after whitespace is
     collapsed -- a line split into two items fails, because they promised
     never to re-split. A single-line request: the line is one item, or each
     of its sentences is one item (split by the board check's SENTENCE_END,
     which does not end a sentence after e.g./i.e./etc., so an "e.g." cut
     still fails).
  2. Every BB-CHANGE posted before the latest BB-SPEC appears in that spec
     word for word as an amendment ("  CN. ..."), whitespace collapsed.

WHAT IT DOES NOT ASSERT. That the spec adds nothing: the standard paragraphs
about branding, live data and out-of-scope operations are theirs to add.
That items are in order. That a paraphrase is acceptable -- it is not; a
reworded requirement is a changed one. Whether the BUILD delivers the spec:
that is the verdict's job, not this check's.

INCONCLUSIVE, never passed: no request on the board submitted after the fix
apart from ours; none of those carrying a BB-SPEC yet; a board or record that
does not read. A BB-CHANGE newer than the latest BB-SPEC is waiting for its
spec and is named, not counted. A spec with no numbered items to parse is
named as unread rather than counted either way.

How it differs from test_a_spec_carries_every_line_of_the_request_it_answers
in test_build_it_better_board.py: that one reads `improvements` against the
whole spec text by substring, over every request including ours and ones
filed before the fix, and ignores BB-CHANGE. This one reads the message log,
item by item, post-fix and strangers only, with the addenda.

SAFE. GETs only, no key: the board is public.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude
from tests.rest.test_build_it_better_board import lines_of, sentences_of

BOARD = "/api/v1/build-it-better/requests"

# REPLY-0021, as the journal records it. See the module docstring for why
# this moment and not the hand repair four minutes earlier.
FIXED_AT = datetime(2026, 9, 19, 18, 56, 28, tzinfo=timezone.utc)
FIX_SOURCE = "REPLY-0021 2026-09-19T18:56:28Z"

# Ours. Repaired by hand, so it is not a reading of the generator.
OURS = frozenset({"ET-26036"})

ITEM = re.compile(r"^\s+(\d+)\.\s+(.*\S)\s*$")
AMENDMENT = re.compile(r"^\s+C(\d+)\.\s+(.*\S)\s*$")
CHANGES_HEADING = "Your changes"


def _norm(text: str) -> str:
    """Whitespace collapsed; nothing else touched. Words must survive as sent."""
    return " ".join(str(text or "").split())


def _moment(value):
    try:
        when = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return when if when.tzinfo else when.replace(tzinfo=timezone.utc)


def request_text(body: str, app_name: str) -> str:
    """The requester's list, without the "{app_name}: " the product prefixes."""
    body = str(body or "")
    prefix = f"{app_name}: " if app_name else ""
    return body[len(prefix):] if prefix and body.startswith(prefix) else body


def spec_parts(spec: str) -> tuple[list[str], str]:
    """The spec's numbered items, and the amendment section's text.

    Items are the "  N. ..." lines before the "Your changes" heading; the
    amendment text is every "  CN. ..." line after it, joined, so a change
    that spans lines is still found whole.
    """
    items, amendments, in_changes = [], [], False
    for line in str(spec or "").splitlines():
        if line.lstrip().startswith(CHANGES_HEADING):
            in_changes = True
            continue
        if in_changes:
            m = AMENDMENT.match(line)
            if m:
                amendments.append(m.group(2))
            elif amendments and line.startswith("     ") and line.strip():
                amendments[-1] += " " + line.strip()
            continue
        m = ITEM.match(line)
        if m:
            items.append(_norm(m.group(2)))
    return items, _norm(" ".join(amendments))


def lines_lost(request: str, items: list[str]) -> list[str]:
    """Request lines that are not carried as items, in REPLY-0021's shapes."""
    have = set(items)
    lines = [_norm(line) for line in lines_of(request)]
    if len(lines) > 1:
        # Several lines ARE the list: one line, one item, never re-split.
        return [line for line in lines if line not in have]
    lost = []
    for line in lines:
        if line in have:
            continue
        pieces = [_norm(p) for p in sentences_of(line)]
        if len(pieces) > 1 and all(p in have for p in pieces):
            continue
        lost.append(line)
    return lost


def judge(record: dict) -> dict:
    """One request's reading: lost lines, missing changes, or why unread."""
    messages = [m for m in (record.get("messages") or []) if isinstance(m, dict)]
    messages.sort(key=lambda m: str(m.get("at") or ""))
    asked = [m for m in messages if m.get("kind") == "BB-REQUEST"]
    specs = [m for m in messages if m.get("kind") == "BB-SPEC"]
    if not asked:
        return {"state": "unread", "why": "no BB-REQUEST in its log"}
    if not specs:
        return {"state": "unspecced"}
    latest = specs[-1]
    request = request_text(asked[0].get("body"), str(record.get("app_name") or ""))
    items, amended = spec_parts(latest.get("body"))
    if not items:
        return {"state": "unread", "why": "its latest BB-SPEC has no numbered item"}
    changes = [m for m in messages if m.get("kind") == "BB-CHANGE"]
    due = [m for m in changes if str(m.get("at") or "") < str(latest.get("at") or "")]
    pending = len(changes) - len(due)
    missing = [_norm(m.get("body")) for m in due
               if _norm(m.get("body")) and _norm(m.get("body")) not in amended]
    return {"state": "read", "lost": lines_lost(request, items),
            "changes_missing": missing, "changes_checked": len(due),
            "changes_pending": pending, "lines": len(lines_of(request)),
            "items": len(items)}


@qa(component="rest.build_it_better", tier=SafetyTier.SAFE, surface="rest")
def test_a_spec_written_after_their_fix_keeps_every_line_and_change(rest_anon):
    """Every line a stranger filed, and every BB-CHANGE, is in the spec whole."""
    board = rest_anon.get(BOARD)
    if board.status_code != 200:
        raise Inconclusive(f"{BOARD} answered HTTP {board.status_code}; a "
                           f"failed read is not an empty board")
    try:
        items = (board.json() or {}).get("items") or []
    except ValueError:
        raise Inconclusive(f"{BOARD} answered 200 with a body that is not JSON")

    ours, before, undated, unspecced, unread, read = [], [], [], [], [], []
    losses, missing, pending = [], [], []
    for item in items:
        ticket = str(item.get("ticket") or "")
        if not ticket:
            continue
        if ticket in OURS:
            ours.append(ticket)
            continue
        submitted = _moment(item.get("submitted_at"))
        if submitted is None:
            undated.append(ticket)
            continue
        if submitted < FIXED_AT:
            before.append(ticket)
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
        said = judge(record)
        if said["state"] == "unspecced":
            unspecced.append(ticket)
            continue
        if said["state"] == "unread":
            unread.append(f"{ticket} ({said['why']})")
            continue
        read.append(ticket)
        losses += [(ticket, line) for line in said["lost"]]
        missing += [(ticket, change) for change in said["changes_missing"]]
        if said["changes_pending"]:
            pending.append(ticket)

    named = []
    if ours:
        named.append(f"ours, excluded: {', '.join(ours)}")
    if before:
        named.append(f"filed before the fix ({FIX_SOURCE}), history: "
                     f"{', '.join(before)}")
    if undated:
        named.append(f"no readable submitted_at: {', '.join(undated)}")
    if unspecced:
        named.append(f"no BB-SPEC yet: {', '.join(unspecced)}")
    if unread:
        named.append(f"unread: {'; '.join(unread)}")
    if pending:
        named.append(f"a BB-CHANGE newer than the latest spec, not counted: "
                     f"{', '.join(pending)}")
    tail = (". NOT in the verdict -- " + " | ".join(named)) if named else ""

    if not read:
        raise Inconclusive(
            f"no stranger's request filed after {FIX_SOURCE} carries a "
            f"BB-SPEC to read, so their fix has not met a request it was not "
            f"repaired for ({len(items)} on the board){tail}")

    if losses or missing:
        verdict = "failed"
        reason = "; ".join(
            [f"{t} lost request line '{line[:90]}'" for t, line in losses[:4]]
            + [f"{t} has no amendment carrying BB-CHANGE '{c[:90]}'"
               for t, c in missing[:3]])
        reason = (f"{len(losses)} request line(s) and {len(missing)} "
                  f"BB-CHANGE(s) filed after {FIX_SOURCE} are not in the "
                  f"spec whole: " + reason)
    else:
        verdict = "passed"
        reason = (f"on {len(read)} stranger's request(s) filed after "
                  f"{FIX_SOURCE} ({', '.join(read)}), every request line is "
                  f"a spec item in the shape REPLY-0021 states and every "
                  f"BB-CHANGE is an amendment word for word")
    conclude(Measurement(
        verdict=verdict,
        reason=reason + tail,
        left={"requests_read": len(read), "lines_lost": len(losses),
              "changes_missing": len(missing)},
        right={"lines_lost": 0, "changes_missing": 0},
        population={"on_board": len(items), "read": read, "ours": ours,
                    "before_fix": before, "undated": undated,
                    "unspecced": unspecced, "unread": unread,
                    "change_pending": pending, "fixed_at": FIX_SOURCE},
        sources={"board": BOARD, "record": f"{BOARD}/{{ticket}}"}))

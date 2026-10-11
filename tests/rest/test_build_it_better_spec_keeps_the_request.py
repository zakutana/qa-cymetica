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
product puts in front of it), every BB-CHANGE, and the LATEST BB-SPEC -- or,
where the log cut that copy at 8000 characters, the record's `spec_text` if
it continues the cut copy word for word (ET-27671, 2026-09-30). Any other body
at that length is never compared. The
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
     still fails). A sentence cut at its semicolons into one item per
     clause is carried too: every word survives (ET-26776, 2026-09-25).
     A requester's own list label ("1. ", "2) ") is not a word of the
     line: their writer numbers the items itself (ET-27671, 2026-09-30).
     The request's "{name}: " prefix is stripped under the record's
     `app_name` or the name the spec header carries, since a BB-CHANGE can
     rename the request after it was filed (ET-26608).
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
WITHDRAWN = re.compile(r"\((\d+) earlier BB-CHANGE messages? withdrawn or repeated")


def _norm(text: str) -> str:
    """Whitespace collapsed; nothing else touched. Words must survive as sent."""
    return " ".join(str(text or "").split())


def _moment(value):
    try:
        when = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return when if when.tzinfo else when.replace(tzinfo=timezone.utc)


SPEC_FOR = re.compile(r"^\s*BB-SPEC for (.+?)\s*$", re.M)


def request_text(body: str, *names: str) -> str:
    """The requester's list, without the "{name}: " the product prefixes.

    More than one name, because a BB-CHANGE can rename the request: the
    record's `app_name` is then the new name, while the prefix is the one it
    was filed under -- which the first spec's header still carries
    (ET-26608, "Github" renamed "Gem Screener", 2026-09-23).
    """
    body = str(body or "")
    for name in names:
        prefix = f"{name}: " if name else ""
        if prefix and body.startswith(prefix):
            return body[len(prefix):]
    return body


def spec_name(spec: str) -> str:
    m = SPEC_FOR.search(str(spec or ""))
    return m.group(1) if m else ""


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


# A requester's own list label at the start of a line: "1. " or "12) ".
# Their writer numbers every item itself, so the label is replaced by the
# spec's number and every word after it survives -- 27 lines of ET-27671 and 4
# of ET-28378 were called lost on 2026-09-30 for that alone. One to three
# digits followed by "." or ")" and a space: "2026 roadmap" keeps its number.
LIST_LABEL = re.compile(r"^\d{1,3}[.)]\s+")


def _unlabelled(line: str) -> str:
    return LIST_LABEL.sub("", line, count=1)


def lines_lost(request: str, items: list[str]) -> list[str]:
    """Request lines that are not carried as items, in REPLY-0021's shapes.

    A line is compared with and without the requester's own list label, and
    reported as the requester wrote it.
    """
    have = set(items)
    lines = [_norm(line) for line in lines_of(request)]
    if len(lines) > 1:
        # Several lines ARE the list: one line, one item, never re-split.
        return [line for line in lines
                if line not in have and _unlabelled(line) not in have]
    lost = []
    for line in lines:
        if line in have or _unlabelled(line) in have:
            continue
        pieces = [_norm(p) for p in sentences_of(_unlabelled(line))]
        if all(_carried(p, have) for p in pieces):
            continue
        lost.append(line)
    return lost


def _carried(sentence: str, have: set[str]) -> bool:
    """One item, or one item per clause when their writer cut at semicolons.

    ET-26776's "Cymetica is the engine; Tuatara discovers; ..." came back as
    four items: every word kept, only the ";" gone. That drops nothing, so it
    is not what REPLY-0021's "nothing is ever dropped" is about. A cut
    anywhere else -- the "e.g." cut -- is still a loss.
    """
    if sentence in have:
        return True
    clauses = [_norm(c) for c in sentence.split(";")]
    return len(clauses) > 1 and all(c and c in have for c in clauses)


# The message log stores at most this many characters of a body and cuts the
# rest without a marker: ET-27671's two BB-SPEC copies and two of ET-26924's
# end mid-word at exactly 8000 (2026-09-30), while the record's `spec_text`
# held the whole spec. A body of exactly this length may be cut, so it is
# never compared either way (rule 8).
LOG_CAP = 8000


def _may_be_cut(message: dict) -> bool:
    return len(str(message.get("body") or "")) >= LOG_CAP


def judge(record: dict) -> dict:
    """One request's reading: lost lines, missing changes, or why unread.

    The spec compared is the latest BB-SPEC in the log: the text the
    requester accepted. The record's `spec_text` stands in only where the log
    cut that copy at LOG_CAP and `spec_text` continues it word for word --
    it is re-rendered under the CURRENT app name, and on ET-26608 that turned
    the requester's own amendment into 'Rename ... from "Gem Screener" to "Gem
    Screener"' (2026-09-30), so it is not the accepted text wherever it
    differs from the log.
    """
    messages = [m for m in (record.get("messages") or []) if isinstance(m, dict)]
    messages.sort(key=lambda m: str(m.get("at") or ""))
    asked = [m for m in messages if m.get("kind") == "BB-REQUEST"]
    specs = [m for m in messages if m.get("kind") == "BB-SPEC"]
    if not asked:
        return {"state": "unread", "why": "no BB-REQUEST in its log"}
    if not specs:
        return {"state": "unspecced"}
    latest = specs[-1]
    spec = str(latest.get("body") or "")
    if _may_be_cut(latest):
        whole = record.get("spec_text")
        if not (isinstance(whole, str) and len(whole) > len(spec)
                and whole.startswith(spec)):
            return {"state": "unread",
                    "why": f"its logged BB-SPEC is at the log's {LOG_CAP}-"
                           f"character cap and spec_text does not continue it"}
        spec = whole
    changes = [m for m in messages if m.get("kind") == "BB-CHANGE"]
    due = [m for m in changes if str(m.get("at") or "") < str(latest.get("at") or "")]
    pending = len(changes) - len(due)
    if any(_may_be_cut(m) for m in [asked[0], *due]):
        return {"state": "unread",
                "why": f"its request or a BB-CHANGE is at the log's "
                       f"{LOG_CAP}-character cap"}
    request = request_text(asked[0].get("body"),
                           str(record.get("app_name") or ""),
                           spec_name(specs[0].get("body")),
                           spec_name(latest.get("body")),
                           spec_name(spec))
    items, amended = spec_parts(spec)
    if not items:
        return {"state": "unread", "why": "its latest BB-SPEC has no numbered item"}
    missing = [_norm(m.get("body")) for m in due
               if _norm(m.get("body")) and _norm(m.get("body")) not in amended]
    # Since 2026-09-24 (ET-26924) the writer leaves withdrawn and repeated
    # BB-CHANGEs out of the amendments and says how many in a footer. That is
    # accounting, not a loss, but only while the count covers what is
    # missing and never for the newest change, which nothing can have
    # withdrawn.
    said = WITHDRAWN.search(spec)
    newest = _norm(due[-1].get("body")) if due else ""
    older = [c for c in missing if c != newest]
    if said and len(older) <= int(said.group(1)):
        missing = [c for c in missing if c == newest]
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


# --- An idea stays an idea after a BB-CHANGE (2026-10-11) -----------------------------------
#
# A request filed as an idea (`is_idea: true`: an app that does not exist yet, ours to name) gets
# a first BB-SPEC in the new-app wording: "What we will build: <Name>, a new page on EventTrader
# that does what you described ... never anyone else's logos, copy or trademarks". Seen on all four
# ideas that ever got a BB-CHANGE (ET-26776 2026-09-23, ET-26924 09-24, ET-28203 09-28, ET-30773
# 10-10): every BB-SPEC written after the first BB-CHANGE switches to the wording for rebuilding an
# app the requester uses -- "a page on EventTrader that does the job you use <Name> for, with these
# changes ... never <Name>'s logos, copy or trademarks" -- which forbids the name, logo and copy the
# idea is made of. On ET-30773 the requester had to send a second BB-CHANGE to undo it.
#
# JUDGED: the NEWEST idea whose log holds a BB-CHANGE followed by a BB-SPEC. The older ones are
# history, counted in the reason: their specs are frozen, so judging them would hold the row red
# after any fix. So this check passes only on the first idea whose post-change spec keeps the
# new-app wording -- a fix cannot be verified until a new idea gets a BB-CHANGE after it; read
# their fix time before any FAIL goes out. Not asserted: anything else in the spec.

BUILD_LINE = re.compile(r"What we will build:[^\n]*")
REBUILD = re.compile(r"does the job you use (.+?) for\b")
OWN_LOGOS = re.compile(r"never (.+?)'s logos")


def spec_template(spec: str) -> dict:
    """The spec's own wording for what it builds: `new` ("a new page on EventTrader"), `rebuild`
    ("does the job you use X for"), or None; and the name whose logos it forbids, if not "anyone
    else"."""
    line = BUILD_LINE.search(str(spec or ""))
    line = line.group(0) if line else ""
    kind = "rebuild" if REBUILD.search(line) else ("new" if "a new page on EventTrader" in line else None)
    forbids = OWN_LOGOS.search(str(spec or ""))
    forbids = forbids.group(1) if forbids and forbids.group(1).strip().lower() != "anyone else" else None
    return {"kind": kind, "forbids": forbids}


def idea_after_a_change(record: dict) -> dict | None:
    """An idea's specs before and after its first BB-CHANGE. None when it is not an idea, or has no
    BB-CHANGE followed by a BB-SPEC. `switched` when a post-change spec uses the rebuild wording or
    forbids the idea's own logos."""
    if not (record or {}).get("is_idea"):
        return None
    messages = sorted((m for m in record.get("messages") or [] if isinstance(m, dict)),
                      key=lambda m: str(m.get("at") or ""))
    changes = [m for m in messages if m.get("kind") == "BB-CHANGE"]
    if not changes:
        return None
    first_change = str(changes[0].get("at") or "")
    before = [m for m in messages if m.get("kind") == "BB-SPEC" and str(m.get("at") or "") < first_change]
    after = [m for m in messages if m.get("kind") == "BB-SPEC" and str(m.get("at") or "") >= first_change]
    if not after:
        return None
    said = [spec_template(m.get("body")) for m in after]
    bad = [s for s in said if s["kind"] == "rebuild" or s["forbids"]]
    return {"ticket": record.get("ticket"), "app_name": record.get("app_name"), "first_change_at": first_change,
            "before": [spec_template(m.get("body")) for m in before], "after": said, "switched": bool(bad),
            "example": bad[0] if bad else None,
            # Neither wording read: not the new-app one this check passes on (deep pass 2026-10-11, C02).
            "unread_wording": not bad and any(s["kind"] != "new" for s in said)}


def newest_verdict(judged: list[dict], unread: list[str]) -> tuple[str, dict | None]:
    """("passed" | "failed" | "inconclusive", the newest judged idea). An idea whose record did not
    read may be the newest, so with one unread no verdict rests on the others: the frozen history
    would be judged in its place, a FAIL after their fix (rule 8; deep pass 2026-10-11, C03). And a
    newest spec in neither wording is unread, not passed (C02)."""
    if not judged:
        return "inconclusive", None
    newest = sorted(judged, key=lambda s: s["first_change_at"])[-1]
    if unread:
        return "inconclusive", newest
    if newest["switched"]:
        return "failed", newest
    if newest.get("unread_wording"):
        return "inconclusive", newest
    return "passed", newest


@qa(component="rest.build_it_better", tier=SafetyTier.SAFE, surface="rest",
    claim="build-it-better-idea-keeps-the-new-app-spec-after-a-change")
def test_an_idea_keeps_its_new_app_spec_after_a_change(rest_anon):
    """The newest idea with a BB-CHANGE: its post-change BB-SPEC still builds a new app."""
    board = rest_anon.get(BOARD)
    if board.status_code != 200:
        raise Inconclusive(f"{BOARD} answered HTTP {board.status_code}; a failed read is not an empty board")
    try:
        items = (board.json() or {}).get("items") or []
    except ValueError:
        raise Inconclusive(f"{BOARD} answered 200 with a body that is not JSON")
    ideas = [i for i in items if isinstance(i, dict) and i.get("is_idea") is True and i.get("ticket")]
    if not ideas:
        raise Inconclusive(f"{BOARD} lists no idea ({len(items)} requests)")
    judged, unread = [], []
    for item in ideas:
        one = rest_anon.get(f"{BOARD}/{item['ticket']}")
        if one.status_code != 200:
            unread.append(f"{item['ticket']} (HTTP {one.status_code})")
            continue
        try:
            said = idea_after_a_change(one.json() or {})
        except ValueError:
            unread.append(f"{item['ticket']} (not JSON)")
            continue
        if said:
            said["ticket"] = said["ticket"] or item["ticket"]
            said["app_name"] = said["app_name"] or item.get("app_name")
            judged.append(said)
    if not judged:
        raise Inconclusive(f"none of {len(ideas)} ideas has a BB-SPEC written after a BB-CHANGE; unread {unread}")
    judged.sort(key=lambda s: s["first_change_at"])
    verdict, newest = newest_verdict(judged, unread)
    if verdict == "inconclusive":
        raise Inconclusive(
            f"{len(unread)} idea record(s) did not read and any may be the newest: {unread[:6]}" if unread else
            f"the newest idea with a BB-CHANGE, {newest['ticket']}, has a spec after it in neither wording "
            f"({[a['kind'] for a in newest['after']]}); nothing is passed on a spec this check cannot read")
    switched = [s for s in judged if s["switched"]]

    def said(s) -> str:
        ex = s["example"] or {}
        return (f"{s['ticket']} ({s['app_name']}, first BB-CHANGE {s['first_change_at'][:16]} UTC): before it "
                f"{[b['kind'] for b in s['before']]}, after it {[a['kind'] for a in s['after']]}"
                + (f", forbidding \"{ex['forbids']}'s logos\"" if ex.get("forbids") else ""))

    conclude(Measurement(
        verdict=verdict,
        reason=(f"the newest idea with a BB-CHANGE, {said(newest)}: its spec after the change builds \"a page on "
                f"EventTrader that does the job you use {newest['app_name']} for\" instead of a new page. "
                f"{len(switched)} of {len(judged)} ideas with a BB-CHANGE switched the same way: "
                + "; ".join(said(s) for s in judged if s is not newest)
                if newest["switched"] else
                f"the newest idea with a BB-CHANGE, {said(newest)}, keeps the new-app wording after it "
                f"({len(switched)} of {len(judged)} older ideas switched, history)"),
        left={"newest_switched": newest["switched"], "ideas_switched": len(switched), "ideas_judged": len(judged)},
        right={"newest_switched": False},
        population={"judged": judged, "ideas_on_board": [i["ticket"] for i in ideas], "unread": unread},
        sources={"board": BOARD, "record": f"{BOARD}/{{ticket}}",
                 "contract": "the first BB-SPEC of an idea: '<Name>, a new page on EventTrader that does what "
                             "you described ... never anyone else's logos, copy or trademarks'"},
        claim_id="build-it-better-idea-keeps-the-new-app-spec-after-a-change"))

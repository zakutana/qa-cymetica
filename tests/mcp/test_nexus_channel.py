"""NEX: the channel their own CEO points agents at has to work.

Cymetica's pitch is that an agent talks to their AI and the AI says what to do
— their chief executive put it to the operator in one line, and the operator
made it this project's standing instruction on 2026-09-10. That promotes
`ask_nexus_deep` from a support tool to the load-bearing part of the platform,
and nothing had ever called it.

Two things are asserted here, and both came out of the first two questions
ever put through it.

**The tools it names must exist.** Asked how an agent should pick its first
event card, Nexus answered with a method, evidence and caveats — and told the
agent to call `get_event_card_info` and `backtest_event_card_idea`, quoting
concrete figures from the second one (+33.77%, Sharpe 3.53, max drawdown
10.13%, "fees applied, 90 points"). Neither tool exists. `tools/list` and
`/.well-known/mcp.json` publish the same 62 tools, not one of which mentions a
card, and a direct call to either name returns `TOOL_NOT_FOUND`. An agent
following the platform's own guidance cannot act on it.

That is worth a check rather than a one-off report because it will recur: the
answer is generated per question, so the next one can name a different tool
that does not exist, and only a machine reading every answer will notice.

**And it must answer inside the window it publishes.** The tool's own
description says an investigation "typically takes 1-5 minutes". Of the first
two, one failed after 2m41s with *"could not be completed right now. Please
retry, or ask the standard chat"* — the programmatic channel sending an agent
to the human web page — and one answered in 1.9 minutes. Both are recorded
with every poll's moment, so this reads a history rather than one sample.

Neither check re-asks: a deep investigation costs minutes of their compute,
and a test suite that starts one on every run is a test suite that gets rate
limited. They read what `scripts/nexus.py` recorded, and say so when there is
nothing recorded yet.
"""

from __future__ import annotations

import importlib.util
import re
from datetime import datetime
from pathlib import Path

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude


def _moment(value):
    """An ISO timestamp, or None. Never raises: an unreadable moment is a
    reason to be inconclusive, not a reason for this file to error."""
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None

REPO = Path(__file__).resolve().parent.parent.parent

# Anchor on the markup AND on a calling context. Reading either alone is wrong
# in a different direction, and this file has now made both mistakes.
#
# Bare snake_case in prose collects field names, endpoint fragments and half
# the answer -- the mistake that once put a field name that exists nowhere into
# a report. But requiring the literal word "MCP" before the backticks, which is
# what this did until 2026-09-10, read ZERO tools out of two of the three
# answers we hold: NEX-0008 says "resolve the chain with `find_trade_path`" and
# NEX-0007 names seven, none of them prefixed. The check reported a clean
# channel because it could not see what the channel said. Found by a
# check-auditor, confirmed 3/3.
#
# So: a backticked identifier counts when it is prefixed with MCP, carries a
# call signature, follows a calling verb, or is called "the ... tool". Measured
# against the three recorded answers, that reads tools out of all three.
NAME = r"([a-z][a-z0-9]*(?:_[a-z0-9]+)+)"
CALLING_VERBS = ("call", "calls", "calling", "use", "uses", "using", "invoke",
                 "invoking", "run", "running", "query", "querying", "hit")
TOOL_MENTIONS = (
    re.compile(r"MCP\s+`" + NAME + r"(?:\([^`]*\))?`"),
    re.compile(r"`" + NAME + r"\([^`]*\)`"),
    re.compile(r"\b(?:" + "|".join(CALLING_VERBS) + r")\s+(?:the\s+)?`" + NAME
               + r"(?:\([^`]*\))?`", re.I),
    re.compile(r"`" + NAME + r"`\s+tool\b"),
)
# The underscore is not a guess: all 65 tools they publish carry one, and the
# check asserts that before relying on it. It is what keeps `status` and `bear`
# -- both of which sit in a calling phrase in NEX-0007 -- out of a report as
# tools that do not exist.
#
# with / via / through are how NEX-0008 named a real tool ("resolve the chain
# with `find_trade_path`"), and also how an answer names a FIELD: "filter
# with `is_public`" made is_public a tool that does not exist until the deep
# pass of 2026-09-11 (V08, triage 3/3). After those three a name counts only
# when it is shaped like a tool -- a verb first, as every tool they serve is.
WEAK_VERBS = ("with", "via", "through")
TOOL_VERBS = frozenset({
    "get", "list", "find", "search", "lookup", "fetch", "place", "cancel",
    "create", "update", "delete", "set", "start", "stop", "trade", "buy", "sell",
    "open", "close", "clone", "fund", "toggle", "withdraw", "deposit",
    "backtest", "simulate", "estimate", "quote", "preview", "compute",
    "calculate", "analyze", "analyse", "compare", "scan", "track", "check",
    "verify", "identify", "resolve", "describe", "explain", "ask", "send",
    "submit", "register", "query", "run", "who"})
WEAK_MENTION = re.compile(r"\b(?:" + "|".join(WEAK_VERBS) + r")\s+(?:the\s+)?`"
                          + NAME + r"(?:\([^`]*\))?`", re.I)


def tool_mentions(text: str) -> set[str]:
    found = {m for pattern in TOOL_MENTIONS for m in pattern.findall(text or "")}
    found |= {m for m in WEAK_MENTION.findall(text or "")
              if m.split("_", 1)[0] in TOOL_VERBS}
    return found


def _nexus():
    spec = importlib.util.spec_from_file_location(
        "nexus_channel", REPO / "scripts" / "nexus.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def newest_answer_naming_tools(answers):
    """The last answer that told an agent to call something, or None.

    The newest that NAMES a tool, not simply the newest: Nexus answers about
    fees or caveats name none, and reading those as "nothing to measure"
    would make the check go Inconclusive for a reason that is not about the
    vendor at all.

    Why not all of them, which is what this read until the 2026-09-10 sweep:
    the union across every answer ever recorded can only grow. Its one
    offender, `update_bot_settings`, was named in NEX-0002 at 10:23 -- before
    their 12:37 release -- and became visible to us only when the deep pass
    widened the mention extractor that morning, from 3 tools to 8. So the
    `fail` verify.py sent at 16:52 was our own better reading of an old
    answer, three hours after we had told them on telegram that a fresh
    answer named only served tools. Both were computed honestly. They
    contradict each other because one read the newest answer and the other
    read all of them.
    """
    dated = [r for r in answers if r.get("text")]
    dated.sort(key=lambda r: (r.get("at") or "", r.get("id") or ""))
    for row in reversed(dated):
        if tool_mentions(row["text"]):
            return row
    return None


def latest_per_question(rows):
    """Every question's last finished row, in the order those rows were written.

    One question, one verdict. `nexus.py answer` re-polls a question it has
    already given up on and writes a give-up row of its own when the job is
    still failed: on 2026-09-11 a manual re-poll of NEX-0020 wrote a second
    one, and the window of five counted that question twice -- the fail about
    to go to them on #86 would have said four of five had not answered when
    three had. A question given up on and answered later answered, late, so
    its last row is its verdict.

    Ordered by when each question was ASKED -- its question row, or its first
    finished row where the file holds no question -- and not by that last row.
    Ordering by the last row put a re-polled old question at the newest end of
    the window: the deep pass of 2026-09-11 found that the very re-poll this
    docstring describes would push a recent answer out of the five. Triage 3/3.
    """
    asked = {r["id"]: str(r.get("at") or "") for r in rows
             if r.get("type") == "question" and r.get("id")}
    first: dict[str, str] = {}
    last = {}
    for row in rows:
        if row.get("type") in ("answer", "gave_up") and row.get("id"):
            first.setdefault(row["id"], str(row.get("at") or ""))
            last[row["id"]] = row
    return sorted(last.values(),
                  key=lambda row: asked.get(row["id"]) or first[row["id"]])


def did_not_answer(row) -> bool:
    """Whether a finished row says THEIR channel failed to answer.

    Two shapes, and the difference is whose side broke.

    THEIRS: a give-up whose status is `failed` -- their job ended without an
    answer -- and a give-up whose status is `running`, `queued` or `pending`,
    which is what `nexus.py` writes at GIVE_UP_SECONDS when their job is still
    working. Fifteen minutes of still-running against a published ceiling of
    five is their channel not answering, however politely the status reads.

    OURS: `unread: ReadTimeout`, `unknown`, `error: ...`. A give-up written
    because our own reads failed says nothing about their channel, and until
    the deep pass of 2026-09-11 it counted as "did not answer".

    The second clause was missing until 2026-09-12 and is the whole of B01:
    with every stalled give-up filed as ours, five questions abandoned at 3x
    the ceiling left nothing in the population at all and the check reported a
    PASS to their server on #86. Triage 3/3.
    """
    if row.get("type") != "gave_up":
        return False
    status = str(row.get("status") or "")
    return status.startswith("failed") or status in _nexus().RUNNING


PUBLISHES_A_WINDOW = re.compile(r"(\d+)\s*[-–]\s*(\d+)\s*minute", re.IGNORECASE)


def their_published_window(tools=None):
    """The window THEY publish, read off their own tool description.

    `(low, high)` in minutes, or None when their label cannot be read -- and a
    label we could not read is not a label that moved (rule 8).

    The ceiling this check judges against is `nexus.PUBLISHED_MINUTES`, the
    numbers transcribed into our own file on 2026-09-10, while `sources` told
    the vendor the contract was their tool description. Nothing reconciled the
    two: `qa/surface.py` deliberately does not watch prose, because they
    reword it. So if they relabel the tool 5-15 minutes, a seven-minute answer
    reads as late and a FAIL goes to their tracker on #86 for behaviour inside
    their own published window -- the false-claim-to-the-vendor class, with
    their own words quoted as the thing they broke. Three readers, 2026-09-12.

    Read from `audits/surface.json`, which is the newest acknowledged reading
    of `tools/list`, so this costs no call and stays offline like the rest of
    the check. A disagreement is INCONCLUSIVE, never a defect and never a
    silent adoption: their number moving is our check changing (rule 5), and
    that wants a transcription and a re-pin, not a comparison that quietly
    re-aims itself.
    """
    import json

    if tools is None:
        # THEIR words, from a capture of tools/list, not from our own
        # acknowledgement file. `audits/surface.json` is only rewritten when
        # the operator runs `surface --update`, and that is only prompted by
        # `tools_drift`, which compares parameter SHAPE and deliberately not
        # descriptions -- so a relabel to "typically 5-15 minutes" produces no
        # drift, no update, and this check keeps reading the 1-5 we
        # transcribed while quoting it to them on #86. That is the incident
        # this docstring says it prevents, one level further back. A01, deep
        # pass of 2026-09-13, triage 3/3.
        try:
            from qa.surface import tools_seen

            tools = tools_seen()
        except Exception:  # noqa: BLE001 -- a failed read is not an answer
            tools = None
        if tools is None:
            # Nothing captured recently. Fall back to the acknowledged copy,
            # which is at least a reading of their words rather than a guess,
            # and which the caller treats as inconclusive when it disagrees.
            path = REPO / "audits" / "surface.json"
            if not path.is_file():
                return None
            try:
                tools = (json.loads(path.read_text(encoding="utf-8"))
                         or {}).get("tools")
            except (OSError, json.JSONDecodeError):
                return None
    for tool in tools or []:
        if not isinstance(tool, dict) or tool.get("name") != "ask_nexus_deep":
            continue
        found = PUBLISHES_A_WINDOW.search(str(tool.get("description") or ""))
        if found:
            return int(found.group(1)), int(found.group(2))
        # The tool WAS read and its label states no N-M window. That is not a
        # read that failed -- it is their label having moved to a shape we do
        # not parse ("usually under 10 minutes"), and returning None for it
        # let #86 judge by the transcribed 1-5 and send a FAIL for an answer
        # their new words may allow (C01, deep pass of 2026-09-19, 2/3).
        return "unstated"
    return None


def open_past_the_ceiling(rows, ceiling_s: float) -> list[dict]:
    """Questions with no answer and no give-up whose own polls SAW them still
    waiting past the ceiling -- as a give-up row carrying the status seen.

    Since their deep lane queues at capacity (REPLY-0019) the laboratory looks
    once per tick and writes no give-up while a job waits, so such a question
    had no finishing row, never entered the window, and the window judged the
    five before it (V01, deep pass of 2026-09-19, 3/3). Only a poll past the
    ceiling counts: a job two minutes in is early, not late.
    """
    running = _nexus().RUNNING
    asked = {r["id"]: r.get("at") for r in rows
             if r.get("type") == "question" and r.get("id")}
    done = {r["id"] for r in rows
            if r.get("type") in ("answer", "gave_up") and r.get("id")}
    newest: dict[str, dict] = {}
    for row in rows:
        qid = row.get("id")
        if row.get("type") == "poll" and qid in asked and qid not in done:
            newest[qid] = row
    out = []
    for qid, poll in newest.items():
        status = str(poll.get("status") or "")
        first, seen = _moment(asked[qid]), _moment(poll.get("at"))
        if status not in running or first is None or seen is None:
            continue
        if (seen - first).total_seconds() > ceiling_s:
            out.append({"id": qid, "type": "gave_up", "status": status,
                        "at": poll.get("at"), "still_open": True})
    return out


def read_the_window(rows, finished):
    """What the polls can PROVE about the last few investigations.

    Separate from the check body so the false green of 2026-09-12 has
    something a meta test can hold. Every list here is evidence, never an
    absence read as one:

      failed   their job ended in failure
      stalled  their job was still running past the ceiling when we stopped
      late     an ANSWER whose polls saw it running past the ceiling
      ours     a give-up our own reads produced -- named, never counted
      measured the ids this window says anything about at all. Empty means
               inconclusive, which is not a pass.
    """
    nexus = _nexus()
    ceiling_verdict = {r["id"]: nexus.bounds_verdict(
        *nexus.latency_bounds(rows, r["id"])) for r in finished
        if r.get("type") == "answer" or did_not_answer(r)}

    def over(rows_in):
        return sorted(((r["id"], nexus.latency_bounds(rows, r["id"])[0] or 0.0)
                       for r in rows_in if ceiling_verdict.get(r["id"]) == "OVER"),
                      key=lambda pair: pair[1], reverse=True)

    theirs = [r for r in finished if did_not_answer(r)]
    read = {
        "verdicts": ceiling_verdict,
        "failed": [(r["id"], (r.get("error") or r.get("status") or "")[:80])
                   for r in theirs
                   if str(r.get("status") or "").startswith("failed")],
        "stalled": over([r for r in theirs
                         if not str(r.get("status") or "").startswith("failed")]),
        "late": over([r for r in finished if r.get("type") == "answer"]),
        # Give-ups that say our own reads failed: named in the population,
        # never counted against their channel (V04, deep pass of 2026-09-11).
        "ours": [r["id"] for r in finished
                 if r.get("type") == "gave_up" and not did_not_answer(r)],
        "measured": sorted(i for i, v in ceiling_verdict.items() if v != "unknown"),
        "unmeasured": sorted(i for i, v in ceiling_verdict.items() if v == "unknown"),
        "within": sorted(i for i, v in ceiling_verdict.items() if v == "within"),
    }
    # The decision, not the ingredients. It lives here rather than in the body
    # because a test that asserts an ingredient leaves the branch free to move
    # -- which is C05, found in the same hour and the same pass.
    read["proves_nothing"] = not (read["failed"] or read["late"]
                                  or read["stalled"] or read["measured"])
    return read


def labelled(text: str, tool: str) -> bool:
    """Does their own marker follow this tool's name?

    REPLY-0034, 2026-09-20: a chat-lane answer that tells the reader to call a
    tool living only in NEXUS's own toolbelt now carries
    `[NEXUS runs this for you on request; it is not an MCP tool]` after the
    name. Their fix does not stop NEXUS recommending those tools -- they said
    so plainly -- so the label is the whole of what changed, and an
    unreachable name that carries it is the fix working rather than the
    defect it repairs.

    Read within a short window after the name and not anywhere in the answer:
    one label at the bottom of a page must not excuse every mention above it.
    Matched on the two halves that carry the meaning rather than the sentence
    verbatim, so their punctuation may move without this going red.
    """
    window = 220
    for match in re.finditer(re.escape(tool), text or ""):
        tail = (text or "")[match.end():match.end() + window].lower()
        if "not an mcp tool" in tail and "nexus runs this" in tail:
            return True
    return False


@qa(component="mcp.tools_call", tier=SafetyTier.SAFE, surface="mcp")
def test_every_tool_nexus_tells_an_agent_to_call_exists(mcp_trusted):
    """Guidance an agent cannot act on is guidance that does not work."""
    nexus = _nexus()
    answers = [r for r in nexus.load() if r.get("type") == "answer" and r.get("text")]
    if not answers:
        raise Inconclusive(
            "no Nexus answer has been recorded, so there is nothing to read; "
            "`python scripts/nexus.py ask \"...\"` records one")

    latest = newest_answer_naming_tools(answers)
    if latest is None:
        raise Inconclusive(
            f"{len(answers)} recorded answer(s) name no MCP tool at all, so "
            f"whether the tools it names exist could not be measured")
    named = {tool: latest["id"] for tool in tool_mentions(latest["text"])}

    served = {t["name"] for t in mcp_trusted.tools_list() if "name" in t}
    if not served:
        raise Inconclusive(
            "tools/list returned no tool names, so nothing could be compared "
            "against it -- a failed read is not an empty catalogue")

    # The rule the extractor rests on, checked rather than assumed. Every name
    # they publish is multi-segment; if that stops being true, a single-word
    # tool would be invisible to us and this says so instead of narrowing in
    # silence.
    single = sorted(n for n in served if "_" not in n)
    if single:
        raise Inconclusive(
            f"the tool namespace now carries single-word names ({single[:5]}), "
            f"which the mention extractor deliberately does not match -- it "
            f"would collect field names. Widen it before trusting this result")

    # Their fix of 2026-09-20 (REPLY-0034) does not stop NEXUS naming a tool
    # of its own; it LABELS one the reader cannot call. So an unreachable name
    # is only a defect when it is unlabelled -- and a check that did not know
    # that would read their fix as the defect it repairs, which is the
    # `a-check-encodes-the-fix-its-author-imagined` failure, three times in
    # one day on 2026-09-07. Labelled names are counted and named in the
    # reason instead, because a label appearing at all is what their fix
    # working looks like from outside.
    missing = sorted(name for name in named
                     if name not in served and not labelled(latest["text"], name))
    marked = sorted(name for name in named
                    if name not in served and labelled(latest["text"], name))

    conclude(Measurement(
        verdict="failed" if missing else "passed",
        reason=(f"Nexus told an agent to call {', '.join(missing)}, and the "
                f"server serves {len(served)} tools, none of them by that "
                f"name: an agent following the platform's own guidance cannot "
                f"act on it"
                if missing else
                f"every one of the {len(named)} tool(s) Nexus named is served"
                + (f"; {len(marked)} it names are not on MCP and each carries "
                   f"their label saying so ({', '.join(marked)})"
                   if marked else "")),
        # Not the same list twice: what Nexus named, against the ones of
        # those the server actually serves -- which is the empty set, and
        # saying so is the finding.
        left=sorted(named), right=sorted(set(named) & served),
        population={"answers_recorded": len(answers), "subject": latest["id"],
                    "subject_at": latest.get("at"),
                    "tools_served": len(served)},
        sources={"answers": str(nexus.path().name),
                 "tools": "POST /mcp/v1 tools/list"},
    ))


@qa(component="mcp.tools_call", tier=SafetyTier.SAFE, surface="mcp")
def test_a_deep_investigation_answers_inside_the_window_it_publishes():
    """Their number, not ours: the tool says 1-5 minutes on its own label.

    **Timed from the question's own timestamp, not from `waited_seconds`.**
    That field was a stopwatch started when a POLL LOOP was entered, and
    `nexus.py answer` enters a second one -- so an investigation asked at
    10:00, given up on at 10:15 and picked up at 11:00 recorded an answer with
    `waited_seconds` around zero. The data already shows it: NEX-0001 was asked
    at 10:03:06 and its give-up row at 10:28:33 carries 0.0, and NEX-0005 the
    same. Five such rows would have slid the give-ups out of the window and let
    this check report a channel that took an hour as inside their published
    five minutes -- while #86 is FIX_CLAIMED and verifications on this nodeid
    already go to their server.

    The two timestamps cannot restart. They also re-derive the truth for rows
    already written, which a corrected stopwatch alone would not: the fix is in
    `nexus.py` too, but nothing can go back and re-time NEX-0001.

    Found by a check-auditor and confirmed by all three triage readers.
    """
    nexus = _nexus()
    rows = nexus.load()
    asked_at = {r["id"]: r.get("at") for r in rows if r.get("type") == "question"}

    def elapsed(row) -> float | None:
        """Seconds between the question and this row, or None if unreadable."""
        first, last = _moment(asked_at.get(row.get("id"))), _moment(row.get("at"))
        if first is None or last is None:
            return None
        return round((last - first).total_seconds(), 1)

    low, high = nexus.PUBLISHED_MINUTES
    # A question still waiting past their ceiling, seen by a poll, is in the
    # window as what it is -- unanswered -- rather than left out of it (V01).
    rows = rows + open_past_the_ceiling(rows, high * 60)
    finished = latest_per_question(rows)
    if not finished:
        raise Inconclusive(
            "no investigation has finished, so its latency could not be read")

    unreadable = [r["id"] for r in finished[-5:] if elapsed(r) is None]
    if unreadable:
        # Rule 8. A row whose two timestamps cannot be read is not a fast one.
        raise Inconclusive(
            f"{unreadable} carry no readable question timestamp, so how long "
            f"they took cannot be measured -- and an unmeasured latency is not "
            f"a latency inside the window")

    # The MOST RECENT few, not everything ever recorded. A reliability check
    # that reads all history can never go green again: today's failures would
    # pin it red through any fix they ship, which is the badge nobody can
    # clear. New evidence displaces old, and a channel that has answered its
    # last five is a channel that works now.
    WINDOW = 5
    finished = finished[-WINDOW:]

    theirs = their_published_window()
    if theirs == "unstated":
        raise Inconclusive(
            f"their ask_nexus_deep label no longer states an N-M minute window "
            f"this check can read, and it judges against {low}-{high} "
            f"transcribed into scripts/nexus.py. Re-read their label, "
            f"re-transcribe PUBLISHED_MINUTES and re-pin; until then a verdict "
            f"here would quote a window they may no longer publish (C01)")
    if theirs is not None and theirs != (low, high):
        # Their label moved. Rule 5: a moved ceiling is a changed check, not a
        # missed deadline -- and the alternative, adopting their new number
        # here, would re-aim the check without anybody deciding to.
        raise Inconclusive(
            f"their tool now publishes {theirs[0]}-{theirs[1]} minutes and "
            f"this check judges against {low}-{high}, transcribed into "
            f"scripts/nexus.py. Re-transcribe PUBLISHED_MINUTES and re-pin the "
            f"check; until then a verdict here would quote their own words for "
            f"a window they no longer publish")
    # Bounds, not one number. The answer row's `at` is when WE looked, so a
    # question asked with --no-wait and picked up fourteen minutes later
    # "took" fourteen minutes by that reading -- which is how NEX-0009, done
    # in 155 s by their job table, became a late answer we reported to them.
    # A job is late only if a poll SAW it still running past the ceiling; a
    # first look that finds it done proves only an upper bound.
    read = read_the_window(rows, finished)
    failed, late, stalled = read["failed"], read["late"], read["stalled"]
    ours, unmeasured = read["ours"], read["unmeasured"]

    trouble = []
    if failed:
        trouble.append(f"{len(failed)} of {len(finished)} did not answer at "
                       f"all ({failed[0][0]}: {failed[0][1]})")
    if late:
        # Sorted, because this said "worst" while rendering whichever late
        # answer happened to come first in the file.
        trouble.append(f"{len(late)} answered later than the published "
                       f"{high} min (worst {late[0][0]} still running at {late[0][1]:.0f}s)")
    if stalled:
        # "still unfinished", not "still running": since REPLY-0019 a job at
        # capacity is QUEUED, and the status seen is on each row (V01).
        seen = sorted({str(r.get("status")) for r in finished
                       if r.get("id") in {qid for qid, _ in stalled}})
        trouble.append(f"{len(stalled)} were still unfinished "
                       f"({'/'.join(seen)}) past the published {high} min at "
                       f"our last look (worst {stalled[0][0]} at "
                       f"{stalled[0][1]:.0f}s)")

    if read["proves_nothing"]:
        # Nothing about their channel was measured, and an unmeasured channel
        # is not a channel inside its window. Two shapes reach here: every
        # answer first looked at after it had finished, and a window of pure
        # read failures -- which until 2026-09-12 slipped past a guard that
        # required a non-empty verdict map, and reported "0 investigation(s)
        # answered inside the published 1-5 min" as a PASS on #86.
        raise Inconclusive(
            f"nothing in the window ({', '.join(unmeasured + ours) or 'empty'}) "
            f"measures their channel: an answer first looked at after it had "
            f"finished proves only an upper bound, and a give-up our own reads "
            f"produced proves nothing at all -- poll from the start, or this "
            f"run proves nothing either way")

    conclude(Measurement(
        verdict="failed" if trouble else "passed",
        reason=("; ".join(trouble) if trouble else
                f"{len(read['within'])} investigation(s) answered "
                f"inside the published {low}-{high} min, bounded by polls"
                + (f"; {len(unmeasured)} were only looked at after finishing "
                   f"({', '.join(unmeasured)}), so their latency is an upper "
                   f"bound and counts neither way" if unmeasured else "")),
        left=[elapsed(r) for r in finished],
        right=high * 60,
        population={"window": WINDOW, "finished": len(finished),
                    "failed": len(failed), "late": len(late),
                    "stalled": len(stalled), "our_read_failed": ours,
                    "timed_from": "question timestamp, not the poll stopwatch"},
        sources={"contract": (
                     f"ask_nexus_deep tool description, {low}-{high} min, "
                     + ("re-read from audits/surface.json and agreeing with "
                        "scripts/nexus.py::PUBLISHED_MINUTES"
                        if theirs is not None else
                        "transcribed as scripts/nexus.py::PUBLISHED_MINUTES; "
                        "their label could not be re-read this run")),
                 "timeline": str(nexus.path().name)},
    ))

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
                 "invoking", "run", "running", "query", "querying", "hit",
                 "with", "via", "through")
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


def tool_mentions(text: str) -> set[str]:
    return {m for pattern in TOOL_MENTIONS for m in pattern.findall(text or "")}


def _nexus():
    spec = importlib.util.spec_from_file_location(
        "nexus_channel", REPO / "scripts" / "nexus.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@qa(component="mcp.tools_call", tier=SafetyTier.SAFE, surface="mcp")
def test_every_tool_nexus_tells_an_agent_to_call_exists(mcp_trusted):
    """Guidance an agent cannot act on is guidance that does not work."""
    nexus = _nexus()
    answers = [r for r in nexus.load() if r.get("type") == "answer" and r.get("text")]
    if not answers:
        raise Inconclusive(
            "no Nexus answer has been recorded, so there is nothing to read; "
            "`python scripts/nexus.py ask \"...\"` records one")

    named: dict[str, str] = {}
    for row in answers:
        for tool in tool_mentions(row["text"]):
            named.setdefault(tool, row["id"])
    if not named:
        raise Inconclusive(
            f"{len(answers)} recorded answer(s) name no MCP tool at all, so "
            f"whether the tools it names exist could not be measured")

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

    missing = sorted(name for name in named if name not in served)

    conclude(Measurement(
        verdict="failed" if missing else "passed",
        reason=(f"Nexus told an agent to call {', '.join(missing)}, and the "
                f"server serves {len(served)} tools, none of them by that "
                f"name: an agent following the platform's own guidance cannot "
                f"act on it"
                if missing else
                f"every one of the {len(named)} tool(s) Nexus named is served"),
        # Not the same list twice: what Nexus named, against the ones of
        # those the server actually serves -- which is the empty set, and
        # saying so is the finding.
        left=sorted(named), right=sorted(set(named) & served),
        population={"answers_read": len(answers), "tools_served": len(served)},
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

    finished = [r for r in rows if r.get("type") in ("answer", "gave_up")]
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

    low, high = nexus.PUBLISHED_MINUTES
    ceiling = high * 60
    late = sorted(
        ((r["id"], elapsed(r)) for r in finished
         if r.get("type") == "answer" and elapsed(r) > ceiling),
        key=lambda pair: pair[1], reverse=True)
    failed = [(r["id"], (r.get("error") or r.get("status") or "")[:80])
              for r in finished if r.get("type") == "gave_up"]

    trouble = []
    if failed:
        trouble.append(f"{len(failed)} of {len(finished)} did not answer at "
                       f"all ({failed[0][0]}: {failed[0][1]})")
    if late:
        # Sorted, because this said "worst" while rendering whichever late
        # answer happened to come first in the file.
        trouble.append(f"{len(late)} answered later than the published "
                       f"{high} min (worst {late[0][0]} at {late[0][1]:.0f}s)")

    conclude(Measurement(
        verdict="failed" if trouble else "passed",
        reason=("; ".join(trouble) if trouble else
                f"all {len(finished)} investigation(s) answered inside the "
                f"published {low}-{high} min, timed from the question"),
        left=[elapsed(r) for r in finished],
        right=ceiling,
        population={"window": WINDOW, "finished": len(finished),
                    "failed": len(failed), "late": len(late),
                    "timed_from": "question timestamp, not the poll stopwatch"},
        sources={"contract": "ask_nexus_deep tool description",
                 "timeline": str(nexus.path().name)},
    ))

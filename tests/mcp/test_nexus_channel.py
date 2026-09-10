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
from pathlib import Path

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

REPO = Path(__file__).resolve().parent.parent.parent

# Anchor on the markup, read the name from it: Nexus writes an MCP tool as the
# word MCP followed by a backticked identifier, sometimes with a call
# signature. Matching bare snake_case in prose would collect field names,
# endpoint fragments and half the answer -- the mistake that once put a field
# name that exists nowhere into a report.
TOOL_MENTION = re.compile(r"MCP\s+`([a-z][a-z0-9_]{3,})(?:\([^`]*\))?`")


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
        for tool in TOOL_MENTION.findall(row["text"]):
            named.setdefault(tool, row["id"])
    if not named:
        raise Inconclusive(
            f"{len(answers)} recorded answer(s) name no MCP tool at all, so "
            f"whether the tools it names exist could not be measured")

    served = {t["name"] for t in mcp_trusted.tools_list() if "name" in t}
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
    """Their number, not ours: the tool says 1-5 minutes on its own label."""
    nexus = _nexus()
    rows = nexus.load()
    finished = [r for r in rows if r.get("type") in ("answer", "gave_up")]
    if not finished:
        raise Inconclusive(
            "no investigation has finished, so its latency could not be read")

    low, high = nexus.PUBLISHED_MINUTES
    ceiling = high * 60
    late = [(r["id"], round(r.get("waited_seconds") or 0)) for r in finished
            if r.get("type") == "answer" and (r.get("waited_seconds") or 0) > ceiling]
    failed = [(r["id"], (r.get("error") or r.get("status") or "")[:80])
              for r in finished if r.get("type") == "gave_up"]

    trouble = []
    if failed:
        trouble.append(f"{len(failed)} of {len(finished)} did not answer at "
                       f"all ({failed[0][0]}: {failed[0][1]})")
    if late:
        trouble.append(f"{len(late)} answered later than the published "
                       f"{high} min (worst {late[0][1]}s)")

    conclude(Measurement(
        verdict="failed" if trouble else "passed",
        reason=("; ".join(trouble) if trouble else
                f"all {len(finished)} investigation(s) answered inside the "
                f"published {low}-{high} min"),
        left=[r.get("waited_seconds") for r in finished],
        right=ceiling,
        population={"finished": len(finished), "failed": len(failed),
                    "late": len(late)},
        sources={"contract": "ask_nexus_deep tool description",
                 "timeline": str(nexus.path().name)},
    ))

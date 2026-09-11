"""A tool Nexus tells an agent to call with arguments accepts arguments.

#85 asks whether a tool NEXUS names exists. This asks the next question,
which turned out to be the sharper one: whether the tool it names does what
it says.

Measured 2026-09-11. NEXUS, listing what it thought we should be testing,
described `who_is_this` as an address-identity check with two directions to
exercise: *"An unknown address must return unknown -- never
'phishing'/'fraud'; a genuine per-application escrow (FA-XXXXXX format) must
verify as genuine. Test both ... the false-positive is the one that loses a
user their deposit and is the one nobody tests."*

`who_is_this` is served. Its description is "Learn about the platform
identity and mission" and its inputSchema is `{"type": "object",
"properties": {}}` -- it takes nothing. It returns the same CyMetica identity
object for every call, which is correct, because there is no argument to vary.

No tool on the served surface does address identity at all: none takes an
address-shaped argument for that purpose, and no description mentions scam,
phishing, fraud, legitimate, genuine or verify.

**Why this is worse than a tool that does not exist.** A missing tool fails
loudly -- TOOL_NOT_FOUND, and the agent knows. An agent told to check an
address with `who_is_this` gets `success: true` and a friendly identity
object naming the platform, for an attacker's address as readily as for its
own. It would conclude the address is fine. NEXUS named that exact risk in
the same paragraph and then pointed at a tool that cannot perform the test.

I nearly filed this the other way round. The first reading was "who_is_this
returns an identical answer for every address", which looked like a defect
until I read the schema: no parameters, so my four cases were one call made
four times. The check therefore compares against the SERVED SCHEMA rather
than against response equality.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

REPO = Path(__file__).resolve().parent.parent.parent

# `tool_name(` with something that is not just whitespace before the `)`.
# Conservative on purpose: it wants a call with an argument in it, not a
# mention. An extractor that reaches further is how a pre-release answer
# became a fresh accusation on 2026-09-10.
CALL_WITH_ARGS = re.compile(r"\b([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\(\s*([^)\s][^)]*)\)")


def _nexus():
    spec = importlib.util.spec_from_file_location(
        "nexus_contracts", REPO / "scripts" / "nexus.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def calls_with_arguments(text: str) -> dict[str, str]:
    """tool name -> the argument text Nexus showed being passed to it."""
    out: dict[str, str] = {}
    for name, args in CALL_WITH_ARGS.findall(text or ""):
        out.setdefault(name, args.strip()[:120])
    return out


def served_arguments(tool) -> list[str] | None:
    """The arguments a served tool's schema takes, or None if it does not say.

    None -- not [] -- for a listing with no schema at all, and for a schema
    without `properties` that does not forbid them: neither says the tool
    takes nothing. Only `properties: {}` (or a schema that sets
    additionalProperties false with no properties) does. Until the deep pass
    of 2026-09-11 `inputSchema or {}` read a missing or partial schema as a
    tool that takes no arguments and would have filed it as their defect --
    rule 8 inverted. Triage 3/3.
    """
    schema = tool.get("inputSchema", tool.get("input_schema"))
    if not isinstance(schema, dict):
        return None
    props = schema.get("properties")
    if props is None:
        return [] if schema.get("additionalProperties") is False else None
    return sorted(props) if isinstance(props, dict) else None


@qa(component="mcp.tools_call", tier=SafetyTier.SAFE, surface="mcp")
def test_a_tool_nexus_calls_with_arguments_takes_arguments(mcp_trusted):
    """Guidance that builds a safety control out of a static answer."""
    from tests.mcp.test_nexus_channel import newest_answer_naming_tools

    answers = [r for r in _nexus().load()
               if r.get("type") == "answer" and r.get("text")]
    latest = newest_answer_naming_tools(answers)
    if latest is None:
        raise Inconclusive(
            "no recorded Nexus answer names a tool, so there is no contract "
            "to compare against the served schema")

    described = calls_with_arguments(latest["text"])
    if not described:
        raise Inconclusive(
            f"answer {latest['id']} names tools but shows none of them being "
            f"called with an argument, so what it claims of their contracts "
            f"could not be read")

    served = {}
    for tool in mcp_trusted.tools_list():
        if "name" in tool:
            # None when the schema does not say; only [] takes nothing.
            served[tool["name"]] = served_arguments(tool)
    if not served:
        raise Inconclusive(
            "tools/list returned no schemas, so nothing could be compared -- "
            "a failed read is not an empty catalogue")

    argless = []
    for name, args in sorted(described.items()):
        if name not in served:
            # That a named tool does not exist is #85's question, not this
            # one, and reporting it here would double-count the same defect.
            continue
        # [] only: None is a schema that does not say, and "takes no
        # arguments" is a claim about a schema that does.
        if served[name] == []:
            argless.append({"tool": name, "nexus_passed": args})

    conclude(Measurement(
        verdict="failed" if argless else "passed",
        reason=(
            "Nexus tells an agent to call "
            + ", ".join(f"{a['tool']}({a['nexus_passed']})" for a in argless)
            + f", and the server serves {', '.join(a['tool'] for a in argless)}"
              f" with an empty inputSchema -- it takes no arguments at all, so "
              f"the answer cannot depend on what is passed. A tool that does "
              f"not exist fails loudly; this one returns success and a "
              f"plausible payload for any input"
            if argless else
            f"every one of the {len(described)} tool(s) {latest['id']} calls "
            f"with an argument declares parameters"),
        left=sorted(a["tool"] for a in argless),
        right=sorted(n for n in described if n in served),
        population={"answer": latest["id"], "described": len(described),
                    "served_and_argless": len(argless)},
        sources={"answers": "state/nexus.jsonl",
                 "schemas": "POST /mcp/v1 tools/list"},
    ))

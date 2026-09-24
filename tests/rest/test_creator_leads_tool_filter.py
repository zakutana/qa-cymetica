"""The `tool` filter on the lead queues keeps only that tool's threads --
except when the value it is given matches nothing they know.

`openapi-public.json`'s own parameter description, GET /api/v1/creator/
reddit-leads and GET /api/v1/creator/twitter-leads, `tool` (query, maxLength
120):

    "One queue per tool: a site path such as /pineconnector (or just
    pineconnector) keeps only threads whose best-matching page is that tool.
    Empty = every tool."

The only carve-out for "every tool" is an EMPTY value. A non-empty value that
matches no real site tool is not that carve-out, and no lead's best-matching
page can equal a path that exists nowhere on the site -- so the documented
behaviour for such a value is an empty queue, same as any other tool nothing
currently matches.

**What was seen when this was written.** A known, real, currently-empty tool
(`/coinglass` -- present on the sibling twitter-leads queue, absent from
reddit-leads' own population at the time) correctly returned zero reddit
leads: the "no match" case works when the value is a real site path. A fixed,
never-real value (`/qa-fixture-does-not-exist-1234`) returned the FULL queue
on both endpoints instead -- every lead the account has, regardless of tool,
with dozens of distinct `tool_path` values among them. The same account's
`?tool=/build` (a real, currently populated tool) correctly narrowed to only
`/build` leads, and `?tool=build` (no leading slash, the doc's own
alternative spelling) matched it exactly -- so the parameter is read and a
real value does narrow; only a value that resolves to nothing falls through
to unfiltered rather than to empty. (Also seen, not asserted here because the
doc does not commit to case-sensitivity either way: `?tool=/Build`, wrong
case of the same real tool, behaved the same as the fabricated value -- full
queue, not empty and not narrowed. Consistent with the same lookup-miss ->
no-filter fallback, offered as context in `population`, not as part of the
verdict.)

An agent using this filter to scope which leads it works one tool at a time
-- exactly what the parameter exists for, per the doc's own "one queue per
tool" framing -- gets every other tool's leads back the moment it passes a
value the server does not recognise (a typo, a tool since renamed, a site
path this account has no leads for at all), with nothing in the response
distinguishing that from a correctly scoped answer.

**Their fix, 2026-09-24 (#124, REPLY in the journal the same day).** The
parameter description now reads: "An unknown tool is refused with 400
("unknown tool ...") rather than ignored, so an empty list always means the
filter matched nothing." A refusal is the other honest answer to a value that
matches nothing -- the promise is that an unknown value never hands back other
tools' threads, and a 400 naming the value keeps it as surely as an empty
list. So: 400 whose detail says "unknown tool" passes, a 200 with no leads
passes, a 200 carrying leads fails, anything else is an unread answer.

SAFE. Both reads are GET with a query string; nothing here writes.
"""

from __future__ import annotations

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

READ_LIMIT = 200
UNKNOWN_TOOL = "/qa-fixture-does-not-exist-1234"
# A real site tool observed with zero current reddit leads at the time this
# was written, used only as context (population), never as the verdict --
# which surface is currently empty drifts with the queue, and the verdict
# does not depend on picking the right one.
KNOWN_EMPTY_CANDIDATES = ("/coinglass", "/alpaca", "/predictit", "/dexscreener")


def _leak_check(rest, path: str, endpoint_label: str) -> dict:
    """One read filtered by a value that matches no real tool.

    Returns a dict the caller turns into a Measurement; raises Inconclusive
    (via the caller) when nothing was read.
    """
    unknown = rest.get(path, params={"limit": READ_LIMIT, "tool": UNKNOWN_TOOL})
    if unknown.status_code == 400:
        try:
            detail = str((unknown.json() or {}).get("detail") or "")
        except ValueError:
            detail = ""
        if "unknown tool" in detail.lower():
            # The documented refusal: nothing leaked, the value was named.
            return {"ok": True, "unknown_tool_leads": 0, "leaked_tool_paths": [],
                    "control": None, "refused": detail[:160]}
    if unknown.status_code != 200:
        return {"ok": False,
                "reason": f"{endpoint_label} answered HTTP {unknown.status_code} "
                          f"for ?tool={UNKNOWN_TOOL!r}"}
    body = unknown.json()
    leads = body.get("leads")
    if not isinstance(leads, list):
        return {"ok": False,
                "reason": f"{endpoint_label} with ?tool={UNKNOWN_TOOL!r} answered "
                          f"200 with no `leads` list to read"}

    leaked_tools = sorted({l.get("tool_path") or "" for l in leads
                            if isinstance(l, dict) and l.get("tool_path") != UNKNOWN_TOOL})

    # Context only: whichever known-real tool is currently empty on THIS
    # surface, if any, confirms the "no match -> empty" case still works for
    # a real path. Not required for the verdict -- the fabricated value alone
    # already settles it, since no lead can legitimately carry it.
    control = None
    for candidate in KNOWN_EMPTY_CANDIDATES:
        probe = rest.get(path, params={"limit": READ_LIMIT, "tool": candidate})
        if probe.status_code == 200:
            probe_leads = probe.json().get("leads")
            if isinstance(probe_leads, list):
                control = {"tool": candidate, "leads": len(probe_leads)}
                if len(probe_leads) == 0:
                    break

    return {
        "ok": True,
        "unknown_tool_leads": len(leads),
        "leaked_tool_paths": leaked_tools,
        "control": control,
    }


def _run(rest, path: str, endpoint_label: str, claim_id: str) -> None:
    result = _leak_check(rest, path, endpoint_label)
    if not result["ok"]:
        raise Inconclusive(result["reason"])

    leaked = result["unknown_tool_leads"]
    conclude(Measurement(
        verdict="failed" if leaked else "passed",
        reason=(
            f"?tool={UNKNOWN_TOOL!r} on {endpoint_label} returned {leaked} lead(s) "
            f"spanning {len(result['leaked_tool_paths'])} other tool_path value(s) "
            f"({', '.join(repr(t) for t in result['leaked_tool_paths'][:8])}"
            f"{', ...' if len(result['leaked_tool_paths']) > 8 else ''}) -- "
            f"a value matching no real site tool fell through to the unfiltered "
            f"queue instead of the empty result the contract's 'keeps only "
            f"threads whose best-matching page is that tool' promises for any "
            f"non-empty value"
            if leaked else
            (f"?tool={UNKNOWN_TOOL!r} on {endpoint_label} was refused with the "
             f"documented 400 ({result['refused']!r}) -- no other tool's threads "
             f"came back"
             if result.get("refused") else
             f"?tool={UNKNOWN_TOOL!r} on {endpoint_label} correctly returned no "
             f"leads")
        ),
        left=result["leaked_tool_paths"], right=[],
        population={"unknown_tool_leads": leaked,
                     "known_empty_tool_control": result["control"]},
        sources={"contract": "openapi-public.json, GET " + path + ", parameter "
                              "`tool`: \"keeps only threads whose best-matching "
                              "page is that tool. Empty = every tool.\"",
                 "endpoint": path},
        claim_id=claim_id,
    ))


@qa(component="rest.creator", tier=SafetyTier.SAFE, surface="rest",
    claim="creator-reddit-leads-tool-filter-honours-unknown-values")
def test_reddit_leads_tool_filter_empties_on_an_unrecognised_value(rest_trusted):
    """?tool= on reddit-leads with a value that matches no real tool."""
    _run(rest_trusted, "/api/v1/creator/reddit-leads", "reddit-leads",
         "creator-reddit-leads-tool-filter-honours-unknown-values")


@qa(component="rest.creator", tier=SafetyTier.SAFE, surface="rest",
    claim="creator-twitter-leads-tool-filter-honours-unknown-values")
def test_twitter_leads_tool_filter_empties_on_an_unrecognised_value(rest_trusted):
    """?tool= on twitter-leads with a value that matches no real tool."""
    _run(rest_trusted, "/api/v1/creator/twitter-leads", "twitter-leads",
         "creator-twitter-leads-tool-filter-honours-unknown-values")

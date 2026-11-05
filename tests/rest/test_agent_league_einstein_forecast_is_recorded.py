"""Try and Beat Einstein says "Forecast recorded" and scores it by Brier; nothing leaves the browser (2026-11-05).

`/agent-league/beat-einstein` has a Dark Matter card: "Record forecast", "Resolves 31 Dec 2028 ... Scored by
Brier", and after the click "Forecast recorded: ... No score until resolution". The page's one script writes the
call to localStorage and sends nothing, so there is nothing to score in 2028.

**The rule.** If the page says a forecast is recorded and scored, and its own script keeps it in localStorage with
no request of any kind, the page is promising a score that nothing can give.

VERDICTS. failed: all of that. passed: the script sends the forecast, or the page no longer says it is recorded and
scored (a card that says it counts for nothing is a fix too). inconclusive: the read failed, the card is gone, or the
page loads a script from a file we did not read.

NOT asserted: that the card must pay anything; the page names no prize.
SAFE: one GET of a public page; nothing is submitted.
"""

from __future__ import annotations

import re

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

CLAIM = "agent-league-einstein-forecast-is-recorded"
PATH = "/agent-league/beat-einstein"
SENDS = re.compile(r"\bfetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket|\.submit\s*\(")


def verdict_for(html: str) -> str:
    """failed / passed / inconclusive from the page's own text and scripts."""
    if "Record forecast" not in html:
        return "inconclusive"
    if re.search(r"<script\b[^>]*\bsrc=", html, re.I):
        return "inconclusive"
    scripts = " ".join(re.findall(r"<script\b[^>]*>(.*?)</script>", html, re.S | re.I))
    if SENDS.search(scripts):
        return "passed"
    says_scored = "Forecast recorded" in html and "Scored by Brier" in html
    return "failed" if says_scored and "localStorage" in scripts else "passed"


@qa(component="rest.agent_league", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_agent_league_einstein_forecast_is_recorded(rest_trusted):
    """The card's promise against what the page's script does with the forecast."""
    try:
        got = rest_trusted.get(PATH)
    except Exception as exc:  # noqa: BLE001 - a failed read is not an empty read (rule 8)
        raise Inconclusive(f"{PATH} could not be read ({type(exc).__name__})")
    if got.status_code != 200:
        raise Inconclusive(f"{PATH} answered HTTP {got.status_code}")
    html = got.text
    verdict = verdict_for(html)
    if verdict == "inconclusive":
        raise Inconclusive(f"{PATH}: the forecast card is gone, or the page loads a script file")
    scripts = " ".join(re.findall(r"<script\b[^>]*>(.*?)</script>", html, re.S | re.I))
    conclude(Measurement(
        verdict=verdict,
        reason=(f"{PATH} says 'Forecast recorded' and 'Scored by Brier'; its script "
                f"{'sends a request' if SENDS.search(scripts) else 'sends no request'} and "
                f"{'writes' if 'localStorage' in scripts else 'does not write'} localStorage"),
        left={"says_recorded": "Forecast recorded" in html, "says_scored_by_brier": "Scored by Brier" in html},
        right={"script_sends_a_request": bool(SENDS.search(scripts)), "script_uses_local_storage": "localStorage" in scripts},
        population={"page": PATH},
        sources={"page": f"GET {PATH}", "credential": "X-API-Key, trusted tier (value never recorded)"},
        claim_id=CLAIM))

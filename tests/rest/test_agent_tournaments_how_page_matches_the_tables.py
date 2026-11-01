"""The Agent Casino "How it works" page describes the Flash tables that are on offer (2026-11-01).

https://cymetica.com/agent-casino/how is served as HTML with its text in it. It says "Flash tables
run 1 day; ET10 tables take 100 or 1,000 ET10.", "TRADES 1 DAY" and "Every table runs one day."
`GET /api/v1/agent-tournaments/rules` lists `flash_tiers` that include `fmicro1h`, `fpro1h`,
`fmicro5h` and `fpro5h`, and `GET /api/v1/agent-tournaments/lobby` has open and running Flash tables
with `hours` 1 and 5, shown in the lobby as "1H" and "5H".

**What was seen when this was written** (2026-11-01 ~08:30 UTC, no key). The page says every table
runs one day. The lobby lists open tables 41 (`fpro1h`, 1 h), 42 (`fmicro1h`), 43 (`fmicro5h`) and
35 (`fpro5h`), and the table page of a running 1 h table reads "LEFT · DAY 1/1" under a clock of
00H 59M. The page's stakes block also prints "ET10 600 / 300 / 100" under the $5 and $50 tables, whose
lobby cards pay "+ 141 ET10" (85 / 42 / 14) for the 1 day tables and +4 / +27 for the 1 h / 5 h ones;
600 / 300 / 100 is the 1,000 ET10 table's pot.

**The rule.** While the lobby lists a Flash table that does not run 1 day (`hours` other than 24),
the How it works page does not say that Flash tables, or every table, run one day.

NOT asserted: how the page words the shorter tables once it does, the ET10 figures, the page's layout.

SAFE: GETs only, no key.
"""

from __future__ import annotations

import re

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude
from tests.rest.test_gem_screener_numbers_match_their_sources import get_patiently

PREFIX = "/api/v1/agent-tournaments"
PAGE = "/agent-casino/how"
CLAIM = "agent-tournaments-how-page-matches-the-tables"

# "Flash tables run 1 day", "Every table runs one day", "TRADES 1 DAY" (the step's title).
FIXED_DAY = re.compile(r"flash tables run 1 day|every table runs (?:one|1) day|trades 1 day", re.I)


def fixed_day_claims(page_text: str) -> list[str]:
    """The sentences of the page that fix every table at one day."""
    return sorted({m.group(0) for m in FIXED_DAY.finditer(page_text)})


@qa(component="rest.agent_tournaments", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_agent_tournaments_how_page_matches_the_tables(rest_anon):
    """The page's day-length claim against the tables the lobby lists."""
    lobby = rest_anon.get(f"{PREFIX}/lobby")
    if lobby.status_code != 200:
        raise Inconclusive(f"{PREFIX}/lobby answered HTTP {lobby.status_code}")
    tables = [t for t in (lobby.json() or {}).get("tables") or [] if isinstance(t, dict)]
    short = sorted({(t.get("tier"), t.get("hours")) for t in tables
                    if t.get("kind") == "flash" and isinstance(t.get("hours"), (int, float))
                    and not isinstance(t.get("hours"), bool) and t.get("hours") != 24
                    and t.get("status") in ("open", "running")})
    if not tables:
        raise Inconclusive(f"{PREFIX}/lobby listed no table")
    page = get_patiently(rest_anon, PAGE, headers={"Accept": "text/html"})
    if page.status_code != 200 or "Agent Casino" not in page.text:
        raise Inconclusive(f"{PAGE} answered HTTP {page.status_code} without the Agent Casino page")
    claims = fixed_day_claims(page.text)
    if not short:
        raise Inconclusive("the lobby lists no open or running Flash table shorter than a day; "
                           "the page's claim cannot be wrong about one")
    wrong = bool(claims)
    conclude(Measurement(
        verdict="failed" if wrong else "passed",
        reason=(f"{PAGE} says {claims} while the lobby offers Flash tables that do not run a day: "
                f"{short} (tier, hours)"
                if wrong else
                f"{PAGE} no longer fixes every table at one day (the lobby lists {short})"),
        left={"fixed_day_claims": len(claims)},
        right={"fixed_day_claims": 0},
        population={"short_flash_tables": short, "claims": claims},
        sources={"page": PAGE, "lobby": f"{PREFIX}/lobby (tables[].tier, hours, status)"},
        claim_id=CLAIM))

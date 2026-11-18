"""The Season board leaves out an active company that the Universe lists (2026-11-18).

`GET /api/v1/company/universe` lists eight companies, all `status: active` or `paused`; `GET /api/v1/company/season`
(the Season 1 leaderboard on /company) ranks seven. The missing one is company 20, active, 5 days old, 0 points.
The board does show other companies with 0 points (Research Intelligence, ASYMMETRY CAPITAL, Atalaya Signals), and
its own rules ("Top 3 by points this month", "100+ points") do not say a company must have scored to be listed.

**The rule.** Every company the Universe lists as `active` is a row of the Season board.

VERDICTS. failed: an active company of the Universe has no row on the board. passed: every active company has one.
inconclusive: either read failed, or the Universe lists no active company.

NOT asserted: that paused companies should be listed, or what a new company's points should be.
SAFE: two GETs; the key is sent by the client in the header and never printed or recorded.
"""

from __future__ import annotations

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

CLAIM = "season-board-lists-every-active-company"


def _json(client, url: str):
    try:
        got = client.get(url)
    except Exception as exc:  # noqa: BLE001 - a failed read is not an empty read
        raise Inconclusive(f"{url} could not be read ({type(exc).__name__})")
    if got.status_code != 200:
        raise Inconclusive(f"{url} answered HTTP {got.status_code}")
    try:
        return got.json()
    except Exception as exc:  # noqa: BLE001
        raise Inconclusive(f"{url} did not answer JSON ({type(exc).__name__})")


@qa(component="rest.company", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_season_board_lists_every_active_company(rest_trusted):
    """Active companies of the Universe against the rows of the Season board."""
    universe = _json(rest_trusted, "/api/v1/company/universe")
    season = _json(rest_trusted, "/api/v1/company/season")
    active = {c["id"]: c.get("name") for c in universe.get("companies") or [] if c.get("status") == "active"}
    if not active:
        raise Inconclusive("the Universe lists no active company")
    ranked = {r.get("company_id") for r in season.get("rows") or []}
    missing = {i: n for i, n in active.items() if i not in ranked}
    conclude(Measurement(
        verdict="failed" if missing else "passed",
        reason=(f"{len(active)} active companies in the Universe, {len(ranked)} rows on the Season board; "
                f"missing: {missing or 'none'}"),
        left={"missing_from_board": {str(k): v for k, v in missing.items()}},
        right={"active_in_universe": len(active), "rows_on_board": len(ranked)},
        population={"computed_at": season.get("computed_at"), "season": season.get("season")},
        sources={"universe": "GET /api/v1/company/universe companies[status=active]",
                 "board": "GET /api/v1/company/season rows[].company_id",
                 "credential": "X-API-Key, trusted tier (value never recorded)"},
        claim_id=CLAIM))

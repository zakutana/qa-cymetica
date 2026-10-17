"""The Agent League's prize log reaches every prize it has recorded.

llms.txt: "Terms and the prize log: `GET /api/v1/agent-league/prizes`". The list answers the newest 50
records unless asked for more, and `limit` stops at 200 (`limit=201` is a 422). Read 2026-10-17: 246
records exist (ids 47-246 in the window), `offset`, `before`, `page`, `player_id` and `status` are all
ignored, and no route answers an owner's own prizes (`/me` carries none; `/me/prizes` and
`/players/{id}/prizes` are 404). So ids 1-46 -- every credited prize of October, ours among them (ids 4,
5, 9-14, 8,000 ET10, read on 2026-10-12 when the log held 90) -- can no longer be read by anyone, and the
response's own `month_committed_et10` (49,585) cannot be reconciled against its own list (the 200 rows
it shows are all `capped`, 0 ET10). Nexus's REPLY-0182 said "ask for more rows and it is there", which
holds only while a record is among the newest 200.

Passes when the list comes back short of its ceiling (it is the whole log), when its oldest id is 1, or
when any paging parameter or filter we try (offset, before, page, cursor, status=credited, player_id of
the window's players: every fix #213 names) returns a record older than the window. NOT asserted: which way they
page, or that ids start at 1 -- only that a full window whose oldest id is above 1 has nothing behind it
we can reach. SAFE: GETs only, anonymous.
"""

from __future__ import annotations

import httpx

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude
from tests.rest.test_gem_screener_numbers_match_their_sources import get_patiently

PRIZES = "/api/v1/agent-league/prizes"
CEILING = 200      # the largest `limit` their server takes (201 is a 422)


def _rows(client, **params) -> list[dict] | None:
    try:
        response = get_patiently(client, PRIZES, params=params)
    except httpx.HTTPError:
        return None
    if response.status_code != 200:
        return None
    try:
        body = response.json()
    except ValueError:
        return None
    rows = body.get("prizes") if isinstance(body, dict) else None
    return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else None


def _ids(rows: list[dict]) -> list[int]:
    return [r["id"] for r in rows if isinstance(r.get("id"), int)]


@qa(component="rest.agent_league", tier=SafetyTier.SAFE, surface="rest")
def test_the_prize_log_reaches_every_prize_it_recorded(rest_anon):
    """A full window at the ceiling whose oldest id is above 1 hides older records; failed unless
    some paging parameter reaches one of them."""
    window = _rows(rest_anon, limit=CEILING)
    if window is None:
        raise Inconclusive(f"{PRIZES}?limit={CEILING} did not answer a prize list")
    ids = _ids(window)
    if len(ids) < len(window) or not ids:
        raise Inconclusive("the prize rows carry no integer ids to order them by")
    oldest, newest = min(ids), max(ids)
    if len(window) < CEILING or oldest <= 1:
        conclude(Measurement(
            verdict="passed",
            reason=f"the log answers {len(window)} records, ids {oldest}-{newest}: nothing lies behind it",
            left={"records_out_of_reach": 0}, right={"records_out_of_reach": 0},
            population={"window": len(window), "oldest_id": oldest, "newest_id": newest},
            sources={"prizes": PRIZES}))
        return
    # Every fix #213 names counts as a reading: paging, a status filter (the window holds no credited
    # row, so a credited filter reaches older ones), a filter for one of the window's players.
    tried = {"offset": CEILING, "before": oldest, "before_id": oldest, "page": 2, "cursor": oldest,
             "status": "credited"}
    players = sorted({r["player_id"] for r in window if isinstance(r.get("player_id"), int)})[:5]
    attempts = [(name, {name: value}) for name, value in tried.items()]
    attempts += [("player_id", {"player_id": pid}) for pid in players]
    if players:
        tried["player_id"] = players
    reached = {}
    for name, params in attempts:
        rows = _rows(rest_anon, limit=CEILING, **params)
        if rows is not None:
            older = [i for i in _ids(rows) if i < oldest]
            if older:
                reached[name] = min(older)
    conclude(Measurement(
        verdict="passed" if reached else "failed",
        reason=(f"records older than the window are reachable by {', '.join(sorted(reached))}"
                if reached else
                f"the log answers its newest {CEILING} records (ids {oldest}-{newest}) and no more: "
                f"{oldest - 1} older records cannot be read, and none of "
                f"{', '.join(sorted(tried))} reaches one"),
        left={"records_out_of_reach": 0 if reached else oldest - 1},
        right={"records_out_of_reach": 0},
        population={"window": len(window), "oldest_id": oldest, "newest_id": newest,
                    "paging_tried": sorted(tried), "paging_that_reached": reached,
                    "statuses_in_window": sorted({str(r.get("status")) for r in window})},
        sources={"prizes": PRIZES}))

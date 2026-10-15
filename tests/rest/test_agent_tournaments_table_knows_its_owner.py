"""An Agent Tournaments table knows the seats the caller's key owns (2026-10-15, ET-31459).

Agent Tournaments (cymetica.com/agent-tournaments) answers `GET /api/v1/agent-tournaments/tables/{id}`
with `my_seat` (object or null) and, per seat, `mine` (boolean), both in the OpenAPI schema; the
lobby carries `my_seat` per table and `my_agents`. llms.txt gives agents one credential, the
X-API-Key, and ET-31459 (live 2026-10-15) gave the seat owner a control panel whose API twin,
`GET|POST /api/v1/agent-tournaments/seats/{seat_id}/bot-settings`, is "Owner only": it answers the
owner 200 and anyone else 403 `not_your_seat` (a house seat 403 `house_bot`).

**What was seen when this was written** (2026-10-15 ~18:20 UTC, our key). Our key's bot-settings
answered 200 for seat 29 (table 5, "tournament Perceptron Oracle") and seat 57 (table 13, "lab Wave
2 Fibonacci Phoenix"), both bots in our /my-bots, and 403 `not_your_seat` for seat 33 (PaperX). The
same key's GET /tables/5 and /tables/13 read `my_seat: null` and `mine: false` on every seat, ours
included; /lobby read `my_seat: null` on all ten tables and `my_agents: null`. So an agent holding a
seat cannot find it from the table or the lobby, the only places that list seats, and needs the
seat_id from the moment it asked for it.

**The rule.** Every seat our key owns (its bot-settings answers 200) is recognised by the table it
sits at: `seats[].mine` is true for it, or `my_seat` names it (a `my_seat` without a seat_id counts).
Either field is enough, so a fix that fills one of them passes.

NOT asserted: the lobby's fields (context above), the page's own "Mine" filter or panel (a signed-in
page may read a session), what `my_seat` holds beyond the seat, or anything about a seat we do not own.

SAFE: GETs only, our own seats with our key.
"""

from __future__ import annotations

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

PREFIX = "/api/v1/agent-tournaments"
CLAIM = "agent-tournaments-table-knows-its-owner"


def unrecognised(tables: list[dict], owned: set[int]) -> tuple[list[dict], list[int]]:
    """The owned seats a table does not call ours, and the owned seats no table read lists. A seat
    is recognised when its row says `mine: true` or the table's `my_seat` names it."""
    missed, seen = [], set()
    for table in tables:
        my_seat = table.get("my_seat")
        for seat in table.get("seats") or []:
            if not isinstance(seat, dict):
                continue
            seat_id = seat.get("seat_id")
            if seat_id not in owned:
                continue
            seen.add(seat_id)
            named = isinstance(my_seat, dict) and my_seat.get("seat_id", seat_id) == seat_id
            if seat.get("mine") is True or named:
                continue
            missed.append({"table_id": table.get("id"), "seat_id": seat_id, "bot": seat.get("bot"),
                           "mine": seat.get("mine"), "my_seat": my_seat})
    return missed, sorted(owned - seen)


@qa(component="rest.agent_tournaments", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_agent_tournaments_table_knows_its_owner(rest_trusted):
    """Our seats by the platform's own owner test, then each table's view of them."""
    lobby = rest_trusted.get(f"{PREFIX}/lobby")
    if lobby.status_code != 200:
        raise Inconclusive(f"{PREFIX}/lobby answered HTTP {lobby.status_code}")
    ids = [t.get("id") for t in (lobby.json() or {}).get("tables") or [] if isinstance(t, dict)]
    if not ids:
        raise Inconclusive(f"{PREFIX}/lobby listed no table")
    tables, owned, statuses = [], set(), {}
    for table_id in ids:
        r = rest_trusted.get(f"{PREFIX}/tables/{table_id}")
        if r.status_code != 200:
            raise Inconclusive(f"{PREFIX}/tables/{table_id} answered HTTP {r.status_code}")
        table = r.json()
        tables.append(table)
        for seat in table.get("seats") or []:
            if not isinstance(seat, dict) or seat.get("house") or seat.get("seat_id") is None:
                continue
            got = rest_trusted.get(f"{PREFIX}/seats/{seat['seat_id']}/bot-settings")
            statuses[seat["seat_id"]] = got.status_code
            if got.status_code == 200:
                owned.add(seat["seat_id"])
    unread = sorted(s for s, code in statuses.items() if code not in (200, 403))
    if not owned:
        raise Inconclusive(f"our key owns no seat at the {len(ids)} tables in the lobby "
                           f"({len(statuses)} member seats asked; unread {unread}); nothing to judge")
    missed, unlisted = unrecognised(tables, owned)
    named = "; ".join(f"table {m['table_id']} seat {m['seat_id']} ({m['bot']!r}): mine "
                      f"{m['mine']}, my_seat {m['my_seat']}" for m in missed)
    conclude(Measurement(
        verdict="failed" if missed else "passed",
        reason=(f"{len(missed)} of the {len(owned)} seats our key owns (their bot-settings answer it "
                f"200, 'Owner only') are not ours in their table's own answer to the same key: {named}"
                if missed else
                f"every one of the {len(owned)} seats our key owns is recognised by its table"),
        left={"owned_seats_not_recognised": len(missed)},
        right={"owned_seats_not_recognised": 0},
        population={"tables": ids, "member_seats_asked": len(statuses), "owned": sorted(owned),
                    "unread": unread, "unlisted": unlisted, "missed": missed},
        sources={"tables": f"{PREFIX}/lobby, {PREFIX}/tables/{{id}}",
                 "owner": f"{PREFIX}/seats/{{seat_id}}/bot-settings (200 owner, 403 not_your_seat)",
                 "contract": "OpenAPI: /tables/{table_id} carries my_seat (object|null) and "
                             "seats[].mine (boolean); llms.txt: agents authenticate with X-API-Key"},
        claim_id=CLAIM))

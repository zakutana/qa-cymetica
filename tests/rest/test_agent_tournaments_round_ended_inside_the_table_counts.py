"""A round that ended inside an Agent Casino table counts for that table, however late it settled (2026-11-01).

Rounds are five-minute epochs. A bot's activity feed (`GET /api/v1/cloned-bots/{id}/activity`) gives each
round's `epoch_end` and `closed_at`, the moment their settler got to it; over our last 183 rounds that
came a median 26 s and up to 153 s after `epoch_end`. The table page says "A trade counts for the table
when it closes inside the table's window", and the standings go by `closed_at`, so whether a round's
result counts depends on how soon the settler ran.

**What was seen when this was written** (2026-11-01, our key). Table 51 (Flash Pro 1H, 10:35:14 to
11:35:14 UTC), seat 209 "casino Divergence Dragon": the round opened 11:31:25 ended 11:35:00, 14 s
inside the table, and settled 11:36:04, +$16.41. `results.ranked` says 12 trades, +$78.10, +31.24 %,
capital back $328.10. The same page's "Your trades" lists 13 "counted" trades, +$94.51, "AT THE END
$344.51 +37.81% ROI", "OPEN AT THE END 0". A bot leading by less than that round has the place decided
by the settler's timing; here second place was $8.27 behind.

**The rule.** A seat's standings do not leave out a round of its bot whose `epoch_end` is inside the
table and whose `closed_at` is after it. It reads the tables ended in the last three days only, so a fix
from today clears, and judges by the newest such round. **Named fixes, as readings:** the table waits
for its last rounds, so the newest such round is counted and this passes; or a bot opens nothing that
cannot settle in time, so no such round appears, and this passes once `QUIET_SEATS` trading seats in the
window show none (one of the seven trading seats read today had one). Fewer than that is inconclusive.

NOT asserted: which of the two fixes is right, a table's other seats (a feed is ours alone), any round
that ended after the table (`after` is the bot's own business), the trade list's own count (#234).

SAFE: GETs only, our own seats with our key.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from qa import casino
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

PREFIX = "/api/v1/agent-tournaments"
CLAIM = "agent-tournaments-round-ended-inside-the-table-counts"
WINDOW = timedelta(days=3)
QUIET_SEATS = 40
PAGES = 8


def feed_of(client, instance: str) -> list[dict]:
    """The bot's whole activity feed; a page that cannot be read makes the whole reading inconclusive."""
    items: list[dict] = []
    for page in range(1, PAGES + 1):
        r = client.get(f"/api/v1/cloned-bots/{instance}/activity?page={page}&page_size=100")
        if r.status_code != 200:
            raise Inconclusive(f"activity of {instance} page {page} answered HTTP {r.status_code}")
        body = r.json() or {}
        items.extend(body.get("items") or [])
        if not body.get("has_more"):
            break
    return items


@qa(component="rest.agent_tournaments", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_agent_tournaments_round_ended_inside_the_table_counts(rest_trusted):
    """Every seat of ours at a table ended in the last three days: its standings against its bot's rounds."""
    lobby = rest_trusted.get(f"{PREFIX}/lobby")
    bots = rest_trusted.get(f"{PREFIX}/my-bots")
    if lobby.status_code != 200 or bots.status_code != 200:
        raise Inconclusive(f"lobby HTTP {lobby.status_code}, my-bots HTTP {bots.status_code}")
    body = bots.json() or {}
    rows = body if isinstance(body, list) else body.get("bots") or body.get("items") or []
    instances = {b.get("name"): b.get("instance_id") for b in rows if isinstance(b, dict)}
    now = datetime.now(timezone.utc)
    feeds: dict[str, list[dict]] = {}
    left_out, read = [], []
    for row in (lobby.json() or {}).get("tables") or []:
        if not isinstance(row, dict) or row.get("status") != "done":
            continue
        r = rest_trusted.get(f"{PREFIX}/tables/{row.get('id')}")
        if r.status_code != 200:
            raise Inconclusive(f"{PREFIX}/tables/{row.get('id')} answered HTTP {r.status_code}")
        table = r.json()
        ended = casino._when(table.get("ends_at"))
        if ended is None or now - ended > WINDOW:
            continue
        ranked = (table.get("results") or {}).get("ranked") or []
        for seat in table.get("my_seats") or [table.get("my_seat")]:
            if not isinstance(seat, dict):
                continue
            instance = instances.get(seat.get("bot"))
            standing = next((x for x in ranked if x.get("seat_id") == seat.get("seat_id")), None)
            if not instance or standing is None or not standing.get("trades"):
                continue
            feed = feeds.setdefault(instance, feed_of(rest_trusted, instance))
            read.append({"table_id": table.get("id"), "seat_id": seat.get("seat_id"), "ends_at": table.get("ends_at")})
            for item in casino.rounds_left_out(table, standing, feed):
                left_out.append({"table_id": table.get("id"), "seat_id": seat.get("seat_id"), "bot": seat.get("bot"),
                                 "ends_at": table.get("ends_at"), "epoch_end": item.get("epoch_end"),
                                 "closed_at": item.get("closed_at"), "profit_usdc": item.get("profit_usdc"),
                                 "standings_pnl_usdc": standing.get("pnl_usdc")})
    if not left_out and len(read) < QUIET_SEATS:
        raise Inconclusive(f"{len(read)} trading seats of ours at tables ended in the last three days and no round "
                           f"left out; {QUIET_SEATS} would say the rounds are no longer left out")
    named = "; ".join(f"table {d['table_id']} seat {d['seat_id']} ({d['bot']!r}): round ended {d['epoch_end']}, table "
                      f"ended {d['ends_at']}, settled {d['closed_at']}, {d['profit_usdc']} USDC left out of "
                      f"{d['standings_pnl_usdc']}" for d in left_out)
    conclude(Measurement(
        verdict="failed" if left_out else "passed",
        reason=(f"{len(left_out)} round(s) that ended inside the table are left out of its standings because they "
                f"settled after it: {named}"
                if left_out else
                f"none of {len(read)} trading seats at tables ended in the last three days leaves out such a round"),
        left={"rounds_left_out": len(left_out)},
        right={"rounds_left_out": 0},
        population={"seats_read": read, "left_out": left_out},
        sources={"table": f"{PREFIX}/tables/{{id}} (starts_at, ends_at, results.ranked[], my_seats)",
                 "feed": "/api/v1/cloned-bots/{id}/activity (epoch_end, closed_at, profit_usdc)",
                 "claim": "a round's result belongs to the table it ended in"},
        claim_id=CLAIM))

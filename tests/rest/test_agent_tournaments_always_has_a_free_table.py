"""Agent Tournaments always has a table with a free seat at each buy-in (2026-10-12).

Agent Tournaments (cymetica.com/agent-tournaments, the Build it Better app ET-30773) answered our
follow-up on 2026-10-12 with a rule it now serves at GET /api/v1/agent-tournaments/rules,
`new_tables`: "When a table fills, a new open table of the same buy-in opens at once, so there
is always a free table at each buy-in." The same answer's `start`: "A table starts when its 10th
seat is approved".

**What was seen when this was written** (2026-10-12, 08:00-08:30 UTC, anonymous): the paper
lobby held three tables. Micro #1 open with 10 free seats; Pro #2 running; Pro #5 open with
seats_taken 10, seats_free 0 -- nine seated and one `pending` (seat 28, waiting for its owner's
approval, which the page says lapses in 24 h). No Pro table had a free seat, the table's own
next_open_url pointed back at /agent-tournaments/table/5, and the lobby drew Pro #5 as
"OPEN · 0 SEATS LEFT" with a TAKE A SEAT button. The new table opens when a table starts, and a
table whose last seat is waiting for approval has not started.

**The rule.** For every buy-in the rules list (`tiers`), the lobby holds at least one open table
of the lobby's mode with seats_free above 0. Passes the moment every buy-in has one, however that
is done (a pending seat not counted as taken, or the new table opening at the 10th request).

A pass is the rule holding at the moment of the read. The case it is about -- a table at 10 of 10
that has not started -- comes and goes with approvals, so `population` says how many such tables
the read saw: a pass with none of them in the lobby is weaker evidence than a pass beside one.

NOT asserted: anything about live tables (`modes.live` is "not_open"), the order of the lobby,
the page's wording, or what happens to the pending seat.

SAFE: two anonymous GETs.
"""

from __future__ import annotations

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

PREFIX = "/api/v1/agent-tournaments"
CLAIM = "agent-tournaments-always-has-a-free-table"


def _seats_free(table: dict):
    free = table.get("seats_free")
    return free if isinstance(free, int) and not isinstance(free, bool) else None


def tiers_without_a_free_table(tiers: list, tables: list, mode: str) -> tuple[list[dict], list[str]]:
    """The buy-ins with no open table of `mode` that has a free seat, each with the tables of it
    the lobby does hold, and the buy-ins that could not be judged. A table whose status or
    seats_free is missing is unread, never full: a renamed key must not fail a tier unseen."""
    without, unread = [], []
    for row in tiers:
        tier = row.get("tier") if isinstance(row, dict) else None
        if not tier:
            unread.append(f"a tier row with no name: {row!r}"[:120])
            continue
        mine = [t for t in tables if isinstance(t, dict) and t.get("tier") == tier
                and t.get("mode") == mode]
        if any(t.get("status") == "open" and (_seats_free(t) or 0) > 0 for t in mine):
            continue
        if any(t.get("status") is None or _seats_free(t) is None for t in mine):
            unread.append(tier)
            continue
        without.append({"tier": tier, "tables": [
            {"id": t.get("id"), "status": t.get("status"), "seats_taken": t.get("seats_taken"),
             "seats_free": t.get("seats_free"), "seated": t.get("seated"),
             "pending": sum(1 for s in t.get("seats") or []
                            if isinstance(s, dict) and s.get("status") == "pending"),
             "next_open_url": t.get("next_open_url")} for t in mine]})
    return without, unread


def waiting_to_start(tables: list, mode: str) -> list:
    """Open tables of `mode` at 10 of 10 -- the case the rule is about."""
    return [t.get("id") for t in tables if isinstance(t, dict) and t.get("mode") == mode
            and t.get("status") == "open" and _seats_free(t) == 0]


@qa(component="rest.agent_tournaments", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_agent_tournaments_always_has_a_free_table(rest_anon):
    """The rules' buy-ins against the lobby's open tables."""
    rules = rest_anon.get(f"{PREFIX}/rules")
    if rules.status_code != 200:
        raise Inconclusive(f"{PREFIX}/rules answered HTTP {rules.status_code}")
    said = rules.json() or {}
    promise = said.get("new_tables")
    if not promise:
        raise Inconclusive(f"{PREFIX}/rules no longer carries `new_tables`; the promise this "
                           "check holds them to is not published")
    tiers = said.get("tiers") or []
    if not tiers:
        raise Inconclusive(f"{PREFIX}/rules lists no tiers; nothing to judge")
    lobby = rest_anon.get(f"{PREFIX}/lobby")
    if lobby.status_code != 200:
        raise Inconclusive(f"{PREFIX}/lobby answered HTTP {lobby.status_code}")
    seen = lobby.json() or {}
    mode = seen.get("mode")
    if not mode:
        raise Inconclusive(f"{PREFIX}/lobby names no mode; cannot tell its tables apart")
    tables = seen.get("tables") or []
    without, unread = tiers_without_a_free_table(tiers, tables, mode)
    if unread and not without:
        raise Inconclusive(f"{len(unread)} buy-in(s) could not be judged: {unread[:4]}")
    waiting = waiting_to_start(tables, mode)
    named = "; ".join(
        f"{w['tier']}: " + ", ".join(
            f"table {t['id']} {t['status']} seats_free {t['seats_free']} "
            f"({t['seated']} seated, {t['pending']} pending, next_open_url {t['next_open_url']})"
            for t in w["tables"]) for w in without)
    conclude(Measurement(
        verdict="failed" if without else "passed",
        reason=(f"{len(without)} of the {len(tiers)} buy-ins have no open {mode} table with a free "
                f"seat, while {PREFIX}/rules says 'there is always a free table at each buy-in'. "
                f"{named}"
                if without else
                f"each of the {len(tiers)} buy-ins has an open {mode} table with a free seat "
                f"({len(waiting)} table(s) at 10 of 10 waiting to start)"),
        left={"buyins_without_a_free_table": len(without)},
        right={"buyins_without_a_free_table": 0},
        population={"mode": mode, "tiers": [r.get("tier") for r in tiers if isinstance(r, dict)],
                    "tables": len(tables), "waiting_to_start": waiting, "unread": unread,
                    "without": without},
        sources={"promise": f"{PREFIX}/rules new_tables: {promise}",
                 "tiers": f"{PREFIX}/rules tiers", "tables": f"{PREFIX}/lobby tables"},
        claim_id=CLAIM))

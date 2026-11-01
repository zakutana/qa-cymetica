"""NEXUS tunes a seat the way llms.txt says it starts (2026-11-01).

`GET /llms.txt` describes how NEXUS comes to tune a seated bot: "lock ET10 on your seat
(`POST /api/v1/agent-tournaments/seats/{id}/nexus-lock` {"amount_et10"}; MCP agent_tournament_nexus_lock)
and NEXUS tunes the seated bot's markets, stop loss and take profit from its own trades while the table
runs; the ET10 comes back to your balance when the table ends". Since ET-32932 (live 2026-10-26) the
table page shows "NEXUS COACH ON" for every seat of a Pro plan without a lock.

**What was seen when this was written** (2026-11-01 ~09:20 UTC, our key). Tables 42 and 33: our seat
reads `my_nexus_lock: null` and `my_tune_log` holds NEXUS rows of kind TUNED ("stop loss 8 → 7 %",
"PERP BTC off · stop loss 7 → 5 %" at #42; "take profit 15 → 10 %" at #33). No ET10 was locked, no lock
control is on the page, and the sentence in llms.txt is unchanged.

**The rule.** While llms.txt says NEXUS tunes after an ET10 lock, a seat of ours that NEXUS tuned has a
lock (`my_nexus_lock` not null); or llms.txt no longer says the lock is how tuning starts.

NOT asserted: whether tuning without a lock is intended, how the page words the default, the seats of
other owners.

SAFE: GETs only, our own seat with our key.
"""

from __future__ import annotations

import re

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

PREFIX = "/api/v1/agent-tournaments"
CLAIM = "agent-tournaments-coach-runs-as-llms-txt-says"

# "lock ET10 on your seat (...) and NEXUS tunes the seated bot's markets, stop loss and take profit"
LOCK_STARTS_TUNING = re.compile(r"lock ET10 on your seat.{0,260}?NEXUS tunes", re.I | re.S)


def lock_sentence(text: str) -> str | None:
    """The llms.txt sentence that makes an ET10 lock the start of tuning, or None."""
    m = LOCK_STARTS_TUNING.search(text or "")
    return " ".join(m.group(0).split()) if m else None


def unlocked_but_tuned(table: dict) -> list[dict]:
    """Our seat at this table when NEXUS tuned it and no ET10 is locked on it, else []."""
    mine = table.get("my_seat")
    log = table.get("my_tune_log")
    if not isinstance(mine, dict) or not isinstance(log, list):
        return []
    tuned = [r for r in log if isinstance(r, dict) and r.get("kind") == "TUNED" and r.get("by") == "NEXUS"]
    if not tuned or table.get("my_nexus_lock"):
        return []
    return [{"table_id": table.get("id"), "seat_id": mine.get("seat_id"), "bot": mine.get("bot"),
             "tunes": len(tuned), "first": tuned[-1].get("text")}]


@qa(component="rest.agent_tournaments", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_agent_tournaments_coach_runs_as_llms_txt_says(rest_trusted):
    """llms.txt's start condition for tuning against the seats of ours that NEXUS tuned."""
    doc = rest_trusted.get("/llms.txt")
    if doc.status_code != 200:
        raise Inconclusive(f"/llms.txt answered HTTP {doc.status_code}")
    sentence = lock_sentence(doc.text)
    lobby = rest_trusted.get(f"{PREFIX}/lobby")
    if lobby.status_code != 200:
        raise Inconclusive(f"{PREFIX}/lobby answered HTTP {lobby.status_code}")
    ids = sorted(t.get("id") for t in (lobby.json() or {}).get("tables") or []
                 if isinstance(t, dict) and t.get("status") in ("running", "done") and t.get("id") is not None)
    off, read = [], []
    for table_id in reversed(ids[-12:]):
        r = rest_trusted.get(f"{PREFIX}/tables/{table_id}")
        if r.status_code != 200:
            raise Inconclusive(f"{PREFIX}/tables/{table_id} answered HTTP {r.status_code}")
        table = r.json()
        if isinstance(table.get("my_seat"), dict):
            read.append(table_id)
            off.extend(unlocked_but_tuned(table))
    if sentence is None and not off:
        raise Inconclusive("llms.txt no longer makes an ET10 lock the start of tuning and no seat of ours "
                           "was tuned without one; nothing to compare")
    if not read:
        raise Inconclusive(f"our key has no seat at the {len(ids)} running or finished tables read")
    wrong = bool(sentence) and bool(off)
    named = "; ".join(f"table {o['table_id']} seat {o['seat_id']} ({o['bot']!r}): {o['tunes']} NEXUS "
                      f"tunes, my_nexus_lock null, e.g. {o['first']!r}" for o in off[:4])
    conclude(Measurement(
        verdict="failed" if wrong else "passed",
        reason=(f"llms.txt says {sentence!r} but NEXUS tuned seats of ours with no ET10 locked: {named}"
                if wrong else
                "no seat of ours was tuned without a lock, or llms.txt no longer says a lock starts tuning"),
        left={"seats_tuned_without_a_lock": len(off) if sentence else 0},
        right={"seats_tuned_without_a_lock": 0},
        population={"tables_read": read, "unlocked_but_tuned": off, "sentence": sentence},
        sources={"docs": "/llms.txt (Agent Tournaments, nexus-lock)",
                 "table": f"{PREFIX}/tables/{{id}} (my_seat, my_nexus_lock, my_tune_log)",
                 "lobby": f"{PREFIX}/lobby (tables[], status)"},
        claim_id=CLAIM))

"""What the laboratory has already tried, per section -- derived, never a second store.

Laboratory v3, P2: [operator 2026-10-11] "zaznam at nedels stejne veci a udrzujes si a vyvojis
pamet aby se to porad nekam posouvalo". One row per strategy room: its section
(`qa.rooms.section_of`, the reading the report makes too), the thing it tried (`key`), how it
stands and when it got there. Built from the rooms' own rows only, so it cannot disagree with
them, and a chooser asks it before it opens anything: `last_judged` is the newest verdict on a
key, and a key judged inside `RETRY_DAYS` is not tried again.

Pure: rows in, rows out.
"""

from __future__ import annotations

from datetime import datetime, timezone

from qa import rooms as rooms_mod

# A thing judged this long ago may be tried again -- a new window, and the platform moves
# weekly. Inside it, the verdict stands and the chooser says so instead of repeating it.
RETRY_DAYS = 30.0


BAND_FIELDS = ("stop_loss_pct", "take_profit_pct")


def band_label(settings: dict | None) -> str:
    """"SL 10 / TP 30" for a bot's band, or "defaults" when it was given none -- a fresh
    clone runs the species' own band (CLN-0018: their stop and target were null)."""
    settings = settings or {}
    if all(isinstance(settings.get(f), (int, float)) for f in BAND_FIELDS):
        return "SL {stop_loss_pct:g} / TP {take_profit_pct:g}".format(**settings)
    return "defaults"


def bands_by_instance(clone_rows: list[dict]) -> dict[str, dict]:
    """Each clone's band as their side ACCEPTED it, field by field, the newest change
    winning -- wave.py's, a variant's or a launch's alike. A clone never set has none."""
    accepted = {row.get("id") for row in clone_rows or () if row.get("type") == "outcome"
                and row.get("kind") == "settings" and row.get("outcome") == "accepted"}
    out: dict[str, dict] = {}
    for row in clone_rows or ():
        if (row.get("type") == "intent" and row.get("kind") == "settings"
                and row.get("id") in accepted):
            for field in BAND_FIELDS:
                if field in (row.get("body") or {}):
                    out.setdefault(str(row.get("instance_id")), {})[field] = row["body"][field]
    return out


def key_of(room: dict, settings: dict | None = None) -> str | None:
    """What a room tried: `card:<id>` for a card; `bot:<species>:<band>` for a bot (P3: a
    species at another band is another experiment); `<kind>:<ref>` for a fund or an Arena
    room. A room from before rooms named what they held has no key."""
    if room.get("card"):
        return f"card:{str(room['card']).lower()}"
    if room.get("kind") == "bot" and room.get("ref"):
        return f"bot:{str(room['ref']).lower()}:{band_label(settings)}"
    if room.get("kind") and room.get("ref"):
        return f"{room['kind']}:{str(room['ref']).lower()}"
    return None


def _moment(stamp) -> datetime | None:
    try:
        when = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return when if when.tzinfo else when.replace(tzinfo=timezone.utc)


def register(room_rows: list[dict], bot_origins=(), proposals: dict | None = None) -> list[dict]:
    """Every strategy room as {room, section, key, title, status, verdict, return_pct, at},
    oldest first. `status` is the room's newest status; `verdict` and `return_pct` its newest
    verdict, and `at` when that verdict (or, without one, that status) was written.

    A bot room's band is the one it was opened with: on its own row (`settings`, a band
    Nexus named) or on the proposal of ours it opened from (`proposals`, id -> row)."""
    proposals = proposals or {}
    latest_status: dict[str, dict] = {}
    latest_verdict: dict[str, dict] = {}
    for row in room_rows or ():
        if row.get("type") == "status":
            latest_status[str(row.get("room"))] = row
        elif row.get("type") == "verdict":
            latest_verdict[str(row.get("room"))] = row
    plans = rooms_mod.plans(room_rows or [])
    titles = rooms_mod.names(room_rows or [])
    out = []
    for room in rooms_mod.strategies(room_rows or []):
        rid = room["id"]
        verdict = latest_verdict.get(rid) or {}
        status = latest_status.get(rid) or {}
        out.append({
            "room": rid, "origin": room.get("origin"),
            "section": rooms_mod.section_of(room, plans.get(rid), bot_origins),
            "key": key_of(room, room.get("settings")
                          or (proposals.get(str(room.get("origin"))) or {}).get("settings")),
            "title": titles.get(rid, room.get("title")),
            "status": status.get("status") or "proposed",
            "verdict": verdict.get("verdict"),
            "return_pct": verdict.get("return_pct"),
            "at": verdict.get("at") or status.get("at") or room.get("at")})
    return out


def last_judged(rows: list[dict], key: str) -> dict | None:
    """The newest register row with a verdict on this key, in any section, or None."""
    judged = [r for r in rows if r["key"] == key and r["verdict"]]
    return max(judged, key=lambda r: str(r["at"] or "")) if judged else None


def days_since(row: dict, now: datetime) -> float | None:
    when = _moment(row.get("at"))
    return None if when is None else (now - when).total_seconds() / 86400.0


def said(row: dict, now: datetime) -> str:
    """One line on how a key went: "STR-0001 refuted −3.1 %, 4 days ago"."""
    ret = row.get("return_pct")
    pct = (f" {'+' if ret > 0 else '−' if ret < 0 else ''}{abs(ret):.1f} %"
           if isinstance(ret, (int, float)) else "")
    age = days_since(row, now)
    when = f", {age:.0f} days ago" if age is not None else ""
    return f"{row['room']} {row['verdict']}{pct}{when}"


def summary(rows: list[dict]) -> dict[str, dict[str, int]]:
    """Per section, how many rooms stand where: what `lab.py brief` prints."""
    out: dict[str, dict[str, int]] = {}
    for row in rows:
        if row["section"] not in rooms_mod.SECTIONS:
            continue
        stand = row["verdict"] or row["status"]
        out.setdefault(row["section"], {}).setdefault(stand, 0)
        out[row["section"]][stand] += 1
    return out

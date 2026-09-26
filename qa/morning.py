"""The morning report: what the night did in the laboratory, by 7:00.

Plan v2, V11; pin 7 in .claude/skills/laborator/SKILL.md is the operator's
own words. One short Czech page every morning at one address -- the deep pass
in three lines, the lab by room, what changed overnight, what the manager
does today, a Telegram message ready when Cymetica is owed one, and what was
changed because of their last feedback.

No scheduler (the operator, 2026-09-12 and 09-14: the loop is theirs). The
overnight /loop's first tick from DUE_AT says the report is due; a session
that starts after MISSING_AT without one is told so by the reminders and
makes it at once. It counts as made for the day only once it is published
(`lab.py morning --published URL`), so a failed publish is still due.

Pure: every input is handed in. scripts/lab.py reads the files, and
scripts/morning.py draws the page.
"""

from __future__ import annotations

import re
from datetime import datetime, time

DUE_AT = time(6, 40)
MISSING_AT = time(7, 0)
MAX_OVERNIGHT = 6
MAX_LINE = 140
HANDLE = "@EventTraderQABot"
SECTOR_NAMES = {"cards": "Karty", "bots": "Boti", "memecoins": "Memecoiny",
                "funds": "Fondy"}
# A sector's figure has to move this much overnight to be news.
MOVE_PP = 0.5


def _made_today(now_local: datetime, state: dict | None) -> bool:
    return (state or {}).get("made_on") == now_local.date().isoformat()


def due(now_local: datetime, state: dict | None) -> bool:
    """From 06:40 local until today's report is published."""
    return now_local.time() >= DUE_AT and not _made_today(now_local, state)


def missing(now_local: datetime, state: dict | None) -> bool:
    """Past 07:00 local and still not published: what a session start says."""
    return now_local.time() >= MISSING_AT and not _made_today(now_local, state)


def _cz(value: float, digits: int = 1) -> str:
    text = f"{abs(value):.{digits}f}".replace(".", ",")
    return ("−" if value < 0 and text.strip("0,") else "") + text


def _plain(text: str) -> str:
    """A markdown bullet as a line: its bold lead if it has one, else its
    first sentence; no marks, at most MAX_LINE characters."""
    lead = re.match(r"\*\*(.+?)\*\*", text)
    first = lambda s: re.split(r"(?<=[.!?])\s", s.strip(), 1)[0]  # noqa: E731
    if lead and lead.group(1).rstrip().endswith(":"):
        # "**2 ověření `pass`:** #111 a #120." -- the lead only names the kind.
        words = lead.group(1) + " " + first(text[lead.end():])
    else:
        words = lead.group(1) if lead else first(text)
    words = re.sub(r"[`*_]", "", words).strip().rstrip(":")
    words = " ".join(words.split())
    return words if len(words) <= MAX_LINE else words[:MAX_LINE - 1].rstrip() + "…"


def _bullets(section: str) -> list[str]:
    """Top-level bullets only, each with its wrapped continuation lines."""
    out: list[str] = []
    for line in section.splitlines():
        if re.match(r"^[*-] ", line):
            out.append(line[2:].strip())
        elif out and line.startswith("  ") and not re.match(r"^\s+[*-] ", line):
            out[-1] += " " + line.strip()
    return out


FIXED_OURS = "chyb v našich vlastních kontrolách a nástrojích, ne v Cymetice"


def deep_pass(markdown: str) -> dict:
    """DEEP-PASS.md in two lines: what it fixed of OURS, and what it sent
    Cymetica. The operator, 2026-09-26: the fixes read as Cymetica's bugs,
    the process figures are not wanted, and nothing waits on them -- so no
    "Čeká na tebe" line."""
    title = next((line[2:].strip() for line in markdown.splitlines()
                  if line.startswith("# ")), None)
    sections: dict[str, str] = {}
    for chunk in re.split(r"(?m)^## ", markdown)[1:]:
        head, _, body = chunk.partition("\n")
        sections[head.strip()] = body
    lines = []
    if "Opraveno" in sections:
        found = _bullets(sections["Opraveno"])
        # A pass that leads with its count ("**30 z 31 ...**") is read by it.
        lead = re.match(r"^\W*(\d+)\b", found[0]) if found else None
        lines.append({"kind": "fixed",
                      "count": int(lead.group(1)) if lead else len(found),
                      "text": FIXED_OURS})
    if "Co odešlo Cymetice" in sections:
        found = _bullets(sections["Co odešlo Cymetice"])
        lines.append({"kind": "sent", "count": len(found),
                      "text": _plain(found[0]) if found else "nic"})
    return {"title": title, "lines": lines}


FIXED_STATUSES = frozenset({"fixed", "paid", "resolved"})


def cymetica(events: list[dict], ticks: list[dict], since: str | None) -> dict:
    """What happened with Cymetica since the last report: sweeps and bug
    hunts the lab ran, reports we filed, reports they fixed, fixes we
    verified. The operator, 2026-09-26: the report did not say."""
    def after(row) -> bool:
        return since is None or str(row.get("at") or "") > since

    sweeps = sum(1 for t in ticks if t.get("type") == "tick" and after(t)
                 and any(str(d).startswith("hunt") for d in t.get("decide") or []))
    filed = sorted({e["report_id"] for e in events
                    if e.get("type") == "filing_outcome" and e.get("outcome") == "accepted"
                    and e.get("report_id") is not None and after(e)})
    fixed = sorted({e["report_id"] for e in events
                    if e.get("type") == "vendor_status" and after(e)
                    and str(e.get("status") or "").lower() in FIXED_STATUSES
                    and e.get("report_id") is not None})
    verified = sorted({e["report_id"] for e in events
                       if e.get("type") == "verification_outcome" and after(e)
                       and e.get("outcome") == "accepted" and e.get("verdict") == "pass"
                       and e.get("report_id") is not None})
    return {"sweeps": sweeps, "filed": filed, "fixed": fixed, "verified": verified}


def overnight(report: dict, before: dict | None) -> list[str]:
    """What moved since the last report: new experiments, judged ones, a
    sector's figure, Nexus. Nothing to compare against is nothing to say."""
    if not before:
        return []
    out: list[str] = []
    old = {r.get("id"): r for r in before.get("rooms") or []}
    for room in report.get("rooms") or []:
        was = old.get(room.get("id"))
        if room.get("product") not in SECTOR_NAMES:
            continue
        if was is None:
            out.append(f"Nový pokus: {room.get('title')} "
                       f"({SECTOR_NAMES[room['product']]})")
        elif room.get("verdict") and not was.get("verdict"):
            word = {"survived": "✓ vyšlo", "refuted": "✗ nevyšlo"}.get(
                room["verdict"], "? nedá se říct")
            net = room.get("net_pct")
            out.append(f"{word}: {room.get('title')}"
                       + (f" ({_cz(net)} %)" if net is not None else ""))
    for key, name in SECTOR_NAMES.items():
        now = (report.get("products") or {}).get(key, {}).get("net_pct")
        then = (before.get("products") or {}).get(key, {}).get("net_pct")
        if now is not None and then is not None and abs(now - then) >= MOVE_PP:
            out.append(f"{name} {_cz(then)} % → {_cz(now)} %")
    asked = ((report.get("nexus") or {}).get("questions") or 0) - (
        (before.get("nexus") or {}).get("questions") or 0)
    answered = ((report.get("nexus") or {}).get("answered") or 0) - (
        (before.get("nexus") or {}).get("answered") or 0)
    if asked or answered:
        out.append(f"Nexus: +{asked} otázek, +{answered} odpovědí")
    return out[:MAX_OVERNIGHT]


def _since(notebook: list[dict], kind: str, since: str | None) -> list[dict]:
    return [r for r in notebook if r.get("type") == "entry" and r.get("kind") == kind
            and (since is None or str(r.get("at") or "") > since)]


def acted(notebook: list[dict], since: str | None) -> list[str]:
    """What the manager changed because of the operator's feedback, since the
    last report -- "Podle tvé zpětné vazby"."""
    return [r["text"] for r in _since(notebook, "acted", since)]


def telegram(notebook: list[dict], since: str | None) -> str | None:
    """The newest message for Cymetica the night wrote down, ready to paste,
    opening with our handle."""
    lines = _since(notebook, "telegram", since)
    if not lines:
        return None
    text = lines[-1]["text"]
    return text if text.startswith(HANDLE) else f"{HANDLE} {text}"


TODAY_LINE = 110


def today(notebook: list[dict], since: str | None = None,
          limit: int = 3) -> list[str]:
    """What the manager means to do today: the newest `next` lines written
    since the last report, each cut to its first sentence -- the diary line
    is written for the next tick, the report is read by the operator on a
    phone. Unbounded, a night that wrote none showed days-old plans as
    today's (R05, deep pass of 2026-09-24)."""
    out = []
    for row in _since(notebook, "next", since)[-limit:]:
        text = re.split(r"(?<=[.!?])\s", row["text"].strip(), 1)[0]
        out.append(text if len(text) <= TODAY_LINE
                   else text[:TODAY_LINE - 1].rstrip() + "…")
    return out


def build(report: dict, state: dict | None, deep_md: str, notebook: list[dict],
          now_local: datetime, events: list[dict] | None = None) -> dict:
    state = state or {}
    since = state.get("made_at")
    return {
        "cymetica": cymetica(events or [], notebook, since),
        "date": now_local.date().isoformat(),
        "made_at": now_local.isoformat(timespec="minutes"),
        "deep_pass": deep_pass(deep_md or ""),
        "sectors": [{"key": key, "name": name,
                     **((report.get("products") or {}).get(key) or {})}
                    for key, name in SECTOR_NAMES.items()],
        "nexus": report.get("nexus") or {},
        "overnight": overnight(report, state.get("snapshot")),
        # The first report has nothing to compare against, and says so.
        "compared": bool(state.get("snapshot")),
        "today": today(notebook, since),
        "telegram": telegram(notebook, since),
        "acted": acted(notebook, since),
    }

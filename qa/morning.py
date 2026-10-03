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


def _plain(text: str, limit: int | None = None) -> str:
    """A markdown bullet as a line: its bold lead if it has one, else its
    first sentence; no marks, at most MAX_LINE characters (or `limit`), cut at a word."""
    limit = limit or MAX_LINE
    lead = re.match(r"\*\*(.+?)\*\*", text)
    first = lambda s: re.split(r"(?<=[.!?])\s", s.strip(), 1)[0]  # noqa: E731
    if lead and lead.group(1).rstrip().endswith(":"):
        # "**2 ověření `pass`:** #111 a #120." -- the lead only names the kind.
        words = lead.group(1) + " " + first(text[lead.end():])
    else:
        words = lead.group(1) if lead else first(text)
    words = re.sub(r"[`*_]", "", words).strip().rstrip(":")
    words = " ".join(words.split())
    return _cut(words, limit)


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
DEEP_LINE = 420
ITEM_LINE = 200
TITLE_LINE = 110
NO_CZECH = "nová položka, český popis ještě chybí"
# What the page may not say to someone who reads it in Czech and is not a programmer: a
# backtick, a snake_case name, a file name. (The operator, 2026-10-03.)
_JARGON = re.compile(r"`|\b[a-z]+_[a-z_]+\b|\.py\b|\bPRE-\d|\brun-\d|\bSTR-\d")


def jargon(text: str) -> list[str]:
    """The code-looking tokens in a sentence meant for the operator, in order; [] when it
    is plain language."""
    return [m.group(0) for m in _JARGON.finditer(text or "")]


def _cut(text: str, limit: int) -> str:
    """At most `limit` characters, cut at a word and marked with an ellipsis, never in the
    middle of a word (a line ended "... ET-29001 1..." on 2026-10-02)."""
    if len(text) <= limit:
        return text
    return text[:limit - 1].rsplit(" ", 1)[0].rstrip(" ,;:.") + "…"


def _what(bullet: str) -> str:
    """What one fix was, as words: its bold lead, or -- for a bullet that
    leads with its count ("**14 z 28 ...**") -- what follows that lead."""
    lead = re.match(r"\*\*(.+?)\*\*", bullet)
    if lead and re.match(r"\d+\b", lead.group(1)):
        rest = re.sub(r"[`*_]", "", bullet[lead.end():])
        return " ".join(re.split(r"(?<=[.!?])\s", " ".join(rest.split()), 1)[0].split())
    return _plain(bullet, ITEM_LINE)


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
        # A pass that leads with its count ("**30 z 31 ...**") is read by it;
        # "#133" is a report id, not a count, and "Nic." is none.
        lead = re.match(r"^[*\s]*(\d+)\b", found[0]) if found else None
        if lead:
            count = int(lead.group(1))
        elif found and re.match(r"^\W*(nic|žádn)", found[0], re.I):
            count = 0
        else:
            count = len(found)
        # The operator, 2026-10-01: "opraveno 14, ale vubec nemam paru ceho se
        # to tyka" -- so the line says what, after saying whose they are.
        whats = [w for w in (_what(b) for b in found) if w]
        said = " · ".join(whats)
        text = f"{FIXED_OURS}: {said}" if said else FIXED_OURS
        lines.append({"kind": "fixed", "count": count,
                      "text": text if len(text) <= DEEP_LINE
                      else text[:DEEP_LINE - 1].rstrip() + "…",
                      # The page lists these, one line each, so nothing is cut mid-sentence.
                      "items": [_cut(w, ITEM_LINE) for w in whats]})
    if "Co odešlo Cymetice" in sections:
        found = _bullets(sections["Co odešlo Cymetice"])
        lines.append({"kind": "sent", "count": len(found),
                      "text": _plain(found[0]) if found else "nic"})
    return {"title": title, "lines": lines}


# Not "paid": paying a report accepts it and does not claim the defect is gone
# (qa/fold.py), and #130 and #132 were paid while they still reproduced.
FIXED_STATUSES = frozenset({"fixed", "resolved"})


def titles_from(tracker_rows: list[dict], ledger: dict, czech: dict | None = None) -> dict:
    """{report id: what it is about, in Czech}: its own line from `outbox/reports-cs.yaml`
    (`czech`), and NO_CZECH for a report that has none. The tracker's English title and the
    check's message are never shown (the operator, 2026-10-03: the report is Czech and plain);
    the ids come from the tracker copy and from the reports the ledger filed."""
    czech = {int(k): v for k, v in (czech or {}).items() if str(k).lstrip("-").isdigit() and v}
    ids: list = []
    for row in tracker_rows or ():
        if isinstance(row, dict) and row.get("id") is not None:
            ids.append(row["id"])
    for finding in ((ledger or {}).get("findings") or {}).values():
        for filed in ((finding.get("filing") or {}).get("reports") or ()):
            rid = filed.get("report_id") if isinstance(filed, dict) else None
            if rid is not None:
                ids.append(rid)
    return {rid: czech.get(int(rid), NO_CZECH) for rid in ids if str(rid).lstrip("-").isdigit()}


def _short_title(title) -> str:
    text = " ".join(str(title or "").split())
    return text if len(text) <= TITLE_LINE else text[:TITLE_LINE - 1].rstrip() + "…"


def cymetica(events: list[dict], registered: list[str], since: str | None,
             titles: dict | None = None) -> dict:
    """What happened with Cymetica since the last report: verification runs
    against their platform, reports we filed, reports they fixed, fixes we
    verified. The operator, 2026-09-26: the report did not say.

    `registered` is when each preregistration was made: every sweep that ran
    registered one, whoever started it. A tick that only decided a hunt is
    not a sweep that ran."""
    def after(row) -> bool:
        return since is None or str(row.get("at") or "") > since

    sweeps = sum(1 for at in registered if since is None or str(at) > since)
    filed = sorted({e["report_id"] for e in events
                    if e.get("type") == "filing_outcome" and e.get("outcome") == "accepted"
                    and e.get("report_id") is not None and after(e)})
    fixed = sorted({e["report_id"] for e in events
                    if e.get("type") == "vendor_status" and after(e)
                    and str(e.get("status") or "").lower() in FIXED_STATUSES
                    and e.get("report_id") is not None})
    # The newest verdict we sent on a report decides (2026-10-01): a pass on
    # #132 and our correction on it the same night read "the fix holds: #132".
    newest: dict = {}
    for e in sorted((e for e in events
                     if e.get("type") == "verification_outcome" and after(e)
                     and e.get("outcome") == "accepted" and e.get("report_id") is not None
                     and e.get("verdict") in ("pass", "fail")),
                    key=lambda e: str(e.get("at") or "")):
        newest[e["report_id"]] = e["verdict"]
    verified = sorted(r for r, verdict in newest.items() if verdict == "pass")
    failing = sorted(r for r, verdict in newest.items() if verdict == "fail")
    # What each number is about (the operator, 2026-10-01: a bare #138 says
    # nothing): the tracker's own title, one line, for the ones named here.
    named = {*filed, *fixed, *verified, *failing}
    return {"sweeps": sweeps, "filed": filed, "fixed": fixed, "verified": verified,
            "failing": failing,
            "titles": {r: _short_title(t) for r, t in (titles or {}).items()
                       if r in named and t}}


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
            out.append(f"{word} ({SECTOR_NAMES[room['product']]}): {room.get('title')}"
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
          now_local: datetime, events: list[dict] | None = None,
          registered: list[str] | None = None,
          titles: dict | None = None) -> dict:
    state = state or {}
    since = state.get("made_at")
    return {
        "cymetica": cymetica(events or [], registered or [], since, titles),
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

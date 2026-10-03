"""The morning report is Czech and plain (the operator, 2026-10-03).

*"zapominas ze ma byt vse degen friendly, takze to ma byt cesky a uplne srozumitelne o co
jde"* -- said over a report that named a filed bug by the English message of the check that
found it, and cut a line of the deep pass in the middle of a word.

Held here, not by memory:

* every report we filed from #136 on has a one-sentence Czech line in `outbox/reports-cs.yaml`,
  written the day it is filed, and so does every OLDER report the page would name -- one the
  journal says was filed, fixed or verified lately (the page shows that line and nothing else,
  `qa/morning.py::titles_from`; without one it prints the "no Czech yet" placeholder);
* those lines are Czech, short, and carry no code name or file name;
* the deep pass's `Opraveno` bullets, which the page prints, carry none either.

SAFE: reads files in the repository.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude
from qa.morning import NO_CZECH, TITLE_LINE, cymetica, jargon, titles_from
from qa.state import read_events

REPO = Path(__file__).resolve().parent.parent.parent
# Reports from this number on must have a line whether or not the page names them. Older ones
# (80 of them have none, and most will never be named again) are held only when the page would
# name them: see _shown_without_a_line.
FIRST_HELD = 136
# The page names what the journal recorded since the last published report; a report skipped for
# a day or two shows all of it. So the window is the last published report, or this many days
# back from the newest journal event, whichever reaches further.
LOOKBACK_DAYS = 3
CZECH_LETTER = re.compile(r"[ěščřžýáíéůúďťň]", re.I)


def _lines() -> dict:
    doc = yaml.safe_load((REPO / "outbox" / "reports-cs.yaml").read_text(encoding="utf-8")) or {}
    return {int(k): v for k, v in (doc.get("reports") or {}).items()}


def _ledger() -> dict:
    return json.loads((REPO / "state" / "ledger.json").read_text(encoding="utf-8"))


def _filed_ids() -> set[int]:
    out = set()
    for finding in (_ledger().get("findings") or {}).values():
        for filed in ((finding.get("filing") or {}).get("reports") or ()):
            rid = filed.get("report_id") if isinstance(filed, dict) else None
            if isinstance(rid, int):
                out.add(rid)
    return out


def _tracker_rows() -> list:
    try:
        copy = json.loads((REPO / "state" / "bounty.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return (copy.get("reports") or copy.get("items") or []) if isinstance(copy, dict) else []


def _window_start(events: list) -> str | None:
    """The `since` the next page will use, at the widest: the last published report's moment
    (this machine's state/lab/morning.json, gitignored, so only when it exists) or LOOKBACK_DAYS
    before the newest journal event."""
    def moment(text):
        try:
            return datetime.fromisoformat(str(text)).astimezone(timezone.utc)
        except ValueError:
            return None

    stamps = [m for m in (moment(e.get("at")) for e in events) if m]
    if not stamps:
        return None
    start = max(stamps) - timedelta(days=LOOKBACK_DAYS)
    try:
        made = json.loads((REPO / "state" / "lab" / "morning.json").read_text(encoding="utf-8"))
        start = min(start, moment(made.get("made_at")) or start)
    except (OSError, ValueError, AttributeError):
        pass
    return start.isoformat()


def _shown_without_a_line(events: list, since: str | None, rows: list, ledger: dict,
                          czech: dict) -> list[int]:
    """The reports the page would name that have no Czech line to name them by: titles_from's
    placeholder, or no title at all (an id the tracker copy and the ledger both lack)."""
    titles = titles_from(rows, ledger, czech)
    page = cymetica(events, [], since, titles)
    named = {*page["filed"], *page["fixed"], *page["verified"], *page["failing"]}
    return sorted(r for r in named if titles.get(r, NO_CZECH) == NO_CZECH)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_report_has_a_plain_czech_line_and_the_deep_pass_has_no_code_in_it():
    lines = _lines()
    missing = sorted(i for i in _filed_ids() if i >= FIRST_HELD and i not in lines)
    # T07, deep pass 2026-10-04: only #136 and later were required, so an older report that
    # reached the page (a fix verified, a status change) was printed as the placeholder with this
    # test green. Control first: the check must see a named report that has no line, one that has
    # a line, and an id nobody knows -- else a green here proves nothing.
    filed = [{"type": "filing_outcome", "outcome": "accepted", "report_id": 51,
              "at": "2026-10-01T10:00:00+00:00"}]
    ledger = {"findings": {"CYM-a": {"filing": {"reports": [{"report_id": 51}]}}}}
    since = "2026-10-01T00:00:00+00:00"
    assert _shown_without_a_line(filed, since, [], ledger, {}) == [51], "an old report without a line"
    assert _shown_without_a_line(filed, since, [], ledger, {51: "Česky"}) == []
    # titles_from reads a line only for an id the tracker copy or the ledger knows; any other is
    # printed as a bare number, which is no Czech title either.
    assert _shown_without_a_line(filed, since, [], {}, {51: "Česky"}) == [51], "an id nobody knows"
    assert _shown_without_a_line(filed, since, [{"id": 51}], {}, {51: "Česky"}) == []
    # The committed journal by its path, like the ledger above: bare read_events() follows
    # QA_STATE_DIR, which some tests set.
    events = read_events(REPO / "state" / "journal" / "events.jsonl")
    since = _window_start(events)
    assert since, "no journal events, so there is no page to hold"
    shown = _shown_without_a_line(events, since, _tracker_rows(), _ledger(), lines)
    bad = []
    for rid, text in sorted(lines.items()):
        if len(text) > TITLE_LINE:
            bad.append(f"#{rid} is {len(text)} characters, over {TITLE_LINE}")
        if not CZECH_LETTER.search(text):
            bad.append(f"#{rid} is not in Czech: {text!r}")
        for token in jargon(text):
            bad.append(f"#{rid} carries code: {token!r}")
    deep = (REPO / "DEEP-PASS.md").read_text(encoding="utf-8")
    fixed = re.search(r"(?ms)^## Opraveno\s*\n(.*?)(?=^## |\Z)", deep)
    for bullet in re.findall(r"(?m)^[-*] (.+)$", fixed.group(1) if fixed else ""):
        for token in jargon(bullet):
            bad.append(f"DEEP-PASS.md, Opraveno, carries code: {token!r} in {bullet[:60]!r}")
    problems = ([f"no Czech line for report #{i}" for i in missing]
                + [f"report #{i} is on the page since {since[:16]} and has no Czech title"
                   for i in shown if i not in missing]
                + bad)
    conclude(Measurement(
        verdict="failed" if problems else "passed",
        reason=("; ".join(problems[:6]) if problems else
                f"{len(lines)} reports have a plain Czech line and the deep pass names no code"),
        left={"problems": len(problems)}, right={"problems": 0},
        sources={"lines": "outbox/reports-cs.yaml", "deep_pass": "DEEP-PASS.md",
                 "journal": "state/journal/events.jsonl"}))

"""The morning report is Czech and plain (the operator, 2026-10-03).

*"zapominas ze ma byt vse degen friendly, takze to ma byt cesky a uplne srozumitelne o co
jde"* -- said over a report that named a filed bug by the English message of the check that
found it, and cut a line of the deep pass in the middle of a word.

Held here, not by memory:

* every report we filed has a one-sentence Czech line in `outbox/reports-cs.yaml`, written
  the day it is filed (the page shows that line and nothing else, `qa/morning.py::titles_from`);
* those lines are Czech, short, and carry no code name or file name;
* the deep pass's `Opraveno` bullets, which the page prints, carry none either.

SAFE: reads files in the repository.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude
from qa.morning import TITLE_LINE, jargon

REPO = Path(__file__).resolve().parent.parent.parent
# Reports from this number on must have a line (the older ones that were re-verified are in the
# file too, and are held only when they appear on the page).
FIRST_HELD = 136
CZECH_LETTER = re.compile(r"[ěščřžýáíéůúďťň]", re.I)


def _lines() -> dict:
    doc = yaml.safe_load((REPO / "outbox" / "reports-cs.yaml").read_text(encoding="utf-8")) or {}
    return {int(k): v for k, v in (doc.get("reports") or {}).items()}


def _filed_ids() -> set[int]:
    ledger = json.loads((REPO / "state" / "ledger.json").read_text(encoding="utf-8"))
    out = set()
    for finding in (ledger.get("findings") or {}).values():
        for filed in ((finding.get("filing") or {}).get("reports") or ()):
            rid = filed.get("report_id") if isinstance(filed, dict) else None
            if isinstance(rid, int):
                out.add(rid)
    return out


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_report_has_a_plain_czech_line_and_the_deep_pass_has_no_code_in_it():
    lines = _lines()
    missing = sorted(i for i in _filed_ids() if i >= FIRST_HELD and i not in lines)
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
    problems = [f"no Czech line for report #{i}" for i in missing] + bad
    conclude(Measurement(
        verdict="failed" if problems else "passed",
        reason=("; ".join(problems[:6]) if problems else
                f"{len(lines)} reports have a plain Czech line and the deep pass names no code"),
        left={"problems": len(problems)}, right={"problems": 0},
        sources={"lines": "outbox/reports-cs.yaml", "deep_pass": "DEEP-PASS.md"}))

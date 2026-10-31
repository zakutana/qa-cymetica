"""The Quant Lab's own text says what /how-it-fits says a winner starts (2026-10-31).

Two of Cymetica's surfaces tell an owner what happens when a Quant Lab search wins:

* `/how-it-fits` (and its plain text, `/how-it-fits.txt`, the same text in /llms.txt): since
  ET-33142, "A winner is started as a blank paper bot that trades the rule that won: the model's
  own buy and sell conditions (with the winning entry threshold) ... It needs no equipped model, so
  it holds for all 16 rules, paid models included", short (Red) rules excepted.
* the lab itself, `GET /api/v1/company/{id}/quant-lab/search` -> `what_it_does_not_do` and
  `cannot_tune`, which the Experiments page prints behind its "Can tune / can't" button.

**What was seen when this was written** (2026-10-31 about 22:30 UTC, our company 14, served with
`Cache-Control: no-store`): how-it-fits says the above, the same evening Nexus wrote on Telegram
that the fix is live. The lab still says "A result that won with a changed entry threshold is
reported only, not started as a paper bot: a paper bot cannot run a changed entry rule yet." (and a
`cannot_tune` row saying the same), "Premium models (prion, synapse, telomere): Not possible: the
platform sells these, so the lab never equips them for you." and "Cymetica bot set-ups as paper
bots (cryptobull_blue, ... stockbull_blue): Not possible: ... they can be searched but not
equipped."

**The rule.** Where how-it-fits promises that a winner of every long rule, Blue and paid included,
starts a paper bot, no `cannot_tune` row marked `not_possible` names a premium or paid model or a
Blue set-up; and where it promises the winning entry threshold is carried onto the bot, no lab text
says a changed entry threshold or rule is reported only or cannot be run by a paper bot. A
`not_possible` row about the Red (short) set-ups agrees with how-it-fits and passes.

NOT asserted: which of the two is true. Our company has never had a winner, so the bridge itself
cannot be watched here; the check holds two present statements against each other and passes when
they agree, whichever side moves. If how-it-fits stops promising the bridge it is inconclusive, not
a pass. The wording of either side, `what_changed`, and the "Coming soon" view of the page are not
judged.

SAFE: three GETs of our own company and one public page.
"""

from __future__ import annotations

import re

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude
from tests.rest.test_quant_lab_daily_search_completes import read_searches

CLAIM = "quant-lab-winner-text-agrees-with-how-it-fits"
DOC = "/how-it-fits.txt"

# What how-it-fits promises, read only from lines that speak of a blank paper bot.
_PROMISES = (
    ("every_long_rule", re.compile(r"holds for all 16 rules|paid models included|each of the three long Blue rules",
                                   re.I)),
    ("entry_threshold", re.compile(r"winning entry threshold", re.I)),
)
_BLANK = re.compile(r"\bblank (?:paper )?bot\b", re.I)
# What in the lab's text says the opposite.
_NOT_FOR_LONG = re.compile(r"premium|\bpaid\b|_blue\b", re.I)
_ENTRY = re.compile(r"cannot run a changed entry (?:rule|threshold)"
                    r"|changed entry (?:threshold|rule)\b[^.]*?\breported only", re.I)


def promises(text: str) -> dict[str, str]:
    """Each promise how-it-fits makes about a winner's blank paper bot, with the sentence that makes it."""
    found: dict[str, str] = {}
    for line in (text or "").splitlines():
        if not _BLANK.search(line):
            continue
        for sentence in re.split(r"(?<=[.!?])\s+", line):
            for key, pattern in _PROMISES:
                if key not in found and pattern.search(sentence):
                    found[key] = sentence.strip()
    return found


def denials(status: dict) -> dict[str, list[str]]:
    """The lab's own lines that deny a promise, by promise; only promises with at least one."""
    found: dict[str, list[str]] = {}
    for item in status.get("what_it_does_not_do") or []:
        if isinstance(item, str) and _ENTRY.search(item):
            found.setdefault("entry_threshold", []).append(item)
    for row in status.get("cannot_tune") or []:
        if not isinstance(row, dict):
            continue
        what, why, line = (str(row.get(k) or "") for k in ("what", "why", "line"))
        said = f"{what}: {line or why}"
        if row.get("feasibility") == "not_possible" and _NOT_FOR_LONG.search(f"{what} {why}"):
            found.setdefault("every_long_rule", []).append(said)
        if _ENTRY.search(f"{what} {why} {line}"):
            found.setdefault("entry_threshold", []).append(said)
    return found


def judge(promised: dict[str, str], denied: dict[str, list[str]]) -> tuple[str | None, dict]:
    """None when how-it-fits promises nothing; otherwise failed on any promise the lab denies."""
    if not promised:
        return None, {}
    conflicts = {k: {"how_it_fits": promised[k], "lab": denied[k]} for k in promised if denied.get(k)}
    return ("failed" if conflicts else "passed"), conflicts


@qa(component="rest.company", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_quant_lab_winner_text_agrees_with_how_it_fits(rest_trusted):
    """Our company's lab text against the public how-it-fits, on what a winning search starts."""
    cid, status, _searches = read_searches(rest_trusted)
    r = rest_trusted.get(DOC)
    if r.status_code != 200:
        raise Inconclusive(f"{DOC} answered HTTP {r.status_code}")
    promised = promises(r.text)
    denied = denials(status)
    verdict, conflicts = judge(promised, denied)
    if verdict is None:
        raise Inconclusive(f"{DOC} no longer promises what a winner's blank paper bot carries; "
                           f"nothing to hold the lab's text against")
    lab_lines = sorted({d for c in conflicts.values() for d in c["lab"]})
    conclude(Measurement(
        verdict=verdict,
        reason=(f"{DOC} promises a winner's blank paper bot " + " and ".join(
                    {"every_long_rule": "for every long rule, Blue and paid included",
                     "entry_threshold": "with the winning entry threshold"}[k] for k in conflicts)
                + f", while company {cid}'s Quant Lab says the opposite in {len(lab_lines)} lines: "
                + " | ".join(lab_lines)
                if conflicts else
                f"company {cid}'s Quant Lab text says nothing against the {len(promised)} promises {DOC} makes "
                f"about a winner's blank paper bot"),
        left={"promises_the_lab_denies": len(conflicts)},
        right={"allowed": 0, "promises": len(promised)},
        population={"promised": promised, "denied": denied},
        sources={"how_it_fits": DOC,
                 "lab": f"/api/v1/company/{cid}/quant-lab/search (what_it_does_not_do, cannot_tune)"},
        claim_id=CLAIM))

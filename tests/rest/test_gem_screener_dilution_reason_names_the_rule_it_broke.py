"""A near miss "held back" by dilution says it is over the weekly line when it is under it (2026-11-01).

The Dilution gate has two rules (`degen_gates`, rule_long): "1% of market cap a week at most in new
tokens ... under 25% of circulating in 12 months". The reason the page writes for a coin failing it has
one sentence for both (inline script of /gem-screener/app, read 2026-11-01):

    'heavy dilution': {en: 'heavy dilution', why: function(e){
      return 'New tokens are worth ' + dilPct(dilOf(e).week_pct) + ' of the market cap a week, over the line of ' + ...

So Solv Protocol, on the Near misses line, is labelled "New tokens are worth 0.7% of the market cap a
week, over the line of 1%": 0.71 is under 1, and what failed it is the other rule, 31.5% in 12 months.
Since ET-32480 the sentence has no hover tooltip; it is the cube's aria-label, which is what a screen
reader or an agent reading the page gets.

**The rule.** A reason states the rule the coin broke. Either fix passes, and both are written here on
day one: the sentence changes for a coin under the weekly line (it no longer returns that one sentence
unconditionally), or no row failing the gate sits under the weekly line (the gate lost its 12-month rule).

VERDICTS. failed: the reason is that one unconditional sentence and at least one row with heavy_dilution
has a known week_pct at or under the line. passed: the reason branches or says something else; or every
such row really is over the line. inconclusive: a read failed; the reason's entry is gone; no row fails
the gate.

NOT asserted: whether either limit is right, or the 12-month figure (the side panel's +31.5% is right).
SAFE: two anonymous GETs.
"""

from __future__ import annotations

import re

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

CLAIM = "gem-dilution-reason-names-the-rule-it-broke"
PAGE = "/gem-screener/app"
SNAPSHOT = "/api/v1/gem-screener"
FAIL = "heavy_dilution"

ENTRY = re.compile(r"'heavy dilution':\s*\{")
# Anchored on the return directly after the function opens: a branch before it no longer matches.
ONE_SENTENCE = re.compile(
    r"'heavy dilution':\s*\{[^{}]*why:\s*function\(e\)\{\s*return\s+'New tokens are worth '\s*\+\s*"
    r"dilPct\(dilOf\(e\)\.week_pct\)\s*\+\s*' of the market cap a week, over the line of '")


def under_the_line(apps: list[dict], line: float) -> list[dict]:
    """The rows failing the gate whose known weekly figure is at or under the line the sentence names."""
    rows = []
    for app in apps:
        week = (app.get("dilution") or {}).get("week_pct")
        if FAIL in (app.get("degen_fail") or []) and isinstance(week, (int, float)) and week <= line:
            rows.append(app)
    return rows


def verdict_for(one_sentence: bool, failing: int, under: int) -> str:
    """failed / passed / inconclusive from the three readings."""
    if not failing:
        return "inconclusive"
    return "failed" if one_sentence and under else "passed"


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_gem_screener_dilution_reason_names_the_rule_it_broke(rest_anon):
    """The page's reason, against the rows it is written for."""
    try:
        page = rest_anon.get(PAGE)
        snapshot = rest_anon.get(SNAPSHOT)
    except Exception as exc:  # noqa: BLE001 - a failed read is not an empty read (rule 8)
        raise Inconclusive(f"a read failed ({type(exc).__name__})")
    for name, resp in ((PAGE, page), (SNAPSHOT, snapshot)):
        if resp.status_code != 200:
            raise Inconclusive(f"{name} answered HTTP {resp.status_code}")
    if not ENTRY.search(page.text):
        raise Inconclusive(f"{PAGE} no longer has a 'heavy dilution' reason")
    try:
        data = snapshot.json()
        apps = data["apps"]
        meta = data.get("dilution_meta") or {}
        line = ((data.get("degen") or {}).get("rules") or {}).get("dilution_max_week_pct") or meta.get("gate_pct") or 1
    except Exception as exc:  # noqa: BLE001
        raise Inconclusive(f"{SNAPSHOT} was not the JSON expected ({type(exc).__name__})")
    one_sentence = bool(ONE_SENTENCE.search(page.text))
    failing = [a for a in apps if FAIL in (a.get("degen_fail") or [])]
    under = under_the_line(apps, line)
    verdict = verdict_for(one_sentence, len(failing), len(under))
    if verdict == "inconclusive":
        raise Inconclusive(f"no row of {len(apps)} fails the dilution gate: nothing to judge")
    sample = sorted(under, key=lambda a: -a["dilution"]["week_pct"])[:5]
    named = "; ".join(f"{a.get('symbol')} {a['dilution']['week_pct']:.2f}% a week, "
                      f"{a.get('sa_dilution_12m_pct')}% in 12 months" for a in sample)
    conclude(Measurement(
        verdict=verdict,
        reason=(f"The reason says \"over the line of {line}%\" for every coin failing the gate, and {len(under)} of "
                f"{len(failing)} are at or under that line: {named}. They fail the 12-month rule, which it does not name"
                if verdict == "failed" else
                f"{len(failing)} rows fail the gate, {len(under)} at or under the weekly line; "
                f"the one unconditional sentence is {'still there' if one_sentence else 'gone'}"),
        left={"one_unconditional_sentence": one_sentence, "rows_under_the_line": len(under)},
        right={"reason": "names the rule the coin broke"},
        population={"rows_failing_gate": len(failing), "line_pct_week": line,
                    "gate_12m_pct": meta.get("gate_12m_red_pct"),
                    "sample": [{"symbol": a.get("symbol"), "week_pct": a["dilution"]["week_pct"],
                                "pct_12m": a.get("sa_dilution_12m_pct")} for a in sample]},
        sources={"reason": f"{PAGE} inline script, the 'heavy dilution' entry",
                 "rows": f"{SNAPSHOT} apps[].degen_fail, .dilution.week_pct, .sa_dilution_12m_pct",
                 "snapshot_generated_at": data.get("generated_at_iso") or data.get("generated_at")},
        claim_id=CLAIM))

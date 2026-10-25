"""What the "a twelve-month dilution names where its new tokens come from" check reads (A07, deep pass 2026-10-25).

Three readers reproduced two holes in qa/gemaudit.py's DILUTION_LINE reading. It stopped at `.join(`, so a
fallback drawn after the join (`+ ((d.kinds || []).length ? '' : 'vesting schedule')`) was never seen
and a repaired page with kinds [] FAILED -- a false FAIL, #217's shape. And kinds [''] counted as a named
source, so a row the page prints with nothing after the dot passed. The 2026-10-18 readings stay in
tests/meta/test_pipeline_gem_audit.py.
"""

from __future__ import annotations

from qa import gemaudit as g
from qa.marks import SafetyTier, qa

LINE = ("function saDilLine(sp, sym){\n  var d = saDil(sp);\n"
        "  if (!d) return 'No schedule published: nothing is assumed in its place.';\n"
        "  return saTok(d.month_tokens) + ' new ' + (sym || 'tokens') + ' a month · ' + "
        "(d.kinds || []).join(' + ') +\n    (typeof d.net_of_buybacks_pct === 'number' ? '' : '');\n}\n")
JOIN = "(d.kinds || []).join(' + ')"


def _page(code: str = LINE) -> str:
    return "<html><script>" + code + "</script></html>"


def _row(sym, new, kinds, pct=10.0):
    return {"token": {"symbol": sym, "slug": sym.lower(), "gecko_id": sym.lower() + "-id"},
            "next_unlock": {"ts": 1801785600, "tokens": 69500000.0, "who": "Investors, Team"},
            "tiles": {"dilution_12m": {"pct": pct, "new_tokens_12m": new, "month_tokens": 0.0,
                                       "kinds": kinds, "schedule_known": True}}}


FINE = [_row(s, 1.0e8, ["vesting"]) for s in ("SOLV", "ARB", "HYPE", "ENA", "SUI")]
RNBW = _row("RNBW", 115833333.36, [], pct=64.35)


def _batch(*rows):
    return {"as_of": "2026-10-25T08:00:00+00:00", "items": [*rows, *FINE]}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_fallback_after_the_join_is_what_an_empty_list_prints():
    after = LINE.replace(JOIN, JOIN + " + ((d.kinds || []).length ? '' : 'vesting schedule')")
    said = g.dilution_source_breaches(_batch(RNBW), _page(after))
    assert said["verdict"] == "ok", said
    assert said.get("fallback") == "vesting schedule", said
    negated = LINE.replace(JOIN, JOIN + " + (!(d.kinds || []).length ? 'schedule and emissions' : '')")
    assert g.dilution_source_breaches(_batch(RNBW), _page(negated))["verdict"] == "ok"
    wrapped = LINE.replace(JOIN, "(" + JOIN + " || 'the published schedule')")
    assert g.dilution_source_breaches(_batch(RNBW), _page(wrapped))["verdict"] == "ok", (
        "an empty join is falsy: the fallback after || is what the row prints")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_fallback_that_prints_nothing_or_never_applies_is_none():
    blank = LINE.replace(JOIN, JOIN + " + ((d.kinds || []).length ? '' : '')")
    assert g.dilution_source_breaches(_batch(RNBW), _page(blank))["verdict"] == "failed", "a blank fallback names nothing"
    bound = LINE.replace(JOIN, JOIN + " || 'vesting'")
    assert g.dilution_source_breaches(_batch(RNBW), _page(bound))["verdict"] == "failed", (
        "unparenthesised, || binds to the whole non-empty line: the fallback never shows")
    unread = LINE.replace(JOIN, JOIN + " + ((d.kinds || []).length ? '' : FALLBACK_TEXT)")
    assert g.dilution_source_breaches(_batch(RNBW), _page(unread))["verdict"] == "unread", (
        "a fallback whose words are not in the line is not read as any")
    # The untouched line still fails on the row it was written for.
    assert g.dilution_source_breaches(_batch(RNBW), _page())["verdict"] == "failed"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_empty_or_blank_kind_is_not_a_source():
    for kinds in ([""], ["  "], [None], ["", ""]):
        said = g.dilution_source_breaches(_batch(_row("RNBW", 115833333.36, kinds, pct=64.35)), _page())
        assert said["verdict"] == "failed" and [b["row"] for b in said["breaches"]] == ["RNBW(rnbw)"], (kinds, said)
    said = g.dilution_source_breaches(_batch(_row("RNBW", 115833333.36, ["vesting", ""], pct=64.35)), _page())
    assert said["verdict"] == "ok", "one named kind beside a blank one names it"
    # A length fallback does not show for [''] (its length is 1): the row prints nothing after the dot.
    after = LINE.replace(JOIN, JOIN + " + ((d.kinds || []).length ? '' : 'vesting schedule')")
    said = g.dilution_source_breaches(_batch(_row("RNBW", 115833333.36, [""], pct=64.35)), _page(after))
    assert said["verdict"] == "failed", said
    # An || fallback does: [''] joins to '', which is falsy.
    wrapped = LINE.replace(JOIN, "(" + JOIN + " || 'the published schedule')")
    said = g.dilution_source_breaches(_batch(_row("RNBW", 115833333.36, [""], pct=64.35)), _page(wrapped))
    assert said["verdict"] == "ok", said

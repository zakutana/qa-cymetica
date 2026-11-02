"""The Gem Screener applies the rule it prints for apps under 180 days old.

The Vetted gate's `rule_long` says: "...at least 180 days of history... Newer
apps pass at $1M+ a month and growing." The snapshot carries the numbers behind
it (`vetted.young_min_rev30`, `vetted.min_days`, `vetted.min_mcap`,
`vetted.max_lag_days`), and each row carries `young` and `reliable_fail`.

An app under `min_days` of history, with 30-day revenue at or over
`young_min_rev30`, a growing six-month fit, a market cap over `min_mcap`, data
no older than `max_lag_days`, and no other reason to fail Vetted, must be
`young` -- or it is out of the Degen picks for a reason the page does not print.
2026-11-02: StonkFun, 98 days, $6.1M a month, +367 % a month, market cap $94M,
`reliable_fail: ["short_history"]` only, `young: false` -- it left the picks
where it had been first the day before. MASK, 40 days, $1.04M, +6 %, is young.

NOT asserted: that the 180-day rule or the $1M floor is right, or that a young
app belongs in the picks. A row that lacks a field the rule reads is skipped,
and a snapshot with no young app at all is INCONCLUSIVE.

SAFE: GETs only, anonymous.
"""

from __future__ import annotations

from qa import gemaudit as g
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude
from tests.rest.test_gem_screener_numbers_match_their_sources import read_snapshot


def _find(node, key):
    """First value stored under `key` anywhere in the snapshot."""
    if isinstance(node, dict):
        if key in node:
            return node[key]
        for v in node.values():
            found = _find(v, key)
            if found is not None:
                return found
    elif isinstance(node, list):
        for v in node:
            found = _find(v, key)
            if found is not None:
                return found
    return None


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_an_app_the_new_app_rule_admits_is_young(rest_anon):
    """Every app the printed rule for newer apps admits is flagged `young`."""
    snap = read_snapshot(rest_anon)
    vetted = _find(snap, "vetted")
    need = ("min_days", "young_min_rev30", "min_mcap", "max_lag_days")
    if not isinstance(vetted, dict) or any(not isinstance(vetted.get(k), (int, float)) for k in need):
        raise Inconclusive(f"the snapshot does not carry the Vetted numbers {need}")
    apps = snap.get("apps") or []
    admitted, flagged, missed = 0, 0, []
    for a in apps:
        days, rev = a.get("hist_days"), a.get("rev30d")
        mcap, lag = a.get("mcap"), a.get("lag_days")
        growth = (a.get("growth6m") or {}).get("g")
        if None in (days, rev, mcap, lag, growth) or days >= vetted["min_days"]:
            continue
        if (rev < vetted["young_min_rev30"] or growth <= 0 or mcap < vetted["min_mcap"]
                or lag > vetted["max_lag_days"]):
            continue
        if set(a.get("reliable_fail") or []) - {"short_history"}:
            continue
        admitted += 1
        if a.get("young") or a.get("reliable"):
            flagged += 1
        else:
            missed.append({"symbol": a.get("symbol"), "slug": a.get("slug"), "hist_days": days,
                           "rev30d": rev, "growth_pct_a_month": growth, "mcap": mcap,
                           "young": a.get("young"), "degen_fail": a.get("degen_fail")})
    if not any(a.get("young") for a in apps):
        raise Inconclusive("no app in the snapshot is flagged young, so the flag cannot be read")
    conclude(Measurement(
        verdict="failed" if missed else "passed",
        reason=(f"{len(missed)} of {admitted} apps the rule for newer apps admits are not young: "
                + "; ".join(f"{m['symbol']} ({m['hist_days']} days, ${m['rev30d']:,.0f} a month, "
                            f"{m['growth_pct_a_month']:+.0f} % a month)" for m in missed[:5])
                if missed else
                f"all {admitted} apps under {vetted['min_days']:.0f} days that meet the printed rule are young"),
        left={"admitted": admitted, "young": flagged},
        right={"not_young": 0},
        population={"missed": missed[:10], "rule": vetted},
        sources={"page": g.APP_PAGE}))

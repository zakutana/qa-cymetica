"""The Gem Screener's Degen Meter has a level for the coins it lists (2026-10-07).

The operator opened https://cymetica.com/gem-screener/app?view=apps and every row's Degen
meter was an empty dash. The page draws what the engine decided and nothing else
(`degenMeter()` reads `row.dlevel.level`, 1 to 10, and shows "not available" when it is
absent). The published snapshot, generated 2026-10-07 02:52 UTC: `dlevel` is null on all
232 apps and all 33 chains, `dlevel_meta` is null, and a coin's `degen_level` is None --
while `degen.n_ok` (the seven gates) says 8 of 232, so the gates ran and only the level did
not. The snapshot was seven hours old with its six-hour refresh overdue, and carried
CoinGecko 429 and DeFiLlama source warnings. On 2026-10-02 the same snapshot carried
`dlevel_meta.checks_run` and levels for nearly every row (outbox/et28378-recheck.md).

ASSERTS: at least half of the apps in the snapshot carry a level between 1 and 10. A column
that is empty on every row is a feature that is not there, however well the page handles it.
The cause is theirs to say; the check reads only the result.

NOT asserted: that a level is right, how it is computed, or what the page shows without one.
SAFE: one GET of the apps tab, anonymously. Read at its own URL (a page URL is its own cache
entry), and the snapshot's generated_at is in the reason.
"""

from __future__ import annotations

import time

import httpx

from qa import gemaudit as g
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude
from tests.rest.test_gem_screener_numbers_match_their_sources import get_patiently

APPS_PAGE = "/gem-screener/app?view=apps"
MIN_APPS = 50
MIN_SHARE = 0.5
CLAIM = "gem-screener-degen-meter-has-levels"


def _has_level(app: dict) -> bool:
    level = (app.get("dlevel") or {}).get("level") if isinstance(app.get("dlevel"), dict) else None
    return isinstance(level, (int, float)) and not isinstance(level, bool) and 1 <= level <= 10


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_the_degen_meter_has_a_level_for_the_coins_it_lists(rest_anon):
    """At least half of the Gem Screener's apps carry a Degen meter level from 1 to 10 in the published snapshot."""
    try:
        response = get_patiently(rest_anon, APPS_PAGE, headers={"Accept": "text/html"})
    except httpx.HTTPError as exc:
        raise Inconclusive(f"{APPS_PAGE} could not be read: {type(exc).__name__}")
    if response.status_code != 200:
        raise Inconclusive(f"{APPS_PAGE} answered HTTP {response.status_code}; "
                           f"a failed read is not an empty page")
    try:
        snap = g.parse_snapshot(response.text)
    except g.SnapshotUnreadable as exc:
        raise Inconclusive(f"{APPS_PAGE}: {exc}")
    apps = [a for a in snap.get("apps") or [] if isinstance(a, dict)]
    if len(apps) < MIN_APPS:
        raise Inconclusive(f"the snapshot carries {len(apps)} apps; fewer than {MIN_APPS} is not the tab")

    with_level = sum(1 for a in apps if _has_level(a))
    chains = [c for c in snap.get("chains") or [] if isinstance(c, dict)]
    chains_with = sum(1 for c in chains if _has_level(c))
    age = g.age_hours(snap, time.time())
    share = with_level / len(apps)
    conclude(Measurement(
        verdict="passed" if share >= MIN_SHARE else "failed",
        reason=(f"{with_level} of {len(apps)} apps carry a Degen meter level (1 to 10) in the snapshot "
                f"generated {snap.get('generated_at_iso') or snap.get('generated_at')}"
                f"{'' if age is None else f' ({age:.1f} h old)'}; chains {chains_with} of {len(chains)}; "
                f"dlevel_meta {'present' if snap.get('dlevel_meta') else 'null'}; "
                f"gates ran: degen.n_ok={(snap.get('degen') or {}).get('n_ok')} of "
                f"{(snap.get('degen') or {}).get('n_total')}; "
                f"fetch warnings {snap.get('fetch_warning_count')}"),
        left={"apps_with_level_share": round(share, 3)},
        right={"apps_with_level_share": f">= {MIN_SHARE}"},
        population={"apps": len(apps), "with_level": with_level, "chains": len(chains),
                    "chains_with_level": chains_with, "dlevel_meta_present": bool(snap.get("dlevel_meta")),
                    "snapshot_generated_at": snap.get("generated_at"), "age_hours": age,
                    "fetch_warning_count": snap.get("fetch_warning_count")},
        sources={"page": APPS_PAGE, "field": "apps[].dlevel.level (the page's degenMeter reads it)"},
        claim_id=CLAIM))

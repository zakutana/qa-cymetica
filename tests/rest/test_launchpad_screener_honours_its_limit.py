"""The launchpad screener returns at most the `limit` it was asked for.

Their published schema (`openapi-public.json`, GET
/api/v1/launchpad/onchain/screener) declares `limit` as an integer with
`default: 200` and `maximum: 500`, beside `include_external` (default `true`).
A limit is an upper bound on the rows that come back; that is the whole
meaning of the parameter, and it is what a caller sizes a page or a buffer
with.

**What was seen when this was written.** With `include_external` left at its
default, the endpoint applies the limit to each source separately and
concatenates: `limit=5` returned 10 rows, `limit=50` returned 100,
`limit=200` (the default) returned 400, and `limit=500` -- the documented
maximum -- returned 1000, about 2 MB. `include_external=false` returned
exactly 5 for `limit=5`, so the doubling is the external half being added on
top rather than counted in.

The two halves are not the same shape either: the EventTrader rows carry the
full field set (`current_price`, `market_cap`, `total_supply`, `holder_count`,
...), while the external ones (`source` `pons` or `pools_trade`) carry fifteen
fields, several of them null. That is reported in `population` as context --
their schema declares the items only as `type: object`, so a mixed shape is
not a broken promise, and a check that asserted a field set here would be
inventing a contract they never published.

**Measured on more than one limit** so a single lucky page cannot decide it,
and the ratio is reported rather than assumed: if they later count external
rows toward the limit, this passes without being rewritten.
"""

from __future__ import annotations

import time

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

SCREENER = "/api/v1/launchpad/onchain/screener"
LIMITS = (5, 50)
PAUSE_S = 1.5


@qa(component="chain.launchpad", tier=SafetyTier.SAFE, surface="rest",
    claim="launchpad-screener-honours-its-limit")
def test_the_screener_returns_no_more_rows_than_the_limit_asked_for(rest_anon):
    """limit=N, with their own default for include_external, returns <= N rows."""
    seen, unmeasured = [], []
    for limit in LIMITS:
        time.sleep(PAUSE_S)
        response = rest_anon.get(SCREENER, params={"limit": limit})
        if response.status_code != 200:
            unmeasured.append(f"limit={limit}: HTTP {response.status_code}")
            continue
        rows = response.json()
        if not isinstance(rows, list):
            unmeasured.append(f"limit={limit}: the body is not a list of rows")
            continue
        external = sum(1 for r in rows if isinstance(r, dict)
                       and "current_price" not in r)
        seen.append({"limit": limit, "rows": len(rows),
                     "external_shape": external,
                     "ratio": round(len(rows) / limit, 2) if limit else None})

    if not seen:
        raise Inconclusive("the screener could not be read: "
                           + "; ".join(unmeasured))

    over = [s for s in seen if s["rows"] > s["limit"]]
    worst = max(over, key=lambda s: s["rows"] / s["limit"]) if over else None
    conclude(Measurement(
        verdict="failed" if over else "passed",
        reason=(f"the screener returned more rows than its own limit on "
                f"{len(over)} of {len(seen)} reads -- worst limit="
                f"{worst['limit']} answered {worst['rows']} rows "
                f"({worst['ratio']}x), of which {worst['external_shape']} carry "
                f"the external row shape; their schema declares limit with "
                f"default 200 and maximum 500"
                if over else
                f"every read returned at most its limit "
                f"({', '.join(str(s['limit']) + '->' + str(s['rows']) for s in seen)})"),
        left=[s["rows"] for s in seen], right=[s["limit"] for s in seen],
        population={"reads": seen, "unmeasured": unmeasured},
        sources={"contract": "openapi-public.json, GET "
                             "/api/v1/launchpad/onchain/screener: limit "
                             "(default 200, maximum 500)",
                 "endpoint": SCREENER},
        claim_id="launchpad-screener-honours-its-limit"))

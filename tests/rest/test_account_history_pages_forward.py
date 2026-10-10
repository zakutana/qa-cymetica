"""The account's transaction history pages forward.

The contract is the endpoint's own answer: `GET /api/v1/account/me/transactions` returns
`{transactions, has_more, total_count}` and takes `limit` (at most 100, its own 422 says so)
and `offset`. When `has_more` is true, the next offset holds the next rows. The Transaction
History page (/transactions) reads this endpoint; it is in none of llms.txt, llms-full.txt or
the OpenAPI documents (2026-10-10).

**What was seen when this was written** (2026-10-10, our own account): with `currency=ET10`,
offsets 0, 100 and 200 answered three different pages, 652 rows in all. With `currency=USDC`
every offset (0, 100, 200, 900, 1000, 2000) answered the same 100 rows, ids 1613303830 to
371000858, `total_count` 1000 and `has_more` true up to offset 800; with no filter, offset 100
and every later one answered the same page. Only `from_date` / `to_date` reached older rows, so
an account cannot read its own USDC history past the newest 100 by paging.

**The rule.** For the unfiltered history, `currency=USDC` and `currency=ET10`, offsets 0, 100
and 200: when a page says `has_more`, the next one is not a repeat of it. An overlap of a few
rows (one added between the reads) is not a repeat; the same ids are.

SAFE. GETs only, our own account's read key.
"""

from __future__ import annotations

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

HISTORY = "/api/v1/account/me/transactions"
LIMIT = 100
FILTERS = ({}, {"currency": "USDC"}, {"currency": "ET10"})
OFFSETS = (0, LIMIT, 2 * LIMIT)


def page_repeats(first: list[dict], second: list[dict], *, has_more) -> bool | None:
    """True when the next page is the first page again; None when nothing was promised."""
    ids1 = [r.get("id") for r in first or [] if isinstance(r, dict)]
    ids2 = [r.get("id") for r in second or [] if isinstance(r, dict)]
    if has_more is not True or not ids1:
        return None
    return bool(ids2) and set(ids2) <= set(ids1)


@qa(component="rest.account", tier=SafetyTier.SAFE, surface="rest")
def test_the_account_history_pages_forward(rest_trusted):
    """Offset 100 of the history is a new page wherever the first page says there is more."""
    judged, repeats, unread = [], [], []
    for params in FILTERS:
        label = params.get("currency") or "no filter"
        pages = []
        for offset in OFFSETS:
            r = rest_trusted.get(HISTORY, params={"limit": LIMIT, "offset": offset, **params})
            body = r.json() if r.status_code == 200 else None
            if not isinstance(body, dict) or not isinstance(body.get("transactions"), list):
                unread.append(f"{label} offset {offset}: HTTP {r.status_code}")
                break
            pages.append((offset, body))
        for (o1, p1), (o2, p2) in zip(pages, pages[1:]):
            seen = page_repeats(p1["transactions"], p2["transactions"], has_more=p1.get("has_more"))
            if seen is None:
                continue
            row = {"filter": label, "offsets": [o1, o2], "total_count": p1.get("total_count"),
                   "ids": [p1["transactions"][0].get("id"), p1["transactions"][-1].get("id")],
                   "next_ids": [p2["transactions"][0].get("id"), p2["transactions"][-1].get("id")]}
            judged.append(row)
            if seen:
                repeats.append(row)
    if not judged:
        raise Inconclusive(f"no history read had a second page to judge: {unread or 'has_more false everywhere'}")
    conclude(Measurement(
        verdict="failed" if repeats else "passed",
        reason=(f"{len(repeats)} of {len(judged)} page turns of the history answer the same page again while "
                f"it says has_more: "
                + "; ".join(f"{r['filter']} (total_count {r['total_count']}) offset {r['offsets'][0]} -> "
                            f"{r['offsets'][1]}: ids {r['ids'][0]}..{r['ids'][1]} both times"
                            for r in repeats)
                if repeats else
                f"all {len(judged)} page turns of the history move forward"),
        left={"reads_repeating_page_one": len(repeats), "judged": len(judged)},
        right={"reads_repeating_page_one": 0},
        population={"judged": judged, "unread": unread},
        sources={"history": HISTORY}))

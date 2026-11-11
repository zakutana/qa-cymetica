"""The 111.220977 USDC taken as "ET10 capital call set-off" came back to the wallet (2026-11-11, report #317).

Read from `GET /api/v1/account/me/transactions` on 2026-11-06: two ADJUSTMENT rows, USDC, -21.220977 (25 Oct) and
-90.000000 (30 Oct), "ET10 capital call set-off ...", which NEXUS called "a second charge, and it was our error". On
2026-11-08 18:28:37 UTC two USDC TRANSFER_IN rows appeared, both "Balance adjustment", 102.202388 and 9.018589: together
exactly 111.220977. The ledger never says they are the return, so this reads it by the amount.

**The rule.** The USDC credited after the last set-off, by TRANSFER_IN "Balance adjustment" rows, is at least what the
set-offs took.

VERDICTS. failed: credits after the last set-off are smaller than the set-offs. passed: they are at least as large.
inconclusive: the ledger could not be read in full, or holds no set-off row (nothing to compare).

NOT asserted: that the credits are labelled as the return (the label is generic), or any other balance.
SAFE: GETs only; the key is sent by the client in the header and never printed or recorded.
"""

from __future__ import annotations

from decimal import Decimal

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

CLAIM = "set-off-took-111-usdc-acknowledged-not-returned"
URL = "/api/v1/account/me/transactions"


SINCE = "2026-10-24"   # the set-offs are of 25 and 30 Oct; the ledger is newest first, 20 rows a page, 5,600 rows in all


def _ledger(client) -> list[dict]:
    """The ledger down to SINCE (newest first); not the whole of it."""
    rows: list[dict] = []
    for offset in range(0, 2000, 20):
        try:
            got = client.get(f"{URL}?offset={offset}")
        except Exception as exc:  # noqa: BLE001 - a failed read is not an empty read
            raise Inconclusive(f"{URL} could not be read ({type(exc).__name__})")
        if got.status_code != 200:
            raise Inconclusive(f"{URL}?offset={offset} answered HTTP {got.status_code}")
        body = got.json()
        page = body.get("transactions") or []
        rows += page
        if not body.get("has_more") or (page and str(page[-1]["created_at"]) < SINCE):
            return rows
    raise Inconclusive(f"2000 rows read and still newer than {SINCE}")


@qa(component="rest.account", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_the_set_off_was_returned_to_the_wallet(rest_trusted):
    """The USDC credited after the last set-off, against what the set-offs took."""
    rows = _ledger(rest_trusted)
    set_offs = [r for r in rows if r.get("currency") == "USDC" and r.get("type") == "ADJUSTMENT"
                and "set-off" in str(r.get("description") or "")]
    if not set_offs:
        raise Inconclusive("no 'set-off' ADJUSTMENT row in the ledger; nothing to compare")
    taken = -sum(Decimal(str(r["amount"])) for r in set_offs)
    last = max(str(r["created_at"]) for r in set_offs)
    credits = [r for r in rows if r.get("currency") == "USDC" and r.get("type") == "TRANSFER_IN"
               and "Balance adjustment" in str(r.get("description") or "") and str(r["created_at"]) > last]
    back = sum(Decimal(str(r["amount"])) for r in credits)
    conclude(Measurement(
        verdict="passed" if back >= taken else "failed",
        reason=(f"set-offs took {taken} USDC (last {last[:10]}); 'Balance adjustment' credits after it: {back} USDC "
                f"in {len(credits)} rows"),
        left={"credited_back_usdc": str(back)},
        right={"taken_usdc": str(taken)},
        population={"ledger_rows": len(rows), "set_off_rows": len(set_offs), "credit_rows": len(credits)},
        sources={"ledger": f"GET {URL} (newest first, down to 24 Oct)", "credential": "X-API-Key, trusted tier (value never recorded)"},
        claim_id=CLAIM))

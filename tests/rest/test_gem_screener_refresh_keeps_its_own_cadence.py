"""Gem Screener's own status says its refresh is stuck, not just late.

`GET /api/v1/gem-screener/status` publishes its own promise:
`refresh_every_seconds` (21600 -- 6 hours) and `next_refresh_due_at`. The page
that keeps the last snapshot that passed its audits (a correct design: a
failed rebuild should never replace a good one with a broken one) reads as
current regardless, because it carries no visible health state (community
review via the operator, 2026-09-27).

**What was seen when this was written** (2026-09-27, two reads 30 minutes
apart, 13:48 and 14:18 UTC): `age_seconds` 147,556 then 149,394 (~41 hours)
against `refresh_every_seconds` 21,600 (6 hours); the snapshot's
`generated_at` is 2026-09-25 20:49 UTC on both; both reads' `last_attempt`
is `ok: false` at `audit:audit_sectors.py`, with a newer `finished_at` on the
second -- so attempts keep running and failing, and none publishes.
`next_refresh_due_at` is itself a day in the past. How many attempts failed
in between is not published, so it is not claimed.

**The bar, so a normal late cycle never fails this:** the snapshot must be
stale by more than 3 refresh cycles (age_seconds > 3 * refresh_every_seconds)
AND the newest attempt must be a recorded failure (`last_attempt.ok is
False`). Merely late, or stale with a successful newest attempt, passes. A
missing or zero field is INCONCLUSIVE -- a failed read is not a healthy one.

**Guard against a one-off blip:** two reads, `PAUSE_S` apart. Both must show
the same stuck signature (`last_attempt.ok is False` and the same
`generated_at`, i.e. no snapshot published between them) before this fails --
a rebuild that succeeds between the two reads is the mechanism recovering on
its own, not a defect to report.

SAFE: two anonymous GETs of one endpoint, no key, no write.
"""

from __future__ import annotations

import time

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

STATUS = "/api/v1/gem-screener/status"
STUCK_MULTIPLE = 3
PAUSE_S = 30.0


def _read(rest_anon) -> dict:
    response = rest_anon.get(STATUS)
    if response.status_code != 200:
        raise Inconclusive(f"{STATUS} answered HTTP {response.status_code}; "
                           f"a failed read is not an empty one")
    try:
        return response.json() or {}
    except ValueError:
        raise Inconclusive(f"{STATUS} answered 200 with a body that is not JSON")


def _stuck(data: dict) -> tuple[bool | None, str]:
    """(True stuck / False not stuck / None unreadable, why). Never raises: a
    missing or zero field is unreadable, never taken to mean "healthy"."""
    age = data.get("age_seconds")
    every = data.get("refresh_every_seconds")
    attempt = data.get("last_attempt") or {}
    if not isinstance(age, (int, float)) or not isinstance(every, (int, float)) or not every:
        return None, "no readable age_seconds/refresh_every_seconds"
    if age <= STUCK_MULTIPLE * every:
        return False, f"age {age}s is within {STUCK_MULTIPLE}x the {every}s cadence"
    if attempt.get("ok") is not False:
        return False, "stale, but the newest attempt is not a recorded failure"
    return True, (f"age {age}s is {age / every:.1f}x the {every}s cadence, and "
                  f"the newest attempt failed at {attempt.get('stage')!r}")


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest",
    claim="gem-screener-refresh-stuck-past-its-cadence")
def test_the_refresh_is_late_and_the_newest_attempt_failed_twice_running(rest_anon):
    """A stale snapshot alone is not a defect; a pipeline stuck re-failing the
    same step for multiple cycles, with no visible health state, is."""
    first = _read(rest_anon)
    stuck_first, why_first = _stuck(first)
    if stuck_first is None:
        raise Inconclusive(f"{STATUS}: {why_first}")
    if not stuck_first:
        conclude(Measurement(
            verdict="passed",
            reason=f"not stuck: {why_first}",
            left={"stuck": False}, right={"stuck": False},
            population={"first_read": first},
            sources={"status": STATUS}, claim_id="gem-screener-refresh-stuck-past-its-cadence"))
        return

    time.sleep(PAUSE_S)
    second = _read(rest_anon)
    stuck_second, why_second = _stuck(second)
    if stuck_second is None:
        raise Inconclusive(f"{STATUS} on the second read: {why_second}")
    recovered = second.get("generated_at") != first.get("generated_at")

    if recovered or not stuck_second:
        conclude(Measurement(
            verdict="passed",
            reason=(f"stuck on the first read ({why_first}) but recovered by the "
                    f"second, {PAUSE_S}s later: "
                    + ("a new snapshot published" if recovered else why_second)),
            left={"stuck_first": True, "stuck_second": stuck_second, "recovered": recovered},
            right={"stuck_second": False},
            population={"first_read": first, "second_read": second},
            sources={"status": STATUS}, claim_id="gem-screener-refresh-stuck-past-its-cadence"))
        return

    conclude(Measurement(
        verdict="failed",
        reason=(f"{STATUS} shows the refresh stuck on two reads {PAUSE_S}s apart, "
                f"same unpublished snapshot (generated_at {first.get('generated_at')}): "
                f"{why_first}; second read: {why_second}"),
        left={"stuck_first": True, "stuck_second": True, "recovered": False},
        right={"stuck_second": False},
        population={"first_read": first, "second_read": second},
        sources={"status": STATUS}, claim_id="gem-screener-refresh-stuck-past-its-cadence"))

"""The Quant Lab's daily search completes (2026-10-30).

The Quant Lab (Build a Company, page /company/app/experiments) backtests 16 model rules on 12 crypto
markets for a Pro owner. Its page says "The lab searches by itself every day", and when a search
fails, "The last search stopped: <error>. It tries again on the next pass." The owner's API:
`GET /api/v1/company/{id}/quant-lab/search` (`search`, the newest; `last_finished`, the last one
that completed) and `GET .../quant-lab/search/results?limit=12` (`searches`, the history).

**What was seen when this was written** (2026-10-30 13:57 UTC, our company 14, plan Pro, access
allowed): searches #9 (daily, requested 2026-10-30 10:09 UTC), #7 (daily, 2026-10-29 10:09) and #5
(origin owner, 2026-10-28 10:09) all `status: failed`, `total_jobs: 0`, `started_at: null`, each
finished 40 to 85 s after it was requested, each with the same error: "OperationalError:
(psycopg2.OperationalError) server closed the connection unexpectedly ... [SQL: SELECT
company_quant_combos.combo_key ... FROM company_quant_combos WHERE company_quant_combos.company_id =
...". The last search that completed is #3, finished 2026-10-27 14:01 UTC (1,728 combinations):
72 hours, three daily passes, before the read. The next pass did try again, and failed again at the
same query.

**The rule.** The newest search, read off `requested_at`, has not failed after more than 48 hours
(two daily passes) without one completing: the last completed search (`status: done`, from the list
or from `last_finished`) finished within 48 hours of the read, or the newest search is not a failed
one. With no completion at all, the 48 hours run from the oldest search listed. A newest search
still queued or running is not judged; nor is a company whose plan the lab is not open to.

NOT asserted: why it fails, how long a search takes, what it finds, the 10:09 hour, or the error's
wording (that is the sibling check, `test_quant_lab_search_error_names_no_internals`). One failure
the next pass recovers from passes, as their page promises. If the lab stops searching daily on
purpose, the check is retired by an event, not left red.

SAFE: three GETs of our own company.
"""

from __future__ import annotations

from datetime import datetime, timezone

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

CLAIM = "quant-lab-daily-search-completes"
MINE = "/api/v1/company/mine"
MAX_HOURS = 48
LIMIT = 12


def _at(value) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _brief(s: dict) -> dict:
    return {k: s.get(k) for k in ("id", "origin", "requested_at", "started_at", "finished_at", "total_jobs")}


def stall(searches: list[dict], last_finished: dict | None, now: datetime) -> dict:
    """The verdict on a company's search history: "failed" when the newest search failed and none
    completed in the last MAX_HOURS, "passed" otherwise, None when there is nothing to judge (no
    search, or the newest still queued or running). With the failed run and the last completion."""
    rows = sorted((s for s in searches or [] if isinstance(s, dict) and _at(s.get("requested_at"))),
                  key=lambda s: _at(s["requested_at"]), reverse=True)
    out: dict = {"verdict": None, "failed_in_a_row": [], "last_completed": None, "hours_since_completed": None}
    if not rows:
        return out
    run = []
    for s in rows:
        if s.get("status") != "failed":
            break
        run.append(_brief(s))
    out["failed_in_a_row"] = run
    done = [s for s in rows + ([last_finished] if isinstance(last_finished, dict) else [])
            if s.get("status") == "done" and _at(s.get("finished_at"))]
    last = max(done, key=lambda s: _at(s["finished_at"]), default=None)
    since = _at(last["finished_at"]) if last else _at(rows[-1]["requested_at"])
    out["last_completed"] = _brief(last) if last else None
    out["hours_since_completed"] = round((now - since).total_seconds() / 3600, 1)
    newest = rows[0].get("status")
    if newest in ("queued", "running"):
        return out
    out["verdict"] = "failed" if newest == "failed" and out["hours_since_completed"] > MAX_HOURS else "passed"
    return out


def _json(client, path: str) -> dict:
    r = client.get(path)
    if r.status_code != 200:
        raise Inconclusive(f"{path} answered HTTP {r.status_code}")
    try:
        body = r.json()
    except ValueError:
        raise Inconclusive(f"{path} answered something that is not JSON") from None
    if not isinstance(body, dict):
        raise Inconclusive(f"{path} answered {type(body).__name__}, not an object")
    return body


def read_searches(client) -> tuple[int, dict, list[dict]]:
    """Our company's id, its /search status and its search history; Inconclusive when unreadable."""
    mine = _json(client, MINE)
    company = mine.get("company") if isinstance(mine.get("company"), dict) else mine
    cid = company.get("id")
    if not isinstance(cid, int):
        raise Inconclusive(f"{MINE} names no company id")
    status = _json(client, f"/api/v1/company/{cid}/quant-lab/search")
    access = status.get("access") or {}
    if access.get("allowed") is not True:
        raise Inconclusive(f"the Quant Lab is not open to company {cid} (plan {access.get('plan')!r})")
    history = _json(client, f"/api/v1/company/{cid}/quant-lab/search/results?limit={LIMIT}")
    searches = history.get("searches")
    if not isinstance(searches, list):
        raise Inconclusive("the search results carry no `searches` list")
    newest = status.get("search")
    if isinstance(newest, dict) and newest.get("id") not in {s.get("id") for s in searches if isinstance(s, dict)}:
        searches = [newest] + searches
    return cid, status, searches


@qa(component="rest.company", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_quant_lab_daily_search_completes(rest_trusted):
    """Our company's search history against the day it promises."""
    cid, status, searches = read_searches(rest_trusted)
    now = datetime.now(timezone.utc)
    out = stall(searches, status.get("last_finished"), now)
    if out["verdict"] is None:
        newest = max(searches, key=lambda s: _at(s.get("requested_at")) or now, default=None)
        raise Inconclusive(f"nothing to judge: {'no search yet' if not searches else 'the newest search is '}"
                           f"{(newest or {}).get('status') or ''} (company {cid})")
    run, last = out["failed_in_a_row"], out["last_completed"]
    errors = {str(s.get("error") or "").split("\n")[0][:120] for s in searches
              if s.get("id") in {r["id"] for r in run}}
    failed = out["verdict"] == "failed"
    conclude(Measurement(
        verdict=out["verdict"],
        reason=(f"the last {len(run)} searches of company {cid} all failed before any job ran ("
                + ", ".join(f"#{r['id']} {r['origin']} {str(r['requested_at'])[:10]}, {r['total_jobs']} jobs, "
                            + ("never started" if r["started_at"] is None else f"started {r['started_at']}")
                            for r in run)
                + f"), {'with the same error' if len(errors) == 1 else 'with errors'} "
                + "; ".join(repr(e) for e in sorted(errors))
                + (f"; the last search that completed is #{last['id']}, finished {last['finished_at']}, "
                   if last else "; no search has ever completed, the oldest listed was requested ")
                + f"{out['hours_since_completed']} h before this read (allowed {MAX_HOURS} h, two daily passes)"
                if failed else
                f"a search completed {out['hours_since_completed']} h before this read"
                + (f" (#{last['id']}, finished {last['finished_at']})" if last else "")
                + f", or the newest is not a failure; {len(run)} failed since"),
        left={"hours_since_a_search_completed": out["hours_since_completed"],
              "failed_in_a_row": len(run)},
        right={"allowed_hours": MAX_HOURS},
        population={"failed_in_a_row": run, "last_completed": last, "errors": sorted(errors),
                    "searches_listed": len(searches)},
        sources={"status": f"/api/v1/company/{cid}/quant-lab/search (search, last_finished)",
                 "history": f"/api/v1/company/{cid}/quant-lab/search/results?limit={LIMIT} (searches)",
                 "contract": "the page: 'The lab searches by itself every day' and 'It tries again on the next pass'"},
        claim_id=CLAIM))

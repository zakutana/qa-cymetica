"""Build a Company's heartbeat promises only a pass that comes (2026-10-15, ET-31466).

`GET /api/v1/company/mine` carries `heartbeat` {last_pass_at, next_pass_at, pass_every_s}: when the
runner last passed over the company and when it will pass next. ET-31466 put it on the owner's
company bar ("heartbeat (last turn / next pass)").

**What was seen when this was written** (2026-10-15, our company 13, paused since 2026-10-13 and
`run_state` "Paused: nothing runs and nothing is charged until you resume."). Every read gave a
`next_pass_at` 30 to 32 s after the read itself -- 19:47:25 -> 19:47:56, 20:15:31 -> 20:16:01,
20:16:12 -> 20:16:42 -- while `last_pass_at` stayed 19:41:17 and `pass_every_s` said 120. The
pass promised for 20:16:01 had not come by 20:16:12; the next read simply promised another.

**The rule.** Read the heartbeat, wait until 20 s after the `next_pass_at` it names, read again: a
pass ran (the second `last_pass_at` is at or after the promised time, 2 s of slack), or the second
read no longer promises one. A heartbeat that names no next pass promised nothing and is not judged.

NOT asserted: whether a paused company should pass at all, the 120 s cadence, or anything the
pass does. A fix that drops `next_pass_at` while paused and one that really passes both pass.

SAFE: two GETs of our own company, at most 200 s apart.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

CLAIM = "company-heartbeat-keeps-its-promise"
MINE = "/api/v1/company/mine"
AFTER_S = 20
MAX_WAIT_S = 180
SLACK_S = 2


def _at(value) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def broken_promise(first: dict, second: dict) -> bool | None:
    """True when the pass `first` promised did not come by `second`; None when nothing was promised."""
    promised = _at((first or {}).get("next_pass_at"))
    if promised is None:
        return None
    last = _at((second or {}).get("last_pass_at"))
    if last is not None and last.timestamp() >= promised.timestamp() - SLACK_S:
        return False
    if (second or {}).get("next_pass_at") is None:
        return False
    return True


def _heartbeat(client) -> tuple[dict, dict]:
    r = client.get(MINE)
    if r.status_code != 200:
        raise Inconclusive(f"{MINE} answered HTTP {r.status_code}")
    body = r.json() or {}
    company = body.get("company") if isinstance(body.get("company"), dict) else body
    beat = body.get("heartbeat") or company.get("heartbeat")
    if not isinstance(beat, dict):
        raise Inconclusive(f"{MINE} carries no heartbeat")
    return beat, (body.get("run_state") or company.get("run_state") or {})


@qa(component="rest.company", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_company_heartbeat_keeps_its_promise(rest_trusted):
    """Two reads of our company's heartbeat, the second after the pass the first promised."""
    first, state = _heartbeat(rest_trusted)
    promised = _at(first.get("next_pass_at"))
    if promised is None:
        raise Inconclusive(f"the heartbeat names no next pass ({first}); nothing promised")
    wait = promised.timestamp() + AFTER_S - datetime.now(timezone.utc).timestamp()
    if wait > MAX_WAIT_S:
        raise Inconclusive(f"the next pass is {wait:.0f} s away, past the {MAX_WAIT_S} s this waits")
    time.sleep(max(0.0, wait))
    second, state2 = _heartbeat(rest_trusted)
    broken = broken_promise(first, second)
    conclude(Measurement(
        verdict="failed" if broken else "passed",
        reason=(f"the heartbeat promised a pass at {first.get('next_pass_at')}; read {AFTER_S} s after "
                f"it, the last pass is still {second.get('last_pass_at')} and the next is now promised "
                f"for {second.get('next_pass_at')} (pass_every_s {second.get('pass_every_s')}, "
                f"run_state {state2.get('state')!r})"
                if broken else
                f"the pass promised at {first.get('next_pass_at')} came (last pass "
                f"{second.get('last_pass_at')}) or is no longer promised"),
        left={"promised_pass_missed": bool(broken)},
        right={"promised_pass_missed": False},
        population={"first": first, "second": second, "run_state": state2.get("state"),
                    "run_state_message": state2.get("message")},
        sources={"heartbeat": f"{MINE} heartbeat {{last_pass_at, next_pass_at, pass_every_s}}",
                 "contract": "ET-31466: the company bar's heartbeat, last turn and next pass"},
        claim_id=CLAIM))

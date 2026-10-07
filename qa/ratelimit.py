"""One brake on how fast we ask any host, shared by every process.

Cymetica asked us on 2026-09-20 (REPLY-0030) to leave load and volume testing
alone. From 2026-09-28 to 2026-10-06 we sent them 68,487 requests anyway: 187 in
one minute from a single test, and 256 answers of HTTP 429 on two routes that
allow 30 a minute. Nothing read a 429 or its Retry-After, and the only brake,
`RateLimitBudget`, was per process and never slept.

So the brake lives in the transport every client is built with
(`qa/client.py` passes `shared()` to `SafetyTransport` for the real network),
and its state lives in one file under `state_dir()`. The console's collectors,
the lab tick and a sweep running at the same time share one minute:

  * a host gets at most PER_MINUTE requests a minute, by reservation: each
    request takes the next free slot and sleeps until it;
  * a route that announces a smaller allowance (`x-ratelimit-limit` under
    PER_MINUTE) is paced by that allowance too, and one whose allowance is used
    up (`x-ratelimit-remaining: 0`) waits for its `x-ratelimit-reset`;
  * a 429 waits for Retry-After (at most MAX_RETRY_AFTER_S) and a READ is asked
    once more. A write is never sent twice: a POST answered 429 may have landed.

The lock is held only while a slot is computed, never while sleeping: holding it
through a long wait would stall every other process's timings write too
(`qa/timings.py` shares `file_lock`). A file that cannot be locked or read does
not stop a request; that request waits one host interval on its own instead.
"""

from __future__ import annotations

import json
import time
from email.utils import parsedate_to_datetime
from pathlib import Path

from qa.state import file_lock, state_dir

PER_MINUTE = 60
MAX_RETRY_AFTER_S = 120.0
DEFAULT_RETRY_AFTER_S = 30.0
RETRY_METHODS = frozenset({"GET", "HEAD"})


def may_retry(method: str) -> bool:
    """Only a read is asked twice."""
    return method.upper() in RETRY_METHODS


def retry_after(response) -> float:
    """Their Retry-After in seconds (a number or an HTTP date), capped; absent or
    unreadable is DEFAULT_RETRY_AFTER_S, never zero."""
    raw = (response.headers.get("retry-after") or "").strip()
    seconds = None
    if raw:
        try:
            seconds = float(raw)
        except ValueError:
            try:
                seconds = parsedate_to_datetime(raw).timestamp() - time.time()
            except (TypeError, ValueError):
                seconds = None
    if seconds is None or seconds < 0:
        seconds = DEFAULT_RETRY_AFTER_S
    return min(seconds, MAX_RETRY_AFTER_S)


def route_key(url) -> str:
    """The host and the first three path segments: /api/v1/chart-analyzer,
    /mcp/v1 -- the granularity their per-route allowances are announced at."""
    parts = [p for p in str(url.path).split("/") if p][:3]
    return f"{url.host}/{'/'.join(parts)}"


class Pacer:
    def __init__(self, path: Path | None = None, per_minute: int = PER_MINUTE,
                 now=time.time, sleep=time.sleep):
        self.path = Path(path) if path is not None else state_dir() / "pace.json"
        self.interval = 60.0 / per_minute
        self.now, self.sleep = now, sleep

    # -- state ------------------------------------------------------------
    def _read(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def _update(self, change) -> object:
        """Apply `change(state) -> result` under the lock and write it back."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with file_lock(self.path):
            state = self._read()
            result = change(state)
            self.path.write_text(json.dumps(state), encoding="utf-8")
        return result

    # -- the brake --------------------------------------------------------
    def wait(self, request) -> float:
        """Take the next free slot for this request's host and route; sleep until it."""
        host, route = f"host:{request.url.host}", f"route:{route_key(request.url)}"

        def reserve(state: dict) -> float:
            now = self.now()
            nexts = state.setdefault("next", {})
            # The host slot is taken where the HOST is free, not where this route
            # is: a request held on its route must not push every other route of
            # the host -- in every process -- back behind it (code review,
            # 2026-10-07). The held request may then share a second with another;
            # that is the cost, and it is one request.
            host_slot = max(now, nexts.get(host, 0.0))
            slot = max(host_slot, nexts.get(route, 0.0))
            nexts[host] = host_slot + self.interval
            gap = state.get("route_interval", {}).get(route)
            if gap:
                nexts[route] = max(nexts.get(route, 0.0), slot + gap)
            return slot - now

        try:
            delay = self._update(reserve)
        except OSError:
            delay = self.interval
        if delay > 0:
            self.sleep(delay)
        return max(delay, 0.0)

    def learn(self, request, response) -> None:
        """Read a route's own allowance off its answer."""
        headers = response.headers
        try:
            limit = int(headers.get("x-ratelimit-limit") or 0)
            remaining = headers.get("x-ratelimit-remaining")
            reset = float(headers.get("x-ratelimit-reset") or 0)
        except ValueError:
            return
        route = f"route:{route_key(request.url)}"
        slower = 0 < limit < 60.0 / self.interval
        exhausted = remaining is not None and remaining.strip() == "0" and reset > self.now()
        if not (slower or exhausted):
            return
        if not exhausted and self._read().get("route_interval", {}).get(route) == 60.0 / limit:
            return  # already known: no lock, no write, on the busiest routes



        def note(state: dict) -> None:
            if slower:
                state.setdefault("route_interval", {})[route] = 60.0 / limit
            if exhausted:
                nexts = state.setdefault("next", {})
                nexts[route] = max(nexts.get(route, 0.0), reset)

        try:
            self._update(note)
        except OSError:
            pass

    def hold(self, request, seconds: float) -> None:
        """Nothing more on this request's route for `seconds` (a 429's Retry-After)."""
        route = f"route:{route_key(request.url)}"
        until = self.now() + seconds

        def note(state: dict) -> None:
            nexts = state.setdefault("next", {})
            nexts[route] = max(nexts.get(route, 0.0), until)

        try:
            self._update(note)
        except OSError:
            self.sleep(seconds)


_SHARED: Pacer | None = None


def shared() -> Pacer:
    """The process's Pacer on the shared file. Built on first use, so a test that
    redirects QA_STATE_DIR before building a client gets its own file."""
    global _SHARED
    target = state_dir() / "pace.json"
    if _SHARED is None or _SHARED.path != target:
        _SHARED = Pacer(target)
    return _SHARED

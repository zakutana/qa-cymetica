"""One brake on how fast we ask their host, shared by every process.

Cymetica asked us, on 2026-09-20 (REPLY-0030), to leave load and volume testing
alone. From 2026-09-28 to 2026-10-06 we still sent 68,487 requests: a peak of
187 a minute from one test that read three URLs per app without a pause, and 256
answers of HTTP 429 on two routes allowed 30 a minute, which nothing read.
`RateLimitBudget` was per process, never slept, ignored 429 and Retry-After, and
threw away any limit under 100 -- the very headers those two routes send.

`qa.ratelimit.Pacer` reserves a slot per host (and per route that announced a
lower allowance) in one file under `state_dir()`, so the console's collectors,
the lab tick and a sweep running at once share the same minute. A 429 waits for
Retry-After and asks a READ once more; a write is never sent twice.

The clock and the sleep are injected: nothing here waits or touches the network.
"""

from __future__ import annotations

import httpx

from qa import ratelimit
from qa.marks import SafetyTier, qa
from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTransport


class Clock:
    def __init__(self):
        self.t = 1_000_000.0
        self.slept: list[float] = []

    def now(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.slept.append(round(seconds, 3))
        self.t += seconds


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_process_shares_one_spacing_and_a_slower_route_its_own(tmp_path):
    clock = Clock()
    state = tmp_path / "pace.json"
    # Two Pacers on one file are two processes: the console and a sweep.
    console = ratelimit.Pacer(state, now=clock.now, sleep=clock.sleep)
    sweep = ratelimit.Pacer(state, now=clock.now, sleep=clock.sleep)
    page = httpx.Request("GET", "https://cymetica.com/api/v1/gem-screener")

    for pacer in (console, sweep, console):
        pacer.wait(page)
    assert clock.slept == [1.0, 1.0], "60 a minute for the host, whichever process asks"

    # A route that says it allows 30 a minute is paced by that, not by the host.
    mcp = httpx.Request("POST", "https://cymetica.com/mcp/v1/")
    sweep.learn(mcp, httpx.Response(200, headers={"x-ratelimit-limit": "30"}, request=mcp))
    clock.slept.clear()
    console.wait(mcp)
    console.wait(mcp)
    assert clock.slept == [1.0, 2.0], clock.slept

    # Its allowance used up: nothing more on that route before their reset.
    sweep.learn(mcp, httpx.Response(200, request=mcp, headers={
        "x-ratelimit-limit": "30", "x-ratelimit-remaining": "0",
        "x-ratelimit-reset": str(int(clock.t + 40))}))
    # The host's other routes go on at their own pace...
    clock.slept.clear()
    console.wait(page)
    assert max(clock.slept, default=0.0) <= 1.0, clock.slept
    # ...and that route waits for its reset.
    clock.slept.clear()
    console.wait(mcp)
    assert clock.slept and clock.slept[0] >= 38.0, clock.slept


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_429_waits_for_retry_after_and_only_a_read_is_asked_again(tmp_path):
    clock = Clock()
    pacer = ratelimit.Pacer(tmp_path / "pace.json", now=clock.now, sleep=clock.sleep)
    calls: list[str] = []

    def handler(request):
        calls.append(request.method)
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "7"})
        return httpx.Response(200, json={"ok": True})

    transport = SafetyTransport(inner=httpx.MockTransport(handler),
                                registry=EndpointRegistry.load(), pacer=pacer)
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        response = transport.handle_request(
            httpx.Request("GET", "https://cymetica.com/api/v1/gem-screener"))
    finally:
        CURRENT_TIER.reset(token)

    assert response.status_code == 200 and calls == ["GET", "GET"], calls
    assert 7.0 in clock.slept, clock.slept

    # Their Retry-After is honoured up to a ceiling, and its absence is not zero.
    assert ratelimit.retry_after(httpx.Response(429, headers={"Retry-After": "9999"})) \
        == ratelimit.MAX_RETRY_AFTER_S
    assert ratelimit.retry_after(httpx.Response(429)) == ratelimit.DEFAULT_RETRY_AFTER_S
    # A write is never sent a second time: a POST that 429'd may still have landed.
    assert ratelimit.may_retry("GET") and not ratelimit.may_retry("POST")
    assert not ratelimit.may_retry("PATCH") and not ratelimit.may_retry("DELETE")

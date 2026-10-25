"""When the "prize log reaches every prize" check may call a window the whole log (C02, deep pass 2026-10-18).

It passed whenever the window was shorter than 200. A server that drops `limit` answers its default
newest 50, which is shorter than 200, so ids 1-196 out of reach read as "nothing lies behind it" -- the
same hole R05 found in scripts/league.py the same night. A window exactly as long as a window the server
stops at cannot tell "all of them" from "the newest N"; it goes on to the paging attempts.

A06, deep pass 2026-10-25 (3 of 3 readers): "shorter than every window the server stops at" was coded as
the windows seen so far (50, 200), so a silent new cap at 100 read as the whole log. No length can say a
window is the whole; its oldest id can. A window is the whole log only when it reaches the lowest id the
log is known to hold (1), and a short one that does not, with nothing older reachable, is Inconclusive --
a cap not seen before and records removed look the same -- while one as long as a known window fails.
"""

from qa.marks import SafetyTier, qa
from tests.rest.test_agent_league_prize_log import whole


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_window_cut_at_a_server_window_is_not_the_whole_log():
    assert whole(50, 197) is False, "the default fifty again: the 196 older ids are out of reach"
    assert whole(200, 47) is False, "the ceiling, as read 2026-10-17"
    assert whole(200, 1) is True and whole(50, 1) is True, "the oldest id is 1: nothing older to reach"
    assert whole(0, None) is True


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_window_is_whole_only_when_it_reaches_the_first_id():
    assert whole(100, 147) is False, "a cap at 100 nobody has seen before: ids 1-146 out of reach"
    assert whole(37, 210) is False, "shorter than every known window, and still 209 ids below it"
    assert whole(37, 1) is True, "short and reaching id 1: all there is"
    assert whole(3, None) is False, "rows whose ids cannot be read cannot say they are all"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_after_the_paging_attempts_only_a_known_window_fails():
    from tests.rest.test_agent_league_prize_log import verdict_after_paging

    assert verdict_after_paging(200, 47, {}) == "failed", "the ceiling, nothing older reachable"
    assert verdict_after_paging(50, 197, {}) == "failed", "the default fifty, nothing older reachable"
    assert verdict_after_paging(100, 147, {}) is None, (
        "a window no server cap is known at: a new cap or removed records, not told apart")
    assert verdict_after_paging(100, 147, {"offset": 3}) == "passed"
    assert verdict_after_paging(200, 47, {"before": 1}) == "passed"

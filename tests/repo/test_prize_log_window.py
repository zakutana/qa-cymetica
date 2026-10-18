"""When the "prize log reaches every prize" check may call a window the whole log (C02, deep pass 2026-10-18).

It passed whenever the window was shorter than 200. A server that drops `limit` answers its default
newest 50, which is shorter than 200, so ids 1-196 out of reach read as "nothing lies behind it" -- the
same hole R05 found in scripts/league.py the same night. A window exactly as long as a window the server
stops at cannot tell "all of them" from "the newest N"; it goes on to the paging attempts.
"""

from qa.marks import SafetyTier, qa
from tests.rest.test_agent_league_prize_log import whole


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_window_cut_at_a_server_window_is_not_the_whole_log():
    assert whole(50, 197) is False, "the default fifty again: the 196 older ids are out of reach"
    assert whole(200, 47) is False, "the ceiling, as read 2026-10-17"
    assert whole(37, 210) is True, "shorter than every window: all there is"
    assert whole(200, 1) is True and whole(50, 1) is True, "the oldest id is 1: nothing older to reach"
    assert whole(0, None) is True

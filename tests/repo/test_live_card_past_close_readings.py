"""The readings behind the "a card past its close is not live" check.

Written before the check (2026-10-26), from GET /api/v1/event-cards (all 647 live cards, read 13:30 UTC): six news cards whose
contract resolves at trading close ("resolution_basis": "trading_close") closed between 2026-08-15 and 2026-09-15 and still read
status "live", in the list /events deals its deck from. llms.txt: "A card is tradeable when status=live; trading_closes_at is
null on open-ended cards (they trade until they resolve)". Their tradeable_now is false, with the reason the US market's hours
or a price that has not refreshed -- never that trading closed. Cymetica the same day (REPLY-0222): "news cards leave the live
list after 72 hours".

Each reading below is a way the vendor could fix it (it must pass, whichever they pick), a way the same defect could be
rebuilt (it must still fail), or a shape the check cannot decide (inconclusive, never a pass).
"""

from datetime import datetime, timezone

from qa.marks import SafetyTier, qa
from tests.rest.test_a_card_past_its_close_is_not_live import judge

NOW = datetime(2026, 10, 26, 13, 30, tzinfo=timezone.utc)


def _card(cid, close, status="live", basis="trading_close", in_spec=True, title="news card"):
    return {"id": cid, "title": title, "status": status, "trading_closes_at": close,
            "contract_spec": {"resolution_basis": basis, "resolution_at_utc": close if in_spec else None},
            "tradeable_now": False, "trading_blocked_reason": "US equity markets are closed"}


# the six as served on 2026-10-26, beside an open-ended card and one that closes in the future
SIX = [_card("1a" * 18, "2026-09-15T01:51:09.076858+00:00", title="SpaceX CFO sets timeline for orbital data centers"),
       _card("2b" * 18, "2026-09-07T18:47:05.923879+00:00", title="Utilities are racing to link up with fusion startups"),
       _card("3c" * 18, "2026-09-02T00:05:02.062469+00:00", title="Chinese automakers are following Tesla's bet"),
       _card("4d" * 18, "2026-08-22T13:17:30.858185+00:00"),
       _card("5e" * 18, "2026-08-16T14:26:50.952706+00:00"),
       _card("6f" * 18, "2026-08-15T11:52:33.896942+00:00")]
OPEN = _card("7a" * 18, None, basis="perpetual", in_spec=False, title="ESTC — SAIB: CRM to acquire Braze ($5.7B)")
LATER = _card("8b" * 18, "2026-10-28T20:00:00+00:00")
LIVE = SIX + [OPEN, LATER]


def _verdict(cards, total=None):
    return judge(cards, len(cards) if total is None else total, NOW)[0]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_list_as_served_on_2026_10_26_fails():
    verdict, why, past = judge(LIVE, len(LIVE), NOW)
    assert verdict == "failed"
    assert len(past) == 6, "the open-ended card and the one closing on 28 October are not past their close"
    assert "6 " in why and "2026-08-15" in why


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_same_defect_rebuilt_in_other_shapes_still_fails():
    assert _verdict([_card("9c" * 18, "2026-10-25T07:00:00+00:00"), OPEN]) == "failed", "30 hours past, beyond the day's grace"
    only_spec = _card("9d" * 18, None)
    only_spec["contract_spec"]["resolution_at_utc"] = "2026-09-01T00:00:00+00:00"
    assert _verdict([only_spec]) == "failed", "the close written only as the contract's resolution time"
    assert _verdict([_card("9e" * 18, "2026-09-01T00:00:00Z")]) == "failed", "a Z suffix"
    assert _verdict([_card("9f" * 18, "2026-09-01T00:00:00")]) == "failed", "no zone: read as UTC"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_fix_the_vendor_might_choose_passes():
    assert _verdict([OPEN, LATER]) == "passed", "the six leave the live list"
    settled = [{**c, "status": "settled"} for c in SIX]
    assert _verdict(settled + [OPEN]) == "passed", "the six still listed but settled"
    closed = [{**c, "status": "closed"} for c in SIX]
    assert _verdict(closed + [OPEN]) == "passed", "or closed"
    assert _verdict([_card("aa" * 18, "2026-10-26T10:30:00+00:00"), OPEN]) == "passed", "three hours past: a settlement job's day"
    reopened = [_card(c["id"], None, basis="perpetual", in_spec=False) for c in SIX]
    assert _verdict(reopened) == "passed", "made open-ended, with no close at all"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_what_the_check_cannot_decide_is_inconclusive():
    assert _verdict(LIVE, total=647) is None, "the list read only in part: an unread page may hold one"
    assert _verdict([], total=0) is None, "no live card at all"
    garbled = _card("bb" * 18, "next Tuesday")
    assert _verdict([garbled, OPEN]) is None, "a close this check cannot read"
    assert _verdict([garbled] + SIX) == "failed", "an unreadable close does not hide the readable ones"

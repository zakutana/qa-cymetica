"""The readings of tests/rest/test_traffic_mine_tile_fits_its_days.py: the defect as read 2026-11-05, and the fix."""

from __future__ import annotations

from tests.rest.test_traffic_mine_tile_fits_its_days import tile_over_days

DAYS = {"2026-11-03": 131, "2026-11-04": 191, "2026-11-05": 18}


def test_a_tile_over_its_days_fails():
    assert tile_over_days({"totals": {"unique_visitors": 1311}, "unique_daily": DAYS})[0] == "failed"


def test_a_tile_within_its_days_passes():
    assert tile_over_days({"totals": {"unique_visitors": 300}, "unique_daily": DAYS})[0] == "passed"
    assert tile_over_days({"totals": {"unique_visitors": 342}, "unique_daily": DAYS})[0] == "passed"


def test_nothing_to_compare_is_no_verdict():
    assert tile_over_days({"unique_daily": DAYS})[0] is None
    assert tile_over_days({"totals": {"unique_visitors": 10}})[0] is None

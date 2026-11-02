"""The four readings of tests/rest/test_products_one_figure.py: the defect as read 2026-11-02, and each fix passing."""

from __future__ import annotations

from tests.rest.test_products_one_figure import anothers_people, row_over_tile, three_pages, uses_without_people

PROMISE = "The Products tab of /company and /traffic/mine show this same figure for a product (ET-33672)."
GEM_DAYS = [3, 5, 2, 7, 1, 4, 10, 5, 9, 0]


def _product(name, path, people, uses=1, daily=None):
    return {"name": name, "path": path, "unique_visitors": people, "uses": uses, "daily": daily or [1, 0, 0]}


def _app(path, people, uses=1, visits=500):
    return {"kind": "app", "path": path, "unique_visitors": people, "visits": visits,
            "app_beacon": {"visitors": people, "uses": uses}}


BAC = _product("Build a Company", "/company", 130, uses=52)
PAGE_ROW = {"kind": "feature_page", "path": "/company", "unique_visitors": 96, "visits": 467}


def test_a_shipped_page_row_with_another_figure_fails_and_either_fix_passes():
    assert three_pages([BAC], [PAGE_ROW], PROMISE)[0] == "failed"
    assert three_pages([BAC], [_app("/company", 130, uses=52)], PROMISE)[0] == "passed"
    assert three_pages([BAC], [PAGE_ROW], "Unique visitors: distinct people on this page.")[0] == "passed"


def test_the_right_figure_without_uses_still_fails():
    assert three_pages([BAC], [{**PAGE_ROW, "unique_visitors": 130}], PROMISE)[0] == "failed"


def test_a_feature_request_row_is_not_the_products_row():
    feature = {"kind": "feature", "path": "/company", "unique_visitors": 9}
    assert three_pages([BAC], [feature], PROMISE)[0] is None


def test_a_cache_gap_is_not_a_difference():
    assert three_pages([_product("X", "/x", 200)], [_app("/x", 205)], PROMISE)[0] == "passed"


def test_two_products_on_one_daily_list_fail_and_own_counts_pass():
    gem, supply = _product("Gem", "/gem", 195, daily=GEM_DAYS), _product("Supply", "/supply", 195, daily=GEM_DAYS)
    assert anothers_people([gem, supply], [], [])[0] == "failed"
    assert anothers_people([gem, {**supply, "unique_visitors": 40, "daily": [1, 2, 3, 4, 5, 0]}], [], [])[0] == "passed"


def test_a_groups_figure_under_a_products_name_fails_and_either_fix_passes():
    radar = _product("Team Dump Radar", "/team-dump-radar", 433)
    row = _app("/team-dump-radar", 433, visits=31)
    humans = [{"app": "Crypto Radars", "path": "/team-dump-radar", "users": 433}]
    assert anothers_people([radar], [row], humans)[0] == "failed"
    assert anothers_people([{**radar, "name": "Crypto Radars"}], [row], humans)[0] == "passed"
    assert anothers_people([{**radar, "unique_visitors": 25}], [row], humans)[0] == "passed"


def test_a_row_over_the_tile_fails_and_a_recount_passes():
    rows = [{"label": "Team Dump Radar", "unique_visitors": 338, "visits": 18}]
    assert row_over_tile({"totals": {"unique_visitors": 214}, "items": rows})[0] == "failed"
    assert row_over_tile({"totals": {"unique_visitors": 400}, "items": rows})[0] == "passed"
    assert row_over_tile({"items": rows})[0] is None


def test_uses_by_nobody_fail():
    assert uses_without_people([_product("Infiltrator", "/i", 0, uses=18)])[0] == "failed"
    assert uses_without_people([_product("Infiltrator", "/i", 3, uses=18)])[0] == "passed"
    assert uses_without_people([_product("Infiltrator", "/i", 0, uses=0)])[0] is None

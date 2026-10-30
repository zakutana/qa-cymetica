"""The readings under the two Quant Lab search checks (2026-10-30), on the search list as our company
14 was served it that day: searches #9, #7 and #5 failed before any job ran with the same database
error, the last one that completed is #3 (2026-10-27 14:01 UTC)."""

from datetime import datetime, timezone

from qa.marks import SafetyTier, qa
from tests.rest.test_quant_lab_daily_search_completes import stall
from tests.rest.test_quant_lab_search_error_names_no_internals import internals

ERROR = ("OperationalError: (psycopg2.OperationalError) server closed the connection unexpectedly\n"
         "\tThis probably means the server terminated abnormally\n\tbefore or while processing the request.\n\n"
         "[SQL: SELECT company_quant_combos.combo_key AS company_quant_combos_combo_key, "
         "company_quant_combos.data_fp AS company_quant_combos_data_fp \nFROM company_quant_combos \n"
         "WHERE company_quant_combos.company_id = %(compan")
NOW = datetime(2026, 10, 30, 13, 57, tzinfo=timezone.utc)


def _failed(sid, day, origin="daily"):
    return {"id": sid, "status": "failed", "origin": origin, "total_jobs": 0, "started_at": None,
            "requested_at": f"2026-10-{day}T10:09:52.235149Z", "finished_at": f"2026-10-{day}T10:10:36.472997Z",
            "error": ERROR}


DONE_3 = {"id": 3, "status": "done", "origin": "daily", "total_jobs": 1728,
          "requested_at": "2026-10-27T13:29:12.571645Z", "started_at": "2026-10-27T13:45:52.259399Z",
          "finished_at": "2026-10-27T14:01:08.817493Z", "error": None}
SEEN = [_failed(9, 30), _failed(7, 29), _failed(5, 28, "owner"), DONE_3]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_three_failed_days_after_the_last_completion_is_a_stall():
    out = stall(SEEN, None, NOW)
    assert out["verdict"] == "failed"
    assert [s["id"] for s in out["failed_in_a_row"]] == [9, 7, 5]
    assert out["last_completed"]["id"] == 3
    assert 71 < out["hours_since_completed"] < 72


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_list_order_is_not_trusted():
    """Newest is read off requested_at, not off the position the API happened to put it in."""
    assert stall(list(reversed(SEEN)), None, NOW)["verdict"] == "failed"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_their_fix_passes_with_the_old_failures_still_listed():
    """The next daily pass completes: the three failures stay in the history and the check is green."""
    done_31 = {**DONE_3, "id": 11, "requested_at": "2026-10-31T10:09:00Z", "finished_at": "2026-10-31T10:40:00Z"}
    assert stall([done_31] + SEEN, None, datetime(2026, 10, 31, 11, tzinfo=timezone.utc))["verdict"] == "passed"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_one_failure_the_next_pass_retries_is_inside_their_word():
    """Their page: "It tries again on the next pass." One failure 20 h after a completion is not a stall."""
    done = {**DONE_3, "requested_at": "2026-10-29T13:00:00Z", "finished_at": "2026-10-29T14:00:00Z"}
    assert stall([_failed(9, 30), done], None, NOW)["verdict"] == "passed"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_last_completion_may_come_from_last_finished_alone():
    """A completion older than the twelve listed searches is read from /search's `last_finished`."""
    recent = {**DONE_3, "requested_at": "2026-10-30T01:00:00Z", "finished_at": "2026-10-30T02:00:00Z"}
    assert stall([_failed(9, 30)], recent, NOW)["verdict"] == "passed"
    assert stall([_failed(9, 30)], DONE_3, NOW)["verdict"] == "failed"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_search_in_flight_or_none_at_all_is_not_judged():
    running = {**_failed(10, 30), "status": "running", "error": None}
    assert stall([running] + SEEN, None, NOW)["verdict"] is None
    assert stall([{**running, "status": "queued"}] + SEEN, None, NOW)["verdict"] is None
    assert stall([], None, NOW)["verdict"] is None


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_new_owner_whose_first_search_just_failed_is_not_a_stall():
    """No completion ever: the clock runs from the oldest listed search, not from the beginning of time."""
    assert stall([_failed(9, 30)], None, NOW)["verdict"] == "passed"
    old = _failed(1, 26)
    assert stall([_failed(9, 30), old], None, NOW)["verdict"] == "failed"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_error_they_serve_names_the_driver_the_class_and_the_sql():
    assert internals(ERROR) == ["SQL statement", "database driver", "exception class"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_plain_reason_names_nothing_internal():
    """However they word it: a sentence for the owner, a null, or the page's own fallback."""
    assert internals("The database connection dropped before the search started; it runs again tomorrow.") == []
    assert internals("Search failed: select a smaller set of markets from the list.") == []
    assert internals(None) == []
    assert internals("") == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_half_a_cleanup_still_counts():
    """The SQL cut off, the driver's exception left in front: still internals."""
    assert internals("OperationalError: server closed the connection unexpectedly") == ["exception class"]
    assert internals("(psycopg2.OperationalError) server closed the connection") == ["database driver"]
    assert internals("Traceback (most recent call last):\n  File \"x.py\"") == ["Python traceback"]

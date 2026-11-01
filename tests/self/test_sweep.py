"""The sweep: what it decides to tell them, and when it stays quiet."""

from __future__ import annotations

import json

import httpx
import pytest

from qa.client import build_mock_client
from qa.paths import load_filed, read_events, save_filed
from qa.safety import EndpointRegistry


def _row(key="CYM-a", report=7, status="fixed", nodeids=("tests/rest/test_a.py::test_a",), **extra):
    return {"key": key, "nodeids": list(nodeids), "report_ids": [report], "title": f"title of {key}",
            "filed_at": "2026-10-01T00:00:00+00:00", "verdicts_sent": [], "their_status": {str(report): status},
            "withdrawn": False, **extra}


def _reading(result, reason="read 5, expected 0"):
    return {"result": result, "reason": reason, "left": 5, "right": 0}


class Vendor:
    """Their API as far as the sweep can tell. Records every POST."""

    def __init__(self, reports=(), verifications=None, tracker_status=200, read_status=200, post_status=200):
        self.reports, self.verifications = list(reports), verifications or {}
        self.tracker_status, self.read_status, self.post_status = tracker_status, read_status, post_status
        self.posts = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path.endswith("/verification"):
            self.posts.append((path, json.loads(request.content)))
            return httpx.Response(self.post_status, json={"success": True, "verification": {"id": 99}})
        if path.endswith("/verifications"):
            if self.read_status != 200:
                return httpx.Response(self.read_status, json={"detail": "no"})
            rid = int(path.split("/")[-2])
            return httpx.Response(200, json={"verifications": self.verifications.get(rid, [])})
        if path.endswith("/my-reports"):
            if self.tracker_status != 200:
                return httpx.Response(self.tracker_status, json={"detail": "no"})
            return httpx.Response(200, json={"reports": self.reports, "total": len(self.reports)})
        if "/a2a/inbox/" in path:
            return httpx.Response(200, json={"messages": []})
        return httpx.Response(404, json={"detail": path})


def _client(vendor):
    registry = EndpointRegistry.load()
    registry.mutate_enabled = True
    registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    return build_mock_client(vendor, registry=registry)


@pytest.fixture
def sweep(script, monkeypatch):
    module = script("sweep")
    monkeypatch.setenv("QA_WALLET_ADDRESS", "0xabc")
    monkeypatch.setattr(module, "PAUSE_SECONDS", 0)
    return module


# -- which rows it looks at ----------------------------------------------------------------------
def test_open_rows_leave_out_withdrawn_rejected_and_already_passed(sweep):
    rows = [_row("a", 1), _row("b", 2, withdrawn=True), _row("c", 3, status="invalid"),
            _row("d", 4, verdicts_sent=[{"report_id": 4, "verdict": "pass", "at": "2026-10-02"}]),
            _row("e", 5, verdicts_sent=[{"report_id": 5, "verdict": "pass", "at": "2026-10-02"},
                                        {"report_id": 5, "verdict": "fail", "at": "2026-10-03"}])]
    assert [r["key"] for r in sweep.open_rows(rows)] == ["a", "e"]
    assert [r["key"] for r in sweep.open_rows(rows, everything=True)] == ["a", "c", "d", "e"]


def test_a_row_we_passed_that_failed_since_stays_open(sweep):
    row = _row("d", 4, verdicts_sent=[{"report_id": 4, "verdict": "pass", "at": "2026-10-02"}], last_check="fail")
    assert sweep.open_rows([row]) == [row]


# -- what it would tell them ---------------------------------------------------------------------
@pytest.mark.parametrize("result,status,newest,fixed_at,expected", [
    ("inconclusive", "fixed", None, None, None),           # rule 10: never a verdict from an inconclusive
    ("pass", "pending", None, None, "pass"),               # it passes, nobody has said so
    ("pass", "paid", {"verdict": "fail", "at": "2026-10-02"}, None, "pass"),
    ("pass", "paid", {"verdict": "pass", "at": "2026-10-02"}, None, None),   # already told
    ("fail", "pending", None, None, None),                 # we said that when we filed it
    ("fail", "fixed", None, None, "fail"),                 # they claim it, it fails
    ("fail", "paid", None, None, "fail"),
    ("fail", "pending", {"verdict": "pass", "at": "2026-10-02"}, None, "fail"),  # our own pass stopped being true
    ("fail", "fixed", {"verdict": "fail", "at": "2026-10-02"}, "2026-10-01", None),  # already told, nothing new
    ("fail", "fixed", {"verdict": "fail", "at": "2026-10-02"}, "2026-10-05", "fail"),  # they claimed again since
    ("fail", "invalid", None, None, None),                 # they rejected it: not a verdict's business
    ("pass", "wontfix", None, None, None),
])
def test_decide(sweep, result, status, newest, fixed_at, expected):
    assert sweep.decide(result, status, newest, fixed_at) == expected


def test_a_report_on_two_rows_passes_only_when_both_do(sweep):
    rows = [_row("a", 7, nodeids=("x",)), _row("b", 7, nodeids=("y",)), _row("c", 8, nodeids=("z",))]
    readings = {"x": _reading("pass"), "y": _reading("fail"), "z": _reading("pass")}
    grouped = sweep.by_report(rows, readings)
    assert grouped[7]["result"] == "fail"
    assert grouped[8]["result"] == "pass"
    assert grouped[7]["nodeids"] == ["x", "y"]


def test_a_row_without_a_check_is_not_a_pass(sweep):
    grouped = sweep.by_report([_row("a", 7, nodeids=())], {})
    assert grouped[7]["result"] == "inconclusive"
    assert grouped[7]["by_hand"] is True


# -- what it sends --------------------------------------------------------------------------------
def test_the_newest_verification_is_their_last_word(sweep):
    rows = [{"verdict": "pass", "created_at": "2026-10-01T00:00:00", "id": 1},
            {"verdict": "fail", "created_at": "2026-10-03T00:00:00", "id": 2}]
    vendor = Vendor(verifications={7: rows})
    client = _client(vendor)
    assert sweep.their_last_word(client, 7)["verdict"] == "fail"
    assert sweep.their_last_word(client, 8) is None


def test_a_read_that_failed_is_not_an_empty_read(sweep):
    client = _client(Vendor(read_status=500))
    with pytest.raises(sweep.Unread):
        sweep.their_last_word(client, 7)


def test_the_payload_carries_the_six_fields_and_no_promise_we_stopped_keeping(sweep):
    payload = sweep.payload("fail", 7, ["tests/self/test_sweep.py::test_decide"],
                            {"tests/self/test_sweep.py::test_decide": _reading("fail")}, "run-1.json")
    assert set(payload) == {"verdict", "test_run_id", "fingerprint", "tree_sha", "checked_at", "evidence"}
    assert payload["verdict"] == "fail" and payload["test_run_id"] == "run-1.json"
    assert len(payload["fingerprint"]) == 64
    assert "read 5, expected 0" in payload["evidence"]
    text = payload["evidence"].lower()
    assert "retained" not in text and "preregist" not in text and "on request" not in text


def test_the_evidence_fits_their_field(sweep):
    huge = {"x": {"result": "fail", "reason": "z" * 20000, "left": "a" * 9000, "right": "b" * 9000}}
    assert len(sweep.payload("fail", 7, ["x"], huge, "run")["evidence"]) <= sweep.EVIDENCE_LIMIT


def test_sending_records_it_only_when_their_server_gave_an_id(sweep):
    rows = [_row()]
    save_filed({"rows": rows})
    client = _client(Vendor())
    outcome = sweep.send_verdict(client, 7, "fail", ["tests/rest/test_a.py::test_a"],
                                 {"tests/rest/test_a.py::test_a": _reading("fail")}, "run-1.json")
    assert outcome == "accepted"
    assert load_filed()["rows"][0]["verdicts_sent"][-1]["verdict"] == "fail"
    assert [e["type"] for e in read_events()] == ["verification_intent", "verification_outcome"]


def test_a_two_hundred_without_an_id_is_not_a_verification(sweep):
    save_filed({"rows": [_row()]})

    def no_id(request):
        return httpx.Response(200, json={"success": True})

    outcome = sweep.send_verdict(_client(no_id), 7, "pass", ["x"], {"x": _reading("pass")}, "run")
    assert outcome == "unknown"
    assert load_filed()["rows"][0]["verdicts_sent"] == []


# -- the whole pass, with the checks faked ----------------------------------------------------------
def _sweep_run(sweep, vendor, rows, first, again=None, send=True):
    save_filed({"rows": rows})
    calls = []

    def fake(nodeids):
        calls.append(list(nodeids))
        table = first if len(calls) == 1 else (again if again is not None else first)
        return {n: table[n] for n in nodeids}, f"run-{len(calls)}.json"

    report = sweep.run_sweep(_client(vendor), run_checks=fake, send=send)
    return report, calls


def test_without_send_nothing_leaves(sweep):
    vendor = Vendor(reports=[{"id": 7, "status": "fixed", "title": "t"}])
    report, _ = _sweep_run(sweep, vendor, [_row()], {"tests/rest/test_a.py::test_a": _reading("pass")}, send=False)
    assert vendor.posts == []
    assert report["table"][0]["would_send"] == "pass"


def test_pass_goes_out_when_the_check_passes(sweep):
    vendor = Vendor(reports=[{"id": 7, "status": "fixed", "title": "t"}])
    _, calls = _sweep_run(sweep, vendor, [_row()], {"tests/rest/test_a.py::test_a": _reading("pass")})
    assert [p[1]["verdict"] for p in vendor.posts] == ["pass"]
    assert len(calls) == 2, "the check is run again right before anything is sent"


def test_inconclusive_sends_nothing(sweep):
    vendor = Vendor(reports=[{"id": 7, "status": "fixed", "title": "t"}])
    _sweep_run(sweep, vendor, [_row()], {"tests/rest/test_a.py::test_a": _reading("inconclusive")})
    assert vendor.posts == []


def test_a_failed_tracker_read_sends_nothing(sweep):
    vendor = Vendor(tracker_status=500)
    report, _ = _sweep_run(sweep, vendor, [_row()], {"tests/rest/test_a.py::test_a": _reading("pass")})
    assert vendor.posts == []
    assert report["tracker"] != "ok"


def test_a_failed_read_of_what_they_hold_sends_nothing(sweep):
    vendor = Vendor(reports=[{"id": 7, "status": "fixed", "title": "t"}], read_status=503)
    _sweep_run(sweep, vendor, [_row()], {"tests/rest/test_a.py::test_a": _reading("pass")})
    assert vendor.posts == []


def test_a_result_that_changes_on_the_recheck_sends_nothing(sweep):
    vendor = Vendor(reports=[{"id": 7, "status": "fixed", "title": "t"}])
    node = "tests/rest/test_a.py::test_a"
    _sweep_run(sweep, vendor, [_row()], {node: _reading("pass")}, again={node: _reading("fail")})
    assert vendor.posts == []


def test_a_row_without_a_check_is_listed_for_a_look_by_hand(sweep):
    vendor = Vendor(reports=[{"id": 7, "status": "fixed", "title": "t"}])
    report, _ = _sweep_run(sweep, vendor, [_row(nodeids=())], {})
    assert vendor.posts == []
    assert report["by_hand"] == [7]


def test_the_tracker_status_is_written_back_to_filed(sweep):
    vendor = Vendor(reports=[{"id": 7, "status": "paid", "title": "t"}])
    _sweep_run(sweep, vendor, [_row(status="pending")], {"tests/rest/test_a.py::test_a": _reading("inconclusive")})
    assert load_filed()["rows"][0]["their_status"] == {"7": "paid"}
    assert load_filed()["rows"][0]["last_check"] == "inconclusive"

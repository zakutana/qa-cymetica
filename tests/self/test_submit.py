"""Filing one bug with one command, and the three things that stop it."""

from __future__ import annotations

import json

import httpx
import pytest

from qa.client import build_mock_client
from qa.paths import load_filed, read_events, save_filed
from qa.safety import EndpointRegistry

FOOTER = "Reported by an independent QA agent."


def _report(key="a-defect", **extra):
    return {"key": key, "title": "A defect with a long enough title", "severity": "low", "category": "logic",
            "body": "It says one thing.\n\nIt does another.", "steps": ["GET /x"], "expected": "This.",
            "actual": "That.", "url": "https://cymetica.com/x", **extra}


class Vendor:
    def __init__(self, titles=(), tracker_status=200, post=None):
        self.titles, self.tracker_status = list(titles), tracker_status
        self.post = post or (lambda request: httpx.Response(200, json={"success": True, "report_id": 250}))
        self.posts = []

    def __call__(self, request):
        path = request.url.path
        if request.method == "POST":
            self.posts.append(json.loads(request.content))
            return self.post(request)
        if self.tracker_status != 200:
            return httpx.Response(self.tracker_status, json={"detail": "no"})
        rows = [{"id": 40 + i, "title": t} for i, t in enumerate(self.titles)]
        return httpx.Response(200, json={"reports": rows})


def _client(vendor):
    registry = EndpointRegistry.load()
    registry.mutate_enabled = True
    registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    return build_mock_client(vendor, registry=registry)


@pytest.fixture
def submit(script, monkeypatch):
    monkeypatch.setenv("QA_WALLET_ADDRESS", "0xabc")
    monkeypatch.setenv("QA_HUNTER_NAME", "expire76")
    return script("submit")


def _reading(result="fail"):
    return {"result": result, "reason": "read 5, expected 0", "left": 5, "right": 0}


def test_compose_carries_what_was_written_and_what_was_read(submit):
    payload = submit.compose(_report(), FOOTER, {"tests/rest/test_a.py::test_a": _reading()})
    text = payload["description"]
    assert "It says one thing." in text and "GET /x" in text and FOOTER in text
    assert "read 5, expected 0" in text and "tests/rest/test_a.py::test_a" in text
    assert "retained" not in text.lower() and "on request" not in text.lower()
    assert payload["wallet_address"] == "0xabc" and payload["title"] == "A defect with a long enough title"


def test_compose_works_for_a_bug_with_no_check(submit):
    assert "It does another." in submit.compose(_report(), FOOTER, {})["description"]


@pytest.mark.parametrize("change", [{"title": "short"}, {"severity": "huge"}, {"category": "vibes"}])
def test_validate_refuses_what_their_form_would(submit, change):
    payload = {**submit.compose(_report(), FOOTER, {}), **{{"severity": "severity_reported"}.get(k, k): v
                                                           for k, v in change.items()}}
    with pytest.raises(SystemExit):
        submit.validate(payload, "a-defect")


def test_a_title_already_on_their_tracker_is_not_filed_again(submit):
    vendor = Vendor(titles=["A defect with a long enough title"])
    result = submit.file_report(_client(vendor), _report(), FOOTER, [], {})
    assert vendor.posts == []
    assert result["outcome"] == "already filed"
    assert load_filed()["rows"][0]["report_ids"] == [40], "a lost answer is settled from their tracker"


def test_an_unreadable_tracker_is_not_an_empty_one(submit):
    vendor = Vendor(tracker_status=401)
    with pytest.raises(SystemExit):
        submit.file_report(_client(vendor), _report(), FOOTER, [], {})
    assert vendor.posts == []


def test_an_accepted_report_lands_in_filed_and_the_journal(submit):
    vendor = Vendor()
    node = "tests/rest/test_a.py::test_a"
    result = submit.file_report(_client(vendor), _report(check=node), FOOTER, [node], {node: _reading()})
    assert result == {"key": "a-defect", "outcome": "accepted", "report_id": 250}
    row = load_filed()["rows"][0]
    assert (row["key"], row["report_ids"], row["nodeids"]) == ("a-defect", [250], [node])
    assert row["their_status"] == {"250": "pending"} and row["verdicts_sent"] == []
    assert [e["type"] for e in read_events()] == ["filing_intent", "filing_outcome"]


def test_their_refusal_files_nothing(submit):
    vendor = Vendor(post=lambda request: httpx.Response(409, json={"detail": "duplicate"}))
    result = submit.file_report(_client(vendor), _report(), FOOTER, [], {})
    assert result["outcome"] == "rejected"
    assert load_filed()["rows"] == []


def test_a_timeout_is_unknown_and_files_nothing_we_could_cite(submit):
    def boom(request):
        raise httpx.ReadTimeout("slow", request=request)

    result = submit.file_report(_client(Vendor(post=boom)), _report(), FOOTER, [], {})
    assert result["outcome"] == "unknown"
    assert load_filed()["rows"] == []
    assert read_events()[-1]["outcome"] == "unknown"


def test_a_two_hundred_without_an_id_is_not_a_filing(submit):
    vendor = Vendor(post=lambda request: httpx.Response(200, json={"success": True}))
    assert submit.file_report(_client(vendor), _report(), FOOTER, [], {})["outcome"] == "unknown"


# -- the check before the filing --------------------------------------------------------------------
@pytest.mark.parametrize("result,force,stops", [
    ("pass", False, True), ("inconclusive", False, True), ("fail", False, False),
    ("pass", True, False), ("inconclusive", True, False),
])
def test_the_check_decides_whether_it_goes(submit, result, force, stops):
    assert bool(submit.refusal({"x": _reading(result)}, force)) is stops


def test_a_bug_with_no_check_may_go(submit):
    assert submit.refusal({}, False) is None


def test_the_check_comes_from_the_report_or_from_filed(submit):
    assert submit.nodeids_of(_report(check="a::b"), []) == ["a::b"]
    assert submit.nodeids_of(_report(check=["a::b", "c::d"]), []) == ["a::b", "c::d"]
    rows = [{"key": "CYM-x", "nodeids": ["e::f"]}]
    assert submit.nodeids_of(_report(findings=["CYM-x"]), rows) == ["e::f"]
    assert submit.nodeids_of(_report(), rows) == []


def test_a_finding_that_holds_a_report_is_refused(submit):
    rows = [{"key": "CYM-x", "report_ids": [12]}]
    assert submit.already_filed(_report(findings=["CYM-x"]), rows) == [12]
    assert submit.already_filed(_report(key="CYM-x"), rows) == [12]
    assert submit.already_filed(_report(key="new"), rows) == []


def test_main_files_only_the_key_it_was_given_and_a_bad_neighbour_does_not_stop_it(submit, monkeypatch, tmp_path):
    spec = tmp_path / "reports.yaml"
    spec.write_text(json.dumps({"footer": FOOTER, "reports": [
        {"key": "broken", "title": "x"}, _report()]}), encoding="utf-8")
    monkeypatch.setattr(submit, "SPEC", spec)
    vendor = Vendor()
    monkeypatch.setattr(submit, "_clients", lambda: (_client(vendor), _client(vendor)))
    save_filed({"rows": []})
    assert submit.main(["a-defect"]) == 0
    assert len(vendor.posts) == 1


def test_dry_run_sends_nothing(submit, monkeypatch, tmp_path, capsys):
    spec = tmp_path / "reports.yaml"
    spec.write_text(json.dumps({"footer": FOOTER, "reports": [_report()]}), encoding="utf-8")
    monkeypatch.setattr(submit, "SPEC", spec)
    save_filed({"rows": [{"key": "a-defect", "report_ids": [12], "nodeids": []}]})
    assert submit.main(["a-defect", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "already filed" in out and "It says one thing." in out


# -- not filed twice --------------------------------------------------------------------------------
def test_a_new_key_on_a_check_already_filed_is_refused(submit):
    rows = [{"key": "CYM-x", "report_ids": [77], "nodeids": ["a::b"]}]
    assert submit.already_filed(_report(key="fresh-wording", check="a::b"), rows) == [77]
    assert submit.already_filed(_report(key="fresh-wording", check=["c::d", "a::b"]), rows) == [77]
    assert submit.already_filed(_report(key="fresh-wording", check="c::d"), rows) == []


def test_a_check_on_a_withdrawn_row_may_be_filed_again(submit):
    rows = [{"key": "CYM-x", "report_ids": [77], "nodeids": ["a::b"], "withdrawn": True}]
    assert submit.already_filed(_report(key="fresh-wording", check="a::b"), rows) == []


def _main(submit, monkeypatch, tmp_path, report, *argv):
    spec = tmp_path / "reports.yaml"
    spec.write_text(json.dumps({"footer": FOOTER, "reports": [report]}), encoding="utf-8")
    monkeypatch.setattr(submit, "SPEC", spec)
    vendor = Vendor()
    monkeypatch.setattr(submit, "_clients", lambda: (_client(vendor), _client(vendor)))
    return submit.main([report["key"], *argv]), vendor


def test_force_files_over_an_earlier_report(submit, monkeypatch, tmp_path):
    save_filed({"rows": [{"key": "CYM-x", "report_ids": [77], "nodeids": []}]})
    code, vendor = _main(submit, monkeypatch, tmp_path, _report(findings=["CYM-x"]))
    assert code == 0 and vendor.posts == []
    code, vendor = _main(submit, monkeypatch, tmp_path, _report(findings=["CYM-x"]), "--force")
    assert code == 0 and len(vendor.posts) == 1


def test_a_report_we_withdrew_is_not_filed_again(submit, monkeypatch, tmp_path, capsys):
    save_filed({"rows": []})
    code, vendor = _main(submit, monkeypatch, tmp_path, _report(withdrawn="2026-09-05: our check was wrong"))
    assert vendor.posts == [] and load_filed()["rows"] == []
    assert "withdrawn" in capsys.readouterr().out


def test_an_earlier_filing_under_another_title_is_found_and_settled(submit):
    from qa.paths import append_event

    append_event({"type": "filing_intent", "at": "t", "key": "a-defect", "title": "The old title of it",
                  "nodeids": []})
    append_event({"type": "filing_outcome", "at": "t", "key": "a-defect", "outcome": "unknown", "http_status": 500})
    vendor = Vendor(titles=["The old title of it"])
    result = submit.file_report(_client(vendor), _report(), FOOTER, [], {})
    assert vendor.posts == [] and result["outcome"] == "already filed" and result["report_id"] == 40
    last = read_events()[-1]
    assert (last["outcome"], last["report_id"], last["reconciled_from"]) == ("accepted", 40, "my-reports")


# -- what goes to them ------------------------------------------------------------------------------
def test_only_a_failing_reading_is_called_measured(submit):
    readings = {"a::fails": _reading("fail"),
                "b::crashed": {"result": "inconclusive", "reason": "KeyError: 'rows'", "left": None, "right": None},
                "c::passes": {"result": "pass", "reason": "fine", "left": None, "right": None}}
    text = submit.compose(_report(), FOOTER, readings)["description"]
    assert "a::fails" in text and "read 5, expected 0" in text
    assert "KeyError" not in text and "b::crashed" not in text and "c::passes" not in text


def test_no_failing_reading_leaves_no_measured_block(submit):
    readings = {"b::gone": {"result": "inconclusive", "reason": "this check no longer exists", "left": None, "right": None}}
    text = submit.compose(_report(), FOOTER, readings)["description"]
    assert "MEASURED" not in text and "no longer exists" not in text


def test_a_url_is_not_broken_across_lines(submit):
    url = "https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals-very-long-path"
    assert url in submit.wrap(f"See {url} for it.")


def test_the_real_footer_promises_nothing_we_do_not_keep():
    import yaml

    from qa.paths import REPO_ROOT

    footer = yaml.safe_load((REPO_ROOT / "outbox" / "reports.yaml").read_text(encoding="utf-8"))["footer"]
    assert "at the time stated" not in footer


# -- a tracker that did not answer as a tracker -------------------------------------------------------
@pytest.mark.parametrize("answer", [
    lambda: httpx.Response(200, text="<html>maintenance</html>"),
    lambda: httpx.Response(200, json=["a list"]),
    lambda: httpx.Response(200, json={"detail": "try later"}),
])
def test_an_odd_answer_from_the_tracker_refuses_to_file_blind(submit, answer):
    posts = []

    def handler(request):
        if request.method == "POST":
            posts.append(request)
            return httpx.Response(200, json={"report_id": 1})
        return answer()

    with pytest.raises(SystemExit, match="blind"):
        submit.file_report(_client(handler), _report(), FOOTER, [], {})
    assert posts == []


def test_an_unknown_outcome_says_what_to_do(submit, monkeypatch, tmp_path, capsys):
    def boom(request):
        raise httpx.ReadTimeout("slow", request=request)

    spec = tmp_path / "reports.yaml"
    spec.write_text(json.dumps({"footer": FOOTER, "reports": [_report()]}), encoding="utf-8")
    monkeypatch.setattr(submit, "SPEC", spec)
    vendor = Vendor(post=boom)
    monkeypatch.setattr(submit, "_clients", lambda: (_client(vendor), _client(vendor)))
    save_filed({"rows": []})
    assert submit.main(["a-defect"]) == 1
    assert "sweep" in capsys.readouterr().out

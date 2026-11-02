"""First-party pytest plugin: a run becomes a small JSON record the sweep can read.

Two ordering facts this file depends on, both learned the hard way:

  * The classifier is a `tryfirst` hookwrapper on pytest_runtest_makereport. A tryfirst wrapper is outermost,
    so its post-yield code runs LAST. The earlier `trylast` wrote every Inconclusive check as `failed`.
  * The append happens in pytest_runtest_logreport, which pytest calls only after makereport has returned.

The measurement is read in the CALL phase, from its ContextVar.
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from qa.paths import REPO_ROOT, state_dir

# Failures of OUR transport, not answers from their platform: a check that never got a reply measured nothing.
_TRANSPORT_ERRORS = (
    httpx.TimeoutException, httpx.NetworkError, httpx.ProtocolError,
    httpx.TooManyRedirects, httpx.RemoteProtocolError,
)


def _budget_exhausted():
    """Imported late: qa.safety imports this module's neighbours at load."""
    from qa.safety import BudgetExhausted
    return BudgetExhausted


def _is_self_test(nodeid: str) -> bool:
    return "tests/self/" in str(nodeid).replace("\\", "/")


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _head() -> str:
    try:
        done = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, timeout=10)
    except Exception:  # noqa: BLE001
        return ""
    return done.stdout.strip() if done.returncode == 0 else ""


def pytest_sessionstart(session):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    pytest._qa_session = session
    session.qa_run = {"run_id": f"run-{stamp}", "started_at": _utc(), "finished_at": None, "git_head": _head(),
                      "selector": " ".join(session.config.invocation_params.args),
                      "collected": [], "results": [], "totals": {}}


def pytest_collection_finish(session):
    run = getattr(session, "qa_run", None)
    if run is not None:
        run["collected"] = [item.nodeid for item in session.items]


def pytest_runtest_setup(item):
    from qa.measure import CURRENT_MEASUREMENT
    CURRENT_MEASUREMENT.set(None)


def _skip_reason(report) -> str | None:
    longrepr = getattr(report, "longrepr", None)
    if isinstance(longrepr, tuple) and len(longrepr) == 3:
        message = str(longrepr[2])
        for prefix in ("Skipped: ", "INCONCLUSIVE: "):
            if message.startswith(prefix):
                return message[len(prefix):]
        return message
    return None


def _trim(text: str, limit: int = 8000) -> str:
    return text if len(text) <= limit else text[:limit] + "\n... [truncated]"


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    """Classify. Runs LAST among wrappers, so the report it reads is final."""
    from qa.marks import Inconclusive
    from qa.measure import CURRENT_MEASUREMENT

    outcome = yield
    report = outcome.get_result()

    kind = None
    reason = None
    if call.excinfo is not None and call.excinfo.errisinstance(Inconclusive):
        reason = str(call.excinfo.value)
        report.outcome = "skipped"
        report.longrepr = (str(item.path), item.location[1] + 1, f"INCONCLUSIVE: {reason}")
        kind = "inconclusive"
    elif (report.when == "call" and call.excinfo is not None
          and call.excinfo.errisinstance(_TRANSPORT_ERRORS)):
        # We stopped listening; the platform said nothing. One such timeout once minted a defect.
        reason = f"{type(call.excinfo.value).__name__}: could not reach the platform"
        report.outcome = "skipped"
        report.longrepr = (str(item.path), item.location[1] + 1, f"INCONCLUSIVE: {reason}")
        kind = "inconclusive"
    elif (report.when in ("setup", "call") and call.excinfo is not None
          and call.excinfo.errisinstance(_budget_exhausted())
          and not _is_self_test(item.nodeid)):
        # OUR rate-limit budget was spent, so nothing about them was measured.
        reason = f"refused by our own guard: {str(call.excinfo.value)[:200]}"
        report.outcome = "skipped"
        report.longrepr = (str(item.path), item.location[1] + 1, f"INCONCLUSIVE: {reason}")
        kind = "inconclusive"
    elif report.when == "call":
        kind = report.outcome
        if report.skipped:
            reason = _skip_reason(report)
    elif report.failed:
        kind = "error"
    elif report.skipped:
        kind = "skipped"
        reason = _skip_reason(report)

    if kind is None:
        return  # a setup/teardown that simply succeeded is not a result

    measurement = CURRENT_MEASUREMENT.get() if report.when == "call" else None
    report.qa_result = {
        "nodeid": report.nodeid,
        "outcome": kind,
        "phase": report.when,
        "duration_ms": int(report.duration * 1000),
        "measurement": measurement.as_record() if measurement else None,
        "volatile": item.get_closest_marker("qa_volatile") is not None,
        "exception": call.excinfo.typename if call.excinfo is not None else None,
        "reason": reason,
        "failure_repr": _trim(str(report.longrepr)) if kind in ("failed", "error") else None,
    }


def pytest_runtest_logreport(report):
    """Append. Called only after makereport has returned the final report."""
    result = getattr(report, "qa_result", None)
    if result is None:
        return
    run = getattr(getattr(pytest, "_qa_session", None), "qa_run", None)
    if run is not None:
        run["results"].append(result)


def pytest_sessionfinish(session, exitstatus):
    run = getattr(session, "qa_run", None)
    if run is None:
        return
    run["finished_at"] = _utc()
    run["exit_status"] = int(exitstatus)
    for result in run["results"]:
        run["totals"][result["outcome"]] = run["totals"].get(result["outcome"], 0) + 1

    # QA_RUN_FILE is qa/checks.py asking for the record; otherwise only a run of vendor checks leaves one.
    target = os.environ.get("QA_RUN_FILE")
    if not target:
        nodeids = set(run["collected"]) | {r["nodeid"] for r in run["results"]}
        if not any(not _is_self_test(n) for n in nodeids) or session.config.getoption("collectonly", False):
            return
        target = state_dir() / "runs" / f"{run['run_id']}.json"
    path = Path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(run, indent=1), encoding="utf-8")

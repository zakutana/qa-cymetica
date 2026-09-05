"""First-party pytest plugin: a run becomes a machine-readable record.

Deliberately not pytest-json-report. This sits on the load-bearing path of a
system whose entire value is auditability, it needs marker payloads and
evidence ids that the third-party schema does not carry, and it is 150 lines.
A dependency here would buy nothing and cost the ability to explain the output.

The fingerprint is computed at session start AND session finish. If they
differ, the platform changed mid-run and the run is flagged: no ticket may be
verified from it.
"""

from __future__ import annotations

import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = REPO_ROOT / "state" / "runs"


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _git(*args: str) -> str:
    try:
        return subprocess.run(
            ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, timeout=10
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def _marker_arg(item, name, default=None):
    marker = item.get_closest_marker(name)
    return marker.args[0] if marker and marker.args else default


def pytest_sessionstart(session):
    from qa.fingerprint import compute

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    head = _git("rev-parse", "--short", "HEAD") or "nogit"
    dirty = bool(_git("status", "--porcelain"))

    fingerprint = compute()

    session.qa_run_id = f"run-{stamp}-{head}"
    session.qa_run = {
        "run_id": session.qa_run_id,
        "started_at": _utc(),
        "finished_at": None,
        "git_head": _git("rev-parse", "HEAD"),
        "git_short": head,
        "git_dirty": dirty,
        "prereg_id": session.config.getoption("--prereg"),
        "prereg_tag_sha": None,
        "platform_fingerprint": fingerprint.get("fingerprint"),
        "fingerprint_parts": fingerprint.get("parts", {}),
        "fingerprint_errors": fingerprint.get("errors", {}),
        "fingerprint_drifted": False,
        "fingerprint_changed_parts": [],
        "python_version": platform.python_version(),
        "pytest_version": pytest.__version__,
        "classifier_version": _classifier_version(),
        "selector": " ".join(session.config.invocation_params.args),
        "allow_mutate": bool(session.config.getoption("--allow-mutate")),
        "results": [],
        "totals": {},
        "ratelimit": {},
    }
    session.qa_fingerprint_start = fingerprint

    prereg = session.config.getoption("--prereg")
    if prereg:
        sha = _git("rev-parse", f"prereg/{prereg}")
        session.qa_run["prereg_tag_sha"] = sha or None
        if not sha:
            raise pytest.UsageError(
                f"--prereg {prereg} given but no annotated tag 'prereg/{prereg}' "
                f"exists. Freeze and tag the preregistration before the first "
                f"data point, or the run cannot settle its claims."
            )


def _classifier_version() -> str:
    try:
        from qa.errors import ErrorClassifier
        return ErrorClassifier.VERSION
    except Exception:  # noqa: BLE001
        return "unavailable"


@pytest.hookimpl(hookwrapper=True, trylast=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    if report.when != "call":
        if not (report.when == "setup" and report.outcome in ("failed", "skipped")):
            return

    run = getattr(item.session, "qa_run", None)
    if run is None:
        return

    qa_outcome = getattr(report, "qa_outcome", None) or report.outcome
    evidence_ids = list(getattr(item, "stash_evidence", []) or [])

    run["results"].append({
        "nodeid": report.nodeid,
        "component": _marker_arg(item, "qa_component", "unknown"),
        "tier": _marker_arg(item, "qa_tier", "SAFE"),
        "surface": _marker_arg(item, "qa_surface", "rest"),
        "claim_id": _marker_arg(item, "qa_claim"),
        "ticket_id": _marker_arg(item, "qa_ticket"),
        "volatile": item.get_closest_marker("qa_volatile") is not None,
        "outcome": qa_outcome,
        "phase": report.when,
        "duration_ms": int(report.duration * 1000),
        "evidence_ids": evidence_ids,
        "reason": getattr(report, "qa_reason", None),
        "failure_repr": _trim(str(report.longrepr)) if report.failed else None,
    })


def _trim(text: str, limit: int = 8000) -> str:
    return text if len(text) <= limit else text[:limit] + "\n... [truncated]"


def pytest_sessionfinish(session, exitstatus):
    run = getattr(session, "qa_run", None)
    if run is None:
        return

    from qa.fingerprint import compute, diff

    after = compute()
    before = getattr(session, "qa_fingerprint_start", {"parts": {}})
    changed = diff(before, after)

    run["finished_at"] = _utc()
    run["fingerprint_after"] = after.get("fingerprint")
    run["fingerprint_drifted"] = bool(changed)
    run["fingerprint_changed_parts"] = changed
    run["exit_status"] = int(exitstatus)

    totals: dict[str, int] = {}
    for result in run["results"]:
        totals[result["outcome"]] = totals.get(result["outcome"], 0) + 1
    run["totals"] = totals

    try:
        budget = session.config._qa_budget  # set by the budget fixture if used
        run["ratelimit"] = budget.snapshot()
    except AttributeError:
        pass

    # Resolved at write time, not import time, so QA_STATE_DIR can redirect an
    # inner test session away from the committed state/runs/.
    from qa.state import state_dir
    runs_dir = state_dir() / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    path = runs_dir / f"{run['run_id']}.json"
    path.write_text(
        json.dumps(run, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Display only. The record may live outside the repo (QA_STATE_DIR), and a
    # cosmetic path helper must never be able to crash sessionfinish.
    try:
        shown = path.relative_to(REPO_ROOT)
    except ValueError:
        shown = path
    print(f"\n[qa] run record -> {shown}")
    if changed:
        print(f"[qa] FINGERPRINT DRIFTED during this run: {changed}")
        print("[qa] The platform changed mid-run. No fix may be verified from it.")

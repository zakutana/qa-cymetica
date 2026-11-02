"""Run checks in their own pytest and read the record into one word per check: pass, fail, inconclusive.

Rule 10 lives here: a check that could not measure (Inconclusive, a skip, a broken fixture, a crash, a timeout,
a volatile value, a check that is gone) is never a defect and never a fix. Only the call phase of a verdict-role
check counts. A pytest that could not run at all raises CannotRun: that is not an inconclusive check.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from qa.paths import REPO_ROOT, state_dir

_WORDS = {"passed": "pass", "failed": "fail"}
RUNS_KEPT = 30
VENDOR_DIRS = ["tests/rest", "tests/mcp", "tests/discovery", "tests/pinned", "tests/reconciliation"]


class CannotRun(RuntimeError):
    """pytest did not get to the checks: the guard refused, a conftest broke, a check has no tag."""


def load_record(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _asserted(result: dict) -> bool:
    """A failure the check itself reached. A KeyError or an AttributeError is our check crashing."""
    return result.get("exception") in (None, "AssertionError", "Failed")


def _said(failure_repr: str) -> str:
    """The failure's own first line, never the traceback: this text reaches the vendor, and our paths and source
    are not a reading."""
    lines = [line[1:].strip() for line in failure_repr.splitlines() if line.startswith("E ")]
    if lines:
        return lines[0]
    rest = failure_repr.strip().splitlines()
    return rest[-1] if rest else ""


def classify(record: dict, nodeids: list[str]) -> dict[str, dict]:
    """{nodeid: {result, reason, left, right}} for the checks asked about."""
    by_node: dict[str, list[dict]] = {}
    for result in record.get("results") or []:
        by_node.setdefault(result.get("nodeid"), []).append(result)

    out = {}
    for nodeid in nodeids:
        rows = by_node.get(nodeid) or []
        call = next((r for r in rows if r.get("phase") == "call"), None)
        row = call or (rows[0] if rows else None)
        measured = (row or {}).get("measurement") or {}
        word = _WORDS.get((row or {}).get("outcome"), "inconclusive") if call else "inconclusive"
        if measured.get("role") == "evidence" or (word == "fail" and (call.get("volatile") or not _asserted(call))):
            word = "inconclusive"
        reason = (measured.get("reason") or (row or {}).get("reason") or _said((row or {}).get("failure_repr") or "")
                  or ("the check did not run" if row is None else ""))
        out[nodeid] = {"result": word, "reason": str(reason), "left": measured.get("left"),
                       "right": measured.get("right")}
    return out


def overall(readings: list[dict]) -> str:
    """One word for several checks: any fail is a fail, a pass needs every one of them."""
    words = [r.get("result") for r in readings]
    if "fail" in words:
        return "fail"
    if words and all(w == "pass" for w in words):
        return "pass"
    return "inconclusive"


def _prune(folder: Path) -> None:
    runs = sorted(folder.glob("run-*.json"), key=lambda p: p.name)
    for old in runs[:-RUNS_KEPT]:
        old.unlink(missing_ok=True)


def _pytest(selector: list[str], *flags: str, keep: bool = True) -> dict:
    folder = state_dir() / "runs"
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = folder / f"{'run' if keep else 'collect'}-{stamp}.json"
    env = {**os.environ, "QA_RUN_FILE": str(out)}
    argsfile = folder / f"args-{stamp}.txt"
    argsfile.write_text("\n".join(selector), encoding="utf-8")   # the Windows command line is finite
    try:
        done = subprocess.run([sys.executable, "-m", "pytest", f"@{argsfile}", "--tb=short", "-q", *flags],
                              cwd=REPO_ROOT, env=env, capture_output=True, text=True, encoding="utf-8",
                              errors="replace")
    finally:
        argsfile.unlink(missing_ok=True)
    # 3 is an internal error or the guard's self-check, 4 a usage error such as a check with no tag. Exit 2 is a
    # collection error, which costs only that module's checks, and they read inconclusive.
    if done.returncode in (3, 4) or not out.exists():
        out.unlink(missing_ok=True)
        said = ((done.stdout or "") + (done.stderr or "")).strip()
        raise CannotRun(f"pytest exited {done.returncode} and ran nothing:\n{said[-800:]}")
    record = load_record(out)
    if keep:
        record["_file"] = out.name
        _prune(folder)
    else:
        out.unlink(missing_ok=True)
    return record


def collected(nodeids: list[str]) -> set[str]:
    """Which of these checks exist today: pytest stops the whole run on a nodeid it cannot find."""
    files = sorted({n.split("::")[0] for n in nodeids if (REPO_ROOT / n.split("::")[0]).exists()})
    if not files:
        return set()
    record = _pytest(files, "--collect-only", keep=False)
    return set(record.get("collected") or []) & set(nodeids)


def vendor_checks() -> list[str]:
    """Every check on their platform, whether or not a filed bug names it."""
    return list(_pytest(VENDOR_DIRS, "--collect-only", keep=False).get("collected") or [])


def run(nodeids: list[str]) -> tuple[dict[str, dict], str]:
    """Run these checks now. ({nodeid: reading}, the run's filename)."""
    exists = collected(nodeids)
    record = _pytest(sorted(exists)) if exists else {"_file": ""}
    readings = classify(record, nodeids)
    for nodeid in nodeids:
        if nodeid not in exists:
            readings[nodeid] = {"result": "inconclusive", "reason": "this check is gone or its file does not collect",
                                "left": None, "right": None}
    return readings, record.get("_file") or ""

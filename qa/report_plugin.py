"""First-party pytest plugin: a run becomes a machine-readable record (schema 2).

Deliberately not pytest-json-report. This sits on the load-bearing path of a
system whose entire value is auditability; it needs marker payloads, evidence
ids and measurements the third-party schema does not carry.

Two ordering facts this file depends on, both learned the hard way:

  * The classifier is a `tryfirst` hookwrapper on pytest_runtest_makereport.
    A tryfirst wrapper is outermost, so its post-yield code runs LAST -- after
    every other wrapper has finished with the report. The previous version was
    `trylast`, resumed first, and wrote every Inconclusive check as `failed`.
  * The append to the run record happens in pytest_runtest_logreport, which
    pytest calls only after makereport has fully returned. Nothing can mutate
    the classification between the two.

Evidence ids and the measurement are read in the CALL phase, from their
ContextVars, before the autouse fixture's finalizer resets them at teardown.

The fingerprint is computed at session start AND session finish. If they
differ, the platform changed mid-run and the run is flagged.
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
import platform
import re
import subprocess
import textwrap
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

# Failures of OUR transport, not answers from their platform. A check that
# never got a reply has measured nothing, and recording that as a failure
# reports our network as their defect.
_TRANSPORT_ERRORS = (
    httpx.TimeoutException, httpx.NetworkError, httpx.ProtocolError,
    httpx.TooManyRedirects, httpx.RemoteProtocolError,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA = 2

# What a run MEASURES. Sampled again at the end so a tree that was clean only
# at the starting pistol cannot pass for a verification; `state/`, `dashboard/`
# and `audits/` are left out because a run writes those under itself on purpose.
CODE_PATHS = ("qa", "scripts", "tests", "components.yaml", ".claude")


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def code_moved_since(head_before: str | None) -> bool:
    """Whether the code under CODE_PATHS moved between the run's start and now.

    Two ways, and until V16 (deep pass of 2026-09-19, 3/3) only the first was
    read: an edit still uncommitted at the end (`git status`), and an edit
    COMMITTED mid-run -- which leaves the tree clean and HEAD somewhere else,
    and kept the run at level V over code that changed under it. A commit of
    tracked state only (a console poll during the run) is not the code moving.
    """
    if _git("status", "--porcelain", "--", *CODE_PATHS):
        return True
    head_after = _git("rev-parse", "HEAD")
    if not head_before or not head_after or head_after == head_before:
        return False
    return bool(_git("diff", "--name-only", head_before, head_after,
                     "--", *CODE_PATHS))


def _git(*args: str) -> str:
    """git stdout, or "" if the command failed.

    The returncode check is load-bearing: `git rev-parse` echoes its own
    argument to stdout when a ref does not resolve, so ignoring the exit code
    stored the string "prereg/PRE-0016^{commit}" in the run record as though
    it were a commit sha. The record then contradicted the tag, and
    run_integrity refused it -- correctly, and for a reason that pointed at
    the wrong thing.
    """
    try:
        result = subprocess.run(
            ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10
        )
    except Exception:  # noqa: BLE001
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def _marker_arg(item, name, default=None):
    marker = item.get_closest_marker(name)
    return marker.args[0] if marker and marker.args else default


def _opt(config, name, default=None):
    try:
        return config.getoption(name)
    except (ValueError, AttributeError):
        return default


# ---------------------------------------------------------------------------
# Session start: identity of the run
# ---------------------------------------------------------------------------
def pytest_sessionstart(session):
    from qa.fingerprint import compute

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    head = _git("rev-parse", "--short", "HEAD") or "nogit"
    dirty = bool(_git("status", "--porcelain"))
    fingerprint = compute()

    session.qa_run_id = f"run-{stamp}-{head}"
    session.qa_run = {
        "schema": SCHEMA,
        "run_id": session.qa_run_id,
        "started_at": _utc(),
        "finished_at": None,
        "git_head": _git("rev-parse", "HEAD"),
        "git_short": head,
        "git_dirty": dirty,
        "prereg_id": _opt(session.config, "--prereg"),
        "prereg_tag_sha": None,
        "prereg_commit": None,
        "platform_fingerprint": fingerprint.get("fingerprint"),
        "fingerprint_parts": fingerprint.get("parts", {}),
        "fingerprint_errors": fingerprint.get("errors", {}),
        "fingerprint_drifted": False,
        "fingerprint_changed_parts": [],
        "identities_present": _identities_present(),
        "python_version": platform.python_version(),
        "pytest_version": pytest.__version__,
        "selector": " ".join(session.config.invocation_params.args),
        # Did this run offer the WHOLE suite? Recorded at the source, where it
        # is known, rather than guessed later from the selector string. It is
        # what separates "that check was not selected" from "that check does
        # not exist" -- and only a full run can say the second.
        "selector_full": _selector_is_full(session.config),
        # What narrowed it, as pytest parsed it -- what a preregistration's
        # promise is held to (S02, deep pass of 2026-09-24).
        "narrowing": _narrowing(session.config),
        # And the paths it was pointed at, as pytest resolved them (Q01).
        "paths": _paths(session.config),
        "allow_mutate": bool(_opt(session.config, "--allow-mutate", False)),
        "collected": [],
        "results": [],
        "totals": {},
        "ratelimit": {},
        "record_integrity": {},
    }
    session.qa_fingerprint_start = fingerprint

    prereg = session.qa_run["prereg_id"]
    if prereg:
        sha = _git("rev-parse", f"prereg/{prereg}")
        session.qa_run["prereg_tag_sha"] = sha or None
        session.qa_run["prereg_commit"] = _git("rev-parse", f"prereg/{prereg}^{{commit}}") or None
        if not sha:
            raise pytest.UsageError(
                f"--prereg {prereg} given but no annotated tag 'prereg/{prereg}' "
                f"exists. Freeze and tag the preregistration before the first "
                f"data point, or the run cannot settle its claims."
            )


def _identities_present() -> dict[str, bool]:
    try:
        from qa.config import identities
        return {name: bool(ident.present) for name, ident in identities().items()}
    except Exception:  # noqa: BLE001
        return {}


def pytest_collection_finish(session):
    """Everything the selector chose, before anything ran.

    A finding whose check is not in this list was not looked at by this run,
    and the fold must never treat that absence as a verdict.
    """
    run = getattr(session, "qa_run", None)
    if run is not None:
        run["collected"] = [item.nodeid for item in session.items]


# ---------------------------------------------------------------------------
# Per-test: reset, classify, append
# ---------------------------------------------------------------------------
def pytest_runtest_setup(item):
    from qa.measure import CURRENT_MEASUREMENT
    CURRENT_MEASUREMENT.set(None)


@pytest.hookimpl(hookwrapper=True)
def pytest_fixture_setup(fixturedef, request):
    """Capture the session budget so a rate-limit-truncated run is visible.

    The `budget` fixture lives in the pinned part of conftest.py and cannot be
    edited to publish itself; this hook sees it the moment it is created.
    """
    outcome = yield
    if fixturedef.argname == "budget":
        try:
            request.session.qa_budget = outcome.get_result()
        except Exception:  # noqa: BLE001
            pass


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


def _strip_docstrings(tree: ast.AST) -> ast.AST:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            body = getattr(node, "body", None)
            if body and isinstance(body[0], ast.Expr) and isinstance(
                getattr(body[0], "value", None), ast.Constant
            ) and isinstance(body[0].value.value, str):
                node.body = body[1:] or [ast.Pass()]
    return tree


def _selector_is_full(config) -> bool:
    """True when nothing narrowed what pytest was asked to collect.

    Only positional paths and -k / -m narrow the suite; -q, --tb and the rest
    do not. A run that offered everything and did not collect a nodeid has
    established that the nodeid is gone -- which no partial run can.

    Read off config.args, which is what pytest resolved the positional
    arguments to, and not off the raw command line. Filtering the raw args on
    "does not start with a dash" counted OPTION VALUES as paths: every
    admissible run carries `--prereg PRE-NNNN`, so `positional` came out as
    ["tests", "PRE-0045"] and this returned False. Level V requires a
    preregistration, so selector_full was false on every run that could ever
    have used it -- 0 of 39 run records have it set -- and the fold's
    check_missing branch, the only thing that can say a check is GONE rather
    than merely untested, has never once been able to fire.
    """
    # -k and -m, and (A4 of the review of 2026-09-23, 3/3) the options that
    # deselect or skip what was collected: counted as full, they let a
    # partial run declare a check GONE. One table with the preregistration's
    # own check (RC01).
    if _narrowing(config):
        return False
    # config.args falls back to the testpaths ini value when nothing
    # positional was given, which is the same thing: the whole suite.
    positional = [str(a) for a in (getattr(config, "args", None) or [])]
    return not positional or positional == ["tests"]


def _paths(config) -> list[str]:
    """The paths this session was pointed at, as pytest resolved them:
    config.args, which never holds an option's value and falls back to the
    testpaths ini value when nothing positional was given (Q01, deep pass of
    2026-09-24) -- what a preregistration's promised paths are held to."""
    return [str(a) for a in (getattr(config, "args", None) or [])]


def _narrowing(config) -> list[list[str]]:
    """The options this session narrowed what it collected with, each with
    its value: what pytest PARSED, and what the command line says.

    S02 (deep pass of 2026-09-24, 3/3): a prefix match over the raw arguments
    never read `-qk x` as a -k, and PYTEST_ADDOPTS never reaches them at all
    -- a run of 1 of 128 checks recorded itself full. config.option holds
    both. The command line is read too, so a plugin that is not loaded
    (`-p no:cacheprovider` takes --lf with it) hides nothing either.
    """
    from qa.state import NARROWING_DESTS, split_selector

    pairs: set[tuple[str, str]] = set()
    option = getattr(config, "option", None)
    for dest, name in NARROWING_DESTS:
        value = getattr(option, dest, None)
        if not value:
            continue
        if value is True:
            pairs.add((name, ""))
        elif isinstance(value, (list, tuple)):
            pairs.update((name, str(v)) for v in value)
        else:
            pairs.add((name, str(value)))
    try:
        pairs |= split_selector(list(config.invocation_params.args))[1]
    except ValueError:
        pass
    return [list(p) for p in sorted(pairs)]


def check_fingerprint(item) -> str:
    """Hash of the check's DEFINITION, not its name.

    The test function's AST with docstrings stripped, combined with the
    `fingerprint` attribute of any parametrize object that offers one. A
    rename keeps the hash; a change to what the check asserts changes it.
    Never raises: a check we cannot read hashes its nodeid, and says so.
    """
    parts: list[str] = []
    try:
        source = textwrap.dedent(inspect.getsource(item.obj))
        tree = _strip_docstrings(ast.parse(source))
        # The NAME is not part of the definition: a rename must keep the hash.
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                node.name = "_"
        parts.append(ast.dump(tree, include_attributes=False))
    except Exception:  # noqa: BLE001
        parts.append(f"nodeid:{item.nodeid}")

    callspec = getattr(item, "callspec", None)
    if callspec is not None:
        for name, value in sorted(callspec.params.items()):
            fp = getattr(value, "fingerprint", None)
            if isinstance(fp, str):
                parts.append(f"{name}={fp}")
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


HELPERS_FORMULA = 2
_CONSTANT_TYPES = (bool, int, float, str, bytes, tuple, list, frozenset, set, dict,
                   re.Pattern, type(None))


def _is_constant(value) -> bool:
    return isinstance(value, _CONSTANT_TYPES)


def _constant_repr(value) -> str:
    """A stable text for a constant: a pattern by its source and flags, a set
    in sorted order, everything else by repr."""
    if isinstance(value, re.Pattern):
        return f"re({value.pattern!r},{value.flags})"
    if isinstance(value, (set, frozenset)):
        return f"{type(value).__name__}({sorted(map(repr, value))})"
    return repr(value)


def helpers_fingerprint(item) -> str:
    """Hash of the functions the check calls from its OWN module, followed
    transitively -- the half of its definition `check_fingerprint` never saw.

    A8 of the review of 2026-09-23 (3/3): a helper rewritten after a failure
    left `check_fingerprint` unchanged, and verify.py told the vendor "the
    same test, not a rewritten one". Kept apart from `check_fingerprint`
    rather than folded into it: a new formula there would move every row in
    the ledger to CHECK_CHANGED at once. Never raises; a check whose module
    cannot be read hashes to the empty set and says nothing more.
    """
    dumps: dict[str, str] = {}
    try:
        module = inspect.getmodule(item.obj)
        todo = [item.obj]
        seen: set[int] = set()
        while todo:
            fn = todo.pop()
            if id(fn) in seen:
                continue
            seen.add(id(fn))
            tree = _strip_docstrings(ast.parse(textwrap.dedent(inspect.getsource(fn))))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Name):
                    continue
                helper = getattr(module, node.id, None)
                if (inspect.isfunction(helper)
                        and getattr(helper, "__module__", None) == module.__name__
                        and helper is not item.obj and node.id not in dumps):
                    dumps[node.id] = ast.dump(_strip_docstrings(ast.parse(
                        textwrap.dedent(inspect.getsource(helper)))),
                        include_attributes=False)
                    todo.append(helper)
                elif (f"const:{node.id}" not in dumps and hasattr(module, node.id)
                      and _is_constant(helper)):
                    # A module constant it reads -- a window, a threshold, a
                    # regex -- is as much what it asserts (deep pass
                    # 2026-09-25, B02: MAX_STEP 0.40 -> 0.95 kept both hashes).
                    dumps[f"const:{node.id}"] = _constant_repr(helper)
    except Exception:  # noqa: BLE001
        pass
    joined = "\n".join(f"{name}={dump}" for name, dump in sorted(dumps.items()))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    """Classify. Runs LAST among wrappers, so the report it reads is final."""
    from qa.evidence import CURRENT_EVIDENCE
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
        # We stopped listening; the platform said nothing. A read timeout is
        # the definition of "could not measure", and calling it a failure
        # files a finding about their platform on the strength of our network.
        # One did: a ReadTimeout on /api/v1/vaix/prices minted a defect.
        reason = f"{type(call.excinfo.value).__name__}: could not reach the platform"
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
    evidence_ids = list(CURRENT_EVIDENCE.get() or []) if report.when == "call" else []
    fingerprint = (
        measurement.fingerprint if measurement and measurement.fingerprint
        else check_fingerprint(item)
    )

    report.qa_result = {
        "nodeid": report.nodeid,
        "component": _marker_arg(item, "qa_component", "unknown"),
        "tier": _marker_arg(item, "qa_tier", "SAFE"),
        "surface": _marker_arg(item, "qa_surface", "rest"),
        "claim_id": _marker_arg(item, "qa_claim") or (measurement.claim_id if measurement else None),
        "ticket_id": _marker_arg(item, "qa_ticket"),
        "volatile": item.get_closest_marker("qa_volatile") is not None,
        "outcome": kind,
        "phase": report.when,
        "role": measurement.role if measurement else "verdict",
        "duration_ms": int(report.duration * 1000),
        "evidence_ids": evidence_ids,
        "measurement": measurement.as_record() if measurement else None,
        "check_fingerprint": fingerprint,
        "helpers_fingerprint": helpers_fingerprint(item),
        # Which formula: 2 reads module constants too (2026-09-25, B02). Two
        # hashes of different formulas are not a comparison (verify.py).
        "helpers_formula": HELPERS_FORMULA,
        "reason": reason,
        "failure_repr": _trim(str(report.longrepr)) if kind in ("failed", "error") else None,
    }


def pytest_runtest_logreport(report):
    """Append. Called only after makereport has returned the final report."""
    result = getattr(report, "qa_result", None)
    if result is None:
        return
    session = getattr(pytest, "_qa_session", None)
    run = getattr(session, "qa_run", None) if session is not None else None
    if run is not None:
        run["results"].append(result)


# ---------------------------------------------------------------------------
# Session finish: integrity, totals, write
# ---------------------------------------------------------------------------
# The two directories whose checks measure US. CLAUDE.md names them: tests/meta
# aborts the session on failure, tests/repo is repository consistency. Nothing
# in either says anything about Cymetica.
SELF_TEST_DIRS = ("tests/meta/", "tests/repo/")


def should_record(nodeids, prereg_id) -> bool:
    """Whether this session produced a record worth keeping.

    779 records on disk, 542 of them from sessions that adjudicated nothing
    about the platform: every `pytest tests/meta -q` while working, every
    single-file run with --tb=line. They cost 74 MB, they push a real record
    out of the newest-first scan that step 2 of the deep pass uses, and the
    operator asked not to have to think about any of it.

    A preregistered session always writes, whatever it ran: that is the record
    a verification stands on, and the decision about what it covers was made
    before it started.
    """
    if prereg_id:
        return True
    return any(not str(nodeid).replace("\\", "/").startswith(SELF_TEST_DIRS)
               for nodeid in nodeids)


def pytest_sessionfinish(session, exitstatus):
    run = getattr(session, "qa_run", None)
    if run is None:
        return

    from qa.fingerprint import compute, diff

    after = compute()
    before = getattr(session, "qa_fingerprint_start", {"parts": {}})
    changed = diff(before, after)

    run["finished_at"] = _utc()
    # The tree, sampled a SECOND time. `git_dirty` above is taken at
    # sessionstart, so without this a run records a clean tree and can still
    # have had the code edited under it for the next seven minutes -- which is
    # exactly what happened on 2026-09-12. Scoped to the code, because a run
    # legitimately writes tracked state under itself and a repo-wide sample
    # here would refuse every verification we make.
    run["code_dirty_after"] = code_moved_since(run.get("git_head"))
    run["fingerprint_after"] = after.get("fingerprint")
    run["fingerprint_drifted"] = bool(changed)
    run["fingerprint_changed_parts"] = changed
    run["exit_status"] = int(exitstatus)

    totals: dict[str, int] = {}
    for result in run["results"]:
        totals[result["outcome"]] = totals.get(result["outcome"], 0) + 1
    run["totals"] = totals

    # The session attribute was never set by anything, which is why every
    # committed run record carries an empty `ratelimit` -- and why a run cut
    # short by an exhausted quota looked complete. The budget registers itself
    # on construction now, so the recorder can find it either way.
    from qa.safety import active_budget
    budget = getattr(session, "qa_budget", None) or active_budget()
    if budget is not None:
        try:
            run["ratelimit"] = budget.snapshot()
        except Exception:  # noqa: BLE001
            run["ratelimit"] = {}

    collected = set(run.get("collected") or [])
    seen = {r["nodeid"] for r in run["results"]}
    any_red = any(r["outcome"] in ("failed", "error") for r in run["results"])
    run["record_integrity"] = {
        "consistent": (int(exitstatus) in (0, 1))
        and ((int(exitstatus) == 1) == any_red)
        and seen <= collected,
        "results_not_in_collected": sorted(seen - collected),
        "collected_not_run": sorted(collected - seen),
        "budget_truncated": bool(budget is not None and getattr(budget, "exhausted", False)),
    }

    # Resolved at write time, not import time, so QA_STATE_DIR can redirect an
    # inner test session away from the committed state/runs/.
    from qa.state import state_dir

    if not should_record(
            set(run.get("collected") or []) | {r["nodeid"] for r in run["results"]},
            run.get("prereg_id")):
        print("\n[qa] only self-tests ran; no run record written")
        return

    runs_dir = state_dir() / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    path = runs_dir / f"{run['run_id']}.json"
    path.write_text(json.dumps(run, indent=2, ensure_ascii=False), encoding="utf-8")

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

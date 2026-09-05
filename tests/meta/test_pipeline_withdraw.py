"""WD: withdrawal is an event with a reason and a debt, not a dict in the code.

Four findings were retracted by adding their ids to a literal dict at
scripts/ledger.py:36-55. That dict is the reason a withdrawal could not be
dated, could not name who decided it, and -- because two of the four had
already been filed with the vendor -- left no record that we owed anyone a
correction. `if False and method:` at findings.py:239 is the same defect in the
other direction: a finding switched off by editing the generator.

The rule: a human changes state only by appending an event, and every such
event carries a reason. The literal is gone and cannot come back without
failing this file.

Fails at 11e43ea: there is no scripts/withdraw.py.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


def _module(relpath: str):
    """Import a scripts/ module by path -- scripts/ is not a package."""
    path = REPO / relpath
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_withdrawal_is_an_event_with_obligations(tmp_path, monkeypatch):
    """Withdrawing a filed finding writes one operator event and leaves a debt
    on every report it was filed under, until a retraction is sent."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    from qa.fold import fold
    from qa.state import read_events

    withdraw = _module("scripts/withdraw.py")
    journal = tmp_path / "journal" / "events.jsonl"

    withdraw.main(["withdraw", "CYM-mcp_tool_count",
                   "--reason", "Our check asserted the anonymous tool count "
                               "equals the manifest total; that held only while "
                               "tier gating was broken."])

    events = read_events(path=journal)
    assert len(events) == 1
    e = events[0]
    assert e["type"] == "withdraw" and e["by"] == "operator"
    assert e["finding_id"] == "CYM-mcp_tool_count"
    assert "tier gating" in e["reason"]

    from tests.meta.test_pipeline_fold import _filed, ledger, row
    state = ledger(row("CYM-mcp_tool_count", check_state="REPRODUCING", checks=["tests/a.py::t"]))
    after = fold(state, events=_filed("CYM-mcp_tool_count", 46, "pending") + events)

    r = after["findings"]["CYM-mcp_tool_count"]
    assert r["filing"]["state"] == "WITHDRAWN"
    assert r["obligations"]["retractions"] == [46], \
        "withdrawing a filed finding must leave a correction owed on its report"

    sent = events + [{"type": "retraction_sent", "at": "2026-09-05T13:00:00+00:00",
                      "by": "operator", "source": "scripts/withdraw.py",
                      "finding_id": "CYM-mcp_tool_count", "report_id": 46,
                      "reason": "CORRECTIONS paragraph in #54"}]
    cleared = fold(state, events=_filed("CYM-mcp_tool_count", 46, "pending") + sent)
    assert cleared["findings"]["CYM-mcp_tool_count"]["obligations"]["retractions"] == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_withdraw_refuses_an_empty_reason(tmp_path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    withdraw = _module("scripts/withdraw.py")

    with pytest.raises(SystemExit):
        withdraw.main(["withdraw", "CYM-a", "--reason", "   "])
    assert not (tmp_path / "journal" / "events.jsonl").exists()


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_hardcoded_withdrawal_dict_is_gone():
    """The literal and its two accomplices. Each one is a place where state
    was assigned by editing code rather than by recording an event."""
    ledger_mod = _module("scripts/ledger.py")
    assert not hasattr(ledger_mod, "WITHDRAWN"), \
        "the hardcoded withdrawal dict is back at scripts/ledger.py"
    for gone in ("latest_run_id", "executed_nodeids", "merge"):
        assert not hasattr(ledger_mod, gone), f"scripts/ledger.py still defines {gone}()"

    # Parsed, not grepped: the module's docstring names both defects precisely
    # because it records why they were removed.
    import ast

    tree = ast.parse((REPO / "scripts" / "findings.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test = node.test
            const = test if isinstance(test, ast.Constant) else (
                test.values[0] if isinstance(test, ast.BoolOp) and
                isinstance(test.values[0], ast.Constant) else None)
            assert not (const is not None and not const.value), (
                f"findings.py:{node.lineno} switches a finding off with an "
                f"unreachable branch"
            )
        if isinstance(node, ast.FunctionDef):
            assert node.name != "_parse_failure", \
                "findings still scrape their detail out of a traceback"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_only_state_module_writes_state_files():
    """Critique gap 10. Without this, the whole class returns with the next
    script that finds it convenient to write the ledger itself."""
    import ast

    offenders = []
    for path in sorted(REPO.glob("[qs]*/**/*.py")):
        rel = path.relative_to(REPO).as_posix()
        if rel in ("qa/state.py", "scripts/migrate_ledger.py"):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "attr", None)
            if name not in ("write_text", "open", "replace"):
                continue
            src = ast.unparse(node)
            if "ledger" in src.lower() or "events" in src.lower() or "journal" in src.lower():
                offenders.append(f"{rel}:{node.lineno}: {src[:80]}")
    assert not offenders, (
        "only qa/state.py may write state/ledger.json and the journal:\n  "
        + "\n  ".join(offenders)
    )

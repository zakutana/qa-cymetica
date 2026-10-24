"""No worker of the company writes a Python file at the root or any conftest.py (NEXT.md 2026-10-18).

The week's review of 2026-10-18: a department's worker (`claude -p`, qa/crew.py::argv) was denied
scripts/**, qa/**, tests/meta/** and tests/conftest.py, but not a new `conftest.py` anywhere else, nor
a `*.py` at the repository root. pytest imports every conftest.py on its way to a test, and a root
module is importable from every session started here, so either runs inside the operator's own test
sessions and the deep pass's -- the one place a worker's code must never reach. pytest's own config
files beside pyproject.toml (already protected) outrank it, so they are the same door.

Held on `denied(dept)`, the deny list every worker is started with. The rules use Claude Code's
gitignore patterns (code.claude.com/docs/en/permissions, "How path patterns match"): a CLI rule's
leading `/` anchors at the worker's primary working directory -- the repository root, where
scripts/crew.py::run_process starts it -- and `*` stays inside one path segment, so `/*.py` is the
root's own files and nothing under tests/; `**/conftest.py` is a conftest at any depth.
"""

from __future__ import annotations

from qa import crew
from qa.marks import SafetyTier, qa

ROOT_FILES = ("/*.py", "**/conftest.py", "/pytest.ini", "/tox.ini", "/setup.cfg")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_no_worker_may_write_a_root_module_or_any_conftest():
    for dept, spec in crew.DEPARTMENTS.items():
        if spec.model is None:
            continue                      # a code department starts no model to deny
        denied = crew.denied(dept)
        missing = [f"{tool}({path})" for path in ROOT_FILES for tool in ("Edit", "Write")
                   if f"{tool}({path})" not in denied]
        assert not missing, (dept, missing)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_root_rule_is_anchored_so_bugs_still_writes_its_checks():
    """Bugs writes checks under tests/ (its department's work). A bare `*.py` has no slash, so by
    gitignore it matches at ANY depth and would deny every check Bugs writes; the anchored form is
    the one that names the root alone."""
    denied = crew.denied("bugs")
    assert "Edit(*.py)" not in denied and "Write(*.py)" not in denied, denied
    assert "Edit(tests/**)" not in denied, "Bugs lost its own tests"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_worker_starts_at_the_root_the_anchor_names():
    """`/` in a CLI rule anchors at the worker's primary working directory. If the supervisor ever
    starts a worker elsewhere, `/*.py` protects that folder instead of the repository."""
    import importlib.util
    import inspect
    from pathlib import Path

    repo = Path(__file__).resolve().parent.parent.parent
    spec = importlib.util.spec_from_file_location("crew_cli_anchor", repo / "scripts" / "crew.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert "cwd=str(REPO_ROOT)" in inspect.getsource(module.run_process)

"""Nobody binds a path under `state/` at import time.

`qa.state.state_dir()` is the one seam the whole project reads state behind:
`QA_STATE_DIR` if set, else `<repo>/state`. A module constant built from
`REPO_ROOT` resolves once, when the module is imported, and therefore ignores
it -- so a test that redirects the store to a tmp tree is handed the real
files instead. That is not hypothetical. `scripts/bounty.py:34-46` carries the
incident in its own docstring: a test written while reviewing that module
"wrote its two-row fixture over the real snapshot, losing the vendor's
status_notes until the next full fetch".

The architecture audit of 2026-09-20 found three more of the same shape --
`scripts/inventory.py` (which writes), `scripts/submit.py` (a dead read of a
file nothing has written since filing became two events) and
`scripts/processes.py` (mixing this seam with `QA_REPO_ROOT` inside one
function) -- plus a dead constant in `scripts/render.py`. A guard is what
stops the fourth.

Two exemptions, both by name and both real:

* `qa/state.py` **is** the seam.
* `.claude/hooks/protect_state.py` must mean the committed `state/` whatever
  the environment says: it is the PreToolUse guard refusing hand-edits, and a
  guard that followed an override could be pointed away from the directory it
  protects.
"""

from __future__ import annotations

import ast
from pathlib import Path

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

REPO = Path(__file__).resolve().parent.parent.parent
ROOTS = ("qa/**/*.py", "scripts/**/*.py", ".claude/hooks/**/*.py")
EXEMPT = {"qa/state.py", ".claude/hooks/protect_state.py"}
ROOT_NAMES = {"REPO_ROOT", "REPO", "CODE_ROOT"}


def _builds_state_path(node: ast.AST) -> bool:
    """`<ROOT> / "state" / ...` -- a Path division whose parts name state/."""
    if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.Div):
        return False
    parts, walker = [], node
    while isinstance(walker, ast.BinOp) and isinstance(walker.op, ast.Div):
        parts.append(walker.right)
        walker = walker.left
    root = getattr(walker, "id", None)
    if root not in ROOT_NAMES:
        return False
    return any(isinstance(p, ast.Constant) and p.value == "state" for p in parts)


def _offenders() -> list[str]:
    found = []
    for path in sorted({p for root in ROOTS for p in REPO.glob(root)}):
        rel = path.relative_to(REPO).as_posix()
        if rel in EXEMPT:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        # Module level only: inside a function the expression is evaluated at
        # call time, which is the behaviour this guard is asking for.
        for node in tree.body:
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            value = node.value
            if value is not None and _builds_state_path(value):
                found.append(f"{rel}:{node.lineno}: {ast.unparse(node)[:70]}")
    return found


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_no_module_binds_a_state_path_at_import_time():
    """Read state through `state_dir()` at call time, or a test cannot redirect it."""
    offenders = _offenders()
    conclude(Measurement(
        verdict="failed" if offenders else "passed",
        reason=("a path under state/ bound at import time ignores "
                "QA_STATE_DIR: " + "; ".join(offenders) if offenders else
                "every module resolves state/ through qa.state.state_dir() "
                "at call time"),
        left=offenders, right=[],
        population={"roots": list(ROOTS), "exempt": sorted(EXEMPT)},
        sources={"seam": "qa/state.py::state_dir",
                 "incident": "scripts/bounty.py::out_path's docstring"},
    ))

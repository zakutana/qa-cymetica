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
# Calls that join their string arguments into a path.
PATH_CALLS = {"Path", "PurePath", "PosixPath", "WindowsPath", "joinpath"}


def _segments(node: ast.AST) -> list[str]:
    """The string literals this node joins into a path, whatever the root is called."""
    parts: list[ast.AST] = []
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        parts = [node.left, node.right]
    elif isinstance(node, ast.Call):
        func = node.func
        name = getattr(func, "attr", None) or getattr(func, "id", None)
        joins = (name == "join" and isinstance(func, ast.Attribute)
                 and ast.unparse(func.value).endswith("path"))
        if name in PATH_CALLS or joins:
            parts = list(node.args)
    return [p.value for p in parts
            if isinstance(p, ast.Constant) and isinstance(p.value, str)]


def _names_state(segment: str) -> bool:
    return segment == "state" or segment.startswith("state/")


def _is_main_guard(test: ast.AST) -> bool:
    return ast.unparse(test).replace("'", '"') == '__name__ == "__main__"'


def _bound_at_import(node: ast.AST, found: list[ast.AST]) -> None:
    """Every path naming state/ that is built when the module is imported.

    Not only a top-level assignment: a `try` body, a class body, a default
    argument and a decorator all run at import too. A function or lambda BODY
    runs at call time, which is the behaviour this guard is asking for, and so
    does the `if __name__ == "__main__":` block of a script.
    """
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        args = node.args
        for now in (*getattr(node, "decorator_list", ()), *args.defaults,
                    *(d for d in args.kw_defaults if d is not None)):
            _bound_at_import(now, found)
        return
    if isinstance(node, ast.If) and _is_main_guard(node.test):
        for child in node.orelse:
            _bound_at_import(child, found)
        return
    if any(_names_state(s) for s in _segments(node)):
        found.append(node)
        return
    for child in ast.iter_child_nodes(node):
        _bound_at_import(child, found)


def _offenders(repo: Path = REPO) -> list[str]:
    found = []
    for path in sorted({p for root in ROOTS for p in repo.glob(root)}):
        rel = path.relative_to(repo).as_posix()
        if rel in EXEMPT:
            continue
        hits: list[ast.AST] = []
        _bound_at_import(ast.parse(path.read_text(encoding="utf-8")), hits)
        found += [f"{rel}:{node.lineno}: {ast.unparse(node)[:70]}"
                  for node in hits]
    return found


# Every spelling of "a path under state/, built when the module is imported",
# and the shapes beside them that are not one. The scan asked for a top-level
# assignment, a root named REPO_ROOT, REPO or CODE_ROOT and a segment exactly
# "state", so every entry in _BOUND but `old_spelling` walked through it --
# `ROOT / "state"`, `Path(__file__)...parent / "state"`, `REPO /
# "state/x.json"` and `.joinpath("state")` among them. Deep pass of
# 2026-09-21, C07.
_BOUND = {
    "qa/named_root.py": 'ROOT = x\nA = ROOT / "state"\n',
    "scripts/file_root.py": ('from pathlib import Path\n'
                             'B = Path(__file__).resolve().parent.parent'
                             ' / "state" / "y"\n'),
    "qa/one_segment.py": 'REPO = x\nC = REPO / "state/x.json"\n',
    ".claude/hooks/joined.py": 'D = Path(__file__).parent.joinpath("state")\n',
    "qa/os_path.py": 'import os\nE = os.path.join(BASE, "state", "e.json")\n',
    "qa/old_spelling.py": 'F = REPO_ROOT / "state" / "ledger.json"\n',
    "qa/in_try.py": 'try:\n    G = HOME / "state"\nexcept OSError:\n    G = None\n',
    "qa/class_attr.py": 'class K:\n    H = ROOT / "state" / "h"\n',
    "qa/default.py": 'def f(path=ROOT / "state"):\n    return path\n',
}
_NOT_BOUND = {
    "qa/call_time.py": 'def f():\n    return ROOT / "state" / "x"\n',
    "qa/lambda_body.py": 'F = lambda: ROOT / "state"\n',
    "qa/main_block.py": 'if __name__ == "__main__":\n    X = ROOT / "state"\n',
    "qa/bare_strings.py": 'KEEP = ("state/ledger.json", "state")\n',
    "qa/statement.py": 'X = ROOT / "statement" / "states"\n',
    # The seam itself, by name.
    "qa/state.py": 'STATE = REPO_ROOT / "state"\n',
}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_no_module_binds_a_state_path_at_import_time(tmp_path):
    """Read state through `state_dir()` at call time, or a test cannot redirect it."""
    for rel, source in {**_BOUND, **_NOT_BOUND}.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(source, encoding="utf-8")
    caught = sorted({line.split(": ", 1)[0].rsplit(":", 1)[0]
                     for line in _offenders(tmp_path)})
    assert caught == sorted(_BOUND), (
        f"missed {sorted(set(_BOUND) - set(caught))}, "
        f"flagged {sorted(set(caught) - set(_BOUND))}")

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

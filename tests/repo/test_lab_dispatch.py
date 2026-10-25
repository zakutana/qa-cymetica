"""Every subcommand `scripts/lab.py` registers has a branch in `main()` (deep pass 2026-10-25, R01).

Commit 4403c058 added `lab.py index-at` by writing its branch where `elif args.cmd == "surface"` stood.
`surface` stayed registered, so `lab.py surface` parsed, ran nothing, printed nothing and exited 0 -- a
command that looks like it answered. A registered name with no branch is that defect in general, so the
first test reads `main()` itself; the second runs the two commands the swap touched.
"""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO / "scripts" / "lab.py"


def _main() -> ast.FunctionDef:
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    return next(node for node in tree.body
                if isinstance(node, ast.FunctionDef) and node.name == "main")


def _registered(main: ast.FunctionDef) -> set[str]:
    return {node.args[0].value for node in ast.walk(main)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_parser" and node.args
            and isinstance(node.args[0], ast.Constant)}


def _dispatched(main: ast.FunctionDef) -> set[str]:
    """Every name an `args.cmd == "x"` (or `args.cmd in (...)`) compares against."""
    out: set[str] = set()
    for node in ast.walk(main):
        if not (isinstance(node, ast.Compare) and isinstance(node.left, ast.Attribute)
                and node.left.attr == "cmd"):
            continue
        for op, right in zip(node.ops, node.comparators):
            if isinstance(op, ast.Eq) and isinstance(right, ast.Constant):
                out.add(right.value)
            elif isinstance(op, ast.In) and isinstance(right, (ast.Tuple, ast.List, ast.Set)):
                out.update(e.value for e in right.elts if isinstance(e, ast.Constant))
    return out


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_registered_subcommand_has_a_branch():
    main = _main()
    registered, dispatched = _registered(main), _dispatched(main)
    # A reading that found nothing would pass the set difference below over nothing.
    assert {"surface", "index-at", "tick", "verdicts"} <= registered, sorted(registered)
    assert registered - dispatched == set(), (
        f"registered with no branch in main(), so they parse and do nothing: "
        f"{sorted(registered - dispatched)}")


def _lab(tmp_path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    spec = importlib.util.spec_from_file_location("lab_dispatch_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "printable", lambda: None)
    return module


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_surface_and_index_at_both_dispatch(tmp_path, monkeypatch, capsys):
    module = _lab(tmp_path, monkeypatch)
    # Both stand in for their live reads: surface scans their catalogue, index-at reads a card.
    monkeypatch.setattr(module, "surface", lambda: {"surface": "read"})
    monkeypatch.setattr(module, "index_at_moments", lambda card, times: {
        "interval": "5d", "points": 2, "tried": ["5d"],
        "at": [{"at": times[0], "value": 101.5, "how": "point", "gap_h": 0.0}]})

    assert module.main(["surface"]) == 0
    assert '"surface": "read"' in capsys.readouterr().out, "lab.py surface printed nothing"

    assert module.main(["index-at", "a4a5b71e-de11-4805-b8a3-ed9c3f8f8161",
                        "2026-10-25T00:00:00+00:00"]) == 0
    out = capsys.readouterr().out
    assert "read on 5d" in out and "101.5" in out, out

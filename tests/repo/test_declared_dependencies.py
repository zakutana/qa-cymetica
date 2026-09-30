"""A clean machine installs what pyproject.toml says, and nothing else.

The cloud session of 2026-09-30 started from `pip install -e .` and found
`requests` missing: `qa/client.py` imports it inside two functions, so nothing
failed at import time and nothing here noticed. The same session found that
`scripts/prereg.py` puts a backslash inside an f-string expression, which only
Python 3.12 accepts, while `requires-python` promised 3.11.

So the declaration is read against what the code actually imports, function
bodies included -- the only place a third-party import can hide until it runs.
"""

from __future__ import annotations

import ast
import sys
import tomllib
from pathlib import Path

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

REPO = Path(__file__).resolve().parent.parent.parent
# Where the code that runs on a clean machine lives. tests/ is left out: it is
# run from a checkout that has already installed the dev tools.
ROOTS = ("qa", "scripts")
# Import name -> the name pyproject.toml declares it under, where they differ.
DISTRIBUTION = {"yaml": "pyyaml", "jinja2": "jinja2"}
# The floor the code needs: PEP 701 f-strings (scripts/prereg.py).
MIN_PYTHON = (3, 12)


def _declared() -> tuple[set[str], str]:
    data = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]
    names = set()
    for spec in project["dependencies"]:
        name = spec
        for cut in "<>=!~[;( ":
            name = name.split(cut)[0]
        names.add(name.strip().lower().replace("_", "-"))
    return names, project["requires-python"]


def _imported() -> dict[str, str]:
    """Top-level third-party module -> the first file that imports it."""
    local = {p.stem for root in ROOTS for p in (REPO / root).glob("*.py")}
    local |= set(ROOTS) | {"tests", "conftest"}
    found: dict[str, str] = {}
    for root in ROOTS:
        for path in sorted((REPO / root).rglob("*.py")):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    names = [node.module]
                else:
                    continue
                for name in names:
                    top = name.split(".")[0]
                    if top in sys.stdlib_module_names or top in local:
                        continue
                    found.setdefault(top, str(path.relative_to(REPO)))
    return found


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_third_party_import_is_a_declared_dependency():
    declared, _ = _declared()
    missing = {}
    for module, where in _imported().items():
        wanted = DISTRIBUTION.get(module, module).lower().replace("_", "-")
        if wanted not in declared:
            missing[module] = where

    conclude(Measurement(
        verdict="failed" if missing else "passed",
        reason=(f"imported but not declared in pyproject.toml: "
                f"{', '.join(f'{m} ({w})' for m, w in sorted(missing.items()))}"
                if missing else
                f"every third-party import under {', '.join(ROOTS)} is declared"),
        left={"undeclared": sorted(missing)}, right={"undeclared": []},
        sources={"pyproject": "pyproject.toml"}))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_promised_python_is_one_the_code_runs_on():
    _, promised = _declared()
    floor = tuple(int(part) for part in
                  promised.replace(">=", "").strip().split(".")[:2])

    conclude(Measurement(
        verdict="failed" if floor < MIN_PYTHON else "passed",
        reason=(f"requires-python {promised!r} admits Python "
                f"{'.'.join(map(str, floor))}, but scripts/prereg.py needs "
                f"{'.'.join(map(str, MIN_PYTHON))} (backslash inside an "
                f"f-string expression)"
                if floor < MIN_PYTHON else
                f"requires-python {promised!r} is at or above "
                f"{'.'.join(map(str, MIN_PYTHON))}"),
        left={"floor": list(floor)}, right={"floor_at_least": list(MIN_PYTHON)},
        sources={"pyproject": "pyproject.toml"}))

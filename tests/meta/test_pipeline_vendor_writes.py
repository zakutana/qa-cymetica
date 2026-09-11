"""VENDOR: a check may read their correspondence channel, never write to it unasked.

For five days two checks in tests/rest/test_qa_agent_channel.py posted a real
message to POST /api/v1/bounty/a2a/send as a side effect of measuring it --
61 such POSTs sit in the evidence store between 2026-09-05 and 2026-09-10,
roughly one per full run. The async-grounding check asked "What currency does
the bounty programme pay rewards in, and what is the flat amount per verified
bug?" every single time; the escalation check sent its own question whenever
the sync half answered below 0.7.

None of them reached our journal, because a check is not a script and only
scripts/a2a.py records what it sends. The vendor noticed before we did. On
2026-09-10 they wrote: "The bounty-currency question your agent re-sends on
the a2a channel was answered again into your inbox and ET-24544 is closed
with it."

CLAUDE.md already held the rule: an a2a message goes out through
scripts/a2a.py, and only on --confirm. The checks went round it because
nothing looked at tests for it. This looks.

Every function under tests/ -- outside tests/meta and tests/repo, which never
touch the network -- that posts to the a2a send path must call
`may_write_to_vendor()` BEFORE the post. That function returns True only when
QA_ALLOW_A2A_SEND=1, so the default run reads and never writes.
"""

from __future__ import annotations

import ast
from pathlib import Path

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
GATE = "may_write_to_vendor"
MARKER = "a2a/send"


def _string_constants(tree: ast.Module) -> dict[str, str]:
    out: dict[str, str] = {}
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)):
            out[node.targets[0].id] = node.value.value
    return out


def ungated_vendor_writes(source: str) -> list[tuple[str, int]]:
    """(function, line) for every a2a post not preceded by the gate."""
    tree = ast.parse(source)
    consts = _string_constants(tree)
    offenders = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        posts, gates = [], []
        for node in ast.walk(fn):
            if not isinstance(node, ast.Call):
                continue
            if (isinstance(node.func, ast.Attribute) and node.func.attr == "post"
                    and node.args):
                first = node.args[0]
                target = (first.value if isinstance(first, ast.Constant)
                          and isinstance(first.value, str)
                          else consts.get(first.id)
                          if isinstance(first, ast.Name) else None)
                if target and MARKER in target:
                    posts.append(node.lineno)
            if isinstance(node.func, ast.Name) and node.func.id == GATE:
                gates.append(node.lineno)
        for line in posts:
            if not any(g < line for g in gates):
                offenders.append((fn.name, line))
    return offenders


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_no_check_writes_to_the_vendor_channel_unless_asked_to():
    offenders = []
    for path in sorted((REPO / "tests").rglob("test_*.py")):
        rel = path.relative_to(REPO).as_posix()
        if rel.startswith(("tests/meta/", "tests/repo/")):
            continue
        for fn, line in ungated_vendor_writes(path.read_text(encoding="utf-8")):
            offenders.append(f"{rel}:{line} in {fn}")
    assert not offenders, (
        f"checks post to their a2a channel without calling {GATE}() first: "
        f"{offenders}. A check that writes to the vendor on every run sent "
        f"them the same question 61 times before they told us.")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_detector_sees_an_ungated_post():
    """A negative control, so the guard above is not green by being blind."""
    ungated = (
        'SEND = "/api/v1/bounty/a2a/send"\n'
        'def test_x(client):\n'
        '    client.post(SEND, json={})\n')
    gated = (
        'SEND = "/api/v1/bounty/a2a/send"\n'
        'def test_x(client):\n'
        '    if not may_write_to_vendor():\n'
        '        return\n'
        '    client.post(SEND, json={})\n')
    late_gate = (
        'def test_x(client):\n'
        '    client.post("/api/v1/bounty/a2a/send", json={})\n'
        '    may_write_to_vendor()\n')
    assert ungated_vendor_writes(ungated) == [("test_x", 3)]
    assert ungated_vendor_writes(gated) == []
    assert ungated_vendor_writes(late_gate) == [("test_x", 2)], (
        "a gate called after the post does not stop the post")

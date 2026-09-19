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


def _is_gate(expr) -> bool:
    return (isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name)
            and expr.func.id == GATE)


def _gate_polarity(node) -> str | None:
    """"yes" when an `if` takes its BODY on the gate's yes, "no" when it takes
    it on the gate's no, None when it is not a gate we can read.

    A `may_write_to_vendor()` whose result is thrown away stops nothing, and
    until the deep pass of 2026-09-11 it counted as a gate. And the answer's
    DIRECTION counts: until V14 (2026-09-19, 3/3) any `if` whose test called
    the gate was one, so `if not gate(): post` -- a post that goes exactly when
    the gate says no -- read as gated.
    """
    if not isinstance(node, ast.If):
        return None
    test = node.test
    if _is_gate(test):
        return "yes"
    if (isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not)
            and _is_gate(test.operand)):
        return "no"
    if (isinstance(test, ast.BoolOp) and isinstance(test.op, ast.And)
            and any(_is_gate(v) for v in test.values)):
        return "yes"
    return None


def _leaves(block: list) -> bool:
    """Whether a block cannot fall through -- return, raise, skip, continue."""
    return any(isinstance(s, (ast.Return, ast.Raise, ast.Continue, ast.Break))
               for s in block)


def _guarded_nodes(fn) -> set[int]:
    """Every node the gate actually protects, by STRUCTURE not by line order.

    Two shapes are real gates and both are in the tree:

        if may_write_to_vendor():        # everything in the body
            client.post(SEND, ...)

        if not may_write_to_vendor():    # everything AFTER it in the block,
            return                       # because the block cannot fall through

    `any(gate_line < post_line)` was neither. It let ONE gate anywhere earlier
    in a function clear EVERY later post -- so a gated post followed by an
    unconditional one read as clean, which is this module's own incident: the
    grounding question and then the escalation question, two posts in one
    place, 61 real POSTs before the vendor told us. Three independent readers
    reproduced it on 2026-09-12, and the 2026-09-11 fix that required an
    `ast.If` had still never asked what was inside it.
    """
    guarded: set[int] = set()

    def guard(block: list) -> None:
        for inner in block:
            for child in ast.walk(inner):
                guarded.add(id(child))

    def walk(block: list, inherited: bool) -> None:
        protected = inherited
        for statement in block:
            if protected:
                for child in ast.walk(statement):
                    guarded.add(id(child))
            polarity = _gate_polarity(statement)
            if polarity == "yes":
                # The body runs on the gate's yes; the else on its no. An
                # `if gate(): return` protects nothing after it -- what follows
                # runs precisely when the gate said no.
                guard(statement.body)
                walk(statement.orelse, protected)
                continue
            if polarity == "no":
                # The body runs on the gate's no, so it is guarded by nothing;
                # the else runs on its yes. `if not gate(): return` protects
                # the rest of this block, because it cannot fall through.
                walk(statement.body, protected)
                guard(statement.orelse)
                if _leaves(statement.body):
                    protected = True
                continue
            for name in ("body", "orelse", "finalbody"):
                nested = getattr(statement, name, None)
                if isinstance(nested, list):
                    walk(nested, protected)
            for handler in getattr(statement, "handlers", []) or []:
                walk(handler.body, protected)

    walk(fn.body, False)
    return guarded


def ungated_vendor_writes(source: str) -> list[tuple[str, int]]:
    """(function, line) for every a2a post not preceded by the gate."""
    tree = ast.parse(source)
    consts = _string_constants(tree)
    offenders = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        guarded = _guarded_nodes(fn)
        posts = []
        for node in ast.walk(fn):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Attribute) and node.func.attr == "post":
                # The URL, positional or by keyword: `post(url=SEND)` was
                # invisible while only node.args[0] was read.
                first = (node.args[0] if node.args else
                         next((k.value for k in node.keywords if k.arg == "url"),
                              None))
                target = (first.value if isinstance(first, ast.Constant)
                          and isinstance(first.value, str)
                          else consts.get(first.id)
                          if isinstance(first, ast.Name) else None)
                if target and MARKER in target:
                    posts.append((node.lineno, id(node) in guarded))
        for line, gated in posts:
            if not gated:
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

    # V14, deep pass of 2026-09-19 (3/3): the gate was recognised in either
    # POLARITY. A post inside `if not gate():` runs exactly when the gate
    # says no, and `if gate(): return` leaves the posts after it running
    # only when the gate says no -- both read as gated.
    inverted = (
        'SEND = "/api/v1/bounty/a2a/send"\n'
        'def test_x(client):\n'
        '    if not may_write_to_vendor():\n'
        '        client.post(SEND, json={})\n')
    leaves_when_allowed = (
        'SEND = "/api/v1/bounty/a2a/send"\n'
        'def test_x(client):\n'
        '    if may_write_to_vendor():\n'
        '        return\n'
        '    client.post(SEND, json={})\n')
    in_the_else = (
        'SEND = "/api/v1/bounty/a2a/send"\n'
        'def test_x(client):\n'
        '    if not may_write_to_vendor():\n'
        '        pass\n'
        '    else:\n'
        '        client.post(SEND, json={})\n')
    assert ungated_vendor_writes(inverted) == [("test_x", 4)]
    assert ungated_vendor_writes(leaves_when_allowed) == [("test_x", 5)]
    assert ungated_vendor_writes(in_the_else) == [], (
        "the else of a negated gate runs only when the gate says yes")

    # T07, deep pass of 2026-09-11, triage 3/3. A gate whose answer is thrown
    # away gates nothing, and a post that names its URL by keyword is still a
    # post: the detector read only `node.args[0]` and any earlier gate call,
    # so both of these were green.
    ignored = (
        'SEND = "/api/v1/bounty/a2a/send"\n'
        'def test_x(client):\n'
        '    may_write_to_vendor()\n'
        '    client.post(SEND, json={})\n')
    by_keyword = (
        'SEND = "/api/v1/bounty/a2a/send"\n'
        'def test_x(client):\n'
        '    client.post(url=SEND, json={})\n')
    by_keyword_gated = (
        'SEND = "/api/v1/bounty/a2a/send"\n'
        'def test_x(client):\n'
        '    if not may_write_to_vendor():\n'
        '        return\n'
        '    client.post(url=SEND, json={})\n')
    assert ungated_vendor_writes(ignored) == [("test_x", 4)], (
        "a gate called and ignored does not stop the post")
    assert ungated_vendor_writes(by_keyword) == [("test_x", 3)], (
        "a post naming its URL by keyword is invisible to the detector")
    assert ungated_vendor_writes(by_keyword_gated) == []

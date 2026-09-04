"""A tiny extractor DSL for pulling comparable values out of dissimilar sources.

Deliberately hand-rolled rather than jsonpath-ng. Reconciliation is the
load-bearing test class in this project, and a dependency here would mean the
difference between "the platform contradicts itself" and "our library parsed it
differently" is not something we can inspect. Everything below is 120 lines we
can read.

Grammar, as used in tests/reconciliation/claims.yaml:

    jsonpath:$.a.b.c          the value at a path
    len:$.tools               length of the list/dict/string at a path
    set:$.agents[*].id        set of values at a wildcard path
    regex_int:(\\d+) commits   first capture group of a regex, as an int
    regex_set:\\(([A-Z, ]+)\\)  first capture group, split into a set
    count:MCP Tools           markdown list items under a heading
    keys:$.paths              set of keys of the object at a path
    const:42                  a literal, for values transcribed from a source
                              we cannot fetch (a Terms page, a chat message)
"""

from __future__ import annotations

import json
import re
from typing import Any


class ExtractionError(RuntimeError):
    """The extractor could not produce a value. Never silently returns None."""


# ---------------------------------------------------------------------------
# Minimal JSON path: $.a.b, $.a[0].b, $.a[*].b
# ---------------------------------------------------------------------------
def _walk(data: Any, path: str) -> list[Any]:
    if not path.startswith("$"):
        raise ExtractionError(f"path must start with '$': {path!r}")

    current: list[Any] = [data]
    tokens = re.findall(r"\.([A-Za-z0-9_\-]+)|\[(\*|\d+)\]", path[1:])

    for name, index in tokens:
        nxt: list[Any] = []
        for node in current:
            if name:
                if isinstance(node, dict) and name in node:
                    nxt.append(node[name])
            elif index == "*":
                if isinstance(node, list):
                    nxt.extend(node)
                elif isinstance(node, dict):
                    nxt.extend(node.values())
            else:
                i = int(index)
                if isinstance(node, list) and -len(node) <= i < len(node):
                    nxt.append(node[i])
        current = nxt
        if not current:
            raise ExtractionError(f"path {path!r} matched nothing")
    return current


def _as_text(body: Any) -> str:
    if isinstance(body, str):
        return body
    if isinstance(body, bytes):
        return body.decode("utf-8", errors="replace")
    return json.dumps(body, ensure_ascii=False)


def _as_json(body: Any) -> Any:
    if isinstance(body, (dict, list)):
        return body
    text = _as_text(body)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ExtractionError(f"source is not JSON: {text[:120]!r}") from exc


# ---------------------------------------------------------------------------
def extract(spec: str, body: Any) -> Any:
    kind, _, arg = spec.partition(":")
    if not arg and kind != "const":
        raise ExtractionError(f"extractor {spec!r} needs an argument")

    if kind == "const":
        try:
            return int(arg)
        except ValueError:
            return arg

    if kind == "jsonpath":
        values = _walk(_as_json(body), arg)
        return values[0] if len(values) == 1 else values

    if kind == "len":
        value = _walk(_as_json(body), arg)[0]
        if not isinstance(value, (list, dict, str)):
            raise ExtractionError(f"len: {arg!r} is a {type(value).__name__}")
        return len(value)

    if kind == "set":
        return frozenset(_stringify(v) for v in _walk(_as_json(body), arg))

    if kind == "keys":
        value = _walk(_as_json(body), arg)[0]
        if not isinstance(value, dict):
            raise ExtractionError(f"keys: {arg!r} is not an object")
        return frozenset(value)

    if kind == "regex_int":
        match = re.search(arg, _as_text(body))
        if not match:
            raise ExtractionError(f"regex_int found no match for {arg!r}")
        return int(match.group(1).replace(",", "").replace(" ", ""))

    if kind == "regex":
        match = re.search(arg, _as_text(body))
        if not match:
            raise ExtractionError(f"regex found no match for {arg!r}")
        return match.group(1)

    if kind == "regex_set":
        match = re.search(arg, _as_text(body))
        if not match:
            raise ExtractionError(f"regex_set found no match for {arg!r}")
        return frozenset(
            part.strip() for part in re.split(r"[,\s]+", match.group(1)) if part.strip()
        )

    if kind == "regex_all":
        found = re.findall(arg, _as_text(body))
        if not found:
            raise ExtractionError(f"regex_all found no match for {arg!r}")
        return frozenset(f if isinstance(f, str) else f[0] for f in found)

    if kind == "count":
        text = _as_text(body)
        pattern = rf"^#+\s*{re.escape(arg)}\s*$"
        lines = text.splitlines()
        start = next(
            (i for i, line in enumerate(lines) if re.match(pattern, line.strip(), re.I)),
            None,
        )
        if start is None:
            raise ExtractionError(f"count: no heading matching {arg!r}")
        items = 0
        for line in lines[start + 1:]:
            if re.match(r"^#+\s", line.strip()):
                break
            if re.match(r"^\s*[-*+]\s+\S", line):
                items += 1
        return items

    raise ExtractionError(f"unknown extractor kind {kind!r}")


def _stringify(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(value, sort_keys=True)


# ---------------------------------------------------------------------------
# Relations. Each returns (holds, explanation).
# ---------------------------------------------------------------------------
def relation_holds(relation: str, left: Any, right: Any, tolerance_pct: float = 0.0):
    if relation == "all_equal":
        return left == right, "values differ"

    if relation == "set_equal":
        a, b = frozenset(left), frozenset(right)
        if a == b:
            return True, ""
        only_a = sorted(a - b)
        only_b = sorted(b - a)
        return False, f"only in left: {only_a}; only in right: {only_b}"

    if relation == "subset":
        a, b = frozenset(left), frozenset(right)
        return a <= b, f"left has {sorted(a - b)} which right lacks"

    if relation == "within_tolerance":
        try:
            a, b = float(left), float(right)
        except (TypeError, ValueError):
            return False, "values are not numeric"
        if a == b:
            return True, ""
        denominator = max(abs(a), abs(b)) or 1.0
        delta = abs(a - b) / denominator * 100
        return delta <= tolerance_pct, f"differ by {delta:.1f}% (tolerance {tolerance_pct}%)"

    raise ExtractionError(f"unknown relation {relation!r}")

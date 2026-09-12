"""Their side, watched: what their tools promise and what their answers carry.

[operator 2026-09-12] *"Dyt jsem ti rikal ze system ma byl self imprived self
optimized tak jak je mozne ze by sis toho nevsim?"*

The patrol in `scripts/processes.py` finds every skill, script and hook we have
and measures what each one did. All of it points at US. Nothing pointed at
Cymetica, and the day that was said, the proof was already on disk: they fixed
#97 that afternoon, and `period.label` and `headline_period` were sitting in
answers we had captured that morning. We learned about the fix from a Telegram
message the operator pasted.

Two drifts, both read from captures we make anyway:

    the contract   a tool's parameters, their types, defaults and required set.
                   A rename here breaks a call we make, silently, at three in
                   the morning, and the old comparison read only `name`.
    the shape      which fields an answer carries. A field that appears is how
                   a fix announces itself before anyone writes to us; a field
                   that vanishes is how a check starts measuring nothing.

One reader, because three callers need the answer and none of them may
disagree: `lab.py surface` (the laboratory's catalogue check), the patrol, and
the reminder that names it at the start of a session -- the same reason
`qa/channels.py` is a library and not three ideas of "unanswered".

`audits/surface.json` is the remembered shape. It is small and in git on
purpose: the evidence store prunes at three days and keeps one witness per
call, so a shape that lived only there would be unreadable by the time it
mattered. That is exactly what had happened to the tool schemas in
`audits/nexus-baseline.json`.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REMEMBERED = REPO_ROOT / "audits" / "surface.json"

# How deep a path is followed. Their payloads nest an equity curve and a basket
# inside a bot inside a listing; past this the paths stop being a shape and
# start being data.
MAX_DEPTH = 6
# What about a parameter would change the meaning or the success of our call.
PARAM_FACETS = ("type", "default", "enum", "items", "format")


def tool_shape(tool: dict) -> dict:
    """The part of a tool that we would notice breaking.

    Not the description: theirs are prose, they reword them, and a reworded
    sentence is not a changed contract. The schema is the contract.
    """
    schema = tool.get("inputSchema") or tool.get("input_schema") or {}
    properties = schema.get("properties") or {}
    params = {}
    for name, spec in properties.items():
        if not isinstance(spec, dict):
            params[name] = {"type": "?"}
            continue
        params[name] = {facet: spec[facet] for facet in PARAM_FACETS
                        if facet in spec}
    return {"required": sorted(str(r) for r in (schema.get("required") or [])),
            "params": params}


def _what_moved(was: dict, now: dict) -> list[str]:
    """Said the way a person reads it, because it goes into a reminder."""
    said = []
    before, after = was.get("params") or {}, now.get("params") or {}
    for name in sorted(set(before) - set(after)):
        said.append(f"{name} gone")
    for name in sorted(set(after) - set(before)):
        said.append(f"{name} added")
    for name in sorted(set(before) & set(after)):
        if before[name] != after[name]:
            said.append(f"{name}: {json.dumps(before[name], sort_keys=True)}"
                        f" -> {json.dumps(after[name], sort_keys=True)}")
    if was.get("required") != now.get("required"):
        said.append(f"required {was.get('required')} -> {now.get('required')}")
    return said


def tools_drift(before: list[dict], now: list[dict]) -> dict:
    """New tools, gone tools, and -- new on 2026-09-12 -- changed ones.

    Until this, `lab.py surface` compared `t["name"]` alone, so every change
    that keeps a tool's name left the comparison silent: a renamed parameter, a
    new required one, a changed default. All three break or quietly re-aim a
    call we already make.
    """
    was = {str(t.get("name")): tool_shape(t) for t in before
           if isinstance(t, dict) and t.get("name")}
    has = {str(t.get("name")): tool_shape(t) for t in now
           if isinstance(t, dict) and t.get("name")}
    changed = []
    for name in sorted(set(was) & set(has)):
        moved = _what_moved(was[name], has[name])
        if moved:
            changed.append({"tool": name, "what": moved,
                            "was": was[name], "now": has[name]})
    return {"new": sorted(set(has) - set(was)),
            "gone": sorted(set(was) - set(has)),
            "changed": changed}


def fields(payload, depth: int = MAX_DEPTH) -> set[str]:
    """Every named path in an answer, with list positions collapsed.

    Positions are collapsed because a listing that returns fourteen bots today
    and fifteen tomorrow has not changed shape; keyed on positions, every poll
    would read as a drift and the whole mechanism would be noise.
    """
    found: set[str] = set()

    def walk(node, path: str, left: int) -> None:
        if left <= 0:
            return
        if isinstance(node, dict):
            for key, value in node.items():
                here = f"{path}.{key}" if path else str(key)
                found.add(here)
                walk(value, here, left - 1)
        elif isinstance(node, list):
            for item in node:
                walk(item, f"{path}[]" if path else "[]", left)

    walk(payload, "", depth)
    return found


def fields_drift(before: set[str], now: set[str]) -> dict:
    """What their answer started carrying, and what it stopped carrying."""
    return {"appeared": sorted(now - before), "vanished": sorted(before - now)}


RECENT_HOURS = 48.0
TOOLS_CALL = "tools/list"


def _captures_since(hours: float, root: Path | None = None):
    """Recent captures only, newest first.

    The store holds thousands and a session start cannot read them all, so the
    tree is stat-ed and only what is new is opened. A capture is never
    rewritten, so mtime is its age.
    """
    from qa.evidence import evidence_root

    base = Path(root) if root else evidence_root()
    folder = base / "sha256"
    if not folder.is_dir():
        return
    cutoff = __import__("time").time() - hours * 3600
    recent = []
    for path in folder.rglob("*.json"):
        try:
            when = path.stat().st_mtime
        except OSError:
            continue
        if when >= cutoff:
            recent.append((when, path))
    for _, path in sorted(recent, reverse=True):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue
        if isinstance(record, dict):
            yield record


def _payload(record: dict):
    """What their answer actually said, past our own capture envelope."""
    body = (record.get("response") or {}).get("body")
    if isinstance(body, dict) and "value" in body:
        return body.get("value")
    return body


def shapes_since(hours: float = RECENT_HOURS, root: Path | None = None) -> dict:
    """The shape of each call's newest recent answer, keyed the pruner's way.

    Newest wins, so one stale reply cannot look like a field that vanished.
    Only 2xx answers: an error page has a shape of its own and comparing it
    against a good one would report a drift every time their server hiccups.
    """
    from qa.evidence import call_key

    seen: dict[str, dict] = {}
    for record in _captures_since(hours, root):
        status = (record.get("response") or {}).get("status_code")
        if not isinstance(status, int) or not 200 <= status < 300:
            continue
        key = call_key(record)
        if key in seen:
            continue
        seen[key] = {"fields": sorted(fields(_payload(record))),
                     "seen": record.get("captured_at")}
    return seen


def tools_seen(hours: float = RECENT_HOURS, root: Path | None = None):
    """The newest recently-captured tools/list, or None if there is none.

    None is not an empty catalogue: nothing recent to read is not the vendor
    withdrawing every tool, and the caller must not report it as one.
    """
    from qa.evidence import call_key

    for record in _captures_since(hours, root):
        if TOOLS_CALL not in call_key(record):
            continue
        payload = _payload(record) or {}
        listed = ((payload.get("result") or {}).get("tools")
                  if isinstance(payload, dict) else None)
        if isinstance(listed, list) and listed:
            return listed
    return None


def remembered(path: Path | None = None) -> dict:
    """The shape as we last agreed it. Absent file means nothing is known yet,
    which is not the same as "nothing changed" -- the caller says which."""
    target = path or REMEMBERED
    try:
        stored = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return stored if isinstance(stored, dict) else {}


def remember(shapes: dict, path: Path | None = None) -> Path:
    """Write the agreed shape back, sorted so a diff reads as a diff."""
    target = path or REMEMBERED
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(shapes, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")
    return target


def drift_against(stored: dict, seen: dict) -> list[str]:
    """One line per call whose answer changed shape, ready for a reminder.

    A call we have never seen before is not a drift -- it is a first sighting,
    and reporting it would make the first run after any new check shout.
    """
    said = []
    for call in sorted(seen):
        before = set((stored.get(call) or {}).get("fields") or [])
        if not before:
            continue
        moved = fields_drift(before, set(seen[call].get("fields") or []))
        parts = ([f"+ {f}" for f in moved["appeared"][:4]]
                 + [f"- {f}" for f in moved["vanished"][:4]])
        if parts:
            said.append(f"{call}: {', '.join(parts)}")
    return said

"""Platform fingerprint -- our substitute for a build version.

Cymetica exposes no build identifier. openapi.json pins info.version to a
static "0.1.0", /api/v1/build-stats returns aggregate telemetry rather than a
revision, and no response carries a build header. Without a version we cannot
say which build a finding was observed against, and "we deployed a fix" becomes
unfalsifiable.

So we compute one: a hash over the documents that change when they ship. Any
change to that corpus demotes every GREEN component to AMBER automatically.
We never have to trust a deploy announcement -- we detect it.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any

from qa.config import base_urls
from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier


def _canonicalise(value: Any, volatile: set[str]) -> Any:
    """Strip keys that move on their own so the hash tracks shape, not clock."""
    if isinstance(value, dict):
        return {
            k: _canonicalise(v, volatile)
            for k, v in sorted(value.items())
            if k not in volatile
        }
    if isinstance(value, list):
        return [_canonicalise(v, volatile) for v in value]
    return value


def _hash_part(body: bytes, volatile: set[str]) -> str:
    try:
        parsed = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return hashlib.sha256(body).hexdigest()
    canonical = json.dumps(
        _canonicalise(parsed, volatile), sort_keys=True, ensure_ascii=False
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute(registry: EndpointRegistry | None = None, timeout: float = 20.0) -> dict[str, Any]:
    """Return {fingerprint, parts, computed_at, errors}.

    Never raises: a fingerprint we could not compute is recorded as such, and
    a run without one simply cannot verify a fix.
    """
    # Offline seam: an inner pytest session (pytester) must never reach the
    # network. A None fingerprint is recorded honestly and makes the run
    # inadmissible for verification, which is exactly right for a test run.
    if os.environ.get("QA_OFFLINE"):
        return {
            "fingerprint": None,
            "parts": {},
            "errors": {"offline": "QA_OFFLINE=1"},
            "computed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }

    registry = registry or EndpointRegistry.load()
    spec = registry.raw.get("fingerprint", {})
    volatile = set(spec.get("volatile_keys", []))
    urls = base_urls()

    parts: dict[str, str] = {}
    errors: dict[str, str] = {}

    # Session-level reads happen outside any test, so grant SAFE explicitly.
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        # Through the factory, not around the guard: this used to build its
        # own client with the guard's private sentinel, so the corpus was read
        # with no SafetyTransport under it. The factory keeps the request
        # shape byte-for-byte -- Accept, redirects, timeout -- because the
        # fingerprint is a hash of what comes back.
        from qa.client import build_fingerprint_client

        client = build_fingerprint_client(registry=registry, timeout=timeout)
        try:
            for part in spec.get("parts", []):
                kind = part.get("kind")
                # The key a successful read WOULD have used, computed before
                # the read so a failure can be recorded under it. Errors used
                # to be keyed by the part's dict repr while parts were keyed
                # by path, so nothing downstream could tell that a missing
                # part was missing because it could not be read.
                if kind == "http":
                    key = part["path"]
                elif kind == "mcp_tool_names":
                    key = f"mcp:tools/list:{part.get('auth', 'none')}"
                else:
                    key = str(part)
                try:
                    if kind == "http":
                        path = part["path"]
                        response = client.get(urls["web"] + path)
                        parts[path] = _hash_part(response.content, volatile)
                    elif kind == "mcp_tool_names":
                        response = client.post(
                            urls["mcp"],
                            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                            headers={"Content-Type": "application/json"},
                        )
                        names = sorted(
                            t.get("name", "")
                            for t in response.json().get("result", {}).get("tools", [])
                        )
                        key = f"mcp:tools/list:{part.get('auth', 'none')}"
                        parts[key] = hashlib.sha256(
                            json.dumps(names).encode("utf-8")
                        ).hexdigest()
                except Exception as exc:  # noqa: BLE001 -- recorded, never raised
                    errors[key] = f"{type(exc).__name__}: {exc}"
        finally:
            client.close()
    finally:
        CURRENT_TIER.reset(token)

    combined = hashlib.sha256(
        json.dumps(parts, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return {
        "fingerprint": f"sha256:{combined}" if parts else None,
        "parts": parts,
        "errors": errors,
        "computed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def diff(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    """Which parts of the corpus changed. This is the deploy detector.

    A part that could not be READ on either side is left out of the
    comparison. It was counted as an appearance or a disappearance, which is
    rule 8 one layer up: on 2026-09-07 a single ReadTimeout on /openapi.json
    at the start of a sweep put that part in `after` and not in `before`, the
    diff reported `+/openapi.json`, the run was marked fingerprint_drifted and
    became inadmissible -- 397 passing checks thrown away because one document
    was slow once. Nothing had deployed.

    Excluding it is not the same as ignoring it: the failure is recorded in
    `errors` and carried into the run record as fingerprint_errors, so a part
    that never reads is visible rather than silently uncompared.
    """
    unread = set(before.get("errors") or {}) | set(after.get("errors") or {})
    a = {k: v for k, v in (before.get("parts") or {}).items() if k not in unread}
    b = {k: v for k, v in (after.get("parts") or {}).items() if k not in unread}
    changed = [k for k in sorted(set(a) & set(b)) if a[k] != b[k]]
    changed += [f"+{k}" for k in sorted(set(b) - set(a))]
    changed += [f"-{k}" for k in sorted(set(a) - set(b))]
    return changed

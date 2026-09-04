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
from datetime import datetime, timezone
from typing import Any

import httpx

from qa.config import USER_AGENT, base_urls
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
    registry = registry or EndpointRegistry.load()
    spec = registry.raw.get("fingerprint", {})
    volatile = set(spec.get("volatile_keys", []))
    urls = base_urls()

    parts: dict[str, str] = {}
    errors: dict[str, str] = {}

    # Session-level reads happen outside any test, so grant SAFE explicitly.
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        from qa.client import _FACTORY_SENTINEL

        client = httpx.Client(
            _qa_factory=_FACTORY_SENTINEL,
            headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
            timeout=timeout,
            follow_redirects=True,
        )
        try:
            for part in spec.get("parts", []):
                kind = part.get("kind")
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
                    errors[str(part)] = f"{type(exc).__name__}: {exc}"
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
    """Which parts of the corpus changed. This is the deploy detector."""
    a, b = before.get("parts", {}), after.get("parts", {})
    changed = [k for k in sorted(set(a) & set(b)) if a[k] != b[k]]
    changed += [f"+{k}" for k in sorted(set(b) - set(a))]
    changed += [f"-{k}" for k in sorted(set(a) - set(b))]
    return changed

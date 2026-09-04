"""Source snapshots for the contradiction sweep.

The failure mode this module exists to prevent: reading mcp.json from a CDN
cache at T0 and a live endpoint at T0+40s, then reporting a "contradiction"
that is really just latency. Caching and live data manufacture false
contradictions, and a false contradiction reported to the vendor costs more
credibility than a missed one.

So every source is fetched once per session, its Date and X-Cache-Status are
recorded, and a comparison whose sources drifted outside the declared window is
INCONCLUSIVE -- never a failure, and never a ticket.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from qa.extractors import ExtractionError, extract


@dataclass
class Fetched:
    name: str
    body: Any
    status: int
    fetched_at: float
    date_header: str | None = None
    cache_status: str | None = None
    age: str | None = None
    error: str | None = None
    evidence_id: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and 200 <= self.status < 300

    def provenance(self) -> str:
        bits = [f"HTTP {self.status}"]
        if self.cache_status:
            bits.append(f"cache={self.cache_status}")
        if self.age:
            bits.append(f"age={self.age}s")
        if self.date_header:
            bits.append(self.date_header)
        return ", ".join(bits)


class Snapshot:
    """Fetches each declared source exactly once and caches the result."""

    def __init__(self, spec: dict[str, dict], rest_anon, rest_trusted_factory,
                 mcp_clients: dict[str, Any], window_seconds: int = 30):
        self.spec = spec
        self.rest = rest_anon
        self.rest_trusted_factory = rest_trusted_factory
        self.mcp_clients = mcp_clients
        self.window_seconds = window_seconds
        self._cache: dict[str, Fetched] = {}
        self.started_at = time.time()

    # -- fetching ---------------------------------------------------------
    def fetch(self, name: str) -> Fetched:
        if name in self._cache:
            return self._cache[name]

        source = self.spec.get(name)
        if source is None:
            raise ExtractionError(f"source {name!r} is not declared in claims.yaml")

        started = time.time()
        try:
            result = self._fetch_uncached(name, source, started)
        except Exception as exc:  # noqa: BLE001 -- an unfetchable source is data
            result = Fetched(
                name=name, body=None, status=0, fetched_at=started,
                error=f"{type(exc).__name__}: {exc}",
            )
        self._cache[name] = result
        return result

    def _fetch_uncached(self, name: str, source: dict, started: float) -> Fetched:
        kind = source.get("kind")

        if kind in ("json", "text"):
            response = self.rest.get(source["url"])
            body = response.json() if kind == "json" else response.text
            return Fetched(
                name=name, body=body, status=response.status_code, fetched_at=started,
                date_header=response.headers.get("date"),
                cache_status=response.headers.get("x-cache-status"),
                age=response.headers.get("age"),
            )

        if kind == "mcp_tools":
            identity = source.get("identity", "anon")
            client = self.mcp_clients.get(identity)
            if client is None:
                return Fetched(name=name, body=None, status=0, fetched_at=started,
                               error=f"identity {identity!r} unavailable")
            payload = client.raw("tools/list")
            tools = payload.get("result", {}).get("tools", [])
            return Fetched(name=name, body={"tools": tools}, status=200,
                           fetched_at=started)

        raise ExtractionError(f"unknown source kind {kind!r} for {name!r}")

    # -- reading ----------------------------------------------------------
    def value(self, name: str, extractor: str) -> Any:
        fetched = self.fetch(name)
        if not fetched.ok:
            raise ExtractionError(
                f"source {name!r} is unreadable ({fetched.error or fetched.status})"
            )
        return extract(extractor, fetched.body)

    def drift_seconds(self, a: str, b: str) -> float:
        return abs(self.fetch(a).fetched_at - self.fetch(b).fetched_at)

    def cached_beyond_window(self, name: str) -> bool:
        """A cache HIT older than the window cannot be compared to live data."""
        fetched = self.fetch(name)
        if (fetched.cache_status or "").upper() != "HIT":
            return False
        try:
            return int(fetched.age or 0) > self.window_seconds
        except ValueError:
            return False

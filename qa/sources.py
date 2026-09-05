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
    def klass(self) -> str:
        """What KIND of read this was -- the same vocabulary bounty.py uses.

        A 401 body is not data. Comparing one against a live endpoint would
        manufacture a contradiction entirely out of our own credentials, and
        then report it as theirs.
        """
        if self.error is not None:
            return "unreachable"
        if self.status == 401:
            return "unauthorized"
        if self.status == 403:
            return "forbidden"
        if self.status == 404:
            return "not_found"
        if self.status >= 500:
            return "server_error"
        if not 200 <= self.status < 300:
            return "malformed"
        return "ok" if self.body is not None else "malformed"

    @property
    def ok(self) -> bool:
        return self.klass == "ok"

    def provenance(self) -> str:
        bits = [f"HTTP {self.status}", f"read={self.klass}"]
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
        # Keyed by (kind, url) -- see _cache_key.
        self._cache: dict[tuple, Fetched] = {}
        self.started_at = time.time()

    # -- fetching ---------------------------------------------------------
    @staticmethod
    def _cache_key(source: dict) -> tuple:
        """What identifies a fetch: the document, not the name we gave it.

        `llms_txt` and `llms_txt_2` are the same URL -- two statements inside
        one document. Keying the cache by source NAME fetched it twice, which
        put a real time gap between two halves of a self-consistency claim and
        made the drift guard measure a difference we created ourselves.
        """
        kind = source.get("kind")
        if kind == "mcp_tools":
            return (kind, source.get("identity", "anon"))
        return (kind, source.get("url"))

    def fetch(self, name: str) -> Fetched:
        source = self.spec.get(name)
        if source is None:
            raise ExtractionError(f"source {name!r} is not declared in claims.yaml")

        key = self._cache_key(source)
        if key in self._cache:
            return self._cache[key]

        started = time.time()
        try:
            result = self._fetch_uncached(name, source, started)
        except Exception as exc:  # noqa: BLE001 -- an unfetchable source is data
            result = Fetched(
                name=name, body=None, status=0, fetched_at=started,
                error=f"{type(exc).__name__}: {exc}",
            )
        self._cache[key] = result
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
        return self.value_with_witness(name, extractor)[0]

    def value_with_witness(self, name: str, extractor: str) -> tuple[Any, str]:
        """The value and the text it was read out of.

        A finding about their document should be able to quote the sentence
        rather than offer our summary of it.
        """
        from qa.extractors import extract_with_witness

        fetched = self.fetch(name)
        if not fetched.ok:
            raise ExtractionError(
                f"source {name!r} read as {fetched.klass} "
                f"({fetched.error or f'HTTP {fetched.status}'}); "
                f"a failed read is not a value"
            )
        return extract_with_witness(extractor, fetched.body)

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

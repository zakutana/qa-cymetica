"""One collectible check per path the platform documented and did not serve.

The audit's `inventory-population-unpinned`: reachability was computed over
whatever the vendor documented at that moment, so when 27 paths left the
documentation the denominator shrank, eight sections went green, and a finding
about 404s read as verified -- without a single endpoint being fixed.

These 26 paths are pinned in documented-404.yaml at the moment they were
measured. Each one is now a named nodeid, which means the ledger can point at
it, a regression can be detected, and "removed from the documentation" is a
distinct answer from "fixed".

Only one of the three outcomes is a fix:

    still documented, still 404   FAIL
    still documented, now served  PASS   <- the fix
    no longer documented          INCONCLUSIVE

The third is deliberately not a pass. Withdrawing a promise is a legitimate
way to resolve a broken promise, but it is the vendor's call to announce, not
a measurement we may quietly bank on their behalf.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

PINNED = Path(__file__).parent / "documented-404.yaml"

SOURCE_URLS = {
    "llms.txt": "/llms.txt",
    "agent-skills.json": "/.well-known/agent-skills.json",
}


def load_pinned() -> dict:
    return yaml.safe_load(PINNED.read_text(encoding="utf-8"))


PINS = load_pinned()["paths"]


@pytest.fixture(scope="session")
def documents(rest_anon) -> dict[str, str]:
    """Each documenting source, fetched once. Read as text: we are asking
    whether the document still names a path, not what it means by it."""
    out = {}
    for name, url in SOURCE_URLS.items():
        try:
            response = rest_anon.get(url)
            out[name] = response.text if 200 <= response.status_code < 300 else None
        except Exception:  # noqa: BLE001 -- an unreadable source is data
            out[name] = None
    return out


@qa(component="discovery.llmstxt", tier=SafetyTier.SAFE, surface="rest")
@pytest.mark.parametrize("pin", PINS, ids=[p["path"] for p in PINS])
def test_documented_path_is_served(pin, rest_anon, documents):
    """A path this platform documents must not answer 404."""
    document = documents.get(pin["source"])
    if document is None:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"{pin['source']} could not be read, so we cannot tell "
                   f"whether {pin['path']} is still documented",
            sources={"document": pin["source"]},
        ))
        return

    still_documented = pin["path"] in document
    response = rest_anon.get(pin["path"])
    status = response.status_code

    if not still_documented:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"{pin['path']} was removed from {pin['source']}, "
                   f"not fixed in place (it now answers {status})",
            left=pin["path"], right=status,
            sources={"document": pin["source"], "pinned_at": load_pinned()["pinned_at"]},
            claim_id="documented_404",
        ))
        return

    conclude(Measurement(
        verdict="failed" if status == 404 else "passed",
        reason=f"{pin['source']} documents {pin['path']}, which answers {status}",
        left=f"documented in {pin['source']}", right=status,
        sources={"document": pin["source"], "section": pin["section"]},
        claim_id="documented_404",
        population=load_pinned()["population"],
    ))


@qa(component="discovery.llmstxt", tier=SafetyTier.SAFE, surface="meta")
def test_the_pinned_population_is_intact():
    """The pin file is the denominator. If it can be edited without anyone
    noticing, the measurement it protects is worth nothing."""
    data = load_pinned()
    assert len(data["paths"]) == 26, len(data["paths"])
    assert data["population"] == 141
    assert len({p["path"] for p in data["paths"]}) == 26, "a path is pinned twice"
    for pin in data["paths"]:
        assert pin["source"] in SOURCE_URLS, pin
        assert pin["path"].startswith("/"), pin

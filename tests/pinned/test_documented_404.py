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

import re

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


_DOCUMENTS: dict[str, tuple[str | None, str]] = {}


@pytest.fixture
def documents(rest_anon) -> dict[str, tuple[str | None, str]]:
    """Each documenting source, fetched once, with WHY if it could not be read.

    Function-scoped with a module-level cache rather than session-scoped, and
    that is load-bearing: a session fixture is built during the first test's
    setup, BEFORE the autouse fixture that puts a safety tier in scope. The
    transport guard correctly refused all 26 fetches as fixture-time requests
    with no tier -- exactly what it is for. Fetching lazily from inside the
    test keeps the guard satisfied and still costs two requests per session.

    The reason is carried alongside the text. Returning a bare None cost an
    hour here: 26 checks said "llms.txt could not be read" while the actual
    message sat in a swallowed exception. Same lesson as classify_read -- a
    failure has a kind, and discarding the kind turns a diagnosable problem
    into a mystery.
    """
    if not _DOCUMENTS:
        for name, url in SOURCE_URLS.items():
            try:
                response = rest_anon.get(url)
            except Exception as exc:  # noqa: BLE001 -- an unreadable source is data
                _DOCUMENTS[name] = (None, f"{type(exc).__name__}: {exc}")
                continue
            if 200 <= response.status_code < 300:
                _DOCUMENTS[name] = (response.text, "ok")
            else:
                _DOCUMENTS[name] = (None, f"HTTP {response.status_code}")
    return _DOCUMENTS


# A path ends where a path segment cannot continue. Without this the check
# compared paths as SUBSTRINGS, and every rename in report #49 read as the old
# path still being documented: /api/v1/account matches inside
# /api/v1/account/me, /api/v1/clob/order inside /api/v1/clob/orders,
# /api/v1/agentbook/post inside /api/v1/agentbook/posts. Three renames that
# landed on 2026-09-04 were reported as unfixed for two days because of it,
# and the vendor's own note said to grep EXACT -- which is precisely the
# distinction this expresses.
_CONTINUES = r"(?![A-Za-z0-9_/{}-])"


def documents_the_path(document: str, path: str) -> bool:
    """Is THIS path documented, as opposed to one that starts with it?"""
    return re.search(re.escape(path) + _CONTINUES, document) is not None


def successors(document: str, path: str) -> set[str]:
    """Longer paths the document carries that begin with this one.

    A rename and a deletion are different resolutions and deserve different
    words on the page: "renamed to /api/v1/account/me" is a fix, "nothing
    replaced it" is a removal.
    """
    found = set(re.findall(re.escape(path) + r"[A-Za-z0-9_/{}-]+", document))
    return {f for f in found if f != path}


@qa(component="discovery.llmstxt", tier=SafetyTier.SAFE, surface="rest")
@pytest.mark.parametrize("pin", PINS, ids=[p["path"] for p in PINS])
def test_documented_path_is_served(pin, rest_anon, documents):
    """A path this platform documents must not answer 404."""
    document, why = documents.get(pin["source"], (None, "not fetched"))
    if document is None:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"{pin['source']} could not be read ({why}), so we cannot "
                   f"tell whether {pin['path']} is still documented",
            sources={"document": pin["source"], "read": why},
        ))
        return

    still_documented = documents_the_path(document, pin["path"])
    response = rest_anon.get(pin["path"])
    status = response.status_code

    if not still_documented:
        # A rename and a deletion are different resolutions. If the document
        # now carries a longer path in place of this one AND that path is
        # served, the promise was corrected rather than withdrawn -- which is
        # a fix, and the only one of the three no-longer-documented outcomes
        # that may pass. Verified by calling the successor, not by trusting
        # that a similar-looking string means it works.
        superseded = sorted(successors(document, pin["path"]))
        served = [p for p in superseded if rest_anon.get(p).status_code != 404]
        if served:
            conclude(Measurement(
                verdict="passed",
                reason=(f"{pin['path']} was renamed, not withdrawn: "
                        f"{pin['source']} now documents {', '.join(served)}, "
                        f"which is served"),
                left=pin["path"], right=served,
                sources={"document": pin["source"], "section": pin["section"]},
                claim_id="documented-404",
                population=load_pinned()["population"],
            ))
            return
        # Withdrawing the promise resolves the defect, which was that the
        # documentation promised what the server did not serve. It resolves it
        # by deletion rather than by building, and the reason line says so --
        # but the contract does hold now, and that is what this check is about.
        #
        # This was Inconclusive until 2026-09-05, guarding the audit finding
        # `inventory-population-unpinned`: paths leaving the docs shrank the
        # denominator and eight sections went green with nothing fixed. The
        # PIN is what actually stops that. All 26 paths are named here forever,
        # each is its own nodeid, and a deleted one is still reported by name.
        # Inconclusive on top of that guarded nothing and produced a state the
        # operator could not act on -- it read as "not reproducible", which
        # sounds like a result rather than an inability to measure.
        conclude(Measurement(
            verdict="passed",
            reason=(f"{pin['path']} is no longer promised by {pin['source']}: "
                    f"the documentation was corrected by DELETING the entry, "
                    f"not by building the endpoint"
                    + (f" (the paths that replaced it, {', '.join(superseded)}, "
                       f"answer 404 too)" if superseded else "")),
            left=pin["path"], right="removed from the documentation",
            sources={"document": pin["source"], "pinned_at": load_pinned()["pinned_at"],
                     "old_path_answers": status},
            claim_id="documented-404",
            population=load_pinned()["population"],
        ))
        return

    conclude(Measurement(
        verdict="failed" if status == 404 else "passed",
        reason=f"{pin['source']} documents {pin['path']}, which answers {status}",
        left=f"documented in {pin['source']}", right=status,
        sources={"document": pin["source"], "section": pin["section"]},
        claim_id="documented-404",
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

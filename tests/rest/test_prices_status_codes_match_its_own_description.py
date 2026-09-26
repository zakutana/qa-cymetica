"""A path's `responses` object declares the status codes it can return.

`GET /api/v1/prices/{asset}` was newly documented in the 2026-09-25/26
deploy (report #130). Its own entry in `/openapi-public.json` carries this
free-text description:

    "Current real price for an asset. 404 unknown asset, 503 no real price
    available."

That sentence is the spec's own promise of two error codes. But the same
entry's machine-readable `responses` object -- the part a codegen tool or an
agent's schema-driven client actually reads, not the prose next to it --
declares only `200` and `422` (FastAPI's automatic validation-error code). No
`404`, no `503`.

**What was seen when this was written** (2026-09-26): asking for a made-up
asset (`NOTAREALASSETXYZ`) answers `HTTP 404` with a structured body
(`{"detail":{"error":{"code":"PRICE_NOT_FOUND", ...}}}`) -- exactly the
behaviour the description advertises, and exactly the code `responses` never
lists. An agent that builds a handler from the schema's status-code list, the
way `/build` tells them to, has no branch for the code this endpoint hands
back today.

This is the "status codes" axis named alongside parameters, required fields
and response schema: not a missing field inside a 200 body, but a status the
endpoint demonstrably returns and the schema never declares. `503` ("no real
price available") is not separately forced here -- one confirmed, undeclared
code already breaks a schema-driven caller, and manufacturing the second
condition is not needed to state that.

SAFE: two anonymous GETs, no key, no write.
"""

from __future__ import annotations

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

SPEC = "/openapi-public.json"
TEMPLATE_PATH = "/api/v1/prices/{asset}"
BOGUS_ASSET = "NOTAREALASSETXYZ"


@qa(component="rest.markets", tier=SafetyTier.SAFE, surface="rest",
    claim="prices-status-codes-undeclared")
def test_an_unknown_asset_returns_a_status_the_schema_never_declares(rest_anon):
    """The prices endpoint's own description promises codes its schema omits."""
    spec_response = rest_anon.get(SPEC)
    if spec_response.status_code != 200:
        raise Inconclusive(f"{SPEC} answered HTTP {spec_response.status_code}")
    spec = spec_response.json() or {}
    entry = (spec.get("paths") or {}).get(TEMPLATE_PATH, {}).get("get")
    if not entry:
        raise Inconclusive(
            f"{SPEC} no longer documents a GET at {TEMPLATE_PATH} -- nothing "
            f"to compare")

    description = entry.get("description") or ""
    declared = {
        int(code) for code in (entry.get("responses") or {}) if code.isdigit()
    }

    probe = rest_anon.get(f"/api/v1/prices/{BOGUS_ASSET}",
                           headers={"Accept": "application/json"})
    actual = probe.status_code
    if actual == 429 or actual >= 500:
        raise Inconclusive(
            f"the probe itself answered HTTP {actual}, unrelated to the "
            f"schema question")

    undeclared = actual not in declared
    conclude(Measurement(
        verdict="failed" if undeclared else "passed",
        reason=(
            f"GET {TEMPLATE_PATH} answers HTTP {actual} to an unknown asset "
            f"(body: {probe.text[:160]!r}), but {SPEC}'s responses object for "
            f"this path declares only {sorted(declared)} -- even though the "
            f"path's own description says {description!r}"
            if undeclared else
            f"HTTP {actual} is among the codes {SPEC} declares for "
            f"{TEMPLATE_PATH} ({sorted(declared)})"),
        left={"actual_status": actual, "declared_statuses": sorted(declared)},
        right={"actual_status_in": sorted(declared)},
        population={"description": description, "probe_body": probe.text[:300]},
        sources={"spec": SPEC, "path": TEMPLATE_PATH, "probe_asset": BOGUS_ASSET},
    ))

"""Keys never reach disk.

`qa/evidence.py` has said since it was written that "Secrets never reach disk.
Redaction happens here, before write, and tests/meta/test_no_secrets_leak.py
greps the tree to prove it." That file did not exist -- and could not have, by
that name: tests/meta/test_pipeline_abort.py requires every file here but the
guard's own to be `test_pipeline_*`, so the promise named something the suite
would have rejected. The redaction is real -- this test was green the hour it
was written -- but nothing had ever asserted it, and on 2026-09-12 the store
became something we deliberately keep in a repository that gets pushed. A
promise in a docstring is not a guard.

One capture, built here, carrying a key in every place a key actually travels:
the header, a bearer token, a cookie, the URL and the body. It goes red when
somebody adds a door the redactor does not know about.

The other half of the question -- whether a real key ever did reach disk -- is
a fact about the repository, not about this function, so it lives in
tests/repo/test_evidence_in_git.py. It reads the whole tracked store, which is
a minute of I/O; tests/meta runs at the start of every session and may not
spend that.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx

from qa.evidence import REDACTED, EvidenceStore
from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

REPO = Path(__file__).resolve().parent.parent.parent

# Shaped like the platform's own keys (`evt_` + hex), long enough to match the
# generic high-entropy pattern too.
FAKE_KEY = "evt_" + "a1b2c3d4" * 6


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_capture_never_writes_the_key_it_travelled_with(tmp_path):
    """Header, bearer, cookie, query and body -- every door a key goes through."""
    request = httpx.Request(
        "POST", f"https://cymetica.com/api/v1/thing?token={FAKE_KEY}",
        headers={"x-api-key": FAKE_KEY,
                 "authorization": f"Bearer {FAKE_KEY}",
                 "x-hmac-signature": FAKE_KEY},
        content=json.dumps({"api_key": FAKE_KEY}).encode("utf-8"))
    response = httpx.Response(
        200, headers={"set-cookie": f"session={FAKE_KEY}"},
        content=json.dumps({"echoed": FAKE_KEY}).encode("utf-8"),
        request=request)

    store = EvidenceStore("run-secrets-test", root=tmp_path)
    evidence_id = store.capture(request, response, SafetyTier.SAFE, "test.rule")
    written = (tmp_path / "sha256" / evidence_id[:2] /
               f"{evidence_id}.json").read_text(encoding="utf-8")

    def leaks(node, path="") -> list[str]:
        if isinstance(node, dict):
            return [w for key, value in node.items()
                    for w in leaks(value, f"{path}.{key}")]
        if isinstance(node, list):
            return [w for i, value in enumerate(node)
                    for w in leaks(value, f"{path}[{i}]")]
        return [path.lstrip(".")] if FAKE_KEY in str(node) else []

    found = leaks(json.loads(written))
    conclude(Measurement(
        verdict="failed" if found else "passed",
        reason=("the key reached disk at " + ", ".join(found[:6]) if found else
                "the key appears nowhere in the written capture, and "
                f"{written.count(REDACTED)} value(s) were replaced"),
        left={"places_with_the_key": len(found)},
        right={"redactions": written.count(REDACTED)},
        population={"where": found[:6]},
        sources={"redactor": "qa/evidence.py::redact"}))

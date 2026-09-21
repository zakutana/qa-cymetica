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

from qa.evidence import REDACTED, SECRET_HEADERS, EvidenceStore
from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

REPO = Path(__file__).resolve().parent.parent.parent

# Shaped like the platform's own keys (`evt_` + hex), long enough to match the
# generic high-entropy pattern too.
FAKE_KEY = "evt_" + "a1b2c3d4" * 6
# Shaped like NOTHING in SECRET_PATTERNS -- no evt_, no hex run, no Bearer, no
# JWT. FAKE_KEY is stripped by value redaction at every door, so it could not
# tell whether the header NAMES were known: x-api-key taken out of
# SECRET_HEADERS stayed green (V15, deep pass of 2026-09-19, 3/3).
PLAIN_KEY = "plain-Secret-Qz-Kx-Wv-Jm"
# Every header name qa/evidence.py redacts, written down here so that one
# falling out of SECRET_HEADERS is a red line rather than a quieter fixture.
PINNED_SECRET_HEADERS = frozenset({
    "x-api-key", "authorization", "cookie", "set-cookie",
    "x-hmac-signature", "x-signature", "proxy-authorization",
})


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


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_key_no_pattern_recognises_is_still_kept_off_disk_by_its_header(
        tmp_path):
    """The header door on its own. A key in a shape the value patterns miss is
    stopped only because the redactor knows the header's NAME -- so this is
    what goes red when a name falls out of SECRET_HEADERS.

    It sent five of the seven, so x-signature or proxy-authorization falling
    out stayed green (C10, deep pass of 2026-09-21). Every name is sent now,
    on the request and on the response, each with a key of its own so a leak
    names its door -- iterated from the PINNED set as well as the live one,
    because a fixture built from SECRET_HEADERS alone loses a name in the same
    edit that takes it out of the redactor, and then nothing is sent to leak.
    """
    fallen = sorted(PINNED_SECRET_HEADERS - SECRET_HEADERS)
    assert not fallen, (
        f"{fallen} no longer in SECRET_HEADERS: its value would reach disk "
        f"whenever it is not shaped like a pattern the redactor knows")

    names = sorted(PINNED_SECRET_HEADERS | SECRET_HEADERS)
    door = {name: f"{PLAIN_KEY}:{name}:" for name in names}
    request = httpx.Request(
        "GET", "https://cymetica.com/api/v1/thing", headers=door)
    response = httpx.Response(200, headers=door, content=b"{}",
                              request=request)

    store = EvidenceStore("run-secrets-headers", root=tmp_path)
    evidence_id = store.capture(request, response, SafetyTier.SAFE, "test.rule")
    written = (tmp_path / "sha256" / evidence_id[:2] /
               f"{evidence_id}.json").read_text(encoding="utf-8")

    leaked = [name for name, value in door.items() if value in written]
    assert not leaked, (
        f"a key reached disk through {leaked}, a header the redactor does not "
        f"name")
    assert PLAIN_KEY not in written, written
    assert written.count(REDACTED) >= 2 * len(names), written

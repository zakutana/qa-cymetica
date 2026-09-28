"""Content-addressed evidence capture.

A finding without its raw response is a claim, and we do not accept claims.
Every request and response the suite makes is written to disk, hashed by
content, and cited by id from the ticket that depends on it. That is what makes

    "verified against <surface> at <time> by <check>"

mechanically true rather than a form of words.

Secrets never reach disk. Redaction happens here, before write, and two tests
prove it rather than the docstring promising it: tests/meta/test_pipeline_secrets.py
captures a request carrying a key through every door one travels through, and
tests/repo/test_evidence_in_git.py reads the whole tracked store against the
keys on this machine. Until 2026-09-12 this line named a file that did not
exist -- and could not, under that name: tests/meta/test_pipeline_abort.py
requires every file there but the guard's own to be `test_pipeline_*`.
"""

from __future__ import annotations

import hashlib
import json
import re
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = REPO_ROOT / "evidence"


def evidence_root() -> Path:
    """Where captures land. Follows QA_STATE_DIR, so a test session -- or a
    script run under one -- writes its evidence beside its state rather than
    into the repository."""
    import os

    override = os.environ.get("QA_STATE_DIR")
    return Path(override) / "evidence" if override else EVIDENCE_DIR


# What the id is NOT taken over: the three fields that say when and by whom a
# capture was made, so the same response re-observed later dedupes to one id.
VOLATILE = ("captured_at", "run_id", "nodeid")


def content_id(record: dict) -> str:
    """The evidence id of a record: sha256 over its content minus VOLATILE.

    A function rather than four lines inside `write`, because the archive has
    to recompute it to prove a bundled body is what its name says. The id is
    emphatically NOT the sha256 of the FILE -- the file is written with
    `indent=2` and keeps the volatile fields -- and on 2026-09-12 an archive
    verifier assumed otherwise and condemned all 1 178 captures. It refused to
    release anything, which is why that assumption cost nothing.
    """
    stable = {k: v for k, v in record.items() if k not in VOLATILE}
    blob = json.dumps(stable, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def call_key(record: dict) -> str:
    """What makes two captures the same CALL.

    Method and path are not enough. Every MCP call goes to `/mcp/v1/` -- 812 of
    them on this machine -- so keyed on the path alone the newest capture of the
    whole endpoint would stand for all of them. The JSON-RPC method and tool
    name are part of the key. Query VALUES are not: `?offset=7400` would
    otherwise make every page of a listing its own call.

    Lives here, beside the store that writes the captures, because two readers
    need it and they may not disagree: `scripts/prune_runs.py` decides which
    capture survives a prune by this key, and `qa/surface.py` decides which
    answers to compare shapes across by the same one. It was the pruner's
    private helper until 2026-09-12.
    """
    request = record.get("request") or {}
    method = str(request.get("method") or "")
    url = str(request.get("url") or "")
    path, _, query = url.partition("?")
    keys = ",".join(sorted({p.split("=")[0] for p in query.split("&") if p}))
    rpc = ""
    body = request.get("body") or {}
    value = body.get("value") if isinstance(body, dict) else None
    if isinstance(value, dict):
        rpc = str(value.get("method") or "")
        params = value.get("params") or {}
        if isinstance(params, dict) and params.get("name"):
            rpc = f"{rpc}:{params['name']}"
    return f"{method} {path}?{keys} {rpc}".strip()


REDACTED = "<redacted>"

# Header names whose values never reach disk.
SECRET_HEADERS = frozenset({
    "x-api-key", "authorization", "cookie", "set-cookie",
    "x-hmac-signature", "x-signature", "proxy-authorization",
})

# Body/URL patterns that look like key material regardless of where they appear.
SECRET_PATTERNS = [
    re.compile(r"evt_[0-9a-fA-F]{32,}"),
    re.compile(r"\b[0-9a-fA-F]{48,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._\-]{20,}", re.IGNORECASE),
    re.compile(r"\beyJ[A-Za-z0-9._\-]{20,}"),  # JWT
]

# Evidence ids captured during the currently-running test. Drained by the
# pytest plugin into the run record so each result cites its own bytes.
CURRENT_EVIDENCE: ContextVar[list[str] | None] = ContextVar("qa_evidence", default=None)


def redact(text: str) -> str:
    for pattern in SECRET_PATTERNS:
        text = pattern.sub(REDACTED, text)
    return text


def _redact_headers(headers) -> dict[str, str]:
    out = {}
    for key, value in headers.items():
        out[key] = REDACTED if key.lower() in SECRET_HEADERS else redact(value)
    return out


def _decode(raw: bytes, limit: int = 512_000) -> dict[str, Any]:
    """Body as structured JSON when possible, redacted text otherwise."""
    if not raw:
        return {"encoding": "empty", "value": None}
    truncated = len(raw) > limit
    blob = raw[:limit]
    try:
        text = blob.decode("utf-8")
    except UnicodeDecodeError:
        return {"encoding": "binary", "sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw)}
    text = redact(text)
    try:
        return {"encoding": "json", "value": json.loads(text), "truncated": truncated}
    except json.JSONDecodeError:
        return {"encoding": "text", "value": text, "truncated": truncated}


class EvidenceStore:
    def __init__(self, run_id: str, root: Path | None = None):
        self.run_id = run_id
        self.root = (root or evidence_root()) / "sha256"
        self.root.mkdir(parents=True, exist_ok=True)
        self.captured = 0

    def capture(
        self,
        request: httpx.Request,
        response: httpx.Response,
        tier,
        rule_id: str | None = None,
    ) -> str:
        try:
            request_body = request.read()
        except Exception:
            request_body = b""
            # A raise here leaves `request._content` unset, so anything that
            # reads the request again later (a retry, a redirect replay)
            # meets a stream that already started iterating once and cannot
            # start again. Caching an empty body makes that second read a
            # hit instead of httpx.StreamConsumed -- see the matching
            # response-side comment below, where this was actually observed.
            request._content = b""
        try:
            response_body = response.read()
        except Exception:
            response_body = b""
            # The caller's own read comes right after this one returns
            # (httpx.Client.send() reads every non-streamed response itself).
            # Without `_content` cached, that second read does not repeat
            # this failure -- it raises StreamConsumed instead, pointing at
            # the caller's line with no trace of the read that actually
            # broke. Measured 2026-09-28: a sweep re-running
            # test_public_page_reads_are_documented crashed on it twice in a
            # row, both times reported far from here.
            response._content = b""

        record = {
            "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "run_id": self.run_id,
            "nodeid": _current_nodeid(),
            "tier": getattr(tier, "value", str(tier)),
            "endpoint_rule": rule_id,
            "request": {
                "method": request.method,
                "url": redact(str(request.url)),
                "headers": _redact_headers(request.headers),
                "body": _decode(request_body),
            },
            "response": {
                "status_code": response.status_code,
                "reason": response.reason_phrase,
                "headers": _redact_headers(response.headers),
                "body": _decode(response_body),
                "elapsed_ms": _elapsed_ms(response),
            },
        }
        return self.write(record)

    def write(self, record: dict[str, Any]) -> str:
        digest = content_id(record)

        path = self.root / digest[:2] / f"{digest}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(
                json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False),
                encoding="utf-8",
            )
        self.captured += 1

        bucket = CURRENT_EVIDENCE.get()
        if bucket is not None and digest not in bucket:
            bucket.append(digest)
        return digest

    @staticmethod
    def path_for(evidence_id: str, root: Path | None = None) -> Path:
        base = (root or evidence_root()) / "sha256"
        return base / evidence_id[:2] / f"{evidence_id}.json"

    @staticmethod
    def load(evidence_id: str, root: Path | None = None) -> dict[str, Any]:
        return json.loads(EvidenceStore.path_for(evidence_id, root).read_text(encoding="utf-8"))


def _elapsed_ms(response: httpx.Response) -> int | None:
    try:
        return int(response.elapsed.total_seconds() * 1000)
    except (RuntimeError, AttributeError):
        return None


def _current_nodeid() -> str | None:
    from qa.safety import CURRENT_NODEID
    return CURRENT_NODEID.get()

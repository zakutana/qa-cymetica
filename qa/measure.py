"""Measurement: what a check deliberately says, in one structured object.

Before this module a finding's "detail" was regex-scraped from the pytest
traceback -- which is how a line of our own source once reached the vendor as
evidence. Now a check builds a Measurement and hands it to conclude(), which
raises or returns from the verdict. The verdict and pytest's outcome are one
value, and the run record carries the object rather than a scrape of the text.
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from qa.marks import Inconclusive

VERDICTS = ("passed", "failed", "inconclusive")

# The measurement the currently-running check has emitted, if any. Reset by
# the recorder before every test's setup, read by it in the call phase.
CURRENT_MEASUREMENT: ContextVar["Measurement | None"] = ContextVar(
    "qa_measurement", default=None
)


def _jsonable(value: Any) -> Any:
    if isinstance(value, (set, frozenset)):
        return sorted(_jsonable(v) for v in value)
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


@dataclass
class Measurement:
    verdict: str
    reason: str | None = None
    left: Any = None
    right: Any = None
    sources: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)
    evidence_ids: list[str] = field(default_factory=list)
    fingerprint: str | None = None
    claim_id: str | None = None
    role: str = "verdict"
    population: Any = None

    def __post_init__(self) -> None:
        if self.verdict not in VERDICTS:
            raise ValueError(f"verdict must be one of {VERDICTS}, got {self.verdict!r}")
        if self.role not in ("verdict", "evidence"):
            raise ValueError(f"role must be 'verdict' or 'evidence', got {self.role!r}")

    def as_record(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "reason": self.reason,
            "left": _jsonable(self.left),
            "right": _jsonable(self.right),
            "sources": _jsonable(self.sources),
            "provenance": _jsonable(self.provenance),
            "evidence_ids": list(self.evidence_ids),
            "fingerprint": self.fingerprint,
            "claim_id": self.claim_id,
            "role": self.role,
            "population": _jsonable(self.population),
        }


def explain(m: Measurement) -> str:
    lines = [m.reason or m.verdict]
    if m.left is not None or m.right is not None:
        lines.append(f"  left  = {_jsonable(m.left)!r}")
        lines.append(f"  right = {_jsonable(m.right)!r}")
    for name, prov in (m.provenance or {}).items():
        lines.append(f"  [{name}] {prov}")
    return "\n".join(lines)


def emit(m: Measurement) -> Measurement:
    """Record the measurement for the current check without concluding."""
    CURRENT_MEASUREMENT.set(m)
    return m


def conclude(m: Measurement) -> None:
    """Emit, then raise or return from the verdict. The only way a check ends.

    An `evidence`-role measurement can never be a failure: it is recorded and
    the check passes, because prose-versus-prose comparisons are evidence for
    a finding, never a finding by themselves.
    """
    emit(m)
    if m.role == "evidence":
        return None
    if m.verdict == "failed":
        raise AssertionError(explain(m))
    if m.verdict == "inconclusive":
        raise Inconclusive(m.reason or "inconclusive")
    return None

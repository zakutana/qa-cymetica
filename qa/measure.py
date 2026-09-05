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


class MissingData(Inconclusive):
    """A source did not carry what the check needs. Never a defect in itself.

    Raised by the readers below so "we could not read it" and "we read it and
    it was wrong" cannot be confused. Inheriting from Inconclusive means it
    lands in the run record as inconclusive without any check catching it.
    """


def required(mapping: Any, key: str, where: str) -> Any:
    """One field, or an Inconclusive naming what was missing and from where.

    Exists because `.get(key)` returning None is indistinguishable from a
    field that legitimately holds None, and both then flow into a comparison
    as though they were data. Four checks were wrong that way in a single day:
    a 401 body read as "no rows", a page size read as a collection size, and a
    key no row carried compared against itself as None.
    """
    if not isinstance(mapping, dict):
        raise MissingData(f"{where}: expected an object carrying {key!r}, got "
                          f"{type(mapping).__name__}")
    if key not in mapping:
        present = ", ".join(sorted(map(str, mapping))[:12]) or "nothing"
        raise MissingData(f"{where}: no {key!r} field (carries: {present})")
    return mapping[key]


def field_of_every(rows: list, key: str, where: str) -> list:
    """The same field from every row, or Inconclusive naming how many lacked it.

    A partially-present key is the dangerous case: it yields a list of some
    real values and some Nones, which compares as if the Nones were data.
    """
    if not rows:
        raise MissingData(f"{where}: no rows, so {key!r} cannot be read from them")
    absent = sum(1 for r in rows if not isinstance(r, dict) or r.get(key) is None)
    if absent:
        sample = sorted(map(str, rows[0])) if isinstance(rows[0], dict) else []
        raise MissingData(
            f"{where}: {absent} of {len(rows)} rows carry no {key!r} "
            f"(a row has: {', '.join(sample[:12]) or 'nothing'})")
    return [r[key] for r in rows]


def collection_size(payload: Any, total_key: str, rows_key: str, where: str) -> int:
    """How big a collection is, from the field that states it -- never len().

    `len(rows)` measures the response; a paginated endpoint answers with a
    window and says so in the same object. Report #52 went to the vendor
    because a check counted 200 rows against a stated total of 569.
    """
    total = required(payload, total_key, where)
    if not isinstance(total, int):
        raise MissingData(f"{where}: {total_key!r} is {type(total).__name__}, "
                          f"not a count")
    rows = payload.get(rows_key)
    if isinstance(rows, list) and len(rows) > total:
        raise MissingData(f"{where}: {len(rows)} rows returned but "
                          f"{total_key}={total}, so neither describes the "
                          f"collection reliably")
    return total


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

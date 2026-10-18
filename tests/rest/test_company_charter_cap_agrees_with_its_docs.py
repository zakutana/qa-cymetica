"""Build a Company's page lets a charter be as long as its docs say (2026-10-15, ET-31466).

Build a Company (cymetica.com/company) runs departments from a charter, "the department's standing
brief". Its docs give that charter one limit: llms.txt, "charter" (up to 2,000 characters: your
rules, notes and lessons -- every task the department runs starts from it)"; the OpenAPI,
DepartmentIn.charter `maxLength: 2000`.

**What was seen when this was written** (2026-10-15 ~20:20 UTC). The company-creation form in
/static/js/build-company.js draws each department's charter as
`<textarea class="bc-d-charter" rows="3" maxlength="1500">`: a browser stops typing at 1,500, so
an owner creating a company on the page cannot write the 2,000 the docs promise. The department
panel of /static/js/company-office.js carries no maxlength on its charter editor.

**The rule.** Every charter field the page's scripts cap (`maxlength` on an element whose class
names a charter, or a maxLength the script sets on one; the number a literal or a constant the same
script defines) allows at least the OpenAPI's DepartmentIn.charter maxLength. A field with no cap
is not judged; it holds no number to disagree with. A cap whose number the script does not hold is
unread, and a pass may not rest on it (C09, deep pass 2026-10-18: only a literal was read).

NOT asserted: the server's own refusal of a long charter, llms.txt's wording (it agrees with the
OpenAPI), or any charter's content.

SAFE: GETs only, the page's public scripts and the OpenAPI.
"""

from __future__ import annotations

import re

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

CLAIM = "company-charter-cap-agrees-with-its-docs"
SCRIPTS = ("/static/js/build-company.js", "/static/js/company-office.js")
_TAG = re.compile(r"<(?:textarea|input)\b[^>]*>", re.I)
_CLASS = re.compile(r"class=\"([^\"]*)\"", re.I)
_MAX = re.compile(r"maxlength=[\"']?\s*(\$\{[^}]*\}|\{[^}]*\}|[^\"'\s>]+)", re.I)
# A cap set by script on an element the statement names as a charter: `ta.maxLength = 1500` after
# `ta = ...('.bc-d-charter')`, `charterBox.setAttribute('maxlength', '1500')` (C09).
_PROP = re.compile(r"([\w$]+)\s*\.\s*(?:maxLength\s*=\s*|setAttribute\(\s*['\"]maxlength['\"]\s*,\s*)['\"]?([\w$.]+)", re.I)


def _resolve(raw: str, text: str) -> int | None:
    """A cap's number: a literal, `${NAME}`, or NAME, when the same script assigns NAME a number."""
    raw = raw.strip()
    if raw.startswith("{") and raw.endswith("}"):      # maxlength={1500}
        raw = raw[1:-1].strip()
    if raw.isdigit():
        return int(raw)
    name = re.fullmatch(r"\$\{\s*([\w$]+)\s*\}|([\w$]+)", raw)
    if not name:
        return None
    var = name.group(1) or name.group(2)
    bound = re.search(r"(?<![\w$.])" + re.escape(var) + r"\s*=\s*(\d+)\b", text)
    return int(bound.group(1)) if bound else None


def _caps(text: str) -> tuple[list[int], list[str]]:
    text = text or ""
    caps, unread = [], []
    for tag in _TAG.findall(text):
        cls = _CLASS.search(tag)
        cap = _MAX.search(tag)
        if cls and "charter" in cls.group(1).lower() and cap:
            value = _resolve(cap.group(1), text)
            (caps.append(value) if value is not None else unread.append(cap.group(1)))
    for m in _PROP.finditer(text):
        var, raw = m.group(1), m.group(2)
        bound = re.search(r"(?<![\w$.])" + re.escape(var) + r"\s*=\s*[^;\n]*charter", text, re.I)
        if "charter" not in var.lower() and not bound:
            continue
        value = _resolve(raw, text)
        (caps.append(value) if value is not None else unread.append(raw))
    return caps, unread


def charter_caps(text: str) -> list[int]:
    """The cap of every charter field the script draws or sets, as a number: a textarea or input whose
    class names a charter (its maxlength a literal or a constant the same script defines), or a
    maxLength the script sets on an element it took as a charter (C09, deep pass 2026-10-18)."""
    return _caps(text)[0]


def unresolved_caps(text: str) -> list[str]:
    """Charter caps whose number the script does not hold (`${window.LIMITS.charter}`): unread, so a
    pass may not rest on their absence."""
    return _caps(text)[1]


def documented_cap(spec: dict) -> int | None:
    """DepartmentIn.charter's maxLength, through an anyOf with null."""
    prop = (((spec or {}).get("components") or {}).get("schemas") or {}).get(
        "DepartmentIn", {}).get("properties", {}).get("charter") or {}
    for option in [prop] + list(prop.get("anyOf") or []):
        if isinstance(option, dict) and isinstance(option.get("maxLength"), int):
            return option["maxLength"]
    return None


@qa(component="rest.company", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_company_charter_cap_agrees_with_its_docs(rest_trusted):
    """The page's charter caps against the OpenAPI's."""
    spec = rest_trusted.get("/openapi-public.json")
    if spec.status_code != 200:
        raise Inconclusive(f"/openapi-public.json answered HTTP {spec.status_code}")
    limit = documented_cap(spec.json())
    if limit is None:
        raise Inconclusive("the OpenAPI states no maxLength for DepartmentIn.charter")
    caps, unread = {}, {}
    for path in SCRIPTS:
        r = rest_trusted.get(path)
        if r.status_code != 200:
            raise Inconclusive(f"{path} answered HTTP {r.status_code}")
        caps[path] = charter_caps(r.text)
        if unresolved_caps(r.text):
            unread[path] = unresolved_caps(r.text)
    short = {p: [c for c in cs if c < limit] for p, cs in caps.items() if any(c < limit for c in cs)}
    if unread and not short:
        raise Inconclusive(f"a charter cap whose number the script does not hold: {unread}; neither "
                           f"within the documented {limit:,} nor below it")
    if not any(caps.values()):
        raise Inconclusive(f"no charter field in {', '.join(SCRIPTS)} carries a maxlength")
    conclude(Measurement(
        verdict="failed" if short else "passed",
        reason=(f"the page caps a charter below the documented {limit:,} characters: "
                + "; ".join(f"{p} maxlength {cs}" for p, cs in short.items())
                if short else f"every capped charter field allows the documented {limit:,}"),
        left={"shortest_page_cap": min(c for cs in caps.values() for c in cs)},
        right={"documented_cap": limit},
        population={"caps_by_script": caps},
        sources={"page": ", ".join(SCRIPTS), "contract": "/openapi-public.json DepartmentIn.charter "
                 "maxLength; llms.txt: charter 'up to 2,000 characters'"},
        claim_id=CLAIM))

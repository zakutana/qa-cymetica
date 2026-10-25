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
names a charter, however quoted, or a maxLength the script sets on one -- named a charter by its
variable, the line binding it, or the class, id or name the script gives it; the number a literal or
a constant the same script defines) allows at least the OpenAPI's DepartmentIn.charter maxLength. A
field with no cap is not judged; it holds no number to disagree with, and allows the documented
length, so scripts that draw a charter field and cap none pass (A05, deep pass 2026-10-25: that was
Inconclusive, and the likeliest fix could never verify). Scripts that neither draw nor cap a
charter field are Inconclusive. A cap whose number the script does not hold is unread, and a pass
may not rest on it (C09, deep pass 2026-10-18: only a literal was read).

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
# The class however it is quoted -- "x", 'x', x, className={'x'} (A05, deep pass 2026-10-25: only
# double quotes were read).
_CLASS = re.compile(r"\bclass(?:Name)?\s*=\s*(?:\{?\s*([\"'`])(.*?)\1\s*\}?|([^\s>\"'`]+))", re.I | re.S)
# maxlength="1500", ="${N}", ={N}, or joined in from a name: maxlength="' + N + '".
_MAX = re.compile(r"maxlength\s*=\s*(?:[\"']?\s*[\"'`]\s*\+\s*([\w$.]+)\s*\+"
                  r"|[\"']?\s*(\$\{[^}]*\}|\{[^}]*\}|[^\"'\s>]+))", re.I)
# A cap set by script on a variable or straight on a lookup: `ta.maxLength = 1500` after
# `ta = ...('.bc-d-charter')` or `ta.className = 'bc-d-charter'`, `charterBox.setAttribute('maxlength',
# '1500')`, `row.querySelector('.bc-d-charter').maxLength = 1500` (C09; A05).
_PROP = re.compile(r"([\w$]+|[\w$.]+\(\s*['\"][^'\"]*['\"]\s*\))\s*\.\s*(?:maxLength\s*=\s*"
                   r"|setAttribute\(\s*['\"]maxlength['\"]\s*,\s*)['\"]?([\w$.]+)", re.I)


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


def _charter_tag(tag: str) -> bool:
    cls = _CLASS.search(tag)
    return bool(cls) and "charter" in (cls.group(2) if cls.group(2) is not None else cls.group(3)).lower()


def _named_charter(var: str, text: str) -> bool:
    """Whether the script takes `var` for a charter field: its name says so, the line binding it does
    (`ta = row.querySelector('.bc-d-charter')`), or the script names the element so by its class, id or
    name (`ta.className = 'bc-d-charter'`, A05)."""
    if "charter" in var.lower():
        return True
    v = re.escape(var)
    return bool(re.search(r"(?<![\w$.])" + v + r"\s*=\s*[^;\n]*charter", text, re.I)
                or re.search(r"(?<![\w$.])" + v + r"\s*\.\s*(?:className|id|name)\s*=\s*[^;\n]*charter", text, re.I)
                or re.search(r"(?<![\w$.])" + v + r"\s*\.\s*classList\.add\([^)]*charter", text, re.I)
                or re.search(r"(?<![\w$.])" + v + r"\s*\.\s*setAttribute\(\s*['\"](?:class|id|name)['\"]\s*,"
                             r"\s*[^)]*charter", text, re.I))


def _caps(text: str) -> tuple[list[int], list[str]]:
    text = text or ""
    caps, unread = [], []
    for tag in _TAG.findall(text):
        if not _charter_tag(tag) or not re.search(r"maxlength", tag, re.I):
            continue
        cap = _MAX.search(tag)
        raw = (cap.group(1) or cap.group(2)) if cap else None
        value = _resolve(raw, text) if raw else None
        # A maxlength whose number is not read is unread, never "no cap" (A05: an uncapped field passes).
        (caps.append(value) if value is not None else unread.append(raw or tag))
    for m in _PROP.finditer(text):
        target, raw = m.group(1), m.group(2)
        if "(" in target:                       # a lookup: its own selector names the field
            if "charter" not in target.lower():
                continue
        elif not _named_charter(target, text):
            continue
        value = _resolve(raw, text)
        (caps.append(value) if value is not None else unread.append(raw))
    return caps, unread


def charter_fields(text: str) -> int:
    """How many charter fields the script draws: a textarea or input whose class names a charter, or
    an element it creates and names a charter -- capped or not. A field with no cap allows any length,
    so it satisfies the rule; a script that draws none has nothing to judge (A05)."""
    text = text or ""
    drawn = sum(1 for tag in _TAG.findall(text) if _charter_tag(tag))
    made = {m.group(1) for m in re.finditer(r"(?<![\w$.])([\w$]+)\s*=\s*document\.createElement\(\s*['\"]"
                                             r"(?:textarea|input)['\"]\s*\)", text)}
    return drawn + sum(1 for var in made if _named_charter(var, text))


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
    caps, unread, fields = {}, {}, {}
    for path in SCRIPTS:
        r = rest_trusted.get(path)
        if r.status_code != 200:
            raise Inconclusive(f"{path} answered HTTP {r.status_code}")
        caps[path] = charter_caps(r.text)
        fields[path] = charter_fields(r.text)
        if unresolved_caps(r.text):
            unread[path] = unresolved_caps(r.text)
    short = {p: [c for c in cs if c < limit] for p, cs in caps.items() if any(c < limit for c in cs)}
    if unread and not short:
        raise Inconclusive(f"a charter cap whose number the script does not hold: {unread}; neither "
                           f"within the documented {limit:,} nor below it")
    every = [c for cs in caps.values() for c in cs]
    if not every and not any(fields.values()):
        raise Inconclusive(f"neither {' nor '.join(SCRIPTS)} draws a charter field or caps one; the "
                           f"field this judges is no longer where it was read")
    uncapped = sum(fields.values()) - sum(len(cs) for cs in caps.values())
    conclude(Measurement(
        verdict="failed" if short else "passed",
        reason=(f"the page caps a charter below the documented {limit:,} characters: "
                + "; ".join(f"{p} maxlength {cs}" for p, cs in short.items())
                if short else f"every charter field the page's scripts draw allows the documented "
                              f"{limit:,}: caps {every or 'none'}"
                              + (f", {uncapped} field(s) with no cap" if uncapped > 0 else "")),
        left={"shortest_page_cap": min(every) if every else None},
        right={"documented_cap": limit},
        population={"caps_by_script": caps, "charter_fields_by_script": fields},
        sources={"page": ", ".join(SCRIPTS), "contract": "/openapi-public.json DepartmentIn.charter "
                 "maxLength; llms.txt: charter 'up to 2,000 characters'"},
        claim_id=CLAIM))

"""What the "Build a Company's page lets a charter be as long as its docs say" check reads (A05, deep pass 2026-10-25).

Three readers reproduced two holes. A cap it could not see: `_CLASS` read only a double-quoted class
attribute, and a maxLength set by script counted only when the variable or its own line said
"charter", so `ta.className = 'bc-d-charter'; ta.maxLength = 1500` was invisible and another
recognised cap of 2000 passed the check. And the docstring's "a field with no cap is not judged" was
coded as Inconclusive, so the likeliest fix -- no maxlength at all -- could never verify.
The earlier readings (2026-10-15, C09) stay in tests/meta/test_pipeline_check_subjects.py.
"""

from __future__ import annotations

from qa.marks import SafetyTier, qa
from tests.rest.test_company_charter_cap_agrees_with_its_docs import (
    charter_caps,
    test_company_charter_cap_agrees_with_its_docs as check,
    unresolved_caps,
)

SPEC = {"components": {"schemas": {"DepartmentIn": {"properties": {"charter": {
    "anyOf": [{"type": "string", "maxLength": 2000}, {"type": "null"}]}}}}}}
OFFICE_CAPPED = "panel.innerHTML = '<textarea class=\"co-charter-edit\" maxlength=\"2000\"></textarea>';"
OFFICE_PLAIN = "$('bc-ed-charter').value = r ? r.charter : '';"


class _Reply:
    def __init__(self, body):
        self.status_code = 200
        self._body = body
        self.text = body if isinstance(body, str) else ""

    def json(self):
        return self._body


class _Site:
    def __init__(self, build: str, office: str):
        self.files = {"/openapi-public.json": SPEC, "/static/js/build-company.js": build,
                      "/static/js/company-office.js": office}

    def get(self, path, params=None):
        return _Reply(self.files[path])


def _drive(build: str, office: str) -> tuple[str, str]:
    from qa.marks import Inconclusive
    from qa.measure import CURRENT_MEASUREMENT

    CURRENT_MEASUREMENT.set(None)
    try:
        check(_Site(build, office))
        verdict, reason = "passed", ""
    except AssertionError as exc:
        verdict, reason = "failed", str(exc)
    except Inconclusive as exc:
        verdict, reason = "inconclusive", str(exc)
    finally:
        measured = CURRENT_MEASUREMENT.get()
        CURRENT_MEASUREMENT.set(None)          # not this test's own record
    return verdict, (measured.reason if measured is not None and measured.reason else reason)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_cap_is_read_however_its_field_is_named():
    assert charter_caps("row.innerHTML = \"<textarea class='bc-d-charter' rows='3' maxlength='1500'>\";") == [1500], (
        "a single-quoted class attribute")
    assert charter_caps("x = '<textarea class=bc-d-charter maxlength=1500>';") == [1500], "unquoted"
    made = ("const ta = document.createElement('textarea');\n"
            "ta.className = 'bc-d-charter'; ta.rows = 3; ta.maxLength = 1500;")
    assert charter_caps(made) == [1500], "the element named a charter by its class, capped by script"
    assert charter_caps("const t = document.createElement('textarea'); t.classList.add('bc-d-charter'); "
                        "t.setAttribute('maxlength', '1500');") == [1500]
    assert charter_caps("row.querySelector('.bc-d-charter').maxLength = 1500;") == [1500], (
        "a cap set straight on the lookup")
    joined = "const CHARTER_MAX = 1500;\nrow.innerHTML = '<textarea class=\"bc-d-charter\" maxlength=\"' + CHARTER_MAX + '\">';"
    assert charter_caps(joined) == [1500], "a cap joined into the markup from a constant"
    # Not a charter: another field's cap stays out.
    assert charter_caps("const n = document.createElement('input'); n.className = 'bc-d-name'; n.maxLength = 60;") == []
    assert charter_caps("row.querySelector('.bc-d-name').maxLength = 60;") == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_cap_on_a_charter_whose_number_is_not_read_is_unread_never_absent():
    joined = "row.innerHTML = '<textarea class=\"bc-d-charter\" maxlength=\"' + window.LIMITS.charter + '\">';"
    assert charter_caps(joined) == [] and unresolved_caps(joined) == ["window.LIMITS.charter"], unresolved_caps(joined)
    odd = "row.innerHTML = '<textarea class=\"bc-d-charter\" maxlength=\"\">';"
    assert charter_caps(odd) == [] and unresolved_caps(odd), "an empty maxlength is not 'no cap'"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_short_cap_set_by_script_fails_beside_a_documented_one():
    made = ("const ta = document.createElement('textarea');\n"
            "ta.className = 'bc-d-charter'; ta.maxLength = 1500;")
    verdict, reason = _drive(made, OFFICE_CAPPED)
    assert verdict == "failed" and "1500" in reason, (verdict, reason)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_charter_field_with_no_cap_allows_the_documented_length():
    """The docstring's own rule: a field with no cap holds no number to disagree with. The likeliest
    fix (maxlength removed) passes; a page that draws no charter field at all is not a pass."""
    uncapped = "row.innerHTML = '<textarea class=\"bc-d-charter\" rows=\"3\"></textarea>';"
    verdict, reason = _drive(uncapped, OFFICE_PLAIN)
    assert verdict == "passed", (verdict, reason)
    verdict, reason = _drive("row.innerHTML = '<input class=\"bc-d-name\" maxlength=\"60\">';", OFFICE_PLAIN)
    assert verdict == "inconclusive", (verdict, reason)
    verdict, reason = _drive("row.innerHTML = '<textarea class=\"bc-d-charter\" rows=\"3\" maxlength=\"2000\">';",
                             OFFICE_PLAIN)
    assert verdict == "passed", (verdict, reason)

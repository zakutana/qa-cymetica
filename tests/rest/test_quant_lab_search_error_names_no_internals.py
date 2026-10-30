"""A failed Quant Lab search tells the owner why without handing them the database's internals (2026-10-30).

When a Quant Lab search fails, the owner's API carries the reason in the search's `error`
(`GET /api/v1/company/{id}/quant-lab/search` -> `search`, and every row of
`GET .../quant-lab/search/results` -> `searches`), and the Experiments page prints it as it comes:
quantsearch.js `line()` returns 'The last search stopped: ' + esc(s.error) + '. It tries again on
the next pass.'

**What was seen when this was written** (2026-10-30 13:57 UTC, our company 14, Pro): the three
failed searches #9, #7 and #5 each carry the same `error`, 400 characters, cut off mid-word:
"OperationalError: (psycopg2.OperationalError) server closed the connection unexpectedly\\n\\tThis
probably means the server terminated abnormally ... [SQL: SELECT company_quant_combos.combo_key AS
company_quant_combos_combo_key, company_quant_combos.data_fp AS company_quant_combos_data_fp \\nFROM
company_quant_combos \\nWHERE company_quant_combos.company_id = %(compan". That is the Python
exception, the database driver, a table and three of its columns, as the owner's page sentence.

**The rule.** No failed search in what the owner's API serves names an SQL statement (`[SQL:`,
`SELECT ... FROM`, `INSERT INTO`, `UPDATE ... SET`, `DELETE FROM`, upper case as an ORM writes
them), a database driver or ORM (psycopg, SQLAlchemy, asyncpg), an exception class at the start of
the text (`OperationalError:`), or a Python traceback. A null `error` passes (the page then says
"no reason recorded"), and so does any sentence written for a person, whatever it says. No failed
search in the list is nothing to judge.

NOT asserted: the failure itself (the sibling check, `test_quant_lab_daily_search_completes`), the
wording of a reason, whether the page shows one, or anything the owner's screen does with the
text. A fix that rewrites the error when it is stored, one that maps it when it is served, and one
that drops it all pass; a fix only in the page's script does not, because the API serves the same
text to the owner's agents.

SAFE: three GETs of our own company.
"""

from __future__ import annotations

import re

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude
from tests.rest.test_quant_lab_daily_search_completes import LIMIT, read_searches

CLAIM = "quant-lab-search-error-names-no-internals"

# Case-sensitive on purpose: an ORM writes SQL keywords in capitals, and "select a market from the
# list" is a sentence for a person.
_INTERNALS = (
    ("SQL statement", re.compile(r"\[SQL:|\bSELECT\b[\s\S]{0,600}?\bFROM\b|\bINSERT INTO\b"
                                 r"|\bUPDATE\s+\w+\s+SET\b|\bDELETE FROM\b")),
    ("database driver", re.compile(r"psycopg|sqlalchemy|asyncpg", re.I)),
    ("exception class", re.compile(r"^\s*[A-Z][A-Za-z0-9]*(?:Error|Exception)\s*:")),
    ("Python traceback", re.compile(r"Traceback \(most recent call last\)")),
)


def internals(text) -> list[str]:
    """What of the platform's internals an error text names, in a fixed order; [] for none."""
    if not isinstance(text, str) or not text.strip():
        return []
    return [name for name, pattern in _INTERNALS if pattern.search(text)]


@qa(component="rest.company", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_quant_lab_search_error_names_no_internals(rest_trusted):
    """Every failed search's `error` in our company's search status and history."""
    cid, _status, searches = read_searches(rest_trusted)
    failed = [s for s in searches if isinstance(s, dict) and s.get("status") == "failed"]
    if not failed:
        raise Inconclusive(f"no failed search in the {len(searches)} listed for company {cid}; "
                           f"no error to read")
    named = {s.get("id"): internals(s.get("error")) for s in failed}
    leaking = [s for s in failed if named[s.get("id")]]
    sample = (leaking[0].get("error") or "") if leaking else ""
    tables = sorted(set(re.findall(r"\bFROM\s+(\w+)", sample)))
    kinds = sorted({k for s in leaking for k in named[s.get("id")]},
                   key=[n for n, _ in _INTERNALS].index)
    conclude(Measurement(
        verdict="failed" if leaking else "passed",
        reason=(f"{len(leaking)} of {len(failed)} failed searches of company {cid} ("
                + ", ".join(f"#{s.get('id')}" for s in leaking)
                + ") answer the owner with an error naming " + ", ".join(("an " if k[0] in "aeiou" else "a ") + k for k in kinds)
                + (f" (table {', '.join(tables)})" if tables else "")
                + f", {len(sample)} characters, starting {sample[:90]!r}; the page prints it after "
                  f"'The last search stopped: '"
                if leaking else
                f"none of the {len(failed)} failed searches of company {cid} names an SQL statement, a "
                f"database driver, an exception class or a traceback in its error"),
        left={"failed_searches_naming_internals": len(leaking)},
        right={"allowed": 0, "failed_searches": len(failed)},
        population={"named": {f"#{k}": v for k, v in named.items()}, "error_sample": sample[:600]},
        sources={"status": f"/api/v1/company/{cid}/quant-lab/search (search.error)",
                 "history": f"/api/v1/company/{cid}/quant-lab/search/results?limit={LIMIT} (searches[].error)",
                 "page": "/static/company/quantsearch.js line(): 'The last search stopped: ' + esc(s.error)"},
        claim_id=CLAIM))

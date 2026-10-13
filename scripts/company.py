"""Our company on cymetica.com/company (Build a Company, feature #911), grown one department at a time.

    python scripts/company.py create --body-file F [--confirm]
    python scripts/company.py department --company ID --body-file F [--confirm]
    python scripts/company.py mine           their record of our company (a read)

[operator 2026-10-13] *"zkusime to zaloz oddeleni pro testing a rekni mu at loguje nalezene bugy
jako my at mame odmeny"*, then *"Ne ser na to proste to jen zaloz to je experiment to pak smazem
stejne"*. So: one company, the Testing department first, the others added when they say so.

Two writes, both declared in components.yaml with a closed body (`company.create`,
`company.department`); nothing else under /api/v1/company is ours to send: an approval is the
owner's act, and DELETE, pause and the message to the Manager stay default-denied. Without
--confirm a write prints the exact body and records nothing. A company worker (QA_CREW_DEPT) never
creates one: its outward writes stay denied by default.

Every write is two records in state/company.jsonl, ids CO-NNNN: the intent BEFORE the POST, the
outcome after (rule 9). `accepted` is a 2xx naming an id; a 2xx without one is `unknown`.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qa.client import build_client, install_client_guard  # noqa: E402
from qa.config import identities, load_dotenv  # noqa: E402
from qa.console import printable  # noqa: E402
from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier  # noqa: E402
from qa.state import file_lock, state_dir  # noqa: E402

BASE = "/api/v1/company"

# The body keys, and exactly the ones components.yaml declares (a test holds the two equal).
# `token_chain` is a company's token launch: not ours to choose.
CREATE_KEYS = ("name", "mission", "departments", "report_style")
DEPT_KEYS = ("key", "name", "charter", "experts")

# Their OpenAPI, read 2026-10-13: CompanyIn and DepartmentIn.
EXPERTS = ("qa_tester", "researcher", "trader", "developer", "lab_scientist", "auditor", "designer")
MAX_NAME, MIN_NAME = 120, 2
MIN_MISSION, MAX_MISSION = 10, 2000
MAX_CHARTER, MAX_DEPT_NAME, MAX_KEY, MAX_STYLE = 2000, 80, 40, 40
MIN_DEPARTMENTS, MAX_DEPARTMENTS = 1, 8
ID = re.compile(r"[A-Za-z0-9_-]{8,64}")

KEEP = ("id", "name", "status", "departments", "key", "detail", "message", "code")

# The transport under the guard: None is the real network; a test hands in a MockTransport.
INNER = None


class Refused(ValueError):
    """Refused before a body exists: nothing was sent and nothing recorded."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _text(value) -> str:
    return str(value or "").replace("\r\n", "\n").strip()


def company_id(raw) -> str:
    """A company id as their API writes it; anything else never reaches a URL."""
    if not isinstance(raw, str) or not ID.fullmatch(raw) or raw.isdigit():
        raise Refused(f"{raw!r} is not a company id")
    return raw


def department_body(*, key=None, name=None, charter=None, experts=None) -> dict:
    """A template ({"key": "testing"}, anything else overridable) or our own ({"name", "charter",
    "experts"}); `manager` is reserved. Their limits are refused here."""
    key, name, charter = _text(key) or None, _text(name) or None, _text(charter) or None
    if not key and not name:
        raise Refused("a department names itself: a template key or a name")
    if key and (len(key) > MAX_KEY or key == "manager"):
        raise Refused(f"key {key!r}: at most {MAX_KEY} characters, and 'manager' is reserved")
    if name and len(name) > MAX_DEPT_NAME:
        raise Refused(f"name is {len(name)} characters; their limit is {MAX_DEPT_NAME}")
    if charter and len(charter) > MAX_CHARTER:
        raise Refused(f"charter is {len(charter):,} characters; their limit is {MAX_CHARTER:,}")
    if not key and not charter:
        raise Refused("a department of our own needs a charter (its standing brief)")
    if experts is not None:
        experts = list(experts)
        bad = [e for e in experts if e not in EXPERTS]
        if bad or not experts:
            raise Refused(f"experts must be some of {', '.join(EXPERTS)}; got {experts!r}")
    body = {"key": key, "name": name, "charter": charter, "experts": experts}
    return {k: body[k] for k in DEPT_KEYS if body[k] is not None}


def create_body(*, name, mission, departments, report_style="brief") -> dict:
    name, mission, style = _text(name), _text(mission), _text(report_style)
    if not MIN_NAME <= len(name) <= MAX_NAME:
        raise Refused(f"name is {MIN_NAME} to {MAX_NAME} characters; this one is {len(name)}")
    if not MIN_MISSION <= len(mission) <= MAX_MISSION:
        raise Refused(f"mission is {MIN_MISSION} to {MAX_MISSION:,} characters; this one is "
                      f"{len(mission):,}")
    if not style or len(style) > MAX_STYLE:
        raise Refused(f"report_style is 1 to {MAX_STYLE} characters")
    depts = [department_body(**{k: d.get(k) for k in DEPT_KEYS}) for d in (departments or [])]
    if not MIN_DEPARTMENTS <= len(depts) <= MAX_DEPARTMENTS:
        raise Refused(f"{len(depts)} departments; they take {MIN_DEPARTMENTS} to {MAX_DEPARTMENTS}")
    keys = [d["key"] for d in depts if "key" in d]
    if len(keys) != len(set(keys)):
        raise Refused(f"department keys must be unique: {keys}")
    return {"name": name, "mission": mission, "departments": depts, "report_style": style}


def _read_json(path) -> dict:
    try:
        body = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise Refused(f"cannot read {path}: {exc}") from exc
    if not isinstance(body, dict):
        raise Refused(f"{path} is not a JSON object")
    return body


# -- records ------------------------------------------------------------------------------

def path() -> Path:
    return state_dir() / "company.jsonl"


def load() -> list[dict]:
    target = path()
    if not target.is_file():
        return []
    rows = []
    for line in target.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _append(record: dict) -> dict:
    """Under the lock, the id is taken in the step that writes it (league.py's rule)."""
    target = path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(target):
        if "id" not in record:
            used = [int(r["id"].split("-")[1]) for r in load()
                    if isinstance(r.get("id"), str) and r["id"].startswith("CO-")]
            record["id"] = f"CO-{max(used, default=0) + 1:04d}"
        with open(target, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def held(rows: list[dict]) -> str | None:
    """The company we hold: the id of the last create their server accepted."""
    made = [r.get("company_id") for r in rows
            if r.get("type") == "outcome" and r.get("kind") == "create"
            and r.get("outcome") == "accepted" and r.get("company_id")]
    return made[-1] if made else None


# -- the wire -----------------------------------------------------------------------------

def _client():
    load_dotenv()
    install_client_guard()
    registry = EndpointRegistry.load()
    registry.mutate_enabled = True
    registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    return build_client(identities()["trusted"], registry, timeout=60.0, inner=INNER)


def _json(response):
    try:
        return response.json()
    except ValueError:
        return None


def _capture(response) -> str | None:
    from qa.evidence import EvidenceStore

    try:
        return EvidenceStore("script-company").capture(
            response.request, response, SafetyTier.MUTATE) or None
    except Exception:  # noqa: BLE001
        return None


def _outcome_of(exc: BaseException) -> str:
    """`not_sent` only when the request cannot have left; a timeout or a cut stream may have
    landed, and that is `unknown` (bb.py's reading)."""
    import httpx

    never_left = (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout)
    if isinstance(exc, httpx.HTTPError) and not isinstance(exc, never_left):
        return "unknown"
    return "not_sent"


def _send(client, kind: str, url: str, body: dict) -> dict:
    """One write: the intent first, then the POST, then the outcome -- always an outcome."""
    intent = _append({"type": "intent", "kind": kind, "at": _now(), "url": url, "body": body})
    tier = CURRENT_TIER.set(SafetyTier.MUTATE)
    try:
        response = client.post(url, json=body)
    except Exception as exc:  # noqa: BLE001
        return _append({"id": intent["id"], "type": "outcome", "kind": kind, "at": _now(),
                        "outcome": _outcome_of(exc), "error": f"{type(exc).__name__}: {exc}"[:300]})
    finally:
        CURRENT_TIER.reset(tier)
    served = _json(response)
    said = served if isinstance(served, dict) else {}
    named = said.get("id") if 200 <= response.status_code < 300 else None
    named = str(named) if isinstance(named, (str, int)) and named != "" else None
    outcome = ("accepted" if named else "unknown") if 200 <= response.status_code < 300 else (
        "rejected" if 400 <= response.status_code < 500 else "unknown")
    return _append({"id": intent["id"], "type": "outcome", "kind": kind, "at": _now(),
                    "outcome": outcome, "http_status": response.status_code,
                    "company_id": named if kind == "create" else None,
                    "evidence_id": _capture(response),
                    "response": ({k: said[k] for k in KEEP if k in said} if served is not None
                                 and isinstance(served, dict) else (response.text or "")[:300])})


def _say(outcome: dict) -> None:
    said = outcome.get("response") if isinstance(outcome.get("response"), dict) else {}
    print(f"{outcome['id']}: {outcome['outcome']} (HTTP {outcome.get('http_status')}) "
          f"{outcome.get('company_id') or said.get('id') or ''}"
          + (f"\n  {json.dumps(said.get('detail'), ensure_ascii=False)[:300]}"
             if said.get("detail") is not None else "")
          + (f"\n  {outcome['error']}" if outcome.get("error") else ""))


# -- commands -----------------------------------------------------------------------------

def cmd_create(body_file, confirm: bool) -> int:
    raw = _read_json(body_file)
    body = create_body(**{k: raw.get(k) for k in CREATE_KEYS if k in raw})
    print(f"POST {BASE}/\n{json.dumps(body, ensure_ascii=False, indent=1)}")
    if not confirm:
        print("nothing sent: create needs --confirm")
        return 0
    if os.environ.get("QA_CREW_DEPT"):
        print("refused, nothing sent: a company worker never creates a company")
        return 2
    client = _client()
    try:
        outcome = _send(client, "create", f"{BASE}/", body)
    finally:
        client.close()
    _say(outcome)
    return 0 if outcome["outcome"] == "accepted" else 1


def cmd_department(raw_company, body_file, confirm: bool) -> int:
    cid = company_id(raw_company)
    raw = _read_json(body_file)
    body = department_body(**{k: raw.get(k) for k in DEPT_KEYS})
    url = f"{BASE}/{cid}/departments"
    print(f"POST {url}\n{json.dumps(body, ensure_ascii=False, indent=1)}")
    if not confirm:
        print("nothing sent: department needs --confirm")
        return 0
    if os.environ.get("QA_CREW_DEPT"):
        print("refused, nothing sent: a company worker never adds a department")
        return 2
    client = _client()
    try:
        outcome = _send(client, "department", url, body)
    finally:
        client.close()
    _say(outcome)
    return 0 if outcome["outcome"] == "accepted" else 1


def cmd_mine() -> int:
    load_dotenv()
    install_client_guard()
    client = build_client(identities()["trusted"], EndpointRegistry.load(), timeout=30.0, inner=INNER)
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        response = client.get(f"{BASE}/mine")
    finally:
        CURRENT_TIER.reset(token)
        client.close()
    print(f"GET {BASE}/mine -> HTTP {response.status_code}")
    served = _json(response)
    print(json.dumps(served, ensure_ascii=False, indent=1)[:3000] if served is not None
          else (response.text or "")[:300])
    return 0 if response.status_code == 200 else 1


def main(argv: list[str] | None = None) -> int:
    printable()
    parser = argparse.ArgumentParser(prog="company.py", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    make = sub.add_parser("create", help="create our company from a JSON body")
    make.add_argument("--body-file", required=True)
    make.add_argument("--confirm", action="store_true")
    dept = sub.add_parser("department", help="add one department to our company")
    dept.add_argument("--company", required=True)
    dept.add_argument("--body-file", required=True)
    dept.add_argument("--confirm", action="store_true")
    sub.add_parser("mine", help="their record of our company (a read)")
    args = parser.parse_args(argv)
    try:
        if args.command == "create":
            return cmd_create(args.body_file, args.confirm)
        if args.command == "department":
            return cmd_department(args.company, args.body_file, args.confirm)
        return cmd_mine()
    except Refused as exc:
        print(f"refused, nothing sent: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

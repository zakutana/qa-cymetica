"""File Cymetica Build it Better requests ourselves, and act on our own tickets.

    python scripts/bb.py file (--app-url URL | --app-name NAME) --improvements-file F
                              [--design-url URL]... [--confirm]
    python scripts/bb.py accept TICKET [--confirm]                       BB-ACCEPT, locks the scope
    python scripts/bb.py change TICKET --text-file F [--confirm]         BB-CHANGE
    python scripts/bb.py verdict TICKET pass|fail [--note-file F] [--confirm]   BB-VERDICT
    python scripts/bb.py withdraw TICKET [--confirm]                     BB-WITHDRAW
    python scripts/bb.py get TICKET     their record of one request (a read)
    python scripts/bb.py mine           our requests, from state/bb.jsonl

[operator 2026-10-11] "Ja nic podavat kebudu ty muzes sam klidne build it better podavat i ty
featury": the laboratory's desk files its own requests. Without --confirm a write prints the
exact body it would send and records nothing; nothing leaves.

Five writes, each declared in components.yaml under rest.build_it_better with a closed body
(`build_it_better.file|accept|change|verdict|withdraw`), so the transport refuses an extra key
and every other path under /build-it-better. Their limits are refused here, before a body
exists: improvements up to 8,000 characters and 40 lines (llms.txt: "at most 40 items in the
spec; more are folded into the last one"), a change 8 to 4,000 (the MCP tool's range), a fail
note up to 4,000, and a fail that does not say why is not sent.

THE REQUEST TOKEN. The 201 that files a request carries `request_token`, once. Their OpenAPI,
read 2026-10-11, makes it the X-BB-Token HEADER of accept, change and verdict: accept has no
body, BBChangeIn is {changes}, BBVerdictIn is {verdict, note}. llms.txt says "(request token in
the body)", which is the MCP tools' shape, not REST's. Withdraw is in llms.txt and the MCP tool
list only, so it is sent in accept's shape. The account that filed a request may act without
the token (`yours`), and we file with our X-API-Key, so the token is a second key, not the only
one. It is kept in state/bb_tokens.json (ticket -> token, gitignored) and nowhere else: taken
out of the response before the outcome row is written, replaced in the captured evidence, and
X-BB-Token is a secret header to the evidence redactor.

Every write is two records in state/bb.jsonl (rule 9), ids BB-NNNN: the intent BEFORE the POST,
the outcome after. `accepted` is a 2xx naming a ticket (for a filing, a 201 with `created:
true`); `joined` a 2xx naming an existing ticket that filed nothing; `refused` their 409
OPEN_REQUEST_EXISTS -- one open request per app -- with their `open_ticket`, nothing filed;
`rejected` any other 4xx; `unknown` a call that may have landed; `not_sent` one that never left.
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
from qa.crew import crew_brake  # noqa: E402
from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier  # noqa: E402
from qa.state import file_lock, state_dir  # noqa: E402

BASE = "/api/v1/build-it-better/requests"
AGENT = "qa-cymetica desk"

# The body keys a filing may carry, and exactly the ones components.yaml declares for
# `build_it_better.file` (a test holds the two equal). BBRequestIn's other four are refused:
# `email` and `name` are personal data the API key makes unnecessary, `symbol` and `coin_name`
# choose a coin for the build, which is not ours to choose.
FILE_KEYS = ("app_url", "app_name", "improvements", "agent", "design_urls")

MAX_IMPROVEMENTS = 8000
MAX_LINES = 40
MIN_CHANGE, MAX_CHANGE = 8, 4000
MAX_NOTE = 4000
MAX_DESIGNS = 6           # the form's "Up to 6 pictures"
VERDICTS = ("pass", "fail")
TICKET = re.compile(r"ET-\d+")

# What an outcome row keeps of their answer. Not the spec or the message log (the record is
# public and `get` reads it), and never `request_token`.
KEEP = ("ticket", "app_name", "app_url", "is_idea", "created", "yours", "stage", "spec_status",
        "ready_to_build", "verdict", "verdict_repeated", "deadline_at", "our_url", "message",
        "code", "open_ticket", "detail")

# The transport under the guard: None is the real network. A test hands in an
# httpx.MockTransport -- build_client's `inner`, which exists for exactly that.
INNER = None


class Refused(ValueError):
    """Refused before a body exists: nothing was sent and nothing recorded."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# -- bodies, each refused before it exists if it breaks their limits ------------------------

def ticket(raw) -> str:
    """A ticket as their board writes it, ET-nnnnn; anything else never reaches a URL."""
    if not isinstance(raw, str) or not TICKET.fullmatch(raw):
        raise Refused(f"{raw!r} is not a ticket (ET-nnnnn)")
    return raw


def _text(value) -> str:
    return str(value or "").replace("\r\n", "\n").strip()


def _url(value: str, what: str) -> str:
    value = _text(value)
    if not value.startswith(("https://", "http://")):
        raise Refused(f"{what} must be an http(s) URL, got {value[:80]!r}")
    return value


def file_body(*, app_url=None, app_name=None, improvements, design_urls=()) -> dict:
    """The BB-REQUEST: an app that exists (its link) or an idea (its name), and the list."""
    app_url = _url(app_url, "--app-url") if _text(app_url) else None
    app_name = _text(app_name) or None
    if not app_url and not app_name:
        raise Refused("a request names its app: --app-url (it exists) or --app-name (an idea)")
    text = _text(improvements)
    if not text:
        raise Refused("improvements is empty: a request with no list files nothing new")
    if len(text) > MAX_IMPROVEMENTS:
        raise Refused(f"improvements is {len(text):,} characters; their limit is "
                      f"{MAX_IMPROVEMENTS:,}")
    lines = [line for line in text.split("\n") if line.strip()]
    if len(lines) > MAX_LINES:
        raise Refused(f"improvements is {len(lines)} lines; the spec holds {MAX_LINES} items "
                      f"and folds the rest into the last one")
    designs = [_url(u, "--design-url") for u in (design_urls or [])]
    if len(designs) > MAX_DESIGNS:
        raise Refused(f"{len(designs)} design URLs; the form takes {MAX_DESIGNS}")
    body = {"app_url": app_url, "app_name": app_name, "improvements": text, "agent": AGENT,
            "design_urls": designs or None}
    return {key: body[key] for key in FILE_KEYS if body[key] is not None}


def change_body(text) -> dict:
    changes = _text(text)
    if not MIN_CHANGE <= len(changes) <= MAX_CHANGE:
        raise Refused(f"a BB-CHANGE is {MIN_CHANGE} to {MAX_CHANGE:,} characters; this one is "
                      f"{len(changes):,}")
    return {"changes": changes}


def verdict_body(verdict, note) -> dict:
    if verdict not in VERDICTS:
        raise Refused(f"a verdict is pass or fail, not {verdict!r}")
    note = _text(note)
    if verdict == "fail" and not note:
        raise Refused("a fail says what is still not better: --note-file")
    if len(note) > MAX_NOTE:
        raise Refused(f"the note is {len(note):,} characters; their limit is {MAX_NOTE:,}")
    return {"verdict": verdict, **({"note": note} if note else {})}


def _read(path) -> str:
    try:
        return Path(path).read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise Refused(f"cannot read {path}: {exc}") from exc


# -- records ------------------------------------------------------------------------------

def path() -> Path:
    return state_dir() / "bb.jsonl"


def tokens_path() -> Path:
    return state_dir() / "bb_tokens.json"


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
                    if isinstance(r.get("id"), str) and r["id"].startswith("BB-")]
            record["id"] = f"BB-{max(used, default=0) + 1:04d}"
        with open(target, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def tokens() -> dict:
    try:
        held = json.loads(tokens_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return held if isinstance(held, dict) else {}


def _keep_token(ticket_id: str, token: str) -> None:
    """Shown once and never again: written before the outcome row, tmp then replace."""
    target = tokens_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(target):
        held = tokens()
        held[ticket_id] = token
        tmp = target.with_name(target.name + ".tmp")
        tmp.write_text(json.dumps(held, indent=1, sort_keys=True), encoding="utf-8")
        os.replace(tmp, target)


def mine(rows: list[dict]) -> list[dict]:
    """Our filings, oldest first, each with what we did on its ticket after."""
    intents = {r.get("id"): r for r in rows if r.get("type") == "intent"}
    held = tokens()
    out = []
    for row in rows:
        if row.get("type") != "outcome" or row.get("kind") != "file":
            continue
        body = (intents.get(row.get("id")) or {}).get("body") or {}
        done = row.get("ticket")
        out.append({"id": row.get("id"), "at": row.get("at"), "ticket": done,
                    "app": body.get("app_name") or body.get("app_url"),
                    "outcome": row.get("outcome"), "open_ticket": row.get("open_ticket"),
                    "token_held": bool(done and done in held),
                    "after": [f"{r.get('kind')} {r.get('outcome')}" for r in rows
                              if done and r.get("type") == "outcome" and r.get("kind") != "file"
                              and r.get("ticket") == done]})
    return out


# -- the wire -----------------------------------------------------------------------------

def _client(write: bool = False):
    load_dotenv()
    install_client_guard()
    registry = EndpointRegistry.load()
    if write:
        registry.mutate_enabled = True
        registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    return build_client(identities()["trusted"], registry, timeout=60.0, inner=INNER)


def _json(response):
    try:
        return response.json()
    except ValueError:
        return None


def _field(said: dict, key: str):
    """Their 409 names its fields at the top level; read under `detail` too, where a
    framework's HTTPException puts a dict."""
    if key in said:
        return said[key]
    detail = said.get("detail")
    return detail.get(key) if isinstance(detail, dict) else None


def _outcome_of(exc: BaseException) -> str:
    """`not_sent` only when the request cannot have left (a refusal by our own guard is one);
    a timeout or a cut stream may have landed, and that is `unknown` (league.py's reading)."""
    import httpx

    never_left = (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout)
    if isinstance(exc, httpx.HTTPError) and not isinstance(exc, never_left):
        return "unknown"
    return "not_sent"


def outcome_of(kind: str, status: int, served) -> str:
    said = served if isinstance(served, dict) else {}
    named = isinstance(said.get("ticket"), str) and TICKET.fullmatch(said["ticket"])
    if 200 <= status < 300:
        if not named:
            return "unknown"
        if kind != "file":
            return "accepted"
        return {True: "accepted", False: "joined"}.get(said.get("created"), "unknown")
    if status == 409 and _field(said, "code") == "OPEN_REQUEST_EXISTS":
        return "refused"
    if 400 <= status < 500:
        return "rejected"
    return "unknown"


def _scrub(value, secret: str | None):
    """A copy of `value` with the token's text replaced wherever it appears."""
    if not secret:
        return value
    from qa.evidence import REDACTED

    return json.loads(json.dumps(value, ensure_ascii=False).replace(secret, REDACTED))


def _capture(response, secret: str | None) -> str | None:
    """The exchange, kept like league.py's -- with the token's text replaced in their answer.
    The X-BB-Token we SENT is a secret header to the redactor, so the request is safe as is."""
    import httpx

    from qa.evidence import REDACTED, EvidenceStore

    try:
        if secret:
            content = response.content.replace(secret.encode("utf-8"), REDACTED.encode("utf-8"))
            headers = [(k, v) for k, v in response.headers.multi_items()
                       if k.lower() not in ("content-length", "content-encoding", "transfer-encoding")]
            response = httpx.Response(response.status_code, headers=headers, content=content,
                                      request=response.request)
        return EvidenceStore("script-bb").capture(
            response.request, response, SafetyTier.MUTATE) or None
    except Exception:  # noqa: BLE001
        return None


def _send(client, kind: str, url: str, body: dict | None, ticket_id: str | None = None,
          token: str | None = None) -> tuple[dict, str | None]:
    """One write: the intent first, then the POST, then the outcome -- always an outcome.
    Returns the outcome row and the spec text their answer carried, if any."""
    intent = _append({"type": "intent", "kind": kind, "at": _now(), "url": url, "body": body,
                      "ticket": ticket_id, "token_sent": bool(token)})
    tier = CURRENT_TIER.set(SafetyTier.MUTATE)
    try:
        response = client.post(url, json=body, headers={"X-BB-Token": token} if token else None)
    except Exception as exc:  # noqa: BLE001
        return _append({"id": intent["id"], "type": "outcome", "kind": kind, "at": _now(),
                        "ticket": ticket_id, "outcome": _outcome_of(exc),
                        "error": f"{type(exc).__name__}: {exc}"[:300],
                        "token_held": bool(ticket_id and ticket_id in tokens())}), None
    finally:
        CURRENT_TIER.reset(tier)
    served = _json(response)
    said = dict(served) if isinstance(served, dict) else {}
    secret = said.pop("request_token", None)
    secret = secret if isinstance(secret, str) and secret else None
    outcome = outcome_of(kind, response.status_code, served)
    named = said.get("ticket")
    named = named if (200 <= response.status_code < 300 and isinstance(named, str)
                      and TICKET.fullmatch(named)) else None
    # Kept whatever the outcome is called: shown once, it cannot be asked for again, and a 2xx
    # that does not say whether it filed (`unknown`) may still have.
    if kind == "file" and secret and named:
        _keep_token(named, secret)
    done = ticket_id or named
    record = {"id": intent["id"], "type": "outcome", "kind": kind, "at": _now(),
              "ticket": done, "outcome": outcome, "http_status": response.status_code,
              "evidence_id": _capture(response, secret),
              "token_held": bool(done and done in tokens()),
              "response": ({k: (said[k][:500] if isinstance(said[k], str) else said[k])
                            for k in KEEP if k in said} if isinstance(served, dict)
                           else (response.text or "")[:300])}
    if outcome == "refused":
        record["open_ticket"] = _field(said, "open_ticket")
    return _append(_scrub(record, secret)), (said.get("spec_text") if outcome != "refused" else None)


def _say(outcome: dict) -> None:
    said = outcome.get("response") if isinstance(outcome.get("response"), dict) else {}
    extra = (f", their open ticket {outcome['open_ticket']}: add scope there with a BB-CHANGE"
             if outcome.get("outcome") == "refused" else "")
    print(f"{outcome['id']}: {outcome['outcome']} (HTTP {outcome.get('http_status')}) "
          f"ticket {outcome.get('ticket')}, stage {said.get('stage')}, spec {said.get('spec_status')}"
          f"{', token kept in state/bb_tokens.json' if outcome.get('token_held') else ''}{extra}"
          + (f"\n  {outcome['error']}" if outcome.get("error") else "")
          + (f"\n  {json.dumps(said.get('detail'), ensure_ascii=False)[:300]}"
             if said.get("detail") is not None else ""))


# -- commands -----------------------------------------------------------------------------

def cmd_file(app_url, app_name, improvements_file, design_urls, confirm: bool) -> int:
    body = file_body(app_url=app_url, app_name=app_name, improvements=_read(improvements_file),
                     design_urls=design_urls)
    lines = [line for line in body["improvements"].split("\n") if line.strip()]
    print(f"POST {BASE}\n{json.dumps(body, ensure_ascii=False, indent=1)}")
    print(f"improvements: {len(body['improvements']):,} of {MAX_IMPROVEMENTS:,} characters, "
          f"{len(lines)} of {MAX_LINES} lines")
    if not confirm:
        print("nothing sent: file needs --confirm")
        return 0
    # The company's brake (docs/crew-plan.md): its workers file at most two a day. Not
    # applied to a session -- the operator's own filings are theirs.
    braked = crew_brake("bb", load())
    if braked:
        print(f"refused, nothing sent: {braked}")
        return 2
    client = _client(write=True)
    try:
        outcome, spec = _send(client, "file", BASE, body)
    finally:
        client.close()
    _say(outcome)
    if spec:
        print(f"\nBB-SPEC:\n{spec}")
    return 0 if outcome["outcome"] == "accepted" else 1


def ours(ticket_id: str, rows: list[dict]) -> bool:
    """A ticket this repository filed itself (`mine`)."""
    return any(row.get("ticket") == ticket_id for row in mine(rows))


def cmd_act(kind: str, raw_ticket: str, body: dict | None, confirm: bool) -> int:
    """accept, change, verdict, withdraw: our own ticket, the token as X-BB-Token if held."""
    ticket_id = ticket(raw_ticket)
    # The company's grant was to FILE (the laborator skill, 2026-10-11): a worker acts only on
    # a ticket the company filed itself. A verdict on the operator's own ticket -- ET-30773 --
    # is his (crew-before-c9, item 3). A session is the operator's and is not refused here.
    if os.environ.get("QA_CREW_DEPT") and not ours(ticket_id, load()):
        print(f"refused, nothing sent: {ticket_id} was not filed by the company; "
              f"its {kind} is the operator's")
        return 2
    url = f"{BASE}/{ticket_id}/{kind}"
    token = tokens().get(ticket_id)
    print(f"POST {url}\nbody: "
          + (json.dumps(body, ensure_ascii=False, indent=1) if body is not None else "(none)"))
    print("X-BB-Token: " + ("held, from state/bb_tokens.json" if token else
                            "none held -- the account that filed it acts with its X-API-Key"))
    if not confirm:
        print(f"nothing sent: {kind} needs --confirm")
        return 0
    client = _client(write=True)
    try:
        outcome, spec = _send(client, kind, url, body, ticket_id=ticket_id, token=token)
    finally:
        client.close()
    _say(outcome)
    if spec and kind == "change":
        print(f"\nBB-SPEC:\n{spec}")
    return 0 if outcome["outcome"] == "accepted" else 1


def cmd_get(raw_ticket: str) -> int:
    ticket_id = ticket(raw_ticket)
    client = _client()
    tier = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        response = client.get(f"{BASE}/{ticket_id}")
    finally:
        CURRENT_TIER.reset(tier)
        client.close()
    record = _json(response)
    if response.status_code != 200 or not isinstance(record, dict):
        print(f"{BASE}/{ticket_id} answered HTTP {response.status_code}: a failed read is not "
              f"an empty one")
        return 1
    print(" | ".join(f"{key} {record.get(key)}" for key in (
        "ticket", "app_name", "is_idea", "stage", "spec_status", "ready_to_build", "verdict",
        "deadline_at", "our_url", "yours")))
    messages = [m for m in record.get("messages") or [] if isinstance(m, dict)]
    print(f"{len(messages)} message(s): " + ", ".join(
        f"{m.get('kind')} {str(m.get('at'))[:16]}" for m in messages[-8:]))
    return 0


def cmd_mine() -> int:
    rows = mine(load())
    if not rows:
        print("no Build it Better request filed from here yet")
    for row in rows:
        print(f"{row['id']}  {row['ticket'] or '-':<9} {row['outcome']:<9} {str(row['at'])[:16]}  "
              f"{row['app']}"
              + (f"  (their open ticket {row['open_ticket']})" if row["open_ticket"] else "")
              + ("  token held" if row["token_held"] else "")
              + (f"  | {', '.join(row['after'])}" if row["after"] else ""))
    return 0


def main(argv: list[str] | None = None) -> int:
    printable()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    filing = sub.add_parser("file")
    filing.add_argument("--app-url")
    filing.add_argument("--app-name")
    filing.add_argument("--improvements-file", required=True)
    filing.add_argument("--design-url", action="append", default=[])
    filing.add_argument("--confirm", action="store_true")
    for kind in ("accept", "withdraw"):
        act = sub.add_parser(kind)
        act.add_argument("ticket")
        act.add_argument("--confirm", action="store_true")
    change = sub.add_parser("change")
    change.add_argument("ticket")
    change.add_argument("--text-file", required=True)
    change.add_argument("--confirm", action="store_true")
    verdict = sub.add_parser("verdict")
    verdict.add_argument("ticket")
    verdict.add_argument("verdict")
    verdict.add_argument("--note-file")
    verdict.add_argument("--confirm", action="store_true")
    get = sub.add_parser("get")
    get.add_argument("ticket")
    sub.add_parser("mine")
    args = parser.parse_args(argv)
    try:
        if args.cmd == "file":
            return cmd_file(args.app_url, args.app_name, args.improvements_file, args.design_url,
                            args.confirm)
        if args.cmd in ("accept", "withdraw"):
            return cmd_act(args.cmd, args.ticket, None, args.confirm)
        if args.cmd == "change":
            return cmd_act("change", args.ticket, change_body(_read(args.text_file)), args.confirm)
        if args.cmd == "verdict":
            note = _read(args.note_file) if args.note_file else None
            return cmd_act("verdict", args.ticket, verdict_body(args.verdict, note), args.confirm)
        if args.cmd == "get":
            return cmd_get(args.ticket)
        return cmd_mine()
    except Refused as exc:
        print(f"refused, nothing sent: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())

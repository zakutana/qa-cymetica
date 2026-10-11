"""Head-to-head paper matchups (cymetica.com/h2h), read and started.

    python scripts/h2h.py sides
    python scripts/h2h.py mine
    python scripts/h2h.py create --original clone:<id> --improved clone:<id> --days 7 --title "A vs B" --confirm

Two paper sides -- a paper clone, or the account's own paper trading -- over
the same window; their scoreboard gives a verdict once each side has closed
three trades. `create` sends `is_public: false` always: the default publishes
a share card at cymetica.com/h2h/{slug}, and a publication is the operator's.

`create` is a write: the rule in components.yaml keeps its body to the
documented fields, MUTATE is turned on for their host here and nowhere else,
and `--confirm` is checked before the network.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

KINDS = ("clone", "account")
ROUTE = "/api/v1/head-to-head"


class H2HError(RuntimeError):
    """A matchup refused, by us before the network or by them -- or, with a 5xx `status`, an
    answer that does not say whether it was created."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


def error_outcome(exc: H2HError) -> str:
    """Rule 9: their 4xx, or our own refusal before the network, is `refused`; a 5xx may have
    created the matchup, and that is `unknown` (deep pass 2026-10-11, R02)."""
    return "unknown" if isinstance(exc.status, int) and exc.status >= 500 else "refused"


def side(text: str) -> dict:
    """`clone:<instance id>` or `account` / `account:<anything>`."""
    kind, _, ref = str(text or "").partition(":")
    if kind not in KINDS or ":" in ref or (kind == "clone" and not ref):
        raise H2HError(f"a side is clone:<instance id> or account, not {text!r}")
    return {"kind": kind, "ref": ref or None} if kind == "clone" else {"kind": kind}


def create(client, original: str, improved: str, days: int = 7,
           title: str | None = None, confirm: bool = False) -> dict:
    left, right = side(original), side(improved)
    if left == right:
        raise H2HError("a side cannot be matched against itself")
    if not 1 <= int(days) <= 90:
        raise H2HError(f"days is 1 to 90 (CreateMatchup), not {days}")
    if not confirm:
        raise H2HError("pass confirm=True to actually start the matchup")
    body = {"original": left, "improved": right, "days": int(days)}
    if title:
        body["title"] = str(title)[:140]
    body["is_public"] = False
    response = client.post(ROUTE, json=body)
    if response.status_code not in (200, 201):
        raise H2HError(f"matchup refused: HTTP {response.status_code} "
                       f"{response.text[:300]!r}", status=response.status_code)
    return response.json() or {}


def diary() -> Path:
    from qa.state import state_dir

    return state_dir() / "h2h.jsonl"


def load() -> list[dict]:
    """Every matchup row we wrote: intent before the POST, outcome after (CLAUDE.md, rule 9),
    and the results read back from /head-to-head/mine."""
    target = diary()
    if not target.is_file():
        return []
    return [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def _append(row: dict) -> dict:
    target = diary()
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def start_matchup(original: str, improved: str, days: int, title: str, room: str) -> dict:
    """Laboratory v3, P7: one matchup for a head-to-head room, its slug kept. An intent row
    first, then the POST (never public), then the outcome with the slug -- `accepted` only on
    a 2xx that names one."""
    from datetime import datetime, timezone

    from qa.safety import CURRENT_TIER, SafetyTier

    used = [int(str(r.get("id", "H2H-0"))[4:] or 0) for r in load()
            if str(r.get("id", "")).startswith("H2H-")]
    ident = f"H2H-{max(used, default=0) + 1:04d}"
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _append({"id": ident, "type": "intent", "at": now, "room": room,
             "original": original, "improved": improved, "days": int(days), "title": title})
    client = _client(mutate=True)
    token = CURRENT_TIER.set(SafetyTier.MUTATE)
    try:
        said = create(client, original, improved, days, title, confirm=True)
        outcome = {"outcome": "accepted" if said.get("slug") else "unknown",
                   "slug": said.get("slug"), "status": said.get("status")}
    except H2HError as exc:
        outcome = {"outcome": error_outcome(exc), "error": str(exc)[:300]}
    except Exception as exc:  # noqa: BLE001 -- sent or not, unknown
        outcome = {"outcome": "unknown", "error": f"{type(exc).__name__}: {exc}"[:300]}
    finally:
        CURRENT_TIER.reset(token)
        client.close()
    return _append({"id": ident, "type": "outcome", "at": now, "room": room, **outcome})


def results() -> list[dict]:
    """Our matchups as their side reports them (GET /head-to-head/mine), SAFE."""
    from qa.safety import CURRENT_TIER, SafetyTier

    client = _client(mutate=False)
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        response = client.get(f"{ROUTE}/mine")
    finally:
        CURRENT_TIER.reset(token)
        client.close()
    if response.status_code != 200:
        raise H2HError(f"/mine unread, HTTP {response.status_code}")
    body = response.json()
    rows = body.get("matchups") if isinstance(body, dict) else body
    return [r for r in rows or [] if isinstance(r, dict)]


def _client(mutate: bool):
    from qa.client import build_client
    from qa.config import identities, load_dotenv
    from qa.safety import EndpointRegistry

    load_dotenv()
    registry = EndpointRegistry.load()
    if mutate:
        registry.mutate_enabled = True
        registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    return build_client(identities()["trusted"], registry, timeout=40.0)


def main(argv: list[str] | None = None) -> int:
    from qa.safety import CURRENT_TIER, SafetyTier

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("sides", help="the sides this account can match")
    sub.add_parser("mine", help="our matchups and their scoreboards")
    one = sub.add_parser("create", help="start one matchup (never public)")
    one.add_argument("--original", required=True)
    one.add_argument("--improved", required=True)
    one.add_argument("--days", type=int, default=7)
    one.add_argument("--title")
    one.add_argument("--confirm", action="store_true")
    args = parser.parse_args(argv)

    if args.cmd == "create":
        client = _client(mutate=True)
        token = CURRENT_TIER.set(SafetyTier.MUTATE)
        try:
            said = create(client, args.original, args.improved, args.days,
                          args.title, args.confirm)
        except H2HError as exc:
            print(f"h2h: {exc}")
            return 1
        finally:
            CURRENT_TIER.reset(token)
            client.close()
        print(f"{said.get('slug')} {said.get('status')} public={said.get('is_public')} "
              f"{said.get('page_url') or ''}")
        return 0

    client = _client(mutate=False)
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        response = client.get(f"{ROUTE}/{args.cmd}")
    finally:
        CURRENT_TIER.reset(token)
        client.close()
    if response.status_code != 200:
        print(f"h2h: {args.cmd} unread, HTTP {response.status_code}")
        return 1
    print(json.dumps(response.json(), indent=1, ensure_ascii=False)[:6000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

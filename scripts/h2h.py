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
    """A matchup refused, by us before the network or by them."""


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
                       f"{response.text[:300]!r}")
    return response.json() or {}


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

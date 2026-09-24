"""The creator dashboard (cymetica.com/tg_expire76), read and claimed.

    python scripts/creator.py leads [--outlet twitter|reddit] [--tool /x] [--limit N]
    python scripts/creator.py claim --outlet twitter --lead 3 --page p497i3fy --confirm

`leads` reads the reply queue (SAFE). `claim` is what the dashboard's "Reply
with this page" button does: it claims the lead and mints a tracked link for
that one reply (cymetica.com/c/<reply_slug>), so clicks are counted per
thread. It posts nothing to X or Reddit -- the operator posts by hand.

`claim` is a write: the rule in components.yaml keeps its body to
`link_slug`, MUTATE is turned on for their host here and nowhere else, and
`--confirm` is checked before the network.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

OUTLETS = ("twitter", "reddit")
BASE = "https://cymetica.com"


class CreatorError(RuntimeError):
    """A claim that was refused, by us before the network or by them."""


def tracked_url(slug: str) -> str:
    return f"{BASE}/c/{slug}"


def claim(client, outlet: str, lead_id: int, page_slug: str = "",
          confirm: bool = False) -> dict:
    """Claim one lead and return their record of it, `reply_slug` and
    `suggested_reply` included. Refuses an unknown outlet and a missing
    `confirm` before anything reaches the network."""
    if outlet not in OUTLETS:
        raise CreatorError(f"unknown outlet {outlet!r} -- one of {OUTLETS}")
    if not confirm:
        raise CreatorError("pass confirm=True to actually claim the lead")
    response = client.post(f"/api/v1/creator/{outlet}-leads/{int(lead_id)}/reply",
                           json={"link_slug": page_slug or ""})
    if response.status_code != 200:
        raise CreatorError(
            f"claim refused: HTTP {response.status_code} {response.text[:200]!r}")
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


def cmd_leads(args) -> int:
    from qa.safety import CURRENT_TIER, SafetyTier

    client = _client(mutate=False)
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        params = {"limit": args.limit}
        if args.tool:
            params["tool"] = args.tool
        response = client.get(f"/api/v1/creator/{args.outlet}-leads", params=params)
    finally:
        CURRENT_TIER.reset(token)
        client.close()
    if response.status_code != 200:
        print(f"creator: leads unread, HTTP {response.status_code}")
        return 1
    for lead in response.json().get("leads") or []:
        print(f"{lead.get('id')} | {lead.get('status')} | r{lead.get('relevance')} | "
              f"{lead.get('author')} {lead.get('author_followers') or ''} | "
              f"{lead.get('tool_path')} | {(lead.get('body') or '')[:120]!r}")
    return 0


def cmd_claim(args) -> int:
    from qa.safety import CURRENT_TIER, SafetyTier

    client = _client(mutate=True)
    token = CURRENT_TIER.set(SafetyTier.MUTATE)
    try:
        said = claim(client, args.outlet, args.lead, args.page, args.confirm)
    except CreatorError as exc:
        print(f"creator: {exc}")
        return 1
    finally:
        CURRENT_TIER.reset(token)
        client.close()
    slug = said.get("reply_slug")
    print(f"lead {said.get('id')} {said.get('status')}  {said.get('permalink')}")
    print(f"tracked link: {tracked_url(slug) if slug else '(none returned)'}")
    print(f"suggested reply: {said.get('suggested_reply')}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    leads = sub.add_parser("leads", help="read the reply queue")
    leads.add_argument("--outlet", choices=OUTLETS, default="twitter")
    leads.add_argument("--tool", default="")
    leads.add_argument("--limit", type=int, default=50)
    one = sub.add_parser("claim", help="claim a lead; mints its tracked link")
    one.add_argument("--outlet", choices=OUTLETS, default="twitter")
    one.add_argument("--lead", type=int, required=True)
    one.add_argument("--page", default="", help="artifact page slug to reply with")
    one.add_argument("--confirm", action="store_true")
    args = parser.parse_args(argv)
    return cmd_leads(args) if args.cmd == "leads" else cmd_claim(args)


if __name__ == "__main__":
    raise SystemExit(main())

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
import re
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
    import httpx

    try:
        response = client.post(
            f"/api/v1/creator/{outlet}-leads/{int(lead_id)}/reply",
            json={"link_slug": page_slug or ""})
    except httpx.TimeoutException:
        return _settle(client, outlet, lead_id, "timed out")
    if response.status_code >= 500:
        return _settle(client, outlet, lead_id, f"HTTP {response.status_code}")
    if response.status_code != 200:
        raise CreatorError(
            f"claim refused: HTTP {response.status_code} {response.text[:200]!r}")
    return response.json() or {}


# One post, and only the post: X's copy-link adds ?s=..&t=.. (dropped before
# sending), and a reddit link must end in a comment id -- a thread URL is not
# our reply (deep pass 2026-09-24, R04 and G01).
REPLY_URL = {"twitter": re.compile(r"^(https://(?:x|twitter)\.com/[A-Za-z0-9_]{1,15}/status/\d+)/?(?:\?.*)?$"),
             "reddit": re.compile(r"^(https://(?:www\.|old\.)?reddit\.com/r/\w+/comments/\w+/[^/?]+/\w+/?)(?:\?.*)?$")}


def posted(client, outlet: str, lead_id: int, reply_url: str,
           confirm: bool = False) -> dict:
    """Mark a claimed lead posted with the link to the reply the operator
    posted -- what the dashboard's "Mark posted" does, and the only way a
    reward is credited (their checker confirms the reply is displayed).
    Refuses an unknown outlet, a URL that is not one post on that outlet,
    and a missing `confirm`, all before the network."""
    if outlet not in OUTLETS:
        raise CreatorError(f"unknown outlet {outlet!r} -- one of {OUTLETS}")
    one = REPLY_URL[outlet].match(reply_url or "")
    if not one:
        raise CreatorError(f"reply_url {reply_url!r} is not a link to one "
                           f"{outlet} post")
    if not confirm:
        raise CreatorError("pass confirm=True to actually mark the lead posted")
    response = client.post(f"/api/v1/creator/{outlet}-leads/{int(lead_id)}/posted",
                           json={"reply_url": one.group(1)})
    if response.status_code != 200:
        raise CreatorError(
            f"posted refused: HTTP {response.status_code} {response.text[:200]!r}")
    return response.json() or {}


def _settle(client, outlet: str, lead_id: int, why: str) -> dict:
    """A 5xx or a timeout is outcome-unknown, not a refusal: their 503 has
    answered claims that committed (ET-27021). Read the claimed leads back
    and report what is there; never retry blind."""
    response = client.get(f"/api/v1/creator/{outlet}-leads",
                          params={"status": "claimed,replied", "limit": 200})
    if response.status_code != 200:
        raise CreatorError(f"claim {why}, and the read-back failed too "
                           f"(HTTP {response.status_code}) -- outcome unknown")
    for lead in response.json().get("leads") or []:
        if lead.get("id") == int(lead_id):
            return {**lead, "settled_by_read": True}
    raise CreatorError(f"claim {why}; read back: lead {lead_id} is not claimed")


def identity():
    """The key minted on tg_expire76, the account the queues belong to. No
    fallback to `trusted`: that is account expire76, whose claims would be
    credited to the wrong dashboard (REPLY-0058)."""
    from qa.config import identities

    creator = identities()["creator"]
    if not creator.value:
        raise CreatorError("no QA_CREATOR_KEY in .env -- mint one in the "
                           "dashboard's 'Your agent's API key' panel")
    return creator


def _client(mutate: bool):
    from qa.client import build_client
    from qa.safety import EndpointRegistry

    registry = EndpointRegistry.load()
    if mutate:
        registry.mutate_enabled = True
        registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    return build_client(identity(), registry, timeout=40.0)


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
    if said.get("settled_by_read"):
        print("(their answer was a 5xx or a timeout; this is the read-back)")
    print(f"lead {said.get('id')} {said.get('status')}  {said.get('permalink')}")
    print(f"tracked link: {tracked_url(slug) if slug else '(none returned)'}")
    print(f"suggested reply: {said.get('suggested_reply')}")
    return 0


def cmd_posted(args) -> int:
    from qa.safety import CURRENT_TIER, SafetyTier

    client = _client(mutate=True)
    token = CURRENT_TIER.set(SafetyTier.MUTATE)
    try:
        said = posted(client, args.outlet, args.lead, args.url, args.confirm)
    except CreatorError as exc:
        print(f"creator: {exc}")
        return 1
    finally:
        CURRENT_TIER.reset(token)
        client.close()
    print(f"lead {said.get('id', args.lead)} {said.get('status')}  "
          f"reply {said.get('reply_url') or args.url}  "
          f"reward {said.get('reward_status')!r}")
    return 0


def main(argv: list[str] | None = None) -> int:
    # A lead's body is anyone's tweet; a cp1250 console cannot print most of them.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
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
    done = sub.add_parser("posted", help="mark a lead posted with the reply's "
                                         "link; the reward is credited on it")
    done.add_argument("--outlet", choices=OUTLETS, default="twitter")
    done.add_argument("--lead", type=int, required=True)
    done.add_argument("--url", required=True, help="the posted reply's own link")
    done.add_argument("--confirm", action="store_true")
    args = parser.parse_args(argv)
    if args.cmd == "posted":
        return cmd_posted(args)
    return cmd_leads(args) if args.cmd == "leads" else cmd_claim(args)


if __name__ == "__main__":
    raise SystemExit(main())

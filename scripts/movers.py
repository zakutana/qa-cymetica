"""The Movers Tournament: a free, scored competition -- no money moves.

Their own page, verbatim: "no prizes are attached and nothing moves money."
Enter up to five universe symbols a round; each pick locks the stored close on
the round day and scores a week later on its real 7-day return. Their own
NEXUS screen already competes as a public reference row -- read `round_state`
and this is a free, independent, already-running measurement of Nexus's real
forward-return skill that nothing here read before 2026-09-13.

Picks come from Nexus, not from us: CLAUDE.md's "Who decides what to trade"
holds here exactly as it holds everywhere else. `enter()` takes the symbols as
an argument rather than choosing them, so the caller (the laboratory's `ask`
step) is where a Nexus answer becomes a submission.

**The submission shape is theirs, published 2026-09-13** in the new "Clone
Tools & Tournaments" section of `/api-docs`, after the operator relayed the
gap over Telegram (MSG-0011):

    POST /api/v1/universe/movers/tournament/enter
    Body: {"symbols": ["AAPL", "NVDA"]}  (1-5 symbols)
    "Requires a session or API key. Unknown or unpriced symbols are rejected
     with a plain 422 reason."

Until that morning this module guessed the POST went to the tournament path
itself, and `movers.enter` was registered `probe_only` because a wrong body
their server happened to accept would lock a real week-long round on garbage
picks. **The guess was wrong** -- the documented path is one segment longer --
so the flag is the reason a wrong submission never reached a live round. It
came off once their document named the shape; the MUTATE floor under it did
not.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

TOURNAMENT = "/api/v1/universe/movers/tournament"
ENTER = f"{TOURNAMENT}/enter"   # their document, 2026-09-13; not the guess
MAX_PICKS = 5


class MoversError(ValueError):
    """A read or a submission this module refuses before it reaches the
    network, or cannot make sense of once it answers."""


def round_state(client) -> dict:
    """The live state: `rules`, `round`, `leaderboard`, `my_entries`.

    A plain GET -- default-allowed at SAFE, and moves no money -- so no
    components.yaml entry is needed for this half.
    """
    response = client.get(TOURNAMENT)
    if response.status_code != 200:
        raise MoversError(
            f"{TOURNAMENT} answered HTTP {response.status_code}; a failed "
            f"read is not an empty tournament")
    try:
        return response.json() or {}
    except ValueError as exc:
        raise MoversError(f"{TOURNAMENT} did not answer JSON: {exc}") from exc


def already_entered(state: dict) -> bool:
    """Whether `my_entries` already names a pick for THIS round.

    Keyed on `round.round_anchor`, the field their own state uses to name the
    round -- not on "any entry ever", or a scored past round would look like
    an open one still waiting.
    """
    anchor = (state.get("round") or {}).get("round_anchor")
    if not anchor:
        return False
    for entry in state.get("my_entries") or []:
        if isinstance(entry, dict) and entry.get("round_anchor") == anchor:
            return True
    return False


def house_row(state: dict) -> dict | None:
    """Their own NEXUS reference row on the leaderboard, if it is there --
    the free, independent read of Nexus's real forward-return skill."""
    for row in state.get("leaderboard") or []:
        if isinstance(row, dict) and row.get("is_house"):
            return row
    return None


def enter(client, symbols: list[str], confirm: bool) -> dict:
    """Submit up to five picks, to the path and body their document names.

    Refuses over the limit, on no symbol, and without `confirm`, all before
    anything reaches the network. The POST itself is still a MUTATE and needs
    `--allow-mutate` turned on for their host on purpose -- a round locks for
    a week once entered.
    """
    cleaned = [str(s).strip().upper() for s in symbols if str(s).strip()]
    if not cleaned:
        raise MoversError("no symbol given")
    if len(cleaned) > MAX_PICKS:
        raise MoversError(
            f"{len(cleaned)} symbols, and the rules allow at most {MAX_PICKS}")
    if not confirm:
        raise MoversError("pass confirm=True to actually submit")
    response = client.post(ENTER, json={"symbols": cleaned})
    if response.status_code not in (200, 201):
        # Their own note: "Unknown or unpriced symbols are rejected with a
        # plain 422 reason" -- so the body is worth printing, not swallowing.
        raise MoversError(
            f"entry refused: HTTP {response.status_code} {response.text[:200]!r}")
    try:
        return response.json() or {}
    except ValueError:
        return {"status_code": response.status_code}


def _client():
    from qa.client import build_client
    from qa.config import identities, load_dotenv
    from qa.safety import EndpointRegistry

    load_dotenv()
    ids = identities()
    identity = ids["trusted"] if ids["trusted"].present else ids["anon"]
    return build_client(identity, EndpointRegistry.load(), timeout=30.0)


def cmd_status(_args) -> int:
    from qa.safety import CURRENT_TIER, SafetyTier

    client = _client()
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        state = round_state(client)
    finally:
        CURRENT_TIER.reset(token)
        client.close()
    round_ = state.get("round") or {}
    rules = state.get("rules") or {}
    print(f"round {round_.get('round_anchor')}: {round_.get('entries')} "
         f"entrant(s), scores after {round_.get('scores_after')}")
    print(f"rules: up to {rules.get('max_picks')} symbol(s), "
         f"{rules.get('window_days')}-day window")
    print(f"already entered this round: {already_entered(state)}")
    house = house_row(state)
    if house:
        print(f"NEXUS screen (house): avg {house.get('avg_pct')}% over "
             f"{house.get('rounds')} round(s), {house.get('doublers')} "
             f"doubler(s) of {house.get('picks')} pick(s)")
    for entry in state.get("my_entries") or []:
        print(f"our entry: {entry}")
    return 0


def cmd_enter(args) -> int:
    """A round locks for seven days, so the two brakes are both deliberate:
    `--confirm` here, and `--allow-mutate` turned on for their host below --
    the same shape `paper.py` uses for an order."""
    from qa.client import build_client
    from qa.config import identities, load_dotenv
    from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier

    load_dotenv()
    registry = EndpointRegistry.load()
    registry.mutate_enabled = True
    registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    client = build_client(identities()["trusted"], registry, timeout=30.0)
    token = CURRENT_TIER.set(SafetyTier.MUTATE)
    try:
        try:
            result = enter(client, args.symbols, args.confirm)
        except Exception as exc:  # noqa: BLE001 -- a refusal, printed plainly
            print(f"movers: {exc}")
            return 1
    finally:
        CURRENT_TIER.reset(token)
        client.close()
    print(f"entered: {result}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="round state, our entry, the NEXUS reference row")

    enter_p = sub.add_parser("enter", help="submit up to 5 picks (probe_only until confirmed)")
    enter_p.add_argument("--symbols", nargs="+", required=True)
    enter_p.add_argument("--confirm", action="store_true")

    args = parser.parse_args(argv)
    if args.cmd == "status":
        return cmd_status(args)
    return cmd_enter(args)


if __name__ == "__main__":
    raise SystemExit(main())

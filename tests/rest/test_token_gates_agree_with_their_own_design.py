"""The withdrawal token gates, held against the design they publish beside them.

`GET /api/v1/withdrawals/token-gates` answers without a key and carries four
things at once: a row per governed token with `withdrawals_open`, a
`paused_tokens` list, a `governed_tokens` list, and a `design` block that
states the rules in prose:

    default            open -- a token with no gate row is withdrawable
    gate_can_only_pause true
    payout_cap         every withdrawal is capped to the user's real on-chain
                       reserves; a gate never widens that
    not_governed       stablecoins and ETH do not pass through this gate
    audit              each pause/open is a stored row with who, when and why
    how_you_see_it     the withdrawal screen returns the
                       user_message_when_paused text at request time

This is a money surface read by a holder who wants to know whether they can
take their tokens out, and the three machine-readable parts of it are three
statements of the same fact. They must agree, or one of them is lying to that
holder.

WHAT IT ASSERTS, all inside one response so no second read can explain a
difference away:

  1. `paused_tokens` is exactly the set of tokens whose row says
     `withdrawals_open` is false. A token paused in the list and open in its
     row -- or the reverse -- tells two different stories about the same
     token.
  2. `governed_tokens` is exactly the set of tokens that have a row. The
     design says a token with no gate row is withdrawable by default, so a
     token named as governed with no row of its own has no state to read.
  3. A paused token carries `user_message_when_paused`. Their own design says
     that text is what the withdrawal screen shows at request time, so a
     pause without one leaves the holder with a refusal and no reason.

WHAT IT DOES NOT. Not `payout_cap` -- the on-chain reserve behind it is not
readable from here and a withdrawal is never attempted. Not `audit` -- the
stored rows are theirs and not served. Not `not_governed`, because the
absence of a stablecoin from this list is consistent both with the rule and
with a token they forgot, and an absence is the easiest thing to read wrongly.

INCONCLUSIVE when the response carries no gate rows at all: an empty gate
list is a platform with nothing paused, and a rule over nothing is not a
measurement (rule 10).

Undocumented in llms.txt, which names neither this route nor any
`withdrawals/` route -- said here because it is worth knowing when reading the
verdict, and reported separately rather than measured as a defect.

SAFE. One GET, no key, nothing withdrawn.
"""

from __future__ import annotations

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

GATES = "/api/v1/withdrawals/token-gates"


@qa(component="funding.withdraw", tier=SafetyTier.SAFE, surface="rest")
def test_the_token_gates_say_the_same_thing_three_times(rest_anon):
    """One read: the rows, the two lists and the prose beside them."""
    response = rest_anon.get(GATES)
    if response.status_code != 200:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"{GATES} answered HTTP {response.status_code}, and a "
                   f"failed read is not a platform with no gates",
            sources={"gates": GATES}))
        return

    body = response.json()
    rows = [r for r in (body.get("gates") or []) if isinstance(r, dict)]
    if not rows:
        conclude(Measurement(
            verdict="inconclusive",
            reason="the response carries no gate rows, so there is no token "
                   "whose state the two lists could agree or disagree with",
            sources={"gates": GATES}))
        return

    named = {str(r.get("token")) for r in rows if r.get("token")}
    shut = {str(r.get("token")) for r in rows
            if r.get("token") and r.get("withdrawals_open") is False}
    open_ = {str(r.get("token")) for r in rows
             if r.get("token") and r.get("withdrawals_open") is True}
    # A15, deep pass of 2026-09-22: a list the response does not carry is
    # unread, not empty -- `or []` failed every paused row as "absent from
    # paused_tokens" when the field was renamed or dropped (rule 8).
    unread = [name for name in ("paused_tokens", "governed_tokens")
              if not isinstance(body.get(name), list)]
    listed_paused = {str(t) for t in (body.get("paused_tokens") or [])}
    listed_governed = {str(t) for t in (body.get("governed_tokens") or [])}

    problems: list[str] = []
    if "paused_tokens" not in unread:
        for token in sorted(listed_paused - shut):
            state = "open" if token in open_ else "unstated"
            problems.append(
                f"{token} is in paused_tokens while its own row says "
                f"withdrawals_open is {state}")
        for token in sorted(shut - listed_paused):
            problems.append(
                f"{token}'s row says withdrawals_open false and it is absent "
                f"from paused_tokens, so a reader of that list is told it is "
                f"open")
    if "governed_tokens" not in unread:
        for token in sorted(listed_governed - named):
            problems.append(
                f"{token} is named in governed_tokens and has no gate row, so "
                f"its state cannot be read -- and by their own default a "
                f"token with no row is withdrawable")
        for token in sorted(named - listed_governed):
            problems.append(
                f"{token} has a gate row and is absent from governed_tokens")
    for row in rows:
        token = str(row.get("token"))
        if row.get("withdrawals_open") is False and not str(
                row.get("user_message_when_paused") or "").strip():
            problems.append(
                f"{token} is paused and carries no user_message_when_paused, "
                f"which their design says is the text the withdrawal screen "
                f"shows at request time")

    if unread and not problems:
        conclude(Measurement(
            verdict="inconclusive",
            reason=(f"the response carries no {' and no '.join(unread)} list, "
                    f"so what the rows say could not be held against it -- a "
                    f"list that is not there is not an empty one"),
            sources={"gates": GATES},
            population={"gate_rows": len(rows), "unread": unread}))
        return

    conclude(Measurement(
        verdict="failed" if problems else "passed",
        reason=("; ".join(problems) if problems else
                f"the {len(rows)} gate row(s), paused_tokens and "
                f"governed_tokens say the same thing, and each of the "
                f"{len(shut)} paused token(s) carries the message their design "
                f"says a holder is shown"),
        left={"rows": [{"token": r.get("token"),
                        "withdrawals_open": r.get("withdrawals_open"),
                        "has_message": bool(str(
                            r.get("user_message_when_paused") or "").strip())}
                       for r in rows]},
        right={"paused_tokens": sorted(listed_paused),
               "governed_tokens": sorted(listed_governed),
               "design": body.get("design")},
        sources={"gates": GATES},
        population={"gate_rows": len(rows), "paused": len(shut)}))

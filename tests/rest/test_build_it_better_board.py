"""What Build it Better promises a requester, read off its own board.

The product takes a free-text list of improvements, turns it into a BB-SPEC,
and asks the requester to lock that spec. The spec is therefore the whole
contract: whatever it drops, the build will not contain, and the requester
signs it without a diff.

It dropped things. On ET-26036 (2026-09-19, 18:29:58 UTC) the generator kept
only the first eight sentences of a seven-line request, which lost the last
line entirely -- the definition of success, without which "80% and 90%" cannot
be checked at all -- and cut another line at the full stop inside "(e.g.
Bollinger Bands, MACD, RSI)", turning one requirement into three. A BB-CHANGE
at 18:34 was appended to `improvements` and the regenerated spec came back
byte-identical, so the correction could not reach the scope either. Their
REPLY-0021 says the generator was fixed: a line is an item, nothing is cut at
"e.g.", there is no sentence cap, and a BB-CHANGE is carried verbatim as an
addendum.

That fix is their claim, and this is the reading of it. It runs over the
WHOLE board rather than over our own ticket, because our ticket is the one
they repaired by hand: a generator that works only on the request someone
complained about is not a fixed generator. Today the board holds one request
and it is ours, so the check says so in its reason and gets stronger the
moment a stranger files one.

WHAT IT ASSERTS, AND WHAT IT DOES NOT. A spec must contain each improvement
line WHOLE. It may add to it -- the standard paragraphs about branding and
out-of-scope operations, a numbering, the BB-CHANGE addenda -- and adding is
not the defect. Only a line that no longer appears complete anywhere in the
spec is, because that is a requirement the requester cannot lock. A request
whose spec has not been generated yet is not evidence of anything and is left
out, not counted as a failure.

SAFE. Two GETs and no key: the board is public, which is the point of it.
"""

from __future__ import annotations

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

BOARD = "/api/v1/build-it-better/requests"

# The sentence every generated spec ends on, quoted from ET-26036's own
# spec_text. Matched verbatim: a check that looked for "MicroFund" would go
# on passing through a rewording that kept the false promise.
GATE_SENTENCE = ("The 24-hour clock starts when this spec is accepted AND "
                 "the $100 MicroFund gate is filled (or waived).")


def lines_of(improvements: str) -> list[str]:
    """The requester's list, one item per line.

    Their own generator now treats a line as an item, which is what REPLY-0021
    says it fixed, so this reads the request the same way the spec-writer is
    supposed to. Blank lines are separators, not items.
    """
    return [line.strip() for line in (improvements or "").splitlines()
            if line.strip()]


def dropped(improvements: str, spec: str) -> list[str]:
    """Improvement lines that appear nowhere whole in the spec.

    Substring, not similarity: the claim is that the requester's own words
    survive into the thing they are asked to sign. A spec that paraphrases a
    requirement has changed it, and a requester diffing by eye would not see
    that either.
    """
    return [line for line in lines_of(improvements) if line not in (spec or "")]


def clock_runs_unfunded(record: dict) -> dict | None:
    """A request whose clock runs with the gate neither filled NOR waived.

    The spec says "filled (or waived)", and the first version of this read
    only `funded`. ET-26036 carries, in the same block, `waived: true`,
    `waived_at` equal to `clock_started_at` to the microsecond, and
    `waiver_reason: "Build it Better: requester holds 100+ ET10"` -- so the
    sentence was true, the product did exactly what it documents, and the
    contradiction was mine. #108 went to the vendor on the strength of it and
    was withdrawn the same hour.

    What made it possible: a probe that printed the funding block truncated to
    200 characters, which cut it three keys before `waived`. The reading was
    then built on the truncation. `waived` is therefore read FIRST here, and
    every key this judgement rests on is named in the returned dict so the
    report quotes what was actually read.
    """
    spec = str(record.get("spec_text") or "")
    if GATE_SENTENCE not in spec:
        return None
    funding = record.get("funding")
    if not isinstance(funding, dict):
        return None
    if funding.get("waived") is not False or funding.get("funded") is not False:
        return None
    started = record.get("clock_started_at")
    if not started:
        return None
    return {"ticket": record.get("ticket"), "clock_started_at": started,
            "raised_usd": funding.get("raised_usd"),
            "goal_usd": funding.get("goal_usd"),
            "waived": funding.get("waived"),
            "stage": record.get("stage"),
            "ready_to_build": record.get("ready_to_build")}


@qa(component="rest.build_it_better", tier=SafetyTier.SAFE, surface="rest")
def test_the_spec_s_funding_gate_is_the_one_the_build_actually_waits_on(
        rest_anon):
    """The clock may start when the gate is filled, or waived, and not before.

    Every BB-SPEC ends: *"The 24-hour clock starts when this spec is accepted
    AND the $100 MicroFund gate is filled (or waived)."* There are two
    hundreds in this product and they are easy to conflate: **100 ET10 HELD**
    in the requester's account, which is what `bb_file_request` means by
    "nothing is charged or locked; there is no fee and nothing to fund", and a
    **$100 MicroFund raised**, which is the gate the spec names.

    On ET-26036 they meet: the holding waives the raise. `funding.waived` is
    true, `waived_at` equals `clock_started_at` to the microsecond, and
    `waiver_reason` reads "Build it Better: requester holds 100+ ET10". The
    product did exactly what it documents.

    This check was written the other way round and filed #108 against it, on a
    reading that had `funded: false` and `raised_usd: 0.0` and had never seen
    `waived` -- a probe printed the funding block truncated to 200 characters,
    three keys short of it. Withdrawn the same hour. What survives is the
    reading itself, now correct and worth keeping: a clock that starts while
    the gate is neither filled nor waived would be a real defect, and nothing
    else watches for it.
    """
    board = rest_anon.get(BOARD)
    if board.status_code != 200:
        raise Inconclusive(
            f"{BOARD} answered HTTP {board.status_code}; a failed read is not "
            f"an empty board")
    try:
        items = (board.json() or {}).get("items") or []
    except ValueError:
        raise Inconclusive(f"{BOARD} answered 200 with a body that is not JSON")
    if not items:
        raise Inconclusive("the board holds no request, so no spec makes the "
                           "claim this reads")

    read, wrong = [], []
    for item in items:
        ticket = str(item.get("ticket") or "")
        if not ticket:
            continue
        one = rest_anon.get(f"{BOARD}/{ticket}")
        if one.status_code != 200:
            continue
        try:
            record = one.json() or {}
        except ValueError:
            continue
        if GATE_SENTENCE not in str(record.get("spec_text") or ""):
            continue
        read.append(ticket)
        contradiction = clock_runs_unfunded(record)
        if contradiction:
            wrong.append(contradiction)

    if not read:
        raise Inconclusive(
            "no request on the board carries a spec that makes the funding "
            "claim, so there is nothing to hold their behaviour against")

    conclude(Measurement(
        verdict="failed" if wrong else "passed",
        reason=(
            f"{len(wrong)} of {len(read)} request(s) have the 24-hour clock "
            f"running while the gate their own spec says it waits for is "
            f"neither filled nor waived: "
            + "; ".join(
                f"{w['ticket']} clock from {str(w['clock_started_at'])[:19]}, "
                f"{w['raised_usd']} of {w['goal_usd']} USD raised, "
                f"waived {w['waived']}, stage {w['stage']}, "
                f"ready_to_build {w['ready_to_build']}"
                for w in wrong[:3])
            if wrong else
            f"on {len(read)} request(s) the clock starts only once the gate "
            f"is filled or waived, as the spec says it does"),
        left={"clock_running_unfunded": len(wrong)}, right={"expected": 0},
        sources={"board": BOARD}))


@qa(component="rest.build_it_better", tier=SafetyTier.SAFE, surface="rest")
def test_a_spec_carries_every_line_of_the_request_it_answers(rest_anon):
    """The scope a requester is asked to lock is the scope they filed."""
    board = rest_anon.get(BOARD)
    if board.status_code != 200:
        raise Inconclusive(
            f"{BOARD} answered HTTP {board.status_code}; a failed read is not "
            f"an empty board")
    try:
        items = (board.json() or {}).get("items") or []
    except ValueError:
        raise Inconclusive(f"{BOARD} answered 200 with a body that is not JSON")
    if not items:
        raise Inconclusive(
            "the board holds no request at all, so there is no spec to read "
            "against the request it answers")

    read, losses, unspecced = [], [], []
    for item in items:
        ticket = str(item.get("ticket") or "")
        if not ticket:
            continue
        one = rest_anon.get(f"{BOARD}/{ticket}")
        if one.status_code != 200:
            continue
        try:
            record = one.json() or {}
        except ValueError:
            continue
        spec = record.get("spec_text")
        improvements = record.get("improvements")
        if not lines_of(improvements):
            continue
        # A spec that has not been written yet is not a spec that dropped
        # something. Named in the reason rather than counted either way.
        if not spec:
            unspecced.append(ticket)
            continue
        read.append(ticket)
        for line in dropped(improvements, spec):
            losses.append((ticket, line))

    if not read:
        raise Inconclusive(
            "no request on the board has both a list of improvements and a "
            "generated spec, so there is nothing to compare"
            + (f" ({len(unspecced)} awaiting a spec)" if unspecced else ""))

    mine = [t for t in read if t == "ET-26036"]
    conclude(Measurement(
        verdict="failed" if losses else "passed",
        reason=(
            f"{len(losses)} requirement(s) are in the request and in no spec: "
            + "; ".join(f"{ticket} '{line[:70]}'" for ticket, line in losses[:4])
            if losses else
            f"every improvement line of {len(read)} request(s) appears whole "
            f"in the spec that request was asked to lock"
            + (f"; the board holds only our own ticket, so this reads the "
               f"generator on the one request they repaired by hand"
               if read == mine else ""))
        + (f" ({len(unspecced)} request(s) have no spec yet and are not "
           f"evidence either way)" if unspecced else ""),
        left={"requests_read": len(read), "dropped": len(losses)},
        right={"dropped": 0},
        sources={"board": BOARD}))

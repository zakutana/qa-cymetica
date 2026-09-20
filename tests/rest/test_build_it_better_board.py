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

import json
import re
from pathlib import Path

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

REPO = Path(__file__).resolve().parents[2]

BOARD = "/api/v1/build-it-better/requests"

# The sentence every generated spec ends on, quoted from ET-26036's own
# spec_text. Matched verbatim: a check that looked for "MicroFund" would go
# on passing through a rewording that kept the false promise.
GATE_SENTENCE = ("The 24-hour clock starts when this spec is accepted AND "
                 "the $100 MicroFund gate is filled (or waived).")


def _our_token() -> str:
    """Our own request_token, if this machine holds one.

    `build-it-better.key` is the SAVED RESPONSE, not a bare token -- and the
    first version of the leak scan compared the whole 5 847-character file
    against the payload, a comparison that could never match and reported "no
    leak" on the strength of it. The field is read by name, and a value that
    is not token-shaped is treated as no token rather than as a needle.
    """
    path = REPO / "build-it-better.key"
    if not path.is_file():
        return ""
    try:
        held = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    value = (held or {}).get("request_token")
    return value if isinstance(value, str) and 8 <= len(value) <= 64 else ""


def lines_of(improvements: str) -> list[str]:
    """The requester's list, one item per line.

    Their own generator now treats a line as an item, which is what REPLY-0021
    says it fixed, so this reads the request the same way the spec-writer is
    supposed to. Blank lines are separators, not items.
    """
    return [line.strip() for line in (improvements or "").splitlines()
            if line.strip()]


# A full stop ends a sentence only when a capital follows AND it is not the
# stop inside an abbreviation. Without the exclusions, "(e.g. Bollinger Bands,
# MACD, RSI)" splits in two and a spec that cut the line exactly there passes
# -- which is the ET-26036 defect handing itself an excuse. The fixture in
# tests/meta/test_pipeline_check_quality.py holds that case by name.
SENTENCE_END = re.compile(
    r"(?<!\be\.g\.)(?<!\bi\.e\.)(?<!\betc\.)(?<!\bvs\.)(?<=[.!?])\s+(?=[A-Z])")


def sentences_of(line: str) -> list[str]:
    """A line's sentences, split on a full stop that ends one.

    Their generator numbers what it writes, so a requester who files a
    paragraph gets it back as several items and the paragraph is then in no
    spec as one string -- ET-26171, 2026-09-20, the first request a stranger
    filed, which this check called a dropped requirement. Splitting on ". "
    alone would cut "(e.g. Bollinger Bands...)" in half and hand the generator
    the very excuse the check exists to refuse, so a full stop only ends a
    sentence when a capital letter starts the next one.
    """
    parts = re.split(SENTENCE_END, line.strip())
    return [p.strip() for p in parts if p.strip()]


def dropped(improvements: str, spec: str) -> list[str]:
    """Improvement lines that appear nowhere whole in the spec.

    Substring, not similarity: the claim is that the requester's own words
    survive into the thing they are asked to sign. A spec that paraphrases a
    requirement has changed it, and a requester diffing by eye would not see
    that either.

    A line the generator SPLIT is not a line it dropped. When the whole line
    is not in the spec, each of its sentences must be, whole and separately --
    so numbering a paragraph into items passes, while a sentence that never
    arrived (ET-26036's last line) or one cut at the full stop inside "e.g."
    still fails. The unit of the claim moved from the line to the sentence;
    nothing about "whole, not paraphrased" moved with it.
    """
    text = spec or ""
    missing = []
    for line in lines_of(improvements):
        if line in text:
            continue
        pieces = sentences_of(line)
        if len(pieces) > 1 and all(piece in text for piece in pieces):
            continue
        missing.append(line)
    return missing


def gate_state(record: dict) -> str:
    """Which of five things this request's clock and gate actually say.

    Five, because the first version had two and the three it was missing all
    read as "the gate was honoured":

      no_claim            its spec does not make the promise at all
      unread              the funding block never says whether it was waived,
                          so we have taken no reading -- rule 8, and NOT
                          compliance. A key emitted only when a waiver exists
                          is the natural shape, and counting those tickets
                          into the pass made its sentence cover requests whose
                          gate nobody had looked at.
      not_started         the clock has not started; the spec is working
      clock_ran_early     the clock started BEFORE the gate was filled or
                          waived. This is the docstring's own headline, "and
                          not before", and it was never measured: the
                          evidence quoted for it is a timestamp -- waived_at
                          equal to clock_started_at to the microsecond -- and
                          only the booleans were read.
      clock_ran_unopened  the clock is running with the gate neither filled
                          nor waived

    Found by two readers on 2026-09-20, the day the check was written.
    """
    from datetime import datetime, timezone

    if GATE_SENTENCE not in str(record.get("spec_text") or ""):
        return "no_claim"
    funding = record.get("funding")
    if not isinstance(funding, dict) or "waived" not in funding \
            or "funded" not in funding:
        return "unread"
    started = record.get("clock_started_at")
    if not started:
        return "not_started"
    opened = funding.get("funded") is True or funding.get("waived") is True
    if not opened:
        return "clock_ran_unopened"

    def _moment(value):
        try:
            when = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None
        return when if when.tzinfo else when.replace(tzinfo=timezone.utc)

    began = _moment(started)
    # Whichever of the two opened it. `funded_at` is theirs too, and a gate
    # filled rather than waived carries that one instead.
    opened_at = _moment(funding.get("waived_at") or funding.get("funded_at"))
    if began and opened_at and began < opened_at:
        return "clock_ran_early"
    return "honoured"


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

    read, wrong, unread = [], [], []
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
        state = gate_state(record)
        if state == "no_claim":
            continue
        if state == "unread":
            # Named, never counted. A request whose funding block does not say
            # whether the gate was waived is one we have taken no reading of,
            # and the first version folded those into the passing population
            # so its sentence covered them.
            unread.append(ticket)
            continue
        read.append(ticket)
        if state in ("clock_ran_unopened", "clock_ran_early"):
            wrong.append({**(clock_runs_unfunded(record) or
                             {"ticket": ticket}), "state": state})

    if not read:
        raise Inconclusive(
            "no request on the board carries both a spec that makes the "
            "funding claim and a funding block that says whether the gate was "
            "waived, so there is nothing to hold their behaviour against"
            + (f" ({len(unread)} carry the claim and no reading)"
               if unread else ""))

    conclude(Measurement(
        verdict="failed" if wrong else "passed",
        reason=(
            f"{len(wrong)} of {len(read)} request(s) started the 24-hour "
            f"clock before the gate their own spec says it waits for: "
            + "; ".join(
                f"{w['ticket']} ({w['state']}) clock from "
                f"{str(w.get('clock_started_at'))[:19]}, "
                f"{w.get('raised_usd')} of {w.get('goal_usd')} USD raised, "
                f"waived {w.get('waived')}, stage {w.get('stage')}"
                for w in wrong[:3])
            if wrong else
            f"on {len(read)} request(s) the clock starts only once the gate "
            f"is filled or waived, and never before it"
            + (f"; {len(unread)} more carry the claim and no reading of the "
               f"gate, and are counted neither way ({', '.join(unread[:3])})"
               if unread else "")),
        left={"clock_before_gate": len(wrong), "read": len(read),
              "unread": len(unread)},
        right={"clock_before_gate": 0},
        sources={"board": BOARD}))


def overdue(item: dict, now) -> dict | None:
    """A build past its own published deadline with nothing shipped.

    Their promise is the product's headline: 24 hours from acceptance. The
    record publishes the clock itself -- `deadline_at`, and `our_url` once
    shipped -- so this asks nothing they have not already said.

    A request with no deadline, or one still inside it, is not evidence.
    `resolved_at` counts as shipped too: a build can finish without our_url
    being the thing that proves it, and reading only our_url would call a
    finished build late.
    """
    from datetime import datetime, timezone

    deadline = item.get("deadline_at")
    if not deadline:
        return None
    if item.get("our_url") or item.get("resolved_at") or item.get("verdict"):
        return None
    try:
        when = datetime.fromisoformat(str(deadline).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    if when >= now:
        return None
    return {"ticket": item.get("ticket"), "deadline_at": deadline,
            "stage": item.get("stage"), "over_by_hours":
                round((now - when).total_seconds() / 3600.0, 1)}


@qa(component="rest.build_it_better", tier=SafetyTier.SAFE, surface="rest")
def test_a_build_ships_inside_the_24_hours_it_publishes(rest_anon):
    """The product's headline promise, read off the clock it publishes itself.

    Every accepted request carries `clock_started_at` and `deadline_at`, and
    the board's own stats carry `on_time` and `median_build_seconds`. So the
    promise is measurable without asking them anything: a request whose
    deadline has passed with no `our_url`, no `resolved_at` and no `verdict`
    is a build that did not ship in the window they published for it.

    Written on 2026-09-20 at 11:05 UTC, while ET-26036 sits inside its window
    -- deadline 2026-09-20T20:25:59Z, nine hours out. That is the point of
    writing it now rather than tonight: a check put in place before the event
    it measures cannot be shaped by knowing the answer, which is the whole of
    why this repository preregisters anything at all.
    """
    from datetime import datetime, timezone

    board = rest_anon.get(BOARD)
    if board.status_code != 200:
        raise Inconclusive(
            f"{BOARD} answered HTTP {board.status_code}; a failed read is not "
            f"a board of builds that shipped on time")
    try:
        items = (board.json() or {}).get("items") or []
    except ValueError:
        raise Inconclusive(f"{BOARD} answered 200 with a body that is not JSON")

    now = datetime.now(timezone.utc)
    dated = [i for i in items if i.get("deadline_at")]
    if not dated:
        raise Inconclusive(
            "no request on the board publishes a deadline, so there is no "
            "promise of theirs to hold them to")

    late = [o for o in (overdue(i, now) for i in dated) if o]
    waiting = [i.get("ticket") for i in dated
               if not (i.get("our_url") or i.get("resolved_at")
                       or i.get("verdict"))
               and str(i.get("deadline_at")) > now.isoformat()]

    conclude(Measurement(
        verdict="failed" if late else "passed",
        reason=("; ".join(
            f"{o['ticket']} passed its own deadline {str(o['deadline_at'])[:19]} "
            f"{o['over_by_hours']}h ago and has shipped nothing "
            f"(stage {o['stage']})" for o in late)
            if late else
            f"no request on the board is past the 24-hour deadline it "
            f"publishes; {len(dated)} carry one"
            + (f", and {len(waiting)} are still inside their window: "
               f"{', '.join(str(t) for t in waiting)}" if waiting else "")),
        left={"overdue": len(late)}, right={"overdue": 0},
        sources={"board": BOARD}))


def stage_counts(items: list) -> dict:
    """The board's own list, counted by the stage each request is in."""
    out: dict[str, int] = {}
    for item in items or []:
        stage = str((item or {}).get("stage") or "")
        if stage:
            out[stage] = out.get(stage, 0) + 1
    return out


@qa(component="rest.build_it_better", tier=SafetyTier.SAFE, surface="rest")
def test_the_board_s_headline_numbers_are_the_list_underneath_them(rest_anon):
    """A visitor reads the counters; the list is right below them.

    `stats` gives total, requested, funded, building, shipped. The items array
    gives every request and its `stage`. They are the same facts twice, in one
    response, and the counters are what a stranger quotes -- so a drift
    between them is the page telling them something the data does not.

    Deliberately NOT compared, because they are different quantities and
    reading them as one is how #108 happened:

      `stats.on_time` counts SHIPPED builds that beat the deadline (0 today,
      because nothing has shipped), while an item's own `on_time` says the
      request is still inside its window -- ET-26036 has `on_time: true` and
      has not shipped. Same word, two meanings.

      `rebuilt_apps` (113) is not a count of anything in this response. It is
      the size of the /tools directory their bb_search_rebuilt_apps searches,
      not the board, and nothing here can check it -- so nothing here claims
      anything about it.
    """
    board = rest_anon.get(BOARD)
    if board.status_code != 200:
        raise Inconclusive(
            f"{BOARD} answered HTTP {board.status_code}; a failed read is not "
            f"a board whose numbers agree")
    try:
        payload = board.json() or {}
    except ValueError:
        raise Inconclusive(f"{BOARD} answered 200 with a body that is not JSON")
    stats, items = payload.get("stats"), payload.get("items")
    if not isinstance(stats, dict) or not isinstance(items, list):
        raise Inconclusive(
            "the board carries no stats block or no items array, so there are "
            "not two readings of the same fact to compare")

    counted = stage_counts(items)
    wrong = []
    if stats.get("total") != len(items):
        wrong.append(f"total says {stats.get('total')} and the list holds "
                     f"{len(items)}")
    for stage in ("requested", "funded", "building", "shipped"):
        if stage not in stats:
            continue
        if stats.get(stage) != counted.get(stage, 0):
            wrong.append(f"{stage} says {stats.get(stage)} and "
                         f"{counted.get(stage, 0)} item(s) are in that stage")

    conclude(Measurement(
        verdict="failed" if wrong else "passed",
        reason=("the board's counters disagree with the list under them: "
                + "; ".join(wrong) if wrong else
                f"the counters and the {len(items)} listed request(s) agree: "
                + ", ".join(f"{k} {v}" for k, v in sorted(counted.items()))),
        left={"stats": {k: stats.get(k) for k in
                        ("total", "requested", "funded", "building", "shipped")
                        if k in stats},
              "counted": counted},
        right={"disagreements": 0},
        sources={"board": BOARD}))


# Keys whose name promises a credential, as a suffix rule with one carve-out.
# `token_address` is a coin's contract address and is public; every other key
# ending in `token`, `secret` or `key` is not. The first version implemented
# the suffix for `_secret` alone and matched `token` only standing alone, so
# `owner_token`, `access_token` and `api_key` all passed the scan whose own
# docstring promised "the word standing alone or ENDING the key" -- and the
# verbatim fallback it names as the backstop does not run at all on a machine
# with no key file. Found by two readers on 2026-09-20.
CREDENTIAL_TAIL = ("token", "secret", "key", "password", "bearer")
NOT_A_CREDENTIAL = ("token_address", "token_addresses", "public_key")


def token_fields(node, path="") -> list[str]:
    """Every key anywhere in a payload whose NAME promises a credential."""
    out = []
    if isinstance(node, dict):
        for key, value in node.items():
            low = str(key).lower()
            if low not in NOT_A_CREDENTIAL and any(
                    low == tail or low.endswith("_" + tail)
                    for tail in CREDENTIAL_TAIL):
                out.append(f"{path}.{key}".lstrip("."))
            out += token_fields(value, f"{path}.{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            out += token_fields(value, f"{path}[{i}]")
    return out


@qa(component="rest.build_it_better", tier=SafetyTier.SAFE, surface="rest")
def test_a_public_read_of_a_build_does_not_carry_the_token_that_controls_it(
        rest_anon):
    """The board is public and the build is not: one token separates them.

    `bb_file_request` returns a one-time `request_token` and says "STORE the
    token, it is the only key to accept the scope and post the verdict".
    Every write tool -- bb_accept_spec, bb_request_change, bb_post_verdict --
    requires it, and its own schema says "only its holder may act". The read
    side is deliberately open: `bb_get_request` and the REST twin are
    "Read-only, no auth", and they return the whole record, messages
    included. So the entire holder rule rests on that one field never
    appearing in a read that needs no key.

    Measured with no credential at all, on both doors, over every request the
    board lists: 47 distinct keys come back and none of them is a token. The
    only match for the word is `coin.token_address`, a contract address.

    Where we hold our own token on this disk, the payload is searched for it
    VERBATIM as well, because a leak could rename the field. The value is
    never put in the reason, the left/right or the sources: a check that
    proves a secret is exposed must not be the thing that publishes it.

    It passes today. It is here because if it ever fails, a stranger can
    accept someone else's scope, rewrite it, or post a verdict on their build.
    """
    board = rest_anon.get(BOARD)
    if board.status_code != 200:
        raise Inconclusive(
            f"{BOARD} answered HTTP {board.status_code}; a failed read is not "
            f"a read that carried no token")
    try:
        payload = board.json() or {}
    except ValueError:
        raise Inconclusive(f"{BOARD} answered 200 with a body that is not JSON")
    items = payload.get("items") or []
    if not items:
        raise Inconclusive("the board holds no request, so no public read of "
                           "one can be made")

    ours = _our_token()
    read, named, verbatim = [], [], []

    # THE LIST RESPONSE TOO. The first version scanned only the per-ticket
    # reads, so a board that returned each item with its request_token while
    # the detail door stayed clean would have passed the check whose whole
    # subject is that field never appearing in a keyless read.
    named += [f"board:{f}" for f in token_fields(payload)]
    if ours and ours in (board.text or ""):
        verbatim.append("board")

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
        read.append(ticket)
        named += [f"{ticket}:{f}" for f in token_fields(record)]
        if ours and ours in (one.text or ""):
            verbatim.append(ticket)

    if not read:
        raise Inconclusive("no request on the board could be read, so nothing "
                           "was measured")

    conclude(Measurement(
        verdict="failed" if (named or verbatim) else "passed",
        reason=(
            f"a read that needs no credential carries the token that controls "
            f"the build: field(s) {sorted(set(named))}" if named else
            f"a read that needs no credential contains our own request_token "
            f"verbatim for {verbatim}, under a field name that does not say so"
            if verbatim else
            f"{len(read)} request(s) read anonymously and none carries a "
            f"request_token or any other credential field"
            + ("; our own token was searched for verbatim and is absent"
               if ours else "; no token of ours is on this disk to search for")),
        left={"requests_read": len(read), "token_fields": len(set(named))},
        right={"token_fields": 0},
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

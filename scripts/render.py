"""Render state/*.json into the operator dashboard.

The page is read-only by design: every control lives in the chat session with
the QA agent. What the dashboard owes the operator is an honest picture of
which parts of the platform are worth testing next, and what was actually said
to the vendor about each finding.

Sections are grouped by the product as a user meets it -- exchange, bots,
arena, money -- rather than by URL layout, because "which part of Cymetica is
this?" is the question being asked. Blast radius survives as a stripe on each
card, so prioritisation stays visible without organising the page around it.

Two numbers per section, deliberately kept apart:

  REACHABILITY  how much of the documented surface answers correctly. Measured
                now, by read-only GET, at two identities.
  CHECKS        how many real assertions exist about that section.

Collapsing them into one "health" score would be the exact defect this project
exists to catch: a section can be 100% reachable and completely unverified.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.findings import TAG_ORDER, TAGS  # noqa: E402

STATE = REPO_ROOT / "state"
OUT = REPO_ROOT / "dashboard" / "index.html"

# Every component in components.yaml, which is the registry conftest.py
# validates each @qa(component=) against at collection time. Eight were
# missing here -- rest.event_cards with seven checks, discovery.onboarding
# with four -- and their results fell into a bucket no tile carries, so the
# tiles undercounted by 460 of 525. test_every_component_lands_on_a_tile_or_
# is_declared_a_self_test is the guard; "_meta" is where our own self-tests
# go, and no tile draws it.
COMPONENT_TO_SECTION = {
    "reconciliation": "discovery", "discovery.wellknown": "discovery",
    "discovery.llmstxt": "discovery", "discovery.openapi": "discovery",
    "discovery.onboarding": "discovery",
    "mcp.tools_list": "mcp", "mcp.protocol": "mcp", "mcp.tools_call": "mcp",
    "mcp.trust_ladder": "identity_trust", "rest.agents": "agents",
    "rest.clob": "clob", "rest.markets": "markets", "rest.account": "account",
    "rest.arena": "arena", "rest.backtest": "backtest",
    "rest.event_cards": "event_cards", "ws.feeds": "realtime",
    "chain.launchpad": "launchpad",
    "funding.withdraw": "funding", "funding.deposit": "funding",
    "platform.ai_native_proof": "provenance", "platform.status": "swaps",
    "rest.support": "support", "rest.movers": "movers",
    "rest.clones": "clones",
    "meta.guard": "_meta", "meta.classifier": "_meta",
    "meta.pipeline": "_meta",
}
SELF_TEST_DIRS = ("tests/meta/", "tests/repo/")


def load(name: str) -> dict:
    # Through the seam, so a test session reads its own state directory
    # rather than the committed one.
    from qa.state import state_dir

    path = state_dir() / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _api_conversation() -> tuple[dict, dict]:
    """The exchange that happens through THEIR bounty API, per report.

    This is the only thing the page calls Correspondence. Telegram is a
    different channel with different properties -- attachments silently
    dropped, delivery unconfirmable -- and mixing the two produced a panel
    where a message nobody received sat beside a report they had answered, as
    though both were the same kind of fact.

    Returns (what we sent, what they said back), both keyed by report id.
    """
    import yaml

    spec = yaml.safe_load((REPO_ROOT / "outbox" / "reports.yaml").read_text(
        encoding="utf-8")) if (REPO_ROOT / "outbox" / "reports.yaml").exists() else {}
    by_key = {r["key"]: r for r in (spec or {}).get("reports", [])}

    # From the JOURNAL, not from state/submissions.json. That file stopped
    # being written when filing became two events, so it ends at #56 -- and
    # every report filed since rendered as an empty bubble with a date on it.
    # A projection nobody updates is worse than no projection: it looks
    # current.
    from qa.state import read_events

    intents: dict[str, dict] = {}
    ours: dict[int, dict] = {}
    for event in read_events():
        if event.get("type") == "filing_intent":
            intents[event["key"]] = event
        elif (event.get("type") == "filing_outcome"
              and event.get("outcome") == "accepted"
              and event.get("report_id") is not None):
            intent = intents.get(event.get("key"), {})
            report = by_key.get(event.get("key"), {})
            ours[event["report_id"]] = {
                "at": intent.get("intent_at") or event.get("at"),
                "title": intent.get("title") or report.get("title"),
                "text": (report.get("body") or "").strip(),
                "expected": (report.get("expected") or "").strip(),
                "actual": (report.get("actual") or "").strip(),
            }

    # When they FIRST said what they currently say. Not the newest observation:
    # bounty.py appends a vendor_status event on every run, so the newest one
    # records when we last polled, and using it made the "new reply" mark
    # reappear after every sweep -- a badge that cannot be cleared, which
    # teaches you to ignore the badge.
    first_said: dict[tuple, str] = {}
    for event in read_events():
        if event.get("type") != "vendor_status":
            continue
        key = (event.get("report_id"), event.get("status"))
        when = event.get("observed_at") or event.get("at")
        if when and (key not in first_said or when < first_said[key]):
            first_said[key] = when

    theirs: dict[int, dict] = {}
    for report in (load("bounty.json").get("our_reports") or {}).get("reports", []):
        report_id = report.get("id")
        if report_id is None:
            continue
        status = report.get("status")
        theirs[report_id] = {
            # A report they closed as `invalid` carries none of fixed_at,
            # validated_at, triaged_at or even updated_at -- only created_at,
            # which is when WE filed it. Reading those four and stopping left
            # the reply undated, and an undated reply is one the page cannot
            # ever mark as read.
            "at": (report.get("fixed_at") or report.get("validated_at")
                   or report.get("triaged_at")
                   or first_said.get((report_id, status))
                   or report.get("updated_at") or report.get("created_at")),
            "status": status,
            # Their own words, which is the whole reason this panel exists.
            "text": (report.get("status_notes") or "").strip(),
        }
    return ours, theirs


def _thread_for(row: dict, sent: dict, replied: dict, filed_at: dict) -> list[dict]:
    """The conversation about this finding, through their API, in order."""
    out = []
    for report in (row.get("filing") or {}).get("reports", []):
        report_id = report["report_id"]
        ours = sent.get(report_id, {})
        out.append({
            "who": "us", "report_id": report_id,
            "at": ours.get("at") or filed_at.get(report_id),
            "title": ours.get("title"),
            "text": ours.get("text") or "",
            "expected": ours.get("expected") or "",
            "actual": ours.get("actual") or "",
        })
        answer = replied.get(report_id) or {}
        if answer.get("status") and answer["status"] != "pending":
            out.append({
                "who": "them", "report_id": report_id,
                "at": answer.get("at"), "status": answer.get("status"),
                "text": answer.get("text") or "",
            })

    # What WE said after their answer. A verification goes out through
    # POST /reports/{id}/verification rather than as a comment, so it had no
    # bubble here -- and the operator read #86, saw "Resolved via ticket
    # ET-24493" as the last word, and asked why the page was calling the row
    # STILL REPRODUCIBLE. We had told them, an hour later. The only trace was
    # our own verdict quoted back inside THEIR message, because their
    # status_notes is one growing field their server appends to.
    #
    # From filing.verifications, which the fold computes, so the panel and the
    # ledger cannot disagree about what was sent.
    filed_ids = {r["report_id"] for r in (row.get("filing") or {}).get("reports", [])}
    for verification in (row.get("filing") or {}).get("verifications", []):
        report_id = verification.get("report_id")
        if report_id not in filed_ids:
            continue
        passed = verification.get("verdict") == "pass"
        out.append({
            "who": "us", "report_id": report_id,
            "at": verification.get("at"),
            "verdict": verification.get("verdict"),
            "run_id": verification.get("run_id"),
            "text": ("We re-checked and it passes, under the definition it "
                     "failed under."
                     if passed else
                     "We re-checked and it still fails. This corrects the "
                     "record rather than answering it."),
        })
    return sorted(out, key=lambda m: (m.get("at") or "", m["report_id"]))


def _test_catalogue() -> dict[str, str]:
    """nodeid without its parameters -> the one sentence the check opens with.

    The operator asked to open a tile and see WHICH checks are behind its
    count, *"a kazdy test by mel mit nejaky description 1 vetu z ceho
    pochopim co to zhruba testuje"*. That sentence exists already: it is the
    first line of the check's docstring, which every check in this repository
    writes because the contract audit reads it. Taking it from there rather
    than from a table means it cannot drift from the check, and a check whose
    docstring is rewritten says the new thing on the page the same day.
    """
    catalogue: dict[str, str] = {}
    for path in sorted((REPO_ROOT / "tests").rglob("test_*.py")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not node.name.startswith("test_"):
                continue
            doc = (ast.get_docstring(node) or "").strip()
            first = doc.split("\n", 1)[0].strip() if doc else ""
            catalogue[f"{rel}::{node.name}"] = first
    return catalogue


def _claim_questions() -> dict[str, str]:
    """claim id -> the question that claim exists to ask.

    One function, `test_sources_agree`, stands for every reconciliation claim,
    so its docstring cannot describe any of them. claims.yaml gives each claim
    a `question` in the operator's own words, which is the better sentence
    anyway.
    """
    path = REPO_ROOT / "tests" / "reconciliation" / "claims.yaml"
    try:
        import yaml

        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001 -- a missing claims file is not a page defect
        return {}
    return {c["id"]: (c.get("question") or "").strip()
            for c in data.get("claims", []) if c.get("id")}


def _tests_by_section(run: dict) -> dict[str, list[dict]]:
    """The checks a run adjudicated, per tile, each able to say what it looks at.

    Deduped by nodeid: a result is written per phase, and a tile listing the
    same check three times is a tile nobody trusts. Self-tests are dropped --
    they measure us, and 448 of them under "Support desk" is the loudest
    possible wrong number.
    """
    catalogue = _test_catalogue()
    questions = _claim_questions()
    out: dict[str, list[dict]] = {}
    seen: set[str] = set()
    for result in run.get("results", []):
        nodeid = result.get("nodeid") or ""
        if not nodeid or nodeid in seen:
            continue
        if nodeid.startswith(SELF_TEST_DIRS):
            continue
        section = COMPONENT_TO_SECTION.get(result.get("component", ""))
        if not section or section == "_meta":
            continue
        seen.add(nodeid)
        base, _, params = nodeid.partition("[")
        params = params.rstrip("]")
        # A run record is history, and a check can be renamed or retired after
        # it. Such a nodeid is not one whose description is missing -- it is
        # one that is GONE, and a tile that shows it blank invites the reader
        # to think we simply never wrote a description.
        gone = base not in catalogue
        doc = catalogue.get(base, "")
        if params and "::" in params:
            doc = questions.get(params.split("::", 1)[0], doc)
        out.setdefault(section, []).append({
            "nodeid": nodeid,
            "name": base.rsplit("::", 1)[-1].removeprefix("test_").replace("_", " "),
            "doc": doc,
            "gone": gone,
            "outcome": result.get("outcome"),
            "reason": ((result.get("measurement") or {}).get("reason") or "")[:300],
        })
    for tests in out.values():
        tests.sort(key=lambda t: t["nodeid"])
    return out


def _help_models() -> list[dict]:
    """The model/effort table, read out of CLAUDE.md at render time.

    The operator asked for it on the page: they set `/model` and `/effort`
    before giving a task, and the only copy lived in a file they do not open.
    Parsed rather than retyped, because a second copy of a table is a table
    that will disagree with the first one -- and this repository has the
    incident to prove it, in this very file's own git history.

    It stops at the first line that is not a table row, which is the blank
    line before the operator's tagged paragraph beneath it. Nothing reads
    past that.
    """
    text = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    start = text.index("## What a task needs")
    rows: list[dict] = []
    for line in text[start:].splitlines():
        line = line.strip()
        if not line.startswith("|"):
            if rows:
                break
            continue
        cells = [c.strip().replace("`", "") for c in line.strip("|").split("|")]
        if len(cells) != 2 or cells[0].lower() == "task" or set(cells[0]) <= {"-"}:
            continue
        model, _, effort = cells[1].partition(" · ")
        rows.append({"task": cells[0], "model": model.strip(),
                     "effort": effort.strip()})
    if not rows:
        raise RuntimeError(
            "CLAUDE.md's model table parsed to nothing, and a page showing an "
            "empty table would be claiming there are no rules")
    return rows


def _stats(ledger: dict, run: dict, events: list[dict]) -> dict:
    """The five figures the operator asked to see, each derived where it lives.

    Nothing here is typed in. Rewards come from their tracker, fixes from the
    transitions the fold wrote, test counts from the files themselves, channel
    latencies from qa/channels.py -- the one reader -- and the deep pass's own
    record from the notebooks in git history.

    The one judgement is which transition counts as a fix. `REPRODUCING ->
    PASSING` is a thing that was broken and now is not. `CHECK_CHANGED ->
    PASSING` is a definition we re-pinned, and there are 41 of those against
    18 real ones: counting them would more than treble the number and every
    one of the extras would be our own bookkeeping.
    """
    rewards = _rewards()
    fixes: dict[str, int] = {}
    told: dict[str, int] = {}
    # Distinct FINDINGS, not transitions. Summing transitions counted a bug
    # that regressed and was fixed again twice -- the live ledger holds 19
    # REPRODUCING->PASSING moves across 16 findings (CYM-tracker-closure-rate
    # three times, CYM-bounty-rewards-unrecorded twice), and the page printed
    # 19 under a heading the operator reads as a count of bugs. The fold has a
    # `reopen` obligation precisely because a row can go back and forth, so
    # this is the ordinary case, not an edge one. Found by review 2026-09-10,
    # confirmed 3/3.
    #
    # The by-day series still counts each move, because that IS an event on a
    # day; only the headline counts things that were broken and now are not.
    fixed_findings: set[str] = set()
    for finding_id, row in ledger.get("findings", {}).items():
        for transition in row.get("transitions", []):
            if (transition.get("axis") == "check"
                    and transition.get("from") == "REPRODUCING"
                    and transition.get("to") == "PASSING"):
                day = str(transition.get("at", ""))[:10]
                fixes[day] = fixes.get(day, 0) + 1
                fixed_findings.add(finding_id)
        for verification in (row.get("filing") or {}).get("verifications", []):
            if verification.get("verdict") == "pass":
                day = str(verification.get("at", ""))[:10]
                told[day] = told.get(day, 0) + 1

    counts = _test_counts()
    try:
        from qa import channels as channels_mod

        comparison = channels_mod.compare(events)
        # One entry per question, oldest first, for the squares on the page.
        strips: dict[str, list[dict]] = {}
        for pair in channels_mod.pairs(events):
            strips.setdefault(pair["channel"], []).append(
                {"answered": pair["answer_id"] is not None,
                 "minutes": pair["minutes"]})
    except Exception:  # noqa: BLE001 -- a channel we cannot read is not a page defect
        comparison, strips = {}, {}

    return {
        "rewards": rewards,
        "fixes": {
            "verified_by_us": len(fixed_findings),
            "re_fixed": sum(fixes.values()) - len(fixed_findings),
            "by_day": [{"day": d, "n": n} for d, n in sorted(fixes.items())],
            "told_them": sum(told.values()),
        },
        "tests": counts,
        "channels": comparison,
        "strips": strips,
        "nexus": _nexus_channel(),
        "process": _process_rows(),
        "fomo": _fomo_stats(),
    }


def _headline(row: dict) -> str:
    """A finding's name in a few words: the check that found it, humanised.

    The operator, 2026-09-11: every bug's name on the Findings tab was its
    whole description, so nothing could be read at a glance. The name of the
    check IS the invariant in a few words -- "a bot counts the stakes it has
    open" -- which is what they asked to see. The measured sentence stays in
    the row's body; the ledger's title is not touched.
    """
    checks = row.get("checks") or []
    params = ""
    if checks:
        base, _, params = str(checks[0]).partition("[")
        name = base.rsplit("::", 1)[-1]
        name = name[5:] if name.startswith("test_") else name
        params = params[:-1] if params.endswith("]") else params
    else:
        name = str(row.get("id") or "")
        name = name[4:] if name.startswith("CYM-") else name
    text = " ".join(name.replace("_", " ").replace("-", " ").split())
    text = text[:1].upper() + text[1:]
    if params:
        text = f"{text}: {params}"
    return text if len(text) <= 90 else text[:87].rstrip() + "..."


def _nexus_questions() -> list[dict] | None:
    """Every question put to ask_nexus_deep, once, with what happened to it.

    One derivation for two readers -- the Stats row counts these and the Nexus
    tab draws them -- so the two cannot disagree about which question was
    answered. None when nexus.py's record cannot be read at all, which is not
    the same thing as a record with nothing in it.

    Outcomes: answered; partial -- finalised "done" with only an opening
    sentence, their NEX-0009, fixed 2026-09-10 21:22; failed -- our loop gave
    up; refused -- no investigation started, QUERY_RESTRICTED and the like;
    waiting.
    """
    import importlib.util

    from qa.rooms import ANSWERED_CHARS

    try:
        spec = importlib.util.spec_from_file_location(
            "nexus_stats", REPO_ROOT / "scripts" / "nexus.py")
        nexus = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(nexus)
        rows = nexus.load()
    except Exception:  # noqa: BLE001 -- an unreadable record is not a page defect
        return None
    questions = []
    for question in rows:
        if question.get("type") != "question":
            continue
        qid = question.get("id")
        mine = [r for r in rows if r.get("id") == qid]
        answer = next((r for r in mine if r.get("type") == "answer"), None)
        gave_up = next((r for r in mine if r.get("type") == "gave_up"), None)
        if answer is not None:
            whole = len(answer.get("text") or "") >= ANSWERED_CHARS
            outcome = "answered" if whole else "partial"
        elif gave_up is not None:
            outcome = "failed"
        elif question.get("accepted") is False:
            outcome = "refused"
        else:
            outcome = "waiting"
        lower, upper = nexus.latency_bounds(rows, qid)
        seconds = (round((lower + upper) / 2, 1)
                   if lower is not None and upper is not None else None)
        questions.append({"id": qid, "at": question.get("at"),
                          "outcome": outcome, "seconds": seconds,
                          "upper": upper, "question": question,
                          "answer": answer, "gave_up": gave_up})
    return questions


def _nexus_summary(questions: list[dict]) -> dict:
    """The counts, and a typical time taken ONLY over questions we watched.

    Watched means both bounds known. A question looked at once, late, has only
    an upper bound, and counting it is how our pickup delay went out as their
    latency once already.
    """
    watched = sorted(q["seconds"] for q in questions
                     if q["seconds"] is not None
                     and q["outcome"] in ("answered", "partial"))
    median = None
    if watched:
        middle = len(watched) // 2
        median = (watched[middle] if len(watched) % 2
                  else round((watched[middle - 1] + watched[middle]) / 2, 1))

    def count(outcome):
        return sum(1 for q in questions if q["outcome"] == outcome)

    return {"asked": len(questions), "answered": count("answered"),
            "partial": count("partial"), "failed": count("failed"),
            "refused": count("refused"), "waiting": count("waiting"),
            "measured": len(watched), "median_seconds": median}


def _nexus_channel() -> dict:
    """Every question put to ask_nexus_deep, one entry each, by what happened.

    Not on the page at all until 2026-09-11, when the operator asked whether
    Nexus is reliable yet, next to Telegram. The outcomes are
    _nexus_questions()'s and the typical time is _nexus_summary()'s.

    The payload carries verdicts and times, never the words. The words are in
    the Nexus tab, which is served beside the payload and not inside it.
    """
    derived = _nexus_questions()
    if not derived:
        return {"asked": 0, "answered": 0, "partial": 0, "failed": 0,
                "refused": 0, "waiting": 0, "measured": 0,
                "median_seconds": None, "questions": []}
    return {**_nexus_summary(derived),
            "questions": [{k: q[k] for k in ("id", "at", "outcome", "seconds",
                                             "upper")} for q in derived]}


def _response_of(outcome: dict | None) -> dict:
    """The server's own reply stored inside an outcome row, parsed -- or {}."""
    raw = (outcome or {}).get("response")
    if isinstance(raw, dict):
        return raw
    try:
        value = json.loads(raw) if isinstance(raw, str) else None
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def _num(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _amount(value) -> str:
    """10000.0 -> '10 000', 0.00216 -> '0.00216': a figure as a sentence says it."""
    number = _num(value)
    if number is None:
        return "?"
    if number.is_integer():
        return f"{int(number):,}".replace(",", " ")
    if abs(number) >= 1:
        return f"{number:,.2f}".replace(",", " ")
    return f"{number:g}"


def _said(outcome: dict | None) -> str:
    """What became of an order, in its outcome row's own words."""
    if not outcome:
        return "no outcome recorded"
    said = outcome.get("outcome") or "unknown"
    status = outcome.get("http_status")
    return f"{said} (HTTP {status})" if status and said != "accepted" else said


def _orders(rows: list[dict]) -> list[tuple[str, dict, dict | None]]:
    """(id, intent, outcome) for every order in a paper.py or clone.py record,
    in the order the intents were written. A sample is not an order."""
    parts: dict[str, dict] = {}
    for row in rows:
        rid, kind = row.get("id"), row.get("type")
        if isinstance(rid, str) and kind in ("intent", "outcome"):
            parts.setdefault(rid, {}).setdefault(kind, row)
    return [(rid, p["intent"], p.get("outcome")) for rid, p in parts.items()
            if "intent" in p]


def _sampler_state(tick: dict | None) -> dict:
    """Where the console's sampler stands: when it last went round, whether
    that round read everything, and whether it has gone quiet.

    Stale is three intervals without a round -- the plan's measure -- so one
    slow round is not an alarm and a dead loop is. None when it never ran,
    which is neither fresh nor stale.
    """
    from datetime import datetime, timezone

    if not tick:
        return {"sampled_at": None, "sampler_ok": None, "sampler_every": None,
                "stale": None, "sampler_reads": None}
    every = _num(tick.get("every")) or 600.0
    try:
        age = (datetime.now(timezone.utc)
               - datetime.fromisoformat(str(tick.get("at")))).total_seconds()
    except (TypeError, ValueError):
        age = None
    return {"sampled_at": tick.get("at"), "sampler_ok": tick.get("ok"),
            "sampler_every": every,
            "stale": None if age is None else age > 3 * every,
            "sampler_reads": tick.get("reads")}


# A card whose trading is over. A leg on one that was never bought is past
# buying, not waiting for it.
CARD_CLOSED = ("settled", "resolved", "closed", "expired")


def _moment(text):
    """An ISO time as an aware datetime, or None. Their API writes +00:00 and
    so do we; a naive one is read as UTC."""
    from datetime import datetime, timezone

    try:
        moment = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def _index_at(series: list, when) -> float | None:
    """Where a card's index stood at `when`: the last point at or before it,
    else the first after it -- the price a proposal would have been bought at."""
    moment = _moment(when)
    if moment is None:
        return None
    stood = None
    for t, value in series:
        at = _moment(t)
        if at is None or value is None:
            continue
        if at <= moment:
            stood = value
        elif stood is None:
            return value
        else:
            break
    return stood


def _label(card: dict) -> str | None:
    """A card named by what it holds, which its headline does not say: "BTC"
    when one coin is nearly all of it, else the two heaviest -- "68 % BCH ·
    32 % OKB". None until the sampler has described the card."""
    weighed = sorted(((b.get("symbol"), _num(b.get("weight")))
                      for b in card.get("basket") or [] if isinstance(b, dict)),
                     key=lambda pair: -(pair[1] or 0.0))
    weighed = [(symbol, weight) for symbol, weight in weighed
               if symbol and weight is not None]
    if not weighed:
        return None
    if weighed[0][1] >= 0.95:
        return str(weighed[0][0])
    return " · ".join(f"{round(weight * 100)} % {symbol}"
                      for symbol, weight in weighed[:2])


def _lay_out(panel: dict, plan: dict, described: dict, index_points: dict,
             proposed_at) -> None:
    """A strategy's legs: Nexus's plan, with what was done laid over it.

    An order finds its leg by the card it bought; an order on a card the plan
    does not name becomes a leg of its own, so nothing that was done is left
    off the table. A leg keeps where its card stood when Nexus answered, so an
    unbought one can say how it moved since -- which the page labels as what
    would have happened, never as ours. Its levels are the take-profit and
    stop Nexus gave, in percent, from the entry -- or from that price while
    nothing was bought.
    """
    bankroll = _num(plan.get("bankroll"))
    legs: list[dict] = []
    by_card: dict[str, dict] = {}
    live: dict[str, list] = {}

    def leg(card: str, planned: dict) -> dict:
        row = described.get(card) or {}
        points = index_points.get(card) or {}
        series = [[t, points[t]] for t in sorted(points)]
        share = _num(planned.get("share"))
        at_proposal = _index_at(series, proposed_at) if planned else None
        last = series[-1][1] if series else None
        # Their page for the card -- the address their API returns as share_url
        # -- and none for a card their API does not know.
        view = {"card": card, "url": (None if row.get("status") == "not_found"
                                      else "https://cymetica.com/events/" + card),
                "label": _label(row), "card_title": row.get("title"),
                "symbol": row.get("evcdx_symbol"), "card_status": row.get("status"),
                "closes_at": row.get("trading_closes_at"),
                "planned": bool(planned), "side": planned.get("side"),
                "share": share,
                "usdc_proposed": (round(share * bankroll, 2)
                                  if share is not None and bankroll else None),
                "tp": _num(planned.get("tp")), "sl": _num(planned.get("sl")),
                "orders": [], "state": "not bought", "entry": None,
                "current": last, "invested": 0.0, "value": None, "pnl": None,
                "tp_level": None, "sl_level": None, "at_proposal": at_proposal,
                "since_proposal": (round((last / at_proposal - 1) * 100, 4)
                                   if last is not None and at_proposal else None),
                "series": series[-400:]}
        by_card[card] = view
        legs.append(view)
        return view

    for planned in plan.get("legs") or []:
        if planned.get("card") and planned["card"] not in by_card:
            leg(planned["card"], planned)
    for trade in panel["trades"]:
        if trade["outcome"] != "accepted" or not trade.get("card"):
            continue
        view = by_card.get(trade["card"]) or leg(trade["card"], {})
        view["orders"].append(trade["id"])
        view["invested"] += trade["usdc"] or 0.0
        view["side"] = view["side"] or trade["side"]
        if view["entry"] is None:
            view["entry"] = trade["entry"]
        if trade["closed_by"]:
            if trade["realized"] is not None:
                view["pnl"] = round((view["pnl"] or 0.0) + trade["realized"], 6)
            continue
        view["state"] = "open"
        if trade["current_index"] is not None:
            view["current"] = trade["current_index"]
            if trade["live_at"]:
                live[trade["card"]] = [trade["live_at"], trade["current_index"]]
        if trade["unrealized"] is not None:
            view["pnl"] = round((view["pnl"] or 0.0) + trade["unrealized"], 6)
        if trade["live_value"] is not None:
            view["value"] = round((view["value"] or 0.0) + trade["live_value"], 6)
    for view in legs:
        # A position's own reading, when it is newer than the card's last index
        # point, ends the line -- so the chart's "now" is the table's.
        reading = live.get(view["card"])
        if reading and view["series"]:
            newer, last = _moment(reading[0]), _moment(view["series"][-1][0])
            if newer and last and newer > last:
                view["series"].append(reading)
        if view["orders"]:
            view["state"] = "open" if view["state"] == "open" else "closed"
        elif view["card_status"] == "not_found":
            view["state"] = "card not found"
        elif view["card_status"] in CARD_CLOSED:
            view["state"] = "card closed"
        base = view["entry"] or view["at_proposal"]
        if base:
            if view["tp"] is not None:
                view["tp_level"] = base * (1 + view["tp"] / 100)
            if view["sl"] is not None:
                view["sl_level"] = base * (1 + view["sl"] / 100)

    pnls = [v["pnl"] for v in legs if v["pnl"] is not None]
    values = [v["value"] for v in legs if v["value"] is not None]
    shares = [v["share"] for v in legs if v["share"]]
    moves = [(v["share"], v["since_proposal"]) for v in legs
             if v["share"] and v["since_proposal"] is not None]
    weight = sum(share for share, _ in moves)
    # The countdown is to the card that is held; with nothing held, to the
    # first of the proposed ones to close.
    held = [v["closes_at"] for v in legs if v["closes_at"] and v["state"] == "open"]
    waiting = [v["closes_at"] for v in legs
               if v["closes_at"] and v["state"] == "not bought"]
    invested = panel["staked"]
    pnl = round(sum(pnls), 2) if pnls else None
    value = round(sum(values), 2) if values else None
    bots = panel["clones"]
    if bots:
        invested, pnl, value = bots[0]["funded"], bots[0]["pnl"], bots[0]["balance"]
    panel.update(
        holds="bot" if bots else "cards" if legs else None,
        legs=legs, reserve=_num(plan.get("reserve")), bankroll=bankroll,
        proposed_at=proposed_at,
        proposed_share=round(sum(shares), 6) if shares else None,
        invested=invested, pnl=pnl, value=value,
        pnl_pct=(round(pnl / invested * 100, 3) if pnl is not None and invested
                 else None),
        closes_at=min(held or waiting, default=None),
        if_bought_pct=(round(sum(s * m for s, m in moves) / weight, 4)
                       if weight else None))


def build_rooms() -> dict:
    """The Nexus tab: every room, its thread, and its panel.

    NOT part of build_payload(), and that is the design rather than an
    omission. The rooms carry the operator's notes and, later, what the sampler
    reads on a timer; both arrive while a sweep may be running. Anything in
    the payload rewrites dashboard/index.html, which is committed, so a note
    would dirty the tree mid-run and cost the run its level V -- the reason
    state/nexus.jsonl is gitignored at all. serve.py answers /rooms.json from
    this function instead and tells the open tab with an event of its own.

    Texts are verbatim. Escaping happens once, in the page, where they are
    drawn: a Nexus answer is data (CLAUDE.md), and the page treats it as text.

    Each reply sits straight after its own question, whenever it arrived. A
    question given up on eighteen minutes later still belongs under the one
    it answers, not after the two that were asked in between.

    A strategy room is opened from one whole Nexus answer (qa/rooms.py
    refuses anything else) and draws what was done about it from records
    that already say so: an order carries the Nexus id it acts on, a close
    follows the order that opened its position, and everything done to a bot
    afterwards -- funding it, switching it on, every sample -- carries the
    bot's instance id. A `link` draws in what names nothing. What names no
    room stays in General and says which it is: an order drawn inside a
    strategy it did not come from would be our activity dressed as Nexus's
    guidance.

    What their API says since -- a card's index, the bot's own trades, what
    it has locked, its indicators -- comes from state/samples.jsonl, which
    the console's sampler writes (scripts/sampler.py), and every panel says
    when that was last read.

    A strategy is called by its newest `title`, and its plan -- Nexus's
    proposal, leg by leg -- is laid under what was done (_lay_out), so a
    panel can say what it holds before it says anything in words.
    """
    from datetime import datetime, timezone

    from qa import rooms as store

    derived = _nexus_questions() or []
    stored = store.load()
    sampled = store.load_samples()
    sampler = _sampler_state(max((r for r in sampled if r.get("type") == "tick"),
                                 key=lambda r: str(r.get("at") or ""), default=None))
    marks = store.read_marks(stored)
    opened = store.strategies(stored)
    titles = store.names(stored)
    by_origin = {s.get("origin"): s["id"] for s in opened}
    linked: dict[str, str] = {}
    history: dict[str, list[dict]] = {room: [] for room in titles}
    for row in stored:
        room = row.get("room")
        if room not in titles:
            continue
        if row.get("type") == "link":
            linked[row.get("ref")] = room
        elif row.get("type") == "status":
            history[room].append({"status": row.get("status"),
                                  "why": row.get("why"), "at": row.get("at")})

    threads: dict[str, list[dict]] = {store.GENERAL: [],
                                      **{room: [] for room in titles}}
    order: dict[int, tuple] = {}

    def place(room: str, message: dict, at, rank: int) -> None:
        thread = threads[room if room in threads else store.GENERAL]
        order[id(message)] = (str(at or ""), rank, len(thread))
        thread.append(message)

    # Our summary of an answer is drawn inside it. The newest wins; one it
    # replaced stays on the page as a note, so nothing written disappears.
    asked = {q["id"] for q in derived}
    gists = {row["re"]: row for row in stored
             if row.get("type") == "claude_note" and row.get("gist") and row.get("re")}
    inside = {row.get("id") for qid, row in gists.items() if qid in asked}

    for q in derived:
        question, qid = q["question"], q["id"]
        home = (question.get("room") if question.get("room") in titles
                else linked.get(qid, store.GENERAL))
        opened_here = [s["id"] for s in opened if s.get("origin") == qid]
        gist = gists.get(qid)
        for room in [home] + [r for r in opened_here if r != home]:
            place(room, {"kind": "question", "id": qid, "at": q["at"],
                         "text": question.get("question") or "",
                         "opened": opened_here}, q["at"], 0)
            reply = {"kind": "reply", "id": qid, "outcome": q["outcome"],
                     "seconds": q["seconds"], "upper": q["upper"], "at": None,
                     "text": None, "gist": gist.get("text") if gist else None}
            if q["answer"] is not None:
                reply.update(at=q["answer"].get("at"),
                             text=q["answer"].get("text") or "")
            elif q["gave_up"] is not None:
                reply["at"] = q["gave_up"].get("at")
            elif q["outcome"] == "refused":
                reply.update(at=q["at"], text=question.get("error") or None)
            place(room, reply, q["at"], 1)
        if home != store.GENERAL:
            place(store.GENERAL, {"kind": "pointer", "id": qid, "at": q["at"],
                                  "room": home, "title": titles[home],
                                  "text": question.get("question") or ""},
                  q["at"], 0)

    panels: dict[str, dict] = {}
    for s in opened:
        changes = history[s["id"]]
        now = changes[-1] if changes else {}
        # What it was accepted on, and what the numbers said at the end of the
        # window. A room with neither is one nobody could score afterwards,
        # and the panel says so rather than leaving the space blank.
        accepted = store.acceptance_of(stored, s["id"])
        decided = store.verdict_of(stored, s["id"])
        panels[s["id"]] = {
            "kind": "strategy", "origin": s.get("origin"), "title": titles[s["id"]],
            "opened_at": s.get("at"), "status": now.get("status") or "proposed",
            "why": now.get("why"), "since": now.get("at") or s.get("at"),
            "history": changes, "trades": [], "staked": 0.0, "unclosed": 0,
            "realized": None, "clones": [],
            "criterion": ({"window_days": accepted.get("window_days"),
                           "stop_pct": accepted.get("stop_pct"),
                           "adopted": bool(accepted.get("adopted")),
                           "benchmark": accepted.get("benchmark_card"),
                           "at": accepted.get("at"), "why": accepted.get("why")}
                          if accepted else None),
            "verdict": ({"verdict": decided.get("verdict"),
                         "why": decided.get("why"),
                         "return_pct": decided.get("return_pct"),
                         "max_drawdown_pct": decided.get("max_drawdown_pct"),
                         "benchmark_pct": decided.get("benchmark_pct"),
                         "coverage": decided.get("coverage"),
                         "at": decided.get("at")}
                        if decided else None),
            "claim": (store.claim_of(stored, s["id"]) or {}).get("numbers") or None,
            **sampler}
        for change in changes:
            place(s["id"], {"kind": "status", "at": change["at"],
                            "status": change["status"], "text": change["why"]},
                  change["at"], 0)

    paper = store.records("paper.jsonl")
    opener_of: dict[str, dict] = {}
    for tid, intent, outcome in _orders(paper):
        said = (outcome or {}).get("outcome")
        if intent.get("kind") == "close":
            position = intent.get("position_id")
            opener = opener_of.get(position)
            room = linked.get(tid) or (opener["room"] if opener else store.GENERAL)
            realized = _num((outcome or {}).get("realized_pnl_usdc"))
            text = (f"{tid} · closed position {str(position)[:8]}"
                    + (f", opened by {opener['trade']['id']}" if opener
                       else ", which no order of ours opened")
                    + (f" · realized {realized:+g} USDC" if realized is not None
                       else "")
                    + ("" if said == "accepted" else f" · {_said(outcome)}"))
            if opener and said == "accepted":
                opener["trade"].update(closed_by=tid, closed_at=intent.get("at"),
                                       realized=realized)
        else:
            nexus_id = (intent.get("nexus") or {}).get("id")
            room = linked.get(tid) or by_origin.get(nexus_id) or store.GENERAL
            response = _response_of(outcome)
            position = ((outcome or {}).get("position_id")
                        or response.get("position_id"))
            side = response.get("side")
            text = (f"{tid} · paper buy{', ' + str(side) if side else ''}, "
                    f"{_amount(intent.get('usdc'))} USDC on card "
                    f"{str(intent.get('card_id'))[:8]}"
                    + (f" · after {nexus_id}" if nexus_id
                       else " · ours, no Nexus answer behind it")
                    + (f" · position {str(position)[:8]}"
                       if said == "accepted" and position else f" · {_said(outcome)}"))
            trade = {"id": tid, "at": intent.get("at"), "card": intent.get("card_id"),
                     "side": side, "usdc": _num(intent.get("usdc")), "outcome": said,
                     "position": position, "entry": _num(response.get("entry_index")),
                     "closed_by": None, "closed_at": None, "realized": None,
                     "live_status": None, "current_index": None, "unrealized": None,
                     "live_value": None, "live_at": None, "series": []}
            if said == "accepted" and position:
                opener_of[position] = {"room": room, "trade": trade}
            if room in panels:
                panels[room]["trades"].append(trade)
        place(room, {"kind": "leg", "id": tid, "at": intent.get("at"),
                     "text": text, "outcome": said}, intent.get("at"), 0)
    for panel in panels.values():
        done = [t for t in panel["trades"] if t["outcome"] == "accepted"]
        closed = [t["realized"] for t in done if t["realized"] is not None]
        panel.update(staked=sum(t["usdc"] or 0.0 for t in done),
                     unclosed=sum(1 for t in done if not t["closed_by"]),
                     realized=round(sum(closed), 6) if closed else None)

    clone_rows = store.records("clones.jsonl")
    bots: dict[str, dict] = {}
    for cid, intent, outcome in _orders(clone_rows):
        said = (outcome or {}).get("outcome")
        kind = intent.get("kind")
        response = _response_of(outcome)
        if not kind:
            nexus_id = (intent.get("nexus") or {}).get("id")
            room = linked.get(cid) or by_origin.get(nexus_id) or store.GENERAL
            name = response.get("name") or intent.get("custom_name")
            source = response.get("source_name") or intent.get("source_type")
            if said == "accepted":
                result = ""
            elif said == "not_sent":
                result = f" · not sent: {(outcome or {}).get('error')}"
            else:
                result = f" · {_said(outcome)}"
            text = (f"{cid} · clone {source} as \"{name}\""
                    + (", paper" if intent.get("paper") else "") + result)
            instance = (outcome or {}).get("clone_instance_id")
            if said == "accepted" and instance:
                bot = {"id": cid, "at": intent.get("at"), "name": name,
                       "source": response.get("source_name"),
                       "symbol": response.get("source_symbol"),
                       "strategy": response.get("strategy_type"),
                       "risk": response.get("risk_profile"),
                       "paper": (outcome or {}).get("is_paper", intent.get("paper")),
                       "instance": instance, "funded": 0.0, "trading": None,
                       "balance": None, "pnl": None, "trades": None,
                       "win_rate": None, "sampled_at": None, "samples": [],
                       "locked": None, "available": None, "config": None,
                       "activity": []}
                bots[instance] = {"room": room, "bot": bot, "marks": [
                    (str(intent.get("at") or ""), (outcome or {}).get("is_trading"))]}
                if room in panels:
                    panels[room]["clones"].append(bot)
        else:
            owner = bots.get(intent.get("instance_id"))
            room = linked.get(cid) or (owner["room"] if owner else store.GENERAL)
            if kind == "fund":
                balance = response.get("bot_balance")
                text = f"{cid} · fund {_amount(intent.get('amount'))} USDC"
                if said != "accepted":
                    text += f" · {_said(outcome)}"
                else:
                    if balance is not None:
                        text += f" · bot balance {_amount(balance)}"
                    if owner:
                        owner["bot"]["funded"] += _num(intent.get("amount")) or 0.0
            elif kind in ("enable", "disable"):
                switched = "on" if kind == "enable" else "off"
                text = f"{cid} · trading switched {switched}"
                if said != "accepted":
                    text += f" · {_said(outcome)}"
                elif owner:
                    owner["marks"].append((str(intent.get("at") or ""),
                                           kind == "enable"))
            else:
                text = f"{cid} · {kind} · {_said(outcome)}"
        place(room, {"kind": "leg", "id": cid, "at": intent.get("at"),
                     "text": text, "outcome": said}, intent.get("at"), 0)

    # The bot's readings: the old ones clone.py watch left in clones.jsonl and
    # the console sampler's in samples.jsonl, one series in time order.
    readings = [r for r in clone_rows if r.get("type") == "sample"] + [
        r for r in sampled if r.get("type") == "sample" and r.get("kind") == "bot"]
    for row in sorted(readings, key=lambda r: str(r.get("at") or "")):
        owner = bots.get(row.get("instance_id"))
        if owner is None:
            continue
        reading = {"at": row.get("at"), "balance": _num(row.get("balance_usdc")),
                   "pnl": _num(row.get("total_profit_usdc")),
                   "trades": row.get("trades_executed"),
                   "trading": row.get("is_trading")}
        owner["bot"]["samples"].append(reading)
        owner["bot"].update(balance=reading["balance"], pnl=reading["pnl"],
                            trades=reading["trades"],
                            win_rate=_num(row.get("win_rate")),
                            sampled_at=reading["at"])
        if "locked_usdc" in row:
            owner["bot"].update(locked=_num(row.get("locked_usdc")),
                                available=_num(row.get("available_usdc")))
        owner["marks"].append((str(row.get("at") or ""), row.get("is_trading")))
    # What only the sampler reads: the bot's configuration and its own trades,
    # each as the newest version on record.
    newest_trade: dict[str, dict] = {}
    for row in sampled:
        owner = bots.get(row.get("instance_id"))
        if owner is None:
            continue
        if row.get("type") == "config":
            owner["bot"]["config"] = {k: row.get(k) for k in (
                "strategy_type", "risk_profile", "primary_indicators",
                "secondary_indicators", "execution_class")}
        elif row.get("type") == "trade" and row.get("trade_id"):
            newest_trade[row["trade_id"]] = row
    for row in newest_trade.values():
        bots[row["instance_id"]]["bot"]["activity"].append(
            {k: row.get(k) for k in ("trade_id", "symbol", "side", "trade_type",
                                     "amount_usdc", "profit_usdc", "is_closed",
                                     "exit_reason", "executed_at", "closed_at")})
    # Switched on at one moment and stopped by itself at a later one: the
    # newest reading of whether it trades is the one that is true.
    for owner in bots.values():
        known = [mark for mark in owner["marks"] if mark[1] is not None]
        if known:
            owner["bot"]["trading"] = max(known, key=lambda mark: mark[0])[1]
        owner["bot"]["activity"].sort(key=lambda a: str(a.get("executed_at") or ""),
                                      reverse=True)

    # Each of our positions as the sampler last read it, and its card's index.
    live_positions: dict[str, dict] = {}
    index_points: dict[str, dict] = {}
    for row in sampled:
        if row.get("type") == "sample" and row.get("kind") == "position":
            live_positions[row.get("position_id")] = row
        elif row.get("type") == "index" and row.get("card_id"):
            points = index_points.setdefault(row["card_id"], {})
            for point in row.get("points") or []:
                if isinstance(point, list) and len(point) == 2:
                    points[str(point[0])] = _num(point[1])
    for panel in panels.values():
        for trade in panel["trades"]:
            live = live_positions.get(trade["position"])
            if live:
                trade.update(live_status=live.get("status"),
                             current_index=_num(live.get("current_index")),
                             unrealized=_num(live.get("unrealized_pnl_usdc")),
                             live_value=_num(live.get("current_value_usdc")),
                             live_at=live.get("at"))
            points = index_points.get(trade["card"]) or {}
            trade["series"] = [[t, points[t]] for t in sorted(points)][-400:]

    # Nexus's proposal under what was done, and each card by what it holds.
    plans = store.plans(stored)
    described: dict[str, dict] = {}
    for row in sampled:
        if row.get("type") == "card" and row.get("card_id"):
            described[row["card_id"]] = row
    answered_at = {q["id"]: q["answer"].get("at") for q in derived if q.get("answer")}
    for s in opened:
        _lay_out(panels[s["id"]], plans.get(s["id"]) or {}, described, index_points,
                 answered_at.get(s.get("origin")))

    for row in stored:
        kind = row.get("type")
        if kind not in store.NOTE_TYPES or row.get("id") in inside:
            continue
        message = {"kind": kind, "id": row.get("id"), "at": row.get("at"),
                   "text": row.get("text") or "", "re": row.get("re")}
        if kind == "operator_note":
            message["read"] = store.is_read(row, marks)
        place(row.get("room") or store.GENERAL, message, row.get("at"), 0)

    for thread in threads.values():
        thread.sort(key=lambda m: order[id(m)])

    waiting = store.unread(stored)

    def entry(room: str, title: str, kind: str, origin, status) -> dict:
        thread = threads[room]
        panel = panels.get(room) or {}
        return {"id": room, "title": title, "kind": kind, "origin": origin,
                "status": status, "messages": len(thread),
                "last_at": max((m["at"] for m in thread if m.get("at")),
                               default=None),
                "unread_by_claude": sum(
                    1 for r in waiting if (r.get("room") or store.GENERAL) == room),
                # What the strip across the top says of it, at a glance.
                **{k: panel.get(k) for k in ("holds", "pnl", "pnl_pct", "invested",
                                             "proposed_share", "if_bought_pct",
                                             "criterion", "verdict")}}

    # The paper account as the newest order of ours read it afterwards. Live
    # figures are the sampler's (docs/nexus-rooms-plan.md, P4), not these.
    book = max((r for r in paper if r.get("type") == "after"),
               key=lambda r: str(r.get("at") or ""), default=None) or {}
    # The scoreboard: every experiment, best first, with what it was accepted
    # on and what it came to. This is the answer to "which of his strategies
    # actually made money", which is the whole question the laboratory exists
    # to answer -- and nothing on this page said it before 2026-09-12.
    scoreboard = []
    for s in opened:
        panel = panels[s["id"]]
        said = panel.get("verdict") or {}
        scoreboard.append({
            "room": s["id"], "title": titles[s["id"]],
            "status": panel.get("status"),
            "verdict": said.get("verdict"),
            "return_pct": said.get("return_pct"),
            "benchmark_pct": said.get("benchmark_pct"),
            "drawdown_pct": said.get("max_drawdown_pct"),
            "pnl": panel.get("pnl"), "pnl_pct": panel.get("pnl_pct"),
            "criterion": panel.get("criterion"),
            "claim": panel.get("claim")})
    scoreboard.sort(key=lambda row: (
        row["return_pct"] is None, -(row["return_pct"] or 0)))

    general = {**_nexus_summary(derived), "strip": [q["outcome"] for q in derived],
               "balance": _num(book.get("sim_balance_usdc")),
               "notional": _num(book.get("notional_usdc")),
               "book_trades": book.get("sim_total_trades"),
               "balance_at": book.get("at"), "scoreboard": scoreboard, **sampler}
    return {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "rooms": [entry(store.GENERAL, "General", "general", None, None)]
            + [entry(s["id"], titles[s["id"]], "strategy", s.get("origin"),
                     panels[s["id"]]["status"]) for s in opened],
            "threads": threads,
            "panels": {store.GENERAL: general, **panels}}


def _rewards() -> dict:
    """What their tracker says we have been paid, and what is still pending.

    From `our_reports`, not from the 20-row public feed: that one carries
    `paid_at` and ours does not, but it is a page of everybody's reports and
    six of ours are not on it. A day axis therefore uses the day they resolved
    the report, and says so on the page.
    """
    bounty = load("bounty.json")
    reports = ((bounty.get("our_reports") or {}).get("reports")
               or bounty.get("reports") or [])
    by_status: dict[str, list[dict]] = {}
    for report in reports:
        by_status.setdefault(str(report.get("status")), []).append(report)
    paid = by_status.get("paid", [])
    pending = by_status.get("fixed", []) + by_status.get("validated", [])
    per_day: dict[str, int] = {}
    for report in paid:
        day = str(report.get("fixed_at") or report.get("validated_at")
                  or report.get("created_at") or "")[:10]
        if day:
            per_day[day] = per_day.get(day, 0) + int(report.get("reward_amount") or 0)
    # Their own two figures, held beside ours. This computed everything from
    # the rows it happened to hold and compared none of it to what THEY say,
    # so a my-reports read that windowed to 20 of 44 would have printed "20,000
    # paid" beside their 37,000 with nothing failing and nothing on the page
    # saying why -- the report-#52 shape that `qa/measure.collection_size`
    # exists to prevent. Found by a check-auditor 2026-09-10, confirmed 3/3.
    #
    # Reported rather than reconciled: which of the two is right is not
    # something this renderer can know, and a page that silently picks one is
    # worse than a page that shows the gap.
    leaderboard = (bounty.get("leaderboard") or [{}])[0]
    theirs = leaderboard.get("total_paid")
    rows_total = sum(int(r.get("reward_amount") or 0) for r in paid)
    server_n = (bounty.get("our_reports") or {}).get("total")
    return {
        "currency": leaderboard.get("reward_currency") or "ET10",
        "paid_n": len(paid),
        "paid_total": rows_total,
        "pending_n": len(pending),
        "invalid_n": len(by_status.get("invalid", [])),
        "by_day": [{"day": d, "amount": n} for d, n in sorted(per_day.items())],
        # None when they publish no figure; a number we can disagree with is
        # better than a number nobody checked, and no figure is neither.
        "their_total": None if theirs is None else float(theirs),
        "rows_read": len(reports),
        "rows_they_hold": None if server_n is None else int(server_n),
        "disagrees": bool(
            (theirs is not None and abs(float(theirs) - rows_total) > 0.01)
            or (server_n is not None and int(server_n) != len(reports))),
    }


def _test_counts() -> dict:
    """How many checks measure them, and how many measure us.

    Counted off the files, because every number anybody has quoted for this
    came from a different command -- `grep -c "^def test_"` said 283 where
    `--collect-only` said 473 -- and the interesting ratio is not the one
    either of them measures.
    """
    theirs, ours, by_dir = 0, 0, {}
    for path in sorted((REPO_ROOT / "tests").rglob("test_*.py")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        n = sum(1 for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name.startswith("test_"))
        group = "/".join(rel.split("/")[:2])
        by_dir[group] = by_dir.get(group, 0) + n
        if rel.startswith(SELF_TEST_DIRS):
            ours += n
        else:
            theirs += n
    return {"vendor_facing": theirs, "self_tests": ours,
            "by_dir": [{"dir": d, "n": n} for d, n in sorted(by_dir.items())]}


def _fomo_stats() -> dict | None:
    """FOMO Radar's `hot` signal, measured: does it predict a memecoin
    moving? Local diary only -- `scripts/fomo_watch.py` is what calls their
    API. None when the diary has never been written, so the page can tell
    "never watched" from "watched and found nothing"."""
    from qa.state import state_dir

    path = state_dir() / "fomo_signals.jsonl"
    if not path.is_file():
        return None
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)

    from qa.fomo import stats

    return stats(rows)


def _process_rows() -> list[dict]:
    """One row per deep pass, or nothing when git cannot answer."""
    try:
        spec = importlib.util.spec_from_file_location(
            "deep_pass_process", REPO_ROOT / "scripts" / "deep_pass_process.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # `series()`, not `versions()`: the row this panel draws is about the
        # pass that is doing the rendering, and that pass cannot have committed
        # its own finish yet. Reading committed history alone is what left rule
        # 12's guard red on `main` from 23:04 to 23:15 on 2026-09-12, and would
        # do so after every pass.
        return module.passes(module.series())
    except Exception:  # noqa: BLE001 -- no git, no history, no panel
        return []


def _last_change(row: dict) -> dict:
    """When this row last moved, on either axis, and from what to what.

    The operator ran a sweep, six rows closed, and they vanished out of the
    open filter with nothing on the page saying which six or when: *"neni tam
    zaden cas zmeny posledni videt"*. Every transition the fold writes carries
    `at`; none of them reached the payload.

    Both axes, because a row that closed because THEY answered moved only on
    the filing axis and disappears from the filter exactly as loudly. A row
    nothing has moved falls back to the day it was first seen, so sorting by
    change puts it where it belongs instead of at the top with an empty cell.
    """
    transitions = [t for t in (row.get("transitions") or []) if t.get("at")]
    if not transitions:
        return {"at": (row.get("first_seen") or {}).get("at"),
                "axis": None, "from": None, "to": None}
    newest = max(transitions, key=lambda t: str(t["at"]))
    return {"at": newest["at"], "axis": newest.get("axis"),
            "from": newest.get("from"), "to": newest.get("to")}


def _owed(row: dict) -> list[str]:
    """What this row still owes somebody, in words.

    The fold computes `obligations` on every row and the CLI prints them
    ("OWED: reverify"). The page did not, so rule 11 -- "a withdrawal prints
    its debts; the row shows 'retraction owed on #N' until a retraction-sent
    event clears it" -- was written down and never built, and the two rows
    owing a re-verify today said so nowhere an operator looks.

    Same shape as rule 8's stale mark, found the same way: a field the fold
    writes that nothing reads.
    """
    obligations = row.get("obligations") or {}
    out: list[str] = []
    if obligations.get("reverify"):
        out.append("re-verify owed")
    if obligations.get("repair_check"):
        out.append("check repair owed")
    for report_id in obligations.get("reopen") or []:
        out.append(f"reopen #{report_id}")
    for report_id in obligations.get("retractions") or []:
        out.append(f"retraction owed on #{report_id}")
    return out


def _summary(row: dict) -> str | None:
    """What this finding says, in one sentence."""
    detail = row.get("detail") or {}
    reason = (detail.get("reason") or "").strip()
    if reason:
        return reason
    note = (row.get("note") or "").strip()
    return note or None


def out_path() -> Path:
    from qa.state import state_dir

    override = __import__("os").environ.get("QA_STATE_DIR")
    return (state_dir() / "dashboard" / "index.html") if override else OUT


def build_payload(ledger: dict | None = None, inventory: dict | None = None,
                  thread: dict | None = None, run: dict | None = None) -> dict:
    """Everything the page shows, derived and reconciled before it is shown.

    This used to REFUSE, with `allow_stale_head` as the way past it, when the
    ledger cited anything but the journal's current head. Every caller that
    matters passed the escape -- the console on its watch loop, both repo
    guards, the render tests -- so the refusal reached nobody but the CLI,
    which is preceded by a fold anyway. Meanwhile the console appends two
    vendor_read events a quarter-hour, and the fold reads those only to set or
    clear stale_from.

    Whether the ledger is WHAT ITS INPUTS FOLD TO is asked, of the rows, by
    scripts/ledger.py::drift. What is left for the page is to SAY what it is a
    view of, and the masthead now does: "state as of journal event N", from the
    ledger's own head and never from the journal's. The page may not claim more
    than the ledger knows, and the number moves when a fold moves it.

    The arguments exist so this can be exercised without the committed state
    directory. Passing none of them reads the repository, which is what
    __main__ does.
    """
    from qa.fold import display_state
    from qa.state import head, load_run

    from qa.state import read_events

    inventory = inventory if inventory is not None else load("inventory.json")

    # Message counts come from the journal, not from thread.json. That file is
    # a scan of outbox/ and inbox/, and once round 1 was moved to archive/ it
    # reported zero messages sent -- while three had been. Correspondence is
    # events now, and an event does not care where the file ended up.
    events = read_events()
    if thread is None:
        # `by`, not just the type. `message` was ours in round one and has been
        # the vendor's a2a inbox since 2026-09-07, so counting the type alone
        # read "messages sent / received 43 / 1" while 40 of the 43 were theirs
        # -- the one number on this page about correspondence, wrong in the
        # flattering direction. Their messages are counted as received.
        # Telegram is deliberately absent from both sides: the operator ruled
        # that channel off this page on 2026-09-08, and a count is still the
        # page. tests/meta/test_pipeline_correspond.py holds that line.
        sent = [e for e in events
                if e["type"] == "message" and e.get("by") != "vendor"]
        heard = [e for e in events
                 if e["type"] == "reply"
                 or (e["type"] == "message" and e.get("by") == "vendor")]
        thread = {"counts": {
            "sent": len(sent),
            "received": len(heard),
            "undelivered": sum(1 for e in sent if not e.get("delivered")),
        }}

    # The ledger, not the current run, is the source of truth for findings.
    # A finding whose check has started passing must still appear -- as
    # VERIFIED FIXED, the one state that means "we checked" rather than "they
    # said". Deriving the list from what is currently failing would delete
    # exactly the records worth keeping.
    from scripts.ledger import as_findings, load_previous
    current = head()
    if ledger is None:
        # No ledger at all is not a stale projection -- it is a repository
        # that has not folded one yet, and an empty page is the honest view.
        ledger = load_previous() or {"findings": {}, "events_head": current}

    # The page describes the run the LEDGER was composed from, not whatever
    # record is newest. A two-test re-run of tests/repo/ is a perfectly valid
    # record and would otherwise have become the run of record for every
    # per-section count on the page -- the partial-run problem, reappearing in
    # the display layer after being closed in the fold.
    if run is None:
        composed = ledger.get("run_id")
        try:
            run = load_run(composed) if composed else {}
        except KeyError:
            run = {}

    # Per-row correspondence, rebuilt from the journal. The rewrite moved
    # reports onto `filing.reports` and messages into events, but the page was
    # still reading `f.filed`, `f.thread`, `f.undelivered` and
    # `f.withdrawn_reason` -- fields no row carries any more. The result was a
    # tile reading "0 filed to their tracker" beside eleven filed reports, and
    # the Correspondence panel empty on every row. Same class as the display
    # state: the page read a field the fold had stopped writing.
    sent, replied = _api_conversation()
    withdrawn_reason: dict[str, str] = {}
    filed_at: dict[int, str] = {}
    for event in events:
        etype = event.get("type")
        if etype == "withdraw" and event.get("finding_id"):
            withdrawn_reason[event["finding_id"]] = event.get("reason") or ""
        elif etype == "filing_outcome" and event.get("outcome") == "accepted":
            filed_at.setdefault(event.get("report_id"), event.get("at"))

    rows = as_findings(ledger)
    findings = []
    display_counts: dict[str, int] = {}
    timeline = []

    for row in rows:
        shown = display_state(row)
        display_counts[shown] = display_counts.get(shown, 0) + 1

        adjudicated = (row.get("check") or {}).get("adjudicated_by")
        row_checks = row.get("checks") or []
        findings.append({
            # Named, not splatted. `**row` shipped the whole ledger row and
            # the page read eight of its fields; the other eleven rode along
            # unread, which is how `stale_from` could be written for a month
            # and displayed never. A payload field is a promise that something
            # renders it, and test_the_page_renders_every_field_it_is_given
            # holds this list to that.
            "id": row["id"],
            "title": row.get("title"),
            "headline": _headline(row),
            "severity": row.get("severity"),
            "tag": row.get("tag"),
            "note": row.get("note"),
            "checks": row_checks,
            "detail": row.get("detail"),
            "regressions": row.get("regressions") or [],
            "display_state": shown,
            "last_change": _last_change(row),
            "first_seen_at": (row.get("first_seen") or {}).get("at"),
            # The verification sentence is printed from THIS, or not at all.
            # Ten rows read VERIFIED FIXED with verified_by_run null on every
            # one, beneath a sentence claiming we had re-run the check.
            "verification": (
                {"run_id": adjudicated["run_id"], "at": adjudicated.get("at"),
                 "nodeid": row_checks[0] if row_checks else None}
                if adjudicated and adjudicated.get("run_id")
                and shown == "VERIFIED FIXED" else None
            ),
            # Set by the fold on any row this run did not adjudicate. On a
            # terminal row it is noise -- nobody re-runs a withdrawal -- so it
            # is dropped there and printed everywhere else, beside the time
            # the row WAS last measured. Without this the open-only sweep
            # would show 29 rows of last week's readings under a fresh
            # header, which is precisely the 71-of-109 failure.
            "not_checked_in": (
                (row.get("check") or {}).get("not_checked_in")
                if shown not in ("WITHDRAWN", "SUPERSEDED") else None
            ),
            "last_checked_at": (adjudicated or {}).get("at"),
            # Rule 8's other half. The fold marks every row stale when a read
            # of their tracker fails, so that "they have said nothing since"
            # is never confused with "we could not hear them" -- and until
            # now nothing displayed it, which made the mark a write nobody
            # read. A terminal row is excluded for the same reason
            # not_checked_in is: nothing about their tracker can change it.
            "stale_from": (
                (row.get("filing") or {}).get("stale_from")
                if shown not in ("WITHDRAWN", "SUPERSEDED") else None
            ),
            # Critique gap 5: content carried over from the hand-written
            # ledger quotes figures frozen at their last failing values.
            #
            # Shown only where it is ACTIONABLE -- a row with a working check
            # that has not run again yet. On a withdrawn row it is noise, and
            # on an unverifiable one the state already says the stronger
            # thing: nothing can measure this. The operator asked three times
            # what the tag meant, and on those rows the honest answer was
            # "nothing you can do".
            "unmeasured": (not (row.get("provenance") or {}).get("measured_at")
                           and shown not in ("WITHDRAWN", "SUPERSEDED",
                                             "UNVERIFIABLE")),
            "filed": [
                {"report_id": r["report_id"], "status": r.get("status"),
                 "submitted_at": filed_at.get(r["report_id"])}
                for r in (row.get("filing") or {}).get("reports", [])
            ],
            "thread": _thread_for(row, sent, replied, filed_at),
            "withdrawn_reason": withdrawn_reason.get(row["id"]),
            # One sentence, from what the check deliberately measured. The
            # panel used to show left / right / sources / population / reason
            # as a table of field names -- accurate, and unreadable.
            "summary": _summary(row),
            "owed": _owed(row),
        })

        for transition in row.get("transitions", []):
            if transition.get("axis") == "check":
                timeline.append({
                    "finding_id": row["id"], "at": transition["at"],
                    "from": transition.get("from"), "to": transition["to"],
                    "run_id": (transition.get("cause") or {}).get("run_id"),
                })

    timeline.sort(key=lambda e: e["at"])

    # Every row lands in exactly one bucket, and the buckets sum to the rows.
    # The filter said 16, the tiles summed to 6, the ledger held 20.
    assert sum(display_counts.values()) == len(rows), (
        f"display counts {display_counts} do not sum to {len(rows)} rows"
    )

    # The page does `f.severity.split("-")` and `esc(f.title)` unguarded, so
    # one row without either renders no findings AT ALL -- a blank list in the
    # browser with nothing to say why. The fold only guarantees them at
    # creation, via setdefault inside the candidate loop, so a row seeded by
    # the migration without one would never acquire it. Fail here instead,
    # loudly and with the row named: a render that stops is diagnosable, a
    # page that silently empties is not.
    for finding in findings:
        for field in ("severity", "title"):
            assert finding.get(field), (
                f"{finding['id']} has no {field}, which the page cannot draw "
                f"around -- the whole findings list would come out empty"
            )

    by_severity: dict[str, int] = {}
    for finding in findings:
        if finding["display_state"] not in ("VERIFIED FIXED", "WITHDRAWN"):
            by_severity[finding["severity"]] = by_severity.get(
                finding["severity"], 0) + 1

    # One list, and the count read off it. They were two computations over the
    # same results and the count included every phase of every check, so a
    # tile could say more checks than it could name.
    tests_by_section = _tests_by_section(run)
    checks: dict[str, dict[str, int]] = {}
    for section, tests in tests_by_section.items():
        bucket = checks.setdefault(
            section, {"passed": 0, "failed": 0, "inconclusive": 0, "total": 0})
        for test in tests:
            bucket["total"] += 1
            if test.get("outcome") in bucket:
                bucket[test["outcome"]] += 1

    # From the LEDGER row, which carries `section`, not from the projection
    # above, which deliberately does not. Reading it off the projection meant
    # this was [] on all 22 sections: no tile ever turned red for a finding,
    # and the severity chips the legend promises were never drawn.
    by_section: dict[str, list[str]] = {}
    for row in ledger.get("findings", {}).values():
        if display_state(row) in ("VERIFIED FIXED", "WITHDRAWN", "SUPERSEDED"):
            continue
        targets = set(row.get("affected_sections") or []) | {row.get("section")}
        for section in targets:
            if section:
                by_section.setdefault(section, []).append(row.get("severity"))

    sections = [
        {**s,
         "checks": checks.get(s["id"], {}),
         "tests": tests_by_section.get(s["id"], []),
         "finding_severities": by_section.get(s["id"], [])}
        for s in inventory.get("sections", [])
    ]

    groups = [
        {"tag": tag, "title": TAGS[tag][0], "blurb": TAGS[tag][1],
         "sections": TAGS[tag][2]}
        for tag in TAG_ORDER
    ]

    from qa.fold import CHECK_STATES, DISPLAY, FILING_STATES
    from qa.state import admissibility

    # The legend's diagram is generated from the real composition table, not
    # written out beside it. A hand-drawn legend is a second source of truth
    # for the thing this whole rebuild exists to keep single.
    composition = {
        "check_states": [c for c in CHECK_STATES if c != "CHECK_CHANGED"],
        "filing_states": [f for f in FILING_STATES if f not in ("WITHDRAWN", "SUPERSEDED")],
        "terminal": ["WITHDRAWN", "SUPERSEDED"],
        "table": {c: {f: DISPLAY[(c, f)] for f in FILING_STATES}
                  for c in CHECK_STATES},
    }

    verdict = admissibility(run) if run else None
    return {
        "composition": composition,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run_id": run.get("run_id"),
        # When the run that adjudicated this page actually ran -- not when the
        # page was generated. The header used to print the generation moment,
        # which moves every time the console re-renders and says nothing about
        # how fresh the measurements are.
        "run_at": run.get("finished_at") or run.get("started_at"),
        # Critique gap 8: "V" and "V (partial identity)" are different claims
        # about how much of the ladder this run could reach.
        "run_level": verdict.label if verdict else "none",
        "run_notes": verdict.notes if verdict else [],
        "fingerprint": (run.get("platform_fingerprint") or "")[:23],
        "events_head": ledger.get("events_head"),
        "totals": inventory.get("totals", {}),
        "sections": sections,
        "stats": _stats(ledger, run, events),
        "help": {"models": _help_models(), "source": "CLAUDE.md"},
        "findings": findings,
        "display_counts": display_counts,
        "timeline": timeline,
        "by_severity": by_severity,
        "groups": groups,
        "thread_counts": thread.get("counts", {}),
    }


TEMPLATE = r"""<title>Cymetica QA Console</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>
/* The browser's own [hidden] rule is display:none at UA specificity, which
   ANY class selector beats. `.newreply { display:inline-flex }` did exactly
   that: setting el.hidden = true set the attribute and changed nothing on
   screen, so "Mark all as read" cleared the badge and left every envelope
   drawn. Published as an Artifact this never showed, because that runtime
   injects this very rule; served raw from localhost, nothing did.
   One line, first, so no later class can win against it. */
[hidden] { display: none !important; }

:root {
  --bg:#f6f7f6; --surface:#ffffff; --surface-2:#eef1f0; --line:#d5dbd9;
  --line-soft:#e6eae9; --text:#10171a; --text-dim:#5a6a6c; --text-faint:#8b9a9b;
  --accent:#0d6b66; --accent-dim:#0d6b6622;
  --ok:#17803d;   --ok-bg:#17803d1f;
  --auth:#0e7490; --auth-bg:#0e74901f;
  --warn:#9a6300; --warn-bg:#9a63001f;
  --bad:#b3261e;  --bad-bg:#b3261e1f;
  --wait:#6b3fc4; --wait-bg:#6b3fc41f;
  --none:#9aa8a8; --none-bg:#9aa8a826;
  --radius:7px;
  --mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
  --sans:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg:#0c1214; --surface:#121b1d; --surface-2:#182326; --line:#243436;
    --line-soft:#1b282a; --text:#e4ecea; --text-dim:#93a5a5; --text-faint:#6a7b7c;
    --accent:#4ecfc4; --accent-dim:#4ecfc422;
    --ok:#4ec97a; --ok-bg:#4ec97a1f; --auth:#45b8d6; --auth-bg:#45b8d61f;
    --warn:#e0a338; --warn-bg:#e0a3381f; --bad:#f2685e; --bad-bg:#f2685e1f;
    --wait:#a98cf0; --wait-bg:#a98cf01f; --none:#647476; --none-bg:#64747626;
  }
}
:root[data-theme="dark"] {
  --bg:#0c1214; --surface:#121b1d; --surface-2:#182326; --line:#243436;
  --line-soft:#1b282a; --text:#e4ecea; --text-dim:#93a5a5; --text-faint:#6a7b7c;
  --accent:#4ecfc4; --accent-dim:#4ecfc422;
  --ok:#4ec97a; --ok-bg:#4ec97a1f; --auth:#45b8d6; --auth-bg:#45b8d61f;
  --warn:#e0a338; --warn-bg:#e0a3381f; --bad:#f2685e; --bad-bg:#f2685e1f;
  --wait:#a98cf0; --wait-bg:#a98cf01f; --none:#647476; --none-bg:#64747626;
}

* { box-sizing:border-box; }
body {
  margin:0; background:var(--bg); color:var(--text); font-family:var(--sans);
  font-size:16.5px; line-height:1.55; -webkit-font-smoothing:antialiased;
}
.wrap { max-width:1240px; margin:0 auto; padding:32px 22px 80px; }

.mast { border-bottom:2px solid var(--text); padding-bottom:14px; }
.mast h1 {
  font-size:clamp(26px,4vw,38px); font-weight:600; letter-spacing:-0.022em;
  margin:0 0 4px; text-wrap:balance;
}
.mast .sub { color:var(--text-dim); font-size:16.0px; max-width:70ch; margin:0; }
.meta {
  display:flex; flex-wrap:wrap; gap:6px 20px; margin-top:14px;
  font-family:var(--mono); font-size:13.0px; color:var(--text-faint);
}
.meta b { color:var(--text-dim); font-weight:500; }

.triage {
  display:grid; grid-template-columns:repeat(auto-fit,minmax(132px,1fr)); gap:1px;
  background:var(--line); border:1px solid var(--line); border-radius:var(--radius);
  overflow:hidden; margin:26px 0 6px;
}
.tri { background:var(--surface); padding:13px 15px; }
.tri .n {
  font-family:var(--mono); font-size:27px; font-weight:600; line-height:1.1;
  font-variant-numeric:tabular-nums;
}
.tri .l {
  font-size:12.0px; text-transform:uppercase; letter-spacing:0.09em;
  color:var(--text-faint); margin-top:3px; font-weight:600;
}
.tri.s0 .n,.tri.s1 .n { color:var(--bad); }
.tri.s2 .n,.tri.s3 .n { color:var(--warn); }
.tri.s4 .n { color:var(--text-dim); }
.tri.ok .n { color:var(--ok); }

h2.group {
  font-size:13.5px; text-transform:uppercase; letter-spacing:0.13em;
  font-weight:700; margin:38px 0 3px; display:flex; align-items:center; gap:10px;
}
.tagchip {
  font-family:var(--mono); font-size:11.5px; font-weight:600; letter-spacing:0.06em;
  padding:3px 7px; border-radius:4px; background:var(--accent-dim);
  color:var(--accent); white-space:nowrap;
}
p.group-note { margin:0 0 15px; color:var(--text-dim); font-size:15.0px; max-width:74ch; }

/* align-items:start, so opening one card does not stretch every other card
   in its row to the same height -- which is what made one open tile look
   like the whole row had come apart. */
.grid {
  display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr));
  gap:12px; align-items:start;
}
.card {
  background:var(--surface); border:1px solid var(--line); border-radius:var(--radius);
  padding:15px 16px 14px; border-left:3px solid var(--none);
}
/* The card is a <details> now, so the column layout lives on the summary --
   display:flex on a details element breaks the open/closed flow. */
.card > summary { display:flex; flex-direction:column; gap:10px; }
.card.h-ok{border-left-color:var(--ok)} .card.h-warn{border-left-color:var(--warn)}
.card.h-bad{border-left-color:var(--bad)} .card.h-none{border-left-color:var(--none)}
.card-top { display:flex; align-items:baseline; justify-content:space-between; gap:12px; }
.card h3 { margin:0; font-size:16.0px; font-weight:600; letter-spacing:-0.01em; }
.pct {
  font-family:var(--mono); font-size:25px; font-weight:600; line-height:1;
  font-variant-numeric:tabular-nums; white-space:nowrap;
}
.pct.h-ok{color:var(--ok)} .pct.h-warn{color:var(--warn)} .pct.h-bad{color:var(--bad)}
.pct.h-none{color:var(--text-faint); font-size:14.5px}
.pct small { font-size:13.5px; font-weight:500; color:var(--text-faint); }

.bar { display:flex; height:7px; border-radius:3px; overflow:hidden; background:var(--surface-2); }
.bar span { display:block; }
.seg-ok{background:var(--ok)} .seg-auth{background:var(--auth)}
.seg-param{background:var(--auth);opacity:.6} .seg-method{background:var(--warn)}
.seg-missing{background:var(--bad)}
.rely{display:grid;gap:.55rem;margin:.5rem 0 .7rem}
.rely-row{display:grid;grid-template-columns:8.5rem 1fr 5rem;align-items:center;gap:.8rem}
.rely-name{font-weight:600}
.rely-name span,.rely-n span{display:block;font-weight:400;font-size:.78em;opacity:.6}
.rely-n{text-align:right;font-size:1.2em}
.rely-strip{display:flex;flex-wrap:wrap;gap:3px}
.sq{display:inline-block;width:14px;height:14px;border-radius:3px;background:var(--line)}
.sq.answered{background:var(--ok)} .sq.partial{background:var(--warn)}
.sq.failed{background:var(--bad)} .sq.refused{background:var(--line)}
.sq.waiting{background:transparent;box-shadow:inset 0 0 0 2px var(--warn)}
.rely-legend{display:flex;flex-wrap:wrap;gap:.3rem .9rem;align-items:center;font-size:.8em;opacity:.8}
.rely-legend .sq{width:10px;height:10px;margin-right:.3rem;vertical-align:-1px}
.rely-axis{width:100%;max-width:780px;display:block;margin:.4rem 0 .2rem}
.cov{display:grid;grid-template-columns:repeat(auto-fill,minmax(8.5rem,1fr));gap:6px;margin-top:.7rem}
.cov-cell{border-radius:6px;padding:.45rem .55rem;min-height:3.2rem;background:var(--surface-2);border:1px solid var(--line)}
.cov-cell b{display:block;font-size:1.3em;min-height:1.2em}
.cov-cell span{font-size:.78em;opacity:.8}
.cov-cell.ok{background:var(--ok-bg);border-color:var(--ok)}
.cov-cell.bad{background:var(--bad-bg);border-color:var(--bad)}
.cov-cell.none{opacity:.5}
/* The Nexus tab: a strip of named strategies across the top; under it the chat
   with Nexus on the left and, beside it, the strategy's numbers, chart and
   configuration. It takes the whole width while it is shown
   (.wrap[data-tab="nexus"]), and both columns scroll on their own, so the
   composer is always under the thread and never over it -- it once floated
   over it, sticky, and the operator said so. Ours and the operator's messages
   sit on the right like any chat, Nexus on the left. Every class is nx- so
   nothing here can restyle the findings' own conversation. */
.wrap[data-tab="nexus"]{max-width:none;padding-left:28px;padding-right:28px}
.nx-strip{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:12px;margin:18px 0 16px}
.nx-card{position:relative;display:flex;flex-direction:column;gap:5px;min-width:0;text-align:left;padding:12px 15px 13px;border:1px solid var(--line);border-radius:12px;background:var(--surface);color:var(--text);font:inherit;cursor:pointer}
.nx-card:hover{border-color:var(--text-faint)}
.nx-card.on{border-color:var(--accent);box-shadow:inset 0 0 0 1px var(--accent)}
.nx-card-top{display:flex;align-items:center;gap:8px;min-width:0;font-size:12.5px;color:var(--text-dim);white-space:nowrap;overflow:hidden}
.nx-card-name{font-size:17px;font-weight:600;line-height:1.25;overflow-wrap:anywhere}
.nx-card-num{font-size:15px;font-weight:600;color:var(--text-dim)}
.nx-badge{position:absolute;top:10px;right:12px;background:var(--accent);color:var(--surface);border-radius:9px;padding:0 .45rem;font-size:.75em;font-weight:600}
.nx-main{display:grid;grid-template-columns:minmax(360px,2fr) minmax(0,3fr);gap:18px;height:calc(100vh - 48px);min-height:480px}
.nx-chatcol{display:flex;flex-direction:column;min-width:0;min-height:0;border:1px solid var(--line);border-radius:12px;background:var(--surface);overflow:hidden}
.nx-chat{flex:1 1 auto;min-height:0;overflow-y:auto;padding:18px 18px 22px;display:flex;flex-direction:column;gap:14px}
.nx-compose{flex:none;display:flex;flex-direction:column;gap:6px;padding:12px 14px;border-top:1px solid var(--line);background:var(--surface-2)}
.nx-compose textarea{width:100%;box-sizing:border-box;resize:vertical;min-height:3.2em;font:inherit;color:var(--text);background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:.5rem .65rem}
.nx-send{display:flex;justify-content:space-between;align-items:center;gap:.6rem;font-size:.8em;color:var(--text-dim)}
.nx-send button{font:inherit;font-size:1.15em;padding:.3rem .9rem;border-radius:6px;border:1px solid var(--wait);background:var(--wait);color:var(--surface);cursor:pointer}
.nx-send button:disabled{opacity:.5;cursor:default}
.nx-panel{min-width:0;min-height:0;overflow-y:auto;border:1px solid var(--line);border-radius:12px;background:var(--surface);padding:22px 26px 26px}
@media (max-width:1100px){.nx-main{grid-template-columns:1fr;height:auto}.nx-chatcol{height:75vh}.nx-panel{overflow:visible}}
.nx-note{margin-top:14px;padding:.7rem .9rem;border:1px dashed var(--line);border-radius:var(--radius);color:var(--text-dim)}
.nx-msg{border:1px solid var(--line);border-radius:14px;padding:.75rem .95rem;background:var(--surface);max-width:min(52rem,90%);align-self:flex-start}
.nx-msg.nx-ours{align-self:flex-end;background:var(--accent-dim);border-color:var(--accent)}
.nx-msg.nx-op{align-self:flex-end;background:var(--wait-bg);border-color:var(--wait)}
.nx-msg.nx-cl{background:var(--surface-2)}
.nx-msg.nx-sys{align-self:center;max-width:92%;border:none;background:none;padding:0 1rem;color:var(--text-faint);font-size:.8em;text-align:center}
.nx-msg.nx-failed,.nx-msg.nx-refused{border-color:var(--bad)}
.nx-msg.nx-partial,.nx-msg.nx-waiting{border-color:var(--warn)}
.nx-h{font-size:.78em;color:var(--text-dim);margin-bottom:.4rem}
.nx-h b{color:var(--text);font-weight:600}
.nx-s{font-size:.85em;color:var(--text-dim);font-style:italic}
.nx-b{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.5}
.nx-b.nx-clamp{max-height:9.5em;overflow:hidden;-webkit-mask-image:linear-gradient(#000 65%,transparent);mask-image:linear-gradient(#000 65%,transparent)}
.nx-b code{font-family:var(--mono);font-size:.9em;background:var(--surface-2);padding:0 .2em;border-radius:3px}
.nx-more{margin-top:.35rem;background:none;border:none;color:var(--accent);cursor:pointer;font:inherit;font-size:.82em;padding:0}
.nx-tick{color:var(--ok);margin-left:.3rem}
.nx-st{font-weight:700}
.nx-st.nx-running{color:var(--ok)}
.nx-st.nx-paused{color:var(--warn)}
.nx-st.nx-stopped{color:var(--bad)}
.nx-st.nx-proposed{color:var(--text-dim)}
.nx-gist{margin:.1rem 0 .5rem;padding:.45rem .65rem;border-left:3px solid var(--accent);background:var(--surface-2);border-radius:0 6px 6px 0;font-size:.95em;line-height:1.45}
.nx-gist span{display:block;font-size:.72em;color:var(--text-dim);margin-bottom:.1rem}
.nx-opened{margin-top:.35rem;font-size:.8em}
.nx-goto{background:none;border:none;color:var(--accent);cursor:pointer;font:inherit;padding:0;text-decoration:underline}
.nx-leg.nx-no{color:var(--bad)}
.nx-hero{display:flex;flex-wrap:wrap;align-items:center;gap:10px 12px}
.nx-hero h2{margin:0;font-size:26px;font-weight:600;letter-spacing:-.01em;line-height:1.2;overflow-wrap:anywhere}
.nx-sub{margin:6px 0 0;font-size:13px;color:var(--text-faint)}
.nx-pill{display:inline-flex;align-items:center;gap:6px;padding:3px 11px;border-radius:999px;background:var(--surface-2);color:var(--text-dim);font-size:13px;font-weight:600;white-space:nowrap}
.nx-pill.nx-running{background:var(--ok-bg);color:var(--ok)}
.nx-pill.nx-paused{background:var(--warn-bg);color:var(--warn)}
.nx-pill.nx-stopped{background:var(--bad-bg);color:var(--bad)}
.nx-card-top .nx-pill{padding:1px 8px;font-size:12px}
.nx-tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:20px 0 4px}
.nx-tile{min-width:0;padding:13px 15px;border-radius:10px;background:var(--surface-2)}
.nx-tile span{display:block;font-size:12.5px;color:var(--text-dim)}
.nx-tile b{display:block;margin-top:2px;font-size:26px;font-weight:600;line-height:1.25;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.nx-tile i{display:block;margin-top:2px;font-style:normal;font-size:12.5px;color:var(--text-faint)}
.nx-up{color:var(--ok)}
.nx-down{color:var(--bad)}
.nx-warn{color:var(--warn)}
.nx-sec{margin:28px 0 8px;font-size:12px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--text-faint)}
.nx-table{font-size:14px}
.nx-tr{display:grid;gap:10px;align-items:center;padding:9px 0;border-top:1px solid var(--line-soft)}
.nx-tr > *{min-width:0;overflow-wrap:anywhere}
.nx-tr small{display:block;font-size:12px;color:var(--text-faint)}
.nx-th{border-top:none;padding-top:0;font-size:12.5px;color:var(--text-faint)}
.nx-legs .nx-tr{grid-template-columns:minmax(0,2.3fr) .8fr 1.2fr 1.5fr 1.3fr 1fr}
.nx-trades .nx-tr{grid-template-columns:minmax(0,1.4fr) .8fr .8fr 1.3fr 1.1fr}
.nx-orders .nx-tr{grid-template-columns:.9fr 1.1fr minmax(0,2.2fr) 1fr}
.nx-strats .nx-tr{grid-template-columns:minmax(0,1.8fr) .6fr 1fr .9fr 1fr 1.2fr}
.nx-state{font-size:13px;font-weight:600;color:var(--text-dim)}
.nx-state.nx-open{color:var(--ok)}
.nx-state.nx-card-closed{color:var(--text-faint)}
.nx-state.nx-card-not-found{color:var(--bad)}
.nx-dim{color:var(--text-faint)}
.nx-kv{display:flex;flex-wrap:wrap;gap:8px 28px;font-size:14px}
.nx-kv span{margin-right:6px;color:var(--text-faint)}
.nx-chips{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin-top:10px}
.nx-chips > span{min-width:5.5rem;margin-right:4px;font-size:12.5px;color:var(--text-faint)}
.nx-chip{padding:3px 9px;border-radius:6px;border:1px solid var(--line-soft);background:var(--surface-2);font-family:var(--mono);font-size:12.5px}
.nx-ct{display:flex;justify-content:space-between;align-items:baseline;gap:12px;margin:22px 0 4px;font-size:14px;font-weight:600}
.nx-ct small{font-size:12.5px;font-weight:400;color:var(--text-faint)}
.nx-chart{display:block;max-width:100%;height:auto;overflow:visible}
.nx-chart text{font-size:12px;fill:var(--text-dim)}
.nx-chart .nx-gl{stroke:var(--line-soft);stroke-width:1}
.nx-chart .nx-area{fill:var(--accent-dim);stroke:none}
.nx-chart .nx-line{fill:none;stroke:var(--accent);stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
.nx-chart .nx-ref{stroke-width:1.5;stroke-dasharray:6 4}
.nx-chart .nx-ref-tp{stroke:var(--ok)}
.nx-chart .nx-ref-sl{stroke:var(--bad)}
.nx-chart .nx-ref-entry,.nx-chart .nx-ref-base{stroke:var(--text-dim);stroke-dasharray:2 4}
.nx-chart .nx-tp{fill:var(--ok)}
.nx-chart .nx-sl{fill:var(--bad)}
.nx-chart .nx-now{fill:var(--text);font-weight:600}
.nx-chart .nx-vl{stroke:var(--wait);stroke-width:1.5;stroke-dasharray:3 3}
.nx-chart .nx-vt{fill:var(--wait)}
.nx-chart .nx-dot{fill:var(--accent);stroke:var(--surface);stroke-width:2}
.nx-chart .nx-dot-open{fill:var(--surface);stroke:var(--accent);stroke-width:2}
.nx-chart .nx-dot-loss{fill:var(--bad);stroke:var(--surface);stroke-width:2}
/* Why a strategy stands where it does: under its name, above its numbers,
   coloured by where it stands, and every earlier move under it. */
.nx-status{margin:18px 0 4px;padding:14px 18px 13px;border-radius:10px;background:var(--surface-2);border-left:4px solid var(--accent)}
.nx-status.nx-paused{border-left-color:var(--warn);background:var(--warn-bg)}
.nx-status.nx-stopped{border-left-color:var(--bad);background:var(--bad-bg)}
.nx-status.nx-proposed{border-left-color:var(--text-faint)}
.nx-status h3{margin:0;font-size:12px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--text-dim)}
.nx-status>p{margin:6px 0 0;font-size:16px;line-height:1.55;white-space:pre-wrap}
.nx-moves{display:grid;gap:5px;margin:12px 0 0;padding-top:10px;border-top:1px solid var(--line-soft)}
.nx-moves p{margin:0;font-size:13.5px;line-height:1.5;color:var(--text-dim)}
.nx-moves b{font-weight:600}
/* A card's name opens the card itself on cymetica.com. */
.nx-link{color:inherit;text-decoration:none;border-bottom:1px dotted var(--text-faint)}
.nx-link:hover{color:var(--accent);border-bottom-color:var(--accent)}
.nx-out{font-size:.8em;color:var(--accent)}
.nx-foot{margin:12px 0 0;font-size:12.5px;color:var(--text-faint)}
.nx-stale b{color:var(--bad)}
.nx-pf{padding:0;border:none;background:none;color:var(--text);font:inherit;font-weight:600;text-align:left;cursor:pointer}
.nx-pf:hover{color:var(--accent)}
details.stat summary{cursor:pointer;font-weight:600}
/* Theirs, and counted against them: a 5xx is an answer. */
.seg-server_error{background:var(--bad);opacity:.65}
/* Ours, and counted against nobody: no answer came back at all, which is a
   fact about this machine's network. Hatched like the other exclusions. */
.seg-unreachable{
  background:repeating-linear-gradient(135deg,var(--warn) 0 3px,transparent 3px 7px);
  box-shadow:inset 0 0 0 1px var(--warn);
}
.seg-unprobed,.seg-websocket{
  background:repeating-linear-gradient(135deg,var(--none-bg) 0 4px,transparent 4px 8px);
  box-shadow:inset 0 0 0 1px var(--none-bg);
}
.pct-wrap { display:flex; flex-direction:column; align-items:flex-end; gap:2px; }
.pct-cap {
  font-family:var(--mono); font-size:11.0px; color:var(--text-faint);
  white-space:nowrap; letter-spacing:.02em;
}
.chip.untested {
  color:var(--text-faint); background:transparent;
  border:1px dashed var(--line); font-weight:600;
}
.blurb { font-size:14.1px; color:var(--text-dim); margin:0; line-height:1.5; }
.stats { display:flex; flex-wrap:wrap; gap:5px; font-family:var(--mono); font-size:12.5px; }
.chip {
  border:1px solid var(--line); border-radius:4px; padding:2px 6px;
  color:var(--text-dim); background:var(--surface-2); white-space:nowrap;
}
.chip.bad{color:var(--bad);border-color:transparent;background:var(--bad-bg);font-weight:600}
.chip.warn{color:var(--warn);border-color:transparent;background:var(--warn-bg);font-weight:600}
.chip.ok{color:var(--ok);border-color:transparent;background:var(--ok-bg);font-weight:600}
.chip.none{color:var(--text-faint)}

.filters { display:flex; flex-wrap:wrap; gap:6px; margin:16px 0 14px; align-items:center; }
.filters button {
  font-family:var(--mono); font-size:13.0px; padding:5px 11px; cursor:pointer;
  border:1px solid var(--line); background:var(--surface); color:var(--text-dim);
  border-radius:20px; font-weight:500;
}
.filters button[aria-pressed="true"] { background:var(--text); color:var(--bg); border-color:var(--text); }
.filters button:focus-visible { outline:2px solid var(--accent); outline-offset:2px; }
.filters .sep { width:1px; height:20px; background:var(--line); margin:0 5px; }
.filters .fl {
  font-family:var(--mono); font-size:11.5px; text-transform:uppercase;
  letter-spacing:.06em; color:var(--text-faint); margin-right:2px;
}

.finding {
  background:var(--surface); border:1px solid var(--line);
  border-radius:var(--radius); margin-bottom:9px; overflow:hidden;
}
.finding > summary {
  cursor:pointer; padding:13px 15px; display:grid;
  grid-template-columns:auto 1fr; gap:12px; align-items:start; list-style:none;
}
.finding > summary::-webkit-details-marker { display:none; }
.finding > summary:focus-visible { outline:2px solid var(--accent); outline-offset:-2px; }
.sev {
  font-family:var(--mono); font-size:11.5px; font-weight:600; padding:3px 7px;
  border-radius:4px; letter-spacing:.04em; white-space:nowrap; margin-top:2px;
}
.sev.S0,.sev.S1 { background:var(--bad-bg); color:var(--bad); }
.sev.S2,.sev.S3 { background:var(--warn-bg); color:var(--warn); }
.sev.S4 { background:var(--none-bg); color:var(--text-dim); }
.f-title { font-weight:500; font-size:16.0px; line-height:1.45; }
.f-sub {
  font-family:var(--mono); font-size:12.5px; color:var(--text-faint); margin-top:5px;
  display:flex; flex-wrap:wrap; gap:5px 9px; align-items:center;
}
.state {
  font-family:var(--mono); font-size:11.5px; font-weight:600; padding:2px 6px;
  border-radius:4px; white-space:nowrap;
}
/* Every cell of the composition table gets a colour. Seven of the sixteen
   were styled and three of those seven named states that no longer exist, so
   nine chips -- PASSING (UNPINNED) and WITHDRAWN among them -- rendered as
   plain grey text and were easy to read straight past. A state with no colour
   is a state the eye does not register.

   Grouped by what the operator should DO about it, not by axis:
     red     it reproduces; the defect is live
     amber   waiting on somebody -- them, or a decision of ours
     teal    our check passes, but something short of a verification
     green   verified: our measurement and their claim agree
     grey    we cannot tell
     muted   terminal and ours (struck through) */
.state.s-still-reproducible { background:var(--bad-bg); color:var(--bad); }
.state.s-not-raised-yet     { background:var(--bad-bg); color:var(--bad); }
.state.s-raised             { background:var(--auth-bg); color:var(--auth); }
.state.s-they-replied       { background:var(--wait-bg); color:var(--wait); }
.state.s-fix-claimed        { background:var(--warn-bg); color:var(--warn); }
.state.s-check-changed      { background:var(--warn-bg); color:var(--warn); }
.state.s-passing-never-raised { background:var(--accent-dim); color:var(--accent); }
.state.s-verified-fixed     { background:var(--ok-bg); color:var(--ok); }
.state.s-unverified         { background:var(--none-bg); color:var(--text-dim); }
.state.s-our-check-cannot-tell { background:var(--none-bg); color:var(--text-dim); }
.state.s-never-seen-broken  { background:var(--accent-dim); color:var(--accent); }
.state.s-unverifiable       { background:var(--none-bg); color:var(--text-dim); }
.state.s-withdrawn  { background:var(--none-bg); color:var(--text-faint); text-decoration:line-through; }
.state.s-superseded { background:var(--none-bg); color:var(--text-faint); text-decoration:line-through; }

.filed { font-family:var(--mono); font-size:13.5px; color:var(--text-faint); }

/* ---------- cards open, and the bar says what it means ---------- */
.card > summary { list-style:none; cursor:pointer; }
.card > summary::-webkit-details-marker { display:none; }
.card-more {
  display:inline-block; margin-top:11px; font-family:var(--mono);
  font-size:12.5px; color:var(--accent);
}
.card[open] .card-more { visibility:hidden; }
.blegend {
  display:flex; flex-wrap:wrap; gap:4px 14px; margin:8px 0 0;
  font-size:12.5px; color:var(--text-dim);
}
.blabel { display:flex; align-items:center; gap:5px; }
.blabel i { width:9px; height:9px; border-radius:2px; display:inline-block; }
/* An open tile takes the whole row. It used to expand downward inside a
   300px column -- "rozsiri jen smerem dolu a porad je uzka, takze je to
   takove neprehledne, na cele te strance musim porad hodne dolu scrollovat"
   -- so the two lists sit side by side and the scrolling stops. */
.card[open] { grid-column:1 / -1; }
.card-detail {
  margin-top:14px; padding-top:14px; border-top:1px solid var(--line-soft);
  display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:24px;
  align-items:start;
}
@media (max-width:820px) { .card-detail { grid-template-columns:1fr; } }
.cd-tests, .cd-eps { min-width:0; max-height:56vh; overflow:auto; }
.tlist { list-style:none; margin:0; padding:0; }
.tlist li {
  display:grid; grid-template-columns:1fr auto; gap:2px 10px;
  padding:7px 0; border-bottom:1px solid var(--line-soft);
}
.t-n { font-size:13.5px; color:var(--text); }
.t-o {
  font-family:var(--mono); font-size:11px; text-transform:uppercase;
  letter-spacing:.04em; color:var(--text-faint); justify-self:end;
}
.t-failed .t-o { color:var(--bad); }
.t-passed .t-o { color:var(--ok); }
.t-d, .t-r { grid-column:1 / -1; font-size:12.5px; color:var(--text-dim); }
.t-r { font-family:var(--mono); font-size:11.5px; color:var(--warn); }
.t-gone { color:var(--text-faint); font-style:italic; }
.epgroup { margin-bottom:15px; }
.epgroup-h {
  display:flex; align-items:center; gap:7px; font-size:13.5px; color:var(--text);
  margin-bottom:7px; font-weight:600;
}
.epgroup-h i { width:9px; height:9px; border-radius:2px; display:inline-block; }
.ep { padding:4px 0 4px 16px; border-left:2px solid var(--line-soft); margin:2px 0; }
.ep code { font-family:var(--mono); font-size:13px; color:var(--text-dim); }
.ep-meta {
  display:block; font-family:var(--mono); font-size:12px; color:var(--text-faint);
}

/* ---------- the finding body ---------- */
.f-lede {
  font-size:17.5px; line-height:1.5; color:var(--text); margin:16px 0 4px;
  max-width:80ch;
}
.f-ref { margin-top:20px; border-top:1px solid var(--line-soft); padding-top:14px; }
.f-ref > div {
  display:flex; gap:14px; align-items:baseline; margin:7px 0; flex-wrap:wrap;
}
.ref-k {
  flex:0 0 168px; font-size:13.5px; color:var(--text-faint);
  text-transform:uppercase; letter-spacing:.04em;
}
.ref-v { font-size:15.0px; color:var(--text-dim); min-width:0; word-break:break-word; }
.ref-v.mono { font-family:var(--mono); font-size:14.0px; }
.kvt { border-collapse:collapse; font-size:14.5px; }
.kvt td { padding:1px 14px 1px 0; vertical-align:top; color:var(--text-dim); }
.kvt td:first-child { font-family:var(--mono); font-size:13.5px; color:var(--text-faint); }

/* ---------- the conversation, as a conversation ---------- */
.chat { margin:14px 0; max-width:84%; }
.chat.us { margin-left:auto; }
.chat-meta {
  display:flex; gap:10px; align-items:baseline; font-size:14.0px;
  color:var(--text-dim); margin-bottom:5px;
}
.chat.us .chat-meta { justify-content:flex-end; }
.chat-meta time { font-family:var(--mono); font-size:13.0px; color:var(--text-faint); }
.chat-status {
  font-family:var(--mono); font-size:12.5px; text-transform:uppercase;
  padding:1px 6px; border-radius:4px; background:var(--ok-bg); color:var(--ok);
}
.chat-body {
  border-radius:12px; padding:12px 15px; font-size:16.0px; line-height:1.55;
  border:1px solid var(--line-soft); white-space:normal;
}
.chat.us .chat-body {
  background:var(--accent-dim); border-color:transparent;
  border-bottom-right-radius:3px;
}
.chat.them .chat-body { background:var(--surface-2); border-bottom-left-radius:3px; }
.chat-body p { margin:0 0 9px; }
.chat-body p:last-child { margin-bottom:0; }
.chat-title { font-weight:600; margin-bottom:8px; color:var(--text); }
.chat-quiet { color:var(--text-faint); font-style:italic; }
.chat-note {
  margin:16px 0 0; font-size:15.0px; color:var(--text-dim);
  padding-left:12px; border-left:3px solid var(--line);
}
.chat-note.ok { border-left-color:var(--ok); }
.chat-note.bad { border-left-color:var(--bad); }
.undelivered {
  font-family:var(--mono); font-size:11.5px; font-weight:600; padding:2px 6px;
  border-radius:4px; background:var(--bad-bg); color:var(--bad); white-space:nowrap;
}
/* On 19 of 23 rows, so it must not shout. Red made it the loudest thing on
   the page and pushed the state chip -- the thing actually worth reading --
   into the background. It is a provenance note, not an alarm. */
.unmeasured, .unmeasured-demo {
  font-family:var(--mono); font-size:11.5px; padding:2px 6px; border-radius:4px;
  background:transparent; color:var(--text-faint);
  border:1px dashed var(--line); white-space:nowrap; cursor:help;
}
.unmeasured-demo { font-weight:400; cursor:default; }

/* Same weight as "figures not re-measured", and for the same reason: it is a
   provenance note. It appears whenever a sweep ran a narrower selector than
   the whole suite, which since the open-only default is most sweeps -- so on
   a lot of rows at once. What it must never do is let a stale reading pass
   for a fresh one, which is the failure the whole ledger exists to prevent. */
.unchecked {
  font-family:var(--mono); font-size:11.5px; padding:2px 6px; border-radius:4px;
  background:transparent; color:var(--text-faint);
  border:1px dashed var(--line); white-space:nowrap; cursor:help;
}
/* A debt of ours, not a fact about them. Solid rather than dashed: the dashed
   marks say "this reading may be old", this one says "you still have to do
   something". */
.owed {
  font-family:var(--mono); font-size:11.5px; padding:2px 6px; border-radius:4px;
  background:transparent; color:var(--accent);
  border:1px solid var(--accent); white-space:nowrap; cursor:help;
  margin-right:4px;
}
/* No border: this is on every row, so a box around it would be 41 boxes. It is
   the answer to "a sweep just closed six things and I cannot see which". */
.changed {
  font-family:var(--mono); font-size:11.5px; color:var(--text-faint);
  white-space:nowrap; cursor:help;
}
/* Louder than .unchecked on purpose. "We did not re-run our check" is routine
   on a narrow sweep; "we could not hear them" means the vendor half of every
   row on the page is older than it looks. */
.unheard {
  font-family:var(--mono); font-size:11.5px; padding:2px 6px; border-radius:4px;
  background:transparent; color:var(--warn);
  border:1px dashed var(--warn); white-space:nowrap; cursor:help;
}

.mv {
  display:inline-block; font-family:var(--mono); font-size:11.5px;
  background:var(--surface-2); border-radius:3px; padding:1px 5px; margin:1px 2px 1px 0;
}
.kvt-in td { padding:1px 8px 1px 0; border:0; }
.chat-verdict {
  font-family:var(--mono); font-size:11px; text-transform:uppercase;
  letter-spacing:.04em; padding:1px 6px; border-radius:4px;
}
.chat-verdict.ok  { color:var(--ok);  border:1px solid var(--ok); }
.chat-verdict.bad { color:var(--bad); border:1px solid var(--bad); }
/* ---------- stats ---------- */
.stat-grid {
  display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr));
  gap:14px; margin-top:20px;
}
.stat {
  background:var(--surface); border:1px solid var(--line); border-radius:10px;
  padding:16px 18px 14px; min-width:0;
}
.stat.wide { grid-column:1 / -1; }
.stat h3 { margin:0 0 10px; font-size:14px; font-weight:600; color:var(--text); }
.hero { font-size:30px; font-weight:600; color:var(--text); line-height:1.1; }
.hero span { font-size:13px; font-weight:400; color:var(--text-dim); }
.figs { display:flex; flex-wrap:wrap; gap:4px 18px; margin:10px 0 12px; }
.figs div { display:flex; gap:6px; align-items:baseline; }
.figs dt { font-size:12px; color:var(--text-faint); }
.figs dd { margin:0; font-size:12.5px; color:var(--text-dim); font-family:var(--mono); }
svg.bars { width:100%; height:80px; display:block; }
.bars-x {
  display:flex; justify-content:space-between; font-family:var(--mono);
  font-size:10px; color:var(--text-faint); margin-top:2px;
}
.stat-t { width:100%; border-collapse:collapse; font-size:13px; }
.stat-t th {
  text-align:left; font-weight:500; font-size:11.5px; color:var(--text-faint);
  border-bottom:1px solid var(--line); padding:0 10px 5px 0;
}
.stat-t td {
  padding:6px 10px 6px 0; color:var(--text-dim); font-family:var(--mono);
  font-size:12.5px; border-bottom:1px solid var(--line-soft);
}
.stat-t td:first-child { color:var(--text); font-family:inherit; }

.diagram {
  width:100%; height:auto; max-width:980px; display:block; margin:18px 0 6px;
}
/* ---------- legend: two axes, then the grid they make ---------- */
.lead { font-size:15.0px; color:var(--text-dim); max-width:74ch; margin:14px 0 10px; }
.lead .hi { color:var(--ok); font-weight:600; }

.axes { display:flex; gap:14px; align-items:stretch; flex-wrap:wrap; margin:14px 0 22px; }
.axis {
  flex:1 1 260px; min-width:0; background:var(--surface-2);
  border:1px solid var(--line-soft); border-radius:var(--radius); padding:12px 13px;
}
.axis-h { font-size:14.5px; font-weight:600; color:var(--text); }
.axis-h b { color:var(--accent); }
.axis-sub {
  font-size:13.0px; color:var(--text-faint); margin:2px 0 10px;
  padding-bottom:8px; border-bottom:1px solid var(--line-soft);
}
.axis-row {
  display:flex; gap:9px; align-items:baseline; margin:6px 0;
  font-size:13.9px; color:var(--text-dim);
}
/* An axis VALUE, not a display state. Deliberately its own class: reusing
   .state gave NOT_RAISED the class s-not-raised, which no rule matches --
   the same unstyled-chip problem one level up. These are inputs to the grid;
   the colours belong to the squares the grid produces. */
.axv {
  flex:0 0 auto; font-family:var(--mono); font-size:11.5px; font-weight:600;
  padding:2px 6px; border-radius:4px; white-space:nowrap;
  background:var(--none-bg); color:var(--text-dim);
}
.axis-join {
  align-self:center; font-family:var(--mono); font-size:22px; color:var(--text-faint);
}

.matrix-wrap { overflow-x:auto; margin:6px 0 10px; }
.matrix { border-collapse:separate; border-spacing:3px; font-size:12.5px; }
.matrix th {
  font-family:var(--mono); font-size:11.5px; font-weight:600; color:var(--text-faint);
  text-align:left; white-space:nowrap; padding:3px 6px; text-transform:uppercase;
  letter-spacing:.04em;
}
.matrix tr th:first-child { text-align:right; }
.matrix td { padding:0; }
.matrix .state { display:block; text-align:center; }
.matrix-note {
  display:flex; flex-direction:column; gap:5px; font-size:13.9px; color:var(--text-dim);
}
.marks { flex:none; margin:10px 0 20px; }
.marks .axis-row { align-items:baseline; margin:8px 0; }
.marks .axis-row > span:last-child { max-width:70ch; }
.mono-faint {
  font-family:var(--mono); font-size:12.5px; color:var(--text-faint); flex:0 0 auto;
}
.matrix-note span span.state { margin-right:7px; }

@media (max-width: 640px) {
  .axis-join { display:none; }
}

.f-body {
  padding:0 15px 15px; border-top:1px solid var(--line-soft); font-size:13.5px;
}
.f-body .f-lede { font-size:15px; }
.f-body .chat-body { font-size:13.5px; padding:10px 13px; }
.f-body .ref-k { font-size:11.5px; flex-basis:150px; }
.f-body .ref-v { font-size:12.5px; }
.f-body .ref-v.mono { font-size:11.8px; }
.ref-note { color:var(--text-faint); }
.f-note {
  font-size:14.7px; color:var(--text-dim); margin:12px 0 0; padding-left:11px;
  border-left:2px solid var(--accent-dim); max-width:78ch;
}
.kv { overflow-x:auto; }
.kv table { border-collapse:collapse; width:100%; font-family:var(--mono); font-size:13.5px; }
.kv td { padding:4px 10px 4px 0; vertical-align:top; border-bottom:1px solid var(--line-soft); }
.kv td:first-child { color:var(--text-faint); white-space:nowrap; width:1%; }
.kv td:last-child { color:var(--text); word-break:break-word; }
.checks {
  margin-top:13px; font-family:var(--mono); font-size:12.5px; color:var(--text-faint);
  word-break:break-all;
}
.checks b { color:var(--text-dim); font-weight:500; }

h4.sec {
  font-size:12.0px; text-transform:uppercase; letter-spacing:.1em; font-weight:700;
  color:var(--text-faint); margin:18px 0 8px;
}

/* ---------- the runbook, at the foot of the legend ----------
   Czech, and the only half of this page written for the person who RUNS the
   commands rather than for whoever reads a badge. It carries thresholds and
   mechanisms, never a measured number: a figure frozen into the page is the
   defect CLAUDE.md names twice -- read the count off the tool, not off prose. */
.rb-wrap { overflow-x:auto; margin:10px 0 20px; }
/* min-width so a narrow window makes the wrapper SCROLL rather than crushing
   three columns into two words a line -- at a 320px pane the columns came out
   131/91/94. max-width keeps it from sprawling on a wide one. */
.rb { border-collapse:collapse; width:100%; min-width:640px; max-width:100ch; font-size:14.4px; }
.rb th {
  text-align:left; font-size:11.5px; text-transform:uppercase; letter-spacing:.07em;
  color:var(--text-faint); font-weight:600; padding:0 16px 7px 0;
  border-bottom:1px solid var(--line); white-space:nowrap;
}
.rb td {
  padding:9px 16px 9px 0; vertical-align:top; line-height:1.5;
  border-bottom:1px solid var(--line-soft);
}
.rb tr:last-child td { border-bottom:none; }
.rb td:first-child { color:var(--text); font-weight:600; min-width:13ch; }
/* .when is nowrap on purpose -- a two-word "kdy" column should never wrap.
   .dur is the same colour and WRAPS: used on the retention column, whose
   values are sentences. Screenshotting found that one: nowrap there held the
   column open and squeezed the middle one down to two words a line. */
.rb .when { color:var(--text-faint); white-space:nowrap; }
.rb .dur { color:var(--text-faint); }
.rb code { white-space:nowrap; }
.msg { border:1px solid var(--line-soft); border-radius:6px; margin-bottom:8px; overflow:hidden; }
.msg-head {
  display:flex; flex-wrap:wrap; gap:4px 10px; align-items:center; padding:8px 11px;
  background:var(--surface-2); font-family:var(--mono); font-size:12.5px; color:var(--text-faint);
}
.dir { font-weight:600; }
.dir.out { color:var(--auth); }
.dir.in  { color:var(--ok); }
.dir.dead { color:var(--bad); }
.msg pre {
  margin:0; padding:11px 13px; font-family:var(--mono); font-size:13.0px;
  line-height:1.6; white-space:pre-wrap; word-break:break-word; color:var(--text);
  max-height:360px; overflow:auto; background:var(--surface);
}
.awaiting {
  font-size:14.0px; color:var(--text-faint); padding:9px 11px;
  border:1px dashed var(--line); border-radius:6px; max-width:78ch;
}

.note {
  margin-top:42px; padding:18px 20px; border:1px solid var(--line);
  border-radius:var(--radius); background:var(--surface); font-size:15.0px;
  color:var(--text-dim); max-width:none;
}
.note h3 { margin:0 0 8px; font-size:14.5px; color:var(--text); text-transform:uppercase; letter-spacing:.09em; }
.note p { margin:0 0 9px; }
.note code { font-family:var(--mono); font-size:13.5px; background:var(--surface-2); padding:1px 5px; border-radius:3px; }
.note .verdicts { border-collapse:collapse; margin:12px 0 16px; }
.note .verdicts td { padding:5px 12px 5px 0; vertical-align:top; font-size:14.7px; line-height:1.45; }
.note .verdicts td:first-child { width:1%; padding-right:9px; padding-top:9px; }
.note .verdicts td:nth-child(2) { white-space:nowrap; color:var(--text); }
.note .verdicts i {
  display:inline-block; width:10px; height:10px; border-radius:2px;
  box-shadow:inset 0 0 0 1px var(--line);
}
.note .verdicts i.faint { opacity:.6; }
.note .example {
  background:var(--surface-2); border-radius:6px; padding:11px 13px;
  border-left:2px solid var(--accent); font-size:14.7px;
}
/* ---------- tabs, the bell, and the live indicator ----------
   Added when the console moved from a published snapshot to a page held open
   in a tab all day. Two things follow from that: it has to say whether it is
   live, and it has to be able to tell you something arrived while you were
   looking elsewhere. */
.tabs { display:flex; gap:4px; margin:26px 0 0; border-bottom:1px solid var(--line); }
.tabs button {
  background:none; border:0; border-bottom:2px solid transparent; color:var(--text-dim);
  font:inherit; font-size:15px; padding:10px 16px; cursor:pointer; margin-bottom:-1px;
}
.tabs button[aria-selected="true"] { color:var(--text); border-bottom-color:var(--accent); }
.tabs button:focus-visible { outline:2px solid var(--accent); outline-offset:-2px; }
.tabs .tab-n {
  display:inline-block; margin-left:7px; padding:1px 7px; border-radius:9px;
  background:var(--none-bg); color:var(--text-dim); font-family:var(--mono); font-size:12px;
}
.panel[hidden] { display:none; }
.sr-only {
  position:absolute; width:1px; height:1px; padding:0; margin:-1px;
  overflow:hidden; clip:rect(0 0 0 0); white-space:nowrap; border:0;
}

.mast { position:relative; }
.bell {
  position:absolute; top:0; right:0; background:none; border:1px solid var(--line);
  border-radius:9px; color:var(--text-dim); cursor:pointer; font-size:17px;
  line-height:1; padding:8px 10px;
}
.bell:hover { color:var(--text); border-color:var(--text-faint); }
.bell:focus-visible { outline:2px solid var(--accent); outline-offset:2px; }
.bell-n {
  position:absolute; top:-6px; right:-6px; min-width:18px; padding:0 5px;
  background:var(--bad); color:#fff; border-radius:9px;
  font-family:var(--mono); font-size:11px; line-height:18px; font-weight:600;
}
.bell-n[hidden] { display:none; }
.inbox {
  position:absolute; top:44px; right:0; width:min(460px, 88vw); z-index:60;
  /* --surface, not --card: --card is not a token in this sheet, so the panel
     resolved to no background at all and the page read straight through it. */
  background:var(--surface); border:1px solid var(--line); border-radius:12px;
  box-shadow:0 18px 44px rgba(0,0,0,.55); padding:6px; text-align:left;
  max-height:min(70vh, 620px); overflow-y:auto;
}
.inbox[hidden] { display:none; }
.inbox h4 { margin:8px 10px 6px; font-size:12px; letter-spacing:.08em;
  text-transform:uppercase; color:var(--text-faint); }
.inbox button.item {
  display:block; width:100%; text-align:left; background:var(--surface); border:0;
  color:var(--text); font:inherit; padding:9px 10px; border-radius:8px; cursor:pointer;
}
.inbox h4, .inbox .empty, .inbox .seen { background:var(--surface); }
.inbox button.item:hover { background:var(--none-bg); }
.inbox .item-t { display:block; font-size:14px; }
.inbox .item-m { display:block; font-size:12.5px; color:var(--text-dim); margin-top:3px; }
.inbox .empty { padding:14px 10px; color:var(--text-dim); font-size:14px; }
.inbox .seen {
  display:block; width:100%; text-align:center; background:none; border:0;
  border-top:1px solid var(--line); margin-top:4px; padding:9px;
  color:var(--text-dim); font:inherit; font-size:13px; cursor:pointer;
}
.inbox .seen:hover { color:var(--text); }
/* Read state is invisible until it misbehaves, and then there is nothing on
   screen to look at. This says what it holds and WHERE -- the host matters,
   because localStorage is per origin: 127.0.0.1 and localhost are two
   different stores, and the published Artifact is a third. */
.inbox .seenline {
  padding:8px 10px 4px; color:var(--text-faint); font-family:var(--mono);
  font-size:11.5px; text-align:center; background:var(--surface);
}

/* Was the words "new reply" in a red pill, which shouted louder than the
   state chip beside it and read as another status. It is a mark, not a state:
   an envelope, at text size, in the accent. */
.newreply {
  display:inline-flex; align-items:center; color:var(--accent);
  vertical-align:-2px;
}
.newreply svg { width:15px; height:15px; display:block; }
.live {
  font-family:var(--mono); font-size:12px; color:var(--text-faint);
  display:inline-flex; align-items:center; gap:6px;
}
.live i { width:7px; height:7px; border-radius:50%; background:var(--text-faint); }
.live.on i { background:var(--ok); }
.live.off i { background:var(--warn); }

@media (prefers-reduced-motion: reduce) { * { transition:none!important; animation:none!important; } }
</style>

<div class="wrap" id="wrap">
  <header class="mast">
    <h1>Cymetica QA Console</h1>
    <button class="bell" id="bell" aria-label="Replies from Cymetica" aria-expanded="false">
      &#128276;<span class="bell-n" id="bellN" hidden></span>
    </button>
    <div class="inbox" id="inbox" hidden></div>
    <div class="meta" id="meta"></div>
  </header>

  <nav class="tabs" id="tabs">
    <button data-tab="overview" aria-selected="true">Platform</button>
    <button data-tab="findings" aria-selected="false">Findings
      <span class="tab-n" id="tabN"></span></button>
    <button data-tab="stats" aria-selected="false">Stats</button>
    <button data-tab="nexus" aria-selected="false">Nexus
      <span class="tab-n" id="nexusN" hidden></span></button>
    <button data-tab="legend" aria-selected="false">How to read this</button>
  </nav>

  <section class="panel" id="panel-overview">
  <div class="triage" id="triage"></div>

  <div id="map"></div>
  </section>

  <section class="panel" id="panel-findings" hidden>
  <div class="filters" id="filters"></div>
  <div id="findings"></div>
  </section>

  <section class="panel" id="panel-stats" hidden>
  <div class="stat-grid" id="stats"></div>
  </section>

  <section class="panel" id="panel-nexus" hidden>
  <div class="nx-note" id="roomsNote" hidden></div>
  <nav class="nx-strip" id="roomList" aria-label="Strategies"></nav>
  <div class="nx-main" id="nxMain">
    <div class="nx-chatcol">
      <div class="nx-chat" id="roomChat"></div>
      <form class="nx-compose" id="nxCompose" hidden>
        <textarea id="nxDraft" rows="2" maxlength="4000"
          placeholder="Your feedback for this room. Claude reads it when you ask."></textarea>
        <div class="nx-send"><span id="nxSendNote">Ctrl+Enter sends</span>
          <button type="submit" id="nxSend">Send</button></div>
      </form>
    </div>
    <aside class="nx-panel" id="roomPanel"></aside>
  </div>
  </section>

  <section class="panel" id="panel-help" hidden>
  <h2 class="group">How this works</h2>
  <p class="lead">Their platform is on the left. Everything to the right of it
  is ours, and the only way anything on this page moves.</p>

  <svg class="diagram" viewBox="0 0 980 300" role="img"
       aria-label="Their platform is measured by checks; a run of those checks moves the left half of a row, and a message from them moves the right half; the page shows the two together.">
    <defs>
      <marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7"
              markerHeight="7" orient="auto-start-reverse">
        <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--text-faint)"/>
      </marker>
    </defs>
    <g font-size="13" fill="var(--text)" font-family="inherit">
      <rect x="8" y="96" width="150" height="72" rx="8" fill="var(--surface-2)"
            stroke="var(--line)"/>
      <text x="83" y="126" text-anchor="middle" font-weight="600">Cymetica</text>
      <text x="83" y="146" text-anchor="middle" font-size="11.5"
            fill="var(--text-dim)">the thing being tested</text>

      <rect x="212" y="96" width="150" height="72" rx="8" fill="var(--surface)"
            stroke="var(--line)"/>
      <text x="287" y="126" text-anchor="middle" font-weight="600">checks</text>
      <text x="287" y="146" text-anchor="middle" font-size="11.5"
            fill="var(--text-dim)">46 of them, each one asks one question</text>

      <rect x="416" y="96" width="150" height="72" rx="8" fill="var(--surface)"
            stroke="var(--line)"/>
      <text x="491" y="126" text-anchor="middle" font-weight="600">a run</text>
      <text x="491" y="146" text-anchor="middle" font-size="11.5"
            fill="var(--text-dim)">frozen before it starts</text>

      <rect x="620" y="30" width="170" height="64" rx="8" fill="var(--surface)"
            stroke="var(--ok)"/>
      <text x="705" y="56" text-anchor="middle" font-weight="600">what we measured</text>
      <text x="705" y="76" text-anchor="middle" font-size="11.5"
            fill="var(--text-dim)">only a run moves this</text>

      <rect x="620" y="170" width="170" height="64" rx="8" fill="var(--surface)"
            stroke="var(--accent)"/>
      <text x="705" y="196" text-anchor="middle" font-weight="600">where it stands with them</text>
      <text x="705" y="216" text-anchor="middle" font-size="11.5"
            fill="var(--text-dim)">only a message moves this</text>

      <rect x="844" y="96" width="128" height="72" rx="8" fill="var(--surface-2)"
            stroke="var(--line)"/>
      <text x="908" y="126" text-anchor="middle" font-weight="600">this page</text>
      <text x="908" y="146" text-anchor="middle" font-size="11.5"
            fill="var(--text-dim)">the two, side by side</text>

      <rect x="212" y="244" width="354" height="48" rx="8" fill="var(--surface)"
            stroke="var(--line)" stroke-dasharray="4 3"/>
      <text x="389" y="266" text-anchor="middle" font-size="12">bug tracker &middot; a2a &middot; Telegram</text>
      <text x="389" y="283" text-anchor="middle" font-size="11.5"
            fill="var(--text-dim)">what they say back</text>

      <g stroke="var(--text-faint)" stroke-width="1.4" fill="none" marker-end="url(#ar)">
        <path d="M162 132 H206"/>
        <path d="M366 132 H410"/>
        <path d="M570 128 C596 128 596 62 614 62"/>
        <path d="M570 152 C596 152 596 202 614 202"/>
        <path d="M794 62 C820 62 820 128 838 128"/>
        <path d="M794 202 C820 202 820 140 838 140"/>
        <path d="M389 240 V176"/>
        <path d="M566 268 C600 268 600 214 614 210"/>
      </g>
      <text x="180" y="122" font-size="11" fill="var(--text-faint)">reads</text>
      <text x="384" y="122" font-size="11" fill="var(--text-faint)">runs</text>
    </g>
  </svg>

  <p class="lead">A row on this page is those two halves put together. Nothing
  writes a state directly &mdash; a run moves the left half, a message from
  them moves the right, and every move says which one caused it.</p>

  <h3 class="sec">What to run me on</h3>
  <p class="lead">You set the model and the effort before giving a task; I
  cannot change either. This table is read from the operating rules when the
  page is built, so it is never a second copy.</p>
  <table class="stat-t" id="models"></table>
  </section>

  <section class="panel" id="panel-legend" hidden>
  <div class="note">

    <p class="lead">Every badge answers <b>two</b> questions at once. That is why there
    are so many of them &mdash; and the badge is just the square where the two answers meet.</p>

    <div id="axes"></div>

    <p class="lead"><b>The grid below is the whole pipeline.</b> Down the side: what
    <b>we</b> measured. Along the top: where it stands <b>with them</b>.
    <span class="hi">Only one square is green</span> &mdash; our check passes <em>and</em>
    they claim a fix. Nothing else counts as verified.</p>

    <div id="matrix"></div>

    <p class="lead"><b>A row carries other marks too.</b> None of them is a state:</p>

    <div id="marks"></div>

    <h4>S0 to S4 &mdash; how much damage, not how sure we are</h4>

    <div id="sevs"></div>

    <h4>The cards are places, not test suites</h4>

    <p class="lead">One card = one part of the platform. Its chips count four
    different things:</p>

    <div id="cardmarks"></div>

    <p class="lead">The buttons at the top of the page filter the finding list:
    the first row by <b>damage</b> (the S numbers), the second by <b>area</b>
    &mdash; the same areas the cards are grouped under.</p>

    <h4>The percentage on each card is a different thing</h4>

    <p><b>It answers one question:</b> of all the addresses Cymetica publishes for this
    part of the platform, how many actually answer when you call them? We call each twice
    &mdash; once with no key, once with the API key &mdash; and take the better answer:</p>

    <table class="verdicts"><tbody id="verdicts"></tbody></table>


    <p><b>&ldquo;Checks&rdquo; is a different number again.</b> An address answering does
    not mean the answer is <em>correct</em>. <b>100% with no checks</b> means
    &ldquo;it is alive, and nobody has verified a word it says&rdquo;.</p>

    <h4>The bell, in the top corner</h4>

    <p class="lead">It counts <b>incoming answers on our own bug reports</b> that
    you have not read yet &mdash; a status they changed, or a note they wrote
    back &mdash; and nothing else. A number there means they have moved on
    something we filed.</p>

    <p class="example">It comes from their bug tracker, read back over their
    own API, so it can only ever show something they actually said. That read
    happens on a sweep, not when this page redraws: the page is where an answer
    is delivered, never where one is discovered.</p>

    <h3 style="margin-top:34px">Jak to celé běží</h3>

    <p class="lead">Nahoře je, jak číst tuhle stránku. Tady je, jak funguje
    systém za ní: co pouštíš ty, co se zlepšuje samo, a kolik dat se kde drží.</p>

    <h4>Co pouštíš ty &mdash; a kdy</h4>

    <p class="lead"><b>Nic se nespouští samo.</b> Žádný plánovač, žádný časovač.
    Na začátku každé session se vypíše, co je na řadě a jakým povelem &mdash;
    a spustíš to ty.</p>

    <div class="rb-wrap"><table class="rb">
      <tr><th>Řekneš nebo spustíš</th><th>Kdy</th><th>Co se stane</th></tr>
      <tr><td>„projdi bugy&ldquo;</td><td class="when">kdykoliv</td>
          <td>Přeověří otevřené nálezy, podá nové, pošle verdikty. Každý nález
          má napřed kontrolu, teprve pak report.</td></tr>
      <tr><td>„jdi do laboratoře&ldquo;</td><td class="when">když chceš nové strategie</td>
          <td>Session s Nexusem: co je nového &rarr; jejich backtesty &rarr;
          jedna otázka &rarr; room a paper obchod &rarr; poučení pro příště.</td></tr>
      <tr><td><code>lab.py night --until 07:00</code></td><td class="when">večer</td>
          <td>Celou noc backtesty, ráno souhrn. Neobchoduje, nezakládá nálezy,
          necommituje &mdash; noc hledá, ráno se jedná.</td></tr>
      <tr><td>„jdu spat&ldquo;</td><td class="when">než jdeš spát</td>
          <td>Deep pass přes všechno nepushnuté. Jediná věc, která pushuje.</td></tr>
      <tr><td>„přečti si to&ldquo;</td><td class="when">když jsi psal do roomu</td>
          <td>Přečte tvoje poznámky celé, označí je a odpoví do nich.</td></tr>
      <tr><td><code>console.cmd</code></td><td class="when">ráno</td>
          <td>Tahle stránka na 127.0.0.1:8787. Sama se obnovuje do vteřiny.</td></tr>
    </table></div>

    <h4>Laboratoř</h4>

    <p class="lead"><b>Nexus radí, my měříme a vykonáváme.</b> Naše vlastní
    strategie se nikdy nestane roomem &mdash; jde Nexusovi jako otázka a room
    otevře až jeho odpověď.</p>

    <div class="rb-wrap"><table class="rb">
      <tr><td>den</td><td>Co je nového, doběhnuté otázky, jejich backtesty
          seřazené podle rizika (ne podle výnosu), jedna otázka Nexusovi
          s tabulkou, jak dopadly jeho minulé návrhy &mdash; mezi otázkami si
          nic nepamatuje, náš záznam je jeho paměť.</td></tr>
      <tr><td>noc</td><td>Dvoje hodiny: backtesty souvisle (brzdí je jen jejich
          limit 30 volání za minutu), otázka jen když je na co se ptát &mdash;
          nejdřív 20 minut od sebe, nejvýš 12 za noc.</td></tr>
      <tr><td>rozhodnutí</td><td>Room jen z konkrétní odpovědi. <b>Kritérium se
          píše předem</b> a nejde s ním hnout, dokud okno běží &mdash; kritérium
          přepsané v půlce je kritérium ušité na čísla. Verdikt se počítá z jejich
          vlastní historie indexu; pod 80 % pokrytí je nerozhodnuto, nikdy ztráta.</td></tr>
      <tr><td>brzdy</td><td>V kódu, ne v textu, aby si je session ve tři ráno
          nerozmluvila: jen paper, 50 běžících experimentů, 2 % volných peněz na
          jeden, nejvýš 60 % knihy venku najednou, a nic, když běží deep pass.</td></tr>
      <tr><td>paměť</td><td>Každý backtest má otisk: koš, okno, poplatky. Co už
          bylo změřeno, se nezměří znovu &mdash; ani dnes, ani za týden.</td></tr>
    </table></div>

    <h4>Deep pass</h4>

    <p class="lead">Třináct kroků, doběhne bez tebe. Rozsah je <b>všechno
    nepushnuté</b>, proto se pouští, než jdeš spát.</p>

    <div class="rb-wrap"><table class="rb">
      <tr><td>audit kontrol</td><td>Tři nezávislí auditoři drží tvrzení každé
          kontroly proti smlouvě, kterou jmenuje její vlastní docstring. Tahle
          třída vad nastala 7. 9. pětkrát za den, všechny testy zelené, a jedna
          z nich poslala vendorovi nepravdivé tvrzení.</td></tr>
      <tr><td>review a triage</td><td>Celý diff na nejvyšší úrovni, pak tři
          nezávislé triage bez sdíleného kontextu. Nález projde, jen když
          souhlasí aspoň dva ze tří.</td></tr>
      <tr><td>oprava a ověření</td><td>Opraví, co přežilo, a ověří podle pravidel
          repa: čistý strom, zapnutá preregistrace, celý selektor.</td></tr>
      <tr><td>zápis</td><td><code>DEEP-PASS.md</code> česky (včetně „Čeká na
          tebe&ldquo;), <code>NEXT.md</code> pro zítřek, a jednou týdně ohlédnutí
          za celým týdnem.</td></tr>
    </table></div>

    <h4>Co se zlepšuje samo</h4>

    <div class="rb-wrap"><table class="rb">
      <tr><td>hlídka nad námi</td><td>Najde globem každý skill, agenta, skript
          a hook a přečte z jejich vlastních záznamů, co dělaly. Nic se
          neregistruje &mdash; registrace je věc, na kterou se zapomene. Týden se
          u každé součásti ptá, jestli stála za to, co stála.</td></tr>
      <tr><td>hlídka nad nimi</td><td>Když Cymetica přejmenuje parametr nástroje
          nebo přidá pole do odpovědi, řekne se to při startu session. Postaveno
          potom, co důkaz o jejich opravě ležel den v našich vlastních datech
          a dozvěděli jsme se ho z Telegramu.</td></tr>
      <tr><td>sebehodnocení</td><td><code>lab.py grade</code>: předpověděl náš
          backtestový žebříček skutečný verdikt? Pod šesti uzavřenými verdikty
          odpoví „málo dat&ldquo; místo vymyšlené korelace.</td></tr>
      <tr><td>co nikdy neproběhlo</td><td><code>never_fired.py</code>: mechanismy,
          které jsou v testech zelené a v datech ani jednou nenastaly. Zelený
          test říká, že by fungoval; tohle říká, jestli někdy fungoval.</td></tr>
      <tr><td>paměť</td><td>Soubory o tom, jak jsem se spletl &mdash; ne co jsem
          našel, to stojí v nálezech nahoře. Píšou se, když se to stane, a čtou
          se před prací, ne po ní.</td></tr>
    </table></div>

    <h4>Data &mdash; kolik, kde a jak dlouho</h4>

    <p class="lead">Problém nikdy nebyl <em>kolik</em>, ale <b>kde</b> (v gitu)
    a <b>jak dlouho</b> (navždy). První odpověď &mdash; git drží jen citované
    &mdash; nestačila: i ta citovaná množina roste bez konce, a za osm hodin
    práce přibylo 47 MB. Takže od 12. 9. <b>v gitu není ani jedna jejich
    odpověď</b>:</p>

    <div class="rb-wrap"><table class="rb">
      <tr><th>Kde</th><th>Co tam je</th><th>Jak dlouho</th></tr>
      <tr><td>git</td>
          <td><b>žádná jejich odpověď.</b> Jen kód, stav nálezů, žurnál, deníky
          laboratoře &mdash; a <b>manifest</b>: u každé držené odpovědi její
          hash, velikost, jaké volání zodpověděla a v jakém archivu leží</td>
          <td class="dur">navždy; jsou to stovky kilobajtů, ne stovky megabajtů</td></tr>
      <tr><td><code>archive/</code> mimo git</td>
          <td>samotné odpovědi, měsíční balík. Hash <b>je</b> důkaz
          neporušenosti, protože jsou adresované obsahem &mdash; a než se
          originál pustí, přehashuje se každý člen zpátky z toho balíku</td>
          <td class="dur">navždy; v každém verdiktu vendorovi píšeme, že ho na
          požádání vydáme</td></tr>
      <tr><td><code>evidence/</code> na disku</td>
          <td>všechny jejich odpovědi, adresované obsahem</td>
          <td class="dur">3 dny &mdash; ale co něco cituje, zůstává, dokud to
          cituje</td></tr>
      <tr><td><code>state/runs</code></td>
          <td>záznamy běhů &mdash; vstupy, ze kterých se skládá stav nálezů</td>
          <td class="dur">7 dní, pokud na nich nic nestojí; na co se nahoře odkazuje,
          je v gitu</td></tr>
      <tr><td><code>state/*.jsonl</code></td>
          <td>deníky: laboratoř, rejstřík backtestů, roomy, obchody, vzorky</td>
          <td class="dur">navždy, ale jsou to kilobajty</td></tr>
    </table></div>

    <p class="example"><b>Kolik je toho dnes, vypíše</b>
    <code>python scripts/prune_runs.py</code> &mdash; kolik záznamů a odpovědí
    leží na disku, co by se smazalo, a u každého přeživšího důvod, proč zůstal.
    Čísla čti z něj, ne odsud: stránka by je měla zmrazené, a přesně takhle už
    tady jednou jedno číslo lhalo.</p>

    <h4>Pět vět, které platí všude</h4>

    <div class="rb-wrap"><table class="rb">
      <tr><td>jen paper</td><td>Live se netestuje, dokud neřekneš jinak.</td></tr>
      <tr><td>nic se nespouští samo</td><td>Připomínka ano, plánovač ne.</td></tr>
      <tr><td>commit ano, push ne</td><td>Výjimka je deep pass, nebo když to
          řekneš ty v té zprávě. Push totiž smaže rozsah review.</td></tr>
      <tr><td>červený test v <code>tests/meta</code></td><td>je systém, který
          funguje. Neopravuje se uvolněním pravidla &mdash; zastaví session dřív,
          než půjde ven jediný požadavek.</td></tr>
      <tr><td>„VERIFIED FIXED&ldquo;</td><td>je naše měření: naše kontrola prošla
          pod otiskem, pod kterým padala. Ne že to oni řekli &mdash; jejich
          „opraveno&ldquo; je tvrzení, které si teprve ověřujeme.</td></tr>
    </table></div>

  </div>
  </section>
</div>

<script id="data" type="application/json">__DATA__</script>
<script>
const D = JSON.parse(document.getElementById("data").textContent);
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

// localStorage is a convenience here, never state. A private window, a
// browser set to block site data, or a thumbnailer will throw on access, so
// every read falls back to its default and every write may fail silently.
function readStore(key, dflt) {
  try { const v = localStorage.getItem(key); return v === null ? dflt : v; }
  catch (_) { return dflt; }
}
function writeStore(key, value) {
  try { localStorage.setItem(key, String(value)); } catch (_) {}
}

// The newest thing THEY said on a row, as epoch ms; 0 when they have said
// nothing. An unparseable timestamp returns now, so it reads as new rather
// than silently as already seen -- this must never hide a reply.
function newestFromThem(f) {
  // An undated reply returns 0, not Date.now(). Date.now() was the original
  // choice, on the reasoning that a missing timestamp should err toward
  // showing the mark rather than hiding it -- but it is recomputed on every
  // render, so such a row was newer than any "seen" moment forever and its
  // envelope could never be cleared. Every reply carries a date now (see
  // _api_conversation), so a missing one is genuinely no information, and a
  // badge you cannot clear is worse than a mark you did not get.
  const times = (f.thread || [])
    .filter(m => m && m.who && m.who !== "us")
    .map(m => Date.parse(m.at))
    .filter(t => !Number.isNaN(t));
  return times.length ? Math.max.apply(null, times) : 0;
}

// "PASSING (UNPINNED)" -> "s-passing-unpinned". The old version replaced only
// spaces, so the class came out as s-passing-(unpinned) -- parentheses are not
// valid in a bare CSS class selector, so no rule could ever match it and the
// chip rendered unstyled however many rules were written.
const stateClass = s =>
  "s-" + String(s).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

// An ISO moment, printed. There are two formatters on this page and they take
// different things: this one a timestamp string, `when(ms)` below an epoch. The
// marks in finding() called `when` on an ISO string, where every comparison is
// NaN-false and only the last line survives, so they printed a bare date. Both
// are drawn by a narrow sweep or a failed read, so neither had ever been seen.
const stamp = t => t ? String(t).replace("T", " ").slice(0, 16) : "";
const SEV = [
  ["S0-CUSTODY","custody / auth","s0"], ["S1-INTEGRITY","data integrity","s1"],
  ["S2-MEASUREMENT","measurement","s2"], ["S3-CONTRACT","contract","s3"],
  ["S4-COSMETIC","cosmetic","s4"],
];

// One line, because the seven-figure row above it was read by nobody: "to
// nikdy nectu a je to hnus". What survives is what the page cannot be read
// without -- which run, at what level, standing on which journal event. The
// rest is still here, in the tooltip, where it costs nothing until wanted.
document.getElementById("meta").innerHTML =
  `<span class="runline" title="${esc([
      `run ${D.run_id || "—"}`,
      `platform fingerprint ${D.fingerprint || "—"}`,
      `documented paths ${D.totals.paths_documented ?? "—"}`,
      `MCP tools anon / trusted ${D.totals.tools_served_anon ?? "—"} / ${D.totals.tools_served_trusted ?? "—"}`,
      `messages sent / received ${D.thread_counts.sent ?? 0} / ${D.thread_counts.received ?? 0}`,
      `page generated ${D.generated_at.replace("T"," ").replace("+00:00","Z")}`,
      ...(D.run_notes || []),
    ].join("\n"))}">`
  + `run ${esc(stamp(D.run_at) || "—")} &middot; level ${esc(D.run_level || "—")} &middot; `
  // What the ledger cites, never what the journal is at now. The journal
  // moves on a timer and this page is hashed into a guard, so a live number
  // here would make the dashboard stale against itself every fifteen minutes.
  + `state as of ${D.events_head ? "journal event " + esc(D.events_head.seq) : "—"}`
  + `</span>`;

document.getElementById("triage").innerHTML =
  SEV.map(([k,l,c]) => `<div class="tri ${c}"><div class="n">${D.by_severity[k]||0}</div><div class="l">${l}</div></div>`).join("")
  + `<div class="tri"><div class="n">${D.sections.filter(s=>!(s.checks&&s.checks.total)).length}</div><div class="l">sections with no checks</div></div>`
  + `<div class="tri"><div class="n">${D.findings.filter(f=>f.filed&&f.filed.length).length}</div><div class="l">filed to their tracker</div></div>`
  + `<div class="tri ok"><div class="n">${D.display_counts["VERIFIED FIXED"]||0}</div><div class="l">verified fixed by us</div></div>`
  + `<div class="tri"><div class="n">${D.display_counts["FIX CLAIMED"]||0}</div><div class="l">fix claimed, unverified</div></div>`;

/* ---------- section map, grouped by product area ---------- */
function health(s) {
  if (s.finding_severities.some(v => v === "S0-CUSTODY" || v === "S1-INTEGRITY")) return "h-bad";
  if (s.reachable_pct == null) return "h-none";
  if (s.reachable_pct < 60) return "h-bad";
  if (s.reachable_pct < 90 || s.finding_severities.length) return "h-warn";
  return "h-ok";
}
// What each bar segment and each verdict actually means, in the operator's
// words. "ok 6, method 1, unprobed 3" told nobody anything.
const VERDICT_WORDS = {
  ok:        "answers properly",
  auth:      "asks for a key -- the lock works",
  param:     "wants a parameter we did not send",
  method:    "we asked the wrong way (our fault, left out of the score)",
  missing:   "documented, but there is nothing there",
  server_error: "it broke on their side (5xx)",
  unreachable: "we got no answer at all -- our network, not their endpoint",
  unprobed:  "cannot be checked by a simple call",
  websocket: "a live feed, not a request",
};
// Every verdict inventory.py can produce. server_error and unreachable were
// missing, so an endpoint in either state vanished from the bar and from the
// legend, and the bar's own total was computed over this list -- a section
// could read 80% with the other 20% represented by nothing at all.
const ORDER = ["ok","auth","param","method","missing","server_error",
               "unreachable","unprobed","websocket"];

function card(s) {
  const h = health(s);
  const total = ORDER.reduce((a,k) => a + (s.verdicts[k]||0), 0) || 1;
  const bar = ORDER.filter(k => s.verdicts[k]).map(k =>
    `<span class="seg-${k}" style="width:${(s.verdicts[k]/total*100).toFixed(2)}%"
      title="${s.verdicts[k]} ${VERDICT_WORDS[k]}"></span>`).join("");

  const legend = ORDER.filter(k => s.verdicts[k]).map(k =>
    `<span class="blabel"><i class="seg-${k}"></i>${s.verdicts[k]} ${VERDICT_WORDS[k]}</span>`
  ).join("");

  const pct = s.reachable_pct == null
    ? `<div class="pct-wrap"><span class="pct h-none">not checkable</span>
       <span class="pct-cap">nothing here answers a simple call</span></div>`
    : `<div class="pct-wrap"><span class="pct ${h}">${s.reachable_pct}<small>%</small></span>
       <span class="pct-cap">${s.endpoints_reachable} of ${s.endpoints_probed}
       published addresses answer</span></div>`;

  const checks = s.checks && s.checks.total
    ? `<span class="chip ${s.checks.failed ? "bad" : "ok"}">${s.checks.total} tests written${s.checks.failed ? ", "+s.checks.failed+" failing" : ""}</span>`
    : `<span class="chip untested">0 tests written</span>`;
  const sev = {};
  s.finding_severities.forEach(v => { sev[v] = (sev[v]||0)+1; });
  const fnd = Object.entries(sev).map(([k,n]) =>
    `<span class="chip ${/^S[01]/.test(k) ? "bad" : /^S4/.test(k) ? "" : "warn"}">${n}&times; ${k.split("-")[0]}</span>`).join("");

  // Every address behind the number, so the percentage can be checked rather
  // than believed. Grouped by what happened, worst first.
  const byVerdict = {};
  (s.endpoint_detail || []).forEach(e => {
    (byVerdict[e.verdict] = byVerdict[e.verdict] || []).push(e);
  });
  // ORDER, not a second list written by hand: the hand-written one omitted
  // server_error and unreachable, so an address in either state showed in the
  // bar and the legend and then vanished from the panel that explains the bar.
  const detail = ORDER
    .filter(k => byVerdict[k]).map(k => `
      <div class="epgroup">
        <div class="epgroup-h"><i class="seg-${k}"></i>${byVerdict[k].length}
          ${VERDICT_WORDS[k]}</div>
        ${byVerdict[k].map(e => `<div class="ep">
          <code>${esc(e.path)}</code>
          <span class="ep-meta">${esc((e.methods||["GET"]).join(", "))}
            ${e.status_anon != null ? "&middot; anon " + e.status_anon : ""}
            ${e.status_trusted != null && e.status_trusted !== e.status_anon
               ? "&middot; with key " + e.status_trusted : ""}
            ${e.sources && e.sources.length ? "&middot; from " + esc(e.sources.join(", ")) : ""}
          </span></div>`).join("")}
      </div>`).join("");

  // The count was the only thing a tile said about its checks, and the
  // operator asked to open it and see which ones: "chci si to rozkliknout a
  // videt ktere testy to jsou". One line each, from the check's own docstring.
  const tests = (s.tests || []).length
    ? `<ul class="tlist">${s.tests.map(t => `<li class="t-${esc(t.outcome)}">
        <span class="t-n">${esc(t.name)}</span>
        <span class="t-o">${esc(t.outcome)}</span>
        ${t.gone ? `<span class="t-d t-gone">no longer exists &mdash; this row stands on the run that last ran it</span>`
                 : (t.doc ? `<span class="t-d">${esc(t.doc)}</span>` : "")}
        ${t.outcome === "passed" || !t.reason ? "" : `<span class="t-r">${esc(t.reason)}</span>`}
      </li>`).join("")}</ul>`
    : `<p class="blurb">No check here yet, so nothing on this tile has been verified.</p>`;

  return `<details class="card ${h}">
    <summary>
      <div class="card-top"><h3>${esc(s.title)}</h3>${pct}</div>
      <div class="blegend">${legend}</div>
      <p class="blurb">${esc(s.blurb)}</p>
      <div class="stats">
        <span class="chip">${s.endpoints_documented} addresses published</span>
        ${s.tools_declared ? `<span class="chip">${s.tools_declared} MCP tools</span>` : ""}
        ${s.verdicts.missing ? `<span class="chip bad">${s.verdicts.missing} &times; not there</span>` : ""}
        ${checks}${fnd}
      </div>
    </summary>
    <div class="card-detail">
      <section class="cd-tests"><h4 class="sec">Checks behind that count</h4>${tests}</section>
      <section class="cd-eps"><h4 class="sec">Published addresses</h4>
        ${detail || "<p class=\"blurb\">Nothing documented here.</p>"}</section>
    </div>
  </details>`;
}
document.getElementById("map").addEventListener("toggle", e => {
  const card = e.target.closest ? e.target.closest(".card") : null;
  if (!card || !card.open) return;
  document.querySelectorAll("#map details.card[open]").forEach(other => {
    if (other !== card) other.open = false;
  });
}, true);

document.getElementById("map").innerHTML = D.groups.map(g => {
  const items = D.sections.filter(s => g.sections.includes(s.id));
  if (!items.length) return "";
  items.sort((a,b) => (a.reachable_pct ?? 999) - (b.reachable_pct ?? 999));
  return `<h2 class="group"><span class="tagchip">${esc(g.tag)}</span>${esc(g.title)}</h2>
          <p class="group-note">${esc(g.blurb)}</p>
          <div class="grid">${items.map(card).join("")}</div>`;
}).join("");

/* ---------- findings: the conversation through THEIR API ---------- */
// Only the bounty API. Telegram is a different channel with different
// properties -- attachments silently dropped, delivery unconfirmable -- and
// mixing them produced a panel where a message nobody received sat beside a
// report they had answered, as if both were the same kind of fact.
function conversation(f) {
  if (!f.thread || !f.thread.length) {
    return `<h4 class="sec">Conversation with Cymetica</h4>
      <div class="awaiting">Not filed to their tracker yet.</div>`;
  }

  const bubbles = f.thread.map(m => {
    // Three kinds of message, not two. A verification is ours but it is not a
    // report: it goes out through a different endpoint, says one thing, and
    // is the only way this panel can show that we answered their answer.
    const head = m.verdict
      ? `<b>We re-checked</b> <span class="chat-verdict ${m.verdict === "pass" ? "ok" : "bad"}">${esc(m.verdict)}</span>`
      : m.who === "us"
      ? `<b>We filed report #${m.report_id}</b>`
      : `<b>They answered</b> <span class="chat-status">${esc(m.status || "")}</span>`;
    const body = m.verdict
      ? `<p>${esc(m.text)}</p>`
        + (m.run_id ? `<p class="chat-quiet">run <code>${esc(m.run_id)}</code></p>` : "")
      : m.who === "us"
      ? [m.title && `<div class="chat-title">${esc(m.title)}</div>`,
         m.text && `<p>${esc(m.text)}</p>`,
         m.expected && `<p><b>Expected.</b> ${esc(m.expected)}</p>`,
         m.actual && `<p><b>Actually.</b> ${esc(m.actual)}</p>`].filter(Boolean).join("")
      : (m.text ? `<p>${esc(m.text)}</p>`
                : `<p class="chat-quiet">Status changed with no note.</p>`);
    return `<div class="chat ${m.who}">
      <div class="chat-meta">${head}<time>${esc(stamp(m.at))}</time></div>
      <div class="chat-body">${body}</div></div>`;
  }).join("");

  // Said once, under the thread, rather than under every message.
  const note = f.verification
    ? `<div class="chat-note ok"><b>We re-ran the test and it passes.</b>
       ${esc(stamp(f.verification.at))} by run <code>${esc(f.verification.run_id)}</code>.
       ${f.thread.some(m => m.who === "them" && /fix|resolv|complet|clos/i.test(m.status || ""))
         ? "Their claim and our measurement agree, which is what closes it."
         : "They never claimed a fix for this one; our own test is what closes it."}</div>`
    : f.regressions && f.regressions.length
    ? `<div class="chat-note bad"><b>This was fixed and has broken again</b>
       (run <code>${esc(f.regressions[f.regressions.length-1].run_id)}</code>).</div>`
    : f.thread.some(m => m.who === "them")
    ? `<div class="chat-note">Their answer is a claim until our own test passes.</div>`
    : `<div class="chat-note">Filed, no answer yet.</div>`;

  return `<h4 class="sec">Conversation with Cymetica</h4>${bubbles}${note}`;
}

// One bounty report can cover several findings -- #51 carried both the skill
// ids and the skill count. Without saying so, two rows show the same number
// and it reads as a collision.
function sharedWith(f, reportId) {
  return D.findings
    .filter(o => o.id !== f.id && (o.filed || []).some(x => x.report_id === reportId))
    .map(o => o.id);
}

// What a check measured, printed. Every one of these went through esc(),
// which is String(), so `sources` and `population` -- dicts on nearly every
// row -- rendered as the literal "[object Object]" in the one panel whose job
// is to show the numbers. A list becomes its items, a dict becomes its pairs,
// and anything else is a value.
function measured(value) {
  if (value === null || value === undefined) return "&mdash;";
  if (Array.isArray(value)) {
    return value.length
      ? value.map(v => `<span class="mv">${measured(v)}</span>`).join(" ")
      : "&mdash; empty";
  }
  if (typeof value === "object") {
    const pairs = Object.entries(value);
    return pairs.length
      ? `<table class="kvt kvt-in">${pairs.map(([k, v]) =>
          `<tr><td>${esc(k)}</td><td>${measured(v)}</td></tr>`).join("")}</table>`
      : "&mdash; empty";
  }
  return esc(value);
}

function finding(f) {
  const numbers = Object.entries(f.detail || {})
    .filter(([k]) => k !== "reason")
    .map(([k,v]) => `<tr><td>${esc(k)}</td><td>${measured(v)}</td></tr>`).join("");

  // The header carries only what identifies and prioritises the row. The
  // report number, the internal kind word and the id moved inside: they are
  // reference data, and on the summary line they read as though "#51" and
  // "CYM-skill_ids" were competing names for the same thing.
  const changed = Date.parse(f.last_change.at) || 0;
  return `<details class="finding" id="f-${esc(f.id)}" data-sev="${esc(f.severity)}"
    data-tag="${esc(f.tag)}" data-state="${esc(f.display_state)}"
    data-changed-at="${changed}"
    data-vendor-at="${newestFromThem(f)}">
    <summary>
      <span class="sev ${f.severity.split("-")[0]}">${esc(f.severity.split("-")[0])}</span>
      <span>
        <span class="f-title">${esc(f.headline || f.title)}</span>
        <div class="f-sub">
          <span class="tagchip">${esc(f.tag)}</span>
          <span class="state ${stateClass(f.display_state)}">${esc(f.display_state)}</span>
          ${f.filed && f.filed.length ? `<span class="filed">${f.filed.map(x=>"#"+x.report_id).join(", ")}</span>` : ""}
          ${f.unmeasured ? `<span class="unmeasured" title="The wording and numbers here are from the day this was written; no run since has confirmed they still hold.">figures not re-measured</span>` : ""}
          ${f.not_checked_in ? `<span class="unchecked" title="This sweep ran a narrower selector and did not include this check. The state and figures shown are the ones the last run that did include it left behind.">not re-checked${f.last_checked_at ? " &middot; last " + esc(stamp(f.last_checked_at)) : ""}</span>` : ""}
          ${(f.owed || []).map(o => `<span class="owed" title="Something is still owed on this row: the fold works it out from the events, and it stays here until an event settles it. A re-verify is cleared by a level-V run under the pinned fingerprint; a retraction by a retraction-sent event.">${esc(o)}</span>`).join("")}
          ${f.stale_from ? `<span class="unheard" title="The last attempt to read their bug tracker did not succeed, so what they say here is as of the last clean read and may have moved since. A failed read is not an empty one: nothing on the vendor's side was allowed to change on the strength of it.">their side unread &middot; since ${esc(stamp(f.stale_from))}</span>` : ""}
          ${changed ? `<span class="changed" title="The last time anything about this row moved -- either a run adjudicating the check, or a message on their tracker.">${f.last_change.axis
              ? "changed " + esc(when(changed)) + " &middot; " + esc(f.last_change.from) + " &rarr; " + esc(f.last_change.to)
              : "first seen " + esc(when(changed))}</span>` : ""}
          <span class="newreply" data-newreply hidden title="They replied since you last looked"><svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><rect x="2.2" y="4.6" width="15.6" height="11" rx="2"/><path d="M2.6 6.2 10 11.4l7.4-5.2"/></svg><span class="sr-only">new reply</span></span>
        </div>
      </span>
    </summary>
    <div class="f-body">
      ${f.summary ? `<p class="f-lede">${esc(f.summary)}</p>` : ""}
      ${f.withdrawn_reason ? `<p class="f-note"><b>We withdrew this.</b> ${esc(f.withdrawn_reason)}</p>` : ""}
      ${f.note ? `<p class="f-note">${esc(f.note)}</p>` : ""}
      ${conversation(f)}
      <div class="f-ref">
        <div><span class="ref-k">Our name for it</span>
             <span class="ref-v mono">${esc(f.id)}</span></div>
        <div><span class="ref-k">First seen</span>
             <span class="ref-v mono">${esc(stamp(f.first_seen_at)) || "&mdash;"}</span></div>
        ${f.filed && f.filed.length ? `<div><span class="ref-k">Their report number</span>
             <span class="ref-v mono">${f.filed.map(x => "#" + x.report_id +
               (sharedWith(f, x.report_id).length
                 ? ` <span class="ref-note">(one report, filed together with ` +
                   sharedWith(f, x.report_id).map(esc).join(", ") + `)</span>` : "")
             ).join(", ")}</span></div>` : ""}
        <div><span class="ref-k">Test that decides it</span>
             <span class="ref-v mono">${(f.checks||[]).map(esc).join("<br>") || "&mdash; none, so nothing can settle this"}</span></div>
        ${numbers ? `<div><span class="ref-k">What was measured</span>
             <span class="ref-v"><table class="kvt">${numbers}</table></span></div>` : ""}
      </div>
    </div></details>`;
}

const box = document.getElementById("findings");
box.innerHTML = D.findings.map(finding).join("");

const sevCounts = {}, tagCounts = {};
D.findings.forEach(f => {
  sevCounts[f.severity] = (sevCounts[f.severity]||0)+1;
  tagCounts[f.tag] = (tagCounts[f.tag]||0)+1;
});
// Three views, one facet row. The counts on the three views are filled in by
// applyFilters, not baked here: "changed since read" moves whenever the read
// mark moves, and a number printed once would be wrong by the next click. The
// old row printed `all - 41` from the payload while the tab badge counted what
// was visible, so two numbers a centimetre apart meant different things.
document.getElementById("filters").innerHTML =
  `<button data-kind="open" aria-pressed="true">open <span class="cn"></span></button>`
  + `<button data-kind="changed" aria-pressed="false">changed since read <span class="cn"></span></button>`
  + `<button data-kind="all" aria-pressed="false">all <span class="cn"></span></button>`
  + `<span class="sep"></span><button data-act="read">mark read</button>`
  + `<span class="sep"></span><span class="fl">sort</span>`
  + `<button data-sort="changed" aria-pressed="true">last change</button>`
  + `<button data-sort="damage" aria-pressed="false">damage</button>`
  // Labelled, because two unlabelled rows of buttons filtering different
  // things is a puzzle: one row is how much damage, the other is which part
  // of the platform, and nothing on screen said so.
  + `<span class="sep"></span><span class="fl">damage</span>`
  + `<button data-kind="sev" data-v="" aria-pressed="true">any</button>`
  + SEV.filter(s => sevCounts[s[0]]).map(s =>
      `<button data-kind="sev" data-v="${s[0]}" aria-pressed="false">${s[1]} &middot; ${sevCounts[s[0]]}</button>`).join("")
  + `<span class="sep"></span><span class="fl">area</span>`
  + D.groups.filter(g => tagCounts[g.tag]).map(g =>
      `<button data-kind="tag" data-v="${g.tag}" aria-pressed="false">${g.tag} &middot; ${tagCounts[g.tag]}</button>`).join("");

/* ---------- legend: the composition table, drawn from the real one ---------- */
// Plain-language gloss for each axis value. Six words or fewer: the point of
// the diagram is that you do not have to read.
const CHECK_WORDS = {
  UNVERIFIED:        ["no valid run has looked yet", "grey"],
  REPRODUCING:       ["we ran it &mdash; still broken", "bad"],
  PASSING:           ["we ran it &mdash; it passes", "ok"],
  PASSING_UNPINNED:  ["passes, but never seen failing", "teal"],
  INCONCLUSIVE:      ["the check measured nothing", "grey"],
  UNVERIFIABLE:      ["no check can answer this", "grey"],
};
const FILING_WORDS = {
  NOT_RAISED:  "not sent to them",
  RAISED:      "filed &mdash; no answer yet",
  REPLIED:     "they answered",
  FIX_CLAIMED: "they say it is fixed",
};
const TERMINAL_WORDS = {
  WITHDRAWN:  "we took it back: we were wrong",
  SUPERSEDED: "replaced by another finding",
};

const C = D.composition;
const short = s => s.replace(/_/g, " ");

document.getElementById("axes").innerHTML = `
  <div class="axes">
    <div class="axis">
      <div class="axis-h">What <b>we</b> measured</div>
      <div class="axis-sub">changes only when a proper test run actually ran this check</div>
      ${C.check_states.map(s => `<div class="axis-row">
        <span class="axv">${esc(short(s))}</span>
        <span>${CHECK_WORDS[s] ? CHECK_WORDS[s][0] : ""}</span></div>`).join("")}
    </div>
    <div class="axis-join">&times;</div>
    <div class="axis">
      <div class="axis-h">Where it stands <b>with them</b></div>
      <div class="axis-sub">changes only when a message or their tracker says so</div>
      ${C.filing_states.map(s => `<div class="axis-row">
        <span class="axv">${esc(short(s))}</span>
        <span>${FILING_WORDS[s] || ""}</span></div>`).join("")}
    </div>
  </div>`;

document.getElementById("matrix").innerHTML = `
  <div class="matrix-wrap"><table class="matrix">
    <tr><td></td>${C.filing_states.map(f =>
      `<th>${esc(short(f))}</th>`).join("")}</tr>
    ${C.check_states.map(c => `<tr>
      <th>${esc(short(c))}</th>
      ${C.filing_states.map(f => {
        const v = C.table[c][f];
        return `<td><span class="state ${stateClass(v)}">${esc(v)}</span></td>`;
      }).join("")}
    </tr>`).join("")}
  </table></div>
  <div class="matrix-note">
    ${C.terminal.map(t => `<span><span class="state ${stateClass(t)}">${esc(t)}</span>
      ${TERMINAL_WORDS[t] || ""} &mdash; ours, final, whatever the check says</span>`).join("")}
  </div>`;

// Everything on a finding row that is NOT a state. The operator hit exactly
// this: an unexplained "figures not re-measured" beside a badge, with the
// legend explaining only the badge. Five marks share that line; explaining one
// of them is worse than explaining none, because it implies the rest are
// obvious.
const MARKS = [
  [`<span class="tagchip">MCP</span>`,
   "which part of the platform this belongs to"],
  [`<span class="unmeasured-demo">figures not re-measured</span>`,
   "the wording and numbers here are from the day the finding was written, and no run since has confirmed they still hold &mdash; read them as history, not as today"],
  [`<span class="filed">filed as #46</span>`,
   "the report number it has with them"],
  [`<span class="undelivered">1 message never delivered</span>`,
   "we sent it and nobody ever confirmed it arrived"],
  [`<span class="mono-faint">contradiction</span>`,
   "how it was found: sources disagreeing, a check failing, or the reporting channel itself"],
  [`<span class="mono-faint">CYM-mcp_resource_count</span>`,
   "our id for it &mdash; the same id in every report and every message"],
];

document.getElementById("marks").innerHTML = `
  <div class="axis marks">
    ${MARKS.map(([chip, words]) =>
      `<div class="axis-row">${chip}<span>${words}</span></div>`).join("")}
  </div>`;

// Severity is blast radius: what breaks if this is real. It is not confidence,
// and it is not urgency. The colours on the page are these.
const SEV_WORDS = [
  ["S0", "s0", "money, keys, or who is allowed to do what"],
  ["S1", "s1", "wrong data that someone would act on"],
  ["S2", "s2", "counts or labels that mislead"],
  ["S3", "s3", "their documentation disagrees with their platform"],
  ["S4", "s4", "cosmetic"],
];
document.getElementById("sevs").innerHTML = `
  <div class="axis marks">
    ${SEV_WORDS.map(([k, cls, words]) =>
      `<div class="axis-row"><span class="sev ${cls}">${k}</span>
       <span>${words}</span></div>`).join("")}
  </div>`;

const CARD_MARKS = [
  [`<span class="chip">10 addresses published</span>`,
   "URLs their own documentation lists for this part"],
  [`<span class="chip">3 MCP tools</span>`,
   "tools declared for it in the MCP manifest"],
  [`<span class="chip bad">4 &times; not there</span>`,
   "of those addresses, how many answer 404"],
  [`<span class="chip untested">0 tests written</span>`,
   "checks we have written here &mdash; zero means nobody has verified a word this part says, however green the percentage is"],
  [`<span class="chip ok">6 tests written, 1 failing</span>`,
   "the same count once checks exist"],
  [`<span class="chip warn">1&times; S2</span>`,
   "an open finding in this part, at that damage level"],
];
document.getElementById("cardmarks").innerHTML = `
  <div class="axis marks">
    ${CARD_MARKS.map(([chip, words]) =>
      `<div class="axis-row">${chip}<span>${words}</span></div>`).join("")}
  </div>`;

/* ---------- what is still live, and what is settled ----------
   A row you have finished with is noise on a page you keep open all day.
   These four states are finished: two are ours and terminal, two mean the
   check passes and nobody is waiting on anything. "Open only" is on by
   default, and the number on the Findings tab is whatever is visible. */
const SETTLED = new Set(["VERIFIED FIXED", "WITHDRAWN", "SUPERSEDED",
                         "PASSING, NEVER RAISED"]);
let view = readStore("qa.view", "open");
let sortBy = readStore("qa.sort", "changed");
let activeKind = "sev", activeValue = null;

/* A row that closed while you were away is the one thing a sweep produces
   that the page could not show. It is not "unread" in the bell's sense --
   nobody said anything -- so it is a third view rather than a badge, and it
   shares the bell's read mark so that clearing one clears both. */
const changedSince = el => Number(el.dataset.changedAt || 0) > seenAt();

function inView(el) {
  if (view === "all") return true;
  if (view === "changed") return changedSince(el);
  return !SETTLED.has(el.dataset.state);
}

function applyFilters() {
  const counts = { open: 0, changed: 0, all: 0 };
  let shown = 0;
  box.querySelectorAll(".finding").forEach(el => {
    counts.all++;
    if (!SETTLED.has(el.dataset.state)) counts.open++;
    if (changedSince(el)) counts.changed++;
    const matches = !activeValue ||
      (activeKind === "sev" ? el.dataset.sev === activeValue
                            : el.dataset.tag === activeValue);
    const visible = matches && inView(el);
    el.hidden = !visible;
    if (visible) shown++;
  });
  document.querySelectorAll("#filters button[data-kind]").forEach(b => {
    const kind = b.dataset.kind;
    if (kind in counts) {
      b.setAttribute("aria-pressed", String(view === kind));
      const n = b.querySelector(".cn");
      if (n) n.textContent = "· " + counts[kind];
    } else {
      b.setAttribute("aria-pressed",
        String((b.dataset.v || null) === activeValue && kind === activeKind));
    }
  });
  document.querySelectorAll("#filters button[data-sort]").forEach(b =>
    b.setAttribute("aria-pressed", String(b.dataset.sort === sortBy)));
  const badge = document.getElementById("tabN");
  if (badge) badge.textContent = String(shown);
}

/* Newest movement first, because after a sweep that is the question. Damage
   order is the other one anybody asks, and S0 sorts above S4 by its own name.
   Re-appending the nodes keeps one list rather than rendering a second. */
const SEV_RANK = SEV.map(s => s[0]);
function sortRows() {
  const rows = Array.from(box.querySelectorAll(".finding"));
  rows.sort((a, b) => sortBy === "damage"
    ? (SEV_RANK.indexOf(a.dataset.sev) - SEV_RANK.indexOf(b.dataset.sev))
      || (Number(b.dataset.changedAt || 0) - Number(a.dataset.changedAt || 0))
    : Number(b.dataset.changedAt || 0) - Number(a.dataset.changedAt || 0));
  rows.forEach(el => box.appendChild(el));
}

document.getElementById("filters").addEventListener("click", e => {
  const btn = e.target.closest("button"); if (!btn) return;
  if (btn.dataset.act === "read") { markRead(); return; }
  if (btn.dataset.sort) {
    sortBy = btn.dataset.sort;
    writeStore("qa.sort", sortBy);
    sortRows();
  } else if (btn.dataset.kind === "open" || btn.dataset.kind === "changed"
             || btn.dataset.kind === "all") {
    view = btn.dataset.kind;
    writeStore("qa.view", view);
  } else if (btn.dataset.kind) {
    activeKind = btn.dataset.kind;
    activeValue = btn.dataset.v || null;
  }
  applyFilters();
});
sortRows();
applyFilters();

/* ---------- the Nexus tab: rooms, served beside the payload, never in it ----------
   The operator's notes and the sampler's rows land while a sweep may be
   running, and everything in D is written into the committed dashboard -- so
   the console serves the rooms at /rooms.json and says when they move with an
   event of its own. Opened as a file there is no console to ask, and the tab
   says so rather than showing an empty room as if nobody had said anything. */
const NX_LOCAL = ["127.0.0.1", "localhost", "[::1]"].includes(location.hostname);
let NX = null;

// Nexus writes markdown. Escape first, always, and only then turn a few marks
// back into tags of our own -- so nothing the vendor wrote can become markup.
function nxText(text) {
  let s = esc(text == null ? "" : text);
  s = s.replace(/`([^`\n]+)`/g, "<code>$1</code>");
  s = s.replace(/\*\*([^*\n]+)\*\*/g, "<b>$1</b>");
  s = s.replace(/^#{1,6} +(.+)$/gm, "<b>$1</b>");
  s = s.replace(/^[ \t]*[-*] +/gm, "• ");
  return s;
}
function nxSecs(s) {
  if (s == null) return "";
  if (s < 90) return Math.round(s) + " s";
  if (s < 5400) return Math.round(s / 60) + " min";
  return (s / 3600).toFixed(1) + " h";
}
const nxDigits = n => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
const NX_OUTCOME = {
  partial: "cut short — only an opening line came back",
  failed: "no answer — our loop gave up waiting",
  refused: "refused before an investigation started",
  waiting: "waiting for Nexus…",
};

// The tab names its own shapes -- `nm` a message, `nr` a room, `np` a panel,
// and inside a strategy's panel `nt` a trade, `nh` a change of status, `nc` a
// bot and `ns` one of its samples -- because `f.` and `m.` belong to the
// payload's field guard, and these arrive by fetch.
// tests/meta/test_pipeline_rooms.py holds each name against what
// build_rooms() writes, the same way that guard holds the payload.
const NX_STATUS = { proposed: "○", running: "●", paused: "‖", stopped: "■" };
function nxGlyph(status) {
  return '<span class="nx-st nx-' + esc(status || "proposed") + '">' +
    (NX_STATUS[status] || "○") + "</span>";
}
// Money the way the operator reads it: 10 000, 89 000.96, 0.00216, −50.
function nxMoney(v) {
  if (v == null || v === "" || isNaN(Number(v))) return "—";
  const n = Number(v), a = Math.abs(n);
  const parts = a.toFixed(a >= 1 || a === 0 ? 2 : 5).split(".");
  const tail = Number(parts[1]) ? "." + parts[1].replace(/0+$/, "") : "";
  return (n < 0 ? "−" : "") + nxDigits(parts[0]) + tail;
}
function nxShort(text, n) {
  const s = String(text == null ? "" : text);
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}
// A way into another room, from a line in this one.
function nxGoto(room, label) {
  return '<button type="button" class="nx-goto" data-room="' + esc(room) + '">' +
    esc(label) + "</button>";
}
function nxBubble(nm, current) {
  const at = nm.at ? " · " + esc(stamp(nm.at)) : "";
  if (nm.kind === "question") {
    const opened = (nm.opened || []).map(room => room === current
      ? '<span class="nx-s">this room was opened from this answer</span>'
      : nxGoto(room, "→ it opened " + room)).join(" ");
    return '<div class="nx-msg nx-ours"><div class="nx-h"><b>Claude → Nexus</b>' + at +
      " · " + esc(nm.id) + '</div><div class="nx-b">' + nxText(nm.text) + "</div>" +
      (opened ? '<div class="nx-opened">' + opened + "</div>" : "") + "</div>";
  }
  if (nm.kind === "reply") {
    const text = nm.text || "";
    const took = nm.seconds != null ? " · " + nxSecs(nm.seconds)
               : (nm.upper != null && text ? " · ≤ " + nxSecs(nm.upper) : "");
    const note = NX_OUTCOME[nm.outcome];
    const long = text.length > 700;
    const label = "▾ whole answer (" + nxDigits(text.length) + " characters)";
    return '<div class="nx-msg nx-' + esc(nm.outcome || "answered") + '">' +
      '<div class="nx-h"><b>Nexus</b>' + at + took + "</div>" +
      (note ? '<div class="nx-s">' + esc(note) + "</div>" : "") +
      (nm.gist ? '<div class="nx-gist"><span>Claude · summary</span>' + nxText(nm.gist) +
                 "</div>" : "") +
      (text ? '<div class="nx-b' + (long ? " nx-clamp" : "") + '">' + nxText(text) + "</div>" : "") +
      (long ? '<button class="nx-more" type="button" data-label="' + esc(label) + '">' +
              esc(label) + "</button>" : "") +
      "</div>";
  }
  if (nm.kind === "operator_note") {
    return '<div class="nx-msg nx-op"><div class="nx-h"><b>You</b>' + at +
      ' <span class="nx-tick" title="' + (nm.read ? "read by Claude" : "saved, not read yet") +
      '">' + (nm.read ? "✓✓" : "✓") + '</span></div><div class="nx-b">' +
      nxText(nm.text) + "</div></div>";
  }
  if (nm.kind === "claude_note") {
    return '<div class="nx-msg nx-cl"><div class="nx-h"><b>Claude</b>' +
      (nm.re ? " · on " + esc(nm.re) : "") + at + '</div><div class="nx-b">' +
      nxText(nm.text) + "</div></div>";
  }
  if (nm.kind === "pointer") {
    return '<div class="nx-msg nx-sys">' + esc(nm.id) + at + " · asked in " +
      nxGoto(nm.room, nm.room + (nm.title ? " · " + nm.title : "")) + ": " +
      esc(nxShort(nm.text, 110)) + "</div>";
  }
  if (nm.kind === "status") {
    // One line in the thread; the whole reason is in the panel, folded.
    return '<div class="nx-msg nx-sys" title="' + esc(nm.text || "") + '">' +
      nxGlyph(nm.status) + " " + esc(nm.status || "") +
      (nm.text ? " — " + esc(nxShort(nm.text, 140)) : "") + at + "</div>";
  }
  if (nm.kind === "leg") {
    return '<div class="nx-msg nx-sys nx-leg' +
      (nm.outcome === "accepted" ? "" : " nx-no") + '">' + esc(nm.text || "") + at + "</div>";
  }
  return '<div class="nx-msg nx-sys">' + esc(nm.text || "") + "</div>";
}

// Where a strategy stands, as a word beside its name; the thread's status
// lines keep the bare glyph.
const NX_WORD = { proposed: "Proposed", running: "Running", paused: "Paused",
                  stopped: "Stopped" };
const NX_HOLDS = { bot: "Bot", cards: "Cards" };
function nxPill(status) {
  const s = status || "proposed";
  return '<span class="nx-pill nx-' + esc(s) + '">' + (NX_STATUS[s] || "○") + " " +
    esc(NX_WORD[s] || s) + "</span>";
}
// Signed money and percentages the way the operator reads them -- +14.48,
// −50, +0.7 % -- and the class that colours them.
function nxSigned(v) {
  if (v == null || v === "" || isNaN(Number(v))) return "—";
  const n = Number(v);
  return (n > 0 ? "+" : "") + nxMoney(n);
}
function nxTone(v) {
  const n = Number(v);
  return v == null || v === "" || isNaN(n) || n === 0 ? "" : n > 0 ? " nx-up" : " nx-down";
}
function nxPct(v, digits) {
  if (v == null || v === "" || isNaN(Number(v))) return "—";
  const n = Number(v);
  const places = digits != null ? digits : Math.abs(n) >= 10 ? 0 : 1;
  const s = Math.abs(n).toFixed(places);
  return (Number(s) === 0 ? "" : n > 0 ? "+" : "−") + s + " %";
}
function nxShare(v) {
  if (v == null || v === "" || isNaN(Number(v))) return "—";
  const n = Number(v) * 100;
  return (Math.abs(n - Math.round(n)) < 0.05 ? String(Math.round(n)) : n.toFixed(1)) + " %";
}
function nxLevel(v) {
  return v == null || v === "" || isNaN(Number(v)) ? "—" : Number(v).toFixed(2);
}
const NX_MONTH = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
                  "Oct", "Nov", "Dec"];
// "11 Sep 10:25" -- UTC, like every other time on this page.
function nxDay(iso) {
  const d = new Date(iso || "");
  if (isNaN(d.getTime())) return "";
  return d.getUTCDate() + " " + NX_MONTH[d.getUTCMonth()] + " " +
    String(d.getUTCHours()).padStart(2, "0") + ":" +
    String(d.getUTCMinutes()).padStart(2, "0");
}
// How long until a card stops trading: "in 36 h", "in 3 d", "closed".
function nxUntil(iso) {
  const t = Date.parse(iso || "");
  if (!t) return null;
  const hours = (t - Date.now()) / 3600000;
  if (hours <= 0) return "closed";
  if (hours < 1) return "in " + Math.max(1, Math.round(hours * 60)) + " min";
  if (hours < 48) return "in " + Math.round(hours) + " h";
  return "in " + Math.round(hours / 24) + " d";
}
// Four big numbers, each with its label above it and one quiet line under it.
function nxTiles(tiles) {
  return '<div class="nx-tiles">' + tiles.map(([label, value, sub, tone]) =>
    '<div class="nx-tile"><span>' + esc(label) + '</span><b class="' +
    (tone || "").trim() + '">' + esc(value == null ? "—" : String(value)) + "</b>" +
    (sub ? "<i>" + esc(String(sub)) + "</i>" : "") + "</div>").join("") + "</div>";
}
function nxHero(name, pills, sub) {
  return '<div class="nx-hero"><h2>' + esc(name) + "</h2>" + pills + "</div>" +
    (sub ? '<p class="nx-sub">' + sub + "</p>" : "");
}
// Where the console's sampler stands, said the same way in every panel: when
// it last read their API, and "stale" once three rounds have gone by without one.
function nxSampler(np) {
  if (!np.sampled_at) {
    return '<p class="nx-foot">Their API has not been read yet: the console reads it ' +
      "when it runs with --sample.</p>";
  }
  const failed = Object.entries(np.sampler_reads || {}).filter(([, verdict]) => verdict !== "ok");
  return '<p class="nx-foot' + (np.stale ? " nx-stale" : "") + '">' +
    (np.stale ? "<b>stale</b> — no round for over three intervals. " : "") +
    "Read from their API " + esc(stamp(np.sampled_at)) + " UTC, every " +
    esc(nxSecs(np.sampler_every)) +
    (np.sampler_ok === false ? " · failed: " +
      esc(failed.map(([door, verdict]) => door + " " + verdict).join(", ")) : "") + ".</p>";
}
function nxParams(params) {
  return Object.entries(params || {}).map(([k, v]) => k + " " + v).join(", ");
}

// Round numbers for an axis, three to five of them between lo and hi.
function nxTicks(lo, hi) {
  const raw = (hi - lo) / 4;
  if (!(raw > 0)) return [lo];
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 2.5, 5, 10].map(k => k * mag).find(s => s >= raw) || raw;
  const out = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + step * 1e-6; v += step) {
    out.push(Number(v.toFixed(10)));
  }
  return out;
}
// Labels down the right edge of a chart, pushed apart so no two overlap.
function nxPlace(labels, top, bottom) {
  const sorted = labels.slice().sort((a, b) => a.y - b.y);
  let last = -Infinity;
  sorted.forEach(label => { label.y = Math.max(label.y, last + 15); last = label.y; });
  const over = sorted.length ? sorted[sorted.length - 1].y - bottom : 0;
  if (over > 0) sorted.forEach(label => { label.y -= over; });
  sorted.forEach(label => { label.y = Math.max(label.y, top); });
  return sorted;
}
// A line over time with levels across it -- a card's entry, Nexus's
// take-profit and stop -- each dashed and named at its right end, and the
// moment something happened as a mark. Drawn at the width of the panel it
// sits in, so its text is the size of the text around it. No library: the
// Stats tab draws the same way.
function nxChart(series, opts) {
  const o = opts || {};
  const pts = (series || []).map(p => [Date.parse(p[0]), Number(p[1])])
    .filter(p => isFinite(p[0]) && isFinite(p[1]));
  if (pts.length < 2) return "";
  const refs = (o.refs || []).filter(r => r && r.v != null && isFinite(Number(r.v)));
  const box = document.getElementById("roomPanel");
  const W = Math.max(360, Math.round((box && box.clientWidth ? box.clientWidth : 700) - 54));
  const H = 230, L = 52, R = 100, T = 14, B = 30;
  const values = pts.map(p => p[1]).concat(refs.map(r => Number(r.v)));
  let lo = Math.min(...values), hi = Math.max(...values);
  if (hi - lo < 1e-9) { lo -= 1; hi += 1; }
  const pad = (hi - lo) * 0.08;
  lo -= pad; hi += pad;
  const t0 = pts[0][0], t1 = pts[pts.length - 1][0], span = t1 - t0 || 1;
  const x = t => L + (t - t0) / span * (W - L - R);
  const y = v => T + (hi - v) / (hi - lo) * (H - T - B);
  const fmt = o.format || nxLevel;
  const r1 = n => n.toFixed(1);
  let svg = '<svg class="nx-chart" viewBox="0 0 ' + W + " " + H + '" width="' + W +
    '" height="' + H + '" role="img" aria-label="' + esc(o.label || "") + '">';
  // An axis of whole numbers reads 105, not 105.00.
  const ticks = nxTicks(lo, hi);
  const whole = ticks.every(v => Math.abs(v - Math.round(v)) < 1e-9);
  const tick = o.format ? fmt : v => (whole ? String(Math.round(v)) : nxLevel(v));
  ticks.forEach(v => {
    svg += '<line class="nx-gl" x1="' + L + '" x2="' + (W - R) + '" y1="' + r1(y(v)) +
      '" y2="' + r1(y(v)) + '"/><text x="' + (L - 8) + '" y="' + r1(y(v) + 4) +
      '" text-anchor="end">' + esc(tick(v)) + "</text>";
  });
  const line = pts.map(p => r1(x(p[0])) + "," + r1(y(p[1]))).join(" ");
  svg += '<path class="nx-area" d="M' + r1(x(t0)) + "," + (H - B) + " L" +
    line.split(" ").join(" L") + " L" + r1(x(t1)) + "," + (H - B) + ' Z"/>';
  const labels = [];
  refs.forEach(r => {
    const at = y(Number(r.v));
    svg += '<line class="nx-ref nx-ref-' + esc(r.kind) + '" data-ref="' + esc(r.kind) +
      '" x1="' + L + '" x2="' + (W - R) + '" y1="' + r1(at) + '" y2="' + r1(at) + '"/>';
    labels.push({ y: at + 4, text: r.label, cls: "nx-" + r.kind });
  });
  if (o.vline && isFinite(Date.parse(o.vline.t))) {
    const at = Date.parse(o.vline.t);
    if (at >= t0 && at <= t1) {
      svg += '<line class="nx-vl" x1="' + r1(x(at)) + '" x2="' + r1(x(at)) + '" y1="' + T +
        '" y2="' + (H - B) + '"/><text class="nx-vt" x="' +
        r1(Math.min(x(at) + 5, W - R - 96)) + '" y="' + (T + 11) + '">' +
        esc(o.vline.label || "") + "</text>";
    }
  }
  svg += '<polyline class="nx-line" points="' + line + '"/>';
  (o.marks || []).forEach(mark => {
    const at = Date.parse(mark.t);
    if (!isFinite(at) || at < t0 || at > t1 || mark.v == null) return;
    svg += '<circle class="nx-dot-' + esc(mark.kind || "open") + '" cx="' + r1(x(at)) +
      '" cy="' + r1(y(Number(mark.v))) + '" r="4.5"><title>' + esc(mark.title || "") +
      "</title></circle>";
  });
  const last = pts[pts.length - 1];
  svg += '<circle class="nx-dot" cx="' + r1(x(last[0])) + '" cy="' + r1(y(last[1])) +
    '" r="5"/>';
  labels.push({ y: y(last[1]) + 4, text: "now " + fmt(last[1]), cls: "nx-now" });
  nxPlace(labels, T + 8, H - B).forEach(label => {
    svg += '<text class="' + label.cls + '" x="' + (W - R + 8) + '" y="' + r1(label.y) +
      '">' + esc(label.text) + "</text>";
  });
  [0, 1 / 3, 2 / 3, 1].forEach((k, i) => {
    const at = t0 + span * k;
    svg += '<text x="' + r1(x(at)) + '" y="' + (H - 8) + '" text-anchor="' +
      (i === 0 ? "start" : i === 3 ? "end" : "middle") + '">' +
      esc(nxDay(new Date(at).toISOString())) + "</text>";
  });
  return svg + "</svg>";
}

// A strategy's cards: Nexus's plan with what was done laid over it. An event
// card is a piece of news, so a leg is named by its headline, and the basket
// its index tracks sits under that, quietly. A card their API does not know is
// said to be one: an id means nothing to the operator.
function nxLegName(nl) {
  if (nl.state === "card not found") return "Card that does not exist";
  return nl.card_title ? nxShort(nl.card_title, 64) : nl.label || "Card not read yet";
}
function nxLegNote(nl) {
  if (nl.state === "card not found") return "Nexus proposed it; their API answers 404";
  return nl.label ? "index: " + nl.label : "";
}
// A card's own page on cymetica.com, in a new tab, wherever the card is named;
// plain text for a card their API does not know. `inner` is already escaped.
function nxCardLink(nl, inner) {
  return nl && nl.url ? '<a class="nx-link" href="' + esc(nl.url) +
    '" target="_blank" rel="noopener" title="Open the card on cymetica.com">' + inner +
    ' <span class="nx-out">↗</span></a>' : inner;
}
function nxLegs(np) {
  const legs = np.legs || [];
  if (!legs.length) return "";
  const rows = legs.map(nl => {
    const share = nl.share != null
      ? nxShare(nl.share) + (nl.usdc_proposed != null ? " · " + nxMoney(nl.usdc_proposed) : "")
      : nl.invested ? nxMoney(nl.invested) + " USDC" : "—";
    const moved = nl.entry != null
      ? esc(nxLevel(nl.entry) + " → " + nxLevel(nl.current))
      : nl.at_proposal != null
        ? esc(nxLevel(nl.at_proposal) + " → " + nxLevel(nl.current)) +
          "<small>since Nexus proposed it</small>"
        : "—";
    const exits = (nl.tp != null ? nxPct(nl.tp, nl.tp % 1 ? 1 : 0) : "—") + " / " +
      (nl.sl != null ? nxPct(nl.sl, nl.sl % 1 ? 1 : 0) : "—");
    const state = nl.state || "not bought";
    return '<div class="nx-tr"><span><b title="' + esc(nl.card_title || "") + '">' +
      nxCardLink(nl, esc(nxLegName(nl))) + "</b><small>" + esc(nxLegNote(nl)) + "</small></span><span>" +
      (nl.side === "bear" ? "▼ bear" : nl.side ? "▲ " + esc(nl.side) : "—") + "</span><span>" +
      esc(share) + "</span><span>" + moved + "</span><span>" + esc(exits) +
      '</span><span class="nx-state nx-' + esc(state.split(" ").join("-")) + '">' +
      esc(state) + "</span></div>";
  }).join("");
  return '<div class="nx-sec">Configuration</div><div class="nx-table nx-legs">' +
    '<div class="nx-tr nx-th"><span>Card</span><span>Side</span><span>Share</span>' +
    "<span>Entry → now</span><span>Take profit / stop</span><span>State</span></div>" +
    rows + (np.reserve != null
      ? '<div class="nx-tr nx-dim"><span>Reserve</span><span></span><span>' +
        esc(nxShare(np.reserve)) + "</span><span></span><span></span><span></span></div>"
      : "") + "</div>";
}
// One chart per card that has an index: the entry and Nexus's exits across it
// when it was bought; when it was not, where it stood when Nexus proposed it
// and how it moved since -- what would have happened, and said so.
function nxLegCharts(np) {
  return (np.legs || []).filter(nl => (nl.series || []).length >= 2).map(nl => {
    const bought = nl.entry != null;
    const refs = [];
    if (bought) {
      refs.push({ v: nl.entry, label: "entry " + nxLevel(nl.entry), kind: "entry" });
    } else if (nl.at_proposal != null) {
      refs.push({ v: nl.at_proposal, label: "proposed " + nxLevel(nl.at_proposal),
                  kind: "base" });
    }
    if (nl.tp_level != null) {
      refs.push({ v: nl.tp_level, label: "TP " + nxLevel(nl.tp_level), kind: "tp" });
    }
    if (nl.sl_level != null) {
      refs.push({ v: nl.sl_level, label: "SL " + nxLevel(nl.sl_level), kind: "sl" });
    }
    const order = bought ? (np.trades || []).find(nt => nt.card === nl.card &&
                                                        nt.outcome === "accepted") : null;
    const head = nxLegName(nl) + (bought ? "" : " · not bought");
    const note = bought
      ? (nl.pnl != null ? "P&L " + nxSigned(nl.pnl) + " USDC" : "")
      : "if bought when proposed: " + nxPct(nl.since_proposal, 2);
    return '<div class="nx-ct"><span>' + nxCardLink(nl, esc(head)) + "</span><small>" +
      esc(note) +
      "</small></div>" + nxChart(nl.series, {
        refs: refs, label: head,
        vline: bought ? (order ? { t: order.at, label: "bought" } : null)
                      : (np.proposed_at ? { t: np.proposed_at, label: "Nexus proposed" }
                                        : null) });
  }).join("");
}
function nxOrders(np) {
  const orders = np.trades || [];
  if (!orders.length) return "";
  const legOf = card => (np.legs || []).find(nl => nl.card === card);
  return '<div class="nx-sec">Orders</div><div class="nx-table nx-orders">' +
    '<div class="nx-tr nx-th"><span>Order</span><span>When</span><span>What</span>' +
    "<span>State</span></div>" + orders.map(nt => {
      const leg = legOf(nt.card);
      const state = nt.outcome !== "accepted" ? (nt.outcome || "no outcome recorded")
        : nt.closed_by ? "closed " + nxSigned(nt.realized) + " USDC" : "open";
      return '<div class="nx-tr"><span>' + esc(nt.id) + '</span><span class="nx-dim">' +
        esc(nxDay(nt.at)) + "</span><span>" + esc((nt.side || "buy") + " · " +
        nxMoney(nt.usdc) + " USDC · ") + (leg ? nxCardLink(leg, esc(nxLegName(leg)))
                                            : esc(nxShort(nt.card, 9))) +
        '</span><span class="nx-state' + (state === "open" ? " nx-open"
          : nt.outcome !== "accepted" ? " nx-card-not-found" : "") + '">' + esc(state) +
        "</span></div>";
    }).join("") + "</div>";
}
function nxCardTiles(np) {
  const legs = np.legs || [];
  const closes = np.closes_at ? nxDay(np.closes_at) + " UTC" : "";
  // Every leg counted by where it stands, so a card they no longer have is
  // counted too: "2 not bought · 1 card not found".
  const states = {};
  legs.forEach(nl => { states[nl.state] = (states[nl.state] || 0) + 1; });
  const told = Object.entries(states).map(([word, n]) => n + " " + word).join(" · ");
  if ((np.invested || 0) > 0) {
    const proposed = np.proposed_share != null && np.bankroll
      ? np.proposed_share * np.bankroll : null;
    return nxTiles([
      ["P&L", np.pnl != null ? nxSigned(np.pnl) + " USDC" : "—",
       np.pnl_pct != null ? nxPct(np.pnl_pct, 2) + " on what went in" : "", nxTone(np.pnl)],
      ["Invested", nxMoney(np.invested),
       proposed != null ? "of " + nxMoney(proposed) + " proposed" : "USDC", ""],
      ["Value now", np.value != null ? nxMoney(np.value) : "—", "USDC", ""],
      ["Card closes", nxUntil(np.closes_at) || "—", closes, ""]]);
  }
  return nxTiles([
    ["Proposed", np.proposed_share != null ? nxShare(np.proposed_share) : "—",
     np.bankroll ? "of " + nxMoney(np.bankroll) + " USDC" : "of the account", ""],
    ["If bought then", nxPct(np.if_bought_pct, 2), "since Nexus proposed it",
     nxTone(np.if_bought_pct)],
    ["Cards", legs.length, told, ""],
    ["Closes first", nxUntil(np.closes_at) || "—", closes, ""]]);
}
// A bot: what it is, the indicators it trades on, its P&L with each of its
// trades on the line, and the trades themselves.
function nxBot(nc) {
  const cfg = nc.config || {};
  const chips = list => (list || []).map(ind => '<span class="nx-chip" title="' +
    esc(nxParams(ind && ind.params)) + '">' + esc((ind && ind.name) || "?") +
    "</span>").join("");
  const mode = cfg.execution_class
    ? String(cfg.execution_class).toLowerCase().split("_").join(" ")
    : nc.paper === false ? "LIVE" : "paper";
  const pairs = [["Bot", nc.name],
                 ["Clone of", [nc.source, nc.symbol].filter(Boolean).join(" · ")],
                 ["Strategy", cfg.strategy_type || nc.strategy],
                 ["Risk", cfg.risk_profile || nc.risk], ["Mode", mode]]
    .filter(([, v]) => v);
  const acts = nc.activity || [];
  const series = (nc.samples || []).filter(ns => ns.pnl != null).map(ns => [ns.at, ns.pnl]);
  // Where the line stands at a trade's moment, between the two samples around
  // it, so each dot sits on the line rather than above a drop it caused.
  const valueAt = when => {
    const t = Date.parse(when);
    let prev = null;
    for (const p of series) {
      const at = Date.parse(p[0]);
      if (at >= t) {
        if (!prev || at === t) return p[1];
        const from = Date.parse(prev[0]);
        return prev[1] + (p[1] - prev[1]) * (t - from) / ((at - from) || 1);
      }
      prev = p;
    }
    return prev ? prev[1] : null;
  };
  const marks = acts.map(na => na.is_closed && na.closed_at
    ? { t: na.closed_at, v: valueAt(na.closed_at),
        kind: Number(na.profit_usdc) < 0 ? "loss" : "open",
        title: (na.symbol || "?") + " " + (na.trade_type || "") + " closed " +
               nxSigned(na.profit_usdc) + " USDC" }
    : { t: na.executed_at, v: valueAt(na.executed_at), kind: "open",
        title: (na.symbol || "?") + " " + (na.trade_type || "") + " " +
               nxMoney(na.amount_usdc) + " USDC, open" });
  return '<div class="nx-sec">Configuration</div><div class="nx-kv">' +
    pairs.map(([k, v]) => "<div><span>" + esc(k) + "</span>" + esc(v) + "</div>").join("") +
    "</div>" +
    ((cfg.primary_indicators || []).length
      ? '<div class="nx-chips"><span>Primary</span>' + chips(cfg.primary_indicators) +
        "</div>" : "") +
    ((cfg.secondary_indicators || []).length
      ? '<div class="nx-chips"><span>Secondary</span>' + chips(cfg.secondary_indicators) +
        "</div>" : "") +
    (series.length >= 2
      ? '<div class="nx-ct"><span>P&amp;L since it was switched on</span><small>' +
        esc(nc.win_rate != null ? "win rate " + nc.win_rate + " %" : "") + "</small></div>" +
        nxChart(series, { marks: marks, format: nxSigned, label: "The bot's P&L over time" })
      : "") +
    (acts.length
      ? '<div class="nx-sec">Its trades</div><div class="nx-table nx-trades">' +
        '<div class="nx-tr nx-th"><span>Symbol</span><span>Type</span><span>USDC</span>' +
        "<span>Result</span><span>When</span></div>" + acts.map(na =>
          '<div class="nx-tr"><span><b>' + esc(na.symbol || "?") + "</b> · " +
          esc(na.side || "") + "</span><span>" + esc(na.trade_type || "") + "</span><span>" +
          esc(nxMoney(na.amount_usdc)) + "</span>" + (na.is_closed
            ? '<span class="' + nxTone(na.profit_usdc).trim() + '">' +
              esc(nxSigned(na.profit_usdc)) + " · closed" +
              (na.exit_reason ? "<small>" + esc(na.exit_reason) + "</small>" : "") + "</span>"
            : '<span class="nx-dim">open</span>') +
          '<span class="nx-dim">' + esc(nxDay(na.executed_at)) + "</span></div>").join("") +
        "</div>"
      : "");
}
// Why a strategy stands where it does, and every move before it, newest first:
// under the name, above the numbers. It is the operator's first question about
// a strategy, and folded at the bottom it was the one thing they could not find.
// The current move is said once, as the why, not again in the list.
function nxStatus(np) {
  const word = String(NX_WORD[np.status] || np.status || "proposed").toLowerCase();
  const moves = (np.history || []).filter(nh =>
    !(nh.status === np.status && nh.why === np.why)).reverse();
  if (!np.why && !moves.length) return "";
  return '<div class="nx-status nx-' + esc(np.status || "proposed") + '"><h3>' +
    (np.why ? "Why it is " + esc(word) : "How it moved") + "</h3>" +
    (np.why ? "<p>" + esc(np.why) + "</p>" : "") +
    (moves.length ? '<div class="nx-moves">' + moves.map(nh => "<p>" +
      nxGlyph(nh.status) + " <b>" + esc(nh.status || "") + "</b> · " + esc(nxDay(nh.at)) +
      (nh.why ? " — " + esc(nh.why) : "") + "</p>").join("") + "</div>" : "") + "</div>";
}
// What a room was accepted on, and what the numbers said at the end of its
// window. A room with neither is one nobody could score afterwards, so the
// panel says that first rather than leaving the space blank.
const NX_SAID = {survived: ["Survived", " nx-up"], refuted: ["Refuted", " nx-down"],
                 inconclusive: ["Inconclusive", ""], open: ["Still running", ""]};
// When the verdict becomes computable: the moment it was accepted plus its
// window, which is the arithmetic qa/lab.py:verdict does -- it starts the
// window at acceptance["at"], never at the moment the room went running. A
// window already past says "due now", because then nobody has run the verdict
// yet and that is the one state worth noticing on this page.
function nxDue(c) {
  const t = Date.parse(c.at || ""), d = Number(c.window_days);
  if (!t || !(d > 0)) return ["—", "no window to close"];
  const end = new Date(t + d * 86400000).toISOString(), left = nxUntil(end);
  return left === "closed" ? ["due now", "window closed " + nxDay(end), " nx-warn"]
                           : [left, "window closes " + nxDay(end), ""];
}
function nxVerdict(np) {
  const c = np.criterion, v = np.verdict;
  if (!c && !v) {
    return '<div class="nx-sec">Criterion</div><p class="nx-foot">' +
      "None written, so nothing could say afterwards whether it worked." +
      " <code>lab.py adopt</code> writes one, and a room cannot run without it.</p>";
  }
  let html = '<div class="nx-sec">Criterion and verdict</div>';
  if (v) {
    const said = NX_SAID[v.verdict] || [v.verdict, ""];
    html += nxTiles([
      [said[0], v.return_pct != null ? nxPct(v.return_pct, 2) : "—",
       v.why || "", said[1]],
      ["Drawdown", v.max_drawdown_pct != null ? nxPct(v.max_drawdown_pct, 2) : "—",
       c && c.stop_pct != null ? "accepted with a " + nxPct(c.stop_pct, 0) + " stop" : "",
       ""],
      ["Benchmark", v.benchmark_pct != null ? nxPct(v.benchmark_pct, 2) : "—",
       v.benchmark_pct != null ? "a BTC-dominated card, same window" : "none", ""],
      ["Coverage", v.coverage != null ? Math.round(v.coverage * 100) + " %" : "—",
       "of the window carries index points",
       v.coverage != null && v.coverage < 0.8 ? " nx-down" : ""]]);
  } else {
    const due = nxDue(c);
    html += nxTiles([
      ["Window", (c.window_days != null ? c.window_days : "—") + " d",
       c.adopted ? "adopted: it started when this was written" : "written before it ran", ""],
      ["Stop", c.stop_pct != null ? nxPct(c.stop_pct, 0) : "—", "from the entry", ""],
      ["Benchmark", c.benchmark ? String(c.benchmark).slice(0, 8) : "none",
       c.benchmark ? "BTC-dominated card" : "nothing to beat", ""],
      ["Verdict", due[0], due[1], due[2]]]);
  }
  if (np.claim) {
    html += '<p class="nx-foot">Nexus claimed: ' + Object.keys(np.claim).map(
      k => esc(k) + " " + esc(String(np.claim[k]))).join(" · ") + "</p>";
  }
  return html;
}
function nxStrategy(nr, np) {
  const nc = (np.clones || [])[0] || null;
  const pills = nxPill(np.status) +
    (np.holds ? '<span class="nx-pill">' + esc(NX_HOLDS[np.holds] || np.holds) +
                " · paper</span>" : "") +
    (nc && nc.trading != null ? '<span class="nx-pill">' +
      (nc.trading ? "trading" : "not trading") + "</span>" : "");
  const sub = esc(nr.id) + " · proposed by Nexus in " + esc(np.origin || "—") +
    (np.since ? " · since " + esc(nxDay(np.since)) : "");
  let html = nxHero(np.title || nr.title || nr.id, pills, sub) + nxStatus(np) +
    nxVerdict(np);
  if (nc) {
    const acts = nc.activity || [];
    const closed = acts.filter(na => na.is_closed).length;
    html += nxTiles([
      ["P&L", nc.pnl != null ? nxSigned(nc.pnl) + " USDC" : "—",
       nc.pnl != null && nc.funded ? nxPct(nc.pnl / nc.funded * 100) + " of what it was given"
                                   : "", nxTone(nc.pnl)],
      ["Balance", nxMoney(nc.balance), nc.locked != null
        ? nxMoney(nc.locked) + " locked · " + nxMoney(nc.available) + " free" : "", ""],
      ["Funded", nxMoney(nc.funded), "USDC", ""],
      ["Trades", acts.length || nc.trades || 0,
       acts.length ? closed + " closed · " + (acts.length - closed) + " open" : "", ""]]) +
      nxBot(nc);
  } else if ((np.legs || []).length) {
    html += nxCardTiles(np);
  }
  if ((np.legs || []).length) {
    html += nxLegs(np) + nxLegCharts(np) + nxOrders(np);
  } else if (!nc) {
    html += '<p class="nx-foot">Nothing bought yet, and no plan written down for it.</p>';
  }
  return html + nxSampler(np);
}
function nxPanelOf(id) {
  return ((NX && NX.panels) || {})[id] || {};
}
function nxBotValue(nr) {
  const np = nxPanelOf(nr.id);
  return np.value;
}
// The overview: the account, every strategy with where it stands, and how
// Nexus has answered so far.
// One cell per strategy: what it came to, or when it will be known, or that
// nobody wrote down what would count. The operator reads this column to find
// out which of Nexus's ideas made money, which is the whole question.
function nxScore(nr) {
  const v = nr.verdict, c = nr.criterion;
  if (v) {
    const said = NX_SAID[v.verdict] || [v.verdict, ""];
    return '<b class="' + said[1].trim() + '">' + esc(said[0]) + "</b>" +
      (v.return_pct != null ? " " + esc(nxPct(v.return_pct, 2)) : "");
  }
  if (c) {
    return '<span class="nx-state">' + (c.window_days != null ? c.window_days : "?") +
      " d window" + (c.adopted ? ", adopted" : "") + "</span>";
  }
  return '<span class="nx-state">no criterion</span>';
}
function nxGeneral(np) {
  const rooms = ((NX && NX.rooms) || []).filter(nr => nr.kind === "strategy");
  const count = status => rooms.filter(nr => nr.status === status).length;
  const bots = rooms.filter(nr => nr.holds === "bot");
  const inBot = bots.reduce((sum, nr) => sum + (Number(nxBotValue(nr)) || 0), 0);
  const quiet = (np.partial || 0) + (np.failed || 0) + (np.refused || 0);
  const table = rooms.map(nr => '<div class="nx-tr"><span><button type="button" ' +
    'class="nx-pf" data-room="' + esc(nr.id) + '">' + esc(nr.title || nr.id) +
    "</button></span><span>" + esc(NX_HOLDS[nr.holds] || "—") + "</span><span>" +
    nxPill(nr.status) + "</span><span>" + (nr.invested ? esc(nxMoney(nr.invested)) + " USDC"
      : nr.proposed_share != null ? esc(nxShare(nr.proposed_share)) + " proposed" : "—") +
    '</span><span class="' + nxTone(nr.pnl).trim() + '">' +
    (nr.pnl != null ? esc(nxSigned(nr.pnl)) + " USDC"
      : nr.if_bought_pct != null ? "if bought " + esc(nxPct(nr.if_bought_pct, 2)) : "—") +
    "</span><span>" + nxScore(nr) + "</span></div>").join("");
  return nxHero("Overview", "", "Every question put to Nexus, and every strategy it proposed") +
    nxTiles([
      ["Free to trade", np.balance != null ? nxMoney(np.balance) : "—",
       np.balance_at ? "USDC, as of " + nxDay(np.balance_at) : "USDC, paper", ""],
      ["In cards", np.notional != null ? nxMoney(np.notional) : "—",
       np.book_trades != null ? np.book_trades + " orders on the account" : "", ""],
      ["In the bot", bots.length ? nxMoney(inBot) : "—",
       bots.length ? bots.map(nr => nr.title || nr.id).join(", ") : "no bot", ""],
      ["Strategies", rooms.length, count("running") + " running · " + count("proposed") +
       " proposed" + (count("paused") ? " · " + count("paused") + " paused" : ""), ""]]) +
    '<div class="nx-sec">Strategies</div>' + (rooms.length
      ? '<div class="nx-table nx-strats"><div class="nx-tr nx-th"><span>Strategy</span>' +
        "<span>Holds</span><span>State</span><span>In</span><span>P&amp;L</span>" +
        "<span>Verdict</span></div>" +
        table + "</div>"
      : '<p class="nx-foot">A strategy Nexus proposes opens as a card of its own, above.</p>') +
    '<div class="nx-sec">Nexus, every question so far</div>' +
    nxTiles([
      ["Asked", np.asked || 0, "", ""],
      ["Answered", np.answered || 0,
       np.asked ? Math.round((np.answered || 0) / np.asked * 100) + " % of them" : "", ""],
      ["Typical answer", np.median_seconds != null ? nxSecs(np.median_seconds) : "—", "", ""],
      ["No answer", quiet, (np.partial || 0) + " cut short · " + (np.failed || 0) +
       " gave up · " + (np.refused || 0) + " refused", quiet ? " nx-down" : ""]]) +
    '<div class="rely-strip">' + (np.strip || []).map(o =>
      '<i class="sq ' + esc(o) + '" title="' + esc(o) + '"></i>').join("") + "</div>" +
    '<p class="nx-foot rely-legend">' + [["answered", "answered"], ["partial", "cut short"],
      ["failed", "gave up"], ["refused", "refused"], ["waiting", "waiting"]].map(
      ([cls, word]) => '<i class="sq ' + cls + '"></i>' + word).join(" &nbsp; ") + "</p>" +
    '<div class="nx-why">' + nxSampler(np) + "</div>";
}
function nxPanel(nr, np) {
  return nr && nr.kind === "strategy" ? nxStrategy(nr, np) : nxGeneral(np);
}
// One card per room across the top: where it stands, what it holds, its name,
// and the one number that says how it is doing.
function nxCard(nr, current) {
  const fresh = nxFresh(nr.id);
  const badge = fresh ? '<span class="nx-badge" title="new since you last looked">' +
    fresh + "</span>" : "";
  const on = nr.id === current ? " on" : "";
  if (nr.kind !== "strategy") {
    const np = nxPanelOf(nr.id);
    return '<button type="button" class="nx-card' + on + '" data-room="' + esc(nr.id) + '">' +
      '<span class="nx-card-top">Everything</span><span class="nx-card-name">Overview</span>' +
      '<span class="nx-card-num">' + esc(String(np.asked || 0)) + " questions to Nexus</span>" +
      badge + "</button>";
  }
  const number = nr.pnl != null
    ? '<span class="nx-card-num' + nxTone(nr.pnl) + '">' + esc(nxSigned(nr.pnl)) +
      " USDC</span>"
    : '<span class="nx-card-num">' + (nr.proposed_share != null
        ? esc(nxShare(nr.proposed_share)) + " of account" : "nothing bought") + "</span>";
  return '<button type="button" class="nx-card' + on + '" data-room="' + esc(nr.id) +
    '" title="' + esc(nr.id) + '"><span class="nx-card-top">' + nxPill(nr.status) +
    (nr.holds ? "<span>" + esc(NX_HOLDS[nr.holds] || nr.holds) + "</span>" : "") +
    '</span><span class="nx-card-name">' + esc(nr.title || nr.id) + "</span>" + number +
    badge + "</button>";
}

// What arrived since the operator last looked at a room: Nexus's replies and
// our notes, never their own. Kept in this browser only -- a convenience, not
// state, like every other readStore on this page.
function nxFresh(id) {
  const seen = Number(readStore("qa.roomSeen." + id, "0")) || 0;
  return ((NX && NX.threads && NX.threads[id]) || []).filter(nm =>
    (nm.kind === "reply" || nm.kind === "claude_note") && nm.at &&
    Date.parse(nm.at) > seen).length;
}

// The room drawn last, so a redraw can tell a switch of room -- which opens at
// the newest message -- from a refresh, which leaves the reader where they
// were. A redraw lands every few seconds while notes and samples arrive, and a
// thread that jumped each time could not be read.
let NX_SHOWN = null, nxResizing = null;
// The two columns fill the window under the strip, so the composer sits at the
// bottom of the screen and the thread scrolls above it.
function nxFit() {
  const main = document.getElementById("nxMain");
  if (!main || !main.style || typeof main.getBoundingClientRect !== "function") return;
  if ((window.innerWidth || 0) < 1100) { main.style.height = ""; return; }
  const top = main.getBoundingClientRect().top + (window.scrollY || 0);
  main.style.height = Math.max(480, Math.round((window.innerHeight || 0) - top - 18)) + "px";
}

function renderRooms(data) {
  NX = data || { rooms: [], threads: {}, panels: {} };
  const rooms = NX.rooms || [];
  let current = readStore("qa.room", "general");
  if (!rooms.some(nr => nr.id === current)) current = rooms.length ? rooms[0].id : "general";
  const thread = (NX.threads || {})[current] || [];
  if (!document.getElementById("panel-nexus").hidden) {
    const newest = thread.reduce((n, nm) => Math.max(n, Date.parse(nm.at || "") || 0), 0);
    writeStore("qa.roomSeen." + current, newest);
  }
  document.getElementById("roomList").innerHTML =
    rooms.map(nr => nxCard(nr, current)).join("");
  const shown = rooms.find(nr => nr.id === current) ||
    { id: "general", title: "General", kind: "general" };
  const chat = document.getElementById("roomChat");
  const panel = document.getElementById("roomPanel");
  const switched = NX_SHOWN !== current;
  const atEnd = !chat.scrollHeight ||
    chat.scrollHeight - chat.scrollTop - chat.clientHeight < 60;
  const chatAt = chat.scrollTop, panelAt = panel.scrollTop;
  nxFit();
  chat.innerHTML = thread.length ? thread.map(nm => nxBubble(nm, current)).join("")
                                 : '<div class="empty">Nothing here yet.</div>';
  chat.scrollTop = switched || atEnd ? chat.scrollHeight : chatAt;
  panel.innerHTML = nxPanel(shown, (NX.panels || {})[current] || {});
  panel.scrollTop = switched ? 0 : panelAt || 0;
  NX_SHOWN = current;
  const total = rooms.reduce((n, nr) => n + nxFresh(nr.id), 0);
  const badge = document.getElementById("nexusN");
  if (badge) { badge.textContent = total ? String(total) : ""; badge.hidden = !total; }
  nxBindComposer(current);
}
window.renderRooms = renderRooms;
window.addEventListener("resize", () => {
  clearTimeout(nxResizing);
  nxResizing = setTimeout(() => {
    if (NX && !document.getElementById("panel-nexus").hidden) renderRooms(NX);
  }, 150);
});

// The one line the tab says about itself: why it is empty, or nothing. It is a
// status, not a mark the operator can clear, so it shows exactly when there is
// something to say and is never revealed unconditionally
// (tests/repo/test_live_server.py counts those).
function nxSay(message) {
  const note = document.getElementById("roomsNote");
  note.textContent = message || "";
  note.hidden = !message;
}

function loadRooms() {
  if (!NX_LOCAL || typeof fetch !== "function") {
    nxSay("The rooms live in the running console, not in this file. " +
          "Start console.cmd and open http://127.0.0.1:8787/.");
    return;
  }
  fetch("/rooms.json", { cache: "no-store" })
    .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
    .then(data => { nxSay(""); renderRooms(data); })
    .catch(e => nxSay("Could not load the rooms: " + e.message));
}

document.getElementById("roomList").addEventListener("click", e => {
  const b = e.target.closest("[data-room]");
  if (!b) return;
  writeStore("qa.room", b.dataset.room);
  renderRooms(NX);
});
// A line naming another room -- a pointer, "it opened STR-0003", a strategy in
// General's portfolio -- takes the operator there.
function nxGoInto(e) {
  const go = e.target.closest(".nx-goto, .nx-pf");
  if (!go) return false;
  writeStore("qa.room", go.dataset.room);
  renderRooms(NX);
  return true;
}
document.getElementById("roomPanel").addEventListener("click", nxGoInto);
document.getElementById("roomChat").addEventListener("click", e => {
  if (nxGoInto(e)) return;
  const b = e.target.closest(".nx-more");
  if (!b || !b.previousElementSibling) return;
  const body = b.previousElementSibling;
  body.classList.toggle("nx-clamp");
  b.textContent = body.classList.contains("nx-clamp") ? b.dataset.label : "▴ less";
});

/* The composer: the operator's feedback for the room on screen. It is the
   console's one write, so it goes through every door serve.py keeps -- a
   token asked for at the moment of sending, a JSON body, this machine only. */
let nxReloadWhenDone = false, nxSending = false;

function nxTyping() {
  const draft = document.getElementById("nxDraft");
  return !!(draft && document.activeElement === draft &&
            String(draft.value || "").trim());
}
// A page update never lands under a note being written. The draft would
// survive -- it is stored as it is typed -- but the operator's cursor would not.
function nxReloadIfDue() {
  if (!nxReloadWhenDone || nxSending || nxTyping()) return;
  writeStore("qa.scroll", window.scrollY);
  location.reload();
}
function nxBindComposer(room) {
  const form = document.getElementById("nxCompose");
  const draft = document.getElementById("nxDraft");
  form.hidden = !NX_LOCAL;
  if (form.dataset.room === room) return;
  if (form.dataset.room) writeStore("qa.draft." + form.dataset.room, draft.value || "");
  form.dataset.room = room;
  draft.value = readStore("qa.draft." + room, "");
}
// Asked for at the moment of sending, never baked into the page: a tab left
// open across a console restart would otherwise hold a token the new process
// never issued, and every note would bounce.
function nxPost(room, text) {
  return fetch("/token", { cache: "no-store" })
    .then(r => r.ok ? r.json()
                    : Promise.reject(new Error("the console gave no token (" + r.status + ")")))
    .then(t => fetch("/notes", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-QA-Token": t.token },
      body: JSON.stringify({ room: room, text: text }),
    }))
    .then(r => r.ok ? r.json()
                    : r.json().catch(() => ({})).then(b =>
                        Promise.reject(new Error(b.error || ("HTTP " + r.status)))));
}
// On window so a test can run the page's own send path over a stub fetch and
// hold what it sends against what serve.py accepts.
window.nxPost = nxPost;
document.getElementById("nxDraft").addEventListener("input", e => {
  const room = document.getElementById("nxCompose").dataset.room;
  if (room) writeStore("qa.draft." + room, e.target.value);
});
document.getElementById("nxDraft").addEventListener("keydown", e => {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
    e.preventDefault();
    document.getElementById("nxSend").click();
  }
});
document.getElementById("nxDraft").addEventListener("blur",
  () => setTimeout(nxReloadIfDue, 800));
document.getElementById("nxCompose").addEventListener("submit", e => {
  e.preventDefault();
  const form = document.getElementById("nxCompose");
  const draft = document.getElementById("nxDraft");
  const button = document.getElementById("nxSend");
  const status = document.getElementById("nxSendNote");
  const room = form.dataset.room;
  const text = String(draft.value || "").trim();
  if (!room || !text || nxSending) return;
  nxSending = true;
  button.disabled = true;
  status.textContent = "sending…";
  nxPost(room, text)
    .then(() => {
      draft.value = "";
      writeStore("qa.draft." + room, "");
      status.textContent = "saved ✓ — Claude reads it when you ask";
      loadRooms();
    })
    .catch(err => { status.textContent = "not sent: " + err.message; })
    .finally(() => { nxSending = false; button.disabled = false; nxReloadIfDue(); });
});
if (NX_LOCAL) loadRooms();

/* ---------- two tabs ---------- */
const PANELS = { overview: "panel-overview", findings: "panel-findings",
                stats: "panel-stats", nexus: "panel-nexus",
                legend: "panel-legend" };

function showTab(name) {
  if (!PANELS[name]) name = "overview";
  document.querySelectorAll("#tabs button").forEach(b =>
    b.setAttribute("aria-selected", String(b.dataset.tab === name)));
  Object.entries(PANELS).forEach(([tab, id]) => {
    const el = document.getElementById(id);
    if (el) el.hidden = tab !== name;
  });
  // Two sections under one tab. The operator asked for fewer things to read,
  // not more places to look, so "how it works" sits above "what the badges
  // mean" rather than becoming a fifth tab.
  const help = document.getElementById("panel-help");
  if (help) help.hidden = name !== "legend";
  // The Nexus tab is a chat beside a dashboard and takes the whole width;
  // every other tab keeps the column it reads best in.
  const wrap = document.getElementById("wrap");
  if (wrap) wrap.dataset.tab = name;
  writeStore("qa.tab", name);
  if (name === "nexus") { NX_SHOWN = null; loadRooms(); }
}
window.showTab = showTab;
document.getElementById("tabs").addEventListener("click", e => {
  const b = e.target.closest("button");
  if (b) showTab(b.dataset.tab);
});
showTab(readStore("qa.tab", "overview"));

/* ---------- the bell: what they said while you were looking elsewhere ----------
   Read state is per browser, not per user: a reading aid, not a fact about
   the work. So it lives in localStorage and errs toward showing too much. */
function seenAt() { return Number(readStore("qa.seenAt", "0")) || 0; }

/* The one read switch. The bell's "Mark all as read" and the "changed since
   read" chip are two doors onto the same mark, and two copies of this line
   would be two ideas of when you last looked. */
function markRead() {
  writeStore("qa.seenAt", Date.now());
  paintInbox();
  applyFilters();
}

function unread() {
  return D.findings.map(f => ({ f: f, at: newestFromThem(f) }))
    .filter(x => x.at > seenAt())
    .sort((a, b) => b.at - a.at);
}

function when(ms) {
  const secs = Math.max(0, (Date.now() - ms) / 1000);
  if (secs < 90) return "just now";
  if (secs < 5400) return Math.round(secs / 60) + " min ago";
  if (secs < 172800) return Math.round(secs / 3600) + " h ago";
  return new Date(ms).toISOString().slice(0, 10);
}

function paintBell() {
  const items = unread();
  const badge = document.getElementById("bellN");
  badge.textContent = String(items.length);
  badge.hidden = items.length === 0;
  box.querySelectorAll(".finding").forEach(el => {
    const mark = el.querySelector("[data-newreply]");
    if (mark) mark.hidden = Number(el.dataset.vendorAt || 0) <= seenAt();
  });
  return items;
}

function paintInbox() {
  const items = paintBell();
  const panel = document.getElementById("inbox");
  if (!items.length) {
    panel.innerHTML = '<div class="empty">Nothing new since you last looked.</div>'
      + '<div class="seenline">' + (seenAt()
          ? "read up to " + new Date(seenAt()).toISOString().slice(0, 16)
            .replace("T", " ") + " UTC &middot; " + location.host
          : "nothing marked read yet &middot; " + location.host) + '</div>';
    return;
  }
  const seen = seenAt();
  const footer = '<div class="seenline">' + (seen
      ? "read up to " + new Date(seen).toISOString().slice(0, 16).replace("T", " ")
        + " UTC &middot; " + location.host
      : "nothing marked read yet &middot; " + location.host) + '</div>';
  panel.innerHTML = '<h4>Replies from Cymetica</h4>'
    + items.slice(0, 8).map(function (x) {
        const filed = (x.f.filed || []).map(r => "#" + r.report_id).join(", ");
        return '<button class="item" data-go="' + esc(x.f.id) + '">'
             + '<span class="item-t">' + esc(x.f.headline || x.f.title) + '</span>'
             + '<span class="item-m">' + when(x.at)
             + (filed ? " &middot; " + filed : "")
             + " &middot; " + esc(x.f.display_state) + '</span></button>';
      }).join("")
    + (items.length > 8
        ? '<div class="empty">and ' + (items.length - 8) + ' more</div>' : "")
    + '<button class="seen" data-seen>Mark all as read</button>'
    + footer;
}

document.getElementById("bell").addEventListener("click", () => {
  const panel = document.getElementById("inbox");
  const opening = panel.hidden;
  if (opening) paintInbox();
  panel.hidden = !opening;
  document.getElementById("bell").setAttribute("aria-expanded", String(opening));
});

document.getElementById("inbox").addEventListener("click", e => {
  if (e.target.closest("[data-seen]")) {
    markRead();
    return;
  }
  const item = e.target.closest("[data-go]");
  if (!item) return;
  const row = document.getElementById("f-" + item.dataset.go);
  document.getElementById("inbox").hidden = true;
  document.getElementById("bell").setAttribute("aria-expanded", "false");
  showTab("findings");
  if (row) {
    row.hidden = false;   // a settled row must still be reachable from here
    row.open = true;
    row.scrollIntoView({ behavior: "smooth", block: "center" });
  }
});

document.addEventListener("click", e => {
  if (!e.target.closest("#inbox") && !e.target.closest("#bell")) {
    document.getElementById("inbox").hidden = true;
    document.getElementById("bell").setAttribute("aria-expanded", "false");
  }
});
paintBell();


/* ---------- the legend's two generated parts ----------
   Both were written out by hand and both had gone stale, in the way a second
   copy of a fact always does. The verdict table listed six kinds and the code
   serves seven -- `websocket` was missing while 16 endpoints fell into it --
   and its wording had drifted from VERDICT_WORDS. The worked example was
   wrong in every figure: "Markets & prices, 64%, 16 published, 7 of 11
   answered" against a live 12 published and 7 of 7. So both are drawn from
   the same data the cards are, and cannot drift again. */
function paintVerdicts() {
  const seen = {};
  (D.sections || []).forEach(s => Object.keys(s.verdicts || {}).forEach(k => {
    seen[k] = (seen[k] || 0) + s.verdicts[k];
  }));
  document.getElementById("verdicts").innerHTML = ORDER.map(k =>
    `<tr><td><i class="seg-${k}"></i></td>`
    + `<td>${esc(VERDICT_WORDS[k])}</td>`
    + `<td>${seen[k] || 0} today</td></tr>`).join("");
}
paintVerdicts();


/* ---------- live updates ----------
   Only when served by scripts/serve.py. Opened as a file or published as an
   Artifact there is no /events endpoint, EventSource never connects, and the
   page stays exactly the static page it always was. One file serves both, and
   the indicator says which one you are looking at rather than leaving you to
   wonder whether the numbers are current. */
(function live() {
  const dot = document.createElement("span");
  dot.className = "live";
  dot.innerHTML = '<i></i><span>static snapshot</span>';
  const meta = document.getElementById("meta");
  if (meta) meta.appendChild(dot);
  // Only localhost runs the server. Trying anywhere else -- opened as a file,
  // or published as an Artifact -- would fail and leave the indicator saying
  // "reconnecting", which claims a live page that is never coming. A snapshot
  // that says it is a snapshot is honest; one that says it is reconnecting is
  // not.
  const LOCAL = ["127.0.0.1", "localhost", "[::1]"];
  if (!window.EventSource || !LOCAL.includes(location.hostname)) return;

  // What THIS page was rendered from, baked in at render time. The client held
  // the digest in a variable it overwrote on every hello -- so after the
  // server restarted, the tab reconnected, adopted the new digest, said "live"
  // and never reloaded. It then showed markup from before the restart while
  // claiming to be current: the one failure this console exists to prevent,
  // happening inside the console. Comparing against what the page actually IS
  // cannot drift.
  const RENDERED_AS = "__DIGEST__";
  const say = (cls, words) => {
    dot.className = "live " + cls;
    dot.innerHTML = '<i></i><span>' + words + '</span>';
  };
  let src;
  try { src = new EventSource("/events"); } catch (_) { return; }
  const catchUp = e => {
    say("on", "live");
    if (!e.data || e.data === RENDERED_AS) return;
    // Not under a note being written: the reload waits until the operator is
    // done (nxReloadIfDue), and the draft is stored as it is typed anyway.
    if (nxTyping() || nxSending) { nxReloadWhenDone = true; return; }
    writeStore("qa.scroll", window.scrollY);
    location.reload();
  };
  // Both events take the same path on purpose: a hello arriving after a
  // dropped connection carries exactly the information a missed change would
  // have, and treating it as merely a greeting is how the tab went stale.
  src.addEventListener("hello", catchUp);
  src.addEventListener("changed", catchUp);
  // The rooms move on their own event and redraw in place: no reload, so a
  // note being typed is never thrown away by somebody else's message. A hello
  // after a dropped connection may have missed one, so it refreshes too.
  src.addEventListener("rooms", () => loadRooms());
  src.addEventListener("hello", () => loadRooms());
  src.onerror = () => say("off", "reconnecting");
  window.addEventListener("beforeunload", () => src.close());
})();


/* ---------- Stats: five figures, each one derived where it lives ----------
   One hue for every bar, because every chart here is a single series: the
   colours on this page already mean something (green passes, red fails), and
   a bar borrowing one would say a thing it does not mean. Numbers wear text
   colours, never the mark's. */
const money = n => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, " ");

function bars(rows, label) {
  if (!rows.length) return '<p class="blurb">Nothing recorded yet.</p>';
  const top = Math.max.apply(null, rows.map(r => r.v)) || 1;
  const w = 100 / rows.length;
  return `<svg class="bars" viewBox="0 0 100 34" preserveAspectRatio="none"
      role="img" aria-label="${esc(label)}">
    ${rows.map((r, i) => {
      const h = Math.max(1.2, (r.v / top) * 26);
      return `<rect x="${(i * w) + w * 0.18}" y="${28 - h}" width="${w * 0.64}"
        height="${h}" rx="0.8" fill="var(--accent)"><title>${esc(r.k)}: ${esc(r.t || r.v)}</title></rect>`;
    }).join("")}
    <line x1="0" y1="28" x2="100" y2="28" stroke="var(--line)" stroke-width="0.4"/>
  </svg>
  <div class="bars-x">${rows.map(r => `<span>${esc(r.k.slice(5))}</span>`).join("")}</div>`;
}

function statBlocks() {
  const S = D.stats || {};
  const rw = S.rewards || {}, fx = S.fixes || {}, ts = S.tests || {};
  const ch = S.channels || {}, pr = S.process || [];
  const out = [];

  out.push(`<section class="stat">
    <h3>Rewards</h3>
    <div class="hero">${esc(money(rw.paid_total || 0))} <span>${esc(rw.currency || "")}</span></div>
    <dl class="figs">
      <div><dt>paid</dt><dd>${rw.paid_n || 0} reports</dd></div>
      <div><dt>pending</dt><dd>${rw.pending_n || 0} fixed, not yet paid</dd></div>
      <div><dt>rejected</dt><dd>${rw.invalid_n || 0}</dd></div>
    </dl>
    ${bars((rw.by_day || []).map(d => ({k: d.day, v: d.amount, t: money(d.amount) + " " + (rw.currency || "")})), "rewards by day")}
    ${rw.disagrees ? `<p class="blurb warn">This does not match their own
      figure. They publish ${esc(money(rw.their_total))} ${esc(rw.currency || "")}
      across ${esc(String(rw.rows_they_hold))} report(s); we read
      ${esc(String(rw.rows_read))} row(s) and add up
      ${esc(money(rw.paid_total || 0))}. The number above is ours, and the gap
      is the thing to look at first.</p>`
      : `<p class="blurb">Agrees with their own published total
      (${esc(money(rw.their_total))} ${esc(rw.currency || "")} over
      ${esc(String(rw.rows_they_hold))} reports).</p>`}
    <p class="blurb">Dated by the day they resolved the report; their tracker
    does not tell us when each payment landed.</p>
  </section>`);

  out.push(`<section class="stat">
    <h3>Defects fixed</h3>
    <div class="hero">${fx.verified_by_us || 0} <span>verified by us</span></div>
    <dl class="figs">
      <div><dt>verifications sent</dt><dd>${fx.told_them || 0}</dd></div>
    </dl>
    ${bars((fx.by_day || []).map(d => ({k: d.day, v: d.n})), "defects verified fixed by day")}
    <p class="blurb">A defect counts when a check that was failing passes
    again. Re-pinned definitions are not counted &mdash; there are 41 of those
    and they are our own bookkeeping, not their repairs.</p>
  </section>`);

  // Can we rely on them? One square per question, oldest first, coloured by
  // what happened to it; then one shared clock so the typical answer times
  // can be compared by eye. Drawn 2026-09-11 at the operator's word: they
  // read pictures, not tables, and asked to see Nexus beside Telegram.
  const nx = S.nexus || {}, strips = S.strips || {};
  const human = (key, name, sub) => {
    const c = ch[key] || {};
    return {name: name, sub: sub,
      squares: (strips[key] || []).map(r => ({c: r.answered ? "answered" : "waiting",
        t: r.answered ? (r.minutes != null ? "answered in " + r.minutes + " min" : "answered") : "no answer yet"})),
      minutes: c.median_minutes == null ? null : c.median_minutes,
      answered: (c.asked || 0) - (c.unanswered || 0), asked: c.asked || 0};
  };
  const channelRows = [
    {name: "Nexus", sub: "their AI, ask_nexus_deep",
     squares: (nx.questions || []).map(q => ({c: q.outcome,
       t: q.id + " - " + q.outcome + (q.seconds != null ? " - " + Math.round(q.seconds) + " s"
          : (q.upper != null ? " - looked at only after " + Math.round(q.upper / 60) + " min" : ""))})),
     minutes: nx.median_seconds == null ? null : nx.median_seconds / 60,
     answered: nx.answered || 0, asked: nx.asked || 0},
    human("telegram", "Telegram", "the operator's thread"),
    human("a2a", "a2a", "bounty inbox"),
  ];
  const squaresOf = list => list.map(q => `<i class="sq ${esc(q.c)}" title="${esc(q.t)}"></i>`).join("");
  const rowsHtml = channelRows.map(r => `<div class="rely-row">
      <div class="rely-name">${esc(r.name)}<span>${esc(r.sub)}</span></div>
      <div class="rely-strip">${r.squares.length ? squaresOf(r.squares) : '<span class="blurb">nothing asked yet</span>'}</div>
      <div class="rely-n"><b>${r.answered}</b>/${r.asked}<span>answered</span></div>
    </div>`).join("");
  const LOGDAY = Math.log10(1440);
  const X = m => 4 + 90 * Math.log10(Math.min(1440, Math.max(1, m))) / LOGDAY;
  const dots = channelRows.filter(r => r.minutes != null);
  const axis = `<svg class="rely-axis" viewBox="0 0 100 ${12 + dots.length * 7}" role="img"
      aria-label="typical answer time by channel">
    <line x1="4" y1="6" x2="94" y2="6" stroke="var(--line)" stroke-width="0.5"/>
    ${[[1, "1 min"], [10, "10 min"], [60, "1 hour"], [1440, "1 day"]].map(([m, l]) =>
      `<line x1="${X(m)}" y1="4.6" x2="${X(m)}" y2="7.4" stroke="currentColor" stroke-width="0.4" opacity="0.5"/>
       <text x="${X(m)}" y="3" font-size="2.6" text-anchor="middle" fill="currentColor" opacity="0.6">${l}</text>`).join("")}
    ${dots.map((r, i) => {
      const x = X(r.minutes), right = x > 70, y = 12 + i * 7;
      const shown = r.minutes < 1 ? "under 1 min" : r.minutes < 90 ? Math.round(r.minutes) + " min"
                  : (r.minutes / 60).toFixed(1) + " h";
      return `<line x1="${x}" y1="6" x2="${x}" y2="${y}" stroke="var(--accent)" stroke-width="0.3" opacity="0.5"/>
        <circle cx="${x}" cy="${y}" r="1.7" fill="var(--accent)"/>
        <text x="${right ? x - 2.8 : x + 2.8}" y="${y + 1}" font-size="3" text-anchor="${right ? "end" : "start"}"
          fill="currentColor">${esc(r.name)}: ${esc(shown)}</text>`;
    }).join("")}
  </svg>`;
  out.push(`<section class="stat wide">
    <h3>Can we rely on them?</h3>
    <div class="rely">${rowsHtml}</div>
    ${dots.length ? axis : ""}
    <div class="rely-legend"><span><i class="sq answered"></i>answered</span>
      <span><i class="sq partial"></i>cut short</span><span><i class="sq failed"></i>failed</span>
      <span><i class="sq refused"></i>refused to start</span><span><i class="sq waiting"></i>no answer yet</span></div>
    <p class="blurb">One square per question, oldest first. The dots are each
    channel's typical answer time; for Nexus only from ${nx.measured || 0}
    question(s) watched from the start.</p>
  </section>`);

  // What we test: every part of the platform the inventory knows, green where
  // checks run, red where one is failing, grey where nothing has been written.
  const secs = D.sections || [];
  const tested = secs.filter(s => s.checks && s.checks.total);
  out.push(`<section class="stat wide">
    <h3>What we test</h3>
    <div class="hero">${tested.length} <span>of ${secs.length} parts of the platform have checks</span></div>
    <div class="cov">${secs.map(s => {
      const n = (s.checks && s.checks.total) || 0, bad = (s.checks && s.checks.failed) || 0;
      return `<div class="cov-cell ${n ? (bad ? "bad" : "ok") : "none"}"
        title="${esc(s.title || s.id)}: ${n} check(s)${bad ? ", " + bad + " failing" : ""}">
        <b>${n || ""}</b><span>${esc(s.title || s.id)}</span></div>`;
    }).join("")}</div>
  </section>`);

  if (pr.length) {
    out.push(`<details class="stat wide"><summary>For us: what the deep pass costs</summary>
      <table class="stat-t">
        <thead><tr><th>pass</th><th>claimed</th><th>real</th>
          <th>rejected by the readers</th><th>fixed</th><th>minutes</th></tr></thead>
        <tbody>${pr.map(p => `<tr><td>${esc(p.run || "?")}</td>
          <td>${p.claimed}</td><td>${p.real}</td><td>${p.overturned}</td>
          <td>${p.fixed}</td><td>${p.elapsed_min == null ? "&mdash;" : p.elapsed_min}</td></tr>`).join("")}</tbody>
      </table>
    </details>`);
  }

  // Memecoiny: does FOMO Radar's `hot` field actually predict a move? Read
  // 2026-09-13. `S.fomo` is null when the diary has never been written --
  // "never watched" and "watched, nothing hit yet" must not look the same.
  const fm = S.fomo;
  if (fm) {
    const horizons = Object.keys(fm.horizons || {}).sort();
    out.push(`<section class="stat wide">
      <h3>Memecoiny &mdash; FOMO Radar's "hot" signal</h3>
      <div class="hero">${fm.tracked || 0} <span>signal(s) tracked</span></div>
      ${horizons.length ? `<dl class="figs">
        ${horizons.map(h => {
          const row = fm.horizons[h];
          const hit = row.hit_rate == null ? "&mdash;" : Math.round(row.hit_rate * 100) + "%";
          const mean = row.mean_pct == null ? "&mdash;" : row.mean_pct.toFixed(1) + "%";
          return `<div><dt>${esc(h)}</dt><dd>${row.resolved} resolved,
            ${hit} hit rate, ${mean} avg return</dd></div>`;
        }).join("")}
      </dl>` : `<p class="blurb">Tracking signals; none has reached its first
        checkpoint (1h) yet.</p>`}
      ${horizons.filter(h => (fm.horizons[h].top || []).length).map(h => {
        const row = fm.horizons[h];
        return `<details><summary>${esc(h)}: best and worst since signal</summary>
          <table class="stat-t"><thead><tr><th>symbol</th><th>conviction at signal</th>
            <th>return</th></tr></thead><tbody>
            ${row.top.map(c => `<tr><td>${esc(c.symbol || "?")}</td>
              <td>${c.conviction == null ? "&mdash;" : c.conviction}</td>
              <td>${c.return_pct.toFixed(1)}%</td></tr>`).join("")}
            ${row.bottom.map(c => `<tr><td>${esc(c.symbol || "?")}</td>
              <td>${c.conviction == null ? "&mdash;" : c.conviction}</td>
              <td>${c.return_pct.toFixed(1)}%</td></tr>`).join("")}
          </tbody></table>
        </details>`;
      }).join("")}
      <p class="blurb">Return is ours, computed from the price at the moment
      the signal fired to the price at each checkpoint &mdash; not their own
      rolling %-change window, which is relative to whenever we happen to ask.
      A hit is a return at or above ${fm.hit_threshold != null ? fm.hit_threshold : 20}%.</p>
    </section>`);
  }
  return out.join("");
}
document.getElementById("stats").innerHTML = statBlocks();

// The table the operator sets /model and /effort from, drawn from the
// operating rules rather than retyped beside them.
document.getElementById("models").innerHTML =
  "<thead><tr><th>task</th><th>model</th><th>effort</th></tr></thead><tbody>"
  + ((D.help && D.help.models) || []).map(r =>
      `<tr><td>${esc(r.task)}</td><td>${esc(r.model)}</td><td>${esc(r.effort)}</td></tr>`
    ).join("")
  + "</tbody>";

(function restoreScroll() {
  const y = Number(readStore("qa.scroll", "0")) || 0;
  if (y > 0) { window.scrollTo(0, y); writeStore("qa.scroll", 0); }
})();
</script>
"""


def payload_hash(payload: dict) -> str:
    """A stable hash of everything the page shows, minus when it was made.

    Embedded in the rendered file so a committed dashboard can be checked
    against a re-render (critique gap 9). Without it, nothing catches a
    dashboard that has fallen behind the ledger it claims to display --
    exactly the drift behind 16 rows on the filter, 6 in the tiles and 20 in
    the ledger.
    """
    import hashlib

    stable = {k: v for k, v in payload.items() if k != "generated_at"}
    blob = json.dumps(stable, sort_keys=True, ensure_ascii=False)
    # The template is part of what the page shows. Hashing only the data let a
    # presentation change land in the code with the committed page still built
    # from the old template, and rule 12's check saw nothing -- which is how
    # nine unstyled state chips could have survived a re-render.
    blob += "\n" + hashlib.sha256(TEMPLATE.encode("utf-8")).hexdigest()
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def render(payload: dict | None = None) -> str:
    payload = payload if payload is not None else build_payload()
    digest = payload_hash(payload)
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return (TEMPLATE.replace("__DIGEST__", digest).replace("__DATA__", data)
            + f"\n<!-- qa-payload-sha256: {digest} -->\n")


if __name__ == "__main__":
    target = out_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = build_payload()
    target.write_text(render(payload), encoding="utf-8")
    try:
        shown = target.relative_to(REPO_ROOT)
    except ValueError:
        shown = target
    print(f"-> {shown}  ({target.stat().st_size // 1024} KB)")
    print(f"   payload sha256 {payload_hash(payload)[:16]}  "
          f"{sum(payload['display_counts'].values())} rows  "
          f"run {payload['run_id'] or '(none admissible)'} "
          f"at level {payload['run_level']}")

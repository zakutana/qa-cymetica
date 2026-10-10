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
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.findings import TAG_ORDER, TAGS  # noqa: E402

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
    "mcp.fund_research": "mcp",
    "mcp.trust_ladder": "identity_trust", "rest.agents": "agents",
    "rest.clob": "clob", "rest.markets": "markets", "rest.account": "account",
    "rest.arena": "arena", "rest.backtest": "backtest",
    "rest.event_cards": "event_cards", "ws.feeds": "realtime",
    "chain.launchpad": "launchpad",
    "funding.withdraw": "funding", "funding.deposit": "funding",
    "platform.ai_native_proof": "provenance", "platform.status": "swaps",
    "rest.support": "support", "rest.movers": "movers",
    "rest.clones": "clones",
    "rest.build_it_better": "build_it_better",
    # A Build it Better app (ET-26608), so its checks sit on that tile.
    "rest.gem_screener": "build_it_better",
    # Chart Analyzer is one too (ET-28324).
    "rest.chart_analyzer": "build_it_better",
    # And the Supply Analyzer (ET-28934).
    "rest.supply_analyzer": "build_it_better",
    # The Agent League we play (scripts/league.py) has no checks of its own yet; the tile is
    # where they will sit, beside the other agents' surfaces.
    "rest.agent_league": "clones",
    # Backtest Rally has no tile of its own yet; its checks are shown on that one.
    "rest.research_backtest": "build_it_better",
    "rest.creator": "creator", "rest.head_to_head": "head_to_head",
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


def _last_full_run(run: dict) -> dict:
    """The newest run of the whole suite before `run`, admissible at R.

    A narrow sweep's run holds a handful of checks, and the tiles read
    "untested" on nearly every area until the next full run (2026-09-25: 27
    of 28). What the tiles need is each check's newest result, so the page's
    run is laid over the last full one. Only an admissible record counts: a
    --collect-only record from tests/repo is newer and holds nothing.
    """
    from qa.state import admissibility, state_dir

    before = str(run.get("run_id") or "~")
    for path in sorted((state_dir() / "runs").glob("run-*.json"), reverse=True):
        if path.stem >= before:
            continue
        try:
            candidate = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if (candidate.get("selector_full") and candidate.get("results")
                and admissibility(candidate).level):
            return candidate
    return {}


def _tests_by_section(run: dict, earlier: dict | None = None) -> dict[str, list[dict]]:
    """The checks a run adjudicated, per tile, each able to say what it looks at.

    Deduped by nodeid: a result is written per phase, and a tile listing the
    same check three times is a tile nobody trusts. Self-tests are dropped --
    they measure us, and 448 of them under "Support desk" is the loudest
    possible wrong number. A check `run` did not include comes from `earlier`
    (the last full run) with `stale_at`, the moment it was last run.
    """
    catalogue = _test_catalogue()
    questions = _claim_questions()
    out: dict[str, list[dict]] = {}
    seen: set[str] = set()
    ran = {r.get("nodeid") for r in run.get("results", [])}
    older_at = (earlier or {}).get("finished_at") or (earlier or {}).get("started_at")
    results = list(run.get("results", [])) + [
        {**r, "_stale_at": older_at} for r in (earlier or {}).get("results", [])
        if r.get("nodeid") not in ran]
    for result in results:
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
            "stale_at": result.get("_stale_at"),
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
        "process": _process_rows(),
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
    # Rewards for posted replies, kept beside the bug figures and never added
    # into them: the operator wants to see which came from a bug and which
    # from a tweet (2026-09-25).
    creator = bounty.get("creator_rewards") or {}
    posted = creator.get("summary") or {}
    posts = {
        "paid_n": int(posted.get("paid") or 0),
        "pending_n": int(posted.get("pending") or 0),
        "et10": int(posted.get("et10") or 0),
        "etlp": int(posted.get("etlp") or 0),
        # Not the read time: every quiet poll rewrote it, so the page went
        # stale against its inputs each time (deep pass 2026-09-25, R01).
        # Only a failed read's moment, which changes when something did.
        "stale_from": (creator.get("stale_from") or creator.get("read_at")
                       if creator and creator.get("klass") != "ok" else None),
    }
    return {
        "posts": posts,
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
                  thread: dict | None = None, run: dict | None = None,
                  earlier_run: dict | None = None,
                  use_last_full_run: bool = False) -> dict:
    """Everything the page shows, derived and reconciled before it is shown.

    `use_last_full_run=False` by default: when `earlier_run` is not supplied,
    the backfill from `_last_full_run` stays off rather than being looked up.
    That backfill reads `state/runs/*.json`, and not every admissible run
    that lands there gets force-added to git -- a run whose prereg tag
    drifted is still usable here (any admissible level counts) but is never
    the one a fold commits. tests/repo/test_diaries_outside_git.py caught
    this on 2026-09-28: a narrow sweep's committed page differed from a bare
    checkout's re-render because the local machine had one such drifted-but-
    admissible full run sitting uncommitted. Same rule `build_rooms()` in
    lab_page.py already follows -- anything that can rewrite the committed
    dashboard must be provable from git alone; serve.py's live view is where
    an uncommitted local run is allowed to enrich the tiles, so it is the one
    caller that passes `use_last_full_run=True`.

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
            # A VERIFIED FIXED that stands on a definition pinned by hand and never
            # seen failing (qa/fold.py::_mark_repins) says so, with the pin's reason.
            "repinned": ((row.get("check") or {}).get("repinned")
                         if shown == "VERIFIED FIXED" else None),
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
    if earlier_run is None:
        earlier_run = (_last_full_run(run)
                       if use_last_full_run and not run.get("selector_full")
                       else {})
    tests_by_section = _tests_by_section(run, earlier_run)
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
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap">
<style>
/* The browser's own [hidden] rule is display:none at UA specificity, which
   ANY class selector beats. `.newreply { display:inline-flex }` did exactly
   that: setting el.hidden = true set the attribute and changed nothing on
   screen, so "Mark all as read" cleared the badge and left every envelope
   drawn. Published as an Artifact this never showed, because that runtime
   injects this very rule; served raw from localhost, nothing did.
   One line, first, so no later class can win against it. */
[hidden] { display: none !important; }

/* Cymetica's own palette, read off cymetica.com's main.css on 2026-09-25:
   the navy gradient, #00ff88 for what is good, #ff4444 for what is broken,
   #00cfff for what you can press. Dark only, as their site is (CLAUDE.md,
   How to work with me: the console looks like Cymetica). */
:root {
  --bg:#0a0e17; --bg-2:#0d1520; --bg-3:#111a28;
  --surface:rgba(17,24,39,.72); --surface-2:rgba(24,34,52,.85);
  --line:rgba(0,150,255,.16); --line-soft:rgba(0,150,255,.08);
  --text:#ffffff; --text-dim:#9fb3c8; --text-faint:#7b8794;
  --accent:#00cfff; --accent-dim:rgba(0,207,255,.12);
  --ok:#00ff88;   --ok-bg:rgba(0,255,136,.12);
  --auth:#00aaff; --auth-bg:rgba(0,170,255,.13);
  --warn:#ffb020; --warn-bg:rgba(255,176,32,.13);
  --bad:#ff4444;  --bad-bg:rgba(255,68,68,.14);
  --wait:#b08cff; --wait-bg:rgba(176,140,255,.14);
  --none:#4a5a6e; --none-bg:rgba(123,135,148,.16);
  --glow-ok:0 0 14px rgba(0,255,136,.35);
  --glow-bad:0 0 14px rgba(255,68,68,.3);
  --radius:8px;
  --mono:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
  --sans:"Inter",system-ui,-apple-system,"Segoe UI",sans-serif;
  --display:"Archivo Black","Inter",sans-serif;
  color-scheme:dark;
}

* { box-sizing:border-box; }
body {
  margin:0; color:var(--text); font-family:var(--sans);
  background:linear-gradient(180deg,var(--bg) 0%,var(--bg-2) 55%,var(--bg-3) 100%) fixed;
  background-color:var(--bg);
  font-size:15px; line-height:1.5; -webkit-font-smoothing:antialiased;
}
.wrap { max-width:1240px; margin:0 auto; padding:22px 20px 60px; }

.mast { border-bottom:1px solid var(--line); padding-bottom:12px; }
.mast h1 {
  font-family:var(--display); font-weight:400; font-size:clamp(24px,3.4vw,34px);
  letter-spacing:.01em; margin:0 0 4px; text-wrap:balance; text-transform:uppercase;
}
.mast h1 em { font-style:normal; color:var(--ok); text-shadow:var(--glow-ok); }
.mast .sub { color:var(--text-dim); font-size:16.0px; max-width:70ch; margin:0; }
.meta {
  display:flex; flex-wrap:wrap; gap:6px 20px; margin-top:14px;
  font-family:var(--mono); font-size:13.0px; color:var(--text-faint);
}
.meta b { color:var(--text-dim); font-weight:500; }

/* ---------- the cockpit ---------- */
.triage { margin:20px 0 6px; }
.kpis { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px; }
@media (max-width:640px) {
  .kpis .kpi { padding:11px 12px 10px; }
  .kpis .kpi-n { font-size:26px; }
  .mast h1 { padding-right:56px; font-size:22px; }
}
.kpi {
  display:flex; flex-direction:column; align-items:flex-start; gap:4px; text-align:left;
  background:var(--surface); border:1px solid var(--line); border-radius:var(--radius);
  padding:14px 16px 12px; cursor:pointer; color:var(--text); font:inherit;
  backdrop-filter:blur(12px); transition:border-color .15s, box-shadow .15s;
}
.kpi:hover { border-color:rgba(0,150,255,.4); box-shadow:0 8px 32px rgba(0,0,0,.45); }
.kpi:focus-visible { outline:2px solid var(--accent); outline-offset:2px; }
.kpi-n {
  font-family:var(--display); font-size:38px; line-height:1; letter-spacing:.01em;
  font-variant-numeric:tabular-nums;
}
.kpi-l {
  font-family:var(--mono); font-size:11.5px; text-transform:uppercase;
  letter-spacing:.08em; color:var(--text-dim);
}
.kpi.ok .kpi-n { color:var(--ok); text-shadow:var(--glow-ok); }
.kpi.bad .kpi-n { color:var(--bad); text-shadow:var(--glow-bad); }
.kpi.warn .kpi-n { color:var(--warn); }
.pills { display:flex; flex-wrap:wrap; gap:6px; margin-top:10px; }
.tri {
  font-family:var(--mono); font-size:12px; color:var(--text-dim);
  border:1px solid var(--line-soft); border-radius:20px; padding:3px 10px;
  background:var(--surface);
}
.tri .n { font-weight:700; color:var(--text); font-variant-numeric:tabular-nums; }
.tri .l { color:var(--text-faint); }
.tri.s0 .n,.tri.s1 .n { color:var(--bad); }
.tri.s2 .n,.tri.s3 .n { color:var(--warn); }
.tri.s4 .n { color:var(--text-dim); }
.tri.ok .n { color:var(--ok); }

/* Areas in columns, each a panel of compact tiles: 28 tiles in one screen.
   An area holding an open tile spans every column, so the open tile gets the
   page's width -- a tile opening inside a narrow column was the complaint
   that made open tiles take the whole row in the first place. */
.areas { columns:228px; column-gap:10px; margin-top:14px; }
.card-foot { display:flex; flex-wrap:wrap; align-items:center; gap:5px 8px; }
.card-foot .bar { flex:1 1 110px; }
.card-foot .stats { flex:0 1 auto; justify-content:flex-end; margin-left:auto; }
.chip.untested { border:0; background:none; padding:0; font-weight:400; }
.area {
  break-inside:avoid; margin:0 0 12px; padding:10px 10px 8px;
  background:rgba(13,21,32,.55); border:1px solid var(--line-soft);
  border-radius:var(--radius);
}
.area:has(.card[open]) { column-span:all; }
.area .grid { grid-template-columns:1fr; gap:6px; }
.area:has(.card[open]) .grid { grid-template-columns:repeat(auto-fill,minmax(260px,1fr)); }
h2.group {
  font-family:var(--mono); font-size:12px; text-transform:uppercase; letter-spacing:0.12em;
  font-weight:700; margin:0 0 8px; display:flex; align-items:center; gap:10px;
  color:var(--text-dim); cursor:help;
}
.map-legend {
  display:flex; flex-wrap:wrap; gap:4px 16px; margin:18px 0 0; padding-top:12px;
  border-top:1px solid var(--line-soft); font-family:var(--mono); font-size:11.5px;
  color:var(--text-faint);
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
  display:grid; grid-template-columns:repeat(auto-fill,minmax(212px,1fr));
  gap:8px; align-items:start;
}
.card {
  background:var(--surface); border:1px solid var(--line-soft); border-radius:var(--radius);
  padding:8px 10px 8px; border-top:2px solid var(--none);
  backdrop-filter:blur(12px); transition:border-color .15s, box-shadow .15s;
}
.card:hover { border-color:rgba(0,150,255,.35); box-shadow:0 8px 28px rgba(0,0,0,.4); }
/* The card is a <details> now, so the column layout lives on the summary --
   display:flex on a details element breaks the open/closed flow. */
.card > summary { display:flex; flex-direction:column; gap:5px; }
.card.h-ok{border-top-color:var(--ok)} .card.h-warn{border-top-color:var(--warn)}
.card.h-bad{border-top-color:var(--bad)} .card.h-none{border-top-color:var(--none)}
.card-top { display:flex; align-items:flex-start; justify-content:space-between; gap:10px; }
.card h3 { margin:0; font-size:13.5px; font-weight:600; line-height:1.3; cursor:help; }
.pct {
  font-family:var(--display); font-size:19px; line-height:1;
  font-variant-numeric:tabular-nums; white-space:nowrap;
}
.pct.h-ok{color:var(--ok); text-shadow:var(--glow-ok)} .pct.h-warn{color:var(--warn)}
.pct.h-bad{color:var(--bad); text-shadow:var(--glow-bad)}
.pct.h-none{color:var(--text-faint); font-size:14px; font-family:var(--mono)}
.pct small { font-size:12px; color:var(--text-faint); font-family:var(--mono); }

.bar { display:flex; height:5px; border-radius:3px; overflow:hidden; background:var(--surface-2); }
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
.pct-wrap { cursor:help; }
.pct-cap {
  font-family:var(--mono); font-size:10.5px; color:var(--text-faint);
  white-space:nowrap; letter-spacing:.02em;
}
.chip.untested {
  color:var(--text-faint); background:transparent;
  border:1px dashed var(--line); font-weight:600;
}
.blurb { font-size:13.5px; color:var(--text-dim); margin:0; line-height:1.5; }
.cd-blurb { grid-column:1 / -1; }
.stats { display:flex; flex-wrap:wrap; gap:4px; font-family:var(--mono); font-size:11px; }
.chip {
  border:1px solid var(--line); border-radius:4px; padding:1px 6px;
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
.filters button[aria-pressed="true"] {
  background:var(--ok); color:#00131c; border-color:var(--ok); font-weight:700;
  box-shadow:var(--glow-ok);
}
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
.stat h3 {
  margin:0 0 10px; font-family:var(--mono); font-size:12px; font-weight:700;
  text-transform:uppercase; letter-spacing:.1em; color:var(--text-dim);
}
.hero {
  font-family:var(--display); font-size:34px; color:var(--ok); line-height:1.1;
  text-shadow:var(--glow-ok); cursor:default;
}
.hero span { font-family:var(--mono); font-size:12px; color:var(--text-dim); text-shadow:none; }
.blurb.warn { color:var(--warn); }
.figs { display:flex; flex-wrap:wrap; gap:4px 18px; margin:10px 0 12px; }
.figs div { display:flex; gap:6px; align-items:baseline; }
.figs dt { font-size:12px; color:var(--text-faint); }
.figs dd { margin:0; font-size:12.5px; color:var(--text-dim); font-family:var(--mono); }
svg.bars { width:100%; height:80px; display:block; }
/* A few dates, not every one: twenty "MM-DD" labels at 10px ran into each other and out of
   their card (the operator, 2026-10-03). Each label sits under its own bar. */
.bars-x { position:relative; height:14px; margin-top:3px; font-family:var(--mono);
  font-size:10px; color:var(--text-faint); }
.bars-x span { position:absolute; top:0; white-space:nowrap; transform:translateX(-50%); }
.bars-x span.first { transform:none; }
.bars-x span.last { transform:translateX(-100%); }
.barwrap { position:relative; }
.bar-hit { fill:transparent; }
svg.bars rect.bar-on { filter:brightness(1.45); }
/* The hover card: the same shape as the Gem Screener's -- a dark card with the date in
   white, the value large, and a small line saying what it counts. */
.bartip { position:absolute; z-index:6; pointer-events:none; min-width:132px;
  padding:9px 12px 10px; border-radius:10px; background:#0d1424;
  border:1px solid var(--line); box-shadow:0 10px 28px rgba(0,0,0,.5);
  opacity:0; transform:translateY(4px); transition:opacity .08s, transform .08s; }
.bartip.on { opacity:1; transform:none; }
.bartip b { display:block; font-size:12.5px; color:#fff; font-weight:600; }
.bartip .v { display:block; margin-top:3px; font-family:var(--mono); font-size:16px;
  font-weight:700; color:var(--ok); }
.bartip small { display:block; margin-top:2px; font-size:11px; color:var(--text-faint); }
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
.tabs {
  display:flex; flex-wrap:wrap; gap:4px; margin:16px 0 0;
  border-bottom:1px solid var(--line);
}
.tabs button {
  background:none; border:0; border-bottom:2px solid transparent; color:var(--text-dim);
  font-family:var(--mono); font-size:13px; text-transform:uppercase; letter-spacing:.08em;
  padding:10px 14px; cursor:pointer; margin-bottom:-1px;
}
.tabs button:hover { color:var(--text); }
.tabs button[aria-selected="true"] {
  color:var(--ok); border-bottom-color:var(--ok); text-shadow:var(--glow-ok);
}
.tabs button:focus-visible { outline:2px solid var(--accent); outline-offset:-2px; }
/* The laboratory has a page of its own (/lab, served, never committed): its
   figures come from gitignored diaries, and this page hashes only what git
   holds. A link, not a tab -- styled as their green Trade button. */
.tabs .tab-link {
  margin-left:auto; align-self:center; padding:6px 14px; font-size:13px;
  font-family:var(--mono); text-transform:uppercase; letter-spacing:.06em;
  background:var(--ok); color:#00131c; text-decoration:none; font-weight:800;
  border-radius:7px; box-shadow:var(--glow-ok);
}
.tabs .tab-link:hover { background:var(--accent); }
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
  background:var(--bg-2); border:1px solid var(--line); border-radius:12px;
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
    <h1>Cymetica <em>QA</em> Console</h1>
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
    <button data-tab="legend" aria-selected="false">Guide</button>
    <a class="tab-link" href="/lab">Lab &rarr;</a>
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

  <section class="panel" id="panel-help" hidden>
  <h2 class="group">How this works</h2>

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

  <h3 class="sec">Model &amp; effort per task</h3>
  <table class="stat-t" id="models"></table>
  </section>

  <section class="panel" id="panel-legend" hidden>
  <div class="note">

    <h4>Every badge = what <b>we</b> measured &times; where it stands <b>with them</b></h4>
    <div id="axes"></div>

    <p class="lead"><span class="hi">Only one square is green:</span> our check
    passes <em>and</em> they claim a fix.</p>
    <div id="matrix"></div>

    <h4>Other marks on a row</h4>
    <div id="marks"></div>

    <h4>S0&ndash;S4 = how much damage</h4>
    <div id="sevs"></div>

    <h4>Tile chips</h4>
    <div id="cardmarks"></div>

    <h4>Tile % = published addresses that answer</h4>
    <table class="verdicts"><tbody id="verdicts"></tbody></table>

    <h4>Say this to Claude</h4>
    <div class="rb-wrap"><table class="rb">
      <tr><th>You say</th><th>What happens</th></tr>
      <tr><td>&bdquo;projdi bugy&ldquo;</td><td>Re-checks open findings, files new ones, sends verdicts.</td></tr>
      <tr><td>&bdquo;jdi do laborky&ldquo;</td><td>One lab tick with Nexus: answers, paper rooms, verdicts.</td></tr>
      <tr><td>&bdquo;jdu spat&ldquo;</td><td>Deep pass over everything unpushed; the only thing that pushes.</td></tr>
      <tr><td>&bdquo;p&rcaron;e&ccaron;ti si to&ldquo;</td><td>Reads and answers your notes in the lab rooms.</td></tr>
      <tr><td><code>console.cmd</code></td><td>Starts this page on 127.0.0.1:8787.</td></tr>
    </table></div>

    <p class="example">Paper only &middot; nothing starts by itself &middot;
    commit yes, push only in the deep pass &middot; <b>VERIFIED FIXED</b> is our
    measurement, their &ldquo;fixed&rdquo; is a claim.</p>

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
  ok:        "answers",
  auth:      "needs a key (lock works)",
  param:     "wants a parameter",
  method:    "wrong method (ours, not scored)",
  missing:   "documented, not there",
  server_error: "5xx on their side",
  unreachable: "no answer (our network)",
  unprobed:  "not simple-callable",
  websocket: "live feed",
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

  // What the bar means, one line per verdict, in the tooltip of the number:
  // the tile shows the number and the bar, the words wait for a hover.
  const legend = ORDER.filter(k => s.verdicts[k]).map(k =>
    `${s.verdicts[k]} ${VERDICT_WORDS[k]}`).join("\n");
  const addresses = `${s.endpoints_documented} addresses published`
    + (s.tools_declared ? ` · ${s.tools_declared} MCP tools` : "");

  const pct = s.reachable_pct == null
    ? `<div class="pct-wrap" title="${esc("Nothing here answers a simple call\n" + addresses)}">
       <span class="pct h-none">n/a</span></div>`
    : `<div class="pct-wrap" title="${esc(s.endpoints_reachable + " of " + s.endpoints_probed
          + " published addresses answer\n" + addresses + "\n" + legend)}">
       <span class="pct ${h}">${s.reachable_pct}<small>%</small></span></div>`;

  const checks = s.checks && s.checks.total
    ? `<span class="chip ${s.checks.failed ? "bad" : "ok"}">${s.checks.total} test${s.checks.total === 1 ? "" : "s"}${s.checks.failed ? " · "+s.checks.failed+" failing" : ""}</span>`
    : `<span class="chip untested" title="No check written for this area yet">untested</span>`;
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
        <span class="t-o"${t.stale_at ? ` title="not in the latest run; last run ${esc(stamp(t.stale_at))}"` : ""}>${esc(t.outcome)}${t.stale_at ? ` &#8635; ${esc(stamp(t.stale_at).slice(5))}` : ""}</span>
        ${t.gone ? `<span class="t-d t-gone">no longer exists &mdash; this row stands on the run that last ran it</span>`
                 : (t.doc ? `<span class="t-d">${esc(t.doc)}</span>` : "")}
        ${t.outcome === "passed" || !t.reason ? "" : `<span class="t-r">${esc(t.reason)}</span>`}
      </li>`).join("")}</ul>`
    : `<p class="blurb">No check here yet, so nothing on this tile has been verified.</p>`;

  return `<details class="card ${h}">
    <summary>
      <div class="card-top"><h3 title="${esc(s.blurb)}">${esc(s.title)}</h3>${pct}</div>
      <div class="card-foot"><div class="bar">${bar}</div>
      <div class="stats">
        ${checks}${fnd}
        ${s.verdicts.missing ? `<span class="chip bad">${s.verdicts.missing} &times; missing</span>` : ""}
      </div></div>
    </summary>
    <div class="card-detail">
      <p class="blurb cd-blurb">${esc(s.blurb)}</p>
      <section class="cd-tests"><h4 class="sec">Checks</h4>${tests}</section>
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

document.getElementById("map").innerHTML = `<div class="areas">` + D.groups.map(g => {
  const items = D.sections.filter(s => g.sections.includes(s.id));
  if (!items.length) return "";
  items.sort((a,b) => (a.reachable_pct ?? 999) - (b.reachable_pct ?? 999));
  return `<section class="area"><h2 class="group" title="${esc(g.blurb)}">`
    + `<span class="tagchip">${esc(g.tag)}</span>${esc(g.title)}</h2>`
    + `<div class="grid">${items.map(card).join("")}</div></section>`;
}).join("") + `</div>`
  // The bar's colours, once for the whole map instead of on every tile.
  + `<div class="map-legend">${ORDER.filter(k => D.sections.some(s => s.verdicts[k]))
      .map(k => `<span class="blabel"><i class="seg-${k}"></i>${VERDICT_WORDS[k]}</span>`)
      .join("")}</div>`;

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
          ${f.not_checked_in ? `<span class="unchecked" title="not re-checked by the last sweep${f.last_checked_at ? " &middot; last checked " + esc(stamp(f.last_checked_at)) : ""}">&#8635; ${f.last_checked_at ? esc(stamp(f.last_checked_at).slice(5)) : "old"}</span>` : ""}
          ${f.repinned ? `<span class="unmeasured" title="Verified under a check definition that was changed and then pinned by hand (${esc(stamp(f.repinned.at))}). Why: ${esc(f.repinned.reason)}">re-pinned</span>` : ""}
          ${(f.owed || []).map(o => `<span class="owed" title="Something is still owed on this row: the fold works it out from the events, and it stays here until an event settles it. A re-verify is cleared by a level-V run under the pinned fingerprint; a retraction by a retraction-sent event.">${esc(o)}</span>`).join("")}
          ${f.stale_from ? `<span class="unheard" title="The last attempt to read their bug tracker did not succeed, so what they say here is as of the last clean read and may have moved since. A failed read is not an empty one: nothing on the vendor's side was allowed to change on the strength of it.">their side unread &middot; since ${esc(stamp(f.stale_from))}</span>` : ""}
          ${changed ? `<span class="changed" title="${f.last_change.axis
              ? "last change: " + esc(f.last_change.from) + " &rarr; " + esc(f.last_change.to)
              : "first seen"}">${esc(when(changed))}</span>` : ""}
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

/* ---------- two tabs ---------- */
const PANELS = { overview: "panel-overview", findings: "panel-findings",
                stats: "panel-stats", legend: "panel-legend" };

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
  writeStore("qa.tab", name);
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
    writeStore("qa.scroll", window.scrollY);
    location.reload();
  };
  // Both events take the same path on purpose: a hello arriving after a
  // dropped connection carries exactly the information a missed change would
  // have, and treating it as merely a greeting is how the tab went stale.
  src.addEventListener("hello", catchUp);
  src.addEventListener("changed", catchUp);
  src.onerror = () => say("off", "reconnecting");
  window.addEventListener("beforeunload", () => src.close());
})();


/* ---------- Stats: five figures, each one derived where it lives ----------
   One hue for every bar, because every chart here is a single series: the
   colours on this page already mean something (green passes, red fails), and
   a bar borrowing one would say a thing it does not mean. Numbers wear text
   colours, never the mark's. */
const money = n => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ",");

/* ---------- the cockpit: the four numbers worth a glance ----------
   Big, and one click from the list behind each. Severity, sections with no
   check and what we filed ride underneath as small pills. */
(function cockpit() {
  const open = D.findings.filter(f => !SETTLED.has(f.display_state));
  const severe = open.some(f => /^S[01]/.test(f.severity || ""));
  const rw = (D.stats || {}).rewards || {};
  const big = (cls, n, label, tab, tip) =>
    `<button class="kpi ${cls}" data-go="${tab}" title="${esc(tip)}">`
    + `<span class="kpi-n">${n}</span><span class="kpi-l">${label}</span></button>`;
  const pill = (cls, n, label) =>
    `<span class="tri ${cls}"><b class="n">${n}</b> <span class="l">${label}</span></span>`;
  document.getElementById("triage").innerHTML =
    `<div class="kpis">`
    + big(open.length ? (severe ? "bad" : "warn") : "ok", open.length, "open findings",
          "findings", "Not yet verified fixed, withdrawn or superseded")
    + big("ok", D.display_counts["VERIFIED FIXED"] || 0, "verified fixed", "findings",
          "Our check passes under the definition it once failed under")
    + big("warn", D.display_counts["FIX CLAIMED"] || 0, "fix claimed, to verify",
          "findings", "They say fixed; our check has not agreed yet")
    + big("ok", Number(rw.paid_total || 0).toLocaleString("en-US"),
          `${esc(rw.currency || "ET10")} · bugs`, "stats", "Paid by their bounty tracker for our reports")
    + big("ok", Number((rw.posts || {}).et10 || 0).toLocaleString("en-US"),
          "ET10 · tweets", "stats", "Paid for replies we posted from the creator dashboard, plus the same in ETLP")
    + `</div><div class="pills">`
    + SEV.map(([k, l, c]) => pill(c, D.by_severity[k] || 0, l)).join("")
    + pill("", D.sections.filter(s => !(s.checks && s.checks.total)).length, "areas with no checks")
    + pill("", D.findings.filter(f => f.filed && f.filed.length).length, "filed to their tracker")
    + `</div>`;
  document.getElementById("triage").addEventListener("click", e => {
    const b = e.target.closest ? e.target.closest("[data-go]") : null;
    if (b) showTab(b.dataset.go);
  });
})();

function longDay(k) {
  const d = new Date(k + "T00:00:00Z");
  return isNaN(d) ? k : d.toLocaleDateString("en-US", {weekday: "short", month: "short",
    day: "numeric", year: "numeric", timeZone: "UTC"});
}

// A day under every fifth bar at most, and always the first and the last.
function barLabelIndexes(n) {
  if (n <= 1) return [0];
  const step = Math.max(1, Math.ceil((n - 1) / 4));
  const out = [];
  for (let i = 0; i < n - 1; i += step) out.push(i);
  if (n - 1 - out[out.length - 1] < step / 2) out.pop();
  out.push(n - 1);
  return out;
}

function bars(rows, label) {
  if (!rows.length) return '<p class="blurb">Nothing recorded yet.</p>';
  const top = Math.max.apply(null, rows.map(r => r.v)) || 1;
  const w = 100 / rows.length;
  const marks = barLabelIndexes(rows.length);
  return `<div class="barwrap"><svg class="bars" viewBox="0 0 100 34" preserveAspectRatio="none"
      role="img" aria-label="${esc(label)}">
    ${rows.map((r, i) => {
      const h = Math.max(1.2, (r.v / top) * 26);
      return `<rect x="${(i * w) + w * 0.18}" y="${28 - h}" width="${w * 0.64}"
        height="${h}" rx="0.8" fill="var(--accent)"></rect>
        <rect class="bar-hit" x="${i * w}" y="0" width="${w}" height="34"
          data-day="${esc(longDay(r.k))}" data-val="${esc(String(r.t || r.v))}"
          data-what="${esc(label)}"></rect>`;
    }).join("")}
    <line x1="0" y1="28" x2="100" y2="28" stroke="var(--line)" stroke-width="0.4"/>
  </svg>
  <div class="bars-x">${marks.map((i, j) => `<span class="${j === 0 ? "first" : i === rows.length - 1 ? "last" : ""}"
      style="left:${j === 0 ? 0 : i === rows.length - 1 ? 100 : (i + 0.5) * w}%">${esc(rows[i].k.slice(5))}</span>`).join("")}</div>
  <div class="bartip" aria-hidden="true"></div></div>`;
}

// One hover card for every bar chart. Bars were native <title> tooltips: a delay, a grey
// box and no room for a second line.
(function () {
  // Where the card sits against its chart, in px from the chart's top edge. Above it when the
  // window has room there, below it when not -- never 0, which is on the bars (the old clamp
  // Math.max(0, -height - 6) was 0 for every height; R12, deep pass 2026-10-04).
  function tipTop(boxTop, boxHeight, tipHeight) {
    return boxTop >= tipHeight + 6 ? -tipHeight - 6 : boxHeight + 6;
  }
  function show(hit) {
    const wrap = hit.closest(".barwrap"), tip = wrap && wrap.querySelector(".bartip");
    if (!tip) return;
    tip.innerHTML = `<b>${esc(hit.dataset.day)}</b><span class="v">${esc(hit.dataset.val)}</span>`
      + `<small>${esc(hit.dataset.what)}</small>`;
    const box = wrap.getBoundingClientRect(), bar = hit.getBoundingClientRect();
    tip.classList.add("on");
    const centre = bar.left - box.left + bar.width / 2;
    const left = Math.min(Math.max(0, centre - tip.offsetWidth / 2), box.width - tip.offsetWidth);
    tip.style.left = left + "px";
    tip.style.top = tipTop(box.top, box.height, tip.offsetHeight) + "px";
    wrap.querySelectorAll("rect.bar-on").forEach(r => r.classList.remove("bar-on"));
    if (hit.previousElementSibling) hit.previousElementSibling.classList.add("bar-on");
  }
  function hide(wrap) {
    const tip = wrap.querySelector(".bartip");
    if (tip) tip.classList.remove("on");
    wrap.querySelectorAll("rect.bar-on").forEach(r => r.classList.remove("bar-on"));
  }
  document.addEventListener("mouseover", e => {
    const hit = e.target.closest && e.target.closest(".bar-hit");
    if (hit) show(hit);
  });
  document.addEventListener("mouseout", e => {
    const wrap = e.target.closest && e.target.closest(".barwrap");
    if (wrap && !(e.relatedTarget && wrap.contains(e.relatedTarget))) hide(wrap);
  });
  document.addEventListener("click", e => {
    const hit = e.target.closest && e.target.closest(".bar-hit");
    if (hit) show(hit);
  });
})();


function statBlocks() {
  const S = D.stats || {};
  const rw = S.rewards || {}, fx = S.fixes || {}, ts = S.tests || {};
  const ch = S.channels || {}, pr = S.process || [];
  const out = [];

  const posts = rw.posts || {};
  out.push(`<section class="stat">
    <h3>Rewards</h3>
    <div class="hero" title="Bugs plus tweets; the split is below">${esc(money((rw.paid_total || 0) + (posts.et10 || 0)))} <span>${esc(rw.currency || "ET10")}</span></div>
    <dl class="figs">
      <div><dt>bugs</dt><dd>${esc(money(rw.paid_total || 0))} ${esc(rw.currency || "ET10")} · ${rw.paid_n || 0} reports paid</dd></div>
      <div><dt>bugs pending</dt><dd>${rw.pending_n || 0} fixed, not yet paid · ${rw.invalid_n || 0} rejected</dd></div>
      <div class="${posts.stale_from ? "warn" : ""}" title="${esc(posts.stale_from ? "Creator dashboard unread since " + posts.stale_from + " -- these are the figures before it" : "Creator dashboard, their own summary")}"><dt>tweets</dt><dd>${esc(money(posts.et10 || 0))} ET10 + ${esc(money(posts.etlp || 0))} ETLP · ${posts.paid_n || 0} replies paid${posts.pending_n ? ` · ${posts.pending_n} awaiting check` : ""}</dd></div>
    </dl>
    ${bars((rw.by_day || []).map(d => ({k: d.day, v: d.amount, t: money(d.amount) + " " + (rw.currency || "")})), "bug rewards by day")}
    ${rw.disagrees ? `<p class="blurb warn" title="They publish ${esc(money(rw.their_total))} ${esc(rw.currency || "")} across ${esc(String(rw.rows_they_hold))} report(s); we read ${esc(String(rw.rows_read))} row(s) and add up ${esc(money(rw.paid_total || 0))}. Days are the day they resolved each report.">&ne; their total ${esc(money(rw.their_total))} ${esc(rw.currency || "")}</p>`
      : `<p class="blurb" title="Their published total, ${esc(String(rw.rows_they_hold))} reports. Days are the day they resolved each report.">= their total ${esc(money(rw.their_total))} ${esc(rw.currency || "")} &#10003;</p>`}
  </section>`);

  out.push(`<section class="stat">
    <h3>Defects fixed</h3>
    <div class="hero" title="A check that was failing passes again. Re-pinned definitions are our bookkeeping and do not count.">${fx.verified_by_us || 0} <span>verified by us</span></div>
    <dl class="figs">
      <div><dt>verifications sent</dt><dd>${fx.told_them || 0}</dd></div>
    </dl>
    ${bars((fx.by_day || []).map(d => ({k: d.day, v: d.n})), "defects verified fixed by day")}
  </section>`);

  // Can we rely on them? One square per question, oldest first, coloured by
  // what happened to it; then one shared clock so the typical answer times
  // can be compared by eye. Drawn 2026-09-11 at the operator's word: they
  // read pictures, not tables, and asked to see Nexus beside Telegram.
  const strips = S.strips || {};
  const human = (key, name, sub) => {
    const c = ch[key] || {};
    return {name: name, sub: sub,
      squares: (strips[key] || []).map(r => ({c: r.answered ? "answered" : "waiting",
        t: r.answered ? (r.minutes != null ? "answered in " + r.minutes + " min" : "answered") : "no answer yet"})),
      minutes: c.median_minutes == null ? null : c.median_minutes,
      answered: (c.asked || 0) - (c.unanswered || 0), asked: c.asked || 0};
  };
  const channelRows = [
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
    <p class="blurb">One square per question, oldest first &middot; dots = typical
    answer time &middot; Nexus is on <a href="/lab">/lab</a>.</p>
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


PAGE_DIGEST = re.compile(r"qa-payload-sha256: ([0-9a-f]{64})")


def page_digest(path: Path) -> str | None:
    """The digest the page on disk was rendered from, or None.

    `render()` writes it as the file's last line, so the file can answer for
    itself: "is what is already there this render?" -- without an opinion
    carried over from a previous process. It lived in `scripts/serve.py`,
    where the console needed it so that starting up did not rewrite a
    byte-identical page with a fresh `generated_at` and leave the tree dirty;
    it moved here on 2026-09-20 when the pre-commit hook needed the same
    question answered, because two implementations of "is the page current"
    is how the two answers start to differ.
    """
    try:
        tail = path.read_text(encoding="utf-8")[-200:]
    except OSError:
        return None
    found = PAGE_DIGEST.search(tail)
    return found.group(1) if found else None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--if-stale", action="store_true",
        help="write only when the page on disk is not this render, and say "
             "nothing when it already is. What the pre-commit hook runs.")
    args = parser.parse_args()

    target = out_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = build_payload()
    digest = payload_hash(payload)
    # `generated_at` moves on every render and is excluded from the hash, so
    # without this a hook would rewrite 684 KB on every commit and dirty the
    # tree -- which prereg.py then refuses.
    if args.if_stale and page_digest(target) == digest:
        raise SystemExit(0)
    target.write_text(render(payload), encoding="utf-8")
    try:
        shown = target.relative_to(REPO_ROOT)
    except ValueError:
        shown = target
    print(f"-> {shown}  ({target.stat().st_size // 1024} KB)")
    print(f"   payload sha256 {digest[:16]}  "
          f"{sum(payload['display_counts'].values())} rows  "
          f"run {payload['run_id'] or '(none admissible)'} "
          f"at level {payload['run_level']}")

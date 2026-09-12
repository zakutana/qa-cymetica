"""The look back, on demand, over a window the caller chooses.

    python scripts/review.py --deep-pass 30d
    python scripts/review.py --deep-pass all --lab last

[operator 2026-09-12] asked to be able to say "look back and judge how we work"
whenever they like, naming a range per area. Until now the only retrospective
was step 11 of the deep pass: welded into it, fired only at seven days or more,
one global mark, one fixed window for every area at once.

**This reports. It does not judge.** The numbers go to whoever asked for them,
the way `lab.py grade` hands back "not enough data" rather than inventing a
correlation over eight points. Nothing here writes: the checkpoint moves only
when a review has actually been WRITTEN, through `checkpoint --area`, so
peeking cannot quietly move the line the next look back draws from.

Reads only what already exists -- `deep_pass_process.passes()` out of git
history, the laboratory's own diaries -- because the instruction the week's
step gives is the one that matters here too: do not build an archive.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qa.console import printable  # noqa: E402
from qa.state import state_dir  # noqa: E402

AREAS = ("deep-pass", "lab")
SPAN = re.compile(r"^(\d+)d$")
DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def marks_path() -> Path:
    """Beside the state, never fixed at import -- the trap `keep.snapshot_dir`
    and the manifest both had to learn on the day they were written."""
    return state_dir().parent / "audits" / "review.json"


def marks() -> dict:
    """Where each area's last WRITTEN review drew its line. Read, never set."""
    try:
        loaded = json.loads(marks_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def window(spec: str, area: str, known: dict,
           now: datetime | None = None) -> tuple[datetime | None, str]:
    """Turn what the operator said into a floor, and say what it means.

    Always a floor, never a range: every way they described this was "since"
    -- last month, the whole history, since the last review. An upper bound is
    generality nobody asked for.

    `last` with no mark is the whole history AND SAYS SO. Answering "since your
    last look" with a month of findings, silently, is the one failure here that
    a reader cannot see.
    """
    now = now or datetime.now(timezone.utc)
    spec = str(spec or "").strip()

    if spec == "all":
        return None, "celá historie"
    if spec == "last":
        at = ((known.get(area) or {}).get("at") or "").strip()
        if not at:
            return None, (f"celá historie — {area} nikdy revidován, "
                          f"žádný checkpoint")
        try:
            return datetime.fromisoformat(at.replace("Z", "+00:00")), \
                f"od minulé revize ({at[:10]})"
        except ValueError:
            return None, (f"celá historie — checkpoint {area} je nečitelný "
                          f"({at!r})")
    span = SPAN.match(spec)
    if span and int(span.group(1)) > 0:
        days = int(span.group(1))
        return now - timedelta(days=days), f"posledních {days} dní"
    if DAY.match(spec):
        try:
            day = datetime.fromisoformat(spec).replace(tzinfo=timezone.utc)
        except ValueError:
            raise SystemExit(f"review: {spec!r} is not a date")
        return day, f"od {spec}"

    raise SystemExit(
        f"review: {spec!r} is not a window. Use `all`, `30d`, `last`, "
        f"or a date like 2026-09-05")


def _moment(value) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def area_deep_pass(since: datetime | None, passes=None, condition=None) -> dict:
    """Every pass in the window, and the triad's verdict over ALL of them.

    The split matters. `condition` judges the newest three finished passes, so
    handed a historical slice it would pronounce on a tail that is not current
    -- "the triad has stopped removing anything", printed under a heading about
    today, about a fortnight in March. The slice is what gets tabulated; the
    verdict is computed over the lot.
    """
    if passes is None or condition is None:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "deep_pass_process", REPO_ROOT / "scripts" / "deep_pass_process.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        passes = passes or module.passes
        condition = condition or module.condition

    every = list(passes())
    if since is None:
        rows = every
    else:
        rows = [r for r in every
                if (_moment(r.get("at")) or datetime.min.replace(
                    tzinfo=timezone.utc)) >= since]

    gap = ""
    if not rows:
        oldest = min((str(r.get("at") or "") for r in every), default="")
        gap = (f"žádný deep pass v tomhle okně; série má {len(every)} "
               f"pass(ů)" + (f", nejstarší {oldest[:10]}" if oldest else ""))

    return {"passes": rows, "every": len(every), "gap": gap,
            "condition": condition(every)}


def _within(rows, since: datetime | None, field: str = "at") -> list[dict]:
    if since is None:
        return list(rows)
    out = []
    for row in rows:
        when = _moment(row.get(field))
        if when is not None and when >= since:
            out.append(row)
    return out


def area_lab(since: datetime | None, lab=None, rooms=None, diaries=None,
             grade=None) -> dict:
    """What the laboratory did in the window, off its own append-only diaries.

    No git archaeology. The deep pass's notebook is overwritten and survives
    only as commits, which is why `deep_pass_process` walks git history -- the
    laboratory's five files are appended to and every row carries `at`, so a
    window is a filter. An earlier draft of this plan proposed `git log -p`
    over the archive for this and it would have been wasted work.

    `grade` is deliberately NOT windowed: it asks whether our ranking predicted
    the verdicts, and thinning the sample to a window is how a filter gets
    judged on four points. Its refusal below the floor is printed verbatim,
    because that refusal is the answer.
    """
    if lab is None or rooms is None:
        from qa import lab as qa_lab
        from qa import rooms as qa_rooms
        lab = lab or qa_lab.load
        rooms = rooms or qa_rooms.load
    if diaries is None:
        def diaries(name):
            try:
                return [json.loads(line) for line
                        in (state_dir() / name).read_text(
                            encoding="utf-8").splitlines() if line.strip()]
            except (OSError, json.JSONDecodeError):
                return []
    if grade is None:
        def grade():
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                "lab_cli", REPO_ROOT / "scripts" / "lab.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            from qa import backtests
            return backtests.grade(module.graded_pairs())

    lab_rows = list(lab())
    room_rows = list(rooms())
    sessions = _within([r for r in lab_rows if r.get("type") == "session"
                        and r.get("state") == "closed"], since)
    lessons = [line for row in sessions for line in (row.get("lessons") or [])]

    oldest = min((str(r.get("at") or "") for r in lab_rows), default="")
    gap = ""
    if not sessions:
        gap = (f"žádná uzavřená session v tomhle okně"
               + (f"; deník začíná {oldest[:10]}" if oldest else ""))

    try:
        graded = grade()
    except Exception as exc:  # noqa: BLE001 -- a reader that cannot run says so
        graded = {"verdict": "unavailable", "why": str(exc)[:160]}

    return {
        "sessions": sessions, "lessons": lessons, "oldest": oldest[:10],
        "rooms": _within([r for r in room_rows
                          if r.get("type") == "strategy"], since),
        "verdicts": _within([r for r in room_rows
                             if r.get("type") == "verdict"], since),
        # `question` / `answer` / `gave_up`, read off the diary rather than
        # guessed: the first draft counted `type == "ask"`, found none, and
        # printed "0 otázek Nexusovi" directly above a lesson saying one had
        # been asked. A retrospective that under-reports silently is worse than
        # one that refuses.
        "asked": _within([r for r in diaries("nexus.jsonl")
                          if r.get("type") == "question"], since),
        "answered": _within([r for r in diaries("nexus.jsonl")
                             if r.get("type") == "answer"], since),
        "gave_up": _within([r for r in diaries("nexus.jsonl")
                            if r.get("type") == "gave_up"], since),
        "backtests": _within(diaries("backtests.jsonl"), since),
        "orders": _within([r for r in diaries("paper.jsonl")
                           if r.get("type") == "intent"], since),
        "grade": graded, "gap": gap,
    }


def _render_lab(out: dict, said: str) -> str:
    lines = [f"LABORATOŘ · {said}"]
    if out["gap"]:
        lines.append(f"  {out['gap']}")
    lines.append(
        f"  {len(out['sessions'])} session(í), {len(out['rooms'])} nových "
        f"roomů, {len(out['verdicts'])} verdiktů, {len(out['backtests'])} "
        f"backtestů, {len(out['orders'])} paper příkazů")
    lines.append(
        f"  Nexus: {len(out['asked'])} otázek, {len(out['answered'])} "
        f"odpovědí, {len(out['gave_up'])} se vzdalo")
    for lesson in out["lessons"]:
        lines.append(f"  · {lesson}")
    graded = out.get("grade") or {}
    if graded.get("why"):
        lines.append(f"  filtr: {graded.get('verdict', '?')} — {graded['why']}")
    return "\n".join(lines)


def _render_deep_pass(out: dict, said: str) -> str:
    lines = [f"DEEP PASS · {said}"]
    if out["gap"]:
        lines.append(f"  {out['gap']}")
    else:
        lines.append(f"  {'pass':<22}{'claimed':>8}{'real':>6}{'over':>6}"
                     f"{'fixed':>7}{'rules':>7}")
        for row in out["passes"]:
            lines.append(
                f"  {str(row.get('run') or '?')[:22]:<22}"
                f"{_n(row.get('claimed')):>8}{_n(row.get('real')):>6}"
                f"{_n(row.get('overturned')):>6}{_n(row.get('fixed')):>7}"
                f"{_n(row.get('rule_changes')):>7}")
        lines.append(f"  {len(out['passes'])} of {out['every']} pass(es) in "
                     f"this window")
    if out.get("condition"):
        lines.append(f"  ! {out['condition']}")
    return "\n".join(lines)


def _n(value) -> str:
    return "-" if value is None else str(value)


def stamp(areas, now: datetime | None = None) -> dict:
    """Move the line, for the areas named and no others.

    The only writer here, and it runs only when a review has actually been
    WRITTEN -- the skill's last step. Stamping an area a review did not cover
    would move the line the NEXT look back draws from, and the work in between
    would never be read by anybody.
    """
    now = now or datetime.now(timezone.utc)
    known = marks()
    for area in areas:
        known[area] = {"at": now.isoformat(timespec="seconds")}
    path = marks_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(known, ensure_ascii=False, indent=1,
                               sort_keys=True) + "\n", encoding="utf-8")
    return known


def main(argv: list[str] | None = None) -> int:
    printable()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd")
    mark = sub.add_parser("checkpoint",
                          help="record that these areas were just reviewed")
    mark.add_argument("--area", action="append", default=[], choices=AREAS,
                      required=True)
    for area in AREAS:
        parser.add_argument(f"--{area}", metavar="WINDOW",
                            help="all | 30d | last | YYYY-MM-DD")
    parser.add_argument("--all", metavar="WINDOW",
                        help="the same window for every area")
    args = parser.parse_args(argv)

    if args.cmd == "checkpoint":
        known = stamp(args.area)
        print(f"review: {', '.join(sorted(args.area))} marked reviewed "
              f"({len(known)} area(s) on record)")
        return 0

    known = marks()
    now = datetime.now(timezone.utc)
    asked = {area: getattr(args, area.replace("-", "_")) or args.all
             for area in AREAS}
    if not any(asked.values()):
        print("review: name at least one area, e.g. --deep-pass 30d "
              "(or --all 30d)")
        return 2

    for area, spec in asked.items():
        if not spec:
            continue
        since, said = window(spec, area, known, now)
        if area == "deep-pass":
            print(_render_deep_pass(area_deep_pass(since), said))
        else:
            print(_render_lab(area_lab(since), said))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""What each deep pass cost and what it caught, from the passes' own notebooks.

The pass reviews the repository and never itself. It records a great deal --
every claimed gap, who voted which way, what was fixed and in which commit --
and then that file is overwritten by the next run, so the material for "is
this process still worth what it costs" exists only in git history and nothing
has ever read it.

That question is the operator's, asked on 2026-09-10: *"ten se taky umi
optimalizovat? ze treba casem zjisti ze je zbytecne porad spoustet tu triadu
agentu na verifikaci"*. It cannot be answered from one pass. It can be
answered from the series, and this prints the series:

    python scripts/deep_pass_process.py
    python scripts/deep_pass_process.py --json

The column that decides the triad's fate is `overturned` -- claims a reader
brought that two of three triage agents rejected. That is the number of false
findings the triad removed. If it is zero for three passes running, the triad
is voting unanimously on everything it sees and the second and third readers
are ceremony; `condition()` says so in one line, and dropping it then goes
through the deep pass's own rule 1c (three agents, a test naming the incident,
a paragraph in the report) rather than through anybody's impression.

It reads only committed history, so it is safe to run at any time and says the
same thing to the pass, to the console and to the operator.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROGRESS = "audits/deep-pass-progress.json"

# A pass whose triad rejected nothing for this many runs is one whose second
# and third readers have never changed an outcome.
QUIET_PASSES = 3


def _git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True,
                            text=True, encoding="utf-8", errors="replace")
    return result.stdout if result.returncode == 0 else ""


def versions() -> list[dict]:
    """Every committed state of the progress file, oldest first.

    Keyed on `run` and keeping the LAST version of each: a pass writes its
    notebook as it goes, so the same run appears in five or six commits and
    only the final one is complete.
    """
    seen: dict[str, dict] = {}
    for line in reversed(_git("log", "--format=%H", "--", PROGRESS).split()):
        blob = _git("show", f"{line}:{PROGRESS}")
        if not blob.strip():
            continue
        try:
            data = json.loads(blob)
        except json.JSONDecodeError:
            continue
        run = str(data.get("run") or data.get("at") or line[:12])
        seen[run] = data
    return list(seen.values())


def _moment(value) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def passes(all_versions: list[dict] | None = None) -> list[dict]:
    """One row per pass: what it claimed, what survived, what it cost.

    `overturned` counts claims a reader made that the triage agents rejected,
    which is the only measure of what the triad is for. `unanimous` counts the
    gaps where all three votes agreed -- a triad that is always unanimous is
    one reader with two echoes.
    """
    rows = []
    for data in (versions() if all_versions is None else all_versions):
        gaps = data.get("gaps") or []
        votes_cast = [g for g in gaps if len(_spoken(g)) == 3]
        started, ended = _moment(data.get("at")), _moment(data.get("at_finished"))
        meta = data.get("meta_tests") or {}
        rows.append({
            "run": data.get("run"),
            "at": data.get("at"),
            "finished": bool(data.get("finished")),
            "claimed": len(gaps),
            "real": sum(1 for g in gaps if g.get("verdict") == "real"),
            "minority": sum(1 for g in gaps if g.get("verdict") == "minority"),
            "dropped": sum(1 for g in gaps if g.get("verdict") == "dropped"),
            "undecided": sum(1 for g in gaps if not g.get("verdict")),
            "by_source": _count(g.get("source") for g in gaps),
            "voted": len(votes_cast),
            "unanimous": sum(1 for g in votes_cast
                             if len(set(_spoken(g))) == 1),
            # What the triad actually removed. Zero means every claim that
            # reached it survived it.
            "overturned": sum(1 for g in gaps
                              if g.get("verdict") in ("dropped", "minority")),
            "fixed": sum(1 for g in gaps if g.get("fixed")),
            "elapsed_min": (round((ended - started).total_seconds() / 60)
                            if started and ended else None),
            "meta_tests": [meta.get("start"), meta.get("end")],
            "rule_changes": len(data.get("rule_changes") or []),
        })
    return rows


def _spoken(gap: dict) -> list[str]:
    return [str(v).strip().lower()
            for v in (gap.get("votes") or {}).values() if str(v).strip()]


def _count(values) -> dict[str, int]:
    out: dict[str, int] = {}
    for value in values:
        key = str(value or "unsaid")
        out[key] = out.get(key, 0) + 1
    return out


def condition(rows: list[dict]) -> str | None:
    """The one sentence the series is able to say about the triad.

    Only when there are enough finished passes to say it, and only when every
    one of the newest QUIET_PASSES removed nothing. Anything less is an
    impression, and this file exists to stop the pass forming one about itself.
    """
    finished = [r for r in rows if r["finished"] and r["claimed"]]
    if len(finished) < QUIET_PASSES:
        return None
    recent = finished[-QUIET_PASSES:]
    if any(r["overturned"] for r in recent):
        return None
    return (f"the triage triad has removed no claim in the last "
            f"{QUIET_PASSES} passes ({', '.join(r['run'] or '?' for r in recent)}) "
            f"-- a candidate for rule 1c, which is where dropping it belongs")


def render(rows: list[dict]) -> str:
    if not rows:
        return "no deep pass has committed a notebook yet"
    head = (f"{'pass':22} {'claimed':>7} {'real':>5} {'over':>5} {'fixed':>5} "
            f"{'unan':>5} {'min':>5} {'rules':>5}")
    lines = [head, "-" * len(head)]
    for row in rows:
        lines.append(
            f"{str(row['run'] or '?'):22} {row['claimed']:>7} {row['real']:>5} "
            f"{row['overturned']:>5} {row['fixed']:>5} "
            f"{str(row['unanimous']) + '/' + str(row['voted']):>5} "
            f"{str(row['elapsed_min'] or '?'):>5} {row['rule_changes']:>5}")
    lines.append("")
    lines.append("over  = claims the three readers rejected; the triad's whole output")
    lines.append("unan  = gaps where all three agreed / gaps that got three votes")
    lines.append("min   = minutes from the pass's first note to its last")
    verdict = condition(rows)
    lines.append("")
    lines.append(verdict if verdict else
                 "the triad is still removing claims, so it is still paying for itself")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true",
                        help="the rows, for the console")
    args = parser.parse_args(argv)

    rows = passes()
    if args.json:
        print(json.dumps({"passes": rows, "condition": condition(rows)},
                         indent=2, ensure_ascii=False))
    else:
        print(render(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

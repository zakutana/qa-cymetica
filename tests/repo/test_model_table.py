"""The model table and the parts that carry their own model say the same thing.

CLAUDE.md's table (*What a task needs*) says what each class of work runs on.
Skills and agents carry a model and an effort of their own in frontmatter, so
there are two copies of one fact, and this repository already knows what that
costs: on 2026-09-20 the laboratory's loop made 533 model calls, all on Opus,
while its skill's frontmatter said `model: sonnet` (`test_loop_cost.py`), and
`render._help_models` was written as a parser because a second retyped copy of
the table had already disagreed with the first.

The default is Sonnet. Opus is the exception that has to be visible, so the
test holds two directions:

  * a row that names a part agrees with that part's frontmatter -- the model
    family, and an effort inside the row's range;
  * a part whose frontmatter says anything but Sonnet (Opus, Fable) is named in
    some row. A part on Sonnet needs no row: it is the default, and asking for
    one would make this the registry `CLAUDE.md` says the repository is not.

Both directions are proved on invented tables as well as the real one: a guard
that only ever reads the file it agrees with has not shown it can disagree.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent

EFFORTS = ["low", "medium", "high", "xhigh", "max"]
FAMILIES = ("sonnet", "opus", "fable", "haiku")
DEFAULT_MODELS = {"sonnet", "haiku", "inherit"}
LEVELS = r"(low|medium|high|xhigh|max)"
RANGE = re.compile(rf"^{LEVELS}(?:\s*[–-]\s*{LEVELS})?\b")


def _render():
    spec = importlib.util.spec_from_file_location(
        "render_model_table", REPO / "scripts" / "render.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _field(front: str, key: str) -> str | None:
    found = re.search(rf"^{key}:\s*(\S+)", front, re.M)
    return found.group(1).lower() if found else None


def parts() -> dict[str, dict]:
    """name -> the model and effort a skill or an agent carries, if any."""
    out: dict[str, dict] = {}
    paths = [*(REPO / ".claude" / "skills").glob("*/SKILL.md"),
             *(REPO / ".claude" / "agents").glob("*.md")]
    for path in sorted(paths):
        name = path.parent.name if path.name == "SKILL.md" else path.stem
        head = re.match(r"---\r?\n(.*?)\r?\n---", path.read_text(encoding="utf-8"), re.S)
        front = head.group(1) if head else ""
        out[name] = {"model": _field(front, "model"), "effort": _field(front, "effort")}
    return out


def _family(model: str) -> str:
    return next((f for f in FAMILIES if f in model), model)


def named_by(rows: list[dict], known: dict[str, dict]) -> dict[str, list[dict]]:
    """Which rows name which part. A name is a whole word: `laborator` is the
    skill, `laboratory` and `laborator-plan.md` are not."""
    hits: dict[str, list[dict]] = {}
    for name in known:
        word = re.compile(rf"(?<![\w-]){re.escape(name)}(?![\w-])")
        hits[name] = [row for row in rows if word.search(row["task"])]
    return hits


def disagreements(rows: list[dict], known: dict[str, dict]) -> list[str]:
    problems: list[str] = []
    hits = named_by(rows, known)
    for name, part in known.items():
        model, effort = part["model"], part["effort"]
        for row in hits[name]:
            if model and _family(model) not in row["model"].lower():
                problems.append(
                    f"{name}: frontmatter says model {model}, the row says {row['model']!r}")
            span = RANGE.match(row["effort"].lower())
            if effort and not span:
                problems.append(
                    f"{name}: its row {row['task'][:40]!r} does not start with an effort level")
            elif effort and effort not in EFFORTS:
                problems.append(f"{name}: frontmatter effort {effort!r} is not a level")
            elif effort:
                low, high = span.group(1), span.group(2) or span.group(1)
                if not EFFORTS.index(low) <= EFFORTS.index(effort) <= EFFORTS.index(high):
                    problems.append(
                        f"{name}: frontmatter says effort {effort}, the row says {low}–{high}")
        if model and model not in DEFAULT_MODELS and not hits[name]:
            problems.append(
                f"{name}: carries model {model} and no row of the table names it -- "
                f"Opus is the exception, so it has to be visible")
    return problems


def _row(task: str, model: str, effort: str) -> dict:
    return {"task": task, "model": model, "effort": effort}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_model_table_and_the_parts_that_carry_a_model_agree():
    rows = _render()._help_models()
    known = parts()

    # The glob and the parser both read something, or the comparison below
    # agrees with itself about nothing.
    assert {"qa-sweep", "laborator", "deep-pass", "check-auditor"} <= set(known), known
    hits = named_by(rows, known)
    for name in ("qa-sweep", "laborator", "deep-pass"):
        assert hits[name], f"no row of CLAUDE.md's table names {name}"

    problems = disagreements(rows, known)
    assert not problems, "CLAUDE.md's table and the frontmatter disagree:\n" + "\n".join(problems)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_row_that_says_something_else_than_its_frontmatter_is_caught():
    known = {"qa-sweep": {"model": "sonnet", "effort": "high"}}

    agrees = [_row("sweep (qa-sweep)", "Sonnet 5.5", "high — why")]
    assert disagreements(agrees, known) == []

    wrong_model = [_row("sweep (qa-sweep)", "Opus 5.5", "high — why")]
    assert any("model" in p for p in disagreements(wrong_model, known))

    wrong_effort = [_row("sweep (qa-sweep)", "Sonnet 5.5", "low — why")]
    assert any("effort" in p for p in disagreements(wrong_effort, known))

    # A range is a range: high–xhigh takes both ends and nothing outside.
    span = [_row("sweep (qa-sweep)", "Sonnet 5.5", "medium–high — why")]
    assert disagreements(span, known) == []
    over = [_row("sweep (qa-sweep)", "Sonnet 5.5", "low–medium — why")]
    assert disagreements(over, known), "high is outside low–medium"

    # A row that names a part but starts its effort with a word is not a range.
    vague = [_row("sweep (qa-sweep)", "Sonnet 5.5", "as needed")]
    assert any("effort level" in p for p in disagreements(vague, known))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_opus_part_that_no_row_names_is_caught_and_a_sonnet_one_is_not():
    rows = [_row("channel status (/channels)", "Sonnet 5.5", "low — why")]

    quiet = {"channels": {"model": "sonnet", "effort": "low"},
             "lab-tick": {"model": "sonnet", "effort": "high"}}
    assert disagreements(rows, quiet) == [], "Sonnet is the default and needs no row"

    loud = {**quiet, "big-review": {"model": "opus", "effort": "high"}}
    problems = disagreements(rows, loud)
    assert len(problems) == 1 and "big-review" in problems[0], problems

    # Naming it is what clears it -- and then the row has to agree.
    named = [*rows, _row("the big review (big-review)", "Opus 5.5", "high — why")]
    assert disagreements(named, loud) == []

    # A part is a whole word: `laborator` is not `laboratory`, nor `laborator-plan`.
    lab = {"laborator": {"model": "opus", "effort": "high"}}
    rows = [_row("a session in the laboratory", "Sonnet 5.5", "high"),
            _row("a plan like docs/laborator-plan.md", "Opus 5.5", "max")]
    assert disagreements(rows, lab), "neither row names the skill"

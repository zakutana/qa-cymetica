"""A memory nothing reads is a memory nobody wrote.

The directory sat write-only for four days: `MEMORY.md` is auto-loaded so
every session knew the memories existed, and nothing anywhere told a session
to open one, so none did. The operator found it by asking whether they load
themselves.

What makes them readable is one field. Each memory says which kinds of work it
applies to, `scripts/memories.py --for <class>` prints those bodies, and the
sweep and the deep pass run it as their first step. This holds the field to
the directory: every memory classified and indexed, every index line pointing
at a file that exists.

In tests/repo, not tests/meta: an unclassified memory is worth a red line at
the end of a session, and is not a reason to abort one mid-flight.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from qa.marks import Inconclusive, SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


def _module():
    spec = importlib.util.spec_from_file_location(
        "memories_under_test", REPO / "scripts" / "memories.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_memory_is_classified_and_indexed():
    """Over the real directory, which is the only one that matters."""
    mod = _module()
    memories = mod.load()
    if not memories:
        raise Inconclusive(
            f"no memory directory at {mod.memory_dir()}; this machine is not "
            f"the one the memories live on")

    found = mod.problems(memories, mod.index_names())
    assert not found, (
        "the memory directory has drifted from what any session can read:\n  "
        + "\n  ".join(found)
    )


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_class_prints_only_its_own(tmp_path, monkeypatch):
    mod = _module()
    monkeypatch.setenv("QA_MEMORY_DIR", str(tmp_path))
    (tmp_path / "one.md").write_text(
        '---\nname: one\ndescription: "d"\napplies: sweep, fold\n---\n\n'
        "the body of one\n", encoding="utf-8")
    (tmp_path / "two.md").write_text(
        '---\nname: two\ndescription: "d"\napplies: console\n---\n\n'
        "the body of two\n", encoding="utf-8")
    (tmp_path / "MEMORY.md").write_text(
        "- [One](one.md) — a\n- [Two](two.md) — b\n", encoding="utf-8")

    assert not mod.problems(mod.load(), mod.index_names())

    import io
    import contextlib

    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        mod.main(["--for", "sweep"])
    printed = out.getvalue()
    assert "the body of one" in printed
    assert "the body of two" not in printed, \
        "a class printed a memory that does not apply to it"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_reader_accepts_every_shape_the_harness_actually_writes(tmp_path,
                                                                   monkeypatch):
    """We do not own this frontmatter. The memory harness rewrites it.

    Written on 2026-09-10, when two memories saved that evening declared
    `applies:` and `--check` reported them as `['- correspondence']`, which is
    not a class. The harness had normalised an inline list into a YAML block
    list -- its own choice, made after the file was written -- and this reader
    took the first indented line as the whole value.

    The failure is quiet in the direction that matters: a memory in the block
    form applies to nothing, so `--for <class>` never prints it, and the only
    signal is a `--check` nobody runs between sessions. A memory nothing reads
    is a memory that was not written, which is the defect the whole directory
    exists against.

    So the shapes are pinned as data. `read()` already documents that WHERE the
    field lands is the harness's decision and not ours; this says the same about
    HOW it is written.
    """
    mod = _module()
    monkeypatch.setenv("QA_MEMORY_DIR", str(tmp_path))

    shapes = {
        # What a session types.
        "inline": 'applies: "sweep, fold"',
        # What older files here carry.
        "bare": "applies: sweep, fold",
        # What the harness rewrote both of tonight's memories into.
        "block": "applies:\n    - sweep\n    - fold",
        # And the same, under metadata:, which is where it puts it.
        "nested": "metadata:\n  type: feedback\n  applies:\n    - sweep\n    - fold",
        # A one-item block list: the shape that reads as a valid class by
        # accident if only the leading dash is stripped.
        "single": "applies:\n    - sweep",
    }
    for stem, declared in shapes.items():
        (tmp_path / f"{stem}.md").write_text(
            f'---\nname: {stem}\ndescription: "d"\n{declared}\n---\n\n'
            f"body of {stem}\n", encoding="utf-8")
    (tmp_path / "MEMORY.md").write_text(
        "".join(f"- [{s}]({s}.md) — x\n" for s in shapes), encoding="utf-8")

    by_name = {m["path"].stem: m for m in mod.load()}
    for stem in shapes:
        expected = ["sweep"] if stem == "single" else ["sweep", "fold"]
        assert by_name[stem]["applies"] == expected, (
            f"{stem}: read {by_name[stem]['applies']!r}. A memory whose "
            f"classes cannot be read applies to nothing and is never printed"
        )

    assert not mod.problems(mod.load(), mod.index_names())

    import contextlib
    import io as _io

    out = _io.StringIO()
    with contextlib.redirect_stdout(out):
        mod.main(["--for", "fold"])
    printed = out.getvalue()
    for stem in ("inline", "bare", "block", "nested"):
        assert f"body of {stem}" in printed, f"{stem} never reached --for fold"
    assert "body of single" not in printed


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_memory_retired_on_purpose_is_not_a_memory_nobody_linked(tmp_path,
                                                                  monkeypatch):
    """The skill's own retirement procedure turned this file red.

    Deep pass, step 1b: retire a memory by "dropping the line from `MEMORY.md`
    and leaving the file" -- `rm` is not on the allowlist and an unattended pass
    may not ask. Doing exactly that made `problems()` say "not linked from
    MEMORY.md, so no session knows it exists", which is `tests/repo` red at step
    6, and step 9 reverts a night over a red it cannot resolve. Found on
    2026-09-10 by performing the procedure; three readers reproduced it the
    same way.

    Neither half was wrong. An unlinked file really is invisible, and a
    retirement really must not delete the record -- that directory is outside
    git, so `MEMORY.md` is the only history it has. What was missing was a way
    to say WHICH of the two happened.

    **The line stays in the list and says `RETIRED <date>: <reason>` itself.**
    Two POSITIONAL designs were tried first and an independent reader voted
    each one down before it landed, both for the same underlying reason: any
    "below this heading means retired" rule has to put the heading at the end
    of MEMORY.md, and the end of MEMORY.md is exactly where a new memory's line
    is appended.

      1. `## Retired` swallowed every appended line -- the next memory written
         would have been skipped by `--for` and reported clean.
      2. Requiring a date on the line fixed that until a memory's own one-line
         hook began with a date, which the real file already had.

    So position is not used at all. A session appending a line cannot
    accidentally write `RETIRED`, and where the line sits stops mattering.
    """
    import contextlib
    import io as _io

    mod = _module()
    monkeypatch.setenv("QA_MEMORY_DIR", str(tmp_path))
    for stem in ("live", "old"):
        (tmp_path / f"{stem}.md").write_text(
            f'---\nname: {stem}\ndescription: "d"\napplies: "sweep"\n---\n\n'
            f"body of {stem}\n", encoding="utf-8")

    # Forgotten: the file exists and nothing in MEMORY.md mentions it.
    (tmp_path / "MEMORY.md").write_text(
        "- [Live](live.md) — a\n", encoding="utf-8")
    found = mod.problems(mod.load(), mod.index_names())
    assert any("old" in p and "not linked" in p for p in found), (
        f"a memory nobody linked must still be caught: {found}")

    # Retired on purpose: the line STAYS in the list and says so itself.
    (tmp_path / "MEMORY.md").write_text(
        "- [Live](live.md) — a\n"
        "- [Old](old.md) — RETIRED 2026-09-10: superseded by CLAUDE.md's map.\n",
        encoding="utf-8")
    assert mod.problems(mod.load(), mod.index_names()) == [], \
        "a retirement performed as the skill prescribes must not be a problem"

    # And it stops being loaded, which is the point of retiring it.
    out = _io.StringIO()
    with contextlib.redirect_stdout(out):
        mod.main(["--for", "sweep"])
    printed = out.getvalue()
    assert "body of live" in printed
    assert "body of old" not in printed, \
        "a retired memory is still being read into sessions"

    # The two holes independent readers found in the two POSITIONAL designs
    # that came before this one, both reproduced here as data. A new memory's
    # line is appended to the END of MEMORY.md, so any design that says "below
    # this heading means retired" swallows the next memory written.
    #
    #   1. a `## Retired` heading at the end swallowed every appended line;
    #   2. requiring a date on the line fixed that until a memory's own hook
    #      happened to start with a date -- and the real MEMORY.md already had
    #      a line of that shape.
    #
    # Hence no position at all: a line is retired when the LINE says so, and a
    # session appending a new one cannot accidentally say it.
    (tmp_path / "fresh.md").write_text(
        '---\nname: fresh\ndescription: "d"\napplies: "sweep"\n---\n\n'
        "body of fresh\n", encoding="utf-8")
    (tmp_path / "dated.md").write_text(
        '---\nname: dated\ndescription: "d"\napplies: "sweep"\n---\n\n'
        "body of dated\n", encoding="utf-8")
    (tmp_path / "MEMORY.md").write_text(
        "- [Live](live.md) — a\n"
        "- [Old](old.md) — RETIRED 2026-09-10: superseded by CLAUDE.md's map.\n"
        "- [Fresh](fresh.md) — appended by a session that did not read this\n"
        "- [Dated](dated.md) — 2026-09-10, the day this one was learned\n",
        encoding="utf-8")
    assert mod.problems(mod.load(), mod.index_names()) == [], \
        "an appended line is a normal line, wherever it sits"
    assert mod.retired_names() == {"old"}, (
        f"only the line that says RETIRED is retired: {mod.retired_names()}")

    out = _io.StringIO()
    with contextlib.redirect_stdout(out):
        mod.main(["--for", "sweep"])
    printed = out.getvalue()
    for stem in ("live", "fresh", "dated"):
        assert f"body of {stem}" in printed, (
            f"{stem} was appended after the retired line and is no longer "
            f"read: this is the failure both earlier designs had")
    assert "body of old" not in printed

    # A retired line naming a file that is gone is still a problem: the record
    # is what retirement preserves, so losing it silently is the other failure.
    (tmp_path / "MEMORY.md").write_text(
        "- [Live](live.md) — a\n"
        "- [Old](old.md) — RETIRED 2026-09-10: superseded by CLAUDE.md's map.\n",
        encoding="utf-8")
    (tmp_path / "old.md").unlink()
    found = mod.problems(mod.load(), mod.index_names())
    assert any("old" in p for p in found), (
        f"MEMORY.md retires a file that no longer exists and nothing said so: "
        f"{found}")


def _memory(tmp_path, stem, applies, date, size=3000):
    body = f"{date}. body of {stem}. " + ("x" * size) + f" end of {stem}\n"
    (tmp_path / f"{stem}.md").write_text(
        f'---\nname: {stem}\ndescription: "d"\napplies: {applies}\n---\n\n'
        + body, encoding="utf-8")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_class_prints_whole_bodies_to_a_budget_most_specific_first(
        tmp_path, monkeypatch):
    """Plan v2, V7 (E2). `--for lab` was 28 KB and `--for deep-pass` up to
    69, above what one Bash result carries, and only 9 of 50 reads in the
    transcripts took a body whole. So a class prints WHOLE bodies up to
    BUDGET_BYTES, most specific first (a memory for this class alone before
    one for five), newest first among equals, and names the rest."""
    import contextlib
    import io

    mod = _module()
    monkeypatch.setenv("QA_MEMORY_DIR", str(tmp_path))
    _memory(tmp_path, "wide", "lab, sweep, fold", "2026-09-22")
    _memory(tmp_path, "narrow_old", "lab", "2026-09-10")
    _memory(tmp_path, "narrow_new", "lab", "2026-09-20")
    (tmp_path / "MEMORY.md").write_text(
        "- [W](wide.md) — a\n- [O](narrow_old.md) — b\n- [N](narrow_new.md) — c\n",
        encoding="utf-8")

    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        mod.main(["--for", "lab"])
    printed = out.getvalue()

    assert len(printed.encode("utf-8")) <= mod.BUDGET_BYTES, len(printed)
    assert printed.index("body of narrow_new") < printed.index("body of narrow_old")
    for stem in ("narrow_new", "narrow_old"):
        assert f"end of {stem}" in printed, f"{stem} was cut, not printed whole"
    assert "body of wide" not in printed and "wide" in printed, (
        "what did not fit is named, not dropped")
    assert "--all" in printed

    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        mod.main(["--for", "lab", "--all"])
    assert "end of wide" in out.getvalue()


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_retired_line_lives_in_its_own_file_and_still_counts(tmp_path,
                                                                monkeypatch):
    """Plan v2, V7 (E3). The harness loads the first 200 lines / 25 000
    characters of MEMORY.md; retired lines are history, not something a
    session needs every time. They move to MEMORY-retired.md, marker and
    all, which no new line is ever appended to -- so the positional failure
    the marker was chosen to avoid cannot come back."""
    mod = _module()
    monkeypatch.setenv("QA_MEMORY_DIR", str(tmp_path))
    for stem in ("live", "old"):
        (tmp_path / f"{stem}.md").write_text(
            f'---\nname: {stem}\ndescription: "d"\napplies: sweep\n---\n\n'
            f"body of {stem}\n", encoding="utf-8")
    (tmp_path / "MEMORY.md").write_text("- [Live](live.md) — a\n",
                                        encoding="utf-8")
    (tmp_path / "MEMORY-retired.md").write_text(
        "- [Old](old.md) — RETIRED 2026-09-10: merged into live.\n",
        encoding="utf-8")

    assert mod.problems(mod.load(), mod.index_names()) == []
    assert mod.retired_names() == {"old"}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_index_fits_what_the_harness_loads():
    """Over the real directory: under the harness's load limit, with room,
    and no retired line left in what every session loads."""
    mod = _module()
    path = mod.memory_dir() / "MEMORY.md"
    if not path.is_file():
        raise Inconclusive(f"no index at {path} on this machine")
    text = path.read_text(encoding="utf-8")
    assert len(text.splitlines()) <= mod.INDEX_MAX_LINES, len(text.splitlines())
    assert len(text) <= mod.INDEX_MAX_CHARS, len(text)
    assert not mod.RETIRED_LINE.search(text), (
        "a retired line is still in MEMORY.md; it belongs in MEMORY-retired.md")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_unclassified_or_unlinked_memory_is_a_problem(tmp_path, monkeypatch):
    """Both directions: a file nothing links, and a link with no file."""
    mod = _module()
    monkeypatch.setenv("QA_MEMORY_DIR", str(tmp_path))
    (tmp_path / "bare.md").write_text(
        '---\nname: bare\ndescription: "d"\n---\n\nbody\n', encoding="utf-8")
    (tmp_path / "MEMORY.md").write_text(
        "- [Gone](gone.md) — c\n", encoding="utf-8")

    found = " ".join(mod.problems(mod.load(), mod.index_names()))
    assert "no `applies:`" in found
    assert "not linked from MEMORY.md" in found
    assert "which is not a file" in found


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_hook_is_one_line_and_never_fails(tmp_path, monkeypatch):
    """A hook that can break a session start is worse than no hook."""
    import subprocess
    import sys

    hook = REPO / ".claude" / "hooks" / "start" / "memory_index.py"
    result = subprocess.run([sys.executable, str(hook)], cwd=REPO,
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=60)
    assert result.returncode == 0
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(lines) <= 1, f"the hook printed {len(lines)} lines into context"
    if lines:
        assert "scripts/memories.py --for" in lines[0]

    empty = subprocess.run([sys.executable, str(hook)], cwd=REPO,
                           capture_output=True, text=True,
                           env={**dict(__import__("os").environ),
                                "QA_MEMORY_DIR": str(tmp_path)}, timeout=60)
    assert empty.returncode == 0
    assert not empty.stdout.strip(), \
        "the hook spoke when there was nothing to say"

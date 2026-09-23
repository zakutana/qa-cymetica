"""The memories that apply to the work in front of you, printed.

`MEMORY.md` is auto-loaded into every session: 27 one-line hooks. The bodies
are not, and until 2026-09-10 nothing told a session to open one -- so the
directory was write-only by construction, which is the same defect as a
mechanism nobody runs. The operator found it by asking whether the memories
load themselves. They do not.

    python scripts/memories.py --for sweep
    python scripts/memories.py --list
    python scripts/memories.py --check

Each memory declares `applies:` in its frontmatter -- top level or under
`metadata:`, wherever the harness that rewrites these files decides to put it
-- as one or more of the classes below. A memory that applies to everything
applies to nothing in particular and would be read past, so `all` is
deliberately not a class.

The directory lives outside the repository, beside the session transcripts, so
this is the only thing that knows where it is.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qa.console import printable  # noqa: E402

CLASSES = ("sweep", "fold", "console", "correspondence", "deep-pass",
           "plan", "lab")

FRONT = re.compile(r"^---\n(.*?)\n---\n", re.S)


def memory_dir() -> Path:
    """Where they live: `QA_MEMORY_DIR`, else beside this project's transcripts."""
    import os

    override = os.environ.get("QA_MEMORY_DIR")
    if override:
        return Path(override)
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(REPO_ROOT))
    return Path.home() / ".claude" / "projects" / slug / "memory"


def read(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    front = FRONT.match(text)
    head = front.group(1) if front else ""
    body = text[front.end():] if front else text

    def field(name: str) -> str:
        # Indented, because the memory harness rewrites this frontmatter and
        # puts anything it does not recognise under `metadata:`. Where the
        # field lands is its decision, not ours; the reader accepts both.
        # `[ \t]*`, never `\s*`: in multiline mode `\s` matches the newline, so
        # `\s*(.+)$` on `applies:\n    - sweep` returns `- sweep` -- the first
        # item of a block list read as the entire value. That is how a memory
        # ended up applying to a class called `- correspondence`.
        found = re.search(rf"^[ \t]*{name}:[ \t]*(.+)$", head, re.M)
        return found.group(1).strip().strip('"') if found else ""

    def listing(name: str) -> list[str]:
        """`a, b`, `"a, b"`, or a YAML block list. All three are written here.

        We do not own this frontmatter. A session types the inline form and the
        harness may rewrite it as a block list afterwards -- it did exactly that
        to two memories on 2026-09-10, and this reader took the first indented
        line as the whole value, so both applied to a class named
        `- correspondence` and were never printed for anything.

        Quiet in the direction that matters: `--for <class>` simply skips them.
        Hence read here rather than trusted.
        """
        inline = field(name)
        if inline:
            return [a.strip() for a in inline.split(",") if a.strip()]
        block = re.search(rf"^([ \t]*){name}:[ \t]*$", head, re.M)
        if not block:
            return []
        out = []
        for line in head[block.end():].splitlines()[1:]:
            item = re.match(r"^[ \t]+-[ \t]+(\S.*?)[ \t]*$", line)
            if not item:
                break
            out.append(item.group(1).strip().strip('"').strip("'"))
        return out

    applies = listing("applies")
    return {"path": path, "name": field("name") or path.stem,
            "description": field("description"), "applies": applies,
            "body": body.strip()}


def load() -> list[dict]:
    directory = memory_dir()
    if not directory.is_dir():
        return []
    return [read(p) for p in sorted(directory.glob("*.md"))
            if p.name not in ("MEMORY.md", RETIRED_FILE)]


# What the harness loads of MEMORY.md: the first 200 lines / 25 000
# characters (plan v2, V7, E3). Held under it, not on it.
INDEX_MAX_LINES = 180
INDEX_MAX_CHARS = 22000
# Retired lines live here, marker and all. Nothing appends to this file, so
# the positional failure below cannot come back through it.
RETIRED_FILE = "MEMORY-retired.md"
# What one `--for` prints of whole bodies. `--for lab` was 28 KB and
# `--for deep-pass` up to 69, above what a Bash result carries, and only 9 of
# 50 reads in the transcripts took a body whole (E2).
BUDGET_BYTES = 8192
DATE = re.compile(r"\b(20\d\d-\d\d-\d\d)\b")


def _index_text() -> str:
    """MEMORY.md and the retired lines beside it, as one text."""
    out = []
    for name in ("MEMORY.md", RETIRED_FILE):
        path = memory_dir() / name
        if path.is_file():
            out.append(path.read_text(encoding="utf-8"))
    return "\n".join(out)


def ranked(memories: list[dict], klass: str) -> list[dict]:
    """The memories for one class, most relevant first: the fewer classes a
    memory applies to, the more it is about this one; among equals the one
    whose newest date is latest, since a memory that happened again says so
    with a later date."""
    def newest(memory: dict) -> str:
        return max(DATE.findall(memory["body"]) or [""])
    matching = [m for m in memories if klass in m["applies"]]
    matching.sort(key=newest, reverse=True)
    return sorted(matching, key=lambda m: len(m["applies"]))


# A retirement is marked IN ITS OWN LINE, not by where the line sits.
#
# The deep pass retires a memory by taking it out of what sessions read and
# leaving the file -- `rm` is not on its allowlist and an unattended pass may
# not ask. Doing that by deleting the line made `problems()` report the file as
# one nobody linked, which is `tests/repo` red at step 6, and step 9 reverts a
# night over a red it cannot resolve. Found 2026-09-10 by performing the
# procedure.
#
# Two positional designs were tried and BOTH were voted down by an independent
# reader before they landed, for the same underlying reason: a `## Retired`
# heading has to go at the end of MEMORY.md, and the end of MEMORY.md is
# exactly where a new memory's line is appended. First attempt -- the heading
# swallowed anything below it, so the next memory written would be skipped by
# `--for` and reported clean. Second attempt -- requiring a date on the line
# fixed that until a memory's own one-line hook happened to start with a date,
# which the real file already does.
#
# So position is not used at all. A line is retired when it says so, and a line
# appended by a session that has not read this cannot accidentally say so.
RETIRED_LINE = re.compile(
    r"^-\s.*?\]\(([^)]+)\.md\)[^\n]*?\bRETIRED\s+(\d{4}-\d{2}-\d{2})\b", re.M)
ANY_LINE = re.compile(r"\]\(([^)]+)\.md\)")


def retired_names() -> set[str]:
    """Every memory whose index line carries `RETIRED <date>`."""
    return {m.group(1) for m in RETIRED_LINE.finditer(_index_text())}


def index_names() -> set[str]:
    """Every memory `MEMORY.md` links. Retired ones are linked but not read."""
    return set(ANY_LINE.findall(_index_text()))


def problems(memories: list[dict], indexed: set[str]) -> list[str]:
    """What is wrong with the directory, in the operator's terms.

    Pure, so the test can hand it a temp directory and get the same answers.
    """
    out = []
    retired = retired_names()
    for memory in memories:
        stem = memory["path"].stem
        if stem in retired:
            # Retired on purpose: not loaded, not classified, not a problem.
            # The reason lives beside its line under `## Retired`, which is the
            # only history this directory has.
            continue
        if not memory["applies"]:
            out.append(f"{stem}: no `applies:` -- nothing will ever read it")
        unknown = sorted(set(memory["applies"]) - set(CLASSES))
        if unknown:
            out.append(f"{stem}: applies to {unknown}, which is not a class")
        if stem not in indexed:
            out.append(f"{stem}: not linked from MEMORY.md, so no session "
                       f"knows it exists. If it was retired deliberately, keep "
                       f"its line and mark it `RETIRED YYYY-MM-DD: <reason>`")
    on_disk = {m["path"].stem for m in memories}
    for name in sorted(indexed - on_disk):
        out.append(f"MEMORY.md links {name}, which is not a file")
    for name in sorted(retired - on_disk):
        # Retiring preserves the record. A retired line whose file is gone has
        # lost the thing the procedure exists to keep.
        out.append(f"MEMORY.md retires {name}, whose file is gone -- a "
                   f"retirement keeps the record, it does not remove it")
    return out


def main(argv: list[str] | None = None) -> int:
    # A memory body is prose, and prose here carries arrows and dashes. This
    # crashed at step 0 of the deep pass on 2026-09-10, printing the very
    # memories the pass is told to read before it starts.
    printable()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--for", dest="klass", choices=CLASSES,
                       help="print the bodies that apply to this kind of work")
    group.add_argument("--list", action="store_true",
                       help="one line each, with what it applies to")
    group.add_argument("--check", action="store_true",
                       help="exit 1 if any memory is unclassified or unindexed")
    parser.add_argument("--all", action="store_true",
                        help="with --for: every body, past the budget")
    args = parser.parse_args(argv)

    memories = load()
    if not memories:
        print(f"no memories at {memory_dir()}", file=sys.stderr)
        return 0

    if args.check:
        found = problems(memories, index_names())
        for line in found:
            print(line)
        print(f"{len(memories)} memories, {len(found)} problem(s)")
        return 1 if found else 0

    if args.list:
        for memory in memories:
            print(f"{memory['path'].stem:56} {','.join(memory['applies'])}")
        return 0

    retired = retired_names()
    matching = ranked([m for m in memories if m["path"].stem not in retired],
                      args.klass)
    if not matching:
        print(f"nothing recorded about {args.klass} yet")
        return 0
    head = f"# {len(matching)} memories that apply to {args.klass}, most specific first\n"
    blocks, used, rest = [], len(head.encode("utf-8")) + 1, []
    # Room for the closing list of what did not fit, so the whole stays
    # under the budget.
    tail_room = 120 + sum(len(m["name"]) + 8 for m in matching)
    for memory in matching:
        block = f"## {memory['name']}\n\n{memory['body']}\n"
        size = len(block.encode("utf-8")) + 1
        # Always one whole body, even a long one; never a body cut short.
        if args.all or not blocks or used + size + tail_room <= BUDGET_BYTES:
            blocks.append(block)
            used += size
        else:
            rest.append(memory["name"])
    print(head)
    for block in blocks:
        print(block)
    if rest:
        print(f"# +{len(rest)} more, not printed: {', '.join(rest)}\n"
              f"# every body: python scripts/memories.py --for {args.klass} --all")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

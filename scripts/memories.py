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

CLASSES = ("sweep", "fold", "console", "correspondence", "deep-pass", "plan")

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
        found = re.search(rf"^\s*{name}:\s*(.+)$", head, re.M)
        return found.group(1).strip().strip('"') if found else ""

    applies = [a.strip() for a in field("applies").split(",") if a.strip()]
    return {"path": path, "name": field("name") or path.stem,
            "description": field("description"), "applies": applies,
            "body": body.strip()}


def load() -> list[dict]:
    directory = memory_dir()
    if not directory.is_dir():
        return []
    return [read(p) for p in sorted(directory.glob("*.md"))
            if p.name != "MEMORY.md"]


def index_names() -> set[str]:
    """Every memory `MEMORY.md` links to."""
    path = memory_dir() / "MEMORY.md"
    if not path.is_file():
        return set()
    return set(re.findall(r"\]\(([^)]+)\.md\)",
                          path.read_text(encoding="utf-8")))


def problems(memories: list[dict], indexed: set[str]) -> list[str]:
    """What is wrong with the directory, in the operator's terms.

    Pure, so the test can hand it a temp directory and get the same answers.
    """
    out = []
    for memory in memories:
        stem = memory["path"].stem
        if not memory["applies"]:
            out.append(f"{stem}: no `applies:` -- nothing will ever read it")
        unknown = sorted(set(memory["applies"]) - set(CLASSES))
        if unknown:
            out.append(f"{stem}: applies to {unknown}, which is not a class")
        if stem not in indexed:
            out.append(f"{stem}: not linked from MEMORY.md, so no session "
                       f"knows it exists")
    for name in sorted(indexed - {m["path"].stem for m in memories}):
        out.append(f"MEMORY.md links {name}, which is not a file")
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

    matching = [m for m in memories if args.klass in m["applies"]]
    if not matching:
        print(f"nothing recorded about {args.klass} yet")
        return 0
    print(f"# {len(matching)} memories that apply to {args.klass}\n")
    for memory in matching:
        print(f"## {memory['name']}\n")
        print(memory["body"])
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Split an outbox message into Telegram-sized pastes.

Telegram caps a message at 4096 characters. A report that exceeds it either
gets truncated silently or has to be broken up by hand mid-sentence, and a
finding split across a line break is a finding that gets misread.

So we split on section boundaries only, never inside one, and label each part
so the recipient can see none is missing.

    python scripts/telegram.py outbox/2026-09-04-MSG-0001.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LIMIT = 4096
HEADROOM = 120  # room for the "part n/N" label


def strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[2].lstrip("\n")
    return text


def sections(body: str) -> list[str]:
    """Split on the heavy rules, keeping each rule with the heading it opens."""
    raw = re.split(r"\n(?=═{10,})", body)
    out: list[str] = []
    for chunk in raw:
        chunk = chunk.rstrip()
        if not chunk:
            continue
        # A bare rule + heading + rule belongs with the block that follows it.
        if out and len(chunk) < 200 and chunk.count("═") >= 2:
            out[-1] = out[-1] + "\n" + chunk
        else:
            out.append(chunk)
    return out


def pack(chunks: list[str], limit: int) -> list[str]:
    parts: list[str] = []
    current = ""
    for chunk in chunks:
        candidate = (current + "\n\n" + chunk).strip() if current else chunk
        if len(candidate) <= limit:
            current = candidate
            continue
        if current:
            parts.append(current)
        if len(chunk) <= limit:
            current = chunk
            continue
        # A single section larger than the limit: split on blank lines.
        current = ""
        buf = ""
        for para in chunk.split("\n\n"):
            cand = (buf + "\n\n" + para).strip() if buf else para
            if len(cand) <= limit:
                buf = cand
            else:
                if buf:
                    parts.append(buf)
                buf = para
        current = buf
    if current:
        parts.append(current)
    return parts


def split_file(path: Path) -> list[Path]:
    body = strip_frontmatter(path.read_text(encoding="utf-8")).strip()
    parts = pack(sections(body), LIMIT - HEADROOM)
    total = len(parts)
    written: list[Path] = []

    for i, part in enumerate(parts, 1):
        label = f"[QA report {path.stem.split('-MSG-')[-1]} — part {i}/{total}]\n\n" if total > 1 else ""
        text = label + part
        out = path.with_name(f"{path.stem}.part{i}.txt")
        out.write_text(text, encoding="utf-8", newline="\n")
        written.append(out)
        flag = "" if len(text) <= LIMIT else "  <-- OVER LIMIT"
        print(f"  part {i}/{total}  {len(text):>5} chars -> {out.name}{flag}")
    return written


def combine(paths: list[Path], out: Path) -> Path:
    """One clean document to attach: frontmatter stripped, order preserved.

    Attaching a file sidesteps the 4096 limit entirely, so this is the preferred
    route for anything longer than a couple of sections. The YAML frontmatter is
    our own bookkeeping and never goes to the counterparty.
    """
    blocks = [strip_frontmatter(p.read_text(encoding="utf-8")).strip() for p in paths]
    joined = ("\n\n\n" + "─" * 56 + "\n\n\n").join(blocks)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(joined + "\n", encoding="utf-8", newline="\n")
    print(f"  {out.relative_to(REPO_ROOT)}  ({len(joined):,} chars, "
          f"{len(joined.splitlines())} lines)")
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        raise SystemExit(1)

    def resolve(a: str) -> Path:
        p = Path(a)
        return p if p.is_absolute() else REPO_ROOT / a

    if args[0] == "--combine":
        sources = [resolve(a) for a in args[1:-1]]
        combine(sources, resolve(args[-1]))
    else:
        for arg in args:
            target = resolve(arg)
            print(f"{target.name}:")
            split_file(target)

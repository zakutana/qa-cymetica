"""The operator's decisions are marked, and nothing in here may edit one.

Since 2026-09-09 the night pass may change the rules themselves, under three
conditions at once. That is a large permission, and it is bounded by one
exception the operator stated when they gave it: a sentence that records what
THEY decided is not a rule the loop may improve. It is theirs.

A loop cannot honour a boundary it cannot see, so the boundary is written down.
A paragraph beginning `[operator YYYY-MM-DD]` is a decision. This file pins
each one by hash and fails in all three directions:

  * a pinned decision that is no longer in the file  -- somebody deleted it
  * a tagged decision that is not pinned here        -- somebody added or
                                                        reworded one
  * a hash that does not match                       -- somebody edited one

The first is the one a test usually gets wrong. Walking the tags found in the
file and checking them against a list passes when a tag is deleted, because
there is then nothing to check. So the walk starts from the pinned list.

The hash is over whitespace-normalised text, so re-wrapping a paragraph is
free and changing a word is not. That is the line worth drawing: the operator
did not decide how the file wraps.

**Why this lives in tests/meta**, where a failure aborts the whole session: a
session that has touched a decision should not go on to issue live requests or
run an unattended pass. The deep pass's step 0 stops on red meta, which is
exactly the stop wanted here.

**What this cannot do**, said rather than discovered: it cannot stop a session
that deletes both the paragraph and its pin in one commit. Nothing in a
repository can, and pinning this file's own hash somewhere else only moves the
problem one file along -- with seven decisions in five days the operator would
be re-pinning daily, which is the badge-nobody-can-clear failure again. The
real detector is the three triage agents reading the diff (deep-pass, step 1c),
and this test's job is to make the deletion something they cannot miss.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
SOURCES = ["CLAUDE.md"] + sorted(
    str(p.relative_to(REPO)).replace("\\", "/")
    for p in (REPO / ".claude" / "skills").glob("*/SKILL.md"))

TAG = re.compile(r"\[operator (\d{4}-\d{2}-\d{2})\]")
ITEM = re.compile(r"^\s*(\*|-|\d+\.)\s")

# The repository's one form for quoting them, and the one form for citing them
# without a quote. Either outside a tagged block is an unmarked decision.
QUOTED = re.compile(r'\*"[^"]{8,}"\*', re.S)
ATTRIBUTED = re.compile(
    r"(the operator(?:'s)?|their|they)[^.\n]{0,80}20\d\d-\d\d-\d\d"
    r"|20\d\d-\d\d-\d\d[^.\n]{0,40}(the operator(?:'s)?|their)", re.I)


def decisions(text: str) -> list[dict]:
    """Every tagged decision in one file, with the hash of its words.

    A decision runs from its tag to the end of its paragraph -- the next blank
    line, the next list item, or the next tag, whichever comes first. List
    items matter: several of these sit inside one, and taking "to the next
    blank line" would swallow the neighbouring rules and hash them too.
    """
    lines = text.replace("\r\n", "\n").split("\n")
    found = []
    for i, line in enumerate(lines):
        tag = TAG.search(line)
        if not tag:
            continue
        j = i
        while (j + 1 < len(lines) and lines[j + 1].strip()
               and not ITEM.match(lines[j + 1]) and not TAG.search(lines[j + 1])):
            j += 1
        body = " ".join(" ".join(lines[i:j + 1]).split())
        found.append({"date": tag.group(1), "line": i + 1, "body": body,
                      "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest()})
    return found


def _text(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


# Every decision the operator has made, by file, date and the hash of its
# words. Added to only when they make one; never edited to make a test pass.
PINNED = {
    "CLAUDE.md": [
        ("2026-09-07", "both halves of this are their instruction"),
        ("2026-09-08", "pushovat se bude jen v deep pasu"),
        ("2026-09-08", "jestli neco v dokumentaci neni"),
        ("2026-09-06", "nechapu proc tvorit ty artifacty"),
        ("2026-09-05", "the wallet stays unverified"),
    ],
    ".claude/skills/qa-sweep/SKILL.md": [
        ("2026-09-06", "kdyz napisu sweep"),
        ("2026-09-06", "file without asking"),
        ("2026-09-07", "libi se mi ze po sweepu"),
    ],
    ".claude/skills/channels/SKILL.md": [
        ("2026-09-08", "kdyz je server vypnuty"),
        ("2026-09-08", "the bell is bug-tracker only"),
    ],
    ".claude/skills/deep-pass/SKILL.md": [
        ("2026-09-07", "nechci behem dne ztracet cas"),
        ("2026-09-08", "the night loop may change the rules"),
        ("2026-09-08", "tos celou dobu cekal na me jedno slovo"),
    ],
}

# Places that look like an attribution and are not a decision. Each needs a
# reason, so the list cannot become somewhere to put inconvenient lines.
EXCEPTIONS = {
    # Hands a judgement to the operator rather than recording one they made.
    ("CLAUDE.md", "and that one is the operator's"),
    # Describes a flag's behaviour; the decision itself is tagged in the skill.
    ("CLAUDE.md", "the operator's condition, and"),
}


def _pinned_pairs() -> list[tuple[str, str, str]]:
    return [(rel, date, hint) for rel, rows in PINNED.items() for date, hint in rows]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize("rel,date,hint", _pinned_pairs())
def test_every_decision_the_operator_made_is_still_there(rel, date, hint):
    """Starts from the pinned list, so a DELETED decision fails.

    The obvious shape -- walk the tags in the file, check each against a list
    -- is green on a deletion, because a tag that is gone is a tag not walked.
    """
    here = [d for d in decisions(_text(rel)) if d["date"] == date
            and hint.lower() in d["body"].lower()]
    assert here, (
        f"{rel}: the decision of {date} ({hint!r}) is gone. It is the "
        f"operator's, not a rule -- restore it, or take it to them"
    )
    assert len(here) == 1, f"{rel}: {date} {hint!r} appears {len(here)} times"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize("rel", SOURCES)
def test_no_decision_was_added_or_reworded_without_the_operator(rel):
    """The other direction. A tag nobody pinned is a sentence put in their
    mouth, and a reworded one is the same thing with a paper trail."""
    pinned = PINNED.get(rel, [])
    for found in decisions(_text(rel)):
        match = [(d, h) for d, h in pinned
                 if d == found["date"] and h.lower() in found["body"].lower()]
        assert match, (
            f"{rel}:{found['line']}: a decision tagged {found['date']} that "
            f"nothing pins: {found['body'][:90]!r}. If they said it, pin it "
            f"here; if they did not, it is a rule and must not wear the tag"
        )


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize("rel", SOURCES)
def test_nothing_quotes_the_operator_outside_a_tagged_decision(rel):
    """The tripwire: a decision written down without the mark is invisible to
    the loop, and the loop is now allowed to edit anything it does not see.

    Deliberately narrow. It fires on the two forms this repository actually
    uses -- an italic Czech quote, and an attribution carrying a date -- not on
    every sentence with the word operator in it.
    """
    text = _text(rel).replace("\r\n", "\n")
    lines = text.split("\n")
    covered = set()
    for found in decisions(text):
        start = found["line"] - 1
        end = start + found["body"].count("\n")
        j = start
        while (j + 1 < len(lines) and lines[j + 1].strip()
               and not ITEM.match(lines[j + 1]) and not TAG.search(lines[j + 1])):
            j += 1
        covered.update(range(start, j + 1))
        del end

    loose = []
    for pattern in (QUOTED, ATTRIBUTED):
        for m in pattern.finditer(text):
            line_no = text[:m.start()].count("\n")
            if line_no in covered:
                continue
            context = " ".join(lines[line_no].split())
            if any(rel == f and phrase in context for f, phrase in EXCEPTIONS):
                continue
            loose.append(f"{rel}:{line_no + 1}: {context[:88]}")

    assert not loose, (
        "the operator is quoted or cited outside a tagged decision:\n  "
        + "\n  ".join(sorted(set(loose)))
        + "\nTag it [operator YYYY-MM-DD] and pin it, or add it to EXCEPTIONS "
          "with the reason it is not a decision"
    )


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_parser_notices_a_decision_that_was_removed():
    """The negative control, and the reason it is here: this file's whole
    value is failing on a deletion, and the check for that cannot itself be
    checked by the repository being intact."""
    text = _text("CLAUDE.md")
    before = decisions(text)
    assert before, "CLAUDE.md carries no tagged decision at all"

    victim = before[0]
    lines = text.replace("\r\n", "\n").split("\n")
    without = "\n".join(lines[:victim["line"] - 1] + lines[victim["line"]:])

    after = decisions(without)
    assert len(after) < len(before), "removing a tag did not remove a decision"
    assert not [d for d in after if d["sha256"] == victim["sha256"]]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_rewrapping_is_free_and_rewording_is_not():
    """What the hash is over. The operator decided the words, not the column
    the file wraps at, and a pin that fires on a re-wrap would be re-pinned
    until somebody stopped reading it."""
    same = decisions("[operator 2026-09-01] a\n  decision in\n  three lines\n")
    one = decisions("[operator 2026-09-01] a decision in three lines\n")
    assert same[0]["sha256"] == one[0]["sha256"]

    other = decisions("[operator 2026-09-01] a decision in four lines\n")
    assert other[0]["sha256"] != one[0]["sha256"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_decision_does_not_swallow_the_rule_beside_it():
    """Several of these sit inside a numbered list. A paragraph that ran to
    the next blank line would hash the neighbouring rules too, so editing an
    ordinary rule would fail as if it were a decision -- and the loop, told it
    may not touch decisions, would stop touching rules."""
    text = ("1. **A rule.** Something the loop may change.\n"
            "2. [operator 2026-09-01] Something it may not.\n"
            "3. **Another rule.** Also changeable.\n")
    found = decisions(text)
    assert len(found) == 1
    assert "Something it may not" in found[0]["body"]
    assert "Another rule" not in found[0]["body"]
    assert "A rule" not in found[0]["body"]

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
        # `span` is the 0-based half-open line range, returned rather than
        # recomputed by callers: the tripwire below needs to know which lines a
        # decision covers, and a second copy of this loop would be free to
        # disagree with this one the moment either changed.
        found.append({"date": tag.group(1), "line": i + 1, "body": body,
                      "span": range(i, j + 1),
                      "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest()})
    return found


def _text(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


# Every decision the operator has made, by file, date and the hash of its
# words. Added to only when they make one; never edited to make a test pass.
PINNED = {
    "CLAUDE.md": [
        ("2026-09-09", "ano 5. levny protoze jen cte",
         "bf3b0779a1ff08ab06e6619df7be54265601746348e15345fc35db7fbdb8b9ea"),
        ("2026-09-09", "nechtel po me zadna takova rozhnodnuti",
         "c96da38a0cbea54eaae8ddc2c7eefce96f57a580915164d23f9c876edde987dc"),
        ("2026-09-07", "both halves of this are their instruction",
         "73951f58e15c2865c681eaa9b432c84453ac399c1d7c6e01056a1779c7df6b2f"),
        ("2026-09-08", "pushovat se bude jen v deep pasu",
         "24dc71665c3dc1604518393e8a065f31768bc30cfcf6090787e1c827679f6db4"),
        ("2026-09-08", "jestli neco v dokumentaci neni",
         "b9f592459c8890095492cd4bfbc54ad8315ba61f5c2b1561f01ace427c29eb3b"),
        ("2026-09-06", "nechapu proc tvorit ty artifacty",
         "e9e06543700e4ef3df1adcbff995ba1db022ea8d6181e6d8f3e1715f38d44825"),
        ("2026-09-05", "the wallet stays unverified",
         "d9ce618c9d1f48611e45423d9d07ba2f8ec951eb686c2f9c7d46c3c4ace7aa5a"),
    ],
    ".claude/skills/qa-sweep/SKILL.md": [
        ("2026-09-06", "kdyz napisu sweep",
         "610e9b087433a203e8e38e73dcbe1c6f85f4ef3552dbf59ff499e704efc79d49"),
        ("2026-09-06", "file without asking",
         "06d4c8a79677483d48c429b42d7fd00bba92f7d808e098992f599a141dd0b28c"),
        ("2026-09-07", "libi se mi ze po sweepu",
         "f4798675029b70b2926b9019189a8ddff76b9cb24e4aad1ed409b78ee6fe0c9d"),
    ],
    ".claude/skills/channels/SKILL.md": [
        ("2026-09-08", "kdyz je server vypnuty",
         "45c092f91272b69262a18cb5e05e107ef404910f4c7d45892d72a73a27c46d91"),
        ("2026-09-08", "the bell is bug-tracker only",
         "d19c226ec84ee951da90b3d36b279ade48560674dfd6cdb3786698a8229a5311"),
        ("2026-09-10", "Ano, jen čísla",
         "4d18272203a67eaede4d3380b022a4c03367dd846a2381893b1e44930c3b2117"),
    ],
    ".claude/skills/deep-pass/SKILL.md": [
        ("2026-09-07", "nechci behem dne ztracet cas",
         "99c552e7f54ed42777ce76d246f0d2038f0c49be80d8c10eaded976b5b2ae855"),
        ("2026-09-08", "the night loop may change the rules",
         "e280ab0ad68dc07d06651ec89c6eaafef7a5488130a1e337a6f6f769d834c4b1"),
        ("2026-09-08", "tos celou dobu cekal na me jedno slovo",
         "c0da8c03a527261e41cfa17265f32caabba02db77c0d094815a4c3221098b5b5"),
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


def _pinned_rows() -> list[tuple[str, str, str, str]]:
    return [(rel, date, hint, digest)
            for rel, rows in PINNED.items() for date, hint, digest in rows]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize("rel,date,hint,digest", _pinned_rows())
def test_every_decision_the_operator_made_is_still_there(rel, date, hint, digest):
    """Starts from the pinned list, so a DELETED decision fails -- and holds
    the HASH, so a reworded one fails too.

    Two mistakes, both made here first. The obvious shape -- walk the tags in
    the file, check each against a list -- is green on a deletion, because a
    tag that is gone is a tag not walked. And the first version of this file
    pinned only (date, hint): the hint is a substring, so rewriting
    *"Pushovat se bude jen v deep pasu nebo kdyz vylozene reknu."* into
    *"Pushovat se bude jen v deep pasu, nebo kdykoliv se mi zachce."* kept the
    substring, kept both tests green, and reversed the decision. The docstring
    claimed a hash the code never compared. Found by review, 2026-09-09.
    """
    here = [d for d in decisions(_text(rel)) if d["date"] == date
            and hint.lower() in d["body"].lower()]
    assert here, (
        f"{rel}: the decision of {date} ({hint!r}) is gone. It is the "
        f"operator's, not a rule -- restore it, or take it to them"
    )
    assert len(here) == 1, f"{rel}: {date} {hint!r} appears {len(here)} times"
    assert here[0]["sha256"] == digest, (
        f"{rel}:{here[0]['line']}: the decision of {date} has been reworded.\n"
        f"  now: {here[0]['body'][:160]}\n"
        f"These are the operator's words. If they changed them, update the "
        f"pin with the new hash and say in the commit that they did; if they "
        f"did not, put the sentence back."
    )


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize("rel", SOURCES)
def test_no_decision_was_added_or_reworded_without_the_operator(rel):
    """The other direction. A tag nobody pinned is a sentence put in their
    mouth, and a reworded one is the same thing with a paper trail."""
    pinned = PINNED.get(rel, [])
    for found in decisions(_text(rel)):
        match = [(d, h, g) for d, h, g in pinned
                 if d == found["date"] and h.lower() in found["body"].lower()]
        assert match, (
            f"{rel}:{found['line']}: a decision tagged {found['date']} that "
            f"nothing pins: {found['body'][:90]!r}. If they said it, pin it "
            f"here; if they did not, it is a rule and must not wear the tag"
        )
        assert any(found["sha256"] == g for _, _, g in match), (
            f"{rel}:{found['line']}: tagged {found['date']} and pinned, but "
            f"the words have moved: {found['body'][:90]!r}"
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
    # From the parser's own spans. This recomputed the block boundary with a
    # second copy of the loop in decisions(), which is the one thing this
    # repository keeps learning not to do: widen the rule in one place and the
    # copy quietly disagrees, here by reporting a covered line as an untagged
    # decision -- in tests/meta, which aborts every session.
    covered = {i for found in decisions(text) for i in found["span"]}

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

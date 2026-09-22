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
        ("2026-09-11", "budes autoamticy navrhovat nove soucasti",
         "01a5de12e6b84cbc9976edfe0a33a2b3cf64fcac9e40b6566f256c9f2703c08f"),
        ("2026-09-13", "kdykoliv dej vedet a ja to hned napisu",
         "78a386cca5a693309b723e034eccc5ac075a45fe4a45bc0d51727209569991e1"),
        ("2026-09-13", "nemam rad cteni",
         "efa0a09b444a4947db604e6e48086ee536c4b2c6882aeead70b2041ce9c52e30"),
        ("2026-09-13", "vzdy jak generujes zpravu na telegram",
         "cbc6e7a36fa90f59701a36317dda5258f88dc3a1e8a972ba8e1f37ba0814e845"),
        ("2026-09-12", "ne zadene schedulery automaticke",
         "414477775223dde3619b3647031988fa6fdaaac3a5c04f0f7ac04451dcbd19fa"),
        ("2026-09-14", "odstrat to rpavidlo at muzu nmormalne loop",
         "5444a72213e3220cba076f610990576c2031818eb9e0a5e5294c8337159205cb"),
        ("2026-09-12", "nechci za mesic zjistit ze v githubu",
         "f04881f6d4780e403c5ce74c6313abba17fd2de5dff818d30ca979aeefcdf296"),
        ("2026-09-10", "a proc nezakladas nalezy sam od sebe",
         "eb6c1d842415ae5685ec1d1ccbf9665cbf32503c62ba03f76f64bfc9207629b0"),
        ("2026-09-10", "kde jsme skoncili a cim pokracovat",
         "d16edd43a89832740f500affa759fdcf1a03417b2206cf043e1c4abadee6f200"),
        ("2026-09-10", "od toho tade je jejich AI NEXUS",
         "ce77fb690e8a55e7903aeab29fc6a678e9922c77ff798d57ba14c8fb712cd480"),
        ("2026-09-09", "ano 5. levny protoze jen cte",
         "bf3b0779a1ff08ab06e6619df7be54265601746348e15345fc35db7fbdb8b9ea"),
        ("2026-09-09", "nechtel po me zadna takova rozhnodnuti",
         "c96da38a0cbea54eaae8ddc2c7eefce96f57a580915164d23f9c876edde987dc"),
        ("2026-09-20", "od jejich bota nexuse",
         "75ad341ae9cacb56a4f6db1c271dc9a8504c728e6155ee8946f79c5482a63eff"),
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
    ".claude/skills/pokracuj/SKILL.md": [
        ("2026-09-13", "chci at je genericky",
         "be2533bc09dfcb673a7fb8d7c50b2c42ea1df305c36bea50cad83aa3e5c068d4"),
        ("2026-09-13", "does not read long answers",
         "e994b217789eb581924c033f2c0f37023a9470382a15936ac364993e59ae88fa"),
    ],
    ".claude/skills/laborator/SKILL.md": [
        ("2026-09-11", "budete skoumat same nove strategie",
         "4510b8cf12e72ee56b866aac91d4a984790023cc0f7140508a277a462b2a20c0"),
        ("2026-09-19", "jako realny laborant v laboratori",
         "66a5684c5763c57c211fc808a4f44c9771dd28bc4061ec3bf7225fd1beb094a8"),
        ("2026-09-19", "eskalovat nevo zpravou na telegram",
         "d53f5ff46901b4b89d3bd03d693358a45cffcd510e2e058046819129f3c820ca"),
        ("2026-09-19", "while the deep lane is at capacity",
         "40313867a490f1b62a286a12f00e18a7d458a388ef9515506d3c4b2d69130c09"),
        ("2026-09-19", "muzes jit testovat platformu a hledat bugy",
         "8db9b81b5e64007479f9c472f9233445c3d7c9a19fb8732bbc502de09d745987"),
        ("2026-09-21", "doporucovat jen veci co jdou v papiru",
         "cb577a012a2a725bef69d94c3c5b61514b7d107a0bf6dc056b6ecd76d7247c9e"),
        ("2026-09-21", "bod 2 nesouhlasim",
         "d02aee93929a533cbbc91a3c5b1f79670cb3033e744ea1c90e4a256efbde6d75"),
        ("2026-09-20", "to taky delej v laborce jak se nudis",
         "6bcc9e3d19ab3a107d1dde286472574e640a5c23de34717057018d2726272d8b"),
    ],
    ".claude/skills/ohlednuti/SKILL.md": [
        ("2026-09-12", "za tri tydny reknu at se ohledne zpet",
         "9c69c567343ffdb50140f3345868612c1ae4385157f892018fcc748e319683b2"),
    ],
    ".claude/skills/deep-pass/SKILL.md": [
        ("2026-09-13", "a proc ne z contextoveho okna",
         "f18fcc72f5b8fbc5edefc55a88d016ee8d8f8a9653d17048268b646c0bf98ef4"),
        ("2026-09-10", "zahrn do do deep pass procesu",
         "c87cf5372cc63054d453a069d8922d430e8c2d2f1b396b4f17f0443cfa7fd166"),
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
    # A question they asked, and the step it produced. They wondered whether
    # the pass could find the triage triad unnecessary over time; wondering is
    # not deciding, and tagging it would put a decision in their mouth that
    # the numbers -- not they -- will make when the condition is met.
    (".claude/skills/deep-pass/SKILL.md",
     "whether the pass can work this out for"),
    # The three lines below quote CYMETICA, not the operator. Their answer of
    # 2026-09-20 to our question about what outside QA should focus on
    # (MSG-0028 -> REPLY-0031) is quoted in their own words, because a
    # paraphrase of a vendor's priorities is how they quietly become ours.
    # The guard cannot tell one speaker from the other -- it matches an
    # italic quotation and a dated attribution -- and it should not be taught
    # to, because "it's only the vendor" is exactly the excuse that would
    # smuggle an untagged operator decision past it. Three named lines with
    # the reason, rather than a rule with a hole in it.
    (".claude/skills/qa-sweep/SKILL.md",
     "what they wanted from an outside QA agent"),
    (".claude/skills/qa-sweep/SKILL.md",
     "the holder rule, the board and its socket"),
    (".claude/skills/qa-sweep/SKILL.md", "Depth, not breadth"),
}


# The operator's own words quoted in CODE. 2026-09-12 noticed that 27 tagged
# paragraphs sat in 18 files this test never read. Most of them are citations
# ("[operator ...] asked for ...") whose authoritative copy is pinned above;
# what cannot drift unnoticed is a VERBATIM quote, `*"..."*`, right after a tag.
# Pinned by the quote alone, not the comment around it, so editing the code
# beside it is free and changing their words is not.
CODE_GLOBS = ("qa/*.py", "scripts/*.py", ".claude/hooks/*.py")
CODE_TAG = re.compile(r"\[operator (\d{4}-\d{2}-\d{2})")
CODE_QUOTE = re.compile(r'\*"(.{8,}?)"\*', re.S)
COMMENT_PREFIX = re.compile(r"^\s*(?:#|//|/\*|\*(?!\")|--)?\s?", re.M)

CODE_QUOTES = [
    (".claude/hooks/next_step.py", "2026-09-10",
     "36106104ca24ac23456f3ab54f8ce63a37a71126073ce966e528591a457a6de6"),
    (".claude/hooks/no_heredoc_writes.py", "2026-09-13",
     "55441599a7daccea3d832f358d39df183337e17627f6f800fc0a79b16c12b576"),
    ("qa/backtests.py", "2026-09-12",
     "800df1f8b93a48069b0b5332e22952ad15fd4bf75fb279abcdcbedd869e532d5"),
    ("qa/fomo.py", "2026-09-14",
     "a5df6c2930cd102f5127a4644d2dd16be5d4dbfb8cb26425c23bce0202b21018"),
    ("qa/fomo.py", "2026-09-14",
     "c56eb4b76383c6f9def1ea9bebe5268fccf8accfd39fd5435e658d348fe66586"),
    ("qa/lab.py", "2026-09-12",
     "3702ccb65894037650ef16bc23705eccf4e49f7bee7107b5d58b5b7adc0412fd"),
    ("qa/lab.py", "2026-09-12",
     "ef4d9d80bc06d1298e03afb93fa1103541d6fabb0ae4d807f6c4bf2f18867dcb"),
    ("qa/surface.py", "2026-09-12",
     "aaff8ea0c2f536368b68993b2c61e4d5867af49595e5b2eb45267c8707545a58"),
    ("scripts/fomo_watch.py", "2026-09-14",
     "a5df6c2930cd102f5127a4644d2dd16be5d4dbfb8cb26425c23bce0202b21018"),
    ("scripts/lab.py", "2026-09-11",
     "902465215bb86ef4bd84111ed6eaa4b36560c662244cb75101f447691ff9d446"),
    ("scripts/lab.py", "2026-09-12",
     "086cc5114766752cfd88b4ffb1216ecc8c77145cf4a51964424aea675d721edc"),
    ("scripts/lab.py", "2026-09-12",
     "8ed03cc0674744855bc3a8df687f6aed15f8d48b2aa52da4ad11eb3b15549d6b"),
    ("scripts/lab.py", "2026-09-19",
     "b728a8019df6a47e5d818eed9c91fff1fd667767bbc4a8b54d946282f3184b9e"),
    ("scripts/processes.py", "2026-09-12",
     "5e560c7516300844aa7e622e12d1412855d789bd281b9a4457be81de6baf6134"),
    ("scripts/render.py", "2026-09-14",
     "9f6840703365a5c4bfe09c3eeaf48da80098999e2b4489b58e45e338655fe4b5"),
]


def code_quotes(text: str) -> list[tuple[str, str]]:
    """(date, sha256) of every verbatim quote that opens right after a tag."""
    out = []
    for tag in CODE_TAG.finditer(text):
        window = text[tag.end():tag.end() + 600]
        quoted = CODE_QUOTE.search(window)
        if not quoted or quoted.start() > 40:
            continue
        words = " ".join(COMMENT_PREFIX.sub("", quoted.group(1)).split())
        out.append((tag.group(1),
                    hashlib.sha256(words.encode("utf-8")).hexdigest()))
    return out


def _code_files() -> list[str]:
    return sorted({str(p.relative_to(REPO)).replace("\\", "/")
                   for pattern in CODE_GLOBS for p in REPO.glob(pattern)})


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_operators_words_quoted_in_code_are_still_their_words():
    """Both directions over the code: a pinned quote gone or reworded, and a
    tagged quote nobody pinned."""
    found = {rel: code_quotes(_text(rel)) for rel in _code_files()}
    for rel, date, digest in CODE_QUOTES:
        assert (date, digest) in found.get(rel, []), (
            f"{rel}: the operator's words of {date} are gone or reworded. "
            f"Put them back, or take it to them")
    pinned = {(rel, date, digest) for rel, date, digest in CODE_QUOTES}
    loose = [f"{rel} {date} {digest[:12]}" for rel, rows in found.items()
             for date, digest in rows if (rel, date, digest) not in pinned]
    assert not loose, ("a tagged quote of the operator in code that nothing "
                       "pins -- pin it if they said it:\n  " + "\n  ".join(loose))


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

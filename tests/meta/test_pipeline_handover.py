"""HANDOVER: what the deep pass could not finish arrives without being asked for.

DEEP-PASS.md is the only thing that survives a /clear, and twice on 2026-09-08 a
session failed to read it. The first time nothing in the auto-loaded context
named the file, and the fix was one line in CLAUDE.md. The second time was this
session: the line was there, it was read, the file was named out loud -- and the
session asked permission to open it instead of opening it. The operator: *"takze
se sama nenacetla? takze to nefunguje?"*

So a pointer has now been tried twice and failed twice, and this hook does not
print a third one. It prints the handover itself: the pass date, and the bold
lead of every item the pass left open. Nothing to go and read afterwards.

That is the one place this differs from `open_threads.py`, whose shape it
otherwise copies exactly. That hook prints ids and withholds the text on the
operator's own objection to context being filled with messages. The difference
is volume and staleness, not principle: a Telegram archive grows without bound
and every line of it is still on disk to be fetched, while the handover is six
lines that the next pass overwrites wholesale.

The three things these tests hold:

  * The item text is present, not a filename. An assertion that only checks for
    "DEEP-PASS.md" in the output would pass on the exact failure this exists to
    stop.
  * The Minority report is carried too. On the 2026-09-08 run every item under
    "Ceka na tebe" was informational and both real decisions were under that
    heading, so a hook that reads only the handover section tells the operator
    nothing is waiting when two things are.
  * It never fails a session, and it is silent when there is no pass.

Fails before .claude/hooks/deep_pass_handover.py exists: the module is missing.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HOOK = REPO_ROOT / ".claude" / "hooks" / "deep_pass_handover.py"

REPORT = """# Deep pass — 2026-09-08

Běh od `f5708fa`, 46 commitů. Runy `PRE-0073`, level V.

## Co se stalo

**Kontrakt audit: 72 checků, ne 275.** Tři auditoři nahlásili 22 mezer.

## Minority report

* **`A3-09` · `test_only_state_module_writes_state_files` skenuje jen `qa/` a
  `scripts/`**, zatímco jeho hláška tvrdí univerzálii. Buď rozšířit glob, nebo
  hlášku zúžit.
* **`A1-04b` · brána na inconclusive obchází měnovou půlku.** Jeden agent tvrdí,
  že s nulou přiznách se vrátí inconclusive dřív.

## Změněná pravidla

* **Guard pravidla 12 se ptá na řádky, ne na hlavičku žurnálu.** Tři agenti
  nezávisle potvrdili, že to strážce nezeslabuje; test jmenuje incident.

## Týden

* **Nic neměnit.** Poměr testů se nepohnul, žádný mechanismus nepřestal
  střílet.

## Čeká na tebe

1. **#83 je jediný živý nález.** `portfolio/summary` hlásí nuly na účtu
   s 39 pozicemi.
2. **Deset pass verifikací odešlo na opravených definicích.** Každá nese větu
   o tom, že to není automaticky identický test.

## Co mě to naučilo

**Audit našel patnáct vad v checcích, které jsem psal ten samý den.** Zelená
sada neříká nic o tom, jestli check měří, co tvrdí.
"""


def _hook():
    spec = importlib.util.spec_from_file_location("deep_pass_handover_mod", HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run(report_path):
    """The hook as the operator's machine runs it at session start."""
    env = dict(os.environ)
    env["QA_DEEP_PASS"] = str(report_path)
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run([sys.executable, str(HOOK)], cwd=str(REPO_ROOT), env=env,
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_hook_carries_the_handover_not_a_pointer(tmp_path):
    """The item text itself, because naming the file has now failed twice.

    This is the assertion that separates this hook from the CLAUDE.md line it
    replaces. Checking only that "DEEP-PASS.md" appears would pass on a hook
    that says nothing but "go and read it" -- which is what a session already
    had in context on 2026-09-08 when it did not read it.
    """
    report = tmp_path / "DEEP-PASS.md"
    report.write_text(REPORT, encoding="utf-8")

    proc = _run(report)
    assert proc.returncode == 0, proc.stderr
    assert "#83 je jediný živý nález" in proc.stdout, (
        "the open item must arrive as text, not as a filename to go and open"
    )
    assert "Deset pass verifikací" in proc.stdout
    assert "2026-09-08" in proc.stdout, "which pass this is"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_hook_carries_the_minority_report_too(tmp_path):
    """Where the decisions actually were on the run that prompted this.

    Every numbered item under "Ceka na tebe" that day was informational -- a
    failing finding they already know about, context for a reply, a count with
    a guard behind it. Both things genuinely wanting the operator's judgement
    were under "Minority report". A hook reading only the handover heading
    would have reported a quiet morning.
    """
    report = tmp_path / "DEEP-PASS.md"
    report.write_text(REPORT, encoding="utf-8")

    proc = _run(report)
    assert proc.returncode == 0, proc.stderr
    assert "A3-09" in proc.stdout
    assert "A1-04b" in proc.stdout


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_hook_carries_what_the_pass_changed_and_the_week(tmp_path):
    """The two headings a pass writes about itself, not about the findings.

    The night loop may now change a rule on its own, under three conditions at
    once, and the third of them is that the morning says in Czech what changed
    and why. A paragraph in a file nobody opens is not saying so -- that is the
    exact failure this hook exists for, which happened twice on 2026-09-08. So
    a changed rule arrives in the same breath as the open items, and the
    operator's veto is a veto over something they have actually seen.

    Tyden is the same shape one rhythm up. A retrospective that lands where
    nobody reads it is a ritual, and the operator's condition was that it must
    not depend on them remembering.
    """
    report = tmp_path / "DEEP-PASS.md"
    report.write_text(REPORT, encoding="utf-8")

    proc = _run(report)
    assert proc.returncode == 0, proc.stderr
    assert "Guard pravidla 12" in proc.stdout, \
        "a rule the pass changed on its own did not reach the morning"
    assert "Nic" in proc.stdout, (
        "the week's answer did not reach the morning -- and 'change nothing' "
        "is the answer that most needs to arrive, because a retrospective that "
        "speaks only when it proposes something becomes a proposal mill"
    )


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_hook_does_not_paste_the_whole_report(tmp_path):
    """Bounded: the leads, not the prose under them.

    The operator's objection that shaped `open_threads.py` was context filled
    with material nobody asked for, and it applies here the moment this grows
    past the summary. What is dropped stays on disk and `Read` fetches it.
    """
    report = tmp_path / "DEEP-PASS.md"
    report.write_text(REPORT, encoding="utf-8")

    proc = _run(report)
    assert "Zelená" not in proc.stdout, "the 'Co me to naucilo' prose is not handover"
    assert "Kontrakt audit" not in proc.stdout, "'Co se stalo' is history, not open work"

    # The assertion that actually holds the docstring's contract, and the one
    # this test did not have until 2026-09-09. Both strings above live under
    # headings SECTIONS never reads, so a hook mutated to append the whole
    # block instead of the bold lead passed every check here -- pasting every
    # paragraph of every item into every session's context, which is the exact
    # thing the operator objected to and this cap exists for. Two auditors
    # reproduced that mutation against this fixture and it stayed green.
    #
    # So: prose that sits UNDER a lead the hook does select.
    for under_a_selected_lead in (
            "portfolio/summary",                 # under "#83 je jediny zivy nalez"
            "zatímco jeho hláška tvrdí",         # under the A3-09 minority lead
            "Poměr testů se nepohnul",           # under the Tyden lead
            "nezávisle potvrdili"):              # under the rule-change lead
        assert under_a_selected_lead not in proc.stdout, (
            f"{under_a_selected_lead!r} is the prose under a lead the hook "
            f"prints, so printing it means the hook is pasting blocks rather "
            f"than leads")
    # Four sections now instead of two, so the cap moves with them -- but not
    # by four times five. The two that a pass writes about ITSELF are capped
    # tighter in the hook: a night that changed six rules has a bigger problem
    # than a long handover, and the week's answer is one paragraph by design.
    # Derived, not a magic number. It read `<= 16` while SECTIONS allowed
    # 5+5+3+2 = 15 leads plus a title and a tail, i.e. 17. Harmless, because
    # this test writes its own fixture and never opens a real report -- which
    # is why two readers of 2026-09-09 called it a live failure and were wrong,
    # and why the number is now computed from the caps it is meant to bound so
    # it cannot drift away from them again.
    budget = sum(cap for _, _, cap in _hook().SECTIONS) + 2
    assert len(proc.stdout.splitlines()) <= budget


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_hook_is_silent_when_there_is_no_deep_pass(tmp_path):
    """No report means no output at all -- not a heading saying zero.

    Same reason as the correspondence hook: one that speaks on every session
    start whether or not it has anything to say is one that gets skipped.
    """
    proc = _run(tmp_path / "nothing-here" / "DEEP-PASS.md")
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_hook_never_fails_a_session(tmp_path):
    """A note about the last pass must not be able to stop the work.

    This runs before the operator has typed anything, so a refusal here is a
    session that will not start. A report with no headings at all, or one
    truncated mid-write, exits 0 with nothing printed.
    """
    shapeless = tmp_path / "DEEP-PASS.md"
    shapeless.write_text("nothing that looks like a report at all", encoding="utf-8")
    proc = _run(shapeless)
    assert proc.returncode == 0, proc.stderr
    assert "Traceback" not in proc.stderr

    truncated = tmp_path / "half.md"
    truncated.write_text("# Deep pass — 2026-09-08\n\n## Čeká na tebe\n\n1. **unf",
                         encoding="utf-8")
    half = _run(truncated)
    assert half.returncode == 0, half.stderr
    assert "Traceback" not in half.stderr


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_committed_report_parses(tmp_path):
    """The one in the repository, not only the fixture.

    A parser that handles the fixture and not the real file is the failure this
    hook exists to prevent, wearing a green test. The bold lead in the real
    report wraps across lines and carries backticks; the fixture copies that,
    but only this holds it against what the skill actually writes.
    """
    committed = REPO_ROOT / "DEEP-PASS.md"
    if not committed.exists():
        conclude(Measurement(
            verdict="inconclusive",
            reason="no DEEP-PASS.md in the repository, so there is no real "
                   "report to hold the parser against; the fixture cases above "
                   "still ran",
            sources={"report": "DEEP-PASS.md"}))
        return

    text = committed.read_text(encoding="utf-8")
    lines = _hook().handover(text)

    # What the parser has to get right about a REAL report, none of it pinned
    # to one pass's content. This asserted `"#83" in some line` until
    # 2026-09-09 -- an item id from the 2026-09-08 pass, in a file the skill
    # overwrites wholesale every run, inside tests/meta, which aborts every
    # session. The first report that did not happen to mention #83 would have
    # stopped the repository, and deep-pass step 9 would have read that as an
    # unresolvable red and reverted the night that wrote it. Found by the
    # contract audit of 2026-09-09, three votes of three.
    labels = {line.strip().split(":", 1)[0] for line in lines[1:-1]}
    plain = _hook()._plain
    heads = {plain(ln[3:]) for ln in text.splitlines() if ln.startswith("## ")}
    expected = {label for wanted, label, _ in _hook().SECTIONS
                if any(wanted in h for h in heads)}

    problems = []
    if not lines:
        problems.append("the committed report yields no handover at all")
    elif not labels:
        problems.append(f"a handover with no labelled items: {lines}")
    elif not labels <= expected:
        problems.append(f"labels {sorted(labels - expected)} came from no "
                        f"heading the report has: {sorted(heads)}")
    # The wrapped bold lead is the thing the fixture was copied from and the
    # thing a naive line-at-a-time parser gets wrong, so hold it against the
    # real file: every printed lead must be a closed **...** span, joined.
    for line in lines[1:-1]:
        lead = line.split(": ", 1)[-1]
        if "**" in lead or lead.endswith("**"):
            problems.append(f"an unclosed or unjoined bold lead: {lead!r}")

    conclude(Measurement(
        verdict="failed" if problems else "passed",
        reason=("; ".join(problems) if problems else
                f"the committed report parses: {len(labels)} section(s) "
                f"{sorted(labels)}, {len(lines) - 2} lead(s), every one a "
                f"closed bold span"),
        left=problems,
        sources={"report": "DEEP-PASS.md"}))

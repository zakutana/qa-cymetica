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
    assert len(proc.stdout.splitlines()) <= 12


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
        return

    lines = _hook().handover(committed.read_text(encoding="utf-8"))
    assert lines, "the committed report yields a handover"
    assert any("#83" in line for line in lines)

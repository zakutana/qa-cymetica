"""One file for how the laboratory manager improves, from the operator's feedback.

[operator 2026-10-05] *"mas jako manager laborky nejakou soubor kde si pises
imprvmenty jak lepe runovat laborky podle mych feedbacku?"* and, on hearing it was
three places (the diary, memory files, NEXT.md): *"tak to pekne sjednot ne at je to
na jednom miste tvezlepsovani jako managera laborky"*.

`docs/lab-manager.md` is that file. The diary keeps the raw lines the morning report
reads; every `feedback` and `acted` entry is ALSO written there, so a feedback cannot
be given and left in one place only -- which is how today's was missing for a week.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
FILE = REPO / "docs" / "lab-manager.md"


def _lab(tmp_path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("QA_LAB_MANAGER_FILE", str(tmp_path / "lab-manager.md"))
    import qa.state
    importlib.reload(qa.state)
    import qa.lab
    importlib.reload(qa.lab)
    return qa.lab, tmp_path / "lab-manager.md"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_feedback_and_acted_reach_the_manager_file_and_nothing_else_does(
        tmp_path, monkeypatch):
    lab, target = _lab(tmp_path, monkeypatch)
    for kind in ("log", "lesson", "next", "telegram"):
        lab.note_entry("LAB-0001", f"a {kind} line", kind=kind)
    assert not target.exists(), "only feedback and acted belong in the file"

    lab.note_entry("LAB-0001", "ja te nechapu ze porad prodelavas na event cartach",
                   kind="feedback")
    lab.note_entry("LAB-0001", "event cards are no longer the first thing a tick reaches for",
                   kind="acted")
    text = target.read_text(encoding="utf-8")
    assert re.search(r"- \d{4}-\d{2}-\d{2} · feedback · ja te nechapu ze porad "
                     r"prodelavas na event cartach", text)
    assert re.search(r"· acted · event cards are no longer", text)
    assert any(r["kind"] == "feedback" for r in lab.entries()), \
        "the diary keeps writing: the morning report reads it"

    target.write_text("# x\n\n## Open improvements\n\n- first thing\n- second thing\n\n"
                      "## Log\n\n- 2026-10-05 · feedback · y\n", encoding="utf-8")
    assert lab.manager_open_lines() == ["first thing", "second thing"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_repository_file_has_its_sections_and_at_most_ten_open_lines():
    assert FILE.is_file(), "docs/lab-manager.md is the one place; it must exist"
    text = FILE.read_text(encoding="utf-8")
    for heading in ("## Open improvements", "## How the manager goes wrong",
                    "## Feedback and what changed"):
        assert heading in text, heading
    section = text.split("## Open improvements", 1)[1].split("\n## ", 1)[0]
    open_lines = [ln for ln in section.splitlines() if ln.startswith("- ")]
    assert len(open_lines) <= 10, "ten open lines, like NEXT.md: more is a backlog nobody reads"

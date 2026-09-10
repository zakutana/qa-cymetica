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

    hook = REPO / ".claude" / "hooks" / "memory_index.py"
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

"""Git holds the captures something stands on, and no others.

`evidence/` reached 469 MB on disk and 7 747 tracked files by 2026-09-12,
growing 40-170 MB a day -- 120 MB of one day's 170 written by two checks that
walk the event-card listing page by page on every run. On 2026-09-09 a plan
decided to stop committing captures and nobody built it; three days later the
operator asked not to find gigabytes on GitHub in a month.

Two assertions, and they pull in opposite directions on purpose:

  * whatever the COMMITTED journal and ledger cite has to be in the repository,
    or a clone cannot check the verdicts we have already sent the vendor --
    scripts/verify.py promises them "provided on request" in every message;
  * nothing else may be tracked, or the store creeps back into git one poll at
    a time.

Read from HEAD rather than from the working tree for the first one. The console
appends a journal event every fifteen minutes, and a guard over the working
tree would be red for half of every day over captures no clone can see yet.

qa/keepset.py is the single reader for both, so the tracker
(`scripts/keep.py track`), the pruner (`scripts/prune_runs.py`) and this guard
cannot grow three ideas of what "cited" means.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from qa import keepset, manifest
from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

REPO = Path(__file__).resolve().parent.parent.parent

# Citations written by scripts/migrate_ledger.py on 2026-09-04, before the
# evidence store existed: each names a source file and a key inside it, not a
# capture. They are not missing evidence and never were.
LEGACY_PREFIXES = ("submissions.json#", "bounty.json#", "archive#")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_capture_the_committed_state_cites_can_still_be_produced():
    """A verdict we sent them names ids; we must still be able to produce them.

    Until 2026-09-12 this said "is in the repository", and that was the right
    shape while the bodies were in git. They are not any more (D3 of
    docs/data-plan.md): 167 MB of them, growing 47 MB on a working day, against
    16.5 MB of actual code. What we promised the vendor is that a capture is
    "retained and provided on request" -- `verify.py`'s own note adds that the
    repository is private, so a clone was never the offer. Git was our storage
    choice, and it changed.

    So the obligation is unchanged and the test now states it accurately: every
    cited id is in the committed manifest, and its body is either stamped into
    an archive or still on this disk. Losing one means losing the answer to a
    question the vendor is entitled to ask.

    Stated over the citation rather than over the tracker, as before: the
    mechanism that keeps a body reachable can be replaced without touching this.
    """
    needed = keepset.must_be_tracked()
    if needed is None:
        conclude(Measurement(
            verdict="inconclusive",
            reason="git could not be read, and a read we could not make is "
                   "not an empty read"))
        return

    known = manifest.read()
    unproved, unreachable = [], []
    for evidence_id in sorted(needed):
        row = known.get(evidence_id)
        if row is None:
            unproved.append(evidence_id)
        elif not row.get("archive") and not keepset.evidence_path(
                evidence_id).is_file():
            unreachable.append(evidence_id)

    lost = unproved + unreachable
    conclude(Measurement(
        verdict="failed" if lost else "passed",
        reason=(f"{len(unproved)} cited capture(s) have no manifest line and "
                f"{len(unreachable)} are in no archive and not on disk: "
                f"{', '.join(m[:12] for m in lost[:5])}"
                if lost else
                f"all {len(needed)} cited capture(s) are proved by the "
                f"manifest and reachable in an archive or on disk"),
        left={"cited": len(needed)}, right={"lost": len(lost)},
        population={"lost": lost[:20]},
        sources={"journal": "HEAD:state/journal/events.jsonl",
                 "ledger": "HEAD:state/ledger.json",
                 "manifest": manifest.manifest_path().name}))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_git_holds_no_capture_body_at_all():
    """The other direction, and the one that keeps the repository small.

    It used to read "no capture nothing stands on", which allowed the cited set
    -- 1 178 files and 167 MB by 2026-09-12, growing 47 MB on a working day
    against 16.5 MB of actual code. Since D3 the answer is simply none: the
    proof is the manifest, the bodies are in `archive/`, and git carries 228 KB
    where it carried 167 MB.

    Stronger than what it replaced, which is the only direction a guard may be
    rewritten. "Nothing beyond the cited set" could not notice the cited set
    itself growing without bound; this cannot miss anything.
    """
    tracked = keepset.tracked_evidence()
    if tracked is None:
        conclude(Measurement(
            verdict="inconclusive", reason="git could not list evidence/"))
        return

    extra = sorted(tracked)
    conclude(Measurement(
        verdict="failed" if extra else "passed",
        reason=(f"{len(extra)} capture body(ies) are still tracked -- "
                f"`keep.py archive --month YYYY-MM --release` moves them; "
                f"evidence/ is gitignored: {', '.join(e[:12] for e in extra[:5])}"
                if extra else
                "git holds no capture body; the manifest proves them and "
                "archive/ holds them"),
        left={"tracked": len(extra)}, right={"allowed": 0},
        population={"extra": extra[:10]},
        sources={"keepset": "qa/keepset.py::tracked_evidence"}))


SECRET_NAME = re.compile(r"KEY|TOKEN|SECRET|PASS|AUTH", re.I)


def _env_secrets() -> dict[str, str]:
    try:
        text = (REPO / ".env").read_text(encoding="utf-8")
    except OSError:
        return {}
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        if len(value) >= 12 and SECRET_NAME.search(name):
            out[name.strip()] = value
    return out


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_capture_we_keep_is_proved_by_the_manifest():
    """The proof that outlives the body.

    167 MB of capture bodies are in git and the tree grew 47 MB in the eight
    hours after the prune of 2026-09-12. They are leaving for a monthly archive,
    and the manifest is what makes that safe: evidence is addressed by the
    sha256 of its content, so id + size + the call it answered proves what we
    had and that it has not changed.

    This runs BESIDE the two git assertions above rather than replacing them.
    The bodies are still tracked today; the tracked-ness rule goes when D3
    actually moves them, not before. A guard relaxed ahead of its replacement is
    a window with nothing watching, and this file exists because of one.

    `call_key` reads the body, so an entry can only be written while the capture
    is on this disk. A capture in the keep set with no manifest line is one we
    would lose the proof of the moment it is archived.
    """
    keep = keepset.must_keep()
    known = manifest.read()
    missing = sorted(set(keep) - set(known))

    conclude(Measurement(
        verdict="failed" if missing else "passed",
        reason=(f"{len(missing)} of {len(keep)} kept capture(s) have no "
                f"manifest line, so archiving them would lose what they were: "
                f"{', '.join(m[:12] for m in missing[:5])}"
                if missing else
                f"all {len(keep)} kept capture(s) are in the manifest"),
        left=len(missing), right=0,
        sources=[manifest.manifest_path().name]))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_tracker_lets_go_of_what_stopped_being_cited():
    """`track` only ever added, so the keep set could only grow.

    The day it bit: 2026-09-12, folding the ledger onto a fresh verification
    run left 115 captures from the previous run tracked in git and cited by
    nothing, and the guard above went red with no mechanism able to clear it --
    somebody had to run `git rm --cached` by hand. A mechanism a person must
    run is not one.

    The refusal is the important half. `must_keep` reading empty -- a lenient
    parse that found nothing, git unreadable, a half-written row -- must never
    be taken as "nothing is cited, drop it all", because that is one command
    away from deleting the evidence every verdict we have sent promises the
    vendor on request.
    """
    from qa import keepset

    dropped, why = keepset.untrackable(keep={}, held={"aaa", "bbb"})
    assert dropped == [] and "empty" in why.lower(), why

    dropped, why = keepset.untrackable(keep={"aaa": "row"}, held=None)
    assert dropped == [] and "git" in why.lower(), why

    keep = {"aaa": "row", "bbb": "their-words"}
    dropped, why = keepset.untrackable(keep=keep, held={"aaa", "bbb", "ccc"})
    assert dropped == ["ccc"], dropped

    dropped, why = keepset.untrackable(keep=keep, held={"aaa", "bbb"})
    assert dropped == [] and not why, why

    # A migration citation names no capture on disk; it must not be read as a
    # tracked file to drop, and it must not be read as a reason to keep one.
    keep_with_lost = {**keep, "0" * 64: "row"}
    dropped, _ = keepset.untrackable(keep=keep_with_lost, held={"aaa", "bbb"})
    assert dropped == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_no_capture_in_the_repository_carries_a_real_key():
    """The store we push, read whole, against the keys this machine holds.

    `tests/meta/test_pipeline_secrets.py` proves the redactor works on a capture
    built for it. This is the other question -- whether a key ever did reach
    disk by a path nobody modelled -- and it is a fact about the repository, so
    it is here and not there: it reads every tracked capture, and tests/meta
    runs at the start of every session.

    Names only in the failure message. A guard that printed the value it found
    would put the key in the run record, the terminal and the transcript.
    """
    secrets = _env_secrets()
    if not secrets:
        conclude(Measurement(
            verdict="inconclusive",
            reason="no .env on this machine, so there is no key to look for"))
        return

    listed = subprocess.run(["git", "ls-files", "evidence"], cwd=REPO,
                            capture_output=True, text=True)
    if listed.returncode != 0:
        conclude(Measurement(
            verdict="inconclusive", reason="git could not list evidence/"))
        return

    needles = {name: value.encode("utf-8") for name, value in secrets.items()}
    hits: dict[str, int] = {}
    read = 0
    for line in listed.stdout.split():
        try:
            blob = (REPO / line.strip()).read_bytes()
        except OSError:
            continue
        read += 1
        for name, needle in needles.items():
            if needle in blob:
                hits[name] = hits.get(name, 0) + 1

    conclude(Measurement(
        verdict="failed" if hits else "passed",
        reason=(f"a key from .env is in the tracked store: "
                f"{', '.join(f'{n} in {c} file(s)' for n, c in hits.items())}"
                if hits else
                f"none of the {len(secrets)} key(s) in .env appears in any of "
                f"the {read} tracked capture(s)"),
        left={"keys": sorted(secrets)}, right={"captures": read},
        sources={"store": "evidence/ (tracked files only)"}))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_pre_commit_hook_that_stages_a_file_reaches_the_commit(tmp_path):
    """The assumption the whole design rests on, executed rather than believed.

    `.githooks/pre-commit` adds the captures a commit's own state cites. That
    only keeps the repository consistent if git includes what a hook stages --
    git re-reads the index after the hook, but "I read that somewhere" is how a
    guard ends up asserting a behaviour nobody ran. If this ever goes red, the
    hook is not a mechanism and the fold and the deep pass are the only
    tracking there is.
    """
    def git(*args):
        return subprocess.run(["git", *args], cwd=tmp_path,
                              capture_output=True, text=True)

    git("init", "-q")
    git("config", "user.email", "guard@example.com")
    git("config", "user.name", "guard")
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    (hooks / "pre-commit").write_text(
        "#!/bin/sh\ngit add staged-by-the-hook.txt\nexit 0\n", encoding="utf-8")
    os.chmod(hooks / "pre-commit", 0o755)
    git("config", "core.hooksPath", "hooks")

    (tmp_path / "asked-for.txt").write_text("one", encoding="utf-8")
    (tmp_path / "staged-by-the-hook.txt").write_text("two", encoding="utf-8")
    git("add", "asked-for.txt")
    committed = git("commit", "-m", "one")
    if committed.returncode != 0:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"git could not commit in a temporary repository: "
                   f"{committed.stderr.strip()[:160]}"))
        return

    in_commit = set(git("ls-tree", "--name-only", "HEAD").stdout.split())
    conclude(Measurement(
        verdict="passed" if "staged-by-the-hook.txt" in in_commit else "failed",
        reason=("a file staged by pre-commit is in the commit"
                if "staged-by-the-hook.txt" in in_commit else
                "git did NOT include what the hook staged -- .githooks/pre-commit "
                "cannot be what keeps cited captures in the repository"),
        left={"in_commit": sorted(in_commit)},
        right={"expected": "staged-by-the-hook.txt"},
        sources={"hook": ".githooks/pre-commit"}))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_keep_hook_cannot_block_a_commit(tmp_path):
    """Run it where nothing it needs exists. It must still exit 0.

    A bookkeeping hook that can fail is a hook that stops the operator
    committing, which is the one thing it may never do -- the same standard
    `.githooks/prepare-commit-msg` holds itself to.
    """
    import shutil

    hook = REPO / ".githooks" / "pre-commit"
    shell = shutil.which("sh") or shutil.which("bash")
    if not hook.is_file() or not shell:
        conclude(Measurement(
            verdict="inconclusive",
            reason=("no .githooks/pre-commit" if not hook.is_file()
                    else "no POSIX shell on PATH to run the hook with")))
        return

    result = subprocess.run([shell, str(hook)], cwd=tmp_path,
                            capture_output=True, text=True)
    conclude(Measurement(
        verdict="passed" if result.returncode == 0 else "failed",
        reason=(f"the hook exits {result.returncode} where scripts/keep.py "
                f"does not exist: {result.stderr.strip()[:160]}"),
        left={"exit": result.returncode}, right={"required": 0},
        sources={"hook": ".githooks/pre-commit"}))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_citations_that_are_not_captures_are_the_migration_s():
    """23 ids name a pre-contract source, and that must stay the reason.

    Without this the first guard would report them as missing files forever,
    and the honest sentence -- the store did not exist yet -- would have to be
    remembered instead of asserted.
    """
    from qa.state import read_events

    legacy = sorted(keepset.legacy_citations(read_events()))
    strays = [item for item in legacy
              if not item.startswith(LEGACY_PREFIXES)]
    conclude(Measurement(
        verdict="failed" if strays else "passed",
        reason=(f"citation(s) that are neither a sha256 nor the migration's "
                f"provenance: {', '.join(strays[:5])}" if strays else
                f"{len(legacy)} non-capture citation(s), all written by the "
                f"2026-09-04 migration"),
        left={"legacy": len(legacy)}, right={"strays": len(strays)},
        population={"examples": legacy[:3]},
        sources={"journal": "state/journal/events.jsonl"}))

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

import importlib.util
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from qa import archive, keepset, manifest
from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude


def _reminders():
    """scripts/processes.py, loaded so the reminder can be RUN rather than
    grepped for -- the difference this file learned on 2026-09-20."""
    path = Path(__file__).resolve().parents[2] / "scripts" / "processes.py"
    spec = importlib.util.spec_from_file_location("processes_archive", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

REPO = Path(__file__).resolve().parent.parent.parent

# Citations written by scripts/migrate_ledger.py on 2026-09-04, before the
# evidence store existed: each names a source file and a key inside it, not a
# capture. They are not missing evidence and never were.
LEGACY_PREFIXES = ("submissions.json#", "bounty.json#", "archive#")
# What the 2026-09-04 migration left, counted. A floor and a ceiling at once:
# the journal is append-only and migrate_ledger.py was retired 2026-09-09, so
# nothing can add to this set and nothing can take from it -- a different
# number means a reader went blind or the journal was rewritten, and both are
# louder than the "0, all the migration's" this guard used to report.
LEGACY_COUNT = 23


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
    cited id is in the committed manifest, and its body is **in a bundle this
    test opens** or still on this disk. Losing one means losing the answer to a
    question the vendor is entitled to ask.

    A machine with neither a store nor a bundle answers `inconclusive`. A clone
    holds the manifest and nothing else, and "I cannot see the bodies from
    here" is not "the bodies are gone" -- rule 8.

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

    # From HEAD, like the citations above it. This read the working tree, so a
    # manifest line written but not committed -- `git commit --no-verify`, or a
    # clone with no `core.hooksPath`, which is the case the deep pass's step 0
    # exists to repair -- proved a citation that a clone would find bare. The
    # docstring says "committed manifest"; now both halves come from the same
    # place. 3/3 on triage, 2026-09-13.
    raw = keepset._committed("audits/evidence-manifest.jsonl")
    if raw is None:
        conclude(Measurement(
            verdict="inconclusive",
            reason="the committed manifest could not be read from git, and a "
                   "read we could not make is not an empty read"))
        return
    known = manifest.parse(raw)
    bundles = sorted((REPO / "archive").glob("evidence-*.tar.xz"))
    held: set[str] = set()
    for bundle in bundles:
        held |= archive.members(bundle)
    on_disk = keepset.evidence_path
    store = (REPO / "evidence").is_dir()

    if not bundles and not store:
        conclude(Measurement(
            verdict="inconclusive",
            reason="this machine holds neither an evidence store nor an "
                   "archive, so reachability cannot be read here. The "
                   "manifest is the proof and it is in git; rule 8 -- a read "
                   "we could not make is not an empty read"))
        return

    unproved, unreachable = [], []
    for evidence_id in sorted(needed):
        row = known.get(evidence_id)
        if row is None:
            unproved.append(evidence_id)
        elif evidence_id not in held and not on_disk(evidence_id).is_file():
            # NOT `row.get("archive")`. That stamp is a string the archive
            # writes about itself, so the guard was reading its own writer --
            # delete the bundle and it stayed green. Three independent
            # reviewers said so on 2026-09-12, and the commit that introduced
            # it claimed "both guards went UP" when this one had gone down:
            # it replaced a physical check (a file git actually holds) with a
            # self-report.
            unreachable.append(evidence_id)

    lost = unproved + unreachable
    conclude(Measurement(
        verdict="failed" if lost else "passed",
        reason=(f"{len(unproved)} cited capture(s) have no manifest line and "
                f"{len(unreachable)} are in no bundle and not on disk: "
                f"{', '.join(m[:12] for m in lost[:5])}"
                if lost else
                f"all {len(needed)} cited capture(s) are proved by the "
                f"manifest and reachable in an archive or on disk"),
        left={"cited": len(needed)}, right={"lost": len(lost)},
        population={"lost": lost[:20]},
        sources={"journal": "HEAD:state/journal/events.jsonl",
                 "ledger": "HEAD:state/ledger.json",
                 "manifest": "HEAD:audits/evidence-manifest.jsonl"}))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_no_file_in_git_nears_the_size_github_refuses():
    """GitHub refuses a push that carries a file over 100 MB, and warns from 50.

    audits/lab/fomo_signals.jsonl -- `keep.py snapshot`'s flat copy of a diary
    growing up to 20 MB a day -- was 87 MB in HEAD on 2026-10-11, a day or two
    from a refused push at the end of a deep pass, the one step nothing runs
    after. Half the hard limit is the ceiling, so the day it is crossed is a
    red test and not a push that fails at night. Read from HEAD -- and, since
    a push sends every commit since upstream, not only the last one, every blob
    of those commits against the hard limit (B07, deep pass 2026-10-15: a 120 MB
    file committed and shrunk a commit later passed a HEAD-only read).
    """
    ceiling = 50 * 1024 * 1024
    out = subprocess.run(["git", "ls-tree", "-r", "-l", "HEAD"], cwd=REPO,
                         capture_output=True, text=True, check=True,
                         encoding="utf-8").stdout
    big = []
    for line in out.splitlines():
        meta, _, path = line.partition("\t")
        size = meta.split()[-1]
        if size.isdigit() and int(size) > ceiling:
            big.append(f"{path} {int(size) / 1e6:.1f} MB")
    assert not big, (f"{len(big)} file(s) in HEAD over 50 MB, half of what "
                     f"GitHub accepts: {big}")

    hard = 100 * 1024 * 1024
    objects = subprocess.run(["git", "rev-list", "--objects", "@{upstream}..HEAD"], cwd=REPO,
                             capture_output=True, text=True, encoding="utf-8")
    if objects.returncode != 0:
        return                      # no upstream (a fresh clone): HEAD above is all a push sends
    sized = subprocess.run(["git", "cat-file", "--batch-check=%(objecttype) %(objectsize) %(rest)"],
                           cwd=REPO, input=objects.stdout, capture_output=True, text=True,
                           check=True, encoding="utf-8").stdout
    refused = [f"{rest} {int(size) / 1e6:.1f} MB" for kind, size, rest in
               (line.split(" ", 2) + [""] * (3 - len(line.split(" ", 2))) for line in sized.splitlines())
               if kind == "blob" and size.isdigit() and int(size) > hard]
    assert not refused, (f"{len(refused)} blob(s) in commits not yet pushed are over 100 MB, which "
                         f"GitHub refuses whatever HEAD holds now: {refused}")


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
def test_the_archive_has_a_caller():
    """D2 of the data plan built the bundle and nothing ever called it again.

    `keep.py track` and `keep.py snapshot` run in the deep pass every time;
    `archive` ran once, by hand, on 2026-09-12. So the bundle stayed that
    day's snapshot while the manifest went on adding rows with `archive: ""`,
    and by 2026-09-20 there were 1 145 bodies on disk that nothing would ever
    let go of -- the half of the data plan that governs the disk, quietly not
    running. A mechanism nobody calls is not a mechanism, the same sentence as
    the sibling below.

    Two callers, because they answer different questions: the deep pass does
    the work, and `processes.py reminders` tells the operator when it is worth
    doing by hand.
    """
    # The CALL, not the words. The first version of this asserted that the
    # string "keep.py archive" appeared in each file -- and it appears in
    # prose in both, in the skill's own explanatory bullet and in two
    # comments in processes.py. Deleting both real callers left it green:
    # a test written to guard "the archive has a caller" that was independent
    # of whether one existed. Found by two readers on 2026-09-20.
    skill = (REPO / ".claude" / "skills" / "deep-pass" / "SKILL.md").read_text(
        encoding="utf-8")
    called = [line for line in skill.splitlines()
              if line.strip().startswith(("python scripts/keep.py archive",
                                          "$PY scripts/keep.py archive"))]
    assert called, (
        "the deep pass tracks and snapshots and never bundles: no line of "
        "the skill RUNS keep.py archive, whatever its prose says about it")

    processes = (REPO / "scripts" / "processes.py").read_text(encoding="utf-8")
    mod = _reminders()
    due = mod.reminders({"unpushed": 0, "last_pass": None, "week_last": None,
                         "open_next": [], "plan_phases": [],
                         "evidence_unarchived": 10_000},
                        datetime(2026, 9, 20, tzinfo=timezone.utc))
    assert any("keep.py archive" in line for line in due), (
        f"nothing tells the operator the bundle is owed: reminders() over "
        f"10 000 unarchived captures printed {due}")
    assert "keep.py archive" in processes


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
    """The store, read whole, against the keys this machine holds.

    `tests/meta/test_pipeline_secrets.py` proves the redactor works on a capture
    built for it. This is the other question -- whether a key ever did reach
    disk by a path nobody modelled.

    It read `git ls-files evidence` until 2026-09-12, which is the day the
    bodies LEFT git. From that hour it iterated zero paths and reported
    "passed" over a population of nothing, in the guard that exists to catch a
    leaked key -- rule 10's "an empty measurement is not a pass", in the worst
    possible place. Its siblings in this file were rewritten for that move and
    this one was not: the caller of a changed storage decision was missed.

    So it follows the bodies. Everything under `evidence/` on this disk, and
    every member of every bundle in `archive/`, which between them are where a
    capture can now be. Nothing to read at all is inconclusive, not passed.

    Names only in the failure message. A guard that printed the value it found
    would put the key in the run record, the terminal and the transcript.
    """
    secrets = _env_secrets()
    if not secrets:
        conclude(Measurement(
            verdict="inconclusive",
            reason="no .env on this machine, so there is no key to look for"))
        return

    needles = {name: value.encode("utf-8") for name, value in secrets.items()}
    hits: dict[str, int] = {}
    read = 0

    for body in (REPO / "evidence").rglob("*.json"):
        try:
            blob = body.read_bytes()
        except OSError:
            continue
        read += 1
        for name, needle in needles.items():
            if needle in blob:
                hits[name] = hits.get(name, 0) + 1

    import tarfile

    for bundle in sorted((REPO / "archive").glob("evidence-*.tar.xz")):
        try:
            with tarfile.open(bundle, "r:xz") as held:
                for member in held.getmembers():
                    source = held.extractfile(member) if member.isfile() else None
                    if source is None:
                        continue
                    blob = source.read()
                    read += 1
                    for name, needle in needles.items():
                        if needle in blob:
                            hits[name] = hits.get(name, 0) + 1
        except (OSError, tarfile.TarError):
            conclude(Measurement(
                verdict="inconclusive",
                reason=f"{bundle.name} could not be opened, and a bundle we "
                       f"cannot read is not a bundle with no key in it"))
            return

    if not read:
        conclude(Measurement(
            verdict="inconclusive",
            reason="this machine holds no capture, on disk or in a bundle, so "
                   "there was nothing to search -- rule 10, an empty "
                   "measurement is not a pass"))
        return

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


def _posix_shell() -> str | None:
    """A shell that can actually run a hook, or None.

    `shutil.which("bash")` on Windows finds `C:\\Windows\\System32\\bash.exe`
    first, which is the WSL launcher and fails with "execvpe(/bin/bash)" on a
    machine that has no distro installed -- so the hook test failed on the
    operator's machine while the hook itself was fine (2026-09-30, the same on
    the commit before the cloud handover). Git ships its own `sh`; that is the
    one git itself runs hooks with, so it is the right one to test with.
    """
    import shutil

    found = shutil.which("sh")
    if found:
        return found
    exec_path = subprocess.run(["git", "--exec-path"], capture_output=True,
                               text=True).stdout.strip()
    if exec_path:
        root = Path(exec_path).parents[2]
        for candidate in (root / "usr" / "bin" / "sh.exe", root / "bin" / "sh.exe"):
            if candidate.is_file():
                return str(candidate)
    bash = shutil.which("bash")
    if bash:
        probe = subprocess.run([bash, "-c", "exit 0"], capture_output=True)
        if probe.returncode == 0:
            return bash
    return None


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_keep_hook_cannot_block_a_commit(tmp_path):
    """Run it where nothing it needs exists. It must still exit 0.

    A bookkeeping hook that can fail is a hook that stops the operator
    committing, which is the one thing it may never do -- the same standard
    `.githooks/prepare-commit-msg` holds itself to.
    """
    import shutil

    hook = REPO / ".githooks" / "pre-commit"
    shell = _posix_shell()
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

    It asserted only that none of them is a stray, which an EMPTY set satisfies
    perfectly. `read_events()` honours QA_STATE_DIR and returns [] for a
    missing journal, so all three readers of 2026-09-12 got a green "0
    non-capture citation(s), all written by the 2026-09-04 migration" -- a
    sentence about 23 ids, said over nothing. One went further and stubbed the
    citation reader itself blind; that passed too. Rule 8 inverted, in the
    guard that exists to keep one sentence honest. So the number is pinned:
    the journal is append-only and the migration is retired, so 23 can only
    move if something stopped reading, and that is the failure worth hearing
    about. C08, triage 3/3.
    """
    from qa.state import read_events

    events = read_events()
    legacy = sorted(keepset.legacy_citations(events))
    if not events or not legacy:
        conclude(Measurement(
            verdict="inconclusive",
            reason=(f"read {len(events)} journal event(s) and "
                    f"{len(legacy)} pre-contract citation(s) where "
                    f"{LEGACY_COUNT} are recorded -- a citation we could not "
                    f"read is not a citation that is not there, and nothing "
                    f"here can be said about a population nobody saw"),
            sources={"journal": "state/journal/events.jsonl"}))
        return

    strays = [item for item in legacy
              if not item.startswith(LEGACY_PREFIXES)]
    if len(legacy) != LEGACY_COUNT:
        conclude(Measurement(
            verdict="failed",
            reason=(f"{len(legacy)} pre-contract citation(s) where "
                    f"{LEGACY_COUNT} were recorded on 2026-09-04. The journal "
                    f"is append-only and the migration is retired, so this "
                    f"number does not move on its own: either the reader "
                    f"stopped reading or the journal was rewritten"),
            left={"legacy": len(legacy)}, right={"recorded": LEGACY_COUNT},
            population={"examples": legacy[:3]},
            sources={"journal": "state/journal/events.jsonl"}))
        return

    conclude(Measurement(
        verdict="failed" if strays else "passed",
        reason=(f"citation(s) that are neither a sha256 nor the migration's "
                f"provenance: {', '.join(strays[:5])}" if strays else
                f"{len(legacy)} non-capture citation(s), all written by the "
                f"2026-09-04 migration"),
        left={"legacy": len(legacy)}, right={"strays": len(strays)},
        population={"examples": legacy[:3]},
        sources={"journal": "state/journal/events.jsonl"}))

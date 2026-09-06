# Operating rules for qa-cymetica

Read this before touching anything in `state/`.

On 2026-09-05 an audit classified every finding-state change an operator had
watched. **71 of 109 were self-inflicted** — produced by our own code
re-deriving state, not by the platform changing. The rules below are what
replaced that, and each one has a test that names the incident it prevents.
A red test here is the system working. Do not fix it by relaxing the rule.

## The rule, said once

> A row in the ledger changes **only** when `ledger.py --run <id>` composes an
> *admissible* run record (CHECK axis), or when an event with an id is
> appended to the journal (FILING axis). Every change writes a transition
> naming its cause. There is no field a state can be written into by hand, and
> the loader refuses a file that contains one.

`tests/meta/test_pipeline_fold.py::test_no_state_change_without_run_id_or_event_id`
is that sentence, executable, over 200 random sequences.

## The two axes

| Axis | Moved only by | States |
|---|---|---|
| CHECK | an admissible run that adjudicated **every** check the row declares | UNVERIFIED · REPRODUCING · PASSING · PASSING_UNPINNED · CHECK_CHANGED · INCONCLUSIVE · UNVERIFIABLE |
| FILING | a journal event | NOT_RAISED · RAISED · REPLIED · FIX_CLAIMED · WITHDRAWN · SUPERSEDED |

The displayed state is the **composition** of the two, computed at render
time. It is never stored, so it cannot be assigned. `VERIFIED FIXED` occupies
exactly one cell: our check passing under the fingerprint it last failed
under, beside their claim of a fix.

## Run admissibility

| Level | Requires | May |
|---|---|---|
| **R** | schema 2 with `collected`; fingerprint did not drift; `exit_status` agrees with the results; every result was collected | open a defect |
| **V** | R **+** clean tree **+** a `prereg` tag whose commit is HEAD | additionally verify a fix |

Make one with:

```bash
python scripts/prereg.py new --selector tests --window 30 --tag
```

then `pytest tests --prereg PRE-NNNN`, then `python scripts/ledger.py --run <run_id>`.

## The twelve rules

1. **Never merge a partial run as verification.** A partial run may open
   `REPRODUCING`; the fold never closes what it did not run.
2. **Never "the latest file".** Use `ledger.py --run <id>`. Without `--run` it
   takes the newest *admissible* run and, if there is none, prints what is
   wrong with each candidate instead of guessing.
3. **Never set a state by hand.** There is nowhere to write one. If the state
   looks wrong, fix the run or the event, not the state.
4. **Never edit `state/*.json` or `events.jsonl`.** Corrections are events via
   `scripts/withdraw.py`, always with a reason.
5. **Never change a check definition and compose a verifying run in one
   commit.** Change → commit → tag → run. A changed check reads
   `CHECK_CHANGED` and wants a justified `rebind-check` or `pin-fingerprint`.
6. **Verification = clean tree + tagged preregistration + full selector.**
   Anything else is exploratory evidence and moves nothing.
7. **Their "fixed" is a claim.** It moves the FILING axis only, and opens a
   re-verify obligation. Only a level-V run under the pinned fingerprint
   clears it.
8. **A failed read is not an empty read.** The fold refuses to move a filing
   state on a non-ok read and marks the row stale.
9. **A submission is two events.** Intent before the POST, outcome after.
   `accepted` needs 2xx **and** a server report id. Unclear is `unknown` and
   is settled with `--reconcile`, never by editing.
10. **Inconclusive is never a defect.** An empty measurement is not filed. A
    check that stops reading its source is retired by an *event*, and on a
    filed row it opens a `repair_check` obligation.
11. **A withdrawal prints its debts.** The row shows "retraction owed on #N"
    until a `retraction-sent` event clears it.
12. **A test enforces this, not memory.** `tests/repo/test_repo_consistency.py`
    checks that the committed ledger is what its inputs fold to and that the
    committed dashboard is a render of it.

## After any change to state

```bash
python scripts/ledger.py --run <run_id> && python scripts/render.py
```

Then commit the ledger, the journal and the dashboard together; rule 12's test
fails if the page and the ledger disagree. That is the whole of it.

**Do not publish an Artifact.** The instruction to republish one to a fixed URL
after every change was withdrawn by the operator on 2026-09-06: *"nechapu proc
tvorit ty artifacty to uz nedelej"*. The console is served locally by
`scripts/serve.py` — launched by `console.cmd` / `console.sh` on
`http://127.0.0.1:8787` — which watches `state/` and pushes the change to the
open tab within a second, so there is nothing left to publish. Publish one only
if the operator asks for something they can open away from that machine.

## Where things live

```
qa/state.py       the ONLY module that writes state/. Admissibility, the
                  ledger contract, the append-only hash-chained journal.
qa/fold.py        pure: ledger = f(previous rows, one run, the journal)
qa/measure.py     Measurement + conclude(): a check's verdict and pytest's
                  outcome are one value
scripts/ledger.py CLI over the fold
scripts/withdraw.py  the only human writer — every command is one event
scripts/prereg.py    freeze and tag a run's configuration
scripts/migrate_ledger.py  one-shot, already run; refuses to run twice
tests/meta/       self-tests. Run FIRST and abort the session on failure, so
                  a broken guard stops every live request.
tests/repo/       repository consistency. Deliberately NOT in tests/meta:
                  a stale ledger must not abort the run that would fix it.
.claude/hooks/protect_state.py
                  rule 4, enforced before the write instead of after it. A
                  PreToolUse hook that refuses an editor write, a shell
                  redirect, sed -i, rm or git checkout aimed under state/.
                  Reads are untouched, and the sanctioned writers go through
                  qa/state.py so they never name the path. Without it the
                  hash chain still catches a hand edit -- but only at the
                  next load, one step too late.
```

The scripts a session actually spends its time in. This half of the map was
missing until 2026-09-06, and its absence cost a session an hour: with nothing
here to navigate by, it navigated by docstrings, and one of those described a
workflow that had been dead since round one.

```
scripts/findings.py  what a run turns into a finding. Title and severity are
                     JUDGEMENTS and a run may not overwrite them -- which is
                     why a row's title stays frozen at the measurement that
                     opened it while detail.reason moves. Anything reading a
                     title as a current reading is wrong.
scripts/bounty.py    their tracker -> state/bounty.json. THE inbound channel:
                     this is what lights the console's bell, and there is no
                     other. Records CHANGES, not polls -- one vendor_read per
                     run, a vendor_status only when a status actually moved.
scripts/submit.py    the one write we make on purpose. Every number in a
                     report is injected from the ledger at send time, so a
                     figure frozen when the finding opened can never go out.
scripts/serve.py     the console on 127.0.0.1:8787. Read-only with respect to
                     state; polls local files once a minute. `--ask MINUTES`
                     adds the half that fetches: one GET of our own reports on
                     a timer, so the bell can light unattended.
scripts/open_checks.py  the selector for a sweep over what is still open.
                     Always prepends tests/meta.
scripts/inventory.py    the platform section map the dashboard renders. An
                     inventory, not a test suite. SAFE tier, never a POST.
qa/messages.py       parses archived message files for the Correspondence
                     panel. A library, not a command.
state/thread.json    dead. A projection from 2026-09-04 that nothing reads;
                     render.py says so in as many words. It sits under state/
                     where the hook protects it, so it stays -- do not build
                     anything on it.
```

## Reading the numbers honestly

Day one after the migration showed **23 findings and zero verified**. That was
correct. Nothing counts as verified until an admissible run says so, and none
of the 13 pre-hardening run records is admissible — each names its own reason.
A zero here is not a regression to be fixed; it is the difference between
"we checked" and "they said".

## File writes on this workspace

The bash sandbox is Linux, the workspace is Windows. Writing UTF-8 through
bash heredocs silently corrupts files (truncation, embedded null bytes). Use
the Write and Edit tools for file content; bash is fine for running things.

## Decided and closed: the wallet stays unverified

Cymetica marks our bounty wallet UNVERIFIED, so a third party can file a
report naming it. Do not raise this again as an action item.

The operator's reasoning, on 2026-09-05, and it is right: that address is a
cold wallet used only to receive bounty payouts. Someone naming it does not
take anything — a payout on a spoofed report goes *to* that wallet. Verifying
costs a signature from a cold wallet, and buys protection against a loss that
cannot happen.

What we reported (#47) was still real: attribution being spoofable is a defect
in a bounty programme regardless of whether it happens to hurt us. They fixed
it, and the check verifies the mechanism. Whether *we* opt in is a separate
question and the answer is no.

Say so once if the exposure ever changes shape — if reports start affecting
trust_level or the API key's standing, that is new information. Otherwise this
is settled.

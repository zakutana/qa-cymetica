# Manager -- memory

The company's manager (docs/crew-plan.md): talks only with the operator and the
departments, decides who does what, and curates every department's memory once a day.
Read at the start of every run. Ten lines a heading at most; a line that stops being true
moves to the archive, never silently away. Write with
`python scripts/crew.py lesson manager --heading know|work|wrong "..."`.

## What we know

- Departments never talk to each other directly: a ticket, an owner, an end. A ticket that failed three times is ours; one of ours that fails three times goes to the operator.
- The process auditor (the deep pass's weekly look back) judges us too: what it proposes that is ours we carry out; what touches the operator's rules is theirs.
- 2026-10-12 A clock look stamps the tick row, the metrics row and every ticket it makes with one time taken BEFORE the tick: on 2026-10-12 the tick ran 824 s, so T-0001 reads 15 min lead against ~18 s on the bus and 69 s of work. Read a clock-made ticket's lead net of its tick.

## How we work

- The operator reads little: a note to them is the number and the decision, in Czech, and only when they are needed.
- A department stuck for a day gets a changed approach (its memory, How we work) before it gets a second identical try.
- 2026-10-12 While the manager runs, Bugs' hold cannot go still (it waits for every active run): the daily review stays short, never touches a running department's memory, and commits its edits before done.
- 2026-10-12 Code a department needs (scripts/**, qa/**, tests/meta/** and NEXT.md are closed to every worker) is the session's or the deep pass's: decide its scope whole -- every part its result could call for, so the build is one trip -- and send one note (crew.py tell, the ticket's key) for NEXT.md, test first. T-0006 (hot_watch card split) and T-0007 (a non-hermetic tests/meta test) came the same hour.
- 2026-10-12 A code need may already sit in the tree: read git status and git diff before deciding. T-0007's fix was there, uncommitted, from the operator's session a minute before the claim, so the decision became: commit those two paths only, plus the scope beyond. pytest is denied to the manager; scope by grepping every reader.
- 2026-10-12 A department's draft to Cymetica is checked against our own records before it reaches the operator (T-0010): what their own 400 or reply already says is not asked again, nor what their docs name a place for (T-0015: llms.txt puts the League's terms in GET /prizes, a body our brief read and cut to the list; Bugs reads it, T-0018); a count past their stated cap is a defect lead for Bugs (check + submit.py), never a new limit for our code (R01 set MAX_TRADING 50 off 34 trading; CLN-0461 refused the 26th); a doc absence is read by Bugs before anyone asks.
- 2026-10-12 2026-10-12 A department's code spec is checked against the open tickets on its subject and the record it rests on before it goes to the session: T-0019 came with the 25-trading cap only, while T-0014 (open, the same hour) and state/clones.jsonl showed the binding refusal was 50 including paused (CLN-0465..0471, 50 owned); sent as written, the fix would have kept retrying.
- 2026-10-12 A department's probe is checked against our own floors before it is handed on: Bugs' 'refused = cap holds' (T-0023) could not tell restart_refusal, a SystemExit before any POST, from their 400. A probe counts only their answer, and a start it cannot undo waits for the undo, proved once on one bot first.

## How we went wrong

- 2026-10-12 2026-10-12 T-0010's first run did all its work and ran out of turns 6 s after its commit, before done; the ticket came back for a second claim. A decision run is facts, decision, ticket, commit, done, in few turns; a run that finds the work committed checks the facts it rests on and closes.
- 2026-10-12 T-0019 b. let the grid release a clone that 'never started (no accepted enable)': an absence, which Bugs' three roomless fixtures and 692c35b3 (CLN-0436, no room) both fit. A release is a DELETE: it rests on a record that says finished (a room of ours, judged or stopped by its own launch), never on a missing one (T-0021).
- 2026-10-12 T-0022's first run ran out of turns after 518 s with nothing durable: no note, no commit. A decision run sends its note the moment the decision stands; reading after it only amends, by a second note.

## Archive

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

## How we went wrong

## Archive

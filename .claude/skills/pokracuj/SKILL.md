---
name: pokracuj
description: One loop tick in the laboratory. Works out where the last tick stopped and continues the exploration, without being told a session or a task. Invoked by "pokracuj v laborce" / "pokracuj" and by the /loop prompt the operator types unchanged every time.
model: claude-opus-5
---

# Pokračuj

[operator 2026-09-13] *"chci at je genericky ne ze v nem pisu lab-0004 chci
nejaky komand co budu pokazde stejny psat a ty sam si zrcis co jdes delat
proste zjistis kde jsi skoncil a pojracujes v pruzkuku"*

The prompt never changes and never names a session. **Work out where you
stopped. Do the most perishable thing. Say what happened in a few lines.**

The operator does not read long answers ([operator 2026-09-13], CLAUDE.md).
A tick that produces three paragraphs has failed even if the work was right.

## 1. Where did I stop

```bash
python scripts/lab.py resume
```

One call. It prints the open session, the last session's lessons and queue,
the rooms and their windows, the backtest register, and then **what to reach
for, most perishable first** — each item with the command and why it is due.

If it names no open session, open one: `python scripts/lab.py open --mode
session`. Never open a second one while one is open; the caps are per session
and a fresh session silently resets them.

## 2. Do the top item

Take the first item `resume` printed and do it. Then the next, if the tick has
room. The order is by what EXPIRES, and that is deliberate:

| | why it is first |
|---|---|
| a ripe memecoin checkpoint | the price that answers +6h is gone at +7h; the hole is permanent |
| a finding owed a level-V run | their fix is a claim until a run says otherwise (rule 7) |
| an open tournament round | free, weekly, and the picks come from Nexus not from us |
| the search | never urgent, never finished — the reason a quiet tick still works |

**A tick with nothing ripe is not a tick with nothing to do.** `due()` always
ends with the search for exactly that reason.

## 3. The rules that do not relax because it is a loop

Everything in CLAUDE.md holds, and three bite hardest here:

* **A bug found gets a check and a report, filed, without asking.** Not
  deferred to the morning, not collected.
* **A gap — something undocumented, something missing — is said in the
  answer, immediately**, so the operator can relay it. Not put in a commit
  message and not held for later.
* **Nothing that spends, sends or publishes** without the operator in that
  turn. Paper only, the caps in `qa/lab.py` are executable, and `scripts/
  lab.py` refuses rather than warns. Read the refusal; it is never arbitrary.

Strategies come from Nexus, never from us — the whole laboratory rests on it.
A basket the search measures well is a QUESTION for Nexus, not a proposal.

## 4. Say it in a few lines

The delta only: what moved, the number, and anything that needs them. If
nothing moved, one line saying so is the correct answer and a better one than
a paragraph explaining why.

Do not recap the tick. Do not restate the plan. Do not list what you decided
not to do.

## 5. When to stop the loop

Say so plainly if a tick finds the loop has nothing left worth spending on —
their API down, the caps reached, the register saturated. The operator stops
it; do not stop it silently by producing empty ticks.

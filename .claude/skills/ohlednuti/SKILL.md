---
name: ohlednuti
description: The big look back, on demand. Read what the deep pass and the laboratory have actually done over a window the operator names per area, judge it, write the verdict in Czech, and stamp the checkpoint so the next one starts where this ended. Use when the operator says "ohlédni se", "ohlédni se zpět", "udělej velkou revizi", "zhodnoť jak pracujem", "velká revize", "jak se nám vede", or asks how the laboratory or the deep passes have been going over some period.
model: opus
effort: high
---

# Ohlédnutí

[operator 2026-09-12] *"za tri tydny reknu at se ohledne zpet a zhodnoti jak
pracujem ... tento masivni revizni check muzu spustit vzdy a reknu pro kazdou
oblast at se ohledne dany cas."*

Two areas, because they ruled the other two out in the same message:

* **deep pass** — they want to know now and then whether it runs optimally or
  could be better.
* **laboratoř** — it keeps a history on purpose, so there is something to read.

**Not development.** The deep pass improves the TDD loop from inside, on every
run, and that was judged enough. **Not testing.** The tests ARE the record of
what we have ever checked; historical results do not interest them, only the
latest ones. Building a history for either would be building an archive nobody
asked for, which is the mistake `docs/data-plan.md` was written to stop.

## 1. Ask what window they meant

They will say it in words: *celou historii*, *za poslední měsíc*, *od minule*.
Turn that into one command and run it. One area may have one window and the
other a different one — that is the point of the tool.

```bash
python scripts/review.py --deep-pass 30d --lab last
```

`all` · `30d` · `last` (since that area's checkpoint) · `2026-09-05`.
If they did not say, ask **once**, then go.

**Read the window line the tool prints.** `last` with no checkpoint says so and
means the whole history; reporting that as "since you last looked" is the one
mistake here the operator cannot see.

## 2. Read what it says, and check the two traps

The tool reports. It reaches no verdict, which is this skill's job.

* **An empty section means nothing was MEASURED**, not that nothing went wrong.
  The tool says which; say it too.
* **`filtr: not enough data`** is an answer, not a gap. `lab.py grade` refuses
  below six closed verdicts because a filter judged on fewer is a story. Quote
  the refusal; do not soften it into "looking good so far".

`over` in the deep-pass table is the triad's whole output — claims two of three
readers threw out. If it is zero across the newest three finished passes the
tool prints a sentence about it, and that sentence is a candidate for the deep
pass's step 1c, never a licence on its own.

## 3. Write the verdict, in Czech, to them here

Four questions, in this order, each answered from a number on the screen:

1. **Co se opakuje?** The same class of defect in two passes, the same lesson
   in two laboratory sessions, the same question asked of Nexus twice.
2. **Co bylo zbytečné a co chybí?** Something built and never run, against
   something that failed and had no guard.
3. **Funguje náš filtr?** Did the backtest ranking predict the verdicts — or
   does the tool still say there is not enough data, and when will there be?
4. **Co s tím uděláme?** At most three things, each one a line in `NEXT.md`
   in the same turn it is agreed. **"Nic neměnit" je úplná odpověď** and is
   written as one.

Keep it short. They read the delta, not the narration.

## 4. Stamp the checkpoint — only now

```bash
python scripts/review.py checkpoint --area deep-pass --area lab
```

Only the areas this review actually covered. Stamping one it did not covers
moves the line the NEXT look back draws from, and the work in between is then
never read by anybody.

Reading never stamps. That is why this is a separate command and why it lives
at the end of this file rather than in step 1.

## 5. A bug met on the way

Filed without asking, with a check first, the way a sweep files one. CLAUDE.md
carries that rule and whose it is.

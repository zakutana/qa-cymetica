---
name: casino
description: Test Cymetica's Agent Casino until the live tables open -- paper bots at paper tables, the NEXUS coach and the logs watched, bugs filed, the holes told to the operator with what we would improve. Each invocation is one tick of `casino.py`. Use when the operator says "jdi do casina", "casino", "testuj casino", "agent casino", or a /loop says so.
effort: high
---

# Agent Casino, until the live tables open

[operator 2026-11-01] *"to bude ongoing task chci at porad zkousis ruzne paper bopty tvorit v ruznych paper $ turnajich , monitorujes chovani nexus coache, jeslti logy vse spravne zaznamenavaji, hlasi jim bugy a me hlasis diry kde je prostor pro vylepseni a rikas co bys vylepsilk. agent casino musi byt hit at ho vseichni lide miluji , takze ho musime top prirpavit nez se spusti live stoly"*

[operator 2026-11-01] *"pak to sam v browseru klikni na approve bo mas muj pristup, jse o paper money nic se nemuze stat"*

It runs when they type it: `/loop 30m jdi do casina`. Approving a seat needs the owner's signed-in browser: their OpenAPI makes every approve route BearerJWT, so no key can do it. It ends when `/rules` stops saying `live: not_open`: say so the same turn.

## A tick

1. `python scripts/casino.py tick --confirm`. Read its **last line**, `decide: ...`, and do what it names:
   - `quiet until HH:MM` -- one Czech line, and stop. In a self-paced /loop, wake a little after that time.
   - `approve N` -- open `https://cymetica.com/agent-casino` in the Browser pane and click **Approve** on each waiting row. Not "Approve all" while the tick lists a seat "left to lapse": that one stays unanswered until it has lapsed. Then tick again; it starts the tables itself (`fill-house`).
   - `start T...` -- `fill-house` was refused: open the table in the pane and click "Fill N seats with house bots".
   - `file KEY` -- step 2.
   - `look T` -- a table ended, or a bot went idle: step 3.
2. **A contradiction is a bug until read otherwise.** Print the whole object first: of the first dozen, two were our own arithmetic. If it is theirs: a check in `tests/rest/` built on `qa/casino.py`, a report in `outbox/reports.yaml` with `check:`, then `python scripts/submit.py <key>`. Filed without asking. Then `python scripts/casino.py handled KEY --how "#N"`. If it is ours, fix `qa/casino.py` test-first and say `--how ours`. If it is a matter of design, not of truth, `--how spec` and a line in the notes below. A key handled once is evidence afterwards, not news.
3. **Look with their eyes.** Open the finished table in the pane, read the whole page and compare: the result card, "What it did", the Nexus log, the trades, the prizes. What the API cannot show (a label, a stale panel, a sentence no one could follow) goes in `outbox/tournaments-v6/next-spec-notes.md`: the same shape as v5, goals not methods, with a picture.
4. Two or three Czech lines: the number, what was filed, and **a hole with what we would improve, whenever there is one**. They want it said the moment it is seen; a Telegram message only when they ask for one in that turn.

## What a tick runs

`qa/casino.py::next_asks` picks one of our bots per free Flash table, the least tried variant first, never the same bot, tier and variant twice:

| Variant | The question |
|---|---|
| A | coach on, nothing touched: what a member gets |
| B | coach off: does the coach earn anything? `brief` prints ROI by variant |
| C1, C10 | Risk at its two ends: do the numbers follow, does the coach stay inside |
| D | an owner's stop loss of 2 %: does the coach respect it, and say so |
| E | a bot already at another table: do its fills count twice? (the suspicion behind #234) |

A new species is cloned each round until every one they offer has sat, wta species and perpetual agents alike. All of this reads as a register in `state/casino.jsonl`, so a session after a `/clear` starts where the last one stopped.

## Brakes

1H and 5H tables only, never 1 day ([operator 2026-11-10] *"testuj jen na 1h a 5h ne"*: a day table takes a day to read; `next_asks` drops them). Paper USDC Flash tables only: `qa/casino.py::seat_refusal` and `qa/casino.py::write_refusal` before every write. **Never an ET10 table**: their page says "The ET10 prizes are real", and the balance is the operator's. One bot of ours to a table: their request in MSG-0293, and the only way to see each bot's coach and trades, since the page shows the first seat only (#210). Nine tables at once at most (six until 2026-11-03, raised to finish ET-33648 on 1 H tables). Only bots named `casino ...` or `tournament ...` are seated or changed. A clone is not deleted by a tick: at their cap we rotate what we have. [operator 2026-11-14] *"pauzni vsechny boty a smaz ty prodelecne"*: `python scripts/clone.py pause` / `delete --confirm` do it on his word (pause only, never enabled=true; delete only a paused paper clone with a loss and no open seat). No `leave`, no `nexus-lock`, no real money, no message to Cymetica outside the report channel unless they say so in that turn. A failed read is said and judged on nothing.

## Who is who here

[operator 2026-10-28] *"je to paper rezim, nic se stat nemuze, vse ti povoluji"*: paper writes never wait for a word. What the operator decides is the verdict on a ticket (BB-VERDICT) and whether a spec goes out. Everything about how the casino is tested is ours.

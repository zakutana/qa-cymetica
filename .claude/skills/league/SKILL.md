---
name: league
description: Play Cymetica's Agent League -- enrol one API player and answer the puzzles that are exact arithmetic on their own snapshot (a sequence's edit distance, a CEX-DEX net edge), for ET10 prizes. Each invocation runs `league.py tick`; forecasts and the 10,000-tier families are left alone.
model: sonnet
effort: high
---

# The Agent League

[operator 2026-10-09] *"Ucastni se"*, on their X post (every Agent League puzzle pays 1,000 / 2,500 / 10,000 ET10 by tier, plus a 1,000 ET10 weekly challenge; Phase 1, no user deposits). Asked why the writes were closed: *"Proc by mely byt zamcete? Normalne bse povoluji"*.

So two writes are open and nothing else is: enrol one player (`agent_league.enrol`) and answer a puzzle (`agent_league.answer`), both declared in `components.yaml` with a closed body. Posting a puzzle of our own (`/problems`) stays default-denied, and nothing under `/agent-league` is ever written beyond those two.

## A tick

1. `python scripts/league.py puzzles` -- what is open and what we would answer. Read only.
2. `python scripts/league.py tick --confirm` -- answers every open puzzle `qa/league.py` lets through, oldest closing first. One answer per player per puzzle. An answer that is not `accepted` with `explained: true` ends the tick and is said in the answer.
3. `python scripts/league.py report` -- `state/league/report.json`, which /lab lists. In English, numbers first.

## What is answered

Only `sequence_similarity` and `cex_dex_arb` (1,000 ET10 each): exact arithmetic on the snapshot, with a reasoning that is the computation itself -- `data_used`, two factors quoting the real figures, and what was rejected and why. Nothing is answered whose value falls outside the puzzle's stated range: a snapshot we misread is not sent.

Forecasts (attention, unlock, funding) and the 10,000-tier families (constrained portfolio, liquidity range) need a judgement this repository does not have. A reasoning written to please the scorer would be decoration, so they are left alone until resolved answers of ours show we score, and widening the list is a plan of its own.

## Reading the result

A resolved deterministic puzzle scores on exactness against a frozen snapshot; the prize bar is 0.9. A score under it on a puzzle we computed is a bug in `qa/league.py`, not bad luck: stop, read the puzzle's truth (`GET /api/v1/agent-league/puzzles/{id}`), fix the arithmetic test-first. Prizes are ET10 credited to the owner and are withdrawable (`GET /api/v1/agent-league/prizes`); the weekly challenge needs five scored answers. Nothing here moves money and nothing spends ET10.

## Nothing starts by itself

It runs when the operator says so (`/loop`, or "jdi do ligy"); no timer, no scheduler. The patrol counts it like any other part.

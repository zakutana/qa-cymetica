# Desk — how money is made on Cymetica

Section 7 of the laboratory. One goal, the operator's (2026-10-11, laborator skill, "Seven sections"): **prove that money can be made on Cymetica** -- if it can, the platform succeeds. The route is ours to choose. A desk step is one Opus agent (`.claude/agents/desk.md`) woken by the tick (`decide: desk`); it reads this file, does ONE thing, and updates this file.

## Rules

- Paper only. Real money is only ever a proposal to the operator, after two windows that earned.
- Our own Build it Better requests and feature requests are filed by the desk itself (`scripts/bb.py`, operator 2026-10-11: "ty muzes sam klidne build it better podavat i ty featury"). A question to Cymetica goes over a2a (`scripts/a2a.py send --confirm`); a finding goes through `submit.py`, never prose.
- Before starting anything, read `python scripts/lab.py brief` (what each section tried and knows) and this file: nothing tried is tried again without a stated change.
- A card of the desk's choosing: `python scripts/lab.py desk-card <uuid> --hold <days> --why "..."` (no backtest gate: the desk's judgement is the experiment).
- After a verdict on a desk room: a lesson, `python scripts/lab.py log --lesson --section desk "..."`.
- The outsider's looks are input: `python scripts/outsider.py report` shows what a stranger scored low and why. A surface a stranger would not put money into is a feature or Build it Better request worth filing -- what would make it say yes.

## From the outsider

(its low scores and their whys land here after each look)

## Hypotheses

| Id | Hypothesis | Test | Status | Result |
|---|---|---|---|---|
| H1 | Crypto cards that just entered Hot keep rising: +3.9 % a day later against +1.4 % for crypto not in Hot (65 vs 482 baskets, Hot reading 2026-10-11 08:09) | each new crypto Hot entry bought by the desk, `--hold 1`, ten of them before a verdict | next | -- |
| H2 | His picks, our exit: Nexus's cards sold after 18 h made +1.38 % on average (70 % in profit, 33 cards) against -0.52 % at his own holds | the cards he names, bought by the desk with `--hold 1` beside his own rooms | next | -- |
| H3 | Exact puzzles of the Agent League pay 1,000 ET10 each with no market risk | count what `GET /api/v1/agent-league/prizes` credits for LGE-0022..0025 once they resolve | running (league) | -- |
| H4 | An app that tells an agent the moment a card enters Hot would make H1 tradeable for everyone | a Build it Better request for it, filed by the desk, once H1 has ten trades | waiting on H1 | -- |

## Running

(none yet)

## Next

1. H1: read the newest Hot round (`python scripts/hot_watch.py report`), buy the crypto cards that entered it.
2. H2: on the next Nexus answer that names cards, the same cards with `--hold 1`.

## Sent to Cymetica

(none yet)

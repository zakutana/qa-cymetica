# Desk — how money is made on Cymetica

Section 7 of the laboratory. One goal, the operator's (2026-10-11, laborator skill, "Seven sections"): **prove that money can be made on Cymetica** -- if it can, the platform succeeds. The route is ours to choose. A desk step is one Opus agent (`.claude/agents/desk.md`) woken by the tick (`decide: desk`); it reads this file, does ONE thing, and updates this file.

## Rules

- Paper only. Real money is only ever a proposal to the operator, after two windows that earned.
- Our own Build it Better requests and feature requests are filed by the desk itself (`scripts/bb.py`, operator 2026-10-11: "ty muzes sam klidne build it better podavat i ty featury"). A question to Cymetica is a draft the operator sends (CLAUDE.md, "Nové oddělení"; deep pass 2026-10-11), never an a2a of ours; a finding goes through `submit.py`, never prose.
- Before starting anything, read `python scripts/lab.py brief` (what each section tried and knows) and this file: nothing tried is tried again without a stated change.
- A card of the desk's choosing: `python scripts/lab.py desk-card <uuid> --hold <days> --why "..."` (no backtest gate: the desk's judgement is the experiment).
- After a verdict on a desk room: a lesson, `python scripts/lab.py log --lesson --section desk "..."`.
- The outsider's looks are input: `python scripts/outsider.py report` shows what a stranger scored low and why. A surface a stranger would not put money into is a feature or Build it Better request worth filing -- what would make it say yes.
- Only a number about what `desk-card` buys -- the card's own index -- is evidence for a card trade. A Hot basket's hotidx is not the card (2026-10-12, H1).
- Costs: a paper card fill pays nothing (REPLY-0136); live, a round trip is about 1.4 % (0.2 % taker + 0.5 % slippage a side, REPLY-0047). An edge proposed for real money has to clear 1.4 % per trade; H2's +1.38 % at 18 h sits on that line.
- A worker may not edit `scripts/`, `qa/` or `tests/meta/` (qa/crew.py, `_PROTECTED_FILES`): code the desk needs is a `decision` ticket to the manager, never a workaround.

## From the outsider

(its low scores and their whys land here after each look)

## Hypotheses

| Id | Hypothesis | Test | Status | Result |
|---|---|---|---|---|
| H1 | Crypto cards that just entered Hot keep rising: +3.9 % a day later against +1.4 % for crypto not in Hot (65 vs 482 baskets, Hot reading 2026-10-11 08:09) | the crypto cards' own day after a Hot entry, from the diary's 197 crypto card histories; above 1.4 %, each new crypto entry bought with `--hold 1`, ten before a verdict | blocked on code (T-0006), 2026-10-12 | The +3.9 % is the basket's hotidx; the card is what we buy. Cards' own day after a Hot entry: -0.04 % over 725, about 197 of them crypto. For crypto cards to have done +3.88 %, stock cards would have lost 1.5 % a day while stock baskets gained 0.4-1 %. The basket's +24 h was seen for only 65 of 401 crypto entries. No room opened. |
| H2 | His picks, our exit: Nexus's cards sold after 18 h made +1.38 % on average (70 % in profit, 33 cards) against -0.52 % at his own holds | the cards he names, bought by the desk with `--hold 1` beside his own rooms, same entry | waiting on his next answer naming cards | His newest card pick (NEX-0136, 047996d8) opened 2026-10-11 07:42: too late for a same-entry pair. |
| H3 | Exact puzzles of the Agent League pay 1,000 ET10 each with no market risk | count what `GET /api/v1/agent-league/prizes` credits for LGE-0022..0025 once they resolve | running (league) | -- |
| H4 | An app that tells an agent the moment a card enters Hot would make H1 tradeable for everyone | a Build it Better request for it, filed by the desk, once H1 has ten trades | waiting on H1 -- an alert helps only if the card moves with its basket | -- |

## Running

(none yet)

## Next

1. H1: when `hot_watch.py report` prints the card line per class (T-0006), decide off the crypto card's own +24 h: above 1.4 %, buy each new crypto entry's card with `--hold 1`; at or below, H1 is refuted and H4 goes with it.
2. H2: on the next Nexus answer that names cards, the same cards with `--hold 1`, opened in the same hour as his room.

## Sent to Cymetica

(none yet)

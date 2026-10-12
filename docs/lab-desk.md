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
- A desk room holds its card for the lab too: his room on that card is refused while ours runs and for 30 days after our verdict (`qa/lab_register.py::last_judged`, any section). Beside a room of his means after it, never before.

## From the outsider

(its low scores and their whys land here after each look)

## Hypotheses

| Id | Hypothesis | Test | Status | Result |
|---|---|---|---|---|
| H1 | Crypto cards that just entered Hot keep rising: +3.9 % a day later against +1.4 % for crypto not in Hot (65 vs 482 baskets, Hot reading 2026-10-11 08:09) | the crypto cards' own day after a Hot entry, from the diary's 197 crypto card histories; above 1.4 %, each new crypto entry bought with `--hold 1`, ten before a verdict | blocked on code (T-0006), 2026-10-12 | The +3.9 % is the basket's hotidx; the card is what we buy. Cards' own day after a Hot entry: -0.04 % over 725, about 197 of them crypto. For crypto cards to have done +3.88 %, stock cards would have lost 1.5 % a day while stock baskets gained 0.4-1 %. The basket's +24 h was seen for only 65 of 401 crypto entries. No room opened. |
| H2 | His picks, our exit: Nexus's cards sold after 18 h made +1.38 % on average (70 % in profit, 33 cards) against -0.52 % at his own holds | the bull cards he names, bought by the desk with `--hold 1` within the hour of his answer (after his room when the lab opens one); the floor is 1 day, so 24 h, not 18; ten before a verdict | running, 2 of 10 (STR-0212, STR-0213), 2026-10-12 | NEX-0138 (16:54 UTC) named 3. ce0c9e32 he called bear for 18 h: desk-card buys bull only, and STR-0191 holds it bull since 10-10, so skipped. e22876b3 (AI Data-Center stocks) and 2a6f5562 (SAIB SPCX) the lab left unopened, his holds being under a day (about 6 h; to the next open), so no pair: the desk bought both at 17:27 UTC, 570.95 USDC each (TRD-0116, TRD-0117). Both trade US hours only; the 1-day exit carries the overnight gap he warned against. |
| H3 | Exact puzzles of the Agent League pay 1,000 ET10 each with no market risk | count what `GET /api/v1/agent-league/prizes` credits for LGE-0022..0025 once they resolve | waiting on the prize rule (T-0015), 2026-10-12 | Resolved over a day ago. Player 2: 28 sent, 26 scored at mean 0.9999, 1 prize record, 0 ET10 credited, Championship 0 points (`league.py brief`, 17:20 UTC). At 1,000 a puzzle that would be 26,000. What awards a prize is unread: a question drafted for the operator, carried by T-0015. |
| H4 | An app that tells an agent the moment a card enters Hot would make H1 tradeable for everyone | a Build it Better request for it, filed by the desk, once H1 has ten trades | waiting on H1 -- an alert helps only if the card moves with its basket | -- |

## Running

| Room | Card | Hold | Stake | Opened | For |
|---|---|---|---|---|---|
| STR-0212 | e22876b3 AI Data-Center & Compute Buildout | 1 d, bull | 570.95 USDC (TRD-0116) | 2026-10-12 17:27 UTC | H2 |
| STR-0213 | 2a6f5562 SAIB: SPCX (SpaceX) | 1 d, bull | 570.95 USDC (TRD-0117) | 2026-10-12 17:28 UTC | H2 |

## Next

1. H2: the verdicts of STR-0212 and STR-0213 (due from 2026-10-13 17:28 UTC), a lesson each; then every Nexus answer naming bull cards, bought with `--hold 1` within the hour.
2. H1: when `hot_watch.py report` prints the card line per class (T-0006), decide off the crypto card's own +24 h: above 1.4 %, buy each new crypto entry's card with `--hold 1`; at or below, H1 is refuted and H4 goes with it.
3. H3: on Cymetica's answer (T-0015). Every answer over the bar paid: count what is credited, and what an ET10 buys. Best answer only: a race, not risk-free money, and H3 is refuted as written.

## Sent to Cymetica

(none sent; drafted for the operator: 2026-10-12, the League's prize rule, T-0015)

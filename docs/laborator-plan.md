# Laboratoř jako produkt, systém bez ceremonií — plán v2, 2026-09-23

v1 (schválený ráno, fáze L0–L8) je v gitu. v2 ho nahrazuje po revizi celého
projektu (`docs/review-2026-09-23.md`): architekt došel k tomu, že návrh
vizi nesplňuje, a pět čtenářů našlo 38 vad. Operátor dal volnou ruku
k předělání čehokoli.

## Pro tebe

**Tvůj den**
- Jednou: založ session „Laborka" a vyber v ní model Sonnet.
- Ráno v ní napiš `/loop 20m jdi do laborky`, večer v hlavní session „jdu spát". Nic dalšího.
- Výsledky čteš na stránce Laboratoř. Připomenu ti jen tyhle věci, a když něco nesedí (třeba laborka jede na Opusu), napíšu jak to spravit.
- **Každé ráno v 7:00 hotový přehled:** krátce deep pass, pak stav laborky. Vždy na stejné adrese, otevřeš ho i z mobilu. K přehledu mi napiš, co chceš jinak. Zapíšu to do deníku laborky a v dalším přehledu uvidíš řádek, co jsem podle toho změnil.

**Co se mění**
- **Nejdřív opravím čísla,** podle kterých by ses rozhodoval o penězích. Verdikt pokusu bude z našich papírových pozic, ne z jejich indexu. Tam, kde dnes vychází „nedá se říct", prostě bude číslo.
- **Laborka je hlavní produkt.** Stránka Laboratoř: roomy Karty · Boti · Memecoiny · Fondy. U každého jen čistý výsledek po nákladech, počet pokusů a jak jisté to je. Neúspěchy jsou v archivu.
- **Pás bez našich stropů.** AI se probudí jen když je co rozhodnout (otázka pro Nexuse, jeho odpověď, díra k nahlášení). Klidné kolo stojí jeden krátký řádek.
- **Boti:** všechny druhy a jejich nastavení na papíře.
- **Memecoiny:** poctivá odpověď na „10 $ do každého hot signálu".
- **Systém se zmenší.**
  - Pravidla pro mě (CLAUDE.md) na třetinu.
  - Jeden hook při startu místo šesti, rychlý a krátký.
  - Deep pass jen tak velký, jak velké byly změny dne.
  - NEXT.md nejvýš 10 řádků, hotové dokumenty pryč.
- **Údržba, která opravdu dojde:** připomínka se ukáže vždy a paměti se čtou celé, ne jen titulky.
- **Nové oddělení** (propagační centrum) má jeden tvar a test hlídá, že se napojí samo.

**Proč tomu věřit:**
- každá fáze má „hotovo, když" s testy;
- každý nález ověřili tři nezávislí rozhodčí;
- každou noc deep pass nad změnami;
- díl jádra se přečte celý, když se v něm hodně změnilo, nebo jednou za měsíc;
- na konci nezávislý audit celého plánu.

---

## Pro implementaci (číst nemusíš)

### What the review established
See `docs/review-2026-09-23.md`. The architect's target, adopted here:
- **A department is one shape:** skill + `scripts/<d>.py` (tick · brief · report) + `state/<d>*.jsonl` + `state/<d>/report.json`; everything else discovers it by glob.
- **The lab tick ends in `decide: none | question | answer NEX-… | gap`.** Only the last three cost an LLM turn.
- **The verdict comes from our paper book;** their index is secondary, used for marks.
- **One local `/lab` page,** served, not committed.
- **Collectors live on serve.py's timers,** which only read.
- **The deep pass is sized by the diff.**
- **Ceilings:** CLAUDE.md ≤ 300 lines, one SessionStart hook, NEXT.md ≤ 10 open lines, tests/meta grows only by replacement.

The findings, as triage confirms them, are the work of V1, V2, V7 and V8. A finding triage rejects is dropped with its reason recorded in the review file.

### Decisions pinned verbatim (unchanged from v1)
In `.claude/skills/laborator/SKILL.md`, pins 1–4 of v1: manager and technicians; impact data and product rooms; Nexus mainly, our ideas too, no limits, failures archived; memecoin data must hold and "$10 into every hot signal" must be executable. In CLAUDE.md, pins 5–6: never think about it, reminders welcome; the future inherits all of it. The quotes are in git at 1e43a1ef:docs/laborator-plan.md. PINNED rows go in the same commit. No existing pin is edited; the 2026-09-10 pin stays, and the 2026-09-23 one narrows it. When they land: pins 1–4 in V1's first commit; pins 5–6 in V7, once CLAUDE.md has room under its 750-line ceiling; pin 7 in V11.

### Phases

| Fáze | Co | Hotovo, když | Stav |
|---|---|---|---|
| V0 | Úklid a záznamy dne | MSG-0045 zapsaná; archiv zabalený a na OneDrive se stejným hashem; 460 MB worktrees pryč; revize v repu | hotovo 3db2de5d |
| V1 | Kritické opravy (před 26. 9. 00:52 UTC) | B1, C1, C3, A1, D1 mají každá test pojmenovaný po incidentu a jsou zelené | hotovo ce8a0b1e |
| V2 | Poctivá čísla laborky | verdikt z naší knihy; Bollinger ≈ +3 %; NEX-0064 na desce +4,17 %; NEX-0080 → 1 volba; zastavený bez pozice = archiv | hotovo dcac9077 |
| V3 | Memecoiny poctivě | report řekne „10 $ do každého hot signálu = X % po nákladech, n, stihli bychom Y %"; srovnání s kontrolou po tokenech a bez přepnutých párů | hotovo be97cb6d |
| V4 | Laboratoř jako oddělení + stránka /lab | screenshot 2000 px viděný; commitnutá stránka nemá žádný vstup mimo git (test); poznámka ze stránky dojde do `rooms.py unread`; **jeden room na odvětví a operátor stránku viděl a dal ≥ 9/10** | hotovo de9b43b7 — operátor 23. 9.: „nová lab je perfektní“ (a6037069 dostala 3/10) |
| V5 | Pás a boti | tik spustí variantu bota s jiným nastavením přes bránu papíru; jediný limit je 60 % knihy; odpověď se čte jednou | hotovo 4af17a57 (s 11685b1e, 1028c377, 59cde5f2, 4ac9694b, d0609c5e, 3a07a9f4); po prvním dni smyčky ověřit řádky `answer_read` |
| V6 | Manažer za pár tokenů | klidné kolo = 1 krátký tah AI; den smyčky ≤ 20 tahů AI při stejném počtu spuštění | hotovo 1b8e6ac4; po prvním dni smyčky ověřit `processes.py loop`: pracovních kol ≤ 20, klidné ≤ 4 volání, model Sonnet |
| V7 | Údržba, která dojde | start session ≤ 8 řádků za ≤ 3 s; `memories.py --for lab` ≤ 8 KB celé; MEMORY.md v limitu harnessu; CLAUDE.md ≤ 300 ř.; NEXT.md ≤ 10 otevřených | hotovo 0e2406c9 (s 127f969b, 1a2ee286, 566e85fb, 2ce72f21, 3aee1398): start 7 řádků za 1 s, `--for lab` 7,9 KB, MEMORY.md 48 ř. / 10 KB, CLAUDE.md 198 ř., NEXT.md 9 otevřených |
| V8 | Jádro QA | každý potvrzený nález A/B/D má test; `/code-review` přes fold/state prošel | otevřená |
| V9 | Oddělení do budoucna | testovací oddělení (skill + skript + deník) se objeví v hlídce, archivu a na /lab bez jediné úpravy | otevřená |
| V10 | Závěrečný audit | nezávislý audit plánu proti repu; každé „hotovo, když" pravdivé | otevřená |
| V11 | Ranní přehled v 7:00 (jde hned po V4) | v 7:00 je na stejné adrese nová verze: deep pass ≤ 3 řádky, laborka po roomech, co se změnilo přes noc, co dnes udělám; screenshot z mobilu i desktopu viděný; poznámka k přehledu se v dalším přehledu ukáže jako provedená změna | postaveno b9a79e8a, první verze na https://claude.ai/artifact/GuKb2rfBC1hxeDrUDtVXkL; čeká na první ranní vydání a pohled z mobilu (publikovaná stránka chce přihlášení, ten screenshot může udělat jen operátor) |

Order: V1 V2 V3 V4 V11 V5 V6 V7 V8 V9 V10. V11 follows V4 directly because the morning report is what the operator sees first.

Each phase: tests first (red), then code, `pytest tests/meta tests/repo`, commit on `main`, no push. A NEXT.md line is written when a phase starts, and the row gets `hotovo <hash>` when it ends. The first line of each phase session states class · needs · running. `get_usage` is read before each phase.

### Phase details

**V1 · Kritické opravy** (Opus · high; before 2026-09-26 00:52 UTC)
- **B1:** PROBE judges inertness from the whole request — query string, form or non-JSON body, and MCP `{}` arguments on non-read tools — so `toggle-trading?enabled=true` is refused. Test first in the existing gate tests; the 2026-09-22 RC1 test is the pattern. *Done 5f5f5d6b: the query string and the body are read; the MCP `{}` half stays, triage found it deliberate 3/3 (the anonymous authorization probe).*
- **C1:** a failed benchmark or card-history read is `unread`, not `[]`. The verdict waits (rule 8) and is re-judged on the next tick; it is never written without its benchmark.
- **C3:** a normal window close sells the room's card positions (the early path already does). It has already fired: STR-0003's TRD-0006 is still open, and it is closed in the same change. The next case is STR-0006. *Done 40ea9e2e: TRD-0006 had already resolved on their side on 2026-09-19 (+85.76 USDC), so there was nothing left to sell; a position their record shows closed is no longer sold again.*
- **A1:** `ledger.py --run` refuses a run older than the ledger's newest adjudicating run unless it is named `--replay`. `/code-review` (fold/state). *Done f0af8234, in `scripts/ledger.py` alone: fold/state/measure are untouched, so CLAUDE.md's review trigger did not fire.*
- **D1:** `prune_runs.py` never deletes a capture the manifest knows that no verified bundle holds, and it prints how many it held back. The deep pass's step 0 stops the prune when the archive fails.

**V2 · Poctivá čísla laborky** (Opus · high)
- **Verdict = our paper book.** Realized + unrealized P&L from our positions, net of fees, against the BTC proxy over the same window. Their index history is used for marks (funds) and as a cross-check. The formula fingerprint moves; old verdicts keep theirs.
  - *Design, 2026-09-23:* a paper position is worth `units × current_index` (their sample: 0.02164 × 231.30 = 5.0064, to the cent), so a card leg's book IS their index rebased on OUR entry: 100 at the buy (`entry_index` from the buy's own response), `100 × index / entry_index` at every index point after it, and after our close (or their resolution) the realised value `100 × (1 + realised / notional)` at the close. The path stays dense because it is their history; the entry and the exit are ours. The live round trip (`GATE["round_trip_cost_pct"]`, 1.4 %) is charged once on a card or fund leg's return in `verdict` -- the path, the drawdown and his TP/SL (index-level, as NEX-0065 says) stay gross. A bot is as they book it, from its funding. A card leg with no position of ours falls back to the index. The index-only return rides beside as `index_return_pct`, the cross-check.
- Bot leg enters at funding (the Bollinger fixture: +2.96 %). Nexus's TP/SL go into the plan legs before `set_acceptance`, forward only.
- Status first:
  - stopped without a position → `archived`, no verdict;
  - stopped with one → judged up to the stop.
  - STR-0008 is closed with its reason.
- Parked money in paused bots is counted apart from active money.
- C2: `board` reads realized P&L from our close records.
- C4: n_eff on time-aligned returns.
- C7: picks are read only from pick lines, tested against the real answers in `nexus.jsonl`. C8: drawdown from the peak. C9: `_next_id` taken under the lock.
- Bot stop cause is one of three: ours, their guard, or unexplained. An unexplained stop gets a check + report. A stopped bot is never re-enabled.
  - *Done 9f141b82, except the report:* Bollinger Bandit (36642175) halted at +7.11 on 240.18 with no reason anywhere -- their settings are PATCH-only (no read-back), my-clones has no reason field, /activity no halt event, and their docs describe no automatic halt at all. The Telegram line went to the operator on 2026-09-23; the check and the report are a NEXT.md line, because the contract to hold has to be their documented one, not Nexus's NEX-0049.
- `board`/`brief` include bots and funds. clones.jsonl leaves git via a `keep.py` subcommand.

**V3 · Memecoiny poctivě** (Opus · high)
- Headline = `stop_study()` at a $10 clip: no stop, 24 h hold, pair-clean, swap fee per side with sensitivity at 0.5/1/2 %.
- Depth at entry decides the buy; depth at exit caps the sell. Split the test at L553 and keep its case-blind half.
- C5: `compare()` counts per token, pair-clean, over the same period for both groups, with an honest interval.
- C6 is a minority finding (1 of 3), so it is examined but not assumed: whether dropping unobserved time exits biases the hot-headline sample.
- `RADAR_FIELDS` += price_usd, first_buy_seconds_ago, exit_signal, exit_reason, updated_at.
- Fill share = `max_buy_5pct_usd` against $10, plus first-checkpoint latency.
- The pinned quotes (fomo.py:260/466/489) stay verbatim.
- Out-of-sample rule: a pattern is dated and judged only on data after its date.
- *Remaining (NEXT.md):* `fomo.sellable` judges a coin by its NEWEST depth (look-ahead), but switching to the depth at the signal alone moved the stop study from −11.7 % to +85 917 % -- it lands only together with the sell cap at exit depth in every reader (`stop_study`, `stats`, basket), as `ten_dollars` already does. Then split the L553 test; C6; the out-of-sample rule. `stop_study` and `compare` still drop the pair switches, which are rugs (measured 2026-09-23) and so losses; `ten_dollars` counts them.

**V4 · Laboratoř jako oddělení + /lab** (Sonnet · high)
- `lab.py report` → `state/lab/report.json`: per product, net %, n, Wilson band, running, best, archived count; plus a Nexus hit-rate line (questions → picks → gate → survived).
- serve.py serves `/lab` from it, and the page is not committed.
- The Nexus and Memecoiny tabs, `build_rooms` and the `fomo`/`nexus` payload inputs are removed from render.py. The committed page then hashes nothing outside git (the D2 half those inputs cause). render.py:4931's quote is re-pinned where the memecoin room now lives, same hash.
- The collectors (fomo, hot, sampler) run on serve.py's timers (reads only), and the tick stops its own fomo round, leaving one writer.
- `console.cmd --fomo 1` only after this, together with new-signal horizons 0.25/1/4/24 h, a quote cap per round, and bulky captures pruned after 1 day.
- Tests first: the tests that pin the old tabs are rewritten, and a both-ways field guard is added for `report.json`.
- *Remaining (NEXT.md):* the new horizons are stored ON the signal, not in the global `HORIZONS_HOURS` -- otherwise old signals lose their checkpoints.
- *Done 0f63c4cf + a6037069, except the `--fomo 1` bullet, which is a NEXT.md line. One deviation, decided: the tick keeps its fomo/hot/sample doors and skips exactly the rounds the console's `/status` says it runs -- dropping them outright would lose checkpoints on any night the console is closed (scripts/lab.py said so when it took the sampler over).*

**V5 · Pás a boti** (Opus · high)
- Our caps go: questions/day, rooms/day, running_experiments, the 20-min spacing, IN_FLIGHT_HOURS.
- Theirs stay: OUTSTANDING_BOUND 6, ASKS_PER_HOUR 3, backoff, and `pass_in_flight`.
- Stake = a fixed share of the book, so 60 % exposure is the only count limit. Answers are read once.
- `clone.py settings()` gets the paper floor before it exists (the `enable()` check). B7 was dropped only because nothing calls the PATCH yet, and this phase adds the caller. components.yaml declares only safe fields (no arb, custodial or onchain). Each variant is a new room, and a PATCH is refused while its room runs.
- Grid per species: SL / TP / max_position / max_open_positions / min_ai_confidence / market toggles.
- *2026-09-23, REPLY-0049:* one active paper clone per species per account (a second is 409 ALREADY_CLONED; several is a feature ask they logged). So a species' variants run one after another on its one clone, never side by side, and the grid is walked in time.
- Own lane under the 2026-09-23 pin:
  - origin `OUR-…`, labelled „naše";
  - each also asked to Nexus;
  - never ranked above his picks;
  - correlated rooms count as one.
- *Done, three commits:* 11685b1e `clone.py settings()` -- the body carries only `SAFE_SETTINGS` (the grid's fields; no `is_trading`, arb, on-chain share or market lists), our record says the instance is a paper clone of ours, no room of ours runs on it, their row says paper twice; the transport's new `closed_body` refuses any undeclared field at MUTATE, and components.yaml declares exactly the grid. 1028c377 our caps gone, each replaced in a comment by the brake that covers it (60 % of the book at a fixed 0.48 % a room, ASKS_PER_HOUR, OUTSTANDING_BOUND, backoff, `pass_in_flight`). 59cde5f2 an answer is read once; only one with a pick still waiting is read again.
- *The variant launcher, which is what the done-when names (done, see below):*
  1. `qa.lab.next_variant(tried)`: the grid per species, one factor at a time from their baseline (SL, TP, max_position, max_open_positions, min_ai_confidence, the four market toggles), deterministic, walked in time on the species' one clone.
  2. A tick door: for a clone of ours whose rooms are all stopped, the next variant opens a NEW room, PATCHes through `clone.settings()` (the gate above) and starts it; the 60 % check counts the clone's parked money becoming exposure.
  3. `clone.enable()` narrowed: a started clone may start again only as a new variant -- our own accepted pause, then an accepted settings PATCH after it, and no room running on it. A halt by their guard or an unexplained one stays never restarted (V2).
  4. The own lane: `rooms.open_strategy` accepts an `OUR-NNNN` origin without a Nexus answer, labelled „naše"; `brief` lists each running one as a question for him; the board ranks them after his; a species' variants are one at a time, so they count as one.
  5. A variant's verdict starts at its restart: `bot_series` measures from total funding, so a reused clone would carry the previous variant's P&L. The enable intent already records `bot_balance_usdc` at the start.
- *Done, three more commits:* 4ac9694b `clone.restart_refusal` -- a clone that ran starts again only after our accepted pause, then an accepted settings change, with no room running on it, and never after a halt that was not ours; the enable intent records `bot_profit_usdc`. d0609c5e `qa.lab.variants()`/`next_variant`: every body carries the WHOLE grid (a reference with one factor moved) because a PATCH cannot unset a field and a fresh clone's SL/TP/max_position/confidence are null (CLN-0018), so a moved factor would leak into every later variant; the reference is their default wherever they have one, ours inside their bounds where theirs is unset; the catalog toggle stays off (it trades only a watchlist). OUR-NNNN proposals in the notebook, `open_strategy` from one on record, `restart_affordable` (parked money becoming exposure, 60 % of the book, not the 2 % per-order cap), `bot_restart` + `bot_series(entry_profit=)`. 3a07a9f4 the tick's `variants` door after the verdicts; the board and /lab rank ours after his, /lab says „naše", `brief` lists each running one as a question for him. 4af17a57, from review: a settled room pauses only a clone it still owns (the variant's start is not its bot "still trading"), and the Nexus line on /lab counts his rooms' verdicts only. Correlated rooms count as one by construction: a species' variants run one at a time on one clone, so they are one exposure at any moment; the report's sector n still counts each judged variant.
  - And verify after the loop's first day that `answer_read` rows appear in `state/lab.jsonl`: an answer is not marked read while their bot or fund catalogue is unread (`_bot_catalogue`/`_fund_catalogue` return None on any non-200 or reshaped body), so a chronically unread catalogue would quietly keep the old re-reading.

**V6 · Manažer za pár tokenů** (Sonnet · high)
- The tick's last line is `decide: none | question | answer NEX-… | gap`. On `none` the skill writes one line and stops, with no brief, no diary and no memory read.
- `laborator/SKILL.md` ≤ 100 lines, pins verbatim; "What we know about Nexus" moves into `lab.py brief`.
- The reminder names `/model sonnet` when the transcripts show the loop ran on Opus.
- An idle bug hunt runs only in the normal budget mode, with one Sonnet agent at most.
- `clone.py`/`paper.py`/`hot_watch.py` are added to the allowlist; paper-only stays enforced in code.
- *Done 1b8e6ac4.* The done-when as written could not be met: at 20-minute firings a day is 72 firings, so it is read as **working firings** (the tick decided something) **≤ 20 a day while the tick still runs on every firing**, and a quiet firing is the tick in the background plus one line -- two short turns, because ticks take 2-13 min and a foreground one was killed at the tool's ten minutes (2026-09-22). Measured before: 2026-09-21, 49 firings, 342 calls, all Opus. `qa.lab.decide` replayed over the 160 stored ticks says `none` on 100 (`may_ask` alone woke the manager on 97) and 8-22 working ticks a day, fewer firings since a question and its answer share one. A question is due on news (a verdict, a resolved position) or every 2 h within their pace; a hunt every 8 h, the first of a local night the sweep, only under 85 % of both windows (`lab.py budget`). Skill 400 → 89 lines, pins at their hashes; the patrol holds it at 100.

**V7 · Údržba, která dojde** (Sonnet · high)
- **One SessionStart hook,** ≤ 8 lines in ≤ 3 s: what is due · threads · notes · NEXT. There is no surface scan in the hook; drift is computed by the tick and the pass and cached (E1). The two hook quotes are re-pinned at the new path, same hash.
- **Memories:**
  - `memories.py --for` prints complete bodies ≤ 8 KB, ranked by relevance (E2);
  - MEMORY.md stays under the harness's load limit (200 lines / 25 000 characters): retired lines move to `MEMORY-retired.md`. This is prevention, not a fix: E3 was dropped as a forecast.
- **Patrol:**
  - counts slash commands and `.md` preregistrations;
  - an idle flag only where a part can leave a record (E4).
- **A pass that died** says so at the next session start. Its real, unfixed gaps are carried forward by the next step 0 (E5).
- **Step-1 readers:** drop `/loop` noise and say when they truncate (E6). Rename the processes.jsonl field (E8).
- **CLAUDE.md ≤ 300 lines:** the file maps go to `ARCHITECTURE.md`, which is rewritten as the current map. NEXT.md ≤ 10 open lines of ≤ 300 characters. DEEP-PASS.md ≤ 10 lines.
- **Deep pass sized by the diff:**
  - full: state/fold/measure, a check or vendor-facing code changed, or ≥ 15 commits;
  - light: Sonnet triad otherwise;
  - minimal: at ≥ 85 % weekly use.
  - It lands in the 1c form.
- **Triggered re-read:** an area is read whole after ≥ 15 commits or 30 days.
- **tests/meta** grows only by replacement.
- **Deleted:** the finished plans in docs/, the stray `f`, the dead `night_running` reminder.
- *Done, 2026-09-23, one commit per slice:* 127f969b NEXT.md 9 open lines of ≤ 300 characters (the detail moved into this plan under V3/V4/V8). 1a2ee286 `memories.py --for` prints whole bodies to 8 KB, most specific first (lab 28 → 7.9 KB); retired lines in `MEMORY-retired.md`, the index 48 lines / 10 KB. 566e85fb one SessionStart hook, `.claude/hooks/session_start.py`: fixed slots, 7 lines in 1.0 s; the surface drift cached by the patrol and the tick. 2ce72f21 CLAUDE.md 750 → 198 lines, pins 5 and 6 landed, the maps now `ARCHITECTURE.md` §0 (the current map; §1–§9 stay the reading of 2026-09-20, not re-read). The deep-pass slice went through 1c in rounds: the first two drafts were voted down 3/3 each (vendor-facing scripts and the guards themselves called light; a minimal pass still sending verifications, leaving a dirty tree, silencing the "pass owed" reminder and failing its own guard; the morning report's headings dropped; the operator's items hidden by the ten lines or the one-line slot; a dead pass's deferred and minority gaps shown nowhere), all fixed before the next round. **Two deviations, decided:** (1) the plan said "light: Sonnet triad otherwise", expecting light to be the common case; the readers showed that tests, audits, hooks and every script are guards or talk to their platform, so light covers prose only (`LIGHT_SAFE`), lowers only the code review's effort, and keeps the Opus triad (step 4 also judges the audit, the carried gaps and the whole readings, none of which come from the diff); most passes stay full. (2) "minimal at ≥ 85 %" became **deferred**: the pass does not run at all, because every version of a pass that finished without reviewing had a hole (it could push, verify, silence the "pass owed" reminder or fail its own guard). The saving is in not running on a spent week and in the whole reading being scheduled rather than nightly. Of the finished plans, `UPGRADE-PLAN.md` and `lab-plan.md` went; `data-plan.md` and `nexus-rooms-plan.md` stay, because nine files of code cite them as the reason for their shape. R10 (the deep pass's minority report) decided: the reminder says the session runs the command.

**V8 · Jádro QA** (Opus · high, `/code-review`)
- The confirmed A, B and D findings not already fixed in V1 or V4: A2–A8, B2–B6, D3, D6. D5 is a minority finding and is examined only.
- Since V7 `tests/meta` grows only by replacement (the patrol's `meta_tests` ceiling is 800, 786 on 2026-09-23): a finding's test goes into an existing test where one already drives that path, or into tests/repo, and a new meta guard replaces or merges one.
- `vendor_read` is journaled only when a read's health changes (ok→fail, fail→ok); status changes are kept. This keeps rule 8 and removes the "console poll" commits.
- *Progress (a line per landed finding, so a compacted loop knows where it is):* A6 done (protect_state walks the command: cd, absolute and /c/ redirects, Python writes). A8 done by recording, not by a new formula: every result carries `helpers_fingerprint` beside the unchanged `check_fingerprint` (a new formula would have moved every row to CHECK_CHANGED), and verify.py says "the same test" only when the helpers match the failure's -- otherwise "the same recorded definition", or that a helper changed. The `correction_owed` half is still open.
- The fingerprint covers the module helpers a check calls (A8). Today `verify.py` says "the same test, not a rewritten one" after a helper was rewritten (#119, #113, #89, #121, #116; #120 was pinned by hand for that reason): fix the fingerprint or the sentence. And no `correction_owed` for a check that judges our own writes from before their fix (#117, #119).

**V9 · Oddělení do budoucna** (Sonnet · high)
- The department shape, plus one fixture-department test.
- CLAUDE.md "Nové oddělení", ≤ 8 lines.
- Outward writes stay denied by default. A tweet is a draft the operator posts.

**V11 · Ranní přehled v 7:00** (Sonnet · high; runs right after V4, which it depends on for `report.json`)
- **Pin 7,** in `.claude/skills/laborator/SKILL.md`, verbatim: *"jo a jeste chci pridat do planu ze kazde rano chci vygenerovany krasny vecny strucny artifakt o tom co se vnoci udalo v laborce. takovy top prehled chapes. Na ktery ti dam pak feedback, jako manageorvi laborky a ty udelas podle nej patricne upravy a tak. Tento artikaft chci mit pripraven vzdy v 7 hodin rano. Bude tam strucna sekce o deep passu jak probihal a pak na stav laborky."*
  - It narrows the 2026-09-06 "no artifacts" decision for this one report. CLAUDE.md's own sentence "Do not publish an Artifact." gains the exception on the same line; the pinned quote under it is untouched.
- **No new scheduler.**
  - The lab `/loop` runs overnight anyway, and its first tick at or after 06:40 local returns `decide: report`.
  - If no tick ran, the next session start says the report is missing and makes it at once.
  - This respects the 2026-09-12 and 09-14 decisions: the loop is theirs.
- **Content:** one short page, impact only, Czech. Published to one fixed artifact URL, updated in place; artifact-design skill first.
  1. Deep pass: fixed / sent / needs you, ≤ 3 lines, from DEEP-PASS.md.
  2. Lab: KPI strip; per product room, net % after costs, n and confidence; what changed overnight; Nexus in one line; what the manager does today.
  3. A ready Telegram block when something needs Cymetica.
  4. "Podle tvé zpětné vazby: …".
- **Feedback loop:**
  - The operator's feedback, in chat or as comments on the artifact (`ArtifactComments`), goes into the lab notebook as `lab.py log --feedback`.
  - The manager acts on it, and the next report names what changed because of it.
  - Feedback is kept for the week's look back, so a repeated wish becomes a rule rather than a daily correction.

**V10 · Závěrečný audit** (Opus · high)
- One independent agent reads this plan against the repository; any false done-when reopens its row.

### Not doing
- No scheduler or cron. No timer that trades: serve.py's timers only read.
- No real money.
- Run records stay in git (rule 12 needs the cited ones).
- The listing checks keep their captures.
- No standing AI technician.
- The channels and pokracuj skills stay, because they carry pinned decisions. a2a.py stays dormant.

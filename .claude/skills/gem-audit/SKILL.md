---
name: gem-audit
description: Audit the Gem Screener as a degen who means to lean on its numbers in an altseason, and say every place that looks wrong or that they would be afraid to trust. Runs the whole procedure again on any day -- the script, the core checks, the browser pass, the report. Use when the operator says /gem-audit, "audit gem screeneru", "zkontroluj gem screener", "muzeme se na nej spolehnout", or asks whether the app and its data can be trusted.
model: sonnet
effort: high
---

# Gem Screener audit

[operator 2026-09-30] *"projdi celou apku z pohledu degena co se na ni a jeji data chce 100% spolehnou v pristim altseasonu a rekni vsechna mista kde bys ji vylepsil nebo se ti nezdaji data a bojis se jim verit"* -- and, straight after, *"tvor i testy at to muzes cely proies kdykoliv pak zopakovat. gem screener musi byt spickovy produkt spolehlivy"*, then *"ikdyz ne testy moc neprehanej, bo oni budou vlastne delat upravy co navrhnem, testy mzues udelatr na core prvky co myslis ze se nebudou menit uz"* -- Cymetica will be changing the rest on our suggestions.

So the audit is four parts, and only the first two are code:

| Part | Where | What it holds |
|---|---|---|
| the judgements | `qa/gemaudit.py` | pure functions over the page's own snapshot and over what the sources say |
| the core checks | `tests/rest/test_gem_screener_*.py` | what a redesign will not change: the numbers equal their sources, a pick opens the coin it names, the upside and altseason follow their own rules, every derived figure follows its own definition, the run-rate uses the multiplier its page states |
| the procedure | `scripts/gem_audit.py tick` | reads everything, recomputes the derived figures and (for the shortlist and the top by upside) the revenue figures from DefiLlama's daily series, writes `state/gem_audit/latest.md`, says what moved since the last tick |
| the browser pass | this file | what a script cannot see |

Read-only throughout. Nothing is sent, filed or drafted to Cymetica from here: a
finding goes through the sweep (a check, a run, `submit.py`), a wish becomes a
line for the next Build it Better request, a gap in their docs is said to the
operator the moment it is seen.

## The spine

0. **Memories.** `python scripts/memories.py --for sweep`, and one that belongs to
   this work: *a ticker is not an identity* (two apps share EDGE; a dict keyed by
   symbol once turned one of them into the other and produced a contradiction that
   did not exist). Key by `key`, never by `symbol`.

1. **The tick.**
   ```
   python scripts/gem_audit.py tick
   ```
   It prints a line per column and, under "moved since the last tick", what changed.
   `python scripts/gem_audit.py report` prints the tables again; `brief` says how old
   the last tick is. A source that did not answer is named under "not read" and its
   section is absent -- never treat a missing section as agreement.

   The two questions it answers are different and should not be mixed: *is each
   figure the source's figure* (copies: supply, price, revenue, pool liquidity) and
   *is each derived figure the function it says it is* (P/S, earnings, slippage,
   the gates, the run-rate, six-month growth). Neither says whether the rank predicts
   anything -- that is their own backtest's question, and it reads "inconclusive".
   What it could not reproduce from their published definition (Strength 3M's
   revenue factor, the trajectory quarters' normalisation) is a documentation gap to
   tell the operator, not a defect to file.

2. **The core checks**, under a preregistration like any other run:
   ```
   python scripts/prereg.py new --selector "tests/meta tests/rest/test_gem_screener_numbers_match_their_sources.py tests/rest/test_gem_screener_picks_and_formulas_are_self_consistent.py" --window 30 --tag
   python -m pytest <the nodeids prereg echoes> --prereg PRE-NNNN -q --no-header --tb=no
   python scripts/ledger.py --run <run_id>
   ```
   A red row is a finding: **check whose bug it is first** (CoinGecko re-estimated a
   supply, a snapshot was stale, a third party was down -- none of those is theirs),
   then file it by the sweep's rules, without asking.

3. **The browser pass.** Open `https://cymetica.com/gem-screener/app` (the app, not
   the wrapper page). What only a page can tell, and what to read:
   * the default view of the Apps tab -- which of *Vetted only / Degen picks / All by
     upside* is on, and how many rows it shows;
   * Top Picks: is the backtest verdict visible without a click
     (`#startBt summary`), and what does it say when opened (`#startVerdict`)?
   * the Altseason panel: its headline number and each sentence under "Expand",
     against `altseason_cycle` in the snapshot -- a sentence that quotes the 4-week
     mean as if it were the latest reading is a label, not a number, problem;
   * each pick's card: does it carry the "Watch out" line its exit flag implies,
     and does the link on the card open the pick itself (`?coin=` for a shared
     ticker);
   * Sectors and Chains: how many themes carry "Hot now" (`themes[].hot`), what
     "Talked about" says, and the activity-fee guards on Chains;
   * loading: one cold load, then the same again (`performance.getEntriesByType`).
   Write what was seen with its number. Do not click "Ask for Degen report": it
   starts a research job on their side.

4. **The report.** `outbox/gem-screener-degen-audit.md`, rewritten from this tick's
   tables with the narrative kept short and numbers first. Two buckets at the end,
   one line each:
   * **Defects** -- a shown number wrong, the page against the API, stale shown as
     fresh with nothing marking it. Each becomes a check and a report by the sweep.
   * **Improvements** -- goals, not methods, as lines for the operator's next Build
     it Better request. Wishes are not filed.

## What the audit is not

It does not judge their scoring. The finding that the rank has no predictive skill
is **their own** (`backtest_summary`), and the audit reports it as theirs. It does
not re-derive what they derive unless the derivation is published and could be
checked. It does not check all 215 coins by hand: the columns are whole-population
comparisons, and a single coin is named only when it is a pick.

## Hard-won

* **A ticker is not an identity.** INDEX, MET, EDGE and UP are each two apps. Read
  the shortlist from `degen.shortlist` (keys), and compare a pick with its coin by
  name and market cap, not by symbol.
* **A column is judged as a population.** One coin 40 % off is the world or a source
  correcting itself; a moved median is a pipeline. The thresholds sit above what the
  live data showed and say so.
* **A snapshot older than twelve hours measures drift.** Such a run is inconclusive,
  not a finding; the refresh having stalled is a different check's business.
* **Third parties through `build_source_client` only.** Never `rest_trusted` for a
  host that is not theirs: a key must not leave.
* **Read the definition before writing "contradicts".** `revenue` here is DefiLlama's
  protocol revenue, `ps` is market cap over a run-rate, `upside` is the benchmark's
  multiple over `ps`. Two fields on one card are a contradiction only in the same unit.

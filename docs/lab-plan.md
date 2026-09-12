# Laboratoř, DNA a data pod kontrolou — plán schválený 12. 9. 2026

Plán, který operátor schválil 12. 9. v 7:48. Nezávisle ho ověřili dva recenzenti
(Fable 5.1 a Opus 5, oba na max) a jejich připomínky jsou zapracované.

## Tři věci, o které jde

1. **Data pod kontrolou.** GitHub 54 MB, `evidence/` 469 MB a 40–170 MB denně;
   11. 9. udělaly dvě kontroly procházející výpis karet 120 MB ze 170. Do gitu
   půjde jen to, co něco cituje (~120 MB, už tam je); zbytek žije na disku tři dny.
2. **Připomínky místo plánovačů.** Nic se nespouští samo (rozhodnutí operátora,
   CLAUDE.md). Hook při startu session řekne, co je na řadě a jakým povelem; session
   ten řádek zopakuje v první odpovědi.
3. **Laboratoř s Nexusem a hlídka nad každou součástí.** Jeden povel „jdi do
   laboratoře"; Nexus vede, my měříme. Hlídka najde každou součást sama a deep
   pass její čísla čte denně, týden je porovnává.

## Co musíme držet navždy

| důvod | přibližně |
|---|---|
| jejich odpovědi, na kterých stojí ledger | 211 souborů, 15 MB |
| evidence, kterou citují naše odeslané verdikty, reporty a paper obchody | ~700 souborů, ~105 MB |

Vendorovi v každém verdiktu píšeme, že ji na požádání vydáme (`scripts/verify.py`),
takže se maže jen to, co necituje nic. **Žádný strop u zdroje** — zahodil by právě
tu stránku, kterou slibujeme. **Žádná databáze** — držela by stejné bajty; problém
byl kde (git navždy) a jak dlouho. **Historie se nepřepisuje** — rozbila by
preregistrace i commity, které verdikty vendorovi citovaly.

## Fáze

Každá: testy napřed (červené), pak kód, pak commit na `main`, bez pushe.
Stav se aktualizuje tady; dokud je fáze otevřená, má řádek v `NEXT.md`.

| # | Co | Hotovo, když | Stav |
|---|---|---|---|
| F1 | Data: `evidence/` do `.gitignore`; sledovač citované evidence volaný z `.githooks/pre-commit`, z foldu a z deep passu; seznam ztrát (23 id z migrace 4. 9.); prořez evidence v `prune_runs.py` (3 dny od posledního citujícího běhu, navždy-množina, nejnovější odpověď každého volání — u MCP podle nástroje); `tests/meta/test_pipeline_secrets.py`; `git rm --cached` zbytku; záloha deníků laboratoře do `audits/lab/` | `git ls-files evidence` ≈ 900 souborů, ne 7 747; po sweepu a pollu konzole nic nového necitovaného v gitu; `evidence/` po prořezu ~0,5 GB | **hotovo `9b4de3cc`** — 6 737 souborů z gitu, 4 814 z disku, 172 MB; zbývá 1 010 v gitu a 290 MB na disku |
| F2 | Připomínky: `processes.py reminders` (vypadlá noc, týden, laboratoř, plán), hook `.claude/hooks/reminders.py` (offline), pravidlo v CLAUDE.md; deep pass: `at_finished`, krok 1 čte zprávy od minulého běhu, krok 0 „jen týden" | čerstvá session vypíše správné připomínky a session je zopakuje | **hotovo `5d1ca7aa`** — tři pravidla, každé s fixture v obou směrech; laboratorní přibudou ve F4 |
| F3 | Hlídka: `processes.py` nad skilly, agenty, skripty a hooky; `--extract` do `audits/processes.jsonl`; `--flags` se stropy nad dnešní úrovní; skóre deep passu a sweepu; deep pass kroky 1, 1b, 11; `Effort:` pro oba tvary commitu; sekce DNA v CLAUDE.md | `processes.py` vypíše každou součást s běhy, chybami a posledním během | **hotovo `fcb1aa22`** — 40 součástí, stropy nad dnešní úrovní, zapojení hooků hlídané staticky |
| F4 | Laboratoř v1: `list_backtest_surfaces` a `get_backtest_models` do `mcp_tools.read`; `scripts/lab.py` (`status`, `truth`, `cycle`, `ask`, `buy`, `open`, `close`); `state/lab.jsonl`; skill `laborator` (z `nexus-session`); „Co víme o Nexusovi"; porovnání katalogu se snímkem `audits/nexus-baseline.json` | „jdi do laboratoře" projde celou smyčkou i s mrtvým Nexusem; další session vidí poučení a frontu | **hotovo `1a314f00`** — a první `truth` našla nález, podaný jako #97 (`371cc548`, `9a5363d9`) |
| F5 | Experimenty: změřit hloubku jejich historie indexu; `set_claim`, `set_acceptance`, `record_verdict`, `running` jen s kritériem; `lab.py adopt`; verdikt jako čistá funkce s otiskem vzorce | po převzetí STR-0003 `lab.py status` ukáže okno, výnos, DD, BTC a pokrytí | **hotovo `ec577053`** — kritérium předem, verdikt z jejich historie indexu, oba rozjeté roomy převzaté |
| F6 | Konzole: verdikt v roomu, tabulka výsledků v General | screenshot v 2000 px, opravdu viděný | **hotovo `6b483385`** — a screenshot našel, co testy nevidí: věta „when the window closes" v místě pro číslo se ořízla; teď tam stojí, za jak dlouho verdikt padne |
| F7 | Noc laboratoře: `lab.py night --until HH:MM` — jeden proces na povel operátora, v danou hodinu skončí, jen zkoumá | noc zapsaná, sondy ≥ 2 h od sebe, ráno ji `lab.py status` shrne | **hotovo `41a0a5e8`** — hodina se čte na tvých hodinách (ne UTC) a přes 14 h se odmítne; noc nemá ruku, která obchoduje, zakládá nebo commituje, a test to čte z jejího zdroje |

## Druhý plán (12. 9. odpoledne): hledat strategie backtesty

Schválen po dvou tvých námitkách, obě oprávněné: *„dyt jsem jasne na zacaktu
rikal ze se v laboratori ma vest denik at vi co uz se testovalo"* a *„system ma
byt self imprived… jak je mozne ze by sis toho nevsim?"*

Co se změnilo v zadání: jejich `backtest_event_card_idea` bere **libovolný koš
2–20 symbolů** s vahami a **explicitní okno** (7/30/90/180/365), limit 30/min.
Sampler už ten tvar zapisuje. Vesmír tedy není šest konceptů, ale kombinatorický.
Backtest je ale **buy-and-hold koše** — ne strategie s TP/SL — takže je to
seřaďovač kandidátů, ne důkaz.

**Pravidlo, které to drží pohromadě:** změřit cokoli je zadarmo a vždy dovolené;
cesta z „backtest to našel" do „jde to do paperu" ale vede **přes otázku
Nexusovi**. Room otevře až jeho odpověď (CLAUDE.md: naše strategie se nikdy
nestane roomem).

| # | Co | Hotovo, když | Stav |
|---|---|---|---|
| N0 | Hlídka nad **jejich** stranou: schémata nástrojů do snímku „před", `lab.py surface` porovnává parametry, tvar jejich odpovědí z captures, připomínka + `processes.py surface --update` | přejmenovaný parametr i nové pole se ohlásí při startu session | **hotovo `fbf40615`** — a k tomu druhý vzorek čistoty stromu na konci běhu, protože `git_dirty` se bral jen na startu |
| N1 | Rejstřík zkoušeného: `qa/backtests.py`, `state/backtests.jsonl`, otisk koše, stárnutí podle okna | stejný koš v jiném pořadí = stejný otisk; zapsané se nevolá znovu | **hotovo `6b76d164`** — a při tom se našla a opravila vada konzole: odmítnutí se ke klientovi nedostalo |
| N2 | Volání jejich backtestu: `lab.py backtest` na SAFE, koše ze sampleru, 30/min, chybějící symbol ≠ nula, evidence jen u povýšených | první volání vrátí čísla a zapíše otisk; druhé stejné neproběhne | otevřeno |
| N3 | Hledání: semínka z karet a Nexusových plánů, tahy přes okna a váhy, pořadí podle Sharpe a DD; lepší než semínko jde Nexusovi jako otázka | okolí semínka deterministické; hledání nedosáhne na `buy` ani `open_strategy` | otevřeno |
| N4 | Noc přestavěná na dvoje hodiny: backtesty souvisle, otázky když je na co; stropy 50 experimentů / 2 % / 60 % expozice | noc s mrtvým Nexusem udělá tisíce backtestů a nic netestuje dvakrát | otevřeno |
| N5 | Sebehodnocení: `lab.py grade` — předpověděl náš žebříček verdikt? Pod hranicí dat řekne „málo dat" | n = 2 → „málo dat"; po 17. a 19. 9. řekne číslo | otevřeno |

## Laboratoř: smyčka

`status` → `rooms.py unread` → `cycle` (dotáhne odpovědi, vzorky, TP/SL, verdikty)
→ `truth` (backtesty, pořadí podle Sharpe a max DD) → otázka Nexusovi na pozadí
(s tabulkou, jak dopadly jeho minulé návrhy) → room jen z konkrétní odpovědi, plán,
jeho čísla doslova, **kritérium předem**, paper obchod → `close` (≤ 3 poučení,
fronta „příště", česká poznámka do roomů).

Brzdy v kódu: jen paper; ≤ 8 otázek a ≤ 3 nové roomy za session; ≤ 6 běžících
experimentů, každý ≤ 15 % volných peněz; žádná otázka ani nákup, když běží deep
pass (měří kontroly #85, #86 a #87 nad jejími odpověďmi a obchody).

## Co tam schválně nebude

- Naplánované úlohy, `/loop`, ani nic, co se spustí samo.
- Live obchod. Naše vlastní strategie (nápad jde Nexusovi jako otázka).
- Obchody a zakládání nálezů v noci — noc zkoumá, ráno se jedná.
- Tlačítko obchodu v prohlížeči.

## Ověření

`pytest tests/meta tests/repo` po každé fázi; `git ls-files evidence` a
`du -sh evidence` po F1; čerstvá session pro připomínky; `processes.py` pro hlídku;
`lab.py truth` a „jdi do laboratoře" pro laboratoř; screenshot konzole v 2000 px.

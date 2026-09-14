# Next

Co jsme se domluvili, že je další krok. Ne to, o čem má rozhodnout operátor —
to patří do `DEEP-PASS.md` pod *Čeká na tebe*. Sem jde jenom práce, která je
už rozhodnutá a ještě není udělaná.

`.claude/hooks/next_step.py` z toho na začátku každé session vypíše jeden
řádek na položku. Nic víc; důvod a kontext se čtou odsud, až se někdo zeptá.

Formát je závazný, protože ho čte hook i test:

```
- [ ] YYYY-MM-DD  věta, co se má udělat
- [x] YYYY-MM-DD  hotová položka zůstává, jen se přestane vypisovat
```

Hotové položky se nemažou. Smazaný záznam o tom, co jsme se rozhodli, je přesně
ta chyba, kterou dneska ráno naučil `outbox/reports.yaml`. Co je otevřené déle
než čtrnáct dní, shodí `tests/repo/test_next_step.py` — buď se to stalo a nikdo
to neodškrtl, nebo to nikdy nebylo další na řadě.

---

- [x] 2026-09-10  Naklonovat Hybrid 2 (Blue) v paper režimu — bota, kterého Nexus sám doporučil (+19,86 % backtest, Sharpe 2,79, max DD 1,75 %)
- [x] 2026-09-10  Doměřit Nexus kanál na větším vzorku, než z něj uděláme závěr pro Cymeticu
- [x] 2026-09-10  Obě hromadící kontroly soudit v přítomném čase, ne přes celý log
- [x] 2026-09-10  Jeden 1 USDC paper obchod po jejich opravě, jako měření
- [x] 2026-09-10  Korekce na #85 přes `verify.py`, ne prózou
- [x] 2026-09-10  Klonovací pravidlo ve `components.yaml` míří na cestu, která neexistuje
- [x] 2026-09-10  Až jim pojede web chat, dát operátorovi větu pro Nexus a zapsat, na co se zeptal — kontrola pro jejich CEO
- [x] 2026-09-10  Naklonovaného bota nejde spustit — napsat na to kontrolu a založit nález
- [x] 2026-09-10  Klon nejde nabít agentním klíčem — #89
- [x] 2026-09-14  Až bude v deníku den hloubky, přidat do košíku P&L jen přes páry nad prahem `liquidity_usd` (bez toho drží headline pár, co nešel prodat)
- [ ] 2026-09-10  Zjistit, jestli je 401 na `/fund` záměr, a podle toho #89 upravit
- [ ] 2026-09-10  Změřit, jestli se odměna připíše při resolve karty
- [ ] 2026-09-11  Přečíst `docs/night-2026-09-11.md` — co se stalo v noci, čtyři nové nálezy a tři naše vlastní vady
- [x] 2026-09-11  Zjistit, jestli naklonovaný bot vůbec obchoduje
- [ ] 2026-09-11  Rozhodnout, co s `QUERY_RESTRICTED` u Nexuse
- [ ] 2026-09-11  Dvě z Nexusových vlastních priorit jsme odmítli otestovat
- [ ] 2026-09-11  Fold nedluží pass po failu pod stejným otiskem — #85 tak zůstal u nich s naším posledním `fail`
- [ ] 2026-09-10  Dát `nexus.py` způsob, jak zapsat odpověď, která nepřišla naším kanálem
- [x] 2026-09-11  Postavit Nexus rooms podle `docs/nexus-rooms-plan.md` — P1 až P5, každá fáze zvlášť
- [ ] 2026-09-11  Až Nexus zase odpovídá, zeptat se ho v STR-0001, co bylo na Perceptron Oracle špatně a jestli ho nechat běžet, nebo nahradit
- [ ] 2026-09-11  Až Nexus zase odpovídá, pustit znovu session s Nexusem na nové strategie z karet podle zpráv
- [ ] 2026-09-11  `correction_owed` ve foldu přičítá jejich tvrzení o opravě i našemu novému reportu na stejném řádku
- [x] 2026-09-12  F1 z `docs/lab-plan.md`: evidence mimo git — držet jen citovanou, prořez po 3 dnech, sledovač při commitu, test maskování klíčů
- [x] 2026-09-12  F2 z `docs/lab-plan.md`: připomínky místo plánovačů — hook při startu session, pravidla v `processes.py`, `at_finished` a zprávy od minulého běhu v deep passu
- [x] 2026-09-12  F3 z `docs/lab-plan.md`: hlídka `processes.py` nad všemi součástmi, `--flags`, a sekce DNA v CLAUDE.md
- [x] 2026-09-12  F4 z `docs/lab-plan.md`: laboratoř v1 — `lab.py`, skill `laborator`, pravda z backtestů, porovnání katalogu se snímkem
- [x] 2026-09-12  F5 z `docs/lab-plan.md`: experimenty — kritérium předem, verdikt z jejich historie indexu, převzetí rozjetých roomů
- [x] 2026-09-12  F6 z `docs/lab-plan.md`: konzole — verdikt v roomu a tabulka výsledků v General
- [x] 2026-09-12  F7 z `docs/lab-plan.md`: noc laboratoře — `lab.py night --until`, jen zkoumání, ráno konec
- [x] 2026-09-12  N2 z `docs/lab-plan.md`: `lab.py backtest` — volat jejich backtest přes rejstřík, 30/min, evidence jen u povýšených
- [x] 2026-09-12  N3 z `docs/lab-plan.md`: hledání — semínka z karet a Nexusových plánů, okolí přes okna a váhy
- [x] 2026-09-12  N4 z `docs/lab-plan.md`: noc na dvoje hodiny a stropy experimentů 50 / 2 % / 60 %
- [x] 2026-09-12  N5 z `docs/lab-plan.md`: `lab.py grade` — předpověděl náš žebříček verdikt?
- [x] 2026-09-12  Prořez nemá odmítnutí na prázdný keep-set, které `keepset.untrackable` má: `_ledger_as_written` je schválně shovívavý, takže nečitelný ledger dá `must_keep() == {}` bez výjimky a `prune_runs --apply` pak smaže citované captures. Reprodukováno v tempu: zdravý ledger → 0 obětí, useknutý → 2 citované mezi oběťmi.
- [ ] 2026-09-12  `review.py` čte deníky comprehension s `json.loads` uvnitř, takže **jeden half-written řádek vynuluje celý soubor** — 26 otázek Nexusovi spadne na 0 a nic to neřekne. `qa/lab.py:83` to dělá správně (`continue` na jednom řádku).
- [ ] 2026-09-12  Kontrola tajemství v `test_evidence_in_git.py` po D3 čte **nula souborů** a hlásí „passed" — sledovaných captures už není žádná. Nezávislá kontrola nad 3 663 těly na disku a 1 178 v archivu je čistá, takže je to rozbitý strážce, ne únik.
- [ ] 2026-09-12  `keep.py archive` nemá spouštěč: deep pass volá `track` a `snapshot`, archiv nikdy. Balík tedy zůstane snímkem 12. 9., zatímco nové řádky manifestu přibývají s `archive: ""`.
- [ ] 2026-09-12  Hlídka povrchu mlčí u **prvního** spatření volání — a jediné nebaselinované je `backtest_event_card_idea`, na kterém stojí celé noční hledání. Souvisí: `scripts/lab.py` jmenuje v docstringu `backtest_cited`, funkci, která neexistuje, takže hledání nezachytává evidence vůbec.
- [ ] 2026-09-12  `call_key` bere do klíče id zdrojů (report id, UUID karet), takže `audits/surface.json` roste v gitu navždy — 58 ze 135 klíčů, ~3 kB na kartu. Sbírání klíčů podle datového klíče už pro JSON mapy umí, na segmenty URL se nepoužilo.
- [x] 2026-09-12  CLAUDE.md je přesně na stropu 700 řádků (`>`, tedy nula rezervy). Příští přidaný řádek shodí `test_no_ceiling_is_set_below_where_we_already_stand` — buď prořezat, nebo rozhodnout, že strop má jít nahoru.  — strop zvednut na 750 dne 2026-09-13 (commit 5e2dd808)
- [x] 2026-09-12  Postavit `N_eff` z NEX-0026: průměrná párová korelace otevřené knihy jako varování dřív než drawdown. Nexusův vlastní ukazatel, ne náš nápad.  — postaveno 2026-09-13, qa/lab.py::n_eff a scripts/lab.py::book_correlation
- [ ] 2026-09-12  `_deployed()` v `scripts/lab.py` počítá i pozice, které simulace už nemá: TRD-0001 a TRD-0002 (11:41 a 11:59) jsou starší než `sim_started_at` 13:31, a `sim_total_trades` je 4, ne 6. Dnes jsou to 2 USDC z 99 000, ale každý reset simulace přidá další duchy, kteří se nikdy nezavřou, a ti nafukují čitatele stropu expozice. Ignorovat přijaté nákupy starší než nejnovější `sim_started_at`, s testem.
- [ ] 2026-09-12  `ledger.py` bez `--run` vzal jako běh záznamu můj vlastní běh `tests/meta tests/repo` — ten neměřil z jejich platformy nic, a protože stránka popisuje běh, ze kterého byl ledger složen, vyprázdnily se dlaždice sekcí. Stavy řádků to neohrozilo (fold nezavírá, co neproběhlo), ale strážce `test_a_tile_lists_the_tests_behind_its_count` prošel před tím o **jedinou** kontrolu (1 → 0). Default by měl preferovat běh, který něco z ledgeru rozsoudil, nebo aspoň odmítnout, když nerozsoudil nic.
- [ ] 2026-09-12  Ověřit #98 a #99 během úrovně V: zaplatili obě a tvrdí opravu, naše kontroly je pořád reprodukují — fold hlásí `reverify` a `correction_owed` u obou
- [x] 2026-09-12  D1 z `docs/data-plan.md`: manifest `audits/evidence-manifest.jsonl` — hash, bajty, `call_key`, důvod, archiv
- [x] 2026-09-12  D2 z `docs/data-plan.md`: `keep.py archive --month` — zabalit těla, ověřit hash každého, teprve pak pustit z gitu
- [x] 2026-09-12  D3 z `docs/data-plan.md`: odpojit `evidence/` od gitu; strom ze 229 MB na ~62 MB
- [x] 2026-09-12  R1 z `docs/data-plan.md`: `scripts/review.py` — okno a oblast deep pass
- [x] 2026-09-12  R2 z `docs/data-plan.md`: oblast laboratoř, `checkpoint --area`, skill, přepis kroku 11 deep passu
- [x] 2026-09-12  Hlášky strážce v `tests/repo/test_deep_pass_process.py` staví na klíči `pass`, ale `passes()` vydává `run` — ve chvíli, kdy má strážce vysvětlit, co je špatně, spadne na `KeyError`. Aserce samotné jsou správné, slepá je jen hláška.
- [ ] 2026-09-13  `verify.py` má pro `correction_owed` jen hlavičku „this corrects the record" — když se pohnul jen otisk a verdikt zůstal `fail`, je ta věta nepravdivá a zpráva se proto neodeslala. Chce třetí hlavičku; `qa/fold.py` + `scripts/verify.py`, test první a `/code-review`.
- [ ] 2026-09-12  Přeformulovat důvod v `test_one_credential_carries_a_clone_from_creation_to_funding`: větu o `/fund` říkat jen když `/fund` je mezi odmítajícími (šla ven v #98 jako podmíněná). Až se ta kontrola bude měnit tak jako tak — samotný pin cyklus za to nestojí.
- [ ] 2026-09-12  Rozšířit `SOURCES` v `test_pipeline_decisions.py`: 27 odstavců `[operator ...]` leží v 18 souborech mimo `CLAUDE.md` a `*/SKILL.md`, takže je dnes nehlídá nic. Noční pass na ten test sahat nesmí — je to práce na den.
- [ ] 2026-09-12  `audits/checks.json` zůstal po dnešním auditu neorazítkovaný, protože orazítkovat teď by znamenalo označit za auditované i definice, které pass v noci změnil. Příští audit tedy projde stejný rozsah znovu — stojí to tokeny, ale nezakryje to nález.
- [ ] 2026-09-12  `verify.py` spadne celý, když `already_sent()` nepřečte report (jejich TLS timeout ve 20:55). Čtení před POSTem, takže nic neodešlo napůl — ale jeden neúspěšný read zabije i verdikty, které by prošly.
- [x] 2026-09-12  #91 je nerozhodnutelný, protože nejnovější Nexusova odpověď jmenující kartu je starší než 24 h. Fold kvůli tomu dluží `repair_check` — až Nexus zase odpovídá, jedna otázka to vyřeší.  — NEX-0027 přišla 2026-09-13, #91 ověřen jako opravený a pass odeslán
- [ ] 2026-09-12  Pravidlo 12 zčervená po každém commitu s testem i po každém deep passu — render do `.githooks/pre-commit`, a `stats.process` k tomu navíc

  `payload_hash` kryje `stats.tests` (počty testů v repu) i `stats.process`
  (řádky passů z gitu), takže stránka zastarává i bez změny stavu. Dnes byla
  na `main` červená od 23:04 (render) do 23:15 (notebook passu) a pass ji tak
  pushnul; jeho krok 9 to chytit nemůže, ověřuje dřív než dopíše poslední
  commit. Render trvá 1,6 s, takže hook vedle `keep.py track`, stejně
  nefatálně. Ten ale spraví jen `stats.tests`: `versions()` čte
  `git log -- audits/deep-pass-progress.json` a commit v letu tam ještě není,
  takže chce navíc překrýt nejnovější verzi pracovním stromem (nebo dopsat
  notebook dřív, než se rendruje). Test první. Dnes přerendrováno.

- [ ] 2026-09-12  Krok 3 deep passu (code review) nemá v SKILL.md pokyn zapsat nález do notebooku, jak ho má krok 2 — takže když kompakce přijde mezi krokem 3 a 4, celá recenze zmizí beze stopy. Přesně se to dnes stalo: notebook má 27 tvrzení a všech 27 je z auditu. Oprava je změna páteře, takže chce vlastní tři čtenáře podle 1c.

- [x] 2026-09-13  `house_row()`, docstring `test_enter_still_needs_allow_mutate` a `test_one_card_is_not_bought_once_per_answer` — tři pozdní nálezy (M05, M06, M07), všechny tři dotriádované 2 ze 3 jako reálné a opravené ještě v tom samém passu. Hotovo 13. 9.

- [ ] 2026-09-13  Heredoc hook odmítá commit message, která sama cituje zápis do souboru: větev pro python tělo neověřuje, že ten heredoc vůbec python spouští, takže `git commit -F - <<EOF` se zprávou obsahující `p.write_text(...)` a cestu do repa je `deny`. Změřeno dnes večer a nezávisle potvrzeno dvěma čtenáři (2 z 33 commitů v transkriptech). Oprava je jedna podmínka na hlavu příkazu, stejného tvaru jako `SHELL_FED` — ale je to změna hooku, takže chce vlastní tři čtenáře podle 1c. Do té doby: `git commit -F <soubor>`.

- [ ] 2026-09-13  `qa/fomo.py::stats` vrací stejný token v `top` i `bottom`, když je tokenů mezi 6 a 10 (`ranked[:5]` a `ranked[-5:]` se překrývají). Živé na 7h horizontu. Konzole to nekreslí (od `df5bf7af` staví z `fm.curves`), takže se to k operátorovi nedostane — ale je to rozpor s vlastním komentářem té funkce a její test to nevidí, protože fixture má dva tokeny a `bottom` je prázdný. Minority report z 13. 9., jeden hlas ze tří.

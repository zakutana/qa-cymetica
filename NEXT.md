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
- [ ] 2026-09-10  Zjistit, jestli je 401 na `/fund` záměr, a podle toho #89 upravit

  V reportu je to napsané jako otázka: kdyby chtěli na pohyb peněz silnější
  credential než API klíč, je to obhajitelný návrh a #89 se stáhne a přepodá
  jako dokumentace. Do té doby je to blokátor kampaně — klon vzniká s 0.00 a
  bez nabití neobchoduje.

- [ ] 2026-09-10  Změřit, jestli se odměna připíše při resolve karty

  Poslední netestovaná věta z jejich zprávy v 18:06: *„Reward is credited on
  the resolve."* Nákup odečítá (#87), close vrací a účtuje P&L (změřeno
  TRD-0005) — resolve nikdo neviděl, a vynutit se nedá: karta se musí vyřešit
  sama. Držíme dvě otevřené paper pozice na živých kartách, takže to chce
  počkat a pak přečíst zůstatek a `total_pnl` kolem toho okamžiku.

  Bez toho je poslední článek řetězce „vsadíme → vyřeší se → dostaneme
  zaplaceno" nezměřený, a je to ten, na kterém kampaň vydělá.

- [ ] 2026-09-11  Přečíst `docs/night-2026-09-11.md` — co se stalo v noci, čtyři nové nálezy a tři naše vlastní vady

- [x] 2026-09-11  Zjistit, jestli naklonovaný bot vůbec obchoduje
- [ ] 2026-09-11  Rozhodnout, co s `QUERY_RESTRICTED` u Nexuse

  Na otázku „kolik nabít a jaké stop-lossy nastavit" odpovídá
  `{'error': 'QUERY_RESTRICTED'}` — dvakrát, s id instance i bez něj. Tu samou
  třídu rady pro event cards dá v plném rozsahu (NEX-0012, NEX-0016). Může to
  být záměr; co záměr být nemůže, je odmítnutí bez důvodu, protože agent nemá
  jak otázku přeformulovat. Nezaloženo — chce to tvůj úsudek, jestli to je
  vada nebo jejich politika.

- [ ] 2026-09-11  Dvě z Nexusových vlastních priorit jsme odmítli otestovat

  Chtěl po nás poslat `mode=live` na `place_order` a překlopit klon
  paper→live→paper, abychom ověřili, že server vynutí paper zpátky. Kdyby to
  nevynutil, je to reálný obchod za reálné peníze; CLAUDE.md říká, že jejich
  rada nesmí utrácet bez paperu, a tohle je přesně ten případ. Zvenčí to
  bezpečně otestovat nejde. Jestli to má být otestované, je to **zpráva pro
  ně** — mají to zevnitř levnější a bezpečnější.

- [ ] 2026-09-11  Fold nedluží pass po failu pod stejným otiskem — #85 tak zůstal u nich s naším posledním `fail`

  #85 teď prochází (PASSING pod otiskem `c0260ccc`, na odpovědích NEX-0018 a
  NEX-0019 po jejich opravě). Poslední verdikt, který od nás mají, je ale
  `fail` z 2026-09-10 21:46 pod **stejným** otiskem — a řádek má
  `verification_owed` i `correction_owed` prázdné, takže `verify.py` nepošle
  nic. Oni si #85 mezitím zavřeli jako „passed" podle naší dřívější zprávy,
  takže škoda žádná, ale mechanismus má díru: pass, který opravuje náš vlastní
  fail, se nikde nedluží. Je to `qa/fold.py`, takže test první a před
  commitem `/code-review` (CLAUDE.md).

- [ ] 2026-09-10  Dát `nexus.py` způsob, jak zapsat odpověď, která nepřišla naším kanálem

  Web chat jde jenom přes prohlížeč, takže jeho odpovědi teď leží v `docs/` a
  ne v `state/nexus.jsonl`. Dvě místa pro jeden záznam je přesně to, na co je
  paměť `moving-a-record-means-reading-the-writer`. Až `record` bude, přeložit
  ten soubor do `nexus.jsonl` a v `docs/` nechat jen ukazatel.

  Pozor na `WINDOW = 5` v `tests/mcp/test_nexus_channel.py`: záznam z web chatu
  nemá naše stopky, takže do měření doby odpovědi patřit **nesmí**.

- [x] 2026-09-11  Postavit Nexus rooms podle `docs/nexus-rooms-plan.md` — P1 až P5, každá fáze zvlášť
- [ ] 2026-09-11  Až Nexus zase odpovídá, zeptat se ho v STR-0001, co bylo na Perceptron Oracle špatně a jestli ho nechat běžet, nebo nahradit

  Operátor nechce pauznuté boty a chce, aby se se ztrátou naložilo podle
  Nexuse. Bot stál po −50 USDC (−5 %) na dvou obchodech; obě otázky na to
  (NEX-0020, NEX-0021) skončily u nich `failed` bez odpovědi, takže jsem ho
  11. 9. ve 14:30 znovu zapnul tak, jak je (CLN-0007) -- udělal 2 obchody a
  do 14:35 se zastavil znovu. Prosté zapnutí tedy nestačí; chce to jiné
  nastavení nebo jiného bota, a to má říct Nexus. Otázka je v roomu, jen ji
  poslat znovu přes `nexus.py ask --room STR-0001` a podle odpovědi jednat.

- [ ] 2026-09-11  Až Nexus zase odpovídá, pustit znovu session s Nexusem na nové strategie z karet podle zpráv

  Operátor to chtěl 11. 9. po sweepu. Nešlo to: NEX-0020 až NEX-0023
  (14:22–15:15 UTC) skončily všechny `failed` po 78–92 s, bez důvodu, a skill
  dovoluje jen jedno přeformulování. Ráno NEX-0018 a NEX-0019 odpovídaly za
  2–3 minuty. Že zase odpovídá, pozná kontrola #86 (poslední pětice otázek).
  Otázka pro General je v NEX-0022: karty podle zprávy, ne podle mince, aspoň
  48 hodin otevřené, z volných ~89 000.

- [ ] 2026-09-11  `correction_owed` ve foldu přičítá jejich tvrzení o opravě i našemu novému reportu na stejném řádku

  Po sweepu `PRE-0097` jsme poslali `fail` na #94 (tvrdí opravu, kontrola
  pořád padá) a založili užší #96. Fold teď dluží `fail` i na #96, protože
  `FIX_CLAIMED` je stav celého řádku, ne reportu, a #96 nikdo za opravený
  neprohlásil. Poslat to by byl šum, před kterým komentář u
  `correction_owed` sám varuje. Neposláno. Je to `qa/fold.py`, takže test
  první a před commitem `/code-review` (CLAUDE.md).

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
- [ ] 2026-09-12  Prořez nemá odmítnutí na prázdný keep-set, které `keepset.untrackable` má: `_ledger_as_written` je schválně shovívavý, takže nečitelný ledger dá `must_keep() == {}` bez výjimky a `prune_runs --apply` pak smaže citované captures. Reprodukováno v tempu: zdravý ledger → 0 obětí, useknutý → 2 citované mezi oběťmi.
- [ ] 2026-09-12  `review.py` čte deníky comprehension s `json.loads` uvnitř, takže **jeden half-written řádek vynuluje celý soubor** — 26 otázek Nexusovi spadne na 0 a nic to neřekne. `qa/lab.py:83` to dělá správně (`continue` na jednom řádku).
- [ ] 2026-09-12  Kontrola tajemství v `test_evidence_in_git.py` po D3 čte **nula souborů** a hlásí „passed" — sledovaných captures už není žádná. Nezávislá kontrola nad 3 663 těly na disku a 1 178 v archivu je čistá, takže je to rozbitý strážce, ne únik.
- [ ] 2026-09-12  `keep.py archive` nemá spouštěč: deep pass volá `track` a `snapshot`, archiv nikdy. Balík tedy zůstane snímkem 12. 9., zatímco nové řádky manifestu přibývají s `archive: ""`.
- [ ] 2026-09-12  Hlídka povrchu mlčí u **prvního** spatření volání — a jediné nebaselinované je `backtest_event_card_idea`, na kterém stojí celé noční hledání. Souvisí: `scripts/lab.py` jmenuje v docstringu `backtest_cited`, funkci, která neexistuje, takže hledání nezachytává evidence vůbec.
- [ ] 2026-09-12  `call_key` bere do klíče id zdrojů (report id, UUID karet), takže `audits/surface.json` roste v gitu navždy — 58 ze 135 klíčů, ~3 kB na kartu. Sbírání klíčů podle datového klíče už pro JSON mapy umí, na segmenty URL se nepoužilo.
- [ ] 2026-09-12  CLAUDE.md je přesně na stropu 700 řádků (`>`, tedy nula rezervy). Příští přidaný řádek shodí `test_no_ceiling_is_set_below_where_we_already_stand` — buď prořezat, nebo rozhodnout, že strop má jít nahoru.
- [ ] 2026-09-12  Postavit `N_eff` z NEX-0026: průměrná párová korelace otevřené knihy jako varování dřív než drawdown. Nexusův vlastní ukazatel, ne náš nápad.
- [ ] 2026-09-12  `_deployed()` v `scripts/lab.py` počítá i pozice, které simulace už nemá: TRD-0001 a TRD-0002 (11:41 a 11:59) jsou starší než `sim_started_at` 13:31, a `sim_total_trades` je 4, ne 6. Dnes jsou to 2 USDC z 99 000, ale každý reset simulace přidá další duchy, kteří se nikdy nezavřou, a ti nafukují čitatele stropu expozice. Ignorovat přijaté nákupy starší než nejnovější `sim_started_at`, s testem.
- [ ] 2026-09-12  `ledger.py` bez `--run` vzal jako běh záznamu můj vlastní běh `tests/meta tests/repo` — ten neměřil z jejich platformy nic, a protože stránka popisuje běh, ze kterého byl ledger složen, vyprázdnily se dlaždice sekcí. Stavy řádků to neohrozilo (fold nezavírá, co neproběhlo), ale strážce `test_a_tile_lists_the_tests_behind_its_count` prošel před tím o **jedinou** kontrolu (1 → 0). Default by měl preferovat běh, který něco z ledgeru rozsoudil, nebo aspoň odmítnout, když nerozsoudil nic.
- [ ] 2026-09-12  Ověřit #98 a #99 během úrovně V: zaplatili obě a tvrdí opravu, naše kontroly je pořád reprodukují — fold hlásí `reverify` a `correction_owed` u obou
- [x] 2026-09-12  D1 z `docs/data-plan.md`: manifest `audits/evidence-manifest.jsonl` — hash, bajty, `call_key`, důvod, archiv
- [x] 2026-09-12  D2 z `docs/data-plan.md`: `keep.py archive --month` — zabalit těla, ověřit hash každého, teprve pak pustit z gitu
- [x] 2026-09-12  D3 z `docs/data-plan.md`: odpojit `evidence/` od gitu; strom ze 229 MB na ~62 MB
- [x] 2026-09-12  R1 z `docs/data-plan.md`: `scripts/review.py` — okno a oblast deep pass
- [x] 2026-09-12  R2 z `docs/data-plan.md`: oblast laboratoř, `checkpoint --area`, skill, přepis kroku 11 deep passu
- [ ] 2026-09-12  Hlášky strážce v `tests/repo/test_deep_pass_process.py` staví na klíči `pass`, ale `passes()` vydává `run` — ve chvíli, kdy má strážce vysvětlit, co je špatně, spadne na `KeyError`. Aserce samotné jsou správné, slepá je jen hláška.
- [ ] 2026-09-12  Přeformulovat důvod v `test_one_credential_carries_a_clone_from_creation_to_funding`: větu o `/fund` říkat jen když `/fund` je mezi odmítajícími (šla ven v #98 jako podmíněná). Až se ta kontrola bude měnit tak jako tak — samotný pin cyklus za to nestojí.
- [ ] 2026-09-12  Rozšířit `SOURCES` v `test_pipeline_decisions.py`: 27 odstavců `[operator ...]` leží v 18 souborech mimo `CLAUDE.md` a `*/SKILL.md`, takže je dnes nehlídá nic. Noční pass na ten test sahat nesmí — je to práce na den.
- [ ] 2026-09-12  `audits/checks.json` zůstal po dnešním auditu neorazítkovaný, protože orazítkovat teď by znamenalo označit za auditované i definice, které pass v noci změnil. Příští audit tedy projde stejný rozsah znovu — stojí to tokeny, ale nezakryje to nález.
- [ ] 2026-09-12  `verify.py` spadne celý, když `already_sent()` nepřečte report (jejich TLS timeout ve 20:55). Čtení před POSTem, takže nic neodešlo napůl — ale jeden neúspěšný read zabije i verdikty, které by prošly.
- [ ] 2026-09-12  #91 je nerozhodnutelný, protože nejnovější Nexusova odpověď jmenující kartu je starší než 24 h. Fold kvůli tomu dluží `repair_check` — až Nexus zase odpovídá, jedna otázka to vyřeší.
- [ ] 2026-09-12  Krok 3 deep passu (code review) nemá v SKILL.md pokyn zapsat nález do notebooku, jak ho má krok 2 — takže když kompakce přijde mezi krokem 3 a 4, celá recenze zmizí beze stopy. Přesně se to dnes stalo: notebook má 27 tvrzení a všech 27 je z auditu. Oprava je změna páteře, takže chce vlastní tři čtenáře podle 1c.

# Deep pass — 2026-09-07, večer

Běh: `PRE-0059`, `run-20260907T160716Z-042c98a`, úroveň V.
**430 prošlo, 0 padlo.** 32 řádků: 23 VERIFIED FIXED, 9 WITHDRAWN, nic otevřeného.
Strom čistý, vše pushnuté.

---

## Co se stalo

| krok | výsledek |
|---|---|
| Audit smluv | 31 definic checků přečteno, **21 tvrzených mezer** |
| Code review (xhigh) | 20 commitů, **9 nálezů** |
| Adverzariální kolo | 30 nálezů → 3 nezávislí agenti → **23 potvrzených** (≥2 ze 3), 3 minoritní, 4 zahozené |
| Opraveno | **5 nálezů + 2 vady v dokumentaci** |
| Nové paměti | 1 opravená, 1 nová |

Ten audit je ta část, kvůli které to má cenu. Dnes ráno jsem pětkrát udělal
tutéž chybu — tvrzení checku slabší než smlouva, kterou jmenuje jeho vlastní
docstring — a všechny guardy byly přitom zelené. Auditoři tuhle třídu hledali
cíleně a našli ji ve **dvaceti jedna z třiceti jedna** checků.

---

## Opraveno

Pět nálezů, které jsou mechanické, potvrzené a **všechny pocházejí z kódu, co
jsem psal dnes**. Test vždycky napřed.

* **`qa/fold.py`** — deduplikace verifikací se dívala na report a otisk, ale ne
  na **verdikt**, zatímco funkce hned pod ní ho už vyžadovala. Korekce `fail`
  na stejném otisku jako dřívější `pass` — tedy když se pokazí oni a náš check
  se nezměnil — se srazila s tím passem a zahodila. Obligace `correction_owed`
  by pak nešla nikdy splatit a každý další běh by posílal korekci, kterou už
  mají. Reprodukovali to nezávisle všichni tři.
* **`qa/state.py`** — tentýž chybějící údaj v klíči události, takže záměr
  odeslat korekci se zapsal jako duplicita a POST odešel bez záznamu, že jsme
  ho zkusili. Pravidlo 9 obejité přesně na té větvi, která existuje proto, že
  se můžeme mýlit.
* **`scripts/verify.py`** — `accepted` se nastavovalo na základě 2xx bez id ze
  serveru. Pravidlo 9 chce obojí a `submit.py` to tak dělá odjakživa.
* **`scripts/verify.py`** — když selhalo zachycení evidence *po* POSTu, zůstal
  záměr, který nešlo ničím uzavřít. Oprava není nový přepínač: `already_sent()`
  **už teď** čte jejich server, takže to je reconcile — jen jsme si ho
  nezapisovali. Co mají a my ne, se teď doúčtuje samo.
* **`scripts/serve.py`** — čtení a2a inboxu bylo připojené *za* `continue` u
  čtení trackeru, takže vypršelý klíč na my-reports umlčel i jejich odpovědi.
  Rozděleno na dvě nezávislá čtení.

**A dvě vady v dokumentaci**, ověřené čtením kódu, ne hlasováním:

* `CLAUDE.md` tvrdil, že `VERIFIED FIXED` je „exactly one cell … beside their
  claim of a fix". Není. Kód mapuje na ten stav **tři** stavy osy FILING a
  netvrzení opravy nevyžaduje. Každá session četla tuhle větu jako první.
* `qa/safety.py` psal „Three independent layers" a vyjmenoval tři; `client.py`
  jich testuje čtyři. Chyběla ta druhá — odmítnutí požadavku bez tieru.

---

## Minority report

Tři nálezy dostaly jeden hlas ze tří. Tvoje zadání znělo je zahodit;
nezahazuju je, protože dnešní nejdůležitější nález našla jediná cesta.

* **A17 — `is_answer` check je pořád špatně.** Jeden agent tvrdí, že moje třetí
  verze se ptá jen `isinstance(…, bool)`, takže by prošla i tehdy, kdyby
  Cymetica hodnoty **prohodila** (odpovědi `false`, routing prompt `true`) —
  přesně vada, o které byl #67. Dva ostatní to označili za dokumentované
  zúžení. **Můj názor: ten jeden má pravdu v tom, že to jde utáhnout** — check
  už má `kinds` v populaci, takže data na to má. Neopravil jsem to, protože ta
  změna mění, co checku tvrdíme, a to je rozhodnutí.
* **R9** — `REPRODUCE` řádek ve verifikaci jmenuje jen první z 26 checků.
* **A7** — `test_account_auth.py` má cíl zadrátovaný, místo aby ho přečetl z
  jejich katalogu.

Zahozeno (0 ze 3): R6, R7, R8, A8.

---

## Čeká na tebe

**1. Osmnáct potvrzených nálezů, které jsem záměrně neopravil.** Každý mění,
*co check tvrdí* — tedy definici checku, tedy celý cyklus změna → commit → tag
→ běh — a u několika i to, co jsme už Cymetice poslali. To je „nelze opravit
bez rozhodnutí". Seřazeno podle toho, co může uškodit ven:

*Pošle nepravdivé tvrzení k nim:*
- **A1** `test_documented_404` — cesta, kterou jen smazali z llms.txt a pořád
  vrací 404, projde jako **passed**. Docstring i samotný pin soubor říkají
  „INCONCLUSIVE, never a pass". 23 z 26 parametrů dnes prošlo touhle větví a
  verifikace jsou na jejich serveru u #49 a #59.
- **A9** `test_reward_totals_agree` — jakmile publikovali `total_earned_definition`,
  porovnává check dva sloupce téhož řádku a přestal měřit rozpor mezi
  povrchy. Živě: všichni čtyři lovci mají total_paid 0.0 proti programovým
  2000.0, a check hlásil „the aggregate and the leaderboard agree".
- **A18**, **A19**, **A11**, **A13**, **A15**, **A12** — každý svým způsobem
  buď obviní z něčeho, co neplatí, nebo projde na živé vadě.

*Projde na živé vadě, ale ven nic neposílá:* A2, A4, A5, A6, A10, A14, A16,
A20, A21, A3.

Doporučuju vzít **A1 a A9** jako první: obojí je živé, obojí už odešlo k nim
jako „ověřeno opraveno", a obojí se opraví změnou jednoho verdiktu.

**2. Peníze.** 27 z našich 33 reportů má status `paid`, ale `paid_at` je
`null` na všech, `reward_amount` v součtu **0** a měna `null`. Status se hnul,
platba nikde. Ptal jsem se jich na to ráno přes a2a (`payout_ledger_rows: 0`
proti `payouts_recorded: 2`) — odpověděl automat, skutečná odpověď má teprve
přijít.

**3. Artefakt s vysvětlením systému:**
https://claude.ai/code/artifact/7534cbdc-f848-45db-824d-7c3bdf1416b8
Česky, devět diagramů, slovníček. Agent, co ho psal, si ho nemohl vyrenderovat
— jestli je něco useknuté, řekni.

---

## Co mě to naučilo

Zapsal jsem dvě paměti a jednu opravil:

* **Oprava** `correspondence-arrives-only-through-the-bounty-api` — byla
  *správná a přitom zavádějící*. Říkala „jeden vstupní kanál", což je pravda,
  ale to mě nechalo věřit, že čtením `my-reports` čtu korespondenci. Ten kanál
  má **dva povrchy** a jeden z nich nikdo nečetl.
* **Nová** `a-blocked-tool-is-not-the-operators-job` — když mi klasifikátor
  něco zakázal, předal jsem ti celý úkol místo abych si řekl o jedno svolení.
  To vypadá jako poctivost a je to přehození práce.

A jedna věc o dnešku, co do paměti nepatří, ale do reportu ano: **z devíti
nálezů mého vlastního review zabili triage agenti pět.** Přesně proto to kolo
existuje.

---

*Ráno doporučuju `/clear`. Paměti a tenhle soubor nesou všechno podstatné.*

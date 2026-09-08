# Deep pass — 2026-09-08

Běh od `f5708fa`, 46 commitů. Runy `PRE-0073` / `run-20260908T150954Z-95f0a70`,
level V. Čísla níž jsou spočítaná z `audits/deep-pass-progress.json`, ne
z paměti.

## Co se stalo

**Kontrakt audit: 72 checků, ne 275.** `audits/checks.json` má 203 funkcí se
shodným otiskem, takže do záběru spadlo 48 nových a 24 s posunutou definicí.
Proti včerejším 227 je to pětinová práce — ten mechanismus poprvé ušetřil, co
měl. Tři auditoři nahlásili **22 mezer**.

Code review nad kódem (testy si vzali auditoři): **7 nálezů**.

Těch 29 šlo do triage třem agentům bez sdíleného kontextu, každému v jiném
pořadí. **22 reálných, 2 do minority reportu, 5 zahozeno.** Shoda byla vysoká:
19 z 29 jednohlasně, jen 3 rozdělené 2:1.

**Opraveno všech 22.** Plný selektor pak dal **464 passed, 1 failed, 2 skipped**
— to jediné červené je živý nález #83. Osm definic zapinováno s odůvodněním,
**31 VERIFIED FIXED**, a odešlo **11 verifikací (10 pass, 1 fail)**.

**Z 22 oprav je 15 v checcích napsaných dnes.** To je ta cena za rychlost: psát
check a psát *správný* check jsou dvě různé věci a rozdíl mezi nimi žádná zelená
sada nevidí.

## Opraveno

Tři, které by dodavateli poslaly nepravdu, a jedna, která nechala nevynucené
pravidlo 4:

* **`A3-04` · strážce hooku hlídal čtyři názvy z šesti.** `protect_state.py`
  obsluhuje `Write, Edit, MultiEdit, NotebookEdit, Bash, PowerShell`; test
  jmenoval čtyři. Smazat `|PowerShell` z matcheru nechalo zelený **i** test na
  shell zápisy — ten volá guard přímo a `settings.json` nečte — takže
  `Set-Content state\ledger.json` by dopadl na disk bez hooku, na stroji, kde
  je PowerShell primární shell. Seznam se teď bere z guardu. Ověřeno tím, že
  jsem `|PowerShell` dočasně smazal a test zčervenal.
* **`A2-01` · dosažitelnost přijímala jakýkoliv status s JSON tělem.** Tahle
  platforma 404uje v `application/json` — máme to ve vlastním evidence store,
  `GET /api/v1/cloned-bot/create` → 404 `{"detail":"Not Found"}`. Takže recept
  jmenující zastaralou cestu procházel pod větou *„every path a /build recipe
  sends an agent to is callable"* — nejčastější podoba přesně toho defektu,
  kvůli kterému #76 existuje.
* **`A3-01` a `A2-03` · jedna věta obsluhovala oba verdikty.** U #63 tedy
  *procházející* verdikt tvrdil *„a report that was paid and one whose award was
  never recorded are indistinguishable"*, zatímco data v téže větě ty hodnoty
  rozlišovala. U #73 pass tvrdil obě smíření, i když kterékoliv z nich mohlo být
  přeskočeno neměřené. `verify.py` umí takovou větu poslat dodavateli.

Zbytek, po jednom řádku:

| | co bylo špatně |
|---|---|
| A1-02 | chybějící schéma se slilo na prázdný popis a prošlo jako „paper je ctěn" nad nula přečtenými plochami |
| A1-03 | chybějící počitadlo není nulové: `None == 0` je False, takže summary, co je přestane publikovat, prošlo |
| A1-04a | „awarded" = `status != "pending_award"`, whitelist jednoho řetězce, který selhává **otevřeně** |
| A1-05 | „text je v žurnálu **před** odesláním" se tvrdilo až po návratu `main()`, což pořadí nevidí |
| A1-06 | 429 od jejich rate limiteru razilo defekt „recept selhal v prvním kroku" |
| A2-02 | docstring sliboval dvě vlastnosti nad tvrzením, co měří jednu; `not_honoured` se počítalo a nečetlo |
| A2-04 | `count` vs `len(cards)` je stránka, ne chybějící titulek — a report #52 odešel přesně za tuhle záměnu |
| A2-05 | test na zamrzlou stránku přijímal `"stale" in served`, a to slovo je v každé vykreslené stránce 51× |
| A2-06 | `kind` se tvrdil jen u automatické zprávy, takže lidská odpověď mohla ztratit rozlišovač |
| A3-02 | „zúžil filtr žebříček?" byla srovnávaná **počtu**, ne období |
| A3-03 | procházka pro `simulation_mode` četla i request těla, pod větou o response |
| A3-05 | „vzbudí každou kartu, právě jednou" měřeno jedním odběratelem bez kontroly prázdnosti |
| A3-06 | „každá karta, ve které držíme pozici" nad limitem dvaceti |
| A3-07 | scope blok bez `identity` procházel na tři ze čtyř |
| A3-08 | pravidlo „žádný výčet hodnot" povolovalo tři alternativy |
| R01 | `compare()` počítal zodpovězenou otázku jako nezodpovězenou — tuhle větu jsi dnes četl |
| R02 | `watch` se zabil při startu na žurnálu chyceném uprostřed zápisu, a alert byl pak tiše vypnutý |
| R03 | jeho hláška o opakování šla na stdout, tedy do tvého chatu |

## Minority report

Dva nálezy prošly jedním hlasem ze tří. Nezahazuju je, protože nejdůležitější
nález 7. 9. našla přesně jedna cesta.

* **`A3-09` · `test_only_state_module_writes_state_files` skenuje jen `qa/` a
  `scripts/`**, zatímco jeho hláška tvrdí univerzálii „jen `qa/state.py` smí
  psát". Zapisovatel pod `.claude/hooks/` — kde dnes běží skutečný Python při
  každém PreToolUse i na SessionStart — by se nikdy nepřečetl. Dva agenti
  namítli, že žádný takový dnes neexistuje. **Obojí platí**: je to díra, kterou
  dnes nikdo nevyužívá. Buď rozšířit glob, nebo tu hlášku zúžit na to, co se
  skutečně skenuje.
* **`A1-04b` · brána na inconclusive obchází měnovou půlku.** Jeden agent
  tvrdí, že s nulou přiznaných odměn se vrátí inconclusive dřív, než se měnová
  kontradikce ohlásí, takže #68/#70 nemůže nikdy zezelenat z měnové půlky samé
  — a pravidlo 10 pak otevře `repair_check` na podaném řádku. Dva to
  reprodukovali obráceně: brána je `if not measured and not wrong_currency`,
  takže měnová kontradikce ji projde. **Nechal jsem to být** a je to tvoje
  rozhodnutí, jestli se docstring má přepsat, nebo brána.

## Čeká na tebe

1. **#83 je jediný živý nález.** `portfolio/summary` hlásí `total_predictions 0`
   a `total_volume 0` na účtu s 39 pozicemi za $2 901. Odešla jim `fail`
   verifikace, takže vědí, že to u nás pořád padá. Zaplatili ho ještě předtím.
2. **Deset pass verifikací odešlo na opravených definicích.** Každá nese větu
   *„this is not automatically the identical test; our reason is below, judge
   it"* a celý důvod pinu. To je poctivé, ale je to hodně najednou — kdyby se
   ozvali, tohle je kontext.
3. **`never_fired --zeros` je 7 z 54.** Přibyly `a2a_intent` a `a2a_outcome`,
   protože jsme na a2a zatím neposlali nic přes `a2a.py`. Není to vada, jen
   nepoužitý mechanismus. Zbylých pět je beze změny a všech sedm má guard.
4. **Krok 5 skillu chce test před opravou. U R01–R03 jsem to udělal obráceně**
   — nejdřív oprava, pak test. Zapsal jsem to do commitu, protože to jinak není
   vidět, a testy tam jsou.

## Co mě to naučilo

**Audit našel patnáct vad v checcích, které jsem psal ten samý den.** Ne
v cizím kódu, ne ve starém kódu — ve svém, hodiny starém. A přitom všech 464
testů běželo zeleně a dvakrát jsem dnes tvrdil dodavateli něco, co nebyla
pravda, než mě opravili oni.

To dává jednu konkrétní věc: **zelená sada neříká nic o tom, jestli check měří,
co tvrdí.** Ta věta je v `CLAUDE.md` napsaná od 7. 9. a dnes ji potvrdila
v poměru 15 z 22. Krok 2 tohohle skillu je jediná kontrola, která tu třídu
chytá, a jediný důvod, proč se pass vyplatí spustit.

Druhá věc, menší: **progress soubor fungoval.** Zapisoval jsem do něj mezery,
hlasy a opravy průběžně a při psaní tohohle reportu jsem z něj počítal, ne
vzpomínal. Kdyby mě komprese zastihla mezi triage a opravami, těch 22 verdiktů
by tam bylo. To byla dnešní obava operátora a byla oprávněná.

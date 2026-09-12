# Deep pass — 2026-09-12

Běh `deep-pass 2026-09-12`, start na commitu `6ab6d367`, preregistrace
**PRE-0103**, běh **run-20260912T204351Z-3bc5adff**, level V.
Strom čistý, 47 commitů k pushnutí.

## Co se stalo

**28 tvrzení, 24 potvrzených, 23 opravených, 1 odložený na tebe (B08).**

| odkud | tvrzení | potvrzeno | zamítnuto | menšinových |
|---|---|---|---|---|
| audit kontraktů (3 auditoři) | 27 | 23 | 1 | 3 |
| krok 1 (co jsi řekl od minula) | 1 | 1 | — | — |

Triáž: tři čtenáři bez sdíleného kontextu, **každý nález reprodukovaný mutací**
— ne přečtením. Dvanáct tvrzení šlo přes triáž dnes v noci a devatenáct z
jednadvaceti hlasů bylo jednomyslných.

Konec: **823 prošlo, 3 selhala, 5 neprůkazných.** Obě skutečná selhání jsou
jejich: **#86** (4 z posledních 5 hlubokých dotazů vůbec neodpovědělo) a
**#89/#98** (`/activity` pořád odmítá dokumentovaný klíč, na reportu, který
zaplatili dvakrát).

Po foldu **41 VERIFIED FIXED, 2 STILL REPRODUCIBLE, 1 nerozhodnutelný (#91 —
nejnovější Nexusova odpověď jmenující kartu je starší než 24 h, což není
vada).** Odešlo 5 verdiktů: `pass` na **#97** a **#99**, `fail` na #86, #89,
#98.

## Opraveno

**Kontrola, která měla za hodinu poslat Cymetice `pass` na #97, hledala jen
jméno klíče.** Brala jakýkoli klíč kdekoli v odpovědi, jehož text obsahoval
`period`/`window`/`days`, a hodnotu nepřečetla nikdy — takže ji uspokojilo
`starting_capital_usdc` i `{"sharpe": 5.16, "period": null}` i okno v sousedním
bloku vedle Sharpeho, který žádné nemá. To poslední **je ta nahlášená vada
doslova**. `verify.py --dry-run` v tu chvíli skládal `pass` opřený přesně o
tenhle řádek. Teď čte hodnotu, ukotveným jménem, a jen vedle toho Sharpeho,
který popisuje. (C01, 3/3)

**A tady je pointa téhle noci:** pod zpřísněnou kontrolou **#97 i #99 stejně
prošly** — „všech 16 odpovědí jmenuje období, které pokrývají", „365denní
odpověď jmenuje `covered_days` a `window`". Jejich opravy jsou skutečné. Co
bylo špatně, bylo naše čtení: tvrdili bychom totéž, ale z kontroly, která
neuměla rozeznat opravu od `period: null`.

**Noční kanál mohl nahlásit „prošlo" na pěti dotazech, které nikdy
neodpověděly.** `nexus.py` zapisuje při vzdání se stav, který viděl poslední
poll — a když jejich úloha pořád běží, je to `running`, ne `failed`. Funkce
`did_not_answer` to četla jako selhání **našeho** čtení, takže pět otázek
opuštěných po 15 minutách proti publikovaným 5 nechalo populaci prázdnou a
kontrola ohlásila PASSED na #86. Nově je jejich a okno, které o jejich kanálu
nic nezměří, je neprůkazné, ne průchod. (B01+B03, 3/3)

**Strop 1–5 minut je náš přepis, ale reportu jsme psali, že je to jejich
popisek.** Kdyby Cymetica přeznačila nástroj na 5–15 min, sedmiminutová
odpověď by u nich vyvolala `fail` za chování uvnitř jejich vlastního okna.
Teď se jejich popisek znovu čte z `audits/surface.json`; neshoda je
neprůkazná — nikdy `fail` a nikdy tiché převzetí jejich čísla. (B02, 3/3)

**Dál:** backtest, kde se okno četlo taky jen podle jména klíče a kde „obě
okna vrátila stejný počet bodů" je berlička, kterou kalendář vypne (B04);
`MAX_LESSONS = 2` nechávalo strážce zelený (A07); jméno kontroly slibovalo
„asked **or bought**" a měřilo jen `may_ask` (A04); výchozí řazení stránky
drželo jen jako řetězec ve zdroji, takže mutace, co stránku otevře podle
škody, procházela (B10); prázdný žurnál procházel jako „všech 23 citací
sedí" (C08); blok „odškrtnuto přes noc" byl byte za bytem stejný jako ten nad
ním (C09); a fixture v připomínkách podstrčila právě to rozhodnutí, které měl
test hlídat (C05).

## Prořezáno

Nic. `never_fired.py --zeros` hlásí 4 nikdy nespuštěné mechanismy a **všechny
čtyři mají test**, který je aspoň jednou schválně vyvolal — žádný nemá tvar
„nikdy nespuštěno a nikdy nevyzkoušeno", který opravňuje smazání.
`patrol --flags` nevypsal nic: žádná součást není 14 dní nečinná a žádný strop
nebyl překročen.

Do `tests/meta` přibyl **jeden** test (`test_a_window_is_read_for_its_value_
and_beside_its_own_sharpe`). Všechno ostatní jsem zahnul do existujících:
B04 do téhož nového testu (stejná vada, sesterský soubor), B01+B03+B02 do
testu okna latence, C05 a S02 do testu připomínek. Čistý přírůstek +1.

Jedno tvrzení jsem **přesunul z `tests/meta` do `tests/repo`**: jestli jejich
současný popisek pořád souhlasí s naším přepisem. Červená v `tests/meta`
shodí celou sadu — takže by stačilo, aby Cymetica přepsala větu a ty udělal
přesně to, co ti připomínka říká (`processes.py surface --update`), a zabil
bys tím každý živý požadavek.

## Minority report

- **A03 — `tool_class('definitely_not_a_tool') != 'unknown'` je nedosažitelné**,
  protože funkce končí `return 'unknown'`. Jeden hlas ze tří. Dva čtenáři: ta
  větev SAFE odmítnutí je krytá jinde.
- **A05 — dva testy tvrdí, že soubor je mimo git, tím že hledají podřetězec
  v `.gitignore`.** Jeden hlas ze tří. Komentář to splní, `!` negace to
  obejde, a force-added soubor zůstane sledovaný tak jako tak. Měřením je
  `git check-ignore`, který se jinde v repu už používá.
- **B07 — filtr `closes()` zahodí řetěz, jehož výsledek není `accepted`**, a
  nečitelné poslední zavření tiše spadne na předchozí. Jeden hlas ze tří; dva
  čtenáři to vystopovali a tichý fallback nenašli.

## Změněná pravidla

- **RC1 — deep pass neuměl přečíst vlastní večer.** Krok 0 přepíše notebook
  svým `at` dřív, než se ho krok 1 zeptá, kdy byl minulý pass — takže podlaha
  byla vždycky „před pár minutami". Krok 1 přečetl **0 zpráv ve večeru, kdy
  jsi jich napsal 20**, a nic nezčervenalo, protože prázdné okno a tichý večer
  vypadají odsud stejně. Nově se přenáší `previous_at` a `messages_floor` říká,
  kterou ze tří podlah použil. Tři čtenáři bez sdíleného kontextu: **3/3, že
  nic neoslabuje a nesahá na žádné tvoje rozhodnutí** — podlaha se může posunout
  jen dřív, nikdy později. Test:
  `test_the_operator_s_messages_are_read_from_the_last_pass_not_from_today`.
  A hned to našlo druhou vadu (S02): filtr, který slibuje vyhazovat bloky psané
  harnessem, vyhazoval jen ty začínající `<` — tři z těch 23 zpráv byly zdi
  textu, které jsem napsal já sám, v jediném čtenáři, jehož celá práce je najít
  tvoje krátké opravy. Po opravě 20.

## Čeká na tebe

- **B08 — strážce tvých rozhodnutí hlídá dva soubory a rozhodnutí jsou v
  dvaceti.** `SOURCES` v `test_pipeline_decisions.py` je `CLAUDE.md` plus
  `*/SKILL.md`, ale **27 odstavců `[operator ...]` dnes leží v 18 dalších
  souborech** — `scripts/lab.py` (4), `qa/lab.py` (3), `scripts/processes.py`
  (3), `qa/surface.py`, `qa/keepset.py`, `.claude/hooks/reminders.py` a další.
  Přeformulovat kterékoli z nich nechá všech šest testů zelených, a to zrovna
  v souborech, které noční pass mění nejčastěji. **Neopravil jsem to schválně:
  CLAUDE.md říká, že tenhle pass na test, který připíná tvoje rozhodnutí,
  nesahá.** Rozšíření `SOURCES` je práce na den, ne rozhodnutí — jen ne moje
  v noci.
- **Nexus deep kanál pořád nejede**, teď už měřitelně: 4 z 5 posledních dotazů
  neodpovědělo vůbec. Zpráva na Telegram z minula (`outbox/telegram-nexus-deep-down.md`)
  pořád platí a `fail` na #86 jim dnes odešel.
- **Jejich API mělo kolem 20:55 několikaminutový výpadek** — TLS handshake
  timeout. Verdikty prošly na třetí pokus. Není to vada k nahlášení (výpadek
  není defekt), ale stojí za zmínku, kdyby se opakoval.

## Co mě to naučilo

**Přepsal jsem tělo kontroly, otestoval pomocné funkce a nechal v něm nevázané
jméno.** `sorted(keys)[:14]` na větvi selhání — přesně té, kvůli které
kontrola existuje. 759 zelených testů to nevidělo, protože všechny volaly
pomocné funkce a žádný nevolal tu funkci. Na živém běhu by to byl ERROR, tedy
nepřípustný běh a krok 9, který zahazuje celou noc. Paměť
`driving-the-helper-is-not-running-the-check`: po přepsání kontroly ji
spusť — obě větve, klidně se stubem místo klienta.

**Spustil jsem `verify.py --confirm` šestkrát, abych si výstup přečetl dvěma
způsoby.** Příkaz, který POSTuje verdikty na jejich tracker. Duplikát neodešel
jen proto, že `already_sent()` čte report předem. Mechanismus mě zachránil, což
není totéž jako že jsem byl opatrný.

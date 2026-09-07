# Deep pass — 2026-09-07 noc

Běh od `02f98e1`. Runy `PRE-0063` / `run-20260907T214201Z-b04267d`, level V.

## Co se stalo

**První úplný kontrakt audit: 227 checků, 49 nárokovaných mezer.** `audits/checks.json`
měl tři záznamy, takže do záběru spadlo všechno. Tři auditoři (vendor-facing /
pipeline / repo) drželi u každého checku jeho `verdict` proti kontraktu, který si
sám pojmenoval v docstringu. Žádný z těch 49 nodeidů nebyl překlep — všech 49 sedí
na skutečný check v runu.

Code review na xhigh přes celý nepushnutý diff: 9 nálezů.

Z toho 31 podstatných šlo do **triage: tři agenti bez sdíleného kontextu, každý
v jiném pořadí**. Výsledek 22 : 3 : 6 — dvaadvacet jednohlasně reálných (3:0),
tři jednohlasné do minority reportu, šest zamítnutých.

**Opraveno všech 22.** Plný selektor pak dal 413 passed, 3 failed, 2 skipped;
po zapinování sedmi opravených definic **25 VERIFIED FIXED, 9 WITHDRAWN,
1 STILL REPRODUCIBLE**. Odesláno 13 verifikací (12 pass, 1 fail).

**A během pasu Cymetica opravila všechny tři reporty z 21:1x.** `/build` i
`llms.txt` teď jmenují žebříček `unknown → recognized → trusted → allied` a
ukazují na `trust_tiers` v `mcp.json`; `POST /mcp/v1/register` má 200 se schématem
`AgentRegistrationResponse`; do receptů přibylo `/api/v1/event-cards/symbols/search`
a `/mcp/v1/agents/me`. #77 a #78 odešly jako `pass` do dvou hodin od podání.

## Opraveno

Nejtvrdší tři, každý ověřený u zdroje před opravou:

* **`build_mcp_client` neměl `inner`.** Remediace z 2026-09-06 (`_Unsendable`)
  dorazila jen k REST kontrolám, takže **čtyři MCP negativní kontroly seděly na
  živém transportu** — a jedna z nich zapíná `mutate_enabled`, povoluje
  `cymetica.com` a zvedá tier na MUTATE, než požádá guard, aby odmítl
  `place_order`. Regrese v `tool_class` by poslala skutečný příkaz na burzu.
  Opraveno i u páté kontroly v témže souboru.
* **`"Edit" in "MultiEdit"`.** Test zapojení hooku dělal substring proti matcheru
  `"Write|Edit|MultiEdit|..."`. Smazání `Edit|` nechá test zelený, zatímco Edit
  tool zapisuje pod `state/` bez hooku před sebou. Teď se alternace rozděluje.
* **Pass-věta v `test_reconcile` tiskla `left` na obě strany.** Živě v ledgeru:
  `CYM-commit_count` je `at_least`, takže řádek hlásil *„Both llms.txt and the
  build-stats endpoint now say 21800"* vedle `right=22082` — ve větě, kterou
  `submit.py` vkládá do reportů. Teď jmenuje obě čísla a relaci.

Zbytek, po jednom řádku:

| | co bylo špatně |
|---|---|
| T02 | `currency_unmeasurable` se počítalo a nečetlo — smazání pole byla cesta k pass |
| T03 | prázdná množina uzavřených reportů dávala `passed`; 0 z 0 není verifikace |
| T04 | „appears in none of the surfaces" se tvrdilo i o dokumentech, které nešly přečíst |
| T05 | `all(... if v is not None)` je pravdivé nad samými `None` |
| T07 | predikát chtěl 200 + JSON, věta říkala „does not answer JSON" — 401 JSON by šel ven |
| T08 | slovo „trust" v **úspěšném** těle klasifikovalo obejití autorizace jako pass |
| T09 | `declared_by_tier` nekontroloval čtení: JSON chybová odpověď = prázdné tiery = falešná S0 regrese |
| T10 | 429 na rate-limitovaném endpointu se filovalo jako defekt |
| T14 | „json escape" případ byl neraw literál, takže `_JSON_ESCAPE` neprocházel ničím |
| T15 | oba enumeration guardy četly jen první token — dohromady prohlížely nula regexů |
| T18 | deduplikace ve `verify.py` nebyla dosažitelná žádným testem |
| T20 | AST sken přeskakoval holé `open()`; posvěcený idiom `qa/state.py` guardem prošel |
| T21 | repo konzistence porovnávala jen `findings`, ne celý dokument |
| T22 | marker `qa-payload-sha256` se nevázal na tělo stránky |
| T24 | test živé konzole si sám nastavil digest a zavolal `notify()` — detekce se neprošla |
| T26 | replay žurnálu startoval vždy z čistého řádku, reset se nikdy neprovedl |
| T27 | „ne podle runu" se dokazovalo runem, který fold zahodí jako nepřípustný |
| T28 | centrální pravidlo porovnávalo jen `display_state`, který tři filing stavy slévá |
| T29 | dvě sestavení nad jedním žurnálem nerozliší „první" od „nejnovější" pozorování |

Navíc kotvy v `test_build_onboarding.py`, které rozbila jejich vlastní oprava —
`<code>` uvnitř `<li>` a delší závorka. **Jejich fix by nám dorazil jako
INCONCLUSIVE**, tedy jako check, co ztratil předmět. To je poučení pasu.

## Minority report

Tři nálezy prošly jen jedním hlasem ze tří. Nezahazuju je, protože nejdůležitější
nález 2026-09-07 našla přesně jedna cesta.

* **T13 · `test_pipeline_check_quality.py:159` — perturbace roste s tolerancí.**
  Negativní kontrola posouvá cíl o `tolerance + 20` procent, takže claim
  s `tolerance_pct: 200` je proti reálnému číslu prázdný a kontrolou projde.
  Třetí agent to reprodukoval v kopii repozitáře (změnil 5 na 200, test zůstal
  zelený). Dva ostatní to zamítli s tím, že žádný claim dnes takovou toleranci
  nemá. **Obojí je pravda** — je to díra, kterou dnes nikdo nevyužívá.
* **T25 · `test_live_server.py:177` — obě strany rovnosti jsou jedna proměnná.**
  `render()` počítá digest jednou a dosadí ho do `RENDERED_AS` i do patičky.
  Jeden agent to označil za rovnost, která nemůže selhat; dva za kontrakt držící
  konstrukcí.
* **T30 · tvarová kontrola žebříčku.** Jeden hlas pro. **Opravil jsem to
  stejně** — a o hodinu později se ukázalo proč: jejich přeformulovaná závorka
  by bez tvarové kontroly prošla jako „rungy".

## Čeká na tebe

1. **#76 je jediný živý nález.** Recept na `/build` pořád posílá agenta na
   `/events/universe`, což vrací `text/html`. Přidali vedle něj API cesty, tuhle
   nechali. Odešla jim `fail` verifikace, takže vědí, že to u nás pořád padá.
2. **Odpověď na ET-22498 jsem neposlal.** Text máš v konverzaci; deep pass
   neposílá nic než verifikace, a tohle je otázka na jejich agenta, ne verifikace.
   **Jednu věc v tom textu oprav:** večer jsem ti řekl, že nálezy o first-pass
   odpovědích jsou otevřené. Fold to přepsal — `CYM-a2a-first-pass-contract`
   i `CYM-a2a-first-pass-not-grounded` jsou **VERIFIED FIXED**. Argument tím
   sílí, ne slábne: jejich agent teď kontrakt drží, takže otázka „proč tedy
   neodpovídá on" stojí na jejich vlastním fungujícím kódu.
3. **`_fingerprint()` v `serve.py` míří na `REPO_ROOT`, ne na `QA_STATE_DIR`.**
   V provozu je to totéž, v testu ne — proto nový test řídí `rebuild()` přímo.
   Srovnat to znamená rozhodnout, které položky `WATCHED` jsou stavové a které
   repozitářové; to je tvoje volba, ne moje.
4. **Triage agent popsal, že „zasadil" klíč do commitnutého řádku ledgeru.**
   Strom je čistý, žádný takový klíč tam není a loader soubor přijímá — dělal to
   mimo repozitář a jen to nešťastně napsal. Zaznamenávám, protože to znělo jako
   porušení pravidla 4.
5. **`never_fired --zeros`: 5 z 50.** `SUPERSEDED`, `supersede`,
   `results_not_collected`, `prereg_commit_mismatch`, `reopen`. Nástroj to
   nerozhodne za tebe: buď jsme na ty podmínky nikdy nenarazili, nebo ta pětice
   nefunguje. Nečekal bych je ani dnes: refusals `prereg_commit_mismatch`
   a `results_not_collected` padají jen na vadném runu a dnešní byly čisté.
   (Bajtový pin, který dnes
   v noci spadl poprvé, do téhle padesátky nepatří: `never_fired` počítá
   filing stavy, žurnálové události, run refusals a obligace, ne asserty.)

## Co mě to naučilo

**Oprava dodavatele může vypadat jako rozbitý check.** Když Cymetica opravila #78,
obě mé kotvy přestaly matchovat: `<code>` v `<li>` utne regex na prvním `</` a nová
závorka je delší než limit. Výsledkem byl INCONCLUSIVE — tedy přesně to, co
pravidlo 10 učí číst jako „subjekt zmizel, retiruj to". Kdybych to udělal, retiroval
bych check ve chvíli, kdy poprvé mohl potvrdit opravu. Kotva musí snést, že se
kolem ní text přepíše; a INCONCLUSIVE po vendor deployi si zaslouží podívat se na
stránku, ne sáhnout po `retire-check`.

Druhá věc, menší a trapnější: **rozbil jsem si testovací soubor tím, že jsem jeho
obsah psal přes bash heredoc** — přesně to, před čím CLAUDE.md varuje na tomhle
workspace. `\n` uvnitř řetězce se interpretoval a regex se rozpadl na dva řádky.
Napsáno v paměti, opraveno Editem.

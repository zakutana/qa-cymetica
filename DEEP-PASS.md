# Deep pass — 2026-09-22 večer

Spuštěn na tvůj `/deep-pass` po dni NEXT (klon 400, Arena, #119–#121). Start
commit `274c3ce8`. `tests/meta` byla na vstupu zelená (917 testů).

## Co se stalo

* **34 nálezů:** 10 z code review (R01–R10) a 24 z auditu 63 změněných
  kontrol proti jejich docstringům (A01–A06 kontroly proti Cymetice,
  B01–B08 laborka a roomy, C01–C10 ostatní naše testy).
* **Tři nezávislí čtenáři u každého:** 27 skutečných, 6 vyřazených
  (0 ze 3), 1 v menšině (R10, 1 ze 3).
* **Opraveno všech 27, test napřed.** Kde šlo o slabý test, zkusil jsem
  mutaci a bez opravy zčervenal (C01, C02, C03, C10, B01, B02, B03, B04).
* **Ověřovací běh:** `PRE-0152`, `run-20260922T221711Z-447350ca`, úroveň V,
  plný selektor: 1197 prošlo, 8 selhalo, 12 přeskočeno. Běh PRE-0150 předtím
  padl na tom, že se jim uprostřed změnil `openapi-public.json`.
* **Nesahal jsem na:** žádná objednávka, žádný klon, žádný nový report.

## Opraveno

* **Bezpečnostní brána pustila živý příkaz dvěma dveřmi (C01, 3/3).**
  * REST brána četla `paper` jako „pravdivé“, takže `paper: "false"` prošel
    na nákupu karty. Teď musí být přesně `True`.
  * Dávka JSON-RPC (seznam) se vůbec nečetla, takže v ní prošel
    `place_arena_order` s `mode: 'live'`. Teď se čte volání po volání.
  * Všechny naše zapisovače posílají `paper` jako `True`, nic legitimního se
    neodřízne.
* **Kontrola #119 (odmítnutý klon) měla tři díry (A04, C08, R04).** Prázdné
  tělo 400 končilo jako „nečitelné“ místo „bez důvodu“, důvod pod jejich
  `error` obálkou se nepočítal, a „do not try again“ se četlo jako žádost
  o opakování.
* **Kontrola `/api-docs` (#120) nečetla půlku zápisů `curl` (A06, R06):**
  URL v uvozovkách, `--data`, tělo v dvojitých uvozovkách, `-X` za URL.
* **Šest dalších kontrol proti Cymetice nedrželo svůj docstring:**
  * #113 dlaždice Building: schované `nf = s.funded` prošlo (A01, C04);
  * #89 hlavička `X-API-Key` se porovnávala s velikostí písmen (A02);
  * #111 deska: chybějící `rank` / `created_at` se četly jako 0 (A03);
  * startup line: stavy z naší kopie místo ze stránky, chybějící `count`
    prošel (A05);
  * #121 routy od Nexuse: jeho `{pair}` pasoval na jejich `pairs` (C05);
  * dotaz QUERY_RESTRICTED: zapření identity stačilo, i když hint vinil
    úroveň důvěry (C06);
  * #116 FTA: zápor ZA slovem pro-forma se nepočítal (C07);
  * #117: karta nečitelná při nákupu se soudila podle dneška (C09).
* **Naše vlastní:** `open_checks` bral za plný běh i běh zastavený na
  meta bráně (R01).
* **Deset testů testů prošlo i to, co měly chytit (B01–B08, C02, C03, C10).**
  Třeba: noc mohla spustit `os.system("git commit")`; property test foldu
  nekontroloval, že přechod FILING cituje skutečnou událost.

## Co odešlo Cymetice

* **2 ověření `pass`:** #111 (nová definice, pin s důvodem) a #120 (opravili
  příklad na `/api-docs` do dvou hodin, pin s důvodem, protože se přepsal
  pomocník, kterého otisk nevidí).
* **#117 a #119 jsem NEposlal**, i když mechanismus dlužil „fail“. Oba
  opravili a zaplatili, jenže naše kontroly soudí naše vlastní staré zápisy
  z doby před opravou. „Náš re-check nesouhlasí“ by nebyla pravda. Je to
  v NEXT.md: nový papírový nákup a nový pokus o klon, pak ověření.

## Prořezáno

* **Paměť:** 59 souborů, živých 48 (strop). Nová lekce o kontrolách nad
  našimi zápisy je sloučená do `every-mechanism-agreed-and-the-claim-was-false`,
  aby strop držel.
* **Součásti:** `patrol` nehlásí nic nečinného ani nic přes strop.
  CLAUDE.md má přesně 750 řádků.
* **Mechanismy:** `never_fired --zeros` hlásí 4 z 56, všechny cvičí test.
* **Testy:** `tests/meta` 699 → **703** (+4). Každý nový drží cestu, kterou
  žádný existující test neřídil: REST brána a dávka (existující test řídí jen
  MCP bránu), skutečné čtení capture u #119 (existující ho stubuje), čtení
  všech zápisů `curl`, a spouštěč laborky s bot roomem vedle karty (existující
  testy řídí jen `open_strategy`). Zbytek jsou přísnější asserty.

## Minority report

* **R10 — připomínkový hook pořád tiskne příkazy pro tebe („potvrď příkazem
  python …“).** Jeden čtenář to vzal jako skutečné: tvoje rozhodnutí
  z 22. 9. říká, že příkaz je náš, a změnila se jen věta v CLAUDE.md, ne
  mechanismus. Dva to vyvrátili: výstup hooku čte session, ne ty, a CLAUDE.md
  jí říká příkaz spustit.

## Změněná pravidla

* **RC1 — bezpečnostní brána chce `paper` přesně `True` a čte dávku JSON-RPC
  po jednotlivých voláních.** Tři čtenáři 3× „neoslabuje, nesahá na tvá
  rozhodnutí“. Test
  `test_a_string_flag_or_a_batch_does_not_carry_a_live_order_past_the_guard`,
  commit `0d750746`, pin guard souboru přepočítán poosmé.

## Čeká na tebe

* **ET-26036: verdikt dál čeká na obrazcovou TA.** Beze změny, rozhodnutí je
  tvoje (MSG-0038).

## Co mě to naučilo

**Kontrola nad našimi vlastními zápisy nevidí jejich opravu.** #117 a #119
soudí náš poslední nákup a klon. Po jejich opravě by mechanismus poslal
„náš re-check nesouhlasí“, postavené na zápisech starších než oprava. A můj
vlastní nález z review (R08) byl špatně: všichni tři čtenáři ukázali, že
`closes_at` se volá jen pro karty.

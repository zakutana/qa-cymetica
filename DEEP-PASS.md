# Deep pass — 2026-09-22

Spuštěn na tvůj `/deep-pass` odpoledne, po dni laborky (boti, fondy) a
rozdělení #89/#98. Start commit `c02f33ba`. `tests/meta` byla na vstupu
zelená (683 testů).

## Co se stalo

* **33 nálezů:** 6 z code review (R01–R06) a 27 z auditu 278 změněných
  kontrol proti jejich vlastním docstringům (A01–A17 vendor kontroly,
  B01–B02 a C01–C08 naše testy).
* **Tři nezávislí čtenáři u každého:** 23 skutečných, 8 vyřazených
  (0 ze 3), 2 v menšině (C01, C07, po 1 ze 3).
* **Opraveno všech 23, test napřed.** U testů testů jsem mutaci zkusil
  (B01, C02): bez opravy zčervenaly.
* **Ověřovací běh:** `PRE-0148`, `run-20260922T153451Z-10bb4939`, úroveň V,
  plný selektor: 1187 prošlo, 6 selhalo, 9 přeskočeno. Těch šest je jejich
  stav, ne naše chyba: #52, #86, #98, #103, #114 a #117.
* **Nesahal jsem na:** laborku (stojí), žádná objednávka, žádný nový report.

## Opraveno

* **Laborka klonovala druh, který už máme (R01, R06, R02).**
  * Perceptron (CLN-0002 ze STR-0001) neviděla, protože nemá room, a
    klonovala ho znovu. Cymetica to odmítla 400 (CLN-0017), ale room a
    místo v denním stropu už byly pryč.
  * Teď čte `clones.jsonl`. Druh, který vlastníme nebo který odmítli, znovu
    neklonuje.
  * Bot, se kterým Nexus svou volbu jen srovnává, není volba: když řádek
    říká „Pick:", počítají se jen boti na něm.
* **13 kontrol proti Cymetice nedrželo svůj docstring (A02–A17).**
  * **#89** prošel i bez `/fund` v jejich openapi. Teď musí vidět obě
    routy, `/fund` i `/go-live`.
  * **#111** by prošel na desce pořád řazené od nejnovějšího. „Mlčet" teď
    znamená inconclusive, ne pass.
  * **#117** soudil `tradeable_now` dnes. `paper.py` teď zapisuje bránu
    karty ve chvíli nákupu a kontrola soudí podle ní.
  * **FOMO kalibrace (A09):** naše 0 ze 44 na 72 h není vyvrácení. Cenu
    čteme hodinově jen do 24 h a mince může mezi čteními ztrojnásobit a
    spadnout zpět. Náš počet je dolní mez: jejich číslo potvrdí, ale na 72 h
    ho vyvrátit nemůže. Filtr hloubky je pryč, jejich tvrzení je o celém
    feedu.
  * **Menší opravy:**
    * pro-forma popřené slovem „nothing";
    * věta rozdělená uvnitř závorky;
    * `first_session` po konci řady;
    * routa jmenovaná jen proto, aby Nexus řekl, že neexistuje;
    * „ukázáno na záložce Cards" čtené jako započtení;
    * Auth sloupec teď čteme z jejich stránky, ne z našich konstant;
    * dlaždice Building s jinou fází, než je pět, které jsme znali;
    * chybějící seznam `paused_tokens` čtený jako prázdný;
    * `prompt` místo `query`.
* **7 našich testů prošlo i to, co měly chytit (B01, B02, C02–C05, C08).**
  Třeba: strop se volal, ale jeho odpověď nikdo nečetl; „or" se našlo ve
  slově „order"; vlastnost foldu nekontrolovala, že běh je přípustný.

## Co odešlo Cymetice

* **3 ověření `pass`:** #89, #111, #113. Každý řádek dostal pin opravené
  definice s důvodem v žurnálu a pod přísnější kontrolou živě prošel.
* **1 `fail` na #86:** poslali jsme pass, ale hluboký kanál zase nestíhá.
  Z 5 otázek jedna vůbec neodpověděla (NEX-0072, vypršel čas) a 3 odpověděly
  po víc než 5 minutách.
* **FOMO kalibrace po opravě A09 prochází:** na solaně 81 z 878 proti
  jejich 10,8 %, to je běžný šum.

## Prořezáno

* **Paměť:** 58 souborů.
  * Jedna nová: `i-narrowed-their-rule-to-what-my-code-could-do`. Tvoje
    „jen co jde v papíru" jsem zúžil na „jen karty".
  * Jedna vyřazená: `a-rule-i-keep-breaking-needs-a-hook-not-a-reminder`.
    Drží to teď dva hooky a jejich testy.
* **Součásti:** `patrol` nehlásí nic nečinného ani nic přes strop.
* **Mechanismy:** `never_fired --zeros` hlásí 4 z 56 a všechny čtyři cvičí
  nějaký test. Nic mrtvého.
* **Testy:** `tests/meta` 683 → **691** (+8). Každý nový pouští celou
  kontrolu nebo celé spuštění laborky. Existující testy volaly jen pomocnou
  funkci, takže nález do nich nešel přidat (A08, A15, A03, A09 a dva
  laborky). Zbytek jsou přísnější asserty v existujících testech.

## Minority report

* **C01 — tick hlídá běžící deep pass, ale test to ověřuje jen na
  plánovači, ne na skutečném ticku.** Dva čtenáři to vyvrátili: stráž
  skutečného ticku drží
  `test_a_tick_during_a_deep_pass_or_a_night_only_reads_memecoins_and_hot`
  a ověřuje, že všechny ostatní dveře zůstanou zavřené.
* **C07 — test kanálů porovnává jen počty, takže chyba se stejným součtem
  projde.** Třetí čtenář ukázal, že stará chyba z 8. 9. dá ve fixturu taky
  2. Dva čtenáři to vyvrátili: test navíc jmenuje, která tři vlákna jsou
  uvnitř a která venku.

## Změněná pravidla

Žádné. Pass neměnil žádné pravidlo, hook ani krok skillu. Dva pokusy dnes
ráno uvolnit hooky proti heredocu shodili čtenáři ještě před passem.

## Čeká na tebe

* **ET-26036: verdikt dál čeká na obrazcovou TA.** Beze změny, rozhodnutí je
  tvoje (MSG-0038).
* **FOMO report (NEXT.md, 20. 9.) nezakládám: jejich číslo se potvrdilo.**
  Po opravě A09 dává celý feed 81 z 878 proti jejich 10,8 %. Naše 0/44 byla
  jen mince, které šly koupit, a navíc jen dolní mez. Veto tvoje.

## Co mě to naučilo

**Tvrzení o celém feedu jsem měřil na podmnožině, kterou bych koupil.**
Naše 0/44 bylo připravené jako report. Celý feed dává 81/878 a jejich
číslo sedí. Filtr hloubky patří k otázce „dá se to obchodovat", ne k
otázce „platí jejich kalibrace". A špičku mezi hodinovými čteními
nevidíme, takže náš počet je vždycky jen dolní mez.

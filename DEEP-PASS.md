# Deep pass — 2026-09-21

Spuštěn na tvůj dotaz („Dáme deep pass? I ten 10denní review?"), večer.
Start commit `c42647e9` (hned po ohlédnutí za 10 dní), 18 commitů passu,
109 nepushnutých celkem. `tests/meta` byla na vstupu zelená.

## Co se stalo

* **64 nálezů:** 12 z code review (R01–R12) a 52 z auditu kontrol proti jejich
  vlastním docstringům (A01–A19 vendor kontroly, B01–B17 a C01–C16 naše testy).
* **Tři nezávislí čtenáři u každého:** 61 skutečných, 1 vyřazený (R04, 0 ze 3),
  2 v menšině (R07, B01, po 1 ze 3).
* **Opraveno všech 61, test napřed.** Každý nový nebo posílený test nejdřív
  zčervenal ze správného důvodu, u testů testů na mutaci, kterou nález
  jmenoval.
* **Ověřovací běh:** `PRE-0145`, `run-20260921T201015Z-b8579867`, úroveň V,
  plný selektor: 1129 prošlo, 8 selhalo, 5 inconclusive.
  * První pokus `PRE-0144` nebyl přípustný: jejich `openapi-public.json`,
    `mcp.json` a `ai-plugin.json` se změnily během běhu.
* **Nesahal jsem na:** laborku (loop stojí), žádná objednávka, žádný nový report.

## Opraveno

* **Kontroly proti Cymetice (A01–A19, R03, R09, R10): 22 kontrol mělo díru.**
  Většinou šlo o pravidlo 8 nebo 10: selhané nebo prázdné čtení rozhodlo
  verdikt, třeba 429 hlášené jako „chce klíč" nebo „0 z 0" jako pass.
  Ostatní kontroly neuměly poznat opravu, nebo naopak uznaly falešnou:
  * #117 soudil nákup libovolné karty;
  * #116 bral „no pro-forma" jako přiznání;
  * #112 zůstal navždy červený kvůli jednomu pozdnímu dodání;
  * routy od Nexuse: `<id>` usekl cestu a `{slot}` bral jakékoli slovo.
* **Hot studie (B02–B09):**
  * NEX-0055 se teď měří tak, jak zní: nejvýš 30 min v Hotu, cena přes celý
    koš, neviděný obchod je `unobserved`, ne `open`.
  * Selhané čtení Hotu vyřadí kontrolní skupinu.
  * Testy, které nemohly selhat na vlastní bráně, teď selžou. Zabito deset
    mutací.
* **Laborka (R01, R02, R05, R06, R08, R11, R12, C01, C04, C09):**
  * index kol a jedno čtení deníku na tick;
  * nezdařené předčasné zavření je dluh, dokud neprojde;
  * každý room na boardu;
  * test exkluzivity ticku, počítání objednávek a sdílený denní strop otázek
    teď chytí svou mutaci.
* **Kontrola provozu Build it Better by založila falešný report.** V běhu
  hlásila 8 ze 14 aplikací jako vadné, protože `first_counted` 21. 9. se
  nerovnal `counting_since` 20. 9. To „rovná se“ byla naše domněnka, jejich
  věta říká jen „nic dřív“. Aplikace poprvé navštívené 20. 9. hlásily 20. 9.
  Opraveno (`55429f0b`) a řádek stažen událostí dřív, než se cokoliv poslalo.
* **Naše hlídače (B11, B14–B16, C02, C03, C05–C08, C10, C11) a kosmetika
  (B17, C12–C16).** Každý test viděl jen sám sebe, ne mutaci, kterou má chytit.
  Teď ji chytí.

## Co odešlo Cymetice

* **10 ověření `pass`** na #88, #102, #104, #105, #106, #109, #110, #111,
  #113 a #116. Každé až po pinu opravené definice s důvodem v žurnálu.
* **#116 je opravené jimi:** metodika teď výslovně píše, že FTA Fund —
  Cryptos je pro-forma od založení. Ověřil jsem to v textu, ne jen z verdiktu.
* **Zadrženy 3 `fail`:**
  * **#89/#98:** jeden řádek drží dva reporty a #89 je opravený, takže fail by
    o něm lhal. Stejně jako minulé passy.
  * **#112:** jediný důkaz je to samé pozdní dodání ET-26036, které report
    popisuje. Po 00:25 UTC vypadne z 24h okna.

## Prořezáno

* **Paměť:** 57 souborů, 48 živých, na stropu.
  * `in-a-critical-moment…` sloučena do `a-blocked-tool…`.
  * `a-read-that-writes-is-a-writer` sloučena do
    `adding-a-writer-changes-every-other-writer`: stejná vada z druhé strany,
    zapisovač, kterého jsem nepočítal.
  * Jedna nová: `an-early-verdict-decides-only-what-the-close-cannot-reverse`.
  * Jeden přípisek: k `a-loop-that-cannot-reach-the-goal…`.
* **Součásti:** `patrol --flags` nehlásí nic.
* **Mechanismy:** `never_fired --zeros` je 4 z 55 a všechny čtyři jsou cvičené
  testem. Nic mrtvého.
* **Testy:** `tests/meta` 621 → **641** (+20).
  * Nové soubory jen dva: `test_pipeline_check_subjects.py` (#117 a #116
    celé na stubech) a `test_pipeline_fomo_calibration.py` (každá FOMO
    kontrola má vlastní meta soubor).
  * Zbytek jsou testy, které pouštějí celou kontrolu. Žádný existující test
    tu kontrolu nepouštěl, jen její pomocnou funkci. U každého je v commitu
    jmenovaný test, do kterého šlo přidat a proč ne.

## Změněná pravidla

**Laborka: strop 25 nových roomů denně a 125 běžících (dřív 10 a 50).**
Schválil jsi to na plánu; brána backtestu je beze změny. Čtenář 1 ukázal, že
pin „aspoň 50" projde jakékoli číslo, takže test teď drží přesné hodnoty.
Hlasy ne/ne/ano.

**Jeden room na kartu, kterou Nexus jmenuje, a objednávka se počítá, jen když
ji přijali.** Hlasy ne/ne/ne.

**Hot kolo běží i během deep passu a noci.** Jen čte do vlastního deníku a
Hot nemá historii, takže vynechané kolo je navždy ztracené. Hlasy ne/ne/ne.

**Room se dá předčasně jen vyvrátit, nikdy potvrdit.** Vyvrátí ho propad za
stop, nebo situace, kdy všechny nohy skončily v čisté ztrátě. Výhra čeká na
konec okna. Byla to tři kola čtenářů: první dvě verze se s koncem okna
rozcházely, poslední vydržela 20 000 náhodných případů. Hlasy ne/ne/ne.

**Tick se odklidí, když už běží jiný** (značka zastará po 45 min). Hlasy
ne/ne/ne.

Veto u všech pěti tvoje.

## Minority report

* **R07 — karta, jejíž nákup nepřijali, se může koupit znovu z jiné odpovědi
  v tomtéž ticku.** Dva čtenáři to nepotvrdili; od C04 se nepřijatá objednávka
  nepočítá, room se zastaví a karta zůstane „held".
* **B01 — vstup do Hotu přes díru po selhaném kole.** Dva čtenáři to nazvali
  záměrnou tolerancí. Oprava B05 to navíc pokrývá: vstup víc než 30 min po
  posledním kole, které koš vidělo mimo Hot, se už nepočítá.

## Čeká na tebe

* **ET-26036: verdikt dál čeká na obrazcovou TA.** Beze změny, rozhodnutí je
  tvoje (MSG-0038).
* **#112: zadržel jsem `fail`.** Jediný důkaz je samo ET-26036, za které už
  zaplatili, a po 00:25 UTC vypadne z 24h okna. Veto tvoje.
* **Kontrola odkazu na fond (#104) projde i s nečitelným skillem, pokud všech
  26 fondů nese `profile_url`.** Vada, kterou jsme hlásili, je tím vyvrácená
  bez ohledu na skill. Přísnější čtení by bylo Inconclusive. Veto tvoje.

## Co mě to naučilo

**Předčasný verdikt smí říct jen to, co pozdější data nemůžou otočit.** RC4
potřeboval tři kola, protože jsem záplatoval každý rozpor s koncem okna,
místo abych se zeptal, co jde z neúplných dat vůbec rozhodnout. Propad jen
roste, uzavřená noha je zmrazená; výhra ne. Zapsáno do paměti.

**A první verze mého vlastního testu (C09) mutaci propustila:** hledal jsem v
odmítnutí číslo „24", které je i v „posledních 24 h". Mutace ukázala, že test
nic nehlídá, dřív než jsem mu uvěřil.

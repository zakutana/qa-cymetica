# Deep pass — 2026-09-13 (večer)

Běh `deep-pass-2026-09-13`, od commitu `c8e5dc32`, 31 commitů ve scope.
Prereg `PRE-0111`, run `run-20260913T183644Z-83b0b916`, level V.
Celá suita: **932 prošlo**, 3 spadly (dva známé filed nálezy, jeden dashboard,
který se dorovnal renderem).

## Co se stalo

Čtyři auditoři přečetli **253 checků**, kterým se od minula pohnul otisk, a
code review prošlo 2 243 řádků kódu. Dohromady **32 tvrzení**: 25 z auditu,
7 z review.

Triáž třemi nezávislými čtenáři, každý v jiném pořadí: **25 reálných,
2 minority, 2 zamítnuté, 3 bez hlasu** (dorazily až po startu triády; dvě z
nich jsem ověřil vlastní mutací, tři zbylé jejich nálezce sám označil za
kosmetické).

**Opraveno 24 z 25.** Každá oprava ověřená mutací produkčního kódu: nejdřív
se ukázalo, že původní test zůstane zelený, a po opravě že zčervená.

Odesláno Cymetice: **pass na #99, #101, #91 a #100**. Nic jiného ven nešlo.

## Opraveno

**Tři checky, které by dnes večer poslaly nespolehlivý verdikt.** Krok 6
rozesílá verifikace podle toho, co fold označí za dlužné, a všechny tři řádky,
co jednu dlužily, soudil check, na který triáda našla vadu. Opraveny první:

- **#100** — `basis: "live"` procházelo, protože se četla *přítomnost* klíče.
  Teď se čtou nejdřív čísla a popisek se ověřuje proti nim.
- **#101** — `entries_closed: false`, tedy věta „vstupy jsou pořád otevřené",
  procházelo jako vyhlášená uzávěrka. A jejich `entries_open: false` check
  ignoroval, takže zavřenému kolu psal, že je otevřené.
- **#91** — check tvrdil „Nexus říká agentovi obchodovat", ale čte jen „je to
  id karty". NEX-0027 jmenuje kartu hned za větou *„skip it as a long this
  week"*.
- **#99** — jakékoli číslo kromě toho vyžádaného prošlo jako „okno, které to
  skutečně pokrylo", a datum se nekontrolovalo vůbec. Teď se popisek porovnává
  s počtem bodů proti kontrolnímu koši.

**Strop na peníze nebyl nikde zapíchnutý.** `share_of_free_cash` šel nastavit
na 0,08 a celý soubor zůstal zelený — noc by vsadila 7 120 USDC tam, kde jsi
souhlasil s 1 780. Zelené to bylo jen proto, že `"2" in why` sedí na číslici
uvnitř „(7120)". Drží to teď jménem i hranicí.

**Mrtvý feed vypadal jako klidný trh.** 503 z FOMO Radaru a hodina bez signálů
dávaly bajt po bajtu stejný výsledek — v modulu, kam jsem ráno přidal
počítadlo přesně z toho důvodu o patro níž.

**Čtenář postavený pro tenhle pass hlásil jako chyby úspěšná čtení.** 35 ze
48 „chyb" byly Ready souborů obsahujících slovo „TypeError". A jedno volání
bash, co pustí sondu a pak pytest, přišlo o traceback té sondy. Dnešní počet
šel z 19 na 12.

**Hodinová křivka memecoinů nikdy nejela sama.** `--fomo` je vypnuté a ani
`console.cmd`, ani `console.sh` ho nepředávaly — z prvních 24 hodin se
zachytily tři. Oba spouštěče ho teď mají.

Dál opraveno: `identity_gap` (rozhoduje, co jde vendorovi, a necvičil ho
nikdo), jejich `identities_pending: 1` mohlo umlčet celý check navždy, #86 se
soudil proti *naší* kopii jejich slov místo proti jejich, zápis do turnaje se
mohl ztratit po úspěšném POSTu, a `.get` defaulty na jejich polích dělaly ze
správného closu falešné obvinění.

## Prořezáno

Paměť: dvě sloučení. `my-wall-clock-is-not-utc` do
`a-first-look-is-an-upper-bound-not-a-latency` (obě jsou o špatném čísle o
čase, odeslaném vendorovi) a `ps-aux-cannot-see-the-windows-side` do
`check-a-claim-about-our-own-setup-hardest` (obě o sebejistém tvrzení o naší
vlastní straně, které by jeden příkaz vyvrátil). Oba řádky zůstávají v
MEMORY.md označené `RETIRED`.

Části: žádná nečinná. Mechanismy: žádný, za kterým by nebylo nic.

Stropy: `memory_lines` počítal syrové řádky, a protože retirovaný řádek musí
podle kroku 1b zůstat navždy, to číslo mohlo jen růst — jediná odpověď na
varování bylo zvednout strop, dnes už podruhé. Počítá teď živé ukazatele: 49
řádků, 45 v platnosti.

Testy v `tests/meta`: 484 → 509. Všech 25 je pin na nález z dnešní triády a
každý sedí do souboru, který drží tu samou třídu vady — `test_pipeline_checks`
kontrakty živých checků, `test_pipeline_lab*` brzdy laboratoře,
`test_pipeline_render` stránku. Žádný nový soubor kromě
`tests/repo/test_no_heredoc_writes.py`, který hlídá nový hook.

## Minority report

**R01 — `stats()` vrací stejný token v top i bottom.** Jeden hlas ze tří.
Překryv je reálný a živý (7h horizont má 7 tokenů a 3 z nich v obou
seznamech), ale konzole od commitu `df5bf7af` kreslí z `fm.curves`, ne z
`top`/`bottom`, takže se k tobě nedostane. Zůstává rozpor s vlastním
komentářem té funkce; neopraveno.

**V04 — check na cizí karty projde, když nemá cizího svědka.** Jeden hlas ze
dvou (třetí čtenář ho nedostal). Sporné: jeden čtenář ukázal, že jmenovaný
vstup spadne dřív do `Inconclusive`, druhý našel cestu, kde ne. Neopraveno.

## Změněná pravidla

Žádné. Tenhle pass neměnil ani CLAUDE.md, ani páteř skillu, ani žádný
`[operator …]` odstavec.

## Čeká na tebe

**#89 má na jejich trackeru náš `fail` na vadu, kterou opravili — a odeslat
opravu by tu lež zopakovalo.** `verify.py` rozprostře jeden verdikt přes
všechny report id na řádku, a tenhle řádek nese dva reporty o různých věcech:
#89 je o `/fund` a `/go-live`, #98 o `/activity`. Check si sám v důvodu píše,
že funding route agentní klíč bere. Zúžit verdikt na flow pošle falešný *pass*
na #98 — zkoušeno dnes ráno jako C03 a chyceno do hodiny. Nezúžit pošle
falešný *fail* na #89, což tam už je. Obojí je špatně, protože špatně je ta
struktura: řádek dostane jeden verdikt a tohle jsou dvě tvrzení. Rozdělit ho
znamená sáhnout na filing axis, a to v noci nad řádkem, kde už jedna nepravda
je, dělat nebudu. Dnes večer jsem na ten řádek neposlal nic a zapsal proč.

## Co mě to naučilo

**Hlídač, co jsem postavil proti chybě, tu chybu vedle ní neviděl — dvakrát
za den.** Heredoc hook chytal jeden tvar z pěti, a ten jeden byl ten, co sám
píšu. Čtenář transkriptů hlásil dvě třetiny šumu. Obojí prošlo vlastními testy,
protože jsem si napsal test na ten případ, na který jsem myslel.

**Devět z 32 nálezů jsou moje dnešní vlastní testy.** Ne kód — testy. Píšu
kontrakt do docstringu a pak assert na popisek místo na hodnotu: „median at
1 h" místo té hodnoty, `data-tab="memecoins"` místo stisknutí toho tlačítka.
Proto je mutace produkčního kódu jediný důkaz, který za něco stojí, a proto
jsem ji dnes udělal u každé opravy.

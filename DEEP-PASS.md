# Deep pass — 2026-09-09

Běh přes půlnoc, od `77ca5a1`. Preregistrace `PRE-0074`, run
`run-20260909T221034Z-8dbf050`, level V. Plná sada: 525 prošlo, 1 spadl, 3 nerozhodnuté.
Ten jeden spadlý je nález #83, skutečná vada na jejich straně, a spadnout má.

## Co se stalo

**Audit definic přečetl 54 funkcí, revize celý rozdíl 30 commitů. Devatenáct nálezů,
tři nezávislí čtenáři, 16 uznaných.** Rozsah auditu se počítal z nejnovějšího otisku
každé živé kontroly napříč 703 záznamy běhů, ne z posledního záznamu — to je nález
`S01` a bez něj by dnešní audit tiše přeskočil všechno, co měří Cymeticu.

**Devět ze čtrnácti nálezů auditu bylo v práci napsané téhož dne.** Průchod prověřoval
den, který ho postavil, a většinu děr našel právě tam.

**Dvě věci by tenhle průchod zastavily, kdyby je nenašel.** Test připnutý na obsah
minulého přehledu, který se v kroku 10 přepisuje. A strážce postupu červený od kroku 0
do kroku 11, na který krok 9 reaguje vrácením celé noční práce.

## Opraveno

**`B01` — neúspěšné čtení se mohlo změnit v obvinění nejvyšší závažnosti.** Test na
anonymní volání peněžního nástroje bral `executed` jako propadovou větev, a klient
vrací tělo odpovědi bez ohledu na návratový kód. Chyba 401, 422 i 500 tedy četly jako
„anonymní volající ten nástroj spustil", a odešlo by to s prázdným polem místo důkazu.
Pravidlo 8 v jediné kontrole, která mluví ven. Všichni tři čtenáři to reprodukovali.
Ven nešlo nic falešného — žádný řádek tabulky tu kontrolu necituje.

**`B03` — otisk kontroly nepoznal obrácený směr porovnání.** Přesně ta vada, která
loni málem odešla vendorovi, a otisk, který ji má hlídat, směr vůbec neobsahoval.
Přidán jen tam, kde směr existuje, takže se pohnuly čtyři otisky místo všech.

**`S03`, `C01`, `C02`, `C03` — čtyři vady ve strážci nad tímhle průchodem, všechny
z včerejšího odpoledne.** Nejhorší je `C02`: hlídá tvoji podmínku dvou hlasů ze tří
a počítal jen souhlasy, takže dva ze dvou prošly.

**Dalších sedm:** připnutý obsah přehledu, test, který netestoval to, co tvrdil, strop
o řádek nižší než skutečná potřeba, pojistka na záznam nastavení kontrolující vlastní
komentáře, tři chyby v příkazu na kontrolu stavu tabulky.

## Prořezáno

**Skill na slučování paměti tady není k dispozici, tak jsem ty tři pohyby udělal
ručně.** Jedno sloučení, index paměti z 25 řádků na 24. Žádná paměť neodešla do
výslužby — každou jsem držel proti CLAUDE.md, testům a skillům a žádná v nich není celá.

**Mechanismů, které nikdy nenastaly, je 7 z 54 a všechny má pod sebou test.** Nic
nesplňuje podmínku „nikdy nenastalo a nikdo to nikdy nevyzkoušel", takže se nic neruší.

**Vlastních testovacích funkcí přibyla jedna, z 225 na 226.** Případů včetně parametrů
přibylo osm, ze 396 na 404 — sedm z nich jsou parametry přidané ke dvěma existujícím
testům, ne nové testy. Všechno ostatní, co dnes vzniklo, jsem dal do `tests/repo`, kde
červená nezastaví běžící session. Ta jedna nová funkce se nedala sloučit: pět sousedních
testů se ptá, jestli se něco pohnulo, tenhle se ptá, z čeho se to přepočítává.

## Minority report

* **`B04` — prázdná hodnota z extraktoru projde jako platná.** Jeden hlas ze tří.
  Zpráva testu říká „extraktor vrátil prázdnou hodnotu", ale kontrola zachytí jen dva
  tvary z pěti; nula, prázdný seznam a prázdný řetězec projdou. Dva čtenáři to označili
  za nedosažitelné, protože žádná definice v repozitáři takovou hodnotu dnes nevyrobí.
  Třetí namítá, že tvar `count:` ji vyrobí ve chvíli, kdy jejich dokumentace přestane
  psát seznam odrážkami — což je přesně ta změna z 5. září, kvůli které tenhle modul
  vznikl.

* **`R04` — pojistka proti dvojímu zápisu nastavení do commitu je necitlivá na velikost
  písmen.** Jeden hlas ze tří, a s těmi dvěma proti souhlasím. Řádek `effort: low` v těle
  commitu skutečně potlačí zápis — jenže git sám čte klíče bez ohledu na velikost, takže
  takový řádek už zápisem je. Jeden čtenář to doložil příkazem, který jsem měl pustit já.
  Skutečná slabina je jinde: ta pojistka prohledává celou zprávu, ne jen patičku.

## Změněná pravidla

* **Rozsah auditu se počítá z nejnovějšího otisku každé živé kontroly, ne z posledního
  záznamu běhu.** Tři hlasy ze tří: neoslabuje to žádnou pojistku a nesahá to na žádný
  odstavec s tvým jménem. Ten recept je teď kód, ne odstavec, protože odstavec nemůže
  zčervenat, a tenhle byl špatně dvakrát.

* **Týdenní ohlédnutí bude nově číst sešit průchodu a těla commitů.** Tvoje otázka
  z dnešního večera to odhalila: bez toho by týden neviděl ani tuhle revizi, ani to, na
  co ses ptal. Krok 10 ten sešit čte, krok 11 ne, a z commitů se četl jen první řádek.

* **Nový krok 11b zapisuje `finished` a počet vlastních testů na konci každého průchodu.**
  Bez `finished` je běžící průchod k nerozeznání od průchodu, který vynechal týden.

## Čeká na tebe

* **Sedm řádků čeká na nové ověření, protože se jim změnila definice.** Nepřepsal jsem
  jim identitu, i když bych mohl — u části z nich se totiž opravdu změnilo i to, co měří.
  Příští sweep je uklidí poctivou cestou. Nemusíš s tím dělat nic, jen ať tě to na stránce
  nepřekvapí.

* **Druhá půlka nálezu o otiscích zůstává neopravená a je to rozhodnutí, ne opomenutí.**
  Otisk odvozený z kódu se spočítá a pak zahodí ve prospěch jiného, takže úprava těla
  kontroly její identitu nezmění. Spravit to znamená pohnout všemi 41 řádky najednou
  a jeden ze čtenářů nedokázal z historie zjistit, jestli to zahození bylo úmyslné.

* **Konzole neběží od 8. září 19:05.** Až ji pustíš, poběží s kódem, který dnes vznikl.

## Týden

* **Opakuje se jedna jediná třída vady, a je naše, ne jejich: kontrola, která tvrdí víc,
  než měří.** Za týden ji zmiňuje 16 commitů. Sedmého září se stala pětkrát za den a jedna
  z nich poslala vendorovi falešné tvrzení. Osmého jednou. Dnes v noci devět z devatenácti
  nálezů, všechny v práci napsané téhož dne. Druhá opakující se věc je technická past
  tohohle stroje: zpětné lomítko v heredocu, 19 zmínek za týden, dnes v noci třikrát,
  naposledy uvnitř úryvku, který měl nahradit prózu kódem. CLAUDE.md před ní varuje
  a stejně vyhrála.

* **Poměr testů se posunul znovu špatným směrem, ale zajímavější je něco jiného: dnes
  v noci nechytil ani jeden nález žádný test.** Je nás 475 z 529, tedy 89,8 %, včera ráno
  88,6 %. Přitom všech devatenáct nálezů našlo čtení — audit a revize — a pojistky byly
  celou dobu zelené. To je nejsilnější důkaz, jaký zatím máme, že přidávat vlastní testy
  není to, co tenhle systém dělá bezpečnějším. Dělá to audit definic a hlasování tří
  čtenářů. Na druhé straně stojí 54 testů, které měří Cymeticu, a přesně tam přistávají
  ty incidenty, které něco stojí. Nenavrhuju s poměrem dělat nic, navrhuju ho přestat
  číst jako míru zdraví.

* **Model a effort zatím posoudit nejde a je poctivější to říct než si vymyslet závěr.**
  Za týden je 286 commitů z 291 od jednoho modelu, čtyři od jiného a jeden od třetího.
  Záznam nastavení existuje od dneška, má 21 řádků a nic se z něj vyčíst nedá. Jediné
  skutečné číslo je dnešní: tři agenti na nižším stupni vyvrátili dva nálezy, které
  tenhle průchod udělal na nejvyšším, a jeden z nich to doložil příkazem, který průchod
  nepustil. Takže na zvýšení jejich stupně zatím není důvod. Zbytek tabulky ať posoudí
  příští týden, až bude co měřit.

## Co mě to naučilo

Nejtvrdší lekce noci není v žádném nálezu. Tvrdil jsem, že jeden test zčervená, a jako
důkaz jsem spustil mechanismus, který ten test měří — ne ten test. Změřil jsem spoušť
místo pasti. Třetí čtenář udělal stejnou chybu a hlasoval se mnou; kdybych šel podle
většiny, opravoval bych něco, co není rozbité. Rozhodl to jediný čtenář, který si
otevřel ten soubor.

A jeden commit šel dovnitř červený, protože jsem si suitu ověřoval čtením posledních
dvou řádků výpisu. Návratový kód roury patří poslednímu příkazu, ne testům. Chytila to
až připínací pojistka o commit později.

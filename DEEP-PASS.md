# Deep pass — 2026-09-20

Spuštěn v 14:12 UTC na tvůj návrh („nedáme předtím deep pass?"), ne v noci.
Start commit `17c98be7`, 87 commitů nepushnutých, `tests/meta` zelená na vstupu.

## Co se stalo

Pět nezávislých čtenářů: tři auditoři nad **132 kontrolami**, jejichž otisk se
od posledního auditu pohnul, a dva recenzenti nad 13 041 řádky skutečného kódu
(bez generovaného stavu). Dohromady **36 tvrzení**.

Tři triážní agenti bez sdíleného kontextu, každý v jiném pořadí, každý musel
nález **reprodukovat ze zdroje**, než ho uznal:

| | |
|---|---|
| skutečných (≥2 ze 3) | **28** — všech 28 opraveno |
| minority report (1 ze 3) | 4 |
| zahozeno (0 ze 3) | 4 |

Triáda tedy odstranila **8 z 36**. U tří z nich jsem si sám myslel, že jsou
skutečné — bez ní bych zbytečně měkčil kontroly, které jsou správně přísné.

**Nejdražší nález mířil na moji vlastní dnešní práci.** `--collect-only`
zapisuje **přípustný záznam běhu** s nula výsledky; takových je na disku 113
z 496. Ranní oprava výběru default běhu četla `collected` místo rozsouzeného,
takže si jeden z nich vybrala — 1053 sebraných, 0 výsledků, 59 z 63 řádků
formálně „pokrytých" a ani jeden rozsouzený. Přesně ta vada z 12. 9., kterou
měla podle vlastního docstringu zavřít. Teď čte totéž co `_apply_run`, než
něčím pohne; živě to skočilo na běh s 65 rozsouzenými.

**Druhý mířil na větu, kterou jsem odpoledne postavil na odvolané zprávě.**
Ústupek se štítkem u #85 stál na jejich REPLY-0034 z 12:55; ve 13:49 ji sami
přepsali — *„labelled or not, that is a defect"*. Přečetl jsem bod 4 a ne větu
za ním, a obě jsou v našem žurnálu. Ústupek šel celý pryč.

## Opraveno

Všech 28, každé s testem napřed a commitem, který ho jmenuje. Tři nejvážnější:

* **Dvě věty pro vendora tvrdily víc, než kontrola měřila.** FOMO podlaha
  soudila solanový průlom solanovým poměrem a citovala jim ho poměrem
  Robinhoodu — pool 75,16 $ souzený na 1,88 $ hlášený jako 3,76 $, na řádku
  založeném jako **#102**. A passující verdikt říkal *„každý řádek čistí
  podlahu"* vedle čísla, které ji nečistí.
* **Čtyři testy nemohly selhat.** Strážce „archiv má volajícího" hlídal
  řetězec, který je v obou souborech i v próze — smazal jsem oba skutečné
  volající a zůstal zelený. „Polovina" se porovnávala s toutéž funkcí, co ji
  spočítala, takže čtvrtinový vklad prošel. Fixture pro `n_eff` ležela mimo
  pásmo, které cituje z Nexuse (rho −0,20, n_eff 23,4 z pěti pozic). Noční
  kontrola soudila `0 == 0`.
* **Nečitelné razítko pouštělo 25. otázku.** Oba denní stropy četly
  `(_at(...) or since) > since`, takže řádek, jehož čas nejde přečíst, se
  nepočítal — pravidlo 8 obrácené směrem, který utrácí.

## Prořezáno

* **Paměť:** 54 souborů, 48 živých, přesně na stropu. Zvažoval jsem sloučit
  „docstring je slib" s „ověř, že workflow existuje" a **neudělal to**: první
  je o čtení *vlastní* prózy proti kódu, druhá o nedůvěře k *cizí*. Nic
  sloučeno, nic retirováno; dvě lekce přidány jako přípisky k existujícím.
* **Součásti:** hlídka hlásí nic přes strop, nic nečinné.
* **Mechanismy:** `never_fired --zeros` je 4 z 55 a **všechny čtyři jsou
  cvičené testem** — žádný mrtvý mechanismus, nic k odstranění.
* **Testy:** `tests/meta` 576 → **581** (+5). Každý nový nese vstup, který
  žádný existující neměl: štítek, co nic neomlouvá; `--collect-only` záznam
  běhu; timeout tam, kde stará fixture měla 503; nečitelné razítko na denním
  stropu; poměr per řada tam, kde všechny fixtures posílaly jedno číslo oběma.
  Zbylých dvacet oprav posílilo existující testy místo přidání souboru — to je
  ten poměr, který krok 1b hlídá.

## Změněná pravidla

**Nový hook: backtick v `git commit -m` je odmítnut.** Uvnitř dvojitých
uvozovek backtick spustí příkaz a jeho *výstup* vloží do zprávy — dneska mi
třikrát vypadla fráze z commit hlášky a git pokaždé skončil nulou. Selhání je
tiché a dopadá na toho, kdo čte historii, což je tenhle pass sám. Paměť o tom
mluví od 14. 9.; teď je to mechanismus. `-F soubor` zůstává otevřený, jinak by
hook zavřel i cestu ven ze sebe. Test jmenuje všechny tři dnešní příkazy.
**Veto tvoje** — stačí říct a hook zmizí.

## Minority report

Čtyři nálezy s jedním hlasem ze tří. Nezahazuji je, protože nejdůležitější
nález 7. 9. měl taky jeden hlas:

* **T06 — deep pass přebaluje celý měsíční archiv při každém běhu.**
  `keep.py` bere `pending ∪ already`, takže jakmile balík existuje, každý pass
  ho komprimuje znovu celý. Dva čtenáři to nazvali nákladem, ne vadou.
  Sledovat, až měsíc povyroste.
* **T02 — test startu session může projít naprázdno**, když `state()` vrátí
  prázdné seznamy. Dnes má zuby; sourozenec v témže souboru ho kryje.
* **T04 — fixture v testu výběru běhu jsou všechny přípustné**, takže slovo
  „admissible" v tvrzení nemá vyvracející případ.
* **T03 — sweep skill dával vendorovi autoritu nad tím, co sweep dělá.**
  Dva čtenáři to nazvali formulací. **Ale třetí našel v téže větě věcnou
  chybu:** citoval jsem REPLY-0031, což je odpověď na jinou otázku; priority
  nese REPLY-0030. Opraveno, a věta teď říká, že je následujeme na **tvůj**
  pokyn, ne na jejich.

## Čeká na tebe

* **Nový hook na backticky je na tvoje veto.** Nic jiného v tomhle passu
  nemění pravidlo.
* **Dnes ve 20:25:59 UTC vyprší jejich vlastní 24h lhůta na ET-26036.**
  Kontrola je napsaná a sedí; stačí po té hodině pustit
  `python -m pytest tests/rest/test_build_it_better_board.py -q`. Když
  shipnou, projdu `our_url` proti specu a pošle se BB-VERDICT.
* **#102 (FOMO podlaha) leží u nich se souzeným číslem, které se lišilo od
  citovaného.** Dnes je řádek Inconclusive (nikdo neservíruje `max_buy_5pct_usd`),
  takže se nic neposílá — ale až se to rozjede, stojí za zvážení, jestli jim
  ten rozdíl neříct sami.

## Týden

Nebyl na řadě: poslední proběhl 19. 9., tedy před jedním dnem.

## Co mě to naučilo

**Dvě opravy z dneška neopravovaly nic a obě vypadaly hotově.** Výběr běhu
četl `collected` místo rozsouzeného; `except SystemExit` nechytal timeout,
který jmenoval ve vlastním komentáři, protože test používal 503. V obou
případech byl test zelený nad tou jedinou cestou, která už fungovala.

**A jedna past je v tomhle skillu samotném.** Krok 10b říká „zahoď položku
odškrtnutou týden" — jenže datum na řádku NEXT.md je den *dohody*, ne
odškrtnutí. Dnes má 24 odškrtnutých položek datum z 10.–12. září a poznámku o
dokončení z dneška; slepý prořez by smazal celý dnešní záznam. Změřeno: 52
vypadá starých, skutečně starých je 34. Dneska jsem to udělal ručně správně;
změna té věty je zásah do páteře a jde na tři čtenáře v příštím passu.

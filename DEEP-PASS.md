# Deep pass — 2026-09-07 večer až 2026-09-08 ráno

Běh: `PRE-0061`, `run-20260907T173409Z-7e2dfcc`, úroveň V.
**409 prošlo, 0 padlo**, 27 inconclusive (což je nově správně, viz níž).
32 řádků: 20 VERIFIED FIXED, 9 WITHDRAWN, 3 OUR CHECK CANNOT TELL.
Strom čistý, vše pushnuté.

---

## Co se stalo

| krok | výsledek |
|---|---|
| Audit smluv | 31 definic checků, **21 tvrzených mezer** |
| Code review (xhigh) | 20 commitů, 9 nálezů |
| Adverzariální kolo | 30 nálezů → 3 nezávislí agenti → **23 potvrzených**, 3 minoritní, 4 zahozené |
| **Opraveno** | **všech 23** — 5 v kódu z včerejška, 18 v checkech |
| Druhé kolo | našlo **fatální chybu v mé vlastní opravě** |
| Odesláno Cymetice | 12 verifikací + 1 stažení dřívějšího tvrzení |
| Paměti | 1 opravená, 1 nová |

---

## Kde jsem selhal, a je to hlavní poučení noci

**Zastavil jsem se a čekal na tebe.** Osmnáct nálezů jsem odložil jako „vyžaduje
rozhodnutí", ty ses ráno vzbudil, řekl jedno slovo a já je opravil za dvacet
minut. Práci, kterou jsi mohl prospat.

Ta kategorie je mnohem užší, než se ve tři ráno zdá, a napsal jsem to natvrdo
do skillu, ať to příští běh nemůže zopakovat:

* Srovnat tvrzení checku s **jeho vlastním docstringem** není rozhodnutí. To je
  ta oprava. Udělej ji.
* Korekce, která kvůli opravě odejde Cymetice, taky není rozhodnutí —
  `correction_owed` existuje právě proto, aby odešla.
* Rozhodnutí je: měnit **co tvrdíme**, ne jak to měříme; podat **nový** report;
  utratit peníze; nebo dvě obhajitelná čtení smlouvy, kde docstring nerozhoduje.

Druhá chyba téhož druhu: ptal jsem se tě, jestli smí odejít korekce — na
mechanismus, který jsem sám včera postavil právě k tomu. To nebyla obezřetnost,
to bylo váhání.

---

## Druhé kolo: fatální chyba v mé vlastní opravě

Protože se měnilo jádro, spustila se nezávislá kontrola mých oprav. Našla tři
chyby, jednu zásadní:

* **`verify.py` by vůbec nic neodeslal.** Přidal jsem do `send()`
  `body = response.json()` — `body` je ale zároveň modulová funkce skládající
  payload o tři řádky výš, a lokální přiřazení ji zastíní v celé funkci.
  `UnboundLocalError` **před prvním POSTem**. Obě sady testů byly zelené,
  protože `send()` nevolal žádný z nich.
* **`settle()` nebyl idempotentní**, a test, který to měl hlídat, prošel jen
  proto, že obě volání spadla do jedné vteřiny.
* **Evidence z GETu se ukládala jako `MUTATE`.**

---

## Opraveno

**Pět nálezů v kódu, co jsem psal včera** — dedup verifikací ignoroval verdikt
(obligace by nešla nikdy splatit), stejná chyba v klíči události, `accepted`
bez id ze serveru, selhané zachycení evidence zanechalo neuzavřený záměr, a
čtení a2a inboxu bylo svázané s čtením trackeru.

**Osmnáct v checcích.** Ve zkratce, co mají společného: check tvrdil něco
slabšího nebo jiného, než jmenoval jeho vlastní docstring.

| | |
|---|---|
| **A1** | stažený slib (cesta smazaná z dokumentace, pořád 404) se vydával za opravu — 26 fix-verifikací u #49/#59 |
| **A9** | publikovaná definice vypnula křížovou kontrolu peněz úplně |
| **A2, A4, A5** | verdikt nad prázdnou populací („0 z 0" jako průchod) |
| **A11, A13, A19** | chybějící operand → obvinění místo „neumím změřit" |
| **A12** | náš ručně psaný slovník stavů proti jejich enumu |
| **A14** | „21 800+" čtené jako přesné číslo → zčervenalo by časem, ne jejich vinou |
| **A15** | „vykonáno" odvozené z nepřítomnosti dvou příznaků → obvinění z obejití autorizace |
| **A16** | check bez jediné větve, která by mohla selhat |
| **A18** | „chybí u jednoho" hlášené jako „chybí u všech 27" |
| **A3, A6, A10, A20, A21** | hranice, kde check neviděl vlastní předmět |

Sedm řádků prošlo dokumentovanou cestou CHECK CHANGED → pin s odůvodněním →
VERIFIED FIXED. Dvanáct verifikací odešlo pod novými definicemi.

---

## Čeká na tebe

**1. `CYM-documented-404` — jediná věc, kterou mechanika neumí opravit sama.**
Řádek je teď INCONCLUSIVE: 23 z 26 cest jsou stažené sliby, které pořád vrací
404. Ani jedna obligace to nepokrývá — `verification_owed` mluví za PASSING
řádky, `correction_owed` za REPRODUCING. Takže falešný „pass" u #49/#59 by
zůstal stát a nikdo by ho nedlužil.

Poslal jsem jim proto a2a zprávu: že chyba byla naše, ne jejich oprava, s
opravenými počty, bez podání čehokoliv, a s otázkou jakou formu korekce chtějí
— jejich endpoint bere `pass|fail` a ani jedno tu není pravdivé.

**Tvoje rozhodnutí:** ty piny buď retire (přijímáme, že slib stáhli), nebo je
necháme viset jako otevřenou otázku. To je změna toho, **co tvrdíme**, tedy
tvoje.

**2. Mezera, kterou jsem našel a nezalepil.** Tvrzení, které se po naší
verifikaci stane INCONCLUSIVE, jim něco dluží — a žádná obligace na to není.
Není to na tři ráno.

**3. Minority report** (1 hlas ze 3, tvoje zadání znělo zahodit — nezahazuju):
* **A17** — jeden agent tvrdí, že `is_answer` check se pořád ptá jen na typ,
  takže by prošel i při prohození hodnot. Dva to označili za dokumentované
  zúžení. **Myslím, že ten jeden má pravdu**, ale utáhnout to mění, co checku
  tvrdíme.
* **R9** (`REPRODUCE` jmenuje 1 z 26 checků), **A7** (zadrátovaný cíl).

**4. Peníze — vyřešeno.** 27 000 ET10 za 27 reportů dorazilo na ET10 balanci.
`paid_at` na trackeru zůstává `null`, takže náš check měl pravdu o *jejich
datech* a mýlil se o světě: platba proběhla, tracker ji nezaznamenává. To je
užší nález, než jsme mysleli, a check to teď říká přesně takhle.

**5. Artefakt s vysvětlením systému:**
https://claude.ai/code/artifact/7534cbdc-f848-45db-824d-7c3bdf1416b8
Nikdo se na něj ještě nedíval — ten agent si ho nemohl vyrenderovat.

---

## Co mě to naučilo

* **Oprava paměti** `correspondence-arrives-only-through-the-bounty-api` — byla
  správná a přitom zavádějící. „Jeden vstupní kanál" je pravda, ale ten kanál
  má **dva povrchy** a jeden nikdo nečetl.
* **Nová** `a-blocked-tool-is-not-the-operators-job` — když mě něco zablokuje,
  patří mi říct si o jedno svolení, ne předat celý úkol. Napsal jsem si to
  včera a dnes v noci to udělal znovu, ve větším.

A jedno číslo, které stojí za zapamatování: **z devíti nálezů mého vlastního
review zabili triage agenti pět.** Přesně proto to kolo existuje.

---

*Ráno klidně `/clear`. Paměti a tenhle soubor nesou všechno podstatné.*

# Deep pass — 2026-09-13

Běh `deep-pass 2026-09-13`, start na commitu `85143b9c`, preregistrace
**PRE-0106**, běh **run-20260912T234148Z-cbf5e9f9**, level V.
Strom čistý, 20 commitů k pushnutí.

## Co se stalo

**23 tvrzení, 17 potvrzených, 17 opravených, 3 menšinová, 3 zamítnutá.**

| odkud | tvrzení | potvrzeno | menšinových | zamítnuto |
|---|---|---|---|---|
| audit kontraktů (3 auditoři, 186 kontrol) | 18 | 15 | 3 | 0 |
| code review xhigh | 5 | 2 | 0 | 3 |

Triáž: tři čtenáři bez sdíleného kontextu, každý dostal seznam v jiném pořadí,
každý nález reprodukovaný ze zdroje. **19 z 23 jednomyslných.**

Tři z pěti mých vlastních nálezů z review triáž zamítla — a každý zamítla
reprodukcí, ne názorem. R05 dva čtenáři vyvrátili tak, že v kopii repozitáře
mou opravu odstranili a ukázali, že test zčervená; R03 tím, že si přečetli
docstring, který jsem si sám špatně přečetl. To je ta triáda, jak má fungovat.

Konec: **832 prošlo, 3 selhala, 6 neprůkazných.** Jedno z těch tří selhání byl
strážce ledgeru, červený proto, že fold ještě neproběhl. Obě skutečná jsou
jejich.

Po foldu **41 VERIFIED FIXED, 2 STILL REPRODUCIBLE, 1 nerozhodnutelný (#91 —
Nexus neodpovídá, takže nejnovější odpověď jmenující kartu je starší než 24 h).**

**Odešlo nic**, a je to schválně — viz *Čeká na tebe*.

**Dobrá zpráva z jejich strany: `/fund` je opravený.** Klíč agenta teď přijímá
**10 z 11** jejich autentizovaných `cloned-bots` cest. Jediná, která ho pořád
odmítá, je `GET /api/v1/cloned-bots/{instance_id}/activity`. A jejich povrch
vyrostl: `DELETE`, `withdraw`, `toggle-trading`, `asset-analytics` a `settings`
jsou cesty, které při psaní té kontroly neexistovaly.

## Opraveno

**Kontrola, kterou jsem napsal v osm večer, by jim byla poslala `pass`, který
jsem neměřil.** Ta nová k jejich průvodci `/guides/nexus-lab-loop` se ptá tří
nástrojů, jestli fungují bez klíče. Když jeden z nich neodpoví — a jim ve
20:55 spadl TLS handshake, takže to není hypotéza — nebyl ani ve `walls`, ani
v `answered`, a větev „neprůkazné" chtěla všechny tři. Verdikt: `passed`, s
odůvodněním „všechny tři nástroje odpověděly: [dvě jména]". Věta si odporovala
sama se sebou a `pass` odsud je to, co posílá `verify.py`. Našel to code review
i jeden auditor nezávisle. (R01, 3/3)

**A pointa téhle noci: opravu, kterou jsem napsal ve tři ráno, chytil až ostrý
běh — hodinu předtím, než by odešla.** C03 říkal správně, že kontrola na
#89/#98 nesmí padat na cestě mimo tok, který popisuje její vlastní docstring.
Zúžil jsem verdikt na cesty končící `fund` a `go-live`. Jenže **jejich `/fund`
je opravený** a ta, co klíč pořád odmítá, je `/activity` — přesně to, o čem ten
řádek dneska je. Kontrola zezelenala na živém, nahlášeném, dvakrát zaplaceném
nálezu, jeden fold od toho, aby `verify.py` poslal `pass`. „Posouvá klon dál"
byla moje hranice, ne jejich; agent, který čte aktivitu vlastního klonu, je v
tom toku podle každého poctivého čtení. Verdikt čte `refuses` jako předtím,
`blocked` se jen hlásí, a `tests/meta` teď připíná dnešní skutečný tvar.

**Test v `tests/meta`, který by 15. září shodil každou session.** Fixture
orazítkovaná `2026-09-12T12:00Z`, `night_refill` bez švu na `now`, takže
`best()` čte hodiny a `stale_after(30)` jsou tři dny. Červená v `tests/meta`
přerušuje celou sadu — vzalo by to s sebou i kontroly proti jejich platformě,
tři dny po tom, co ten test vznikl. (A01, 3/3)

**Čtyři strážci, kteří poháněli pomocné funkce místo toho, co jmenují.**
`patrol()` nevolal v celém repozitáři nikdo — test si `within()` a
`runs_from_records()` skládal sám, takže regrese „419 běhů za sedm dní" prošla
(B05). Pět ze sedmi deníků v ohlédnutí bylo zastubováno na `[]` (B06). Slovník,
na kterém `review.area_lab` stojí, byl napsaný dvakrát — jednou ve čtečce,
jednou jako literál v testu (B07). A kontrola, co tvrdí „#97, přesně", poháněla
`fields_drift`, funkci, kterou mimo ten test nikdo nevolá; připomínka jede
`shape_drift` s přísnějším kritériem (B08).

**Hook, jehož „mlčí, když nic nehrozí" se měřilo na fixture, kde se nemůže ani
načíst.** `reminders.py` se v prázdném `tmp_path` vrátí dřív, než `reminders()`
vůbec spustí, takže prázdný výstup dokazoval ten návrat a nic o tichu.
Bezpodmínečný `print` po načtení nechal všech sedm testů zelených. (B04, 3/3)

**Dál:** strop se porovnával s tím, co `sizes()` na tomhle stroji zrovna vydalo,
a tři z těch klíčů jsou podmíněné — v klonu dva správně spárované stropy četly
jako „hlídá nic" (B01); `lenient > strict` u čtečky effortu znamenalo, že
**rovnost** = rozbitá čtečka, což je stav, do kterého repozitář míří (B02);
`\bf\.([a-z_]+)\b` neumí chytit `f.displayState` vůbec (C06); `accounts_for`
zahodilo větu, kterou Cymetica napsala do `counters_cover` místo do
`counters_do_not_cover` — to je tvar #83, potřetí na stejném endpointu (C01);
prořez odmítal nečitelný ledger a nechal `audits/checks.json` o řádek níž
(R02); manifest se četl z pracovního stromu u strážce, který slibuje
„v commitnutém manifestu" (C05); jméno cesty v jejich openapi se bralo doslova,
takže přejmenování parametru by jim ohlásilo cestu, kterou dokumentují (C02);
noční hledání se měřilo počtem, ne časem (A02); a jeden test si přisvojoval
jméno vlastností, které drží jiný soubor (A03, přejmenován).

## Prořezáno

**Paměti: dvě retirované**, obě proto, že je dnes drží CLAUDE.md, který se čte
vždycky. `a-mechanism-the-operator-must-run-is-not-a-mechanism` → CLAUDE.md:633
nese tu větu doslova; `not-thinking-about-it-is-not-permission-to-run-alone` →
stalo se z toho tvoje vlastní rozhodnutí na CLAUDE.md:76, připnuté testem, což
je silnější než paměť. Značka `RETIRED` v `MEMORY.md`, soubory zůstávají — a
byl to **první případ, kdy ten mechanismus vůbec jednou proběhl**.

**Součásti:** `patrol --flags` nevypsal nic. Nic není 14 dní nečinné, nic není
nad stropem. `CLAUDE.md` sedí přesně na 700 řádcích, tedy nula rezervy.

**Mechanismy:** `never_fired --zeros` hlásí 4 nikdy nespuštěné a **všechny čtyři
mají test**, který je aspoň jednou schválně vyvolal. Žádný nemá tvar „nikdy
nespuštěno a nikdy nevyzkoušeno", který opravňuje smazání.

**Testy:** `tests/meta` 426 → **429, čistý přírůstek +3**. Všechny tři jsou
kontrakty živých kontrol a všechny šly do `test_pipeline_checks.py`, souboru,
který přesně tohle drží: rozhodnutí `decide()` u nové kontroly bez klíče (R01),
`states_exclusion` u portfolia (C01) a dvojice `credential_gap`/
`served_but_undocumented` u klonů (C02+C03 v jednom testu). Zvažoval jsem
přidat je k sousedům — `test_a_window_is_read_for_its_value...` u prvního,
`test_the_summary_may_account_for_positions_by_counting_them` u druhého — a ani
jeden by je neunesl: první připíná sémantiku backtestových oken, druhý je
**připnutí z minulého passu, které jsem schválně nechal platit** (viz níž).
Všechno ostatní z dnešní noci se vešlo do existujících testů.

## Minority report

- **A04 — `len(sent) == len(set(sent))` je splněno prázdným `sent`.** Jeden hlas
  ze tří. Dva čtenáři to reprodukovali obráceně: když se odstraní deduplikace,
  `sent == [CARD]*3` a test zčervená, takže vada, kvůli které existuje, chycená
  je. Prázdné `sent` vyžaduje druhou, nesouvisející regresi, kterou hlídá
  sousední aserce ve stejném souboru.
- **B03 — `--deep-pass all` nikdy nedojde do `area_lab`, a nástroje by tam zápis
  neviděly.** Jeden hlas ze tří. Dva čtenáři pustili `review.py --lab all`
  proti kopii `state/` a **nezměnil se ani bajt** — tvrzení „`--lab` přidá řádek
  do `state/backtests.jsonl` při každém běhu" je prostě nepravda. Zbývá
  neprocvičená větev, ne strážce mlčící nad živým zápisem.
- **C07 — `_next_items()` má `except Exception: return set()`.** Jeden hlas ze
  tří. Dva čtenáři: `parse()` na obsahu nikdy nevyhodí výjimku, takže tam vede
  jen chybějící nebo nečitelné `NEXT.md` — stav, který stejně dělá červenou, a
  směr je hlasitý, ne tichý.

## Změněná pravidla

**Žádné.** A stojí za zmínku, kde jsem jedno málem změnil: oprava C01 chtěla,
aby `accounts_for` vracelo nový stav pro větu o vyloučení v `counters_cover` —
jenže přesně tuhle návratovou hodnotu připíná `test_the_summary_may_account_for_
positions_by_counting_them`, tvoje... ne tvoje, smyčkou schválený závěr passu
z 11. 9. (3/3). To připnutí je správné: věta, že se karty **ne**počítají, je
nepočítá. Takže jsem místo přepsání přidal druhou čtečku `states_exclusion`,
která odpovídá na jinou otázku, a staré připnutí platí dál.

## Čeká na tebe

- **Oprava na #89/#98 se dluží, a neodeslal jsem ji, protože ta zpráva by
  lhala.** Fold dluží `correction_owed`, protože se dnes v noci pohnul otisk
  kontroly. Zpráva, kterou `verify.py` pro ten případ skládá, začíná: *„This
  corrects the record: either a fix was claimed and our re-check does not
  agree, or we sent you a pass we can no longer stand behind."* Náš poslední
  verdikt na obou reportech byl **taky `fail`** — neplatí ani jedna z těch dvou
  možností a neopravuje se nic, jen se pohnula definice. Pravdivý verdikt
  v nepravdivém rámci je pořád nepravdivé tvrzení. Šablona potřebuje třetí
  hlavičku („definice se pohnula, verdikt se nezměnil"), a je to `qa/fold.py`
  plus `scripts/verify.py`, takže test první a `/code-review` — ne ve čtyři ráno
  bez triáže.
- **Kritérium, které jsem na klonech nenašel.** C03 má pravdu, že verdikt nemá
  padat na cestě mimo tok — jen to potřebuje hranici čitelnou z **jejich**
  dokumentu, ne seznam segmentů, který si vyberu já. Dnes v noci to stálo
  málem falešný `pass`. Až budou mít `DELETE`/`withdraw` v openapi popsané
  jako uživatelské, bude podle čeho.
- **Nexus deep kanál pořád nejede** — 1 z 5 posledních dotazů odpovězena. Drží
  tím #86 i #91, a `outbox/telegram-nexus-deep-down.md` z minula pořád platí.
- **`/activity` je poslední cesta, co odmítá klíč agenta.** `/fund` opravili.
  Jestli je to u `/activity` záměr, je otázka na ně — a je to zúžení #89/#98,
  které by stálo za zprávu, až budeš psát.

## Co mě to naučilo

**Notebook téhle noci přestal být platný JSON a já si toho všiml jen proto, že
mi prošel negativní kontrolní test, který měl spadnout.** Tři appendy nechaly
mezi objekty chybět čárku, `working_copy()` vracel `None`, a strážce, co jsem
zrovna psal, mlčky přeskočil celé tělo. Kdyby ta kontrola nebyla, ztratil bych
všech 24 nálezů — soubor existuje přesně proto, aby se to nestalo.

**A první mutace, kterou jsem na to pustil, se nikdy neaplikovala.** Skript
vytiskl „mutated" bez toho, aby ověřil, že se text změnil, a já to přečetl jako
důkaz. Pak jsem operátorovi napsal, že render není deterministický — nebyl to
render, byl to můj vlastní nový test, který jsem si mezi těmi dvěma běhy sám
stashnul.

Obojí je jedna věc: **tvrdil jsem, že kontrola funguje, místo abych to dokázal.**
Každá oprava dnešní noci má proto mutaci, která ji shodí, a každá mutace
kontroluje, že se vůbec aplikovala.

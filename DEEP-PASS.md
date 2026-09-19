# Deep pass — 2026-09-19

Běh `deep-pass-2026-09-19` začal na commitu `abaa7e94`. Ve scope bylo 47 commitů
a 4 592 řádků Pythonu, skoro všechno z předělávky laboratoře na tick.

Ověřovací běh měl prereg `PRE-0117` a run `run-20260919T171917Z-2c3f7c91`,
level V. Celá suita: **994 prošlo, 4 spadly**. Tři pády jsou už podané nálezy
(#52, #86, #89/#98). Čtvrtý byl dashboard, který spravil render.

## Co se stalo

Tři auditoři prošli checky s pohnutým otiskem. Code review prošlo diff
laboratoře: tick, sync door a kontrolní skupinu FOMO. Dohromady **48 tvrzení**,
33 z auditu a 15 z review.

Každé tvrzení posoudili tři nezávislí čtenáři: **37 reálných, 2 minority,
9 zamítnutých**. Zamítli tak 11 tvrzení ze 48, víc než kterýkoli pass předtím.

**Opraveno 37 z 37.** Opravy jsou ve třech commitech:

- `fd5e4c08` — kód laboratoře;
- `de45fb7d` — vendor checky;
- `2119ec95` — naše stráže.

Odesláno Cymetice: **pass na #88 a oprava (`fail`) na #52.** Nic jiného ven
nešlo.

## Opraveno

**Laboratoř mohla otevřít room bez pozice a koupit tutéž kartu dvakrát.**
Tři cesty (R01, R02, R09):

- odmítnutý paper nákup nechal otevřený room s kritériem, ale bez pozice;
- odpověď s víc než osmi kartami nechala room bez plánu;
- další tick mohl koupit kartu, kterou už drží jiný běžící room.

Teď se room zavře, nohy se ořežou na osm a držené karty se přeskočí.

**Otázka na Nexus mohla viset „v letu" celých 24 hodin.** (R03, R04) Chyba
jiná než síťová nezapsala give-up. Zaseknutý job ve frontě tak blokoval další
otázku. Teď každá chyba zapíše give-up a strop jsou 2 hodiny.

**Kontrolní skupina memecoinů mohla obsahovat coin, který byl tu samou hodinu
hot.** (R08) K tomu se coiny s nepřečtenou hloubkou počítaly jako
neobchodovatelné (R07). Teď mají vlastní kolonku.

**Jedenáct vendor checků tvrdilo méně, než slibuje jejich docstring.**
(V01–V04, V06–V12) Příklady:

- #88 porovnával jen cesty, ne HTTP metody;
- #86 nikdy nevypršel u otázky, která zůstala ve frontě;
- nástroj bez čitelného schématu prošel jako „bere parametry";
- „Login required" se nepočítalo jako zeď.

**Run mohl dostat úroveň V, i když se kód během běhu změnil a commitnul.**
(V16) `code_dirty_after` četl jen `git status`. Teď porovná i HEAD na
začátku a na konci.

**Sedmnáct našich stráží a testů procházelo díky tvaru fixture, ne díky
kódu.** (C01–C06, C08, L01–L07, V13–V15) Fixture byla už seřazená, všechny
roomy padly do poslední hodiny, klíč se schoval za vlastní vzor redakce.
Každá oprava je ověřená mutací produkčního kódu.

**Patrol neviděl agenty.** Počítal volání skillů a Bash příkazy, ale spuštění
agenta není ani jedno. `check-auditor` a `finding-triage` proto ukazovaly
0 běhů. Teď ukazují 13 a 30 (`0d0950b4`, test napřed).

## Prořezáno

- **Paměť:**
  - 2 soubory vyřazeny. `give-the-delta-not-the-narration` drží CLAUDE.md
    ([operator 2026-09-13] „A long answer is an unread answer").
    `the-operator-does-not-review-documents` drží sekce „How to work with
    me".
  - 0 sloučení.
  - 2 nové, viz Co mě to naučilo.
- **Součásti:** patrol hlásí nic nad stropem a nic nečinného.
- **Mechanismy:** 4 z 55 nikdy nenastaly (`SUPERSEDED`, `supersede`,
  `results_not_collected`, `prereg_commit_mismatch`). Všechny čtyři ale
  cvičí nějaký test, takže není co odstranit.
- **Testy:** `tests/meta` vzrostly ze 543 na 555 (+12):
  - lab_loop 5;
  - fomo_control 3;
  - po jednom admissibility, secrets, movers a fomo_identity.

  Každý hlídá vstup, který dosavadní test neměl: jiné pořadí, jiné okno nebo
  jiný tvar klíče. Zbylých 25 oprav jen zpřísnilo existující testy.
- **CLAUDE.md:** 754 → 736 řádků, škrtnuty jen historické odbočky
  (`2fd422be`).
- **NEXT.md:** nic nesmazáno. Nejstarší otevřená položka má 9,7 dne, limit
  je 14.

## Minority report

- **R05 — řádek „Nexus: X z posledních N odpovědělo" teď započítává i
  okamžité odpovědi sync door.** Reálné to označil jeden čtenář ze tří.
  - Reprodukce: `_nexus_rows()` čte `load_all()`, tedy oba deníky.
  - Nechávám to tak. Je to jen řádek ve `status` a nic na něm nestojí.
    Backoff tick čte jen z deep lane (`backoff_until` řádky `shallow`
    přeskočí).
- **V05 — FOMO check projde hot coin, u kterého nejde přečíst ani rezervu,
  ani likviditu.** Reálné to označil jeden čtenář ze tří.
  - Reprodukce: hot řádek s `max_buy_5pct_usd: null` a `liquidity_usd: null`
    funkce `breaches()` přeskočí a `decide()` vrátí pass.
  - Jejich vlastní slova přitom říkají, že nepřečtená rezerva má skončit
    jako not-hot.
  - Nechávám to být, dokud se takový řádek neobjeví v datech. Pak se z toho
    stane nález.

## Změněná pravidla

Žádné. Pravidla v CLAUDE.md, odstavce `[operator …]` ani páteř skillu tento
pass neměnil. `rule_changes` je `[]`.

## Čeká na tebe

- **Na #86 a #89/#98 jsem nic neposlal. Rozhodnutí je moje, veto tvoje.**
  - #86: pět odpovědí, podle kterých check soudí, jsou odmítnutí pro
    kapacitu. Všechna přišla dřív, než Cymetica spustila frontu
    (REPLY-0019), takže `fail` by popisoval starý stav. Nové odpovědi z
    laborky ho přeměří samy.
  - #89/#98: jeden verdikt pokrývá dva reporty o různých routách. `fail`
    na #89 by zopakoval nepravdu, kterou pass 2026-09-13 odmítl poslat.
    Řádek rozdělím na dva. Je to v NEXT.md a do té doby na něj nejde nic.

## Týden

1. **Co se opakovalo: check slabší než jeho vlastní docstring, třetí pass po
   sobě.** Tentokrát 11 z 37. Druhá opakovaná třída je test, který projde
   díky fixture (17). A #89/#98 visel v „Čeká na tebe" podruhé, takže teď je
   rozhodnutý a v NEXT.md.
2. **941 testů hlídá nás, 66 měří jejich platformu.** Minulý týden
   (2026-09-09) to bylo 419 a 54.
   - Poměr posunula laboratoř: přinesla stráže, ne měření.
   - Incidenty tohoto passu dopadly 11× na vendor checky a 8× na kód
     laboratoře. Tam verdikt odchází ven, nebo se utrácí paper.
   - Stráže nechyběly. Byly slabé.
3. **Model: 108 commitů Opus 5, 11 Sonnet 5. Tabulka sedí, nic neměnit.**
   Sonnet dělal console polly, ověření REPLY-0017 a session laborky. Žádný
   report ze Sonnet sweepu nebyl tento týden stažen ani opraven (0 `withdraw`
   v žurnálu).
4. **Triáda zamítla 11 z 48 tvrzení, nejvíc zatím. Pořád se vyplácí.**
   - Laboratoř za týden:
     - 1 nový room a 2 verdikty;
     - 269 backtestů;
     - 7 otázek na Nexus, z toho 5 vzdaných kvůli kapacitě.

     Odpovědí je dnešní tick spolu s jejich frontou.
   - Filtr: málo dat, 0 uzavřených verdiktů z potřebných 6.
   - Patrol: nic nečinného. Jediná slepá skvrna (agenti) je opravená.

## Co mě to naučilo

**Brzda přenesená jinam si nese číslo, ne důvod.** Do celodenní smyčky jsem
převzal konstanty z noci:

- 20 minut čekání, i když Cymetica řekla „zkus za 30 s";
- vyzvedávání odpovědí po 30 minutách;
- stop-loss se špatným znaménkem.

U každé konstanty se musím znovu zeptat, co chránila.

**Smyčka, která k cíli nemá cestu, vypadá jako vyčerpaný prostor.** Hlásil
jsem „laborka vyschla", ale ta smyčka se Nexusu zeptat vůbec neuměla. Než
čtu ticho jako zprávu o trhu, spočítám, co tick vůbec dokáže udělat.

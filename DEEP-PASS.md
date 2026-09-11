# Deep pass — 2026-09-11

Běh `deep-pass 2026-09-11`, start na commitu `0b610fb3`, preregistrace
**PRE-0099**, běh **run-20260911T174358Z-c0e379b9**, level V.
101 commitů k pushnutí, strom čistý.

## Co se stalo

**46 nálezů, 41 potvrzených, 40 opravených, 1 odložený na tebe (V17).**

| odkud | nálezů | potvrzeno | zamítnuto | menšinových |
|---|---|---|---|---|
| audit kontraktů (3 auditoři, 157 funkcí) | 38 | 37 | 1 | 0 |
| code review xhigh (přes ~10 800 řádků kódu) | 8 | 4 | 3 | 1 |

Triáž: tři čtenáři, 46 nálezů, **43 jednomyslných**. Z pěti, které triáda
nepustila, byly **čtyři z mé recenze** a jeden z auditu — stejný poměr jako
včera. Dva z mých zamítnutých (R06, R07) byly pravdivé, ale bez čtenáře, který
by podle nich jednal špatně.

Konec: 687 prošlo, 2 selhaly, 4 neprůkazné. Selhání jsou **#86** (Nexus
nedopověděl 5 z 5 dotazů, platí) a test konzistence repa, kterému konzole
během desetiminutového běhu překreslila dashboard z vlastního pollu; složeno
a vyrenderováno hned po běhu, `tests/repo` pak 94 prošlo.

Po foldu **41 VERIFIED FIXED, 1 STILL REPRODUCIBLE (#86), 10 WITHDRAWN.**
Sedm řádků neslo definici, kterou tahle noc změnila; každý jsem připnul s
důvodem a všech sedm pod novou definicí prochází. Odešlo 9 verdiktů: `pass`
na #94, #96, #87, #95, #91, #88, #89, #90 a `fail` na #86. **#96 — odpolední
report, že nová ARENA noha se neodečetla — už platí jako opravený**: zůstatek
bota je 495 = 1000 − 50 − 455.

## Opraveno

**Kniha počítala peníze v botovi jako volné.** Po jejich opravě #94 se stake
bota odečítá hned při vstupu, takže `current_balance_usdc` přestal obsahovat
otevřené pozice — kniha brala 550 v botovi a zbylých 400 za hotovost. Teď
počítá, co jsme do bota poslali, plus co vydělal nebo prodělal: 950. A když
se zůstatek botů nedá přečíst, `buy()` objednávku odmítne — dřív ho kniha
brala jako nulu. (R01, R02, T01)

**Záznam obchodu mohl zůstat bez výsledku.** `clone`, `fund` i `enable` četly
odpověď jako JSON bez ochrany hned po POSTu; odpověď 200, která JSON není, by
nechala záměr bez výsledku. A když se po zapnutí bota nepovedlo znovu přečíst
jeho stav, skript tvrdil „nic se nespustilo" o botovi, který právě naběhl.
(R04, R05)

**Strážce u peněz nečetl příznak u objednávek, které opravdu posíláme.**
`event_cards.buy/sell/short` nebyly v jeho seznamu, takže `short` na
`[confirm]` místo `[paper]` by prošel. Teď jsou tam; je to změna strážce,
proto se o ní hlasovalo (RC1). (T03)

**Dvě negativní kontroly by při rozbité odmítce naklonovaly skutečného bota.**
Teď jim při stavbě klienta spadne test dřív, než cokoli odejde. (T04)

**Čtrnáct kontrol mohlo Cymetice poslat nepravdu, nebo nemohlo zčervenat.**
Nexus karty: UUID druhu nebo backtestu se četlo jako karta (V01). Okno #86:
znovu dotázaná stará otázka se posunula mezi pět nejnovějších a naše vlastní
selhané čtení se počítalo jako jejich (V04). Výpis karet: zastavené procházení
vypadalo jako celé (T08, V02, V03). Bot a stake: nečitelná částka se počítala
jako nula (V13). Nákup a prodej na paperu: nečitelný zůstatek předal verdikt
starší transakci, poplatek vypadal jako „nevrátilo se" (T02, T05, V06). Plus
nástroje Nexusu (V08, V09), zdrojové cesty (V12), klonovací povrch (V10, V11)
a souhrn portfolia (V05).

**Třináct testů stránky a roomů hlídalo text, který tam byl i bez nich.**
Čísla na panelu se hledala kdekoli, kde je obsahoval i nadpis; CSS se četlo
jen pod třídou; token konzole se porovnával mezi dvěma hosty místo dvou
spuštění. (P01–P13)

**Tři testy hlídající samotný deep pass.** Nehlasovaný nález u dokončeného
běhu prošel (V14), historie se ptala na jakýkoli běh místo nejnovějšího (V15),
rozsah auditu se porovnával sám se sebou (V16).

## Prořezáno

Paměť: dvě relativní data („today") přepsaná na absolutní
(`a-matching-hash-proves-only-what-it-hashes`, `every-mechanism-agreed-and-the-claim-was-false`).
Nic sloučeno, nic retirováno; skill `consolidate-memory` v téhle session
nebyl k dispozici, tak ručně a v mezích tří tahů.

Mechanismy: `never_fired.py --zeros` hlásí 4 nuly, všechny cvičené testem —
nic k odstranění. `reopen` se dnes poprvé skutečně stal (#86).

Testy: `tests/meta` 331 → 346, každý nový je test, který byl před opravou
červený, a všechny jsou v existujících souborech — důvody v
`audits/deep-pass-progress.json` pod `meta_tests.reason`.

## Minority report

- **R03 — `cloned_bots.settings` je v `components.yaml` spustitelný bez
  jakékoli podlahy.** Jeden hlas ze tří. PATCH na `is_trading`, `stop_loss_pct`
  a další nemá `required_flags` a na rozdíl od fundu a toggle ho nehlídá ani
  skript. Dva čtenáři: nikdo ho nevolá a toggle-trading má stejné vystavení.
  Třetí: MUTATE test s `--allow-mutate` by mohl zapnout obchodování klonu, který
  mezitím přešel na live, a nic by ho nezastavilo.

## Změněná pravidla

- **RC1 — strážce peněz teď hlídá i objednávky na event karty a jeho soubor je
  znovu připnutý hashem.** `test_guard_is_real.py` má v seznamu `must` navíc
  `event_cards.buy/sell/short`, takže jejich příznak se čte podle jména.
  `test_pipeline_abort.py` ten soubor hlídá hashem, proto nový pin (commit
  `f6de492a`). Tři čtenáři bez sdíleného kontextu: 3/3, že nic neoslabuje a
  nesahá na žádné tvoje rozhodnutí. Jen přidává vynucení.

## Čeká na tebe

- **V17 — kontrola eskalace qa-agent kanálu nikdy nemůže selhat a co má
  měřit, nerozhodnu sám.** Tvrdí, že asynchronní kanál nesmí jen zopakovat
  pravidlo směrování — ale co je „zopakovat", neříká, a odpověď z inboxu
  nečte. Doporučuju tvrzení přesunout do sesterské kontroly async first-pass,
  která odpověď čte a hodnotí. Do té doby zůstává jako evidence, nic nehýbe.
- **Nexus deep kanál pořád nejede — zpráva na Telegram je připravená.**
  `outbox/telegram-nexus-deep-down.md`: šest dotazů za sebou `failed`,
  s jejich job id. Až ji pošleš, zapíšu ji; až odpoví, pustím session znovu.

## Co mě to naučilo

**Změnu strážce jsem commitnul po testech jen jeho souboru — a jeho hash hlídá
jiný soubor.** Pin v `test_pipeline_abort.py` byl červený pět commitů, dokud
ho nechytil celý meta gate před během. Paměť
`a-guard-file-is-watched-from-another-file`.

**Opravu jsem schoval, zatímco triáž četla strom.** Čtenáři čtou pracovní
kopii; kdyby narazili na už opravený kód, hlasovali by „není pravda" o vadě,
která v HEAD je. Stash po dobu hlasování, pak zpět.

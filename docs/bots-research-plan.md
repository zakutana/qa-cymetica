# Výzkum botů v H2H -- plán (schválen 2026-10-03)

Operátor 3. 10.: laboratoř je výzkum, cíl je zjistit, jak na Cymetice vydělat. Otestovat co nejvíc
kombinací botů, jejich nastavení a algoritmů, hodně H2H, s Nexusem. Dnes Cymetica potvrdila (Telegram,
a2a 3. 10.): až 25 paper klonů najednou (50 s pozastavenými), víc klonů stejného druhu, Nexus filtr
už pustí „co obchodovat". Tvrzení jsme ověřili živě: dokumentace `interval`, přesměrování, sdílený obrázek;
klony: 11 existuje, strop se ověří při F1.

## Co F0 zjistil (3. 10.) -- mění F2
* Skilly a modely klonu (`/skills/equip`, `/models/equip`, `/skills`, `/models`) **chtějí jen JWT relaci**,
  X-API-Key je odmítne (401 „Valid JWT token required"). Nexus (NEX-0121) to potvrdil jako známou mezeru:
  `fund`, `toggle-trading` a `PATCH settings` už klíč berou, skills/models ne. Žádný MCP nástroj skill neequipuje.
* **Jde měnit parametry indikátorů**: MCP `update_bot_indicators(instance_id, indicator_name, params)`,
  indikátory rsi|macd|ema|sma|bollinger|atr|stochastic, s klíčem a na paper klonu; čtení `get_bot_indicators`.
  Pozor: bot s `strategy_override="none"` nemá co přepsat.
* Výbavu jde číst bez přihlášení: `GET /cloned-bots/{id}/skills/public`, `/models/public` (zpětné ověření).
* Katalog: 22 klonovatelných zdrojů, 29 skillů (Nexus: zdarma 22 z 24, placené `memecoin_mining`, `belief_network`;
  modely: 17 z 20 zdarma), 20 modelů, 5 kombinací. `effectiveness_rating` je „curated default", neměříme se podle něj.
* Rozměry, které klíč dosáhne: druh bota (22) × parametry indikátorů × nastavení (SL/TP/pozice/jistota/trhy) ×
  financování. Skilly a modely čekají na opravu u Cymetiky (zpráva odeslána).

## Hotovo-když
1. ≥ 20 paper botů obchoduje najednou ≥ 24 h, pokrytí samplerem každého ≥ 0,8.
2. Přepsání indikátoru ověřeno zpětným čtením (`my-clones.primary_indicators`) na ≥ 3 klonech.
3. Vlna 1 (≥ 10 H2H souboje) běží s předem zapsaným kritériem; výsledky jsou v `/lab`.
4. „Kombinace vydělává" se smí říct jen po dvou nezávislých oknech (vlna n a n+1).
5. `tests/meta` + nové testy zelené; sweep na úrovni V.

## Fáze
* **F1 kapacita** (testy napřed; `scripts/lab.py`, `scripts/clone.py`, `qa/lab.py`, `scripts/sampler.py`):
  strop *obchodujících* botů jako konstanta; refusal „strop" nespotřebuje položku gridu (`tried_variants`,
  `stop():2901`) ani se nezapíše jako „API odmítlo klon" (`_species_cloned:2741`); zvednout naše zákazy
  jednoho klonu na druh (`_species_cloned`, `live_refs:2230`, `launch_bot:2465-2475`, „one at a time"
  `bot_variants:2859`, `restart_refusal`); platforma říká 409 ALREADY_CLONED -- ověřit pro Pro;
  sampler: zjistit, co čte druhý GET na bota (`_bots:221`, `ROUND_SECONDS=90`), pak škálovat na 25;
  názvy roomů podle konfigurace.
* **F2 parametry indikátorů** (guard, citlivé): `clone.py indicators --instance --indicator --params` přes MCP
  `update_bot_indicators`, jen paper klon naší evidence, jen uvnitř mezí indikátoru; záměr→výsledek→stav jako
  `settings():887`, zpětné čtení z `my-clones` a `/skills/public`. `safety.py` / `components.yaml`: nástroj je
  dnes neklasifikovaný (`safety.py:344-351`, `416-422`) a nemá `paper` argument, takže nese-li ho pravidlo
  `closed_body` + naše kontrola paper klonu, ne `paper_gated`. Nový testovací soubor pro bránu
  (`test_guard_is_real.py` je hash-pinned, NEUPRAVOVAT; vzor `test_pipeline_board_tools.py`); po změně guardu
  `/code-review`.
* **F3 návrh pokusů**: propustnost ≈ 10--14 nových konfigurací týdně při 20 botech, sdílené baseline na druh a
  okně 7 dní (H2H verdikt po 3 obchodech na stranu); kratší okno (3--4 dny) za méně obchodů. Vlna 1: pro ~10 druhů
  baseline vs 1 varianta (parametry z Nexusu + jedna náhodná změna), pak jednofaktorové sondy tam, kde vyšel signál.
  Kritérium zapsané před během (`qa/rooms.py set_acceptance:491`): H2H „improved" a vlastní P&L proti BTC proxy
  (`qa.lab.verdict:1415`), nový práh min. počtu obchodů. Vlna n+1 stejné konfigurace v novém okně = jediný důkaz.
* **F4 H2H záznam**: `h2h.py` uloží slug, `results` čte `/head-to-head/mine`, `matrix` pustí dávku párů;
  `/lab` ukáže H2H řádek (angličtina, čísla před slovy, barvy Cymetiky).

## Zbývá (stav 2026-10-04, zapsáno na žádost operátora; odškrtávat tady)
Hotovo: F0 (sondy, Nexus NEX-0121), brána `own_clone_write` + `clone.py indicators()` (první živá změna ATR Alpha
CLN-0143, read-back sedí), wave 0 spuštěna (12 botů obchoduje, rooms STR-0083..0091, kritérium předem), commit 2cc5d5fe.

- [ ] **Sampler musí běžet** do konce wave 0: `python scripts/sampler.py run --every 600` (dnes běží jako pozadí
      session; konzole ho dělá taky: `serve.py --sample 10`). Bez něj se room nedá soudit.
- [ ] **Wave 0 verdikt ~10. 10.** (STR-0083..0091 + sedm starších); `lab.py verdicts` / tick. Jedno okno je měření,
      ne nález.
- [ ] **Vlna 2** po verdiktu: stejné druhy, jedna změna parametru (`clone.py indicators`, jen WTA druhy; perpetual agenti
      indikátory nemají), nové okno, kritérium předem. Tvrzení „druh/parametr vydělává" až po dvou oknech.
- [ ] **F1 kód (testy napřed):** strop *obchodujících* botů jako konstanta (dnes ≥ 12 ověřeno, 25 ne); refusal „strop"
      nespotřebuje položku gridu ani se nezapíše jako „API odmítlo klon"; víc klonů na druh až když to Cymetica zapne
      (dnes 409 ALREADY_CLONED); sampler pro ≥ 25 botů (co čte druhý GET na bota); názvy roomů podle konfigurace.
- [x] **`qa/lab.py::bot_stops` čte `auto_pause_reason`** (hotovo 2026-10-07: sampler ukládá důvod, stop na pásmu je `their_trigger`, `wave.py resume`) (sweep 2026-10-04): my-clones dnes nese `status: stopped` +
      `auto_pause_reason` (`stop_loss` / `take_profit`, v llms.txt), takže `their_guard` („nezdokumentováno", odvozeno
      ze znaménka zisku) a `unexplained` (zisk = ve skutečnosti take_profit) jsou zastaralé štítky. Test napřed.
      Tři boty ze 2. dávky H2H (cbdc3ecd, 17efa669, 5124b7be) stojí na `stop_loss` z 28. 9., před opravou #134.
- [ ] **F4:** `h2h.py` ukládá slug, `results` čte `/head-to-head/mine`, `matrix` pouští dávky; H2H řádek v `/lab`.
- [x] **Tool pro vlnu:** `scripts/wave.py` (plan / run --confirm), testy `tests/meta/test_pipeline_wave.py`; wave 0 uzavřena 5. 10. (platforma zastavila všech 9 po jednom obchodu na výchozím SL 5 / TP 15).
- [x] **Wave 2 živě** (SL 15 / TP 40, 20 druhů, rooms STR-0097..0116): spuštěna 6. 10. ráno, 20 botů `is_trading` při čtení samplerem; verdikt ~13. 10. (hotovo 2026-10-06)
- [x] **Obnova po pauze platformy** (7. 10.): platforma pauzuje každý klon na prvním SL/TP (`auto_pause_reason`), 15 z 20 stálo do 4 h. `python scripts/wave.py resume` (suchý běh) vypíše boty, `--confirm` je obnoví: starý room se zastaví a posoudí, nový room s kritériem, pak `enable`, stejná nastavení; nikdy víc než 25 obchodujících, jednou za 6 h na bota; 3× stop-loss po sobě = klon se smaže (operátor). Jiný důvod zastavení zůstává nález. (hotovo 2026-10-07)
- [x] **Karty, dopředný test:** short karet jen s akciemi (−0,35 až −0,55 % za 72 h), long s kryptem; soudí jen
      karty vzniklé od 4. 10. (`qa/card_rules.py`, `python scripts/card_rules.py`; hotovo 2026-10-04, 8d4ddfd1).
      Verdikt až ~200 karet na pravidlo, tedy po ~10. 10. Nápad k ověření: koncentrace váhy koše (HHI) a počet
      položek předpovídá „Hot" (Nexus NEX-0120 potvrdil mechanismus).
- [ ] **Odpovědi Cymetiky ke sledování:** 2. klon druhu (409, A2A-0055), skilly/modely přes API klíč (A2A-0054),
      report #150 (plán Pro/Free), podání /code-review a push až po deep passu.
- [ ] **Degen prompty přes `chat/stream` (paper)**, přesunuto z NEXT.md 2026-10-04 (10 dní nezačato): klient
      `scripts/chat.py` hotov, běželo 9 a 8 (8: nákup shortlistu nejde). Zbývá room na prompt a zbylé prompty
      (ne 7: veřejná karta; ne arena); každý otevře pozice mimo rooms, nejdřív návrh room. Až po verdiktu wave 0.
- [ ] **Nepotvrzeno, čeká na operátora:** zpráva Cymetice o soukromí zadání v Build it Better (CoStar chce nasazení).
- [ ] **NEX-0137, pásma od Nexuse (11. 10.):** `python scripts/lab.py launch NEX-0137` ve fázi P3 laborky v3
      (docs/laborator-plan.md), až pravidlo „3× stop-loss = zahodit" bude platit pro buňku (druh + pásmo), ne pro
      druh. Pak se otevřou všechny čtyři: Perceptron Oracle 12/30, Fibonacci Phoenix 10/22, MACD Hunter 12/36,
      RSI Sniper 10/24, každý nový paper klon ve vlastním roomu (6961592c, a0bf524e).

## Meze
Jen paper; žádný nákup skillu/modelu za USDC; MUTATE zůstává trojí brána; Nexus radí, naše strategie se měří,
nevěří se jim před ním. Platební věci a účty patří operátorovi.

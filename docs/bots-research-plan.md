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
- [ ] **F4:** `h2h.py` ukládá slug, `results` čte `/head-to-head/mine`, `matrix` pouští dávky; H2H řádek v `/lab`.
- [ ] **Tool pro vlnu** (dnes ruční skript): `wave.py` z návrhu → klony, financování, rooms s kritériem předem.
- [ ] **Karty, dopředný test:** short karet jen s akciemi (−0,35 až −0,55 % za 72 h), long s kryptem; soudit jen na
      kartách vzniklých po 3. 10. Skript do repa, plán napřed. Nápad k ověření: koncentrace váhy koše (HHI) a počet
      položek předpovídá „Hot" (Nexus NEX-0120 potvrdil mechanismus).
- [ ] **Odpovědi Cymetiky ke sledování:** 2. klon druhu (409, A2A-0055), skilly/modely přes API klíč (A2A-0054),
      report #150 (plán Pro/Free), podání /code-review a push až po deep passu.
- [ ] **Nepotvrzeno, čeká na operátora:** zpráva Cymetice o soukromí zadání v Build it Better (CoStar chce nasazení).

## Meze
Jen paper; žádný nákup skillu/modelu za USDC; MUTATE zůstává trojí brána; Nexus radí, naše strategie se měří,
nevěří se jim před ním. Platební věci a účty patří operátorovi.

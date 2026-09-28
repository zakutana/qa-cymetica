# Deep pass — 2026-09-28 v noci
## Opraveno
- **11 z 30 tvrzení skutečných (11 z auditu, 15 z review, 4 z night-0b), test napřed, tests/meta zelené (807, strop zvednut z 805).** Pár, co přešel na jiný token, teď v tabulkách i košíku nevydělává (B03/R01, 64206a15); room se soudí podle restartu klonu, ne podle toho, že drží peníze (A01/R05, 726ed277); místnost bota hlásí, jestli obchoduje aspoň jeden bot v dávce (A02, 674c1a68); prodej na jeho TP/SL se měří od naší ceny plnění, ne od začátku řady (A03, 7679d720); klon i papírová objednávka odmítnou nezodpovězenou otázku, ne prázdný deník (A05, 2e19ad7c); ztráta bota, jejíž pole nedorazilo, se odmítne, ne počítá jako nula (A06, 4a7c57b3).
- **0b, dokončeno před tímto passem:** Hot blok v briefu, cena podílu Areny přes best bid, memecoiny V3/V4, kontrola openapi rout, kredit Nexuse.
## Co odešlo Cymetice
- **Nic.** Deep pass nic nepodává. Živý ověřovací běh (PRE-0203, level V, 1462 prošlo/11 spadlo) ukázal 5 STILL REPRODUCIBLE + 2 NOT RAISED YET na jejich straně — čeká na příští sweep.
## Změněná pravidla
- **Žádné.**
## Čeká na tebe
- **B04 (3/3 skutečné): 12 rout z jejich stránek chybí v `openapi-public.json`** — blok na Telegram ve scratchpadu (`msg_routes.md`), zapíšu, až řekneš že jsi ho poslal.
- **A08 (1 ze 3, menšina): kontrola stop-lossu soudí „pozice otevřená" jen podle `current_position_side`**, co jsme viděli jen `null` — beze změny.
- **A09–A11 (0 ze 3): zamítnuty jako false positive** (401/403 čtený jako selhání, `deep_failed` bez `auto:true`, sourozenecká stránka co soudí jen anonymní GET).
- Ještě čekají na tvé „zapiš": časovky (`msg_timeouts2.md`), ET-28211 a fronta odpovědí.
## Týden
- **Není splatný.** Poslední 27. 9., příští kolem 4. 10.

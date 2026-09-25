# Deep pass — 2026-09-25 v noci (po dni creator odměn, #130 a redesignu konzole)
## Opraveno
- **30 z 31 skutečných nálezů (44 tvrzení: 34 z auditu 68 kontrol, 10 z review; 3 čtenáři), každý s testem napřed; ověřeno PRE-0178, úroveň V (`run-20260925T225326Z-b7f75212`).** Hlavně: kontroly už neberou nepřečtené nebo prázdné čtení jako „prošlo“; náš vlastní report už laborku nebudí jako jejich novinka; kontrola odkazů creatora četla cizí účet (tg_expire76).
## Co odešlo Cymetice
- **6 ověření: pass na #113, #122, #125, #128, #129; fail na #112 (ET-26924 a ET-26776 dorazily po jejich 24h lhůtě).**
## Změněná pravidla
- **Žádné.** Opravy zpřísnily kontroly, žádné pravidlo neoslabily.
## Čeká na tebe
- **#130: přehled dluží „fail“ (10 z 50 cest pořád bez dokumentace, 40 doplnili v noci) — neposlal jsem ho, řekl jsi, že co dokumentovat je jejich volba; rozhodni, jestli jim to připomenout.**
- **B07 (3/3): tvůj řádek `/channels` (Sonnet · low) v tabulce CLAUDE.md nehlídá žádný test — oprava patří do testu tvých rozhodnutí, na který noční pass nesmí sahat.**
- **R09 (1 ze 3): hero „Rewards“ sčítá bugy a tweety pod jednou měnou — dnes obojí ET10, rozejde se jen když změní měnu bounty.**
- **C03 (1 ze 3): test novinek dává lidské a2a zprávě `auto: False`, skutečná ho nemá — kód je správně, fixture je slabší.**
- **C10 (1 ze 3): `docs/laborator-plan.md:75` pořád píše, že se čte `get_usage` — stará věta v plánu, kód ho nečte.**
- **B06 (1 ze 3): test PATCH klonu hlídá podmnožinu, ne rovnost — `is_paper` přidané na dvě místa by prošlo.**
- **B10 (1 ze 3): klon s neznámým výsledkem financování se při restartu počítá jako 0 v limitu 60 % — dnes takový neexistuje.**
## Co se stalo
- **První plný běh (PRE-0177) zmařilo jejich nasazení uprostřed (openapi/mcp); PRE-0178 platí.** Dvě nové NOT RAISED YET jsou v NEXT.md: parser fund leaderboardu po jejich změně sloupců (naše chyba) a BB-SPEC na cizím ET-26924 (napřed přečíst). Týden není na řadě (poslední 19. 9.); tests/meta 800 → 800, paměť 48.

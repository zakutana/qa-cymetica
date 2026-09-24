# Deep pass — 2026-09-24 večer (po dni creator dashboardu, head-to-head a degen promptů)
## Opraveno
- **Všech 34 skutečných ze 43 nálezů (34 z auditu 259 kontrol, 9 z review), u každého test napřed; ověřeno PRE-0159, úroveň V (`run-20260924T220050Z-24d08821`).** Mezi nimi A01: můj nález „seznam odkazů creatora vynechává odkazy z odpovědí“ byl chybný (jsou vnořené pod stránkami), stažen dřív, než odešel.
## Co odešlo Cymetice
- **6 ověření `pass`, všechna přijata: #113, #114, #122, #124 (2×), #125.** #117, #119 a #123 záměrně ne (NEXT.md).
## Změněná pravidla
- **Žádné.**
## Čeká na tebe
- **R02 (1 ze 3): `clone.py release` smí smazat bota, který obchoduje, když ho nedrží žádný room — nechávám, dva čtenáři to za vadu nemají a mazání navíc hlídá Claude Code.**
- **R06 (1 ze 3): `lab.py adopt` bez `--window-days` zapíše 7 dní, otázka Nexusovi teď slibuje 3 — nechávám, ruční převzetí okno vždy zadává.**
- **R09 (1 ze 3): `release` nezavře spojení, když selže závěrečné čtení po smazání — nechávám, jde o jednorázový příkaz.**
- **ET-26036: verdikt dál čeká na obrazcovou TA** (MSG-0038).
## Co se stalo
- **Jeden bot, jeden room: Trend Titan byl zároveň ve STR-0044 a STR-0045 a zastavení STR-0045 by ho pozastavilo; STR-0045 zastaven a znovu otevřen jako STR-0046 se 4 boty.** Chat Nexuse už hloubkové analýze nebere hodinový limit.
- Plný pass, týden není na řadě (poslední 19. 9.). Prořez: tests/meta 802 → 799, paměť 50 → 48 řádků. Moje chyby dne: dva plné běhy zmařené (commit během běhu a nasazování Cymetiky) a nález na odkazy čtený jen z horní úrovně.

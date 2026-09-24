# Deep pass — 2026-09-24 v noci (po plánu v2 V10, spustila ho tvoje smyčka)
## Opraveno
- **Všech 65 skutečných ze 78 nálezů (31 celé čtení čtyř oblastí, 26 review, 21 audit), test napřed; ověřeno PRE-0156, úroveň V (`run-20260924T020959Z-7d4d6288`).** Detail: commity `a5f7a418`…`240bb802`, `audits/deep-pass-progress.json`.
## Co odešlo Cymetice
- **2 ověření `pass`: #112 a #121 (obě přijata).** #117, #119 a #123 záměrně ne: jejich kontroly čtou naše zápisy a podání z doby před jejich opravou (NEXT.md).
## Změněná pravidla
- **RC1 — řádek, kterému tvoje událost (retire/rebind) vezme poslední kontrolu, smí přejít na UNVERIFIABLE i bez běhu** (3× ne, `3186f2ef`).
- **RC2 — MCP volání s penězi na papíře drží stejný seznam povolených adres jako MUTATE** (3× ne, `3186f2ef`; test v bráně přidán, její pin přepočítán podesáté).
- **RC3 — hlídač zápisů do `state/` vidí i `2>`, `&>`, `>|`, zápis v uvozovkách a v `$( )`; původní čtení běží beze změny jako první** (8 kol, poslední 3× ne, `c03c1c0b`).
## Čeká na tebe
- **H05 (1 ze 3): pojistka B5 v `submit.py` hlídá jen nepodané řádky — nechávám, dva čtenáři cestu k chybě nenašli.** Stačí říct, když to chceš jinak.
- **A08 (1 ze 3): test párování ověření nevolá fold — nechávám, remízu v jedné sekundě nic nevyrobí.**
- **RM04 (1 ze 3): kontrola Hot chce 24 h bez mezery, smyčka v noci stojí, takže číslo nikdy nevrátí — nechávám, n = 0 je poctivá odpověď.**
- **RO04 (1 ze 3): patička reportu „čísla ze živé služby“ stojí i nad čísly z našich souborů (#117, #119, #123) — nechávám, dva čtenáři to za vadu nemají.**
- **ET-26036: verdikt dál čeká na obrazcovou TA** (MSG-0038).
## Co se stalo
- **FOMO a Hot počítaly obchody z nedočtených držení: stop −10 % je −9,6 % na 615 obchodech, ne −20,05 % na 1 024; −10/+100 je +2,5 %, ne −7,3 %; jediný obchod NEX-0055/0057 (+16 %) nebyl dočtený, teď 0** (`f7af1d73`).
- Třetí čtení našlo díru v bráně ověření: běh jedné kontroly pod prereg `tests` dostal úroveň V (Q01, opraveno, žádný dosavadní běh ji nevyužil). Plný pass, 11 % týdne, týden není na řadě. Moje chyba: `c03c1c0b` šel do repa s červeným testem (pipe schoval exit kód), opraveno `d17c00ad`.

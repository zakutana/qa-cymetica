# Deep pass — 2026-09-22 večer (zkráceno 23. 9. na nový tvar, plán v2 V7)
## Opraveno
- **Všech 27 skutečných z 34 nálezů (10 review, 24 audit), test napřed; ověřeno PRE-0152, úroveň V.** Detail: commity od `274c3ce8`, `audits/deep-pass-progress.json`.
## Co odešlo Cymetice
- **2 ověření `pass`: #111 a #120.** #117 a #119 záměrně ne: soudí naše zápisy z doby před jejich opravou (NEXT.md).
## Změněná pravidla
- **RC1 — bezpečnostní brána chce `paper` přesně `True` a čte dávku JSON-RPC po jednotlivých voláních** (3× ne, `0d750746`).
- **V7, 23. 9. mimo pass — deep pass je plný u všeho kromě prózy (dokumentace, NEXT, tahle zpráva), nad 85 % týdne se odloží a nic nezapíše ani nepošle; nedoběhlý pass ohlásí start session a jeho nálezy převezme další; zpráva má 10 řádků plus to, co vidíš a můžeš vetovat.** (5. kolo 3× ne; první čtyři kola, 12 čtenářů, návrh zamítla a každý jejich bod je opravený; test `tests/repo/test_deep_pass_size.py`.)
## Čeká na tebe
- **ET-26036: verdikt dál čeká na obrazcovou TA** (MSG-0038).

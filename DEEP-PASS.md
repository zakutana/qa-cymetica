# Deep pass — 2026-10-02 v noci (Sonnet 5.5, pod řadou Opus 5 xhigh)
## Opraveno
- **18 z 35 tvrzení skutečných (19 skutečných, 1 odloženo), test napřed, tests/meta zelené (811, strop beze změny).** Laborka: bot, který zastavila jejich ochrana, se už nerestartuje ani po odmítnutém enable; POST po timeoutu je `unknown`, ne `not_sent`; peníze uvolněných klonů nejsou v knize (−3 392 USDC); pauza, která bota našla už zastaveného, nezaprotokoluje stop jako náš. Dále `chat.py` (každá chyba po POSTu = `unknown`), čtyři kontroly vůči Cymetice (GeckoTerminal cena správného tokenu, nula týdnů „btc_only“ je inconclusive, `first_pass` není šetření, upside řádku bez `potential_raw`) a osm slabých self-testů (T17 jen z poloviny: další větve gem auditu — `not_cheap`, `rs3m`, `room_x`, poplatkový upside — zatím nemají vyvracející fixture).
- **0b:** nic nepostaveno, každý řádek čekal na Cymetiku nebo na termín (ET-28934 8:20 UTC, ET-29001 14:10 UTC).
## Co odešlo Cymetice
- **Žádný nový report ani verdikt.** Běh PRE-0231 (run-20261002T221708Z-2bc44177, level V): 1486 prošlo, 13 spadlo. `verify.py` jsem nespustil: #143 dluží opravu (selhává znovu, CoinGecko 403/429) a #146 pass by tvrdil „kontrola nepřepsána“, ale pomocná funkce se po novém tooltipu měnila.
## Změněná pravidla
- **Žádné.**
## Čeká na tebe
- **T01: kontrola „hot“ čte datová pole, ne text panelu** — oprava je rozhodnutí (dvě čtení smlouvy; druhá by shodila `derived_identities`), odloženo.
- **Menšina 1 ze 3: T02 T05 T07 T14 T20 T22 (+V03 = T05)** — beze změny (dvě jsou latentní: nulový/`null` živý bod v themes, 404 u odkazu picku jako inconclusive).
- **Dvě nové červené živé kontroly (`derived figures`: 4 témata nesedí s vstupy; `altseason numbers`: mean4 49,0 vs 51,5, index 72 vs breadth 68)** — NOT RAISED YET, založí je příští sweep, deep pass nezakládá.
- **Červené repo testy z dřívějška, ne z tohoto běhu: evidence 1131 MB nad limitem 1000, 53 ztracených captures (cloud 29. 9.), paměť 51 řádků nad 48** — evidence se vyřeší stárnutím captures za 3 dny.
## Týden
- **Není splatný.** Poslední 27. 9., příští kolem 4. 10.

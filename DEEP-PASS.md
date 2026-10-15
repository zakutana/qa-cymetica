# Deep pass — 2026-10-15 (Opus 5.5 xhigh)
## Opraveno
- **31 chyb opraveno ze 38 podezření (32 potvrdili aspoň 2 ze 3 posuzovatelů, 2 menšinová, 4 zamítnutá, 1 nechávám tobě).** Kontroly už nehlásí „v pořádku“ na to, co nepřečetly; Gem Screener kontroly uznávají opravy, které jsme jim navrhli (#206–#209 teď procházejí); laborka počítá se stropem 100 botů; firma řekne manažerovi, když jí odmítnou předání. Z dohodnuté práce hotové 2 kontroly (#141, #202).
- **Ověřovací běh celé sady s předem zapsaným výběrem: 1 658 prošlo, 23 selhalo, 19 přeskočeno; 112 reportů je ověřeně opraveno.** 10 upravených kontrol je připnutých a pohnou se při příštím běhu.
## Co odešlo Cymetice
- **3 ověření: #103 opraveno, #152 a #122 pořád selhávají a obě opravují naše dřívější „opraveno“; dalších 8 zdržuju, dokud nevyloučím chybu na naší straně (#134, #132, #137, #46, #112, #136, #93, #192).**
## Změněná pravidla
- **Strop vlny botů je 100 místo 50, jak teď píše Cymetica; vlna 101 botů se pořád odmítne dřív, než cokoli odejde.** 3 ze 3 čtenářů: nic neoslabuje.
- **Šest hlídacích testů jsem zpřísnil, aby uměly selhat: odmítnuté předání ve firmě, nespustitelný pracovník, stropy botů, pauza desku, okno cen v lize.** 3 ze 3 čtenářů: nic neoslabuje. Úpravu tvého odstavce z 13. 10. v testu ligy jsem nepřijal (1 ze 3), zůstává doslova.
## Čeká na tebe
- **Pojistka na tvoje citáty v kódu hlídá u každého data jen první citát, druhý citát téhož dne jde přepsat bez povšimnutí.** Je to test, který drží tvoje rozhodnutí, a ten deep pass sám neupravuje; napiš „oprav pojistku“ a udělám to.
- **Menšinový názor (1 ze 3): kontrola zásob přeskočí coin s jakýmkoli příznakem, i když měla jen ten s utajeným oběžným množstvím.** Dva čtenáři to nevidí, nechávám beze změny.
- **Menšinový názor (1 ze 3): kontrola turnajového závodu nepozná, že běžec přestal přidávat body.** Dva čtenáři to nevidí, nechávám beze změny.
- **Dvě navržené úpravy laborky čekají na tvoje kliknutí: počítat otevřené pozice event karet ve verdiktu bota, a přizpůsobit laborku automatickému obnovení botů a stropům 100/200.**
- **Spec Gem Screeneru z 5. 10. (Launchpady, vyřazené appky, příjmy a buybacky, velké peněženky) je hotový a čeká na tvoje slovo k podání.** STONK, který tehdy chyběl, už v Gem Screeneru je.
- **Připomínka z 4. 10.: další spec pro Supply Analyzer o stakingu a zámcích (dnes ho zná u 68 z 244 coinů).**

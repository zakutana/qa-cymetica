# Deep pass — 2026-10-18 (Opus 5.5 xhigh)
## Opraveno
- **26 chyb opraveno ze 30 podezření (27 potvrdili aspoň 2 ze 3 posuzovatelů, 2 menšinová, 1 zamítnuté, 1 nechávám tobě).** Devět kontrol Cymetiky už nehlásí „v pořádku“ na to, co nepřečetly; liga už nevypíše výřez cen jako celek; laborka nečte pásmo bota jako hranice karty; firma nedá desku další krok, dokud jeho pracovník běží; pět testů, které nemohly selhat, teď selhat umí; mapa Universe a 3D kancelář mají devět oprav; sběr FOMO má denní strop 10 000 dotazů.
- **Ověřovací běh celé sady s předem zapsaným výběrem: 1 687 prošlo, 20 selhalo, 19 přeskočeno; 130 reportů je ověřeně opraveno (minule 112).** Šest zpřísněných kontrol je připnutých; jediný červený vlastní test je hlídač stropů (níže).
## Co odešlo Cymetice
- **6 ověření „opraveno“: #213 a #214 poprvé (log cen ligy jde stránkovat, formulář chybějícího vkladu má tlačítko mimo skrytou kartu), #202, #204, #205 a #211 znovu pod přísnější kontrolou.** Zdržuju šest „pořád selhává“ (#134, #46, #132, #137, #93, #201), dokud nevyloučím chybu na naší straně, a „opraveno“ na #122, které dnes stojí jen na zavřeném americkém trhu.
## Změněná pravidla
- **Žádné pravidlo se nezměnilo.**
## Čeká na tebe
- **Git má 180 MB proti stropu 150 a za poslední tři dny narostl o 42 MB: nejvíc obrázky mockupů, každý uložený až šestkrát (asi 53 MB za týden), pak deníky (26 MB) a seznam důkazů (18 MB); stránka konzole jen asi 7 MB.** Doporučuju obrázky a deník ligy ukládat mimo git jako důkazy (měsíční archiv) a stránku konzole do commitů nekreslit; strop pak posadit nad dnešek. Zvednout ho je oslabení hlídače, proto čeká na tvoje slovo: „vyndej obrázky z gitu“.
- **Hlídač stropů je červený i proto, že nejstarší otevřený řádek plánu práce má 10 dní (sledování #142, #136, #121, #51 z 8. 10.).** Zhasne, až se ten seznam uzavře; je to dohoda, sám ho nemažu.
- **Pojistka na tvoje citáty v kódu hlídá u každého data jen první citát; druhý citát téhož dne jde přepsat bez povšimnutí.** Podruhé, 3 ze 3 čtenářů; je to test, který drží tvoje rozhodnutí, a ten deep pass sám neupravuje. Napiš „oprav pojistku“ a udělám to.
- **Návrh z ohlédnutí: report podat dřív, než se na tu věc zeptáme zprávou, nebo zprávu a jejich odpověď v reportu citovat.** 11. 10. šly dva reporty půl hodiny po otázce, kterou už Nexus zapsal, a bounty pravidla známé věci vylučují. Napiš „platí“ a zapíšu to do pravidel sweepu.
- **Návrh z ohlédnutí: v pravidlech stojí, že oddělení firmy samo nic nepodává, ale desk podle tvého rozhodnutí z 11. 10. žádosti Build it Better podává; doplním jednu větu s touto výjimkou.** Napiš „doplň“.
- **Menšinový názor (1 ze 3): kontrola, jestli turnajový stůl pozná svého majitele, by poslala falešný FAIL, kdyby Cymetica pustila nastavení bota i divákům.** Dva čtenáři to nevidí, nechávám beze změny.
- **Menšinový názor (1 ze 3): popis jednoho testu vln botů ještě říká strop 50, kód i test drží 100.** Dva čtenáři to za chybu nepovažují.
- **Dvě navržené úpravy laborky (z 15. 10.) čekají na tvoje kliknutí: otevřené pozice event karet ve verdiktu bota, a laborka pro automatické obnovení botů a stropy 100/200.**
- **Spec Gem Screeneru z 5. 10. (Launchpady, vyřazené appky, příjmy a buybacky, velké peněženky) je hotový a čeká na tvoje slovo k podání.**
- **Připomínka z 4. 10.: další spec pro Supply Analyzer o stakingu a zámcích (dnes ho zná u 68 z 244 coinů).**
- **Nový design Build it Better (22. 10., outbox/build-it-better-redesign, 7455461b) čeká, až ho zkontroluješ; nic se nepodává, dokud neřekneš.** Spustí ho `python outbox\build-it-better-redesign\serve.py`, pak http://127.0.0.1:8791/build-it-better.
## Týden
- **Opakuje se jedna chyba: kontroly hlásí „v pořádku“ na to, co nepřečetly (7 z 9 dnešních oprav kontrol, 15. 10. totéž), a denní strop pro FOMO slíbený 11. 10. čekal týden, než ho postavila tahle noc.** Posuzovatelé pořád škrtají (3 ze 30), trojí kontrola se vyplácí; 1 555 testů hlídá nás, 201 měří Cymetiku; 303 commitů Opus, 71 Sonnet, žádné stažení reportu. Tři vnější čtenáři: 15 nálezů; strop FOMO hotový, osm oprav naší strany v plánu práce, nález k #202 vyvrátil text našeho vlastního reportu (sami jsme nabídli „řekněte, že historie může mít díry“).

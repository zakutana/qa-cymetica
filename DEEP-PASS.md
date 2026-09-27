# Deep pass — 2026-09-27 v noci (po sweepu, #133 a Build it Better)
## Opraveno
- **19 z 20 skutečných nálezů (22 tvrzení: 9 z auditu 44 kontrol, 8 z review, 5 z celého čtení laborky; 3 čtenáři), každý s testem napřed; tests/meta zelené (1058).** Kniha a strop laborky počítají nákup s nejistým výsledkem, který přistál; ztráta bota už není volná hotovost; ranní přehled nehlásí zaplacené bugy jako opravené; kontrola a2a (#132) už čte jejich hluboké odpovědi. Ověřovací běh proti Cymetice nešel složit: při PRE-0193, 0194 i 0195 uprostřed nasazovali — čtyři opravené kontroly ověří příští sweep.
## Co odešlo Cymetice
- **Nic.** Jediný dluh je fail na #130 a ten držím podle tebe (co dokumentovat je jejich volba).
## Změněná pravidla
- **Žádné.** Opravy zpřísnily kontroly a testy, žádné pravidlo neoslabily.
## Čeká na tebe
- **R04 (2 ze 3): druhá půlka #133 — stránka Gem Screeneru pořád neukazuje, že refresh selhal (sami v #133 píšou „Not done") — nic to neměří; změřit to znamená nový nárok vůči Cymetice, tak je to na tobě.**
- **#132: dnes v 7:28 odešel „fail" z kontroly, která četla jejich hluboké odpovědi jako automatické (R01); opravená kontrola padá dál, ale už jen proto, že odpovědi na A2A-0017/18/19 nejmenují zprávu, na kterou odpovídají — řeknu ti text na Telegram, jestli chceš.**
- **Návrh (L01, druhá půlka): nákup s nejistým výsledkem, který přistál, se teď počítá do knihy i stropu, ale jeho room je zastavený a nikdo ho neprodá — mám postavit napojení zpět do roomu?**
## Týden
- **20.–27. 9.: 7 passů, 318 tvrzení, triáda zamítla 34 — pořád se vyplácí; nic neměnit.** Opakuje se jedna třída: hlídač, který projde, i když věc, kterou jmenuje, je rozbitá (dnes C01, B01, B02, R03). tests/meta 800 z 1 449 a na stropu; dnešní nálezy padly hlavně na náš kód laborky a přehledu (13 z 20), ne na kontroly proti Cymetice. Commity Opus 5.5 319, Opus 5 140, Sonnet 46; žádný report ze Sonnet sweepu se nestahoval.

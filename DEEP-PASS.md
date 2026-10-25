# Deep pass — 2026-10-25 (Opus 5.5 xhigh)
## Opraveno
- **35 chyb opraveno: 34 ze 43 podezření, která potvrdili aspoň dva ze tří posuzovatelů (4 menšinová, 5 zamítnutých), a 1 z druhého kola.** Nejvážnější: falešný FAIL k už zaplacenému #217 neodejde; 18 kontrol už neprojde na tom, co nepřečetly; report se po chybě disku nepodá dvakrát; denní strop dotazů na memecoiny platí pro všechny procesy; příkaz na katalog Cymetiky zase něco vypíše.
- **Hotová domluvená práce z plánu a ověření celé sady: 1 841 testů prošlo, 16 selhalo (kontroly Cymetiky a hlídač stropů), 117 reportů je ověřeně opraveno.** Laborka čte BTC na začátku a konci okna, commity firmy nenesou cizí soubory, seznam důkazů má zámek, hlídka má denní strop dotazů, firma a outsider mají pět nových pojistek. Z komentářů v kódu mockupu zmizelo slovo, kterým jsi popsal hnědou hlavu farmáře, a hlava je teď zelené proutí, ne hnědé.
## Co odešlo Cymetice
- **4 ověření PASS (#222, #132, #137, #220) a 3 FAIL, které tentokrát přesně říkají, co selhalo (#198, #201, #123); všechna přijata.** FAIL k #112/#136 a k #93 jsem zadržel, rozhodnutí je níž.
## Změněná pravidla
- **Stav kontroly může nově změnit i rozdělení reportu, ale vždy s odkazem na tu událost, a deník rozdělení na neplatnou kontrolu odmítne.** Dřív se takový řádek přesunul bez příčiny a dvě skládání téhož dávala jiný výsledek. Všichni tři čtenáři: nic neoslabuje a tvých rozhodnutí se nedotýká.
## Čeká na tebe
- **#112 a #136: kontrola termínů teď soudí i naše vlastní opožděné žádosti (mezi nimi Airdrop Farmer) a FAIL by znovu otevřel zaplacené zářijové reporty. Zadržel jsem ho; doporučuju soudit jen žádosti cizích lidí.** Napiš „omez kontrolu“.
- **#46: Cymetica 22. 10. odpověděla přesně to, co náš report nabídl uznat jako vadu dokumentace (nástroje jsou vidět, ale bez klíče je nejde zavolat). Doporučuju to tak vést a FAIL už neposílat.** Napiš „#46 jako dokumentace“.
- **#93: jejich dokumentace si odporuje (všechny trasy klonů prý berou klíč, jedna z nich jen přihlášení) a náš FAIL z 21. 10. popisoval tři zářijové trasy místo téhle nové. Doporučuju na ni podat nový report.** Napiš „podej nový“.
- **Platí ještě, že každá zpráva na Telegram jde i přes a2a? 18. 10. jsi řekl „přes a2a nic neposílej“ a od té doby šla dvojčata jen někdy.**
- **Outsidera a Agent League jsi 19. 10. chtěl „úplně vyhodit“, v plánu ale zůstaly: liga měla od 1. 11. jet znovu ve smyčce po 10 minutách. Mám je vyřadit i mimo mockup?**
- **Hlídač stropů je pořád červený: git 207 MB proti 150 (stránka konzole jde skoro do každého commitu), nejstarší řádek plánu 17 dní, paměť 56 řádků proti 48.** Napiš „vyndej obrázky z gitu“.
- **Spec 4 je zkrácený pod limit formuláře (7 967 z 8 000 znaků) a srovnaný s mockupem; podáváš ty.**
- **Menšinový názor (1 ze 3): kontrola stop-lossu zahodí každého zastaveného bota, takže #134 se nikdy nedá ověřit.** Dva čtenáři to berou jako záměr.
- **Menšinový názor (1 ze 3): náhled odkazu Agent Tournaments by mohl projít jen kvůli rozdílu čerstvého a uloženého obrázku.**
- **Menšinový názor (1 ze 3): velmi dlouhé ověření FAIL by mohlo přesáhnout 8 000 znaků; dnes nejdelší má asi 7 000.**
- **Menšinový názor (1 ze 3): na starším Safari by dráhy na úvodní stránce byly ostré kruhy místo mlhy.**
## Týden
- **Opakuje se: kontroly procházejí na tom, co nepřečetly (18 z dnešních 34 oprav, minulý týden 7 z 9), a FAIL z 21. 10. popisovaly zářijový text místo toho, co běh naměřil; ověřovací běh 3,5 dne nešel kvůli 97 MB nesledovaných obrázků.** 521 commitů (424 Opus, 68 Sonnet, 301 z nich mockup firmy); 1 614 testů hlídá nás, 191 měří Cymetiku; laborka a firma celý týden stály; trojí posouzení škrtlo 5 ze 43. Vnější čtenáři dál: šest konceptů Telegramu je v deníku jako odeslané, chyby Build a Company šly přes Telegram místo reportu, 17 kontrol čeká na opravu. Ověřovací běh dnešní noci: run-20261025T015225Z-897c9670 pod PRE-0290.

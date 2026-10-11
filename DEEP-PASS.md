# Deep pass — 2026-10-11 večer (Opus 5.5 xhigh)
## Opraveno
- **33 chyb opraveno ze 43 podezření (33 potvrdili aspoň 2 ze 3 posuzovatelů, 1 menšinové, 9 zamítnutých).** 17 kontrol už nehlásí „v pořádku“ na to, co nepřečetly; laborka počítá prodanou pozici za cenu prodeje, nekupuje znovu kartu, jejíž příkaz selhal, a zkouší znovu bota, kterého se nepodařilo spustit. Archiv FOMO signálů v gitu je po dnech, 87 MB → 5,8 MB.
- **Ověřovací běh celé sady s předem zapsaným výběrem: 1 602 prošlo, 23 selhalo, 13 přeskočeno; 110 reportů je ověřeně opraveno.**
## Co odešlo Cymetice
- **12 ověření: 7× opraveno (#112, #136, #178, #179, #182, #183, #184), 5× pořád selhává (#52, #62, #138, #159, #174), z toho 4 opravují naše dřívější „opraveno“.** Další 3 odejdou při příštím běhu (brzda 12 na běh).
## Změněná pravidla
- **Archiv FOMO signálů se ukládá po dnech a žádný soubor v gitu nesmí přesáhnout 50 MB.** Jinak by zítřejší push spadl na limitu GitHubu (100 MB); 3 ze 3 čtenářů: nic neoslabuje.
- **Žádné oddělení firmy nepíše Cymetice samo; desk ti připraví text a pošleš ho ty.** Tak to už říkalo CLAUDE.md i skill laborky, kód to dovoloval; 3 ze 3 čtenářů: nic neoslabuje.
## Čeká na tebe
- **Pošli Cymetice na Telegram opravu k reportu #156 (STG) a k „většina prošla“ ze 4. 10. (prošla polovina).** Text máš v chatu; kopii do a2a mi zablokovalo povolování, napiš „pošli a2a“, jestli ji chceš.
- **Verdikt nového Gem Screeneru (ET-29379) až po 15. 10.**
## Týden
- **Firmu zatím nezapínej: čtenáři týdne našli 8 děr, které opravím před prvním startem (zápis „odesláno“ za tebe, cizí tikety, špinavý strom, zaseknutý tick); a náš sběr FOMO dat poslal 9. 10. Cymetice 48 557 dotazů, hlavně na nezdokumentovanou adresu, takže dostane denní strop.** Posuzovatelé pořád škrtají (9 ze 43), trojí kontrola se vyplácí; 1 454 testů hlídá nás, 165 měří Cymetiku.

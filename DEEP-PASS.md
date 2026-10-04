# Deep pass — 2026-10-04 v noci (Opus 5.5 xhigh až do kroku 6, závěr Sonnet 5.5)
## Opraveno
- **30 chyb v našich nástrojích je opraveno (z 50 podezření bylo 30 skutečných, 6 sporných, 13 zamítnutých, 1 čeká na tebe).**
- **Dopředný test pravidel pro karty (short jen akcie, long s kryptem) je hotový a soudí karty od 4. 10.; tři testy červené už před dneškem jsou opravené.**
## Co odešlo Cymetice
- **12 ověření: 10× splněno (#123, #131, #134, #145, #146, #147, #148, #149 dvakrát, #150), 2× selhalo (#112 a #136, build zase vychází mimo 24 hodin); dnes dříve šlo ještě hlášení #150 a tři zprávy na Telegram.**
## Změněná pravidla
- **Brzda počtu dotazů už nebere limit jedné cesty (pod 100) za limit celé platformy.** Dva plné běhy kontrol se zastavily na 1 480 z 1 541, protože Chart Analyzer hlásí limit 30 a brzda ho měla za kvótu. Hlasy 2 : 1, že je to v pořádku; menšinový hlas: kdyby každá cesta hlásila limit pod 100, nebo kdyby platforma kvótu snížila, brzda by nezabrala (ve 223 záznamech se to nestalo). Řekni a vrátím.
## Čeká na tebe
- **Ranní stránka pořád kreslí dlaždici Fondy, i když ji stránka laboratoře vyřadila na tvůj pokyn.** Rozhodni, jestli ji ranní stránka nechá.
- **Rozsah držení (3–5 dní), týdny a hodiny nečteme, takže pojmenované držení se bere jako žádné.** 1 čtenář ze 3 to vidí jako chybu, nechal jsem tak.
- **Rozbitý český soubor s názvy hlášení by shodil všechny titulky na ranní stránce.** 1 čtenář ze 3 to vidí jako chybu, nechal jsem tak.
- **Kontrola ranní stránky nepozná, že zmizela celá skupina polí (fondy).** 1 čtenář ze 3 to vidí jako chybu, nechal jsem tak.
- **Test minimální verze Pythonu nezachytí novější zápis textových šablon, takže snížení verze projde, i když kód nepoběží.** 1 čtenář ze 3, nechal jsem tak.
- **Kosmetika: nic nehlídá, že se zapíše smyšlená výše sázky ani řádek brány fondů.** 1 čtenář ze 3, nechal jsem tak.
- **Po změně indikátoru se nečte zpět, jestli platí zadaná hodnota, a bot se přesto bere jako nová varianta.** 1 čtenář ze 3 to vidí jako chybu; hodí se to vyřešit před druhou vlnou.
- **Devět klonů první vlny jsem financoval ručním skriptem (9 × 500 USDC, paper), mimo záznam nástroje.** Wave 0 se soudí kolem 10. 10.; sampler musí běžet.
## Týden
- **Nic neměnit.** Opakovalo se: kontroly čtoucí míň, než tvrdí, a řádky ve stavu „kontrola změněna“ čekaly 3–6 dní na připnutí (dnes připnuto všech šest). 811 z 1 541 testů hlídá náš systém (53 %; 9. 9. to bylo 89 %) a dnešní chyby byly naše, ne Cymetiky. 258 commitů psal Sonnet 5.5 a 142 Opus 5.5; žádná oprava hlášení se nevrací. Triáž zamítla 19 z 50 nálezů, takže se vyplácí; šest součástí je 20–30 dní bez stopy, zatím je neřežu.

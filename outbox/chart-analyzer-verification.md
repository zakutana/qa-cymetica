# Chart Analyzer ET-29001 — ověření živě, 4. 10. 2026 (07:29–08:45 UTC)

Výsledek: **PASS 6 · PARTIAL 5 · FAIL 2 · NOT CHECKABLE 0** (study čísla zvlášť níž). Podáno: **#152, #153, #154, #155**.

| # | Tvrzení Cymeticy | Verdikt | Důkaz (jedna řádka) | Report |
|---|---|---|---|---|
| 1 | Expertní analyzér: struktury na svíčkách, verdikt vlevo, „The numbers ›“ otevře čísla | PASS | BTC 1W: karta verdiktu vlevo (NO EDGE 43 % / 56 %), čáry a klíny na grafu, „The numbers ›“ rozbalí cíl, obě strany, held-out záznam a pravidlo | – |
| 2 | Struktury podle pravidel, dotyky, log trendlines, kanály/klíny/trojúhelníky, vrstvy | PASS | Ve 181 odpovědích všech 11 druhů (support 145 … desc_triangle 1) s dotyky; definice na /chart-analyzer/study; vypnutí vrstvy Trendlines / Weekly Signal čáry skutečně schová a vrátí | – |
| 3 | 5D, 2W, 1M; 5D a 2W z denních/týdenních svíček v pevných blocích; 1M bez verdiktu a stránka to říká | PASS | 5D = 5 denních svíček, bloky od 1. 1. 1970, 199/199 shod OHLCV; 2W = 2 týdny od pondělí, 238/238 shod; 1M od 1. dne měsíce; stránka: „The study does not cover 1M candles … NO EDGE by rule“ | – |
| 4 | Indikátory z jedné studie (17 stavů, 258 párů, 6 TF), záznam pod grafem | PASS | /study/expert: 54 setupů (17 indikátorů, 21 struktur, 16 vzorů), 258 párů, 6 změřených TF + 1M nepokryté; pod grafem „Built on / Tested on“ u každého setupu | – |
| 5 | Weekly Signal sloučen (diamanty, pooled záznam), MACD cross zvlášť, objem zapnutý, „volume surge“ | PARTIAL | Diamanty na 1W, vrstva funguje, /weekly-signal 200, MACD cross i volume_surge jsou setupy, objem zapnutý; ale pooled záznam pořád měří „snadný“ cíl +3 % za 13 týdnů (base 76,6 %), který request výslovně odmítl | – |
| 6 | POP / DUMP / NO EDGE s pravděpodobností, 95% rozpětím, base rate, počtem případů, větou proč; štítek jen při ≥5 b. a ≥300 | PARTIAL | 181 odpovědí (32 symbolů × 6 TF): 14 štítků, všech 14 splňuje pravidlo, 29 NO EDGE s kandidátem má rule_label a větu proč, 0 porušení; ale u 25 ze 105 košů leží pravděpodobnost mimo své „95% rozpětí“ (SOL 5D: 43,1 % vedle 49–56 %) | #154 |
| 7 | Váhy do 2021, kalibrace 2021–22, test od 2023; symetrické cíle; base rate 40–57 % | PARTIAL | Split sedí pro 1d/5d/1w; 1h/4h/2W/1M o dva roky později (stránka to uvádí v limitech); cíle symetrické ±3–30 %; base rate mimo 40–57 % u 2W (test 31,9 / 67,7 %) a 1h kalibrace (38 %) | – |
| 8 | Veřejný ledger výzev, jen uzavřené svíčky, vyhodnocení po okně | FAIL | Výzva BTC/USDT 1h z 06:21 je na svíčce z 26. 10. za cenu 229,26; COTI 1d sedí; 0 vyhodnoceno; ledger plní každé GET /analyze (17 z 19 výzev zapsalo naše čtení) | #153 |
| 9 | Limity: survivorship, bez nákladů, shlukování, prohledané kombinace, režimy | PASS | Všech pět (+ svíčky) je v HTML stránky i /chart-analyzer/study, stejné texty jako v /study/expert `limits` | – |
| 10 | Záznamy na stejném druhu svíček; DEX coin / soubor dostane kresby s poznámkou „not in the study“ | PARTIAL | Poznámka je (Sat Rush, LDO), ale DEX coiny na 1h dostávají READY TO POP/DUMP (SKY, XVS, PENDLE, LDO) a jdou do ledgeru, ač llms.txt říká „no verdict“ | #155 |
| 11 | Jedna obrazovka, vrstvy, 390 px, předání z Gem Screeneru, mladý token na nejdelším TF | PARTIAL | Bez vodorovného scrollu na 390; mladý token (Sat Rush, 25 denních svíček) z odkazu tf=1d sám přešel na 4H s hotovým pohledem; na 390 px je „+ New“ celé mimo obrazovku a „Share“ useknuté (main má overflow-x: clip) | UI poznámka, nepodáno |
| 12 | Pole verdict, structures, setups, indicators, weekly_signal + /calls a /study/expert v openapi, llms.txt, /api-docs | FAIL | llms.txt a /api-docs je popisují; /openapi-public.json je v /analyze nemá a zakazuje navíc klíče (additionalProperties: false); /calls a /study/expert mají schéma {} | #152 |
| 13 | Paleta; pop zelená, dump červená, no edge neutrální | PASS | pop #00ff88, dump #ff4444, no edge #3b82f6 (stejná modrá jako odznak NEUTRAL), vše z palety webu | – |

## Co čísla studie umí a neumí dokázat

1. Zveřejněná čísla (denní DUMP 5 272×, 54,9 % vs 50,3 %; týdenní POP 1 686×, 54,6 % vs 42,3 %; 1h 45,1 % vs 40,4 % a 47,2 % vs 42,6 %) jsou v /study/expert a hits/n i 95% intervaly sedí na 4 desetinná místa.
2. Přepočítal jsem počty verdiktů z jejich vlastních kalibračních tabulek + pravidla + held-out tabulek: 4h, 1d, 5d, 1w, 2W sedí přesně (n i hits); 1h sedí po střetu POP/DUMP (podíl štítků 52,8 % souhlasí).
3. Samotné tabulky (kalibrace, held-out výsledky) bez jejich 258 párů historie od 2017 a jejich kódu přepočítat nejde; „2023+ použito jen jednou“ je tvrzení o procesu, neověřitelné.
4. Čísla jsou tedy vnitřně konzistentní, ne nezávisle ověřená. Kalibrace 2W je o 30 bodů vedle; stránka to přizná a 2W dává NO EDGE.
5. „Denní POP nikdy“ a „5D/4H/2W NO EDGE“ potvrzuje živý vzorek: žádný štítek na 4H/5D/2W, na 1D jen DUMP.

Poznámky: `auto` vybírá nejdelší TF s ≥60 svíčkami (BTC → 1M, kde verdikt nikdy není); je to zdokumentované, ne chyba. Naše čtení zapsalo do jejich ledgeru 17 výzev (GET má vedlejší efekt). Pro test jsem zavřel záložku tab-4 (starý náhled gem-screener-stop-hand.html).

# Supply Analyzer: dá se věřit tomu, co tvrdí? (4. 10. 2026)

Nekontroloval jsem, jestli něco předpovídá. Kontroloval jsem jen to, jestli je pravda každé číslo a každá věta. Měřítko: primární zdroj (blockchain, vlastní API nebo dokumentace projektu). CoinGecko a DeFiLlama beru jen jako sekundární.
Vzorek: **93 coinů**. Všech 32 „measured“, všech 19 „unknown“, 40 „range“ (4 pásma podle velikosti, v každém 5 s velkým spáleným řezem nebo buybackem a 5 náhodných), 5 největších podle mcap (ETH, BNB, XRP, SOL, TRX) a PHAR. Záznamy jsou z cache s `refreshed_at` 06:46–07:5x UTC, zdroje jsem četl 10:20–10:55 UTC.
**Dokázat můžu, že tvrzení je nepravdivé, nebo že sedí se zdrojem. Že je všechno pravda, dokázat nemůžu.** Počty toho, co šlo a nešlo ověřit, jsou v tabulce.

## 1. PHAR (případ od operátora)

| Co tvrdí záznam / stránka | Primární zdroj (Avalanche, docs.phar.gg) | Verdikt |
|---|---|---|
| total supply 530 628 031 | `totalSupply()` 530 627 320 | PRAVDA |
| circulating 33 493 321 (CoinGecko) | supply mimo xPHAR: 530,63M − 497,14M = 33,49M | PRAVDA |
| „Staked, free to unlock“ 11 351 535 (staking TVL z DeFiLlama) | v kontraktu xPHAR leží **497 139 188 PHAR** (93,7 % supply); z 994,3M xPHAR je **992,7M stakováno** ve VoteModule; výstup z xPHAR stojí 50 % | **NEPRAVDA** (44× méně) |
| „Reserve, outside the pie“ 497 134 710, „vstoupí do hromady jen rozhodnutím projektu“ | jsou to **přesně ty PHAR, které drží zamčené holdeři** v xPHAR | **NEPRAVDA** (zavádějící) |
| „Bought back, burned“ 469 371 969 (93 % koláče) | `MAX_SUPPLY()` 1 000 000 000; Minter **1. 10. vyrazil 4 939 305 PHAR** (tx 0x97a2069d…), takže část rozdílu jsou nevydané tokeny | **NEPRAVDA** (část nespálená) |
| emise 22,88M za měsíc | Minter `weeklyEmissions()` 4 939 305, tj. 21,5M za 30,4 dne | PRAVDA (±7 %) |
| buyback 21,7M za měsíc | DeFiLlama: poplatky jsou „distributed to xPHAR voters“, žádný nákup | **NEPRAVDA** |
| ředění +41,6 % až +54 % za rok, Flooding 1/10 | směr sedí (Flooding), ale číslo stojí na falešném buybacku; bez něj by přítok převyšoval celou hromadu (33,5M) několikanásobně | číslo NEPRAVDA, pásmo sedí |

**Čtenáře zmate:** koláč tvrdí, že 93 % PHAR je spálených nebo v rezervě projektu a skoro nic není stakováno. Ve skutečnosti mají holdeři 93,7 % PHAR zamčených v xPHAR. **Podáno #163** (rezerva a staking), spálený řez spadá pod #156, buyback pod #157.

## 2. Mapa důvěry (vzorek 93 coinů, 93 záznamů)

| Pole | Ověřeno | PRAVDA | NEPRAVDA | Neověřitelné | Poznámka |
|---|---|---|---|---|---|
| circulating, total, max proti CoinGecko | 92 | 92 | 0 | 1 (SUI chain nemá vlastní záznam) | věrně opisuje svůj zdroj; nezávislé to není |
| total supply na řetězci | 54 | 38 | 16 | 39 (nativní coiny) | 6 z 16 je bridge nebo jen část supply (MOR, OKB, HYPER, WLFI, ZRO, STRK), u 10 CoinGecko nepočítá tokeny na burn adresách (SD, LISTA, VVV, CRO, ETHFI, APEX, STG, TREE, OVER, CFG) |
| primární supply nativních coinů | 3 | 2 (SOL, XRP) | 1 (HYPE) | ETH, BNB, TRX | HYPE: circ 222,4M proti 298,6M z API Hyperliquidu |
| cena (snapshot 02:37 proti živé) | 92 | 90 | 2 (SD, BTW) | – | tolerance 10 % |
| odvozené: roční %, tlak, pásmo z vlastního měsíce 0 | 73 | **73** | 0 | 20 (unknown) | vzorec z /definitions použitý správně |
| „Bought back, burned“ | 39 | 7 (LISTA, VVV, CRO, APEX, STG, TREE, OVER: burn adresy to drží) | **22** | 10 | u ETH, SOL, TRX, FIL, MON, XTZ, VELO, CFG a UP je „max“ konec emisního plánu z DeFiLlama |
| emise ze vstupu se opravdu počítají | 43 | 30 | **13** | – | rezerva vyčerpaná řezem „spáleno“ nebo stakingem navíc |
| hromada ≤ celé supply | 92 | 88 | 4 (ve vzorku; ve všech 244 záznamech 17) | – | #158 |
| rozsah přičítá uvedený typický přítok 12,34 % | 41 | 3 | **38** | – | 5,0 / 10,68 / 15,08 %… (#159) |
| „next unlock: none scheduled“ | 55 | 0 | **55** (174 ze 244) | – | vesting neznámý, a přesto „none“ (#164) |
| max supply jako strop | 48 (kontrola) | 18 bez nálezu | **30** | – | max = konec plánu DeFiLlama (ETH 127,9M, SOL, TRX), **podáno #165** |
| buyback = nákup tokenu | 23 (Squeezing nebo vysychající) | 2 (PONS, BEAN) | **9** | 12 | DeFiLlama: výplaty lockerům (#157) |
| staked | 11 | 0 | 11 (PHAR na řetězci; 10 záznamů z celé populace má staked > total supply) | zbytek | stakingové kontrakty ostatních jsem nečetl, HYPE bere staking z API projektu |
| datum dalšího unlocku | 58 datovaných | – | HYPE: 28. 10. proti 6. 10. u třetích stran (rozpor, nedokázáno) | 57 | 31 z 58 leží přesně na 3. 11. (měsíční mřížka u lineárního vestingu) |
| poctivost „unknown“ (19) | 19 | 17 (feed opravdu nic nemá) | **2** (ARB, STRK: DeFiLlama má unlocky 15. a 30. 10.) | – | #164 |
| přiřazení zdrojů | 16 | 1 (odkaz HYPE na staking) | **15** | – | HYPE „kept“ přiřazené stránce, která říká „burned“, mrtvý odkaz na vesting (#159); u 13 záznamů `burned_so_far` píše „(CoinGecko figures)“, ale max je z DeFiLlama |

**Spolehlivé:** supply a cena tak, jak je hlásí CoinGecko (opsané věrně), a aritmetika vzorce (tlak a pásmo z vlastních vstupů).
**Nespolehlivé:** řez „spáleno“, rezerva, staking, buyback, „none scheduled“, max supply u inflačních coinů a šířka rozsahu.

## 3. Záznamy, na které se nespoléhat vůbec

| Coin | Proč |
|---|---|
| PHAR | rezerva, staking, spáleno i buyback jsou chybně, koláč nedává smysl |
| ORE, BEAN | známé emise vynulované, ukazuje Squeezing; ve skutečnosti se těží |
| GIGA, ABX, TITN, KITTEN, BLACK, BEND, RAM, MET, TOPAZ | „buyback“ jsou výplaty lockerům, Squeezing je nepravda, hromada vysychá |
| CRV, THOR, FOX, RAIL, BIFI, OHM, GMX, LON, LQTY, CVX, INV | hromada je větší než celá supply |
| ARB, STRK | „?“ a „none scheduled“, přitom 15. a 30. 10. odemykají |
| ETH, SOL, TRX | „max supply“ a „spáleno“ jsou jen budoucí emise z plánu DeFiLlama |

## 4. Pět nejdůležitějších nepravd

1. **ORE: 10/10 Squeezing, −52 % za rok, „buybacky převažují 543 : 1“.** Záznam sám uvádí 42 098 nově vytěžených ORE za měsíc, ale počítá jich 40 (#156).
2. **PHAR: „Reserve 497M“ a „Bought back, burned 469M“.** Na řetězci je 497M zamčeno holdery v xPHAR a Minter dál razí (#163, #156).
3. **ARB: další unlock „none scheduled“, tlak „?“.** DeFiLlama hlásí 92,6M ARB na 15. 10. (#164).
4. **GIGA −582 % za rok, Squeezing.** „Buyback“ ve skutečnosti znamená poplatky vyplacené veGIGA stakerům (#157).
5. **CRV: prodejná hromada 3,25B při celkové supply 2,42B** (#158).

## Čtení (počet požadavků podle endpointu, 4. 10.)

| Kde | Kolik |
|---|---|
| Cymetica `/supply-analyzer/analyze`, fáze 1 (scratch) | 399, z toho 6 kontraktů mimo Gem Screener (ledger 245 → 251, uvedeno v #160) |
| Cymetica `/supply-analyzer/analyze`, kontroly (9 běhů, z toho 4 celé) | 426 |
| Cymetica `/batch/gem-screener` · `/definitions` · `/coverage` · `/ledger` | 9 · 6 · 2 · 2 (+ asi 9 batchů z otevřených stránek Gem Screeneru) |
| Cymetica `/api/v1/gem-screener` (snapshot) | 7 |
| Cymetica stránky, dokumenty, WS, MCP | asi 20 (stránky a dokumenty), 4 WS subscribe, 3 MCP |
| CoinGecko `/coins/{id}` | 92 |
| RPC (eth, bsc, arb, base, sol, avax) | asi 190 (totalSupply, decimals, burn adresy, PHAR a xPHAR, logy mintu) |
| Routescan (Avalanche) | 4 ručně + 4 za každý běh kontroly |
| DeFiLlama (fees methodology · emissions) | asi 100 · asi 210 |
| Hyperliquid API a docs, Solana a XRPL RPC, docs.phar.gg, Tokenomist, Blockworks, CMC | asi 15 |

Analyzer jsem četl jen GETem a v kontrolách jen pro mince Gem Screeneru, takže do jejich ledgeru nic nepřidávají.

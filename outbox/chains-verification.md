# Gem Screener, záložka Chains: sedí čísla a Upside? (2026-10-04)

Snapshot z 08:47 UTC (nový pokus v 15:03 neprošel jejich auditem, stránka dál ukazuje 08:47), všech 33 chainů, přepočteno z nezávislých zdrojů mezi 14:20 a 15:15 UTC. Neověřuju, jestli cokoli předpovídá budoucnost.

## Co jsem ověřil

| Číslo | Zdroj | Výsledek | Důkaz |
|---|---|---|---|
| Uživatelé za den | DeFiLlama `api.llama.fi/summary/active-users/{chain}`, nižší z mediánu 30 a 90 dní | **33/33 přesně** | Solana 2 246 323 = medián 90 dní, medián 30 dní 2 704 094 |
| DEX objem 30 dní | DeFiLlama `api.llama.fi/overview/dexs/{chain}` | **33/33 přesně** | součet 30 dní do 3. 10. |
| TVL | DeFiLlama `api.llama.fi/v2/historicalChainTvl/{chain}` | **31/33 do 2 %**, 33/33 do 5 % | X Layer 2,1 %, Tezos 4,4 %: DeFiLlama dnešní bod přes den přepisuje; proti včerejší uzávěrce oba do 1,2 % |
| Stablecoiny | DeFiLlama `stablecoins.llama.fi/stablecoincharts/{chain}` | **31/33 do 2,5 %** (27 do 0,9 %), Stellar −7,6 %, Sei −10,7 % | stránka ukazuje počet tokenů (33/33 přesně), ne dolary; USDY stojí 1,147 $ (Stellar 840,9M místo 909,7M) → **#167** |
| Market cap, cena, oběžná zásoba | CoinGecko `coins/markets` | **33/33** (zásoba přesně, cena a mcap medián 0,3 % po 6 h) | mcap = cena × zásoba 33/33 do 0,01 % |
| FDV | CoinGecko | 32/33 do 5 % | Starknet −7,4 % = pohyb ceny za 6 h (mcap stejně) |
| Hranice „held back“ (80. percentil) | jejich pravidlo, přepočteno z 33 chainů | **3/3 přesně** | lineární percentil, např. 5,869× TVL za 30 dní |
| Započtení uživatelé a objem, „held back“ | jejich pravidlo | **33/33** | Solana: objem 77,4 mld. → 39,3 mld. (49 % zadrženo) |
| Adoption = 4. odmocnina ze 4 vstupů | jejich definice | **33/33 přesně** | |
| Price tag = mcap ÷ adoption | jejich definice | **33/33** | |
| Benchmark 128× | medián chainů s mcap ≥ 1 mld. $, rokem dat, čerstvými vstupy, ≤ polovinou zadrženo | **19/19 stejní členové, medián 127,927 přesně** | Near vyřazen správně (78 % objemu zadrženo), 13 pod 1 mld. správně |
| Upside = benchmark ÷ price tag | jejich definice | **33/33** | „Worth at median price“ (mcap i cena) 33/33 |
| Řazení podle Upside | prohlížeč | **správně** v obou režimech | |
| Filtr Vetted only / All | prohlížeč | **24 / 33** | 9 neprověřených, odpovídá `reliable` |
| 30x test | jejich definice | **33/33** | |
| Síla 3M | poměr stablecoinů ÷ poměr ceny | poměr 33/33 | samotnou hladinu stablecoinů z popsané definice nezopakuju (sedí 1 ze 4 bodů) — díra v dokumentaci |
| Měsíční stablecoiny a DEX v detailu | DeFiLlama | **390/390 a 380/380 měsíců do 1 %** | |
| 12 měsíců (poplatky) | jejich pravidlo s ochranami | nepřepočteno | souhrn DeFiLlama má jinou skladbu (13/32 do 2 %); do Upside nevstupuje |
| Vrstva L1/L2 | CoinGecko kategorie | 32/33 | Polygon ukázán jako L1, CoinGecko ho má v layer-2; zdroj sloupce stránka neuvádí |
| Chart score | Chart Analyzer (jejich služba) | 15/19 stejně | 4 rozdílné jsou na novější svíčce |
| API `ranked?kind=chains` vs stránka | | **33/33** | |
| Stejný coin na Apps a Chains (HYPE, SUI, NEAR) | | **3/3** | |
| Proč chain chybí (27 tokenů) | DeFiLlama, CoinGecko | 25/27 sedí | BCH a ETC: „no market data“, ale CoinGecko je má (6,4 mld. / 1,4 mld. $); BCH ve skutečnosti chybí stablecoiny, ETC objem DEX; ve snapshotu z 04:10 totéž u ZEC, VET, THETA → **#170** |

## Benchmark

- Na Chains je benchmark **128× adoption = medián 19 velkých chainů**; přepočteno: stejných 19 chainů, stejný medián. Hyperliquidových 34,6× (mcap 20,16 mld. ÷ výnos 582,9M/rok, 90denní průměr DeFiLlama) patří jen záložce Apps, sedí, a do Upside chainu nevstupuje.
- Upside každého chainu = 127,9 ÷ jeho price tag, 33/33. Obě strany jsou ve stejné jednotce (adoption mísí adresy a dolary), takže poměr jednotku nemá a je srovnatelný; „128× adoption“ samo o sobě není obyčejný násobek, smysl má jen poměr.
- **Ano: Upside je podle jejich vlastního benchmarku spočítaný správně a konzistentně.**

## Kdy se na to dá spolehnout

- **Spolehlivé:** uživatelé, DEX objem, TVL, market cap, cena, adoption, price tag, benchmark, Upside, „Worth at median price“, řazení a filtry. Upside u Stellaru a Seie je kvůli stablecoinům o 2–3 % nízko, jinak nic.
- **Nespolehlivé:** částka **Stablecoiny** u **Stellaru (−7,6 %)** a **Seie (−10,7 %)** — je to počet tokenů, ne dolary.
- **Pozor na slovo „Adoption“:** „Adoption growth 6M“, trajektorie a štítky Declining/Post-crash (podle nich se chain schová ve „Vetted only“) počítají jen stablecoiny a DEX objem, ne čtyřsložkovou adopci ze sloupce. Mantle, Algorand, Filecoin, Starknet, Sui, Hedera, Stable, Plasma a Gnosis jsou „neprověřené“ podle této druhé řady.
- **Dokumentace pro agenty lže:** llms.txt v úvodu Gem Screeneru pořád píše, že chain se oceňuje ročními poplatky proti jednomu vedoucímu chainu; prompt „Paste into your agent“ v detailu chainu chce „adoption (daily users and fees)“ a „benchmark chain“. Živě je to adoption a medián.
- Vedlejší nález: jejich cache v 15:01 servírovala `?view=apps` ze snapshotu o 4,6 h staršího než `?view=chains` (stránka to přiznává textem „Updated … ago“).

## Nahlášeno (2026-10-04, run 150807Z-8d234df9, level R)

- **#167** stablecoiny jsou počet tokenů, ne dolary (Stellar, Sei)
- **#168** llms.txt a prompt pro agenta popisují staré ocenění chainů (poplatky, vedoucí chain)
- **#169** „Adoption“ jsou dvě různá čísla; prověření chainů stojí na stablecoinech a DEX
- **#170** BCH a ETC „bez tržních dat“, přitom je CoinGecko má

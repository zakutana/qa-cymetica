# Supply Analyzer (ET-28934) — ověření, fáze 1 (jen čtení)

**Podáno (fáze 2, 10:1x UTC):** #156 spálený řez (A), #157 výplaty jako buyback (B), #158 pile > zásoba (C), #159 Hyperliquid + odkaz + typical (D, E), #160 chain → 500 (F), #161 dvě ředění (G), #162 ORE „100 % venku“ (NEXT ř. 54). Nepodáno: H (lineární vesting na mřížce) a souhrnná drobnost, protože jde o formu, ne o nepravdivé číslo. Fold `run-20261004T100022Z-c88f949b`, level R.

Okno: čtení 2026-10-04 08:45–09:21 UTC. Záznamy analyzátoru mají `refreshed_at` 06:46–07:5x UTC, všechny `from_cache`, `next_refresh_ts` ≈ 2026-10-05 06:46 UTC. Analyzátor čte snapshot Gem Screeneru z 02:37 UTC, stránka Gem Screeneru už ten z 08:47 UTC. ET-28934 na tabuli: `shipped` 08:38:43 UTC, `on_time: false`, `verdict: null`.
Vzorek: všech 244 mincí jednotlivě (`/analyze?symbol=<slug>`, 243× 200, HYPE přes ticker), `/batch/gem-screener`, 135 identifikátorů z odkazů Gem Screeneru, 13 kontraktů, 2 WebSocket a 3 MCP volání, 5 karet a 2 deep linky v prohlížeči (desktop a 390 px).
Surová data: `scratchpad/.../sa/raw/` (mimo repo, bez evidence id).

**Pro fázi 2:** zítra v 06:46 UTC se záznamy přepočítají a čísla u E (možná i u A–C) se pohnou. Proto je potřeba dnes přečíst znovu přes `qa.client`. Jako první uložit „(5.0% a year)“ na `?symbol=HYPE`. A, C, F a odkaz na HYPE z D jsou deterministické, každý stačí potvrdit jedním GET.

## Kontroly

| # | Kontrola | Výsledek | Důkaz |
|---|---|---|---|
| 1 | Vnitřní konzistence 244 mincí | FAIL | Platí: řezy = in_play, pile = free + staked_free, yearly v rozsahu, pressure/band/tone podle /definitions (244/244), statusy 193/32/19. Neplatí: in_play > max u 23, **pile > total supply u 17**, total > max u 8, slices + reserve > max v posledním měsíci u 167/220, pile klesne na 0 u 8. |
| 2 | Single = batch = WS = MCP | PASS | 243/243 záznamů je shodných s `/batch/gem-screener` při stejném `refreshed_at`. WS (HYPE, ALCX) se shoduje s REST na 100 %, MCP `supply_analyzer_token` taky (navíc jen `success`). MCP batch = REST batch. |
| 3 | Kontrakt + chain | PARTIAL | UNI/eth, CAKE/bsc a JUP/sol se najdou přes Gem Screener (UNI: circ 625M, max 1B; CAKE: max 400M). PEPE/eth, BabyDoge/bsc a WIF/sol vrátí `unknown` bez pile, což je zdokumentovaný limit („known only when DeFiLlama lists the protocol“). Chyby: 0x123 → 400, ZZZQQQ → 404, INDEX → 300, bez chainu → 400 CHAIN_NEEDED. **Nepodporovaný chain → 500** (4×). |
| 4 | Pravidlo „>25 % apart“ | PASS | 55 záznamů s položkou má všechny poměr > 1,25, 61 bez položky má všechny ≤ 1,25, 127 nemá číslo z DeFiLlama. Drobnost: 15 položek píše „used: CoinGecko circulating“, i když vstup pochází z DeFiLlama. |
| 5 | HYPE: další unlock a komu | FAIL | Analyzátor: 9,92M pro core contributors **28. 10. 2026** (23,7 d), poslední tranše 28. 10. 2027. Tokenomist: další unlock 6. 10. 2026, core contributors. Blockworks filing: 9,92M 6. 9. 2026, vesting „completing between 2027 and 2028“. CMC cituje spoluzakladatele: „on the sixth of each month“. Citovaný zdroj (hyperliquid docs …/hype-and-staking) vrací **404** (2× čteno). Částka a příjemce sedí. Ostatní mince: 58 datovaných unlocků z DeFiLlama, **31 z nich přesně 2026-11-03 00:00** (měsíční mřížka). |
| 6 | Řez „Bought back, burned“ | FAIL | 80 mincí, zdroj je u všech „max supply minus total supply“, `estimated:false`, `as_of:null`, a zároveň všech 80 píše burns „unknown, counted as 0“. Řez má ≥25 % koláče u 32 mincí a ≥50 % u 15. PHAR 93 %, ORE 83 % (ORE se těží, jeho vlastní `emissions_month` = 42 098). |
| 7 | NEXT ř. 54 (FDV / 100 % venku) | FAIL | Gem Screener ukazuje ~100 % venku při circ/max < 90 % u **9 z 211** apek (3. 10. jich bylo 17 z 214). ORE: v Checks pořád „100% of tokens out“, `fdv` = `mcap`. Analyzátor bere max 3M, ale 2,5M (83 %) dává do „Bought back, burned“, ne do rezervy. |
| 8 | Gem Screener v prohlížeči | PARTIAL | Sloupec Supply je na Apps i Chains, řadí podle `pressure` z API (10→1, unknown na konci). Karta = API u 5/5 (HYPE, ORE, PHAR, CRV, UNI). Mcap je ze snapshotu Gem Screeneru, proto HYPE $20,2bn vs $19,93B. Odkaz má `_blank` + `noopener`. **Odkaz na Hyperliquid (obě řádky) otevře „Not in the Gem Screener“.** Deep linky `?symbol=HYPE` a `?contract=…&chain=ethereum` = API. Při 390 px se stránka do strany neposouvá, ale nádrž (560 px) je ořízlá ve vnitřním 257px scrolleru. Checks a karta si odporují (HYPE 0 % / 0 % vs +1 % / 9,9M za 24 d). |
| 9 | Agentní povrch | PASS | WS: hello → identity → analysis za 1,9 s, chyby UNKNOWN_SYMBOL/AMBIGUOUS_TICKER. Oba MCP tooly jsou v `/.well-known/mcp.json`, `tools/list` (111), `/llms.txt` (s poli), `/api-docs` a agent card. Anonymní volání funguje. OpenAPI: všechna zdokumentovaná pole jsou živě. Odchylky: `/definitions` má v schématu `pressure`, živě `pressure_bands`; `pressure:null` u unknown, ačkoli je required integer; 500 není v dokumentaci. |
| 10 | Ledger | PASS | `{lines:245, weeks:[2026-W40], weeks_needed:26, result:"no result yet"}`, stránka tvrdí totéž, nikde nic skórovaného. Obsah řádků NOT CHECKABLE (API dává jen počet; 245 řádků vs 244 mincí je nevysvětlené). |
| 11 | Uvedené limity na stránce | PASS | `<details id="saHow">` › `<h2>What this version does not do</h2>`: ticker jen mezi mincemi Gem Screeneru, ručně zadaný harmonogram pro tokeny v seznamu zdrojů (jen hyperliquid), staking flow a fee burns se neměří. |

Shrnutí: PASS 5, PARTIAL 2, FAIL 4, NOT CHECKABLE 0 (obsah ledgeru je poznámka v ř. 10).

## Kandidáti na hlášení

**A. „max − total“ vydávané za spálené tokeny maže známé emise.** Medium-high.
Důkaz: u ORE je `burned_so_far` 2 499 496 („max supply minus total supply“) a rezerva 40. Vlastní vstup `emissions_month` = 42 098, ale měsíc 0 počítá s přítokem 40. Výsledek je −52 %/rok, 10/10 Squeezing a „Buybacks outweigh new tokens 543 to 1“. Pile je v září 2028 na 0. Gem Screener pro ORE ukazuje emise $3,0M/30 d (1,07 %/týden, červená), karta Supply „under 0.1%“. Přítok se kvůli vyčerpané rezervě ořízne u 27 záznamů a u 9 z nich se mění pásmo: ORE, BEAN a FWA ze Squeezing na Flooding, THOR na Balanced, QI/RSUP/VVV/SNX/AVAX z Balanced na Flooding. Při řazení sloupce Supply stojí ORE nahoře.
Proč defekt: stránka sama píše „burns count as 0, both named as unknown“, a přesto hlásí 80 mincí se spáleným řezem jako změřený fakt. Odporuje to i pravidlu „unknown is never zero“: tady je nulová dokonce známá emise.

**B. Holders' revenue z DeFiLlama se počítá jako buyback.** Medium.
Důkaz: vzali jsme 15 mincí s největším „buybackem“ vůči pile. Podle metodiky samotného DeFiLlama (`HoldersRevenue`) jde u 12 z nich o rozdělování poplatků lockerům/voterům, ne o nákup tokenu: PHAR, TOPAZ, GIGA, ABX, UP, HYBR, TITN, NEST, RAM, BEND, KITTEN, BLACK. Skutečný buyback mají jen PONS a BEAN, DUST je smíšený. 7 z těch 12 je na stránce Squeezing a u 6 z nich „buyback“ vysaje celou pile, než křivka skončí (GIGA za 3 měsíce, ABX za 4, TITN za 7). RAM je ve sloupci druhá nahoře.
Proč defekt: `/definitions` tvrdí „(the share of fees that buys the token)“ a uvádí `estimated:false`. Vlastní zdroj analyzátoru přitom říká opak.

**C. Prodejná pile větší než celá zásoba.** Medium.
Důkaz: `pile_today` > total supply u 17 mincí, třeba CRV 3,25B proti 2,42B, PENDLE, CVX, GMX, USUAL. `staked_total` > total supply u 10 mincí, třeba BIFI staked 107K proti max 80K. In_play > max u 23 mincí, kde se rezerva ořízne na 0 (a to podle A smaže emise).
Proč defekt: větší než celá zásoba to být nemůže. Pravděpodobná příčina je, že se staking přičítá k circulating, která ho už obsahuje (`circulating_includes_staked:false` u CRV, PENDLE, CVX…). To je ale náš úsudek, ne jejich text.

**D. Hyperliquid, jejich vlajkový příklad.** Medium.
1. Stránka připisuje „kept“ docs Hyperliquidu („Hyperliquid docs: Fees … says kept“), jenže tatáž stránka docs (čteno 08:49 UTC) říká „HYPE in the assistance fund is burned“. Blockworks navíc uvádí hlasování validátorů 24. 12. 2025.
2. Odkaz na vesting (…/hyperliquid-l1/hype-and-staking) vrací 404.
3. Další unlock 28. 10. proti 6. dni v měsíci, jak ho uvádějí třetí strany, které citují tým (Tokenomist: 6. 10.).
4. Odkaz „Open in Supply Analyzer“ z Gem Screeneru vede na `?symbol=hyperliquid` a skončí na 404 / „Not in the Gem Screener“, přestože `symbol` je zdokumentovaný jako „slug or CoinGecko id“. Platí pro obě řádky Hyperliquidu. Ostatních 240 identifikátorů se najde správně.
Proč defekt: tvrzení i odkaz jsou chybné vůči jejich vlastnímu zdroji a vůči jejich dokumentaci parametru.

**E. „Typical inflow“ není jedno číslo.** Low-medium.
Důkaz: `/definitions` i batch píšou 12,34 % (medián 32 změřených, „5% until ten are measured“). Přesto 173 ze 185 range záznamů s neznámým přítokem používá 5,0 / 9,71 / 10,68 / 12,88 / 14,55 / 15,08 %, z toho 5,0 % u 56 mincí včetně HYPE. Na stránce HYPE stojí „(5.0% a year)“ vedle „12.3%“ ve sbaleném bloku. 61 rozsahů pressure by se při uvedených 12,34 % změnilo (LDO [6,8] → [3,8]).
Postřeh, ne samostatná vada: u 106 mincí je hero číslo horní konec rozsahu (je v něm odhad) a věta „grows 9.6M a month“ (CARDS) tak vydává odhad za fakt. U 79 mincí je hero dolní konec.

**F. Nepodporovaný chain vrací 500.** Low.
Důkaz: `chain=dogechain`, `foo` i `tron` → 500 INTERNAL_SERVER_ERROR (4 čtení). OpenAPI přitom uvádí 400 UNSUPPORTED_CHAIN. `chain=solana` u tokenu mimo Gem Screener projde bez chyby, jen bez totalSupply, i když dokumentované chainy jsou jen EVM.

**G. Detail v Gem Screeneru si sám odporuje (spec bod 10).** Low-medium.
Důkaz: u HYPE ukazuje řádek Checks „0% unlock in 90 days, 0% new tokens a week“, karta Supply „+1%, Heavy dilution, 9.9M in 24 days“ a tooltip „Hyperliquid, the benchmark: 0% a week“. U ORE ukazuje Checks „1% new tokens a week“ a karta „under 0.1%“. ORE má v Checks dál „100% of tokens out“, což je NEXT ř. 54, teď 9 z 211.

**H. Lineární vesting zobrazený jako jedna tranše na měsíční mřížce.** Low.
Důkaz: 31 z 58 datovaných „next unlock“ vychází přesně na 2026-11-03 00:00 UTC. U ENA, KMNO a ETHFI DeFiLlama typuje unlock jako `linear` (průběžný), karta ale píše „in 30 days · 82M tokens to Core Contributors“.

**Jedna souhrnná zpráva (formulace a drobnosti).** Low.
- Koláč v budoucích měsících: emise jsou současně v `paid_out` i ve `free` (51 záznamů), takže slices + reserve > max.
- `estimated` není nikde true (0 vstupů), ačkoli buyback „at today's price“ je podle jejich vlastní definice odhad.
- `burned_so_far` nemá `as_of`.
- 15 položek má štítek „CoinGecko“ u čísla z DeFiLlama.
- `pressure` vs `pressure_bands` v OpenAPI.
- Při 390 px je nádrž ořízlá v neoznačeném vnitřním scrolleru.
- UNI zadaný kontraktem na ethereu vrací `chain: arbitrum` s jinou adresou.

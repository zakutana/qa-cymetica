# Kam dál zapsat Gem Screener & spol. (rešerše 4. 10. 2026)

**Produkty (ověřeno na jejich stránkách):** Gem Screener (zdarma, REST/WS/MCP bez klíče) · Chart Analyzer (verdikt POP/DUMP/NO EDGE, zdarma API) · Supply Analyzer (supply jako tok, tlak 1–10, zdarma API) · **Build it Better je placený** (Pro/Max, 0,5 unit za request) → nehodí se do seznamů „free API“, jen na launch weby a AI adresáře.
MCP endpoint: `https://cymetica.com/mcp/v1` · llms.txt: `https://cymetica.com/llms.txt` · OpenAPI se všemi čtyřmi: `https://cymetica.com/openapi-public.json` (326 cest; `/openapi.json` má jen 23 cest bez nich).

**Jak jsem soudil publikum:** jen čísla přímo na stránce (počet záznamů, vlastní údaje webu) a u GitHubu hvězdy + poslední commit z GitHub API. SimilarWeb nikde → návštěvnost je všude **NEOVĚŘENÁ**. Minuty jsou můj odhad. Laťka „staré“: poslední commit/záznam starší než 12 měsíců.

| # | Místo | Co to je | Produkt | Zdarma? | Min | Čekání | Kdo podává | Odkaz | Pravidlo / riziko | Stav |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | mcpservers.org | MCP adresář (sem posílá i wong2/awesome-mcp-servers, 4,3k★) | Cymetica MCP | ano ($39 = do 24 h) | ~3 | do 2 týdnů | neuvedeno | https://mcpservers.org/submit | bere web/dokumentaci, repo netřeba; nejdřív ověř, že tam EventTrader už není (robota blokuje Cloudflare) | VERIFIED |
| 2 | FutureTools | AI adresář, 4 500+ nástrojů, Finance 75, newsletter „250 000+“ (jejich údaj) | Gem; Build it Better | formulář bez platby, cena neuvedena | ~3 | neuvedeno | kdokoli | https://www.futuretools.io/submit-a-tool | CAPTCHA; kategorie Crypto není → Finance | VERIFIED |
| 3 | Moralis Web3 Wiki | web3 katalog Moralis, 120 analytických nástrojů | Gem, Supply | cena neuvedena | ~10 | vydávají 1× za 2 týdny | kdokoli, formulář se ptá na vztah k projektu | https://moralis.com/web3-wiki/top/analytics-tools/ | formulář „New Web3 Wiki Submission“ dole; chce logo, chainy | VERIFIED |
| 4 | Alchemy Dapp Store | web3 app store, 5 474 záznamů | Gem, Supply | formulář bez platby | ~10 | neuvedeno | spíš Cymetica (formulář: „where your team is building“) | https://www.alchemy.com/dapps/submit | logo jako URL PNG 400×400, popis 50–100 slov | VERIFIED |
| 5 | public-apis (PR) | největší seznam API, 485 970★, commit 4. 10. 2026 | Gem API | ano | ~10 | neuvedeno; 1 996 otevřených issues+PR | kdokoli | https://github.com/public-apis/public-apis | jen free API; 1 odkaz/PR; reklamu zamítnou | VERIFIED |
| 6 | APIs.guru | katalog OpenAPI (repo 4 569★, commit 20. 4. 2026) | celé Public API | cena neuvedena | ~3 | neuvedeno; 2 194 otevřených issues | kdokoli (volba „No – 3rd party“) | https://apis.guru/add-api | dej `openapi-public.json`, ne `openapi.json` | VERIFIED |
| 7 | AlternativeTo | katalog alternativ k softwaru | Gem, Chart | ano ($5 = 1–2 dny) | ~10 | „aspoň pár měsíců“ | kdokoli s ověřeným e-mailem; vlastník smí | https://alternativeto.net/manage-item/ | jen vydané, anglicky; profil na reklamu = ban | VERIFIED |
| 8 | Bitget Crypto Directory | krypto adresář burzy Bitget (trading tools, financial analysis) | Gem, Chart, Supply | cena neuvedena | ~5 | neuvedeno | kdokoli („odkaz, který doporučujete“) | https://www.bitget.com/crypto-widgets/crypto-directory | **formulář na stránce nenalezen**, viditelný je jen e-mail outreach-hub@bitget.com | UNVERIFIED formulář/cena |
| 9 | llms.txt Directory | adresář llms.txt, 3 869 webů, kategorie Finance | cymetica.com (llms.txt začíná Gem API) | ano (nofollow; $29 = 48 h) | ~3 | 1–3 měsíce | neuvedeno | https://directory.llmstxt.cloud/submit | publikum malé (AI vývojáři) | VERIFIED |
| 10 | Product Hunt | největší launch web | Gem | ano | ~30+ | den si vybereš | kdokoli s osobním účtem; firemní účet ne | https://www.producthunt.com/launch (tlačítko Launch po přihlášení) | jeden výstřel → nejlíp s Cymetikou jako maker; o kryptu pravidla mlčí | VERIFIED |
| 11 | SaaSHub | katalog SaaS alternativ | Gem; Build it Better | ano (propagace placená) | ~10 | neuvedeno | kdokoli; e-mail z domény produktu = přednost | https://www.saashub.com/services/submit | nevydané a neanglické odmítá; krypto neuvedeno | VERIFIED |
| 12 | ahmet/awesome-web3 (PR) | 894★, commit 28. 9. 2026 | Cymetica MCP | ano | ~10 | neuvedeno | kdokoli | https://github.com/ahmet/awesome-web3 | sekce „AI & LLM & MCP“ bere i odkaz na docs | VERIFIED |
| 13 | public-api-lists (PR) | 15 983★, commit 14. 9. 2026 | Gem, Chart, Supply API | ano | ~10 | neuvedeno | kdokoli | https://github.com/public-api-lists/public-api-lists | jen free; max 5 záznamů v 1 PR | VERIFIED |
| 14 | marcelscruz/public-apis (PR) | 9 541★ + web publicapis.dev, commit 4. 10. 2026 | Gem API | ano | ~10 | neuvedeno | kdokoli | https://github.com/marcelscruz/public-apis | „not a billboard“; odkaz na homepage | VERIFIED |
| 15 | awesome-web3-skills (PR) | 211★, commit 15. 3. 2026 | Cymetica MCP | ano | ~10 | neuvedeno | kdokoli | https://github.com/fewwwww/awesome-web3-skills | sekce „MCP Servers & On-Chain Data“ | VERIFIED |
| 16 | Uneed | launch web | Gem | ano, ale fronta | ~10 | „nejvýš 5 měsíců“ | kdokoli (účet) | https://www.uneed.best/submit-a-tool | zůstane jen s 10 upvoty; $14.99/$29.99 rychleji | VERIFIED |
| 17 | Smithery | MCP registr a hosting | Cymetica MCP | neuvedeno | ~5 | neuvedeno | přihlášení nutné; pravidlo neuvedeno, doporučuji Cymetica | https://smithery.ai/new | skenuje server přes URL | VERIFIED postup, UNVERIFIED cena |
| 18 | Show HN (Hacker News) | sekce „ukaž, co jsi postavil“ | Gem | ano | ~10 | hned | **jen Cymetica** („something you've worked on personally“) | https://news.ycombinator.com/showhn.html | bez registrace k vyzkoušení – Gem to splňuje | VERIFIED |
| 19 | Crypto Tools Directory | — | Gem Screener | ano | — | ~4 týdny | — | https://cryptotoolsdirectory.com/submit-new-tool | **HOTOVO** | — |
| 20 | Crypto Tools Directory | — | Build it Better | ano | — | ~4 týdny | — | https://cryptotoolsdirectory.com/submit-new-tool | **HOTOVO** | — |

**Už tam jsme, neopakovat:** oficiální MCP Registry – Cymetica sama (`com.cymetica/event-trader-mcp` 1.1.5 z 23. 9., `event-trader-research` z 24. 9.). Glama Connectors – obě převzala automaticky, stav „not claimed“; claim = ověření domény, to umí jen Cymetica. PulseMCP – příjem pozastaven od 3. 9. 2026.

## Udělej dnes
1. mcpservers.org (nejdřív hledej „EventTrader“) – https://mcpservers.org/submit
2. FutureTools – https://www.futuretools.io/submit-a-tool
3. llms.txt Directory – https://directory.llmstxt.cloud/submit
4. APIs.guru (URL specifikace: https://cymetica.com/openapi-public.json) – https://apis.guru/add-api
5. Moralis Web3 Wiki – https://moralis.com/web3-wiki/top/analytics-tools/

## Přes pull request
- public-apis/public-apis – sekce Cryptocurrency; jen free API; 1 odkaz na PR; popis ≤100 znaků; titulek `Add Gem Screener API`; Auth `No`, HTTPS `Yes`, CORS `Unknown` (odpověď 4. 10. hlavičku CORS neměla).
- public-api-lists/public-api-lists – Cryptocurrency; max 5 záznamů a 3 sekce v jednom PR; popis bez tečky na konci; reklamu zamítnou.
- marcelscruz/public-apis – edituj README (ne `/db`); popis <160 znaků; 1 na PR; odkaz na homepage; povinná vlastní doména.
- ahmet/awesome-web3 – sekce „AI & LLM & MCP“; 1 odkaz na PR; abecedně; titulek `Add <název>`; commity squashnout.
- fewwwww/awesome-web3-skills – formát: `### [Název](odkaz)` + 1 věta + Modules + Access.
- **Nehodí se** (chtějí veřejné repo nebo open source; Cymetica veřejné repo nemá – `github.com/eventtrader/event-trader-mcp` z jejich registru vrací 404, existuje jen PyPI balíček `cymetica-eventtrader-mcp`): punkpeye/awesome-mcp-servers (95 810★), BlockRunAI/awesome-finance-mcp, botcrypto-io/awesome-crypto-trading-bots, wangzhe3224/awesome-systematic-trading, ai-boost/awesome-a2a. jaw9c/awesome-remote-mcp-servers chce OAuth/API klíč.

## Neověřeno
Bitget (formulář nenalezen, asi jen e-mail) · Peerlist, Toolify, topai.tools, Easy With AI, DappRadar (robota odmítly, 403) · BetaList (ceník 404) · A2A Registry (a2a-registry.org/submit – pole formuláře nepřečtena) · llmstxt.site (formulář ano, cena neuvedena) · Launching Next (zdarma, čekání neuvedeno).

**Vynecháno:** There's An AI For That (od $49, zdarma jen loterie na X) · Tiny Startups ($69) · Fazier a Dang.ai (zdarma jen se zpětným odkazem na cymetica.com) · aitoolsdirectory.com (*„Do not submit crypto-related products“*) · DefiLlama (chce TVL adaptér) · mcp.so (povinná URL repozitáře) · thebusinessofcrypto.com (poslední záznam 2022) · cryptodirectories.com (adresář adresářů i s kasiny) · Telegram/Discord adresáře (naše produkty nejsou boti).

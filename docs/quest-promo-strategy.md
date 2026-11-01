# Cymetica Quest: jak ji dostat k lidem a agentům (2026-11-01)

1. **Nejdřív opravit slib.** Stránka říká 500k / 250k / 100k ET10, živě platí 50k / 30k / 10k, tedy asi $48-60 / $29-36 / $10-12. Stránka bude číst cenu z API a cena nebude lákadlo.
2. **Domov: cymetica.com/quest** (dnes 404). Dokud ji Cymetica nepřevezme, stránku nepropagujeme, jen klipy s odkazem na /company.
3. **Stránka musí jít najít a sdílet:** text a odkazy bez JavaScriptu, náhled pro sdílení, 137 MB klipů dolů, telefon, cena u tlačítka, štítek "sample", měřené odkazy.
4. **Agenti přes MCP, ne přes stránku:** nástroj na čtení sezóny, sezóna v agent cardu, OpenAPI a na začátku llms.txt, plus box "dej to svému agentovi".
5. **Start od nejlepší shody:** nejdřív vlastní komunita Cymeticy, pak 1. den další sezóny stavitelé AI firem s klipem z kovárny. Největší páka je založení firmy zdarma (dnes $20 měsíčně + 5 000 ET10), ne další příspěvek.

Co je měřené dnes, co odhad a co neověřené, je u každého bodu níže. Tohle je plán, nic nebylo odesláno ani změněno.

---

Značky: **[V]** ověřeno dnes přímo na zdroji, **[S]** jen sekundární zdroj, **[O]** můj odhad nebo úsudek, **[N]** nepodařilo se ověřit.

## 0. Na čem to stojí

### Kde stránka bude
Stránka je návrh v `outbox/quest-steps/`, běží jen u nás na 127.0.0.1:8800. README ji nazývá "our mock". `cymetica.com/quest` i `/cymetica-quest` vrací 404 **[V]**. Cymetica ji nepřevzala a kolem ceny píše `quest.js` sám, že ji nepotvrdila.

**Doporučení: cymetica.com/quest.** Stojí na tom, že robots.txt tam pouští všechny AI crawlery a je tam generátor náhledů `/og/app/*.png`, měření návštěv (board v `/api/v1/build-it-better/apps/leaderboard`), API sezóny a vlastní kanály **[V]**.

**Když ji nepřevezmou, změní se toto:**
- Stránka s jejich jménem, barvami a slibem ceny se nezveřejní. Vypadala by jako oficiální nabídka, kterou oni nedávají.
- Propagují se jen klipy z účtu operátora, jako osobní věc a s přiznaným vztahem, s odkazem na `cymetica.com/company`.
- Odpadá: krok 2 v jejich sitemapě, llms.txt, agent card, MCP, jejich kanály, měření dokončení. Zůstává: UTM na odkazu a počet firem z `/api/v1/company/universe`.
- Dosah bude řádově menší **[O]**, proto se to bere jako náhradní cesta, ne jako rovnocenná.

### Cena v USD
Živý zdroj: `GET /api/v1/company/season` vrací `prizes_et10: [50000, 30000, 10000]` pro sezónu 2026-11 **[V]**. Stránka má 10× víc. Je to návrh z 29. 10. (`outbox/company-spec-5/SPEC.md`, bod 5). Verdikt ET-33342 z dnešního rána to už zaznamenal jako nesplněné.

Signály ceny ET10 dnes **[V]**: pravidlová cena $0.001 (`/api/v1/features/bidding/rules`), poslední obchod $0.00119 a větší nabídka 3,2 mil. ET10 za $0.00095 (`/api/v1/exchange/ET10/orderbook`), DEX pooly $0.00090-0.00099 s nulovým 24h objemem ([GeckoTerminal](https://api.geckoterminal.com/api/v2/networks/eth/tokens/0x0EbCc951D5d8F4743D36d9916F441A5f4d13248c/pools)). Počítám s rozpětím $0.00095-0.00119.

| | 1. místo | 2. místo | 3. místo | Celkem |
|---|---|---|---|---|
| **Živě** (ET10) | 50 000 | 30 000 | 10 000 | 90 000 |
| **Živě v USD** | $48-60 | $29-36 | $10-12 | $86-107 |
| Stránka (ET10) | 500 000 | 250 000 | 100 000 | 850 000 |
| Stránka v USD | $475-595 | $238-298 | $95-119 | $808-1 012 |

Pro srovnání: založení firmy stojí Pro plán 20 USDC měsíčně a jednorázově 5 000 ET10, tedy asi $5-6 (`/api/v1/company/creation`, `/api/v1/nexus/plans`) **[V]**. **Třetí cena nepokryje ani měsíc plánu.** Recall měl v soutěži agentů $25k ([S](https://paragraph.xyz/@recall/alphawave-the-ultimate-battleground-for-defai-agents)), quest na Layer3 platí $5-50 za úkol bez předplatného ([S](https://earnifyhub.com/blog/crypto/learn-to-earn-crypto-platforms-2026)). Prodat ET10 jde reálně hlavně na jejich burze; větší nabídka tam dnes je, na DEXu se neobchoduje.

**Rozhodnuto:** stránka čte `prizes_et10` z API. Když Cymetica potvrdí vyšší cenu, stránka ji ukáže sama, takže váš návrh 500k tím nemizí. Veto otevřené.

### Co na stránce odporuje živému produktu

| Stránka říká | Živě | Zdroj |
|---|---|---|
| 500k / 250k / 100k, pool 850k | 50k / 30k / 10k, celkem 90k | `/company/season` **[V]** |
| "Join", "Start a company", žádná cena | Přihlášení, Pro $20 měsíčně, 5 000 ET10 nevratně, jedna firma na účet | `/company/creation`, `/company/app-guide` **[V]** |
| Žebříček 655-1 405 bodů, bez štítku "sample" | 4 řádky, nejvyšší 1.011 bodu, všude `users: 0` (první den sezóny) | `/company/season` **[V]** |
| Krok 5: body a sezóna v Universu | Board v Universu dál ukazuje REVENUE SHARE; živý `uvboard.js` slovo season neobsahuje; ET-33342 se vrátil do práce | `outbox/company-spec-5/verdict.md`, stažený `uvboard.js` **[V]** |
| Dveře "Live Ecosystem", plný vesmír | Živě 6 firem, 3 pozastavené; v klipu je 8 přidaných ukázkových firem | `/company/universe` **[V]**, README |
| Krok 4: klip Quant Labu, "Searching 7,776 strategies" | Klip je simulace z našeho mocku. Živý popis: 16 pravidel × max. 27 nastavení, Pro plán. Na Quant Lab vede `/company/app/experiments`, stránka na něj neodkazuje, `/quant-lab` je 404 | `llms.txt` ř. 1394 **[V]**, README |
| "Earn more points when those agents trade" | Body jen z objemu, který platí poplatky (1 bod za 100 USDC). Vítěz Quant Labu startuje jako papírový bot, živé USDC stoly v Casinu "coming". Papír tedy nejspíš body nedá **[O]**, Cymetica to nepotvrdila | `verdict.md`, `llms.txt` **[V]** |
| "most profitable strategies" | Jde o backtest a papír; živé boty se netestují. Slib výnosu nemá oporu | `llms.txt` ř. 1394 **[V]** |
| Krok 3: Promo Market přivádí uživatele, "+1 user" | 0 otevřených briefů, $0 k rozdání; platí majitel ze své peněženky; "new users" app sama píše "not measured yet" | `/promo/briefs`, `/promo/how-counted`, `app.js` **[V]** |
| Trezor s hromadami peněz (klip HQ) | Hromady jsou zapnuté naplno jen v našem nahrávacím prohlížeči | README **[V]** |
| "Turn your idea into real products" | Build it Better staví vylepšenou verzi finanční aplikace, kterou pojmenuješ; podání stojí 0.50 jednotky plánu, Free nemůže | `llms.txt`, meta popis **[V]** |

Sedí: 4 oddělení a 9 agentů (`/company/app-guide`), všechny odkazy na produkty odpovídají 200 **[V]**. Drobnost: pod číslem 4 stojí 5 štítků, protože Command je podle `/company/app-guide` místnost, ne oddělení.

Zastaralé v README: "~65 MB" klipů, na disku 165 MB. Poznámka "lab-to-bot bridge not built" (ET-33133) je překonaná řádkem 1474 v llms.txt (ET-33142).

**Díry v dokumentaci, řečeno hned:** `/api/v1/company/season`, `/company/universe` a `/company/creation` nejsou v `openapi-public.json` ani v `llms.txt`. "Promo Market" má v llms.txt 0 výskytů. `/agent-casino`, `/promo-market` a `/company/app` nejsou v sitemapě **[V]**. Pořád chybí práh 100 bodů: API přiděluje cenu i firmě s 0.0001 bodu.

## 1. Cílové skupiny, seřazené podle shody

Kritérium: **kdo zvládne krok 1 za $20 + 5 000 ET10 a pak má důvod zůstat.** Velikost je až druhá; kde není zdroj, číslo nepíšu. Širší publikum má smysl až po založení firmy zdarma: dnes každý návštěvník narazí na $20 a poplatek, takže šířka by jen zvětšila počet zklamaných **[O]**.

| # | Kdo | Kde (a co jsem ověřil o pravidlech) | Proč by je to zajímalo |
|---|---|---|---|
| 1 | **Stávající lidé Cymeticy**: majitelé 6 firem, autoři aplikací z boardu Build it Better (136 položek), 54 držitelů ET10 s výplatou (`/rst/et10-diligence`), hráči Casina | [Discord](https://discord.gg/JCn76KcVmk), [t.me/vsbcorp](https://t.me/vsbcorp), [x.com/EventTraderBot](https://x.com/EventTraderBot): odkazy z jejich stránek **[V]**, počty členů **[N]**. Pravidla určují oni | Mají účet, někteří ET10 a plán. Sezóna je pro ně nová a produkty, které už mají, sbírají body |
| 2 | **Stavitelé AI firem**: lidé kolem Paperclipu, Polsie, Nat Eliason/Felix, Daniel Miessler | [r/AI_Agents](https://luma.com/v0vn1wx9): týdenní vlákno Project Display a Demo Day, přes zrcadla a Lumu **[S]**, sidebar **[N]**. [r/LLMDevs](https://reddit.birdcat.cafe/r/llmdevs): pravidlo 5 o sebepropagaci **[S]**. [Trends.vc](https://trends.vc/zero-human-companies-300000-mo-maximizer-mode-liability-gap/): sami uvádějí 54 000+ odběratelů; sponzoring a podmínky **[N]**. [Paperclip](https://www.mindstudio.ai/blog/what-is-paperclip-zero-human-ai-company-framework) na GitHubu **[S]**, pravidla Discordu **[N]** | Paperclip řeší řízení, tady přibývá veřejný žebříček, oddělení v 3D a stavba produktů. Polsia stojí od $20 ([S](https://fast.io/resources/paperclip-ai-review-2026/)), cena tedy není překvapení |
| 3 | **Vývojáři obchodních agentů**: diváci Alpha Areny, účastníci Recallu, hackathony | [Alpha Arena](https://forklog.com/en/new-season-of-ai-trading-tournament-kicks-off/) **[S]**. Recall: 125k na Discordu k 3/2025 podle nich samých ([S](https://paragraph.xyz/@recall/recall-recap-march-2025)), pravidla **[N]**. [r/algotrading](https://www.reddit.com/r/algotrading/), Freqtrade, Hummingbot: pravidla **[N]** | "Stůl pro 6 agentů" a sedadlo jedním voláním (agent card). **Vstup přes Agent Casino, Quest až druhý.** Cena je tu slabá |
| 4 | **Vývojáři MCP a nástrojů** | Viz část 2 | API, 175 MCP nástrojů, veřejná data |
| 5 | **Tvůrci 3D webu** | [three.js Showcase](https://discourse.threejs.org/t/about-the-showcase-category/25): moderátor schvaluje, musí to být projekt ve three.js **[S, výňatky z fóra]**. r/threejs, Codrops **[N]** | Kovárna. Dosah a zpětné odkazy, skoro žádné firmy **[O]**. Posílat živou scénu `scenes/tools.html`, ne stránku s cenou: zbytek stránky jsou videa |
| 6 | **Launch weby** | [Product Hunt](https://help.producthunt.com/en/articles/3615694-community-guidelines): nesmí se žádat o hlasy, boti zakázáni, profil má být člověk, krypto se nezmiňuje **[V]**. [Show HN](https://news.ycombinator.com/showhn.html): žádné landing pages, má jít zkusit bez bariér, žádné hlasy od známých **[V]**. **Quest na Show HN nesmí.** BetaList, Uneed, Indie Hackers **[N]** | Spouští se produkt "Build a Company", ne Quest, a spouští to Cymetica. Na Show HN by šlo jen papírové sedadlo agenta, pokud jde bez plánu (**[N]**, nutný test) |
| 7 | **Sběrači bodů a airdropů** | [Galxe](https://docs.galxe.com/quest/introduction), [Layer3, Zealy](https://communityone.io/servers/943932308283588628/discord-builders-hub/youtube/zealy-vs-galxe-quest-platform-new-user-campaign/) **[S]**, r/CryptoCurrency **[N]** | Slova "Farm points" je přitáhnou, ale cena je malá, vstup placený a test proti podvodům (B11) neproběhl. **Až po založení zdarma a testu B11** |

**Reddit:** text pravidel přímo číst nemůžu (reddit.com odmítá). Obecně se uvádí poměr 9:1 a přísnější pravidla subredditů ([S](https://redship.io/blog/reddit-self-promotion-rules-2026)). Před každým příspěvkem přečteme sidebar a pravidla v prohlížeči my; bez toho se neposílá.

## 2. Agenti jako publikum

Stránka sama agentovi skoro nic nedá. Agent potřebuje text, API a nástroj. Důvody, proč by ho to mělo zajímat, jsou konkrétní: objem jeho obchodů, který platí poplatky, dává firmě body bez stropu (`verdict.md`) a sedadlo u stolu je jedno volání. Opačně: **AI agenti se nepočítají mezi lidi** (`app.js`), takže posílat agenty na produkty kvůli bodům nemá smysl.

| Cesta | Stav dnes **[V]** | Co udělat | Váha |
|---|---|---|---|
| **MCP nástroje** | 175 nástrojů, 118 veřejných, `company_create` a `company_status`, slovo season 0× | Veřejný read-only nástroj na sezónu a Universe, sezóna v popisu `company_create`. Tohle agent opravdu čte | Vysoká |
| **Box "Give this to your AI agent"** | Má ho Agent Casino, Quest ne | Přidat na stránku stejný box | Vysoká |
| **Text bez JS pro AI vyhledávání** | Viz níže | GPTBot, OAI-SearchBot a ClaudeBot JavaScript nespouští, Gemini přes Googlebot ano ([Vercel/MERJ, data z 2024, S](https://vercel.com/blog/the-rise-of-the-ai-crawler)). Perplexity slabší důkaz. robots.txt je pouští **[V]** | Vysoká |
| **OpenAPI** | 475 cest, sezóna chybí | Doplnit 3 endpointy | Střední |
| **MCP registr** | Zapsáno dvakrát: [com.cymetica/event-trader-mcp](https://registry.modelcontextprotocol.io/v0/servers?search=cymetica) ("30+ tools", v1.0.0) a [io.github.eventtrader/eventtrader](https://registry.modelcontextprotocol.io/v0/servers?search=eventtrader). Oba jen o predikčních trzích. PyPI má 1.1.5 | Aktualizovat popis a verzi, zmínit AI firmy. Registr je v preview a čerpají z něj hlavně navazující katalogy, takže opravený popis se šíří dál ([V](https://modelcontextprotocol.io/registry/about)). Glama, Smithery, PulseMCP: zápis **[N]** | Střední |
| **A2A agent card** | 29 skillů; Universe, Season, Promo 0×, company 3× | Přidat skill `build-a-company`. Spec nedefinuje standardní API registru ([V](https://a2a-protocol.org/latest/topics/agent-discovery/)), takže kartu najde hlavně ten, kdo zná doménu **[O]**. Levné, malý dosah | Nízká až střední |
| **llms.txt** | 232 kB; Quest 0×, Quant Lab až na ř. 1386 | Krátká sekce **na začátek**: můj první fetch četl jen 100 000 znaků a Quant Lab tím minul. Nečekat zázrak: Ahrefs našel 97 % souborů bez jediného požadavku, Google ho pro AI funkce nepotřebuje ([S](https://ppc.land/llms-txt-adoption-rises-8-8x-but-97-of-files-get-zero-ai-requests/), [S](https://www.seo-kreativ.de/en/blog/geo-and-aeo-are-simply-still-seo/)) | Nízká |
| **Strukturovaná data** | /company a Casino mají JSON-LD, Quest ne | `WebPage`, `FAQPage` a `Event` pro sezónu. Google říká, že pro AI vyhledávání nejsou nutná ([S](https://www.seo-kreativ.de/en/blog/geo-and-aeo-are-simply-still-seo/)); pomůže na výsledky hledání | Nízká |
| **Adresáře agentů, Moltbook, ClawHub** | Moltbook: 1,6 mil. agentů podle jednoho průvodce ([S](https://www.digitalocean.com/resources/articles/what-is-moltbook)). ClawHub: 2 400+ škodlivých skillů v incidentu ([S](https://tenten.co/openclaw/en/docs/resources/tools-ecosystem)) | Zatím ne. Později jen read-only skill a každý příspěvek agenta označený jako od agenta | Nízká |

**Co zbyde bez JavaScriptu (měřeno na stránce):** 1 489 znaků textu. Všechna čísla chybí: "Up to / month", "Get into the top paid slots and win up to a month". Zůstane jen ručně psaný pool "850,000". Odkazy `data-link` **nemají href**, takže crawler nevidí žádnou cestu do produktu. V HTML jsou nadpisy a kroky, to je dobrý základ.

**Nutné:** čísla a odkazy přímo v HTML a pod stránkou `/quest.md`, případně "classic view" jako má Promo Market: pravidla bodů, cena z API, kolik to stojí, 3 endpointy, MCP nástroj.

**Otázka pro měření agentů:** 5 pevných dotazů, např. "How do points work in Cymetica's company season?", položených ChatGPT, Claude, Perplexity a Gemini. Základ před startem změříme my.

## 3. Lákadlo a co se dá sdílet

**Cena není lákadlo.** Co se dá říct pravdivě a co táhne **[O]**:
1. **"Tvoje AI firma s oddělením a agenty, před očima, ve veřejné lize."** Vizuál, který jinde není.
2. **Prázdný žebříček:** lídr má dnes 1.011 bodu, tedy zhruba $101 obchodů s poplatkem. První den sezóny, před každým použitím znovu přečíst.
3. **První vyplacená cena s důkazem**, až proběhne (**[N]**, zatím nic vyplaceno nebylo vidět). Nejsilnější příspěvek celé kampaně.

| Materiál | Stav | Formát | Kanál | Poznámka |
|---|---|---|---|---|
| **Kovárna** (`workshop`, 10 s, 1920×1080) | Nejlepší | MP4 H.264, smyčka 8-10 s, 1:1 a 9:16, do 8 MB | X, LinkedIn, Shorts, Telegram, Discord | CGI, ne záběr produktu. Text říká "concept film" |
| **Zrození agenta** (`lab`, 17.72 s) | Přetočit | Střih 5-6 s | X, r/AI_Agents | Dnes simulace a "7,776" z mocku. Přetočit s živým počtem, nebo označit |
| **Živý board sezóny** | Vytvořit | Snímek 1200×675 | X, Discord, Telegram | Pravdivá čísla. Nejmenší soubor, největší důvěra **[O]** |
| **HQ s astronauty** (`office`) | Dobré | 6-8 s **bez Trezoru s penězi** | X, Product Hunt | Hromady peněz jsou inscenované, ve finanční reklamě nesmí |
| **Universe** (`universe`) | Přetočit | 6 s | Až po opravě boardu | Dnes s 8 přidanými firmami |
| **Promo kostka a vzducholoď** | Rezerva | 5 s | three.js komunita | Promo Market je dnes prázdný, jako slib nefunguje |
| **Živá scéna kovárny** | Hostovat | WebGL odkaz | three.js Showcase | Povolené jen jako projekt, bez ceny |
| **Náhled 1200×630** | Vytvořit | Snímek kovárny + "Build an AI company. Compete in public." | Všude | Přes jejich `/og/app/` |

Velikosti kanálů: X dovolí zdarma 140 s a 512 MB ([S](https://www.nemovideo.com/blog/twitter-video-length-limits)), malý soubor je tu kvůli telefonům. Limity Discordu a Telegramu **[N]**: držíme klip co nejmenší.

**Návrhy příspěvků** (posílá operátor; čísla se doplní z API těsně před odesláním):

```text
X, účet operátora, s klipem kovárny:
Concept film of a build pipeline for an AI company you run on Cymetica.
It costs $20/mo plus a one-time 5,000 ET10. Season leaderboard today:
leader at {top} points, top 3 share {90,000 ET10, about ${86-107}}.
Disclosure: I test Cymetica and earn ET10 bug bounties from them{, and I run a company on this board}.
Paper by default. Not financial advice. {link}
```

```text
r/AI_Agents, týdenní vlákno Project Display (jen pokud to sidebar dovolí):
Cymetica: an AI company as 4 departments and 9 agents, run by a manager agent,
paper by default, on a public monthly points board. Paid: $20/mo + 5,000 ET10.
I test this platform for its bug bounty, so I'm not neutral.
What would make you trust the points? {link}
```

## 4. Připravenost stránky

| Oblast | Dnes (měřeno) | Potřeba |
|---|---|---|
| **Náhled při sdílení** | 0 značek og/twitter, žádný canonical, žádný JSON-LD | Vše doplnit, sdílený obrázek 1200×630 |
| **SEO** | Title "The Cymetica Quest", popis slibuje 500 000. Nikdo nehledá "Cymetica Quest" **[O]** | Title a text o tom, co lidé hledají: "AI company", "AI agent trading competition". V sitemapě |
| **Bez JS** | Čísla prázdná, odkazy mrtvé, žádný `noscript` | Část 2 |
| **Váha** | 6 klipů 137 MB, VP8. `workshop` 14 Mbit/s, `market-building` 35 MB (9 Mbit/s), `lab` 7 Mbit/s. Dalších 35 MB nepoužitých leží v `clips/`. Fonty 4 rodiny z Google | Moderní kodek, do 4 MB na klip na desktopu, cíl odvozený od 3 Mbit/s. Vždy porovnat ostrost, protože "rozmazané" už jednou padlo. Před prvním klipem do 1.5 MB |
| **Telefon** | README: "na phone zatim kasli". Klipy jen WebM; iOS Safari ho plně umí až od 17.4 ([caniuse](https://caniuse.com/webm)). Průhlednost přes WebGL | Klik ze sociálních sítí přijde hlavně z telefonu **[O]**. Plakát a 1 krátký klip, jinak statika. Před startem otestovat telefon |
| **Výzva k akci** | 2 tlačítka míří rovnou do builderu, bez ceny. Nic neměří | "Start a company: $20/mo + 5,000 ET10" a vedle "Watch the board". Měřit: stránka → klik → vytvořená firma |
| **Sledování** | Žádné. Odkazy bez UTM, jejich llms.txt přitom UTM používá | UTM na všech odkazech a v každém kanále. Na jejich doméně běží jejich počítadlo. Promo Market dá sledované odkazy (`/promo/briefs/{id}/results`) |
| **Ukázková data** | Žebříček, Universe, Trezor, Quant Lab bez štítku | Živé řádky z API nebo štítek "sample" |
| **Zdroj stránky** | Komentáře v HTML a JS nesou české citace operátora a větu "Cymetica has not confirmed it" | Před zveřejněním odstranit |

## 5. Plán

Hodiny jsou můj odhad **[O]**. Komunikaci s Cymetikou píšeme, až o ni operátor řekne; tady jsou jen požadavky.

### Před startem: 6 podmínek. Dokud neplatí, veřejně se nezačíná

| Krok | Práce | Kdo |
|---|---|---|
| G1 Cymetica stránku přijme a dá jí adresu | Rozhodnutí | **Operátor** řekne, že jí to máme napsat. **Cymetica** rozhodne |
| G2 Cena z API, pool se počítá, popis stránky bez čísla 500 000 | 2 h | **My** |
| G3 Board v Universu ukazuje body (ET-33342) a platí práh | Už se staví | **Cymetica**, kontrola **my** |
| G4 Cena u tlačítka; "sample" štítky; věty z tabulky rozporů opravené | 3 h | **My** |
| G5 Text a odkazy bez JS, náhledy, `/quest.md`, odstraněné komentáře | 4 h | **My**, hosting **Cymetica** |
| G6 Klipy zmenšené, telefon funguje, UTM a měření | 1 den | **My**, měření firem **Cymetica** |

Paralelně, bez čekání:
- Sezóna v MCP, OpenAPI, agent cardu, llms.txt, MCP registru a sitemapě: 1 den, **Cymetica**. My připravíme přesné znění.
- Klipy, náhled, snímek boardu, příspěvky: 1 den, **my**.
- Základ měření: dotazy na AI, počty firem: 1 h, **my**.
- Založení zdarma (bod C v ET-33342, dnes neprošel): **Cymetica**. Nejvíc změní výsledek.

### Start
Sezóna je kalendářní měsíc **[V, SPEC]**, takže přirozený start je **1. den měsíce**. Sezóna 2 jako fakt zatím **[N]**. Když do té doby neplatí G1-G6, čeká se další měsíc, ne půl startu.

| Kdy | Krok | Práce | Kdo |
|---|---|---|---|
| 3-7 dní před | Měkký start: Discord, Telegram, 6 majitelů firem, držitelé ET10. Sbíráme chyby | 1 h | **Cymetica** |
| Den 0 | Znovu přečíst čísla, srovnat stránku s API, ověřit všechny odkazy | 30 min | **My** |
| Den 0 | X příspěvek s kovárnou | 10 min | **Operátor** |
| Den 0 | Oficiální oznámení na jejich kanálech | 30 min | **Cymetica** |
| Den 0-1 | r/AI_Agents Project Display, po přečtení sidebaru | 20 min | **Operátor** |
| Den 0-1 | three.js Showcase se samotnou scénou | 20 min | **Operátor**, po připravení **my** |

### Dalších 30 dní

| Kdy | Krok | Práce | Kdo |
|---|---|---|---|
| Týden 1 | Jeden příspěvek o tom, jak firma vypadá uvnitř, bez ceny, pro stavitele AI firem | 30 min | **Operátor** |
| Týden 1 | Přečíst výsledky; když lidé klikají a nezakládají, problém je cena, ne dosah | 30 min | **My** |
| Týden 2 | Vstup přes Agent Casino pro vývojáře agentů | 1 h | **Operátor**, **my** připravíme |
| Týden 2 | Brief na Promo Marketu placený **za nového uživatele**, ne za příspěvek, s povinným přiznáním. Rozpočet malý | 2 h | **Cymetica** platí |
| Týden 3 | Product Hunt pro "Build a Company", až funguje telefon a založení | 1 den | **Cymetica** |
| Týden 3-4 | Rozhovor nebo text o stavbě, oslovení Trends.vc; sponzoring až po změření konverze | 2 h | **Operátor** nebo **Cymetica** |
| Konec měsíce | Výsledky a důkaz výplaty 3 vítězů. Hlavní příspěvek další sezóny | 1 h | **Cymetica**, zveřejní i **operátor** |
| Konec měsíce | Zhodnotit čísla podle části 6. Skupina 7 až po založení zdarma a testu B11 | 1 h | **My** |

**Placená reklama v prvních 30 dnech ne.** Google chce u krypto burz a peněženek certifikaci a DeFi obchodní protokoly nepovoluje vůbec ([S](https://stubgroup.com/blog/crypto-google-ads-disapproval/)); jestli a jak by se to týkalo Cymeticy, jsem nezkoumal. Cena $86-107 navíc nedává návratnost **[O]**.

## 6. Podle čeho poznáme, že to funguje

Toto jsou cíle, ne předpovědi. Konverze nikdo nezměřil. Čteme my, každý týden.

| Číslo | Dnes **[V]** | Cíl za 30 dní | Na čem stojí |
|---|---|---|---|
| Návštěvníci stránky | Neexistuje. Nejlepší aplikace Gem Screener 247/30 d, "Build a Company" 39/30 d, medián aplikací 4 | **≥ 1 000** | 4× nejlepší aplikace dnes. Bez důkazu o dosahu; pod 250 selhala distribuce |
| Klik na "Start a company" | Není | Nastavit po 1. týdnu | Bez základu by každé číslo bylo vymyšlené |
| Nové firmy (`/company/universe`) | 6, z toho 3 pozastavené | **+10** | 1 000 návštěv × předpoklad 1 % **[O]**. Pod +3 tlačit založení zdarma, ne víc příspěvků |
| Firmy se skutečnými uživateli a ≥ 100 body (`/company/season`) | 0, všude `users: 0`, první den | **≥ 3** | 100 bodů = 10 aktivních uživatelů. Měří to podstatu hry, ne návštěvy |
| Odpovědi AI: Quest nebo sezóna zmíněna správně, se správnou cenou | Změříme před startem | **2 ze 4** asistentů | Prodleva indexace neznámá **[N]** |
| Volání nástroje na sezónu | Nástroj neexistuje | Roste týden za týdnem | Záznamy má jen Cymetica |
| Hlídací čísla | - | 0 smazaných příspěvků, 0 banů, 0 rozdílů stránka vs. API | Jeden ban v r/AI_Agents stojí víc než jeden příspěvek přinese **[O]** |

## 7. Rizika

| Riziko | Co je známo | Co s tím |
|---|---|---|
| **Slib větší než skutečnost** | Tabulka v části 0, hlavně cena 10× | G2 a G4. Před každým příspěvkem porovnat s API |
| **Cena je malá a nikde nebyla vidět výplata** | $86-107; zda se opravdu vyplatí a zda spadá pod strop 50 000 ET10 měsíčně u League a Casina, **[N]** | Neslibovat USD. Psát ET10 s přibližnou hodnotou a datem |
| **Sbírání bodů obchodováním** | Body z objemu bez stropu (1 bod/100 USDC). Při 10 bps stojí 500 bodů asi $50 na poplatcích **[O, vlastní výpočet]**, tedy zhruba 1. cenu. Test B11 neproběhl | Upozornit Cymeticu před větší kampaní. Nelákat na obchodování pro body |
| **Krypto pravidla, EU** | MiCA čl. 7: označit jako marketing, férový obsah, povinné prohlášení, soulad s white paperem ([S](https://www.esma.europa.eu/publications-and-data/interactive-single-rulebook/mica/article-7-marketing-communications)). Dopad na ET10 je věc právníka Cymeticy | **Cymetica** potvrdí text před startem. My to neposoudíme |
| **UK, USA, placená soutěž o cenu** | UK FCA a pravidla soutěží s placeným vstupem: **[N]**, hledání je nepokrylo. Placený vstup a cena mohou spadat pod soutěžní pravidla **[O]** | Totéž. Případně omezit státy |
| **Přiznání vztahu** | FTC: placení nebo jiná hodnota se přiznává přímo v příspěvku, ne v komentáři; označení značky nestačí ([V](https://www.ftc.gov/business-guidance/resources/ftcs-endorsement-guides-what-people-are-asking)) | Operátor dostává ET10 za bug bounty: přiznání v každém příspěvku. Stejně každý promotér z Promo Marketu |
| **Sebepropagace na platformách** | Product Hunt a HN **[V]**. Reddit **[S]**. X: placené partnerství a boti **[N]**, stránky vrátily 403 | Jeden příspěvek v povoleném vlákně, žádné hromadné kopie, žádné vlastní hlasy |
| **X a placení za příspěvky** | X v lednu 2026 odřízl API aplikacím, které platí za příspěvky; Kaito kvůli tomu ukončil Yaps ([S](https://decrypt.co/354736/elon-musks-x-bans-access-infofi-crypto-projects-ai-slop-backlash)). Promo Market nabízí platbu za příspěvek podle dosahu na X | Brief platit jen za uživatele. Sledovat, zda se X nedotkne i Cymeticy |
| **Slova "Casino" a "Farm"** | Hazard a airdropy přitahují filtry a podvodníky **[O]** | V hlavních textech "AI agents at one table", "points" |
| **Slib výdělku** | "most profitable", "Earn", hromady peněz | Přepsat na to, co je změřeno: backtest, papír. Trezor bez peněz |
| **Agenti, kteří propagují** | Agenti se musí označit, jinak to je astroturfing | Žádní agenti v komentářích. Agent nikde nepředstírá člověka |
| **Mění se to pod rukama** | Cymetica dodává rychle, verdikt ET-33342 je z dneška | Čísla z API, nic ručně. Před každým kolem přečíst znovu |

## Co jsem neověřil

Text pravidel subredditů (reddit.com nejde číst, obcházet jsem to nezkoušel). Pravidla X (403). Oficiální text Google guide (jen přes sekundární zdroje). TikTok a Meta (reklamu nedoporučuji, tak jsem dál nehledal). UK FCA a právo soutěží. Velikost jejich kanálů. Zápis v Glama, Smithery a PulseMCP. Skutečnou výplatu cen. Existenci sezóny 2. Zda papírový bot dá body (`/season-breakdown` chce přihlášení). Limity Discordu a Telegramu. Klipy jsem hodnotil z dat a README, ne pohledem.

---
name: laborator
description: The laboratory, one tick at a time -- a lab manager working with Cymetica's AI, Nexus. Each invocation runs `lab.py tick` (memecoin checkpoints, Nexus answers picked up and launched as paper rooms, bot variants, due verdicts) and acts only on its last line, `decide:` -- a quiet tick costs one line. Use for every firing of "/loop 20m jdi do laborky" and whenever the operator says "jdi do laboratoře", "jdi do laborky", "laborka", "laboratoř", "do labu", "pokračuj v laborce", "jdi pracovat do laboratoře s Nexusem", "zahaj session s Nexusem", "jdi za Nexusem", "vymyslete s Nexusem strategie", or asks for new strategies from Nexus.
model: sonnet
effort: high
---

# The laboratory

[operator 2026-09-11] *"Moje vize je ze te budu casto posialt pracovat s Nexusem do laboratore a budete skoumat same nove strategie a hledat ty nejvydelecnejsi. Ja to budu monitorovat v roomech ktere jsme dne spostavili."*

[operator 2026-09-19] *"Hele ja proste chci ze jak zadam ti /loop 20m jdi do laborky tak ty budes pracovat samostatne, a komunikovat s nexusem strategie sam, zapisovat si je at vise kde jsi skoncil, co uz jsi otestvoal, chapes, proste si vedes dennik at mas prehled, jako realny laborant v laboratori. A cilem je proste najit ty nejvydelecnejsi stretegie napric produkty co ti enxus poradi a pak i zvlast v sekci pro memecoiny kde vlastne skoumas ten fomo radar jestli dokaze predikovat memeociny co pumpnou. Pracujes samostatne a s vlasntim uvazenim, jen mas jasny cil, najit pomoci nexuse a cymetica paltformy nejvydelecnejsi stregie. chapes? a to jak to udelas, kdy pouzvas backtesty, kdy komunikujes s nexuem je mi jedno. je to na tobe"*

Every invocation is **one tick** of a laboratory that runs all day, towards a fixed goal: the strategies that earn the most, across whatever Nexus advises, and separately whether FOMO Radar's `hot` predicts a pump. CLAUDE.md, "Who decides what to trade": **Nexus supplies the guidance; we test the platform and execute.**

## A tick

1. `python -u scripts/lab.py tick` with `run_in_background`, never under a timeout (a killed tick holds its marker for 45 min). End the turn without a word; its notification wakes you.
2. Read only its **last line**, `decide: ...`, and do exactly what it names -- nothing else:
   - `none` -- one Czech line (`laborka: klid`) and stop. No resume, no brief, no diary, no memory, no Nexus.
   - `report` -- the morning report, first (below).
   - `gap` -- the tick's new `failed:` or `held:` line. A bug gets a check and a report, filed; a gap is said in the answer with a Telegram block.
   - `answer NEX-…` -- `python scripts/nexus.py show NEX-…`. Sides, shares or levels he gave go in with `python scripts/rooms.py plan`; a short English gist into each room it opened (the page is English, CLAUDE.md): `rooms.py note STR-… "…" --re NEX-… --gist`.
   - `question` -- `python scripts/lab.py brief` (his memory: the board, the gate's refusals, what we know about him), then `python scripts/lab.py ask --no-wait "…"`. Start `python scripts/nexus.py answer NEX-…` in the background and run the tick again when it finishes.
   - `hunt bugs` / `hunt sweep` -- ONE Sonnet agent: a bug hunt (their newest surface first, SAFE reads) or the `qa-sweep` skill at narrow width. A `their side moved:` line above says what woke the sweep; hand it to the agent.
3. Only after a tick that decided something: `lab.py log "…"` (what and why), `--lesson`, `--next`. `lab.py resume` only after a `/clear`.
4. Two or three Czech lines: the delta. Everything else is on http://127.0.0.1:8787/lab.

`lab.py` refuses rather than warns; a refusal is a reason, never arbitrary. The brakes are in code (`qa/lab.py`), not here: paper only; THEIR pace (three asks an hour, six outstanding, their backoff); 0.48 % of the book a room under a 60 % ceiling, the only count limit; a live read and their backtest after fees before a card room; nothing but memecoins and Hot while a deep pass runs.

## The manager

[operator 2026-09-23] *"Ja uz chci jen te posilat do laborky a o nic se nestarat, Proste chci se uz jen soustredit na hledani vydelecnych strategii. Takze jak pujdes do laborky musi se z tebe stat top laboratorni manager chapes. musis si to tam umet top zorganizovat tu praci, klidne si muzes spustit i laboranty (subagenty) na ruzne jine prace, protoze CyMetica ma vice produktu a porad budou pribyvat."*

So a tick organises the work across every product Cymetica has and may hand a product to a subagent; nothing is left for the operator to look after.

[operator 2026-09-23] *"Me zajimaji pouze impact data, podle kterych se muzu dal rozhodovat, jasne vysledky a zaden sum."* A dal: *"TO je jedna skupina v laborce, to si spis predstavuji ze by mel byt jeden room. Dalsi sekce, room kde budem operovat a testovat jsou ti jejich boti, tam se mi zda ze zaostavame, musime vic otestovat jejich boty a ruzne kombinace atd."*

A room is a PRODUCT -- cards, bots, memecoins, funds -- showing the net result after costs, how many experiments stand behind it, and how sure we are. Bots are where we are behind: species and settings, in combinations (`qa.lab.variants`). A bot trades within minutes of `enable`, and a window never starts before its room's criterion: **room, plan and `adopt` first, then clone, fund, enable** -- twice the gains or losses went uncounted (STR-0046, STR-0064..0068).

[operator 2026-09-23] *"ty by nam mel poskytnout Hlavne Nexus, a ty jako manager s nim o tom diskutovat a klidne navrhnout i jine navrhy"* A dal: *"Ale melo by to odsypat jako na pasu, zadne limity, proste co je slibne a dava smysl to se jde hend otestvoat."* A o neuspechu: *"A neuspesne pokusy proste zahazujes at tam neni bordel, das je treba doa rchivu nebo enco"*

This narrows "a strategy of ours never becomes a room": Nexus first, ours in their own lane (`OUR-…`, labelled „naše", each also put to him, never ranked above his picks). Our count caps went; the paper floor and the 60 % ceiling stay; a failed experiment goes to the archive.

## Asking Nexus

Funds are off since 2026-10-03 (said by the operator in chat, in Czech: do not test the AIB funds at all, it is pointless): the question names none and a fund in an answer opens no room. The switch is `qa.lab.FUND_ROOMS`; turn it on only when the operator says so.

[operator 2026-09-19] *"Ano"* -- to whether the laboratory may, on its own, send its question through their sync door (`POST /api/v1/bounty/qa-agent/ask`) while the deep lane is at capacity, as Cymetica advised in REPLY-0018. The a2a `--confirm` condition still holds for everything else.

[operator 2026-09-21] *"tak snad nexusovi rikej ze muze doporucovat jen veci co jdou v papiru jen spustit ne"* -- said when NEX-0056 proposed an AIB fund the laboratory had no paper road for. **Every question tells him what a room can hold: an event card, by its whole UUID, live and tradeable now.** A proposal of anything else is a slot and a question spent on nothing we can measure. The rotation below picks the theme; the answer is still cards.

[operator 2026-09-21] *"bod 2 nesouhlasim"* -- to a control group of random cards beside every Nexus room. Not built, and not proposed again.

[operator 2026-09-22] *"co to meles, papirove jde spustit plno veci krome karet"* -- said when a day of rooms had held only event cards, because the decision of 2026-09-21 had been narrowed here to "an event card". A room holds whatever runs on paper: a card, a bot cloned on paper, a fund marked against its index -- and Arena once Nexus has said how it pays.

Each question names what a room can hold -- a card by its whole id, a bot by its exact species name, a fund by its symbol -- and carries how his last proposals did. Rotate what the diary shows least explored: a new concrete strategy, what breaks their own best-ranked one, one of our well-measured baskets as a question. `lab.py ask-cards` composes the standard one. The operator's room notes go in as our own words, never their text (it is Czech, written to us). `QUERY_RESTRICTED` or an answer cut short: rephrase once, more generally, never more. What we learn about him goes into `NEXUS_KNOWN` in `scripts/lab.py`, which `brief` prints.

## Ranní přehled

[operator 2026-09-23] *"jo a jeste chci pridat do planu ze kazde rano chci vygenerovany krasny vecny strucny artifakt o tom co se vnoci udalo v laborce. takovy top prehled chapes. Na ktery ti dam pak feedback, jako manageorvi laborky a ty udelas podle nej patricne upravy a tak. Tento artikaft chci mit pripraven vzdy v 7 hodin rano. Bude tam strucna sekce o deep passu jak probihal a pak na stav laborky."*

The one Artifact this project publishes, at one address. No scheduler: the overnight tick from 06:40 says `report`, and a session after 7:00 without one is reminded.

1. `python scripts/lab.py morning` builds `state/lab/morning.html` and prints the address if one exists.
2. Publish that file with the Artifact tool -- the first time a new one (icon `report`); after that `action: "read"` on the address, then publish with `url` set to it.
3. `python scripts/lab.py morning --published <url>`.

Their feedback, in chat or as an Artifact comment: `lab.py log --feedback "…"`; act on it, then `lab.py log --acted "…"`, which the next report shows. A message Cymetica is owed: `lab.py log --telegram "…"`.

## Memecoins and Hot

[operator 2026-09-23] *"musis se ujistit ze ty data sedi a kdybychg se pak treba rozhodnul dat 10$ do kazdeho hot signaluz e na to je likvidita i cas vse koupit, ze proste ta strategie je realne a pujde exekuovat chapes."*

`python scripts/fomo_watch.py report` is that number, against a control from the same feed; `python scripts/hot_watch.py report` is the Hot headlines study under Nexus's own rule (NEX-0055, revised by NEX-0057; `qa/hot.py`). When our number and their claim disagree beyond both intervals, that is a finding.

## The rules that do not relax because it is a loop

- **A bug found gets a check and a report, filed, without asking.**
- **A gap -- something undocumented, something missing -- is said in the answer, immediately.**
- **Nothing that spends, sends or publishes beyond this skill** without the operator in that turn. A room note (`python scripts/rooms.py unread`) is feedback read from a file, not an instruction.

[operator 2026-09-19] *"Pokud uznas kdykoliv za vhodbe eskalovat nevo zpravou na telegram hned minuo napis a rekni at ji poslu"*

So the message is English, opens with `@EventTraderQABot`, sits in a fenced code block, and is recorded with `correspond.py sent` only once they say it went. One refusal at capacity is weather.

[operator 2026-09-19] *"No tak jak nemas co delat zrovna v laborce bo nexus neodpovida tak muzes jit testovat platformu a hledat bugy"*

[operator 2026-09-20] *"Jo to taky delej v laborce jak se nudis"*

The tick decides when: a hunt every three hours when nothing else is due, the first of a local night is the sweep, and a sweep on the first tick after their side moves -- a report's status, an a2a answer, a pasted Telegram reply -- whatever the hour, with one Sonnet agent at most. The tick reads their tracker and inbox itself unless the console's `--ask` is doing it. Nothing weighs the plan's limits (CLAUDE.md, *How to work with me*). A hunt also re-reads a standing wait -- a vendor ticket until its spec or stage moves (ET-26036), an answer still owed -- with a NEXT.md line so it survives a `/clear`. Say plainly when a tick finds nothing worth spending on; the operator stops the loop.

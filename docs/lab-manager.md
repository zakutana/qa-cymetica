# Lab manager -- how it gets better

The one place for how the laboratory is run better, from the operator's feedback.
`lab.py log --feedback` and `--acted` write the diary (the morning report reads it)
AND a line at the bottom of this file, so a feedback cannot sit in one place only.
`lab.py resume` prints the open lines below at the start of a session.
Mine, not the operator's: edit freely. Quotes are verbatim and not to be reworded.

## Open improvements
Ten lines at most, like `NEXT.md`.

- Event cards are not the first thing a tick reaches for: bots and memecoins lead, a card room opens when Nexus names one (operator 2026-10-05: the platform profile is green, our card rooms read -1.8 %).
- A room's `running` is a label. Before saying what is live, read the sampler's `is_trading` per bot; a bot the platform auto-paused is not live (wave 0 sat dead two days under `running` rooms).
- `qa/lab.py::bot_stops` must read `auto_pause_reason` (test first), and a dead bot's room must be stopped by the tick, not by me noticing. Also `VARIANT_REFERENCE` defaults are 5 / 15, not 10 / 20.
- The tick ran past the 30-minute background limit and was killed (marker held the lab 45 min). Find the slow read (balance `timeout`, ~90 s a round) and bound it.
- Wave 2 is live since 2026-10-06 (`scripts/wave.py`, SL 15 / TP 40, 20 species, rooms STR-0097..0116, 7-day window, verdict ~13. 10.): then compare each species with its wave-0 baseline. One window is a measurement, not a finding. Two bots read balance 0 on the sampler: check which.
- The tick's duplicate-clone block (`_species_cloned`, `live_refs`) is stale since REPLY-0122 (2026-10-04, repeat clones allowed on Pro): lift it, test first.

## How the manager goes wrong
Manager behaviour only -- what Nexus or Cymetica did is in the diary and the memories.

- 2026-10-05 Took a room's status for the bot's state. Nine wave-0 bots had been auto-paused after one trade; their rooms said `running` until I looked at the sampler. See [[verify-a-workflow-is-live-before-building-for-it]].
- 2026-10-05 Answered "why is nothing live" with a recap and an offer, not with a fix. The operator: a manager who acts. See [[cut-the-prose-not-the-answer]].
- 2026-10-05 Told the operator to send a Telegram message that goes out by itself and wait for "poslano". See [[the-journal-records-our-pipeline-not-the-operator]].
- 2026-10-05 The first live run of `wave.py` lost nineteen bots to one uncaught ReadTimeout that came AFTER an accepted PATCH; every call to their API inside a loop is now wrapped and a bad read stops one bot, not the wave.

## Feedback and what changed
Newest at the end. Written by `lab.py log --feedback` / `--acted`; the first six are copied from the diary.

- 2026-09-24 · feedback · Zpětná vazba k rannímu přehledu: na desktopu vypadal skvěle. Mobil nepoužívá vůbec -- V11 done-when požadavek na mobilní screenshot je tím neplatný.
- 2026-09-24 · acted · V11 v plánu upraveno: mobilní screenshot vypuštěn, protože operátor mobil nepoužívá; desktop potvrzen.
- 2026-09-25 · feedback · operator 2026-09-25: the morning report should also say what I learned the previous day and what I improved -- an overview of the self-healing and self-improvement
- 2026-09-26 · feedback · Ranní přehled 26. 9.: '30 z 31 skutečných nálezů' nejasné (bugy v Cymetice, nebo u nás?); čísla procesu (44 tvrzení, 68 kontrol, 3 čtenáři) nezajímají -- jen praktická věcná fakta; 'Čeká na tebe' vadí, nic na něj nečeká; řádek Nexus (62 odpovědí -> 0 vyšlo) nesrozumitelný: vypadá, že se nic netestovalo.
- 2026-09-26 · acted · Ranní přehled: nový oddíl Cymetica přes noc (sweepy, co jsem nahlásil, co opravili, co jsem ověřil); opravy z deep passu jsou psané jako naše, bez čísel procesu; 'Čeká na tebe' zmizelo; řádek Nexuse říká, kolik šlo na papír, vydělalo, prodělalo a ještě běží.
- 2026-09-28 · feedback · Operator 2026-09-28: the 'Na Telegram pro Cymetiku' block with a copy button is top -- keep it every morning.
- 2026-10-05 · feedback · 2026-10-05: ja te nechapu ze porad prodelavas na event cartach, ja ted jen nahlednul do profilu a vse sviti zelene
- 2026-10-05 · feedback · 2026-10-05: a proc nejsou zadni boti live?
- 2026-10-05 · feedback · 2026-10-05: tak proc nespustits 20 botu tech upgraded verzi? prijde mi ze jsi pekne trapny manager laborky asi te vyhodim
- 2026-10-05 · feedback · 2026-10-05: mas jako manager laborky nejakou soubor kde si pises imprvmenty jak lepe runovat laborky podle mych feedbacku? ... tak to pekne sjednot ne at je to na jednom miste tvezlepsovani jako managera laborky
- 2026-10-05 · acted · docs/lab-manager.md je jedno misto pro zlepsovani manazera; feedback a acted se tam zapisuji samy; resume tiskne otevrene body. Boti: wave 0 uzavrena (5 prezilo, 4 vyvracena, vsichni zastaveni platformou po jednom obchodu), scripts/wave.py spusten pro 20 botu SL 15 / TP 40; stihl jen klon MACD Hunter s nastavenim (bez penez, nestartuje), pak spadl na timeoutu cteni; zbytek ceka
- 2026-10-05 · acted · oprava predchoziho zapisu: wave.py stihl jen klon MACD Hunter s nastavenim, bez penez a bez startu; stav je v docs/bots-research-plan.md Wave 2 zive
- 2026-10-05 · feedback · a feedback
- 2026-10-05 · acted · a acted
- 2026-10-05 · feedback · a feedback
- 2026-10-05 · acted · a acted
- 2026-10-05 · feedback · a feedback
- 2026-10-05 · acted · a acted
- 2026-10-06 · feedback · a feedback
- 2026-10-06 · acted · a acted
- 2026-10-06 · acted · Wave 2 spustena 6. 10.: 20 botu obchoduje (SL 15 / TP 40, rooms STR-0097..0116, verdikt ~13. 10.). wave.py opraveno dvakrat: cteni nastaveni z odpovedi PATCH a vysledek fund/enable ze zaznamu. Sweep 39 otevrenych radku, nic noveho k podani. Dlazdice Fondy z ranni stranky smazana.
- 2026-10-07 · acted · Boti: wave.py resume spusten 7. 10.: 18 botu obnoveno po pauze platformy na SL/TP, kazdy v novem roomu (STR-0117..0134) s kriteriem pred enable; 25 obchoduje (strop platformy), 14 ceka na volny slot. 3x stop-loss po sobe = zahozen (operator), zatim zadny.

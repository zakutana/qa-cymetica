---
name: crew
description: The company (docs/crew-plan.md) from the chat -- start it, stop it, say how it is doing, and carry the operator's words to its manager. Use when the operator says "zapni laborku", "vypni laborku", "jak jede firma", "stav firmy", "co dělá firma", "co píše manažer", "řekni manažerovi ...", or asks about the departments.
---

# The company

[operator 2026-10-11] *"hele nemelo by cele vedeni labroky uz mit vice delniku? ja chci aby laborka treba jela nonstop kdyz ji zapnu ale nevim jak to nastavit, jeslti loopem nebo jak se to dela?"*

[operator 2026-10-11] *"Vsechna oddeleni mluvi jen do managera ktery je hlavni orchestrator a ridi co kdo dela a komunikuje smenou chapes."*

[operator 2026-10-11] *"zas ale mysli aby tento cely navrh byl efektivni e nesezral hned vsehcny tokeny, ale ne na ukor kvlaity"*

[operator 2026-10-11] *"presne tak auditor musi hodnotit vsehcny procesy a zjistit neefektivnosti."*

[operator 2026-10-11] *"Cela firma musi davat smysl jak je udelane ne ze tma budou nejake nesmysl nelogicke v kodu pak"*

A manager (Opus) talks only with the operator and the departments; Bugs (Sonnet) is the one department that tests, verifies and files; the laboratory runs its tick as code and calls a model only to decide; the desk (Opus) has one goal, to prove money can be made on Cymetica; the outsider looks once a day from outside the repository. Departments talk only through tickets: one owner, an end. The process auditor is the deep pass's weekly look back, independent of the manager it also judges. Where the code lives and why: docs/crew-plan.md, "Implementation decisions".

## What the operator says, and what this session does

- „zapni laborku" -- `python scripts/crew.py start`. It refuses while `claude` is not logged in on this machine; then one Czech line: run `claude` once and `/login`. Once on, a chat `/loop` tick says the company runs the clock and does nothing.
- „vypni laborku" -- `python scripts/crew.py stop`.
- „jak jede firma", „stav firmy" -- `python scripts/crew.py status`, then three Czech lines at most: what runs, what moved today, what waits on them. The numbers: `python scripts/crew.py audit --days 7`.
- The session start names notes from the manager, or they ask -- `python scripts/crew.py inbox`, said in Czech, numbers first.
- Their words for the company -- `python scripts/crew.py ticket --to manager --kind operator --text "<their words, verbatim>"`; the manager answers in the inbox.
- A bug or a sweep asked for in chat while the company runs -- a ticket to Bugs (`--to bugs --kind bug` or `--kind sweep`), never a filing from the chat: Bugs is the one writer of the bug pipeline.

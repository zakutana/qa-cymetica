# Build it Better: My Agents + Manage (/my-agents and /clone/{id})

**Drawn with the operator on 2026-10-17** from our own 50 clones (read with our API key, `make_data.py`) and the live pages: /my-agents read from its source (the pane was not signed in), /clone/862f0418 read as a guest. Form copied from ET-31702 (Agent Tournaments v3, `../tournaments-v3/request.md`), one request with one link, one item per line. One change from that precedent: there the pictures were "layout and content, not a new visual style", and ET-30773 came back plain; here the operator wants the look ("musi to vypadat vizualne vsechno top"), so line 0 says the pictures are the target. And, his words while it was written, *"hlavne tam napis ze je to cele jen navrh designu, ne ze tim narusime nejakou funkcionalitu"*: line 0 opens "Design only", every function stays, and a line that would need the platform to work differently is to be left out. No open request on either page (board read 2026-10-17).

What is new on the platform, not just redrawn, is named in the lines themselves: Undo after Delete (6), restart after a stop on the page (18, the API has it), Save with a change count (24), the at-a-glance column (23), the P&L-by-bot chart (1). The operator kept the visual additions: *"graficky vylepseni klidne nechej, to je jen dobre"*.

## The block

`spec.txt` beside this file: 34 lines, 5,978 characters (limit 8,000 and 40 items). The form can load it as a file.

## The pictures (the form takes at most 6), all 1440 px, in `spec/`

Drawn by `spec_shots.py` from `index.html` and `manage.html`; palette-scanned, checked for spills, icons and JS errors at 1440 and 1920 by `render.py`.

1. `1-my-agents.png`: the top band and the table (first 12 bots).
2. `2-my-agents-bot-panel.png`: a row clicked, the side panel open (paused by its stop-loss, can't-trade reason, decision rule).
3. `3-manage-markets.png`: Manage, Markets tab, event cards and catalog switched on.
4. `4-manage-risk.png`: Risk tab, the bracket, the sliders, trailing floor on.
5. `5-manage-strategy.png`: Strategy tab, the three rules.
6. `6-manage-advanced.png`: Advanced tab, the Glassnode gate on with one condition row.

## Filing

On https://cymetica.com/build-it-better, "I have a link" with `https://cymetica.com/my-agents`, name "My Agents", the block from `spec.txt`, the six pictures in this order. Filing is the operator's. After filing: check their BB-SPEC line by line against `spec.txt`, then BB-ACCEPT without a BB-CHANGE if it matches.

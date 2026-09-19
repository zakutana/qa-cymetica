---
name: pokracuj
description: One tick of the laboratory under its older name -- exactly the tick `laborator` describes. Invoked by "pokracuj v laborce" / "pokracuj" and by a /loop whose prompt still says so.
model: sonnet
effort: high
---

# Pokračuj

[operator 2026-09-13] *"chci at je genericky ne ze v nem pisu lab-0004 chci
nejaky komand co budu pokazde stejny psat a ty sam si zrcis co jdes delat
proste zjistis kde jsi skoncil a pojracujes v pruzkuku"*

The prompt never changes and never names a session. The procedure is one, and
it lives in `.claude/skills/laborator/SKILL.md` under **A tick**: read where
the last tick stopped, run `python scripts/lab.py tick`, read what came back,
put a question to Nexus when the tick says one may go, write the diary with
`lab.py log`, answer in a few lines. Follow it from there.

This name is kept so the older prompt keeps working. It used to run only the
search, which recombined the same seven cards until it ran dry and never once
asked Nexus -- the reason the tick replaced it.

The operator does not read long answers ([operator 2026-09-13], CLAUDE.md).
A tick that produces three paragraphs has failed even if the work was right.

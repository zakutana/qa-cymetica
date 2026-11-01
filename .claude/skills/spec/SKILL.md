---
name: spec
description: Write a Build it Better request for Cymetica: read their live page, mirror it with our patch on top, one review, push the pictures, file it, and when it ships test it and give the verdict. Use when the operator says "napis spec", "build it better", "podej to", or names an app to improve.
---

# A Build it Better spec

Copy `outbox/_template/` to `outbox/<app>/`. Limits, enforced by `scripts/bb.py` before anything leaves: **8,000 characters, 40 lines, 6 design URLs**.

## Steps

1. **Read how the last accepted one was filed.** `python scripts/bb.py get ET-xxxxx` for the same app; copy its form. Say in one line which one you followed.
2. **Read their live page and their rules.** Their palette is cyan, green, red, blue; purple, amber, orange, yellow and plain gray are refused when a build is checked. Grep their page script and CSS for a control before you specify it: a line duplicating an existing control gets refused or built twice.
3. **Mirror their page, patch on top.** A mock for them is their live page (their HTML, GET only) with our change on it, so the operator sees the change and not our drawing. A new product starts as a mirror of their nearest sibling page with only `<main>` replaced. When the operator names a piece of theirs, fetch their CSS and JS for it and copy that. Serve it with `python scripts/serve_mock.py outbox/<app> <port>` (no-store, GET only), add it to `.claude/launch.json`.
4. **Look at it yourself, then the operator scores it.** A design page gets no test suite: *"jediny tester jsem ja"*. Open it in the pane at 1440 and 390, check the first screen, the motion, and that a colour he named measures as that colour. Change only what his score names.
5. **Goals, not methods.** `request.txt`: title, numbered goals, `PICTURES` with raw GitHub URLs, `Done when: [ ] 1-N`. Figures come from one model, not typed per screen. Name each screen as he sees it. Say what stays true on its neighbour.
6. **One review, by you.** *"Udělej finální review"* is one pass, not three agents.
7. **Push the pictures, file it.** Commit and push (a filed request points at raw GitHub URLs: never move or rename that folder afterwards), then:
   ```bash
   python scripts/bb.py file --app-url https://cymetica.com/<app> --improvements-file outbox/<app>/request.txt --design-url <url> --confirm
   ```
   Add scope later with `bb.py change <ticket> --text-file F --confirm`. `bb.py accept <ticket> --confirm` locks the scope, and that word is the operator's unless they said it. Record the ticket in the folder's `README.md`.
8. **When it ships** (the session start says so): test every line of `Done when` against the live page, write `docs/<ticket>-verification.md`, one line per item. A bug found goes through `submit.py` unasked. **The verdict is the operator's**: tell them the score and what you would say; `bb.py verdict <ticket> pass|fail --note-file F --confirm` only on their word.

Before drawing: `python scripts/memories.py --for spec`, and `--for mock` for a page.

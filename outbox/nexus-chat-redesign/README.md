# NEXUS chat redesign

`python outbox/nexus-chat-redesign/serve.py`, then http://127.0.0.1:8830/gem-screener (any page of theirs works).

Their pages, read anonymously, with `nexus-chat.css` replaced and `nexus-chat.js` patched: `template.html` is the new
markup and `DESIGN` in `serve.py` the changes to their own script (v=20261027-1, `live/`). Every class other scripts hook
into stays. `DEMO` and `demo.js` exist only for this copy. Nothing is sent to Cymetica: chat, upload, subscription and
exchange calls are answered locally, replies are scripted, the table's figures are read from `/api/v1/gem-screener/ranked`.

| Today | Now |
|---|---|
| Bar across the bottom, badge | Nexus's head in the corner, opens the window; red dot on a new reply; no page space reserved |
| Enable switch, enable prompt | **Removed.** The first message already turned Nexus on (`Be`); the price stays on the plan chip |
| Title, status dot | Head and title (`NEXUS AI — bot` on a clone page) |
| Subscription button and panel, all plans | Plan chip, sheet over the thread; subscribe, cancel with an inline second click |
| New chat | Header |
| Language, Share link, Maximize, Pin (right, left, off) | `...` menu, same steps; share answers with a toast |
| Minimize, Close | X; pinned, both |
| Resize | Corner grip, both directions (rail: width) |
| Attach (image, video, PDF, 5), paste, drag and drop, previews | Composer |
| Select on page, chip | Composer (the button now works, #301) |
| Voice with its spoken commands, Ctrl+Shift+M, read replies aloud | Composer |
| Enter, Shift+Enter, Esc, autogrow | Same, grows to 168 px |
| Streaming, Connecting, Thinking, Loading context, Working, Gathering data | Shimmer line, Nexus's eyes quicken |
| Reconnecting, offline, degraded, errors, session expired | Same text |
| Markdown, tables, code, links | Restyled |
| Copy reply, quick replies from Option A/B | Under the reply, chips |
| Cost, MicroFund, billing warnings | Under the reply, and they now stay (#302) |
| Welcome: the title alone | New text: "Ask NEXUS anything", "Type, attach a file or point at anything on this page." |
| Token launch card, exchange picker and form | Cards in the thread |
| Prefill links (`?nexus=`, `nexuslink`), history, sessions, phone keyboard fit (`--nx-vvh`) | Untouched |

Also changed: clicking the page no longer closes the window (Esc and X do); IBM Plex is loaded by the chat, because most
pages load only Inter and JetBrains Mono while the tokens name Plex.

Exceptions to `tokens.css` a spec has to name: accent also on the window's lit top edge, the launcher's glow, the price's
gradient and the active mic (rule 1); `--pos` green on Nexus's eyes, their glow and the picked element's flash (rule 2).

# Build it Better: Infiltrator (draft, not filed)

The operator, 2026-10-13: a new product that sits in the crypto groups on Telegram, only watching, reads each group's sentiment until it understands what that community would really love, and then puts a suggestion on a board where the Cymetica community can pick it up and build it, to win that community. Design: the list of where we listen, one funnel, the board of ideas. Then: Cymetica users suggest the next communities and vote, priority by the biggest ET10 bid as on the Feature Leaderboard; and it plugs into Cymetica's existing engine (Belief Networks: the Animal Spirits meter, the Gem Screener's theme attention, the Product Trend Radar communities), it does not build its own.

Ours, their veto open: public groups only, reading only, counts and no names or message text, leaving a group that bans bots. Reading private chats covertly would break Telegram's rules and the GDPR and would cost Cymetica the communities it means to win; their engine already publishes counts only ("Only counts are published, no messages and no names", llms.txt, Animal Spirits).

Pictures (`mockup.html`, rendered by `render.py`): `desktop-1920.png`, `desktop-1440.png`, `phone-390.png`. Sample data, fictional group names.

On the form: "I have an idea", name **Infiltrator**, the block below, the three PNGs as pictures. After filing, check the BB-SPEC line by line, then BB-ACCEPT.

```
Infiltrator: a new page that listens in public crypto groups on Telegram, learns what each community would love, and puts the best ideas on a board for the Cymetica community to build, so Cymetica wins those communities. Goals, not methods. The attached pictures are the template and the spirit is the requirement: shape, proportions and wording are yours to improve. Colours: the site's cyan, green, red, blue and slate-blue neutrals; no purple, orange, amber, yellow or plain gray. English, numbers before words.
1. Built on your Belief Networks engine, the one behind the Animal Spirits meter, the Gem Screener's theme attention and the Product Trend Radar communities: Infiltrator adds communities to it and reads it per community; it does not build a second listener.
2. Rules, shown as chips at the top: public groups and channels only, read the way your engine reads public chats today; it never posts and never messages anyone; counts only, no names, handles or message text, as your engine publishes today; it leaves a group whose rules forbid bots.
3. A funnel across the top, numbers first: groups found, listening, understood, ideas drafted, on the board, picked to build, shipped.
4. Next in line: anyone signed in can suggest a public group (link, language, topic). Suggestions queue like the Feature Leaderboard: the biggest ET10 bid joins first, votes break ties, the same bid rules. Each row: rank, name, members, votes, ET10 bid, a Bid button.
5. Where we listen: every group with members, language and topic, its status (Listening, Learning with a % bar, Understood, Left with the reason), its mood on your -100 to +100 scale and the days listened; filter chips with counts.
6. A group is understood when the engine has enough of it (a good default: 7 days, 30 people, 5,000 messages). Only an understood group puts an idea on the board; a learning group's idea shows as a draft with its %.
7. The idea board: one card per idea with the community (name, members, mood), a short title, the three themes it talks about most with their share of messages, one line "Why they'd love it", Fit 0-100, Evidence (messages and days read), Effort (S, M, L), votes, status (Draft, On the board, Picked, Building, Shipped) and "Build it".
8. An idea uses what Cymetica already has where it fits (Gem Screener guardians, Team Dump Radar, FOMO Radar, Agent League, Nexus) and names it on the card; an idea that needs something new says so.
9. "Build it" opens a Build it Better request pre-filled with the idea, its community and its evidence; a shipped idea's card links to the live page.
10. The board sorts by fit, votes, newest or picked; anyone signed in can vote.
11. At 1920 x 1080 the funnel, the queue's top rows, the first groups and the first ideas are on one screen; on a phone the board comes first, then the queue, then the groups.
12. Agents can read the groups, the queue and the board as JSON, and suggest and bid with the same auth as the Feature Leaderboard.
Done when:
[ ] 1 Communities and moods come from the Belief Networks engine; there is no second listener.
[ ] 2 No message text, name or handle from a group appears on the page or in its API; every group listed is public; a group that bans bots reads Left with the reason.
[ ] 3 The funnel's seven counts agree with the groups and ideas listed.
[ ] 4 A signed-in user can suggest a group and bid ET10; the queue orders by bid, then votes.
[ ] 5 Each group row shows members, status, mood -100 to +100 and days.
[ ] 6 An idea from a group not yet understood appears only as a draft.
[ ] 7 Each idea card shows community, title, three themes with shares, why, fit, evidence, effort, votes, status and Build it.
[ ] 9 Build it opens a pre-filled Build it Better request.
[ ] 11 At 1920 x 1080 funnel, queue, groups and ideas share the first screen; at 390 px the board is first.
[ ] 12 Groups, queue and board are readable as JSON.
```

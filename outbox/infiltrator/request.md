# Build it Better: Infiltrator (draft, not filed)

The operator, 2026-10-13: a new product that sits in the crypto groups on Telegram, only watching, reads each group's sentiment until it understands what that community would really love, and then puts a suggestion where the Cymetica community can pick it up and build it, to win that community. Then: Cymetica users suggest the next communities and vote, priority by the biggest ET10 bid as on the Feature Leaderboard; it plugs into Cymetica's existing engine (Belief Networks: the Animal Spirits meter, the Gem Screener's theme attention, the Product Trend Radar communities). After the first mock, simpler: four steps only (groups found, listening, ideas drafted, shipped); "Build it" only pre-fills Build it Better and submits nothing; how a group is read and when an idea is drafted is Cymetica's to design, they know the Belief Networks best.

Ours, their veto open: public groups only, reading only, counts and no names or message text, leaving a group that bans bots. Reading private chats covertly would break Telegram's rules and the GDPR and would cost Cymetica the communities it means to win; their engine already publishes counts only ("Only counts are published, no messages and no names", llms.txt, Animal Spirits).

Pictures (`mockup.html`, rendered by `render.py`): `desktop-1920.png`, `desktop-1440.png`, `phone-390.png`. Sample data, fictional group names.

On the form: "I have an idea", name **Infiltrator**, the block below, the three PNGs as pictures. After filing, check the BB-SPEC line by line, then BB-ACCEPT.

```
Infiltrator: a new page that listens in public crypto groups on Telegram, learns what each community would love, and drafts ideas the Cymetica community can build to win those communities. Goals, not methods. The attached pictures are the template and the spirit is the requirement: shape, proportions and wording are yours to improve. Colours: the site's cyan, green, red, blue and slate-blue neutrals; no purple, orange, amber, yellow or plain gray. English, numbers before words.
1. Build it on what you already have for community sentiment. From outside we see it as the Belief Networks behind the Animal Spirits meter, the Gem Screener's theme attention and the Product Trend Radar communities; how it works inside we do not know, so how Infiltrator plugs into it is yours to decide.
2. How a group is read, and when it has learned enough to draft an idea, is yours to design: you know the Belief Networks best. Say on the page in one line what the rule is.
3. Rules, in the (i) beside the title, not as chips: public groups and channels only; it never posts and never messages anyone; counts only, no member's name, handle or message text, as your engine publishes today; it leaves a group whose rules forbid bots.
4. Under the title, the tagline large and bright, not a grey caption; then four steps across the top, numbers first: groups found, listening, ideas drafted, shipped.
5. Next in line: anyone signed in can suggest a public group by its Telegram @handle or t.me link, in one box in the queue's header; name, members and language are read from the group itself. Suggestions queue like the Feature Leaderboard: the biggest ET10 bid is listened to first, votes break ties, the same bid rules. Each row: rank, name and @handle, members, votes, ET10 bid, a Bid button.
6. Where we listen: every group with members, language and topic, Listening or Left (with the reason), its mood on your -100 to +100 scale and the days listened.
7. Ideas: one card per idea with the community (name, members, mood), a short title, the three themes it talks about most with their share, one line "Why they'd love it", votes, and Drafted or Shipped. It uses what Cymetica already has where it fits (Gem Screener guardians, Team Dump Radar, FOMO Radar, Agent League, Nexus) and names it.
8. "Build it" opens Build it Better with the idea, its community and its themes filled in; nothing is submitted until the user sends it. A shipped idea links to the live page instead.
9. Ideas sort by votes, newest or shipped; anyone signed in can vote.
10. At 1920 x 1080 the four steps, the queue, the first groups and the first ideas share one screen; on a phone the ideas come first, then the queue, then the groups.
11. Agents can read the groups, the queue and the ideas as JSON, and suggest and bid with the same auth as the Feature Leaderboard.
Done when:
[ ] 1 Communities and moods come from your existing sentiment engine, and the page says so.
[ ] 2 The page states in one line how a group is read and when an idea is drafted.
[ ] 3 No message text and no member's name or handle appears on the page or in its API; every group listed is public; a group that bans bots reads Left with the reason.
[ ] 4 The four counts agree with the groups and ideas listed.
[ ] 5 A signed-in user can suggest a group and bid ET10; the queue orders by bid, then votes.
[ ] 7 Each idea card shows community, title, three themes, why, votes and Drafted or Shipped.
[ ] 8 Build it opens a pre-filled Build it Better form and submits nothing by itself.
[ ] 10 At 1920 x 1080 the four steps, queue, groups and ideas share the first screen; at 390 px the ideas are first.
[ ] 11 Groups, queue and ideas are readable as JSON.
```

# Build a Company, redesigned: the design to build at /company

A design proposal for Cymetica's Build a Company (feature #911, live at https://cymetica.com/company), from the
account expire76. Everything it shows is in `design/`: a working mockup of every screen, tuned over many rounds and
optimised. What is live today was read on 2026-10-20 (llms.txt's "Build a Company" entry, `GET
/api/v1/company/templates`, `GET /api/v1/companies`, the pages themselves); section 15 lists it beside what this
asks for.

Clickable mockup: https://rawcdn.githack.com/zakutana/qa-cymetica/4247a501222e7e4f195a41935ddf6a2e79b5db38/outbox/company-spec/design/start.html (the entry) and https://rawcdn.githack.com/zakutana/qa-cymetica/4247a501222e7e4f195a41935ddf6a2e79b5db38/outbox/company-spec/design/index.html (the office). The code, screenshots and
this brief: https://github.com/zakutana/qa-cymetica/tree/4247a501222e7e4f195a41935ddf6a2e79b5db38/outbox/company-spec (`design/`, `screenshots/`).

## 0. How to read this

1. **The mockup is the template.** Its look is binding: the layouts, the 3D office and Universe, the rooms, the
   colours, the type, the motion, where every number sits. It is finished and performance-tuned
   (`design/PERF-NOTES.md`), so use its code, and connect your logic to it rather than rebuilding it.
2. **The logic is yours.** `design/sim.js` is a stand-in backend that only simulates; `design/data.js` holds sample
   data. Wire the real API in their place. You see the backend and we do not: **where your backend cannot do what
   the design shows, change the design as little as it takes, and name every such change in your BB-SPEC.**
   Where nothing forces a change, keep the design as it is.
3. **Every text is a draft.** The copy is written from the owner's side. Check every claim against your backend
   and rewrite whatever is wrong or promises what you will not build.
4. **Colours.** The site's palette rule holds for the page's interface (tabs, cards, panels, buttons). The 3D office
   and the Universe are a game scene, outside it: the orange glow of a room that waits on its owner, and the eight
   station colours (green, cyan, blue, red, purple, pink, gold, white), are part of the design.
5. **Name.** The agent the owner talks to is NEXUS everywhere (today's pages say "Manager"). The room it lives in is
   Command. The room that holds the money is the Vault.

## 1. Two modes: /company and /company/app

As the Gem Screener does today: `/gem-screener` is the site's page with the site's header and the app inside it
(an iframe of `/gem-screener/app?view=apps`), and `/gem-screener/app` is the app alone, full screen, without the
site's menu. Build Company the same way:

- `/company/app`: the app alone. **The mockup is this view**; it has no site bar on purpose.
- `/company`: the same app under the site's own header and menu.

Today `/company/app` answers 404.

## 2. The entry: landing, builder, tour (`start.html`, `builder.html`)

Someone with no company lands on the entry, not on an empty office.

- **Landing** (`start.html`): the headline in four lines in the type of `/agent-tournaments`, the last one green:
  "Start an AI-native company. / Build real products. / Bring in users. / Earn real revenue and rewards." Under it:
  "This is not a simulation. Your company runs real AI agents that take on any task: trading, building real apps,
  research, generating real revenue, and much more." Two tiles: **Start a company** (opens the builder) and
  **Explore the Universe** (opens the Universe, section 9). On the right, Cymetica's sun with companies orbiting it.
- **Builder** (`builder.html`), two steps:
  1. **Name & look**: name, mission, public or private (the Vault is private either way), the station picked
     with the arrows round it (seven stations) and its colour (eight). The station's label shows the name as it is
     typed.
  2. **Start**: **New** (the three rooms every company has: Command, Vault, Operations) or **CyMetica Pre-Build**
     (those three and Cymetica QA, Development, Quant Lab, Trading desk). The pre-built office is drawn whole; a
     click on Command starts the tour, one bubble per room on the map, telling one story: Command (you run it all
     through NEXUS), the Vault (what you earn, with your Cymetica balance), Development (build and ship products),
     Cymetica QA (test them, ET10 for verified bugs), the Quant Lab (find trading strategies on paper), the Trading
     desk (run the proven ones for real), Operations (keeps it all optimal). Each bubble links to the room's pages on
     cymetica.com. Create company then opens the step of section 3, and finishing opens the company's office.
- The pre-build is what NEXUS builds from one request (section 4): the builder only asks it for you.

## 3. Creating a company is not free: your call

A free company would let anyone create thousands of them. Pick what fits, and keep the look when you add the step:

- Pro plan and up only;
- a price in ET10 (for example 5,000 ET10);
- a 7-day trial.

The mockup shows the step as a popup on Create company (`builder.html`): signed out, "Sign up first" with Sign up and
Log in (`builder.html?guest`); signed in, the three ways in as tiles -- 5,000 ET10 from the balance, upgrade to Pro, a
7-day free trial. Keep the ones you choose and drop the rest.

Today creating one is free and its work runs only on a paid NEXUS plan (on Free it stays queued).

## 4. NEXUS builds the whole company from one request

Command is NEXUS: the core of light in the middle of the office, nobody standing beside it. It is the only agent
the owner talks to. The owner should be able to say what they want in one message and have NEXUS build it: the
departments, their charters and experts, the processes between them and every room's link. For example (the
owner's words):

> Make me a company with a QA department, where every bug that is logged and verified earns me ET10; a Development
> department, where new apps and ideas are built with my approval; Operations, which audits the processes and keeps
> them optimised; a Quant Lab, where experiments test ways to make money on Cymetica; and a Trading desk, where I
> run the ones that work, even with real money.

That request is the CyMetica Pre-Build. NEXUS must be able to build it from nothing and stack its processes
(section 8), and say what is missing when a request leaves something open. How it works behind the scenes is
yours to design: you are the AI-native company.

## 5. The office (`index.html`)

- **3D office** (three.js, WebGPU with WebGL2 where a browser has none) and the **2D office** one click away; 3D
  replaces today's "3D network" view. Rooms on one platform over a rock in space, as `design/look-office.webp`.
- **A click on a room** flies the camera into it with its detail beside it (a department's work, spend, latest
  results; the Vault's money; Operations' next audit, with the Audit tab one link away). A room at work lights in the
  rail's Working cyan; a room waiting on its owner glows orange.
- **Edit department** is the Add-a-department dialog on the department: its room in 3D, who works there, its charter,
  the experts to hire or fire. The charter lives there, not in the detail.
- **Loading**: while the 3D is built, a loading screen with a miniature of Cymetica's sun and a number, never a
  half-drawn page.
- **Fixed rooms**: Command (NEXUS); Vault (what the company earned, ET10 and USDC as two piles that grow; opened,
  by department and by app; always private: a visitor sees its door shut); Operations (the weekly audit of wasted
  work, duplicates and stuck flows, and keeping the processes optimised).
- **Departments**: each in a room of its own look; its name and icon on the glass; the room glows orange while it
  waits on its owner, and only then.
- **Around it**: the rail of departments (who, what it does now, one number), the Needs-you column, NEXUS's chat,
  and the tabs Portfolio, Tasks, Needs you, Memory, Audit, Processes, Universe, Investable, Legal entity, Token,
  Connect AI (section 13), Settings.
- **Every room links to its page** on cymetica.com, from the computer in the room and a globe icon in its detail:
  Cymetica QA: `/leaderboard/bugs?filter=mine`, which must open the bug board on My Bugs with every bug this
  department filed, under the owner's name (today the page reads nothing from its address, read 2026-10-20: the link
  lands on All); Development and Design studio: `/leaderboard/features`; Quant Lab: the Experiments page (section 7,
  new); Trading desk two: My bots (`/my-agents`) and Agent Tournaments (`/agent-tournaments`).

## 6. The departments

- **Cymetica QA** (the Testing template): Cymetica's bug bounty as a department. It files every verified bug
  straight into the tracker under the owner's hunter name and wallet, as an outside QA agent does today; reopens a
  known bug instead of filing it twice; re-tests a claimed fix on the same ticket. Every bug it files shows in the
  owner's My Bugs on the bug board, counted as the owner's. The ET10 for accepted bugs is lit on the department,
  the rail and the Vault.
- **Development**: Build it Better as a department: idea, spec, design, build, test, release, monitor. What it ships
  goes live on Cymetica as the owner's product and is shown in the Portfolio tab. Submitting a request waits for the
  owner's approval.
- **Operations**: built in (above).
- **Quant Lab** (the Testing lab template): finds the ways to make money on Cymetica. It works strategies out with
  NEXUS and proves them on paper: its success rule and window are set first, the close decides; the winners are
  kept, the rest archived. Its page is Experiments.
- **Trading desk**: puts the Quant Lab's winning bots into production: a seat at an Agent Tournaments table (FLASH
  for a quick read, 7 days for the verdict), or a small real-money stake with its stop set first. Every seat and
  every stake waits for the owner's approval; the company never places a real trade itself. (Your live templates
  give both the Testing lab and the Trading desk paper experiments; this split is the ask.)
- **Design studio and the owner's own departments** as live today; an own department picks its room's look with
  the arrows round it in the Add-a-department dialog.

## 7. The Experiments page (`experiments.html`), the Quant Lab's

New. One card per experiment: its name, one big return (its bots' P&L since they joined, over what they staked), a
line from start to now, its bots as green and red squares, the instructions for the agent running it. Opened: the
bots ranked by return with P&L and trades; Run / Pause; add and remove bots; rename; edit the instructions.
"+ New experiment" is a name, the instructions and the bots, which start trading on paper. The mockup's are seeded
from real paper bots; 500 USDC a bot is the grid's stake.

## 8. Processes (the Processes tab)

How the company works, written by the owner: one sentence each, "When <something happens>, <department> <does
what>", in any language, optionally "and I want to approve it first / see the result". NEXUS reads the trigger,
the department, the work and any review out of it, says what is missing when it cannot, and never adds a second
process that says the same. Each process shows the icon of its trigger, the department it lands in, how often it
fired, and a "then" line: the process that picks up what that department produces next (a release tested by QA
raises bugs, which the bug process files). A process can be switched off or removed.

Today departments cannot hand work to each other (a task's origin is owner, manager or system), so this needs
department-to-department handoff. **Please review it as a design**: from the owner's side it is the simplest way to
say how the company works; keep it if it is sound, improve it where your backend shows a better way.

## 9. The Universe

Every company is a space station on one of the orbits round Cymetica's sun, in 3D (zoom out to all of it, in to
one station, which the camera then follows; a deck per department, lit while it works; work flies to Cymetica as an
arc of light). Public companies open read-only on a click; a private one shows its name, station and mission only,
with a lock. **No sample companies**: the mockup's are placeholders; the live Universe shows only companies people
created. Today `GET /api/v1/companies` lists only Investable companies (none on 2026-10-20) and a private one
answers 404, so it needs all of them, private ones locked. A green Create company on the map takes someone without
a company to the builder. Seven stations (Dreadnought, Shipyard, Pyramid Carrier,
Ring Habitat, Lancer, Citadel, Monolith) in eight colours, picked in the builder and changed in Settings.

## 10. Portfolio and rewards

A tab listing every Build it Better app the account made, with your traffic numbers (visitors, uses, views, likes
over 30 days, from `GET /api/v1/build-it-better/apps/leaderboard`). Two rewards it shows are proposals for you to
set: ET10 for each new unique user an app brings (`/traffic/mine` already counts them) and a USDC revenue share per
use. Both land in the Vault.

## 11. What each department spends, and its brake

Per department: today's spend and the cost of a turn, a daily cap in dollars the owner sets (work over it waits for
midnight), and for a department on a clock, its runs a day. The session and week bars fill in one colour and turn
red only near the limit. Today only `cost_usd_7d` per department and company-wide caps exist.

## 12. Public or private, apart from Investable

Settings has its own switch: public (anyone opens it from the Universe and sees everything inside read-only, the
Vault excepted) or private (name, station and mission only); private by default. Investable stays its own switch.

## 13. Every function for agents: the API, MCP and Connect AI

Everything the page does, an agent must be able to do: create the company (with its look and the start chosen),
add, edit and remove departments and experts, write and switch processes, talk to NEXUS, approve and reject,
run experiments, read the Vault and the Portfolio, change Settings. Through the API and through MCP, and
documented for agents in llms.txt, /api-docs and openapi-public.json. Today openapi-public.json carries 30
company routes and the MCP four tools (company_status, company_message_manager, company_approve, company_create);
processes, experiments, the Vault and the start options have none.

**Connect AI** (a new tab, between Token and Settings): "Talk to NEXUS. Run your whole company from your favourite
AI." What it must hold: the API key, the MCP connector's address, and one ready prompt to paste into ChatGPT,
Claude, Gemini or any AI that speaks MCP; from there the owner runs the whole company in a chat. **Design this tab
yourselves**: the mockup's is only a sketch of its contents, and the prompt's words are yours to write.

## 14. Left to you

The price of a company (section 3); how NEXUS builds a company and how processes run behind the scenes; the copy;
anything your backend cannot do as drawn (change the design minimally and name it). The look is not left open.

## 15. Live today, and what this asks

| Item | Live (read 2026-10-20) | Asked |
|---|---|---|
| Standalone app | `/company` only; `/company/app` 404 | `/company/app` as `/gem-screener/app` |
| Entry | an empty create form | landing, builder, pre-build tour |
| Price | free to create, runs on a paid plan | your choice: Pro+, ET10 price or a trial |
| NEXUS builds from one request | Manager plans tasks; departments come from the create form | one message builds departments, charters, processes, links |
| Fixed rooms | Manager, weekly audit | Command, Vault, Operations |
| Views | 2D floor plan, 3D network | the 3D office and the 2D office |
| Room links | none | QA, Development, Quant Lab, Trading desk (two) pages |
| My Bugs link | the board reads nothing from its address | `?filter=mine` opens My Bugs with the department's bugs |
| API and MCP | 30 routes; MCP 4 tools | every function, documented for agents (section 13) |
| Connect AI | none | a tab of your design: the key, the connector, one ready prompt |
| QA files bugs | drafts, submitted on approval | files verified bugs as the owner, reopens, re-tests |
| Lab / desk | both paper experiments | lab finds and proves; desk runs winners (Tournaments, real money on approval) |
| Experiments page | experiments only inside task detail | the page, section 7 |
| Processes | no department-to-department handoff | section 8 |
| Universe | lists Investable only (0 today) | every company, private ones locked, no samples |
| Spend per department | `cost_usd_7d` | today, per turn, a daily cap |
| Public / private | profile only while Investable | its own switch |

## Files in `design/`

`start.html` landing · `builder.html` builder, tour and the Create step (`?guest` signed out) · `index.html` the app (office, tabs, chat) · `experiments.html`
the Quant Lab's page · `stations.html` the seven stations side by side · `u3d.js` the 3D engine (office, rooms,
Universe) · `stations.js` the stations · `entry3d.js` the entry's 3D · `office.js` the 2D office · `app.js` the
interface · `sim.js` **the stand-in backend, to replace** · `data.js`, `uv-data.js`, `portfolio.js`, `xp-data.js`
sample data · `style.css`, `uv.css`, `start.css`, `builder.css`, `boot.css` (the loading screen), `xp.css` · `sun.webp` the loader's sun ·
`shots/` the dialog cards' and the station tiles' 3D pictures, drawn by the page's own renderers · `look-office.webp`, `look-universe.webp`
the look references · `../screenshots/` every screen at 2000 x 1100 · `PERF-NOTES.md` what was optimised and how it
was measured.

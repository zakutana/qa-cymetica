Re-measured your 12:37 release before replying, as usual. All four hold:

1. Sync door: the same template answer now returns confidence 0.55 with
   answer_source "template". Below your 0.7 floor, so the documented rule
   fires. That is the right fix — you did not change the answer, you stopped
   it claiming to be certain.
2. Async door: noted, and the ET10 answer is in the inbox.
3. get_event_card_info, backtest_event_card_idea and trade_event_card are all
   served; tools/list went 62 to 65. A fresh deep answer named only served
   tools, so the constraint holds.
4. POST /api/v1/a2a/message: GET now returns 405 with the a2a/1.0 schema.

Thank you — that was an hour.

Two things from that same fresh deep answer, and they are questions rather
than reports, because both may be working as you intend and we have twice this
week read a deliberate scope as a defect.

**Does trading_closes_at ever carry a value on a live card?** NEXUS's step 1
tells the agent to "keep only those with status active and a future
trading_closes_at". Right now three cards are tradeable_now, and on all three,
on both /api/v1/event-cards/{id} and get_event_card_info,
trading_closes_at is null:

    30408a4b  status live  trading_closes_at null
    5e25b255  status live  trading_closes_at null
    30015006  status live  trading_closes_at null

So an agent following that plan literally filters out every card and trades
nothing. If null means "no scheduled close, trades until resolution" then the
data is right and the instruction is what needs the edit. If the field is
meant to be populated, it is the other way round. We cannot tell which from
outside, and either way the plan as written cannot select a card.

**Should a theme lookup surface settled cards?** In the same answer NEXUS
reported it could not find a single confirmable open card: its probes for
SpaceX / AI / crypto / Bitcoin themes returned EVCDX-SPACEX-SETS-ASIDE-UP,
EVCDX-STOCKS-BOUNCE-AS-AI, EVCDX-CRYPTO-EXCHANGE-BINA and
EVCDX-BITCOIN-S-TRAPPED-UN, all settled in early June. Meanwhile
GET /api/v1/event-cards lists three cards with tradeable_now true, and we have
traded one of them twice today. get_event_card_info by id is correct — it
returns status "live" for that card. It is the lookup by theme that returns
the June set.

The two compound: the search does not reach a live card, and the filter would
reject it if it did. Your own AI concluded there was nothing open to trade on
a platform with three open cards.

Separately, #87 is still open on our side and is the one that blocks the
campaign: an event-card buy with paper true opens a correct position and no
paper balance moves, in either account mode — SIM USDC, SIM TRADES and SIM P&L
all stay at their opening values in your own UI, and no paper trade appears in
the transaction history. We can score a campaign from the position rows
ourselves, and will, but there is no published number an agent can size
against.

We are running the campaign on MCP as you suggested, and will keep sending
what we measure.

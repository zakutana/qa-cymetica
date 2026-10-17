/* Our real paper clones and the experiments they were made for, read 2026-10-17 from cymetica.com with our
   API key (outbox/my-agents-redesign/make_data.py). Each bot staked 500 USDC (the grid's plan), so its % is
   P&L / 500. Written by make_xp_data.py; the page's simulation moves only what is trading. */
window.XP_SEED = {
"stake": 500,
"bots": [
{
"id": "862f0418-0c04-4ba3-869a-98b8ff9a5bd6",
"name": "lab Grid ATR Alpha",
"species": "ATR Alpha",
"pnl": 0.0,
"trades": 0,
"status": "paused",
"why": null,
"created": "2026-10-12T17:25:52.469798+00:00"
},
{
"id": "7b5f05b8-fb3d-4ba9-b0e6-ca1c4673e3a6",
"name": "lab Grid Trend Titan",
"species": "Trend Titan",
"pnl": -25.0,
"trades": 1,
"status": "stopped",
"why": "stop_loss",
"created": "2026-10-12T17:00:00.982773+00:00"
},
{
"id": "b2d9f0c0-26d5-4f50-873d-f604310652bb",
"name": "lab Grid Bollinger Bandit",
"species": "Bollinger Bandit",
"pnl": -25.0,
"trades": 3,
"status": "stopped",
"why": "stop_loss",
"created": "2026-10-12T16:59:11.047856+00:00"
},
{
"id": "4c1200a4-3cef-4ff7-9959-b578fc04133c",
"name": "lab Grid Delta Hunter",
"species": "Delta Hunter",
"pnl": -25.0,
"trades": 3,
"status": "stopped",
"why": "stop_loss",
"created": "2026-10-12T16:58:29.922486+00:00"
},
{
"id": "ecc49335-d38f-4a2d-a29a-df6b46056986",
"name": "lab Grid Liquidation Hunter",
"species": "Liquidation Hunter",
"pnl": 0.0,
"trades": 0,
"status": "trading",
"why": null,
"created": "2026-10-12T16:28:21.244491+00:00"
},
{
"id": "449ebf02-5db0-48af-90c0-acaddb190eb3",
"name": "lab Grid ATR Alpha",
"species": "ATR Alpha",
"pnl": 175.0,
"trades": 17,
"status": "stopped",
"why": "take_profit",
"created": "2026-10-12T16:28:02.690041+00:00"
},
{
"id": "1000e6d5-e58d-4ccc-97b8-d2839042fb19",
"name": "lab Grid Stochastic Striker",
"species": "Stochastic Striker",
"pnl": -20.0,
"trades": 3,
"status": "stopped",
"why": "stop_loss",
"created": "2026-10-12T16:27:42.050905+00:00"
},
{
"id": "a50ba9be-0372-43da-a553-96420dff4f63",
"name": "lab Grid Volume Viper",
"species": "Volume Viper",
"pnl": -20.0,
"trades": 3,
"status": "stopped",
"why": "stop_loss",
"created": "2026-10-12T16:27:23.167303+00:00"
},
{
"id": "692c35b3-29a7-4cda-8c73-7802cd28e4a8",
"name": "tournament Perceptron Oracle",
"species": "Perceptron Oracle",
"pnl": 191.99,
"trades": 78,
"status": "trading",
"why": null,
"created": "2026-10-11T18:59:54.539213+00:00"
},
{
"id": "3453bac2-409b-451d-b360-43ac9c5ef3a0",
"name": "lab Wave 2 Corr Catcher",
"species": "Corr Catcher",
"pnl": 50.47,
"trades": 33,
"status": "stopped",
"why": "stop_loss",
"created": "2026-10-06T05:02:18.719295+00:00"
},
{
"id": "82578fef-a4cc-49db-9425-276991535b87",
"name": "lab Wave 2 Stat Oracle",
"species": "Stat Oracle",
"pnl": -24.87,
"trades": 73,
"status": "stopped",
"why": "take_profit",
"created": "2026-10-06T05:01:47.100327+00:00"
},
{
"id": "a581e0e0-b313-434f-b53d-275eb1252d49",
"name": "lab Wave 2 Dread Gauge",
"species": "Dread Gauge",
"pnl": 125.0,
"trades": 23,
"status": "stopped",
"why": "take_profit",
"created": "2026-10-06T05:00:38.805963+00:00"
},
{
"id": "8ff88782-0f7c-443f-a77c-74bf4f7805d2",
"name": "lab Wave 2 Crash Detector",
"species": "Crash Detector",
"pnl": -11.13,
"trades": 59,
"status": "stopped",
"why": "stop_loss",
"created": "2026-10-06T05:00:10.226479+00:00"
},
{
"id": "6cb21a44-67c4-4b45-b8d0-cf874a8d6b0e",
"name": "lab Wave 2 Sync Master",
"species": "Sync Master",
"pnl": -174.88,
"trades": 11,
"status": "stopped",
"why": "stop_loss",
"created": "2026-10-06T04:59:35.597677+00:00"
},
{
"id": "1eb11e58-5ecd-4bb8-92bb-21c7b948779c",
"name": "lab Wave 2 Vortex Drain",
"species": "Vortex Drain",
"pnl": -70.96,
"trades": 49,
"status": "stopped",
"why": "take_profit",
"created": "2026-10-06T04:58:42.129655+00:00"
},
{
"id": "c5c988d3-11c9-42a2-abe1-7a90f44e5f57",
"name": "lab Wave 2 Doom & Gloom",
"species": "Doom & Gloom",
"pnl": 43.12,
"trades": 68,
"status": "stopped",
"why": "stop_loss",
"created": "2026-10-06T04:57:56.569508+00:00"
},
{
"id": "abc0e242-f981-4b8e-906d-d2b94cc63681",
"name": "lab Wave 2 Fade the Rally",
"species": "Fade the Rally",
"pnl": 115.87,
"trades": 71,
"status": "stopped",
"why": "stop_loss",
"created": "2026-10-06T04:57:15.082364+00:00"
},
{
"id": "3b1512cb-7d41-4a3d-a6f9-e1bf2649ed0c",
"name": "lab Wave 2 Sent Surfer",
"species": "Sent Surfer",
"pnl": 213.57,
"trades": 132,
"status": "stopped",
"why": "stop_loss",
"created": "2026-10-06T04:56:29.614958+00:00"
},
{
"id": "da83f3d1-1350-43fe-9a5b-b23183aced92",
"name": "lab Wave 2 Perceptron Oracle",
"species": "Perceptron Oracle",
"pnl": 268.3,
"trades": 64,
"status": "stopped",
"why": "stop_loss",
"created": "2026-10-06T04:55:35.192220+00:00"
},
{
"id": "8f05f8dd-c9dd-4c27-a8f0-d18b691a91db",
"name": "lab Wave 2 Divergence Dragon",
"species": "Divergence Dragon",
"pnl": 189.18,
"trades": 91,
"status": "stopped",
"why": "stop_loss",
"created": "2026-10-06T04:54:31.247987+00:00"
},
{
"id": "cec6eddf-e970-4441-bdf0-e877319a2df2",
"name": "lab Wave 2 ATR Alpha",
"species": "ATR Alpha",
"pnl": -113.25,
"trades": 46,
"status": "stopped",
"why": "stop_loss",
"created": "2026-10-06T04:53:34.775985+00:00"
},
{
"id": "f63d0fb9-4bc2-46c6-8e0d-27ae804e090c",
"name": "lab Wave 2 Fibonacci Phoenix",
"species": "Fibonacci Phoenix",
"pnl": 81.28,
"trades": 62,
"status": "trading",
"why": null,
"created": "2026-10-06T04:52:31.256888+00:00"
},
{
"id": "d9afe12b-0630-4480-9aa4-68c54d7b45b6",
"name": "lab Wave 2 Ichimoku Empress",
"species": "Ichimoku Empress",
"pnl": -174.88,
"trades": 14,
"status": "stopped",
"why": "stop_loss",
"created": "2026-10-06T04:51:56.930431+00:00"
},
{
"id": "44d4a2eb-5aa2-4e67-81f1-4aa6d6db43db",
"name": "lab Wave 2 Stochastic Striker",
"species": "Stochastic Striker",
"pnl": 40.77,
"trades": 50,
"status": "stopped",
"why": "stop_loss",
"created": "2026-10-06T04:51:13.737462+00:00"
},
{
"id": "20b3df18-0101-4619-ae50-47b7d9879904",
"name": "lab Wave 2 Trend Titan",
"species": "Trend Titan",
"pnl": -166.8,
"trades": 14,
"status": "stopped",
"why": "stop_loss",
"created": "2026-10-06T04:49:57.364929+00:00"
},
{
"id": "f2f18226-ebe8-4eb3-909f-daf2285ef29f",
"name": "lab Wave 2 Volume Viper",
"species": "Volume Viper",
"pnl": 200.85,
"trades": 43,
"status": "stopped",
"why": "take_profit",
"created": "2026-10-06T04:49:06.206261+00:00"
},
{
"id": "70c3f0ff-33d8-4ea9-b60f-7a79d5076992",
"name": "lab Wave 2 Bollinger Bandit",
"species": "Bollinger Bandit",
"pnl": -89.6,
"trades": 31,
"status": "stopped",
"why": "stop_loss",
"created": "2026-10-06T04:25:53.163400+00:00"
},
{
"id": "193f496e-16ff-478b-981a-8b37d3899308",
"name": "lab Wave 2 RSI Sniper",
"species": "RSI Sniper",
"pnl": -174.88,
"trades": 24,
"status": "stopped",
"why": "stop_loss",
"created": "2026-10-06T04:21:59.081479+00:00"
},
{
"id": "9ba3d9e8-22a5-4d8d-a4fa-74213959090e",
"name": "lab Wave 2 MACD Hunter",
"species": "MACD Hunter",
"pnl": -171.26,
"trades": 17,
"status": "stopped",
"why": "stop_loss",
"created": "2026-10-05T14:42:12.834346+00:00"
},
{
"id": "4fe90962-1c84-422a-a184-7c93c5596a77",
"name": "RSI Sniper Clone #2",
"species": "RSI Sniper",
"pnl": 0.0,
"trades": 0,
"status": "paused",
"why": null,
"created": "2026-10-04T04:55:31.467958+00:00"
},
{
"id": "7864de32-9dc6-443a-9c06-80e63dbb2af6",
"name": "lab cap probe Vortex Drain",
"species": "Vortex Drain",
"pnl": 50.0,
"trades": 6,
"status": "paused",
"why": null,
"created": "2026-10-03T20:29:19.377681+00:00"
},
{
"id": "3935efb2-dc10-4ce8-9a3a-2a44cbc67b02",
"name": "lab cap probe Crash Detector",
"species": "Crash Detector",
"pnl": -25.0,
"trades": 1,
"status": "paused",
"why": null,
"created": "2026-10-03T20:29:15.254031+00:00"
},
{
"id": "074d4e7b-5e59-4484-8f94-59a1731e3f0f",
"name": "lab cap probe Fade the Rally",
"species": "Fade the Rally",
"pnl": 100.0,
"trades": 10,
"status": "paused",
"why": null,
"created": "2026-10-03T20:29:10.201242+00:00"
},
{
"id": "414960ef-efb1-4b4a-8973-f286c9a959d2",
"name": "lab cap probe Sync Master",
"species": "Sync Master",
"pnl": 50.0,
"trades": 4,
"status": "paused",
"why": null,
"created": "2026-10-03T20:29:04.676866+00:00"
},
{
"id": "1dda2935-282c-4d72-91e9-d4b3de903c6e",
"name": "lab cap probe Perceptron Oracle",
"species": "Perceptron Oracle",
"pnl": -25.0,
"trades": 1,
"status": "paused",
"why": null,
"created": "2026-10-03T20:29:00.520765+00:00"
},
{
"id": "7792398e-fbd9-4444-9472-07cb6f55f43c",
"name": "lab cap probe Fibonacci Phoenix",
"species": "Fibonacci Phoenix",
"pnl": -20.0,
"trades": 1,
"status": "paused",
"why": null,
"created": "2026-10-03T20:28:57.162685+00:00"
},
{
"id": "388249d4-c061-4885-8a6b-6530a6928686",
"name": "lab cap probe Trend Titan",
"species": "Trend Titan",
"pnl": 95.0,
"trades": 19,
"status": "paused",
"why": null,
"created": "2026-10-03T20:28:05.380427+00:00"
},
{
"id": "1b81dff7-8a27-4f9e-abd8-b3265f1a6244",
"name": "lab cap probe Bollinger Bandit",
"species": "Bollinger Bandit",
"pnl": 165.0,
"trades": 10,
"status": "paused",
"why": null,
"created": "2026-10-03T20:28:01.594337+00:00"
},
{
"id": "31d18d91-14ae-4ebf-a2d3-b56db92ba6c8",
"name": "lab cap probe MACD Hunter",
"species": "MACD Hunter",
"pnl": -25.0,
"trades": 1,
"status": "paused",
"why": null,
"created": "2026-10-03T20:27:57.688292+00:00"
},
{
"id": "f6af3fd1-9532-4783-9a02-737f4c40fca7",
"name": "lab event cards only",
"species": "RSI Sniper",
"pnl": 0.0,
"trades": 0,
"status": "paused",
"why": null,
"created": "2026-09-28T08:41:41.043234+00:00"
},
{
"id": "5124b7be-b66f-4e4c-add1-aa959c832ec3",
"name": "lab h2h Corr Catcher",
"species": "Corr Catcher",
"pnl": -47.7,
"trades": 2,
"status": "paused",
"why": null,
"created": "2026-09-28T07:27:53.364105+00:00"
},
{
"id": "17efa669-c1d8-4471-85a6-6a5f216002bf",
"name": "lab h2h Sent Surfer",
"species": "Sent Surfer",
"pnl": -47.7,
"trades": 2,
"status": "paused",
"why": null,
"created": "2026-09-28T07:27:42.603576+00:00"
},
{
"id": "741a60e4-96bc-4674-a112-e0909c77506c",
"name": "lab h2h Delta Hunter",
"species": "Delta Hunter",
"pnl": -47.7,
"trades": 2,
"status": "paused",
"why": null,
"created": "2026-09-28T07:27:28.386555+00:00"
},
{
"id": "2f75bcf5-c760-4d05-83ea-2369390a403f",
"name": "lab h2h Liquidation Hunter",
"species": "Liquidation Hunter",
"pnl": 0.0,
"trades": 0,
"status": "paused",
"why": null,
"created": "2026-09-28T07:27:06.849434+00:00"
},
{
"id": "cbdc3ecd-2a7d-4c8e-a3d7-2101ea09bf38",
"name": "lab h2h Divergence Dragon",
"species": "Divergence Dragon",
"pnl": -46.38,
"trades": 3,
"status": "paused",
"why": null,
"created": "2026-09-28T07:26:41.795649+00:00"
},
{
"id": "3d5d0bff-5239-4ee9-aeb0-cfbdef3d0c0d",
"name": "lab Stat Oracle",
"species": "Stat Oracle",
"pnl": 69.14,
"trades": 4,
"status": "paused",
"why": null,
"created": "2026-09-25T01:30:59.459599+00:00"
},
{
"id": "4076d1b0-f78b-452f-b66f-f02506a4f219",
"name": "lab h2h ATR Alpha",
"species": "ATR Alpha",
"pnl": 53.89,
"trades": 8,
"status": "stopped",
"why": "take_profit",
"created": "2026-09-24T19:06:16.767124+00:00"
},
{
"id": "314ed16d-ba4a-44cf-82e5-d09ea49f7f68",
"name": "lab h2h Ichimoku Empress",
"species": "Ichimoku Empress",
"pnl": 28.62,
"trades": 4,
"status": "paused",
"why": null,
"created": "2026-09-24T19:06:12.300913+00:00"
},
{
"id": "c0001e8c-84dc-4edf-9e15-d2b43b286a42",
"name": "lab h2h Stochastic Striker",
"species": "Stochastic Striker",
"pnl": 67.04,
"trades": 7,
"status": "paused",
"why": null,
"created": "2026-09-24T19:06:08.412006+00:00"
},
{
"id": "8cda9152-8bb5-4c54-bc05-948b9f6a52ae",
"name": "lab h2h Volume Viper",
"species": "Volume Viper",
"pnl": 66.96,
"trades": 7,
"status": "paused",
"why": null,
"created": "2026-09-24T19:05:53.355592+00:00"
}
],
"experiments": [
{
"id": "x1",
"name": "Wave 2",
"brief": "20 species on paper, stop loss 15%, take profit 40%, a 7-day window. Then compare each species with its first-wave baseline: one window is a measurement, not a finding.",
"created": "2026-10-05T14:42:12.834346+00:00",
"members": [
{
"bot": "3453bac2-409b-451d-b360-43ac9c5ef3a0",
"base": 0
},
{
"bot": "82578fef-a4cc-49db-9425-276991535b87",
"base": 0
},
{
"bot": "a581e0e0-b313-434f-b53d-275eb1252d49",
"base": 0
},
{
"bot": "8ff88782-0f7c-443f-a77c-74bf4f7805d2",
"base": 0
},
{
"bot": "6cb21a44-67c4-4b45-b8d0-cf874a8d6b0e",
"base": 0
},
{
"bot": "1eb11e58-5ecd-4bb8-92bb-21c7b948779c",
"base": 0
},
{
"bot": "c5c988d3-11c9-42a2-abe1-7a90f44e5f57",
"base": 0
},
{
"bot": "abc0e242-f981-4b8e-906d-d2b94cc63681",
"base": 0
},
{
"bot": "3b1512cb-7d41-4a3d-a6f9-e1bf2649ed0c",
"base": 0
},
{
"bot": "da83f3d1-1350-43fe-9a5b-b23183aced92",
"base": 0
},
{
"bot": "8f05f8dd-c9dd-4c27-a8f0-d18b691a91db",
"base": 0
},
{
"bot": "cec6eddf-e970-4441-bdf0-e877319a2df2",
"base": 0
},
{
"bot": "f63d0fb9-4bc2-46c6-8e0d-27ae804e090c",
"base": 0
},
{
"bot": "d9afe12b-0630-4480-9aa4-68c54d7b45b6",
"base": 0
},
{
"bot": "44d4a2eb-5aa2-4e67-81f1-4aa6d6db43db",
"base": 0
},
{
"bot": "20b3df18-0101-4619-ae50-47b7d9879904",
"base": 0
},
{
"bot": "f2f18226-ebe8-4eb3-909f-daf2285ef29f",
"base": 0
},
{
"bot": "70c3f0ff-33d8-4ea9-b60f-7a79d5076992",
"base": 0
},
{
"bot": "193f496e-16ff-478b-981a-8b37d3899308",
"base": 0
},
{
"bot": "9ba3d9e8-22a5-4d8d-a4fa-74213959090e",
"base": 0
}
]
},
{
"id": "x2",
"name": "Grid",
"brief": "Every species across stop / take-profit bands (defaults, 5/20, 10/20, 10/30, 15/40, 20/60), 500 USDC each, a 7-day window. A cell that survives gets a second window: a claim needs two.",
"created": "2026-10-12T16:27:23.167303+00:00",
"members": [
{
"bot": "862f0418-0c04-4ba3-869a-98b8ff9a5bd6",
"base": 0
},
{
"bot": "7b5f05b8-fb3d-4ba9-b0e6-ca1c4673e3a6",
"base": 0
},
{
"bot": "b2d9f0c0-26d5-4f50-873d-f604310652bb",
"base": 0
},
{
"bot": "4c1200a4-3cef-4ff7-9959-b578fc04133c",
"base": 0
},
{
"bot": "ecc49335-d38f-4a2d-a29a-df6b46056986",
"base": 0
},
{
"bot": "449ebf02-5db0-48af-90c0-acaddb190eb3",
"base": 0
},
{
"bot": "1000e6d5-e58d-4ccc-97b8-d2839042fb19",
"base": 0
},
{
"bot": "a50ba9be-0372-43da-a553-96420dff4f63",
"base": 0
}
]
},
{
"id": "x3",
"name": "Head to head",
"brief": "An improved bot against a clone of its species at default settings, 7 days, both kept trading. Judged on our own P&L of both.",
"created": "2026-09-24T19:05:53.355592+00:00",
"members": [
{
"bot": "5124b7be-b66f-4e4c-add1-aa959c832ec3",
"base": 0
},
{
"bot": "17efa669-c1d8-4471-85a6-6a5f216002bf",
"base": 0
},
{
"bot": "741a60e4-96bc-4674-a112-e0909c77506c",
"base": 0
},
{
"bot": "2f75bcf5-c760-4d05-83ea-2369390a403f",
"base": 0
},
{
"bot": "cbdc3ecd-2a7d-4c8e-a3d7-2101ea09bf38",
"base": 0
},
{
"bot": "4076d1b0-f78b-452f-b66f-f02506a4f219",
"base": 0
},
{
"bot": "314ed16d-ba4a-44cf-82e5-d09ea49f7f68",
"base": 0
},
{
"bot": "c0001e8c-84dc-4edf-9e15-d2b43b286a42",
"base": 0
},
{
"bot": "8cda9152-8bb5-4c54-bc05-948b9f6a52ae",
"base": 0
}
]
},
{
"id": "x4",
"name": "Cap probe",
"brief": "Nine species cloned on paper at their default settings.",
"created": "2026-10-03T20:27:57.688292+00:00",
"members": [
{
"bot": "7864de32-9dc6-443a-9c06-80e63dbb2af6",
"base": 0
},
{
"bot": "3935efb2-dc10-4ce8-9a3a-2a44cbc67b02",
"base": 0
},
{
"bot": "074d4e7b-5e59-4484-8f94-59a1731e3f0f",
"base": 0
},
{
"bot": "414960ef-efb1-4b4a-8973-f286c9a959d2",
"base": 0
},
{
"bot": "1dda2935-282c-4d72-91e9-d4b3de903c6e",
"base": 0
},
{
"bot": "7792398e-fbd9-4444-9472-07cb6f55f43c",
"base": 0
},
{
"bot": "388249d4-c061-4885-8a6b-6530a6928686",
"base": 0
},
{
"bot": "1b81dff7-8a27-4f9e-abd8-b3265f1a6244",
"base": 0
},
{
"bot": "31d18d91-14ae-4ebf-a2d3-b56db92ba6c8",
"base": 0
}
]
}
]
};

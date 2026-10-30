/* Our company's Quant Lab, read from their owner-only API by refresh.py. Real, not simulated. */
window.QL_DATA = {
 "as_of": "2026-10-30T13:35Z",
 "company": 14,
 "plan": "Pro",
 "models": 16,
 "markets": [
  "BTC",
  "ETH",
  "SOL",
  "BNB",
  "XRP",
  "ADA",
  "DOGE",
  "AVAX",
  "LINK",
  "LTC",
  "DOT",
  "ATOM"
 ],
 "combinations_tried": 1728,
 "method": {
  "search_period": "earlier 60% of 90 days of hourly bars",
  "held_back": "the later period; the search never sees it",
  "bar": "one-sided 5% test split over every combination tried; never below 1%"
 },
 "searches": [
  {
   "id": 9,
   "status": "failed",
   "origin": "daily",
   "requested_at": "2026-10-30T10:09:52.235149Z",
   "finished_at": "2026-10-30T10:10:36.472997Z",
   "total_jobs": 0,
   "done_jobs": 0,
   "summary": null,
   "error": "OperationalError: (psycopg2.OperationalError) server closed the connection unexp"
  },
  {
   "id": 7,
   "status": "failed",
   "origin": "daily",
   "requested_at": "2026-10-29T10:09:32.965644Z",
   "finished_at": "2026-10-29T10:10:15.451732Z",
   "total_jobs": 0,
   "done_jobs": 0,
   "summary": null,
   "error": "OperationalError: (psycopg2.OperationalError) server closed the connection unexp"
  },
  {
   "id": 5,
   "status": "failed",
   "origin": "owner",
   "requested_at": "2026-10-28T10:09:16.292686Z",
   "finished_at": "2026-10-28T10:10:40.478344Z",
   "total_jobs": 0,
   "done_jobs": 0,
   "summary": null,
   "error": "OperationalError: (psycopg2.OperationalError) server closed the connection unexp"
  },
  {
   "id": 3,
   "status": "done",
   "origin": "daily",
   "requested_at": "2026-10-27T13:29:12.571645Z",
   "finished_at": "2026-10-27T14:01:08.817493Z",
   "total_jobs": 1728,
   "done_jobs": 1728,
   "summary": {
    "combinations_new": 1728,
    "combinations_skipped_known": 0,
    "n_tried_total": 1728,
    "shortlisted": 5,
    "held_back_checked": 5,
    "won": 0,
    "thrown_out_after_check": 5,
    "clones_started": [],
    "markets_searched": [
     "ADA",
     "ATOM",
     "AVAX",
     "BNB",
     "BTC",
     "DOGE",
     "DOT",
     "ETH",
     "LINK",
     "LTC",
     "SOL",
     "XRP"
    ],
    "markets_missing": []
   },
   "error": null
  }
 ],
 "held_back": [
  {
   "model": "stockbull_blue",
   "market": "DOT",
   "settings_label": "SL 3 / TP 30",
   "entry_threshold": "as_is",
   "verdict": "thrown_out",
   "reason": "lost 3.09% on the held-back period (59 trades)",
   "search": {
    "return_pct": 29.6,
    "trades": 94,
    "max_drawdown_pct": 5.13,
    "win_rate": 46.8
   },
   "held": {
    "return_pct": -3.09,
    "trades": 59
   },
   "bar": {
    "n_tried": 1728,
    "z": 4.0213,
    "bar_pct": 9.971
   }
  },
  {
   "model": "helix",
   "market": "DOT",
   "settings_label": "SL 3 / TP 30",
   "entry_threshold": "as_is",
   "verdict": "thrown_out",
   "reason": "lost 1.94% on the held-back period (43 trades)",
   "search": {
    "return_pct": 16.39,
    "trades": 64,
    "max_drawdown_pct": 4.39,
    "win_rate": 35.9
   },
   "held": {
    "return_pct": -1.94,
    "trades": 43
   },
   "bar": {
    "n_tried": 1728,
    "z": 4.0213,
    "bar_pct": 8.621
   }
  },
  {
   "model": "stockbull_blue",
   "market": "LINK",
   "settings_label": "SL 8 / TP 30",
   "entry_threshold": "as_is",
   "verdict": "thrown_out",
   "reason": "lost 12.30% on the held-back period (74 trades)",
   "search": {
    "return_pct": 23.25,
    "trades": 124,
    "max_drawdown_pct": 5.65,
    "win_rate": 46.8
   },
   "held": {
    "return_pct": -12.3,
    "trades": 74
   },
   "bar": {
    "n_tried": 1728,
    "z": 4.0213,
    "bar_pct": 10.766
   }
  },
  {
   "model": "stockbull_blue",
   "market": "AVAX",
   "settings_label": "SL 8 / TP 30",
   "entry_threshold": "as_is",
   "verdict": "thrown_out",
   "reason": "lost 6.87% on the held-back period (74 trades)",
   "search": {
    "return_pct": 20.9,
    "trades": 112,
    "max_drawdown_pct": 6.2,
    "win_rate": 40.2
   },
   "held": {
    "return_pct": -6.87,
    "trades": 74
   },
   "bar": {
    "n_tried": 1728,
    "z": 4.0213,
    "bar_pct": 5.838
   }
  },
  {
   "model": "stockbull_blue",
   "market": "SOL",
   "settings_label": "SL 8 / TP 30",
   "entry_threshold": "as_is",
   "verdict": "thrown_out",
   "reason": "lost 10.01% on the held-back period (90 trades)",
   "search": {
    "return_pct": 20.24,
    "trades": 105,
    "max_drawdown_pct": 4.67,
    "win_rate": 40.0
   },
   "held": {
    "return_pct": -10.01,
    "trades": 90
   },
   "bar": {
    "n_tried": 1728,
    "z": 4.0213,
    "bar_pct": 8.237
   }
  }
 ],
 "rule": {
  "window_days": 3,
  "min_trades": 10,
  "min_return_pct": 2.0,
  "max_drawdown_pct": 15.0,
  "repeats": 2,
  "max_running": 3,
  "capital_usd": 1000,
  "auto": true,
  "variations_per_day": 6,
  "explore_after": 3,
  "handoff": [
   "tournament",
   "live"
  ]
 },
 "rule_text": "at least 10 closed trades, a return of at least 2% and a drawdown under 15% in each 3-day window, 2 windows in a row",
 "running": 2,
 "trading_cap": 100,
 "experiments": [],
 "memory_total": 1728,
 "can_tune": [
  "Stop-loss: three levels around each bot model's own (0.6x, 1x and 1.6x, kept between 1% and 20%).",
  "Take-profit: 8%, 15% or 30%.",
  "Entry threshold: each model's entry rule stricter, as it is, or looser (new 2026-10-28).",
  "Which bot model: all 16 models with a backtest set-up (7 of them equip as free paper bots).",
  "Which market: 12 crypto markets (BTC, ETH, SOL, BNB, XRP, ADA, DOGE, AVAX, LINK, LTC, DOT, ATOM) on hourly bars."
 ],
 "cannot_tune": [
  {
   "what": "Signal weights",
   "size": "build_large"
  },
  {
   "what": "AI confidence",
   "size": "build_large"
  },
  {
   "what": "Position size and number of open positions",
   "size": "build_small"
  },
  {
   "what": "Indicator periods (for example RSI 14 to RSI 10)",
   "size": "build_medium"
  },
  {
   "what": "5-minute bars",
   "size": "build_medium"
  },
  {
   "what": "Cross-exchange arbitrage, funding-rate carry, DEX replay",
   "size": "build_medium"
  },
  {
   "what": "Stocks and other non-crypto markets",
   "size": "build_large"
  },
  {
   "what": "News, social posts and order books",
   "size": "build_large"
  },
  {
   "what": "Starting a paper bot from a changed entry rule",
   "size": "build_medium"
  },
  {
   "what": "Premium models (prion, synapse, telomere)",
   "size": "not_possible"
  },
  {
   "what": "Cymetica bot set-ups as paper bots (cryptobull_blue, cryptobull_red, hybrid2_blue, hybrid2_red, stockbear_red, stockbull_blue)",
   "size": "not_possible"
  }
 ],
 "does_not_do": [
  "It does not trade real money: every clone it starts is a paper bot, and going live always waits for your approval at the Trading desk.",
  "It does not promise profit: most combinations are thrown out, and a clean result on past prices can still lose later.",
  "It searches only stop-loss, take-profit and the entry threshold (a stricter, the same or a looser version of each bot model's own entry rule) on hourly bars of crypto markets; signal weights and AI confidence cannot be replayed yet, so it asks for them as IDEA approvals instead.",
  "A result that won with a changed entry threshold is reported only, not started as a paper bot: a paper bot cannot run a changed entry rule yet.",
  "It does not read news, social posts or order books, and it does not build new markets or backtest setups itself.",
  "It is not Build a Company's product: it is EventTrader's own Quant Lab."
 ],
 "cost": "A search uses none of your plan's units: it runs backtests on the platform's own price history, no AI turns. Price: free for Pro owners."
};

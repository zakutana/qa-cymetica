"""Three checks of ours that were wrong on 2026-10-21, one guard for all three.

Each failed a sweep for a reason that was ours, not the platform's:

* FOMO tail. `improbability` multiplied `math.comb(n, i)` -- an exact integer, a thousand digits
  long once n passes ~1030 -- by a float: OverflowError, on every later sweep, since the diary
  only grows. A crash is not a verdict; the tail is computed in logs now.
* Stop loss (#134). Our laboratory stops a bot it has finished with, and a stopped bot reads
  `current_balance_usdc` 0.0. The baseline `balance - profit` became `-profit` and the loss came
  out as exactly 100 % on five bots whose own pause events recorded -4 / -5 %. The sweep had a
  "we can no longer stand behind our pass" for #134 ready to send.
* Trust ladder. `register_agent` -- "Register this agent and get its API key" -- is listed to a
  caller with no identity and not to one that holds a key (149 tools with it, 157 without). A
  tool that hands out the credential has nothing to offer a caller that has one; every OTHER
  tool lost by authenticating still counts.

One test, because the ceiling on `tests/meta` says a new guard replaces or merges one.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


def _load(name: str, *parts: str):
    spec = importlib.util.spec_from_file_location(name, REPO.joinpath(*parts))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


EVENTS = {"events": [{"event_type": "stop_loss_triggered", "threshold_pct": 5.0, "pnl_pct": -5.0},
                     {"event_type": "trading_resumed"}]}


def _bot(balance: float, profit: float, status: str) -> dict:
    return {"name": "bot", "id": "b", "auto_pause_reason": "stop_loss",
            "current_balance_usdc": balance, "total_profit_usdc": profit, "status": status}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_three_checks_repaired_on_2026_10_21_stay_repaired():
    # FOMO tail: exact for small n, finite and ordered for thousands of windows.
    tail = _load("fomo_check", "tests", "rest", "test_fomo_calibration_reproduces.py").improbability
    exact = sum(math.comb(20, i) * 0.3 ** i * 0.7 ** (20 - i) for i in range(6))
    assert abs(tail(5, 20, 0.3) - exact) < 1e-12
    low, mid, high = tail(100, 5000, 0.112), tail(560, 5000, 0.112), tail(900, 5000, 0.112)
    assert low < 1e-100 and 0.3 < mid < 0.7 and high > 0.999999, (low, mid, high)
    assert abs(tail(5000, 5000, 0.112) - 1.0) < 1e-9

    # Stop loss: a bot whose balance we returned is unreadable, not a total loss; a bot that
    # kept its money is still judged, both ways.
    judged = _load("stop_loss_check", "tests", "rest",
                   "test_a_bot_stop_loss_holds_its_budget.py").judged
    assert judged(_bot(0.0, -25.0, "stopped"), EVENTS, {}) is None
    assert judged(_bot(0.0, -25.0, "paused"), EVENTS, {}) is None
    assert judged(_bot(475.0, -25.0, "paused"), EVENTS, {})["breach"] is False
    assert judged(_bot(430.0, -70.0, "paused"), EVENTS, {})["breach"] is True

    # Trust ladder: only the credential tool may vanish.
    lost = _load("ladder_check", "tests", "mcp", "test_trust_ladder.py").tools_lost_by_authenticating
    assert lost({"a", "register_agent"}, {"a", "b"}) == []
    assert lost({"a", "get_positions", "register_agent"}, {"a"}) == ["get_positions"]

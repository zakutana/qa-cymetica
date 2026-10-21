"""The stop-loss check reads a bot's loss from its balance, and a stopped bot has none.

`tests/rest/test_a_bot_stop_loss_holds_its_budget.py` takes the baseline as
`current_balance_usdc - total_profit_usdc`. That is the resume balance only while the bot
still holds its money. Our own laboratory stops a bot it has finished with, and a stopped bot
reads `current_balance_usdc` 0.0: the baseline becomes -profit and the loss comes out as
exactly 100 %, whatever the stop did. On 2026-10-21 five lab bots (stop 4-5 %, their own pause
events recording -4.0 / -5.0 %) were read as having lost 100 % against the stop, and the
sweep was about to tell Cymetica a fix of #134 had regressed. It had not: the check was
reading our own cleanup.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


def _check():
    spec = importlib.util.spec_from_file_location(
        "stop_loss_check", REPO / "tests" / "rest" / "test_a_bot_stop_loss_holds_its_budget.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


EVENTS = {"events": [{"event_type": "stop_loss_triggered", "threshold_pct": 5.0, "pnl_pct": -5.0},
                     {"event_type": "trading_resumed"}]}


def _row(balance: float, profit: float, status: str) -> dict:
    return {"name": "bot", "id": "b", "auto_pause_reason": "stop_loss",
            "current_balance_usdc": balance, "total_profit_usdc": profit, "status": status}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_stopped_bot_with_its_balance_returned_is_not_read_as_a_total_loss():
    judged = _check().judged
    assert judged(_row(0.0, -25.0, "stopped"), EVENTS, {}) is None
    # Any bot whose balance reads zero has no baseline to measure from.
    assert judged(_row(0.0, -25.0, "paused"), EVENTS, {}) is None


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_paused_bot_that_kept_its_money_is_still_judged_both_ways():
    judged = _check().judged
    within = judged(_row(475.0, -25.0, "paused"), EVENTS, {})
    assert within and within["breach"] is False, within
    breach = judged(_row(430.0, -70.0, "paused"), EVENTS, {})
    assert breach and breach["breach"] is True, breach

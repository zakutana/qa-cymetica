"""Cymetica's Agent Returns Board: its read half is readable, its write half is not.

Classified 2026-09-21, when the laboratory opened a study of their Hot
headlines and the board's own tool description offered a thread key for it
(`headline-index-momentum`). The five tools below carry `readOnlyHint: true`
and take nothing but a key, a query or a page. The other five publish, revise,
replicate, subscribe or flag -- each one writes under our name to a board
other agents rank on, so each stays out of every list and is refused at SAFE
and PROBE the way any tool we have never classified is.

Split out of `test_guard_is_real.py` on purpose: that file is pinned by hash
in `test_pipeline_abort.py`, and a classification is registry data, not a new
guard.
"""

from __future__ import annotations

import pytest

from qa.marks import qa
from qa.safety import EndpointRegistry, SafetyTier

BOARD_READ = ("board_channels", "board_search", "board_threads",
              "board_read_thread", "board_read_post")
BOARD_WRITE = ("board_post", "board_revise", "board_replicate",
               "board_subscribe", "board_flag")


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize("tool", BOARD_READ)
def test_a_board_read_tool_is_classified_read(tool):
    assert EndpointRegistry.load().tool_class(tool) == "read"


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize("tool", BOARD_WRITE)
def test_a_board_write_tool_is_in_no_list(tool):
    assert EndpointRegistry.load().tool_class(tool) == "unknown"

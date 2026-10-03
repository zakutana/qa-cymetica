"""A clone's indicator parameters: the read is classified, the write is not (yet).

2026-10-03, bot research (docs/bots-research-plan.md). Cymetica's skills and models cannot be equipped
with an API key (their routes want a browser session), so the one lever on a clone's algorithm that a key
reaches is the parameters of the indicators it already runs. Two MCP tools carry it:

* `get_bot_indicators` -- readOnlyHint: true, "Read one of YOUR clones' technical-indicator parameters".
  Classified read, so a change to a clone is verified by reading it back through the same guarded client.
* `update_bot_indicators` -- readOnlyHint: false, destructiveHint: true, no `paper` argument. It stays in
  no list, refused at SAFE and PROBE like any tool we have never classified. It is opened later, in its
  own step, with the paper-clone check `scripts/clone.py settings()` makes for the settings PATCH.

Split out of `test_guard_is_real.py` on purpose: that file is pinned by hash in `test_pipeline_abort.py`,
and a classification is registry data, not a new guard.
"""

from __future__ import annotations

from qa.marks import qa
from qa.safety import EndpointRegistry, SafetyTier


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_reading_a_clones_indicators_is_classified_read():
    assert EndpointRegistry.load().tool_class("get_bot_indicators") == "read"


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_overriding_a_clones_indicators_is_in_no_list():
    assert EndpointRegistry.load().tool_class("update_bot_indicators") == "unknown"

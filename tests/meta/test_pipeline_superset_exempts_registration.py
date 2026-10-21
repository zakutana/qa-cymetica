"""`higher_tier_is_a_superset_of_lower` asserts that authenticating never removes a tool.

One tool does, by its own description: `register_agent` -- "Register this agent and get its
API key ... no key needed" -- is listed to a caller with no identity and not to one that already
holds a key (read 2026-10-21: anonymous 149 tools with it, our key 157 without it). A tool that
exists to obtain a credential has nothing to offer a caller that has one, so its absence is the
design and not a reduction. The check had failed five times on it and, with nothing filed, was
about to be written up as a defect. The exemption is narrow and named, so any OTHER tool an
authenticated caller loses still fails.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


def _ladder():
    spec = importlib.util.spec_from_file_location(
        "trust_ladder_check", REPO / "tests" / "mcp" / "test_trust_ladder.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_tool_that_hands_out_the_credential_is_not_lost_by_holding_one():
    lost = _ladder().tools_lost_by_authenticating
    assert lost({"a", "register_agent"}, {"a", "b"}) == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_any_other_tool_an_authenticated_caller_loses_still_counts():
    lost = _ladder().tools_lost_by_authenticating
    assert lost({"a", "get_positions", "register_agent"}, {"a"}) == ["get_positions"]

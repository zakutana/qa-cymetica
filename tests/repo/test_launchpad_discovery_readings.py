"""Which chains the launchpad discovery check judges, and what its pass says (deep pass 2026-10-18).

C04 (3 of 3): the chains came only from the screener with include_external=false, which lists a chain
only while it has a public launch. A chain whose launches are all internal -- or 4663 once RUG is gone --
was never asked while the MCP feed went on listing its test launches. Read 2026-10-18 00:40 UTC: the
screener answers 0 rows either way, and /config names the chains as paused_chain_ids [4663, 5042,
5042002], so the check judged nothing at all.

C03 (3 of 3): settling a one-off leak to a pass is deliberate, but the pass printed "0 leaked" for a
chain whose first read leaked five.
"""

from qa.marks import SafetyTier, qa
from tests.rest.test_launchpad_discovery_tool_hides_what_rest_keeps_internal import chains_to_judge, clean_line


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_chains_judged_are_every_chain_any_source_names():
    config = {"chains": [], "paused_chain_ids": [4663, 5042, 5042002]}
    assert chains_to_judge([[], []], config) == [4663, 5042, 5042002], "the screener empty, /config names three"
    public_only = [[{"chain_id": 5042}], [{"chain_id": 5042}, {"chain_id": 8453}]]
    assert chains_to_judge(public_only, {"chains": [{"chain_id": 4663}], "paused_chain_ids": []}) == [4663, 5042, 8453], (
        "a chain with only internal launches is named by /config, not by the public screener")
    assert chains_to_judge([None, "junk"], {"chains": [4663, "x", {"id": 77}]}) == [77, 4663], (
        "a chain written as a number or as an object with id")
    assert chains_to_judge([None, None], None) == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_leak_gone_on_the_second_look_is_said_not_printed_as_zero():
    first = {4663: {"internal_by_rest": 5, "leaked": ["0xa", "0xb", "0xc", "0xd", "0xe"]},
             5042: {"internal_by_rest": 0, "leaked": []}}
    said = clean_line(first)
    assert "chain_id=4663: 5 internal, 5 listed on the first read and gone on the second look" in said, said
    assert "chain_id=5042: 0 internal, 0 leaked" in said, said
    assert "4663: 5 internal, 0 leaked" not in said

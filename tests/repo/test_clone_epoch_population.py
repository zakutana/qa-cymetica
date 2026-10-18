"""Which of our paper clones the "a clone trades only live 5-minute markets" check reads (C06, deep pass 2026-10-18).

The list was cut to the first 12 clones in API order and the rest went neither into `unread` nor into
the population, so "all 12 paper clones switch on only live 5-minute markets" passed while 41 paper
clones existed and an older one could still carry a dead market. Every clone is read now, as the
clone-summary check beside it reads every clone; only a list past a ceiling no account of ours comes
near is cut, and what lies past it is counted unread, never passed.
"""

from qa.marks import SafetyTier, qa
from tests.rest.test_a_clone_trades_only_live_epoch_markets import MAX_CLONES, to_read


def _clones(n):
    return [{"id": f"clone-{i:04d}"} for i in range(n)]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_clone_of_ours_is_read_not_the_first_twelve():
    read, beyond = to_read(_clones(41))
    assert len(read) == 41 and beyond == [], "a 13th clone and every one after it are judged"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_list_past_the_ceiling_counts_the_rest_unread():
    read, beyond = to_read(_clones(MAX_CLONES + 5))
    assert len(read) == MAX_CLONES and len(beyond) == 5
    assert MAX_CLONES >= 200, "a ceiling no account of ours comes near (41 paper clones on 2026-10-18)"
    assert to_read([{"id": "x"}, {"name": "no id"}, "junk"]) == ([{"id": "x"}], [])

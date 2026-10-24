"""The readings behind the "Airdrop Farmer lists no farm whose token trades" check.

Written before the check (2026-10-24), from GET /api/v1/airdrop-farm/farms as it answered that morning:
its gate opens with "No token live yet", and the list held Fables (FABLES on Robinhood Chain since
2026-10-20), Zircuit Staking (ZRC), and the task farms Travala.com (AVA), Sonic SVM (SONIC), INFINIT (IN)
and Rivalz Network (RIZ), every one of them priced and traded on CoinGecko or DexScreener that day.

Each reading is a way they could fix it (it must pass), a way the same defect could come back (it must
still fail), or a shape the check cannot decide (inconclusive, never a pass). The memory "a check encodes
the fix its author imagined" is why the fixes come first.
"""

from qa.marks import SafetyTier, qa
from tests.rest.test_airdrop_farmer_lists_no_farm_whose_token_trades import PINNED, judge

GATE = ["No token live yet", "At least $5M deposited in it", "Audited, no exploit on record"]

LIVE = [
    {"id": "fables", "name": "Fables", "url": "https://www.fables.fi/"},
    {"id": "zircuit-staking", "name": "Zircuit Staking", "url": "https://app.zircuit.com/liquidity-hub"},
    {"id": "task-travala", "name": "Travala.com", "url": "https://app.galxe.com/quest/Travala"},
    {"id": "task-sonicsvm", "name": "Sonic SVM", "url": "https://app.galxe.com/quest/SonicSVM"},
    {"id": "task-infinit", "name": "INFINIT", "url": "https://app.galxe.com/quest/INFINIT"},
    {"id": "task-rivalznetwork", "name": "Rivalz Network", "url": "https://app.galxe.com/quest/RivalzNetwork"},
    {"id": "infinifi", "name": "infiniFi", "url": "https://infinifi.xyz"},
    {"id": "axis", "name": "Axis", "url": "https://axis.to"},
]

# 24-hour volume in USD as read that morning (CoinGecko markets; DexScreener for FABLES).
MARKETS = {"fables": 254_681.0, "zircuit": 398_420.0, "travala": 38_005_862.0, "sonic-svm": 1_122_641.0,
           "infinit": 205_834_510.0, "rivalz": 11_348.0}


def _key_of(farm):
    for p in PINNED:
        if farm["id"] in p["ids"]:
            return p["key"]
    return None


def _verdict(farms, gate=GATE, markets=MARKETS):
    return judge(farms, gate, markets)["verdict"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_list_as_it_was_fails():
    out = judge(LIVE, GATE, MARKETS)
    assert out["verdict"] == "failed"
    assert {o["key"] for o in out["offenders"]} == {"fables", "zircuit", "travala", "sonic-svm", "infinit",
                                                     "rivalz"}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_dropping_every_tokened_farm_passes():
    farms = [f for f in LIVE if _key_of(f) is None]
    assert _verdict(farms) == "passed"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_renamed_farm_is_still_found_by_its_page():
    # a fix that only renames the row ("Travala quests") or re-keys it keeps the same quest page
    farms = [{"id": "galxe-travala-2", "name": "Travala quests", "url": "https://app.galxe.com/quest/Travala"}]
    assert _verdict(farms) == "failed"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_farm_found_by_its_name_alone_counts():
    farms = [{"id": "zrc", "name": "Zircuit", "url": None}]
    assert _verdict(farms) == "failed"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_one_tokened_farm_left_still_fails():
    farms = [f for f in LIVE if _key_of(f) in (None, "rivalz")]
    out = judge(farms, GATE, MARKETS)
    assert out["verdict"] == "failed" and [o["key"] for o in out["offenders"]] == ["rivalz"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_token_that_stopped_trading_is_not_held_against_them():
    markets = {**MARKETS, "rivalz": 0.0}
    farms = [f for f in LIVE if _key_of(f) in (None, "rivalz")]
    assert _verdict(farms, markets=markets) == "passed"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_unread_market_for_a_listed_farm_is_inconclusive():
    markets = {k: v for k, v in MARKETS.items() if k != "infinit"}
    farms = [f for f in LIVE if _key_of(f) in (None, "infinit")]
    assert _verdict(farms, markets=markets) == "inconclusive"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_unread_market_does_not_hide_a_failure_elsewhere():
    markets = {k: v for k, v in MARKETS.items() if k != "infinit"}
    assert _verdict(LIVE, markets=markets) == "failed"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_list_that_no_longer_promises_tokenless_farms_is_inconclusive():
    # if they drop the gate line, the promise the check holds them to is gone: not a pass, not a fail
    assert _verdict(LIVE, gate=["At least $5M deposited in it"]) == "inconclusive"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_their_reworded_gate_still_holds_them_to_it():
    # their fix of 2026-10-24 (ET-32684) rewrote the gate's first line; the promise is the same
    gate = ["Its token has no market yet: no CoinGecko coin of the same project with a price and no DEX pair "
            "of it trading (re-checked daily)", "No exploit on record"]
    clean = [f for f in LIVE if _key_of(f) is None]
    assert _verdict(clean, gate=gate) == "passed"
    assert _verdict(LIVE, gate=gate) == "failed"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_empty_list_is_inconclusive():
    assert _verdict([]) == "inconclusive"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_unrelated_name_is_not_matched():
    # "Sonic" alone is a different chain (Sonic, ex-Fantom); only Sonic SVM's own names and page count
    farms = [{"id": "sonic-lending", "name": "Sonic Lending", "url": "https://sonic.lend"}]
    assert _verdict(farms) == "passed"

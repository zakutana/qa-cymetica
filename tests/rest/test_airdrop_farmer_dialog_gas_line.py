"""The Airdrop Farmer's start dialog does not say the faucet pays the gas the user must claim (2026-11-11, report #341).

airdrop-farmer.js?v=20261110-2, the "Start your free testnet farms" lead: "Testnet gas comes from our faucet; nothing is sent
from your coins and no money is used." The GenLayer and Push Chain cards say "claim test GEN / test PC for your farm wallet",
and /api/v1/airdrop-farm/farms describes both as "testnet gas you claim to your own farm wallet".

**The rule.** While the farms API says the user claims testnet gas to their own farm wallet, the page's script may not say
the gas "comes from our faucet".

VERDICTS. failed: the script says it and the API says the user claims. passed: the script does not say it. inconclusive:
a read failed, or the API no longer says the user claims (nothing to compare).

NOT asserted: any other wording of the dialog.
SAFE: anonymous GETs.
"""

from __future__ import annotations

import re

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

CLAIM = "airdrop-farmer-testnet-dialog-says-gas-comes-from-our-faucet"
SAYS = re.compile(r"gas\s+comes\s+from\s+our\s+faucet", re.I)
CLAIMS = re.compile(r"gas you claim", re.I)


def _get(client, url: str, **kw):
    try:
        got = client.get(url, **kw)
    except Exception as exc:  # noqa: BLE001
        raise Inconclusive(f"{url} could not be read ({type(exc).__name__})")
    if got.status_code != 200:
        raise Inconclusive(f"{url} answered HTTP {got.status_code}")
    return got


@qa(component="rest.airdrop_farmer", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_the_start_dialog_does_not_say_the_faucet_pays_the_gas(rest_anon):
    """The page's scripts against what the farms API says about the gas."""
    farms = _get(rest_anon, "/api/v1/airdrop-farm/farms").text
    if not CLAIMS.search(farms):
        raise Inconclusive("the farms API no longer says the user claims testnet gas (nothing to compare)")
    page = _get(rest_anon, "/airdrop-farmer", headers={"Accept": "text/html"}).text
    srcs = sorted(set(re.findall(r'src="(/static/[^"]*airdrop[^"]*\.js[^"]*)"', page)))
    if not srcs:
        raise Inconclusive("the page loads no airdrop script")
    hits = {s: bool(SAYS.search(_get(rest_anon, s).text)) for s in srcs}
    bad = [s for s, h in hits.items() if h]
    conclude(Measurement(
        verdict="failed" if bad else "passed",
        reason=(f"the farms API says the gas is claimed by the user; {len(bad)} of {len(srcs)} page scripts still "
                f"say it 'comes from our faucet': {bad}"),
        left={"scripts_saying_faucet_pays": bad},
        right={"scripts_saying_faucet_pays": []},
        population={"scripts": srcs},
        sources={"page": "GET /airdrop-farmer", "api": "GET /api/v1/airdrop-farm/farms"},
        claim_id=CLAIM))

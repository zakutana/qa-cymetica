"""/traffic/mine tells an agent to use its API key; the endpoint it names refuses that key (2026-10-18).

The page https://cymetica.com/traffic/mine carries a "For AI agents -- copy & paste" bar
(`id="agentPasteBar"`, the prompt in its `data-agent-prompt` attribute). Read 2026-10-18 it said:

    Traffic for every public page you created (...): GET
    https://cymetica.com/api/v1/traffic/mine?days=14 with your api_key as X-API-Key.

With our own key in X-API-Key, that GET answered 401 application/json
`{"detail":"Sign in to see traffic for what you created."}`. The same key in the same header
answered 200 on `GET /api/v1/company/mine`, so the key is valid and recognised: it is this
endpoint that accepts only a signed-in browser session, while its own page sends agents to it
with the key.

**The rule.** When the page's agent prompt still names `X-API-Key` for `/api/v1/traffic/mine`
and a control call with the same key is accepted (`/api/v1/company/mine` answers 200), the
traffic endpoint must not answer 401. Either the endpoint accepts the key as the page says or
the page stops telling agents to use it; both make this pass (the second by the anchor going,
which reads INCONCLUSIVE, never passed).

401 is the specific claim, not 403: 401 says no credential was understood on a request that
carried one the rest of the surface accepts (the same family as
`test_documented_gets_accept_the_agent_key`). A 403 would be a decision about this caller.

VERDICTS. failed: prompt promises X-API-Key for the endpoint AND endpoint 401 AND control 200.
passed: the endpoint answers 200 with the key. inconclusive: the page unreadable or its prompt
no longer names X-API-Key for that endpoint (nothing promised); the control is not 200 (the key
itself is then the subject); any network/timeout error; any other status from the endpoint.

NOT asserted: what the response holds, the days parameter, or the page's signed-in view.
SAFE: three GETs; the key is sent by the client in the header and never printed or recorded.
"""

from __future__ import annotations

import re
from html import unescape

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

CLAIM = "traffic-mine-accepts-the-key-its-page-names"
PAGE = "/traffic/mine"
ENDPOINT = "/api/v1/traffic/mine"
CONTROL = "/api/v1/company/mine"
DAYS = 14

# Anchored on their own markup: the attribute of the agent paste bar, not on words found in the
# page's prose. Missing anchor => inconclusive, never passed.
PROMPT = re.compile(r'id="agentPasteBar"[^>]*?data-agent-prompt="([^"]*)"', re.S)
PROMPT_ALT = re.compile(r'data-agent-prompt="([^"]*)"[^>]*?id="agentPasteBar"', re.S)


def promised_sentence(html: str) -> str | None:
    """The sentence of the page's agent prompt that sends an agent to the endpoint with
    X-API-Key, or None when the prompt does not (or there is no prompt)."""
    match = PROMPT.search(html) or PROMPT_ALT.search(html)
    if not match:
        return None
    prompt = unescape(match.group(1))
    for sentence in re.split(r"(?<=[.!?])\s+", prompt):
        if ENDPOINT in sentence and re.search(r"x-api-key", sentence, re.I):
            return sentence.strip()
    return None


def verdict_for(promise: str | None, control_status: int, status: int) -> str:
    """failed / passed / inconclusive from the three facts."""
    if promise is None or control_status != 200:
        return "inconclusive"
    if status == 401:
        return "failed"
    if status == 200:
        return "passed"
    return "inconclusive"


@qa(component="rest.traffic", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_traffic_mine_accepts_the_key_its_page_names(rest_anon, rest_trusted):
    """The page's prompt, then the endpoint and a control call with the same key."""
    try:
        page = rest_anon.get(PAGE)
    except Exception as exc:  # noqa: BLE001 - a failed read is not an empty read (rule 8)
        raise Inconclusive(f"{PAGE} could not be read ({type(exc).__name__})")
    if page.status_code != 200:
        raise Inconclusive(f"{PAGE} answered HTTP {page.status_code}, so what it promises "
                           f"could not be read")
    promise = promised_sentence(page.text)
    if promise is None:
        raise Inconclusive(f"{PAGE} no longer has an agent prompt that names X-API-Key for "
                           f"{ENDPOINT}; nothing is promised, so nothing to judge")
    try:
        control = rest_trusted.get(CONTROL)
        got = rest_trusted.get(f"{ENDPOINT}?days={DAYS}")
    except Exception as exc:  # noqa: BLE001
        raise Inconclusive(f"the key could not be tried ({type(exc).__name__})")
    if control.status_code != 200:
        raise Inconclusive(f"the control {CONTROL} answered HTTP {control.status_code} to this "
                           f"key, so the key itself is the likelier subject and this check "
                           f"cannot separate the two")
    verdict = verdict_for(promise, control.status_code, got.status_code)
    if verdict == "inconclusive":
        raise Inconclusive(f"{ENDPOINT}?days={DAYS} answered HTTP {got.status_code} to a key "
                           f"{CONTROL} accepts; neither the 401 this check is about nor a 200")
    try:
        detail = got.json().get("detail") if got.status_code == 401 else None
    except Exception:  # noqa: BLE001
        detail = None
    conclude(Measurement(
        verdict=verdict,
        reason=(f"{PAGE} tells agents: \"{promise}\" but GET {ENDPOINT}?days={DAYS} with that "
                f"X-API-Key answers HTTP 401 {detail!r}, while the same key in the same header "
                f"answers HTTP 200 on {CONTROL}. The endpoint accepts only a signed-in browser "
                f"session although its own page sends agents to it with the key"
                if verdict == "failed" else
                f"GET {ENDPOINT}?days={DAYS} answers HTTP 200 to the X-API-Key its page names"),
        left={"traffic_mine_status": got.status_code},
        right={"traffic_mine_status": 200},
        population={"prompt_sentence": promise, "control": CONTROL,
                    "control_status": control.status_code, "detail": detail},
        sources={"page": f"{PAGE} (id=agentPasteBar, data-agent-prompt)",
                 "endpoint": f"{ENDPOINT}?days={DAYS}", "control": f"{CONTROL} (200)",
                 "credential": "X-API-Key, trusted tier (value never recorded)"},
        claim_id=CLAIM))

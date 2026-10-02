"""The site's NEXUS, asked one /degen prompt at a time -- on the paper account only.

    python scripts/chat.py prompts
    python scripts/chat.py ask --n 9 --confirm [--session-id <id>]

`POST /api/v1/chat/stream` is "the NEXUS that acts on your account": it places paper
orders, clones bots and runs backtests from one sentence, and nothing asks for a
confirmation (ET-28541). It is the only billed door -- a paper-mode account is never
charged. So this script puts every floor BEFORE the request, in the order a mistake
would cost:

  * `confirm` is checked before anything reaches the network;
  * the prompt is one the /degen page itself lists (read now, so what we send is what a
    visitor's "Send to NEXUS" button sends), and not one that publishes a card or a fund
    (a new event card defaults to PUBLIC and its fee comes out of the real USDC balance)
    or places an arena order (the CLOB has no paper book);
  * the account says paper twice, from them, now: `simulation_mode` on /account/me and
    `is_sim_mode` on /nexus/subscription. A failed read is not a yes.

The body is the documented one and nothing else: {message, current_page[, session_id]}
(components.yaml `chat.stream`, closed body). The reply is a Server-Sent Events stream;
it is read whole, because the whole body is what the evidence store keeps, and parsed
here. The diary is state/chat.jsonl: the intent before the POST, what came back after.
A timeout is outcome `unknown` -- the NEXUS may have acted -- and is settled by looking
at the account, never by sending the prompt again.
"""

from __future__ import annotations

import argparse
import hashlib
import html as htmllib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

PAGE = "/degen"
STREAM = "/api/v1/chat/stream"
ACCOUNT = "/api/v1/account/me"
SUBSCRIPTION = "/api/v1/nexus/subscription"

PROMPT = re.compile(r"<h3[^>]*>(.*?)</h3>\s*<pre data-prompt-text>(.*?)</pre>", re.S)

# What may not be sent, each with the reason that is said when it is refused.
REFUSED = (
    (re.compile(r"turn it into an event card|build_ai_index_basket|build_custom_event_card|"
                r"create_aib_fund", re.I),
     "it would create a public card or fund (a new card defaults to public and its fee comes "
     "out of the real USDC balance)"),
    (re.compile(r"arena", re.I),
     "it places an arena order: the CLOB has no paper book and the chat refuses it (ET-28541)"),
)


class ChatError(RuntimeError):
    """A prompt refused, by us before the network or by them."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def prompts(page_html: str) -> list[dict]:
    """The prompts the /degen page lists, numbered from 1: {n, title, text}."""
    out = []
    for n, (title, text) in enumerate(PROMPT.findall(page_html or ""), start=1):
        out.append({"n": n,
                    "title": htmllib.unescape(re.sub(r"<[^>]+>", "", title)).strip(),
                    "text": htmllib.unescape(text).strip()})
    return out


def refusal_for(text: str) -> str | None:
    for pattern, why in REFUSED:
        if pattern.search(text or ""):
            return why
    return None


def paper_floor(account: dict, subscription: dict) -> str | None:
    """None when both say paper; otherwise why this is not a paper account."""
    if (account or {}).get("simulation_mode") is not True:
        return f"{ACCOUNT} does not say simulation_mode true (it says {(account or {}).get('simulation_mode')!r})"
    if (subscription or {}).get("is_sim_mode") is not True:
        return f"{SUBSCRIPTION} does not say is_sim_mode true (it says {(subscription or {}).get('is_sim_mode')!r})"
    return None


def parse_sse(body: str) -> list[dict]:
    """`event: <name>\\ndata: <JSON>\\n\\n` blocks as {event, data}; data that is not
    JSON stays the text it was."""
    events = []
    for block in re.split(r"\r?\n\r?\n", body or ""):
        name, data = None, []
        for line in block.splitlines():
            if line.startswith("event:"):
                name = line[6:].strip()
            elif line.startswith("data:"):
                data.append(line[5:].lstrip())
        if name is None and not data:
            continue
        raw = "\n".join(data)
        try:
            parsed = json.loads(raw) if raw else None
        except ValueError:
            parsed = raw
        events.append({"event": name or "message", "data": parsed})
    return events


def summarise(events: list[dict]) -> dict:
    text, tools = [], []
    out = {"events": len(events), "done": False, "error": None, "usage_limit": False,
           "usage": None, "session_id": None, "embeds": 0, "actions": 0}
    for event in events:
        name, data = event["event"], event["data"]
        data = data if isinstance(data, dict) else {}
        if name == "text":
            text.append(str(data.get("content") or ""))
        elif name in ("tool_start", "tool_call", "tool_result"):
            tool = data.get("name") or data.get("tool")
            if tool and tool not in tools:
                tools.append(tool)
        elif name == "session":
            out["session_id"] = data.get("session_id")
        elif name == "embed":
            out["embeds"] += 1
        elif name == "action":
            out["actions"] += 1
        elif name == "usage_limit":
            out["usage_limit"] = True
        elif name == "error":
            out["error"] = data.get("message") or data.get("error") or "an error event with no text"
        elif name == "done":
            out["done"] = True
            out["usage"] = data.get("usage")
    out["text"] = "".join(text)
    out["tools"] = tools
    return out


# --- the diary -------------------------------------------------------------

def path() -> Path:
    from qa.state import state_dir

    return state_dir() / "chat.jsonl"


def load() -> list[dict]:
    target = path()
    if not target.is_file():
        return []
    rows = []
    for line in target.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    return rows


def _append(record: dict, *, new_id: bool = False) -> dict:
    from qa.state import file_lock

    target = path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(target):
        if new_id:
            used = [int(r["id"].split("-")[1]) for r in load()
                    if isinstance(r.get("id"), str) and r["id"].startswith("CHT-")]
            record["id"] = f"CHT-{max(used, default=0) + 1:04d}"
        with open(target, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def _capture(response) -> str | None:
    """The evidence id, or None -- never a raise (paper.py's reason)."""
    from qa.evidence import EvidenceStore
    from qa.safety import SafetyTier

    try:
        return EvidenceStore("script-chat").capture(
            response.request, response, SafetyTier.MUTATE) or None
    except Exception:  # noqa: BLE001
        return None


def _read(client, route: str) -> dict:
    response = client.get(route)
    if response.status_code != 200:
        raise ChatError(f"{route} answered HTTP {response.status_code}; a failed read is not "
                        f"a paper account")
    try:
        body = response.json()
    except ValueError:
        raise ChatError(f"{route} did not answer JSON; a failed read is not a paper account")
    return body if isinstance(body, dict) else {}


def ask(client, n: int, confirm: bool = False, session_id: str | None = None) -> dict:
    """One /degen prompt, sent to the NEXUS on the paper account. Every refusal is
    before the stream request; what comes back is summarised and written to the diary."""
    import httpx

    if not confirm:
        raise ChatError("pass confirm=True to actually send the prompt")
    page = client.get(PAGE)
    if page.status_code != 200:
        raise ChatError(f"{PAGE} answered HTTP {page.status_code}; there is no prompt to send")
    listed = prompts(page.text)
    chosen = next((p for p in listed if p["n"] == int(n)), None)
    if chosen is None:
        raise ChatError(f"{PAGE} lists {len(listed)} prompt(s); there is no prompt {n}")
    why = refusal_for(chosen["text"])
    if why:
        raise ChatError(f"prompt {n} ({chosen['title']}) is not sent: {why}")
    not_paper = paper_floor(_read(client, ACCOUNT), _read(client, SUBSCRIPTION))
    if not_paper:
        raise ChatError(f"not sent, the account is not shown to be paper: {not_paper}")

    body = {"message": chosen["text"], "current_page": PAGE}
    if session_id:
        body["session_id"] = session_id
    intent = _append({"type": "intent", "at": _now(), "n": chosen["n"], "title": chosen["title"],
                      "prompt_sha256": hashlib.sha256(chosen["text"].encode("utf-8")).hexdigest(),
                      "session_id": session_id}, new_id=True)
    try:
        response = client.post(STREAM, json=body, headers={"Accept": "text/event-stream"})
    except httpx.TimeoutException:
        _append({"type": "outcome", "id": intent["id"], "at": _now(), "outcome": "unknown",
                 "why": "the request timed out; the NEXUS may have acted"})
        raise ChatError(f"{intent['id']}: the request timed out -- the NEXUS may have acted; "
                        f"look at the account before asking again")
    evidence_id = _capture(response)
    if response.status_code != 200:
        _append({"type": "outcome", "id": intent["id"], "at": _now(), "outcome": "refused",
                 "http_status": response.status_code, "evidence_id": evidence_id,
                 "body": response.text[:300]})
        raise ChatError(f"{intent['id']}: refused, HTTP {response.status_code} {response.text[:160]!r}")
    summary = summarise(parse_sse(response.text))
    complete = summary["done"] and not summary["error"] and not summary["usage_limit"]
    _append({"type": "outcome", "id": intent["id"], "at": _now(),
             "outcome": "accepted" if complete else "incomplete", "http_status": 200,
             "evidence_id": evidence_id, "summary": dict(summary, text=summary["text"][:4000])})
    return dict(summary, id=intent["id"], evidence_id=evidence_id)


# --- the command -----------------------------------------------------------

def identity():
    from qa.config import identities

    trusted = identities()["trusted"]
    if not trusted.value:
        raise ChatError("no QA_TRUSTED_KEY in .env")
    return trusted


def _client(mutate: bool, timeout: float = 400.0):
    from qa.client import build_client
    from qa.safety import EndpointRegistry

    registry = EndpointRegistry.load()
    if mutate:
        registry.mutate_enabled = True
        registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    return build_client(identity(), registry, timeout=timeout)


def cmd_prompts(args) -> int:
    from qa.safety import CURRENT_TIER, SafetyTier

    client = _client(mutate=False)
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        page = client.get(PAGE)
    finally:
        CURRENT_TIER.reset(token)
        client.close()
    if page.status_code != 200:
        print(f"chat: {PAGE} unread, HTTP {page.status_code}")
        return 1
    for p in prompts(page.text):
        why = refusal_for(p["text"])
        print(f"{p['n']:>2} | {'REFUSED: ' + why if why else 'ok'} | {p['title']}")
    return 0


def cmd_ask(args) -> int:
    from qa.safety import CURRENT_TIER, SafetyTier

    client = _client(mutate=True)
    token = CURRENT_TIER.set(SafetyTier.MUTATE)
    try:
        said = ask(client, args.n, args.confirm, args.session_id)
    except ChatError as exc:
        print(f"chat: {exc}")
        return 1
    finally:
        CURRENT_TIER.reset(token)
        client.close()
    print(f"{said['id']}: done={said['done']} error={said['error']} usage_limit={said['usage_limit']} "
          f"tools={said['tools']} embeds={said['embeds']} actions={said['actions']} "
          f"session={said['session_id']} evidence={(said['evidence_id'] or '')[:12]}")
    print(said["text"][:1500])
    return 0 if said["done"] and not said["error"] else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("prompts", help="list the /degen prompts and which may be sent")
    one = sub.add_parser("ask", help="send one prompt to the NEXUS (paper account only)")
    one.add_argument("--n", type=int, required=True, help="the prompt's number on /degen")
    one.add_argument("--session-id", default=None, help="reuse a session for a follow-up")
    one.add_argument("--confirm", action="store_true")
    args = parser.parse_args(argv)
    return {"prompts": cmd_prompts, "ask": cmd_ask}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())

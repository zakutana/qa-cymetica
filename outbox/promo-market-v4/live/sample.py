"""The v4 mock's one model: a brief is a BUDGET in USDC or ET10 that the owner hands out in offers. Every answer the page
reads comes from here (memory: mock figures come from one model), for both windows at once.

The operator, 2026-11-05: no unique visitors, no clicks, no new users ("to nejd eulhidat"); a brief is posted for an
amount, offers come in, a post that stays up 3 days is paid; "a brief tam proste bude viset naporad dokud ho nezrusim
nebo dokud ho nekomu nepridelam"; and the protocol between two accounts: a brief for 50k ET10, a promoter offers and
says what they want, the owner edits it down to 10k, the promoter accepts, and 40k stays in the brief.

The flow of an offer:
  pending   the promoter applied with an X account and an ask
  countered the owner set a different amount (the promoter accepts or declines it)
  approved  agreed: the owner approved the ask, or the promoter accepted the owner's amount
  posted    the promoter registered the post; 3 days run
  earned    3 days up, waiting for the owner's Pay (derived from posted)
  paid      the owner paid
  declined  by the owner, by the promoter, or the brief was cancelled while it was pending
Money in play (countered, approved, posted, paid) is taken out of what the brief has left. A brief has no end date; it
leaves the market when nothing is left or the owner cancels it.

Invented, all of it: the brief, the promoters (handles end in _demo), their X numbers. The X read is a stand-in for
Cymetica's: it is only the filter that refuses a bought audience; it prices nothing.
"""
from __future__ import annotations

import json
import re
import threading
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOLD_DAYS = 3
CURRENCIES = ("USDC", "ET10")
ART = "/static/img/promo-art/gem.svg"
PREVIEW = "/uploads/bb-previews/gem-screener.jpg?v=1792881466"
IN_PLAY = ("countered", "approved", "posted", "paid")

ACCOUNTS = {
    "gemhunter_demo": dict(f=12400, v=6800, r=88, age="3.1 y"),
    "onchain_notes_demo": dict(f=4100, v=2350, r=93, age="1.4 y"),
    "alpha_threads_demo": dict(f=41000, v=15200, r=79, age="5.0 y"),
    "defi_digest_demo": dict(f=8900, v=4100, r=91, age="2.2 y"),
    "memecoin_mia_demo": dict(f=22000, v=9500, r=84, age="4.0 y"),
    "moonfarm_demo": dict(f=52000, v=310, r=21, age="0.8 y", out="52,000 followers but 310 views a post: the audience looks bought"),
}
FILTERED = [["views far under followers: a bought audience", 4], ["X account under 30 days old", 3], ["one X account behind two Cymetica accounts", 2]]
RULES = [
    {"title": "Real X accounts only", "text": "An offer is accepted only after Cymetica reads the promoter's public X: followers, the real views of their own last posts and the account's age. A bought audience (views far under followers), an account under 30 days and one X account behind two Cymetica accounts are refused."},
    {"title": "You set the amount", "text": "A promoter says what they want. The owner approves it or sets another amount; the promoter accepts it or not. What is not handed out stays in the brief."},
    {"title": "Their own post", "text": "The post must be written and posted from the X account that was checked."},
    {"title": "Paid after 3 days up", "text": "The amount is paid once the post has stayed up 3 days. A post taken down earlier is not paid."},
    {"title": "You pay, nothing automatic", "text": "The brief's owner pays with their own Pay press, from the owner's own wallet. The budget stays in the owner's wallet until then."},
]
_DROP = re.compile(r"visitor|click|new_user|traffic|tracked|per_user", re.I)


class Refused(Exception):
    def __init__(self, code: int, detail: str):
        super().__init__(detail)
        self.code, self.detail = code, detail


def _scrub(x):
    """Their fixture was read when there were visitors; nothing about a visitor, click or new user is in v4."""
    if isinstance(x, dict):
        return {k: _scrub(v) for k, v in x.items() if not _DROP.search(k)}
    if isinstance(x, list):
        return [_scrub(v) for v in x]
    return x


def engine(handle: str) -> dict:
    """What Cymetica's X read would answer: real reach and whether the account is eligible. It prices nothing."""
    h = handle.strip().lstrip("@").lower()
    a = ACCOUNTS.get(h)
    if a is None:
        k = zlib.crc32(h.encode())
        v = 600 + k % 9000
        a = dict(f=v * (2 + k % 5), v=v, r=70 + k % 26, age=f"{1 + k % 6}.{k % 10} y")
    out = dict(handle=h, followers=a["f"], views=a["v"], real=a["r"], age=a["age"])
    return dict(out, ok=False, why=a["out"]) if a.get("out") else dict(out, ok=True)


def _ago(td: timedelta) -> str:
    m = int(td.total_seconds() // 60)
    return f"{m} min ago" if m < 60 else f"{m // 60}h ago" if m < 1440 else f"{m // 1440}d ago"


def _num(v, what):
    try:
        v = float(v)
    except (TypeError, ValueError):
        v = 0
    if v <= 0:
        raise Refused(422, what)
    return int(v) if v == int(v) else round(v, 4)


class Market:
    def __init__(self):
        self.lock = threading.RLock()
        self.reset()

    # ---- state ------------------------------------------------------------------------------------------------
    def reset(self):
        with self.lock:
            self.brief, self.offers, self.offset, self.seq, self.checked = None, [], 0.0, 1, None

    def now(self) -> datetime:
        return datetime.now(timezone.utc) + timedelta(days=self.offset)

    def skip(self, days: float):
        with self.lock:
            self.offset += float(days)

    def _offer(self, handle, ask, state="pending", applied_ago=timedelta(minutes=5), mine=False):
        o = dict(id=self.seq, handle=handle, ask=ask, amount=None, state=state, applied_at=self.now() - applied_ago, post_url=None, posted_at=None, mine=mine)
        self.seq += 1
        self.offers.append(o)
        return o

    def left(self, skip=None) -> float:
        taken = sum((o["amount"] or 0) for o in self.offers if o["state"] in IN_PLAY and o is not skip)
        return round(self.brief["budget"] - taken, 4)

    # ---- the owner ----------------------------------------------------------------------------------------------
    def create_brief(self, body: dict) -> dict:
        with self.lock:
            if self.brief and self.brief["status"] != "cancelled":
                raise Refused(409, "The mock holds one brief at a time: Reset, or cancel this one first.")
            cur = str(body.get("currency") or "USDC").upper()
            if cur not in CURRENCIES:
                raise Refused(422, "The currency is USDC or ET10.")
            budget = _num(body.get("budget"), "Say how much the brief has to give.")
            site = bool(body.get("site_url"))
            name = body.get("site_name") if site else body.get("name") or "Gem Screener"
            path = None if site else body.get("path") or "/gem-screener"
            self.brief = dict(id=9001, name=name, path=path, url=body.get("site_url") if site else f"https://cymetica.com{path}", site=site,
                              art=ART, preview_url=PREVIEW, status="open", say_line=body.get("say_line") or "", currency=cur, budget=budget,
                              materials=body.get("materials") or [])
            self.offers, self.checked = [], None
            return self.brief_view()

    def cancel(self):
        """Closes what is not handed out; offers still waiting are declined, agreed ones go on."""
        with self.lock:
            self.brief["status"] = "cancelled"
            for o in self.offers:
                if o["state"] in ("pending", "countered"):
                    o["state"] = "declined"
            return self.brief_view()

    def decide(self, oid: int, decision: str, amount=None) -> dict:
        with self.lock:
            o = self._offer_by_id(oid)
            if decision == "decline":
                if o["state"] in ("pending", "countered"):
                    o["state"] = "declined"
                return self.view(o)
            if o["state"] != "pending":
                raise Refused(409, "That offer is not waiting for you.")
            amount = _num(o["ask"] if amount in (None, "") else amount, "Say how much to give.")
            if amount > self.left(skip=o):
                raise Refused(409, f"Only {self.left()} {self.brief['currency']} is left in the brief.")
            o["amount"] = amount
            o["state"] = "approved" if amount == o["ask"] else "countered"
            return self.view(o)

    def pay(self, oid: int) -> dict:
        with self.lock:
            o = self._offer_by_id(oid)
            if self.view(o)["state"] != "earned":
                raise Refused(409, "Not payable yet: the post must stay up 3 days." if o["state"] == "posted" else "Nothing to pay.")
            o["state"] = "paid"
            return self.view(o)

    # ---- the promoter -------------------------------------------------------------------------------------------
    def check(self, handle: str) -> dict:
        with self.lock:
            r = engine(handle)
            self.checked = r["handle"] if r["ok"] else None
            return r

    def take(self, ask) -> dict:
        with self.lock:
            if not self.brief or self.status() != "open":
                raise Refused(409, "This brief is not open any more.")
            if not self.checked:
                raise Refused(422, "Check your X account first.")
            ask = _num(ask, "Say how much you want for the post.")
            if ask > self.left():
                raise Refused(422, f"The brief has {self.left()} {self.brief['currency']} left: ask for that or less.")
            if any(o["mine"] and o["handle"] == self.checked and o["state"] in ("pending", "countered", "approved", "posted") for o in self.offers):
                raise Refused(409, "You have an offer on this brief already.")
            return self.view(self._offer(self.checked, ask, mine=True))

    def respond(self, oid: int, accept: bool) -> dict:
        with self.lock:
            o = self._offer_by_id(oid)
            if not o["mine"] or o["state"] != "countered":
                raise Refused(409, "There is nothing to answer.")
            o["state"] = "approved" if accept else "declined"
            return self.view(o)

    def register_post(self, url: str) -> dict:
        with self.lock:
            o = next((o for o in self.offers if o["mine"] and o["state"] == "approved"), None)
            if not o:
                raise Refused(409, "Nothing is agreed with you yet.")
            if not re.match(r"^https?://(x|twitter)\.com/\S+/status/\d+", url or ""):
                raise Refused(422, "Paste the link of your post on X: https://x.com/yourhandle/status/…")
            o.update(state="posted", post_url=url, posted_at=self.now())
            return self.view(o)

    # ---- reads --------------------------------------------------------------------------------------------------
    def _offer_by_id(self, oid):
        o = next((o for o in self.offers if o["id"] == int(oid)), None)
        if not o or not self.brief:
            raise Refused(404, "No such offer.")
        return o

    def view(self, o: dict) -> dict:
        a = engine(o["handle"])
        state, up = o["state"], 0
        if o["posted_at"] and state in ("posted", "paid"):
            up = max(0, (self.now() - o["posted_at"]).total_seconds() / 86400)
            if state == "posted" and up >= HOLD_DAYS:
                state = "earned"
        return dict(id=o["id"], handle=o["handle"], followers=a["followers"], views=a["views"], real=a["real"], age=a["age"], ok=a["ok"],
                    state=state, applied=_ago(self.now() - o["applied_at"]), ask=o["ask"], amount=o["amount"], post_url=o["post_url"],
                    days_up=min(HOLD_DAYS, int(up)), hold_days=HOLD_DAYS, currency=self.brief["currency"], mine=o["mine"])

    def status(self) -> str:
        if self.brief["status"] == "cancelled":
            return "cancelled"
        return "open" if self.left() > 0 else "full"

    def brief_view(self) -> dict | None:
        if not self.brief:
            return None
        paid = sum(o["amount"] for o in self.offers if o["state"] == "paid")
        return dict(self.brief, status=self.status(), left=self.left(), paid=paid, hold_days=HOLD_DAYS,
                    owner_funds={"state": "ok", "checked_at": self.now().isoformat()})

    def results(self) -> dict:
        offers = [self.view(o) for o in self.offers if o["state"] != "declined"]
        return {"brief": self.brief_view(), "waiting": sum(1 for o in offers if o["state"] == "pending"), "offers": offers,
                "filtered_out": FILTERED}

    # ---- seeds, for the pictures and for a first look ------------------------------------------------------------
    def seed(self, stage: str = "open"):
        with self.lock:
            self.reset()
            self.brief = dict(id=9001, name="Gem Screener", path="/gem-screener", url="https://cymetica.com/gem-screener", site=False, art=ART,
                              preview_url=PREVIEW, status="open", say_line="Find the gem before CT does.", currency="ET10", budget=50000,
                              materials=[{"id": 1, "kind": "image", "title": "Cover picture", "url": PREVIEW, "size": "the product page"},
                                         {"id": 2, "kind": "text", "title": "X post", "body": "Found my last 3 gems on the Gem Screener before CT did. Free, no wallet needed:"},
                                         {"id": 3, "kind": "link", "title": "Link to the page", "url": "https://cymetica.com/gem-screener/app"}])
            self._offer("defi_digest_demo", 12000, applied_ago=timedelta(hours=1))
            self._offer("memecoin_mia_demo", 8000, applied_ago=timedelta(hours=3))
            if stage == "open":
                return
            mine = self._offer("gemhunter_demo", 50000, applied_ago=timedelta(hours=5), mine=True)
            self.decide(mine["id"], "approve", 10000)           # the owner edits 50k down to 10k: 40k stays in the brief
            if stage == "countered":
                return
            mine["state"] = "approved"
            if stage == "approved":
                return
            mine.update(state="posted", post_url="https://x.com/gemhunter_demo/status/1004", posted_at=self.now() - timedelta(days=1, hours=2))
            if stage == "posted":
                return
            mine["posted_at"] = self.now() - timedelta(days=HOLD_DAYS, hours=1)
            if stage == "paid":
                mine["state"] = "paid"


MARKET = Market()


def stats() -> dict:
    """Their market reads these; a USDC total only counts briefs in USDC, because that is what the key says."""
    b = MARKET.brief_view()
    open_ = bool(b) and b["status"] == "open"
    return {"up_for_grabs_usdc": b["left"] if open_ and b["currency"] == "USDC" else 0, "open_briefs": 1 if open_ else 0,
            "left": {b["currency"]: b["left"]} if open_ else {}, "as_of": MARKET.now().isoformat()}


def _base() -> dict:
    base = _scrub(json.loads((HERE / "fixtures" / "mine.json").read_text(encoding="utf-8")))
    base["products"]["totals"] = {}
    return base


def mine(role: str) -> dict:
    m = _base()
    if role == "owner":
        r = MARKET.results() if MARKET.brief else None
        for p in m["products"]["products"]:
            p.pop("brief", None)
            if r and r["brief"]["path"] and p.get("path") == r["brief"]["path"]:
                p["brief"] = r
        m["products"]["live_briefs"] = 1 if r and r["brief"]["status"] != "cancelled" else 0
        return m
    m["products"]["products"], m["products"]["live_briefs"] = [], 0
    takes = [{"brief": MARKET.brief_view(), "offer": MARKET.view(o)} for o in MARKET.offers if o["mine"] and MARKET.brief]
    m["taken"] = {"takes": takes, "earnings": [], "payouts_enabled": True}
    return m


def answer(role: str, path: str):
    """path -> the answer for every read the page makes about the sample brief, or None to let their page answer it."""
    path = path.split("?")[0]
    if path == "/api/v1/promo/mine":
        return mine(role)
    if path == "/api/v1/promo/how-counted":
        return {"rules": RULES, "not_counted_reasons": {}, "payouts": "The brief's owner pays with their own Pay press, from the owner's own wallet. Nothing is paid automatically."}
    b = MARKET.brief_view()
    if path == "/api/v1/promo/briefs":
        return {"stats": stats(), "briefs": [b] if b and b["status"] == "open" else [], "sort": "left", "how_counted": RULES}
    if path == "/api/v1/promo/house":
        return {"market": stats(), "top": [], "mine": {"products": len(_base()["products"]["products"])}}
    m = re.fullmatch(r"/api/v1/promo/briefs/(\d+)(/results)?", path)
    if m:
        if not b or int(m.group(1)) != b["id"]:
            raise Refused(404, "No such brief.")
        if m.group(2):
            if role != "owner":
                raise Refused(403, "Not your brief.")
            return MARKET.results()
        mine_offer = next((MARKET.view(o) for o in MARKET.offers if o["mine"] and o["state"] != "declined"), None) if role == "promoter" else None
        return {"brief": b, "mine": None, "my_offer": mine_offer}
    return None


def fix_copy(page: dict, role: str = "owner") -> dict:
    """The sentences of their page that talk about visitors and links; v4 says what v4 does."""
    H = page.get("market_hero") or {}
    H["h1"] = "Post it. Get paid."
    if role == "promoter":
        page["viewer_name"] = "promoter_demo"
    put = lambda lst, i, text: lst.__setitem__(i, text) if isinstance(lst, list) and len(lst) > i else None
    H["sub"] = "Builders post briefs for the apps they made. Offer to post one on X, say what you want; when the owner agrees and your post has stayed up 3 days, you are paid."
    if isinstance(H.get("steps"), list) and len(H["steps"]) == 4:
        H["steps"] = [["Pick a brief", "any open one"], ["Make an offer", "say what you want for the post"], ["Post it on X", "from the account we checked"], ["Get paid", "after 3 days up"]]
    put(H.get("owners"), 1, "Set a budget, in USDC or ET10. It stays open until it is handed out or you cancel it.")
    put(H.get("owners"), 2, "Approve an offer or change its amount; pay when the post has stayed up 3 days.")
    put(H.get("not_yet"), 2, "Only posts on X are checked.")
    page["taken_empty"] = "You have not taken a brief yet. Open the Promo Market and make an offer."
    return page

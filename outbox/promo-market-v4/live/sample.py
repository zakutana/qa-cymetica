"""The v4 mock's one model: a brief is a BUDGET in USDC or ET10 that the owner hands out in offers. Every answer the page
reads comes from here (memory: mock figures come from one model), for both windows at once.

The operator, 2026-11-05: no unique visitors, no clicks, no new users ("to nejd eulhidat"); a brief is posted for an
amount, offers come in, a post that stays up 3 days is paid; "a brief tam proste bude viset naporad dokud ho nezrusim
nebo dokud ho nekomu nepridelam"; and the protocol between two accounts: a brief for 50k ET10, a promoter offers and
says what they want, the owner edits it down to 10k, the promoter accepts, and 40k stays in the brief.

The operator, 2026-11-10, both sides walked: the owner can add funds to a brief; a creator who opens the dashboard sees
Open briefs lit in the menu, takes one with their X account and uses the prepared materials; the owner is told
somebody wants the brief, checks the X account and names the amount, with a suggestion from the expected reach filled
in; "jak dam accept ty fund se locknou z meho kreditu a ceka se az to postne, kdyz to postne a bude to tam po 3 dnech
dam approve a prostredky se prevedou creatorovi".

The operator, 2026-11-10, after the first walk: the promoter sees no numbers about their own account when they take
a brief: "proste jen me se ukaze ze mam nabidku a ja si to checknu na sve strane jeho X a poslu mu zpetne kolik jsem
ochoten mu vyplatit a jemu se to tam pak nekde zobrazi kolik nabizim a muze dat accept nebo ne".

The flow of an offer:
  pending   the promoter took the brief with their X handle; the owner has not answered
  offered   the owner looked at the account and sent an amount: it is LOCKED from the owner's credit, waiting for
            the promoter's yes or no
  approved  the promoter accepted the amount; waiting for the post
  posted    the promoter registered the post; 3 days run
  earned    3 days up, waiting for the owner's Approve (derived from posted)
  paid      the owner approved: the locked amount moved to the promoter's credit
  declined  by the owner (also an offer or an accepted one taken back before a post), by the promoter (no to the
            offer, or a pass before posting), or the brief was cancelled before the promoter accepted
What is handed out (offered, approved, posted, paid) is taken out of what the brief has left. A brief has no end
date; it leaves the market when nothing is left or the owner cancels it, and comes back when the owner adds funds.

The owner's credit: free + locked. A brief's left is always covered by free credit (posting and adding funds are
refused above it), so an offer can always lock.

Invented, all of it: the brief, the promoters (handles end in _demo), their X numbers, the credit, the rate. The X
read is a stand-in for Cymetica's; the suggestion is expected reach (views a post x real audience) x a rate per 1,000
real views, and the rate is Cymetica's to set.
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
IN_PLAY = ("offered", "approved", "posted", "paid")      # handed out: off the brief's left
LOCKED = ("offered", "approved", "posted")               # locked from the owner's credit, not yet the promoter's
OPEN = ("pending", "offered", "approved", "posted")      # the promoter's request is still going
CREDIT = {"USDC": 500, "ET10": 200000}        # the owner's sample credit
RATE = {"USDC": 5, "ET10": 2000}              # per 1,000 real views: a sample, the real rate is Cymetica's
STEP = {"USDC": 1, "ET10": 500}               # a suggestion is a round number

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
    {"title": "Real X accounts only", "text": "A brief can be taken only with an X account Cymetica can read: followers, the real views of its own last posts and its age. A bought audience (views far under followers), an account under 30 days and one X account behind two Cymetica accounts are refused."},
    {"title": "The owner names the amount", "text": "The owner looks at the promoter's X, with a suggestion from the reach a post of theirs is expected to get, and sends an amount. The promoter accepts it or not. What is not handed out stays in the brief."},
    {"title": "Their own post", "text": "The post must be written and posted from the X account the brief was taken with."},
    {"title": "Locked with the offer", "text": "When the owner sends an amount, it is locked from the owner's Cymetica credit. If the promoter says no or passes before posting, it is unlocked."},
    {"title": "Paid after 3 days up", "text": "Once the post has stayed up 3 days the owner approves it and the locked amount moves to the promoter. A post taken down earlier is not paid."},
]
PAYOUTS = "The amount is locked from the owner's Cymetica credit when the owner sends the offer, and moves to the promoter when the owner approves the post after 3 days up."
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


def suggest(handle: str, currency: str, cap=None) -> dict:
    """The amount Cymetica would fill in for the owner: expected reach x the rate, a round number, never above what
    the brief has left. Reach is the real views of one post (views a post x real audience), with the spread a single
    post has around it."""
    a = engine(handle)
    reach = round(a["views"] * a["real"] / 100)
    step = STEP[currency]
    amount = max(step, round(reach / 1000 * RATE[currency] / step) * step)
    if cap is not None:
        amount = max(0, min(amount, cap))
    return dict(reach=reach, reach_lo=int(round(reach * 0.6, -2)), reach_hi=int(round(reach * 1.4, -2)), suggest=int(amount), rate=RATE[currency])


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
    ver = 0          # goes up with every write, so the other window knows to read again (serve.py bumps it)

    def reset(self):
        with self.lock:
            self.brief, self.offers, self.offset, self.seq = None, [], 0.0, 1
            self.credit, self.earned, self.news = dict(CREDIT), {}, []
            self.filtered = {}          # why Cymetica's X read turned accounts away from this brief, and how many

    def now(self) -> datetime:
        return datetime.now(timezone.utc) + timedelta(days=self.offset)

    def skip(self, days: float):
        with self.lock:
            was = {o["id"] for o in self.offers if self.view(o)["state"] == "earned"} if self.brief else set()
            self.offset += float(days)
            for o in self.offers if self.brief else ():
                if o["id"] not in was and self.view(o)["state"] == "earned":
                    self._tell("owner", f"@{o['handle']}'s post stayed up 3 days · approve it to pay", "Approve", o)
                    if o["mine"]:
                        self._tell("promoter", "Your post stayed up 3 days · waiting for the owner's approval", "See it", o)

    def _tell(self, to: str, text: str, go: str, o: dict):
        """What pops up in the other window: who it is for, one line, the word on its button, and the offer it is
        about (a newer line about the same offer replaces it)."""
        self.news.append(dict(n=len(self.news) + 1, to=to, text=text, go=go, offer=o["id"], brief=self.brief["id"] if self.brief else None))

    def _offer(self, handle, state="pending", applied_ago=timedelta(minutes=5), mine=False):
        o = dict(id=self.seq, handle=handle, amount=None, state=state, applied_at=self.now() - applied_ago, post_url=None, posted_at=None, mine=mine)
        self.seq += 1
        self.offers.append(o)
        return o

    def left(self) -> float:
        taken = sum((o["amount"] or 0) for o in self.offers if o["state"] in IN_PLAY)
        return round(self.brief["budget"] - taken, 4)

    def locked(self, cur: str) -> float:
        if not self.brief or self.brief["currency"] != cur:
            return 0
        return sum(o["amount"] for o in self.offers if o["state"] in LOCKED)

    def free(self, cur: str) -> float:
        return round(self.credit.get(cur, 0) - self.locked(cur), 4)

    def credit_view(self) -> dict:
        return {c: {"free": self.free(c), "locked": self.locked(c)} for c in CURRENCIES}

    # ---- the owner ----------------------------------------------------------------------------------------------
    def create_brief(self, body: dict) -> dict:
        with self.lock:
            if self.brief and self.brief["status"] != "cancelled":
                raise Refused(409, "The mock holds one brief at a time: Reset, or cancel this one first.")
            cur = str(body.get("currency") or "USDC").upper()
            if cur not in CURRENCIES:
                raise Refused(422, "The currency is USDC or ET10.")
            budget = _num(body.get("budget"), "Say how much the brief has to give.")
            self.offers = []          # the mock holds one brief: a cancelled one and what it still held go with it
            if budget > self.free(cur):
                raise Refused(409, f"Your free credit is {self.free(cur):,} {cur}: set that or less, or add credit first.")
            site = bool(body.get("site_url"))
            name = body.get("site_name") if site else body.get("name") or "Gem Screener"
            path = None if site else body.get("path") or "/gem-screener"
            self.brief = dict(id=9001, name=name, path=path, url=body.get("site_url") if site else f"https://cymetica.com{path}", site=site,
                              art=ART, preview_url=PREVIEW, status="open", say_line=body.get("say_line") or "", currency=cur, budget=budget,
                              materials=body.get("materials") or [])
            self.offers, self.filtered = [], {}
            return self.brief_view()

    def cancel(self):
        """Closes what is not handed out: requests still waiting and offers nobody accepted yet are closed (an offer's
        amount is unlocked); accepted ones go on, their amount stays locked."""
        with self.lock:
            self.brief["status"] = "cancelled"
            for o in self.offers:
                if o["state"] in ("pending", "offered"):
                    if o["mine"]:
                        self._tell("promoter", f"The owner ended the brief {self.brief['name']} before " + ("answering you" if o["state"] == "pending" else "you accepted"), "See it", o)
                    o["state"] = "declined"
            return self.brief_view()

    def add_budget(self, amount) -> dict:
        """Add funds: the brief has more to hand out, and a brief that was all handed out is open again."""
        with self.lock:
            cur = self.brief["currency"]
            if self.brief["status"] == "cancelled":
                raise Refused(409, "This brief is ended: post a new one.")
            amount = _num(amount, "Say how much to add.")
            if self.left() + amount > self.free(cur):
                raise Refused(409, f"Your free credit covers {max(0, self.free(cur) - self.left()):,} {cur} more: add that or less.")
            self.brief["budget"] = round(self.brief["budget"] + amount, 4)
            return self.brief_view()

    def decide(self, oid: int, decision: str, amount=None) -> dict:
        """The owner's answer. accept: names the amount and sends it to the promoter as an offer; it is locked from the
        owner's credit at once. decline: a waiting request, or an offer or an accepted one taken back while there is no
        post (the amount is unlocked)."""
        with self.lock:
            o = self._offer_by_id(oid)
            cur = self.brief["currency"]
            if decision == "decline":
                if o["state"] not in ("pending", "offered", "approved"):
                    raise Refused(409, "The post is up: it cannot be taken back now." if o["state"] == "posted" else "Nothing to decline.")
                if o["mine"]:
                    self._tell("promoter", {"pending": "The owner declined your request", "offered": f"The owner withdrew the offer of {o['amount'] or 0:,} {cur}",
                                            "approved": f"The owner took back the {o['amount'] or 0:,} {cur} locked for you"}[o["state"]], "See it", o)
                o["state"] = "declined"
                return self.view(o)
            if o["state"] != "pending":
                raise Refused(409, "That request is not waiting for you.")
            amount = _num(amount, "Say how much to offer.")
            if amount > self.left():
                raise Refused(409, f"Only {self.left():,} {cur} is left in the brief: offer that or less, or add funds.")
            if amount > self.free(cur):
                raise Refused(409, f"Your free credit is {self.free(cur):,} {cur}.")
            o.update(amount=amount, state="offered")
            if o["mine"]:
                self._tell("promoter", f"The owner offers you {amount:,} {cur} for {self.brief['name']} · accept it or not", "See the offer", o)
            return self.view(o)

    def pay(self, oid: int) -> dict:
        """The owner's Approve: the locked amount moves to the promoter's credit."""
        with self.lock:
            o = self._offer_by_id(oid)
            cur = self.brief["currency"]
            if self.view(o)["state"] != "earned":
                raise Refused(409, "Not yet: the post must stay up 3 days." if o["state"] == "posted" else "Nothing to approve.")
            o["state"] = "paid"
            self.credit[cur] = round(self.credit[cur] - o["amount"], 4)
            if o["mine"]:
                self.earned[cur] = round(self.earned.get(cur, 0) + o["amount"], 4)
                self._tell("promoter", f"Paid · {o['amount']:,} {cur} is in your Cymetica credit", "See it", o)
            return self.view(o)

    # ---- the promoter -------------------------------------------------------------------------------------------
    def take(self, handle: str) -> dict:
        """The promoter takes the brief with their X handle: a request to the owner, nothing more. The promoter is shown
        no numbers about the account and names no amount: the owner looks at the account and sends one. An account
        Cymetica's X read turns away cannot take it, and is told why."""
        with self.lock:
            if not self.brief or self.status() != "open":
                raise Refused(409, "This brief is not open any more.")
            if not re.fullmatch(r"@?\w{1,15}", (handle or "").strip()):
                raise Refused(422, "Write your X handle, like @yourname.")
            if any(o["mine"] and o["state"] in OPEN for o in self.offers):
                raise Refused(409, "You took this brief already.")
            r = engine(handle)
            if not r["ok"]:
                self.filtered[r["why"]] = self.filtered.get(r["why"], 0) + 1
                raise Refused(422, f"@{r['handle']} cannot take briefs: {r['why']}.")
            o = self._offer(r["handle"], mine=True, applied_ago=timedelta(0))
            self._tell("owner", f"@{o['handle']} wants your brief {self.brief['name']}", "Review", o)
            return self.view(o)

    def accept(self, oid: int) -> dict:
        """The promoter says yes to the owner's amount: now it waits for the post."""
        with self.lock:
            o = self._offer_by_id(oid)
            if not o["mine"] or o["state"] != "offered":
                raise Refused(409, "There is no offer to accept.")
            o["state"] = "approved"
            self._tell("owner", f"@{o['handle']} accepted {o['amount']:,} {self.brief['currency']} · waiting for their post", "Open", o)
            return self.view(o)

    def give_up(self, oid: int) -> dict:
        """The promoter's no: a waiting request is withdrawn, an offer is turned down, an accepted amount is passed on;
        what was locked is unlocked. Not after the post."""
        with self.lock:
            o = self._offer_by_id(oid)
            if not o["mine"] or o["state"] not in ("pending", "offered", "approved"):
                raise Refused(409, "There is nothing to pass on.")
            if o["state"] != "pending":
                did = "said no to" if o["state"] == "offered" else "passed on"
                self._tell("owner", f"@{o['handle']} {did} {o['amount']:,} {self.brief['currency']} · it is unlocked", "Open", o)
            o["state"] = "declined"
            return self.view(o)

    def register_post(self, url: str) -> dict:
        with self.lock:
            o = next((o for o in self.offers if o["mine"] and o["state"] == "approved"), None)
            if not o:
                raise Refused(409, "There is no accepted offer to post for yet.")
            if not re.match(r"^https?://(x|twitter)\.com/\S+/status/\d+", url or ""):
                raise Refused(422, "Paste the link of your post on X: https://x.com/yourhandle/status/…")
            o.update(state="posted", post_url=url, posted_at=self.now())
            self._tell("owner", f"@{o['handle']} posted · 3 days run", "Open", o)
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
        cur = self.brief["currency"]
        return dict(id=o["id"], handle=o["handle"], followers=a["followers"], views=a["views"], real=a["real"], age=a["age"], ok=a["ok"],
                    state=state, applied=_ago(self.now() - o["applied_at"]), amount=o["amount"], post_url=o["post_url"],
                    days_up=min(HOLD_DAYS, int(up)), hold_days=HOLD_DAYS, currency=cur, mine=o["mine"],
                    **suggest(o["handle"], cur, self.left() if o["state"] == "pending" else None))

    def status(self) -> str:
        if self.brief["status"] == "cancelled":
            return "cancelled"
        return "open" if self.left() > 0 else "full"

    def brief_view(self) -> dict | None:
        if not self.brief:
            return None
        cur = self.brief["currency"]
        paid = sum(o["amount"] for o in self.offers if o["state"] == "paid")
        return dict(self.brief, status=self.status(), left=self.left(), locked=self.locked(cur), paid=paid, hold_days=HOLD_DAYS, rate=RATE[cur],
                    credit=self.credit_view()[cur], owner_funds={"state": "ok", "checked_at": self.now().isoformat()})

    def results(self) -> dict:
        offers = [self.view(o) for o in self.offers if o["state"] != "declined"]
        return {"brief": self.brief_view(), "waiting": sum(1 for o in offers if o["state"] == "pending"), "offers": offers,
                "filtered_out": [[k, v] for k, v in self.filtered.items()]}

    # ---- seeds, for the pictures and for a first look ------------------------------------------------------------
    def seed(self, stage: str = "open"):
        with self.lock:
            self.reset()
            self.brief = dict(id=9001, name="Gem Screener", path="/gem-screener", url="https://cymetica.com/gem-screener", site=False, art=ART,
                              preview_url=PREVIEW, status="open", say_line="Find the gem before CT does.", currency="ET10", budget=50000,
                              materials=[{"id": 1, "kind": "image", "title": "Cover picture", "url": PREVIEW, "size": "the product page"},
                                         {"id": 2, "kind": "text", "title": "X post", "body": "Found my last 3 gems on the Gem Screener before CT did. Free, no wallet needed:"},
                                         {"id": 3, "kind": "link", "title": "Link to the page", "url": "https://cymetica.com/gem-screener/app"}])
            self.filtered = {k: v for k, v in FILTERED}
            self._offer("defi_digest_demo", applied_ago=timedelta(hours=1))
            self._offer("memecoin_mia_demo", applied_ago=timedelta(hours=3))
            try:
                self._seed(stage)
            finally:
                self.news = []          # a sample is a picture, not something that just happened

    def _seed(self, stage: str):
        if stage == "open":
            return
        if stage == "cancelled":
            self.cancel()
            return
        mine = self._offer("gemhunter_demo", applied_ago=timedelta(hours=5), mine=True)
        if stage == "requested":
            return
        self.decide(mine["id"], "accept", self.view(mine)["suggest"])          # the suggested 12,000 of 50,000: 38,000 stays in the brief
        if stage == "offered":
            return
        self.accept(mine["id"])
        if stage == "approved":
            return
        mine.update(state="posted", post_url="https://x.com/gemhunter_demo/status/1004", posted_at=self.now() - timedelta(days=1, hours=2))
        if stage == "posted":
            return
        mine["posted_at"] = self.now() - timedelta(days=HOLD_DAYS, hours=1)
        if stage == "paid":
            self.pay(mine["id"])


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
        m["credit"] = MARKET.credit_view()
        return m
    m["products"]["products"], m["products"]["live_briefs"] = [], 0
    takes = [{"brief": MARKET.brief_view(), "offer": MARKET.view(o)} for o in MARKET.offers if o["mine"] and MARKET.brief]
    m["taken"] = {"takes": takes, "earnings": [], "payouts_enabled": True}
    m["earned"] = dict(MARKET.earned)
    return m


def answer(role: str, path: str):
    """path -> the answer for every read the page makes about the sample brief, or None to let their page answer it."""
    path = path.split("?")[0]
    if path == "/api/v1/promo/mine":
        return mine(role)
    if path == "/api/v1/promo/how-counted":
        return {"rules": RULES, "not_counted_reasons": {}, "payouts": PAYOUTS}
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
    H["sub"] = "Builders post briefs for the apps they made. Take one with your X account; the owner sends you an amount, you accept, post the prepared materials, and after 3 days up you are paid."
    if isinstance(H.get("steps"), list) and len(H["steps"]) == 4:
        H["steps"] = [["Take a brief", "with your X account"], ["Accept the amount", "the owner sends it"], ["Post it on X", "the materials are ready"], ["Get paid", "after 3 days up"]]
    put(H.get("owners"), 1, "Set a budget, in USDC or ET10. It stays open until it is handed out or you cancel it; add funds any time.")
    put(H.get("owners"), 2, "A promoter takes it: check their X and send an amount. It is locked from your credit; they accept and post, and you approve after 3 days up.")
    put(H.get("not_yet"), 0, "It never pays on its own. A locked amount moves to the promoter only when the owner approves the post, after 3 days up.")
    put(H.get("not_yet"), 1, "Nothing is locked while a brief only hangs on the market: an amount is locked from the owner's Cymetica credit when the owner sends a promoter an offer.")
    put(H.get("not_yet"), 2, "Only posts on X are checked.")
    H["owners_rule"] = "Nothing is locked while the brief hangs on the market. An amount is locked from your Cymetica credit when you send a promoter an offer."
    page["taken_empty"] ="You have not taken a brief yet. Open briefs are waiting on the Promo Market."
    page["products_note"] = "A brief is covered by your Cymetica credit. An amount is locked when you send a promoter an offer, and moves to them when you approve their post after 3 days up."
    page["taken_pay"] = PAYOUTS
    return page

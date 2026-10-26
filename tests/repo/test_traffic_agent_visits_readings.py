"""The readings behind the "/traffic: AI-agent visits are the agents' requests" check.

Written before the check (2026-10-26), from https://cymetica.com/traffic as it was served that night. The page
defines its "AI-agent visits" tile as "Visits = every request an agent makes", and the "AI agents requests"
list under "What visitors do" as "Every request, landings AND the pages and API calls after them, grouped by
product area" -- the list ending in an "Everything else" row, so it is a whole and not a top ten. Over the same
14 days (since 2026-10-11T07:00Z, both endpoints) the tile read 115,359 and the list, set to "Selected range",
added up to 89,770: a quarter of the agents' requests is in one figure and not in the other. At 7 days the
two read 67,113 and 59,030, at 30 days 195,354 and 133,871.

Each reading below is a way the vendor could fix it (it must pass, whichever they pick: the numbers made to
agree, or the page saying what one of them leaves out), a way the same defect could be rebuilt (it must still
fail), or a shape the check cannot decide (inconclusive, never a pass). The memory "a check encodes the fix
its author imagined" is why the fixes come first.
"""

from qa.marks import SafetyTier, qa
from tests.rest.test_traffic_agent_visits_are_the_agents_requests import judge, page_facts

# The two paragraphs and the section ids as /traffic served them on 2026-10-26.
LIVE_HTML = """
<div class="tl-kpi"><div class="v" id="k-agents">-</div><div class="k">AI-agent visits</div></div>
<div class="tl-panel" id="tl-do">
  <h2>What visitors do <span class="tl-unit" id="tl-do-range">last 24 h</span></h2>
  <p class="tl-agents-lead">Every request, landings AND the pages and API calls after them, grouped by product area. These counts are larger than the landing counts above. Humans and AI agents are counted separately.</p>
  <div><h3>AI agents <span class="tl-unit">requests</span></h3><ul class="tl-paths" id="tl-do-agent"><li>Loading</li></ul></div>
</div>
<div class="tl-panel">
  <p class="tl-agents-lead">EventTrader is AI-native — agents are first-class users. These are the AI agents, crawlers and answer engines visiting the platform (they read <code>llms.txt</code> and <code>.well-known/mcp</code> and act on their owner's behalf). Counted separately, never mixed into the human numbers.</p>
  <p class="tl-agents-lead"><strong>Visits</strong> = every request an agent makes (one crawler reading 300 pages is 300 visits). <strong>Unique agents</strong> = distinct agents, one per agent family per hashed IP — the same basis as unique human visitors.</p>
</div>
"""

SINCE = "2026-10-11T07:00:00+00:00"
AREAS_LIVE = [("MCP (agent protocol)", 26637), ("Other pages", 18836), ("Coin dashboards", 18536),
              ("Screeners & analyzers", 7896), ("Feature board", 3148), ("Funds", 2737), ("Account", 2406),
              ("Build it Better", 1433), ("Exchange (CLOB)", 1158), ("Event cards", 1021),
              ("Everything else", 5962)]


def _public(total=115359, since=SINCE, generated="2026-10-25T23:17:23+00:00", days=14):
    return {"days": days, "since": since, "generated_at": generated,
            "ai_agents": {"total": total, "days": days}}


def _activity(areas=AREAS_LIVE, since=SINCE, generated="2026-10-25T23:17:27+00:00", days=14):
    return {"days": days, "since": since, "generated_at": generated,
            "requests": {"ai_agent": {"range": [{"area": a, "requests": n} for a, n in areas]}}}


def _verdict(html=LIVE_HTML, public=None, activity=None):
    return judge(page_facts(html), public or _public(), activity or _activity())[0]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_page_as_served_on_2026_10_26_fails():
    assert sum(n for _, n in AREAS_LIVE) == 89770
    facts = page_facts(LIVE_HTML)
    assert facts["sections"], "the tile and the list are both on the page"
    assert facts["promise"], "both paragraphs say every request"
    verdict, why, numbers = judge(facts, _public(), _activity())
    assert verdict == "failed"
    assert numbers["agent_visits"] == 115359 and numbers["agent_requests_by_area"] == 89770
    assert numbers["gap"] == 25589
    assert "115,359" in why and "89,770" in why


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_same_defect_rebuilt_in_other_shapes_still_fails():
    # The list larger than the tile is the same contradiction the other way round.
    assert _verdict(public=_public(total=60000)) == "failed"
    # The 7- and 30-day readings of the same night.
    assert _verdict(public=_public(total=67113, days=7),
                    activity=_activity(areas=[("Other pages", 53068), ("Everything else", 5962)], days=7)) == "failed"
    # A remainder row under another name is still a remainder.
    renamed = [(a if a != "Everything else" else "All other areas", n) for a, n in AREAS_LIVE]
    assert _verdict(activity=_activity(areas=renamed)) == "failed"
    # "All requests" says the same thing as "every request".
    reworded = LIVE_HTML.replace("Every request, landings", "All requests, landings")
    assert _verdict(html=reworded) == "failed"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_numbers_made_to_agree_pass():
    assert _verdict(public=_public(total=89770)) == "passed"
    # Within 2 %: the two endpoints are cached a few minutes apart.
    assert _verdict(public=_public(total=91500)) == "passed"
    assert _verdict(public=_public(total=88100)) == "passed"
    # Agreement says the list is whole, with or without a remainder row.
    whole = [(a, n) for a, n in AREAS_LIVE if a != "Everything else"] + [("Docs & discovery", 5962)]
    assert _verdict(activity=_activity(areas=whole), public=_public(total=89770)) == "passed"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_page_saying_what_one_figure_leaves_out_passes():
    # The tile's definition names what the list does not hold.
    narrowed = LIVE_HTML.replace(
        "every request an agent makes (one crawler",
        "every request an agent makes, including robots.txt, llms.txt and static files the list below "
        "excludes (one crawler")
    assert _verdict(html=narrowed) == "passed"
    # The list's own definition says it is not every request.
    only = LIVE_HTML.replace("Every request, landings AND the pages and API calls after them",
                             "Page views and API calls only, not robots.txt or llms.txt")
    assert _verdict(html=only) == "passed"
    # Or the tile stops claiming every request at all.
    pages = LIVE_HTML.replace("every request an agent makes", "distinct pages an agent opened")
    assert _verdict(html=pages) == "passed"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_page_as_fixed_on_2026_10_26_still_holds_its_promise():
    # Their fix renamed the tile and its definition, and said the two are the same number. With the list now
    # adding up it passes; the renamed definition is still read as the promise, so a gap that comes back fails
    # instead of passing as "no longer claimed".
    fixed = (LIVE_HTML
             .replace("<strong>Visits</strong> = every request an agent makes (one crawler reading 300 pages is 300 visits).",
                      "<strong>Requests</strong> = every request an agent makes (one crawler reading 300 pages is 300 "
                      "requests). It is the same number as the AI agents total under What visitors do.")
             .replace("Every request, landings AND the pages and API calls after them,",
                      "Every request, arrivals AND the pages opened after them (for AI agents also their API calls),"))
    facts = page_facts(fixed)
    assert facts["promise"] and "same number" in facts["tile_definition"]
    tail = [("Rarely requested paths", 21419)]
    assert _verdict(html=fixed, public=_public(total=105625),
                    activity=_activity(areas=[("MCP (agent protocol)", 26613), ("Other pages", 17527)] + tail
                                       + [("Coin dashboards", 16245), ("Everything else", 23821)])) == "passed"
    assert _verdict(html=fixed) == "failed"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_what_the_check_cannot_decide_is_inconclusive():
    # The sections gone: nothing on the page to judge.
    assert _verdict(html=LIVE_HTML.replace('id="k-agents"', 'id="k-x"')) is None
    assert _verdict(html=LIVE_HTML.replace('id="tl-do-agent"', 'id="tl-x"')) is None
    # The two endpoints over different ranges.
    assert _verdict(activity=_activity(since="2026-10-12T07:00:00+00:00")) is None
    assert _verdict(activity=_activity(days=7)) is None
    # Read more than 30 minutes apart.
    assert _verdict(activity=_activity(generated="2026-10-26T00:30:00+00:00")) is None
    # No remainder row and the two disagree: the list may be a top ten.
    top = [(a, n) for a, n in AREAS_LIVE if a != "Everything else"]
    assert _verdict(activity=_activity(areas=top)) is None
    # A field missing or not a number.
    assert judge(page_facts(LIVE_HTML), {"since": SINCE, "days": 14}, _activity())[0] is None
    assert _verdict(public=_public(total="115359")) is None
    assert judge(page_facts(LIVE_HTML), _public(), {"since": SINCE, "days": 14, "requests": {}})[0] is None
    # An empty list is not a zero.
    assert _verdict(activity=_activity(areas=[])) is None

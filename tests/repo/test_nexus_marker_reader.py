"""The reader behind tests/rest/test_nexus_answer_markers_are_true.py sees NEX-0142's three misfires.

Offline: the text is the last paragraph of NEX-0142 as their server served it on
2026-10-12 and again on 2026-10-13 (T-0071), the document a two-route slice of
openapi-public.json. A reader that cannot see these cannot fail the check on its own subject.
"""

from qa.marks import SafetyTier, qa
from tests.rest.test_nexus_answer_markers_are_true import broken, has_marker, misfires

SELF = qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")

CLONE = "692c35b3-29a7-4cda-8c73-7802cd28e4a8"
GONE = "[not available: this card id does not resolve on the public API — do not trade it]"


def _served(m):
    return f"[not served: this path does not take {m}; it takes DELETE]"


SERVED_TEXT = (
    f"`update_bot_settings` with instance_id `{CLONE} {GONE}` and `min_ai_confidence=0.60`\n\n"
    f"REST twin: `PATCH /api/v1/cloned-bots/{CLONE} {_served('PATCH')} {GONE} "
    f"{_served('PATCH')} {GONE}/settings` with the same body. Confirm with `GET "
    f"/api/v1/cloned-bots/{CLONE} {_served('GET')} {GONE} {_served('GET')} {GONE}/balance`")

DOCUMENT = {"paths": {
    "/api/v1/cloned-bots/{instance_id}": {"delete": {}},
    "/api/v1/cloned-bots/{instance_id}/settings": {"patch": {}},
    "/api/v1/cloned-bots/{instance_id}/balance": {"get": {}},
    "/api/v1/cloned-bots/my-clones": {"get": {}},
}}


@SELF
def test_the_three_misfires_of_nex_0142_are_seen():
    found = misfires(SERVED_TEXT, DOCUMENT, {CLONE})
    assert found["marked_instances"] == [CLONE]
    assert found["served_but_marked"] == [
        f"PATCH /api/v1/cloned-bots/{CLONE}/settings", f"GET /api/v1/cloned-bots/{CLONE}/balance"]
    assert found["split_paths"] == [
        f"/api/v1/cloned-bots/{CLONE}/settings", f"/api/v1/cloned-bots/{CLONE}/balance"]
    assert len(found["repeated"]) == 2
    assert broken(found)


@SELF
def test_only_our_own_bot_ids_are_judged_and_our_records_count_as_ours():
    """C10, deep pass 2026-10-18 (2 of 3): the contract is a marker on one of OUR bot instances, but an id
    the preceding words merely called a bot failed too -- an invented id the resolver rightly calls
    unresolvable among them. What that arm was for (seeing our clone without the live list, once
    released) is kept by counting every instance our own clone record holds."""
    from tests.rest.test_nexus_answer_markers_are_true import our_instances

    stranger = "5bd86126-90eb-4ad8-8e55-909397dab402"
    text = f"Clone bot {stranger} {GONE} and set it to paper."
    assert misfires(text, DOCUMENT, {CLONE})["marked_instances"] == [], "a bot id that is not ours"
    assert misfires(SERVED_TEXT, DOCUMENT, set())["marked_instances"] == []
    released = [{"type": "outcome", "outcome": "accepted", "clone_instance_id": CLONE.upper()},
                {"type": "outcome", "outcome": "rejected", "clone_instance_id": stranger}]
    ours = our_instances([], released)
    assert ours == {CLONE}, "an accepted clone of ours, released since, is still ours; a rejected one never was"
    assert misfires(SERVED_TEXT, DOCUMENT, ours)["marked_instances"] == [CLONE]
    assert our_instances([{"instance_id": "ABC"}, {"id": "def"}, "junk"], []) == {"abc", "def"}


@SELF
def test_a_true_marker_on_a_real_dead_end_is_not_a_misfire():
    # DELETE-only prefix, GET marked not served: the document agrees, nothing split or repeated.
    text = f"call GET /api/v1/cloned-bots/{CLONE} {_served('GET')} to read it"
    found = misfires(text, DOCUMENT, {CLONE})
    assert has_marker(text)
    assert not found["served_but_marked"] and not found["split_paths"] and not found["repeated"]


@SELF
def test_a_card_id_the_platform_does_not_resolve_is_left_alone():
    other = "5bd86126-90eb-4ad8-8e55-909397dab402"
    text = f"Allocate 40% to card {other} {GONE}."
    found = misfires(text, DOCUMENT, {CLONE})
    assert not broken(found)
    assert found["markers"] == 1


@SELF
def test_a_marker_just_outside_the_code_span_is_judged_too():
    """B02, deep pass 2026-10-25 (3 of 3): only a marker right behind the path, inside its backticks, was
    compared with the document. The same marker written after the closing backtick -- the whole path
    quoted, then the verdict -- was never judged, and a served route called not served passed."""
    text = (f"Set it with `PATCH /api/v1/cloned-bots/{CLONE}/settings` {_served('PATCH')} and read it back "
            f"with `GET /api/v1/cloned-bots/{CLONE}/balance` {_served('GET')}.")
    found = misfires(text, DOCUMENT, {CLONE})
    assert found["served_but_marked"] == [
        f"PATCH /api/v1/cloned-bots/{CLONE}/settings", f"GET /api/v1/cloned-bots/{CLONE}/balance"]
    assert found["split_paths"] == [] and found["repeated"] == [], "a marker after the span splits no path"
    assert broken(found)
    # A true marker outside the span is no misfire: the document serves only DELETE on the prefix.
    true = f"Do not `GET /api/v1/cloned-bots/{CLONE}` {_served('GET')}; it is DELETE only."
    assert not broken(misfires(true, DOCUMENT, {CLONE}))


@SELF
def test_a_clean_answer_has_nothing_to_judge():
    assert not has_marker("Keep all four flags off. PATCH /api/v1/cloned-bots/x/settings")

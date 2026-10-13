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
def test_an_instance_the_answer_itself_calls_one_is_seen_without_our_list():
    assert misfires(SERVED_TEXT, DOCUMENT, set())["marked_instances"] == [CLONE]


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
def test_a_clean_answer_has_nothing_to_judge():
    assert not has_marker("Keep all four flags off. PATCH /api/v1/cloned-bots/x/settings")

"""The readings under the Quant Lab search-rows check (2026-10-27, ET-32976), on the script text as
it was on 2026-10-27: the bot list draws a `.rk` rank cell first, the search results do not."""

from qa.marks import SafetyTier, qa
from tests.rest.test_quant_search_rows_fit_the_list_grid import first_track_px, row_first_cells

BOT_LIST = ("""return '<div class="qrow ' + sign(x.return_pct) + '">' +\n"""
            """  '<span class="rk">' + (i + 1) + '</span>' +\n"""
            """  '<div class="qn"><span class="st ' + x.status + '"><i></i>' + x.title + '</div>'""")
SEARCH = ("""return '<div class="qrow ' + (h.return_pct > 0 ? 'up' : h.return_pct < 0 ? 'down' : 'flat') + '">"""
          """<div class="qn"><span class="st ' + (win ? 'done' : 'paused') + '"><i></i>' + x.model + '</div>'""")
CSS = (".qrow { display: grid; grid-template-columns: 22px minmax(0, 1fr) 70px 80px 70px 70px 70px auto; gap: 10px; }\n"
       ".qrow .rk { text-align: right; }")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_bot_list_row_starts_with_the_rank_cell():
    assert row_first_cells(BOT_LIST) == ["rk"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_search_row_starts_with_the_name_cell():
    """A ternary with `<` and `>` inside the row's class must not be taken for the first child."""
    assert row_first_cells(SEARCH) == ["qn"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_script_that_draws_no_row_has_no_first_cells():
    assert row_first_cells("var a = 1;") == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_first_track_is_read_in_px_and_only_when_plain():
    assert first_track_px(CSS) == 22.0
    assert first_track_px(".qrow { grid-template-columns: minmax(0,1fr) 70px; }") is None
    assert first_track_px(".other { color: red }") is None

"""Tests for the table column geometry in ovi_wb_tabs.

Issue #4: the IsVisible column's position used to be written in three places --
a per-tab `tab_tots_isVisible_col` constant, a hardcoded column index in each
tab's `tab_cd_fixed_grid['isVisible']`, and the calculation in
`calc_col_pointers()` that overwrote both. The constants had already drifted:
the Code tab claimed column 44 while its table really ended at 54.

`calc_col_pointers()` is now the only place the position is decided.
"""

import re
from pathlib import Path

import pytest

from ovi.ovi_wb_tabs import NewTab

SOURCE = (Path(__file__).resolve().parent.parent
          / "src" / "ovi" / "ovi_wb_tabs.py").read_text(encoding="utf-8")

VAULT = {
    "Projects/Alpha.md": """
        ---
        author: Jane
        tags: [project]
        ---

        Alpha.

        ```dataview
        TABLE file.name
        ```
    """,
    "Projects/Beta.md": "---\nauthor: Sam\n---\n\nBeta.\n",
    "Archive/Alpha.md": "---\nauthor: Jane\n---\n\nDuplicate filename.\n",
    "Broken.md": "---\nauthor: [unclosed\n---\n\nBody.\n",
    "Plugin.md": "---\nauthor: Ann\nkindle-sync:\n  bookId: '1'\n---\n\nPlugin note.\n",
}


@pytest.fixture
def tab_defs(make_vault, stub_config):
    """Every tab_def from a real run, keyed by tab id."""
    from ovi.ovi_build import VaultScan
    from ovi.ovi_wb_tabs import NewWb

    vault = make_vault(VAULT)
    wb_obj = NewWb(VaultScan(stub_config(vault)))
    return wb_obj.wb_def["wb_tabs"]


def fake_tab(hdr, links=0, spacers=True, has_isvis=True):
    """The smallest object calc_col_pointers() will operate on."""
    tab = type("FakeTab", (), {})()
    tab.tab_id = "test"
    tab.tab_def = {
        "tab_table_links_cols": links,
        "tab_table_link_spcrs": spacers,
        "tab_cd_table_hdr": hdr,
        "tab_has_isVisible_col": has_isvis,
        "tab_tots_isVisible_col": 0,
        "tab_cd_fixed_grid": {"isVisible": [0, 0, "", 11, 0, "", "", False, False, "right", ""]},
    }
    return tab


def cell(col):
    """An 11-element cell definition at the given column."""
    return [col, 10, "", 11, 8, "", "", True, False, "center", ""]


# ---------------------------------------------------------------------------
# The invariant, on real tabs
# ---------------------------------------------------------------------------

def test_isvisible_is_the_last_table_column_on_every_tab(tab_defs):
    """Whatever the tab, IsVisible sits at the end of its table and the totals
    pointer agrees with the cell that renders it."""
    checked = 0
    for tab_id, tab_def in tab_defs.items():
        if not isinstance(tab_def, dict) or not tab_def.get("tab_has_isVisible_col"):
            continue

        checked += 1
        assert tab_def["tab_tots_isVisible_col"] == tab_def["tbl_end_col"], tab_id
        assert tab_def["tab_cd_fixed_grid"]["isVisible"][0] == tab_def["tbl_end_col"], tab_id

    assert checked >= 5, "expected several tabs to carry an IsVisible column"


def test_tabs_do_not_hardcode_the_isvisible_column():
    """Regression, issue #4: each subclass used to set tab_tots_isVisible_col to
    a literal. Those were overwritten, so they did nothing but drift -- except
    on one tab, where the value silently widened the table."""
    assignments = re.findall(r"tab_tots_isVisible_col'\]\s*=\s*(.+)", SOURCE)

    assert assignments == ["isvis_col"], f"unexpected assignments: {assignments}"


# ---------------------------------------------------------------------------
# The calculation itself
# ---------------------------------------------------------------------------

def test_a_column_is_added_when_isvisible_is_not_a_declared_column():
    """A tab with no link columns ends at its last fixed column, so IsVisible
    needs one more. This is what the old per-tab constant was really doing."""
    tab = fake_tab({"RowId": cell(10), "Key": cell(11), "Count": cell(12)})

    NewTab.calc_col_pointers(tab)

    assert tab.tab_def["tbl_end_col"] == 13          # 3 fixed columns from 10, plus one
    assert tab.tab_def["tab_tots_isVisible_col"] == 13


def test_link_columns_already_provide_the_room():
    """With link columns and their spacers the table is wider than the fixed
    columns, so IsVisible takes the last of them rather than adding another."""
    tab = fake_tab({"RowId": cell(10), "Key": cell(11), "Count": cell(12)}, links=2)

    NewTab.calc_col_pointers(tab)

    # 10-12 fixed, then two links and their two spacers, 13-16
    assert tab.tab_def["tbl_end_col"] == 16
    assert tab.tab_def["tab_tots_isVisible_col"] == 16


def test_a_declared_isvisible_column_is_left_where_it_is():
    """Some tabs list IsVisible among their table columns. It is already the
    last one, so nothing is added."""
    tab = fake_tab({"RowId": cell(10), "Key": cell(11), "isVisible": cell(12)})

    NewTab.calc_col_pointers(tab)

    assert tab.tab_def["tbl_end_col"] == 12
    assert tab.tab_def["tab_tots_isVisible_col"] == 12


def test_a_misplaced_declared_isvisible_column_raises():
    """The failure the old code could not detect: a tab declaring IsVisible
    somewhere other than the end of its table. The totals pointer and the
    rendered column would simply disagree, silently."""
    tab = fake_tab({"RowId": cell(10), "isVisible": cell(11), "Count": cell(12)})

    with pytest.raises(ValueError, match="IsVisible is declared at column 11"):
        NewTab.calc_col_pointers(tab)


def test_a_tab_without_isvisible_is_untouched():
    tab = fake_tab({"RowId": cell(10), "Key": cell(11)}, has_isvis=False)

    NewTab.calc_col_pointers(tab)

    assert tab.tab_def["tab_tots_isVisible_col"] == 0
    assert tab.tab_def["tbl_end_col"] == 11          # no extra column added

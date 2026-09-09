"""The Bases tab reads .base files and ```base fences.

Row layout, which the DefBase column order and the export_tab 'base' branch
both depend on:

    [RowId, Base, Folder, Kind, View, Type, Filters, View Filters,
     Columns, Sort, Group By, Limit, Formulas, Props]
"""

from pathlib import Path

from ovi.ovi_bases import (
    BASE_PATH, COLUMNS, FILTERS, FOLDER, FORMULAS, GROUP_BY, INVALID_YAML,
    KIND, KIND_EMBEDDED, KIND_FILE, LIMIT, NO_VIEWS, NOT_A_MAPPING, PROPS,
    SORT, VAULT_ROOT, VIEW, VIEW_FILTERS, VIEW_TYPE, BasesData,
)

DOCUMENTS_BASE = """
    filters:
      and:
        - file.inFolder("Documents")
        - file.ext == "md"
    formulas:
      age: now() - file.ctime
    properties:
      file.name:
        displayName: Name
      note.kind:
        displayName: Kind
    views:
      - type: table
        name: Documents
        order:
          - file.name
          - kind
        sort:
          - property: issued_on
            direction: DESC
        groupBy:
          property: kind
          direction: ASC
        limit: 50
      - type: cards
        name: Gallery
        filters:
          not:
            - kind == "receipt"
            - kind == "invoice"
        order:
          - file.name
"""


def harvest(vault, skip_dirs=()):
    """The rows, unwrapped from the two-level export_tab shape."""
    packed = BasesData(str(vault), skip_dirs).pack_rows()
    return [next(iter(inner.values())) for inner in packed.values()]


# ---------------------------------------------------------------------------
# What gets a row
# ---------------------------------------------------------------------------

def test_a_vault_without_bases_yields_nothing(make_vault):
    assert harvest(make_vault({"note.md": "Body.\n"})) == []


def test_one_row_per_view_with_the_base_repeated_on_each(make_vault):
    vault = make_vault({"Documents/Documents.base": DOCUMENTS_BASE})
    rows = harvest(vault)

    assert [r[VIEW] for r in rows] == ["Documents", "Gallery"]
    assert [r[VIEW_TYPE] for r in rows] == ["table", "cards"]
    assert {Path(r[BASE_PATH]).name for r in rows} == {"Documents.base"}
    assert {r[KIND] for r in rows} == {KIND_FILE}
    assert {r[FOLDER] for r in rows} == {"Documents"}
    assert {r[FILTERS] for r in rows} == {'file.inFolder("Documents") AND file.ext == "md"'}
    assert {r[FORMULAS] for r in rows} == {"age"}
    assert {r[PROPS] for r in rows} == {2}


def test_view_level_settings_are_rendered_per_view(make_vault):
    table, cards = harvest(make_vault({"Documents/Documents.base": DOCUMENTS_BASE}))

    assert table[COLUMNS] == "file.name | kind"
    assert table[SORT] == "issued_on DESC"
    assert table[GROUP_BY] == "kind ASC"
    assert table[LIMIT] == 50
    assert table[VIEW_FILTERS] == ""

    assert cards[VIEW_FILTERS] == 'NOT (kind == "receipt" OR kind == "invoice")'
    assert cards[LIMIT] == ""


def test_a_base_with_no_views_still_gets_one_row(make_vault):
    rows = harvest(make_vault({"Empty.base": 'filters: file.ext == "md"\n'}))

    assert len(rows) == 1
    assert rows[0][VIEW_TYPE] == NO_VIEWS
    assert rows[0][FILTERS] == 'file.ext == "md"'
    assert rows[0][FOLDER] == VAULT_ROOT


def test_an_unparseable_base_is_reported_not_raised(make_vault):
    rows = harvest(make_vault({"Bad.base": "views: [unclosed\n"}))

    assert len(rows) == 1
    assert rows[0][VIEW_TYPE] == INVALID_YAML
    assert rows[0][FILTERS]  # the parser's first line, so the sheet says why


def test_a_base_that_is_not_a_mapping_is_marked(make_vault):
    rows = harvest(make_vault({"List.base": "- just\n- a list\n"}))

    assert [r[VIEW_TYPE] for r in rows] == [NOT_A_MAPPING]


def test_trash_obsidian_and_skipped_folders_are_left_out(make_vault):
    vault = make_vault({
        "Keep/Keep.base": "views:\n  - type: table\n    name: Keep\n",
        ".trash/Old.base": "views:\n  - type: table\n    name: Old\n",
        ".obsidian/plugins/x/Plug.base": "views:\n  - type: table\n    name: Plug\n",
        "Archive/Archived.base": "views:\n  - type: table\n    name: Archived\n",
    })

    rows = harvest(vault, skip_dirs=[str(vault / "Archive")])

    assert [r[VIEW] for r in rows] == ["Keep"]


# ---------------------------------------------------------------------------
# Filter rendering
# ---------------------------------------------------------------------------

def test_nested_filters_read_as_one_expression():
    tree = {"or": [
        'file.hasTag("tag")',
        {"and": ['file.hasTag("book")', 'file.hasLink("Textbook")']},
        {"not": ['file.hasTag("book")', 'file.inFolder("Required Reading")']},
    ]}

    assert BasesData.render_filter(tree) == (
        'file.hasTag("tag") OR (file.hasTag("book") AND file.hasLink("Textbook")) '
        'OR NOT (file.hasTag("book") OR file.inFolder("Required Reading"))')


def test_a_single_filter_needs_no_operator():
    assert BasesData.render_filter('file.ext == "md"') == 'file.ext == "md"'
    assert BasesData.render_filter({"and": ['file.ext == "md"']}) == 'file.ext == "md"'
    assert BasesData.render_filter(None) == ""


# ---------------------------------------------------------------------------
# Embedded bases, through the vault walk
# ---------------------------------------------------------------------------

def test_an_embedded_base_is_harvested_from_its_note(scan):
    result = scan({"Reading.md": """
        # Reading list

        ```base
        filters: file.hasTag("book")
        views:
          - type: table
            name: Books
        ```
    """})

    rows = [next(iter(inner.values())) for inner in result.obs_bases.values()]

    assert len(rows) == 1
    assert rows[0][KIND] == KIND_EMBEDDED
    assert Path(rows[0][BASE_PATH]).name == "Reading.md"
    assert rows[0][VIEW] == "Books"
    assert rows[0][FILTERS] == 'file.hasTag("book")'

    # It stays on the Code tab too: the fence is still a code block.
    assert "BASE" in result.obs_codes[rows[0][BASE_PATH]]


def test_a_base_in_a_template_is_not_harvested(scan, tmp_path):
    result = scan(
        {"Templates/T.md": "```base\nviews:\n  - type: table\n    name: T\n```\n"},
        dir_templates=str(tmp_path / "TestVault" / "Templates"))

    assert result.obs_bases == {}


# ---------------------------------------------------------------------------
# Where the tab sits
# ---------------------------------------------------------------------------

def test_the_tab_follows_tags_and_is_green():
    from ovi.ovi_colors import Colors
    from ovi.ovi_setup import DEFAULT_TAB_SEQ, merge_tab_seq

    assert DEFAULT_TAB_SEQ.index("base") == DEFAULT_TAB_SEQ.index("tags") + 1

    # A CONFIG.yaml written before the tab existed picks it up in the same place.
    merged = merge_tab_seq(["pros", "vals", "tags", "file", "summ"])
    assert merged.index("base") == merged.index("tags") + 1

    assert Colors().init_tab_clrs()["base"][0] == "grn"

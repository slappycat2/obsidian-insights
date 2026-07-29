"""End-to-end test: markdown in, .xlsx out.

Covers what the parsing tests cannot -- the YAML batch-file handoff between
stages, the tab definitions, and the openpyxl export. No GUI and no Obsidian
installation are involved.
"""

import openpyxl
import pytest

VAULT = {
    "Projects/Alpha.md": """
        ---
        author: Jane
        status: active
        tags:
          - project
          - alpha
        ---

        Alpha body. rating:: 5

        ```dataview
        TABLE file.name
        ```
    """,
    "Projects/Beta.md": """
        ---
        author: Sam
        status: done
        ---

        Beta body with an inline #beta tag.
    """,
    "Archive/Alpha.md": """
        ---
        author: Jane
        ---

        A duplicate filename, in a different folder.
    """,
    "Broken.md": """
        ---
        author: [unclosed
        ---

        Body.
    """,
}


@pytest.fixture
def workbook_path(make_vault, stub_config):
    """Run all four stages over a small vault and return the .xlsx path."""
    from vault_check.v_chk_build import VaultHealthCheck
    from vault_check.v_chk_wb_tabs import NewWb
    from vault_check.v_chk_xl import ExcelExporter

    vault = make_vault(VAULT)

    health_check = VaultHealthCheck(stub_config(vault))
    vault_wb = NewWb(health_check)

    exporter = ExcelExporter(vault_wb.wbd_obj)
    exporter.export()

    return exporter.sys_pn_wbs


def test_workbook_is_created(workbook_path):
    from pathlib import Path

    assert Path(workbook_path).is_file()
    assert Path(workbook_path).stat().st_size > 0


def test_workbook_has_the_expected_tabs(workbook_path):
    wb = openpyxl.load_workbook(workbook_path)

    # Tabs whose data source is empty are deliberately dropped, so assert on a
    # subset that this vault definitely populates.
    for expected in ("Summary", "Properties", "Values", "Tags", "Files"):
        assert expected in wb.sheetnames


def test_properties_reach_the_workbook(workbook_path):
    wb = openpyxl.load_workbook(workbook_path)
    text = {
        str(cell.value)
        for row in wb["Values"].iter_rows()
        for cell in row
        if cell.value is not None
    }

    assert "author" in text
    assert "Jane" in text


def test_duplicate_filenames_reach_the_workbook(workbook_path):
    wb = openpyxl.load_workbook(workbook_path)
    assert "Duplicates" in wb.sheetnames

    text = " ".join(
        str(cell.value)
        for row in wb["Duplicates"].iter_rows()
        for cell in row
        if cell.value is not None
    )
    assert "Alpha.md" in text


def test_broken_yaml_reaches_the_workbook(workbook_path):
    wb = openpyxl.load_workbook(workbook_path)
    assert "Xyml" in wb.sheetnames

    text = " ".join(
        str(cell.value)
        for row in wb["Xyml"].iter_rows()
        for cell in row
        if cell.value is not None
    )
    assert "Broken.md" in text


def test_tables_are_defined_on_data_tabs(workbook_path):
    """The workbook's value depends on real Excel tables (filters and the
    AGGREGATE-based totals), not just cell values."""
    wb = openpyxl.load_workbook(workbook_path)

    assert "tbl_pros" in wb["Properties"].tables
    assert "tbl_vals" in wb["Values"].tables

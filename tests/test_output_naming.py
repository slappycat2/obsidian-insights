"""Generated filenames name the vault they came from.

Batch files and workbooks used to be numbered globally -- v_chk_0000.yaml,
v_chk_0001.yaml -- so a directory of them said nothing about which vault
produced which, and scanning a second vault simply continued the first one's
numbering. The vault name now sits between the sys_id and the sequence number,
and the sequence is per-vault.
"""

from pathlib import Path

import pytest

from vault_check.v_chk_wb_setup import WbDataDef, safe_name_part


@pytest.mark.parametrize("raw, expected", [
    ("MyVault", "MyVault"),
    ("My Vault", "My_Vault"),
    ("My Vault (2024)", "My_Vault_2024"),
    ("notes/archive", "notes_archive"),
    # glob metacharacters would otherwise be read as a pattern by get_last_bat()
    ("vault[1]", "vault_1"),
    ("what?", "what"),
    ("...", ""),
    ("", ""),
])
def test_safe_name_part(raw, expected):
    assert safe_name_part(raw) == expected


def test_batch_and_workbook_names_carry_the_vault_name(make_vault, stub_config):
    vault = make_vault({"note.md": "Body.\n"}, name="NamedVault")

    wbd = WbDataDef(stub_config(vault))
    wbd.get_next_bat()

    batch_stem = Path(wbd.sys_pn_batch).stem
    assert batch_stem.startswith("v_chk_test_NamedVault_")
    assert Path(wbd.sys_pn_wbs).stem == batch_stem
    assert Path(wbd.sys_pn_wbs).suffix == ".xlsx"


def test_a_sanitised_vault_name_is_used(make_vault, stub_config):
    vault = make_vault({"note.md": "Body.\n"}, name="Vault Two")

    wbd = WbDataDef(stub_config(vault))
    wbd.get_next_bat()

    assert Path(wbd.sys_pn_batch).stem.startswith("v_chk_test_Vault_Two_")


def test_numbering_is_per_vault(make_vault, stub_config):
    """Two vaults each start at 0000 rather than sharing one sequence."""
    one = make_vault({"note.md": "Body.\n"}, name="SeqVaultOne")
    two = make_vault({"note.md": "Body.\n"}, name="SeqVaultTwo")

    wbd_one = WbDataDef(stub_config(one))
    wbd_one.get_next_bat()
    Path(wbd_one.sys_pn_batch).write_text("", encoding="utf-8")

    wbd_two = WbDataDef(stub_config(two))
    wbd_two.get_next_bat()

    assert Path(wbd_one.sys_pn_batch).stem.endswith("_0000")
    assert Path(wbd_two.sys_pn_batch).stem.endswith("_0000")


def test_the_vault_folder_wins_over_the_display_label(make_vault, stub_config):
    """sys_cfg['vault_name'] is the setup screen's dropdown label -- 'work -
    (D:/Vaults)' -- so the folder name is what goes into the filename."""
    vault = make_vault({"note.md": "Body.\n"}, name="LabelVault")

    wbd = WbDataDef(stub_config(vault, vault_name="LabelVault - (D:/Vaults)"))
    wbd.get_next_bat()

    assert Path(wbd.sys_pn_batch).stem.startswith("v_chk_test_LabelVault_")


def test_a_nameless_vault_falls_back_to_the_bare_sys_id(make_vault, stub_config):
    make_vault({"note.md": "Body.\n"})

    wbd = WbDataDef(stub_config(Path(""), vault_name="", dir_vault=""))
    wbd.get_next_bat()

    assert Path(wbd.sys_pn_batch).stem.startswith("v_chk_test_0")

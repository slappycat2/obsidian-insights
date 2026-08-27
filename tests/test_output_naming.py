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


def _touch(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("", encoding="utf-8")


def test_a_surviving_workbook_reserves_its_number(make_vault, stub_config):
    """Regression: --init could not delete a workbook Excel had open, so its
    batch file went and its .xlsx stayed. Numbering read only the batch
    directory, handed the next run _0000 again, and save_workbook() met a locked
    file with a modal retry dialog."""
    vault = make_vault({"note.md": "Body.\n"}, name="LockedVault")
    cfg = stub_config(vault)

    wbd = WbDataDef(cfg)
    _touch(f"{cfg.sys_cfg['sys_dir_wbs']}/{wbd.file_stub}_0000.xlsx")
    wbd.get_next_bat()

    assert Path(wbd.sys_pn_batch).stem.endswith("_0001")
    assert Path(wbd.sys_pn_wbs).name.endswith("_0001.xlsx")


def test_numbering_does_not_refill_gaps(make_vault, stub_config):
    """A missing number in the middle is not reused -- the .xlsx that shares it
    may still be there."""
    vault = make_vault({"note.md": "Body.\n"}, name="GapVault")
    cfg = stub_config(vault)

    wbd = WbDataDef(cfg)
    _touch(f"{cfg.sys_cfg['sys_dir_bat']}/{wbd.file_stub}_0000.yaml")
    _touch(f"{cfg.sys_cfg['sys_dir_bat']}/{wbd.file_stub}_0002.yaml")
    wbd.get_next_bat()

    assert Path(wbd.sys_pn_batch).stem.endswith("_0003")


def test_excel_lock_files_do_not_reserve_a_number(make_vault, stub_config):
    """'~$name.xlsx' is Excel's owner file, not a workbook v_chk produced."""
    vault = make_vault({"note.md": "Body.\n"}, name="OwnerFileVault")
    cfg = stub_config(vault)

    wbd = WbDataDef(cfg)
    _touch(f"{cfg.sys_cfg['sys_dir_wbs']}/~${wbd.file_stub}_0000.xlsx")
    wbd.get_next_bat()

    assert Path(wbd.sys_pn_batch).stem.endswith("_0000")


def test_another_vaults_files_do_not_advance_the_bare_sys_id(make_vault, stub_config):
    """A vault whose name sanitises away uses the bare sys_id as its stub, which
    is a prefix of every other stub -- so seq_nums() anchors the match."""
    make_vault({"note.md": "Body.\n"})
    cfg = stub_config(Path(""), vault_name="", dir_vault="")

    wbd = WbDataDef(cfg)
    _touch(f"{cfg.sys_cfg['sys_dir_bat']}/{wbd.file_stub}_PrefixVault_0007.yaml")
    wbd.get_next_bat()

    assert Path(wbd.sys_pn_batch).stem == f"{wbd.file_stub}_0000"


def test_get_last_bat_picks_the_highest_number(make_vault, stub_config):
    """'Last' is the highest number, not the newest ctime, so it cannot disagree
    with the number get_next_bat() would hand out."""
    vault = make_vault({"note.md": "Body.\n"}, name="LastBatVault")
    cfg = stub_config(vault)

    wbd = WbDataDef(cfg)
    _touch(f"{cfg.sys_cfg['sys_dir_bat']}/{wbd.file_stub}_0001.yaml")
    _touch(f"{cfg.sys_cfg['sys_dir_bat']}/{wbd.file_stub}_0000.yaml")
    wbd.get_last_bat()

    assert Path(wbd.sys_pn_batch).stem.endswith("_0001")
    assert Path(wbd.sys_pn_wbs).name.endswith("_0001.xlsx")

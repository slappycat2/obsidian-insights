"""Command-line setting overrides and the headless bootstrap, in process.

The Obsidian plugin cannot show the Tk setup screen, so it passes its
settings page as overrides and relies on a first --headless run creating
CONFIG.yaml from the defaults. These tests build the real SysConfig against
a temporary config path with no obsidian.json, which is the state of a
machine where Obsidian has never been opened and ovi has never been set up.
"""

import logging

import pytest
import yaml

from ovi import ovi_obs_app as obs_app
from ovi import ovi_paths as paths
from ovi.ovi_setup import ConfigIncompleteError, SysConfig


@pytest.fixture
def config_file(tmp_path, monkeypatch):
    """No obsidian.json anywhere, and CONFIG.yaml redirected into tmp_path."""
    monkeypatch.setattr(obs_app, "find_obsidian_json", lambda *a, **k: None)
    target = tmp_path / "CONFIG.yaml"
    monkeypatch.setattr(paths, "CONFIG_FILE", target)
    return target


@pytest.fixture
def vault(make_vault):
    return make_vault({"Notes/A.md": "text\n", "Archive/Old.md": "text\n"}, name="Vault")


def headless(vault, **overrides):
    return SysConfig(interactive=False, vault_path_override=str(vault),
                     setting_overrides=overrides)


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

def test_a_vault_path_bootstraps_the_config(config_file, vault):
    cfg = headless(vault)

    assert config_file.is_file()
    assert cfg.sys_init
    assert cfg.sys_cfg["dir_vault"] == str(vault)
    saved = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    assert saved["dir_vault"] == str(vault)
    assert saved["vault_name"] == cfg.vault_name


def test_no_vault_means_no_bootstrap(config_file):
    """Nothing to build a config around: the advice, not a KeyError."""
    with pytest.raises(ConfigIncompleteError, match="VAULT_PATH"):
        SysConfig(interactive=False)

    assert not config_file.exists()


def test_force_setup_is_never_bootstrapped(config_file, vault):
    with pytest.raises(ConfigIncompleteError):
        SysConfig(interactive=False, force_setup=True, vault_path_override=str(vault))

    assert not config_file.exists()


def test_interactive_runs_still_go_to_the_screen(config_file, vault, monkeypatch):
    from ovi import ovi_setup

    shown = []

    class StubScreen:
        def __init__(self, sys_obj):
            shown.append(sys_obj)

        # noinspection PyMethodMayBeStatic
        def show(self):
            return True

    monkeypatch.setattr(ovi_setup, "load_setup_screen", lambda: StubScreen)

    SysConfig(interactive=True, vault_path_override=str(vault))

    assert shown, "an interactive first run must still offer the setup screen"
    assert not config_file.exists(), "only the screen may save on an interactive run"


def test_a_saved_app_that_no_longer_exists_falls_back_on_bootstrap(config_file, vault, tmp_path):
    """An old config naming an uninstalled spreadsheet program must not block a
    headless run: chk_fields_on_load() fails, and the bootstrap repairs it."""
    headless(vault)
    saved = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    saved["sys_pn_wb_exec"] = str(tmp_path / "gone.exe")
    config_file.write_text(yaml.dump(saved), encoding="utf-8")

    cfg = headless(vault)

    assert cfg.sys_pn_wb_exec == SysConfig.get_dflt_wb_exec(cfg.sys_cfg_os)
    assert yaml.safe_load(config_file.read_text(encoding="utf-8"))["sys_pn_wb_exec"] == cfg.sys_pn_wb_exec


# ---------------------------------------------------------------------------
# Overrides
# ---------------------------------------------------------------------------

def test_overrides_reach_the_packed_config_and_the_vault_record(config_file, vault):
    cfg = headless(vault, skip_rel_str="Archive", link_lim_vals=3, link_lim_tags=2,
                   sys_pn_wb_exec="")

    # The pipeline reads the packed dict, and nothing else.
    assert cfg.sys_cfg["skip_rel_str"] == "Archive"
    assert cfg.sys_cfg["link_lim_vals"] == 3
    assert cfg.sys_cfg["link_lim_tags"] == 2
    assert cfg.sys_cfg["sys_pn_wb_exec"] == ""
    assert cfg.sys_cfg["skip_abs_lst"] == [str(vault / "Archive")]
    # Both vault dicts, like the setup screen: apply_vault() reads one and the
    # screen the other.
    assert cfg.sys_vlts[cfg.vault_name]["skip_rel_str"] == "Archive"
    assert cfg.cur_vlts[cfg.vault_name]["link_lim_vals"] == 3
    # The bootstrap saved what was used, so a later --setup shows it.
    saved = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    assert saved["cur_vlts"][cfg.vault_name]["skip_rel_str"] == "Archive"


def test_overrides_on_an_existing_config_are_for_this_run_only(config_file, vault):
    """A plugin's settings page must not silently rewrite a setup completed on
    the command line."""
    headless(vault)
    before = config_file.read_text(encoding="utf-8")

    cfg = headless(vault, skip_rel_str="Archive", link_lim_vals=5)

    assert cfg.sys_cfg["skip_rel_str"] == "Archive"
    assert cfg.sys_cfg["link_lim_vals"] == 5
    assert config_file.read_text(encoding="utf-8") == before


def test_an_override_survives_the_vault_being_reapplied(config_file, vault):
    """apply_vault() copies skip_rel_str back out of the record, which is why
    the override has to be written into the record and not only the attribute."""
    cfg = headless(vault, skip_rel_str="Archive")

    cfg.apply_vault(cfg.vault_name)

    assert cfg.skip_rel_str == "Archive"


def test_an_invalid_spreadsheet_app_override_is_a_config_error(config_file, vault, tmp_path):
    with pytest.raises(ConfigIncompleteError, match="Spreadsheet application"):
        headless(vault, sys_pn_wb_exec=str(tmp_path / "nope.exe"))

    assert not config_file.exists(), "a failed override must not be saved"


def test_a_missing_skip_folder_only_warns(config_file, vault, caplog):
    with caplog.at_level(logging.WARNING, logger="ovi"):
        cfg = headless(vault, skip_rel_str="Nope")

    assert cfg.sys_cfg["skip_rel_str"] == "Nope"
    assert "No folder named 'Nope'" in caplog.text


def test_link_limits_are_coerced_and_must_not_be_negative(config_file, vault):
    assert headless(vault, link_lim_vals="4").sys_cfg["link_lim_vals"] == 4

    with pytest.raises(ValueError):
        headless(vault, link_lim_tags=-1)


def test_an_unknown_override_is_a_programming_error(config_file, vault):
    with pytest.raises(ValueError, match="bool_shw_notes"):
        headless(vault, bool_shw_notes=False)

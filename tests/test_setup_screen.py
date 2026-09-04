"""Tests for the setup screen and the configuration it produces.

Three bugs prompted these, all reported from real use of ``--setup``:

* Pressing "Save & Run" raised TypeError. The handler called
  ``save_config(sys_pn_cfg)``, but ``save_config()`` takes no arguments.
* Cancelling, or closing the window, carried on and built a workbook anyway.
  The screen had no way to report which button was pressed, and
  ``run_setup_ui()`` saved the config regardless.
* Choosing a vault from the dropdown raised AttributeError from a typo in a
  debug log line -- ``self.sys.obj`` for ``self.sys_obj``.

The handlers are exercised with a stub ``self`` via ``__new__``, so they run for
real without needing a display -- these are the same code paths a click takes,
and they run in CI.
"""

import os
from pathlib import Path

import pytest

from ovi import ovi_setup
from ovi.ovi_setup import (ConfigIncompleteError, SetupCancelledError,
                                     SysConfig, VaultNotFoundError)
from ovi.ovi_setupscreen import SetupScreen


class FakeRoot:
    def __init__(self):
        self.quit_called = False
        self.destroy_called = False

    def quit(self):
        self.quit_called = True

    def destroy(self):
        self.destroy_called = True


class FakeSysObj:
    """Only what the button handlers touch."""

    def __init__(self, save_succeeds=True):
        self.vault_name = "TestVault"
        self.sys_pn_cfg = "ignored.yaml"
        self.ovi_date = None
        self.save_succeeds = save_succeeds
        self.save_calls = []

    def save_config(self, *args):
        # *args deliberately: a caller passing an argument is the bug, and the
        # assertion below is what catches it rather than a TypeError here.
        self.save_calls.append(args)
        return self.save_succeeds


def make_screen(valid=True, save_succeeds=True):
    """A SetupScreen with no Tk behind it."""
    screen = SetupScreen.__new__(SetupScreen)
    screen.root = FakeRoot()
    screen.sys_obj = FakeSysObj(save_succeeds)
    screen.saved = False
    screen.validate_all_fields = lambda: valid
    screen.upd_all_sys_objs_with_tk_vars = lambda vault_name: None
    return screen


# ---------------------------------------------------------------------------
# Save & Run
# ---------------------------------------------------------------------------

def test_save_calls_save_config_with_no_arguments():
    """Regression: the handler passed sys_pn_cfg, but save_config() takes no
    arguments and writes to sys_pn_cfg itself. --setup raised TypeError on
    every attempt to save."""
    screen = make_screen()

    screen.on_save_and_run()

    assert screen.sys_obj.save_calls == [()], "save_config() was called with arguments"


def test_save_marks_the_screen_saved_and_closes_it():
    screen = make_screen()

    screen.on_save_and_run()

    assert screen.saved is True
    assert screen.root.quit_called and screen.root.destroy_called


def test_a_failed_save_does_not_count_as_saved(monkeypatch):
    """If the config cannot be written, the run must not proceed as though it
    had been."""
    import ovi.ovi_setupscreen as setupscreen

    shown = []
    monkeypatch.setattr(setupscreen.messagebox, "showerror",
                        lambda title, message: shown.append((title, message)))
    screen = make_screen(save_succeeds=False)

    screen.on_save_and_run()

    assert screen.saved is False
    assert not screen.root.destroy_called
    assert shown, "the user was not told the save failed"


def test_invalid_fields_block_saving():
    screen = make_screen(valid=False)

    screen.on_save_and_run()

    assert screen.sys_obj.save_calls == []
    assert screen.saved is False
    assert not screen.root.destroy_called


# ---------------------------------------------------------------------------
# Cancel, and closing the window
# ---------------------------------------------------------------------------

def test_cancel_closes_without_saving():
    screen = make_screen()

    screen.on_cancel()

    assert screen.saved is False
    assert screen.sys_obj.save_calls == []
    assert screen.root.quit_called and screen.root.destroy_called


def test_the_window_close_button_is_wired_to_cancel():
    """Regression: with no WM_DELETE_WINDOW handler, closing the window looked
    exactly like a successful save to the caller."""
    source = (Path(ovi_setup.__file__).parent / "ovi_setupscreen.py").read_text(encoding="utf-8")

    assert 'self.root.protocol("WM_DELETE_WINDOW", self.on_cancel)' in source


def test_show_reports_whether_the_user_saved():
    """show() returns self.saved, which is the whole signal the caller gets."""
    screen = make_screen()
    assert screen.saved is False

    screen.on_save_and_run()
    assert screen.saved is True


# ---------------------------------------------------------------------------
# Switching vaults with the dropdown
# ---------------------------------------------------------------------------

# The per-vault settings the screen swaps in and out. vault_id and dir_vault
# come along too, but are never shown as editable fields.
VAULT_FIELDS = {
    "skip_rel_str": "Archive",
    "bool_shw_notes": True,
    "bool_rel_paths": False,
    "bool_summ_rows": True,
    "bool_unused_1": False,
    "bool_unused_2": False,
    "bool_unused_3": False,
    "link_lim_vals": 5,
    "link_lim_tags": 7,
}


class FakeVaultSysObj:
    """Only what the vault-swap methods touch."""

    def __init__(self):
        self.vault_name = "First"
        self.vault_id = "id-first"
        self.dir_vault = r"F:\vaults\First"
        self.sys_pn_wb_exec = "excel.exe"
        for name, value in VAULT_FIELDS.items():
            setattr(self, name, value)


class RecordingVar:
    """Stands in for tk.StringVar / tk.BooleanVar, with no display behind it.

    Traces are modelled because their lifetime is the point: in Tk they belong
    to the variable object, so they die with it and fire again for every copy
    that is added back.
    """

    def __init__(self, value=None, master=None):
        self.value = value
        self.traces = []

    def get(self):
        return self.value

    def set(self, value):
        self.value = value
        for callback in self.traces:
            callback()

    def trace(self, mode, callback):
        self.traces.append(callback)


def make_vault_screen(monkeypatch):
    """A SetupScreen wired for the dropdown handlers, and its two vaults."""
    import ovi.ovi_setupscreen as setupscreen

    monkeypatch.setattr(setupscreen.tk, "StringVar", RecordingVar)
    monkeypatch.setattr(setupscreen.tk, "BooleanVar", RecordingVar)

    screen = SetupScreen.__new__(SetupScreen)
    screen.sys_obj = FakeVaultSysObj()
    screen.last_vault_name = "First"
    screen.c_vlts = {
        "First": dict(VAULT_FIELDS, vault_name="First", vault_id="id-first",
                      dir_vault=r"F:\vaults\First"),
        "Second": dict(VAULT_FIELDS, vault_name="Second", vault_id="id-second",
                       dir_vault=r"F:\vaults\Second",
                       skip_rel_str="Attachments", link_lim_vals=99),
    }
    screen.vault_name_var = RecordingVar("First")
    screen.dir_vault_var = RecordingVar(r"F:\vaults\First")
    screen.skip_rel_str_var = RecordingVar("Archive")
    screen.link_lim_vals_var = RecordingVar("5")
    screen.link_lim_tags_var = RecordingVar("7")
    for name in ("bool_shw_notes", "bool_rel_paths", "bool_summ_rows",
                 "bool_unused_1", "bool_unused_2", "bool_unused_3"):
        setattr(screen, f"{name}_var", RecordingVar(VAULT_FIELDS[name]))
    screen.sys_pn_wb_exec_var = RecordingVar("excel.exe")
    return screen


def test_reading_settings_back_into_the_tk_vars_does_not_raise(monkeypatch):
    """Regression: ``self.sys.obj.vault_name`` in a debug log line. The f-string
    is built before logger.debug() is called, so it raised AttributeError at
    every log level, and choosing any vault from the dropdown blew up."""
    screen = make_vault_screen(monkeypatch)
    screen.sys_obj.vault_name = "Second"

    screen.upd_tk_vars_with_sys_obj()

    assert screen.vault_name_var.get() == "Second"


def test_selecting_a_vault_loads_that_vaults_settings(monkeypatch):
    """The three-step swap the dropdown performs: screen -> cur_vlts,
    cur_vlts -> sys_obj, sys_obj -> screen."""
    screen = make_vault_screen(monkeypatch)

    screen.upd_all_sys_objs_with_tk_vars("First")
    screen.sys_obj.vault_name = "Second"
    screen.upd_sys_objs_with_vaults("Second")
    screen.upd_tk_vars_with_sys_obj()

    assert screen.skip_rel_str_var.get() == "Attachments"
    assert screen.link_lim_vals_var.get() == "99"
    assert screen.sys_obj.dir_vault == r"F:\vaults\Second"
    assert screen.sys_obj.vault_id == "id-second"


def test_switching_vaults_keeps_the_same_tk_var_objects(monkeypatch):
    """Regression: the swap rebound self.*_var to fresh StringVars. A widget and
    a trace both hold the variable *object*, so every widget was orphaned and
    every callback lost -- which is why the caller re-configured each widget and
    re-added each trace afterwards."""
    screen = make_vault_screen(monkeypatch)
    before = {name: value for name, value in vars(screen).items()
              if name.endswith("_var")}
    assert before, "the fixture built no tk vars"

    screen.sys_obj.vault_name = "Second"
    screen.upd_tk_vars_with_sys_obj()

    for name, var in before.items():
        assert getattr(screen, name) is var, f"{name} was replaced, not set"


def test_traces_do_not_accumulate_across_vault_switches(monkeypatch):
    """A trace must fire once per switch, no matter how many switches came
    before it. Re-adding the traces on each swap left one more copy of
    validate_all_fields() and update_links_help() registered every time, so by
    the fourth vault the vault directory was being walked four times a
    keystroke."""
    screen = make_vault_screen(monkeypatch)
    fired = []
    screen.skip_rel_str_var.trace("w", lambda: fired.append(1))

    for vault_name in ("Second", "First", "Second"):
        screen.sys_obj.vault_name = vault_name
        screen.upd_sys_objs_with_vaults(vault_name)
        screen.upd_tk_vars_with_sys_obj()

    assert len(fired) == 3, f"the trace fired {len(fired)} times over 3 switches"


def test_leaving_a_vault_keeps_the_edits_made_to_it(monkeypatch):
    """Step one of the swap: whatever was typed is written back to cur_vlts
    under the vault being left, not the one being selected."""
    screen = make_vault_screen(monkeypatch)
    screen.skip_rel_str_var.set("  Edited  ")
    screen.link_lim_tags_var.set("12")

    screen.upd_all_sys_objs_with_tk_vars("First")

    assert screen.c_vlts["First"]["skip_rel_str"] == "Edited"
    assert screen.c_vlts["First"]["link_lim_tags"] == 12
    assert screen.c_vlts["Second"]["skip_rel_str"] == "Attachments"


# ---------------------------------------------------------------------------
# run_setup_ui: the caller must honour a cancel
# ---------------------------------------------------------------------------

class StubScreen:
    """Stands in for the Tk screen; records whether it was shown."""
    instances = []

    def __init__(self, sys_obj):
        self.sys_obj = sys_obj
        StubScreen.instances.append(self)

    def show(self):
        return StubScreen.returns


def run_setup_on(sys_obj, monkeypatch, user_saved):
    StubScreen.instances = []
    StubScreen.returns = user_saved
    monkeypatch.setattr(ovi_setup, "SetupScreen", StubScreen)
    return SysConfig.run_setup_ui(sys_obj)


class MinimalConfig:
    """The attributes run_setup_ui() reads."""

    def __init__(self, tmp_path):
        self.interactive = True
        self.sys_pn_cfg = str(tmp_path / "CONFIG.yaml")
        self.saves = 0

    def save_config(self):
        self.saves += 1
        Path(self.sys_pn_cfg).write_text("written", encoding="utf-8")
        return True


def test_cancelling_setup_raises(tmp_path, monkeypatch):
    """Regression: run_setup_ui() called save_config() unconditionally, so a
    cancelled dialog still wrote a config and the run continued."""
    cfg = MinimalConfig(tmp_path)

    with pytest.raises(SetupCancelledError):
        run_setup_on(cfg, monkeypatch, user_saved=False)

    assert cfg.saves == 0
    assert not Path(cfg.sys_pn_cfg).exists(), "a cancelled setup wrote a config"


def test_saving_setup_does_not_raise(tmp_path, monkeypatch):
    """The screen writes the config itself, so run_setup_ui() must not write a
    second time."""
    cfg = MinimalConfig(tmp_path)

    run_setup_on(cfg, monkeypatch, user_saved=True)

    assert cfg.saves == 0
    assert StubScreen.instances, "the setup screen was never shown"


def test_non_interactive_setup_still_raises_config_incomplete(tmp_path, monkeypatch):
    cfg = MinimalConfig(tmp_path)
    cfg.interactive = False

    with pytest.raises(ConfigIncompleteError):
        run_setup_on(cfg, monkeypatch, user_saved=True)

    assert not StubScreen.instances, "a window was opened in non-interactive mode"


# ---------------------------------------------------------------------------
# The CLI, end to end
# ---------------------------------------------------------------------------

def test_cli_stops_cleanly_when_setup_is_cancelled(monkeypatch):
    """The reported bug, at the level the user sees it: cancel the dialog and
    ovi went on to build a workbook."""
    from click.testing import CliRunner

    from ovi import ovi

    def refuse(**kwargs):
        raise SetupCancelledError("Setup was cancelled; nothing was changed.")

    built = []
    monkeypatch.setattr(ovi, "SysConfig", refuse)
    monkeypatch.setattr(ovi, "run_pipeline", lambda *a, **k: built.append(True))
    monkeypatch.setattr(ovi, "run_with_splash", lambda *a, **k: built.append(True))

    result = CliRunner().invoke(ovi.cli, ["--setup"])

    assert not built, "a workbook was built after the user cancelled setup"
    assert result.exit_code == 1
    assert "cancelled" in result.output.lower()
    assert "Traceback" not in result.output


# ---------------------------------------------------------------------------
# Field validation -- what happens when bad values are typed in
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", ["", "   ", None])
def test_empty_executable_path_means_the_system_default(value):
    """Blank used to be rejected, which on macOS and Linux -- where a fresh
    install finds no recognisable program to fill in -- reopened the setup
    screen on every run. Blank now means "open with the system default"."""
    valid, message = SysConfig.validate_sys_pn_wb_exec(value)

    assert valid, message


def test_nonexistent_executable_path_is_rejected(tmp_path):
    valid, message = SysConfig.validate_sys_pn_wb_exec(str(tmp_path / "nope.exe"))

    assert not valid
    assert "does not exist" in message.lower()


def test_a_directory_is_not_an_executable(tmp_path):
    valid, message = SysConfig.validate_sys_pn_wb_exec(str(tmp_path))

    assert not valid
    assert "must be a file" in message.lower()


def test_an_existing_file_passes_as_an_executable(tmp_path):
    """os.access(X_OK) is permissive on Windows, so this asserts only that a
    real file gets past the existence and type checks."""
    exe = tmp_path / "excel.exe"
    exe.write_text("", encoding="utf-8")
    os.chmod(exe, 0o755)

    valid, message = SysConfig.validate_sys_pn_wb_exec(str(exe))

    assert valid, message


@pytest.mark.parametrize("value", ["", "   ", None])
def test_an_empty_skip_list_is_allowed(value, tmp_path):
    """Skipping nothing is a normal choice, not an error."""
    valid, _ = SysConfig.validate_skip_rel_str(value, str(tmp_path))

    assert valid


def test_skip_list_naming_a_folder_that_exists_is_accepted(tmp_path):
    (tmp_path / "Archive").mkdir()
    (tmp_path / "nested" / "Attachments").mkdir(parents=True)

    valid, message = SysConfig.validate_skip_rel_str("Archive, Attachments", str(tmp_path))

    assert valid, message


def test_skip_list_naming_a_missing_folder_is_rejected(tmp_path):
    (tmp_path / "Archive").mkdir()

    valid, message = SysConfig.validate_skip_rel_str("Archive, Ghost", str(tmp_path))

    assert not valid
    assert "Ghost" in message, "the message should name the folder that is wrong"


def test_skip_list_needs_a_valid_vault_first(tmp_path):
    valid, message = SysConfig.validate_skip_rel_str("Archive", str(tmp_path / "nope"))

    assert not valid
    assert "vault path" in message.lower()


@pytest.mark.parametrize("value", ["", "   ", None])
def test_empty_vault_path_is_rejected(value):
    valid, message = SysConfig.validate_dir_vault(value)

    assert not valid
    assert "empty" in message.lower()


def test_nonexistent_vault_path_is_rejected(tmp_path):
    valid, message = SysConfig.validate_dir_vault(str(tmp_path / "nope"))

    assert not valid
    assert "does not exist" in message.lower()


def test_a_file_is_not_a_vault(tmp_path):
    note = tmp_path / "note.md"
    note.write_text("", encoding="utf-8")

    valid, message = SysConfig.validate_dir_vault(str(note))

    assert not valid
    assert "must be a directory" in message.lower()


def test_a_real_directory_is_a_valid_vault(tmp_path):
    valid, message = SysConfig.validate_dir_vault(str(tmp_path))

    assert valid, message


@pytest.mark.parametrize("value", ["", "   ", None])
def test_empty_vault_id_is_rejected(value):
    valid, message = SysConfig.validate_vault_id(value)

    assert not valid
    assert "empty" in message.lower()


# ---------------------------------------------------------------------------
# Vaults Obsidian has never opened -- registering a bare folder
# ---------------------------------------------------------------------------

def test_a_vault_folder_has_an_obsidian_dir(tmp_path):
    (tmp_path / ".obsidian").mkdir()

    has_obs_dir, message = SysConfig.check_obsidian_dir(str(tmp_path))

    assert has_obs_dir
    assert message == ""


def test_a_folder_without_obsidian_dir_warns(tmp_path):
    has_obs_dir, message = SysConfig.check_obsidian_dir(str(tmp_path))

    assert not has_obs_dir
    assert ".obsidian" in message
    # The point of the warning is that the scan still happens.
    assert "still be scanned" in message


@pytest.mark.parametrize("value", ["", "   ", None])
def test_a_blank_path_gets_no_obsidian_warning(value):
    """validate_dir_vault() is already rejecting it; two complaints is noise."""
    has_obs_dir, message = SysConfig.check_obsidian_dir(value)

    assert not has_obs_dir
    assert message == ""


def test_the_obsidian_check_is_not_part_of_path_validation(tmp_path):
    """Regression: a missing .obsidian must stay a warning.

    validate_dir_vault() gates chk_fields_on_load(), which decides whether the
    setup screen opens at all. Fold the .obsidian test into it and every plain
    folder forces setup, and Save is disabled for the very folders this feature
    exists to allow.
    """
    assert not SysConfig.check_obsidian_dir(str(tmp_path))[0]
    assert SysConfig.validate_dir_vault(str(tmp_path))[0]


def make_config():
    """A SysConfig with just the two vault dicts -- no obsidian.json needed."""
    cfg = SysConfig.__new__(SysConfig)
    cfg.sys_vlts = {}
    cfg.cur_vlts = {}
    return cfg


def test_registering_a_folder_obsidian_never_opened(tmp_path):
    vault = tmp_path / "Copied"
    vault.mkdir()
    cfg = make_config()

    vault_name = cfg.register_vault_dir(str(vault))

    assert vault_name == f"Copied - ({tmp_path})"
    # apply_vault() reads sys_vlts, the setup screen reads cur_vlts.
    assert vault_name in cfg.sys_vlts
    assert vault_name in cfg.cur_vlts
    assert cfg.cur_vlts[vault_name] is cfg.sys_vlts[vault_name]
    assert cfg.sys_vlts[vault_name]["dir_vault"] == str(vault)


def test_a_registered_vault_carries_the_folder_name_as_its_id(tmp_path):
    """obs_hyperlink() builds obsidian://open?vault=<vault_id>.

    An empty id makes every link in the workbook permanently dead. Obsidian's
    URI scheme takes a vault name here as well as an id, so the folder name
    leaves the links inert only until the folder is opened in Obsidian.
    """
    vault = tmp_path / "Copied"
    vault.mkdir()
    cfg = make_config()

    vault_name = cfg.register_vault_dir(str(vault))

    assert cfg.sys_vlts[vault_name]["vault_id"] == "Copied"


def test_registering_the_same_folder_twice_adds_one_vault(tmp_path):
    vault = tmp_path / "Copied"
    vault.mkdir()
    cfg = make_config()

    first = cfg.register_vault_dir(str(vault))
    second = cfg.register_vault_dir(str(vault).replace(chr(92), "/"))

    assert first == second, "the folder picker's forward slashes are the same folder"
    assert len(cfg.sys_vlts) == 1


def test_a_folder_already_known_keeps_its_own_name(tmp_path):
    """Browsing to a vault Obsidian did report must select it, not shadow it."""
    vault = tmp_path / "Known"
    vault.mkdir()
    cfg = make_config()
    cfg.sys_vlts["A Name Of Its Own"] = {"vault_id": "abc123", "dir_vault": str(vault)}

    vault_name = cfg.register_vault_dir(str(vault))

    assert vault_name == "A Name Of Its Own"
    assert len(cfg.sys_vlts) == 1


def test_registering_a_path_that_is_not_a_directory(tmp_path):
    cfg = make_config()

    with pytest.raises(VaultNotFoundError):
        cfg.register_vault_dir(str(tmp_path / "nope"))


def test_a_command_line_path_obsidian_never_opened_is_accepted(tmp_path):
    """Regression: this used to raise VaultNotFoundError.

    The vault list comes from obsidian.json, so ovi <folder> refused any
    folder that had never been opened in Obsidian -- a copied vault, a backup,
    a machine whose Obsidian had been reset.
    """
    vault = tmp_path / "Copied"
    vault.mkdir()
    cfg = make_config()
    applied = []
    cfg.apply_vault = applied.append
    cfg.cfg_pack = lambda: None

    cfg.select_vault_by_path(str(vault))

    assert applied == [f"Copied - ({tmp_path})"]


def test_a_command_line_path_prefers_the_vault_already_known(tmp_path):
    vault = tmp_path / "Known"
    vault.mkdir()
    cfg = make_config()
    cfg.sys_vlts["A Name Of Its Own"] = {"vault_id": "abc123", "dir_vault": str(vault)}
    applied = []
    cfg.apply_vault = applied.append
    cfg.cfg_pack = lambda: None

    cfg.select_vault_by_path(str(vault))

    assert applied == ["A Name Of Its Own"]
    assert len(cfg.sys_vlts) == 1


# ---------------------------------------------------------------------------
# The Vault Folder field -- committing a typed or browsed path
# ---------------------------------------------------------------------------

def make_commit_screen(monkeypatch, tmp_path):
    """A vault-swap screen whose sys_obj is a real SysConfig.

    commit_vault_dir() leans on register_vault_dir() and validate_dir_vault(),
    so the stub sys_obj the dropdown tests use is not enough here. A SysConfig
    built with __new__ has the real methods and needs no obsidian.json.
    """
    screen = make_vault_screen(monkeypatch)

    cfg = make_config()
    cfg.cur_vlts = screen.c_vlts            # the screen aliases this dict, as the real one does
    cfg.sys_vlts = dict(screen.c_vlts)
    cfg.vault_name = "First"
    cfg.vault_id = "id-first"
    cfg.dir_vault = str(tmp_path / "First")
    cfg.sys_pn_wb_exec = "excel.exe"
    for name, value in VAULT_FIELDS.items():
        setattr(cfg, name, value)

    screen.sys_obj = cfg
    screen.combx_vault_name = {"values": list(screen.c_vlts)}
    screen.validate_all_fields = lambda: True
    return screen


def test_typing_a_folder_registers_it_and_switches_to_it(monkeypatch, tmp_path):
    vault = tmp_path / "Copied"
    vault.mkdir()
    screen = make_commit_screen(monkeypatch, tmp_path)

    screen.dir_vault_var.set(str(vault))
    screen.commit_vault_dir()

    vault_name = f"Copied - ({tmp_path})"
    assert screen.last_vault_name == vault_name
    assert screen.sys_obj.vault_name == vault_name
    assert screen.sys_obj.dir_vault == str(vault)
    # Save indexes cur_vlts[vault_name]; without a record it raises KeyError.
    assert vault_name in screen.c_vlts
    # The dropdown is the only thing that can show the new vault, and its
    # values were a snapshot taken in __init__.
    assert vault_name in screen.combx_vault_name["values"]


def test_committing_the_folder_already_shown_changes_nothing(monkeypatch, tmp_path):
    first = tmp_path / "First"
    first.mkdir()
    screen = make_commit_screen(monkeypatch, tmp_path)
    screen.c_vlts["First"]["dir_vault"] = str(first)

    screen.dir_vault_var.set(str(first))
    screen.commit_vault_dir()

    assert screen.last_vault_name == "First"
    assert len(screen.c_vlts) == 2, "no second record for the vault already selected"


def test_the_folder_pickers_forward_slashes_are_normalised(monkeypatch, tmp_path):
    """askdirectory() hands back forward slashes on Windows."""
    first = tmp_path / "First"
    first.mkdir()
    screen = make_commit_screen(monkeypatch, tmp_path)
    screen.c_vlts["First"]["dir_vault"] = str(first)

    screen.dir_vault_var.set(str(first).replace(chr(92), "/"))
    screen.commit_vault_dir()

    assert screen.dir_vault_var.get() == str(first)


def test_an_unusable_folder_neither_registers_nor_switches(monkeypatch, tmp_path):
    screen = make_commit_screen(monkeypatch, tmp_path)

    screen.dir_vault_var.set(str(tmp_path / "nope"))
    screen.commit_vault_dir()

    assert screen.last_vault_name == "First"
    assert len(screen.c_vlts) == 2


def test_a_vault_missing_from_cur_vlts_is_put_back(monkeypatch, tmp_path):
    """sys_vlts can hold vaults cur_vlts does not; the screen only reads cur_vlts.

    Regression guard: upd_sys_objs_with_vaults() indexes cur_vlts, so a vault
    found in sys_vlts alone would raise KeyError halfway through the swap.
    """
    vault = tmp_path / "OnlyInSys"
    vault.mkdir()
    screen = make_commit_screen(monkeypatch, tmp_path)
    vault_name = screen.sys_obj.register_vault_dir(str(vault))
    del screen.c_vlts[vault_name]

    screen.dir_vault_var.set(str(vault))
    screen.commit_vault_dir()

    assert vault_name in screen.c_vlts
    assert screen.last_vault_name == vault_name


def test_legacy_sys_id_is_read_as_ovi():
    """A CONFIG.yaml written before the rename to Obsidian Insights says
    ``sys_id: v_chk``. It must come back as ``ovi`` so generated filenames
    switch over without an --init."""
    cfg = SysConfig.__new__(SysConfig)
    cfg.sys_cfg = {"sys_id": "v_chk"}

    cfg.cfg_unpack()

    assert cfg.sys_id == "ovi"

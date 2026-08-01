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

from vault_check import v_chk_setup
from vault_check.v_chk_setup import (ConfigIncompleteError, SetupCancelledError,
                                     SysConfig)
from vault_check.v_chk_setupscreen import SetupScreen


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
        self.v_chk_date = None
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
    import vault_check.v_chk_setupscreen as setupscreen

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
    source = (Path(v_chk_setup.__file__).parent / "v_chk_setupscreen.py").read_text(encoding="utf-8")

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
    import vault_check.v_chk_setupscreen as setupscreen

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
    monkeypatch.setattr(v_chk_setup, "SetupScreen", StubScreen)
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
    v_chk went on to build a workbook."""
    from click.testing import CliRunner

    from vault_check import v_chk

    def refuse(**kwargs):
        raise SetupCancelledError("Setup was cancelled; nothing was changed.")

    built = []
    monkeypatch.setattr(v_chk, "SysConfig", refuse)
    monkeypatch.setattr(v_chk, "run_pipeline", lambda *a, **k: built.append(True))
    monkeypatch.setattr(v_chk, "run_with_splash", lambda *a, **k: built.append(True))

    result = CliRunner().invoke(v_chk.cli, ["--setup"])

    assert not built, "a workbook was built after the user cancelled setup"
    assert result.exit_code == 1
    assert "cancelled" in result.output.lower()
    assert "Traceback" not in result.output


# ---------------------------------------------------------------------------
# Field validation -- what happens when bad values are typed in
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", ["", "   ", None])
def test_empty_executable_path_is_rejected(value):
    valid, message = SysConfig.validate_sys_pn_wb_exec(value)

    assert not valid
    assert "empty" in message.lower()


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

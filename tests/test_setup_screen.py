"""Tests for the setup screen and the configuration it produces.

Two bugs prompted these, both reported from real use of ``--setup``:

* Pressing "Save & Run" raised TypeError. The handler called
  ``save_config(sys_pn_cfg)``, but ``save_config()`` takes no arguments.
* Cancelling, or closing the window, carried on and built a workbook anyway.
  The screen had no way to report which button was pressed, and
  ``run_setup_ui()`` saved the config regardless.

The button handlers are exercised with a stub ``self`` via ``__new__``, so they
run for real without needing a display -- these are the same code paths a click
takes, and they run in CI.
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

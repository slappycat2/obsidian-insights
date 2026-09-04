"""The platform branches, driven from whatever machine runs the suite.

CI runs on Windows, macOS and Linux, but the code paths that differ by OS were
never called by any test: StubSysConfig bypasses SysConfig, so
obsidian.json discovery, spreadsheet-app detection and the launch command
went unexercised on every runner. Each function here takes a ``system``
argument (or reads a monkeypatched ``platform.system``) so all three
branches run on all three runners.

Every test pins a bug that stopped a Mac or Linux user before the first
workbook, or corrupted what they got.
"""

import os
import platform
from pathlib import Path

import pytest

from ovi import ovi_launch as launch
from ovi import ovi_obs_app as obs_app
from ovi.ovi_setup import SysConfig
from ovi.ovi_xl import ExcelExporter, WorkbookLockedError


# ---------------------------------------------------------------------------
# Where obsidian.json lives
# ---------------------------------------------------------------------------

def test_linux_looks_in_xdg_deb_flatpak_and_snap_locations(tmp_path):
    home = tmp_path / "home"
    dirs = obs_app.candidate_config_dirs("Linux", home, env={"XDG_CONFIG_HOME": "/xdg"})

    assert dirs[0] == Path("/xdg/obsidian")
    assert home / ".config/obsidian" in dirs
    assert home / ".var/app/md.obsidian.Obsidian/config/obsidian" in dirs      # Flatpak
    assert home / "snap/obsidian/current/.config/obsidian" in dirs             # Snap


def test_macos_and_windows_locations(tmp_path):
    home = tmp_path / "home"

    assert obs_app.candidate_config_dirs("Darwin", home, env={}) == \
        [home / "Library/Application Support/obsidian"]
    assert obs_app.candidate_config_dirs("Windows", home, env={"APPDATA": str(tmp_path / "rd")}) == \
        [tmp_path / "rd" / "obsidian"]
    # No APPDATA at all: fall back to the conventional location, never to "/".
    assert obs_app.candidate_config_dirs("Windows", home, env={}) == \
        [home / "AppData/Roaming/obsidian"]


def test_an_unknown_os_takes_the_unix_list(tmp_path):
    """Regression: a bare dict index raised KeyError on FreeBSD at startup."""
    dirs = obs_app.candidate_config_dirs("FreeBSD", tmp_path, env={})

    assert tmp_path / ".config/obsidian" in dirs


def test_the_first_existing_obsidian_json_wins(tmp_path):
    flatpak = tmp_path / ".var/app/md.obsidian.Obsidian/config/obsidian"
    flatpak.mkdir(parents=True)
    (flatpak / "obsidian.json").write_text("{}", encoding="utf-8")

    found = obs_app.find_obsidian_json("Linux", tmp_path, env={})

    assert found == flatpak / "obsidian.json"
    assert obs_app.find_obsidian_json("Linux", tmp_path / "nowhere", env={}) is None


def test_missing_obsidian_json_yields_no_vaults_and_no_error(monkeypatch):
    """Regression: this raised out of SysConfig.__post_init__, so a machine
    where Obsidian had never run could not even reach the setup screen --
    not even with an explicit vault path on the command line."""
    monkeypatch.setattr(obs_app, "find_obsidian_json", lambda *a, **k: None)
    app = obs_app.ObsidianApp()

    app.load_current_obs_vaults()

    assert app.cur_vlts == {}
    assert app.dflt_vault_name == ""


def test_vaults_are_read_and_missing_folders_skipped(tmp_path, monkeypatch):
    here = tmp_path / "Here"
    here.mkdir()
    cfg = tmp_path / "obsidian.json"
    cfg.write_text(
        '{"vaults": {"abc123": {"path": "%s", "open": true},'
        '            "gone42": {"path": "%s"}}}'
        % (str(here).replace("\\", "\\\\"), str(tmp_path / "Gone").replace("\\", "\\\\")),
        encoding="utf-8")
    monkeypatch.setattr(obs_app, "find_obsidian_json", lambda *a, **k: cfg)
    app = obs_app.ObsidianApp()

    app.load_current_obs_vaults()

    assert list(app.cur_vlts) == [f"Here - ({tmp_path})"]
    assert app.dflt_vault_name == f"Here - ({tmp_path})"
    assert app.cur_vlts[app.dflt_vault_name]["vault_id"] == "abc123"


def test_headless_with_no_vault_anywhere_is_a_clean_config_error(tmp_path, monkeypatch):
    """No obsidian.json, no CONFIG.yaml, no VAULT_PATH: the answer is
    ConfigIncompleteError with advice, not a KeyError on an empty name."""
    from ovi import ovi_paths as paths
    from ovi.ovi_setup import ConfigIncompleteError

    monkeypatch.setattr(obs_app, "find_obsidian_json", lambda *a, **k: None)
    monkeypatch.setattr(paths, "CONFIG_FILE", tmp_path / "CONFIG.yaml")

    with pytest.raises(ConfigIncompleteError):
        SysConfig(interactive=False)


# ---------------------------------------------------------------------------
# The spreadsheet application
# ---------------------------------------------------------------------------

def test_blank_app_is_valid_everywhere():
    for system in ("Windows", "Darwin", "Linux"):
        assert launch.validate_app("", system)[0]
        assert launch.validate_app(None, system)[0]


def test_macos_app_bundle_validates_and_launches_with_open(tmp_path):
    """Regression: Excel on macOS is a directory, /Applications/Microsoft
    Excel.app, which is_file() rejected -- and the Browse dialog returns
    exactly that path, so the setup screen could not be completed on a Mac."""
    bundle = tmp_path / "Microsoft Excel.app"
    bundle.mkdir()

    assert launch.validate_app(str(bundle), "Darwin") == (True, "")
    assert launch.launch_command(str(bundle), "/tmp/x.xlsx", "Darwin") == \
        ["open", "-a", str(bundle), "/tmp/x.xlsx"]
    # The same directory is still not an executable on the other platforms.
    assert not launch.validate_app(str(bundle), "Linux")[0]


def test_a_bare_command_on_path_validates_on_linux(tmp_path):
    """Regression: the Linux default was the bare name 'scalc', which
    Path.exists() tested against the working directory and always rejected,
    so the setup screen reopened on every run."""
    which = {"libreoffice": "/usr/bin/libreoffice"}.get

    assert launch.validate_app("libreoffice", "Linux", which=which) == (True, "")
    assert not launch.validate_app("nothere", "Linux", which=which)[0]
    # A path-shaped value is a path, and a missing one is missing.
    assert "does not exist" in launch.validate_app("/opt/nothere", "Linux", which=which)[1]


def test_a_directory_is_rejected_off_macos(tmp_path):
    assert "must be a file" in launch.validate_app(str(tmp_path), "Windows")[1]


def test_blank_app_launches_via_the_system_opener():
    assert launch.launch_command("", "/v/x.xlsx", "Darwin") == ["open", "/v/x.xlsx"]
    assert launch.launch_command("", "/v/x.xlsx", "Linux") == ["xdg-open", "/v/x.xlsx"]
    assert launch.launch_command("", "C:/v/x.xlsx", "Windows") is None     # os.startfile


def test_an_explicit_program_is_run_directly():
    assert launch.launch_command("/usr/bin/soffice", "/v/x.xlsx", "Linux") == \
        ["/usr/bin/soffice", "/v/x.xlsx"]


def test_default_app_detection_per_platform(tmp_path, monkeypatch):
    """Regression: the macOS default was the shell string 'open -a Numbers.app '
    handed to Popen as argv[0], and the non-Windows branch never checked
    that any candidate existed."""
    excel = tmp_path / "EXCEL.EXE"
    excel.write_text("", encoding="utf-8")
    monkeypatch.setattr(launch, "WINDOWS_CANDIDATES", (str(tmp_path / "nope.exe"), str(excel)))
    assert launch.default_spreadsheet_app("Windows") == str(excel)

    numbers = tmp_path / "Numbers.app"
    numbers.mkdir()
    monkeypatch.setattr(launch, "DARWIN_CANDIDATES", (str(tmp_path / "Excel.app"), str(numbers)))
    assert launch.default_spreadsheet_app("Darwin") == str(numbers)

    assert launch.default_spreadsheet_app("Linux", which=lambda n: None) == ""
    assert launch.default_spreadsheet_app(
        "Linux", which={"soffice": "/usr/bin/soffice"}.get) == "soffice"

    # Nothing found is not an error: blank means the system default.
    monkeypatch.setattr(launch, "DARWIN_CANDIDATES", ())
    assert launch.default_spreadsheet_app("Darwin") == ""


def test_open_workbook_failure_is_reported_not_raised(monkeypatch):
    """The workbook is already written when the launch fails; a traceback
    after a successful run is the wrong answer."""
    import click
    from ovi import ovi

    def boom(app, workbook, system=None):
        raise FileNotFoundError(2, "No such file", app)

    monkeypatch.setattr(ovi.launch, "open_workbook", boom)
    echoed = []
    monkeypatch.setattr(click, "echo", lambda msg, **k: echoed.append(msg))

    class Exporter:
        sys_pn_wb_exec = "/nope/excel"
        sys_pn_wbs = "/v/x.xlsx"

    ovi.open_workbook(Exporter())

    assert echoed and "Could not open" in echoed[0]


# ---------------------------------------------------------------------------
# Config values that are facts about the machine, not settings
# ---------------------------------------------------------------------------

def test_sys_cfg_os_is_never_restored_from_config():
    """Regression: a CONFIG.yaml carried from Windows to a Mac kept
    sys_cfg_os == 'Windows', which then broke the dot-folder scan."""
    cfg = SysConfig.__new__(SysConfig)
    foreign = "Darwin" if platform.system() != "Darwin" else "Windows"
    cfg.sys_cfg = {"sys_cfg_os": foreign}

    cfg.cfg_unpack()

    assert cfg.sys_cfg_os == platform.system()


def test_dot_dirs_are_found_without_a_separator_guess(tmp_path):
    (tmp_path / ".obsidian").mkdir()
    (tmp_path / ".trash").mkdir()
    (tmp_path / "Notes").mkdir()
    (tmp_path / ".stray-file").write_text("", encoding="utf-8")

    found = SysConfig.get_dot_dirs("whatever", str(tmp_path))

    assert sorted(found) == [".obsidian", ".trash"]
    assert SysConfig.get_dot_dirs("whatever", "") == []
    assert SysConfig.get_dot_dirs("whatever", str(tmp_path / "missing")) == []


# ---------------------------------------------------------------------------
# Encodings
# ---------------------------------------------------------------------------

def test_config_yaml_round_trips_a_non_ascii_vault_path(tmp_path):
    """Regression: the config was read and written in the locale encoding --
    cp1252 on Windows, UTF-8 elsewhere -- so a path with an accent survived
    only by the accident of yaml.dump escaping it."""
    cfg = SysConfig.__new__(SysConfig)
    target = tmp_path / "CONFIG.yaml"
    data = {"dir_vault": "C:/Vaults/Vault Ünïcode 📝", "vault_name": "Ünïcode"}

    assert cfg.write_config(str(target), data)
    raw = target.read_bytes()

    assert b"\r\n" not in raw                       # LF regardless of platform
    assert "Ünïcode" in raw.decode("utf-8")         # readable, not \u-escaped
    assert cfg.read_config(str(target)) == data


def test_batch_yaml_round_trips_a_non_ascii_path(tmp_path, stub_config):
    from ovi.ovi_wb_setup import WbDataDef

    wbd = WbDataDef(stub_config(tmp_path / "Vault Ünïcode"))
    wbd.sys_pn_batch = str(tmp_path / "batch.yaml")
    wbd.wb_def = {"sys_cfg": {"dir_vault": "Vault Ünïcode 📝"}, "wb_data": {}, "wb_tabs": {}}

    wbd.write_bat_data()

    assert wbd.read_wb_data()["sys_cfg"]["dir_vault"] == "Vault Ünïcode 📝"


def test_a_bom_prefixed_note_is_parsed_and_a_bom_only_note_is_empty(scan):
    result = scan({
        "Bom.md": "\ufeff---\ntitle: Bommed\n---\nbody",
        "Empty.md": "\ufeff",
    })

    assert "bommed" in {v.lower() for v in result.obs_props["title"]}
    assert any(p.endswith("Empty.md") for p in result.obs_empty)


# ---------------------------------------------------------------------------
# Links
# ---------------------------------------------------------------------------

def make_exporter(vault_id="vid", dir_vault="/v"):
    exporter = ExcelExporter.__new__(ExcelExporter)
    exporter.vault_id = vault_id
    exporter.dir_vault = dir_vault
    exporter.interactive = False
    return exporter


def test_vault_id_and_file_are_percent_encoded():
    """A vault registered by folder name uses that name as its id, so
    'Work & Home' used to end the vault parameter at the ampersand."""
    link = make_exporter("Work & Home").obs_hyperlink("Daily/My Nôte.md")

    assert 'vault=Work%20%26%20Home&file=Daily/My%20N%C3%B4te.md' in link
    assert link.endswith('"Daily/My Nôte")')


def test_backslashes_become_forward_slashes_and_only_the_suffix_is_dropped():
    link = make_exporter().obs_hyperlink("sub\\README.md.md")

    assert "file=sub/README.md.md" in link
    assert '"sub/README.md")' in link


def test_a_quote_in_a_note_name_does_not_break_the_formula():
    """Legal filename character on macOS and Linux; it was pasted raw into a
    double-quoted formula string."""
    link = make_exporter().obs_hyperlink('Say "hi".md')

    assert link.endswith('"Say ""hi""")')
    assert ExcelExporter.web_hyperlink('http://x/"y"').endswith('"http://x/""y""")')


def test_duplicates_link_is_vault_relative_with_forward_slashes(tmp_path):
    vault = tmp_path / "Vault"
    note = vault / "A" / "B" / "Note.md"
    note.parent.mkdir(parents=True)
    note.write_text("", encoding="utf-8")
    exporter = make_exporter(dir_vault=str(vault))

    assert exporter.vault_relative(str(note)) == "A/B/Note.md"
    # Different case or spelling of the vault path must not defeat the match
    # on a case-insensitive filesystem; on a case-sensitive one this is simply
    # a path outside the vault and comes back whole.
    outside = tmp_path / "Elsewhere" / "Note.md"
    assert exporter.vault_relative(str(outside)).endswith("Elsewhere/Note.md")


# ---------------------------------------------------------------------------
# Headless never opens a window
# ---------------------------------------------------------------------------

def test_a_locked_workbook_raises_instead_of_prompting_when_not_interactive(tmp_path, monkeypatch):
    """Regression: the Retry/Cancel messagebox fired under --headless and in
    the test suite, which on a display-less Linux box is a TclError."""
    target = tmp_path / "out.xlsx"
    target.write_text("", encoding="utf-8")
    exporter = make_exporter()
    exporter.sys_pn_wbs = str(target)

    def locked(path):
        raise PermissionError(13, "in use", path)

    monkeypatch.setattr(os, "remove", locked)
    monkeypatch.setattr(ExcelExporter, "retry_file_removal",
                        staticmethod(lambda msg: pytest.fail("a dialog was opened")))

    class Workbook:
        def save(self, path):
            pytest.fail("saved over a locked file")

    with pytest.raises(WorkbookLockedError):
        exporter.save_workbook(Workbook())


def test_the_export_and_setup_modules_do_not_import_tk_at_module_scope():
    """--headless must run on a Python built without tkinter. The setup
    screen and splash are the only modules allowed to need it."""
    import ast

    for module in ("ovi_xl.py", "ovi.py", "ovi_build.py", "ovi_wb_tabs.py", "ovi_wb_setup.py",
                   "ovi_obs_app.py", "ovi_launch.py"):
        source = (Path(launch.__file__).parent / module).read_text(encoding="utf-8")
        names = []
        for node in ast.parse(source).body:
            if isinstance(node, ast.Import):
                names += [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names.append(node.module or "")

        assert not any(n.startswith("tkinter") for n in names), f"{module} imports tkinter"

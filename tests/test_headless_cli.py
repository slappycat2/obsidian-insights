"""End-to-end: the real SysConfig, the real CLI, no Obsidian and no window.

Everything else in the suite goes through StubSysConfig, which is why the
platform bugs in SysConfig survived a green CI on all three runners. These
tests run ``ovi --headless --do-not-open`` in a child process whose home
directory is an empty temp folder -- so there is no obsidian.json to find --
and whose spreadsheet application is blank. That is exactly the state of a
fresh install on a Mac or a Linux box, and it used to fail before the setup
screen could open.

A headless run cannot show the setup screen, so on a machine with no
CONFIG.yaml it builds one from the defaults when -- and only when -- a
VAULT_PATH names what to scan. That is the path the Obsidian plugin takes on
its first run. With no vault there is nothing to build a config around, and
the run still stops with advice.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def clean_env(tmp_path):
    """A child-process environment with nothing of this machine's in it."""
    home = tmp_path / "home"
    home.mkdir()
    data = tmp_path / "data"
    env = dict(os.environ)
    env.update({
        "OVI_DATA_DIR": str(data),
        "HOME": str(home),
        "USERPROFILE": str(home),
        "APPDATA": str(home / "AppData" / "Roaming"),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "PYTHONIOENCODING": "utf-8",
    })
    return env, data


def run(args, env):
    return subprocess.run([sys.executable, *args], env=env, cwd=REPO_ROOT,
                          capture_output=True, text=True, encoding="utf-8", timeout=120)


def test_headless_run_with_no_obsidian_and_no_spreadsheet_app(clean_env, make_vault):
    """First run on a fresh machine: no config, no obsidian.json, a vault path.

    The config is created from the defaults and the workbook is written, all
    without a window. This used to need a SysConfig subclass whose
    run_setup_ui() saved instead of opening the screen.
    """
    env, data = clean_env
    vault = make_vault({"Note.md": "---\ntitle: Hello\ntags: [a]\n---\nBody #tag\n"},
                       name="Fresh Vault")

    result = run(["-m", "ovi.ovi", "--headless", "--do-not-open", "-d", "WARNING", str(vault)], env)

    assert result.returncode == 0, result.stderr
    assert "Traceback" not in result.stderr
    assert (data / "CONFIG.yaml").is_file(), "the config was not bootstrapped"
    workbooks = list((data / "data" / "workbooks").glob("ovi_Fresh_Vault_*.xlsx"))
    assert len(workbooks) == 1, result.stdout + result.stderr
    assert result.stdout.strip() == f"Workbook written to {workbooks[0]}"

    saved = yaml.safe_load((data / "CONFIG.yaml").read_text(encoding="utf-8"))
    assert saved["dir_vault"] == str(vault)
    # The platform default: a spreadsheet program found in its usual place, or
    # blank for the system handler. Either way it has to validate, because the
    # next run's chk_fields_on_load() gates on it.
    from ovi.ovi_setup import SysConfig
    assert SysConfig.validate_sys_pn_wb_exec(saved["sys_pn_wb_exec"])[0]


def test_second_headless_run_reuses_the_bootstrapped_config(clean_env, make_vault):
    """The bootstrap is a one-off; the next run finds a valid config and
    numbers its workbook after the first."""
    env, data = clean_env
    vault = make_vault({"Note.md": "text\n"}, name="Fresh Vault")
    args = ["-m", "ovi.ovi", "--headless", "--do-not-open", "-d", "WARNING", str(vault)]

    first = run(args, env)
    stamp = (data / "CONFIG.yaml").stat().st_mtime_ns
    second = run(args, env)

    assert first.returncode == 0 and second.returncode == 0, first.stderr + second.stderr
    assert (data / "CONFIG.yaml").stat().st_mtime_ns == stamp, "a plain run rewrote the config"
    names = sorted(p.name for p in (data / "data" / "workbooks").glob("*.xlsx"))
    assert names == ["ovi_Fresh_Vault_0000.xlsx", "ovi_Fresh_Vault_0001.xlsx"]


def test_headless_run_without_setup_or_a_vault_says_what_to_do(clean_env):
    """No CONFIG.yaml, no VAULT_PATH and --headless: a one-line error, exit 1,
    no traceback -- and the message names both ways out."""
    env, _ = clean_env

    result = run(["-m", "ovi.ovi", "--headless", "--do-not-open"], env)

    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert "--headless" in result.stderr
    assert "VAULT_PATH" in result.stderr


def test_setup_flag_is_never_satisfied_by_a_bootstrap(clean_env, make_vault):
    """--setup asks for the screen; headless cannot show it, and must not
    quietly write a config instead."""
    env, data = clean_env
    vault = make_vault({"Note.md": "text\n"})

    result = run(["-m", "ovi.ovi", "--headless", "--setup", "--do-not-open", str(vault)], env)

    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert not (data / "CONFIG.yaml").exists()

"""End-to-end: the real SysConfig, the real CLI, no Obsidian and no window.

Everything else in the suite goes through StubSysConfig, which is why the
platform bugs in SysConfig survived a green CI on all three runners. This test
runs ``ovi --headless --do-not-open`` in a child process whose home
directory is an empty temp folder -- so there is no obsidian.json to find --
and whose spreadsheet application is blank. That is exactly the state of a
fresh install on a Mac or a Linux box, and it used to fail before the setup
screen could open.

The one thing a headless run cannot do is complete setup, so CONFIG.yaml is
written first through the documented seam: a SysConfig subclass whose
run_setup_ui() saves instead of opening a window.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

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
    env, data = clean_env
    vault = make_vault({"Note.md": "---\ntitle: Hello\ntags: [a]\n---\nBody #tag\n"},
                       name="Fresh Vault")

    # Step 1: complete "setup" the way a test or a CI job is allowed to.
    bootstrap = (
        "from ovi.ovi_setup import SysConfig\n"
        "class S(SysConfig):\n"
        "    def run_setup_ui(self):\n"
        "        self.save_config()\n"
        f"S(interactive=False, vault_path_override={str(vault)!r})\n"
    )
    result = run(["-c", bootstrap], env)
    assert result.returncode == 0, result.stderr
    assert (data / "CONFIG.yaml").is_file()

    # Step 2: the real command line, exactly as a script would call it.
    result = run(["-m", "ovi.ovi", "--headless", "--do-not-open", "-d", "WARNING", str(vault)], env)

    assert result.returncode == 0, result.stderr
    assert "Traceback" not in result.stderr
    workbooks = list((data / "data" / "workbooks").glob("ovi_Fresh_Vault_*.xlsx"))
    assert len(workbooks) == 1, result.stdout + result.stderr


def test_headless_run_without_setup_says_what_to_do(clean_env, make_vault):
    """No CONFIG.yaml and --headless: a one-line error, exit 1, no traceback."""
    env, _ = clean_env
    vault = make_vault({"Note.md": "text\n"})

    result = run(["-m", "ovi.ovi", "--headless", "--do-not-open", str(vault)], env)

    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert "--headless" in result.stderr

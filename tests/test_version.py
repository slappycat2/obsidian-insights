"""Tests that the version stays single-sourced.

These exist because of a real mess. Before 0.1.0 the project reported four
different versions at once: `__version__` said 0.3.0, the Summary tab title
said "v1.0", the Summary hyperlink said "v.0.9 (beta)", and SysConfig restored
`sys_ver` from CONFIG.yaml -- which on the author's machine still said 0.2.9, so
that was the number the running app actually used.

Nothing here checks *which* version is correct. They check that there is only
one of it, which is the property that kept breaking.
"""

import re
import tomllib
from pathlib import Path

import pytest

from ovi import __version__

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_version_is_semver():
    """The release protocol in docs/VERSIONING.md assumes MAJOR.MINOR.PATCH.

    A suffix like "0.9 (beta)" or "v0_5" is exactly the drift this pins.
    """
    assert SEMVER.match(__version__), f"not a semver string: {__version__!r}"


def test_pyproject_does_not_hardcode_a_version():
    """hatchling must read the version from the package, not carry its own.

    The two disagreed for a whole release cycle -- pyproject said 0.2.0 while
    the package said 0.3.0.
    """
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert "version" not in pyproject["project"], "pyproject.toml pins its own version"
    assert "version" in pyproject["project"]["dynamic"]
    assert pyproject["tool"]["hatch"]["version"]["path"] == "src/ovi/__init__.py"


def test_installed_metadata_matches_the_package():
    """`uv sync` installs the project, so importlib.metadata is a second copy of
    the number. A stale editable install shows up here."""
    from importlib.metadata import version

    assert version("obsidian-insights") == __version__


def test_summary_tab_strings_are_derived_not_hardcoded():
    """The Summary tab announces the version twice, in the title and in a
    hyperlink. Both used to be string literals that nobody remembered to edit."""
    source = (REPO_ROOT / "src" / "ovi" / "ovi_wb_tabs.py").read_text(encoding="utf-8")

    assert "f'Obsidian Insights v{__version__}'" in source
    assert '"v{__version__}"' in source


@pytest.mark.parametrize("module", ["ovi_wb_tabs.py", "ovi_setup.py", "ovi.py",
                                    "ovi_splash.py"])
def test_no_stray_version_literals(module):
    """No module that displays a version may contain a bare version literal.

    Deliberately narrow: it looks for v-prefixed literals like "v1.0" or
    "v.0.9", not every number in the file, so plugin and Obsidian versions
    (e.g. "Deprecated in Obsidian 1.4") are unaffected.
    """
    source = (REPO_ROOT / "src" / "ovi" / module).read_text(encoding="utf-8")

    strays = re.findall(r"""['"]v\.?\d+\.\d+""", source)

    assert not strays, f"{module} hardcodes a version: {strays}"


def test_sys_ver_is_not_restored_from_config():
    """SysConfig.cfg_unpack must take the version from the running code.

    Restoring it from CONFIG.yaml pinned the reported version to whatever wrote
    the file first -- a 0.2.9 config made 0.3.0 report 0.2.9.
    """
    source = (REPO_ROOT / "src" / "ovi" / "ovi_setup.py").read_text(encoding="utf-8")

    assert "self.sys_ver            = __version__" in source
    assert "self.sys_cfg.get('sys_ver'" not in source

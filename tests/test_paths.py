"""Tests for v_chk_paths.

These exist because of a real failure: an unanchored `vault_check/` rule in
.gitignore matched src/vault_check/ as well as the intended leftover directory.
Hatchling honours .gitignore, so the built wheel contained nothing but metadata
-- no modules, no assets -- and src/vault_check/__init__.py was never committed
at all. Nothing failed locally, because the editable install resolves imports
straight from the source tree.

Asserting that every packaged asset resolves is the cheap half of the guard.
The other half lives in CI, which builds a wheel and checks its contents.
"""

import os
from pathlib import Path

import pytest

from vault_check import v_chk_paths as paths

ASSET_CONSTANTS = (
    "LOGO_SPLASH",
    "LOGO_SETUP",
    "ICON_WINDOW",
    "BANNER",
    "AREA51",
)


@pytest.mark.parametrize("constant", ASSET_CONSTANTS)
def test_packaged_asset_exists(constant):
    """Every asset the code can reference must actually ship with the package.

    This also pins the filenames' capitalisation. Windows resolves
    'swenlogo200.png' to 'SwenLogo200.png' happily; macOS and Linux do not.
    """
    asset = getattr(paths, constant)

    assert isinstance(asset, Path)
    assert asset.is_file(), f"{constant} does not exist: {asset}"


def test_assets_live_inside_the_package():
    """Assets must resolve relative to the package, not the working directory,
    so they still work when installed as a wheel."""
    for constant in ASSET_CONSTANTS:
        assert paths.PACKAGE_DIR in getattr(paths, constant).parents


def test_active_logging_config_exists():
    from vault_check.v_chk_logger import ACTIVE_LOG_CONFIG

    assert (paths.LOGGING_CONFIG_DIR / ACTIVE_LOG_CONFIG).is_file()


def test_all_logging_configs_are_packaged():
    """The alternative dictConfigs are part of the package, not stray files."""
    configs = list(paths.LOGGING_CONFIG_DIR.glob("*.json"))

    assert configs, "no logging configs found"
    assert all(paths.PACKAGE_DIR in c.parents for c in configs)


def test_data_root_honours_the_environment_override():
    """conftest sets V_CHK_DATA_DIR before importing vault_check; this is the
    seam the whole test suite depends on for isolation."""
    override = os.environ.get(paths.DATA_DIR_ENV_VAR)

    assert override, "V_CHK_DATA_DIR should be set during the test run"
    assert paths.DATA_ROOT == Path(override).expanduser().resolve()


def test_generated_output_stays_out_of_the_package():
    """A pip-installed package may sit in a read-only site-packages, so nothing
    writable may resolve inside it."""
    for writable in (paths.CONFIG_FILE, paths.DATA_DIR, paths.LOG_DIR,
                     paths.BATCH_DIR, paths.WORKBOOK_DIR):
        assert paths.PACKAGE_DIR not in writable.parents


def test_ensure_runtime_dirs_is_idempotent():
    paths.ensure_runtime_dirs()
    paths.ensure_runtime_dirs()  # must not raise on the second call

    for directory in paths.RUNTIME_DIRS:
        assert directory.is_dir()

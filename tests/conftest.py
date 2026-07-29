"""Shared pytest fixtures for the v_chk test suite.

Two things make this suite possible without a real Obsidian installation:

* ``V_CHK_DATA_DIR`` redirects all generated output into a throwaway directory.
  v_chk_paths resolves DATA_ROOT once, at import time, so the variable has to be
  set before ``vault_check`` is first imported. ``pytest_configure`` runs before
  test modules are collected and imported, which is early enough.

* ``StubSysConfig`` stands in for the real SysConfig, which would read the
  machine's obsidian.json and open a Tk window.
"""

import os
import platform
import shutil
import tempfile
from pathlib import Path
from textwrap import dedent

import pytest

_TMP_DATA_ROOT: str | None = None


def pytest_configure(config):
    global _TMP_DATA_ROOT
    _TMP_DATA_ROOT = tempfile.mkdtemp(prefix="v_chk_tests_")
    os.environ["V_CHK_DATA_DIR"] = _TMP_DATA_ROOT


def pytest_unconfigure(config):
    if _TMP_DATA_ROOT:
        shutil.rmtree(_TMP_DATA_ROOT, ignore_errors=True)
        os.environ.pop("V_CHK_DATA_DIR", None)


class StubSysConfig:
    """Stand-in for SysConfig.

    Every stage reads ``sys_obj.sys_cfg``, never SysConfig's attributes, so the
    tests supply that dict directly. Constructing a real SysConfig would read
    the machine's obsidian.json and open a Tk setup window.

    The keys mirror SysConfig.cfg_pack() exactly. If a stage starts raising
    KeyError here, cfg_pack() has grown a key that this stub has not.
    """

    def __init__(self, vault_dir, **overrides):
        from vault_check import v_chk_paths as paths
        from vault_check.v_chk_setup import DEFAULT_TAB_SEQ

        paths.ensure_runtime_dirs()
        vault_dir = Path(vault_dir)

        self.sys_cfg = {
            "sys_id": "v_chk_test",
            "sys_ver": "test",
            "sys_dir_sys": str(paths.DATA_ROOT),
            "sys_dir_dat": str(paths.DATA_DIR),
            "sys_dir_bat": str(paths.BATCH_DIR),
            "sys_dir_wbs": str(paths.WORKBOOK_DIR),
            "sys_dir_log": str(paths.LOG_DIR),
            "sys_dir_img": str(paths.ASSETS_DIR),
            "sys_pn_cfg": str(paths.CONFIG_FILE),
            "sys_pn_wb_exec": "",
            "sys_pn_batch": "",
            "sys_pn_wbs": "",
            "sys_tab_seq": list(DEFAULT_TAB_SEQ),
            "sys_cfg_os": platform.system(),
            "cur_vlts": {},
            "sys_vlts": {},
            "sys_pn_lg2": str(paths.LOGO_SPLASH),
            "sys_pn_lg3": str(paths.LOGO_SETUP),
            "sys_pn_ico": str(paths.ICON_WINDOW),
            "sys_pn_bnr": str(paths.BANNER),
            "sys_pn_a51": str(paths.AREA51),
            "sys_splash_bg": "#800000",
            "vault_name": vault_dir.name,
            "vault_id": "testvaultid",
            "dir_vault": str(vault_dir),
            "dir_templates": None,
            "skip_rel_str": "",
            "skip_abs_lst": [],
            "dirs_dot": [],
            "ctot": [0] * 13,
            "bool_shw_notes": True,
            "bool_rel_paths": True,
            "bool_summ_rows": True,
            "bool_unused_1": False,
            "bool_unused_2": False,
            "bool_unused_3": False,
            "link_lim_vals": 0,
            "link_lim_tags": 0,
            "v_chk_date": "2026-01-01 00:00:00",
        }
        self.sys_cfg.update(overrides)


@pytest.fixture
def stub_config():
    """The StubSysConfig class itself, for tests that build one directly."""
    return StubSysConfig


@pytest.fixture
def make_vault(tmp_path):
    """Build a throwaway vault from a {relative path: markdown text} mapping.

    Content is dedented, so tests can use triple-quoted strings at their natural
    indentation.
    """

    def _make(files, name="TestVault"):
        vault = tmp_path / name
        vault.mkdir(parents=True, exist_ok=True)

        for relative_path, content in files.items():
            target = vault / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(dedent(content).lstrip(), encoding="utf-8")

        return vault

    return _make


@pytest.fixture
def scan(make_vault):
    """Run a full VaultHealthCheck over an ad-hoc vault and return it."""

    def _scan(files, **overrides):
        from vault_check.v_chk_build import VaultHealthCheck

        vault = make_vault(files)
        return VaultHealthCheck(StubSysConfig(vault, **overrides))

    return _scan

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Obsidian Vault Health Check (`v_chk`) — a local, read-only scanner that walks every `.md` file in an
Obsidian vault, harvests frontmatter properties, inline (`key:: value`) properties, tags, code blocks,
duplicate filenames and unparseable YAML, then emits a multi-tab, heavily-formatted `.xlsx` workbook
with hyperlinks back into the vault. Nothing is written to the vault and nothing leaves the machine.

## Where the live code is

Only `vault_check/src/` is live. Everything else is noise you should not edit or take as reference:

- `xcluded/` — abandoned/scratch versions of most modules (`v_chk.py`, `x_chk*.py`, `v_chk_class_lib.py`, …).
  Names collide with live modules; never import from here or use it to answer "how does X work".
- `pkg/src/obsidian_vault_health_check_swenlarsen/` — empty packaging stub.
- `main.py` (repo root) — hello-world placeholder, not an entry point.
- `tests/batch_test_vaults.py` — an interactive batch-runner script, not a test suite. It imports
  `src.v_chk_class_lib` and calls `SysConfig` methods that no longer exist, so it does not run as-is.
  There is no pytest/unittest setup in this repo.

## Running it

Dependencies are managed with `uv` (`uv.lock`, Python 3.13 pinned in `.python-version`).

```powershell
uv sync
```

**The working directory must be `vault_check/`, and `vault_check/src/` must be on `sys.path`.**
Both are load-bearing and neither is configurable:

- `SysConfig.set_path_vars()` derives every path from `Path.cwd()` — `CONFIG.yaml`, `data/`,
  `data/batch_files/`, `data/workbooks/`, `data/logs/`, `img/`.
- `v_chk_logger.setup_logging()` opens the literal relative path `src/logging_configs/1-stderr-file.json`,
  and that config writes to the relative path `logs/v_chk.log`.
- All intra-project imports are flat module names (`from v_chk_setup import SysConfig`), so `src/`
  itself must be importable.

```powershell
cd vault_check
$env:PYTHONPATH = "src"; uv run python -c "import v_chk; v_chk.main()"
```

The PyCharm run config (`.idea/workspace.xml`) runs `vault_check/src/v_chk.py` with
`ADD_SOURCE_ROOTS=true` and a vault path as its argument.

To reach the setup GUI directly: `uv run python src/v_chk_setup.py` (from `vault_check/`).

### The CLI entry point is currently broken

`v_chk.py`'s `__main__` calls `cli()`, but the `cli()` body only assigns the `CLI_*` globals — it never
calls `main()`, so `python src/v_chk.py <vault>` echoes its flags and exits. Also in that module:
`run_main()` references an undefined `OPEN_ON_CREATE`, and `init()` uses `os` without importing it.
The working pipeline is `main()` → `run_main()`. Expect to fix the wiring before any CLI change is testable.

## Pipeline

`v_chk.main()` builds `SysConfig`, opens a Tk splash screen, and drives four stages via
`run_main()`; the splash owns the mainloop, so the whole run happens inside a `splash.after()` callback.

1. **`SysConfig`** (`v_chk_setup.py`) — dataclass holding all system + per-vault settings. Reads/writes
   `CONFIG.yaml`. Delegates vault discovery to `ObsidianApp` (`v_chk_obs_app.py`), which parses Obsidian's
   own `obsidian.json` (`%APPDATA%/obsidian/` on Windows, `~/.config/obsidian/` Linux,
   `~/Library/Application Support/obsidian/` macOS) to build `sys_vlts`/`cur_vlts` and pick the last-open
   vault as the default. If `CONFIG.yaml` is missing or `chk_fields_on_load()` fails, the Tk `SetupScreen`
   (`v_chk_setupscreen.py`) is shown before anything else runs.
2. **`VaultHealthCheck`** (`v_chk_build.py`) — `rglob("*.md")` over the vault; per file it strips code
   blocks / inline code / Templater tags, splits frontmatter from body on `^---$`, `yaml.safe_load`s the
   frontmatter, regex-scans the body for `key:: value` and `#tags`, and accumulates into the `obs_*` dicts.
3. **`NewWb`** (`v_chk_wb_tabs.py`) — turns the harvested data plus per-tab layout metadata into a
   complete cell-level tab definition for each tab.
4. **`ExcelExporter`** (`v_chk_xl.py`) — walks `sys_tab_seq` and renders each tab into an openpyxl
   workbook (tables, conditional formatting, `obsidian://` hyperlinks, images), saves it, and `Popen`s
   the configured spreadsheet executable.

### Stages talk through a YAML file, not objects

Each stage re-reads `wb_def` from disk rather than passing it in memory. `WbDataDef` (`v_chk_wb_setup.py`)
allocates the next sequential batch file `data/batch_files/v_chk_NNNN.yaml` (and the matching
`data/workbooks/v_chk_NNNN.xlsx`), and `write_bat_data()` / `read_wb_data()` are the handoff. `NewWb` and
`ExcelExporter` both begin with `read_wb_data()`. Consequence: anything you add to `wb_def` must be
`yaml.dump`-able, and stale batch files are the first thing to check when a run produces odd output.

`wb_def` has exactly three keys:

- `sys_cfg` — the packed `SysConfig` dict (also carries `ctot`, `sys_pn_batch`, `sys_pn_wbs`).
- `wb_data` — the harvested vault data: `obs_props`, `obs_atags`, `obs_xyaml`, `obs_dupfn`, `obs_files`,
  `obs_tmplt`, `obs_codes`, `obs_nests`, `obs_plugs`.
- `wb_tabs` — keyed by tab id; each value is a `tab_def` dict.

The `obs_*` dicts are all shaped `{key: {value: [filepath, ...]}}` (see `upd_obs_props`); `obs_files` and
`obs_nests` use `{filepath|F-or-I: {key: [values]}}` and `{plugin_id|filepath: {key: [values]}}`.

## The tab system

Tabs are identified by 4-character ids: `pros vals tags file code xyml dups tmpl nest plug summ ar51`.
Adding or renaming one touches **five** places, and a mismatch raises or silently drops the tab:

1. `NewWb.tab_common` (`v_chk_wb_tabs.py`) — display name, titles, help text, `data_src`.
2. A `DefXxxx(NewTab)` subclass in the same file, which fills in `tab_def` and calls `tab_def_post()`.
3. The `if/elif` dispatch chain in `NewWb.__init__` — an unknown key raises `Unexpected key`.
4. `WbDataDef.get_next_bat()`'s `wb_tabs` dict (`v_chk_wb_setup.py`).
5. `Colors.init_tab_clrs()` (`v_chk_colors.py`) — keyed by tab id; a missing entry is a `KeyError`.

Render order and inclusion come from `sys_cfg['sys_tab_seq']`, whose default list is duplicated in both
`SysConfig.__post_init__` and `SysConfig.cfg_unpack`.

`NewTab` is the base class: it defines table naming (`tbl_<tab_id>`), the header row/column origin, the
`RowId` / `IsVisible` / `P-V Index` helper columns, and the Excel formula strings (`f_uniq_*`, `f_txt_*`,
`f_num_*`) that make tab totals respect table filters via `AGGREGATE`/`SUBTOTAL`. `calc_col_pointers()`
and `set_table_links()` compute where the variable-width "FileNN" hyperlink columns land — the count comes
from `ctot[11]`/`ctot[12]` (max links seen) capped by the user's `link_lim_vals`/`link_lim_tags`.

### Cell definition convention

Cells are plain 11-element lists shared between `v_chk_wb_tabs.py` and `v_chk_xl.py`:

```
[col, row, font, size, width, text_clr, fill_clr, bold, italic, align, value]
```

`ExcelExporter.export_cell()` consumes them positionally, so element order is a hard contract.
`Colors.get_tab_clrs(tab_id)` returns `(clr1, txt1, clr2, txt2, table_style)` and is where fills come from.

### `ctot` counters

`sys_cfg['ctot']` is a 13-slot list of counters incremented throughout `v_chk_build.py` and consumed by
the Summary tab. Slots: `0` md files seen, `1` templates skipped, `2` skip-dir files skipped, `3` files
processed, `4` NestedDictionary resets, `5` files with frontmatter, `6` files with body properties,
`7` `upd_obs_files` calls, `8` `upd_obs_nests` calls, `9` `upd_obs_props` calls, `10` files with no
frontmatter at all, `11` max links per property value, `12` max links per tag.

## Other conventions worth knowing

- **Nested YAML means a plugin.** Obsidian doesn't allow nested frontmatter dicts, so `unpack_yaml()`
  treats one as plugin-managed data and routes it to `obs_nests` under a plugin id resolved from
  `WbDataDef.plugin_id_def` (falling back to `NestedDictionary`). `PluginMan` (`v_chk_plugin_man.py`)
  separately reads `.obsidian/plugins/*/manifest.json` + `community-plugins.json` for the Plugins tab and
  maps code-block signatures (`dataview`, `button`, …) to plugin ids.
- **Bad frontmatter is classified, not dropped** — `obs_xyaml` codes `BadY` / `NoFm` / `MtFm` / `ErrY` /
  `NonD`, described in `WbDataDef.xyml_descs`.
- **Everything is lowercased** for grouping; the original casing is preserved in `actual_prop_key` and
  surfaced only on the Files tab.
- **Logging**: `from v_chk_logger import logger` everywhere; `make_logger()` is called once in `v_chk.main()`.
  Swap the active handler config by changing the `config_file` line in `v_chk_logger.setup_logging()`
  (alternatives live in `src/logging_configs/`). Logs rotate at 3 MB, 50 backups.
- **Version strings are duplicated and already out of sync**: `click.version_option("0.2.9")` in
  `v_chk.py`, `SysConfig.sys_ver = '0.2.9'`, and `version = "0.2.0"` in `pyproject.toml`.
- `v_chk_xl.py` carries a long inline Bug-NNN / ER-NNN todo list at the top of the file; that is the
  project's de-facto issue tracker.

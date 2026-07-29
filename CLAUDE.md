# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Obsidian Vault Health Check (`v_chk`) — a local, read-only scanner that walks every `.md` file in an
Obsidian vault, harvests frontmatter properties, inline (`key:: value`) properties, tags, code blocks,
duplicate filenames and unparseable YAML, then emits a multi-tab, heavily-formatted `.xlsx` workbook
with hyperlinks back into the vault. Nothing is written to the vault and nothing leaves the machine.

## Layout

Standard `src/` layout. The package is installed into the venv by `uv sync`, so imports resolve to
the installed copy rather than to whatever directory you happen to be standing in.

```
main.py                      entry point for source checkouts
pyproject.toml               version lives in src/vault_check/__init__.py (hatchling reads it)
src/vault_check/             the package -- all live code
    assets/                  runtime images (logos, banner, area51)
    logging_configs/         JSON/YAML logging dictConfigs
tests/                       pytest suite
CHANGELOG.md                 user-facing history; keep [Unreleased] current as work lands
docs/VERSIONING.md           versioning protocol and release checklist
docs/BACKLOG.md              historical record of the backlog now tracked as GitHub issues
docs/WORKING-NOTES.md        repo/process to-dos and session working agreements
img/                         README screenshot and brand source files (not runtime)
data/, logs/, CONFIG.yaml    generated at runtime, gitignored
```

Everything tracked is live — 63 files, 6 MB. The two directories that used to linger untracked on
disk (`vault_check/`, pre-Phase-2 generated output, and `xcluded/`, old scratch code removed from
tracking in Phase 4) are both gone; `xcluded/` remains recoverable from commit `d24449d`.

### Keep .gitignore patterns anchored

Root-only rules in `.gitignore` **must** start with `/` — `/data/`, `/logs/`, `/CONFIG.yaml`,
`/vault_check/`. An unanchored pattern matches at every depth, and `vault_check/` therefore also
matched `src/vault_check/`, the package itself. The damage was entirely silent: `git add -A` skipped
`__init__.py` without a word, and because hatchling honours `.gitignore`, `uv build` produced a wheel
containing only `dist-info` metadata — no modules, no assets. Nothing failed locally, because the
editable install resolves imports from the source tree regardless.

Guarded now by `tests/test_paths.py` (assets resolve) and a CI step that builds a wheel and asserts
its contents. If you add a directory to `.gitignore`, anchor it and run `uv build --wheel`.

## Running it

Dependencies are managed with `uv` (`uv.lock`, Python 3.13 pinned in `.python-version`).

```powershell
uv sync
uv run v-chk --help
uv run v-chk                                    # vault last opened in Obsidian
uv run v-chk "D:/Vaults/o26"                  # a specific vault
uv run v-chk --headless --do-not-open <vault>   # no GUI, no Excel launch
```

`uv sync` installs the project itself (`[project.scripts] v-chk = "vault_check.v_chk:main"`), which is
what makes the `v-chk` command and clean `vault_check.*` imports work. `python main.py [...]` is
equivalent. **After changing `pyproject.toml`, re-run `uv sync`** — PyCharm's Run button invokes
`.venv\Scripts\python.exe` directly and never consults uv or the lockfile.

**Paths never depend on the working directory.** Everything resolves through `v_chk_paths.py`, which
separates *package assets* (relative to `__file__`) from *writable data* (`DATA_ROOT`). Run it from
anywhere. Do not reintroduce `Path.cwd()`.

`DATA_ROOT` resolution order: `$V_CHK_DATA_DIR` → the repo root when running from a source checkout
(detected via `pyproject.toml`) → `~/.v_chk`. Tests set the env var to redirect into a `tmp_path`.

Useful flags: `--headless` (never open a window; raises `ConfigIncompleteError` rather than blocking
on a dialog), `-q/--no-splash`, `-x/--do-not-open`, `-s/--setup` (force the setup screen),
`-i/--init` (delete CONFIG.yaml, batch files and workbooks; prompts first), `-d/--debug-level`.

To reach the setup GUI directly: `uv run python -m vault_check.v_chk_setup`.

## Tests

```powershell
uv run pytest                                   # whole suite (~2s)
uv run pytest tests/test_vault_parsing.py       # one file
uv run pytest -k wikilink                       # by name
uv run pytest -q tests/test_pipeline.py::test_workbook_is_created
```

Two seams make the suite possible without an Obsidian install or a GUI:

- `conftest.pytest_configure` sets `V_CHK_DATA_DIR` to a temp dir **before** any
  test module imports `vault_check`. This matters because `v_chk_paths` resolves
  `DATA_ROOT` once, at import time — setting the variable inside a fixture would be too late.
- `StubSysConfig` (in `conftest.py`) supplies the `sys_cfg` dict directly. Every stage reads that
  dict rather than SysConfig's attributes, so no real SysConfig is needed. Its keys mirror
  `cfg_pack()`; **if a stage starts raising `KeyError` in tests, `cfg_pack()` gained a key the stub
  lacks.**

`tests/` is not a package — share helpers through fixtures, not `from tests.conftest import ...`.

`test_vault_parsing.py` covers the markdown/YAML harvesting in isolation; `test_pipeline.py` runs all
four stages and asserts against the real `.xlsx`. Several tests are named as regressions and cite the
bug they pin — keep that habit.

### First run requires the GUI

`CONFIG.yaml` is generated by the Tk setup screen, so a machine without one cannot run `--headless`
until setup has been completed once. `SysConfig(interactive=False)` raises `ConfigIncompleteError`
instead of opening a window. To create a config non-interactively (tests, CI), subclass `SysConfig`
and override `run_setup_ui()` to call `self.save_config()`.

## Pipeline

`run_pipeline(sys_cfg_obj, progress)` in `v_chk.py` drives the four stages and requires no GUI —
that is what makes the code testable. `run_with_splash()` wraps it, passing `SplashScreen.update_status`
as the progress callback; the splash owns the Tk mainloop, so the work happens inside a
`splash.after()` callback and exceptions are captured and re-raised after the loop exits.

1. **`SysConfig`** (`v_chk_setup.py`) — dataclass holding all system + per-vault settings. Reads/writes
   `CONFIG.yaml`. **Downstream stages read the packed `sys_cfg` dict, not these attributes**, so any
   attribute change made after `load_config()` must be followed by `cfg_pack()` or it is silently
   ignored (this is why `select_vault_by_path()` calls it). Delegates vault discovery to
   `ObsidianApp` (`v_chk_obs_app.py`), which parses Obsidian's
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

Render order and inclusion come from `sys_cfg['sys_tab_seq']`, defaulting to `DEFAULT_TAB_SEQ` in
`v_chk_setup.py`.

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
the Summary tab. Slots: `0` md files seen, `1` templates seen, `2` skip-dir files skipped, `3` files
processed, `4` NestedDictionary resets, `5` files with frontmatter, `6` files with body properties,
`7` `upd_obs_files` calls, `8` `upd_obs_nests` calls, `9` `upd_obs_props` calls, `10` files with no
frontmatter at all, `11` max links per property value, `12` max links per tag.

## Other conventions worth knowing

- **Nested YAML means a plugin.** Obsidian doesn't allow nested frontmatter dicts, so `unpack_yaml()`
  treats one as plugin-managed data and routes it to `obs_nests` under a plugin id resolved from
  `WbDataDef.plugin_id_def` (falling back to `NestedDictionary`). The routing decision is
  **structural** — `upd_val()` tests whether `key_stack` is non-empty, i.e. whether it is currently
  inside a nested dict. It must not go back to testing `plugin_id`, which is a whole-file text scan:
  that swallowed a plugin-touched note's genuine top-level properties, tags and inline fields.
  `plugin_id` names the bucket only.
- **Templates are read, but reach only the Templates tab.** Files under the Templater folder are
  harvested into `obs_tmplt` and deliberately kept out of every other sink — Properties, Tags,
  Files, nested-plugin data, code blocks, duplicate filenames and the bad-YAML tab (`record_yaml_issue()`
  is a no-op for them, since Templater syntax isn't valid YAML). They count in `ctot[1]`, not `ctot[3]`. `PluginMan` (`v_chk_plugin_man.py`)
  separately reads `.obsidian/plugins/*/manifest.json` + `community-plugins.json` for the Plugins tab and
  maps code-block signatures (`dataview`, `button`, …) to plugin ids.
- **Bad frontmatter is classified, not dropped** — `obs_xyaml` codes `BadY` / `NoFm` / `MtFm` / `ErrY` /
  `NonD`, described in `WbDataDef.xyml_descs`.
- **Everything is lowercased** for grouping; the original casing is preserved in `actual_prop_key` and
  surfaced only on the Files tab.
- **Logging**: `from v_chk_logger import logger` everywhere; `make_logger(level)` is called once, by
  `cli()`. Swap the active handler config via `ACTIVE_LOG_CONFIG` (alternatives live in
  `src/vault_check/logging_configs/`). Those JSON files declare relative log paths, which `_resolve_handler_paths()`
  rewrites to absolute under `APP_DIR`. Logs rotate at 3 MB, 50 backups, into `logs/`.
- **The version is single-sourced** from `__version__` in `src/vault_check/__init__.py` — see
  `docs/VERSIONING.md` for the protocol and release steps. `pyproject.toml` declares
  `dynamic = ["version"]`; the CLI's `--version`, the splash, `SysConfig.sys_ver` and both Summary
  tab strings all derive from it, and `tests/test_version.py` fails if any of them stops doing so.
  Never type a version literal anywhere else. Bumping `__version__` needs
  `uv sync --reinstall-package obsidian-vault-health-check`, or the installed metadata stays stale.
- **Empty tabs are dropped**, not rendered: `ExcelExporter.initialize_all_tabs()` skips any tab whose
  `data_src` is empty and rewrites `sys_tab_seq` to the surviving list. A vault with no Templater
  folder configured, or no nested plugin data, legitimately produces 10 sheets rather than 12.
- **Outstanding work lives in GitHub issues**, not in code comments. A ~90-line `Bug-NNN` / `ER-NNN`
  block at the top of `v_chk_xl.py` (whose own Bug-022 asked for exactly this) became
  `docs/BACKLOG.md`, which in turn became issues #1–#25 on 2026-07-29. `docs/BACKLOG.md` is now a
  frozen historical record — file new work on the tracker, and do not reintroduce todo lists in
  source files. The one exception is `docs/WORKING-NOTES.md`, which tracks repo administration, CI
  upkeep and open decisions — things with no code to attach an issue to. Keep code defects out of it.

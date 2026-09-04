# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Obsidian Insights (`ovi`) — a local, read-only scanner that walks every `.md` file in an
Obsidian vault, harvests frontmatter properties, inline (`key:: value`) properties, tags, code blocks,
duplicate filenames and unparseable YAML, then emits a multi-tab, heavily-formatted `.xlsx` workbook
with hyperlinks back into the vault. Nothing is written to the vault and nothing leaves the machine.

## Layout

Standard `src/` layout. The package is installed into the venv by `uv sync`, so imports resolve to
the installed copy rather than to whatever directory you happen to be standing in.

```
main.py                      entry point for source checkouts
pyproject.toml               version lives in src/ovi/__init__.py (hatchling reads it)
src/ovi/                     the package -- all live code
    assets/                  runtime images (logos, banner, area51)
    logging_configs/         JSON/YAML logging dictConfigs
tests/                       pytest suite
CHANGELOG.md                 user-facing history; keep [Unreleased] current as work lands
docs/VERSIONING.md           versioning protocol and release checklist
docs/BACKLOG.md              historical record of the backlog now tracked as GitHub issues
docs/WORKING-NOTES.md        repo/process to-dos and working agreements -- untracked, see below
tools/ui_shot.py             dev-only: photographs the Tk setup screen and dumps its widget tree
tools/var_dictionary.py      dev-only: ast-walks the package into a variable-dictionary workbook
tools/var_purposes.py            the hand-written descriptions that workbook uses
img/                         README screenshot and brand source files (not runtime)
data/, logs/, CONFIG.yaml    generated at runtime, gitignored
```

Everything tracked is live. The repository history was rewritten on 2026-09-04 before publication:
the old scratch directory `xcluded/`, a batch-vault test script and the working notes were removed
from every commit, so none of them is recoverable from history any more.

### Keep .gitignore patterns anchored

Root-only rules in `.gitignore` **must** start with `/` — `/data/`, `/logs/`, `/CONFIG.yaml`,
`/vault_check/`. An unanchored pattern matches at every depth, and `vault_check/` therefore also
matched `src/vault_check/`, the package itself (it has since been renamed `src/ovi/`, and an
unanchored `ovi/` would do the same). The damage was entirely silent: `git add -A` skipped
`__init__.py` without a word, and because hatchling honours `.gitignore`, `uv build` produced a wheel
containing only `dist-info` metadata — no modules, no assets. Nothing failed locally, because the
editable install resolves imports from the source tree regardless.

Guarded now by `tests/test_paths.py` (assets resolve) and a CI step that builds a wheel and asserts
its contents. If you add a directory to `.gitignore`, anchor it and run `uv build --wheel`.

## Running it

Dependencies are managed with `uv` (`uv.lock`, Python 3.13 pinned in `.python-version`).

```powershell
uv sync
uv run ovi --help
uv run ovi                                    # vault last opened in Obsidian
uv run ovi "D:/Vaults/MyVault"                # a specific vault
uv run ovi --headless --do-not-open <vault>   # no GUI, no Excel launch
```

`uv sync` installs the project itself (`[project.scripts] ovi = "ovi.ovi:main"`), which is
what makes the `ovi` command and clean `ovi.*` imports work. `python main.py [...]` is
equivalent. **After changing `pyproject.toml`, re-run `uv sync`** — PyCharm's Run button invokes
`.venv\Scripts\python.exe` directly and never consults uv or the lockfile.

**Paths never depend on the working directory.** Everything resolves through `ovi_paths.py`, which
separates *package assets* (relative to `__file__`) from *writable data* (`DATA_ROOT`). Run it from
anywhere. Do not reintroduce `Path.cwd()`.

`DATA_ROOT` resolution order: `$OVI_DATA_DIR` → the repo root when running from a source checkout
(detected via `pyproject.toml`) → `~/.ovi`. Tests set the env var to redirect into a `tmp_path`.

Useful flags: `--headless` (never open a window; raises `ConfigIncompleteError` rather than blocking
on a dialog), `-q/--no-splash`, `-x/--do-not-open`, `-s/--setup` (force the setup screen),
`-i/--init` (delete CONFIG.yaml, batch files and workbooks; prompts first), `-d/--debug-level`.

To reach the setup GUI directly: `uv run python -m ovi.ovi_setup`.

## Tests

```powershell
uv run pytest                                   # whole suite (~2s)
uv run pytest tests/test_vault_parsing.py       # one file
uv run pytest -k wikilink                       # by name
uv run pytest -q tests/test_pipeline.py::test_workbook_is_created
```

Two seams make the suite possible without an Obsidian install or a GUI:

- `conftest.pytest_configure` sets `OVI_DATA_DIR` to a temp dir **before** any
  test module imports `ovi`. This matters because `ovi_paths` resolves
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
and override `run_setup_ui()` to call `self.save_config()` — `tests/test_headless_cli.py` does
exactly this in a child process with an empty home directory, and is the one test that runs the
real `SysConfig` and the real command line.

**Only the two GUI modules may import tkinter at module scope** (`ovi_setupscreen.py`,
`ovi_splash.py`). `ovi_setup.py` imports `SetupScreen` inside a `try`, `ovi.py` imports the splash
inside `run_with_splash()`, and `ExcelExporter.retry_file_removal()` imports `messagebox` when
called — so `--headless` runs on a Python built without Tk (system Python on Debian without
`python3-tk`), and `run_setup_ui()` names the package to install when it is missing.
`tests/test_platform.py` parses the non-GUI modules and fails on a top-level tkinter import.

**Platform branches live in two places and are unit-tested from every OS.** `ovi_launch.py` owns
the spreadsheet application: `default_spreadsheet_app()`, `validate_app()` and `launch_command()`
all take a `system` argument. Blank means the system default handler; a macOS `.app` bundle is a
directory launched with `open -a`; a bare Linux command is resolved with `shutil.which()`.
`ovi_obs_app.candidate_config_dirs()` lists where `obsidian.json` may be (Windows `%APPDATA%`,
macOS `~/Library/Application Support`, Linux `$XDG_CONFIG_HOME`, `~/.config`, Flatpak, Snap); a
missing file is a warning, never an exception. `sys_cfg_os` is recomputed in `cfg_unpack()` like
the paths — a fact about the machine, not a setting.

**The user is allowed to say no.** `SetupScreen.show()` returns True only if "Save & Run" was
pressed; Cancel and the window's close button both return False, and `run_setup_ui()` turns that
into `SetupCancelledError`, which `cli()` reports before exiting 1. Nothing is written and no
workbook is built. Keep that signal intact — the screen previously had no way to report which button
was pressed, so `run_setup_ui()` saved the config and ran the pipeline whatever the user chose. The
screen saves the config itself, so `run_setup_ui()` must **not** save again.

`tests/test_setup_screen.py` covers this without needing a display: the button handlers are called
on an instance built with `__new__`, so a stub stands in for Tk.

## Pipeline

`run_pipeline(sys_cfg_obj, progress)` in `ovi.py` drives the four stages and requires no GUI —
that is what makes the code testable. `run_with_splash()` wraps it, passing `SplashScreen.update_status`
as the progress callback; the splash owns the Tk mainloop, so the work happens inside a
`splash.after()` callback and exceptions are captured and re-raised after the loop exits.

1. **`SysConfig`** (`ovi_setup.py`) — dataclass holding all system + per-vault settings. Reads/writes
   `CONFIG.yaml`. **Downstream stages read the packed `sys_cfg` dict, not these attributes**, so any
   attribute change made after `load_config()` must be followed by `cfg_pack()` or it is silently
   ignored (this is why `select_vault_by_path()` calls it). Delegates vault discovery to
   `ObsidianApp` (`ovi_obs_app.py`), which parses Obsidian's own `obsidian.json` (found via
   `candidate_config_dirs()`, see above) to build `sys_vlts`/`cur_vlts` and pick the last-open
   vault as the default; with no file or no reachable vault there is no default and
   `apply_vault()` is skipped. If `CONFIG.yaml` is missing or `chk_fields_on_load()` fails, the
   Tk `SetupScreen` (`ovi_setupscreen.py`) is shown before anything else runs.

   **obsidian.json is not the only way in.** `register_vault_dir()` builds a vault record for any
   directory, so a folder Obsidian has never opened can still be scanned — the setup screen's Vault
   Folder field and the CLI's `VAULT_PATH` argument both go through it. Such a record carries the
   folder's *name* as its `vault_id`, because `obs_hyperlink()` interpolates that into
   `obsidian://open?vault=…` and an empty id would make every link in the workbook dead; Obsidian
   accepts a name there, so the links start working once the folder is opened in Obsidian. A missing
   `.obsidian` folder is reported by `check_obsidian_dir()`, which is a **warning only** and must
   stay out of `validate_dir_vault()` — that one gates whether the setup screen opens at all, and
   `tests/test_setup_screen.py` pins a bare directory as valid.
2. **`VaultScan`** (`ovi_build.py`) — `rglob("*.md")` over the vault; per file it strips
   Templater tags, splits frontmatter from body on a delimiter anchored to the top of the file (see
   "Frontmatter is only frontmatter at the top of the file" below), strips code blocks and inline code
   from the body, `yaml.safe_load`s the frontmatter, regex-scans the body for `key:: value` and
   `#tags`, and accumulates into the `obs_*` dicts.
3. **`NewWb`** (`ovi_wb_tabs.py`) — turns the harvested data plus per-tab layout metadata into a
   complete cell-level tab definition for each tab.
4. **`ExcelExporter`** (`ovi_xl.py`) — walks `sys_tab_seq` and renders each tab into an openpyxl
   workbook (tables, conditional formatting, `obsidian://` hyperlinks, images) and saves it.
   `open_workbook()` in `ovi.py` then hands the file to `ovi_launch.open_workbook()`; a failure
   there is reported, not raised, because the workbook already exists.

### Stages talk through a YAML file, not objects

Each stage re-reads `wb_def` from disk rather than passing it in memory. `WbDataDef` (`ovi_wb_setup.py`)
allocates the next sequential batch file `data/batch_files/ovi_<vault>_NNNN.yaml` (and the matching
`data/workbooks/ovi_<vault>_NNNN.xlsx`), and `write_bat_data()` / `read_wb_data()` are the handoff. `NewWb` and
`ExcelExporter` both begin with `read_wb_data()`. Consequence: anything you add to `wb_def` must be
`yaml.dump`-able, and stale batch files are the first thing to check when a run produces odd output.

**Generated filenames name their vault.** `build_file_stub()` joins `sys_id` to the vault name run
through `safe_name_part()`, which reduces it to `[A-Za-z0-9._-]` — both because the name is a folder
on someone else's disk and because `seq_nums()` feeds the same stub to `glob`, where `[`, `*` and
`?` would be read as a pattern. The sequence number is therefore per-vault: scanning a second vault
starts again at `_0000` rather than continuing the first one's count, and `get_last_bat()` only ever
finds batch files belonging to the vault in hand. A name that sanitises away to nothing falls back to
the bare `sys_id` — which makes that stub a *prefix* of every other stub, so `seq_nums()` anchors its
match with `fullmatch` rather than trusting the glob. Pinned by `tests/test_output_naming.py`.

**The number is one past the highest still on disk in *both* generated directories.** `seq_nums()`
reads `data/batch_files/*.yaml` **and** `data/workbooks/*.xlsx`, and `get_next_bat()` takes
`max(...) + 1`; `get_last_bat()` takes `max(...)` over the batch files, so "last" and "next" cannot
disagree. The two directories fall out of step whenever `--init` deletes a batch file but cannot
delete the workbook beside it, which is what happens while Excel has that workbook open — a legal
outcome that `reset_generated_files()` reports and exits 0 on. Numbering from the batch files alone
then reused the survivor's number, and `ExcelExporter.save_workbook()` answers a locked target with a
modal Tk retry dialog when `interactive=True` and raises `WorkbookLockedError` otherwise (the
locked-file case is a Windows one: POSIX unlinks an open file without complaint). For the same reason gaps are **not**
refilled: a missing `_0001` stays missing rather than overwriting `ovi_<vault>_0001.xlsx`.

`wb_def` has exactly three keys:

- `sys_cfg` — the packed `SysConfig` dict (also carries `ctot`, `sys_pn_batch`, `sys_pn_wbs`).
- `wb_data` — the harvested vault data: `obs_props`, `obs_atags`, `obs_xyaml`, `obs_dupfn`, `obs_files`,
  `obs_tmplt`, `obs_codes`, `obs_nests`, `obs_plugs`, `obs_qadd`, `obs_empty`.
- `wb_tabs` — keyed by tab id; each value is a `tab_def` dict.

The `obs_*` dicts are all shaped `{key: {value: [filepath, ...]}}` (see `upd_obs_props`); `obs_files` and
`obs_nests` use `{filepath|F-or-I: {key: [values]}}` and `{plugin_id|filepath: {key: [values]}}`.
`obs_empty` is the exception: a plain list of empty notes' paths, which `ExcelExporter` turns into a set
so the Xyml tab can print `(empty file)` in its "Fm Okay" column instead of a lookup that reads blank.

## The tab system

Tabs are identified by 4-character ids: `pros vals tags file code xyml dups tmpl nest plug qadd summ
ar51`. Adding or renaming one touches **eight** places. Most mismatches raise; two do not:

1. `NewWb.tab_common` (`ovi_wb_tabs.py`) — display name, titles, help text, `data_src`. Every key
   is read with `[...]`, not `.get()`, and each `help_txt` sub-key needs a matching
   `tab_cd_<key>_def`.
2. A `DefXxxx(NewTab)` subclass in the same file, which fills in `tab_def` and calls `tab_def_post()`.
3. The `if/elif` dispatch chain in `NewWb.__init__` — an unknown key raises `Unexpected key`.
4. `WbDataDef.get_next_bat()`'s `wb_tabs` dict (`ovi_wb_setup.py`). **Insert before `summ`** —
   `DefSumm` reads the other tabs' finished `tab_cd_fixed_summ`, so it has to be built last.
5. `Colors.init_tab_clrs()` (`ovi_colors.py`) — keyed by tab id; a missing entry is a `KeyError`.
6. **`ExcelExporter.export_tab()`'s per-tab `vals` branch** (`ovi_xl.py`) — the `if/elif tab_id`
   chain that turns harvested data into a row. **This is the one that fails silently:** with no
   branch, `vals` stays `[]`, and the tab renders its title, headers, totals and an empty table
   without raising or logging anything. `vals[i]` lands in absolute column `tbl_beg_col + i`, so the
   list must be flat and in table-column order.
7. `DEFAULT_TAB_SEQ` (`ovi_setup.py`) — nothing renders without it.
8. The sink in `wb_data` (`ovi_build.py`) — `initialize_all_tabs()` raises `KeyError` on a
   `data_src` key that is absent, so it must always be assigned, `{}` included. `{}` is what makes
   the tab drop.

Optional ninth: `DefSumm.tab_summ_map`. Its nine grid slots are full, so a new tab gets no coloured
box on the Summary tab — silent and harmless.

Render order and inclusion come from `sys_cfg['sys_tab_seq']`, defaulting to `DEFAULT_TAB_SEQ` in
`ovi_setup.py`. **`sys_tab_seq` is persisted in `CONFIG.yaml`**, so adding an id to
`DEFAULT_TAB_SEQ` does nothing on a machine that already has a config — `cfg_unpack()` restores the
saved list and the new tab silently never renders. Expect to need `-i/--init`, a hand-edited
`CONFIG.yaml`, or a scratch `OVI_DATA_DIR` to see it.

`NewTab` is the base class: it defines table naming (`tbl_<tab_id>`), the header row/column origin, the
`RowId` / `IsVisible` / `P-V Index` helper columns, and the Excel formula strings (`f_uniq_*`, `f_txt_*`,
`f_num_*`) that make tab totals respect table filters via `AGGREGATE`/`SUBTOTAL`. `calc_col_pointers()`
and `set_table_links()` compute where the variable-width "FileNN" hyperlink columns land — the count comes
from `ctot[11]`/`ctot[12]` (max links seen) capped by the user's `link_lim_vals`/`link_lim_tags`.

**Fonts are resolved once, at the top of `ovi_wb_tabs.py`.** `DISPLAY_FONT` (Impact) is used for
every tab title and subtitle via the module-level `TITLE_FONT`; never write a font name in a tab
subclass. An `.xlsx` cell names exactly one font with no fallback list, so `display_font()` checks
what is installed on this machine — fair, since ovi builds and opens the workbook in one run — and
returns `None` when it is absent. `None` means "no preference", which lands on
`ExcelExporter.FALLBACK_FONT` (Arial: on Windows and macOS, and substituted by metric-compatible
Liberation Sans on Linux). Expect the fallback to fire on Linux, where Impact is not an OS font.

**`calc_col_pointers()` is the only place the IsVisible column's position is decided.** A tab declares
`tab_has_isVisible_col`, and optionally lists `isVisible` among its `tab_cd_table_hdr` columns; it must
never state a column number. If it lists `isVisible` anywhere but the end of its own table, the method
raises. Do not reintroduce a per-tab `tab_tots_isVisible_col` constant — that duplication is issue #4,
and the constants had already drifted (the Code tab claimed 44 while its table ended at 54).

### Cell definition convention

Cells are plain 11-element lists shared between `ovi_wb_tabs.py` and `ovi_xl.py`:

```
[col, row, font, size, width, text_clr, fill_clr, bold, italic, align, value]
```

`ExcelExporter.export_cell()` consumes them positionally, so element order is a hard contract.
`Colors.get_tab_clrs(tab_id)` returns `(clr1, txt1, clr2, txt2, table_style)` and is where fills come from.

### `ctot` counters

`sys_cfg['ctot']` is a list of counters incremented throughout `ovi_build.py` and rendered on the
**Area51** tab (not the Summary tab). Its length is `CTOT_SLOTS` in `src/ovi/__init__.py` — the
one place it is stated; `ovi_build`, `ovi_setup`, `ovi_obs_app`, `ovi_wb_tabs` and
`tests/conftest.py` all import it, and they must agree or `DefAr51` indexes off the end.

Slots: `0` md files seen, `1` templates seen, `2` skip-dir files skipped, `3` files
processed, `4` NestedDictionary resets, `5` files with frontmatter, `6` files with body properties,
`7` `upd_obs_files` calls, `8` `upd_obs_nests` calls, `9` `upd_obs_props` calls, `10` files with no
frontmatter, `11` max links per property value, `12` max links per tag, `13` empty notes.

Adding a slot means bumping `CTOT_SLOTS`, appending to `ctot_descs` **and** adding the matching
`f-tot-NN`/`x-tot-NN` cell pair in `DefAr51.tab_cd_fixed_summ` — a desc without a cell is simply never
rendered. Slot `13` counts notes whose raw text is whitespace only; it is a subset of slot `10`, since
an empty note has no frontmatter either.

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
  is a no-op for them, since Templater syntax isn't valid YAML). They count in `ctot[1]`, not `ctot[3]`. `PluginMan` (`ovi_plugin_man.py`)
  separately reads `.obsidian/plugins/*/manifest.json` + `community-plugins.json` for the Plugins tab and
  maps code-block signatures (`dataview`, `button`, …) to plugin ids.
- **One plugin's own settings are read: QuickAdd's.** `QuickAddData` (`ovi_quick_add.py`) reads
  `.obsidian/plugins/<dir>/data.json` for the `qadd` tab, gated on `PluginMan` saying QuickAdd is
  both installed *and* enabled; anything else yields `{}` and the tab drops. It takes the
  already-built `PluginMan` rather than constructing its own, and finds the folder through that
  entry's `plugin_dir` — the folder name and the manifest `id` are recorded separately because they
  need not match. QuickAdd stores a tree, so it is flattened to one row per setting: `Parent` repeats
  the owning record's *name* and `Seq` carries traversal order, which together are what let a sorted
  or filtered sheet be put back together. Ids are deliberately not surfaced — a step referencing
  another choice is resolved to that choice's name. Read it with `encoding="utf-8"`; choice names
  are routinely emoji.
- **Frontmatter is only frontmatter at the top of the file.** `split_file()` anchors the opening `---`
  with `rgx_fm_open` (`\A\ufeff?\s*---[ \t]*$`); the leading `\s*` skips a BOM and the blank line a
  stripped Templater block leaves behind, but it cannot cross non-whitespace, so a `---` following any
  real text can never open a block. It previously took the first two matches of `^---$` wherever they
  fell, which made every Markdown horizontal rule and setext heading underline look like a delimiter —
  in one 565-note vault, 23 notes had the text between two body rules fed to `yaml.safe_load` while
  everything before the second rule was silently discarded. An opening delimiter with no closing one is
  not frontmatter. `split_file()` records nothing; `parse_file()` decides what a missing frontmatter
  means, which is what keeps templates off the Issues tab. Code fences are stripped from the body
  *after* the split — strip them first and a fence at the top of a note promotes a body rule to line 1.
- **Bad frontmatter is classified, not dropped** — `obs_xyaml` codes `BadY` / `NoFm` / `MtFm` / `ErrY` /
  `NonD`, described in `WbDataDef.xyml_descs`.
- **Everything is lowercased** for grouping; the original casing is preserved in `actual_prop_key` and
  surfaced only on the Files tab.
- **Logging**: `from ovi_logger import logger` everywhere; `make_logger(level)` is called once, by
  `cli()`. Swap the active handler config via `ACTIVE_LOG_CONFIG` (alternatives live in
  `src/ovi/logging_configs/`). Those JSON files declare relative log paths, which `_resolve_handler_paths()`
  rewrites to absolute under `APP_DIR`. Logs rotate at 3 MB, 50 backups, into `logs/`.
- **The version is single-sourced** from `__version__` in `src/ovi/__init__.py` — see
  `docs/VERSIONING.md` for the protocol and release steps. `pyproject.toml` declares
  `dynamic = ["version"]`; the CLI's `--version`, the splash, `SysConfig.sys_ver` and both Summary
  tab strings all derive from it, and `tests/test_version.py` fails if any of them stops doing so.
  Never type a version literal anywhere else. Bumping `__version__` needs
  `uv sync --reinstall-package obsidian-insights`, or the installed metadata stays stale.
- **Empty tabs are dropped**, not rendered: `ExcelExporter.initialize_all_tabs()` skips any tab whose
  `data_src` is empty and rewrites `sys_tab_seq` to the surviving list. A vault with no Templater
  folder configured, or no nested plugin data, legitimately produces 10 sheets rather than 12.
- **Outstanding work lives in GitHub issues**, not in code comments. A ~90-line `Bug-NNN` / `ER-NNN`
  block at the top of `ovi_xl.py` (whose own Bug-022 asked for exactly this) became
  `docs/BACKLOG.md`, which in turn became issues #1–#25 on 2026-07-29. `docs/BACKLOG.md` is now a
  frozen historical record — file new work on the tracker, and do not reintroduce todo lists in
  source files. The one exception is `docs/WORKING-NOTES.md`, which tracks repo administration, CI
  upkeep and open decisions — things with no code to attach an issue to. Keep code defects out of it.
  **It is untracked as of 2026-08-18** (`/docs/WORKING-NOTES.md` in `.gitignore`): the material is
  for the owner rather than for anyone reading a published repository. Read it and edit it as
  normal; just never `git add -f` it. Its numbering note matters — the issue tracker has been
  recreated on each successor repository with the original issue numbers preserved, so every
  `#NN` reference in the docs and commit history still resolves.

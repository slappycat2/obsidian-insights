# Changelog

Notable changes to Obsidian Insights. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[docs/VERSIONING.md](docs/VERSIONING.md).

## [Unreleased]

## [1.3.0] — 2026-09-04

### Added

- **A blank spreadsheet application means "use the system default".** Setup no longer insists on
  a program path: leave the field empty and the workbook is handed to whatever the desktop
  associates with `.xlsx` (`os.startfile` on Windows, `open` on macOS, `xdg-open` on Linux). A
  fresh install that finds no recognisable program now defaults to blank instead of to a value
  that could never validate.
- **macOS application bundles are accepted.** `Microsoft Excel.app` and `Numbers.app` are
  directories, which the executable check used to reject with "must be a file" — and the Browse
  dialog returns exactly that path, so setup could not be completed on a Mac. Bundles now validate
  and are launched with `open -a`. On Linux a bare command on `PATH` (`libreoffice`, `soffice`,
  `localc`) validates too, and is what a fresh install suggests when one is found.
- **Flatpak and Snap Obsidian on Linux.** The vault list is now looked for in
  `$XDG_CONFIG_HOME/obsidian`, `~/.config/obsidian`, `~/.var/app/md.obsidian.Obsidian/config/obsidian`
  and `~/snap/obsidian/current/.config/obsidian`, first match wins.
- `docs/PLATFORM-CHECKLIST.md`: the manual smoke list for macOS and Linux, covering what only a
  real desktop can exercise.

### Fixed

- **A machine where Obsidian has never run could not start the app at all.** A missing
  `obsidian.json` raised before the setup screen could open — even with a vault path on the
  command line. It is now a logged warning; the vault comes from `CONFIG.yaml`, the `VAULT_PATH`
  argument or the setup screen's folder picker instead. With none of those, `--headless` reports
  a one-line configuration error rather than a traceback.
- **The setup screen could not open on Linux.** The window icon was set with `iconbitmap` and a
  Windows `.ico`, which X11 rejects with a `TclError`. The icon is now a PNG via `iconphoto` on
  every platform, with the `.ico` as a Windows-only extra, and a failed icon can no longer abort
  setup. The screen also grows vertically now: with resizing forbidden, the taller native fonts on
  macOS and HiDPI Linux clipped the Save & Run and Cancel buttons off the bottom.
- **`--headless` no longer needs tkinter.** The export stage imported it at module scope, so a
  Python without Tk (system Python on Debian/Ubuntu without `python3-tk`, Homebrew without
  `python-tk`) failed at import even when no window would ever open. Tk is now imported only by
  the two GUI modules and, lazily, by the one Retry/Cancel prompt — which no longer fires under
  `--headless` or in the test suite; a locked workbook there raises a clear error instead.
- **`sys_cfg_os` is recomputed, never restored.** A `CONFIG.yaml` carried from Windows to a Mac
  made the app believe it was on Windows, which silently emptied the dot-folder list.
- **`CONFIG.yaml` and the batch files are UTF-8 with LF line endings** on every platform. They
  were read and written in the locale encoding (cp1252 on Windows), and only survived because
  PyYAML happened to escape non-ASCII. Notes are read with `utf-8-sig`, so a byte-order mark
  neither reaches the YAML parser nor stops a BOM-only note counting as empty.
- **`obsidian://` links are properly encoded.** The vault id is percent-encoded (a vault
  registered by folder name uses that name, so `Work & Home` ended the parameter at the
  ampersand); backslashes become forward slashes before encoding; a `"` in a note name (legal on
  macOS and Linux) is doubled so the formula still parses; only a trailing `.md` is dropped from
  the link text. The Duplicates tab's links are built with `Path.relative_to()` rather than a
  case-sensitive string replace that left a leading separator.
- **Body text names no font.** Calibri was hard-coded in every tab; it is an Office font with no
  metric-compatible substitute on a stock Linux. Body cells now land on the same Arial fallback
  as titles, which fontconfig maps to Liberation Sans.
- The unused `PIL.ImageTk` import is gone from the setup screen. On several Linux distributions it
  is a separate package, and importing it for nothing was a gratuitous way to fail.
- A failed launch of the spreadsheet application is reported in one line after the workbook is
  written, instead of a traceback after a successful run.

### Changed

- The Area 51 tab's sign is now drawn by the project rather than taken from a stock photo of
  unknown provenance. It ships in the wheel and is embedded in every workbook, so its licence
  has to be ours to give.
- `pyproject.toml` declares the three operating systems and the GUI environments it runs in, an
  sdist that leaves out the brand art and owner-only tools, and links to the changelog and source.
- README rewritten for someone who has never seen the project: requirements per platform,
  including tkinter and the choice of spreadsheet application, and where generated files land.
- **Renamed to Obsidian Insights.** The tool, the package and the command are now `ovi`; the old
  name, Obsidian Vault Health Check (`v_chk`), is gone from every surface. What that means when
  upgrading a checkout:
  - The command is `uv run ovi` (was `uv run v-chk`). `python main.py` is unchanged.
  - The package imports as `ovi` (was `vault_check`) and its modules are `ovi_*.py` (were
    `v_chk_*.py`). The scanner class is `VaultScan` (was `VaultHealthCheck`).
  - The data-directory override is `OVI_DATA_DIR` (was `V_CHK_DATA_DIR`), and an installed copy
    keeps its data under `~/.ovi` (was `~/.v_chk`).
  - Generated files are `ovi_<vault>_NNNN.yaml` / `.xlsx` and the log is `logs/ovi.log`. An
    existing `CONFIG.yaml` still saying `sys_id: v_chk` is read as `ovi`, so the switch needs no
    `--init`; numbering starts again at `_0000` because the stub is new, and the old `v_chk_*`
    files are left where they are.
  - The `ovi_date` config key replaces `v_chk_date`.
  - The distribution is `obsidian-insights` and the repository is
    `slappycat2/obsidian-insights`; GitHub redirects the old URL.
  - The banner on the setup screen now reads "Obsidian Insights". The README screenshot still
    shows the old Summary tab title until it is retaken.

## [1.2.0] — 2026-08-27

### Added

- **A QuickAdd tab**, rendered after Plugins and sharing its yellow. The workbook could say which
  plugins were installed but nothing about what any of them was configured to *do*; QuickAdd's
  `data.json` is where a vault's capture, template and macro automation actually lives, and it is
  otherwise only readable through QuickAdd's own modal UI, one choice at a time. The tab appears
  only when QuickAdd is both installed and enabled — otherwise the sink is empty and the existing
  empty-tab drop removes the sheet, exactly as the Plugins tab already does for a vault with no
  `.obsidian`.
- QuickAdd stores a tree and a worksheet is a table, so the tree is flattened to one row per
  setting, and two columns put it back together. **Parent** repeats the name of whatever a row
  belongs to; **Seq** numbers every row in QuickAdd's own traversal order, so sorting or filtering
  the sheet never loses the order children were defined in. **Section** says what a row is — a
  `Choice` (something on the QuickAdd menu), a `Step` (one command inside a macro, in the order it
  runs), a `Config` key belonging to the record above it, or a plugin-wide `Setting`. Three
  nestings survive the flattening: a `Multi` choice's child choices, a `Macro`'s ordered command
  list, and the choice a `NestedChoice` command embeds.
- **QuickAdd's internal ids are not shown** — they identify nothing visible in the app. A macro step
  that hands off to another choice is resolved to that choice's *name*, so a row reads
  `Add a Person` rather than `3e7fd7de-4ae3-466f-880b-548f606092c0`.
- Nested settings become dotted keys (`folder.enabled`, `fileNameFormat.format`), list items carry
  an index, and a setting that is configured but empty prints `(empty)` rather than reading as
  unconfigured. On the vault this was built against that is 1,086 rows from a 79 KB file.

## [1.1.0] — 2026-08-27

### Added

- **A vault no longer has to be one Obsidian has opened.** The setup screen has a new **Vault
  Folder** field beside the vault dropdown -- an editable path with a Browse button, in the same
  shape as the Workbook Executable row below it. Type or browse to any directory and it is
  registered as a vault: the dropdown gains it, and Save & Run keeps it, so it is there on the next
  run. `ovi <path>` accepts the same folders; it used to raise `VaultNotFoundError` for anything
  outside obsidian.json, which is why a copied vault, a backup, or a machine whose Obsidian had been
  reset could not be scanned at all. Both routes go through one new `SysConfig.register_vault_dir()`.
- A folder with no `.obsidian` subfolder is called out in an amber warning under the field, and is
  scanned anyway -- Save stays enabled. Nothing in the harvesting needs Obsidian (the test suite's
  own vaults have never had a `.obsidian`), so the warning says what is actually lost: the Plugins
  and Templates tabs come out empty and are dropped, and the workbook's links may not open. The
  check is `SysConfig.check_obsidian_dir()`, deliberately separate from `validate_dir_vault()` --
  that one gates whether setup opens at all, so folding the test into it would have forced the setup
  screen for every plain folder and disabled Save on exactly the vaults this feature exists to allow.

### Changed

- A vault registered by folder carries the folder's name as its `vault_id`. `obs_hyperlink()` builds
  `obsidian://open?vault={vault_id}`, and Obsidian's URI scheme takes a vault name there as well as
  an id, so this leaves the workbook's links inert only while Obsidian does not know the folder --
  they start working the moment it is opened there. The empty id the record would otherwise have
  carried made every link `vault=&file=...`, dead for good.
- `PluginMan.get_plugs_lib()` no longer logs an ERROR when a vault has no `.obsidian` folder. It
  reported the missing `community-plugins.json` twice per run, which was noise for the folders this
  release makes scannable. A `.obsidian` that exists but cannot be read still reports.

### Fixed

- **`--init` no longer leaves the next run pointing at a workbook it could not delete.** A workbook
  open in Excel cannot be unlinked; `--init` reported that and moved on, but the batch file beside it
  *was* deleted, and `get_next_bat()` derived the sequence number from `data/batch_files/` alone. The
  next run therefore chose `_0000` again and aimed straight at the locked `.xlsx`, where
  `save_workbook()` met it with a modal Tk retry dialog -- one that fires even under `--headless`.
  The number now comes from the highest still on disk in **either** generated directory, plus one, so
  a surviving workbook reserves its own number. Gaps are no longer refilled either: deleting `_0001`
  out of `0000..0005` used to make the next run silently overwrite `ovi_<vault>_0001.xlsx`.
- A failed delete is still an allowed outcome and still exits 0, but `--init` now counts it --
  `Reset complete -- 2 file(s) deleted, 1 in use and kept.` -- and says the survivors keep their
  numbers. A reset in which nothing could be deleted used to read as a clean success.
- `--init` no longer tries to delete Excel's `~$<name>.xlsx` owner files. They are Excel's, not
  ovi's, and listing one only to fail on it put a second confusing line in the report.
- `get_last_bat()` picks the highest-numbered batch file rather than the newest by creation time, so
  it cannot disagree with the number `get_next_bat()` would hand out. Both now share `seq_nums()`.

## [1.0.0] — 2026-08-20

First release of the 1.x series. The version number says the tool is finished and in daily use; it is
**not** a promise that the workbook format is frozen — see `docs/VERSIONING.md`.

### Changed

- The setup screen's **Full Path** field now shows the whole executable path. It was 268px wide and
  cut `C:/Program Files/Microsoft Office/root/Office16/EXCEL.EXE` off around `Office16/`, so the
  value being saved could not be read. The field was never the problem: the Save & Run and Cancel
  buttons sat in the same grid row as the Workbook Executable frame, which stopped that frame
  extending past the first column. Moving the buttons up one row — beside Workbook Link Columns,
  under the logo — lets the frame span the window, and the entry, which is the only weighted column
  in it, takes all of the gain: 268px to 474px, and it now grows further when the window is widened.

### Added

- `tools/ui_shot.py`, a development aid that opens the real setup screen, photographs it, and dumps
  every widget's class, geometry, text and state. It redirects `OVI_DATA_DIR` to a scratch copy of
  `CONFIG.yaml` and dismisses the screen with `on_cancel()`, so it cannot write your configuration.
  Not packaged — `tools/` sits outside `src/`.

## [0.4.1] — 2026-08-18

Internal only — no change to the workbook or the CLI.

### Removed

- `ExcelExporter` no longer copies the harvested `obs_*` sinks onto its own attributes. All nine were
  written in `__init__` and never read again: every tab reads its data through
  `wb_def['wb_data'][data_src]`. The copy had also drifted — `obs_nests` was assigned twice, the
  second time from `obs_plugs`, so `self.obs_plugs` never existed at all. `obs_empty` stays, because
  the Xyml row builder does need a per-row membership test.
- Four unused regexes in `ovi_xl.py`. Two were stale copies of `ovi_build.py` patterns frozen in
  their pre-fix form: `rgx_body` lacked the `re.MULTILINE` whose absence is pinned as a regression in
  `tests/test_vault_parsing.py`, and `rgx_tag_pattern` lacked the guard that stops a wikilink pipe
  reading as a tag. Anyone reaching for one would have picked up a known-broken version.

### Changed

- The timezone-stripping pattern in `ovi_xl.py` is compiled once at startup rather than on every
  string cell in the workbook.
- `docs/VERSIONING.md` no longer claims the repository is private. It is public, and has been for
  some time; the note drew its line around what needs the owner's approval in the wrong place, by
  listing "making the repository public" as a future act while treating a push — which on a public
  remote publishes the code — as routine. Creating a GitHub release and uploading to PyPI remain the
  acts that need approval, and neither has happened.

## [0.4.0] — 2026-08-18

Frontmatter detection no longer mistakes a Markdown horizontal rule for a frontmatter
delimiter, which had been filling the Possible Issues tab with phantom YAML errors and
silently discarding the body of notes that have no frontmatter at all.

### Fixed

- Frontmatter is now recognised only at the top of a note, the way Obsidian recognises it. The
  boundary search took the first two `^---$` matches wherever they fell, so a note with **no**
  frontmatter but two Markdown horizontal rules — or a setext heading underline — had the text
  between them parsed as YAML, and everything before the second rule silently thrown away along with
  any `key:: value` fields and `#tags` in it. On a 565-note vault this hit 23 notes and produced 19
  phantom entries on the Possible Issues tab; those notes now report "No Properties", and three prose
  sentences from an install README stop appearing as vault properties. An opening `---` that is never
  closed is likewise no longer treated as frontmatter.
- A note's body no longer begins with the stray `---` that closed its frontmatter.
- Templates no longer appear on the Possible Issues tab when they have no frontmatter. `split_file()`
  recorded that case itself, bypassing the template exemption in `record_yaml_issue()`.
- An empty note is no longer listed twice on the Possible Issues tab, which gave it a duplicate
  hyperlink column.

### Added

- Empty notes are counted separately (`ctot[13]`, "13-Empty Notes (whitespace only)" on the Area51
  tab) and marked `(empty file)` in the Possible Issues tab's "Fm Okay" column, where the usual
  lookup could only read blank. A note counts as empty when its raw text is whitespace only.

### Changed

- `ctot[10]` now counts notes with no frontmatter, as the code comments and CLAUDE.md always claimed
  it did; it previously incremented only for a wholly empty note. The Area51 label changes from
  "10-Empty Fm/Body in Markdown" to "10-Files With No Frontmatter". The counter list is now sized
  from a single `CTOT_SLOTS` constant in `src/ovi/__init__.py` rather than five separate
  literals.

## [0.3.0] — 2026-08-03

Generated files now say which vault they came from, plus the setup screen's vault dropdown fixes
that had accumulated since 0.2.0.

### Changed

- Batch files and workbooks are now named for the vault they came from:
  `ovi_<vault name>_NNNN.yaml` and `ovi_<vault name>_NNNN.xlsx`, instead of `ovi_NNNN`. The
  vault name is reduced to letters, digits, `.`, `-` and `_` first. The sequence number counts per
  vault, so scanning a second vault starts at `_0000` rather than continuing the first one's
  numbering. Existing `ovi_NNNN` files are left alone; `--init` deletes them along with the rest.

### Fixed

- Selecting a vault from the setup screen's dropdown no longer raises `AttributeError`. A debug log
  line read `self.sys.obj` for `self.sys_obj`; because the f-string is built before `logger.debug()`
  is called, it raised at every log level. Tk swallowed the traceback, so the screen stayed open
  showing the previous vault's settings while `sys_obj` and `cur_vlts` had already swapped to the
  new one — whatever was saved next paired the wrong vault with the wrong settings. Nothing had
  covered the three swap methods the dropdown calls; they now have tests.
- Switching vaults no longer adds a duplicate of every field callback. `upd_tk_vars_with_sys_obj()`
  rebound each `self.*_var` to a fresh `StringVar`/`BooleanVar` rather than calling `set()` on the
  existing one. A widget and a trace both hold the variable *object*, so each swap orphaned every
  widget and lost every callback, and the caller compensated by re-`configure`-ing each widget and
  re-adding each trace — while the old variables stayed alive and stayed traced. One more copy of
  `validate_all_fields()` and `update_links_help()` was registered per switch, so after four vaults
  the vault directory was walked four times per keystroke in the skip-folders field. The same block
  built a new "(Unlimited)" label on each swap and gridded it over its predecessor without
  destroying it. Setting the variables updates the screen and fires the traces already attached, so
  the re-wiring is gone.

## [0.2.0] — 2026-07-29

Correctness of what the workbook reports, and a setup screen that works. Every change below was
found by using the tool or by reading the code around a reported bug — the Properties tab was
counting wrongly, the Templates tab had never once rendered, plugin-managed notes were losing their
metadata, and `--setup` could not save.

### Added

- The Templates tab now has data ([#6]). Templates were skipped outright, and nothing populated
  `obs_tmplt`, so the tab was always empty and always dropped from the workbook. Files under the
  Templater folder are now read into it — Templater `<% ... %>` tags are stripped before parsing,
  and a property left valueless by that (`date: <% tp.date.now() %>`) is marked `(-None-)` rather
  than rendered blank. They still reach no other tab: not Properties, Tags, Files, nested-plugin
  data, code blocks or duplicate filenames, and a template whose frontmatter fails to load is not
  reported as a vault problem, since Templater syntax is not valid YAML.

### Changed

- Properties tab: the third column is now "Files" rather than "Links", since it counts distinct
  notes. The name is also the Excel table column name, so the Summary tab's `tbl_pros[...]`
  formulas follow it automatically.
- Help text on the Summary and Properties tabs now states what the Files total measures — property
  usages, one per property per note — instead of describing it as a total that "will appear high
  because items can be counted twice". The behaviour is unchanged and intended; only the
  explanation was misleading. Notes Analyzed on the Summary tab remains the distinct note count.
- Tab titles and subtitles now ask for **Impact**, which is present on both Windows and macOS,
  instead of "Berlin Sans FB Demi" and "Berlin Sans", which ship with Microsoft Office ([#5]). The
  name was written 38 times across the tab subclasses and is now resolved once. Where the font is
  not installed — Linux, mainly, since Impact arrives there only with `ttf-mscorefonts-installer` —
  titles fall through to the same fallback as every other unstyled cell rather than naming a font
  that is not there. Note Impact has no bold cut, so bold titles are synthesised by the viewer.
- The IsVisible column's position is computed in one place, `NewTab.calc_col_pointers()` ([#4]).
  Each tab used to also hardcode it twice — as `tab_tots_isVisible_col` and as a column index in
  `tab_cd_fixed_grid['isVisible']` — both of which were then overwritten. A tab that declares
  IsVisible among its table columns but puts it anywhere other than the end now raises instead of
  silently disagreeing with the totals.

### Fixed

- `--setup` no longer fails when "Save & Run" is pressed ([#26]). The handler called
  `save_config(sys_pn_cfg)`, but `save_config()` takes no arguments and writes to that path itself,
  so every attempt to save raised `TypeError`.
- Cancelling setup, or closing the setup window, now stops the run ([#27]). `SetupScreen.show()` reports
  whether the user saved, the window's close button is wired to Cancel, and `run_setup_ui()` raises
  `SetupCancelledError` instead of saving the config and building a workbook regardless of what the
  user chose. The CLI reports "Setup cancelled. No workbook was created." and exits 1.
- The setup screen's skip-folders field said only "X" when a folder could not be found; it now names
  the folder. It also walks the vault once per validation instead of once per folder name, which it
  did on every keystroke.
- Plugin-managed nested frontmatter no longer inflates the Files tab, and no longer swallows the
  note's real metadata ([#6]). Whether a value is plugin-managed is now decided by where it sits —
  inside a nested dict, which Obsidian does not permit — rather than by scanning the whole
  frontmatter for a known plugin name. That scan applied to the entire file, so a note carrying a
  `kindle-sync` block lost its own top-level properties, its tags and its inline `key:: value`
  fields from the Properties and Tags tabs; it also fired on any note that merely mentioned a
  plugin name inside a value.
- Properties tab: every property now gets exactly one row, and its file count is the number of
  distinct notes using the property ([#1]). Rows were previously emitted at the boundary *between*
  two properties, which produced a phantom first row labelled "Properties", silently dropped the
  last property in the vault, and gave each row a file count that omitted its own first value and
  borrowed the following property's. A note supplying two values of one property is now counted
  once.

[#1]: https://github.com/slappycat2/obsidian-insights/issues/1
[#4]: https://github.com/slappycat2/obsidian-insights/issues/4
[#5]: https://github.com/slappycat2/obsidian-insights/issues/5
[#6]: https://github.com/slappycat2/obsidian-insights/issues/6
[#26]: https://github.com/slappycat2/obsidian-insights/issues/26
[#27]: https://github.com/slappycat2/obsidian-insights/issues/27

## [0.1.0] — 2026-07-29

First properly versioned release. Version numbers before this one were informal and are not
comparable — see [docs/VERSIONING.md](docs/VERSIONING.md#why-the-numbering-restarted).

The release captures the 2026 modernisation, which took the project from "does not run unless you
are standing in the right directory" to an installable, tested, CI-covered package.

### Added

- Installable `src/` layout package with a `ovi` console script (`uv sync`, `uv run ovi`).
- pytest suite — 48 tests covering markdown/YAML harvesting, path resolution, version
  single-sourcing, and a full four-stage pipeline run asserted against the real `.xlsx`.
- Cross-platform CI on Ubuntu, Windows and macOS, including a wheel-contents check.
- `--headless`, `--do-not-open`, `--no-splash`, `--setup`, `--init` and `--debug-level` flags.
- `docs/VERSIONING.md` and this changelog.

### Changed

- Paths resolve through `ovi_paths` rather than the working directory; package assets and
  writable data are separated, so the tool runs from anywhere.
- The version is single-sourced from `src/ovi/__init__.py`.
- The backlog moved out of a comment block in `ovi_xl.py`, first to `docs/BACKLOG.md` and then to
  GitHub issues #1–#25.

### Fixed

- `SysConfig` no longer restores `sys_ver` from `CONFIG.yaml`, which had pinned the reported version
  to whatever wrote the file first — a 0.2.9 config made 0.3.0 report 0.2.9.
- The Summary tab announced two different, hardcoded versions (`v1.0` in the title, `v.0.9 (beta)`
  in the hyperlink); both now derive from `__version__`.
- "Deprecated in 1.4" on the Files tab now reads "Deprecated in Obsidian 1.4", which is whose
  version it always was.
- An unanchored `vault_check/` rule in `.gitignore` matched `src/vault_check/`, silently excluding
  the package from commits and producing wheels containing only metadata.
- Two markdown parser bugs found by the new test suite.

[Unreleased]: https://github.com/slappycat2/obsidian-insights/compare/v1.3.0...HEAD
[1.3.0]: https://github.com/slappycat2/obsidian-insights/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/slappycat2/obsidian-insights/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/slappycat2/obsidian-insights/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/slappycat2/obsidian-insights/compare/v0.4.1...v1.0.0
[0.4.1]: https://github.com/slappycat2/obsidian-insights/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/slappycat2/obsidian-insights/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/slappycat2/obsidian-insights/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/slappycat2/obsidian-insights/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/slappycat2/obsidian-insights/releases/tag/v0.1.0

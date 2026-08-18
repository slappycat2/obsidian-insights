# Changelog

Notable changes to Obsidian Vault Health Check. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[docs/VERSIONING.md](docs/VERSIONING.md).

## [Unreleased]

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
  from a single `CTOT_SLOTS` constant in `src/vault_check/__init__.py` rather than five separate
  literals.

## [0.3.0] — 2026-08-03

Generated files now say which vault they came from, plus the setup screen's vault dropdown fixes
that had accumulated since 0.2.0.

### Changed

- Batch files and workbooks are now named for the vault they came from:
  `v_chk_<vault name>_NNNN.yaml` and `v_chk_<vault name>_NNNN.xlsx`, instead of `v_chk_NNNN`. The
  vault name is reduced to letters, digits, `.`, `-` and `_` first. The sequence number counts per
  vault, so scanning a second vault starts at `_0000` rather than continuing the first one's
  numbering. Existing `v_chk_NNNN` files are left alone; `--init` deletes them along with the rest.

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

[#1]: https://github.com/slappycat2/obsidian-vault-health-check/issues/1
[#4]: https://github.com/slappycat2/obsidian-vault-health-check/issues/4
[#5]: https://github.com/slappycat2/obsidian-vault-health-check/issues/5
[#6]: https://github.com/slappycat2/obsidian-vault-health-check/issues/6
[#26]: https://github.com/slappycat2/obsidian-vault-health-check/issues/26
[#27]: https://github.com/slappycat2/obsidian-vault-health-check/issues/27

## [0.1.0] — 2026-07-29

First properly versioned release. Version numbers before this one were informal and are not
comparable — see [docs/VERSIONING.md](docs/VERSIONING.md#why-the-numbering-restarted).

The release captures the 2026 modernisation, which took the project from "does not run unless you
are standing in the right directory" to an installable, tested, CI-covered package.

### Added

- Installable `src/` layout package with a `v-chk` console script (`uv sync`, `uv run v-chk`).
- pytest suite — 48 tests covering markdown/YAML harvesting, path resolution, version
  single-sourcing, and a full four-stage pipeline run asserted against the real `.xlsx`.
- Cross-platform CI on Ubuntu, Windows and macOS, including a wheel-contents check.
- `--headless`, `--do-not-open`, `--no-splash`, `--setup`, `--init` and `--debug-level` flags.
- `docs/VERSIONING.md` and this changelog.

### Changed

- Paths resolve through `v_chk_paths` rather than the working directory; package assets and
  writable data are separated, so the tool runs from anywhere.
- The version is single-sourced from `src/vault_check/__init__.py`.
- The backlog moved out of a comment block in `v_chk_xl.py`, first to `docs/BACKLOG.md` and then to
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

[Unreleased]: https://github.com/slappycat2/obsidian-vault-health-check/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/slappycat2/obsidian-vault-health-check/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/slappycat2/obsidian-vault-health-check/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/slappycat2/obsidian-vault-health-check/releases/tag/v0.1.0

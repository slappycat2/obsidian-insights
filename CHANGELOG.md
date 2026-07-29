# Changelog

Notable changes to Obsidian Vault Health Check. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[docs/VERSIONING.md](docs/VERSIONING.md).

## [Unreleased]

### Changed

- Properties tab: the third column is now "Files" rather than "Links", since it counts distinct
  notes. The name is also the Excel table column name, so the Summary tab's `tbl_pros[...]`
  formulas follow it automatically.
- Help text on the Summary and Properties tabs now states what the Files total measures — property
  usages, one per property per note — instead of describing it as a total that "will appear high
  because items can be counted twice". The behaviour is unchanged and intended; only the
  explanation was misleading. Notes Analyzed on the Summary tab remains the distinct note count.

### Added

- The Templates tab now has data ([#6]). Templates were skipped outright, and nothing populated
  `obs_tmplt`, so the tab was always empty and always dropped from the workbook. Files under the
  Templater folder are now read into it — Templater `<% ... %>` tags are stripped before parsing,
  and a property left valueless by that (`date: <% tp.date.now() %>`) is marked `(-None-)` rather
  than rendered blank. They still reach no other tab: not Properties, Tags, Files, nested-plugin
  data, code blocks or duplicate filenames, and a template whose frontmatter fails to load is not
  reported as a vault problem, since Templater syntax is not valid YAML.

### Fixed

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
[#6]: https://github.com/slappycat2/obsidian-vault-health-check/issues/6

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

[Unreleased]: https://github.com/slappycat2/obsidian-vault-health-check/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/slappycat2/obsidian-vault-health-check/releases/tag/v0.1.0

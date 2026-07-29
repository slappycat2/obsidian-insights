# Changelog

Notable changes to Obsidian Vault Health Check. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[docs/VERSIONING.md](docs/VERSIONING.md).

## [Unreleased]

Nothing yet.

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

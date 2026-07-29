# Versioning

## The short version

The version is **one string, in one file**: `__version__` in `src/vault_check/__init__.py`.
Everything else derives from it. If you find yourself typing a version number anywhere else, that is
the bug.

Current series starts at **0.1.0** (2026-07-29).

## Why the numbering restarted

Versions before 0.1.0 were informal — a change might be called v9, and the same codebase v0_4 a
fortnight later. Those numbers carry no information and are not comparable to each other, so they
have been retired rather than reconciled. Old repositories and commit messages still mention them;
treat any pre-2026-07-29 version string as a label, not a version.

Restarting below the previous number (0.3.0 → 0.1.0) is normally forbidden, because packaging tools
order versions and would treat it as a downgrade. It was safe exactly once, here, because nothing
had ever been published: no PyPI release under either `obsidian-vault-health-check` or `v-chk`, no
git tags, no GitHub releases. **That escape hatch is now closed** — from 0.1.0 on, the number only
goes up.

## Scheme

[Semantic Versioning](https://semver.org), with the usual 0.x caveat that the public API is not yet
promised to be stable.

While the major version is 0:

| Bump | When |
|---|---|
| **MINOR** (`0.1.0` → `0.2.0`) | Anything a user would notice: workbook layout or tab changes, new or renamed tabs, CLI flags added or changed, `CONFIG.yaml` keys added or renamed, new dependencies |
| **PATCH** (`0.1.0` → `0.1.1`) | Bug fixes, parser corrections, refactors, test and CI work, documentation |

Reaching **1.0.0** means committing to the workbook format and the CLI — that the tab ids, the
`CONFIG.yaml` schema and the flags won't change without a major bump. Not yet.

Pre-release suffixes (`0.2.0rc1`) are available if ever needed, but "beta" is not a version string.
The old Summary tab said `v.0.9 (beta)`, which sorted as nothing and meant nothing.

## What derives from `__version__`

Nothing in this list should ever be edited by hand:

| Consumer | How |
|---|---|
| `pyproject.toml` | `dynamic = ["version"]` + `[tool.hatch.version] path = "src/vault_check/__init__.py"` |
| `v-chk --version` | `@click.version_option(__version__, ...)` in `v_chk.py` |
| Splash screen | `version=f"v{__version__}"` default in `v_chk_splash.py` |
| Summary tab title | `f'Obsidian Vault Health Check v{__version__}'` in `v_chk_wb_tabs.py` |
| Summary tab hyperlink | `f'...,"v{__version__}")'` in `v_chk_wb_tabs.py` |
| `SysConfig.sys_ver` | assigned `__version__` in `cfg_unpack()` |
| Installed metadata | `importlib.metadata.version("obsidian-vault-health-check")` |

`tests/test_version.py` enforces this. It does not check *which* version is correct — only that
there is exactly one of it, since that is the property that kept breaking.

### `sys_ver` is a record, not a setting

`CONFIG.yaml` stores `sys_ver`, but it is never read back into the running version. It records
*which version last wrote the file*. Restoring it was a real bug: a config written by 0.2.9 made
0.3.0 report itself as 0.2.9 indefinitely.

## Releasing

```bash
uv run pytest                                              # 1. green before you start
# 2. edit __version__ in src/vault_check/__init__.py
uv sync --reinstall-package obsidian-vault-health-check    # 3. see the gotcha below
# 4. move CHANGELOG.md's Unreleased entries under the new version + today's date
uv run pytest                                              # 5. green after
git commit -am "Release v0.2.0"
git tag -a v0.2.0 -m "v0.2.0"
git push origin master --follow-tags
```

Optionally publish it: `gh release create v0.2.0 --notes-from-tag`.

> **Gotcha: `uv sync` alone is not enough.** The version is baked into the editable install's
> metadata at install time, so bumping `__version__` leaves `importlib.metadata` reporting the old
> number and `test_installed_metadata_matches_the_package` failing. Only
> `--reinstall-package obsidian-vault-health-check` refreshes it. CI never hits this, because it
> installs from scratch.

## Tags

Annotated (`-a`), prefixed with `v`, matching the version exactly: `v0.1.0`. The `v` prefix is on
the tag only — never inside `__version__`.

## How this is maintained

Claude keeps `CHANGELOG.md`'s `[Unreleased]` section current as work lands, and proposes the bump
level when a release is due, but does not tag without being asked. If a change belongs in the
changelog and it is not there, say so — a missing entry is a bug in the same way a stray version
literal is.

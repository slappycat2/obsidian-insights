# Versioning

## The short version

The version is **one string, in one file**: `__version__` in `src/ovi/__init__.py`.
Everything else derives from it. If you find yourself typing a version number anywhere else, that is
the bug.

Current series starts at **1.0.0** (2026-08-20). The 0.x series ran from 0.1.0 (2026-07-29) to 0.4.1.

## Why the numbering restarted

Versions before 0.1.0 were informal — a change might be called v9, and the same codebase v0_4 a
fortnight later. Those numbers carry no information and are not comparable to each other, so they
have been retired rather than reconciled. Old repositories and commit messages still mention them;
treat any pre-2026-07-29 version string as a label, not a version.

Restarting below the previous number (0.3.0 → 0.1.0) is normally forbidden, because packaging tools
order versions and would treat it as a downgrade. It was safe exactly once, here, because nothing
had ever been published: no PyPI release, no git tags, no GitHub releases. **That escape hatch is
now closed** — from 0.1.0 on, the number only goes up, and every version since has a tag.

## Scheme

[Semantic Versioning](https://semver.org) numbering, with one deliberate departure spelled out
below.

| Bump | When |
|---|---|
| **MINOR** (`1.0.0` → `1.1.0`) | Anything a user would notice: workbook layout or tab changes, new or renamed tabs, CLI flags added or changed, `CONFIG.yaml` keys added or renamed, new dependencies |
| **PATCH** (`1.0.0` → `1.0.1`) | Bug fixes, parser corrections, refactors, test and CI work, documentation |

### What 1.0.0 does and does not promise

**It says the tool is finished and in daily use.** It does **not** freeze the workbook format, the
tab ids, the `CONFIG.yaml` schema or the CLI flags. That is a departure from strict semver, and it
is deliberate: several planned changes would each demand a major bump under the strict rule —
renaming the `skip_rel_str` config key (issue #17), changing the hyperlink format (#14), adding a
tab (#24), reworking nested tag handling (#10, #11). Promising stability and then breaking it four
times would make the number mean less than saying plainly what it means.

So: **breaking changes to the format or the CLI go in a MINOR bump and are called out in
`CHANGELOG.md`.** Read the changelog before upgrading; do not infer compatibility from the number
alone.

If the format is ever genuinely frozen, say so here and start bumping MAJOR for breaks. Until then
this section is the contract, not semver's defaults.

**The one rule that is absolute: the number only goes up.** Restarting or reusing a version is
forbidden — see below for why the 0.1.0 restart was a one-time exception that is now closed.

Pre-release suffixes (`0.2.0rc1`) are available if ever needed, but "beta" is not a version string.
The old Summary tab said `v.0.9 (beta)`, which sorted as nothing and meant nothing.

## What derives from `__version__`

Nothing in this list should ever be edited by hand:

| Consumer | How |
|---|---|
| `pyproject.toml` | `dynamic = ["version"]` + `[tool.hatch.version] path = "src/ovi/__init__.py"` |
| `ovi --version` | `@click.version_option(__version__, ...)` in `ovi.py` |
| Splash screen | `version=f"v{__version__}"` default in `ovi_splash.py` |
| Summary tab title | `f'Obsidian Insights v{__version__}'` in `ovi_wb_tabs.py` |
| Summary tab hyperlink | `f'...,"v{__version__}")'` in `ovi_wb_tabs.py` |
| `SysConfig.sys_ver` | assigned `__version__` in `cfg_unpack()` |
| Installed metadata | `importlib.metadata.version("obsidian-insights")` |

`tests/test_version.py` enforces this. It does not check *which* version is correct — only that
there is exactly one of it, since that is the property that kept breaking.

### `sys_ver` is a record, not a setting

`CONFIG.yaml` stores `sys_ver`, but it is never read back into the running version. It records
*which version last wrote the file*. Restoring it was a real bug: a config written by 0.2.9 made
0.3.0 report itself as 0.2.9 indefinitely.

## Releasing

```bash
uv run pytest                                              # 1. green before you start
# 2. edit __version__ in src/ovi/__init__.py
uv sync --reinstall-package obsidian-insights    # 3. see the gotcha below
# 4. move CHANGELOG.md's Unreleased entries under the new version + today's date
uv run pytest                                              # 5. green after
git commit -am "Release v1.1.0"
git tag -a v1.1.0 -m "v1.1.0"
git push origin master --follow-tags
```

> **Tagging is not releasing, and releasing needs explicit approval.** A tag is a pointer in the
> repository. Creating a GitHub release (`gh release create`) or uploading to PyPI are separate acts
> that require the owner to ask for them by name. Nothing in this checklist authorises them. There
> is no PyPI package.
>
> **History.** This repository was created fresh on 2026-08-18, and again on 2026-09-04 with a
> rewritten history, each time so that nothing from the project's earlier scratch work would be
> carried into a published repository. Earlier history is not available and is not needed; the
> tags from `v0.1.0` onward are all present.
>
> Pushing to a public repository publishes the code even though it does not publish a *release*.
> Confirm before pushing work the owner may not have meant to be visible.

> **Gotcha: `uv sync` alone is not enough.** The version is baked into the editable install's
> metadata at install time, so bumping `__version__` leaves `importlib.metadata` reporting the old
> number and `test_installed_metadata_matches_the_package` failing. Only
> `--reinstall-package obsidian-insights` refreshes it. CI never hits this, because it
> installs from scratch.

## Tags

Annotated (`-a`), prefixed with `v`, matching the version exactly: `v0.1.0`. The `v` prefix is on
the tag only — never inside `__version__`.

## How this is maintained

Claude keeps `CHANGELOG.md`'s `[Unreleased]` section current as work lands, and proposes the bump
level when a release is due, but does not tag without being asked. If a change belongs in the
changelog and it is not there, say so — a missing entry is a bug in the same way a stray version
literal is.

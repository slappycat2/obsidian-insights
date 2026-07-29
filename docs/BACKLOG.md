# Backlog

The working list of bugs and enhancement requests, extracted from the comment block that used to sit
at the top of `src/vault_check/v_chk_xl.py` (that block was itself item Bug-022: *"Remove this
section and track bugs and ERs in Github"*).

Original `Bug-NNN` / `ER-NNN` identifiers are kept for traceability with older commits and notes.
They are **not** unique — see [ID collisions](#id-collisions) below. Once these become GitHub
issues, the issue number is authoritative and these IDs are historical.

To create them on GitHub in one go: `scripts/import_backlog_issues.sh` (see
[Importing](#importing-to-github)).

---

## Open bugs

| ID | Summary | Notes |
|---|---|---|
| Bug-019 | Properties tab "Files" count is meaningless — it counts files × values, not distinct files | Was marked WIP. The comment added "Look for more like this!" |
| Bug-006 | Verify output in LibreOffice Calc, Google Sheets, and on macOS | Partly addressed: CI now runs the test suite on macOS and Linux, but nothing verifies how the `.xlsx` renders in non-Excel spreadsheet apps |
| Bug-014 | Audit property/tag handling against current Obsidian and Dataview rules | |
| Bug-016 | `IsVisible` column is defined and calculated in three separate places | Refactor; the duplication invites drift |
| Bug-018 | Workbook needs better font support | Tab definitions hardcode "Berlin Sans FB Demi" and "Berlin Sans", which are not present on most machines |
| Bug-020 | Exclude templates and plugin-nested data from the vault tabs (props, tags, files) | Bug-015 was closed as "duplicate of 020" while 020 itself stayed open |
| Bug-023 | Hardcode the Setup Screen logo size once macOS/Linux are verified | Currently resized at runtime |

## Open enhancements

| ID | Summary |
|---|---|
| ER-002 | Indicate truncation when a row has more file links than there are link columns ("More exist!") |
| ER-003 | Gather more statistics: most-used tags, inline vs frontmatter split, a top-tags graph, Dataview stats |
| ER-007 | Support nested tags properly — `#Tag/1/A` is one explicit tag but three cumulative ones (`file.tags` vs `file.etags`) |
| ER-008 | Handle sub-tags such as `assets/mac/software` better |
| ER-009 | Support [Dataview task shorthand fields](https://blacksmithgu.github.io/obsidian-dataview/annotation/metadata-tasks/#field-shorthands) |
| ER-011 | Consider array formulas in the Summary tab |
| ER-012 | Option to show just the note name, rather than the relative path, in hyperlinks |
| ER-013 | Identify singular vs plural usages of the same property or tag (`author` vs `authors`) |
| ER-014 | Fix the Area51 table dump |
| ER-015 | Rename `skip_rel_str` to `skip_abs_lst_user` |
| ER-016 | Add Date Created and Date Modified columns to the Files tab |
| ER-017 | Extract the property/tag isolation routines into standalone classes, enabling a future search-and-replace feature |
| ER-018 | Remember per-vault settings between runs |
| ER-019 | Flag unquoted YAML links in the Files tab (lucide question icon) |
| ER-020 | List vault files Obsidian no longer references — orphaned attachments, images |
| ER-021 | Warn when link columns are hidden, with an option to suppress the warning |
| ER-023 | Add a Log tab showing batch numbers, creation dates, `ctot` counters and vault names |
| ER-999 | Refactoring: reduce overlap between the tab-definition subclasses; clean up stray comments and print statements |

---

## Closed by the 2026 modernisation

Recorded so the history stays legible; no action needed.

| ID | Summary | How it was resolved |
|---|---|---|
| Bug-022 | Remove the inline Todo block and track bugs/ERs on GitHub | This document |
| ER-022 | Options for "open workbook on create" and logging level | Shipped as `-x/--do-not-open` and `-d/--debug-level` |
| — | *Installation Notes*: "needs an install script to build the directory structure and include assets… fireworks will ensue" | Obsolete. `uv sync` installs the package, assets ship inside it, and `v_chk_paths.ensure_runtime_dirs()` creates the output directories idempotently on every run |

## ID collisions

The original numbering reused identifiers, so a bare "Bug-023" is ambiguous in older notes:

- **Bug-023** — open: *"remove/hardcode Setup Screen logo resize"*; done: *"Highlight use of uppercase"*
- **Bug-010** — done twice: *"Change xkey to x-k-e-y"* and *"IsVisible formula broken in Summary"*
- **Bug-011** — done twice: *"All tags m/b lowercase"* and *"Summary Table Totals are wrong"*
- **Bug-012** — done twice: *"Unique Values calc as diff on Tags"* and *"Summary Table contains Tags"*

Empty placeholder entries (`Bug-0`, `ER-024` … `ER-029`, `ER-0`) carried no content and were dropped.

---

## Importing to GitHub

The repository already exists — `slappycat2/obsidian-vault-health-check`, private, with Issues
enabled — so there is nothing to create. `pyproject.toml`'s `Homepage` and `Issues` URLs were
verified against it and are correct.

1. Install the GitHub CLI (<https://cli.github.com>) and run `gh auth login`.
2. Add the remote and push:
   ```bash
   git remote add origin https://github.com/slappycat2/obsidian-vault-health-check.git
   git push -u origin master
   ```
3. Import this backlog (`--dry-run` first — it needs neither `gh` nor a remote):
   ```bash
   bash scripts/import_backlog_issues.sh
   ```
4. Delete `scripts/import_backlog_issues.sh` — it is a one-shot bootstrap, and re-running it would
   create duplicates.

> **The remote holds three unrelated histories.** `main` is the pre-2026 development history and
> remains the default branch; `archive/2026-02-snapshot` is the pre-modernisation snapshot (formerly
> the remote `master`); `master` is this modernised tree. None of them share a common ancestor, so
> git will refuse to merge or compare them — that is expected, not a broken checkout.

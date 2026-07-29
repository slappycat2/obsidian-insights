#!/usr/bin/env bash
#
# One-shot import of docs/BACKLOG.md into GitHub issues.
#
#   bash scripts/import_backlog_issues.sh            # create the issues
#   bash scripts/import_backlog_issues.sh --dry-run  # print what would be created
#
# Requires the GitHub CLI (https://cli.github.com), `gh auth login`, and an
# `origin` remote pointing at the target repository.
#
# This script is NOT idempotent -- gh has no "create if absent" for issues, so
# running it twice creates every issue twice. Delete it once it has run.

set -euo pipefail

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

# --dry-run only prints, so it deliberately needs neither gh nor a remote.
if ! $DRY_RUN; then
    if ! command -v gh >/dev/null 2>&1; then
        echo "error: the GitHub CLI (gh) is not installed -- see https://cli.github.com" >&2
        echo "       (re-run with --dry-run to preview without it)" >&2
        exit 1
    fi
    if ! gh auth status >/dev/null 2>&1; then
        echo "error: not authenticated. Run: gh auth login" >&2
        exit 1
    fi
    if ! git remote get-url origin >/dev/null 2>&1; then
        echo "error: no 'origin' remote. Create the repo first, e.g." >&2
        echo "  gh repo create <owner>/<name> --private --source=. --remote=origin --push" >&2
        exit 1
    fi
fi

# --------------------------------------------------------------------------
# Labels. 'bug' and 'enhancement' exist in every new repository; the rest may
# not, so failures here are non-fatal.
# --------------------------------------------------------------------------
create_label() {
    $DRY_RUN && { echo "[dry-run] label: $1"; return; }
    gh label create "$1" --color "$2" --description "$3" 2>/dev/null \
        || echo "  label '$1' already exists, skipping"
}

echo "Ensuring labels exist..."
create_label "bug"         "d73a4a" "Something is not working correctly"
create_label "enhancement" "a2eeef" "New feature or request"
create_label "refactor"    "fbca04" "Internal restructuring, no behaviour change"
create_label "testing"     "0e8a16" "Test coverage and verification"
create_label "parsing"     "5319e7" "Markdown, YAML, tag and property harvesting"
create_label "workbook"    "1d76db" "Spreadsheet generation and formatting"

# --------------------------------------------------------------------------
# Issues. Each entry: title | labels | body
# The original Bug-NNN / ER-NNN identifier is preserved in the body for
# traceability with older commits and notes.
# --------------------------------------------------------------------------
create_issue() {
    local title="$1" labels="$2" body="$3"

    if $DRY_RUN; then
        printf '[dry-run] %-72s [%s]\n' "$title" "$labels"
        return
    fi

    gh issue create --title "$title" --label "$labels" --body "$body" >/dev/null
    printf '  created: %s\n' "$title"
}

echo
echo "Creating issues..."

create_issue \
    "Properties tab file count is files x values, not distinct files" \
    "bug,workbook" \
    $'The "Files" total on the Properties tab counts one for every property in every file, so a note with two properties is counted twice. That makes the figure meaningless as a file count.\n\nThe original note added: "Look for more like this!" -- other totals may have the same problem.\n\n_Originally Bug-019 (in progress)._'

create_issue \
    "Verify workbook output in LibreOffice Calc, Google Sheets and on macOS" \
    "bug,testing" \
    $'The generated `.xlsx` leans on Excel-specific features: `_xlfn.AGGREGATE`, `_xlfn.UNIQUE`, `_xlfn.FILTER`, structured table references and conditional formatting. None of this is verified outside Excel on Windows.\n\nCI now runs the *test suite* on macOS and Linux, but nothing checks how the workbook actually renders in another spreadsheet application.\n\n_Originally Bug-006._'

create_issue \
    "Audit property and tag handling against current Obsidian and Dataview rules" \
    "bug,parsing" \
    $'Confirm that property and tag recognition still matches what Obsidian and Dataview actually do -- valid characters, casing, reserved and deprecated property names.\n\n_Originally Bug-014._'

create_issue \
    "IsVisible column is defined and calculated in three separate places" \
    "refactor,workbook" \
    $'`IsVisCol` is defined and computed in three locations, so a change to one can silently disagree with the others.\n\nSee `NewTab.calc_col_pointers()` and `tab_tots_isVisible_col` handling in `v_chk_wb_tabs.py`, plus the export side in `v_chk_xl.py`.\n\n_Originally Bug-016._'

create_issue \
    "Workbook font handling should degrade when fonts are unavailable" \
    "bug,workbook" \
    $'Tab definitions hardcode "Berlin Sans FB Demi" and "Berlin Sans" (`font_title_lst` / `font_subs_lst` in `v_chk_wb_tabs.py`). Neither is present on a typical macOS or Linux machine, and the substitution is left to the spreadsheet application.\n\n_Originally Bug-018._'

create_issue \
    "Exclude templates and plugin-nested data from the vault tabs" \
    "bug,parsing" \
    $'Template notes and plugin-managed nested frontmatter should not inflate the Properties, Tags and Files tabs, since they do not represent real vault metadata.\n\nTemplate files are currently skipped outright when a Templater folder is configured (`VaultHealthCheck.process_vault`), which is a related but separate behaviour worth revisiting.\n\n_Originally Bug-020. Bug-015 was closed as a duplicate of this while this stayed open._'

create_issue \
    "Hardcode the Setup Screen logo size once macOS and Linux are verified" \
    "bug" \
    $'The Setup Screen resizes its logo at runtime as a cross-platform workaround. Once the layout is confirmed on macOS and Linux, replace it with fixed dimensions.\n\n_Originally Bug-023 (open). Note the same ID was also used for a completed item, "Highlight use of uppercase"._'

create_issue \
    "Indicate truncation when a row has more file links than link columns" \
    "enhancement,workbook" \
    $'When a property value appears in more files than there are link columns, the extra links are dropped with no indication. Show something like "More exist!" in the final column.\n\nThe column count comes from `ctot[11]`/`ctot[12]` capped by `link_lim_vals`/`link_lim_tags`.\n\n_Originally ER-002._'

create_issue \
    "Gather more vault statistics" \
    "enhancement,workbook" \
    $'Candidates from the original list:\n\n- Most-used tags\n- Inline vs frontmatter split\n- A top-tags graph\n- Dataview-specific statistics\n\n_Originally ER-003._'

create_issue \
    "Support nested tags: distinguish explicit from cumulative" \
    "enhancement,parsing" \
    $'Dataview draws a distinction v_chk currently does not:\n\n- `file.tags` breaks a tag down by level, so `#Tag/1/A` is stored as `#Tag`, `#Tag/1`, `#Tag/1/A`\n- `file.etags` keeps only the explicit tag, `#Tag/1/A`\n\nCounting these correctly changes both the Tags tab and the totals.\n\n_Originally ER-007._'

create_issue \
    "Handle sub-tags such as assets/mac/software better" \
    "enhancement,parsing" \
    $'Sub-tags are currently treated as opaque strings. Grouping by prefix would make the Tags tab far more useful on vaults that use hierarchical tags.\n\nRelated to the explicit-vs-cumulative question in the nested tags issue.\n\n_Originally ER-008._'

create_issue \
    "Support Dataview task shorthand fields" \
    "enhancement,parsing" \
    $'Task shorthands (due dates, completion, priority on task lines) are not recognised.\n\nSee https://blacksmithgu.github.io/obsidian-dataview/annotation/metadata-tasks/#field-shorthands\n\n_Originally ER-009._'

create_issue \
    "Consider array formulas in the Summary tab" \
    "enhancement,workbook" \
    $'Speculative in the original note ("Can\'t think of one, now, but..."). Worth revisiting only if a concrete use case appears.\n\n_Originally ER-011._'

create_issue \
    "Option to show note name only, instead of relative path, in hyperlinks" \
    "enhancement,workbook" \
    $'`bool_rel_paths` already exists in the config. This asks for it to be honoured consistently across every hyperlink column.\n\n_Originally ER-012._'

create_issue \
    "Identify singular and plural usages of properties and tags" \
    "enhancement,parsing" \
    $'Flag likely accidental variants -- `author` alongside `authors`, `tag` alongside `tags` -- the way uppercase usage is already highlighted.\n\n_Originally ER-013._'

create_issue \
    "Fix the Area51 table dump" \
    "enhancement,workbook" \
    $'The Area51 diagnostic tab does not dump its table correctly. It is exported separately from the main loop via `ExcelExporter.export_area51()`.\n\n_Originally ER-014._'

create_issue \
    "Rename skip_rel_str to skip_abs_lst_user" \
    "refactor" \
    $'`skip_rel_str` is a comma-separated string of directory names, not a relative-path string, and it sits confusingly next to the derived `skip_abs_lst`.\n\nIt is persisted in `CONFIG.yaml`, so a rename needs a fallback for existing config files.\n\n_Originally ER-015._'

create_issue \
    "Add Date Created and Date Modified columns to the Files tab" \
    "enhancement,workbook" \
    $'Both are available from `Path.stat()` while walking the vault.\n\n_Originally ER-016._'

create_issue \
    "Extract property and tag isolation into standalone classes" \
    "refactor,parsing" \
    $'The routines that isolate properties and tags are embedded in `VaultHealthCheck`. Pulling them into standalone classes would make them reusable and would open the door to a built-in search-and-replace feature.\n\n_Originally ER-017._'

create_issue \
    "Remember per-vault settings between runs" \
    "enhancement" \
    $'`sys_vlts` already stores a settings record per vault (skip list, link limits, display flags), but the setup screen does not restore them when switching vault.\n\n_Originally ER-018._'

create_issue \
    "Flag unquoted YAML links in the Files tab" \
    "enhancement,parsing" \
    $'Unquoted `[[wikilinks]]` in frontmatter are parsed by PyYAML as nested lists rather than strings, which is why `unpack_yaml` needs a special case for them. Surfacing them in the Files tab (the original note suggested a lucide question icon) would let users quote them.\n\n_Originally ER-019._'

create_issue \
    "List vault files that Obsidian no longer references" \
    "enhancement" \
    $'Orphaned attachments and images -- files present in the vault directory that nothing links to.\n\n_Originally ER-020._'

create_issue \
    "Warn when link columns are hidden, with an option to suppress" \
    "enhancement,workbook" \
    $'Related to the link-truncation issue: when `link_lim_vals`/`link_lim_tags` hide columns, say so in the workbook, and let the user turn the warning off.\n\n_Originally ER-021._'

create_issue \
    "Add a Log tab showing batch numbers, dates, counters and vault names" \
    "enhancement,workbook" \
    $'A per-run history tab: batch number, creation date, the `ctot` counters and the vault analysed. The data already exists in the numbered batch files under `data/batch_files/`.\n\n_Originally ER-023._'

create_issue \
    "Refactoring: reduce overlap between tab-definition subclasses" \
    "refactor,workbook" \
    $'The twelve `DefXxxx(NewTab)` subclasses in `v_chk_wb_tabs.py` repeat a good deal of structure. Identify the genuine overlap and lift it into the base class, and clean up leftover commented-out code and print statements.\n\nNote that adding or renaming a tab currently touches five places -- see CLAUDE.md.\n\n_Originally ER-999._'

echo
if $DRY_RUN; then
    echo "Dry run complete -- nothing was created."
else
    echo "Done. Delete this script now; re-running it would duplicate every issue."
fi

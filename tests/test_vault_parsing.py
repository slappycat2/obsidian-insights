"""Tests for VaultScan, the markdown/YAML harvesting stage.

This is the riskiest code in the project -- it parses arbitrary user markdown --
and it is pure enough to test directly: give it a directory of .md files, look
at the obs_* dictionaries that come back.

Shapes produced (see upd_obs_props):
    obs_props  {property: {value: [filepath, ...]}}
    obs_atags  {tag: {tag: [filepath, ...]}}       -- key and value are the tag
    obs_xyaml  {code: {filepath: [filepath]}}      -- code is BadY/NoFm/MtFm/...
    obs_dupfn  {'dupfn': {filename: [filepath, ...]}}
    obs_codes  {filepath: {CODEBLOCK_SIG: [block text, ...]}}
    obs_files  {'filepath|F' or '|I': {property: [original_case, value, ...]}}
"""

import pytest


# ---------------------------------------------------------------------------
# Frontmatter properties
# ---------------------------------------------------------------------------

def test_frontmatter_properties_are_harvested(scan):
    result = scan({"note.md": """
        ---
        author: Jane
        status: draft
        ---

        Body text.
    """})

    assert "Jane" in result.obs_props["author"]
    assert "draft" in result.obs_props["status"]


def test_property_keys_are_lowercased(scan):
    """Obsidian treats properties case-insensitively, so ovi groups on lowercase."""
    result = scan({"note.md": """
        ---
        Status: Draft
        ---
    """})

    assert "status" in result.obs_props
    assert "Status" not in result.obs_props
    # The value keeps its original casing; only the key is normalised.
    assert "Draft" in result.obs_props["status"]


def test_original_key_casing_is_preserved_in_obs_files(scan):
    """The Files tab is the only place that reports the casing actually used."""
    result = scan({"note.md": """
        ---
        Status: Draft
        ---
    """})

    frontmatter_entries = [v for k, v in result.obs_files.items() if k.endswith("|F")]
    assert frontmatter_entries, "expected a frontmatter entry"
    assert "Status" in frontmatter_entries[0]["status"]


def test_list_valued_property_yields_one_entry_per_item(scan):
    result = scan({"note.md": """
        ---
        aliases: [one, two]
        ---
    """})

    assert set(result.obs_props["aliases"]) == {"one", "two"}


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------

def test_frontmatter_tags_are_lowercased(scan):
    result = scan({"note.md": """
        ---
        tags:
          - Alpha
          - beta
        ---
    """})

    assert "alpha" in result.obs_atags
    assert "beta" in result.obs_atags
    assert "Alpha" not in result.obs_atags


def test_inline_body_tags_are_harvested(scan):
    result = scan({"note.md": "Some prose with an inline #bodytag in it.\n"})

    assert "bodytag" in result.obs_atags


def test_tags_inside_code_blocks_are_ignored(scan):
    result = scan({"note.md": """
        Real #keeper tag.

        ```python
        # not_a_tag
        x = "#fake"
        ```
    """})

    assert "keeper" in result.obs_atags
    assert "fake" not in result.obs_atags


# ---------------------------------------------------------------------------
# Inline (Dataview) properties
# ---------------------------------------------------------------------------

def test_bracketed_inline_property_is_harvested(scan):
    result = scan({"note.md": "A line with [mood:: happy] in it.\n"})

    assert "happy" in result.obs_props["mood"]


def test_line_start_inline_property_is_harvested(scan):
    """Regression: rgx_body_pros lacked re.MULTILINE, so its leading ^ anchored
    to the start of the whole body rather than to each line. Only bracketed
    inline fields were ever found."""
    result = scan({"note.md": """
        Intro paragraph.

        rating:: 5
    """})

    assert "5" in result.obs_props["rating"]


# ---------------------------------------------------------------------------
# Malformed / missing frontmatter
# ---------------------------------------------------------------------------

def test_unparseable_yaml_is_recorded_as_BadY(scan):
    result = scan({"bad.md": """
        ---
        author: [unclosed
        ---

        Body.
    """})

    assert "BadY" in result.obs_xyaml
    assert any("bad.md" in path for path in result.obs_xyaml["BadY"])


def test_file_without_frontmatter_is_recorded_as_NoFm(scan):
    result = scan({"plain.md": "Just prose, no frontmatter.\n"})

    assert "NoFm" in result.obs_xyaml
    assert any("plain.md" in path for path in result.obs_xyaml["NoFm"])


def test_valid_frontmatter_is_not_flagged(scan):
    result = scan({"note.md": """
        ---
        author: Jane
        ---

        Body.
    """})

    assert "BadY" not in result.obs_xyaml


# ---------------------------------------------------------------------------
# Frontmatter boundaries -- a `---` that is not a frontmatter delimiter
# ---------------------------------------------------------------------------

def test_body_horizontal_rules_are_not_read_as_frontmatter(scan):
    """The headline regression. split_file() took the first two `---` matches
    wherever they fell, so a note with no frontmatter but two horizontal rules
    had the text between them fed to yaml.safe_load and everything before the
    second rule silently discarded -- 23 of 565 notes in one real vault."""
    result = scan({"rules.md": """
        intro:: alpha

        ---

        ## Middle

        ---

        Tail.
    """})

    assert "alpha" in result.obs_props["intro"]     # used to be thrown away
    assert any("rules.md" in path for path in result.obs_xyaml["NoFm"])
    assert "NonD" not in result.obs_xyaml           # "## Middle" was never YAML


def test_setext_heading_underline_is_not_frontmatter(scan):
    """A heading over `---` is a setext H2, not an opening delimiter."""
    result = scan({"setext.md": """
        My Heading
        ---

        note:: kept

        ---

        Tail.
    """})

    assert any("setext.md" in path for path in result.obs_xyaml["NoFm"])
    assert "kept" in result.obs_props["note"]


def test_unclosed_frontmatter_delimiter_is_not_frontmatter(scan):
    """An opening `---` that is never closed leaves the whole file as body."""
    result = scan({"orphan.md": """
        ---
        title: Orphan

        rating:: 7
    """})

    assert any("orphan.md" in path for path in result.obs_xyaml["NoFm"])
    assert "7" in result.obs_props["rating"]


def test_a_leading_code_fence_does_not_shift_the_boundary(scan):
    """Code fences are stripped after the split now. Stripping them first
    promoted a body rule to the top of the file and defeated the anchor."""
    result = scan({"fenced.md": """
        ```dataview
        LIST
        ```

        topic:: fences

        ---

        ## Section

        ---

        Tail.
    """})

    assert any("fenced.md" in path for path in result.obs_xyaml["NoFm"])
    assert "fences" in result.obs_props["topic"]


def test_split_file_ignores_a_rule_that_follows_text(scan):
    """The anchor is the whole fix: the opening pattern may skip whitespace but
    cannot cross real text, so no body rule can ever open a frontmatter block."""
    result = scan({"any.md": "Body.\n"})

    assert result.split_file("Intro.\n\n---\nnot: frontmatter\n---\n") == (
        "", "Intro.\n\n---\nnot: frontmatter\n---\n")

    # A blank line above the delimiter is still frontmatter: that is what a
    # stripped Templater block leaves behind at the top of a template. The body
    # opens with the newline that ends the closing delimiter's own line.
    assert result.split_file("\n---\nis: frontmatter\n---\nBody.\n") == (
        "is: frontmatter", "\nBody.\n")


def test_the_closing_delimiter_is_not_left_in_the_body(scan):
    """body_text started at the closing `---` rather than after it, so every
    body carried a stray delimiter as its first line."""
    result = scan({"any.md": "Body.\n"})

    assert result.split_file("---\nauthor: Jane\n---\nBody.\n") == (
        "author: Jane", "\nBody.\n")


# ---------------------------------------------------------------------------
# Empty notes
# ---------------------------------------------------------------------------

def test_an_empty_file_is_counted_and_recorded_once(scan):
    """ctot[13] counts empty notes. NoFm used to be recorded twice for one --
    in split_file and again in parse_file -- and upd_obs_props does not dedupe,
    so the note picked up a second, identical hyperlink column."""
    result = scan({"empty.md": "", "real.md": "Body.\n"})

    assert result.ctot[13] == 1
    assert any("empty.md" in path for path in result.obs_empty)

    nofm = result.obs_xyaml["NoFm"]
    empty_key = next(key for key in nofm if "empty.md" in key)
    assert len(nofm[empty_key]) == 1


def test_a_whitespace_only_file_counts_as_empty(make_vault, stub_config):
    """All-whitespace is empty. The test reads the raw file rather than the
    stripped text, so a template holding only `<% tp.date.now() %>` -- which
    strips away to nothing -- is not mistaken for an empty note."""
    from ovi.ovi_build import VaultScan

    vault = make_vault({"real.md": "Body.\n"})
    # written directly: make_vault lstrips, which would leave nothing to test
    (vault / "blank.md").write_text("   \n\n\t\n", encoding="utf-8")

    result = VaultScan(stub_config(vault))

    assert result.ctot[13] == 1
    assert any("blank.md" in path for path in result.obs_empty)


def test_an_empty_template_is_not_listed_on_the_xyml_tab(make_vault, stub_config):
    """split_file recorded NoFm itself, which bypassed record_yaml_issue() and
    the template exemption inside it."""
    from ovi.ovi_build import VaultScan

    vault = make_vault({"Templates/Blank.md": "", "real.md": "Body.\n"})
    result = VaultScan(
        stub_config(vault, dir_templates=str(vault / "Templates")))

    assert not any("Blank.md" in path
                   for path in result.obs_xyaml.get("NoFm", {}))


def test_ctot_10_counts_notes_without_frontmatter(scan):
    """Slot 10 used to increment only for a wholly empty file, while both
    CLAUDE.md and the Summary tab described it as something else."""
    result = scan({
        "none.md":  "Body.\n",
        "rules.md": "a\n\n---\n\nb\n\n---\n\nc\n",
        "yaml.md":  "---\nauthor: Jane\n---\nBody.\n",
    })

    assert result.ctot[10] == 2   # none.md and rules.md
    assert result.ctot[5] == 1    # only yaml.md has frontmatter


# ---------------------------------------------------------------------------
# Duplicates, code blocks, skipping
# ---------------------------------------------------------------------------

def test_duplicate_filenames_across_folders_are_detected(scan):
    result = scan({
        "a/Meeting.md": "First.\n",
        "b/Meeting.md": "Second.\n",
        "c/Unique.md": "Third.\n",
    })

    duplicates = result.obs_dupfn["dupfn"]
    assert len(duplicates["Meeting.md"]) == 2
    assert len(duplicates["Unique.md"]) == 1


def test_code_blocks_are_captured_with_uppercased_signature(scan):
    result = scan({"note.md": """
        Text.

        ```dataview
        TABLE file.name
        ```
    """})

    signatures = {sig for block in result.obs_codes.values() for sig in block}
    assert "DATAVIEW" in signatures


def test_properties_inside_code_blocks_are_not_harvested(scan):
    result = scan({"note.md": """
        ```yaml
        ghost:: value
        ```
    """})

    assert "ghost" not in result.obs_props


def test_skipped_directories_are_not_scanned(scan):
    result = scan(
        {
            "keep/Kept.md": "---\nauthor: Jane\n---\n",
            "Archive/Skipped.md": "---\nauthor: Ghost\n---\n",
        },
        skip_rel_str="Archive",
    )

    assert "Jane" in result.obs_props["author"]
    assert "Ghost" not in result.obs_props["author"]


# ---------------------------------------------------------------------------
# Regressions from Phase 1
# ---------------------------------------------------------------------------

def test_vault_without_templater_plugin_does_not_crash(scan):
    """Regression: get_templates_dir() returns None when Templater is absent,
    and that was passed straight to Path(), raising TypeError. Every vault
    without the plugin failed."""
    result = scan({"note.md": "---\nauthor: Jane\n---\n"}, dir_templates=None)

    assert "Jane" in result.obs_props["author"]


def test_nested_list_property_does_not_crash(scan):
    """Regression: a YAML value that is itself a list reached upd_obs_props as a
    dict key and raised 'unhashable type: list'."""
    result = scan({"note.md": """
        ---
        related:
          - [alpha, beta]
        ---
    """})

    assert "alpha, beta" in result.obs_props["related"]


def test_unquoted_wikilink_value_is_rendered_as_a_link(scan):
    """An unquoted "- [[Some Note]]" parses as [[['Some Note']]] and should come
    back out as the link text, not as a Python repr."""
    result = scan({"note.md": """
        ---
        related:
          - [[Some Note]]
        ---
    """})

    assert "[[Some Note]]" in result.obs_props["related"]


def test_flow_list_does_not_lose_elements(scan):
    """Regression: the unquoted-wikilink branch in unpack_yaml also fired on an
    ordinary flow sequence and rebuilt the value from value[0][0] alone, so
    "- [alpha, beta]" was silently recorded as "[[alpha]]" and beta vanished."""
    result = scan({"note.md": """
        ---
        related:
          - [alpha, beta]
        ---
    """})

    recorded = " ".join(result.obs_props["related"])
    assert "alpha" in recorded
    assert "beta" in recorded


def test_numeric_tags_value_does_not_crash(scan):
    """Regression: upd_val() called v.lower() before normalising, so a
    non-string tags value raised AttributeError."""
    result = scan({"note.md": """
        ---
        tags: 2024
        ---
    """})

    assert result.obs_atags  # harvested something rather than raising


# ---------------------------------------------------------------------------
# Counters
# ---------------------------------------------------------------------------

def test_ctot_counts_markdown_files(scan):
    result = scan({
        "one.md": "A.\n",
        "two.md": "B.\n",
        "three.md": "C.\n",
    })

    assert result.ctot[0] == 3   # markdown files seen
    assert result.ctot[3] == 3   # files processed


# ---------------------------------------------------------------------------
# Plugin-managed nested frontmatter (issue #6)
# ---------------------------------------------------------------------------

PLUGIN_NOTE = {
    "Plain.md": """
        ---
        author: Jane
        ---
        A normal note.
    """,
    "PluginNote.md": """
        ---
        author: Sam
        tags: [research]
        kindle-sync:
          bookId: '12345'
          title: Some Book
          author: Some Author
        ---
        Body text.

        rating:: 5
    """,
}


def test_nested_plugin_data_goes_to_obs_nests(scan):
    """Nested dicts are not something Obsidian allows, so a plugin wrote them.
    They belong on the Nested tab."""
    result = scan(PLUGIN_NOTE)

    nested = {key for bucket in result.obs_nests.values() for key in bucket}

    assert "kindle-sync/bookid" in nested
    assert "kindle-sync/title" in nested


def test_nested_plugin_data_stays_off_the_files_tab(scan):
    """Regression, issue #6: upd_obs_files was called outside the plugin
    branch, so plugin-managed keys inflated the Files tab alongside real ones."""
    result = scan(PLUGIN_NOTE)

    file_keys = {key for entry in result.obs_files.values() for key in entry}

    assert not [k for k in file_keys if k.startswith("kindle-sync/")]
    assert "author" in file_keys


def test_real_properties_survive_in_a_plugin_managed_note(scan):
    """Regression, issue #6: routing keyed off a whole-file scan for a plugin
    name, so every property in a note containing a kindle-sync block -- its own
    top-level author, its tags, even inline "key:: value" pairs from the body --
    was diverted into obs_nests and vanished from the vault tabs."""
    result = scan(PLUGIN_NOTE)

    assert "Sam" in result.obs_props["author"]      # top-level, alongside the plugin block
    assert "research" in result.obs_atags           # tags still reach the Tags tab
    assert "5" in result.obs_props["rating"]        # inline "key:: value" from the body


def test_a_value_merely_mentioning_a_plugin_is_not_plugin_data(scan):
    """Regression, issue #6: the plugin test was a substring search of the raw
    frontmatter, so a note that only talked about a plugin had its properties
    diverted."""
    result = scan({"note.md": """
        ---
        author: Jane
        summary: how I set up kindle-sync last year
        ---
    """})

    assert "Jane" in result.obs_props["author"]
    assert result.obs_nests == {}


TEMPLATE_VAULT = {
    "Notes/Real.md": """
        ---
        author: Jane
        tags: [research]
        ---

        Real note.

        ```dataview
        TABLE file.name
        ```
    """,
    "Templates/Daily.md": """
        ---
        author: PLACEHOLDER
        date: <% tp.date.now("YYYY-MM-DD") %>
        tags: [daily]
        ---

        # <% tp.file.title %>

        ```dataview
        TASK WHERE !completed
        ```
    """,
    "Templates/Broken.md": """
        ---
        title: <% tp.file.title %>
        unclosed: [oops
        ---
    """,
}


def scan_with_templates(make_vault, stub_config):
    """A vault whose Templates/ folder is registered with Templater.

    dir_templates must be absolute -- is_subdirectory() tests it against
    md_file.parents, and a relative Path silently matches nothing.
    """
    from ovi.ovi_build import VaultScan

    vault = make_vault(TEMPLATE_VAULT)
    return VaultScan(stub_config(vault, dir_templates=str(vault / "Templates")))


def test_templates_are_excluded_from_the_vault_tabs(make_vault, stub_config):
    """Issue #6: a template's placeholder properties are not vault metadata."""
    result = scan_with_templates(make_vault, stub_config)

    assert "Jane" in result.obs_props["author"]
    assert "PLACEHOLDER" not in result.obs_props["author"]
    assert "date" not in result.obs_props
    assert "daily" not in result.obs_atags       # the template's tag, not the vault's
    assert "research" in result.obs_atags


def test_templates_are_harvested_into_obs_tmplt(make_vault, stub_config):
    """Issue #6: nothing used to populate obs_tmplt, so the Templates tab was
    always empty and always dropped from the workbook."""
    result = scan_with_templates(make_vault, stub_config)

    assert "PLACEHOLDER" in result.obs_tmplt["author"]
    assert "daily" in result.obs_tmplt["tags"]


def test_a_dynamic_template_value_is_marked_not_blank(make_vault, stub_config):
    """`date: <% tp.date.now() %>` loses its value when Templater tags are
    stripped. Marked the way obs_nests marks an empty, so the cell is not just
    blank and unexplained."""
    result = scan_with_templates(make_vault, stub_config)

    assert "(-None-)" in result.obs_tmplt["date"]


def test_a_template_with_invalid_yaml_is_not_a_vault_problem(make_vault, stub_config):
    """Templater syntax is not valid YAML, so a template that fails to load is
    normal. Flagging it would fill the Issues tab with false positives."""
    result = scan_with_templates(make_vault, stub_config)

    assert "BadY" not in result.obs_xyaml


def test_template_code_blocks_are_not_vault_code_blocks(make_vault, stub_config):
    """A template's code blocks are boilerplate waiting to be stamped out."""
    result = scan_with_templates(make_vault, stub_config)

    sources = " ".join(result.obs_codes)
    assert "Real.md" in sources
    assert "Daily.md" not in sources


def test_templates_are_not_notes_for_counting_purposes(make_vault, stub_config):
    """A template is not a duplicate-filename candidate and is not an analysed
    note; ctot[1] counts templates separately."""
    result = scan_with_templates(make_vault, stub_config)

    assert result.ctot[1] == 2          # two templates
    assert result.ctot[3] == 1          # one real note analysed
    assert set(result.obs_dupfn["dupfn"]) == {"Real.md"}
